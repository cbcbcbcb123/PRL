"""Postprocess the eight existing transverse-notch cases with the mean-normal transfer.

No FEM system is built here.  Every signal is re-extracted from the saved raw
time series, and the Section 24 continuous two-layer transfer is evaluated
without fitting.
"""

from __future__ import annotations

import argparse
import cmath
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


SCHEMA = "paper2_mean_normal_transfer_v01"
FORMULA_VERSION = "science_brief_sections_24_25_at_0fa6805d"
EXPECTED_CODE_VERSION = "0fa6805d888e2468b51298d46bb44ff154b499d6"
SOURCE_V02_RUNTIME_VERSION = "7cf40e211ccbd01b5baa60693834ea7907b89405"
SOURCE_PREREGISTRATION_COMMIT = "9842b3bfab7f11e947d0c355fa8b0202a368138f"
BRIEF_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/science_brief.md")
BRIEF_SHA256 = "8e2f0ed04e33cc028aef3291743206e848bf66321c0a577026966d545da5a289"
CASE_ROOT_RELATIVE = Path("results/paper2_transverse_notch/v02_20260905/cases")
OUTPUT_RELATIVE = Path(
    "results/paper2_transverse_notch/v02_20260905/mean_normal_transfer_v01.json"
)
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


def _fundamental(signal: np.ndarray, steps_per_cycle: int) -> np.ndarray:
    values = np.asarray(signal[..., :steps_per_cycle], dtype=np.float64)
    if values.shape[-1] != steps_per_cycle:
        raise ValueError("raw signal does not contain one complete cycle")
    centered = values - np.mean(values, axis=-1, keepdims=True)
    return (2.0 / steps_per_cycle) * np.fft.rfft(centered, axis=-1)[..., 1]


def _p1_mean(x_values: np.ndarray, field_values: np.ndarray, length: float) -> complex:
    x_nodes = np.asarray(x_values, dtype=np.float64)
    field = np.asarray(field_values, dtype=np.complex128)
    if x_nodes.ndim != 1 or field.ndim != 1 or x_nodes.shape != field.shape:
        raise ValueError("P1 mean inputs must be matching one-dimensional arrays")
    if len(x_nodes) < 2 or not np.all(np.diff(x_nodes) > 0.0):
        raise ValueError("interface coordinates are invalid")
    tolerance = 5.0e-12 * max(1.0, abs(length))
    if not math.isclose(float(x_nodes[0]), -0.5 * length, abs_tol=tolerance):
        raise ValueError("left interface endpoint does not equal -L/2")
    if not math.isclose(float(x_nodes[-1]), 0.5 * length, abs_tol=tolerance):
        raise ValueError("right interface endpoint does not equal L/2")
    integral = np.sum(0.5 * (field[:-1] + field[1:]) * np.diff(x_nodes))
    return complex(integral / length)


def _lame_parameters(young_modulus: float, poisson_ratio: float) -> tuple[float, float]:
    shear_modulus = young_modulus / (2.0 * (1.0 + poisson_ratio))
    lame_lambda = (
        young_modulus
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    return lame_lambda, shear_modulus


def _sinhc(value: complex) -> complex:
    if abs(value) < 1.0e-7:
        square = value * value
        return 1.0 + square / 6.0 + square * square / 120.0
    return cmath.sinh(value) / value


def _layer_transfer(
    lame_lambda: complex,
    longitudinal_modulus: complex,
    drag: float,
    omega_discrete: float,
    thickness: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    kappa_squared = 1.0j * omega_discrete * drag / longitudinal_modulus
    kappa = cmath.sqrt(kappa_squared)
    scaled = kappa * thickness
    hyperbolic_cosine = cmath.cosh(scaled)
    hyperbolic_sine_ratio = _sinhc(scaled)
    matrix = np.asarray(
        (
            (
                hyperbolic_cosine,
                thickness * hyperbolic_sine_ratio / longitudinal_modulus,
            ),
            (
                longitudinal_modulus
                * kappa_squared
                * thickness
                * hyperbolic_sine_ratio,
                hyperbolic_cosine,
            ),
        ),
        dtype=np.complex128,
    )
    forcing = np.asarray(
        (
            -lame_lambda
            * thickness
            * hyperbolic_sine_ratio
            / longitudinal_modulus,
            lame_lambda * (1.0 - hyperbolic_cosine),
        ),
        dtype=np.complex128,
    )
    return matrix, forcing, {
        "kappa_squared": _complex_record(kappa_squared),
        "kappa": _complex_record(kappa),
        "kappa_times_thickness": _complex_record(scaled),
    }


def _transfer_coefficients(config: dict[str, Any], steps: int) -> dict[str, Any]:
    length = float(config["length"])
    period = float(config["period"])
    time_step = period / steps
    omega_discrete = 2.0 * math.tan(math.pi / steps) / time_step
    lambda_m, mu_m = _lame_parameters(
        float(config["myocardium_young_modulus"]),
        float(config["myocardium_poisson_ratio"]),
    )
    lambda_equilibrium, mu_equilibrium = _lame_parameters(
        float(config["ecm_equilibrium_young_modulus"]),
        float(config["ecm_equilibrium_poisson_ratio"]),
    )
    lambda_maxwell, mu_maxwell = _lame_parameters(
        float(config["ecm_maxwell_young_modulus"]),
        float(config["ecm_maxwell_poisson_ratio"]),
    )
    relaxation_time = float(config["ecm_relaxation_time"])
    phi_discrete = (
        1.0j * omega_discrete * relaxation_time
        / (1.0 + 1.0j * omega_discrete * relaxation_time)
    )
    lambda_e = lambda_equilibrium + phi_discrete * lambda_maxwell
    mu_e = mu_equilibrium + phi_discrete * mu_maxwell
    longitudinal_m = lambda_m + 2.0 * mu_m
    longitudinal_e = lambda_e + 2.0 * mu_e

    matrix_m, forcing_m, layer_m = _layer_transfer(
        lambda_m,
        longitudinal_m,
        float(config["myocardium_drag"]),
        omega_discrete,
        float(config["myocardium_thickness"]),
    )
    matrix_e, forcing_e, layer_e = _layer_transfer(
        lambda_e,
        longitudinal_e,
        float(config["ecm_drag"]),
        omega_discrete,
        float(config["ecm_thickness"]),
    )
    lower_interface = np.asarray(
        (
            (1.0, 1.0 / float(config["ecm_myocardium_interface_stiffness"])),
            (0.0, 1.0),
        ),
        dtype=np.complex128,
    )
    bottom_vector = np.asarray(
        (1.0, float(config["support_normal_stiffness"])),
        dtype=np.complex128,
    )
    endocardial_impedance = 1.0j * omega_discrete * float(config["endocardial_drag"])
    top_row = np.asarray(
        (
            endocardial_impedance,
            1.0
            + endocardial_impedance
            / float(config["endocardium_ecm_interface_stiffness"]),
        ),
        dtype=np.complex128,
    )
    vector_v = matrix_e @ lower_interface @ matrix_m @ bottom_vector
    vector_wa = matrix_e @ lower_interface @ forcing_m
    vector_wepsilon = vector_wa + forcing_e
    denominator = complex(top_row @ vector_v)
    if abs(denominator) <= FLOOR:
        raise RuntimeError("mean-normal transfer denominator is near zero")
    stress_selector = np.asarray((0.0, 1.0), dtype=np.complex128)

    def coefficient(vector_w: np.ndarray) -> complex:
        return complex(
            stress_selector @ vector_w
            - (stress_selector @ vector_v) * (top_row @ vector_w) / denominator
        )

    p_epsilon = coefficient(vector_wepsilon)
    p_activation = coefficient(vector_wa)

    q_m = longitudinal_m - lambda_m * lambda_m / longitudinal_m
    q_e = longitudinal_e - lambda_e * lambda_e / longitudinal_e
    a_m = float(config["myocardium_thickness"]) * q_m
    k0 = (
        float(config["endocardial_axial_stiffness"])
        + float(config["support_tangential_stiffness"]) * length * length / 12.0
        + 1.0j
        * omega_discrete
        * length
        * length
        / 12.0
        * (
            float(config["myocardium_drag"])
            * float(config["myocardium_thickness"])
            + float(config["endocardial_drag"])
        )
    )
    b_e = q_e + (
        1.0j
        * omega_discrete
        * float(config["ecm_drag"])
        * length
        * length
        / 12.0
    )
    chi0 = complex(
        a_m
        / (a_m + k0 + float(config["ecm_thickness"]) * b_e)
    )
    values = (
        p_epsilon,
        p_activation,
        chi0,
        denominator,
        lambda_e,
        mu_e,
        q_e,
    )
    if not all(np.isfinite(value.real) and np.isfinite(value.imag) for value in values):
        raise RuntimeError("non-finite transfer coefficient")
    return {
        "p_epsilon": p_epsilon,
        "p_activation": p_activation,
        "chi0": chi0,
        "denominator": denominator,
        "omega_discrete": omega_discrete,
        "phi_discrete": phi_discrete,
        "lambda_m": complex(lambda_m),
        "mu_m": complex(mu_m),
        "lambda_e": complex(lambda_e),
        "mu_e": complex(mu_e),
        "Q_m": complex(q_m),
        "Q_e": complex(q_e),
        "K0": complex(k0),
        "B_e": complex(b_e),
        "layer_m": layer_m,
        "layer_e": layer_e,
    }


def _comparison(
    prediction: complex,
    actual: complex,
    actual_quantity: str,
) -> dict[str, Any]:
    residual = prediction - actual
    denominator = abs(actual)
    interpretable = denominator > FLOOR and abs(prediction) > FLOOR
    return {
        "prediction_minus_actual": _complex_record(residual),
        "absolute_complex_residual": float(abs(residual)),
        "relative_complex_residual": (
            float(abs(residual) / denominator) if denominator > FLOOR else None
        ),
        "signed_relative_amplitude_difference": (
            float((abs(prediction) - denominator) / denominator)
            if denominator > FLOOR
            else None
        ),
        "absolute_relative_amplitude_difference": (
            float(abs(abs(prediction) - denominator) / denominator)
            if denominator > FLOOR
            else None
        ),
        "phase_prediction_minus_actual_deg": (
            math.degrees(cmath.phase(prediction / actual)) if interpretable else None
        ),
        "phase_interpretable": interpretable,
        "relative_denominator_definition": f"magnitude of {actual_quantity}",
        "floor": FLOOR,
    }


def _self_test() -> dict[str, Any]:
    steps = 128
    theta = 2.0 * math.pi * np.arange(steps) / steps
    harmonic_errors = {
        "cosine": abs(complex(_fundamental(np.cos(theta), steps)) - 1.0),
        "sine": abs(complex(_fundamental(np.sin(theta), steps)) + 1.0j),
        "constant": abs(complex(_fundamental(np.ones(steps), steps))),
    }
    lame_lambda = 2.1
    longitudinal_modulus = 5.2
    thickness = 0.37
    matrix, forcing, _ = _layer_transfer(
        lame_lambda, longitudinal_modulus, 0.0, 2.0 * math.pi, thickness
    )
    expected_matrix = np.asarray(
        ((1.0, thickness / longitudinal_modulus), (0.0, 1.0)),
        dtype=np.complex128,
    )
    expected_forcing = np.asarray(
        (-lame_lambda * thickness / longitudinal_modulus, 0.0),
        dtype=np.complex128,
    )
    transfer_error = max(
        float(np.max(np.abs(matrix - expected_matrix))),
        float(np.max(np.abs(forcing - expected_forcing))),
    )
    tolerance = 2.0e-13
    passed = max(harmonic_errors.values()) <= tolerance and transfer_error <= tolerance
    return {
        "pass": bool(passed),
        "tolerance": tolerance,
        "harmonic_errors": {
            key: float(value) for key, value in harmonic_errors.items()
        },
        "zero_drag_layer_limit_error": transfer_error,
    }


def _complex_consistency(extracted: complex, recorded: complex) -> dict[str, Any]:
    absolute = abs(extracted - recorded)
    relative = absolute / max(abs(recorded), FLOOR)
    return {
        "absolute_complex_difference": float(absolute),
        "relative_difference": float(relative),
        "tolerance": 1.0e-11,
        "pass": bool(absolute <= 1.0e-11),
    }


def run(output_path: Path, code_version: str) -> int:
    start = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[1]
    expected_output = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_path.resolve() != expected_output:
        raise RuntimeError(f"output boundary mismatch: {output_path.resolve()}")
    if output_path.exists():
        raise FileExistsError(output_path)
    if code_version != EXPECTED_CODE_VERSION:
        raise RuntimeError(f"analysis code version drift: {code_version}")
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
        raise RuntimeError(f"formula brief hash drift: {brief_hash}")
    self_test = _self_test()
    if not self_test["pass"]:
        raise RuntimeError(f"self-test failed: {self_test}")

    records: list[dict[str, Any]] = []
    complex_values: dict[tuple[str, float, str], dict[str, complex]] = {}
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
        if spec["key"] != key:
            raise RuntimeError(f"case identity mismatch for {key}")
        if (
            float(spec["de"]) != 0.2
            or int(spec["steps_per_cycle"]) != 128
            or float(spec["activation_peak"]) != 0.1
            or spec["case_id"] not in {"A1", "S1"}
            or spec["spatial_label"] not in {"S2", "S3"}
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
                raise RuntimeError(f"required raw array missing for {key}")
            activation_signal = np.asarray(arrays["activation_two_cycles"], dtype=np.float64)
            shortening_signal = np.asarray(
                arrays["limited_shortening_two_cycles"], dtype=np.float64
            )
            x_nodes = np.asarray(arrays["x_interface_nodes"], dtype=np.float64)
            traction = np.asarray(
                arrays["endocardium_ecm_traction_two_cycles"], dtype=np.float64
            ).reshape(len(x_nodes), 2, -1)
            time_values = np.asarray(arrays["time_two_cycles"], dtype=np.float64)
        raw_arrays = (activation_signal, shortening_signal, x_nodes, traction, time_values)
        if not all(np.all(np.isfinite(values)) for values in raw_arrays):
            raise RuntimeError(f"non-finite direct input for {key}")
        if len(time_values) != 2 * steps + 1:
            raise RuntimeError(f"unexpected time-series length for {key}")
        if not np.allclose(
            time_values,
            np.linspace(0.0, 2.0 * float(config["period"]), 2 * steps + 1),
            rtol=0.0,
            atol=2.0e-14,
        ):
            raise RuntimeError(f"time axis drift for {key}")

        activation_temporal = complex(_fundamental(activation_signal, steps))
        profile_average = float(case_json["system"]["active_profile_average"])
        mean_activation = activation_temporal * profile_average
        mean_strain = -complex(_fundamental(shortening_signal, steps))
        traction_fundamental_y = _fundamental(traction[:, 1, :], steps)
        actual_c0 = _p1_mean(x_nodes, traction_fundamental_y, length)

        recorded_activation = complex(
            float(case_json["activation_fundamental"]["real"]),
            float(case_json["activation_fundamental"]["imag"]),
        ) * profile_average
        recorded_shortening = complex(
            float(case_json["observables"]["overall_shortening"]["coefficient_real"]),
            float(case_json["observables"]["overall_shortening"]["coefficient_imag"]),
        )
        recorded_c0 = _complex_from_record(case_json["spatial_modes"]["c0"])
        consistency = {
            "mean_activation": _complex_consistency(mean_activation, recorded_activation),
            "mean_strain": _complex_consistency(mean_strain, -recorded_shortening),
            "upper_y_traction_c0": _complex_consistency(actual_c0, recorded_c0),
        }
        if not all(item["pass"] for item in consistency.values()):
            raise RuntimeError(f"raw-array versus JSON extraction mismatch for {key}")

        transfer = _transfer_coefficients(config, steps)
        p_epsilon = transfer["p_epsilon"]
        p_activation = transfer["p_activation"]
        chi0 = transfer["chi0"]
        conditional_c0 = p_epsilon * mean_strain + p_activation * mean_activation
        source_strain = -chi0 * mean_activation
        source_c0 = p_epsilon * source_strain + p_activation * mean_activation
        conditional_comparison = _comparison(
            conditional_c0,
            actual_c0,
            "raw-array actual upper-interface y-traction c0",
        )
        source_comparison = _comparison(
            source_c0,
            actual_c0,
            "raw-array actual upper-interface y-traction c0",
        )
        strain_comparison = _comparison(
            source_strain,
            mean_strain,
            "raw-array actual mean macro strain",
        )
        term_epsilon = p_epsilon * mean_strain
        term_activation = p_activation * mean_activation
        cancellation_denominator = abs(actual_c0)
        cancellation_condition = (
            (abs(term_epsilon) + abs(term_activation)) / cancellation_denominator
            if cancellation_denominator > FLOOR
            else None
        )
        values_to_check = (
            mean_activation,
            mean_strain,
            actual_c0,
            conditional_c0,
            source_strain,
            source_c0,
        )
        if not all(np.isfinite(value.real) and np.isfinite(value.imag) for value in values_to_check):
            raise RuntimeError(f"non-finite derived value for {key}")

        point = (spec["case_id"], float(spec["thickness_ratio"]), spec["spatial_label"])
        complex_values[point] = {
            "actual_c0": actual_c0,
            "conditional_residual": conditional_c0 - actual_c0,
            "source_residual": source_c0 - actual_c0,
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
                },
                "parameter_summary": {
                    "config_digest": config["config_digest"],
                    "length": length,
                    "myocardium_thickness": config["myocardium_thickness"],
                    "ecm_thickness": config["ecm_thickness"],
                    "ecm_relaxation_time": config["ecm_relaxation_time"],
                    "steps_per_cycle": steps,
                    "active_profile_average": profile_average,
                },
                "raw_array_extraction": {
                    "mean_activation": _complex_record(mean_activation),
                    "mean_macro_strain_equals_negative_shortening": _complex_record(mean_strain),
                    "actual_upper_y_traction_c0": _complex_record(actual_c0),
                    "json_consistency": consistency,
                },
                "transfer": {
                    "p_epsilon": _complex_record(p_epsilon),
                    "p_activation": _complex_record(p_activation),
                    "passive_denominator_ell_dot_v": _complex_record(transfer["denominator"]),
                    "chi0": _complex_record(chi0),
                    "omega_discrete": transfer["omega_discrete"],
                    "phi_discrete": _complex_record(transfer["phi_discrete"]),
                    "material": {
                        name: _complex_record(transfer[name])
                        for name in ("lambda_m", "mu_m", "lambda_e", "mu_e", "Q_m", "Q_e", "K0", "B_e")
                    },
                },
                "conditional_mapping": {
                    "c0_conditional": _complex_record(conditional_c0),
                    "comparison_to_actual": conditional_comparison,
                },
                "source_prediction": {
                    "macro_strain_from_minus_chi0_activation": _complex_record(source_strain),
                    "macro_strain_comparison_to_actual": strain_comparison,
                    "c0_source": _complex_record(source_c0),
                    "comparison_to_actual": source_comparison,
                    "scope_warning": (
                        "chi0 ignores macro-to-nonzero-mode feedback; S1 is retained as a negative diagnostic, not a validated autonomous prediction"
                    ),
                },
                "cancellation": {
                    "p_epsilon_times_actual_strain": _complex_record(term_epsilon),
                    "p_activation_times_actual_activation": _complex_record(term_activation),
                    "condition_number": (
                        float(cancellation_condition)
                        if cancellation_condition is not None
                        else None
                    ),
                    "denominator_definition": "magnitude of raw-array actual upper-interface y-traction c0",
                    "denominator_amplitude": float(cancellation_denominator),
                    "interpretable": cancellation_denominator > FLOOR,
                    "floor": FLOOR,
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
    grid_pairs: list[dict[str, Any]] = []
    for case_id, thickness in (
        ("A1", 0.21),
        ("A1", 0.26),
        ("A1", 0.31),
        ("S1", 0.26),
    ):
        coarse_values = complex_values[(case_id, thickness, "S2")]
        fine_values = complex_values[(case_id, thickness, "S3")]
        grid_difference = abs(fine_values["actual_c0"] - coarse_values["actual_c0"])
        grid_record = {
            "case_id": case_id,
            "thickness_ratio": thickness,
            "absolute_complex_S3_minus_S2_actual_c0": float(grid_difference),
            "difference_role": "two-grid absolute difference proxy, not a rigorous error bound",
            "conditional_residual": {},
            "source_residual": {},
        }
        for spatial, values in (("S2", coarse_values), ("S3", fine_values)):
            conditional_abs = abs(values["conditional_residual"])
            source_abs = abs(values["source_residual"])
            conditional_ratio = conditional_abs / grid_difference if grid_difference > FLOOR else None
            source_ratio = source_abs / grid_difference if grid_difference > FLOOR else None
            grid_record["conditional_residual"][spatial] = {
                "absolute": float(conditional_abs),
                "over_grid_difference": (
                    float(conditional_ratio) if conditional_ratio is not None else None
                ),
            }
            grid_record["source_residual"][spatial] = {
                "absolute": float(source_abs),
                "over_grid_difference": float(source_ratio) if source_ratio is not None else None,
            }
            record_by_point[(case_id, thickness, spatial)]["grid_pair"] = {
                "absolute_complex_S3_minus_S2_actual_c0": float(grid_difference),
                "conditional_residual_over_grid_difference": (
                    float(conditional_ratio) if conditional_ratio is not None else None
                ),
                "source_residual_over_grid_difference": (
                    float(source_ratio) if source_ratio is not None else None
                ),
                "near_zero_grid_difference": grid_difference <= FLOOR,
            }
        s2_residual = abs(coarse_values["conditional_residual"])
        s3_residual = abs(fine_values["conditional_residual"])
        grid_record["conditional_residual_S2_over_S3"] = (
            float(s2_residual / s3_residual) if s3_residual > FLOOR else None
        )
        grid_pairs.append(grid_record)

    conditional_abs = [
        record["conditional_mapping"]["comparison_to_actual"]["absolute_complex_residual"]
        for record in records
    ]
    conditional_relative = [
        record["conditional_mapping"]["comparison_to_actual"]["relative_complex_residual"]
        for record in records
        if record["conditional_mapping"]["comparison_to_actual"]["relative_complex_residual"] is not None
    ]
    s3_records = [record for record in records if record["spec"]["spatial_label"] == "S3"]
    s2_records = [record for record in records if record["spec"]["spatial_label"] == "S2"]
    elapsed = time.perf_counter() - start
    if elapsed > POSTPROCESS_BUDGET_SECONDS:
        raise RuntimeError("120-second postprocessing budget exceeded")
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        raise RuntimeError("formula brief changed during postprocessing")
    payload = {
        "schema": SCHEMA,
        "status": "COMPLETED_DIAGNOSTIC_NO_NEW_PASS_GATE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "post_hoc_existing_array_diagnostic",
        "formula": {
            "version": FORMULA_VERSION,
            "brief_path": BRIEF_RELATIVE.as_posix(),
            "brief_sha256": BRIEF_SHA256,
            "analysis_code_version": code_version,
            "source_v02_runtime_version": SOURCE_V02_RUNTIME_VERSION,
            "source_preregistration_commit": SOURCE_PREREGISTRATION_COMMIT,
            "conditional_equation": "c0_cond = p_epsilon*epsilon_bar + p_activation*a_bar",
            "source_equation": "epsilon_src = -chi0*a_bar; c0_src = p_epsilon*epsilon_src + p_activation*a_bar",
            "time_fundamental": "2/N times first rFFT coefficient after temporal mean removal, first cycle samples only",
            "space_mean": "exact trapezoidal integral of the native P1 nodal field divided by L",
            "residual_sign": "prediction minus raw-array actual",
        },
        "runtime": {
            "elapsed_seconds": elapsed,
            "budget_seconds": POSTPROCESS_BUDGET_SECONDS,
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "gpu": "not_used",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "self_test": self_test,
            "script_path": "scripts/analyze_paper2_mean_normal_transfer_v01.py",
            "script_sha256": _sha256(Path(__file__)),
        },
        "direct_input_count": 8,
        "holdouts": "LOCKED_NOT_READ",
        "records": records,
        "grid_pairs": grid_pairs,
        "aggregate": {
            "maximum_conditional_absolute_complex_residual_all": max(conditional_abs),
            "maximum_conditional_relative_complex_residual_all": max(conditional_relative),
            "maximum_conditional_absolute_complex_residual_S2": max(
                record["conditional_mapping"]["comparison_to_actual"]["absolute_complex_residual"]
                for record in s2_records
            ),
            "maximum_conditional_absolute_complex_residual_S3": max(
                record["conditional_mapping"]["comparison_to_actual"]["absolute_complex_residual"]
                for record in s3_records
            ),
            "conditional_residual_S2_over_S3_by_physical_point": [
                record["conditional_residual_S2_over_S3"] for record in grid_pairs
            ],
            "maximum_cancellation_condition_number": max(
                record["cancellation"]["condition_number"] for record in records
            ),
            "all_json_extraction_consistency_pass": all(
                all(
                    item["pass"]
                    for item in record["raw_array_extraction"]["json_consistency"].values()
                )
                for record in records
            ),
            "all_values_finite": True,
        },
        "claim_boundary": {
            "no_new_fem": True,
            "no_holdout_read": True,
            "not_a_new_preregistered_pass_gate": True,
            "conditional_mapping_uses_actual_macro_strain": True,
            "chi0_source_prediction_is_separate_and_can_fail": True,
            "S1_negative_diagnostic_retained": True,
            "does_not_explain_nonzero_B1_or_local_loading": True,
            "not_continuous_notch_or_novelty_certification": True,
            "S2_S3_difference_is_not_a_rigorous_error_bound": True,
        },
    }
    _create_json(output_path, payload)
    print(
        f"ANALYSIS_DONE cases={len(records)} elapsed={elapsed:.6f} "
        f"max_conditional_S3={payload['aggregate']['maximum_conditional_absolute_complex_residual_S3']:.6e}",
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
                },
            )
        print(f"ANALYSIS_ABORTED {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
