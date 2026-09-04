#!/usr/bin/env python3
"""Execute the frozen v06 identity gate by read-only source post-processing."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from paper2_m2.identity_gate_v06 import (  # noqa: E402
    calibration_audit_only,
    classify_identity_records,
    endpoint_key,
    evaluate_identity_gate,
    field_diagnostics_audit_only,
    finite_tree,
    load_dynamic_observations,
    numerical_change_envelope,
    sha256_file,
    structural_control_audit,
)
from paper2_m2.protocol_v06 import FROZEN_PROTOCOL_V06  # noqa: E402


SOURCE_SPECS = {
    "T64": {
        "relative_path": "results/paper2_m2/identity_2d_v03_t64_v01_20260903",
        "decision": "T64_NUMERICAL_PASS_V03",
        "stage_file": "stage_T64_gate.json",
        "numerical_field": "all_T64_numerical_gates_pass",
        "steps": 64,
    },
    "T128": {
        "relative_path": "results/paper2_m2/identity_2d_v04_t128_v02_20260903",
        "decision": "T128_STAGE_PASS_V04",
        "stage_file": "stage_T128_gate.json",
        "numerical_field": "all_T128_numerical_gates_pass",
        "steps": 128,
    },
    "T256": {
        "relative_path": "results/paper2_m2/identity_2d_v05_t256_v02_20260904",
        "decision": "T256_TIME_CONVERGENCE_PASS_V05",
        "stage_file": "stage_T256_gate.json",
        "numerical_field": "all_T256_numerical_gates_pass",
        "steps": 256,
    },
}


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-t64-dir", type=Path, required=True)
    parser.add_argument("--source-t128-dir", type=Path, required=True)
    parser.add_argument("--source-t256-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", type=str, required=True)
    return parser.parse_args()


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not finite_tree(payload):
        raise ValueError(f"non-finite JSON value in {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _write_hash_ledger(output_dir: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for path in sorted(item for item in output_dir.rglob("*") if item.is_file()):
        if path.name == "hash_ledger.json":
            continue
        relative = path.relative_to(output_dir).as_posix()
        files[relative] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    payload = {"schema": "paper2_m2a_v06_hash_ledger", "files": files}
    _write_json(output_dir / "hash_ledger.json", payload)
    return payload


def _git_head() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _peak_memory_gib() -> float:
    memory = psutil.Process().memory_info()
    peak_bytes = getattr(memory, "peak_wset", memory.rss)
    return float(peak_bytes / (1024.0**3))


def _current_package_snapshot(source_dir: Path) -> dict[str, str]:
    ledger = _load_json(source_dir / "hash_ledger.json")
    snapshot = {
        relative: sha256_file(source_dir / relative)
        for relative in sorted(ledger["files"])
    }
    snapshot["hash_ledger.json"] = sha256_file(source_dir / "hash_ledger.json")
    return snapshot


def _validate_source_package(
    *,
    label: str,
    source_dir: Path,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    failures: list[str] = []
    required = (
        "run_manifest.json",
        "hash_ledger.json",
        "pass_summary.json",
        "endpoint_summaries.json",
        "structural_gates.json",
        spec["stage_file"],
        "finite_value_audit.json",
    )
    for name in required:
        if not (source_dir / name).is_file():
            failures.append(f"missing:{name}")
    if failures:
        return (
            {
                "label": label,
                "source_dir": str(source_dir),
                "pass": False,
                "failures": failures,
            },
            {},
            {},
            {},
        )

    ledger = _load_json(source_dir / "hash_ledger.json")
    summary = _load_json(source_dir / "pass_summary.json")
    manifest = _load_json(source_dir / "run_manifest.json")
    summaries = _load_json(source_dir / "endpoint_summaries.json")
    structural = _load_json(source_dir / "structural_gates.json")
    stage_gate = _load_json(source_dir / spec["stage_file"])
    finite_audit = _load_json(source_dir / "finite_value_audit.json")

    hash_failures: list[str] = []
    snapshot: dict[str, str] = {}
    for relative, expected in sorted(ledger.get("files", {}).items()):
        path = source_dir / relative
        if not path.is_file():
            hash_failures.append(f"missing:{relative}")
            continue
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size
        snapshot[relative] = actual_hash
        if actual_hash != expected.get("sha256") or actual_size != expected.get("bytes"):
            hash_failures.append(f"mismatch:{relative}")
    snapshot["hash_ledger.json"] = sha256_file(source_dir / "hash_ledger.json")
    actual_files = {
        path.relative_to(source_dir).as_posix()
        for path in source_dir.rglob("*")
        if path.is_file() and path.name != "hash_ledger.json"
    }
    ledger_files = set(ledger.get("files", {}))
    if actual_files != ledger_files:
        failures.append("hash_ledger_file_set_mismatch")
    failures.extend(hash_failures)

    json_failures: list[str] = []
    for path in sorted(source_dir.rglob("*.json")):
        try:
            _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            json_failures.append(f"{path.name}:{type(error).__name__}")
    failures.extend(f"json:{item}" for item in json_failures)

    expected_endpoint_count = 54
    expected_dynamic_npz = 12
    dynamic_files = sorted((source_dir / "selected_dynamic_holdouts").glob("*.npz"))
    checks = {
        "status_complete": summary.get("status") == "COMPLETE_AT_SUPERVISOR_GATE",
        "decision_match": summary.get("decision") == spec["decision"],
        "endpoint_count": summary.get("completed_endpoints") == expected_endpoint_count
        and summary.get("expected_endpoints") == expected_endpoint_count
        and len(summaries) == expected_endpoint_count,
        "structural_count_and_pass": len(structural) == expected_endpoint_count
        and all(record.get("pass") is True for record in structural.values()),
        "summary_structural_pass": summary.get("all_structural_gates_pass") is True,
        "summary_numerical_pass": summary.get(spec["numerical_field"]) is True,
        "stage_gate_pass": stage_gate.get("pass") is True,
        "stage_gate_counts": stage_gate.get("counts")
        == {
            "spatial": 74,
            "cycle": 54,
            "hotspot": 2,
            "spatial_pass": 74,
            "cycle_pass": 54,
            "hotspot_pass": 2,
        },
        "finite_audit_pass": finite_audit.get("pass") is True,
        "dynamic_npz_count": len(dynamic_files) == expected_dynamic_npz,
        "read_only_unchanged": summary.get("read_only_unchanged") is True,
    }
    if label == "T256":
        time_gate = _load_json(source_dir / "T64_T128_T256_time_gate.json")
        checks["three_level_time_gate"] = bool(
            time_gate.get("pass") is True
            and time_gate.get("record_count") == 74
            and summary.get("three_level_time_gate", {}).get("pass") is True
            and summary.get("three_level_time_gate", {}).get("record_count") == 74
        )
    for check_name, passed in checks.items():
        if not passed:
            failures.append(f"check:{check_name}")

    implementation_hashes = manifest.get("implementation_sha256", {})
    implementation_failures: list[str] = []
    for relative, expected_hash in sorted(implementation_hashes.items()):
        path = PROJECT_ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            implementation_failures.append(relative)
    failures.extend(f"implementation_hash:{item}" for item in implementation_failures)
    lock = {
        "schema": "paper2_m2a_v06_source_package_lock",
        "label": label,
        "source_dir": str(source_dir),
        "source_manifest_schema": manifest.get("schema"),
        "source_summary_decision": summary.get("decision"),
        "hash_ledger_sha256": snapshot["hash_ledger.json"],
        "hash_ledger_entries": len(ledger_files),
        "hash_failures": hash_failures,
        "all_nonledger_files_listed": actual_files == ledger_files,
        "json_files": len(list(source_dir.rglob("*.json"))),
        "json_failures": json_failures,
        "dynamic_npz_found": len(dynamic_files),
        "implementation_hashes_checked": len(implementation_hashes),
        "implementation_hash_failures": implementation_failures,
        "checks": checks,
        "failures": failures,
        "pass": not failures,
    }
    return lock, summaries, structural, snapshot


def _load_observation_matrix(
    source_dir: Path,
    *,
    steps: int,
    include_fields: bool,
) -> dict[str, dict[str, dict[str, Any]]]:
    protocol = FROZEN_PROTOCOL_V06
    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for case_id in protocol.holdout_cases:
        matrix[case_id] = {}
        for representation in protocol.representations:
            key = endpoint_key(case_id, representation, protocol.spatial_level, steps)
            path = source_dir / "selected_dynamic_holdouts" / f"{key}.npz"
            if not path.is_file():
                raise FileNotFoundError(f"missing frozen dynamic holdout: {path}")
            matrix[case_id][representation] = load_dynamic_observations(
                path,
                case_id=case_id,
                steps_per_cycle=steps,
                include_fields=include_fields,
                protocol=protocol,
            )
    return matrix


def _summary_from_identity(
    identity: dict[str, Any],
    *,
    preflight_pass: bool,
    sources_unchanged: bool,
    elapsed_seconds: float,
    peak_memory_gib: float,
) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V06
    resource_pass = bool(
        elapsed_seconds <= protocol.total_runtime_budget_seconds
        and peak_memory_gib <= protocol.peak_memory_budget_gib
    )
    final_decision = (
        identity["decision"]
        if preflight_pass and sources_unchanged and resource_pass
        else "BLOCKED"
    )
    return {
        "schema": "paper2_m2a_v06_identity_gate_pass_summary",
        "status": (
            "COMPLETE_AT_SUPERVISOR_GATE"
            if final_decision != "BLOCKED"
            else "FAIL_CLOSED_AT_SUPERVISOR_GATE"
        ),
        "decision": final_decision,
        "candidate_identity_decision": identity["decision"],
        "identity_gate_execution_complete": final_decision != "BLOCKED",
        "all_formal_identity_thresholds_pass": identity[
            "all_formal_identity_thresholds_pass"
        ],
        "formal_holdout_cases": identity["formal_holdout_cases"],
        "formal_record_count": identity["formal_record_count"],
        "transferable_cases": identity["transferable_cases"],
        "nontransferable_cases": identity["nontransferable_cases"],
        "no_go_failures": identity["no_go_failures"],
        "maybe_flags": identity["maybe_flags"],
        "preflight_pass": preflight_pass,
        "source_packages_unchanged": sources_unchanged,
        "resource": {
            "elapsed_seconds": elapsed_seconds,
            "budget_seconds": protocol.total_runtime_budget_seconds,
            "peak_memory_gib": peak_memory_gib,
            "memory_budget_gib": protocol.peak_memory_budget_gib,
            "within_budget": resource_pass,
            "cpu_processes": protocol.cpu_processes,
            "gpu_used": False,
            "network_used": False,
            "solver_or_endpoint_run": False,
        },
        "stop_boundary": {
            "M2B_run": False,
            "S5_run": False,
            "three_dimensional_run": False,
            "whole_atrium_run": False,
            "CFD_or_FSI_run": False,
            "GPU_used": False,
            "new_solver_used": False,
        },
        "evidence_boundary": (
            "The decision applies only to the six preregistered holdouts in the frozen "
            "idealized two-dimensional S4/T256/D0 benchmark. It is not physiological, "
            "three-dimensional, organ-scale, EFE, fluid, or experimental evidence."
        ),
    }


def main() -> None:
    arguments = _parse_arguments()
    protocol = FROZEN_PROTOCOL_V06.checked()
    started = time.perf_counter()

    source_dirs = {
        "T64": _resolved(arguments.source_t64_dir),
        "T128": _resolved(arguments.source_t128_dir),
        "T256": _resolved(arguments.source_t256_dir),
    }
    output_dir = _resolved(arguments.output_dir)
    contract = _resolved(arguments.contract)
    authorization = _resolved(arguments.authorization)
    expected_output = _resolved(
        PROJECT_ROOT / "results/paper2_m2/identity_gate_v06_v01_20260904"
    )
    path_failures: list[str] = []
    for label, spec in SOURCE_SPECS.items():
        expected = _resolved(PROJECT_ROOT / spec["relative_path"])
        if source_dirs[label] != expected:
            path_failures.append(f"{label}_source_path_mismatch")
    if output_dir != expected_output:
        path_failures.append("output_path_mismatch")
    expected_contract = _resolved(
        PROJECT_ROOT
        / "project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md"
    )
    expected_authorization = _resolved(
        PROJECT_ROOT
        / "project_control/paper2_m2a_v05_1_t256_supervisor_acceptance_and_identity_gate_decision_v01.md"
    )
    if contract != expected_contract:
        path_failures.append("contract_path_mismatch")
    if authorization != expected_authorization:
        path_failures.append("authorization_path_mismatch")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")

    source_locks: dict[str, Any] = {}
    summaries_by_level: dict[str, dict[str, Any]] = {}
    structural_by_level: dict[str, dict[str, Any]] = {}
    source_snapshots_before: dict[str, dict[str, str]] = {}
    try:
        for label, spec in SOURCE_SPECS.items():
            lock, summaries, structural, snapshot = _validate_source_package(
                label=label, source_dir=source_dirs[label], spec=spec
            )
            source_locks[label] = lock
            summaries_by_level[label] = summaries
            structural_by_level[label] = structural
            source_snapshots_before[label] = snapshot
        v01_gain_source = PROJECT_ROOT / "scripts/run_paper2_m2_identity_2d_v01.py"
        v01_gain_source_hash = sha256_file(v01_gain_source)
        gain_operator_lock = {
            "source": protocol.combined_gain_operator_source,
            "expected_sha256": protocol.combined_gain_operator_source_sha256,
            "actual_sha256": v01_gain_source_hash,
            "pass": v01_gain_source_hash
            == protocol.combined_gain_operator_source_sha256,
            "post_hoc_operator": False,
        }
        preflight_pass = bool(
            not path_failures
            and all(lock.get("pass") for lock in source_locks.values())
            and gain_operator_lock["pass"]
            and "passed" in arguments.host_pytest_summary
        )
        preflight = {
            "schema": "paper2_m2a_v06_preflight",
            "path_failures": path_failures,
            "source_locks": source_locks,
            "frozen_combined_load_gain_operator_lock": gain_operator_lock,
            "host_pytest_summary": arguments.host_pytest_summary,
            "solver_or_endpoint_run": False,
            "pass": preflight_pass,
        }
        if not preflight_pass:
            raise RuntimeError("v06 source/path/test preflight failed")

        observations_t128 = _load_observation_matrix(
            source_dirs["T128"], steps=128, include_fields=False
        )
        observations_t256 = _load_observation_matrix(
            source_dirs["T256"], steps=256, include_fields=True
        )
        identity = evaluate_identity_gate(
            summaries_t256=summaries_by_level["T256"],
            observations_t256=observations_t256,
            protocol=protocol,
        )
        envelope = numerical_change_envelope(
            summaries_t128=summaries_by_level["T128"],
            summaries_t256=summaries_by_level["T256"],
            observations_t128=observations_t128,
            observations_t256=observations_t256,
            protocol=protocol,
        )
        calibration = calibration_audit_only(
            summaries_by_level["T256"], protocol
        )
        fields = field_diagnostics_audit_only(observations_t256, protocol)
        structure_control = structural_control_audit(
            summaries_by_level["T256"], structural_by_level["T256"], protocol
        )
        preflight["structural_control"] = structure_control

        source_snapshots_after = {
            label: _current_package_snapshot(source_dirs[label])
            for label in SOURCE_SPECS
        }
        sources_unchanged = source_snapshots_after == source_snapshots_before
        elapsed_seconds = time.perf_counter() - started
        peak_memory_gib = _peak_memory_gib()
        summary = _summary_from_identity(
            identity,
            preflight_pass=preflight_pass,
            sources_unchanged=sources_unchanged,
            elapsed_seconds=elapsed_seconds,
            peak_memory_gib=peak_memory_gib,
        )
        identity_summary = {
            "schema": "paper2_m2a_v06_identity_gate_summary",
            "decision": summary["decision"],
            "formal_holdout_count": len(protocol.holdout_cases),
            "formal_record_count": identity["formal_record_count"],
            "transferable_cases": identity["transferable_cases"],
            "nontransferable_cases": identity["nontransferable_cases"],
            "no_go_failures": identity["no_go_failures"],
            "maybe_flags": identity["maybe_flags"],
            "calibration_cases_used_for_identity_pass_count": 0,
            "interfaces_gated_separately": ["myocardium_ecm", "endocardium_ecm"],
            "combined_gain_operator_source": protocol.combined_gain_operator_source,
            "identity_difference_reduced_by_numerical_envelope": False,
            "evidence_boundary": identity["evidence_boundary"],
        }
        protocol_payload = protocol.as_dict()
        protocol_digest = __import__("hashlib").sha256(
            json.dumps(protocol_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        implementation_paths = (
            "src/paper2_m2/protocol_v06.py",
            "src/paper2_m2/identity_gate_v06.py",
            "scripts/run_paper2_m2_identity_gate_v06.py",
            "tests/paper2_m2/test_protocol_v06.py",
            "tests/paper2_m2/test_identity_gate_v06.py",
        )
        run_manifest = {
            "schema": "paper2_m2a_v06_identity_gate_manifest",
            "protocol": protocol_payload,
            "protocol_digest": protocol_digest,
            "provenance": {
                "contract": str(contract),
                "contract_sha256": sha256_file(contract),
                "authorization": str(authorization),
                "authorization_sha256": sha256_file(authorization),
                "baseline_git_head": _git_head(),
                "source_packages": {
                    label: str(path) for label, path in source_dirs.items()
                },
                "source_sha256_before": source_snapshots_before,
                "source_sha256_after": source_snapshots_after,
                "source_packages_unchanged": sources_unchanged,
                "frozen_combined_load_gain_operator": gain_operator_lock,
            },
            "implementation_sha256": {
                relative: sha256_file(PROJECT_ROOT / relative)
                for relative in implementation_paths
            },
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "platform": platform.platform(),
                "cpu_processes": 1,
                "gpu_used": False,
                "network_used": False,
                "solver_or_endpoint_run": False,
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
                "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
                "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            },
            "output_contract": {
                "create_only": True,
                "json_only": True,
                "new_npz_created": False,
            },
        }
        output_dir.mkdir(parents=True, exist_ok=False)
        _write_json(output_dir / "preflight.json", preflight)
        _write_json(output_dir / "identity_gate_by_case.json", identity)
        _write_json(output_dir / "identity_gate_summary.json", identity_summary)
        _write_json(output_dir / "numerical_change_envelope.json", envelope)
        _write_json(output_dir / "calibration_audit_only.json", calibration)
        _write_json(output_dir / "field_diagnostics_audit_only.json", fields)
        _write_json(output_dir / "run_manifest.json", run_manifest)
        _write_json(
            output_dir
            / ("pass_summary.json" if summary["decision"] != "BLOCKED" else "failure_summary.json"),
            summary,
        )
        _write_hash_ledger(output_dir)
        print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    except Exception as error:
        if output_dir.exists():
            raise
        elapsed_seconds = time.perf_counter() - started
        failure = {
            "schema": "paper2_m2a_v06_identity_gate_failure_summary",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "decision": "BLOCKED",
            "reason": f"{type(error).__name__}: {error}",
            "elapsed_seconds": elapsed_seconds,
            "peak_memory_gib": _peak_memory_gib(),
            "solver_or_endpoint_run": False,
            "gpu_used": False,
        }
        minimal_preflight = locals().get(
            "preflight",
            {
                "schema": "paper2_m2a_v06_preflight",
                "path_failures": path_failures,
                "source_locks": source_locks,
                "pass": False,
            },
        )
        minimal_manifest = {
            "schema": "paper2_m2a_v06_identity_gate_manifest_blocked",
            "protocol": protocol.as_dict(),
            "baseline_git_head": _git_head(),
            "solver_or_endpoint_run": False,
            "gpu_used": False,
            "network_used": False,
        }
        output_dir.mkdir(parents=True, exist_ok=False)
        _write_json(output_dir / "preflight.json", minimal_preflight)
        _write_json(output_dir / "run_manifest.json", minimal_manifest)
        _write_json(output_dir / "failure_summary.json", failure)
        _write_hash_ledger(output_dir)
        print(json.dumps(failure, indent=2, sort_keys=True), flush=True)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()

