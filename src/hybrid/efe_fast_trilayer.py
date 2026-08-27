"""Fast three-layer DCM--FEM--DCM mechanics for EFE Node 1 N1-1.

The module owns one closed active myocardial surface, one shared tetrahedral
cardiac-jelly layer, and one closed passive endocardial surface.  The two
cell--ECM interfaces are evaluated separately while the ECM bulk energy is
assembled exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from route_h.contact_adhesion import material_tether_energy_force_with_reference
from route_h.dcm_cell import CellReference, build_cell_reference, surface_volume_and_gradient
from route_h.discretization import load_discretization_level
from route_h.displacement_controlled_cell_v02 import (
    _triangle_angles_and_gradients,
    evaluate_surface_energy,
)
from route_h.distributed_active_cell import (
    SurfaceFiberReference,
    build_surface_fiber_reference,
    distributed_fiber_energy_gradient,
)
from route_h.ecm_finite_strain import ECMReference, build_ecm_reference, ecm_energy_force
from route_h.geometry import triangle_geometry
from route_h.loads import blood_nodal_force, kelvin_voigt_support, support_weights

from .cell_ecm_coupling import CellECMTether, build_cell_ecm_tether
from .fixed_topology_active_cell_ecm import _locate_interface_point
from .remesh_registry import SurfaceMaterialRegistry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
DCMLevel = Literal["D0", "D1"]
ECMLevel = Literal["E0", "E1", "E2"]


class ECMEnergyForceBackend(Protocol):
    """Explicit seam for interchangeable, equation-equivalent ECM backends."""

    def __call__(
        self,
        vertices: FloatArray,
        reference: ECMReference,
        internal_z: FloatArray | None = None,
        *,
        mu_eq: float = 1.0,
        kappa_eq: float = 20.0,
        mu_ve: float = 0.5,
    ) -> tuple[dict[str, float], FloatArray, FloatArray]: ...

DCM_LEVELS: dict[DCMLevel, str] = {"D0": "base", "D1": "fine"}
ECM_LEVELS: dict[ECMLevel, tuple[int, int, int]] = {
    "E0": (5, 4, 4),
    "E1": (8, 6, 6),
    "E2": (10, 8, 8),
}


@dataclass(frozen=True)
class SurfaceLayerReference:
    vertices: FloatArray
    faces: IntArray
    cell: CellReference
    reference_angles: FloatArray
    reference_face_areas: FloatArray


@dataclass(frozen=True)
class MaterialInterface:
    name: str
    registry: SurfaceMaterialRegistry
    ecm_boundary_faces: IntArray
    tethers: tuple[CellECMTether, ...]


@dataclass(frozen=True)
class InterfaceEvaluation:
    energy: float
    cell_force: FloatArray
    ecm_force: FloatArray
    minimum_gap: float
    pair_force_residual: float
    pair_moment_residual: float


@dataclass(frozen=True)
class FastTrilayerModel:
    dcm_level: DCMLevel
    ecm_level: ECMLevel
    myocyte: SurfaceLayerReference
    endocardium: SurfaceLayerReference
    myocyte_fibers: SurfaceFiberReference
    ecm_reference: ECMReference
    ecm_myocyte_faces: IntArray
    ecm_endocardial_faces: IntArray
    myocyte_interface: MaterialInterface
    endocardial_interface: MaterialInterface
    endocardial_lumen_face_ids: IntArray
    myocyte_support_face_ids: IntArray
    myocyte_support_weights: FloatArray
    support_stiffness: FloatArray
    gap: float
    jelly_thickness: float
    mu_eq: float
    kappa_eq: float
    mu_ve: float
    eta_ve: float
    fiber_stiffness: float
    global_area_stiffness: float
    bending_stiffness: float
    mesh_quality_stiffness: float
    ecm_footprint_scale: float
    ecm_divisions: tuple[int, int, int]


@dataclass(frozen=True)
class FastTrilayerEvaluation:
    total_stored_energy: float
    energy_components: dict[str, float]
    myocyte_force: FloatArray
    ecm_force: FloatArray
    endocardial_force: FloatArray
    myocyte_energy_gradient: FloatArray
    ecm_energy_gradient: FloatArray
    endocardial_energy_gradient: FloatArray
    pressure_force: FloatArray
    wss_force: FloatArray
    support_force: FloatArray
    myocyte_volume_ratio: float
    endocardial_volume_ratio: float
    myocyte_area_ratio: float
    endocardial_area_ratio: float
    minimum_myocyte_face_area_ratio: float
    minimum_endocardial_face_area_ratio: float
    minimum_ecm_jacobian: float
    maximum_ecm_jacobian: float
    minimum_gap: float
    pair_force_residual_mj: float
    pair_moment_residual_mj: float
    pair_force_residual_je: float
    pair_moment_residual_je: float


def _structured_layer(
    *,
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    z_bounds: tuple[float, float],
    divisions: tuple[int, int, int],
) -> tuple[FloatArray, IntArray, IntArray, IntArray]:
    nx, ny, nz = divisions
    if min(nx, ny, nz) < 1:
        raise ValueError("ECM divisions must be positive")
    if not x_bounds[0] < x_bounds[1] or not y_bounds[0] < y_bounds[1]:
        raise ValueError("ECM bounds must have positive span")
    if not z_bounds[0] < z_bounds[1]:
        raise ValueError("ECM bounds must have positive span")

    x_values = np.linspace(*x_bounds, nx + 1)
    y_values = np.linspace(*y_bounds, ny + 1)
    z_values = np.linspace(*z_bounds, nz + 1)

    def vertex_id(ix: int, iy: int, iz: int) -> int:
        return ix * (ny + 1) * (nz + 1) + iy * (nz + 1) + iz

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
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                v000 = vertex_id(ix, iy, iz)
                v100 = vertex_id(ix + 1, iy, iz)
                v010 = vertex_id(ix, iy + 1, iz)
                v110 = vertex_id(ix + 1, iy + 1, iz)
                v001 = vertex_id(ix, iy, iz + 1)
                v101 = vertex_id(ix + 1, iy, iz + 1)
                v011 = vertex_id(ix, iy + 1, iz + 1)
                v111 = vertex_id(ix + 1, iy + 1, iz + 1)
                block = [
                    [v000, v100, v110, v111],
                    [v000, v110, v010, v111],
                    [v000, v010, v011, v111],
                    [v000, v011, v001, v111],
                    [v000, v001, v101, v111],
                    [v000, v101, v100, v111],
                ]
                for tetrahedron in block:
                    local = vertices[tetrahedron]
                    dm = np.column_stack(
                        (
                            local[1] - local[0],
                            local[2] - local[0],
                            local[3] - local[0],
                        )
                    )
                    if float(np.linalg.det(dm)) < 0.0:
                        tetrahedron[1], tetrahedron[2] = tetrahedron[2], tetrahedron[1]
                    tetrahedra.append(tetrahedron)

    def boundary_faces(iy: int) -> IntArray:
        faces: list[list[int]] = []
        for ix in range(nx):
            for iz in range(nz):
                v00 = vertex_id(ix, iy, iz)
                v10 = vertex_id(ix + 1, iy, iz)
                v01 = vertex_id(ix, iy, iz + 1)
                v11 = vertex_id(ix + 1, iy, iz + 1)
                faces.extend(([v00, v10, v11], [v00, v11, v01]))
        return np.asarray(faces, dtype=np.int64)

    return (
        vertices,
        np.asarray(tetrahedra, dtype=np.int64),
        boundary_faces(0),
        boundary_faces(ny),
    )


def _surface_reference(
    vertices: FloatArray,
    faces: IntArray,
    primary: IntArray,
    directional: IntArray,
) -> SurfaceLayerReference:
    cell = build_cell_reference(vertices, faces, primary, directional)
    areas, _ = triangle_geometry(vertices, faces)
    angles, _ = _triangle_angles_and_gradients(vertices[faces])
    return SurfaceLayerReference(
        vertices=np.asarray(vertices, dtype=np.float64).copy(),
        faces=np.asarray(faces, dtype=np.int64).copy(),
        cell=cell,
        reference_angles=angles,
        reference_face_areas=areas,
    )


def _build_material_interface(
    *,
    name: str,
    point_id_offset: int,
    cell: SurfaceLayerReference,
    selected_cell_face_ids: IntArray,
    ecm_vertices: FloatArray,
    ecm_boundary_faces: IntArray,
    adhesion_work: float,
    opening_cutoff: float,
    tangential_stiffness: float,
) -> MaterialInterface:
    point_ids: list[int] = []
    face_ids: list[int] = []
    barycentric: list[FloatArray] = []
    weights: list[float] = []
    ecm_face_ids: list[int] = []
    ecm_weights: list[FloatArray] = []
    interface_y = float(ecm_vertices[ecm_boundary_faces[0, 0], 1])
    for local_id, face_id in enumerate(selected_cell_face_ids.tolist()):
        point = cell.vertices[cell.faces[face_id]].mean(axis=0)
        projected = point.copy()
        projected[1] = interface_y
        host_face, host_weights = _locate_interface_point(
            projected,
            ecm_vertices,
            ecm_boundary_faces,
        )
        point_ids.append(point_id_offset + local_id)
        face_ids.append(face_id)
        barycentric.append(np.full(3, 1.0 / 3.0, dtype=np.float64))
        weights.append(float(cell.reference_face_areas[face_id]))
        ecm_face_ids.append(host_face)
        ecm_weights.append(host_weights)

    registry = SurfaceMaterialRegistry(
        point_ids=np.asarray(point_ids, dtype=np.int64),
        face_ids=np.asarray(face_ids, dtype=np.int64),
        barycentric=np.asarray(barycentric, dtype=np.float64),
        reference_weights=np.asarray(weights, dtype=np.float64),
        labels=tuple(name for _ in point_ids),
        state=np.zeros((len(point_ids), 0), dtype=np.float64),
    )
    tethers = tuple(
        build_cell_ecm_tether(
            material_point_id=point_id,
            ecm_face_id=ecm_face_id,
            ecm_barycentric=host_weights,
            cell_reference_vertices=cell.vertices,
            cell_faces=cell.faces,
            registry=registry,
            ecm_reference_vertices=ecm_vertices,
            ecm_boundary_faces=ecm_boundary_faces,
            adhesion_work=adhesion_work,
            opening_cutoff=opening_cutoff,
            tangential_stiffness=tangential_stiffness,
        )
        for point_id, ecm_face_id, host_weights in zip(
            point_ids,
            ecm_face_ids,
            ecm_weights,
            strict=True,
        )
    )
    return MaterialInterface(
        name=name,
        registry=registry,
        ecm_boundary_faces=ecm_boundary_faces.copy(),
        tethers=tethers,
    )


def build_fast_trilayer_model(
    *,
    dcm_level: DCMLevel = "D0",
    ecm_level: ECMLevel = "E0",
    gap: float = 0.04,
    jelly_thickness: float = 0.30,
    ecm_footprint_scale: float = 1.0,
    endocardial_y_span: float = 0.20,
    contact_normal_cutoff: float = 0.90,
    adhesion_work: float = 0.02,
    opening_cutoff: float = 0.12,
    tangential_stiffness: float = 2.0,
    mu_eq: float = 1.0,
    kappa_eq: float = 20.0,
    mu_ve: float = 0.5,
    eta_ve: float = 0.5,
    support_stiffness_ratio: float = 1.0,
    fiber_stiffness: float = 10.0,
    global_area_stiffness: float = 0.1,
    bending_stiffness: float = 0.01,
    mesh_quality_stiffness: float = 0.05,
) -> FastTrilayerModel:
    """Build the frozen N1-1 local three-layer reference geometry."""
    if dcm_level not in DCM_LEVELS or ecm_level not in ECM_LEVELS:
        raise ValueError("unsupported DCM or ECM level")
    if min(gap, jelly_thickness, endocardial_y_span) <= 0.0:
        raise ValueError("trilayer thickness and gap parameters must be positive")
    if not np.isfinite(ecm_footprint_scale) or ecm_footprint_scale < 1.0:
        raise ValueError("ECM footprint scale must be finite and at least one")
    if min(mu_eq, kappa_eq, mu_ve, support_stiffness_ratio) < 0.0:
        raise ValueError("trilayer material parameters must be nonnegative")
    if not np.isfinite(eta_ve) or eta_ve <= 0.0:
        raise ValueError("ECM viscosity must be finite and positive")

    arrays, _ = load_discretization_level(DCM_LEVELS[dcm_level])
    cell_id = 6
    myocyte_vertices = np.asarray(arrays["cell_vertices"][cell_id], dtype=np.float64)
    faces = np.asarray(arrays["cell_faces"][cell_id], dtype=np.int64)
    primary = np.asarray(arrays["cell_primary_identity"][cell_id], dtype=np.int64)
    directional = np.asarray(
        arrays["cell_directional_identity"][cell_id], dtype=np.int64
    )
    myocyte = _surface_reference(myocyte_vertices, faces, primary, directional)
    _, myocyte_normals = triangle_geometry(myocyte.vertices, myocyte.faces)
    myocyte_interface_faces = np.flatnonzero(
        myocyte_normals[:, 1] > contact_normal_cutoff
    ).astype(np.int64)
    support_face_ids = np.flatnonzero(
        myocyte_normals[:, 1] <= contact_normal_cutoff
    ).astype(np.int64)

    myocyte_x_bounds = (
        float(myocyte.vertices[:, 0].min()),
        float(myocyte.vertices[:, 0].max()),
    )
    myocyte_z_bounds = (
        float(myocyte.vertices[:, 2].min()),
        float(myocyte.vertices[:, 2].max()),
    )
    x_centre = 0.5 * (myocyte_x_bounds[0] + myocyte_x_bounds[1])
    z_centre = 0.5 * (myocyte_z_bounds[0] + myocyte_z_bounds[1])
    x_half_span = 0.5 * (myocyte_x_bounds[1] - myocyte_x_bounds[0])
    z_half_span = 0.5 * (myocyte_z_bounds[1] - myocyte_z_bounds[0])
    x_bounds = (
        x_centre - ecm_footprint_scale * x_half_span,
        x_centre + ecm_footprint_scale * x_half_span,
    )
    z_bounds = (
        z_centre - ecm_footprint_scale * z_half_span,
        z_centre + ecm_footprint_scale * z_half_span,
    )
    base_divisions = ECM_LEVELS[ecm_level]
    ecm_divisions = (
        int(np.ceil(base_divisions[0] * ecm_footprint_scale - 1.0e-12)),
        base_divisions[1],
        int(np.ceil(base_divisions[2] * ecm_footprint_scale - 1.0e-12)),
    )
    jelly_y_min = float(myocyte.vertices[:, 1].max()) + gap
    jelly_y_max = jelly_y_min + jelly_thickness
    ecm_vertices, tetrahedra, lower_faces, upper_faces = _structured_layer(
        x_bounds=x_bounds,
        y_bounds=(jelly_y_min, jelly_y_max),
        z_bounds=z_bounds,
        divisions=ecm_divisions,
    )
    ecm_reference = build_ecm_reference(ecm_vertices, tetrahedra)

    centre = myocyte.vertices.mean(axis=0)
    original_y_span = float(np.ptp(myocyte.vertices[:, 1]))
    endocardial_vertices = myocyte.vertices.copy()
    endocardial_vertices[:, 1] = (
        centre[1]
        + (endocardial_vertices[:, 1] - centre[1])
        * endocardial_y_span
        / original_y_span
    )
    translation = jelly_y_max + gap - float(endocardial_vertices[:, 1].min())
    endocardial_vertices[:, 1] += translation
    endocardium = _surface_reference(
        endocardial_vertices,
        faces,
        primary,
        directional,
    )
    _, endocardial_normals = triangle_geometry(
        endocardium.vertices, endocardium.faces
    )
    endocardial_interface_faces = np.flatnonzero(
        endocardial_normals[:, 1] < -contact_normal_cutoff
    ).astype(np.int64)
    lumen_face_ids = np.flatnonzero(
        endocardial_normals[:, 1] > contact_normal_cutoff
    ).astype(np.int64)

    myocyte_interface = _build_material_interface(
        name="myocyte_jelly",
        point_id_offset=10_000,
        cell=myocyte,
        selected_cell_face_ids=myocyte_interface_faces,
        ecm_vertices=ecm_vertices,
        ecm_boundary_faces=lower_faces,
        adhesion_work=adhesion_work,
        opening_cutoff=opening_cutoff,
        tangential_stiffness=tangential_stiffness,
    )
    endocardial_interface = _build_material_interface(
        name="jelly_endocardium",
        point_id_offset=20_000,
        cell=endocardium,
        selected_cell_face_ids=endocardial_interface_faces,
        ecm_vertices=ecm_vertices,
        ecm_boundary_faces=upper_faces,
        adhesion_work=adhesion_work,
        opening_cutoff=opening_cutoff,
        tangential_stiffness=tangential_stiffness,
    )
    support_weight = support_weights(
        myocyte.vertices,
        myocyte.faces,
        support_face_ids,
    )
    support_scalar = support_stiffness_ratio * mu_eq / jelly_thickness
    return FastTrilayerModel(
        dcm_level=dcm_level,
        ecm_level=ecm_level,
        myocyte=myocyte,
        endocardium=endocardium,
        myocyte_fibers=build_surface_fiber_reference(
            myocyte.vertices,
            myocyte.faces,
        ),
        ecm_reference=ecm_reference,
        ecm_myocyte_faces=lower_faces,
        ecm_endocardial_faces=upper_faces,
        myocyte_interface=myocyte_interface,
        endocardial_interface=endocardial_interface,
        endocardial_lumen_face_ids=lumen_face_ids,
        myocyte_support_face_ids=support_face_ids,
        myocyte_support_weights=support_weight,
        support_stiffness=np.eye(3) * support_scalar,
        gap=gap,
        jelly_thickness=jelly_thickness,
        mu_eq=mu_eq,
        kappa_eq=kappa_eq,
        mu_ve=mu_ve,
        eta_ve=eta_ve,
        fiber_stiffness=fiber_stiffness,
        global_area_stiffness=global_area_stiffness,
        bending_stiffness=bending_stiffness,
        mesh_quality_stiffness=mesh_quality_stiffness,
        ecm_footprint_scale=float(ecm_footprint_scale),
        ecm_divisions=ecm_divisions,
    )


def evaluate_material_interface(
    interface: MaterialInterface,
    cell_reference: SurfaceLayerReference,
    ecm_reference: ECMReference,
    cell_vertices: FloatArray,
    ecm_vertices: FloatArray,
    *,
    reject_penetration: bool = True,
) -> InterfaceEvaluation:
    cell_force = np.zeros_like(cell_vertices)
    ecm_force = np.zeros_like(ecm_vertices)
    total_energy = 0.0
    minimum_gap = float("inf")
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    for tether in interface.tethers:
        row = row_by_id[tether.material_point_id]
        cell_face = cell_reference.faces[int(interface.registry.face_ids[row])]
        ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
        energies, local_cell_force, local_ecm_force, state = (
            material_tether_energy_force_with_reference(
                cell_vertices,
                cell_face,
                ecm_vertices,
                ecm_face,
                reference_master_vertices=cell_reference.vertices,
                reference_slave_vertices=ecm_reference.vertices,
                master_barycentric=interface.registry.barycentric[row],
                slave_barycentric=tether.ecm_barycentric,
                reference_weight=float(interface.registry.reference_weights[row]),
                g0_pair=tether.reference_gap,
                normal_orientation_sign=tether.normal_orientation_sign,
                reference_t1=tether.reference_t1,
                reference_t2=tether.reference_t2,
                adhesion_work=tether.adhesion_work,
                opening_cutoff=tether.opening_cutoff,
                tangential_stiffness=tether.tangential_stiffness,
            )
        )
        np.add.at(cell_force, cell_face, local_cell_force)
        np.add.at(ecm_force, ecm_face, local_ecm_force)
        total_energy += energies["adhesion_total"]
        current_gap = float(state["gap"])
        if reject_penetration and current_gap < -1.0e-12:
            raise ValueError(
                f"{interface.name} penetration at material point "
                f"{tether.material_point_id}: gap={current_gap:.17g}"
            )
        minimum_gap = min(minimum_gap, current_gap)
    resultant = cell_force.sum(axis=0) + ecm_force.sum(axis=0)
    moment = (
        np.cross(cell_vertices, cell_force).sum(axis=0)
        + np.cross(ecm_vertices, ecm_force).sum(axis=0)
    )
    scale = max(
        1.0,
        float(np.linalg.norm(cell_force)) + float(np.linalg.norm(ecm_force)),
    )
    return InterfaceEvaluation(
        energy=float(total_energy),
        cell_force=cell_force,
        ecm_force=ecm_force,
        minimum_gap=minimum_gap,
        pair_force_residual=float(np.linalg.norm(resultant) / scale),
        pair_moment_residual=float(np.linalg.norm(moment) / scale),
    )


def _surface_area_ratio(layer: SurfaceLayerReference, vertices: FloatArray) -> float:
    areas, _ = triangle_geometry(vertices, layer.faces)
    return float(areas.sum() / layer.reference_face_areas.sum())


def _minimum_face_area_ratio(
    layer: SurfaceLayerReference,
    vertices: FloatArray,
) -> float:
    areas, _ = triangle_geometry(vertices, layer.faces)
    return float(np.min(areas / layer.reference_face_areas))


def evaluate_fast_trilayer_state(
    model: FastTrilayerModel,
    myocyte_vertices: FloatArray,
    ecm_vertices: FloatArray,
    endocardial_vertices: FloatArray,
    *,
    activation: float = 0.0,
    pressure: float = 0.0,
    wss_command: FloatArray | None = None,
    ecm_internal_z: FloatArray | None = None,
    ecm_backend: ECMEnergyForceBackend | None = None,
    reject_penetration: bool = True,
) -> FastTrilayerEvaluation:
    """Evaluate stored mechanics and assembled nodal force residuals."""
    if myocyte_vertices.shape != model.myocyte.vertices.shape:
        raise ValueError("myocyte vertex shape does not match the model")
    if ecm_vertices.shape != model.ecm_reference.vertices.shape:
        raise ValueError("ECM vertex shape does not match the model")
    if endocardial_vertices.shape != model.endocardium.vertices.shape:
        raise ValueError("endocardial vertex shape does not match the model")
    selected_wss = (
        np.zeros(3, dtype=np.float64)
        if wss_command is None
        else np.asarray(wss_command, dtype=np.float64)
    )
    if selected_wss.shape != (3,):
        raise ValueError("WSS command must have shape (3,)")

    myocyte_surface = evaluate_surface_energy(
        myocyte_vertices,
        model.myocyte,
        global_area_stiffness=model.global_area_stiffness,
        bending_stiffness=model.bending_stiffness,
        mesh_quality_stiffness=model.mesh_quality_stiffness,
        reference_angles=model.myocyte.reference_angles,
        reference_face_areas=model.myocyte.reference_face_areas,
    )
    endocardial_surface = evaluate_surface_energy(
        endocardial_vertices,
        model.endocardium,
        global_area_stiffness=model.global_area_stiffness,
        bending_stiffness=model.bending_stiffness,
        mesh_quality_stiffness=model.mesh_quality_stiffness,
        reference_angles=model.endocardium.reference_angles,
        reference_face_areas=model.endocardium.reference_face_areas,
    )
    active = distributed_fiber_energy_gradient(
        myocyte_vertices,
        model.myocyte_fibers,
        activation=activation,
        stiffness=model.fiber_stiffness,
    )
    selected_ecm_backend = ecm_energy_force if ecm_backend is None else ecm_backend
    ecm_energies, ecm_bulk_force, jacobians = selected_ecm_backend(
        ecm_vertices,
        model.ecm_reference,
        ecm_internal_z,
        mu_eq=model.mu_eq,
        kappa_eq=model.kappa_eq,
        mu_ve=model.mu_ve,
    )
    myocyte_interface = evaluate_material_interface(
        model.myocyte_interface,
        model.myocyte,
        model.ecm_reference,
        myocyte_vertices,
        ecm_vertices,
        reject_penetration=reject_penetration,
    )
    endocardial_interface = evaluate_material_interface(
        model.endocardial_interface,
        model.endocardium,
        model.ecm_reference,
        endocardial_vertices,
        ecm_vertices,
        reject_penetration=reject_penetration,
    )
    support_energy, support_force, _ = kelvin_voigt_support(
        myocyte_vertices,
        np.zeros_like(myocyte_vertices),
        model.myocyte.vertices,
        model.myocyte_support_weights,
        model.support_stiffness,
        np.zeros((3, 3), dtype=np.float64),
    )
    pressure_force, wss_force = blood_nodal_force(
        endocardial_vertices,
        model.endocardium.faces,
        model.endocardial_lumen_face_ids,
        pressure=pressure,
        wss_command=selected_wss,
    )

    myocyte_energy_gradient = (
        myocyte_surface.gradient
        + active.gradient
        - myocyte_interface.cell_force
        - support_force
    )
    ecm_energy_gradient = -(
        ecm_bulk_force
        + myocyte_interface.ecm_force
        + endocardial_interface.ecm_force
    )
    endocardial_energy_gradient = (
        endocardial_surface.gradient - endocardial_interface.cell_force
    )
    myocyte_force = -myocyte_energy_gradient
    ecm_force = -ecm_energy_gradient
    endocardial_force = (
        -endocardial_energy_gradient + pressure_force + wss_force
    )
    myocyte_volume, _ = surface_volume_and_gradient(
        myocyte_vertices, model.myocyte.faces
    )
    endocardial_volume, _ = surface_volume_and_gradient(
        endocardial_vertices, model.endocardium.faces
    )
    energies = {
        "myocyte_surface": float(myocyte_surface.total),
        "myocyte_active": float(active.energy),
        "endocardial_surface": float(endocardial_surface.total),
        "ecm_equilibrium": float(ecm_energies["ecm_equilibrium"]),
        "ecm_viscoelastic": float(ecm_energies["ecm_viscoelastic"]),
        "ecm": float(ecm_energies["ecm_total"]),
        "interface_myocyte_jelly": float(myocyte_interface.energy),
        "interface_jelly_endocardium": float(endocardial_interface.energy),
        "support": float(support_energy),
    }
    total = float(
        energies["myocyte_surface"]
        + energies["myocyte_active"]
        + energies["endocardial_surface"]
        + energies["ecm"]
        + energies["interface_myocyte_jelly"]
        + energies["interface_jelly_endocardium"]
        + energies["support"]
    )
    return FastTrilayerEvaluation(
        total_stored_energy=total,
        energy_components=energies,
        myocyte_force=myocyte_force,
        ecm_force=ecm_force,
        endocardial_force=endocardial_force,
        myocyte_energy_gradient=myocyte_energy_gradient,
        ecm_energy_gradient=ecm_energy_gradient,
        endocardial_energy_gradient=endocardial_energy_gradient,
        pressure_force=pressure_force,
        wss_force=wss_force,
        support_force=support_force,
        myocyte_volume_ratio=float(myocyte_volume / model.myocyte.cell.volume0),
        endocardial_volume_ratio=float(
            endocardial_volume / model.endocardium.cell.volume0
        ),
        myocyte_area_ratio=_surface_area_ratio(model.myocyte, myocyte_vertices),
        endocardial_area_ratio=_surface_area_ratio(
            model.endocardium, endocardial_vertices
        ),
        minimum_myocyte_face_area_ratio=_minimum_face_area_ratio(
            model.myocyte, myocyte_vertices
        ),
        minimum_endocardial_face_area_ratio=_minimum_face_area_ratio(
            model.endocardium, endocardial_vertices
        ),
        minimum_ecm_jacobian=float(jacobians.min()),
        maximum_ecm_jacobian=float(jacobians.max()),
        minimum_gap=min(
            myocyte_interface.minimum_gap,
            endocardial_interface.minimum_gap,
        ),
        pair_force_residual_mj=myocyte_interface.pair_force_residual,
        pair_moment_residual_mj=myocyte_interface.pair_moment_residual,
        pair_force_residual_je=endocardial_interface.pair_force_residual,
        pair_moment_residual_je=endocardial_interface.pair_moment_residual,
    )


def reference_evaluation(model: FastTrilayerModel) -> FastTrilayerEvaluation:
    return evaluate_fast_trilayer_state(
        model,
        model.myocyte.vertices,
        model.ecm_reference.vertices,
        model.endocardium.vertices,
    )


def rigidly_transform_model(
    model: FastTrilayerModel,
    rotation: FloatArray,
    translation: FloatArray,
) -> FastTrilayerModel:
    """Rotate and translate the complete reference, including material frames."""
    rotation = np.asarray(rotation, dtype=np.float64)
    translation = np.asarray(translation, dtype=np.float64)
    if rotation.shape != (3, 3) or translation.shape != (3,):
        raise ValueError("invalid rigid transform shape")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1.0e-12):
        raise ValueError("rotation must be orthogonal")
    if float(np.linalg.det(rotation)) <= 0.0:
        raise ValueError("rotation must be proper")

    def transformed(vertices: FloatArray) -> FloatArray:
        return vertices @ rotation.T + translation

    myocyte = _surface_reference(
        transformed(model.myocyte.vertices),
        model.myocyte.faces,
        model.myocyte.cell.primary,
        model.myocyte.cell.directional,
    )
    endocardium = _surface_reference(
        transformed(model.endocardium.vertices),
        model.endocardium.faces,
        model.endocardium.cell.primary,
        model.endocardium.cell.directional,
    )
    ecm_reference = build_ecm_reference(
        transformed(model.ecm_reference.vertices),
        model.ecm_reference.tetrahedra,
    )

    def transformed_interface(
        old: MaterialInterface,
        layer: SurfaceLayerReference,
    ) -> MaterialInterface:
        tethers = tuple(
            build_cell_ecm_tether(
                material_point_id=tether.material_point_id,
                ecm_face_id=tether.ecm_face_id,
                ecm_barycentric=tether.ecm_barycentric,
                cell_reference_vertices=layer.vertices,
                cell_faces=layer.faces,
                registry=old.registry,
                ecm_reference_vertices=ecm_reference.vertices,
                ecm_boundary_faces=old.ecm_boundary_faces,
                adhesion_work=tether.adhesion_work,
                opening_cutoff=tether.opening_cutoff,
                tangential_stiffness=tether.tangential_stiffness,
            )
            for tether in old.tethers
        )
        return replace(old, tethers=tethers)

    return replace(
        model,
        myocyte=myocyte,
        endocardium=endocardium,
        myocyte_fibers=build_surface_fiber_reference(
            myocyte.vertices,
            myocyte.faces,
            direction=rotation @ model.myocyte_fibers.direction,
        ),
        ecm_reference=ecm_reference,
        myocyte_interface=transformed_interface(model.myocyte_interface, myocyte),
        endocardial_interface=transformed_interface(
            model.endocardial_interface, endocardium
        ),
        myocyte_support_weights=model.myocyte_support_weights.copy(),
        support_stiffness=rotation @ model.support_stiffness @ rotation.T,
    )
