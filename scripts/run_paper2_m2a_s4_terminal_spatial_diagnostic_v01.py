"""Run the authorized M2A S3/S4 terminal spatial diagnostic only."""

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

from paper2_m2.config import FROZEN_CONFIG, SpatialLevel  # noqa: E402
from paper2_m2.identity_2d import (  # noqa: E402
    Endpoint,
    build_system_for_level,
    simulate_endpoint,
)
from paper2_m2.interface_projection import (  # noqa: E402
    common_segment_space_time_l2,
    constant_traction_projection_manufactured_check,
    project_piecewise_linear_to_common_segments,
)


CASES = ("ID-A2", "ID-S1")
REPRESENTATIONS = ("DCM", "FEM")
LEVELS = (
    SpatialLevel("S3", 64, 16),
    SpatialLevel("S4", 128, 32),
)
STEPS_PER_CYCLE = 64
TOLERANCE_LABEL = "C1"
COMMON_SEGMENTS = 64
RUNTIME_BUDGET_SECONDS = 900.0
MEMORY_BUDGET_GIB = 16.0
REPLAY_RELATIVE_TOLERANCE = 1.0e-12
SKIPPED_REPLAY_KEYS = frozenset(("runtime_seconds_including_assembly",))
FROZEN_MODULES = (
    PROJECT_ROOT / "src" / "paper2_m2" / "config.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    _assert_finite_json(payload)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _assert_finite_json(payload: Any, path: str = "root") -> None:
    if isinstance(payload, bool) or payload is None or isinstance(payload, str):
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


def _relative_difference(value_a: float, value_b: float, floor: float) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def _endpoint_structural_gate(endpoint: Endpoint) -> dict[str, Any]:
    config = FROZEN_CONFIG
    summary = endpoint.summary
    checks = {
        "solver_residual": {
            "value": summary["solver"]["maximum_relative_residual"],
            "threshold": summary["solver"]["acceptance_tolerance"],
            "pass": summary["solver"]["pass"],
        },
        "action_reaction": {
            "value": summary["interface_action_reaction_relative_error"],
            "threshold": config.action_reaction_relative_tolerance,
            "pass": summary["interface_action_reaction_relative_error"]
            <= config.action_reaction_relative_tolerance,
        },
        "power_ledger": {
            "value": summary["ledger"]["maximum_normalized_residual"],
            "threshold": config.power_ledger_relative_tolerance,
            "pass": summary["ledger"]["maximum_normalized_residual"]
            <= config.power_ledger_relative_tolerance,
        },
        "nonnegative_dissipation": {
            "value": summary["ledger"]["minimum_physical_dissipation"],
            "threshold": config.dissipation_lower_tolerance,
            "pass": summary["ledger"]["minimum_physical_dissipation"]
            >= config.dissipation_lower_tolerance,
        },
        "cycle_state": {
            "value": summary["cycle_state_relative_difference"],
            "threshold": config.cycle_state_relative_tolerance,
            "pass": summary["cycle_state_relative_difference"]
            <= config.cycle_state_relative_tolerance,
        },
        "ufl_manual_assembly": {
            "value": summary["manufactured_uniform_strain_relative_error"],
            "threshold": config.manufactured_solution_relative_tolerance,
            "pass": summary["manufactured_uniform_strain_relative_error"]
            <= config.manufactured_solution_relative_tolerance,
        },
    }
    return {"pass": all(item["pass"] for item in checks.values()), "checks": checks}


def _native_x(endpoint_system: Any) -> np.ndarray:
    layer = endpoint_system.myocardium_mesh
    return layer.dof_coordinates[layer.top_nodes, 0]


def _traction_field(endpoint: Endpoint, key: str, nodes: int) -> np.ndarray:
    return endpoint.arrays[key].reshape(nodes, 2, -1)[:, :, :STEPS_PER_CYCLE]


def _historical_record(
    old_summary: dict[str, Any],
    *,
    case_id: str,
    representation: str,
    interface_name: str,
) -> dict[str, Any]:
    candidates = [
        record
        for record in old_summary["comparisons"]
        if record.get("case_id") == case_id
        and record.get("representation") == representation
        and record.get("interface") == interface_name
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one historical S2/S3 record for "
            f"{case_id}/{representation}/{interface_name}"
        )
    return candidates[0]


def _direction_consistent(
    earlier_value: float,
    middle_value: float,
    refined_value: float,
) -> bool:
    first_increment = middle_value - earlier_value
    second_increment = refined_value - middle_value
    scale = max(
        abs(earlier_value),
        abs(middle_value),
        abs(refined_value),
        FROZEN_CONFIG.near_zero_traction_absolute_scale,
    )
    return bool(
        first_increment * second_increment >= 0.0
        or (
            abs(first_increment)
            <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance * scale
            and abs(second_increment)
            <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance * scale
        )
    )


def _compare_replay_values(
    old_value: Any,
    new_value: Any,
    *,
    path: str,
    record: dict[str, Any],
) -> None:
    if isinstance(old_value, dict):
        if not isinstance(new_value, dict):
            record["failures"].append(f"{path}:type")
            return
        old_keys = set(old_value) - SKIPPED_REPLAY_KEYS
        new_keys = set(new_value) - SKIPPED_REPLAY_KEYS
        if old_keys != new_keys:
            record["failures"].append(f"{path}:keys")
            return
        for key in sorted(old_keys):
            _compare_replay_values(
                old_value[key],
                new_value[key],
                path=f"{path}.{key}",
                record=record,
            )
        return
    if isinstance(old_value, bool):
        record["exact_paths_compared"] += 1
        if not isinstance(new_value, bool) or old_value is not new_value:
            record["failures"].append(path)
        return
    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        difference = _relative_difference(float(old_value), float(new_value), 1.0e-30)
        record["numeric_paths_compared"] += 1
        record["maximum_numeric_relative_difference"] = max(
            record["maximum_numeric_relative_difference"], difference
        )
        if difference > REPLAY_RELATIVE_TOLERANCE:
            record["failures"].append(path)
        return
    record["exact_paths_compared"] += 1
    if old_value != new_value:
        record["failures"].append(path)


def _replay_record(old_summary: dict[str, Any], new_summary: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "relative_tolerance": REPLAY_RELATIVE_TOLERANCE,
        "skipped_nondeterministic_keys": sorted(SKIPPED_REPLAY_KEYS),
        "numeric_paths_compared": 0,
        "exact_paths_compared": 0,
        "maximum_numeric_relative_difference": 0.0,
        "failures": [],
    }
    _compare_replay_values(old_summary, new_summary, path="summary", record=record)
    record["pass"] = not record["failures"]
    return record


def _run_assembly_probe(
    passive_scale: float,
    active_scale: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    system = build_system_for_level(
        representation="FEM",
        level=LEVELS[1],
        passive_dcm_scale=passive_scale,
        active_dcm_scale=active_scale,
        active_profile="uniform",
    )
    manufactured_error = float(system.manufactured_error)
    threshold = float(FROZEN_CONFIG.manufactured_solution_relative_tolerance)
    return {
        "schema": "paper2_m2a_s4_endpoint_assembly_probe_v01",
        "representation": "FEM",
        "case_profile": "ID-A2_uniform",
        "spatial_level": "S4",
        "nx": LEVELS[1].nx,
        "ny_per_layer": LEVELS[1].ny_per_layer,
        "state_size": system.state_size,
        "matrix_a_shape": list(system.matrix_a.shape),
        "matrix_a_nnz": int(system.matrix_a.nnz),
        "ufl_manual_relative_error": manufactured_error,
        "threshold": threshold,
        "elapsed_seconds": time.perf_counter() - started,
        "pass": manufactured_error <= threshold,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--autonomous-decision", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--s3-execution-record", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--source-s3-summary", type=Path, required=True)
    parser.add_argument("--source-s3-endpoint-summaries", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    endpoints_dir = arguments.output_dir / "endpoints"
    endpoints_dir.mkdir(exist_ok=False)
    started = time.perf_counter()

    with arguments.source_calibration.open("r", encoding="utf-8") as stream:
        calibration = json.load(stream)
    with arguments.source_s3_summary.open("r", encoding="utf-8") as stream:
        old_s3_summary = json.load(stream)
    with arguments.source_s3_endpoint_summaries.open("r", encoding="utf-8") as stream:
        old_s3_endpoint_summaries = json.load(stream)
    if calibration["config_digest"] != FROZEN_CONFIG.digest():
        _write_json(
            arguments.output_dir / "failure.json",
            {
                "status": "FAIL_CLOSED",
                "stage": "source_calibration",
                "reason": "source calibration does not match frozen M2A configuration",
            },
        )
        raise SystemExit(2)
    passive_scale = float(calibration["passive"]["dcm_passive_scale"])
    active_scale = float(calibration["active"]["dcm_active_scale"])

    preflight_tests = {
        "schema": "paper2_m2a_s4_preflight_tests_v01",
        "host_targeted_pytest": arguments.host_pytest_summary,
        "frozen_container_targeted_pytest": arguments.container_pytest_summary,
        "pass": (
            "passed" in arguments.host_pytest_summary
            and "passed" in arguments.container_pytest_summary
        ),
    }
    _write_json(arguments.output_dir / "preflight_tests.json", preflight_tests)
    if not preflight_tests["pass"]:
        _write_json(
            arguments.output_dir / "failure.json",
            {
                "status": "FAIL_CLOSED",
                "stage": "targeted_tests",
                "preflight_tests": preflight_tests,
            },
        )
        raise SystemExit(2)

    projection_checks = {
        "schema": "paper2_m2a_s4_common_interface_projection_checks_v01",
        "definition": (
            "exact integral average of native P1 nodal traction on each of the "
            "64 frozen S3 common segments"
        ),
        "S3_to_common_S3": constant_traction_projection_manufactured_check(
            native_segments=64, common_segments=COMMON_SEGMENTS
        ),
        "S4_to_common_S3": constant_traction_projection_manufactured_check(
            native_segments=128, common_segments=COMMON_SEGMENTS
        ),
    }
    projection_checks["pass"] = bool(
        projection_checks["S3_to_common_S3"]["pass"]
        and projection_checks["S4_to_common_S3"]["pass"]
    )
    _write_json(
        arguments.output_dir / "projection_manufactured_checks.json",
        projection_checks,
    )
    if not projection_checks["pass"]:
        _write_json(
            arguments.output_dir / "failure.json",
            {
                "status": "FAIL_CLOSED",
                "stage": "projection_manufactured_checks",
                "checks": projection_checks,
            },
        )
        raise SystemExit(2)

    frozen_hashes_before = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in FROZEN_MODULES
    }
    manifest = {
        "schema": "paper2_m2a_s4_terminal_spatial_diagnostic_manifest_v01",
        "authorized_scope": {
            "cases": list(CASES),
            "representations": list(REPRESENTATIONS),
            "levels": [
                {
                    "label": level.label,
                    "nx": level.nx,
                    "ny_per_layer": level.ny_per_layer,
                }
                for level in LEVELS
            ],
            "steps_per_cycle": STEPS_PER_CYCLE,
            "tolerance": TOLERANCE_LABEL,
            "common_segments": COMMON_SEGMENTS,
            "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
            "memory_budget_gib": MEMORY_BUDGET_GIB,
        },
        "frozen_config_digest": FROZEN_CONFIG.digest(),
        "fixed_calibration": {
            "dcm_passive_scale": passive_scale,
            "dcm_active_scale": active_scale,
        },
        "frozen_module_sha256_before": frozen_hashes_before,
        "provenance": {
            "authorization_sha256": _sha256(arguments.authorization),
            "autonomous_decision_sha256": _sha256(arguments.autonomous_decision),
            "contract_sha256": _sha256(arguments.contract),
            "s3_execution_record_sha256": _sha256(arguments.s3_execution_record),
            "source_calibration_sha256": _sha256(arguments.source_calibration),
            "source_s3_summary_sha256": _sha256(arguments.source_s3_summary),
            "source_s3_endpoint_summaries_sha256": _sha256(
                arguments.source_s3_endpoint_summaries
            ),
            "runner_sha256": _sha256(Path(__file__).resolve()),
        },
        "runtime": {
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "cpu_processes": 1,
            "network": "disabled_by_container",
            "gpu_used": False,
        },
    }
    _write_json(arguments.output_dir / "manifest.json", manifest)

    assembly_probe = _run_assembly_probe(passive_scale, active_scale)
    _write_json(arguments.output_dir / "assembly_probe.json", assembly_probe)
    if not assembly_probe["pass"]:
        _write_json(
            arguments.output_dir / "failure.json",
            {
                "status": "FAIL_CLOSED",
                "stage": "S4_endpoint_assembly_probe",
                "probe": assembly_probe,
            },
        )
        raise SystemExit(2)

    endpoints: dict[tuple[str, str, str], Endpoint] = {}
    systems: dict[tuple[str, str, str], Any] = {}
    structural_gates: dict[str, Any] = {}
    endpoint_summaries: dict[str, Any] = {}
    for case_id in CASES:
        profile = "S1" if case_id == "ID-S1" else "uniform"
        for representation in REPRESENTATIONS:
            for level in LEVELS:
                endpoint_started = time.perf_counter()
                system = build_system_for_level(
                    representation=representation,
                    level=level,
                    passive_dcm_scale=passive_scale,
                    active_dcm_scale=active_scale,
                    active_profile=profile,
                )
                endpoint = simulate_endpoint(
                    system=system,
                    case_id=case_id,
                    steps_per_cycle=STEPS_PER_CYCLE,
                    tolerance_label=TOLERANCE_LABEL,
                )
                endpoint.summary["runtime_seconds_including_assembly"] = (
                    time.perf_counter() - endpoint_started
                )
                key = (case_id, representation, str(level.label))
                text_key = "__".join(key)
                endpoints[key] = endpoint
                systems[key] = system
                endpoint_summaries[text_key] = endpoint.summary
                structural = _endpoint_structural_gate(endpoint)
                structural_gates[text_key] = structural
                np.savez_compressed(endpoints_dir / f"{text_key}.npz", **endpoint.arrays)
                if not structural["pass"]:
                    _write_json(
                        arguments.output_dir / "failure.json",
                        {
                            "status": "FAIL_CLOSED",
                            "stage": "endpoint_structural_gate",
                            "endpoint": text_key,
                            "gate": structural,
                        },
                    )
                    raise SystemExit(2)
                elapsed_now = time.perf_counter() - started
                peak_now = float(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    / (1024.0 * 1024.0)
                )
                if elapsed_now > RUNTIME_BUDGET_SECONDS or peak_now > MEMORY_BUDGET_GIB:
                    _write_json(
                        arguments.output_dir / "failure.json",
                        {
                            "status": "FAIL_CLOSED",
                            "stage": "resource_budget",
                            "elapsed_seconds": elapsed_now,
                            "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
                            "peak_memory_gib": peak_now,
                            "memory_budget_gib": MEMORY_BUDGET_GIB,
                        },
                    )
                    raise SystemExit(2)

    _write_json(arguments.output_dir / "endpoint_summaries.json", endpoint_summaries)
    _write_json(arguments.output_dir / "structural_gates.json", structural_gates)

    replay_records: dict[str, Any] = {}
    replay_all_pass = True
    for case_id in CASES:
        for representation in REPRESENTATIONS:
            text_key = "__".join((case_id, representation, "S3"))
            replay = _replay_record(
                old_s3_endpoint_summaries[text_key], endpoint_summaries[text_key]
            )
            replay_records[text_key] = replay
            replay_all_pass = replay_all_pass and replay["pass"]
    s3_replay = {
        "schema": "paper2_m2a_s3_summary_pointwise_replay_v01",
        "source": str(arguments.source_s3_endpoint_summaries),
        "records": replay_records,
        "pass": replay_all_pass,
    }
    _write_json(arguments.output_dir / "s3_replay.json", s3_replay)

    common_x = np.linspace(
        -0.5 * FROZEN_CONFIG.length,
        0.5 * FROZEN_CONFIG.length,
        COMMON_SEGMENTS + 1,
    )
    comparison_records: list[dict[str, Any]] = []
    observable_dependent_records: list[str] = []
    native_all_pass = True
    projected_all_pass = True
    native_direction_all_consistent = True
    projected_direction_all_consistent = True
    for case_id in CASES:
        for representation in REPRESENTATIONS:
            system_s3 = systems[(case_id, representation, "S3")]
            system_s4 = systems[(case_id, representation, "S4")]
            endpoint_s3 = endpoints[(case_id, representation, "S3")]
            endpoint_s4 = endpoints[(case_id, representation, "S4")]
            for interface_name, array_key, summary_metric in (
                (
                    "myocardium_ecm",
                    "myocardium_ecm_traction_two_cycles",
                    "myocardium_ecm_traction_l2",
                ),
                (
                    "endocardium_ecm",
                    "endocardium_ecm_traction_two_cycles",
                    "endocardium_ecm_traction_l2",
                ),
            ):
                nodes_s3 = len(system_s3.interface_weights)
                nodes_s4 = len(system_s4.interface_weights)
                traction_s3 = _traction_field(endpoint_s3, array_key, nodes_s3)
                traction_s4 = _traction_field(endpoint_s4, array_key, nodes_s4)
                projected_s3 = project_piecewise_linear_to_common_segments(
                    _native_x(system_s3), traction_s3, common_x
                )
                projected_s4 = project_piecewise_linear_to_common_segments(
                    _native_x(system_s4), traction_s4, common_x
                )
                native_s3 = float(endpoint_s3.summary[summary_metric])
                native_s4 = float(endpoint_s4.summary[summary_metric])
                projected_l2_s3 = common_segment_space_time_l2(
                    common_x,
                    projected_s3,
                    FROZEN_CONFIG.period / STEPS_PER_CYCLE,
                )
                projected_l2_s4 = common_segment_space_time_l2(
                    common_x,
                    projected_s4,
                    FROZEN_CONFIG.period / STEPS_PER_CYCLE,
                )
                native_difference = _relative_difference(
                    native_s3,
                    native_s4,
                    FROZEN_CONFIG.near_zero_traction_absolute_scale,
                )
                projected_difference = _relative_difference(
                    projected_l2_s3,
                    projected_l2_s4,
                    FROZEN_CONFIG.near_zero_traction_absolute_scale,
                )
                threshold = FROZEN_CONFIG.spatial_endpoint_relative_tolerance
                native_pass = native_difference <= threshold
                projected_pass = projected_difference <= threshold
                historical = _historical_record(
                    old_s3_summary,
                    case_id=case_id,
                    representation=representation,
                    interface_name=interface_name,
                )
                historical_native_s2 = float(historical["recomputed_native_S2"])
                historical_native_s3 = float(historical["native_S3"])
                historical_projected_s2 = float(historical["projected_common_S2"])
                historical_projected_s3 = float(historical["projected_common_S3"])
                native_direction_consistent = _direction_consistent(
                    historical_native_s2, historical_native_s3, native_s4
                )
                projected_direction_consistent = _direction_consistent(
                    historical_projected_s2, historical_projected_s3, projected_l2_s4
                )
                observable_conclusion_differs = native_pass != projected_pass
                if observable_conclusion_differs:
                    observable_dependent_records.append(
                        f"{case_id}:{representation}:{interface_name}"
                    )
                native_all_pass = native_all_pass and native_pass
                projected_all_pass = projected_all_pass and projected_pass
                native_direction_all_consistent = (
                    native_direction_all_consistent and native_direction_consistent
                )
                projected_direction_all_consistent = (
                    projected_direction_all_consistent and projected_direction_consistent
                )
                comparison_records.append(
                    {
                        "case_id": case_id,
                        "representation": representation,
                        "interface": interface_name,
                        "historical_native_S2": historical_native_s2,
                        "historical_native_S3": historical_native_s3,
                        "recomputed_native_S3": native_s3,
                        "native_S4": native_s4,
                        "native_S3_source_replay_relative_difference": _relative_difference(
                            historical_native_s3,
                            native_s3,
                            FROZEN_CONFIG.near_zero_traction_absolute_scale,
                        ),
                        "native_S3_S4_relative_difference": native_difference,
                        "native_pass_1pct": native_pass,
                        "historical_projected_common_S2": historical_projected_s2,
                        "historical_projected_common_S3": historical_projected_s3,
                        "recomputed_projected_common_S3": projected_l2_s3,
                        "projected_common_S4": projected_l2_s4,
                        "projected_S3_source_replay_relative_difference": _relative_difference(
                            historical_projected_s3,
                            projected_l2_s3,
                            FROZEN_CONFIG.near_zero_traction_absolute_scale,
                        ),
                        "projected_S3_S4_relative_difference": projected_difference,
                        "projected_pass_1pct": projected_pass,
                        "native_direction_S2_S3_to_S3_S4_consistent": (
                            native_direction_consistent
                        ),
                        "projected_direction_S2_S3_to_S3_S4_consistent": (
                            projected_direction_consistent
                        ),
                        "observable_conclusion_differs": observable_conclusion_differs,
                        "threshold": threshold,
                    }
                )

    frozen_hashes_after = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in FROZEN_MODULES
    }
    frozen_modules_unchanged = frozen_hashes_before == frozen_hashes_after
    structural_all_pass = bool(
        preflight_tests["pass"]
        and projection_checks["pass"]
        and assembly_probe["pass"]
        and all(record["pass"] for record in structural_gates.values())
        and replay_all_pass
        and frozen_modules_unchanged
    )
    directions_all_consistent = bool(
        native_direction_all_consistent and projected_direction_all_consistent
    )

    elapsed_seconds = time.perf_counter() - started
    peak_memory_gib = float(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)
    )
    within_budget = bool(
        elapsed_seconds <= RUNTIME_BUDGET_SECONDS
        and peak_memory_gib <= MEMORY_BUDGET_GIB
    )
    if not structural_all_pass or not within_budget:
        diagnostic_decision = "DIAGNOSTIC_FAIL"
        rationale = (
            "a structural, projection, assembly, S3 replay, frozen-module, or resource gate failed"
        )
    elif observable_dependent_records:
        diagnostic_decision = "OBSERVABLE_DEPENDENT"
        rationale = (
            "native nodal and frozen common-segment observables give different 1% conclusions"
        )
    elif native_all_pass and projected_all_pass and directions_all_consistent:
        diagnostic_decision = "DIAGNOSTIC_PASS"
        rationale = (
            "all eight interface indicators enter the 1% band in both observables "
            "with S2/S3-to-S3/S4 direction consistency"
        )
    else:
        diagnostic_decision = "DIAGNOSTIC_FAIL"
        rationale = (
            "at least one interface indicator remains above 1% or reverses refinement direction"
        )

    summary = {
        "schema": "paper2_m2a_s4_terminal_spatial_diagnostic_summary_v01",
        "status": "COMPLETE_AT_SUPERVISOR_GATE",
        "diagnostic_decision": diagnostic_decision,
        "rationale": rationale,
        "structural_all_pass": structural_all_pass,
        "native_all_pass_1pct": native_all_pass,
        "projected_all_pass_1pct": projected_all_pass,
        "native_direction_all_consistent": native_direction_all_consistent,
        "projected_direction_all_consistent": projected_direction_all_consistent,
        "observable_dependent_records": observable_dependent_records,
        "comparisons": comparison_records,
        "frozen_modules": {
            "before": frozen_hashes_before,
            "after": frozen_hashes_after,
            "unchanged": frozen_modules_unchanged,
        },
        "resource": {
            "elapsed_seconds": elapsed_seconds,
            "budget_seconds": RUNTIME_BUDGET_SECONDS,
            "peak_memory_gib": peak_memory_gib,
            "memory_budget_gib": MEMORY_BUDGET_GIB,
            "within_budget": within_budget,
            "cpu_processes": 1,
            "gpu_used": False,
        },
        "stop_boundary": {
            "S5_run": False,
            "T128_run": False,
            "T256_run": False,
            "full_324_endpoint_matrix_run": False,
            "M2B_run": False,
            "identity_GO_MAYBE_NO_GO_issued": False,
            "production_metric_changed": False,
            "production_spatial_ladder_changed": False,
        },
        "evidence_boundary": (
            "This is the authorized fixed-T64 terminal S3/S4 spatial diagnostic, "
            "not M2A identity acceptance or a three-dimensional result."
        ),
    }
    _write_json(arguments.output_dir / "diagnostic_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
