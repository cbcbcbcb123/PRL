"""Create-only, solver-free readback of the same-load representation experiment.

Reported engineering integrity, candidate qualification and paired inference are
separate. Synthetic test fixtures never constitute scientific qualification.
"""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial import cKDTree

from prl.verification.mixed_cube import error_metrics, quadrature, verify
from prl.verification.mixed_cube_space import kinematics, pressure_shape, sample_points
from prl.verification.mixed_cube_representation import convergence as representation_convergence
from prl.verification.positive_j import audit_paths
from prl.verification.saved_segment import resolve_roundtrip
from prl.verification.ventricle_3d import load_arrays


SCHEMA = 'prl.mixed_cube_representation_proposal.v1'


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _attempt(function, *args):
    try:
        return function(*args)
    except Exception as error:
        return {'status': 'failed', 'reason': repr(error)}


def check_mixed_mapping(data, state):
    """Require complete, disjoint vector maps, not merely matching prefixes."""
    mixed = state['mixed_state']
    first, second = data['mixed_u_map'], data['mixed_p_map']
    combined = np.concatenate((first, second))
    valid = (mixed.ndim == 1 and np.issubdtype(combined.dtype, np.integer)
             and len(combined) == len(mixed)
             and np.array_equal(np.sort(combined), np.arange(len(mixed)))
             and all(np.isfinite(state[key]).all() for key in ('u', 'pressure', 'mixed_state'))
             and np.array_equal(mixed[first], state['u'].ravel())
             and np.array_equal(mixed[second], state['pressure']))
    if not valid:
        raise ValueError('Invalid or drifting saved mixed-state mapping')


def describe_iterate(data, state):
    """Evaluate all real saved states in bounded cell chunks, including failures."""
    check_mixed_mapping(data, state)
    report = {'maximum_nodal_displacement': float(np.linalg.norm(state['u'], axis=1).max())}
    for label, points in (('production', data['qpoints']), ('extra', sample_points(data))):
        minima, maxima, nonpositive, cells_bad = [], [], 0, 0
        for first in range(0, len(data['cells']), 64):
            local = {**data, 'cells': data['cells'][first:first+64]}
            jacobian = kinematics(local, state['u'], points)[1]
            if not np.isfinite(jacobian).all():
                raise ValueError('Nonfinite persisted-state Jacobian')
            minima.append(float(jacobian.min()))
            maxima.append(float(jacobian.max()))
            nonpositive += int((jacobian <= 0).sum())
            cells_bad += int(np.any(jacobian <= 0, axis=1).sum())
        if not minima:
            raise ValueError('Empty saved mesh')
        report[label] = dict(minimum_J=min(minima), maximum_J=max(maxima),
                             nonpositive_points=nonpositive, cells_with_nonpositive_J=cells_bad)
    report['status'] = ('passed' if all(report[key]['minimum_J'] > 0
                                      for key in ('production', 'extra')) else 'failed')
    return report


def coordinate_alignment(reference, current, tolerance=1e-12):
    """Return current indices in reference order; reject ambiguous/missing nodes."""
    reference, current = np.asarray(reference), np.asarray(current)
    if (reference.shape != current.shape or reference.ndim != 2 or reference.shape[1] != 3
            or len(reference) == 0 or not np.isfinite(reference).all() or not np.isfinite(current).all()):
        raise ValueError('Incompatible/nonfinite coordinate arrays')
    distance, indices = cKDTree(current).query(reference, k=2)
    if (np.max(distance[:, 0]) > tolerance or np.any(distance[:, 1] <= tolerance)
            or len(np.unique(indices[:, 0])) != len(reference)):
        raise ValueError('Coordinate correspondence is not a unique tolerance-bounded bijection')
    return indices[:, 0], float(distance[:, 0].max())


def _difference(reference, current):
    delta = current-reference
    denominator = float(np.linalg.norm(reference))
    return {'relative_nodal_l2': float(np.linalg.norm(delta)/denominator) if denominator else None,
            'absolute_nodal_l2': float(np.linalg.norm(delta)),
            'maximum_absolute_component': float(np.abs(delta).max()),
            'maximum_nodal_magnitude': float(np.linalg.norm(delta, axis=1).max())
            if delta.ndim == 2 else float(np.abs(delta).max())}


def compare_aligned_states(reference_data, reference_state, current_data, current_state):
    """Nodal vector comparison, explicitly not a spatially integrated L2 norm."""
    for data, state in ((reference_data, reference_state), (current_data, current_state)):
        check_mixed_mapping(data, state)
        if (int(data.get('u_degree', 2)), int(data.get('p_degree', 1))) != (2, 1):
            raise ValueError('Quadrature control requires the same P2/P1 spaces')
    report = {'status': 'passed', 'norm_scope': 'coordinate-aligned nodal Euclidean norms; not field L2'}
    for label, coordinate, cell in (('u', 'coordinates', 'cells'),
                                     ('pressure', 'pressure_coordinates', 'pressure_cells')):
        indices, maximum = coordinate_alignment(reference_data[coordinate], current_data[coordinate])
        inverse = np.empty_like(indices)
        inverse[indices] = np.arange(len(indices))
        expected = sorted(tuple(sorted(row)) for row in reference_data[cell])
        actual = sorted(tuple(sorted(row)) for row in inverse[current_data[cell]])
        if expected != actual:
            raise ValueError('Quadrature-control mesh connectivity differs')
        report[label] = {**_difference(reference_state[label], current_state[label][indices]),
                         'maximum_coordinate_difference': maximum, 'nodes': len(indices)}
    return report


def quadrature_control(root, reference_root, cases):
    current_name, old_name = 'mms_p2p1_q8_n8', 'mms_k100_n8'
    if reference_root is None or not (root/'raw'/f'{current_name}_state.npz').exists():
        return {'status': 'not_run', 'reason': 'No current terminal state or historical reference supplied'}
    reference_root = Path(reference_root)
    old_path = reference_root/'raw'/f'{old_name}_state.npz'
    if not old_path.exists():
        return {'status': 'not_run', 'reason': 'Historical n8 terminal state missing'}
    old_config, current_config = _read(reference_root/'configuration.json'), _read(root/'configuration.json')
    old_case = next(item for item in old_config['cases'] if item['name'] == old_name)
    current_case = next(item for item in current_config['cases'] if item['name'] == current_name)
    if (any(old_case[key] != current_case[key] for key in ('kind', 'kappa', 'n'))
            or (old_config['quadrature_degree'], current_config['quadrature_degree']) != (6, 8)):
        raise ValueError('Quadrature-control frozen case or integration degrees differ')
    report = compare_aligned_states(load_arrays(reference_root/'raw'/f'{old_name}_mesh.npz'),
        load_arrays(old_path), load_arrays(root/'raw'/f'{current_name}_mesh.npz'),
        load_arrays(root/'raw'/f'{current_name}_state.npz'))
    old_audit = _read(reference_root/'raw'/f'{old_name}_audit.json')
    report.update(reference_root=str(reference_root.resolve()), reference_case=old_name,
        current_case=current_name, reference_quadrature_degree=6, current_quadrature_degree=8,
        equation_qualified_pair=(old_audit['status'] == 'passed'
                                 and cases.get(current_name, {}).get('status') == 'passed'),
        interpretation='Only n8 is a matched integration control; old n2/n4 remain historical.')
    return report


def terminal_pressure_for_faces(data, state):
    """Evaluate P1/P2 at actual face centroids through each owning tetrahedron."""
    owners = data['boundary_owners']
    vertices = data['coordinates'][data['cells'][owners, :4]]
    centroids = data['coordinates'][data['boundary_faces'][:, :3]].mean(axis=1)
    mapping = np.stack([vertices[:, index]-vertices[:, 0] for index in (1, 2, 3)], axis=-1)
    reference = np.linalg.solve(mapping, (centroids-vertices[:, 0])[..., None])[..., 0]
    basis = pressure_shape(data, reference)
    return np.einsum('fa,fa->f', basis, state['pressure'][data['pressure_cells'][owners]])


def integration_diagnostics(data, state, case):
    """Retain the original readback when denser sampling discovers unsafe J."""
    result = {'qualification_uses_frozen_order6': True, 'threshold_changes': 0}
    for order in (6, 8):
        try:
            result[f'order{order}'] = error_metrics(data, state, case, order=order)[0]
        except Exception as error:
            result[f'order{order}'] = None
            result[f'order{order}_failure'] = repr(error)
    result['order8_J_safety'] = _attempt(describe_iterate,
        {**data, 'qpoints': quadrature(3, 8)[0]}, state)
    six, eight = result['order6'], result['order8']
    result['absolute_differences'] = ({key: abs(eight[key]-value) if value is not None else None
                                       for key, value in six.items()
                                       if key != 'evaluation_points_per_cell'} if six and eight else None)
    result['status'] = ('passed' if six and eight and result['order8_J_safety']['status'] == 'passed'
                        else 'failed')
    return result


def case_path_qualification(name, original, endpoint):
    """Keep mandatory path checks local without changing the original whole audit."""
    if 'candidates' not in original or 'checks' not in original:
        return {'status': 'failed', 'reason': 'Original path audit could not finish',
                'original_audit_status': original['status']}
    candidates = [item for item in original['candidates'] if item['case'] == name]
    prefixes = [f'{name}_{item["sequence"]}_' for item in candidates]
    checks = {key: value for key, value in original['checks'].items()
              if any(key.startswith(prefix) for prefix in prefixes)}
    required = []
    for item, prefix in zip(candidates, prefixes):
        required.extend(prefix+label for label in ('path', 'native_kinematics', 'scale', 'base_is_accepted'))
        if item['accepted_scale'] is not None:
            required.append(prefix+'accepted_in_segment')
    missing = [key for key in required if key not in checks]
    failed = [key for key, value in checks.items() if not value]
    certificates = {key: endpoint.get('certificates', {})[key] for key in failed
                    if key in endpoint.get('certificates', {})}
    resolved = [key for key in failed if key.endswith('_accepted_in_segment')
                and certificates.get(key, {}).get('status') == 'passed'
                and certificates[key].get('bitwise_endpoint_equal') is True
                and certificates[key].get('maximum_endpoint_difference') == 0.]
    unresolved = [key for key in failed if key not in resolved]
    status = ('failed' if missing or unresolved else 'passed' if candidates else 'not_run')
    return {'status': status, 'candidates': len(candidates), 'checks': checks,
            'original_audit_status': original['status'], 'original_failed_checks': failed,
            'certificates': certificates, 'endpoint_resolved_failures': resolved,
            'unresolved_failed_checks': unresolved, 'missing_required_checks': missing,
            'original_checks_preserved': True, 'threshold_changes': 0}


def _qualified_convergence(rows, convergence, config):
    eligible = {row['name'] for row in rows if row.get('independent_comparison_eligible')}
    paired = [entry for entry in convergence.get('paired_comparison', [])
              if all(f'mms_p3p{degree}_n{entry["n"]}' in eligible for degree in (1, 2))]
    contribution = ('passed' if len(paired) == 3 and all(entry[key]['decreased'] for entry in paired
                     for key in ('relative_u_H1', 'relative_pressure_L2')) else 'unknown')
    candidate = dict(convergence.get('groups', {}).get('candidate_p3p2', {'status': 'not_run'}))
    candidate['registered_gate_status'] = candidate['status']
    candidate_names = {case['name'] for case in config['cases'] if case['role'] == 'candidate'}
    unsafe_candidates = [row['name'] for row in rows if row['name'] in candidate_names
                         and row.get('error_integration', {}).get('status') == 'failed']
    if unsafe_candidates:
        candidate.update(status='failed', additional_readback_failures=unsafe_candidates)
    elif candidate['status'] == 'passed' and not candidate_names.issubset(eligible):
        candidate.update(status='blocked', reason='Candidate saved-state or path safety is not fully verified')
    prerequisite_names = {case['name'] for case in config['cases']
                          if case['role'] in {'candidate', 'prerequisite', 'quadrature_control'}}
    candidate_with_prerequisites = convergence['status']
    if any(row.get('error_integration', {}).get('status') == 'failed'
           for row in rows if row['name'] in prerequisite_names):
        candidate_with_prerequisites = 'failed'
    elif candidate_with_prerequisites == 'passed' and not prerequisite_names.issubset(eligible):
        candidate_with_prerequisites = 'blocked'
    return {'candidate_k100_qualification': candidate,
            'candidate_with_prerequisites': candidate_with_prerequisites,
            'registered_candidate_with_prerequisites': convergence['status'],
            'paired_pressure_contribution': contribution, 'safety_qualified_paired_comparison': paired}


def _matrix_status(rows):
    states = [row['equilibrium'] for row in rows]
    return ('passed' if states and all(value == 'passed' for value in states)
            else 'failed' if 'failed' in states else 'not_run'
            if all(value == 'not_run' for value in states) else 'blocked')


def analyze(root, reference_root=None):
    root = Path(root)
    config, summary = _read(root/'configuration.json'), _read(root/'summary.json')
    if config['schema'] != SCHEMA:
        raise ValueError('Only the registered representation experiment is supported')
    readback = _attempt(verify, root)
    paths = _attempt(audit_paths, root)
    endpoint = (_attempt(resolve_roundtrip, root, paths) if 'candidates' in paths
                else {'status': 'failed', 'reason': 'Path audit could not finish'})
    failure = _read(root/'failure.json') if (root/'failure.json').exists() else {}
    reports = readback.get('cases', {})
    rows, iterates, arrays, checks = [], {}, {}, {}
    for case in config['cases']:
        name = case['name']
        native = summary.get('cases', {}).get(name, {})
        audited = reports.get(name, {})
        row = {**case, 'equilibrium': audited.get('status', 'not_run'), 'metrics': None,
               'DOF': None, 'tetrahedra': None, 'solver_seconds': None,
               'preparation_seconds': native.get('preparation_seconds'), 'iterations': None,
               'process_peak_rss_bytes': None,
               'memory_scope': 'Linux process cumulative high-water RSS through this case; not isolated case peak'}
        row['case_path_qualification'] = case_path_qualification(name, paths, endpoint)
        row['case_path_status'] = row['case_path_qualification']['status']
        if failure.get('case') == name:
            row.update(equilibrium='failed', reason='interrupted; no qualified terminal equilibrium')
        mesh_path = root/'raw'/f'{name}_mesh.npz'
        state_path = root/'raw'/f'{name}_state.npz'
        if not mesh_path.exists():
            if state_path.exists() or native:
                checks[name+'_required_mesh'] = False
            rows.append(row)
            continue
        data = load_arrays(mesh_path)
        row.update(DOF=len(data['mixed_u_map'])+len(data['mixed_p_map']), tetrahedra=len(data['cells']))
        for key in ('coordinates', 'cells', 'pressure_coordinates', 'pressure_cells',
                    'boundary_faces', 'boundary_tags', 'boundary_owners', 'mixed_u_map', 'mixed_p_map',
                    'u_reference_nodes', 'p_reference_nodes', 'face_reference_nodes',
                    'u_degree', 'p_degree', 'fixed'):
            if key in data:
                arrays[name+'_'+key] = data[key]
        folder = root/'iterates'/name
        row['saved_candidate_vectors'] = len(list(folder.glob('candidate_*.npz')))
        if (folder/'guard_failure.json').exists():
            row['guard_failure'] = _read(folder/'guard_failure.json')
        history = _read(folder/'history.json') if (folder/'history.json').exists() else []
        entries = {int(entry['iteration']): entry for entry in history}
        saved_paths = sorted(folder.glob('iterate_*.npz'))
        numbers = [int(path.stem.split('_')[-1]) for path in saved_paths]
        checks[name+'_history_inventory'] = len(entries) == len(history) and set(numbers) == set(entries)
        states = []
        for path, index in zip(saved_paths, numbers):
            state = load_arrays(path)
            detail = _attempt(describe_iterate, data, state)
            entry = entries.get(index, {})
            if detail['status'] == 'passed' and 'minimum_sampled_J' in entry:
                minimum = min(detail[key]['minimum_J'] for key in ('production', 'extra'))
                detail['monitor_agreement'] = abs(minimum-entry['minimum_sampled_J']) <= 1e-11
                if not detail['monitor_agreement']:
                    detail['status'] = 'failed'
            checks[name+'_'+path.stem] = detail['status'] == 'passed'
            states.append({**entry, 'iteration': index, **detail})
            arrays[f'{name}_u_{index}'] = state['u']
            arrays[f'{name}_pressure_{index}'] = state['pressure']
        arrays[name+'_iterations'] = np.asarray(numbers, dtype=np.int64)
        iterates[name] = states
        if state_path.exists():
            state = load_arrays(state_path)
            metadata = (_read(state_path.with_suffix('.json'))
                        if state_path.with_suffix('.json').exists() else {})
            if not audited:
                row.update(equilibrium='failed', reason='Terminal state lacks successful independent readback')
            row.update(metrics=audited.get('metrics'), solver_seconds=metadata.get('elapsed_seconds'),
                       iterations=metadata.get('iterations'),
                       process_peak_rss_bytes=metadata.get('process_peak_rss_bytes'))
            checks[name+'_independent_terminal'] = bool(audited)
            terminal = _attempt(describe_iterate, data, state)
            checks[name+'_terminal_mapping_and_J'] = terminal['status'] == 'passed'
            row['terminal_diagnostics'] = terminal
            row['error_integration'] = integration_diagnostics(data, state, case)
            row['supplemental_order8_safety'] = row['error_integration']['order8_J_safety']['status']
            checks[name+'_error_integration'] = row['error_integration']['status'] == 'passed'
            row['independent_comparison_eligible'] = bool(audited.get('status') == 'passed'
                and checks[name+'_error_integration'] and terminal['status'] == 'passed'
                and states and all(item['status'] == 'passed' for item in states)
                and checks[name+'_history_inventory'] and row['case_path_status'] == 'passed')
            arrays[name+'_terminal_u'] = state['u']
            arrays[name+'_terminal_pressure'] = state['pressure']
            arrays[name+'_terminal_face_pressure'] = terminal_pressure_for_faces(data, state)
        elif native:
            checks[name+'_required_terminal'] = False
        if failure.get('case') == name and not state_path.exists():
            row.update(equilibrium='failed', reason='interrupted; no terminal equilibrium')
        rows.append(row)
    convergence = readback.get('convergence', {'status': 'unknown', 'groups': {}})
    comparison = _attempt(quadrature_control, root, reference_root, reports)
    statuses = [readback['status'], endpoint['status']]
    count = sum(len(items) for items in iterates.values())
    integrity = ('failed' if 'failed' in statuses or not all(checks.values()) or comparison['status'] == 'failed'
                 else 'passed' if reports or count else 'not_run')
    report = {'status': summary['status'], 'source_summary_preserved': True,
        'delivery_integrity': integrity, 'all_matrix_equation_status': _matrix_status(rows),
        **_qualified_convergence(rows, convergence, config),
        'convergence': convergence, 'cases': rows, 'config': config,
        'completed_equilibria': len(reports), 'accepted_states_checked': count,
        'qualified_equilibria': sum(item['status'] == 'passed' for item in reports.values()),
        'accepted_updates_checked': sum(sum(item['iteration'] > 0 for item in items) for items in iterates.values()),
        'accepted_paths_checked': paths.get('accepted_steps_checked', 0),
        'guard_candidates': len(paths.get('candidates', [])), 'iterate_diagnostics': iterates,
        'saved_candidate_vectors': sum(row.get('saved_candidate_vectors', 0) for row in rows),
        'completed_state_readback': readback['status'], 'original_path_audit_status': paths['status'],
        'path_audit_status': endpoint['status'], 'checks': checks, 'quadrature_control': comparison,
        'SNES_calls': summary.get('attempted_solves'), 'container_invocations': summary.get('container_invocations'),
        'automatic_retries': summary.get('automatic_retries'),
        'batch_elapsed_seconds': summary.get('elapsed_seconds'),
        'memory_comparison_scope': 'RSS is a cumulative maximum within each source process; do not sum case peaks.',
        'original_ventricular_gate': 'failed_unchanged',
        'limits': ['Newton iterations are solver progress, not physiological time.',
                   'Sampled positive J is not proof of global injectivity.',
                   'P3/P1 and P3/P2 share displacement space and loading, not total DOF.',
                   'Candidate kappa100 qualification does not qualify original kappa1000 ventricle.',
                   'Q6/Q8 state differences are nodal norms; old n2/n4 are historical only.']}
    return report, arrays, {'delivery_readback.json': readback, 'path_readback.json': paths,
                           'path_endpoint_certificate.json': endpoint}


def merge_analyses(roots, analyses, case_sources=None):
    """Merge disjoint attempts against the full eight-case contract, never hide a retry.

    Duplicate started cases require an explicit case_sources[name] root index.
    Every attempt report remains in the output even when such a choice is made.
    """
    case_sources = case_sources or {}
    if len(roots) != len(analyses) or not analyses:
        raise ValueError('Each nonempty attempt list needs exactly one root per analysis')
    configs = [item[0]['config'] for item in analyses]
    full = next((config for config in configs if len(config['cases']) == 8), None)
    if full is None:
        raise ValueError('The original full eight-case configuration is required')
    expected = {case['name']: case for case in full['cases']}
    for config in configs:
        for key in ('schema', 'quadrature_degree', 'mms_gates', 'patch_gates', 'candidate_orders', 'solver', 'trial_guard'):
            if config[key] != full[key]:
                raise ValueError('Cross-attempt frozen configuration drift: '+key)
        if any(case != expected.get(case['name']) for case in config['cases']):
            raise ValueError('Unregistered or changed cross-attempt case')
    choices = {}
    for name in expected:
        options = [(index, row) for index, (report, _, _) in enumerate(analyses)
                   for row in report['cases'] if row['name'] == name]
        started = [(index, row) for index, row in options
                   if row['DOF'] is not None or row['equilibrium'] != 'not_run']
        if name in case_sources:
            options = [(index, row) for index, row in started if index == case_sources[name]]
            if len(options) != 1:
                raise ValueError('Explicit case source does not identify a started case: '+name)
            choices[name] = options[0]
        elif len(started) > 1:
            raise ValueError('Duplicate started case requires explicit case_sources: '+name)
        else:
            choices[name] = started[0] if started else options[0]
    if set(case_sources)-set(expected):
        raise ValueError('Unknown explicit case source')
    rows, arrays, iterates, verified = [], {}, {}, {}
    for name, (index, row) in choices.items():
        report, saved_arrays, documents = analyses[index]
        rows.append({**row, 'source_root': str(Path(roots[index]).resolve()), 'source_attempt_index': index})
        arrays.update({key: value for key, value in saved_arrays.items() if key.startswith(name+'_')})
        if name in report['iterate_diagnostics']:
            iterates[name] = report['iterate_diagnostics'][name]
        if name in documents['delivery_readback.json'].get('cases', {}):
            verified[name] = documents['delivery_readback.json']['cases'][name]
    convergence = representation_convergence(verified, full)
    attempts = [{'root': str(Path(root).resolve()), 'report': item[0]}
                for root, item in zip(roots, analyses)]
    base = analyses[0][0]
    integrity_statuses = [item[0]['delivery_integrity'] for item in analyses]
    integrity = ('failed' if 'failed' in integrity_statuses else 'passed'
                 if 'passed' in integrity_statuses else 'not_run')
    matrix = _matrix_status(rows)
    result = {**base, 'status': 'passed' if matrix == convergence['status'] == 'passed' else 'failed',
        'delivery_integrity': integrity, 'all_matrix_equation_status': matrix,
        **_qualified_convergence(rows, convergence, full),
        'cases': rows, 'config': full, 'convergence': convergence,
        'attempts': attempts, 'case_source_selection': case_sources,
        'expected_cases': 8, 'completed_equilibria': len(verified),
        'qualified_equilibria': sum(item['status'] == 'passed' for item in verified.values()),
        'iterate_diagnostics': iterates,
        'quadrature_control': next((item[0]['quadrature_control'] for item in analyses
                                   if item[0]['quadrature_control']['status'] != 'not_run'),
                                  {'status': 'not_run'})}
    for key in ('SNES_calls', 'container_invocations', 'automatic_retries', 'batch_elapsed_seconds',
                'accepted_states_checked', 'accepted_updates_checked', 'accepted_paths_checked',
                'guard_candidates', 'saved_candidate_vectors'):
        values = [item[0].get(key) for item in analyses]
        result[key] = sum(values) if all(value is not None for value in values) else None
    documents = {}
    for name in ('delivery_readback.json', 'path_readback.json', 'path_endpoint_certificate.json'):
        original = [{'root': str(Path(root).resolve()), 'result': item[2][name]}
                    for root, item in zip(roots, analyses)]
        statuses = [item['result']['status'] for item in original]
        status = ('failed' if 'failed' in statuses else 'passed' if 'passed' in statuses else 'not_run')
        documents[name] = {'status': status, 'attempts': original}
    documents['delivery_readback.json'].update(cases=verified, convergence=convergence,
                                              evaluated_states=len(verified))
    result['completed_state_readback'] = documents['delivery_readback.json']['status']
    result['original_path_audit_status'] = documents['path_readback.json']['status']
    result['path_audit_status'] = documents['path_endpoint_certificate.json']['status']
    return result, arrays, documents


def deliver(workspace, root, reference_root=None, additional_roots=(), case_sources=None):
    """Preserve every input byte, including manifests, and exclusively create outputs."""
    workspace, root = Path(workspace), Path(root)
    filenames = ('delivery_analysis.json', 'delivery_readback.json', 'path_readback.json',
                 'path_endpoint_certificate.json', 'figure_states.npz', 'delivery_integrity.json')
    if any((root/name).exists() for name in filenames):
        raise FileExistsError('Create-only representation delivery: an output already exists')
    roots = [root, *map(Path, additional_roots)]
    if len({path.resolve() for path in roots}) != len(roots):
        raise ValueError('Duplicate attempt root')
    snapshots = {path: _digest(path) for source in roots for path in source.rglob('*') if path.is_file()}
    protected, source_count, references = {}, 0, {}
    for source in roots:
        references, sources = _read(source/'protected_inputs.json'), _read(source/'source_hashes.json')
        protected.update({Path(path): value for path, value in references['files'].items()})
        protected.update({source/'sources_at_execution'/name: value for name, value in sources.items()})
        source_count += len(sources)
    if reference_root is not None:
        protected.update({path: _digest(path) for path in Path(reference_root).rglob('*') if path.is_file()})
    def assert_unchanged():
        for path, expected in {**snapshots, **protected}.items():
            if not path.is_file() or _digest(path) != expected:
                raise ValueError('Protected input or execution snapshot drift: '+str(path))
    assert_unchanged()
    started = time.monotonic()
    analyses = [analyze(source, reference_root) for source in roots]
    report, arrays, documents = (merge_analyses(roots, analyses, case_sources)
                                 if len(roots) > 1 else analyses[0])
    assert_unchanged()
    documents['delivery_analysis.json'] = report
    documents['delivery_integrity.json'] = {'status': 'passed', 'scope': 'byte preservation only',
        'protected_files': len(protected), 'preexisting_dirty_files': references.get('preexisting_dirty_files'),
        'execution_source_snapshots': source_count, 'original_input_files': len(snapshots),
        'analysis_seconds': time.monotonic()-started, 'additional_solves': 0, 'gpu': 0,
        'analyzer_sha256': _digest(Path(__file__)), 'workspace': str(workspace.resolve())}
    for name, document in documents.items():
        with (root/name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    with (root/'figure_states.npz').open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    assert_unchanged()
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--reference-root', type=Path)
    parser.add_argument('--additional-root', action='append', type=Path, default=[])
    parser.add_argument('--case-sources', type=Path, help='Optional JSON case name to zero-based root index')
    args = parser.parse_args()
    result = deliver(args.workspace, args.root, args.reference_root, args.additional_root,
                     _read(args.case_sources) if args.case_sources else None)
    print(json.dumps({key: result[key] for key in ('delivery_integrity', 'all_matrix_equation_status',
        'candidate_k100_qualification', 'paired_pressure_contribution', 'completed_equilibria',
        'accepted_states_checked', 'accepted_paths_checked')}, indent=2))
