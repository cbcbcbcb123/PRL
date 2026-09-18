"""Read-only evidence/git checks; writes only this task's audit record."""
import json
from pathlib import Path
import subprocess

from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.result_store import result_admission
from prl.runs.fenicsx_runtime import save_json

workspace=Path(__file__).resolve().parents[3]
root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918')
evidence=Path(__file__).parent
manifest=json.loads((root/'manifest.json').read_text())
internal=json.loads((root/'protected_preflight.json').read_text())
external=json.loads((root/'external_protected_preflight.json').read_text())
dirty=json.loads((root/'preexisting_changes.json').read_text())
protected={item['path'] for item in dirty}
allowed={
    'src/prl/cli.py','src/prl/fem/fenicsx_contour_pressure.py','src/prl/runs/fenicsx_contour_pressure.py',
    'src/prl/verification/fenicsx_pressure.py','src/prl/verification/fenicsx_contour_active.py',
    'src/prl/verification/contour_boundary.py','src/prl/rendering/fenicsx_contour_pressure.py',
    'src/prl/rendering/fenicsx_contour_active.py','tests/prl/test_fenicsx_contour_active.py',
    'tests/prl/test_fenicsx_contour_pressure_render.py','project_control/ventricle_fem_contour_active_contract_v01.md',
    'project_control/ventricle_fem_contour_active_execution_v01.md',
    'project_control/result_index/f6s1s9_contour_active_v01_20260918.json',
    'project_control/evidence/f6s1s9_delivery_v01/tests_before_run.json',
    'project_control/evidence/f6s1s9_delivery_v01/finalization.json',
    'project_control/evidence/f6s1s9_delivery_v01/closure_audit.py',
    'project_control/evidence/f6s1s9_delivery_v01/closure_audit.json',
    'project_control/evidence/f6s1s9_delivery_v01/navigation_validation.json',
    'START_HERE.md','project_control/CURRENT_STATUS.md','memory/project_cockpit/status.json','memory/project_cockpit/task_log.jsonl'}
def git(*arguments):
    return subprocess.check_output(['git',*arguments],cwd=workspace).decode('utf-8')
paths={entry[3:].replace('\\','/') for entry in git('status','--porcelain=v1','-z','--untracked-files=all').split('\0') if entry}
all_files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
manifest_files={item['path'] for item in manifest['files']}
storage=result_admission(workspace,0)
checks={
    'manifest_identity':digest(root/'manifest.json')=='80b0ecbe6bd35e6d00479fbeb1e424c89969e862a01bdb0885bb43dab9734c2b',
    'manifest_all_files':all_files==manifest_files|{'manifest.json'},
    'manifest_hashes':all(digest(root/item['path'])==item['sha256'] for item in manifest['files']),
    'protected_evidence_and_dirty':protected_unchanged(workspace,internal,external,dirty),
    'exact_task_git_scope':not paths-protected-allowed,
    'original_dirty_set_present':protected<=paths,
    'branch_main':git('branch','--show-current').strip()=='main',
    'index_empty':not git('diff','--cached','--name-only').strip(),
    'storage':storage['can_start'],
    'science_sources_unchanged':all(digest(workspace/path)==sha for path,sha in json.loads((root/'source_hashes.json').read_text()).items())}
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
    'unexpected_git_paths':sorted(paths-protected-allowed),'remaining_task_git_paths':sorted(paths-protected),
    'result_files':len(all_files),'manifest_entries':len(manifest_files),
    'result_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
    'protected_files':len(internal)+len(external),'dirty_files':len(dirty),
    'repository_bytes':storage['repository']['usage']['logical_bytes'],'checked_commit':git('rev-parse','HEAD').strip(),
    'result_manifest_sha256':digest(root/'manifest.json'),'new_scientific_solves':0}
save_json(evidence/'closure_audit.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
