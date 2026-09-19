"""Host-only evidence handling tests; no scientific solver or result package."""
import copy
from pathlib import Path

import numpy as np
import pytest

from prl.runs import mixed_cube_representation_delivery as delivery
from prl.fem.mixed_cube_representation_spec import configuration
from prl.verification.mixed_cube import exact_fields
from test_mixed_cube import fixture as quadratic_fixture
from test_mixed_cube_representation import cubic_fixture


def saved(data, kind='cubic_volume'):
    data = copy.deepcopy(data)
    u = exact_fields(data['coordinates'], kind, 1000.)['u']
    pressure = exact_fields(data['pressure_coordinates'], kind, 1000.)['pressure']
    size = u.size+pressure.size
    permutation = np.random.default_rng(4).permutation(size)
    data['mixed_u_map'], data['mixed_p_map'] = permutation[:u.size], permutation[u.size:]
    mixed = np.empty(size)
    mixed[data['mixed_u_map']], mixed[data['mixed_p_map']] = u.ravel(), pressure
    return data, dict(u=u, pressure=pressure, mixed_state=mixed)


def test_cubic_all_state_sampling_and_quadratic_pressure_face_values():
    data, state = saved(cubic_fixture(2))
    report = delivery.describe_iterate(data, state)
    assert report['status'] == 'passed'
    assert report['extra']['minimum_J'] == pytest.approx(1.)
    centroids = data['coordinates'][data['boundary_faces'][:, :3]].mean(axis=1)
    np.testing.assert_allclose(delivery.terminal_pressure_for_faces(data, state),
                               6*centroids[:, 0]**2, atol=1e-12, rtol=0)


def test_nonpositive_accepted_state_is_failed_not_a_valid_equilibrium():
    data, state = saved(cubic_fixture(2))
    state['u'] = -2*data['coordinates']
    state['mixed_state'][data['mixed_u_map']] = state['u'].ravel()
    report = delivery.describe_iterate(data, state)
    assert report['status'] == 'failed'
    assert report['production']['nonpositive_points'] > 0
    assert report['extra']['cells_with_nonpositive_J'] == len(data['cells'])


@pytest.mark.parametrize('defect', ['duplicate_map', 'value_drift', 'nonfinite'])
def test_state_map_corruption_fails_closed(defect):
    data, state = saved(quadratic_fixture(), 'quadratic_volume')
    if defect == 'duplicate_map':
        data['mixed_p_map'][0] = data['mixed_u_map'][0]
    elif defect == 'value_drift':
        state['u'][0, 0] += 1e-4
    else:
        state['pressure'][0] = np.nan
    with pytest.raises(ValueError, match='mixed-state mapping'):
        delivery.check_mixed_mapping(data, state)


def reordered(data, state):
    result = copy.deepcopy(data)
    values = {}
    for key, coordinate, cells in (('u', 'coordinates', 'cells'),
                                     ('pressure', 'pressure_coordinates', 'pressure_cells')):
        permutation = np.random.default_rng(18).permutation(len(data[coordinate]))
        inverse = np.empty_like(permutation)
        inverse[permutation] = np.arange(len(permutation))
        result[coordinate] = data[coordinate][permutation].copy()
        result[cells] = inverse[data[cells][::-1]]
        values[key] = state[key][permutation].copy()
    size = values['u'].size
    result['mixed_u_map'] = np.arange(size)
    result['mixed_p_map'] = np.arange(size, size+values['pressure'].size)
    values['mixed_state'] = np.concatenate((values['u'].ravel(), values['pressure']))
    return result, values


def test_quadrature_comparison_aligns_nodes_cells_and_mixed_maps():
    data, state = saved(quadratic_fixture(), 'quadratic_volume')
    other, values = reordered(data, state)
    other['coordinates'] += 2e-16
    report = delivery.compare_aligned_states(data, state, other, values)
    assert report['status'] == 'passed'
    assert report['u']['relative_nodal_l2'] == 0
    assert report['pressure']['maximum_absolute_component'] == 0
    values['u'] *= 1.001
    values['mixed_state'][other['mixed_u_map']] = values['u'].ravel()
    assert delivery.compare_aligned_states(data, state, other, values)['u']['relative_nodal_l2'] == pytest.approx(.001)
    other['cells'][0, 0] = other['cells'][0, 1]
    with pytest.raises(ValueError, match='connectivity'):
        delivery.compare_aligned_states(data, state, other, values)


@pytest.mark.parametrize('defect', ['duplicate', 'offset', 'nan'])
def test_coordinate_alignment_rejects_nonbijective_correspondence(defect):
    coordinates = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    current = coordinates.copy()
    if defect == 'duplicate':
        current[1] = current[0]
    elif defect == 'offset':
        current[0, 0] = 1e-5
    else:
        current[0, 0] = np.nan
    with pytest.raises(ValueError):
        delivery.coordinate_alignment(coordinates, current)


def test_order8_failure_preserves_order6_and_explicit_safety_failure(monkeypatch):
    def metrics(data, state, case, order):
        if order == 8:
            raise ValueError('Nonpositive independently sampled J')
        return {'relative_u_H1': .1, 'minimum_sampled_J': .01}, {}
    monkeypatch.setattr(delivery, 'error_metrics', metrics)
    monkeypatch.setattr(delivery, 'describe_iterate', lambda *args: {
        'status': 'failed', 'production': {'minimum_J': -.01, 'nonpositive_points': 2}})
    report = delivery.integration_diagnostics({}, {}, {})
    assert report['status'] == 'failed'
    assert report['order6']['minimum_sampled_J'] == .01
    assert report['order8'] is None
    assert report['order8_J_safety']['production']['minimum_J'] < 0
    assert report['threshold_changes'] == 0


def test_real_cubic_fixture_integrates_both_orders_without_scientific_claim():
    data, state = saved(cubic_fixture(2))
    report = delivery.integration_diagnostics(data, state, {'kind': 'cubic_volume', 'kappa': 1000.})
    assert report['status'] == 'passed'
    assert report['order6']['relative_u_H1'] < 1e-10
    assert report['order8']['relative_pressure_L2'] < 1e-10
    assert report['absolute_differences']['relative_u_H1'] < 1e-10


def test_empty_failed_package_does_not_pass_readback_or_qualification(monkeypatch):
    config = configuration()
    from prl.verification.mixed_cube_representation import convergence
    outcome = convergence({}, config)
    summary = {'status': 'failed', 'cases': {}, 'attempted_solves': 0, 'automatic_retries': 0,
               'convergence': outcome}
    monkeypatch.setattr(delivery, '_read', lambda path: config if Path(path).name == 'configuration.json' else summary)
    monkeypatch.setattr(Path, 'exists', lambda path: False)
    monkeypatch.setattr(delivery, 'verify', lambda root: {'status': 'not_run', 'cases': {}, 'convergence': outcome})
    monkeypatch.setattr(delivery, 'audit_paths', lambda root: {'status': 'not_run', 'checks': {},
        'candidates': [], 'accepted_steps_checked': 0})
    report, arrays, documents = delivery.analyze(Path('unused-fixture'))
    assert report['status'] == 'failed'
    assert report['delivery_integrity'] == 'not_run'
    assert report['candidate_k100_qualification']['status'] == 'not_run'
    assert report['completed_equilibria'] == report['accepted_states_checked'] == 0
    assert all(row['equilibrium'] == 'not_run' and row['metrics'] is None for row in report['cases'])
    assert not arrays
    assert documents['path_endpoint_certificate.json']['status'] == 'not_run'


def test_missing_terminal_retains_real_failed_accepted_state(monkeypatch):
    data, state = saved(cubic_fixture(2))
    state['u'] = -2*data['coordinates']
    state['mixed_state'][data['mixed_u_map']] = state['u'].ravel()
    config = configuration()
    case = config['cases'][0]
    config['cases'] = [case]
    name = case['name']
    from prl.verification.mixed_cube_representation import convergence
    outcome = convergence({}, config)
    documents = {'configuration.json': config, 'summary.json': {'status': 'failed', 'cases': {},
        'attempted_solves': 1, 'convergence': outcome}, 'failure.json': {'case': name},
        'history.json': [{'iteration': 0, 'minimum_sampled_J': -1., 'residual': 1.}]}
    monkeypatch.setattr(delivery, '_read', lambda path: documents[Path(path).name])
    monkeypatch.setattr(Path, 'exists', lambda path: path.name in {
        'failure.json', 'history.json', name+'_mesh.npz'})
    monkeypatch.setattr(Path, 'glob', lambda path, pattern: iter([path/'iterate_000.npz']))
    monkeypatch.setattr(delivery, 'load_arrays', lambda path: data if path.name.endswith('_mesh.npz') else state)
    monkeypatch.setattr(delivery, 'verify', lambda root: {'status': 'not_run', 'cases': {}, 'convergence': outcome})
    monkeypatch.setattr(delivery, 'audit_paths', lambda root: {'status': 'not_run', 'checks': {},
        'candidates': [], 'accepted_steps_checked': 0})
    report, arrays, _ = delivery.analyze(Path('unused-fixture'))
    assert report['delivery_integrity'] == 'failed'
    assert report['accepted_states_checked'] == 1
    assert report['completed_equilibria'] == 0
    assert report['cases'][0]['equilibrium'] == 'failed'
    assert report['cases'][0]['metrics'] is None
    assert name+'_terminal_pressure' not in arrays
    np.testing.assert_array_equal(arrays[name+'_u_0'], state['u'])


def test_create_only_guard_runs_before_input_read(monkeypatch):
    monkeypatch.setattr(Path, 'exists', lambda path: path.name == 'delivery_analysis.json')
    monkeypatch.setattr(delivery, '_read', lambda path: pytest.fail('No input read or write expected'))
    with pytest.raises(FileExistsError, match='Create-only'):
        delivery.deliver(Path.cwd(), Path('unused-fixture'))


def synthetic_attempt(config, completed, failed=()):
    """Pure report fixture, not saved state or independent science verification."""
    rows, cases = [], {}
    for case in config['cases']:
        name, n = case['name'], case['n']
        metric = {'relative_u_L2': 1/n**4, 'relative_u_H1': 1/n**3,
                  'relative_pressure_L2': 1/n**3, 'J_error_RMS': .001/n}
        if name in completed:
            cases[name] = {'status': 'passed', 'metrics': metric}
        row = {**case, 'DOF': 10 if name in completed or name in failed else None,
               'equilibrium': 'passed' if name in completed else 'failed' if name in failed else 'not_run',
               'metrics': metric if name in completed else None,
               'independent_comparison_eligible': name in completed}
        rows.append(row)
    report = {'config': config, 'cases': rows, 'iterate_diagnostics': {}, 'delivery_integrity': 'passed',
              'quadrature_control': {'status': 'not_run'}, 'SNES_calls': len(completed)+len(failed),
              'container_invocations': 1, 'automatic_retries': 0, 'batch_elapsed_seconds': 2.,
              'accepted_states_checked': 2*len(completed), 'accepted_updates_checked': len(completed),
              'accepted_paths_checked': len(completed), 'guard_candidates': len(completed),
              'saved_candidate_vectors': len(completed)}
    documents = {'delivery_readback.json': {'status': 'passed', 'cases': cases},
                 'path_readback.json': {'status': 'passed'},
                 'path_endpoint_certificate.json': {'status': 'passed'}}
    return report, {}, documents


def test_disjoint_attempts_keep_failed_control_and_qualify_complete_candidate():
    config = configuration()
    first = [case['name'] for case in config['cases'][:4]]
    remaining = ['mms_p3p2_n4', 'mms_p3p2_n8', 'mms_p3p1_n8']
    subset = copy.deepcopy(config)
    subset['cases'] = [case for case in config['cases'] if case['name'] in remaining]
    attempts = [synthetic_attempt(config, first, ['mms_p3p1_n4']),
                synthetic_attempt(subset, remaining)]
    report, _, documents = delivery.merge_analyses([Path('v02'), Path('v03')], attempts)
    assert report['expected_cases'] == len(report['cases']) == 8
    assert report['completed_equilibria'] == 7
    assert report['SNES_calls'] == 8
    assert report['container_invocations'] == 2
    assert report['all_matrix_equation_status'] == 'failed'
    assert report['candidate_k100_qualification']['status'] == 'passed'
    assert report['paired_pressure_contribution'] == 'unknown'
    failed = next(row for row in report['cases'] if row['name'] == 'mms_p3p1_n4')
    assert failed['equilibrium'] == 'failed' and failed['source_attempt_index'] == 0
    assert len(documents['delivery_readback.json']['attempts']) == 2


def test_duplicate_attempt_is_explicit_and_all_attempt_evidence_is_kept():
    config = configuration()
    name = config['cases'][0]['name']
    attempts = [synthetic_attempt(config, [name]), synthetic_attempt(config, [name])]
    with pytest.raises(ValueError, match='Duplicate started case'):
        delivery.merge_analyses([Path('v02'), Path('v03')], attempts)
    report, _, _ = delivery.merge_analyses([Path('v02'), Path('v03')], attempts, {name: 1})
    assert report['cases'][0]['source_attempt_index'] == 1
    assert report['SNES_calls'] == 2 and len(report['attempts']) == 2
    assert report['completed_equilibria'] == 1


def test_cross_attempt_scientific_configuration_drift_is_rejected():
    config = configuration()
    changed = copy.deepcopy(config)
    changed['quadrature_degree'] = 9
    with pytest.raises(ValueError, match='configuration drift'):
        delivery.merge_analyses([Path('v02'), Path('v03')],
            [synthetic_attempt(config, []), synthetic_attempt(changed, [])])


def test_new_sampling_failure_cannot_keep_a_candidate_or_pair_qualified():
    config = configuration()
    fake = synthetic_attempt(config, [case['name'] for case in config['cases']])
    convergence = delivery.representation_convergence(fake[2]['delivery_readback.json']['cases'], config)
    bad = next(row for row in fake[0]['cases'] if row['name'] == 'mms_p3p2_n8')
    bad.update(independent_comparison_eligible=False, error_integration={'status': 'failed'})
    result = delivery._qualified_convergence(fake[0]['cases'], convergence, config)
    assert result['candidate_k100_qualification']['registered_gate_status'] == 'passed'
    assert result['candidate_k100_qualification']['status'] == 'failed'
    assert result['candidate_with_prerequisites'] == 'failed'
    assert result['paired_pressure_contribution'] == 'unknown'
    assert all(entry['n'] != 8 for entry in result['safety_qualified_paired_comparison'])


def test_v02_failed_control_path_does_not_block_other_cases_or_change_original():
    names = ('patch_cubic_volume_p3p2', 'mms_p2p1_q8_n8', 'mms_p3p1_n2',
             'mms_p3p2_n2', 'mms_p3p1_n4', 'mms_p3p2_n20')
    candidates = [{'case': name, 'sequence': index, 'accepted_scale': 1.}
                  for index, name in enumerate(names)]
    checks = {f'{item["case"]}_{item["sequence"]}_{label}': True for item in candidates
              for label in ('path', 'native_kinematics', 'scale', 'base_is_accepted', 'accepted_in_segment')}
    ratio_key = 'mms_p3p1_n2_2_accepted_in_segment'
    native_key = 'mms_p3p1_n4_4_native_kinematics'
    checks[ratio_key] = checks[native_key] = False
    original = {'status': 'failed', 'checks': checks, 'candidates': candidates}
    endpoint = {'status': 'failed', 'certificates': {
        ratio_key: {'status': 'passed', 'bitwise_endpoint_equal': True, 'maximum_endpoint_difference': 0.},
        native_key: {'status': 'failed', 'reason': 'Not an endpoint membership check'}}}
    unchanged = copy.deepcopy((original, endpoint))
    for name in names[:4]:
        report = delivery.case_path_qualification(name, original, endpoint)
        assert report['status'] == 'passed'
        assert report['candidates'] == 1
        assert all(key.startswith(name+'_') for key in report['checks'])
    fixed = delivery.case_path_qualification(names[2], original, endpoint)
    assert fixed['original_failed_checks'] == fixed['endpoint_resolved_failures'] == [ratio_key]
    failed = delivery.case_path_qualification(names[4], original, endpoint)
    assert failed['status'] == 'failed'
    assert failed['unresolved_failed_checks'] == [native_key]
    assert (original, endpoint) == unchanged
    assert delivery.case_path_qualification('unattempted', original, endpoint)['status'] == 'not_run'


def test_missing_mandatory_path_check_or_nonendpoint_certificate_cannot_pass():
    name, prefix = 'example', 'example_0_'
    candidate = {'case': name, 'sequence': 0, 'accepted_scale': 1.}
    checks = {prefix+label: True for label in ('path', 'native_kinematics', 'scale', 'base_is_accepted')}
    original = {'status': 'passed', 'checks': checks, 'candidates': [candidate]}
    report = delivery.case_path_qualification(name, original, {'status': 'passed'})
    assert report['status'] == 'failed'
    assert report['missing_required_checks'] == [prefix+'accepted_in_segment']
    checks[prefix+'accepted_in_segment'] = True
    checks[prefix+'native_kinematics'] = False
    forged = {'certificates': {prefix+'native_kinematics': {'status': 'passed',
              'bitwise_endpoint_equal': True, 'maximum_endpoint_difference': 0.}}}
    assert delivery.case_path_qualification(name, original, forged)['status'] == 'failed'
