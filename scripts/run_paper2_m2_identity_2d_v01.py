"""Execute the governed Paper-2 M2A two-dimensional identity matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import dolfinx
import numpy as np
import scipy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paper2_m2.config import FROZEN_CONFIG  # noqa: E402
from paper2_m2.identity_2d import (  # noqa: E402
    Endpoint,
    ModelSystem,
    build_calibration,
    build_system,
    simulate_endpoint,
)


HELD_OUT_CASES = ("ID-A2", "ID-LN", "ID-LS", "ID-C0", "ID-CQ", "ID-S1")
DYNAMIC_CASES = ("ID-A1",) + HELD_OUT_CASES
PRIMARY_METRICS = (
    "peak_limited_shortening",
    "shortening_waveform_l2",
    "myocardium_ecm_traction_l2",
    "endocardium_ecm_traction_l2",
    "total_dissipation",
)


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


def _summary_metric(summary: dict[str, Any], metric: str) -> float:
    if metric == "total_dissipation":
        ledger = summary["ledger"]
        return float(
            ledger["total_drag_dissipation"]
            + ledger["total_sls_dissipation"]
        )
    return float(summary[metric])


def _relative_difference(value_a: float, value_b: float, floor: float) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def _metric_floor(metric: str) -> float:
    config = FROZEN_CONFIG
    if "shortening" in metric:
        return config.near_zero_shortening_absolute_scale
    if "traction" in metric:
        return config.near_zero_traction_absolute_scale
    return config.near_zero_energy_absolute_scale


def _endpoint_key(
    case_id: str,
    representation: str,
    spatial_label: str,
    steps_per_cycle: int,
    tolerance_label: str,
) -> str:
    return "__".join(
        (
            case_id,
            representation,
            spatial_label,
            f"T{steps_per_cycle}",
            tolerance_label,
        )
    )


def _structural_gate(summary: dict[str, Any]) -> dict[str, Any]:
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
            "pass": summary["maximum_state_norm"]
            <= config.zero_state_absolute_tolerance,
        }
    if summary["case_id"] == "ID-P1":
        checks["uniform_strain_manufactured_solution"] = {
            "value": summary["manufactured_uniform_strain_relative_error"],
            "threshold": config.manufactured_solution_relative_tolerance,
            "pass": summary["manufactured_uniform_strain_relative_error"]
            <= config.manufactured_solution_relative_tolerance,
        }
    return {
        "pass": all(check["pass"] for check in checks.values()),
        "checks": checks,
    }


def _global_structural_checks(system: ModelSystem) -> dict[str, Any]:
    rng = np.random.default_rng(20260903)
    state = 1.0e-3 * rng.standard_normal(system.state_size)
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
        np.dot(system.active_vector_h, state)
        + system.active_scalar_c * activation
    )
    derivative_error = _relative_difference(
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


def _numerical_stage_gate(
    summaries: dict[str, dict[str, Any]],
    steps_per_cycle: int,
) -> dict[str, Any]:
    config = FROZEN_CONFIG
    comparisons: list[dict[str, Any]] = []
    failures: list[str] = []
    for case_id in config.cases:
        for representation in ("DCM", "FEM"):
            metrics = ("passive_tangent",) if case_id == "ID-P1" else (
                ("maximum_state_norm",) if case_id == "ID-P0" else PRIMARY_METRICS
            )
            for tolerance_label in ("C0", "C1"):
                level_values: dict[str, dict[str, float]] = {}
                for spatial_label in ("S0", "S1", "S2"):
                    key = _endpoint_key(
                        case_id,
                        representation,
                        spatial_label,
                        steps_per_cycle,
                        tolerance_label,
                    )
                    level_values[spatial_label] = {
                        metric: _summary_metric(summaries[key], metric)
                        for metric in metrics
                    }
                for metric in metrics:
                    values = [level_values[level][metric] for level in ("S0", "S1", "S2")]
                    floor = _metric_floor(metric)
                    fine_difference = _relative_difference(values[1], values[2], floor)
                    first_increment = values[1] - values[0]
                    second_increment = values[2] - values[1]
                    scale = max(*(abs(value) for value in values), floor)
                    direction_consistent = bool(
                        first_increment * second_increment >= 0.0
                        or (
                            abs(first_increment) <= config.spatial_endpoint_relative_tolerance * scale
                            and abs(second_increment) <= config.spatial_endpoint_relative_tolerance * scale
                        )
                    )
                    passed = bool(
                        fine_difference <= config.spatial_endpoint_relative_tolerance
                        and direction_consistent
                    )
                    record = {
                        "kind": "spatial",
                        "case_id": case_id,
                        "representation": representation,
                        "tolerance_label": tolerance_label,
                        "metric": metric,
                        "values_S0_S1_S2": values,
                        "finest_two_relative_difference": fine_difference,
                        "threshold": config.spatial_endpoint_relative_tolerance,
                        "direction_consistent": direction_consistent,
                        "pass": passed,
                    }
                    comparisons.append(record)
                    if not passed:
                        failures.append(
                            f"spatial:{case_id}:{representation}:{tolerance_label}:{metric}"
                        )

            for spatial_label in ("S0", "S1", "S2"):
                for metric in metrics:
                    values = []
                    for tolerance_label in ("C0", "C1"):
                        key = _endpoint_key(
                            case_id,
                            representation,
                            spatial_label,
                            steps_per_cycle,
                            tolerance_label,
                        )
                        values.append(_summary_metric(summaries[key], metric))
                    difference = _relative_difference(
                        values[0], values[1], _metric_floor(metric)
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
    for representation in ("DCM", "FEM"):
        for tolerance_label in ("C0", "C1"):
            hotspot_values = []
            for spatial_label in ("S0", "S1", "S2"):
                key = _endpoint_key(
                    "ID-S1",
                    representation,
                    spatial_label,
                    steps_per_cycle,
                    tolerance_label,
                )
                hotspot_values.append(float(summaries[key]["hotspot_x"]))
            fine_dx = config.length / config.spatial("S2").nx
            hotspot_jump = abs(hotspot_values[2] - hotspot_values[1])
            passed = hotspot_jump <= fine_dx + 1.0e-12
            comparisons.append(
                {
                    "kind": "hotspot_spatial",
                    "representation": representation,
                    "tolerance_label": tolerance_label,
                    "values_S0_S1_S2": hotspot_values,
                    "finest_two_absolute_jump": hotspot_jump,
                    "threshold_one_finest_cell": fine_dx,
                    "pass": passed,
                }
            )
            if not passed:
                failures.append(f"hotspot:{representation}:{tolerance_label}")
    return {
        "steps_per_cycle": steps_per_cycle,
        "pass": not failures,
        "failures": failures,
        "comparisons": comparisons,
    }


def _time_gate(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    config = FROZEN_CONFIG
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for case_id in config.cases:
        for representation in ("DCM", "FEM"):
            metrics = ("passive_tangent",) if case_id == "ID-P1" else (
                ("maximum_state_norm",) if case_id == "ID-P0" else PRIMARY_METRICS
            )
            for metric in metrics:
                values = []
                for steps in config.time_steps_per_cycle:
                    key = _endpoint_key(case_id, representation, "S2", steps, "C1")
                    values.append(_summary_metric(summaries[key], metric))
                floor = _metric_floor(metric)
                fine_difference = _relative_difference(values[1], values[2], floor)
                first_increment = values[1] - values[0]
                second_increment = values[2] - values[1]
                scale = max(*(abs(value) for value in values), floor)
                direction_consistent = bool(
                    first_increment * second_increment >= 0.0
                    or (
                        abs(first_increment) <= config.spatial_endpoint_relative_tolerance * scale
                        and abs(second_increment) <= config.spatial_endpoint_relative_tolerance * scale
                    )
                )
                passed = bool(
                    fine_difference <= config.spatial_endpoint_relative_tolerance
                    and direction_consistent
                )
                records.append(
                    {
                        "case_id": case_id,
                        "representation": representation,
                        "metric": metric,
                        "values_T64_T128_T256": values,
                        "finest_two_relative_difference": fine_difference,
                        "threshold": config.spatial_endpoint_relative_tolerance,
                        "direction_consistent": direction_consistent,
                        "pass": passed,
                    }
                )
                if not passed:
                    failures.append(f"time:{case_id}:{representation}:{metric}")
    return {"pass": not failures, "failures": failures, "comparisons": records}


def _response_signal(case_id: str, endpoint: Endpoint, steps: int) -> np.ndarray:
    arrays = endpoint.arrays
    if case_id == "ID-LN":
        return -arrays["mean_endocardial_normal_displacement_two_cycles"][:steps]
    if case_id == "ID-LS":
        return arrays["mean_endocardial_tangential_displacement_two_cycles"][:steps]
    return arrays["limited_shortening_two_cycles"][:steps]


def _waveform_difference(value_a: np.ndarray, value_b: np.ndarray, floor: float) -> float:
    return float(
        np.linalg.norm(value_a - value_b)
        / max(np.linalg.norm(value_a), np.linalg.norm(value_b), floor * math.sqrt(value_a.size))
    )


def _identity_gate(
    endpoints: dict[str, Endpoint],
    summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    config = FROZEN_CONFIG
    steps = 256
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    maybe_flags: list[str] = []
    case_scores: dict[str, float] = {}
    for case_id in HELD_OUT_CASES:
        endpoint_dcm = endpoints[_endpoint_key(case_id, "DCM", "S2", steps, "C1")]
        endpoint_fem = endpoints[_endpoint_key(case_id, "FEM", "S2", steps, "C1")]
        summary_dcm = endpoint_dcm.summary
        summary_fem = endpoint_fem.summary
        scalar_tests = (
            (
                "peak_limited_shortening",
                config.identity_shortening_relative_tolerance,
                config.near_zero_shortening_absolute_scale,
            ),
            (
                "total_dissipation",
                config.identity_energy_relative_tolerance,
                config.near_zero_energy_absolute_scale,
            ),
        )
        case_score = 0.0
        for metric, threshold, floor in scalar_tests:
            value_dcm = _summary_metric(summary_dcm, metric)
            value_fem = _summary_metric(summary_fem, metric)
            difference = _relative_difference(value_dcm, value_fem, floor)
            passed = difference <= threshold
            case_score = max(case_score, difference)
            records.append(
                {
                    "case_id": case_id,
                    "metric": metric,
                    "dcm": value_dcm,
                    "fem": value_fem,
                    "absolute_difference": abs(value_dcm - value_fem),
                    "relative_difference": difference,
                    "threshold": threshold,
                    "pass": passed,
                }
            )
            if not passed:
                (failures if difference > config.identity_no_go_relative_threshold else maybe_flags).append(
                    f"identity:{case_id}:{metric}"
                )

        shortening_dcm = endpoint_dcm.arrays["limited_shortening_two_cycles"][:steps]
        shortening_fem = endpoint_fem.arrays["limited_shortening_two_cycles"][:steps]
        shortening_wave_difference = _waveform_difference(
            shortening_dcm,
            shortening_fem,
            config.near_zero_shortening_absolute_scale,
        )
        traction_dcm = endpoint_dcm.arrays[
            "myocardium_ecm_traction_two_cycles"
        ][:, :steps]
        traction_fem = endpoint_fem.arrays[
            "myocardium_ecm_traction_two_cycles"
        ][:, :steps]
        traction_wave_difference = _waveform_difference(
            traction_dcm,
            traction_fem,
            config.near_zero_traction_absolute_scale,
        )
        for metric, difference, threshold in (
            (
                "shortening_waveform_normalized_L2",
                shortening_wave_difference,
                config.identity_waveform_relative_tolerance,
            ),
            (
                "common_interface_traction_normalized_L2",
                traction_wave_difference,
                config.identity_traction_relative_tolerance,
            ),
        ):
            passed = difference <= threshold
            case_score = max(case_score, difference)
            records.append(
                {
                    "case_id": case_id,
                    "metric": metric,
                    "relative_difference": difference,
                    "threshold": threshold,
                    "pass": passed,
                }
            )
            if not passed:
                (failures if difference > config.identity_no_go_relative_threshold else maybe_flags).append(
                    f"identity:{case_id}:{metric}"
                )

        response_dcm = _response_signal(case_id, endpoint_dcm, steps)
        response_fem = _response_signal(case_id, endpoint_fem, steps)
        harmonic_dcm = complex(np.fft.rfft(response_dcm - np.mean(response_dcm))[1])
        harmonic_fem = complex(np.fft.rfft(response_fem - np.mean(response_fem))[1])
        amplitude_dcm = 2.0 * abs(harmonic_dcm) / steps
        amplitude_fem = 2.0 * abs(harmonic_fem) / steps
        coherent = bool(
            amplitude_dcm >= config.coherence_amplitude_floor
            and amplitude_fem >= config.coherence_amplitude_floor
        )
        if coherent:
            phase_difference = abs(float(np.angle(harmonic_dcm / harmonic_fem)))
            phase_pass = phase_difference <= config.identity_phase_absolute_tolerance_rad
        else:
            phase_difference = None
            phase_pass = True
        records.append(
            {
                "case_id": case_id,
                "metric": "fundamental_phase",
                "amplitude_dcm": amplitude_dcm,
                "amplitude_fem": amplitude_fem,
                "coherence_gate": coherent,
                "absolute_phase_difference_rad": phase_difference,
                "threshold_rad": config.identity_phase_absolute_tolerance_rad,
                "pass": phase_pass,
                "near_zero_rule_applied": not coherent,
            }
        )
        if not phase_pass:
            if phase_difference is not None and phase_difference > 0.15:
                failures.append(f"identity:{case_id}:phase")
            else:
                maybe_flags.append(f"identity:{case_id}:phase")

        cycle_energy_dcm = float(summary_dcm["ledger"]["cycle_energy_change"])
        cycle_energy_fem = float(summary_fem["ledger"]["cycle_energy_change"])
        energy_absolute_difference = abs(cycle_energy_dcm - cycle_energy_fem)
        energy_pass = energy_absolute_difference <= config.near_zero_energy_absolute_scale
        records.append(
            {
                "case_id": case_id,
                "metric": "cycle_stored_energy_change_near_zero",
                "dcm": cycle_energy_dcm,
                "fem": cycle_energy_fem,
                "absolute_difference": energy_absolute_difference,
                "absolute_threshold": config.near_zero_energy_absolute_scale,
                "pass": energy_pass,
            }
        )
        if not energy_pass:
            failures.append(f"identity:{case_id}:cycle_energy")
        case_scores[case_id] = case_score

    for combined_case in ("ID-C0", "ID-CQ"):
        gains = {}
        for representation in ("DCM", "FEM"):
            combined = endpoints[
                _endpoint_key(combined_case, representation, "S2", steps, "C1")
            ]
            active = endpoints[
                _endpoint_key("ID-A2", representation, "S2", steps, "C1")
            ]
            normal = endpoints[
                _endpoint_key("ID-LN", representation, "S2", steps, "C1")
            ]
            amplitudes = []
            for endpoint in (combined, active, normal):
                signal = endpoint.arrays["limited_shortening_two_cycles"][:steps]
                harmonic = complex(np.fft.rfft(signal - np.mean(signal))[1])
                amplitudes.append(2.0 * abs(harmonic) / steps)
            gains[representation] = amplitudes[0] / max(
                amplitudes[1] + amplitudes[2],
                config.near_zero_shortening_absolute_scale,
            )
        difference = _relative_difference(
            gains["DCM"], gains["FEM"], config.near_zero_shortening_absolute_scale
        )
        passed = difference <= config.identity_combined_gain_relative_tolerance
        records.append(
            {
                "case_id": combined_case,
                "metric": "combined_load_gain",
                "dcm": gains["DCM"],
                "fem": gains["FEM"],
                "relative_difference": difference,
                "threshold": config.identity_combined_gain_relative_tolerance,
                "pass": passed,
            }
        )
        if not passed:
            (failures if difference > config.identity_no_go_relative_threshold else maybe_flags).append(
                f"identity:{combined_case}:combined_gain"
            )

    hotspot_dcm = endpoints[
        _endpoint_key("ID-S1", "DCM", "S2", steps, "C1")
    ].summary["hotspot_x"]
    hotspot_fem = endpoints[
        _endpoint_key("ID-S1", "FEM", "S2", steps, "C1")
    ].summary["hotspot_x"]
    hotspot_difference = abs(float(hotspot_dcm) - float(hotspot_fem))
    hotspot_threshold = config.length / config.spatial("S2").nx
    hotspot_pass = hotspot_difference <= hotspot_threshold + 1.0e-12
    records.append(
        {
            "case_id": "ID-S1",
            "metric": "hotspot_center",
            "dcm": hotspot_dcm,
            "fem": hotspot_fem,
            "absolute_difference": hotspot_difference,
            "threshold_one_finest_cell": hotspot_threshold,
            "pass": hotspot_pass,
        }
    )
    if not hotspot_pass:
        failures.append("identity:ID-S1:hotspot")

    if failures:
        decision = "NO-GO-ID"
    elif maybe_flags:
        decision = "MAYBE-ID"
    else:
        decision = "GO-ID"
    return {
        "decision": decision,
        "pass_all_identity_thresholds": not failures and not maybe_flags,
        "no_go_failures": failures,
        "maybe_flags": maybe_flags,
        "case_max_relative_scores": case_scores,
        "comparisons": records,
        "evidence_boundary": (
            "Identity applies only to the preregistered M2A endpoints in this "
            "linear small-strain plane-strain periodic benchmark."
        ),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    config = FROZEN_CONFIG.checked()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    fields_dir = arguments.output_dir / "selected_fields"
    fields_dir.mkdir(exist_ok=False)
    started = time.perf_counter()
    manifest = {
        "schema": "paper2_m2a_identity_2d_run_manifest_v01",
        "config": config.canonical_payload(),
        "config_digest": config.digest(),
        "contract_sha256": _sha256(arguments.contract),
        "authorization_sha256": _sha256(arguments.authorization),
        "preflight_sha256": _sha256(arguments.preflight),
        "runtime": {
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "cpu_processes": config.cpu_processes,
            "gpu_used": False,
        },
    }
    _write_json(arguments.output_dir / "run_manifest.json", manifest)

    calibration = build_calibration(config)
    _write_json(arguments.output_dir / "calibration.json", calibration)
    passive_scale = float(calibration["passive"]["dcm_passive_scale"])
    active_scale = float(calibration["active"]["dcm_active_scale"])

    systems: dict[tuple[str, str, str], ModelSystem] = {}
    for representation in ("DCM", "FEM"):
        for spatial_label in ("S0", "S1", "S2"):
            for profile in ("uniform", "S1"):
                systems[(representation, spatial_label, profile)] = build_system(
                    representation=representation,
                    spatial_label=spatial_label,
                    passive_dcm_scale=passive_scale,
                    active_dcm_scale=active_scale,
                    active_profile=profile,
                    config=config,
                )
    global_checks = _global_structural_checks(systems[("FEM", "S1", "uniform")])
    if not all(record["pass"] for record in global_checks.values()):
        failure = {
            "status": "FAIL_CLOSED",
            "stage": "global_structural_checks",
            "checks": global_checks,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        raise SystemExit(2)

    summaries: dict[str, dict[str, Any]] = {}
    selected_endpoints: dict[str, Endpoint] = {}
    structural_records: dict[str, Any] = {}
    stage_gates = []
    endpoint_counter = 0
    for steps_per_cycle in config.time_steps_per_cycle:
        stage_started = time.perf_counter()
        for case_id in config.cases:
            profile = "S1" if case_id == "ID-S1" else "uniform"
            for representation in ("DCM", "FEM"):
                for spatial_label in ("S0", "S1", "S2"):
                    system = systems[(representation, spatial_label, profile)]
                    for tolerance_label in ("C0", "C1"):
                        endpoint_started = time.perf_counter()
                        endpoint = simulate_endpoint(
                            system=system,
                            case_id=case_id,
                            steps_per_cycle=steps_per_cycle,
                            tolerance_label=tolerance_label,
                        )
                        elapsed = time.perf_counter() - endpoint_started
                        endpoint.summary["runtime_seconds"] = elapsed
                        key = _endpoint_key(
                            case_id,
                            representation,
                            spatial_label,
                            steps_per_cycle,
                            tolerance_label,
                        )
                        summaries[key] = endpoint.summary
                        gate = _structural_gate(endpoint.summary)
                        structural_records[key] = gate
                        endpoint_counter += 1
                        if elapsed > config.endpoint_runtime_budget_seconds or not gate["pass"]:
                            failure = {
                                "status": "FAIL_CLOSED",
                                "stage": f"T{steps_per_cycle}_endpoint",
                                "endpoint": key,
                                "runtime_seconds": elapsed,
                                "runtime_budget_seconds": config.endpoint_runtime_budget_seconds,
                                "structural_gate": gate,
                                "completed_endpoints": endpoint_counter,
                            }
                            _write_json(arguments.output_dir / "failure.json", failure)
                            raise SystemExit(2)
                        if (
                            steps_per_cycle == 256
                            and spatial_label == "S2"
                            and tolerance_label == "C1"
                            and case_id in HELD_OUT_CASES
                        ):
                            selected_endpoints[key] = endpoint
                            np.savez_compressed(
                                fields_dir / f"{key}.npz", **endpoint.arrays
                            )

        stage_gate = _numerical_stage_gate(summaries, steps_per_cycle)
        stage_gate["runtime_seconds"] = time.perf_counter() - stage_started
        stage_gates.append(stage_gate)
        _write_json(
            arguments.output_dir / f"stage_T{steps_per_cycle}_gate.json",
            stage_gate,
        )
        if not stage_gate["pass"]:
            failure = {
                "status": "FAIL_CLOSED",
                "stage": f"T{steps_per_cycle}_numerical_gate",
                "failures": stage_gate["failures"],
                "completed_endpoints": endpoint_counter,
            }
            _write_json(arguments.output_dir / "failure.json", failure)
            raise SystemExit(2)

    time_gate = _time_gate(summaries)
    _write_json(arguments.output_dir / "time_gate.json", time_gate)
    if not time_gate["pass"]:
        failure = {
            "status": "FAIL_CLOSED",
            "stage": "time_numerical_gate",
            "failures": time_gate["failures"],
            "completed_endpoints": endpoint_counter,
        }
        _write_json(arguments.output_dir / "failure.json", failure)
        raise SystemExit(2)

    identity_gate = _identity_gate(selected_endpoints, summaries)
    _write_json(arguments.output_dir / "identity_gate.json", identity_gate)
    _write_json(arguments.output_dir / "endpoint_summaries.json", summaries)
    _write_json(arguments.output_dir / "structural_gates.json", structural_records)
    final = {
        "schema": "paper2_m2a_identity_2d_final_v01",
        "status": "COMPLETE_FOR_INSPECTOR_AND_HUMAN_GATE",
        "decision": identity_gate["decision"],
        "completed_endpoints": endpoint_counter,
        "expected_endpoints": 324,
        "all_structural_gates_pass": all(
            record["pass"] for record in structural_records.values()
        )
        and all(record["pass"] for record in global_checks.values()),
        "all_numerical_gates_pass": all(gate["pass"] for gate in stage_gates)
        and time_gate["pass"],
        "identity_gate": identity_gate,
        "global_structural_checks": global_checks,
        "runtime_seconds": time.perf_counter() - started,
        "resource_budget_seconds": config.matrix_runtime_budget_seconds,
        "within_resource_budget": (
            time.perf_counter() - started <= config.matrix_runtime_budget_seconds
        ),
        "config_digest": config.digest(),
        "evidence_boundary": (
            "No M2B, 3D, fluid, parameter sweep, GPU, or EFE biological claim is authorized by this result."
        ),
    }
    _write_json(arguments.output_dir / "final_summary.json", final)
    print(json.dumps(final, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
