"""Create-only retained-mesh audit. No solver or container launch capability."""
import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np
from prl.result_store import result_admission, result_path
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest, package_manifest
from prl.runs.fenicsx_runtime import read_docker, save_json, IMAGE
from prl.verification.tetra_quality import analyze
from prl.verification.ventricle_3d import load_arrays

RESULT = Path('results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918')
PARENT = Path('results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
PARENT_SHA = '7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4'
CONTRACT = 'project_control/ventricle_fem_3d_mesh_quality_contract_v01.md'
MECHANICS = ['src/prl/fem/ventricle_geometry.py', 'src/prl/fem/fenicsx_ventricle.py',
             'src/prl/verification/ventricle_3d.py', 'src/prl/fem/ventricle_protocol.py']
SOURCES = [CONTRACT, 'src/prl/verification/tetra_quality.py', 'src/prl/runs/ventricle_mesh_quality.py',
           'src/prl/verification/ventricle_mesh_probe.py', 'src/prl/cli.py', 'tests/prl/test_tetra_quality.py', *MECHANICS]


def compute(root):
    root = Path(root)
    config = json.loads((root/'input/configuration.json').read_text())
    reference = json.loads((root/'input/parent_mesh_diagnostic.json').read_text())
    summaries = {}
    arrays = {}
    checks = {}
    for name in ['M0', 'M1']:
        mesh = load_arrays(root/'input'/f'{name}_mesh.npz')
        state = load_arrays(root/'input'/f'{name}_state_pressure_1.npz')
        data, summaries[name] = analyze(mesh, state, config)
        arrays.update({name+'_'+key: value for key, value in data.items()})
        prior = reference['spatial'][name]['regions']['all']
        actual = summaries[name]['regions']['all']
        checks[name+'_cells'] = summaries[name]['cells'] == prior['cells']
        checks[name+'_J_identity'] = abs(actual['distributions']['max_abs_J_minus_one']['max']-prior['max_abs_J_minus_one']) < 1e-12
        checks[name+'_failed_count_identity'] = actual['volume_gate_failed_cells'] == prior['above_one_percent_cells']
        checks[name+'_original_load'] = float(state['load']) == .01 and float(state['activation']) == 0.
        checks[name+'_finite_quality'] = bool(all(np.isfinite(data[k]).all() for k in data))
    return {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
        'meshes': summaries, 'scientific_pressure_gate': 'failed', 'new_FEM_solves': 0,
        'shape_screen_only': {'q_radius_below': .2, 'min_dihedral_below_deg': 10., 'universal_acceptance_gate': False},
        'correlation': 'Descriptive per-cell ranks rounded to 12 decimals; no p values or biological replicates.',
        'causation': 'unknown', 'unstructured_FEM': 'not_run'}, arrays


def run(workspace):
    workspace = Path(workspace).resolve(strict=True)
    root = result_path(workspace, RESULT, new=True)
    parent = result_path(workspace, PARENT)
    if not (workspace/CONTRACT).is_file() or digest(parent/'manifest.json') != PARENT_SHA:
        raise ValueError('Contract or parent identity mismatch')
    frozen = json.loads((parent/'manifest.json').read_text())
    if not all(digest(parent/entry['path']) == entry['sha256'] for entry in frozen['files']):
        raise ValueError('Frozen parent changed')
    internal = json.loads((parent/'protected_preflight.json').read_text())
    external = json.loads((parent/'external_protected_preflight.json').read_text())
    external.update({str(p): digest(p) for p in parent.rglob('*') if p.is_file()})
    dirty = json.loads((parent/'preexisting_changes.json').read_text())
    if not protected_unchanged(workspace, internal, external, dirty):
        raise ValueError('Protected data or unrelated edits changed')
    mechanical_identity = {key: digest(workspace/key) == digest(parent/'sources_at_delivery'/key) for key in MECHANICS}
    if not all(mechanical_identity.values()):
        raise ValueError('Original mechanics changed')
    admission = result_admission(workspace, 128*1024**2, 64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage refused')
    root.mkdir(parents=True, exist_ok=False)
    (root/'input').mkdir()
    for filename, value in [('storage_preflight.json', admission), ('protected_preflight.json', internal),
        ('external_protected_preflight.json', external), ('preexisting_changes.json', dirty),
        ('mechanical_identity.json', mechanical_identity)]:
        save_json(root/filename, value)
    copies = [(parent/'configuration.json', root/'input/configuration.json'),
              (parent/'manifest.json', root/'input/parent_manifest.json'),
              (parent/'mesh_diagnostic.json', root/'input/parent_mesh_diagnostic.json')]
    for name, folder in [('M0', 'retained'), ('M1', 'raw')]:
        for filename in [f'{name}_mesh.npz', f'{name}_state_pressure_1.npz', f'{name}_state_pressure_1.json']:
            copies.append((parent/folder/filename, root/'input'/filename))
    copies.extend((workspace/key, root/'sources_at_execution'/key) for key in SOURCES)
    identities = {}
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        identities[target.relative_to(root).as_posix()] = {'source': str(source), 'sha256': digest(source)}
    save_json(root/'copied_identities.json', identities)
    # Read back the one already completed, read-only dependency probe; never rerun it.
    inspection = json.loads(read_docker('inspect', 'prl-f6s2d2a-mesher-probe-v01-20260918'))[0]
    save_json(root/'mesher_probe_inspect.json', inspection)
    save_json(root/'mesher_availability.json', {
        'status': 'passed' if inspection['State']['ExitCode'] == 0 and inspection['Image'] == IMAGE else 'failed',
        'host_find_spec': {name: bool(importlib.util.find_spec(name)) for name in ['gmsh', 'tetgen', 'meshio']},
        'container_stdout_observed_in_tool': {'gmsh': True, 'meshio': False, 'tetgen': False},
        'probe_only_find_spec': True, 'gmsh_native_import_and_meshing': 'not_run',
        'container_command': inspection['Config']['Cmd'], 'probes': 1, 'new_FEM_solves': 0,
        'note': 'Discovery is not proof that Gmsh native library can load or create the required mesh.'})
    report, arrays = compute(root)
    np.savez_compressed(root/'cell_metrics.npz', **arrays)
    save_json(root/'quality_report.json', report)
    save_json(root/'audit_input_manifest.json', package_manifest(root))
    return report


def verify(root):
    root = Path(root)
    report, arrays = compute(root)
    saved = load_arrays(root/'cell_metrics.npz')
    same = saved.keys() == arrays.keys() and all(np.array_equal(saved[key], arrays[key]) for key in saved)
    identities = json.loads((root/'copied_identities.json').read_text())
    copies = all(digest(root/key) == value['sha256'] for key, value in identities.items())
    saved_report = json.loads((root/'quality_report.json').read_text())
    checks = {'recomputed_metrics_exact': same, 'copied_inputs_and_sources': copies,
              'summary_recomputed_exact': saved_report == report, 'original_failure_retained': report['scientific_pressure_gate'] == 'failed'}
    return {'status': 'passed' if all(checks.values()) and report['status'] == 'passed' else 'failed',
            'checks': checks, 'new_FEM_solves': 0, 'scientific_pressure_gate': 'failed'}


def finalize(workspace):
    """Seal completed offline delivery; no launches, figure changes or cleanup."""
    import html
    import platform
    from importlib.metadata import version
    from prl.result_store import register_result
    from prl.storage import scan_workspace
    workspace = Path(workspace).resolve(strict=True); root = result_path(workspace, RESULT)
    if (root/'manifest.json').exists():
        raise FileExistsError('Delivery already frozen')
    verification = verify(root)
    formal = json.loads((root/'audit_input_manifest.json').read_text())
    internal = json.loads((root/'protected_preflight.json').read_text())
    external = json.loads((root/'external_protected_preflight.json').read_text())
    dirty = json.loads((root/'preexisting_changes.json').read_text())
    revision = Path(json.loads((root/'render_preparation.json').read_text())['revision']); prefix = revision.name
    methods = (revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    tests = json.loads((root/'tests.json').read_text())
    checks = {'verification': verification['status'] == 'passed',
        'audit_inputs_unchanged': all(digest(root/item['path']) == item['sha256'] for item in formal['files']),
        'ancestors_and_unrelated_edits': protected_unchanged(workspace, internal, external, dirty),
        'mechanics_unchanged': all(digest(workspace/key) == digest(root/'sources_at_execution'/key) for key in MECHANICS),
        'notebook_visual_and_final': all(marker in methods for marker in ['包状态: 最终包', '人工/代理视觉验收: 通过', '自动校验: 通过']),
        'figure_input_copy': digest(root/'figure_data.npz') == digest(revision/f'01_{prefix}_data.npz'),
        'figure_quality_snapshot': digest(workspace/'src/prl/verification/tetra_quality.py') == digest(next(revision.glob('*_quality.py'))),
        'figure_helper_snapshot': digest(workspace/'src/prl/rendering/ventricle_mesh_quality.py') == digest(next(revision.glob('*_helper.py'))),
        'tests': tests['status'] == 'passed' and tests['passed'] == 121,
        'repository_below_3GiB': scan_workspace(workspace).logical_bytes < 3*1024**3}
    if not all(checks.values()):
        raise ValueError('Delivery rejected: '+str(checks))
    save_json(root/'post_verification.json', verification)
    save_json(root/'delivery_environment.json', {'python': platform.python_version(), 'platform': platform.platform(),
        'packages': {key: version(key) for key in ['numpy', 'scipy', 'matplotlib', 'nbformat', 'nbclient', 'ipython']},
        'note': 'Read from unchanged host environment at delivery; notebook records its Python/kernel execution separately.'})
    execution = 'project_control/ventricle_fem_3d_mesh_quality_execution_v01.md'
    proposal = 'project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md'
    sources = sorted(set(SOURCES+[execution, proposal, 'src/prl/rendering/ventricle_mesh_quality.py']))
    for key in sources:
        target = root/'sources_at_delivery'/key; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace/key, target)
    save_json(root/'delivery_source_hashes.json', {key: digest(workspace/key) for key in sources})
    (root/'report.md').write_text((workspace/execution).read_text(encoding='utf-8'), encoding='utf-8')
    picture = (revision/f'04_{prefix}.png').relative_to(root).as_posix()
    notebook = (revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix()
    links = [('质量报告', 'quality_report.json'), ('逐单元指标', 'cell_metrics.npz'), ('Notebook', notebook),
             ('诊断复核', 'post_verification.json'), ('交付验收', 'delivery_audit.json'), ('完整清单', 'manifest.json')]
    navigation = ' · '.join(f'<a href="{html.escape(target)}">{html.escape(label)}</a>' for label, target in links)
    (root/'index.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>PRL 网格质量审查</title>'
        '<style>body{font:18px/1.7 system-ui;max-width:1300px;margin:35px auto;padding:0 20px;color:#182c36}'
        'img{width:100%}.warning{color:#a33430}a{color:#226b61}</style><h1>网格质量改善，仍不能单独解释基底体积误差</h1>'
        '<p>离线诊断与交付 passed；原三维压力资格 <span class="warning">failed</span>。新FEM求解：0。</p>'
        '<p>M0→M1最小二面角4.411°→6.638°，q最小值0.1514→0.2220；局部体积偏差仍1.5227%→1.4496%。</p>'
        '<p>M1全部120个超限单元都邻接基底；其中72个没有触发形状筛查。384个远区形状标记单元无一超体积门。</p>'
        '<p>筛查阈值q&lt;0.2或最小二面角&lt;10°不是普适合格门，相关性不是因果。尚未运行非结构化候选。</p>'
        f'<p>{navigation}</p><img src="{picture}" alt="原网格形状、体积误差和全部单元散点">'
        '<p>下步：同一多面体边界的内部非结构化剖分，先验收几何和质量，再按合同决定是否加载。'
        '不改变材料、压力、基底或原1%门。Gmsh只发现模块，实际加载和网格生成尚未验证。</p></html>', encoding='utf-8')
    save_json(root/'summary.json', {'status': 'passed', 'stage': 'F6-S2-D2A', 'scientific_pressure_gate': 'failed',
        'causal_identification': 'unknown', 'new_FEM_solves': 0, 'unstructured_mesh': 'not_run',
        'rendering': 'passed', 'tests_passed': tests['passed'], 'subtests_passed': tests['subtests_passed'],
        'next_contract': proposal, 'next_execution': 'pending_confirmation'})
    save_json(root/'delivery_audit.json', {'status': 'passed', 'checks': checks, 'audit_files_unchanged': len(formal['files']),
        'protected_external_files_unchanged': len(external), 'preexisting_dirty_files_unchanged': len(dirty),
        'tests': tests, 'new_FEM_solves': 0, 'repository_bytes': scan_workspace(workspace).logical_bytes})
    save_json(root/'manifest.json', package_manifest(root))
    checksum = digest(root/'manifest.json')
    register_result(workspace, root, 'passed', checksum)
    return {'status': 'passed', 'files': len(list(p for p in root.rglob('*') if p.is_file())),
            'bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()), 'manifest_sha256': checksum,
            'protected_external_files': len(external), 'preexisting_dirty_files': len(dirty)}
