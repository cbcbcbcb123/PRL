"""One bounded origin fetch; never checkout, prune, delete, or push."""
import json
import os
from pathlib import Path
import subprocess
import time

from prl.storage import evaluate_storage, scan_workspace

workspace = Path.cwd().resolve()
output = workspace / 'project_control/evidence/git_main_integration_v01'
report_path = output / 'fetch_report.json'
if report_path.exists() or (output / 'fetch_stdout.log').exists():
    raise RuntimeError('Create-only fetch attempt already exists')
if subprocess.check_output(['git', 'remote', 'get-url', 'origin'], text=True).strip() != 'https://github.com/cbcbcbcb123/PRL.git':
    raise RuntimeError('Unexpected origin')
admission = evaluate_storage(scan_workspace(workspace), planned_new_bytes=192*1024**2, stop_reserve_bytes=64*1024**2)
if not admission['can_start']:
    raise RuntimeError('Storage admission refused')
git_dir = workspace / '.git'
def git_size():
    return sum(p.stat().st_size for p in git_dir.rglob('*') if p.is_file())
initial = git_size()
command = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
           '-c', 'http.lowSpeedLimit=1024', '-c', 'http.lowSpeedTime=20',
           'fetch', '--no-auto-maintenance', '--no-tags', '--no-recurse-submodules', 'origin']
environment = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
started = time.monotonic()
reason = None
with (output/'fetch_stdout.log').open('x', encoding='utf-8') as stdout, (output/'fetch_stderr.log').open('x', encoding='utf-8') as stderr:
    process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=environment)
    while process.poll() is None:
        if time.monotonic()-started > 180 or git_size()-initial > 192*1024**2:
            reason = 'time or Git growth budget exceeded'
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
            process.wait(timeout=10)
            break
        time.sleep(.5)
post = evaluate_storage(scan_workspace(workspace), planned_new_bytes=0, stop_reserve_bytes=64*1024**2)
growth = git_size()-initial
report = {'status': 'passed' if process.returncode == 0 and reason is None and post['can_start'] and growth <= 192*1024**2 else 'failed',
          'command':command, 'exit_code':process.returncode, 'stop_reason':reason,
          'elapsed_seconds':time.monotonic()-started, 'git_initial_bytes':initial,
          'git_growth_bytes':growth, 'workspace_before_bytes':admission['usage']['logical_bytes'],
          'workspace_after_bytes':post['usage']['logical_bytes'], 'budget_bytes':192*1024**2,
          'stop_reserve_bytes':64*1024**2, 'checkout':False, 'prune':False, 'push':False}
report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['status']=='passed' else 2)
