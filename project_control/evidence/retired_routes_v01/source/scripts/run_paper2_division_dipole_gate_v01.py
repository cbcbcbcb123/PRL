"""Run the frozen Paper 2 division-dipole mechanical bridge gate.

The calculation is deliberately limited to the pre-registered mirror,
equal-area I3/I4 ECM dipole under the existing A1 harmonic mechanics.
It does not implement division dynamics, lineage evolution, or a DCM.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any

import numpy as np
import scipy
from scipy import integrate
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg

from run_paper2_feedback_kernel_gate_v01 import _footprint_stiffnesses


SCHEMA = "paper2_division_dipole_gate_v01"
EXPECTED_BASE_COMMIT = "962bdd54196fa94d2e0597aefbff825dc6c03fc7"
EXPECTED_PROJECT_ROOT = Path("/workspace")
EXPECTED_OUTPUT = Path("/output/summary.json")
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
EXPECTED_PYTHONPATH_PREFIX = (
    "/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:"
    "/usr/local/lib:"
)
SOURCE_PATHS = (
    "project_control/CURRENT_STATUS.md",
    "project_control/prl_independent_theory_mainline_plan_v04.md",
    "results/paper2_science_pilot/v01_20260905/science_brief.md",
    "src/paper2_hybrid/config.py",
    "src/paper2_hybrid/model.py",
    "src/paper2_hybrid/numerics.py",
    "scripts/run_paper2_feedback_kernel_gate_v01.py",
    "scripts/run_paper2_division_dipole_gate_v01.py",
)
SPATIAL_LEVELS = ("S2", "S3")
STEPS_PER_CYCLE = 128
FOOTPRINT_COUNT = 8
MOTHER_FOOTPRINTS = (3, 4)
FD_AMPLITUDES = (1.0e-4, 5.0e-5)
SOLVE_BUDGET_SECONDS = 30.0
FD_RELATIVE_TOLERANCE = 1.0e-2
FD_NEAR_ZERO_MAGNITUDE = 1.0e-10
FD_FIXED_ABSOLUTE_TOLERANCE = 1.0e-8
CROSS_GRID_RELATIVE_TOLERANCE = 5.0e-2
NOISE_MULTIPLIER = 100.0
ALGEBRAIC_TOLERANCE = 1.0e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(np.real(value)), "imag": float(np.imag(value))}


def _finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    if isinstance(value, (float, np.floating)):
        return math.isfinite(float(value))
    return True


class SolveLedger:
    def __init__(self) -> None:
        self.budget_seconds = SOLVE_BUDGET_SECONDS
        self.elapsed_seconds = 0.0
        self.factorization_count = 0
        self.rhs_count = 0
        self.records: list[dict[str, Any]] = []

    def factor(self, matrix: sparse.spmatrix, label: str):
        if self.elapsed_seconds >= self.budget_seconds:
            raise TimeoutError("30-second linear-solve budget exhausted before factorization")
        started = time.perf_counter()
        factor = sparse_linalg.splu(matrix.tocsc())
        elapsed = time.perf_counter() - started
        self.elapsed_seconds += elapsed
        self.factorization_count += 1
        self.records.append(
            {"kind": "factorization", "label": label, "seconds": elapsed}
        )
        if self.elapsed_seconds > self.budget_seconds:
            raise TimeoutError("30-second cumulative linear-solve budget exceeded")
        return factor

    def solve(self, factor: Any, rhs: np.ndarray, label: str) -> np.ndarray:
        if self.elapsed_seconds >= self.budget_seconds:
            raise TimeoutError("30-second linear-solve budget exhausted before RHS")
        started = time.perf_counter()
        solution = np.asarray(factor.solve(rhs))
        elapsed = time.perf_counter() - started
        self.elapsed_seconds += elapsed
        columns = 1 if rhs.ndim == 1 else int(rhs.shape[1])
        self.rhs_count += columns
        self.records.append(
            {
                "kind": "triangular_solve",
                "label": label,
                "rhs_columns": columns,
                "seconds": elapsed,
            }
        )
        if self.elapsed_seconds > self.budget_seconds:
            raise TimeoutError("30-second cumulative linear-solve budget exceeded")
        return solution


def _residual_record(
    matrix: sparse.spmatrix, solution: np.ndarray, rhs: np.ndarray
) -> dict[str, float]:
    residual = np.asarray(matrix @ solution - rhs)
    relative = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1.0e-30))
    matrix_norm = float(sparse_linalg.norm(matrix, ord=np.inf))
    denominator = matrix_norm * float(np.linalg.norm(solution, ord=np.inf))
    denominator += float(np.linalg.norm(rhs, ord=np.inf))
    backward = float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30))
    return {"relative": relative, "backward": backward}


def _area_decoupling_checks() -> dict[str, Any]:
    cases = (
        (0.23, 0.37, -0.18, 0.41, 0.62, 1.7, 0.9, 1.3),
        (0.50, -0.22, 0.31, -0.17, 0.79, 0.8, 1.4, 0.7),
        (0.74, 0.11, 0.46, 0.28, 0.35, 2.1, 0.6, 1.9),
    )
    records = []
    maximum_error = 0.0
    for eta, a_plus, a_minus, s_bar, q_value, chi, delta_s, time_scale in cases:
        s_plus = s_bar + (1.0 - eta) * q_value * delta_s
        s_minus = s_bar - eta * q_value * delta_s
        numerator_plus = -a_plus + chi * s_plus / time_scale
        numerator_minus = -a_minus + chi * s_minus / time_scale
        monopole = eta * a_plus + (1.0 - eta) * a_minus
        dipole = a_plus - a_minus
        direct_monopole = eta * numerator_plus + (1.0 - eta) * numerator_minus
        direct_dipole = numerator_plus - numerator_minus
        expected_monopole = -monopole + chi * s_bar / time_scale
        expected_dipole = -dipole + chi * q_value * delta_s / time_scale
        error = max(
            abs(direct_monopole - expected_monopole),
            abs(direct_dipole - expected_dipole),
        )
        maximum_error = max(maximum_error, error)
        records.append(
            {
                "eta": eta,
                "direct_monopole_numerator": direct_monopole,
                "expected_monopole_numerator": expected_monopole,
                "direct_dipole_numerator": direct_dipole,
                "expected_dipole_numerator": expected_dipole,
                "maximum_absolute_error": error,
            }
        )
    return {
        "identity": "area-weighted A is independent of q*delta_s while D receives q*delta_s",
        "cases": records,
        "maximum_absolute_error": maximum_error,
        "tolerance": ALGEBRAIC_TOLERANCE,
        "pass": maximum_error <= ALGEBRAIC_TOLERANCE,
    }


def _phi_step(u_value: float, v_value: float, r_value: float) -> float:
    if u_value >= 0.0:
        return 1.0 - math.exp(-v_value)
    if u_value + r_value * v_value <= 0.0:
        return 0.0
    lower = -u_value / r_value
    return 1.0 - math.exp(-(v_value - lower))


def _phi_checks() -> dict[str, Any]:
    step_cases = ((0.7, 0.4), (1.3, 1.1), (2.2, 0.65))
    endpoint_records = []
    interior_records = []
    short_records = []
    maximum_error = 0.0
    for v_value, r_value in step_cases:
        start_value = _phi_step(0.0, v_value, r_value)
        start_expected = 1.0 - math.exp(-v_value)
        end_value = _phi_step(-r_value * v_value, v_value, r_value)
        endpoint_error = max(abs(start_value - start_expected), abs(end_value))
        maximum_error = max(maximum_error, endpoint_error)
        endpoint_records.append(
            {
                "v": v_value,
                "r": r_value,
                "gate_on_at_pulse_start": start_value,
                "gate_on_expected": start_expected,
                "gate_turns_on_at_pulse_end": end_value,
                "maximum_absolute_error": endpoint_error,
            }
        )
        threshold = 0.4 * v_value
        u_value = -r_value * threshold
        analytic = _phi_step(u_value, v_value, r_value)
        numerical = integrate.quad(
            lambda y_value: math.exp(-(v_value - y_value))
            * (1.0 if u_value + r_value * y_value >= 0.0 else 0.0),
            0.0,
            v_value,
            points=[threshold],
            epsabs=1.0e-14,
            epsrel=1.0e-14,
        )[0]
        interior_error = abs(analytic - numerical)
        maximum_error = max(maximum_error, interior_error)
        interior_records.append(
            {
                "u": u_value,
                "v": v_value,
                "r": r_value,
                "analytic": analytic,
                "quadrature": numerical,
                "absolute_error": interior_error,
            }
        )
    for u_value, v_value in ((-1.4, 0.8), (0.25, 1.7), (1.2, 0.35)):
        q_value = 1.0 / (1.0 + math.exp(-u_value))
        exact_r_zero = integrate.quad(
            lambda y_value: math.exp(-(v_value - y_value)) * q_value,
            0.0,
            v_value,
            epsabs=1.0e-14,
            epsrel=1.0e-14,
        )[0]
        short_limit = q_value * (1.0 - math.exp(-v_value))
        short_error = abs(exact_r_zero - short_limit)
        maximum_error = max(maximum_error, short_error)
        short_records.append(
            {
                "u": u_value,
                "v": v_value,
                "r_limit": 0.0,
                "Phi_q": exact_r_zero,
                "q_u_times_one_minus_exp_minus_v": short_limit,
                "absolute_error": short_error,
            }
        )
    return {
        "definition": "Phi_q=integral_0^v exp[-(v-y)] q(u+r*y) dy",
        "step_gate_endpoint_checks": endpoint_records,
        "step_gate_interior_checks": interior_records,
        "short_pulse_limit_checks": short_records,
        "short_pulse_limit_interpretation": "r*v=Delta/tau_c tends to zero; r=0 is evaluated at fixed nonzero v",
        "maximum_absolute_error": maximum_error,
        "tolerance": ALGEBRAIC_TOLERANCE,
        "pass": maximum_error <= ALGEBRAIC_TOLERANCE,
    }


def _equal_timescale_checks() -> dict[str, Any]:
    cases = (
        (0.7, 1.3, 0.6, 0.9),
        (1.8, -0.4, 1.1, 2.3),
        (0.35, 2.2, 1.7, 0.28),
    )
    records = []
    maximum_relative_error = 0.0
    with localcontext() as context:
        context.prec = 80
        relative_separation = Decimal("1e-24")
        for rho_value, dipole_end, time_value, tau_value in cases:
            rho_decimal = Decimal(str(rho_value))
            dipole_decimal = Decimal(str(dipole_end))
            time_decimal = Decimal(str(time_value))
            tau_a = Decimal(str(tau_value))
            tau_m = tau_a * (Decimal(1) + relative_separation)
            general = (
                rho_decimal
                * dipole_decimal
                * tau_a
                / (tau_m - tau_a)
                * ((-time_decimal / tau_m).exp() - (-time_decimal / tau_a).exp())
            )
            limit = (
                rho_decimal
                * dipole_decimal
                * (time_decimal / tau_a)
                * (-time_decimal / tau_a).exp()
            )
            relative_error = abs(general - limit) / max(abs(limit), Decimal("1e-70"))
            relative_error_float = float(relative_error)
            maximum_relative_error = max(maximum_relative_error, relative_error_float)
            records.append(
                {
                    "rho": rho_value,
                    "D_e": dipole_end,
                    "time": time_value,
                    "tau": tau_value,
                    "relative_tau_separation": float(relative_separation),
                    "general_kernel": float(general),
                    "equal_timescale_limit": float(limit),
                    "relative_error": relative_error_float,
                }
            )
    return {
        "general": "rho*D_e*tau_a/(tau_m-tau_a)*(exp(-t/tau_m)-exp(-t/tau_a))",
        "limit": "rho*D_e*(t/tau)*exp(-t/tau)",
        "cases": records,
        "maximum_relative_error": maximum_relative_error,
        "tolerance": ALGEBRAIC_TOLERANCE,
        "pass": maximum_relative_error <= ALGEBRAIC_TOLERANCE,
    }


def _algebraic_identity_gate() -> dict[str, Any]:
    area = _area_decoupling_checks()
    phi = _phi_checks()
    timescale = _equal_timescale_checks()
    return {
        "status": "PASS" if area["pass"] and phi["pass"] and timescale["pass"] else "FAIL",
        "area_weighted_monopole_dipole_decoupling": area,
        "Phi_q": phi,
        "equal_timescale_ECM_kernel": timescale,
        "geometry_scope": {
            "covered": "mirror equal-area daughters I3 and I4",
            "not_covered": "unequal-area or non-mirror daughters",
            "required_outside_scope": "retain the second-order curvature term O(d_eff^2 * grad^2(s))",
        },
    }


def _interface_dipole_operator(system: Any) -> tuple[sparse.csr_matrix, dict[str, Any]]:
    nx = int(system.config.spatial(system.spatial_label).nx)
    if nx % FOOTPRINT_COUNT:
        raise RuntimeError("mesh does not align with the eight physical footprints")
    endocardium_rows, ecm_top_rows = system.endocardium_ecm_rows
    relative = (
        system.endocardium_transform[endocardium_rows]
        - system.ecm_transform[ecm_top_rows]
    ).tocsr()
    traction_operator = (
        system.config.endocardium_ecm_interface_stiffness * relative
    ).tocsr()
    dx = system.config.length / nx
    footprint_length = system.config.length / FOOTPRINT_COUNT
    stride = nx // FOOTPRINT_COUNT
    ell_traction = np.zeros(2 * (nx + 1), dtype=np.float64)
    footprint_records = []
    for footprint, sign in ((3, 1.0), (4, -1.0)):
        nodes = np.arange(footprint * stride, (footprint + 1) * stride + 1)
        weights = np.full(len(nodes), dx, dtype=np.float64)
        weights[[0, -1]] *= 0.5
        ell_traction[2 * nodes] += sign * weights / footprint_length
        footprint_records.append(
            {
                "footprint": footprint,
                "interval": [
                    -0.5 * system.config.length + footprint * footprint_length,
                    -0.5 * system.config.length + (footprint + 1) * footprint_length,
                ],
                "sign": sign,
                "quadrature_weight_sum": float(np.sum(weights)),
                "normalization": footprint_length,
            }
        )
    dipole_row = sparse.csr_matrix(ell_traction.reshape(1, -1)) @ traction_operator
    return dipole_row.tocsr(), {
        "traction_sign": "t_endo_minus_ecm = k_endo_ecm*(u_endo-u_ecm)",
        "component": "axial tangential",
        "dipole_sign": "area-normalized mean over I3 minus area-normalized mean over I4",
        "interface_measure_in_2D": "line length with local trapezoidal endpoint halves",
        "footprints": footprint_records,
        "ell_traction_nonzero_entries": [
            {"row": int(index), "weight": float(ell_traction[index])}
            for index in np.flatnonzero(ell_traction)
        ],
        "operator_independent_of_m": True,
    }


def _fd_gate(analytic: float, finite_difference: float) -> dict[str, Any]:
    absolute_error = abs(finite_difference - analytic)
    if abs(analytic) <= FD_NEAR_ZERO_MAGNITUDE:
        return {
            "classification": "near_zero",
            "relative_error": None,
            "absolute_error": absolute_error,
            "absolute_tolerance": FD_FIXED_ABSOLUTE_TOLERANCE,
            "pass": absolute_error <= FD_FIXED_ABSOLUTE_TOLERANCE,
        }
    relative_error = absolute_error / abs(analytic)
    return {
        "classification": "resolved",
        "relative_error": relative_error,
        "absolute_error": absolute_error,
        "absolute_tolerance": None,
        "pass": relative_error <= FD_RELATIVE_TOLERANCE,
    }


def _level_gate(label: str, config: Any, ledger: SolveLedger) -> dict[str, Any]:
    from paper2_hybrid.model import _case_components, build_system

    started = time.perf_counter()
    system = build_system(spatial_label=label, active_profile="uniform", config=config)
    active_dc, active_harmonic, load_dc, load_harmonic, profile = _case_components(
        "A1", system
    )
    if profile != "uniform" or np.any(load_dc) or np.any(load_harmonic):
        raise RuntimeError("A1 source contract drift")
    if abs(active_harmonic) <= 0.0:
        raise RuntimeError("active eigenstrain harmonic has no phase")
    dt = config.period / STEPS_PER_CYCLE
    omega = 2.0 * math.pi / config.period
    zeta = np.exp(1j * omega * dt)
    delta_t = (zeta - 1.0) / dt
    mu = 0.5 * (zeta + 1.0)
    harmonic_matrix = (delta_t * system.matrix_g + mu * system.matrix_a).tocsr()
    physical_source = load_harmonic - system.active_vector_h * active_harmonic
    harmonic_rhs = mu * physical_source
    factor = ledger.factor(harmonic_matrix, f"{label}:baseline")
    harmonic_state = ledger.solve(factor, harmonic_rhs, f"{label}:baseline")
    baseline_residual = _residual_record(
        harmonic_matrix, harmonic_state, harmonic_rhs
    )

    stiffnesses, footprint_partition = _footprint_stiffnesses(system)
    dipole_stiffness = (stiffnesses[3] - stiffnesses[4]).tocsr()
    sensitivity_rhs = -mu * (dipole_stiffness @ harmonic_state)
    sensitivity_state = ledger.solve(
        factor, sensitivity_rhs, f"{label}:analytic_dq_dm"
    )
    sensitivity_residual = _residual_record(
        harmonic_matrix, sensitivity_state, sensitivity_rhs
    )
    dipole_row, traction_definition = _interface_dipole_operator(system)
    baseline_traction_dipole = complex((dipole_row @ harmonic_state)[0])
    complex_derivative = complex((dipole_row @ sensitivity_state)[0])
    active_phase = complex(active_harmonic / abs(active_harmonic))
    scalar_derivative = float(np.real(complex_derivative * np.conjugate(active_phase)))

    fd_records = []
    residual_records = [baseline_residual, sensitivity_residual]
    for amplitude in FD_AMPLITUDES:
        states: dict[int, np.ndarray] = {}
        state_residuals: dict[str, Any] = {}
        dipole_outputs: dict[int, complex] = {}
        for sign in (-1, 1):
            perturbation = sign * amplitude
            perturbed_matrix = (
                harmonic_matrix + perturbation * mu * dipole_stiffness
            ).tocsr()
            perturbed_factor = ledger.factor(
                perturbed_matrix, f"{label}:m={perturbation:+.1e}"
            )
            state = ledger.solve(
                perturbed_factor,
                harmonic_rhs,
                f"{label}:m={perturbation:+.1e}",
            )
            states[sign] = state
            state_residual = _residual_record(
                perturbed_matrix, state, harmonic_rhs
            )
            state_residuals[str(sign)] = state_residual
            residual_records.append(state_residual)
            dipole_outputs[sign] = complex((dipole_row @ state)[0])
        complex_fd = (dipole_outputs[1] - dipole_outputs[-1]) / (2.0 * amplitude)
        scalar_fd = float(np.real(complex_fd * np.conjugate(active_phase)))
        gate = _fd_gate(scalar_derivative, scalar_fd)
        complex_absolute_error = abs(complex_fd - complex_derivative)
        complex_relative_error = complex_absolute_error / max(
            abs(complex_derivative), 1.0e-30
        )
        gate.update(
            {
                "amplitude": amplitude,
                "dipole_output_minus": _complex_record(dipole_outputs[-1]),
                "dipole_output_plus": _complex_record(dipole_outputs[1]),
                "complex_finite_difference": _complex_record(complex_fd),
                "scalar_finite_difference_G_D": scalar_fd,
                "complex_absolute_error": complex_absolute_error,
                "complex_relative_error": complex_relative_error,
                "linear_residuals": state_residuals,
            }
        )
        fd_records.append(gate)

    residual_pass = all(
        item["relative"] <= config.direct_relative_residual_tolerance
        and item["backward"] <= config.direct_backward_error_tolerance
        for item in residual_records
    )
    fd_pass = all(item["pass"] for item in fd_records)
    maximum_fd_absolute_error = max(item["absolute_error"] for item in fd_records)
    maximum_relative_residual = max(item["relative"] for item in residual_records)
    response_scale = max(
        abs(scalar_derivative),
        *(abs(item["scalar_finite_difference_G_D"]) for item in fd_records),
        1.0e-30,
    )
    residual_equivalent_noise = response_scale * maximum_relative_residual
    raw_noise = max(maximum_fd_absolute_error, residual_equivalent_noise, 1.0e-30)
    resolution_floor = NOISE_MULTIPLIER * raw_noise
    above_noise = abs(scalar_derivative) > resolution_floor
    all_values_finite = _finite(
        {
            "baseline": baseline_residual,
            "sensitivity": sensitivity_residual,
            "complex_derivative": _complex_record(complex_derivative),
            "scalar_derivative": scalar_derivative,
            "fd": fd_records,
            "noise": resolution_floor,
        }
    )
    return {
        "spatial_label": label,
        "mesh": {
            "nx": int(config.spatial(label).nx),
            "ny_per_layer": int(config.spatial(label).ny_per_layer),
            "state_size": int(system.state_size),
            "ecm_cell_count": int(len(system.ecm_mesh.cells)),
        },
        "harmonic_system": {
            "dt": dt,
            "zeta": _complex_record(complex(zeta)),
            "delta_t": _complex_record(complex(delta_t)),
            "mu": _complex_record(complex(mu)),
            "physical_source_fixed_under_m": True,
            "baseline_residual": baseline_residual,
        },
        "ECM_dipole": {
            "p_M": {"I3": 1.0, "I4": -1.0, "all_other_footprints": 0.0},
            "K_definition": "K_3-K_4; equilibrium Young-modulus branch only",
            "K_frobenius_norm": float(sparse_linalg.norm(dipole_stiffness)),
            "footprint_partition": footprint_partition,
        },
        "traction_readout": traction_definition,
        "active_eigenstrain_reference": {
            "lambda_hat": _complex_record(complex(active_harmonic)),
            "unit_phase": _complex_record(active_phase),
            "projection": "G_D=Re[(ell_T^T*d_t_hat/dm)*conj(lambda_hat/abs(lambda_hat))]",
        },
        "baseline_complex_traction_dipole": _complex_record(
            baseline_traction_dipole
        ),
        "analytic_derivative": {
            "delta_q_formula": "-H_T^{-1}*mu*(K_3-K_4)*q_hat",
            "complex_dT_hat_dm": _complex_record(complex_derivative),
            "in_phase_G_D": scalar_derivative,
            "linear_residual": sensitivity_residual,
        },
        "finite_difference": {
            "records": fd_records,
            "relative_tolerance": FD_RELATIVE_TOLERANCE,
            "near_zero_magnitude": FD_NEAR_ZERO_MAGNITUDE,
            "fixed_absolute_tolerance": FD_FIXED_ABSOLUTE_TOLERANCE,
            "pass": fd_pass,
        },
        "linear_residual_gate": {
            "relative_tolerance": config.direct_relative_residual_tolerance,
            "backward_tolerance": config.direct_backward_error_tolerance,
            "maximum_relative_residual": maximum_relative_residual,
            "maximum_backward_error": max(item["backward"] for item in residual_records),
            "pass": residual_pass,
        },
        "noise_resolution": {
            "formula": "100*max(max_FD_scalar_absolute_error, response_scale*max_linear_relative_residual, 1e-30)",
            "response_scale": response_scale,
            "maximum_FD_scalar_absolute_error": maximum_fd_absolute_error,
            "linear_residual_equivalent_noise": residual_equivalent_noise,
            "raw_noise": raw_noise,
            "multiplier": NOISE_MULTIPLIER,
            "resolution_floor": resolution_floor,
            "absolute_G_D": abs(scalar_derivative),
            "above_100x_noise_floor": above_noise,
        },
        "all_values_finite": all_values_finite,
        "FEM_derivative_pass": bool(
            footprint_partition["partition_pass"]
            and residual_pass
            and fd_pass
            and all_values_finite
        ),
        "elapsed_wall_seconds": time.perf_counter() - started,
    }


def _cross_grid(levels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = [
        float(levels[label]["analytic_derivative"]["in_phase_G_D"])
        for label in SPATIAL_LEVELS
    ]
    relative_change = abs(values[1] - values[0]) / max(
        abs(values[0]), abs(values[1]), 1.0e-30
    )
    above_noise = [
        bool(levels[label]["noise_resolution"]["above_100x_noise_floor"])
        for label in SPATIAL_LEVELS
    ]
    resolved = bool(
        all(levels[label]["FEM_derivative_pass"] for label in SPATIAL_LEVELS)
        and all(above_noise)
        and relative_change <= CROSS_GRID_RELATIVE_TOLERANCE
    )
    return {
        "status": (
            "MECHANICAL_DIPOLE_READOUT_RESOLVED" if resolved else "NOT_RESOLVED"
        ),
        "G_D": dict(zip(SPATIAL_LEVELS, values, strict=True)),
        "above_100x_noise_floor": dict(
            zip(SPATIAL_LEVELS, above_noise, strict=True)
        ),
        "relative_change_formula": "abs(S3-S2)/max(abs(S2),abs(S3),1e-30)",
        "relative_change": relative_change,
        "relative_tolerance": CROSS_GRID_RELATIVE_TOLERANCE,
        "pass": resolved,
        "S4_not_run": True,
    }


def _parameter_identifiability(cross_grid: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "STRUCTURAL_MEASUREMENT_PATHS_ONLY_NOT_EXPERIMENTALLY_CALIBRATED",
        "q_t_c_tau_c": {
            "independent_measurement": "division imaging",
            "experimental_status": "not_provided_in_this_gate",
        },
        "tau_a_chi": {
            "independent_measurement": "mother/daughter uniform traction pulses",
            "experimental_status": "not_provided_in_this_gate",
        },
        "tau_m_rho": {
            "independent_measurement": "ECM time series under measured D drive",
            "experimental_status": "not_provided_in_this_gate",
        },
        "G_D": {
            "measurement": "this frozen FEM mechanical gate",
            "gate_status": cross_grid["status"],
        },
        "no_fabricated_data": True,
        "structural_list_is_not_parameter_calibration": True,
    }


def run(output: Path, base_commit: str) -> int:
    if base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError(
            f"base commit drift: {base_commit} != {EXPECTED_BASE_COMMIT}"
        )
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root.resolve() != EXPECTED_PROJECT_ROOT:
        raise RuntimeError(f"project mount drift: {repo_root.resolve()}")
    if output.resolve() != EXPECTED_OUTPUT:
        raise RuntimeError(f"output boundary mismatch: {output.resolve()}")
    if output.exists() or (output.parent.exists() and any(output.parent.iterdir())):
        raise RuntimeError("create-only output target is not empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    ledger = SolveLedger()
    started = time.perf_counter()
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": {
            "base_commit": base_commit,
            "source_hashes": {
                relative: _sha256(repo_root / relative) for relative in SOURCE_PATHS
            },
        },
        "frozen_scope": {
            "case": "A1 uniform prescribed active strain",
            "activation_peak": 0.10,
            "H": 0.3,
            "De": 0.2,
            "T": STEPS_PER_CYCLE,
            "spatial_levels": list(SPATIAL_LEVELS),
            "mother_region": "I3 union I4",
            "daughter_left": "I3",
            "daughter_right": "I4",
            "p_M": [0.0, 0.0, 0.0, 1.0, -1.0, 0.0, 0.0, 0.0],
            "FD_amplitudes": list(FD_AMPLITUDES),
            "holdouts_read": False,
            "S4_run": False,
            "division_DCM_implemented": False,
            "T1_or_Floquet_run": False,
            "fluid_nonlinear_3D_reaction_trajectory": False,
        },
        "frozen_gates": {
            "algebraic_absolute_tolerance": ALGEBRAIC_TOLERANCE,
            "FD_relative_tolerance": FD_RELATIVE_TOLERANCE,
            "FD_near_zero_magnitude": FD_NEAR_ZERO_MAGNITUDE,
            "FD_fixed_absolute_tolerance": FD_FIXED_ABSOLUTE_TOLERANCE,
            "noise_multiplier": NOISE_MULTIPLIER,
            "cross_grid_relative_tolerance": CROSS_GRID_RELATIVE_TOLERANCE,
            "linear_solve_budget_seconds": SOLVE_BUDGET_SECONDS,
        },
    }
    return_code = 1
    try:
        for variable in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            if os.environ.get(variable) != "1":
                raise RuntimeError(
                    f"single-CPU environment drift: {variable}={os.environ.get(variable)!r}"
                )
        if os.environ.get("PAPER2_IMAGE_ID") != EXPECTED_IMAGE_ID:
            raise RuntimeError("container image identity drift")
        if not os.environ.get("PYTHONPATH", "").startswith(
            EXPECTED_PYTHONPATH_PREFIX
        ):
            raise RuntimeError("PYTHONPATH drift")

        import dolfinx
        from paper2_hybrid.config import ACTIVE_CONFIG

        dolfinx_path = Path(dolfinx.__file__).resolve()
        expected_dolfinx_root = Path(
            "/usr/local/dolfinx-real/lib/python3.12/dist-packages/dolfinx"
        )
        if not str(dolfinx_path).startswith(str(expected_dolfinx_root) + os.sep):
            raise RuntimeError(f"dolfinx import path drift: {dolfinx_path}")
        config = replace(
            ACTIVE_CONFIG,
            ecm_thickness=0.3 * ACTIVE_CONFIG.length,
            ecm_relaxation_time=0.2 * ACTIVE_CONFIG.period,
            activation_peak=0.10,
        ).checked()
        summary["parameters"] = {
            **asdict(config),
            "config_digest": config.digest(),
            "footprint_intervals": [
                [
                    -0.5 * config.length + index * config.length / FOOTPRINT_COUNT,
                    -0.5 * config.length
                    + (index + 1) * config.length / FOOTPRINT_COUNT,
                ]
                for index in range(FOOTPRINT_COUNT)
            ],
        }
        summary["execution"] = {
            "status": "RUNNING",
            "runtime": {
                "container_name": os.environ.get("PAPER2_CONTAINER_NAME"),
                "container_image": "dolfinx/dolfinx:v0.11.0",
                "container_image_id": os.environ.get("PAPER2_IMAGE_ID"),
                "network": "none",
                "cpu_limit": 1,
                "memory_limit_gib": 8,
                "gpu_count": 0,
                "root_filesystem_read_only": True,
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "dolfinx": dolfinx.__version__,
                "dolfinx_path": dolfinx_path.as_posix(),
            },
        }
        algebraic = _algebraic_identity_gate()
        levels = {
            label: _level_gate(label, config, ledger) for label in SPATIAL_LEVELS
        }
        cross_grid = _cross_grid(levels)
        FEM_pass = all(
            levels[label]["FEM_derivative_pass"] for label in SPATIAL_LEVELS
        )
        summary["algebraic_identity"] = algebraic
        summary["FEM_derivative"] = {
            "status": "PASS" if FEM_pass else "FAIL",
            "levels": levels,
        }
        summary["cross_grid_resolution"] = cross_grid
        summary["parameter_identifiability"] = _parameter_identifiability(
            cross_grid
        )
        summary["scientific_interpretation"] = {
            "status": cross_grid["status"],
            "bounded_claim": (
                "the pre-registered mirror equal-area mechanical traction-dipole readout is resolved"
                if cross_grid["pass"]
                else "the pre-registered mechanical traction-dipole readout is not resolved"
            ),
            "not_a_division_mechanism_proof": True,
            "not_DCM_necessity": True,
            "not_experimental_truth_or_calibration": True,
            "not_Nature_Physics_maturity": True,
            "unequal_or_nonmirror_division_requires_second_order_curvature": True,
            "independent_supervisor_acceptance_required": True,
        }
        summary["execution"]["status"] = "PASS"
        summary["execution"]["completed_at_utc"] = datetime.now(
            timezone.utc
        ).isoformat()
        summary["status"] = "COMPLETED"
        return_code = 0
    except BaseException as error:
        summary["status"] = "FAILED_CLOSED"
        summary["execution"] = {
            **summary.get("execution", {}),
            "status": "FAIL",
            "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        summary.setdefault("algebraic_identity", {"status": "NOT_EVALUABLE"})
        summary.setdefault("FEM_derivative", {"status": "NOT_EVALUABLE"})
        summary.setdefault(
            "cross_grid_resolution", {"status": "NOT_EVALUABLE", "pass": False}
        )
        summary.setdefault(
            "parameter_identifiability",
            {"status": "NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE"},
        )
        summary.setdefault(
            "scientific_interpretation",
            {
                "status": "NOT_EVALUABLE",
                "not_a_scientific_negative_result": True,
            },
        )
    finally:
        summary["execution"]["solve_ledger"] = {
            "budget_seconds": ledger.budget_seconds,
            "elapsed_seconds": ledger.elapsed_seconds,
            "factorization_count": ledger.factorization_count,
            "rhs_count": ledger.rhs_count,
            "records": ledger.records,
        }
        summary["execution"]["total_wall_seconds"] = time.perf_counter() - started
        summary["execution"]["peak_rss_gib"] = (
            float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / (1024.0**2)
        )
        summary["execution"]["memory_budget_hard_enforced_by_container"] = True
        summary["all_reported_values_finite"] = _finite(summary)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "algebraic_identity": summary["algebraic_identity"]["status"],
                "FEM_derivative": summary["FEM_derivative"]["status"],
                "cross_grid_resolution": summary["cross_grid_resolution"]["status"],
                "solve_seconds": summary["execution"]["solve_ledger"][
                    "elapsed_seconds"
                ],
                "wall_seconds": summary["execution"]["total_wall_seconds"],
            },
            indent=2,
        )
    )
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    arguments = parser.parse_args()
    return run(arguments.output, arguments.base_commit)


if __name__ == "__main__":
    sys.exit(main())
