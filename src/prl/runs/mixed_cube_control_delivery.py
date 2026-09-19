"""Offline control evidence. Never invokes Docker, a solver, or a retry."""
import json
from pathlib import Path
import shutil
import numpy as np
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json
from prl.runs.mixed_cube_delivery import analyze
from prl.verification.positive_j import audit_paths
from prl.verification.saved_segment import resolve_roundtrip
from prl.verification.ventricle_3d import load_arrays


def deliver(workspace, root):
    workspace, root = Path(workspace), Path(root)
    if (root/'delivery_analysis.json').exists() or (root/'manifest.json').exists():
        raise FileExistsError('Create-only offline delivery; no overwrite')
    config = json.loads((root/'configuration.json').read_text())
    if config['schema'] != 'prl.mixed_cube_controls.v1':
        raise ValueError('Only the four registered controls are supported')
    report, _, readback = analyze(root)
    paths = audit_paths(root)
    endpoint = resolve_roundtrip(root,paths)
    if endpoint['status'] != 'passed':
        raise ValueError('Independent path audit failed; retain original evidence')
    references = json.loads((root/'protected_inputs.json').read_text())
    sources = json.loads((root/'source_hashes.json').read_text())
    if not all(digest(path) == expected for path, expected in references['files'].items()):
        raise ValueError('Protected prior evidence drift')
    if not all(digest(root/'sources_at_execution'/path) == expected for path, expected in sources.items()):
        raise ValueError('Execution source snapshot drift')
    report.update(path_audit_status=endpoint['status'],original_path_audit_status=paths['status'],
        endpoint_certificate=endpoint,
        accepted_paths_verified=paths['accepted_steps_checked'],
        guard_candidates=len(paths['candidates']),
        reduced_candidates=sum(item['scale'] < 1 for item in paths['candidates']),
        config=config)
    arrays = {}
    for label, name in [('patch','patch_quadratic_volume'), ('fine','isochoric_k1000_n8')]:
        data = load_arrays(root/'raw'/f'{name}_mesh.npz')
        for key in ['coordinates','boundary_faces','boundary_tags','boundary_owners']:
            arrays[f'{label}_{key}'] = data[key]
        # Preserve all actual accepted states for these two cases, never interpolate time.
        history = report['iterate_diagnostics'][name]
        arrays[f'{label}_iterations'] = np.array([item['iteration'] for item in history])
        for entry in history:
            index = entry['iteration']
            saved = load_arrays(root/'iterates'/name/f'iterate_{index:03d}.npz')
            arrays[f'{label}_u_{index}'] = saved['u']
        terminal = load_arrays(root/'raw'/f'{name}_state.npz')
        lookup = {tuple(np.round(xyz,13)): index for index,xyz in enumerate(data['pressure_coordinates'])}
        faces = data['boundary_faces'][:,:3]
        pressure = np.array([terminal['pressure'][lookup[tuple(np.round(data['coordinates'][node],13))]]
                             for node in faces.ravel()]).reshape(-1,3)
        arrays[f'{label}_terminal_face_pressure'] = pressure.mean(axis=1)
    np.savez_compressed(root/'figure_states.npz', **arrays)
    save_json(root/'delivery_analysis.json', report)
    save_json(root/'delivery_readback.json', readback)
    save_json(root/'path_readback.json', paths)
    save_json(root/'path_endpoint_certificate.json', endpoint)
    target = root/'delivery_sources'
    target.mkdir(exist_ok=False)
    paths_to_copy = [Path(__file__), workspace/'src/prl/runs/mixed_cube_delivery.py',
        workspace/'src/prl/rendering/mixed_cube_controls.py',workspace/'src/prl/verification/positive_j.py',
        workspace/'src/prl/verification/saved_segment.py']
    for source in paths_to_copy:
        shutil.copy2(source,target/source.name)
    save_json(root/'delivery_integrity.json', {
        'status':'passed','protected_files':len(references['files']),
        'preexisting_dirty_files':references['preexisting_dirty_files'],
        'execution_source_snapshots':len(sources),
        'delivery_sources':{p.name:digest(p) for p in target.iterdir()},
        'completed_states_verified':readback['evaluated_states'],
        'accepted_states_verified':sum(len(items) for items in report['iterate_diagnostics'].values()),
        'accepted_paths_verified':paths['accepted_steps_checked'],
        'additional_solves':0,'gpu':0,'automatic_retries':0})
    print(json.dumps({'delivery':'passed','control_gates':report['status'],
        'path_audit_after_endpoint_certificate':endpoint['status'],'original_path_audit':paths['status'],
        'accepted_paths':paths['accepted_steps_checked'],
        'original_ventricular_gate':'failed_unchanged'},indent=2))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    args=parser.parse_args()
    deliver(args.workspace,args.root)
