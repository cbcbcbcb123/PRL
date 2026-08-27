"""Constrained equilibrium solver for the EFE Node 1 fast trilayer.

Each closed DCM surface has one coordinate eliminated analytically.  The
remaining coordinates therefore parameterize the exact constant-volume
manifold instead of asking a dense optimizer to enforce two equality
constraints.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize, root

from route_h.contact_adhesion import material_tether_gap_and_gradients
from route_h.dcm_cell import surface_volume_and_gradient
from route_h.loads import blood_nodal_force

from .efe_fast_trilayer import (
    ECMEnergyForceBackend,
    FastTrilayerEvaluation,
    FastTrilayerModel,
    FloatArray,
    evaluate_fast_trilayer_state,
)


IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class ExactVolumeCoordinates:
    """Full trilayer coordinates with one dependent scalar per DCM layer."""

    reference_flat: FloatArray
    free_indices: IntArray
    myocyte_dependent_index: int
    endocardial_dependent_index: int
    myocyte_coordinate_count: int
    ecm_coordinate_count: int
    endocardial_coordinate_count: int


@dataclass(frozen=True)
class TrilayerEquilibrium:
    variables: FloatArray
    myocyte_vertices: FloatArray
    ecm_vertices: FloatArray
    endocardial_vertices: FloatArray
    evaluation: FastTrilayerEvaluation
    activation: float
    pressure: float
    wss_command: FloatArray
    optimizer_success: bool
    optimizer_message: str
    optimizer_iterations: int
    optimizer_evaluations: int
    newton_success: bool
    newton_message: str
    newton_iterations: int
    newton_evaluations: int
    follower_iterations: int
    follower_residual: float
    normalized_kkt_residual: float
    volume_constraint_residual: float
    volume_multipliers: FloatArray
    preconditioner_block_scales: FloatArray
    mechanical_converged: bool


def build_exact_volume_coordinates(
    model: FastTrilayerModel,
) -> ExactVolumeCoordinates:
    blocks = (
        model.myocyte.vertices.reshape(-1),
        model.ecm_reference.vertices.reshape(-1),
        model.endocardium.vertices.reshape(-1),
    )
    reference_flat = np.concatenate(blocks)
    _, myocyte_volume_gradient = surface_volume_and_gradient(
        model.myocyte.vertices,
        model.myocyte.faces,
    )
    _, endocardial_volume_gradient = surface_volume_and_gradient(
        model.endocardium.vertices,
        model.endocardium.faces,
    )
    myocyte_coordinate_count = model.myocyte.vertices.size
    ecm_coordinate_count = model.ecm_reference.vertices.size
    endocardial_coordinate_count = model.endocardium.vertices.size
    myocyte_dependent_index = int(
        np.argmax(np.abs(myocyte_volume_gradient.reshape(-1)))
    )
    endocardial_offset = myocyte_coordinate_count + ecm_coordinate_count
    endocardial_dependent_index = endocardial_offset + int(
        np.argmax(np.abs(endocardial_volume_gradient.reshape(-1)))
    )
    free_mask = np.ones(len(reference_flat), dtype=np.bool_)
    free_mask[myocyte_dependent_index] = False
    free_mask[endocardial_dependent_index] = False
    return ExactVolumeCoordinates(
        reference_flat=reference_flat,
        free_indices=np.flatnonzero(free_mask).astype(np.int64),
        myocyte_dependent_index=myocyte_dependent_index,
        endocardial_dependent_index=endocardial_dependent_index,
        myocyte_coordinate_count=myocyte_coordinate_count,
        ecm_coordinate_count=ecm_coordinate_count,
        endocardial_coordinate_count=endocardial_coordinate_count,
    )


def _restore_dependent_coordinate(
    flat_coordinates: FloatArray,
    *,
    block_start: int,
    vertex_count: int,
    faces: IntArray,
    target_volume: float,
    dependent_index: int,
) -> FloatArray:
    block_end = block_start + 3 * vertex_count
    vertices = flat_coordinates[block_start:block_end].reshape(vertex_count, 3)
    local_index = dependent_index - block_start
    scalar_view = vertices.reshape(-1)
    scalar_view[local_index] = 0.0
    volume_at_zero, _ = surface_volume_and_gradient(vertices, faces)
    scalar_view[local_index] = 1.0
    volume_at_one, _ = surface_volume_and_gradient(vertices, faces)
    coefficient = volume_at_one - volume_at_zero
    if abs(coefficient) <= 1.0e-12:
        raise ValueError("dependent coordinate lost volume sensitivity")
    scalar_view[local_index] = (target_volume - volume_at_zero) / coefficient
    return vertices


def unpack_exact_volume_variables(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    variables: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    if variables.shape != (len(coordinates.free_indices),):
        raise ValueError("invalid reduced trilayer variable shape")
    flat = coordinates.reference_flat.copy()
    flat[coordinates.free_indices] += variables
    myocyte_vertices = _restore_dependent_coordinate(
        flat,
        block_start=0,
        vertex_count=len(model.myocyte.vertices),
        faces=model.myocyte.faces,
        target_volume=model.myocyte.cell.volume0,
        dependent_index=coordinates.myocyte_dependent_index,
    )
    ecm_start = coordinates.myocyte_coordinate_count
    ecm_end = ecm_start + coordinates.ecm_coordinate_count
    ecm_vertices = flat[ecm_start:ecm_end].reshape(
        model.ecm_reference.vertices.shape
    )
    endocardial_vertices = _restore_dependent_coordinate(
        flat,
        block_start=ecm_end,
        vertex_count=len(model.endocardium.vertices),
        faces=model.endocardium.faces,
        target_volume=model.endocardium.cell.volume0,
        dependent_index=coordinates.endocardial_dependent_index,
    )
    return myocyte_vertices, ecm_vertices, endocardial_vertices


def _volume_constraint_gradients(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    myocyte_vertices: FloatArray,
    endocardial_vertices: FloatArray,
) -> FloatArray:
    full_coordinate_count = len(coordinates.reference_flat)
    gradients = np.zeros((2, full_coordinate_count), dtype=np.float64)
    _, myocyte_gradient = surface_volume_and_gradient(
        myocyte_vertices,
        model.myocyte.faces,
    )
    _, endocardial_gradient = surface_volume_and_gradient(
        endocardial_vertices,
        model.endocardium.faces,
    )
    gradients[0, : coordinates.myocyte_coordinate_count] = (
        myocyte_gradient.reshape(-1) / model.myocyte.cell.volume0
    )
    endocardial_start = (
        coordinates.myocyte_coordinate_count + coordinates.ecm_coordinate_count
    )
    gradients[1, endocardial_start:] = (
        endocardial_gradient.reshape(-1) / model.endocardium.cell.volume0
    )
    return gradients


def reduce_gradient_to_exact_volume_manifold(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    full_gradient: FloatArray,
    myocyte_vertices: FloatArray,
    endocardial_vertices: FloatArray,
) -> FloatArray:
    if full_gradient.shape != coordinates.reference_flat.shape:
        raise ValueError("invalid full trilayer gradient shape")
    constraint_gradients = _volume_constraint_gradients(
        model,
        coordinates,
        myocyte_vertices,
        endocardial_vertices,
    )
    projected = full_gradient.copy()
    for row, dependent_index in enumerate(
        (
            coordinates.myocyte_dependent_index,
            coordinates.endocardial_dependent_index,
        )
    ):
        pivot = constraint_gradients[row, dependent_index]
        if abs(pivot) <= 1.0e-12:
            raise ValueError("dependent coordinate has singular volume tangent")
        projected -= (
            full_gradient[dependent_index]
            / pivot
            * constraint_gradients[row]
        )
    return projected[coordinates.free_indices]


def trilayer_gap_values_and_full_gradients(
    model: FastTrilayerModel,
    myocyte_vertices: FloatArray,
    ecm_vertices: FloatArray,
    endocardial_vertices: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    """Evaluate both DCM--FEM interface gaps and full-coordinate Jacobian."""
    full_coordinate_count = (
        myocyte_vertices.size + ecm_vertices.size + endocardial_vertices.size
    )
    interface_specs = (
        (
            model.myocyte_interface,
            model.myocyte.faces,
            myocyte_vertices,
            0,
        ),
        (
            model.endocardial_interface,
            model.endocardium.faces,
            endocardial_vertices,
            myocyte_vertices.size + ecm_vertices.size,
        ),
    )
    tether_count = sum(len(interface.tethers) for interface, *_ in interface_specs)
    gaps = np.empty(tether_count, dtype=np.float64)
    jacobian = np.zeros(
        (tether_count, full_coordinate_count),
        dtype=np.float64,
    )
    ecm_offset = myocyte_vertices.size
    tether_index = 0
    for interface, cell_faces, cell_vertices, cell_offset in interface_specs:
        row_by_id = {
            int(point_id): row
            for row, point_id in enumerate(interface.registry.point_ids)
        }
        for tether in interface.tethers:
            row = row_by_id[tether.material_point_id]
            cell_face = cell_faces[int(interface.registry.face_ids[row])]
            ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
            gap, cell_local, ecm_local = material_tether_gap_and_gradients(
                cell_vertices,
                cell_face,
                ecm_vertices,
                ecm_face,
                master_barycentric=interface.registry.barycentric[row],
                slave_barycentric=tether.ecm_barycentric,
                normal_orientation_sign=tether.normal_orientation_sign,
            )
            gaps[tether_index] = gap
            for local_id, vertex_id in enumerate(cell_face):
                start = cell_offset + 3 * int(vertex_id)
                jacobian[tether_index, start : start + 3] += cell_local[local_id]
            for local_id, vertex_id in enumerate(ecm_face):
                start = ecm_offset + 3 * int(vertex_id)
                jacobian[tether_index, start : start + 3] += ecm_local[local_id]
            tether_index += 1
    return gaps, jacobian


def trilayer_gap_constraints(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    variables: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    """Return ``gap >= 0`` values and Jacobian on the exact-volume manifold."""
    myocyte, ecm, endocardium = unpack_exact_volume_variables(
        model,
        coordinates,
        variables,
    )
    gaps, full_jacobian = trilayer_gap_values_and_full_gradients(
        model,
        myocyte,
        ecm,
        endocardium,
    )
    constraint_gradients = _volume_constraint_gradients(
        model,
        coordinates,
        myocyte,
        endocardium,
    )
    projected = full_jacobian.copy()
    for row, dependent_index in enumerate(
        (
            coordinates.myocyte_dependent_index,
            coordinates.endocardial_dependent_index,
        )
    ):
        pivot = constraint_gradients[row, dependent_index]
        if abs(pivot) <= 1.0e-12:
            raise ValueError("dependent coordinate has singular volume tangent")
        projected -= (
            full_jacobian[:, dependent_index, None]
            / pivot
            * constraint_gradients[row][None, :]
        )
    return gaps, projected[:, coordinates.free_indices]


def augmented_contact_energy_gradient(
    gaps: FloatArray,
    gap_jacobian: FloatArray,
    multipliers: FloatArray,
    penalty: float,
) -> tuple[float, FloatArray, FloatArray]:
    """Powell--Hestenes--Rockafellar term for ``gap >= 0`` contact."""
    if penalty <= 0.0:
        raise ValueError("contact penalty must be positive")
    if gaps.shape != multipliers.shape:
        raise ValueError("contact multiplier shape does not match gaps")
    if gap_jacobian.shape[0] != len(gaps):
        raise ValueError("contact Jacobian row count does not match gaps")
    trial_multipliers = np.maximum(0.0, multipliers - penalty * gaps)
    energy = float(
        (
            np.dot(trial_multipliers, trial_multipliers)
            - np.dot(multipliers, multipliers)
        )
        / (2.0 * penalty)
    )
    gradient = -(gap_jacobian.T @ trial_multipliers)
    return energy, gradient, trial_multipliers


def _full_stored_gradient(evaluation: FastTrilayerEvaluation) -> FloatArray:
    return np.concatenate(
        (
            evaluation.myocyte_energy_gradient.reshape(-1),
            evaluation.ecm_energy_gradient.reshape(-1),
            evaluation.endocardial_energy_gradient.reshape(-1),
        )
    )


def _full_external_force(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    endocardial_vertices: FloatArray,
    *,
    pressure: float,
    wss_command: FloatArray,
) -> FloatArray:
    pressure_force, wss_force = blood_nodal_force(
        endocardial_vertices,
        model.endocardium.faces,
        model.endocardial_lumen_face_ids,
        pressure=pressure,
        wss_command=wss_command,
    )
    force = np.zeros_like(coordinates.reference_flat)
    endocardial_start = (
        coordinates.myocyte_coordinate_count + coordinates.ecm_coordinate_count
    )
    force[endocardial_start:] = (pressure_force + wss_force).reshape(-1)
    return force


def _kkt_audit(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    evaluation: FastTrilayerEvaluation,
    myocyte_vertices: FloatArray,
    endocardial_vertices: FloatArray,
    external_force: FloatArray,
) -> tuple[FloatArray, float]:
    gradient = _full_stored_gradient(evaluation) - external_force
    constraint_gradients = _volume_constraint_gradients(
        model,
        coordinates,
        myocyte_vertices,
        endocardial_vertices,
    )
    multipliers = np.linalg.lstsq(
        constraint_gradients.T,
        -gradient,
        rcond=None,
    )[0]
    multiplier_force = constraint_gradients.T @ multipliers
    residual = gradient + multiplier_force
    normalized = float(
        np.linalg.norm(residual)
        / max(
            1.0,
            float(np.linalg.norm(gradient)),
            float(np.linalg.norm(multiplier_force)),
        )
    )
    return multipliers, normalized


def contact_kkt_audit(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    evaluation: FastTrilayerEvaluation,
    myocyte_vertices: FloatArray,
    ecm_vertices: FloatArray,
    endocardial_vertices: FloatArray,
    external_force: FloatArray,
    contact_multipliers: FloatArray,
) -> tuple[FloatArray, float, FloatArray, float]:
    """Audit volume equality and unilateral-contact KKT conditions."""
    gaps, gap_jacobian = trilayer_gap_values_and_full_gradients(
        model,
        myocyte_vertices,
        ecm_vertices,
        endocardial_vertices,
    )
    if contact_multipliers.shape != gaps.shape:
        raise ValueError("contact multiplier shape does not match tether gaps")
    gradient = (
        _full_stored_gradient(evaluation)
        - external_force
        - gap_jacobian.T @ contact_multipliers
    )
    constraint_gradients = _volume_constraint_gradients(
        model,
        coordinates,
        myocyte_vertices,
        endocardial_vertices,
    )
    volume_multipliers = np.linalg.lstsq(
        constraint_gradients.T,
        -gradient,
        rcond=None,
    )[0]
    volume_force = constraint_gradients.T @ volume_multipliers
    residual = gradient + volume_force
    normalized = float(
        np.linalg.norm(residual)
        / max(
            1.0,
            float(np.linalg.norm(gradient)),
            float(np.linalg.norm(volume_force)),
        )
    )
    complementarity = (
        float(np.max(np.abs(contact_multipliers * gaps)))
        if len(gaps)
        else 0.0
    )
    return volume_multipliers, normalized, gaps, complementarity


def _diagonal_preconditioner(
    model: FastTrilayerModel,
    coordinates: ExactVolumeCoordinates,
    *,
    ecm_backend: ECMEnergyForceBackend | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Estimate deterministic diagonal scales with matrix-free Hessian probes."""
    free_indices = coordinates.free_indices
    myocyte_end = coordinates.myocyte_coordinate_count
    ecm_end = myocyte_end + coordinates.ecm_coordinate_count
    masks = (
        free_indices < myocyte_end,
        (free_indices >= myocyte_end) & (free_indices < ecm_end),
        free_indices >= ecm_end,
    )
    reference_variables = np.zeros(len(free_indices), dtype=np.float64)
    reference_state = unpack_exact_volume_variables(
        model,
        coordinates,
        reference_variables,
    )
    reference_evaluation = evaluate_fast_trilayer_state(
        model,
        *reference_state,
        ecm_backend=ecm_backend,
        reject_penetration=False,
    )
    reference_full_gradient = _full_stored_gradient(reference_evaluation)
    reference_reduced_gradient = reduce_gradient_to_exact_volume_manifold(
        model,
        coordinates,
        reference_full_gradient,
        reference_state[0],
        reference_state[2],
    )
    diagonal = np.zeros(len(free_indices), dtype=np.float64)
    rng = np.random.default_rng(20260817)
    perturbation = 2.0e-6
    probe_count = 8
    for _ in range(probe_count):
        direction = rng.choice(
            np.asarray([-1.0, 1.0], dtype=np.float64),
            size=len(free_indices),
        )
        variables = perturbation * direction
        state = unpack_exact_volume_variables(model, coordinates, variables)
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            ecm_backend=ecm_backend,
            reject_penetration=False,
        )
        full_gradient = _full_stored_gradient(evaluation)
        reduced_gradient = reduce_gradient_to_exact_volume_manifold(
            model,
            coordinates,
            full_gradient,
            state[0],
            state[2],
        )
        hessian_product = (
            reduced_gradient - reference_reduced_gradient
        ) / perturbation
        diagonal += direction * hessian_product
    diagonal = np.abs(diagonal / probe_count)
    positive = diagonal[diagonal > 1.0e-10]
    if len(positive) == 0:
        return np.ones(len(free_indices)), np.ones(3)
    lower = float(np.percentile(positive, 5.0))
    upper = float(np.percentile(positive, 95.0))
    regularized = np.clip(diagonal, max(1.0e-8, lower), upper)
    target = float(np.exp(np.mean(np.log(regularized))))
    variable_scales = np.sqrt(target / regularized)
    variable_scales = np.clip(variable_scales, 0.1, 10.0)
    block_scales = np.asarray(
        [
            float(np.median(variable_scales[mask]))
            for mask in masks
        ],
        dtype=np.float64,
    )
    return variable_scales, block_scales


def solve_fast_trilayer_equilibrium(
    model: FastTrilayerModel,
    *,
    initial_variables: FloatArray | None = None,
    activation: float = 0.0,
    pressure: float = 0.0,
    wss_command: FloatArray | None = None,
    ecm_internal_z: FloatArray | None = None,
    ecm_backend: ECMEnergyForceBackend | None = None,
    maximum_iterations: int = 120,
    maximum_newton_iterations: int = 20,
    maximum_follower_iterations: int = 5,
    follower_tolerance: float = 1.0e-7,
    displacement_bound: float = 0.15,
) -> TrilayerEquilibrium:
    """Solve one load state with exact DCM volumes and follower blood loads."""
    if (
        maximum_iterations < 1
        or maximum_newton_iterations < 0
        or maximum_follower_iterations < 1
    ):
        raise ValueError(
            "optimizer/follower limits must be positive and Newton limit "
            "must be nonnegative"
        )
    if follower_tolerance <= 0.0 or displacement_bound <= 0.0:
        raise ValueError("solver tolerances and bounds must be positive")
    selected_wss = (
        np.zeros(3, dtype=np.float64)
        if wss_command is None
        else np.asarray(wss_command, dtype=np.float64)
    )
    if selected_wss.shape != (3,):
        raise ValueError("WSS command must have shape (3,)")

    coordinates = build_exact_volume_coordinates(model)
    variables = (
        np.zeros(len(coordinates.free_indices), dtype=np.float64)
        if initial_variables is None
        else np.asarray(initial_variables, dtype=np.float64).copy()
    )
    if variables.shape != (len(coordinates.free_indices),):
        raise ValueError("invalid initial trilayer variable shape")
    variable_scales, block_scales = _diagonal_preconditioner(
        model, coordinates, ecm_backend=ecm_backend
    )

    _, _, initial_endocardium = unpack_exact_volume_variables(
        model,
        coordinates,
        variables,
    )
    frozen_external_force = _full_external_force(
        model,
        coordinates,
        initial_endocardium,
        pressure=pressure,
        wss_command=selected_wss,
    )
    optimizer_success = False
    optimizer_message = "not_started"
    optimizer_iterations = 0
    optimizer_evaluations = 0
    newton_success = False
    newton_message = "not_started"
    newton_iterations = 0
    newton_evaluations = 0
    follower_residual = 0.0
    follower_iteration = 0

    for follower_iteration in range(1, maximum_follower_iterations + 1):
        cached_variables: FloatArray | None = None
        cached_state: tuple[
            FloatArray,
            FloatArray,
            FloatArray,
            FastTrilayerEvaluation,
        ] | None = None

        def cached(
            current: FloatArray,
        ) -> tuple[FloatArray, FloatArray, FloatArray, FastTrilayerEvaluation]:
            nonlocal cached_variables, cached_state
            if (
                cached_variables is None
                or cached_state is None
                or not np.array_equal(current, cached_variables)
            ):
                myocyte_vertices, ecm_vertices, endocardial_vertices = (
                    unpack_exact_volume_variables(model, coordinates, current)
                )
                evaluation = evaluate_fast_trilayer_state(
                    model,
                    myocyte_vertices,
                    ecm_vertices,
                    endocardial_vertices,
                    activation=activation,
                    ecm_internal_z=ecm_internal_z,
                    ecm_backend=ecm_backend,
                    reject_penetration=False,
                )
                cached_variables = np.asarray(current, dtype=np.float64).copy()
                cached_state = (
                    myocyte_vertices,
                    ecm_vertices,
                    endocardial_vertices,
                    evaluation,
                )
            return cached_state

        def objective(current: FloatArray) -> tuple[float, FloatArray]:
            myocyte_vertices, _, endocardial_vertices, evaluation = cached(
                current
            )
            displacement = np.zeros_like(coordinates.reference_flat)
            displacement[coordinates.free_indices] = current
            endocardial_start = (
                coordinates.myocyte_coordinate_count
                + coordinates.ecm_coordinate_count
            )
            displacement[endocardial_start:] = (
                endocardial_vertices - model.endocardium.vertices
            ).reshape(-1)
            potential = evaluation.total_stored_energy - float(
                np.dot(frozen_external_force, displacement)
            )
            full_gradient = (
                _full_stored_gradient(evaluation) - frozen_external_force
            )
            reduced_gradient = reduce_gradient_to_exact_volume_manifold(
                model,
                coordinates,
                full_gradient,
                myocyte_vertices,
                endocardial_vertices,
            )
            return float(potential), reduced_gradient

        scaled_initial = variables / variable_scales

        def scaled_objective(current: FloatArray) -> tuple[float, FloatArray]:
            energy, gradient = objective(variable_scales * current)
            return energy, variable_scales * gradient

        result = minimize(
            scaled_objective,
            scaled_initial,
            method="L-BFGS-B",
            jac=True,
            bounds=[
                (-displacement_bound / scale, displacement_bound / scale)
                for scale in variable_scales
            ],
            options={
                "maxiter": maximum_iterations,
                "ftol": 1.0e-14,
                "gtol": 2.0e-7,
                "maxls": 40,
                "maxcor": 60,
            },
        )
        variables = variable_scales * np.asarray(result.x, dtype=np.float64)
        optimizer_success = bool(result.success)
        optimizer_message = str(result.message)
        optimizer_iterations += int(result.nit)
        optimizer_evaluations += int(result.nfev)

        def scaled_force_residual(current: FloatArray) -> FloatArray:
            physical_variables = variable_scales * current
            (
                myocyte_vertices,
                _,
                endocardial_vertices,
                evaluation,
            ) = cached(physical_variables)
            full_gradient = (
                _full_stored_gradient(evaluation) - frozen_external_force
            )
            return variable_scales * reduce_gradient_to_exact_volume_manifold(
                model,
                coordinates,
                full_gradient,
                myocyte_vertices,
                endocardial_vertices,
            )

        scaled_variables = variables / variable_scales
        initial_force_residual = scaled_force_residual(scaled_variables)
        if float(np.max(np.abs(initial_force_residual))) <= 1.0e-7:
            newton_success = True
            newton_message = "coarse_solution_already_below_force_tolerance"
        elif maximum_newton_iterations == 0:
            newton_success = False
            newton_message = "Newton refinement explicitly skipped"
        else:
            newton_result = root(
                scaled_force_residual,
                scaled_variables,
                method="krylov",
                options={
                    "maxiter": maximum_newton_iterations,
                    "fatol": 1.0e-7,
                    "jac_options": {
                        "inner_maxiter": 30,
                        "inner_M": result.hess_inv,
                    },
                },
            )
            candidate_variables = (
                variable_scales
                * np.asarray(newton_result.x, dtype=np.float64)
            )
            candidate_residual = np.asarray(
                newton_result.fun,
                dtype=np.float64,
            )
            if (
                np.linalg.norm(candidate_residual)
                < np.linalg.norm(initial_force_residual)
                and np.max(np.abs(candidate_variables))
                <= displacement_bound * (1.0 + 1.0e-10)
            ):
                variables = candidate_variables
            newton_success = bool(newton_result.success)
            newton_message = str(newton_result.message)
            newton_iterations += int(newton_result.nit)
            newton_evaluations += int(newton_result.nfev)
        _, _, endocardial_vertices, _ = cached(variables)
        updated_external_force = _full_external_force(
            model,
            coordinates,
            endocardial_vertices,
            pressure=pressure,
            wss_command=selected_wss,
        )
        follower_residual = float(
            np.linalg.norm(updated_external_force - frozen_external_force)
            / max(
                1.0,
                float(np.linalg.norm(updated_external_force)),
                float(np.linalg.norm(frozen_external_force)),
            )
        )
        frozen_external_force = updated_external_force
        if (
            (pressure == 0.0 and np.linalg.norm(selected_wss) == 0.0)
            or follower_residual <= follower_tolerance
        ):
            break

    myocyte_vertices, ecm_vertices, endocardial_vertices = (
        unpack_exact_volume_variables(model, coordinates, variables)
    )
    evaluation = evaluate_fast_trilayer_state(
        model,
        myocyte_vertices,
        ecm_vertices,
        endocardial_vertices,
        activation=activation,
        pressure=pressure,
        wss_command=selected_wss,
        ecm_internal_z=ecm_internal_z,
        ecm_backend=ecm_backend,
        reject_penetration=False,
    )
    final_external_force = _full_external_force(
        model,
        coordinates,
        endocardial_vertices,
        pressure=pressure,
        wss_command=selected_wss,
    )
    multipliers, normalized_kkt_residual = _kkt_audit(
        model,
        coordinates,
        evaluation,
        myocyte_vertices,
        endocardial_vertices,
        final_external_force,
    )
    volume_constraint_residual = max(
        abs(evaluation.myocyte_volume_ratio - 1.0),
        abs(evaluation.endocardial_volume_ratio - 1.0),
    )
    mechanical_converged = bool(
        np.isfinite(normalized_kkt_residual)
        and normalized_kkt_residual <= 1.0e-5
        and volume_constraint_residual <= 1.0e-8
        and follower_residual <= follower_tolerance
    )
    return TrilayerEquilibrium(
        variables=variables,
        myocyte_vertices=myocyte_vertices,
        ecm_vertices=ecm_vertices,
        endocardial_vertices=endocardial_vertices,
        evaluation=evaluation,
        activation=float(activation),
        pressure=float(pressure),
        wss_command=selected_wss.copy(),
        optimizer_success=optimizer_success,
        optimizer_message=optimizer_message,
        optimizer_iterations=optimizer_iterations,
        optimizer_evaluations=optimizer_evaluations,
        newton_success=newton_success,
        newton_message=newton_message,
        newton_iterations=newton_iterations,
        newton_evaluations=newton_evaluations,
        follower_iterations=follower_iteration,
        follower_residual=follower_residual,
        normalized_kkt_residual=normalized_kkt_residual,
        volume_constraint_residual=float(volume_constraint_residual),
        volume_multipliers=multipliers,
        preconditioner_block_scales=block_scales,
        mechanical_converged=mechanical_converged,
    )
