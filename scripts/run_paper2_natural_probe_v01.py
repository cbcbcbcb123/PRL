from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy
from scipy.integrate import solve_ivp


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "project_control/prl_independent_theory_mainline_plan_v04.md"
BRIEF = ROOT / "results/paper2_science_pilot/v01_20260905/science_brief.md"
STATUS = ROOT / "project_control/CURRENT_STATUS.md"
FROZEN_INPUT = ROOT / "results/paper2_rest_length_write_read/v01_20260907/summary.json"
MODEL_SOURCE = ROOT / "scripts/run_paper2_rest_length_write_read_v01.py"
OUTPUT_DIRECTORY = ROOT / "results/paper2_natural_probe/v01_20260907"
OUTPUT = OUTPUT_DIRECTORY / "summary.json"

EXPECTED_HEAD = "f2c5590ea99e1bc15be422c6a3e876b8c4a65df2"
EXPECTED_HASHES = {
    PLAN: "b2503629516cc6bb9f73ddd48ee7e9bb8e6348850ea756010beb7dbb1f1294df",
    BRIEF: "a68506b0cc44ee17cc44925400779c27d57ceb5ada7d2cc61a8dcd2dbad5e4ad",
    STATUS: "aef999d23e4d4854c9f3a07a7c0e9d192c4b96ae4b5bdc7fc841fbe9f5d8dd29",
    FROZEN_INPUT: "38dfc26c9d8596ebedbaad974276b1c4a60c6f4a84c42e477bca866f019b9bd7",
    MODEL_SOURCE: "ab3c0d8db1998523d98a497ca3d969e1517012306a564e99f9959f23acfd500e",
}

PROBE_AMPLITUDE = 1.0e-5
OMEGA = 0.01
CYCLES = 3
POINTS_PER_CYCLE = 129
RTOL = 1.0e-9
STATE_ATOL = 1.0e-12
LEDGER_ATOL = 1.0e-15
MAX_SOLVE_SECONDS = 60.0

THRESHOLDS = {
    "energy_balance_relative": 1.0e-6,
    "dissipation_floor": -1.0e-14,
    "fit_relative_rms": 1.0e-3,
    "even_over_odd_harmonic_rms": 1.0e-2,
    "trained_r_drift_fraction": 1.0e-2,
    "nonlinear_amplitude_prediction_relative": 1.0e-2,
    "nonlinear_phase_prediction_degrees": 0.5,
    "effect_prediction_relative": 0.1,
    "E2_gain_trained_reference_relative": 1.0e-5,
}


class BudgetExceeded(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_model() -> Any:
    sys.dont_write_bytecode = True
    specification = importlib.util.spec_from_file_location("frozen_rest_length_model", MODEL_SOURCE)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot import frozen rest-length model")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _peak_memory() -> tuple[int | None, str]:
    if os.name != "nt":
        return None, "unavailable_non_windows"

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel = ctypes.windll.kernel32
    process_api = ctypes.windll.psapi
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    process_api.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    process_api.GetProcessMemoryInfo.restype = ctypes.c_int
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not process_api.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None, "unavailable_GetProcessMemoryInfo_failed"
    return int(counters.PeakWorkingSetSize), "windows_peak_working_set"


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _phase_degrees(value: complex) -> float:
    return float(np.degrees(np.angle(value)))


def _phase_difference_degrees(value: float, reference: float) -> float:
    return float((value - reference + 180.0) % 360.0 - 180.0)


def _frozen_states(data: dict[str, Any], model: Any) -> dict[str, dict[str, np.ndarray | float]]:
    reference = {"q": np.asarray((model.PARAMETERS.s0, model.PARAMETERS.h0)), "r": model.PARAMETERS.r0}
    states = {"nonlinear_reference": reference, "E2_reference": reference}
    for source_name, target_name in (("nonlinear_F0", "nonlinear_trained"), ("E2_F0", "E2_trained")):
        record = data["histories"][source_name]["true_final_state"]
        states[target_name] = {"q": np.asarray(record["q"], dtype=float), "r": float(record["r"])}
    return states


def _conditional_q(model_name: str, state: dict[str, Any], data: dict[str, Any], model: Any) -> np.ndarray:
    if model_name == "nonlinear" and state["label"] == "trained":
        return np.asarray(data["histories"]["nonlinear_F0"]["conditional_static_diagnostic_same_r"]["q_star"])
    if model_name == "E2" and state["label"] == "trained":
        return np.asarray(data["histories"]["E2_F0"]["conditional_static_diagnostic_same_r"]["q_star"])
    return np.asarray((model.PARAMETERS.s0, model.PARAMETERS.h0))


def _linear_prediction(model_name: str, q_equilibrium: np.ndarray, r_value: float, coefficients: dict[str, Any], model: Any) -> dict[str, Any]:
    parameters = model.PARAMETERS
    if model_name == "nonlinear":
        matrix_q = model._nonlinear_hessian(q_equilibrium, r_value, parameters)
        direction = q_equilibrium / np.linalg.norm(q_equilibrium)
    else:
        matrix_q = np.asarray(coefficients["K"])
        direction = np.asarray(coefficients["direction_g"])
    coupling = 2.0 * parameters.k * direction
    d_value = 2.0 * parameters.k
    joint_hessian = np.block([[matrix_q, -coupling[:, None]], [-coupling[None, :], np.asarray([[d_value]])]])
    jacobian = np.block([
        [-matrix_q, coupling[:, None]],
        [parameters.mu * coupling[None, :], np.asarray([[-parameters.mu * d_value]])],
    ])
    input_vector = np.asarray((1.0, 0.0, 0.0))
    state_gain = np.linalg.solve(1j * OMEGA * np.eye(3) - jacobian, input_vector)
    tension_row = np.asarray((parameters.k * direction[0], parameters.k * direction[1], -parameters.k))
    h_s = complex(state_gain[0])
    h_t = complex(tension_row @ state_gain)
    return {
        "q_equilibrium": q_equilibrium.tolist(),
        "r": r_value,
        "matrix_q": matrix_q.tolist(),
        "joint_hessian": joint_hessian.tolist(),
        "joint_hessian_eigenvalues": np.linalg.eigvalsh(joint_hessian).tolist(),
        "jacobian": jacobian.tolist(),
        "jacobian_eigenvalues": [_complex_record(complex(value)) for value in np.linalg.eigvals(jacobian)],
        "H_s": _complex_record(h_s), "H_s_abs": abs(h_s), "H_s_phase_deg": _phase_degrees(h_s),
        "H_t": _complex_record(h_t), "H_t_abs": abs(h_t), "H_t_phase_deg": _phase_degrees(h_t),
    }


def _energy_and_gradient(model_name: str, q_value: np.ndarray, r_value: float, coefficients: dict[str, Any], model: Any) -> tuple[float, np.ndarray, float]:
    if model_name == "nonlinear":
        energy = model._nonlinear_energy(q_value, r_value, model.PARAMETERS)
        q_gradient, r_gradient = model._nonlinear_gradient(q_value, r_value, model.PARAMETERS)
    else:
        energy = model._e2_energy(q_value, r_value, coefficients, model.PARAMETERS)
        q_gradient, r_gradient = model._e2_gradient(q_value, r_value, coefficients, model.PARAMETERS)
    return float(energy), np.asarray(q_gradient), float(r_gradient)


def _tension(model_name: str, q_value: np.ndarray, r_value: float, coefficients: dict[str, Any], model: Any) -> float:
    if model_name == "nonlinear":
        return float(model.PARAMETERS.k * (np.linalg.norm(q_value) - r_value))
    displacement = q_value - np.asarray((model.PARAMETERS.s0, model.PARAMETERS.h0))
    state = r_value - model.PARAMETERS.r0
    return float(model.PARAMETERS.k * (coefficients["direction_g"] @ displacement - state))


def _hessians(model_name: str, q_value: np.ndarray, r_value: float, coefficients: dict[str, Any], model: Any) -> tuple[np.ndarray, np.ndarray]:
    if model_name == "nonlinear":
        matrix_q = model._nonlinear_hessian(q_value, r_value, model.PARAMETERS)
        direction = q_value / np.linalg.norm(q_value)
    else:
        matrix_q = np.asarray(coefficients["K"])
        direction = np.asarray(coefficients["direction_g"])
    coupling = 2.0 * model.PARAMETERS.k * direction
    joint = np.block([[matrix_q, -coupling[:, None]], [-coupling[None, :], np.asarray([[2.0 * model.PARAMETERS.k]])]])
    return matrix_q, joint


def _events() -> tuple[Callable[[float, np.ndarray], float], Callable[[float, np.ndarray], float]]:
    def height(_: float, state: np.ndarray) -> float:
        return float(state[1])

    def length(_: float, state: np.ndarray) -> float:
        return float(math.hypot(state[0], state[1]))

    height.terminal = True
    length.terminal = True
    height.direction = -1.0
    length.direction = -1.0
    return height, length


def _run_trajectory(model_name: str, state_label: str, sigma: int, initial: dict[str, Any], coefficients: dict[str, Any], model: Any, deadline: float) -> dict[str, Any]:
    period = 2.0 * math.pi / OMEGA
    total_time = CYCLES * period
    force_scale = sigma * PROBE_AMPLITUDE

    def right_hand_side(time_value: float, state: np.ndarray) -> np.ndarray:
        if time.perf_counter() > deadline:
            raise BudgetExceeded("formal cumulative solve_ivp budget exceeded")
        q_value = state[:2]
        r_value = float(state[2])
        force = force_scale * math.sin(OMEGA * time_value)
        _, q_gradient, r_gradient = _energy_and_gradient(model_name, q_value, r_value, coefficients, model)
        q_rate = np.asarray((force, 0.0)) - q_gradient
        r_rate = -model.PARAMETERS.mu * r_gradient
        return np.asarray((q_rate[0], q_rate[1], r_rate, force * q_rate[0], q_rate @ q_rate, model.PARAMETERS.mu * r_gradient * r_gradient))

    times = np.linspace(0.0, total_time, CYCLES * (POINTS_PER_CYCLE - 1) + 1)
    initial_vector = np.asarray((initial["q"][0], initial["q"][1], initial["r"], 0.0, 0.0, 0.0))
    solution = solve_ivp(
        right_hand_side, (0.0, total_time), initial_vector, method="Radau", t_eval=times,
        rtol=RTOL, atol=np.asarray((STATE_ATOL, STATE_ATOL, STATE_ATOL, LEDGER_ATOL, LEDGER_ATOL, LEDGER_ATOL)),
        max_step=period / 128.0, events=_events(),
    )
    if not solution.success or len(solution.t) != len(times):
        raise RuntimeError(f"trajectory {model_name}/{state_label}/{sigma} failed: {solution.message}")

    energies, tensions, min_q_eigen, min_joint_eigen = [], [], math.inf, math.inf
    for index in range(solution.y.shape[1]):
        q_value = solution.y[:2, index]
        r_value = float(solution.y[2, index])
        energy, _, _ = _energy_and_gradient(model_name, q_value, r_value, coefficients, model)
        energies.append(energy)
        tensions.append(_tension(model_name, q_value, r_value, coefficients, model))
        q_hessian, joint_hessian = _hessians(model_name, q_value, r_value, coefficients, model)
        min_q_eigen = min(min_q_eigen, float(np.min(np.linalg.eigvalsh(q_hessian))))
        min_joint_eigen = min(min_joint_eigen, float(np.min(np.linalg.eigvalsh(joint_hessian))))
    initial_energy = energies[0]
    final_energy = energies[-1]
    work, d_q, d_r = map(float, solution.y[3:6, -1])
    balance = work - (final_energy - initial_energy) - d_q - d_r
    scale = max(abs(work), abs(final_energy - initial_energy), d_q + d_r, 1.0e-12)
    sparse = []
    for index, time_value in enumerate(solution.t):
        sparse.append({
            "time": float(time_value), "force": force_scale * math.sin(OMEGA * time_value),
            "s": float(solution.y[0, index]), "h": float(solution.y[1, index]), "r": float(solution.y[2, index]),
            "tension": tensions[index], "energy": energies[index], "W": float(solution.y[3, index]),
            "D_q": float(solution.y[4, index]), "D_r": float(solution.y[5, index]),
        })
    return {
        "model": model_name, "state": state_label, "sigma": sigma,
        "initial_state": {"q": np.asarray(initial["q"]).tolist(), "r": float(initial["r"])},
        "final_state": {"q": solution.y[:2, -1].tolist(), "r": float(solution.y[2, -1])},
        "solver": {"method": "Radau", "success": True, "nfev": int(solution.nfev), "njev": int(solution.njev), "nlu": int(solution.nlu), "saved_points": len(solution.t)},
        "domain_and_stability": {
            "minimum_height": float(np.min(solution.y[1])),
            "minimum_side_length": float(np.min(np.hypot(solution.y[0], solution.y[1]))),
            "minimum_q_hessian_eigenvalue": min_q_eigen,
            "minimum_joint_hessian_eigenvalue": min_joint_eigen,
            "events": [len(values) for values in solution.t_events],
        },
        "energy_ledger": {"initial_energy": initial_energy, "final_energy": final_energy, "W": work, "D_q": d_q, "D_r": d_r, "balance_error": balance, "balance_relative": abs(balance) / scale},
        "sparse_trajectory": sparse,
    }


def _fit_centered_response(plus: dict[str, Any], minus: dict[str, Any], zero: dict[str, Any], output_name: str) -> dict[str, Any]:
    time_values = np.asarray([item["time"] for item in plus["sparse_trajectory"]])
    plus_values = np.asarray([item[output_name] for item in plus["sparse_trajectory"]])
    minus_values = np.asarray([item[output_name] for item in minus["sparse_trajectory"]])
    zero_values = np.asarray([item[output_name] for item in zero["sparse_trajectory"]])
    odd = (plus_values - minus_values) / (2.0 * PROBE_AMPLITUDE)
    even = (plus_values + minus_values - 2.0 * zero_values) / (2.0 * PROBE_AMPLITUDE)
    window = time_values >= (2.0 * math.pi / OMEGA - 1.0e-12)
    fitted_time = time_values[window]
    centered_time = fitted_time - np.mean(fitted_time)
    design = np.column_stack((np.ones(len(fitted_time)), centered_time, np.sin(OMEGA * fitted_time), np.cos(OMEGA * fitted_time)))
    coefficients, _, _, _ = np.linalg.lstsq(design, odd[window], rcond=None)
    harmonic = coefficients[2] * design[:, 2] + coefficients[3] * design[:, 3]
    residual = odd[window] - design @ coefficients
    harmonic_rms = float(np.sqrt(np.mean(harmonic * harmonic)))
    residual_relative = float(np.sqrt(np.mean(residual * residual)) / harmonic_rms)
    even_ratio = float(np.sqrt(np.mean(even[window] * even[window])) / harmonic_rms)
    gain = complex(coefficients[2], coefficients[3])
    return {
        "fit_window": {"start": float(fitted_time[0]), "finish": float(fitted_time[-1]), "points": len(fitted_time), "discarded_cycles": 1, "fitted_cycles": 2},
        "fit_columns": ["constant", "centered_time", "sin", "cos"], "fit_coefficients": coefficients.tolist(),
        "H": _complex_record(gain), "amplitude": abs(gain), "phase_degrees": _phase_degrees(gain),
        "harmonic_rms": harmonic_rms, "fit_residual_relative_rms": residual_relative,
        "even_over_odd_fitted_harmonic_rms": even_ratio,
        "odd_window": odd[window].tolist(), "even_window_not_detrended": even[window].tolist(),
    }


def _analyze_group(trajectories: dict[str, dict[str, Any]], model_name: str, state_label: str, prediction: dict[str, Any], initial_magnitude: float) -> dict[str, Any]:
    prefix = f"{model_name}_{state_label}"
    plus, minus, zero = (trajectories[f"{prefix}_{suffix}"] for suffix in ("plus", "minus", "zero"))
    fits = {name: _fit_centered_response(plus, minus, zero, name) for name in ("s", "tension")}
    r_plus = np.asarray([item["r"] for item in plus["sparse_trajectory"]])
    r_minus = np.asarray([item["r"] for item in minus["sparse_trajectory"]])
    r_zero = np.asarray([item["r"] for item in zero["sparse_trajectory"]])
    drift = float(np.max(np.abs(r_zero - r_zero[0])))
    plus_difference = float(np.max(np.abs(r_plus - r_zero)))
    minus_difference = float(np.max(np.abs(r_minus - r_zero)))
    record = {
        "fits": fits,
        "no_probe_background": {"r_start": float(r_zero[0]), "r_finish": float(r_zero[-1]), "maximum_absolute_r_drift": drift},
        "probe_relative_to_background": {"plus_max_abs_delta_r": plus_difference, "minus_max_abs_delta_r": minus_difference},
        "prediction": prediction,
    }
    if state_label == "trained":
        record["trained_r_drift_fractions_of_initial_m_wait"] = {
            "no_probe": drift / initial_magnitude, "plus_vs_background": plus_difference / initial_magnitude,
            "minus_vs_background": minus_difference / initial_magnitude,
        }
    else:
        record["reference_r_changes_absolute_only"] = {"no_probe": drift, "plus_vs_background": plus_difference, "minus_vs_background": minus_difference}
    return record


def _evaluate(trajectories: dict[str, dict[str, Any]], groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    individual = {}
    for key, group in groups.items():
        prediction = group["prediction"]
        item = {}
        for output_name, prediction_key in (("s", "H_s"), ("tension", "H_t")):
            fit = group["fits"][output_name]
            expected = complex(prediction[prediction_key]["real"], prediction[prediction_key]["imag"])
            item[output_name] = {
                "amplitude_prediction_relative_error": abs(fit["amplitude"] - abs(expected)) / abs(expected),
                "phase_prediction_difference_degrees": _phase_difference_degrees(fit["phase_degrees"], _phase_degrees(expected)),
                "fit_residual_relative_rms": fit["fit_residual_relative_rms"],
                "even_over_odd_harmonic_rms": fit["even_over_odd_fitted_harmonic_rms"],
            }
        individual[key] = item

    nonlinear_reference = groups["nonlinear_reference"]["fits"]
    nonlinear_trained = groups["nonlinear_trained"]["fits"]
    dynamic_stiffness_change = nonlinear_reference["s"]["amplitude"] / nonlinear_trained["s"]["amplitude"] - 1.0
    tension_change = nonlinear_trained["tension"]["amplitude"] / nonlinear_reference["tension"]["amplitude"] - 1.0
    predicted_stiffness_change = 0.01331026361043897
    predicted_tension_change = -0.00404946523427618
    effects = {
        "dynamic_stiffness_relative_change": dynamic_stiffness_change,
        "tension_gain_relative_change": tension_change,
        "predicted_dynamic_stiffness_relative_change": predicted_stiffness_change,
        "predicted_tension_gain_relative_change": predicted_tension_change,
        "dynamic_stiffness_effect_prediction_relative_error": abs(dynamic_stiffness_change - predicted_stiffness_change) / abs(predicted_stiffness_change),
        "tension_effect_prediction_relative_error": abs(tension_change - predicted_tension_change) / abs(predicted_tension_change),
        "H_s_phase_trained_minus_reference_degrees_descriptive": _phase_difference_degrees(nonlinear_trained["s"]["phase_degrees"], nonlinear_reference["s"]["phase_degrees"]),
        "H_t_phase_trained_minus_reference_degrees_descriptive": _phase_difference_degrees(nonlinear_trained["tension"]["phase_degrees"], nonlinear_reference["tension"]["phase_degrees"]),
    }
    e2 = {}
    for output_name in ("s", "tension"):
        reference = groups["E2_reference"]["fits"][output_name]
        trained = groups["E2_trained"]["fits"][output_name]
        ref_gain = complex(reference["H"]["real"], reference["H"]["imag"])
        trained_gain = complex(trained["H"]["real"], trained["H"]["imag"])
        e2[output_name] = abs(trained_gain - ref_gain) / abs(ref_gain)

    trajectory_checks = {
        key: {
            "energy": value["energy_ledger"]["balance_relative"] <= THRESHOLDS["energy_balance_relative"],
            "dissipation": value["energy_ledger"]["D_q"] >= THRESHOLDS["dissipation_floor"] and value["energy_ledger"]["D_r"] >= THRESHOLDS["dissipation_floor"],
            "domain": value["domain_and_stability"]["minimum_height"] > 0 and value["domain_and_stability"]["minimum_side_length"] > 0 and value["domain_and_stability"]["events"] == [0, 0],
            "q_hessian": value["domain_and_stability"]["minimum_q_hessian_eigenvalue"] > 0,
            "joint_hessian": value["domain_and_stability"]["minimum_joint_hessian_eigenvalue"] > 0,
        }
        for key, value in trajectories.items()
    }
    nonlinear_prediction_pass = all(
        individual[f"nonlinear_{state}"][output]["amplitude_prediction_relative_error"] <= THRESHOLDS["nonlinear_amplitude_prediction_relative"]
        and abs(individual[f"nonlinear_{state}"][output]["phase_prediction_difference_degrees"]) <= THRESHOLDS["nonlinear_phase_prediction_degrees"]
        for state in ("reference", "trained") for output in ("s", "tension")
    )
    fit_pass = all(
        item[output]["fit_residual_relative_rms"] <= THRESHOLDS["fit_relative_rms"]
        and item[output]["even_over_odd_harmonic_rms"] <= THRESHOLDS["even_over_odd_harmonic_rms"]
        for item in individual.values() for output in ("s", "tension")
    )
    trained_drift_pass = all(
        value <= THRESHOLDS["trained_r_drift_fraction"]
        for key in ("nonlinear_trained", "E2_trained")
        for value in groups[key]["trained_r_drift_fractions_of_initial_m_wait"].values()
    )
    checks = {
        "individual_group_output_checks": individual,
        "nonlinear_effects": effects,
        "E2_trained_reference_complex_gain_relative_differences": e2,
        "trajectory_checks": trajectory_checks,
        "all_12_trajectory_checks_pass": all(all(values.values()) for values in trajectory_checks.values()),
        "all_fit_and_even_contamination_checks_pass": fit_pass,
        "trained_r_drift_checks_pass": trained_drift_pass,
        "nonlinear_single_state_prediction_checks_pass": nonlinear_prediction_pass,
        "nonlinear_opposite_effect_signs_pass": dynamic_stiffness_change > 0 and tension_change < 0,
        "nonlinear_effect_prediction_checks_pass": abs(effects["dynamic_stiffness_effect_prediction_relative_error"]) <= THRESHOLDS["effect_prediction_relative"] and abs(effects["tension_effect_prediction_relative_error"]) <= THRESHOLDS["effect_prediction_relative"],
        "E2_fixed_incremental_response_check_pass": all(value <= THRESHOLDS["E2_gain_trained_reference_relative"] for value in e2.values()),
    }
    checks["all_preregistered_checks_pass"] = all(value for key, value in checks.items() if key.endswith("_pass"))
    return checks


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite value")
        return value
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(type(value).__name__)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.check_only == arguments.execute:
        parser.error("select exactly one mode")
    return arguments


def main() -> None:
    arguments = _arguments()
    actual_hashes = {path: _sha(path) for path in EXPECTED_HASHES}
    mismatches = {str(path): {"expected": EXPECTED_HASHES[path], "actual": actual_hashes[path]} for path in EXPECTED_HASHES if actual_hashes[path] != EXPECTED_HASHES[path]}
    if _head() != EXPECTED_HEAD or mismatches:
        raise RuntimeError(f"frozen input mismatch: head={_head()}, mismatches={mismatches}")
    frozen = json.loads(FROZEN_INPUT.read_text(encoding="utf-8"))
    model = _load_model()
    coefficients = model._initial_coefficients(model.PARAMETERS)
    raw_states = _frozen_states(frozen, model)
    state_records = {
        "nonlinear_reference": {**raw_states["nonlinear_reference"], "label": "reference"},
        "nonlinear_trained": {**raw_states["nonlinear_trained"], "label": "trained"},
        "E2_reference": {**raw_states["E2_reference"], "label": "reference"},
        "E2_trained": {**raw_states["E2_trained"], "label": "trained"},
    }
    predictions = {
        key: _linear_prediction(key.split("_")[0], _conditional_q(key.split("_")[0], value, frozen, model), float(value["r"]), coefficients, model)
        for key, value in state_records.items()
    }
    planned = [f"{model_name}_{state}_{suffix}" for model_name in ("nonlinear", "E2") for state in ("trained", "reference") for suffix in ("plus", "minus", "zero")]
    if arguments.check_only:
        print(json.dumps(_json_ready({"status": "CHECK_ONLY_NO_TRAJECTORY_OR_OUTPUT", "HEAD": _head(), "hashes": {str(path.relative_to(ROOT)): value for path, value in actual_hashes.items()}, "trajectory_count": len(planned), "planned_trajectories": planned, "predictions": predictions, "thresholds": THRESHOLDS}), indent=2))
        return
    if OUTPUT_DIRECTORY.exists():
        raise RuntimeError(f"create-only output exists: {OUTPUT_DIRECTORY}")

    start_utc = datetime.now(timezone.utc)
    timer = time.perf_counter()
    deadline = timer + MAX_SOLVE_SECONDS
    trajectories: dict[str, Any] = {}
    failures: list[str] = []
    try:
        for model_name in ("nonlinear", "E2"):
            for state_label in ("trained", "reference"):
                initial = state_records[f"{model_name}_{state_label}"]
                for sigma, suffix in ((1, "plus"), (-1, "minus"), (0, "zero")):
                    key = f"{model_name}_{state_label}_{suffix}"
                    trajectories[key] = _run_trajectory(model_name, state_label, sigma, initial, coefficients, model, deadline)
    except Exception as error:
        failures.append(f"{type(error).__name__}: {error}")
    solve_seconds = time.perf_counter() - timer
    groups: dict[str, Any] = {}
    checks = None
    if len(trajectories) == 12 and not failures:
        for model_name in ("nonlinear", "E2"):
            for state_label in ("trained", "reference"):
                key = f"{model_name}_{state_label}"
                initial_magnitude = abs(float(state_records[key]["r"]) - model.PARAMETERS.r0)
                groups[key] = _analyze_group(trajectories, model_name, state_label, predictions[key], initial_magnitude)
        checks = _evaluate(trajectories, groups)
        if not checks["all_preregistered_checks_pass"]:
            failures.append("one or more preregistered gates failed")
    if solve_seconds > MAX_SOLVE_SECONDS:
        failures.append("formal cumulative solve time exceeded")
    peak_bytes, peak_method = _peak_memory()
    source_hashes = {str(path.relative_to(ROOT)): value for path, value in actual_hashes.items()}
    source_hashes[str(Path(__file__).resolve().relative_to(ROOT))] = _sha(Path(__file__))
    payload = {
        "schema": "paper2_natural_probe_v01", "status": "COMPLETED_WITH_FAIL_CLOSED_FAILURE" if failures else "NUMERICAL_GATES_PASS_PENDING_SUPERVISOR_REVIEW",
        "layered_status": {"implementation": "passed", "12_trajectories": "passed" if len(trajectories) == 12 else "failed_or_incomplete", "preregistered_gates": "passed" if checks and checks["all_preregistered_checks_pass"] else "failed_or_not_run", "scientific_acceptance": "pending_supervisor_review", "original_four_holdouts": "not_run"},
        "failures": failures,
        "claim_boundary": {"natural_state_evolution_during_probe": True, "conditional_state_freezing": False, "natural_dynamic_experiment_validated": False, "ECM_or_active_myocardium_present": False, "trained_reference_phase_difference_resolved": False, "DCM_necessity_or_Nature_Physics_mechanism": False},
        "version": {"prediction_HEAD": EXPECTED_HEAD, "source_sha256": source_hashes, "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
        "protocol": {"probe_amplitude": PROBE_AMPLITUDE, "omega": OMEGA, "period": 2 * math.pi / OMEGA, "cycles": CYCLES, "discarded_cycles": 1, "fit_cycles": 2, "saved_points_each": CYCLES * (POINTS_PER_CYCLE - 1) + 1, "rtol": RTOL, "state_atol": STATE_ATOL, "ledger_atol": LEDGER_ATOL, "max_step": 2 * math.pi / OMEGA / 128},
        "frozen_initial_states": {key: {"q": np.asarray(value["q"]).tolist(), "r": float(value["r"]), "source": "section78_true_final_state" if value["label"] == "trained" else "common_reference"} for key, value in state_records.items()},
        "preregistered_linear_predictions_recomputed": predictions,
        "trajectories": trajectories, "group_analyses": groups, "checks": checks,
        "execution": {"start_utc": start_utc.isoformat(), "finish_utc": datetime.now(timezone.utc).isoformat(), "formal_solve_ivp_seconds": solve_seconds, "budget_seconds": MAX_SOLVE_SECONDS, "trajectory_count": len(trajectories), "peak_working_set_bytes": peak_bytes, "peak_working_set_gib": None if peak_bytes is None else peak_bytes / 1024**3, "peak_memory_method": peak_method, "memory_budget_gib": 8, "memory_budget_enforced": False, "GPU_used": False, "thread_environment": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}},
        "thresholds": THRESHOLDS,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=False)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(_json_ready(payload), handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(OUTPUT), "status": payload["status"], "solve_seconds": solve_seconds, "trajectory_count": len(trajectories), "failures": failures}))


if __name__ == "__main__":
    main()
