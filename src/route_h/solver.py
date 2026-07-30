"""The only Stage 1 computation entry point.

This module evaluates passive reference/local manufactured states.  It has no
time-trajectory runner, active controller, or Stage 2 gate dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .contracts import require_passive_stage1
from .contact_adhesion import (
    count_surface_pair_proper_intersections,
    count_surface_self_intersections,
    material_tether_energy_force_with_reference,
)
from .coupling import SurfaceEntity, eligible_entity_pairs, ordered_steric_pair
from .dcm_cell import build_cell_reference, passive_energy_force
from .ecm_finite_strain import build_ecm_reference, ecm_energy_force
from .geometry import load_reference_bundle


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PassiveReferenceResult:
    total_energy: float
    maximum_cell_force: float
    maximum_ecm_force: float
    minimum_ecm_jacobian: float
    active_enabled: bool
    trajectory_run: bool


@dataclass(frozen=True)
class ReferenceSealAudit:
    eligible_steric_pairs: int
    steric_owner_records: int
    steric_energy: float
    minimum_steric_gap: float
    proper_intersections: int
    material_tether_count: int
    maximum_tether_opening: float
    maximum_tether_slip: float
    maximum_tether_force: float
    assembled_net_force: float
    assembled_net_moment: float


def evaluate_passive_reference(
    *,
    active: bool = False,
    full_patch_trajectory: bool = False,
) -> PassiveReferenceResult:
    require_passive_stage1(
        active=active,
        full_patch_trajectory=full_patch_trajectory,
    )
    arrays, _ = load_reference_bundle()
    cell_energy = 0.0
    maximum_cell_force = 0.0
    for cell_id in range(len(arrays["cell_vertices"])):
        reference = build_cell_reference(
            arrays["cell_vertices"][cell_id],
            arrays["cell_faces"][cell_id],
            arrays["cell_primary_identity"][cell_id],
            arrays["cell_directional_identity"][cell_id],
        )
        energies, force = passive_energy_force(
            arrays["cell_vertices"][cell_id], reference
        )
        cell_energy += energies["cell_total"]
        maximum_cell_force = max(maximum_cell_force, float(np.max(np.linalg.norm(force, axis=1))))
    ecm_reference = build_ecm_reference(
        arrays["ecm_vertices"], arrays["ecm_tetrahedra"]
    )
    ecm_energies, ecm_force, jacobians = ecm_energy_force(
        arrays["ecm_vertices"], ecm_reference
    )
    return PassiveReferenceResult(
        total_energy=cell_energy + ecm_energies["ecm_total"],
        maximum_cell_force=maximum_cell_force,
        maximum_ecm_force=float(np.max(np.linalg.norm(ecm_force, axis=1))),
        minimum_ecm_jacobian=float(np.min(jacobians)),
        active_enabled=False,
        trajectory_run=False,
    )


def audit_reference_seal() -> ReferenceSealAudit:
    """Run the full assembled PreA reference-state checks."""
    require_passive_stage1()
    arrays, metadata = load_reference_bundle()
    cell_count = len(arrays["cell_vertices"])
    entity_vertices = [array for array in arrays["cell_vertices"]] + [arrays["ecm_vertices"]]
    entity_faces = [array for array in arrays["cell_faces"]] + [arrays["ecm_boundary_faces"]]
    assembled = [np.zeros_like(vertices) for vertices in entity_vertices]
    maximum_opening = 0.0
    maximum_slip = 0.0
    maximum_tether_force = 0.0
    tether_integer = arrays["material_tether_integer"]
    tether_float = arrays["material_tether_float"]
    for integer, value in zip(tether_integer, tether_float, strict=True):
        interface_code, _, master_id, master_face_id, slave_id, slave_face_id = map(int, integer)
        adhesion_work, tangential_stiffness = (
            (0.02, 0.5) if interface_code == 3 else (0.03, 2.0)
        )
        _, master_force, slave_force, state = material_tether_energy_force_with_reference(
            entity_vertices[master_id],
            entity_faces[master_id][master_face_id],
            entity_vertices[slave_id],
            entity_faces[slave_id][slave_face_id],
            reference_master_vertices=entity_vertices[master_id],
            reference_slave_vertices=entity_vertices[slave_id],
            master_barycentric=value[:3],
            slave_barycentric=value[3:6],
            reference_weight=float(value[6]),
            g0_pair=float(value[7]),
            normal_orientation_sign=float(value[8]),
            reference_t1=value[9:12],
            reference_t2=value[12:15],
            adhesion_work=adhesion_work,
            tangential_stiffness=tangential_stiffness,
        )
        assembled[master_id][entity_faces[master_id][master_face_id]] += master_force
        assembled[slave_id][entity_faces[slave_id][slave_face_id]] += slave_force
        maximum_opening = max(maximum_opening, abs(float(state["opening"])))
        maximum_slip = max(maximum_slip, float(np.linalg.norm(state["slip"])))
        maximum_tether_force = max(
            maximum_tether_force,
            float(np.max(np.linalg.norm(master_force, axis=1))),
            float(np.max(np.linalg.norm(slave_force, axis=1))),
        )

    surface_entities: list[SurfaceEntity] = []
    for cell_id in range(cell_count):
        surface_entities.append(SurfaceEntity(
            metadata["entity_ids"][cell_id],
            arrays["cell_vertices"][cell_id],
            arrays["cell_faces"][cell_id],
            np.arange(len(arrays["cell_vertices"][cell_id]), dtype=np.int64),
            arrays["cell_gauge_dual_area_weights"][cell_id],
        ))
    surface_entities.append(SurfaceEntity(
        "ECM",
        arrays["ecm_vertices"],
        arrays["ecm_boundary_faces"],
        arrays["ecm_exterior_vertex_ids"],
        arrays["ecm_exterior_vertex_dual_area_weights"],
    ))
    pairs = eligible_entity_pairs(surface_entities)
    steric_energy = 0.0
    owner_count = 0
    minimum_gap = float("inf")
    proper_intersections = sum(
        count_surface_self_intersections(entity.vertices, entity.faces, stop_after_first=True)
        for entity in surface_entities
    )
    for first, second in pairs:
        energy, first_force, second_force, owners, gap = ordered_steric_pair(
            surface_entities[first], surface_entities[second]
        )
        steric_energy += energy
        assembled[first] += first_force
        assembled[second] += second_force
        owner_count += owners
        minimum_gap = min(minimum_gap, gap)
        proper_intersections += count_surface_pair_proper_intersections(
            surface_entities[first].vertices,
            surface_entities[first].faces,
            surface_entities[second].vertices,
            surface_entities[second].faces,
            stop_after_first=True,
        )
    total_force = sum((force.sum(axis=0) for force in assembled), np.zeros(3))
    total_moment = sum((
        np.cross(vertices, force).sum(axis=0)
        for vertices, force in zip(entity_vertices, assembled, strict=True)
    ), np.zeros(3))
    return ReferenceSealAudit(
        eligible_steric_pairs=len(pairs),
        steric_owner_records=owner_count,
        steric_energy=steric_energy,
        minimum_steric_gap=minimum_gap,
        proper_intersections=proper_intersections,
        material_tether_count=len(tether_integer),
        maximum_tether_opening=maximum_opening,
        maximum_tether_slip=maximum_slip,
        maximum_tether_force=maximum_tether_force,
        assembled_net_force=float(np.linalg.norm(total_force)),
        assembled_net_moment=float(np.linalg.norm(total_moment)),
    )
