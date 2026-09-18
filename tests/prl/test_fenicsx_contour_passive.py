"""Bounded continuation protocol tests, not scientific equilibrium data."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from prl.runs.fenicsx_contour_pressure import configuration,completion_configuration,run_contour_passive
from prl.verification.fenicsx_contour_pressure import completion_scope_checks,same_mixed_mesh,response_comparison
from prl.fem.fenicsx_contour_pressure import advance_passive_mesh


def test_exact_six_remaining_and_public_flag():
    assert all(completion_scope_checks(completion_configuration(),configuration()).values())
    from prl.cli import _parser
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-fenicsx-contour-pressure','--complete-passive']).complete_passive


@pytest.mark.parametrize('key,value',[
    ('new_loads',[.02,.04,.06,.08]),('reused_loads',[0.]),('maximum_equilibrium_solves',7),
    ('mu',2.),('kappa',2000.),('active_peak',.1),('pressure_space','CG1'),
    ('quadrature_degree',8),('meshes',[{'name':'M0'}]),('retain_solver_iterates',False)])
def test_completion_scope_cannot_expand_or_change_physics(key,value):
    config=completion_configuration(); config[key]=value
    assert not all(completion_scope_checks(config,configuration()).values())


def test_create_only_before_docker():
    with patch('prl.runs.fenicsx_contour_pressure.result_path',side_effect=FileExistsError), \
         patch('prl.runs.fenicsx_contour_pressure.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run_contour_passive(Path(__file__).resolve().parents[2])
        docker.assert_not_called()


def test_restart_requires_mixed_numbering_not_just_coordinates():
    keys=['coordinates','cells','layers','pressure_coordinates','pressure_cells','inner_edges',
        'fixed','qpoints','qweights','mixed_u_map','mixed_p_map','pressure_space']
    retained={key:np.array([0,1]) for key in keys}; actual=deepcopy(retained)
    assert same_mixed_mesh(actual,retained)
    actual['mixed_p_map']=np.array([1,0])
    assert not same_mixed_mesh(actual,retained)
    assert not same_mixed_mesh({}, {})


@pytest.mark.parametrize('failure_at',['solve','validate'])
def test_first_failure_prevents_next_load(failure_at):
    calls=[]
    def solve(label,pressure,activation,initial):
        calls.append((label,pressure,activation))
        assert np.array_equal(initial,[7.])
        if failure_at=='solve':
            raise ValueError('explicit fixture failure')
        return initial
    def validate(label):
        raise ValueError('explicit fixture gate failure')
    with pytest.raises(ValueError):
        advance_passive_mesh(SimpleNamespace(solve=solve),np.array([7.]),lambda label:None,validate)
    assert calls==[('passive_2',.04,0.)]


def test_three_exact_loads_and_chained_initials():
    calls=[]
    def solve(label,pressure,activation,initial):
        calls.append((pressure,float(initial[0]))); return initial+1
    advance_passive_mesh(SimpleNamespace(solve=solve),np.array([7.]),lambda label:None,lambda label:None)
    assert calls==[(.04,7.),(.06,8.),(.08,9.)]


def test_both_original_mesh_response_gates_apply():
    assert response_comparison(0.,0.)['status']=='passed'
    assert response_comparison(.2,.2005)['status']=='passed'
    assert response_comparison(.2,.203)['status']=='failed'
    assert response_comparison(.001,.0012)['status']=='failed'
