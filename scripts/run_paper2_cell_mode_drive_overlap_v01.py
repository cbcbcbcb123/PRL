"""Project three preserved ECM-top motion fields onto one fixed N=2 cell mode.

This is a bounded, non-blind postprocessing probe.  It reads exactly three
preserved case JSON/NPZ pairs plus four provenance sources, reconstructs the
historical configuration through the byte-locked pure config module, and does
not import or build the mechanics model.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import runpy
import sys
import time
from typing import Any

import numpy as np


SCHEMA = "paper2_cell_mode_drive_overlap_v01"
FROZEN_ANALYSIS_COMMIT = "e5cfb0e07060046ad945b1c868cd618ec8f9e10d"
PRIOR_ANALYSIS_COMMIT = "5e56203972f9360c02454e502aef509059d8b09c"
ORIGINAL_RUN_CODE_VERSION = "740f2da07b6bfd4000ca900e5c27dcc9e3041483"
EXPECTED_CONFIG_DIGEST = "e32007757c2807c5c56e684f4c175a8896cd27371b97170333b9f8c25bb61e69"
PLAN_RELATIVE = Path("project_control/prl_independent_theory_mainline_plan_v04.md")
PLAN_SHA256 = "418c958c8a6dfeb4191cd80559c0713eec59c993bed27d21c7ecb0958e00bf26"
BRIEF_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/science_brief.md")
BRIEF_SHA256 = "2796f4fec314253f9551064cfce1f55b9eb27f7ae051ba712e2d5918df7032cc"
OUTPUT_RELATIVE = Path("results/paper2_cell_mode_drive_overlap/v01_20260905/summary.json")
CASE_ROOT_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/numerical/cases")
RUN_MANIFEST_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/numerical/run_manifest.json")
CONFIG_RELATIVE = Path("src/paper2_hybrid/config.py")
PILOT_RUNNER_RELATIVE = Path("scripts/run_paper2_science_pilot_v01.py")
MODEL_RELATIVE = Path("src/paper2_hybrid/model.py")
EXTRA_SOURCE_HASHES = {
    RUN_MANIFEST_RELATIVE.as_posix(): "bf571f576525439baa1385f76fb0cdc96fca4ed39caf4cfae85a7c6776a4c621",
    CONFIG_RELATIVE.as_posix(): "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe",
    PILOT_RUNNER_RELATIVE.as_posix(): "2675b91436dacc43ed9ad3121b8a24dfd8826f93440db184bbd7abad597002e7",
    MODEL_RELATIVE.as_posix(): "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800",
}
CASE_KEYS = (
    "basic__de0p2__h0p3__a1__s2__t128__a0p1",
    "basic__de0p2__h0p3__s1__s2__t128__a0p1",
    "space__de0p2__h0p3__s1__s3__t128__a0p1",
)
CASE_SOURCE_HASHES = {
    "basic__de0p2__h0p3__a1__s2__t128__a0p1.json": "1484c0e3ffbdc3b6fd144df1943a2a418c5e5f68cb1beb5810bc2a395f8580a0",
    "basic__de0p2__h0p3__a1__s2__t128__a0p1.npz": "39006a9738eed18c77a5f3dd398049412a4ccf511cdeb98dc4909943e36461bc",
    "basic__de0p2__h0p3__s1__s2__t128__a0p1.json": "61d5b104989204808310e539892b29b1a9ea657da32c42624b1685a1df12a9d7",
    "basic__de0p2__h0p3__s1__s2__t128__a0p1.npz": "2795cf0318cd9075728ba9951b3c4b43fe2de72d6dfd4a567a7895426953eaef",
    "space__de0p2__h0p3__s1__s3__t128__a0p1.json": "c13bb55c64e4a1303cb12a14e3442d0a723b98aafdeb298757960596da33f203",
    "space__de0p2__h0p3__s1__s3__t128__a0p1.npz": "01aca7b4e3069b81e008b8a1ec8a92ed827fb646e0b7ec98a28ed7c61e1efb62",
}
STEPS = 128
POSTPROCESS_BUDGET_SECONDS = 30.0
ARRAY_LOAD_LIMIT_BYTES = 512 * 1024 * 1024
PROJECT_MEMORY_LIMIT_GIB = 8
FLOOR = 1.0e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _write_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            _jsonable(payload),
            handle,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write("\n")


def _complex_record(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "amplitude": float(abs(value)),
    }


def _harmonic(signal: np.ndarray, steps: int = STEPS) -> np.ndarray:
    values = np.asarray(signal[..., :steps], dtype=np.float64)
    if values.shape[-1] != steps:
        raise ValueError("incomplete frozen first-cycle DFT window")
    centered = values - np.mean(values, axis=-1, keepdims=True)
    return (2.0 / steps) * np.fft.rfft(centered, axis=-1)[..., 1]


def _cell_mode(x_values: np.ndarray, length: float) -> np.ndarray:
    return 4.0 * np.abs(np.asarray(x_values, dtype=np.float64)) / length - 1.0


def _p1_integral(field: np.ndarray, x_values: np.ndarray) -> complex:
    widths = np.diff(x_values)
    return complex(np.sum(widths * (field[:-1] + field[1:]) / 2.0))


def _p1_product_integral(
    first: np.ndarray, second: np.ndarray, x_values: np.ndarray
) -> complex:
    widths = np.diff(x_values)
    return complex(
        np.sum(
            widths
            * (
                2.0 * first[:-1] * second[:-1]
                + first[:-1] * second[1:]
                + first[1:] * second[:-1]
                + 2.0 * first[1:] * second[1:]
            )
            / 6.0
        )
    )


def _p1_complex_rms(field: np.ndarray, x_values: np.ndarray, length: float) -> float:
    widths = np.diff(x_values)
    left = field[:-1]
    right = field[1:]
    mean_square = float(
        np.sum(
            widths
            * (
                np.abs(left) ** 2
                + np.real(left * np.conjugate(right))
                + np.abs(right) ** 2
            )
            / 3.0
        )
        / length
    )
    return math.sqrt(max(mean_square, 0.0))


def _relative_phase(value: complex, activation: complex, value_floor: float) -> dict[str, Any]:
    interpretable = abs(value) > value_floor and abs(activation) > FLOOR
    if not interpretable:
        return {
            "interpretable": False,
            "relative_to_activation_rad": None,
            "relative_to_activation_deg": None,
            "value_floor": value_floor,
            "activation_floor": FLOOR,
        }
    phase = float(np.angle(value / activation))
    return {
        "interpretable": True,
        "relative_to_activation_rad": phase,
        "relative_to_activation_deg": math.degrees(phase),
        "value_floor": value_floor,
        "activation_floor": FLOOR,
    }


def _self_test() -> dict[str, Any]:
    theta = 2.0 * math.pi * np.arange(STEPS) / STEPS
    temporal_errors = {
        "constant": abs(complex(_harmonic(np.full(STEPS, 3.25)))),
        "unit_cosine": abs(complex(_harmonic(np.cos(theta))) - 1.0),
    }
    x_values = np.linspace(-0.5, 0.5, 33)
    mode = _cell_mode(x_values, 1.0)
    spatial_errors = {
        "mode_mean": abs(_p1_integral(mode, x_values)),
        "mode_mean_square": abs(_p1_product_integral(mode, mode, x_values) - 1.0 / 3.0),
        "constant_projection": abs(_p1_product_integral(mode, np.ones_like(mode), x_values)),
        "mode_projection": abs(_p1_product_integral(mode, mode, x_values) - 1.0 / 3.0),
    }
    tolerance = 3.0e-14
    return {
        "pass": max((*temporal_errors.values(), *spatial_errors.values())) <= tolerance,
        "tolerance": tolerance,
        "temporal_errors": temporal_errors,
        "spatial_errors": spatial_errors,
    }


def _verify_sources(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    direct_ledger: dict[str, Any] = {}
    for relative_text, expected_hash in EXTRA_SOURCE_HASHES.items():
        relative_path = Path(relative_text)
        path = repo_root / relative_path
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"extra source hash mismatch: {relative_text} expected={expected_hash} actual={actual_hash}"
            )
        direct_ledger[relative_text] = {
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
        }
    for file_name, expected_hash in CASE_SOURCE_HASHES.items():
        relative_path = CASE_ROOT_RELATIVE / file_name
        path = repo_root / relative_path
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"case source hash mismatch: {file_name} expected={expected_hash} actual={actual_hash}"
            )
        direct_ledger[relative_path.as_posix()] = {
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
        }

    with (repo_root / RUN_MANIFEST_RELATIVE).open("r", encoding="utf-8") as handle:
        run_manifest = json.load(handle)
    if run_manifest.get("code_version") != ORIGINAL_RUN_CODE_VERSION:
        raise RuntimeError("original run manifest code_version mismatch")
    for source_relative in (CONFIG_RELATIVE, PILOT_RUNNER_RELATIVE, MODEL_RELATIVE):
        expected_hash = EXTRA_SOURCE_HASHES[source_relative.as_posix()]
        if run_manifest["source_hashes"].get(source_relative.as_posix()) != expected_hash:
            raise RuntimeError(f"run-manifest source hash mismatch: {source_relative}")
    manifest_case_keys = {record["key"] for record in run_manifest["cases"]}
    if not set(CASE_KEYS).issubset(manifest_case_keys):
        raise RuntimeError("one or more selected cases are absent from the original run manifest")

    pilot_text = (repo_root / PILOT_RUNNER_RELATIVE).read_text(encoding="utf-8")
    required_pilot_fragments = (
        "config = replace(",
        "ecm_thickness=spec.thickness_ratio * ACTIVE_CONFIG.length",
        "ecm_relaxation_time=spec.de * ACTIVE_CONFIG.period",
        "activation_peak=spec.activation_peak",
        '"config_digest": config.digest()',
    )
    if not all(fragment in pilot_text for fragment in required_pilot_fragments):
        raise RuntimeError("original pilot replacement/serialization symbol check failed")
    model_text = (repo_root / MODEL_RELATIVE).read_text(encoding="utf-8")
    required_model_fragments = (
        "traction_endo_ecm = system.config.endocardium_ecm_interface_stiffness * (",
        "endo - ecm_top",
    )
    if not all(fragment in model_text for fragment in required_model_fragments):
        raise RuntimeError("production traction-sign symbol check failed")
    symbol_checks = {
        "pilot_three_replacements_and_digest_serialization": True,
        "model_t_code_equals_kce_times_endo_minus_ecm": True,
        "package_model_and_runner_not_imported": True,
    }
    return direct_ledger, {"run_manifest": run_manifest, "symbol_checks": symbol_checks}


def _reconstructed_configs(repo_root: Path, case_jsons: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], float]:
    loaded_before = {name for name in sys.modules if name == "paper2_hybrid" or name.startswith("paper2_hybrid.")}
    if loaded_before:
        raise RuntimeError("paper2_hybrid package was imported before pure config loading")
    namespace = runpy.run_path(
        str(repo_root / CONFIG_RELATIVE), run_name="__paper2_historical_config_snapshot__"
    )
    active_config = namespace["ACTIVE_CONFIG"]
    comparisons: dict[str, Any] = {}
    stiffness_values: list[float] = []
    for key in CASE_KEYS:
        case_json = case_jsons[key]
        spec = case_json["spec"]
        reconstructed = replace(
            active_config,
            ecm_thickness=float(spec["thickness_ratio"]) * active_config.length,
            ecm_relaxation_time=float(spec["de"]) * active_config.period,
            activation_peak=float(spec["activation_peak"]),
        ).checked()
        digest = reconstructed.digest()
        actual_digest = case_json["actual_config"]["config_digest"]
        endpoint_digest = case_json["endpoint_summary"]["config_digest"]
        if not (
            digest == EXPECTED_CONFIG_DIGEST
            and actual_digest == digest
            and endpoint_digest == digest
        ):
            raise RuntimeError(f"reconstructed configuration digest mismatch: {key}")
        stiffness = float(reconstructed.endocardium_ecm_interface_stiffness)
        stiffness_values.append(stiffness)
        comparisons[key] = {
            "reconstructed_digest": digest,
            "actual_config_digest": actual_digest,
            "endpoint_summary_digest": endpoint_digest,
            "length": float(reconstructed.length),
            "period": float(reconstructed.period),
            "ecm_thickness": float(reconstructed.ecm_thickness),
            "ecm_relaxation_time": float(reconstructed.ecm_relaxation_time),
            "activation_peak": float(reconstructed.activation_peak),
            "endocardium_ecm_interface_stiffness_k_ce": stiffness,
            "pass": True,
        }
    loaded_after = {name for name in sys.modules if name == "paper2_hybrid" or name.startswith("paper2_hybrid.")}
    if loaded_after:
        raise RuntimeError("pure config loading unexpectedly imported paper2_hybrid package")
    if any(value != 7.0 for value in stiffness_values):
        raise RuntimeError("reconstructed k_ce is not 7.0")
    return comparisons, stiffness_values[0]


def _case_analysis(
    repo_root: Path,
    key: str,
    case_json: dict[str, Any],
    stiffness: float,
) -> tuple[dict[str, Any], int]:
    spec = case_json["spec"]
    actual = case_json["actual_config"]
    if not (
        spec["key"] == key
        and spec["case_id"] in {"A1", "S1"}
        and spec["spatial_label"] in {"S2", "S3"}
        and int(spec["steps_per_cycle"]) == STEPS
        and float(spec["de"]) == 0.2
        and float(spec["thickness_ratio"]) == 0.3
        and float(actual["length"]) == 1.0
        and float(actual["period"]) == 1.0
        and float(actual["ecm_thickness"]) == 0.3
        and float(actual["ecm_relaxation_time"]) == 0.2
    ):
        raise RuntimeError(f"case identity/configuration mismatch: {key}")
    npz_path = repo_root / CASE_ROOT_RELATIVE / f"{key}.npz"
    if case_json["arrays"]["sha256"] != _sha256(npz_path):
        raise RuntimeError(f"case JSON-to-NPZ hash mismatch: {key}")
    required = (
        "time_two_cycles",
        "activation_two_cycles",
        "x_interface_nodes",
        "endocardial_displacement_two_cycles",
        "endocardium_ecm_traction_two_cycles",
        "endocardium_ecm_traction_fundamental_real",
        "endocardium_ecm_traction_fundamental_imag",
    )
    with np.load(npz_path) as arrays:
        if any(name not in arrays.files for name in required):
            raise RuntimeError(f"required source array missing: {key}")
        if int(case_json["arrays"]["key_count"]) != len(arrays.files):
            raise RuntimeError(f"NPZ key count mismatch: {key}")
        time_values = np.asarray(arrays["time_two_cycles"], dtype=np.float64)
        activation = np.asarray(arrays["activation_two_cycles"], dtype=np.float64)
        x_values = np.asarray(arrays["x_interface_nodes"], dtype=np.float64)
        endocardial = np.asarray(
            arrays["endocardial_displacement_two_cycles"], dtype=np.float64
        )
        traction_flat = np.asarray(
            arrays["endocardium_ecm_traction_two_cycles"], dtype=np.float64
        )
        stored_traction_fundamental = np.asarray(
            arrays["endocardium_ecm_traction_fundamental_real"], dtype=np.float64
        ) + 1.0j * np.asarray(
            arrays["endocardium_ecm_traction_fundamental_imag"], dtype=np.float64
        )
    selected_arrays = (
        time_values,
        activation,
        x_values,
        endocardial,
        traction_flat,
        stored_traction_fundamental,
    )
    loaded_bytes = sum(value.nbytes for value in selected_arrays)
    if not all(np.all(np.isfinite(value.real)) and np.all(np.isfinite(value.imag)) for value in selected_arrays):
        raise RuntimeError(f"non-finite selected source array: {key}")
    node_count = len(x_values)
    expected_time_shape = (2 * STEPS + 1,)
    if not (
        time_values.shape == expected_time_shape
        and activation.shape == expected_time_shape
        and endocardial.shape == (node_count, 2, 2 * STEPS + 1)
        and traction_flat.shape == (2 * node_count, 2 * STEPS + 1)
        and stored_traction_fundamental.shape == (node_count, 2)
    ):
        raise RuntimeError(f"selected source dimensions mismatch: {key}")
    expected_time = np.linspace(0.0, 2.0, 2 * STEPS + 1)
    time_axis_error = float(np.max(np.abs(time_values - expected_time)))
    if time_axis_error > 5.0e-14:
        raise RuntimeError(f"time-axis mismatch: {key}")
    widths = np.diff(x_values)
    if not (
        np.all(widths > 0.0)
        and math.isclose(float(x_values[0]), -0.5, abs_tol=5.0e-12, rel_tol=0.0)
        and math.isclose(float(x_values[-1]), 0.5, abs_tol=5.0e-12, rel_tol=0.0)
        and float(np.min(np.abs(x_values))) <= 5.0e-12
    ):
        raise RuntimeError(f"interface coordinate mismatch: {key}")

    traction = traction_flat.reshape(node_count, 2, -1)
    endocardial_y = endocardial[:, 1, :STEPS]
    traction_y = traction[:, 1, :STEPS]
    ecm_y = endocardial_y - traction_y / stiffness
    periodic_checks = {
        "endocardial_y": float(np.max(np.abs(endocardial_y[-1] - endocardial_y[0]))),
        "traction_y_code": float(np.max(np.abs(traction_y[-1] - traction_y[0]))),
        "recovered_ecm_y": float(np.max(np.abs(ecm_y[-1] - ecm_y[0]))),
    }
    if max(periodic_checks.values()) > FLOOR:
        raise RuntimeError(f"periodic y endpoint mismatch: {key}")

    activation_coefficient = complex(_harmonic(activation))
    endocardial_coefficient = _harmonic(endocardial_y)
    traction_coefficient = _harmonic(traction_y)
    ecm_coefficient = _harmonic(ecm_y)
    stored_y = stored_traction_fundamental[:, 1]
    traction_fundamental_error = float(np.max(np.abs(traction_coefficient - stored_y)))
    if traction_fundamental_error > 1.0e-12:
        raise RuntimeError(f"raw-to-stored traction fundamental mismatch: {key}")
    recorded_activation = complex(
        float(case_json["observables"]["activation"]["fundamental_coefficient_real"]),
        float(case_json["observables"]["activation"]["fundamental_coefficient_imag"]),
    )
    activation_error = abs(activation_coefficient - recorded_activation)
    if activation_error > 1.0e-12:
        raise RuntimeError(f"raw-to-recorded activation fundamental mismatch: {key}")

    mode = _cell_mode(x_values, float(actual["length"]))
    mode_mean = float(
        _p1_integral(mode, x_values).real / float(actual["length"])
    )
    mode_mean_square = float(
        _p1_product_integral(mode, mode, x_values).real / float(actual["length"])
    )
    if abs(mode_mean) > 3.0e-14 or abs(mode_mean_square - 1.0 / 3.0) > 3.0e-14:
        raise RuntimeError(f"cell-mode algebra mismatch: {key}")
    projection_p = _p1_product_integral(mode, ecm_coefficient, x_values) / float(
        actual["length"]
    )
    generalized_force = stiffness * float(actual["length"]) * projection_p
    ecm_spatial_mean = _p1_integral(ecm_coefficient, x_values) / float(actual["length"])
    centered_ecm = ecm_coefficient - ecm_spatial_mean
    centered_rms = _p1_complex_rms(centered_ecm, x_values, float(actual["length"]))
    overlap_denominator = math.sqrt(1.0 / 3.0) * centered_rms
    normalized_overlap = (
        float(abs(projection_p) / overlap_denominator)
        if overlap_denominator > FLOOR * float(actual["length"])
        else None
    )
    projection_over_activation = (
        _complex_record(projection_p / activation_coefficient)
        if abs(activation_coefficient) > FLOOR
        else None
    )
    return {
        "case_key": key,
        "spec": spec,
        "configuration": {
            "actual_config": actual,
            "reconstructed_k_ce": stiffness,
        },
        "input_checks": {
            "selected_array_shapes": {
                "time_two_cycles": list(time_values.shape),
                "activation_two_cycles": list(activation.shape),
                "x_interface_nodes": list(x_values.shape),
                "endocardial_displacement_two_cycles": list(endocardial.shape),
                "endocardium_ecm_traction_two_cycles": list(traction_flat.shape),
            },
            "loaded_array_bytes": loaded_bytes,
            "time_axis_maximum_absolute_error": time_axis_error,
            "x_strictly_increasing_contains_zero_and_endpoints_match": True,
            "periodic_y_endpoint_maximum_absolute_mismatches": periodic_checks,
            "raw_to_stored_traction_fundamental_maximum_absolute_error": traction_fundamental_error,
            "raw_to_recorded_activation_fundamental_absolute_error": activation_error,
            "all_selected_arrays_finite": True,
        },
        "cell_mode": {
            "definition": "v(-L/2)=1, v(0)=-1, v(L/2)=1; linear on each half",
            "physical_cell_width_a": float(actual["length"]) / 2.0,
            "P1_mean": mode_mean,
            "P1_mean_square": mode_mean_square,
            "not_measured_endocardial_cell_scale": True,
        },
        "activation_reference_alpha": _complex_record(activation_coefficient),
        "projection_p": {
            **_complex_record(projection_p),
            "phase": _relative_phase(
                projection_p, activation_coefficient, FLOOR * float(actual["length"])
            ),
        },
        "generalized_force_F_delta": {
            **_complex_record(generalized_force),
            "definition": "k_ce*L*p with the production code-sign convention",
            "phase": _relative_phase(
                generalized_force,
                activation_coefficient,
                stiffness * float(actual["length"]) ** 2 * FLOOR,
            ),
        },
        "projection_p_over_activation_alpha": projection_over_activation,
        "recovered_ecm_y_first_fundamental": {
            "P1_spatial_mean": _complex_record(ecm_spatial_mean),
            "P1_zero_spatial_mean_RMS": centered_rms,
            "normalized_overlap_absolute": normalized_overlap,
            "normalized_overlap_denominator": overlap_denominator,
            "near_zero_rule": "normalized overlap is null when denominator <=1e-12*L",
        },
        "sign_and_evidence_boundary": {
            "t_y_code": "k_ce*(u_endo_y-u_ecm_y)",
            "recovery": "u_ecm_y=u_endo_y-t_y_code/k_ce",
            "F_delta": "hypothetical conservative attachment cross-load for a prescribed basis displacement",
            "not_cell_deformation_attachment_force_or_DCM_solution": True,
        },
    }, loaded_bytes


def run(output_path: Path) -> int:
    start = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[1]
    expected_output = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_path.resolve() != expected_output:
        raise RuntimeError("output boundary mismatch")
    if output_path.exists() or output_path.parent.exists():
        raise RuntimeError("create-only output target is occupied")
    if _sha256(repo_root / PLAN_RELATIVE) != PLAN_SHA256:
        raise RuntimeError("frozen main-plan hash mismatch")
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        raise RuntimeError("frozen science-brief hash mismatch")
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-thread environment mismatch: {variable}")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1" or not sys.dont_write_bytecode:
        raise RuntimeError("bytecode-cache prohibition is not active")
    self_test = _self_test()
    if not self_test["pass"]:
        raise RuntimeError("temporal/spatial algebra self-test failed")
    direct_ledger, provenance = _verify_sources(repo_root)
    case_jsons: dict[str, dict[str, Any]] = {}
    for key in CASE_KEYS:
        with (repo_root / CASE_ROOT_RELATIVE / f"{key}.json").open(
            "r", encoding="utf-8"
        ) as handle:
            case_jsons[key] = json.load(handle)
    config_comparisons, stiffness = _reconstructed_configs(repo_root, case_jsons)
    if stiffness != 7.0:
        raise RuntimeError("k_ce reconstruction mismatch")

    records: list[dict[str, Any]] = []
    total_loaded_array_bytes = 0
    for key in CASE_KEYS:
        if time.perf_counter() - start > POSTPROCESS_BUDGET_SECONDS:
            raise RuntimeError("30-second postprocessing budget exceeded")
        record, loaded_bytes = _case_analysis(
            repo_root, key, case_jsons[key], stiffness
        )
        records.append(record)
        total_loaded_array_bytes += loaded_bytes
    if total_loaded_array_bytes > ARRAY_LOAD_LIMIT_BYTES:
        raise RuntimeError("selected array load exceeded 512 MiB")

    by_key = {record["case_key"]: record for record in records}
    s1_s2 = by_key[CASE_KEYS[1]]["projection_p"]
    s1_s3 = by_key[CASE_KEYS[2]]["projection_p"]
    p_s2 = complex(float(s1_s2["real"]), float(s1_s2["imag"]))
    p_s3 = complex(float(s1_s3["real"]), float(s1_s3["imag"]))
    error_proxy = abs(p_s3 - p_s2)
    comparison_threshold = 2.0 * max(error_proxy, FLOOR)
    classification = (
        "RESOLVED_BASELINE_DRIVE_PROJECTION"
        if abs(p_s3) > comparison_threshold
        else "INCONCLUSIVE_BASELINE_PROJECTION"
    )
    elapsed = time.perf_counter() - start
    if elapsed > POSTPROCESS_BUDGET_SECONDS:
        raise RuntimeError("30-second postprocessing budget exceeded")
    if _sha256(repo_root / PLAN_RELATIVE) != PLAN_SHA256:
        raise RuntimeError("main plan changed during postprocessing")
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        raise RuntimeError("science brief changed during postprocessing")
    for relative_text, expected_hash in EXTRA_SOURCE_HASHES.items():
        if _sha256(repo_root / relative_text) != expected_hash:
            raise RuntimeError(f"extra source changed during postprocessing: {relative_text}")
    for file_name, expected_hash in CASE_SOURCE_HASHES.items():
        if _sha256(repo_root / CASE_ROOT_RELATIVE / file_name) != expected_hash:
            raise RuntimeError(f"case source changed during postprocessing: {file_name}")

    source_file_bytes = sum(item["bytes"] for item in direct_ledger.values())
    payload = {
        "schema": SCHEMA,
        "status": "COMPLETED_BOUNDED_NONBLIND_POSTPROCESS_NO_MECHANISM_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_question": (
            "Do three preserved ECM-top motion fields have a resolvable conservative "
            "drive projection onto one prescribed two-cell triangular mode?"
        ),
        "preregistration": {
            "main_plan": {
                "path": PLAN_RELATIVE.as_posix(),
                "sha256": PLAN_SHA256,
                "section": 28,
            },
            "science_brief": {
                "path": BRIEF_RELATIVE.as_posix(),
                "sha256": BRIEF_SHA256,
                "sections": [48, 48.1],
            },
            "frozen_analysis_commit_with_source_clarification": FROZEN_ANALYSIS_COMMIT,
            "prior_analysis_commit_before_clarification": PRIOR_ANALYSIS_COMMIT,
        },
        "source_provenance": {
            "direct_source_count": len(direct_ledger),
            "direct_source_ledger": direct_ledger,
            "total_direct_source_file_bytes": source_file_bytes,
            "original_run_manifest_code_version": ORIGINAL_RUN_CODE_VERSION,
            "original_run_manifest_source_hashes": provenance["run_manifest"][
                "source_hashes"
            ],
            "code_symbol_checks": provenance["symbol_checks"],
            "actual_config_k_ce_field_was_absent_and_section_48_1_clarified_source": True,
            "per_case_reconstructed_config": config_comparisons,
            "reconstructed_k_ce": stiffness,
        },
        "analysis_definition": {
            "time_window": "first 128 samples of the first cycle; repeated endpoint excluded",
            "time_fundamental": "2/N first rFFT coefficient after temporal mean removal",
            "cell_mode": "v(-L/2)=1, v(0)=-1, v(L/2)=1; P1 on each half",
            "projection": "p=L^-1 integral v*u_ecm_y_hat dx using exact native-P1 product integration",
            "generalized_force": "F_delta=k_ce*L*p",
            "traction_code_sign": "t_y_code=k_ce*(u_endo_y-u_ecm_y)",
        },
        "self_test": self_test,
        "records": records,
        "A1_role": "descriptive S2 record only; no spatial-resolution classification",
        "S1_two_grid_decision": {
            "p_S2": _complex_record(p_s2),
            "p_S3": _complex_record(p_s3),
            "E_p_absolute_complex_difference": error_proxy,
            "floor_1e_minus_12_L": FLOOR,
            "two_times_max_error_or_floor": comparison_threshold,
            "absolute_p_S3": abs(p_s3),
            "classification": classification,
            "classification_is_not_mechanism_or_numerical_pass": True,
        },
        "runtime": {
            "postprocess_elapsed_seconds": elapsed,
            "postprocess_budget_seconds": POSTPROCESS_BUDGET_SECONDS,
            "python_executable": sys.executable,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "cpu_threads": 1,
            "gpu": "not_used",
            "network": "not_used",
            "new_container": "not_used",
            "selected_array_load_bytes": total_loaded_array_bytes,
            "selected_array_load_limit_bytes": ARRAY_LOAD_LIMIT_BYTES,
            "project_memory_limit_gib": PROJECT_MEMORY_LIMIT_GIB,
            "bytecode_cache": "disabled",
            "entry_path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "entry_sha256": _sha256(Path(__file__).resolve()),
        },
        "existing_compute_ledger_unchanged": {
            "completed_periodic_cases": 46,
            "completed_static_rhs": 30,
            "fem_and_failure_seconds": 170.24076614002115,
            "this_postprocess_seconds_recorded_separately": elapsed,
        },
        "claim_boundary": {
            "nonblind_existing_data_probe": True,
            "prescribed_one_way_basis_field": True,
            "not_new_DCM_FEM_or_state_solution": True,
            "not_a_holdout_prediction": True,
            "not_cell_deformation_attachment_force_or_closed_cell_model": True,
            "not_equal_active_work_or_equal_global_motion": True,
            "not_DCM_necessity_mechanism_or_paper_pass": True,
            "no_parameter_extension_or_next_stage_authorized": True,
        },
        "holdouts": "ORIGINAL_FOUR_LOCKED_NOT_READ",
        "next_gate": "SUPERVISOR_INDEPENDENT_RECOMPUTATION_STOP",
    }
    _write_json_exclusive(output_path, payload)
    print(
        f"CELL_MODE_OVERLAP_DONE cases=3 decision={classification} elapsed={elapsed:.6f}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.self_test:
        report = _self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if arguments.output is None:
        parser.error("--output is required unless --self-test is used")
    try:
        return run(arguments.output)
    except BaseException as error:
        repo_root = Path(__file__).resolve().parents[1]
        expected_output = (repo_root / OUTPUT_RELATIVE).resolve()
        if arguments.output.resolve() == expected_output and not arguments.output.exists():
            failure_payload = {
                "schema": SCHEMA,
                "status": "ABORTED_FAIL_CLOSED",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "frozen_analysis_commit": FROZEN_ANALYSIS_COMMIT,
                "entry_sha256": _sha256(Path(__file__).resolve()),
                "no_automatic_retry_or_scope_change": True,
                "holdouts": "ORIGINAL_FOUR_LOCKED_NOT_READ",
            }
            _write_json_exclusive(arguments.output, failure_payload)
        print(f"CELL_MODE_OVERLAP_ABORTED {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
