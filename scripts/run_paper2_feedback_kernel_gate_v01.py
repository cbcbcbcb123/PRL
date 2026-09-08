"""Run the preregistered Paper 2 mechanical-feedback-kernel gate.

This runner is intentionally narrow: A1, H=0.3, De=0.2, T128, S2/S3,
eight fixed physical footprints, and equilibrium-ECM-modulus sensitivities only.
It reuses the frozen paper2_hybrid assembly and does not change production APIs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
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
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg


SCHEMA = "paper2_feedback_kernel_gate_v01"
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
    "project_control/prl_independent_theory_mainline_plan_v04.md",
    "results/paper2_science_pilot/v01_20260905/science_brief.md",
    "project_control/CURRENT_STATUS.md",
    "src/paper2_hybrid/config.py",
    "src/paper2_hybrid/model.py",
    "src/paper2_hybrid/numerics.py",
    "scripts/run_paper2_feedback_kernel_gate_v01.py",
)
SPATIAL_LEVELS = ("S2", "S3")
FOOTPRINT_COUNT = 8
FD_COLUMNS = (0, 3)
FD_AMPLITUDES = (1.0e-4, 5.0e-5)
STEPS_PER_CYCLE = 128
SOLVE_BUDGET_SECONDS = 60.0
UNIFORMITY_TOLERANCE = 1.0e-8
CIRCULANT_TOLERANCE = 1.0e-8
FD_RELATIVE_TOLERANCE = 1.0e-2
CROSS_GRID_RELATIVE_TOLERANCE = 5.0e-2
AMPLITUDE_FLOOR = 1.0e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    if isinstance(value, (float, np.floating)):
        return math.isfinite(float(value))
    return True


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(np.real(value)), "imag": float(np.imag(value))}


class SolveLedger:
    def __init__(self, budget_seconds: float) -> None:
        self.budget_seconds = float(budget_seconds)
        self.elapsed_seconds = 0.0
        self.factorization_count = 0
        self.rhs_count = 0
        self.records: list[dict[str, Any]] = []

    def factor(self, matrix: sparse.spmatrix, label: str):
        if self.elapsed_seconds >= self.budget_seconds:
            raise TimeoutError("solve budget exhausted before factorization")
        started = time.perf_counter()
        factor = sparse_linalg.splu(matrix.tocsc())
        elapsed = time.perf_counter() - started
        self.elapsed_seconds += elapsed
        self.factorization_count += 1
        self.records.append(
            {"kind": "factorization", "label": label, "seconds": elapsed}
        )
        if self.elapsed_seconds > self.budget_seconds:
            raise TimeoutError("60-second cumulative solve budget exceeded")
        return factor

    def solve(self, factor: Any, rhs: np.ndarray, label: str) -> np.ndarray:
        if self.elapsed_seconds >= self.budget_seconds:
            raise TimeoutError("solve budget exhausted before triangular solve")
        started = time.perf_counter()
        answer = np.asarray(factor.solve(rhs))
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
            raise TimeoutError("60-second cumulative solve budget exceeded")
        return answer


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


def _active_work(
    system: Any,
    dc_state: np.ndarray,
    harmonic_state: np.ndarray,
    active_dc: float,
    active_harmonic: complex,
) -> float:
    omega = 2.0 * math.pi / system.config.period
    times = np.linspace(0.0, system.config.period, STEPS_PER_CYCLE + 1)
    phase = np.exp(1j * omega * times)
    states = dc_state[:, None] + np.real(harmonic_state[:, None] * phase[None, :])
    activation = active_dc + np.real(active_harmonic * phase)
    work = 0.0
    for step in range(STEPS_PER_CYCLE):
        midpoint = 0.5 * (states[:, step] + states[:, step + 1])
        activation_midpoint = 0.5 * (activation[step] + activation[step + 1])
        active_conjugate = float(system.active_vector_h @ midpoint)
        active_conjugate += system.active_scalar_c * float(activation_midpoint)
        work += active_conjugate * float(activation[step + 1] - activation[step])
    return float(work)


def _footprint_stiffnesses(system: Any) -> tuple[list[sparse.csr_matrix], dict[str, Any]]:
    length = float(system.config.length)
    footprint_length = length / FOOTPRINT_COUNT
    x_centroids = np.asarray(system.ecm_mesh.cell_centroids[:, 0], dtype=np.float64)
    footprint_index = np.floor((x_centroids + 0.5 * length) / footprint_length).astype(int)
    footprint_index = np.clip(footprint_index, 0, FOOTPRINT_COUNT - 1)
    strain_global = (system.ecm_strain_operator_full @ system.ecm_transform).tocsr()
    stiffnesses: list[sparse.csr_matrix] = []
    counts: list[int] = []
    areas: list[float] = []
    for footprint in range(FOOTPRINT_COUNT):
        mask = footprint_index == footprint
        counts.append(int(np.count_nonzero(mask)))
        areas.append(float(np.sum(system.ecm_mesh.cell_areas[mask])))
        blocks = [
            area * system.ecm_constitutive_equilibrium if selected else np.zeros((3, 3))
            for area, selected in zip(system.ecm_mesh.cell_areas, mask, strict=True)
        ]
        weighted = sparse.block_diag(blocks, format="csr")
        stiffnesses.append((strain_global.T @ weighted @ strain_global).tocsr())
    summed = sum(stiffnesses[1:], stiffnesses[0].copy()).tocsr()
    reference = system.component_matrices["ecm_equilibrium"]
    partition_error = float(
        sparse_linalg.norm(summed - reference)
        / max(float(sparse_linalg.norm(reference)), 1.0e-30)
    )
    return stiffnesses, {
        "definition": "periodic physical top-hats over I_j of length L/8, uniform through ECM thickness",
        "cell_counts": counts,
        "physical_areas": areas,
        "partition_relative_error": partition_error,
        "partition_pass": partition_error <= 1.0e-12,
    }


def _strain_readout(system: Any) -> tuple[sparse.csr_matrix, dict[str, Any]]:
    nx = int(system.config.spatial(system.spatial_label).nx)
    if nx % FOOTPRINT_COUNT:
        raise RuntimeError("mesh nodes do not align with the eight fixed physical footprints")
    stride = nx // FOOTPRINT_COUNT
    footprint_length = system.config.length / FOOTPRINT_COUNT
    rows = []
    for footprint in range(FOOTPRINT_COUNT):
        left = footprint * stride
        right = (footprint + 1) * stride
        row = (
            system.endocardium_transform.getrow(2 * right)
            - system.endocardium_transform.getrow(2 * left)
        ) / footprint_length
        rows.append(row)
    operator = sparse.vstack(rows, format="csr")
    return operator, {
        "definition": "endpoint axial tangential displacement difference after full endocardium_transform divided by L/8",
        "endpoint_node_stride": stride,
        "includes_common_macro_affine_mode": True,
    }


def _nearest_circulant(matrix: np.ndarray) -> np.ndarray:
    size = matrix.shape[0]
    first_column = np.asarray(
        [np.mean([matrix[row, (row - offset) % size] for row in range(size)]) for offset in range(size)]
    )
    return np.asarray(
        [[first_column[(row - column) % size] for column in range(size)] for row in range(size)]
    )


def _candidate_modes(matrix: np.ndarray) -> list[dict[str, Any]]:
    values, vectors = np.linalg.eig(matrix)
    uniform = np.ones(matrix.shape[0], dtype=np.complex128) / math.sqrt(matrix.shape[0])
    order = np.argsort(np.real(values))[::-1]
    result = []
    for rank, index in enumerate(order):
        vector = vectors[:, index]
        vector /= max(np.linalg.norm(vector), 1.0e-30)
        result.append(
            {
                "rank_by_real_part": rank,
                "eigenvalue": _complex_record(complex(values[index])),
                "uniform_overlap": float(abs(np.vdot(uniform, vector))),
                "vector": [_complex_record(complex(item)) for item in vector],
            }
        )
    return result


def _fd_gate(analytic: np.ndarray, finite_difference: np.ndarray, scale: float) -> dict[str, Any]:
    analytic_norm = float(np.linalg.norm(analytic))
    absolute_error = float(np.linalg.norm(analytic - finite_difference))
    floor = 1.0e-10 * max(scale, 1.0e-30)
    absolute_tolerance = 1.0e-8 * max(scale, 1.0e-30)
    if analytic_norm <= floor:
        return {
            "classification": "near_zero",
            "analytic_norm": analytic_norm,
            "floor": floor,
            "absolute_error": absolute_error,
            "absolute_tolerance": absolute_tolerance,
            "relative_error": None,
            "pass": absolute_error <= absolute_tolerance,
        }
    relative_error = absolute_error / analytic_norm
    return {
        "classification": "resolved",
        "analytic_norm": analytic_norm,
        "floor": floor,
        "absolute_error": absolute_error,
        "absolute_tolerance": None,
        "relative_error": relative_error,
        "pass": relative_error <= FD_RELATIVE_TOLERANCE,
    }


def _perturbed_state(
    system: Any,
    stiffness: sparse.csr_matrix,
    perturbation: float,
    mu: complex,
    harmonic_matrix: sparse.csr_matrix,
    rhs_dc: np.ndarray,
    rhs_harmonic: np.ndarray,
    ledger: SolveLedger,
    label: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    matrix_a = (system.matrix_a + perturbation * stiffness).tocsr()
    matrix_h = (harmonic_matrix + perturbation * mu * stiffness).tocsr()
    factor_a = ledger.factor(matrix_a, f"{label}:dc")
    dc_state = ledger.solve(factor_a, rhs_dc, f"{label}:dc")
    factor_h = ledger.factor(matrix_h, f"{label}:harmonic")
    harmonic_state = ledger.solve(factor_h, rhs_harmonic, f"{label}:harmonic")
    return dc_state, harmonic_state, {
        "dc": _residual_record(matrix_a, dc_state, rhs_dc),
        "harmonic": _residual_record(matrix_h, harmonic_state, rhs_harmonic),
    }


def _level_result(label: str, config: Any, ledger: SolveLedger) -> dict[str, Any]:
    from paper2_hybrid.model import _case_components, build_system

    started = time.perf_counter()
    system = build_system(spatial_label=label, active_profile="uniform", config=config)
    active_dc, active_harmonic, load_dc, load_harmonic, profile = _case_components("A1", system)
    if profile != "uniform" or np.any(load_dc) or np.any(load_harmonic):
        raise RuntimeError("A1 source contract drift")
    dt = config.period / STEPS_PER_CYCLE
    omega = 2.0 * math.pi / config.period
    zeta = np.exp(1j * omega * dt)
    delta_t = (zeta - 1.0) / dt
    mu = 0.5 * (zeta + 1.0)
    harmonic_matrix = (delta_t * system.matrix_g + mu * system.matrix_a).tocsr()
    rhs_dc = load_dc - system.active_vector_h * active_dc
    physical_harmonic_source = load_harmonic - system.active_vector_h * active_harmonic
    rhs_harmonic = mu * physical_harmonic_source

    factor_a = ledger.factor(system.matrix_a, f"{label}:baseline:dc")
    dc_state = ledger.solve(factor_a, rhs_dc, f"{label}:baseline:dc")
    factor_h = ledger.factor(harmonic_matrix, f"{label}:baseline:harmonic")
    harmonic_state = ledger.solve(factor_h, rhs_harmonic, f"{label}:baseline:harmonic")
    baseline_residuals = {
        "dc": _residual_record(system.matrix_a, dc_state, rhs_dc),
        "harmonic": _residual_record(harmonic_matrix, harmonic_state, rhs_harmonic),
    }

    readout, readout_record = _strain_readout(system)
    epsilon_hat = np.asarray(readout @ harmonic_state).ravel()
    amplitudes = 2.0 * np.abs(epsilon_hat)
    if np.any(amplitudes <= AMPLITUDE_FLOOR):
        raise RuntimeError(
            "at least one footprint strain amplitude is at or below the "
            "1e-12 derivative-evaluation floor"
        )
    maximum_amplitude = float(np.max(np.abs(amplitudes)))
    if maximum_amplitude <= AMPLITUDE_FLOOR:
        uniformity = {
            "status": "not_evaluable",
            "denominator": maximum_amplitude,
            "value": None,
            "pass": False,
        }
    else:
        value = float((np.max(amplitudes) - np.min(amplitudes)) / maximum_amplitude)
        uniformity = {
            "status": "evaluated",
            "denominator": maximum_amplitude,
            "value": value,
            "pass": value <= UNIFORMITY_TOLERANCE,
        }

    stiffnesses, footprint_record = _footprint_stiffnesses(system)
    sensitivity_rhs = np.column_stack([-mu * (item @ harmonic_state) for item in stiffnesses])
    sensitivity_states = ledger.solve(factor_h, sensitivity_rhs, f"{label}:analytic:8_columns")
    sensitivity_residuals = []
    for column, stiffness in enumerate(stiffnesses):
        residual = harmonic_matrix @ sensitivity_states[:, column] + mu * (stiffness @ harmonic_state)
        denominator = max(float(np.linalg.norm(mu * (stiffness @ harmonic_state))), 1.0e-30)
        sensitivity_residuals.append(float(np.linalg.norm(residual) / denominator))
    phase_gradient = np.conjugate(epsilon_hat) / np.maximum(np.abs(epsilon_hat), 1.0e-300)
    response_derivative = readout @ sensitivity_states
    kernel = 2.0 * np.real(phase_gradient[:, None] * response_derivative)
    kernel = np.asarray(kernel, dtype=np.float64)
    kernel_norm_fro = float(np.linalg.norm(kernel, ord="fro"))
    kernel_norm_2 = float(np.linalg.norm(kernel, ord=2))

    circulant = _nearest_circulant(kernel)
    circulant_residual = float(
        np.linalg.norm(kernel - circulant, ord="fro") / max(kernel_norm_fro, 1.0e-30)
    )
    circulant_pass = circulant_residual <= CIRCULANT_TOLERANCE
    preconditions_pass = bool(uniformity["pass"] and circulant_pass)

    base_work = _active_work(system, dc_state, harmonic_state, active_dc, active_harmonic)
    fd_records: dict[str, Any] = {}
    all_fd_pass = True
    perturbed_work: dict[str, float] = {}
    for column in FD_COLUMNS:
        column_records = []
        for amplitude in FD_AMPLITUDES:
            states: dict[int, tuple[np.ndarray, np.ndarray]] = {}
            residuals: dict[str, Any] = {}
            for sign in (-1, 1):
                perturbation = sign * amplitude
                key = f"column_{column}:r={perturbation:+.1e}"
                dc_perturbed, harmonic_perturbed, residual = _perturbed_state(
                    system,
                    stiffnesses[column],
                    perturbation,
                    mu,
                    harmonic_matrix,
                    rhs_dc,
                    rhs_harmonic,
                    ledger,
                    f"{label}:{key}",
                )
                states[sign] = (dc_perturbed, harmonic_perturbed)
                residuals[str(sign)] = residual
                perturbed_work[key] = _active_work(
                    system, dc_perturbed, harmonic_perturbed, active_dc, active_harmonic
                )
            plus = 2.0 * np.abs(np.asarray(readout @ states[1][1]).ravel())
            minus = 2.0 * np.abs(np.asarray(readout @ states[-1][1]).ravel())
            finite_difference = (plus - minus) / (2.0 * amplitude)
            gate = _fd_gate(kernel[:, column], finite_difference, kernel_norm_fro)
            gate.update(
                {
                    "amplitude": amplitude,
                    "analytic": kernel[:, column].tolist(),
                    "finite_difference": finite_difference.tolist(),
                    "linear_residuals": residuals,
                }
            )
            column_records.append(gate)
            all_fd_pass = all_fd_pass and bool(gate["pass"])
        fd_records[str(column)] = column_records

    summed_stiffness = sum(stiffnesses[1:], stiffnesses[0].copy()).tocsr()
    analytic_global = np.sum(kernel, axis=1)
    global_records = []
    for amplitude in FD_AMPLITUDES:
        states = {}
        residuals = {}
        for sign in (-1, 1):
            perturbation = sign * amplitude
            key = f"global_uniform:r={perturbation:+.1e}"
            dc_perturbed, harmonic_perturbed, residual = _perturbed_state(
                system,
                summed_stiffness,
                perturbation,
                mu,
                harmonic_matrix,
                rhs_dc,
                rhs_harmonic,
                ledger,
                f"{label}:{key}",
            )
            states[sign] = (dc_perturbed, harmonic_perturbed)
            residuals[str(sign)] = residual
            perturbed_work[key] = _active_work(
                system, dc_perturbed, harmonic_perturbed, active_dc, active_harmonic
            )
        plus = 2.0 * np.abs(np.asarray(readout @ states[1][1]).ravel())
        minus = 2.0 * np.abs(np.asarray(readout @ states[-1][1]).ravel())
        finite_difference = (plus - minus) / (2.0 * amplitude)
        gate = _fd_gate(analytic_global, finite_difference, kernel_norm_fro)
        gate.update(
            {
                "amplitude": amplitude,
                "analytic_sum_of_columns": analytic_global.tolist(),
                "finite_difference": finite_difference.tolist(),
                "linear_residuals": residuals,
            }
        )
        global_records.append(gate)
        all_fd_pass = all_fd_pass and bool(gate["pass"])

    all_linear_residuals = list(baseline_residuals.values())
    for column_records in fd_records.values():
        for record in column_records:
            for pair in record["linear_residuals"].values():
                all_linear_residuals.extend(pair.values())
    for record in global_records:
        for pair in record["linear_residuals"].values():
            all_linear_residuals.extend(pair.values())
    residual_pass = bool(
        all(
            pair["relative"] <= config.direct_relative_residual_tolerance
            and pair["backward"] <= config.direct_backward_error_tolerance
            and _finite(pair)
            for pair in all_linear_residuals
        )
        and max(sensitivity_residuals) <= config.direct_relative_residual_tolerance
        and all(math.isfinite(item) for item in sensitivity_residuals)
    )

    spectral: dict[str, Any]
    if preconditions_pass:
        eigenvalues = np.fft.fft(circulant[:, 0])
        imaginary_scale = max(float(np.max(np.abs(np.real(eigenvalues)))), 1.0e-30)
        spectrum_real = bool(np.max(np.abs(np.imag(eigenvalues))) <= 1.0e-8 * imaginary_scale)
        real_values = np.real(eigenvalues)
        nonuniform_indices = list(range(1, FOOTPRINT_COUNT))
        leading_index = max(nonuniform_indices, key=lambda index: real_values[index])
        spectral = {
            "status": "fourier_labels_allowed",
            "spectrum_real_within_tolerance": spectrum_real,
            "eigenvalues_by_k": [_complex_record(complex(item)) for item in eigenvalues],
            "uniform_mode_value": float(real_values[0]),
            "leading_nonuniform_k": int(leading_index),
            "leading_nonuniform_value": float(real_values[leading_index]),
            "leading_nonuniform_is_positive": bool(real_values[leading_index] > 0.0),
            "candidate_modes_of_full_G": _candidate_modes(kernel),
        }
    else:
        spectral = {
            "status": "fourier_labels_forbidden_preconditions_failed",
            "spectrum_real_within_tolerance": None,
            "uniform_mode_value": None,
            "leading_nonuniform_k": None,
            "leading_nonuniform_value": None,
            "leading_nonuniform_is_positive": None,
            "candidate_modes_of_full_G": _candidate_modes(kernel),
        }

    result = {
        "spatial_label": label,
        "state_size": int(system.state_size),
        "mesh": {
            "nx": int(config.spatial(label).nx),
            "ny_per_layer": int(config.spatial(label).ny_per_layer),
            "ecm_cell_count": int(len(system.ecm_mesh.cells)),
            "manufactured_operator_relative_error": float(system.manufactured_error),
        },
        "discrete_harmonic_symbols": {
            "dt": dt,
            "zeta": _complex_record(complex(zeta)),
            "delta_t": _complex_record(complex(delta_t)),
            "mu": _complex_record(complex(mu)),
        },
        "readout": readout_record,
        "footprints": footprint_record,
        "baseline": {
            "epsilon_hat": [_complex_record(complex(item)) for item in epsilon_hat],
            "S": amplitudes.tolist(),
            "uniformity": uniformity,
            "active_input_work": base_work,
            "linear_residuals": baseline_residuals,
        },
        "kernel": {
            "definition": "G_ij=d[2*abs(epsilon_hat_i)]/d r_j at r=0",
            "matrix": kernel.tolist(),
            "frobenius_norm": kernel_norm_fro,
            "operator_2_norm": kernel_norm_2,
            "analytic_state_relative_residuals": sensitivity_residuals,
            "nearest_circulant_matrix": circulant.tolist(),
            "nearest_circulant_residual": circulant_residual,
            "nearest_circulant_pass": circulant_pass,
        },
        "finite_difference_checks": {
            "columns": fd_records,
            "global_uniform_modulus": global_records,
            "all_pass": all_fd_pass,
        },
        "active_input_work_under_modulus_perturbations": {
            "fixed_active_strain_source": True,
            "baseline": base_work,
            "values": perturbed_work,
            "changes_from_baseline": {
                key: value - base_work for key, value in perturbed_work.items()
            },
            "may_change_with_modulus": True,
        },
        "spectral": spectral,
        "gates": {
            "footprint_partition_pass": footprint_record["partition_pass"],
            "baseline_uniformity_pass": uniformity["pass"],
            "circulant_pass": circulant_pass,
            "fourier_preconditions_pass": preconditions_pass,
            "finite_difference_pass": all_fd_pass,
            "linear_residual_pass": residual_pass,
        },
        "elapsed_wall_seconds": time.perf_counter() - started,
    }
    result["all_values_finite"] = _finite(result)
    result["numerical_level_pass"] = bool(
        result["all_values_finite"]
        and all(result["gates"][key] for key in (
            "footprint_partition_pass",
            "baseline_uniformity_pass",
            "circulant_pass",
            "finite_difference_pass",
            "linear_residual_pass",
        ))
    )
    return result


def _relative_or_absolute_cross_gate(first: float, second: float, scale: float) -> dict[str, Any]:
    floor = 1.0e-10 * scale
    absolute_change = abs(second - first)
    if abs(first) <= floor or abs(second) <= floor:
        return {
            "classification": "near_zero",
            "relative_change": None,
            "absolute_change": absolute_change,
            "absolute_tolerance": 0.05 * scale,
            "pass": absolute_change <= 0.05 * scale,
        }
    relative_change = absolute_change / max(abs(first), abs(second))
    return {
        "classification": "resolved",
        "relative_change": relative_change,
        "absolute_change": absolute_change,
        "absolute_tolerance": None,
        "pass": relative_change <= CROSS_GRID_RELATIVE_TOLERANCE,
    }


def _cross_grid(levels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    norms = [float(levels[label]["kernel"]["operator_2_norm"]) for label in SPATIAL_LEVELS]
    scale = max(norms[0], norms[1], 1.0e-30)
    if not all(levels[label]["gates"]["fourier_preconditions_pass"] for label in SPATIAL_LEVELS):
        return {
            "status": "not_evaluable_fourier_preconditions_failed",
            "Q_scale": scale,
            "Q_floor": 1.0e-10 * scale,
            "pass": False,
            "gain_window": None,
        }
    spectral = [levels[label]["spectral"] for label in SPATIAL_LEVELS]
    if not all(item["spectrum_real_within_tolerance"] for item in spectral):
        return {
            "status": "not_evaluable_complex_spectrum",
            "Q_scale": scale,
            "Q_floor": 1.0e-10 * scale,
            "pass": False,
            "gain_window": None,
        }
    leading = [float(item["leading_nonuniform_value"]) for item in spectral]
    uniform = [float(item["uniform_mode_value"]) for item in spectral]
    leading_gate = _relative_or_absolute_cross_gate(leading[0], leading[1], scale)
    uniform_gate = _relative_or_absolute_cross_gate(uniform[0], uniform[1], scale)
    floor = 1.0e-10 * scale
    ratio_record: dict[str, Any]
    if all(value > floor for value in leading + uniform):
        ratios = [leading[index] / uniform[index] for index in range(2)]
        ratio_change = abs(ratios[1] - ratios[0]) / max(abs(ratios[0]), abs(ratios[1]))
        ratio_record = {
            "status": "evaluated",
            "values": ratios,
            "relative_change": ratio_change,
            "pass": ratio_change <= CROSS_GRID_RELATIVE_TOLERANCE,
        }
    else:
        ratio_record = {"status": "not_applicable", "values": None, "relative_change": None, "pass": None}
    grid_error = max(abs(leading[1] - leading[0]), abs(uniform[1] - uniform[0]))
    advantages = [leading[index] - uniform[index] for index in range(2)]
    robust_nonuniform_advantage = bool(
        leading_gate["pass"]
        and uniform_gate["pass"]
        and ratio_record["pass"] is not False
        and all(value > 0.0 for value in leading)
        and all(value > grid_error for value in advantages)
    )
    gain_window = None
    if robust_nonuniform_advantage:
        conservative_leading = min(leading)
        conservative_uniform = max(uniform)
        if conservative_uniform > floor:
            lower = 1.0 / conservative_leading
            upper = 1.0 / conservative_uniform
            gain_window = {
                "kind": "bounded_uniform_stable_nonuniform_unstable",
                "lower_open": lower,
                "upper_open": upper,
                "nonempty": lower < upper,
            }
        elif conservative_uniform <= 0.0:
            gain_window = {
                "kind": "uniform_never_crosses_for_positive_g",
                "nonuniform_threshold": 1.0 / conservative_leading,
            }
    passed = bool(
        leading_gate["pass"]
        and uniform_gate["pass"]
        and (ratio_record["pass"] is not False)
    )
    return {
        "status": "evaluated",
        "Q_scale": scale,
        "Q_floor": floor,
        "leading_nonuniform_values": dict(zip(SPATIAL_LEVELS, leading, strict=True)),
        "uniform_mode_values": dict(zip(SPATIAL_LEVELS, uniform, strict=True)),
        "leading_nonuniform_gate": leading_gate,
        "uniform_mode_gate": uniform_gate,
        "ratio_gate": ratio_record,
        "observed_grid_error": grid_error,
        "nonuniform_advantages": dict(zip(SPATIAL_LEVELS, advantages, strict=True)),
        "robust_nonuniform_advantage": robust_nonuniform_advantage,
        "gain_window": gain_window,
        "pass": passed,
    }


def run(output: Path, base_commit: str) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root.resolve() != EXPECTED_PROJECT_ROOT:
        raise RuntimeError(f"project mount drift: {repo_root.resolve()}")
    if output.resolve() != EXPECTED_OUTPUT:
        raise RuntimeError(f"output boundary mismatch: {output.resolve()} != {EXPECTED_OUTPUT}")
    if output.exists() or output.parent.exists() and any(output.parent.iterdir()):
        raise RuntimeError("create-only output target is not empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-CPU environment drift: {variable}={os.environ.get(variable)!r}")
    if os.environ.get("PAPER2_IMAGE_ID") != EXPECTED_IMAGE_ID:
        raise RuntimeError("container image identity drift")
    if not os.environ.get("PYTHONPATH", "").startswith(EXPECTED_PYTHONPATH_PREFIX):
        raise RuntimeError("PYTHONPATH drift")

    import dolfinx
    from paper2_hybrid.config import ACTIVE_CONFIG

    dolfinx_path = Path(dolfinx.__file__).resolve()
    if not str(dolfinx_path).startswith("/usr/local/dolfinx-real/lib/python3.12/dist-packages/dolfinx/"):
        raise RuntimeError(f"dolfinx import path drift: {dolfinx_path}")
    started = time.perf_counter()
    ledger = SolveLedger(SOLVE_BUDGET_SECONDS)
    source_hashes = {relative: _sha256(repo_root / relative) for relative in SOURCE_PATHS}
    config = replace(
        ACTIVE_CONFIG,
        ecm_thickness=0.3 * ACTIVE_CONFIG.length,
        ecm_relaxation_time=0.2 * ACTIVE_CONFIG.period,
        activation_peak=0.10,
    ).checked()
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "RUNNING",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": base_commit,
        "source_hashes": source_hashes,
        "frozen_scope": {
            "case": "A1",
            "active_profile": "uniform",
            "activation_peak": 0.10,
            "ecm_thickness_over_length": 0.3,
            "ecm_relaxation_time_over_period": 0.2,
            "steps_per_cycle": STEPS_PER_CYCLE,
            "spatial_levels": list(SPATIAL_LEVELS),
            "footprint_count": FOOTPRINT_COUNT,
            "fd_columns": list(FD_COLUMNS),
            "fd_amplitudes": list(FD_AMPLITUDES),
            "pressure_wss_fluid": False,
            "holdouts_read": False,
        },
        "actual_config": {**asdict(config), "config_digest": config.digest()},
        "runtime": {
            "container_image": "dolfinx/dolfinx:v0.11.0",
            "container_image_id": os.environ.get("PAPER2_IMAGE_ID"),
            "container_name": os.environ.get("PAPER2_CONTAINER_NAME"),
            "network": "none",
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "gpu_count": 0,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "dolfinx": dolfinx.__version__,
            "dolfinx_path": dolfinx_path.as_posix(),
        },
        "claim_boundary": {
            "evidence": "mechanical-kernel feasibility for a continuum-plus-elastic-chain baseline",
            "not_dcm_evidence": True,
            "endocardium_is_elastic_chain_with_common_macro_affine_mode": True,
            "not_full_slow_system_stability_proof": True,
            "not_experimental_reachability_or_biological_calibration": True,
            "not_scientific_gate_pass_until_independent_supervisor_review": True,
            "fixed_frequency_not_paper3_frequency_decoding": True,
        },
    }
    try:
        levels = {label: _level_result(label, config, ledger) for label in SPATIAL_LEVELS}
        cross_grid = _cross_grid(levels)
        all_values_finite = _finite(levels) and _finite(cross_grid)
        numerical_pass = bool(
            all_values_finite
            and all(levels[label]["numerical_level_pass"] for label in SPATIAL_LEVELS)
            and cross_grid["pass"]
        )
        summary.update(
            {
                "status": "COMPLETED_NUMERICAL_PASS" if numerical_pass else "COMPLETED_NUMERICAL_FAIL",
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "levels": levels,
                "cross_grid": cross_grid,
                "all_values_finite": all_values_finite,
                "numerical_gate_pass": numerical_pass,
                "scientific_gate_status": "PENDING_INDEPENDENT_SUPERVISOR_REVIEW",
            }
        )
    except BaseException as error:
        summary.update(
            {
                "status": "FAILED_CLOSED",
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "numerical_gate_pass": False,
                "scientific_gate_status": "NOT_EVALUABLE",
            }
        )
    finally:
        summary["solve_ledger"] = {
            "budget_seconds": ledger.budget_seconds,
            "elapsed_seconds": ledger.elapsed_seconds,
            "factorization_count": ledger.factorization_count,
            "rhs_count": ledger.rhs_count,
            "records": ledger.records,
        }
        summary["total_wall_seconds"] = time.perf_counter() - started
        summary["peak_rss_gib"] = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / (1024.0**2)
        summary["memory_budget_hard_enforced_by_container"] = True
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps({key: summary.get(key) for key in ("status", "numerical_gate_pass", "scientific_gate_status", "total_wall_seconds")}, indent=2))
    return 0 if summary["status"] == "COMPLETED_NUMERICAL_PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    arguments = parser.parse_args()
    return run(arguments.output, arguments.base_commit)


if __name__ == "__main__":
    sys.exit(main())
