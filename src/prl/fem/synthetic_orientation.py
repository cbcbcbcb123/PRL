"""Controlled myocardial long-axis fields on the F0 elliptic FEM mesh.

The 2 x 24 patches in this module are material labels, not explicit cells.  The
module changes only the direction of the prescribed myocardial active strain;
geometry, passive material, activation magnitude, and boundary conditions are
identical between the paired conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

import numpy as np
from numpy.typing import NDArray
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .active_ellipse import (
    ASPECT_X,
    ASPECT_Y,
    PEAK_ACTIVATION,
    RADIAL_BOUNDARIES,
    EllipticModel,
    build_model,
    polygon_area,
    signed_triangle_areas,
)


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

CONDITIONS = ("uniform", "synthetic_random")
PATCH_BANDS = 2
PATCH_SECTORS = 24
PATCH_COUNT = PATCH_BANDS * PATCH_SECTORS
RANDOM_SEED = 20260916
MAX_OFFSET_DEGREES = 18.0


@dataclass
class OrientationFieldModel:
    """F0 mesh plus a myocardial active-direction field."""

    base: EllipticModel
    condition: str
    patch_ids: IntArray
    patch_offsets_degrees: FloatArray
    orientation_angles: FloatArray
    active_strain_unit: FloatArray
    active_load_unit: FloatArray


def generate_patch_offsets(condition: str) -> FloatArray:
    """Return the frozen 2 x 24 direction offsets in degrees."""

    if condition not in CONDITIONS:
        raise ValueError(f"unknown orientation-field condition: {condition}")
    if condition == "uniform":
        return np.zeros((PATCH_BANDS, PATCH_SECTORS), dtype=np.float64)

    generator = np.random.Generator(np.random.PCG64(RANDOM_SEED))
    raw = generator.standard_normal((PATCH_BANDS, PATCH_SECTORS))
    smooth = (
        0.50 * raw
        + 0.20 * np.roll(raw, 1, axis=1)
        + 0.20 * np.roll(raw, -1, axis=1)
        + 0.10 * raw[::-1]
    )
    smooth -= float(np.mean(smooth))
    maximum = float(np.max(np.abs(smooth)))
    if maximum <= 0.0:  # pragma: no cover - impossible for the frozen random draw
        raise RuntimeError("synthetic orientation field has zero amplitude")
    return smooth * (MAX_OFFSET_DEGREES / maximum)


def _patch_ids(base: EllipticModel) -> IntArray:
    centroids = np.mean(base.coordinates[base.cells], axis=1)
    parameter_angle = np.mod(
        np.arctan2(centroids[:, 1] / ASPECT_Y, centroids[:, 0] / ASPECT_X),
        2.0 * math.pi,
    )
    sector = np.floor(PATCH_SECTORS * parameter_angle / (2.0 * math.pi)).astype(
        np.int64
    )
    sector = np.clip(sector, 0, PATCH_SECTORS - 1)
    elliptic_radius = np.sqrt(
        (centroids[:, 0] / ASPECT_X) ** 2 + (centroids[:, 1] / ASPECT_Y) ** 2
    )
    myocardial_inner = RADIAL_BOUNDARIES[2]
    myocardial_outer = RADIAL_BOUNDARIES[3]
    radial_fraction = (elliptic_radius - myocardial_inner) / (
        myocardial_outer - myocardial_inner
    )
    band = np.floor(PATCH_BANDS * radial_fraction).astype(np.int64)
    band = np.clip(band, 0, PATCH_BANDS - 1)
    patch_ids = band * PATCH_SECTORS + sector
    patch_ids = patch_ids.astype(np.int64)
    patch_ids[base.cell_layers != 2] = -1
    return patch_ids


def _tangent_angle(centroid: FloatArray) -> float:
    parameter_angle = math.atan2(
        float(centroid[1]) / ASPECT_Y,
        float(centroid[0]) / ASPECT_X,
    )
    tangent = np.asarray(
        [-ASPECT_X * math.sin(parameter_angle), ASPECT_Y * math.cos(parameter_angle)],
        dtype=np.float64,
    )
    tangent /= np.linalg.norm(tangent)
    return math.atan2(float(tangent[1]), float(tangent[0]))


def build_orientation_model(level_label: str, condition: str) -> OrientationFieldModel:
    """Build one paired model while preserving the F0 passive operator."""

    base = build_model(level_label)
    offsets = generate_patch_offsets(condition)
    patch_ids = _patch_ids(base)
    orientation_angles = np.full(len(base.cells), np.nan, dtype=np.float64)
    active_strain_unit = np.zeros((len(base.cells), 3), dtype=np.float64)
    active_load = np.zeros(2 * len(base.coordinates), dtype=np.float64)

    for cell_id, connectivity in enumerate(base.cells):
        if base.cell_layers[cell_id] != 2:
            continue
        centroid = np.mean(base.coordinates[connectivity], axis=0)
        angle = _tangent_angle(centroid)
        patch_id = int(patch_ids[cell_id])
        band, sector = divmod(patch_id, PATCH_SECTORS)
        angle += math.radians(float(offsets[band, sector]))
        orientation_angles[cell_id] = angle
        direction = np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float64)
        eigenstrain = -np.asarray(
            [
                direction[0] ** 2,
                direction[1] ** 2,
                2.0 * direction[0] * direction[1],
            ],
            dtype=np.float64,
        )
        active_strain_unit[cell_id] = eigenstrain
        dofs = base.cell_dofs[cell_id]
        constitutive = base.material_matrices[2]
        active_load[dofs] += (
            base.areas[cell_id]
            * base.strain_matrices[cell_id].T
            @ constitutive
            @ eigenstrain
        )

    return OrientationFieldModel(
        base=base,
        condition=condition,
        patch_ids=patch_ids,
        patch_offsets_degrees=offsets,
        orientation_angles=orientation_angles,
        active_strain_unit=active_strain_unit,
        active_load_unit=active_load,
    )


def _sparse_infinity_norm(matrix: sp.spmatrix) -> float:
    return float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel()))


def solve_orientation_cycle(
    level_label: str,
    condition: str,
    phase_count: int = 41,
) -> dict[str, Any]:
    """Solve a quasi-static active cycle for one frozen orientation field."""

    if phase_count < 5 or phase_count % 2 == 0:
        raise ValueError("phase_count must be odd and at least five")
    started = time.perf_counter()
    model = build_orientation_model(level_label, condition)
    base = model.base
    constraint_count = base.constraints.shape[0]
    zero = sp.csr_matrix((constraint_count, constraint_count))
    matrix = sp.bmat(
        [[base.stiffness, base.constraints.T], [base.constraints, zero]],
        format="csc",
    )
    factor_started = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_started
    matrix_norm = _sparse_infinity_norm(matrix)

    phases = np.linspace(0.0, 1.0, phase_count)
    activation = 0.5 * PEAK_ACTIVATION * (1.0 - np.cos(2.0 * math.pi * phases))
    peak_index = int(np.argmax(activation))
    node_count = len(base.coordinates)
    cell_count = len(base.cells)
    displacements = np.zeros((phase_count, node_count, 2), dtype=np.float64)
    multipliers = np.zeros((phase_count, constraint_count), dtype=np.float64)
    strains = np.zeros((phase_count, cell_count, 3), dtype=np.float64)
    stresses = np.zeros_like(strains)
    equivalent_stress = np.zeros((phase_count, cell_count), dtype=np.float64)
    pressure = np.zeros_like(equivalent_stress)
    lumen_area = np.zeros(phase_count, dtype=np.float64)
    outer_area = np.zeros(phase_count, dtype=np.float64)
    stored_energy = np.zeros(phase_count, dtype=np.float64)
    minimum_triangle_area = np.zeros(phase_count, dtype=np.float64)
    maximum_backward_residual = 0.0
    maximum_constraint_residual = 0.0
    solve_seconds = 0.0

    for phase_index, alpha in enumerate(activation):
        rhs = np.concatenate(
            [model.active_load_unit * float(alpha), np.zeros(constraint_count)]
        )
        solve_started = time.perf_counter()
        solution = factor.solve(rhs)
        solve_seconds += time.perf_counter() - solve_started
        residual = matrix @ solution - rhs
        denominator = (
            matrix_norm * np.linalg.norm(solution, ord=np.inf)
            + np.linalg.norm(rhs, ord=np.inf)
        )
        maximum_backward_residual = max(
            maximum_backward_residual,
            float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30)),
        )
        displacement = solution[: 2 * node_count].reshape(node_count, 2)
        multipliers[phase_index] = solution[-constraint_count:]
        maximum_constraint_residual = max(
            maximum_constraint_residual,
            float(np.max(np.abs(base.constraints @ solution[: 2 * node_count]))),
        )
        displacements[phase_index] = displacement
        deformed = base.coordinates + displacement
        triangle_areas = signed_triangle_areas(deformed, base.cells)
        minimum_triangle_area[phase_index] = float(np.min(triangle_areas))
        lumen_area[phase_index] = polygon_area(deformed[base.inner_nodes])
        outer_area[phase_index] = polygon_area(deformed[base.outer_nodes])

        for cell_id, dofs in enumerate(base.cell_dofs):
            local_displacement = solution[dofs]
            strain = base.strain_matrices[cell_id] @ local_displacement
            elastic_strain = strain - float(alpha) * model.active_strain_unit[cell_id]
            constitutive = base.material_matrices[int(base.cell_layers[cell_id])]
            stress = constitutive @ elastic_strain
            strains[phase_index, cell_id] = strain
            stresses[phase_index, cell_id] = stress
            equivalent_stress[phase_index, cell_id] = math.sqrt(
                max(
                    stress[0] ** 2
                    - stress[0] * stress[1]
                    + stress[1] ** 2
                    + 3.0 * stress[2] ** 2,
                    0.0,
                )
            )
            pressure[phase_index, cell_id] = -0.5 * (stress[0] + stress[1])
            stored_energy[phase_index] += (
                0.5
                * base.areas[cell_id]
                * float(elastic_strain @ constitutive @ elastic_strain)
            )

    lumen_fraction_change = (lumen_area - lumen_area[0]) / lumen_area[0]
    outer_fraction_change = (outer_area - outer_area[0]) / outer_area[0]
    return {
        "schema_version": "prl.fem_synthetic_orientation_cycle.v1",
        "level": level_label,
        "condition": condition,
        "model": model,
        "phases": phases,
        "activation": activation,
        "displacements": displacements,
        "multipliers": multipliers,
        "strains": strains,
        "stresses": stresses,
        "equivalent_stress": equivalent_stress,
        "pressure": pressure,
        "lumen_area": lumen_area,
        "outer_area": outer_area,
        "lumen_fraction_change": lumen_fraction_change,
        "outer_fraction_change": outer_fraction_change,
        "stored_energy": stored_energy,
        "minimum_triangle_area": minimum_triangle_area,
        "peak_index": peak_index,
        "maximum_abs_strain": float(np.max(np.abs(strains))),
        "maximum_equivalent_stress": float(np.max(equivalent_stress)),
        "pressure_range": [float(np.min(pressure)), float(np.max(pressure))],
        "maximum_backward_residual": maximum_backward_residual,
        "maximum_constraint_residual": maximum_constraint_residual,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": time.perf_counter() - started,
    }


def _weighted_cv(values: FloatArray, weights: FloatArray) -> float:
    mean = float(np.sum(weights * values) / np.sum(weights))
    variance = float(np.sum(weights * (values - mean) ** 2) / np.sum(weights))
    return math.sqrt(max(variance, 0.0)) / max(abs(mean), 1.0e-30)


def paired_sensitivity(
    uniform: dict[str, Any], synthetic_random: dict[str, Any]
) -> dict[str, float]:
    """Compute the preregistered paired response metrics."""

    if uniform["level"] != synthetic_random["level"]:
        raise ValueError("paired results must use the same mesh level")
    uniform_model = uniform["model"].base
    random_model = synthetic_random["model"].base
    if not np.array_equal(uniform_model.cells, random_model.cells) or not np.array_equal(
        uniform_model.coordinates, random_model.coordinates
    ):
        raise ValueError("paired results do not share an identical mesh")
    peak = int(uniform["peak_index"])
    uniform_displacement = uniform["displacements"][peak]
    random_displacement = synthetic_random["displacements"][peak]
    displacement_difference = float(
        np.linalg.norm(random_displacement - uniform_displacement)
        / max(np.linalg.norm(uniform_displacement), 1.0e-30)
    )
    myocardium = uniform_model.cell_layers == 2
    weights = uniform_model.areas[myocardium]
    uniform_stress = uniform["equivalent_stress"][peak, myocardium]
    random_stress = synthetic_random["equivalent_stress"][peak, myocardium]
    stress_difference = float(
        math.sqrt(float(np.sum(weights * (random_stress - uniform_stress) ** 2)))
        / max(math.sqrt(float(np.sum(weights * uniform_stress**2))), 1.0e-30)
    )
    uniform_outer = np.linalg.norm(
        uniform_displacement[uniform_model.outer_nodes], axis=1
    )
    random_outer = np.linalg.norm(
        random_displacement[uniform_model.outer_nodes], axis=1
    )
    return {
        "peak_relative_displacement_l2": displacement_difference,
        "peak_myocardial_equivalent_stress_relative_l2": stress_difference,
        "peak_lumen_fraction_change_difference": float(
            synthetic_random["lumen_fraction_change"][peak]
            - uniform["lumen_fraction_change"][peak]
        ),
        "uniform_peak_myocardial_stress_cv": _weighted_cv(uniform_stress, weights),
        "synthetic_random_peak_myocardial_stress_cv": _weighted_cv(
            random_stress, weights
        ),
        "uniform_peak_outer_displacement_cv": float(
            np.std(uniform_outer) / max(np.mean(uniform_outer), 1.0e-30)
        ),
        "synthetic_random_peak_outer_displacement_cv": float(
            np.std(random_outer) / max(np.mean(random_outer), 1.0e-30)
        ),
    }
