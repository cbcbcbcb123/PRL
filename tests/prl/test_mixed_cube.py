"""Analytical and failure-policy tests; none invokes Docker or a FEM solve."""
from itertools import product
import math
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from prl.fem.mixed_cube_spec import configuration, cube, disposition
from prl.fem.mixed_material import passive_energy
from prl.verification.mixed_cube import (quadrature, exact_fields, exact_kinematics,
    boundary_data, assembled, error_metrics, numerical_face_forces, convergence)
from prl.verification.ventricle_3d import EDGES


def fixture():
    raw=cube(2); vertices=raw['xyz']; nodes=list(vertices); edges={}
    def midpoint(i,j):
        key=tuple(sorted((int(i),int(j))))
        if key not in edges:
            edges[key]=len(nodes); nodes.append((vertices[i]+vertices[j])/2)
        return edges[key]
    cells=np.array([list(t)+[midpoint(t[i],t[j]) for i,j in EDGES] for t in raw['tetrahedra']])
    coordinates=np.asarray(nodes); q,w=quadrature(3,4); fq,fw=quadrature(2,4)
    return {'coordinates':coordinates,'cells':cells,'pressure_coordinates':vertices,
        'pressure_cells':raw['tetrahedra'],'qpoints':q,'qweights':w,'facet_qpoints':fq,'facet_qweights':fw,
        'fixed':np.repeat((coordinates[:,0]==0)[:,None],3,axis=1),**boundary_data(coordinates,cells)}


def test_matrix_is_exactly_the_approved_eight_cases():
    cfg=configuration(); cases=cfg['cases']
    assert len(cases)==cfg['maximum_equilibrium_solves']==8
    assert [case['kind'] for case in cases[:2]]==['affine','shear']
    assert [(case['n'],case['kappa']) for case in cases[2:]]==[(n,k) for k in [100.,1000.] for n in [2,4,8]]
    assert cfg['resources']['gpu']==cfg['resources']['automatic_retries']==0


@pytest.mark.parametrize('n',[2,4,8])
def test_cube_geometry_count_volume_and_face_conformity(n):
    data=cube(n); v=data['xyz'][data['tetrahedra']]
    determinants=np.linalg.det(np.stack([v[:,i]-v[:,0] for i in [1,2,3]],axis=-1))
    assert len(v)==6*n**3 and determinants.min()>0
    assert determinants.sum()/6==pytest.approx(1.)
    assert np.array_equal(data['tetrahedra'],cube(n)['tetrahedra'])


def test_independent_quadrature_all_tetra_monomials_through_degree_eight():
    q,w=quadrature(3)
    for i,j,k in product(range(9),repeat=3):
        if i+j+k<=8:
            exact=math.factorial(i)*math.factorial(j)*math.factorial(k)/math.factorial(i+j+k+3)
            assert np.sum(w*q[:,0]**i*q[:,1]**j*q[:,2]**k)==pytest.approx(exact,rel=3e-13,abs=1e-15)


@pytest.mark.parametrize('kind',['affine','shear','mms'])
def test_analytic_reference_gradient_and_body_against_independent_differences(kind):
    points=np.random.default_rng(19).uniform(.1,.9,(13,3)); h=1e-5
    reference=exact_fields(points,kind,1000.)
    body=np.zeros_like(points)
    for axis in range(3):
        step=np.zeros(3); step[axis]=h
        plus=exact_fields(points+step,kind,1000.); minus=exact_fields(points-step,kind,1000.)
        np.testing.assert_allclose((plus['u']-minus['u'])/(2*h),reference['grad'][...,axis],rtol=2e-8,atol=1e-10)
        body-=(plus['P'][...,axis]-minus['P'][...,axis])/(2*h)
    np.testing.assert_allclose(body,reference['body'],rtol=2e-6,atol=3e-7)
    np.testing.assert_allclose(reference['pressure'],1000*(reference['J']-1),rtol=0,atol=0)
    assert reference['J'].min()>1-.002*np.pi-1e-12


@pytest.mark.parametrize('kind',['affine','shear'])
def test_nonzero_analytical_patch_reconstructs_volume_force_and_every_face(kind):
    data=fixture(); case={'kind':kind,'kappa':1000.}
    exact=exact_fields(data['coordinates'],kind,1000.)
    state={'u':exact['u'],'pressure':exact_fields(data['pressure_coordinates'],kind,1000.)['pressure']}
    report=assembled(data,state,case)
    assert np.linalg.norm(report['force'][~data['fixed']])<1e-10
    assert np.linalg.norm(report['weak'])<1e-12
    faces=numerical_face_forces(data,state,case)
    np.testing.assert_allclose(faces,report['face_exact'],rtol=1e-10,atol=1e-10)
    reaction=np.where(data['fixed'],report['force'],0.).sum(axis=0)
    np.testing.assert_allclose(reaction,report['face_exact'][0],rtol=1e-10,atol=1e-10)
    errors,_=error_metrics(data,state,case)
    assert errors['relative_u_L2']<1e-12 and errors['relative_u_H1']<1e-12
    assert errors['max_abs_J_error']<1e-12 and errors['projection_defect_RMS']<1e-12


def test_shared_energy_is_exactly_previous_ventricular_formula():
    rng=np.random.default_rng(7)
    for _ in range(20):
        F=np.eye(3)+rng.normal(size=(3,3))*.03; J=np.linalg.det(F); p=float(rng.normal())
        expected=1./2*(J**(-2/3)*np.sum(F*F)-3)+p*(J-1)-p**2/(2*1000.)
        assert passive_energy(F,J,p,1.,1000.,lambda a,b:np.sum(a*b))==expected


def test_stop_rules_preserve_failures_without_retry_or_dependency_continuation():
    soft={'status':'failed','hard_failures':[]}
    hard={'status':'failed','hard_failures':['assembly_and_load_agreement']}
    assert disposition('affine',soft)=='stop_batch'
    assert disposition('mms',soft)=='continue_registered_cases'
    assert disposition('mms',hard)=='stop_batch'
    assert convergence({},configuration())['status']=='not_run'


def test_missing_states_are_not_scientific_failures_or_successes():
    cfg=configuration()
    report=convergence({'patch_affine':{'status':'failed'}},cfg)
    assert report['status']=='not_run'
    assert all(group['status']=='not_run' for group in report['groups'].values())
    report=convergence({'mms_k100_n2':{'status':'passed'}},cfg)
    assert report['status']=='blocked'


def test_affine_patch_body_is_identically_zero_but_mms_body_is_not():
    points=np.random.default_rng(8).uniform(.1,.9,(31,3))
    for kind in ['affine','shear']:
        assert np.array_equal(exact_fields(points,kind,1000.)['body'],np.zeros_like(points))
    assert np.linalg.norm(exact_fields(points,'mms',1000.)['body'])>0


def test_reject_inverted_finite_state():
    from prl.verification.mixed_cube import piola
    with pytest.raises(ValueError,match='Nonpositive'):
        piola(np.diag([-1.,1.,1.])[None],np.zeros(1))


def test_convergence_gates_do_not_confuse_solver_success_with_field_qualification():
    cfg=configuration(); states={}
    for case in cfg['cases'][2:]:
        n=case['n']; states[case['name']]={'status':'passed','metrics':{
            'relative_u_L2':1/n**3,'relative_u_H1':1/n**2,'relative_pressure_L2':1/n**2,'J_error_RMS':.001/n}}
    assert convergence(states,cfg)['status']=='passed'
    states['mms_k1000_n8']['metrics']['relative_pressure_L2']=.2
    assert convergence(states,cfg)['status']=='failed'


def test_existing_result_refuses_before_runtime_and_cli_is_fem_scoped():
    from prl.runs.mixed_cube import run
    from prl.cli import _parser,FEM_RUN_COMMANDS
    assert 'fem-mixed-cube' in FEM_RUN_COMMANDS
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-mixed-cube']).command==command
    with patch('prl.runs.mixed_cube.result_path',side_effect=FileExistsError),patch('prl.runs.mixed_cube.read_docker') as runtime:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2])
        runtime.assert_not_called()


def test_v02_is_explicit_and_does_not_reuse_v01_container_or_directory():
    from prl.runs.mixed_cube import batch_spec,run,RESULT
    from prl.cli import _parser
    assert batch_spec('v01')['result']==RESULT
    assert batch_spec('v02')['result']!=RESULT
    assert batch_spec('v02')['container']!=batch_spec('v01')['container']
    assert _parser().parse_args(['run','fem-mixed-cube','--batch','v02']).batch=='v02'
    with pytest.raises(ValueError,match='explicitly authorized'):
        batch_spec('v03')
    with patch('prl.runs.mixed_cube.result_path',side_effect=FileExistsError),patch('prl.runs.mixed_cube.read_docker') as runtime:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2],'v02')
        runtime.assert_not_called()


def test_production_quadrature_can_miss_a_negative_p2_jacobian():
    from prl.runs.mixed_cube_delivery import describe_iterate
    data=fixture(); displacement=np.zeros_like(data['coordinates']); x=data['coordinates'][:,0]
    # Exactly represented quadratic: J=2X-0.0001. Interior rule is positive,
    # but X=0 boundary samples are negative; neither condition may be hidden.
    displacement[:,0]=x*x-1.0001*x
    pressure=np.zeros(len(data['pressure_coordinates']))
    data['mixed_u_map']=np.arange(displacement.size)
    data['mixed_p_map']=np.arange(displacement.size,displacement.size+pressure.size)
    state={'u':displacement,'pressure':pressure,'mixed_state':np.r_[displacement.ravel(),pressure]}
    report,arrays=describe_iterate(data,state)
    assert report['production']['minimum_J']>0
    assert report['extra']['minimum_J']==pytest.approx(-.0001)
    assert report['extra']['cells_with_nonpositive_J']>0
    assert not report['valid_at_sampled_points']
    assert len(arrays['extra_cell_minimum_J'])==48


def test_offline_iterate_diagnostics_reject_map_drift():
    from prl.runs.mixed_cube_delivery import describe_iterate
    data=fixture(); displacement=np.zeros_like(data['coordinates'])
    pressure=np.zeros(len(data['pressure_coordinates']))
    data['mixed_u_map']=np.arange(displacement.size)
    data['mixed_p_map']=np.arange(displacement.size,displacement.size+pressure.size)
    mixed=np.r_[displacement.ravel(),pressure]; mixed[0]=1
    with pytest.raises(ValueError,match='mapping drift'):
        describe_iterate(data,{'u':displacement,'pressure':pressure,'mixed_state':mixed})
