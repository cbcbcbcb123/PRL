"""Single approved, create-only eight-case batch using the existing bounded runtime."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os
import numpy as np
from prl.fem.mixed_cube_spec import configuration,cube
from prl.result_store import result_path,result_admission
from prl.runs.fenicsx_runtime import read_docker,IMAGE,TAG,save_json,invoke_bounded
from prl.runs.fenicsx_ring import digest
from prl.runs.fem_finite_strain import scientific_lock
from prl.verification.mixed_cube import verify

RESULT=Path('results/ventricle_fem/mixed_cube_benchmark_v01_20260918')
CONTRACT='project_control/ventricle_volume_qualification_adoption_v01.md'
BATCHES={
    'v01':{'result':RESULT,'contract':CONTRACT,
        'authorization':'new_FEM_authorization: user_confirmed_eight_case_batch_20260918',
        'container':'prl-mixed-cube-benchmark-v01-20260918'},
    'v02':{'result':Path('results/ventricle_fem/mixed_cube_benchmark_v02_20260918'),
        'contract':'project_control/ventricle_mixed_cube_benchmark_v02.md',
        'authorization':'new_FEM_authorization: user_confirmed_same_eight_case_v02_20260919',
        'container':'prl-mixed-cube-benchmark-v02-20260919'}}
V01_MANIFEST='5d3c7d623c4cb80404946a7bd04f1be104296b48ab0f213bb1a5b240c4b575fb'
PREREQUISITES={
    'results/ventricle_fem/volume_projection_audit_v01_20260918':'78a9542bd69d6373a4e25f4bec421f6ea5441a49e4d5334932811201cd85628b',
    'results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918':'7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4'}
SOURCES=[CONTRACT,'src/prl/fem/mixed_cube_spec.py','src/prl/fem/mixed_material.py',
    'src/prl/fem/fenicsx_mixed_cube.py','src/prl/fem/fenicsx_ventricle.py','src/prl/fem/fenicsx_ring.py',
    'src/prl/fem/ring_geometry.py','src/prl/fem/ventricle_geometry.py','src/prl/verification/mixed_cube.py',
    'src/prl/verification/ventricle_3d.py','src/prl/verification/fenicsx_ring.py',
    'src/prl/runs/mixed_cube.py','src/prl/runs/fenicsx_runtime.py','src/prl/runs/fem_finite_strain.py',
    'src/prl/result_store.py','src/prl/storage.py','project_control/result_storage_policy.json',
    'src/prl/cli.py','tests/prl/test_mixed_cube.py','tests/prl/test_ventricle_3d.py']


def protection(workspace):
    references={}
    for identifier,expected in PREREQUISITES.items():
        root=result_path(workspace,identifier)
        if digest(root/'manifest.json')!=expected:
            raise ValueError('Frozen prerequisite manifest drift')
        entries=json.loads((root/'manifest.json').read_text(encoding='utf-8'))['files']
        for entry in entries:
            path=root/entry['path']
            if digest(path)!=entry['sha256']:
                raise ValueError('Frozen prerequisite data drift')
            references[str(path)]=entry['sha256']
        references[str(root/'manifest.json')]=expected
    parent=result_path(workspace,'results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918')
    dirty=json.loads((parent/'preexisting_changes.json').read_text(encoding='utf-8'))
    for item in dirty:
        path=workspace/item['path']
        if digest(path)!=item['sha256']:
            raise ValueError('Preexisting unrelated edit drift: '+item['path'])
        references[str(path)]=item['sha256']
    expert=workspace/'plan/active/EXP-20260918-FEM-review-v01'
    for item in json.loads((expert/'source_manifest.json').read_text(encoding='utf-8'))['files']:
        path=expert/item['path']
        if digest(path)!=item['sha256']:
            raise ValueError('Expert original drift')
        references[str(path)]=item['sha256']
    return references,len(dirty)


def batch_spec(batch):
    if batch not in BATCHES:
        raise ValueError('Only explicitly authorized batch versions are registered')
    return BATCHES[batch]


def run(workspace,batch='v01'):
    workspace=Path(workspace).resolve(strict=True)
    selected=batch_spec(batch)
    root=result_path(workspace,selected['result'],new=True)
    if selected['authorization'] not in (workspace/selected['contract']).read_text(encoding='utf-8'):
        raise ValueError('Explicit eight-case authorization missing')
    references,dirty_count=protection(workspace)
    config=configuration()
    if batch=='v02':
        previous=result_path(workspace,RESULT)
        if digest(previous/'manifest.json')!=V01_MANIFEST:
            raise ValueError('v01 frozen manifest drift')
        for item in json.loads((previous/'manifest.json').read_text(encoding='utf-8'))['files']:
            path=previous/item['path']
            if digest(path)!=item['sha256']:
                raise ValueError('v01 frozen evidence drift: '+str(path))
            references[str(path)]=item['sha256']
        references[str(previous/'manifest.json')]=V01_MANIFEST
        if config!=json.loads((previous/'configuration.json').read_text(encoding='utf-8')):
            raise ValueError('v02 must retain every v01 physical/numerical configuration field')
    sources=list(dict.fromkeys([selected['contract'],*SOURCES]))
    for name in sources:
        if name.endswith('.py'):
            ast.parse((workspace/name).read_text(encoding='utf-8'))
    admission=result_admission(workspace,256*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission blocked')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned runtime unavailable; no restart/repair/pull allowed')
    if read_docker('ps','-q'):
        raise RuntimeError('Another container is running')
    root.mkdir(parents=True,exist_ok=False); (root/'input').mkdir()
    save_json(root/'configuration.json',config); save_json(root/'docker_preflight.json',version)
    save_json(root/'storage_preflight.json',admission)
    save_json(root/'protected_inputs.json',{'files':references,'preexisting_dirty_files':dirty_count})
    for n in [2,4,8]:
        np.savez_compressed(root/'input'/f'n{n}.npz',**cube(n))
    hashes={}
    for name in sources:
        target=root/'sources_at_execution'/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(workspace/name,target); hashes[name]=digest(workspace/name)
    save_json(root/'source_hashes.json',hashes)
    save_json(root/'input_hashes.json',{p.name:digest(p) for p in (root/'input').iterdir()})
    environment=dict(os.environ,PYTHONPATH=str(workspace/'src'),PYTHONDONTWRITEBYTECODE='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    command=[sys.executable,'-B','-X','utf8','-m','pytest','-q','-p','no:cacheprovider',
             'tests/prl/test_mixed_cube.py','tests/prl/test_ventricle_3d.py','tests/prl/test_volume_projection.py']
    tests=subprocess.run(command,cwd=workspace,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=60)
    save_json(root/'tests.json',{'command':command,'stdout':tests.stdout,'stderr':tests.stderr,'exit_code':tests.returncode})
    if tests.returncode:
        raise RuntimeError('Host implementation tests failed; no container invocation')
    with scientific_lock(workspace):
        if read_docker('ps','-q'):
            raise RuntimeError('A container appeared after preflight; stop')
        execution=invoke_bounded(workspace,root,selected['container'],
            '/workspace/src/prl/fem/fenicsx_mixed_cube.py',seconds=1800)
    protected=all(digest(path)==expected for path,expected in references.items())
    sources=all(digest(workspace/name)==expected for name,expected in hashes.items())
    save_json(root/'post_protection.json',{'status':'passed' if protected and sources else 'failed',
        'protected_files':len(references),'preexisting_dirty_files':dirty_count,'source_files':len(hashes),
        'protected_unchanged':protected,'sources_unchanged':sources})
    if (root/'summary.json').exists():
        try:
            post=verify(root)
        except Exception as error:
            post={'status':'failed','reason':repr(error),'scope':'readback failed; solver outputs preserved'}
        save_json(root/'post_verification.json',post)
    else:
        post={'status':'failed','reason':'No complete solver summary; last saved states retained'}
        save_json(root/'post_verification.json',post)
    return {'status':execution['status'],'result':str(root),'execution':execution,
        'readback':post['status'],'protection':'passed' if protected and sources else 'failed',
        'qualification':post.get('qualification','unknown'),'new_container_invocations':1,'automatic_retries':0}
