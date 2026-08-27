"""Single-cycle active DCM cell coupled to finite-strain viscoelastic ECM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from route_h.distributed_active_dynamics import smooth_periodic_activation
from route_h.ecm_finite_strain import (
    deformation_gradient,
    relax_internal_variable_exact,
)

from .fixed_topology_active_cell_ecm import (
    FixedTopologyModel,
    FixedTopologySample,
    StateEvaluation,
    _sample_from_evaluation,
    evaluate_variables,
    gap_constraints,
    initial_variables,
    sample_passes,
)


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ViscoelasticCycleSample:
    step_index: int
    time: float
    activation: float
    activation_rate: float
    mechanical: FixedTopologySample
    ecm_internal_z: FloatArray
    ecm_internal_z_norm: float
    ecm_equilibrium_energy: float
    ecm_viscoelastic_energy: float
    ecm_dissipation_step: float
    cumulative_ecm_dissipation: float
    coupling_iterations: int
    coupling_residual: float


@dataclass(frozen=True)
class ViscoelasticCycleRun:
    status: str
    model: FixedTopologyModel
    period: float
    steps_per_cycle: int
    peak_activation: float
    relaxation_time: float
    deborah_number: float
    coupling_tolerance: float
    samples: tuple[ViscoelasticCycleSample, ...]


@dataclass(frozen=True)
class _EquilibriumResult:
    variables: FloatArray
    evaluation: StateEvaluation
    mechanical: FixedTopologySample


def _solve_equilibrium(
    model: FixedTopologyModel,
    variables: FloatArray,
    *,
    activation: float,
    ecm_internal_z: FloatArray,
    max_iterations: int,
) -> _EquilibriumResult:
    cached_variables: FloatArray | None = None
    cached_evaluation: StateEvaluation | None = None
    cached_gap_variables: FloatArray | None = None
    cached_gaps: FloatArray | None = None
    cached_gap_jacobian: FloatArray | None = None

    def cached(current: FloatArray) -> StateEvaluation:
        nonlocal cached_variables, cached_evaluation
        if (
            cached_variables is None
            or cached_evaluation is None
            or not np.array_equal(current, cached_variables)
        ):
            cached_variables = np.asarray(current, dtype=np.float64).copy()
            cached_evaluation = evaluate_variables(
                model,
                cached_variables,
                activation=activation,
                ecm_internal_z=ecm_internal_z,
            )
        return cached_evaluation

    def cached_gap(current: FloatArray) -> tuple[FloatArray, FloatArray]:
        nonlocal cached_gap_variables, cached_gaps, cached_gap_jacobian
        if (
            cached_gap_variables is None
            or cached_gaps is None
            or cached_gap_jacobian is None
            or not np.array_equal(current, cached_gap_variables)
        ):
            cached(current)
            cached_gap_variables = np.asarray(current, dtype=np.float64).copy()
            cached_gaps, cached_gap_jacobian = gap_constraints(model, current)
        return cached_gaps, cached_gap_jacobian

    def objective(current: FloatArray) -> tuple[float, FloatArray]:
        evaluation = cached(current)
        return evaluation.total_energy, evaluation.variable_gradient

    def volume_constraint(current: FloatArray) -> tuple[float, FloatArray]:
        evaluation = cached(current)
        return (
            evaluation.volume_ratio - 1.0,
            evaluation.volume_constraint_gradient,
        )

    result = minimize(
        objective,
        np.asarray(variables, dtype=np.float64),
        method="SLSQP",
        jac=True,
        constraints=(
            {
                "type": "eq",
                "fun": lambda current: volume_constraint(current)[0],
                "jac": lambda current: volume_constraint(current)[1],
            },
            {
                "type": "ineq",
                "fun": lambda current: cached_gap(current)[0],
                "jac": lambda current: cached_gap(current)[1],
            },
        ),
        bounds=[(-0.15, 0.15)] * len(variables),
        options={
            "maxiter": max_iterations,
            "ftol": 1.0e-12,
            "disp": False,
        },
    )
    solved_variables = np.asarray(result.x, dtype=np.float64)
    evaluation = evaluate_variables(
        model,
        solved_variables,
        activation=activation,
        ecm_internal_z=ecm_internal_z,
    )
    mechanical = _sample_from_evaluation(
        model,
        evaluation,
        solved_variables,
        activation=activation,
        optimizer_success=bool(result.success),
        optimizer_message=str(result.message),
        optimizer_iterations=int(result.nit),
        optimizer_evaluations=int(result.nfev),
    )
    return _EquilibriumResult(
        variables=solved_variables,
        evaluation=evaluation,
        mechanical=mechanical,
    )


def update_ecm_internal_state(
    model: FixedTopologyModel,
    ecm_vertices: FloatArray,
    previous_internal_z: FloatArray,
    time_step: float,
) -> tuple[FloatArray, float]:
    """Return exact branch relaxation at fixed end-step deformation.

    The returned dissipation is a nonnegative discrete proxy
    ``dt * integral eta ||Delta Z / dt||^2 dV0``. It is intentionally not
    presented as a closed energy balance for the staggered scheme.
    """
    if not np.isfinite(time_step) or time_step <= 0.0:
        raise ValueError("time step must be finite and positive")
    reference = model.vertical_slice.ecm_reference
    expected_shape = (len(reference.tetrahedra), 3, 3)
    if previous_internal_z.shape != expected_shape:
        raise ValueError("invalid ECM internal-variable shape")
    updated = np.empty_like(previous_internal_z)
    dissipation = 0.0
    for tetrahedron_id, tetrahedron in enumerate(reference.tetrahedra):
        deformation = deformation_gradient(
            ecm_vertices[tetrahedron],
            reference.dm_inverse[tetrahedron_id],
        )
        updated[tetrahedron_id] = relax_internal_variable_exact(
            deformation,
            previous_internal_z[tetrahedron_id],
            time_step,
            mu_ve=model.vertical_slice.mu_ve,
            eta_ve=model.vertical_slice.eta_ve,
        )
        discrete_rate = (
            updated[tetrahedron_id] - previous_internal_z[tetrahedron_id]
        ) / time_step
        dissipation += (
            time_step
            * reference.volume0[tetrahedron_id]
            * model.vertical_slice.eta_ve
            * float(np.sum(discrete_rate * discrete_rate))
        )
    return updated, float(dissipation)


def _relative_internal_residual(candidate: FloatArray, guess: FloatArray) -> float:
    return float(
        np.linalg.norm(candidate - guess)
        / max(1.0e-12, float(np.linalg.norm(candidate)), float(np.linalg.norm(guess)))
    )


def run_viscoelastic_cell_ecm_cycle(
    model: FixedTopologyModel,
    *,
    period: float = 1.0,
    steps_per_cycle: int = 12,
    peak_activation: float = 0.20,
    coupling_tolerance: float = 5.0e-4,
    maximum_coupling_iterations: int = 6,
    max_optimizer_iterations: int = 1000,
    progress_callback: Callable[[ViscoelasticCycleSample], None] | None = None,
) -> ViscoelasticCycleRun:
    """Run one 0 -> peak -> 0 cycle with staggered implicit ECM memory."""
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and positive")
    if steps_per_cycle < 4 or steps_per_cycle % 2:
        raise ValueError("steps per cycle must be even and at least four")
    if not np.isfinite(peak_activation) or not 0.0 < peak_activation < 1.0:
        raise ValueError("peak activation must lie strictly inside (0,1)")
    if model.vertical_slice.mu_ve <= 0.0:
        raise ValueError("viscoelastic cycle requires positive ECM mu_ve")
    if not np.isfinite(coupling_tolerance) or coupling_tolerance <= 0.0:
        raise ValueError("coupling tolerance must be finite and positive")
    if maximum_coupling_iterations < 1:
        raise ValueError("maximum coupling iterations must be positive")

    reference = model.vertical_slice.ecm_reference
    internal_z = np.zeros((len(reference.tetrahedra), 3, 3), dtype=np.float64)
    variables = initial_variables(model)
    time_step = period / steps_per_cycle
    relaxation_time = 2.0 * model.vertical_slice.eta_ve / model.vertical_slice.mu_ve
    samples: list[ViscoelasticCycleSample] = []
    cumulative_dissipation = 0.0

    initial_evaluation = evaluate_variables(
        model,
        variables,
        activation=0.0,
        ecm_internal_z=internal_z,
    )
    initial_mechanical = _sample_from_evaluation(
        model,
        initial_evaluation,
        variables,
        activation=0.0,
        optimizer_success=True,
        optimizer_message="reference_state",
        optimizer_iterations=0,
        optimizer_evaluations=1,
    )
    initial_sample = ViscoelasticCycleSample(
            step_index=0,
            time=0.0,
            activation=0.0,
            activation_rate=0.0,
            mechanical=initial_mechanical,
            ecm_internal_z=internal_z.copy(),
            ecm_internal_z_norm=0.0,
            ecm_equilibrium_energy=float(
                initial_evaluation.energy_components["ecm_equilibrium"]
            ),
            ecm_viscoelastic_energy=float(
                initial_evaluation.energy_components["ecm_viscoelastic"]
            ),
            ecm_dissipation_step=0.0,
            cumulative_ecm_dissipation=0.0,
            coupling_iterations=0,
            coupling_residual=0.0,
    )
    samples.append(initial_sample)
    if progress_callback is not None:
        progress_callback(initial_sample)

    status = "completed_route_connection_pilot"
    for step_index in range(1, steps_per_cycle + 1):
        time = step_index * time_step
        activation, activation_rate = smooth_periodic_activation(
            time,
            period=period,
            peak_activation=peak_activation,
        )
        previous_internal_z = internal_z.copy()
        internal_guess = previous_internal_z.copy()
        coupling_residual = float("inf")
        equilibrium: _EquilibriumResult | None = None
        internal_candidate = previous_internal_z.copy()
        for coupling_iteration in range(1, maximum_coupling_iterations + 1):
            equilibrium = _solve_equilibrium(
                model,
                variables,
                activation=activation,
                ecm_internal_z=internal_guess,
                max_iterations=max_optimizer_iterations,
            )
            variables = equilibrium.variables
            internal_candidate, _ = update_ecm_internal_state(
                model,
                equilibrium.evaluation.ecm_vertices,
                previous_internal_z,
                time_step,
            )
            coupling_residual = _relative_internal_residual(
                internal_candidate,
                internal_guess,
            )
            internal_guess = internal_candidate
            if coupling_residual <= coupling_tolerance:
                break
        if equilibrium is None:
            raise RuntimeError("viscoelastic equilibrium loop did not execute")

        internal_z = internal_candidate
        final_evaluation = evaluate_variables(
            model,
            variables,
            activation=activation,
            ecm_internal_z=internal_z,
        )
        final_mechanical = _sample_from_evaluation(
            model,
            final_evaluation,
            variables,
            activation=activation,
            optimizer_success=equilibrium.mechanical.optimizer_success,
            optimizer_message=equilibrium.mechanical.optimizer_message,
            optimizer_iterations=equilibrium.mechanical.optimizer_iterations,
            optimizer_evaluations=equilibrium.mechanical.optimizer_evaluations,
        )
        _, dissipation_step = update_ecm_internal_state(
            model,
            final_evaluation.ecm_vertices,
            previous_internal_z,
            time_step,
        )
        cumulative_dissipation += dissipation_step
        cycle_sample = ViscoelasticCycleSample(
                step_index=step_index,
                time=float(time),
                activation=activation,
                activation_rate=activation_rate,
                mechanical=final_mechanical,
                ecm_internal_z=internal_z.copy(),
                ecm_internal_z_norm=float(np.linalg.norm(internal_z)),
                ecm_equilibrium_energy=float(
                    final_evaluation.energy_components["ecm_equilibrium"]
                ),
                ecm_viscoelastic_energy=float(
                    final_evaluation.energy_components["ecm_viscoelastic"]
                ),
                ecm_dissipation_step=dissipation_step,
                cumulative_ecm_dissipation=cumulative_dissipation,
                coupling_iterations=coupling_iteration,
                coupling_residual=coupling_residual,
        )
        samples.append(cycle_sample)
        if progress_callback is not None:
            progress_callback(cycle_sample)
        internal_symmetry = np.max(
            np.abs(internal_z - np.swapaxes(internal_z, 1, 2))
        )
        internal_trace = np.max(np.abs(np.trace(internal_z, axis1=1, axis2=2)))
        if (
            not sample_passes(final_mechanical)
            or coupling_residual > coupling_tolerance
            or dissipation_step < -1.0e-15
            or internal_symmetry > 1.0e-12
            or internal_trace > 1.0e-12
        ):
            status = "failed_physical_numerical_or_coupling_gate"
            break
    if len(samples) != steps_per_cycle + 1:
        status = "failed_before_cycle_end"
    return ViscoelasticCycleRun(
        status=status,
        model=model,
        period=float(period),
        steps_per_cycle=steps_per_cycle,
        peak_activation=float(peak_activation),
        relaxation_time=float(relaxation_time),
        deborah_number=float(relaxation_time / period),
        coupling_tolerance=float(coupling_tolerance),
        samples=tuple(samples),
    )
