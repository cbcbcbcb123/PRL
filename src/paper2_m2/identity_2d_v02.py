"""Pure orchestration and gate logic for the M2A v02 T64 stage."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .config import FROZEN_CONFIG
from .interface_projection import (
    common_segment_space_time_l2,
    project_piecewise_linear_to_common_segments,
)
from .protocol_v02 import FROZEN_PROTOCOL_V02


DYNAMIC_HOLDOUT_CASES = ("ID-A2", "ID-LN", "ID-LS", "ID-C0", "ID-CQ", "ID-S1")
PRIMARY_METRICS = (
    "peak_limited_shortening",
    "shortening_waveform_l2",
    "myocardium_ecm_traction_l2",
    "endocardium_ecm_traction_l2",
    "total_dissipation",
)
TRACTION_METRICS = (
    "myocardium_ecm_traction_l2",
    "endocardium_ecm_traction_l2",
)


def endpoint_key(
    case_id: str,
    representation: str,
    spatial_label: str,
    tolerance_label: str,
) -> str:
    return "__".join(
        (
            case_id,
            representation,
            spatial_label,
            "T64",
            tolerance_label,
        )
    )


def summary_metric(summary: dict[str, Any], metric: str) -> float:
    if metric == "total_dissipation":
        ledger = summary["ledger"]
        return float(
            ledger["total_drag_dissipation"] + ledger["total_sls_dissipation"]
        )
    return float(summary[metric])


def relative_difference(value_a: float, value_b: float, floor: float) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def metric_floor(metric: str) -> float:
    if "shortening" in metric:
        return FROZEN_CONFIG.near_zero_shortening_absolute_scale
    if "traction" in metric:
        return FROZEN_CONFIG.near_zero_traction_absolute_scale
    return FROZEN_CONFIG.near_zero_energy_absolute_scale


def metrics_for_case(case_id: str) -> tuple[str, ...]:
    if case_id == "ID-P1":
        return ("passive_tangent",)
    if case_id == "ID-P0":
        return ("maximum_state_norm",)
    return PRIMARY_METRICS


def endpoint_structural_gate(summary: dict[str, Any]) -> dict[str, Any]:
    config = FROZEN_CONFIG
    checks = {
        "solver_residual": {
            "value": summary["solver"]["maximum_relative_residual"],
            "threshold": summary["solver"]["acceptance_tolerance"],
            "pass": summary["solver"]["pass"],
        },
        "interface_action_reaction": {
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
    }
    if summary["case_id"] == "ID-P0":
        checks["zero_state"] = {
            "value": summary["maximum_state_norm"],
            "threshold": config.zero_state_absolute_tolerance,
            "pass": summary["maximum_state_norm"] <= config.zero_state_absolute_tolerance,
        }
    if summary["case_id"] == "ID-P1":
        checks["uniform_strain_manufactured_solution"] = {
            "value": summary["manufactured_uniform_strain_relative_error"],
            "threshold": config.manufactured_solution_relative_tolerance,
            "pass": summary["manufactured_uniform_strain_relative_error"]
            <= config.manufactured_solution_relative_tolerance,
        }
    return {"pass": all(check["pass"] for check in checks.values()), "checks": checks}


def global_structural_checks(system: Any) -> dict[str, Any]:
    generator = np.random.default_rng(20260903)
    state = 1.0e-3 * generator.standard_normal(system.state_size)
    activation = 0.037
    step = 1.0e-7
    energy_plus = (
        0.5 * state @ (system.matrix_material @ state)
        + (activation + step) * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * (activation + step) ** 2
    )
    energy_minus = (
        0.5 * state @ (system.matrix_material @ state)
        + (activation - step) * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * (activation - step) ** 2
    )
    numerical_derivative = (energy_plus - energy_minus) / (2.0 * step)
    analytic_derivative = (
        np.dot(system.active_vector_h, state) + system.active_scalar_c * activation
    )
    derivative_error = relative_difference(
        float(numerical_derivative), float(analytic_derivative), 1.0e-12
    )
    return {
        "units": {
            "system": "nondimensional_M2A_identity_benchmark",
            "pass": True,
        },
        "normal_and_traction_sign": {
            "lumen_normal": "negative_y_from_lumen_toward_wall",
            "interface_traction": "positive_on_first_named_domain",
            "pass": True,
        },
        "active_power_derivative": {
            "analytic": float(analytic_derivative),
            "central_difference": float(numerical_derivative),
            "relative_error": derivative_error,
            "threshold": 1.0e-7,
            "pass": derivative_error <= 1.0e-7,
        },
        "ufl_manual_assembly": {
            "relative_error": system.manufactured_error,
            "threshold": FROZEN_CONFIG.manufactured_solution_relative_tolerance,
            "pass": system.manufactured_error
            <= FROZEN_CONFIG.manufactured_solution_relative_tolerance,
        },
    }


def _native_x(system: Any) -> np.ndarray:
    layer = system.myocardium_mesh
    return layer.dof_coordinates[layer.top_nodes, 0]


def _traction_field(endpoint: Any, key: str, nodes: int) -> np.ndarray:
    steps = FROZEN_PROTOCOL_V02.steps_per_cycle
    return endpoint.arrays[key].reshape(nodes, 2, -1)[:, :, :steps]


def common_projection_sidecar(system: Any, endpoint: Any) -> dict[str, Any]:
    if system.spatial_label not in ("S3", "S4"):
        return {
            "available": False,
            "reason": "S2 is coarser than the frozen 64-segment diagnostic grid",
        }
    common_x = np.linspace(
        -0.5 * FROZEN_CONFIG.length,
        0.5 * FROZEN_CONFIG.length,
        FROZEN_PROTOCOL_V02.common_projection_segments + 1,
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
            FROZEN_CONFIG.period / FROZEN_PROTOCOL_V02.steps_per_cycle,
        )
    return {
        "available": True,
        "role": "diagnostic_sidecar_not_production_gate",
        "common_segments": FROZEN_PROTOCOL_V02.common_projection_segments,
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


def t64_numerical_gate(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    protocol = FROZEN_PROTOCOL_V02
    config = FROZEN_CONFIG
    comparisons: list[dict[str, Any]] = []
    failures: list[str] = []
    projection_observable_differences: list[str] = []

    for case_id in config.cases:
        metrics = metrics_for_case(case_id)
        for representation in protocol.representations:
            for tolerance_label in protocol.tolerance_labels:
                level_values: dict[str, dict[str, float]] = {}
                for spatial_label in ("S2", "S3", "S4"):
                    key = endpoint_key(
                        case_id, representation, spatial_label, tolerance_label
                    )
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
                        "tolerance_label": tolerance_label,
                        "metric": metric,
                        "values_S2_S3_S4": values,
                        "finest_two_relative_difference": fine_difference,
                        "threshold": config.spatial_endpoint_relative_tolerance,
                        "direction_consistent": direction_consistent,
                        "production_observable": "native_nodal_or_spring",
                        "pass": passed,
                    }
                    if metric in TRACTION_METRICS:
                        key_s3 = endpoint_key(case_id, representation, "S3", tolerance_label)
                        key_s4 = endpoint_key(case_id, representation, "S4", tolerance_label)
                        projected_s3 = float(
                            summaries[key_s3]["v02_common_projection_sidecar"]["values"][metric]
                        )
                        projected_s4 = float(
                            summaries[key_s4]["v02_common_projection_sidecar"]["values"][metric]
                        )
                        projected_difference = relative_difference(
                            projected_s3, projected_s4, floor
                        )
                        projected_pass = (
                            projected_difference
                            <= config.spatial_endpoint_relative_tolerance
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
                                f"{case_id}:{representation}:{tolerance_label}:{metric}"
                            )
                    comparisons.append(record)
                    if not passed:
                        failures.append(
                            f"spatial:{case_id}:{representation}:{tolerance_label}:{metric}"
                        )

            for spatial_label in ("S2", "S3", "S4"):
                for metric in metrics:
                    values = [
                        summary_metric(
                            summaries[
                                endpoint_key(
                                    case_id,
                                    representation,
                                    spatial_label,
                                    tolerance_label,
                                )
                            ],
                            metric,
                        )
                        for tolerance_label in protocol.tolerance_labels
                    ]
                    difference = relative_difference(
                        values[0], values[1], metric_floor(metric)
                    )
                    passed = difference <= config.solver_profile_relative_tolerance
                    comparisons.append(
                        {
                            "kind": "C0_C1",
                            "case_id": case_id,
                            "representation": representation,
                            "spatial_label": spatial_label,
                            "metric": metric,
                            "values_C0_C1": values,
                            "relative_difference": difference,
                            "threshold": config.solver_profile_relative_tolerance,
                            "pass": passed,
                        }
                    )
                    if not passed:
                        failures.append(
                            f"C0_C1:{case_id}:{representation}:{spatial_label}:{metric}"
                        )

    hotspot_records: list[dict[str, Any]] = []
    for representation in protocol.representations:
        for tolerance_label in protocol.tolerance_labels:
            values = [
                float(
                    summaries[
                        endpoint_key("ID-S1", representation, level, tolerance_label)
                    ]["hotspot_x"]
                )
                for level in ("S2", "S3", "S4")
            ]
            jump = abs(values[2] - values[1])
            threshold = config.length / protocol.spatial("S4").nx
            passed = jump <= threshold + 1.0e-12
            record = {
                "kind": "hotspot_spatial",
                "representation": representation,
                "tolerance_label": tolerance_label,
                "values_S2_S3_S4": values,
                "finest_two_absolute_jump": jump,
                "threshold_one_S4_cell": threshold,
                "pass": passed,
            }
            hotspot_records.append(record)
            comparisons.append(record)
            if not passed:
                failures.append(f"hotspot:{representation}:{tolerance_label}")

    cycle_records: list[dict[str, Any]] = []
    for case_id in config.cases:
        for representation in protocol.representations:
            for spatial_label in ("S2", "S3", "S4"):
                for tolerance_label in protocol.tolerance_labels:
                    key = endpoint_key(
                        case_id, representation, spatial_label, tolerance_label
                    )
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
    tolerance_records = [record for record in comparisons if record["kind"] == "C0_C1"]
    return {
        "schema": "paper2_m2a_v02_t64_numerical_gate_v01",
        "steps_per_cycle": protocol.steps_per_cycle,
        "decision_observable": "native_nodal_or_spring_traction",
        "pass": not failures,
        "failures": failures,
        "counts": {
            "spatial": len(spatial_records),
            "C0_C1": len(tolerance_records),
            "hotspot": len(hotspot_records),
            "cycle": len(cycle_records),
            "spatial_pass": sum(record["pass"] for record in spatial_records),
            "C0_C1_pass": sum(record["pass"] for record in tolerance_records),
            "hotspot_pass": sum(record["pass"] for record in hotspot_records),
            "cycle_pass": sum(record["pass"] for record in cycle_records),
        },
        "projection_sidecar": {
            "role": "diagnostic_only_not_a_production_gate",
            "observable_conclusion_differences": projection_observable_differences,
        },
        "comparisons": comparisons,
        "cycle_records": cycle_records,
    }
