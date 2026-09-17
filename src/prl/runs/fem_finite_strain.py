"""Bounded F3-B finite-strain engineering qualification; never a heart fit."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import scipy

from prl.runs.fem_active_ellipse import _manifest, _sha256, _write_json
from prl.storage import evaluate_storage, scan_workspace

RESULT = Path('results/ventricle_fem/f3b_finite_strain_v01_20260917')
CONTRACT = Path('project_control/ventricle_fem_finite_strain_contract_v01.md')
CAP = 96 * 1024**2
RESERVE = 64 * 1024**2
TIMEOUT = 1200


def configuration():
    """The predeclared matrix is not selected from scientific outcomes."""
    nh = {'model': 'neo_hookean', 'mu': 1.0}
    guccione = {'model': 'guccione', 'C': 1.0, 'bff': 8.0, 'bxx': 2.0, 'bfx': 4.0}
    five = np.linspace(0, 1, 5)
    cases = {}

    def add(name, kind, material, mesh, bulk, fiber=(1, 0, 0)):
        phases = np.linspace(0, 1, 9) if kind == 'active' else five
        cases[name] = {
            'kind': kind, 'material': material.copy(), 'fiber': list(fiber),
            'bulk': float(bulk), 'subdivisions': list(mesh),
            'lengths': [4.0 if kind == 'bending' else 2.0, 1.0, 1.0],
            'phases': phases.tolist(),
            'T_values': (1 - np.cos(2*np.pi*phases)).tolist() if kind == 'active' else [0.0]*len(phases),
            'stretch_values': (1+.3*phases).tolist() if kind == 'stretch' else [1.0]*len(phases),
            'traction_values': (.005*phases).tolist() if kind == 'bending' else [0.0]*len(phases),
            'rotation_degrees': (60*phases).tolist() if kind == 'rotation' else [0.0]*len(phases),
            'rotation_center': [0.0, 0.0, 0.0],
        }

    for bulk in (100, 1000):
        for level, mesh in (('coarse', (1, 1, 1)), ('fine', (2, 2, 2))):
            add(f'nh_stretch_{level}_k{bulk}', 'stretch', nh, mesh, bulk)
    for direction, fiber in (('fiber_x', (1, 0, 0)), ('fiber_y', (0, 1, 0))):
        add(f'guccione_stretch_{direction}', 'stretch', guccione, (2, 2, 2), 1000, fiber)
    for bulk in (100, 1000):
        add(f'nh_active_k{bulk}', 'active', nh, (2, 2, 2), bulk)
    add('guccione_active_k1000', 'active', guccione, (2, 2, 2), 1000)
    for bulk in (100, 1000):
        for level, mesh in (('coarse', (2, 1, 1)), ('fine', (4, 2, 2))):
            add(f'nh_bending_{level}_k{bulk}', 'bending', nh, mesh, bulk)
    add('nh_rigid_rotation', 'rotation', nh, (2, 2, 2), 1000)
    return {
        'schema_version': 'prl.finite_strain_configuration.v1', 'cases': cases,
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__,
                    'scipy': scipy.__version__, 'platform': platform.platform()},
        'material_probes': [
            {'name': f'{model["model"]}_T{tension}',
             'material': {**model, 'active_tension': float(tension)}, 'fiber': [1, 0, 0]}
            for model in (nh, guccione) for tension in (0, 2)
        ],
        'scope': '3-D synthetic blocks and beams; NOT a 3-D zebrafish ventricle',
        'units': 'dimensionless length and stress; parameters NOT calibrated',
        'element': 'continuous Q2 displacement / Q1 pressure, 27 Gauss points',
        'active_stress': 'P_act = T F f0 outer f0; prescribed second-Piola fiber tension, not constant Cauchy stress',
        'pressure_convention': 'mixed p is tension-positive volumetric stress; physical pressure = -trace(Cauchy)/3; neither is cavity pressure',
        'resources': {'threads': 1, 'gpu': 0, 'dcm': 0, 'wall_seconds': TIMEOUT,
                      'stage_bytes': CAP, 'reserve_bytes': RESERVE, 'automatic_retries': 0},
        'thresholds': {'kinematics': 1e-10, 'stress_relative': 2e-6,
                       'stress_absolute_zero': 2e-7, 'free_residual': 2e-6,
                       'pressure_weak_residual': 1e-8, 'analytic': 1e-6,
                       'objectivity': 1e-8, 'tangent': 2e-5, 'affine_mesh': 1e-6,
                       'beam_mesh_relative': .05, 'bulk_tip_relative': .05,
                       'homogeneous_volume_change': .01},
    }


def boundary_data(mesh, case, step):
    """Explicit symmetry planes or clamp; non-specified faces are traction-free."""
    xyz = mesh['nodes']
    length = np.asarray(case['lengths'])
    fixed = {}
    kind = case['kind']
    if kind in ('stretch', 'active'):
        for component in range(3):
            for node in np.flatnonzero(np.isclose(xyz[:, component], 0)):
                fixed[3*int(node)+component] = 0.0
        if kind == 'stretch':
            for node in np.flatnonzero(np.isclose(xyz[:, 0], length[0])):
                fixed[3*int(node)] = (case['stretch_values'][step]-1)*length[0]
    elif kind == 'bending':
        for node in np.flatnonzero(np.isclose(xyz[:, 0], 0)):
            for component in range(3):
                fixed[3*int(node)+component] = 0.0
    elif kind == 'rotation':
        angle = np.deg2rad(case['rotation_degrees'][step])
        rot = np.array([[np.cos(angle), -np.sin(angle), 0],
                        [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
        on_boundary = np.any(np.isclose(xyz, 0) | np.isclose(xyz, length), axis=1)
        values = xyz @ rot.T - xyz
        for node in np.flatnonzero(on_boundary):
            for component in range(3):
                fixed[3*int(node)+component] = float(values[node, component])
    else:
        raise ValueError(f'Unregistered boundary case: {kind}')
    force = np.zeros(3*len(xyz))
    if kind == 'bending':
        # Q2 endpoint integrals over a uniform face: Simpson weights assembled
        # over all face elements, not equal force at every mesh node.
        subdivisions = case['subdivisions']
        def weights(count, size):
            values = np.full(2*count+1, 2.0)
            values[1::2] = 4.0
            values[[0, -1]] = 1.0
            return values * size/(6*count)
        wy = weights(subdivisions[1], length[1])
        wz = weights(subdivisions[2], length[2])
        for node in np.flatnonzero(np.isclose(xyz[:, 0], length[0])):
            iy = int(round(xyz[node, 1]*2*subdivisions[1]/length[1]))
            iz = int(round(xyz[node, 2]*2*subdivisions[2]/length[2]))
            force[3*node+1] = case['traction_values'][step]*wy[iy]*wz[iz]
    return fixed, force


def check_budget(root):
    size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if size > CAP:
        raise RuntimeError('F3-B exceeded its 96 MiB stage cap')
    return size


@contextmanager
def scientific_lock(workspace):
    """OS-released lock; retained ordinary file, no deletion or stale-lock bypass."""
    if os.name != 'nt':
        raise RuntimeError('This frozen runner requires its Windows locking implementation')
    import msvcrt
    path = workspace/'project_control'/'fem_scientific_execution.lock'
    with path.open('a+b') as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _protected_manifests(workspace):
    output = {}
    for folder in ('f2_measured_contour_v01_20260917', 'f3a_fixed_mesh_v01_20260917'):
        root = workspace/'results/ventricle_fem'/folder
        path = root/'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        for item in manifest['files']:
            if _sha256(root/item['path']) != item['sha256']:
                raise RuntimeError(f'Protected prior result hash mismatch: {folder}/{item["path"]}')
        output[folder] = {'manifest_sha256': _sha256(path), 'verified_file_count': len(manifest['files'])}
    return output


def worker(workspace):
    from prl.fem.mixed_hex import structured_mesh, solve
    from prl.fem.hyperelastic import material_response
    root = workspace/RESULT
    pre = evaluate_storage(scan_workspace(workspace), planned_new_bytes=CAP, stop_reserve_bytes=RESERVE)
    if not pre['can_start']:
        return {'status': 'blocked', 'reason': 'storage admission', 'storage': pre}
    if not (workspace/CONTRACT).is_file():
        raise FileNotFoundError(CONTRACT)
    with scientific_lock(workspace):
        root.mkdir(parents=True, exist_ok=False)
        (root/'raw').mkdir()
        started = time.perf_counter()
        current_context = {'case': None, 'step': None}
        try:
            _write_json(root/'storage_preflight.json', pre)
            config = configuration()
            _write_json(root/'configuration.json', config)
            sources = [CONTRACT, Path('src/prl/fem/hyperelastic.py'), Path('src/prl/fem/mixed_hex.py'),
                       Path('src/prl/runs/fem_finite_strain.py'), Path('src/prl/verification/fem_finite_strain.py'),
                       Path('src/prl/rendering/fem_finite_strain.py'), Path('src/prl/storage.py')]
            _write_json(root/'source_hashes.json', {p.as_posix(): _sha256(workspace/p) for p in sources})
            protected = _protected_manifests(workspace)
            _write_json(root/'protected_evidence_preflight.json', protected)
            angle = np.pi/3
            rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                                 [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
            base_gradient = np.array([[1.12, .09, .02], [.03, .93, .04], [.02, -.01, 1.05]])
            gradients = np.array([np.eye(3), rotation, base_gradient, rotation@base_gradient])
            probe_responses = [material_response(gradients, item['material'], item['fiber'])
                               for item in config['material_probes']]
            np.savez_compressed(root/'raw'/'material_points.npz',
                                F=np.repeat(gradients[None], len(probe_responses), axis=0),
                                **{key: np.array([item[key] for item in probe_responses])
                                   for key in ('energy', 'P', 'tangent', 'J')})
            for name, case in config['cases'].items():
                mesh = structured_mesh(tuple(case['subdivisions']), lengths=tuple(case['lengths']))
                records, histories = [], []
                initial = None
                for step, phase in enumerate(case['phases']):
                    current_context = {'case': name, 'step': step, 'phase': phase, 'case_configuration': case}
                    if time.perf_counter()-started > TIMEOUT-60:
                        raise TimeoutError('F3-B compute budget exhausted; preserving written states')
                    fixed, force = boundary_data(mesh, case, step)
                    material = {**case['material'], 'fiber': case['fiber']}
                    print(f'{name}: state {step+1}/{len(case["phases"])}', flush=True)
                    solved = solve(mesh, material, case['bulk'], active_tension=case['T_values'][step], dirichlet=fixed,
                                   external_forces=force,
                                   initial=initial, tolerance=1e-9, max_iterations=30)
                    initial = solved['vector']
                    dofs = np.asarray(sorted(fixed), dtype=np.int64)
                    records.append({
                        'displacements': solved['u'], 'pressure_dofs': solved['p'],
                        'fixed_values': np.array([fixed[int(d)] for d in dofs]),
                        'external_forces': force, 'reaction': solved['residual'][:3*len(mesh['nodes'])],
                        'newton_residual': solved['normalized_free_residual'],
                        **{key: solved[key] for key in ('F', 'P', 'Green', 'J')},
                        'Cauchy': solved['cauchy_stress'], 'energy': solved['energy_density'],
                    })
                    histories.append(solved['history'])
                    count = len(records)
                    payload = {key: np.asarray([row[key] for row in records]) for key in records[0]}
                    payload.update(coordinates=mesh['nodes'], cells=mesh['elements'],
                                   pressure_coordinates=mesh['pressure_nodes'], pressure_cells=mesh['pressure_elements'],
                                   phases=np.asarray(case['phases'][:count]), activation=np.asarray(case['T_values'][:count]),
                                   prescribed_stretch=np.asarray(case['stretch_values'][:count]), fixed_dofs=dofs)
                    # Atomic same-filesystem checkpoint replacement: a write
                    # error leaves the preceding complete checkpoint intact.
                    checkpoint = root/'raw'/f'{name}.npz'
                    pending = root/'raw'/f'{name}.pending.npz'
                    maximum_pending_bytes = sum(value.nbytes for value in payload.values()) + 8192*len(payload)
                    if check_budget(root) + maximum_pending_bytes > CAP:
                        raise RuntimeError('F3-B cannot preserve an atomic checkpoint within its stage cap')
                    np.savez_compressed(pending, **payload)
                    os.replace(pending, checkpoint)
                    _write_json(root/'raw'/f'{name}_newton.json', histories)
                    _write_json(root/'progress.json', {'status': 'unknown', 'case': name, 'completed_states': count,
                                                       'elapsed_s': time.perf_counter()-started})
                    check_budget(root)
            from prl.verification.fem_finite_strain import verify_fem_finite_strain
            verification = verify_fem_finite_strain(root, save=True)
            if _protected_manifests(workspace) != protected:
                raise RuntimeError('Protected prior evidence changed')
            _write_json(root/'protected_evidence_postflight.json', protected)
            _write_json(root/'summary.json', {'status': verification['status'], 'cases': verification.get('cases', {}),
                                             'scope': config['scope'], 'biological_validation': 'not_run'})
            from prl.rendering.fem_finite_strain import render_fem_finite_strain
            rendering = render_fem_finite_strain(root)
            post = evaluate_storage(scan_workspace(workspace), planned_new_bytes=0, stop_reserve_bytes=RESERVE)
            _write_json(root/'storage_postflight.json', post)
            report = {'status': verification['status'] if post['can_start'] and rendering['status']=='passed' else 'failed',
                      'solver_completed': True, 'rendering': rendering['status'], 'elapsed_s': time.perf_counter()-started,
                      'scientific_invocations': 1, 'automatic_retries': 0, 'threads': 1, 'gpu': 0, 'dcm': 0,
                      'biological_validation': 'not_run', 'stage_bytes_before_manifest': check_budget(root)}
            _write_json(root/'execution.json', report)
            _write_json(root/'progress.json', report)
            _write_json(root/'manifest.json', _manifest(root))
            check_budget(root)
            return report
        except Exception as exc:
            failure = {'status': 'failed', 'reason': repr(exc), 'elapsed_s': time.perf_counter()-started,
                       'retained_states': 'all fully written raw states retained', 'automatic_retries': 0,
                       'context': current_context}
            if hasattr(exc, 'last_state'):
                dofs = np.array(sorted(fixed), dtype=np.int64)
                retained = {key: value for key, value in exc.last_state.items()
                            if isinstance(value, np.ndarray)}
                np.savez_compressed(root/'last_newton_state.npz', **retained,
                                    coordinates=mesh['nodes'], cells=mesh['elements'],
                                    pressure_coordinates=mesh['pressure_nodes'], pressure_cells=mesh['pressure_elements'],
                                    prescribed_dofs=dofs, prescribed_values=np.array([fixed[int(d)] for d in dofs]),
                                    prescribed_forces=force)
                _write_json(root/'last_newton_history.json', exc.last_state.get('history', []))
            _write_json(root/'failure.json', failure)
            _write_json(root/'progress.json', failure)
            _write_json(root/'manifest.json', _manifest(root))
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.worker:
        if os.environ.get('PRL_FINITE_STRAIN_CONTROLLER') != '1':
            raise RuntimeError('Worker must be launched by the bounded controller')
        result = worker(workspace)
        print(json.dumps(result, indent=2))
        return 0 if result['status']=='passed' else 1
    env = os.environ.copy()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env[name] = '1'
    env['PYTHONPATH'] = str(workspace/'src')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['MPLCONFIGDIR'] = str(workspace/RESULT/'runtime_cache')
    env['PRL_FINITE_STRAIN_CONTROLLER'] = '1'
    try:
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'prl.runs.fem_finite_strain',
                               '--workspace', str(workspace), '--worker'], cwd=workspace, env=env,
                              timeout=TIMEOUT, check=False).returncode
    except subprocess.TimeoutExpired:
        if (workspace/RESULT).is_dir():
            _write_json(workspace/RESULT/'timeout.json', {'status':'failed', 'reason':'1200 second cap', 'automatic_retries':0})
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
