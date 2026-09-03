from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paper2_m1.idealized_strip import (  # noqa: E402
    DriveProtocol,
    StripConfig,
    _energy_components,
    assemble_strip_system,
    run_case,
    run_validation_suite,
)


@pytest.fixture(scope="module")
def validation_suite():
    return run_validation_suite()


def test_energy_matrix_is_exactly_the_component_energy() -> None:
    system = assemble_strip_system(StripConfig(node_count=7))
    generator = np.random.default_rng(20260903)
    state = 0.01 * generator.standard_normal(system.state_size)
    activation = 0.07
    matrix_energy = float(
        0.5 * state @ system.matrix_a @ state
        + activation * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * activation**2
    )
    component_energy = float(
        sum(_energy_components(system, state, activation).values())
    )
    assert component_energy == pytest.approx(matrix_energy, abs=2.0e-16)


def test_zero_drive_and_separated_lumen_components(validation_suite) -> None:
    assert validation_suite["gates"]["zero_drive_equilibrium"]
    assert validation_suite["diagnostics"]["zero_state_norm"] == 0.0
    assert validation_suite["gates"]["normal_pressure_is_component_separated"]
    assert validation_suite["diagnostics"]["pressure_tangential_leak"] == 0.0
    assert validation_suite["gates"]["shear_is_component_separated"]
    assert validation_suite["diagnostics"]["shear_normal_leak"] == 0.0


def test_active_fem_identity_transfer_and_external_port(validation_suite) -> None:
    active = validation_suite["case_summaries"]["active_only"]
    external = validation_suite["case_summaries"]["external_port_only"]
    assert active["model_identity"] == (
        "endocardial_DCM__viscoelastic_ECM_FEM__active_myocardial_FEM"
    )
    assert active["peak_myocardial_shortening"] > 0.08
    assert active["peak_ecm_shortening"] > 0.01
    assert active["peak_endocardial_shortening"] > 0.005
    assert active["maximum_absolute_ecm_internal_z"] > 0.02
    assert active["maximum_absolute_endocardium_ecm_traction"] > 0.04
    assert active["integrated_work"]["active"] > 0.0
    assert external["integrated_work"]["external"] > 0.0
    assert "activation" in active["transfer"]
    assert (
        active["transfer"]["activation"]["responses"][
            "myocardial_shortening"
        ]["gain"]
        > 0.0
    )
    assert (
        active["transfer"]["activation"]["responses"][
            "endocardial_shortening"
        ]["gain"]
        > 0.0
    )


def test_action_reaction_power_and_passive_limit(validation_suite) -> None:
    assert validation_suite["status"] == "passed_m1_human_gate_candidate"
    assert validation_suite["gates"]["action_reaction"]
    assert validation_suite["gates"]["power_sign_and_ledger"]
    assert validation_suite["gates"]["interface_power"]
    assert validation_suite["gates"]["passive_limit_and_dissipation"]
    for summary in validation_suite["case_summaries"].values():
        assert summary["maximum_action_reaction_error"] <= 1.0e-12
        assert summary["maximum_absolute_step_ledger_residual"] <= 1.0e-11
        assert (
            summary["maximum_absolute_cycle_integrated_ledger_residual"]
            <= 1.0e-11
        )
        assert summary["maximum_absolute_interface_power_residual"] <= 1.0e-11
        assert summary["minimum_step_dissipation"] >= -1.0e-14


def test_instantaneous_power_ports_are_serialized() -> None:
    result = run_case(
        "combined_ports",
        config=StripConfig(cycles=1, steps_per_cycle=32),
        drive=DriveProtocol(
            activation_peak=0.05,
            pressure_peak=0.02,
            shear_amplitude=0.01,
            external_tangential_amplitude=0.01,
        ),
    )
    for name in (
        "power_lumen",
        "power_external",
        "power_active",
        "dissipation_power_ecm",
        "dissipation_power_endocardium",
        "dissipation_power_myocardium",
        "stored_energy_rate",
        "numerical_residual_power",
    ):
        assert name in result.arrays
        assert np.all(np.isfinite(result.arrays[name]))
    assert len(result.summary["cycle_ledgers"]) == 1


def test_deterministic_replay_and_bounded_sensitivity_screen(
    validation_suite,
) -> None:
    assert validation_suite["gates"]["deterministic_replay"]
    assert validation_suite["deterministic_replay_exact"]
    assert validation_suite["gates"]["time_sensitivity_screen"]
    assert validation_suite["gates"]["mesh_sensitivity_screen"]
    assert validation_suite["sensitivity"]["claim"] == (
        "finite_screen_only_not_formal_convergence"
    )


def test_invalid_activation_is_rejected() -> None:
    with pytest.raises(ValueError, match="activation_peak"):
        run_case("invalid", drive=DriveProtocol(activation_peak=1.0))
