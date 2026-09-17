"""Bounded local-image Docker adapter; no pulls, deletion or host FEM installs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time

from prl.storage import evaluate_storage, scan_workspace

IMAGE = 'sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8'
TAG = 'dolfinx/dolfinx:v0.11.0'
RESULT = Path('results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917')


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def read_docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True,
                            encoding='utf-8', timeout=20, check=True)
    return result.stdout.strip()


def container_command(workspace, name, script, output=None):
    args = ['docker', 'run', '--pull=never', '--name', name, '--network=none',
            '--cpus=1', '--memory=8g', '--memory-swap=8g', '--pids-limit=256',
            '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--log-driver=none', '--ipc=private',
            '--mount', f'type=bind,source={workspace},target=/workspace,readonly',
            '--tmpfs', '/root/.cache:rw,exec,nosuid,nodev,size=536870912',
            '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=268435456']
    if output is not None:
        args += ['--mount', f'type=bind,source={output},target=/out']
        # Preserve the pinned image's verified DOLFINx library path (G0 evidence).
        args += ['--env', 'PYTHONPATH=/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:']
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        args += ['--env', key+'=1']
    args += ['--env', 'PYTHONDONTWRITEBYTECODE=1', IMAGE, 'python3', '-B', script]
    return args


def verify_container_settings(inspect):
    host = inspect['HostConfig']
    return {
        'image_identity': inspect['Image'] == IMAGE,
        'single_cpu': host['NanoCpus'] == 1_000_000_000,
        'memory_8gib': host['Memory'] == 8*1024**3,
        'network_none': host['NetworkMode'] == 'none',
        'root_readonly': host['ReadonlyRootfs'] is True,
        'no_gpu_requests': not host.get('DeviceRequests'),
        'project_readonly': any(m['Destination']=='/workspace' and not m['RW'] for m in inspect['Mounts']),
        'no_docker_socket': all(m['Destination'] != '/var/run/docker.sock' for m in inspect['Mounts']),
        'no_auto_remove': not host['AutoRemove'],
    }


def run_g0(workspace):
    workspace = Path(workspace).resolve(strict=True)
    root = workspace/RESULT
    if root.exists():
        raise FileExistsError('F6-S0 result is create-only; no automatic repeat')
    admission = evaluate_storage(scan_workspace(workspace), planned_new_bytes=128*1024**2,
                                 stop_reserve_bytes=64*1024**2)
    if not admission['can_start']:
        raise RuntimeError('Storage admission refused')
    version = json.loads(read_docker('version', '--format', '{{json .}}'))
    image = json.loads(read_docker('image', 'inspect', TAG))[0]
    if image['Id'] != IMAGE:
        raise RuntimeError('Local image identity drift; no pull allowed')
    root.mkdir(parents=True, exist_ok=False)
    save_json(root/'storage_preflight.json', admission)
    save_json(root/'docker_version.json', version)
    save_json(root/'image_identity.json', image)
    name = 'prl-f6s0-g0-v01-20260917'
    args = container_command(workspace, name, '/workspace/src/prl/fem/fenicsx_probe.py')
    save_json(root/'g0_command.json', args)
    started = time.monotonic()
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', timeout=180)
        (root/'g0_stdout.log').write_text(result.stdout, encoding='utf-8')
        (root/'g0_stderr.log').write_text(result.stderr, encoding='utf-8')
        inspection = json.loads(read_docker('inspect', name))[0]
        save_json(root/'g0_container_inspect.json', inspection)
        settings = verify_container_settings(inspection)
        payloads = [x.split('=',1)[1] for x in result.stdout.splitlines() if x.startswith('PRL_G0_JSON=')]
        payload = json.loads(payloads[-1]) if payloads else {'status':'failed', 'reason':'no G0 payload'}
        payload.update({'container_checks': settings, 'container_name': name,
                        'exit_code': result.returncode, 'wall_seconds':time.monotonic()-started})
        if result.returncode != 0 or not all(settings.values()):
            payload['status'] = 'failed'
    except subprocess.TimeoutExpired:
        read_docker('stop', '--time', '5', name)
        payload = {'status':'failed', 'reason':'G0 180-second timeout', 'container_name':name}
    save_json(root/'g0_runtime.json', payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


if __name__ == '__main__':
    raise SystemExit(0 if run_g0(Path.cwd())['status']=='passed' else 2)
