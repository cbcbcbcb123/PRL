#!/usr/bin/env python3
"""Run the v06 identity gate with the exact v06.1 T64 EOF compatibility."""

from __future__ import annotations

import argparse
import copy
import hashlib
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from paper2_m2.identity_gate_v06 import (  # noqa: E402
    calibration_audit_only,
    classify_identity_records,
    evaluate_identity_gate,
    field_diagnostics_audit_only,
    finite_tree,
    numerical_change_envelope,
    sha256_file,
    structural_control_audit,
)
from paper2_m2.protocol_v06 import FROZEN_PROTOCOL_V06  # noqa: E402
from paper2_m2.protocol_v06_1 import (  # noqa: E402
    FROZEN_TEST_EOF_COMPATIBILITY_V06_1,
    evaluate_exact_test_eof_compatibility,
)


EXPECTED_BASELINE_GIT_HEAD = "7ec88653a5fa880d4dd9f0168bacf9b2c2aeb073"
EXPECTED_OUTPUT = "results/paper2_m2/identity_gate_v06_v02_20260904"
EXPECTED_CONTRACT = (
    "project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md"
)
EXPECTED_AUTHORIZATION = (
    "project_control/"
    "paper2_m2a_v06_t64_test_eof_hash_diagnosis_and_v06_1_retry_decision_v01.md"
)


def _load_v06_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_paper2_m2_identity_gate_v06.py"
    specification = importlib.util.spec_from_file_location(
        "paper2_m2_identity_gate_v06_frozen_runner", path
    )
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot import frozen v06 runner from {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


V06_RUNNER = _load_v06_runner()
SOURCE_SPECS = V06_RUNNER.SOURCE_SPECS


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


def _git_revision(reference: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", reference],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _git_path_is_clean(relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", relative_path],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and not completed.stdout.strip()


def _host_tests_pass(summary: str) -> bool:
    lowered = summary.lower()
    return "passed" in lowered and "failed" not in lowered and "error" not in lowered


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
    payload = {"schema": "paper2_m2a_v06_1_hash_ledger", "files": files}
    _write_json(output_dir / "hash_ledger.json", payload)
    return payload


def _manifest_recorded_hash(manifest: dict[str, Any], relative_path: str) -> str | None:
    values = manifest.get(
        FROZEN_TEST_EOF_COMPATIBILITY_V06_1.manifest_hash_container, {}
    )
    return values.get(relative_path) if isinstance(values, dict) else None


def _effective_source_locks(
    *,
    source_dirs: dict[str, Path],
    host_pytest_summary: str,
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, str]],
    dict[str, Any],
]:
    raw_locks: dict[str, Any] = {}
    summaries_by_level: dict[str, dict[str, Any]] = {}
    structural_by_level: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, dict[str, str]] = {}
    for label, specification in SOURCE_SPECS.items():
        lock, summaries, structural, snapshot = V06_RUNNER._validate_source_package(
            label=label,
            source_dir=source_dirs[label],
            spec=specification,
        )
        raw_locks[label] = lock
        summaries_by_level[label] = summaries
        structural_by_level[label] = structural
        snapshots[label] = snapshot

    eof_protocol = FROZEN_TEST_EOF_COMPATIBILITY_V06_1.checked()
    allowed_failure = f"implementation_hash:{eof_protocol.relative_path}"
    t64_lock = raw_locks["T64"]
    t64_other_source_locks_pass = bool(
        t64_lock.get("failures") == [allowed_failure]
        and t64_lock.get("implementation_hash_failures")
        == [eof_protocol.relative_path]
    )
    t64_manifest = V06_RUNNER._load_json(source_dirs["T64"] / "run_manifest.json")
    t128_manifest_path = source_dirs["T128"] / "run_manifest.json"
    t256_manifest_path = source_dirs["T256"] / "run_manifest.json"
    t128_manifest = V06_RUNNER._load_json(t128_manifest_path)
    t256_manifest = V06_RUNNER._load_json(t256_manifest_path)
    current_test_path = PROJECT_ROOT / eof_protocol.relative_path
    compatibility = evaluate_exact_test_eof_compatibility(
        source_label="T64",
        relative_path=eof_protocol.relative_path,
        manifest_expected_sha256=t64_manifest.get("implementation_sha256", {}).get(
            eof_protocol.relative_path, ""
        ),
        current_content=current_test_path.read_bytes(),
        git_clean=_git_path_is_clean(eof_protocol.relative_path),
        t128_manifest_sha256=sha256_file(t128_manifest_path),
        t128_recorded_current_sha256=_manifest_recorded_hash(
            t128_manifest, eof_protocol.relative_path
        ),
        t256_manifest_sha256=sha256_file(t256_manifest_path),
        t256_recorded_current_sha256=_manifest_recorded_hash(
            t256_manifest, eof_protocol.relative_path
        ),
        t64_other_source_locks_pass=t64_other_source_locks_pass,
        t128_source_lock_pass=bool(raw_locks["T128"].get("pass")),
        t256_source_lock_pass=bool(raw_locks["T256"].get("pass")),
        host_tests_pass=_host_tests_pass(host_pytest_summary),
        protocol=eof_protocol,
    )

    effective_locks = copy.deepcopy(raw_locks)
    effective_locks["T64"]["v06_raw_pass"] = t64_lock.get("pass")
    effective_locks["T64"]["v06_raw_failures"] = list(
        t64_lock.get("failures", [])
    )
    effective_locks["T64"]["v06_1_compatibility"] = compatibility
    effective_locks["T64"]["failures"] = (
        [] if compatibility["pass"] else list(compatibility["failures"])
    )
    effective_locks["T64"]["pass"] = bool(compatibility["pass"])
    effective_locks["T64"]["accepted_label"] = compatibility["accepted_label"]
    return (
        effective_locks,
        summaries_by_level,
        structural_by_level,
        snapshots,
        compatibility,
    )


def _classification_audit(
    identity: dict[str, Any], *, preconditions_complete: bool
) -> dict[str, Any]:
    records = [
        record
        for case_id in FROZEN_PROTOCOL_V06.holdout_cases
        for record in identity["cases"][case_id]["records"]
    ]
    recomputed = classify_identity_records(
        records, preconditions_complete=preconditions_complete
    )
    severity_counts = {
        severity: sum(record.get("severity") == severity for record in records)
        for severity in ("pass", "maybe", "no_go")
    }
    return {
        "schema": "paper2_m2a_v06_1_classification_audit",
        "frozen_v06_candidate_decision": identity["decision"],
        "independently_recomputed_decision": recomputed,
        "decisions_match": recomputed == identity["decision"],
        "formal_record_count": len(records),
        "severity_counts": severity_counts,
        "thresholds_changed": False,
        "exploratory_metric_added": False,
        "numerical_envelope_subtracted": False,
        "pass": recomputed == identity["decision"],
    }


def main() -> None:
    arguments = _parse_arguments()
    protocol = FROZEN_PROTOCOL_V06.checked()
    eof_protocol = FROZEN_TEST_EOF_COMPATIBILITY_V06_1.checked()
    started = time.perf_counter()

    source_dirs = {
        "T64": _resolved(arguments.source_t64_dir),
        "T128": _resolved(arguments.source_t128_dir),
        "T256": _resolved(arguments.source_t256_dir),
    }
    output_dir = _resolved(arguments.output_dir)
    contract = _resolved(arguments.contract)
    authorization = _resolved(arguments.authorization)
    path_failures: list[str] = []
    for label, specification in SOURCE_SPECS.items():
        expected = _resolved(PROJECT_ROOT / specification["relative_path"])
        if source_dirs[label] != expected:
            path_failures.append(f"{label}_source_path_mismatch")
    if output_dir != _resolved(PROJECT_ROOT / EXPECTED_OUTPUT):
        path_failures.append("output_path_mismatch")
    if contract != _resolved(PROJECT_ROOT / EXPECTED_CONTRACT):
        path_failures.append("contract_path_mismatch")
    if authorization != _resolved(PROJECT_ROOT / EXPECTED_AUTHORIZATION):
        path_failures.append("authorization_path_mismatch")
    baseline_head = _git_revision("HEAD")
    upstream_head = _git_revision("@{upstream}")
    if baseline_head != EXPECTED_BASELINE_GIT_HEAD:
        path_failures.append("baseline_git_head_mismatch")
    if upstream_head != EXPECTED_BASELINE_GIT_HEAD:
        path_failures.append("upstream_git_head_mismatch")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")

    source_locks: dict[str, Any] = {}
    source_snapshots_before: dict[str, dict[str, str]] = {}
    try:
        (
            source_locks,
            summaries_by_level,
            structural_by_level,
            source_snapshots_before,
            compatibility,
        ) = _effective_source_locks(
            source_dirs=source_dirs,
            host_pytest_summary=arguments.host_pytest_summary,
        )
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
            and compatibility["pass"]
            and gain_operator_lock["pass"]
            and _host_tests_pass(arguments.host_pytest_summary)
        )
        preflight = {
            "schema": "paper2_m2a_v06_1_preflight",
            "path_failures": path_failures,
            "baseline_git_head": baseline_head,
            "upstream_git_head": upstream_head,
            "source_locks": source_locks,
            "exact_test_eof_compatibility": compatibility,
            "frozen_combined_load_gain_operator_lock": gain_operator_lock,
            "host_pytest_summary": arguments.host_pytest_summary,
            "host_tests_pass": _host_tests_pass(arguments.host_pytest_summary),
            "solver_or_endpoint_run": False,
            "pass": preflight_pass,
        }
        if not preflight_pass:
            raise RuntimeError("v06.1 source/path/test preflight failed")

        observations_t128 = V06_RUNNER._load_observation_matrix(
            source_dirs["T128"], steps=128, include_fields=False
        )
        observations_t256 = V06_RUNNER._load_observation_matrix(
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
        calibration = calibration_audit_only(summaries_by_level["T256"], protocol)
        fields = field_diagnostics_audit_only(observations_t256, protocol)
        structure_control = structural_control_audit(
            summaries_by_level["T256"], structural_by_level["T256"], protocol
        )
        preflight["structural_control"] = structure_control
        if not structure_control["pass"]:
            raise RuntimeError("v06.1 structural control failed")

        source_snapshots_after = {
            label: V06_RUNNER._current_package_snapshot(source_dirs[label])
            for label in SOURCE_SPECS
        }
        sources_unchanged = source_snapshots_after == source_snapshots_before
        elapsed_seconds = time.perf_counter() - started
        peak_memory_gib = V06_RUNNER._peak_memory_gib()
        summary = V06_RUNNER._summary_from_identity(
            identity,
            preflight_pass=preflight_pass,
            sources_unchanged=sources_unchanged,
            elapsed_seconds=elapsed_seconds,
            peak_memory_gib=peak_memory_gib,
        )
        summary["schema"] = "paper2_m2a_v06_1_identity_gate_pass_summary"
        summary["accepted_source_lock_compatibility"] = eof_protocol.accepted_label
        classification = _classification_audit(
            identity,
            preconditions_complete=bool(
                preflight_pass and sources_unchanged and structure_control["pass"]
            ),
        )
        if not classification["pass"] or summary["decision"] != identity["decision"]:
            raise RuntimeError("v06.1 classification audit failed")
        identity_summary = {
            "schema": "paper2_m2a_v06_1_identity_gate_summary",
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
        protocol_digest = hashlib.sha256(
            json.dumps(protocol_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        implementation_paths = (
            "src/paper2_m2/protocol_v06.py",
            "src/paper2_m2/identity_gate_v06.py",
            "scripts/run_paper2_m2_identity_gate_v06.py",
            "tests/paper2_m2/test_protocol_v06.py",
            "tests/paper2_m2/test_identity_gate_v06.py",
            "src/paper2_m2/protocol_v06_1.py",
            "scripts/run_paper2_m2_identity_gate_v06_1.py",
            "tests/paper2_m2/test_v06_1_source_lock.py",
        )
        run_manifest = {
            "schema": "paper2_m2a_v06_1_identity_gate_manifest",
            "frozen_v06_protocol": protocol_payload,
            "frozen_v06_protocol_digest": protocol_digest,
            "v06_1_exact_eof_compatibility_protocol": eof_protocol.as_dict(),
            "provenance": {
                "contract": str(contract),
                "contract_sha256": sha256_file(contract),
                "authorization": str(authorization),
                "authorization_sha256": sha256_file(authorization),
                "baseline_git_head": baseline_head,
                "upstream_git_head": upstream_head,
                "source_packages": {
                    label: str(path) for label, path in source_dirs.items()
                },
                "source_sha256_before": source_snapshots_before,
                "source_sha256_after": source_snapshots_after,
                "source_packages_unchanged": sources_unchanged,
                "frozen_combined_load_gain_operator": gain_operator_lock,
                "accepted_source_lock_compatibility": compatibility,
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

        artifacts = {
            "preflight.json": preflight,
            "identity_gate_by_case.json": identity,
            "identity_gate_summary.json": identity_summary,
            "numerical_change_envelope.json": envelope,
            "calibration_audit_only.json": calibration,
            "field_diagnostics_audit_only.json": fields,
            "classification_audit.json": classification,
            "run_manifest.json": run_manifest,
            "pass_summary.json": summary,
        }
        if not all(finite_tree(payload) for payload in artifacts.values()):
            raise ValueError("non-finite value detected before v06.1 output creation")
        output_dir.mkdir(parents=True, exist_ok=False)
        for name, payload in artifacts.items():
            _write_json(output_dir / name, payload)
        finite_audit = {
            "schema": "paper2_m2a_v06_1_finite_value_audit",
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
        elapsed_seconds = time.perf_counter() - started
        failure = {
            "schema": "paper2_m2a_v06_1_identity_gate_failure_summary",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "decision": "BLOCKED",
            "reason": f"{type(error).__name__}: {error}",
            "elapsed_seconds": elapsed_seconds,
            "peak_memory_gib": V06_RUNNER._peak_memory_gib(),
            "solver_or_endpoint_run": False,
            "gpu_used": False,
        }
        minimal_preflight = locals().get(
            "preflight",
            {
                "schema": "paper2_m2a_v06_1_preflight",
                "path_failures": path_failures,
                "source_locks": source_locks,
                "pass": False,
            },
        )
        minimal_manifest = {
            "schema": "paper2_m2a_v06_1_identity_gate_manifest_blocked",
            "frozen_v06_protocol": protocol.as_dict(),
            "v06_1_exact_eof_compatibility_protocol": eof_protocol.as_dict(),
            "baseline_git_head": baseline_head,
            "upstream_git_head": upstream_head,
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
