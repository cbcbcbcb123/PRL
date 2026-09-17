"""Independent verification of the active elliptic FEM pilot package."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np


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


def _constitutive(young: float, poisson: float) -> np.ndarray:
    lame = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    return np.asarray(
        [[lame + 2.0 * shear, lame, 0.0],
         [lame, lame + 2.0 * shear, 0.0],
         [0.0, 0.0, shear]],
        dtype=np.float64,
    )


def _polygon_area(points: np.ndarray) -> float:
    return 0.5 * float(
        np.sum(points[:, 0] * np.roll(points[:, 1], -1))
        - np.sum(points[:, 1] * np.roll(points[:, 0], -1))
    )


def _verify_level(path: Path, configuration: dict[str, Any]) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        coordinates = data["coordinates"]
        cells = data["cells"].astype(np.int64)
        layers = data["cell_layers"].astype(np.int64)
        inner_nodes = data["inner_nodes"].astype(np.int64)
        phases = data["phases"]
        activation = data["activation"]
        displacement = data["displacements"]
        saved_strain = data["strains"]
        saved_stress = data["stresses"]
        saved_lumen_area = data["lumen_area"]

    matrices: list[np.ndarray] = []
    reference_areas: list[float] = []
    tangential_eigenstrain = np.zeros((len(cells), 3), dtype=np.float64)
    aspect_x = float(configuration["geometry"]["aspect_x"])
    aspect_y = float(configuration["geometry"]["aspect_y"])
    for cell_id, cell in enumerate(cells):
        matrix, area = _triangle_matrix(coordinates[cell])
        matrices.append(matrix)
        reference_areas.append(area)
        if layers[cell_id] == 2:
            centroid = np.mean(coordinates[cell], axis=0)
            angle = math.atan2(centroid[1] / aspect_y, centroid[0] / aspect_x)
            tangent = np.asarray(
                [-aspect_x * math.sin(angle), aspect_y * math.cos(angle)]
            )
            tangent /= np.linalg.norm(tangent)
            tangential_eigenstrain[cell_id] = -np.asarray(
                [tangent[0] ** 2, tangent[1] ** 2, 2.0 * tangent[0] * tangent[1]]
            )
    matrix_array = np.asarray(matrices)
    material_order = ("endocardium", "ecm", "myocardium")
    constitutive = tuple(
        _constitutive(
            float(configuration["materials"][name]["young"]),
            float(configuration["materials"][name]["poisson"]),
        )
        for name in material_order
    )

    maximum_strain_error = 0.0
    maximum_stress_error = 0.0
    minimum_deformed_area = math.inf
    recomputed_lumen = np.zeros(len(phases), dtype=np.float64)
    for phase_index in range(len(phases)):
        deformed = coordinates + displacement[phase_index]
        points = deformed[cells]
        deformed_areas = 0.5 * (
            (points[:, 1, 0] - points[:, 0, 0])
            * (points[:, 2, 1] - points[:, 0, 1])
            - (points[:, 2, 0] - points[:, 0, 0])
            * (points[:, 1, 1] - points[:, 0, 1])
        )
        minimum_deformed_area = min(minimum_deformed_area, float(np.min(deformed_areas)))
        recomputed_lumen[phase_index] = _polygon_area(deformed[inner_nodes])
        for cell_id, cell in enumerate(cells):
            local = displacement[phase_index, cell].reshape(-1)
            strain = matrix_array[cell_id] @ local
            stress = constitutive[int(layers[cell_id])] @ (
                strain - activation[phase_index] * tangential_eigenstrain[cell_id]
            )
            maximum_strain_error = max(
                maximum_strain_error,
                float(np.max(np.abs(strain - saved_strain[phase_index, cell_id]))),
            )
            maximum_stress_error = max(
                maximum_stress_error,
                float(np.max(np.abs(stress - saved_stress[phase_index, cell_id]))),
            )
    lumen_error = float(np.max(np.abs(recomputed_lumen - saved_lumen_area)))
    peak_index = int(np.argmax(activation))
    peak_change = float(
        (recomputed_lumen[peak_index] - recomputed_lumen[0]) / recomputed_lumen[0]
    )
    finite = bool(
        np.all(np.isfinite(displacement))
        and np.all(np.isfinite(saved_strain))
        and np.all(np.isfinite(saved_stress))
    )
    return {
        "finite": finite,
        "minimum_reference_area": float(np.min(reference_areas)),
        "minimum_deformed_area": minimum_deformed_area,
        "maximum_strain_recompute_error": maximum_strain_error,
        "maximum_stress_recompute_error": maximum_stress_error,
        "maximum_lumen_area_recompute_error": lumen_error,
        "peak_lumen_fraction_change": peak_change,
        "maximum_abs_saved_strain": float(np.max(np.abs(saved_strain))),
        "state_count": int(len(phases)),
    }


def verify_fem_active_ellipse(result: Path, *, save: bool = True) -> dict[str, Any]:
    result = result.resolve()
    configuration = json.loads(
        (result / "configuration.json").read_text(encoding="utf-8")
    )
    summary = json.loads((result / "summary.json").read_text(encoding="utf-8"))
    levels = {
        label: _verify_level(result / "raw" / f"{label}.npz", configuration)
        for label in ("G0", "G1")
    }
    mesh_difference = abs(
        levels["G1"]["peak_lumen_fraction_change"]
        - levels["G0"]["peak_lumen_fraction_change"]
    )
    checks = {
        "all_states_finite": all(level["finite"] for level in levels.values()),
        "all_triangles_positive": all(
            level["minimum_deformed_area"] > 0.0 for level in levels.values()
        ),
        "strain_independently_recomputed": max(
            level["maximum_strain_recompute_error"] for level in levels.values()
        ) <= 1.0e-10,
        "stress_independently_recomputed": max(
            level["maximum_stress_recompute_error"] for level in levels.values()
        ) <= 1.0e-10,
        "lumen_area_independently_recomputed": max(
            level["maximum_lumen_area_recompute_error"] for level in levels.values()
        ) <= 1.0e-10,
        "linear_backward_residual": float(summary["maximum_backward_residual"]) <= 1.0e-10,
        "rigid_constraint_residual": float(summary["maximum_constraint_residual"]) <= 1.0e-10,
        "small_strain_scope": levels["G1"]["maximum_abs_saved_strain"] <= 0.05,
        "nonzero_active_contraction": levels["G1"]["peak_lumen_fraction_change"] <= -0.005,
        "two_level_lumen_response": mesh_difference <= 2.0e-3,
        "forty_one_actual_states": all(
            level["state_count"] == 41 for level in levels.values()
        ),
    }
    report = {
        "schema_version": "prl.fem_active_ellipse_verification.v1",
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "2-D synthetic active elliptic three-layer FEM engineering feasibility",
        "checks": checks,
        "levels": levels,
        "mesh_peak_lumen_change_absolute_difference": mesh_difference,
        "scientific_gates": {
            "fem_engineering_feasibility": "passed" if all(checks.values()) else "failed",
            "zebrafish_calibration": "not_run",
            "biological_validation": "not_run",
            "fluid_structure_interaction": "not_run",
            "dcm_fem_advantage": "not_run",
        },
        "interpretation": (
            "A pass establishes only the independent small-strain FEM path and its "
            "synthetic active response; it does not establish zebrafish agreement."
        ),
    }
    if save:
        (result / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return report
