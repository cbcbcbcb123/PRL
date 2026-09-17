"""Bounded F4 dispatch/retention checks; scientific solves mocked, no files written."""

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest

from prl.fem import mixed_hex
from prl.runs import fem_curved_pressure as runner


def test_geometry_is_curved_reference_and_constraint_set_is_plane_strain():
    config = runner.configuration()
    mesh, fixed, faces = runner.curved_mesh(config['cases'][0], config['geometry'])
    assert mesh['geometry_mapping'] == 'isoparametric'
    assert len(mesh['elements']) == 8 and len(faces) == 4
    assert np.all(faces[:, 1:] == np.array([0, -1]))
    radius = np.linalg.norm(mesh['nodes'][:, :2], axis=1)
    assert radius.min() == pytest.approx(1) and radius.max() == pytest.approx(1.25)
    assert all(3 * node + 2 in fixed for node in range(len(radius)))
    assert all(value == 0 for value in fixed.values())
    for node, point in enumerate(mesh['nodes']):
        assert (3 * node in fixed) == bool(np.isclose(point[0], 0))
        assert (3 * node + 1 in fixed) == bool(np.isclose(point[1], 0))


@pytest.fixture
def dispatch(monkeypatch):
    memory = {'calls': [], 'reports': {}, 'checkpoints': {}, 'fail_at': None}

    def mock_solve(mesh, material, kappa, **kwargs):
        memory['calls'].append({'counts': mesh['counts'], **deepcopy(kwargs)})
        if len(memory['calls']) == memory['fail_at']:
            raise RuntimeError('injected F4 solve failure')
        n, m, e = len(mesh['nodes']), len(mesh['pressure_nodes']), len(mesh['elements'])
        tensor = (e, 27, 3, 3)
        vector = np.asarray(kwargs['initial']).copy()
        return {'u': vector[:3*n].reshape(n, 3), 'p': vector[3*n:], 'vector': vector,
                'residual': np.zeros(3*n+m), 'normalized_free_residual': 0.0,
                'F': np.broadcast_to(np.eye(3), tensor).copy(), 'P': np.zeros(tensor),
                'Green': np.zeros(tensor), 'J': np.ones((e, 27)),
                'cauchy_stress': np.zeros(tensor), 'energy_density': np.zeros((e, 27)), 'history': []}

    monkeypatch.setattr(mixed_hex, 'solve', mock_solve)
    pressure = ModuleType('prl.fem.follower_pressure')
    pressure.assemble_pressure = lambda mesh, *a, **k: {'force': np.zeros(3 * len(mesh['nodes']))}
    monkeypatch.setitem(sys.modules, pressure.__name__, pressure)
    for module_name, function in [('prl.verification.fem_curved_pressure', 'verify_fem_curved_pressure'),
                                  ('prl.rendering.fem_curved_pressure', 'render_fem_curved_pressure')]:
        module = ModuleType(module_name)
        setattr(module, function, lambda *a, **k: {'status': 'passed'})
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setattr(runner, 'protected_evidence', lambda root: {'mock': 'passed'})
    monkeypatch.setattr(runner, 'scan_workspace', lambda root: None)
    monkeypatch.setattr(runner, 'evaluate_storage', lambda *a, **k: {'can_start': True})
    monkeypatch.setattr(runner, 'scientific_lock', lambda root: nullcontext())
    monkeypatch.setattr(runner, '_sha256', lambda path: 'mock')
    monkeypatch.setattr(runner, '_manifest', lambda root: {'files': []})
    monkeypatch.setattr(runner, 'package_bytes', lambda root: 0)
    monkeypatch.setattr(runner, '_write_json', lambda path, obj: memory['reports'].update({str(path): deepcopy(obj)}))
    monkeypatch.setattr(runner, 'checkpoint', lambda root, name, obj: memory['checkpoints'].update({name: deepcopy(obj)}))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(Path, 'is_file', lambda *a, **k: True)
    return memory


def test_only_fixed_ten_states_with_original_newton_gates(dispatch):
    result = runner.worker(Path.cwd())
    assert result['status'] == 'passed' and result['new_solves'] == 10
    assert result['completed_states'] == 10 and result['scientific_invocations'] == 1
    assert result['automatic_retries'] == 0
    assert [call['follower_pressure']['pressure'] for call in dispatch['calls']] == [0, .02, .04, .06, .08] * 2
    assert all(call['tolerance'] == 1e-9 and call['max_iterations'] == 30 and call['max_line_search'] == 16
               for call in dispatch['calls'])
    assert dispatch['checkpoints']['coarse']['loads'].shape == (5,)
    assert dispatch['checkpoints']['fine']['loads'].shape == (5,)


def test_failed_step_stops_and_keeps_written_prefix(dispatch):
    dispatch['fail_at'] = 3
    with pytest.raises(RuntimeError, match='injected F4'):
        runner.worker(Path.cwd())
    assert len(dispatch['calls']) == 3
    assert dispatch['checkpoints']['coarse']['loads'].tolist() == [0, .02]
    assert 'fine' not in dispatch['checkpoints']
    failure = next(v for key, v in dispatch['reports'].items() if key.endswith('failure.json'))
    assert failure['completed_states'] == 2 and failure['context']['pressure'] == .04


def test_no_start_when_storage_rejects(dispatch, monkeypatch):
    monkeypatch.setattr(runner, 'evaluate_storage', lambda *a, **k: {'can_start': False})
    assert runner.worker(Path.cwd())['status'] == 'blocked'
    assert not dispatch['calls'] and not dispatch['checkpoints']


def test_existing_result_refuses_execution(dispatch, monkeypatch):
    def refuse(*args, **kwargs): raise FileExistsError('retained result')
    monkeypatch.setattr(Path, 'mkdir', refuse)
    with pytest.raises(FileExistsError): runner.worker(Path.cwd())
    assert not dispatch['calls']


def test_second_write_failure_does_not_mask_first_failure(dispatch, monkeypatch):
    dispatch['fail_at'] = 2
    original = runner.checkpoint
    def checkpoint(root, name, payload):
        if name == 'failure_state': raise OSError('injected retention failure')
        return original(root, name, payload)
    monkeypatch.setattr(runner, 'checkpoint', checkpoint)
    with pytest.raises(RuntimeError, match='injected F4'):
        runner.worker(Path.cwd())
    failure = next(v for key, v in dispatch['reports'].items() if key.endswith('failure.json'))
    assert 'retention failure' in failure['failure_state_write_error']
    assert dispatch['checkpoints']['coarse']['loads'].tolist() == [0]


def test_final_budget_failure_cannot_publish_passed(dispatch, monkeypatch):
    monkeypatch.setattr(runner, 'package_bytes', lambda root: runner.CAP)
    with pytest.raises(RuntimeError, match='headroom'): runner.worker(Path.cwd())
    assert not any(key.endswith('execution.json') and not key.endswith('solver_execution.json')
                   for key in dispatch['reports'])


def test_pending_write_failure_keeps_old_checkpoint(monkeypatch):
    replacements = []
    monkeypatch.setattr(runner, 'package_bytes', lambda root: 0)
    def fail(*args, **kwargs): raise OSError('injected write failure')
    monkeypatch.setattr(runner.np, 'savez_compressed', fail)
    monkeypatch.setattr(runner.os, 'replace', lambda *a: replacements.append(a))
    with pytest.raises(OSError): runner.checkpoint(Path.cwd(), 'mock', {'x': np.zeros(3)})
    assert not replacements


def test_pending_file_budget_is_included(monkeypatch):
    monkeypatch.setattr(runner, 'package_bytes', lambda root: runner.CAP)
    with pytest.raises(RuntimeError, match='budget'): runner.checkpoint(Path.cwd(), 'mock', {'x': np.zeros(3)})


def test_worker_requires_controller(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['fem_curved_pressure', '--worker'])
    monkeypatch.delenv('PRL_CURVED_PRESSURE_CONTROLLER', raising=False)
    with pytest.raises(RuntimeError, match='bounded curved-pressure controller'): runner.main()
