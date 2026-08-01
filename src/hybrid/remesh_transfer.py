"""Remesh-safe transfer of myocardial material fields.

This module is the executable Python reference for the C++ remesh contract.
Persistent material-point IDs own biology; triangle IDs only locate that state
on the current surface mesh.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray

from .remesh_registry import RebindReport, SurfaceMaterialRegistry, rebind_registry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class SurfaceRegion(str, Enum):
    APICAL = "apical"
    BASAL = "basal"
    LATERAL = "lateral"


class RemeshOperation(str, Enum):
    EDGE_SPLIT = "edge_split"
    EDGE_SWAP = "edge_swap"
    EDGE_MERGE = "edge_merge"


@dataclass(frozen=True)
class RemeshEvent:
    """One cell-local topology edit emitted by a cell-engine adapter."""

    cell_id: int
    operation: RemeshOperation
    before_revision: int
    after_revision: int

    def __post_init__(self) -> None:
        if self.cell_id < 0:
            raise ValueError("cell_id must be nonnegative")
        if self.before_revision < 0:
            raise ValueError("before_revision must be nonnegative")
        if self.after_revision <= self.before_revision:
            raise ValueError("after_revision must be greater than before_revision")
        if not isinstance(self.operation, RemeshOperation):
            raise TypeError("operation must be a RemeshOperation")


@dataclass(frozen=True)
class MyocardialMaterialField:
    """Biological state keyed only by persistent material-point ID."""

    point_ids: IntArray
    regions: tuple[SurfaceRegion, ...]
    fiber_directions: FloatArray
    active_state: FloatArray

    def __post_init__(self) -> None:
        count = len(self.point_ids)
        if self.point_ids.shape != (count,):
            raise ValueError("point_ids must be one-dimensional")
        if len(np.unique(self.point_ids)) != count:
            raise ValueError("myocardial material-point IDs must be unique")
        if len(self.regions) != count:
            raise ValueError("regions length does not match point_ids")
        if not all(isinstance(region, SurfaceRegion) for region in self.regions):
            raise TypeError("regions must contain SurfaceRegion values")
        if self.fiber_directions.shape != (count, 3):
            raise ValueError("fiber_directions must have shape (n, 3)")
        if self.active_state.ndim != 2 or self.active_state.shape[0] != count:
            raise ValueError("active_state must have shape (n, n_active_state)")
        if not np.all(np.isfinite(self.fiber_directions)):
            raise ValueError("fiber_directions must be finite")
        if not np.all(np.isfinite(self.active_state)):
            raise ValueError("active_state must be finite")
        if np.any(np.linalg.norm(self.fiber_directions, axis=1) <= 1e-14):
            raise ValueError("fiber directions must be nonzero")


@dataclass(frozen=True)
class RemeshTransferAudit:
    operation: RemeshOperation
    point_count: int
    region_retention_fraction: float
    active_state_residual: float
    maximum_fiber_norm_error: float
    maximum_fiber_tangency_error: float
    minimum_fiber_alignment: float
    rebind: RebindReport


def _host_normals(
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
) -> FloatArray:
    triangles = vertices[faces[face_ids]]
    normals = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 1e-14):
        raise ValueError("myocardial material point has a degenerate host face")
    return normals / lengths[:, None]


def transfer_myocardial_state(
    event: RemeshEvent,
    registry: SurfaceMaterialRegistry,
    field: MyocardialMaterialField,
    old_vertices: FloatArray,
    old_faces: IntArray,
    new_vertices: FloatArray,
    new_faces: IntArray,
    *,
    maximum_distance: float = 1e-12,
) -> tuple[SurfaceMaterialRegistry, MyocardialMaterialField, RemeshTransferAudit]:
    """Transfer one myocardial material field across one remesh event.

    The returned field is ordered exactly like the returned registry. Active
    variables and region identities are copied by persistent ID. Fibers are
    projected into the new host tangent plane, normalized, and sign-aligned
    with the pre-remesh director.
    """

    registry_ids = [int(value) for value in registry.point_ids]
    field_row = {int(value): row for row, value in enumerate(field.point_ids)}
    if set(registry_ids) != set(field_row):
        raise ValueError("registry and myocardial field must own the same point IDs")

    ordered_rows = np.asarray([field_row[value] for value in registry_ids], dtype=np.int64)
    old_regions = tuple(field.regions[row] for row in ordered_rows)
    registry_regions = tuple(SurfaceRegion(label) for label in registry.labels)
    if old_regions != registry_regions:
        raise ValueError("registry labels and myocardial regions disagree")

    old_fibers = np.asarray(field.fiber_directions[ordered_rows], dtype=np.float64)
    old_fibers = old_fibers / np.linalg.norm(old_fibers, axis=1)[:, None]
    old_normals = _host_normals(old_vertices, old_faces, registry.face_ids)
    old_tangency = np.abs(np.einsum("ni,ni->n", old_fibers, old_normals))
    if np.any(old_tangency > 1e-10):
        raise ValueError("pre-remesh fiber is not tangent to its host face")

    rebound, rebind = rebind_registry(
        registry,
        old_vertices,
        old_faces,
        new_vertices,
        new_faces,
        maximum_distance=maximum_distance,
    )
    new_normals = _host_normals(new_vertices, new_faces, rebound.face_ids)
    projected = old_fibers - np.einsum("ni,ni->n", old_fibers, new_normals)[:, None] * new_normals
    projected_norms = np.linalg.norm(projected, axis=1)
    if np.any(projected_norms <= 1e-14):
        raise ValueError("fiber transport collapsed during tangent-plane projection")
    projected /= projected_norms[:, None]
    signed_alignment = np.einsum("ni,ni->n", projected, old_fibers)
    projected[signed_alignment < 0.0] *= -1.0
    alignment = np.abs(np.einsum("ni,ni->n", projected, old_fibers))

    ordered_active_state = np.asarray(field.active_state[ordered_rows], dtype=np.float64)
    transferred = MyocardialMaterialField(
        point_ids=rebound.point_ids.copy(),
        regions=old_regions,
        fiber_directions=projected,
        active_state=ordered_active_state.copy(),
    )
    audit = RemeshTransferAudit(
        operation=event.operation,
        point_count=len(registry_ids),
        region_retention_fraction=float(
            sum(left is right for left, right in zip(old_regions, transferred.regions, strict=True))
            / max(1, len(old_regions))
        ),
        active_state_residual=float(
            np.max(
                np.abs(transferred.active_state - ordered_active_state),
                initial=0.0,
            )
        ),
        maximum_fiber_norm_error=float(
            np.max(
                np.abs(np.linalg.norm(transferred.fiber_directions, axis=1) - 1.0),
                initial=0.0,
            )
        ),
        maximum_fiber_tangency_error=float(
            np.max(
                np.abs(np.einsum("ni,ni->n", transferred.fiber_directions, new_normals)),
                initial=0.0,
            )
        ),
        minimum_fiber_alignment=float(np.min(alignment, initial=1.0)),
        rebind=rebind,
    )
    return rebound, transferred, audit
