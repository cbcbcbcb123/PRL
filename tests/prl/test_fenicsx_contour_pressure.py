"""Bounded-scope/protocol regressions, not scientific equilibria."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from prl.runs.fenicsx_contour_pressure import configuration, run_contour_pressure
from prl.verification.fenicsx_contour_pressure import scope_checks, contour_state_audit


def test_exact_contour_scope_and_unchanged_qualified_physics():
    from prl.runs.fenicsx_fine_ring import configuration as previous
    assert all(scope_checks(configuration(),previous()).values())
    from prl.cli import _parser,FEM_RUN_COMMANDS
    for command in ['run','verify']:
        parsed = _parser().parse_args([command,'fem-fenicsx-contour-pressure'])
        assert getattr(parsed,command+'_command') in FEM_RUN_COMMANDS


@pytest.mark.parametrize('key,value',[
    ('objects',['ring','contour']),('active_peak',.1),('passive_loads',[0.,.02,.04]),
    ('maximum_equilibrium_solves',5),('mu',2.),('kappa',2000.),('pressure_space','CG1'),
    ('geometry_kind','ring'),('meshes',[{'name':'M0'}]),('retain_solver_iterates',False),
    ('resources',{'seconds':2400,'threads':1,'gpu':0,'automatic_retries':0})])
def test_scope_drift_refused(key,value):
    from prl.runs.fenicsx_fine_ring import configuration as previous
    config=configuration(); config[key]=value
    assert not all(scope_checks(config,previous()).values())


def test_create_only_rejection_precedes_docker():
    with patch('prl.runs.fenicsx_contour_pressure.result_path',side_effect=FileExistsError), \
         patch('prl.runs.fenicsx_contour_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_contour_pressure(Path(__file__).resolve().parents[2])
        docker.assert_not_called()


@pytest.mark.parametrize('updates,solver,expected',[
    (0,{'status':'not_run',**{k:None for k in ['ksp_reason','pc_failed_reason','mumps_infog_1','mumps_infog_2','mumps_icntl_14']}},True),
    (0,{'status':'passed','ksp_reason':4},False),
    (0,{'status':'not_run'},False),
    (3,{'status':'passed','ksp_reason':4,'pc_failed_reason':0,'mumps_infog_1':0,'mumps_icntl_14':100},True),
    (3,{'status':'not_run','ksp_reason':None},False),
    (3,{'status':'passed','ksp_reason':4,'pc_failed_reason':0,'mumps_infog_1':0,'mumps_icntl_14':20},False),
])
def test_factor_report_fail_closed_and_no_null_comparison(updates,solver,expected):
    # Keep mechanics separate: this explicit protocol fixture tests only metadata gates.
    with patch('prl.verification.fenicsx_contour_pressure.diagnostic_state',return_value={'checks':{'physical':True}}):
        report=contour_state_audit({}, {'load':0. if updates==0 else .02,'stress':np.zeros(3)},
            {'iterations':updates,'linear_solver':deepcopy(solver)},configuration())
    assert (report['status']=='passed') == expected


def test_existing_physical_failure_is_not_hidden_by_good_factor():
    solver={'status':'passed','ksp_reason':4,'pc_failed_reason':0,'mumps_infog_1':0,'mumps_icntl_14':100}
    with patch('prl.verification.fenicsx_contour_pressure.diagnostic_state',return_value={'checks':{'local_volume':False}}):
        report=contour_state_audit({}, {'load':.02}, {'iterations':3,'linear_solver':solver},configuration())
    assert report['status']=='failed' and not report['checks']['local_volume']
