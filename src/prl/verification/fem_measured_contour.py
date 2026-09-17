"""Independently audit the saved measured-outline, two-dimensional FEM pilot.

This module intentionally imports neither the FEM runner nor its assembler.
Image-outline agreement and numerical consistency do not validate biological
material parameters, inferred wall layers, or a physiological beating cycle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage, sparse
from scipy.spatial.distance import cdist


_TOLERANCE = 1.0e-10
_MATERIALS = {"endocardium": 1.0, "ecm": 0.5, "myocardium": 2.5}
_LEVELS = {"G0": (96, (2, 2, 4)), "G1": (192, (4, 4, 8))}
_RADIAL_FRACTIONS = np.array([1.00, 1.05, 1.10, 1.35]) / 1.35


def _signed_polygon_area(points: np.ndarray) -> float:
    successor = np.roll(points, -1, axis=0)
    return float(np.sum(points[:, 0] * successor[:, 1]
                        - points[:, 1] * successor[:, 0]) / 2.0)


def _maximum_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(actual - expected)))


def _rasterize_outline(points_xy: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Independent even-odd scanline rasterization at integer pixel centers."""
    raster = np.zeros(shape, dtype=bool)
    start = points_xy
    end = np.roll(points_xy, -1, axis=0)
    first_row = max(0, int(np.ceil(points_xy[:, 1].min())))
    last_row = min(shape[0] - 1, int(np.floor(points_xy[:, 1].max())))
    for row in range(first_row, last_row + 1):
        crossing = ((start[:, 1] <= row) & (end[:, 1] > row)
                    | (end[:, 1] <= row) & (start[:, 1] > row))
        selected_start, selected_end = start[crossing], end[crossing]
        intersections = np.sort(selected_start[:, 0] + (row - selected_start[:, 1])
                                * (selected_end[:, 0] - selected_start[:, 0])
                                / (selected_end[:, 1] - selected_start[:, 1]))
        if len(intersections) % 2:
            raise ValueError("Odd scanline intersection count for closed outline")
        for left, right in intersections.reshape(-1, 2):
            first_column = max(0, int(np.ceil(left)))
            last_column = min(shape[1] - 1, int(np.floor(right)))
            if first_column <= last_column:
                raster[row, first_column:last_column + 1] = True
        # The half-open crossing rule avoids counting vertices twice; include
        # any horizontal boundary or isolated integer vertex explicitly.
        horizontal = (start[:, 1] == row) & (end[:, 1] == row)
        for first, second in zip(start[horizontal], end[horizontal]):
            first_column = max(0, int(np.ceil(min(first[0], second[0]))))
            last_column = min(shape[1] - 1, int(np.floor(max(first[0], second[0]))))
            if first_column <= last_column:
                raster[row, first_column:last_column + 1] = True
        for column in start[start[:, 1] == row, 0]:
            if column == np.floor(column) and 0 <= column < shape[1]:
                raster[row, int(column)] = True
    return raster


def _sampled_hausdorff(first: np.ndarray, second: np.ndarray) -> float:
    """Use bounded all-pairs distance blocks rather than the extractor's KD tree."""
    directed = []
    for origin, destination in ((first, second), (second, first)):
        worst_nearest = 0.0
        for offset in range(0, len(origin), 256):
            distances = cdist(origin[offset:offset + 256], destination)
            worst_nearest = max(worst_nearest, float(distances.min(axis=1).max()))
        directed.append(worst_nearest)
    return max(directed)


def _arclength_samples(points: np.ndarray, count: int) -> np.ndarray:
    following = np.roll(points, -1, axis=0)
    segment_lengths = np.linalg.norm(following - points, axis=1)
    if np.any(segment_lengths <= 0):
        raise ValueError("Smoothed outline contains a zero-length segment")
    stations = np.concatenate(([0.0], np.cumsum(segment_lengths)))
    queries = stations[-1] * np.arange(count) / count
    segment = np.searchsorted(stations, queries, side="right") - 1
    fraction = (queries - stations[segment]) / segment_lengths[segment]
    return points[segment] + fraction[:, None] * (following[segment] - points[segment])


def _verify_geometry_source(result: Path, geometry: dict[str, Any],
                            configuration: dict[str, Any]) -> tuple[dict, dict]:
    with np.load(result / "geometry_source.npz", allow_pickle=False) as archive:
        source = {name: np.asarray(archive[name]) for name in (
            "raw_contour_um", "smooth_contour_um", "slice_mask", "source_slice_mask",
            "voxel_um", "slice_z_index", "center_um", "length_scale_um")}
    raw, smooth = source["raw_contour_um"], source["smooth_contour_um"]
    for points in (raw, smooth):
        if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
                or not np.all(np.isfinite(points))):
            raise ValueError("Source contours must be finite N by 2 polygons")
    mask = source["slice_mask"]
    original = source["source_slice_mask"]
    voxel = source["voxel_um"]
    scale = float(source["length_scale_um"])
    center = source["center_um"]
    if (mask.ndim != 2 or original.shape != mask.shape
            or not np.all(np.isin(mask, [0, 1])) or not np.all(np.isin(original, [0, 1]))
            or voxel.shape != (3,) or not np.all(np.isfinite(voxel)) or np.any(voxel <= 0)
            or center.shape != (2,) or not np.all(np.isfinite(center))
            or not np.isfinite(scale) or scale <= 0):
        raise ValueError("Invalid source masks, voxel calibration, center or length scale")
    mask, original = mask.astype(bool), original.astype(bool)
    labels, component_count = ndimage.label(original)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    if not np.any(sizes):
        raise ValueError("Source slice is empty")
    largest = labels == int(np.argmax(sizes))
    expected_mask = ndimage.binary_fill_holes(largest)
    raster = _rasterize_outline(smooth / voxel[:2], mask.shape)
    union = int(np.count_nonzero(raster | mask))
    if union == 0:
        raise ValueError("Empty mask and smoothed-contour raster")
    iou = float(np.count_nonzero(raster & mask) / union)
    hausdorff = _sampled_hausdorff(raw, smooth)
    outer_area = _signed_polygon_area(smooth)
    if outer_area <= 0 or _signed_polygon_area(raw) <= 0:
        raise ValueError("Raw and smoothed contours must have positive signed area")
    expected_scale = float(np.sqrt(outer_area / np.pi) / 1.35)
    edge = np.roll(smooth, -1, axis=0) - smooth
    inward_distance = (edge[:, 0] * (center[1] - smooth[:, 1])
                       - edge[:, 1] * (center[0] - smooth[:, 0])) / np.linalg.norm(edge, axis=1)
    checks = {
        "source_mask_processing_recomputed": bool(np.array_equal(mask, expected_mask)),
        "source_component_accounting_recomputed": (
            int(geometry["components"]) == component_count
            and int(geometry["discarded_component_pixels"]) == int(original.sum() - largest.sum())
            and int(geometry["filled_hole_pixels"]) == int(mask.sum() - largest.sum())),
        "source_mask_iou_independently_recomputed": abs(iou - float(geometry["source_mask_iou"])) <= _TOLERANCE,
        "sampled_hausdorff_independently_recomputed": abs(hausdorff - float(geometry["contour_hausdorff_um"])) <= _TOLERANCE,
        "source_mask_iou_at_least_098": iou >= 0.98,
        "source_contour_hausdorff_at_most_2um": hausdorff <= 2.0,
        "physical_scale_independently_recomputed": max(
            abs(expected_scale - scale),
            abs(scale - float(geometry["length_scale_um"])),
            abs(scale - float(configuration["geometry"]["length_scale_um"]))) <= _TOLERANCE,
        "source_outer_area_independently_recomputed": abs(outer_area - float(geometry["smooth_outer_area_um2"])) <= _TOLERANCE,
        "source_coordinate_mapping_metadata_consistent": (
            _maximum_error(center, np.asarray(geometry["center_um"])) <= _TOLERANCE
            and _maximum_error(center, np.asarray(configuration["geometry"]["center_um"])) <= _TOLERANCE
            and _maximum_error(voxel, np.asarray(geometry["voxel_um"])) <= _TOLERANCE
            and int(source["slice_z_index"]) == int(geometry["slice_z_index"])
            == int(configuration["geometry"]["slice_z_index"])),
        "positive_homothetic_kernel_margin": float(inward_distance.min()) > 0,
        "homothetic_kernel_margin_recomputed": abs(float(inward_distance.min())
                                                    - float(geometry["kernel_margin_um"])) <= _TOLERANCE,
        "frozen_radial_fractions": (
            _maximum_error(np.asarray(geometry["radial_boundary_fractions"]), _RADIAL_FRACTIONS) <= _TOLERANCE
            and _maximum_error(np.asarray(configuration["geometry"]["radial_boundary_fractions"]),
                               _RADIAL_FRACTIONS) <= _TOLERANCE),
    }
    return source, {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
                    "source_mask_iou": iou, "sampled_contour_hausdorff_um": hausdorff,
                    "source_outer_area_um2": outer_area, "length_scale_um": expected_scale,
                    "minimum_inward_kernel_margin_um": float(inward_distance.min())}


def _verify_mesh_geometry(arrays: dict[str, np.ndarray], configuration: dict[str, Any],
                          source: dict[str, np.ndarray], label: str) -> dict[str, Any]:
    angular_count, intervals = _LEVELS[label]
    raw_level = configuration["levels"][label]
    boundary = _arclength_samples(source["smooth_contour_um"], angular_count)
    normalized = (boundary - source["center_um"]) / float(source["length_scale_um"])
    radii = np.concatenate([np.linspace(_RADIAL_FRACTIONS[index], _RADIAL_FRACTIONS[index + 1],
                                       count + 1)[:-1] for index, count in enumerate(intervals)]
                           + [np.array([_RADIAL_FRACTIONS[-1]])])
    expected_coordinates = (radii[:, None, None] * normalized[None, :, :]).reshape(-1, 2)
    coordinates, cells, layers = arrays["coordinates"], arrays["cells"].astype(int), arrays["cell_layers"]
    if coordinates.shape != expected_coordinates.shape:
        raise ValueError(f"{label} node count differs from frozen radial/arclength discretization")
    inner, outer = arrays["inner_nodes"].astype(int), arrays["outer_nodes"].astype(int)
    if len(inner) != angular_count or len(outer) != angular_count:
        raise ValueError(f"{label} boundary cycle count differs from frozen discretization")
    geometry_error = _maximum_error(coordinates, expected_coordinates)
    outer_um_error = _maximum_error(coordinates[outer] * float(source["length_scale_um"])
                                    + source["center_um"], boundary)
    radial_indices = cells // angular_count
    angular_indices = cells % angular_count
    ring_index = radial_indices.min(axis=1)
    if np.any(ring_index >= sum(intervals)):
        raise ValueError("Triangle has no associated radial interval")
    expected_layers = np.repeat(np.arange(3), intervals)[ring_index]
    segment_start = np.zeros(len(cells), dtype=int)
    valid_segments = True
    for cell, vertex_angles in enumerate(angular_indices):
        pair = np.unique(vertex_angles)
        if len(pair) != 2 or (pair[1] - pair[0] not in (1, angular_count - 1)):
            valid_segments = False
            continue
        segment_start[cell] = pair[0] if pair[1] - pair[0] == 1 else pair[1]
    expected_tangents = boundary[(segment_start + 1) % angular_count] - boundary[segment_start]
    expected_tangents /= np.linalg.norm(expected_tangents, axis=1)[:, None]
    expected_tangents[expected_layers != 2] = 0
    tangent_error = _maximum_error(arrays["active_tangents"], expected_tangents)
    checks = {
        "frozen_mesh_discretization": (int(raw_level["ntheta"]) == angular_count
                                       and tuple(raw_level["radial_intervals"]) == intervals),
        "outer_boundary_is_measured_arclength_discretization": outer_um_error <= _TOLERANCE,
        "all_nodes_match_homothetic_source_mapping": geometry_error <= _TOLERANCE,
        "declared_boundary_indices_match_radial_rings": bool(
            np.array_equal(inner, np.arange(angular_count))
            and np.array_equal(outer, np.arange(len(coordinates) - angular_count, len(coordinates)))),
        "triangles_connect_adjacent_radial_angular_intervals": bool(
            valid_segments and np.all(radial_indices.max(axis=1) - ring_index == 1)),
        "material_layers_match_radial_intervals": bool(np.array_equal(layers, expected_layers)),
        "active_tangents_follow_outer_polygon_segments": tangent_error <= _TOLERANCE,
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "maximum_outer_contour_coordinate_error_um": outer_um_error,
            "maximum_homothetic_node_coordinate_error": geometry_error,
            "maximum_segment_tangent_error": tangent_error}


def _boundary_matches(cells: np.ndarray, inner: np.ndarray, outer: np.ndarray) -> bool:
    """Ensure the saved cycles really are the two boundary loops of the mesh."""
    edges = np.concatenate((cells[:, [0, 1]], cells[:, [1, 2]], cells[:, [2, 0]]))
    unique_edges, incidence = np.unique(np.sort(edges, axis=1), axis=0,
                                       return_counts=True)
    actual = {tuple(edge) for edge in unique_edges[incidence == 1]}
    expected: set[tuple[int, int]] = set()
    for cycle in (inner, outer):
        if len(cycle) < 3 or len(np.unique(cycle)) != len(cycle):
            return False
        expected.update(tuple(sorted((int(first), int(second))))
                        for first, second in zip(cycle, np.roll(cycle, -1)))
    return bool(np.all(incidence <= 2) and actual == expected
                and len(expected) == len(inner) + len(outer)
                and not np.intersect1d(inner, outer).size)


def _verify_level(path: Path, configuration: dict[str, Any],
                  geometry_source: dict[str, np.ndarray] | None = None) -> dict[str, Any]:
    required = ("coordinates", "cells", "cell_layers", "inner_nodes", "outer_nodes",
                "phases", "activation", "displacements", "strains", "stresses",
                "equivalent_stress", "pressure", "lumen_area", "outer_area",
                "active_strain_unit", "active_tangents")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in required}
    if not all(np.issubdtype(value.dtype, np.number) and np.all(np.isfinite(value))
               for value in arrays.values()):
        raise ValueError("All required saved arrays must be numeric and finite")
    coordinates = arrays["coordinates"]
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or len(coordinates) < 6:
        raise ValueError("coordinates must be a nonempty N by 2 mesh")
    for name in ("cells", "cell_layers", "inner_nodes", "outer_nodes"):
        if not np.array_equal(arrays[name], arrays[name].astype(np.int64)):
            raise ValueError(f"{name} contains noninteger indices")
    cells = arrays["cells"].astype(np.int64)
    layers = arrays["cell_layers"].astype(np.int64)
    inner = arrays["inner_nodes"].astype(np.int64)
    outer = arrays["outer_nodes"].astype(np.int64)
    if cells.ndim != 2 or cells.shape[1] != 3 or not len(cells):
        raise ValueError("cells must be a nonempty M by 3 connectivity array")
    count, nodes, states = len(cells), len(coordinates), 41
    shapes = {"cell_layers": (count,), "phases": (states,), "activation": (states,),
              "displacements": (states, nodes, 2), "strains": (states, count, 3),
              "stresses": (states, count, 3), "equivalent_stress": (states, count),
              "pressure": (states, count), "lumen_area": (states,),
              "outer_area": (states,), "active_strain_unit": (count, 3),
              "active_tangents": (count, 2)}
    for name, shape in shapes.items():
        if arrays[name].shape != shape:
            raise ValueError(f"{name} shape {arrays[name].shape} differs from {shape}")
    if inner.ndim != 1 or outer.ndim != 1:
        raise ValueError("Boundary cycles must be one dimensional")
    if any(np.any(index < 0) or np.any(index >= nodes) for index in (cells, inner, outer)):
        raise ValueError("Connectivity or boundary node index is out of bounds")
    if set(layers.tolist()) != {0, 1, 2}:
        raise ValueError("All three material layers must be present, indexed 0, 1, 2")

    # Each column of inverse([1,x_i,y_i]) is a P1 basis coefficient vector.
    # This affine-inverse construction is independent of the runner's explicit
    # triangle-edge formula for its strain-displacement matrices.
    points = coordinates[cells]
    affine = np.concatenate((np.ones((count, 3, 1)), points), axis=2)
    signed_areas = np.linalg.det(affine) / 2.0
    if np.any(signed_areas <= 0):
        raise ValueError("Reference mesh contains inverted or degenerate triangles")
    gradients = np.linalg.inv(affine)[:, 1:, :]
    strain_maps = np.zeros((count, 3, 6), dtype=np.float64)
    strain_maps[:, 0, 0::2] = gradients[:, 0, :]
    strain_maps[:, 1, 1::2] = gradients[:, 1, :]
    strain_maps[:, 2, 0::2] = gradients[:, 1, :]
    strain_maps[:, 2, 1::2] = gradients[:, 0, :]
    constitutive = []
    for name in _MATERIALS:
        young = float(configuration["materials"][name]["young"])
        poisson = float(configuration["materials"][name]["poisson"])
        multiplier = young / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        constitutive.append(multiplier * np.asarray(
            [[1.0 - poisson, poisson, 0.0], [poisson, 1.0 - poisson, 0.0],
             [0.0, 0.0, (1.0 - 2.0 * poisson) / 2.0]]))
    elasticity = np.asarray(constitutive)[layers]
    tangents = arrays["active_tangents"]
    active = layers == 2
    eigenstrain = np.zeros((count, 3), dtype=np.float64)
    eigenstrain[active, 0] = -tangents[active, 0] ** 2
    eigenstrain[active, 1] = -tangents[active, 1] ** 2
    eigenstrain[active, 2] = -2.0 * tangents[active, 0] * tangents[active, 1]

    dofs = (2 * cells[:, :, None] + np.arange(2)).reshape(count, 6)
    local_stiffness = np.einsum("mai,mab,mbj,m->mij", strain_maps, elasticity,
                                strain_maps, signed_areas)
    stiffness = sparse.coo_matrix(
        (local_stiffness.ravel(),
         (np.broadcast_to(dofs[:, :, None], (count, 6, 6)).ravel(),
          np.broadcast_to(dofs[:, None, :], (count, 6, 6)).ravel())),
        shape=(2 * nodes, 2 * nodes)).tocsr()
    local_load = np.einsum("mai,mab,mb,m->mi", strain_maps, elasticity,
                          eigenstrain, signed_areas)
    unit_load = np.zeros(2 * nodes, dtype=np.float64)
    np.add.at(unit_load, dofs.ravel(), local_load.ravel())

    # Three gauge conditions remove only mean translation and mean rotation.
    gauge = np.zeros((3, 2 * nodes), dtype=np.float64)
    gauge[0, 0::2], gauge[1, 1::2] = 1.0 / nodes, 1.0 / nodes
    rotational_scale = float(np.sum(coordinates ** 2))
    if rotational_scale <= 0:
        raise ValueError("Degenerate rotational gauge")
    gauge[2, 0::2] = -coordinates[:, 1] / rotational_scale
    gauge[2, 1::2] = coordinates[:, 0] / rotational_scale
    kkt_norm = max(float(np.max(np.asarray(abs(stiffness).sum(axis=1)).ravel()
                                + np.sum(np.abs(gauge), axis=0))),
                   float(np.max(np.sum(np.abs(gauge), axis=1))))

    displacement = arrays["displacements"]
    activation = arrays["activation"]
    expected_phase = np.linspace(0.0, 1.0, states)
    expected_activation = 0.015 * (1.0 - np.cos(2.0 * np.pi * expected_phase))
    recomputed_strain = np.einsum("mai,smi->sma", strain_maps,
                                  displacement[:, cells].reshape(states, count, 6))
    elastic_strain = recomputed_strain - activation[:, None, None] * eigenstrain
    recomputed_stress = np.einsum("mab,smb->sma", elasticity, elastic_strain)
    first, second, shear = np.moveaxis(recomputed_stress, -1, 0)
    recomputed_pressure = -(first + second) / 2.0
    recomputed_equivalent = np.sqrt(np.maximum(
        first ** 2 - first * second + second ** 2 + 3.0 * shear ** 2, 0.0))

    maximum_backward_residual = 0.0
    maximum_force_residual = 0.0
    maximum_gauge_residual = 0.0
    maximum_multiplier = 0.0
    minimum_deformed_area = float("inf")
    lumen_areas = np.zeros(states)
    outer_areas = np.zeros(states)
    for state in range(states):
        vector = displacement[state].reshape(-1)
        rhs = activation[state] * unit_load
        imbalance = stiffness @ vector - rhs
        # Recover, rather than trust saved, KKT multipliers. Projection removes
        # only forces in the span of the declared three gauge reactions.
        multipliers = np.linalg.solve(gauge @ gauge.T, -(gauge @ imbalance))
        force_residual = imbalance + gauge.T @ multipliers
        gauge_residual = gauge @ vector
        full_residual = max(float(np.max(np.abs(force_residual))),
                            float(np.max(np.abs(gauge_residual))))
        denominator = (kkt_norm * max(float(np.max(np.abs(vector))),
                                      float(np.max(np.abs(multipliers))))
                       + float(np.max(np.abs(rhs))))
        maximum_backward_residual = max(maximum_backward_residual,
                                         full_residual / max(denominator, 1.0e-30))
        maximum_force_residual = max(maximum_force_residual,
                                     float(np.max(np.abs(force_residual))))
        maximum_gauge_residual = max(maximum_gauge_residual,
                                     float(np.max(np.abs(gauge_residual))))
        maximum_multiplier = max(maximum_multiplier,
                                 float(np.max(np.abs(multipliers))))
        deformed = coordinates + displacement[state]
        deformed_points = deformed[cells]
        edges = deformed_points[:, 1:] - deformed_points[:, :1]
        areas = (edges[:, 0, 0] * edges[:, 1, 1]
                 - edges[:, 0, 1] * edges[:, 1, 0]) / 2.0
        minimum_deformed_area = min(minimum_deformed_area, float(np.min(areas)))
        lumen_areas[state] = _signed_polygon_area(deformed[inner])
        outer_areas[state] = _signed_polygon_area(deformed[outer])

    peak = int(np.argmax(expected_activation))
    reference_lumen = _signed_polygon_area(coordinates[inner])
    if reference_lumen <= 0:
        raise ValueError("Reference lumen cycle must have positive signed area")
    peak_change = float((lumen_areas[peak] - reference_lumen) / reference_lumen)
    errors = {
        "maximum_strain_recompute_error": _maximum_error(recomputed_strain, arrays["strains"]),
        "maximum_stress_recompute_error": _maximum_error(recomputed_stress, arrays["stresses"]),
        "maximum_pressure_recompute_error": _maximum_error(recomputed_pressure, arrays["pressure"]),
        "maximum_equivalent_stress_recompute_error": _maximum_error(
            recomputed_equivalent, arrays["equivalent_stress"]),
        "maximum_lumen_area_recompute_error": _maximum_error(lumen_areas, arrays["lumen_area"]),
        "maximum_outer_area_recompute_error": _maximum_error(outer_areas, arrays["outer_area"]),
        "maximum_eigenstrain_recompute_error": _maximum_error(eigenstrain, arrays["active_strain_unit"]),
    }
    checks = {
        "all_required_arrays_finite": True,
        "forty_one_frozen_phase_states": _maximum_error(arrays["phases"], expected_phase) <= _TOLERANCE,
        "frozen_cosine_activation_peak_003": _maximum_error(activation, expected_activation) <= _TOLERANCE,
        "unit_myocardial_tangents": _maximum_error(np.linalg.norm(tangents[active], axis=1),
                                                   np.ones(np.count_nonzero(active))) <= _TOLERANCE,
        "nonmyocardial_tangents_zero": float(np.max(np.abs(tangents[~active]))) <= _TOLERANCE,
        "boundary_cycles_match_mesh": _boundary_matches(cells, inner, outer),
        "no_duplicate_triangles": len(np.unique(np.sort(cells, axis=1), axis=0)) == count,
        "no_unused_mesh_nodes": len(np.unique(cells)) == nodes,
        "all_triangles_positive": minimum_deformed_area > 0,
        "cavity_and_outer_areas_positive_nested": bool(np.all(lumen_areas > 0)
                                                      and np.all(outer_areas > lumen_areas)),
        "all_fields_independently_recomputed": max(errors.values()) <= _TOLERANCE,
        "assembled_kkt_backward_residual": maximum_backward_residual <= _TOLERANCE,
        "rigid_gauge_residual": maximum_gauge_residual <= _TOLERANCE,
        "small_strain_scope": float(np.max(np.abs(recomputed_strain))) <= 0.05,
        "nonzero_active_contraction": peak_change <= -0.005,
        "unloaded_endpoints_return_to_reference": float(np.max(np.abs(displacement[[0, -1]]))) <= _TOLERANCE,
    }
    mesh_geometry = None
    if geometry_source is not None:
        mesh_geometry = _verify_mesh_geometry(arrays, configuration, geometry_source, path.stem)
        checks["mesh_geometry_independently_verified"] = mesh_geometry["status"] == "passed"
    return {
        "status": "passed" if all(checks.values()) else "failed", "checks": checks,
        "finite": True, "state_count": states, "node_count": nodes, "triangle_count": count,
        "minimum_reference_area": float(np.min(signed_areas)),
        "minimum_deformed_area": minimum_deformed_area,
        "peak_lumen_fraction_change": peak_change,
        "maximum_abs_recomputed_strain": float(np.max(np.abs(recomputed_strain))),
        "maximum_abs_saved_strain": float(np.max(np.abs(arrays["strains"]))),
        "maximum_backward_residual": maximum_backward_residual,
        "maximum_force_residual_absolute": maximum_force_residual,
        "maximum_constraint_residual": maximum_gauge_residual,
        "maximum_recovered_gauge_multiplier": maximum_multiplier,
        "mesh_geometry": mesh_geometry,
        **errors,
    }


def verify_fem_measured_contour(result: Path, save: bool = True) -> dict[str, Any]:
    """Verify source-outline geometry and raw FEM states; optionally save a report."""
    result = Path(result).resolve()
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    geometry = json.loads((result / "geometry.json").read_text(encoding="utf-8"))
    geometry_source = None
    try:
        geometry_source, geometry_verification = _verify_geometry_source(result, geometry, configuration)
    except (OSError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError) as error:
        geometry_verification = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    levels: dict[str, Any] = {}
    for label in ("G0", "G1"):
        try:
            levels[label] = _verify_level(result / "raw" / f"{label}.npz", configuration, geometry_source)
        except (OSError, ValueError, KeyError, IndexError, TypeError,
                np.linalg.LinAlgError, ZeroDivisionError) as error:
            levels[label] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    complete = all("peak_lumen_fraction_change" in level for level in levels.values())
    difference = (abs(levels["G1"]["peak_lumen_fraction_change"]
                      - levels["G0"]["peak_lumen_fraction_change"]) if complete else None)
    try:
        materials_frozen = all(
            abs(float(configuration["materials"][name]["young"]) - young) <= _TOLERANCE
            and abs(float(configuration["materials"][name]["poisson"]) - 0.30) <= _TOLERANCE
            for name, young in _MATERIALS.items())
        length_scale = float(configuration["geometry"]["length_scale_um"])
        valid_scale = bool(np.isfinite(length_scale) and length_scale > 0)
    except (KeyError, ValueError, TypeError):
        materials_frozen, valid_scale = False, False
    try:
        source_iou = float(geometry["source_mask_iou"])
        hausdorff = float(geometry["contour_hausdorff_um"])
    except (KeyError, ValueError, TypeError):
        source_iou, hausdorff = float("nan"), float("nan")
    checks = {
        "frozen_three_layer_materials": materials_frozen,
        "positive_physical_length_scale": valid_scale,
        "source_mask_iou_at_least_098": bool(np.isfinite(source_iou) and 0.98 <= source_iou <= 1.0),
        "source_contour_hausdorff_at_most_2um": bool(np.isfinite(hausdorff) and 0 <= hausdorff <= 2.0),
        "both_mesh_levels_independently_verified": all(level["status"] == "passed"
                                                        for level in levels.values()),
        "two_level_lumen_response": difference is not None and difference <= 0.002,
        "source_geometry_independently_verified": geometry_verification["status"] == "passed",
    }
    status = "passed" if all(checks.values()) else "failed"
    report = {
        "schema_version": "prl.fem_measured_contour_verification.v1",
        "status": status,
        "scope": "FEM-only measured 2-D outline with assumed wall layers and active strain",
        "checks": checks, "levels": levels,
        "mesh_peak_lumen_change_absolute_difference": difference,
        "geometry_verification": geometry_verification,
        "geometry_checks_source": "geometry_source.npz; independent scanline raster, pairwise distances and mesh mapping",
        "scientific_gates": {"fem_engineering_feasibility": status,
                             "zebrafish_calibration": "not_run",
                             "biological_validation": "not_run",
                             "fluid_structure_interaction": "not_run"},
        "interpretation": (
            "A pass verifies the declared outline tolerance, independently reassembled "
            "small-strain equilibrium and saved fields. Wall layers, fiber directions, "
            "material constants and activation remain assumptions. Cycle phase is "
            "unscaled load continuation, not physiological time. Pressure is minus "
            "the mean in-plane normal stress; equivalent stress uses the declared "
            "two-dimensional invariant, not the full plane-strain 3-D invariant."
        ),
    }
    if save:
        (result / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
