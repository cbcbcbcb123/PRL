"""Single-invocation supplement for the missing F3-B rigid-rotation gate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

import numpy as np

from prl.runs.fem_active_ellipse import _manifest, _sha256, _write_json
from prl.runs.fem_finite_strain import boundary_data, scientific_lock
from prl.storage import evaluate_storage, scan_workspace

RESULT = Path('results/ventricle_fem/f3c_rotation_repair_v01_20260917')
PARENT = Path('results/ventricle_fem/f3b_finite_strain_v01_20260917')
CONTRACT = Path('project_control/ventricle_fem_rotation_repair_contract_v01.md')
PARENT_HASH = '76167e61c4cdaf38011f6cd11ab4f329fa4d4439d9f3bf5a40dfc213acd79dc3'
CAP, RESERVE, TIMEOUT = 16 * 1024**2, 64 * 1024**2, 300
STATE_FIELDS = ('displacements', 'pressure_dofs', 'fixed_values', 'external_forces',
                'reaction', 'newton_residual', 'F', 'P', 'Cauchy', 'Green', 'J', 'energy')


def verify_parent(workspace):
    """Read-only exact-parent evidence admission, never its former run entry."""
    parent = workspace / PARENT
    manifest = parent / 'manifest.json'
    if _sha256(manifest) != PARENT_HASH:
        raise ValueError('F3-B parent manifest changed')
    items = json.loads(manifest.read_text(encoding='utf-8'))['files']
    if len(items) != 62:
        raise ValueError('F3-B parent inventory changed')
    for item in items:
        unresolved = parent / item['path']
        lexical_chain = [unresolved, *[p for p in unresolved.parents if p == parent or p.is_relative_to(parent)]]
        if any(p.is_symlink() or (getattr(p.lstat(), 'st_file_attributes', 0) &
                                 getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)) for p in lexical_chain):
            raise ValueError('Parent evidence contains a reparse/link path')
        path = unresolved.resolve()
        if not path.is_relative_to(parent.resolve()):
            raise ValueError('Parent evidence path escapes or is a link')
        if path.stat().st_size != item['bytes'] or _sha256(path) != item['sha256']:
            raise ValueError(f'Parent evidence changed: {item["path"]}')
    return {'status': 'passed', 'manifest_sha256': PARENT_HASH, 'verified_files': len(items)}


def configuration(workspace):
    parent = json.loads((workspace / PARENT / 'configuration.json').read_text(encoding='utf-8'))
    return {
        'schema_version': 'prl.fem_rotation_configuration.v1',
        'parent': {'path': '../' + PARENT.name, 'path_base': 'package',
                   'manifest_sha256': PARENT_HASH, 'expected_manifest_files': 62},
        'case': parent['cases']['nh_rigid_rotation'],
        'perturbation': {'amplitude': .002, 'components': [1, -.7, .5],
                         'definition': 'product_sin_pi_X_over_L', 'length_scale': 1.0,
                         'boundary_bubble_exactly_zero': True},
        'resources': {'threads': 1, 'gpu': 0, 'dcm': 0, 'seconds': TIMEOUT,
                      'stage_bytes': CAP, 'reserve_bytes': RESERVE, 'automatic_retries': 0},
        'new_scientific_solves': 5,
        'state_origin': ['parent_retained_0_degrees'] + ['new_equilibrium'] * 4,
        'predictor': 'reference-Q2 component-wise harmonic Dirichlet increment lifting',
        'units': 'dimensionless engineering block; angles are not physiological time',
    }


def mesh_payload(mesh):
    return {'coordinates': mesh['nodes'], 'cells': mesh['elements'],
            'pressure_coordinates': mesh['pressure_nodes'], 'pressure_cells': mesh['pressure_elements']}


def state_payload(solved, fixed, force):
    dofs = np.array(sorted(fixed), dtype=np.int64)
    return {
        'displacements': solved['u'], 'pressure_dofs': solved['p'],
        'fixed_values': np.array([fixed[int(d)] for d in dofs]),
        'external_forces': force, 'reaction': solved['residual'][:force.size],
        'newton_residual': solved['normalized_free_residual'],
        **{key: solved[key] for key in ('F', 'P', 'Green', 'J')},
        'Cauchy': solved['cauchy_stress'], 'energy': solved['energy_density'],
    }


def package_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def checkpoint(root, name, payload):
    """Owned-file atomic replacement, with old+pending bytes budgeted."""
    maximum = sum(np.asarray(v).nbytes for v in payload.values()) + 8192 * len(payload)
    if package_bytes(root) + maximum > CAP:
        raise RuntimeError('Rotation checkpoint exceeds 16 MiB stage budget')
    path = root / 'raw' / f'{name}.npz'
    pending = path.with_suffix('.pending.npz')
    np.savez_compressed(pending, **payload)
    os.replace(pending, path)


def worker(workspace):
    from prl.fem.mixed_hex import structured_mesh, lift_dirichlet_initial, solve
    root = workspace / RESULT
    pre = evaluate_storage(scan_workspace(workspace), planned_new_bytes=CAP, stop_reserve_bytes=RESERVE)
    if not pre['can_start']:
        return {'status': 'blocked', 'reason': 'storage admission', 'storage': pre}
    if not (workspace / CONTRACT).is_file():
        raise FileNotFoundError(CONTRACT)
    protected = verify_parent(workspace)
    with scientific_lock(workspace):
        root.mkdir(parents=True, exist_ok=False)
        (root / 'raw').mkdir()
        start = time.perf_counter()
        context, current_guess, solve_count = {}, None, 0
        try:
            config = configuration(workspace)
            case = config['case']
            _write_json(root / 'configuration.json', config)
            _write_json(root / 'storage_preflight.json', pre)
            _write_json(root / 'parent_evidence_preflight.json', protected)
            sources = [CONTRACT, Path('src/prl/fem/mixed_hex.py'), Path('src/prl/fem/hyperelastic.py'),
                       Path('src/prl/runs/fem_rotation.py'), Path('src/prl/runs/fem_finite_strain.py'),
                       Path('src/prl/verification/fem_rotation.py'), Path('src/prl/verification/fem_finite_strain.py'),
                       Path('src/prl/rendering/fem_rotation.py'), Path('src/prl/cli.py')]
            _write_json(root / 'source_hashes.json', {p.as_posix(): _sha256(workspace / p) for p in sources})
            mesh = structured_mesh(tuple(case['subdivisions']), case['lengths'])
            mesh_data = mesh_payload(mesh)
            with np.load(workspace / PARENT / 'raw/nh_rigid_rotation.npz', allow_pickle=False) as saved:
                parent = {key: saved[key].copy() for key in saved.files}
            if len(parent['phases']) != 1 or float(parent['phases'][0]) != 0:
                raise ValueError('Expected exactly the retained zero-degree state')
            for key, value in mesh_data.items():
                if not np.array_equal(value, parent[key]):
                    raise ValueError(f'Parent mesh mismatch: {key}')
            records = [{key: parent[key][0] for key in STATE_FIELDS}]
            histories = json.loads((workspace / PARENT / 'raw/nh_rigid_rotation_newton.json').read_text(encoding='utf-8'))
            previous = np.concatenate((parent['displacements'][0].ravel(), parent['pressure_dofs'][0]))
            fixed_dofs = parent['fixed_dofs']
            initial_records, prediction_diagnostics = [], []

            def save_rotation():
                count = len(records)
                payload = {key: np.asarray([r[key] for r in records]) for key in STATE_FIELDS}
                payload.update(mesh_data, fixed_dofs=fixed_dofs, phases=np.asarray(case['phases'][:count]),
                               activation=np.asarray(case['T_values'][:count]),
                               prescribed_stretch=np.asarray(case['stretch_values'][:count]),
                               angles=np.asarray(case['rotation_degrees'][:count]))
                checkpoint(root, 'rotation', payload)
                _write_json(root / 'raw/rotation_newton.json', histories)

            save_rotation()
            material = {**case['material'], 'fiber': case['fiber']}
            for step in range(1, 5):
                context = {'kind': 'rotation', 'angle': case['rotation_degrees'][step], 'step': step}
                if time.perf_counter() - start > TIMEOUT - 30:
                    raise TimeoutError('Rotation compute deadline reached')
                fixed, force = boundary_data(mesh, case, step)
                if not np.array_equal(np.array(sorted(fixed)), fixed_dofs):
                    raise ValueError('Fixed DOF set changed')
                boundary_only = previous.copy()
                boundary_only[fixed_dofs] = [fixed[int(d)] for d in fixed_dofs]
                current_guess = boundary_only
                lifted = lift_dirichlet_initial(mesh, previous, fixed)
                current_guess = lifted['vector']
                initial_records.append({'previous_vectors': previous.copy(), 'predicted_vectors': current_guess.copy(),
                                        'boundary_only_vectors': boundary_only,
                                        'fixed_values': np.array([fixed[int(d)] for d in fixed_dofs])})
                prediction_diagnostics.append(lifted['diagnostics'])
                checkpoint(root, 'rotation_initials', {
                    **mesh_data, 'fixed_dofs': fixed_dofs,
                    'angles': np.asarray(case['rotation_degrees'][1:step+1]),
                    **{key: np.asarray([r[key] for r in initial_records]) for key in initial_records[0]}})
                _write_json(root / 'prediction_diagnostics.json', prediction_diagnostics)
                print(f'rotation: solve {step}/4, angle {context["angle"]}', flush=True)
                solve_count += 1
                solved = solve(mesh, material, case['bulk'], dirichlet=fixed, initial=current_guess,
                               external_forces=force, tolerance=1e-9, max_iterations=30, max_line_search=16)
                records.append(state_payload(solved, fixed, force))
                histories.append(solved['history'])
                previous = solved['vector'].copy()
                save_rotation()
                _write_json(root / 'progress.json', {'status': 'unknown', 'rotation_states': len(records),
                                                    'new_solves': solve_count, 'context': context})

            context = {'kind': 'perturbed_recovery', 'angle': 60}
            if time.perf_counter() - start > TIMEOUT - 30:
                raise TimeoutError('Recovery compute deadline reached')
            perturbation = config['perturbation']
            bubble = np.prod(np.sin(np.pi * mesh['nodes'] / np.asarray(case['lengths'])), axis=1)
            on_boundary = np.any(np.isclose(mesh['nodes'], 0) |
                                 np.isclose(mesh['nodes'], case['lengths']), axis=1)
            bubble[on_boundary] = 0.0
            current_guess = previous.copy()
            current_guess[:3*len(mesh['nodes'])] += (perturbation['amplitude'] * bubble[:, None] *
                                                   np.asarray(perturbation['components'])).ravel()
            checkpoint(root, 'perturbed_initial', {**mesh_data, 'initial_vector': current_guess,
                                                  'target_vector': previous, 'fixed_dofs': fixed_dofs})
            print('perturbed recovery: one solve at 60 degrees', flush=True)
            solve_count += 1
            recovered = solve(mesh, material, case['bulk'], dirichlet=fixed, initial=current_guess,
                              external_forces=force, tolerance=1e-9, max_iterations=30, max_line_search=16)
            checkpoint(root, 'perturbed_recovery', {**mesh_data, **state_payload(recovered, fixed, force),
                                                   'fixed_dofs': fixed_dofs, 'initial_vector': current_guess,
                                                   'final_vector': recovered['vector']})
            _write_json(root / 'raw/perturbed_recovery_newton.json', recovered['history'])
            _write_json(root / 'solver_execution.json', {'status': 'passed', 'new_solves': solve_count,
                                                       'rotation_states': 5, 'parent_retained_states': 1,
                                                       'scientific_invocations': 1, 'automatic_retries': 0,
                                                       'elapsed_seconds': time.perf_counter()-start})
            if verify_parent(workspace) != protected:
                raise ValueError('Protected F3-B changed')
            _write_json(root / 'parent_evidence_postflight.json', protected)
            from prl.verification.fem_rotation import verify_fem_rotation
            verification = verify_fem_rotation(root, save=True)
            from prl.rendering.fem_rotation import render_fem_rotation
            rendering = render_fem_rotation(root)
            post = evaluate_storage(scan_workspace(workspace), planned_new_bytes=0, stop_reserve_bytes=RESERVE)
            _write_json(root / 'storage_postflight.json', post)
            # Reserve bounded metadata/manifest space before publishing status.
            # Never write a passed execution then discover a known cap failure.
            if package_bytes(root) + 65536 > CAP:
                raise RuntimeError('Final package lacks 64 KiB control-record headroom')
            report = {'status': verification['status'] if rendering['status']=='passed' and post['can_start'] else 'failed',
                      'solver_completed': True, 'rendering': rendering['status'], 'new_solves': solve_count,
                      'scientific_invocations': 1, 'automatic_retries': 0, 'threads': 1, 'gpu': 0, 'dcm': 0,
                      'biological_validation': 'not_run', 'elapsed_seconds': time.perf_counter()-start}
            _write_json(root / 'execution.json', report)
            _write_json(root / 'progress.json', report)
            _write_json(root / 'manifest.json', _manifest(root))
            return report
        except Exception as error:
            failure = {'status': 'failed', 'reason': repr(error), 'context': context,
                       'new_solve_attempts': solve_count, 'automatic_retries': 0,
                       'elapsed_seconds': time.perf_counter()-start}
            if current_guess is not None:
                retained = {'attempted_initial_vector': current_guess, **mesh_data}
                if hasattr(error, 'last_state'):
                    retained.update({k: v for k, v in error.last_state.items() if isinstance(v, np.ndarray)})
                try:
                    if hasattr(error, 'last_state'):
                        _write_json(root / 'last_iteration_history.json', error.last_state.get('history', []))
                    checkpoint(root, 'failure_state', retained)
                except (OSError, RuntimeError) as retention_error:
                    # A second disk/budget failure must not hide the original
                    # reason. Previously completed atomic checkpoints remain.
                    failure['failure_state_write_error'] = repr(retention_error)
                    failure['retained_evidence'] = 'last fully written raw checkpoints; no deletion or retry'
            _write_json(root / 'failure.json', failure)
            _write_json(root / 'progress.json', failure)
            _write_json(root / 'manifest.json', _manifest(root))
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.worker:
        if os.environ.get('PRL_ROTATION_CONTROLLER') != '1':
            raise RuntimeError('Use the bounded rotation controller')
        result = worker(workspace)
        print(json.dumps(result, indent=2))
        return 0 if result['status']=='passed' else 1
    env = os.environ.copy()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env[name] = '1'
    env.update(PYTHONPATH=str(workspace/'src'), PYTHONDONTWRITEBYTECODE='1',
               MPLCONFIGDIR=str(workspace/RESULT/'runtime_cache'), PRL_ROTATION_CONTROLLER='1')
    try:
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'prl.runs.fem_rotation',
                               '--workspace', str(workspace), '--worker'], cwd=workspace, env=env,
                              timeout=TIMEOUT, check=False).returncode
    except subprocess.TimeoutExpired:
        if (workspace/RESULT).is_dir():
            _write_json(workspace/RESULT/'timeout.json', {'status': 'failed', 'reason': '300 second cap',
                                                         'automatic_retries': 0})
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
