from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg


REPO_ROOT = Path(__file__).resolve().parents[1]
PAIR_RUNNER = REPO_ROOT / "scripts/run_paper2_pair_junction_probe_v01.py"
CLOSED_CELL_SOURCE = REPO_ROOT / "scripts/run_paper2_closed_cell_ritz_probe_v01.py"
PLAN_SOURCE = REPO_ROOT / "project_control/prl_independent_theory_mainline_plan_v04.md"
OUTPUT_DIRECTORY = REPO_ROOT / "results/paper2_shape_coupling_coefficients/v01_20260907"
OUTPUT_PATH = OUTPUT_DIRECTORY / "summary.json"

EXPECTED_PAIR_RUNNER_SHA256 = "4c6a4f10c992828268ef4e0175129f56dc29205ee0cd7e1ee72656736b550126"
EXPECTED_CLOSED_CELL_SHA256 = "9a0b9e738624e92559421064f99aae8979ae065dd67d112ad0bb681f85dd9eec"

CELL_COUNT = 8
U0 = 1.0e-5
BALANCE_TOLERANCE = 1.0e-8
IDENTITY_TOLERANCE = 1.0e-8
NEAR_ZERO_RATIO = 1.0e-10
EXPLORATORY_RESOLUTION_TOLERANCE = 0.05
CALCULATION_BUDGET_SECONDS = 30.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def _load_pair_runner() -> Any:
    sys.dont_write_bytecode = True
    specification = importlib.util.spec_from_file_location(
        "frozen_pair_probe_for_shape_coefficients", PAIR_RUNNER
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load pair-junction assembly source")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _matrix_sha256(matrix: sparse.csr_matrix) -> str:
    value = matrix.copy().tocsr()
    value.sum_duplicates()
    value.sort_indices()
    digest = hashlib.sha256()
    digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
    digest.update(value.indptr.astype(np.int64, copy=False).tobytes())
    digest.update(value.indices.astype(np.int64, copy=False).tobytes())
    digest.update(value.data.astype(np.float64, copy=False).tobytes())
    return digest.hexdigest()


def _peak_working_set_bytes() -> tuple[int | None, str]:
    if os.name != "nt":
        return None, "unavailable_non_windows"

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    success = ctypes.windll.psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), counters.cb
    )
    if not success:
        return None, "unavailable_GetProcessMemoryInfo_failed"
    return int(counters.PeakWorkingSetSize), "windows_peak_working_set"


def _rows_from_original_edges(module: Any) -> dict[str, list[np.ndarray]]:
    return module._load_cell_rows()


def _cell_readout_and_null_mode(cell_dofs: int, total_dofs: int) -> tuple[np.ndarray, np.ndarray]:
    readout = np.zeros(total_dofs, dtype=np.float64)
    null_mode = np.zeros(total_dofs, dtype=np.float64)
    coefficient = 1.0 / (2.0 * CELL_COUNT)
    for cell in range(CELL_COUNT):
        offset = 8 * cell
        readout[offset + 0] -= coefficient
        readout[offset + 2] -= coefficient
        readout[offset + 4] += coefficient
        readout[offset + 6] += coefficient
        null_mode[offset + 4] = 1.0
        null_mode[offset + 6] = 1.0
    if cell_dofs != 8 * CELL_COUNT:
        raise RuntimeError("unexpected cell DOF count")
    return readout, null_mode


def _geometric_source(
    module: Any,
    rows: dict[str, list[np.ndarray]],
    total_dofs: int,
) -> tuple[np.ndarray, dict[str, float], sparse.csr_matrix]:
    wave = np.cos(2.0 * math.pi * np.arange(CELL_COUNT) / CELL_COUNT)
    factor = float(module.K_EDGE / module.CELL_HEIGHT**2)
    from_rows = np.zeros(total_dofs, dtype=np.float64)
    direct = np.zeros(total_dofs, dtype=np.float64)
    side_rows: list[np.ndarray] = []

    for cell in range(CELL_COUNT):
        offset = 8 * cell
        local = wave[cell] * rows["edge"][3] + wave[(cell + 1) % CELL_COUNT] * rows["edge"][1]
        from_rows[offset : offset + 8] += factor * local

        left = np.zeros(8, dtype=np.float64)
        left[7] = 1.0
        left[1] = -1.0
        right = np.zeros(8, dtype=np.float64)
        right[5] = 1.0
        right[3] = -1.0
        direct[offset : offset + 8] += factor * (
            wave[cell] * left + wave[(cell + 1) % CELL_COUNT] * right
        )
        side_rows.extend((left, right))

    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    for cell in range(CELL_COUNT):
        offset = 8 * cell
        for local_row in (rows["edge"][1], rows["edge"][3]):
            local_matrix = factor * np.outer(local_row, local_row)
            nonzero_rows, nonzero_columns = np.nonzero(local_matrix)
            for local_i, local_j in zip(nonzero_rows, nonzero_columns):
                row_indices.append(offset + int(local_i))
                column_indices.append(offset + int(local_j))
                values.append(float(local_matrix[local_i, local_j]))
    side_matrix = sparse.coo_matrix(
        (values, (row_indices, column_indices)), shape=(total_dofs, total_dofs)
    ).tocsr()
    side_matrix.sum_duplicates()

    alpha = factor * float(
        sum(wave[cell] ** 2 + wave[(cell + 1) % CELL_COUNT] ** 2 for cell in range(CELL_COUNT))
    )
    checks = {
        "original_edge_rows_vs_direct_max_abs": float(np.max(np.abs(from_rows - direct))),
        "left_row_vs_original_edge_3_max_abs": float(
            np.max(np.abs(side_rows[0] - rows["edge"][3]))
        ),
        "right_row_vs_original_edge_1_max_abs": float(
            np.max(np.abs(side_rows[1] - rows["edge"][1]))
        ),
        "alpha": alpha,
    }
    return from_rows, checks, side_matrix


def _bottom_cosine_source(
    module: Any,
    thickness: float,
    nx: int,
    ny: int,
    total_dofs: int,
) -> tuple[np.ndarray, np.ndarray]:
    source = np.zeros(total_dofs, dtype=np.float64)
    bottom_displacement = np.zeros((nx, 2), dtype=np.float64)
    x_coordinates = -0.5 * module.BOX_LENGTH + np.arange(nx) * module.BOX_LENGTH / nx
    bottom_displacement[:, 1] = U0 * np.cos(
        2.0 * math.pi * (x_coordinates + 0.5 * module.BOX_LENGTH) / module.BOX_LENGTH
    )
    dx = module.BOX_LENGTH / nx
    dy = thickness / ny
    constitutive = module._constitutive_matrix()

    for iy in range(ny):
        for ix in range(nx):
            triangles = (
                ((ix, iy), (ix + 1, iy), (ix + 1, iy + 1)),
                ((ix, iy), (ix + 1, iy + 1), (ix, iy + 1)),
            )
            for triangle in triangles:
                coordinates = np.array(
                    [
                        (-0.5 * module.BOX_LENGTH + node_x * dx, node_y * dy)
                        for node_x, node_y in triangle
                    ],
                    dtype=np.float64,
                )
                strain, area = module._triangle_operator(coordinates)
                local_matrix = area * strain.T @ constitutive @ strain
                prescribed = np.zeros(6, dtype=np.float64)
                mappings: list[int | None] = []
                for local_node, (node_x, node_y) in enumerate(triangle):
                    if node_y == 0:
                        prescribed[2 * local_node : 2 * local_node + 2] = bottom_displacement[
                            node_x % nx
                        ]
                    mappings.extend(
                        (
                            module._ecm_free_index(node_x, node_y, 0, nx),
                            module._ecm_free_index(node_x, node_y, 1, nx),
                        )
                    )
                coupling_force = local_matrix @ prescribed
                for local_dof, free_index in enumerate(mappings):
                    if free_index is not None:
                        source[module.CELL_DOF_COUNT + int(free_index)] -= coupling_force[local_dof]
    return source, bottom_displacement


def _solution_record(solution: np.ndarray, multiplier: float, nx: int, ny: int, cell_dofs: int) -> dict[str, Any]:
    return {
        "cell_displacements_shape_8x4x2": solution[:cell_dofs].reshape(CELL_COUNT, 4, 2).tolist(),
        "ecm_free_displacements_shape_ny_nx_2": solution[cell_dofs:].reshape(ny, nx, 2).tolist(),
        "lagrange_multiplier": float(multiplier),
    }


def _normalized_ratio(numerator: float, *denominators: float) -> float:
    scale = max(*(abs(value) for value in denominators), np.finfo(np.float64).tiny)
    return abs(numerator) / scale


def _mesh_case(module: Any, rows: dict[str, list[np.ndarray]], resolution: str, nx: int, ny: int) -> tuple[dict[str, Any], int]:
    thickness = float(module.CELL_WIDTH)
    ecm_matrix, free_coordinates, mesh_metadata = module._ecm_stiffness(thickness, nx, ny)
    ecm_dofs = int(ecm_matrix.shape[0])
    total_dofs = int(module.CELL_DOF_COUNT) + ecm_dofs
    terms = module._block_cell_terms(rows, ecm_dofs)
    zero_cells = sparse.csr_matrix((module.CELL_DOF_COUNT, module.CELL_DOF_COUNT))
    terms["ecm_plane_strain"] = sparse.block_diag((zero_cells, ecm_matrix), format="csr")
    terms["cell_ecm_distributed_attachment"] = module._distributed_attachment(nx, ny, total_dofs)
    terms["cell_connections"] = module._cell_connections(total_dofs, ())

    active_term_names = (
        "cell_area",
        "cell_edge",
        "ecm_plane_strain",
        "cell_ecm_distributed_attachment",
        "cell_connections",
    )
    matrix = sum(
        (terms[name] for name in active_term_names),
        sparse.csr_matrix((total_dofs, total_dofs)),
    ).tocsr()
    matrix.sum_duplicates()

    readout, null_mode = _cell_readout_and_null_mode(module.CELL_DOF_COUNT, total_dofs)
    geometric_source, edge_row_checks, side_matrix = _geometric_source(
        module, rows, total_dofs
    )
    physical_source, bottom_displacement = _bottom_cosine_source(
        module, thickness, nx, ny, total_dofs
    )

    augmented = sparse.bmat(
        [[matrix, sparse.csr_matrix(readout[:, None])], [sparse.csr_matrix(readout[None, :]), None]],
        format="csc",
    )
    factorization = sparse_linalg.splu(augmented, permc_spec="COLAMD")
    solutions: dict[str, tuple[np.ndarray, float]] = {}
    right_hand_side_count = 0
    for name, source in (("u0_physical", physical_source), ("z_geometric", geometric_source)):
        augmented_source = np.concatenate((source, np.zeros(1, dtype=np.float64)))
        augmented_solution = factorization.solve(augmented_source)
        right_hand_side_count += 1
        solutions[name] = (augmented_solution[:-1], float(augmented_solution[-1]))

    u0, multiplier_u0 = solutions["u0_physical"]
    z_value, multiplier_z = solutions["z_geometric"]
    alpha = edge_row_checks["alpha"]
    c_k = 4.0 * CELL_COUNT / module.CELL_HEIGHT**2

    weighted_side_extension = 0.0
    weighted_area_strain = 0.0
    cell_u0 = u0[: module.CELL_DOF_COUNT].reshape(CELL_COUNT, 4, 2)
    wave = np.cos(2.0 * math.pi * np.arange(CELL_COUNT) / CELL_COUNT)
    normalized_area_strains: list[float] = []
    for cell in range(CELL_COUNT):
        left_extension = cell_u0[cell, 3, 1] - cell_u0[cell, 0, 1]
        right_extension = cell_u0[cell, 2, 1] - cell_u0[cell, 1, 1]
        weighted_side_extension += (
            wave[cell] * left_extension + wave[(cell + 1) % CELL_COUNT] * right_extension
        )
        area_strain = float(
            rows["area"][0] @ cell_u0[cell].reshape(-1) / module.CELL_AREA
        )
        normalized_area_strains.append(area_strain)
        weighted_area_strain += (wave[cell] + wave[(cell + 1) % CELL_COUNT]) * area_strain

    f_h_cross = float(-(geometric_source @ u0) / U0)
    f_h_edge = float(
        -(module.K_EDGE / module.CELL_HEIGHT**2) * weighted_side_extension / U0
    )
    f_h_area = float(
        module.K_AREA * weighted_area_strain / (2.0 * module.CELL_HEIGHT * U0)
    )
    f_h_values = np.array((f_h_cross, f_h_edge, f_h_area), dtype=np.float64)
    f_h_identity_scale = max(float(np.max(np.abs(f_h_values))), alpha * np.finfo(np.float64).eps)
    f_h_identity_error = float(np.max(np.abs(f_h_values - f_h_cross)) / f_h_identity_scale)

    g_dot_z = float(geometric_source @ z_value)
    c_g_schur = float(alpha - g_dot_z)
    residual_components: dict[str, float] = {}
    residual_components["cell_area"] = float(z_value @ (terms["cell_area"] @ z_value))
    residual_components["cell_edge_non_side"] = float(
        z_value @ ((terms["cell_edge"] - side_matrix) @ z_value)
    )
    residual_side = 0.0
    cell_z = z_value[: module.CELL_DOF_COUNT].reshape(CELL_COUNT, 4, 2)
    for cell in range(CELL_COUNT):
        left_extension = cell_z[cell, 3, 1] - cell_z[cell, 0, 1]
        right_extension = cell_z[cell, 2, 1] - cell_z[cell, 1, 1]
        residual_side += (wave[cell] - left_extension) ** 2
        residual_side += (wave[(cell + 1) % CELL_COUNT] - right_extension) ** 2
    residual_components["cell_edge_side_with_geometric_offset"] = float(
        (module.K_EDGE / module.CELL_HEIGHT**2) * residual_side
    )
    for name in (
        "ecm_plane_strain",
        "cell_ecm_distributed_attachment",
        "cell_connections",
    ):
        residual_components[name] = float(z_value @ (terms[name] @ z_value))
    c_g_residual = float(sum(residual_components.values()))
    c_g_identity_error_absolute = abs(c_g_schur - c_g_residual)

    matrix_norm = max(float(np.linalg.norm(matrix.data)), np.finfo(np.float64).tiny)
    null_residual = matrix @ null_mode
    checks: dict[str, Any] = {
        "matrix_symmetry_relative": float(
            sparse_linalg.norm(matrix - matrix.T) / max(sparse_linalg.norm(matrix), np.finfo(np.float64).tiny)
        ),
        "A0_e_relative_residual": float(np.linalg.norm(null_residual) / (matrix_norm * np.linalg.norm(null_mode))),
        "q_dot_e": float(readout @ null_mode),
        "physical_source_e_orthogonality_relative": _normalized_ratio(
            float(null_mode @ physical_source), np.linalg.norm(null_mode) * np.linalg.norm(physical_source)
        ),
        "geometric_source_e_orthogonality_relative": _normalized_ratio(
            float(null_mode @ geometric_source), np.linalg.norm(null_mode) * np.linalg.norm(geometric_source)
        ),
        "edge_row_factor_checks": edge_row_checks,
        "right_hand_sides": {},
        "F_h_identity_relative_error": f_h_identity_error,
        "C_g_identity_absolute_error": c_g_identity_error_absolute,
        "C_g_identity_relative_error": _normalized_ratio(
            c_g_schur - c_g_residual, c_g_schur, c_g_residual
        ),
        "minimum_nonnegative_residual_component": float(min(residual_components.values())),
    }

    algebraic_residual_scale = c_g_identity_error_absolute
    for name, source, solution, multiplier in (
        ("u0_physical", physical_source, u0, multiplier_u0),
        ("z_geometric", geometric_source, z_value, multiplier_z),
    ):
        balance = matrix @ solution + readout * multiplier - source
        source_norm = max(float(np.linalg.norm(source)), np.finfo(np.float64).tiny)
        balance_relative = float(np.linalg.norm(balance) / source_norm)
        gauge_relative = _normalized_ratio(
            float(readout @ solution), np.linalg.norm(readout) * np.linalg.norm(solution)
        )
        multiplier_relative = float(abs(multiplier) * np.linalg.norm(readout) / source_norm)
        matrix_work = float(solution @ (matrix @ solution))
        source_work = float(solution @ source)
        energy_relative = _normalized_ratio(matrix_work - source_work, matrix_work, source_work)
        residual_work_scale = float(abs(solution @ balance))
        algebraic_residual_scale = max(
            algebraic_residual_scale,
            residual_work_scale,
            np.finfo(np.float64).eps * max(abs(matrix_work), abs(source_work), alpha),
        )
        checks["right_hand_sides"][name] = {
            "source_l2": float(np.linalg.norm(source)),
            "solution_l2": float(np.linalg.norm(solution)),
            "normalized_balance_residual": balance_relative,
            "normalized_Q_gauge_residual": gauge_relative,
            "Q_value": float(readout @ solution),
            "lagrange_multiplier": float(multiplier),
            "normalized_multiplier": multiplier_relative,
            "twice_elastic_energy": matrix_work,
            "source_work": source_work,
            "energy_closure_relative": energy_relative,
            "residual_work_absolute": residual_work_scale,
        }

    identity_checks_pass = bool(
        checks["matrix_symmetry_relative"] <= BALANCE_TOLERANCE
        and checks["A0_e_relative_residual"] <= BALANCE_TOLERANCE
        and abs(checks["q_dot_e"] - 1.0) <= BALANCE_TOLERANCE
        and checks["physical_source_e_orthogonality_relative"] <= BALANCE_TOLERANCE
        and checks["geometric_source_e_orthogonality_relative"] <= BALANCE_TOLERANCE
        and checks["edge_row_factor_checks"]["original_edge_rows_vs_direct_max_abs"] == 0.0
        and checks["F_h_identity_relative_error"] <= IDENTITY_TOLERANCE
        and checks["C_g_identity_relative_error"] <= IDENTITY_TOLERANCE
        and checks["minimum_nonnegative_residual_component"] >= -algebraic_residual_scale
        and all(
            item["normalized_balance_residual"] <= BALANCE_TOLERANCE
            and item["normalized_Q_gauge_residual"] <= BALANCE_TOLERANCE
            and item["normalized_multiplier"] <= BALANCE_TOLERANCE
            and item["energy_closure_relative"] <= BALANCE_TOLERANCE
            for item in checks["right_hand_sides"].values()
        )
    )
    c_g_positive_above_residual = bool(c_g_schur > 0.0 and c_g_schur > algebraic_residual_scale)

    record = {
        "resolution": resolution,
        "parameters": {
            "cell_count": CELL_COUNT,
            "a": float(module.CELL_WIDTH),
            "b": float(module.CELL_HEIGHT),
            "L": float(module.BOX_LENGTH),
            "h_over_a": 1.0,
            "delta": 0.0,
            "kappa": 0.0,
            "K_area": float(module.K_AREA),
            "K_edge": float(module.K_EDGE),
            "K_cc": float(module.K_CC),
            "K_ce": float(module.K_CE),
            "E_eq": float(module.ECM_YOUNG),
            "nu": float(module.ECM_POISSON),
            "nx": nx,
            "ny": ny,
            "U0": U0,
        },
        "mesh": mesh_metadata,
        "free_coordinates": free_coordinates.tolist(),
        "A0": {
            "shape": list(matrix.shape),
            "nnz": int(matrix.nnz),
            "sha256_csr": _matrix_sha256(matrix),
            "included_blocks": list(active_term_names),
            "excluded_block": "cell_angle",
        },
        "gauge": {
            "Q_readout": readout.tolist(),
            "null_mode_e": null_mode.tolist(),
        },
        "inputs": {
            "bottom_cosine_normal_displacement_shape_nx_2": bottom_displacement.tolist(),
            "physical_source_f": physical_source.tolist(),
            "geometric_source_g": geometric_source.tolist(),
            "wave_s_n": wave.tolist(),
        },
        "solutions": {
            "u0_physical": _solution_record(u0, multiplier_u0, nx, ny, module.CELL_DOF_COUNT),
            "z_geometric": _solution_record(z_value, multiplier_z, nx, ny, module.CELL_DOF_COUNT),
        },
        "coefficients": {
            "alpha": alpha,
            "C_k": float(c_k),
            "F_h_cross_product": f_h_cross,
            "F_h_weighted_side_extension": f_h_edge,
            "F_h_weighted_area_strain": f_h_area,
            "F_h_over_alpha_abs": float(abs(f_h_cross) / alpha),
            "F_h_exploratory_near_zero": bool(abs(f_h_cross) / alpha < NEAR_ZERO_RATIO),
            "C_g_schur": c_g_schur,
            "C_g_nonnegative_residual_reconstruction": c_g_residual,
            "C_g_residual_components": residual_components,
            "C_g_algebraic_residual_scale": algebraic_residual_scale,
            "C_g_positive_above_algebraic_residual": c_g_positive_above_residual,
            "C_g_less_than_alpha": bool(c_g_schur < alpha),
        },
        "checks": checks,
        "identity_checks_pass": identity_checks_pass,
    }
    return record, right_hand_side_count


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON value rejected")
        return value
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def main() -> None:
    if OUTPUT_DIRECTORY.exists() or OUTPUT_PATH.exists():
        raise RuntimeError(f"create-only output already exists: {OUTPUT_DIRECTORY}")
    source_hashes = {
        "scripts/run_paper2_pair_junction_probe_v01.py": _sha256(PAIR_RUNNER),
        "scripts/run_paper2_closed_cell_ritz_probe_v01.py": _sha256(CLOSED_CELL_SOURCE),
        "project_control/prl_independent_theory_mainline_plan_v04.md": _sha256(PLAN_SOURCE),
        "scripts/run_paper2_shape_coupling_coefficients_v01.py": _sha256(Path(__file__)),
    }
    if source_hashes["scripts/run_paper2_pair_junction_probe_v01.py"] != EXPECTED_PAIR_RUNNER_SHA256:
        raise RuntimeError("pair-junction assembly source hash mismatch")
    if source_hashes["scripts/run_paper2_closed_cell_ritz_probe_v01.py"] != EXPECTED_CLOSED_CELL_SHA256:
        raise RuntimeError("closed-cell edge-row source hash mismatch")

    module = _load_pair_runner()
    rows = _rows_from_original_edges(module)
    calculation_start = datetime.now(timezone.utc)
    calculation_timer = time.perf_counter()
    cases: list[dict[str, Any]] = []
    total_right_hand_sides = 0
    for resolution, nx, ny in (("coarse", 32, 8), ("fine", 64, 16)):
        case, count = _mesh_case(module, rows, resolution, nx, ny)
        cases.append(case)
        total_right_hand_sides += count
    calculation_seconds = time.perf_counter() - calculation_timer
    calculation_finish = datetime.now(timezone.utc)

    if total_right_hand_sides != 4:
        raise RuntimeError(f"right-hand side count {total_right_hand_sides} is not exactly four")

    coarse = next(case for case in cases if case["resolution"] == "coarse")
    fine = next(case for case in cases if case["resolution"] == "fine")
    coarse_f_h = coarse["coefficients"]["F_h_cross_product"]
    fine_f_h = fine["coefficients"]["F_h_cross_product"]
    coarse_c_g = coarse["coefficients"]["C_g_schur"]
    fine_c_g = fine["coefficients"]["C_g_schur"]
    both_f_h_nonzero = not coarse["coefficients"]["F_h_exploratory_near_zero"] and not fine[
        "coefficients"
    ]["F_h_exploratory_near_zero"]
    f_h_resolution_change = None
    if both_f_h_nonzero:
        f_h_resolution_change = float(abs(coarse_f_h - fine_f_h) / abs(fine_f_h))
    c_g_resolution_change = float(abs(coarse_c_g - fine_c_g) / abs(fine_c_g))
    all_identity_checks_pass = all(case["identity_checks_pass"] for case in cases)
    all_c_g_checks_pass = all(
        case["coefficients"]["C_g_positive_above_algebraic_residual"]
        and case["coefficients"]["C_g_less_than_alpha"]
        for case in cases
    )

    if not all_identity_checks_pass or not all_c_g_checks_pass or calculation_seconds > CALCULATION_BUDGET_SECONDS:
        status = "COMPLETED_WITH_FAIL_CLOSED_CHECK_FAILURE"
    elif both_f_h_nonzero and f_h_resolution_change is not None:
        status = (
            "NONZERO_COEFFICIENT_EXPLORATORY_RESOLUTION_PASS"
            if f_h_resolution_change <= EXPLORATORY_RESOLUTION_TOLERANCE
            and c_g_resolution_change <= EXPLORATORY_RESOLUTION_TOLERANCE
            else "NONZERO_COEFFICIENT_EXPLORATORY_RESOLUTION_FAIL"
        )
    elif all(case["coefficients"]["F_h_exploratory_near_zero"] for case in cases):
        status = "F_H_EXPLORATORY_NEAR_ZERO"
    else:
        status = "F_H_NEAR_ZERO_CLASSIFICATION_NOT_RESOLUTION_STABLE"

    peak_bytes, peak_method = _peak_working_set_bytes()
    payload = {
        "schema": "paper2_shape_coupling_coefficients_v01",
        "status": status,
        "scientific_question": "For the fixed delta=kappa=0 reference state and prescribed bottom cosine-normal displacement, is the missing first-order shape-driving coefficient F_h zero, unresolvable, or nonzero?",
        "claim_boundary": {
            "coefficient_feasibility_only": True,
            "finite_delta_asymptotics_tested": False,
            "shape_or_kappa_scan_performed": False,
            "active_myocardium_present": False,
            "DCM_necessity_established": False,
            "Nature_Physics_mechanism_established": False,
        },
        "version": {
            "git_HEAD": _git_head(),
            "source_sha256": source_hashes,
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "execution": {
            "calculation_start_utc": calculation_start.isoformat(),
            "calculation_finish_utc": calculation_finish.isoformat(),
            "calculation_seconds": calculation_seconds,
            "calculation_budget_seconds": CALCULATION_BUDGET_SECONDS,
            "linear_right_hand_sides": total_right_hand_sides,
            "linear_factorizations": 2,
            "eigensolver_calls": 0,
            "old_state_reruns": 0,
            "cpu_thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
            "peak_working_set_bytes": peak_bytes,
            "peak_working_set_gib": None if peak_bytes is None else peak_bytes / 1024**3,
            "peak_memory_measurement": peak_method,
            "memory_budget_gib": 8.0,
            "memory_budget_enforced": False,
        },
        "thresholds": {
            "normalized_balance_and_identity": BALANCE_TOLERANCE,
            "F_h_over_alpha_exploratory_near_zero": NEAR_ZERO_RATIO,
            "coarse_fine_relative_to_fine_exploratory": EXPLORATORY_RESOLUTION_TOLERANCE,
        },
        "cases": cases,
        "coarse_fine": {
            "F_h_absolute_difference": float(abs(coarse_f_h - fine_f_h)),
            "F_h_relative_difference_over_fine": f_h_resolution_change,
            "C_g_absolute_difference": float(abs(coarse_c_g - fine_c_g)),
            "C_g_relative_difference_over_fine": c_g_resolution_change,
            "F_h_resolution_gate_pass": None
            if f_h_resolution_change is None
            else bool(f_h_resolution_change <= EXPLORATORY_RESOLUTION_TOLERANCE),
            "C_g_resolution_gate_pass": bool(
                c_g_resolution_change <= EXPLORATORY_RESOLUTION_TOLERANCE
            ),
        },
        "all_identity_checks_pass": all_identity_checks_pass,
        "all_C_g_positive_above_residual_and_below_alpha": all_c_g_checks_pass,
    }

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=False)
    with OUTPUT_PATH.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(_json_ready(payload), handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(OUTPUT_PATH), "status": status, "summary": payload["coarse_fine"], "calculation_seconds": calculation_seconds}))


if __name__ == "__main__":
    main()
