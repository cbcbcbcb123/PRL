from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import cKDTree


FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
Layer = Literal["myocardium", "ecm", "endocardium"]

EPS_REF = 1.0e-2
U_REF = 1.0e-2
SIGMA_REF = 1.0e-2
W_REF = 1.0e-4
OMEGA = 2.0 * math.pi
ALPHA_MEAN = 5.0e-3

MATERIAL = {
    "myocardium": (2.5, 0.30),
    "ecm_eq": (1.0, 0.45),
    "ecm_m": (0.7, 0.30),
    "endocardium": (1.0, 0.30),
}


def plane_strain_matrix(young: float, poisson: float) -> FloatArray:
    lame_lambda = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    return np.asarray(
        [
            [lame_lambda + 2.0 * shear, lame_lambda, 0.0],
            [lame_lambda, lame_lambda + 2.0 * shear, 0.0],
            [0.0, 0.0, shear],
        ],
        dtype=np.float64,
    )


C_MYO = plane_strain_matrix(*MATERIAL["myocardium"])
C_EQ = plane_strain_matrix(*MATERIAL["ecm_eq"])
C_M = plane_strain_matrix(*MATERIAL["ecm_m"])
C_ENDO = plane_strain_matrix(*MATERIAL["endocardium"])
EX = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)


@dataclass(frozen=True)
class MeshLevel:
    label: str
    nx: int
    ny_myo: int
    ny_ecm: int
    ny_endo: int


LEVELS = {
    "G0": MeshLevel("G0", 16, 4, 6, 2),
    "G1": MeshLevel("G1", 32, 8, 12, 4),
    "G2": MeshLevel("G2", 64, 16, 24, 8),
}


@dataclass
class FlatSystem:
    level: MeshLevel
    orientation: str
    profile: str
    coordinates: FloatArray
    cells: NDArray[np.int64]
    cell_layers: NDArray[np.int8]
    areas: FloatArray
    centroids: FloatArray
    strain_map: sp.csr_matrix
    constraints: sp.csr_matrix
    k_myo: sp.csr_matrix
    k_eq: sp.csr_matrix
    k_m: sp.csr_matrix
    k_endo: sp.csr_matrix
    active_unit: FloatArray
    p_mean: FloatArray
    p2_mean: FloatArray
    node_wx: NDArray[np.int64]
    node_wy: NDArray[np.int64]
    macro_index: int
    mechanical_size: int
    myo_cells: NDArray[np.int64]
    ecm_cells: NDArray[np.int64]
    endo_cells: NDArray[np.int64]
    ecm_map: sp.csr_matrix
    ecm_weight_m: sp.csr_matrix
    interface_nodes: dict[str, NDArray[np.int64]]


@dataclass(frozen=True)
class AnnulusLevel:
    label: str
    ntheta: int
    nr_endo: int
    nr_ecm: int
    nr_myo: int


ANNULUS_LEVELS = {
    "G0": AnnulusLevel("G0", 32, 2, 6, 4),
    "G1": AnnulusLevel("G1", 64, 4, 12, 8),
    "G2": AnnulusLevel("G2", 128, 8, 24, 16),
}


@dataclass
class AnnulusSystem:
    level: AnnulusLevel
    angle_offset_degrees: float
    coordinates: FloatArray
    cells: NDArray[np.int64]
    cell_layers: NDArray[np.int8]
    areas: FloatArray
    centroids: FloatArray
    strain_map: sp.csr_matrix
    constraints: sp.csr_matrix
    k_myo: sp.csr_matrix
    k_eq: sp.csr_matrix
    k_m: sp.csr_matrix
    k_endo: sp.csr_matrix
    active_unit: FloatArray
    active_direction: FloatArray
    mechanical_size: int
    myo_cells: NDArray[np.int64]
    ecm_cells: NDArray[np.int64]
    endo_cells: NDArray[np.int64]
    ecm_map: sp.csr_matrix
    ecm_weight_m: sp.csr_matrix
    interface_nodes: dict[str, NDArray[np.int64]]
    inner_nodes: NDArray[np.int64]


def _triangle_B(points: FloatArray) -> tuple[FloatArray, float]:
    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]
    twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if twice_area <= 0.0:
        raise ValueError("triangle orientation must be positive")
    area = 0.5 * twice_area
    b = np.asarray([y2 - y3, y3 - y1, y1 - y2], dtype=np.float64) / twice_area
    c = np.asarray([x3 - x2, x1 - x3, x2 - x1], dtype=np.float64) / twice_area
    matrix = np.zeros((3, 6), dtype=np.float64)
    for local in range(3):
        matrix[0, 2 * local] = b[local]
        matrix[1, 2 * local + 1] = c[local]
        matrix[2, 2 * local] = c[local]
        matrix[2, 2 * local + 1] = b[local]
    return matrix, area


def _block_weight(areas: FloatArray, matrix: FloatArray) -> sp.csr_matrix:
    return sp.kron(sp.diags(areas), sp.csr_matrix(matrix), format="csr")


def _quadratic_triangle_profile(points: FloatArray, profile: str) -> tuple[float, float]:
    if profile == "U":
        return 1.0, 1.0
    bary = np.asarray(
        [[2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0],
         [1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0],
         [1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0]],
        dtype=np.float64,
    )
    x = (bary @ points)[:, 0]
    values = 1.0 + 0.2 * np.cos(2.0 * math.pi * x)
    return float(np.mean(values)), float(np.mean(values * values))


def build_flat_system(
    level_label: str,
    profile: str,
    orientation: str = "slash",
) -> FlatSystem:
    level = LEVELS[level_label]
    if profile not in {"U", "H"}:
        raise ValueError("profile must be U or H")
    if orientation not in {"slash", "backslash"}:
        raise ValueError("invalid mesh orientation")

    y_myo = np.linspace(0.0, 0.20, level.ny_myo + 1)
    y_ecm = np.linspace(0.20, 0.50, level.ny_ecm + 1)[1:]
    y_endo = np.linspace(0.50, 0.55, level.ny_endo + 1)[1:]
    y_values = np.concatenate([y_myo, y_ecm, y_endo])
    x_values = np.linspace(-0.5, 0.5, level.nx + 1)
    ny_total = len(y_values) - 1
    coordinates = np.asarray(
        [[x, y] for y in y_values for x in x_values], dtype=np.float64
    )

    def node(ix: int, iy: int) -> int:
        return iy * (level.nx + 1) + ix

    cells: list[list[int]] = []
    layers: list[int] = []
    for iy in range(ny_total):
        layer_id = 0 if iy < level.ny_myo else (1 if iy < level.ny_myo + level.ny_ecm else 2)
        for ix in range(level.nx):
            n00, n10 = node(ix, iy), node(ix + 1, iy)
            n01, n11 = node(ix, iy + 1), node(ix + 1, iy + 1)
            if orientation == "slash":
                local_cells = ([n00, n10, n11], [n00, n11, n01])
            else:
                local_cells = ([n00, n10, n01], [n10, n11, n01])
            cells.extend(local_cells)
            layers.extend([layer_id, layer_id])
    cell_array = np.asarray(cells, dtype=np.int64)
    layer_array = np.asarray(layers, dtype=np.int8)

    unique_node_count = level.nx * (ny_total + 1)
    node_wx = np.empty(len(coordinates), dtype=np.int64)
    node_wy = np.full(len(coordinates), -1, dtype=np.int64)
    wy_offset = unique_node_count
    free_y_count = level.nx * ny_total
    macro_index = unique_node_count + free_y_count
    mechanical_size = macro_index + 1
    for iy in range(ny_total + 1):
        for ix in range(level.nx + 1):
            full = node(ix, iy)
            periodic_ix = 0 if ix == level.nx else ix
            base = iy * level.nx + periodic_ix
            node_wx[full] = base
            if iy > 0:
                node_wy[full] = wy_offset + (iy - 1) * level.nx + periodic_ix

    row_index: list[int] = []
    column_index: list[int] = []
    values: list[float] = []
    areas: list[float] = []
    centroids: list[FloatArray] = []
    p_mean: list[float] = []
    p2_mean: list[float] = []
    nodal_weights = np.zeros(unique_node_count, dtype=np.float64)
    for cell_id, connectivity in enumerate(cell_array):
        points = coordinates[connectivity]
        local_B, area = _triangle_B(points)
        areas.append(area)
        centroids.append(np.mean(points, axis=0))
        mean_p, mean_p2 = _quadratic_triangle_profile(points, profile)
        p_mean.append(mean_p)
        p2_mean.append(mean_p2)
        for local, full_node in enumerate(connectivity):
            wx = int(node_wx[full_node])
            for strain_component in range(3):
                coefficient = float(local_B[strain_component, 2 * local])
                if coefficient:
                    row_index.append(3 * cell_id + strain_component)
                    column_index.append(wx)
                    values.append(coefficient)
                    row_index.append(3 * cell_id + strain_component)
                    column_index.append(macro_index)
                    values.append(coefficient * float(coordinates[full_node, 0]))
            wy = int(node_wy[full_node])
            if wy >= 0:
                for strain_component in range(3):
                    coefficient = float(local_B[strain_component, 2 * local + 1])
                    if coefficient:
                        row_index.append(3 * cell_id + strain_component)
                        column_index.append(wy)
                        values.append(coefficient)
            nodal_weights[wx] += area / 3.0
    area_array = np.asarray(areas, dtype=np.float64)
    centroid_array = np.asarray(centroids, dtype=np.float64)
    strain_map = sp.coo_matrix(
        (values, (row_index, column_index)),
        shape=(3 * len(cell_array), mechanical_size),
    ).tocsr()
    mean_row = np.zeros(mechanical_size, dtype=np.float64)
    mean_row[:unique_node_count] = nodal_weights / np.sum(nodal_weights)
    constraints = sp.csr_matrix(mean_row.reshape(1, -1))

    myo_cells = np.flatnonzero(layer_array == 0)
    ecm_cells = np.flatnonzero(layer_array == 1)
    endo_cells = np.flatnonzero(layer_array == 2)

    def layer_stiffness(ids: NDArray[np.int64], constitutive: FloatArray) -> sp.csr_matrix:
        row_ids = np.asarray([3 * cell + k for cell in ids for k in range(3)], dtype=np.int64)
        mapping = strain_map[row_ids]
        return (mapping.T @ _block_weight(area_array[ids], constitutive) @ mapping).tocsr()

    k_myo = layer_stiffness(myo_cells, C_MYO)
    k_eq = layer_stiffness(ecm_cells, C_EQ)
    k_m = layer_stiffness(ecm_cells, C_M)
    k_endo = layer_stiffness(endo_cells, C_ENDO)
    ecm_rows = np.asarray([3 * cell + k for cell in ecm_cells for k in range(3)], dtype=np.int64)
    ecm_map = strain_map[ecm_rows]
    ecm_weight_m = _block_weight(area_array[ecm_cells], C_M)

    active_unit = np.zeros(mechanical_size, dtype=np.float64)
    for cell in myo_cells:
        rows = slice(3 * int(cell), 3 * int(cell) + 3)
        local_map = strain_map[rows]
        eigenstrain_per_alpha = -float(p_mean[cell]) * EX
        active_unit += np.asarray(
            local_map.T @ (area_array[cell] * (C_MYO @ eigenstrain_per_alpha))
        ).ravel()

    interface_y = {
        "myo_ecm": level.ny_myo,
        "ecm_endo": level.ny_myo + level.ny_ecm,
    }
    interface_nodes = {
        name: np.asarray([node(ix, iy) for ix in range(level.nx + 1)], dtype=np.int64)
        for name, iy in interface_y.items()
    }
    return FlatSystem(
        level=level,
        orientation=orientation,
        profile=profile,
        coordinates=coordinates,
        cells=cell_array,
        cell_layers=layer_array,
        areas=area_array,
        centroids=centroid_array,
        strain_map=strain_map,
        constraints=constraints,
        k_myo=k_myo,
        k_eq=k_eq,
        k_m=k_m,
        k_endo=k_endo,
        active_unit=active_unit,
        p_mean=np.asarray(p_mean, dtype=np.float64),
        p2_mean=np.asarray(p2_mean, dtype=np.float64),
        node_wx=node_wx,
        node_wy=node_wy,
        macro_index=macro_index,
        mechanical_size=mechanical_size,
        myo_cells=myo_cells,
        ecm_cells=ecm_cells,
        endo_cells=endo_cells,
        ecm_map=ecm_map,
        ecm_weight_m=ecm_weight_m,
        interface_nodes=interface_nodes,
    )


def _kkt(matrix: sp.spmatrix, constraints: sp.csr_matrix) -> sp.csc_matrix:
    zero = sp.csr_matrix((constraints.shape[0], constraints.shape[0]))
    return sp.bmat([[matrix, constraints.T], [constraints, zero]], format="csc")


def _normwise_backward(matrix: sp.spmatrix, solution: NDArray, rhs: NDArray) -> float:
    residual = matrix @ solution - rhs
    denominator = spla.norm(matrix, ord=np.inf) * np.linalg.norm(solution, ord=np.inf) + np.linalg.norm(rhs, ord=np.inf)
    return float(np.linalg.norm(residual, ord=np.inf) / max(float(denominator), 1.0e-30))


def _flat_displacement(system: FlatSystem, state: NDArray) -> NDArray:
    displacement = np.zeros((len(system.coordinates), 2), dtype=state.dtype)
    displacement[:, 0] = state[system.node_wx] + state[system.macro_index] * system.coordinates[:, 0]
    free = system.node_wy >= 0
    displacement[free, 1] = state[system.node_wy[free]]
    return displacement


def _fundamental(values: NDArray) -> NDArray:
    samples = values[:-1]
    phase = np.exp(-2.0j * math.pi * np.arange(len(samples)) / len(samples))
    return 2.0 * np.tensordot(phase, samples, axes=(0, 0)) / len(samples)


def _weighted_average(values: NDArray, weights: FloatArray) -> NDArray:
    return np.tensordot(weights / np.sum(weights), values, axes=(0, 0))


def _flat_energy(
    system: FlatSystem,
    strain: FloatArray,
    z_ecm: FloatArray,
    alpha: float,
) -> dict[str, float]:
    myo_strain = strain[system.myo_cells]
    p = system.p_mean[system.myo_cells]
    p2 = system.p2_mean[system.myo_cells]
    areas = system.areas[system.myo_cells]
    quadratic = np.einsum("ni,ij,nj->n", myo_strain, C_MYO, myo_strain)
    cross = np.einsum("ni,i->n", myo_strain @ C_MYO, EX)
    myo = 0.5 * np.sum(areas * (quadratic + 2.0 * alpha * p * cross + alpha * alpha * p2 * C_MYO[0, 0]))
    ecm_strain = strain[system.ecm_cells]
    ecm_eq = 0.5 * np.sum(system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", ecm_strain, C_EQ, ecm_strain))
    maxwell_strain = ecm_strain - z_ecm
    ecm_m = 0.5 * np.sum(system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", maxwell_strain, C_M, maxwell_strain))
    endo_strain = strain[system.endo_cells]
    endo = 0.5 * np.sum(system.areas[system.endo_cells] * np.einsum("ni,ij,nj->n", endo_strain, C_ENDO, endo_strain))
    return {
        "myocardium": float(myo),
        "ecm_equilibrium": float(ecm_eq),
        "ecm_maxwell": float(ecm_m),
        "endocardium": float(endo),
        "total": float(myo + ecm_eq + ecm_m + endo),
    }


def _flat_signals(
    system: FlatSystem,
    state: FloatArray,
    strain: FloatArray,
    z_ecm: FloatArray,
    alpha: float,
) -> dict[str, Any]:
    displacement = _flat_displacement(system, state)
    layer_ids = (system.myo_cells, system.ecm_cells, system.endo_cells)
    layer_strain = np.asarray(
        [_weighted_average(strain[ids], system.areas[ids]) for ids in layer_ids]
    )
    stress = np.zeros_like(strain)
    p = system.p_mean[system.myo_cells]
    stress[system.myo_cells] = (strain[system.myo_cells] + alpha * p[:, None] * EX) @ C_MYO.T
    stress[system.ecm_cells] = strain[system.ecm_cells] @ C_EQ.T + (strain[system.ecm_cells] - z_ecm) @ C_M.T
    stress[system.endo_cells] = strain[system.endo_cells] @ C_ENDO.T
    locals_out: list[FloatArray] = []
    for ids in (system.ecm_cells, system.endo_cells):
        for left, right in ((-0.375, -0.125), (0.125, 0.375)):
            selected = ids[(system.centroids[ids, 0] >= left) & (system.centroids[ids, 0] <= right)]
            locals_out.append(np.concatenate([
                _weighted_average(strain[selected], system.areas[selected]),
                _weighted_average(stress[selected], system.areas[selected]),
            ]))
    top_start = (system.level.ny_myo + system.level.ny_ecm + system.level.ny_endo) * (system.level.nx + 1)
    top_nodes = np.arange(top_start, top_start + system.level.nx + 1, dtype=np.int64)
    top = displacement[top_nodes]
    dx = 1.0 / system.level.nx
    top_l2_sq = 0.0
    for left_value, right_value in zip(top[:-1], top[1:], strict=True):
        top_l2_sq += dx / 3.0 * (
            float(np.dot(left_value, left_value))
            + float(np.dot(right_value, right_value))
            + float(np.dot(left_value, right_value))
        )
    return {
        "ebar": float(state[system.macro_index]),
        "top_l2": math.sqrt(max(top_l2_sq, 0.0)),
        "layer_strain": layer_strain,
        "locals": np.asarray(locals_out),
        "energy": _flat_energy(system, strain, z_ecm, alpha),
        "max_abs_strain": float(np.max(np.abs(strain))),
    }


def _active_work_step(
    system: FlatSystem,
    strain_mid: FloatArray,
    alpha_mid: float,
    delta_alpha: float,
) -> float:
    ids = system.myo_cells
    elastic_stress_without_profile = strain_mid[ids] @ C_MYO.T
    term = system.p_mean[ids] * elastic_stress_without_profile[:, 0]
    term += alpha_mid * system.p2_mean[ids] * C_MYO[0, 0]
    return float(delta_alpha * np.sum(system.areas[ids] * term))


def run_flat_trajectory(
    system: FlatSystem,
    nt: int,
    tau: float = 0.20,
    max_cycles: int = 20,
    convergence_target: float = 1.0e-9,
) -> dict[str, Any]:
    started = time.perf_counter()
    dt = 1.0 / nt
    a = (2.0 * tau - dt) / (2.0 * tau + dt)
    b = dt / (2.0 * tau + dt)
    stiffness = system.k_myo + system.k_eq + system.k_endo + (1.0 - b) * system.k_m
    matrix = _kkt(stiffness, system.constraints)
    factor_started = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_started
    state = np.zeros(system.mechanical_size, dtype=np.float64)
    strain = np.zeros((len(system.cells), 3), dtype=np.float64)
    z_ecm = np.zeros((len(system.ecm_cells), 3), dtype=np.float64)
    previous_cycle: FloatArray | None = None
    previous_z_cycle: FloatArray | None = None
    maximum_backward = 0.0
    maximum_constraint = 0.0
    solve_seconds = 0.0
    rhs_count = 0
    cycle_difference = math.inf
    final_q = final_z = final_eps = None
    for cycle in range(1, max_cycles + 1):
        q_cycle = np.zeros((nt + 1, system.mechanical_size), dtype=np.float64)
        z_cycle = np.zeros((nt + 1, len(system.ecm_cells), 3), dtype=np.float64)
        eps_cycle = np.zeros((nt + 1, len(system.cells), 3), dtype=np.float64)
        q_cycle[0], z_cycle[0], eps_cycle[0] = state, z_ecm, strain
        for step in range(1, nt + 1):
            alpha = ALPHA_MEAN * (1.0 - math.cos(2.0 * math.pi * step / nt))
            history = a * z_ecm + b * strain[system.ecm_cells]
            rhs_mechanical = system.active_unit * alpha + np.asarray(
                system.ecm_map.T @ (system.ecm_weight_m @ history.reshape(-1))
            ).ravel()
            rhs = np.concatenate([rhs_mechanical, np.zeros(system.constraints.shape[0])])
            one_solve = time.perf_counter()
            solution = factor.solve(rhs)
            solve_seconds += time.perf_counter() - one_solve
            rhs_count += 1
            maximum_backward = max(maximum_backward, _normwise_backward(matrix, solution, rhs))
            state_next = np.asarray(solution[: system.mechanical_size], dtype=np.float64)
            maximum_constraint = max(maximum_constraint, float(np.max(np.abs(system.constraints @ state_next))))
            strain_next = np.asarray(system.strain_map @ state_next).reshape(-1, 3)
            z_next = a * z_ecm + b * (strain[system.ecm_cells] + strain_next[system.ecm_cells])
            state, strain, z_ecm = state_next, strain_next, z_next
            q_cycle[step], z_cycle[step], eps_cycle[step] = state, z_ecm, strain
        if previous_cycle is not None and previous_z_cycle is not None:
            q_scale = max(np.linalg.norm(q_cycle), U_REF * math.sqrt(q_cycle.size))
            z_scale = max(np.linalg.norm(z_cycle), EPS_REF * math.sqrt(z_cycle.size))
            cycle_difference = max(
                float(np.linalg.norm(q_cycle - previous_cycle) / q_scale),
                float(np.linalg.norm(z_cycle - previous_z_cycle) / z_scale),
            )
        previous_cycle, previous_z_cycle = q_cycle, z_cycle
        final_q, final_z, final_eps = q_cycle, z_cycle, eps_cycle
        if cycle >= 2 and cycle_difference <= convergence_target:
            break
    assert final_q is not None and final_z is not None and final_eps is not None

    alpha_series = ALPHA_MEAN * (1.0 - np.cos(2.0 * math.pi * np.arange(nt + 1) / nt))
    ebar = np.zeros(nt + 1)
    top_l2 = np.zeros(nt + 1)
    layer_strain = np.zeros((nt + 1, 3, 3))
    local_values = np.zeros((nt + 1, 4, 6))
    energy = np.zeros(nt + 1)
    max_abs_strain = 0.0
    for index in range(nt + 1):
        signal = _flat_signals(system, final_q[index], final_eps[index], final_z[index], float(alpha_series[index]))
        ebar[index] = signal["ebar"]
        top_l2[index] = signal["top_l2"]
        layer_strain[index] = signal["layer_strain"]
        local_values[index] = signal["locals"]
        energy[index] = signal["energy"]["total"]
        max_abs_strain = max(max_abs_strain, signal["max_abs_strain"])
    active_work = np.zeros(nt)
    dissipation = np.zeros(nt)
    energy_residual = np.zeros(nt)
    for step in range(nt):
        delta_alpha = float(alpha_series[step + 1] - alpha_series[step])
        alpha_mid = 0.5 * float(alpha_series[step + 1] + alpha_series[step])
        strain_mid = 0.5 * (final_eps[step + 1] + final_eps[step])
        active_work[step] = _active_work_step(system, strain_mid, alpha_mid, delta_alpha)
        delta_z = final_z[step + 1] - final_z[step]
        zdot = delta_z / dt
        dissipation[step] = float(dt * tau * np.sum(
            system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", zdot, C_M, zdot)
        ))
        energy_residual[step] = energy[step + 1] - energy[step] + dissipation[step] - active_work[step]
    energy_scale = max(float(np.sum(np.abs(active_work))), W_REF)
    energy_relative = float(abs(np.sum(energy_residual)) / energy_scale)

    interface_max_force = 0.0
    interface_max_moment = 0.0
    interface_max_power = 0.0
    for step in range(nt):
        state_mid = 0.5 * (final_q[step + 1] + final_q[step])
        z_mid = 0.5 * (final_z[step + 1] + final_z[step])
        alpha_mid = 0.5 * float(alpha_series[step + 1] + alpha_series[step])
        f_myo = np.asarray(
            system.k_myo @ state_mid - system.active_unit * alpha_mid
        ).ravel()
        f_ecm = (
            system.k_eq @ state_mid
            + system.k_m @ state_mid
            - np.asarray(system.ecm_map.T @ (system.ecm_weight_m @ z_mid.reshape(-1))).ravel()
        )
        f_endo = system.k_endo @ state_mid
        increment = final_q[step + 1] - final_q[step]
        for name, first_force, second_force in (
            ("myo_ecm", f_myo, f_ecm),
            ("ecm_endo", f_ecm, f_endo),
        ):
            full_nodes = system.interface_nodes[name][:-1]
            qx = system.node_wx[full_nodes]
            qy = system.node_wy[full_nodes]
            residual_x = first_force[qx] + second_force[qx]
            residual_y = first_force[qy] + second_force[qy]
            total_x = float(np.sum(residual_x))
            total_y = float(np.sum(residual_y))
            force_error = math.hypot(total_x, total_y) / SIGMA_REF
            xy = system.coordinates[full_nodes]
            moment = float(np.sum(xy[:, 0] * residual_y - xy[:, 1] * residual_x))
            velocity_x = (increment[qx] + increment[system.macro_index] * xy[:, 0]) / dt
            velocity_y = increment[qy] / dt
            power = float(np.dot(residual_x, velocity_x) + np.dot(residual_y, velocity_y))
            interface_max_force = max(interface_max_force, force_error)
            interface_max_moment = max(interface_max_moment, abs(moment) / (SIGMA_REF * 1.0))
            interface_max_power = max(interface_max_power, abs(power) / W_REF)

    q_harmonic = _fundamental(final_q)
    eps_harmonic = _fundamental(final_eps)
    z_harmonic = _fundamental(final_z)
    displacement_harmonic = _flat_displacement(system, q_harmonic)
    layer_harmonic = np.asarray([
        _weighted_average(eps_harmonic[ids], system.areas[ids])
        for ids in (system.myo_cells, system.ecm_cells, system.endo_cells)
    ])
    local_harmonic: list[ComplexArray] = []
    stress_harmonic = np.zeros_like(eps_harmonic)
    stress_harmonic[system.myo_cells] = (eps_harmonic[system.myo_cells] - ALPHA_MEAN * system.p_mean[system.myo_cells, None] * EX) @ C_MYO.T
    stress_harmonic[system.ecm_cells] = eps_harmonic[system.ecm_cells] @ C_EQ.T + (eps_harmonic[system.ecm_cells] - z_harmonic) @ C_M.T
    stress_harmonic[system.endo_cells] = eps_harmonic[system.endo_cells] @ C_ENDO.T
    for ids in (system.ecm_cells, system.endo_cells):
        for left, right in ((-0.375, -0.125), (0.125, 0.375)):
            selected = ids[(system.centroids[ids, 0] >= left) & (system.centroids[ids, 0] <= right)]
            local_harmonic.append(np.concatenate([
                _weighted_average(eps_harmonic[selected], system.areas[selected]),
                _weighted_average(stress_harmonic[selected], system.areas[selected]),
            ]))

    elapsed = time.perf_counter() - started
    return {
        "kind": "time_domain",
        "level": system.level.label,
        "profile": system.profile,
        "orientation": system.orientation,
        "nt": nt,
        "tau": tau,
        "cycles": cycle,
        "cycle_difference": cycle_difference,
        "factorizations": 1,
        "rhs_count": rhs_count,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": elapsed,
        "maximum_backward_residual": maximum_backward,
        "maximum_constraint_residual": maximum_constraint,
        "energy_relative_residual": energy_relative,
        "minimum_dissipation": float(np.min(dissipation)),
        "interface_max_force_mismatch": interface_max_force,
        "interface_max_moment_mismatch": interface_max_moment,
        "interface_max_power_mismatch": interface_max_power,
        "cycle_active_work": float(np.sum(active_work)),
        "cycle_dissipation": float(np.sum(dissipation)),
        "max_abs_strain": max_abs_strain,
        "ebar_harmonic": complex(q_harmonic[system.macro_index]),
        "layer_strain_harmonic": layer_harmonic,
        "local_harmonic": np.asarray(local_harmonic),
        "q_harmonic": q_harmonic,
        "strain_harmonic": eps_harmonic,
        "displacement_harmonic": displacement_harmonic,
        "time": np.arange(nt + 1) / nt,
        "alpha": alpha_series,
        "ebar": ebar,
        "top_l2": top_l2,
        "layer_strain": layer_strain,
        "local_values": local_values,
        "energy": energy,
        "active_work_steps": active_work,
        "dissipation_steps": dissipation,
        "energy_residual_steps": energy_residual,
    }


def reduced_modulus(matrix: NDArray) -> complex:
    return complex(matrix[0, 0] - matrix[0, 1] * matrix[1, 0] / matrix[1, 1])


def uniform_reference(tau: float = 0.20, maxwell: bool = True) -> dict[str, Any]:
    g = (1.0j * OMEGA * tau / (1.0 + 1.0j * OMEGA * tau)) if maxwell else 0.0j
    c_ecm = C_EQ.astype(np.complex128) + g * C_M if maxwell else C_EQ.astype(np.complex128)
    d_m = reduced_modulus(C_MYO)
    d_e = reduced_modulus(c_ecm)
    d_n = reduced_modulus(C_ENDO)
    heights = np.asarray([0.20, 0.30, 0.05])
    denominator = heights[0] * d_m + heights[1] * d_e + heights[2] * d_n
    ebar_h = heights[0] * d_m * ALPHA_MEAN / denominator
    ebar_dc = heights[0] * d_m * (-ALPHA_MEAN) / (
        heights[0] * d_m + heights[1] * reduced_modulus(C_EQ) + heights[2] * d_n
    )
    strain_h = np.zeros((3, 3), dtype=np.complex128)
    strain_dc = np.zeros((3, 3), dtype=np.complex128)
    strain_h[:, 0] = ebar_h
    strain_dc[:, 0] = ebar_dc
    strain_h[0, 1] = -C_MYO[1, 0] / C_MYO[1, 1] * (ebar_h - ALPHA_MEAN)
    strain_dc[0, 1] = -C_MYO[1, 0] / C_MYO[1, 1] * (ebar_dc + ALPHA_MEAN)
    strain_h[1, 1] = -c_ecm[1, 0] / c_ecm[1, 1] * ebar_h
    strain_dc[1, 1] = -C_EQ[1, 0] / C_EQ[1, 1] * ebar_dc
    strain_h[2, 1] = -C_ENDO[1, 0] / C_ENDO[1, 1] * ebar_h
    strain_dc[2, 1] = -C_ENDO[1, 0] / C_ENDO[1, 1] * ebar_dc
    stress_m_h = C_MYO @ (strain_h[0] - ALPHA_MEAN * EX)
    active_work = float(-math.pi * np.imag(stress_m_h[0] * np.conjugate(ALPHA_MEAN)) * heights[0])
    top_uy_h = complex(np.dot(heights, strain_h[:, 1]))
    top_l2_h = math.sqrt(abs(ebar_h) ** 2 / 12.0 + abs(top_uy_h) ** 2)
    return {
        "ebar_harmonic": ebar_h,
        "ebar_dc": ebar_dc,
        "layer_strain_harmonic": strain_h,
        "layer_strain_dc": strain_dc,
        "top_displacement_l2_harmonic": top_l2_h,
        "cycle_active_work": active_work,
        "ecm_complex_matrix": c_ecm,
    }


def flat_frequency(system: FlatSystem, tau: float = 0.20, maxwell: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    g = (1.0j * OMEGA * tau / (1.0 + 1.0j * OMEGA * tau)) if maxwell else 0.0j
    stiffness = (system.k_myo + system.k_eq + system.k_endo).astype(np.complex128) + g * system.k_m
    matrix = _kkt(stiffness, system.constraints.astype(np.complex128))
    # alpha(t)=alpha_mean(1-cos wt), hence alpha_hat=-alpha_mean.
    rhs = np.concatenate([system.active_unit.astype(np.complex128) * (-ALPHA_MEAN), np.zeros(system.constraints.shape[0], dtype=np.complex128)])
    factor_start = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_start
    solve_start = time.perf_counter()
    solution = factor.solve(rhs)
    solve_seconds = time.perf_counter() - solve_start
    q = solution[: system.mechanical_size]
    strain = np.asarray(system.strain_map @ q).reshape(-1, 3)
    return {
        "kind": "frequency_domain",
        "level": system.level.label,
        "profile": system.profile,
        "orientation": system.orientation,
        "tau": tau,
        "maxwell": maxwell,
        "factorizations": 1,
        "rhs_count": 1,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": time.perf_counter() - started,
        "maximum_backward_residual": _normwise_backward(matrix, solution, rhs),
        "maximum_constraint_residual": float(np.max(np.abs(system.constraints @ q))),
        "ebar_harmonic": complex(q[system.macro_index]),
        "q_harmonic": q,
        "strain_harmonic": strain,
        "displacement_harmonic": _flat_displacement(system, q),
    }


def patch_and_zero_checks() -> dict[str, Any]:
    started = time.perf_counter()
    system = build_flat_system("G0", "U")
    stiffness = system.k_myo + system.k_eq + system.k_endo + system.k_m
    matrix = _kkt(stiffness, system.constraints)
    rhs = np.zeros(matrix.shape[0])
    solution = spla.spsolve(matrix, rhs)
    zero_error = float(np.max(np.abs(solution)))

    points = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    local_B, _ = _triangle_B(points)
    target = np.asarray([0.012, -0.004, 0.006])
    nodal = np.asarray([[0.0, 0.0], [target[0], 0.5 * target[2]], [0.5 * target[2], target[1]]]).reshape(-1)
    recovered = local_B @ nodal
    patch_error = float(np.max(np.abs(recovered - target)) / EPS_REF)
    return {
        "zero_normalized_error": zero_error / U_REF,
        "patch_normalized_error": patch_error,
        "zero_pass": zero_error / U_REF <= 1.0e-8,
        "patch_pass": patch_error <= 1.0e-8,
        "protocol_count": 2,
        "factorizations": 1,
        "rhs_count": 1,
        "accounting_note": "ZERO uses one sparse solve; PATCH is a fully prescribed affine kinematic recovery and therefore uses zero factorization/RHS rather than the frozen estimate of one.",
        "wall_seconds": time.perf_counter() - started,
    }


def _phase_error_degrees(value: complex, reference: complex) -> float:
    return abs(math.degrees(math.atan2((value / reference).imag, (value / reference).real)))


def _complex_error(value: complex, reference: complex, scale: float) -> float:
    return float(abs(value - reference) / max(abs(reference), scale))


def uniform_reference_gate(result: dict[str, Any]) -> dict[str, Any]:
    reference = uniform_reference(float(result["tau"]))
    errors: dict[str, float] = {
        "ebar": _complex_error(result["ebar_harmonic"], reference["ebar_harmonic"], EPS_REF),
        "active_work": abs(result["cycle_active_work"] - reference["cycle_active_work"]) / max(abs(reference["cycle_active_work"]), W_REF),
    }
    for layer in range(3):
        errors[f"layer_{layer}_eps_xx"] = _complex_error(
            complex(result["layer_strain_harmonic"][layer, 0]),
            complex(reference["layer_strain_harmonic"][layer, 0]),
            EPS_REF,
        )
        errors[f"layer_{layer}_eps_yy"] = _complex_error(
            complex(result["layer_strain_harmonic"][layer, 1]),
            complex(reference["layer_strain_harmonic"][layer, 1]),
            EPS_REF,
        )
    phases = {
        "ebar": _phase_error_degrees(result["ebar_harmonic"], reference["ebar_harmonic"])
    }
    return {
        "errors": errors,
        "phase_errors_degrees": phases,
        "maximum_error": max(errors.values()),
        "maximum_phase_error_degrees": max(phases.values()),
        "pass": max(errors.values()) <= 1.0e-3 and max(phases.values()) <= 0.2,
        "reference": reference,
    }


def time_convergence_gate(results: dict[int, dict[str, Any]]) -> dict[str, Any]:
    reference = uniform_reference()
    errors = {
        nt: abs(complex(result["ebar_harmonic"]) - reference["ebar_harmonic"])
        for nt, result in results.items()
    }
    orders = {
        "64_to_128": math.log(errors[64] / errors[128], 2.0),
        "128_to_256": math.log(errors[128] / errors[256], 2.0),
    }
    floor = 1.0e-7
    floor_case = errors[256] <= floor
    passed = errors[256] / EPS_REF <= 1.0e-3 and (
        floor_case or all(1.8 <= value <= 2.2 for value in orders.values())
    )
    return {
        "absolute_errors": errors,
        "orders": orders,
        "error_floor_rule_applied": floor_case,
        "pass": passed,
    }


def _spatial_qoi(result: dict[str, Any]) -> dict[str, tuple[complex, float, str]]:
    out: dict[str, tuple[complex, float, str]] = {
        "ebar": (complex(result["ebar_harmonic"]), EPS_REF, "overall"),
    }
    for layer in range(3):
        for component in range(2):
            out[f"layer_{layer}_eps_{component}"] = (
                complex(result["layer_strain_harmonic"][layer, component]), EPS_REF, "overall"
            )
    for region in range(4):
        for component in range(6):
            scale = EPS_REF if component < 3 else SIGMA_REF
            out[f"local_{region}_{component}"] = (
                complex(result["local_harmonic"][region, component]), scale, "local"
            )
    return out


def spatial_gate(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    q0, q1, q2 = (_spatial_qoi(results[label]) for label in ("G0", "G1", "G2"))
    records: dict[str, Any] = {}
    passed = True
    for name, (value2, scale, group) in q2.items():
        value0, value1 = q0[name][0], q1[name][0]
        d01 = abs(value1 - value0) / scale
        d12 = abs(value2 - value1) / scale
        threshold = 0.005 if group == "overall" else 0.01
        floor_case = max(d01, d12) <= threshold / 100.0
        ratio = 0.0 if floor_case else d12 / max(d01, 1.0e-30)
        item_pass = d12 <= threshold and (floor_case or ratio <= 0.7)
        passed = passed and item_pass
        records[name] = {
            "group": group,
            "g0_g1": d01,
            "g1_g2": d12,
            "ratio": ratio,
            "error_floor_rule_applied": floor_case,
            "pass": item_pass,
        }
    return {"readouts": records, "pass": passed}


def mirror_gate(primary: dict[str, Any], mirrored: dict[str, Any], system_primary: FlatSystem, system_mirror: FlatSystem) -> dict[str, Any]:
    tree = cKDTree(system_mirror.coordinates)
    reflected = system_primary.coordinates.copy()
    reflected[:, 0] *= -1.0
    distances, indices = tree.query(reflected)
    if float(np.max(distances)) > 1.0e-12:
        raise RuntimeError("mirror node map failed")
    expected = primary["displacement_harmonic"].copy()
    expected[:, 0] *= -1.0
    displacement_error = float(np.linalg.norm(mirrored["displacement_harmonic"][indices] - expected) / max(np.linalg.norm(expected), U_REF * math.sqrt(expected.size)))

    cell_tree = cKDTree(system_mirror.centroids)
    reflected_cells = system_primary.centroids.copy()
    reflected_cells[:, 0] *= -1.0
    cell_distances, cell_indices = cell_tree.query(reflected_cells)
    if float(np.max(cell_distances)) > 1.0e-12:
        raise RuntimeError("mirror cell map failed")
    expected_strain = primary["strain_harmonic"].copy()
    expected_strain[:, 2] *= -1.0
    strain_error = float(np.linalg.norm(mirrored["strain_harmonic"][cell_indices] - expected_strain) / max(np.linalg.norm(expected_strain), EPS_REF * math.sqrt(expected_strain.size)))
    maximum = max(displacement_error, strain_error)
    return {
        "displacement_error": displacement_error,
        "strain_error": strain_error,
        "maximum_error": maximum,
        "pass": maximum <= 1.0e-8,
    }


def _isotropic_lame(young: float, poisson: float) -> tuple[float, float]:
    return (
        young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson)),
        young / (2.0 * (1.0 + poisson)),
    )


def build_annulus_system(
    level_label: str, angle_offset_degrees: float = 0.0
) -> AnnulusSystem:
    level = ANNULUS_LEVELS[level_label]
    radii = np.concatenate([
        np.linspace(1.0, 1.05, level.nr_endo + 1),
        np.linspace(1.05, 1.35, level.nr_ecm + 1)[1:],
        np.linspace(1.35, 1.55, level.nr_myo + 1)[1:],
    ])
    theta = angle_offset_degrees * math.pi / 180.0 + 2.0 * math.pi * np.arange(level.ntheta) / level.ntheta
    coordinates = np.asarray(
        [[radius * math.cos(value), radius * math.sin(value)] for radius in radii for value in theta],
        dtype=np.float64,
    )

    def node(itheta: int, iradius: int) -> int:
        return iradius * level.ntheta + (itheta % level.ntheta)

    cells: list[list[int]] = []
    layers: list[int] = []
    for iradius in range(len(radii) - 1):
        layer_id = 2 if iradius < level.nr_endo else (
            1 if iradius < level.nr_endo + level.nr_ecm else 0
        )
        for itheta in range(level.ntheta):
            n00 = node(itheta, iradius)
            n10 = node(itheta + 1, iradius)
            n01 = node(itheta, iradius + 1)
            n11 = node(itheta + 1, iradius + 1)
            cells.extend(([n00, n01, n11], [n00, n11, n10]))
            layers.extend((layer_id, layer_id))
    cell_array = np.asarray(cells, dtype=np.int64)
    layer_array = np.asarray(layers, dtype=np.int8)
    mechanical_size = 2 * len(coordinates)
    row_index: list[int] = []
    column_index: list[int] = []
    values: list[float] = []
    areas: list[float] = []
    centroids: list[FloatArray] = []
    active_direction: list[FloatArray] = []
    nodal_weights = np.zeros(len(coordinates), dtype=np.float64)
    bary = np.asarray(
        [[2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0],
         [1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0],
         [1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0]],
        dtype=np.float64,
    )
    for cell_id, connectivity in enumerate(cell_array):
        points = coordinates[connectivity]
        local_B, area = _triangle_B(points)
        areas.append(area)
        centroids.append(np.mean(points, axis=0))
        quadrature_points = bary @ points
        directions = []
        for x, y in quadrature_points:
            angle = math.atan2(y, x)
            sine, cosine = math.sin(angle), math.cos(angle)
            directions.append(np.asarray([-sine * sine, -cosine * cosine, 2.0 * sine * cosine]))
        active_direction.append(np.mean(directions, axis=0))
        for local, full_node in enumerate(connectivity):
            for component in range(2):
                global_dof = 2 * int(full_node) + component
                for strain_component in range(3):
                    coefficient = float(local_B[strain_component, 2 * local + component])
                    if coefficient:
                        row_index.append(3 * cell_id + strain_component)
                        column_index.append(global_dof)
                        values.append(coefficient)
            nodal_weights[full_node] += area / 3.0
    area_array = np.asarray(areas)
    centroid_array = np.asarray(centroids)
    direction_array = np.asarray(active_direction)
    strain_map = sp.coo_matrix(
        (values, (row_index, column_index)),
        shape=(3 * len(cell_array), mechanical_size),
    ).tocsr()
    total_weight = float(np.sum(nodal_weights))
    rotation_scale = float(np.sum(nodal_weights * np.sum(coordinates * coordinates, axis=1)))
    constraints_dense = np.zeros((3, mechanical_size), dtype=np.float64)
    constraints_dense[0, 0::2] = nodal_weights / total_weight
    constraints_dense[1, 1::2] = nodal_weights / total_weight
    constraints_dense[2, 0::2] = -nodal_weights * coordinates[:, 1] / rotation_scale
    constraints_dense[2, 1::2] = nodal_weights * coordinates[:, 0] / rotation_scale
    constraints = sp.csr_matrix(constraints_dense)
    myo_cells = np.flatnonzero(layer_array == 0)
    ecm_cells = np.flatnonzero(layer_array == 1)
    endo_cells = np.flatnonzero(layer_array == 2)

    def layer_map(ids: NDArray[np.int64]) -> sp.csr_matrix:
        rows = np.asarray([3 * cell + k for cell in ids for k in range(3)], dtype=np.int64)
        return strain_map[rows]

    def layer_stiffness(ids: NDArray[np.int64], constitutive: FloatArray) -> sp.csr_matrix:
        mapping = layer_map(ids)
        return (mapping.T @ _block_weight(area_array[ids], constitutive) @ mapping).tocsr()

    k_myo = layer_stiffness(myo_cells, C_MYO)
    k_eq = layer_stiffness(ecm_cells, C_EQ)
    k_m = layer_stiffness(ecm_cells, C_M)
    k_endo = layer_stiffness(endo_cells, C_ENDO)
    ecm_map = layer_map(ecm_cells)
    ecm_weight_m = _block_weight(area_array[ecm_cells], C_M)
    active_unit = np.zeros(mechanical_size, dtype=np.float64)
    for cell in myo_cells:
        rows = slice(3 * int(cell), 3 * int(cell) + 3)
        active_unit += np.asarray(
            strain_map[rows].T
            @ (area_array[cell] * (C_MYO @ direction_array[cell]))
        ).ravel()
    return AnnulusSystem(
        level=level,
        angle_offset_degrees=angle_offset_degrees,
        coordinates=coordinates,
        cells=cell_array,
        cell_layers=layer_array,
        areas=area_array,
        centroids=centroid_array,
        strain_map=strain_map,
        constraints=constraints,
        k_myo=k_myo,
        k_eq=k_eq,
        k_m=k_m,
        k_endo=k_endo,
        active_unit=active_unit,
        active_direction=direction_array,
        mechanical_size=mechanical_size,
        myo_cells=myo_cells,
        ecm_cells=ecm_cells,
        endo_cells=endo_cells,
        ecm_map=ecm_map,
        ecm_weight_m=ecm_weight_m,
        interface_nodes={
            "endo_ecm": np.asarray([node(itheta, level.nr_endo) for itheta in range(level.ntheta)]),
            "ecm_myo": np.asarray([node(itheta, level.nr_endo + level.nr_ecm) for itheta in range(level.ntheta)]),
        },
        inner_nodes=np.asarray([node(itheta, 0) for itheta in range(level.ntheta)]),
    )


def _annulus_polar_strain(system: AnnulusSystem, strain: NDArray) -> NDArray:
    angle = np.arctan2(system.centroids[:, 1], system.centroids[:, 0])
    cosine, sine = np.cos(angle), np.sin(angle)
    radial = cosine * cosine * strain[:, 0] + sine * sine * strain[:, 1] + cosine * sine * strain[:, 2]
    hoop = sine * sine * strain[:, 0] + cosine * cosine * strain[:, 1] - cosine * sine * strain[:, 2]
    return np.column_stack([radial, hoop])


def _annulus_readouts(system: AnnulusSystem, state: NDArray, strain: NDArray) -> dict[str, Any]:
    displacement = np.asarray(state).reshape(-1, 2)
    inner_xy = system.coordinates[system.inner_nodes]
    inner_radial = np.sum(displacement[system.inner_nodes] * inner_xy, axis=1)
    polar = _annulus_polar_strain(system, strain)
    layer_polar = np.asarray([
        _weighted_average(polar[ids], system.areas[ids])
        for ids in (system.endo_cells, system.ecm_cells, system.myo_cells)
    ])
    return {
        "inner_radial": np.mean(inner_radial),
        "layer_polar_strain": layer_polar,
        "displacement": displacement,
        "polar_strain": polar,
    }


def annulus_frequency(system: AnnulusSystem, tau: float = 0.20) -> dict[str, Any]:
    started = time.perf_counter()
    g = 1.0j * OMEGA * tau / (1.0 + 1.0j * OMEGA * tau)
    stiffness = (system.k_myo + system.k_eq + system.k_endo).astype(np.complex128) + g * system.k_m
    matrix = _kkt(stiffness, system.constraints.astype(np.complex128))
    rhs = np.concatenate([
        system.active_unit.astype(np.complex128) * (-ALPHA_MEAN),
        np.zeros(system.constraints.shape[0], dtype=np.complex128),
    ])
    factor_start = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_start
    solve_start = time.perf_counter()
    solution = factor.solve(rhs)
    solve_seconds = time.perf_counter() - solve_start
    state = solution[: system.mechanical_size]
    strain = np.asarray(system.strain_map @ state).reshape(-1, 3)
    readouts = _annulus_readouts(system, state, strain)
    return {
        "kind": "frequency_domain",
        "level": system.level.label,
        "angle_offset_degrees": system.angle_offset_degrees,
        "tau": tau,
        "factorizations": 1,
        "rhs_count": 1,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": time.perf_counter() - started,
        "maximum_backward_residual": _normwise_backward(matrix, solution, rhs),
        "maximum_constraint_residual": float(np.max(np.abs(system.constraints @ state))),
        "inner_radial_harmonic": complex(readouts["inner_radial"]),
        "layer_polar_strain_harmonic": readouts["layer_polar_strain"],
        "state_harmonic": state,
        "strain_harmonic": strain,
        "displacement_harmonic": readouts["displacement"],
        "polar_strain_harmonic": readouts["polar_strain"],
    }


def _annulus_energy(
    system: AnnulusSystem,
    strain: FloatArray,
    z_ecm: FloatArray,
    alpha: float,
) -> float:
    ids = system.myo_cells
    direction = system.active_direction[ids]
    myo_strain = strain[ids]
    elastic = myo_strain - alpha * direction
    myo = 0.5 * np.sum(system.areas[ids] * np.einsum("ni,ij,nj->n", elastic, C_MYO, elastic))
    ecm_strain = strain[system.ecm_cells]
    ecm_eq = 0.5 * np.sum(system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", ecm_strain, C_EQ, ecm_strain))
    maxwell = ecm_strain - z_ecm
    ecm_m = 0.5 * np.sum(system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", maxwell, C_M, maxwell))
    endo_strain = strain[system.endo_cells]
    endo = 0.5 * np.sum(system.areas[system.endo_cells] * np.einsum("ni,ij,nj->n", endo_strain, C_ENDO, endo_strain))
    return float(myo + ecm_eq + ecm_m + endo)


def run_annulus_trajectory(
    system: AnnulusSystem,
    nt: int,
    tau: float = 0.20,
    max_cycles: int = 20,
    convergence_target: float = 1.0e-9,
) -> dict[str, Any]:
    started = time.perf_counter()
    dt = 1.0 / nt
    a = (2.0 * tau - dt) / (2.0 * tau + dt)
    b = dt / (2.0 * tau + dt)
    stiffness = system.k_myo + system.k_eq + system.k_endo + (1.0 - b) * system.k_m
    matrix = _kkt(stiffness, system.constraints)
    factor_start = time.perf_counter()
    factor = spla.splu(matrix)
    factor_seconds = time.perf_counter() - factor_start
    state = np.zeros(system.mechanical_size)
    strain = np.zeros((len(system.cells), 3))
    z_ecm = np.zeros((len(system.ecm_cells), 3))
    previous_q = previous_z = None
    maximum_backward = maximum_constraint = solve_seconds = 0.0
    rhs_count = 0
    cycle_difference = math.inf
    final_q = final_z = final_eps = None
    for cycle in range(1, max_cycles + 1):
        q_cycle = np.zeros((nt + 1, system.mechanical_size))
        z_cycle = np.zeros((nt + 1, len(system.ecm_cells), 3))
        eps_cycle = np.zeros((nt + 1, len(system.cells), 3))
        q_cycle[0], z_cycle[0], eps_cycle[0] = state, z_ecm, strain
        for step in range(1, nt + 1):
            alpha = ALPHA_MEAN * (1.0 - math.cos(2.0 * math.pi * step / nt))
            history = a * z_ecm + b * strain[system.ecm_cells]
            rhs_mechanical = system.active_unit * alpha + np.asarray(
                system.ecm_map.T @ (system.ecm_weight_m @ history.reshape(-1))
            ).ravel()
            rhs = np.concatenate([rhs_mechanical, np.zeros(system.constraints.shape[0])])
            solve_start = time.perf_counter()
            solution = factor.solve(rhs)
            solve_seconds += time.perf_counter() - solve_start
            rhs_count += 1
            maximum_backward = max(maximum_backward, _normwise_backward(matrix, solution, rhs))
            state_next = solution[: system.mechanical_size]
            maximum_constraint = max(maximum_constraint, float(np.max(np.abs(system.constraints @ state_next))))
            strain_next = np.asarray(system.strain_map @ state_next).reshape(-1, 3)
            z_next = a * z_ecm + b * (strain[system.ecm_cells] + strain_next[system.ecm_cells])
            state, strain, z_ecm = state_next, strain_next, z_next
            q_cycle[step], z_cycle[step], eps_cycle[step] = state, z_ecm, strain
        if previous_q is not None and previous_z is not None:
            cycle_difference = max(
                float(np.linalg.norm(q_cycle - previous_q) / max(np.linalg.norm(q_cycle), U_REF * math.sqrt(q_cycle.size))),
                float(np.linalg.norm(z_cycle - previous_z) / max(np.linalg.norm(z_cycle), EPS_REF * math.sqrt(z_cycle.size))),
            )
        previous_q, previous_z = q_cycle, z_cycle
        final_q, final_z, final_eps = q_cycle, z_cycle, eps_cycle
        if cycle >= 2 and cycle_difference <= convergence_target:
            break
    assert final_q is not None and final_z is not None and final_eps is not None
    alpha_series = ALPHA_MEAN * (1.0 - np.cos(2.0 * math.pi * np.arange(nt + 1) / nt))
    energy = np.asarray([
        _annulus_energy(system, final_eps[index], final_z[index], float(alpha_series[index]))
        for index in range(nt + 1)
    ])
    active_work = np.zeros(nt)
    dissipation = np.zeros(nt)
    residual = np.zeros(nt)
    max_abs_strain = float(np.max(np.abs(final_eps)))
    interface_max = 0.0
    for step in range(nt):
        strain_mid = 0.5 * (final_eps[step + 1] + final_eps[step])
        z_mid = 0.5 * (final_z[step + 1] + final_z[step])
        delta_alpha = float(alpha_series[step + 1] - alpha_series[step])
        alpha_mid = 0.5 * float(alpha_series[step + 1] + alpha_series[step])
        ids = system.myo_cells
        stress_myo = (strain_mid[ids] - alpha_mid * system.active_direction[ids]) @ C_MYO.T
        active_work[step] = float(-delta_alpha * np.sum(
            system.areas[ids] * np.einsum("ni,ni->n", stress_myo, system.active_direction[ids])
        ))
        zdot = (final_z[step + 1] - final_z[step]) / dt
        dissipation[step] = float(dt * tau * np.sum(
            system.areas[system.ecm_cells] * np.einsum("ni,ij,nj->n", zdot, C_M, zdot)
        ))
        residual[step] = energy[step + 1] - energy[step] + dissipation[step] - active_work[step]

        state_mid = 0.5 * (final_q[step + 1] + final_q[step])
        f_myo = np.asarray(system.k_myo @ state_mid - system.active_unit * alpha_mid).ravel()
        f_ecm = np.asarray(
            system.k_eq @ state_mid + system.k_m @ state_mid
            - system.ecm_map.T @ (system.ecm_weight_m @ z_mid.reshape(-1))
        ).ravel()
        f_endo = np.asarray(system.k_endo @ state_mid).ravel()
        increment = final_q[step + 1] - final_q[step]
        for name, first_force, second_force in (
            ("endo_ecm", f_endo, f_ecm),
            ("ecm_myo", f_ecm, f_myo),
        ):
            nodes = system.interface_nodes[name]
            residual_force = (first_force + second_force).reshape(-1, 2)[nodes]
            total_force = np.sum(residual_force, axis=0)
            moment = float(np.sum(
                system.coordinates[nodes, 0] * residual_force[:, 1]
                - system.coordinates[nodes, 1] * residual_force[:, 0]
            ))
            velocity = increment.reshape(-1, 2)[nodes] / dt
            power = float(np.sum(residual_force * velocity))
            interface_max = max(
                interface_max,
                float(np.linalg.norm(total_force) / SIGMA_REF),
                abs(moment) / (SIGMA_REF * 1.55),
                abs(power) / W_REF,
            )
    state_h = _fundamental(final_q)
    strain_h = _fundamental(final_eps)
    readouts = _annulus_readouts(system, state_h, strain_h)
    return {
        "kind": "time_domain",
        "level": system.level.label,
        "nt": nt,
        "tau": tau,
        "cycles": cycle,
        "cycle_difference": cycle_difference,
        "factorizations": 1,
        "rhs_count": rhs_count,
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "wall_seconds": time.perf_counter() - started,
        "maximum_backward_residual": maximum_backward,
        "maximum_constraint_residual": maximum_constraint,
        "energy_relative_residual": float(abs(np.sum(residual)) / max(float(np.sum(np.abs(active_work))), W_REF)),
        "minimum_dissipation": float(np.min(dissipation)),
        "interface_max_mismatch": interface_max,
        "cycle_active_work": float(np.sum(active_work)),
        "cycle_dissipation": float(np.sum(dissipation)),
        "max_abs_strain": max_abs_strain,
        "inner_radial_harmonic": complex(readouts["inner_radial"]),
        "layer_polar_strain_harmonic": readouts["layer_polar_strain"],
        "state_harmonic": state_h,
        "strain_harmonic": strain_h,
        "displacement_harmonic": readouts["displacement"],
        "polar_strain_harmonic": readouts["polar_strain"],
        "energy": energy,
        "active_work_steps": active_work,
        "dissipation_steps": dissipation,
        "energy_residual_steps": residual,
    }


def annulus_reference(tau: float = 0.20) -> dict[str, Any]:
    lame_myo = tuple(complex(value) for value in _isotropic_lame(*MATERIAL["myocardium"]))
    lame_endo = tuple(complex(value) for value in _isotropic_lame(*MATERIAL["endocardium"]))
    eq = _isotropic_lame(*MATERIAL["ecm_eq"])
    maxwell = _isotropic_lame(*MATERIAL["ecm_m"])
    g = 1.0j * OMEGA * tau / (1.0 + 1.0j * OMEGA * tau)
    lame_ecm = (complex(eq[0] + g * maxwell[0]), complex(eq[1] + g * maxwell[1]))
    layers = (
        (1.0, 1.05, lame_endo, 0.0j),
        (1.05, 1.35, lame_ecm, 0.0j),
        (1.35, 1.55, lame_myo, complex(-ALPHA_MEAN)),
    )

    def particular(layer_index: int, radius: float) -> tuple[complex, complex]:
        _, _, (lame_lambda, shear), alpha = layers[layer_index]
        if alpha == 0.0j:
            return 0.0j, 0.0j
        coefficient = shear * alpha / (lame_lambda + 2.0 * shear)
        return coefficient * radius * math.log(radius), coefficient * (math.log(radius) + 1.0)

    def basis(layer_index: int, radius: float, which: int) -> tuple[complex, complex]:
        _, _, (lame_lambda, shear), alpha = layers[layer_index]
        if which == 0:
            displacement, derivative = radius, 1.0
        else:
            displacement, derivative = 1.0 / radius, -1.0 / (radius * radius)
        sigma = (lame_lambda + 2.0 * shear) * derivative + lame_lambda * displacement / radius
        return complex(displacement), complex(sigma)

    def particular_sigma(layer_index: int, radius: float) -> tuple[complex, complex]:
        displacement, derivative = particular(layer_index, radius)
        _, _, (lame_lambda, shear), alpha = layers[layer_index]
        sigma = (lame_lambda + 2.0 * shear) * derivative + lame_lambda * (displacement / radius + alpha)
        return displacement, sigma

    matrix = np.zeros((6, 6), dtype=np.complex128)
    rhs = np.zeros(6, dtype=np.complex128)
    row = 0
    # Inner free traction.
    for which in range(2):
        matrix[row, which] = basis(0, 1.0, which)[1]
    rhs[row] = -particular_sigma(0, 1.0)[1]
    row += 1
    for left_layer, right_layer, radius in ((0, 1, 1.05), (1, 2, 1.35)):
        for which in range(2):
            matrix[row, 2 * left_layer + which] = basis(left_layer, radius, which)[0]
            matrix[row, 2 * right_layer + which] = -basis(right_layer, radius, which)[0]
        rhs[row] = -particular_sigma(left_layer, radius)[0] + particular_sigma(right_layer, radius)[0]
        row += 1
        for which in range(2):
            matrix[row, 2 * left_layer + which] = basis(left_layer, radius, which)[1]
            matrix[row, 2 * right_layer + which] = -basis(right_layer, radius, which)[1]
        rhs[row] = -particular_sigma(left_layer, radius)[1] + particular_sigma(right_layer, radius)[1]
        row += 1
    for which in range(2):
        matrix[row, 4 + which] = basis(2, 1.55, which)[1]
    rhs[row] = -particular_sigma(2, 1.55)[1]
    coefficients = np.linalg.solve(matrix, rhs)
    linear_residual = float(np.linalg.norm(matrix @ coefficients - rhs, ord=np.inf) / max(np.linalg.norm(rhs, ord=np.inf), 1.0))

    def evaluate(layer_index: int, radius: NDArray) -> tuple[NDArray, NDArray, NDArray]:
        a_value, b_value = coefficients[2 * layer_index:2 * layer_index + 2]
        _, _, (lame_lambda, shear), alpha = layers[layer_index]
        coefficient = shear * alpha / (lame_lambda + 2.0 * shear) if alpha != 0.0j else 0.0j
        displacement = a_value * radius + b_value / radius + coefficient * radius * np.log(radius)
        radial = a_value - b_value / (radius * radius) + coefficient * (np.log(radius) + 1.0)
        hoop = displacement / radius
        return displacement, radial, hoop

    def quadrature(order: int) -> NDArray:
        nodes, weights = np.polynomial.legendre.leggauss(order)
        output = []
        for layer_index, (inner, outer, _, _) in enumerate(layers):
            radius = 0.5 * (outer - inner) * nodes + 0.5 * (outer + inner)
            scaled_weights = 0.5 * (outer - inner) * weights
            _, radial, hoop = evaluate(layer_index, radius)
            denominator = 0.5 * (outer * outer - inner * inner)
            output.append([
                np.sum(scaled_weights * radius * radial) / denominator,
                np.sum(scaled_weights * radius * hoop) / denominator,
            ])
        return np.asarray(output)

    average_128 = quadrature(128)
    average_256 = quadrature(256)
    reference_error = float(np.max(np.abs(average_256 - average_128)) / EPS_REF)
    inner_displacement = complex(evaluate(0, np.asarray([1.0]))[0][0])
    return {
        "inner_radial_harmonic": inner_displacement,
        "layer_polar_strain_harmonic": average_256,
        "coefficients": coefficients,
        "linear_residual": linear_residual,
        "quadrature_self_error": reference_error,
        "pass": linear_residual <= 1.0e-12 and reference_error <= 1.0e-4,
    }


def annulus_reference_gate(result: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    errors = {
        "inner_radial": _complex_error(
            complex(result["inner_radial_harmonic"]),
            complex(reference["inner_radial_harmonic"]),
            U_REF,
        )
    }
    phases = {
        "inner_radial": _phase_error_degrees(
            complex(result["inner_radial_harmonic"]),
            complex(reference["inner_radial_harmonic"]),
        )
    }
    for layer in range(3):
        for component in range(2):
            errors[f"layer_{layer}_{component}"] = _complex_error(
                complex(result["layer_polar_strain_harmonic"][layer, component]),
                complex(reference["layer_polar_strain_harmonic"][layer, component]),
                EPS_REF,
            )
    return {
        "errors": errors,
        "phase_errors_degrees": phases,
        "maximum_error": max(errors.values()),
        "maximum_phase_error_degrees": max(phases.values()),
        "reference_self_check": {
            "linear_residual": reference["linear_residual"],
            "quadrature_self_error": reference["quadrature_self_error"],
            "pass": reference["pass"],
        },
        "pass": reference["pass"] and max(errors.values()) <= 1.0e-3 and max(phases.values()) <= 0.2,
    }


def annulus_spatial_gate(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def qois(result: dict[str, Any]) -> dict[str, tuple[complex, float]]:
        values = {"inner_radial": (complex(result["inner_radial_harmonic"]), U_REF)}
        for layer in range(3):
            for component in range(2):
                values[f"layer_{layer}_{component}"] = (
                    complex(result["layer_polar_strain_harmonic"][layer, component]), EPS_REF
                )
        return values
    q0, q1, q2 = (qois(results[label]) for label in ("G0", "G1", "G2"))
    records = {}
    passed = True
    for name, (value2, scale) in q2.items():
        value0, value1 = q0[name][0], q1[name][0]
        d01 = abs(value1 - value0) / scale
        d12 = abs(value2 - value1) / scale
        floor_case = max(d01, d12) <= 0.005 / 100.0
        ratio = 0.0 if floor_case else d12 / max(d01, 1.0e-30)
        item_pass = d12 <= 0.005 and (floor_case or ratio <= 0.7)
        passed = passed and item_pass
        records[name] = {
            "g0_g1": d01,
            "g1_g2": d12,
            "ratio": ratio,
            "error_floor_rule_applied": floor_case,
            "pass": item_pass,
        }
    return {"readouts": records, "pass": passed}


def annulus_rotation_gate(
    primary: dict[str, Any], rotated: dict[str, Any], angle_degrees: float
) -> dict[str, Any]:
    angle = math.radians(angle_degrees)
    rotation = np.asarray([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    expected_displacement = primary["displacement_harmonic"] @ rotation.T
    displacement_error = float(
        np.linalg.norm(rotated["displacement_harmonic"] - expected_displacement)
        / max(np.linalg.norm(expected_displacement), U_REF * math.sqrt(expected_displacement.size))
    )
    expected_polar = primary["polar_strain_harmonic"]
    polar_error = float(
        np.linalg.norm(rotated["polar_strain_harmonic"] - expected_polar)
        / max(np.linalg.norm(expected_polar), EPS_REF * math.sqrt(expected_polar.size))
    )
    maximum = max(displacement_error, polar_error)
    return {
        "displacement_error": displacement_error,
        "polar_strain_error": polar_error,
        "maximum_error": maximum,
        "pass": maximum <= 1.0e-8,
    }


def jsonable(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, np.ndarray):
        if np.iscomplexobj(value):
            return {"real": value.real.tolist(), "imag": value.imag.tolist()}
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value
