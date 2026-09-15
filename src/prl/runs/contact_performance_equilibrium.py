"""CPU-only runner for the frozen contact-performance/equilibrium contract.

The runner records commands, hashes, timings, and exit states.  Scientific and
numerical adjudication is intentionally implemented in ``prl.verification``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from ..storage import MIB, evaluate_storage, scan_workspace
from ..workspace import find_workspace


RESULT_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915"
)
CLEANUP_VERDICT_RELATIVE = Path(
    "project_control/evidence/repository_cleanup_v01/final_closure_verdict_v01.json"
)
LONG_DOUBLET_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_long_doublet_v01_20260914"
)
BARRIER_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_contact_barrier_v01_20260914"
)


class ContactTaskContractError(RuntimeError):
    """Raised before execution when a frozen precondition is not satisfied."""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_result(workspace: Path, result: Path | str | None) -> Path:
    candidate = workspace / RESULT_RELATIVE if result is None else Path(result)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved_parent = candidate.parent.resolve(strict=True)
    resolved = resolved_parent / candidate.name
    try:
        resolved.relative_to(workspace.resolve(strict=True))
    except ValueError as error:
        raise ContactTaskContractError("result path must stay inside the workspace") from error
    return resolved


def _require_cleanup_and_storage(workspace: Path) -> dict[str, Any]:
    verdict_path = workspace / CLEANUP_VERDICT_RELATIVE
    if not verdict_path.is_file():
        raise ContactTaskContractError("cleanup closure verdict is missing")
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    if verdict.get("status") != "passed":
        raise ContactTaskContractError("cleanup closure has not passed")
    storage = evaluate_storage(
        scan_workspace(workspace),
        planned_new_bytes=256 * MIB,
        stop_reserve_bytes=64 * MIB,
    )
    if storage["status"] != "passed" or not storage["can_start"]:
        raise ContactTaskContractError("storage admission rejected the scientific task")
    return storage


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OMP_DYNAMIC": "FALSE",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
    )
    return environment


def _call(
    command: list[Path | str], workspace: Path, *, timeout_seconds: float
) -> dict[str, Any]:
    rendered = [str(item) for item in command]
    began = time.monotonic()
    try:
        completed = subprocess.run(
            rendered,
            cwd=workspace,
            env=_environment(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "command": rendered,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": time.monotonic() - began,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": rendered,
            "return_code": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "elapsed_seconds": time.monotonic() - began,
            "timed_out": True,
        }


def _run_q(workspace: Path, result: Path, storage: dict[str, Any]) -> dict[str, Any]:
    if result.exists():
        raise ContactTaskContractError(f"create-only result already exists: {result}")
    q_root = result / "Q"
    scaling_root = q_root / "scaling"
    regression_root = q_root / "regression"
    scaling_root.mkdir(parents=True)
    regression_root.mkdir()

    baseline = workspace / "b/z1m0a/Release/prl_myo_contact_scaling_probe_v01.exe"
    candidate = (
        workspace
        / "b/clean-baseline/src/ventricle_simucell3d_m0/Release"
        / "prl_myo_contact_scaling_probe_v01.exe"
    )
    regression_probe = (
        workspace
        / "b/clean-baseline/src/ventricle_simucell3d_m0/Release"
        / "prl_myo_contact_barrier_probe_v01.exe"
    )
    inputs = workspace / LONG_DOUBLET_RELATIVE / "P/inputs"
    barrier = workspace / BARRIER_RELATIVE / "S"
    required = [baseline, candidate, regression_probe, barrier / "verdict.json"]
    required.extend(inputs / f"{count}_cells.mesh" for count in (2, 4, 16))
    if missing := [str(path) for path in required if not path.is_file()]:
        raise ContactTaskContractError(f"required frozen inputs are missing: {missing}")

    _write_json(
        result / "ownership.json",
        {
            "schema_version": "prl.contact_performance_equilibrium.ownership.v1",
            "owner": "Codex",
            "purpose": "frozen CPU-only contact performance and extended equilibrium task",
            "gpu": False,
            "automatic_retries": 0,
            "output_budget_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )
    source_paths = [
        baseline,
        candidate,
        regression_probe,
        workspace
        / "external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp",
        workspace
        / "external/simucell3d/include/contact_models/contact_node_face_via_spring.hpp",
        workspace
        / "project_control/ventricle_contact_performance_and_extended_equilibrium_contract_v01.md",
        *[inputs / f"{count}_cells.mesh" for count in (2, 4, 16)],
    ]
    _write_json(
        result / "source_hashes_before.json",
        {
            str(path.relative_to(workspace)).replace("\\", "/"): _sha256(path)
            for path in source_paths
        },
    )
    _write_json(result / "storage_preflight.json", storage)

    ledger: list[dict[str, Any]] = []
    for count in (2, 4, 16):
        mesh = inputs / f"{count}_cells.mesh"
        for repetition in range(1, 4):
            for implementation, executable in (
                ("baseline", baseline),
                ("candidate", candidate),
            ):
                case = scaling_root / f"{count}_cells_{implementation}_r{repetition}"
                record = _call(
                    [executable, mesh, case, "4", "quadrature", "1.0", ".10"],
                    workspace,
                    timeout_seconds=120,
                )
                record.update(
                    {
                        "kind": "scaling",
                        "cells": count,
                        "implementation": implementation,
                        "repetition": repetition,
                        "output": case.relative_to(result).as_posix(),
                    }
                )
                ledger.append(record)
                _write_json(q_root / "execution_ledger.json", ledger)
                if record["return_code"] != 0:
                    _write_json(
                        q_root / "execution_status.json",
                        {
                            "status": "failed",
                            "reason": "scaling process failed",
                            "calls": len(ledger),
                        },
                    )
                    return {"status": "failed", "phase": "q", "calls": len(ledger)}

    geometry = _call([regression_probe, "--geometry-self-test"], workspace, timeout_seconds=30)
    geometry.update({"kind": "regression", "case": "geometry_self_test", "expected_return_code": 0})
    ledger.append(geometry)
    _write_json(q_root / "execution_ledger.json", ledger)

    for direction in ("END", "SIDE"):
        tag = f"old_failed_{direction}"
        record = _call(
            [regression_probe, barrier / "inputs" / f"{tag}.mesh", regression_root / f"unused_{direction}", "4", "geometry"],
            workspace,
            timeout_seconds=30,
        )
        record.update({"kind": "regression", "case": tag, "expected_return_code": 3})
        ledger.append(record)
        _write_json(q_root / "execution_ledger.json", ledger)

    regression_cases = sorted(
        path.name for path in barrier.iterdir() if path.is_dir() and path.name != "inputs"
    )
    for tag in regression_cases:
        edge = ".05" if tag.endswith("Q005") else ".10"
        adhesion = "0.0" if tag.endswith("adhesion_off") else "1.0"
        case = regression_root / tag
        record = _call(
            [
                regression_probe,
                barrier / "inputs" / f"{tag}.mesh",
                case,
                "4",
                "quadrature",
                adhesion,
                edge,
            ],
            workspace,
            timeout_seconds=45,
        )
        record.update(
            {
                "kind": "regression",
                "case": tag,
                "expected_return_code": 0,
                "output": case.relative_to(result).as_posix(),
            }
        )
        ledger.append(record)
        _write_json(q_root / "execution_ledger.json", ledger)
        if record["return_code"] != 0:
            break

    complete = all(
        item["return_code"] == item.get("expected_return_code", 0) for item in ledger
    )
    execution = {
        "status": "passed" if complete else "failed",
        "phase": "q",
        "calls": len(ledger),
        "scaling_calls": sum(item["kind"] == "scaling" for item in ledger),
        "regression_calls": sum(item["kind"] == "regression" for item in ledger),
        "adjudication": "not_run",
    }
    _write_json(q_root / "execution_status.json", execution)
    return execution


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _run_equilibrium_process(
    command: list[Path | str], workspace: Path, output: Path, result: Path, total_deadline: float
) -> dict[str, Any]:
    rendered = [str(item) for item in command]
    log_path = output.parent / f"{output.name}.log"
    began = time.monotonic()
    stop_reason: str | None = None
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            rendered,
            cwd=workspace,
            env=_environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stop_requested_at: float | None = None
        while process.poll() is None:
            now = time.monotonic()
            if stop_reason is None and _directory_bytes(result) > 256 * MIB:
                stop_reason = "output_budget_exceeded"
            if stop_reason is None and now >= total_deadline:
                stop_reason = "total_wall_budget_exhausted"
            if stop_reason is not None and stop_requested_at is None:
                _write_json(output / "STOP", {"reason": stop_reason})
                stop_requested_at = now
            if stop_requested_at is not None and now - stop_requested_at > 15:
                process.terminate()
            if now - began > 920:
                stop_reason = stop_reason or "case_wall_budget_exhausted"
                process.terminate()
            time.sleep(0.5)
        return_code = process.wait()
    return {
        "command": rendered,
        "return_code": return_code,
        "elapsed_seconds": time.monotonic() - began,
        "stop_reason": stop_reason,
        "output": output.relative_to(result).as_posix(),
        "log": log_path.relative_to(result).as_posix(),
    }


def _run_e(workspace: Path, result: Path, storage: dict[str, Any]) -> dict[str, Any]:
    q_verdict_path = result / "Q/verdict.json"
    if not q_verdict_path.is_file():
        raise ContactTaskContractError("Q independent verdict is missing")
    if json.loads(q_verdict_path.read_text(encoding="utf-8")).get("status") != "passed":
        raise ContactTaskContractError("Q did not pass; equilibrium must remain not_run")
    e_root = result / "E"
    if e_root.exists():
        raise ContactTaskContractError(f"create-only phase already exists: {e_root}")
    e_root.mkdir()
    _write_json(e_root / "storage_preflight.json", storage)

    engine = (
        workspace
        / "b/clean-baseline/src/ventricle_simucell3d_m0/Release"
        / "prl_myo_contact_barrier_relaxation_v01.exe"
    )
    input_root = workspace / BARRIER_RELATIVE / "S/inputs"
    if not engine.is_file():
        raise ContactTaskContractError("candidate equilibrium engine is missing")

    ledger: list[dict[str, Any]] = []
    started = time.monotonic()
    total_deadline = started + 3600
    cases = [(direction, step) for direction in ("END", "SIDE") for step in (0.02, 0.01)]
    for direction, step in cases:
        tag = f"{direction}_DT{step:.2f}"
        mesh = input_root / f"{direction}_G0.07.mesh"
        output = e_root / tag
        steps = round(20 / step)
        record = _run_equilibrium_process(
            [engine, mesh, output, str(step), str(steps), "free", "900"],
            workspace,
            output,
            result,
            total_deadline,
        )
        record.update(
            {
                "case": tag,
                "direction": direction,
                "dt_max": step,
                "requested_coordinate": 20.0,
                "maximum_steps": steps,
                "input_sha256": _sha256(mesh),
            }
        )
        ledger.append(record)
        _write_json(e_root / "execution_ledger.json", ledger)
        if record["return_code"] != 0:
            break

    complete = len(ledger) == len(cases) and all(item["return_code"] == 0 for item in ledger)
    execution = {
        "status": "passed" if complete else "failed",
        "phase": "equilibrium",
        "cases_run": len(ledger),
        "cases_not_run": [f"{d}_DT{s:.2f}" for d, s in cases[len(ledger) :]],
        "elapsed_seconds": time.monotonic() - started,
        "output_bytes": _directory_bytes(result),
        "adjudication": "not_run",
    }
    _write_json(e_root / "execution_status.json", execution)
    return execution


def run_contact_performance_equilibrium(
    workspace: Path | str | None = None,
    result: Path | str | None = None,
    *,
    phase: str = "q",
) -> dict[str, Any]:
    """Run one frozen create-only phase after cleanup/storage admission."""

    root = find_workspace(workspace)
    target = _bounded_result(root, result)
    storage = _require_cleanup_and_storage(root)
    if phase == "q":
        return _run_q(root, target, storage)
    if phase == "equilibrium":
        return _run_e(root, target, storage)
    raise ContactTaskContractError(f"unknown phase: {phase}")
