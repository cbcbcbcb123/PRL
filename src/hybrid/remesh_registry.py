"""Topology-independent material-point ownership for remeshed cell surfaces."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from route_h.contact_adhesion import global_closest_feature


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class SurfaceMaterialRegistry:
    """Persistent material state whose identity does not depend on triangle IDs."""

    point_ids: IntArray
    face_ids: IntArray
    barycentric: FloatArray
    reference_weights: FloatArray
    labels: tuple[str, ...]
    state: FloatArray

    def __post_init__(self) -> None:
        count = len(self.point_ids)
        if self.point_ids.shape != (count,):
            raise ValueError("point_ids must be one-dimensional")
        if len(np.unique(self.point_ids)) != count:
            raise ValueError("material point IDs must be unique")
        if self.face_ids.shape != (count,):
            raise ValueError("face_ids shape does not match point_ids")
        if self.barycentric.shape != (count, 3):
            raise ValueError("barycentric coordinates must have shape (n, 3)")
        if self.reference_weights.shape != (count,):
            raise ValueError("reference_weights shape does not match point_ids")
        if len(self.labels) != count:
            raise ValueError("labels length does not match point_ids")
        if self.state.ndim != 2 or self.state.shape[0] != count:
            raise ValueError("state must have shape (n, n_state)")
        if np.any(self.reference_weights < 0.0):
            raise ValueError("reference weights must be nonnegative")
        if not np.allclose(self.barycentric.sum(axis=1), 1.0, atol=1e-12):
            raise ValueError("barycentric coordinates must sum to one")
        if np.any(self.barycentric < -1e-12) or np.any(self.barycentric > 1.0 + 1e-12):
            raise ValueError("barycentric coordinates lie outside their host faces")


@dataclass(frozen=True)
class RebindReport:
    point_count: int
    maximum_position_error: float
    id_retention_fraction: float
    state_retention_residual: float
    weight_retention_residual: float


def material_point_positions(
    registry: SurfaceMaterialRegistry,
    vertices: FloatArray,
    faces: IntArray,
) -> FloatArray:
    if np.any(registry.face_ids < 0) or np.any(registry.face_ids >= len(faces)):
        raise ValueError("registry references an invalid face")
    triangles = vertices[faces[registry.face_ids]]
    return np.einsum("ni,nij->nj", registry.barycentric, triangles)


def rebind_registry(
    registry: SurfaceMaterialRegistry,
    old_vertices: FloatArray,
    old_faces: IntArray,
    new_vertices: FloatArray,
    new_faces: IntArray,
    *,
    maximum_distance: float = 1e-12,
) -> tuple[SurfaceMaterialRegistry, RebindReport]:
    """Rebind persistent points to a geometrically equivalent new triangulation."""

    if maximum_distance < 0.0:
        raise ValueError("maximum_distance must be nonnegative")
    old_positions = material_point_positions(registry, old_vertices, old_faces)
    new_face_ids = np.empty(len(registry.point_ids), dtype=np.int64)
    new_barycentric = np.empty((len(registry.point_ids), 3), dtype=np.float64)
    for index, point in enumerate(old_positions):
        owner = global_closest_feature(point, new_vertices, new_faces)
        if owner.squared_distance > maximum_distance * maximum_distance:
            raise ValueError(
                "material point cannot be rebound within the frozen distance: "
                f"id={int(registry.point_ids[index])}, "
                f"distance={np.sqrt(owner.squared_distance):.17g}"
            )
        new_face_ids[index] = owner.face_id
        new_barycentric[index] = owner.barycentric

    rebound = SurfaceMaterialRegistry(
        point_ids=registry.point_ids.copy(),
        face_ids=new_face_ids,
        barycentric=new_barycentric,
        reference_weights=registry.reference_weights.copy(),
        labels=tuple(registry.labels),
        state=registry.state.copy(),
    )
    new_positions = material_point_positions(rebound, new_vertices, new_faces)
    position_error = np.linalg.norm(new_positions - old_positions, axis=1)
    report = RebindReport(
        point_count=len(registry.point_ids),
        maximum_position_error=float(position_error.max(initial=0.0)),
        id_retention_fraction=float(
            np.count_nonzero(rebound.point_ids == registry.point_ids)
            / max(1, len(registry.point_ids))
        ),
        state_retention_residual=float(
            np.max(np.abs(rebound.state - registry.state), initial=0.0)
        ),
        weight_retention_residual=float(
            np.max(
                np.abs(rebound.reference_weights - registry.reference_weights),
                initial=0.0,
            )
        ),
    )
    return rebound, report


def scatter_material_forces(
    registry: SurfaceMaterialRegistry,
    vertices: FloatArray,
    faces: IntArray,
    material_forces: FloatArray,
) -> FloatArray:
    """Scatter point forces to host triangle nodes without changing resultants."""

    if material_forces.shape != (len(registry.point_ids), 3):
        raise ValueError("material_forces must have shape (n, 3)")
    nodal_forces = np.zeros_like(vertices, dtype=np.float64)
    for index, face_id in enumerate(registry.face_ids):
        face = faces[face_id]
        contribution = registry.barycentric[index, :, None] * material_forces[index]
        np.add.at(nodal_forces, face, contribution)
    return nodal_forces


def resultant_and_moment(
    positions: FloatArray,
    forces: FloatArray,
    *,
    origin: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    if positions.shape != forces.shape or positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("positions and forces must both have shape (n, 3)")
    if origin is None:
        origin = np.zeros(3, dtype=np.float64)
    resultant = forces.sum(axis=0)
    moment = np.cross(positions - origin, forces).sum(axis=0)
    return resultant, moment
