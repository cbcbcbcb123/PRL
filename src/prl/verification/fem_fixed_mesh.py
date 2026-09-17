"""Independent audit of a fixed-geometry, fixed-load FEM refinement experiment.

No assembler, solver, or runner implementation is imported.  Engineering
consistency, response convergence, and small-strain applicability are separate
decisions; a small algebraic residual does not override either science gate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse


_TOLERANCE = 1.0e-10
_MATERIALS = {"endocardium": 1.0, "ecm": 0.5, "myocardium": 2.5}
_REQUIRED = ("coordinates", "cells", "cell_layers", "inner_nodes", "outer_nodes",
             "phases", "activation", "displacements", "strains", "stresses",
             "equivalent_stress", "pressure", "lumen_area", "outer_area",
             "stored_energy", "active_strain_unit", "active_tangents", "source_cells")


def _maximum_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(actual - expected)))


def _polygon_area(points: np.ndarray) -> float:
    other = np.roll(points, -1, axis=0)
    return float(np.sum(points[:, 0] * other[:, 1] - points[:, 1] * other[:, 0]) / 2)


def _load(path: Path, required: tuple[str, ...] = _REQUIRED) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as package:
        arrays = {name: np.asarray(package[name]) for name in required}
        if "parent_cells" in package:
            arrays["parent_cells"] = np.asarray(package["parent_cells"])
    if not all(np.issubdtype(value.dtype, np.number) and np.all(np.isfinite(value))
               for value in arrays.values()):
        raise ValueError("All required saved arrays must be numeric and finite")
    return arrays


def _boundary_matches(cells: np.ndarray, inner: np.ndarray, outer: np.ndarray) -> bool:
    edges = np.concatenate((cells[:, [0, 1]], cells[:, [1, 2]], cells[:, [2, 0]]))
    unique, incidence = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    actual = {tuple(edge) for edge in unique[incidence == 1]}
    expected: set[tuple[int, int]] = set()
    for cycle in (inner, outer):
        if len(cycle) < 3 or len(np.unique(cycle)) != len(cycle):
            return False
        expected.update(tuple(sorted((int(first), int(second))))
                        for first, second in zip(cycle, np.roll(cycle, -1)))
    return bool(np.all(incidence <= 2) and actual == expected
                and len(expected) == len(inner) + len(outer)
                and not np.intersect1d(inner, outer).size)


def _boundary_distance(points: np.ndarray, reference: np.ndarray) -> float:
    """Maximum distance to a source polygon's exact line segments, not vertices."""
    directions = np.roll(reference, -1, axis=0) - reference
    squared_lengths = np.sum(directions * directions, axis=1)
    if np.any(squared_lengths <= 0):
        raise ValueError("Source boundary contains a zero-length edge")
    maximum = 0.0
    for offset in range(0, len(points), 256):
        delta = points[offset:offset + 256, None, :] - reference[None, :, :]
        fraction = np.clip(np.einsum("psd,sd->ps", delta, directions)
                           / squared_lengths, 0.0, 1.0)
        difference = delta - fraction[:, :, None] * directions
        maximum = max(maximum, float(np.sqrt(np.sum(difference ** 2, axis=2))
                                     .min(axis=1).max()))
    return maximum


def _verify_fixed_geometry(arrays: dict[str, np.ndarray], source: dict[str, np.ndarray],
                           index: int, areas: np.ndarray) -> dict[str, Any]:
    coordinates, cells = arrays["coordinates"], arrays["cells"].astype(np.int64)
    source_coordinates = source["coordinates"]
    source_connectivity = source["cells"].astype(np.int64)
    ancestry = arrays["source_cells"].astype(np.int64)
    count, source_count = len(cells), len(source_connectivity)
    if ancestry.shape != (count,) or np.any(ancestry < 0) or np.any(ancestry >= source_count):
        raise ValueError("source_cells must map each triangle into the frozen source")
    source_points = source_coordinates[source_connectivity]
    source_affine = np.concatenate((np.ones((source_count, 3, 1)), source_points), axis=2)
    source_areas = np.linalg.det(source_affine) / 2
    if np.any(source_areas <= 0):
        raise ValueError("Frozen source contains a nonpositive triangle")
    child_points = coordinates[cells]
    homogeneous = np.concatenate((np.ones((count, 3, 1)), child_points), axis=2)
    barycentric = np.einsum("mvi,mij->mvj", homogeneous,
                             np.linalg.inv(source_affine)[ancestry])
    partition_areas = np.bincount(ancestry, weights=areas, minlength=source_count)
    expected_parts = 4 ** index
    area_error = _maximum_error(partition_areas, source_areas)
    inherited_active_error = _maximum_error(arrays["active_strain_unit"],
                                            source["active_strain_unit"][ancestry])
    inherited_tangent_error = _maximum_error(arrays["active_tangents"],
                                             source["active_tangents"][ancestry])
    layer_area_error = _maximum_error(
        np.bincount(arrays["cell_layers"].astype(int), weights=areas, minlength=3),
        np.bincount(source["cell_layers"].astype(int), weights=source_areas, minlength=3))
    distances, boundary_area_errors, boundary_identity = {}, {}, True
    for boundary in ("inner_nodes", "outer_nodes"):
        points = coordinates[arrays[boundary].astype(int)]
        reference = source_coordinates[source[boundary].astype(int)]
        distances[boundary] = max(_boundary_distance(points, reference),
                                  _boundary_distance(reference, points))
        boundary_area_errors[boundary] = abs(_polygon_area(points) - _polygon_area(reference))
        boundary_identity = bool(boundary_identity and len(points) == len(reference) * 2 ** index)
    child_size_error = _maximum_error(areas, source_areas[ancestry] / expected_parts)
    lattice_error = _maximum_error(barycentric * 2 ** index,
                                   np.rint(barycentric * 2 ** index))
    checks = {
        "four_way_cell_count_and_ancestry": bool(
            count == source_count * expected_parts
            and np.all(np.bincount(ancestry, minlength=source_count) == expected_parts)),
        "all_child_vertices_within_frozen_source_triangle": bool(
            np.min(barycentric) >= -_TOLERANCE and np.max(barycentric) <= 1 + _TOLERANCE),
        "child_vertices_on_nested_midpoint_lattice": lattice_error <= _TOLERANCE,
        "uniform_child_areas": child_size_error <= _TOLERANCE,
        "each_source_triangle_area_preserved": area_error <= _TOLERANCE,
        "three_layer_areas_preserved": layer_area_error <= _TOLERANCE,
        "boundary_segment_geometry_preserved": max(distances.values()) <= _TOLERANCE,
        "boundary_areas_preserved": max(boundary_area_errors.values()) <= _TOLERANCE,
        "boundary_refinement_count": boundary_identity,
        "material_labels_exactly_inherited": bool(np.array_equal(
            arrays["cell_layers"], source["cell_layers"][ancestry])),
        "active_tensor_exactly_inherited": bool(np.array_equal(
            arrays["active_strain_unit"], source["active_strain_unit"][ancestry])),
        "active_tangents_exactly_inherited": bool(np.array_equal(
            arrays["active_tangents"], source["active_tangents"][ancestry])),
        "source_nodes_are_identical_prefix": bool(np.array_equal(
            coordinates[:len(source_coordinates)], source_coordinates)),
    }
    if index == 0:
        checks["baseline_source_arrays_identical"] = all(
            np.array_equal(arrays[name], source[name]) for name in (
                "coordinates", "cells", "cell_layers", "inner_nodes", "outer_nodes",
                "active_strain_unit", "active_tangents"))
        checks["baseline_identity_ancestry"] = np.array_equal(ancestry, np.arange(source_count))
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "maximum_source_triangle_area_error": area_error,
            "maximum_layer_area_error": layer_area_error,
            "maximum_child_area_error": child_size_error,
            "maximum_barycentric_lattice_error": lattice_error,
            "boundary_segment_distance": distances,
            "boundary_area_errors": boundary_area_errors,
            "maximum_active_tensor_inheritance_error": inherited_active_error,
            "maximum_active_tangent_inheritance_error": inherited_tangent_error}


def _verify_parent_refinement(arrays: dict[str, np.ndarray], previous: dict[str, np.ndarray]) -> dict[str, Any]:
    """Verify exactly one copy of each midpoint child within every saved parent."""
    parents = arrays["parent_cells"]
    previous_cells = previous["cells"].astype(int)
    cells = arrays["cells"].astype(int)
    if (parents.shape != (len(cells),) or not np.array_equal(parents, parents.astype(int))
            or np.any(parents < 0) or np.any(parents >= len(previous_cells))):
        raise ValueError("Invalid immediate-parent mapping")
    parents = parents.astype(int)
    parent_points = previous["coordinates"][previous_cells]
    parent_affine = np.concatenate((np.ones((len(previous_cells), 3, 1)), parent_points), axis=2)
    points = arrays["coordinates"][cells]
    child_affine = np.concatenate((np.ones((len(cells), 3, 1)), points), axis=2)
    barycentric = np.einsum("mvi,mij->mvj", child_affine, np.linalg.inv(parent_affine)[parents])
    doubled = barycentric * 2
    snapped = np.rint(doubled)
    error = _maximum_error(doubled, snapped)
    vertex_codes = np.einsum("mvi,i->mv", snapped.astype(int), np.array([1, 3, 9]))
    sorted_codes = np.sort(vertex_codes, axis=1)
    triangle_codes = sorted_codes @ np.array([1, 32, 1024])
    expected = np.array([[2, 4, 10], [4, 6, 12], [10, 12, 18], [4, 10, 12]]) @ np.array([1, 32, 1024])
    order = np.lexsort((triangle_codes, parents))
    partition_exact = bool(len(cells) == len(previous_cells) * 4
                           and np.all(np.bincount(parents, minlength=len(previous_cells)) == 4))
    if partition_exact:
        partition_exact = bool(np.array_equal(triangle_codes[order].reshape(-1, 4),
                                               np.broadcast_to(np.sort(expected), (len(previous_cells), 4))))
    checks = {"four_exact_midpoint_children_per_parent": partition_exact and error <= _TOLERANCE,
              "previous_nodes_identical_prefix": bool(np.array_equal(
                  arrays["coordinates"][:len(previous["coordinates"])], previous["coordinates"])),
              "source_ancestry_composes_through_parent": bool(np.array_equal(
                  arrays["source_cells"], previous["source_cells"][parents]))}
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "maximum_parent_barycentric_midpoint_error": error}


def _verify_level(arrays: dict[str, np.ndarray], configuration: dict[str, Any],
                  source: dict[str, np.ndarray], index: int) -> dict[str, Any]:
    coordinates = arrays["coordinates"]
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or len(coordinates) < 6:
        raise ValueError("coordinates must be a nonempty N by 2 mesh")
    for name in ("cells", "cell_layers", "inner_nodes", "outer_nodes", "source_cells"):
        if not np.array_equal(arrays[name], arrays[name].astype(np.int64)):
            raise ValueError(f"{name} contains noninteger indices")
    cells = arrays["cells"].astype(np.int64)
    layers = arrays["cell_layers"].astype(np.int64)
    inner = arrays["inner_nodes"].astype(np.int64)
    outer = arrays["outer_nodes"].astype(np.int64)
    if cells.ndim != 2 or cells.shape[1] != 3 or not len(cells):
        raise ValueError("cells must be a nonempty M by 3 connectivity array")
    count, nodes, states = len(cells), len(coordinates), 5
    shapes = {"cell_layers": (count,), "phases": (states,), "activation": (states,),
              "displacements": (states, nodes, 2), "strains": (states, count, 3),
              "stresses": (states, count, 3), "equivalent_stress": (states, count),
              "pressure": (states, count), "lumen_area": (states,), "outer_area": (states,),
              "stored_energy": (states,),
              "active_strain_unit": (count, 3), "active_tangents": (count, 2),
              "source_cells": (count,)}
    for name, shape in shapes.items():
        if arrays[name].shape != shape:
            raise ValueError(f"{name} has shape {arrays[name].shape}, expected {shape}")
    if inner.ndim != 1 or outer.ndim != 1:
        raise ValueError("Boundary cycles must be one dimensional")
    if any(np.any(ids < 0) or np.any(ids >= nodes) for ids in (cells, inner, outer)):
        raise ValueError("Mesh or boundary node index out of bounds")
    if set(layers.tolist()) != {0, 1, 2}:
        raise ValueError("All three layers must be present with labels 0, 1, 2")

    points = coordinates[cells]
    affine = np.concatenate((np.ones((count, 3, 1)), points), axis=2)
    areas = np.linalg.det(affine) / 2
    if np.any(areas <= 0):
        raise ValueError("Reference mesh contains an inverted or degenerate triangle")
    gradient = np.linalg.inv(affine)[:, 1:, :]
    strain_map = np.zeros((count, 3, 6))
    strain_map[:, 0, 0::2], strain_map[:, 1, 1::2] = gradient[:, 0], gradient[:, 1]
    strain_map[:, 2, 0::2], strain_map[:, 2, 1::2] = gradient[:, 1], gradient[:, 0]
    matrices = []
    for name in _MATERIALS:
        young = float(configuration["materials"][name]["young"])
        poisson = float(configuration["materials"][name]["poisson"])
        factor = young / ((1 + poisson) * (1 - 2 * poisson))
        matrices.append(factor * np.array([[1 - poisson, poisson, 0],
                                            [poisson, 1 - poisson, 0],
                                            [0, 0, (1 - 2 * poisson) / 2]]))
    elasticity = np.asarray(matrices)[layers]
    tangents = arrays["active_tangents"]
    active = layers == 2
    eigenstrain = np.zeros((count, 3))
    eigenstrain[active, 0] = -tangents[active, 0] ** 2
    eigenstrain[active, 1] = -tangents[active, 1] ** 2
    eigenstrain[active, 2] = -2 * tangents[active, 0] * tangents[active, 1]
    dofs = (2 * cells[:, :, None] + np.arange(2)).reshape(count, 6)
    local_stiffness = np.einsum("mai,mab,mbj,m->mij", strain_map, elasticity, strain_map, areas)
    stiffness = sparse.coo_matrix((local_stiffness.ravel(), (
        np.broadcast_to(dofs[:, :, None], (count, 6, 6)).ravel(),
        np.broadcast_to(dofs[:, None, :], (count, 6, 6)).ravel())),
        shape=(2 * nodes, 2 * nodes)).tocsr()
    local_load = np.einsum("mai,mab,mb,m->mi", strain_map, elasticity, eigenstrain, areas)
    unit_load = np.zeros(2 * nodes)
    np.add.at(unit_load, dofs.ravel(), local_load.ravel())
    gauge = np.zeros((3, 2 * nodes))
    gauge_coordinates = source["coordinates"]
    gauge_nodes = len(gauge_coordinates)
    gauge[0, :2 * gauge_nodes:2], gauge[1, 1:2 * gauge_nodes:2] = 1 / gauge_nodes, 1 / gauge_nodes
    rotation_scale = float(np.sum(gauge_coordinates ** 2))
    if rotation_scale <= 0:
        raise ValueError("Degenerate rotational gauge")
    gauge[2, :2 * gauge_nodes:2] = -gauge_coordinates[:, 1] / rotation_scale
    gauge[2, 1:2 * gauge_nodes:2] = gauge_coordinates[:, 0] / rotation_scale
    kkt_norm = max(float(np.max(np.asarray(abs(stiffness).sum(axis=1)).ravel()
                                + np.sum(np.abs(gauge), axis=0))),
                   float(np.max(np.sum(np.abs(gauge), axis=1))))
    displacement, activation = arrays["displacements"], arrays["activation"]
    phases = np.linspace(0, 1, states)
    expected_activation = .015 * (1 - np.cos(2 * np.pi * phases))
    strain = np.einsum("mai,smi->sma", strain_map, displacement[:, cells].reshape(states, count, 6))
    stress = np.einsum("mab,smb->sma", elasticity, strain - activation[:, None, None] * eigenstrain)
    stored_energy = .5 * np.einsum("sma,sma,m->s", stress,
                                  strain - activation[:, None, None] * eigenstrain, areas)
    first, second, shear = np.moveaxis(stress, -1, 0)
    pressure = -(first + second) / 2
    equivalent = np.sqrt(np.maximum(first ** 2 - first * second + second ** 2 + 3 * shear ** 2, 0))
    max_backward = max_force = max_gauge = 0.0
    minimum_area = float("inf")
    lumen_area, outer_area = np.zeros(states), np.zeros(states)
    for state in range(states):
        vector, rhs = displacement[state].reshape(-1), activation[state] * unit_load
        imbalance = stiffness @ vector - rhs
        multiplier = np.linalg.solve(gauge @ gauge.T, -(gauge @ imbalance))
        force_residual, gauge_residual = imbalance + gauge.T @ multiplier, gauge @ vector
        force_error, gauge_error = float(np.max(np.abs(force_residual))), float(np.max(np.abs(gauge_residual)))
        denominator = (kkt_norm * max(float(np.max(np.abs(vector))), float(np.max(np.abs(multiplier))))
                       + float(np.max(np.abs(rhs))))
        max_backward = max(max_backward, max(force_error, gauge_error) / max(denominator, 1e-30))
        max_force, max_gauge = max(max_force, force_error), max(max_gauge, gauge_error)
        deformed = coordinates + displacement[state]
        edges = deformed[cells][:, 1:] - deformed[cells][:, :1]
        deformed_areas = (edges[:, 0, 0] * edges[:, 1, 1] - edges[:, 0, 1] * edges[:, 1, 0]) / 2
        minimum_area = min(minimum_area, float(np.min(deformed_areas)))
        lumen_area[state], outer_area[state] = _polygon_area(deformed[inner]), _polygon_area(deformed[outer])
    reference_lumen = _polygon_area(coordinates[inner])
    if reference_lumen <= 0:
        raise ValueError("Reference cavity must have positive signed area")
    peak_change = float((lumen_area[2] - reference_lumen) / reference_lumen)
    errors = {"maximum_strain_recompute_error": _maximum_error(strain, arrays["strains"]),
              "maximum_stress_recompute_error": _maximum_error(stress, arrays["stresses"]),
              "maximum_pressure_recompute_error": _maximum_error(pressure, arrays["pressure"]),
              "maximum_equivalent_stress_recompute_error": _maximum_error(equivalent, arrays["equivalent_stress"]),
              "maximum_lumen_area_recompute_error": _maximum_error(lumen_area, arrays["lumen_area"]),
              "maximum_outer_area_recompute_error": _maximum_error(outer_area, arrays["outer_area"]),
              "maximum_stored_energy_recompute_error": _maximum_error(stored_energy, arrays["stored_energy"]),
              "maximum_eigenstrain_recompute_error": _maximum_error(eigenstrain, arrays["active_strain_unit"])}
    fixed_geometry = _verify_fixed_geometry(arrays, source, index, areas)
    checks = {
        "all_required_arrays_finite": True,
        "five_frozen_phase_states": _maximum_error(arrays["phases"], phases) <= _TOLERANCE,
        "frozen_cosine_activation_peak_003": _maximum_error(activation, expected_activation) <= _TOLERANCE,
        "unit_myocardial_tangents": _maximum_error(np.linalg.norm(tangents[active], axis=1),
                                                   np.ones(np.count_nonzero(active))) <= _TOLERANCE,
        "nonmyocardial_tangents_zero": float(np.max(np.abs(tangents[~active]))) <= _TOLERANCE,
        "boundary_cycles_match_mesh": _boundary_matches(cells, inner, outer),
        "no_duplicate_triangles": len(np.unique(np.sort(cells, axis=1), axis=0)) == count,
        "no_unused_mesh_nodes": len(np.unique(cells)) == nodes,
        "all_reference_and_deformed_triangles_positive": minimum_area > 0,
        "cavity_and_outer_areas_positive_nested": bool(np.all(lumen_area > 0) and np.all(outer_area > lumen_area)),
        "all_fields_independently_recomputed": max(errors.values()) <= _TOLERANCE,
        "assembled_kkt_backward_residual": max_backward <= _TOLERANCE,
        "rigid_gauge_residual": max_gauge <= _TOLERANCE,
        "unloaded_endpoints_return_to_reference": float(np.max(np.abs(displacement[[0, -1]]))) <= _TOLERANCE,
        "fixed_geometry_and_inherited_active_load": fixed_geometry["status"] == "passed",
    }
    maximum_strain = float(np.max(np.abs(strain)))
    replay_errors = None
    if index == 0:
        replay_errors = {name: _maximum_error(arrays[name], source[name][[0, 10, 20, 30, 40]])
                         for name in ("displacements", "strains", "stresses", "lumen_area", "outer_area")}
        checks["f2_saved_baseline_replay"] = max(replay_errors.values()) <= _TOLERANCE
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "node_count": nodes, "triangle_count": count, "state_count": states,
            "minimum_reference_area": float(np.min(areas)), "minimum_deformed_area": minimum_area,
            "peak_lumen_fraction_change": peak_change, "maximum_abs_recomputed_strain": maximum_strain,
            "maximum_backward_residual": max_backward, "maximum_force_residual_absolute": max_force,
            "maximum_constraint_residual": max_gauge, "fixed_geometry": fixed_geometry,
            "recomputed_stored_energy": stored_energy.tolist(), "f2_replay_errors": replay_errors,
            "small_strain_applicability": "passed" if maximum_strain <= .05 else "failed", **errors}


def verify_fem_fixed_mesh(result: Path, save: bool = True) -> dict[str, Any]:
    """Verify three saved nested meshes without performing a scientific solve."""
    result = Path(result).resolve()
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    source_path = Path(configuration["source_path"])
    if not source_path.is_absolute():
        workspace = next((folder for folder in result.parents if (folder / "START_HERE.md").is_file()), None)
        if workspace is None:
            raise ValueError("Relative source_path requires a discoverable PRL workspace")
        source_path = workspace / source_path
    source_path = source_path.resolve()
    source = _load(source_path, tuple(name for name in _REQUIRED if name != "source_cells"))
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    materials_frozen = all(
        abs(float(configuration["materials"][name]["young"]) - young) <= _TOLERANCE
        and abs(float(configuration["materials"][name]["poisson"]) - .3) <= _TOLERANCE
        for name, young in _MATERIALS.items())
    levels: dict[str, Any] = {}
    previous_arrays = None
    for index, label in enumerate(("L0", "L1", "L2")):
        try:
            arrays = _load(result / "raw" / f"{label}.npz")
            levels[label] = _verify_level(arrays, configuration, source, index)
            if index:
                if previous_arrays is None:
                    raise ValueError("Previous level unavailable for nested-mesh audit")
                parent_refinement = _verify_parent_refinement(arrays, previous_arrays)
                levels[label]["parent_refinement"] = parent_refinement
                levels[label]["checks"]["exact_nested_parent_refinement"] = parent_refinement["status"] == "passed"
                if parent_refinement["status"] != "passed":
                    levels[label]["status"] = "failed"
            previous_arrays = arrays
        except (OSError, ValueError, KeyError, IndexError, TypeError, np.linalg.LinAlgError,
                ZeroDivisionError) as error:
            levels[label] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    engineering_checks = {"frozen_source_sha256": configuration.get("source_sha256") == source_digest,
                          "frozen_three_layer_materials": materials_frozen,
                          "all_three_levels_independently_verified": all(
                              level["status"] == "passed" for level in levels.values())}
    complete = all("peak_lumen_fraction_change" in level for level in levels.values())
    coarse_difference = fine_difference = relative_difference = None
    if complete:
        responses = [levels[label]["peak_lumen_fraction_change"] for label in ("L0", "L1", "L2")]
        coarse_difference = abs(responses[1] - responses[0])
        fine_difference = abs(responses[2] - responses[1])
        relative_difference = fine_difference / max(abs(responses[2]), 1e-30)
    energy_complete = all("recomputed_stored_energy" in level for level in levels.values())
    energy_increases = None
    if energy_complete:
        energies = np.asarray([levels[label]["recomputed_stored_energy"] for label in ("L0", "L1", "L2")])
        energy_increases = np.max(np.diff(energies, axis=0), axis=1).tolist()
    engineering_checks["nested_elastic_energy_nonincreasing"] = bool(
        energy_complete and max(energy_increases) <= _TOLERANCE)
    convergence_checks = {
        "last_pair_absolute_cavity_difference_at_most_0002": complete and fine_difference <= .002,
        "last_pair_relative_cavity_difference_at_most_005": complete and relative_difference <= .05,
        "refinement_response_difference_decreases": complete and fine_difference < coarse_difference,
        "nonzero_active_cavity_contraction": complete and levels["L2"]["peak_lumen_fraction_change"] <= -.005,
    }
    engineering = "passed" if all(engineering_checks.values()) else "failed"
    convergence = "passed" if all(convergence_checks.values()) and engineering == "passed" else "failed"
    small_strain = "passed" if all(level.get("small_strain_applicability") == "passed"
                                   for level in levels.values()) else "failed"
    report = {"schema_version": "prl.fem_fixed_mesh_verification.v1",
              "status": "passed" if engineering == convergence == small_strain == "passed" else "failed",
              "checks": engineering_checks, "levels": levels,
              "engineering_consistency": engineering, "mesh_response_convergence": convergence,
              "small_strain_applicability": small_strain,
              "convergence_checks": convergence_checks,
              "coarse_pair_cavity_fraction_difference": coarse_difference,
              "fine_pair_cavity_fraction_difference": fine_difference,
              "fine_pair_cavity_relative_difference": relative_difference,
              "nested_maximum_energy_increases": energy_increases,
              "source_path": str(source_path), "source_sha256": source_digest,
              "scientific_gates": {"fixed_geometry_engineering": engineering,
                                   "mesh_response_convergence": convergence,
                                   "small_strain_applicability": small_strain,
                                   "finite_deformation": "not_run", "zebrafish_calibration": "not_run",
                                   "biological_validation": "not_run"},
              "interpretation": "Five phases are prescribed quasistatic loads, not measured cardiac time. "
                                "This audit isolates spatial refinement on the F2 G1 polygon and inherited "
                                "piecewise active tensor. Small-strain applicability is a separate 5% gate. "
                                "Materials remain uncalibrated; pressure is mean in-plane tissue stress, "
                                "not lumen pressure; the stress invariant is two-dimensional."}
    if save:
        (result / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
