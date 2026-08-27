"""Well-posed displacement-controlled M1 surface equilibrium.

The model separates three roles that were previously conflated:

* one soft global surface-area elasticity term;
* reference-angle mesh regularization, invariant to uniform triangle scaling;
* an exact enclosed-volume equality constraint.

The registered end patches follow a prescribed isochoric affine boundary
motion. Interior vertices are equilibrated by constrained minimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import anchor_length_axis
from .dcm_cell import (
    _triangle_area_gradients_bulk,
    bending_energy_gradient,
    surface_volume_and_gradient,
)
from .geometry import triangle_geometry
from .stage2_gate_a import _build_reference
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class SurfaceEnergyEvaluation:
    total: float
    global_area: float
    bending: float
    mesh_quality: float
    gradient: FloatArray
    total_area_ratio: float


@dataclass(frozen=True)
class DisplacementEquilibriumSample:
    imposed_shortening: float
    measured_anchor_shortening: float
    transverse_boundary_stretch: float
    vertices: FloatArray
    volume_ratio: float
    total_area_ratio: float
    area_group_ratios: FloatArray
    global_area_energy: float
    bending_energy: float
    mesh_quality_energy: float
    volume_multiplier: float
    kkt_residual: float
    boundary_reaction_axial: float
    boundary_reaction_l2: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_success: bool
    optimizer_message: str
    geometry: GeometryDiagnostics


@dataclass(frozen=True)
class DisplacementEquilibriumRun:
    status: str
    target_shortening: float
    global_area_stiffness: float
    bending_stiffness: float
    mesh_quality_stiffness: float
    fixed_vertex_ids: IntArray
    samples: tuple[DisplacementEquilibriumSample, ...]


def global_area_energy_gradient(
    vertices: FloatArray,
    faces: IntArray,
    reference_total_area: float,
    stiffness: float,
) -> tuple[float, FloatArray, float]:
    """Return one total-area penalty rather than regional penalties."""
    if reference_total_area <= 0.0:
        raise ValueError("reference total area must be positive")
    face_areas, local_gradients = _triangle_area_gradients_bulk(
        vertices[faces]
    )
    total_area = float(face_areas.sum())
    strain = total_area / reference_total_area - 1.0
    energy = 0.5 * stiffness * reference_total_area * strain * strain
    gradient = np.zeros_like(vertices)
    np.add.at(
        gradient,
        faces.reshape(-1),
        (stiffness * strain * local_gradients).reshape(-1, 3),
    )
    return float(energy), gradient, total_area / reference_total_area


def _triangle_angles_and_gradients(
    triangles: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    """Return face angles and d(angle)/d(local vertex coordinates)."""
    face_count = len(triangles)
    angles = np.empty((face_count, 3), dtype=np.float64)
    gradients = np.zeros((face_count, 3, 3, 3), dtype=np.float64)
    for angle_id in range(3):
        centre_id = angle_id
        first_id = (angle_id + 1) % 3
        second_id = (angle_id + 2) % 3
        centre = triangles[:, centre_id]
        first = triangles[:, first_id]
        second = triangles[:, second_id]
        first_edge = first - centre
        second_edge = second - centre
        first_length = np.linalg.norm(first_edge, axis=1)
        second_length = np.linalg.norm(second_edge, axis=1)
        if np.any(first_length <= 0.0) or np.any(second_length <= 0.0):
            raise ValueError("mesh-quality energy encountered a zero edge")
        first_unit = first_edge / first_length[:, None]
        second_unit = second_edge / second_length[:, None]
        cosine = np.sum(first_unit * second_unit, axis=1)
        cosine = np.clip(cosine, -1.0 + 1.0e-12, 1.0 - 1.0e-12)
        sine = np.sqrt(np.maximum(1.0 - cosine * cosine, 1.0e-24))
        angles[:, angle_id] = np.arccos(cosine)
        first_gradient = -(
            second_unit - cosine[:, None] * first_unit
        ) / (first_length * sine)[:, None]
        second_gradient = -(
            first_unit - cosine[:, None] * second_unit
        ) / (second_length * sine)[:, None]
        gradients[:, angle_id, first_id] = first_gradient
        gradients[:, angle_id, second_id] = second_gradient
        gradients[:, angle_id, centre_id] = -(
            first_gradient + second_gradient
        )
    return angles, gradients


def mesh_quality_energy_gradient(
    vertices: FloatArray,
    faces: IntArray,
    reference_angles: FloatArray,
    reference_face_areas: FloatArray,
    stiffness: float,
) -> tuple[float, FloatArray]:
    """Penalize angle distortion without penalizing uniform area changes."""
    angles, angle_gradients = _triangle_angles_and_gradients(vertices[faces])
    if angles.shape != reference_angles.shape:
        raise ValueError("reference angles do not match the surface mesh")
    delta = angles - reference_angles
    energy = float(
        0.5
        * stiffness
        * np.sum(reference_face_areas[:, None] * delta * delta)
    )
    local_gradient = np.sum(
        (
            stiffness
            * reference_face_areas[:, None]
            * delta
        )[:, :, None, None]
        * angle_gradients,
        axis=1,
    )
    gradient = np.zeros_like(vertices)
    np.add.at(
        gradient,
        faces.reshape(-1),
        local_gradient.reshape(-1, 3),
    )
    return energy, gradient


def evaluate_surface_energy(
    vertices: FloatArray,
    reference: Any,
    *,
    global_area_stiffness: float,
    bending_stiffness: float,
    mesh_quality_stiffness: float,
    reference_angles: FloatArray,
    reference_face_areas: FloatArray,
) -> SurfaceEnergyEvaluation:
    area, area_gradient, area_ratio = global_area_energy_gradient(
        vertices,
        reference.faces,
        float(reference.cell.area0.sum()),
        global_area_stiffness,
    )
    bending, bending_gradient = bending_energy_gradient(
        vertices,
        reference.cell,
        bending_stiffness,
    )
    quality, quality_gradient = mesh_quality_energy_gradient(
        vertices,
        reference.faces,
        reference_angles,
        reference_face_areas,
        mesh_quality_stiffness,
    )
    return SurfaceEnergyEvaluation(
        total=area + bending + quality,
        global_area=area,
        bending=bending,
        mesh_quality=quality,
        gradient=area_gradient + bending_gradient + quality_gradient,
        total_area_ratio=area_ratio,
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


def _affine_isochoric_map(
    vertices: FloatArray,
    centre: FloatArray,
    previous_shortening: float,
    next_shortening: float,
) -> FloatArray:
    axial_increment = (
        (1.0 - next_shortening) / (1.0 - previous_shortening)
    )
    transverse_increment = 1.0 / np.sqrt(axial_increment)
    transform = np.diag(
        [axial_increment, transverse_increment, transverse_increment]
    )
    return (vertices - centre) @ transform.T + centre


def run_displacement_equilibrium_v02(
    *,
    target_shortening: float = 0.2,
    step_count: int = 10,
    global_area_stiffness: float = 0.1,
    bending_stiffness: float = 0.01,
    mesh_quality_stiffness: float = 0.05,
) -> DisplacementEquilibriumRun:
    """Equilibrate the cell interior under exact-volume displacement loading."""
    if not 0.0 < target_shortening < 1.0:
        raise ValueError("target shortening must lie strictly inside (0,1)")
    if step_count <= 0:
        raise ValueError("step count must be positive")
    if min(
        global_area_stiffness,
        bending_stiffness,
        mesh_quality_stiffness,
    ) < 0.0:
        raise ValueError("surface stiffnesses must be nonnegative")
    if mesh_quality_stiffness <= 0.0:
        raise ValueError("mesh-quality stiffness must remain positive")

    reference = _build_reference()
    reference_face_areas, _ = triangle_geometry(
        reference.vertices,
        reference.faces,
    )
    reference_angles, _ = _triangle_angles_and_gradients(
        reference.vertices[reference.faces]
    )
    minus_ids = np.flatnonzero(reference.active.minus_weights > 0.0)
    plus_ids = np.flatnonzero(reference.active.plus_weights > 0.0)
    fixed_ids = np.unique(np.concatenate((minus_ids, plus_ids))).astype(
        np.int64
    )
    all_ids = np.arange(len(reference.vertices), dtype=np.int64)
    free_ids = np.setdiff1d(all_ids, fixed_ids, assume_unique=True)
    centre = 0.5 * (
        reference.active.minus_weights @ reference.vertices
        + reference.active.plus_weights @ reference.vertices
    )

    def make_sample(
        vertices: FloatArray,
        *,
        shortening: float,
        optimizer_iterations: int,
        optimizer_evaluations: int,
        optimizer_success: bool,
        optimizer_message: str,
    ) -> DisplacementEquilibriumSample:
        evaluation = evaluate_surface_energy(
            vertices,
            reference,
            global_area_stiffness=global_area_stiffness,
            bending_stiffness=bending_stiffness,
            mesh_quality_stiffness=mesh_quality_stiffness,
            reference_angles=reference_angles,
            reference_face_areas=reference_face_areas,
        )
        volume, volume_gradient = surface_volume_and_gradient(
            vertices,
            reference.faces,
        )
        constraint_gradient = (
            volume_gradient[free_ids].reshape(-1)
            / reference.cell.volume0
        )
        objective_gradient = evaluation.gradient[free_ids].reshape(-1)
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
        full_reaction_gradient = (
            evaluation.gradient
            + multiplier * volume_gradient / reference.cell.volume0
        )
        fixed_reaction = -full_reaction_gradient[fixed_ids]
        plus_mask = np.isin(fixed_ids, plus_ids)
        plus_axial_reaction = float(fixed_reaction[plus_mask, 0].sum())
        length, _ = anchor_length_axis(vertices, reference.active)
        geometry = _geometry_diagnostics(vertices, reference)
        return DisplacementEquilibriumSample(
            imposed_shortening=shortening,
            measured_anchor_shortening=(
                1.0 - length / reference.active.length0
            ),
            transverse_boundary_stretch=(
                1.0 / np.sqrt(1.0 - shortening)
            ),
            vertices=vertices.copy(),
            volume_ratio=volume / reference.cell.volume0,
            total_area_ratio=evaluation.total_area_ratio,
            area_group_ratios=_group_area_ratios(vertices, reference),
            global_area_energy=evaluation.global_area,
            bending_energy=evaluation.bending,
            mesh_quality_energy=evaluation.mesh_quality,
            volume_multiplier=multiplier,
            kkt_residual=kkt_residual,
            boundary_reaction_axial=plus_axial_reaction,
            boundary_reaction_l2=float(np.linalg.norm(fixed_reaction)),
            optimizer_iterations=optimizer_iterations,
            optimizer_evaluations=optimizer_evaluations,
            optimizer_success=optimizer_success,
            optimizer_message=optimizer_message,
            geometry=geometry,
        )

    current = reference.vertices.copy()
    samples = [
        make_sample(
            current,
            shortening=0.0,
            optimizer_iterations=0,
            optimizer_evaluations=1,
            optimizer_success=True,
            optimizer_message="reference_state",
        )
    ]
    previous_shortening = 0.0
    status = "completed"
    for shortening_value in np.linspace(
        target_shortening / step_count,
        target_shortening,
        step_count,
    ):
        shortening = float(shortening_value)
        initial = _affine_isochoric_map(
            current,
            centre,
            previous_shortening,
            shortening,
        )
        boundary = _affine_isochoric_map(
            reference.vertices[fixed_ids],
            centre,
            0.0,
            shortening,
        )
        initial[fixed_ids] = boundary

        def unpack(coordinates: FloatArray) -> FloatArray:
            vertices = initial.copy()
            vertices[free_ids] = coordinates.reshape((-1, 3))
            vertices[fixed_ids] = boundary
            return vertices

        def objective(coordinates: FloatArray) -> tuple[float, FloatArray]:
            vertices = unpack(coordinates)
            evaluation = evaluate_surface_energy(
                vertices,
                reference,
                global_area_stiffness=global_area_stiffness,
                bending_stiffness=bending_stiffness,
                mesh_quality_stiffness=mesh_quality_stiffness,
                reference_angles=reference_angles,
                reference_face_areas=reference_face_areas,
            )
            return evaluation.total, evaluation.gradient[free_ids].reshape(-1)

        def volume_constraint(
            coordinates: FloatArray,
        ) -> tuple[float, FloatArray]:
            vertices = unpack(coordinates)
            volume, gradient = surface_volume_and_gradient(
                vertices,
                reference.faces,
            )
            return (
                volume / reference.cell.volume0 - 1.0,
                gradient[free_ids].reshape(-1) / reference.cell.volume0,
            )

        result = minimize(
            objective,
            initial[free_ids].reshape(-1),
            method="SLSQP",
            jac=True,
            constraints=(
                {
                    "type": "eq",
                    "fun": lambda coordinates: volume_constraint(coordinates)[0],
                    "jac": lambda coordinates: volume_constraint(coordinates)[1],
                },
            ),
            options={
                "maxiter": 1000,
                "ftol": 1.0e-12,
                "disp": False,
            },
        )
        candidate = unpack(np.asarray(result.x, dtype=np.float64))
        sample = make_sample(
            candidate,
            shortening=shortening,
            optimizer_iterations=int(result.nit),
            optimizer_evaluations=int(result.nfev),
            optimizer_success=bool(result.success),
            optimizer_message=str(result.message),
        )
        samples.append(sample)
        valid = bool(
            abs(sample.volume_ratio - 1.0) <= 1.0e-8
            and sample.geometry.finite
            and sample.geometry.signed_volume > 0.0
            and sample.geometry.minimum_face_area_ratio >= 0.05
            and sample.geometry.minimum_orientation_cosine > 0.0
            and sample.geometry.flipped_face_count == 0
            and sample.geometry.degenerate_face_count == 0
            and sample.kkt_residual <= 1.0e-5
        )
        if not valid:
            status = "failed_physical_or_geometry_gate"
            break
        current = candidate
        previous_shortening = shortening

    if samples[-1].imposed_shortening < target_shortening:
        status = "failed_before_target"
    return DisplacementEquilibriumRun(
        status=status,
        target_shortening=target_shortening,
        global_area_stiffness=global_area_stiffness,
        bending_stiffness=bending_stiffness,
        mesh_quality_stiffness=mesh_quality_stiffness,
        fixed_vertex_ids=fixed_ids,
        samples=tuple(samples),
    )
