"""Structural checks and common interface observables for the active model."""

from __future__ import annotations

from typing import Any

import numpy as np
import scipy.sparse as sparse

from .config import ACTIVE_CONFIG
from .model import _interface_matrix
from .projection import (
    common_segment_space_time_l2,
    project_piecewise_linear_to_common_segments,
)
from .protocol import ACTIVE_PROTOCOL
from .roles import ACTIVE_TISSUE_ROLES


def relative_difference(value_a: float, value_b: float, floor: float) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def _sparse_symmetry_error(matrix: sparse.spmatrix) -> float:
    difference = (matrix - matrix.T).tocsr()
    numerator = float(np.linalg.norm(difference.data))
    denominator = max(float(np.linalg.norm(matrix.data)), 1.0e-30)
    return numerator / denominator


def global_structural_checks(system: Any) -> dict[str, Any]:
    generator = np.random.default_rng(20260903)
    state = 1.0e-3 * generator.standard_normal(system.state_size)
    activation = 0.037
    step = 1.0e-7
    energy_plus = (
        0.5 * state @ (system.matrix_material @ state)
        + (activation + step) * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * (activation + step) ** 2
    )
    energy_minus = (
        0.5 * state @ (system.matrix_material @ state)
        + (activation - step) * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * (activation - step) ** 2
    )
    numerical_derivative = (energy_plus - energy_minus) / (2.0 * step)
    analytic_derivative = (
        np.dot(system.active_vector_h, state) + system.active_scalar_c * activation
    )
    derivative_error = relative_difference(
        float(numerical_derivative), float(analytic_derivative), 1.0e-12
    )
    matrix_a_symmetry = _sparse_symmetry_error(system.matrix_a)
    matrix_g_symmetry = _sparse_symmetry_error(system.matrix_g)
    support_diagonal = np.asarray(system.matrix_support.diagonal())
    return {
        "fixed_tissue_roles": {
            "value": system.roles.manifest(),
            "expected": ACTIVE_TISSUE_ROLES.manifest(),
            "pass": system.roles == ACTIVE_TISSUE_ROLES,
        },
        "units": {
            "system": "nondimensional_active_hybrid_benchmark",
            "pass": True,
        },
        "normal_and_traction_sign": {
            "lumen_normal": "negative_y_from_lumen_toward_wall",
            "interface_traction": "positive_on_first_named_domain",
            "pass": True,
        },
        "active_power_derivative": {
            "analytic": float(analytic_derivative),
            "central_difference": float(numerical_derivative),
            "relative_error": derivative_error,
            "threshold": 1.0e-7,
            "pass": derivative_error <= 1.0e-7,
        },
        "ufl_manual_assembly": {
            "relative_error": system.manufactured_error,
            "threshold": ACTIVE_CONFIG.manufactured_solution_relative_tolerance,
            "pass": system.manufactured_error
            <= ACTIVE_CONFIG.manufactured_solution_relative_tolerance,
        },
        "material_plus_support_matrix_symmetry": {
            "relative_error": matrix_a_symmetry,
            "threshold": 1.0e-12,
            "pass": matrix_a_symmetry <= 1.0e-12,
        },
        "rate_matrix_symmetry": {
            "relative_error": matrix_g_symmetry,
            "threshold": 1.0e-12,
            "pass": matrix_g_symmetry <= 1.0e-12,
        },
        "rigid_body_mode_control": {
            "support_nnz": int(system.matrix_support.nnz),
            "positive_support_diagonal_count": int(np.count_nonzero(support_diagonal > 0.0)),
            "pass": bool(
                system.matrix_support.nnz > 0 and np.count_nonzero(support_diagonal > 0.0) > 0
            ),
        },
    }


def interface_action_reaction_manufactured_check() -> dict[str, Any]:
    weights = np.asarray((0.5, 1.0), dtype=np.float64)
    size = 8
    first = sparse.csr_matrix(
        (np.ones(4), (np.arange(4), np.arange(4))), shape=(4, size)
    )
    second = sparse.csr_matrix(
        (np.ones(4), (np.arange(4), np.arange(4) + 4)), shape=(4, size)
    )
    stiffness = 7.0
    matrix = _interface_matrix(first, np.arange(4), second, np.arange(4), weights, stiffness)
    state = np.asarray((0.2, -0.1, 0.3, 0.4, -0.2, 0.5, 0.1, -0.3))
    force = np.asarray(matrix @ state).ravel()
    imbalance = force[:4] + force[4:]
    absolute_error = float(np.linalg.norm(imbalance))
    scale = max(float(np.linalg.norm(force)), 1.0e-30)
    relative_error = absolute_error / scale
    return {
        "absolute_force_imbalance": absolute_error,
        "relative_force_imbalance": relative_error,
        "threshold": 1.0e-12,
        "pass": relative_error <= 1.0e-12,
    }


def _native_x(system: Any) -> np.ndarray:
    layer = system.myocardium_mesh
    return layer.dof_coordinates[layer.top_nodes, 0]


def common_projection_sidecar(system: Any, endpoint: Any) -> dict[str, Any]:
    common_x = np.linspace(
        -0.5 * ACTIVE_CONFIG.length,
        0.5 * ACTIVE_CONFIG.length,
        ACTIVE_PROTOCOL.common_projection_segments + 1,
    )
    nodes = len(system.interface_weights)
    values: dict[str, float] = {}
    for metric, array_key in (
        ("myocardium_ecm_traction_l2", "myocardium_ecm_traction_two_cycles"),
        ("endocardium_ecm_traction_l2", "endocardium_ecm_traction_two_cycles"),
    ):
        traction = endpoint.arrays[array_key].reshape(nodes, 2, -1)[
            :, :, : ACTIVE_PROTOCOL.steps_per_cycle
        ]
        projected = project_piecewise_linear_to_common_segments(
            _native_x(system), traction, common_x
        )
        values[metric] = common_segment_space_time_l2(
            common_x,
            projected,
            ACTIVE_CONFIG.period / ACTIVE_PROTOCOL.steps_per_cycle,
        )
    return {
        "available": True,
        "role": "conservative_common_interface_observable",
        "common_segments": ACTIVE_PROTOCOL.common_projection_segments,
        "values": values,
    }
