"""Immutable M2A v03 protocol for the repaired T64 numerical gate."""

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
DIRECT_RELATIVE_RESIDUAL_TOLERANCE = 1.0e-7
DIRECT_BACKWARD_ERROR_TOLERANCE = 1.0e-12
DISCRETE_LEDGER_CLOSURE_TOLERANCE = 1.0e-10


@dataclass(frozen=True)
class M2AV03Protocol:
    schema: str = "paper2_m2a_protocol_v03"
    spatial_levels: tuple[SpatialLevel, ...] = (
        SpatialLevel("S2", 32, 8),
        SpatialLevel("S3", 64, 16),
        SpatialLevel("S4", 128, 32),
    )
    steps_per_cycle: int = 64
    solver_levels: tuple[str, ...] = ("D0",)
    representations: tuple[str, ...] = ("DCM", "FEM")
    common_projection_segments: int = 64
    pilot_runtime_budget_seconds: float = 900.0
    runtime_budget_seconds: float = 3600.0
    memory_budget_gib: float = 16.0
    cpu_processes: int = 1
    expected_pilot_endpoint_count: int = 3
    expected_endpoint_count: int = 54
    direct_relative_residual_tolerance: float = DIRECT_RELATIVE_RESIDUAL_TOLERANCE
    direct_backward_error_tolerance: float = DIRECT_BACKWARD_ERROR_TOLERANCE
    discrete_ledger_closure_tolerance: float = DISCRETE_LEDGER_CLOSURE_TOLERANCE
    source_config_digest: str = EXPECTED_V01_CONFIG_DIGEST
    dcm_passive_scale: float = EXPECTED_DCM_PASSIVE_SCALE
    dcm_active_scale: float = EXPECTED_DCM_ACTIVE_SCALE

    def checked(self) -> "M2AV03Protocol":
        if FROZEN_CONFIG.digest() != EXPECTED_V01_CONFIG_DIGEST:
            raise ValueError("the frozen v01 configuration digest changed")
        if tuple(level.label for level in self.spatial_levels) != ("S2", "S3", "S4"):
            raise ValueError("the v03 production ladder must be S2/S3/S4")
        if tuple((level.nx, level.ny_per_layer) for level in self.spatial_levels) != (
            (32, 8),
            (64, 16),
            (128, 32),
        ):
            raise ValueError("the v03 nested spatial ladder changed")
        if self.steps_per_cycle != 64:
            raise ValueError("the current v03 stage is T64 only")
        if self.solver_levels != ("D0",):
            raise ValueError("v03 has exactly one operational direct-solver level D0")
        if self.representations != ("DCM", "FEM"):
            raise ValueError("both myocardium representations are required")
        expected = (
            len(FROZEN_CONFIG.cases)
            * len(self.representations)
            * len(self.spatial_levels)
            * len(self.solver_levels)
        )
        if expected != self.expected_endpoint_count:
            raise ValueError("the v03 T64 endpoint count must remain 54")
        if self.expected_pilot_endpoint_count != len(self.spatial_levels):
            raise ValueError("the clarified v03 repair pilot must contain three endpoints")
        if self.common_projection_segments != 64:
            raise ValueError("the diagnostic projection must remain on 64 segments")
        return self

    def spatial(self, label: str) -> SpatialLevel:
        return next(level for level in self.checked().spatial_levels if level.label == label)

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self.checked())
        payload["cases"] = list(FROZEN_CONFIG.cases)
        payload["pilot_matrix"] = {
            "cases": ["ID-LN"],
            "representations": ["DCM"],
            "spatial_levels": ["S2", "S3", "S4"],
            "steps_per_cycle": 64,
            "solver_levels": ["D0"],
            "endpoint_count": 3,
            "contract_clarification_applied": True,
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
        "schema": "paper2_m2a_v03_source_calibration_lock_v01",
        "checks": checks,
        "pass": True,
    }


FROZEN_PROTOCOL_V03 = M2AV03Protocol().checked()
