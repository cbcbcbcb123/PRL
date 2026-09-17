"""Supplement dispatch/retention tests: no scientific solves or file writes."""

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest

from prl.fem import mixed_hex
from prl.runs import fem_rotation as runner
from prl.runs.fem_finite_strain import configuration as parent_configuration


@pytest.fixture
def dispatch(monkeypatch):
    case = parent_configuration()['cases']['nh_rigid_rotation']
    config = {'case': case, 'perturbation': {'amplitude': .002, 'components': [1, -.7, .5]}}
    mesh = mixed_hex.structured_mesh((2, 2, 2), (2, 1, 1))
    n, m, e = len(mesh['nodes']), len(mesh['pressure_nodes']), len(mesh['elements'])
    fixed, force = runner.boundary_data(mesh, case, 0)
    tensor = (e, 27, 3, 3)
    memory = {'calls': [], 'checkpoints': {}, 'reports': {}, 'fail_at': None}

    def mock_solve(mesh, material, bulk, **kwargs):
        memory['calls'].append(deepcopy(kwargs))
        if len(memory['calls']) == memory['fail_at']:
            raise RuntimeError('injected solve failure')
        vector = np.asarray(kwargs['initial']).copy()
        return {'vector': vector, 'u': vector[:3*n].reshape(n, 3), 'p': vector[3*n:],
                'residual': np.zeros(3*n+m), 'normalized_free_residual': 0.0,
                'F': np.broadcast_to(np.eye(3), tensor).copy(), 'P': np.zeros(tensor),
                'Green': np.zeros(tensor), 'J': np.ones((e, 27)),
                'cauchy_stress': np.zeros(tensor), 'energy_density': np.zeros((e, 27)), 'history': []}

    initial = mock_solve(mesh, {}, 1000, initial=np.zeros(3*n+m))
    memory['calls'].clear()
    parent = {key: np.asarray([value]) for key, value in runner.state_payload(initial, fixed, force).items()}
    parent.update(runner.mesh_payload(mesh), fixed_dofs=np.array(sorted(fixed)), phases=np.array([0.0]))

    class Saved:
        files = list(parent)
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __getitem__(self, key): return parent[key]

    def mock_lift(mesh, previous, fixed):
        prediction = previous.copy()
        prediction[list(fixed)] = list(fixed.values())
        return {'vector': prediction, 'diagnostics': {'mocked': True}}

    monkeypatch.setattr(runner, 'configuration', lambda root: deepcopy(config))
    monkeypatch.setattr(runner, 'verify_parent', lambda root: {'status': 'passed'})
    monkeypatch.setattr(runner, 'scan_workspace', lambda root: None)
    monkeypatch.setattr(runner, 'evaluate_storage', lambda *a, **k: {'can_start': True})
    monkeypatch.setattr(runner, 'scientific_lock', lambda root: nullcontext())
    monkeypatch.setattr(runner, '_sha256', lambda path: 'mock')
    monkeypatch.setattr(runner, '_manifest', lambda root: {'files': []})
    monkeypatch.setattr(runner, 'package_bytes', lambda root: 0)
    monkeypatch.setattr(runner, '_write_json', lambda path, obj: memory['reports'].update({path.name: deepcopy(obj)}))
    monkeypatch.setattr(runner, 'checkpoint', lambda root, name, obj: memory['checkpoints'].update({name: deepcopy(obj)}))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(Path, 'is_file', lambda *a, **k: True)
    monkeypatch.setattr(Path, 'read_text', lambda *a, **k: '[[]]')
    monkeypatch.setattr(runner.np, 'load', lambda *a, **k: Saved())
    monkeypatch.setattr(mixed_hex, 'solve', mock_solve)
    monkeypatch.setattr(mixed_hex, 'lift_dirichlet_initial', mock_lift)
    for module_name, function in [('prl.verification.fem_rotation', 'verify_fem_rotation'),
                                  ('prl.rendering.fem_rotation', 'render_fem_rotation')]:
        module = ModuleType(module_name)
        setattr(module, function, lambda *a, **k: {'status': 'passed'})
        monkeypatch.setitem(sys.modules, module_name, module)
    return memory


def test_only_four_missing_angles_and_one_recovery_are_dispatched(dispatch):
    result = runner.worker(Path.cwd())
    assert result['status'] == 'passed'
    assert len(dispatch['calls']) == 5
    assert all(call['tolerance'] == 1e-9 and call['max_iterations'] == 30 and call['max_line_search'] == 16
               for call in dispatch['calls'])
    assert dispatch['checkpoints']['rotation']['angles'].tolist() == [0, 15, 30, 45, 60]
    assert dispatch['checkpoints']['rotation']['displacements'].shape[0] == 5
    assert dispatch['checkpoints']['rotation_initials']['predicted_vectors'].shape[0] == 4
    assert dispatch['reports']['solver_execution.json']['parent_retained_states'] == 1
    assert result['automatic_retries'] == 0


def test_solver_failure_stops_and_keeps_the_written_prefix(dispatch):
    dispatch['fail_at'] = 2
    with pytest.raises(RuntimeError, match='injected solve failure'):
        runner.worker(Path.cwd())
    assert len(dispatch['calls']) == 2
    assert dispatch['checkpoints']['rotation']['angles'].tolist() == [0, 15]
    assert 'perturbed_recovery' not in dispatch['checkpoints']
    assert dispatch['reports']['failure.json']['context']['angle'] == 30
    assert dispatch['reports']['failure.json']['automatic_retries'] == 0


def test_storage_rejection_prevents_any_solve(dispatch, monkeypatch):
    monkeypatch.setattr(runner, 'evaluate_storage', lambda *a, **k: {'can_start': False})
    assert runner.worker(Path.cwd())['status'] == 'blocked'
    assert not dispatch['calls'] and not dispatch['checkpoints']


def test_failed_retention_write_still_records_original_failure(dispatch, monkeypatch):
    dispatch['fail_at'] = 2
    capture = runner.checkpoint
    def fail_retention(root, name, payload):
        if name == 'failure_state': raise OSError('second write failure')
        capture(root, name, payload)
    monkeypatch.setattr(runner, 'checkpoint', fail_retention)
    with pytest.raises(RuntimeError, match='injected solve failure'):
        runner.worker(Path.cwd())
    failure = dispatch['reports']['failure.json']
    assert failure['status'] == 'failed'
    assert 'second write failure' in failure['failure_state_write_error']
    assert dispatch['checkpoints']['rotation']['angles'].tolist() == [0, 15]


def test_final_cap_failure_never_publishes_passed_execution(dispatch, monkeypatch):
    monkeypatch.setattr(runner, 'package_bytes', lambda root: runner.CAP)
    with pytest.raises(RuntimeError, match='control-record headroom'):
        runner.worker(Path.cwd())
    assert 'execution.json' not in dispatch['reports']
    assert dispatch['reports']['progress.json']['status'] == 'failed'


def test_existing_result_refuses_to_start(dispatch, monkeypatch):
    def refuse(*args, **kwargs): raise FileExistsError('retained result')
    monkeypatch.setattr(Path, 'mkdir', refuse)
    with pytest.raises(FileExistsError): runner.worker(Path.cwd())
    assert not dispatch['calls']


def test_checkpoint_failure_cannot_replace_last_complete_file(monkeypatch):
    replacements = []
    monkeypatch.setattr(runner, 'package_bytes', lambda path: 0)
    def fail(*args, **kwargs): raise OSError('write failed')
    monkeypatch.setattr(runner.np, 'savez_compressed', fail)
    monkeypatch.setattr(runner.os, 'replace', lambda *args: replacements.append(args))
    with pytest.raises(OSError): runner.checkpoint(Path.cwd(), 'mock', {'x': np.zeros(3)})
    assert not replacements


def test_checkpoint_budgets_pending_copy(monkeypatch):
    monkeypatch.setattr(runner, 'package_bytes', lambda path: runner.CAP)
    with pytest.raises(RuntimeError, match='budget'):
        runner.checkpoint(Path.cwd(), 'mock', {'x': np.zeros(3)})


def test_worker_entry_requires_controller(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['fem_rotation', '--worker'])
    monkeypatch.delenv('PRL_ROTATION_CONTROLLER', raising=False)
    with pytest.raises(RuntimeError, match='bounded rotation controller'): runner.main()
