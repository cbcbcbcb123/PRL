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


def test_resume_is_one_original_pressure_with_only_workspace_change():
    cfg=configuration(resume_first_ring=True)
    old=configuration()
    assert cfg['objects']==['ring'] and cfg['passive_loads']==[.02]
    assert cfg['maximum_equilibrium_solves']==1 and cfg['retain_solver_iterates']
    assert cfg['solver']=={**old['solver'],'mat_mumps_icntl_14':100}
    for key in ['mu','kappa','meshes','radii','quadrature_degree','resources']:
        assert cfg[key]==old[key]
    assert 'mat_mumps_icntl_14' not in old['solver']
    from prl.cli import _parser
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-fenicsx-pressure','--resume-first-ring']).resume_first_ring


def test_resume_create_only_refusal_precedes_docker():
    from prl.runs.fenicsx_pressure import RESUME_RESULT
    with patch('prl.runs.fenicsx_pressure.result_path',side_effect=FileExistsError) as target,patch('prl.runs.fenicsx_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_pressure(Path(__file__).resolve().parents[2],resume_first_ring=True)
        assert target.call_args.args[1]==RESUME_RESULT
        docker.assert_not_called()


def test_resume_v2_requires_interface_gate_without_changing_physics():
    cfg=configuration(resume_first_ring=True,resume_revision=2)
    original=configuration(resume_first_ring=True)
    for key in original:
        assert cfg[key]==original[key]
    assert cfg['runtime_interface_gate'] and cfg['resume_revision']==2
    from prl.cli import _parser
    assert _parser().parse_args(['run','fem-fenicsx-pressure','--resume-first-ring','--resume-revision','2']).resume_revision==2
    with pytest.raises(ValueError):
        configuration(resume_revision=2)


def test_resume_v2_create_only_before_runtime():
    from prl.runs.fenicsx_pressure import RESUME_V2_RESULT
    with patch('prl.runs.fenicsx_pressure.result_path',side_effect=FileExistsError) as target,patch('prl.runs.fenicsx_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_pressure(Path(__file__).resolve().parents[2],resume_first_ring=True,resume_revision=2)
        assert target.call_args.args[1]==RESUME_V2_RESULT
        docker.assert_not_called()


def test_observer_uses_read_only_vector_access():
    # Execute the real small method without importing unavailable host DOLFINx.
    # This protocol regression is not a PETSc integration test or scientific solve.
    import ast
    from types import SimpleNamespace
    source=Path(__file__).resolve().parents[2]/'src/prl/fem/fenicsx_ring.py'
    tree=ast.parse(source.read_text())
    ring=next(item for item in tree.body if isinstance(item,ast.ClassDef) and item.name=='Ring')
    method=next(item for item in ring.body if isinstance(item,ast.FunctionDef) and item.name=='monitor')
    namespace={'np':np,'write_json':lambda *args:None}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
    vector=np.arange(8,dtype=float); before=vector.copy()
    class LockedVector:
        @property
        def array(self):
            raise RuntimeError('VecGetArray cannot write a read-locked SNES monitor vector')
        def getArray(self,readonly=False):
            assert readonly is True
            return vector
    solver=SimpleNamespace(getSolution=lambda:LockedVector())
    observer=SimpleNamespace(history=[],config={'retain_solver_iterates':True},
        iterate_root=Path('nonexistent_test_observer'),vmap=np.arange(4),pmap=np.arange(4,8),
        load=SimpleNamespace(value=.02),activation=SimpleNamespace(value=0.))
    with patch('numpy.savez_compressed') as writer:
        namespace['monitor'](observer,solver,0,.01)
    assert observer.history==[{'iteration':0,'residual':.01}]
    assert np.array_equal(vector,before)
    stored=writer.call_args.kwargs
    assert np.array_equal(stored['mixed_state'],before)
    assert not np.shares_memory(stored['mixed_state'],vector)


def test_factor_option_uses_actual_ksp_prefix_and_outlives_constructor_options():
    import ast
    from types import SimpleNamespace
    source=Path(__file__).resolve().parents[2]/'src/prl/fem/fenicsx_ring.py'
    tree=ast.parse(source.read_text())
    ring=next(item for item in tree.body if isinstance(item,ast.ClassDef) and item.name=='Ring')
    method=next(item for item in ring.body if isinstance(item,ast.FunctionDef) and item.name=='bind_factor_options')
    options={}; namespace={'PETSc':SimpleNamespace(Options=lambda:options)}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
    owner=SimpleNamespace(config=configuration(True),problem=SimpleNamespace(
        solver=SimpleNamespace(getKSP=lambda:SimpleNamespace(getOptionsPrefix=lambda:'dynamic_prefix_'))))
    result=namespace['bind_factor_options'](owner)
    assert options=={'dynamic_prefix_mat_mumps_icntl_14':100}
    assert result['actual_readback_required'] is True
    owner.config=configuration()
    assert namespace['bind_factor_options'](owner) is None


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


def test_plot_recomputes_raw_vectors_and_retains_quadrature_maximum():
    from types import SimpleNamespace
    from prl.rendering.fenicsx_pressure import resumed_plot_data
    mesh=fixture()
    data={f'mesh_{key}':value for key,value in mesh.items()}
    data.update(mu=np.array(1.),kappa=np.array(1000.),iterations=np.array([0,1]),residuals=np.array([1.,1e-12]))
    for index in range(2):
        data.update({f'state_{index}_u':np.full((6,2),index*.01),
                     f'state_{index}_pressure':np.full(6,index*.2),
                     f'state_{index}_activation':np.array(0.),f'state_{index}_load':np.array(.02)})
    calls=[]
    def independent_fields(mesh,state,mu,kappa):
        calls.append(state['u'].copy())
        stress=np.zeros((1,2,3,3)); stress[0,:,0,0]=[2.,4.]
        return {'stress':stress,'J':np.array([[1.001,.99]])}
    mechanics=SimpleNamespace(load_arrays=lambda path:data,fields=independent_fields,
                              cavity=lambda mesh,u,p:(2.+float(u.sum()),None,None))
    _,frames=resumed_plot_data('explicit_in_memory_fixture',mechanics)
    assert len(calls)==len(frames)==2 and [item['iteration'] for item in frames]==[0,1]
    np.testing.assert_allclose(frames[1]['volume_percent'],[1.],atol=1e-12)
    np.testing.assert_allclose(frames[1]['equivalent'],[3.],atol=1e-12)
    np.testing.assert_allclose(frames[1]['displacement'],[np.sqrt(2)*.01])
    assert frames[0]['area_percent']==0. and frames[1]['area_percent']==pytest.approx(6.)
    data['iterations']=np.array([0,2])
    with pytest.raises(ValueError,match='All actual Newton'):
        resumed_plot_data('gapped_fixture',mechanics)
