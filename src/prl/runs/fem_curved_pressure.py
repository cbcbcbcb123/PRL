"""Bounded curved Q2/Q1 wall and current-surface pressure qualification."""

from __future__ import annotations

import argparse
from itertools import product
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time

import numpy as np
import scipy

from prl.runs.fem_active_ellipse import _manifest, _sha256, _write_json
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fem_rotation import mesh_payload, state_payload, package_bytes
from prl.storage import evaluate_storage, scan_workspace

RESULT = Path('results/ventricle_fem/f4_curved_pressure_v01_20260917')
CONTRACT = Path('project_control/ventricle_fem_curved_pressure_contract_v01.md')
CAP, RESERVE, TIMEOUT = 32 * 1024**2, 64 * 1024**2, 600
PARENTS = {
    'f3b_finite_strain_v01_20260917': ('76167e61c4cdaf38011f6cd11ab4f329fa4d4439d9f3bf5a40dfc213acd79dc3', 62),
    'f3c_rotation_repair_v01_20260917': ('705f478f81818e5cc26de499a21ca8596372e816a8b773330293f070373ebf73', 38),
}


def configuration():
    return {
        'schema_version': 'prl.fem_curved_pressure_configuration.v1',
        'cases': [{'name': 'coarse', 'counts': [2, 4, 1]}, {'name': 'fine', 'counts': [3, 8, 1]}],
        'geometry': {'inner_radius': 1.0, 'outer_radius': 1.25, 'angle': np.pi / 2, 'height': .5},
        'material': {'model': 'neo_hookean', 'mu': 1.0}, 'kappa': 1000.0,
        'loads': [0.0, .02, .04, .06, .08],
        'scope': 'quarter-cylinder plane-strain curved pressure qualification',
        'constraints': 'theta=0:uy=0; theta=pi/2:ux=0; every node:uz=0; no other fixed DOFs',
        'element': 'Q2 isoparametric displacement / continuous Q1 pressure; 3^3 volume and 3^2 surface Gauss',
        'units': 'dimensionless engineering length and stress; load steps are NOT physiological time',
        'saved_energy': 'internal isochoric material energy density; not a total potential including follower-pressure work',
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
        'resources': {'threads': 1, 'gpu': 0, 'dcm': 0, 'seconds': TIMEOUT,
                      'stage_bytes': CAP, 'reserve_bytes': RESERVE, 'automatic_retries': 0},
    }


def curved_mesh(case, geometry):
    """A curved reference mesh, not an imposed displacement of a flat wall."""
    from prl.fem.mixed_hex import structured_mesh
    counts = tuple(case['counts'])
    width = geometry['outer_radius'] - geometry['inner_radius']
    mesh = structured_mesh(counts, (width, geometry['angle'], geometry['height']))
    parameter_nodes = mesh['nodes'].copy()
    for key in ('nodes', 'pressure_nodes'):
        radius = geometry['inner_radius'] + mesh[key][:, 0]
        angle = mesh[key][:, 1]
        mesh[key] = np.column_stack((radius * np.cos(angle), radius * np.sin(angle), mesh[key][:, 2]))
    mesh['geometry_mapping'] = 'isoparametric'
    fixed = {3 * node + 2: 0.0 for node in range(len(parameter_nodes))}
    for node, values in enumerate(parameter_nodes):
        if values[1] == 0.0:
            fixed[3 * node + 1] = 0.0
        if values[1] == geometry['angle']:
            fixed[3 * node] = 0.0
    faces = np.array([(np.ravel_multi_index((0, j, k), counts), 0, -1)
                      for j, k in product(range(counts[1]), range(counts[2]))], dtype=np.int64)
    return mesh, fixed, faces


def protected_evidence(workspace):
    reports = {}
    for name, (expected_hash, expected_count) in PARENTS.items():
        root = workspace / 'results/ventricle_fem' / name
        manifest = root / 'manifest.json'
        if _sha256(manifest) != expected_hash:
            raise ValueError(f'Protected manifest changed: {name}')
        items = json.loads(manifest.read_text(encoding='utf-8'))['files']
        if len(items) != expected_count:
            raise ValueError(f'Protected inventory changed: {name}')
        for item in items:
            path = root / item['path']
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Protected path escapes package')
            chain = [path, *[p for p in path.parents if p == root or p.is_relative_to(root)]]
            if any(p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) &
                   getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024) for p in chain):
                raise ValueError('Protected reparse path')
            if path.stat().st_size != item['bytes'] or _sha256(path) != item['sha256']:
                raise ValueError(f'Protected evidence changed: {name}/{item["path"]}')
        reports[name] = {'status': 'passed', 'manifest_sha256': expected_hash, 'verified_files': len(items)}
    return reports


def checkpoint(root, name, payload):
    maximum = sum(np.asarray(v).nbytes for v in payload.values()) + 8192 * len(payload)
    if package_bytes(root) + maximum + 65536 > CAP:
        raise RuntimeError('Curved-pressure checkpoint exceeds stage budget')
    destination = root / 'raw' / f'{name}.npz'
    pending = destination.with_suffix('.pending.npz')
    np.savez_compressed(pending, **payload)
    os.replace(pending, destination)


def worker(workspace):
    from prl.fem.mixed_hex import solve
    from prl.fem.follower_pressure import assemble_pressure
    root = workspace / RESULT
    pre = evaluate_storage(scan_workspace(workspace), planned_new_bytes=CAP, stop_reserve_bytes=RESERVE)
    if not pre['can_start']:
        return {'status': 'blocked', 'reason': 'storage admission', 'storage': pre}
    if not (workspace / CONTRACT).is_file():
        raise FileNotFoundError(CONTRACT)
    protected = protected_evidence(workspace)
    with scientific_lock(workspace):
        root.mkdir(parents=True, exist_ok=False)
        (root / 'raw').mkdir()
        started = time.perf_counter()
        attempts, completed = 0, 0
        context, initial, mesh_data = {}, None, {}
        try:
            config = configuration()
            _write_json(root / 'configuration.json', config)
            _write_json(root / 'storage_preflight.json', pre)
            _write_json(root / 'protected_evidence_preflight.json', protected)
            sources = [CONTRACT, *map(Path, ['src/prl/fem/mixed_hex.py', 'src/prl/fem/follower_pressure.py',
                'src/prl/fem/hyperelastic.py', 'src/prl/runs/fem_curved_pressure.py',
                'src/prl/runs/fem_rotation.py', 'src/prl/runs/fem_finite_strain.py',
                'src/prl/runs/fem_active_ellipse.py', 'src/prl/verification/fem_curved_pressure.py',
                'src/prl/verification/fem_finite_strain.py', 'src/prl/rendering/fem_curved_pressure.py',
                'src/prl/rendering/fem_measured_contour.py', 'src/prl/rendering/fem_finite_strain.py',
                'src/prl/rendering/fem_rotation.py', 'src/prl/rendering/cb_plot_unified_style.py',
                'src/prl/cli.py', 'src/prl/storage.py'])]
            _write_json(root / 'source_hashes.json', {p.as_posix(): _sha256(workspace / p) for p in sources})
            for case in config['cases']:
                mesh, fixed, faces = curved_mesh(case, config['geometry'])
                mesh_data = {**mesh_payload(mesh), 'fixed_dofs': np.array(sorted(fixed)), 'inner_faces': faces}
                records, histories = [], []
                initial = np.zeros(3 * len(mesh['nodes']) + len(mesh['pressure_nodes']))
                for step, pressure in enumerate(config['loads']):
                    context = {'case': case['name'], 'step': step, 'pressure': pressure}
                    if time.perf_counter() - started > TIMEOUT - 60:
                        raise TimeoutError('Curved-pressure compute deadline reached')
                    checkpoint(root, 'current_initial', {**mesh_data, 'vector': initial, 'load': pressure})
                    _write_json(root / 'progress.json', {'status': 'unknown', 'context': context,
                                                        'attempts': attempts, 'completed_states': completed})
                    print(f'{case["name"]}: pressure {pressure}, state {step+1}/5', flush=True)
                    attempts += 1
                    solved = solve(mesh, config['material'], config['kappa'], dirichlet=fixed, initial=initial,
                                   follower_pressure={'faces': faces, 'pressure': pressure},
                                   tolerance=1e-9, max_iterations=30, max_line_search=16)
                    force = assemble_pressure(mesh, solved['u'], faces, pressure, with_tangent=False)['force']
                    records.append({**state_payload(solved, fixed, force), 'initial_vectors': initial.copy()})
                    histories.append(solved['history'])
                    initial = solved['vector'].copy()
                    payload = {key: np.asarray([row[key] for row in records]) for key in records[0]}
                    checkpoint(root, case['name'], {**mesh_data, **payload, 'loads': np.asarray(config['loads'][:len(records)])})
                    _write_json(root / 'raw' / f'{case["name"]}_newton.json', histories)
                    completed += 1
            _write_json(root / 'solver_execution.json', {'status': 'passed', 'new_solves': attempts,
                        'completed_states': completed, 'scientific_invocations': 1, 'automatic_retries': 0,
                        'elapsed_seconds': time.perf_counter() - started})
            after = protected_evidence(workspace)
            if after != protected:
                raise ValueError('Protected evidence drifted')
            _write_json(root / 'protected_evidence_postflight.json', after)
            from prl.verification.fem_curved_pressure import verify_fem_curved_pressure
            verification = verify_fem_curved_pressure(root, save=True)
            from prl.rendering.fem_curved_pressure import render_fem_curved_pressure
            rendering = render_fem_curved_pressure(root)
            post = evaluate_storage(scan_workspace(workspace), planned_new_bytes=65536, stop_reserve_bytes=RESERVE)
            _write_json(root / 'storage_postflight.json', post)
            if package_bytes(root) + 65536 > CAP:
                raise RuntimeError('Final package lacks control-record headroom')
            report = {'status': verification['status'] if rendering['status'] == 'passed' and post['can_start'] else 'failed',
                      'scientific_qualification': verification['status'], 'rendering': rendering['status'],
                      'new_solves': attempts, 'completed_states': completed, 'scientific_invocations': 1,
                      'automatic_retries': 0, 'threads': 1, 'gpu': 0, 'dcm': 0,
                      'biological_validation': 'not_run', 'scope': config['scope'],
                      'elapsed_seconds': time.perf_counter() - started}
            _write_json(root / 'execution.json', report)
            _write_json(root / 'progress.json', report)
            _write_json(root / 'manifest.json', _manifest(root))
            return report
        except Exception as error:
            failure = {'status': 'failed', 'reason': repr(error), 'context': context, 'solve_attempts': attempts,
                       'completed_states': completed, 'automatic_retries': 0,
                       'elapsed_seconds': time.perf_counter() - started}
            if initial is not None:
                retained = {**mesh_data, 'attempted_initial_vector': initial}
                if hasattr(error, 'last_state'):
                    retained.update({key: value for key, value in error.last_state.items() if isinstance(value, np.ndarray)})
                try:
                    checkpoint(root, 'failure_state', retained)
                    if hasattr(error, 'last_state'):
                        _write_json(root / 'last_iteration_history.json', error.last_state.get('history', []))
                except (OSError, RuntimeError) as retention_error:
                    failure['failure_state_write_error'] = repr(retention_error)
                    failure['retained_evidence'] = 'last fully written atomic checkpoints, no deletion/retry'
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
        if os.environ.get('PRL_CURVED_PRESSURE_CONTROLLER') != '1':
            raise RuntimeError('Use the bounded curved-pressure controller')
        result = worker(workspace)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'passed' else 1
    env = os.environ.copy()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env[name] = '1'
    env.update(PYTHONPATH=str(workspace / 'src'), PYTHONDONTWRITEBYTECODE='1',
               MPLCONFIGDIR=str(workspace / RESULT / 'runtime_cache'), PRL_CURVED_PRESSURE_CONTROLLER='1')
    try:
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'prl.runs.fem_curved_pressure',
                               '--workspace', str(workspace), '--worker'], cwd=workspace, env=env,
                              timeout=TIMEOUT, check=False).returncode
    except subprocess.TimeoutExpired:
        if (workspace / RESULT).is_dir():
            _write_json(workspace / RESULT / 'timeout.json', {'status': 'failed', 'reason': '600 second cap',
                        'automatic_retries': 0, 'retained_evidence': 'last fully written atomic checkpoints'})
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
