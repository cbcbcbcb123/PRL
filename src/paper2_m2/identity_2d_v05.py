"""T256 orchestration and three-level time gates for M2A v05."""

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
from .protocol_v05 import FROZEN_PROTOCOL_V05


def endpoint_key(case_id: str, representation: str, spatial_label: str) -> str:
    return "__".join((case_id, representation, spatial_label, "T256", "D0"))


def t128_endpoint_key(case_id: str, representation: str, spatial_label: str) -> str:
    return "__".join((case_id, representation, spatial_label, "T128", "D0"))


def t64_endpoint_key(case_id: str, representation: str, spatial_label: str) -> str:
    return "__".join((case_id, representation, spatial_label, "T64", "D0"))


def simulate_endpoint_v05(*, system: Any, case_id: str) -> Any:
    endpoint = simulate_endpoint_v03(
        system=system,
        case_id=case_id,
        steps_per_cycle=FROZEN_PROTOCOL_V05.steps_per_cycle,
    )
    endpoint.summary["stage_protocol"] = "paper2_m2a_protocol_v05"
    return endpoint


def endpoint_structural_gate(summary: dict[str, Any]) -> dict[str, Any]:
    gate = _endpoint_structural_gate_v03(summary)
    return {
        "schema": "paper2_m2a_v05_endpoint_structural_gate_v01",
        "pass": gate["pass"],
        "checks": gate["checks"],
    }


def _native_x(system: Any) -> np.ndarray:
    layer = system.myocardium_mesh
    return layer.dof_coordinates[layer.top_nodes, 0]


def _traction_field(endpoint: Any, key: str, nodes: int) -> np.ndarray:
    steps = FROZEN_PROTOCOL_V05.steps_per_cycle
    return endpoint.arrays[key].reshape(nodes, 2, -1)[:, :, :steps]


def common_projection_sidecar(system: Any, endpoint: Any) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V05
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


def t256_numerical_gate(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V05
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
                    "steps_per_cycle": 256,
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
                            "v05_common_projection_sidecar"
                        ]["values"][metric]
                    )
                    projected_s4 = float(
                        summaries[endpoint_key(case_id, representation, "S4")][
                            "v05_common_projection_sidecar"
                        ]["values"][metric]
                    )
                    projected_difference = relative_difference(
                        projected_s3, projected_s4, floor
                    )
                    projected_pass = bool(
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
                            f"{case_id}:{representation}:T256:D0:{metric}"
                        )
                comparisons.append(record)
                if not passed:
                    failures.append(
                        f"spatial:{case_id}:{representation}:T256:D0:{metric}"
                    )

    hotspot_records: list[dict[str, Any]] = []
    for representation in protocol.representations:
        values = [
            float(summaries[endpoint_key("ID-S1", representation, level)]["hotspot_x"])
            for level in ("S2", "S3", "S4")
        ]
        jump = abs(values[2] - values[1])
        threshold = config.length / protocol.spatial("S4").nx
        passed = bool(jump <= threshold + 1.0e-12)
        record = {
            "kind": "hotspot_spatial",
            "representation": representation,
            "solver_level": "D0",
            "steps_per_cycle": 256,
            "values_S2_S3_S4": values,
            "finest_two_absolute_jump": jump,
            "threshold_one_S4_cell": threshold,
            "pass": passed,
        }
        hotspot_records.append(record)
        comparisons.append(record)
        if not passed:
            failures.append(f"hotspot:{representation}:T256:D0")

    cycle_records: list[dict[str, Any]] = []
    for case_id in config.cases:
        for representation in protocol.representations:
            for spatial_label in ("S2", "S3", "S4"):
                key = endpoint_key(case_id, representation, spatial_label)
                value = float(summaries[key]["cycle_state_relative_difference"])
                passed = bool(value <= config.cycle_state_relative_tolerance)
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
    expected_counts = {
        "spatial": protocol.expected_spatial_records,
        "hotspot": protocol.expected_hotspot_records,
        "cycle": protocol.expected_cycle_records,
        "spatial_pass": protocol.expected_spatial_records,
        "hotspot_pass": protocol.expected_hotspot_records,
        "cycle_pass": protocol.expected_cycle_records,
    }
    if counts != expected_counts:
        failures.append("gate_record_count_or_pass_count")
    return {
        "schema": "paper2_m2a_v05_t256_numerical_gate_v01",
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


def evaluate_three_level_time_record(
    value_t64: float,
    value_t128: float,
    value_t256: float,
    floor: float,
) -> dict[str, Any]:
    values = np.asarray([value_t64, value_t128, value_t256, floor], dtype=float)
    finite = bool(np.all(np.isfinite(values)))
    if not finite:
        return {
            "T64_value": float(value_t64) if np.isfinite(value_t64) else None,
            "T128_value": float(value_t128) if np.isfinite(value_t128) else None,
            "T256_value": float(value_t256) if np.isfinite(value_t256) else None,
            "floor": float(floor) if np.isfinite(floor) else None,
            "delta_01": None,
            "delta_12": None,
            "r_01": None,
            "r_12": None,
            "one_percent_scale": None,
            "finite": False,
            "finest_relative_pass": False,
            "direction_same_or_both_small": False,
            "change_nonincreasing": False,
            "pass": False,
        }

    value_t64 = float(value_t64)
    value_t128 = float(value_t128)
    value_t256 = float(value_t256)
    floor = float(floor)
    delta_01 = value_t128 - value_t64
    delta_12 = value_t256 - value_t128
    r_01 = abs(delta_01) / max(abs(value_t64), abs(value_t128), floor)
    r_12 = abs(delta_12) / max(abs(value_t128), abs(value_t256), floor)
    one_percent_scale = FROZEN_PROTOCOL_V05.time_fine_relative_tolerance * max(
        abs(value_t64), abs(value_t128), abs(value_t256), floor
    )
    finest_relative_pass = bool(
        r_12 <= FROZEN_PROTOCOL_V05.time_fine_relative_tolerance
    )
    direction_same_or_both_small = bool(
        delta_01 * delta_12 >= 0.0
        or (
            abs(delta_01) <= one_percent_scale
            and abs(delta_12) <= one_percent_scale
        )
    )
    change_nonincreasing = bool(abs(delta_12) <= abs(delta_01) + floor)
    passed = bool(
        finest_relative_pass
        and direction_same_or_both_small
        and change_nonincreasing
    )
    return {
        "T64_value": value_t64,
        "T128_value": value_t128,
        "T256_value": value_t256,
        "floor": floor,
        "delta_01": delta_01,
        "delta_12": delta_12,
        "r_01": r_01,
        "r_12": r_12,
        "one_percent_scale": one_percent_scale,
        "finite": True,
        "finest_relative_pass": finest_relative_pass,
        "direction_same_or_both_small": direction_same_or_both_small,
        "change_nonincreasing": change_nonincreasing,
        "pass": passed,
    }


def three_level_time_gate(
    source_t64: dict[str, dict[str, Any]],
    source_t128: dict[str, dict[str, Any]],
    target_t256: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V05
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for case_id in FROZEN_CONFIG.cases:
        for representation in protocol.representations:
            key_t64 = t64_endpoint_key(case_id, representation, "S4")
            key_t128 = t128_endpoint_key(case_id, representation, "S4")
            key_t256 = endpoint_key(case_id, representation, "S4")
            if (
                key_t64 not in source_t64
                or key_t128 not in source_t128
                or key_t256 not in target_t256
            ):
                failures.append(f"missing_triplet:{key_t64}:{key_t128}:{key_t256}")
                continue
            for metric in metrics_for_case(case_id):
                record_key = (case_id, representation, metric)
                if record_key in seen:
                    failures.append(f"duplicate_triplet:{case_id}:{representation}:{metric}")
                    continue
                seen.add(record_key)
                values = evaluate_three_level_time_record(
                    summary_metric(source_t64[key_t64], metric),
                    summary_metric(source_t128[key_t128], metric),
                    summary_metric(target_t256[key_t256], metric),
                    metric_floor(metric),
                )
                record = {
                    "case_id": case_id,
                    "representation": representation,
                    "spatial_level": "S4",
                    "solver_level": "D0",
                    "metric": metric,
                    "T64_endpoint": key_t64,
                    "T128_endpoint": key_t128,
                    "T256_endpoint": key_t256,
                    "finest_relative_threshold": (
                        protocol.time_fine_relative_tolerance
                    ),
                    **values,
                }
                records.append(record)
                if not record["pass"]:
                    failures.append(f"time:{case_id}:{representation}:{metric}")

    if len(records) != protocol.expected_three_level_time_records:
        failures.append(
            f"record_count:{len(records)}!={protocol.expected_three_level_time_records}"
        )
    maximum_r12_record = (
        max(records, key=lambda record: record["r_12"] or -1.0) if records else None
    )
    maximum_change_ratio_record = None
    finite_records = [
        record
        for record in records
        if record["finite"] and abs(record["delta_01"]) + record["floor"] > 0.0
    ]
    if finite_records:
        maximum_change_ratio_record = max(
            finite_records,
            key=lambda record: abs(record["delta_12"])
            / (abs(record["delta_01"]) + record["floor"]),
        )
    return {
        "schema": "paper2_m2a_v05_three_level_time_gate_v01",
        "label": (
            "THREE_LEVEL_TIME_GATE_PASS"
            if not failures
            else "THREE_LEVEL_TIME_GATE_FAIL"
        ),
        "record_count": len(records),
        "expected_record_count": protocol.expected_three_level_time_records,
        "source_levels": ["T64", "T128"],
        "target_level": "T256",
        "finest_relative_threshold": protocol.time_fine_relative_tolerance,
        "convergence_order_fitted": False,
        "maximum_r12_record": maximum_r12_record,
        "maximum_change_ratio_record": maximum_change_ratio_record,
        "failures": failures,
        "records": records,
        "pass": not failures,
        "evidence_boundary": (
            "This gate checks only preregistered scalar observables at T64/T128/T256. "
            "It does not fit a convergence order or establish DCM-FEM identity."
        ),
    }


def time_nodes_nested(source_t128: np.ndarray, target_t256: np.ndarray) -> dict[str, Any]:
    source = np.asarray(source_t128, dtype=float)
    target = np.asarray(target_t256, dtype=float)
    finite = bool(np.all(np.isfinite(source)) and np.all(np.isfinite(target)))
    shape_pass = bool(
        source.ndim == 1
        and target.ndim == 1
        and target.size == 2 * (source.size - 1) + 1
    )
    maximum_absolute_error = None
    nested = False
    if finite and shape_pass:
        maximum_absolute_error = float(np.max(np.abs(target[::2] - source)))
        nested = bool(maximum_absolute_error <= 1.0e-15)
    return {
        "source_T128_nodes": int(source.size),
        "target_T256_nodes": int(target.size),
        "expected_target_nodes": int(2 * (source.size - 1) + 1),
        "finite": finite,
        "shape_pass": shape_pass,
        "maximum_absolute_error": maximum_absolute_error,
        "absolute_tolerance": 1.0e-15,
        "pass": bool(finite and shape_pass and nested),
    }

