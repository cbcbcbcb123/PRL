"""Run the preregistered eight-endpoint transverse-notch test.

This bounded runner reuses the accepted Paper 2 production model and the
side-effect-free case/observable helpers from the first science pilot.  It
does not modify production APIs, does not run the four locked holdouts, and
does not fit or scan parameters after seeing results.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np

import run_paper2_science_pilot_v01 as pilot


SCHEMA = "paper2_transverse_notch_v01"
CASE_SCHEMA = "paper2_transverse_notch_case_v01"
SUMMARY_SCHEMA = "paper2_transverse_notch_summary_v01"
EXPECTED_PROJECT_ROOT = Path("/workspace")
EXPECTED_OUTPUT_ROOT = Path("/output")
HOST_OUTPUT_RELATIVE = "results/paper2_transverse_notch/v01_20260905"
PREDICTION_COMMIT = "9842b3bfab7f11e947d0c355fa8b0202a368138f"
PREDICTION_PATH = Path(
    "results/paper2_science_pilot/v01_20260905/science_brief.md"
)
PREDICTION_SHA256 = (
    "097c60e179136f02c30511a5f60e7fd5f852b63df1038641e1cce46b1f7465f2"
)
PRIOR_SUMMARY_PATH = Path(
    "results/paper2_science_pilot/v01_20260905/numerical/summary.json"
)
PRIOR_SUMMARY_SHA256 = (
    "8b6ee96662319efa541c187ec3e063484da9979e1710f0ee6c8db6b9f6da6122"
)
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
EXPECTED_CONTAINER_NAME = "prl-paper2-transverse-notch-v01-20260905"
EXPECTED_SOURCE_HASHES = {
    "src/paper2_hybrid/config.py": (
        "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe"
    ),
    "src/paper2_hybrid/model.py": (
        "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800"
    ),
    "src/paper2_hybrid/numerics.py": (
        "620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4"
    ),
    "src/paper2_hybrid/validation.py": (
        "6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5"
    ),
    "scripts/run_paper2_science_pilot_v01.py": (
        "2675b91436dacc43ed9ad3121b8a24dfd8826f93440db184bbd7abad597002e7"
    ),
}
BATCH_WALL_BUDGET_SECONDS = 900.0
PROJECT_WALL_BUDGET_SECONDS = 7200.0
AMPLITUDE_FLOOR = 1.0e-12
CIDFILE_NAME = "container.cid"


def _case_specs() -> tuple[pilot.CaseSpec, ...]:
    cases: list[pilot.CaseSpec] = []
    for thickness_ratio in (0.210, 0.260, 0.310):
        for spatial_label in ("S2", "S3"):
            cases.append(
                pilot._case(
                    "transverse_notch",
                    0.2,
                    thickness_ratio,
                    "A1",
                    "uniform",
                    spatial_label,
                    128,
                )
            )
    for spatial_label in ("S2", "S3"):
        cases.append(
            pilot._case(
                "transverse_notch",
                0.2,
                0.260,
                "S1",
                "S1",
                spatial_label,
                128,
            )
        )
    return tuple(cases)


CASE_SPECS = _case_specs()


def _complex_record(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "amplitude": float(abs(value)),
    }


def _relative_phase_record(
    value: complex,
    activation_coefficient: complex,
    threshold: float,
) -> dict[str, Any]:
    interpretable = (
        abs(value) > threshold and abs(activation_coefficient) > AMPLITUDE_FLOOR
    )
    if not interpretable:
        return {
            "threshold": float(threshold),
            "interpretable": False,
            "relative_to_activation_rad": None,
            "relative_to_activation_deg": None,
        }
    phase = float(np.angle(value / activation_coefficient))
    return {
        "threshold": float(threshold),
        "interpretable": True,
        "relative_to_activation_rad": phase,
        "relative_to_activation_deg": math.degrees(phase),
    }


def _exact_p1_spatial_modes(
    x_values: np.ndarray,
    field_values: np.ndarray,
    length: float,
) -> dict[str, Any]:
    """Integrate c0/cos/sin exactly for the P1 interpolant on each segment."""

    x_nodes = np.asarray(x_values, dtype=np.float64)
    field = np.asarray(field_values, dtype=np.complex128)
    if x_nodes.ndim != 1 or field.ndim != 1 or x_nodes.shape != field.shape:
        raise ValueError("spatial Fourier inputs must be matching one-dimensional arrays")
    if len(x_nodes) < 2 or not np.all(np.isfinite(x_nodes)):
        raise ValueError("spatial Fourier coordinates are invalid")
    if not np.all(np.isfinite(field.real)) or not np.all(np.isfinite(field.imag)):
        raise ValueError("spatial Fourier field is non-finite")
    segment_widths = np.diff(x_nodes)
    if not np.all(segment_widths > 0.0):
        raise ValueError("spatial Fourier coordinates are not strictly increasing")
    coordinate_tolerance = 5.0e-12 * max(1.0, abs(length))
    if not math.isclose(
        float(x_nodes[0]), -0.5 * length, rel_tol=0.0, abs_tol=coordinate_tolerance
    ):
        raise ValueError("left interface coordinate does not match -L/2")
    if not math.isclose(
        float(x_nodes[-1]), 0.5 * length, rel_tol=0.0, abs_tol=coordinate_tolerance
    ):
        raise ValueError("right interface coordinate does not match L/2")

    slopes = np.diff(field) / segment_widths
    intercepts = field[:-1] - slopes * x_nodes[:-1]
    left = x_nodes[:-1]
    right = x_nodes[1:]
    wavenumber = 2.0 * math.pi / length

    integral_constant = np.sum(
        0.5 * (field[:-1] + field[1:]) * segment_widths
    )
    primitive_cos = lambda x: np.sin(wavenumber * x) / wavenumber
    primitive_x_cos = lambda x: (
        x * np.sin(wavenumber * x) / wavenumber
        + np.cos(wavenumber * x) / (wavenumber**2)
    )
    primitive_sin = lambda x: -np.cos(wavenumber * x) / wavenumber
    primitive_x_sin = lambda x: (
        -x * np.cos(wavenumber * x) / wavenumber
        + np.sin(wavenumber * x) / (wavenumber**2)
    )
    integral_cos = np.sum(
        slopes * (primitive_x_cos(right) - primitive_x_cos(left))
        + intercepts * (primitive_cos(right) - primitive_cos(left))
    )
    integral_sin = np.sum(
        slopes * (primitive_x_sin(right) - primitive_x_sin(left))
        + intercepts * (primitive_sin(right) - primitive_sin(left))
    )

    c0 = complex(integral_constant / length)
    c_cos = complex(2.0 * integral_cos / length)
    c_sin = complex(2.0 * integral_sin / length)
    b1 = math.sqrt((abs(c_cos) ** 2 + abs(c_sin) ** 2) / 2.0)
    endpoint_mismatch = abs(field[-1] - field[0])
    endpoint_scale = max(float(np.max(np.abs(field))), AMPLITUDE_FLOOR)
    uniform_spacing_error = float(
        np.max(np.abs(segment_widths - np.mean(segment_widths)))
        / max(float(np.mean(segment_widths)), np.finfo(np.float64).tiny)
    )
    return {
        "definition": {
            "field": "time-fundamental complex y traction on the endocardium-ECM interface",
            "integration": "exact analytic integration of the native piecewise-linear interpolant on every interface segment",
            "c0": "L^-1 integral f dx",
            "c_cos": "2 L^-1 integral f cos(2 pi x/L) dx",
            "c_sin": "2 L^-1 integral f sin(2 pi x/L) dx",
            "B1": "sqrt((|c_cos|^2+|c_sin|^2)/2)",
        },
        "c0": _complex_record(c0),
        "c_cos": _complex_record(c_cos),
        "c_sin": _complex_record(c_sin),
        "B1": float(b1),
        "coordinate_domain": [float(x_nodes[0]), float(x_nodes[-1])],
        "node_count": int(len(x_nodes)),
        "uniform_spacing_relative_error": uniform_spacing_error,
        "periodic_endpoint_check": {
            "absolute_complex_mismatch": float(endpoint_mismatch),
            "relative_to_peak_field": float(endpoint_mismatch / endpoint_scale),
            "used_as_assumption": False,
            "note": "the finite-interval P1 integral remains the reported estimator even if endpoint samples differ",
        },
        "complex_values": {"c0": c0, "c_cos": c_cos, "c_sin": c_sin},
    }


def _self_test() -> dict[str, Any]:
    length = 1.0
    segments = 32
    x_nodes = np.linspace(-0.5 * length, 0.5 * length, segments + 1)
    wavenumber = 2.0 * math.pi / length
    constant = 2.3 - 0.7j
    cosine_amplitude = 1.2 + 0.4j
    sine_amplitude = -0.8 + 0.3j
    field = (
        constant
        + cosine_amplitude * np.cos(wavenumber * x_nodes)
        + sine_amplitude * np.sin(wavenumber * x_nodes)
    )
    modes = _exact_p1_spatial_modes(x_nodes, field, length)
    values = modes["complex_values"]
    p1_hat_factor = float(np.sinc(1.0 / segments) ** 2)
    spatial_errors = {
        "constant": abs(values["c0"] - constant),
        "cosine": abs(values["c_cos"] - cosine_amplitude * p1_hat_factor),
        "sine": abs(values["c_sin"] - sine_amplitude * p1_hat_factor),
    }
    temporal_steps = 128
    theta = 2.0 * math.pi * np.arange(temporal_steps) / temporal_steps
    temporal_cosine = complex(pilot._harmonic_coefficient(np.cos(theta), temporal_steps))
    temporal_sine = complex(pilot._harmonic_coefficient(np.sin(theta), temporal_steps))
    temporal_constant = complex(
        pilot._harmonic_coefficient(np.full(temporal_steps, 3.0), temporal_steps)
    )
    temporal_errors = {
        "cosine": abs(temporal_cosine - 1.0),
        "sine": abs(temporal_sine + 1.0j),
        "constant": abs(temporal_constant),
    }
    tolerance = 2.0e-13
    passed = (
        max(spatial_errors.values()) <= tolerance
        and max(temporal_errors.values()) <= tolerance
    )
    return {
        "pass": bool(passed),
        "tolerance": tolerance,
        "spatial_exact_p1_errors": {
            key: float(value) for key, value in spatial_errors.items()
        },
        "temporal_fundamental_errors": {
            key: float(value) for key, value in temporal_errors.items()
        },
        "p1_hat_factor": p1_hat_factor,
        "normalization_checked": ["constant", "cos(2pi x/L)", "sin(2pi x/L)"],
    }


def _validate_case_plan() -> None:
    if len(CASE_SPECS) != 8:
        raise RuntimeError(f"expected 8 endpoints, got {len(CASE_SPECS)}")
    if len({spec.key for spec in CASE_SPECS}) != 8:
        raise RuntimeError("case keys are not unique")
    actual = {
        (spec.case_id, spec.thickness_ratio, spec.spatial_label)
        for spec in CASE_SPECS
    }
    expected = {
        (case_id, thickness, spatial)
        for case_id, thicknesses in (("A1", (0.210, 0.260, 0.310)), ("S1", (0.260,)))
        for thickness in thicknesses
        for spatial in ("S2", "S3")
    }
    if actual != expected:
        raise RuntimeError(f"case plan drift: {sorted(actual)}")
    for spec in CASE_SPECS:
        if spec.de != 0.2 or spec.steps_per_cycle != 128 or spec.activation_peak != 0.10:
            raise RuntimeError(f"fixed parameter drift in {spec.key}")
        signature = (spec.de, spec.thickness_ratio, spec.case_id)
        if signature in pilot.HOLDOUT_SIGNATURES:
            raise RuntimeError(f"holdout leakage into plan: {spec.key}")


def _verify_frozen_inputs(repo_root: Path, code_version: str) -> dict[str, Any]:
    if code_version != PREDICTION_COMMIT:
        raise RuntimeError(
            f"prediction commit drift: {code_version!r} != {PREDICTION_COMMIT!r}"
        )
    prediction_hash = pilot._sha256(repo_root / PREDICTION_PATH)
    if prediction_hash != PREDICTION_SHA256:
        raise RuntimeError(
            f"prediction brief hash drift: {prediction_hash} != {PREDICTION_SHA256}"
        )
    prior_summary_hash = pilot._sha256(repo_root / PRIOR_SUMMARY_PATH)
    if prior_summary_hash != PRIOR_SUMMARY_SHA256:
        raise RuntimeError(
            f"prior summary hash drift: {prior_summary_hash} != {PRIOR_SUMMARY_SHA256}"
        )
    with (repo_root / PRIOR_SUMMARY_PATH).open("r", encoding="utf-8") as handle:
        prior_summary = json.load(handle)
    if prior_summary.get("case_count") != 26:
        raise RuntimeError("prior batch case count is not the frozen 26")
    if prior_summary.get("holdouts") != "LOCKED_NOT_RUN":
        raise RuntimeError("prior holdout status is not LOCKED_NOT_RUN")
    prior_elapsed = float(prior_summary["total_elapsed_seconds"])
    if prior_elapsed >= PROJECT_WALL_BUDGET_SECONDS:
        raise RuntimeError("project cumulative wall budget was already exhausted")

    source_hashes = {
        path: pilot._sha256(repo_root / path) for path in EXPECTED_SOURCE_HASHES
    }
    if source_hashes != EXPECTED_SOURCE_HASHES:
        raise RuntimeError(
            f"production source hash drift: actual={source_hashes}, expected={EXPECTED_SOURCE_HASHES}"
        )
    return {
        "prediction_commit": code_version,
        "prediction_path": PREDICTION_PATH.as_posix(),
        "prediction_sha256": prediction_hash,
        "prior_summary_path": PRIOR_SUMMARY_PATH.as_posix(),
        "prior_summary_sha256": prior_summary_hash,
        "prior_completed_case_count": 26,
        "prior_elapsed_seconds": prior_elapsed,
        "prior_holdouts": "LOCKED_NOT_RUN",
        "production_source_hashes": source_hashes,
    }


def _check_prediction_unchanged(repo_root: Path) -> None:
    current = pilot._sha256(repo_root / PREDICTION_PATH)
    if current != PREDICTION_SHA256:
        raise RuntimeError(
            f"prediction brief changed during execution: {current} != {PREDICTION_SHA256}"
        )


def _mode_complex(case_record: dict[str, Any], name: str) -> complex:
    entry = case_record["spatial_modes"][name]
    return complex(entry["real"], entry["imag"])


def _comparison_and_gates(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_point = {
        (
            record["spec"]["case_id"],
            float(record["spec"]["thickness_ratio"]),
            record["spec"]["spatial_label"],
        ): record
        for record in records
    }
    point_errors: dict[str, Any] = {}
    for case_id, thickness in (
        ("A1", 0.210),
        ("A1", 0.260),
        ("A1", 0.310),
        ("S1", 0.260),
    ):
        coarse = by_point[(case_id, thickness, "S2")]
        fine = by_point[(case_id, thickness, "S3")]
        differences = {
            name: abs(_mode_complex(fine, name) - _mode_complex(coarse, name))
            for name in ("c0", "c_cos", "c_sin")
        }
        b1_error = math.sqrt(
            (differences["c_cos"] ** 2 + differences["c_sin"] ** 2) / 2.0
        )
        key = f"{case_id}__h{pilot._number_token(thickness)}"
        point_errors[key] = {
            "case_id": case_id,
            "thickness_ratio": thickness,
            "S2_case_key": coarse["spec"]["key"],
            "S3_case_key": fine["spec"]["key"],
            "absolute_complex_error": {
                "c0": float(differences["c0"]),
                "c_cos": float(differences["c_cos"]),
                "c_sin": float(differences["c_sin"]),
                "B1_vector": float(b1_error),
            },
            "error_role": "S2-S3 absolute-difference proxy at this physical point; not a rigorous error bound",
        }

    center = by_point[("A1", 0.260, "S3")]
    center_c0 = _mode_complex(center, "c0")
    center_amplitude = abs(center_c0)
    center_error = point_errors["A1__h0p26"]["absolute_complex_error"]["c0"]
    side_records: list[dict[str, Any]] = []
    for thickness in (0.210, 0.310):
        side = by_point[("A1", thickness, "S3")]
        side_amplitude = abs(_mode_complex(side, "c0"))
        side_error = point_errors[
            f"A1__h{pilot._number_token(thickness)}"
        ]["absolute_complex_error"]["c0"]
        difference = side_amplitude - center_amplitude
        combined_error = side_error + center_error
        pass_inequality = difference > 2.0 * combined_error
        pass_floor = side_amplitude > AMPLITUDE_FLOOR and difference > AMPLITUDE_FLOOR
        fail_inequality = difference < -2.0 * combined_error
        fail_floor = -difference > AMPLITUDE_FLOOR
        side_records.append(
            {
                "side_thickness_ratio": thickness,
                "A_side": float(side_amplitude),
                "A_center": float(center_amplitude),
                "D_side_minus_center": float(difference),
                "e_side": float(side_error),
                "e_center": float(center_error),
                "E_sum": float(combined_error),
                "two_E": float(2.0 * combined_error),
                "pass_inequality_D_gt_2E": bool(pass_inequality),
                "pass_floor": bool(pass_floor),
                "fail_inequality_D_lt_minus_2E": bool(fail_inequality),
                "fail_floor": bool(fail_floor),
            }
        )
    if all(item["pass_inequality_D_gt_2E"] and item["pass_floor"] for item in side_records):
        position_status = "PASS"
    elif any(item["fail_inequality_D_lt_minus_2E"] and item["fail_floor"] for item in side_records):
        position_status = "FAIL"
    else:
        position_status = "INCONCLUSIVE"

    s1_fine = by_point[("S1", 0.260, "S3")]
    s1_b1 = float(s1_fine["spatial_modes"]["B1"])
    s1_error = point_errors["S1__h0p26"]["absolute_complex_error"]["B1_vector"]
    heterogeneous_pass = s1_b1 > 5.0 * s1_error and s1_b1 > AMPLITUDE_FLOOR
    heterogeneous_status = "PASS" if heterogeneous_pass else "INCONCLUSIVE"

    phase_diagnostics: dict[str, Any] = {}
    for case_id, thickness in (
        ("A1", 0.210),
        ("A1", 0.260),
        ("A1", 0.310),
        ("S1", 0.260),
    ):
        fine = by_point[(case_id, thickness, "S3")]
        activation = complex(
            fine["activation_fundamental"]["real"],
            fine["activation_fundamental"]["imag"],
        )
        errors = point_errors[
            f"{case_id}__h{pilot._number_token(thickness)}"
        ]["absolute_complex_error"]
        phase_diagnostics[f"{case_id}__h{pilot._number_token(thickness)}"] = {
            mode: _relative_phase_record(
                _mode_complex(fine, mode),
                activation,
                max(AMPLITUDE_FLOOR, 5.0 * float(errors[mode])),
            )
            for mode in ("c0", "c_cos", "c_sin")
        }

    candidate_retained = position_status == "PASS" and heterogeneous_status == "PASS"
    if candidate_retained:
        candidate_status = "RETAINED_AS_EXPLORATORY_REDUCED_CANDIDATE"
    elif position_status == "FAIL":
        candidate_status = "NOT_RETAINED_POSITION_GATE_FAILED"
    else:
        candidate_status = "NOT_RETAINED_INCONCLUSIVE"
    return {
        "pointwise_S2_S3_error_proxies": point_errors,
        "position_gate": {
            "status": position_status,
            "quantity": "A1 S3 amplitude |c0| at H=0.210, 0.260, 0.310",
            "center_thickness_ratio": 0.260,
            "floor": AMPLITUDE_FLOOR,
            "sides": side_records,
            "interpretation": "three-point exploratory notch test only; not certification of a continuous minimum",
        },
        "heterogeneous_channel_gate": {
            "status": heterogeneous_status,
            "quantity": "S1 S3 B1 at H=0.260",
            "B1_S3": s1_b1,
            "e1_S2_S3_vector": float(s1_error),
            "five_e1": float(5.0 * s1_error),
            "floor": AMPLITUDE_FLOOR,
            "pass_condition": "B1_S3 > 5*e1 and B1_S3 > floor",
        },
        "phase_diagnostics": phase_diagnostics,
        "candidate_status": candidate_status,
        "candidate_retained": candidate_retained,
    }


def _write_failure_summary(output_root: Path, error: BaseException) -> None:
    summary_path = output_root / "summary.json"
    if summary_path.exists():
        return
    completed_case_json = sorted((output_root / "cases").glob("*.json")) if (output_root / "cases").exists() else []
    payload = {
        "schema": SUMMARY_SCHEMA,
        "status": "ABORTED_FAIL_CLOSED",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed_case_count": len(completed_case_json),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "holdouts": "LOCKED_NOT_RUN",
        "claim_boundary": {
            "no_scientific_gate_result_after_abort": True,
            "no_automatic_retry_or_parameter_adjustment": True,
        },
    }
    pilot._create_json(summary_path, payload)


def run(output_root: Path, code_version: str) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root.resolve() != EXPECTED_PROJECT_ROOT.resolve():
        raise RuntimeError(
            f"project mount drift: {repo_root.resolve()} != {EXPECTED_PROJECT_ROOT.resolve()}"
        )
    if output_root.resolve() != EXPECTED_OUTPUT_ROOT.resolve():
        raise RuntimeError(
            f"output mount drift: {output_root.resolve()} != {EXPECTED_OUTPUT_ROOT.resolve()}"
        )
    if not output_root.is_dir():
        raise RuntimeError("output mount does not exist")
    unexpected_entries = [
        item.name for item in output_root.iterdir() if item.name != CIDFILE_NAME
    ]
    if unexpected_entries:
        raise RuntimeError(f"create-only output root is not empty: {unexpected_entries}")
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-CPU environment drift: {variable}={os.environ.get(variable)!r}")
    if os.environ.get("PAPER2_IMAGE_ID") != EXPECTED_IMAGE_ID:
        raise RuntimeError("container image identity drift")
    if os.environ.get("PAPER2_CONTAINER_NAME") != EXPECTED_CONTAINER_NAME:
        raise RuntimeError("container name drift")

    _validate_case_plan()
    self_test = _self_test()
    if not self_test["pass"]:
        raise RuntimeError(f"Fourier normalization self-test failed: {self_test}")
    frozen_inputs = _verify_frozen_inputs(repo_root, code_version)

    from paper2_hybrid.config import ACTIVE_CONFIG
    from paper2_hybrid.model import build_system
    from paper2_hybrid.numerics import endpoint_structural_gate, simulate_endpoint
    from paper2_hybrid.validation import (
        global_structural_checks,
        interface_action_reaction_manufactured_check,
    )
    import dolfinx
    import scipy

    manufactured = interface_action_reaction_manufactured_check()
    if not manufactured["pass"]:
        raise RuntimeError("interface action-reaction manufactured check failed")

    start = time.perf_counter()
    manifest = {
        "schema": SCHEMA,
        "status": "STARTED_FAIL_CLOSED_WITH_FINAL_STATUS_IN_SUMMARY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "preregistered_bounded_exploratory_test_after_training_pilot",
        "prediction": frozen_inputs,
        "runner": {
            "path": "scripts/run_paper2_transverse_notch_v01.py",
            "sha256": pilot._sha256(Path(__file__)),
        },
        "container": {
            "image": "dolfinx/dolfinx:v0.11.0",
            "image_id": EXPECTED_IMAGE_ID,
            "container_name": EXPECTED_CONTAINER_NAME,
            "network": "none",
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "root_filesystem": "read_only",
            "project_mount": "read_only",
            "only_writable_bind_mount": "/output",
            "gpu": "not_requested",
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "dolfinx": dolfinx.__version__,
            "platform": platform.platform(),
        },
        "budgets": {
            "batch_wall_seconds": BATCH_WALL_BUDGET_SECONDS,
            "project_cumulative_wall_seconds": PROJECT_WALL_BUDGET_SECONDS,
            "prior_batch_elapsed_seconds": frozen_inputs["prior_elapsed_seconds"],
        },
        "output_boundary": HOST_OUTPUT_RELATIVE,
        "case_count": 8,
        "cases": [asdict(spec) for spec in CASE_SPECS],
        "holdouts": {
            "status": "LOCKED_NOT_RUN",
            "signatures": [list(item) for item in sorted(pilot.HOLDOUT_SIGNATURES)],
        },
        "fixed_rules": {
            "de": 0.2,
            "steps_per_cycle": 128,
            "activation_peak": 0.10,
            "no_equal_power_claim": True,
            "no_fit_no_threshold_change_no_holdout": True,
        },
        "fourier_normalization_self_test": self_test,
        "manufactured_interface_check": manufactured,
        "scientific_boundary": {
            "prediction_read_after_first_batch": True,
            "not_original_blind_holdout": True,
            "not_continuous_minimum_certification": True,
            "not_formal_spatial_convergence": True,
            "not_nature_physics_novelty_certification": True,
            "interface_action_reaction_is_structural_identity_not_independent_measurement": True,
        },
    }
    pilot._create_json(output_root / "run_manifest.json", manifest)
    case_dir = output_root / "cases"
    case_dir.mkdir(parents=False, exist_ok=False)

    records: list[dict[str, Any]] = []
    for position, spec in enumerate(CASE_SPECS, start=1):
        _check_prediction_unchanged(repo_root)
        elapsed_before = time.perf_counter() - start
        project_elapsed_before = frozen_inputs["prior_elapsed_seconds"] + elapsed_before
        if elapsed_before >= BATCH_WALL_BUDGET_SECONDS:
            raise RuntimeError("900-second batch wall budget reached before next endpoint")
        if project_elapsed_before >= PROJECT_WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second project wall budget reached before next endpoint")

        print(f"CASE_START {position}/8 {spec.key}", flush=True)
        case_start = time.perf_counter()
        config = replace(
            ACTIVE_CONFIG,
            ecm_thickness=spec.thickness_ratio * ACTIVE_CONFIG.length,
            ecm_relaxation_time=spec.de * ACTIVE_CONFIG.period,
            activation_peak=spec.activation_peak,
        ).checked()
        system = build_system(
            spatial_label=spec.spatial_label,
            active_profile=spec.active_profile,
            config=config,
        )
        system_checks = global_structural_checks(system)
        if not all(item["pass"] for item in system_checks.values()):
            failure_record = {
                "schema": CASE_SCHEMA,
                "status": "FAILED_GLOBAL_STRUCTURAL_CHECK",
                "spec": asdict(spec),
                "actual_config": {**asdict(config), "config_digest": config.digest()},
                "system_checks": system_checks,
            }
            pilot._create_json(case_dir / f"{spec.key}.json", failure_record)
            raise RuntimeError(f"global structural check failed for {spec.key}")

        endpoint = simulate_endpoint(
            system=system,
            case_id=spec.case_id,
            steps_per_cycle=spec.steps_per_cycle,
        )
        structural_gate = endpoint_structural_gate(endpoint.summary)
        observables, derived_arrays = pilot._extract_observables(system, endpoint, spec)
        all_arrays = {
            **{name: np.asarray(values) for name, values in endpoint.arrays.items()},
            **derived_arrays,
        }
        nonfinite_keys = [
            name for name, values in all_arrays.items() if not np.all(np.isfinite(values))
        ]
        array_path = case_dir / f"{spec.key}.npz"
        if array_path.exists():
            raise FileExistsError(array_path)
        np.savez_compressed(array_path, **all_arrays)
        array_hash = pilot._sha256(array_path)
        if nonfinite_keys:
            failure_record = {
                "schema": CASE_SCHEMA,
                "status": "FAILED_NONFINITE_ARRAY",
                "spec": asdict(spec),
                "nonfinite_array_keys": nonfinite_keys,
                "arrays": {
                    "path": array_path.relative_to(output_root).as_posix(),
                    "sha256": array_hash,
                },
            }
            pilot._create_json(case_dir / f"{spec.key}.json", failure_record)
            raise RuntimeError(f"non-finite arrays in {spec.key}: {nonfinite_keys}")

        x_nodes = np.asarray(derived_arrays["x_interface_nodes"], dtype=np.float64)
        traction_complex = (
            np.asarray(
                derived_arrays["endocardium_ecm_traction_fundamental_real"],
                dtype=np.float64,
            )
            + 1.0j
            * np.asarray(
                derived_arrays["endocardium_ecm_traction_fundamental_imag"],
                dtype=np.float64,
            )
        )
        raw_modes = _exact_p1_spatial_modes(x_nodes, traction_complex[:, 1], config.length)
        mode_values = raw_modes.pop("complex_values")
        activation = observables["activation"]
        activation_complex = complex(
            activation["fundamental_coefficient_real"],
            activation["fundamental_coefficient_imag"],
        )
        spatial_modes = {
            **raw_modes,
            "c0": _complex_record(mode_values["c0"]),
            "c_cos": _complex_record(mode_values["c_cos"]),
            "c_sin": _complex_record(mode_values["c_sin"]),
        }
        case_elapsed = time.perf_counter() - case_start
        record = {
            "schema": CASE_SCHEMA,
            "status": "COMPLETED" if structural_gate["pass"] else "FAILED_ENDPOINT_STRUCTURAL_GATE",
            "spec": asdict(spec),
            "actual_config": {**asdict(config), "config_digest": config.digest()},
            "system": {
                "state_size": system.state_size,
                "spatial_label": system.spatial_label,
                "active_profile": system.active_profile,
                "active_profile_average": system.active_profile_average,
            },
            "system_checks": system_checks,
            "endpoint_structural_gate": structural_gate,
            "endpoint_summary": endpoint.summary,
            "observables": observables,
            "activation_fundamental": {
                "real": float(activation_complex.real),
                "imag": float(activation_complex.imag),
                "amplitude": float(abs(activation_complex)),
            },
            "spatial_modes": spatial_modes,
            "raw_active_work": float(endpoint.summary["ledger"]["total_active_work"]),
            "arrays": {
                "path": array_path.relative_to(output_root).as_posix(),
                "sha256": array_hash,
                "key_count": len(all_arrays),
            },
            "runtime_seconds": case_elapsed,
            "batch_cumulative_elapsed_seconds": time.perf_counter() - start,
            "project_cumulative_elapsed_seconds": (
                frozen_inputs["prior_elapsed_seconds"] + time.perf_counter() - start
            ),
        }
        case_json_path = case_dir / f"{spec.key}.json"
        pilot._create_json(case_json_path, record)
        record["case_json"] = {
            "path": case_json_path.relative_to(output_root).as_posix(),
            "sha256": pilot._sha256(case_json_path),
        }
        records.append(record)
        print(
            f"CASE_DONE {position}/8 {spec.key} seconds={case_elapsed:.3f} "
            f"structural_pass={structural_gate['pass']}",
            flush=True,
        )
        if not structural_gate["pass"]:
            raise RuntimeError(f"endpoint structural gate failed for {spec.key}")

        del endpoint, system, all_arrays, derived_arrays
        gc.collect()
        _check_prediction_unchanged(repo_root)
        batch_elapsed = time.perf_counter() - start
        if batch_elapsed > BATCH_WALL_BUDGET_SECONDS:
            raise RuntimeError("900-second batch wall budget exceeded after endpoint")
        if frozen_inputs["prior_elapsed_seconds"] + batch_elapsed > PROJECT_WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second project wall budget exceeded after endpoint")

    comparison = _comparison_and_gates(records)
    _check_prediction_unchanged(repo_root)
    total_elapsed = time.perf_counter() - start
    final_summary = {
        "schema": SUMMARY_SCHEMA,
        "status": "COMPLETED",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "preregistered_bounded_exploratory_test_after_training_pilot",
        "case_count": len(records),
        "batch_case_count": 8,
        "prior_case_count": 26,
        "cumulative_completed_case_count": 34,
        "holdouts": "LOCKED_NOT_RUN",
        "all_structural_gates_pass": all(
            record["endpoint_structural_gate"]["pass"] for record in records
        ),
        "all_arrays_finite": True,
        "batch_elapsed_seconds": total_elapsed,
        "prior_batch_elapsed_seconds": frozen_inputs["prior_elapsed_seconds"],
        "project_cumulative_elapsed_seconds": (
            frozen_inputs["prior_elapsed_seconds"] + total_elapsed
        ),
        "budgets": {
            "batch_wall_seconds": BATCH_WALL_BUDGET_SECONDS,
            "project_cumulative_wall_seconds": PROJECT_WALL_BUDGET_SECONDS,
        },
        "comparison": comparison,
        "cases": [
            {
                "key": record["spec"]["key"],
                "case_id": record["spec"]["case_id"],
                "thickness_ratio": record["spec"]["thickness_ratio"],
                "spatial_label": record["spec"]["spatial_label"],
                "structural_pass": record["endpoint_structural_gate"]["pass"],
                "raw_active_work": record["raw_active_work"],
                "spatial_modes": record["spatial_modes"],
                "runtime_seconds": record["runtime_seconds"],
                "case_json": record["case_json"],
                "arrays": record["arrays"],
            }
            for record in records
        ],
        "claim_boundary": {
            "not_original_blind_holdout": True,
            "not_continuous_minimum_certification": True,
            "S2_S3_difference_is_not_error_bound": True,
            "not_formal_spatial_or_temporal_convergence": True,
            "not_equal_power_across_thickness": True,
            "not_nature_physics_novelty_certification": True,
            "negative_or_inconclusive_result_not_retuned": True,
        },
    }
    pilot._create_json(output_root / "summary.json", final_summary)
    print(
        f"RUN_DONE cases={len(records)} candidate={comparison['candidate_status']} "
        f"seconds={total_elapsed:.3f}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--code-version")
    arguments = parser.parse_args()
    if arguments.self_test:
        report = _self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if arguments.output is None or arguments.code_version is None:
        parser.error("--output and --code-version are required unless --self-test is used")
    try:
        return run(arguments.output, arguments.code_version)
    except BaseException as error:
        try:
            if arguments.output.is_dir():
                _write_failure_summary(arguments.output, error)
        except BaseException as summary_error:
            print(
                f"FAILURE_SUMMARY_ERROR {type(summary_error).__name__}: {summary_error}",
                file=sys.stderr,
                flush=True,
            )
        print(
            f"RUN_ABORTED {type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
