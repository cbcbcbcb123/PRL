"""Space-aware independent cube reconstruction; legacy P2/P1 path stays exact."""
from functools import lru_cache

import numpy as np

from . import ventricle_3d as legacy
from .simplex_lagrange import SimplexLagrange


@lru_cache(maxsize=24)
def _element(nodes, dimension, degree):
    return SimplexLagrange(np.asarray(nodes).reshape(-1, dimension), degree)


def _nodal_shape(nodes, degree, points):
    nodes = np.asarray(nodes)
    return _element(tuple(nodes.ravel()), nodes.shape[1], degree).tabulate(points)


def u_shape(data, points):
    if int(data.get('u_degree', 2)) == 2:
        return legacy.tetra_shape(points)[:2]
    return _nodal_shape(data['u_reference_nodes'], int(data['u_degree']), points)


def pressure_shape(data, points):
    if int(data.get('p_degree', 1)) == 1:
        return np.column_stack((1 - points.sum(axis=1), points))
    return _nodal_shape(data['p_reference_nodes'], int(data['p_degree']), points)[0]


def face_shape(data, points):
    if int(data.get('u_degree', 2)) == 2:
        return legacy.triangle_shape(points)
    return _nodal_shape(data['face_reference_nodes'], int(data['u_degree']), points)


def sample_points(data):
    points = legacy.extra_points()
    if int(data.get('u_degree', 2)) == 3:
        points = np.unique(np.vstack((points, data['u_reference_nodes'], data['p_reference_nodes'])), axis=0)
    return points


def kinematics(data, u, points):
    if int(data.get('u_degree', 2)) == 2:
        return legacy.kinematics(data, u, points)
    vertices = data['coordinates'][data['cells'][:, :4]]
    mapping = np.stack([vertices[:, i] - vertices[:, 0] for i in (1, 2, 3)], axis=-1)
    _, derivative = u_shape(data, points)
    gradients = np.einsum('qai,cij->cqaj', derivative, np.linalg.inv(mapping))
    F = np.eye(3) + np.einsum('cai,cqaj->cqij', u[data['cells']], gradients)
    bary = np.column_stack((1 - points.sum(axis=1), points))
    return F, np.linalg.det(F), gradients, np.abs(np.linalg.det(mapping)), bary, vertices


def mapping_checks(data):
    if int(data.get('u_degree', 2)) == 2 and int(data.get('p_degree', 1)) == 1:
        return legacy.mapping_checks(data)
    vertices = data['coordinates'][data['cells'][:, :4]]
    canonical_vertices = np.vstack((np.zeros(3), np.eye(3)))
    checks = {}
    for field, coordinates, cells in [('u', 'coordinates', 'cells'),
                                      ('p', 'pressure_coordinates', 'pressure_cells')]:
        nodes = data[field + '_reference_nodes']
        degree = int(data[field + '_degree'])
        basis, _ = _nodal_shape(nodes, degree, nodes)
        bary = np.column_stack((1 - nodes.sum(axis=1), nodes))
        expected = np.einsum('qa,cai->cqi', bary, vertices)
        actual = data[coordinates][data[cells]]
        checks[field + '_degree_nodes'] = bool(
            nodes.shape[0] == actual.shape[1]
            and np.max(np.abs(nodes[:4] - canonical_vertices)) < 1e-12
            and np.max(np.abs(expected - actual)) < 1e-12
            and np.max(np.abs(basis - np.eye(len(nodes)))) < 1e-12)
    # Audit the saved native-to-export relation independently of the exporter.
    if 'native_cells' in data or 'u_canonical_to_native_slots' in data:
        native = data.get('native_cells')
        slots = data.get('u_canonical_to_native_slots')
        valid = (native is not None and slots is not None
                 and native.shape == slots.shape == data['cells'].shape
                 and np.issubdtype(slots.dtype, np.integer)
                 and np.all(np.sort(slots, axis=1) == np.arange(slots.shape[1])))
        checks['u_export_permutation'] = bool(valid and np.array_equal(
            np.take_along_axis(native, slots, axis=1), data['cells']))
    checks['volume_weights'] = abs(float(data['qweights'].sum()) - 1/6) < 1e-13
    checks['surface_weights'] = abs(float(data['facet_qweights'].sum()) - .5) < 1e-13
    return checks
