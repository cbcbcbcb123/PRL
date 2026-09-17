"""Independent verification for the F1-S synthetic orientation package."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp


MATERIAL_ORDER = ("endocardium", "ecm", "myocardium")


def _constitutive(young: float, poisson: float) -> np.ndarray:
    lame = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    return np.asarray(
        [
            [lame + 2.0 * shear, lame, 0.0],
            [lame, lame + 2.0 * shear, 0.0],
            [0.0, 0.0, shear],
        ],
        dtype=np.float64,
    )


def _triangle_matrix(points: np.ndarray) -> tuple[np.ndarray, float]:
    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]
    determinant = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    area = 0.5 * determinant
    b = np.asarray([y2 - y3, y3 - y1, y1 - y2]) / determinant
    c = np.asarray([x3 - x2, x1 - x3, x2 - x1]) / determinant
    matrix = np.zeros((3, 6), dtype=np.float64)
    for local in range(3):
        matrix[0, 2 * local] = b[local]
        matrix[1, 2 * local + 1] = c[local]
        matrix[2, 2 * local] = c[local]
        matrix[2, 2 * local + 1] = b[local]
    return matrix, area


def _polygon_area(points: np.ndarray) -> float:
    return 0.5 * float(
        np.sum(points[:, 0] * np.roll(points[:, 1], -1))
        - np.sum(points[:, 1] * np.roll(points[:, 0], -1))
    )


def _expected_offsets(configuration: dict[str, Any], condition: str) -> np.ndarray:
    field = configuration["orientation_field"]
    bands = int(field["patch_bands"])
    sectors = int(field["patch_sectors"])
    if condition == "uniform":
        return np.zeros((bands, sectors), dtype=np.float64)
    generator = np.random.Generator(np.random.PCG64(int(field["seed"])))
    raw = generator.standard_normal((bands, sectors))
    smooth = (
        0.50 * raw
        + 0.20 * np.roll(raw, 1, axis=1)
        + 0.20 * np.roll(raw, -1, axis=1)
        + 0.10 * raw[::-1]
    )
    smooth -= float(np.mean(smooth))
    return smooth * (
        float(field["maximum_absolute_offset_degrees"])
        / float(np.max(np.abs(smooth)))
    )


def _expected_field(
    coordinates: np.ndarray,
    cells: np.ndarray,
    layers: np.ndarray,
    configuration: dict[str, Any],
    condition: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    geometry = configuration["geometry"]
    aspect_x = float(geometry["aspect_x"])
    aspect_y = float(geometry["aspect_y"])
    radial = np.asarray(geometry["radial_boundaries"], dtype=np.float64)
    field = configuration["orientation_field"]
    bands = int(field["patch_bands"])
    sectors = int(field["patch_sectors"])
    offsets = _expected_offsets(configuration, condition)
    centroids = np.mean(coordinates[cells], axis=1)
    parameter_angle = np.mod(
        np.arctan2(centroids[:, 1] / aspect_y, centroids[:, 0] / aspect_x),
        2.0 * math.pi,
    )
    sector = np.clip(
        np.floor(sectors * parameter_angle / (2.0 * math.pi)).astype(np.int64),
        0,
        sectors - 1,
    )
    elliptic_radius = np.sqrt(
        (centroids[:, 0] / aspect_x) ** 2 + (centroids[:, 1] / aspect_y) ** 2
    )
    band = np.clip(
        np.floor(bands * (elliptic_radius - radial[2]) / (radial[3] - radial[2])).astype(
            np.int64
        ),
        0,
        bands - 1,
    )
    patch_ids = band * sectors + sector
    patch_ids[layers != 2] = -1
    angles = np.full(len(cells), np.nan, dtype=np.float64)
    eigenstrain = np.zeros((len(cells), 3), dtype=np.float64)
    for cell_id in np.flatnonzero(layers == 2):
        angle = math.atan2(
            float(centroids[cell_id, 1]) / aspect_y,
            float(centroids[cell_id, 0]) / aspect_x,
        )
        tangent = np.asarray(
            [-aspect_x * math.sin(angle), aspect_y * math.cos(angle)], dtype=np.float64
        )
        tangent /= np.linalg.norm(tangent)
        tangent_angle = math.atan2(float(tangent[1]), float(tangent[0]))
        patch_id = int(patch_ids[cell_id])
        patch_band, patch_sector = divmod(patch_id, sectors)
        active_angle = tangent_angle + math.radians(
            float(offsets[patch_band, patch_sector])
        )
        angles[cell_id] = active_angle
        direction = np.asarray([math.cos(active_angle), math.sin(active_angle)])
        eigenstrain[cell_id] = -np.asarray(
            [direction[0] ** 2, direction[1] ** 2, 2.0 * direction[0] * direction[1]]
        )
    return patch_ids, angles, eigenstrain


def _assemble_independent(
    coordinates: np.ndarray,
    cells: np.ndarray,
    layers: np.ndarray,
    eigenstrain: np.ndarray,
    configuration: dict[str, Any],
) -> tuple[
    sp.csc_matrix,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[np.ndarray, ...],
]:
    constitutive = tuple(
        _constitutive(
            float(configuration["materials"][name]["young"]),
            float(configuration["materials"][name]["poisson"]),
        )
        for name in MATERIAL_ORDER
    )
    node_count = len(coordinates)
    degree_count = 2 * node_count
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    active_load = np.zeros(degree_count, dtype=np.float64)
    matrices = np.zeros((len(cells), 3, 6), dtype=np.float64)
    areas = np.zeros(len(cells), dtype=np.float64)
    dofs = np.zeros((len(cells), 6), dtype=np.int64)
    for cell_id, connectivity in enumerate(cells):
        matrix, area = _triangle_matrix(coordinates[connectivity])
        matrices[cell_id] = matrix
        areas[cell_id] = area
        local_dofs = np.asarray(
            [component for node in connectivity for component in (2 * node, 2 * node + 1)],
            dtype=np.int64,
        )
        dofs[cell_id] = local_dofs
        material = constitutive[int(layers[cell_id])]
        local_stiffness = area * matrix.T @ material @ matrix
        for local_row, global_row in enumerate(local_dofs):
            for local_column, global_column in enumerate(local_dofs):
                value = float(local_stiffness[local_row, local_column])
                if value:
                    rows.append(int(global_row))
                    columns.append(int(global_column))
                    values.append(value)
        if layers[cell_id] == 2:
            active_load[local_dofs] += area * matrix.T @ material @ eigenstrain[cell_id]
    stiffness = sp.coo_matrix(
        (values, (rows, columns)), shape=(degree_count, degree_count)
    ).tocsr()
    constraints = np.zeros((3, degree_count), dtype=np.float64)
    constraints[0, 0::2] = 1.0 / node_count
    constraints[1, 1::2] = 1.0 / node_count
    rotation_scale = float(np.sum(coordinates[:, 0] ** 2 + coordinates[:, 1] ** 2))
    constraints[2, 0::2] = -coordinates[:, 1] / rotation_scale
    constraints[2, 1::2] = coordinates[:, 0] / rotation_scale
    block = sp.bmat(
        [
            [stiffness, sp.csr_matrix(constraints).T],
            [sp.csr_matrix(constraints), sp.csr_matrix((3, 3))],
        ],
        format="csc",
    )
    return block, active_load, matrices, areas, dofs, constitutive


def _verify_case(
    path: Path,
    configuration: dict[str, Any],
    condition: str,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    with np.load(path, allow_pickle=False) as payload:
        data = {name: payload[name] for name in payload.files}
    coordinates = data["coordinates"]
    cells = data["cells"].astype(np.int64)
    layers = data["cell_layers"].astype(np.int64)
    patch_ids, angles, eigenstrain = _expected_field(
        coordinates, cells, layers, configuration, condition
    )
    expected_offsets = _expected_offsets(configuration, condition)
    matrix, active_load, strain_matrices, areas, dofs, constitutive = _assemble_independent(
        coordinates, cells, layers, eigenstrain, configuration
    )
    matrix_norm = float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel()))
    maximum_strain_error = 0.0
    maximum_stress_error = 0.0
    maximum_pressure_error = 0.0
    maximum_lumen_error = 0.0
    maximum_backward_residual = 0.0
    maximum_constraint_residual = 0.0
    minimum_deformed_area = math.inf
    inner_nodes = data["inner_nodes"].astype(np.int64)
    for phase_index, alpha in enumerate(data["activation"]):
        displacement = data["displacements"][phase_index]
        multipliers = data["multipliers"][phase_index]
        solution = np.concatenate([displacement.reshape(-1), multipliers])
        rhs = np.concatenate([active_load * float(alpha), np.zeros(3)])
        residual = matrix @ solution - rhs
        denominator = (
            matrix_norm * np.linalg.norm(solution, ord=np.inf)
            + np.linalg.norm(rhs, ord=np.inf)
        )
        maximum_backward_residual = max(
            maximum_backward_residual,
            float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30)),
        )
        maximum_constraint_residual = max(
            maximum_constraint_residual,
            float(np.max(np.abs(matrix[-3:, :-3] @ displacement.reshape(-1)))),
        )
        deformed = coordinates + displacement
        points = deformed[cells]
        deformed_areas = 0.5 * (
            (points[:, 1, 0] - points[:, 0, 0])
            * (points[:, 2, 1] - points[:, 0, 1])
            - (points[:, 2, 0] - points[:, 0, 0])
            * (points[:, 1, 1] - points[:, 0, 1])
        )
        minimum_deformed_area = min(minimum_deformed_area, float(np.min(deformed_areas)))
        lumen = _polygon_area(deformed[inner_nodes])
        maximum_lumen_error = max(
            maximum_lumen_error, abs(lumen - float(data["lumen_area"][phase_index]))
        )
        for cell_id in range(len(cells)):
            strain = strain_matrices[cell_id] @ displacement.reshape(-1)[dofs[cell_id]]
            elastic = strain - float(alpha) * eigenstrain[cell_id]
            stress = constitutive[int(layers[cell_id])] @ elastic
            pressure = -0.5 * float(stress[0] + stress[1])
            maximum_strain_error = max(
                maximum_strain_error,
                float(np.max(np.abs(strain - data["strains"][phase_index, cell_id]))),
            )
            maximum_stress_error = max(
                maximum_stress_error,
                float(np.max(np.abs(stress - data["stresses"][phase_index, cell_id]))),
            )
            maximum_pressure_error = max(
                maximum_pressure_error,
                abs(pressure - float(data["pressure"][phase_index, cell_id])),
            )
    myocardium = layers == 2
    tensor_norm = np.sqrt(
        eigenstrain[myocardium, 0] ** 2
        + eigenstrain[myocardium, 1] ** 2
        + 0.5 * eigenstrain[myocardium, 2] ** 2
    )
    report = {
        "finite": bool(all(np.all(np.isfinite(data[name])) for name in ("displacements", "strains", "stresses", "pressure"))),
        "state_count": int(len(data["phases"])),
        "minimum_reference_area": float(np.min(areas)),
        "minimum_deformed_area": minimum_deformed_area,
        "maximum_abs_saved_strain": float(np.max(np.abs(data["strains"]))),
        "maximum_strain_recompute_error": maximum_strain_error,
        "maximum_stress_recompute_error": maximum_stress_error,
        "maximum_pressure_recompute_error": maximum_pressure_error,
        "maximum_lumen_area_recompute_error": maximum_lumen_error,
        "maximum_independent_backward_residual": maximum_backward_residual,
        "maximum_independent_constraint_residual": maximum_constraint_residual,
        "patch_id_match": bool(np.array_equal(patch_ids, data["patch_ids"])),
        "patch_offset_max_error_degrees": float(
            np.max(np.abs(expected_offsets - data["patch_offsets_degrees"]))
        ),
        "orientation_vector_max_error": float(
            np.max(
                np.abs(
                    np.column_stack((np.cos(angles[myocardium]), np.sin(angles[myocardium])))
                    - np.column_stack(
                        (
                            np.cos(data["orientation_angles"][myocardium]),
                            np.sin(data["orientation_angles"][myocardium]),
                        )
                    )
                )
            )
        ),
        "active_eigenstrain_max_error": float(
            np.max(np.abs(eigenstrain - data["active_strain_unit"]))
        ),
        "active_eigenstrain_trace_max_error": float(
            np.max(np.abs(eigenstrain[myocardium, 0] + eigenstrain[myocardium, 1] + 1.0))
        ),
        "active_eigenstrain_tensor_norm_max_error": float(
            np.max(np.abs(tensor_norm - 1.0))
        ),
        "peak_lumen_fraction_change": float(
            data["lumen_fraction_change"][int(np.argmax(data["activation"]))]
        ),
    }
    return report, data


def _weighted_cv(values: np.ndarray, weights: np.ndarray) -> float:
    mean = float(np.sum(weights * values) / np.sum(weights))
    variance = float(np.sum(weights * (values - mean) ** 2) / np.sum(weights))
    return math.sqrt(max(variance, 0.0)) / max(abs(mean), 1.0e-30)


def _paired_metrics(uniform: dict[str, np.ndarray], random: dict[str, np.ndarray]) -> dict[str, float]:
    peak = int(np.argmax(uniform["activation"]))
    uniform_displacement = uniform["displacements"][peak]
    random_displacement = random["displacements"][peak]
    displacement_difference = float(
        np.linalg.norm(random_displacement - uniform_displacement)
        / max(np.linalg.norm(uniform_displacement), 1.0e-30)
    )
    myocardium = uniform["cell_layers"] == 2
    weights = uniform["reference_areas"][myocardium]
    uniform_stress = uniform["equivalent_stress"][peak, myocardium]
    random_stress = random["equivalent_stress"][peak, myocardium]
    stress_difference = float(
        math.sqrt(float(np.sum(weights * (random_stress - uniform_stress) ** 2)))
        / max(math.sqrt(float(np.sum(weights * uniform_stress**2))), 1.0e-30)
    )
    outer = uniform["outer_nodes"].astype(np.int64)
    uniform_outer = np.linalg.norm(uniform_displacement[outer], axis=1)
    random_outer = np.linalg.norm(random_displacement[outer], axis=1)
    return {
        "peak_relative_displacement_l2": displacement_difference,
        "peak_myocardial_equivalent_stress_relative_l2": stress_difference,
        "peak_lumen_fraction_change_difference": float(
            random["lumen_fraction_change"][peak] - uniform["lumen_fraction_change"][peak]
        ),
        "uniform_peak_myocardial_stress_cv": _weighted_cv(uniform_stress, weights),
        "synthetic_random_peak_myocardial_stress_cv": _weighted_cv(random_stress, weights),
        "uniform_peak_outer_displacement_cv": float(
            np.std(uniform_outer) / max(np.mean(uniform_outer), 1.0e-30)
        ),
        "synthetic_random_peak_outer_displacement_cv": float(
            np.std(random_outer) / max(np.mean(random_outer), 1.0e-30)
        ),
    }


def verify_fem_synthetic_orientation(result: Path, *, save: bool = True) -> dict[str, Any]:
    result = result.resolve()
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    summary = json.loads((result / "summary.json").read_text(encoding="utf-8"))
    cases: dict[str, dict[str, Any]] = {}
    arrays: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    for level in ("G0", "G1"):
        cases[level] = {}
        for condition in ("uniform", "synthetic_random"):
            case_report, case_arrays = _verify_case(
                result / "raw" / condition / f"{level}.npz",
                configuration,
                condition,
            )
            cases[level][condition] = case_report
            arrays[(level, condition)] = case_arrays
    paired = {
        level: _paired_metrics(
            arrays[(level, "uniform")], arrays[(level, "synthetic_random")]
        )
        for level in ("G0", "G1")
    }
    paired_recompute_error = max(
        abs(float(paired[level][name]) - float(summary["paired_sensitivity"][level][name]))
        for level in ("G0", "G1")
        for name in paired[level]
    )
    geometry_identical = all(
        np.array_equal(arrays[(level, "uniform")][name], arrays[(level, "synthetic_random")][name])
        for level in ("G0", "G1")
        for name in ("coordinates", "cells", "cell_layers", "reference_areas", "phases", "activation")
    )
    offsets = arrays[("G1", "synthetic_random")]["patch_offsets_degrees"]
    field_statistics = {
        "mean_degrees": float(np.mean(offsets)),
        "rms_degrees": float(np.sqrt(np.mean(offsets**2))),
        "maximum_absolute_degrees": float(np.max(np.abs(offsets))),
    }
    mesh_lumen_differences = {
        condition: abs(
            cases["G1"][condition]["peak_lumen_fraction_change"]
            - cases["G0"][condition]["peak_lumen_fraction_change"]
        )
        for condition in ("uniform", "synthetic_random")
    }
    fine_displacement = paired["G1"]["peak_relative_displacement_l2"]
    fine_stress = paired["G1"]["peak_myocardial_equivalent_stress_relative_l2"]
    displacement_mesh_difference = abs(
        fine_displacement - paired["G0"]["peak_relative_displacement_l2"]
    )
    stress_mesh_difference = abs(
        fine_stress - paired["G0"]["peak_myocardial_equivalent_stress_relative_l2"]
    )
    checks = {
        "paired_geometry_and_loading_identical": geometry_identical,
        "random_field_mean_zero": abs(field_statistics["mean_degrees"]) <= 1.0e-12,
        "random_field_rms_nonzero": field_statistics["rms_degrees"] >= 4.0,
        "random_field_maximum_frozen": abs(field_statistics["maximum_absolute_degrees"] - 18.0) <= 1.0e-10,
        "random_field_reconstructed": all(
            cases[level][condition]["patch_id_match"]
            and cases[level][condition]["patch_offset_max_error_degrees"] <= 1.0e-12
            and cases[level][condition]["orientation_vector_max_error"] <= 1.0e-12
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "active_magnitude_matched": all(
            cases[level][condition]["active_eigenstrain_trace_max_error"] <= 1.0e-12
            and cases[level][condition]["active_eigenstrain_tensor_norm_max_error"] <= 1.0e-12
            and cases[level][condition]["active_eigenstrain_max_error"] <= 1.0e-12
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "all_states_finite": all(
            cases[level][condition]["finite"]
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "all_triangles_positive": all(
            cases[level][condition]["minimum_deformed_area"] > 0.0
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "small_strain_scope": all(
            cases[level][condition]["maximum_abs_saved_strain"] <= 0.05
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "independent_field_recomputation": all(
            max(
                cases[level][condition]["maximum_strain_recompute_error"],
                cases[level][condition]["maximum_stress_recompute_error"],
                cases[level][condition]["maximum_pressure_recompute_error"],
                cases[level][condition]["maximum_lumen_area_recompute_error"],
            )
            <= 1.0e-10
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "independent_linear_residual": all(
            cases[level][condition]["maximum_independent_backward_residual"] <= 1.0e-10
            and cases[level][condition]["maximum_independent_constraint_residual"] <= 1.0e-10
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "forty_one_actual_states": all(
            cases[level][condition]["state_count"] == 41
            for level in ("G0", "G1")
            for condition in ("uniform", "synthetic_random")
        ),
        "two_level_lumen_response": all(value <= 2.0e-3 for value in mesh_lumen_differences.values()),
        "paired_metrics_independently_recomputed": paired_recompute_error <= 1.0e-10,
        "G1_displacement_effect_at_least_one_percent": fine_displacement >= 0.01,
        "G1_stress_effect_at_least_one_percent": fine_stress >= 0.01,
        "displacement_effect_exceeds_mesh_difference": fine_displacement > 2.0 * displacement_mesh_difference,
        "stress_effect_exceeds_mesh_difference": fine_stress > 2.0 * stress_mesh_difference,
    }
    numerical_names = [
        name
        for name in checks
        if name
        not in {
            "G1_displacement_effect_at_least_one_percent",
            "G1_stress_effect_at_least_one_percent",
            "displacement_effect_exceeds_mesh_difference",
            "stress_effect_exceeds_mesh_difference",
        }
    ]
    sensitivity_names = [name for name in checks if name not in numerical_names]
    engineering_passed = all(checks[name] for name in numerical_names)
    sensitivity_resolved = all(checks[name] for name in sensitivity_names)
    report = {
        "schema_version": "prl.fem_synthetic_orientation_verification.v1",
        "status": "passed" if engineering_passed and sensitivity_resolved else "failed",
        "scope": "controlled synthetic myocardial long-axis field sensitivity",
        "checks": checks,
        "cases": cases,
        "field_statistics": field_statistics,
        "paired_sensitivity": paired,
        "mesh_lumen_differences": mesh_lumen_differences,
        "sensitivity_mesh_differences": {
            "peak_relative_displacement_l2": displacement_mesh_difference,
            "peak_myocardial_equivalent_stress_relative_l2": stress_mesh_difference,
        },
        "maximum_paired_metric_recompute_error": paired_recompute_error,
        "scientific_gates": {
            "engineering": "passed" if engineering_passed else "failed",
            "synthetic_orientation_sensitivity": "passed" if sensitivity_resolved else "unknown",
            "measured_cell_shape_field": "not_run",
            "zebrafish_calibration": "not_run",
            "biological_validation": "not_run",
            "growth": "not_run",
            "ecm_feedback": "not_run",
            "fsi": "not_run",
        },
        "interpretation": (
            "A pass resolves sensitivity to the frozen synthetic long-axis field only. "
            "Material patches are not explicit cells and provide no zebrafish validation."
        ),
    }
    if save:
        (result / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return report
