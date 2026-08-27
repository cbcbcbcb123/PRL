from __future__ import annotations

import numpy as np
import pytest

from hybrid.efe_time_refinement import (
    common_phase_field_differences,
    cycle_closure_ratio,
    dense_cycle_integral,
    dense_cycle_peak,
    dense_linear_cycle,
    dense_waveform_relative_difference,
    expected_two_cycle_transaction_count,
    observed_refinement_order,
    periodic_phase_distance,
    periodic_fixed_point_from_zero_cycle,
    resample_cycle_state_arrays,
    resample_uniform_cycle_history,
    richardson_extrapolation,
    rewrite_legacy_progress_denominator,
    step_for_registered_phase,
    uniform_cycle_phases,
    validate_steps_per_cycle,
)


def test_registered_phase_grids_and_sensitive_phase_mapping() -> None:
    assert len(uniform_cycle_phases(16)) == 17
    assert len(uniform_cycle_phases(32)) == 33
    assert len(uniform_cycle_phases(64)) == 65
    assert len(uniform_cycle_phases(128)) == 129
    assert step_for_registered_phase(0.25, 32) == 8
    assert step_for_registered_phase(0.6875, 32) == 22
    assert step_for_registered_phase(0.8125, 64) == 52
    assert step_for_registered_phase(0.875, 64) == 56
    with pytest.raises(ValueError):
        validate_steps_per_cycle(48)
    assert expected_two_cycle_transaction_count(128) == 256


def test_legacy_progress_denominator_uses_registered_runtime_level() -> None:
    message = "r5 cycle=01 step=44/16 pid=5"
    assert rewrite_legacy_progress_denominator(message, 64) == (
        "r5 cycle=01 step=44/64 pid=5"
    )
    assert rewrite_legacy_progress_denominator(message, 32) == (
        "r5 cycle=01 step=44/32 pid=5"
    )


def test_uniform_refinement_preserves_every_common_phase_exactly() -> None:
    source_phase = uniform_cycle_phases(16)
    history = np.column_stack(
        (
            source_phase,
            source_phase**2,
            np.sin(2.0 * np.pi * source_phase),
        )
    )
    refined = resample_uniform_cycle_history(
        history,
        target_steps_per_cycle=64,
    )
    assert refined.shape == (65, 3)
    assert np.array_equal(refined[::4], history)
    np.testing.assert_array_equal(refined[0], history[0])
    np.testing.assert_array_equal(refined[-1], history[-1])

    phase64 = uniform_cycle_phases(64)
    history64 = np.column_stack((phase64, np.cos(2.0 * np.pi * phase64)))
    refined128 = resample_uniform_cycle_history(
        history64,
        target_steps_per_cycle=128,
    )
    assert refined128.shape == (129, 2)
    assert np.array_equal(refined128[::2], history64)


def test_state_array_transfer_requires_one_shared_registered_history() -> None:
    phase = uniform_cycle_phases(16)
    arrays = {
        "variables": phase[:, None],
        "myocyte_vertices": phase[:, None, None],
        "ecm_vertices": (2.0 * phase)[:, None, None],
        "endocardial_vertices": (3.0 * phase)[:, None, None],
        "ecm_internal_z": phase[:, None, None, None],
    }
    transferred = resample_cycle_state_arrays(
        arrays,
        target_steps_per_cycle=32,
    )
    assert all(value.shape[0] == 33 for value in transferred.values())
    assert np.array_equal(transferred["variables"][::2], arrays["variables"])


def test_affine_cycle_fixed_point_closes_exactly() -> None:
    zero_end = np.asarray([1.0, -2.0, 0.5])
    decay = 0.6
    fixed = periodic_fixed_point_from_zero_cycle(zero_end, decay)
    np.testing.assert_allclose(decay * fixed + zero_end, fixed, atol=1.0e-15)


def test_observed_order_reports_quadratic_and_nonmonotone_cases() -> None:
    exact = 1.25
    result = observed_refinement_order(
        exact + 1.0 / 16.0**2,
        exact + 1.0 / 32.0**2,
        exact + 1.0 / 64.0**2,
    )
    assert result.status == "order_estimated"
    assert result.order == pytest.approx(2.0)

    nonmonotone = observed_refinement_order(1.0, 0.9, 0.95)
    assert nonmonotone.status == "nonmonotone_time_refinement"
    assert nonmonotone.order is None

    noise = observed_refinement_order(1.0, 1.0 + 1.0e-14, 1.0)
    assert noise.status == "order_not_identifiable"
    assert noise.order is None


def test_dense_cycle_rules_use_the_registered_4097_point_grid() -> None:
    phases = np.asarray([0.0, 0.5, 1.0])
    values = np.asarray([0.0, 1.0, 0.0])
    dense_phases, dense_values = dense_linear_cycle(phases, values)
    assert len(dense_phases) == 4097
    assert dense_phases[2048] == pytest.approx(0.5)
    assert dense_values[2048] == pytest.approx(1.0)
    assert dense_cycle_integral(phases, values) == pytest.approx(0.5)
    peak = dense_cycle_peak(phases, values)
    assert peak.value == pytest.approx(1.0)
    assert peak.phase == pytest.approx(0.5)
    assert dense_waveform_relative_difference(
        phases,
        values,
        phases,
        values,
    ) == 0.0


def test_periodic_peak_rule_canonicalizes_boundary_and_uses_circular_distance() -> None:
    phases = np.asarray([0.0, 0.5, 1.0])
    values = np.asarray([0.9, 0.0, 1.0])
    peak = dense_cycle_peak(phases, values)
    assert peak.phase == 0.0
    assert peak.status == "plateau_or_boundary_sensitive"
    assert periodic_phase_distance(0.984375, peak.phase) == pytest.approx(0.015625)
    assert periodic_phase_distance(0.9921875, peak.phase) == pytest.approx(
        0.0078125
    )


def test_cycle_closure_is_normalized_by_motion_amplitude() -> None:
    history = np.zeros((5, 2, 3), dtype=np.float64)
    history[1, :, 0] = 0.5
    history[2, :, 0] = 1.0
    history[3, :, 0] = 0.5
    history[4, :, 0] = 1.0e-4
    closure = cycle_closure_ratio(history)
    assert closure.status == "resolved"
    assert closure.cycle_amplitude == pytest.approx(1.0)
    assert closure.absolute_residual == pytest.approx(1.0e-4)
    assert closure.ratio == pytest.approx(1.0e-4)

    static = cycle_closure_ratio(np.zeros((3, 1, 3), dtype=np.float64))
    assert static.status == "closure_not_identifiable"
    assert static.ratio is None


def test_common_phase_field_comparison_uses_exact_registered_indices() -> None:
    phase16 = uniform_cycle_phases(16)
    phase64 = uniform_cycle_phases(64)
    first = np.column_stack((phase16, phase16**2))
    second = np.column_stack((phase64, phase64**2))
    differences = common_phase_field_differences(first, second)
    assert set(differences) == {"0.0000", "0.2500", "0.5000", "0.7500", "1.0000"}
    assert all(value == 0.0 for value in differences.values())


def test_richardson_extrapolation_is_guarded_by_order_status() -> None:
    exact = 1.25
    estimate = richardson_extrapolation(
        exact + 1.0 / 16.0**2,
        exact + 1.0 / 32.0**2,
        exact + 1.0 / 64.0**2,
    )
    assert estimate.status == "richardson_estimated"
    assert estimate.order == pytest.approx(2.0)
    assert estimate.extrapolated == pytest.approx(exact)

    nonmonotone = richardson_extrapolation(1.0, 0.9, 0.95)
    assert nonmonotone.status == "nonmonotone_time_refinement"
    assert nonmonotone.extrapolated is None

    unstable = richardson_extrapolation(1.0, 0.5, 0.499999999)
    assert unstable.status == "order_not_identifiable"
    assert unstable.extrapolated is None
