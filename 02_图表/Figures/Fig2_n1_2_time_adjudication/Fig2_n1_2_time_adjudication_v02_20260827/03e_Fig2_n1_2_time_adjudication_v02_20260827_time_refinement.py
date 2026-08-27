"""Auditable time-grid transfers and convergence diagnostics for EFE N1-2c."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Mapping

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
SUPPORTED_TIME_LEVELS = (16, 32, 64, 128)


def validate_steps_per_cycle(steps_per_cycle: int) -> int:
    """Return a registered time level or fail closed."""
    selected = int(steps_per_cycle)
    if selected not in SUPPORTED_TIME_LEVELS:
        raise ValueError(
            "steps_per_cycle must be one of "
            f"{SUPPORTED_TIME_LEVELS}, received {selected}"
        )
    return selected


def uniform_cycle_phases(steps_per_cycle: int) -> FloatArray:
    """Return the inclusive uniform phase grid for one registered level."""
    selected = validate_steps_per_cycle(steps_per_cycle)
    return np.linspace(0.0, 1.0, selected + 1, dtype=np.float64)


def step_for_registered_phase(phase: float, steps_per_cycle: int) -> int:
    """Map a phase exactly represented by a registered grid to its step."""
    selected = validate_steps_per_cycle(steps_per_cycle)
    phase_value = float(phase)
    if not math.isfinite(phase_value) or not 0.0 <= phase_value <= 1.0:
        raise ValueError("phase must be finite and lie in [0, 1]")
    raw_step = phase_value * selected
    rounded = int(round(raw_step))
    if not math.isclose(raw_step, rounded, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("phase is not represented exactly by this time level")
    return rounded


def rewrite_legacy_progress_denominator(
    message: str, steps_per_cycle: int
) -> str:
    """Correct the frozen R5 progress-only ``/16`` denominator at runtime."""
    selected = validate_steps_per_cycle(steps_per_cycle)
    return str(message).replace("/16 ", f"/{selected} ")


def symmetric_relative_difference(first: np.ndarray, second: np.ndarray) -> float:
    """Return a symmetric relative L2 difference with a fixed zero guard."""
    first_array = np.asarray(first, dtype=np.float64)
    second_array = np.asarray(second, dtype=np.float64)
    if first_array.shape != second_array.shape:
        raise ValueError("arrays must have identical shapes")
    if not np.all(np.isfinite(first_array)) or not np.all(
        np.isfinite(second_array)
    ):
        raise ValueError("arrays must contain only finite values")
    scale = max(
        1.0e-12,
        float(np.linalg.norm(first_array)),
        float(np.linalg.norm(second_array)),
    )
    return float(np.linalg.norm(first_array - second_array) / scale)


def resample_uniform_cycle_history(
    history: np.ndarray,
    *,
    target_steps_per_cycle: int,
) -> FloatArray:
    """Linearly transfer an inclusive uniform history to a finer registered grid.

    The source level is inferred from the leading dimension.  Only refinement
    between the registered 16/32/64/128 grids is allowed, and all source grid points
    are recovered bit-for-bit in the returned history.
    """
    source = np.asarray(history, dtype=np.float64)
    if source.ndim < 1 or source.shape[0] < 2:
        raise ValueError("history must have an inclusive phase dimension")
    if not np.all(np.isfinite(source)):
        raise ValueError("history must contain only finite values")
    source_steps = validate_steps_per_cycle(source.shape[0] - 1)
    target_steps = validate_steps_per_cycle(target_steps_per_cycle)
    if target_steps < source_steps or target_steps % source_steps != 0:
        raise ValueError("only integer registered time refinement is allowed")
    if target_steps == source_steps:
        return source.copy()

    target_index = np.arange(target_steps + 1, dtype=np.int64)
    scaled = target_index * source_steps / target_steps
    lower = np.floor(scaled).astype(np.int64)
    lower[-1] = source_steps - 1
    fraction = scaled - lower
    fraction[-1] = 1.0
    upper = lower + 1
    weight_shape = (target_steps + 1,) + (1,) * (source.ndim - 1)
    weights = fraction.reshape(weight_shape)
    result = (1.0 - weights) * source[lower] + weights * source[upper]

    stride = target_steps // source_steps
    if not np.array_equal(result[::stride], source):
        raise RuntimeError("refinement failed to preserve common source phases")
    return np.asarray(result, dtype=np.float64)


def resample_cycle_state_arrays(
    arrays: Mapping[str, np.ndarray],
    *,
    target_steps_per_cycle: int,
) -> dict[str, FloatArray]:
    """Transfer every registered state-history array to one finer time grid."""
    required = {
        "variables",
        "myocyte_vertices",
        "ecm_vertices",
        "endocardial_vertices",
        "ecm_internal_z",
    }
    missing = required.difference(arrays)
    if missing:
        raise ValueError(f"cycle state arrays are missing {sorted(missing)}")
    source_lengths = {np.asarray(arrays[name]).shape[0] for name in required}
    if len(source_lengths) != 1:
        raise ValueError("cycle histories do not share a phase dimension")
    return {
        name: resample_uniform_cycle_history(
            np.asarray(arrays[name], dtype=np.float64),
            target_steps_per_cycle=target_steps_per_cycle,
        )
        for name in sorted(required)
    }


def periodic_fixed_point_from_zero_cycle(
    zero_cycle_end: np.ndarray,
    cycle_decay: float,
) -> FloatArray:
    """Recover the fixed point of an affine one-cycle internal-state map."""
    zero_end = np.asarray(zero_cycle_end, dtype=np.float64)
    decay = float(cycle_decay)
    if not np.all(np.isfinite(zero_end)):
        raise ValueError("zero-cycle state must be finite")
    if not math.isfinite(decay) or not 0.0 <= decay < 1.0:
        raise ValueError("cycle decay must be finite and lie in [0, 1)")
    return np.asarray(zero_end / (1.0 - decay), dtype=np.float64)


def expected_two_cycle_transaction_count(steps_per_cycle: int) -> int:
    """Return the audited transaction count for two registered cycles."""
    return 2 * validate_steps_per_cycle(steps_per_cycle)


@dataclass(frozen=True)
class ObservedOrderResult:
    status: str
    order: float | None
    coarse_medium_difference: float
    medium_fine_difference: float


def observed_refinement_order(
    coarse: float,
    medium: float,
    fine: float,
    *,
    noise_floor: float = 1.0e-12,
) -> ObservedOrderResult:
    """Return a two-to-one observed order without inventing asymptotic behavior."""
    values = np.asarray([coarse, medium, fine], dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("refinement values must be finite")
    if not math.isfinite(noise_floor) or noise_floor <= 0.0:
        raise ValueError("noise_floor must be finite and positive")
    coarse_medium = float(abs(coarse - medium))
    medium_fine = float(abs(medium - fine))
    if max(coarse_medium, medium_fine) <= noise_floor:
        return ObservedOrderResult(
            "order_not_identifiable", None, coarse_medium, medium_fine
        )
    signed_first = coarse - medium
    signed_second = medium - fine
    if (
        abs(signed_first) <= noise_floor
        or abs(signed_second) <= noise_floor
        or signed_first * signed_second <= 0.0
        or coarse_medium <= medium_fine
    ):
        return ObservedOrderResult(
            "nonmonotone_time_refinement", None, coarse_medium, medium_fine
        )
    order = math.log2(coarse_medium / medium_fine)
    if not math.isfinite(order) or order <= 0.0:
        return ObservedOrderResult(
            "nonmonotone_time_refinement", None, coarse_medium, medium_fine
        )
    return ObservedOrderResult(
        "order_estimated", float(order), coarse_medium, medium_fine
    )


def _validated_scalar_cycle(
    phases: np.ndarray,
    values: np.ndarray,
) -> tuple[FloatArray, FloatArray]:
    selected_phases = np.asarray(phases, dtype=np.float64)
    selected_values = np.asarray(values, dtype=np.float64)
    if selected_phases.ndim != 1 or selected_values.ndim != 1:
        raise ValueError("phases and values must be one-dimensional")
    if selected_phases.shape != selected_values.shape:
        raise ValueError("phases and values must have identical shapes")
    if len(selected_phases) < 2:
        raise ValueError("a cycle must contain at least two samples")
    if not np.all(np.isfinite(selected_phases)) or not np.all(
        np.isfinite(selected_values)
    ):
        raise ValueError("cycle arrays must contain only finite values")
    if not math.isclose(float(selected_phases[0]), 0.0, abs_tol=1.0e-12):
        raise ValueError("cycle phases must start at zero")
    if not math.isclose(float(selected_phases[-1]), 1.0, abs_tol=1.0e-12):
        raise ValueError("cycle phases must end at one")
    if np.any(np.diff(selected_phases) <= 0.0):
        raise ValueError("cycle phases must be strictly increasing")
    return selected_phases, selected_values


def dense_linear_cycle(
    phases: np.ndarray,
    values: np.ndarray,
    *,
    sample_count: int = 4097,
) -> tuple[FloatArray, FloatArray]:
    """Interpolate one scalar cycle on the frozen inclusive dense grid."""
    selected_phases, selected_values = _validated_scalar_cycle(phases, values)
    if sample_count < 2:
        raise ValueError("sample_count must be at least two")
    dense_phases = np.linspace(0.0, 1.0, sample_count, dtype=np.float64)
    dense_values = np.interp(dense_phases, selected_phases, selected_values)
    return dense_phases, np.asarray(dense_values, dtype=np.float64)


def dense_waveform_relative_difference(
    first_phases: np.ndarray,
    first_values: np.ndarray,
    second_phases: np.ndarray,
    second_values: np.ndarray,
    *,
    sample_count: int = 4097,
) -> float:
    """Compare scalar waveforms on the registered common dense grid."""
    first_grid, first_dense = dense_linear_cycle(
        first_phases,
        first_values,
        sample_count=sample_count,
    )
    second_grid, second_dense = dense_linear_cycle(
        second_phases,
        second_values,
        sample_count=sample_count,
    )
    if not np.array_equal(first_grid, second_grid):
        raise RuntimeError("dense waveform grids are not identical")
    return symmetric_relative_difference(first_dense, second_dense)


def dense_cycle_integral(
    phases: np.ndarray,
    values: np.ndarray,
    *,
    sample_count: int = 4097,
) -> float:
    """Integrate one cycle using the frozen dense-linear trapezoid rule."""
    dense_phases, dense_values = dense_linear_cycle(
        phases,
        values,
        sample_count=sample_count,
    )
    return float(np.trapezoid(dense_values, dense_phases))


@dataclass(frozen=True)
class DensePeakResult:
    value: float
    phase: float
    status: str = "resolved"
    candidate_count: int = 1


def periodic_phase_distance(first: float, second: float) -> float:
    """Return the shortest distance between two phases on a unit cycle."""
    values = np.asarray([first, second], dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("phases must be finite")
    normalized = np.mod(values, 1.0)
    direct = float(abs(normalized[0] - normalized[1]))
    return min(direct, 1.0 - direct)


def dense_cycle_peak(
    phases: np.ndarray,
    values: np.ndarray,
    *,
    mode: Literal["max", "min", "absolute"] = "max",
    sample_count: int = 4097,
) -> DensePeakResult:
    """Locate one deterministic dense-linear peak and its phase."""
    dense_phases, dense_values = dense_linear_cycle(
        phases,
        values,
        sample_count=sample_count,
    )
    if mode == "max":
        objective = dense_values
    elif mode == "min":
        objective = -dense_values
    elif mode == "absolute":
        objective = np.abs(dense_values)
    else:
        raise ValueError("mode must be max, min, or absolute")
    peak_objective = float(np.max(objective))
    tolerance = 8.0 * np.finfo(np.float64).eps * max(1.0, abs(peak_objective))
    candidates = np.flatnonzero(
        np.isclose(objective, peak_objective, rtol=0.0, atol=tolerance)
    )
    index = int(candidates[0])
    raw_phase = float(dense_phases[index])
    canonical_phase = 0.0 if math.isclose(raw_phase, 1.0) else raw_phase
    sensitive = bool(
        len(candidates) > 1
        or index == 0
        or index == len(dense_phases) - 1
    )
    return DensePeakResult(
        value=float(dense_values[index]),
        phase=canonical_phase,
        status="plateau_or_boundary_sensitive" if sensitive else "resolved",
        candidate_count=int(len(candidates)),
    )


@dataclass(frozen=True)
class CycleClosureResult:
    status: str
    ratio: float | None
    absolute_residual: float
    cycle_amplitude: float


def cycle_closure_ratio(
    displacement_history: np.ndarray,
    *,
    amplitude_floor: float = 1.0e-12,
    percentile: float = 95.0,
) -> CycleClosureResult:
    """Normalize phase-one displacement closure by the cycle displacement scale."""
    history = np.asarray(displacement_history, dtype=np.float64)
    if history.ndim < 2 or history.shape[0] < 2:
        raise ValueError("displacement history must include phase and spatial axes")
    if history.shape[-1] != 3:
        raise ValueError("the final displacement axis must have three components")
    if not np.all(np.isfinite(history)):
        raise ValueError("displacement history must contain only finite values")
    if not math.isfinite(amplitude_floor) or amplitude_floor <= 0.0:
        raise ValueError("amplitude_floor must be finite and positive")
    if not math.isfinite(percentile) or not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must lie in [0, 100]")

    relative = history - history[0]
    magnitude = np.linalg.norm(relative, axis=-1)
    phase_scale = np.percentile(
        magnitude.reshape(history.shape[0], -1), percentile, axis=1
    )
    absolute_residual = float(phase_scale[-1])
    cycle_amplitude = float(np.max(phase_scale))
    if cycle_amplitude < amplitude_floor:
        return CycleClosureResult(
            status="closure_not_identifiable",
            ratio=None,
            absolute_residual=absolute_residual,
            cycle_amplitude=cycle_amplitude,
        )
    return CycleClosureResult(
        status="resolved",
        ratio=absolute_residual / cycle_amplitude,
        absolute_residual=absolute_residual,
        cycle_amplitude=cycle_amplitude,
    )


def common_phase_field_differences(
    first_history: np.ndarray,
    second_history: np.ndarray,
    *,
    phases: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> dict[str, float]:
    """Compare two registered state histories at exact common phases."""
    first = np.asarray(first_history, dtype=np.float64)
    second = np.asarray(second_history, dtype=np.float64)
    if first.ndim < 1 or second.ndim < 1:
        raise ValueError("field histories must have a phase dimension")
    if first.shape[1:] != second.shape[1:]:
        raise ValueError("field histories must share the same spatial shape")
    first_steps = validate_steps_per_cycle(first.shape[0] - 1)
    second_steps = validate_steps_per_cycle(second.shape[0] - 1)
    result: dict[str, float] = {}
    for phase in phases:
        first_step = step_for_registered_phase(phase, first_steps)
        second_step = step_for_registered_phase(phase, second_steps)
        result[f"{phase:.4f}"] = symmetric_relative_difference(
            first[first_step], second[second_step]
        )
    return result


@dataclass(frozen=True)
class RichardsonResult:
    status: str
    order: float | None
    extrapolated: float | None
    coarse_medium_difference: float
    medium_fine_difference: float


def richardson_extrapolation(
    coarse: float,
    medium: float,
    fine: float,
    *,
    noise_floor: float = 1.0e-12,
    minimum_stable_order: float = 0.25,
    maximum_stable_order: float = 4.0,
) -> RichardsonResult:
    """Return a guarded two-to-one Richardson estimate when order is credible."""
    order_result = observed_refinement_order(
        coarse,
        medium,
        fine,
        noise_floor=noise_floor,
    )
    if order_result.status != "order_estimated" or order_result.order is None:
        return RichardsonResult(
            order_result.status,
            None,
            None,
            order_result.coarse_medium_difference,
            order_result.medium_fine_difference,
        )
    order = float(order_result.order)
    if not minimum_stable_order <= order <= maximum_stable_order:
        return RichardsonResult(
            "order_not_identifiable",
            None,
            None,
            order_result.coarse_medium_difference,
            order_result.medium_fine_difference,
        )
    denominator = 2.0**order - 1.0
    if abs(denominator) <= noise_floor:
        return RichardsonResult(
            "order_not_identifiable",
            None,
            None,
            order_result.coarse_medium_difference,
            order_result.medium_fine_difference,
        )
    extrapolated = fine + (fine - medium) / denominator
    if not math.isfinite(extrapolated):
        return RichardsonResult(
            "order_not_identifiable",
            None,
            None,
            order_result.coarse_medium_difference,
            order_result.medium_fine_difference,
        )
    return RichardsonResult(
        "richardson_estimated",
        order,
        float(extrapolated),
        order_result.coarse_medium_difference,
        order_result.medium_fine_difference,
    )
