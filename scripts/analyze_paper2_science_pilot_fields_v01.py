"""Post-process the existing Paper 2 science pilot fields without new FEM solves."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any

import numpy as np


SCHEMA = "paper2_science_pilot_field_comparison_v01"
EXPECTED_INPUT = Path("results/paper2_science_pilot/v01_20260905/numerical")
EXPECTED_OUTPUT = EXPECTED_INPUT / "field_comparison_v01.json"
COMMON_X_OVER_L = (-0.25, 0.0, 0.25)
AMPLITUDE_FLOOR = 1.0e-12
POWER_FLOOR = 1.0e-14
RECOMPUTE_TOLERANCE = 1.0e-12
COMPUTE_BUDGET_SECONDS = 120.0
HOLDOUT_SIGNATURES = {
    (0.07, 0.2, "A1"),
    (0.07, 0.2, "S1"),
    (0.7, 0.45, "A1"),
    (0.7, 0.45, "S1"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _create_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write("\n")


def _complex_record(value: complex, activation: complex) -> dict[str, Any]:
    amplitude = abs(value)
    phase_interpretable = (
        amplitude > AMPLITUDE_FLOOR and abs(activation) > AMPLITUDE_FLOOR
    )
    phase_rad = float(np.angle(value / activation)) if phase_interpretable else None
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "amplitude": float(amplitude),
        "phase_relative_to_activation_rad": phase_rad,
        "phase_relative_to_activation_deg": (
            math.degrees(phase_rad) if phase_rad is not None else None
        ),
        "phase_interpretable": phase_interpretable,
    }


def _difference_record(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "absolute_amplitude": float(abs(value)),
    }


def _safe_ratio(numerator: float, denominator: float) -> dict[str, Any]:
    if abs(denominator) <= AMPLITUDE_FLOOR:
        return {
            "defined": False,
            "value": None,
            "reason": "denominator_at_or_below_amplitude_floor",
        }
    return {
        "defined": True,
        "value": float(numerator / denominator),
        "reason": None,
    }


def _phase_difference_deg(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    phase_a = first["phase_relative_to_activation_rad"]
    phase_b = second["phase_relative_to_activation_rad"]
    if phase_a is None or phase_b is None:
        return {
            "defined": False,
            "value": None,
            "reason": "one_or_both_phases_not_interpretable",
        }
    difference = math.atan2(math.sin(phase_b - phase_a), math.cos(phase_b - phase_a))
    return {"defined": True, "value": abs(math.degrees(difference)), "reason": None}


def _harmonic_coefficient(values: np.ndarray, steps_per_cycle: int) -> np.ndarray:
    first_cycle = np.asarray(values[..., :steps_per_cycle], dtype=np.float64)
    centered = first_cycle - np.mean(first_cycle, axis=-1, keepdims=True)
    return (2.0 / steps_per_cycle) * np.fft.rfft(centered, axis=-1)[..., 1]


def _trapezoidal_weights(x_nodes: np.ndarray) -> np.ndarray:
    x_values = np.asarray(x_nodes, dtype=np.float64)
    if x_values.ndim != 1 or len(x_values) < 2:
        raise RuntimeError("interface coordinate array is not one-dimensional")
    spacing = np.diff(x_values)
    if np.any(spacing <= 0.0):
        raise RuntimeError("interface coordinates are not strictly increasing")
    weights = np.empty_like(x_values)
    weights[0] = 0.5 * spacing[0]
    weights[-1] = 0.5 * spacing[-1]
    weights[1:-1] = 0.5 * (spacing[:-1] + spacing[1:])
    return weights


def _weighted_complex_rms(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sqrt(np.sum(weights * np.abs(values) ** 2) / np.sum(weights)))


def _interpolate_complex(
    x_nodes: np.ndarray, values: np.ndarray, x_target: float
) -> complex:
    return complex(
        np.interp(x_target, x_nodes, values.real),
        np.interp(x_target, x_nodes, values.imag),
    )


def _exact_node(x_nodes: np.ndarray, x_target: float) -> bool:
    return bool(np.any(np.isclose(x_nodes, x_target, rtol=0.0, atol=1.0e-13)))


def _peak_record(
    x_nodes: np.ndarray, values: np.ndarray, activation: complex
) -> dict[str, Any]:
    amplitudes = np.abs(values)
    maximum = float(np.max(amplitudes))
    tied = np.flatnonzero(
        np.isclose(amplitudes, maximum, rtol=1.0e-10, atol=1.0e-14)
    )
    first_index = int(tied[0])
    return {
        "maximum": _complex_record(complex(values[first_index]), activation),
        "first_maximum_x_over_L": float(x_nodes[first_index]),
        "tied_maximum_x_over_L": [float(x_nodes[index]) for index in tied],
        "tie_rule": "all nodes within rtol=1e-10 and atol=1e-14 of maximum amplitude; first listed node is the representative",
    }


def _activation_coefficient(record: dict[str, Any]) -> complex:
    activation = record["observables"]["activation"]
    return complex(
        activation["fundamental_coefficient_real"],
        activation["fundamental_coefficient_imag"],
    )


def _active_work(record: dict[str, Any]) -> float:
    return float(
        record["observables"]["work_and_dissipation"]["active_input_work_raw"]
    )


def _load_basic_records(input_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summary_path = input_root / "summary.json"
    summary = _load_json(summary_path)
    items = [item for item in summary["cases"] if item["group"] == "basic"]
    if len(items) != 18:
        raise RuntimeError(f"expected 18 basic cases, found {len(items)}")
    records: list[dict[str, Any]] = []
    for item in items:
        case_json_path = input_root / item["case_json"]["path"]
        if _sha256(case_json_path) != item["case_json"]["sha256"]:
            raise RuntimeError(f"case JSON hash mismatch: {case_json_path}")
        record = _load_json(case_json_path)
        arrays_path = input_root / record["arrays"]["path"]
        if _sha256(arrays_path) != record["arrays"]["sha256"]:
            raise RuntimeError(f"case NPZ hash mismatch: {arrays_path}")
        spec = record["spec"]
        if (
            spec["group"] != "basic"
            or spec["spatial_label"] != "S2"
            or spec["steps_per_cycle"] != 128
            or spec["case_id"] not in {"A1", "S1"}
        ):
            raise RuntimeError(f"basic-case identity drift: {spec}")
        if (spec["de"], spec["thickness_ratio"], spec["case_id"]) in HOLDOUT_SIGNATURES:
            raise RuntimeError("holdout leakage into basic source records")
        record["_source"] = {
            "case_json": case_json_path.relative_to(input_root).as_posix(),
            "case_json_sha256": item["case_json"]["sha256"],
            "arrays": arrays_path.relative_to(input_root).as_posix(),
            "arrays_sha256": record["arrays"]["sha256"],
        }
        records.append(record)
    expected_pairs = {
        (de, thickness, case_id)
        for de in (0.02, 0.2, 2.0)
        for thickness in (0.1, 0.3, 0.6)
        for case_id in ("A1", "S1")
    }
    actual_pairs = {
        (record["spec"]["de"], record["spec"]["thickness_ratio"], record["spec"]["case_id"])
        for record in records
    }
    if actual_pairs != expected_pairs:
        raise RuntimeError("the 3x3 A1/S1 source grid is incomplete or changed")
    return records, summary


def _extract_field(
    input_root: Path, record: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, complex, complex, dict[str, Any]]:
    steps = int(record["spec"]["steps_per_cycle"])
    arrays_path = input_root / record["arrays"]["path"]
    with np.load(arrays_path) as arrays:
        x_nodes = np.asarray(arrays["x_interface_nodes"], dtype=np.float64)
        nodes = len(x_nodes)
        raw_traction = np.asarray(
            arrays["endocardium_ecm_traction_two_cycles"], dtype=np.float64
        ).reshape(nodes, 2, -1)
        if not np.all(np.isfinite(raw_traction)):
            raise RuntimeError(f"non-finite source traction: {arrays_path}")
        recomputed = _harmonic_coefficient(raw_traction, steps)
        stored = np.asarray(
            arrays["endocardium_ecm_traction_fundamental_real"],
            dtype=np.float64,
        ) + 1j * np.asarray(
            arrays["endocardium_ecm_traction_fundamental_imag"],
            dtype=np.float64,
        )
        recompute_error = float(np.max(np.abs(recomputed - stored)))
        if recompute_error > RECOMPUTE_TOLERANCE:
            raise RuntimeError(
                f"stored traction fundamental mismatch {recompute_error}: {arrays_path}"
            )
        shortening_pair = np.asarray(
            arrays["shortening_fundamental_real_imag"], dtype=np.float64
        )
        shortening_stored = complex(shortening_pair[0], shortening_pair[1])
        shortening_recomputed = complex(
            _harmonic_coefficient(
                np.asarray(arrays["limited_shortening_two_cycles"], dtype=np.float64),
                steps,
            )
        )
        shortening_error = abs(shortening_recomputed - shortening_stored)
        if shortening_error > RECOMPUTE_TOLERANCE:
            raise RuntimeError(
                f"stored shortening fundamental mismatch {shortening_error}: {arrays_path}"
            )
    return (
        x_nodes,
        stored[:, 1],
        _activation_coefficient(record),
        shortening_stored,
        {
            "traction_fundamental_max_absolute_recompute_error": recompute_error,
            "shortening_fundamental_absolute_recompute_error": shortening_error,
        },
    )


def _field_description(
    x_nodes: np.ndarray,
    values: np.ndarray,
    activation: complex,
    target_x: tuple[float, ...],
) -> dict[str, Any]:
    weights = _trapezoidal_weights(x_nodes)
    point_records = []
    for x_value in target_x:
        coefficient = _interpolate_complex(x_nodes, values, x_value)
        point_records.append(
            {
                "x_over_L": x_value,
                "coefficient": _complex_record(coefficient, activation),
                "exact_native_node": _exact_node(x_nodes, x_value),
            }
        )
    return {
        "common_points": point_records,
        "weighted_complex_amplitude_rms": _weighted_complex_rms(values, weights),
        "peak": _peak_record(x_nodes, values, activation),
        "weight_sum": float(np.sum(weights)),
    }


def _point_comparison(
    x_nodes: np.ndarray,
    values_a: np.ndarray,
    values_s: np.ndarray,
    activation_a: complex,
    activation_s: complex,
    target_x: tuple[float, ...],
    s_scale: float,
) -> list[dict[str, Any]]:
    records = []
    for x_value in target_x:
        value_a = _interpolate_complex(x_nodes, values_a, x_value)
        value_s = _interpolate_complex(x_nodes, values_s, x_value)
        value_s_scaled = s_scale * value_s
        record_a = _complex_record(value_a, activation_a)
        record_s = _complex_record(value_s, activation_s)
        record_s_scaled = _complex_record(value_s_scaled, activation_s)
        records.append(
            {
                "x_over_L": x_value,
                "exact_native_node": _exact_node(x_nodes, x_value),
                "raw": {
                    "A1": record_a,
                    "S1": record_s,
                    "S1_minus_A1": _difference_record(value_s - value_a),
                    "S1_over_A1_amplitude": _safe_ratio(
                        abs(value_s), abs(value_a)
                    ),
                    "absolute_phase_difference_deg": _phase_difference_deg(
                        record_a, record_s
                    ),
                },
                "equal_active_power": {
                    "A1": record_a,
                    "scaled_S1": record_s_scaled,
                    "scaled_S1_minus_A1": _difference_record(
                        value_s_scaled - value_a
                    ),
                    "scaled_S1_over_A1_amplitude": _safe_ratio(
                        abs(value_s_scaled), abs(value_a)
                    ),
                    "absolute_phase_difference_deg": _phase_difference_deg(
                        record_a, record_s_scaled
                    ),
                },
            }
        )
    return records


def _macro_comparison(
    shortening_a: complex,
    shortening_s: complex,
    activation_a: complex,
    activation_s: complex,
    s_scale: float,
) -> dict[str, Any]:
    scaled_s = s_scale * shortening_s
    record_a = _complex_record(shortening_a, activation_a)
    record_s = _complex_record(shortening_s, activation_s)
    record_scaled_s = _complex_record(scaled_s, activation_s)
    return {
        "raw": {
            "A1": record_a,
            "S1": record_s,
            "S1_minus_A1": _difference_record(shortening_s - shortening_a),
            "S1_over_A1_amplitude": _safe_ratio(abs(shortening_s), abs(shortening_a)),
            "absolute_phase_difference_deg": _phase_difference_deg(record_a, record_s),
        },
        "equal_active_power": {
            "A1": record_a,
            "scaled_S1": record_scaled_s,
            "scaled_S1_minus_A1": _difference_record(scaled_s - shortening_a),
            "scaled_S1_over_A1_amplitude": _safe_ratio(
                abs(scaled_s), abs(shortening_a)
            ),
            "absolute_phase_difference_deg": _phase_difference_deg(
                record_a, record_scaled_s
            ),
            "interpretation": "scaled S1 macro shortening is a consequence of equal-active-power algebraic normalization; it is not constrained to equal A1 motion",
        },
    }


def analyze(repo_root: Path, output_path: Path, code_version: str) -> int:
    start = time.perf_counter()
    input_root = (repo_root / EXPECTED_INPUT).resolve()
    expected_output = (repo_root / EXPECTED_OUTPUT).resolve()
    if output_path.resolve() != expected_output:
        raise RuntimeError("output boundary mismatch")
    if output_path.exists():
        raise RuntimeError("create-only field comparison already exists")
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(name) != "1":
            raise RuntimeError(f"single-CPU environment drift: {name}")

    records, source_summary = _load_basic_records(input_root)
    source_audits: list[dict[str, Any]] = []
    group_results: list[dict[str, Any]] = []
    for de in (0.02, 0.2, 2.0):
        for thickness in (0.1, 0.3, 0.6):
            record_a = next(
                record
                for record in records
                if record["spec"]["de"] == de
                and record["spec"]["thickness_ratio"] == thickness
                and record["spec"]["case_id"] == "A1"
            )
            record_s = next(
                record
                for record in records
                if record["spec"]["de"] == de
                and record["spec"]["thickness_ratio"] == thickness
                and record["spec"]["case_id"] == "S1"
            )
            x_a, field_a, activation_a, shortening_a, audit_a = _extract_field(
                input_root, record_a
            )
            x_s, field_s, activation_s, shortening_s, audit_s = _extract_field(
                input_root, record_s
            )
            if not np.allclose(x_a, x_s, rtol=0.0, atol=1.0e-13):
                raise RuntimeError("A1/S1 native interface grids differ")
            weights = _trapezoidal_weights(x_a)
            power_a = _active_work(record_a)
            power_s = _active_work(record_s)
            if power_a <= POWER_FLOOR or power_s <= POWER_FLOOR:
                raise RuntimeError("active work is non-positive or near zero; equal-power scale disabled")
            scale = math.sqrt(power_a / power_s)
            raw_difference_rms = _weighted_complex_rms(field_s - field_a, weights)
            scaled_field_s = scale * field_s
            scaled_difference_rms = _weighted_complex_rms(
                scaled_field_s - field_a, weights
            )
            rms_a = _weighted_complex_rms(field_a, weights)
            rms_s = _weighted_complex_rms(field_s, weights)
            rms_scaled_s = _weighted_complex_rms(scaled_field_s, weights)
            points = _point_comparison(
                x_a,
                field_a,
                field_s,
                activation_a,
                activation_s,
                COMMON_X_OVER_L,
                scale,
            )
            group_results.append(
                {
                    "de": de,
                    "thickness_ratio_H": thickness,
                    "source_cases": {
                        "A1": record_a["spec"]["key"],
                        "S1": record_s["spec"]["key"],
                    },
                    "active_work": {
                        "P_A1": power_a,
                        "P_S1": power_s,
                        "equal_power_S1_scale_sqrt_P_A1_over_P_S1": scale,
                        "scaled_S1_power_algebraic": scale * scale * power_s,
                        "power_floor": POWER_FLOOR,
                    },
                    "common_point_comparisons": points,
                    "full_field_y_traction": {
                        "raw": {
                            "A1": _field_description(
                                x_a, field_a, activation_a, COMMON_X_OVER_L
                            ),
                            "S1": _field_description(
                                x_s, field_s, activation_s, COMMON_X_OVER_L
                            ),
                            "S1_minus_A1_weighted_complex_rms": raw_difference_rms,
                            "S1_over_A1_weighted_rms": _safe_ratio(rms_s, rms_a),
                            "difference_rms_over_A1_rms": _safe_ratio(
                                raw_difference_rms, rms_a
                            ),
                        },
                        "equal_active_power": {
                            "A1_weighted_complex_amplitude_rms": rms_a,
                            "scaled_S1_weighted_complex_amplitude_rms": rms_scaled_s,
                            "scaled_S1_minus_A1_weighted_complex_rms": scaled_difference_rms,
                            "scaled_S1_over_A1_weighted_rms": _safe_ratio(
                                rms_scaled_s, rms_a
                            ),
                            "difference_rms_over_A1_rms": _safe_ratio(
                                scaled_difference_rms, rms_a
                            ),
                            "A1_peak": _peak_record(x_a, field_a, activation_a),
                            "scaled_S1_peak": _peak_record(
                                x_s, scaled_field_s, activation_s
                            ),
                        },
                    },
                    "macro_shortening_fundamental": _macro_comparison(
                        shortening_a,
                        shortening_s,
                        activation_a,
                        activation_s,
                        scale,
                    ),
                    "interpretation_boundary": {
                        "raw_comparison": "uses the actual activation amplitude in both source simulations but does not impose equal active work",
                        "equal_active_power": "positive algebraic scaling of the linear S1 complex response by sqrt(P_A1/P_S1); no new solve",
                        "not_equal_motion_and_power": True,
                    },
                }
            )
            source_audits.extend(
                (
                    {"case": record_a["spec"]["key"], **record_a["_source"], **audit_a},
                    {"case": record_s["spec"]["key"], **record_s["_source"], **audit_s},
                )
            )
            if time.perf_counter() - start > COMPUTE_BUDGET_SECONDS:
                raise RuntimeError("120-second post-processing compute budget exceeded")

    raw_rms_ratios = [
        group["full_field_y_traction"]["raw"]["S1_over_A1_weighted_rms"]["value"]
        for group in group_results
    ]
    equal_power_rms_ratios = [
        group["full_field_y_traction"]["equal_active_power"][
            "scaled_S1_over_A1_weighted_rms"
        ]["value"]
        for group in group_results
    ]
    equal_power_motion_ratios = [
        group["macro_shortening_fundamental"]["equal_active_power"][
            "scaled_S1_over_A1_amplitude"
        ]["value"]
        for group in group_results
    ]
    scales = [
        group["active_work"]["equal_power_S1_scale_sqrt_P_A1_over_P_S1"]
        for group in group_results
    ]
    payload = {
        "schema": SCHEMA,
        "status": "COMPLETED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "existing_data_postprocessing_not_independent_validation",
        "code_version_at_analysis": code_version,
        "analyzer": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "source": {
            "summary_path": (EXPECTED_INPUT / "summary.json").as_posix(),
            "summary_sha256": _sha256(input_root / "summary.json"),
            "source_status": source_summary["status"],
            "basic_case_count": len(records),
            "resolution_case_count_used": 0,
            "new_fem_case_count": 0,
            "holdout_case_count_used": 0,
            "source_audits": source_audits,
        },
        "definitions": {
            "field": "endocardium-ECM interface traction y component",
            "complex_fundamental": "2/N times first rFFT coefficient after removing the temporal mean over the first cycle",
            "common_x_over_L": list(COMMON_X_OVER_L),
            "interpolation": "piecewise-linear interpolation of real and imaginary complex coefficients separately; exact_native_node is also reported",
            "weights": "trapezoidal nodal quadrature on the full x/L interval; endpoints receive half adjacent spacing and interior nodes half the sum of adjacent spacings",
            "weighted_complex_amplitude_rms": "sqrt(sum_i w_i |q_i|^2 / sum_i w_i)",
            "weighted_complex_difference_rms": "sqrt(sum_i w_i |q_S_i-q_A_i|^2 / sum_i w_i)",
            "equal_active_power_scale": "g=sqrt(P_A1/P_S1), applied to the S1 linear complex response; g^2 P_S1=P_A1 algebraically",
            "amplitude_floor": AMPLITUDE_FLOOR,
            "power_floor": POWER_FLOOR,
            "near_zero_rule": "ratios are omitted when the denominator is at or below the amplitude floor; phase is omitted when response or activation amplitude is at or below the floor",
        },
        "groups": group_results,
        "aggregate": {
            "raw_S1_over_A1_weighted_field_rms_range": [
                min(raw_rms_ratios),
                max(raw_rms_ratios),
            ],
            "equal_power_scaled_S1_over_A1_weighted_field_rms_range": [
                min(equal_power_rms_ratios),
                max(equal_power_rms_ratios),
            ],
            "equal_power_scaled_S1_over_A1_macro_shortening_amplitude_range": [
                min(equal_power_motion_ratios),
                max(equal_power_motion_ratios),
            ],
            "equal_power_scale_range": [min(scales), max(scales)],
            "all_source_hashes_match": True,
            "maximum_traction_fundamental_recompute_error": max(
                audit["traction_fundamental_max_absolute_recompute_error"]
                for audit in source_audits
            ),
            "maximum_shortening_fundamental_recompute_error": max(
                audit["shortening_fundamental_absolute_recompute_error"]
                for audit in source_audits
            ),
            "postprocessing_elapsed_seconds": time.perf_counter() - start,
            "compute_budget_seconds": COMPUTE_BUDGET_SECONDS,
        },
        "claim_boundary": {
            "no_new_fem": True,
            "holdouts_remain_unrun": True,
            "not_equal_motion_and_equal_power": True,
            "not_a_novelty_test": True,
            "not_formal_figure2_certification": True,
            "not_physiological_or_EFE_validation": True,
        },
    }
    if payload["aggregate"]["postprocessing_elapsed_seconds"] > COMPUTE_BUDGET_SECONDS:
        raise RuntimeError("120-second post-processing compute budget exceeded before write")
    _create_json(output_path, payload)
    print(
        "FIELD_COMPARISON_DONE "
        f"groups={len(group_results)} seconds={payload['aggregate']['postprocessing_elapsed_seconds']:.6f} "
        f"output={output_path}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-version", required=True)
    arguments = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if arguments.input_root.resolve() != (repo_root / EXPECTED_INPUT).resolve():
        raise RuntimeError("input boundary mismatch")
    return analyze(repo_root, arguments.output, arguments.code_version)


if __name__ == "__main__":
    raise SystemExit(main())
