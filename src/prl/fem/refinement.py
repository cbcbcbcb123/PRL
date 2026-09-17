"""Conforming midpoint refinement of an already assembled triangular FEM.

This operation refines the discrete problem, not its geometry or direction
field.  Polygon boundaries remain straight, all parent triangle vertices are
retained, and each child inherits its parent's material and eigenstrain.
Uniform refinement preserves triangle shape: it does not repair bad angles.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .active_ellipse import (
    EllipticModel,
    IntArray,
    MeshLevel,
    assemble_model,
    polygon_area,
    signed_triangle_areas,
)


def _edges(cells: IntArray) -> tuple[IntArray, IntArray, IntArray]:
    pairs = cells[:, ((0, 1), (1, 2), (2, 0))]
    ordered = np.sort(pairs, axis=2).reshape(-1, 2)
    edges, inverse, counts = np.unique(
        ordered, axis=0, return_inverse=True, return_counts=True
    )
    return edges, inverse.reshape(-1, 3), counts


def refine_model(model: EllipticModel, label: str) -> tuple[EllipticModel, IntArray]:
    """Split every CCW triangle into four using one midpoint per shared edge.

    Original nodes retain their indices; midpoint nodes follow in lexicographic
    endpoint order.  Four consecutive child cells correspond to one parent.
    The returned parent indices make field inheritance independently auditable.

    ``MeshLevel`` resolution counters are doubled as ancestry metadata only:
    the refined connectivity is authoritative and is not a new structured-ring
    geometry.  Both named boundary loops retain their original CCW convention.
    Only the current three-layer assembly material family is supported; an
    altered material matrix raises an error instead of silently changing it.
    The parent's rigid-motion gauge is extended with zero columns on midpoint
    degrees of freedom.  Its original physical frame is therefore preserved;
    the unweighted node-average gauge is not redefined after refinement.
    """
    if not isinstance(label, str) or not label.strip():
        raise ValueError("a nonempty refinement label is required")
    edges, edge_ids, counts = _edges(model.cells)
    if np.any((counts < 1) | (counts > 2)):
        raise ValueError("refinement requires a conforming manifold triangle mesh")
    boundary_edges = set(map(tuple, edges[counts == 1].tolist()))
    declared_edges: set[tuple[int, int]] = set()
    midpoint_lookup = {
        tuple(edge): len(model.coordinates) + edge_id
        for edge_id, edge in enumerate(edges.tolist())
    }

    def split_boundary(loop: IntArray) -> IntArray:
        refined = np.empty(2 * len(loop), dtype=np.int64)
        for index, first in enumerate(loop):
            second = loop[(index + 1) % len(loop)]
            edge = tuple(sorted((int(first), int(second))))
            if edge not in boundary_edges or edge in declared_edges:
                raise ValueError("named boundary loops must cover distinct exterior edges")
            declared_edges.add(edge)
            refined[2 * index] = first
            refined[2 * index + 1] = midpoint_lookup[edge]
        return refined

    inner_nodes = split_boundary(model.inner_nodes)
    outer_nodes = split_boundary(model.outer_nodes)
    if declared_edges != boundary_edges:
        raise ValueError("named boundary loops do not cover the complete mesh boundary")

    midpoints = np.mean(model.coordinates[edges], axis=1)
    coordinates = np.concatenate((model.coordinates, midpoints), axis=0)
    midpoint_ids = edge_ids + len(model.coordinates)
    first, second, third = model.cells.T
    first_second, second_third, third_first = midpoint_ids.T
    children = np.stack(
        (
            np.column_stack((first, first_second, third_first)),
            np.column_stack((first_second, second, second_third)),
            np.column_stack((third_first, second_third, third)),
            np.column_stack((first_second, second_third, third_first)),
        ),
        axis=1,
    ).reshape(-1, 3)
    parent_cells = np.repeat(np.arange(len(model.cells), dtype=np.int64), 4)
    level = MeshLevel(
        label,
        2 * model.level.ntheta,
        tuple(2 * value for value in model.level.radial_intervals),
    )
    refined_model = assemble_model(
        level,
        coordinates,
        children,
        model.cell_layers[parent_cells],
        inner_nodes,
        outer_nodes,
        model.active_strain_unit[parent_cells],
    )
    if any(
        not np.array_equal(parent, child)
        for parent, child in zip(
            model.material_matrices, refined_model.material_matrices, strict=True
        )
    ):
        raise ValueError("refinement cannot silently replace the parent's material matrices")
    refined_model.constraints = sp.hstack(
        (
            model.constraints,
            sp.csr_matrix((model.constraints.shape[0], 2 * len(midpoints))),
        ),
        format="csr",
    )
    return refined_model, parent_cells


def geometric_quality(model: EllipticModel) -> dict[str, float | int]:
    """Return dimensionless angle/shape diagnostics, without pass/fail policy."""
    points = model.coordinates[model.cells]
    edge_vectors = np.roll(points, -1, axis=1) - points
    squared_lengths = np.sum(edge_vectors**2, axis=2)
    lengths = np.sqrt(squared_lengths)
    areas = signed_triangle_areas(model.coordinates, model.cells)
    quality = 4.0 * np.sqrt(3.0) * areas / np.sum(squared_lengths, axis=1)
    angles = []
    for corner in range(3):
        previous = points[:, (corner - 1) % 3] - points[:, corner]
        following = points[:, (corner + 1) % 3] - points[:, corner]
        cosine = np.sum(previous * following, axis=1) / (
            np.linalg.norm(previous, axis=1) * np.linalg.norm(following, axis=1)
        )
        angles.append(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
    return {
        "node_count": len(model.coordinates),
        "triangle_count": len(model.cells),
        "minimum_signed_area": float(np.min(areas)),
        "minimum_mean_ratio": float(np.min(quality)),
        "median_mean_ratio": float(np.median(quality)),
        "minimum_angle_degrees": float(np.min(angles)),
        "maximum_edge_aspect_ratio": float(np.max(np.max(lengths, axis=1) / np.min(lengths, axis=1))),
        "inner_polygon_area": polygon_area(model.coordinates[model.inner_nodes]),
        "outer_polygon_area": polygon_area(model.coordinates[model.outer_nodes]),
    }
