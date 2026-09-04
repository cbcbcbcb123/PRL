"""Frozen read-only DCM--FEM identity-gate protocol for Paper 2 M2A v06."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .config import FROZEN_CONFIG


@dataclass(frozen=True)
class IdentityGateProtocolV06:
    schema: str = "paper2_m2a_identity_gate_protocol_v06"
    spatial_level: str = "S4"
    steps_per_cycle: int = 256
    solver_level: str = "D0"
    common_projection_segments: int = 64
    combined_gain_operator_source: str = (
        "scripts/run_paper2_m2_identity_2d_v01.py:545-568"
    )
    combined_gain_operator_source_sha256: str = (
        "6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4"
    )
    representations: tuple[str, ...] = ("DCM", "FEM")
    structural_control_cases: tuple[str, ...] = ("ID-P0",)
    calibration_audit_only_cases: tuple[str, ...] = ("ID-P1", "ID-A1")
    holdout_cases: tuple[str, ...] = (
        "ID-A2",
        "ID-LN",
        "ID-LS",
        "ID-C0",
        "ID-CQ",
        "ID-S1",
    )
    shortening_relative_tolerance: float = 0.05
    waveform_relative_tolerance: float = 0.05
    traction_relative_tolerance: float = 0.05
    phase_absolute_tolerance_rad: float = 0.05
    dissipation_relative_tolerance: float = 0.10
    storage_absolute_tolerance: float = 1.0e-10
    combined_gain_relative_tolerance: float = 0.10
    no_go_relative_threshold: float = 0.15
    no_go_phase_threshold_rad: float = 0.15
    shortening_floor: float = 1.0e-6
    traction_floor: float = 1.0e-8
    energy_floor: float = 1.0e-10
    coherence_amplitude_floor: float = 1.0e-10
    hotspot_center_tolerance: float = 1.0 / 128.0
    hotspot_equivalence_relative_tolerance: float = 1.0e-12
    hotspot_equivalence_absolute_tolerance: float = 1.0e-12
    total_runtime_budget_seconds: float = 600.0
    peak_memory_budget_gib: float = 8.0
    cpu_processes: int = 1
    gpu_used: bool = False

    def checked(self) -> "IdentityGateProtocolV06":
        expected_cases = (
            "ID-P0",
            "ID-P1",
            "ID-A1",
            "ID-A2",
            "ID-LN",
            "ID-LS",
            "ID-C0",
            "ID-CQ",
            "ID-S1",
        )
        observed_cases = (
            self.structural_control_cases
            + self.calibration_audit_only_cases
            + self.holdout_cases
        )
        if observed_cases != expected_cases:
            raise ValueError("the frozen v06 case partition was changed")
        if self.representations != ("DCM", "FEM"):
            raise ValueError("the v06 comparison arms must remain DCM/FEM")
        if (self.spatial_level, self.steps_per_cycle, self.solver_level) != (
            "S4",
            256,
            "D0",
        ):
            raise ValueError("the frozen v06 endpoint was changed")
        if self.common_projection_segments != 64:
            raise ValueError("the frozen common interface must have 64 segments")
        if self.combined_gain_operator_source != (
            "scripts/run_paper2_m2_identity_2d_v01.py:545-568"
        ) or self.combined_gain_operator_source_sha256 != (
            "6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4"
        ):
            raise ValueError("the frozen v01 combined-load gain operator was changed")
        expected_thresholds = (
            FROZEN_CONFIG.identity_shortening_relative_tolerance,
            FROZEN_CONFIG.identity_waveform_relative_tolerance,
            FROZEN_CONFIG.identity_traction_relative_tolerance,
            FROZEN_CONFIG.identity_phase_absolute_tolerance_rad,
            FROZEN_CONFIG.identity_energy_relative_tolerance,
            FROZEN_CONFIG.identity_combined_gain_relative_tolerance,
            FROZEN_CONFIG.identity_no_go_relative_threshold,
            FROZEN_CONFIG.near_zero_shortening_absolute_scale,
            FROZEN_CONFIG.near_zero_traction_absolute_scale,
            FROZEN_CONFIG.near_zero_energy_absolute_scale,
            FROZEN_CONFIG.coherence_amplitude_floor,
        )
        observed_thresholds = (
            self.shortening_relative_tolerance,
            self.waveform_relative_tolerance,
            self.traction_relative_tolerance,
            self.phase_absolute_tolerance_rad,
            self.dissipation_relative_tolerance,
            self.combined_gain_relative_tolerance,
            self.no_go_relative_threshold,
            self.shortening_floor,
            self.traction_floor,
            self.energy_floor,
            self.coherence_amplitude_floor,
        )
        if observed_thresholds != expected_thresholds:
            raise ValueError("a frozen v01/v06 identity threshold was changed")
        if self.storage_absolute_tolerance != 1.0e-10:
            raise ValueError("the frozen storage absolute gate was changed")
        if self.hotspot_center_tolerance != 1.0 / 128.0:
            raise ValueError("the frozen hotspot-center gate was changed")
        if (
            self.total_runtime_budget_seconds != 600.0
            or self.peak_memory_budget_gib != 8.0
            or self.cpu_processes != 1
            or self.gpu_used
        ):
            raise ValueError("the frozen v06 resource boundary was changed")
        return self

    def phase_signal(self, case_id: str) -> str:
        if case_id == "ID-LN":
            return "negative_mean_endocardial_normal_displacement"
        if case_id == "ID-LS":
            return "mean_endocardial_tangential_displacement"
        if case_id in self.holdout_cases:
            return "limited_shortening"
        raise ValueError(f"phase signal is not defined for {case_id}")

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["phase_signal_by_case"] = {
            case_id: self.phase_signal(case_id) for case_id in self.holdout_cases
        }
        payload["first_cycle_window"] = [0, self.steps_per_cycle]
        payload["first_cycle_repeated_endpoint_included"] = False
        payload["identity_decisions"] = [
            "GO-ID",
            "MAYBE-ID",
            "NO-GO-ID",
            "BLOCKED",
        ]
        return payload


FROZEN_PROTOCOL_V06 = IdentityGateProtocolV06().checked()
