"""Preserve one authorized Docker startup failure. Read-only probes; no start or repair."""
import json
from pathlib import Path
import subprocess
from prl.runs.mixed_cube import protection
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json
from prl.fem.mixed_cube_spec import control_configuration
from prl.result_store import result_path

workspace=Path.cwd(); target=Path(__file__).parent
if (target/'startup.json').exists() or (target/'backend_failure.log').exists():
    raise FileExistsError('Create-only failure evidence; never repeat a startup')
prior=json.loads((target.parent/'mixed_cube_controls_v01_preflight/integrity.json').read_text())
references,dirty=protection(workspace)
for name,expected in prior['frozen_parent_manifests'].items():
    parent=result_path(workspace,'results/ventricle_fem/'+name)
    assert digest(parent/'manifest.json')==expected
    references[str(parent/'manifest.json')]=expected
    for item in json.loads((parent/'manifest.json').read_text())['files']:
        path=parent/item['path']; assert digest(path)==item['sha256']
        references[str(path)]=item['sha256']
source_checks={name:digest(workspace/name)==expected for name,expected in prior['source_sha256'].items()}
assert all(source_checks.values())
assert control_configuration()==json.loads((target.parent/'mixed_cube_controls_v01_preflight/configuration.json').read_text())
root=result_path(workspace,'results/ventricle_fem/mixed_cube_controls_v01_20260919',new=True)
assert not root.exists()
log=Path('C:/Users/chenb/AppData/Local/Docker/log/host/com.docker.backend.exe.log')
snapshot=log.read_bytes(); text=snapshot.decode('utf-8')
selected=[(index+1,line) for index,line in enumerate(text.splitlines())
    if line.startswith('[2026-09-19T10:06:') and 'initializing Ingest server:' in line
    and any(phrase in line for phrase in ['backend cancelling with error:','backend crashed,','reporting error to user:'])]
assert len(selected)==3 and all('sailor-ingest.sock' in line and 'The file cannot be accessed by the system.' in line for _,line in selected)
excerpt='\n'.join(line for _,line in selected)+'\n'
(target/'backend_failure.log').write_text(excerpt,encoding='utf-8')
probe=subprocess.run(['docker','version','--format','{{json .}}'],capture_output=True,text=True,encoding='utf-8',timeout=20)
parsed=json.loads(probe.stdout)
assert parsed['Server'] is None, 'Engine state changed externally; do not make a stale failure claim'
inventory=[{'path':name,'bytes':0,'attributes':'Archive, ReparsePoint',
    'pre_start_acl_error':'Method failed with unexpected error code 1920.'} for name in [
    'C:/Users/chenb/AppData/Local/Docker/run/dockerEthernetVfkit',
    'C:/Users/chenb/AppData/Local/Docker/run/dockerInference',
    'C:/Users/chenb/AppData/Local/Docker/run/sailor-ingest.sock',
    'C:/Users/chenb/AppData/Local/Docker/run/userAnalyticsOtlpHttp.sock',
    'C:/Users/chenb/AppData/Local/docker-secrets-engine/engine.sock']]
import hashlib
report={'status':'failed','scope':'one authorized normal Docker startup, not an FEM solve',
    'authorization':'User agreed to start installed Docker Desktop once; no repair/install/pull; continue original controls only if ready.',
    'start_invocations':1,'start_recorded_at':'2026-09-19T18:06:25.9411325+08:00',
    'executable':'C:/Program Files/Docker/Docker/Docker Desktop.exe','launch_process_id':22412,
    'startup_method':'PowerShell Start-Process -WindowStyle Hidden -PassThru',
    'pre_start_processes':[],'pre_start_wsl':'docker-desktop Stopped, version 2',
    'socket_inventory':inventory,'backend_log_path':str(log),
    'backend_log_snapshot_bytes':len(snapshot),'backend_log_snapshot_sha256':hashlib.sha256(snapshot).hexdigest(),
    'excerpt_source_lines':[number for number,_ in selected],
    'excerpt_sha256':digest(target/'backend_failure.log'),
    'confirmed_failure':'Ingest socket startup/rename failed; backend reported crash before Linux engine became ready.',
    'fundamental_socket_corruption_cause':'unknown',
    'read_only_version_probe':{'exit_code':probe.returncode,'stdout':parsed,'stderr':probe.stderr},
    'post_failure_ui_backend_processes_observed':True,
    'processes_terminated_by_agent':0,'runtime_repairs':0,'path_moves':0,'deletions':0,
    'installs_updates_pulls_by_agent':0,'automatic_retries':0,'GPU':0,
    'container_invocations':0,'equilibrium_solves':0,'result_created':False,
    'four_cases':'not_run','four_case_compute_authority_consumed':False,'one_start_authority_consumed':True,
    'next_boundary':'Stop startup/repair attempts. A separate runtime-recovery decision is required; no more directory rotation automatically.',
    'integrity':{'status':'passed','protected_files':len(references),'unrelated_dirty_files':dirty,
        'original_control_configuration_unchanged':True,'source_checks':source_checks},
    'copied_entire_docker_log':False}
save_json(target/'startup.json',report)
print(json.dumps({'startup':'failed','evidence':'passed','protected_files':len(references),
    'container_invocations':0,'equilibrium_solves':0,'excerpt_lines':len(selected)}))
