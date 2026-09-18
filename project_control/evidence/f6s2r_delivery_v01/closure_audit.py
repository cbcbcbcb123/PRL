"""Read-only scientific delivery checks and regenerated navigation, no new solve."""
import json
from pathlib import Path
import subprocess
from prl.cockpit import render_cockpit,validate_cockpit_links
from prl.result_store import result_admission
from prl.runs.fenicsx_contour_pressure import protected_unchanged
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json

workspace=Path(__file__).resolve().parents[3]; evidence=Path(__file__).parent
root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918')
render_cockpit(workspace); navigation=validate_cockpit_links(workspace)
save_json(evidence/'navigation_validation.json',navigation)
manifest=json.loads((root/'manifest.json').read_text())
internal=json.loads((root/'protected_preflight.json').read_text())
external=json.loads((root/'external_protected_preflight.json').read_text())
dirty=json.loads((root/'preexisting_changes.json').read_text()); protected={item['path'] for item in dirty}
allowed={'START_HERE.md','project_control/CURRENT_STATUS.md','memory/project_cockpit/status.json',
    'memory/project_cockpit/task_log.jsonl','project_control/evidence/f6s2r_delivery_v01/closure_audit.py',
    'project_control/evidence/f6s2r_delivery_v01/closure_audit.json',
    'project_control/evidence/f6s2r_delivery_v01/navigation_validation.json'}
def git(*args):
    return subprocess.check_output(['git',*args],cwd=workspace).decode('utf-8')
paths={entry[3:].replace('\\','/') for entry in git('status','--porcelain=v1','-z','--untracked-files=all').split('\0') if entry}
all_files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
expected={item['path'] for item in manifest['files']}
snapshots=root/'sources_at_delivery'; source_paths=[p for p in snapshots.rglob('*') if p.is_file()]
storage=result_admission(workspace,0)
checks={
    'manifest_identity':digest(root/'manifest.json')=='cb846ad96711d6706a7a9b2912ddf9100a65c2a3645e9dd7f7af14c0eafd455c',
    'manifest_exact_coverage':all_files==expected|{'manifest.json'},
    'all_manifest_hashes':all(digest(root/f['path'])==f['sha256'] for f in manifest['files']),
    'protected_evidence_and_dirty':protected_unchanged(workspace,internal,external,dirty),
    'delivery_sources_match':all(digest(p)==digest(workspace/p.relative_to(snapshots)) for p in source_paths),
    'strict_navigation':navigation['status']=='passed',
    'git_exact_scope':not paths-protected-allowed,'original_dirty_set_present':protected<=paths,
    'branch_main':git('branch','--show-current').strip()=='main',
    'index_empty':not git('diff','--cached','--name-only').strip(),'storage':storage['can_start'],
}
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
    'unexpected_git_paths':sorted(paths-protected-allowed),'task_git_paths':sorted(paths-protected),
    'checked_commit':git('rev-parse','HEAD').strip(),'result_files':len(all_files),'manifest_entries':len(expected),
    'result_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
    'protected_files':len(internal)+len(external),'dirty_files':len(dirty),
    'repository_bytes':storage['repository']['usage']['logical_bytes'],
    'scientific_status':'failed','native_restart_interface':'passed','new_scientific_solves':0,
    'result_manifest_sha256':digest(root/'manifest.json')}
save_json(evidence/'closure_audit.json',report); print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
