"""Prospective gate tests with fabricated errors, not scientific validation."""
import copy
import math

import pytest

from prl.fem.mixed_cube_refinement_spec import configuration
from prl.fem.mixed_cube_representation_spec import configuration as representation_configuration
from prl.verification.mixed_cube_refinement import convergence, observed_order


def audit(n):
    return {'status': 'passed', 'metrics': {'relative_u_L2': 2/n**4,
        'relative_u_H1': 3/n**3, 'relative_pressure_L2': 1/n**3, 'J_error_RMS': .01/n**2}}


def completed():
    return {'mms_p3p2_n12': audit(12)}


def references():
    return {f'mms_p3p2_n{n}': audit(n) for n in (4, 8)}


def test_new_spec_preserves_original_scientific_settings_and_original_object():
    original = copy.deepcopy(representation_configuration())
    result = configuration()
    assert [case['n'] for case in result['cases']] == [12]
    assert result['maximum_equilibrium_solves'] == 1
    assert all(case['kind'] == 'mms' and case['kappa'] == 100 and
               (case['u_degree'], case['p_degree']) == (3, 2) for case in result['cases'])
    for key in ('mu', 'quadrature_degree', 'solver', 'trial_guard', 'resources',
                'patch_gates', 'mms_gates', 'candidate_orders', 'independent_quadrature'):
        assert result[key] == original[key]
    assert result['refinement']['primary_pair'] == [8, 12]
    result['solver']['snes_max_it'] = 999
    assert representation_configuration() == original
    assert configuration()['solver']['snes_max_it'] == 30


def test_nonuniform_mesh_ratio_not_log2_or_dof_ratio():
    actual = observed_order(2/8**4, 2/12**4, 8, 12)
    assert actual == pytest.approx(4.)
    assert math.log((12/8)**4, 2) < 3.5
    report = convergence(completed(), configuration(), references())
    assert report['status'] == 'passed'
    assert report['primary_EOC']['u_L2'] == pytest.approx(4.)
    assert report['primary_mesh_ratio'] == 12/8
    assert report['original_n2_n4_n8_qualification'] == 'failed_unchanged'


@pytest.mark.parametrize('missing', [4, 8, 12])
def test_missing_grid_cannot_select_an_alternate_interval(missing):
    cases, saved = completed(), references()
    if missing in (4, 8):
        saved.pop(f'mms_p3p2_n{missing}')
    else:
        cases.pop(f'mms_p3p2_n{missing}')
    report = convergence(cases, configuration(), saved)
    assert report['status'] == 'blocked'
    assert report['missing_cases'] == [f'mms_p3p2_n{missing}']
    assert not report['primary_EOC']


def test_safety_failure_and_missing_case_are_not_passed_or_hidden():
    cases = completed()
    cases['mms_p3p2_n12']['safety_status'] = 'failed'
    saved = references()
    saved.pop('mms_p3p2_n8')
    report = convergence(cases, configuration(), saved)
    assert report['status'] == 'failed'
    assert report['nonqualified_cases'] == ['mms_p3p2_n12']


def test_primary_pair_failure_cannot_be_rescued_by_passing_longer_pair():
    cases = completed()
    saved = references()
    saved['mms_p3p2_n4']['metrics']['relative_u_L2'] = .02
    saved['mms_p3p2_n8']['metrics']['relative_u_L2'] = .001
    cases['mms_p3p2_n12']['metrics']['relative_u_L2'] = .001*(8/12)**3.4
    report = convergence(cases, configuration(), saved)
    assert report['secondary_EOC']['4_to_12']['u_L2'] > 3.5
    assert report['primary_EOC']['u_L2'] == pytest.approx(3.4)
    assert report['status'] == 'failed'
    assert report['checks']['u_L2_order'] is False


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), -.1, 0., True, '0.001'])
def test_invalid_errors_are_failed_without_inventing_orders(value):
    cases = completed()
    cases['mms_p3p2_n12']['metrics']['relative_u_L2'] = value
    report = convergence(cases, configuration(), references())
    assert report['status'] == 'failed'
    assert report['invalid_metrics']['mms_p3p2_n12'] == ['relative_u_L2']
    assert report['primary_EOC'] == {}


def test_monotonicity_and_finest_absolute_gates_remain_mandatory():
    cases = completed()
    cases['mms_p3p2_n12']['metrics']['J_error_RMS'] = .00101
    report = convergence(cases, configuration(), references())
    assert report['status'] == 'failed' and not report['checks']['fine_J_error']
    cases = completed()
    saved = references()
    saved['mms_p3p2_n4']['metrics']['relative_u_L2'] = saved['mms_p3p2_n8']['metrics']['relative_u_L2']/2
    report = convergence(cases, configuration(), saved)
    assert report['primary_EOC']['u_L2'] > 3.5
    assert report['status'] == 'failed' and not report['checks']['u_L2_decreases']


def test_changed_pair_or_embedded_reference_is_rejected():
    changed = configuration()
    changed['refinement']['primary_pair'] = [4, 12]
    with pytest.raises(ValueError, match='frozen design'):
        convergence(completed(), changed, references())
    with pytest.raises(ValueError, match='separately'):
        convergence({**completed(), 'mms_p3p2_n8': audit(8)}, configuration(), references())
