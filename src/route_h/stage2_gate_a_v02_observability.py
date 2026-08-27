"""Observable replay of the frozen Gate A v01 single-cell solver.

This module deliberately does not change the frozen mechanics, optimizer
settings, or acceptance thresholds.  It separates accepted trajectory nodes
from the optimizer candidate returned at the first invalid step.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import active_energy_force, activation_protocol
from .dcm_cell import passive_energy_force, surface_volume_and_gradient
from .stage2_gate_a import (
    ACTIVE_PEAK,
    ACTIVE_STIFFNESS,
    DRAG,
    GAUGE_RESIDUAL_LIMIT,
    PROJECTED_RESIDUAL_LIMIT,
    _allocate,
    _build_reference,
    _normalized_projected_residual,
    _objective_and_gradient,
    _record_node,
)


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class OptimizerEvaluation:
    """One objective/gradient evaluation in optimizer call order."""

    evaluation_index: int
    objective: float
    projected_residual: float
    projected_gradient_norm: float
    coordinate_norm: float


@dataclass(frozen=True)
class GeometryDiagnostics:
    """Minimal surface-mesh checks for a diagnostic, not-yet-accepted state."""

    finite: bool
    signed_volume: float
    relative_volume: float
    minimum_face_area_ratio: float
    minimum_orientation_cosine: float
    flipped_face_count: int
    degenerate_face_count: int


@dataclass(frozen=True)
class GateAFailureSnapshot:
    """Rejected optimizer candidate at the first invalid time node."""

    step_index: int
    time: float
    alpha: float
    reason: str
    projected_residual: float
    gauge_increment_residual: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_reported_success: bool
    optimizer_message: str
    callback_count: int
    callback_residuals: tuple[float, ...]
    incremental_objective: float
    projected_gradient_norm: float
    candidate_vertices: FloatArray
    geometry: GeometryDiagnostics
    optimizer_trace: tuple[OptimizerEvaluation, ...]


@dataclass(frozen=True)
class GateAObservableRun:
    """Accepted partial trajectory plus an optional rejected candidate."""

    status: str
    case_id: str
    dt: float
    duration_requested: float
    time: FloatArray
    vertices: FloatArray
    alpha: FloatArray
    alpha_rate: FloatArray
    fiber_length: FloatArray
    axial_shortening: FloatArray
    transverse_scale_change: FloatArray
    volume_error: FloatArray
    centroid_drift: FloatArray
    passive_energy: FloatArray
    active_energy: FloatArray
    stored_energy: FloatArray
    dissipation: FloatArray
    active_power: FloatArray
    active_net_force: FloatArray
    active_net_moment: FloatArray
    projected_residual: FloatArray
    gauge_increment_residual: FloatArray
    optimizer_iterations: IntArray
    optimizer_evaluations: IntArray
    optimizer_reported_success: BoolArray
    failure: GateAFailureSnapshot | None

    @property
    def accepted_steps(self) -> int:
        return len(self.time) - 1

    def summary(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "case_id": self.case_id,
            "dt": self.dt,
            "duration_requested": self.duration_requested,
            "accepted_steps": self.accepted_steps,
            "last_accepted_time": float(self.time[-1]),
            "last_accepted_axial_shortening": float(
                self.axial_shortening[-1]
            ),
            "last_accepted_transverse_scale_changes": [
                float(value) for value in self.transverse_scale_change[-1]
            ],
            "last_accepted_volume_error": float(self.volume_error[-1]),
            "maximum_accepted_projected_residual": float(
                np.max(self.projected_residual)
            ),
            "maximum_accepted_gauge_increment_residual": float(
                np.max(self.gauge_increment_residual)
            ),
        }
        if self.failure is not None:
            payload["failure"] = {
                "step_index": self.failure.step_index,
                "time": self.failure.time,
                "alpha": self.failure.alpha,
                "reason": self.failure.reason,
                "projected_residual": self.failure.projected_residual,
                "projected_residual_limit": PROJECTED_RESIDUAL_LIMIT,
                "gauge_increment_residual": (
                    self.failure.gauge_increment_residual
                ),
                "gauge_increment_residual_limit": GAUGE_RESIDUAL_LIMIT,
                "optimizer_iterations": self.failure.optimizer_iterations,
                "optimizer_evaluations": self.failure.optimizer_evaluations,
                "optimizer_reported_success": (
                    self.failure.optimizer_reported_success
                ),
                "optimizer_message": self.failure.optimizer_message,
                "candidate_geometry": {
                    "finite": self.failure.geometry.finite,
                    "signed_volume": self.failure.geometry.signed_volume,
                    "relative_volume": self.failure.geometry.relative_volume,
                    "minimum_face_area_ratio": (
                        self.failure.geometry.minimum_face_area_ratio
                    ),
                    "minimum_orientation_cosine": (
                        self.failure.geometry.minimum_orientation_cosine
                    ),
                    "flipped_face_count": (
                        self.failure.geometry.flipped_face_count
                    ),
                    "degenerate_face_count": (
                        self.failure.geometry.degenerate_face_count
                    ),
                },
            }
        return payload


@dataclass(frozen=True)
class _ObservableStep:
    accepted: bool
    vertices: FloatArray
    projected_residual: float
    gauge_increment_residual: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_reported_success: bool
    optimizer_message: str
    callback_residuals: tuple[float, ...]
    incremental_objective: float
    projected_gradient_norm: float
    optimizer_trace: tuple[OptimizerEvaluation, ...]
    failure_reason: str | None


def _geometry_diagnostics(
    vertices: FloatArray,
    reference: object,
) -> GeometryDiagnostics:
    faces = reference.faces
    reference_vertices = reference.vertices
    current_edges_1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    current_edges_2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    reference_edges_1 = (
        reference_vertices[faces[:, 1]] - reference_vertices[faces[:, 0]]
    )
    reference_edges_2 = (
        reference_vertices[faces[:, 2]] - reference_vertices[faces[:, 0]]
    )
    current_cross = np.cross(current_edges_1, current_edges_2)
    reference_cross = np.cross(reference_edges_1, reference_edges_2)
    current_double_area = np.linalg.norm(current_cross, axis=1)
    reference_double_area = np.linalg.norm(reference_cross, axis=1)
    area_ratio = np.divide(
        current_double_area,
        reference_double_area,
        out=np.full_like(current_double_area, np.nan),
        where=reference_double_area > 0.0,
    )
    orientation_denominator = current_double_area * reference_double_area
    orientation_cosine = np.divide(
        np.sum(current_cross * reference_cross, axis=1),
        orientation_denominator,
        out=np.full_like(current_double_area, np.nan),
        where=orientation_denominator > 0.0,
    )
    finite = bool(
        np.all(np.isfinite(vertices))
        and np.all(np.isfinite(area_ratio))
        and np.all(np.isfinite(orientation_cosine))
    )
    volume, _ = surface_volume_and_gradient(vertices, faces)
    flipped = int(np.count_nonzero(orientation_cosine <= 0.0))
    degenerate = int(np.count_nonzero(area_ratio <= 1.0e-12))
    return GeometryDiagnostics(
        finite=bool(finite and np.isfinite(volume)),
        signed_volume=float(volume),
        relative_volume=float(volume / reference.cell.volume0),
        minimum_face_area_ratio=float(np.nanmin(area_ratio)),
        minimum_orientation_cosine=float(np.nanmin(orientation_cosine)),
        flipped_face_count=flipped,
        degenerate_face_count=degenerate,
    )


def _solve_observable_step(
    current_vertices: FloatArray,
    reference: object,
    *,
    dt: float,
    alpha: float,
) -> _ObservableStep:
    _, passive_force = passive_energy_force(
        current_vertices,
        reference.cell,
    )
    _, active_force, _ = active_energy_force(
        current_vertices,
        reference.active,
        alpha=alpha,
        k_f=ACTIVE_STIFFNESS,
    )
    zero_drag = np.zeros_like(current_vertices)
    initial_gradient = -passive_force - active_force
    initial_residual = _normalized_projected_residual(
        initial_gradient,
        reference,
        (passive_force, active_force, zero_drag),
    )
    if initial_residual <= PROJECTED_RESIDUAL_LIMIT:
        return _ObservableStep(
            accepted=True,
            vertices=current_vertices.copy(),
            projected_residual=initial_residual,
            gauge_increment_residual=0.0,
            optimizer_iterations=0,
            optimizer_evaluations=1,
            optimizer_reported_success=True,
            optimizer_message="initial_state_satisfies_physical_gate",
            callback_residuals=(),
            incremental_objective=0.0,
            projected_gradient_norm=float(
                np.linalg.norm(
                    reference.null_basis.T @ initial_gradient.reshape(-1)
                )
            ),
            optimizer_trace=(),
            failure_reason=None,
        )

    initial_coordinates = np.zeros(
        reference.null_basis.shape[1],
        dtype=np.float64,
    )
    latest_residual = float("inf")
    evaluated_coordinates: FloatArray | None = None
    trace: list[OptimizerEvaluation] = []
    callback_residuals: list[float] = []

    def objective(coordinates: FloatArray) -> tuple[float, FloatArray]:
        nonlocal latest_residual, evaluated_coordinates
        value, gradient, latest_residual = _objective_and_gradient(
            coordinates,
            current_vertices,
            reference,
            dt=dt,
            alpha=alpha,
        )
        evaluated_coordinates = coordinates.copy()
        trace.append(
            OptimizerEvaluation(
                evaluation_index=len(trace) + 1,
                objective=float(value),
                projected_residual=float(latest_residual),
                projected_gradient_norm=float(np.linalg.norm(gradient)),
                coordinate_norm=float(np.linalg.norm(coordinates)),
            )
        )
        return value, gradient

    def stop_at_physical_gate(coordinates: FloatArray) -> None:
        nonlocal latest_residual, evaluated_coordinates
        if (
            evaluated_coordinates is None
            or not np.array_equal(coordinates, evaluated_coordinates)
        ):
            _, gradient, latest_residual = _objective_and_gradient(
                coordinates,
                current_vertices,
                reference,
                dt=dt,
                alpha=alpha,
            )
            evaluated_coordinates = coordinates.copy()
            trace.append(
                OptimizerEvaluation(
                    evaluation_index=len(trace) + 1,
                    objective=float(
                        _objective_and_gradient(
                            coordinates,
                            current_vertices,
                            reference,
                            dt=dt,
                            alpha=alpha,
                        )[0]
                    ),
                    projected_residual=float(latest_residual),
                    projected_gradient_norm=float(np.linalg.norm(gradient)),
                    coordinate_norm=float(np.linalg.norm(coordinates)),
                )
            )
        callback_residuals.append(float(latest_residual))
        if latest_residual <= PROJECTED_RESIDUAL_LIMIT:
            raise StopIteration

    result = minimize(
        objective,
        initial_coordinates,
        method="L-BFGS-B",
        jac=True,
        callback=stop_at_physical_gate,
        options={
            "maxiter": 200,
            "maxls": 40,
            "maxcor": 20,
            "ftol": 0.0,
            "gtol": 1.0e-10,
        },
    )
    increment = (reference.null_basis @ result.x).reshape(
        current_vertices.shape
    )
    next_vertices = current_vertices + increment
    _, next_passive_force = passive_energy_force(
        next_vertices,
        reference.cell,
    )
    _, next_active_force, _ = active_energy_force(
        next_vertices,
        reference.active,
        alpha=alpha,
        k_f=ACTIVE_STIFFNESS,
    )
    drag_gradient = (
        DRAG / dt * reference.dual_weights[:, None] * increment
    )
    full_gradient = (
        -next_passive_force - next_active_force + drag_gradient
    )
    residual = _normalized_projected_residual(
        full_gradient,
        reference,
        (next_passive_force, next_active_force, drag_gradient),
    )
    gauge_residual = float(
        np.linalg.norm(reference.gauge @ increment.reshape(-1))
    )
    incremental_objective, projected_gradient, _ = _objective_and_gradient(
        result.x,
        current_vertices,
        reference,
        dt=dt,
        alpha=alpha,
    )
    finite = bool(
        np.all(np.isfinite(next_vertices))
        and np.isfinite(residual)
        and np.isfinite(gauge_residual)
    )
    if not finite:
        failure_reason = "nonfinite_candidate"
    elif residual > PROJECTED_RESIDUAL_LIMIT:
        failure_reason = (
            "physical_projected_overdamped_residual_above_limit"
        )
    elif gauge_residual > GAUGE_RESIDUAL_LIMIT:
        failure_reason = "gauge_increment_residual_above_limit"
    else:
        failure_reason = None
    return _ObservableStep(
        accepted=failure_reason is None,
        vertices=next_vertices,
        projected_residual=residual,
        gauge_increment_residual=gauge_residual,
        optimizer_iterations=int(result.nit),
        optimizer_evaluations=int(result.nfev),
        optimizer_reported_success=bool(result.success),
        optimizer_message=str(result.message),
        callback_residuals=tuple(callback_residuals),
        incremental_objective=float(incremental_objective),
        projected_gradient_norm=float(np.linalg.norm(projected_gradient)),
        optimizer_trace=tuple(trace),
        failure_reason=failure_reason,
    )


def _slice_storage(
    storage: dict[str, FloatArray],
    count: int,
) -> dict[str, FloatArray]:
    return {name: values[:count].copy() for name, values in storage.items()}


def run_gate_a_observability(
    case_id: str,
    *,
    dt: float,
    duration: float = 5.0,
) -> GateAObservableRun:
    """Replay Gate A while preserving accepted nodes and a rejected candidate."""

    if case_id not in {"A0_ZERO", "A1_ACTIVE"}:
        raise ValueError(f"unknown Gate A case: {case_id}")
    if dt not in {0.02, 0.01, 0.005}:
        raise ValueError("Gate A dt must be one of the three frozen levels")
    step_count = int(round(duration / dt))
    if not np.isclose(step_count * dt, duration, rtol=0.0, atol=1.0e-12):
        raise ValueError("duration must be an integer multiple of dt")

    reference = _build_reference()
    requested_time = np.linspace(
        0.0,
        duration,
        step_count + 1,
        dtype=np.float64,
    )
    storage = _allocate(len(requested_time), len(reference.vertices))
    iterations = np.zeros(len(requested_time), dtype=np.int64)
    evaluations = np.ones(len(requested_time), dtype=np.int64)
    successes = np.ones(len(requested_time), dtype=np.bool_)
    current = reference.vertices.copy()
    alpha0, alpha_rate0 = (
        activation_protocol(requested_time[0], alpha_peak=ACTIVE_PEAK)
        if case_id == "A1_ACTIVE"
        else (0.0, 0.0)
    )
    _record_node(
        storage,
        0,
        current,
        np.zeros_like(current),
        reference,
        alpha=alpha0,
        alpha_rate=alpha_rate0,
        projected_residual=0.0,
        gauge_residual=0.0,
    )

    accepted_count = 1
    failure: GateAFailureSnapshot | None = None
    for index in range(1, len(requested_time)):
        alpha, alpha_rate = (
            activation_protocol(
                requested_time[index],
                alpha_peak=ACTIVE_PEAK,
            )
            if case_id == "A1_ACTIVE"
            else (0.0, 0.0)
        )
        step = _solve_observable_step(
            current,
            reference,
            dt=dt,
            alpha=alpha,
        )
        if not step.accepted:
            failure = GateAFailureSnapshot(
                step_index=index,
                time=float(requested_time[index]),
                alpha=float(alpha),
                reason=str(step.failure_reason),
                projected_residual=step.projected_residual,
                gauge_increment_residual=(
                    step.gauge_increment_residual
                ),
                optimizer_iterations=step.optimizer_iterations,
                optimizer_evaluations=step.optimizer_evaluations,
                optimizer_reported_success=(
                    step.optimizer_reported_success
                ),
                optimizer_message=step.optimizer_message,
                callback_count=len(step.callback_residuals),
                callback_residuals=step.callback_residuals,
                incremental_objective=step.incremental_objective,
                projected_gradient_norm=step.projected_gradient_norm,
                candidate_vertices=step.vertices.copy(),
                geometry=_geometry_diagnostics(step.vertices, reference),
                optimizer_trace=step.optimizer_trace,
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
            projected_residual=step.projected_residual,
            gauge_residual=step.gauge_increment_residual,
        )
        iterations[index] = step.optimizer_iterations
        evaluations[index] = step.optimizer_evaluations
        successes[index] = step.optimizer_reported_success
        current = step.vertices
        accepted_count += 1

    accepted = _slice_storage(storage, accepted_count)
    status = "completed" if failure is None else "failed_invalid_numerics"
    return GateAObservableRun(
        status=status,
        case_id=case_id,
        dt=dt,
        duration_requested=float(duration),
        time=requested_time[:accepted_count].copy(),
        vertices=accepted["vertices"],
        alpha=accepted["alpha"],
        alpha_rate=accepted["alpha_rate"],
        fiber_length=accepted["fiber_length"],
        axial_shortening=accepted["axial_shortening"],
        transverse_scale_change=accepted["transverse"],
        volume_error=accepted["volume_error"],
        centroid_drift=accepted["centroid_drift"],
        passive_energy=accepted["passive_energy"],
        active_energy=accepted["active_energy"],
        stored_energy=accepted["stored_energy"],
        dissipation=accepted["dissipation"],
        active_power=accepted["active_power"],
        active_net_force=accepted["active_net_force"],
        active_net_moment=accepted["active_net_moment"],
        projected_residual=accepted["projected_residual"],
        gauge_increment_residual=accepted["gauge_residual"],
        optimizer_iterations=iterations[:accepted_count].copy(),
        optimizer_evaluations=evaluations[:accepted_count].copy(),
        optimizer_reported_success=successes[:accepted_count].copy(),
        failure=failure,
    )
