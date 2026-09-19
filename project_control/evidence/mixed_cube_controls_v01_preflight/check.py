"""Offline delivery integrity for a runtime-blocked control batch; never starts Docker."""
import json
from pathlib import Path
from prl.fem.mixed_cube_spec import guarded_configuration,control_configuration
from prl.runs.mixed_cube import protection
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json
from prl.result_store import result_path,result_admission
from prl.cockpit import render_cockpit,validate_cockpit_links

workspace=Path.cwd(); target=Path(__file__).parent
references,dirty=protection(workspace)
parents={
    'mixed_cube_benchmark_v01_20260918':'5d3c7d623c4cb80404946a7bd04f1be104296b48ab0f213bb1a5b240c4b575fb',
    'mixed_cube_benchmark_v02_20260918':'c59044955f3609509f8b8c61d620384ae800f9e2cebfa469d005cd61a9aaedda',
    'mixed_cube_benchmark_v03_20260919':'084a675f13501added2e056f5bc3cca125a2298f09d290240282fc2b570b77b0',
    'mixed_cube_load_diagnosis_v01_20260919':'fae715c181ee24be5ca384e6a43c0257fa52ffcad1d34c5a6a0a58e85652fac1'}
for name,expected in parents.items():
    folder=result_path(workspace,'results/ventricle_fem/'+name)
    assert digest(folder/'manifest.json')==expected
    references[str(folder/'manifest.json')]=expected
    for item in json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['files']:
        path=folder/item['path']; assert digest(path)==item['sha256']
        references[str(path)]=item['sha256']
original=result_path(workspace,'results/ventricle_fem/mixed_cube_benchmark_v03_20260919')
assert guarded_configuration()==json.loads((original/'configuration.json').read_text())
native=result_path(workspace,'results/ventricle_fem/mixed_cube_controls_v01_20260919',new=True)
assert not native.exists(), 'This checker is only for the pre-container blocked snapshot'
render=render_cockpit(workspace); links=validate_cockpit_links(workspace)
assert render['status']==links['status']=='passed'
sources=['src/prl/fem/mixed_cube_spec.py','src/prl/fem/fenicsx_mixed_cube.py',
    'src/prl/verification/mixed_cube.py','src/prl/runs/mixed_cube.py','src/prl/cli.py',
    'src/prl/fem/mixed_material.py','src/prl/fem/positive_j.py',
    'tests/prl/test_mixed_cube.py','tests/prl/test_mixed_cube_controls.py']
save_json(target/'configuration.json',control_configuration())
save_json(target/'integrity.json',{'status':'passed','scope':'host preparation and blocked preflight, not native science',
    'source_sha256':{name:digest(workspace/name) for name in sources},
    'original_v03_configuration_unchanged':True,'protected_files':len(references),
    'preexisting_dirty_files_unchanged':dirty,'frozen_parent_manifests':parents,
    'native_result_created':False,'container_invocations':0,'equilibrium_solves':0,
    'render':render,'links':links,'storage':result_admission(workspace,128*1024**2,64*1024**2)})
print(json.dumps({'status':'passed','protected_files':len(references),'unrelated_dirty':dirty,
    'native_cases':'not_run','links':links['status']}))
