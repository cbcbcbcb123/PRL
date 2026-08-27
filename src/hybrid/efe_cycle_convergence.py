"""Cycle- and time-convergence observables for EFE Node 1 N1-2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class AitkenRelaxation:
    """One bounded vector-Aitken relaxation decision."""

    factor: float
    unconstrained_factor: float | None
    clipped: bool
    residual_growth_safeguard: bool
    degenerate_fallback: bool


def safeguarded_vector_aitken_factor(
    previous_residual: FloatArray,
    current_residual: FloatArray,
    previous_factor: float,
    *,
    minimum_factor: float = 0.1,
    maximum_factor: float = 1.0,
) -> AitkenRelaxation:
    """Return a bounded scalar Aitken factor for a vector fixed point.

    The residuals are the unrelaxed map differences ``G(x) - x``.  A
    residual increase limits the next factor to at most half the previous
    factor.  Degenerate residual differences retain the previous bounded
    factor.
    """
    previous = np.asarray(previous_residual, dtype=np.float64)
    current = np.asarray(current_residual, dtype=np.float64)
    if previous.shape != current.shape or previous.size == 0:
        raise ValueError("Aitken residuals must have equal nonempty shapes")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(current)):
        raise ValueError("Aitken residuals must be finite")
    if not np.isfinite(previous_factor) or previous_factor <= 0.0:
        raise ValueError("previous Aitken factor must be finite and positive")
    if not (
        np.isfinite(minimum_factor)
        and np.isfinite(maximum_factor)
        and 0.0 < minimum_factor <= maximum_factor <= 1.0
    ):
        raise ValueError("Aitken factor bounds must satisfy 0 < min <= max <= 1")

    bounded_previous = float(
        np.clip(previous_factor, minimum_factor, maximum_factor)
    )
    difference = current - previous
    denominator = float(np.dot(difference.ravel(), difference.ravel()))
    scale = max(
        1.0,
        float(np.dot(previous.ravel(), previous.ravel())),
        float(np.dot(current.ravel(), current.ravel())),
    )
    if denominator <= np.finfo(np.float64).eps * scale:
        return AitkenRelaxation(
            factor=bounded_previous,
            unconstrained_factor=None,
            clipped=bounded_previous != previous_factor,
            residual_growth_safeguard=False,
            degenerate_fallback=True,
        )

    unconstrained = -bounded_previous * float(
        np.dot(previous.ravel(), difference.ravel())
    ) / denominator
    bounded = float(np.clip(unconstrained, minimum_factor, maximum_factor))
    residual_grew = bool(np.linalg.norm(current) > np.linalg.norm(previous))
    if residual_grew:
        bounded = min(
            bounded,
            max(minimum_factor, 0.5 * bounded_previous),
        )
    return AitkenRelaxation(
        factor=bounded,
        unconstrained_factor=unconstrained,
        clipped=not np.isclose(bounded, unconstrained, rtol=0.0, atol=0.0),
        residual_growth_safeguard=residual_grew,
        degenerate_fallback=False,
    )


def project_symmetric_traceless(tensors: FloatArray) -> FloatArray:
    """Project one or more 3x3 tensors to the symmetric traceless subspace."""
    array = np.asarray(tensors, dtype=np.float64)
    if array.ndim < 2 or array.shape[-2:] != (3, 3):
        raise ValueError("internal tensors must end in a 3x3 shape")
    if not np.all(np.isfinite(array)):
        raise ValueError("internal tensors must be finite")
    symmetric = 0.5 * (array + np.swapaxes(array, -1, -2))
    traces = np.trace(symmetric, axis1=-2, axis2=-1)
    return symmetric - (traces / 3.0)[..., None, None] * np.eye(3)


def relax_symmetric_traceless_internal_state(
    current: FloatArray,
    raw_update: FloatArray,
    factor: float,
) -> FloatArray:
    """Under-relax a tensor state without changing its admissible subspace."""
    current_array = np.asarray(current, dtype=np.float64)
    raw_array = np.asarray(raw_update, dtype=np.float64)
    if current_array.shape != raw_array.shape:
        raise ValueError("current and raw internal states must have equal shapes")
    if not np.isfinite(factor) or not 0.0 <= factor <= 1.0:
        raise ValueError("relaxation factor must lie in [0, 1]")
    relaxed = current_array + factor * (raw_array - current_array)
    return project_symmetric_traceless(relaxed)


def normalized_l2_difference(first: FloatArray, second: FloatArray) -> float:
    """Return the symmetric normalized Euclidean waveform difference."""
    first_array = np.asarray(first, dtype=np.float64)
    second_array = np.asarray(second, dtype=np.float64)
    if first_array.shape != second_array.shape:
        raise ValueError("waveforms must have identical shapes")
    if not np.all(np.isfinite(first_array)) or not np.all(
        np.isfinite(second_array)
    ):
        raise ValueError("waveforms must be finite")
    scale = max(
        1.0e-12,
        float(np.linalg.norm(first_array)),
        float(np.linalg.norm(second_array)),
    )
    return float(np.linalg.norm(first_array - second_array) / scale)


def periodic_linear_resample(
    phases: FloatArray,
    values: FloatArray,
    target_phases: FloatArray,
) -> FloatArray:
    """Linearly resample one closed-cycle waveform on ``[0, 1]``."""
    phase_array = np.asarray(phases, dtype=np.float64)
    value_array = np.asarray(values, dtype=np.float64)
    target_array = np.asarray(target_phases, dtype=np.float64)
    if phase_array.ndim != 1 or value_array.ndim != 1:
        raise ValueError("phases and values must be one-dimensional")
    if phase_array.shape != value_array.shape or len(phase_array) < 2:
        raise ValueError("phases and values must have equal nontrivial length")
    if not np.all(np.isfinite(phase_array)) or not np.all(
        np.isfinite(value_array)
    ):
        raise ValueError("phases and values must be finite")
    if np.any(np.diff(phase_array) <= 0.0):
        raise ValueError("phases must be strictly increasing")
    if phase_array[0] < -1.0e-12 or phase_array[-1] > 1.0 + 1.0e-12:
        raise ValueError("source phases must lie in [0, 1]")
    if np.any(target_array < 0.0) or np.any(target_array > 1.0):
        raise ValueError("target phases must lie in [0, 1]")
    return np.interp(target_array, phase_array, value_array)


def waveform_differences(
    first_samples: Sequence[Mapping[str, float]],
    second_samples: Sequence[Mapping[str, float]],
    signal_names: Sequence[str],
    *,
    resample_count: int = 4097,
) -> dict[str, float]:
    """Compare two cycles after a shared deterministic phase interpolation."""
    if resample_count < 3:
        raise ValueError("resample_count must be at least three")
    target = np.linspace(0.0, 1.0, resample_count, dtype=np.float64)

    def sampled(
        samples: Sequence[Mapping[str, float]], signal_name: str
    ) -> FloatArray:
        phases = np.asarray(
            [float(sample["t_over_T"]) for sample in samples],
            dtype=np.float64,
        )
        values = np.asarray(
            [float(sample[signal_name]) for sample in samples],
            dtype=np.float64,
        )
        return periodic_linear_resample(phases, values, target)

    return {
        signal_name: normalized_l2_difference(
            sampled(first_samples, signal_name),
            sampled(second_samples, signal_name),
        )
        for signal_name in signal_names
    }


def dense_peak_phase(
    samples: Sequence[Mapping[str, float]],
    signal_name: str,
    *,
    resample_count: int = 4097,
) -> float:
    """Locate a waveform maximum using the frozen dense-linear rule."""
    target = np.linspace(0.0, 1.0, resample_count, dtype=np.float64)
    phases = np.asarray(
        [float(sample["t_over_T"]) for sample in samples], dtype=np.float64
    )
    values = np.asarray(
        [float(sample[signal_name]) for sample in samples], dtype=np.float64
    )
    dense_values = periodic_linear_resample(phases, values, target)
    return float(target[int(np.argmax(dense_values))])


def cycle_integral(
    samples: Sequence[Mapping[str, float]], signal_name: str
) -> float:
    phases = np.asarray(
        [float(sample["t_over_T"]) for sample in samples], dtype=np.float64
    )
    values = np.asarray(
        [float(sample[signal_name]) for sample in samples], dtype=np.float64
    )
    if np.any(np.diff(phases) <= 0.0):
        raise ValueError("cycle phases must be strictly increasing")
    return float(np.trapezoid(values, phases))
