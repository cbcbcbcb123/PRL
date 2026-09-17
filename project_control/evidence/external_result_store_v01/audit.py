"""Read/hash-only acceptance; writes only this task's small audit report."""
from pathlib import Path
import json
import subprocess

from prl.cockpit import validate_cockpit_links
from prl.result_store import result_admission,policy
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json


workspace=Path.cwd().resolve(strict=True)
evidence=workspace/'project_control/evidence/external_result_store_v01'
baseline=json.loads((workspace/'project_control/evidence/git_main_integration_v01/preflight_manifest.json').read_text(encoding='utf-8'))
protected={item['path']:item['sha256'] for item in baseline['files'] if item['path'] in baseline['excluded']}
legacy_drift=[p for p,h in protected.items() if not (workspace/p).is_file() or digest(workspace/p)!=h]
result_files={}
manifest_hashes={}
for package in (workspace/'results/ventricle_fem').iterdir():
    manifest=package/'manifest.json'
    if not manifest.is_file():
        continue
    manifest_hashes[manifest.relative_to(workspace).as_posix()]=digest(manifest)
    for item in json.loads(manifest.read_text())['files']:
        target=package/item['path']
        if not target.resolve().is_relative_to(package.resolve()):
            raise ValueError('Manifest path escape: '+str(target))
        result_files[target.relative_to(workspace).as_posix()]=item['sha256']
result_drift=[p for p,h in result_files.items() if not (workspace/p).is_file() or digest(workspace/p)!=h]
_,store=policy(workspace)
index=json.loads((workspace/'project_control/result_index/external_store_io_v01.json').read_text())
external=store/index['store_relative_path']
external_manifest=external/'manifest.json'
external_ok=digest(external_manifest)==index['manifest_sha256']
external_ok=external_ok and all(digest(external/item['path'])==item['sha256']
                             for item in json.loads(external_manifest.read_text())['files'])
links=validate_cockpit_links(workspace)
admission=result_admission(workspace)
branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
checks={'fifty_unrelated_files_unchanged':len(protected)==50 and not legacy_drift,
        'existing_fem_manifests_valid':not result_drift,
        'external_index_and_manifest_valid':external_ok,'cockpit_links':links['status']=='passed',
        'storage_admission':admission['can_start'],'main_branch':branch=='main',
        'existing_lock_preserved':(workspace/'project_control/fem_scientific_execution.lock').is_file()}
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'protected_unrelated_files':len(protected),'legacy_drift':legacy_drift,
        'fem_files_verified':len(result_files),'fem_drift':result_drift,
        'fem_manifest_sha256':manifest_hashes,'cockpit':links,
        'storage':{'repository_bytes':admission['repository']['usage']['logical_bytes'],
                   'external_result_bytes':admission['usage']['logical_bytes'],
                   'disk_free_bytes':admission['disk_free_bytes'],
                   'fixed_stage_limit_bytes':admission['fixed_stage_limit_bytes']},
        'scientific_solves':0,'deletions':0,'old_result_moves':0,'automatic_retries':0}
save_json(evidence/'delivery_audit.json',report)
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='passed' else 2)
