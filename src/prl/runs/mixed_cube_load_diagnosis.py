"""Create-only offline analysis of the three saved MMS equilibria; no native solver."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
from prl.result_store import result_admission, result_path
from prl.verification.ventricle_3d import load_arrays
from prl.verification.mixed_cube_loads import diagnose

STAGE = 'results/ventricle_fem/mixed_cube_load_diagnosis_v01_20260919'
SOURCE = 'results/ventricle_fem/mixed_cube_benchmark_v03_20260919'
SOURCE_MANIFEST = '084a675f13501added2e056f5bc3cca125a2298f09d290240282fc2b570b77b0'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def run(workspace):
    workspace = Path(workspace).resolve()
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
        if os.environ.get(name) != '1':
            raise ValueError('Single-thread environment required: ' + name)
    target = result_path(workspace, STAGE, new=True)
    source = result_path(workspace, SOURCE)
    admission = result_admission(workspace, planned_new_bytes=16 * 1024 ** 2)
    if not admission['can_start']:
        raise RuntimeError('Offline result storage admission failed')
    if digest(source / 'manifest.json') != SOURCE_MANIFEST:
        raise ValueError('Frozen source manifest drift')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    protected = {str(source / entry['path']): entry['sha256'] for entry in manifest['files']}
    protected[str(source / 'manifest.json')] = SOURCE_MANIFEST
    prior = json.loads((source / 'protected_inputs.json').read_text(encoding='utf-8'))
    protected.update(prior['files'])
    if not all(digest(path) == value for path, value in protected.items()):
        raise ValueError('Protected evidence changed')
    target.mkdir(parents=True, exist_ok=False)
    save(target / 'admission.json', admission)
    save(target / 'sources.json', {'source': str(source), 'protected_sha256': protected,
                                  'scope': 'shared read-only evidence; no raw-array copies'})
    snapshot = target / 'source_code'
    snapshot.mkdir()
    for relative in ['src/prl/verification/mixed_cube_loads.py', 'src/prl/verification/mixed_cube.py',
                     'src/prl/verification/ventricle_3d.py', 'src/prl/runs/mixed_cube_load_diagnosis.py',
                     'tests/prl/test_mixed_cube_loads.py']:
        shutil.copy2(workspace / relative, snapshot / Path(relative).name)
    rows, arrays = [], {}
    started = time.monotonic()
    try:
        for n in [2, 4, 8]:
            if time.monotonic() - started > 300:
                raise TimeoutError('Offline analysis 300-second budget consumed')
            name = f'mms_k100_n{n}'
            case = {'name': name, 'kind': 'mms', 'n': n, 'kappa': 100.}
            data = load_arrays(source / 'raw' / f'{name}_mesh.npz')
            state = load_arrays(source / 'raw' / f'{name}_state.npz')
            row, derived = diagnose(data, state, case)
            row['saved_metrics'] = json.loads((source / 'raw' / f'{name}_audit.json').read_text())['metrics']
            rows.append(row)
            arrays.update({name + '_' + key: value for key, value in derived.items()})
            save(target / f'{name}.json', row)
            print(json.dumps(row), flush=True)
        if not all(digest(path) == value for path, value in protected.items()):
            raise ValueError('Protected evidence changed during analysis')
        np.savez_compressed(target / 'derived.npz', **arrays)
        save(target / 'summary.json', {
            'status': 'passed', 'scientific_qualification': 'failed',
            'scope': 'offline diagnosis completed, not a new equilibrium or scientific qualification',
            'rows': rows, 'protected_files_verified': len(protected),
            'wall_seconds': time.monotonic() - started, 'new_equilibrium_solves': 0,
            'Docker_invocations': 0, 'GPU': 0, 'source_manifest_sha256': SOURCE_MANIFEST})
    except Exception as error:
        save(target / 'failure.json', {'status': 'failed', 'exception': str(error),
                                      'completed_cases': [row['name'] for row in rows]})
        raise
    print(str(target), flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    run(parser.parse_args().workspace)
