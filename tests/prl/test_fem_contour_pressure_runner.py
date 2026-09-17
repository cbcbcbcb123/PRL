"""Bounded F5 dispatch tests; all scientific solves and filesystem writes are mocked."""

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest

from prl.fem import mixed_hex
from prl.runs import fem_contour_pressure as runner


def _mock_built(radial_intervals):
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    node_count = len(mesh["nodes"])
    return {
        "mesh": mesh,
        "fixed": {2: 0.0, 0: 0.0, 1: 0.0, 4: 0.0},
        "inner_faces": np.array([[0, 0, -1]], dtype=np.int64),
        "layer_ids": np.zeros(1, dtype=np.int64),
        "metadata": {
            "node_shape": [3, 3, 3], "pressure_shape": [2, 2, 2],
            "inner_midplane_nodes": [1], "outer_midplane_nodes": [19],
            "anchor_node_ids": {"A": 19, "B": 22},
            "outer_curve_nodes": [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]],
            "radial_q2_fractions": np.linspace(20 / 27, 1, 3).tolist(),
            "radial_q1_fractions": [20 / 27, 1.0],
            "radial_boundary_fractions": [20 / 27, 21 / 27, 22 / 27, 1.0],
            "source_to_solver_rotation": [[1.0, 0.0], [0.0, 1.0]],
            "center_um": [114.0, 149.0], "length_scale_um": 45.1,
            "height": 0.5, "radial_intervals": list(radial_intervals),
        },
    }


@pytest.fixture
def dispatch(monkeypatch):
    memory = {"calls": [], "reports": {}, "checkpoints": {}, "fail_at": None}

    geometry = ModuleType("prl.fem.contour_wall")
    geometry.build_contour_wall = lambda arrays, intervals, **kwargs: _mock_built(intervals)
    monkeypatch.setitem(sys.modules, geometry.__name__, geometry)

    def mock_solve(mesh, material, kappa, **kwargs):
        memory["calls"].append(deepcopy(kwargs))
        if len(memory["calls"]) == memory["fail_at"]:
            raise RuntimeError("injected F5 solve failure")
        n, m, e = len(mesh["nodes"]), len(mesh["pressure_nodes"]), len(mesh["elements"])
        vector = np.asarray(kwargs["initial"]).copy()
        tensor_shape = (e, 27, 3, 3)
        return {
            "u": vector[:3 * n].reshape(n, 3), "p": vector[3 * n:], "vector": vector,
            "residual": np.zeros(3 * n + m), "normalized_free_residual": 0.0,
            "F": np.broadcast_to(np.eye(3), tensor_shape).copy(),
            "P": np.zeros(tensor_shape), "Green": np.zeros(tensor_shape),
            "J": np.ones((e, 27)), "cauchy_stress": np.zeros(tensor_shape),
            "energy_density": np.zeros((e, 27)), "history": [],
        }

    monkeypatch.setattr(mixed_hex, "solve", mock_solve)
    pressure = ModuleType("prl.fem.follower_pressure")
    pressure.assemble_pressure = lambda mesh, *args, **kwargs: {
        "force": np.zeros(3 * len(mesh["nodes"]))
    }
    monkeypatch.setitem(sys.modules, pressure.__name__, pressure)
    verification = ModuleType("prl.verification.fem_contour_pressure")
    verification.verify_fem_contour_pressure = lambda *args, **kwargs: {
        "status": "passed",
        "source_geometry": {"status": "passed", "source_mask_iou": 0.99},
        "cases": {
            "radial_coarse": {"geometry": {"status": "passed"}},
            "radial_fine": {"geometry": {"status": "passed"}},
        },
        "mesh_comparison": {"status": "passed"},
        "gates": {"mock": "passed"},
    }
    monkeypatch.setitem(sys.modules, verification.__name__, verification)
    rendering = ModuleType("prl.rendering.fem_contour_pressure")
    rendering.render_fem_contour_pressure = lambda *args, **kwargs: {"status": "passed"}
    monkeypatch.setitem(sys.modules, rendering.__name__, rendering)

    monkeypatch.setattr(runner, "protected_evidence", lambda root: {"mock": "passed"})
    monkeypatch.setattr(runner, "scan_workspace", lambda root: None)
    monkeypatch.setattr(runner, "evaluate_storage", lambda *args, **kwargs: {"can_start": True})
    monkeypatch.setattr(runner, "scientific_lock", lambda root: nullcontext())
    monkeypatch.setattr(runner, "_sha256", lambda path: "mock")
    monkeypatch.setattr(runner, "_manifest", lambda root: {"files": []})
    monkeypatch.setattr(runner, "package_bytes", lambda root: 0)
    monkeypatch.setattr(runner, "_save_geometry_input", lambda *args: None)
    monkeypatch.setattr(
        runner, "_write_json",
        lambda path, value: memory["reports"].update({str(path): deepcopy(value)}),
    )
    monkeypatch.setattr(
        runner, "checkpoint",
        lambda root, name, value: memory["checkpoints"].update({name: deepcopy(value)}),
    )
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "is_file", lambda *args, **kwargs: True)
    return memory


def test_configuration_freezes_single_material_real_outline_slice():
    config = runner.configuration()
    assert config["loads"] == [0.0, 0.02, 0.04, 0.06, 0.08]
    assert config["material"] == {"model": "neo_hookean", "mu": 1.0}
    assert config["kappa"] == 1000.0
    assert config["solver"] == {"tolerance": 1e-9, "max_iterations": 30, "max_line_search": 16}
    assert config["thresholds"]["same_reference_domain_relative"] == 1e-12
    assert config["thresholds"]["in_plane_z_variation"] == 1e-10
    assert config["thresholds"]["midplane_average_area_relative"] == 1e-10
    assert config["thresholds"]["zero_pressure_stress"] == 2e-7
    assert config["geometry"]["segments"] == 36
    assert [case["radial_intervals"] for case in config["cases"]] == [[1, 1, 2], [2, 2, 4]]
    assert "constructed" in config["scope"] and config["resources"]["gpu"] == 0


def test_worker_attempts_exactly_ten_frozen_solves(dispatch):
    result = runner.worker(Path.cwd())
    assert result["status"] == "passed"
    assert result["new_solves"] == result["completed_states"] == 10
    assert result["scientific_invocations"] == 1 and result["automatic_retries"] == 0
    assert [call["follower_pressure"]["pressure"] for call in dispatch["calls"]] == [
        0.0, 0.02, 0.04, 0.06, 0.08,
    ] * 2
    assert all(call["tolerance"] == 1e-9 for call in dispatch["calls"])
    assert all(call["max_iterations"] == 30 and call["max_line_search"] == 16
               for call in dispatch["calls"])
    assert dispatch["checkpoints"]["radial_coarse"]["loads"].shape == (5,)
    assert dispatch["checkpoints"]["radial_fine"]["loads"].shape == (5,)
    summary = next(value for key, value in dispatch["reports"].items()
                   if key.endswith("summary.json"))
    assert summary["metrics"]["source_geometry"]["source_mask_iou"] == 0.99
    assert set(summary["metrics"]["case_geometry"]) == {"radial_coarse", "radial_fine"}
    source_hashes = next(value for key, value in dispatch["reports"].items()
                         if key.endswith("source_hashes.json"))
    assert {
        "src/prl/verification/fem_finite_strain.py",
        "src/prl/verification/fem_curved_pressure.py",
        "src/prl/rendering/fem_measured_contour.py",
        "src/prl/rendering/fem_finite_strain.py",
        "src/prl/rendering/fem_rotation.py",
        "src/prl/rendering/fem_curved_pressure.py",
        "src/prl/__main__.py",
    }.issubset(source_hashes)


def test_failure_stops_remaining_loads_and_preserves_prefix(dispatch):
    dispatch["fail_at"] = 4
    with pytest.raises(RuntimeError, match="injected F5"):
        runner.worker(Path.cwd())
    assert len(dispatch["calls"]) == 4
    assert dispatch["checkpoints"]["radial_coarse"]["loads"].tolist() == [0.0, 0.02, 0.04]
    assert "radial_fine" not in dispatch["checkpoints"]
    failure = next(value for key, value in dispatch["reports"].items()
                   if key.endswith("failure.json"))
    assert failure["completed_states"] == 3
    assert failure["context"] == {"case": "radial_coarse", "step": 3, "pressure": 0.06}


def test_storage_rejection_starts_no_science(dispatch, monkeypatch):
    monkeypatch.setattr(runner, "evaluate_storage", lambda *args, **kwargs: {"can_start": False})
    assert runner.worker(Path.cwd())["status"] == "blocked"
    assert dispatch["calls"] == []


def test_create_only_result_refuses_existing_directory(dispatch, monkeypatch):
    def refuse(*args, **kwargs):
        raise FileExistsError("retained F5 result")
    monkeypatch.setattr(Path, "mkdir", refuse)
    with pytest.raises(FileExistsError, match="retained F5"):
        runner.worker(Path.cwd())
    assert dispatch["calls"] == []


def test_final_budget_failure_does_not_publish_execution(dispatch, monkeypatch):
    monkeypatch.setattr(runner, "package_bytes", lambda root: runner.CAP)
    with pytest.raises(RuntimeError, match="headroom"):
        runner.worker(Path.cwd())
    assert not any(key.endswith("execution.json") and not key.endswith("solver_execution.json")
                   for key in dispatch["reports"])


def test_worker_flag_requires_controller(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fem_contour_pressure", "--worker"])
    monkeypatch.delenv("PRL_CONTOUR_PRESSURE_CONTROLLER", raising=False)
    with pytest.raises(RuntimeError, match="bounded contour-pressure controller"):
        runner.main()


def test_controller_uses_inner_1200_second_cap(monkeypatch):
    observed = {}

    def complete(*args, **kwargs):
        observed.update(kwargs)
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(sys, "argv", ["fem_contour_pressure", "--workspace", str(Path.cwd())])
    monkeypatch.setattr(runner.subprocess, "run", complete)
    assert runner.main() == 0
    assert observed["timeout"] == runner.TIMEOUT == 1200


def test_controller_timeout_seals_failure_evidence_without_retry(monkeypatch):
    records = {}

    def expire(*args, **kwargs):
        raise runner.subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(sys, "argv", ["fem_contour_pressure", "--workspace", str(Path.cwd())])
    monkeypatch.setattr(runner.subprocess, "run", expire)
    monkeypatch.setattr(Path, "is_dir", lambda path: True)
    monkeypatch.setattr(runner, "_manifest", lambda root: {
        "schema_version": "prl.fem_contour_pressure_manifest.v1", "files": []})
    monkeypatch.setattr(runner, "_write_json",
                        lambda path, value: records.update({path.name: deepcopy(value)}))
    assert runner.main() == 1
    assert {"timeout.json", "failure.json", "progress.json", "manifest.json"} <= set(records)
    assert records["failure.json"]["automatic_retries"] == 0
    assert records["manifest.json"]["schema_version"] == "prl.fem_contour_pressure_manifest.v1"


def test_manifest_uses_f5_schema(monkeypatch):
    monkeypatch.setattr(runner, "_base_manifest", lambda root: {
        "schema_version": "prl.fem_active_ellipse_manifest.v1", "files": []})
    assert runner._manifest(Path.cwd())["schema_version"] == "prl.fem_contour_pressure_manifest.v1"


def test_atomic_checkpoint_does_not_replace_after_write_failure(monkeypatch):
    replacements = []
    monkeypatch.setattr(runner, "package_bytes", lambda root: 0)
    monkeypatch.setattr(runner.np, "savez_compressed",
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("write failed")))
    monkeypatch.setattr(runner.os, "replace", lambda *args: replacements.append(args))
    with pytest.raises(OSError, match="write failed"):
        runner.checkpoint(Path.cwd(), "mock", {"x": np.zeros(4)})
    assert replacements == []


def test_checkpoint_budgets_old_plus_pending(monkeypatch):
    monkeypatch.setattr(runner, "package_bytes", lambda root: runner.CAP)
    with pytest.raises(RuntimeError, match="stage budget"):
        runner.checkpoint(Path.cwd(), "mock", {"x": np.zeros(4)})
