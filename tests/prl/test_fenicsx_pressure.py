"""Pressure-space tests use explicit polynomial fixtures, not science solves."""
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from prl.verification.fenicsx_ring import fields,pressure_basis,shape
from prl.verification.fenicsx_pressure import volume_projection,same_displacement_mesh
from prl.runs.fenicsx_pressure import configuration,run_pressure


def fixture():
    nodes=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,.5],[0.,.5],[.5,0.]])+[2.,0.]
    return {'coordinates':nodes,'cells':np.arange(6)[None],
            'pressure_coordinates':nodes.copy(),'pressure_cells':np.arange(6)[None],
            'pressure_space':np.array('DG2'),'layers':np.array([1]),
            'qpoints':np.array([[.05,.12],[.43,.2],[.22,.57],[.11,.3],[.7,.1],[.25,.25]]),
            'qweights':np.ones(6)/12}


def test_dg2_recovers_quadratic_volume_constraint():
    mesh=fixture(); x,y=mesh['coordinates'].T
    displacement=np.column_stack((.03*x*x,.04*y*y))
    determinant=(1+.06*x)*(1+.08*y)
    state={'u':displacement,'pressure':1000*(determinant-1),'activation':0.}
    actual=fields(mesh,state)
    basis=pressure_basis(mesh)
    pressure=basis@state['pressure']
    assert np.max(np.abs(actual['J'][0]-1-pressure/1000))<1e-14
    assert np.linalg.norm(actual['pressure_residual'])<1e-14
    assert volume_projection(mesh,state)['pointwise_constraint_max']<1e-14


def test_cg1_cannot_exactly_represent_same_quadratic_constraint():
    mesh=fixture(); x,y=mesh['coordinates'].T
    mesh.update(pressure_space=np.array('CG1'),pressure_cells=np.arange(3)[None],
                pressure_coordinates=mesh['coordinates'][:3])
    state={'u':np.column_stack((.03*x*x,.04*y*y)),
           'pressure':1000*((1+.06*x[:3])*(1+.08*y[:3])-1),'activation':0.}
    assert volume_projection(mesh,state)['pointwise_constraint_max']>1e-4


def test_dg2_rejects_scrambled_pressure_coordinates():
    mesh=fixture(); mesh['pressure_coordinates'][[0,1]]=mesh['pressure_coordinates'][[1,0]]
    with pytest.raises(ValueError,match='ordering'):
        pressure_basis(mesh)


def test_dg2_rejects_shared_dofs_and_implicit_basis_guess():
    mesh=fixture(); mesh['pressure_cells']=np.vstack((mesh['pressure_cells'],mesh['pressure_cells']))
    with pytest.raises(ValueError,match='cell-local'):
        pressure_basis(mesh)
    mesh=fixture(); mesh.pop('pressure_space')
    with pytest.raises(ValueError,match='basis'):
        pressure_basis(mesh)


def test_same_constant_pressure_stress_under_both_bases():
    mesh=fixture()
    state={'u':np.zeros((6,2)),'pressure':np.full(6,2.),'activation':0.}
    dg=fields(mesh,state)
    mesh.update(pressure_space=np.array('CG1'),pressure_cells=np.arange(3)[None],
                pressure_coordinates=mesh['coordinates'][:3])
    cg=fields(mesh,{**state,'pressure':np.full(3,2.)})
    for key in ['F','J','stress','force']:
        assert np.allclose(dg[key],cg[key],atol=1e-14)


def test_frozen_execution_scope():
    cfg=configuration()
    assert cfg['pressure_space']=='DG2' and cfg['mu']==1 and cfg['kappa']==1000
    assert cfg['passive_loads']==[0.,.02] and cfg['active_peak']==0
    assert cfg['maximum_equilibrium_solves']==4
    assert cfg['resources']=={'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0}
    from prl.cli import _parser,FEM_RUN_COMMANDS
    assert _parser().parse_args(['run','fem-fenicsx-pressure']).run_command in FEM_RUN_COMMANDS
    assert _parser().parse_args(['verify','fem-fenicsx-pressure']).verify_command=='fem-fenicsx-pressure'


def test_create_only_refusal_precedes_docker():
    with patch('prl.runs.fenicsx_pressure.result_path',side_effect=FileExistsError),patch('prl.runs.fenicsx_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_pressure(Path(__file__).resolve().parents[2])
        docker.assert_not_called()


def test_same_geometry_accepts_renumbering_but_not_moved_nodes():
    mesh=fixture(); mesh['fixed']=np.zeros((6,2),dtype=bool); mesh['fixed'][0]=True
    mesh['inner_edges']=np.array([[0,5,1]])
    permutation=np.array([3,0,5,1,4,2]); inverse=np.argsort(permutation)
    changed={**mesh,'coordinates':mesh['coordinates'][permutation],
             'fixed':mesh['fixed'][permutation],'cells':inverse[mesh['cells']],
             'inner_edges':inverse[mesh['inner_edges']]}
    assert same_displacement_mesh(changed,mesh)
    changed['coordinates']=changed['coordinates'].copy(); changed['coordinates'][0,0]+=.001
    assert not same_displacement_mesh(changed,mesh)
