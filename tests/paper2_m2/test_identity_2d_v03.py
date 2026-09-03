from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest
import scipy.sparse as sparse

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.identity_2d import build_system_for_level, simulate_endpoint
from paper2_m2.identity_2d_v03 import (
    DYNAMIC_HOLDOUT_CASES,
    discrete_material_energy_increment,
    endpoint_key,
    endpoint_structural_gate,
    metrics_for_case,
    t64_numerical_gate,
    upgrade_endpoint_v03,
)
from paper2_m2.protocol_v03 import (
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    FROZEN_PROTOCOL_V03,
)


@dataclass
class _SyntheticEnergySystem:
    matrix_material: sparse.csr_matrix
    active_vector_h: np.ndarray
    active_scalar_c: float


def test_exact_discrete_increment_matches_quadratic_bilinear_energy() -> None:
    matrix = sparse.csr_matrix(np.asarray([[3.0, -0.4], [-0.4, 2.0]]))
    system = _SyntheticEnergySystem(
        matrix_material=matrix,
        active_vector_h=np.asarray([0.7, -0.2]),
        active_scalar_c=1.3,
    )
    state_start = np.asarray([0.8, -0.1])
    state_end = np.asarray([-0.3, 0.9])
    activation_start = 0.11
    activation_end = 0.37

    def energy(state: np.ndarray, activation: float) -> float:
        return float(
            0.5 * state @ (matrix @ state)
            + activation * np.dot(system.active_vector_h, state)
            + 0.5 * system.active_scalar_c * activation**2
        )

    expected = energy(state_end, activation_end) - energy(
        state_start, activation_start
    )
    actual = discrete_material_energy_increment(
        system,
        state_start,
        state_end,
        activation_start,
        activation_end,
    )
    assert actual == pytest.approx(expected, rel=0.0, abs=5.0e-16)


def test_real_s4_regression_reproduces_old_failure_and_repairs_new_ledger() -> None:
    system = build_system_for_level(
        representation="DCM",
        level=FROZEN_PROTOCOL_V03.spatial("S4"),
        passive_dcm_scale=EXPECTED_DCM_PASSIVE_SCALE,
        active_dcm_scale=EXPECTED_DCM_ACTIVE_SCALE,
        active_profile="uniform",
    )
    legacy = simulate_endpoint(
        system=system,
        case_id="ID-LN",
        steps_per_cycle=64,
        tolerance_label="C0",
    )
    assert legacy.summary["ledger"]["maximum_normalized_residual"] == pytest.approx(
        1.465114585633258e-07, rel=0.0, abs=1.0e-18
    )
    assert legacy.summary["ledger"]["maximum_normalized_residual"] > 1.0e-8

    repaired = upgrade_endpoint_v03(
        system=system,
        case_id="ID-LN",
        steps_per_cycle=64,
        legacy_endpoint=legacy,
    )
    nonledger_arrays = (
        "time_two_cycles",
        "activation_two_cycles",
        "limited_shortening_two_cycles",
        "free_shortening_two_cycles",
        "mean_endocardial_tangential_displacement_two_cycles",
        "mean_endocardial_normal_displacement_two_cycles",
        "state_two_cycles",
        "myocardium_ecm_traction_two_cycles",
        "endocardium_ecm_traction_two_cycles",
        "ecm_cell_centroids",
        "ecm_strain_at_peak",
        "ecm_internal_z_at_peak",
        "ecm_stress_at_peak",
    )
    for name in nonledger_arrays:
        assert np.array_equal(repaired.arrays[name], legacy.arrays[name])
    assert repaired.summary["ledger"]["maximum_normalized_residual"] <= 1.0e-8
    assert (
        repaired.summary["ledger"][
            "maximum_ledger_minus_equilibrium_work_relative"
        ]
        <= 1.0e-10
    )
    assert endpoint_structural_gate(repaired.summary)["pass"] is True


def _synthetic_summaries() -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    level_scale = {"S2": 1.0, "S3": 1.004, "S4": 1.006}
    for case_id in FROZEN_CONFIG.cases:
        for representation in FROZEN_PROTOCOL_V03.representations:
            for spatial_label in ("S2", "S3", "S4"):
                value = level_scale[spatial_label]
                summary = {
                    "maximum_state_norm": 0.0 if case_id == "ID-P0" else value,
                    "passive_tangent": value,
                    "peak_limited_shortening": value,
                    "shortening_waveform_l2": value,
                    "myocardium_ecm_traction_l2": value,
                    "endocardium_ecm_traction_l2": value,
                    "ledger": {
                        "total_drag_dissipation": 0.4 * value,
                        "total_sls_dissipation": 0.6 * value,
                    },
                    "cycle_state_relative_difference": 0.0,
                    "hotspot_x": 0.0,
                    "v03_common_projection_sidecar": {
                        "available": spatial_label != "S2",
                        "values": {
                            "myocardium_ecm_traction_l2": value,
                            "endocardium_ecm_traction_l2": value,
                        },
                    },
                }
                summaries[
                    endpoint_key(case_id, representation, spatial_label)
                ] = summary
    return summaries


def test_v03_t64_gate_counts_the_54_distinct_d0_endpoints() -> None:
    result = t64_numerical_gate(_synthetic_summaries())
    assert result["pass"] is True
    assert result["counts"] == {
        "spatial": 74,
        "hotspot": 2,
        "cycle": 54,
        "spatial_pass": 74,
        "hotspot_pass": 2,
        "cycle_pass": 54,
    }
    assert len(DYNAMIC_HOLDOUT_CASES) == 6
    assert all("__D0" in key for key in _synthetic_summaries())
    assert metrics_for_case("ID-P0") == ("maximum_state_norm",)
    assert metrics_for_case("ID-P1") == ("passive_tangent",)
