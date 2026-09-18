"""Independent synthetic algebra/geometry/protocol fixtures, not equilibria."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from prl.fem.ventricle_geometry import configuration,half_ellipsoid,geometry_metrics
from prl.verification.ventricle_3d import (
    EDGES,tetra_shape,triangle_shape,kinematics,fields,cavity,mapping_checks,extra_points)
from prl.runs.ventricle_3d import run


def fixture():
    config=configuration(); case={'name':'M0','segments':8,'bands':2,'radial':[1,1,1]}
    raw=half_ellipsoid(case,config); vertices=raw['xyz']; nodes=list(vertices); edge_map={}
    def midpoint(i,j):
        key=tuple(sorted((int(i),int(j))))
        if key not in edge_map:
            edge_map[key]=len(nodes); nodes.append((vertices[i]+vertices[j])/2)
        return edge_map[key]
    cells=np.array([list(t)+[midpoint(t[i],t[j]) for i,j in EDGES] for t in raw['tetrahedra']])
    faces=np.array([list(t)+[midpoint(t[i],t[j]) for i,j in [(1,2),(0,2),(0,1)]] for t in raw['inner_faces']])
    g,w=np.polynomial.legendre.leggauss(3); g=(g+1)/2; w=w/2
    q=np.array([[a,(1-a)*b,(1-a)*(1-b)*c] for a in g for b in g for c in g])
    qw=np.array([w[i]*w[j]*w[k]*(1-a)**2*(1-b) for i,a in enumerate(g) for j,b in enumerate(g) for k,c in enumerate(g)])
    fq=np.array([[a,(1-a)*b] for a in g for b in g])
    fw=np.array([w[i]*w[j]*(1-a) for i,a in enumerate(g) for j,b in enumerate(g)])
    nodes=np.asarray(nodes)
    data={'coordinates':nodes,'cells':cells,'pressure_coordinates':vertices,'pressure_cells':raw['tetrahedra'],
          'layers':raw['layers'],'qpoints':q,'qweights':qw,'facet_qpoints':fq,'facet_qweights':fw,
          'inner_faces':faces,'fixed':np.repeat((np.abs(nodes[:,2])<1e-12)[:,None],3,axis=1)}
    state={'u':np.zeros_like(nodes),'pressure':np.zeros(len(vertices)),'load':0.,'activation':0.}
    return data,state,config


@pytest.mark.parametrize('name',['M0','M1'])
def test_geometry_conformity(name):
    cfg=configuration(); case=next(c for c in cfg['meshes'] if c['name']==name)
    raw=half_ellipsoid(case,cfg); metrics=geometry_metrics(raw,cfg,name)
    assert metrics['status']=='passed'
    assert metrics['tetrahedra']==(1344 if name=='M0' else 3960)
    assert np.array_equal(raw['xyz'],half_ellipsoid(case,cfg)['xyz'])


def test_geometry_rejects_reversed_tetrahedron():
    cfg=configuration(); raw=half_ellipsoid(cfg['meshes'][0],cfg)
    raw['tetrahedra'][0,[1,2]]=raw['tetrahedra'][0,[2,1]]
    assert not geometry_metrics(raw,cfg,'M0')['checks']['positive_tetrahedra']


def test_basis_partition_kronecker_and_order():
    v=np.vstack((np.zeros(3),np.eye(3)))
    locations=np.vstack((v,[(v[i]+v[j])/2 for i,j in EDGES]))
    n,_,_=tetra_shape(locations)
    assert np.allclose(n,np.eye(10))
    n,dn,_=tetra_shape(extra_points())
    assert np.max(np.abs(n.sum(axis=1)-1))<1e-14
    assert np.max(np.abs(dn.sum(axis=1)))<1e-14
    tri=np.array([[0,0],[1,0],[0,1],[.5,.5],[0,.5],[.5,0]])
    assert np.allclose(triangle_shape(tri)[0],np.eye(6))
    data,_,_=fixture(); assert all(mapping_checks(data).values())
    data['cells'][:,[4,5]]=data['cells'][:,[5,4]]
    assert not mapping_checks(data)['p2_order']


def test_affine_deformation_and_pressure_constraint():
    data,state,cfg=fixture(); F=np.array([[1.01,.02,0],[0,.99,0],[0,0,1.001]])
    state['u']=data['coordinates']@(F-np.eye(3)).T
    state['pressure'][:]=cfg['kappa']*(np.linalg.det(F)-1)
    saved=fields(data,state,cfg)
    assert np.max(np.abs(saved['F']-F))<1e-13
    assert np.max(np.abs(saved['J']-np.linalg.det(F)))<1e-13
    assert np.linalg.norm(saved['weak'])<1e-13


def test_zero_stress_and_rigid_rotation_objectivity():
    data,state,cfg=fixture(); saved=fields(data,state,cfg)
    assert np.max(np.abs(saved['stress']))<1e-12
    angle=.37; Q=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
    state['u']=data['coordinates']@(Q-np.eye(3)).T
    rotated=fields(data,state,cfg)
    assert np.max(np.abs(rotated['stress']))<1e-10
    assert np.max(np.abs(rotated['J']-1))<1e-12


def test_cavity_reference_and_virtual_work():
    data,state,cfg=fixture(); volume,force=cavity(data,state['u'],.02)
    faces=data['coordinates'][data['inner_faces'][:,:3]]
    exact=np.einsum('fi,fi->',faces[:,0],np.cross(faces[:,1],faces[:,2]))/6
    assert abs(volume-exact)<1e-13
    delta=.01*np.cos(data['coordinates']); delta[data['fixed']]=0
    step=1e-5
    vp,_=cavity(data,step*delta,.02); vm,_=cavity(data,-step*delta,.02)
    assert abs(np.sum(force*delta)-.02*(vp-vm)/(2*step))<1e-10


def test_active_energy_force_localization_and_objectivity():
    data,state,cfg=fixture(); state['activation']=.1
    initial=fields(data,state,cfg)
    assert np.max(np.abs(initial['active_stress'][data['layers']!=3]))==0
    assert abs(initial['active_energy'])<1e-12
    delta=.01*np.sin(data['coordinates']+.3); delta[data['fixed']]=0; step=1e-5
    ep=fields(data,{**state,'u':step*delta},cfg)['active_energy']
    em=fields(data,{**state,'u':-step*delta},cfg)['active_energy']
    assert abs(np.sum(initial['active_force']*delta)-(ep-em)/(2*step))<1e-9
    angle=.37; Q=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
    rotated=fields(data,{**state,'u':data['coordinates']@(Q-np.eye(3)).T},cfg)
    expected=np.einsum('ij,cqjk,lk->cqil',Q,initial['active_stress'],Q)
    assert np.max(np.abs(rotated['active_stress']-expected))<1e-11


def test_scope_and_cli():
    from prl.cli import _parser,FEM_RUN_COMMANDS
    cfg=configuration()
    assert len(cfg['meshes'])*len(cfg['states'])==cfg['maximum_equilibrium_solves']==14
    assert cfg['resources']=={'seconds':1800,'threads':1,'gpu':0,'automatic_retries':0}
    assert max(s['p'] for s in cfg['states'])==.02
    assert max(s['Ta'] for s in cfg['states'])==.1
    assert 'fem-idealized-3d' in FEM_RUN_COMMANDS
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-idealized-3d']).command==command


def test_create_only_before_runtime_probe():
    with patch('prl.runs.ventricle_3d.result_path',side_effect=FileExistsError),patch('prl.runs.ventricle_3d.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2])
        docker.assert_not_called()


def test_retained_scalar_pressure_row_layout_matches_flat_layout():
    # Actual F6-S2 payload: pressure was saved as (1,N), not (N,).
    data,state,cfg=fixture()
    expected=fields(data,state,cfg)
    row={**state,'pressure':state['pressure'][None,:]}
    actual=fields(data,row,cfg)
    for key in ['F','J','stress','active_stress','force','weak']:
        assert np.array_equal(actual[key],expected[key])


@pytest.mark.parametrize('shape',[(2,2),(2,0),(0,)])
def test_rejects_unrecognized_pressure_layout(shape):
    data,state,cfg=fixture()
    with pytest.raises(ValueError,match='pressure layout'):
        fields(data,{**state,'pressure':np.zeros(shape)},cfg)


def test_render_cutaway_does_not_change_input_mesh():
    from prl.rendering.ventricle_3d import boundary_faces
    data,_,_=fixture(); before={k:v.copy() for k,v in data.items()}
    faces,owners=boundary_faces(data)
    assert faces.shape[1]==6 and len(faces)==len(owners)>0
    assert len({tuple(sorted(face[:3])) for face in faces})==len(faces)
    assert np.all(data['coordinates'][data['cells'][owners,:4]].mean(axis=1)[:,1]>0)
    assert all(np.array_equal(data[k],v) for k,v in before.items())


def test_resume_only_remaining_thirteen_with_original_branch_seeds():
    from types import SimpleNamespace
    from prl.fem.ventricle_protocol import advance_case,remaining_states
    cfg={**configuration(),'reuse_m0_zero':True}; calls=[]
    zero=np.array([123.])
    for name in ['M0','M1']:
        def solve(spec,initial):
            calls.append((name,spec['label'],initial.copy()))
            return np.array([len(calls)],dtype=float)
        solid=SimpleNamespace(name=name,w=SimpleNamespace(x=SimpleNamespace(array=np.zeros(1))),solve=solve)
        states={'zero':zero.copy()} if name=='M0' else {}
        advance_case(solid,cfg,states,lambda spec:None,lambda spec:None)
        active_seed=next(x[2] for x in calls if x[:2]==(name,'active_1'))
        combined_seed=next(x[2] for x in calls if x[:2]==(name,'combined_1'))
        assert np.array_equal(active_seed,states['zero'])
        assert np.array_equal(combined_seed,states['pressure_2'])
    assert len(calls)==13 and calls[0][:2]==('M0','pressure_1')
    assert len(remaining_states(configuration(),'M0'))==7


def test_resume_does_not_retry_or_continue_after_first_failure():
    from types import SimpleNamespace
    from prl.fem.ventricle_protocol import advance_case
    cfg={**configuration(),'reuse_m0_zero':True}; attempted=[]; accepted=[]
    def fail(spec,initial):
        raise ValueError('synthetic gate failure')
    solid=SimpleNamespace(name='M0',w=SimpleNamespace(x=SimpleNamespace(array=np.zeros(1))),solve=fail)
    with pytest.raises(ValueError,match='synthetic gate failure'):
        advance_case(solid,cfg,{'zero':np.zeros(1)},attempted.append,accepted.append)
    assert len(attempted)==1 and attempted[0]['label']=='pressure_1' and not accepted


def test_restart_allows_only_known_map_layout_change():
    from prl.fem.ventricle_protocol import restart_identity
    current={'coordinates':np.arange(6).reshape(2,3),'mixed_u_map':np.arange(6),'mixed_p_map':np.arange(6,8)}
    retained={k:(v[None,:] if k.startswith('mixed') else v.copy()) for k,v in current.items()}
    state={'mixed_state':np.arange(8),'u':np.arange(6).reshape(2,3),'pressure':np.arange(6,8)[None,:],
           'load':0.,'activation':0.}
    assert all(restart_identity(current,retained,state,8).values())
    altered={**current,'mixed_p_map':current['mixed_p_map'][::-1]}
    assert not all(restart_identity(altered,retained,state,8).values())
    altered={**current,'coordinates':current['coordinates']+1}
    assert not all(restart_identity(altered,retained,state,8).values())
    assert not all(restart_identity(current,retained,state,9).values())


def test_resume_create_only_and_cli():
    from prl.cli import _parser
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-idealized-3d','--resume-qualified-zero']).resume_qualified_zero
    with patch('prl.runs.ventricle_3d.result_path',side_effect=FileExistsError),patch('prl.runs.ventricle_3d.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2],resume=True)
        docker.assert_not_called()
