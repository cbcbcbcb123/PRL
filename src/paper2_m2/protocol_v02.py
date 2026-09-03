"""Immutable incremental protocol for the M2A v02 T64 numerical gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .config import FROZEN_CONFIG, SpatialLevel


EXPECTED_V01_CONFIG_DIGEST = (
    "431bf176833b975af26f6ac05810f6956f2d678dbe6da13f8c11e84d817f46f9"
)
EXPECTED_DCM_PASSIVE_SCALE = 2.4532573887517564
EXPECTED_DCM_ACTIVE_SCALE = 0.8891803904091895


@dataclass(frozen=True)
class M2AV02Protocol:
    schema: str = "paper2_m2a_protocol_v02"
    spatial_levels: tuple[SpatialLevel, ...] = (
        SpatialLevel("S2", 32, 8),
        SpatialLevel("S3", 64, 16),
        SpatialLevel("S4", 128, 32),
    )
    steps_per_cycle: int = 64
    tolerance_labels: tuple[str, ...] = ("C0", "C1")
    representations: tuple[str, ...] = ("DCM", "FEM")
    common_projection_segments: int = 64
    runtime_budget_seconds: float = 3600.0
    memory_budget_gib: float = 16.0
    cpu_processes: int = 1
    expected_endpoint_count: int = 108
    source_config_digest: str = EXPECTED_V01_CONFIG_DIGEST
    dcm_passive_scale: float = EXPECTED_DCM_PASSIVE_SCALE
    dcm_active_scale: float = EXPECTED_DCM_ACTIVE_SCALE

    def checked(self) -> "M2AV02Protocol":
        if FROZEN_CONFIG.digest() != EXPECTED_V01_CONFIG_DIGEST:
            raise ValueError("the frozen v01 configuration digest changed")
        if tuple(level.label for level in self.spatial_levels) != ("S2", "S3", "S4"):
            raise ValueError("the v02 production ladder must be S2/S3/S4")
        if tuple((level.nx, level.ny_per_layer) for level in self.spatial_levels) != (
            (32, 8),
            (64, 16),
            (128, 32),
        ):
            raise ValueError("the v02 nested spatial ladder changed")
        if self.steps_per_cycle != 64:
            raise ValueError("the current v02 stage is T64 only")
        if self.tolerance_labels != ("C0", "C1"):
            raise ValueError("both frozen solver tolerance profiles are required")
        if self.representations != ("DCM", "FEM"):
            raise ValueError("both myocardium representations are required")
        expected = (
            len(FROZEN_CONFIG.cases)
            * len(self.representations)
            * len(self.spatial_levels)
            * len(self.tolerance_labels)
        )
        if expected != self.expected_endpoint_count:
            raise ValueError("the v02 T64 endpoint count must remain 108")
        if self.common_projection_segments != 64:
            raise ValueError("the diagnostic projection must remain on 64 segments")
        return self

    def spatial(self, label: str) -> SpatialLevel:
        return next(level for level in self.checked().spatial_levels if level.label == label)

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self.checked())
        payload["cases"] = list(FROZEN_CONFIG.cases)
        payload["spatial_gate"] = {
            "production_observable": "native_nodal_or_spring_traction",
            "finest_pair": ["S3", "S4"],
            "relative_tolerance": FROZEN_CONFIG.spatial_endpoint_relative_tolerance,
            "direction_required": True,
            "hotspot_cell_width": FROZEN_CONFIG.length / self.spatial("S4").nx,
        }
        payload["solver_profile_gate"] = {
            "relative_tolerance": FROZEN_CONFIG.solver_profile_relative_tolerance
        }
        payload["cycle_gate"] = {
            "relative_tolerance": FROZEN_CONFIG.cycle_state_relative_tolerance
        }
        return payload

    def digest(self) -> str:
        serialized = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


def validate_source_calibration(payload: dict[str, Any]) -> dict[str, Any]:
    actual_digest = payload.get("config_digest")
    actual_passive = payload.get("passive", {}).get("dcm_passive_scale")
    actual_active = payload.get("active", {}).get("dcm_active_scale")
    checks = {
        "config_digest": {
            "expected": EXPECTED_V01_CONFIG_DIGEST,
            "actual": actual_digest,
            "pass": actual_digest == EXPECTED_V01_CONFIG_DIGEST,
        },
        "dcm_passive_scale": {
            "expected": EXPECTED_DCM_PASSIVE_SCALE,
            "actual": actual_passive,
            "pass": actual_passive == EXPECTED_DCM_PASSIVE_SCALE,
        },
        "dcm_active_scale": {
            "expected": EXPECTED_DCM_ACTIVE_SCALE,
            "actual": actual_active,
            "pass": actual_active == EXPECTED_DCM_ACTIVE_SCALE,
        },
    }
    if not all(check["pass"] for check in checks.values()):
        raise ValueError(f"v01 calibration is not byte-value compatible: {checks}")
    return {
        "schema": "paper2_m2a_v02_source_calibration_lock_v01",
        "checks": checks,
        "pass": True,
    }


FROZEN_PROTOCOL_V02 = M2AV02Protocol().checked()
