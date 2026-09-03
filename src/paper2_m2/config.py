"""Immutable configuration frozen after the M2A FEniCSx resource preflight."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Literal


SpatialLabel = Literal["S0", "S1", "S2"]
ToleranceLabel = Literal["C0", "C1"]
Representation = Literal["DCM", "FEM"]


@dataclass(frozen=True)
class SpatialLevel:
    label: SpatialLabel
    nx: int
    ny_per_layer: int


@dataclass(frozen=True)
class SolverToleranceProfile:
    label: ToleranceLabel
    coupling_tolerance: float
    maximum_coupling_iterations: int
    lbfgs_gtol: float
    newton_fatol: float
    follower_tolerance: float
    kkt_tolerance: float


@dataclass(frozen=True)
class M2AConfig:
    schema: str = "paper2_m2a_frozen_config_v01"
    length: float = 1.0
    myocardium_thickness: float = 0.20
    ecm_thickness: float = 0.30
    period: float = 1.0
    spatial_levels: tuple[SpatialLevel, ...] = (
        SpatialLevel("S0", 8, 2),
        SpatialLevel("S1", 16, 4),
        SpatialLevel("S2", 32, 8),
    )
    time_steps_per_cycle: tuple[int, ...] = (64, 128, 256)
    tolerance_profiles: tuple[SolverToleranceProfile, ...] = (
        SolverToleranceProfile("C0", 1.0e-4, 12, 2.0e-7, 1.0e-7, 1.0e-7, 1.0e-5),
        SolverToleranceProfile("C1", 1.0e-5, 24, 2.0e-8, 1.0e-8, 1.0e-8, 1.0e-6),
    )
    cases: tuple[str, ...] = (
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
    calibration_spatial_level: SpatialLabel = "S1"
    calibration_time_steps: int = 128
    calibration_tolerance: ToleranceLabel = "C1"
    activation_peak: float = 0.10
    normal_traction_peak: float = 0.08
    tangential_traction_peak: float = 0.05
    passive_perturbation_strain: float = 1.0e-4
    spatial_activation_contrast: float = 0.35
    myocardium_young_modulus: float = 2.5
    myocardium_poisson_ratio: float = 0.30
    ecm_equilibrium_young_modulus: float = 1.0
    ecm_equilibrium_poisson_ratio: float = 0.45
    ecm_maxwell_young_modulus: float = 0.7
    ecm_maxwell_poisson_ratio: float = 0.30
    ecm_relaxation_time: float = 0.22
    endocardial_axial_stiffness: float = 0.8
    endocardial_transverse_stiffness: float = 0.25
    endocardial_bending_stiffness: float = 0.02
    endocardium_ecm_interface_stiffness: float = 7.0
    ecm_myocardium_interface_stiffness: float = 8.0
    support_tangential_stiffness: float = 0.45
    support_normal_stiffness: float = 0.60
    endocardial_drag: float = 0.10
    ecm_drag: float = 0.05
    myocardium_drag: float = 0.12
    direct_solver: str = "scipy_superlu"
    endpoint_runtime_budget_seconds: float = 30.0
    matrix_runtime_budget_seconds: float = 7200.0
    memory_budget_gib: float = 16.0
    cpu_processes: int = 1
    mesh_diagonal: str = "lower_left_to_upper_right"
    x_boundary_condition: str = "affine_periodic_common_macro_strain"
    action_reaction_relative_tolerance: float = 1.0e-10
    power_ledger_relative_tolerance: float = 1.0e-8
    dissipation_lower_tolerance: float = -1.0e-12
    zero_state_absolute_tolerance: float = 1.0e-10
    manufactured_solution_relative_tolerance: float = 1.0e-6
    spatial_endpoint_relative_tolerance: float = 0.01
    solver_profile_relative_tolerance: float = 0.005
    cycle_state_relative_tolerance: float = 1.0e-3
    identity_shortening_relative_tolerance: float = 0.05
    identity_waveform_relative_tolerance: float = 0.05
    identity_traction_relative_tolerance: float = 0.05
    identity_phase_absolute_tolerance_rad: float = 0.05
    identity_energy_relative_tolerance: float = 0.10
    identity_combined_gain_relative_tolerance: float = 0.10
    identity_no_go_relative_threshold: float = 0.15
    near_zero_shortening_absolute_scale: float = 1.0e-6
    near_zero_traction_absolute_scale: float = 1.0e-8
    near_zero_energy_absolute_scale: float = 1.0e-10
    coherence_amplitude_floor: float = 1.0e-10
    calibration_quantities: tuple[str, ...] = (
        "ID-P1_passive_small_perturbation_tangent",
        "ID-A1_baseline_total_active_work",
    )
    held_out_quantities: tuple[str, ...] = (
        "shortening_waveform",
        "interface_traction_waveform",
        "fundamental_phase",
        "stored_energy_and_dissipation_partition",
        "combined_load_gain",
        "spatial_field_and_hotspot",
    )

    def checked(self) -> "M2AConfig":
        if tuple(level.label for level in self.spatial_levels) != ("S0", "S1", "S2"):
            raise ValueError("the spatial ladder must be S0/S1/S2")
        if tuple((level.nx, level.ny_per_layer) for level in self.spatial_levels) != (
            (8, 2),
            (16, 4),
            (32, 8),
        ):
            raise ValueError("the frozen nested mesh ladder was changed")
        if self.time_steps_per_cycle != (64, 128, 256):
            raise ValueError("the frozen time ladder was changed")
        if tuple(profile.label for profile in self.tolerance_profiles) != ("C0", "C1"):
            raise ValueError("both frozen tolerance profiles are required")
        if len(self.cases) != 9 or len(set(self.cases)) != 9:
            raise ValueError("exactly nine preregistered cases are required")
        positive = (
            self.length,
            self.myocardium_thickness,
            self.ecm_thickness,
            self.period,
            self.activation_peak,
            self.normal_traction_peak,
            self.tangential_traction_peak,
            self.passive_perturbation_strain,
            self.myocardium_young_modulus,
            self.ecm_equilibrium_young_modulus,
            self.ecm_maxwell_young_modulus,
            self.ecm_relaxation_time,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("frozen geometry, drive and material values must be positive")
        if not (0.0 < self.activation_peak < 1.0):
            raise ValueError("activation_peak must lie in (0, 1)")
        return self

    def spatial(self, label: SpatialLabel) -> SpatialLevel:
        return next(level for level in self.spatial_levels if level.label == label)

    def tolerance(self, label: ToleranceLabel) -> SolverToleranceProfile:
        return next(profile for profile in self.tolerance_profiles if profile.label == label)

    def canonical_payload(self) -> dict:
        return asdict(self.checked())

    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


FROZEN_CONFIG = M2AConfig().checked()
