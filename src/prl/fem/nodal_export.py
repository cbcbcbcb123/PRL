"""Canonical nodal export for the registered affine-tetrahedron cube cases.

Only the exported gather map changes. Native DOLFINx function spaces, vectors,
assembly and boundary conditions retain their native orientation conventions.
This is not an export adapter for curved or non-nodal finite elements.
"""
import numpy as np


def canonical_nodal_cells(coordinates, native_cells, reference_nodes):
    """Return reference-ordered global indices and canonical-to-native slots.

    Coordinate matching resolves the P3 edge reversals already incorporated in
    DOLFINx's global DOF map. Each cell must admit a unique bijection; ambiguous,
    degenerate or mismatched data fail closed, without moving any node.
    """
    coordinates = np.asarray(coordinates)
    native_cells = np.asarray(native_cells)
    nodes = np.asarray(reference_nodes)
    vertices = np.vstack((np.zeros(3), np.eye(3)))
    if (coordinates.ndim != 2 or coordinates.shape[1] != 3
            or native_cells.ndim != 2 or nodes.shape != (native_cells.shape[1], 3)
            or native_cells.shape[1] < 4 or not np.issubdtype(native_cells.dtype, np.integer)
            or not np.isfinite(coordinates).all() or not np.isfinite(nodes).all()
            or np.any(native_cells < 0) or np.any(native_cells >= len(coordinates))
            or not np.allclose(nodes[:4], vertices, atol=1e-13, rtol=0)):
        raise ValueError('Invalid affine nodal export arrays')
    positions = coordinates[native_cells]
    corners = positions[:, :4]
    mapping = np.stack([corners[:, i] - corners[:, 0] for i in (1, 2, 3)], axis=-1)
    if np.any(np.abs(np.linalg.det(mapping)) < 1e-14):
        raise ValueError('Degenerate affine cell')
    barycentric = np.column_stack((1 - nodes.sum(axis=1), nodes))
    expected = np.einsum('qa,cai->cqi', barycentric, corners)
    distance = np.max(np.abs(expected[:, :, None, :] - positions[:, None, :, :]), axis=-1)
    matches = distance <= 1e-12
    if not (np.all(matches.sum(axis=1) == 1) and np.all(matches.sum(axis=2) == 1)):
        raise ValueError('No unique coordinate bijection for affine nodal export')
    slots = matches.argmax(axis=2)
    if not np.all(slots[:, :4] == np.arange(4)):
        raise ValueError('Export vertex order changed')
    return np.take_along_axis(native_cells, slots, axis=1), slots
