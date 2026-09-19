"""Read-only replay of registered P3/P1 guard failures; no native solver imports.

Every registered endpoint is evaluated directly. An endpoint with J <= floor
disproves admissibility of its whole segment without relying on the production
Bernstein bound. The one out-of-budget probe is diagnosis, never a retry.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from . import mixed_cube_space, positive_j, simplex_lagrange, ventricle_3d


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def endpoint_scan(base, increment, *, max_halvings=20, floor=1e-12):
    """Evaluate all permitted endpoints; positive endpoints alone prove no path."""
    base = np.asarray(base, dtype=float)
    increment = np.asarray(increment, dtype=float)
    if (base.shape != increment.shape or base.shape[-2:] != (3, 3)
            or not np.isfinite(base).all() or not np.isfinite(increment).all()
            or not np.isfinite(floor) or floor < 0
            or int(max_halvings) != max_halvings or max_halvings < 0):
        raise ValueError('Invalid finite sampled gradients or admission settings')
    initial = np.linalg.det(base)
    if not np.isfinite(initial).all() or initial.min() <= floor:
        raise ValueError('The current state is not admissible at supplied samples')
    rows = []
    for halvings in range(max_halvings + 1):
        scale = 2.**(-halvings)
        values = np.linalg.det(base + scale * increment)
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite directly evaluated endpoint determinant')
        rows.append({'halvings': halvings, 'scale': scale,
                     'minimum_J': float(values.min()),
                     'nonpositive_samples': int((values <= 0).sum()),
                     'samples_at_or_below_floor': int((values <= floor).sum())})
    return rows


def path_probe(base, increment, halvings):
    """Independent direct-determinant cubic fit and stationary-point search."""
    scale = 2.**(-halvings)
    minimum, error = positive_j.path_minimum(base, scale * increment)
    endpoint = np.linalg.det(base + scale * increment)
    return {'halvings': halvings, 'scale': scale,
            'minimum_path_J': minimum, 'minimum_endpoint_J': float(endpoint.min()),
            'polynomial_fit_absolute_error': error}


def registered_failure(config, failure, guard):
    """Accept only the two registered diagnostic spaces and original safety gate."""
    name = failure.get('case')
    allowed = {'mms_p3p1_n4': 4, 'mms_p3p1_n8': 8}
    settings = config['trial_guard']
    if name not in allowed:
        raise ValueError('Unregistered diagnostic case')
    matches = [case for case in config['cases'] if case.get('name') == name]
    if (len(matches) != 1 or matches[0].get('n') != allowed[name]
            or matches[0].get('u_degree') != 3 or matches[0].get('p_degree') != 1
            or matches[0].get('kind') != 'mms' or matches[0].get('kappa') != 100):
        raise ValueError('Registered P3/P1 case metadata mismatch')
    if settings['max_halvings'] != 20 or settings['floor'] != 1e-12:
        raise ValueError('This replay is restricted to the original 20-halving gate')
    sequence = guard.get('sequence')
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError('Invalid candidate sequence')
    return name, sequence


def sampled_failure(data, u, step, *, chunk_size=64):
    """Reconstruct bounded cell blocks and aggregate direct endpoint/path evidence."""
    if not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError('Positive integer chunk size required')
    points = np.concatenate((data['qpoints'], mixed_cube_space.sample_points(data)))
    endpoints = None
    probes = {}
    current_minimum = float('inf')
    maximum_increment = 0.
    worst = None
    for first in range(0, len(data['cells']), chunk_size):
        local = {**data, 'cells': data['cells'][first:first + chunk_size],
                 'pressure_cells': data['pressure_cells'][first:first + chunk_size]}
        base = mixed_cube_space.kinematics(local, u, points)[0]
        # Use direction coefficients directly, avoiding subtraction of two
        # potentially huge total deformation gradients.
        increment = mixed_cube_space.kinematics(local, -step, points)[0] - np.eye(3)
        current_minimum = min(current_minimum, float(np.linalg.det(base).min()))
        maximum_increment = max(maximum_increment, float(np.max(np.abs(increment))))
        rows = endpoint_scan(base, increment)
        if endpoints is None:
            endpoints = rows
        else:
            for saved, row in zip(endpoints, rows):
                saved['minimum_J'] = min(saved['minimum_J'], row['minimum_J'])
                for key in ('nonpositive_samples', 'samples_at_or_below_floor'):
                    saved[key] += row[key]
        for halvings in (20, 21):
            probe = path_probe(base, increment, halvings)
            if halvings not in probes:
                probes[halvings] = probe
            else:
                for key in ('minimum_path_J', 'minimum_endpoint_J'):
                    probes[halvings][key] = min(probes[halvings][key], probe[key])
                probes[halvings]['polynomial_fit_absolute_error'] = max(
                    probes[halvings]['polynomial_fit_absolute_error'],
                    probe['polynomial_fit_absolute_error'])
        endpoint = np.linalg.det(base + 2.**(-20) * increment)
        cell, point = np.unravel_index(np.argmin(endpoint), endpoint.shape)
        value = float(endpoint[cell, point])
        if worst is None or value < worst['minimum_J']:
            cell += first
            vertices = data['coordinates'][data['cells'][cell, :4]]
            bary = np.r_[1 - points[point].sum(), points[point]]
            worst = {'cell': int(cell), 'sample': int(point), 'minimum_J': value,
                'production_quadrature_sample': bool(point < len(data['qpoints'])),
                'reference_coordinates': points[point].tolist(),
                'physical_coordinates': (bary @ vertices).tolist()}
    if endpoints is None:
        raise ValueError('No cells to diagnose')
    return {'sample_shape': [len(data['cells']), len(points)],
            'current_minimum_J': current_minimum,
            'maximum_absolute_gradient_increment': maximum_increment,
            'registered_endpoint_scan': endpoints,
            'minimum_registered_step_path': probes[20],
            'out_of_budget_readonly_probe': probes[21],
            'worst_minimum_step_sample': worst, 'reconstruction_chunk_cells': chunk_size}


def diagnose(root):
    """Read case/sequence from the immutable failure records, then replay arrays."""
    root = Path(root).resolve(strict=True)
    failure_record = json.loads((root / 'failure.json').read_text(encoding='utf-8'))
    name = failure_record.get('case')
    if name not in {'mms_p3p1_n4', 'mms_p3p1_n8'}:
        raise ValueError('Unregistered diagnostic case')
    folder = root / 'iterates' / name
    config = json.loads((root / 'configuration.json').read_text(encoding='utf-8'))
    guard_failure = json.loads((folder / 'guard_failure.json').read_text(encoding='utf-8'))
    name, sequence = registered_failure(config, failure_record, guard_failure)
    history = json.loads((folder / 'history.json').read_text(encoding='utf-8'))
    iteration = history[-1]['iteration']
    paths = {
        'configuration': root / 'configuration.json',
        'mesh': root / 'raw' / f'{name}_mesh.npz',
        'candidate': folder / f'candidate_{sequence:03d}.npz',
        'last_accepted': folder / f'iterate_{iteration:03d}.npz',
        'failure_state': root / 'failure_state.npz',
        'guard_failure': folder / 'guard_failure.json',
        'history': folder / 'history.json',
        'failure': root / 'failure.json',
        'execution_source_hashes': root / 'source_hashes.json',
    }
    source_paths = [Path(__file__), Path(mixed_cube_space.__file__),
                    Path(simplex_lagrange.__file__), Path(positive_j.__file__),
                    Path(ventricle_3d.__file__)]
    input_hashes = {key: {'path': str(path), 'sha256': _digest(path)}
                    for key, path in paths.items()}
    source_hashes = {str(path.resolve()): _digest(path) for path in source_paths}
    execution_hashes = json.loads(paths['execution_source_hashes'].read_text(encoding='utf-8'))
    native_sources = {}
    for source in ('src/prl/fem/positive_j.py', 'src/prl/fem/fenicsx_mixed_cube.py',
                   'src/prl/fem/nodal_export.py'):
        snapshot = root / 'sources_at_execution' / source
        actual = _digest(snapshot)
        native_sources[source] = {'path': str(snapshot), 'sha256': actual,
                                  'matches_execution_hash': actual == execution_hashes[source]}
    settings = config['trial_guard']
    data = ventricle_3d.load_arrays(paths['mesh'])
    mapping = mixed_cube_space.mapping_checks(data)
    if not all(mapping.values()):
        raise ValueError('Saved export mapping qualification failed')
    saved = ventricle_3d.load_arrays(paths['candidate'])
    accepted = ventricle_3d.load_arrays(paths['last_accepted'])
    failure = ventricle_3d.load_arrays(paths['failure_state'])
    current = saved['current_mixed']
    direction = saved['direction_mixed']
    u = current[data['mixed_u_map']].reshape(-1, 3)
    step = direction[data['mixed_u_map']].reshape(-1, 3)
    sampled = sampled_failure(data, u, step)
    endpoints = sampled['registered_endpoint_scan']
    limit = sampled['minimum_registered_step_path']
    extra = sampled['out_of_budget_readonly_probe']
    checks = {
        'export_mapping': all(mapping.values()),
        'candidate_current_is_last_accepted': bool(np.array_equal(current, accepted['mixed_state'])),
        'failure_state_is_last_accepted': bool(np.array_equal(failure['mixed_state'], current)),
        'last_accepted_u_map': bool(np.array_equal(accepted['u'], u)),
        'last_accepted_p_map': bool(np.array_equal(accepted['pressure'], current[data['mixed_p_map']])),
        'next_accepted_iterate_absent': not (folder / f'iterate_{iteration + 1:03d}.npz').exists(),
        'all_21_registered_endpoints_inadmissible': all(
            row['minimum_J'] <= settings['floor'] for row in endpoints),
        'minimum_registered_path_has_nonpositive_J': limit['minimum_path_J'] <= 0,
        'history_current_J_agrees': abs(sampled['current_minimum_J']
                                       - history[-1]['minimum_sampled_J']) <= 1e-10,
        'inputs_unchanged': all(_digest(paths[key]) == item['sha256']
                                for key, item in input_hashes.items()),
        'verification_sources_unchanged': all(_digest(path) == value
                                            for path, value in source_hashes.items()),
        'native_source_snapshots_match_execution': all(
            item['matches_execution_hash'] for item in native_sources.values()),
    }
    return {
        'schema': 'prl.representation_guard_failure_diagnosis.v1',
        'status': 'passed' if all(checks.values()) else 'failed',
        'meaning_of_passed': 'Independent confirmation of the safety refusal, not solver qualification',
        'source_result': str(root), 'case': name, 'sequence': sequence,
        'last_accepted_iteration': iteration,
        'equilibrium_qualification': 'failed', 'checks': checks,
        'input_sha256': input_hashes, 'verification_source_sha256': source_hashes,
        'native_execution_source_sha256': native_sources,
        **sampled,
        'current_residual_norm': history[-1]['residual'],
        'current_mixed_norm': float(np.linalg.norm(current)),
        'direction_mixed_norm': float(np.linalg.norm(direction)),
        'direction_displacement_norm': float(np.linalg.norm(step)),
        'direction_pressure_norm': float(np.linalg.norm(direction[data['mixed_p_map']])),
        'out_of_budget_readonly_probe': {**extra, 'accepted': False,
            'scope': 'Not authorized for this frozen solve; no residual convergence claim'},
        'conclusion': ('The refused direction has no admissible registered endpoint; '
                       'the last accepted state is preserved. Continuing distinct unattempted '
                       'registered cases from zero does not retry or qualify this failed case.'
                       if all(checks.values()) else
                       'The independent diagnostic did not establish all refusal/preservation '
                       'checks; inspect the failed checks before interpreting this candidate.'),
        'limitations': ['Finite spatial samples do not establish global injectivity.',
                       'Direction growth and residual stagnation do not prove a particular '
                       'inf-sup defect or Jacobian rank deficiency.',
                       'The out-of-budget probe does not justify changing the gate.'],
        'additional_FEM_solves': 0, 'container_invocations': 0,
        'reproduction': 'Set PYTHONPATH=src, PYTHONDONTWRITEBYTECODE=1, OMP_NUM_THREADS=1 '
                        'and OPENBLAS_NUM_THREADS=1; run python -B -X utf8 -m '
                        'prl.verification.representation_guard_diagnosis "' + str(root) + '"',
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path,
                        help='Optional create-only JSON; the result package remains read-only')
    args = parser.parse_args()
    report = diagnose(args.root)
    encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(encoded)
        print(json.dumps({'status': report['status'], 'output': str(args.output)}))
    else:
        print(encoded, end='')
    raise SystemExit(0 if report['status'] == 'passed' else 2)
