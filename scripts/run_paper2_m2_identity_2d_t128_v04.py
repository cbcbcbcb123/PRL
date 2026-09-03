"""Run the authorized M2A v04 54-endpoint T128 numerical stage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
from typing import Any

import dolfinx
import numpy as np
import scipy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paper2_m2.config import FROZEN_CONFIG  # noqa: E402
from paper2_m2.identity_2d import build_system_for_level  # noqa: E402
from paper2_m2.identity_2d_v03 import global_structural_checks  # noqa: E402
from paper2_m2.identity_2d_v04 import (  # noqa: E402
    DYNAMIC_HOLDOUT_CASES,
    common_projection_sidecar,
    endpoint_key,
    endpoint_structural_gate,
    simulate_endpoint_v04,
    t128_numerical_gate,
    t64_t128_pair_audit,
)
from paper2_m2.interface_projection import (  # noqa: E402
    constant_traction_projection_manufactured_check,
)
from paper2_m2.protocol_v03 import validate_source_calibration  # noqa: E402
from paper2_m2.protocol_v04 import (  # noqa: E402
    FROZEN_PROTOCOL_V04,
    validate_source_t64_result,
)


READ_ONLY_PATHS = (
    PROJECT_ROOT / "src" / "paper2_m2" / "config.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v02.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v02.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v03.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v03.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_v01.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v02.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2a_v03_ledger_repair_pilot_v01.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v03.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v03.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v03.py",
    PROJECT_ROOT
    / "project_control"
    / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md",
    PROJECT_ROOT
    / "project_control"
    / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md",
    PROJECT_ROOT
    / "project_control"
    / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _hash_paths(paths: tuple[Path, ...]) -> dict[str, str]:
    return {_project_path(path): _sha256(path) for path in paths}


def _assert_finite_json(payload: Any, path: str = "root") -> None:
    if payload is None or isinstance(payload, (str, bool)):
        return
    if isinstance(payload, (int, np.integer)):
        return
    if isinstance(payload, (float, np.floating)):
        if not math.isfinite(float(payload)):
            raise ValueError(f"non-finite JSON value at {path}")
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            _assert_finite_json(value, f"{path}.{key}")
        return
    if isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            _assert_finite_json(value, f"{path}[{index}]")
        return
    raise TypeError(f"unsupported JSON value at {path}: {type(payload)!r}")


def _write_json(path: Path, payload: Any) -> None:
    _assert_finite_json(payload)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _peak_memory_gib() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0))


def _write_hash_ledger(output_dir: Path) -> None:
    ledger_path = output_dir / "hash_ledger.json"
    entries = {
        str(path.relative_to(output_dir)).replace("\\", "/"): {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path != ledger_path
    }
    _write_json(
        ledger_path,
        {"schema": "paper2_m2a_v04_t128_hash_ledger_v01", "files": entries},
    )


def _write_partial_failure(
    *,
    output_dir: Path,
    summaries: dict[str, Any],
    structural_records: dict[str, Any],
    failure: dict[str, Any],
) -> None:
    if summaries:
        _write_json(output_dir / "endpoint_summaries_partial.json", summaries)
    if structural_records:
        _write_json(output_dir / "structural_gates_partial.json", structural_records)
    _write_json(output_dir / "failure.json", failure)
    _write_hash_ledger(output_dir)
    print(json.dumps(failure, indent=2, sort_keys=True, allow_nan=False), flush=True)


def _selected_npz_finite_audit(selected_dir: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    all_finite = True
    for path in sorted(selected_dir.glob("*.npz")):
        arrays: dict[str, Any] = {}
        with np.load(path) as archive:
            for name in archive.files:
                values = archive[name]
                finite = bool(np.all(np.isfinite(values)))
                arrays[name] = {
                    "shape": list(values.shape),
                    "dtype": str(values.dtype),
                    "finite": finite,
                }
                all_finite = all_finite and finite
        records[path.name] = {
            "arrays": arrays,
            "pass": all(item["finite"] for item in arrays.values()),
        }
    expected = len(DYNAMIC_HOLDOUT_CASES) * len(FROZEN_PROTOCOL_V04.representations)
    return {
        "schema": "paper2_m2a_v04_t128_finite_value_audit_v01",
        "selected_dynamic_holdout_npz_expected": expected,
        "selected_dynamic_holdout_npz_found": len(records),
        "records": records,
        "json_finite_enforced_at_write": True,
        "pass": bool(all_finite and len(records) == expected),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract-v04", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--source-t64-dir", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--v03-execution-record", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    protocol = FROZEN_PROTOCOL_V04.checked()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    selected_dir = arguments.output_dir / "selected_dynamic_holdouts"
    selected_dir.mkdir(exist_ok=False)
    started = time.perf_counter()

    try:
        source_t64_lock = validate_source_t64_result(arguments.source_t64_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        failure = {
            "schema": "paper2_m2a_v04_t128_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "source_T64_lock",
            "reason": str(error),
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)
    _write_json(arguments.output_dir / "source_T64_lock.json", source_t64_lock)

    with (arguments.source_t64_dir / "endpoint_summaries.json").open(
        "r", encoding="utf-8"
    ) as stream:
        source_t64_summaries = json.load(stream)
    with arguments.source_calibration.open("r", encoding="utf-8") as stream:
        source_calibration = json.load(stream)
    calibration_lock = validate_source_calibration(source_calibration)
    _write_json(arguments.output_dir / "source_calibration_lock.json", calibration_lock)

    tests = {
        "schema": "paper2_m2a_v04_t128_preflight_tests_v01",
        "host": arguments.host_pytest_summary,
        "frozen_dolfinx_cpu_container": arguments.container_pytest_summary,
        "pass": (
            "passed" in arguments.host_pytest_summary
            and "passed" in arguments.container_pytest_summary
        ),
    }
    _write_json(arguments.output_dir / "preflight_tests.json", tests)
    if not tests["pass"]:
        failure = {
            "schema": "paper2_m2a_v04_t128_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "preflight_tests",
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)

    source_critical_paths = (
        arguments.source_t64_dir / "pass_summary.json",
        arguments.source_t64_dir / "endpoint_summaries.json",
        arguments.source_t64_dir / "hash_ledger.json",
        arguments.source_calibration,
    )
    frozen_paths = READ_ONLY_PATHS + source_critical_paths
    read_only_before = _hash_paths(frozen_paths)
    implementation_paths = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v04.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v04.py",
        Path(__file__).resolve(),
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v04.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v04.py",
    )
    manifest = {
        "schema": "paper2_m2a_identity_2d_v04_t128_manifest_v01",
        "protocol": protocol.canonical_payload(),
        "protocol_digest": protocol.digest(),
        "source_T64_lock": source_t64_lock,
        "source_calibration_sha256": _sha256(arguments.source_calibration),
        "read_only_sha256_before": read_only_before,
        "implementation_sha256": _hash_paths(implementation_paths),
        "provenance": {
            "contract_v04_sha256": _sha256(arguments.contract_v04),
            "authorization_sha256": _sha256(arguments.authorization),
            "v03_execution_record_sha256": _sha256(arguments.v03_execution_record),
        },
        "runtime": {
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "cpu_processes": protocol.cpu_processes,
            "blas_omp_threads": 1,
            "network": "disabled_by_container",
            "gpu_used": False,
        },
        "evidence_labels": {
            "T64_T128": "T64_T128_PAIR_AUDIT_ONLY",
            "time_direction": "PENDING_T256",
            "ID-A2_ID-S1": "parameter_holdout_used_for_numerical_ladder_development",
            "ID-LN_ID-LS_ID-C0_ID-CQ": "primary_numerical_protocol_holdouts",
        },
    }
    _write_json(arguments.output_dir / "run_manifest.json", manifest)

    projection_checks = {
        "schema": "paper2_m2a_v04_t128_projection_preflight_v01",
        "role": "diagnostic_sidecar_only_not_production_gate",
        "S3_to_common_64": constant_traction_projection_manufactured_check(
            native_segments=64, common_segments=64
        ),
        "S4_to_common_64": constant_traction_projection_manufactured_check(
            native_segments=128, common_segments=64
        ),
    }
    projection_checks["pass"] = bool(
        projection_checks["S3_to_common_64"]["pass"]
        and projection_checks["S4_to_common_64"]["pass"]
    )
    _write_json(arguments.output_dir / "projection_preflight.json", projection_checks)
    if not projection_checks["pass"]:
        failure = {
            "schema": "paper2_m2a_v04_t128_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "projection_preflight",
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)

    passive_scale = float(source_calibration["passive"]["dcm_passive_scale"])
    active_scale = float(source_calibration["active"]["dcm_active_scale"])
    probe_started = time.perf_counter()
    probe_system = build_system_for_level(
        representation="FEM",
        level=protocol.spatial("S4"),
        passive_dcm_scale=passive_scale,
        active_dcm_scale=active_scale,
        active_profile="uniform",
    )
    global_checks = global_structural_checks(probe_system)
    assembly_probe = {
        "schema": "paper2_m2a_v04_t128_S4_assembly_probe_v01",
        "representation": "FEM",
        "profile": "uniform",
        "state_size": probe_system.state_size,
        "matrix_a_shape": list(probe_system.matrix_a.shape),
        "matrix_a_nnz": int(probe_system.matrix_a.nnz),
        "ufl_manual_relative_error": float(probe_system.manufactured_error),
        "threshold": FROZEN_CONFIG.manufactured_solution_relative_tolerance,
        "global_structural_checks": global_checks,
        "elapsed_seconds": time.perf_counter() - probe_started,
        "pass": all(record["pass"] for record in global_checks.values()),
    }
    _write_json(arguments.output_dir / "assembly_probe.json", assembly_probe)
    _write_json(arguments.output_dir / "global_structural_checks.json", global_checks)
    if not assembly_probe["pass"]:
        failure = {
            "schema": "paper2_m2a_v04_t128_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "S4_assembly_probe",
            "completed_endpoints": 0,
            "probe": assembly_probe,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)

    systems: dict[tuple[str, str, str], Any] = {("FEM", "S4", "uniform"): probe_system}
    for representation in protocol.representations:
        for level in protocol.spatial_levels:
            for profile in ("uniform", "S1"):
                key = (representation, str(level.label), profile)
                if key not in systems:
                    systems[key] = build_system_for_level(
                        representation=representation,
                        level=level,
                        passive_dcm_scale=passive_scale,
                        active_dcm_scale=active_scale,
                        active_profile=profile,
                    )

    summaries: dict[str, dict[str, Any]] = {}
    structural_records: dict[str, Any] = {}
    endpoint_counter = 0
    for case_id in FROZEN_CONFIG.cases:
        profile = "S1" if case_id == "ID-S1" else "uniform"
        for representation in protocol.representations:
            for level in protocol.spatial_levels:
                system = systems[(representation, str(level.label), profile)]
                endpoint_started = time.perf_counter()
                endpoint = simulate_endpoint_v04(system=system, case_id=case_id)
                endpoint_runtime = time.perf_counter() - endpoint_started
                endpoint.summary["runtime_seconds"] = endpoint_runtime
                endpoint.summary["v04_common_projection_sidecar"] = (
                    common_projection_sidecar(system, endpoint)
                )
                key = endpoint_key(case_id, representation, str(level.label))
                summaries[key] = endpoint.summary
                structural = endpoint_structural_gate(endpoint.summary)
                structural_records[key] = structural
                endpoint_counter += 1

                if case_id in DYNAMIC_HOLDOUT_CASES and level.label == "S4":
                    np.savez_compressed(selected_dir / f"{key}.npz", **endpoint.arrays)

                elapsed = time.perf_counter() - started
                peak_memory = _peak_memory_gib()
                endpoint_budget_pass = (
                    endpoint_runtime <= FROZEN_CONFIG.endpoint_runtime_budget_seconds
                )
                resource_pass = bool(
                    elapsed <= protocol.runtime_budget_seconds
                    and peak_memory <= protocol.memory_budget_gib
                )
                progress = {
                    "event": "endpoint_complete",
                    "completed": endpoint_counter,
                    "expected": protocol.expected_endpoint_count,
                    "percent": round(
                        100.0 * endpoint_counter / protocol.expected_endpoint_count, 2
                    ),
                    "endpoint": key,
                    "runtime_seconds": endpoint_runtime,
                    "structural_pass": structural["pass"],
                }
                print(json.dumps(progress, sort_keys=True), flush=True)
                if not structural["pass"] or not endpoint_budget_pass or not resource_pass:
                    failure = {
                        "schema": "paper2_m2a_v04_t128_failure_v01",
                        "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
                        "stage": "T128_endpoint",
                        "endpoint": key,
                        "completed_endpoints": endpoint_counter,
                        "structural_gate": structural,
                        "endpoint_runtime_seconds": endpoint_runtime,
                        "endpoint_runtime_budget_seconds": (
                            FROZEN_CONFIG.endpoint_runtime_budget_seconds
                        ),
                        "elapsed_seconds": elapsed,
                        "runtime_budget_seconds": protocol.runtime_budget_seconds,
                        "peak_memory_gib": peak_memory,
                        "memory_budget_gib": protocol.memory_budget_gib,
                    }
                    _write_partial_failure(
                        output_dir=arguments.output_dir,
                        summaries=summaries,
                        structural_records=structural_records,
                        failure=failure,
                    )
                    raise SystemExit(2)

    _write_json(arguments.output_dir / "endpoint_summaries.json", summaries)
    _write_json(arguments.output_dir / "structural_gates.json", structural_records)
    stage_gate = t128_numerical_gate(summaries)
    _write_json(arguments.output_dir / "stage_T128_gate.json", stage_gate)
    pair_audit = t64_t128_pair_audit(source_t64_summaries, summaries)
    _write_json(arguments.output_dir / "T64_T128_pair_audit.json", pair_audit)
    finite_audit = _selected_npz_finite_audit(selected_dir)
    _write_json(arguments.output_dir / "finite_value_audit.json", finite_audit)

    read_only_after = _hash_paths(frozen_paths)
    elapsed_seconds = time.perf_counter() - started
    peak_memory_gib = _peak_memory_gib()
    within_resource_budget = bool(
        elapsed_seconds <= protocol.runtime_budget_seconds
        and peak_memory_gib <= protocol.memory_budget_gib
    )
    all_structural_pass = bool(
        assembly_probe["pass"]
        and all(record["pass"] for record in structural_records.values())
    )
    all_pass = bool(
        endpoint_counter == protocol.expected_endpoint_count
        and all_structural_pass
        and stage_gate["pass"]
        and pair_audit["pass"]
        and finite_audit["pass"]
        and source_t64_lock["pass"]
        and read_only_before == read_only_after
        and within_resource_budget
    )
    maximum_pair = max(
        pair_audit["records"], key=lambda record: record["relative_difference"]
    )
    summary = {
        "schema": "paper2_m2a_v04_t128_pass_summary_v01",
        "status": (
            "COMPLETE_AT_SUPERVISOR_GATE"
            if all_pass
            else "FAIL_CLOSED_AT_SUPERVISOR_GATE"
        ),
        "decision": "T128_STAGE_PASS_V04" if all_pass else "T128_STAGE_FAIL_V04",
        "completed_endpoints": endpoint_counter,
        "expected_endpoints": protocol.expected_endpoint_count,
        "steps_per_cycle": 128,
        "solver_level": "D0",
        "C0_C1_axis_present": False,
        "all_structural_gates_pass": all_structural_pass,
        "all_T128_numerical_gates_pass": stage_gate["pass"],
        "stage_gate_counts": stage_gate["counts"],
        "numerical_failures": stage_gate["failures"],
        "projection_sidecar": stage_gate["projection_sidecar"],
        "time_pair_audit": {
            "label": pair_audit["label"],
            "record_count": pair_audit["record_count"],
            "pass": pair_audit["pass"],
            "maximum_relative_difference": pair_audit[
                "maximum_relative_difference"
            ],
            "maximum_relative_difference_record": maximum_pair,
            "direction_assessment": "PENDING_T256",
            "time_convergence_claimed": False,
        },
        "finite_value_audit_pass": finite_audit["pass"],
        "selected_dynamic_holdout_npz": finite_audit[
            "selected_dynamic_holdout_npz_found"
        ],
        "source_T64_lock_pass": source_t64_lock["pass"],
        "calibration_reused_without_refit": True,
        "maximum_direct_relative_residual": max(
            value["solver"]["maximum_relative_residual"]
            for value in summaries.values()
        ),
        "maximum_normwise_backward_error": max(
            value["solver"]["maximum_normwise_backward_error"]
            for value in summaries.values()
        ),
        "maximum_normalized_power_ledger_residual": max(
            value["ledger"]["maximum_normalized_residual"]
            for value in summaries.values()
        ),
        "maximum_discrete_closure_relative": max(
            value["ledger"]["maximum_ledger_minus_equilibrium_work_relative"]
            for value in summaries.values()
        ),
        "maximum_endpoint_subtraction_gap": max(
            value["ledger"]["maximum_absolute_endpoint_subtraction_gap"]
            for value in summaries.values()
        ),
        "read_only_sha256_before": read_only_before,
        "read_only_sha256_after": read_only_after,
        "read_only_unchanged": read_only_before == read_only_after,
        "resource": {
            "elapsed_seconds": elapsed_seconds,
            "budget_seconds": protocol.runtime_budget_seconds,
            "peak_memory_gib": peak_memory_gib,
            "memory_budget_gib": protocol.memory_budget_gib,
            "within_budget": within_resource_budget,
            "cpu_processes": protocol.cpu_processes,
            "gpu_used": False,
        },
        "stop_boundary": {
            "T256_run": False,
            "three_level_time_convergence_assessed": False,
            "identity_gate_computed": False,
            "GO_MAYBE_NO_GO_issued": False,
            "M2B_run": False,
            "three_dimensional_run": False,
            "whole_atrium_run": False,
            "CFD_or_FSI_run": False,
        },
        "evidence_boundary": (
            "T128_STAGE_PASS_V04 establishes only the frozen idealized two-dimensional "
            "T128 numerical stage and a complete T64-to-T128 pair audit. Two time "
            "levels do not establish time convergence or DCM-FEM identity."
        ),
    }
    _write_json(
        arguments.output_dir / ("pass_summary.json" if all_pass else "failure.json"),
        summary,
    )
    _write_hash_ledger(arguments.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), flush=True)
    if not all_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
