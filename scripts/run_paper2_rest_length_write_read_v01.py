from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy
from scipy import optimize
from scipy.integrate import solve_ivp


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "project_control/prl_independent_theory_mainline_plan_v04.md"
BRIEF_PATH = REPO_ROOT / "results/paper2_science_pilot/v01_20260905/science_brief.md"
STATUS_PATH = REPO_ROOT / "project_control/CURRENT_STATUS.md"
OUTPUT_DIRECTORY = REPO_ROOT / "results/paper2_rest_length_write_read/v01_20260907"
OUTPUT_PATH = OUTPUT_DIRECTORY / "summary.json"

STATE_ATOL = 1.0e-11
LEDGER_ATOL = 1.0e-14
STRICT_STATE_ATOL = 1.0e-13
STRICT_LEDGER_ATOL = 1.0e-16
BASE_RTOL = 1.0e-8
STRICT_RTOL = 1.0e-10
CALCULATION_BUDGET_SECONDS = 60.0


@dataclass(frozen=True)
class Parameters:
    a: float = 1.0
    h0: float = 1.0
    k: float = 1.0
    c: float = 1.0
    eta: float = 0.02
    mu: float = 1.0e-4
    s0: float = 1.0
    r0: float = math.sqrt(2.0)
    theta0: float = math.pi / 4.0
    force: float = 5.0e-4


PARAMETERS = Parameters()


class CalculationBudgetExceeded(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def _peak_working_set_bytes() -> tuple[int | None, str]:
    if os.name != "nt":
        return None, "unavailable_non_windows"

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    success = psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    )
    if not success:
        return None, "unavailable_GetProcessMemoryInfo_failed"
    return int(counters.PeakWorkingSetSize), "windows_peak_working_set"


def _nonlinear_energy(q_value: np.ndarray, r_value: float, parameters: Parameters) -> float:
    s_value, h_value = q_value
    length = math.hypot(float(s_value), float(h_value))
    theta = math.atan2(float(s_value), float(h_value))
    return float(
        parameters.k * (length - r_value) ** 2
        + 0.5 * parameters.c * (h_value - parameters.h0) ** 2
        + 0.5 * parameters.eta * (theta - parameters.theta0) ** 2
    )


def _nonlinear_gradient(q_value: np.ndarray, r_value: float, parameters: Parameters) -> tuple[np.ndarray, float]:
    s_value, h_value = q_value
    length_squared = s_value * s_value + h_value * h_value
    length = math.sqrt(float(length_squared))
    direction = np.asarray((s_value, h_value), dtype=np.float64) / length
    theta = math.atan2(float(s_value), float(h_value))
    theta_gradient = np.asarray((h_value, -s_value), dtype=np.float64) / length_squared
    q_gradient = (
        2.0 * parameters.k * (length - r_value) * direction
        + np.asarray((0.0, parameters.c * (h_value - parameters.h0)))
        + parameters.eta * (theta - parameters.theta0) * theta_gradient
    )
    r_gradient = -2.0 * parameters.k * (length - r_value)
    return q_gradient, float(r_gradient)


def _nonlinear_hessian_general(
    q_value: np.ndarray, r_value: complex | float, parameters: Parameters
) -> np.ndarray:
    s_value, h_value = q_value
    value_dtype = np.result_type(q_value.dtype, type(r_value), np.float64)
    length_squared = s_value * s_value + h_value * h_value
    length = np.sqrt(length_squared)
    direction = np.asarray((s_value, h_value), dtype=value_dtype) / length
    identity = np.eye(2, dtype=value_dtype)
    projection = np.outer(direction, direction)
    stretch = 2.0 * parameters.k * (
        projection + ((length - r_value) / length) * (identity - projection)
    )
    area = np.asarray(((0.0, 0.0), (0.0, parameters.c)), dtype=value_dtype)
    theta = np.arctan(s_value / h_value)
    theta_gradient = np.asarray((h_value, -s_value), dtype=value_dtype) / length_squared
    length_fourth = length_squared * length_squared
    theta_hessian = np.asarray(
        (
            (-2.0 * s_value * h_value / length_fourth, (s_value * s_value - h_value * h_value) / length_fourth),
            ((s_value * s_value - h_value * h_value) / length_fourth, 2.0 * s_value * h_value / length_fourth),
        ),
        dtype=value_dtype,
    )
    angle = parameters.eta * (
        np.outer(theta_gradient, theta_gradient)
        + (theta - parameters.theta0) * theta_hessian
    )
    return stretch + area + angle


def _nonlinear_hessian(q_value: np.ndarray, r_value: float, parameters: Parameters) -> np.ndarray:
    return np.asarray(
        np.real_if_close(_nonlinear_hessian_general(q_value.astype(np.float64), r_value, parameters)),
        dtype=np.float64,
    )


def _initial_coefficients(parameters: Parameters) -> dict[str, Any]:
    q_initial = np.asarray((parameters.s0, parameters.h0), dtype=np.float64)
    e_s = np.asarray((1.0, 0.0), dtype=np.float64)
    length = float(np.linalg.norm(q_initial))
    direction = q_initial / length
    matrix = _nonlinear_hessian(q_initial, parameters.r0, parameters)
    d_value = 2.0 * parameters.k
    coupling = d_value * direction
    matrix_inverse_e = np.linalg.solve(matrix, e_s)
    matrix_inverse_b = np.linalg.solve(matrix, coupling)
    compliance = float(e_s @ matrix_inverse_e)
    effective_stiffness = 1.0 / compliance
    tension_gain = float(parameters.k * direction @ matrix_inverse_e)
    k_mem = float(d_value - coupling @ matrix_inverse_b)
    b_force = float(coupling @ matrix_inverse_e)
    lambda_fast = float(np.min(np.linalg.eigvalsh(matrix)))

    q_derivative = matrix_inverse_b
    complex_step = 1.0e-30
    q_complex = q_initial.astype(np.complex128) + 1j * complex_step * q_derivative
    r_complex = complex(parameters.r0, complex_step)
    matrix_derivative = np.imag(
        _nonlinear_hessian_general(q_complex, r_complex, parameters)
    ) / complex_step
    direction_derivative = (
        (np.eye(2) - np.outer(direction, direction)) @ q_derivative / length
    )
    inverse_e_derivative = -np.linalg.solve(matrix, matrix_derivative @ matrix_inverse_e)
    stiffness_derivative = float(
        effective_stiffness**2 * matrix_inverse_e @ matrix_derivative @ matrix_inverse_e
    )
    tension_derivative = float(
        parameters.k
        * (direction_derivative @ matrix_inverse_e + direction @ inverse_e_derivative)
    )

    loading_duration = 0.1 / (parameters.mu * k_mem)
    waiting_duration = 50.0 / lambda_fast
    predicted_m_wait = float(
        (b_force * parameters.force / k_mem)
        * (1.0 - math.exp(-parameters.mu * k_mem * loading_duration))
        * math.exp(-parameters.mu * k_mem * waiting_duration)
    )
    predicted_delta_stiffness = stiffness_derivative * predicted_m_wait
    predicted_delta_tension_gain = tension_derivative * predicted_m_wait
    return {
        "K": matrix,
        "e_s": e_s,
        "direction_g": direction,
        "d": d_value,
        "b": coupling,
        "K_eff": effective_stiffness,
        "A": tension_gain,
        "dK_eff_dr": stiffness_derivative,
        "dA_dr": tension_derivative,
        "k_mem": k_mem,
        "b_F": b_force,
        "lambda_f": lambda_fast,
        "mu_d_over_lambda_f": parameters.mu * d_value / lambda_fast,
        "loading_duration": loading_duration,
        "waiting_duration": waiting_duration,
        "predicted_m_wait": predicted_m_wait,
        "predicted_delta_K_eff": predicted_delta_stiffness,
        "predicted_delta_A": predicted_delta_tension_gain,
        "q_equilibrium_derivative_dr": q_derivative,
        "K_total_derivative_dr": matrix_derivative,
    }


def _e2_energy(q_value: np.ndarray, r_value: float, coefficients: dict[str, Any], parameters: Parameters) -> float:
    displacement = q_value - np.asarray((parameters.s0, parameters.h0))
    state = r_value - parameters.r0
    return float(
        0.5 * displacement @ coefficients["K"] @ displacement
        - state * coefficients["b"] @ displacement
        + 0.5 * coefficients["d"] * state * state
    )


def _e2_gradient(q_value: np.ndarray, r_value: float, coefficients: dict[str, Any], parameters: Parameters) -> tuple[np.ndarray, float]:
    displacement = q_value - np.asarray((parameters.s0, parameters.h0))
    state = r_value - parameters.r0
    q_gradient = coefficients["K"] @ displacement - coefficients["b"] * state
    r_gradient = float(-coefficients["b"] @ displacement + coefficients["d"] * state)
    return q_gradient, r_gradient


def _conditional_readout(
    model: str,
    r_value: float,
    starting_q: np.ndarray,
    coefficients: dict[str, Any],
    parameters: Parameters,
) -> dict[str, Any]:
    e_s = coefficients["e_s"]
    if model == "nonlinear":
        result = optimize.root(
            lambda q_value: _nonlinear_gradient(q_value, r_value, parameters)[0],
            starting_q,
            jac=lambda q_value: _nonlinear_hessian(q_value, r_value, parameters),
            method="hybr",
            options={"xtol": 1.0e-12, "maxfev": 200},
        )
        q_star = np.asarray(result.x, dtype=np.float64)
        gradient, _ = _nonlinear_gradient(q_star, r_value, parameters)
        matrix = _nonlinear_hessian(q_star, r_value, parameters)
        direction = q_star / np.linalg.norm(q_star)
        tension_gain = float(parameters.k * direction @ np.linalg.solve(matrix, e_s))
        solver_record = {
            "method": "scipy.optimize.root_hybr_with_analytic_jacobian",
            "success": bool(result.success),
            "status": int(result.status),
            "message": str(result.message),
            "nfev": int(result.nfev),
            "njev": None if not hasattr(result, "njev") else int(result.njev),
        }
    elif model == "E2":
        state = r_value - parameters.r0
        displacement = np.linalg.solve(coefficients["K"], coefficients["b"] * state)
        q_star = np.asarray((parameters.s0, parameters.h0)) + displacement
        gradient, _ = _e2_gradient(q_star, r_value, coefficients, parameters)
        matrix = coefficients["K"]
        tension_gain = float(
            parameters.k
            * coefficients["direction_g"]
            @ np.linalg.solve(matrix, e_s)
        )
        solver_record = {
            "method": "exact_fixed_E2_linear_conditional_solve",
            "success": True,
            "status": 0,
            "message": "exact linear conditional equilibrium",
            "nfev": 0,
            "njev": 0,
        }
    else:
        raise ValueError(f"unknown model {model}")
    eigenvalues = np.linalg.eigvalsh(matrix)
    compliance = float(e_s @ np.linalg.solve(matrix, e_s))
    return {
        "q_star": q_star.tolist(),
        "equilibrium_residual_l2": float(np.linalg.norm(gradient)),
        "hessian": matrix.tolist(),
        "hessian_eigenvalues": eigenvalues.tolist(),
        "hessian_positive_definite": bool(np.min(eigenvalues) > 0.0),
        "K_eff": float(1.0 / compliance),
        "A_single_side": tension_gain,
        "solver": solver_record,
    }


def _trajectory_rhs(
    model: str,
    force: float,
    coefficients: dict[str, Any],
    parameters: Parameters,
    deadline: float,
) -> Callable[[float, np.ndarray], np.ndarray]:
    def evaluate(_: float, state: np.ndarray) -> np.ndarray:
        if time.perf_counter() > deadline:
            raise CalculationBudgetExceeded("cumulative 60-second calculation budget exceeded")
        q_value = state[:2]
        r_value = float(state[2])
        if model == "nonlinear":
            q_gradient, r_gradient = _nonlinear_gradient(q_value, r_value, parameters)
        elif model == "E2":
            q_gradient, r_gradient = _e2_gradient(q_value, r_value, coefficients, parameters)
        else:
            raise ValueError(f"unknown model {model}")
        q_rate = np.asarray((force, 0.0)) - q_gradient
        r_rate = -parameters.mu * r_gradient
        return np.asarray(
            (
                q_rate[0],
                q_rate[1],
                r_rate,
                force * q_rate[0],
                float(q_rate @ q_rate),
                parameters.mu * r_gradient * r_gradient,
            ),
            dtype=np.float64,
        )

    return evaluate


def _positive_height_event(_: float, state: np.ndarray) -> float:
    return float(state[1])


def _positive_length_event(_: float, state: np.ndarray) -> float:
    return float(math.hypot(state[0], state[1]))


_positive_height_event.terminal = True
_positive_height_event.direction = -1.0
_positive_length_event.terminal = True
_positive_length_event.direction = -1.0


def _integrate_history(
    name: str,
    model: str,
    force: float,
    strict: bool,
    coefficients: dict[str, Any],
    parameters: Parameters,
    deadline: float,
) -> dict[str, Any]:
    loading_duration = coefficients["loading_duration"]
    waiting_duration = coefficients["waiting_duration"]
    divisor = 64 if strict else 32
    relative_tolerance = STRICT_RTOL if strict else BASE_RTOL
    absolute_tolerance = np.asarray(
        [
            STRICT_STATE_ATOL if strict else STATE_ATOL,
            STRICT_STATE_ATOL if strict else STATE_ATOL,
            STRICT_STATE_ATOL if strict else STATE_ATOL,
            STRICT_LEDGER_ATOL if strict else LEDGER_ATOL,
            STRICT_LEDGER_ATOL if strict else LEDGER_ATOL,
            STRICT_LEDGER_ATOL if strict else LEDGER_ATOL,
        ],
        dtype=np.float64,
    )
    initial_state = np.asarray(
        (parameters.s0, parameters.h0, parameters.r0, 0.0, 0.0, 0.0),
        dtype=np.float64,
    )
    load_times = np.linspace(0.0, loading_duration, 25)
    load_solution = solve_ivp(
        _trajectory_rhs(model, force, coefficients, parameters, deadline),
        (0.0, loading_duration),
        initial_state,
        method="Radau",
        t_eval=load_times,
        rtol=relative_tolerance,
        atol=absolute_tolerance,
        max_step=loading_duration / divisor,
        events=(_positive_height_event, _positive_length_event),
    )
    if not load_solution.success or load_solution.t[-1] < loading_duration:
        raise RuntimeError(f"{name} loading segment failed: {load_solution.message}")
    wait_times = np.linspace(0.0, waiting_duration, 17)
    wait_solution = solve_ivp(
        _trajectory_rhs(model, 0.0, coefficients, parameters, deadline),
        (0.0, waiting_duration),
        load_solution.y[:, -1],
        method="Radau",
        t_eval=wait_times,
        rtol=relative_tolerance,
        atol=absolute_tolerance,
        max_step=waiting_duration / divisor,
        events=(_positive_height_event, _positive_length_event),
    )
    if not wait_solution.success or wait_solution.t[-1] < waiting_duration:
        raise RuntimeError(f"{name} waiting segment failed: {wait_solution.message}")

    final_state = wait_solution.y[:, -1]
    q_final = final_state[:2]
    r_final = float(final_state[2])
    conditional = _conditional_readout(
        model, r_final, q_final, coefficients, parameters
    )
    q_star = np.asarray(conditional["q_star"])
    if model == "nonlinear":
        initial_energy = _nonlinear_energy(initial_state[:2], initial_state[2], parameters)
        final_energy = _nonlinear_energy(q_final, r_final, parameters)
    else:
        initial_energy = _e2_energy(initial_state[:2], initial_state[2], coefficients, parameters)
        final_energy = _e2_energy(q_final, r_final, coefficients, parameters)
    work = float(final_state[3])
    q_dissipation = float(final_state[4])
    r_dissipation = float(final_state[5])
    energy_change = final_energy - initial_energy
    balance_error = work - energy_change - q_dissipation - r_dissipation
    balance_scale = max(
        abs(work), abs(energy_change), q_dissipation + r_dissipation, 1.0e-12
    )

    trajectory_time = np.concatenate(
        (load_solution.t, loading_duration + wait_solution.t[1:])
    )
    trajectory_state = np.concatenate(
        (load_solution.y, wait_solution.y[:, 1:]), axis=1
    )
    trajectory_force = np.concatenate(
        (np.full(load_solution.t.shape, force), np.zeros(wait_solution.t[1:].shape))
    )
    trajectory_lengths = np.hypot(trajectory_state[0], trajectory_state[1])
    reference_state = np.asarray((parameters.s0, parameters.h0, parameters.r0))[:, None]
    reference_deviation = trajectory_state[:3] - reference_state
    sparse_trajectory = []
    for index, time_value in enumerate(trajectory_time):
        q_value = trajectory_state[:2, index]
        r_value = float(trajectory_state[2, index])
        energy = (
            _nonlinear_energy(q_value, r_value, parameters)
            if model == "nonlinear"
            else _e2_energy(q_value, r_value, coefficients, parameters)
        )
        sparse_trajectory.append(
            {
                "time": float(time_value),
                "force": float(trajectory_force[index]),
                "s": float(q_value[0]),
                "h": float(q_value[1]),
                "r": r_value,
                "energy": energy,
                "work": float(trajectory_state[3, index]),
                "D_q": float(trajectory_state[4, index]),
                "D_r": float(trajectory_state[5, index]),
            }
        )

    return {
        "name": name,
        "model": model,
        "force": force,
        "strict_integration": strict,
        "integration": {
            "method": "Radau",
            "rtol": relative_tolerance,
            "atol_state": float(absolute_tolerance[0]),
            "atol_ledgers": float(absolute_tolerance[3]),
            "loading_max_step": loading_duration / divisor,
            "waiting_max_step": waiting_duration / divisor,
            "loading": {
                "success": bool(load_solution.success),
                "message": str(load_solution.message),
                "nfev": int(load_solution.nfev),
                "njev": int(load_solution.njev),
                "nlu": int(load_solution.nlu),
            },
            "waiting": {
                "success": bool(wait_solution.success),
                "message": str(wait_solution.message),
                "nfev": int(wait_solution.nfev),
                "njev": int(wait_solution.njev),
                "nlu": int(wait_solution.nlu),
            },
        },
        "true_final_state": {
            "q": q_final.tolist(),
            "r": r_final,
            "m_wait": r_final - parameters.r0,
            "q_minus_conditional_q_star": (q_final - q_star).tolist(),
            "q_minus_conditional_q_star_l2": float(np.linalg.norm(q_final - q_star)),
        },
        "trajectory_domain_and_locality": {
            "minimum_sampled_height": float(np.min(trajectory_state[1])),
            "minimum_sampled_side_length": float(np.min(trajectory_lengths)),
            "positive_height_event_count": int(sum(len(values) for values in load_solution.t_events[:1]))
            + int(sum(len(values) for values in wait_solution.t_events[:1])),
            "positive_length_event_count": int(sum(len(values) for values in load_solution.t_events[1:]))
            + int(sum(len(values) for values in wait_solution.t_events[1:])),
            "height_and_length_remained_positive": bool(
                np.min(trajectory_state[1]) > 0.0
                and np.min(trajectory_lengths) > 0.0
                and all(len(values) == 0 for values in load_solution.t_events)
                and all(len(values) == 0 for values in wait_solution.t_events)
            ),
            "maximum_sampled_absolute_component_offset_from_reference": float(
                np.max(np.abs(reference_deviation))
            ),
            "maximum_sampled_l2_offset_from_reference": float(
                np.max(np.linalg.norm(reference_deviation, axis=0))
            ),
        },
        "conditional_static_diagnostic_same_r": conditional,
        "readout_changes_from_initial": {
            "delta_K_eff": float(conditional["K_eff"] - coefficients["K_eff"]),
            "delta_A": float(conditional["A_single_side"] - coefficients["A"]),
        },
        "energy_ledger": {
            "initial_energy": initial_energy,
            "final_energy": final_energy,
            "delta_energy": energy_change,
            "input_work": work,
            "D_q": q_dissipation,
            "D_r": r_dissipation,
            "balance_error": balance_error,
            "balance_relative": abs(balance_error) / balance_scale,
            "dissipation_nonnegative": bool(
                q_dissipation >= -1.0e-14 and r_dissipation >= -1.0e-14
            ),
        },
        "sparse_trajectory": sparse_trajectory,
    }


def _relative_error(value: float, reference: float) -> float | None:
    if abs(reference) <= np.finfo(np.float64).tiny:
        return None
    return abs(value - reference) / abs(reference)


def _evaluate_checks(histories: dict[str, dict[str, Any]], coefficients: dict[str, Any]) -> dict[str, Any]:
    full = histories["nonlinear_F0"]
    half = histories["nonlinear_F0_over_2"]
    zero = histories["nonlinear_zero"]
    strict = histories["nonlinear_F0_strict"]
    e2_value = histories["E2_F0"]

    def quantities(history: dict[str, Any]) -> np.ndarray:
        return np.asarray(
            (
                history["true_final_state"]["m_wait"],
                history["readout_changes_from_initial"]["delta_K_eff"],
                history["readout_changes_from_initial"]["delta_A"],
            )
        )

    full_values = quantities(full)
    half_values = quantities(half)
    strict_values = quantities(strict)
    prediction = np.asarray(
        (
            coefficients["predicted_m_wait"],
            coefficients["predicted_delta_K_eff"],
            coefficients["predicted_delta_A"],
        )
    )
    prediction_errors = np.abs(full_values - prediction) / np.abs(prediction)
    half_scaling_errors = np.abs(half_values - 0.5 * full_values) / np.abs(0.5 * full_values)
    strict_errors = np.abs(strict_values - full_values) / np.abs(full_values)
    effect_to_strict_difference = np.abs(full_values) / np.maximum(
        np.abs(strict_values - full_values), np.finfo(np.float64).tiny
    )

    zero_state_offset = max(
        abs(zero["true_final_state"]["q"][0] - PARAMETERS.s0),
        abs(zero["true_final_state"]["q"][1] - PARAMETERS.h0),
        abs(zero["true_final_state"]["r"] - PARAMETERS.r0),
    )
    zero_readout_offset = max(
        abs(zero["readout_changes_from_initial"]["delta_K_eff"]),
        abs(zero["readout_changes_from_initial"]["delta_A"]),
    )
    e2_readout_offset = max(
        abs(e2_value["readout_changes_from_initial"]["delta_K_eff"]),
        abs(e2_value["readout_changes_from_initial"]["delta_A"]),
    )
    all_ledgers_pass = all(
        history["energy_ledger"]["balance_relative"] <= 1.0e-6
        and history["energy_ledger"]["dissipation_nonnegative"]
        for history in histories.values()
    )
    all_conditionals_pass = all(
        history["conditional_static_diagnostic_same_r"]["equilibrium_residual_l2"] <= 1.0e-10
        and history["conditional_static_diagnostic_same_r"]["hessian_positive_definite"]
        and history["conditional_static_diagnostic_same_r"]["solver"]["success"]
        for history in histories.values()
    )
    all_trajectories_remain_in_domain = all(
        history["trajectory_domain_and_locality"]["height_and_length_remained_positive"]
        for history in histories.values()
    )
    checks = {
        "quantity_order": ["m_wait", "delta_K_eff", "delta_A"],
        "nonlinear_F0_values": full_values.tolist(),
        "preregistered_first_order_predictions": prediction.tolist(),
        "prediction_relative_errors": prediction_errors.tolist(),
        "prediction_within_5_percent": bool(np.all(prediction_errors <= 0.05)),
        "required_signs_pass": bool(
            full_values[0] > 0.0 and full_values[1] > 0.0 and full_values[2] < 0.0
        ),
        "half_amplitude_relative_deviation_from_half_full": half_scaling_errors.tolist(),
        "half_amplitude_within_5_percent": bool(np.all(half_scaling_errors <= 0.05)),
        "strict_relative_differences": strict_errors.tolist(),
        "strict_within_1_percent": bool(np.all(strict_errors <= 0.01)),
        "effect_over_strict_absolute_difference": effect_to_strict_difference.tolist(),
        "effect_at_least_10x_strict_difference": bool(
            np.all(effect_to_strict_difference >= 10.0)
        ),
        "zero_loading_state_max_abs_offset": float(zero_state_offset),
        "zero_loading_readout_max_abs_increment": float(zero_readout_offset),
        "zero_loading_within_1e_minus_9": bool(
            zero_state_offset <= 1.0e-9 and zero_readout_offset <= 1.0e-9
        ),
        "E2_readout_max_abs_increment": float(e2_readout_offset),
        "E2_readout_within_1e_minus_9": bool(e2_readout_offset <= 1.0e-9),
        "all_energy_ledgers_pass": all_ledgers_pass,
        "all_conditional_static_diagnostics_pass": all_conditionals_pass,
        "all_trajectories_positive_height_and_length": all_trajectories_remain_in_domain,
    }
    checks["all_preregistered_numerical_checks_pass"] = bool(
        checks["prediction_within_5_percent"]
        and checks["required_signs_pass"]
        and checks["half_amplitude_within_5_percent"]
        and checks["strict_within_1_percent"]
        and checks["effect_at_least_10x_strict_difference"]
        and checks["zero_loading_within_1e_minus_9"]
        and checks["E2_readout_within_1e_minus_9"]
        and all_ledgers_pass
        and all_conditionals_pass
        and all_trajectories_remain_in_domain
    )
    return checks


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON value rejected")
        return value
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _prediction_public_record(coefficients: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_ready(value)
        for key, value in coefficients.items()
        if key not in {"e_s", "direction_g", "b", "q_equilibrium_derivative_dr", "K_total_derivative_dr"}
    } | {
        "e_s": coefficients["e_s"].tolist(),
        "direction_g": coefficients["direction_g"].tolist(),
        "b": coefficients["b"].tolist(),
        "q_equilibrium_derivative_dr": coefficients["q_equilibrium_derivative_dr"].tolist(),
        "K_total_derivative_dr": coefficients["K_total_derivative_dr"].tolist(),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prediction-commit")
    parser.add_argument("--prediction-brief-sha256")
    arguments = parser.parse_args()
    if arguments.check_only == arguments.execute:
        parser.error("choose exactly one of --check-only or --execute")
    if arguments.execute and (
        not arguments.prediction_commit or not arguments.prediction_brief_sha256
    ):
        parser.error("--execute requires prediction commit and brief SHA-256")
    return arguments


def main() -> None:
    arguments = _parse_arguments()
    coefficients = _initial_coefficients(PARAMETERS)
    if arguments.check_only:
        print(
            json.dumps(
                {
                    "status": "IMPLEMENTATION_CHECK_ONLY_NO_TRAJECTORY",
                    "output_created": False,
                    "fixed_parameters": PARAMETERS.__dict__,
                    "recomputed_prediction": _prediction_public_record(coefficients),
                    "planned_histories": [
                        "nonlinear_F0",
                        "nonlinear_F0_over_2",
                        "nonlinear_zero",
                        "nonlinear_F0_strict",
                        "E2_F0",
                    ],
                },
                indent=2,
            )
        )
        return

    if OUTPUT_DIRECTORY.exists() or OUTPUT_PATH.exists():
        raise RuntimeError(f"create-only output already exists: {OUTPUT_DIRECTORY}")
    current_head = _git_head()
    current_brief_hash = _sha256(BRIEF_PATH)
    if current_head != arguments.prediction_commit:
        raise RuntimeError(
            f"prediction commit mismatch: expected {arguments.prediction_commit}, actual {current_head}"
        )
    if current_brief_hash != arguments.prediction_brief_sha256.lower():
        raise RuntimeError(
            "prediction brief hash mismatch: "
            f"expected {arguments.prediction_brief_sha256.lower()}, actual {current_brief_hash}"
        )

    execution_start = datetime.now(timezone.utc)
    calculation_timer = time.perf_counter()
    deadline = calculation_timer + CALCULATION_BUDGET_SECONDS
    histories: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    history_definitions = (
        ("nonlinear_F0", "nonlinear", PARAMETERS.force, False),
        ("nonlinear_F0_over_2", "nonlinear", PARAMETERS.force / 2.0, False),
        ("nonlinear_zero", "nonlinear", 0.0, False),
        ("nonlinear_F0_strict", "nonlinear", PARAMETERS.force, True),
        ("E2_F0", "E2", PARAMETERS.force, False),
    )
    for name, model, force, strict in history_definitions:
        try:
            histories[name] = _integrate_history(
                name, model, force, strict, coefficients, PARAMETERS, deadline
            )
        except CalculationBudgetExceeded as error:
            failures.append(f"{name}: {error}")
            break
        except Exception as error:
            failures.append(f"{name}: {type(error).__name__}: {error}")
            break
    calculation_seconds = time.perf_counter() - calculation_timer
    execution_finish = datetime.now(timezone.utc)

    numerical_checks = None
    if len(histories) == len(history_definitions) and not failures:
        numerical_checks = _evaluate_checks(histories, coefficients)
    if calculation_seconds > CALCULATION_BUDGET_SECONDS:
        failures.append("cumulative calculation budget exceeded")
    if numerical_checks is not None and not numerical_checks["all_preregistered_numerical_checks_pass"]:
        failures.append("one or more preregistered numerical checks failed")

    peak_bytes, peak_method = _peak_working_set_bytes()
    source_hashes = {
        "scripts/run_paper2_rest_length_write_read_v01.py": _sha256(Path(__file__)),
        "project_control/prl_independent_theory_mainline_plan_v04.md": _sha256(PLAN_PATH),
        "results/paper2_science_pilot/v01_20260905/science_brief.md": current_brief_hash,
        "project_control/CURRENT_STATUS.md": _sha256(STATUS_PATH),
    }
    if failures:
        status = "COMPLETED_WITH_FAIL_CLOSED_FAILURE"
    else:
        status = "NUMERICAL_CHECKS_PASS_PENDING_SUPERVISOR_REVIEW"
    payload = {
        "schema": "paper2_rest_length_write_read_v01",
        "status": status,
        "layered_status": {
            "implementation": "passed",
            "five_trajectory_histories": "passed" if len(histories) == 5 else "failed_or_incomplete",
            "preregistered_numerical_checks": "passed"
            if numerical_checks and numerical_checks["all_preregistered_numerical_checks_pass"]
            else "failed_or_not_run",
            "scientific_acceptance": "pending_supervisor_review",
            "natural_dynamic_probe_experiment": "not_run",
            "original_four_holdouts": "not_run",
        },
        "failures": failures,
        "scientific_question": "Can the fixed finite-geometry rest-length model write a temporary state under one loading-wait protocol and show opposite conditional changes in K_eff and the single-side affine tension gain?",
        "claim_boundary": {
            "complete_candidate_nonlinear_ODE_used": True,
            "reduced_prediction_used_to_generate_trajectory": False,
            "conditional_same_r_static_readout_only": True,
            "natural_dynamic_probe_completed": False,
            "ECM_or_active_myocardium_present": False,
            "DCM_necessity_or_Nature_Physics_mechanism_established": False,
        },
        "version": {
            "git_HEAD_and_prediction_commit": current_head,
            "prediction_brief_sha256": current_brief_hash,
            "source_sha256": source_hashes,
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "parameters": PARAMETERS.__dict__,
        "preregistered_prediction_recomputed_from_parameters": _prediction_public_record(coefficients),
        "protocol": {
            "loading_duration": coefficients["loading_duration"],
            "waiting_duration": coefficients["waiting_duration"],
            "time_units": "model_time_not_measured_seconds",
            "history_order": [item[0] for item in history_definitions],
        },
        "execution": {
            "start_utc": execution_start.isoformat(),
            "finish_utc": execution_finish.isoformat(),
            "calculation_seconds": calculation_seconds,
            "calculation_budget_seconds": CALCULATION_BUDGET_SECONDS,
            "completed_histories": len(histories),
            "conditional_end_state_solves": len(histories),
            "cpu_thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
            "peak_working_set_bytes": peak_bytes,
            "peak_working_set_gib": None if peak_bytes is None else peak_bytes / 1024**3,
            "peak_memory_measurement": peak_method,
            "memory_budget_gib": 8.0,
            "memory_budget_enforced": False,
            "GPU_used": False,
        },
        "histories": histories,
        "preregistered_checks": numerical_checks,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=False)
    with OUTPUT_PATH.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(_json_ready(payload), handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                "status": status,
                "calculation_seconds": calculation_seconds,
                "completed_histories": len(histories),
                "failures": failures,
            }
        )
    )


if __name__ == "__main__":
    main()
