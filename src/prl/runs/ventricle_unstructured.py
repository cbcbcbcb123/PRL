"""Create-only external package for the approved fixed-boundary comparison."""
import json
from pathlib import Path
import shutil
import numpy as np
from prl.result_store import result_path, result_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest, package_manifest
from prl.runs.fenicsx_runtime import read_docker, IMAGE, TAG, save_json, invoke_bounded
from prl.runs.ventricle_mesh_quality import MECHANICS
from prl.fem.ventricle_geometry import configuration
from prl.verification.ventricle_3d import load_arrays
from prl.verification.mesh_equivalence import compare

RESULT = Path('results/ventricle_fem/f6s2d2b_unstructured_v01_20260918')
PARENT = Path('results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918')
PARENT_SHA = 'c3df60d71c49de891d41e5c20b3fb01eddd922ef4ba3f8591a912b77a0cb24da'
FINE = Path('results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
FINE_SHA = '7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4'
CONTRACT = 'project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md'
ADOPTION = 'project_control/ventricle_fem_3d_unstructured_adoption_v01.md'
SOURCES = [CONTRACT, ADOPTION, *MECHANICS, 'src/prl/fem/unstructured_geometry.py',
    'src/prl/fem/ventricle_unstructured.py', 'src/prl/verification/mesh_equivalence.py',
    'src/prl/verification/tetra_quality.py', 'src/prl/runs/ventricle_unstructured.py',
    'src/prl/runs/fenicsx_runtime.py', 'src/prl/fem/fenicsx_ring.py',
    'src/prl/result_store.py', 'src/prl/storage.py', 'src/prl/cli.py',
    'tests/prl/test_unstructured_mesh.py']


def candidate_configuration():
    original = configuration()
    return {**original, 'meshes': [{'name': 'U1', 'source': 'M1 frozen surfaces'}],
            'states': original['states'][:2], 'maximum_equilibrium_solves': 2,
            'diagnostic_scope': 'One unstructured candidate, conditional zero and original pressure_1'}


def run(workspace):
    workspace = Path(workspace).resolve(strict=True)
    root = result_path(workspace, RESULT, new=True)
    parent, fine = [result_path(workspace, path) for path in [PARENT, FINE]]
    for ancestor, checksum in [(parent, PARENT_SHA), (fine, FINE_SHA)]:
        if digest(ancestor/'manifest.json') != checksum:
            raise ValueError('Frozen prerequisite manifest mismatch')
        manifest = json.loads((ancestor/'manifest.json').read_text())
        if not all(digest(ancestor/f['path']) == f['sha256'] for f in manifest['files']):
            raise ValueError('Frozen prerequisite files changed')
    if not (workspace/ADOPTION).is_file():
        raise ValueError('Approved candidate adoption required')
    internal = json.loads((parent/'protected_preflight.json').read_text())
    external = json.loads((parent/'external_protected_preflight.json').read_text())
    external.update({str(p): digest(p) for p in parent.rglob('*') if p.is_file()})
    dirty = json.loads((parent/'preexisting_changes.json').read_text())
    if not protected_unchanged(workspace, internal, external, dirty):
        raise ValueError('Protected evidence/unrelated modifications changed')
    identity = {key: digest(workspace/key) == digest(parent/'sources_at_delivery'/key) for key in MECHANICS}
    if not all(identity.values()):
        raise ValueError('Mechanical implementation drift')
    runtime = json.loads(read_docker('version', '--format', '{{json .}}'))
    if not runtime.get('Server') or read_docker('image', 'inspect', TAG, '--format', '{{.Id}}') != IMAGE:
        raise RuntimeError('Pinned runtime unavailable; no repair/pull allowed')
    if read_docker('ps', '-q'):
        raise RuntimeError('Another container is running')
    admission = result_admission(workspace, 768*1024**2, 64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage refused')
    root.mkdir(parents=True, exist_ok=False); (root/'input').mkdir()
    for filename, value in [('configuration.json', candidate_configuration()), ('docker_version.json', runtime),
        ('storage_preflight.json', admission), ('protected_preflight.json', internal),
        ('external_protected_preflight.json', external), ('preexisting_changes.json', dirty), ('mechanical_identity.json', identity)]:
        save_json(root/filename, value)
    copies = [(fine/'input'/f'M1_geometry.{extension}', root/'input'/f'M1_geometry.{extension}') for extension in ['npz', 'json']]
    copies += [(parent/'manifest.json', root/'input/parent_manifest.json'),
               (fine/'manifest.json', root/'input/fine_manifest.json'), (parent/'quality_report.json', root/'input/parent_quality_report.json')]
    copies += [(fine/'raw'/name, root/'retained'/name) for name in ['M1_mesh.npz', 'M1_state_pressure_1.npz', 'M1_state_pressure_1.json']]
    copies += [(workspace/key, root/'sources_at_execution'/key) for key in SOURCES]
    identities = {}
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        identities[target.relative_to(root).as_posix()] = {'source': str(source), 'sha256': digest(source)}
    save_json(root/'copied_identities.json', identities)
    with scientific_lock(workspace):
        report = invoke_bounded(workspace, root, 'prl-f6s2d2b-unstructured-v01-20260918',
            '/workspace/src/prl/fem/ventricle_unstructured.py', seconds=1800)
    report['parents_unchanged'] = protected_unchanged(workspace, internal, external, dirty)
    if not report['parents_unchanged']:
        report['status'] = 'failed'
    save_json(root/'execution.json', report)
    save_json(root/'formal_invocation_manifest.json', package_manifest(root))
    return report


def verify(root):
    """Offline reproducibility, deliberately separate from candidate acceptance."""
    root = Path(root)
    identities = json.loads((root/'copied_identities.json').read_text())
    checks = {'copies_unchanged': all(digest(root/k) == v['sha256'] for k, v in identities.items())}
    saved = json.loads((root/'candidate_execution.json').read_text())
    if (root/'mesh_comparison.json').exists():
        report, arrays = compare(load_arrays(root/'input/M1_geometry.npz'), load_arrays(root/'candidate_geometry.npz'))
        checks['comparison_exact'] = report == json.loads((root/'mesh_comparison.json').read_text())
        old = load_arrays(root/'mesh_metrics.npz')
        checks['arrays_exact'] = old.keys() == arrays.keys() and all(np.array_equal(old[k], arrays[k]) for k in old)
        checks['no_FEM_after_mesh_failure'] = report['status'] == 'passed' or (saved['attempted_states'] == 0 and not (root/'raw').exists())
    else:
        checks['recorded_meshing_failure'] = saved['phase'] == 'meshing' and (root/'failure.json').is_file()
    if (root/'offline/mesh_comparison.json').is_file():
        from prl.verification.saved_gmsh import load_saved
        reference = load_arrays(root/'input/M1_geometry.npz')
        raw_candidate = load_saved(root/'candidate.msh', reference)
        saved_candidate = load_arrays(root/'offline/candidate_geometry.npz')
        report, arrays = compare(reference, raw_candidate)
        old_arrays = load_arrays(root/'offline/mesh_metrics.npz')
        checks['export_readback_exact'] = raw_candidate.keys() == saved_candidate.keys() and all(
            np.array_equal(raw_candidate[k], saved_candidate[k]) for k in raw_candidate)
        checks['offline_report_exact'] = report == json.loads((root/'offline/mesh_comparison.json').read_text())
        checks['offline_arrays_exact'] = arrays.keys() == old_arrays.keys() and all(np.array_equal(arrays[k], old_arrays[k]) for k in arrays)
        checks['no_continuation_after_failure'] = saved['attempted_states'] == 0 and not (root/'raw').exists()
    checks['bounded_state_count'] = saved['attempted_states'] <= 2 and saved['automatic_retries'] == 0
    result = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
              'candidate_status': saved['status'], 'FEM': saved['FEM'], 'new_FEM_solves': saved['attempted_states']}
    if saved['attempted_states']:
        from prl.verification.ventricle_3d import verify as verify_mechanics
        result['mechanics'] = verify_mechanics(root)
    return result


def audit_saved_candidate(workspace):
    """Create-only post-failure audit of the single saved mesh. Never resume FEM."""
    from prl.verification.saved_gmsh import load_saved
    import meshio
    root = result_path(workspace, RESULT)
    if (root/'offline').exists():
        raise FileExistsError('Offline extraction already exists')
    formal = json.loads((root/'formal_invocation_manifest.json').read_text())
    if not all(digest(root/f['path']) == f['sha256'] for f in formal['files']):
        raise ValueError('Original invocation files changed')
    original = load_arrays(root/'input/M1_geometry.npz')
    candidate = load_saved(root/'candidate.msh', original)
    report, arrays = compare(original, candidate)
    (root/'offline').mkdir(exist_ok=False)
    np.savez_compressed(root/'offline/candidate_geometry.npz', **candidate)
    np.savez_compressed(root/'offline/mesh_metrics.npz', **arrays)
    save_json(root/'offline/mesh_comparison.json', report)
    save_json(root/'offline/extraction.json', {'status': 'passed', 'meshio_version': meshio.__version__,
        'candidate_msh_sha256': digest(root/'candidate.msh'), 'new_candidates': 0, 'new_FEM_solves': 0,
        'original_invocation': 'failed', 'mapping': 'exact coordinates, no rounding or nearest-neighbor repair',
        'root_cause': 'Gmsh automatically renumbered nodes; original adapter assumed input tags survived.',
        'runtime_adapter_after_fix': 'not_run'})
    return report


def finalize(workspace):
    """Seal the failed candidate and successful offline delivery, never relabel it."""
    import html
    import platform
    from importlib.metadata import version
    from prl.result_store import register_result
    from prl.storage import scan_workspace
    workspace = Path(workspace).resolve(strict=True); root = result_path(workspace, RESULT)
    if (root/'manifest.json').exists():
        raise FileExistsError('Delivery already frozen')
    verified = verify(root)
    formal = json.loads((root/'formal_invocation_manifest.json').read_text())
    internal = json.loads((root/'protected_preflight.json').read_text())
    external = json.loads((root/'external_protected_preflight.json').read_text())
    dirty = json.loads((root/'preexisting_changes.json').read_text())
    revision = Path(json.loads((root/'render_preparation.json').read_text())['revision']); prefix = revision.name
    methods = (revision/f'02_{prefix}_methods.txt').read_text(encoding='utf-8')
    tests = json.loads((root/'tests.json').read_text())
    candidate = json.loads((root/'candidate_execution.json').read_text())
    comparison = json.loads((root/'offline/mesh_comparison.json').read_text())
    execution = 'project_control/ventricle_fem_3d_unstructured_execution_v01.md'
    checks = {'offline_reproduction': verified['status'] == 'passed',
        'original_invocation_unchanged': all(digest(root/item['path']) == item['sha256'] for item in formal['files']),
        'protected_evidence_and_unrelated_changes': protected_unchanged(workspace, internal, external, dirty),
        'mechanics_bytewise_unchanged': all(digest(workspace/key) == digest(root/'sources_at_execution'/key) for key in MECHANICS),
        'failed_candidate_not_relabelled': candidate['status'] == 'failed' and comparison['status'] == 'failed',
        'FEM_not_run': candidate['attempted_states'] == 0 and not (root/'raw').exists(),
        'figure_final_and_visual_checked': all(marker in methods for marker in ['包状态: 最终包', '人工/代理视觉验收: 通过', '自动校验: 通过']),
        'figure_physical_data_copy': digest(root/'figure_data.npz') == digest(revision/f'01_{prefix}_data.npz'),
        'figure_helper_identity': digest(workspace/'src/prl/rendering/ventricle_unstructured.py') == digest(next(revision.glob('*_helper.py'))),
        'figure_quality_identity': digest(workspace/'src/prl/verification/tetra_quality.py') == digest(next(revision.glob('*_quality.py'))),
        'tests': tests['status'] == 'passed' and tests['exit_code'] == 0,
        'repo_below_3GiB': scan_workspace(workspace).logical_bytes < 3*1024**3}
    if not all(checks.values()):
        raise ValueError('Delivery checks failed: '+str(checks))
    save_json(root/'post_verification.json', verified)
    save_json(root/'delivery_environment.json', {'python': platform.python_version(), 'platform': platform.platform(),
        'packages': {key: version(key) for key in ['numpy', 'scipy', 'meshio', 'matplotlib', 'nbformat', 'nbclient', 'ipython']}})
    sources = sorted(set(SOURCES+[execution, 'src/prl/verification/saved_gmsh.py', 'src/prl/rendering/ventricle_unstructured.py']))
    for key in sources:
        target = root/'sources_at_delivery'/key; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace/key, target)
    save_json(root/'delivery_source_hashes.json', {key: digest(workspace/key) for key in sources})
    # Link targets are relative to THIS external result package, not project_control.
    report = (workspace/execution).read_text(encoding='utf-8')
    report = report.replace('../../PRL-results/ventricle_fem/'+root.name+'/', '')
    report = report.replace('(ventricle_fem_3d_unstructured_comparison_contract_v01.md)', '(../../../PRL/project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md)')
    report = report.replace('(ventricle_fem_3d_unstructured_adoption_v01.md)', '(../../../PRL/project_control/ventricle_fem_3d_unstructured_adoption_v01.md)')
    report = report.replace('(../src/', '(../../../PRL/src/')
    (root/'report.md').write_text(report, encoding='utf-8')
    picture = (revision/f'04_{prefix}.png').relative_to(root).as_posix()
    notebook = (revision/f'03_{prefix}_plot.ipynb').relative_to(root).as_posix()
    links = [('执行报告', 'report.md'), ('网格比较', 'offline/mesh_comparison.json'), ('原失败', 'failure.json'),
             ('候选原始MSH', 'candidate.msh'), ('Notebook', notebook), ('交付验收', 'delivery_audit.json'), ('清单', 'manifest.json')]
    navigation = ' · '.join(f'<a href="{html.escape(target)}">{html.escape(label)}</a>' for label, target in links)
    (root/'index.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>PRL 非结构化候选</title>'
        '<style>body{font:18px/1.7 system-ui;max-width:1200px;margin:35px auto;padding:0 20px;color:#182c36}'
        'img{width:100%}.warning{color:#a33430}a{color:#226b61}</style><h1>同边界候选：几何保持，质量门未通过</h1>'
        '<p>一候选已消耗；原执行与网格质量 <span class="warning">failed</span>。离线复核/图件交付passed，FEM not_run。</p>'
        '<p>3960→2611四面体，19119→13483预计DOF；边界、层界和体积保持。q05改善4.44%，未达预设5%。</p>'
        '<p>最小角6.638°→6.811°，但最差q从0.2220降至0.0292，少数ECM单元变差。不能只看均值或外观。</p>'
        '<p>Gmsh已生成网格，输出适配器因节点重编号失效；原失败保留，只读解析现有MSH完成上述审查。'
        '修订适配器通过测试，未重新运行容器。无新应力或变形场，无重跑。</p>'
        f'<p>{navigation}</p><img src="{picture}" alt="实际原/候选四面体结构、质量分布和角度分布">'
        '<p>下一步建议：形成近不可压三维混合离散小基准方案，先验证稳定性与局部体积控制。'
        '原1%门保持，不直接进入生长/FSI。</p></html>', encoding='utf-8')
    save_json(root/'summary.json', {'status': 'failed', 'stage': 'F6-S2-D2B', 'geometry_equivalence': 'passed',
        'quality_improvement_gate': 'failed', 'offline_delivery': 'passed', 'FEM': 'not_run',
        'new_FEM_solves': 0, 'candidate_count': 1, 'automatic_retries': 0,
        'global_q05_improvement_percent': 100*(comparison['candidate']['regions']['all']['q_radius']['p05']/
                                              comparison['reference']['regions']['all']['q_radius']['p05']-1),
        'tests_passed': tests['passed'], 'subtests_passed': tests['subtests_passed'],
        'next_action': 'design a bounded 3D near-incompressible mixed-discretization qualification; no new execution authority'})
    save_json(root/'delivery_audit.json', {'status': 'passed', 'checks': checks,
        'protected_internal_files': len(internal), 'protected_external_files': len(external),
        'preexisting_dirty_files': len(dirty), 'formal_invocation_files': len(formal['files']),
        'tests': tests, 'repository_bytes': scan_workspace(workspace).logical_bytes,
        'scientific_candidate': 'failed', 'new_FEM_solves': 0})
    save_json(root/'manifest.json', package_manifest(root))
    checksum = digest(root/'manifest.json')
    register_result(workspace, root, 'failed', checksum)
    return {'status': 'passed', 'scientific_candidate': 'failed', 'files': sum(p.is_file() for p in root.rglob('*')),
        'bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()), 'manifest_sha256': checksum,
        'protected_internal_files': len(internal), 'protected_external_files': len(external)}
