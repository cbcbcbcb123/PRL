"""One bounded create-only 3D qualification, preserving the retired 2D evidence."""
import json
from pathlib import Path
import shutil
import numpy as np
from prl.fem.ventricle_geometry import configuration,half_ellipsoid,geometry_metrics
from prl.result_store import result_path,result_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_runtime import read_docker,IMAGE,TAG,save_json,invoke_bounded

RESULT=Path('results/ventricle_fem/f6s2_idealized_3d_v01_20260918')
PARENT=Path('results/ventricle_fem/f6s1s9_contour_active_v01_20260918')
PARENT_SHA='80b0ecbe6bd35e6d00479fbeb1e424c89969e862a01bdb0885bb43dab9734c2b'
CONTRACT='project_control/ventricle_fem_idealized_3d_contract_v01.md'
SOURCES=[CONTRACT,'project_control/ventricle_3d_before_growth_decision_v01.md',
    'src/prl/fem/ventricle_geometry.py','src/prl/fem/fenicsx_ventricle.py','src/prl/fem/fenicsx_ring.py',
    'src/prl/fem/ring_geometry.py','src/prl/verification/ventricle_3d.py','src/prl/verification/fenicsx_ring.py',
    'src/prl/runs/ventricle_3d.py','src/prl/runs/fenicsx_runtime.py','src/prl/runs/fenicsx_contour_pressure.py',
    'src/prl/runs/fenicsx_contour.py','src/prl/runs/fenicsx_ring.py','src/prl/runs/fem_finite_strain.py',
    'src/prl/result_store.py','src/prl/storage.py','src/prl/cli.py','project_control/result_storage_policy.json',
    'tests/prl/test_ventricle_3d.py']


def run(workspace):
    workspace=Path(workspace).resolve(strict=True); root=result_path(workspace,RESULT,new=True)
    parent=result_path(workspace,PARENT)
    if not (workspace/CONTRACT).is_file() or digest(parent/'manifest.json')!=PARENT_SHA:
        raise ValueError('Contract or qualified 2D ancestor identity mismatch')
    parent_manifest=json.loads((parent/'manifest.json').read_text())
    if not all(digest(parent/f['path'])==f['sha256'] for f in parent_manifest['files']):
        raise ValueError('Frozen ancestor changed')
    internal=json.loads((parent/'protected_preflight.json').read_text())
    external=json.loads((parent/'external_protected_preflight.json').read_text())
    external.update({str(p):digest(p) for p in parent.rglob('*') if p.is_file()})
    dirty=json.loads((parent/'preexisting_changes.json').read_text())
    if not protected_unchanged(workspace,internal,external,dirty):
        raise ValueError('Protected ancestors/unrelated edits changed')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned runtime unavailable; no repair/pull/restart authorized')
    if read_docker('ps','-q'):
        raise RuntimeError('Another container is running')
    admission=result_admission(workspace,768*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage refused')
    cfg=configuration(); geometries=[]
    for case in cfg['meshes']:
        data=half_ellipsoid(case,cfg); metrics=geometry_metrics(data,cfg,case['name'])
        if metrics['status']!='passed':
            raise ValueError('Geometry qualification rejected before scientific run')
        geometries.append((case['name'],data,metrics))
    root.mkdir(parents=True,exist_ok=False); (root/'input').mkdir()
    for filename,value in [('configuration.json',cfg),('docker_version.json',version),
        ('storage_preflight.json',admission),('protected_preflight.json',internal),
        ('external_protected_preflight.json',external),('preexisting_changes.json',dirty)]:
        save_json(root/filename,value)
    for name,data,metrics in geometries:
        np.savez_compressed(root/'input'/f'{name}_geometry.npz',**data)
        save_json(root/'input'/f'{name}_geometry.json',metrics)
    copies=[(parent/'manifest.json',root/'prerequisite/parent_manifest.json'),
            (parent/'summary.json',root/'prerequisite/parent_summary.json')]
    copies.extend((workspace/p,root/'sources_at_execution'/p) for p in SOURCES)
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
    save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in SOURCES})
    save_json(root/'input_identities.json',{p.relative_to(root).as_posix():digest(p)
        for p in (root/'input').iterdir()})
    with scientific_lock(workspace):
        report=invoke_bounded(workspace,root,'prl-f6s2-idealized-3d-v01-20260918',
            '/workspace/src/prl/fem/fenicsx_ventricle.py',seconds=cfg['resources']['seconds'])
    report.update(parents_unchanged=protected_unchanged(workspace,internal,external,dirty),
                  scientific_invocations=1,runtime_microprobes=0)
    if not report['parents_unchanged']:
        report['status']='failed'
    save_json(root/'execution.json',report)
    save_json(root/'formal_invocation_manifest.json',package_manifest(root))
    return report
