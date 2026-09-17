"""Configuration/dispatch/checkpoint checks; every write and solve is mocked.

These tests do not run any scientific case or create a temporary directory.
"""

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from prl.fem import hyperelastic, mixed_hex
from prl.runs import fem_finite_strain as runner


WORKSPACE = Path(__file__).resolve().parents[2]


def test_frozen_matrix_has_14_cases_and_82_real_requested_states():
    config = runner.configuration()
    cases = config["cases"]
    assert len(cases) == 14
    assert sum(len(case["phases"]) for case in cases.values()) == 82
    assert sum(case["kind"] == "stretch" for case in cases.values()) == 6
    assert sum(case["kind"] == "active" for case in cases.values()) == 3
    assert sum(case["kind"] == "bending" for case in cases.values()) == 4
    assert sum(case["kind"] == "rotation" for case in cases.values()) == 1
    for case in cases.values():
        if case["kind"] == "active":
            np.testing.assert_allclose(case["T_values"], 1 - np.cos(2 * np.pi * np.asarray(case["phases"])))
            assert max(case["T_values"]) == pytest.approx(2)
        else:
            np.testing.assert_array_equal(case["T_values"], 0)
    assert cases["guccione_stretch_fiber_y"]["fiber"] == [0, 1, 0]
    assert config["resources"]["automatic_retries"] == 0
    assert config["resources"]["threads"] == 1
    assert config["resources"]["gpu"] == 0


@pytest.mark.parametrize("kind", ["stretch", "active"])
def test_normal_symmetry_boundaries_do_not_clamp_tangential_motion(kind):
    case = next(case for case in runner.configuration()["cases"].values() if case["kind"] == kind)
    mesh = mixed_hex.structured_mesh(tuple(case["subdivisions"]), case["lengths"])
    fixed, force = runner.boundary_data(mesh, case, len(case["phases"]) - 1)
    for node, xyz in enumerate(mesh["nodes"]):
        for component in range(3):
            expected = xyz[component] == 0 or (kind == "stretch" and component == 0 and xyz[0] == 2)
            assert (3 * node + component in fixed) == expected
    np.testing.assert_array_equal(force, 0)
    if kind == "stretch":
        assert fixed[3 * int(np.flatnonzero(mesh["nodes"][:, 0] == 2)[0])] == pytest.approx(0.6)


@pytest.mark.parametrize("name", ["nh_bending_coarse_k100", "nh_bending_fine_k1000"])
def test_dead_traction_has_exact_force_and_origin_moment(name):
    case = runner.configuration()["cases"][name]
    mesh = mixed_hex.structured_mesh(tuple(case["subdivisions"]), case["lengths"])
    fixed, force = runner.boundary_data(mesh, case, 4)
    nodal = force.reshape(-1, 3)
    np.testing.assert_allclose(nodal.sum(axis=0), [0, 0.005, 0], atol=1e-15)
    np.testing.assert_allclose(np.cross(mesh["nodes"], nodal).sum(axis=0), [-0.0025, 0, 0.02], atol=1e-15)
    assert set(fixed) == {3 * int(node) + component for node in np.flatnonzero(mesh["nodes"][:, 0] == 0)
                          for component in range(3)}
    assert all(mesh["nodes"][node, 0] == 4 for node in np.flatnonzero(np.linalg.norm(nodal, axis=1)))


def test_rotation_is_about_origin_and_only_boundary_is_prescribed():
    case = runner.configuration()["cases"]["nh_rigid_rotation"]
    mesh = mixed_hex.structured_mesh(tuple(case["subdivisions"]), case["lengths"])
    fixed, force = runner.boundary_data(mesh, case, 4)
    angle = np.pi / 3
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    target = mesh["nodes"] @ rotation.T - mesh["nodes"]
    for node, xyz in enumerate(mesh["nodes"]):
        boundary = np.any((xyz == 0) | (xyz == case["lengths"]))
        for component in range(3):
            assert (3 * node + component in fixed) == boundary
            if boundary:
                assert fixed[3 * node + component] == pytest.approx(target[node, component], abs=1e-15)
    np.testing.assert_array_equal(force, 0)


@pytest.fixture
def mocked_worker(monkeypatch):
    """A two-state dispatch fixture; no numerical solve or filesystem writes."""
    config = runner.configuration()
    case = deepcopy(config["cases"]["nh_active_k100"])
    case.update(subdivisions=[1, 1, 1], phases=[0, 0.5], T_values=[0, 2],
                stretch_values=[1, 1], traction_values=[0, 0], rotation_degrees=[0, 0])
    config["cases"] = {"mock_active": case}
    memory = {"arrays": {}, "json": {}, "solve_calls": [], "writes": 0, "checkpoint_writes": 0, "replacements": 0,
              "fail_write": None}
    monkeypatch.setattr(runner, "configuration", lambda: config)
    monkeypatch.setattr(runner, "scan_workspace", lambda workspace: {"fixture": True})
    monkeypatch.setattr(runner, "evaluate_storage", lambda *args, **kwargs: {"can_start": True})
    monkeypatch.setattr(runner, "scientific_lock", lambda workspace: nullcontext())
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "is_file", lambda *args, **kwargs: True)
    monkeypatch.setattr(runner, "_sha256", lambda path: "mock-sha256")
    monkeypatch.setattr(runner, "_protected_manifests", lambda workspace: {"fixture": "unchanged"})
    monkeypatch.setattr(runner, "_write_json", lambda path, value: memory["json"].update({path.name: deepcopy(value)}))
    monkeypatch.setattr(runner, "_manifest", lambda root: {"files": []})
    monkeypatch.setattr(runner, "check_budget", lambda root: 1234)

    def mock_solve(mesh, material, bulk, **kwargs):
        memory["solve_calls"].append((deepcopy(material), bulk, kwargs.copy()))
        n, m, e = len(mesh["nodes"]), len(mesh["pressure_nodes"]), len(mesh["elements"])
        tensor_shape = (e, 27, 3, 3)
        return {"vector": np.zeros(3 * n + m), "u": np.zeros((n, 3)), "p": np.zeros(m),
                "residual": np.zeros(3 * n + m), "normalized_free_residual": 0.0,
                "F": np.broadcast_to(np.eye(3), tensor_shape).copy(), "P": np.zeros(tensor_shape),
                "Green": np.zeros(tensor_shape), "J": np.ones((e, 27)),
                "cauchy_stress": np.zeros(tensor_shape), "energy_density": np.zeros((e, 27)),
                "history": [{"iteration": 0, "normalized_free_residual": 0.0}]}

    def mock_save(path, **payload):
        memory["writes"] += 1
        if path.name.endswith(".pending.npz"):
            memory["checkpoint_writes"] += 1
        if path.name.endswith(".pending.npz") and memory["checkpoint_writes"] == memory["fail_write"]:
            memory["arrays"][str(path)] = {"partial_write": True}
            raise OSError("mock disk write failure")
        memory["arrays"][str(path)] = {key: np.asarray(value).copy() for key, value in payload.items()}

    def mock_replace(source, destination):
        memory["replacements"] += 1
        memory["arrays"][str(destination)] = memory["arrays"][str(source)]

    monkeypatch.setattr(mixed_hex, "solve", mock_solve)
    monkeypatch.setattr(hyperelastic, "material_response", lambda F, *args, **kwargs: {
        "energy": np.zeros(np.shape(F)[:-2]), "P": np.zeros_like(F),
        "tangent": np.zeros((*np.shape(F)[:-2], 3, 3, 3, 3)), "J": np.ones(np.shape(F)[:-2]),
    })
    monkeypatch.setattr(runner.np, "savez_compressed", mock_save)
    monkeypatch.setattr(runner.os, "replace", mock_replace)
    for module_name, function_name in (
        ("prl.verification.fem_finite_strain", "verify_fem_finite_strain"),
        ("prl.rendering.fem_finite_strain", "render_fem_finite_strain"),
    ):
        module = ModuleType(module_name)
        setattr(module, function_name, lambda *args, **kwargs: {"status": "passed", "cases": {}})
        monkeypatch.setitem(sys.modules, module_name, module)
    return memory


def test_worker_passes_activation_fiber_and_continuation_and_atomically_saves(mocked_worker):
    result = runner.worker(WORKSPACE)
    memory = mocked_worker
    assert result["status"] == "passed"
    assert len(memory["solve_calls"]) == 2
    assert [call[2]["active_tension"] for call in memory["solve_calls"]] == [0, 2]
    assert all(call[0]["fiber"] == [1, 0, 0] for call in memory["solve_calls"])
    assert memory["solve_calls"][0][2]["initial"] is None
    assert isinstance(memory["solve_calls"][1][2]["initial"], np.ndarray)
    assert memory["replacements"] == 2
    checkpoint = memory["arrays"][str(WORKSPACE / runner.RESULT / "raw/mock_active.npz")]
    assert checkpoint["displacements"].shape[0] == 2
    np.testing.assert_array_equal(checkpoint["activation"], [0, 2])
    assert memory["json"]["execution.json"]["automatic_retries"] == 0


def test_partial_checkpoint_write_preserves_previous_complete_state(mocked_worker):
    memory = mocked_worker
    memory["fail_write"] = 2
    with pytest.raises(OSError, match="mock disk write failure"):
        runner.worker(WORKSPACE)
    assert len(memory["solve_calls"]) == 2
    assert memory["replacements"] == 1
    checkpoint = memory["arrays"][str(WORKSPACE / runner.RESULT / "raw/mock_active.npz")]
    assert checkpoint["displacements"].shape[0] == 1
    assert memory["json"]["failure.json"]["status"] == "failed"
    assert "execution.json" not in memory["json"]


def test_newton_failure_preserves_context_mesh_boundaries_and_last_state(mocked_worker, monkeypatch):
    original_mock = mixed_hex.solve
    def fail_at_second_state(*args, **kwargs):
        returned = original_mock(*args, **kwargs)
        if len(mocked_worker["solve_calls"]) == 2:
            raise mixed_hex.MixedSolveError("mock Newton failure", returned)
        return returned
    monkeypatch.setattr(mixed_hex, "solve", fail_at_second_state)
    with pytest.raises(mixed_hex.MixedSolveError, match="mock Newton failure"):
        runner.worker(WORKSPACE)
    failure = mocked_worker["json"]["failure.json"]
    assert failure["context"]["case"] == "mock_active"
    assert failure["context"]["step"] == 1
    assert failure["context"]["phase"] == 0.5
    retained = mocked_worker["arrays"][str(WORKSPACE / runner.RESULT / "last_newton_state.npz")]
    for key in ("vector", "coordinates", "cells", "pressure_coordinates", "pressure_cells",
                "prescribed_dofs", "prescribed_values", "prescribed_forces"):
        assert key in retained
    assert mocked_worker["replacements"] == 1
    assert "execution.json" not in mocked_worker["json"]


def test_existing_result_refuses_rerun_before_solver(mocked_worker, monkeypatch):
    def refuse_existing(*args, **kwargs):
        raise FileExistsError("mock existing frozen result")
    monkeypatch.setattr(Path, "mkdir", refuse_existing)
    with pytest.raises(FileExistsError):
        runner.worker(WORKSPACE)
    assert mocked_worker["solve_calls"] == []
    assert mocked_worker["writes"] == 0


def test_storage_refusal_stops_before_any_file_or_solver(mocked_worker, monkeypatch):
    monkeypatch.setattr(runner, "evaluate_storage", lambda *args, **kwargs: {"can_start": False})
    mkdir = Mock(side_effect=AssertionError("must not create a result on budget rejection"))
    monkeypatch.setattr(Path, "mkdir", mkdir)
    result = runner.worker(WORKSPACE)
    assert result["status"] == "blocked"
    assert mocked_worker["solve_calls"] == []
    mkdir.assert_not_called()


def test_worker_cli_bypass_is_rejected_without_execution(monkeypatch):
    worker = Mock(side_effect=AssertionError("unguarded worker launch"))
    monkeypatch.setattr(runner, "worker", worker)
    monkeypatch.setattr(sys, "argv", ["fem_finite_strain", "--workspace", str(WORKSPACE), "--worker"])
    monkeypatch.delenv("PRL_FINITE_STRAIN_CONTROLLER", raising=False)
    with pytest.raises(RuntimeError, match="bounded controller"):
        runner.main()
    worker.assert_not_called()


def test_controller_runs_once_with_frozen_resource_bounds(monkeypatch):
    launch = Mock(return_value=subprocess.CompletedProcess([], 1))
    monkeypatch.setattr(runner.subprocess, "run", launch)
    monkeypatch.setattr(sys, "argv", ["fem_finite_strain", "--workspace", str(WORKSPACE)])
    assert runner.main() == 1
    launch.assert_called_once()
    assert launch.call_args.kwargs["timeout"] == 1200
    environment = launch.call_args.kwargs["env"]
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert environment[name] == "1"
    assert environment["PRL_FINITE_STRAIN_CONTROLLER"] == "1"
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "--worker" in launch.call_args.args[0]


def test_budget_cap_uses_bytes_of_every_stage_file():
    class SimulatedFile:
        def __init__(self, byte_count):
            self.byte_count = byte_count
        def is_file(self):
            return True
        def stat(self):
            return SimpleNamespace(st_size=self.byte_count)
    root = SimpleNamespace(rglob=lambda pattern: [SimulatedFile(runner.CAP), SimulatedFile(1)])
    with pytest.raises(RuntimeError, match="stage cap"):
        runner.check_budget(root)
