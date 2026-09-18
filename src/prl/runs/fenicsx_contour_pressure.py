"""Create-only contour slice with qualified runtime/ancestor evidence reuse."""
import json
from pathlib import Path
import shutil

from prl.fem.ring_geometry import configuration as base_configuration
from prl.result_store import result_path, result_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_contour import SOURCE, PASSIVE_RESULT, FINE_RESULT
from prl.runs.fenicsx_ring import digest, package_manifest
from prl.runs.fenicsx_runtime import read_docker, IMAGE, TAG, save_json, invoke_bounded
from prl.verification.fenicsx_contour import SOURCE_SHA
from prl.verification.fenicsx_contour_pressure import GEOMETRY_HASHES

RESULT = Path('results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918')
PREREQUISITE = Path('results/ventricle_fem/f6s1s6_fine_ring_v01_20260918')
CONTRACT = Path('project_control/ventricle_fem_contour_dg2_contract_v01.md')
SOURCES = [CONTRACT.as_posix(), 'src/prl/cli.py', 'src/prl/fem/fenicsx_contour_pressure.py',
    'src/prl/fem/fenicsx_ring.py','src/prl/fem/ring_geometry.py',
    'src/prl/verification/fenicsx_contour_pressure.py','src/prl/verification/fenicsx_contour.py',
    'src/prl/verification/fenicsx_ring.py','src/prl/verification/fenicsx_pressure.py',
    'src/prl/runs/fenicsx_contour_pressure.py','src/prl/runs/fenicsx_contour.py',
    'src/prl/runs/fenicsx_runtime.py','src/prl/runs/fenicsx_ring.py','src/prl/runs/fem_finite_strain.py',
    'src/prl/result_store.py','src/prl/storage.py','project_control/result_storage_policy.json',
    'tests/prl/test_fenicsx_contour_pressure.py']


def configuration():
    cfg = base_configuration()
    cfg.update(schema_version='prl.contour_pressure.v1',geometry_kind='image_polygon',pressure_space='DG2',
        objects=['contour'],meshes=[{'name':'M0'},{'name':'M1'}],passive_loads=[0.,.02],active_peak=0.,
        maximum_equilibrium_solves=4,retain_solver_iterates=True,diagnostic_trace=True,
        source='72 hpf Fish 4 XY z=39; only outer boundary measured; cavity/layers constructed',
        resources={'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0},
        scope='two retained contour meshes at zero and first pressure; no active/3D/FSI/growth or physiological clock')
    cfg['solver']['mat_mumps_icntl_14'] = 100
    return cfg


def protected_unchanged(workspace, internal, external, dirty):
    # Never call while holding the Windows byte lock: it is a protected dirty file.
    return (all(digest(workspace/path) == sha for path,sha in internal.items())
        and all(digest(path) == sha for path,sha in external.items())
        and all(digest(workspace/item['path']) == item['sha256'] for item in dirty))


def run_contour_pressure(workspace):
    workspace = Path(workspace).resolve(strict=True)
    root = result_path(workspace, RESULT, new=True)
    parent = result_path(workspace, PREREQUISITE)
    if not (workspace/CONTRACT).is_file() or digest(workspace/SOURCE) != SOURCE_SHA:
        raise ValueError('Contract or original source missing/changed')
    manifest = json.loads((parent/'manifest.json').read_text())
    if not all(digest(parent/item['path']) == item['sha256'] for item in manifest['files']):
        raise ValueError('Frozen prerequisite changed')
    qualification = json.loads((parent/'post_verification.json').read_text())
    if qualification['status'] != 'passed' or not all(qualification['checks'].values()):
        raise ValueError('Two-mesh ring prerequisite not passed')
    internal = json.loads((parent/'protected_preflight.json').read_text())
    external = json.loads((parent/'external_protected_preflight.json').read_text())
    external.update({str(p):digest(p) for p in parent.rglob('*') if p.is_file()})
    dirty = json.loads((parent/'preexisting_changes.json').read_text())
    if not protected_unchanged(workspace,internal,external,dirty):
        raise ValueError('Ancestor or unrelated edit drift')
    for name,sha in GEOMETRY_HASHES.items():
        if digest(workspace/PASSIVE_RESULT/'raw'/f'{name}_input_mesh.npz') != sha:
            raise ValueError('Frozen contour input changed')
    version = json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}') != IMAGE:
        raise RuntimeError('Pinned runtime unavailable; no restart/repair/install/pull authorized')
    if read_docker('ps','-q'):
        raise RuntimeError('Another container is running; do not overlap scientific work')
    admission = result_admission(workspace,512*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    root.mkdir(parents=True,exist_ok=False)
    for filename,value in [('configuration.json',configuration()),('docker_version.json',version),
        ('storage_preflight.json',admission),('protected_preflight.json',internal),
        ('external_protected_preflight.json',external),('preexisting_changes.json',dirty)]:
        save_json(root/filename,value)
    copies = [(workspace/SOURCE,root/'geometry_source.npz')]
    for filename in ['configuration.json','post_verification.json','runtime_zero_newton/verification.json']:
        copies.append((parent/filename,root/'prerequisite'/filename))
    for name in ['M0','M1']:
        copies.append((workspace/PASSIVE_RESULT/'raw'/f'{name}_input_mesh.npz',root/'input'/f'{name}_input_mesh.npz'))
        original = workspace/PASSIVE_RESULT if name == 'M0' else result_path(workspace,FINE_RESULT)
        for before,after in [('configuration.json','configuration.json'),(f'raw/{name}_mesh.npz','mesh.npz'),
            (f'raw/{name}_state_passive_1.npz','state.npz'),(f'raw/{name}_state_passive_1.json','state.json')]:
            copies.append((original/before,root/'comparison'/name/after))
    for relative in SOURCES:
        copies.append((workspace/relative,root/'sources_at_execution'/relative))
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
    save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in SOURCES})
    save_json(root/'input_identities.json',{target.relative_to(root).as_posix():{'source':str(source),'sha256':digest(source)} for source,target in copies})
    with scientific_lock(workspace):
        report = invoke_bounded(workspace,root,'prl-f6s1s7-contour-dg2-v01-20260918',
            '/workspace/src/prl/fem/fenicsx_contour_pressure.py')
    report['parents_unchanged'] = protected_unchanged(workspace,internal,external,dirty)
    report.update(scientific_invocations=1,runtime_microprobes=0,mesh_generation_calls=0)
    if not report['parents_unchanged']:
        report['status'] = 'failed'
    save_json(root/'execution.json',report)
    save_json(root/'formal_invocation_manifest.json',package_manifest(root))
    return report
