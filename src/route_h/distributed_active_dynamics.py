"""Implicit overdamped dynamics for the distributed active-fibre M1 cell."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import anchor_length_axis, transverse_scale_changes
from .dcm_cell import surface_volume_and_gradient
from .displacement_controlled_cell_v02 import (
    _triangle_angles_and_gradients,
    evaluate_surface_energy,
)
from .distributed_active_cell import (
    SurfaceFiberReference,
    _group_area_ratios,
    build_surface_fiber_reference,
    distributed_fiber_energy_gradient,
)
from .geometry import triangle_geometry
from .stage2_gate_a import _build_reference
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]
TimeIntegrator = Literal["backward_euler", "crank_nicolson"]


@dataclass(frozen=True)
class AxialEnvironmentReference:
    coordinate_gradient: FloatArray
    reference_coordinate: float
    elastic_stiffness_scale: float
    viscous_coefficient_scale: float


@dataclass(frozen=True)
class AxialEnvironmentEvaluation:
    coordinate: float
    coordinate_shortening: float
    elastic_energy: float
    elastic_gradient: FloatArray
    elastic_resisting_force: float


@dataclass(frozen=True)
class DynamicActiveSample:
    step_index: int
    time: float
    activation: float
    activation_rate: float
    vertices: FloatArray
    measured_anchor_shortening: float
    transverse_scale_change: FloatArray
    volume_ratio: float
    total_area_ratio: float
    fiber_energy: float
    global_area_energy: float
    bending_energy: float
    mesh_quality_energy: float
    axial_load_coordinate: float
    axial_load_shortening: float
    external_elastic_energy: float
    external_elastic_resisting_force: float
    external_viscous_resisting_force: float
    external_total_resisting_force: float
    stored_energy: float
    cell_dissipation_rate: float
    external_viscous_dissipation_rate: float
    external_viscous_dissipation_step: float
    cumulative_external_viscous_dissipation: float
    dissipation_rate: float
    dissipation_step: float
    cumulative_dissipation: float
    algorithmic_dissipation_step: float
    cumulative_algorithmic_dissipation: float
    numerical_dissipation_step: float
    cumulative_numerical_dissipation: float
    active_work_step: float
    cumulative_active_work: float
    balance_residual_step: float
    balance_residual_cumulative: float
    volume_multiplier: float
    dynamic_kkt_residual: float
    gauge_residual: float
    active_net_force_l2: float
    active_net_moment_l2: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_success: bool
    optimizer_message: str
    geometry: GeometryDiagnostics


@dataclass(frozen=True)
class DynamicActiveRun:
    status: str
    period: float
    cycle_count: int
    steps_per_cycle: int
    time_integrator: TimeIntegrator
    drag: float
    peak_activation: float
    fiber_stiffness: float
    global_area_stiffness: float
    bending_stiffness: float
    mesh_quality_stiffness: float
    external_elastic_ratio: float
    external_viscous_ratio: float
    external_elastic_stiffness: float
    external_viscous_coefficient: float
    axial_environment_reference: AxialEnvironmentReference
    fiber_reference: SurfaceFiberReference
    samples: tuple[DynamicActiveSample, ...]


def build_axial_environment_reference(
    reference: Any,
    fibers: SurfaceFiberReference,
    *,
    drag: float,
    fiber_stiffness: float,
) -> AxialEnvironmentReference:
    """Build fixed-axis generalized load coordinates and model scales."""
    axis = reference.active.axis0
    coordinate_gradient = (
        reference.active.plus_weights - reference.active.minus_weights
    )[:, None] * axis[None, :]
    reference_coordinate = float(
        np.sum(coordinate_gradient * reference.vertices)
    )
    elastic_scale = float(
        fiber_stiffness
        * np.sum(
            fibers.support_areas
            * fibers.axial_cosine_squared
            * fibers.axial_cosine_squared
        )
        / (reference_coordinate * reference_coordinate)
    )
    weight_sum = float(reference.dual_weights.sum())
    centroid = np.sum(
        reference.dual_weights[:, None] * reference.vertices,
        axis=0,
    ) / weight_sum
    axial_positions = (reference.vertices - centroid) @ axis
    viscous_scale = float(
        drag
        * np.sum(
            reference.dual_weights
            * (axial_positions / reference_coordinate) ** 2
        )
    )
    if min(reference_coordinate, elastic_scale, viscous_scale) <= 0.0:
        raise ValueError("invalid axial environment reference scale")
    return AxialEnvironmentReference(
        coordinate_gradient=np.asarray(
            coordinate_gradient,
            dtype=np.float64,
        ),
        reference_coordinate=reference_coordinate,
        elastic_stiffness_scale=elastic_scale,
        viscous_coefficient_scale=viscous_scale,
    )


def smooth_periodic_activation(
    time: float,
    *,
    period: float,
    peak_activation: float,
) -> tuple[float, float]:
    """Return a C1-periodic 0 -> peak -> 0 activation and its rate."""
    if not np.isfinite(time) or time < 0.0:
        raise ValueError("time must be finite and nonnegative")
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and positive")
    if not np.isfinite(peak_activation) or not 0.0 < peak_activation < 1.0:
        raise ValueError("peak activation must lie strictly inside (0,1)")
    phase = math.fmod(time, period) / period
    if math.isclose(phase, 1.0, rel_tol=0.0, abs_tol=1.0e-14):
        phase = 0.0
    angle = 2.0 * math.pi * phase
    activation = 0.5 * peak_activation * (1.0 - math.cos(angle))
    activation_rate = (
        math.pi * peak_activation / period * math.sin(angle)
    )
    if abs(activation) < 1.0e-15:
        activation = 0.0
    if abs(activation_rate) < 1.0e-15:
        activation_rate = 0.0
    return float(activation), float(activation_rate)


def run_dynamic_active_cycles(
    *,
    period: float = 1.0,
    cycle_count: int = 1,
    steps_per_cycle: int = 20,
    time_integrator: TimeIntegrator = "backward_euler",
    drag: float = 1.0,
    peak_activation: float = 0.2,
    fiber_stiffness: float = 10.0,
    global_area_stiffness: float = 0.1,
    bending_stiffness: float = 0.01,
    mesh_quality_stiffness: float = 0.05,
    external_elastic_ratio: float = 0.0,
    external_viscous_ratio: float = 0.0,
) -> DynamicActiveRun:
    """Advance one or more active cycles by implicit minimizing movements."""
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and positive")
    if cycle_count <= 0 or steps_per_cycle < 4:
        raise ValueError("invalid cycle discretization")
    if steps_per_cycle % 2:
        raise ValueError("steps per cycle must be even to sample the peak")
    if time_integrator not in ("backward_euler", "crank_nicolson"):
        raise ValueError("unsupported time integrator")
    if not np.isfinite(drag) or drag <= 0.0:
        raise ValueError("drag must be finite and positive")
    if not 0.0 < peak_activation < 1.0:
        raise ValueError("peak activation must lie strictly inside (0,1)")
    if min(
        fiber_stiffness,
        global_area_stiffness,
        bending_stiffness,
        mesh_quality_stiffness,
    ) < 0.0:
        raise ValueError("stiffness values must be nonnegative")
    if fiber_stiffness <= 0.0 or mesh_quality_stiffness <= 0.0:
        raise ValueError("fiber and mesh-quality stiffnesses must be positive")
    if (
        not np.isfinite(external_elastic_ratio)
        or not np.isfinite(external_viscous_ratio)
        or external_elastic_ratio < 0.0
        or external_viscous_ratio < 0.0
    ):
        raise ValueError("external load ratios must be finite and nonnegative")

    reference = _build_reference()
    fibers = build_surface_fiber_reference(
        reference.vertices,
        reference.faces,
    )
    environment_reference = build_axial_environment_reference(
        reference,
        fibers,
        drag=drag,
        fiber_stiffness=fiber_stiffness,
    )
    external_elastic_stiffness = (
        external_elastic_ratio
        * environment_reference.elastic_stiffness_scale
    )
    external_viscous_coefficient = (
        external_viscous_ratio
        * environment_reference.viscous_coefficient_scale
    )
    reference_face_areas, _ = triangle_geometry(
        reference.vertices,
        reference.faces,
    )
    reference_angles, _ = _triangle_angles_and_gradients(
        reference.vertices[reference.faces]
    )
    basis = reference.null_basis
    coordinates = np.zeros(basis.shape[1], dtype=np.float64)
    current_vertices = reference.vertices.copy()
    dt = period / steps_per_cycle
    total_steps = cycle_count * steps_per_cycle
    times = np.linspace(0.0, cycle_count * period, total_steps + 1)

    def unpack(reduced: FloatArray) -> FloatArray:
        return reference.vertices + (basis @ reduced).reshape((-1, 3))

    def environment_evaluation(
        vertices: FloatArray,
    ) -> AxialEnvironmentEvaluation:
        coordinate = float(
            np.sum(environment_reference.coordinate_gradient * vertices)
        )
        displacement = (
            coordinate - environment_reference.reference_coordinate
        )
        elastic_energy = (
            0.5 * external_elastic_stiffness * displacement * displacement
        )
        elastic_gradient = (
            external_elastic_stiffness
            * displacement
            * environment_reference.coordinate_gradient
        )
        return AxialEnvironmentEvaluation(
            coordinate=coordinate,
            coordinate_shortening=(
                1.0
                - coordinate / environment_reference.reference_coordinate
            ),
            elastic_energy=float(elastic_energy),
            elastic_gradient=elastic_gradient,
            elastic_resisting_force=float(
                -external_elastic_stiffness * displacement
            ),
        )

    def physical_evaluations(
        vertices: FloatArray,
        activation: float,
    ) -> tuple[
        Any,
        Any,
        AxialEnvironmentEvaluation,
        FloatArray,
    ]:
        surface = evaluate_surface_energy(
            vertices,
            reference,
            global_area_stiffness=global_area_stiffness,
            bending_stiffness=bending_stiffness,
            mesh_quality_stiffness=mesh_quality_stiffness,
            reference_angles=reference_angles,
            reference_face_areas=reference_face_areas,
        )
        fiber = distributed_fiber_energy_gradient(
            vertices,
            fibers,
            activation=activation,
            stiffness=fiber_stiffness,
        )
        environment = environment_evaluation(vertices)
        return (
            surface,
            fiber,
            environment,
            surface.gradient
            + fiber.gradient
            + environment.elastic_gradient,
        )

    samples: list[DynamicActiveSample] = []
    cumulative_dissipation = 0.0
    cumulative_algorithmic_dissipation = 0.0
    cumulative_numerical_dissipation = 0.0
    cumulative_active_work = 0.0
    cumulative_external_viscous_dissipation = 0.0
    previous_activation, _ = smooth_periodic_activation(
        0.0,
        period=period,
        peak_activation=peak_activation,
    )
    (
        initial_surface,
        initial_fiber,
        initial_environment,
        initial_physical_gradient,
    ) = (
        physical_evaluations(
            current_vertices,
            previous_activation,
        )
    )
    initial_stored_energy = (
        initial_surface.total
        + initial_fiber.energy
        + initial_environment.elastic_energy
    )
    previous_stored_energy = initial_stored_energy
    previous_axial_coordinate = initial_environment.coordinate

    def constrained_multiplier_and_residual(
        dynamic_gradient: FloatArray,
        volume_gradient: FloatArray,
    ) -> tuple[float, float]:
        """Return the scalar volume reaction and normalized KKT residual."""
        constraint_gradient = basis.T @ (
            volume_gradient / reference.cell.volume0
        ).reshape(-1)
        objective_gradient = basis.T @ dynamic_gradient.reshape(-1)
        denominator = float(np.dot(constraint_gradient, constraint_gradient))
        multiplier = (
            -float(np.dot(objective_gradient, constraint_gradient))
            / denominator
            if denominator > 0.0
            else 0.0
        )
        kkt_vector = objective_gradient + multiplier * constraint_gradient
        residual = float(
            np.linalg.norm(kkt_vector)
            / max(
                1.0,
                float(np.linalg.norm(objective_gradient)),
                abs(multiplier) * float(np.linalg.norm(constraint_gradient)),
            )
        )
        return multiplier, residual

    def append_sample(
        *,
        step_index: int,
        time: float,
        activation: float,
        activation_rate: float,
        vertices: FloatArray,
        surface: Any,
        fiber: Any,
        environment: AxialEnvironmentEvaluation,
        volume: float,
        volume_gradient: FloatArray,
        dynamic_gradient: FloatArray,
        velocity: FloatArray,
        axial_velocity: float,
        cell_dissipation_rate: float,
        external_viscous_dissipation_rate: float,
        external_viscous_dissipation_step: float,
        dissipation_rate: float,
        dissipation_step: float,
        algorithmic_dissipation_step: float,
        numerical_dissipation_step: float,
        active_work_step: float,
        balance_residual_step: float,
        optimizer_iterations: int,
        optimizer_evaluations: int,
        optimizer_success: bool,
        optimizer_message: str,
    ) -> DynamicActiveSample:
        multiplier, kkt_residual = constrained_multiplier_and_residual(
            dynamic_gradient,
            volume_gradient,
        )
        length, _ = anchor_length_axis(vertices, reference.active)
        geometry = _geometry_diagnostics(vertices, reference)
        stored_energy = (
            surface.total
            + fiber.energy
            + environment.elastic_energy
        )
        external_viscous_resisting_force = (
            -external_viscous_coefficient * axial_velocity
        )
        return DynamicActiveSample(
            step_index=step_index,
            time=time,
            activation=activation,
            activation_rate=activation_rate,
            vertices=vertices.copy(),
            measured_anchor_shortening=(
                1.0 - length / reference.active.length0
            ),
            transverse_scale_change=transverse_scale_changes(
                vertices,
                reference.active,
                reference.dual_weights,
            ),
            volume_ratio=volume / reference.cell.volume0,
            total_area_ratio=surface.total_area_ratio,
            fiber_energy=fiber.energy,
            global_area_energy=surface.global_area,
            bending_energy=surface.bending,
            mesh_quality_energy=surface.mesh_quality,
            axial_load_coordinate=environment.coordinate,
            axial_load_shortening=environment.coordinate_shortening,
            external_elastic_energy=environment.elastic_energy,
            external_elastic_resisting_force=(
                environment.elastic_resisting_force
            ),
            external_viscous_resisting_force=(
                external_viscous_resisting_force
            ),
            external_total_resisting_force=(
                environment.elastic_resisting_force
                + external_viscous_resisting_force
            ),
            stored_energy=stored_energy,
            cell_dissipation_rate=cell_dissipation_rate,
            external_viscous_dissipation_rate=(
                external_viscous_dissipation_rate
            ),
            external_viscous_dissipation_step=(
                external_viscous_dissipation_step
            ),
            cumulative_external_viscous_dissipation=(
                cumulative_external_viscous_dissipation
            ),
            dissipation_rate=dissipation_rate,
            dissipation_step=dissipation_step,
            cumulative_dissipation=cumulative_dissipation,
            algorithmic_dissipation_step=algorithmic_dissipation_step,
            cumulative_algorithmic_dissipation=(
                cumulative_algorithmic_dissipation
            ),
            numerical_dissipation_step=numerical_dissipation_step,
            cumulative_numerical_dissipation=(
                cumulative_numerical_dissipation
            ),
            active_work_step=active_work_step,
            cumulative_active_work=cumulative_active_work,
            balance_residual_step=balance_residual_step,
            balance_residual_cumulative=(
                stored_energy
                - initial_stored_energy
                + cumulative_dissipation
                - cumulative_active_work
            ),
            volume_multiplier=multiplier,
            dynamic_kkt_residual=kkt_residual,
            gauge_residual=float(
                np.linalg.norm(
                    reference.gauge
                    @ (vertices - reference.vertices).reshape(-1)
                )
            ),
            active_net_force_l2=float(np.linalg.norm(fiber.net_force)),
            active_net_moment_l2=float(np.linalg.norm(fiber.net_moment)),
            optimizer_iterations=optimizer_iterations,
            optimizer_evaluations=optimizer_evaluations,
            optimizer_success=optimizer_success,
            optimizer_message=optimizer_message,
            geometry=geometry,
        )

    initial_volume, initial_volume_gradient = surface_volume_and_gradient(
        current_vertices,
        reference.faces,
    )
    previous_physical_multiplier, _ = constrained_multiplier_and_residual(
        initial_physical_gradient,
        initial_volume_gradient,
    )
    previous_physical_gradient = initial_physical_gradient
    previous_volume_gradient = initial_volume_gradient
    initial_sample = append_sample(
        step_index=0,
        time=0.0,
        activation=previous_activation,
        activation_rate=0.0,
        vertices=current_vertices,
        surface=initial_surface,
        fiber=initial_fiber,
        environment=initial_environment,
        volume=initial_volume,
        volume_gradient=initial_volume_gradient,
        dynamic_gradient=np.zeros_like(current_vertices),
        velocity=np.zeros_like(current_vertices),
        axial_velocity=0.0,
        cell_dissipation_rate=0.0,
        external_viscous_dissipation_rate=0.0,
        external_viscous_dissipation_step=0.0,
        dissipation_rate=0.0,
        dissipation_step=0.0,
        algorithmic_dissipation_step=0.0,
        numerical_dissipation_step=0.0,
        active_work_step=0.0,
        balance_residual_step=0.0,
        optimizer_iterations=0,
        optimizer_evaluations=1,
        optimizer_success=True,
        optimizer_message="reference_state",
    )
    samples.append(initial_sample)
    status = "completed"

    for step_index in range(1, total_steps + 1):
        time = float(times[step_index])
        activation, activation_rate = smooth_periodic_activation(
            time,
            period=period,
            peak_activation=peak_activation,
        )
        old_fiber_at_new_activation = distributed_fiber_energy_gradient(
            current_vertices,
            fibers,
            activation=activation,
            stiffness=fiber_stiffness,
        )
        old_fiber_at_old_activation = distributed_fiber_energy_gradient(
            current_vertices,
            fibers,
            activation=previous_activation,
            stiffness=fiber_stiffness,
        )
        if time_integrator == "backward_euler":
            active_work_step = (
                old_fiber_at_new_activation.energy
                - old_fiber_at_old_activation.energy
            )
            old_constrained_force = np.zeros_like(current_vertices)
        else:
            active_work_step = 0.0
            old_constrained_force = (
                previous_physical_gradient
                + previous_physical_multiplier
                * previous_volume_gradient
                / reference.cell.volume0
            )

        def objective(reduced: FloatArray) -> tuple[float, FloatArray]:
            vertices = unpack(reduced)
            surface, fiber, environment, gradient = physical_evaluations(
                vertices,
                activation,
            )
            increment = vertices - current_vertices
            drag_energy = 0.5 * drag / dt * float(
                np.sum(reference.dual_weights[:, None] * increment * increment)
            )
            drag_gradient = (
                drag
                / dt
                * reference.dual_weights[:, None]
                * increment
            )
            axial_increment = (
                environment.coordinate - previous_axial_coordinate
            )
            external_dashpot_energy = (
                0.5
                * external_viscous_coefficient
                / dt
                * axial_increment
                * axial_increment
            )
            external_dashpot_gradient = (
                external_viscous_coefficient
                / dt
                * axial_increment
                * environment_reference.coordinate_gradient
            )
            if time_integrator == "backward_euler":
                objective_energy = (
                    surface.total
                    + fiber.energy
                    + environment.elastic_energy
                    + drag_energy
                    + external_dashpot_energy
                )
                dynamic_gradient = (
                    gradient
                    + drag_gradient
                    + external_dashpot_gradient
                )
            else:
                objective_energy = (
                    0.5
                    * (
                        surface.total
                        + fiber.energy
                        + environment.elastic_energy
                    )
                    + 0.5 * float(np.sum(old_constrained_force * increment))
                    + drag_energy
                    + external_dashpot_energy
                )
                dynamic_gradient = (
                    0.5 * (old_constrained_force + gradient)
                    + drag_gradient
                    + external_dashpot_gradient
                )
            return (
                objective_energy,
                basis.T @ dynamic_gradient.reshape(-1),
            )

        def volume_constraint(
            reduced: FloatArray,
        ) -> tuple[float, FloatArray]:
            vertices = unpack(reduced)
            volume, gradient = surface_volume_and_gradient(
                vertices,
                reference.faces,
            )
            return (
                volume / reference.cell.volume0 - 1.0,
                basis.T
                @ (gradient / reference.cell.volume0).reshape(-1),
            )

        result = minimize(
            objective,
            coordinates,
            method="SLSQP",
            jac=True,
            constraints=(
                {
                    "type": "eq",
                    "fun": lambda reduced: volume_constraint(reduced)[0],
                    "jac": lambda reduced: volume_constraint(reduced)[1],
                },
            ),
            options={
                "maxiter": (
                    1500
                    if time_integrator == "crank_nicolson"
                    else 1000
                ),
                "ftol": (
                    1.0e-13
                    if time_integrator == "crank_nicolson"
                    else 1.0e-12
                ),
                "disp": False,
            },
        )
        coordinates = np.asarray(result.x, dtype=np.float64)
        vertices = unpack(coordinates)
        (
            surface,
            fiber,
            environment,
            physical_gradient,
        ) = physical_evaluations(vertices, activation)
        velocity = (vertices - current_vertices) / dt
        drag_gradient = drag * reference.dual_weights[:, None] * velocity
        axial_velocity = (
            environment.coordinate - previous_axial_coordinate
        ) / dt
        external_dashpot_gradient = (
            external_viscous_coefficient
            * axial_velocity
            * environment_reference.coordinate_gradient
        )
        if time_integrator == "backward_euler":
            dynamic_gradient = (
                physical_gradient
                + drag_gradient
                + external_dashpot_gradient
            )
        else:
            dynamic_gradient = (
                0.5 * (old_constrained_force + physical_gradient)
                + drag_gradient
                + external_dashpot_gradient
            )
            active_work_step = (
                0.5
                * (activation - previous_activation)
                * (
                    old_fiber_at_old_activation.activation_derivative
                    + fiber.activation_derivative
                )
            )
        cell_dissipation_rate = drag * float(
            np.sum(reference.dual_weights[:, None] * velocity * velocity)
        )
        external_viscous_dissipation_rate = (
            external_viscous_coefficient
            * axial_velocity
            * axial_velocity
        )
        dissipation_rate = (
            cell_dissipation_rate
            + external_viscous_dissipation_rate
        )
        dissipation_step = dissipation_rate * dt
        external_viscous_dissipation_step = (
            external_viscous_dissipation_rate * dt
        )
        cumulative_dissipation += dissipation_step
        cumulative_external_viscous_dissipation += (
            external_viscous_dissipation_step
        )
        cumulative_active_work += active_work_step
        stored_energy = (
            surface.total
            + fiber.energy
            + environment.elastic_energy
        )
        if time_integrator == "backward_euler":
            old_surface_energy = (
                previous_stored_energy
                - old_fiber_at_old_activation.energy
            )
            algorithmic_dissipation_step = (
                old_surface_energy
                + old_fiber_at_new_activation.energy
                - stored_energy
            )
        else:
            algorithmic_dissipation_step = (
                previous_stored_energy + active_work_step - stored_energy
            )
        numerical_dissipation_step = (
            algorithmic_dissipation_step - dissipation_step
        )
        cumulative_algorithmic_dissipation += (
            algorithmic_dissipation_step
        )
        cumulative_numerical_dissipation += numerical_dissipation_step
        balance_residual_step = (
            stored_energy
            - previous_stored_energy
            + dissipation_step
            - active_work_step
        )
        volume, volume_gradient = surface_volume_and_gradient(
            vertices,
            reference.faces,
        )
        sample = append_sample(
            step_index=step_index,
            time=time,
            activation=activation,
            activation_rate=activation_rate,
            vertices=vertices,
            surface=surface,
            fiber=fiber,
            environment=environment,
            volume=volume,
            volume_gradient=volume_gradient,
            dynamic_gradient=dynamic_gradient,
            velocity=velocity,
            axial_velocity=axial_velocity,
            cell_dissipation_rate=cell_dissipation_rate,
            external_viscous_dissipation_rate=(
                external_viscous_dissipation_rate
            ),
            external_viscous_dissipation_step=(
                external_viscous_dissipation_step
            ),
            dissipation_rate=dissipation_rate,
            dissipation_step=dissipation_step,
            algorithmic_dissipation_step=(
                algorithmic_dissipation_step
            ),
            numerical_dissipation_step=numerical_dissipation_step,
            active_work_step=active_work_step,
            balance_residual_step=balance_residual_step,
            optimizer_iterations=int(result.nit),
            optimizer_evaluations=int(result.nfev),
            optimizer_success=bool(result.success),
            optimizer_message=str(result.message),
        )
        samples.append(sample)
        energy_terms_valid = bool(
            np.isfinite(dissipation_step)
            and np.isfinite(algorithmic_dissipation_step)
            and np.isfinite(numerical_dissipation_step)
            and (
                time_integrator == "crank_nicolson"
                or (
                    sample.algorithmic_dissipation_step >= -1.0e-10
                    and sample.numerical_dissipation_step >= -1.0e-8
                )
            )
        )
        valid = bool(
            result.success
            and sample.dissipation_rate >= 0.0
            and energy_terms_valid
            and abs(sample.volume_ratio - 1.0) <= 1.0e-8
            and sample.geometry.finite
            and sample.geometry.signed_volume > 0.0
            and sample.geometry.minimum_face_area_ratio >= 0.05
            and sample.geometry.minimum_orientation_cosine > 0.0
            and sample.geometry.flipped_face_count == 0
            and sample.geometry.degenerate_face_count == 0
            and sample.dynamic_kkt_residual <= 1.0e-5
            and sample.gauge_residual <= 1.0e-10
            and sample.active_net_force_l2 <= 1.0e-10
            and sample.active_net_moment_l2 <= 1.0e-10
        )
        if not valid:
            status = "failed_physical_or_numerical_gate"
            break
        current_vertices = vertices
        previous_activation = activation
        previous_stored_energy = stored_energy
        previous_axial_coordinate = environment.coordinate
        previous_physical_gradient = physical_gradient
        previous_volume_gradient = volume_gradient
        previous_physical_multiplier = (
            sample.volume_multiplier
            if time_integrator == "backward_euler"
            else 2.0 * sample.volume_multiplier
        )

    if samples[-1].step_index != total_steps:
        status = "failed_before_cycle_end"
    return DynamicActiveRun(
        status=status,
        period=period,
        cycle_count=cycle_count,
        steps_per_cycle=steps_per_cycle,
        time_integrator=time_integrator,
        drag=drag,
        peak_activation=peak_activation,
        fiber_stiffness=fiber_stiffness,
        global_area_stiffness=global_area_stiffness,
        bending_stiffness=bending_stiffness,
        mesh_quality_stiffness=mesh_quality_stiffness,
        external_elastic_ratio=external_elastic_ratio,
        external_viscous_ratio=external_viscous_ratio,
        external_elastic_stiffness=external_elastic_stiffness,
        external_viscous_coefficient=external_viscous_coefficient,
        axial_environment_reference=environment_reference,
        fiber_reference=fibers,
        samples=tuple(samples),
    )
