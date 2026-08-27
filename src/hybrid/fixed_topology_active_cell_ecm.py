"""Fixed-topology active DCM cell coupled to explicit tetrahedral ECM patches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import lsq_linear, minimize

from route_h.activation import anchor_length_axis
from route_h.dcm_cell import surface_volume_and_gradient
from route_h.displacement_controlled_cell_v02 import (
    _triangle_angles_and_gradients,
    evaluate_surface_energy,
)
from route_h.distributed_active_cell import (
    SurfaceFiberReference,
    build_surface_fiber_reference,
    distributed_fiber_energy_gradient,
)
from route_h.ecm_finite_strain import (
    ECMReference,
    build_ecm_reference,
    ecm_energy_force,
)
from route_h.geometry import triangle_geometry
from route_h.stage2_gate_a import _build_reference
from route_h.stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)

from .cell_ecm_coupling import (
    CellECMVerticalSlice,
    VerticalSliceEvaluation,
    build_cell_ecm_tether,
)
from .remesh_registry import SurfaceMaterialRegistry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Topology = Literal["basal", "apical", "symmetric"]


@dataclass(frozen=True)
class PatchMesh:
    vertices: FloatArray
    tetrahedra: IntArray
    interface_faces: IntArray
    fixed_vertex_ids: IntArray
    side: str


@dataclass(frozen=True)
class FixedTopologyModel:
    topology: Topology
    cell_reference: Any
    fiber_reference: SurfaceFiberReference
    reference_angles: FloatArray
    reference_face_areas: FloatArray
    vertical_slice: CellECMVerticalSlice
    ecm_fixed_vertex_ids: IntArray
    ecm_free_vertex_ids: IntArray
    tether_weight_sum: float
    contact_polarity_y: float
    fiber_stiffness: float
    global_area_stiffness: float
    bending_stiffness: float
    mesh_quality_stiffness: float


@dataclass(frozen=True)
class StateEvaluation:
    total_energy: float
    energy_components: dict[str, float]
    variable_gradient: FloatArray
    cell_vertices: FloatArray
    ecm_vertices: FloatArray
    cell_gradient: FloatArray
    ecm_gradient: FloatArray
    volume_ratio: float
    volume_constraint_gradient: FloatArray
    geometry: GeometryDiagnostics
    interface: VerticalSliceEvaluation


@dataclass(frozen=True)
class FixedTopologySample:
    activation: float
    cell_vertices: FloatArray
    ecm_vertices: FloatArray
    axial_shortening: float
    centerline_bowing: float
    curvature_proxy: float
    volume_ratio: float
    kkt_residual: float
    active_gap_constraint_count: int
    maximum_gap_multiplier: float
    maximum_gap_complementarity: float
    gauge_residual: float
    minimum_cell_face_area_ratio: float
    minimum_ecm_jacobian: float
    maximum_ecm_jacobian: float
    maximum_ecm_displacement: float
    minimum_gap: float
    pair_force_residual: float
    pair_moment_residual: float
    cell_surface_energy: float
    active_fiber_energy: float
    ecm_energy: float
    coupling_energy: float
    total_energy: float
    interface_force_norm: float
    interface_moment_norm: float
    optimizer_success: bool
    optimizer_message: str
    optimizer_iterations: int
    optimizer_evaluations: int


@dataclass(frozen=True)
class FixedTopologyRun:
    status: str
    topology: Topology
    model: FixedTopologyModel
    samples: tuple[FixedTopologySample, ...]


@dataclass(frozen=True)
class ECMTranslationResponse:
    displacement: float
    energy: float
    reaction: float
    minimum_jacobian: float
    maximum_jacobian: float


def _structured_patch(
    *,
    side: Literal["basal", "apical"],
    cell_y_min: float,
    cell_y_max: float,
    x_bounds: tuple[float, float],
    z_bounds: tuple[float, float],
    gap: float,
    thickness: float,
    x_divisions: int,
    y_divisions: int,
    z_divisions: int,
) -> PatchMesh:
    if min(gap, thickness) <= 0.0:
        raise ValueError("gap and thickness must be positive")
    if min(x_divisions, y_divisions, z_divisions) < 1:
        raise ValueError("patch divisions must be positive")

    if side == "basal":
        surface_y = cell_y_min - gap
        far_y = surface_y - thickness
        y_values = np.linspace(far_y, surface_y, y_divisions + 1)
        interface_y_index = y_divisions
        fixed_y_index = 0
    else:
        surface_y = cell_y_max + gap
        far_y = surface_y + thickness
        y_values = np.linspace(surface_y, far_y, y_divisions + 1)
        interface_y_index = 0
        fixed_y_index = y_divisions

    x_values = np.linspace(x_bounds[0], x_bounds[1], x_divisions + 1)
    z_values = np.linspace(z_bounds[0], z_bounds[1], z_divisions + 1)

    def vertex_id(x_index: int, y_index: int, z_index: int) -> int:
        return (
            x_index * (y_divisions + 1) * (z_divisions + 1)
            + y_index * (z_divisions + 1)
            + z_index
        )

    vertices = np.asarray(
        [
            [x_value, y_value, z_value]
            for x_value in x_values
            for y_value in y_values
            for z_value in z_values
        ],
        dtype=np.float64,
    )

    tetrahedra: list[list[int]] = []
    for x_index in range(x_divisions):
        for y_index in range(y_divisions):
            for z_index in range(z_divisions):
                v000 = vertex_id(x_index, y_index, z_index)
                v100 = vertex_id(x_index + 1, y_index, z_index)
                v010 = vertex_id(x_index, y_index + 1, z_index)
                v110 = vertex_id(x_index + 1, y_index + 1, z_index)
                v001 = vertex_id(x_index, y_index, z_index + 1)
                v101 = vertex_id(x_index + 1, y_index, z_index + 1)
                v011 = vertex_id(x_index, y_index + 1, z_index + 1)
                v111 = vertex_id(x_index + 1, y_index + 1, z_index + 1)
                local_tetrahedra = [
                    [v000, v100, v110, v111],
                    [v000, v110, v010, v111],
                    [v000, v010, v011, v111],
                    [v000, v011, v001, v111],
                    [v000, v001, v101, v111],
                    [v000, v101, v100, v111],
                ]
                for tetrahedron in local_tetrahedra:
                    local = vertices[tetrahedron]
                    matrix = np.column_stack(
                        (
                            local[1] - local[0],
                            local[2] - local[0],
                            local[3] - local[0],
                        )
                    )
                    if float(np.linalg.det(matrix)) < 0.0:
                        tetrahedron[1], tetrahedron[2] = (
                            tetrahedron[2],
                            tetrahedron[1],
                        )
                    tetrahedra.append(tetrahedron)

    interface_faces: list[list[int]] = []
    for x_index in range(x_divisions):
        for z_index in range(z_divisions):
            v00 = vertex_id(x_index, interface_y_index, z_index)
            v10 = vertex_id(x_index + 1, interface_y_index, z_index)
            v01 = vertex_id(x_index, interface_y_index, z_index + 1)
            v11 = vertex_id(x_index + 1, interface_y_index, z_index + 1)
            interface_faces.extend(([v00, v10, v11], [v00, v11, v01]))

    fixed_ids = np.asarray(
        [
            vertex_id(x_index, fixed_y_index, z_index)
            for x_index in range(x_divisions + 1)
            for z_index in range(z_divisions + 1)
        ],
        dtype=np.int64,
    )
    return PatchMesh(
        vertices=vertices,
        tetrahedra=np.asarray(tetrahedra, dtype=np.int64),
        interface_faces=np.asarray(interface_faces, dtype=np.int64),
        fixed_vertex_ids=fixed_ids,
        side=side,
    )


def _combine_patches(
    patches: tuple[PatchMesh, ...],
) -> tuple[FloatArray, IntArray, IntArray, IntArray, tuple[int, ...]]:
    vertices: list[FloatArray] = []
    tetrahedra: list[IntArray] = []
    interface_faces: list[IntArray] = []
    fixed_ids: list[IntArray] = []
    face_offsets: list[int] = []
    vertex_offset = 0
    face_offset = 0
    for patch in patches:
        vertices.append(patch.vertices)
        tetrahedra.append(patch.tetrahedra + vertex_offset)
        interface_faces.append(patch.interface_faces + vertex_offset)
        fixed_ids.append(patch.fixed_vertex_ids + vertex_offset)
        face_offsets.append(face_offset)
        vertex_offset += len(patch.vertices)
        face_offset += len(patch.interface_faces)
    return (
        np.vstack(vertices),
        np.vstack(tetrahedra),
        np.vstack(interface_faces),
        np.concatenate(fixed_ids),
        tuple(face_offsets),
    )


def _barycentric_xz(point: FloatArray, triangle: FloatArray) -> FloatArray:
    projected = triangle[:, [0, 2]]
    origin = projected[0]
    matrix = np.column_stack((projected[1] - origin, projected[2] - origin))
    coordinates = np.linalg.solve(matrix, point[[0, 2]] - origin)
    return np.asarray(
        [1.0 - coordinates[0] - coordinates[1], coordinates[0], coordinates[1]],
        dtype=np.float64,
    )


def _locate_interface_point(
    point: FloatArray,
    vertices: FloatArray,
    faces: IntArray,
) -> tuple[int, FloatArray]:
    best_face = -1
    best_weights: FloatArray | None = None
    best_violation = float("inf")
    for face_id, face in enumerate(faces):
        weights = _barycentric_xz(point, vertices[face])
        violation = max(0.0, -float(weights.min()), float(weights.max()) - 1.0)
        if violation < best_violation:
            best_face = face_id
            best_weights = weights
            best_violation = violation
        if violation <= 1.0e-12:
            break
    if best_weights is None or best_violation > 1.0e-8:
        raise ValueError("cell material point lies outside the ECM interface mesh")
    return best_face, np.clip(best_weights, 0.0, 1.0) / np.clip(
        best_weights, 0.0, 1.0
    ).sum()


def build_fixed_topology_model(
    topology: Topology,
    *,
    gap: float = 0.04,
    ecm_thickness: float = 0.30,
    ecm_footprint_scale: float = 1.0,
    patch_divisions: tuple[int, int, int] = (5, 1, 4),
    contact_normal_cutoff: float = 0.90,
    adhesion_work: float = 0.02,
    opening_cutoff: float = 0.12,
    tangential_stiffness: float = 2.0,
    mu_eq: float = 1.0,
    kappa_eq: float = 20.0,
    mu_ve: float = 0.0,
    eta_ve: float = 0.5,
    fiber_stiffness: float = 10.0,
    global_area_stiffness: float = 0.1,
    bending_stiffness: float = 0.01,
    mesh_quality_stiffness: float = 0.05,
) -> FixedTopologyModel:
    if topology not in ("basal", "apical", "symmetric"):
        raise ValueError("unsupported fixed topology")
    if not np.isfinite(ecm_footprint_scale) or ecm_footprint_scale < 1.0:
        raise ValueError("ECM footprint scale must be finite and at least one")
    reference = _build_reference()
    cell_vertices = reference.vertices
    cell_faces = reference.faces
    face_areas, face_normals = triangle_geometry(cell_vertices, cell_faces)
    x_divisions, y_divisions, z_divisions = patch_divisions
    cell_x_bounds = (
        float(cell_vertices[:, 0].min()),
        float(cell_vertices[:, 0].max()),
    )
    cell_z_bounds = (
        float(cell_vertices[:, 2].min()),
        float(cell_vertices[:, 2].max()),
    )

    def scaled_bounds(bounds: tuple[float, float]) -> tuple[float, float]:
        center = 0.5 * (bounds[0] + bounds[1])
        half_span = 0.5 * (bounds[1] - bounds[0]) * ecm_footprint_scale
        return center - half_span, center + half_span

    patch_parameters = dict(
        cell_y_min=float(cell_vertices[:, 1].min()),
        cell_y_max=float(cell_vertices[:, 1].max()),
        x_bounds=scaled_bounds(cell_x_bounds),
        z_bounds=scaled_bounds(cell_z_bounds),
        gap=gap,
        thickness=ecm_thickness,
        x_divisions=x_divisions,
        y_divisions=y_divisions,
        z_divisions=z_divisions,
    )
    sides: tuple[Literal["basal", "apical"], ...]
    if topology == "symmetric":
        sides = ("basal", "apical")
    else:
        sides = (topology,)
    patches = tuple(
        _structured_patch(side=side, **patch_parameters) for side in sides
    )
    (
        ecm_vertices,
        ecm_tetrahedra,
        ecm_interface_faces,
        fixed_ids,
        face_offsets,
    ) = _combine_patches(patches)
    ecm_reference = build_ecm_reference(ecm_vertices, ecm_tetrahedra)

    point_ids: list[int] = []
    host_face_ids: list[int] = []
    barycentric: list[FloatArray] = []
    reference_weights: list[float] = []
    labels: list[str] = []
    tether_specs: list[tuple[int, int, FloatArray]] = []
    next_point_id = 10_000
    side_weight_scale = 0.5 if topology == "symmetric" else 1.0

    for side_index, side in enumerate(sides):
        if side == "basal":
            selected = np.flatnonzero(face_normals[:, 1] < -contact_normal_cutoff)
        else:
            selected = np.flatnonzero(face_normals[:, 1] > contact_normal_cutoff)
        local_boundary_faces = patches[side_index].interface_faces
        vertex_offset = sum(len(patch.vertices) for patch in patches[:side_index])
        global_boundary_faces = local_boundary_faces + vertex_offset
        interface_y = float(ecm_vertices[global_boundary_faces[0, 0], 1])
        for face_id in selected:
            material_point = cell_vertices[cell_faces[face_id]].mean(axis=0)
            projected = material_point.copy()
            projected[1] = interface_y
            local_ecm_face_id, ecm_weights = _locate_interface_point(
                projected,
                ecm_vertices,
                global_boundary_faces,
            )
            point_id = next_point_id
            next_point_id += 1
            point_ids.append(point_id)
            host_face_ids.append(int(face_id))
            barycentric.append(np.full(3, 1.0 / 3.0, dtype=np.float64))
            reference_weights.append(float(face_areas[face_id] * side_weight_scale))
            labels.append(side)
            tether_specs.append(
                (
                    point_id,
                    face_offsets[side_index] + local_ecm_face_id,
                    ecm_weights,
                )
            )

    registry = SurfaceMaterialRegistry(
        point_ids=np.asarray(point_ids, dtype=np.int64),
        face_ids=np.asarray(host_face_ids, dtype=np.int64),
        barycentric=np.asarray(barycentric, dtype=np.float64),
        reference_weights=np.asarray(reference_weights, dtype=np.float64),
        labels=tuple(labels),
        state=np.zeros((len(point_ids), 0), dtype=np.float64),
    )
    tethers = tuple(
        build_cell_ecm_tether(
            material_point_id=point_id,
            ecm_face_id=ecm_face_id,
            ecm_barycentric=ecm_weights,
            cell_reference_vertices=cell_vertices,
            cell_faces=cell_faces,
            registry=registry,
            ecm_reference_vertices=ecm_vertices,
            ecm_boundary_faces=ecm_interface_faces,
            adhesion_work=adhesion_work,
            opening_cutoff=opening_cutoff,
            tangential_stiffness=tangential_stiffness,
        )
        for point_id, ecm_face_id, ecm_weights in tether_specs
    )
    vertical_slice = CellECMVerticalSlice(
        cell_reference_vertices=cell_vertices,
        cell_faces=cell_faces,
        cell_registry=registry,
        ecm_reference=ecm_reference,
        ecm_boundary_faces=ecm_interface_faces,
        tethers=tethers,
        mu_eq=mu_eq,
        kappa_eq=kappa_eq,
        mu_ve=mu_ve,
        eta_ve=eta_ve,
    )
    fixed_ids = np.unique(fixed_ids)
    free_ids = np.setdiff1d(
        np.arange(len(ecm_vertices), dtype=np.int64),
        fixed_ids,
        assume_unique=True,
    )
    weighted_normal_y = float(
        np.sum(
            registry.reference_weights
            * face_normals[registry.face_ids, 1]
        )
    )
    total_weight = float(registry.reference_weights.sum())
    fiber_reference = build_surface_fiber_reference(cell_vertices, cell_faces)
    reference_angles, _ = _triangle_angles_and_gradients(cell_vertices[cell_faces])
    return FixedTopologyModel(
        topology=topology,
        cell_reference=reference,
        fiber_reference=fiber_reference,
        reference_angles=reference_angles,
        reference_face_areas=face_areas,
        vertical_slice=vertical_slice,
        ecm_fixed_vertex_ids=fixed_ids,
        ecm_free_vertex_ids=free_ids,
        tether_weight_sum=total_weight,
        contact_polarity_y=weighted_normal_y / total_weight,
        fiber_stiffness=fiber_stiffness,
        global_area_stiffness=global_area_stiffness,
        bending_stiffness=bending_stiffness,
        mesh_quality_stiffness=mesh_quality_stiffness,
    )


def initial_variables(model: FixedTopologyModel) -> FloatArray:
    return np.zeros(
        model.cell_reference.null_basis.shape[1]
        + 3 * len(model.ecm_free_vertex_ids),
        dtype=np.float64,
    )


def prescribed_ecm_translation_response(
    model: FixedTopologyModel,
    displacement: float,
    *,
    direction: FloatArray | None = None,
) -> ECMTranslationResponse:
    """Return isolated ECM response to a uniform free-boundary translation."""
    if not np.isfinite(displacement):
        raise ValueError("ECM translation must be finite")
    if direction is None:
        direction = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)
    else:
        direction = np.asarray(direction, dtype=np.float64)
    if direction.shape != (3,):
        raise ValueError("ECM translation direction must have shape (3,)")
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm <= 1.0e-14:
        raise ValueError("ECM translation direction must be nonzero")
    unit_direction = direction / direction_norm
    vertices = model.vertical_slice.ecm_reference.vertices.copy()
    vertices[model.ecm_free_vertex_ids] += displacement * unit_direction
    energies, forces, jacobians = ecm_energy_force(
        vertices,
        model.vertical_slice.ecm_reference,
        model.vertical_slice.ecm_internal_z,
        mu_eq=model.vertical_slice.mu_eq,
        kappa_eq=model.vertical_slice.kappa_eq,
        mu_ve=model.vertical_slice.mu_ve,
    )
    free_resultant = forces[model.ecm_free_vertex_ids].sum(axis=0)
    reaction = -float(np.dot(free_resultant, unit_direction))
    return ECMTranslationResponse(
        displacement=float(displacement),
        energy=float(energies["ecm_total"]),
        reaction=reaction,
        minimum_jacobian=float(jacobians.min()),
        maximum_jacobian=float(jacobians.max()),
    )


def prescribed_ecm_affine_shear_response(
    model: FixedTopologyModel,
    displacement: float,
    *,
    direction: FloatArray | None = None,
) -> ECMTranslationResponse:
    """Audit mesh consistency under the same affine shear deformation field."""
    if not np.isfinite(displacement):
        raise ValueError("ECM shear displacement must be finite")
    if direction is None:
        direction = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)
    else:
        direction = np.asarray(direction, dtype=np.float64)
    if direction.shape != (3,):
        raise ValueError("ECM shear direction must have shape (3,)")
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm <= 1.0e-14:
        raise ValueError("ECM shear direction must be nonzero")
    unit_direction = direction / direction_norm
    reference_vertices = model.vertical_slice.ecm_reference.vertices
    y_values = reference_vertices[:, 1]
    if model.topology == "basal":
        alpha = (y_values - y_values.min()) / (y_values.max() - y_values.min())
    elif model.topology == "apical":
        alpha = (y_values.max() - y_values) / (y_values.max() - y_values.min())
    else:
        alpha = np.empty_like(y_values)
        lower = y_values < 0.3
        upper = ~lower
        lower_values = y_values[lower]
        upper_values = y_values[upper]
        alpha[lower] = (lower_values - lower_values.min()) / (
            lower_values.max() - lower_values.min()
        )
        alpha[upper] = (upper_values.max() - upper_values) / (
            upper_values.max() - upper_values.min()
        )
    vertices = reference_vertices + (
        displacement * alpha[:, None] * unit_direction[None, :]
    )
    energies, forces, jacobians = ecm_energy_force(
        vertices,
        model.vertical_slice.ecm_reference,
        model.vertical_slice.ecm_internal_z,
        mu_eq=model.vertical_slice.mu_eq,
        kappa_eq=model.vertical_slice.kappa_eq,
        mu_ve=model.vertical_slice.mu_ve,
    )
    interface = alpha >= 1.0 - 1.0e-12
    interface_resultant = forces[interface].sum(axis=0)
    reaction = -float(np.dot(interface_resultant, unit_direction))
    return ECMTranslationResponse(
        displacement=float(displacement),
        energy=float(energies["ecm_total"]),
        reaction=reaction,
        minimum_jacobian=float(jacobians.min()),
        maximum_jacobian=float(jacobians.max()),
    )


def unpack_variables(
    model: FixedTopologyModel,
    variables: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    cell_coordinate_count = model.cell_reference.null_basis.shape[1]
    expected = cell_coordinate_count + 3 * len(model.ecm_free_vertex_ids)
    if variables.shape != (expected,):
        raise ValueError("invalid fixed-topology variable shape")
    cell_vertices = model.cell_reference.vertices + (
        model.cell_reference.null_basis @ variables[:cell_coordinate_count]
    ).reshape((-1, 3))
    ecm_vertices = model.vertical_slice.ecm_reference.vertices.copy()
    ecm_vertices[model.ecm_free_vertex_ids] += variables[
        cell_coordinate_count:
    ].reshape((-1, 3))
    return cell_vertices, ecm_vertices


def pack_variables(
    model: FixedTopologyModel,
    cell_vertices: FloatArray,
    ecm_vertices: FloatArray,
) -> FloatArray:
    """Recover reduced optimization variables from a saved physical state."""
    if cell_vertices.shape != model.cell_reference.vertices.shape:
        raise ValueError("invalid saved cell vertex shape")
    if ecm_vertices.shape != model.vertical_slice.ecm_reference.vertices.shape:
        raise ValueError("invalid saved ECM vertex shape")
    cell_displacement = (
        np.asarray(cell_vertices, dtype=np.float64)
        - model.cell_reference.vertices
    ).reshape(-1)
    cell_coordinates, *_ = np.linalg.lstsq(
        model.cell_reference.null_basis,
        cell_displacement,
        rcond=None,
    )
    reconstructed_cell = (
        model.cell_reference.null_basis @ cell_coordinates
    )
    if np.linalg.norm(reconstructed_cell - cell_displacement) > 1.0e-9:
        raise ValueError("saved cell state violates the fixed gauge subspace")
    ecm_displacement = (
        np.asarray(ecm_vertices, dtype=np.float64)
        - model.vertical_slice.ecm_reference.vertices
    )
    if np.linalg.norm(ecm_displacement[model.ecm_fixed_vertex_ids]) > 1.0e-12:
        raise ValueError("saved ECM state moves a fixed far-boundary node")
    return np.concatenate(
        (
            cell_coordinates,
            ecm_displacement[model.ecm_free_vertex_ids].reshape(-1),
        )
    )


def evaluate_variables(
    model: FixedTopologyModel,
    variables: FloatArray,
    *,
    activation: float,
    ecm_internal_z: FloatArray | None = None,
) -> StateEvaluation:
    cell_vertices, ecm_vertices = unpack_variables(model, variables)
    surface = evaluate_surface_energy(
        cell_vertices,
        model.cell_reference,
        global_area_stiffness=model.global_area_stiffness,
        bending_stiffness=model.bending_stiffness,
        mesh_quality_stiffness=model.mesh_quality_stiffness,
        reference_angles=model.reference_angles,
        reference_face_areas=model.reference_face_areas,
    )
    fiber = distributed_fiber_energy_gradient(
        cell_vertices,
        model.fiber_reference,
        activation=activation,
        stiffness=model.fiber_stiffness,
    )
    interface = model.vertical_slice.evaluate(
        cell_vertices,
        ecm_vertices,
        ecm_internal_z=ecm_internal_z,
        reject_penetration=False,
    )
    cell_gradient = surface.gradient + fiber.gradient - interface.cell_forces
    ecm_gradient = -interface.ecm_forces
    cell_reduced_gradient = (
        model.cell_reference.null_basis.T @ cell_gradient.reshape(-1)
    )
    variable_gradient = np.concatenate(
        (
            cell_reduced_gradient,
            ecm_gradient[model.ecm_free_vertex_ids].reshape(-1),
        )
    )
    volume, volume_gradient = surface_volume_and_gradient(
        cell_vertices,
        model.cell_reference.faces,
    )
    volume_reduced_gradient = model.cell_reference.null_basis.T @ (
        volume_gradient / model.cell_reference.cell.volume0
    ).reshape(-1)
    volume_constraint_gradient = np.concatenate(
        (
            volume_reduced_gradient,
            np.zeros(3 * len(model.ecm_free_vertex_ids), dtype=np.float64),
        )
    )
    total_energy = surface.total + fiber.energy + interface.energies["total"]
    return StateEvaluation(
        total_energy=float(total_energy),
        energy_components={
            "cell_surface": float(surface.total),
            "active_fiber": float(fiber.energy),
            "ecm_equilibrium": float(interface.energies["ecm_equilibrium"]),
            "ecm_viscoelastic": float(interface.energies["ecm_viscoelastic"]),
            "ecm": float(interface.energies["ecm_total"]),
            "coupling": float(interface.energies["cell_ecm_coupling"]),
        },
        variable_gradient=variable_gradient,
        cell_vertices=cell_vertices,
        ecm_vertices=ecm_vertices,
        cell_gradient=cell_gradient,
        ecm_gradient=ecm_gradient,
        volume_ratio=float(volume / model.cell_reference.cell.volume0),
        volume_constraint_gradient=volume_constraint_gradient,
        geometry=_geometry_diagnostics(cell_vertices, model.cell_reference),
        interface=interface,
    )


def _tether_gap_and_local_gradients(
    master_vertices: FloatArray,
    master_face: IntArray,
    slave_vertices: FloatArray,
    slave_face: IntArray,
    *,
    master_barycentric: FloatArray,
    slave_barycentric: FloatArray,
    normal_orientation_sign: float,
) -> tuple[float, FloatArray, FloatArray]:
    local_master = master_vertices[master_face]
    local_slave = slave_vertices[slave_face]
    master_point = master_barycentric @ local_master
    slave_point = slave_barycentric @ local_slave
    relative = slave_point - master_point
    edge = local_master[1] - local_master[0]
    other = local_master[2] - local_master[0]
    raw_normal = np.cross(edge, other)
    normal_length = float(np.linalg.norm(raw_normal))
    if normal_length <= 0.0:
        raise ValueError("degenerate material tether master face")
    unit_normal = raw_normal / normal_length
    normal = normal_orientation_sign * unit_normal
    gap = float(np.dot(relative, normal))

    relative_bar = normal
    normal_bar = relative
    unit_normal_bar = normal_orientation_sign * normal_bar
    raw_bar = (
        unit_normal_bar
        - unit_normal * float(np.dot(unit_normal, unit_normal_bar))
    ) / normal_length
    edge_from_normal_bar = np.cross(other, raw_bar)
    other_bar = np.cross(raw_bar, edge)
    master_gradient = np.zeros((3, 3), dtype=np.float64)
    master_gradient[1] += edge_from_normal_bar
    master_gradient[2] += other_bar
    master_gradient[0] -= edge_from_normal_bar + other_bar
    master_gradient -= master_barycentric[:, None] * relative_bar
    slave_gradient = slave_barycentric[:, None] * relative_bar
    return gap, master_gradient, slave_gradient


def gap_constraints(
    model: FixedTopologyModel,
    variables: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    cell_vertices, ecm_vertices = unpack_variables(model, variables)
    tether_count = len(model.vertical_slice.tethers)
    variable_count = len(variables)
    gaps = np.empty(tether_count, dtype=np.float64)
    jacobian = np.zeros((tether_count, variable_count), dtype=np.float64)
    cell_coordinate_count = model.cell_reference.null_basis.shape[1]
    registry = model.vertical_slice.cell_registry
    for tether_index, tether in enumerate(model.vertical_slice.tethers):
        rows = np.flatnonzero(registry.point_ids == tether.material_point_id)
        if len(rows) != 1:
            raise ValueError("material point is not owned exactly once")
        row = int(rows[0])
        cell_face = model.cell_reference.faces[int(registry.face_ids[row])]
        ecm_face = model.vertical_slice.ecm_boundary_faces[tether.ecm_face_id]
        gap, cell_local, ecm_local = _tether_gap_and_local_gradients(
            cell_vertices,
            cell_face,
            ecm_vertices,
            ecm_face,
            master_barycentric=registry.barycentric[row],
            slave_barycentric=tether.ecm_barycentric,
            normal_orientation_sign=tether.normal_orientation_sign,
        )
        cell_gradient = np.zeros_like(cell_vertices)
        ecm_gradient = np.zeros_like(ecm_vertices)
        np.add.at(cell_gradient, cell_face, cell_local)
        np.add.at(ecm_gradient, ecm_face, ecm_local)
        gaps[tether_index] = gap
        jacobian[tether_index, :cell_coordinate_count] = (
            model.cell_reference.null_basis.T @ cell_gradient.reshape(-1)
        )
        jacobian[tether_index, cell_coordinate_count:] = ecm_gradient[
            model.ecm_free_vertex_ids
        ].reshape(-1)
    return gaps, jacobian


def _weighted_centroid(
    vertices: FloatArray,
    weights: FloatArray,
    mask: NDArray[np.bool_],
) -> FloatArray:
    active_weights = weights[mask]
    return np.sum(vertices[mask] * active_weights[:, None], axis=0) / float(
        active_weights.sum()
    )


def centerline_bowing_and_curvature(
    vertices: FloatArray,
    model: FixedTopologyModel,
) -> tuple[float, float]:
    reference_vertices = model.cell_reference.vertices
    x_values = reference_vertices[:, 0]
    weights = model.cell_reference.dual_weights
    left = x_values <= 0.15
    middle = np.abs(x_values - 0.5) <= 0.08
    right = x_values >= 0.85
    if min(int(left.sum()), int(middle.sum()), int(right.sum())) == 0:
        raise ValueError("cell reference lacks centerline sampling regions")
    current_points = [
        _weighted_centroid(vertices, weights, mask)
        for mask in (left, middle, right)
    ]
    reference_points = [
        _weighted_centroid(reference_vertices, weights, mask)
        for mask in (left, middle, right)
    ]
    current_bow = current_points[1][1] - 0.5 * (
        current_points[0][1] + current_points[2][1]
    )
    reference_bow = reference_points[1][1] - 0.5 * (
        reference_points[0][1] + reference_points[2][1]
    )
    bowing = float(current_bow - reference_bow)
    span = float(current_points[2][0] - current_points[0][0])
    curvature = 8.0 * bowing / (span * span)
    return bowing, float(curvature)


def _sample_from_evaluation(
    model: FixedTopologyModel,
    evaluation: StateEvaluation,
    variables: FloatArray,
    *,
    activation: float,
    optimizer_success: bool,
    optimizer_message: str,
    optimizer_iterations: int,
    optimizer_evaluations: int,
) -> FixedTopologySample:
    objective_gradient = evaluation.variable_gradient
    constraint_gradient = evaluation.volume_constraint_gradient
    gaps, gap_jacobian = gap_constraints(model, variables)
    active_gap_mask = gaps <= 1.0e-7
    active_gap_jacobian = gap_jacobian[active_gap_mask]
    multiplier_matrix = np.column_stack(
        (
            constraint_gradient,
            -active_gap_jacobian.T,
        )
    )
    lower_bounds = np.concatenate(
        (
            np.asarray([-np.inf]),
            np.zeros(len(active_gap_jacobian), dtype=np.float64),
        )
    )
    upper_bounds = np.full(len(lower_bounds), np.inf, dtype=np.float64)
    multipliers = lsq_linear(
        multiplier_matrix,
        -objective_gradient,
        bounds=(lower_bounds, upper_bounds),
        tol=1.0e-12,
        lsmr_tol=1.0e-12,
        max_iter=500,
    ).x
    kkt_vector = objective_gradient + multiplier_matrix @ multipliers
    multiplier_force = multiplier_matrix @ multipliers
    kkt_residual = float(
        np.linalg.norm(kkt_vector)
        / max(
            1.0,
            float(np.linalg.norm(objective_gradient)),
            float(np.linalg.norm(multiplier_force)),
        )
    )
    gap_multipliers = multipliers[1:]
    active_gaps = gaps[active_gap_mask]
    length, _ = anchor_length_axis(
        evaluation.cell_vertices,
        model.cell_reference.active,
    )
    bowing, curvature = centerline_bowing_and_curvature(
        evaluation.cell_vertices,
        model,
    )
    cell_displacement = (
        evaluation.cell_vertices - model.cell_reference.vertices
    ).reshape(-1)
    gauge_residual = float(
        np.linalg.norm(model.cell_reference.gauge @ cell_displacement)
    )
    ecm_displacement = (
        evaluation.ecm_vertices
        - model.vertical_slice.ecm_reference.vertices
    )
    interface_force = evaluation.interface.cell_tether_forces
    interface_moment = np.cross(
        evaluation.cell_vertices,
        interface_force,
    ).sum(axis=0)
    return FixedTopologySample(
        activation=activation,
        cell_vertices=evaluation.cell_vertices.copy(),
        ecm_vertices=evaluation.ecm_vertices.copy(),
        axial_shortening=float(1.0 - length / model.cell_reference.active.length0),
        centerline_bowing=bowing,
        curvature_proxy=curvature,
        volume_ratio=evaluation.volume_ratio,
        kkt_residual=kkt_residual,
        active_gap_constraint_count=int(active_gap_mask.sum()),
        maximum_gap_multiplier=(
            float(gap_multipliers.max()) if len(gap_multipliers) else 0.0
        ),
        maximum_gap_complementarity=(
            float(np.max(np.abs(gap_multipliers * active_gaps)))
            if len(gap_multipliers)
            else 0.0
        ),
        gauge_residual=gauge_residual,
        minimum_cell_face_area_ratio=evaluation.geometry.minimum_face_area_ratio,
        minimum_ecm_jacobian=float(evaluation.interface.ecm_jacobians.min()),
        maximum_ecm_jacobian=float(evaluation.interface.ecm_jacobians.max()),
        maximum_ecm_displacement=float(
            np.linalg.norm(ecm_displacement, axis=1).max()
        ),
        minimum_gap=evaluation.interface.minimum_gap,
        pair_force_residual=evaluation.interface.pair_force_residual,
        pair_moment_residual=evaluation.interface.pair_moment_residual,
        cell_surface_energy=evaluation.energy_components["cell_surface"],
        active_fiber_energy=evaluation.energy_components["active_fiber"],
        ecm_energy=evaluation.energy_components["ecm"],
        coupling_energy=evaluation.energy_components["coupling"],
        total_energy=evaluation.total_energy,
        interface_force_norm=float(np.linalg.norm(interface_force)),
        interface_moment_norm=float(np.linalg.norm(interface_moment)),
        optimizer_success=optimizer_success,
        optimizer_message=optimizer_message,
        optimizer_iterations=optimizer_iterations,
        optimizer_evaluations=optimizer_evaluations,
    )


def sample_saved_state(
    model: FixedTopologyModel,
    cell_vertices: FloatArray,
    ecm_vertices: FloatArray,
    *,
    activation: float,
    ecm_internal_z: FloatArray | None = None,
    optimizer_success: bool,
    optimizer_message: str,
    optimizer_iterations: int,
    optimizer_evaluations: int,
) -> FixedTopologySample:
    """Re-evaluate a persisted state with the current constrained KKT audit."""
    variables = pack_variables(model, cell_vertices, ecm_vertices)
    evaluation = evaluate_variables(
        model,
        variables,
        activation=activation,
        ecm_internal_z=ecm_internal_z,
    )
    return _sample_from_evaluation(
        model,
        evaluation,
        variables,
        activation=activation,
        optimizer_success=optimizer_success,
        optimizer_message=optimizer_message,
        optimizer_iterations=optimizer_iterations,
        optimizer_evaluations=optimizer_evaluations,
    )


def _sample_passes(sample: FixedTopologySample) -> bool:
    return bool(
        sample.optimizer_success
        and abs(sample.volume_ratio - 1.0) <= 1.0e-8
        and sample.kkt_residual <= 1.0e-5
        and sample.maximum_gap_complementarity <= 1.0e-8
        and sample.gauge_residual <= 1.0e-10
        and sample.minimum_cell_face_area_ratio >= 0.05
        and sample.minimum_ecm_jacobian > 0.0
        and sample.minimum_gap >= -1.0e-12
        and sample.pair_force_residual <= 1.0e-10
        and sample.pair_moment_residual <= 1.0e-10
    )


def sample_passes(sample: FixedTopologySample) -> bool:
    """Return whether a sampled state satisfies the fixed-topology audit gates."""
    return _sample_passes(sample)


def run_fixed_topology_activation(
    topology: Topology,
    *,
    activation_levels: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20),
    model: FixedTopologyModel | None = None,
    max_iterations: int = 800,
) -> FixedTopologyRun:
    if not activation_levels or activation_levels[0] != 0.0:
        raise ValueError("activation path must start at zero")
    if any(
        not np.isfinite(value) or value < 0.0 or value >= 1.0
        for value in activation_levels
    ):
        raise ValueError("activation values must lie in [0,1)")
    if any(
        later < earlier
        for earlier, later in zip(activation_levels[:-1], activation_levels[1:])
    ):
        raise ValueError("activation path must be nondecreasing")
    if model is None:
        model = build_fixed_topology_model(topology)
    if model.topology != topology:
        raise ValueError("model topology does not match requested run")

    variables = initial_variables(model)
    samples: list[FixedTopologySample] = []
    status = "completed"
    for step_index, activation in enumerate(activation_levels):
        if step_index == 0:
            result_success = True
            result_message = "reference_state"
            result_iterations = 0
            result_evaluations = 1
        else:
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
                    cached_gap_variables = np.asarray(
                        current,
                        dtype=np.float64,
                    ).copy()
                    cached_gaps, cached_gap_jacobian = gap_constraints(
                        model,
                        current,
                    )
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
                variables,
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
            variables = np.asarray(result.x, dtype=np.float64)
            result_success = bool(result.success)
            result_message = str(result.message)
            result_iterations = int(result.nit)
            result_evaluations = int(result.nfev)
        evaluation = evaluate_variables(
            model,
            variables,
            activation=activation,
        )
        sample = _sample_from_evaluation(
            model,
            evaluation,
            variables,
            activation=activation,
            optimizer_success=result_success,
            optimizer_message=result_message,
            optimizer_iterations=result_iterations,
            optimizer_evaluations=result_evaluations,
        )
        samples.append(sample)
        if not _sample_passes(sample):
            status = "failed_physical_or_numerical_gate"
            break
    if len(samples) != len(activation_levels):
        status = "failed_before_peak_activation"
    return FixedTopologyRun(
        status=status,
        topology=topology,
        model=model,
        samples=tuple(samples),
    )
