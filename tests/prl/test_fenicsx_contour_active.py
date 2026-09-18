"""Protocol/explicit synthetic fixtures; these tests are not FEM equilibria."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from prl.runs.fenicsx_contour_pressure import configuration,active_configuration,run_contour_active
from prl.verification.fenicsx_contour_active import active_scope_checks,state_path
from prl.fem.fenicsx_contour_pressure import advance_active_mesh
from prl.verification.fenicsx_pressure import saved_iterates_audit


def test_exact_eight_and_mutually_exclusive_cli():
    assert all(active_scope_checks(active_configuration(),configuration()).values())
    from prl.cli import _parser
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-fenicsx-contour-pressure','--active-at-qualified-pressure']).active_at_qualified_pressure
        with pytest.raises(SystemExit):
            _parser().parse_args([command,'fem-fenicsx-contour-pressure','--active-at-qualified-pressure','--complete-passive'])


@pytest.mark.parametrize('key,value',[
    ('active_levels',[0.,.1]),('fixed_pressure',.04),('maximum_equilibrium_solves',9),
    ('mu',2.),('kappa',2000.),('active_peak',.2),('pressure_space','CG1'),
    ('quadrature_degree',8),('meshes',[{'name':'M0'}]),('retain_solver_iterates',False),
    ('passive_loads',[0.,.02,.04])])
def test_scope_rejects_drift(key,value):
    config=active_configuration(); config[key]=value
    assert not all(active_scope_checks(config,configuration()).values())


def test_create_only_precedes_docker():
    with patch('prl.runs.fenicsx_contour_pressure.result_path',side_effect=FileExistsError), \
         patch('prl.runs.fenicsx_contour_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_contour_active(Path(__file__).resolve().parents[2])
        docker.assert_not_called()


@pytest.mark.parametrize('failure_at',['solve','validate'])
def test_first_failure_stops_active_ladder(failure_at):
    calls=[]
    def solve(label,pressure,activation,initial):
        calls.append((label,pressure,activation))
        if failure_at=='solve':
            raise ValueError('synthetic solve failure')
        return initial
    def validate(label):
        raise ValueError('synthetic gate failure')
    with pytest.raises(ValueError):
        advance_active_mesh(SimpleNamespace(solve=solve),np.array([7.]),lambda label:None,validate)
    assert calls==[('active_1',.02,.025)]


def test_active_initials_are_chained_and_baseline_not_resolved():
    calls=[]
    def solve(label,pressure,activation,initial):
        calls.append((pressure,activation,float(initial[0]))); return initial+1
    advance_active_mesh(SimpleNamespace(solve=solve),np.array([7.]),lambda label:None,lambda label:None)
    assert calls==[(.02,.025,7.),(.02,.05,8.),(.02,.075,9.),(.02,.1,10.)]
    assert state_path('fixture','M0',0)==Path('fixture/retained/M0_state_passive_1.npz')
    assert state_path('fixture','M0',4)==Path('fixture/raw/M0_state_active_4.npz')


@pytest.mark.parametrize('expected,actual,passed',[(0.,.1,False),(.1,.1,True),(.1,.05,False)])
def test_iterate_audit_requires_explicit_frozen_activation(expected,actual,passed):
    vector=np.zeros(3); mesh={'mixed_u_map':np.array([0,1]),'mixed_p_map':np.array([2]),'fixed':np.array([False,False])}
    state={'activation':np.array(actual),'load':np.array(.02),'initial_mixed':vector,'mixed_state':vector}
    iterate={**state,'iteration':0,'residual':0.,'u':np.zeros(2),'pressure':np.zeros(1)}
    with patch.object(Path,'glob',return_value=iter([Path('synthetic_iterate.npz')])), \
         patch('prl.verification.fenicsx_pressure.load_arrays',return_value=iterate), \
         patch('prl.verification.fenicsx_pressure.fields',return_value={'J':np.ones(1),'force':np.zeros(2)}), \
         patch('prl.verification.fenicsx_pressure.cavity',return_value=(1.,np.zeros(2),None)):
        report=saved_iterates_audit('synthetic',mesh,state,{'iterations':0,'history':[{'residual':0.}]},
            {'mu':1.,'kappa':1000.},expected_activation=expected)
    assert (report['status']=='passed') is passed
