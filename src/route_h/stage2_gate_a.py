"""Frozen Stage 2 Gate A single-myocardial-cell response solver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import null_space
from scipy.optimize import minimize

from .activation import (
    ActiveReference,
    active_energy_force,
    active_input_power,
    activation_protocol,
    build_active_reference,
    transverse_scale_changes,
    weighted_centroid,
)
from .dcm_cell import (
    CellReference,
    build_cell_reference,
    nodal_drag_dissipation,
    passive_energy_force,
    surface_volume_and_gradient,
)
from .discretization import load_discretization_level
from .gauge import gauge_matrix
from .ledger import integrated_power_residual, trapezoidal_integral


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

MYOCARDIAL_TEMPLATE_CELL_ID = 6
DRAG = 1.0
ACTIVE_STIFFNESS = 10.0
ACTIVE_PEAK = 0.1
PROJECTED_RESIDUAL_LIMIT = 1.0e-8
GAUGE_RESIDUAL_LIMIT = 1.0e-12
PLATEAU_METRIC_TIME = 3.0


class GateANumericalError(RuntimeError):
    """Raised when the frozen Gate A numerical method fails its own gate."""


@dataclass(frozen=True)
class GateATrajectory:
    case_id: str
    dt: float
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

    def summary(self) -> dict[str, float | int | str | bool | list[float]]:
        plateau_index = int(np.argmin(np.abs(self.time - PLATEAU_METRIC_TIME)))
        if not np.isclose(
            self.time[plateau_index],
            PLATEAU_METRIC_TIME,
            rtol=0.0,
            atol=1.0e-12,
        ):
            raise GateANumericalError("trajectory lacks the frozen t=3.0 node")
        return {
            "case_id": self.case_id,
            "dt": self.dt,
            "accepted_steps": len(self.time) - 1,
            "peak_axial_shortening": float(np.max(self.axial_shortening)),
            "plateau_transverse_scale_changes": [
                float(value)
                for value in self.transverse_scale_change[plateau_index]
            ],
            "maximum_volume_error": float(np.max(np.abs(self.volume_error))),
            "maximum_centroid_drift": float(np.max(self.centroid_drift)),
            "maximum_active_net_force": float(np.max(self.active_net_force)),
            "maximum_active_net_moment": float(np.max(self.active_net_moment)),
            "minimum_dissipation": float(np.min(self.dissipation)),
            "integrated_active_work": trapezoidal_integral(
                self.time,
                self.active_power,
            ),
            "total_dissipation": trapezoidal_integral(
                self.time,
                self.dissipation,
            ),
            "integrated_power_residual": integrated_power_residual(
                self.time,
                self.stored_energy,
                self.dissipation,
                self.active_power,
            ),
            "maximum_projected_residual": float(
                np.max(self.projected_residual)
            ),
            "maximum_gauge_increment_residual": float(
                np.max(self.gauge_increment_residual)
            ),
            "optimizer_reported_success_all_steps": bool(
                np.all(self.optimizer_reported_success)
            ),
            "optimizer_iterations_total": int(
                np.sum(self.optimizer_iterations)
            ),
            "optimizer_evaluations_total": int(
                np.sum(self.optimizer_evaluations)
            ),
        }


@dataclass(frozen=True)
class _GateAReference:
    vertices: FloatArray
    faces: IntArray
    dual_weights: FloatArray
    cell: CellReference
    active: ActiveReference
    gauge: FloatArray
    null_basis: FloatArray
    centroid0: FloatArray


def _build_reference() -> _GateAReference:
    arrays, _ = load_discretization_level("base")
    cell_id = MYOCARDIAL_TEMPLATE_CELL_ID
    vertices = arrays["cell_vertices"][cell_id]
    faces = arrays["cell_faces"][cell_id]
    counts = arrays["cell_anchor_counts"][cell_id]
    minus_face_ids = arrays["cell_anchor_minus_face_ids"][
        cell_id, : int(counts[0])
    ]
    plus_face_ids = arrays["cell_anchor_plus_face_ids"][
        cell_id, : int(counts[1])
    ]
    dual_weights = arrays["cell_gauge_dual_area_weights"][cell_id]
    cell_reference = build_cell_reference(
        vertices,
        faces,
        arrays["cell_primary_identity"][cell_id],
        arrays["cell_directional_identity"][cell_id],
    )
    active_reference = build_active_reference(
        vertices,
        faces,
        minus_face_ids,
        plus_face_ids,
    )
    gauge = gauge_matrix(vertices, dual_weights)
    basis = null_space(gauge)
    if basis.shape != (vertices.size, vertices.size - 6):
        raise GateANumericalError("unexpected Gate A null-space dimension")
    gauge_basis_residual = float(np.linalg.norm(gauge @ basis))
    if gauge_basis_residual > 1.0e-12:
        raise GateANumericalError(
            f"Gate A null-space seal failed: {gauge_basis_residual}"
        )
    return _GateAReference(
        vertices=vertices.copy(),
        faces=faces.copy(),
        dual_weights=dual_weights.copy(),
        cell=cell_reference,
        active=active_reference,
        gauge=gauge,
        null_basis=basis,
        centroid0=weighted_centroid(vertices, dual_weights),
    )


def _relative_difference(first: float, second: float) -> float:
    return abs(first - second) / max(1.0e-8, abs(first), abs(second))


def _objective_and_gradient(
    coordinates: FloatArray,
    current_vertices: FloatArray,
    reference: _GateAReference,
    *,
    dt: float,
    alpha: float,
) -> tuple[float, FloatArray, float]:
    increment = (reference.null_basis @ coordinates).reshape(
        current_vertices.shape
    )
    vertices = current_vertices + increment
    passive_energies, passive_force = passive_energy_force(
        vertices,
        reference.cell,
    )
    active_energy, active_force, _ = active_energy_force(
        vertices,
        reference.active,
        alpha=alpha,
        k_f=ACTIVE_STIFFNESS,
    )
    drag_energy = (
        0.5
        * DRAG
        / dt
        * float(
            np.sum(
                reference.dual_weights[:, None]
                * increment
                * increment
            )
        )
    )
    drag_gradient = (
        DRAG / dt * reference.dual_weights[:, None] * increment
    )
    gradient = -passive_force - active_force + drag_gradient
    objective = (
        float(passive_energies["cell_total"])
        + active_energy
        + drag_energy
    )
    projected_gradient = reference.null_basis.T @ gradient.reshape(-1)
    denominator = max(
        1.0,
        float(np.linalg.norm(passive_force))
        + float(np.linalg.norm(active_force))
        + float(np.linalg.norm(drag_gradient)),
    )
    return objective, projected_gradient, float(
        np.linalg.norm(projected_gradient) / denominator
    )


def _normalized_projected_residual(
    gradient: FloatArray,
    reference: _GateAReference,
    force_blocks: tuple[FloatArray, ...],
) -> float:
    denominator = max(
        1.0,
        sum(float(np.linalg.norm(block)) for block in force_blocks),
    )
    projected = reference.null_basis.T @ gradient.reshape(-1)
    return float(np.linalg.norm(projected) / denominator)


def _solve_step(
    current_vertices: FloatArray,
    reference: _GateAReference,
    *,
    dt: float,
    alpha: float,
) -> tuple[FloatArray, float, float, int, int, bool]:
    passive_energies, passive_force = passive_energy_force(
        current_vertices,
        reference.cell,
    )
    del passive_energies
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
        return (
            current_vertices.copy(),
            initial_residual,
            0.0,
            0,
            1,
            True,
        )

    initial_coordinates = np.zeros(
        reference.null_basis.shape[1],
        dtype=np.float64,
    )

    accepted_residual = float("inf")
    evaluated_coordinates: FloatArray | None = None

    def objective(
        coordinates: FloatArray,
    ) -> tuple[float, FloatArray]:
        nonlocal accepted_residual, evaluated_coordinates
        value, gradient, accepted_residual = _objective_and_gradient(
            coordinates,
            current_vertices,
            reference,
            dt=dt,
            alpha=alpha,
        )
        evaluated_coordinates = coordinates.copy()
        return value, gradient

    def stop_at_physical_gate(coordinates: FloatArray) -> None:
        nonlocal accepted_residual, evaluated_coordinates
        if (
            evaluated_coordinates is None
            or not np.array_equal(coordinates, evaluated_coordinates)
        ):
            _, _, accepted_residual = _objective_and_gradient(
                coordinates,
                current_vertices,
                reference,
                dt=dt,
                alpha=alpha,
            )
            evaluated_coordinates = coordinates.copy()
        if accepted_residual <= PROJECTED_RESIDUAL_LIMIT:
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
    _, passive_force = passive_energy_force(next_vertices, reference.cell)
    _, active_force, _ = active_energy_force(
        next_vertices,
        reference.active,
        alpha=alpha,
        k_f=ACTIVE_STIFFNESS,
    )
    drag_gradient = (
        DRAG / dt * reference.dual_weights[:, None] * increment
    )
    gradient = -passive_force - active_force + drag_gradient
    residual = _normalized_projected_residual(
        gradient,
        reference,
        (passive_force, active_force, drag_gradient),
    )
    gauge_residual = float(
        np.linalg.norm(reference.gauge @ increment.reshape(-1))
    )
    finite = (
        np.all(np.isfinite(next_vertices))
        and np.isfinite(residual)
        and np.isfinite(gauge_residual)
    )
    if (
        not finite
        or residual > PROJECTED_RESIDUAL_LIMIT
        or gauge_residual > GAUGE_RESIDUAL_LIMIT
    ):
        raise GateANumericalError(
            "Gate A implicit step failed without retry: "
            f"residual={residual:.6e}, gauge={gauge_residual:.6e}, "
            f"optimizer_success={result.success}, message={result.message}"
        )
    return (
        next_vertices,
        residual,
        gauge_residual,
        int(result.nit),
        int(result.nfev),
        bool(result.success),
    )


def _allocate(count: int, vertex_count: int) -> dict[str, FloatArray]:
    return {
        "vertices": np.empty((count, vertex_count, 3), dtype=np.float64),
        "alpha": np.empty(count, dtype=np.float64),
        "alpha_rate": np.empty(count, dtype=np.float64),
        "fiber_length": np.empty(count, dtype=np.float64),
        "axial_shortening": np.empty(count, dtype=np.float64),
        "transverse": np.empty((count, 2), dtype=np.float64),
        "volume_error": np.empty(count, dtype=np.float64),
        "centroid_drift": np.empty(count, dtype=np.float64),
        "passive_energy": np.empty(count, dtype=np.float64),
        "active_energy": np.empty(count, dtype=np.float64),
        "stored_energy": np.empty(count, dtype=np.float64),
        "dissipation": np.empty(count, dtype=np.float64),
        "active_power": np.empty(count, dtype=np.float64),
        "active_net_force": np.empty(count, dtype=np.float64),
        "active_net_moment": np.empty(count, dtype=np.float64),
        "projected_residual": np.empty(count, dtype=np.float64),
        "gauge_residual": np.empty(count, dtype=np.float64),
    }


def _record_node(
    storage: dict[str, FloatArray],
    index: int,
    vertices: FloatArray,
    velocity: FloatArray,
    reference: _GateAReference,
    *,
    alpha: float,
    alpha_rate: float,
    projected_residual: float,
    gauge_residual: float,
) -> None:
    passive_energies, _ = passive_energy_force(vertices, reference.cell)
    active_energy, active_force, active_state = active_energy_force(
        vertices,
        reference.active,
        alpha=alpha,
        alpha_rate=alpha_rate,
        k_f=ACTIVE_STIFFNESS,
    )
    volume, _ = surface_volume_and_gradient(vertices, reference.faces)
    centroid = weighted_centroid(vertices, reference.dual_weights)
    active_moment = np.cross(
        vertices - reference.centroid0,
        active_force,
    ).sum(axis=0)
    passive_energy = float(passive_energies["cell_total"])
    storage["vertices"][index] = vertices
    storage["alpha"][index] = alpha
    storage["alpha_rate"][index] = alpha_rate
    storage["fiber_length"][index] = active_state.length
    storage["axial_shortening"][index] = (
        1.0 - active_state.length / reference.active.length0
    )
    storage["transverse"][index] = transverse_scale_changes(
        vertices,
        reference.active,
        reference.dual_weights,
    )
    storage["volume_error"][index] = (
        volume / reference.cell.volume0 - 1.0
    )
    storage["centroid_drift"][index] = (
        np.linalg.norm(centroid - reference.centroid0)
        / reference.active.length0
    )
    storage["passive_energy"][index] = passive_energy
    storage["active_energy"][index] = active_energy
    storage["stored_energy"][index] = passive_energy + active_energy
    storage["dissipation"][index] = nodal_drag_dissipation(
        velocity,
        reference.dual_weights,
        DRAG,
    )
    storage["active_power"][index] = active_input_power(
        active_state,
        k_f=ACTIVE_STIFFNESS,
    )
    storage["active_net_force"][index] = np.linalg.norm(
        active_force.sum(axis=0)
    )
    storage["active_net_moment"][index] = np.linalg.norm(active_moment)
    storage["projected_residual"][index] = projected_residual
    storage["gauge_residual"][index] = gauge_residual


def run_gate_a_trajectory(
    case_id: str,
    *,
    dt: float,
    duration: float = 5.0,
) -> GateATrajectory:
    """Run one frozen A0 or A1 trajectory without adaptive retries."""
    if case_id not in {"A0_ZERO", "A1_ACTIVE"}:
        raise ValueError(f"unknown Gate A case: {case_id}")
    if dt not in {0.02, 0.01, 0.005}:
        raise ValueError("Gate A dt must be one of the three frozen levels")
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
        activation_protocol(time[0], alpha_peak=ACTIVE_PEAK)
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
    )
    for index in range(1, len(time)):
        alpha, alpha_rate = (
            activation_protocol(time[index], alpha_peak=ACTIVE_PEAK)
            if case_id == "A1_ACTIVE"
            else (0.0, 0.0)
        )
        next_vertices, residual, gauge_residual, nit, nfev, success = (
            _solve_step(
                current,
                reference,
                dt=dt,
                alpha=alpha,
            )
        )
        velocity = (next_vertices - current) / dt
        _record_node(
            storage,
            index,
            next_vertices,
            velocity,
            reference,
            alpha=alpha,
            alpha_rate=alpha_rate,
            projected_residual=residual,
            gauge_residual=gauge_residual,
        )
        iterations[index] = nit
        evaluations[index] = nfev
        successes[index] = success
        current = next_vertices
    return GateATrajectory(
        case_id=case_id,
        dt=dt,
        time=time,
        vertices=storage["vertices"],
        alpha=storage["alpha"],
        alpha_rate=storage["alpha_rate"],
        fiber_length=storage["fiber_length"],
        axial_shortening=storage["axial_shortening"],
        transverse_scale_change=storage["transverse"],
        volume_error=storage["volume_error"],
        centroid_drift=storage["centroid_drift"],
        passive_energy=storage["passive_energy"],
        active_energy=storage["active_energy"],
        stored_energy=storage["stored_energy"],
        dissipation=storage["dissipation"],
        active_power=storage["active_power"],
        active_net_force=storage["active_net_force"],
        active_net_moment=storage["active_net_moment"],
        projected_residual=storage["projected_residual"],
        gauge_increment_residual=storage["gauge_residual"],
        optimizer_iterations=iterations,
        optimizer_evaluations=evaluations,
        optimizer_reported_success=successes,
    )


def evaluate_gate_a_acceptance(
    trajectories: dict[str, GateATrajectory],
) -> dict[str, Any]:
    required = {
        "A0_ZERO_dt0.01",
        "A1_ACTIVE_dt0.02",
        "A1_ACTIVE_dt0.01",
        "A1_ACTIVE_dt0.005",
    }
    if set(trajectories) != required:
        raise ValueError(
            "Gate A acceptance requires exactly the frozen A0/A1 runs"
        )
    summaries = {
        key: trajectory.summary()
        for key, trajectory in trajectories.items()
    }
    zero = summaries["A0_ZERO_dt0.01"]
    base = summaries["A1_ACTIVE_dt0.01"]
    fine = summaries["A1_ACTIVE_dt0.005"]
    plateau = np.asarray(
        base["plateau_transverse_scale_changes"],
        dtype=np.float64,
    )
    refinement_names = (
        "peak_axial_shortening",
        "maximum_volume_error",
        "integrated_active_work",
        "total_dissipation",
    )
    refinement = {
        name: _relative_difference(
            float(base[name]),
            float(fine[name]),
        )
        for name in refinement_names
    }
    base_transverse = np.asarray(
        base["plateau_transverse_scale_changes"],
        dtype=np.float64,
    )
    fine_transverse = np.asarray(
        fine["plateau_transverse_scale_changes"],
        dtype=np.float64,
    )
    refinement["plateau_transverse_scale_1"] = _relative_difference(
        float(base_transverse[0]),
        float(fine_transverse[0]),
    )
    refinement["plateau_transverse_scale_2"] = _relative_difference(
        float(base_transverse[1]),
        float(fine_transverse[1]),
    )

    checks = {
        "A0_reference_zero_state": (
            float(zero["peak_axial_shortening"]) <= 1.0e-12
            and float(zero["maximum_volume_error"]) <= 1.0e-12
            and float(zero["maximum_centroid_drift"]) <= 1.0e-12
            and float(zero["integrated_power_residual"]) <= 1.0e-12
        ),
        "A1_axial_shortening": (
            0.01 <= float(base["peak_axial_shortening"]) <= 0.20
        ),
        "A1_transverse_response": (
            bool(np.all(plateau >= -1.0e-10))
            and bool(np.any(plateau > 0.01))
        ),
        "A1_volume": float(base["maximum_volume_error"]) <= 0.005,
        "A1_centroid": float(base["maximum_centroid_drift"]) <= 1.0e-4,
        "A1_active_net_force": (
            float(base["maximum_active_net_force"]) <= 1.0e-10
        ),
        "A1_active_net_moment": (
            float(base["maximum_active_net_moment"]) <= 1.0e-10
        ),
        "A1_nonnegative_dissipation": (
            float(base["minimum_dissipation"]) >= -1.0e-10
        ),
        "A1_power_residual_base": (
            float(base["integrated_power_residual"]) <= 0.005
        ),
        "A1_power_residual_fine": (
            float(fine["integrated_power_residual"]) <= 0.005
        ),
        "A1_projected_residual": (
            float(base["maximum_projected_residual"])
            <= PROJECTED_RESIDUAL_LIMIT
            and float(fine["maximum_projected_residual"])
            <= PROJECTED_RESIDUAL_LIMIT
        ),
        "A1_gauge_residual": (
            float(base["maximum_gauge_increment_residual"])
            <= GAUGE_RESIDUAL_LIMIT
            and float(fine["maximum_gauge_increment_residual"])
            <= GAUGE_RESIDUAL_LIMIT
        ),
        "A1_time_refinement": max(refinement.values()) <= 0.02,
    }
    return {
        "gate_id": "A",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "time_refinement_relative_differences": refinement,
        "summaries": summaries,
    }


def run_gate_a_suite() -> tuple[
    dict[str, GateATrajectory],
    dict[str, Any],
]:
    """Run the complete frozen Gate A suite and return its acceptance record."""
    trajectories = {
        "A0_ZERO_dt0.01": run_gate_a_trajectory(
            "A0_ZERO",
            dt=0.01,
        ),
        "A1_ACTIVE_dt0.02": run_gate_a_trajectory(
            "A1_ACTIVE",
            dt=0.02,
        ),
        "A1_ACTIVE_dt0.01": run_gate_a_trajectory(
            "A1_ACTIVE",
            dt=0.01,
        ),
        "A1_ACTIVE_dt0.005": run_gate_a_trajectory(
            "A1_ACTIVE",
            dt=0.005,
        ),
    }
    acceptance = evaluate_gate_a_acceptance(trajectories)
    return trajectories, acceptance
