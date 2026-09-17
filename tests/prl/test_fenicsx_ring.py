"""Analytic geometry and independent audit regressions; no containers or solves."""

import numpy as np

from prl.fem.ring_geometry import configuration, annulus, geometry_metrics
from prl.verification.fenicsx_ring import shape, fields, cavity, analytic_c, state_audit
from prl.runs.fenicsx_runtime import container_command, IMAGE


def triangle_mesh():
    coordinates=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,.5],[0.,.5],[.5,0.]])+[2.,0.]
    return {'coordinates':coordinates,'cells':np.arange(6)[None],
            'pressure_cells':np.arange(3)[None], 'layers':np.array([1]),
            'qpoints':np.array([[1/6,1/6],[2/3,1/6],[1/6,2/3]]),
            'qweights':np.full(3,1/6)}


def test_frozen_geometry_gates():
    cfg=configuration()
    for case,expected,bound in zip(cfg['meshes'],[896,3584],[.002,.0005]):
        xy,cells,labels=annulus(case['segments'],case['radial'],cfg['radii'])
        result=geometry_metrics(xy,cells,labels,case['segments'],cfg['radii'])
        assert result['cells']==expected
        assert result['minimum_signed_area']>0
        assert result['minimum_angle_degrees']>=20
        assert result['circle_area_relative_error']<=bound
        assert result['boundary_count_correct'] and result['edge_manifold']


def test_shape_quadratic_patch():
    points=np.array([[.12,.23],[.6,.2]])
    n,dn,bary=shape(points)
    nodal=np.array([[0,0],[1,0],[0,1],[.5,.5],[0,.5],[.5,0.]])
    assert np.allclose(n.sum(axis=1),1)
    assert np.allclose(dn.sum(axis=1),0)
    assert np.allclose(n@(nodal[:,0]**2),points[:,0]**2)
    assert np.allclose(np.einsum('qai,a->qi',dn,nodal[:,0]**2),np.column_stack((2*points[:,0],np.zeros(2))))


def test_rigid_rotation_and_pressure_stress():
    data=triangle_mesh()
    angle=.37
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    u=data['coordinates']@(rotation-np.eye(2)).T+np.array([.3,-.2])
    state={'u':u,'pressure':np.full(3,2.),'activation':.1}
    result=fields(data,state)
    assert np.allclose(result['J'],1.,atol=1e-14)
    assert np.allclose(result['stress'],2*np.eye(3),atol=1e-13)
    assert np.max(np.abs(result['active_stress']))==0


def test_active_only_in_myocardium():
    data=triangle_mesh()
    data['layers'][:]=3
    state={'u':np.zeros_like(data['coordinates']),'pressure':np.zeros(3),'activation':.1}
    result=fields(data,state)
    assert np.allclose(np.trace(result['active_stress'],axis1=-2,axis2=-1),.1)
    assert np.allclose(result['stress'],result['active_stress'])


def test_pressure_singleton_export_is_losslessly_accepted():
    data=triangle_mesh()
    state={'u':np.zeros_like(data['coordinates']),'pressure':np.full(3,.04),'activation':0.}
    one=fields(data,state)
    state['pressure']=state['pressure'][None,:]
    two=fields(data,state)
    for key in ['stress','pressure_residual','force']:
        assert np.array_equal(one[key],two[key])


def test_closed_pressure_and_area_work():
    n=12
    theta=2*np.pi*np.arange(n)/n
    corners=np.column_stack((np.cos(theta),np.sin(theta)))
    mids=(corners+np.roll(corners,-1,axis=0))/2
    data={'coordinates':np.vstack((corners,mids)),
          'inner_edges':np.array([[i,n+i,(i+1)%n] for i in range(n)])}
    u=.2*data['coordinates']+np.array([.3,-.5])
    area,force,moment=cavity(data,u,.04)
    assert abs(area-n*np.sin(2*np.pi/n)/2*1.2**2)<1e-13
    assert np.linalg.norm(force.sum(axis=0))<1e-14
    assert abs(moment)<1e-14
    delta=data['coordinates']*.1
    step=1e-5
    ap=cavity(data,u+step*delta,.04)[0]
    am=cavity(data,u-step*delta,.04)[0]
    assert abs(.04*(ap-am)/(2*step)-np.sum(force*delta))<1e-11


def test_incompressible_reference_monotone():
    values=[analytic_c(p) for p in configuration()['passive_loads']]
    assert values[0]==0 and np.all(np.diff(values)>0)


def test_container_constraints_preserve_library_path():
    args=container_command('workspace','name','script','output')
    assert '--pull=never' in args and '--network=none' in args and '--read-only' in args
    assert '--cpus=1' in args and IMAGE in args and '--rm' not in args
    assert 'PYTHONPATH=/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:' in args
    assert '/root/.cache:rw,exec,nosuid,nodev,size=536870912' in args


def test_public_cli_recognizes_fenicsx_without_host_import():
    import sys
    from prl.cli import _parser, FEM_RUN_COMMANDS
    parsed=_parser().parse_args(['verify','fem-fenicsx-ring','--stage','passive'])
    assert parsed.stage=='passive'
    assert 'fem-fenicsx-ring' in FEM_RUN_COMMANDS
    assert 'dolfinx' not in sys.modules


def test_saved_state_audit_is_strict_json_and_rejects_corrupted_F():
    import json
    data=triangle_mesh()
    data['inner_edges']=np.array([[0,5,1],[1,3,2],[2,4,0]])
    data['fixed']=np.zeros((6,2),dtype=bool)
    data['fixed'][0,0]=True
    state={'u':np.zeros((6,2)),'pressure':np.zeros((1,3)),'activation':.1,'load':0.,
           'F':np.broadcast_to(np.eye(3),(1,3,3,3)).copy(),'J':np.ones((1,3)),
           'stress':np.zeros((1,3,3,3)),'active_stress':np.zeros((1,3,3,3)),
           'force_residual':np.zeros((6,2))}
    metadata={'snes_reason':2,'iterations':0,'free_residual_norm':0.,'active_energy':0.}
    report=state_audit(data,state,metadata,configuration())
    assert report['status']=='passed'
    json.dumps(report,allow_nan=False)
    state['F'][0,0,0,0]+=.001
    failed=state_audit(data,state,metadata,configuration())
    assert not failed['checks']['kinematics_reconstruction']
