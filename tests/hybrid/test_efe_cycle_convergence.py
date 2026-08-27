from __future__ import annotations

import numpy as np
import pytest

from hybrid.efe_cycle_convergence import (
    cycle_integral,
    dense_peak_phase,
    normalized_l2_difference,
    periodic_linear_resample,
    relax_symmetric_traceless_internal_state,
    safeguarded_vector_aitken_factor,
    waveform_differences,
)


def test_normalized_l2_difference_is_symmetric_and_zero_for_identity() -> None:
    first = np.asarray([0.0, 1.0, 0.0])
    second = np.asarray([0.0, 0.9, 0.0])
    assert normalized_l2_difference(first, first) == pytest.approx(0.0)
    assert normalized_l2_difference(first, second) == pytest.approx(
        normalized_l2_difference(second, first)
    )


def test_periodic_linear_resample_rejects_nonmonotone_phase() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        periodic_linear_resample(
            np.asarray([0.0, 0.5, 0.5, 1.0]),
            np.asarray([0.0, 1.0, 1.0, 0.0]),
            np.linspace(0.0, 1.0, 9),
        )


def test_waveform_comparison_uses_a_common_phase_grid() -> None:
    coarse_phases = np.linspace(0.0, 1.0, 17)
    fine_phases = np.linspace(0.0, 1.0, 65)
    coarse = [
        {"t_over_T": phase, "response": np.sin(2.0 * np.pi * phase)}
        for phase in coarse_phases
    ]
    fine = [
        {"t_over_T": phase, "response": np.sin(2.0 * np.pi * phase)}
        for phase in fine_phases
    ]
    difference = waveform_differences(
        coarse, fine, ("response",), resample_count=1025
    )["response"]
    assert difference < 0.02


def test_peak_phase_and_integral_follow_frozen_interpolation_rule() -> None:
    phases = np.linspace(0.0, 1.0, 33)
    samples = [
        {
            "t_over_T": phase,
            "response": 0.5 * (1.0 - np.cos(2.0 * np.pi * phase)),
        }
        for phase in phases
    ]
    assert dense_peak_phase(samples, "response") == pytest.approx(
        0.5, abs=1.0 / 4096.0
    )
    assert cycle_integral(samples, "response") == pytest.approx(0.5)


def test_vector_aitken_factor_matches_alternating_scalar_secant() -> None:
    decision = safeguarded_vector_aitken_factor(
        np.asarray([1.0]),
        np.asarray([-0.5]),
        1.0,
    )
    assert decision.factor == pytest.approx(2.0 / 3.0)
    assert decision.unconstrained_factor == pytest.approx(2.0 / 3.0)
    assert not decision.clipped
    assert not decision.residual_growth_safeguard
    assert not decision.degenerate_fallback


def test_vector_aitken_factor_is_bounded_and_handles_degenerate_delta() -> None:
    clipped = safeguarded_vector_aitken_factor(
        np.asarray([1.0]),
        np.asarray([0.5]),
        1.0,
    )
    assert clipped.unconstrained_factor == pytest.approx(2.0)
    assert clipped.factor == pytest.approx(1.0)
    assert clipped.clipped

    degenerate = safeguarded_vector_aitken_factor(
        np.asarray([0.25, -0.25]),
        np.asarray([0.25, -0.25]),
        0.4,
    )
    assert degenerate.factor == pytest.approx(0.4)
    assert degenerate.degenerate_fallback


def test_relaxed_internal_state_is_symmetric_traceless() -> None:
    current = np.zeros((2, 3, 3), dtype=np.float64)
    raw = np.asarray(
        [
            [[2.0, 3.0, 0.0], [1.0, -1.0, 0.0], [0.0, 0.0, 4.0]],
            [[1.0, 0.0, 2.0], [0.0, 1.0, 0.0], [4.0, 0.0, 1.0]],
        ]
    )
    relaxed = relax_symmetric_traceless_internal_state(current, raw, 0.25)
    assert np.max(np.abs(relaxed - np.swapaxes(relaxed, 1, 2))) < 1.0e-15
    assert np.max(np.abs(np.trace(relaxed, axis1=1, axis2=2))) < 1.0e-15


def test_vector_aitken_rejects_nonfinite_residuals() -> None:
    with pytest.raises(ValueError, match="finite"):
        safeguarded_vector_aitken_factor(
            np.asarray([1.0]), np.asarray([np.nan]), 1.0
        )
