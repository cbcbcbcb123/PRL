"""Offline replay of a pre-solve export failure, not a new scientific run."""
import json
from pathlib import Path
import shutil
import numpy as np

from prl.fem.nodal_export import canonical_nodal_cells
from prl.fem.mixed_cube_representation_spec import topology_dof_inventory
from prl.verification.mixed_cube_space import mapping_checks
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json


def diagnose(workspace, root):
    workspace, root = Path(workspace), Path(root)
    if (root/'export_diagnosis.json').exists():
        raise FileExistsError('Create-only diagnostic; original failure remains immutable')
    summary = json.loads((root/'summary.json').read_text())
    if summary['attempted_solves'] != 0 or summary['cases']:
        raise ValueError('This diagnostic supports only the retained pre-solve failure')
    original_files = {str(p.relative_to(root)): digest(p) for p in root.rglob('*') if p.is_file()}
    protected = json.loads((root/'protected_inputs.json').read_text())
    sources = json.loads((root/'source_hashes.json').read_text())
    assert all(digest(p) == value for p, value in protected['files'].items())
    assert all(digest(root/'sources_at_execution'/p) == value for p, value in sources.items())
    source = root/'raw/patch_cubic_volume_p3p2_mesh.npz'
    with np.load(source, allow_pickle=False) as saved:
        data = dict(saved)
    before = mapping_checks(data)
    cells, slots = canonical_nodal_cells(data['coordinates'], data['cells'], data['u_reference_nodes'])
    corrected = dict(data, cells=cells, native_cells=data['cells'], u_canonical_to_native_slots=slots)
    after = mapping_checks(corrected)
    nodes = data['u_reference_nodes']
    expected = np.einsum('qa,cai->cqi', np.column_stack((1-nodes.sum(axis=1), nodes)),
                         data['coordinates'][data['cells'][:, :4]])
    mismatch_before = np.max(np.abs(expected-data['coordinates'][data['cells']]), axis=(1, 2))
    mismatch_after = np.max(np.abs(expected-data['coordinates'][cells]), axis=(1, 2))
    config = json.loads((root/'configuration.json').read_text())
    cost = []
    for case in config['cases']:
        pair = f'p{case["u_degree"]}p{case["p_degree"]}'
        cost.append(dict(name=case['name'], n=case['n'], space=pair,
            expected_dofs=topology_dof_inventory(case['n'])['mixed_dofs'][pair],
            solve_status='not_run', error=None, solve_seconds=None, peak_rss_bytes=None))
    report = {
        'schema': 'prl.mixed_cube_export_diagnosis.v1', 'status': 'passed',
        'scope': 'coordinate-order diagnostic and offline fix only; not equilibrium qualification',
        'batch_status': 'failed', 'native_fixed_interface_status': 'not_run',
        'container_invocations': 1, 'equilibrium_solves': 0, 'automatic_retries': 0, 'gpu': 0,
        'execution_seconds': json.loads((root/'execution.json').read_text())['elapsed_seconds'],
        'source_mesh': str(source), 'source_mesh_sha256': digest(source),
        'tetrahedra': len(cells), 'affected_cells': int(np.count_nonzero(mismatch_before > 1e-12)),
        'changed_local_slots': int(np.count_nonzero(slots != np.arange(slots.shape[1]))),
        'maximum_coordinate_mismatch_before': float(mismatch_before.max()),
        'maximum_coordinate_mismatch_after': float(mismatch_after.max()),
        'mapping_before': before, 'mapping_after': after, 'cases': cost,
        'frozen_execution_sources': len(sources), 'protected_files': len(protected['files']),
        'preexisting_dirty_files': protected['preexisting_dirty_files'],
        'original_files': original_files,
        'known_post_execution_source_changes': [p for p, value in sources.items() if digest(workspace/p) != value],
        'original_ventricular_gate': 'failed', 'pressure_contribution': 'unknown',
        'biological_validation': 'not_run',
    }
    if not all(after.values()):
        raise ValueError('Offline map correction did not satisfy unchanged independent mapping gate')
    np.savez_compressed(root/'export_diagnostic_arrays.npz',
        coordinates=data['coordinates'], boundary_faces=data['boundary_faces'],
        boundary_tags=data['boundary_tags'], cell_index=np.arange(len(cells)),
        mismatch_before=mismatch_before, mismatch_after=mismatch_after,
        native_cells=data['cells'], canonical_cells=cells, canonical_to_native_slots=slots)
    target = root/'offline_fix_sources'; target.mkdir(exist_ok=False)
    paths = ['src/prl/fem/nodal_export.py', 'src/prl/fem/fenicsx_mixed_cube.py',
        'src/prl/verification/mixed_cube_space.py','src/prl/runs/mixed_cube_export_diagnosis.py',
        'src/prl/rendering/mixed_cube_export.py','tests/prl/test_nodal_export.py']
    for path in paths:
        destination = target/path; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace/path, destination)
    report['offline_fix_source_hashes'] = {p: digest(workspace/p) for p in paths}
    assert all(digest(root/p) == value for p, value in original_files.items())
    save_json(root/'export_diagnosis.json', report)
    print(json.dumps({key:report[key] for key in ['status','batch_status','affected_cells',
        'maximum_coordinate_mismatch_before','maximum_coordinate_mismatch_after',
        'native_fixed_interface_status']}, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    args = parser.parse_args(); diagnose(args.workspace, args.root)
