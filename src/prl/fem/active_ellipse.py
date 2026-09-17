"""Independent 2-D active-strain FEM with an elliptic-ring reference fixture.

The assembly accepts conforming triangular geometries and explicit eigenstrain
fields.  Its F0 material constants are synthetic, not a calibrated zebrafish
ventricular constitutive model.
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


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

LAYER_NAMES = ("endocardium", "ecm", "myocardium")
RADIAL_BOUNDARIES = (1.00, 1.05, 1.10, 1.35)
ASPECT_X = 1.25
ASPECT_Y = 1.00
PEAK_ACTIVATION = 0.03
MATERIALS = {
    "endocardium": (1.0, 0.30),
    "ecm": (0.5, 0.30),
    "myocardium": (2.5, 0.30),
}


@dataclass(frozen=True)
class MeshLevel:
    label: str
    ntheta: int
    radial_intervals: tuple[int, int, int]


LEVELS = {
    "G0": MeshLevel("G0", 48, (2, 2, 4)),
    "G1": MeshLevel("G1", 96, (4, 4, 8)),
}


@dataclass
class EllipticModel:
    level: MeshLevel
    coordinates: FloatArray
    cells: IntArray
    cell_layers: IntArray
    areas: FloatArray
    cell_dofs: IntArray
    strain_matrices: FloatArray
    active_strain_unit: FloatArray
    stiffness: sp.csr_matrix
    active_load_unit: FloatArray
    constraints: sp.csr_matrix
    inner_nodes: IntArray
    outer_nodes: IntArray
    material_matrices: tuple[FloatArray, FloatArray, FloatArray]


def plane_strain_matrix(young: float, poisson: float) -> FloatArray:
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


def triangle_strain_matrix(points: FloatArray) -> tuple[FloatArray, float]:
    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]
    twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if twice_area <= 0.0:
        raise ValueError("elliptic FEM mesh contains a non-positive triangle")
    area = 0.5 * twice_area
    b = np.asarray([y2 - y3, y3 - y1, y1 - y2]) / twice_area
    c = np.asarray([x3 - x2, x1 - x3, x2 - x1]) / twice_area
    matrix = np.zeros((3, 6), dtype=np.float64)
    for local in range(3):
        matrix[0, 2 * local] = b[local]
        matrix[1, 2 * local + 1] = c[local]
        matrix[2, 2 * local] = c[local]
        matrix[2, 2 * local + 1] = b[local]
    return matrix, area


def _radial_coordinates(level: MeshLevel) -> tuple[FloatArray, IntArray]:
    values: list[float] = []
    interval_layers: list[int] = []
    for layer, intervals in enumerate(level.radial_intervals):
        segment = np.linspace(
            RADIAL_BOUNDARIES[layer],
            RADIAL_BOUNDARIES[layer + 1],
            intervals + 1,
        )
        values.extend(segment.tolist() if layer == 0 else segment[1:].tolist())
        interval_layers.extend([layer] * intervals)
    return np.asarray(values), np.asarray(interval_layers, dtype=np.int64)


def build_model(level_label: str) -> EllipticModel:
    level = LEVELS[level_label]
    radial, interval_layers = _radial_coordinates(level)
    theta = 2.0 * math.pi * np.arange(level.ntheta) / level.ntheta
    coordinates = np.asarray(
        [
            [ASPECT_X * radius * math.cos(angle), ASPECT_Y * radius * math.sin(angle)]
            for radius in radial
            for angle in theta
        ],
        dtype=np.float64,
    )

    def node(radial_index: int, angular_index: int) -> int:
        return radial_index * level.ntheta + (angular_index % level.ntheta)

    cells: list[list[int]] = []
    layers: list[int] = []
    for radial_index, layer in enumerate(interval_layers):
        for angular_index in range(level.ntheta):
            inner = node(radial_index, angular_index)
            inner_next = node(radial_index, angular_index + 1)
            outer = node(radial_index + 1, angular_index)
            outer_next = node(radial_index + 1, angular_index + 1)
            cells.extend(([inner, outer, outer_next], [inner, outer_next, inner_next]))
            layers.extend((int(layer), int(layer)))
    cell_array = np.asarray(cells, dtype=np.int64)
    layer_array = np.asarray(layers, dtype=np.int64)
    active_strain_unit = np.zeros((len(cell_array), 3), dtype=np.float64)
    for cell_id, connectivity in enumerate(cell_array):
        if layer_array[cell_id] == 2:
            centroid = np.mean(coordinates[connectivity], axis=0)
            angle = math.atan2(centroid[1] / ASPECT_Y, centroid[0] / ASPECT_X)
            tangent = np.asarray(
                [-ASPECT_X * math.sin(angle), ASPECT_Y * math.cos(angle)],
                dtype=np.float64,
            )
            tangent /= np.linalg.norm(tangent)
            active_strain_unit[cell_id] = -np.asarray(
                [tangent[0] ** 2, tangent[1] ** 2, 2.0 * tangent[0] * tangent[1]],
                dtype=np.float64,
            )
    last_ring = len(radial) - 1
    return assemble_model(
        level,
        coordinates,
        cell_array,
        layer_array,
        np.arange(level.ntheta, dtype=np.int64),
        np.arange(
            last_ring * level.ntheta,
            (last_ring + 1) * level.ntheta,
            dtype=np.int64,
        ),
        active_strain_unit,
    )


def assemble_model(
    level: MeshLevel,
    coordinates: FloatArray,
    cells: IntArray,
    cell_layers: IntArray,
    inner_nodes: IntArray,
    outer_nodes: IntArray,
    active_strain_unit: FloatArray,
) -> EllipticModel:
    """Assemble the F0 materials and rigid-motion gauge on a supplied mesh.

    Triangles and both boundary loops must be counterclockwise.  Layer IDs are
    0/1/2 for endocardium/ECM/myocardium.  ``active_strain_unit`` contains the
    engineering components (xx, yy, gamma_xy) per triangle; it is explicit so
    no ellipse-specific direction is inferred for a measured contour.  The
    three constraints remove rigid motion, without clamping boundary nodes.
    """
    coordinates = np.array(coordinates, dtype=np.float64, copy=True)
    active_strain_unit = np.array(active_strain_unit, dtype=np.float64, copy=True)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or len(coordinates) < 3:
        raise ValueError("coordinates must have shape (N, 2), with N >= 3")
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("coordinates must be finite")
    integer_arrays = []
    for name, values in (
        ("cells", cells),
        ("cell_layers", cell_layers),
        ("inner_nodes", inner_nodes),
        ("outer_nodes", outer_nodes),
    ):
        values = np.asarray(values)
        if not np.issubdtype(values.dtype, np.integer):
            raise ValueError(f"{name} must contain integer indices")
        integer_arrays.append(np.array(values, dtype=np.int64, copy=True))
    cell_array, layer_array, inner_nodes, outer_nodes = integer_arrays
    if cell_array.ndim != 2 or cell_array.shape[1] != 3 or len(cell_array) == 0:
        raise ValueError("cells must have shape (M, 3), with M >= 1")
    if np.any(cell_array < 0) or np.any(cell_array >= len(coordinates)):
        raise ValueError("cell connectivity is outside the coordinate array")
    if len(np.unique(cell_array)) != len(coordinates):
        raise ValueError("every coordinate must belong to a triangle")
    if layer_array.shape != (len(cell_array),) or np.any(
        (layer_array < 0) | (layer_array >= len(LAYER_NAMES))
    ):
        raise ValueError("cell_layers must have shape (M,) and contain 0, 1, or 2")
    if active_strain_unit.shape != (len(cell_array), 3) or not np.all(
        np.isfinite(active_strain_unit)
    ):
        raise ValueError("active_strain_unit must be finite with shape (M, 3)")
    for name, boundary in (("inner_nodes", inner_nodes), ("outer_nodes", outer_nodes)):
        if (
            boundary.ndim != 1
            or len(boundary) < 3
            or len(np.unique(boundary)) != len(boundary)
            or np.any(boundary < 0)
            or np.any(boundary >= len(coordinates))
        ):
            raise ValueError(f"{name} must be an ordered loop of valid unique nodes")
        if polygon_area(coordinates[boundary]) <= 0.0:
            raise ValueError(f"{name} must be counterclockwise with positive area")
    if np.intersect1d(inner_nodes, outer_nodes).size:
        raise ValueError("inner and outer boundary loops must be disjoint")
    material_matrices = tuple(
        plane_strain_matrix(*MATERIALS[name]) for name in LAYER_NAMES
    )

    degree_count = 2 * len(coordinates)
    row_indices: list[int] = []
    column_indices: list[int] = []
    stiffness_values: list[float] = []
    active_load = np.zeros(degree_count, dtype=np.float64)
    cell_dofs = np.zeros((len(cell_array), 6), dtype=np.int64)
    strain_matrices = np.zeros((len(cell_array), 3, 6), dtype=np.float64)
    areas = np.zeros(len(cell_array), dtype=np.float64)

    for cell_id, connectivity in enumerate(cell_array):
        points = coordinates[connectivity]
        strain_matrix, area = triangle_strain_matrix(points)
        areas[cell_id] = area
        strain_matrices[cell_id] = strain_matrix
        dofs = np.asarray(
            [component for index in connectivity for component in (2 * index, 2 * index + 1)],
            dtype=np.int64,
        )
        cell_dofs[cell_id] = dofs
        constitutive = material_matrices[int(layer_array[cell_id])]
        local_stiffness = area * strain_matrix.T @ constitutive @ strain_matrix
        for local_row, global_row in enumerate(dofs):
            for local_column, global_column in enumerate(dofs):
                value = float(local_stiffness[local_row, local_column])
                if value:
                    row_indices.append(int(global_row))
                    column_indices.append(int(global_column))
                    stiffness_values.append(value)

        eigenstrain = active_strain_unit[cell_id]
        if np.any(eigenstrain):
            active_load[dofs] += area * strain_matrix.T @ constitutive @ eigenstrain

    stiffness = sp.coo_matrix(
        (stiffness_values, (row_indices, column_indices)),
        shape=(degree_count, degree_count),
    ).tocsr()
    node_count = len(coordinates)
    constraints = np.zeros((3, degree_count), dtype=np.float64)
    constraints[0, 0::2] = 1.0 / node_count
    constraints[1, 1::2] = 1.0 / node_count
    rotation_scale = float(np.sum(coordinates[:, 0] ** 2 + coordinates[:, 1] ** 2))
    constraints[2, 0::2] = -coordinates[:, 1] / rotation_scale
    constraints[2, 1::2] = coordinates[:, 0] / rotation_scale
    return EllipticModel(
        level=level,
        coordinates=coordinates,
        cells=cell_array,
        cell_layers=layer_array,
        areas=areas,
        cell_dofs=cell_dofs,
        strain_matrices=strain_matrices,
        active_strain_unit=active_strain_unit,
        stiffness=stiffness,
        active_load_unit=active_load,
        constraints=sp.csr_matrix(constraints),
        inner_nodes=inner_nodes,
        outer_nodes=outer_nodes,
        material_matrices=material_matrices,
    )


def polygon_area(points: FloatArray) -> float:
    return 0.5 * float(
        np.sum(points[:, 0] * np.roll(points[:, 1], -1))
        - np.sum(points[:, 1] * np.roll(points[:, 0], -1))
    )


def signed_triangle_areas(coordinates: FloatArray, cells: IntArray) -> FloatArray:
    points = coordinates[cells]
    return 0.5 * (
        (points[:, 1, 0] - points[:, 0, 0])
        * (points[:, 2, 1] - points[:, 0, 1])
        - (points[:, 2, 0] - points[:, 0, 0])
        * (points[:, 1, 1] - points[:, 0, 1])
    )


def _sparse_infinity_norm(matrix: sp.spmatrix) -> float:
    return float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel()))


def solve_cycle(level_label: str, phase_count: int = 41) -> dict[str, Any]:
    """Solve the original elliptic fixture, retaining its output contract."""
    if phase_count < 5 or phase_count % 2 == 0:
        raise ValueError("phase_count must be odd and at least five")
    started = time.perf_counter()
    model = build_model(level_label)
    result = solve_model_cycle(model, phase_count)
    result["wall_seconds"] = time.perf_counter() - started
    return result


def solve_model_cycle(model: EllipticModel, phase_count: int = 41) -> dict[str, Any]:
    """Solve a supplied model using the unchanged F0 activation and KKT system."""
    if phase_count < 5 or phase_count % 2 == 0:
        raise ValueError("phase_count must be odd and at least five")
    started = time.perf_counter()
    constraint_count = model.constraints.shape[0]
    zero = sp.csr_matrix((constraint_count, constraint_count))
    matrix = sp.bmat(
        [[model.stiffness, model.constraints.T], [model.constraints, zero]],
        format="csc",
    )
    factor_started = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_started
    matrix_norm = _sparse_infinity_norm(matrix)

    phases = np.linspace(0.0, 1.0, phase_count)
    activation = 0.5 * PEAK_ACTIVATION * (1.0 - np.cos(2.0 * math.pi * phases))
    peak_index = int(np.argmax(activation))
    node_count = len(model.coordinates)
    cell_count = len(model.cells)
    displacements = np.zeros((phase_count, node_count, 2), dtype=np.float64)
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
    peak_gauge_multipliers = np.zeros(constraint_count, dtype=np.float64)

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
        if phase_index == peak_index:
            peak_gauge_multipliers = solution[-constraint_count:].copy()
        maximum_constraint_residual = max(
            maximum_constraint_residual,
            float(np.max(np.abs(model.constraints @ solution[: 2 * node_count]))),
        )
        displacements[phase_index] = displacement
        deformed = model.coordinates + displacement
        triangle_areas = signed_triangle_areas(deformed, model.cells)
        minimum_triangle_area[phase_index] = float(np.min(triangle_areas))
        lumen_area[phase_index] = polygon_area(deformed[model.inner_nodes])
        outer_area[phase_index] = polygon_area(deformed[model.outer_nodes])

        for cell_id, dofs in enumerate(model.cell_dofs):
            local_displacement = solution[dofs]
            strain = model.strain_matrices[cell_id] @ local_displacement
            elastic_strain = strain - float(alpha) * model.active_strain_unit[cell_id]
            constitutive = model.material_matrices[int(model.cell_layers[cell_id])]
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
                * model.areas[cell_id]
                * float(elastic_strain @ constitutive @ elastic_strain)
            )

    lumen_fraction_change = (lumen_area - lumen_area[0]) / lumen_area[0]
    outer_fraction_change = (outer_area - outer_area[0]) / outer_area[0]
    deformed_peak = model.coordinates + displacements[peak_index]
    peak_inner = deformed_peak[model.inner_nodes]
    return {
        "schema_version": "prl.fem_active_ellipse_cycle.v1",
        "level": model.level.label,
        "model": model,
        "phases": phases,
        "activation": activation,
        "displacements": displacements,
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
        "peak_inner_long_span": float(np.ptp(peak_inner[:, 0])),
        "peak_inner_short_span": float(np.ptp(peak_inner[:, 1])),
        "maximum_abs_strain": float(np.max(np.abs(strains))),
        "maximum_equivalent_stress": float(np.max(equivalent_stress)),
        "pressure_range": [float(np.min(pressure)), float(np.max(pressure))],
        "maximum_backward_residual": maximum_backward_residual,
        "maximum_constraint_residual": maximum_constraint_residual,
        "peak_gauge_multipliers": peak_gauge_multipliers,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": time.perf_counter() - started,
    }
