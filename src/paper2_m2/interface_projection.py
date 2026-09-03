"""Conservative common-segment projection for M2A interface observables."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def _checked_axes(native_x: FloatArray, common_x: FloatArray) -> tuple[FloatArray, FloatArray]:
    native_x = np.asarray(native_x, dtype=np.float64)
    common_x = np.asarray(common_x, dtype=np.float64)
    if native_x.ndim != 1 or common_x.ndim != 1:
        raise ValueError("interface coordinates must be one-dimensional")
    if len(native_x) < 2 or len(common_x) < 2:
        raise ValueError("at least one interface segment is required")
    if not np.all(np.diff(native_x) > 0.0) or not np.all(np.diff(common_x) > 0.0):
        raise ValueError("interface coordinates must be strictly increasing")
    if not np.isclose(native_x[0], common_x[0], atol=1.0e-12) or not np.isclose(
        native_x[-1], common_x[-1], atol=1.0e-12
    ):
        raise ValueError("native and common interfaces must share both endpoints")
    for coordinate in common_x:
        if not np.any(np.isclose(native_x, coordinate, atol=1.0e-12)):
            raise ValueError("the common segmentation must be nested in the native grid")
    return native_x, common_x


def project_piecewise_linear_to_common_segments(
    native_x: FloatArray,
    nodal_values: FloatArray,
    common_x: FloatArray,
) -> FloatArray:
    """Return conservative P0 segment averages on a nested common grid.

    ``nodal_values`` has shape ``(native_nodes, ...)``.  The native field is
    interpreted as piecewise linear.  Each returned common-segment value is
    its exact integral average, so the integral of every component is
    preserved to floating-point roundoff.
    """

    native_x, common_x = _checked_axes(native_x, common_x)
    values = np.asarray(nodal_values, dtype=np.float64)
    if values.ndim < 1 or values.shape[0] != len(native_x):
        raise ValueError("nodal_values first axis must match native_x")
    result = np.empty((len(common_x) - 1,) + values.shape[1:], dtype=np.float64)
    for segment in range(len(common_x) - 1):
        left = common_x[segment]
        right = common_x[segment + 1]
        selected = np.flatnonzero(
            (native_x >= left - 1.0e-12) & (native_x <= right + 1.0e-12)
        )
        if len(selected) < 2:
            raise RuntimeError("common segment does not contain a native subsegment")
        local_x = native_x[selected]
        local_values = values[selected]
        widths = np.diff(local_x)
        trapezoids = 0.5 * (local_values[:-1] + local_values[1:])
        reshape = (len(widths),) + (1,) * (values.ndim - 1)
        integral = np.sum(widths.reshape(reshape) * trapezoids, axis=0)
        result[segment] = integral / (right - left)
    return result


def piecewise_linear_integral(native_x: FloatArray, nodal_values: FloatArray) -> FloatArray:
    """Integrate a vector/tensor nodal field exactly under P1 interpolation."""

    native_x = np.asarray(native_x, dtype=np.float64)
    values = np.asarray(nodal_values, dtype=np.float64)
    if values.shape[0] != len(native_x):
        raise ValueError("nodal_values first axis must match native_x")
    widths = np.diff(native_x)
    trapezoids = 0.5 * (values[:-1] + values[1:])
    reshape = (len(widths),) + (1,) * (values.ndim - 1)
    return np.sum(widths.reshape(reshape) * trapezoids, axis=0)


def common_segment_integral(common_x: FloatArray, segment_values: FloatArray) -> FloatArray:
    """Integrate a P0 field on the common segmentation."""

    common_x = np.asarray(common_x, dtype=np.float64)
    values = np.asarray(segment_values, dtype=np.float64)
    if values.shape[0] != len(common_x) - 1:
        raise ValueError("segment_values first axis must match common segments")
    widths = np.diff(common_x)
    reshape = (len(widths),) + (1,) * (values.ndim - 1)
    return np.sum(widths.reshape(reshape) * values, axis=0)


def common_segment_space_time_l2(
    common_x: FloatArray,
    segment_values: FloatArray,
    time_step: float,
) -> float:
    """Space-time L2 norm with left-endpoint time sampling over one cycle."""

    values = np.asarray(segment_values, dtype=np.float64)
    if values.ndim != 3 or values.shape[1] != 2:
        raise ValueError("segment_values must have shape (segments, 2, time_samples)")
    if time_step <= 0.0:
        raise ValueError("time_step must be positive")
    widths = np.diff(np.asarray(common_x, dtype=np.float64))
    return float(
        np.sqrt(
            time_step
            * np.sum(widths[:, None, None] * values * values)
        )
    )


def constant_traction_projection_manufactured_check(
    *,
    native_segments: int,
    common_segments: int,
) -> dict[str, float | bool | int]:
    """Check conservation, sign and work for a constant vector traction."""

    if native_segments % common_segments != 0:
        raise ValueError("native segmentation must be a refinement of common segmentation")
    native_x = np.linspace(-0.5, 0.5, native_segments + 1)
    common_x = np.linspace(-0.5, 0.5, common_segments + 1)
    traction_vector = np.asarray((2.0, -3.0), dtype=np.float64)
    traction = np.repeat(traction_vector[None, :], len(native_x), axis=0)
    displacement_increment = np.column_stack(
        (
            0.03 + 0.02 * native_x + 0.01 * native_x**2,
            -0.01 + 0.04 * native_x - 0.02 * native_x**2,
        )
    )
    projected_traction = project_piecewise_linear_to_common_segments(
        native_x, traction, common_x
    )
    projected_increment = project_piecewise_linear_to_common_segments(
        native_x, displacement_increment, common_x
    )
    native_force = piecewise_linear_integral(native_x, traction)
    projected_force = common_segment_integral(common_x, projected_traction)
    native_work = float(
        piecewise_linear_integral(
            native_x, np.sum(traction * displacement_increment, axis=1)
        )
    )
    projected_work = float(
        common_segment_integral(
            common_x,
            np.sum(projected_traction * projected_increment, axis=1),
        )
    )
    force_error = float(np.linalg.norm(projected_force - native_force))
    constant_error = float(
        np.max(np.abs(projected_traction - traction_vector[None, :]))
    )
    work_error = abs(projected_work - native_work)
    sign_preserved = bool(
        np.all(projected_traction[:, 0] > 0.0)
        and np.all(projected_traction[:, 1] < 0.0)
    )
    tolerance = 1.0e-12
    return {
        "native_segments": native_segments,
        "common_segments": common_segments,
        "constant_field_max_abs_error": constant_error,
        "integrated_force_abs_error": force_error,
        "discrete_interface_work_abs_error": work_error,
        "sign_preserved": sign_preserved,
        "tolerance": tolerance,
        "pass": bool(
            constant_error <= tolerance
            and force_error <= tolerance
            and work_error <= tolerance
            and sign_preserved
        ),
    }
