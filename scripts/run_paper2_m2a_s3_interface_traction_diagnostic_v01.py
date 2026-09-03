"""Run the authorized M2A S2/S3 interface-traction diagnostic only."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    FROZEN_CONFIG.spatial("S2"),
    SpatialLevel("S3", 64, 16),
)
STEPS_PER_CYCLE = 64
TOLERANCE_LABEL = "C1"
COMMON_SEGMENTS = 32
RUNTIME_BUDGET_SECONDS = 900.0
MEMORY_BUDGET_GIB = 16.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


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


def _old_spatial_record(
    old_gate: dict[str, Any],
    *,
    case_id: str,
    representation: str,
    metric: str,
) -> dict[str, Any]:
    candidates = [
        record
        for record in old_gate["comparisons"]
        if record.get("kind") == "spatial"
        and record.get("case_id") == case_id
        and record.get("representation") == representation
        and record.get("tolerance_label") == "C1"
        and record.get("metric") == metric
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one historical record for {case_id}/{representation}/{metric}"
        )
    return candidates[0]


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--failure-record", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--source-stage-gate", type=Path, required=True)
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
    with arguments.source_stage_gate.open("r", encoding="utf-8") as stream:
        old_stage_gate = json.load(stream)
    if calibration["config_digest"] != FROZEN_CONFIG.digest():
        raise RuntimeError("source calibration does not match frozen M2A configuration")
    passive_scale = float(calibration["passive"]["dcm_passive_scale"])
    active_scale = float(calibration["active"]["dcm_active_scale"])

    projection_checks = {
        "schema": "paper2_m2a_common_interface_projection_checks_v01",
        "definition": (
            "exact integral average of native P1 nodal traction on each of the 32 S2 common segments"
        ),
        "S2_to_common_S2": constant_traction_projection_manufactured_check(
            native_segments=32, common_segments=COMMON_SEGMENTS
        ),
        "S3_to_common_S2": constant_traction_projection_manufactured_check(
            native_segments=64, common_segments=COMMON_SEGMENTS
        ),
    }
    projection_checks["pass"] = bool(
        projection_checks["S2_to_common_S2"]["pass"]
        and projection_checks["S3_to_common_S2"]["pass"]
    )
    _write_json(arguments.output_dir / "projection_manufactured_checks.json", projection_checks)
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

    manifest = {
        "schema": "paper2_m2a_s3_interface_traction_diagnostic_manifest_v01",
        "authorized_scope": {
            "cases": list(CASES),
            "representations": list(REPRESENTATIONS),
            "levels": [
                {"label": level.label, "nx": level.nx, "ny_per_layer": level.ny_per_layer}
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
        "provenance": {
            "authorization_sha256": _sha256(arguments.authorization),
            "contract_sha256": _sha256(arguments.contract),
            "failure_record_sha256": _sha256(arguments.failure_record),
            "source_calibration_sha256": _sha256(arguments.source_calibration),
            "source_stage_gate_sha256": _sha256(arguments.source_stage_gate),
            "runner_sha256": _sha256(Path(__file__).resolve()),
            "projection_module_sha256": _sha256(
                PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py"
            ),
            "model_module_sha256": _sha256(
                PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py"
            ),
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
                elapsed = time.perf_counter() - endpoint_started
                endpoint.summary["runtime_seconds_including_assembly"] = elapsed
                key = (case_id, representation, str(level.label))
                text_key = "__".join(key)
                endpoints[key] = endpoint
                systems[key] = system
                endpoint_summaries[text_key] = endpoint.summary
                structural = _endpoint_structural_gate(endpoint)
                structural_gates[text_key] = structural
                np.savez_compressed(
                    endpoints_dir / f"{text_key}.npz",
                    **endpoint.arrays,
                )
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
                if time.perf_counter() - started > RUNTIME_BUDGET_SECONDS:
                    _write_json(
                        arguments.output_dir / "failure.json",
                        {
                            "status": "FAIL_CLOSED",
                            "stage": "runtime_budget",
                            "elapsed_seconds": time.perf_counter() - started,
                            "budget_seconds": RUNTIME_BUDGET_SECONDS,
                        },
                    )
                    raise SystemExit(2)

    _write_json(arguments.output_dir / "endpoint_summaries.json", endpoint_summaries)
    _write_json(arguments.output_dir / "structural_gates.json", structural_gates)

    common_x = np.linspace(-0.5 * FROZEN_CONFIG.length, 0.5 * FROZEN_CONFIG.length, COMMON_SEGMENTS + 1)
    comparison_records: list[dict[str, Any]] = []
    observable_dependent_records: list[str] = []
    node_all_pass = True
    projected_all_pass = True
    direction_all_consistent = True
    replay_all_pass = True
    for case_id in CASES:
        for representation in REPRESENTATIONS:
            system_s2 = systems[(case_id, representation, "S2")]
            system_s3 = systems[(case_id, representation, "S3")]
            endpoint_s2 = endpoints[(case_id, representation, "S2")]
            endpoint_s3 = endpoints[(case_id, representation, "S3")]
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
                nodes_s2 = len(system_s2.interface_weights)
                nodes_s3 = len(system_s3.interface_weights)
                traction_s2 = _traction_field(endpoint_s2, array_key, nodes_s2)
                traction_s3 = _traction_field(endpoint_s3, array_key, nodes_s3)
                x_s2 = _native_x(system_s2)
                x_s3 = _native_x(system_s3)
                projected_s2 = project_piecewise_linear_to_common_segments(
                    x_s2, traction_s2, common_x
                )
                projected_s3 = project_piecewise_linear_to_common_segments(
                    x_s3, traction_s3, common_x
                )
                native_s2 = float(endpoint_s2.summary[summary_metric])
                native_s3 = float(endpoint_s3.summary[summary_metric])
                projected_l2_s2 = common_segment_space_time_l2(
                    common_x,
                    projected_s2,
                    FROZEN_CONFIG.period / STEPS_PER_CYCLE,
                )
                projected_l2_s3 = common_segment_space_time_l2(
                    common_x,
                    projected_s3,
                    FROZEN_CONFIG.period / STEPS_PER_CYCLE,
                )
                native_difference = _relative_difference(
                    native_s2,
                    native_s3,
                    FROZEN_CONFIG.near_zero_traction_absolute_scale,
                )
                projected_difference = _relative_difference(
                    projected_l2_s2,
                    projected_l2_s3,
                    FROZEN_CONFIG.near_zero_traction_absolute_scale,
                )
                native_pass = native_difference <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance
                projected_pass = projected_difference <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance
                old_record = _old_spatial_record(
                    old_stage_gate,
                    case_id=case_id,
                    representation=representation,
                    metric=summary_metric,
                )
                old_s1, old_s2 = [float(value) for value in old_record["values_S0_S1_S2"][1:]]
                replay_difference = _relative_difference(
                    old_s2,
                    native_s2,
                    FROZEN_CONFIG.near_zero_traction_absolute_scale,
                )
                replay_pass = replay_difference <= 1.0e-12
                first_increment = old_s2 - old_s1
                second_increment = native_s3 - native_s2
                scale = max(abs(old_s1), abs(old_s2), abs(native_s3), FROZEN_CONFIG.near_zero_traction_absolute_scale)
                direction_consistent = bool(
                    first_increment * second_increment >= 0.0
                    or (
                        abs(first_increment) <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance * scale
                        and abs(second_increment) <= FROZEN_CONFIG.spatial_endpoint_relative_tolerance * scale
                    )
                )
                observable_conclusion_differs = native_pass != projected_pass
                if observable_conclusion_differs:
                    observable_dependent_records.append(
                        f"{case_id}:{representation}:{interface_name}"
                    )
                node_all_pass = node_all_pass and native_pass
                projected_all_pass = projected_all_pass and projected_pass
                direction_all_consistent = direction_all_consistent and direction_consistent
                replay_all_pass = replay_all_pass and replay_pass
                comparison_records.append(
                    {
                        "case_id": case_id,
                        "representation": representation,
                        "interface": interface_name,
                        "historical_native_S1": old_s1,
                        "historical_native_S2": old_s2,
                        "recomputed_native_S2": native_s2,
                        "native_S3": native_s3,
                        "native_S2_replay_relative_difference": replay_difference,
                        "native_S2_replay_pass": replay_pass,
                        "native_S2_S3_relative_difference": native_difference,
                        "native_pass_1pct": native_pass,
                        "projected_common_S2": projected_l2_s2,
                        "projected_common_S3": projected_l2_s3,
                        "projected_S2_S3_relative_difference": projected_difference,
                        "projected_pass_1pct": projected_pass,
                        "historical_to_new_native_direction_consistent": direction_consistent,
                        "observable_conclusion_differs": observable_conclusion_differs,
                        "threshold": FROZEN_CONFIG.spatial_endpoint_relative_tolerance,
                    }
                )

    structural_all_pass = bool(
        projection_checks["pass"]
        and all(record["pass"] for record in structural_gates.values())
        and replay_all_pass
    )
    if not structural_all_pass:
        diagnostic_decision = "DIAGNOSTIC_FAIL"
        rationale = "a structural, projection-manufactured, or S2 replay gate failed"
    elif observable_dependent_records:
        diagnostic_decision = "OBSERVABLE_DEPENDENT"
        rationale = "native nodal and conservative common-segment observables give different 1% conclusions"
    elif node_all_pass and projected_all_pass and direction_all_consistent:
        diagnostic_decision = "DIAGNOSTIC_PASS"
        rationale = "both observables enter the 1% band and the native refinement direction is consistent"
    else:
        diagnostic_decision = "DIAGNOSTIC_FAIL"
        rationale = "at least one main traction indicator remains above 1% or reverses refinement direction"

    elapsed_seconds = time.perf_counter() - started
    peak_memory_gib = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0))
    within_budget = bool(
        elapsed_seconds <= RUNTIME_BUDGET_SECONDS
        and peak_memory_gib <= MEMORY_BUDGET_GIB
    )
    if not within_budget:
        diagnostic_decision = "DIAGNOSTIC_FAIL"
        rationale = "the authorized runtime or memory budget was exceeded"
    summary = {
        "schema": "paper2_m2a_s3_interface_traction_diagnostic_summary_v01",
        "status": "COMPLETE_AT_HUMAN_GATE",
        "diagnostic_decision": diagnostic_decision,
        "rationale": rationale,
        "structural_all_pass": structural_all_pass,
        "native_all_pass_1pct": node_all_pass,
        "projected_all_pass_1pct": projected_all_pass,
        "native_direction_all_consistent": direction_all_consistent,
        "observable_dependent_records": observable_dependent_records,
        "comparisons": comparison_records,
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
            "T128_run": False,
            "T256_run": False,
            "full_324_endpoint_matrix_run": False,
            "identity_GO_MAYBE_NO_GO_issued": False,
            "production_metric_changed": False,
            "production_spatial_ladder_changed": False,
        },
        "evidence_boundary": (
            "This is a fixed-T64 interface-observable diagnostic, not M2A identity acceptance."
        ),
    }
    _write_json(arguments.output_dir / "diagnostic_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
