#!/usr/bin/env python3
"""Execute the frozen v07 read-only diagnosis of the v06.1 NO-GO-ID result."""

from __future__ import annotations

import argparse
import importlib.util
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

from paper2_m2.identity_no_go_diagnostic_v07 import (  # noqa: E402
    build_diagnostic_classification,
    build_pure_mode_transfer_audit,
    build_signed_permutation_basis_audit,
    build_source_formula_audit,
    build_spatiotemporal_mode_decomposition,
    build_superposition_audit,
    build_traction_scale_direction_components,
    finite_tree,
    sha256_file,
)


EXPECTED_BASELINE_GIT_HEAD = "7c1c1fcbe8ec424f953b18daab7fe682b2c10cfc"
EXPECTED_IDENTITY_RESULT = "results/paper2_m2/identity_gate_v06_v02_20260904"
EXPECTED_T128 = "results/paper2_m2/identity_2d_v04_t128_v02_20260903"
EXPECTED_T256 = "results/paper2_m2/identity_2d_v05_t256_v02_20260904"
EXPECTED_OUTPUT = "results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904"
EXPECTED_CONTRACT = (
    "project_control/paper2_m2_active_myocardial_fem_identity_failure_diagnostic_contract_v07.md"
)
EXPECTED_AUTHORIZATION = (
    "project_control/"
    "paper2_m2a_v06_1_no_go_identity_supervisor_acceptance_and_v07_diagnostic_decision_v01.md"
)
RESOURCE_BUDGET_SECONDS = 600.0
MEMORY_BUDGET_GIB = 8.0


def _load_script_module(name: str, relative_path: str) -> Any:
    path = PROJECT_ROOT / relative_path
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


V06_RUNNER = _load_script_module(
    "paper2_m2_v06_frozen_runner", "scripts/run_paper2_m2_identity_gate_v06.py"
)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-result-dir", type=Path, required=True)
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
        payload = json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    if not finite_tree(payload):
        raise ValueError(f"non-finite JSON value in {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    if not finite_tree(payload):
        raise ValueError(f"refusing to write non-finite JSON payload to {path}")
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
    payload = {"schema": "paper2_m2a_v07_hash_ledger", "files": files}
    _write_json(output_dir / "hash_ledger.json", payload)
    return payload


def _git_revision(reference: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", reference],
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


def _host_tests_pass(summary: str) -> bool:
    lowered = summary.lower()
    return "passed" in lowered and "failed" not in lowered and "error" not in lowered


def _snapshot_paths(relative_paths: list[str]) -> dict[str, str]:
    return {
        relative: sha256_file(PROJECT_ROOT / relative)
        for relative in sorted(set(relative_paths))
    }


def _validate_ledger_package(package_dir: Path) -> tuple[dict[str, Any], dict[str, str]]:
    failures: list[str] = []
    ledger_path = package_dir / "hash_ledger.json"
    if not ledger_path.is_file():
        return (
            {
                "schema": "paper2_m2a_v07_identity_result_source_lock",
                "source_dir": str(package_dir),
                "failures": ["missing:hash_ledger.json"],
                "pass": False,
            },
            {},
        )
    ledger = _load_json(ledger_path)
    ledger_files = set(ledger.get("files", {}))
    actual_files = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file() and path.name != "hash_ledger.json"
    }
    if ledger_files != actual_files:
        failures.append("hash_ledger_file_set_mismatch")
    snapshot: dict[str, str] = {}
    for relative, expected in sorted(ledger.get("files", {}).items()):
        path = package_dir / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        actual_hash = sha256_file(path)
        snapshot[relative] = actual_hash
        if (
            actual_hash != expected.get("sha256")
            or path.stat().st_size != expected.get("bytes")
        ):
            failures.append(f"mismatch:{relative}")
    snapshot["hash_ledger.json"] = sha256_file(ledger_path)
    json_failures: list[str] = []
    for path in sorted(package_dir.rglob("*.json")):
        try:
            _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            json_failures.append(f"{path.name}:{type(error).__name__}")
    failures.extend(f"json:{failure}" for failure in json_failures)
    summary = _load_json(package_dir / "pass_summary.json")
    classification = _load_json(package_dir / "classification_audit.json")
    manifest = _load_json(package_dir / "run_manifest.json")
    checks = {
        "decision_is_NO_GO_ID": summary.get("decision") == "NO-GO-ID",
        "formal_record_count_is_45": summary.get("formal_record_count") == 45,
        "severity_counts_are_35_4_6": classification.get("severity_counts")
        == {"pass": 35, "maybe": 4, "no_go": 6},
        "classification_recompute_pass": classification.get("pass") is True,
        "source_packages_unchanged": manifest.get("provenance", {}).get(
            "source_packages_unchanged"
        )
        is True,
        "finite_audit_pass": _load_json(package_dir / "finite_value_audit.json").get(
            "pass"
        )
        is True,
        "no_npz": not list(package_dir.rglob("*.npz")),
    }
    implementation_failures: list[str] = []
    for relative, expected_hash in sorted(
        manifest.get("implementation_sha256", {}).items()
    ):
        path = PROJECT_ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            implementation_failures.append(relative)
    if implementation_failures:
        failures.extend(
            f"implementation_hash:{relative}"
            for relative in implementation_failures
        )
    for name, passed in checks.items():
        if not passed:
            failures.append(f"check:{name}")
    return (
        {
            "schema": "paper2_m2a_v07_identity_result_source_lock",
            "source_dir": str(package_dir),
            "hash_ledger_entries": len(ledger_files),
            "all_nonledger_files_listed": ledger_files == actual_files,
            "json_failures": json_failures,
            "implementation_hash_failures": implementation_failures,
            "checks": checks,
            "failures": failures,
            "pass": not failures,
        },
        snapshot,
    )


def main() -> None:
    arguments = _parse_arguments()
    started = time.perf_counter()
    identity_result_dir = _resolved(arguments.identity_result_dir)
    source_t128_dir = _resolved(arguments.source_t128_dir)
    source_t256_dir = _resolved(arguments.source_t256_dir)
    output_dir = _resolved(arguments.output_dir)
    contract = _resolved(arguments.contract)
    authorization = _resolved(arguments.authorization)
    expected_paths = {
        "identity_result": _resolved(PROJECT_ROOT / EXPECTED_IDENTITY_RESULT),
        "T128": _resolved(PROJECT_ROOT / EXPECTED_T128),
        "T256": _resolved(PROJECT_ROOT / EXPECTED_T256),
        "output": _resolved(PROJECT_ROOT / EXPECTED_OUTPUT),
        "contract": _resolved(PROJECT_ROOT / EXPECTED_CONTRACT),
        "authorization": _resolved(PROJECT_ROOT / EXPECTED_AUTHORIZATION),
    }
    actual_paths = {
        "identity_result": identity_result_dir,
        "T128": source_t128_dir,
        "T256": source_t256_dir,
        "output": output_dir,
        "contract": contract,
        "authorization": authorization,
    }
    path_failures = [
        f"{name}_path_mismatch"
        for name in expected_paths
        if actual_paths[name] != expected_paths[name]
    ]
    baseline_head = _git_revision("HEAD")
    upstream_head = _git_revision("@{upstream}")
    if baseline_head != EXPECTED_BASELINE_GIT_HEAD:
        path_failures.append("baseline_git_head_mismatch")
    if upstream_head != EXPECTED_BASELINE_GIT_HEAD:
        path_failures.append("upstream_git_head_mismatch")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")

    source_locks: dict[str, Any] = {}
    source_package_snapshots_before: dict[str, dict[str, str]] = {}
    read_only_source_before: dict[str, str] = {}
    try:
        identity_lock, identity_snapshot = _validate_ledger_package(
            identity_result_dir
        )
        source_locks["v06_1_identity"] = identity_lock
        source_package_snapshots_before["v06_1_identity"] = identity_snapshot
        summaries_by_level: dict[str, dict[str, Any]] = {}
        structural_by_level: dict[str, dict[str, Any]] = {}
        for label, source_dir in (("T128", source_t128_dir), ("T256", source_t256_dir)):
            lock, summaries, structural, snapshot = V06_RUNNER._validate_source_package(
                label=label,
                source_dir=source_dir,
                spec=V06_RUNNER.SOURCE_SPECS[label],
            )
            source_locks[label] = lock
            summaries_by_level[label] = summaries
            structural_by_level[label] = structural
            source_package_snapshots_before[label] = snapshot

        identity_manifest = _load_json(identity_result_dir / "run_manifest.json")
        read_only_source_paths = list(
            identity_manifest.get("implementation_sha256", {}).keys()
        ) + [
            "src/paper2_m2/config.py",
            "src/paper2_m2/identity_2d.py",
            "src/paper2_m2/identity_2d_v02.py",
            "src/paper2_m2/identity_2d_v05.py",
            "src/paper2_m2/interface_projection.py",
            EXPECTED_CONTRACT,
            EXPECTED_AUTHORIZATION,
        ]
        read_only_source_before = _snapshot_paths(read_only_source_paths)
        preflight_pass = bool(
            not path_failures
            and all(lock.get("pass") for lock in source_locks.values())
            and _host_tests_pass(arguments.host_pytest_summary)
        )
        preflight = {
            "schema": "paper2_m2a_v07_preflight",
            "path_failures": path_failures,
            "baseline_git_head": baseline_head,
            "upstream_git_head": upstream_head,
            "source_locks": source_locks,
            "host_pytest_summary": arguments.host_pytest_summary,
            "host_tests_pass": _host_tests_pass(arguments.host_pytest_summary),
            "solver_or_endpoint_run": False,
            "pass": preflight_pass,
        }
        if not preflight_pass:
            raise RuntimeError("v07 source/path/test preflight failed")

        observations_t128 = V06_RUNNER._load_observation_matrix(
            source_t128_dir, steps=128, include_fields=False
        )
        observations_t256 = V06_RUNNER._load_observation_matrix(
            source_t256_dir, steps=256, include_fields=False
        )
        traction_audit, failed_arrays = build_traction_scale_direction_components(
            observations_t256
        )
        mode_audit = build_spatiotemporal_mode_decomposition(observations_t256)
        basis_audit = build_signed_permutation_basis_audit(failed_arrays)
        pure_mode_audit = build_pure_mode_transfer_audit(
            observations_t256, summaries_by_level["T256"]
        )
        superposition_audit = build_superposition_audit(
            observations_t128, observations_t256
        )
        source_formula_audit = build_source_formula_audit(PROJECT_ROOT)
        classification = build_diagnostic_classification(
            traction_audit=traction_audit,
            basis_audit=basis_audit,
            mode_audit=mode_audit,
            source_audit=source_formula_audit,
        )
        if classification["v06_1_identity_decision_changed"]:
            raise RuntimeError("v07 attempted to change the frozen NO-GO-ID decision")

        source_package_snapshots_after = {
            "v06_1_identity": _validate_ledger_package(identity_result_dir)[1],
            "T128": V06_RUNNER._current_package_snapshot(source_t128_dir),
            "T256": V06_RUNNER._current_package_snapshot(source_t256_dir),
        }
        read_only_source_after = _snapshot_paths(read_only_source_paths)
        source_packages_unchanged = (
            source_package_snapshots_before == source_package_snapshots_after
        )
        source_files_unchanged = read_only_source_before == read_only_source_after
        elapsed_seconds = time.perf_counter() - started
        peak_memory_gib = _peak_memory_gib()
        resource_pass = bool(
            elapsed_seconds <= RESOURCE_BUDGET_SECONDS
            and peak_memory_gib <= MEMORY_BUDGET_GIB
        )
        if not source_packages_unchanged or not source_files_unchanged:
            raise RuntimeError("v07 read-only source changed during execution")
        if not resource_pass:
            raise RuntimeError("v07 resource budget exceeded")
        if not mode_audit["all_energy_closures_pass"]:
            raise RuntimeError("v07 Parseval or spatial energy closure failed")

        summary = {
            "schema": "paper2_m2a_v07_pass_summary",
            "status": "COMPLETE_AT_SUPERVISOR_GATE",
            "diagnostic_label": classification["diagnostic_label"],
            "v06_1_identity_decision": "NO-GO-ID",
            "identity_decision_changed": False,
            "preflight_pass": True,
            "source_packages_unchanged": source_packages_unchanged,
            "source_files_unchanged": source_files_unchanged,
            "formal_failed_traction_record_count": len(failed_arrays),
            "all_energy_closures_pass": mode_audit["all_energy_closures_pass"],
            "resource": {
                "elapsed_seconds": elapsed_seconds,
                "budget_seconds": RESOURCE_BUDGET_SECONDS,
                "peak_memory_gib": peak_memory_gib,
                "memory_budget_gib": MEMORY_BUDGET_GIB,
                "within_budget": resource_pass,
                "cpu_processes": 1,
                "gpu_used": False,
                "network_used": False,
                "docker_used": False,
                "solver_or_endpoint_run": False,
            },
            "stop_boundary": {
                "identity_retry": False,
                "model_or_extraction_change": False,
                "recalibration": False,
                "M2B_run": False,
                "three_dimensional_run": False,
                "whole_atrium_run": False,
                "CFD_or_FSI_run": False,
                "GPU_used": False,
                "new_solver_used": False,
            },
            "evidence_boundary": classification["evidence_boundary"],
        }
        implementation_paths = (
            "src/paper2_m2/identity_no_go_diagnostic_v07.py",
            "scripts/run_paper2_m2_identity_no_go_diagnostic_v07.py",
            "tests/paper2_m2/test_identity_no_go_diagnostic_v07.py",
        )
        run_manifest = {
            "schema": "paper2_m2a_v07_run_manifest",
            "provenance": {
                "contract": str(contract),
                "contract_sha256": sha256_file(contract),
                "authorization": str(authorization),
                "authorization_sha256": sha256_file(authorization),
                "baseline_git_head": baseline_head,
                "upstream_git_head": upstream_head,
                "source_packages": {
                    "v06_1_identity": str(identity_result_dir),
                    "T128": str(source_t128_dir),
                    "T256": str(source_t256_dir),
                },
                "source_package_sha256_before": source_package_snapshots_before,
                "source_package_sha256_after": source_package_snapshots_after,
                "source_packages_unchanged": source_packages_unchanged,
                "read_only_source_sha256_before": read_only_source_before,
                "read_only_source_sha256_after": read_only_source_after,
                "read_only_source_files_unchanged": source_files_unchanged,
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
                "docker_used": False,
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
        artifacts = {
            "preflight.json": preflight,
            "traction_scale_direction_components.json": traction_audit,
            "spatiotemporal_mode_decomposition.json": mode_audit,
            "signed_permutation_basis_audit.json": basis_audit,
            "pure_mode_transfer_audit.json": pure_mode_audit,
            "superposition_audit.json": superposition_audit,
            "source_formula_audit.json": source_formula_audit,
            "diagnostic_classification.json": classification,
            "run_manifest.json": run_manifest,
            "pass_summary.json": summary,
        }
        if not all(finite_tree(payload) for payload in artifacts.values()):
            raise ValueError("non-finite value detected before v07 output creation")
        output_dir.mkdir(parents=True, exist_ok=False)
        for name, payload in artifacts.items():
            _write_json(output_dir / name, payload)
        for name in artifacts:
            _load_json(output_dir / name)
        finite_audit = {
            "schema": "paper2_m2a_v07_finite_value_audit",
            "json_files_checked": sorted(artifacts),
            "json_file_count": len(artifacts),
            "all_json_parse_and_finite": True,
            "new_npz_created": False,
            "pass": True,
        }
        _write_json(output_dir / "finite_value_audit.json", finite_audit)
        _write_hash_ledger(output_dir)
        print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    except Exception as error:
        if output_dir.exists():
            raise
        failure = {
            "schema": "paper2_m2a_v07_failure_summary",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "formal_result": "BLOCKED",
            "diagnostic_label": None,
            "v06_1_identity_decision": "NO-GO-ID",
            "identity_decision_changed": False,
            "reason": f"{type(error).__name__}: {error}",
            "elapsed_seconds": time.perf_counter() - started,
            "peak_memory_gib": _peak_memory_gib(),
            "solver_or_endpoint_run": False,
            "gpu_used": False,
            "docker_used": False,
        }
        minimal_preflight = locals().get(
            "preflight",
            {
                "schema": "paper2_m2a_v07_preflight",
                "path_failures": path_failures,
                "source_locks": source_locks,
                "pass": False,
            },
        )
        minimal_manifest = {
            "schema": "paper2_m2a_v07_run_manifest_blocked",
            "baseline_git_head": baseline_head,
            "upstream_git_head": upstream_head,
            "read_only_source_sha256_before": read_only_source_before,
            "solver_or_endpoint_run": False,
            "gpu_used": False,
            "network_used": False,
            "docker_used": False,
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
