"""Pure periodic Q2/Q1 geometry adapter for an image-derived outer contour.

The cavity and radial layer interfaces are constructed homothetic surfaces,
not measured anatomy.  This module performs no material evaluation or solve.
"""

from __future__ import annotations

from itertools import product

import numpy as np


RADIAL_BOUNDARIES = (20 / 27, 21 / 27, 22 / 27, 1.)


def _real_array(value, name):
    raw = np.asarray(value)
    if np.iscomplexobj(raw):
        raise ValueError(f"{name} must be real")
    try:
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be finite and real") from error
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _positive_scalar(value, name):
    raw = _real_array(value, name)
    if raw.ndim != 0 or np.asarray(value).dtype.kind == "b" or float(raw) <= 0:
        raise ValueError(f"{name} must be a positive finite real scalar")
    return float(raw)


def _cross(first, second):
    return first[..., 0] * second[..., 1] - first[..., 1] * second[..., 0]


def _curve_geometry(boundary):
    """Exact segmentwise minimum of C cross dC/dxi, and exact Q2 area."""
    count = len(boundary) // 2
    controls = np.stack([boundary[(2 * np.arange(count) + offset) % (2 * count)]
                         for offset in range(3)], axis=1)
    quadratic = .5 * (controls[:, 0] + controls[:, 2]) - controls[:, 1]
    linear = .5 * (controls[:, 2] - controls[:, 0])
    constant = controls[:, 1]
    # C(xi) x C'(xi) = a*xi**2 + b*xi + c.  Minimize on the full interval.
    coefficient_a = _cross(linear, quadratic)
    coefficient_b = 2 * _cross(constant, quadratic)
    coefficient_c = _cross(constant, linear)
    minima = np.minimum(coefficient_a - coefficient_b + coefficient_c,
                        coefficient_a + coefficient_b + coefficient_c)
    minimizing_xi = np.where(coefficient_b >= 0, -1., 1.)
    convex = coefficient_a > 0
    vertex = np.zeros(count)
    np.divide(-coefficient_b, 2 * coefficient_a, out=vertex, where=convex)
    interior = convex & (np.abs(vertex) < 1)
    interior_values = coefficient_a * vertex**2 + coefficient_b * vertex + coefficient_c
    improve = interior & (interior_values < minima)
    minima[improve] = interior_values[improve]
    minimizing_xi[improve] = vertex[improve]
    if not np.all(np.isfinite(minima)) or np.any(minima <= 0):
        raise ValueError("Q2 contour has nonpositive or nonfinite homothetic orientation")
    # The closed curve is star-oriented about the origin; reject repeated winds.
    increments = np.arctan2(_cross(boundary, np.roll(boundary, -1, axis=0)),
                            np.sum(boundary * np.roll(boundary, -1, axis=0), axis=1))
    winding = float(np.sum(increments) / (2 * np.pi))
    if not np.isfinite(winding) or abs(winding - 1) > 1e-10:
        raise ValueError("Q2 contour must have exactly one positive winding")
    exact_area = float(np.sum(coefficient_c + coefficient_a / 3))
    if not np.isfinite(exact_area) or exact_area <= 0:
        raise ValueError("Q2 contour must enclose positive finite area")
    worst = int(np.argmin(minima))
    return {"minimum_orientation_cross": float(minima[worst]),
            "orientation_minima_by_segment": minima.tolist(),
            "orientation_minimizer_segment": worst,
            "orientation_minimizer_xi": float(minimizing_xi[worst]),
            "orientation_polynomial_coefficients": np.column_stack(
                (coefficient_a, coefficient_b, coefficient_c)).tolist(),
            "winding_number": winding, "exact_outer_area": exact_area}


def build_contour_wall(source_arrays, radial_intervals, segments=36, height=.5) -> dict:
    """Build a closed periodic Q2 displacement / continuous Q1 pressure wall.

    Global order is (radial, periodic contour, z), z fastest.  Local order is
    the same tensor product.  There is no duplicate node at the contour seam.
    The frame is x_solver=R*(x_source-center)/L, with A-to-B along positive x.
    All uz and only three in-plane gauge DOFs are fixed; no pressure DOF is fixed.
    Returned metadata is JSON-serializable.  Source arrays are never mutated.
    """
    try:
        intervals = tuple(radial_intervals)
    except TypeError as error:
        raise ValueError("radial_intervals must contain three positive integers") from error
    if (len(intervals) != 3 or any(isinstance(value, (bool, np.bool_))
                                 or not isinstance(value, (int, np.integer)) or value < 1
                                 for value in intervals)):
        raise ValueError("radial_intervals must contain three positive integers")
    intervals = tuple(int(value) for value in intervals)
    if (isinstance(segments, (bool, np.bool_)) or not isinstance(segments, (int, np.integer))
            or segments < 4 or segments % 2):
        raise ValueError("segments must be an even integer of at least four")
    segments = int(segments)
    height = _positive_scalar(height, "height")
    try:
        source = _real_array(source_arrays["smooth_contour_um"], "source contour")
        center = _real_array(source_arrays["center_um"], "source center")
        length_scale = _positive_scalar(source_arrays["length_scale_um"], "length scale")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("source_arrays requires contour, center and length scale") from error
    if source.ndim != 2 or source.shape[1] != 2 or len(source) < 4 or center.shape != (2,):
        raise ValueError("source contour must be Nx2, N>=4, and center must have shape (2,)")
    closed = np.vstack((source, source[0]))
    lengths = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    if np.any(lengths <= 0) or not np.all(np.isfinite(lengths)):
        raise ValueError("source contour must omit its closing duplicate and have no zero-length edges")
    normalized = (source - center) / length_scale
    if np.sum(_cross(normalized, np.roll(normalized, -1, axis=0))) <= 0:
        raise ValueError("source contour must have positive counterclockwise orientation")
    arclength = np.r_[0., np.cumsum(lengths)]
    if not np.isfinite(arclength[-1]):
        raise ValueError("source contour has nonfinite arclength")
    query = np.arange(2 * segments) * arclength[-1] / (2 * segments)
    boundary_um = np.column_stack([np.interp(query, arclength, closed[:, axis]) for axis in (0, 1)])
    boundary_unrotated = (boundary_um - center) / length_scale
    direction = boundary_unrotated[segments] - boundary_unrotated[0]
    separation = float(np.linalg.norm(direction))
    if not np.isfinite(separation) or separation <= 0:
        raise ValueError("half-contour anchor points must be distinct")
    direction = direction / separation
    rotation = np.array([[direction[0], direction[1]], [-direction[1], direction[0]]])
    boundary = boundary_unrotated @ rotation.T
    curve_geometry = _curve_geometry(boundary)

    radial_q1 = [RADIAL_BOUNDARIES[0]]
    radial_layers = []
    for layer, count in enumerate(intervals):
        radial_q1.extend(np.linspace(RADIAL_BOUNDARIES[layer], RADIAL_BOUNDARIES[layer + 1], count + 1)[1:])
        radial_layers.extend([layer] * count)
    radial_q1 = np.asarray(radial_q1)
    radial_count = sum(intervals)
    radial_q2 = np.empty(2 * radial_count + 1)
    radial_q2[::2] = radial_q1
    radial_q2[1::2] = .5 * (radial_q1[:-1] + radial_q1[1:])
    node_shape = (len(radial_q2), 2 * segments, 3)
    pressure_shape = (len(radial_q1), segments, 2)

    def grid_nodes(radii, perimeter, nz):
        output = np.empty((len(radii), len(perimeter), nz, 3))
        output[..., :2] = radii[:, None, None, None] * perimeter[None, :, None, :]
        output[..., 2] = np.linspace(0, height, nz)
        return output.reshape(-1, 3)

    nodes = grid_nodes(radial_q2, boundary, 3)
    pressure_nodes = grid_nodes(radial_q1, boundary[::2], 2)
    cells, pressure_cells, layer_ids, inner_faces = [], [], [], []
    for radial, angular in product(range(radial_count), range(segments)):
        for order, shape, target in ((2, node_shape, cells), (1, pressure_shape, pressure_cells)):
            target.append([np.ravel_multi_index((order * radial + local[0],
                                                 (order * angular + local[1]) % (order * segments), local[2]), shape)
                           for local in product(range(order + 1), repeat=3)])
        layer_ids.append(radial_layers[radial])
        if radial == 0:
            inner_faces.append((len(cells) - 1, 0, -1))
    anchor_a = int(np.ravel_multi_index((2 * radial_count, 0, 1), node_shape))
    anchor_b = int(np.ravel_multi_index((2 * radial_count, segments, 1), node_shape))
    gauge_dofs = [3 * anchor_a, 3 * anchor_a + 1, 3 * anchor_b + 1]
    fixed = {3 * node + 2: 0. for node in range(len(nodes))}
    fixed.update({dof: 0. for dof in gauge_dofs})
    mesh = {"nodes": nodes, "pressure_nodes": pressure_nodes,
            "elements": np.asarray(cells, dtype=np.int64),
            "pressure_elements": np.asarray(pressure_cells, dtype=np.int64),
            "counts": (radial_count, segments, 1),
            "lengths": np.array([1 - RADIAL_BOUNDARIES[0], 2 * np.pi, height]),
            "node_shape": node_shape, "pressure_shape": pressure_shape,
            "element_type": "Q2-Q1-continuous", "geometry_mapping": "isoparametric", "periodic_axis": 1}
    metadata = {"schema_version": "prl.contour_wall_geometry.v1", "segments": segments, "height": height,
                "source_to_solver_rotation": rotation.tolist(), "solver_to_source_rotation": rotation.T.tolist(),
                "rotation_angle_rad": float(np.arctan2(rotation[1, 0], rotation[0, 0])),
                "coordinate_transform": "x_solver=R*(x_source_um-center_um)/length_scale_um",
                "center_um": center.tolist(), "length_scale_um": length_scale,
                "outer_curve_nodes": boundary.tolist(), "outer_curve_nodes_um": boundary_um.tolist(),
                "radial_boundary_fractions": list(RADIAL_BOUNDARIES), "radial_intervals": list(intervals),
                "radial_q1_fractions": radial_q1.tolist(), "radial_q2_fractions": radial_q2.tolist(),
                "node_shape": list(node_shape), "pressure_shape": list(pressure_shape),
                "inner_midplane_nodes": (3 * np.arange(2 * segments) + 1).tolist(),
                "outer_midplane_nodes": (2 * radial_count * 2 * segments * 3
                                         + 3 * np.arange(2 * segments) + 1).tolist(),
                "anchor_node_ids": {"A": anchor_a, "B": anchor_b}, "gauge_dofs": gauge_dofs,
                "internal_geometry": "assumed homothetic cavity and layer labels, not measured anatomy",
                "reference_state": "zero-pressure stress-free geometry is assumed, not measured",
                **curve_geometry,
                "exact_inner_area": curve_geometry["exact_outer_area"] * RADIAL_BOUNDARIES[0]**2,
                "exact_reference_wall_volume": curve_geometry["exact_outer_area"] * (1 - RADIAL_BOUNDARIES[0]**2) * height}
    return {"mesh": mesh, "fixed": fixed, "inner_faces": inner_faces,
            "layer_ids": np.asarray(layer_ids, dtype=np.int64), "metadata": metadata}
