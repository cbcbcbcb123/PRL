"""Independent F5 audit of periodic Q2/Q1 geometry and retained equilibria.

Only independent verification mathematics is reused. No production geometry,
constitutive, pressure, assembly, or runner module supplies a judgment.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import stat
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from .fem_finite_strain import _energy_derivative, _lagrange_at, _numpy_json_scalar, _stored_energy
from .fem_curved_pressure import _tensor_basis, follower_pressure as _surface_pressure


_LOADS = np.array([0.0, 0.02, 0.04, 0.06, 0.08])
_FRACTIONS = np.array([20 / 27, 21 / 27, 22 / 27, 1.0])
_CASES = [{"name": "radial_coarse", "radial_intervals": [1, 1, 2]},
          {"name": "radial_fine", "radial_intervals": [2, 2, 4]}]
_SOURCE_SHA = "e2f3ac0f68b523bddcc8e33e8a0ab057cf06116a43120653b90139894d06fa21"
_PARENTS = {
    "f2_measured_contour_v01_20260917": ("67503c849d363f78e3148c5f44fe66b67d283b92259efc05b07b3571626b1af7", 32),
    "f4_curved_pressure_v01_20260917": ("566a3caabfbcc672b5a62c5b4b21c6d25ad25a61bcbad29730195d09575d3d4f", 33),
}
_THRESHOLDS = {"mask_iou_min": 0.98, "raw_contour_hausdorff_um_max": 2.0,
    "kinematics_absolute": 1e-10, "stress_absolute": 2e-7, "free_force_residual": 2e-6,
    "pressure_weak_residual": 1e-8, "closed_pressure_resultant_and_moment": 2e-8,
    "gauge_reaction": 2e-6, "pressure_virtual_work_relative": 2e-5,
    "maximum_abs_J_minus_one": 0.01, "minimum_peak_cavity_area_change": 0.01,
    "radial_mesh_peak_absolute_difference": 0.002, "radial_mesh_peak_relative_difference": 0.05,
    "same_reference_domain_relative": 1e-12, "in_plane_z_variation": 1e-10,
    "midplane_average_area_relative": 1e-10, "zero_pressure_stress": 2e-7}
_SOLVER = {"tolerance": 1e-9, "max_iterations": 30, "max_line_search": 16}
_EVIDENCE_BOUNDARY = {
    "schema_version": "prl.fem_contour_pressure_configuration.v1",
    "constraints": {
        "plane_strain": "all displacement-node uz=0",
        "in_plane_gauge": "outer mid-z anchor A: ux=uy=0; half-circumference B: uy=0; B ux free",
        "traction": "current inner-surface pressure; exterior traction-free; no end-cap pressure"},
    "scope": "image-derived outer outline with constructed cavity; passive plane-strain qualification, not a real-heart fit",
    "element": "periodic isoparametric Q2 displacement / continuous Q1 pressure; 3^3 volume and 3^2 surface Gauss",
    "units": "length normalized by 45.10550160766466 um; stress and pressure in uncalibrated mu units; load steps are not physiological time",
    "saved_energy": "internal isochoric material energy density; excludes follower-pressure work"}
_GEOMETRY_BOUNDARY = {
    "source": "72 hpf Fish 4 maximum-occupied XY slice z=39; not a projection",
    "reference_assumption": "static image outline treated as zero-pressure stress-free reference",
    "internal_anatomy": "homothetic cavity and layer interfaces are constructed, not measured"}
_PREFLIGHT = {"source_mask_iou": 0.9946353311213261, "raw_contour_hausdorff_um": 1.2491105980802832,
    "smooth_contour_hausdorff_um": 0.9719503052895044, "area_relative_error": 0.00037816659335643266,
    "minimum_orientation_cross": 0.012672907431171892}


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _check_configuration(configuration: dict[str, Any]) -> None:
    expected = {**_EVIDENCE_BOUNDARY, "solver": _SOLVER,
        "cases": _CASES, "material": {"model": "neo_hookean", "mu": 1.0},
        "kappa": 1000.0, "loads": _LOADS.tolist(), "thresholds": _THRESHOLDS,
        "resources": {"threads": 1, "gpu": 0, "dcm": 0, "seconds": 1200,
                      "stage_bytes": 67108864, "reserve_bytes": 67108864, "automatic_retries": 0}}
    for key, value in expected.items():
        if configuration.get(key) != value:
            raise ValueError(f"frozen scientific configuration changed: {key}")
    geometry = configuration["geometry"]
    expected_geometry = {**_GEOMETRY_BOUNDARY, "segments": 36, "height": 0.5, "radial_boundary_fractions": _FRACTIONS.tolist(),
        "source_result": "results/ventricle_fem/f2_measured_contour_v01_20260917",
        "source_geometry": "results/ventricle_fem/f2_measured_contour_v01_20260917/geometry_source.npz",
        "source_geometry_sha256": _SOURCE_SHA, "frozen_preflight": _PREFLIGHT}
    for key, value in expected_geometry.items():
        if geometry.get(key) != value:
            raise ValueError(f"frozen geometry configuration changed: {key}")


def _curve_segments(nodes: np.ndarray) -> np.ndarray:
    if nodes.ndim != 2 or nodes.shape[1] != 2 or len(nodes) < 6 or len(nodes) % 2:
        raise ValueError("a closed periodic Q2 curve needs an even number of planar control nodes")
    indices = (2 * np.arange(len(nodes) // 2)[:, None] + np.arange(3)[None, :]) % len(nodes)
    return nodes[indices]


def q2_area(nodes: np.ndarray) -> float:
    sites, weights = np.polynomial.legendre.leggauss(3)
    values, derivatives = _lagrange_at(sites, np.array([-1.0, 0.0, 1.0]))
    segments = _curve_segments(nodes)
    positions = np.einsum("qa,sai->sqi", values, segments)
    tangents = np.einsum("qa,sai->sqi", derivatives, segments)
    return float(0.5 * np.sum(weights * (positions[..., 0] * tangents[..., 1] - positions[..., 1] * tangents[..., 0])))


def orientation_minimum(nodes: np.ndarray) -> float:
    """Exact quadratic C(xi) cross C'(xi) minimum over every full segment."""
    segments = _curve_segments(nodes)
    constant = segments[:, 1]
    linear = (segments[:, 2] - segments[:, 0]) / 2.0
    quadratic = (segments[:, 0] + segments[:, 2]) / 2.0 - constant
    cross = lambda first, second: first[..., 0] * second[..., 1] - first[..., 1] * second[..., 0]
    coefficients = np.column_stack((cross(constant, linear), 2.0 * cross(constant, quadratic), cross(linear, quadratic)))
    minima = []
    for zero, one, two in coefficients:
        candidates = [-1.0, 1.0]
        if two != 0.0 and -1.0 < -one / (2.0 * two) < 1.0:
            candidates.append(-one / (2.0 * two))
        minima.append(min(zero + one * value + two * value**2 for value in candidates))
    return float(min(minima))


def _resample(source: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    smooth = source["smooth_contour_um"]
    closed = np.vstack((smooth, smooth[0]))
    arclength = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    query = np.arange(72) * arclength[-1] / 72.0
    image_nodes = np.column_stack([np.interp(query, arclength, closed[:, axis]) for axis in range(2)])
    normalized = (image_nodes - source["center_um"]) / float(source["length_scale_um"])
    direction = normalized[36] - normalized[0]
    direction /= np.linalg.norm(direction)
    rotation = np.array([[direction[0], direction[1]], [-direction[1], direction[0]]])
    return normalized @ rotation.T, rotation


def reference_mesh(source: dict[str, np.ndarray], intervals: list[int]) -> dict[str, np.ndarray]:
    if intervals not in ([1, 1, 2], [2, 2, 4]):
        raise ValueError("radial intervals differ from the two frozen meshes")
    curve, rotation = _resample(source)
    pressure_radial = np.r_[_FRACTIONS[0], np.concatenate([
        np.linspace(_FRACTIONS[layer], _FRACTIONS[layer + 1], intervals[layer] + 1)[1:]
        for layer in range(3)])]
    radial = np.empty(2 * len(pressure_radial) - 1)
    radial[::2] = pressure_radial
    radial[1::2] = (pressure_radial[:-1] + pressure_radial[1:]) / 2.0
    shapes = [(len(radial), 72, 3), (len(pressure_radial), 36, 2)]
    coordinates = []
    for fractions, boundary, zcount in ((radial, curve, 3), (pressure_radial, curve[::2], 2)):
        coordinates.append(np.array([[fraction * point[0], fraction * point[1], z]
            for fraction, point, z in itertools.product(fractions, boundary, np.linspace(0.0, 0.5, zcount))]))
    grids = [np.arange(np.prod(shape)).reshape(shape) for shape in shapes]
    cells, pressure_cells = [], []
    for radial_index, circumferential in itertools.product(range(len(pressure_radial) - 1), range(36)):
        for order, grid, collection, count in ((2, grids[0], cells, 72), (1, grids[1], pressure_cells, 36)):
            collection.append([grid[order * radial_index + first, (order * circumferential + second) % count, third]
                               for first, second, third in itertools.product(range(order + 1), repeat=3)])
    anchors = np.array([grids[0][-1, 0, 1], grids[0][-1, 36, 1]])
    fixed = np.unique(np.r_[np.arange(2, 3 * len(coordinates[0]), 3), 3 * anchors[0], 3 * anchors[0] + 1, 3 * anchors[1] + 1])
    return {"coordinates": coordinates[0], "pressure_coordinates": coordinates[1],
        "cells": np.asarray(cells), "pressure_cells": np.asarray(pressure_cells), "fixed_dofs": fixed,
        "inner_faces": np.column_stack((np.arange(36), np.zeros(36, dtype=int), -np.ones(36, dtype=int))),
        "layer_ids": np.repeat(np.repeat(np.arange(3), intervals), 36),
        "radial_fractions": radial, "pressure_radial_fractions": pressure_radial,
        "radial_boundary_fractions": _FRACTIONS.copy(), "outer_curve_q2": curve,
        "source_to_solver_rotation": rotation, "image_center_um": source["center_um"].copy(),
        "length_scale_um": np.asarray(source["length_scale_um"]), "height": np.asarray(0.5),
        "node_shape": np.asarray(shapes[0]), "pressure_shape": np.asarray(shapes[1]),
        "inner_midplane_nodes": grids[0][0, :, 1], "outer_midplane_nodes": grids[0][-1, :, 1],
        "anchor_node_ids": anchors}


def _dense_curve(nodes: np.ndarray, maximum_step: float) -> np.ndarray:
    dense = []
    for segment in _curve_segments(nodes):
        first = (segment[2] - segment[0]) / 2.0
        second = (segment[0] + segment[2]) / 2.0 - segment[1]
        bound = max(np.linalg.norm(first - 2.0 * second), np.linalg.norm(first + 2.0 * second))
        count = max(8, int(np.ceil(2.0 * bound / maximum_step)))
        sites = np.linspace(-1.0, 1.0, count, endpoint=False)
        dense.append(segment[1] + sites[:, None] * first + sites[:, None] ** 2 * second)
    return np.concatenate(dense)


def _mask_iou(nodes_pixels: np.ndarray, mask: np.ndarray) -> float:
    """Independent integer-pixel scanline rasterization of the sampled Q2 curve."""
    following = np.roll(nodes_pixels, -1, axis=0)
    raster = np.zeros(mask.shape, dtype=bool)
    for row in range(max(0, int(np.ceil(nodes_pixels[:, 1].min()))), min(mask.shape[0], int(np.floor(nodes_pixels[:, 1].max())) + 1)):
        crosses = (nodes_pixels[:, 1] > row) != (following[:, 1] > row)
        left, right = nodes_pixels[crosses], following[crosses]
        crossing = np.sort(left[:, 0] + (row - left[:, 1]) * (right[:, 0] - left[:, 0]) / (right[:, 1] - left[:, 1]))
        if len(crossing) % 2:
            raise ValueError("odd crossing count in source-contour scanline")
        for first, second in crossing.reshape(-1, 2):
            begin, end = max(0, int(np.ceil(first))), min(mask.shape[1], int(np.floor(second)) + 1)
            if end > begin:
                raster[row, begin:end] = True
    union = np.sum(raster | mask)
    if union == 0:
        raise ValueError("empty image/curve union")
    return float(np.sum(raster & mask) / union)


def source_diagnostics(source: dict[str, np.ndarray]) -> dict[str, Any]:
    curve, rotation = _resample(source)
    image_curve = curve @ rotation * float(source["length_scale_um"]) + source["center_um"]
    dense = _dense_curve(image_curve, 0.05)
    raw, smooth = source["raw_contour_um"], source["smooth_contour_um"]
    distances = lambda points: max(float(cKDTree(points).query(dense)[0].max()), float(cKDTree(dense).query(points)[0].max()))
    mask_iou = _mask_iou(dense / source["voxel_um"][:2], source["slice_mask"].astype(bool))
    smooth_area = 0.5 * np.sum(smooth[:, 0] * np.roll(smooth[:, 1], -1) - smooth[:, 1] * np.roll(smooth[:, 0], -1))
    minimum = orientation_minimum(curve)
    raw_distance = distances(raw)
    metrics = {"source_mask_iou": mask_iou, "raw_contour_hausdorff_um": raw_distance,
        "smooth_contour_hausdorff_um": distances(smooth),
        "area_relative_error": abs(q2_area(image_curve) / smooth_area - 1.0),
        "minimum_orientation_cross": minimum}
    return {"status": "passed" if mask_iou >= _THRESHOLDS["mask_iou_min"] and raw_distance <= _THRESHOLDS["raw_contour_hausdorff_um_max"] and minimum > 0 else "failed",
        **metrics, "distance_sampling_max_step_um": 0.05,
        "measurement_method": "Independent adaptive Q2 sampling with maximum arc-step bound 0.05 um; symmetric nearest-point sampled Hausdorff distance; integer-pixel scanline IoU; exact Q2 signed area; analytic whole-segment orientation minimum.",
        "preflight_comparison_method": "Frozen preflight is provenance, not a bitwise target. Sampling-density and exact-Q2 versus sampled-polygon area differences are reported; acceptance uses the frozen scientific thresholds.",
        "frozen_preflight": dict(_PREFLIGHT),
        "independent_minus_frozen_preflight": {key: metrics[key] - value for key, value in _PREFLIGHT.items()},
        "scope": "outer outline only; cavity, wall interfaces and unstressed state are assumptions"}


def _bezier(segment: np.ndarray) -> np.ndarray:
    return np.array([segment[0], 2.0 * segment[1] - (segment[0] + segment[2]) / 2.0, segment[2]])


def _split(curve: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left, right = (curve[0] + curve[1]) / 2.0, (curve[1] + curve[2]) / 2.0
    middle = (left + right) / 2.0
    return np.array([curve[0], left, middle]), np.array([middle, right, curve[2]])


def _disjoint(first: np.ndarray, second: np.ndarray, shared=None, depth: int = 0) -> bool:
    if np.any(first.max(axis=0) < second.min(axis=0)) or np.any(second.max(axis=0) < first.min(axis=0)):
        return True
    if shared is not None and max(np.max(np.linalg.norm(first - shared, axis=1)), np.max(np.linalg.norm(second - shared, axis=1))) < 1.0e-9:
        return True
    first_size = float(np.linalg.norm(np.ptp(first, axis=0)))
    second_size = float(np.linalg.norm(np.ptp(second, axis=0)))
    if max(first_size, second_size) < 1.0e-10 or depth >= 80:
        return False  # Unresolved proximity is rejected, never silently called disjoint.
    if first_size >= second_size:
        return all(_disjoint(piece, second, shared, depth + 1) for piece in _split(first))
    return all(_disjoint(first, piece, shared, depth + 1) for piece in _split(second))


def _winding(curve: np.ndarray, point: np.ndarray) -> int:
    winding = 0
    for segment in _curve_segments(curve):
        constant = segment[1] - point
        linear = (segment[2] - segment[0]) / 2.0
        quadratic = (segment[0] + segment[2]) / 2.0 - segment[1]
        coefficients = np.trim_zeros(np.array([quadratic[1], linear[1], constant[1]]), "f")
        roots = np.roots(coefficients) if len(coefficients) > 1 else []
        for root in roots:
            if abs(np.imag(root)) > 1.0e-10:
                continue
            value = float(np.real(root))
            if -1.0 <= value < 1.0:
                x = constant[0] + linear[0] * value + quadratic[0] * value**2
                slope = linear[1] + 2.0 * quadratic[1] * value
                if x > 0 and abs(slope) > 1.0e-12:
                    winding += 1 if slope > 0 else -1
    return winding


def boundary_safety(inner: np.ndarray, outer: np.ndarray) -> bool:
    """Bezier convex-hull subdivision excludes intersections away from shared ends."""
    collections = []
    for curve in (inner, outer):
        segments = _curve_segments(curve)
        for segment in segments:
            linear = (segment[2] - segment[0]) / 2.0
            twice_quadratic = segment[0] + segment[2] - 2.0 * segment[1]
            denominator = np.dot(twice_quadratic, twice_quadratic)
            value = np.clip(-np.dot(linear, twice_quadratic) / denominator, -1.0, 1.0) if denominator > 0 else 0.0
            if np.linalg.norm(linear + value * twice_quadratic) <= 1.0e-12:
                return False
        beziers = [_bezier(segment) for segment in segments]
        for first in range(len(beziers)):
            for second in range(first + 1, len(beziers)):
                shared = None
                if second == first + 1:
                    shared = segments[first, 2]
                elif first == 0 and second == len(beziers) - 1:
                    shared = segments[first, 0]
                if not _disjoint(beziers[first], beziers[second], shared):
                    return False
        collections.append(beziers)
    if any(not _disjoint(first, second) for first in collections[0] for second in collections[1]):
        return False
    return _winding(outer, inner[0]) == 1 and _winding(inner, outer[0]) == 0


def _quadrature(payload: dict[str, np.ndarray], expected: dict[str, np.ndarray]) -> dict[str, Any]:
    for field, value in expected.items():
        actual = payload.get(field)
        if actual is None or actual.shape != value.shape or actual.dtype.kind not in "iuf" or not np.all(np.isfinite(actual)):
            raise ValueError(f"invalid frozen mesh field: {field}")
        if value.dtype.kind in "iu":
            equal = actual.dtype.kind in "iu" and np.array_equal(actual, value)
        else:
            equal = np.max(np.abs(actual - value)) <= 1.0e-12
        if not equal:
            raise ValueError(f"saved {field} differs from independently reconstructed frozen mesh")
    sites, weights = np.polynomial.legendre.leggauss(3)
    indices = np.array(list(itertools.product(range(3), repeat=3)))
    values, derivatives = _tensor_basis(sites[indices], 2)
    pressure_values = _tensor_basis(sites[indices], 1)[0]
    cells = expected["cells"]
    jacobians = np.einsum("eai,qaj->eqij", payload["coordinates"][cells], derivatives)
    determinant = np.linalg.det(jacobians)
    if np.any(determinant <= 0) or not np.all(np.isfinite(determinant)):
        raise ValueError("nonpositive/nonfinite reference Jacobian")
    gradient = np.einsum("qaj,eqji->eqai", derivatives, np.linalg.inv(jacobians))
    surface_indices = np.array(list(itertools.product(range(3), repeat=2)))
    surface_values, surface_derivatives = _tensor_basis(np.column_stack((-np.ones(9), sites[surface_indices])), 2)
    volume_weights = determinant * np.prod(weights[indices], axis=1)
    inner = expected["outer_curve_q2"] * _FRACTIONS[0]
    outer = expected["outer_curve_q2"]
    safe = boundary_safety(inner, outer)
    inner_area, outer_area = q2_area(inner), q2_area(outer)
    reference_volume = float(np.sum(volume_weights))
    exact_volume = 0.5 * (outer_area - inner_area)
    return {"cells": cells, "pressure_cells": expected["pressure_cells"], "pressure_basis": pressure_values,
        "gradients": gradient, "weights": volume_weights, "basis": values,
        "inner_faces": expected["inner_faces"], "face_basis": surface_values,
        "face_derivatives": surface_derivatives, "face_weights": np.prod(weights[surface_indices], axis=1),
        "geometry": {"status": "passed" if safe and abs(reference_volume / exact_volume - 1.0) <= _THRESHOLDS["same_reference_domain_relative"] else "failed",
            "reference_inner_area": inner_area, "reference_outer_area": outer_area,
            "reference_volume": reference_volume, "area_based_reference_volume": exact_volume,
            "minimum_reference_determinant": float(np.min(determinant)), "boundary_safety": safe,
            "minimum_orientation_cross": orientation_minimum(outer),
            "curve_separation_method": "Bezier convex-hull subdivision; unresolved proximity rejected; shared endpoints within 1e-9",
            "periodic_Q2_Q1_topology_and_gauge_match": True}}


def _area_average(boundary: np.ndarray) -> float:
    sites, weights = np.polynomial.legendre.leggauss(3)
    values = _lagrange_at(sites, np.array([-1.0, 0.0, 1.0]))[0]
    sections = np.einsum("qz,nzi->qni", values, boundary)
    return float(np.dot(weights, [q2_area(section[:, :2]) for section in sections]) / 2.0)


def _state(payload: dict[str, np.ndarray], index: int, quadrature: dict[str, Any]) -> dict[str, Any]:
    points, cells = payload["coordinates"], quadrature["cells"]
    displacement = payload["displacements"][index]
    current = points + displacement
    pressure = np.einsum("qb,eb->eq", quadrature["pressure_basis"], payload["pressure_dofs"][index][quadrature["pressure_cells"]])
    F = np.eye(3) + np.einsum("eai,eqaj->eqij", displacement[cells], quadrature["gradients"])
    J = np.linalg.det(F)
    if np.any(J <= 0) or not np.all(np.isfinite(J)):
        raise ValueError("current deformation has nonpositive/nonfinite determinant")
    material, fiber = {"model": "neo_hookean", "mu": 1.0}, np.array([1.0, 0.0, 0.0])
    P = _energy_derivative(F, pressure, material, fiber, 0.0)
    green = (np.einsum("eqki,eqkj->eqij", F, F) - np.eye(3)) / 2.0
    cauchy = np.einsum("eqik,eqjk->eqij", P, F) / J[..., None, None]
    energy = _stored_energy(F, material, fiber, 0.0)
    errors = {name: float(np.max(np.abs(payload[name][index] - value))) for name, value in
              {"F": F, "J": J, "Green": green, "P": P, "Cauchy": cauchy, "energy": energy}.items()}
    external = _surface_pressure(payload, displacement, float(_LOADS[index]), quadrature)["force"]
    internal = np.zeros_like(points)
    local = np.einsum("eqij,eqaj,eq->eai", P, quadrature["gradients"], quadrature["weights"])
    np.add.at(internal, cells.ravel(), local.reshape(-1, 3))
    residual = (internal - external).ravel()
    weak = np.zeros(len(payload["pressure_coordinates"]))
    local_weak = np.einsum("qb,eq,eq->eb", quadrature["pressure_basis"], J - 1.0 - pressure / 1000.0, quadrature["weights"])
    np.add.at(weak, quadrature["pressure_cells"].ravel(), local_weak.ravel())
    free = np.ones(3 * len(points), dtype=bool)
    fixed = payload["fixed_dofs"].astype(int)
    free[fixed] = False
    gauge = fixed[fixed % 3 != 2]
    resultant = float(np.linalg.norm(np.sum(external, axis=0)))
    moment = float(np.sum(np.cross(current, external), axis=0)[2])
    gauge_reaction = float(np.linalg.norm(residual[gauge]))
    free_norm, weak_norm = float(np.linalg.norm(residual[free])), float(np.linalg.norm(weak))
    grid = current.reshape((*payload["node_shape"].astype(int), 3))
    inner = current[payload["inner_midplane_nodes"], :2]
    outer = current[payload["outer_midplane_nodes"], :2]
    inner_area, outer_area = q2_area(inner), q2_area(outer)
    average = _area_average(grid[0])
    z_variation = float(np.max(np.abs(displacement.reshape(grid.shape)[..., :2] - displacement.reshape(grid.shape)[:, :, 1:2, :2])))
    area_difference = abs(inner_area / average - 1.0)
    virtual = current * np.array([0.01, 0.007, 0.0])
    step = 1.0e-4
    virtual_grid = virtual.reshape(grid.shape)
    area_derivative = (_area_average(grid[0] + step * virtual_grid[0]) - _area_average(grid[0] - step * virtual_grid[0])) / (2.0 * step)
    nodal_work = float(np.sum(external * virtual))
    volume_work = float(_LOADS[index] * 0.5 * area_derivative)
    work_error = abs(nodal_work - volume_work) / max(abs(nodal_work), abs(volume_work), 1.0e-14) if index else abs(nodal_work - volume_work)
    safe = quadrature["geometry"]["boundary_safety"] if np.max(np.abs(displacement)) == 0 else boundary_safety(inner, outer)
    field_checks = {"kinematics_and_energy_recomputed": max(errors[key] for key in ("F", "J", "Green", "energy")) <= 1e-10,
        "stress_recomputed": max(errors[key] for key in ("P", "Cauchy")) <= 2e-7,
        "current_external_force_recomputed": float(np.max(np.abs(payload["external_forces"][index] - external.ravel()))) <= 1e-10,
        "reaction_recomputed": float(np.max(np.abs(payload["reaction"][index] - residual))) <= 2e-6,
        "zero_fixed_values_and_prescribed_displacements": bool(np.all(payload["fixed_values"][index] == 0)) and float(np.max(np.abs(displacement.ravel()[fixed]))) <= 1e-10,
        "plane_strain_in_plane_z_independence": z_variation <= _THRESHOLDS["in_plane_z_variation"],
        "midplane_represents_area_average": area_difference <= _THRESHOLDS["midplane_average_area_relative"]}
    if index == 0:
        field_checks["zero_load_unstressed_reference"] = max(float(np.max(np.abs(P))), float(np.max(np.abs(cauchy)))) <= _THRESHOLDS["zero_pressure_stress"] and float(np.max(np.abs(displacement))) <= 1e-10 and float(np.max(np.abs(payload["pressure_dofs"][0]))) <= 1e-10
    force_checks = {"free_force_residual": free_norm <= 2e-6, "pressure_weak_residual": weak_norm <= 1e-8,
        "saved_newton_residual": 0 <= float(payload["newton_residual"][index]) <= _SOLVER["tolerance"],
        "closed_pressure_resultant": resultant <= 2e-8, "closed_pressure_moment": abs(moment) <= 2e-8,
        "gauge_reaction": gauge_reaction <= 2e-6, "pressure_virtual_work": work_error <= (2e-5 if index else 1e-12)}
    geometry_checks = {"positive_J": True, "maximum_local_volume_change": float(np.max(np.abs(J - 1.0))) <= 0.01,
                       "simple_nested_closed_curves": safe, "positive_inner_outer_areas": outer_area > inner_area > 0}
    return {"load": float(_LOADS[index]), "field_checks": field_checks, "force_checks": force_checks,
        "geometry_checks": geometry_checks, "fields_status": "passed" if all(field_checks.values()) else "failed",
        "equilibrium_status": "passed" if all(force_checks.values()) else "failed",
        "geometry_status": "passed" if all(geometry_checks.values()) else "failed",
        "cavity_area": inner_area, "outer_area": outer_area, "height_average_cavity_area": average,
        "cavity_area_change_fraction": inner_area / quadrature["geometry"]["reference_inner_area"] - 1.0,
        "outer_area_change_fraction": outer_area / quadrature["geometry"]["reference_outer_area"] - 1.0,
        "maximum_abs_J_minus_one": float(np.max(np.abs(J - 1.0))), "minimum_J": float(np.min(J)),
        "free_force_residual": free_norm, "pressure_weak_residual": weak_norm,
        "pressure_resultant_norm": resultant, "pressure_moment_z": moment,
        "gauge_reaction_norm": gauge_reaction, "virtual_work_relative_error": work_error,
        "pressure_nodal_virtual_work": nodal_work, "pressure_volume_virtual_work": volume_work,
        "maximum_in_plane_z_variation": z_variation, "midplane_average_area_relative_difference": area_difference,
        "maximum_abs_cauchy": float(np.max(np.abs(cauchy))), "saved_field_errors": errors}


def verify_contour_case(payload: dict[str, np.ndarray], source: dict[str, np.ndarray], intervals: list[int], history: list[Any]) -> dict[str, Any]:
    expected = reference_mesh(source, intervals)
    quadrature = _quadrature(payload, expected)
    nodes, elements, pressures = len(expected["coordinates"]), len(expected["cells"]), len(expected["pressure_coordinates"])
    shapes = {"loads": (5,), "displacements": (5, nodes, 3), "pressure_dofs": (5, pressures),
        "initial_vectors": (5, 3 * nodes + pressures), "fixed_values": (5, len(expected["fixed_dofs"])),
        "external_forces": (5, 3 * nodes), "reaction": (5, 3 * nodes), "newton_residual": (5,),
        "J": (5, elements, 27), "energy": (5, elements, 27)}
    shapes.update({key: (5, elements, 27, 3, 3) for key in ("F", "P", "Cauchy", "Green")})
    for name, shape in shapes.items():
        value = payload.get(name)
        if value is None or value.shape != shape or value.dtype.kind not in "iuf" or not np.all(np.isfinite(value)):
            raise ValueError(f"missing/partial/nonfinite/nonreal raw state: {name}")
    if not np.array_equal(payload["loads"], _LOADS):
        raise ValueError("raw loads differ from the frozen five-pressure ramp")
    previous = np.concatenate((payload["displacements"][:-1].reshape(4, -1), payload["pressure_dofs"][:-1]), axis=1)
    initial = np.vstack((np.zeros((1, 3 * nodes + pressures)), previous))
    if not np.array_equal(initial, payload["initial_vectors"]):
        raise ValueError("initial state chain is not zero then the preceding complete equilibrium")
    if not isinstance(history, list) or len(history) != 5:
        raise ValueError("five Newton history lists are required")
    history_passed = []
    for index, records in enumerate(history):
        if not isinstance(records, list) or not records:
            raise ValueError("empty/invalid Newton history")
        residuals = np.asarray([row["normalized_free_residual"] for row in records], dtype=float)
        history_passed.append(bool(np.all(np.isfinite(residuals)) and np.all(residuals >= 0) and np.all(np.diff(residuals) < 0)
            and [row["iteration"] for row in records] == list(range(len(records))) and len(records) <= _SOLVER["max_iterations"] + 1
            and records[0]["step_length"] == 0 and records[0]["line_search_trials"] == 0
            and all(np.isfinite(row["min_J"]) and row["min_J"] > 0 for row in records)
            and all(np.isfinite(row["step_length"]) and 0 < row["step_length"] <= 1
                    and row["line_search_trials"] == int(row["line_search_trials"]) and 1 <= row["line_search_trials"] <= _SOLVER["max_line_search"] for row in records[1:])
            and residuals[-1] <= _SOLVER["tolerance"] and abs(residuals[-1] - payload["newton_residual"][index]) <= 1e-14
            and abs(records[-1]["min_J"] - float(np.min(payload["J"][index]))) <= 1e-10))
    states = [_state(payload, index, quadrature) for index in range(5)]
    gates = {"reference_geometry": quadrature["geometry"]["status"],
             "history_initial_chain": "passed" if all(history_passed) else "failed"}
    gates.update({name: "passed" if all(state[f"{name}_status"] == "passed" for state in states) else "failed"
                  for name in ("geometry", "fields", "equilibrium")})
    gates["monotone_cavity_response"] = "passed" if np.all(np.diff([state["cavity_area"] for state in states]) > 0) else "failed"
    return {"status": "passed" if all(value == "passed" for value in gates.values()) else "failed",
        "gates": gates, "geometry": quadrature["geometry"], "states": states, "peak": states[-1],
        "history_checks": history_passed, "initial_chain_bitwise_identical": True,
        "scope": "only radial refinement; no circumferential or local stress convergence claim"}


def _protected_evidence(package: Path) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    reports = {}
    for name, (expected_hash, expected_count) in _PARENTS.items():
        directory = package.parent / name
        manifest_path = directory / "manifest.json"
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"protected parent manifest changed: {name}")
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
        if len(entries) != expected_count or len({row["path"] for row in entries}) != expected_count:
            raise ValueError("protected manifest count or uniqueness changed")
        for entry in entries:
            unresolved = directory / entry["path"]
            chain = [unresolved, *[path for path in unresolved.parents if path == directory or path.is_relative_to(directory)]]
            if any(path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024) for path in chain):
                raise ValueError("protected evidence contains a link")
            target = unresolved.resolve()
            if not target.is_relative_to(directory.resolve()) or target.stat().st_size != entry["bytes"] or hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"protected evidence content/path changed: {name}/{entry['path']}")
        reports[name] = {"status": "passed", "manifest_sha256": expected_hash, "verified_files": expected_count}
    for name in ("protected_evidence_preflight.json", "protected_evidence_postflight.json"):
        if json.loads((package / name).read_text(encoding="utf-8")) != reports:
            raise ValueError(f"protected record does not match independent audit: {name}")
    source_path = package.parent / "f2_measured_contour_v01_20260917/geometry_source.npz"
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != _SOURCE_SHA:
        raise ValueError("F2 geometry source hash differs from frozen input")
    original, source = _load(source_path), _load(package / "geometry_input.npz")
    if set(original) != set(source) or not all(np.array_equal(original[name], source[name]) for name in original):
        raise ValueError("retained geometry input arrays differ from protected F2 source")
    return {"status": "passed", "packages": reports, "geometry_input_arrays_bitwise_equal": True}, source


def verify_fem_contour_pressure(result: Path | str, save: bool = True) -> dict[str, Any]:
    package = Path(result)
    gates, cases, extra = {}, {}, {}
    try:
        _check_configuration(json.loads((package / "configuration.json").read_text(encoding="utf-8")))
        gates["configuration"] = "passed"
        protected, source = _protected_evidence(package)
        extra["protected_evidence"] = protected
        gates["protected_evidence"] = protected["status"]
        extra["source_geometry"] = source_diagnostics(source)
        gates["source_geometry"] = extra["source_geometry"]["status"]
        for case in _CASES:
            name = case["name"]
            try:
                raw = _load(package / "raw" / f"{name}.npz")
                history = json.loads((package / "raw" / f"{name}_newton.json").read_text(encoding="utf-8"))
                cases[name] = verify_contour_case(raw, source, case["radial_intervals"], history)
            except (ValueError, KeyError, OSError, TypeError, IndexError, FloatingPointError) as error:
                cases[name] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
        for name in ("reference_geometry", "history_initial_chain", "geometry", "fields", "equilibrium", "monotone_cavity_response"):
            gates[name] = "passed" if all(case.get("gates", {}).get(name) == "passed" for case in cases.values()) else "failed"
        if all("states" in cases[name] for name in ("radial_coarse", "radial_fine")):
            coarse, fine = cases["radial_coarse"], cases["radial_fine"]
            differences = {key: abs(coarse["geometry"][key] / fine["geometry"][key] - 1.0)
                           for key in ("reference_inner_area", "reference_outer_area", "reference_volume")}
            first, second = coarse["peak"]["cavity_area_change_fraction"], fine["peak"]["cavity_area_change_fraction"]
            absolute = abs(first - second)
            relative = absolute / max(abs(second), 1e-14)
            checks = {"same_reference_domain": max(differences.values()) <= _THRESHOLDS["same_reference_domain_relative"],
                      "fine_peak_minimum_response": second >= 0.01,
                      "absolute_response_difference": absolute <= 0.002,
                      "relative_response_difference": relative <= 0.05}
            extra["mesh_comparison"] = {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
                "reference_relative_differences": differences,
                "coarse_peak_cavity_area_change_fraction": first, "fine_peak_cavity_area_change_fraction": second,
                "absolute_difference": absolute, "relative_difference": relative,
                "scope": "radial refinement only; fixed circumferential geometry"}
            gates["radial_mesh_response"] = extra["mesh_comparison"]["status"]
        else:
            gates["radial_mesh_response"] = "failed"
    except (ValueError, KeyError, OSError, TypeError, IndexError, FloatingPointError) as error:
        gates["input_audit"] = "failed"
        extra["audit_error"] = f"{type(error).__name__}: {error}"
    required = {"configuration", "protected_evidence", "source_geometry", "reference_geometry", "history_initial_chain",
                "geometry", "fields", "equilibrium", "monotone_cavity_response", "radial_mesh_response"}
    passed = required.issubset(gates) and all(value == "passed" for value in gates.values())
    report = {"schema_version": "prl.fem_contour_pressure_verification.v1", "status": "passed" if passed else "failed",
        "gates": gates, "cases": cases, **extra,
        "scientific_scope": "image-derived outer outline; assumed cavity/interfaces/unstressed reference; passive plane-strain only",
        "not_run": ["measured_cavity", "measured_wall_thickness", "material_calibration", "physiological_time",
                    "free_3d_heart", "active_contraction_on_this_outline", "blood_flow", "growth", "ECM_feedback",
                    "circumferential_convergence", "local_peak_stress_convergence"]}
    serialized = json.dumps(report, indent=2, allow_nan=False, default=_numpy_json_scalar)
    if save:
        (package / "verification.json").write_text(serialized + "\n", encoding="utf-8")
    return json.loads(serialized)
