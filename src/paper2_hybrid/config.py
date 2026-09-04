"""Immutable configuration for the active FEM-only myocardium architecture."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Literal


SpatialLabel = Literal["S2", "S3", "S4"]
ActiveProfile = Literal["uniform", "S1"]


@dataclass(frozen=True)
class SpatialLevel:
    label: SpatialLabel
    nx: int
    ny_per_layer: int


@dataclass(frozen=True)
class HybridConfig:
    schema: str = "paper2_hybrid_active_config_v08"
    length: float = 1.0
    myocardium_thickness: float = 0.20
    ecm_thickness: float = 0.30
    period: float = 1.0
    spatial_levels: tuple[SpatialLevel, ...] = (
        SpatialLevel("S2", 32, 8),
        SpatialLevel("S3", 64, 16),
        SpatialLevel("S4", 128, 32),
    )
    time_steps_per_cycle: tuple[int, ...] = (64, 128, 256)
    cases: tuple[str, ...] = (
        "P0",
        "P1",
        "A1",
        "A2",
        "LN",
        "LS",
        "C0",
        "CQ",
        "S1",
    )
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
    direct_relative_residual_tolerance: float = 1.0e-7
    direct_backward_error_tolerance: float = 1.0e-12
    discrete_ledger_closure_tolerance: float = 1.0e-10
    mesh_diagonal: str = "lower_left_to_upper_right"
    x_boundary_condition: str = "affine_periodic_common_macro_strain"
    action_reaction_relative_tolerance: float = 1.0e-10
    power_ledger_relative_tolerance: float = 1.0e-8
    dissipation_lower_tolerance: float = -1.0e-12
    zero_state_absolute_tolerance: float = 1.0e-10
    manufactured_solution_relative_tolerance: float = 1.0e-6
    cycle_state_relative_tolerance: float = 1.0e-3

    def checked(self) -> "HybridConfig":
        if tuple(level.label for level in self.spatial_levels) != ("S2", "S3", "S4"):
            raise ValueError("the active spatial ladder must be S2/S3/S4")
        if tuple((level.nx, level.ny_per_layer) for level in self.spatial_levels) != (
            (32, 8),
            (64, 16),
            (128, 32),
        ):
            raise ValueError("the active nested spatial ladder changed")
        if self.time_steps_per_cycle != (64, 128, 256):
            raise ValueError("the active time ladder changed")
        if self.cases != ("P0", "P1", "A1", "A2", "LN", "LS", "C0", "CQ", "S1"):
            raise ValueError("the nine active cases changed")
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
            raise ValueError("geometry, drive and material values must be positive")
        if not (0.0 < self.activation_peak < 1.0):
            raise ValueError("activation_peak must lie in (0, 1)")
        return self

    def spatial(self, label: SpatialLabel) -> SpatialLevel:
        return next(level for level in self.checked().spatial_levels if level.label == label)

    def canonical_payload(self) -> dict:
        return asdict(self.checked())

    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


ACTIVE_CONFIG = HybridConfig().checked()
