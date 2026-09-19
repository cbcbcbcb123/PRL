"""Offline integration and pressure-force certificates; no Docker or FEM solves."""
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from prl.fem.mixed_cube_spec import cube
from prl.verification.ventricle_3d import EDGES
from prl.verification.mixed_cube import assembled, boundary_data, exact_fields, quadrature
from prl.verification.mixed_cube_loads import integrate, pressure_certificate


def mesh_fixture():
    raw = cube(2)
    vertices = raw['xyz']
    nodes, edges = list(vertices), {}
    cells = []
    for cell in raw['tetrahedra']:
        middle = []
        for first, second in EDGES:
            edge = tuple(sorted((int(cell[first]), int(cell[second]))))
            if edge not in edges:
                edges[edge] = len(nodes)
                nodes.append((vertices[edge[0]] + vertices[edge[1]]) / 2)
            middle.append(edges[edge])
        cells.append(list(cell) + middle)
    nodes, cells = np.asarray(nodes), np.asarray(cells)
    points, weights = quadrature(3, 4)
    facet_points, facet_weights = quadrature(2, 4)
    return {'coordinates': nodes, 'cells': cells, 'pressure_coordinates': vertices,
            'pressure_cells': raw['tetrahedra'], 'qpoints': points, 'qweights': weights,
            'facet_qpoints': facet_points, 'facet_qweights': facet_weights,
            'fixed': np.repeat((nodes[:, 0] == 0)[:, None], 3, axis=1),
            **boundary_data(nodes, cells)}


@pytest.mark.parametrize('kind', ['affine', 'shear', 'mms'])
def test_chunked_assembly_matches_existing_independent_verifier(kind):
    data = mesh_fixture()
    case = {'kind': kind, 'kappa': 100.}
    state = {'u': exact_fields(data['coordinates'], kind, 100.)['u'],
             'pressure': exact_fields(data['pressure_coordinates'], kind, 100.)['pressure']}
    expected = assembled(data, state, case)
    result = integrate(data, state, case, coupling=True, chunk_size=7)
    for name in ['force', 'weak', 'external']:
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-10, atol=3e-14)
    if kind != 'mms':
        np.testing.assert_allclose((result['B'].T @ state['pressure']).reshape(state['u'].shape),
                                  result['exact_pressure'], atol=3e-14)


def test_pressure_force_projection_detects_only_the_nonrepresentable_component():
    operator = csr_matrix([[1., 0., 1., 0.], [0., 2., 0., 0.]])
    fixed = np.zeros(4, dtype=bool)
    coefficients = np.array([2., 3.])
    representable = operator.T @ coefficients
    report, arrays = pressure_certificate(operator, representable, fixed)
    assert report['unrepresented_force_norm'] < 1e-14
    load = representable + np.array([1., 0., -1., 2.])
    report, arrays = pressure_certificate(operator, load, fixed)
    np.testing.assert_allclose(arrays['unrepresented_pressure_force'], [1., 0., -1., 2.])
    assert report['pressure_virtual_work'] == pytest.approx(6.)
    assert report['normal_equation_scaled_residual'] < 1e-14


def test_fixed_virtual_displacements_are_excluded_from_projection():
    operator = csr_matrix([[1., 0., 1.]])
    fixed = np.array([False, False, True])
    report, arrays = pressure_certificate(operator, np.array([2., 4., 999.]), fixed)
    np.testing.assert_allclose(arrays['unrepresented_pressure_force'], [0., 4., 0.])
    assert report['pressure_virtual_work'] == pytest.approx(16.)


def test_exact_virtual_work_consistency_and_pressure_scaling():
    data = mesh_fixture()
    case = {'kind': 'mms', 'kappa': 100.}
    state = {'u': exact_fields(data['coordinates'], 'mms', 100.)['u'],
             'pressure': exact_fields(data['pressure_coordinates'], 'mms', 100.)['pressure']}
    first = integrate(data, state, case, 8, coupling=True)
    second = integrate(data, state, {**case, 'kappa': 1000.}, 8, coupling=True)
    free = ~data['fixed']
    np.testing.assert_allclose((first['exact_iso'] + first['exact_pressure'])[free],
                              first['external'][free], atol=1e-11)
    np.testing.assert_allclose(second['exact_pressure'], 10 * first['exact_pressure'], atol=1e-12)
    np.testing.assert_allclose(second['B'].toarray(), first['B'].toarray(), atol=0)
    report, _ = pressure_certificate(first['B'], first['exact_pressure'], data['fixed'])
    assert report['unrepresented_fraction'] > 1e-3


def test_nonpositive_saved_deformation_stops_offline_analysis():
    data = mesh_fixture()
    state = {'u': -2 * data['coordinates'], 'pressure': np.zeros(len(data['pressure_coordinates']))}
    with pytest.raises(ValueError, match='Nonpositive'):
        integrate(data, state, {'kind': 'mms', 'kappa': 100.})
