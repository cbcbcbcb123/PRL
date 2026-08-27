from __future__ import annotations

import numpy as np

from route_h.distributed_active_dynamics import (
    run_dynamic_active_cycles,
    smooth_periodic_activation,
)


def test_smooth_periodic_activation_nodes_and_derivative() -> None:
    peak = 0.2
    period = 1.5
    assert smooth_periodic_activation(
        0.0,
        period=period,
        peak_activation=peak,
    ) == (0.0, 0.0)
    midpoint = smooth_periodic_activation(
        0.5 * period,
        period=period,
        peak_activation=peak,
    )
    assert midpoint == (peak, 0.0)
    endpoint = smooth_periodic_activation(
        period,
        period=period,
        peak_activation=peak,
    )
    assert endpoint == (0.0, 0.0)

    time = 0.31 * period
    epsilon = 1.0e-7
    plus = smooth_periodic_activation(
        time + epsilon,
        period=period,
        peak_activation=peak,
    )[0]
    minus = smooth_periodic_activation(
        time - epsilon,
        period=period,
        peak_activation=peak,
    )[0]
    analytic = smooth_periodic_activation(
        time,
        period=period,
        peak_activation=peak,
    )[1]
    assert np.isclose(
        analytic,
        (plus - minus) / (2.0 * epsilon),
        rtol=2.0e-8,
        atol=2.0e-10,
    )


def test_dynamic_cycle_has_exact_volume_and_nonnegative_dissipation() -> None:
    run = run_dynamic_active_cycles(
        period=1.0,
        cycle_count=1,
        steps_per_cycle=4,
        drag=1.0,
        peak_activation=0.02,
        fiber_stiffness=10.0,
    )
    assert run.status == "completed"
    assert run.time_integrator == "backward_euler"
    assert run.external_elastic_ratio == 0.0
    assert run.external_viscous_ratio == 0.0
    assert all(sample.external_elastic_energy == 0.0 for sample in run.samples)
    assert all(
        sample.external_viscous_dissipation_rate == 0.0
        for sample in run.samples
    )
    assert len(run.samples) == 5
    assert max(abs(sample.volume_ratio - 1.0) for sample in run.samples) < 1.0e-8
    assert min(sample.dissipation_rate for sample in run.samples) >= 0.0
    assert min(
        sample.algorithmic_dissipation_step for sample in run.samples
    ) >= -1.0e-10
    assert min(
        sample.numerical_dissipation_step for sample in run.samples
    ) >= -1.0e-8
    assert max(sample.measured_anchor_shortening for sample in run.samples) > 0.0
    assert max(sample.dynamic_kkt_residual for sample in run.samples) < 1.0e-5
    assert all(sample.optimizer_success for sample in run.samples)
    final = run.samples[-1]
    exact_balance = (
        final.stored_energy
        - run.samples[0].stored_energy
        + final.cumulative_algorithmic_dissipation
        - final.cumulative_active_work
    )
    assert abs(exact_balance) < 1.0e-10


def test_crank_nicolson_cycle_preserves_constraints_and_reduces_defect() -> None:
    run = run_dynamic_active_cycles(
        period=1.0,
        cycle_count=1,
        steps_per_cycle=4,
        time_integrator="crank_nicolson",
        drag=1.0,
        peak_activation=0.02,
        fiber_stiffness=10.0,
    )
    assert run.status == "completed"
    assert run.time_integrator == "crank_nicolson"
    assert len(run.samples) == 5
    assert max(abs(sample.volume_ratio - 1.0) for sample in run.samples) < 1.0e-8
    assert min(sample.dissipation_rate for sample in run.samples) >= 0.0
    assert max(sample.dynamic_kkt_residual for sample in run.samples) < 1.0e-5
    assert all(sample.optimizer_success for sample in run.samples)

    final = run.samples[-1]
    absolute_step_defect = sum(
        abs(sample.balance_residual_step) for sample in run.samples
    )
    assert abs(final.balance_residual_cumulative) < 1.0e-5
    assert absolute_step_defect < 1.0e-4


def test_crank_nicolson_advances_continuously_across_two_cycles() -> None:
    run = run_dynamic_active_cycles(
        period=1.0,
        cycle_count=2,
        steps_per_cycle=4,
        time_integrator="crank_nicolson",
        drag=1.0,
        peak_activation=0.02,
        fiber_stiffness=10.0,
    )
    assert run.status == "completed"
    assert len(run.samples) == 9
    assert run.samples[4].time == 1.0
    assert run.samples[4].activation == 0.0
    assert run.samples[8].time == 2.0
    assert run.samples[8].activation == 0.0
    assert max(abs(sample.volume_ratio - 1.0) for sample in run.samples) < 1.0e-8
    assert all(sample.optimizer_success for sample in run.samples)


def test_axial_environment_load_has_consistent_force_and_dissipation() -> None:
    run = run_dynamic_active_cycles(
        period=1.0,
        cycle_count=1,
        steps_per_cycle=4,
        time_integrator="crank_nicolson",
        drag=1.0,
        peak_activation=0.02,
        fiber_stiffness=10.0,
        external_elastic_ratio=1.0,
        external_viscous_ratio=1.0,
    )
    assert run.status == "completed"
    assert run.external_elastic_stiffness > 0.0
    assert run.external_viscous_coefficient > 0.0
    assert min(sample.external_elastic_energy for sample in run.samples) >= 0.0
    assert min(
        sample.external_viscous_dissipation_rate for sample in run.samples
    ) >= 0.0

    viscous_forces = []
    time_step = run.period / run.steps_per_cycle
    for previous, sample in zip(run.samples[:-1], run.samples[1:], strict=True):
        axial_velocity = (
            sample.axial_load_coordinate - previous.axial_load_coordinate
        ) / time_step
        expected_viscous_force = -run.external_viscous_coefficient * axial_velocity
        expected_viscous_dissipation = (
            run.external_viscous_coefficient * axial_velocity * axial_velocity
        )
        assert np.isclose(
            sample.external_viscous_resisting_force,
            expected_viscous_force,
            rtol=1.0e-12,
            atol=1.0e-14,
        )
        assert np.isclose(
            sample.external_viscous_dissipation_rate,
            expected_viscous_dissipation,
            rtol=1.0e-12,
            atol=1.0e-14,
        )
        assert sample.external_elastic_resisting_force >= -1.0e-12
        viscous_forces.append(sample.external_viscous_resisting_force)

    assert max(viscous_forces) > 0.0
    assert min(viscous_forces) < 0.0
    final = run.samples[-1]
    absolute_step_defect = sum(
        abs(sample.balance_residual_step) for sample in run.samples
    )
    assert abs(final.balance_residual_cumulative) < 1.0e-5
    assert absolute_step_defect < 1.0e-4
