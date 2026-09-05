#!/usr/bin/env python3
"""Single bounded repair of the closed-cell/Ritz v01 JSON boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
V01_RUNNER = REPO_ROOT / "scripts/run_paper2_closed_cell_ritz_probe_v01.py"
V01_FAILED_OUTPUT = REPO_ROOT / "results/paper2_closed_cell_ritz_probe/v01_20260905/summary.json"
V02_OUTPUT = Path("results/paper2_closed_cell_ritz_probe/v02_20260905/summary.json")
FROZEN_COMMIT = "c7a363b25531fd54e6169f570ab6b2f5c14de3a5"
PLAN_SHA256 = "b11dc025d14f34b5b908c1ef9fffc52d7590c3797a0accaf04242ef60e39ef47"
BRIEF_SHA256 = "4650c5f788c814e058f18e88a3514ffa99e15e2a584f994e8894da63a3b051d0"
V01_RUNNER_SHA256 = "9a0b9e738624e92559421064f99aae8979ae065dd67d112ad0bb681f85dd9eec"
V01_FAILED_SHA256 = "38fc48d9153e39fe4b884a7dfccdfcd85b8b2344547048ec7dca85719e94ddff"
V01_FAILED_BYTES = 182
V01_RESERVED_SECONDS = 346.623864
OLD_FEM_SECONDS = 170.24076614002115
WRITER_AUDIT: dict[str, Any] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(repo_root: Path) -> str:
    git_path = repo_root / ".git"
    if git_path.is_file():
        marker = git_path.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir: "):
            raise RuntimeError("unrecognized .git file")
        git_path = (repo_root / marker[8:]).resolve()
    head = (git_path / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    reference = head[5:]
    loose = git_path / reference
    if loose.exists():
        return loose.read_text(encoding="utf-8").strip()
    for line in (git_path / "packed-refs").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "^")):
            commit, name = line.split(" ", 1)
            if name == reference:
                return commit
    raise RuntimeError("HEAD reference was not resolved")


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float rejected")
        return value
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("only string JSON object keys are accepted")
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported JSON boundary type: {type(value).__name__}")


def _serialization_regression() -> dict[str, Any]:
    candidate = {
        "boolean": np.bool_(True),
        "integer": np.int64(7),
        "float": np.float64(0.125),
        "array": np.array([[1, 2], [3, 4]], dtype=np.int32),
        "nested": [np.bool_(False), {"value": np.float32(1.5)}],
    }
    expected = {
        "boolean": True,
        "integer": 7,
        "float": 0.125,
        "array": [[1, 2], [3, 4]],
        "nested": [False, {"value": 1.5}],
    }
    converted = _json_ready(candidate)
    round_trip = json.loads(json.dumps(converted, allow_nan=False))
    if round_trip != expected:
        raise RuntimeError("finite nested JSON round-trip regression failed")

    rejected: dict[str, bool] = {}
    class Unknown:
        pass

    rejection_cases = {
        "NaN": float("nan"),
        "positive_infinity": float("inf"),
        "negative_infinity": -float("inf"),
        "array_with_NaN": np.array([1.0, np.nan]),
        "unknown_type": Unknown(),
    }
    for name, value in rejection_cases.items():
        try:
            json.dumps(_json_ready(value), allow_nan=False)
        except (TypeError, ValueError):
            rejected[name] = True
        else:
            rejected[name] = False
    if not all(rejected.values()):
        raise RuntimeError("invalid JSON boundary value was not rejected")
    return {
        "finite_numpy_scalar_array_nested_round_trip": True,
        "round_trip_value": round_trip,
        "rejected_without_string_fallback": rejected,
        "allow_nan": False,
        "unknown_types_raise_TypeError": True,
        "model_right_sides_solved_by_regression": 0,
    }


def _verify_frozen_sources() -> dict[str, Any]:
    ledger = {
        "project_control/prl_independent_theory_mainline_plan_v04.md": PLAN_SHA256,
        "results/paper2_science_pilot/v01_20260905/science_brief.md": BRIEF_SHA256,
        "scripts/run_paper2_closed_cell_ritz_probe_v01.py": V01_RUNNER_SHA256,
        "results/paper2_closed_cell_ritz_probe/v01_20260905/summary.json": V01_FAILED_SHA256,
    }
    actual = {path: _sha256(REPO_ROOT / path) for path in ledger}
    if actual != ledger:
        raise RuntimeError(f"frozen source hash mismatch: expected={ledger}, actual={actual}")
    if V01_FAILED_OUTPUT.stat().st_size != V01_FAILED_BYTES:
        raise RuntimeError("v01 failed output byte count changed")
    actual_head = _git_head(REPO_ROOT)
    if actual_head != FROZEN_COMMIT:
        raise RuntimeError(f"frozen HEAD mismatch: expected={FROZEN_COMMIT}, actual={actual_head}")
    return {
        "frozen_HEAD": actual_head,
        "sha256": actual,
        "v01_failed_output_bytes": V01_FAILED_OUTPUT.stat().st_size,
        "all_match": True,
    }


def _safe_write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.as_posix() != V02_OUTPUT.as_posix() or path.exists():
        raise RuntimeError("v02 authorized output is occupied or changed")
    preopen_started = datetime.now(timezone.utc)
    preopen_timer = time.perf_counter()

    payload["schema"] = "paper2_closed_cell_ritz_probe_v02"
    payload["status"] = (
        "COMPLETED_BOUNDED_IDEAL_PROTOTYPE_V02"
        if payload["status"] == "COMPLETED_BOUNDED_IDEAL_PROTOTYPE"
        else payload["status"]
    )
    payload["preregistration"] = {
        "frozen_commit": FROZEN_COMMIT,
        "main_plan_section_32_sha256": PLAN_SHA256,
        "science_brief_section_55_sha256": BRIEF_SHA256,
        "section_54_physics_and_thresholds_unchanged": True,
        "section_32_is_current_execution_boundary": True,
    }
    payload["claim_boundary"]["v02_is_serialization_boundary_repair_only"] = True
    runtime = payload["runtime"]
    runtime["calculation_started_at_utc"] = runtime.pop("execution_started_at_utc")
    runtime["calculation_finished_at_utc"] = runtime.pop("execution_finished_at_utc")
    runtime["calculation_elapsed_seconds"] = runtime.pop("execution_elapsed_seconds")
    runtime["calculation_budget_seconds"] = runtime.pop("execution_budget_seconds")
    runtime["entry_path"] = "scripts/run_paper2_closed_cell_ritz_probe_v02.py"
    runtime["entry_sha256"] = _sha256(Path(__file__))
    runtime["output_stage"] = {
        "complete_payload_is_serialized_with_allow_nan_false_and_parsed_before_open_x": True,
        "preopen_validation_started_at_utc": preopen_started.isoformat(),
        "write_and_postsave_elapsed_not_embedded_in_create_only_payload": True,
        "postsave_readback_required_before_delivery": True,
    }
    payload["serialization_regression"] = SERIALIZATION_REGRESSION
    payload["frozen_source_verification"] = FROZEN_SOURCE_VERIFICATION
    payload["v01_failed_attempt_provenance"] = {
        "runner_path": "scripts/run_paper2_closed_cell_ritz_probe_v01.py",
        "runner_sha256": V01_RUNNER_SHA256,
        "failed_output_path": "results/paper2_closed_cell_ritz_probe/v01_20260905/summary.json",
        "failed_output_sha256": V01_FAILED_SHA256,
        "failed_output_bytes": V01_FAILED_BYTES,
        "failure_stage": "JSON serialization stopped at checks.Ritz_reduced_residual.pass",
        "failure_type": "np.bool_ rejected by the default JSON encoder",
        "algebraic_right_sides_attempted": 6,
        "accepted_results": 0,
        "exact_calculation_seconds": None,
        "preparation_to_failed_output_seconds_reserved_conservatively": V01_RESERVED_SECONDS,
        "reserved_interval_is_not_exact_calculation_time": True,
    }
    payload["existing_compute_ledger_unchanged"] = {
        "completed_periodic_cases": 46,
        "completed_static_FEM_right_sides": 30,
        "old_FEM_and_failure_seconds": OLD_FEM_SECONDS,
        "v01_cell_algebraic_right_sides_attempted": 6,
        "v01_cell_results_accepted": 0,
        "v01_conservative_reserved_seconds_including_preparation": V01_RESERVED_SECONDS,
        "old_FEM_plus_v01_conservative_reserved_seconds": OLD_FEM_SECONDS + V01_RESERVED_SECONDS,
        "v02_cell_algebraic_right_sides": 6,
        "v02_cell_calculation_seconds_recorded_separately": runtime["calculation_elapsed_seconds"],
        "serialization_regression_model_right_sides": 0,
    }
    payload["next_gate"] = "SUPERVISOR_INDEPENDENT_RECOMPUTATION_STOP"

    provisional = _json_ready(payload)
    provisional_text = json.dumps(provisional, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(provisional_text) != provisional:
        raise RuntimeError("complete preopen payload round-trip mismatch")
    preopen_finished = datetime.now(timezone.utc)
    runtime["output_stage"]["preopen_validation_finished_at_utc"] = preopen_finished.isoformat()
    runtime["output_stage"]["preopen_validation_elapsed_seconds"] = time.perf_counter() - preopen_timer

    final_payload = _json_ready(payload)
    final_text = json.dumps(final_payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(final_text) != final_payload:
        raise RuntimeError("final preopen payload round-trip mismatch")
    final_serialized = datetime.now(timezone.utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_started = datetime.now(timezone.utc)
    write_timer = time.perf_counter()
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(final_text)
        handle.flush()
        os.fsync(handle.fileno())
    write_finished = datetime.now(timezone.utc)
    saved_text = path.read_text(encoding="utf-8")
    saved_payload = json.loads(saved_text)
    if saved_text != final_text or saved_payload != final_payload:
        raise RuntimeError("postsave byte/text/JSON readback mismatch")
    verified = datetime.now(timezone.utc)
    WRITER_AUDIT.update(
        {
            "final_serialization_finished_at_utc": final_serialized.isoformat(),
            "write_started_at_utc": write_started.isoformat(),
            "write_finished_at_utc": write_finished.isoformat(),
            "write_elapsed_seconds": time.perf_counter() - write_timer,
            "postsave_readback_verified_at_utc": verified.isoformat(),
            "postsave_readback_pass": True,
            "output_bytes": path.stat().st_size,
            "output_sha256": _sha256(path),
        }
    )


def _load_v01_module() -> Any:
    sys.dont_write_bytecode = True
    specification = importlib.util.spec_from_file_location("closed_cell_ritz_v01_frozen", V01_RUNNER)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load frozen v01 runner")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main() -> int:
    global SERIALIZATION_REGRESSION, FROZEN_SOURCE_VERIFICATION
    if (REPO_ROOT / V02_OUTPUT).exists():
        raise RuntimeError("v02 authorized output is already occupied")
    SERIALIZATION_REGRESSION = _serialization_regression()
    FROZEN_SOURCE_VERIFICATION = _verify_frozen_sources()
    module = _load_v01_module()
    module.FROZEN_COMMIT = FROZEN_COMMIT
    module.PLAN_SHA256 = PLAN_SHA256
    module.BRIEF_SHA256 = BRIEF_SHA256
    module.EXPECTED_OUTPUT = V02_OUTPUT
    module._write_exclusive = _safe_write_exclusive
    result = int(module.main())
    if result != 0:
        return result
    output = REPO_ROOT / V02_OUTPUT
    if not output.exists():
        raise RuntimeError("v02 main returned success without an output")
    reloaded = json.loads(output.read_text(encoding="utf-8"))
    if reloaded["status"] != "COMPLETED_BOUNDED_IDEAL_PROTOTYPE_V02":
        raise RuntimeError("v02 postsave status mismatch")
    print("V02_POSTSAVE_AUDIT " + json.dumps(WRITER_AUDIT, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
