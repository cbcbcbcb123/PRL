"""Conservative cell-surface to volumetric-ECM vertical slice."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from route_h.contact_adhesion import material_tether_energy_force_with_reference
from route_h.ecm_finite_strain import ECMReference, ecm_energy_force

from .remesh_registry import SurfaceMaterialRegistry


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class CellECMTether:
    material_point_id: int
    ecm_face_id: int
    ecm_barycentric: FloatArray
    reference_gap: float
    normal_orientation_sign: float
    reference_t1: FloatArray
    reference_t2: FloatArray
    adhesion_work: float
    opening_cutoff: float
    tangential_stiffness: float


@dataclass(frozen=True)
class VerticalSliceEvaluation:
    energies: dict[str, float]
    cell_forces: FloatArray
    ecm_forces: FloatArray
    cell_tether_forces: FloatArray
    ecm_tether_forces: FloatArray
    ecm_jacobians: FloatArray
    minimum_gap: float
    pair_force_residual: float
    pair_moment_residual: float


@dataclass(frozen=True)
class PowerAudit:
    energy_change: float
    integrated_mechanical_power: float
    normalized_residual: float
    step_count: int


def _material_point_row(registry: SurfaceMaterialRegistry, point_id: int) -> int:
    rows = np.flatnonzero(registry.point_ids == point_id)
    if len(rows) != 1:
        raise ValueError(f"material point ID {point_id} is not owned exactly once")
    return int(rows[0])


def build_cell_ecm_tether(
    *,
    material_point_id: int,
    ecm_face_id: int,
    ecm_barycentric: FloatArray,
    cell_reference_vertices: FloatArray,
    cell_faces: NDArray[np.int64],
    registry: SurfaceMaterialRegistry,
    ecm_reference_vertices: FloatArray,
    ecm_boundary_faces: NDArray[np.int64],
    adhesion_work: float,
    opening_cutoff: float = 0.08,
    tangential_stiffness: float = 0.5,
) -> CellECMTether:
    """Freeze one tether's constitutive reference from material coordinates."""

    row = _material_point_row(registry, material_point_id)
    if ecm_face_id < 0 or ecm_face_id >= len(ecm_boundary_faces):
        raise ValueError("ecm_face_id is out of range")
    ecm_barycentric = np.asarray(ecm_barycentric, dtype=np.float64)
    if ecm_barycentric.shape != (3,):
        raise ValueError("ecm_barycentric must have shape (3,)")
    if not np.isclose(ecm_barycentric.sum(), 1.0, atol=1e-12):
        raise ValueError("ecm_barycentric must sum to one")
    if np.any(ecm_barycentric < -1e-12) or np.any(ecm_barycentric > 1.0 + 1e-12):
        raise ValueError("ecm_barycentric lies outside its host face")
    if adhesion_work < 0.0 or tangential_stiffness < 0.0 or opening_cutoff <= 0.0:
        raise ValueError("invalid tether constitutive parameter")

    cell_face = cell_faces[int(registry.face_ids[row])]
    local_cell = cell_reference_vertices[cell_face]
    edge = local_cell[1] - local_cell[0]
    raw_normal = np.cross(edge, local_cell[2] - local_cell[0])
    edge_length = float(np.linalg.norm(edge))
    normal_length = float(np.linalg.norm(raw_normal))
    if edge_length <= 1e-14 or normal_length <= 1e-14:
        raise ValueError("degenerate cell host face")
    raw_normal /= normal_length
    cell_point = registry.barycentric[row] @ local_cell
    ecm_point = ecm_barycentric @ ecm_reference_vertices[ecm_boundary_faces[ecm_face_id]]
    reference_relative = ecm_point - cell_point
    orientation = 1.0 if float(np.dot(reference_relative, raw_normal)) >= 0.0 else -1.0
    normal = orientation * raw_normal
    t1 = edge / edge_length
    t2 = np.cross(normal, t1)
    reference_gap = float(np.dot(reference_relative, normal))
    if reference_gap <= 0.0:
        raise ValueError("reference cell-ECM gap must be strictly positive")

    return CellECMTether(
        material_point_id=material_point_id,
        ecm_face_id=ecm_face_id,
        ecm_barycentric=ecm_barycentric.copy(),
        reference_gap=reference_gap,
        normal_orientation_sign=orientation,
        reference_t1=t1,
        reference_t2=t2,
        adhesion_work=adhesion_work,
        opening_cutoff=opening_cutoff,
        tangential_stiffness=tangential_stiffness,
    )


@dataclass(frozen=True)
class CellECMVerticalSlice:
    """One remeshable closed cell surface coupled to one tetrahedral ECM patch."""

    cell_reference_vertices: FloatArray
    cell_faces: NDArray[np.int64]
    cell_registry: SurfaceMaterialRegistry
    ecm_reference: ECMReference
    ecm_boundary_faces: NDArray[np.int64]
    tethers: tuple[CellECMTether, ...]
    ecm_internal_z: FloatArray | None = None
    mu_eq: float = 1.0
    kappa_eq: float = 20.0
    mu_ve: float = 0.5
    eta_ve: float = 0.5

    def __post_init__(self) -> None:
        if self.cell_reference_vertices.ndim != 2 or self.cell_reference_vertices.shape[1] != 3:
            raise ValueError("cell_reference_vertices must have shape (n, 3)")
        if self.cell_faces.ndim != 2 or self.cell_faces.shape[1] != 3:
            raise ValueError("cell_faces must have shape (m, 3)")
        if np.any(self.cell_faces < 0) or np.any(self.cell_faces >= len(self.cell_reference_vertices)):
            raise ValueError("cell_faces references an invalid vertex")
        edge_counts: dict[tuple[int, int], int] = {}
        for face in self.cell_faces:
            for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
                key = tuple(sorted((int(first), int(second))))
                edge_counts[key] = edge_counts.get(key, 0) + 1
        if not edge_counts or any(count != 2 for count in edge_counts.values()):
            raise ValueError("cell_faces must form a closed two-manifold surface")
        if self.ecm_boundary_faces.ndim != 2 or self.ecm_boundary_faces.shape[1] != 3:
            raise ValueError("ecm_boundary_faces must have shape (m, 3)")
        tether_ids = [tether.material_point_id for tether in self.tethers]
        if len(set(tether_ids)) != len(tether_ids):
            raise ValueError("each material point may own at most one X0-D tether")
        for tether in self.tethers:
            _material_point_row(self.cell_registry, tether.material_point_id)
        if min(self.mu_eq, self.kappa_eq, self.mu_ve) < 0.0:
            raise ValueError("ECM moduli must be nonnegative")
        if not np.isfinite(self.eta_ve) or self.eta_ve <= 0.0:
            raise ValueError("ECM viscosity must be finite and positive")

    def evaluate(
        self,
        cell_vertices: FloatArray,
        ecm_vertices: FloatArray,
        *,
        ecm_internal_z: FloatArray | None = None,
        reject_penetration: bool = True,
    ) -> VerticalSliceEvaluation:
        if cell_vertices.shape != self.cell_reference_vertices.shape:
            raise ValueError("cell vertex shape does not match the reference")
        if ecm_vertices.shape != self.ecm_reference.vertices.shape:
            raise ValueError("ECM vertex shape does not match the reference")

        selected_internal_z = (
            self.ecm_internal_z
            if ecm_internal_z is None
            else np.asarray(ecm_internal_z, dtype=np.float64)
        )
        ecm_energies, ecm_bulk_force, jacobians = ecm_energy_force(
            ecm_vertices,
            self.ecm_reference,
            selected_internal_z,
            mu_eq=self.mu_eq,
            kappa_eq=self.kappa_eq,
            mu_ve=self.mu_ve,
        )
        cell_tether_force = np.zeros_like(cell_vertices, dtype=np.float64)
        ecm_tether_force = np.zeros_like(ecm_vertices, dtype=np.float64)
        coupling_energy = 0.0
        minimum_gap = float("inf")

        for tether in self.tethers:
            row = _material_point_row(self.cell_registry, tether.material_point_id)
            cell_face = self.cell_faces[int(self.cell_registry.face_ids[row])]
            ecm_face = self.ecm_boundary_faces[tether.ecm_face_id]
            energies, local_cell_force, local_ecm_force, state = (
                material_tether_energy_force_with_reference(
                    cell_vertices,
                    cell_face,
                    ecm_vertices,
                    ecm_face,
                    reference_master_vertices=self.cell_reference_vertices,
                    reference_slave_vertices=self.ecm_reference.vertices,
                    master_barycentric=self.cell_registry.barycentric[row],
                    slave_barycentric=tether.ecm_barycentric,
                    reference_weight=float(self.cell_registry.reference_weights[row]),
                    g0_pair=tether.reference_gap,
                    normal_orientation_sign=tether.normal_orientation_sign,
                    reference_t1=tether.reference_t1,
                    reference_t2=tether.reference_t2,
                    adhesion_work=tether.adhesion_work,
                    opening_cutoff=tether.opening_cutoff,
                    tangential_stiffness=tether.tangential_stiffness,
                )
            )
            np.add.at(cell_tether_force, cell_face, local_cell_force)
            np.add.at(ecm_tether_force, ecm_face, local_ecm_force)
            coupling_energy += energies["adhesion_total"]
            current_gap = float(state["gap"])
            if reject_penetration and current_gap < -1e-12:
                raise ValueError(
                    "cell-ECM penetration detected at material point "
                    f"{tether.material_point_id}: gap={current_gap:.17g}"
                )
            minimum_gap = min(minimum_gap, current_gap)

        pair_resultant = cell_tether_force.sum(axis=0) + ecm_tether_force.sum(axis=0)
        pair_moment = (
            np.cross(cell_vertices, cell_tether_force).sum(axis=0)
            + np.cross(ecm_vertices, ecm_tether_force).sum(axis=0)
        )
        pair_scale = max(
            1.0,
            float(np.linalg.norm(cell_tether_force))
            + float(np.linalg.norm(ecm_tether_force)),
        )
        total_ecm_force = ecm_bulk_force + ecm_tether_force
        total_energy = ecm_energies["ecm_total"] + coupling_energy
        energies = {
            **ecm_energies,
            "cell_ecm_coupling": coupling_energy,
            "total": total_energy,
        }
        return VerticalSliceEvaluation(
            energies=energies,
            cell_forces=cell_tether_force,
            ecm_forces=total_ecm_force,
            cell_tether_forces=cell_tether_force,
            ecm_tether_forces=ecm_tether_force,
            ecm_jacobians=jacobians,
            minimum_gap=minimum_gap,
            pair_force_residual=float(np.linalg.norm(pair_resultant) / pair_scale),
            pair_moment_residual=float(np.linalg.norm(pair_moment) / pair_scale),
        )

    def audit_prescribed_motion(
        self,
        cell_start: FloatArray,
        ecm_start: FloatArray,
        cell_velocity: FloatArray,
        ecm_velocity: FloatArray,
        *,
        duration: float,
        step_count: int,
    ) -> PowerAudit:
        if duration <= 0.0:
            raise ValueError("duration must be positive")
        if step_count < 1:
            raise ValueError("step_count must be at least one")
        if cell_velocity.shape != cell_start.shape or ecm_velocity.shape != ecm_start.shape:
            raise ValueError("velocity shapes must match their states")

        times = np.linspace(0.0, duration, step_count + 1)
        energies = np.empty(step_count + 1, dtype=np.float64)
        powers = np.empty(step_count + 1, dtype=np.float64)
        for index, time in enumerate(times):
            evaluation = self.evaluate(
                cell_start + time * cell_velocity,
                ecm_start + time * ecm_velocity,
            )
            energies[index] = evaluation.energies["total"]
            powers[index] = float(
                np.sum(evaluation.cell_forces * cell_velocity)
                + np.sum(evaluation.ecm_forces * ecm_velocity)
            )
        energy_change = float(energies[-1] - energies[0])
        integrated_power = float(np.trapezoid(powers, times))
        residual = abs(energy_change + integrated_power) / max(
            1.0,
            abs(energy_change),
            abs(integrated_power),
        )
        return PowerAudit(
            energy_change=energy_change,
            integrated_mechanical_power=integrated_power,
            normalized_residual=residual,
            step_count=step_count,
        )
