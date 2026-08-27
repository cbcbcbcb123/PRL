"""Gate A M1 v04 solver with increased L-BFGS curvature memory.

The mechanics, time discretization, optimizer configuration, and numerical
thresholds are inherited from M1 v03.  The sole v04 change is increasing
``maxcor`` from 20 to 40; direct physical-gate candidate acceptance is kept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import active_energy_force, activation_protocol
from .dcm_cell import passive_energy_force
from .stage2_gate_a import (
    ACTIVE_PEAK,
    ACTIVE_STIFFNESS,
    GAUGE_RESIDUAL_LIMIT,
    PROJECTED_RESIDUAL_LIMIT,
    GateATrajectory,
    _allocate,
    _build_reference,
    _normalized_projected_residual,
    _objective_and_gradient,
    _record_node,
    evaluate_gate_a_acceptance,
)
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class GateAV04StepAudit:
    """Acceptance evidence for one stored trajectory node."""

    step_index: int
    time: float
    alpha: float
    acceptance_source: str
    initial_objective: float
    accepted_objective: float
    projected_residual: float
    gauge_increment_residual: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_reported_success: bool
    optimizer_message: str
    callback_count: int
    qualifying_evaluation_index: int
    geometry: GeometryDiagnostics

    def as_dict(self) -> dict[str, Any]:
        """Return a strict-JSON-compatible audit record."""
        return {
            "step_index": self.step_index,
            "time": self.time,
            "alpha": self.alpha,
            "acceptance_source": self.acceptance_source,
            "initial_objective": self.initial_objective,
            "accepted_objective": self.accepted_objective,
            "strict_potential_descent": (
                self.accepted_objective < self.initial_objective
            ),
            "projected_residual": self.projected_residual,
            "gauge_increment_residual": self.gauge_increment_residual,
            "optimizer_iterations": self.optimizer_iterations,
            "optimizer_evaluations": self.optimizer_evaluations,
            "optimizer_reported_success": self.optimizer_reported_success,
            "optimizer_message": self.optimizer_message,
            "callback_count": self.callback_count,
            "qualifying_evaluation_index": (
                self.qualifying_evaluation_index
            ),
            "geometry": {
                "finite": self.geometry.finite,
                "signed_volume": self.geometry.signed_volume,
                "relative_volume": self.geometry.relative_volume,
                "minimum_face_area_ratio": (
                    self.geometry.minimum_face_area_ratio
                ),
                "minimum_orientation_cosine": (
                    self.geometry.minimum_orientation_cosine
                ),
                "flipped_face_count": self.geometry.flipped_face_count,
                "degenerate_face_count": (
                    self.geometry.degenerate_face_count
                ),
            },
        }


@dataclass(frozen=True)
class GateAV04Run:
    """A complete trajectory plus per-node acceptance provenance."""

    status: str
    duration_requested: float
    trajectory: GateATrajectory
    step_audits: tuple[GateAV04StepAudit, ...]
    failure: GateAV04FailureSnapshot | None

    def summary(self) -> dict[str, Any]:
        """Combine frozen trajectory metrics with v04 method diagnostics."""
        counts: dict[str, int] = {}
        for audit in self.step_audits[1:]:
            counts[audit.acceptance_source] = (
                counts.get(audit.acceptance_source, 0) + 1
            )
        if self.status == "completed":
            response: dict[str, Any] = self.trajectory.summary()
        else:
            response = {
                "case_id": self.trajectory.case_id,
                "dt": self.trajectory.dt,
                "accepted_steps": len(self.trajectory.time) - 1,
                "last_accepted_time": float(self.trajectory.time[-1]),
                "last_accepted_axial_shortening": float(
                    self.trajectory.axial_shortening[-1]
                ),
                "last_accepted_transverse_scale_changes": [
                    float(value)
                    for value in self.trajectory.transverse_scale_change[-1]
                ],
                "last_accepted_volume_error": float(
                    self.trajectory.volume_error[-1]
                ),
            }
        response.update({
            "status": self.status,
            "duration_requested": self.duration_requested,
            "acceptance_source_counts": counts,
            "maximum_geometry_flipped_face_count": max(
                audit.geometry.flipped_face_count
                for audit in self.step_audits
            ),
            "maximum_geometry_degenerate_face_count": max(
                audit.geometry.degenerate_face_count
                for audit in self.step_audits
            ),
            "minimum_geometry_signed_volume": min(
                audit.geometry.signed_volume for audit in self.step_audits
            ),
            "minimum_geometry_face_area_ratio": min(
                audit.geometry.minimum_face_area_ratio
                for audit in self.step_audits
            ),
            "minimum_geometry_orientation_cosine": min(
                audit.geometry.minimum_orientation_cosine
                for audit in self.step_audits
            ),
        })
        if self.failure is not None:
            response["failure"] = self.failure.as_dict()
        return response


@dataclass(frozen=True)
class GateAV04FailureSnapshot:
    """First rejected v04 candidate, kept outside the accepted trajectory."""

    reason: str
    audit: GateAV04StepAudit
    candidate_vertices: FloatArray

    def as_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "candidate_is_accepted_state": False,
            **self.audit.as_dict(),
        }


@dataclass(frozen=True)
class _Candidate:
    coordinates: FloatArray
    vertices: FloatArray
    objective: float
    projected_residual: float
    gauge_increment_residual: float
    geometry: GeometryDiagnostics


@dataclass(frozen=True)
class _StepResult:
    accepted: bool
    vertices: FloatArray
    audit: GateAV04StepAudit
    failure_reason: str | None


class _PhysicalGateReached(RuntimeError):
    """Internal deterministic stop carrying the first qualifying candidate."""

    def __init__(self, coordinates: FloatArray, evaluation_index: int):
        super().__init__("physical gate reached during objective evaluation")
        self.coordinates = coordinates.copy()
        self.evaluation_index = evaluation_index


def _geometry_passes(geometry: GeometryDiagnostics) -> bool:
    return bool(
        geometry.finite
        and geometry.signed_volume > 0.0
        and geometry.flipped_face_count == 0
        and geometry.degenerate_face_count == 0
    )


def _candidate_from_coordinates(
    coordinates: FloatArray,
    current_vertices: FloatArray,
    reference: object,
    *,
    dt: float,
    alpha: float,
    alpha_limit: float = 0.2,
) -> _Candidate:
    objective, projected_gradient, residual = _objective_and_gradient(
        coordinates,
        current_vertices,
        reference,
        dt=dt,
        alpha=alpha,
        alpha_limit=alpha_limit,
    )
    increment = (reference.null_basis @ coordinates).reshape(
        current_vertices.shape
    )
    vertices = current_vertices + increment
    gauge_residual = float(
        np.linalg.norm(reference.gauge @ increment.reshape(-1))
    )
    geometry = _geometry_diagnostics(vertices, reference)
    finite = bool(
        np.all(np.isfinite(coordinates))
        and np.all(np.isfinite(vertices))
        and np.isfinite(objective)
        and np.all(np.isfinite(projected_gradient))
        and np.isfinite(residual)
        and np.isfinite(gauge_residual)
    )
    if not finite:
        residual = float("inf")
        gauge_residual = float("inf")
    return _Candidate(
        coordinates=coordinates.copy(),
        vertices=vertices,
        objective=float(objective),
        projected_residual=float(residual),
        gauge_increment_residual=gauge_residual,
        geometry=geometry,
    )


def _candidate_passes(
    candidate: _Candidate,
    *,
    initial_objective: float,
) -> bool:
    return bool(
        np.isfinite(candidate.objective)
        and candidate.objective < initial_objective
        and candidate.projected_residual <= PROJECTED_RESIDUAL_LIMIT
        and candidate.gauge_increment_residual <= GAUGE_RESIDUAL_LIMIT
        and _geometry_passes(candidate.geometry)
    )


def _solve_v04_step(
    current_vertices: FloatArray,
    reference: object,
    *,
    step_index: int,
    time: float,
    dt: float,
    alpha: float,
    alpha_limit: float = 0.2,
) -> _StepResult:
    passive_energies, passive_force = passive_energy_force(
        current_vertices,
        reference.cell,
    )
    active_energy, active_force, _ = active_energy_force(
        current_vertices,
        reference.active,
        alpha=alpha,
        k_f=ACTIVE_STIFFNESS,
        alpha_limit=alpha_limit,
    )
    initial_objective = float(
        passive_energies["cell_total"] + active_energy
    )
    zero_drag = np.zeros_like(current_vertices)
    initial_gradient = -passive_force - active_force
    initial_residual = _normalized_projected_residual(
        initial_gradient,
        reference,
        (passive_force, active_force, zero_drag),
    )
    initial_geometry = _geometry_diagnostics(current_vertices, reference)
    if initial_residual <= PROJECTED_RESIDUAL_LIMIT:
        if not _geometry_passes(initial_geometry):
            rejected_audit = GateAV04StepAudit(
                step_index=step_index,
                time=time,
                alpha=alpha,
                acceptance_source="rejected_initial_state",
                initial_objective=initial_objective,
                accepted_objective=initial_objective,
                projected_residual=initial_residual,
                gauge_increment_residual=0.0,
                optimizer_iterations=0,
                optimizer_evaluations=1,
                optimizer_reported_success=True,
                optimizer_message=(
                    "initial_state_satisfies_residual_but_fails_geometry"
                ),
                callback_count=0,
                qualifying_evaluation_index=0,
                geometry=initial_geometry,
            )
            return _StepResult(
                accepted=False,
                vertices=current_vertices.copy(),
                audit=rejected_audit,
                failure_reason="initial_state_geometry_gate_failed",
            )
        return _StepResult(
            accepted=True,
            vertices=current_vertices.copy(),
            audit=GateAV04StepAudit(
                step_index=step_index,
                time=time,
                alpha=alpha,
                acceptance_source="initial_state_physical_gate",
                initial_objective=initial_objective,
                accepted_objective=initial_objective,
                projected_residual=initial_residual,
                gauge_increment_residual=0.0,
                optimizer_iterations=0,
                optimizer_evaluations=1,
                optimizer_reported_success=True,
                optimizer_message=(
                    "initial_state_satisfies_physical_gate"
                ),
                callback_count=0,
                qualifying_evaluation_index=0,
                geometry=initial_geometry,
            ),
            failure_reason=None,
        )

    initial_coordinates = np.zeros(
        reference.null_basis.shape[1],
        dtype=np.float64,
    )
    evaluation_count = 0
    callback_count = 0

    def objective(coordinates: FloatArray) -> tuple[float, FloatArray]:
        nonlocal evaluation_count
        value, gradient, residual = _objective_and_gradient(
            coordinates,
            current_vertices,
            reference,
            dt=dt,
            alpha=alpha,
            alpha_limit=alpha_limit,
        )
        evaluation_count += 1
        finite = bool(
            np.all(np.isfinite(coordinates))
            and np.isfinite(value)
            and np.all(np.isfinite(gradient))
            and np.isfinite(residual)
        )
        if (
            finite
            and value < initial_objective
            and residual <= PROJECTED_RESIDUAL_LIMIT
        ):
            candidate = _candidate_from_coordinates(
                coordinates,
                current_vertices,
                reference,
                dt=dt,
                alpha=alpha,
                alpha_limit=alpha_limit,
            )
            if _candidate_passes(
                candidate,
                initial_objective=initial_objective,
            ):
                raise _PhysicalGateReached(
                    coordinates,
                    evaluation_count,
                )
        return value, gradient

    def record_callback(_coordinates: FloatArray) -> None:
        nonlocal callback_count
        callback_count += 1

    try:
        result = minimize(
            objective,
            initial_coordinates,
            method="L-BFGS-B",
            jac=True,
            callback=record_callback,
            options={
                "maxiter": 200,
                "maxls": 40,
                "maxcor": 40,
                "ftol": 0.0,
                "gtol": 1.0e-10,
            },
        )
    except _PhysicalGateReached as stop:
        coordinates = stop.coordinates
        qualifying_evaluation_index = stop.evaluation_index
        optimizer_iterations = callback_count
        optimizer_evaluations = evaluation_count
        optimizer_reported_success = False
        optimizer_message = (
            "physical_gate_reached_during_objective_evaluation"
        )
        acceptance_source = "objective_evaluation_physical_gate"
    else:
        coordinates = np.asarray(result.x, dtype=np.float64)
        qualifying_evaluation_index = evaluation_count
        optimizer_iterations = int(result.nit)
        optimizer_evaluations = int(result.nfev)
        optimizer_reported_success = bool(result.success)
        optimizer_message = str(result.message)
        acceptance_source = "optimizer_return_physical_gate"

    candidate = _candidate_from_coordinates(
        coordinates,
        current_vertices,
        reference,
        dt=dt,
        alpha=alpha,
        alpha_limit=alpha_limit,
    )
    if not _candidate_passes(
        candidate,
        initial_objective=initial_objective,
    ):
        rejected_audit = GateAV04StepAudit(
            step_index=step_index,
            time=time,
            alpha=alpha,
            acceptance_source="rejected_optimizer_candidate",
            initial_objective=initial_objective,
            accepted_objective=candidate.objective,
            projected_residual=candidate.projected_residual,
            gauge_increment_residual=candidate.gauge_increment_residual,
            optimizer_iterations=optimizer_iterations,
            optimizer_evaluations=optimizer_evaluations,
            optimizer_reported_success=optimizer_reported_success,
            optimizer_message=optimizer_message,
            callback_count=callback_count,
            qualifying_evaluation_index=qualifying_evaluation_index,
            geometry=candidate.geometry,
        )
        return _StepResult(
            accepted=False,
            vertices=candidate.vertices,
            audit=rejected_audit,
            failure_reason=(
                "physical_gate_or_descent_or_geometry_check_failed"
            ),
        )
    return _StepResult(
        accepted=True,
        vertices=candidate.vertices,
        audit=GateAV04StepAudit(
            step_index=step_index,
            time=time,
            alpha=alpha,
            acceptance_source=acceptance_source,
            initial_objective=initial_objective,
            accepted_objective=candidate.objective,
            projected_residual=candidate.projected_residual,
            gauge_increment_residual=(
                candidate.gauge_increment_residual
            ),
            optimizer_iterations=optimizer_iterations,
            optimizer_evaluations=optimizer_evaluations,
            optimizer_reported_success=optimizer_reported_success,
            optimizer_message=optimizer_message,
            callback_count=callback_count,
            qualifying_evaluation_index=qualifying_evaluation_index,
            geometry=candidate.geometry,
        ),
        failure_reason=None,
    )


def run_gate_a_v04_trajectory(
    case_id: str,
    *,
    dt: float,
    duration: float = 5.0,
    alpha_peak: float = ACTIVE_PEAK,
    activation_limit: float = 0.2,
) -> GateAV04Run:
    """Run one M1 v04 A0/A1 trajectory without retries."""
    if case_id not in {"A0_ZERO", "A1_ACTIVE"}:
        raise ValueError(f"unknown Gate A case: {case_id}")
    if dt not in {0.02, 0.01, 0.005}:
        raise ValueError("Gate A dt must be one of the three frozen levels")
    if (
        not np.isfinite(alpha_peak)
        or not np.isfinite(activation_limit)
        or activation_limit <= 0.0
        or not 0.0 <= alpha_peak <= activation_limit
    ):
        raise ValueError(
            "alpha_peak must be finite and inside the configured "
            "activation limit"
        )
    step_count = int(round(duration / dt))
    if not np.isclose(step_count * dt, duration, rtol=0.0, atol=1.0e-12):
        raise ValueError("duration must be an integer multiple of dt")

    reference = _build_reference()
    time = np.linspace(0.0, duration, step_count + 1, dtype=np.float64)
    storage = _allocate(len(time), len(reference.vertices))
    iterations = np.zeros(len(time), dtype=np.int64)
    evaluations = np.ones(len(time), dtype=np.int64)
    successes = np.ones(len(time), dtype=np.bool_)
    current = reference.vertices.copy()
    alpha0, alpha_rate0 = (
        activation_protocol(time[0], alpha_peak=alpha_peak)
        if case_id == "A1_ACTIVE"
        else (0.0, 0.0)
    )
    zero_velocity = np.zeros_like(current)
    _record_node(
        storage,
        0,
        current,
        zero_velocity,
        reference,
        alpha=alpha0,
        alpha_rate=alpha_rate0,
        projected_residual=0.0,
        gauge_residual=0.0,
        alpha_limit=activation_limit,
    )
    initial_geometry = _geometry_diagnostics(current, reference)
    passive_energies, _ = passive_energy_force(current, reference.cell)
    active_energy, _, _ = active_energy_force(
        current,
        reference.active,
        alpha=alpha0,
        k_f=ACTIVE_STIFFNESS,
        alpha_limit=activation_limit,
    )
    initial_objective = float(
        passive_energies["cell_total"] + active_energy
    )
    audits: list[GateAV04StepAudit] = [
        GateAV04StepAudit(
            step_index=0,
            time=0.0,
            alpha=alpha0,
            acceptance_source="initial_reference_state",
            initial_objective=initial_objective,
            accepted_objective=initial_objective,
            projected_residual=0.0,
            gauge_increment_residual=0.0,
            optimizer_iterations=0,
            optimizer_evaluations=1,
            optimizer_reported_success=True,
            optimizer_message="initial_reference_state",
            callback_count=0,
            qualifying_evaluation_index=0,
            geometry=initial_geometry,
        )
    ]

    failure: GateAV04FailureSnapshot | None = None
    for index in range(1, len(time)):
        alpha, alpha_rate = (
            activation_protocol(time[index], alpha_peak=alpha_peak)
            if case_id == "A1_ACTIVE"
            else (0.0, 0.0)
        )
        step = _solve_v04_step(
            current,
            reference,
            step_index=index,
            time=float(time[index]),
            dt=dt,
            alpha=alpha,
            alpha_limit=activation_limit,
        )
        if not step.accepted:
            if step.failure_reason is None:
                raise RuntimeError("rejected v04 step lacks a failure reason")
            failure = GateAV04FailureSnapshot(
                reason=step.failure_reason,
                audit=step.audit,
                candidate_vertices=step.vertices.copy(),
            )
            break
        velocity = (step.vertices - current) / dt
        _record_node(
            storage,
            index,
            step.vertices,
            velocity,
            reference,
            alpha=alpha,
            alpha_rate=alpha_rate,
            projected_residual=step.audit.projected_residual,
            gauge_residual=step.audit.gauge_increment_residual,
            alpha_limit=activation_limit,
        )
        iterations[index] = step.audit.optimizer_iterations
        evaluations[index] = step.audit.optimizer_evaluations
        successes[index] = step.audit.optimizer_reported_success
        audits.append(step.audit)
        current = step.vertices

    accepted_count = len(audits)
    trajectory = GateATrajectory(
        case_id=case_id,
        dt=dt,
        time=time[:accepted_count].copy(),
        vertices=storage["vertices"][:accepted_count].copy(),
        alpha=storage["alpha"][:accepted_count].copy(),
        alpha_rate=storage["alpha_rate"][:accepted_count].copy(),
        fiber_length=storage["fiber_length"][:accepted_count].copy(),
        axial_shortening=(
            storage["axial_shortening"][:accepted_count].copy()
        ),
        transverse_scale_change=(
            storage["transverse"][:accepted_count].copy()
        ),
        volume_error=storage["volume_error"][:accepted_count].copy(),
        centroid_drift=(
            storage["centroid_drift"][:accepted_count].copy()
        ),
        passive_energy=(
            storage["passive_energy"][:accepted_count].copy()
        ),
        active_energy=storage["active_energy"][:accepted_count].copy(),
        stored_energy=storage["stored_energy"][:accepted_count].copy(),
        dissipation=storage["dissipation"][:accepted_count].copy(),
        active_power=storage["active_power"][:accepted_count].copy(),
        active_net_force=(
            storage["active_net_force"][:accepted_count].copy()
        ),
        active_net_moment=(
            storage["active_net_moment"][:accepted_count].copy()
        ),
        projected_residual=(
            storage["projected_residual"][:accepted_count].copy()
        ),
        gauge_increment_residual=(
            storage["gauge_residual"][:accepted_count].copy()
        ),
        optimizer_iterations=iterations[:accepted_count].copy(),
        optimizer_evaluations=evaluations[:accepted_count].copy(),
        optimizer_reported_success=successes[:accepted_count].copy(),
    )
    return GateAV04Run(
        status=("completed" if failure is None else "failed_invalid_numerics"),
        duration_requested=duration,
        trajectory=trajectory,
        step_audits=tuple(audits),
        failure=failure,
    )


def run_gate_a_v04_suite() -> tuple[
    dict[str, GateAV04Run],
    dict[str, Any],
]:
    """Run the complete registered M1 v04 suite and frozen acceptance."""
    configurations = (
        ("A0_ZERO_dt0.01", "A0_ZERO", 0.01),
        ("A1_ACTIVE_dt0.02", "A1_ACTIVE", 0.02),
        ("A1_ACTIVE_dt0.01", "A1_ACTIVE", 0.01),
        ("A1_ACTIVE_dt0.005", "A1_ACTIVE", 0.005),
    )
    runs: dict[str, GateAV04Run] = {}
    for run_id, case_id, dt in configurations:
        run = run_gate_a_v04_trajectory(case_id, dt=dt)
        runs[run_id] = run
        if run.status != "completed":
            acceptance = {
                "gate_id": "A",
                "status": "failed_invalid_numerics",
                "failed_run_id": run_id,
                "failure": (
                    run.failure.as_dict()
                    if run.failure is not None
                    else None
                ),
                "completed_run_ids": [
                    key
                    for key, item in runs.items()
                    if item.status == "completed"
                ],
            }
            return runs, acceptance
    acceptance = evaluate_gate_a_acceptance({
        key: run.trajectory for key, run in runs.items()
    })
    return runs, acceptance
