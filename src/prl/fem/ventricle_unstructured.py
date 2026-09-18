"""Single candidate, geometry-first then at most two unchanged 3D FEM states."""
import json
from pathlib import Path
import time
import traceback
import numpy as np
from prl.fem.unstructured_geometry import generate
from prl.fem.ventricle_geometry import geometry_metrics
from prl.verification.mesh_equivalence import compare
from prl.verification.ventricle_3d import load_arrays
from prl.runs.fenicsx_runtime import save_json


def solve_qualified(root, config, started, counters):
    # Import the production kernel only after independent meshing admission.
    from prl.fem.fenicsx_ventricle import VentricularSolid
    from prl.fem.ventricle_protocol import advance_case
    from prl.verification.ventricle_3d import verify
    (root/'raw').mkdir(exist_ok=False)
    solid = None
    try:
        solid = VentricularSolid(config['meshes'][0], config, root)
        solid.tangent_checks()
        def before(spec):
            if time.monotonic()-started > 1680:
                raise TimeoutError('120 second state preservation reserve')
            if counters['attempted_states'] >= 2:
                raise ValueError('Two-state authorization exhausted')
            counters['current_state'] = spec
            counters['attempted_states'] += 1
        def after(spec):
            counters['accepted_states'] += 1
        advance_case(solid, config, {}, before, after)
        report = verify(root)
        save_json(root/'verification.json', report)
        if report['status'] != 'passed':
            raise ValueError('Independent mechanical verification failed')
    except Exception:
        if solid is not None:
            np.savez_compressed(root/'failure_state.npz', mixed_state=solid.w.x.array.copy(),
                u=solid.w.x.array[solid.vmap].reshape(-1, 3), pressure=solid.w.x.array[solid.pmap])
            save_json(root/'failure_history.json', solid.history)
        raise


def execute(root, generator=generate, solver=solve_qualified):
    root = Path(root); started = time.monotonic()
    config = json.loads((root/'configuration.json').read_text())
    counters = {'attempted_states': 0, 'accepted_states': 0, 'current_state': None}
    phase = 'meshing'
    try:
        reference = load_arrays(root/'input/M1_geometry.npz')
        candidate = generator(reference, root, save_json)
        phase = 'geometry_quality'
        report, arrays = compare(reference, candidate)
        save_json(root/'mesh_comparison.json', report)
        np.savez_compressed(root/'mesh_metrics.npz', **arrays)
        if report['status'] != 'passed':
            raise ValueError('Candidate gate rejected: '+str(report['failed_checks']))
        metrics = geometry_metrics(candidate, config, 'U1')
        save_json(root/'input/U1_geometry.json', metrics)
        np.savez_compressed(root/'input/U1_geometry.npz', **candidate)
        if metrics['status'] != 'passed':
            raise ValueError('Production input geometry check failed')
        if time.monotonic()-started > 1680:
            raise TimeoutError('Insufficient time for mechanics; preserve candidate')
        phase = 'mechanics'
        solver(root, config, started, counters)
        result = {'status': 'passed', 'phase': 'completed', 'mesh_gate': 'passed', 'FEM': 'passed'}
    except Exception as error:
        result = {'status': 'failed', 'phase': phase, 'reason': repr(error), 'traceback': traceback.format_exc(),
                  'mesh_gate': 'passed' if phase == 'mechanics' else 'failed',
                  'FEM': 'failed' if counters['attempted_states'] else 'not_run'}
        save_json(root/'failure.json', {**result, **counters, 'automatic_retries': 0})
        traceback.print_exc()
    result.update(counters, elapsed_seconds=time.monotonic()-started, candidate_allowance=1,
                  automatic_retries=0, gpu=0)
    save_json(root/'candidate_execution.json', result)
    return result


if __name__ == '__main__':
    raise SystemExit(0 if execute(Path('/out'))['status'] == 'passed' else 2)
