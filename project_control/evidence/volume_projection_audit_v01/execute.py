"""Expert-source intake and one create-only saved-state audit; no FEM or mesher."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
PLAN = REPO / 'plan/active/EXP-20260918-FEM-review-v01'
EXPERT = Path(r'C:\Users\chenb\Desktop\PRL_独立评审与复核材料_20260918.zip')
EXPERT_SHA = '2759373b5b7409b4d6538394fcac176faf9a11820023638dc935423ff878a1d9'
OPINION = Path(r'C:\Users\chenb\Desktop\PRL_项目评审与提速建议_20260918.md')
OPINION_SHA = '759125257ea9cbbf7afdcc4a68cd46b3ddfff710855058e682710c197dd476df'
RESULT_ID = Path('results/ventricle_fem/volume_projection_audit_v01_20260918')
PARENT_ID = Path('results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
PARENT_MANIFEST_SHA = '7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def intake():
    if digest(EXPERT) != EXPERT_SHA or digest(OPINION) != OPINION_SHA:
        raise ValueError('Expert source differs from the received frozen identity')
    target = PLAN / 'source'
    if target.exists():
        raise FileExistsError('Expert intake is create-only')
    with zipfile.ZipFile(EXPERT) as archive:
        expected = {'PRL_项目评审与提速建议_20260918.md', 'PRL_review_evidence.md',
            'PRL_review_audit_20260918.json', 'prl_independent_audit.py',
            'PRL_review_shape_tests.txt', 'PRL_review_shape_tests.xml', 'PRL_review_README.md', 'REVIEW_MANIFEST.json'}
        if len(archive.infolist()) != len(expected) or set(archive.namelist()) != expected or archive.testzip():
            raise ValueError('Unexpected expert archive members or CRC failure')
        manifest = json.loads(archive.read('REVIEW_MANIFEST.json'))
        if {r['path'] for r in manifest['files']} != expected - {'REVIEW_MANIFEST.json'}:
            raise ValueError('Incomplete expert archive manifest')
        for member in archive.infolist():
            if member.file_size > 1024**2 or stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError('Nonregular/oversized expert member')
        for entry in manifest['files']:
            content = archive.read(entry['path'])
            if len(content) != entry['bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Expert member hash mismatch: ' + entry['path'])
        if hashlib.sha256(archive.read(OPINION.name)).hexdigest() != OPINION_SHA:
            raise ValueError('Standalone and archived opinions differ')
        target.mkdir()
        shutil.copy2(EXPERT, target / EXPERT.name)
        for name in sorted(expected):
            with (target / name).open('xb') as handle:
                handle.write(archive.read(name))
    files = [{'path': p.relative_to(PLAN).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
             for p in sorted(target.iterdir())]
    save(PLAN / 'source_manifest.json', {'status': 'passed', 'reviewer_identity': 'unknown',
        'original_zip': str(EXPERT), 'original_markdown': str(OPINION), 'files': files,
        'archive_crc': 'passed', 'archive_manifest': 'passed', 'opinions_identical': True,
        'source_modified': False, 'expert_script_executed_during_intake': False})
    print(json.dumps({'intake': 'passed', 'files': len(files), 'root': str(PLAN)}, ensure_ascii=False))


def analyze():
    import numpy as np
    from prl.result_store import result_path, result_admission
    mechanics = load_module('volume_audit_mechanics', REPO / 'src/prl/verification/ventricle_3d.py')
    metrics = load_module('volume_audit_metrics', REPO / 'src/prl/verification/volume_projection.py')
    source = result_path(REPO, PARENT_ID)
    if digest(source / 'manifest.json') != PARENT_MANIFEST_SHA:
        raise ValueError('Original D1 manifest changed')
    parent = read(source / 'manifest.json')
    for entry in parent['files']:
        if digest(source / entry['path']) != entry['sha256']:
            raise ValueError('Original D1 evidence drift: ' + entry['path'])
    for entry in read(PLAN / 'source_manifest.json')['files']:
        if digest(PLAN / entry['path']) != entry['sha256']:
            raise ValueError('Expert input drift')
    root = result_path(REPO, RESULT_ID, new=True)
    budget = result_admission(REPO, 32*1024**2)
    if not budget['can_start']:
        raise RuntimeError('Storage admission blocked')
    root.mkdir()
    save(root / 'storage_admission.json', budget)
    config = read(source / 'configuration.json')
    save(root / 'configuration.json', {'analysis': 'saved_state_volume_projection', 'new_FEM_solves': 0,
        'source_stage': str(source), 'source_manifest_sha256': PARENT_MANIFEST_SHA,
        'fixed_distance_edges': [.15,.30,.45], 'base_distance_coordinate': '-Z/L in reference coordinates',
        'scientific_pressure_gate': .01, 'config_original': config,
        'figure_profile': 'exploratory single page, 160dpi PNG + editable SVG; not publication final'})
    # Retain small source snapshots only; no duplicate large original states.
    snapshot = root / 'sources'
    snapshot.mkdir()
    copy_sources = {'mechanics.py': REPO / 'src/prl/verification/ventricle_3d.py',
        'metrics.py': REPO / 'src/prl/verification/volume_projection.py',
        'geometry_view.py': REPO / 'src/prl/rendering/ventricle_3d.py',
        'draw.py': REPO / 'src/prl/rendering/volume_projection.py',
        'style.py': Path(r'C:\Users\chenb\.codex\skills\cb-plot-unified-style\assets\cb_plot_unified_style.py')}
    identities = [{'path': str(source / 'manifest.json'), 'sha256': PARENT_MANIFEST_SHA}]
    for name, path in copy_sources.items():
        shutil.copy2(path, snapshot / name)
        identities.append({'path': str(path), 'sha256': digest(path), 'copied_to': 'sources/' + name})
    expert = read(PLAN / 'source/PRL_review_audit_20260918.json')
    reports, derived, checks = {}, {}, {}
    compared = ['max_abs_p_over_kappa_at_q_and_extra','rms_projection_defect','max_abs_projection_defect',
        'rms_J_minus_one','rms_p_over_kappa','fraction_solid_volume_in_bad_cells','bad_cells','solid_reference_volume']
    for name, directory in [('M0','retained'),('M1','raw')]:
        files = [source / directory / (name + suffix) for suffix in ['_mesh.npz','_state_pressure_1.npz','_state_pressure_1.json']]
        identities.extend({'path': str(p), 'sha256': digest(p), 'retention': 'original immutable shared evidence'} for p in files)
        mesh, state, metadata = mechanics.load_arrays(files[0]), mechanics.load_arrays(files[1]), read(files[2])
        original = mechanics.state_audit(mesh,state,metadata,config)
        if original['status'] != 'failed' or original['failed_checks'] != ['local_volume']:
            raise ValueError('Original verdict not reproduced')
        result, arrays = metrics.analyze(mesh,state,config,mechanics)
        report = {'original_gate': original, 'projection': result}
        delta = {key: abs(result[key]-expert['states'][name]['additional_diagnostics'][key]) for key in compared}
        checks[name + '_expert_metrics_match'] = all(value < 1e-12 for value in delta.values())
        checks[name + '_projection_orthogonal'] = result['pressure_weak_moment_norm'] < 1e-12 and abs(result['projection_cross_term']) < 1e-16
        checks[name + '_energy_identity'] = abs(result['exact_split_identity_error']) < 1e-12
        report['expert_comparison_absolute_difference'] = delta
        reports[name] = report
        derived.update({name + '_' + key: value for key,value in arrays.items()})
    save(root / 'input_identities.json', {'files': identities, 'parent_manifest_all_files_checked': len(parent['files'])})
    summary = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
        'scientific_pressure_gate': 'failed', 'causal_root': 'unknown', 'new_FEM_solves': 0,
        'states': reports, 'artifact_scope': 'one offline diagnostic page, not a publication figure package'}
    save(root / 'summary.json', summary)
    np.savez_compressed(root / 'derived_cells.npz', **derived)
    if not all(checks.values()):
        raise RuntimeError('Offline diagnostics did not reproduce the evidence; stop before figures')
    os.environ['MPLCONFIGDIR'] = str(root / '.plot_cache')
    renderer = load_module('projection_renderer', snapshot / 'draw.py')
    style = load_module('projection_style', snapshot / 'style.py')
    geometry = load_module('projection_geometry', snapshot / 'geometry_view.py')
    renderer.draw(root,style,geometry)
    for identity in identities:
        if digest(Path(identity['path'])) != identity['sha256']:
            raise ValueError('Source changed after analysis')
    save(root / 'source_postcheck.json', {'status':'passed','checked':len(identities),'originals_modified':False})
    print(json.dumps({'status':summary['status'], 'root':str(root),
        'scientific_pressure_gate':'failed', 'new_FEM_solves':0,
        'states': {name:{'rms': item['projection']['rms_projection_defect'],
            'fixed_far_max_J':item['projection']['regions']['all/distance_ge_0p30']['max_abs_J_minus_one'],
            'peak':item['projection']['peak']} for name,item in reports.items()}}, ensure_ascii=False,indent=2))


def check():
    """Read-only replay with retained independent sources; no plotting or FEM."""
    import numpy as np
    from prl.result_store import result_path
    root = result_path(REPO, RESULT_ID)
    source = result_path(REPO, PARENT_ID)
    if digest(source / 'manifest.json') != PARENT_MANIFEST_SHA:
        raise ValueError('Original evidence manifest drift')
    parent_files = read(source / 'manifest.json')['files']
    for entry in parent_files:
        if digest(source / entry['path']) != entry['sha256']:
            raise ValueError('Original evidence drift: ' + entry['path'])
    expert_files = read(PLAN / 'source_manifest.json')['files']
    for entry in expert_files:
        if digest(PLAN / entry['path']) != entry['sha256']:
            raise ValueError('Expert input drift')
    for entry in read(root / 'input_identities.json')['files']:
        if digest(entry['path']) != entry['sha256']:
            raise ValueError('Analysis source drift: ' + entry['path'])
        if 'copied_to' in entry and digest(root / entry['copied_to']) != entry['sha256']:
            raise ValueError('Snapshot drift: ' + entry['copied_to'])
    mechanics = load_module('retained_projection_mechanics', root / 'sources/mechanics.py')
    metrics = load_module('retained_projection_metrics', root / 'sources/metrics.py')
    config = read(root / 'configuration.json')
    summary = read(root / 'summary.json')
    with np.load(root / 'derived_cells.npz', allow_pickle=False) as retained:
        for name, directory in [('M0', 'retained'), ('M1', 'raw')]:
            mesh = mechanics.load_arrays(source / directory / (name + '_mesh.npz'))
            state = mechanics.load_arrays(source / directory / (name + '_state_pressure_1.npz'))
            result, arrays = metrics.analyze(mesh, state, config['config_original'], mechanics,
                                             edges=config['fixed_distance_edges'])
            if result != summary['states'][name]['projection']:
                raise ValueError('Diagnostic JSON replay differs: ' + name)
            for key, value in arrays.items():
                np.testing.assert_array_equal(value, retained[name + '_' + key])
    return {'status': 'passed', 'parent_files_hash_checked': len(parent_files),
        'expert_files_hash_checked': len(expert_files), 'diagnostics_replay': 'exact',
        'derived_arrays_replay': 'exact', 'new_FEM_solves': 0}


def finalize():
    """Freeze this completed offline delivery only; never rerun a solver."""
    import platform
    import numpy as np
    from PIL import Image
    from prl.result_store import result_path, register_result
    root = result_path(REPO, RESULT_ID)
    if (root / 'manifest.json').exists() or (root / 'delivery_audit.json').exists():
        raise FileExistsError('Delivery freeze is create-only')
    replay = check()
    environment = dict(os.environ, PYTHONPATH=str(REPO / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                       OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    command = [sys.executable, '-B', '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               'tests/prl/test_volume_projection.py', 'tests/prl/test_tetra_quality.py']
    tests = subprocess.run(command, cwd=REPO, env=environment, capture_output=True, text=True,
                           encoding='utf-8', timeout=60)
    save(root / 'targeted_tests_v02.json', {'command': command, 'exit_code': tests.returncode,
        'PYTHONPATH': environment['PYTHONPATH'],
        'stdout': tests.stdout, 'stderr': tests.stderr, 'scope': 'targeted mathematical tests, not full suite or FEM'})
    if tests.returncode != 0:
        raise RuntimeError('Targeted tests failed; do not freeze as passed')
    validator = Path(r'C:\Users\chenb\.codex\skills\cb-plot-unified-style\scripts\validate_cb_plot_style.py')
    style_command = [sys.executable, '-B', '-X', 'utf8', str(validator), str(root / 'diagnostic_style_manifest.json')]
    style_check = subprocess.run(style_command, cwd=REPO, env=environment, capture_output=True,
                                 text=True, encoding='utf-8', timeout=30)
    errors = [line for line in (style_check.stdout + style_check.stderr).splitlines() if line.startswith('FAIL:')]
    expected = ['FAIL: PNG export_dpi must be 600.', 'FAIL: PNG pHYs density is 160.0 dpi, not 600 dpi.']
    if style_check.returncode != 1 or sorted(errors) != sorted(expected):
        raise ValueError('Unexpected publication-style validation outcome')
    style_manifest = read(root / 'diagnostic_style_manifest.json')
    with Image.open(root / 'diagnostic.png') as rendered:
        dimensions = list(rendered.size)
        dpi = rendered.info['dpi']
        if max(abs(value - 160) for value in dpi) > 1 or not style_manifest['validation']['passed']:
            raise ValueError('Exploratory rendering profile failed')
    save(root / 'delivery_audit.json', {'status': 'passed', 'scope': 'offline diagnostic delivery only',
        'scientific_pressure_gate': 'failed', 'causal_root': 'unknown', 'new_FEM_solves': 0,
        'readback': replay, 'targeted_tests': 'passed',
        'initial_test_collection': {'status': 'failed', 'record': 'targeted_tests.json',
            'cause': 'subprocess lacked PYTHONPATH=repository/src; no tests collected',
            'fix': 'only explicit subprocess environment; retained failure, mathematical tests unchanged',
            'verified_record': 'targeted_tests_v02.json'}, 'python': platform.python_version(),
        'numpy': np.__version__, 'visual_review': {'status': 'passed', 'png_dimensions': dimensions,
            'profile': 'exploratory 160dpi, not publication final', 'footer_overlap_corrected': True,
            'final_source_sha256': digest(root / 'sources/draw.py'),
            'initial_source_sha256': 'af44d4c79e75431c5f90a6f51ddb2fa3638f9fe7cf0ca99939c03eab410ded58',
            'revision': 'only canvas height and panel vertical placement; data and mechanics unchanged'},
        'publication_style_check': {'status': 'failed', 'command': style_command,
            'exit_code': style_check.returncode, 'stdout': style_check.stdout, 'stderr': style_check.stderr,
            'disposition': 'explicit exploratory-profile exception; no claim of publication-style pass'},
        'source_postcheck_note': 'source_postcheck.json records initial analysis; this audit rechecks final render revision',
        'new_external_result_root_authorized': True, 'GPU': 0, 'Docker_calls': 0,
        'deletions': 0, 'expert_script_executed': False, 'cache_retained': '.plot_cache; no deletion authorized'})
    files = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
            raise ValueError('Linked result artifact')
        if path.is_file():
            files.append({'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    save(root / 'manifest.json', {'status': 'passed', 'scope': 'completed offline evidence; scientific gate remains failed',
        'files': files, 'logical_bytes_without_manifest': sum(item['bytes'] for item in files)})
    manifest_sha = digest(root / 'manifest.json')
    register_result(REPO, root, 'passed', manifest_sha)
    print(json.dumps({'status': 'passed', 'manifest_sha256': manifest_sha, 'files': len(files)+1,
        'bytes': sum(item['bytes'] for item in files)+(root / 'manifest.json').stat().st_size,
        'targeted_tests': tests.stdout.strip(), 'scientific_gate': 'failed', 'new_FEM_solves': 0}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['intake','analyze','check','finalize'])
    args = parser.parse_args()
    if args.action == 'check':
        print(json.dumps(check(), ensure_ascii=False))
    else:
        {'intake': intake, 'analyze': analyze, 'finalize': finalize}[args.action]()
