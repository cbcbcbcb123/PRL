"""Immutable M2A v05 protocol for T256 and the three-level time gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .config import FROZEN_CONFIG, SpatialLevel
from .protocol_v03 import (
    DIRECT_BACKWARD_ERROR_TOLERANCE,
    DIRECT_RELATIVE_RESIDUAL_TOLERANCE,
    DISCRETE_LEDGER_CLOSURE_TOLERANCE,
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    EXPECTED_V01_CONFIG_DIGEST,
)
from .protocol_v04 import validate_source_t64_result


EXPECTED_T128_PASS_SUMMARY_SHA256 = (
    "0b1ccce87abdbe65633a66fe52c1cb70c24de0c4c8a685d6e2cabf5d37e624ef"
)
EXPECTED_T128_ENDPOINT_SUMMARIES_SHA256 = (
    "ab4a32a886c634b5b3f529d4890f6cdebe412ca1bff9ea3b5191147fa8943511"
)
EXPECTED_T128_HASH_LEDGER_SHA256 = (
    "d819e9c7315b89450ea3e8b8417baf9197370de54fe52efd179dbfb2d981b67f"
)
EXPECTED_T128_LEDGER_ENTRY_COUNT = 25
EXPECTED_T128_DYNAMIC_NPZ_COUNT = 12
TIME_FINE_RELATIVE_TOLERANCE = 0.01


@dataclass(frozen=True)
class M2AV05Protocol:
    schema: str = "paper2_m2a_protocol_v05"
    spatial_levels: tuple[SpatialLevel, ...] = (
        SpatialLevel("S2", 32, 8),
        SpatialLevel("S3", 64, 16),
        SpatialLevel("S4", 128, 32),
    )
    steps_per_cycle: int = 256
    solver_levels: tuple[str, ...] = ("D0",)
    representations: tuple[str, ...] = ("DCM", "FEM")
    common_projection_segments: int = 64
    runtime_budget_seconds: float = 5400.0
    memory_budget_gib: float = 16.0
    cpu_processes: int = 1
    expected_endpoint_count: int = 54
    expected_spatial_records: int = 74
    expected_cycle_records: int = 54
    expected_hotspot_records: int = 2
    expected_three_level_time_records: int = 74
    time_fine_relative_tolerance: float = TIME_FINE_RELATIVE_TOLERANCE
    direct_relative_residual_tolerance: float = DIRECT_RELATIVE_RESIDUAL_TOLERANCE
    direct_backward_error_tolerance: float = DIRECT_BACKWARD_ERROR_TOLERANCE
    discrete_ledger_closure_tolerance: float = DISCRETE_LEDGER_CLOSURE_TOLERANCE
    source_config_digest: str = EXPECTED_V01_CONFIG_DIGEST
    dcm_passive_scale: float = EXPECTED_DCM_PASSIVE_SCALE
    dcm_active_scale: float = EXPECTED_DCM_ACTIVE_SCALE

    def checked(self) -> "M2AV05Protocol":
        if FROZEN_CONFIG.digest() != EXPECTED_V01_CONFIG_DIGEST:
            raise ValueError("the frozen v01 configuration digest changed")
        if tuple(level.label for level in self.spatial_levels) != ("S2", "S3", "S4"):
            raise ValueError("the v05 production ladder must be S2/S3/S4")
        if tuple((level.nx, level.ny_per_layer) for level in self.spatial_levels) != (
            (32, 8),
            (64, 16),
            (128, 32),
        ):
            raise ValueError("the v05 nested spatial ladder changed")
        if self.steps_per_cycle != 256:
            raise ValueError("v05 is the T256 stage only")
        if self.solver_levels != ("D0",):
            raise ValueError("v05 has exactly one operational direct-solver level D0")
        if self.representations != ("DCM", "FEM"):
            raise ValueError("both myocardium representations are required")
        expected = (
            len(FROZEN_CONFIG.cases)
            * len(self.representations)
            * len(self.spatial_levels)
            * len(self.solver_levels)
        )
        if expected != self.expected_endpoint_count:
            raise ValueError("the v05 T256 endpoint count must remain 54")
        if self.common_projection_segments != 64:
            raise ValueError("the diagnostic projection must remain on 64 segments")
        if (
            self.expected_spatial_records,
            self.expected_cycle_records,
            self.expected_hotspot_records,
            self.expected_three_level_time_records,
        ) != (74, 54, 2, 74):
            raise ValueError("the v05 gate record counts changed")
        if self.time_fine_relative_tolerance != 0.01:
            raise ValueError("the v05 finest time-difference tolerance must remain 1 percent")
        return self

    def spatial(self, label: str) -> SpatialLevel:
        return next(level for level in self.checked().spatial_levels if level.label == label)

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self.checked())
        payload["cases"] = list(FROZEN_CONFIG.cases)
        payload["matrix"] = {
            "cases": list(FROZEN_CONFIG.cases),
            "representations": list(self.representations),
            "spatial_levels": [level.label for level in self.spatial_levels],
            "steps_per_cycle": 256,
            "solver_levels": ["D0"],
            "endpoint_count": 54,
        }
        payload["spatial_gate"] = {
            "production_observable": "native_nodal_or_spring_traction",
            "finest_pair": ["S3", "S4"],
            "relative_tolerance": FROZEN_CONFIG.spatial_endpoint_relative_tolerance,
            "direction_required": True,
            "hotspot_cell_width": FROZEN_CONFIG.length / self.spatial("S4").nx,
        }
        payload["cycle_gate"] = {
            "relative_tolerance": FROZEN_CONFIG.cycle_state_relative_tolerance
        }
        payload["ledger_gate"] = {
            "maximum_normalized_residual": FROZEN_CONFIG.power_ledger_relative_tolerance,
            "maximum_ledger_minus_equilibrium_work_relative": (
                self.discrete_ledger_closure_tolerance
            ),
        }
        payload["three_level_time_gate"] = {
            "source_levels": ["T64", "T128"],
            "target": "T256",
            "spatial_level": "S4",
            "solver_level": "D0",
            "expected_records": self.expected_three_level_time_records,
            "finest_relative_tolerance": self.time_fine_relative_tolerance,
            "direction_rule": "same_sign_or_both_changes_within_one_percent_scale",
            "nonincrease_rule": "abs_delta_12_le_abs_delta_01_plus_frozen_floor",
            "convergence_order_fitted": False,
        }
        return payload

    def digest(self) -> str:
        serialized = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_json(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_json(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    return False


def validate_source_t128_result(source_dir: Path) -> dict[str, Any]:
    expected = {
        "pass_summary.json": EXPECTED_T128_PASS_SUMMARY_SHA256,
        "endpoint_summaries.json": EXPECTED_T128_ENDPOINT_SUMMARIES_SHA256,
        "hash_ledger.json": EXPECTED_T128_HASH_LEDGER_SHA256,
    }
    hashes: dict[str, Any] = {}
    for name, expected_digest in expected.items():
        path = source_dir / name
        actual_digest = _sha256(path)
        hashes[name] = {
            "expected": expected_digest,
            "actual": actual_digest,
            "pass": actual_digest == expected_digest,
        }

    with (source_dir / "pass_summary.json").open("r", encoding="utf-8") as stream:
        pass_summary = json.load(stream)
    with (source_dir / "endpoint_summaries.json").open(
        "r", encoding="utf-8"
    ) as stream:
        endpoint_summaries = json.load(stream)
    with (source_dir / "hash_ledger.json").open("r", encoding="utf-8") as stream:
        hash_ledger = json.load(stream)

    ledger_failures: list[str] = []
    for relative_path, record in hash_ledger.get("files", {}).items():
        path = source_dir / relative_path
        if not path.is_file():
            ledger_failures.append(f"missing:{relative_path}")
            continue
        if _sha256(path) != record.get("sha256"):
            ledger_failures.append(f"sha256:{relative_path}")
        if path.stat().st_size != record.get("bytes"):
            ledger_failures.append(f"bytes:{relative_path}")

    endpoint_count = len(endpoint_summaries)
    all_keys = all(key.endswith("__T128__D0") for key in endpoint_summaries)
    dynamic_entries = [
        name
        for name in hash_ledger.get("files", {})
        if name.startswith("selected_dynamic_holdouts/") and name.endswith(".npz")
    ]
    all_finite = _finite_json(pass_summary) and _finite_json(endpoint_summaries)
    passed = bool(
        all(item["pass"] for item in hashes.values())
        and not ledger_failures
        and len(hash_ledger.get("files", {})) == EXPECTED_T128_LEDGER_ENTRY_COUNT
        and len(dynamic_entries) == EXPECTED_T128_DYNAMIC_NPZ_COUNT
        and pass_summary.get("decision") == "T128_STAGE_PASS_V04"
        and endpoint_count == 54
        and all_keys
        and all_finite
    )
    if not passed:
        raise ValueError("the frozen T128 source result failed its v05 provenance lock")
    return {
        "schema": "paper2_m2a_v05_source_t128_lock_v01",
        "hashes": hashes,
        "hash_ledger_entries": len(hash_ledger["files"]),
        "hash_ledger_failures": ledger_failures,
        "source_decision": pass_summary["decision"],
        "endpoint_count": endpoint_count,
        "all_keys_T128_D0": all_keys,
        "selected_dynamic_holdout_npz": len(dynamic_entries),
        "json_finite": all_finite,
        "pass": True,
    }


FROZEN_PROTOCOL_V05 = M2AV05Protocol().checked()

