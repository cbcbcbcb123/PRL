"""Read-only identity post-processing for the frozen Paper 2 M2A v06 gate."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .interface_projection import (
    common_segment_space_time_l2,
    project_piecewise_linear_to_common_segments,
)
from .protocol_v06 import FROZEN_PROTOCOL_V06, IdentityGateProtocolV06


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_tree(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(item) for item in value)
    return True


def endpoint_key(
    case_id: str,
    representation: str,
    spatial_level: str,
    steps_per_cycle: int,
) -> str:
    return "__".join(
        (case_id, representation, spatial_level, f"T{steps_per_cycle}", "D0")
    )


def summary_metric(summary: dict[str, Any], metric: str) -> float:
    if metric == "total_dissipation":
        ledger = summary["ledger"]
        return float(
            ledger["total_drag_dissipation"] + ledger["total_sls_dissipation"]
        )
    if metric == "cycle_stored_energy_change_near_zero":
        return float(summary["ledger"]["cycle_energy_change"])
    return float(summary[metric])


def relative_difference(value_a: float, value_b: float, floor: float) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def first_cycle(values: np.ndarray, steps_per_cycle: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.shape[-1] < steps_per_cycle + 1:
        raise ValueError("dynamic array does not contain one complete cycle plus endpoint")
    return values[..., :steps_per_cycle]


def fundamental(signal: np.ndarray) -> complex:
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("fundamental requires a one-dimensional sampled cycle")
    centered = values - np.mean(values)
    return complex(np.fft.rfft(centered)[1])


def fundamental_amplitude(signal: np.ndarray) -> float:
    values = np.asarray(signal, dtype=np.float64)
    return float(2.0 * abs(fundamental(values)) / values.size)


def wrapped_phase_difference(harmonic_a: complex, harmonic_b: complex) -> float:
    return abs(float(np.angle(np.exp(1j * (np.angle(harmonic_a) - np.angle(harmonic_b))))))


def normalized_l2_difference(
    value_a: np.ndarray,
    value_b: np.ndarray,
    floor: float,
) -> float:
    value_a = np.asarray(value_a, dtype=np.float64)
    value_b = np.asarray(value_b, dtype=np.float64)
    if value_a.shape != value_b.shape:
        raise ValueError("normalized L2 inputs must have identical shapes")
    return float(
        np.linalg.norm(value_a - value_b)
        / max(np.linalg.norm(value_a), np.linalg.norm(value_b), floor)
    )


def project_traction_first_cycle(
    raw_traction: np.ndarray,
    steps_per_cycle: int,
    common_segments: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw_traction, dtype=np.float64)
    native_nodes = 129
    if raw.ndim == 2 and raw.shape[0] == 2 * native_nodes:
        if raw.shape[1] < steps_per_cycle + 1:
            raise ValueError("traction array is shorter than the requested cycle")
        nodal = raw[:, :steps_per_cycle].reshape(native_nodes, 2, steps_per_cycle)
    elif raw.ndim == 3 and raw.shape[:2] == (native_nodes, 2):
        if raw.shape[-1] < steps_per_cycle:
            raise ValueError("traction array is shorter than the requested cycle")
        nodal = raw[..., :steps_per_cycle]
    else:
        raise ValueError("traction must interpret exactly as (129, 2, time)")
    native_x = np.linspace(-0.5, 0.5, native_nodes)
    common_x = np.linspace(-0.5, 0.5, common_segments + 1)
    projected = project_piecewise_linear_to_common_segments(
        native_x, nodal, common_x
    )
    return common_x, projected


def projected_traction_difference(
    common_x: np.ndarray,
    projected_a: np.ndarray,
    projected_b: np.ndarray,
    time_step: float,
    floor: float,
) -> float:
    difference_norm = common_segment_space_time_l2(
        common_x, projected_a - projected_b, time_step
    )
    norm_a = common_segment_space_time_l2(common_x, projected_a, time_step)
    norm_b = common_segment_space_time_l2(common_x, projected_b, time_step)
    return float(difference_norm / max(norm_a, norm_b, floor))


def response_signal(case_id: str, observations: dict[str, Any]) -> np.ndarray:
    if case_id == "ID-LN":
        return -np.asarray(observations["mean_endocardial_normal_displacement"])
    if case_id == "ID-LS":
        return np.asarray(observations["mean_endocardial_tangential_displacement"])
    return np.asarray(observations["limited_shortening"])


def combined_load_gain(
    combined_shortening: np.ndarray,
    active_shortening: np.ndarray,
    normal_shortening: np.ndarray,
    floor: float,
) -> dict[str, float]:
    """Reuse the frozen v01 lines 545--568 combined-load gain exactly."""

    combined_amplitude = fundamental_amplitude(combined_shortening)
    active_amplitude = fundamental_amplitude(active_shortening)
    normal_amplitude = fundamental_amplitude(normal_shortening)
    denominator = max(active_amplitude + normal_amplitude, floor)
    return {
        "combined_amplitude": combined_amplitude,
        "active_ID_A2_amplitude": active_amplitude,
        "normal_ID_LN_amplitude": normal_amplitude,
        "denominator": denominator,
        "gain": combined_amplitude / denominator,
    }


def _severity_for_relative(
    difference: float,
    formal_threshold: float,
    no_go_threshold: float,
) -> str:
    if not math.isfinite(difference):
        return "no_go"
    if difference <= formal_threshold:
        return "pass"
    if difference <= no_go_threshold:
        return "maybe"
    return "no_go"


def scalar_gate_record(
    *,
    case_id: str,
    metric: str,
    dcm: float,
    fem: float,
    floor: float,
    threshold: float,
    no_go_threshold: float,
) -> dict[str, Any]:
    finite = bool(math.isfinite(dcm) and math.isfinite(fem))
    absolute_difference = abs(dcm - fem) if finite else None
    both_near_zero = bool(finite and abs(dcm) <= floor and abs(fem) <= floor)
    if not finite:
        relative = None
        passed = False
        severity = "no_go"
    elif both_near_zero:
        relative = None
        passed = bool(absolute_difference <= floor)
        severity = "pass" if passed else "no_go"
    else:
        relative = relative_difference(dcm, fem, floor)
        severity = _severity_for_relative(relative, threshold, no_go_threshold)
        passed = severity == "pass"
    return {
        "case_id": case_id,
        "metric": metric,
        "dcm": dcm if math.isfinite(dcm) else None,
        "fem": fem if math.isfinite(fem) else None,
        "absolute_difference": absolute_difference,
        "relative_difference": relative,
        "floor": floor,
        "near_zero_absolute_rule_applied": both_near_zero,
        "threshold": threshold,
        "pass": passed,
        "severity": severity,
    }


def relative_gate_record(
    *,
    case_id: str,
    metric: str,
    difference: float,
    threshold: float,
    no_go_threshold: float,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    severity = _severity_for_relative(difference, threshold, no_go_threshold)
    return {
        "case_id": case_id,
        "metric": metric,
        "relative_difference": difference if math.isfinite(difference) else None,
        "threshold": threshold,
        "pass": severity == "pass",
        "severity": severity,
        **(details or {}),
    }


def phase_gate_record(
    *,
    case_id: str,
    signal_name: str,
    signal_dcm: np.ndarray,
    signal_fem: np.ndarray,
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    harmonic_dcm = fundamental(signal_dcm)
    harmonic_fem = fundamental(signal_fem)
    amplitude_dcm = fundamental_amplitude(signal_dcm)
    amplitude_fem = fundamental_amplitude(signal_fem)
    applicable = bool(
        amplitude_dcm > protocol.coherence_amplitude_floor
        and amplitude_fem > protocol.coherence_amplitude_floor
    )
    phase_difference = (
        wrapped_phase_difference(harmonic_dcm, harmonic_fem) if applicable else None
    )
    severity = (
        _severity_for_relative(
            float(phase_difference),
            protocol.phase_absolute_tolerance_rad,
            protocol.no_go_phase_threshold_rad,
        )
        if applicable
        else "pass"
    )
    return {
        "case_id": case_id,
        "metric": "fundamental_phase",
        "signal": signal_name,
        "amplitude_dcm": amplitude_dcm,
        "amplitude_fem": amplitude_fem,
        "amplitude_floor": protocol.coherence_amplitude_floor,
        "applicable": applicable,
        "absolute_phase_difference_rad": phase_difference,
        "threshold_rad": protocol.phase_absolute_tolerance_rad,
        "pass": severity == "pass",
        "severity": severity,
    }


def hotspot_descriptor(
    projected_traction: np.ndarray,
    activation: np.ndarray,
    common_x: np.ndarray,
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    traction = np.asarray(projected_traction, dtype=np.float64)
    activation = np.asarray(activation, dtype=np.float64)
    if traction.shape != (protocol.common_projection_segments, 2, protocol.steps_per_cycle):
        raise ValueError("hotspot traction has the wrong common-grid shape")
    if activation.shape != (protocol.steps_per_cycle,):
        raise ValueError("hotspot activation has the wrong first-cycle shape")
    peak_time_index = int(np.argmax(activation))
    fibre_values = traction[:, 0, peak_time_index]
    maximum = float(np.max(fibre_values))
    equivalent = np.isclose(
        fibre_values,
        maximum,
        rtol=protocol.hotspot_equivalence_relative_tolerance,
        atol=protocol.hotspot_equivalence_absolute_tolerance,
    )
    if bool(np.all(equivalent)):
        connected_components = 1
    else:
        connected_components = int(
            sum(
                bool(equivalent[index] and not equivalent[(index - 1) % equivalent.size])
                for index in range(equivalent.size)
            )
        )
    maximum_index = int(np.argmax(fibre_values))
    segment_centers = 0.5 * (common_x[:-1] + common_x[1:])
    return {
        "peak_time_index": peak_time_index,
        "center": float(segment_centers[maximum_index]),
        "maximum_signed_fibre_traction": maximum,
        "equivalent_peak_segment_indices": np.flatnonzero(equivalent).tolist(),
        "equivalent_peak_connected_components": connected_components,
        "split": connected_components > 1,
        "operator": "maximum_signed_fibre_traction_on_64_common_segments",
    }


def hotspot_gate_record(
    dcm: dict[str, Any],
    fem: dict[str, Any],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    difference = abs(float(dcm["center"]) - float(fem["center"]))
    split = bool(dcm["split"] or fem["split"])
    passed = bool(
        difference
        <= protocol.hotspot_center_tolerance
        + protocol.hotspot_equivalence_absolute_tolerance
        and not split
    )
    return {
        "case_id": "ID-S1",
        "metric": "common_grid_hotspot_center_and_split",
        "dcm": dcm,
        "fem": fem,
        "absolute_center_difference": difference,
        "threshold_one_finest_common_cell": protocol.hotspot_center_tolerance,
        "unexplained_split_present": split,
        "pass": passed,
        "severity": "pass" if passed else "no_go",
    }


def classify_identity_records(
    records: list[dict[str, Any]],
    *,
    preconditions_complete: bool,
) -> str:
    if not preconditions_complete:
        return "BLOCKED"
    severities = [record.get("severity", "no_go") for record in records]
    if any(severity == "no_go" for severity in severities):
        return "NO-GO-ID"
    if any(severity == "maybe" for severity in severities):
        return "MAYBE-ID"
    return "GO-ID"


def load_dynamic_observations(
    path: Path,
    *,
    case_id: str,
    steps_per_cycle: int,
    include_fields: bool,
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        time = first_cycle(archive["time_two_cycles"], steps_per_cycle)
        activation = first_cycle(archive["activation_two_cycles"], steps_per_cycle)
        shortening = first_cycle(
            archive["limited_shortening_two_cycles"], steps_per_cycle
        )
        tangential = first_cycle(
            archive["mean_endocardial_tangential_displacement_two_cycles"],
            steps_per_cycle,
        )
        normal = first_cycle(
            archive["mean_endocardial_normal_displacement_two_cycles"],
            steps_per_cycle,
        )
        common_x, myocardium_traction = project_traction_first_cycle(
            archive["myocardium_ecm_traction_two_cycles"],
            steps_per_cycle,
            protocol.common_projection_segments,
        )
        endocardium_common_x, endocardium_traction = project_traction_first_cycle(
            archive["endocardium_ecm_traction_two_cycles"],
            steps_per_cycle,
            protocol.common_projection_segments,
        )
        if not np.array_equal(common_x, endocardium_common_x):
            raise ValueError("the two interfaces did not use the same common grid")
        fields = {}
        if include_fields:
            for field_name in (
                "ecm_cell_centroids",
                "ecm_strain_at_peak",
                "ecm_internal_z_at_peak",
                "ecm_stress_at_peak",
            ):
                fields[field_name] = np.asarray(archive[field_name], dtype=np.float64)
    arrays = {
        "time": time,
        "activation": activation,
        "limited_shortening": shortening,
        "mean_endocardial_tangential_displacement": tangential,
        "mean_endocardial_normal_displacement": normal,
        "common_x": common_x,
        "myocardium_ecm_common_traction": myocardium_traction,
        "endocardium_ecm_common_traction": endocardium_traction,
        "fields": fields,
    }
    numeric_arrays = [
        time,
        activation,
        shortening,
        tangential,
        normal,
        myocardium_traction,
        endocardium_traction,
        *fields.values(),
    ]
    if not all(np.all(np.isfinite(array)) for array in numeric_arrays):
        raise ValueError(f"non-finite dynamic observation in {path}")
    if time.size != steps_per_cycle or not np.all(np.diff(time) > 0.0):
        raise ValueError(f"invalid first-cycle time grid in {path}")
    return arrays


def evaluate_identity_gate(
    *,
    summaries_t256: dict[str, dict[str, Any]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    records_by_case: dict[str, list[dict[str, Any]]] = {
        case_id: [] for case_id in protocol.holdout_cases
    }
    for case_id in protocol.holdout_cases:
        summary_dcm = summaries_t256[
            endpoint_key(case_id, "DCM", protocol.spatial_level, protocol.steps_per_cycle)
        ]
        summary_fem = summaries_t256[
            endpoint_key(case_id, "FEM", protocol.spatial_level, protocol.steps_per_cycle)
        ]
        obs_dcm = observations_t256[case_id]["DCM"]
        obs_fem = observations_t256[case_id]["FEM"]
        records = records_by_case[case_id]
        records.append(
            scalar_gate_record(
                case_id=case_id,
                metric="peak_limited_shortening",
                dcm=summary_metric(summary_dcm, "peak_limited_shortening"),
                fem=summary_metric(summary_fem, "peak_limited_shortening"),
                floor=protocol.shortening_floor,
                threshold=protocol.shortening_relative_tolerance,
                no_go_threshold=protocol.no_go_relative_threshold,
            )
        )
        records.append(
            relative_gate_record(
                case_id=case_id,
                metric="shortening_waveform_normalized_L2",
                difference=normalized_l2_difference(
                    obs_dcm["limited_shortening"],
                    obs_fem["limited_shortening"],
                    protocol.coherence_amplitude_floor,
                ),
                threshold=protocol.waveform_relative_tolerance,
                no_go_threshold=protocol.no_go_relative_threshold,
                details={
                    "window": [0, protocol.steps_per_cycle],
                    "repeated_cycle_endpoint_included": False,
                },
            )
        )
        time_step = float(obs_dcm["time"][1] - obs_dcm["time"][0])
        for metric, key in (
            (
                "myocardium_ecm_common_traction_normalized_L2",
                "myocardium_ecm_common_traction",
            ),
            (
                "endocardium_ecm_common_traction_normalized_L2",
                "endocardium_ecm_common_traction",
            ),
        ):
            records.append(
                relative_gate_record(
                    case_id=case_id,
                    metric=metric,
                    difference=projected_traction_difference(
                        obs_dcm["common_x"],
                        obs_dcm[key],
                        obs_fem[key],
                        time_step,
                        protocol.traction_floor,
                    ),
                    threshold=protocol.traction_relative_tolerance,
                    no_go_threshold=protocol.no_go_relative_threshold,
                    details={
                        "common_segments": protocol.common_projection_segments,
                        "interface": (
                            "myocardium_ecm" if key.startswith("myocardium") else "endocardium_ecm"
                        ),
                        "operator": "conservative_P1_to_P0_then_arc_length_weighted_space_time_L2",
                    },
                )
            )
        records.append(
            phase_gate_record(
                case_id=case_id,
                signal_name=protocol.phase_signal(case_id),
                signal_dcm=response_signal(case_id, obs_dcm),
                signal_fem=response_signal(case_id, obs_fem),
                protocol=protocol,
            )
        )
        records.append(
            scalar_gate_record(
                case_id=case_id,
                metric="total_dissipation",
                dcm=summary_metric(summary_dcm, "total_dissipation"),
                fem=summary_metric(summary_fem, "total_dissipation"),
                floor=protocol.energy_floor,
                threshold=protocol.dissipation_relative_tolerance,
                no_go_threshold=protocol.no_go_relative_threshold,
            )
        )
        stored_dcm = summary_metric(
            summary_dcm, "cycle_stored_energy_change_near_zero"
        )
        stored_fem = summary_metric(
            summary_fem, "cycle_stored_energy_change_near_zero"
        )
        stored_difference = abs(stored_dcm - stored_fem)
        storage_pass = bool(stored_difference <= protocol.storage_absolute_tolerance)
        records.append(
            {
                "case_id": case_id,
                "metric": "cycle_stored_energy_change_near_zero",
                "dcm": stored_dcm,
                "fem": stored_fem,
                "absolute_difference": stored_difference,
                "absolute_threshold": protocol.storage_absolute_tolerance,
                "pass": storage_pass,
                "severity": "pass" if storage_pass else "no_go",
                "operator_provenance": "frozen_v01_cycle_energy_change",
            }
        )

    for combined_case in ("ID-C0", "ID-CQ"):
        gains: dict[str, dict[str, float]] = {}
        for representation in protocol.representations:
            gains[representation] = combined_load_gain(
                observations_t256[combined_case][representation]["limited_shortening"],
                observations_t256["ID-A2"][representation]["limited_shortening"],
                observations_t256["ID-LN"][representation]["limited_shortening"],
                protocol.shortening_floor,
            )
        difference = relative_difference(
            gains["DCM"]["gain"], gains["FEM"]["gain"], protocol.shortening_floor
        )
        records_by_case[combined_case].append(
            relative_gate_record(
                case_id=combined_case,
                metric="combined_load_gain",
                difference=difference,
                threshold=protocol.combined_gain_relative_tolerance,
                no_go_threshold=protocol.no_go_relative_threshold,
                details={
                    "dcm": gains["DCM"],
                    "fem": gains["FEM"],
                    "operator": (
                        "amplitude(combined)/max(amplitude(ID-A2)+"
                        "amplitude(ID-LN),shortening_floor)"
                    ),
                    "operator_source": protocol.combined_gain_operator_source,
                    "operator_source_sha256": (
                        protocol.combined_gain_operator_source_sha256
                    ),
                    "post_hoc_metric_selection": False,
                },
            )
        )

    common_x = observations_t256["ID-S1"]["DCM"]["common_x"]
    hotspot_dcm = hotspot_descriptor(
        observations_t256["ID-S1"]["DCM"]["myocardium_ecm_common_traction"],
        observations_t256["ID-S1"]["DCM"]["activation"],
        common_x,
        protocol,
    )
    hotspot_fem = hotspot_descriptor(
        observations_t256["ID-S1"]["FEM"]["myocardium_ecm_common_traction"],
        observations_t256["ID-S1"]["FEM"]["activation"],
        common_x,
        protocol,
    )
    records_by_case["ID-S1"].append(
        hotspot_gate_record(hotspot_dcm, hotspot_fem, protocol)
    )

    all_records = [
        record
        for case_id in protocol.holdout_cases
        for record in records_by_case[case_id]
    ]
    decision = classify_identity_records(all_records, preconditions_complete=True)
    cases: dict[str, Any] = {}
    for case_id, records in records_by_case.items():
        cases[case_id] = {
            "formal_identity_case": True,
            "record_count": len(records),
            "all_formal_gates_pass": all(record["pass"] for record in records),
            "no_go_metrics": [
                record["metric"] for record in records if record["severity"] == "no_go"
            ],
            "maybe_metrics": [
                record["metric"] for record in records if record["severity"] == "maybe"
            ],
            "records": records,
        }
    return {
        "schema": "paper2_m2a_identity_gate_by_case_v06",
        "decision": decision,
        "formal_holdout_cases": list(protocol.holdout_cases),
        "formal_record_count": len(all_records),
        "all_formal_identity_thresholds_pass": all(
            record["pass"] for record in all_records
        ),
        "transferable_cases": [
            case_id for case_id, value in cases.items() if value["all_formal_gates_pass"]
        ],
        "nontransferable_cases": [
            case_id for case_id, value in cases.items() if not value["all_formal_gates_pass"]
        ],
        "no_go_failures": [
            f"identity:{record['case_id']}:{record['metric']}"
            for record in all_records
            if record["severity"] == "no_go"
        ],
        "maybe_flags": [
            f"identity:{record['case_id']}:{record['metric']}"
            for record in all_records
            if record["severity"] == "maybe"
        ],
        "cases": cases,
        "evidence_boundary": (
            "Identity is evaluated only for the six preregistered holdouts in the "
            "frozen idealized 2D S4/T256/D0 benchmark."
        ),
    }


def field_diagnostics_audit_only(
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    cases: dict[str, Any] = {}
    for case_id in protocol.holdout_cases:
        fields_dcm = observations_t256[case_id]["DCM"]["fields"]
        fields_fem = observations_t256[case_id]["FEM"]["fields"]
        case_records: dict[str, Any] = {}
        centroid_difference = float(
            np.max(
                np.abs(
                    fields_dcm["ecm_cell_centroids"]
                    - fields_fem["ecm_cell_centroids"]
                )
            )
        )
        case_records["ecm_cell_centroids"] = {
            "maximum_absolute_difference": centroid_difference,
            "shape": list(fields_dcm["ecm_cell_centroids"].shape),
            "role": "geometry_consistency_audit_only",
        }
        for field_name in (
            "ecm_strain_at_peak",
            "ecm_internal_z_at_peak",
            "ecm_stress_at_peak",
        ):
            dcm = fields_dcm[field_name]
            fem = fields_fem[field_name]
            case_records[field_name] = {
                "shape_dcm": list(dcm.shape),
                "shape_fem": list(fem.shape),
                "dcm_l2": float(np.linalg.norm(dcm)),
                "fem_l2": float(np.linalg.norm(fem)),
                "cross_representation_normalized_l2": normalized_l2_difference(
                    dcm, fem, protocol.energy_floor
                ),
                "threshold": None,
                "gating_role": "audit_only_no_preregistered_identity_threshold",
            }
        cases[case_id] = case_records
    return {
        "schema": "paper2_m2a_v06_field_diagnostics_audit_only",
        "identity_gate_applied": False,
        "cases": cases,
    }


def calibration_audit_only(
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for case_id, metric in (
        ("ID-P1", "passive_tangent"),
        ("ID-A1", "total_active_work"),
    ):
        values: dict[str, float] = {}
        for representation in protocol.representations:
            summary = summaries_t256[
                endpoint_key(
                    case_id,
                    representation,
                    protocol.spatial_level,
                    protocol.steps_per_cycle,
                )
            ]
            values[representation] = (
                float(summary["ledger"]["total_active_work"])
                if metric == "total_active_work"
                else float(summary[metric])
            )
        records.append(
            {
                "case_id": case_id,
                "metric": metric,
                "dcm": values["DCM"],
                "fem": values["FEM"],
                "absolute_difference": abs(values["DCM"] - values["FEM"]),
                "relative_difference": relative_difference(
                    values["DCM"], values["FEM"], protocol.energy_floor
                ),
                "gating_role": "calibration_audit_only_not_identity_evidence",
                "pass": None,
            }
        )
    return {
        "schema": "paper2_m2a_v06_calibration_audit_only",
        "identity_gate_applied": False,
        "cases": list(protocol.calibration_audit_only_cases),
        "records": records,
    }


def structural_control_audit(
    summaries_t256: dict[str, dict[str, Any]],
    structural_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for representation in protocol.representations:
        key = endpoint_key(
            "ID-P0", representation, protocol.spatial_level, protocol.steps_per_cycle
        )
        records.append(
            {
                "endpoint": key,
                "maximum_state_norm": float(summaries_t256[key]["maximum_state_norm"]),
                "source_structural_gate_pass": bool(structural_t256[key]["pass"]),
            }
        )
    return {
        "case_id": "ID-P0",
        "identity_evidence": False,
        "records": records,
        "pass": all(record["source_structural_gate_pass"] for record in records),
    }


def _fine_on_coarse(fine: np.ndarray, coarse_size: int) -> np.ndarray:
    fine = np.asarray(fine, dtype=np.float64)
    if fine.shape[-1] != 2 * coarse_size:
        raise ValueError("fine first-cycle samples do not nest the coarse cycle")
    return fine[..., ::2]


def _scalar_envelope(
    *,
    case_id: str,
    metric: str,
    summaries_t128: dict[str, dict[str, Any]],
    summaries_t256: dict[str, dict[str, Any]],
    floor: float,
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        value_s3_t256 = summary_metric(
            summaries_t256[endpoint_key(case_id, representation, "S3", 256)], metric
        )
        value_s4_t256 = summary_metric(
            summaries_t256[endpoint_key(case_id, representation, "S4", 256)], metric
        )
        value_s4_t128 = summary_metric(
            summaries_t128[endpoint_key(case_id, representation, "S4", 128)], metric
        )
        spatial_absolute = abs(value_s4_t256 - value_s3_t256)
        temporal_absolute = abs(value_s4_t256 - value_s4_t128)
        arms[representation] = {
            "S3_T256": value_s3_t256,
            "S4_T256": value_s4_t256,
            "S4_T128": value_s4_t128,
            "spatial_absolute_change": spatial_absolute,
            "temporal_absolute_change": temporal_absolute,
            "absolute_change_sum": spatial_absolute + temporal_absolute,
            "spatial_relative_change": relative_difference(
                value_s3_t256, value_s4_t256, floor
            ),
            "temporal_relative_change": relative_difference(
                value_s4_t128, value_s4_t256, floor
            ),
        }
        arms[representation]["relative_change_sum"] = (
            arms[representation]["spatial_relative_change"]
            + arms[representation]["temporal_relative_change"]
        )
    return {
        "metric": metric,
        "by_representation": arms,
        "combined_absolute_envelope": sum(
            arm["absolute_change_sum"] for arm in arms.values()
        ),
        "combined_relative_envelope": sum(
            arm["relative_change_sum"] for arm in arms.values()
        ),
        "subtracted_from_identity_difference": False,
    }


def _waveform_envelope(
    *,
    case_id: str,
    observations_t128: dict[str, dict[str, dict[str, Any]]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        coarse = observations_t128[case_id][representation]["limited_shortening"]
        fine = observations_t256[case_id][representation]["limited_shortening"]
        temporal = normalized_l2_difference(
            coarse,
            _fine_on_coarse(fine, coarse.size),
            protocol.coherence_amplitude_floor,
        )
        value_s3 = summary_metric(
            summaries_t256[endpoint_key(case_id, representation, "S3", 256)],
            "shortening_waveform_l2",
        )
        value_s4 = summary_metric(
            summaries_t256[endpoint_key(case_id, representation, "S4", 256)],
            "shortening_waveform_l2",
        )
        spatial = relative_difference(
            value_s3, value_s4, protocol.shortening_floor
        )
        arms[representation] = {
            "temporal_T128_to_T256_normalized_L2": temporal,
            "spatial_S3_to_S4_scalar_proxy_relative": spatial,
            "relative_change_sum": temporal + spatial,
        }
    return {
        "metric": "shortening_waveform_normalized_L2",
        "by_representation": arms,
        "combined_relative_envelope": sum(
            arm["relative_change_sum"] for arm in arms.values()
        ),
        "subtracted_from_identity_difference": False,
    }


def _traction_envelope(
    *,
    case_id: str,
    observation_key: str,
    summary_metric_name: str,
    observations_t128: dict[str, dict[str, dict[str, Any]]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        coarse_obs = observations_t128[case_id][representation]
        fine_obs = observations_t256[case_id][representation]
        coarse = coarse_obs[observation_key]
        fine = _fine_on_coarse(fine_obs[observation_key], coarse.shape[-1])
        time_step = float(coarse_obs["time"][1] - coarse_obs["time"][0])
        temporal = projected_traction_difference(
            coarse_obs["common_x"],
            coarse,
            fine,
            time_step,
            protocol.traction_floor,
        )
        summary_s3 = summaries_t256[
            endpoint_key(case_id, representation, "S3", 256)
        ]
        summary_s4 = summaries_t256[
            endpoint_key(case_id, representation, "S4", 256)
        ]
        value_s3 = float(
            summary_s3["v05_common_projection_sidecar"]["values"][
                summary_metric_name
            ]
        )
        value_s4 = float(
            summary_s4["v05_common_projection_sidecar"]["values"][
                summary_metric_name
            ]
        )
        spatial = relative_difference(value_s3, value_s4, protocol.traction_floor)
        arms[representation] = {
            "temporal_T128_to_T256_common_traction_relative": temporal,
            "spatial_S3_to_S4_common_traction_proxy_relative": spatial,
            "relative_change_sum": temporal + spatial,
        }
    return {
        "metric": (
            "myocardium_ecm_common_traction_normalized_L2"
            if summary_metric_name.startswith("myocardium")
            else "endocardium_ecm_common_traction_normalized_L2"
        ),
        "by_representation": arms,
        "combined_relative_envelope": sum(
            arm["relative_change_sum"] for arm in arms.values()
        ),
        "subtracted_from_identity_difference": False,
    }


def _phase_envelope(
    *,
    case_id: str,
    observations_t128: dict[str, dict[str, dict[str, Any]]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    summaries_t128: dict[str, dict[str, Any]],
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        coarse = response_signal(case_id, observations_t128[case_id][representation])
        fine = response_signal(case_id, observations_t256[case_id][representation])
        temporal = wrapped_phase_difference(
            fundamental(coarse), fundamental(_fine_on_coarse(fine, coarse.size))
        )
        custom_displacement_signal = case_id in ("ID-LN", "ID-LS")
        summary_s3 = (
            None
            if custom_displacement_signal
            else summaries_t256[
                endpoint_key(case_id, representation, "S3", 256)
            ].get("shortening_phase_relative_to_activation_rad")
        )
        summary_s4 = (
            None
            if custom_displacement_signal
            else summaries_t256[
                endpoint_key(case_id, representation, "S4", 256)
            ].get("shortening_phase_relative_to_activation_rad")
        )
        summary_t128 = (
            None
            if custom_displacement_signal
            else summaries_t128[
                endpoint_key(case_id, representation, "S4", 128)
            ].get("shortening_phase_relative_to_activation_rad")
        )
        spatial = (
            wrapped_phase_difference(
                np.exp(1j * float(summary_s3)), np.exp(1j * float(summary_s4))
            )
            if summary_s3 is not None and summary_s4 is not None
            else None
        )
        frozen_summary_time = (
            wrapped_phase_difference(
                np.exp(1j * float(summary_t128)), np.exp(1j * float(summary_s4))
            )
            if summary_t128 is not None and summary_s4 is not None
            else None
        )
        arms[representation] = {
            "temporal_T128_to_T256_signal_phase_abs_rad": temporal,
            "spatial_S3_to_S4_frozen_summary_phase_abs_rad": spatial,
            "frozen_summary_T128_to_T256_phase_abs_rad": frozen_summary_time,
            "available_component_sum_rad": temporal + (spatial or 0.0),
            "spatial_component_available": spatial is not None,
        }
    spatial_complete = all(
        arm["spatial_component_available"] for arm in arms.values()
    )
    return {
        "metric": "fundamental_phase",
        "by_representation": arms,
        "combined_available_component_envelope_rad": sum(
            arm["available_component_sum_rad"] for arm in arms.values()
        ),
        "spatial_component_complete": spatial_complete,
        "incomplete_reason": (
            None
            if spatial_complete
            else "ID-LN/ID-LS custom phase signals have no frozen S3 dynamic archive"
        ),
        "classification_uses_identity_gate_not_envelope": True,
        "subtracted_from_identity_difference": False,
    }


def _gain_from_summary_amplitudes(
    *,
    combined_case: str,
    representation: str,
    spatial_level: str,
    steps: int,
    summaries: dict[str, dict[str, Any]],
    floor: float,
) -> float:
    amplitudes = [
        float(
            summaries[
                endpoint_key(case_id, representation, spatial_level, steps)
            ]["shortening_fundamental_amplitude"]
        )
        for case_id in (combined_case, "ID-A2", "ID-LN")
    ]
    return amplitudes[0] / max(amplitudes[1] + amplitudes[2], floor)


def _gain_envelope(
    *,
    combined_case: str,
    summaries_t128: dict[str, dict[str, Any]],
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        gain_s3_t256 = _gain_from_summary_amplitudes(
            combined_case=combined_case,
            representation=representation,
            spatial_level="S3",
            steps=256,
            summaries=summaries_t256,
            floor=protocol.shortening_floor,
        )
        gain_s4_t256 = _gain_from_summary_amplitudes(
            combined_case=combined_case,
            representation=representation,
            spatial_level="S4",
            steps=256,
            summaries=summaries_t256,
            floor=protocol.shortening_floor,
        )
        gain_s4_t128 = _gain_from_summary_amplitudes(
            combined_case=combined_case,
            representation=representation,
            spatial_level="S4",
            steps=128,
            summaries=summaries_t128,
            floor=protocol.shortening_floor,
        )
        spatial = relative_difference(
            gain_s3_t256, gain_s4_t256, protocol.shortening_floor
        )
        temporal = relative_difference(
            gain_s4_t128, gain_s4_t256, protocol.shortening_floor
        )
        arms[representation] = {
            "gain_S3_T256": gain_s3_t256,
            "gain_S4_T256": gain_s4_t256,
            "gain_S4_T128": gain_s4_t128,
            "spatial_relative_change": spatial,
            "temporal_relative_change": temporal,
            "relative_change_sum": spatial + temporal,
        }
    return {
        "metric": "combined_load_gain",
        "operator_source": protocol.combined_gain_operator_source,
        "by_representation": arms,
        "combined_relative_envelope": sum(
            arm["relative_change_sum"] for arm in arms.values()
        ),
        "subtracted_from_identity_difference": False,
    }


def _hotspot_envelope(
    *,
    summaries_t128: dict[str, dict[str, Any]],
    summaries_t256: dict[str, dict[str, Any]],
    protocol: IdentityGateProtocolV06,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for representation in protocol.representations:
        s3_t256 = float(
            summaries_t256[endpoint_key("ID-S1", representation, "S3", 256)][
                "hotspot_x"
            ]
        )
        s4_t256 = float(
            summaries_t256[endpoint_key("ID-S1", representation, "S4", 256)][
                "hotspot_x"
            ]
        )
        s4_t128 = float(
            summaries_t128[endpoint_key("ID-S1", representation, "S4", 128)][
                "hotspot_x"
            ]
        )
        arms[representation] = {
            "native_summary_hotspot_S3_T256": s3_t256,
            "native_summary_hotspot_S4_T256": s4_t256,
            "native_summary_hotspot_S4_T128": s4_t128,
            "spatial_absolute_shift": abs(s4_t256 - s3_t256),
            "temporal_absolute_shift": abs(s4_t256 - s4_t128),
            "absolute_shift_sum": abs(s4_t256 - s3_t256)
            + abs(s4_t256 - s4_t128),
        }
    return {
        "metric": "common_grid_hotspot_center_and_split",
        "proxy_observable": "frozen_native_summary_hotspot_x",
        "by_representation": arms,
        "combined_absolute_envelope": sum(
            arm["absolute_shift_sum"] for arm in arms.values()
        ),
        "subtracted_from_identity_difference": False,
    }


def numerical_change_envelope(
    *,
    summaries_t128: dict[str, dict[str, Any]],
    summaries_t256: dict[str, dict[str, Any]],
    observations_t128: dict[str, dict[str, dict[str, Any]]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
    protocol: IdentityGateProtocolV06 = FROZEN_PROTOCOL_V06,
) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {}
    for case_id in protocol.holdout_cases:
        entries = {
            "peak_limited_shortening": _scalar_envelope(
                case_id=case_id,
                metric="peak_limited_shortening",
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                floor=protocol.shortening_floor,
                protocol=protocol,
            ),
            "shortening_waveform_normalized_L2": _waveform_envelope(
                case_id=case_id,
                observations_t128=observations_t128,
                observations_t256=observations_t256,
                summaries_t256=summaries_t256,
                protocol=protocol,
            ),
            "myocardium_ecm_common_traction_normalized_L2": _traction_envelope(
                case_id=case_id,
                observation_key="myocardium_ecm_common_traction",
                summary_metric_name="myocardium_ecm_traction_l2",
                observations_t128=observations_t128,
                observations_t256=observations_t256,
                summaries_t256=summaries_t256,
                protocol=protocol,
            ),
            "endocardium_ecm_common_traction_normalized_L2": _traction_envelope(
                case_id=case_id,
                observation_key="endocardium_ecm_common_traction",
                summary_metric_name="endocardium_ecm_traction_l2",
                observations_t128=observations_t128,
                observations_t256=observations_t256,
                summaries_t256=summaries_t256,
                protocol=protocol,
            ),
            "fundamental_phase": _phase_envelope(
                case_id=case_id,
                observations_t128=observations_t128,
                observations_t256=observations_t256,
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                protocol=protocol,
            ),
            "total_dissipation": _scalar_envelope(
                case_id=case_id,
                metric="total_dissipation",
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                floor=protocol.energy_floor,
                protocol=protocol,
            ),
            "cycle_stored_energy_change_near_zero": _scalar_envelope(
                case_id=case_id,
                metric="cycle_stored_energy_change_near_zero",
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                floor=protocol.energy_floor,
                protocol=protocol,
            ),
        }
        if case_id in ("ID-C0", "ID-CQ"):
            entries["combined_load_gain"] = _gain_envelope(
                combined_case=case_id,
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                protocol=protocol,
            )
        if case_id == "ID-S1":
            entries["common_grid_hotspot_center_and_split"] = _hotspot_envelope(
                summaries_t128=summaries_t128,
                summaries_t256=summaries_t256,
                protocol=protocol,
            )
        cases[case_id] = entries
    return {
        "schema": "paper2_m2a_v06_numerical_change_envelope",
        "cases": cases,
        "identity_difference_reduced_by_envelope": False,
        "interpretation": (
            "The envelope is diagnostic context only and is never subtracted from an "
            "identity difference or used to change classification."
        ),
    }
