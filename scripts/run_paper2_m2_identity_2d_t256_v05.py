"""Run the authorized M2A v05 T256 and three-level time gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH_FLAGS = frozenset(
    {
        "--output-dir",
        "--contract-v05",
        "--authorization",
        "--source-t64-dir",
        "--source-t128-dir",
        "--source-calibration",
        "--v04-execution-record",
    }
)


def normalize_project_path(value: str | Path) -> Path:
    input_path = Path(value)
    candidate = (
        input_path if input_path.is_absolute() else PROJECT_ROOT / input_path
    ).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"path is outside project root: {value}") from error
    return candidate


def normalize_cli_project_paths(argv: list[str]) -> tuple[list[str], dict[str, Any]]:
    normalized = list(argv)
    records: dict[str, Any] = {}
    seen: set[str] = set()
    for index, token in enumerate(argv):
        if token not in PROJECT_PATH_FLAGS:
            continue
        if token in seen:
            raise ValueError(f"duplicate project path flag: {token}")
        if index + 1 >= len(argv):
            raise ValueError(f"missing value for project path flag: {token}")
        seen.add(token)
        raw_value = argv[index + 1]
        canonical = normalize_project_path(raw_value)
        normalized[index + 1] = str(canonical)
        records[token] = {
            "input": raw_value,
            "canonical": str(canonical),
            "inside_project_root": True,
        }
    missing = sorted(PROJECT_PATH_FLAGS - seen)
    if missing:
        raise ValueError(f"missing project path flags: {missing}")
    return normalized, {
        "schema": "paper2_m2a_v05_path_normalization_audit_v01",
        "project_root": str(PROJECT_ROOT.resolve()),
        "paths": records,
        "all_project_path_flags_seen": True,
        "all_canonical_paths_inside_project": True,
        "normalization_completed_before_runtime_imports": True,
        "normalization_completed_before_output_creation": True,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def _hash_paths(paths: tuple[Path, ...]) -> dict[str, str]:
    return {_project_path(path): _sha256(path) for path in paths}


def _assert_finite_json(payload: Any, path: str = "root") -> None:
    if payload is None or isinstance(payload, (str, bool)):
        return
    if isinstance(payload, Integral):
        return
    if isinstance(payload, Real):
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
        {"schema": "paper2_m2a_v05_t256_hash_ledger_v01", "files": entries},
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


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract-v05", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--source-t64-dir", type=Path, required=True)
    parser.add_argument("--source-t128-dir", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--v04-execution-record", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args(argv[1:])


def _source_ledger_paths(source_dir: Path) -> tuple[Path, ...]:
    with (source_dir / "hash_ledger.json").open("r", encoding="utf-8") as stream:
        ledger = json.load(stream)
    paths = tuple(source_dir / name for name in sorted(ledger["files"]))
    return paths + (source_dir / "hash_ledger.json",)


def _run(normalized_argv: list[str], path_audit: dict[str, Any]) -> None:
    import resource

    import dolfinx
    import numpy as np
    import scipy

    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    from paper2_m2.config import FROZEN_CONFIG
    from paper2_m2.identity_2d import build_system_for_level
    from paper2_m2.identity_2d_v03 import global_structural_checks
    from paper2_m2.identity_2d_v05 import (
        DYNAMIC_HOLDOUT_CASES,
        common_projection_sidecar,
        endpoint_key,
        endpoint_structural_gate,
        simulate_endpoint_v05,
        t256_numerical_gate,
        three_level_time_gate,
        time_nodes_nested,
    )
    from paper2_m2.interface_projection import (
        constant_traction_projection_manufactured_check,
    )
    from paper2_m2.protocol_v03 import validate_source_calibration
    from paper2_m2.protocol_v04 import validate_source_t64_result
    from paper2_m2.protocol_v05 import (
        FROZEN_PROTOCOL_V05,
        validate_source_t128_result,
    )

    def peak_memory_gib() -> float:
        return float(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)
        )

    def selected_npz_audits(
        selected_dir: Path, source_t128_dir: Path
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        finite_records: dict[str, Any] = {}
        nesting_records: dict[str, Any] = {}
        target_paths = sorted(selected_dir.glob("*.npz"))
        for target_path in target_paths:
            arrays: dict[str, Any] = {}
            with np.load(target_path, allow_pickle=False) as target_archive:
                for name in target_archive.files:
                    values = np.asarray(target_archive[name])
                    finite = bool(
                        not np.issubdtype(values.dtype, np.number)
                        or np.all(np.isfinite(values))
                    )
                    arrays[name] = {
                        "shape": list(values.shape),
                        "dtype": str(values.dtype),
                        "finite": finite,
                    }
                target_time = np.asarray(target_archive["time_two_cycles"])

            source_name = target_path.name.replace("__T256__", "__T128__")
            source_path = source_t128_dir / "selected_dynamic_holdouts" / source_name
            source_exists = source_path.is_file()
            source_hash = _sha256(source_path) if source_exists else None
            if source_exists:
                with np.load(source_path, allow_pickle=False) as source_archive:
                    source_time = np.asarray(source_archive["time_two_cycles"])
                nesting = time_nodes_nested(source_time, target_time)
            else:
                nesting = {
                    "source_T128_nodes": 0,
                    "target_T256_nodes": int(target_time.size),
                    "expected_target_nodes": 0,
                    "finite": False,
                    "shape_pass": False,
                    "maximum_absolute_error": None,
                    "absolute_tolerance": 1.0e-15,
                    "pass": False,
                }
            finite_records[target_path.name] = {
                "arrays": arrays,
                "pass": all(item["finite"] for item in arrays.values()),
            }
            nesting_records[target_path.name] = {
                "source_T128_npz": source_name,
                "source_T128_exists": source_exists,
                "source_T128_sha256": source_hash,
                **nesting,
            }

        expected = len(DYNAMIC_HOLDOUT_CASES) * len(FROZEN_PROTOCOL_V05.representations)
        finite_audit = {
            "schema": "paper2_m2a_v05_t256_finite_value_audit_v01",
            "selected_dynamic_holdout_npz_expected": expected,
            "selected_dynamic_holdout_npz_found": len(finite_records),
            "records": finite_records,
            "json_finite_enforced_at_write": True,
            "pass": bool(
                len(finite_records) == expected
                and all(record["pass"] for record in finite_records.values())
            ),
        }
        nesting_audit = {
            "schema": "paper2_m2a_v05_t128_t256_time_node_nesting_audit_v01",
            "selected_dynamic_holdout_pairs_expected": expected,
            "selected_dynamic_holdout_pairs_found": len(nesting_records),
            "records": nesting_records,
            "pass": bool(
                len(nesting_records) == expected
                and all(record["pass"] for record in nesting_records.values())
            ),
        }
        return finite_audit, nesting_audit

    arguments = _parse_arguments(normalized_argv)
    protocol = FROZEN_PROTOCOL_V05.checked()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    selected_dir = arguments.output_dir / "selected_dynamic_holdouts"
    selected_dir.mkdir(exist_ok=False)
    started = time.perf_counter()

    try:
        source_t64_lock = validate_source_t64_result(arguments.source_t64_dir)
        source_t128_lock = validate_source_t128_result(arguments.source_t128_dir)
        with arguments.source_calibration.open("r", encoding="utf-8") as stream:
            source_calibration = json.load(stream)
        calibration_lock = validate_source_calibration(source_calibration)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        failure = {
            "schema": "paper2_m2a_v05_t256_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "source_and_calibration_locks",
            "reason": str(error),
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        print(json.dumps(failure, indent=2, sort_keys=True), flush=True)
        raise SystemExit(2) from error

    _write_json(arguments.output_dir / "source_T64_lock.json", source_t64_lock)
    _write_json(arguments.output_dir / "source_T128_lock.json", source_t128_lock)
    _write_json(arguments.output_dir / "source_calibration_lock.json", calibration_lock)

    with (arguments.source_t64_dir / "endpoint_summaries.json").open(
        "r", encoding="utf-8"
    ) as stream:
        source_t64_summaries = json.load(stream)
    with (arguments.source_t128_dir / "endpoint_summaries.json").open(
        "r", encoding="utf-8"
    ) as stream:
        source_t128_summaries = json.load(stream)

    tests = {
        "schema": "paper2_m2a_v05_t256_preflight_tests_v01",
        "host": arguments.host_pytest_summary,
        "frozen_dolfinx_cpu_container": arguments.container_pytest_summary,
        "pass": bool(
            "passed" in arguments.host_pytest_summary
            and "passed" in arguments.container_pytest_summary
        ),
    }
    _write_json(arguments.output_dir / "preflight_tests.json", tests)
    if not tests["pass"]:
        failure = {
            "schema": "paper2_m2a_v05_t256_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "preflight_tests",
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)

    base_read_only_paths = (
        PROJECT_ROOT / "src" / "paper2_m2" / "config.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v02.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v02.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v03.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v03.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v04.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v04.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_v01.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v02.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2a_v03_ledger_repair_pilot_v01.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v03.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t128_v04.py",
        PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t128_v04_1.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v02.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v02.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v03.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v03.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v04.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v04.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_t128_v04_1_path_normalization.py",
        PROJECT_ROOT
        / "project_control"
        / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md",
        PROJECT_ROOT
        / "project_control"
        / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md",
        PROJECT_ROOT
        / "project_control"
        / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md",
        PROJECT_ROOT
        / "project_control"
        / "paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md",
        PROJECT_ROOT
        / "project_control"
        / "paper2_m2a_v04_t128_path_repair_retry_execution_record_v01.md",
        PROJECT_ROOT
        / "results"
        / "paper2_m2"
        / "identity_2d_v04_t128_v01_20260903"
        / "failure.json",
        PROJECT_ROOT
        / "results"
        / "paper2_m2"
        / "identity_2d_v04_t128_v01_20260903"
        / "hash_ledger.json",
    )
    source_paths = (
        _source_ledger_paths(arguments.source_t64_dir)
        + _source_ledger_paths(arguments.source_t128_dir)
        + (arguments.source_calibration,)
    )
    frozen_paths = base_read_only_paths + source_paths
    read_only_before = _hash_paths(frozen_paths)
    implementation_paths = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v05.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v05.py",
        Path(__file__).resolve(),
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v05.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v05.py",
    )
    manifest = {
        "schema": "paper2_m2a_identity_2d_v05_t256_manifest_v01",
        "path_normalization": path_audit,
        "protocol": protocol.canonical_payload(),
        "protocol_digest": protocol.digest(),
        "source_T64_lock": source_t64_lock,
        "source_T128_lock": source_t128_lock,
        "source_calibration_sha256": _sha256(arguments.source_calibration),
        "read_only_sha256_before": read_only_before,
        "implementation_sha256": _hash_paths(implementation_paths),
        "provenance": {
            "contract_v05_sha256": _sha256(arguments.contract_v05),
            "authorization_sha256": _sha256(arguments.authorization),
            "v04_execution_record_sha256": _sha256(arguments.v04_execution_record),
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
            "T64_T128_T256": "THREE_LEVEL_TIME_GATE_ONLY",
            "time_convergence_order": "NOT_FITTED",
            "identity_gate": "NOT_COMPUTED",
            "ID-A2_ID-S1": "parameter_holdout_used_for_numerical_ladder_development",
            "ID-LN_ID-LS_ID-C0_ID-CQ": "primary_numerical_protocol_holdouts",
        },
    }
    _write_json(arguments.output_dir / "run_manifest.json", manifest)

    projection_checks = {
        "schema": "paper2_m2a_v05_t256_projection_preflight_v01",
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
            "schema": "paper2_m2a_v05_t256_failure_v01",
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
        "schema": "paper2_m2a_v05_t256_S4_assembly_probe_v01",
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
            "schema": "paper2_m2a_v05_t256_failure_v01",
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
                system_key = (representation, str(level.label), profile)
                if system_key not in systems:
                    systems[system_key] = build_system_for_level(
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
                try:
                    endpoint = simulate_endpoint_v05(system=system, case_id=case_id)
                    endpoint_runtime = time.perf_counter() - endpoint_started
                    endpoint.summary["runtime_seconds"] = endpoint_runtime
                    endpoint.summary["v05_common_projection_sidecar"] = (
                        common_projection_sidecar(system, endpoint)
                    )
                    key = endpoint_key(case_id, representation, str(level.label))
                    summaries[key] = endpoint.summary
                    structural = endpoint_structural_gate(endpoint.summary)
                    structural_records[key] = structural
                    endpoint_counter += 1
                    if case_id in DYNAMIC_HOLDOUT_CASES and level.label == "S4":
                        np.savez_compressed(selected_dir / f"{key}.npz", **endpoint.arrays)
                except Exception as error:
                    failure = {
                        "schema": "paper2_m2a_v05_t256_failure_v01",
                        "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
                        "stage": "T256_endpoint_exception",
                        "endpoint": endpoint_key(
                            case_id, representation, str(level.label)
                        ),
                        "completed_endpoints": endpoint_counter,
                        "reason": f"{type(error).__name__}: {error}",
                    }
                    _write_partial_failure(
                        output_dir=arguments.output_dir,
                        summaries=summaries,
                        structural_records=structural_records,
                        failure=failure,
                    )
                    raise SystemExit(2) from error

                elapsed = time.perf_counter() - started
                peak_memory = peak_memory_gib()
                endpoint_budget_pass = bool(
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
                    "elapsed_seconds": elapsed,
                    "peak_memory_gib": peak_memory,
                    "structural_pass": structural["pass"],
                    "scope_held": True,
                }
                print(json.dumps(progress, sort_keys=True), flush=True)
                if not structural["pass"] or not endpoint_budget_pass or not resource_pass:
                    failure = {
                        "schema": "paper2_m2a_v05_t256_failure_v01",
                        "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
                        "stage": "T256_endpoint",
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
    try:
        stage_gate = t256_numerical_gate(summaries)
        time_gate = three_level_time_gate(
            source_t64_summaries, source_t128_summaries, summaries
        )
        finite_audit, nesting_audit = selected_npz_audits(
            selected_dir, arguments.source_t128_dir
        )
    except Exception as error:
        failure = {
            "schema": "paper2_m2a_v05_t256_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "post_endpoint_gate_exception",
            "completed_endpoints": endpoint_counter,
            "reason": f"{type(error).__name__}: {error}",
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        print(json.dumps(failure, indent=2, sort_keys=True), flush=True)
        raise SystemExit(2) from error

    _write_json(arguments.output_dir / "stage_T256_gate.json", stage_gate)
    _write_json(arguments.output_dir / "T64_T128_T256_time_gate.json", time_gate)
    _write_json(arguments.output_dir / "finite_value_audit.json", finite_audit)
    _write_json(
        arguments.output_dir / "T128_T256_time_node_nesting_audit.json",
        nesting_audit,
    )

    read_only_after = _hash_paths(frozen_paths)
    elapsed_seconds = time.perf_counter() - started
    peak_memory = peak_memory_gib()
    within_resource_budget = bool(
        elapsed_seconds <= protocol.runtime_budget_seconds
        and peak_memory <= protocol.memory_budget_gib
    )
    all_structural_pass = bool(
        assembly_probe["pass"]
        and all(record["pass"] for record in structural_records.values())
    )
    all_pass = bool(
        endpoint_counter == protocol.expected_endpoint_count
        and all_structural_pass
        and stage_gate["pass"]
        and time_gate["pass"]
        and finite_audit["pass"]
        and nesting_audit["pass"]
        and source_t64_lock["pass"]
        and source_t128_lock["pass"]
        and calibration_lock["pass"]
        and read_only_before == read_only_after
        and within_resource_budget
    )
    maximum_r12_record = time_gate["maximum_r12_record"]
    maximum_change_ratio_record = time_gate["maximum_change_ratio_record"]
    summary = {
        "schema": "paper2_m2a_v05_t256_pass_summary_v01",
        "status": (
            "COMPLETE_AT_SUPERVISOR_GATE"
            if all_pass
            else "FAIL_CLOSED_AT_SUPERVISOR_GATE"
        ),
        "decision": (
            "T256_TIME_CONVERGENCE_PASS_V05"
            if all_pass
            else "T256_TIME_CONVERGENCE_FAIL_V05"
        ),
        "completed_endpoints": endpoint_counter,
        "expected_endpoints": protocol.expected_endpoint_count,
        "steps_per_cycle": 256,
        "solver_level": "D0",
        "C0_C1_axis_present": False,
        "all_structural_gates_pass": all_structural_pass,
        "all_T256_numerical_gates_pass": stage_gate["pass"],
        "stage_gate_counts": stage_gate["counts"],
        "numerical_failures": stage_gate["failures"],
        "projection_sidecar": stage_gate["projection_sidecar"],
        "three_level_time_gate": {
            "label": time_gate["label"],
            "record_count": time_gate["record_count"],
            "pass": time_gate["pass"],
            "failure_count": len(time_gate["failures"]),
            "failures": time_gate["failures"],
            "maximum_r12_record": maximum_r12_record,
            "maximum_change_ratio_record": maximum_change_ratio_record,
            "convergence_order_fitted": False,
        },
        "finite_value_audit_pass": finite_audit["pass"],
        "time_node_nesting_audit_pass": nesting_audit["pass"],
        "selected_dynamic_holdout_npz": finite_audit[
            "selected_dynamic_holdout_npz_found"
        ],
        "source_T64_lock_pass": source_t64_lock["pass"],
        "source_T128_lock_pass": source_t128_lock["pass"],
        "calibration_reused_without_refit": True,
        "maximum_direct_relative_residual": max(
            value["solver"]["maximum_relative_residual"] for value in summaries.values()
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
            "peak_memory_gib": peak_memory,
            "memory_budget_gib": protocol.memory_budget_gib,
            "within_budget": within_resource_budget,
            "cpu_processes": protocol.cpu_processes,
            "gpu_used": False,
        },
        "stop_boundary": {
            "identity_gate_computed": False,
            "GO_MAYBE_NO_GO_issued": False,
            "M2B_run": False,
            "S5_run": False,
            "three_dimensional_run": False,
            "whole_atrium_run": False,
            "CFD_or_FSI_run": False,
            "GPU_used": False,
        },
        "evidence_boundary": (
            "T256_TIME_CONVERGENCE_PASS_V05 establishes only the frozen idealized "
            "two-dimensional T256 stage and the preregistered T64/T128/T256 scalar "
            "time gate. It does not fit a convergence order or establish DCM-FEM identity."
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


def main() -> None:
    try:
        normalized_argv, path_audit = normalize_cli_project_paths(sys.argv)
    except ValueError as error:
        print(
            json.dumps(
                {
                    "schema": "paper2_m2a_v05_path_gate_failure_v01",
                    "status": "FAIL_CLOSED_BEFORE_OUTPUT_CREATION",
                    "reason": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
        raise SystemExit(2) from error
    _run(normalized_argv, path_audit)


if __name__ == "__main__":
    main()

