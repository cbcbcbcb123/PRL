"""Run the authorized three-endpoint M2A v03 ledger-repair pilot."""

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
from paper2_m2.identity_2d import build_system_for_level, simulate_endpoint  # noqa: E402
from paper2_m2.identity_2d_v03 import (  # noqa: E402
    common_projection_sidecar,
    endpoint_key,
    endpoint_structural_gate,
    upgrade_endpoint_v03,
)
from paper2_m2.protocol_v03 import (  # noqa: E402
    FROZEN_PROTOCOL_V03,
    validate_source_calibration,
)


READ_ONLY_PATHS = (
    PROJECT_ROOT / "src" / "paper2_m2" / "config.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v02.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v02.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_v01.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v02.py",
)
NONLEDGER_ARRAYS = (
    "time_two_cycles",
    "activation_two_cycles",
    "limited_shortening_two_cycles",
    "free_shortening_two_cycles",
    "mean_endocardial_tangential_displacement_two_cycles",
    "mean_endocardial_normal_displacement_two_cycles",
    "state_two_cycles",
    "myocardium_ecm_traction_two_cycles",
    "endocardium_ecm_traction_two_cycles",
    "ecm_cell_centroids",
    "ecm_strain_at_peak",
    "ecm_internal_z_at_peak",
    "ecm_stress_at_peak",
)
NONLEDGER_SUMMARY_FIELDS = (
    "passive_tangent",
    "manufactured_uniform_strain_relative_error",
    "maximum_state_norm",
    "cycle_state_relative_difference",
    "peak_free_shortening",
    "peak_limited_shortening",
    "minimum_limited_shortening",
    "peak_absolute_mean_endocardial_tangential_displacement",
    "peak_absolute_mean_endocardial_normal_displacement",
    "shortening_fundamental_amplitude",
    "shortening_waveform_l2",
    "shortening_phase_relative_to_activation_rad",
    "maximum_myocardium_ecm_traction",
    "maximum_endocardium_ecm_traction",
    "myocardium_ecm_traction_l2",
    "endocardium_ecm_traction_l2",
    "interface_action_reaction_relative_error",
    "hotspot_x",
    "hotspot_traction",
    "maximum_ecm_von_mises_proxy",
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
        {"schema": "paper2_m2a_v03_ledger_repair_pilot_hashes_v01", "files": entries},
    )


def _peak_memory_gib() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0))


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract-v03", type=Path, required=True)
    parser.add_argument("--repair-decision", type=Path, required=True)
    parser.add_argument("--clarification-decision", type=Path, required=True)
    parser.add_argument("--diagnostic-record", type=Path, required=True)
    parser.add_argument("--diagnostic-final", type=Path, required=True)
    parser.add_argument("--diagnostic-ledger-summary", type=Path, required=True)
    parser.add_argument("--source-failure", type=Path, required=True)
    parser.add_argument("--source-partial-summaries", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args()


def _exact_or_none(value_a: Any, value_b: Any) -> bool:
    if value_a is None or value_b is None:
        return value_a is value_b
    return bool(value_a == value_b)


def main() -> None:
    arguments = _parse_arguments()
    protocol = FROZEN_PROTOCOL_V03.checked()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    endpoint_dir = arguments.output_dir / "endpoints"
    endpoint_dir.mkdir(exist_ok=False)
    started = time.perf_counter()

    with arguments.source_calibration.open("r", encoding="utf-8") as stream:
        calibration = json.load(stream)
    with arguments.source_partial_summaries.open("r", encoding="utf-8") as stream:
        source_summaries = json.load(stream)
    with arguments.source_failure.open("r", encoding="utf-8") as stream:
        source_failure = json.load(stream)
    calibration_lock = validate_source_calibration(calibration)
    _write_json(arguments.output_dir / "source_calibration_lock.json", calibration_lock)

    tests = {
        "schema": "paper2_m2a_v03_repair_pilot_preflight_tests_v01",
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
            "schema": "paper2_m2a_v03_repair_pilot_failure_v01",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "stage": "preflight_tests",
            "completed_endpoints": 0,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        _write_hash_ledger(arguments.output_dir)
        raise SystemExit(2)

    read_only_before = _hash_paths(READ_ONLY_PATHS)
    implementation_paths = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v03.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v03.py",
        Path(__file__).resolve(),
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v03.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v03.py",
    )
    manifest = {
        "schema": "paper2_m2a_v03_ledger_repair_pilot_manifest_v01",
        "protocol": protocol.canonical_payload(),
        "protocol_digest": protocol.digest(),
        "contract_clarification_applied": {
            "status": True,
            "clarified_pilot_endpoint_count": 3,
            "reason": "D0_removed_nonoperational_C0_C1_duplicates",
        },
        "source_calibration_sha256": _sha256(arguments.source_calibration),
        "read_only_sha256_before": read_only_before,
        "implementation_sha256": _hash_paths(implementation_paths),
        "provenance": {
            "contract_v03_sha256": _sha256(arguments.contract_v03),
            "repair_decision_sha256": _sha256(arguments.repair_decision),
            "clarification_decision_sha256": _sha256(arguments.clarification_decision),
            "diagnostic_record_sha256": _sha256(arguments.diagnostic_record),
            "diagnostic_final_sha256": _sha256(arguments.diagnostic_final),
            "diagnostic_ledger_summary_sha256": _sha256(
                arguments.diagnostic_ledger_summary
            ),
            "source_failure_sha256": _sha256(arguments.source_failure),
            "source_partial_summaries_sha256": _sha256(
                arguments.source_partial_summaries
            ),
        },
        "runtime": {
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "cpu_processes": 1,
            "blas_omp_threads": 1,
            "network": "disabled_by_container",
            "gpu_used": False,
        },
    }
    _write_json(arguments.output_dir / "manifest.json", manifest)

    passive_scale = float(calibration["passive"]["dcm_passive_scale"])
    active_scale = float(calibration["active"]["dcm_active_scale"])
    summaries: dict[str, Any] = {}
    structural_gates: dict[str, Any] = {}
    reproduction: dict[str, Any] = {}
    identity: dict[str, Any] = {}

    for index, level in enumerate(protocol.spatial_levels, start=1):
        endpoint_started = time.perf_counter()
        system = build_system_for_level(
            representation="DCM",
            level=level,
            passive_dcm_scale=passive_scale,
            active_dcm_scale=active_scale,
            active_profile="uniform",
        )
        legacy = simulate_endpoint(
            system=system,
            case_id="ID-LN",
            steps_per_cycle=protocol.steps_per_cycle,
            tolerance_label="C0",
        )
        endpoint = upgrade_endpoint_v03(
            system=system,
            case_id="ID-LN",
            steps_per_cycle=protocol.steps_per_cycle,
            legacy_endpoint=legacy,
        )
        endpoint.summary["v03_common_projection_sidecar"] = common_projection_sidecar(
            system, endpoint
        )
        elapsed_endpoint = time.perf_counter() - endpoint_started
        endpoint.summary["runtime_seconds"] = elapsed_endpoint
        key = endpoint_key("ID-LN", "DCM", str(level.label))
        summaries[key] = endpoint.summary
        structural = endpoint_structural_gate(endpoint.summary)
        structural_gates[key] = structural

        old_key = f"ID-LN__DCM__{level.label}__T64__C0"
        old_summary = source_summaries[old_key]
        old_value = float(old_summary["ledger"]["maximum_normalized_residual"])
        replay_value = float(
            legacy.summary["ledger"]["maximum_normalized_residual"]
        )
        old_ledger_fields_exact = all(
            _exact_or_none(legacy.summary["ledger"][field], value)
            for field, value in old_summary["ledger"].items()
        )
        reproduction[key] = {
            "source_key": old_key,
            "source_maximum_normalized_residual": old_value,
            "replayed_maximum_normalized_residual": replay_value,
            "maximum_normalized_residual_exact": replay_value == old_value,
            "old_ledger_summary_fields_exact": old_ledger_fields_exact,
            "old_endpoint_subtraction_gate_pass": replay_value <= 1.0e-8,
            "expected_old_failure_present": replay_value > 1.0e-8
            if level.label == "S4"
            else True,
            "pass": bool(
                replay_value == old_value
                and old_ledger_fields_exact
                and (level.label != "S4" or replay_value > 1.0e-8)
            ),
        }

        array_checks = {
            name: bool(np.array_equal(endpoint.arrays[name], legacy.arrays[name]))
            for name in NONLEDGER_ARRAYS
        }
        summary_checks = {
            name: _exact_or_none(endpoint.summary[name], old_summary[name])
            for name in NONLEDGER_SUMMARY_FIELDS
        }
        dissipation_checks = {
            name: endpoint.summary["ledger"][name]
            == legacy.summary["ledger"][name]
            for name in ("total_drag_dissipation", "total_sls_dissipation")
        }
        identity[key] = {
            "nonledger_arrays_exact": array_checks,
            "nonledger_summary_fields_exact_to_v02_C0": summary_checks,
            "dissipation_exact_to_v02_C0": dissipation_checks,
            "pass": bool(
                all(array_checks.values())
                and all(summary_checks.values())
                and all(dissipation_checks.values())
            ),
        }
        np.savez_compressed(endpoint_dir / f"{key}.npz", **endpoint.arrays)

        resource_pass = bool(
            time.perf_counter() - started <= protocol.pilot_runtime_budget_seconds
            and _peak_memory_gib() <= protocol.memory_budget_gib
        )
        progress = {
            "event": "pilot_endpoint_complete",
            "completed": index,
            "expected": protocol.expected_pilot_endpoint_count,
            "endpoint": key,
            "old_ledger": replay_value,
            "new_ledger": endpoint.summary["ledger"]["maximum_normalized_residual"],
            "closure": endpoint.summary["ledger"][
                "maximum_ledger_minus_equilibrium_work_relative"
            ],
            "pass": bool(
                structural["pass"]
                and reproduction[key]["pass"]
                and identity[key]["pass"]
                and resource_pass
            ),
        }
        print(json.dumps(progress, sort_keys=True), flush=True)
        if not progress["pass"]:
            _write_json(arguments.output_dir / "endpoint_summaries_partial.json", summaries)
            _write_json(arguments.output_dir / "structural_gates_partial.json", structural_gates)
            _write_json(arguments.output_dir / "old_failure_reproduction_partial.json", reproduction)
            _write_json(arguments.output_dir / "physical_identity_partial.json", identity)
            failure = {
                "schema": "paper2_m2a_v03_repair_pilot_failure_v01",
                "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
                "stage": "repair_pilot_endpoint",
                "endpoint": key,
                "completed_endpoints": index,
                "structural_gate": structural,
                "reproduction": reproduction[key],
                "physical_identity": identity[key],
                "resource_pass": resource_pass,
            }
            _write_json(arguments.output_dir / "failure.json", failure)
            _write_hash_ledger(arguments.output_dir)
            raise SystemExit(2)

    _write_json(arguments.output_dir / "endpoint_summaries.json", summaries)
    _write_json(arguments.output_dir / "structural_gates.json", structural_gates)
    _write_json(arguments.output_dir / "old_failure_reproduction.json", reproduction)
    _write_json(arguments.output_dir / "physical_identity.json", identity)

    finite_records: dict[str, Any] = {}
    all_finite = True
    for path in sorted(endpoint_dir.glob("*.npz")):
        with np.load(path) as archive:
            record = {
                name: bool(np.all(np.isfinite(archive[name]))) for name in archive.files
            }
        finite_records[path.name] = record
        all_finite = all_finite and all(record.values())
    finite_audit = {
        "schema": "paper2_m2a_v03_repair_pilot_finite_audit_v01",
        "endpoint_npz_expected": protocol.expected_pilot_endpoint_count,
        "endpoint_npz_found": len(finite_records),
        "records": finite_records,
        "json_finite_enforced_at_write": True,
        "pass": bool(
            all_finite and len(finite_records) == protocol.expected_pilot_endpoint_count
        ),
    }
    _write_json(arguments.output_dir / "finite_value_audit.json", finite_audit)

    read_only_after = _hash_paths(READ_ONLY_PATHS)
    elapsed = time.perf_counter() - started
    peak_memory = _peak_memory_gib()
    resource_pass = bool(
        elapsed <= protocol.pilot_runtime_budget_seconds
        and peak_memory <= protocol.memory_budget_gib
    )
    source_s4_value = float(
        source_failure["structural_gate"]["checks"]["power_ledger"]["value"]
    )
    replay_s4 = reproduction[endpoint_key("ID-LN", "DCM", "S4")][
        "replayed_maximum_normalized_residual"
    ]
    all_pass = bool(
        len(summaries) == protocol.expected_pilot_endpoint_count
        and all(record["pass"] for record in structural_gates.values())
        and all(record["pass"] for record in reproduction.values())
        and all(record["pass"] for record in identity.values())
        and replay_s4 == source_s4_value == 1.465114585633258e-07
        and finite_audit["pass"]
        and read_only_before == read_only_after
        and resource_pass
    )
    summary = {
        "schema": "paper2_m2a_v03_repair_pilot_pass_summary_v01",
        "status": "COMPLETE_PHASE_R",
        "decision": "LEDGER_REPAIR_PILOT_PASS_V03" if all_pass else "FAIL_CLOSED",
        "contract_clarification_applied": True,
        "completed_endpoints": len(summaries),
        "expected_endpoints": protocol.expected_pilot_endpoint_count,
        "source_S4_old_failure": source_s4_value,
        "replayed_S4_old_failure": replay_s4,
        "maximum_new_ledger_residual": max(
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
        "finite_value_audit_pass": finite_audit["pass"],
        "resource": {
            "elapsed_seconds": elapsed,
            "budget_seconds": protocol.pilot_runtime_budget_seconds,
            "peak_memory_gib": peak_memory,
            "memory_budget_gib": protocol.memory_budget_gib,
            "within_budget": resource_pass,
            "cpu_processes": 1,
            "gpu_used": False,
        },
        "automatic_next_phase_authorized": all_pass,
        "evidence_boundary": (
            "Phase R validates only the repaired discrete ledger seam on three fixed "
            "ID-LN/DCM/T64/D0 spatial endpoints."
        ),
    }
    if all_pass:
        _write_json(arguments.output_dir / "pass_summary.json", summary)
    else:
        summary["status"] = "FAIL_CLOSED_AT_SUPERVISOR_GATE"
        _write_json(arguments.output_dir / "failure.json", summary)
    _write_hash_ledger(arguments.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), flush=True)
    if not all_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
