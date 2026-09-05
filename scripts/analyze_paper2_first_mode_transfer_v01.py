"""Evaluate the continuous first-spatial-mode transfer on eight saved cases.

This is a no-fit, no-FEM postprocessing diagnostic.  The observable is the
complex Fourier coefficient t_y1=(c_cos-i*c_sin)/2, never the scalar B1.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
from scipy.linalg import expm

import run_paper2_transverse_notch_v02 as notch


SCHEMA = "paper2_first_mode_transfer_v01"
FORMULA_VERSION = "science_brief_section_31_at_bfd70488"
EXPECTED_CODE_VERSION = "bfd70488971527d4246372ca010604f2764f76d6"
BRIEF_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/science_brief.md")
BRIEF_SHA256 = "4abc44dc79039d5740e3e7082fd6e4fa14eccbdf4fce772ceb4c218cd55ff67d"
CASE_ROOT_RELATIVE = Path("results/paper2_transverse_notch/v02_20260905/cases")
OUTPUT_RELATIVE = Path(
    "results/paper2_transverse_notch/v02_20260905/first_mode_transfer_v01.json"
)
SOURCE_RUNNER = "scripts/run_paper2_transverse_notch_v02.py"
SOURCE_RUNNER_SHA256 = "13f0699cb28e7b2ee2c14e90811b75f55c43b0ab82279b2e1687d886a72e9d79"
SOURCE_RUNTIME_VERSION = "7cf40e211ccbd01b5baa60693834ea7907b89405"
FLOOR = 1.0e-12
POSTPROCESS_BUDGET_SECONDS = 120.0


def _case_keys() -> tuple[str, ...]:
    keys: list[str] = []
    for thickness_token in ("0p21", "0p26", "0p31"):
        for spatial in ("s2", "s3"):
            keys.append(
                f"transverse_notch__de0p2__h{thickness_token}__a1__{spatial}__t128__a0p1"
            )
    for spatial in ("s2", "s3"):
        keys.append(
            f"transverse_notch__de0p2__h0p26__s1__{spatial}__t128__a0p1"
        )
    return tuple(keys)


CASE_KEYS = _case_keys()


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
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _create_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(path)
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


def _complex_from_record(record: dict[str, Any]) -> complex:
    return complex(float(record["real"]), float(record["imag"]))


def _fundamental(signal: np.ndarray, steps: int) -> np.ndarray:
    values = np.asarray(signal[..., :steps], dtype=np.float64)
    if values.shape[-1] != steps:
        raise ValueError("signal does not contain a complete cycle")
    centered = values - np.mean(values, axis=-1, keepdims=True)
    return (2.0 / steps) * np.fft.rfft(centered, axis=-1)[..., 1]


def _lame(young_modulus: float, poisson_ratio: float) -> tuple[float, float]:
    shear = young_modulus / (2.0 * (1.0 + poisson_ratio))
    lame_lambda = (
        young_modulus
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    return lame_lambda, shear


def _layer_propagator(
    lame_lambda: complex,
    shear_modulus: complex,
    drag: float,
    spectral_rate: complex,
    wavenumber: float,
    affine_first_coefficient: complex,
    thickness: float,
    myocardium: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    longitudinal = lame_lambda + 2.0 * shear_modulus
    reduced = longitudinal - lame_lambda * lame_lambda / longitudinal
    imaginary_wavenumber = 1.0j * wavenumber
    matrix = np.asarray(
        (
            (0.0, -imaginary_wavenumber, 1.0 / shear_modulus, 0.0),
            (
                -imaginary_wavenumber * lame_lambda / longitudinal,
                0.0,
                0.0,
                1.0 / longitudinal,
            ),
            (
                spectral_rate * drag + wavenumber * wavenumber * reduced,
                0.0,
                0.0,
                -imaginary_wavenumber * lame_lambda / longitudinal,
            ),
            (0.0, spectral_rate * drag, -imaginary_wavenumber, 0.0),
        ),
        dtype=np.complex128,
    )
    source_epsilon = np.asarray(
        (0.0, 0.0, spectral_rate * drag * affine_first_coefficient, 0.0),
        dtype=np.complex128,
    )
    source_activation = (
        np.asarray(
            (
                0.0,
                -lame_lambda / longitudinal,
                -imaginary_wavenumber * reduced,
                0.0,
            ),
            dtype=np.complex128,
        )
        if myocardium
        else np.zeros(4, dtype=np.complex128)
    )
    augmented = np.zeros((6, 6), dtype=np.complex128)
    augmented[:4, :4] = matrix
    augmented[:4, 4] = source_epsilon
    augmented[:4, 5] = source_activation
    propagated = expm(augmented * thickness)
    transition = propagated[:4, :4]
    q_epsilon = propagated[:4, 4]
    q_activation = propagated[:4, 5]
    values = (matrix, transition, q_epsilon, q_activation)
    if not all(
        np.all(np.isfinite(value.real)) and np.all(np.isfinite(value.imag))
        for value in values
    ):
        raise RuntimeError("non-finite layer propagator")
    return transition, q_epsilon, q_activation, {
        "longitudinal_modulus": _complex_record(longitudinal),
        "reduced_modulus_Q": _complex_record(reduced),
        "state_matrix_condition_number": float(np.linalg.cond(matrix)),
    }


def _transfer_coefficients(config: dict[str, Any], steps: int) -> dict[str, Any]:
    length = float(config["length"])
    period = float(config["period"])
    time_step = period / steps
    zeta = np.exp(1.0j * 2.0 * math.pi / steps)
    spectral_rate = complex((2.0 / time_step) * (zeta - 1.0) / (zeta + 1.0))
    wavenumber = 2.0 * math.pi / length
    affine_first = -1.0j * length / (2.0 * math.pi)

    lambda_m, mu_m = _lame(
        float(config["myocardium_young_modulus"]),
        float(config["myocardium_poisson_ratio"]),
    )
    lambda_equilibrium, mu_equilibrium = _lame(
        float(config["ecm_equilibrium_young_modulus"]),
        float(config["ecm_equilibrium_poisson_ratio"]),
    )
    lambda_maxwell, mu_maxwell = _lame(
        float(config["ecm_maxwell_young_modulus"]),
        float(config["ecm_maxwell_poisson_ratio"]),
    )
    phi = (
        spectral_rate * float(config["ecm_relaxation_time"])
        / (1.0 + spectral_rate * float(config["ecm_relaxation_time"]))
    )
    lambda_e = lambda_equilibrium + phi * lambda_maxwell
    mu_e = mu_equilibrium + phi * mu_maxwell

    transition_m, q_m_epsilon, q_m_activation, detail_m = _layer_propagator(
        lambda_m,
        mu_m,
        float(config["myocardium_drag"]),
        spectral_rate,
        wavenumber,
        affine_first,
        float(config["myocardium_thickness"]),
        True,
    )
    transition_e, q_e_epsilon, _, detail_e = _layer_propagator(
        lambda_e,
        mu_e,
        float(config["ecm_drag"]),
        spectral_rate,
        wavenumber,
        affine_first,
        float(config["ecm_thickness"]),
        False,
    )
    bottom = np.asarray(
        (
            (1.0, 0.0),
            (0.0, 1.0),
            (float(config["support_tangential_stiffness"]), 0.0),
            (0.0, float(config["support_normal_stiffness"])),
        ),
        dtype=np.complex128,
    )
    bottom_epsilon = np.asarray(
        (
            0.0,
            0.0,
            float(config["support_tangential_stiffness"]) * affine_first,
            0.0,
        ),
        dtype=np.complex128,
    )
    lower_stiffness = float(config["ecm_myocardium_interface_stiffness"])
    lower_jump = np.asarray(
        (
            (1.0, 0.0, 1.0 / lower_stiffness, 0.0),
            (0.0, 1.0, 0.0, 1.0 / lower_stiffness),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=np.complex128,
    )
    displacement_selector = np.asarray(
        ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0)),
        dtype=np.complex128,
    )
    traction_selector = np.asarray(
        ((0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
        dtype=np.complex128,
    )
    upper_stiffness = float(config["endocardium_ecm_interface_stiffness"])
    chain_impedance = np.diag(
        np.asarray(
            (
                float(config["endocardial_axial_stiffness"])
                * wavenumber
                * wavenumber
                + spectral_rate * float(config["endocardial_drag"]),
                float(config["endocardial_transverse_stiffness"])
                * wavenumber
                * wavenumber
                + float(config["endocardial_bending_stiffness"])
                * wavenumber**4
                + spectral_rate * float(config["endocardial_drag"]),
            ),
            dtype=np.complex128,
        )
    )
    boundary_operator = (
        chain_impedance @ displacement_selector
        + (np.eye(2, dtype=np.complex128) + chain_impedance / upper_stiffness)
        @ traction_selector
    )
    chain_affine_source = (
        spectral_rate
        * float(config["endocardial_drag"])
        * affine_first
        * np.asarray((1.0, 0.0), dtype=np.complex128)
    )
    response_matrix = transition_e @ lower_jump @ transition_m @ bottom
    activation_vector = transition_e @ lower_jump @ q_m_activation
    epsilon_vector = (
        transition_e
        @ lower_jump
        @ (transition_m @ bottom_epsilon + q_m_epsilon)
        + q_e_epsilon
    )
    boundary_matrix = boundary_operator @ response_matrix
    boundary_condition_number = float(np.linalg.cond(boundary_matrix))
    if not np.isfinite(boundary_condition_number):
        raise RuntimeError("first-mode boundary matrix is singular")

    def eliminate(source: np.ndarray, extra: np.ndarray) -> np.ndarray:
        bottom_unknown = np.linalg.solve(
            boundary_matrix,
            -(boundary_operator @ source + extra),
        )
        return source + response_matrix @ bottom_unknown

    activation_state = eliminate(
        activation_vector, np.zeros(2, dtype=np.complex128)
    )
    epsilon_state = eliminate(epsilon_vector, chain_affine_source)
    p_activation = complex(activation_state[3])
    p_epsilon = complex(epsilon_state[3])
    zero_response = p_activation * 0.0 + p_epsilon * 0.0
    values = (p_activation, p_epsilon, zero_response, spectral_rate, phi)
    if not all(np.isfinite(value.real) and np.isfinite(value.imag) for value in values):
        raise RuntimeError("non-finite first-mode transfer coefficient")
    return {
        "p_epsilon": p_epsilon,
        "p_activation": p_activation,
        "spectral_rate_sN": spectral_rate,
        "wavenumber": wavenumber,
        "affine_first_coefficient_X1": affine_first,
        "ecm_phi": phi,
        "ecm_lambda": lambda_e,
        "ecm_mu": mu_e,
        "boundary_matrix_condition_number": boundary_condition_number,
        "zero_two_input_response": zero_response,
        "layer_myocardium": detail_m,
        "layer_ecm": detail_e,
    }


def _extraction_self_test() -> dict[str, Any]:
    steps = 128
    segments = 64
    length = 1.0
    x_nodes = np.linspace(-0.5 * length, 0.5 * length, segments + 1)
    theta = 2.0 * math.pi * np.arange(steps) / steps
    wavenumber = 2.0 * math.pi / length
    cosine_coefficient = 0.73 - 0.41j
    sine_coefficient = -0.22 + 0.57j
    complex_field = (
        cosine_coefficient * np.cos(wavenumber * x_nodes)
        + sine_coefficient * np.sin(wavenumber * x_nodes)
    )
    raw = np.real(complex_field[:, None] * np.exp(1.0j * theta)[None, :])
    recovered_field = _fundamental(raw, steps)
    modes = notch._exact_p1_spatial_modes(x_nodes, recovered_field, length)
    p1_factor = float(np.sinc(1.0 / segments) ** 2)
    expected_cosine = cosine_coefficient * p1_factor
    expected_sine = sine_coefficient * p1_factor
    expected_ty1 = 0.5 * (expected_cosine - 1.0j * expected_sine)
    recovered_ty1 = 0.5 * (
        modes["complex_values"]["c_cos"]
        - 1.0j * modes["complex_values"]["c_sin"]
    )
    errors = {
        "time_complex_field": float(np.max(np.abs(recovered_field - complex_field))),
        "c_cos": float(abs(modes["complex_values"]["c_cos"] - expected_cosine)),
        "c_sin": float(abs(modes["complex_values"]["c_sin"] - expected_sine)),
        "t_y1": float(abs(recovered_ty1 - expected_ty1)),
    }
    tolerance = 3.0e-13
    return {
        "pass": max(errors.values()) <= tolerance,
        "tolerance": tolerance,
        "errors": errors,
        "known_t_y1": _complex_record(expected_ty1),
        "recovered_t_y1": _complex_record(recovered_ty1),
        "B1_not_used": True,
    }


def _comparison(prediction: complex, actual: complex) -> dict[str, Any]:
    residual = prediction - actual
    phase_interpretable = abs(prediction) > FLOOR and abs(actual) > FLOOR
    return {
        "prediction_minus_actual": _complex_record(residual),
        "absolute_complex_residual": float(abs(residual)),
        "eta": None,
        "signed_relative_amplitude_difference_using_actual_t_y1": (
            float((abs(prediction) - abs(actual)) / abs(actual))
            if abs(actual) > FLOOR
            else None
        ),
        "phase_prediction_minus_actual_deg": (
            math.degrees(float(np.angle(prediction / actual)))
            if phase_interpretable
            else None
        ),
        "phase_interpretable": phase_interpretable,
        "floor": FLOOR,
    }


def _consistency(extracted: complex, recorded: complex) -> dict[str, Any]:
    difference = abs(extracted - recorded)
    return {
        "absolute_complex_difference": float(difference),
        "relative_difference": float(difference / max(abs(recorded), FLOOR)),
        "tolerance": 1.0e-11,
        "pass": difference <= 1.0e-11,
    }


def run(output_path: Path, code_version: str) -> int:
    start = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[1]
    expected_output = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_path.resolve() != expected_output:
        raise RuntimeError("output boundary mismatch")
    if output_path.exists():
        raise FileExistsError(output_path)
    if code_version != EXPECTED_CODE_VERSION:
        raise RuntimeError("formula code version drift")
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-CPU environment drift: {variable}")
    brief_hash = _sha256(repo_root / BRIEF_RELATIVE)
    if brief_hash != BRIEF_SHA256:
        raise RuntimeError("formula brief hash drift")
    source_runner_hash = _sha256(repo_root / SOURCE_RUNNER)
    if source_runner_hash != SOURCE_RUNNER_SHA256:
        raise RuntimeError("source runner hash drift")
    extraction_test = _extraction_self_test()
    if not extraction_test["pass"]:
        raise RuntimeError("known-phase cosine/sine extraction self-test failed")

    records: list[dict[str, Any]] = []
    internal: dict[tuple[str, float, str], dict[str, complex | float]] = {}
    case_root = repo_root / CASE_ROOT_RELATIVE
    for key in CASE_KEYS:
        if time.perf_counter() - start > POSTPROCESS_BUDGET_SECONDS:
            raise RuntimeError("120-second postprocessing budget exceeded")
        json_path = case_root / f"{key}.json"
        npz_path = case_root / f"{key}.npz"
        if not json_path.is_file() or not npz_path.is_file():
            raise RuntimeError(f"missing direct input for {key}")
        with json_path.open("r", encoding="utf-8") as handle:
            case_json = json.load(handle)
        spec = case_json["spec"]
        if spec["key"] != key or case_json["status"] != "COMPLETED":
            raise RuntimeError(f"case identity/status mismatch for {key}")
        if (
            float(spec["de"]) != 0.2
            or int(spec["steps_per_cycle"]) != 128
            or float(spec["activation_peak"]) != 0.1
            or spec["case_id"] not in {"A1", "S1"}
            or spec["spatial_label"] not in {"S2", "S3"}
            or float(spec["thickness_ratio"])
            not in ({0.21, 0.26, 0.31} if spec["case_id"] == "A1" else {0.26})
        ):
            raise RuntimeError(f"case scope drift for {key}")
        config = case_json["actual_config"]
        steps = int(spec["steps_per_cycle"])
        length = float(config["length"])
        with np.load(npz_path) as arrays:
            required = (
                "activation_two_cycles",
                "limited_shortening_two_cycles",
                "endocardium_ecm_traction_two_cycles",
                "x_interface_nodes",
                "time_two_cycles",
            )
            if any(name not in arrays.files for name in required):
                raise RuntimeError(f"missing raw array for {key}")
            activation_signal = np.asarray(arrays["activation_two_cycles"], dtype=np.float64)
            shortening_signal = np.asarray(
                arrays["limited_shortening_two_cycles"], dtype=np.float64
            )
            x_nodes = np.asarray(arrays["x_interface_nodes"], dtype=np.float64)
            traction = np.asarray(
                arrays["endocardium_ecm_traction_two_cycles"], dtype=np.float64
            ).reshape(len(x_nodes), 2, -1)
            time_values = np.asarray(arrays["time_two_cycles"], dtype=np.float64)
        direct_arrays = (activation_signal, shortening_signal, x_nodes, traction, time_values)
        if not all(np.all(np.isfinite(value)) for value in direct_arrays):
            raise RuntimeError(f"non-finite direct input for {key}")
        if len(time_values) != 2 * steps + 1:
            raise RuntimeError(f"time-series length drift for {key}")
        expected_time_values = np.linspace(
            0.0,
            2.0 * float(config["period"]),
            2 * steps + 1,
        )
        time_axis_error = float(np.max(np.abs(time_values - expected_time_values)))
        time_axis_tolerance = 5.0e-14 * max(1.0, float(config["period"]))
        if time_axis_error > time_axis_tolerance:
            raise RuntimeError(f"time-axis drift for {key}")

        activation_bar = complex(_fundamental(activation_signal, steps)) * float(
            case_json["system"]["active_profile_average"]
        )
        macro_strain = -complex(_fundamental(shortening_signal, steps))
        traction_y_fundamental = _fundamental(traction[:, 1, :], steps)
        modes = notch._exact_p1_spatial_modes(x_nodes, traction_y_fundamental, length)
        c_cos = modes["complex_values"]["c_cos"]
        c_sin = modes["complex_values"]["c_sin"]
        actual_ty1 = 0.5 * (c_cos - 1.0j * c_sin)
        recorded_c_cos = _complex_from_record(case_json["spatial_modes"]["c_cos"])
        recorded_c_sin = _complex_from_record(case_json["spatial_modes"]["c_sin"])
        recorded_ty1 = 0.5 * (recorded_c_cos - 1.0j * recorded_c_sin)
        recorded_activation = complex(
            float(case_json["activation_fundamental"]["real"]),
            float(case_json["activation_fundamental"]["imag"]),
        ) * float(case_json["system"]["active_profile_average"])
        recorded_shortening = complex(
            float(case_json["observables"]["overall_shortening"]["coefficient_real"]),
            float(case_json["observables"]["overall_shortening"]["coefficient_imag"]),
        )
        consistency = {
            "activation_bar": _consistency(activation_bar, recorded_activation),
            "macro_strain": _consistency(macro_strain, -recorded_shortening),
            "c_cos": _consistency(c_cos, recorded_c_cos),
            "c_sin": _consistency(c_sin, recorded_c_sin),
            "t_y1": _consistency(actual_ty1, recorded_ty1),
        }
        if not all(item["pass"] for item in consistency.values()):
            raise RuntimeError(f"raw-array versus JSON mismatch for {key}")

        transfer = _transfer_coefficients(config, steps)
        if abs(transfer["zero_two_input_response"]) > FLOOR:
            raise RuntimeError(f"zero-two-input check failed for {key}")
        activation_first = (
            0.0j
            if spec["case_id"] == "A1"
            else float(config["spatial_activation_contrast"]) * activation_bar / 2.0
        )
        contribution_epsilon = transfer["p_epsilon"] * macro_strain
        contribution_activation = transfer["p_activation"] * activation_first
        conditional_sum = contribution_epsilon + contribution_activation
        comparison = _comparison(conditional_sum, actual_ty1)
        eta_denominator = (
            abs(contribution_epsilon) + abs(contribution_activation) + FLOOR
        )
        comparison["eta"] = float(
            comparison["absolute_complex_residual"] / eta_denominator
        )
        values = (
            activation_bar,
            activation_first,
            macro_strain,
            c_cos,
            c_sin,
            actual_ty1,
            transfer["p_epsilon"],
            transfer["p_activation"],
            contribution_epsilon,
            contribution_activation,
            conditional_sum,
        )
        if not all(np.isfinite(value.real) and np.isfinite(value.imag) for value in values):
            raise RuntimeError(f"non-finite derived value for {key}")
        point = (spec["case_id"], float(spec["thickness_ratio"]), spec["spatial_label"])
        internal[point] = {
            "actual_ty1": actual_ty1,
            "macro_strain": macro_strain,
            "p_epsilon": transfer["p_epsilon"],
            "residual": conditional_sum - actual_ty1,
            "eta": float(comparison["eta"]),
        }
        records.append(
            {
                "case_key": key,
                "spec": spec,
                "input": {
                    "case_json": json_path.relative_to(repo_root).as_posix(),
                    "case_json_sha256": _sha256(json_path),
                    "npz": npz_path.relative_to(repo_root).as_posix(),
                    "npz_sha256": _sha256(npz_path),
                    "raw_array_shapes": {
                        "activation_two_cycles": list(activation_signal.shape),
                        "limited_shortening_two_cycles": list(shortening_signal.shape),
                        "endocardium_ecm_traction_two_cycles": list(traction.shape),
                        "x_interface_nodes": list(x_nodes.shape),
                        "time_two_cycles": list(time_values.shape),
                    },
                    "time_axis_check": {
                        "maximum_absolute_error": time_axis_error,
                        "tolerance": time_axis_tolerance,
                        "pass": True,
                    },
                },
                "parameter_summary": {
                    "config_digest": config["config_digest"],
                    "length": length,
                    "myocardium_thickness": config["myocardium_thickness"],
                    "ecm_thickness": config["ecm_thickness"],
                    "ecm_relaxation_time": config["ecm_relaxation_time"],
                    "endocardial_axial_stiffness": config[
                        "endocardial_axial_stiffness"
                    ],
                    "steps_per_cycle": steps,
                    "active_profile_average": case_json["system"][
                        "active_profile_average"
                    ],
                    "spatial_activation_contrast": config[
                        "spatial_activation_contrast"
                    ],
                },
                "raw_extraction": {
                    "activation_bar": _complex_record(activation_bar),
                    "activation_first_continuous_target": _complex_record(
                        activation_first
                    ),
                    "macro_strain_equals_negative_shortening": _complex_record(
                        macro_strain
                    ),
                    "c_cos": _complex_record(c_cos),
                    "c_sin": _complex_record(c_sin),
                    "actual_t_y1_equals_half_c_cos_minus_i_c_sin": _complex_record(
                        actual_ty1
                    ),
                    "recorded_B1_not_used_as_t_y1": case_json["spatial_modes"][
                        "B1"
                    ],
                    "json_consistency": consistency,
                },
                "transfer": {
                    "p_epsilon": _complex_record(transfer["p_epsilon"]),
                    "p_activation": _complex_record(transfer["p_activation"]),
                    "spectral_rate_sN": _complex_record(
                        transfer["spectral_rate_sN"]
                    ),
                    "wavenumber": transfer["wavenumber"],
                    "affine_first_coefficient_X1": _complex_record(
                        transfer["affine_first_coefficient_X1"]
                    ),
                    "boundary_matrix_condition_number": transfer[
                        "boundary_matrix_condition_number"
                    ],
                    "zero_two_input_response": _complex_record(
                        transfer["zero_two_input_response"]
                    ),
                },
                "coherent_decomposition": {
                    "p_epsilon_times_macro_strain": _complex_record(
                        contribution_epsilon
                    ),
                    "p_activation_times_activation_first": _complex_record(
                        contribution_activation
                    ),
                    "coherent_complex_sum": _complex_record(conditional_sum),
                    "actual_t_y1": _complex_record(actual_ty1),
                    "comparison": comparison,
                    "warning": (
                        "contribution magnitudes are not additive percentages; only the complex sum is physical"
                    ),
                },
            }
        )

    record_by_point = {
        (
            record["spec"]["case_id"],
            float(record["spec"]["thickness_ratio"]),
            record["spec"]["spatial_label"],
        ): record
        for record in records
    }
    pair_diagnostics: list[dict[str, Any]] = []
    for case_id, thickness in (
        ("A1", 0.21),
        ("A1", 0.26),
        ("A1", 0.31),
        ("S1", 0.26),
    ):
        coarse = internal[(case_id, thickness, "S2")]
        fine = internal[(case_id, thickness, "S3")]
        d23 = (
            abs(fine["actual_ty1"] - coarse["actual_ty1"])
            + abs(fine["p_epsilon"])
            * abs(fine["macro_strain"] - coarse["macro_strain"])
        )
        eta_not_decreased = float(fine["eta"]) >= float(coarse["eta"])
        residual_exceeds_d23 = abs(fine["residual"]) > d23
        warning_triggered = eta_not_decreased and residual_exceeds_d23
        diagnostic = {
            "case_id": case_id,
            "thickness_ratio": thickness,
            "D23": float(d23),
            "definition": (
                "|t_y1,S3-t_y1,S2| + |p_epsilon|*|epsilon_S3-epsilon_S2|"
            ),
            "eta_S2": float(coarse["eta"]),
            "eta_S3": float(fine["eta"]),
            "absolute_residual_S2": float(abs(coarse["residual"])),
            "absolute_residual_S3": float(abs(fine["residual"])),
            "eta_S3_not_decreased": eta_not_decreased,
            "absolute_residual_S3_exceeds_D23": residual_exceeds_d23,
            "section_31_4_warning_triggered": warning_triggered,
            "warning_role": (
                "exploratory warning only; triggered is not a theorem against the full discrete system, "
                "and not triggered is not a scientific PASS"
            ),
        }
        pair_diagnostics.append(diagnostic)
        for spatial in ("S2", "S3"):
            record_by_point[(case_id, thickness, spatial)]["paired_D23"] = {
                "D23": float(d23),
                "section_31_4_warning_triggered": warning_triggered,
            }

    elapsed = time.perf_counter() - start
    if elapsed > POSTPROCESS_BUDGET_SECONDS:
        raise RuntimeError("120-second postprocessing budget exceeded")
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        raise RuntimeError("formula brief changed during postprocessing")
    if _sha256(repo_root / SOURCE_RUNNER) != SOURCE_RUNNER_SHA256:
        raise RuntimeError("source runner changed during postprocessing")
    payload = {
        "schema": SCHEMA,
        "status": "COMPLETED_DIAGNOSTIC_NO_SCIENTIFIC_PASS_GATE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "post_hoc_existing_array_no_fit_first_mode_diagnostic",
        "formula": {
            "version": FORMULA_VERSION,
            "code_version": code_version,
            "brief_path": BRIEF_RELATIVE.as_posix(),
            "brief_sha256": BRIEF_SHA256,
            "state": "(U,V,T,S) periodic fluctuation first mode",
            "layer_propagation": "augmented matrix exponential of the continuous spatial state matrix",
            "boundary_solution": "linear solve of the 2x2 boundary system; no explicit inverse",
            "chain_symbols": "continuous k^2 and k^4",
            "observable": "t_y1=(c_cos-i*c_sin)/2 from raw time fundamental and native P1 spatial integration",
            "activation_first": "A1:0; S1:beta*activation_bar/2 continuous target",
            "residual": "actual t_y1 subtracted from coherent conditional prediction",
        },
        "source_runner_summary": {
            "path": SOURCE_RUNNER,
            "sha256": SOURCE_RUNNER_SHA256,
            "runtime_version": SOURCE_RUNTIME_VERSION,
            "source_case_count": 8,
            "source_endpoint_status": "accepted completed v02 cases",
        },
        "runtime": {
            "elapsed_seconds": elapsed,
            "budget_seconds": POSTPROCESS_BUDGET_SECONDS,
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "gpu": "not_used",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy_expm": True,
            "script_path": "scripts/analyze_paper2_first_mode_transfer_v01.py",
            "script_sha256": _sha256(Path(__file__)),
            "extraction_self_test": extraction_test,
            "zero_two_input_checks_pass": all(
                record["transfer"]["zero_two_input_response"]["amplitude"]
                <= FLOOR
                for record in records
            ),
        },
        "direct_input_count": 8,
        "holdouts": "LOCKED_NOT_READ",
        "records": records,
        "paired_D23_diagnostics": pair_diagnostics,
        "aggregate": {
            "maximum_absolute_complex_residual": max(
                record["coherent_decomposition"]["comparison"][
                    "absolute_complex_residual"
                ]
                for record in records
            ),
            "eta_range": [
                min(
                    record["coherent_decomposition"]["comparison"]["eta"]
                    for record in records
                ),
                max(
                    record["coherent_decomposition"]["comparison"]["eta"]
                    for record in records
                ),
            ],
            "warning_trigger_count": sum(
                diagnostic["section_31_4_warning_triggered"]
                for diagnostic in pair_diagnostics
            ),
            "all_json_extraction_consistency_pass": all(
                all(
                    item["pass"]
                    for item in record["raw_extraction"]["json_consistency"].values()
                )
                for record in records
            ),
            "all_values_finite": True,
        },
        "claim_boundary": {
            "no_new_fem_or_system_build": True,
            "no_holdout_read": True,
            "not_a_new_blind_prediction": True,
            "no_fit_scan_root_or_discrete_chain_correction": True,
            "warning_not_triggered_is_not_PASS": True,
            "warning_triggered_is_not_a_theorem_against_full_discrete_system": True,
            "B1_is_not_t_y1": True,
            "coherent_contribution_magnitudes_are_not_additive_percentages": True,
            "not_novelty_or_experimental_validation": True,
        },
    }
    _create_json(output_path, payload)
    print(
        f"ANALYSIS_DONE cases=8 warnings={payload['aggregate']['warning_trigger_count']} "
        f"elapsed={elapsed:.6f}",
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
        report = _extraction_self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if arguments.output is None or arguments.code_version is None:
        parser.error("--output and --code-version are required unless --self-test is used")
    try:
        return run(arguments.output, arguments.code_version)
    except BaseException as error:
        if (
            arguments.output.parent.is_dir()
            and not arguments.output.exists()
            and arguments.output.resolve()
            == (Path(__file__).resolve().parents[1] / OUTPUT_RELATIVE).resolve()
        ):
            _create_json(
                arguments.output,
                {
                    "schema": SCHEMA,
                    "status": "ABORTED_FAIL_CLOSED",
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "holdouts": "LOCKED_NOT_READ",
                    "no_automatic_retry_or_extension": True,
                },
            )
        print(f"ANALYSIS_ABORTED {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
