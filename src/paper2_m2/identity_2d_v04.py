"""T128 orchestration, gates, and T64-to-T128 pair audit for M2A v04."""

from __future__ import annotations

from typing import Any

import numpy as np

from .config import FROZEN_CONFIG
from .identity_2d_v03 import (
    DYNAMIC_HOLDOUT_CASES,
    endpoint_structural_gate as _endpoint_structural_gate_v03,
    metric_floor,
    metrics_for_case,
    relative_difference,
    simulate_endpoint_v03,
    summary_metric,
)
from .interface_projection import (
    common_segment_space_time_l2,
    project_piecewise_linear_to_common_segments,
)
from .protocol_v04 import FROZEN_PROTOCOL_V04


def endpoint_key(case_id: str, representation: str, spatial_label: str) -> str:
    return "__".join((case_id, representation, spatial_label, "T128", "D0"))


def t64_endpoint_key(case_id: str, representation: str, spatial_label: str) -> str:
    return "__".join((case_id, representation, spatial_label, "T64", "D0"))


def simulate_endpoint_v04(*, system: Any, case_id: str) -> Any:
    endpoint = simulate_endpoint_v03(
        system=system,
        case_id=case_id,
        steps_per_cycle=FROZEN_PROTOCOL_V04.steps_per_cycle,
    )
    endpoint.summary["stage_protocol"] = "paper2_m2a_protocol_v04"
    return endpoint


def endpoint_structural_gate(summary: dict[str, Any]) -> dict[str, Any]:
    gate = _endpoint_structural_gate_v03(summary)
    return {
        "schema": "paper2_m2a_v04_endpoint_structural_gate_v01",
        "pass": gate["pass"],
        "checks": gate["checks"],
    }


def _native_x(system: Any) -> np.ndarray:
    layer = system.myocardium_mesh
    return layer.dof_coordinates[layer.top_nodes, 0]


def _traction_field(endpoint: Any, key: str, nodes: int) -> np.ndarray:
    steps = FROZEN_PROTOCOL_V04.steps_per_cycle
    return endpoint.arrays[key].reshape(nodes, 2, -1)[:, :, :steps]


def common_projection_sidecar(system: Any, endpoint: Any) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V04
    if system.spatial_label not in ("S3", "S4"):
        return {
            "available": False,
            "reason": "S2 is coarser than the frozen 64-segment diagnostic grid",
        }
    common_x = np.linspace(
        -0.5 * FROZEN_CONFIG.length,
        0.5 * FROZEN_CONFIG.length,
        protocol.common_projection_segments + 1,
    )
    nodes = len(system.interface_weights)
    values: dict[str, float] = {}
    for metric, array_key in (
        ("myocardium_ecm_traction_l2", "myocardium_ecm_traction_two_cycles"),
        ("endocardium_ecm_traction_l2", "endocardium_ecm_traction_two_cycles"),
    ):
        traction = _traction_field(endpoint, array_key, nodes)
        projected = project_piecewise_linear_to_common_segments(
            _native_x(system), traction, common_x
        )
        values[metric] = common_segment_space_time_l2(
            common_x,
            projected,
            FROZEN_CONFIG.period / protocol.steps_per_cycle,
        )
    return {
        "available": True,
        "role": "diagnostic_sidecar_not_production_gate",
        "common_segments": protocol.common_projection_segments,
        "steps_per_cycle": protocol.steps_per_cycle,
        "values": values,
    }


def _direction_consistent(values: list[float], floor: float) -> bool:
    first_increment = values[1] - values[0]
    second_increment = values[2] - values[1]
    scale = max(*(abs(value) for value in values), floor)
    tolerance = FROZEN_CONFIG.spatial_endpoint_relative_tolerance
    return bool(
        first_increment * second_increment >= 0.0
        or (
            abs(first_increment) <= tolerance * scale
            and abs(second_increment) <= tolerance * scale
        )
    )


def t128_numerical_gate(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V04
    config = FROZEN_CONFIG
    comparisons: list[dict[str, Any]] = []
    failures: list[str] = []
    projection_observable_differences: list[str] = []

    for case_id in config.cases:
        metrics = metrics_for_case(case_id)
        for representation in protocol.representations:
            level_values: dict[str, dict[str, float]] = {}
            for spatial_label in ("S2", "S3", "S4"):
                key = endpoint_key(case_id, representation, spatial_label)
                level_values[spatial_label] = {
                    metric: summary_metric(summaries[key], metric)
                    for metric in metrics
                }
            for metric in metrics:
                values = [
                    level_values[level][metric] for level in ("S2", "S3", "S4")
                ]
                floor = metric_floor(metric)
                fine_difference = relative_difference(values[1], values[2], floor)
                direction_consistent = _direction_consistent(values, floor)
                passed = bool(
                    fine_difference <= config.spatial_endpoint_relative_tolerance
                    and direction_consistent
                )
                record: dict[str, Any] = {
                    "kind": "spatial",
                    "case_id": case_id,
                    "representation": representation,
                    "solver_level": "D0",
                    "steps_per_cycle": 128,
                    "metric": metric,
                    "values_S2_S3_S4": values,
                    "finest_two_relative_difference": fine_difference,
                    "threshold": config.spatial_endpoint_relative_tolerance,
                    "direction_consistent": direction_consistent,
                    "production_observable": "native_nodal_or_spring",
                    "pass": passed,
                }
                if metric in (
                    "myocardium_ecm_traction_l2",
                    "endocardium_ecm_traction_l2",
                ):
                    projected_s3 = float(
                        summaries[endpoint_key(case_id, representation, "S3")][
                            "v04_common_projection_sidecar"
                        ]["values"][metric]
                    )
                    projected_s4 = float(
                        summaries[endpoint_key(case_id, representation, "S4")][
                            "v04_common_projection_sidecar"
                        ]["values"][metric]
                    )
                    projected_difference = relative_difference(
                        projected_s3, projected_s4, floor
                    )
                    projected_pass = (
                        projected_difference <= config.spatial_endpoint_relative_tolerance
                    )
                    record["diagnostic_common_projection"] = {
                        "common_segments": protocol.common_projection_segments,
                        "values_S3_S4": [projected_s3, projected_s4],
                        "relative_difference": projected_difference,
                        "threshold": config.spatial_endpoint_relative_tolerance,
                        "pass": projected_pass,
                        "gating_role": "sidecar_only",
                    }
                    if projected_pass != passed:
                        projection_observable_differences.append(
                            f"{case_id}:{representation}:T128:D0:{metric}"
                        )
                comparisons.append(record)
                if not passed:
                    failures.append(
                        f"spatial:{case_id}:{representation}:T128:D0:{metric}"
                    )

    hotspot_records: list[dict[str, Any]] = []
    for representation in protocol.representations:
        values = [
            float(summaries[endpoint_key("ID-S1", representation, level)]["hotspot_x"])
            for level in ("S2", "S3", "S4")
        ]
        jump = abs(values[2] - values[1])
        threshold = config.length / protocol.spatial("S4").nx
        passed = jump <= threshold + 1.0e-12
        record = {
            "kind": "hotspot_spatial",
            "representation": representation,
            "solver_level": "D0",
            "steps_per_cycle": 128,
            "values_S2_S3_S4": values,
            "finest_two_absolute_jump": jump,
            "threshold_one_S4_cell": threshold,
            "pass": passed,
        }
        hotspot_records.append(record)
        comparisons.append(record)
        if not passed:
            failures.append(f"hotspot:{representation}:T128:D0")

    cycle_records: list[dict[str, Any]] = []
    for case_id in config.cases:
        for representation in protocol.representations:
            for spatial_label in ("S2", "S3", "S4"):
                key = endpoint_key(case_id, representation, spatial_label)
                value = float(summaries[key]["cycle_state_relative_difference"])
                passed = value <= config.cycle_state_relative_tolerance
                record = {
                    "endpoint": key,
                    "value": value,
                    "threshold": config.cycle_state_relative_tolerance,
                    "pass": passed,
                }
                cycle_records.append(record)
                if not passed:
                    failures.append(f"cycle:{key}")

    spatial_records = [record for record in comparisons if record["kind"] == "spatial"]
    counts = {
        "spatial": len(spatial_records),
        "hotspot": len(hotspot_records),
        "cycle": len(cycle_records),
        "spatial_pass": sum(record["pass"] for record in spatial_records),
        "hotspot_pass": sum(record["pass"] for record in hotspot_records),
        "cycle_pass": sum(record["pass"] for record in cycle_records),
    }
    count_pass = counts == {
        "spatial": protocol.expected_spatial_records,
        "hotspot": protocol.expected_hotspot_records,
        "cycle": protocol.expected_cycle_records,
        "spatial_pass": protocol.expected_spatial_records,
        "hotspot_pass": protocol.expected_hotspot_records,
        "cycle_pass": protocol.expected_cycle_records,
    }
    if not count_pass:
        failures.append("gate_record_count_or_pass_count")
    return {
        "schema": "paper2_m2a_v04_t128_numerical_gate_v01",
        "steps_per_cycle": protocol.steps_per_cycle,
        "solver_level": "D0",
        "decision_observable": "native_nodal_or_spring_traction",
        "pass": not failures,
        "failures": failures,
        "counts": counts,
        "projection_sidecar": {
            "role": "diagnostic_only_not_a_production_gate",
            "observable_conclusion_differences": projection_observable_differences,
        },
        "comparisons": comparisons,
        "cycle_records": cycle_records,
    }


def t64_t128_pair_audit(
    source_t64: dict[str, dict[str, Any]],
    target_t128: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V04
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for case_id in FROZEN_CONFIG.cases:
        for representation in protocol.representations:
            source_key = t64_endpoint_key(case_id, representation, "S4")
            target_key = endpoint_key(case_id, representation, "S4")
            if source_key not in source_t64 or target_key not in target_t128:
                failures.append(f"missing_pair:{source_key}:{target_key}")
                continue
            for metric in metrics_for_case(case_id):
                pair_key = (case_id, representation, metric)
                if pair_key in seen:
                    failures.append(f"duplicate_pair:{case_id}:{representation}:{metric}")
                    continue
                seen.add(pair_key)
                value_t64 = summary_metric(source_t64[source_key], metric)
                value_t128 = summary_metric(target_t128[target_key], metric)
                floor = metric_floor(metric)
                difference = relative_difference(value_t64, value_t128, floor)
                finite = bool(
                    np.isfinite(value_t64)
                    and np.isfinite(value_t128)
                    and np.isfinite(floor)
                    and np.isfinite(difference)
                )
                if not finite:
                    failures.append(f"nonfinite_pair:{case_id}:{representation}:{metric}")
                records.append(
                    {
                        "case_id": case_id,
                        "representation": representation,
                        "spatial_level": "S4",
                        "solver_level": "D0",
                        "metric": metric,
                        "source_endpoint": source_key,
                        "target_endpoint": target_key,
                        "T64_value": value_t64,
                        "T128_value": value_t128,
                        "floor": floor,
                        "relative_difference": difference,
                        "direction_pending_T256": True,
                        "finite": finite,
                    }
                )
    if len(records) != protocol.expected_time_pair_records:
        failures.append(
            f"record_count:{len(records)}!={protocol.expected_time_pair_records}"
        )
    return {
        "schema": "paper2_m2a_v04_t64_t128_pair_audit_v01",
        "label": "T64_T128_PAIR_AUDIT_ONLY",
        "record_count": len(records),
        "expected_record_count": protocol.expected_time_pair_records,
        "direction_assessment": "PENDING_T256",
        "numerical_threshold": None,
        "maximum_relative_difference": (
            max(record["relative_difference"] for record in records)
            if records
            else 0.0
        ),
        "failures": failures,
        "records": records,
        "pass": not failures,
        "evidence_boundary": (
            "This is a strict T64-to-T128 pair audit only. Two time levels cannot "
            "establish direction consistency or time convergence."
        ),
    }
