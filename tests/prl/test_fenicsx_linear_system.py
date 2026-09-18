from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy import sparse

from prl.verification.fenicsx_linear_system import sparse_metrics,classify


def fixture():
    # Two displacement dofs, two independent two-dof pressure cells.
    matrix=sparse.csr_matrix(np.array([
        [2.,0.,1.,0.,1.,0.], [0.,3.,0.,1.,0.,1.],
        [1.,0.,-1e-3,0.,0.,0.], [0.,1.,0.,-2e-3,0.,0.],
        [1.,0.,0.,0.,-3e-3,0.], [0.,1.,0.,0.,0.,-4e-3]]))
    return matrix,np.ones(6),np.array([0,1]),np.array([2,3,4,5]),np.array([[0,1],[0,1]]),np.array([[2,3],[4,5]]),np.array([0])


def test_sparse_metrics_resolve_blocks_and_pressure_regularization():
    report=sparse_metrics(*fixture())
    assert report['shape']==[6,6] and report['structural_rank']==6
    assert report['zero_rows']==report['zero_columns']==0
    assert report['relative_symmetry_error']==0
    assert report['pressure_block']['off_cell_nonzeros']==0
    assert report['pressure_block']['all_cells_full_rank']
    assert report['pressure_displacement_local_rank_histogram']=={'2':2}


def test_classification_separates_backend_failure_from_exact_singularity():
    report=sparse_metrics(*fixture())
    actual=classify(report,{'converged_reason':-11,'relative_residual':1.},
                    {'status':'passed','relative_residual':1e-14})
    assert actual=='mumps_backend_failure_with_superlu_small_residual'
    broken={**report,'zero_rows':1}
    assert classify(broken,{},{} )=='structurally_singular_assembled_system'


def test_diagnostic_configuration_and_create_only_preflight():
    from prl.runs.fenicsx_linear_system import configuration,run_diagnosis
    cfg=configuration()
    assert cfg['pressure_space']=='DG2' and cfg['loads']==[.02]
    assert cfg['nonlinear_equilibrium_solves']==0
    assert cfg['matrix_assemblies']==1 and cfg['mumps_factorizations']==1
    assert cfg['superlu_factorizations']==1 and cfg['automatic_retries']==0
    with patch('prl.runs.fenicsx_linear_system.result_path',side_effect=FileExistsError),patch('prl.runs.fenicsx_linear_system.read_docker') as docker:
        try:
            run_diagnosis(Path(__file__).resolve().parents[2])
        except FileExistsError:
            pass
        else:
            raise AssertionError('create-only diagnostic must refuse an existing path')
        docker.assert_not_called()


def test_cli_exposes_bounded_linear_diagnosis():
    from prl.cli import _parser
    parsed=_parser().parse_args(['diagnose','fem-fenicsx-linear'])
    assert parsed.command=='diagnose'
    assert parsed.diagnose_command=='fem-fenicsx-linear'
    replay=_parser().parse_args(['diagnose','fem-fenicsx-linear','--report-replay'])
    assert replay.report_replay


def test_nonfinite_solver_diagnostics_are_serializable():
    from prl.verification.fenicsx_linear_system import finite_json
    import json
    report=finite_json({'mumps':{'converged_reason':-11,'solution_norm':np.inf,
                               'relative_residual':np.nan,'rinfog':[0.,-np.inf]},'ok':1.})
    assert report=={'mumps':{'converged_reason':-11,'solution_norm':'positive_infinity',
                             'relative_residual':'nan','rinfog':[0.,'negative_infinity']},'ok':1.}
    assert json.loads(json.dumps(report,allow_nan=False))==report


def test_replay_is_create_only_before_docker():
    from prl.runs.fenicsx_linear_system import run_diagnosis,REPLAY_RESULT
    import pytest
    with patch('prl.runs.fenicsx_linear_system.result_path',side_effect=FileExistsError) as paths, patch('prl.runs.fenicsx_linear_system.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_diagnosis(Path(__file__).resolve().parents[2],replay=True)
        assert paths.call_args.args[1]==REPLAY_RESULT
        docker.assert_not_called()


def test_workspace_exhaustion_is_not_misreported_as_singularity():
    from prl.verification.fenicsx_linear_system_result import mumps_failure_cause
    def report(code):
        return {'mumps':{'infog':{'1':code}}}
    assert mumps_failure_cause(report(-9))=='mumps_internal_real_workspace_too_small'
    assert mumps_failure_cause(report(-10))=='mumps_numerical_singularity_or_zero_pivot'
    assert mumps_failure_cause(report(-13))=='mumps_memory_allocation_failure'
    assert mumps_failure_cause({})=='unknown_mumps_failure'
