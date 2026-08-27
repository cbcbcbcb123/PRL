"""Distributed active-fibre equilibrium for the M1 surface cell.

The active material is represented by an anisotropic preferred metric on
all unique surface edges.  It replaces the single end-to-end active spring
while retaining exact volume conservation and a six-mode rigid-body gauge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import anchor_length_axis, transverse_scale_changes
from .dcm_cell import surface_volume_and_gradient
from .displacement_controlled_cell_v02 import evaluate_surface_energy
from .geometry import triangle_geometry
from .stage2_gate_a import _build_reference
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class SurfaceFiberReference:
    edges: IntArray
    reference_lengths: FloatArray
    axial_cosine_squared: FloatArray
    support_areas: FloatArray
    direction: FloatArray


@dataclass(frozen=True)
class FiberEnergyEvaluation:
    energy: float
    gradient: FloatArray
    preferred_length_ratios: FloatArray
    strains: FloatArray
    activation_derivative: float
    net_force: FloatArray
    net_moment: FloatArray


@dataclass(frozen=True)
class DistributedActiveSample:
    step_index: int
    branch: str
    activation: float
    vertices: FloatArray
    measured_anchor_shortening: float
    transverse_scale_change: FloatArray
    volume_ratio: float
    total_area_ratio: float
    area_group_ratios: FloatArray
    fiber_energy: float
    global_area_energy: float
    bending_energy: float
    mesh_quality_energy: float
    activation_energy_derivative: float
    active_net_force_l2: float
    active_net_moment_l2: float
    volume_multiplier: float
    kkt_residual: float
    gauge_residual: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_success: bool
    optimizer_message: str
    geometry: GeometryDiagnostics


@dataclass(frozen=True)
class DistributedActiveCycle:
    status: str
    peak_activation: float
    fiber_stiffness: float
    global_area_stiffness: float
    bending_stiffness: float
    mesh_quality_stiffness: float
    fiber_reference: SurfaceFiberReference
    samples: tuple[DistributedActiveSample, ...]


def build_surface_fiber_reference(
    vertices: FloatArray,
    faces: IntArray,
    *,
    direction: FloatArray | None = None,
) -> SurfaceFiberReference:
    """Build a mesh-consistent distributed axial fibre reference."""
    fiber_direction = np.asarray(
        [1.0, 0.0, 0.0] if direction is None else direction,
        dtype=np.float64,
    )
    norm = float(np.linalg.norm(fiber_direction))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("fiber direction must be finite and nonzero")
    fiber_direction = fiber_direction / norm

    face_edges = np.stack(
        (faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]),
        axis=1,
    )
    edge_occurrences = np.sort(face_edges.reshape((-1, 2)), axis=1)
    edges, inverse = np.unique(
        edge_occurrences,
        axis=0,
        return_inverse=True,
    )
    face_areas, _ = triangle_geometry(vertices, faces)
    support_areas = np.zeros(len(edges), dtype=np.float64)
    np.add.at(
        support_areas,
        inverse,
        np.repeat(face_areas / 3.0, 3),
    )
    vectors = vertices[edges[:, 1]] - vertices[edges[:, 0]]
    lengths = np.linalg.norm(vectors, axis=1)
    if np.any(lengths <= 0.0) or np.any(support_areas <= 0.0):
        raise ValueError("fiber reference contains a degenerate edge")
    axial_cosine_squared = (
        (vectors @ fiber_direction) / lengths
    ) ** 2
    return SurfaceFiberReference(
        edges=np.asarray(edges, dtype=np.int64),
        reference_lengths=np.asarray(lengths, dtype=np.float64),
        axial_cosine_squared=np.asarray(
            axial_cosine_squared,
            dtype=np.float64,
        ),
        support_areas=support_areas,
        direction=fiber_direction,
    )


def distributed_fiber_energy_gradient(
    vertices: FloatArray,
    reference: SurfaceFiberReference,
    *,
    activation: float,
    stiffness: float,
) -> FiberEnergyEvaluation:
    """Evaluate an axial active-strain metric on all surface edges."""
    if not np.isfinite(activation) or not 0.0 <= activation < 1.0:
        raise ValueError("activation must lie in [0,1)")
    if not np.isfinite(stiffness) or stiffness < 0.0:
        raise ValueError("fiber stiffness must be finite and nonnegative")

    edges = reference.edges
    vectors = vertices[edges[:, 1]] - vertices[edges[:, 0]]
    lengths = np.linalg.norm(vectors, axis=1)
    if np.any(lengths <= 0.0):
        raise ValueError("current fiber edge became degenerate")
    contraction_factor = 2.0 * activation - activation * activation
    preferred = np.sqrt(
        1.0 - contraction_factor * reference.axial_cosine_squared
    )
    strains = lengths / reference.reference_lengths - preferred
    energy = 0.5 * stiffness * float(
        np.sum(reference.support_areas * strains * strains)
    )

    coefficients = (
        stiffness
        * reference.support_areas
        * strains
        / reference.reference_lengths
    )
    pair_gradients = coefficients[:, None] * vectors / lengths[:, None]
    gradient = np.zeros_like(vertices)
    np.add.at(gradient, edges[:, 0], -pair_gradients)
    np.add.at(gradient, edges[:, 1], pair_gradients)

    preferred_derivative = (
        -(1.0 - activation)
        * reference.axial_cosine_squared
        / preferred
    )
    activation_derivative = -stiffness * float(
        np.sum(
            reference.support_areas
            * strains
            * preferred_derivative
        )
    )
    force = -gradient
    net_force = force.sum(axis=0)
    net_moment = np.cross(vertices, force).sum(axis=0)
    return FiberEnergyEvaluation(
        energy=energy,
        gradient=gradient,
        preferred_length_ratios=preferred,
        strains=strains,
        activation_derivative=activation_derivative,
        net_force=net_force,
        net_moment=net_moment,
    )


def _group_area_ratios(vertices: FloatArray, reference: Any) -> FloatArray:
    face_areas, _ = triangle_geometry(vertices, reference.faces)
    codes = reference.cell.primary * 10 + reference.cell.directional
    return np.asarray(
        [
            face_areas[codes == key].sum()
            for key in reference.cell.area_group_keys
        ],
        dtype=np.float64,
    ) / reference.cell.area0


def run_distributed_active_cycle(
    *,
    peak_activation: float = 0.2,
    loading_steps: int = 10,
    unloading_steps: int = 10,
    fiber_stiffness: float = 10.0,
    global_area_stiffness: float = 0.1,
    bending_stiffness: float = 0.01,
    mesh_quality_stiffness: float = 0.05,
) -> DistributedActiveCycle:
    """Solve a quasi-static active contraction and relaxation cycle."""
    if not 0.0 < peak_activation < 1.0:
        raise ValueError("peak activation must lie strictly inside (0,1)")
    if loading_steps <= 0 or unloading_steps < 0:
        raise ValueError("invalid activation step counts")
    if min(
        fiber_stiffness,
        global_area_stiffness,
        bending_stiffness,
        mesh_quality_stiffness,
    ) < 0.0:
        raise ValueError("stiffness values must be nonnegative")
    if fiber_stiffness <= 0.0 or mesh_quality_stiffness <= 0.0:
        raise ValueError("fiber and mesh-quality stiffnesses must be positive")

    reference = _build_reference()
    fiber_reference = build_surface_fiber_reference(
        reference.vertices,
        reference.faces,
    )
    reference_face_areas, _ = triangle_geometry(
        reference.vertices,
        reference.faces,
    )
    from .displacement_controlled_cell_v02 import (  # local cycle breaker
        _triangle_angles_and_gradients,
    )

    reference_angles, _ = _triangle_angles_and_gradients(
        reference.vertices[reference.faces]
    )
    load_levels = np.linspace(0.0, peak_activation, loading_steps + 1)
    if unloading_steps:
        unload_levels = np.linspace(
            peak_activation,
            0.0,
            unloading_steps + 1,
        )[1:]
        activation_levels = np.concatenate((load_levels, unload_levels))
        branches = (
            ["loading"] * len(load_levels)
            + ["unloading"] * len(unload_levels)
        )
    else:
        activation_levels = load_levels
        branches = ["loading"] * len(load_levels)

    basis = reference.null_basis
    coordinates = np.zeros(basis.shape[1], dtype=np.float64)

    def unpack(reduced: FloatArray) -> FloatArray:
        return reference.vertices + (basis @ reduced).reshape((-1, 3))

    def evaluations(
        reduced: FloatArray,
        activation: float,
    ) -> tuple[Any, FiberEnergyEvaluation, FloatArray]:
        vertices = unpack(reduced)
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
            fiber_reference,
            activation=activation,
            stiffness=fiber_stiffness,
        )
        gradient = surface.gradient + fiber.gradient
        return surface, fiber, gradient

    samples: list[DistributedActiveSample] = []
    status = "completed"
    for step_index, (activation_value, branch) in enumerate(
        zip(activation_levels, branches, strict=True)
    ):
        activation = float(activation_value)

        def objective(reduced: FloatArray) -> tuple[float, FloatArray]:
            surface, fiber, gradient = evaluations(reduced, activation)
            return (
                surface.total + fiber.energy,
                basis.T @ gradient.reshape(-1),
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

        if step_index == 0:
            optimizer_success = True
            optimizer_message = "reference_state"
            optimizer_iterations = 0
            optimizer_evaluations = 1
        else:
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
                    "maxiter": 1000,
                    "ftol": 1.0e-12,
                    "disp": False,
                },
            )
            coordinates = np.asarray(result.x, dtype=np.float64)
            optimizer_success = bool(result.success)
            optimizer_message = str(result.message)
            optimizer_iterations = int(result.nit)
            optimizer_evaluations = int(result.nfev)

        vertices = unpack(coordinates)
        surface, fiber, gradient = evaluations(coordinates, activation)
        volume, volume_gradient = surface_volume_and_gradient(
            vertices,
            reference.faces,
        )
        objective_gradient = basis.T @ gradient.reshape(-1)
        constraint_gradient = basis.T @ (
            volume_gradient / reference.cell.volume0
        ).reshape(-1)
        denominator = float(np.dot(constraint_gradient, constraint_gradient))
        multiplier = (
            -float(np.dot(objective_gradient, constraint_gradient))
            / denominator
            if denominator > 0.0
            else 0.0
        )
        kkt_vector = objective_gradient + multiplier * constraint_gradient
        kkt_residual = float(
            np.linalg.norm(kkt_vector)
            / max(
                1.0,
                float(np.linalg.norm(objective_gradient)),
                abs(multiplier) * float(np.linalg.norm(constraint_gradient)),
            )
        )
        length, _ = anchor_length_axis(vertices, reference.active)
        geometry = _geometry_diagnostics(vertices, reference)
        gauge_residual = float(
            np.linalg.norm(
                reference.gauge
                @ (vertices - reference.vertices).reshape(-1)
            )
        )
        sample = DistributedActiveSample(
            step_index=step_index,
            branch=branch,
            activation=activation,
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
            area_group_ratios=_group_area_ratios(vertices, reference),
            fiber_energy=fiber.energy,
            global_area_energy=surface.global_area,
            bending_energy=surface.bending,
            mesh_quality_energy=surface.mesh_quality,
            activation_energy_derivative=fiber.activation_derivative,
            active_net_force_l2=float(np.linalg.norm(fiber.net_force)),
            active_net_moment_l2=float(np.linalg.norm(fiber.net_moment)),
            volume_multiplier=multiplier,
            kkt_residual=kkt_residual,
            gauge_residual=gauge_residual,
            optimizer_iterations=optimizer_iterations,
            optimizer_evaluations=optimizer_evaluations,
            optimizer_success=optimizer_success,
            optimizer_message=optimizer_message,
            geometry=geometry,
        )
        samples.append(sample)
        valid = bool(
            optimizer_success
            and abs(sample.volume_ratio - 1.0) <= 1.0e-8
            and sample.geometry.finite
            and sample.geometry.signed_volume > 0.0
            and sample.geometry.minimum_face_area_ratio >= 0.05
            and sample.geometry.minimum_orientation_cosine > 0.0
            and sample.geometry.flipped_face_count == 0
            and sample.geometry.degenerate_face_count == 0
            and sample.kkt_residual <= 1.0e-5
            and sample.gauge_residual <= 1.0e-10
            and sample.active_net_force_l2 <= 1.0e-10
            and sample.active_net_moment_l2 <= 1.0e-10
        )
        if not valid:
            status = "failed_physical_or_numerical_gate"
            break

    if samples[-1].activation != float(activation_levels[-1]):
        status = "failed_before_cycle_end"
    return DistributedActiveCycle(
        status=status,
        peak_activation=peak_activation,
        fiber_stiffness=fiber_stiffness,
        global_area_stiffness=global_area_stiffness,
        bending_stiffness=bending_stiffness,
        mesh_quality_stiffness=mesh_quality_stiffness,
        fiber_reference=fiber_reference,
        samples=tuple(samples),
    )
