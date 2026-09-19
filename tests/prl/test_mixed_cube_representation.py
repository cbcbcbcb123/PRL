"""Preparation only: no runtime calls, equilibrium solve, or scientific result."""
import copy
from itertools import product

import numpy as np
import pytest

from prl.fem.mixed_cube_spec import configuration as original_configuration
from prl.fem.mixed_cube_representation_spec import configuration, topology_dof_inventory
from prl.verification.simplex_lagrange import SimplexLagrange, equispaced_nodes


def test_pending_matrix_has_one_patch_one_quadrature_control_and_six_matched_mms():
    original = copy.deepcopy(original_configuration())
    config = configuration()
    assert config['authorization'] == 'pending_exact_eight_case_confirmation'
    assert config['native_status'] == 'not_run'
    assert len(config['cases']) == config['maximum_equilibrium_solves'] == 8
    assert config['cases'][0]['kind'] == 'cubic_volume'
    assert config['cases'][1]['u_degree'] == 2
    assert config['cases'][1]['role'] == 'quadrature_control'
    for n in (2, 4, 8):
        matched = [c for c in config['cases'][2:] if c['n'] == n]
        assert len(matched) == 2
        assert {c['p_degree'] for c in matched} == {1, 2}
        assert all(c['kind'] == 'mms' and c['kappa'] == 100 and c['u_degree'] == 3 for c in matched)
    assert config['quadrature_degree'] == 8
    assert config['mms_gates'] == original['mms_gates']
    assert config['patch_gates'] == original['patch_gates']
    assert config['solver'] == original['solver']
    assert config['resources']['gpu'] == config['resources']['automatic_retries'] == 0
    config['mms_gates']['fine_relative_u_H1'] = 999
    assert original_configuration() == original
    assert configuration()['mms_gates'] == original['mms_gates']


def test_runtime_requires_separate_explicit_authorization_and_create_only_output():
    from prl.runs.mixed_cube import batch_spec
    spec=batch_spec('representation_v01')
    assert spec['authorization']=='authorization: user_confirmed_representation_eight_cases_20260919'
    assert spec['contract'].endswith('representation_authorization_v01.md')
    assert spec['result'] != batch_spec('controls_v01')['result']
    assert configuration()['authorization']=='pending_exact_eight_case_confirmation'


@pytest.mark.parametrize('n,expected', [
    (2, {'p2p1': 402, 'p3p1': 1056, 'p3p2': 1154}),
    (4, {'p2p1': 2312, 'p3p1': 6716, 'p3p2': 7320}),
    (8, {'p2p1': 15468, 'p3p1': 47604, 'p3p2': 51788}),
])
def test_cost_inventory_uses_actual_mesh_incidence(n, expected):
    report = topology_dof_inventory(n)
    assert report['mixed_dofs'] == expected
    assert report['tetrahedra'] == 6 * n**3


@pytest.mark.parametrize('dimension,degree', product((2, 3), (1, 2, 3)))
def test_nodal_identity_partition_and_all_polynomial_derivatives(dimension, degree):
    nodes = equispaced_nodes(dimension, degree)
    nodes = nodes[np.random.default_rng(103).permutation(len(nodes))]
    element = SimplexLagrange(nodes, degree)
    values, _ = element.tabulate(nodes)
    np.testing.assert_allclose(values, np.eye(len(nodes)), atol=5e-13, rtol=0)
    weights = np.random.default_rng(19).dirichlet(np.ones(dimension + 1), size=19)
    points = weights[:, 1:]
    values, derivatives = element.tabulate(points)
    np.testing.assert_allclose(values.sum(axis=1), 1, atol=5e-13, rtol=0)
    np.testing.assert_allclose(derivatives.sum(axis=1), 0, atol=5e-13, rtol=0)
    # Independent monomial list, including all cubic cross terms.
    for exponent in product(range(degree + 1), repeat=dimension):
        if sum(exponent) > degree:
            continue
        samples = np.prod(nodes ** exponent, axis=1)
        exact = np.prod(points ** exponent, axis=1)
        np.testing.assert_allclose(values @ samples, exact, atol=5e-13, rtol=0)
        for axis in range(dimension):
            reduced = list(exponent)
            factor = reduced[axis]
            reduced[axis] = max(0, factor - 1)
            gradient = factor * np.prod(points ** reduced, axis=1)
            np.testing.assert_allclose(derivatives[:, :, axis] @ samples, gradient,
                                       atol=5e-13, rtol=0)


def test_cubic_volume_patch_has_quadratic_compatible_pressure():
    u_nodes = equispaced_nodes(3, 3)
    p_nodes = equispaced_nodes(3, 2)
    points = np.random.default_rng(7).dirichlet(np.ones(4), size=31)[:, 1:]
    basis, gradient = SimplexLagrange(u_nodes, 3).tabulate(points)
    pressure_basis, _ = SimplexLagrange(p_nodes, 2).tabulate(points)
    u_samples = np.column_stack((.002 * u_nodes[:, 0]**3, np.zeros((len(u_nodes), 2))))
    F = np.eye(3) + np.einsum('ai,qaj->qij', u_samples, gradient)
    pressure = pressure_basis @ (6 * p_nodes[:, 0]**2)
    np.testing.assert_allclose(basis @ u_samples, np.column_stack((.002 * points[:, 0]**3,
                              np.zeros((len(points), 2)))), atol=1e-16, rtol=0)
    np.testing.assert_allclose(np.linalg.det(F), 1 + .006 * points[:, 0]**2, atol=2e-15, rtol=0)
    np.testing.assert_allclose(pressure, 1000 * (np.linalg.det(F) - 1), atol=3e-13, rtol=0)


def test_higher_order_reconstruction_does_not_assume_basix_local_order():
    nodes = equispaced_nodes(3, 3)
    permutation = np.random.default_rng(8).permutation(len(nodes))
    points = np.array([[.1, .2, .3], [0., 0., 0.], [0., 1., 0.]])
    first = SimplexLagrange(nodes, 3).tabulate(points)
    second = SimplexLagrange(nodes[permutation], 3).tabulate(points)
    for original, reordered in zip(first, second):
        np.testing.assert_allclose(reordered, original[:, permutation], atol=5e-13, rtol=0)


def test_bad_nodes_and_nonfinite_evaluation_fail_closed():
    nodes = equispaced_nodes(3, 3)
    with pytest.raises(ValueError, match='Node count'):
        SimplexLagrange(nodes[:-1], 3)
    invalid = nodes.copy()
    invalid[0] = invalid[1]
    with pytest.raises(ValueError, match='Singular'):
        SimplexLagrange(invalid, 3)
    for value in (float('nan'), float('inf'), -1.):
        invalid = nodes.copy()
        invalid[0, 0] = value
        with pytest.raises(ValueError, match='Invalid simplex'):
            SimplexLagrange(invalid, 3)
    with pytest.raises(ValueError, match='Invalid evaluation'):
        SimplexLagrange(nodes, 3).tabulate([[float('nan'), 0, 0]])


def cubic_fixture(pressure_degree):
    from prl.fem.mixed_cube_spec import cube
    from prl.verification.mixed_cube import boundary_data, quadrature
    raw=cube(2)
    def conforming_nodes(degree):
        corner=np.vstack((np.zeros(3),np.eye(3)))
        rest=[point for point in equispaced_nodes(3,degree)
              if not any(np.array_equal(point,v) for v in corner)]
        reference=np.vstack((corner,rest)) if rest else corner
        bary=np.column_stack((1-reference.sum(axis=1),reference))
        coordinates=[]; lookup={}; cells=[]
        for tetra in raw['tetrahedra']:
            ids=[]
            for point in bary@raw['xyz'][tetra]:
                key=tuple(np.round(point,13))
                if key not in lookup:
                    lookup[key]=len(coordinates); coordinates.append(point)
                ids.append(lookup[key])
            cells.append(ids)
        return np.asarray(coordinates),np.asarray(cells),reference
    coordinates,cells,u_nodes=conforming_nodes(3)
    pressure_coordinates,pcells,p_nodes=conforming_nodes(pressure_degree)
    points,weights=quadrature(3); face_points,face_weights=quadrature(2)
    return dict(coordinates=coordinates,cells=cells,pressure_coordinates=pressure_coordinates,
        pressure_cells=pcells,u_reference_nodes=u_nodes,p_reference_nodes=p_nodes,
        u_degree=np.array(3),p_degree=np.array(pressure_degree),
        fixed=np.repeat((coordinates[:,0]==0)[:,None],3,axis=1),
        qpoints=points,qweights=weights,facet_qpoints=face_points,facet_qweights=face_weights,
        **boundary_data(coordinates,cells,3))


@pytest.mark.parametrize('pressure_degree,kind',[(1,'quadratic_volume'),(2,'cubic_volume')])
def test_integrated_cubic_export_reconstructs_equilibrium_and_each_face(pressure_degree,kind):
    from prl.verification.mixed_cube import (assembled,error_metrics,exact_fields,
                                            mapping_checks,numerical_face_forces)
    data=cubic_fixture(pressure_degree); case=dict(kind=kind,kappa=1000.)
    assert all(mapping_checks(data).values())
    assert data['cells'].shape[1]==20 and data['boundary_faces'].shape[1]==10
    state=dict(u=exact_fields(data['coordinates'],kind,1000.)['u'],
               pressure=exact_fields(data['pressure_coordinates'],kind,1000.)['pressure'])
    fields=assembled(data,state,case)
    assert np.linalg.norm(fields['force'][~data['fixed']])<1e-10
    assert np.linalg.norm(fields['weak'])<1e-12
    np.testing.assert_allclose(numerical_face_forces(data,state,case),fields['face_exact'],atol=1e-10,rtol=0)
    metrics,_=error_metrics(data,state,case)
    assert metrics['relative_u_H1']<1e-11 and metrics['relative_pressure_L2']<1e-11
    assert metrics['max_abs_J_error']<1e-12
    data['u_reference_nodes']=data['u_reference_nodes'][::-1].copy()
    assert not all(mapping_checks(data).values())


def test_candidate_accuracy_is_separate_from_control_and_original_qualification():
    from prl.verification.mixed_cube_representation import convergence
    cfg=configuration(); cases={}
    assert convergence(cases,cfg)['status']=='not_run'
    for case in cfg['cases']:
        n=case['n']
        factor=10 if case['role']=='displacement_control' else 1
        cases[case['name']]={'status':'passed','metrics':{
            'relative_u_L2':factor/n**4,'relative_u_H1':factor/n**3,
            'relative_pressure_L2':factor/n**3,'J_error_RMS':.001/n}}
    report=convergence(cases,cfg)
    assert report['status']=='passed' and report['pressure_contribution']=='passed'
    assert report['does_not_qualify_original_ventricle']
    assert report['original_eight_case_qualification']=='failed_unchanged'
    cases['mms_p3p2_n8']['metrics']['relative_u_H1']=.2
    assert convergence(cases,cfg)['status']=='failed'
    cases.pop('mms_p3p2_n4')
    assert convergence(cases,cfg)['status']=='blocked'
