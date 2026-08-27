from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize, root
from scipy.sparse import coo_matrix, diags, eye
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh, splu


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from route_h.dcm_cell import surface_volume_and_gradient  # noqa: E402

from hybrid.efe_fast_trilayer import (  # noqa: E402
    FastTrilayerModel,
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    _diagonal_preconditioner,
    _full_external_force,
    _full_stored_gradient,
    _kkt_audit,
    augmented_contact_energy_gradient,
    build_exact_volume_coordinates,
    contact_kkt_audit,
    reduce_gradient_to_exact_volume_manifold,
    solve_fast_trilayer_equilibrium,
    trilayer_gap_constraints,
    unpack_exact_volume_variables,
)

INPUT = (
    ROOT
    / "results/hybrid/efe_node1_fast_trilayer_v04_20260817/active_only/step_00.npz"
)
OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_sparse_preconditioner_diagnostic_v01_20260818"
)


def node_adjacency(model: FastTrilayerModel) -> list[set[int]]:
    myocyte_count = len(model.myocyte.vertices)
    ecm_count = len(model.ecm_reference.vertices)
    endocardial_count = len(model.endocardium.vertices)
    node_count = myocyte_count + ecm_count + endocardial_count
    adjacency = [{node_id} for node_id in range(node_count)]

    def add_clique(node_ids: np.ndarray) -> None:
        ids = [int(node_id) for node_id in node_ids]
        for node_id in ids:
            adjacency[node_id].update(ids)

    for face in model.myocyte.faces:
        add_clique(face)
    for hinge in model.myocyte.cell.hinges.vertices:
        add_clique(hinge)
    for edge in model.myocyte_fibers.edges:
        add_clique(edge)
    for tetrahedron in model.ecm_reference.tetrahedra:
        add_clique(myocyte_count + tetrahedron)
    endocardial_offset = myocyte_count + ecm_count
    for face in model.endocardium.faces:
        add_clique(endocardial_offset + face)
    for hinge in model.endocardium.cell.hinges.vertices:
        add_clique(endocardial_offset + hinge)

    interface_specs = (
        (model.myocyte_interface, model.myocyte.faces, 0),
        (
            model.endocardial_interface,
            model.endocardium.faces,
            endocardial_offset,
        ),
    )
    for interface, cell_faces, cell_offset in interface_specs:
        row_by_id = {
            int(point_id): row
            for row, point_id in enumerate(interface.registry.point_ids)
        }
        for tether in interface.tethers:
            row = row_by_id[tether.material_point_id]
            cell_face = cell_offset + cell_faces[
                int(interface.registry.face_ids[row])
            ]
            ecm_face = myocyte_count + interface.ecm_boundary_faces[
                tether.ecm_face_id
            ]
            add_clique(np.concatenate((cell_face, ecm_face)))
    return adjacency


def distance_two_coloring(adjacency: list[set[int]]) -> np.ndarray:
    conflicts: list[set[int]] = []
    for neighbors in adjacency:
        local_conflicts: set[int] = set()
        for neighbor in neighbors:
            local_conflicts.update(adjacency[neighbor])
        conflicts.append(local_conflicts)
    order = sorted(
        range(len(adjacency)),
        key=lambda node_id: len(conflicts[node_id]),
        reverse=True,
    )
    colors = np.full(len(adjacency), -1, dtype=np.int64)
    for node_id in order:
        used = {
            int(colors[other])
            for other in conflicts[node_id]
            if colors[other] >= 0
        }
        color = 0
        while color in used:
            color += 1
        colors[node_id] = color
    return colors


def split_full_state(
    model: FastTrilayerModel,
    flat: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    myocyte_end = model.myocyte.vertices.size
    ecm_end = myocyte_end + model.ecm_reference.vertices.size
    return (
        flat[:myocyte_end].reshape(model.myocyte.vertices.shape),
        flat[myocyte_end:ecm_end].reshape(model.ecm_reference.vertices.shape),
        flat[ecm_end:].reshape(model.endocardium.vertices.shape),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--activation", type=float, default=0.06)
    parser.add_argument("--pressure", type=float, default=0.0)
    parser.add_argument("--wss-x", type=float, default=0.0)
    parser.add_argument("--dcm-level", choices=("D0", "D1"), default="D0")
    parser.add_argument(
        "--ecm-level", choices=("E0", "E1", "E2"), default="E0"
    )
    parser.add_argument("--ecm-footprint-scale", type=float, default=1.0)
    parser.add_argument("--maximum-follower-iterations", type=int, default=5)
    parser.add_argument("--follower-tolerance", type=float, default=1.0e-7)
    parser.add_argument("--maximum-contact-iterations", type=int, default=6)
    parser.add_argument("--contact-tolerance", type=float, default=1.0e-7)
    parser.add_argument("--contact-penalty", type=float, default=1.0)
    parser.add_argument("--contact-penalty-growth", type=float, default=10.0)
    parser.add_argument("--coarse-iterations", type=int, default=20)
    parser.add_argument("--skip-coarse", action="store_true")
    parser.add_argument("--skip-sparse-spectral", action="store_true")
    parser.add_argument("--dense-minimum-eigenvalue", action="store_true")
    parser.add_argument("--newton-iterations", type=int, default=20)
    parser.add_argument("--optimizer-ftol", type=float, default=1.0e-15)
    parser.add_argument("--optimizer-gtol", type=float, default=1.0e-8)
    parser.add_argument(
        "--ecm-backend",
        choices=("reference", "fenicsx"),
        default="reference",
    )
    parser.add_argument(
        "--method",
        choices=(
            "krylov",
            "df_sane",
            "modified_newton",
            "spectral_lbfgs",
        ),
        default="krylov",
    )
    arguments = parser.parse_args()
    input_path = arguments.input.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    activation = arguments.activation
    pressure = arguments.pressure
    wss_command = np.asarray([arguments.wss_x, 0.0, 0.0], dtype=np.float64)
    model = build_fast_trilayer_model(
        dcm_level=arguments.dcm_level,
        ecm_level=arguments.ecm_level,
        ecm_footprint_scale=arguments.ecm_footprint_scale,
    )
    fenicsx_backend = None
    selected_ecm_backend = None
    if arguments.ecm_backend == "fenicsx":
        from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

        fenicsx_backend = FenicsxECMBackend(model.ecm_reference)
        selected_ecm_backend = fenicsx_backend.energy_force
    coordinates = build_exact_volume_coordinates(model)
    input_arrays = np.load(input_path)
    initial_variables = np.asarray(input_arrays["variables"], dtype=np.float64)
    ecm_internal_z = (
        np.asarray(input_arrays["ecm_internal_z"], dtype=np.float64).copy()
        if "ecm_internal_z" in input_arrays
        else np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3),
            dtype=np.float64,
        )
    )
    if ecm_internal_z.shape != (
        len(model.ecm_reference.tetrahedra),
        3,
        3,
    ):
        raise ValueError("checkpoint ECM internal-variable shape mismatch")

    coarse_start = time.perf_counter()
    if arguments.skip_coarse:
        variables = initial_variables.copy()
        coarse_kkt = None
        coarse_optimizer_evaluations = 0
        coarse_newton_evaluations = 0
    else:
        coarse = solve_fast_trilayer_equilibrium(
            model,
            initial_variables=initial_variables,
            activation=activation,
            pressure=pressure,
            wss_command=wss_command,
            ecm_internal_z=ecm_internal_z,
            ecm_backend=selected_ecm_backend,
            maximum_iterations=arguments.coarse_iterations,
            maximum_newton_iterations=1,
            maximum_follower_iterations=1,
        )
        variables = coarse.variables.copy()
        coarse_kkt = coarse.normalized_kkt_residual
        coarse_optimizer_evaluations = coarse.optimizer_evaluations
        coarse_newton_evaluations = coarse.newton_evaluations
    coarse_seconds = time.perf_counter() - coarse_start
    variable_scales, block_scales = _diagonal_preconditioner(
        model, coordinates, ecm_backend=selected_ecm_backend
    )
    myocyte, ecm, endocardium = unpack_exact_volume_variables(
        model,
        coordinates,
        variables,
    )
    full_state = np.concatenate(
        (myocyte.reshape(-1), ecm.reshape(-1), endocardium.reshape(-1))
    )
    base_evaluation = evaluate_fast_trilayer_state(
        model,
        myocyte,
        ecm,
        endocardium,
        activation=activation,
        ecm_internal_z=ecm_internal_z,
        ecm_backend=selected_ecm_backend,
        reject_penetration=False,
    )
    base_stored_gradient = _full_stored_gradient(base_evaluation)
    frozen_external_force = _full_external_force(
        model,
        coordinates,
        endocardium,
        pressure=pressure,
        wss_command=wss_command,
    )
    base_objective_gradient = base_stored_gradient - frozen_external_force
    _, myocyte_volume_gradient = surface_volume_and_gradient(
        myocyte,
        model.myocyte.faces,
    )
    _, endocardial_volume_gradient = surface_volume_and_gradient(
        endocardium,
        model.endocardium.faces,
    )
    base_constraint_gradients = np.zeros((2, len(full_state)), dtype=np.float64)
    myocyte_coordinate_count = model.myocyte.vertices.size
    ecm_coordinate_count = model.ecm_reference.vertices.size
    endocardial_start = myocyte_coordinate_count + ecm_coordinate_count
    base_constraint_gradients[0, :myocyte_coordinate_count] = (
        myocyte_volume_gradient.reshape(-1) / model.myocyte.cell.volume0
    )
    base_constraint_gradients[1, endocardial_start:] = (
        endocardial_volume_gradient.reshape(-1)
        / model.endocardium.cell.volume0
    )

    adjacency = node_adjacency(model)
    node_colors = distance_two_coloring(adjacency)
    free_full_indices = coordinates.free_indices
    all_full_indices = np.arange(len(full_state), dtype=np.int64)
    full_node_ids = all_full_indices // 3
    full_components = all_full_indices % 3
    dof_colors = 3 * node_colors[full_node_ids] + full_components
    color_count = int(dof_colors.max()) + 1

    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    constraint_values: tuple[list[float], list[float]] = ([], [])
    perturbation = 2.0e-6
    assembly_start = time.perf_counter()
    for color in range(color_count):
        columns = np.flatnonzero(dof_colors == color)
        perturbed = full_state.copy()
        perturbed[columns] += perturbation
        state = split_full_state(model, perturbed)
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=activation,
            ecm_internal_z=ecm_internal_z,
            ecm_backend=selected_ecm_backend,
            reject_penetration=False,
        )
        gradient_difference = (
            _full_stored_gradient(evaluation) - base_stored_gradient
        ) / perturbation
        _, perturbed_myocyte_volume_gradient = surface_volume_and_gradient(
            state[0],
            model.myocyte.faces,
        )
        _, perturbed_endocardial_volume_gradient = surface_volume_and_gradient(
            state[2],
            model.endocardium.faces,
        )
        perturbed_constraint_gradients = np.zeros_like(
            base_constraint_gradients
        )
        perturbed_constraint_gradients[0, :myocyte_coordinate_count] = (
            perturbed_myocyte_volume_gradient.reshape(-1)
            / model.myocyte.cell.volume0
        )
        perturbed_constraint_gradients[1, endocardial_start:] = (
            perturbed_endocardial_volume_gradient.reshape(-1)
            / model.endocardium.cell.volume0
        )
        constraint_gradient_difference = (
            perturbed_constraint_gradients - base_constraint_gradients
        ) / perturbation
        for column in columns:
            node_id = int(full_node_ids[column])
            support_full_indices = np.asarray(
                [
                    3 * support_node + component
                    for support_node in adjacency[node_id]
                    for component in range(3)
                ],
                dtype=np.int64,
            )
            selected_values = gradient_difference[support_full_indices]
            row_indices.extend(support_full_indices.tolist())
            column_indices.extend([int(column)] * len(support_full_indices))
            values.extend(selected_values.tolist())
            for constraint_id in range(2):
                constraint_values[constraint_id].extend(
                    constraint_gradient_difference[
                        constraint_id,
                        support_full_indices,
                    ].tolist()
                )
    assembly_seconds = time.perf_counter() - assembly_start

    full_coordinate_count = len(full_state)
    tangent = coo_matrix(
        (values, (row_indices, column_indices)),
        shape=(full_coordinate_count, full_coordinate_count),
    ).tocsr()
    constraint_tangents = tuple(
        coo_matrix(
            (local_values, (row_indices, column_indices)),
            shape=(full_coordinate_count, full_coordinate_count),
        ).tocsr()
        for local_values in constraint_values
    )
    antisymmetric = tangent - tangent.T
    symmetry_residual = float(
        np.linalg.norm(antisymmetric.data)
        / max(1.0, float(np.linalg.norm(tangent.data)))
    )
    tangent = 0.5 * (tangent + tangent.T)
    constraint_tangents = tuple(
        0.5 * (constraint_tangent + constraint_tangent.T)
        for constraint_tangent in constraint_tangents
    )
    dependent_indices = np.asarray(
        [
            coordinates.myocyte_dependent_index,
            coordinates.endocardial_dependent_index,
        ],
        dtype=np.int64,
    )
    volume_multipliers = np.asarray(
        [
            -base_objective_gradient[dependent_index]
            / base_constraint_gradients[constraint_id, dependent_index]
            for constraint_id, dependent_index in enumerate(dependent_indices)
        ],
        dtype=np.float64,
    )
    lagrangian_tangent = tangent.copy()
    for multiplier, constraint_tangent in zip(
        volume_multipliers,
        constraint_tangents,
        strict=True,
    ):
        lagrangian_tangent += multiplier * constraint_tangent
    free_tangent = lagrangian_tangent[free_full_indices][:, free_full_indices]
    free_dependent = lagrangian_tangent[free_full_indices][
        :, dependent_indices
    ].toarray()
    dependent_tangent = lagrangian_tangent[dependent_indices][
        :, dependent_indices
    ].toarray()
    constraint_ratio = np.vstack(
        [
            base_constraint_gradients[constraint_id, free_full_indices]
            / base_constraint_gradients[constraint_id, dependent_index]
            for constraint_id, dependent_index in enumerate(dependent_indices)
        ]
    )
    variable_count = len(free_full_indices)
    scale_matrix = diags(variable_scales)
    scaled_free_tangent = (
        scale_matrix @ free_tangent @ scale_matrix
    ).tocsc()
    diagonal = np.abs(scaled_free_tangent.diagonal())
    positive_diagonal = diagonal[diagonal > 1.0e-12]
    diagonal_scale = (
        float(np.median(positive_diagonal))
        if len(positive_diagonal)
        else 1.0
    )
    low_rank_left = np.column_stack(
        (free_dependent, constraint_ratio.T)
    )
    low_rank_middle = np.block(
        [
            [np.zeros((2, 2)), -np.eye(2)],
            [-np.eye(2), dependent_tangent],
        ]
    )
    scaled_low_rank_left = variable_scales[:, None] * low_rank_left

    def apply_unshifted_tangent(vector: np.ndarray) -> np.ndarray:
        return scaled_free_tangent @ vector + scaled_low_rank_left @ (
            low_rank_middle @ (scaled_low_rank_left.T @ vector)
        )

    spectral_start = time.perf_counter()
    spectral_eigenvalues: np.ndarray | None = None
    spectral_eigenvectors: np.ndarray | None = None
    sparse_spectral_converged: bool | None = None
    if arguments.method == "spectral_lbfgs":
        dense_low_rank = scaled_low_rank_left @ (
            low_rank_middle @ scaled_low_rank_left.T
        )
        dense_scaled_tangent = scaled_free_tangent.toarray() + dense_low_rank
        spectral_eigenvalues, spectral_eigenvectors = eigh(
            dense_scaled_tangent,
            eigvals_only=False,
            check_finite=False,
        )
        minimum_tangent_eigenvalue = float(spectral_eigenvalues[0])
    else:
        tangent_operator = LinearOperator(
            (variable_count, variable_count),
            matvec=apply_unshifted_tangent,
            dtype=np.float64,
        )
        if arguments.dense_minimum_eigenvalue:
            dense_low_rank = scaled_low_rank_left @ (
                low_rank_middle @ scaled_low_rank_left.T
            )
            dense_scaled_tangent = (
                scaled_free_tangent.toarray() + dense_low_rank
            )
            minimum_tangent_eigenvalue = float(
                eigh(
                    dense_scaled_tangent,
                    subset_by_index=(0, 0),
                    eigvals_only=True,
                    check_finite=False,
                )[0]
            )
            sparse_spectral_converged = True
        elif arguments.skip_sparse_spectral:
            sparse_spectral_converged = False
            minimum_tangent_eigenvalue = 0.0
        else:
            try:
                sparse_eigenvalues = eigsh(
                    tangent_operator,
                    k=1,
                    which="SA",
                    return_eigenvectors=False,
                    tol=1.0e-5,
                    maxiter=800,
                )
                minimum_tangent_eigenvalue = float(sparse_eigenvalues[0])
                sparse_spectral_converged = True
            except ArpackNoConvergence as error:
                sparse_spectral_converged = False
                if len(error.eigenvalues):
                    minimum_tangent_eigenvalue = float(
                        np.min(error.eigenvalues)
                    )
                else:
                    probe_rng = np.random.default_rng(20260818)
                    rayleigh_values: list[float] = []
                    for _ in range(24):
                        probe = probe_rng.normal(size=variable_count)
                        probe /= np.linalg.norm(probe)
                        rayleigh_values.append(
                            float(
                                np.dot(
                                    probe,
                                    apply_unshifted_tangent(probe),
                                )
                            )
                        )
                    minimum_tangent_eigenvalue = min(rayleigh_values)
    spectral_seconds = time.perf_counter() - spectral_start
    shift = (
        max(
            1.0e-8 * diagonal_scale,
            -minimum_tangent_eigenvalue + 1.0e-8 * diagonal_scale,
        )
        if sparse_spectral_converged is not False
        else 1.0e-6 * diagonal_scale
    )
    factor = None
    factor_attempts = 0
    factor_start = time.perf_counter()
    for factor_attempts in range(1, 9):
        try:
            factor = splu(
                scaled_free_tangent
                + shift * eye(variable_count, format="csc")
            )
            break
        except RuntimeError:
            shift = max(1.0e-12, 10.0 * shift)
    factor_seconds = time.perf_counter() - factor_start
    if factor is None:
        raise RuntimeError("sparse tangent factorization failed")
    inverse_low_rank_left = factor.solve(scaled_low_rank_left)
    woodbury_core = np.linalg.inv(
        np.linalg.inv(low_rank_middle)
        + scaled_low_rank_left.T @ inverse_low_rank_left
    )

    def apply_preconditioner(vector: np.ndarray) -> np.ndarray:
        base_solution = factor.solve(vector)
        return base_solution - inverse_low_rank_left @ (
            woodbury_core @ (scaled_low_rank_left.T @ base_solution)
        )

    preconditioner = LinearOperator(
        (variable_count, variable_count),
        matvec=apply_preconditioner,
        dtype=np.float64,
    )

    residual_evaluations = 0

    def scaled_force_residual(current: np.ndarray) -> np.ndarray:
        nonlocal residual_evaluations
        residual_evaluations += 1
        physical_variables = variable_scales * current
        state = unpack_exact_volume_variables(
            model,
            coordinates,
            physical_variables,
        )
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=activation,
            ecm_internal_z=ecm_internal_z,
            ecm_backend=selected_ecm_backend,
            reject_penetration=False,
        )
        full_gradient = (
            _full_stored_gradient(evaluation) - frozen_external_force
        )
        reduced = reduce_gradient_to_exact_volume_manifold(
            model,
            coordinates,
            full_gradient,
            state[0],
            state[2],
        )
        return variable_scales * reduced

    scaled_initial = variables / variable_scales
    initial_residual = scaled_force_residual(scaled_initial)
    tangent_audits: list[dict[str, float]] = []
    rng = np.random.default_rng(20260818)
    audit_perturbation = 1.0e-6
    for _ in range(3):
        direction = rng.normal(size=variable_count)
        direction /= np.linalg.norm(direction)
        exact_product = (
            scaled_force_residual(
                scaled_initial + audit_perturbation * direction
            )
            - scaled_force_residual(
                scaled_initial - audit_perturbation * direction
            )
        ) / (2.0 * audit_perturbation)
        approximate_product = apply_unshifted_tangent(direction)
        tangent_audits.append(
            {
                "relative_error": float(
                    np.linalg.norm(approximate_product - exact_product)
                    / max(1.0e-12, float(np.linalg.norm(exact_product)))
                ),
                "cosine": float(
                    np.dot(approximate_product, exact_product)
                    / max(
                        1.0e-12,
                        float(np.linalg.norm(approximate_product))
                        * float(np.linalg.norm(exact_product)),
                    )
                ),
            }
        )
    residual_evaluations = 0
    solve_start = time.perf_counter()
    iteration_history: list[dict[str, float | int | bool]] = []
    follower_history: list[dict[str, float | int | bool | str]] = []
    contact_history: list[dict[str, float | int | bool | str]] = []
    contact_projection_history: list[dict[str, float | int | bool]] = []
    follower_residual = 0.0
    contact_converged = True
    reference_gaps, _ = trilayer_gap_constraints(
        model,
        coordinates,
        np.zeros(len(coordinates.free_indices), dtype=np.float64),
    )
    if "contact_multipliers" in input_arrays:
        contact_multipliers = np.asarray(
            input_arrays["contact_multipliers"],
            dtype=np.float64,
        ).copy()
        if contact_multipliers.shape != reference_gaps.shape:
            raise ValueError("checkpoint contact multiplier shape mismatch")
    else:
        contact_multipliers = np.zeros_like(reference_gaps)
    contact_complementarity = 0.0
    contact_penetration = 0.0
    spectral_floor: float | None = None
    if arguments.method == "krylov":
        newton = root(
            scaled_force_residual,
            scaled_initial,
            method="krylov",
            options={
                "maxiter": arguments.newton_iterations,
                "fatol": 1.0e-7,
                "jac_options": {
                    "inner_maxiter": 30,
                    "inner_M": preconditioner,
                },
            },
        )
        solved_scaled_variables = np.asarray(newton.x, dtype=np.float64)
        final_scaled_residual = np.asarray(newton.fun, dtype=np.float64)
        solver_success = bool(newton.success)
        solver_message = str(newton.message)
        solver_iterations = int(newton.nit)
        solver_evaluations = int(newton.nfev)
    elif arguments.method == "df_sane":
        newton = root(
            scaled_force_residual,
            scaled_initial,
            method="df-sane",
            options={
                "maxfev": arguments.newton_iterations,
                "fatol": 1.0e-7,
            },
        )
        solved_scaled_variables = np.asarray(newton.x, dtype=np.float64)
        final_scaled_residual = np.asarray(newton.fun, dtype=np.float64)
        solver_success = bool(newton.success)
        solver_message = str(newton.message)
        solver_iterations = int(getattr(newton, "nit", newton.nfev))
        solver_evaluations = int(newton.nfev)
    elif arguments.method == "modified_newton":
        solved_scaled_variables = scaled_initial.copy()
        solver_success = False
        solver_message = "maximum modified-Newton iterations reached"
        solver_iterations = 0
        external_force = np.zeros_like(coordinates.reference_flat)
        for iteration in range(1, arguments.newton_iterations + 1):
            physical_variables = variable_scales * solved_scaled_variables
            current_state = unpack_exact_volume_variables(
                model,
                coordinates,
                physical_variables,
            )
            current_evaluation = evaluate_fast_trilayer_state(
                model,
                *current_state,
                activation=activation,
                ecm_internal_z=ecm_internal_z,
                ecm_backend=selected_ecm_backend,
                reject_penetration=False,
            )
            residual_evaluations += 1
            current_full_gradient = _full_stored_gradient(current_evaluation)
            current_reduced_gradient = reduce_gradient_to_exact_volume_manifold(
                model,
                coordinates,
                current_full_gradient,
                current_state[0],
                current_state[2],
            )
            current_scaled_gradient = (
                variable_scales * current_reduced_gradient
            )
            _, current_kkt = _kkt_audit(
                model,
                coordinates,
                current_evaluation,
                current_state[0],
                current_state[2],
                external_force,
            )
            if current_kkt <= 1.0e-5:
                solver_success = True
                solver_message = "contract KKT reached by modified Newton"
                solver_iterations = iteration - 1
                break
            direction = -apply_preconditioner(current_scaled_gradient)
            slope = float(np.dot(current_scaled_gradient, direction))
            used_gradient_fallback = False
            if not np.isfinite(slope) or slope >= 0.0:
                direction = -current_scaled_gradient
                slope = -float(
                    np.dot(current_scaled_gradient, current_scaled_gradient)
                )
                used_gradient_fallback = True
            step_length = 1.0
            accepted = False
            candidate_evaluation = current_evaluation
            for line_search_iteration in range(1, 31):
                candidate_scaled = (
                    solved_scaled_variables + step_length * direction
                )
                candidate_variables = variable_scales * candidate_scaled
                if np.max(np.abs(candidate_variables)) > 0.15:
                    step_length *= 0.5
                    continue
                try:
                    candidate_state = unpack_exact_volume_variables(
                        model,
                        coordinates,
                        candidate_variables,
                    )
                    candidate_evaluation = evaluate_fast_trilayer_state(
                        model,
                        *candidate_state,
                        activation=activation,
                        ecm_internal_z=ecm_internal_z,
                        ecm_backend=selected_ecm_backend,
                        reject_penetration=False,
                    )
                    residual_evaluations += 1
                except ValueError:
                    step_length *= 0.5
                    continue
                armijo_bound = (
                    current_evaluation.total_stored_energy
                    + 1.0e-4 * step_length * slope
                )
                if (
                    candidate_evaluation.total_stored_energy <= armijo_bound
                    and candidate_evaluation.minimum_ecm_jacobian >= 0.5
                    and candidate_evaluation.minimum_gap >= -1.0e-12
                ):
                    accepted = True
                    solved_scaled_variables = candidate_scaled
                    break
                step_length *= 0.5
            iteration_history.append(
                {
                    "iteration": iteration,
                    "energy": current_evaluation.total_stored_energy,
                    "kkt": current_kkt,
                    "scaled_gradient_norm": float(
                        np.linalg.norm(current_scaled_gradient)
                    ),
                    "slope": slope,
                    "step_length": step_length,
                    "line_search_iterations": line_search_iteration,
                    "accepted": accepted,
                    "used_gradient_fallback": used_gradient_fallback,
                    "candidate_energy": candidate_evaluation.total_stored_energy,
                }
            )
            solver_iterations = iteration
            if not accepted:
                solver_message = "modified-Newton line search failed"
                break
        final_scaled_residual = scaled_force_residual(solved_scaled_variables)
        solver_evaluations = residual_evaluations
    else:
        if spectral_eigenvalues is None or spectral_eigenvectors is None:
            raise RuntimeError("spectral tangent decomposition is unavailable")
        eigenvalue_magnitudes = np.abs(spectral_eigenvalues)
        positive_magnitudes = eigenvalue_magnitudes[
            eigenvalue_magnitudes > 1.0e-12
        ]
        spectral_floor = max(
            1.0e-8,
            1.0e-6 * float(np.median(positive_magnitudes)),
        )
        regularized_magnitudes = np.maximum(
            eigenvalue_magnitudes,
            spectral_floor,
        )
        spectral_transform = spectral_eigenvectors / np.sqrt(
            regularized_magnitudes
        )[None, :]

        solved_scaled_variables = scaled_initial.copy()
        solver_success = True
        solver_message_parts: list[str] = []
        solver_iterations = 0
        solver_evaluations = 0
        for follower_iteration in range(
            1,
            arguments.maximum_follower_iterations + 1,
        ):
            contact_converged = False
            final_modal_success = False
            final_modal_message = "contact iterations not started"
            for contact_iteration in range(
                1,
                arguments.maximum_contact_iterations + 1,
            ):
                contact_start = solved_scaled_variables.copy()
                multiplier_start = contact_multipliers.copy()
                penalty = arguments.contact_penalty * (
                    arguments.contact_penalty_growth
                    ** (contact_iteration - 1)
                )
                cached_spectral_variables: np.ndarray | None = None
                cached_spectral_value: tuple[float, np.ndarray] | None = None

                def spectral_objective(
                    modal_variables: np.ndarray,
                ) -> tuple[float, np.ndarray]:
                    nonlocal residual_evaluations
                    nonlocal cached_spectral_variables
                    nonlocal cached_spectral_value
                    if (
                        cached_spectral_variables is None
                        or cached_spectral_value is None
                        or not np.array_equal(
                            modal_variables,
                            cached_spectral_variables,
                        )
                    ):
                        scaled_variables = (
                            contact_start
                            + spectral_transform @ modal_variables
                        )
                        physical_variables = (
                            variable_scales * scaled_variables
                        )
                        try:
                            state = unpack_exact_volume_variables(
                                model,
                                coordinates,
                                physical_variables,
                            )
                            evaluation = evaluate_fast_trilayer_state(
                                model,
                                *state,
                                activation=activation,
                                ecm_internal_z=ecm_internal_z,
                                ecm_backend=selected_ecm_backend,
                                reject_penetration=False,
                            )
                        except ValueError:
                            guard_scale = 1.0e6
                            cached_spectral_variables = (
                                modal_variables.copy()
                            )
                            cached_spectral_value = (
                                1.0e6
                                + 0.5
                                * guard_scale
                                * float(
                                    np.dot(modal_variables, modal_variables)
                                ),
                                guard_scale * modal_variables,
                            )
                            return cached_spectral_value
                        residual_evaluations += 1
                        full_gradient = (
                            _full_stored_gradient(evaluation)
                            - frozen_external_force
                        )
                        reduced_gradient = (
                            reduce_gradient_to_exact_volume_manifold(
                                model,
                                coordinates,
                                full_gradient,
                                state[0],
                                state[2],
                            )
                        )
                        gaps, gap_jacobian = trilayer_gap_constraints(
                            model,
                            coordinates,
                            physical_variables,
                        )
                        (
                            contact_energy,
                            contact_gradient,
                            trial_multipliers,
                        ) = augmented_contact_energy_gradient(
                            gaps,
                            gap_jacobian,
                            multiplier_start,
                            penalty,
                        )
                        reduced_gradient += contact_gradient
                        scaled_gradient = variable_scales * reduced_gradient
                        full_coordinates = np.concatenate(
                            (
                                state[0].reshape(-1),
                                state[1].reshape(-1),
                                state[2].reshape(-1),
                            )
                        )
                        potential = (
                            evaluation.total_stored_energy
                            - float(
                                np.dot(
                                    frozen_external_force,
                                    full_coordinates
                                    - coordinates.reference_flat,
                                )
                            )
                            + contact_energy
                        )
                        cached_spectral_variables = modal_variables.copy()
                        cached_spectral_value = (
                            potential,
                            spectral_transform.T @ scaled_gradient,
                        )
                    return cached_spectral_value

                modal_result = minimize(
                    spectral_objective,
                    np.zeros(variable_count, dtype=np.float64),
                    method="L-BFGS-B",
                    jac=True,
                    options={
                        "maxiter": arguments.newton_iterations,
                        "ftol": arguments.optimizer_ftol,
                        "gtol": arguments.optimizer_gtol,
                        "maxls": 50,
                        "maxcor": 60,
                    },
                )
                solved_scaled_variables = (
                    contact_start + spectral_transform @ modal_result.x
                )
                solved_physical_variables = (
                    variable_scales * solved_scaled_variables
                )
                gaps, _ = trilayer_gap_constraints(
                    model,
                    coordinates,
                    solved_physical_variables,
                )
                contact_multipliers = np.maximum(
                    0.0,
                    multiplier_start - penalty * gaps,
                )
                contact_penetration = max(0.0, -float(np.min(gaps)))
                contact_complementarity = float(
                    np.max(np.abs(contact_multipliers * gaps))
                )
                contact_history.append(
                    {
                        "follower_iteration": follower_iteration,
                        "contact_iteration": contact_iteration,
                        "penalty": penalty,
                        "optimizer_success": bool(modal_result.success),
                        "optimizer_message": str(modal_result.message),
                        "optimizer_iterations": int(modal_result.nit),
                        "optimizer_evaluations": int(modal_result.nfev),
                        "minimum_gap": float(np.min(gaps)),
                        "penetration": contact_penetration,
                        "maximum_multiplier": float(
                            np.max(contact_multipliers)
                        ),
                        "complementarity": contact_complementarity,
                    }
                )
                solver_iterations += int(modal_result.nit)
                solver_evaluations += int(modal_result.nfev)
                final_modal_success = bool(modal_result.success)
                final_modal_message = str(modal_result.message)
                if (
                    contact_penetration <= arguments.contact_tolerance
                    and contact_complementarity
                    <= arguments.contact_tolerance
                ):
                    contact_converged = True
                    break
            solved_state = unpack_exact_volume_variables(
                model,
                coordinates,
                variable_scales * solved_scaled_variables,
            )
            updated_external_force = _full_external_force(
                model,
                coordinates,
                solved_state[2],
                pressure=pressure,
                wss_command=wss_command,
            )
            follower_residual = float(
                np.linalg.norm(
                    updated_external_force - frozen_external_force
                )
                / max(
                    1.0,
                    float(np.linalg.norm(updated_external_force)),
                    float(np.linalg.norm(frozen_external_force)),
                )
            )
            follower_history.append(
                {
                    "iteration": follower_iteration,
                    "optimizer_success": final_modal_success,
                    "optimizer_message": final_modal_message,
                    "contact_converged": contact_converged,
                    "follower_residual": follower_residual,
                }
            )
            solver_success = bool(
                solver_success and final_modal_success and contact_converged
            )
            solver_message_parts.append(final_modal_message)
            frozen_external_force = updated_external_force
            if (
                (pressure == 0.0 and np.linalg.norm(wss_command) == 0.0)
                or follower_residual <= arguments.follower_tolerance
            ):
                break
        final_scaled_residual = scaled_force_residual(solved_scaled_variables)
        solver_success = bool(
            solver_success
            and contact_converged
            and follower_residual <= arguments.follower_tolerance
        )
        solver_message = " | ".join(solver_message_parts)
    residual_safeguard_triggered = False
    pre_safeguard_residual_norm = float(
        np.linalg.norm(final_scaled_residual)
    )
    initial_residual_norm = float(np.linalg.norm(initial_residual))
    if arguments.method != "spectral_lbfgs" and (
        not np.isfinite(pre_safeguard_residual_norm)
        or pre_safeguard_residual_norm >= initial_residual_norm
    ):
        solved_scaled_variables = scaled_initial.copy()
        final_scaled_residual = initial_residual.copy()
        residual_safeguard_triggered = True
        solver_success = False
        solver_message = (
            f"{solver_message} | rejected candidate that did not reduce "
            "the scaled residual norm"
        )

    active_contact_ids = np.flatnonzero(contact_multipliers > 1.0e-10)
    for projection_iteration in range(1, 7):
        if len(active_contact_ids) == 0:
            break
        physical_variables = variable_scales * solved_scaled_variables
        gaps, gap_jacobian = trilayer_gap_constraints(
            model,
            coordinates,
            physical_variables,
        )
        active_gaps = gaps[active_contact_ids]
        if float(np.max(np.abs(active_gaps))) <= 1.0e-13:
            break
        active_scaled_jacobian = (
            gap_jacobian[active_contact_ids] * variable_scales[None, :]
        )
        gram = active_scaled_jacobian @ active_scaled_jacobian.T
        correction = -active_scaled_jacobian.T @ np.linalg.lstsq(
            gram,
            active_gaps,
            rcond=1.0e-12,
        )[0]
        step_length = 1.0
        accepted = False
        for _ in range(20):
            candidate_scaled = (
                solved_scaled_variables + step_length * correction
            )
            try:
                candidate_state = unpack_exact_volume_variables(
                    model,
                    coordinates,
                    variable_scales * candidate_scaled,
                )
                candidate_evaluation = evaluate_fast_trilayer_state(
                    model,
                    *candidate_state,
                    activation=activation,
                    ecm_internal_z=ecm_internal_z,
                    ecm_backend=selected_ecm_backend,
                    reject_penetration=False,
                )
            except ValueError:
                step_length *= 0.5
                continue
            candidate_gaps, _ = trilayer_gap_constraints(
                model,
                coordinates,
                variable_scales * candidate_scaled,
            )
            if (
                candidate_evaluation.minimum_ecm_jacobian > 0.5
                and float(
                    np.max(np.abs(candidate_gaps[active_contact_ids]))
                )
                < float(np.max(np.abs(active_gaps)))
            ):
                solved_scaled_variables = candidate_scaled
                accepted = True
                break
            step_length *= 0.5
        contact_projection_history.append(
            {
                "iteration": projection_iteration,
                "active_contact_count": len(active_contact_ids),
                "maximum_active_gap_before": float(
                    np.max(np.abs(active_gaps))
                ),
                "step_length": step_length,
                "accepted": accepted,
            }
        )
        if not accepted:
            break
    if len(active_contact_ids):
        projected_state = unpack_exact_volume_variables(
            model,
            coordinates,
            variable_scales * solved_scaled_variables,
        )
        projected_external_force = _full_external_force(
            model,
            coordinates,
            projected_state[2],
            pressure=pressure,
            wss_command=wss_command,
        )
        projection_follower_residual = float(
            np.linalg.norm(projected_external_force - frozen_external_force)
            / max(
                1.0,
                float(np.linalg.norm(projected_external_force)),
                float(np.linalg.norm(frozen_external_force)),
            )
        )
        follower_residual = max(
            follower_residual,
            projection_follower_residual,
        )
        frozen_external_force = projected_external_force
    final_scaled_residual = scaled_force_residual(solved_scaled_variables)
    solve_seconds = time.perf_counter() - solve_start
    candidate_variables = variable_scales * solved_scaled_variables
    candidate_state = unpack_exact_volume_variables(
        model,
        coordinates,
        candidate_variables,
    )
    final_evaluation = evaluate_fast_trilayer_state(
        model,
        *candidate_state,
        activation=activation,
        pressure=pressure,
        wss_command=wss_command,
        ecm_internal_z=ecm_internal_z,
        ecm_backend=selected_ecm_backend,
        reject_penetration=False,
    )
    external_force = _full_external_force(
        model,
        coordinates,
        candidate_state[2],
        pressure=pressure,
        wss_command=wss_command,
    )
    multipliers, kkt, final_gaps, contact_complementarity = contact_kkt_audit(
        model,
        coordinates,
        final_evaluation,
        candidate_state[0],
        candidate_state[1],
        candidate_state[2],
        external_force,
        contact_multipliers,
    )
    contact_penetration = max(0.0, -float(np.min(final_gaps)))
    active_contact_count = int(
        np.count_nonzero(contact_multipliers > 1.0e-10)
    )
    volume_residual = max(
        abs(final_evaluation.myocyte_volume_ratio - 1.0),
        abs(final_evaluation.endocardial_volume_ratio - 1.0),
    )
    passed = bool(
        kkt <= 1.0e-5
        and follower_residual <= arguments.follower_tolerance
        and contact_penetration <= arguments.contact_tolerance
        and contact_complementarity <= arguments.contact_tolerance
        and float(np.min(contact_multipliers)) >= -1.0e-12
        and volume_residual <= 1.0e-8
        and final_evaluation.minimum_ecm_jacobian >= 0.5
        and final_evaluation.minimum_gap >= -1.0e-12
        and final_evaluation.minimum_myocyte_face_area_ratio >= 0.05
        and final_evaluation.minimum_endocardial_face_area_ratio >= 0.05
    )
    report = {
        "status": (
            "passed_sparse_preconditioner_diagnostic"
            if passed
            else "failed_sparse_preconditioner_diagnostic"
        ),
        "activation": activation,
        "pressure": pressure,
        "wss_command": wss_command.tolist(),
        "dcm_level": model.dcm_level,
        "ecm_level": model.ecm_level,
        "dcm_vertex_count_per_layer": len(model.myocyte.vertices),
        "dcm_face_count_per_layer": len(model.myocyte.faces),
        "ecm_footprint_scale": model.ecm_footprint_scale,
        "ecm_divisions": list(model.ecm_divisions),
        "ecm_vertex_count": len(model.ecm_reference.vertices),
        "ecm_tetrahedron_count": len(model.ecm_reference.tetrahedra),
        "ecm_backend": arguments.ecm_backend,
        "ecm_backend_diagnostics": (
            None
            if fenicsx_backend is None
            else fenicsx_backend.diagnostics()
        ),
        "input_checkpoint": str(input_path),
        "coarse_seconds": coarse_seconds,
        "coarse_kkt": coarse_kkt,
        "coarse_optimizer_evaluations": coarse_optimizer_evaluations,
        "coarse_newton_evaluations": coarse_newton_evaluations,
        "node_color_count": int(node_colors.max()) + 1,
        "dof_color_count": color_count,
        "tangent_nonzeros": int(tangent.nnz),
        "tangent_symmetry_residual_before_symmetrization": symmetry_residual,
        "tangent_assembly_seconds": assembly_seconds,
        "factor_seconds": factor_seconds,
        "factor_attempts": factor_attempts,
        "factor_shift": shift,
        "minimum_tangent_eigenvalue": minimum_tangent_eigenvalue,
        "sparse_spectral_converged": sparse_spectral_converged,
        "dense_minimum_eigenvalue_requested": (
            arguments.dense_minimum_eigenvalue
        ),
        "spectral_seconds": spectral_seconds,
        "spectral_floor": spectral_floor,
        "tangent_vector_audits": tangent_audits,
        "block_scales": block_scales.tolist(),
        "solver_method": arguments.method,
        "newton_success": solver_success,
        "newton_message": solver_message,
        "newton_iterations": solver_iterations,
        "newton_evaluations": solver_evaluations,
        "counted_residual_evaluations": residual_evaluations,
        "newton_seconds": solve_seconds,
        "residual_safeguard_triggered": residual_safeguard_triggered,
        "pre_safeguard_residual_norm": pre_safeguard_residual_norm,
        "follower_tolerance": arguments.follower_tolerance,
        "follower_residual": follower_residual,
        "follower_history": follower_history,
        "contact_tolerance": arguments.contact_tolerance,
        "contact_penalty": arguments.contact_penalty,
        "contact_penalty_growth": arguments.contact_penalty_growth,
        "contact_converged": contact_converged,
        "contact_penetration": contact_penetration,
        "contact_complementarity": contact_complementarity,
        "active_contact_count": active_contact_count,
        "maximum_contact_multiplier": float(
            np.max(contact_multipliers)
        ),
        "contact_history": contact_history,
        "contact_projection_history": contact_projection_history,
        "initial_scaled_residual_norm": float(np.linalg.norm(initial_residual)),
        "initial_scaled_residual_max": float(np.max(np.abs(initial_residual))),
        "final_scaled_residual_norm": float(
            np.linalg.norm(final_scaled_residual)
        ),
        "final_scaled_residual_max": float(
            np.max(np.abs(final_scaled_residual))
        ),
        "scaled_variable_change_norm": float(
            np.linalg.norm(solved_scaled_variables - scaled_initial)
        ),
        "iteration_history": iteration_history,
        "normalized_kkt_residual": kkt,
        "volume_constraint_residual": volume_residual,
        "minimum_ecm_jacobian": final_evaluation.minimum_ecm_jacobian,
        "minimum_gap": final_evaluation.minimum_gap,
        "minimum_myocyte_face_area_ratio": (
            final_evaluation.minimum_myocyte_face_area_ratio
        ),
        "minimum_endocardial_face_area_ratio": (
            final_evaluation.minimum_endocardial_face_area_ratio
        ),
        "passed": passed,
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    np.savez_compressed(
        output_path / f"activation_{round(100 * activation):03d}_state.npz",
        activation=np.asarray(activation),
        variables=candidate_variables,
        myocyte_vertices=candidate_state[0],
        ecm_vertices=candidate_state[1],
        endocardial_vertices=candidate_state[2],
        volume_multipliers=multipliers,
        contact_multipliers=contact_multipliers,
        contact_gaps=final_gaps,
        ecm_internal_z=ecm_internal_z,
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
