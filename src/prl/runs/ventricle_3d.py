"""One bounded create-only 3D qualification, preserving the retired 2D evidence."""
import ast
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
RESUME_RESULT=Path('results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918')
RESUME_CONTRACT='project_control/ventricle_fem_idealized_3d_resume_contract_v01.md'
RESUME_PARENT_SHA='991710ecfb62d72bca971f8254199f119518d8fe199312e1bcea7949645d3e42'
FINE_RESULT=Path('results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
FINE_CONTRACT='project_control/ventricle_fem_3d_fine_pressure_contract_v01.md'
FINE_PARENT_SHA='cb846ad96711d6706a7a9b2912ddf9100a65c2a3645e9dd7f7af14c0eafd455c'
SOURCES=[CONTRACT,'project_control/ventricle_3d_before_growth_decision_v01.md',
    'src/prl/fem/ventricle_geometry.py','src/prl/fem/fenicsx_ventricle.py','src/prl/fem/fenicsx_ring.py',
    'src/prl/fem/ring_geometry.py','src/prl/verification/ventricle_3d.py','src/prl/verification/fenicsx_ring.py',
    'src/prl/runs/ventricle_3d.py','src/prl/runs/fenicsx_runtime.py','src/prl/runs/fenicsx_contour_pressure.py',
    'src/prl/runs/fenicsx_contour.py','src/prl/runs/fenicsx_ring.py','src/prl/runs/fem_finite_strain.py',
    'src/prl/result_store.py','src/prl/storage.py','src/prl/cli.py','project_control/result_storage_policy.json',
    'tests/prl/test_ventricle_3d.py','src/prl/fem/ventricle_protocol.py']


def mechanical_identity(workspace,parent):
    """Prevent the continuation from quietly changing any physical implementation."""
    checks={}
    for relative,names,classname in [
        ('src/prl/fem/fenicsx_ventricle.py',['__init__','solve','monitor'],'VentricularSolid'),
        ('src/prl/verification/ventricle_3d.py',
         ['tetra_shape','triangle_shape','kinematics','extra_points','fields','cavity','mapping_checks','state_audit'],None)]:
        trees=[]
        for base in [Path(workspace),Path(parent)/'sources_at_delivery']:
            tree=ast.parse((base/relative).read_text(encoding='utf-8'))
            if classname:
                tree=next(item for item in tree.body if isinstance(item,ast.ClassDef) and item.name==classname)
            trees.append({item.name:ast.dump(item,include_attributes=False) for item in tree.body
                          if isinstance(item,ast.FunctionDef)})
        for name in names:
            checks[relative+':'+name]=name in trees[0] and trees[0][name]==trees[1].get(name)
    for relative in ['src/prl/fem/ventricle_geometry.py','src/prl/fem/fenicsx_ring.py',
                     'src/prl/runs/fenicsx_runtime.py']:
        checks[relative]=digest(Path(workspace)/relative)==digest(Path(parent)/'sources_at_delivery'/relative)
    return checks


def resume_configuration(parent):
    cfg=json.loads((Path(parent)/'configuration.json').read_text())
    if cfg!=configuration():
        raise ValueError('Original scientific configuration changed')
    return {**cfg,'reuse_m0_zero':True,'maximum_equilibrium_solves':13}


def fine_pressure_configuration(parent):
    previous=json.loads((Path(parent)/'configuration.json').read_text())
    cfg=configuration()
    if previous!={**cfg,'reuse_m0_zero':True,'maximum_equilibrium_solves':13}:
        raise ValueError('Original scientific configuration changed')
    return {**cfg,'meshes':[cfg['meshes'][1]],'states':cfg['states'][:2],
            'maximum_equilibrium_solves':2,'diagnostic_scope':'M1 zero and first pressure only'}


def run(workspace,*,resume=False,fine_pressure=False):
    if resume and fine_pressure:
        raise ValueError('Choose one explicitly authorized slice')
    workspace=Path(workspace).resolve(strict=True)
    root=result_path(workspace,FINE_RESULT if fine_pressure else RESUME_RESULT if resume else RESULT,new=True)
    parent=result_path(workspace,RESUME_RESULT if fine_pressure else RESULT if resume else PARENT)
    contract=FINE_CONTRACT if fine_pressure else RESUME_CONTRACT if resume else CONTRACT
    expected_sha=FINE_PARENT_SHA if fine_pressure else RESUME_PARENT_SHA if resume else PARENT_SHA
    if not (workspace/contract).is_file() or digest(parent/'manifest.json')!=expected_sha:
        raise ValueError('Contract or frozen ancestor identity mismatch')
    parent_manifest=json.loads((parent/'manifest.json').read_text())
    if not all(digest(parent/f['path'])==f['sha256'] for f in parent_manifest['files']):
        raise ValueError('Frozen ancestor changed')
    internal=json.loads((parent/'protected_preflight.json').read_text())
    external=json.loads((parent/'external_protected_preflight.json').read_text())
    external.update({str(p):digest(p) for p in parent.rglob('*') if p.is_file()})
    dirty=json.loads((parent/'preexisting_changes.json').read_text())
    if not protected_unchanged(workspace,internal,external,dirty):
        raise ValueError('Protected ancestors/unrelated edits changed')
    cfg=fine_pressure_configuration(parent) if fine_pressure else resume_configuration(parent) if resume else configuration()
    identity=mechanical_identity(workspace,parent) if resume or fine_pressure else {}
    if resume and (not all(identity.values()) or
                   json.loads((parent/'interface_diagnosis.json').read_text())['status']!='passed'):
        raise ValueError('Mechanical identity or retained-zero diagnosis rejected')
    if fine_pressure:
        for relative in ['src/prl/fem/fenicsx_ventricle.py','src/prl/verification/ventricle_3d.py',
                         'src/prl/fem/ventricle_protocol.py']:
            identity[relative]=digest(workspace/relative)==digest(parent/'sources_at_delivery'/relative)
        if not all(identity.values()) or json.loads((parent/'restart_interface.json').read_text())['status']!='passed':
            raise ValueError('Fine probe changed mechanics or parent interface')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned runtime unavailable; no repair/pull/restart authorized')
    if read_docker('ps','-q'):
        raise RuntimeError('Another container is running')
    admission=result_admission(workspace,768*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage refused')
    geometries=[]
    for case in cfg['meshes']:
        if resume or fine_pressure:
            with np.load(parent/'input'/f'{case["name"]}_geometry.npz',allow_pickle=False) as saved:
                data={k:saved[k] for k in saved.files}
        else:
            data=half_ellipsoid(case,cfg)
        metrics=geometry_metrics(data,cfg,case['name'])
        if metrics['status']!='passed':
            raise ValueError('Geometry qualification rejected before scientific run')
        geometries.append((case['name'],data,metrics))
    root.mkdir(parents=True,exist_ok=False); (root/'input').mkdir()
    for filename,value in [('configuration.json',cfg),('docker_version.json',version),
        ('storage_preflight.json',admission),('protected_preflight.json',internal),
        ('external_protected_preflight.json',external),('preexisting_changes.json',dirty)]:
        save_json(root/filename,value)
    for name,data,metrics in geometries:
        if resume or fine_pressure:
            for extension in ['npz','json']:
                filename=f'{name}_geometry.{extension}'
                shutil.copyfile(parent/'input'/filename,root/'input'/filename)
        else:
            np.savez_compressed(root/'input'/f'{name}_geometry.npz',**data)
            save_json(root/'input'/f'{name}_geometry.json',metrics)
    copies=[(parent/'manifest.json',root/'prerequisite/parent_manifest.json'),
            (parent/'summary.json',root/'prerequisite/parent_summary.json')]
    sources=SOURCES+([RESUME_CONTRACT] if resume else [])
    if fine_pressure:
        sources += [FINE_CONTRACT,'src/prl/verification/ventricle_mesh_probe.py','tests/prl/test_ventricle_mesh_probe.py']
        save_json(root/'mechanical_identity.json',{'status':'passed','checks':identity})
        copies.extend((parent/'raw'/filename,root/'retained'/filename) for filename in
            ['M0_mesh.npz','M0_state_pressure_1.npz','M0_state_pressure_1.json'])
        copies.extend((parent/'retained'/filename,root/'retained'/filename) for filename in
            ['M0_state_zero.npz','M0_state_zero.json'])
        copies.extend((parent/filename,root/'prerequisite'/filename) for filename in
            ['failure.json','offline_diagnosis.json','post_verification.json'])
    if resume:
        save_json(root/'mechanical_identity.json',{'status':'passed','checks':identity})
        copies.extend((parent/'raw'/filename,root/'retained'/filename) for filename in
                      ['M0_mesh.npz','M0_state_zero.npz','M0_state_zero.json'])
        copies.extend((p,root/'retained/iterates/M0_zero'/p.name)
                      for p in (parent/'iterates/M0_zero').iterdir() if p.is_file())
        copies.extend((parent/filename,root/'prerequisite'/filename) for filename in
                      ['interface_diagnosis.json','failure.json'])
    copies.extend((workspace/p,root/'sources_at_execution'/p) for p in sources)
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
    save_json(root/'source_hashes.json',{p:digest(workspace/p) for p in sources})
    save_json(root/'input_identities.json',{p.relative_to(root).as_posix():digest(p)
        for p in (root/'input').iterdir()})
    with scientific_lock(workspace):
        name='prl-f6s2r-idealized-3d-resume-v01-20260918' if resume else 'prl-f6s2-idealized-3d-v01-20260918'
        if fine_pressure:
            name='prl-f6s2d1-3d-fine-pressure-v01-20260918'
        report=invoke_bounded(workspace,root,name,
            '/workspace/src/prl/fem/fenicsx_ventricle.py',seconds=cfg['resources']['seconds'])
    report.update(parents_unchanged=protected_unchanged(workspace,internal,external,dirty),
                  scientific_invocations=1,runtime_microprobes=0)
    if not report['parents_unchanged']:
        report['status']='failed'
    save_json(root/'execution.json',report)
    save_json(root/'formal_invocation_manifest.json',package_manifest(root))
    return report
