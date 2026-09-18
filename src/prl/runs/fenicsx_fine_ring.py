"""Two explicitly bounded phases: native negative control, then fine-only recovery."""
import json
from pathlib import Path
import shutil
import subprocess
import time

from prl.result_store import result_path,result_admission,disk_admission
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fenicsx_ring import digest,package_manifest
from prl.runs.fenicsx_pressure import PASSIVE_RESULT,configuration as passive_configuration
from prl.runs.fenicsx_runtime import read_docker,IMAGE,TAG,container_command,save_json,verify_container_settings

RESULT=Path('results/ventricle_fem/f6s1s6_fine_ring_v01_20260918')
CONTRACT=Path('project_control/ventricle_fem_fine_ring_recovery_contract_v01.md')
SOURCES=['src/prl/fem/fenicsx_ring.py','src/prl/fem/fenicsx_pressure.py','src/prl/fem/fenicsx_zero_newton.py',
         'src/prl/fem/ring_geometry.py','src/prl/verification/fenicsx_ring.py','src/prl/verification/fenicsx_pressure.py',
         'src/prl/runs/fenicsx_fine_ring.py','src/prl/runs/fenicsx_pressure.py','src/prl/runs/fenicsx_runtime.py',
         'src/prl/runs/fenicsx_ring.py','src/prl/runs/fem_finite_strain.py','src/prl/result_store.py',CONTRACT.as_posix()]


def configuration():
    config=passive_configuration(complete_passive_ring=True)
    config.update(fine_passive_only=True,diagnostic_trace=True,execution_plan={'M0':[],'M1':[0,1,2,3,4]},
        maximum_equilibrium_solves=5,scope='only five original fine passive states; coarse retained, no time/biology claims')
    return config


def unchanged(workspace,root):
    internal=json.loads((root/'protected_preflight.json').read_text())
    external=json.loads((root/'external_protected_preflight.json').read_text())
    dirty=json.loads((root/'preexisting_changes.json').read_text())
    return all(digest(workspace/path)==sha for path,sha in internal.items()) and all(digest(path)==sha for path,sha in external.items()) and all(digest(workspace/item['path'])==item['sha256'] for item in dirty)


def snapshot(workspace,root,phase):
    folder=root/('sources_at_'+phase); folder.mkdir(exist_ok=False)
    for relative in SOURCES:
        target=folder/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(workspace/relative,target)
    save_json(root/('source_hashes_'+phase+'.json'),{relative:digest(workspace/relative) for relative in SOURCES})


def invoke(workspace,output,phase,seconds):
    name='prl-f6s1s6-'+phase+'-v01-20260918'
    script='fenicsx_zero_newton.py' if phase=='diagnose' else 'fenicsx_pressure.py'
    args=container_command(workspace,name,'/workspace/src/prl/fem/'+script,output)
    save_json(output/'command.json',args)
    save_json(output/'started.json',{'container':name,'phase':phase,'invocations':1,'automatic_retries':0})
    started=time.monotonic(); stop=None
    with (output/'stdout.log').open('x',encoding='utf-8') as stdout,(output/'stderr.log').open('x',encoding='utf-8') as stderr:
        process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
        try:
            while process.poll() is None:
                if time.monotonic()-started>seconds or not disk_admission(output,0)['can_start']:
                    stop='time_or_disk_limit'; read_docker('stop','--time','5',name); process.wait(timeout=20); break
                time.sleep(.5)
        except BaseException:
            read_docker('stop','--time','5',name); process.wait(timeout=20); raise
    inspection=json.loads(read_docker('inspect',name))[0]
    settings=verify_container_settings(inspection)
    save_json(output/'container_inspect.json',inspection)
    report={'status':'passed' if process.returncode==0 and all(settings.values()) and stop is None else 'failed',
            'exit_code':process.returncode,'stop_reason':stop,'container_checks':settings,
            'OOMKilled':inspection['State']['OOMKilled'],'elapsed_seconds':time.monotonic()-started,'gpu':0,'automatic_retries':0}
    save_json(output/'execution.json',report)
    return report


def assess_native(root):
    root=Path(root); target=root/'native_probe'
    calls_path=target/'legacy/calls.jsonl'
    calls=[json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
    returned=next((r for r in calls if r['event']=='solve_return'),{})
    factor=next((r for r in calls if r['event']=='get_factor_return'),{})
    reasons=next((r for r in calls if r['event']=='get_reasons_return'),{})
    execution=json.loads((target/'execution.json').read_text())
    stderr=(target/'stderr.log').read_text()
    checks={'zero_newton_converged':returned.get('iterations')==0 and returned.get('snes_reason',0)>0,
            'KSP_not_run':reasons.get('ksp_reason')==0 and reasons.get('pc_reason')==0,
            'factor_query_returned':factor.get('factor_exists') is True and factor.get('handle',0)>0,
            'crash_at_infog':bool(calls) and calls[-1]['event']=='get_infog_enter' and ('signal number 11' in stderr or 'Segmentation' in stderr),
            'expected_native_failure':execution['exit_code']!=0 and not execution['OOMKilled'] and execution['stop_reason'] is None,
            'controlled_runtime':all(execution['container_checks'].values())}
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,'negative_control_execution':execution['status'],
            'conclusion':'Confirmed MUMPS INFOG access crash after zero-Newton convergence without a KSP solve; a non-null matrix wrapper is insufficient' if all(checks.values()) else 'Native call-site hypothesis not established; stop before science',
            'rejected_hypothesis':'Null PETSc Mat wrapper: actual wrapper exists; do not equate its existence with completed factorization',
            'scientific_equilibria':0,'last_call':calls[-1] if calls else None}


def run_fine_ring(workspace,phase):
    workspace=Path(workspace).resolve(strict=True)
    if phase not in ('diagnose','complete'):
        raise ValueError('Only the two explicitly authorized phases exist')
    try:
        root=result_path(workspace,RESULT,new=phase=='diagnose')
        resume_preflight=False
    except FileExistsError:
        root=result_path(workspace,RESULT)
        expected={'protected_preflight.json','external_protected_preflight.json','preexisting_changes.json','preflight_error.json'}
        if phase!='diagnose' or not (root/'preflight_error.json').is_file() or {p.name for p in root.iterdir()}!=expected:
            raise
        error=json.loads((root/'preflight_error.json').read_text())
        if error.get('native_invocations')!=0 or error.get('scientific_invocations')!=0 or not unchanged(workspace,root):
            raise ValueError('Only exact intact unstarted preflight can be resumed')
        resume_preflight=True
    if phase=='complete' and (root/'started.json').exists():
        raise FileExistsError('Fine scientific invocation already consumed; no automatic retry')
    if not (workspace/CONTRACT).is_file():
        raise ValueError('Explicit recovery contract required')
    version=json.loads(read_docker('version','--format','{{json .}}'))
    if not version.get('Server') or read_docker('image','inspect',TAG,'--format','{{.Id}}')!=IMAGE:
        raise RuntimeError('Pinned local runtime unavailable; no repair, restart, install or pull')
    admission=result_admission(workspace,256*1024**2,64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    if phase=='diagnose':
        parent=result_path(workspace,PASSIVE_RESULT)
        manifest=json.loads((parent/'manifest.json').read_text())
        if not all(digest(parent/item['path'])==item['sha256'] for item in manifest['files']):
            raise ValueError('Frozen parent changed')
        summary=json.loads((parent/'summary.json').read_text())
        if summary['coarse_pressure_sequence']!='passed':
            raise ValueError('Retained complete coarse prerequisite not passed')
        root.mkdir(parents=True,exist_ok=resume_preflight)
        for filename in ['protected_preflight.json','preexisting_changes.json']:
            if not resume_preflight:
                shutil.copyfile(parent/filename,root/filename)
        external=json.loads((parent/'external_protected_preflight.json').read_text())
        external.update({str(path):digest(path) for path in parent.rglob('*') if path.is_file()})
        if not resume_preflight:
            save_json(root/'external_protected_preflight.json',external)
        if not unchanged(workspace,root):
            raise ValueError('Ancestor or unrelated work drift')
        save_json(root/'configuration.json',configuration()); save_json(root/'storage_preflight.json',admission)
        save_json(root/'docker_version.json',version)
        snapshot(workspace,root,'diagnosis')
        target=root/'native_probe'; target.mkdir()
        shutil.copyfile(root/'configuration.json',target/'configuration.json')
        with scientific_lock(workspace):
            invoke(workspace,target,phase,180)
        report=assess_native(root); report['parents_unchanged']=unchanged(workspace,root)
        if not report['parents_unchanged']:
            report['status']='failed'
        save_json(root/'native_diagnosis.json',report)
        save_json(root/'negative_control_manifest.json',package_manifest(root))
        return report
    report=json.loads((root/'native_diagnosis_review.json').read_text())
    frozen=json.loads((root/'negative_control_manifest.json').read_text())
    if report['status']!='passed' or not unchanged(workspace,root) or not all(digest(root/item['path'])==item['sha256'] for item in frozen['files']):
        raise ValueError('Confirmed negative control and unchanged parents required')
    parent=result_path(workspace,PASSIVE_RESULT)
    retained=root/'retained_passive'; retained.mkdir(exist_ok=False)
    for filename in ['configuration.json','post_verification.json']:
        shutil.copyfile(parent/filename,retained/('verification.json' if filename=='post_verification.json' else filename))
    for index in range(5):
        for extension in ['npz','json']:
            filename=f'M0_state_passive_{index}.{extension}'
            shutil.copyfile(parent/('retained_passive' if index<2 else 'ring/raw')/filename,retained/filename)
    shutil.copyfile(parent/'ring/raw/M0_mesh.npz',retained/'M0_mesh.npz')
    raw=root/'ring/raw'; raw.mkdir(parents=True,exist_ok=False)
    for name in ['M0_mesh.npz','M0_geometry.json','M0_tangent.json','M1_mesh.npz']:
        shutil.copyfile(parent/'ring/raw'/name,(root/'retained_M1_mesh.npz') if name=='M1_mesh.npz' else raw/name)
    shutil.copytree(parent/'comparison',root/'comparison')
    snapshot(workspace,root,'execution')
    save_json(root/'science_storage_preflight.json',admission)
    with scientific_lock(workspace):
        execution=invoke(workspace,root,phase,1200)
    execution['parents_unchanged']=unchanged(workspace,root)
    if not execution['parents_unchanged']:
        execution['status']='failed'
    execution.update(scientific_invocations=1,diagnostic_invocations=1)
    save_json(root/'execution.json',execution)
    save_json(root/'formal_invocation_manifest.json',package_manifest(root))
    return execution
