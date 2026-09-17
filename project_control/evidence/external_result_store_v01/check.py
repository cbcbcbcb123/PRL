"""One create-only host/container I/O acceptance, no scientific invocation."""
from pathlib import Path
import json
import subprocess
from prl.result_store import policy,result_path,result_admission,register_result
from prl.runs.fenicsx_runtime import read_docker,container_command,verify_container_settings,save_json,IMAGE,TAG
from prl.runs.fenicsx_ring import digest,package_manifest

workspace=Path.cwd().resolve(strict=True)
evidence=workspace/'project_control/evidence/external_result_store_v01'
root=result_path(workspace,'results/_storage_checks/external_store_io_v01',new=True)
admission=result_admission(workspace,planned_new_bytes=1024**2)
if not admission['can_start']:
    raise RuntimeError('Storage admission refused')
assert read_docker('image','inspect',TAG,'--format','{{.Id}}')==IMAGE
before={p.relative_to(workspace).as_posix():digest(p) for p in (workspace/'src').rglob('*') if p.is_file()}
protected={}
for package in (workspace/'results/ventricle_fem').iterdir():
    manifest=package/'manifest.json'
    if manifest.is_file():
        for item in json.loads(manifest.read_text())['files']:
            target=package/item['path']
            if not target.resolve().is_relative_to(package.resolve()) or digest(target)!=item['sha256']:
                raise ValueError('Legacy evidence preflight failed: '+str(target))
            protected[target.relative_to(workspace).as_posix()]=digest(target)
root.mkdir(parents=True,exist_ok=False)
for sequence in [1,2]:
    with (root/f'host_round_{sequence}.json').open('x',encoding='utf-8') as handle:
        json.dump({'identity':'prl-external-result-store-v01','sequence':sequence},handle)
    assert all(digest(workspace/p)==h for p,h in before.items())
name='prl-external-results-io-v01-20260917'
args=container_command(workspace,name,'/workspace/project_control/evidence/external_result_store_v01/container_probe.py',root)
save_json(evidence/'command.json',args)
try:
    completed=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=60)
except subprocess.TimeoutExpired:
    read_docker('stop','--time','5',name)
    raise
inspection=json.loads(read_docker('inspect',name))[0]
save_json(evidence/'container_inspect.json',inspection)
settings=verify_container_settings(inspection)
roundtrip=json.loads((root/'docker_roundtrip.json').read_text())
after={p.relative_to(workspace).as_posix():digest(p) for p in (workspace/'src').rglob('*') if p.is_file()}
checks={'container_exit':completed.returncode==0,'container_settings':all(settings.values()),
        'two_host_rounds':roundtrip['rounds_read']==2,'no_scientific_solves':roundtrip['solver_calls']==0,
        'source_tree_unchanged':before==after,'legacy_evidence_unchanged':all(digest(workspace/p)==h for p,h in protected.items()),
        'outside_git':not root.is_relative_to(workspace),'actual_output_bind':any(m['Destination']=='/out' and m['RW'] and str(root).replace('\\','/').lower() in m['Source'].replace('\\','/').lower() for m in inspection['Mounts'])}
save_json(root/'manifest.json',package_manifest(root))
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'scientific_solves':0,
        'output':str(root),'legacy_files_verified':len(protected),'source_files_checked':len(before),
        'stdout':completed.stdout,'stderr':completed.stderr,'admission':admission,
        'container_name':name,'automatic_retries':0,'manifest_sha256':digest(root/'manifest.json')}
save_json(evidence/'execution.json',report)
if report['status']=='passed':
    register_result(workspace,root,'passed',report['manifest_sha256'])
print(json.dumps({k:report[k] for k in ['status','checks','scientific_solves','output','legacy_files_verified']},indent=2))
raise SystemExit(0 if report['status']=='passed' else 2)
