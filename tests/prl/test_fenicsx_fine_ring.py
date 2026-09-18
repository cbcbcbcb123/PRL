"""Explicit controller/protocol fixtures; native integration is separate evidence."""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import ast
import time
import numpy as np

import pytest
from prl.runs.fenicsx_fine_ring import configuration,run_fine_ring


def test_fine_scope_preserves_physics_and_reuses_all_coarse_states():
    from prl.runs.fenicsx_pressure import configuration as previous
    actual=configuration(); parent=previous(complete_passive_ring=True)
    for key in ['mu','kappa','meshes','radii','quadrature_degree','solver','passive_loads','resources','pressure_space']:
        assert actual[key]==parent[key]
    assert actual['execution_plan']=={'M0':[],'M1':[0,1,2,3,4]}
    assert actual['maximum_equilibrium_solves']==5 and actual['active_peak']==0
    from prl.cli import _parser,FEM_RUN_COMMANDS
    assert 'fem-fenicsx-fine-ring' in FEM_RUN_COMMANDS
    assert _parser().parse_args(['run','fem-fenicsx-fine-ring','--phase','diagnose']).phase=='diagnose'


def test_diagnostic_create_only_before_runtime():
    with patch('prl.runs.fenicsx_fine_ring.result_path',side_effect=FileExistsError),patch('prl.runs.fenicsx_fine_ring.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_fine_ring(Path(__file__).resolve().parents[2],'diagnose')
        docker.assert_not_called()


def test_completed_science_cannot_be_retried():
    with patch('prl.runs.fenicsx_fine_ring.result_path',return_value=Path('explicit_fixture')),\
         patch.object(Path,'exists',return_value=True),patch('prl.runs.fenicsx_fine_ring.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_fine_ring(Path(__file__).resolve().parents[2],'complete')
        docker.assert_not_called()


def production_adapter():
    source=Path(__file__).resolve().parents[2]/'src/prl/fem/fenicsx_ring.py'
    tree=ast.parse(source.read_text())
    ring=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Ring')
    methods=[node for node in ring.body if isinstance(node,ast.FunctionDef) and node.name in {'solve','linear_solver_report','trace'}]
    captured=[]
    namespace={'np':np,'time':time,'json':__import__('json'),
               'write_json':lambda path,data:captured.append((str(path),data)),
               'fem':SimpleNamespace(assemble_scalar=lambda form:1.)}
    module=ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='Adapter',bases=[],keywords=[],body=methods,decorator_list=[])],type_ignores=[]))
    exec(compile(module,str(source),'exec'),namespace)
    return namespace['Adapter'],captured


@pytest.mark.parametrize('prior_factor_exists',[False,True])
def test_production_solve_zero_updates_saves_state_without_touching_factor(prior_factor_exists):
    adapter,captured=production_adapter(); owner=adapter()
    calls=[]
    def unsafe_factor():
        calls.append('factor')
        raise RuntimeError('Native hazard or stale factor: must not be queried')
    factor_pc=SimpleNamespace(getFailedReason=lambda:0,getFactorMatrix=unsafe_factor)
    ksp=SimpleNamespace(getPC=lambda:factor_pc,getConvergedReason=lambda:4 if prior_factor_exists else 0)
    solver=SimpleNamespace(getKSP=lambda:ksp,getConvergedReason=lambda:2,getIterationNumber=lambda:0)
    owner.config={'retain_solver_iterates':True}; owner.factor_options={}; owner.root=Path('explicit_memory_only_fixture')
    owner.name='M1'; owner.history=[]; owner.w=SimpleNamespace(x=SimpleNamespace(array=np.zeros(6),scatter_forward=lambda:None))
    owner.load=SimpleNamespace(value=0.); owner.activation=SimpleNamespace(value=0.)
    owner.vmap=np.arange(4); owner.pmap=np.arange(4,6); owner.free_mixed=np.ones(6,dtype=bool)
    owner.vector=lambda form:np.zeros(6); owner.residual_form=None; owner.area_form=None; owner.active_energy_form=None
    owner.expressions={'J':SimpleNamespace(eval=lambda *args:np.ones((1,1)))}; owner.domain=None; owner.cell_ids=np.array([0])
    owner.problem=SimpleNamespace(solver=solver,solve=lambda:None)
    with patch.object(Path,'mkdir'),patch('numpy.savez_compressed') as saved:
        result=owner.solve('passive_0',0.,0.,np.zeros(6))
    assert calls==[]
    report=captured[-1][1]['linear_solver']
    assert report['status']=='not_run' and all(report[key] is None for key in ['ksp_reason','pc_failed_reason','mumps_infog_1','mumps_infog_2','mumps_icntl_14'])
    assert np.array_equal(result,np.zeros(6)) and saved.call_count==2


@pytest.mark.parametrize('ksp_reason,pc_reason,expected',[(4,0,'passed'),(-11,3,'failed'),(0,0,'failed')])
def test_real_updates_require_successful_ksp_before_statistics(ksp_reason,pc_reason,expected):
    adapter,_=production_adapter(); owner=adapter(); calls=[]
    factor=SimpleNamespace(getMumpsInfog=lambda index:0,getMumpsIcntl=lambda index:100)
    def get_factor():
        calls.append('factor'); return factor
    pc=SimpleNamespace(getFailedReason=lambda:pc_reason,getFactorMatrix=get_factor)
    ksp=SimpleNamespace(getConvergedReason=lambda:ksp_reason,getPC=lambda:pc)
    owner.problem=SimpleNamespace(solver=SimpleNamespace(getKSP=lambda:ksp))
    report=owner.linear_solver_report(1)
    assert report['status']==expected
    assert len(calls)==int(expected=='passed')
