#!/usr/bin/env python3
"""Bounded eight-cell / finite-thickness ECM two-junction static probe."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = Path("results/paper2_pair_junction_probe/v01_20260907/summary.json")
FROZEN_HEAD = "ac2fcb6065938a4d6ed7c24d82946059f06ff9ba"
SOURCE_HASHES = {
    "project_control/prl_independent_theory_mainline_plan_v04.md": "e42835c153bc072e871430c3c093373161f59531e067fc98d1d242c3a17c7459",
    "results/paper2_science_pilot/v01_20260905/science_brief.md": "c76f8c0734764bdcaaa76378a5fb32f24b0ed169d41695e603a92cd7f0f8bd03",
    "scripts/run_paper2_closed_cell_ritz_probe_v01.py": "9a0b9e738624e92559421064f99aae8979ae065dd67d112ad0bb681f85dd9eec",
    "src/paper2_hybrid/model.py": "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800",
}

CELL_COUNT = 8
CELL_WIDTH = 0.5
CELL_HEIGHT = 0.1
BOX_LENGTH = CELL_COUNT * CELL_WIDTH
CELL_AREA = CELL_WIDTH * CELL_HEIGHT
K_AREA = 10.0
K_EDGE = 1.0
K_ANGLE = 0.1
K_CC = 1.0
K_CE = 1.0
ECM_YOUNG = 1.0
ECM_POISSON = 0.3
WEAKENING_ALPHA = 0.5
PORT_SPRING = K_CC / CELL_HEIGHT**2
PORT_REMOVAL = WEAKENING_ALPHA * PORT_SPRING
FORCE_AMPLITUDE = 1.0e-5
CELL_DOF_COUNT = CELL_COUNT * 8
OPENING_FLOOR = 1.0e-12 * CELL_HEIGHT
FORCE_FLOOR = PORT_SPRING * OPENING_FLOOR
DIRECT_STATE_LIMIT = 30
FLEXIBILITY_RHS_LIMIT = 14
TOTAL_RHS_LIMIT = 44
CALCULATION_BUDGET_SECONDS = 300.0
PREPARATION_BUDGET_SECONDS = 45.0 * 60.0
WRITER_AUDIT: dict[str, Any] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    git_path = REPO_ROOT / ".git"
    if git_path.is_file():
        marker = git_path.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir: "):
            raise RuntimeError("unrecognized .git file")
        git_path = (REPO_ROOT / marker[8:]).resolve()
    head = (git_path / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    reference = head[5:]
    loose = git_path / reference
    if loose.exists():
        return loose.read_text(encoding="utf-8").strip()
    for line in (git_path / "packed-refs").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "^")):
            commit, name = line.split(" ", 1)
            if name == reference:
                return commit
    raise RuntimeError("HEAD reference not resolved")


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
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON keys must be strings")
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported JSON type: {type(value).__name__}")


def _verify_sources() -> dict[str, Any]:
    actual = {relative: _sha256(REPO_ROOT / relative) for relative in SOURCE_HASHES}
    if actual != SOURCE_HASHES:
        raise RuntimeError(f"source hash mismatch: expected={SOURCE_HASHES}, actual={actual}")
    head = _git_head()
    if head != FROZEN_HEAD:
        raise RuntimeError(f"HEAD mismatch: expected={FROZEN_HEAD}, actual={head}")
    return {"frozen_HEAD": head, "sha256": actual, "all_match": True}


def _load_cell_rows() -> dict[str, list[np.ndarray]]:
    sys.dont_write_bytecode = True
    source = REPO_ROOT / "scripts/run_paper2_closed_cell_ritz_probe_v01.py"
    specification = importlib.util.spec_from_file_location("frozen_closed_cell_v01", source)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load frozen cell Jacobian source")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    rows16 = module._cell_jacobians(0)
    return {
        family: [np.asarray(row[:8], dtype=np.float64) for row in family_rows]
        for family, family_rows in rows16.items()
    }


def _constitutive_matrix() -> np.ndarray:
    shear = ECM_YOUNG / (2.0 * (1.0 + ECM_POISSON))
    lame = ECM_YOUNG * ECM_POISSON / (
        (1.0 + ECM_POISSON) * (1.0 - 2.0 * ECM_POISSON)
    )
    return np.array(
        [[lame + 2.0 * shear, lame, 0.0], [lame, lame + 2.0 * shear, 0.0], [0.0, 0.0, shear]],
        dtype=np.float64,
    )


def _triangle_operator(coordinates: np.ndarray) -> tuple[np.ndarray, float]:
    interpolation = np.column_stack((np.ones(3), coordinates))
    gradients = np.linalg.inv(interpolation)[1:, :].T
    twice_area = np.linalg.det(
        np.array((coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]))
    )
    area = 0.5 * abs(float(twice_area))
    if area <= 0.0:
        raise RuntimeError("non-positive ECM triangle area")
    strain = np.zeros((3, 6), dtype=np.float64)
    for local, (gradient_x, gradient_y) in enumerate(gradients):
        strain[0, 2 * local] = gradient_x
        strain[1, 2 * local + 1] = gradient_y
        strain[2, 2 * local] = gradient_y
        strain[2, 2 * local + 1] = gradient_x
    return strain, area


def _single_cell_terms(rows: dict[str, list[np.ndarray]]) -> dict[str, np.ndarray]:
    result = {name: np.zeros((8, 8), dtype=np.float64) for name in ("cell_area", "cell_edge", "cell_angle")}
    result["cell_area"] += (K_AREA / CELL_AREA**2) * np.outer(rows["area"][0], rows["area"][0])
    references = (CELL_WIDTH, CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
    for row, reference in zip(rows["edge"], references):
        result["cell_edge"] += (K_EDGE / reference**2) * np.outer(row, row)
    for row in rows["angle"]:
        result["cell_angle"] += K_ANGLE * np.outer(row, row)
    return result


def _block_cell_terms(rows: dict[str, list[np.ndarray]], ecm_dofs: int) -> dict[str, sparse.csr_matrix]:
    single = _single_cell_terms(rows)
    terms = {}
    for name, matrix in single.items():
        cell_block = sparse.block_diag([matrix] * CELL_COUNT, format="csr")
        terms[name] = sparse.block_diag((cell_block, sparse.csr_matrix((ecm_dofs, ecm_dofs))), format="csr")
    return terms


def _ecm_free_index(ix: int, iy: int, component: int, nx: int) -> int | None:
    if iy == 0:
        return None
    periodic_ix = ix % nx
    return 2 * ((iy - 1) * nx + periodic_ix) + component


def _ecm_stiffness(thickness: float, nx: int, ny: int) -> tuple[sparse.csr_matrix, np.ndarray, dict[str, Any]]:
    dx = BOX_LENGTH / nx
    dy = thickness / ny
    constitutive = _constitutive_matrix()
    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    area_sum = 0.0
    minimum_area = math.inf
    triangle_count = 0
    for iy in range(ny):
        for ix in range(nx):
            triangles = (
                ((ix, iy), (ix + 1, iy), (ix + 1, iy + 1)),
                ((ix, iy), (ix + 1, iy + 1), (ix, iy + 1)),
            )
            for triangle in triangles:
                coordinates = np.array(
                    [(-0.5 * BOX_LENGTH + node_x * dx, node_y * dy) for node_x, node_y in triangle],
                    dtype=np.float64,
                )
                strain, area = _triangle_operator(coordinates)
                local_matrix = area * strain.T @ constitutive @ strain
                mappings: list[int | None] = []
                for node_x, node_y in triangle:
                    mappings.extend(
                        (
                            _ecm_free_index(node_x, node_y, 0, nx),
                            _ecm_free_index(node_x, node_y, 1, nx),
                        )
                    )
                for local_row, global_row in enumerate(mappings):
                    if global_row is None:
                        continue
                    for local_column, global_column in enumerate(mappings):
                        if global_column is None:
                            continue
                        row_indices.append(global_row)
                        column_indices.append(global_column)
                        values.append(float(local_matrix[local_row, local_column]))
                area_sum += area
                minimum_area = min(minimum_area, area)
                triangle_count += 1
    ecm_dofs = 2 * nx * ny
    matrix = sparse.coo_matrix((values, (row_indices, column_indices)), shape=(ecm_dofs, ecm_dofs)).tocsr()
    matrix.sum_duplicates()
    free_coordinates = np.array(
        [
            (-0.5 * BOX_LENGTH + ix * dx, iy * dy)
            for iy in range(1, ny + 1)
            for ix in range(nx)
        ],
        dtype=np.float64,
    )
    metadata = {
        "nx": nx,
        "ny": ny,
        "dx": dx,
        "dy": dy,
        "triangle_count": triangle_count,
        "free_node_count": nx * ny,
        "free_dof_count": ecm_dofs,
        "assembled_area": area_sum,
        "expected_area": BOX_LENGTH * thickness,
        "minimum_triangle_area": minimum_area,
        "all_triangle_areas_positive": minimum_area > 0.0,
        "bottom_both_components_fixed": True,
        "side_nodes_periodically_identified": True,
        "free_DOF_mapping": "2*((iy-1)*nx+(ix mod nx))+component for iy>0; bottom iy=0 eliminated",
        "periodic_right_to_left_mapping_verified": all(
            _ecm_free_index(nx, row, component, nx)
            == _ecm_free_index(0, row, component, nx)
            for row in range(1, ny + 1)
            for component in range(2)
        ),
        "diagonal": "lower_left_to_upper_right",
    }
    return matrix, free_coordinates, metadata


def _distributed_attachment(nx: int, ny: int, total_dofs: int) -> sparse.csr_matrix:
    if nx % CELL_COUNT != 0:
        raise RuntimeError("ECM top mesh does not align with eight fixed cells")
    dx = BOX_LENGTH / nx
    elements_per_cell = nx // CELL_COUNT
    gauss_nodes = (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
    density = K_CE / (CELL_WIDTH * CELL_HEIGHT**2)
    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    for cell in range(CELL_COUNT):
        cell_left = -0.5 * BOX_LENGTH + cell * CELL_WIDTH
        cell_right = cell_left + CELL_WIDTH
        for local_element in range(elements_per_cell):
            ix = cell * elements_per_cell + local_element
            left = -0.5 * BOX_LENGTH + ix * dx
            right = left + dx
            midpoint = 0.5 * (left + right)
            half = 0.5 * (right - left)
            local_matrix = np.zeros((4, 4), dtype=np.float64)
            for point in gauss_nodes:
                x_value = midpoint + half * point
                cell_shape = np.array(
                    [(cell_right - x_value) / CELL_WIDTH, (x_value - cell_left) / CELL_WIDTH]
                )
                ecm_shape = np.array([(right - x_value) / dx, (x_value - left) / dx])
                difference_shape = np.concatenate((cell_shape, -ecm_shape))
                local_matrix += half * np.outer(difference_shape, difference_shape)
            local_matrix *= density
            for component in range(2):
                indices = (
                    8 * cell + component,
                    8 * cell + 2 + component,
                    CELL_DOF_COUNT + int(_ecm_free_index(ix, ny, component, nx)),
                    CELL_DOF_COUNT + int(_ecm_free_index(ix + 1, ny, component, nx)),
                )
                for local_row, global_row in enumerate(indices):
                    for local_column, global_column in enumerate(indices):
                        row_indices.append(global_row)
                        column_indices.append(global_column)
                        values.append(float(local_matrix[local_row, local_column]))
    matrix = sparse.coo_matrix((values, (row_indices, column_indices)), shape=(total_dofs, total_dofs)).tocsr()
    matrix.sum_duplicates()
    return matrix


def _cell_connections(total_dofs: int, weak_top_x: tuple[int, ...]) -> sparse.csr_matrix:
    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    weak = set(weak_top_x)
    for cell in range(CELL_COUNT):
        following = (cell + 1) % CELL_COUNT
        for current_vertex, following_vertex in ((1, 0), (2, 3)):
            for component in range(2):
                stiffness = PORT_SPRING
                if current_vertex == 2 and component == 0 and cell in weak:
                    stiffness *= 1.0 - WEAKENING_ALPHA
                first = 8 * cell + 2 * current_vertex + component
                second = 8 * following + 2 * following_vertex + component
                for row, column, value in (
                    (first, first, stiffness),
                    (first, second, -stiffness),
                    (second, first, -stiffness),
                    (second, second, stiffness),
                ):
                    row_indices.append(row)
                    column_indices.append(column)
                    values.append(value)
    matrix = sparse.coo_matrix((values, (row_indices, column_indices)), shape=(total_dofs, total_dofs)).tocsr()
    matrix.sum_duplicates()
    return matrix


def _port_vector(connection: int, total_dofs: int) -> np.ndarray:
    following = (connection + 1) % CELL_COUNT
    vector = np.zeros(total_dofs, dtype=np.float64)
    vector[8 * connection + 2 * 2] = -1.0
    vector[8 * following + 2 * 3] = 1.0
    return vector


def _sparse_hash(matrix: sparse.csr_matrix) -> str:
    value = matrix.copy().tocsr()
    value.sum_duplicates()
    value.sort_indices()
    digest = hashlib.sha256()
    digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
    digest.update(value.indptr.astype(np.int64, copy=False).tobytes())
    digest.update(value.indices.astype(np.int64, copy=False).tobytes())
    digest.update(value.data.astype(np.float64, copy=False).tobytes())
    return digest.hexdigest()


def _source_record(source: np.ndarray) -> dict[str, Any]:
    nonzero = np.flatnonzero(source)
    return {
        "size": len(source),
        "nonzero_indices": nonzero.tolist(),
        "nonzero_values": source[nonzero].tolist(),
        "l2_norm": float(np.linalg.norm(source)),
    }


def _state_vector_record(solution: np.ndarray, nx: int, ny: int) -> dict[str, Any]:
    return {
        "cell_displacements_shape_8x4x2": solution[:CELL_DOF_COUNT].reshape(CELL_COUNT, 4, 2).tolist(),
        "ecm_free_displacements_shape_ny_nx_2": solution[CELL_DOF_COUNT:].reshape(ny, nx, 2).tolist(),
        "ecm_bottom_displacements": "identically zero by elimination",
    }


def _matrix_context(
    mesh_context: dict[str, Any],
    weak_connections: tuple[int, ...],
) -> dict[str, Any]:
    key = tuple(sorted(weak_connections))
    cached = mesh_context["matrix_cache"].get(key)
    if cached is not None:
        return cached
    connection = _cell_connections(mesh_context["total_dofs"], key)
    terms = dict(mesh_context["fixed_terms"])
    terms["cell_connections"] = connection
    matrix = sum(terms.values(), sparse.csr_matrix((mesh_context["total_dofs"], mesh_context["total_dofs"]))).tocsr()
    matrix.sum_duplicates()
    symmetry_denominator = max(float(sparse_linalg.norm(matrix)), 1.0e-30)
    symmetry_error = float(sparse_linalg.norm(matrix - matrix.T) / symmetry_denominator)
    factorization = sparse_linalg.splu(matrix.tocsc(), permc_spec="COLAMD")
    minimum_eigenvalue = float(
        sparse_linalg.eigsh(matrix, k=1, sigma=0.0, which="LM", return_eigenvectors=False, tol=1.0e-9)[0]
    )
    cached = {
        "K": matrix,
        "terms": terms,
        "factorization": factorization,
        "symmetry_relative_error": symmetry_error,
        "minimum_eigenvalue": minimum_eigenvalue,
        "positive_definite": minimum_eigenvalue > 0.0,
        "sha256_csr": _sparse_hash(matrix),
        "shape": list(matrix.shape),
        "nnz": int(matrix.nnz),
        "weak_top_x_connections": list(key),
    }
    mesh_context["matrix_cache"][key] = cached
    return cached


def _make_mesh_context(
    thickness_ratio: float,
    nx: int,
    ny: int,
    rows: dict[str, list[np.ndarray]],
) -> dict[str, Any]:
    thickness = thickness_ratio * CELL_WIDTH
    ecm_matrix, free_coordinates, mesh_metadata = _ecm_stiffness(thickness, nx, ny)
    ecm_dofs = ecm_matrix.shape[0]
    total_dofs = CELL_DOF_COUNT + ecm_dofs
    fixed_terms = _block_cell_terms(rows, ecm_dofs)
    fixed_terms["ecm_plane_strain"] = sparse.block_diag(
        (sparse.csr_matrix((CELL_DOF_COUNT, CELL_DOF_COUNT)), ecm_matrix), format="csr"
    )
    fixed_terms["cell_ecm_distributed_attachment"] = _distributed_attachment(nx, ny, total_dofs)
    return {
        "thickness_ratio": thickness_ratio,
        "thickness": thickness,
        "nx": nx,
        "ny": ny,
        "ecm_dofs": ecm_dofs,
        "total_dofs": total_dofs,
        "free_coordinates": free_coordinates,
        "mesh_metadata": mesh_metadata,
        "fixed_terms": fixed_terms,
        "matrix_cache": {},
    }


def _assembly_analytic_checks(
    mesh_contexts: dict[tuple[float, int, int], dict[str, Any]],
) -> dict[str, Any]:
    constitutive = _constitutive_matrix()
    coordinates = np.array([[0.0, 0.0], [0.7, 0.0], [0.7, 0.3]], dtype=np.float64)
    strain, area = _triangle_operator(coordinates)
    gradient = np.array([[0.2, 0.12], [0.18, -0.1]], dtype=np.float64)
    translation = np.array([0.31, -0.27], dtype=np.float64)
    affine = np.concatenate([translation + gradient @ point for point in coordinates])
    measured_strain = strain @ affine
    expected_strain = np.array([0.2, -0.1, 0.3], dtype=np.float64)
    local_matrix = area * strain.T @ constitutive @ strain
    measured_energy = float(0.5 * affine @ local_matrix @ affine)
    expected_energy = float(0.5 * area * expected_strain @ constitutive @ expected_strain)
    rigid_translation = np.tile(np.array([0.43, -0.21]), 3)
    rotation_rate = 0.37
    rigid_rotation = np.concatenate(
        [np.array([-rotation_rate * point[1], rotation_rate * point[0]]) for point in coordinates]
    )
    attachment_checks = {}
    for mesh_key, context in mesh_contexts.items():
        coupling = context["fixed_terms"]["cell_ecm_distributed_attachment"]
        per_component = {}
        for component in range(2):
            common = np.zeros(context["total_dofs"], dtype=np.float64)
            common[np.arange(component, CELL_DOF_COUNT, 2)] = 1.0
            common[CELL_DOF_COUNT + np.arange(component, context["ecm_dofs"], 2)] = 1.0
            per_component["xy"[component]] = {
                "common_translation_action_l2": float(np.linalg.norm(coupling @ common)),
                "row_sum_maximum_absolute": float(np.max(np.abs(coupling @ common))),
            }
        deterministic = np.linspace(-0.9, 1.1, context["total_dofs"])
        reactions = coupling @ deterministic
        force_balance = []
        for component in range(2):
            cell_sum = float(np.sum(reactions[np.arange(component, CELL_DOF_COUNT, 2)]))
            ecm_sum = float(
                np.sum(reactions[CELL_DOF_COUNT + np.arange(component, context["ecm_dofs"], 2)])
            )
            force_balance.append(
                {
                    "component": "xy"[component],
                    "cell_resultant": cell_sum,
                    "ECM_resultant": ecm_sum,
                    "sum": cell_sum + ecm_sum,
                }
            )
        attachment_checks[str(mesh_key)] = {
            "common_translation": per_component,
            "deterministic_action_reaction": force_balance,
            "matrix_symmetry_relative_error": float(
                sparse_linalg.norm(coupling - coupling.T)
                / max(float(sparse_linalg.norm(coupling)), 1.0e-30)
            ),
            "last_cell_right_ECM_node_maps_to_periodic_left": bool(
                _ecm_free_index(context["nx"], context["ny"], 0, context["nx"])
                == _ecm_free_index(0, context["ny"], 0, context["nx"])
            ),
        }
    maximum_attachment_error = max(
        [
            value["matrix_symmetry_relative_error"]
            for value in attachment_checks.values()
        ]
        + [
            item["row_sum_maximum_absolute"]
            for value in attachment_checks.values()
            for item in value["common_translation"].values()
        ]
        + [
            abs(item["sum"])
            for value in attachment_checks.values()
            for item in value["deterministic_action_reaction"]
        ]
    )
    affine_strain_error = float(np.max(np.abs(measured_strain - expected_strain)))
    affine_energy_relative_error = abs(measured_energy - expected_energy) / max(
        abs(expected_energy), 1.0e-30
    )
    rigid_error = max(
        float(np.max(np.abs(strain @ rigid_translation))),
        float(np.max(np.abs(strain @ rigid_rotation))),
        abs(float(0.5 * rigid_translation @ local_matrix @ rigid_translation)),
        abs(float(0.5 * rigid_rotation @ local_matrix @ rigid_rotation)),
    )
    all_mesh_geometry_checks = all(
        context["mesh_metadata"]["all_triangle_areas_positive"]
        and context["mesh_metadata"]["periodic_right_to_left_mapping_verified"]
        and math.isclose(
            context["mesh_metadata"]["assembled_area"],
            context["mesh_metadata"]["expected_area"],
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        )
        for context in mesh_contexts.values()
    )
    return {
        "engineering_shear_definition": "gamma_xy=du_x/dy+du_y/dx",
        "constitutive_C33_equals_mu": bool(
            math.isclose(
                constitutive[2, 2],
                ECM_YOUNG / (2.0 * (1.0 + ECM_POISSON)),
                rel_tol=0.0,
                abs_tol=1.0e-15,
            )
        ),
        "single_triangle_affine": {
            "measured_engineering_strain": measured_strain.tolist(),
            "expected_engineering_strain": expected_strain.tolist(),
            "maximum_absolute_strain_error": affine_strain_error,
            "measured_energy": measured_energy,
            "expected_energy": expected_energy,
            "relative_energy_error": affine_energy_relative_error,
        },
        "single_triangle_rigid_fields": {
            "maximum_strain_or_energy_absolute_error": rigid_error,
        },
        "distributed_attachment": attachment_checks,
        "maximum_attachment_symmetry_translation_or_action_reaction_error": maximum_attachment_error,
        "mesh_positive_area_periodic_mapping_and_total_area": all_mesh_geometry_checks,
        "UFL_PETSc_crosscheck_current_run": "not_run_dependency_unavailable",
        "old_program_numerical_PASS_inherited": False,
        "pass": bool(
            affine_strain_error <= 1.0e-12
            and affine_energy_relative_error <= 1.0e-12
            and rigid_error <= 1.0e-12
            and maximum_attachment_error <= 1.0e-10
            and all_mesh_geometry_checks
        ),
    }


def _solve(
    matrix_context: dict[str, Any],
    source: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    solution = np.asarray(matrix_context["factorization"].solve(source), dtype=np.float64)
    residual = matrix_context["K"] @ solution - source
    source_norm = float(np.linalg.norm(source))
    return solution, {
        "absolute_l2": float(np.linalg.norm(residual)),
        "relative_l2": float(np.linalg.norm(residual) / source_norm) if source_norm > 0.0 else None,
        "near_zero_source_uses_absolute_response": source_norm == 0.0,
    }


def _state_record(
    state_id: str,
    matrix_context: dict[str, Any],
    mesh_context: dict[str, Any],
    source: np.ndarray,
    solution: np.ndarray,
    residual: dict[str, Any],
    ports: np.ndarray,
    weak_flags: tuple[bool, bool],
) -> dict[str, Any]:
    openings = ports.T @ solution
    remaining = np.array(
        [PORT_SPRING * (1.0 - WEAKENING_ALPHA if flag else 1.0) for flag in weak_flags],
        dtype=np.float64,
    )
    connection_forces = remaining * openings
    energy_terms = {
        name: float(0.5 * solution @ term @ solution)
        for name, term in matrix_context["terms"].items()
    }
    total_energy = float(sum(energy_terms.values()))
    work = float(0.5 * source @ solution)
    energy_scale = max(abs(total_energy), abs(work), 1.0e-30)
    return {
        "state_id": state_id,
        "weak_flags_connection_1_2": list(weak_flags),
        "weak_top_x_connections": matrix_context["weak_top_x_connections"],
        "source": _source_record(source),
        "selected_openings_j": openings.tolist(),
        "selected_actual_connection_forces_t": connection_forces.tolist(),
        "selected_remaining_stiffness": remaining.tolist(),
        "residual": residual,
        "energy_terms": energy_terms,
        "total_elastic_energy": total_energy,
        "static_loading_work_half_f_dot_q": work,
        "energy_closure_absolute": abs(total_energy - work),
        "energy_closure_relative": abs(total_energy - work) / energy_scale,
        "static_complex_phase_or_dissipation_not_applicable": True,
        "matrix": {
            "shape": matrix_context["shape"],
            "nnz": matrix_context["nnz"],
            "sha256_csr": matrix_context["sha256_csr"],
            "symmetry_relative_error": matrix_context["symmetry_relative_error"],
            "minimum_eigenvalue": matrix_context["minimum_eigenvalue"],
            "positive_definite": matrix_context["positive_definite"],
        },
        "solution": _state_vector_record(solution, mesh_context["nx"], mesh_context["ny"]),
    }


def _relative_or_absolute_error(
    observed: np.ndarray,
    predicted: np.ndarray,
    floor: float,
) -> dict[str, Any]:
    difference = np.asarray(observed) - np.asarray(predicted)
    scale = float(np.linalg.norm(observed))
    absolute = float(np.linalg.norm(difference))
    return {
        "absolute_l2": absolute,
        "observed_l2": scale,
        "relative_l2": absolute / scale if scale > floor else None,
        "near_zero_uses_absolute": scale <= floor,
    }


def _safe_ratio(numerator: float, denominator: float, floor: float) -> float | None:
    return numerator / denominator if abs(denominator) > floor else None


def _safe_write(output: Path, payload: dict[str, Any]) -> None:
    if output.as_posix() != OUTPUT_RELATIVE.as_posix() or output.exists():
        raise RuntimeError("authorized output path occupied or changed")
    validation_start = datetime.now(timezone.utc)
    validation_timer = time.perf_counter()
    payload["runtime"]["output_stage"] = {
        "preopen_validation_started_at_utc": validation_start.isoformat(),
        "allow_nan": False,
        "open_mode": "x",
        "postsave_readback_required": True,
        "write_and_readback_times_reported_after_immutable_creation": True,
    }
    provisional = _json_ready(payload)
    provisional_text = json.dumps(provisional, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(provisional_text) != provisional:
        raise RuntimeError("preopen JSON round-trip mismatch")
    validation_finish = datetime.now(timezone.utc)
    payload["runtime"]["output_stage"].update(
        {
            "preopen_validation_finished_at_utc": validation_finish.isoformat(),
            "preopen_validation_elapsed_seconds": time.perf_counter() - validation_timer,
        }
    )
    final_payload = _json_ready(payload)
    final_text = json.dumps(final_payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(final_text) != final_payload:
        raise RuntimeError("final preopen JSON round-trip mismatch")
    serialized = datetime.now(timezone.utc)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_start = datetime.now(timezone.utc)
    write_timer = time.perf_counter()
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(final_text)
        handle.flush()
        os.fsync(handle.fileno())
    write_finish = datetime.now(timezone.utc)
    saved_text = output.read_text(encoding="utf-8")
    if saved_text != final_text or json.loads(saved_text) != final_payload:
        raise RuntimeError("postsave JSON/text readback mismatch")
    readback_finish = datetime.now(timezone.utc)
    WRITER_AUDIT.update(
        {
            "final_serialization_finished_at_utc": serialized.isoformat(),
            "write_started_at_utc": write_start.isoformat(),
            "write_finished_at_utc": write_finish.isoformat(),
            "write_only_elapsed_seconds": (write_finish - write_start).total_seconds(),
            "write_plus_readback_elapsed_seconds": time.perf_counter() - write_timer,
            "postsave_readback_verified_at_utc": readback_finish.isoformat(),
            "postsave_readback_pass": True,
            "output_bytes": output.stat().st_size,
            "output_sha256": _sha256(output),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_RELATIVE))
    parser.add_argument("--preparation-start-utc", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if output.as_posix() != OUTPUT_RELATIVE.as_posix() or output.exists():
        raise RuntimeError("authorized output path occupied or changed")
    thread_environment = {
        name: os.environ.get(name)
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    }
    if any(value != "1" for value in thread_environment.values()):
        raise RuntimeError(f"single-thread environment not enforced: {thread_environment}")
    preparation_start = datetime.fromisoformat(arguments.preparation_start_utc)
    if preparation_start.tzinfo is None:
        raise RuntimeError("preparation timestamp must include timezone")
    calculation_start = datetime.now(timezone.utc)
    preparation_seconds = (calculation_start - preparation_start.astimezone(timezone.utc)).total_seconds()
    if not (0.0 <= preparation_seconds <= PREPARATION_BUDGET_SECONDS):
        raise RuntimeError("implementation preparation budget exceeded")
    calculation_timer = time.perf_counter()

    source_verification = _verify_sources()
    rows = _load_cell_rows()
    mesh_contexts: dict[tuple[float, int, int], dict[str, Any]] = {}
    mesh_specs = [(0.2, 32, 8), (1.0, 32, 8), (5.0, 32, 8), (1.0, 64, 16)]
    for mesh_specification in mesh_specs:
        mesh_contexts[mesh_specification] = _make_mesh_context(*mesh_specification, rows)
    analytic_assembly_checks = _assembly_analytic_checks(mesh_contexts)

    direct_states: dict[str, dict[str, Any]] = {}
    raw_states: dict[str, dict[str, Any]] = {}
    groups: dict[str, dict[str, Any]] = {}
    direct_state_count = 0
    flexibility_rhs_count = 0
    failures: list[str] = []
    not_run: list[str] = []

    group_specs = [
        (thickness_ratio, separation, 32, 8, "coarse")
        for thickness_ratio in (0.2, 1.0, 5.0)
        for separation in (1, 3)
    ] + [(1.0, 1, 64, 16, "fine")]

    for thickness_ratio, separation, nx, ny, resolution in group_specs:
        group_id = f"h_over_a_{thickness_ratio:g}__d_{separation}__{resolution}"
        mesh_context = mesh_contexts[(thickness_ratio, nx, ny)]
        port1 = _port_vector(0, mesh_context["total_dofs"])
        port2 = _port_vector(separation, mesh_context["total_dofs"])
        ports = np.column_stack((port1, port2))
        common_source = FORCE_AMPLITUDE * (port1 + port2)

        base_matrix = _matrix_context(mesh_context, ())
        base_solution, base_residual = _solve(base_matrix, common_source)
        direct_state_count += 1
        base_state_id = group_id + "__00"
        base_record = _state_record(
            base_state_id, base_matrix, mesh_context, common_source, base_solution, base_residual, ports, (False, False)
        )
        direct_states[base_state_id] = base_record
        raw_states[base_state_id] = {"q": base_solution, "j": np.asarray(base_record["selected_openings_j"]), "t": np.asarray(base_record["selected_actual_connection_forces_t"]), "W": base_record["static_loading_work_half_f_dot_q"]}

        flexibility = np.asarray(base_matrix["factorization"].solve(ports), dtype=np.float64)
        flexibility_rhs_count += 2
        flexibility_residuals = []
        for column in range(2):
            residual = base_matrix["K"] @ flexibility[:, column] - ports[:, column]
            flexibility_residuals.append(
                {
                    "absolute_l2": float(np.linalg.norm(residual)),
                    "relative_l2": float(np.linalg.norm(residual) / np.linalg.norm(ports[:, column])),
                }
            )
        compliance = ports.T @ flexibility
        j0 = ports.T @ base_solution
        predictions = {}
        for state_name, weak_flags in {
            "00": (False, False),
            "10": (True, False),
            "01": (False, True),
            "11": (True, True),
        }.items():
            removal = np.diag([PORT_REMOVAL if flag else 0.0 for flag in weak_flags])
            stability = np.eye(2) - compliance @ removal
            predicted_openings = np.linalg.solve(stability, j0)
            remaining = np.array(
                [PORT_SPRING * (1.0 - WEAKENING_ALPHA if flag else 1.0) for flag in weak_flags]
            )
            predictions[state_name] = {
                "opening": predicted_openings.tolist(),
                "actual_connection_force": (remaining * predicted_openings).tolist(),
                "I_minus_GD": stability.tolist(),
                "minimum_eigenvalue_symmetric_D_form": float(
                    np.min(
                        np.linalg.eigvalsh(
                            np.eye(2) - np.sqrt(removal) @ compliance @ np.sqrt(removal)
                        )
                    )
                ),
            }

        for state_name, weak_flags, weak_connections in (
            ("10", (True, False), (0,)),
            ("01", (False, True), (separation,)),
            ("11", (True, True), tuple(sorted((0, separation)))),
        ):
            matrix_context = _matrix_context(mesh_context, weak_connections)
            solution, residual = _solve(matrix_context, common_source)
            direct_state_count += 1
            state_id = group_id + "__" + state_name
            record = _state_record(
                state_id, matrix_context, mesh_context, common_source, solution, residual, ports, weak_flags
            )
            direct_states[state_id] = record
            raw_states[state_id] = {"q": solution, "j": np.asarray(record["selected_openings_j"]), "t": np.asarray(record["selected_actual_connection_forces_t"]), "W": record["static_loading_work_half_f_dot_q"]}

        state_ids = {state: group_id + "__" + state for state in ("00", "10", "01", "11")}
        prediction_errors = {}
        for state_name, state_id in state_ids.items():
            direct = raw_states[state_id]
            prediction_errors[state_name] = {
                "opening": _relative_or_absolute_error(
                    direct["j"], np.asarray(predictions[state_name]["opening"]), OPENING_FLOOR
                ),
                "actual_connection_force": _relative_or_absolute_error(
                    direct["t"], np.asarray(predictions[state_name]["actual_connection_force"]), FORCE_FLOOR
                ),
            }

        raw = {state: raw_states[state_id] for state, state_id in state_ids.items()}
        conditional_opening = float(raw["11"]["j"][0] - raw["10"]["j"][0])
        conditional_force = float(raw["11"]["t"][0] - raw["10"]["t"][0])
        four_difference_opening = float(raw["11"]["j"][0] - raw["10"]["j"][0] - raw["01"]["j"][0] + raw["00"]["j"][0])
        four_difference_force = float(raw["11"]["t"][0] - raw["10"]["t"][0] - raw["01"]["t"][0] + raw["00"]["t"][0])
        s_value = float(0.5 * (compliance[0, 0] + compliance[1, 1]))
        g_value = float(0.5 * (compliance[0, 1] + compliance[1, 0]))
        p_value = float(0.5 * (j0[0] + j0[1]))
        denominator = (1.0 - PORT_REMOVAL * s_value) * (
            1.0 - PORT_REMOVAL * (s_value + g_value)
        )
        frozen_conditional = p_value * PORT_REMOVAL * g_value / denominator
        frozen_Ij = (
            p_value * PORT_REMOVAL**2 * g_value * (s_value + g_value) / denominator
        )
        frozen_It = (
            p_value
            * PORT_REMOVAL**2
            * g_value
            * (PORT_SPRING * (s_value + g_value) - 1.0)
            / denominator
        )
        formula_checks = {
            "conditional_opening": _relative_or_absolute_error(
                np.array([conditional_opening]), np.array([frozen_conditional]), OPENING_FLOOR
            ),
            "conditional_force": _relative_or_absolute_error(
                np.array([conditional_force]),
                np.array([(PORT_SPRING - PORT_REMOVAL) * frozen_conditional]),
                FORCE_FLOOR,
            ),
            "four_difference_opening": _relative_or_absolute_error(
                np.array([four_difference_opening]), np.array([frozen_Ij]), OPENING_FLOOR
            ),
            "four_difference_force": _relative_or_absolute_error(
                np.array([four_difference_force]), np.array([frozen_It]), FORCE_FLOOR
            ),
        }
        maximum_prediction_absolute = max(
            item[quantity]["absolute_l2"]
            for item in prediction_errors.values()
            for quantity in ("opening", "actual_connection_force")
        )
        label = "not_classified_near_zero"
        if abs(conditional_opening) > OPENING_FLOOR and abs(j0[0]) > OPENING_FLOOR and abs(j0[1]) > OPENING_FLOOR:
            label = "amplification" if conditional_opening > 0.0 else "screening"

        equal_work_states = {}
        work00 = raw["00"]["W"]
        for state_name in ("00", "10", "01", "11"):
            work = raw[state_name]["W"]
            scale = math.sqrt(work00 / work) if work00 > 0.0 and work > 0.0 else None
            equal_work_states[state_name] = {
                "raw_work": work,
                "amplitude_scale_sqrt_W00_over_W": scale,
                "rescaled_opening": (scale * raw[state_name]["j"]).tolist() if scale is not None else None,
                "rescaled_connection_force": (scale * raw[state_name]["t"]).tolist() if scale is not None else None,
                "no_additional_solve": True,
            }
        rescaled = equal_work_states
        equal_work_contrasts = None
        if all(rescaled[state]["amplitude_scale_sqrt_W00_over_W"] is not None for state in rescaled):
            rj = {state: np.asarray(rescaled[state]["rescaled_opening"]) for state in rescaled}
            rt = {state: np.asarray(rescaled[state]["rescaled_connection_force"]) for state in rescaled}
            equal_work_contrasts = {
                "conditional_opening_j1_11_minus_10": float(rj["11"][0] - rj["10"][0]),
                "conditional_force_t1_11_minus_10": float(rt["11"][0] - rt["10"][0]),
                "four_difference_opening": float(rj["11"][0] - rj["10"][0] - rj["01"][0] + rj["00"][0]),
                "four_difference_force": float(rt["11"][0] - rt["10"][0] - rt["01"][0] + rt["00"][0]),
            }

        groups[group_id] = {
            "thickness_ratio_h_over_a": thickness_ratio,
            "connection_separation_d": separation,
            "resolution": resolution,
            "mesh_key": f"h_over_a_{thickness_ratio:g}__nx_{nx}__ny_{ny}",
            "state_ids": state_ids,
            "baseline_flexibility": {
                "G": compliance.tolist(),
                "sources": {
                    "connection_1_c0": _source_record(port1),
                    "connection_2_cd": _source_record(port2),
                    "each_source_is_a_balanced_top_horizontal_force_pair": bool(
                        abs(np.sum(port1[:CELL_DOF_COUNT:2])) <= 1.0e-15
                        and abs(np.sum(port2[:CELL_DOF_COUNT:2])) <= 1.0e-15
                    ),
                },
                "columns": {
                    "connection_1": _state_vector_record(flexibility[:, 0], nx, ny),
                    "connection_2": _state_vector_record(flexibility[:, 1], nx, ny),
                },
                "column_residuals": flexibility_residuals,
                "G11_minus_G22": float(compliance[0, 0] - compliance[1, 1]),
                "G12_minus_G21": float(compliance[0, 1] - compliance[1, 0]),
                "j0": j0.tolist(),
                "j1_0_minus_j2_0": float(j0[0] - j0[1]),
                "s_average": s_value,
                "g_average": g_value,
                "p_average": p_value,
                "chi_G12_j2_over_j1": _safe_ratio(
                    float(compliance[0, 1] * j0[1]), float(j0[0]), OPENING_FLOOR
                ),
                "baseline_positive_and_port_nonzero": bool(j0[0] > OPENING_FLOOR and j0[1] > OPENING_FLOOR),
            },
            "precomputed_two_port_predictions": predictions,
            "direct_prediction_errors": prediction_errors,
            "frozen_formula_values": {
                "conditional_opening": frozen_conditional,
                "conditional_force": (PORT_SPRING - PORT_REMOVAL) * frozen_conditional,
                "four_difference_opening": frozen_Ij,
                "four_difference_force": frozen_It,
                "denominator": denominator,
                "k_times_s_plus_g": PORT_SPRING * (s_value + g_value),
            },
            "frozen_formula_checks": formula_checks,
            "raw_main_readout": {
                "conditional_opening_j1_11_minus_j1_10": conditional_opening,
                "conditional_connection_force_t1_11_minus_t1_10": conditional_force,
                "four_difference_opening": four_difference_opening,
                "four_difference_connection_force": four_difference_force,
                "classification_from_frozen_positive_port_orientation": label,
                "opening_and_force_conditional_same_sign_expected": bool(
                    conditional_opening * conditional_force > 0.0
                    or (abs(conditional_opening) <= OPENING_FLOOR and abs(conditional_force) <= FORCE_FLOOR)
                ),
                "opening_and_force_four_differences_opposite_sign_typical": bool(
                    four_difference_opening * four_difference_force < 0.0
                ),
                "effect_to_prediction_absolute_error_ratio": abs(conditional_opening)
                / max(
                    max(
                        item["opening"]["absolute_l2"]
                        for item in prediction_errors.values()
                    ),
                    OPENING_FLOOR,
                ),
            },
            "equal_static_work_rescaling": {
                "states": equal_work_states,
                "contrasts": equal_work_contrasts,
                "raw_and_rescaled_kept_separate": True,
                "no_additional_solve": True,
            },
        }

    center_group_id = "h_over_a_1__d_1__coarse"
    center_group = groups[center_group_id]
    center_mesh = mesh_contexts[(1.0, 32, 8)]
    center_matrix = _matrix_context(center_mesh, (0, 1))
    center_port1 = _port_vector(0, center_mesh["total_dofs"])
    center_port2 = _port_vector(1, center_mesh["total_dofs"])
    center_ports = np.column_stack((center_port1, center_port2))
    center_source = FORCE_AMPLITUDE * (center_port1 + center_port2)
    center_full_id = center_group["state_ids"]["11"]
    center_full = raw_states[center_full_id]
    controls = {}
    for name, source_scale in (("zero_force", 0.0), ("half_force", 0.5)):
        source = source_scale * center_source
        solution, residual = _solve(center_matrix, source)
        direct_state_count += 1
        state_id = center_group_id + "__11__" + name
        record = _state_record(
            state_id, center_matrix, center_mesh, source, solution, residual, center_ports, (True, True)
        )
        direct_states[state_id] = record
        raw_states[state_id] = {"q": solution, "j": np.asarray(record["selected_openings_j"]), "t": np.asarray(record["selected_actual_connection_forces_t"]), "W": record["static_loading_work_half_f_dot_q"]}
        controls[name] = state_id

    zero_raw = raw_states[controls["zero_force"]]
    half_raw = raw_states[controls["half_force"]]
    control_checks = {
        "zero_force_maximum_absolute_displacement": float(np.max(np.abs(zero_raw["q"]))),
        "zero_force_absolute_tolerance": OPENING_FLOOR,
        "half_force_displacement_relative_error": float(
            np.linalg.norm(half_raw["q"] - 0.5 * center_full["q"])
            / max(np.linalg.norm(0.5 * center_full["q"]), OPENING_FLOOR)
        ),
        "half_force_opening_relative_error": float(
            np.linalg.norm(half_raw["j"] - 0.5 * center_full["j"])
            / max(np.linalg.norm(0.5 * center_full["j"]), OPENING_FLOOR)
        ),
        "half_force_connection_force_relative_error": float(
            np.linalg.norm(half_raw["t"] - 0.5 * center_full["t"])
            / max(np.linalg.norm(0.5 * center_full["t"]), FORCE_FLOOR)
        ),
        "half_force_energy_quarter_relative_error": abs(
            direct_states[controls["half_force"]]["total_elastic_energy"]
            - 0.25 * direct_states[center_full_id]["total_elastic_energy"]
        )
        / max(0.25 * direct_states[center_full_id]["total_elastic_energy"], 1.0e-30),
        "relative_tolerance": 1.0e-10,
    }
    control_checks["pass"] = (
        control_checks["zero_force_maximum_absolute_displacement"] <= OPENING_FLOOR
        and control_checks["half_force_displacement_relative_error"] <= 1.0e-10
        and control_checks["half_force_opening_relative_error"] <= 1.0e-10
        and control_checks["half_force_connection_force_relative_error"] <= 1.0e-10
        and control_checks["half_force_energy_quarter_relative_error"] <= 1.0e-10
    )

    transition_summary = {}
    for separation in (1, 3):
        sampled = []
        for thickness_ratio in (0.2, 1.0, 5.0):
            group_id = f"h_over_a_{thickness_ratio:g}__d_{separation}__coarse"
            readout = groups[group_id]["raw_main_readout"]
            sampled.append(
                {
                    "h_over_a": thickness_ratio,
                    "conditional_opening": readout["conditional_opening_j1_11_minus_j1_10"],
                    "conditional_force": readout["conditional_connection_force_t1_11_minus_t1_10"],
                    "classification": readout["classification_from_frozen_positive_port_orientation"],
                    "g": groups[group_id]["baseline_flexibility"]["g_average"],
                    "chi": groups[group_id]["baseline_flexibility"]["chi_G12_j2_over_j1"],
                }
            )
        signs = [np.sign(item["conditional_opening"]) if abs(item["conditional_opening"]) > OPENING_FLOOR else 0 for item in sampled]
        transition_summary[f"d_{separation}"] = {
            "samples": sampled,
            "sampled_signs": [int(value) for value in signs],
            "sign_change_in_three_sampled_thicknesses": len(set(value for value in signs if value != 0)) > 1,
            "no_change_does_not_prove_no_continuous_zero": True,
        }

    coarse = groups["h_over_a_1__d_1__coarse"]["raw_main_readout"]
    fine = groups["h_over_a_1__d_1__fine"]["raw_main_readout"]
    grid_opening_change = abs(
        coarse["conditional_opening_j1_11_minus_j1_10"]
        - fine["conditional_opening_j1_11_minus_j1_10"]
    )
    grid_force_change = abs(
        coarse["conditional_connection_force_t1_11_minus_t1_10"]
        - fine["conditional_connection_force_t1_11_minus_t1_10"]
    )
    grid_check = {
        "coarse_group": "h_over_a_1__d_1__coarse",
        "fine_group": "h_over_a_1__d_1__fine",
        "conditional_opening_absolute_change": grid_opening_change,
        "conditional_opening_relative_to_fine": _safe_ratio(
            grid_opening_change,
            abs(fine["conditional_opening_j1_11_minus_j1_10"]),
            OPENING_FLOOR,
        ),
        "conditional_force_absolute_change": grid_force_change,
        "conditional_force_relative_to_fine": _safe_ratio(
            grid_force_change,
            abs(fine["conditional_connection_force_t1_11_minus_t1_10"]),
            FORCE_FLOOR,
        ),
        "exploratory_relative_standard": 0.05,
        "single_point_refinement_does_not_certify_interval": True,
    }
    grid_check["pass_exploratory"] = (
        grid_check["conditional_opening_relative_to_fine"] is not None
        and grid_check["conditional_force_relative_to_fine"] is not None
        and grid_check["conditional_opening_relative_to_fine"] <= 0.05
        and grid_check["conditional_force_relative_to_fine"] <= 0.05
    )

    numerical_metrics = {
        "maximum_direct_relative_residual": max(
            record["residual"]["relative_l2"]
            for record in direct_states.values()
            if record["residual"]["relative_l2"] is not None
        ),
        "zero_direct_absolute_residual": direct_states[controls["zero_force"]]["residual"]["absolute_l2"],
        "maximum_energy_closure_relative": max(record["energy_closure_relative"] for record in direct_states.values()),
        "maximum_matrix_symmetry_relative_error": max(
            context["symmetry_relative_error"]
            for mesh in mesh_contexts.values()
            for context in mesh["matrix_cache"].values()
        ),
        "minimum_matrix_eigenvalue": min(
            context["minimum_eigenvalue"]
            for mesh in mesh_contexts.values()
            for context in mesh["matrix_cache"].values()
        ),
        "maximum_flexibility_relative_residual": max(
            column["relative_l2"]
            for group in groups.values()
            for column in group["baseline_flexibility"]["column_residuals"]
        ),
        "maximum_prediction_relative_error_nonzero": max(
            error[quantity]["relative_l2"]
            for group in groups.values()
            for error in group["direct_prediction_errors"].values()
            for quantity in ("opening", "actual_connection_force")
            if error[quantity]["relative_l2"] is not None
        ),
        "maximum_formula_relative_error_nonzero": max(
            error["relative_l2"]
            for group in groups.values()
            for error in group["frozen_formula_checks"].values()
            if error["relative_l2"] is not None
        ),
        "maximum_G_reciprocity_relative_error": max(
            abs(group["baseline_flexibility"]["G12_minus_G21"])
            / max(
                abs(group["baseline_flexibility"]["G"][0][1]),
                abs(group["baseline_flexibility"]["G"][1][0]),
                1.0e-30,
            )
            for group in groups.values()
        ),
        "maximum_G_equal_diagonal_relative_error": max(
            abs(group["baseline_flexibility"]["G11_minus_G22"])
            / max(
                abs(group["baseline_flexibility"]["G"][0][0]),
                abs(group["baseline_flexibility"]["G"][1][1]),
                1.0e-30,
            )
            for group in groups.values()
        ),
        "maximum_baseline_equal_opening_relative_error": max(
            abs(group["baseline_flexibility"]["j1_0_minus_j2_0"])
            / max(
                abs(group["baseline_flexibility"]["j0"][0]),
                abs(group["baseline_flexibility"]["j0"][1]),
                OPENING_FLOOR,
            )
            for group in groups.values()
        ),
        "minimum_two_port_stability_eigenvalue": min(
            prediction["minimum_eigenvalue_symmetric_D_form"]
            for group in groups.values()
            for prediction in group["precomputed_two_port_predictions"].values()
        ),
        "opening_floor": OPENING_FLOOR,
        "force_floor": FORCE_FLOOR,
    }
    numerical_checks_pass = (
        numerical_metrics["maximum_direct_relative_residual"] <= 1.0e-8
        and numerical_metrics["maximum_energy_closure_relative"] <= 1.0e-8
        and numerical_metrics["maximum_matrix_symmetry_relative_error"] <= 1.0e-12
        and numerical_metrics["minimum_matrix_eigenvalue"] > 0.0
        and numerical_metrics["maximum_flexibility_relative_residual"] <= 1.0e-8
        and numerical_metrics["maximum_prediction_relative_error_nonzero"] <= 1.0e-7
        and numerical_metrics["maximum_formula_relative_error_nonzero"] <= 1.0e-7
        and numerical_metrics["maximum_G_reciprocity_relative_error"] <= 1.0e-8
        and numerical_metrics["maximum_G_equal_diagonal_relative_error"] <= 1.0e-8
        and numerical_metrics["maximum_baseline_equal_opening_relative_error"] <= 1.0e-8
        and numerical_metrics["minimum_two_port_stability_eigenvalue"] > 0.0
        and control_checks["pass"]
    )
    if direct_state_count != DIRECT_STATE_LIMIT:
        failures.append(f"direct state count {direct_state_count} != {DIRECT_STATE_LIMIT}")
    if flexibility_rhs_count != FLEXIBILITY_RHS_LIMIT:
        failures.append(f"flexibility RHS count {flexibility_rhs_count} != {FLEXIBILITY_RHS_LIMIT}")
    if direct_state_count + flexibility_rhs_count != TOTAL_RHS_LIMIT:
        failures.append("total linear RHS count is not 44")
    if not numerical_checks_pass:
        failures.append("one or more frozen numerical checks failed")
    if not analytic_assembly_checks["pass"]:
        failures.append("one or more analytic reimplementation checks failed")

    calculation_finish = datetime.now(timezone.utc)
    calculation_seconds = time.perf_counter() - calculation_timer
    if calculation_seconds > CALCULATION_BUDGET_SECONDS:
        failures.append("calculation budget exceeded")

    mesh_records = {}
    for (thickness_ratio, nx, ny), context in mesh_contexts.items():
        mesh_key = f"h_over_a_{thickness_ratio:g}__nx_{nx}__ny_{ny}"
        mesh_records[mesh_key] = {
            "h_over_a": thickness_ratio,
            "thickness": context["thickness"],
            "mesh": context["mesh_metadata"],
            "free_node_coordinates_half_open_periodic_x": context["free_coordinates"].tolist(),
            "matrix_variants": {
                ",".join(map(str, key)) if key else "none": {
                    "weak_top_x_connections": value["weak_top_x_connections"],
                    "shape": value["shape"],
                    "nnz": value["nnz"],
                    "sha256_csr": value["sha256_csr"],
                    "symmetry_relative_error": value["symmetry_relative_error"],
                    "minimum_eigenvalue": value["minimum_eigenvalue"],
                    "positive_definite": value["positive_definite"],
                }
                for key, value in context["matrix_cache"].items()
            },
        }

    cell_positions = []
    for cell in range(CELL_COUNT):
        left = -0.5 * BOX_LENGTH + cell * CELL_WIDTH
        right = left + CELL_WIDTH
        cell_positions.append([[left, 0.0], [right, 0.0], [right, CELL_HEIGHT], [left, CELL_HEIGHT]])

    payload = {
        "schema": "paper2_pair_junction_probe_v01",
        "status": "COMPLETED_BOUNDED_PAIR_JUNCTION_PROBE" if not failures else "COMPLETED_WITH_FAIL_CLOSED_CHECK_FAILURE",
        "scientific_question": "For eight closed cells coupled bidirectionally to a finite-thickness plane-strain ECM, do two preselected weak top-horizontal junction components switch from screening to amplification across the three frozen thickness samples?",
        "claim_boundary": {
            "static_local_balanced_force_pair_probe": True,
            "not_myocardial_active_drive_EFE_macro_shortening_or_cycle_work": True,
            "fixed_box_length_not_global_local_separation_evidence": True,
            "weakening_direction_is_idealized_not_whole_biological_junction": True,
            "equal_work_rescaling_is_separate_and_has_no_extra_solve": True,
            "two_port_prediction_is_algebraic_validation_not_blind_holdout": True,
            "not_DCM_exclusivity_or_Nature_Physics_mechanism_pass": True,
            "scientific_acceptance_pending_supervisor_independent_review": True,
        },
        "preregistration": {
            "frozen_HEAD": FROZEN_HEAD,
            "main_plan_section": 60,
            "science_brief_sections": [85, 85.4],
            "direct_source_verification": source_verification,
            "prior_statement_superseded_by_current_authorization": True,
        },
        "interface_reuse": {
            "cell_Jacobian": "read-only no-bytecode import of frozen closed-cell v01 physical function",
            "ECM": "same structured triangles, P1 engineering-strain B matrix, plane-strain constitutive law, and manual B^T C B formulas as frozen src/paper2_hybrid/model.py",
            "production_ECM_module_not_imported": True,
            "reason": "the module has mandatory top-level DOLFINx/PETSc dependencies unavailable in the authorized host Python",
            "no_new_dependency_container_or_production_API_change": True,
            "UFL_PETSc_crosscheck_current_run": "not_run",
            "prior_program_numerical_PASS_not_inherited": True,
        },
        "fixed_model": {
            "cell_count": CELL_COUNT,
            "a": CELL_WIDTH,
            "b": CELL_HEIGHT,
            "box_length_L": BOX_LENGTH,
            "cell_vertices_global_reference": cell_positions,
            "cell_vertex_order": "0 lower-left, 1 lower-right, 2 upper-right, 3 upper-left",
            "cell_parameters": {"K_A": K_AREA, "K_edge": K_EDGE, "kappa": K_ANGLE, "K_cc": K_CC, "K_ce": K_CE},
            "ECM": {"plane_strain": True, "E_eq": ECM_YOUNG, "nu": ECM_POISSON, "bottom_xy_fixed": True, "periodic_sides": True},
            "cell_ECM_attachment_density_rho": K_CE / (CELL_WIDTH * CELL_HEIGHT**2),
            "cell_ECM_attachment": "complete distributed two-component spring between each cell basal P1 trace and ECM top P1 trace",
            "port_opening": "j_n=u_(n+1),3,x-u_n,2,x without division by b",
            "selected_connections": {"connection_1": 0, "connection_2": "d in {1,3}"},
            "external_force": "f=F*(c0+cd)",
            "F": FORCE_AMPLITUDE,
            "weakening_alpha": WEAKENING_ALPHA,
            "base_top_x_port_stiffness_k": PORT_SPRING,
            "removed_stiffness_beta_alpha_k": PORT_REMOVAL,
            "other_three_components_per_selected_connection_unchanged": True,
            "no_macro_affine_strain_active_cell_fluid_damage_T1_or_feedback": True,
        },
        "mesh_records": mesh_records,
        "groups": groups,
        "direct_states": direct_states,
        "controls": {
            "state_ids": controls,
            "checks": control_checks,
        },
        "primary_transition_summary": transition_summary,
        "center_grid_exploratory_check": grid_check,
        "analytic_reimplementation_checks": analytic_assembly_checks,
        "numerical_checks": {
            "metrics": numerical_metrics,
            "targets": {"residual": 1.0e-8, "two_port_prediction": 1.0e-7, "energy_closure": 1.0e-8, "matrix_symmetry": 1.0e-12},
            "pass": numerical_checks_pass,
        },
        "execution_ledger": {
            "direct_static_states": direct_state_count,
            "baseline_flexibility_columns": flexibility_rhs_count,
            "total_linear_right_sides": direct_state_count + flexibility_rhs_count,
            "limits": {"direct_static_states": DIRECT_STATE_LIMIT, "flexibility_columns": FLEXIBILITY_RHS_LIMIT, "total": TOTAL_RHS_LIMIT},
            "failed_items": failures,
            "not_run_items": not_run,
            "all_requested_items_run": not failures and not not_run,
            "existing_scientific_and_Bloch_batches_not_recounted": True,
            "original_four_holdouts": "locked_not_read",
        },
        "runtime": {
            "preparation_started_at_utc": preparation_start.astimezone(timezone.utc).isoformat(),
            "calculation_started_at_utc": calculation_start.isoformat(),
            "calculation_finished_at_utc": calculation_finish.isoformat(),
            "preparation_elapsed_seconds": preparation_seconds,
            "preparation_budget_seconds": PREPARATION_BUDGET_SECONDS,
            "calculation_elapsed_seconds": calculation_seconds,
            "calculation_budget_seconds": CALCULATION_BUDGET_SECONDS,
            "entry_path": "scripts/run_paper2_pair_junction_probe_v01.py",
            "entry_sha256": _sha256(Path(__file__)),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "python_executable": sys.executable,
            "cpu_threads": 1,
            "BLAS_thread_environment": {
                **thread_environment,
                "all_equal_one": True,
            },
            "memory_budget_gib": 8,
            "hard_memory_limit_enforced": False,
            "largest_assembled_matrix_CSR_bytes": max(
                int(
                    context["K"].data.nbytes
                    + context["K"].indices.nbytes
                    + context["K"].indptr.nbytes
                )
                for mesh in mesh_contexts.values()
                for context in mesh["matrix_cache"].values()
            ),
            "bytecode_cache": "disabled",
            "GPU_network_container_project_external_files": "not_used",
        },
        "next_gate": "SUPERVISOR_INDEPENDENT_RECOMPUTATION_STOP",
    }
    _safe_write(output, payload)
    print(
        f"PAIR_JUNCTION_DONE status={payload['status']} states={direct_state_count} "
        f"flex={flexibility_rhs_count} calculation={calculation_seconds:.6f}s"
    )
    print("POSTSAVE_AUDIT " + json.dumps(WRITER_AUDIT, sort_keys=True, allow_nan=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
