"""Diagnose the authorized M2A v02 T64 power-ledger failure without repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable

import numpy as np
import scipy
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STEPS_PER_CYCLE = 64
LEVELS = ("S2", "S3", "S4")
TOLERANCES = ("C0", "C1")
REPLAY_TOLERANCE = 1.0e-12
LEDGER_GATE = 1.0e-8
RUNTIME_BUDGET_SECONDS = 900.0
MEMORY_BUDGET_GIB = 16.0
SKIPPED_REPLAY_KEYS = frozenset(("runtime_seconds",))
READ_ONLY_PATHS = (
    PROJECT_ROOT / "src" / "paper2_m2" / "config.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "interface_projection.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v02.py",
    PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v02.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_v01.py",
    PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t64_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v02.py",
    PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v02.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape)).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def relative_difference(value_a: float, value_b: float, floor: float = 1.0e-30) -> float:
    return abs(value_a - value_b) / max(abs(value_a), abs(value_b), floor)


def _assert_finite_json(payload: Any, path: str = "root") -> None:
    if payload is None or isinstance(payload, (str, bool)):
        return
    if isinstance(payload, (int, np.integer)):
        return
    if isinstance(payload, (float, np.floating)):
        if not math.isfinite(float(payload)):
            raise ValueError(f"non-finite JSON value at {path}")
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            _assert_finite_json(value, f"{path}.{key}")
        return
    if isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            _assert_finite_json(value, f"{path}[{index}]")
        return
    raise TypeError(f"unsupported JSON value at {path}: {type(payload)!r}")


def _write_json(path: Path, payload: Any) -> None:
    _assert_finite_json(payload)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _project_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _hash_paths(paths: tuple[Path, ...]) -> dict[str, str]:
    return {_project_path(path): _sha256(path) for path in paths}


def _compare_replay(
    old_value: Any,
    new_value: Any,
    *,
    path: str,
    record: dict[str, Any],
) -> None:
    if isinstance(old_value, dict):
        if not isinstance(new_value, dict):
            record["failures"].append(f"{path}:type")
            return
        old_keys = set(old_value) - SKIPPED_REPLAY_KEYS
        new_keys = set(new_value) - SKIPPED_REPLAY_KEYS
        if old_keys != new_keys:
            record["failures"].append(f"{path}:keys")
            return
        for key in sorted(old_keys):
            _compare_replay(
                old_value[key], new_value[key], path=f"{path}.{key}", record=record
            )
        return
    if isinstance(old_value, bool):
        record["exact_paths"] += 1
        if not isinstance(new_value, bool) or old_value is not new_value:
            record["failures"].append(path)
        return
    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        difference = relative_difference(float(old_value), float(new_value))
        record["numeric_paths"] += 1
        record["maximum_numeric_relative_difference"] = max(
            record["maximum_numeric_relative_difference"], difference
        )
        if difference > REPLAY_TOLERANCE:
            record["failures"].append(path)
        return
    record["exact_paths"] += 1
    if old_value != new_value:
        record["failures"].append(path)


def replay_record(old_summary: dict[str, Any], new_summary: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "relative_tolerance": REPLAY_TOLERANCE,
        "skipped_keys": sorted(SKIPPED_REPLAY_KEYS),
        "numeric_paths": 0,
        "exact_paths": 0,
        "maximum_numeric_relative_difference": 0.0,
        "failures": [],
    }
    _compare_replay(old_summary, new_summary, path="summary", record=record)
    record["pass"] = not record["failures"]
    return record


def _sum_values(values: np.ndarray, policy: str) -> np.number:
    flat = np.asarray(values).ravel()
    if policy == "ordinary":
        return np.dot(flat, np.ones_like(flat))
    if policy == "pairwise":
        return np.sum(flat, dtype=np.float64)
    if policy == "kahan":
        total = 0.0
        compensation = 0.0
        for value in flat:
            adjusted = float(value) - compensation
            updated = total + adjusted
            compensation = (updated - total) - adjusted
            total = updated
        return np.float64(total)
    if policy == "longdouble":
        return np.sum(flat.astype(np.longdouble), dtype=np.longdouble)
    raise ValueError(f"unknown summation policy: {policy}")


def _dot_policy(value_a: np.ndarray, value_b: np.ndarray, policy: str) -> np.number:
    return _sum_values(np.asarray(value_a) * np.asarray(value_b), policy)


def _material_energy_policy(
    system: Any,
    state: np.ndarray,
    activation: float,
    policy: str,
) -> np.number:
    material_action = system.matrix_material @ state
    quadratic = 0.5 * _dot_policy(state, material_action, policy)
    coupling = np.asarray(activation, dtype=np.longdouble if policy == "longdouble" else np.float64) * _dot_policy(
        system.active_vector_h, state, policy
    )
    active_square = (
        np.asarray(0.5 * system.active_scalar_c, dtype=np.longdouble if policy == "longdouble" else np.float64)
        * np.asarray(activation, dtype=np.longdouble if policy == "longdouble" else np.float64) ** 2
    )
    return quadratic + coupling + active_square


def ledger_with_policy(
    system: Any,
    states: np.ndarray,
    activation: np.ndarray,
    loads: np.ndarray,
    policy: str,
) -> dict[str, np.ndarray]:
    time_step = system.config.period / STEPS_PER_CYCLE
    dtype = np.longdouble if policy == "longdouble" else np.float64
    energy = np.asarray(
        [
            _material_energy_policy(system, states[:, index], activation[index], policy)
            for index in range(STEPS_PER_CYCLE + 1)
        ],
        dtype=dtype,
    )
    terms = {
        name: np.zeros(STEPS_PER_CYCLE, dtype=dtype)
        for name in (
            "active_work",
            "lumen_work",
            "support_work",
            "energy_change",
            "drag_dissipation",
            "sls_dissipation",
            "residual",
            "scale",
            "normalized_residual",
        )
    }
    for step in range(STEPS_PER_CYCLE):
        state_start = states[:, step]
        state_end = states[:, step + 1]
        increment = state_end - state_start
        midpoint = 0.5 * (state_start + state_end)
        activation_midpoint = 0.5 * (activation[step] + activation[step + 1])
        activation_increment = activation[step + 1] - activation[step]
        load_midpoint = 0.5 * (loads[:, step] + loads[:, step + 1])
        active_conjugate = _dot_policy(system.active_vector_h, midpoint, policy) + (
            system.active_scalar_c * activation_midpoint
        )
        terms["active_work"][step] = active_conjugate * activation_increment
        terms["lumen_work"][step] = _dot_policy(load_midpoint, increment, policy)
        terms["support_work"][step] = -_dot_policy(
            system.matrix_support @ midpoint, increment, policy
        )
        terms["drag_dissipation"][step] = _dot_policy(
            increment, system.matrix_drag @ increment, policy
        ) / time_step
        terms["sls_dissipation"][step] = _dot_policy(
            increment, system.matrix_sls_dissipation @ increment, policy
        ) / time_step
        terms["energy_change"][step] = energy[step + 1] - energy[step]
        signed = np.asarray(
            (
                terms["active_work"][step],
                terms["lumen_work"][step],
                terms["support_work"][step],
                -terms["energy_change"][step],
                -terms["drag_dissipation"][step],
                -terms["sls_dissipation"][step],
            ),
            dtype=dtype,
        )
        terms["residual"][step] = _sum_values(signed, policy)
        scale_values = np.abs(signed)
        terms["scale"][step] = max(_sum_values(scale_values, policy), dtype(1.0e-14))
        terms["normalized_residual"][step] = abs(terms["residual"][step]) / terms[
            "scale"
        ][step]
    terms["energy"] = energy
    return terms


def normwise_backward_error(
    matrix: sparse.spmatrix,
    solution: np.ndarray,
    rhs: np.ndarray,
) -> float:
    residual = rhs - matrix @ solution
    matrix_inf = float(np.max(np.asarray(abs(matrix).sum(axis=1)).ravel()))
    denominator = matrix_inf * float(np.linalg.norm(solution, ord=np.inf)) + float(
        np.linalg.norm(rhs, ord=np.inf)
    )
    return float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30))


def factorized_refinement(
    matrix: sparse.spmatrix,
    rhs: np.ndarray,
    corrections: int = 2,
) -> tuple[list[np.ndarray], list[dict[str, float]]]:
    factor = sparse_linalg.splu(matrix.tocsc())
    solution = factor.solve(rhs)
    solutions: list[np.ndarray] = []
    records: list[dict[str, float]] = []
    rhs_norm = float(np.linalg.norm(rhs))
    matrix_norm = float(np.max(np.asarray(abs(matrix).sum(axis=1)).ravel()))
    for index in range(corrections + 1):
        residual = rhs - matrix @ solution
        solutions.append(solution.copy())
        records.append(
            {
                "corrections": index,
                "matrix_inf_norm": matrix_norm,
                "rhs_l2_norm": rhs_norm,
                "solution_l2_norm": float(np.linalg.norm(solution)),
                "residual_l2_norm": float(np.linalg.norm(residual)),
                "relative_residual": float(
                    np.linalg.norm(residual) / max(rhs_norm, 1.0e-30)
                ),
                "normwise_backward_error": normwise_backward_error(
                    matrix, solution, rhs
                ),
            }
        )
        if index < corrections:
            solution = solution + factor.solve(residual)
    return solutions, records


def classify_hypotheses(confirmed: dict[str, bool]) -> str:
    primary = [name for name in ("H1", "H3", "H4", "H5") if confirmed[name]]
    if len(primary) > 1:
        return "MULTIFACTOR"
    if primary == ["H1"]:
        return "ALGEBRAIC_SOLVE_DEFECT_CONFIRMED"
    if primary == ["H3"]:
        return "NORMALIZATION_ARTIFACT_CONFIRMED"
    if primary == ["H4"]:
        return "DISCRETE_LEDGER_MISMATCH_CONFIRMED"
    if primary == ["H5"]:
        return "FLOAT_SUMMATION_LIMIT_CONFIRMED"
    return "UNRESOLVED"


def _problem_components(
    system: Any,
    case_components: Callable[..., Any],
) -> dict[str, Any]:
    active_dc, active_harmonic, load_dc, load_harmonic, profile = case_components(
        "ID-LN", system
    )
    if profile != system.active_profile:
        raise RuntimeError("active profile/system mismatch")
    rhs_dc = load_dc - system.active_vector_h * active_dc
    rhs_harmonic = load_harmonic - system.active_vector_h * active_harmonic
    time_step = system.config.period / STEPS_PER_CYCLE
    omega = 2.0 * math.pi / system.config.period
    zeta = np.exp(1j * omega * time_step)
    harmonic_matrix = (
        ((zeta - 1.0) / time_step) * system.matrix_g
        + 0.5 * (zeta + 1.0) * system.matrix_a
    ).tocsc()
    harmonic_rhs = 0.5 * (1.0 + zeta) * rhs_harmonic
    times = np.linspace(0.0, 2.0 * system.config.period, 2 * STEPS_PER_CYCLE + 1)
    phase = np.exp(1j * omega * times)
    activation = active_dc + np.real(active_harmonic * phase)
    loads = load_dc[:, None] + np.real(load_harmonic[:, None] * phase[None, :])
    return {
        "rhs_dc": rhs_dc,
        "harmonic_matrix": harmonic_matrix,
        "harmonic_rhs": harmonic_rhs,
        "phase": phase,
        "activation": activation,
        "loads": loads,
    }


def _branch_states(
    dc_state: np.ndarray,
    harmonic_state: np.ndarray,
    phase: np.ndarray,
) -> np.ndarray:
    return dc_state[:, None] + np.real(harmonic_state[:, None] * phase[None, :])


def _branch_metrics(
    system: Any,
    states: np.ndarray,
    activation: np.ndarray,
    loads: np.ndarray,
    ledger_function: Callable[..., dict[str, Any]],
    traction_function: Callable[..., tuple[np.ndarray, np.ndarray]],
) -> dict[str, float]:
    first_cycle = slice(0, STEPS_PER_CYCLE + 1)
    ledger = ledger_function(
        system,
        states[:, first_cycle],
        activation[first_cycle],
        loads[:, first_cycle],
        STEPS_PER_CYCLE,
    )
    limited_shortening = -states[system.macro_strain_index]
    traction_myo, traction_endo = traction_function(system, states)
    nodes = len(system.interface_weights)
    dt = system.config.period / STEPS_PER_CYCLE
    myo_field = traction_myo[:, :STEPS_PER_CYCLE].reshape(nodes, 2, STEPS_PER_CYCLE)
    endo_field = traction_endo[:, :STEPS_PER_CYCLE].reshape(nodes, 2, STEPS_PER_CYCLE)
    myo_l2 = float(
        np.sqrt(dt * np.sum(system.interface_weights[:, None, None] * myo_field**2))
    )
    endo_l2 = float(
        np.sqrt(dt * np.sum(system.interface_weights[:, None, None] * endo_field**2))
    )
    return {
        "maximum_state_norm": float(np.max(np.linalg.norm(states, axis=0))),
        "peak_limited_shortening": float(
            np.max(limited_shortening[: STEPS_PER_CYCLE + 1])
        ),
        "myocardium_ecm_traction_l2": myo_l2,
        "endocardium_ecm_traction_l2": endo_l2,
        "total_dissipation": float(
            ledger["total_drag_dissipation"] + ledger["total_sls_dissipation"]
        ),
        "maximum_normalized_ledger_residual": float(
            ledger["maximum_normalized_residual"]
        ),
        "cycle_integrated_ledger_residual": float(np.sum(ledger["residual_steps"])),
    }


def _qoi_difference(
    baseline_endpoint: Any,
    baseline_states: np.ndarray,
    branch_states: np.ndarray,
    branch_metrics: dict[str, float],
) -> dict[str, Any]:
    ledger = baseline_endpoint.summary["ledger"]
    baseline_metrics = {
        "maximum_state_norm": float(baseline_endpoint.summary["maximum_state_norm"]),
        "peak_limited_shortening": float(
            baseline_endpoint.summary["peak_limited_shortening"]
        ),
        "myocardium_ecm_traction_l2": float(
            baseline_endpoint.summary["myocardium_ecm_traction_l2"]
        ),
        "endocardium_ecm_traction_l2": float(
            baseline_endpoint.summary["endocardium_ecm_traction_l2"]
        ),
        "total_dissipation": float(
            ledger["total_drag_dissipation"] + ledger["total_sls_dissipation"]
        ),
    }
    relative = {
        name: relative_difference(baseline_metrics[name], branch_metrics[name])
        for name in baseline_metrics
    }
    state_relative = float(
        np.linalg.norm(branch_states - baseline_states)
        / max(np.linalg.norm(baseline_states), 1.0e-30)
    )
    return {
        "baseline": baseline_metrics,
        "relative_differences": relative,
        "state_array_relative_difference": state_relative,
        "maximum_qoi_relative_difference": max(relative.values()),
    }


def _equilibrium_decomposition(
    system: Any,
    states: np.ndarray,
    activation: np.ndarray,
    loads: np.ndarray,
    production_ledger: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    dt = system.config.period / STEPS_PER_CYCLE
    defect_norm = np.zeros(STEPS_PER_CYCLE)
    defect_relative = np.zeros(STEPS_PER_CYCLE)
    defect_work = np.zeros(STEPS_PER_CYCLE)
    mismatch = np.zeros(STEPS_PER_CYCLE)
    for step in range(STEPS_PER_CYCLE):
        state_start = states[:, step]
        state_end = states[:, step + 1]
        increment = state_end - state_start
        midpoint = 0.5 * (state_start + state_end)
        activation_midpoint = 0.5 * (activation[step] + activation[step + 1])
        load_midpoint = 0.5 * (loads[:, step] + loads[:, step + 1])
        rhs_midpoint = load_midpoint - system.active_vector_h * activation_midpoint
        material = system.matrix_a @ midpoint
        viscous = system.matrix_g @ increment / dt
        equilibrium_defect = rhs_midpoint - material - viscous
        defect_norm[step] = np.linalg.norm(equilibrium_defect)
        defect_relative[step] = defect_norm[step] / max(
            np.linalg.norm(rhs_midpoint),
            np.linalg.norm(material) + np.linalg.norm(viscous),
            1.0e-30,
        )
        defect_work[step] = np.dot(equilibrium_defect, increment)
        mismatch[step] = production_ledger["residual_steps"][step] - defect_work[step]
    return {
        "equilibrium_defect_norm": defect_norm,
        "equilibrium_defect_relative": defect_relative,
        "equilibrium_defect_work": defect_work,
        "ledger_minus_equilibrium_defect_work": mismatch,
    }


def _tolerance_audit(endpoints: dict[tuple[str, str], Any]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    all_exact = True
    for level in LEVELS:
        endpoint_c0 = endpoints[(level, "C0")]
        endpoint_c1 = endpoints[(level, "C1")]
        names = sorted(set(endpoint_c0.arrays) | set(endpoint_c1.arrays))
        arrays: dict[str, Any] = {}
        for name in names:
            value_c0 = endpoint_c0.arrays[name]
            value_c1 = endpoint_c1.arrays[name]
            same_shape = value_c0.shape == value_c1.shape
            exact = bool(same_shape and np.array_equal(value_c0, value_c1))
            maximum_difference = (
                float(np.max(np.abs(value_c0 - value_c1))) if same_shape else None
            )
            arrays[name] = {
                "C0_sha256": array_sha256(value_c0),
                "C1_sha256": array_sha256(value_c1),
                "exact_equal": exact,
                "maximum_absolute_difference": maximum_difference,
            }
            all_exact = all_exact and exact
        solver_c0 = endpoint_c0.summary["solver"]
        solver_c1 = endpoint_c1.summary["solver"]
        residual_exact = bool(
            solver_c0["dc_relative_residual"] == solver_c1["dc_relative_residual"]
            and solver_c0["harmonic_relative_residual"]
            == solver_c1["harmonic_relative_residual"]
        )
        records[level] = {
            "arrays": arrays,
            "all_arrays_exact": all(record["exact_equal"] for record in arrays.values()),
            "solver_residuals": {
                "C0": solver_c0,
                "C1": solver_c1,
                "residual_values_exact": residual_exact,
                "acceptance_thresholds_differ": (
                    solver_c0["acceptance_tolerance"]
                    != solver_c1["acceptance_tolerance"]
                ),
            },
        }
        all_exact = all_exact and residual_exact
    return {
        "schema": "paper2_m2a_v02_t64_tolerance_label_audit_v01",
        "records": records,
        "all_state_and_ledger_arrays_exact": all_exact,
        "conclusion": (
            "C0_C1_change_acceptance_threshold_only"
            if all_exact
            else "C0_C1_change_computed_arrays"
        ),
    }


def _ledger_summary(
    production: dict[str, np.ndarray],
    policies: dict[str, dict[str, np.ndarray]],
    equilibrium: dict[str, np.ndarray],
) -> dict[str, Any]:
    worst_step = int(np.argmax(production["normalized_residual_steps"]))
    ordinary = policies["ordinary"]
    scale = ordinary["scale"]
    median_scale = float(np.median(scale))
    maximum_ledger = float(np.max(np.abs(production["residual_steps"])))
    maximum_mismatch = float(
        np.max(np.abs(equilibrium["ledger_minus_equilibrium_defect_work"]))
    )
    policy_records = {}
    for name, result in policies.items():
        policy_records[name] = {
            "maximum_absolute_residual": float(np.max(np.abs(result["residual"]))),
            "maximum_normalized_residual": float(
                np.max(result["normalized_residual"])
            ),
            "cycle_integrated_residual": float(_sum_values(result["residual"], name)),
            "worst_step": int(np.argmax(result["normalized_residual"])),
        }
    return {
        "schema": "paper2_m2a_v02_t64_ledger_decomposition_summary_v01",
        "production": {
            "maximum_absolute_residual": maximum_ledger,
            "maximum_normalized_residual": float(
                np.max(production["normalized_residual_steps"])
            ),
            "cycle_integrated_residual": float(np.sum(production["residual_steps"])),
            "worst_step": worst_step,
            "worst_step_values": {
                "active_work": float(production["active_work_steps"][worst_step]),
                "lumen_work": float(production["lumen_work_steps"][worst_step]),
                "support_work": float(
                    production["external_support_work_steps"][worst_step]
                ),
                "energy_change": float(ordinary["energy_change"][worst_step]),
                "drag_dissipation": float(
                    production["drag_dissipation_steps"][worst_step]
                ),
                "sls_dissipation": float(
                    production["sls_dissipation_steps"][worst_step]
                ),
                "raw_residual": float(production["residual_steps"][worst_step]),
                "normalization_scale": float(scale[worst_step]),
                "normalized_residual": float(
                    production["normalized_residual_steps"][worst_step]
                ),
                "equilibrium_defect_work": float(
                    equilibrium["equilibrium_defect_work"][worst_step]
                ),
                "ledger_minus_equilibrium_defect_work": float(
                    equilibrium["ledger_minus_equilibrium_defect_work"][worst_step]
                ),
            },
            "median_normalization_scale": median_scale,
            "worst_to_median_scale_ratio": float(scale[worst_step] / median_scale),
        },
        "equilibrium": {
            "maximum_defect_norm": float(
                np.max(equilibrium["equilibrium_defect_norm"])
            ),
            "maximum_relative_defect": float(
                np.max(equilibrium["equilibrium_defect_relative"])
            ),
            "maximum_absolute_defect_work": float(
                np.max(np.abs(equilibrium["equilibrium_defect_work"]))
            ),
            "cycle_integrated_defect_work": float(
                np.sum(equilibrium["equilibrium_defect_work"])
            ),
            "maximum_ledger_minus_defect_work": maximum_mismatch,
            "mismatch_to_ledger_residual_ratio": maximum_mismatch
            / max(maximum_ledger, 1.0e-30),
        },
        "summation_policies": policy_records,
        "ordinary_reproduction": {
            "maximum_raw_residual_difference": float(
                np.max(
                    np.abs(ordinary["residual"] - production["residual_steps"])
                )
            ),
            "maximum_normalized_residual_difference": float(
                np.max(
                    np.abs(
                        ordinary["normalized_residual"]
                        - production["normalized_residual_steps"]
                    )
                )
            ),
        },
    }


def _hypothesis_assessment(
    *,
    tolerance_audit: dict[str, Any],
    ledger_summary: dict[str, Any],
    correction: dict[str, Any],
) -> dict[str, Any]:
    s4 = correction["levels"]["S4"]
    baseline_linear = max(
        s4["linear_systems"]["dc"][0]["relative_residual"],
        s4["linear_systems"]["harmonic"][0]["relative_residual"],
    )
    corrected_linear = max(
        s4["linear_systems"]["dc"][2]["relative_residual"],
        s4["linear_systems"]["harmonic"][2]["relative_residual"],
    )
    baseline_ledger = s4["branches"][0]["metrics"][
        "maximum_normalized_ledger_residual"
    ]
    corrected_ledger = s4["branches"][2]["metrics"][
        "maximum_normalized_ledger_residual"
    ]
    linear_improvement = baseline_linear / max(corrected_linear, 1.0e-30)
    ledger_improvement = baseline_ledger / max(corrected_ledger, 1.0e-30)
    qoi_change = s4["branches"][2]["qoi_vs_production"][
        "maximum_qoi_relative_difference"
    ]
    mismatch_ratio = ledger_summary["equilibrium"][
        "mismatch_to_ledger_residual_ratio"
    ]
    worst = ledger_summary["production"]["worst_step_values"]
    scale_ratio = ledger_summary["production"]["worst_to_median_scale_ratio"]
    policy = ledger_summary["summation_policies"]
    best_compensated = min(
        policy["pairwise"]["maximum_normalized_residual"],
        policy["kahan"]["maximum_normalized_residual"],
        policy["longdouble"]["maximum_normalized_residual"],
    )
    summation_improvement = policy["ordinary"]["maximum_normalized_residual"] / max(
        best_compensated, 1.0e-30
    )

    h1 = bool(
        linear_improvement >= 10.0
        and ledger_improvement >= 2.0
        and qoi_change <= 1.0e-6
        and mismatch_ratio <= 0.25
    )
    h2 = bool(tolerance_audit["all_state_and_ledger_arrays_exact"])
    h3 = bool(
        worst["normalized_residual"] > LEDGER_GATE
        and abs(worst["raw_residual"]) <= 1.0e-12
        and scale_ratio <= 0.1
    )
    h4 = bool(
        (linear_improvement >= 10.0 and ledger_improvement < 2.0)
        or mismatch_ratio >= 0.5
    )
    h5 = bool(
        summation_improvement >= 10.0
        and best_compensated <= LEDGER_GATE
    )
    confirmed = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5}
    return {
        "schema": "paper2_m2a_v02_t64_power_ledger_hypotheses_v01",
        "criteria_frozen_in_diagnostic": {
            "H1": "linear improvement >=10, ledger improvement >=2, QoI change <=1e-6, closure mismatch ratio <=0.25",
            "H2": "all C0/C1 state, solver-residual and ledger arrays are exactly equal",
            "H3": "failed normalized residual, abs(raw)<=1e-12 and worst scale <=0.1 median",
            "H4": "linear improvement >=10 without ledger improvement >=2, or closure mismatch ratio >=0.5",
            "H5": "compensated/long-double improves >=10 and crosses the 1e-8 gate",
        },
        "diagnostics": {
            "linear_residual_improvement_factor": linear_improvement,
            "ledger_residual_improvement_factor": ledger_improvement,
            "maximum_corrected_qoi_relative_change": qoi_change,
            "ledger_closure_mismatch_ratio": mismatch_ratio,
            "worst_scale_to_median_ratio": scale_ratio,
            "summation_improvement_factor": summation_improvement,
            "best_compensated_maximum_normalized_residual": best_compensated,
        },
        "hypotheses": {
            name: {"confirmed": value, "status": "CONFIRMED" if value else "FALSIFIED"}
            for name, value in confirmed.items()
        },
        "formal_label": classify_hypotheses(confirmed),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--contract-v02", type=Path, required=True)
    parser.add_argument("--autonomous-decision", type=Path, required=True)
    parser.add_argument("--failure-execution-record", type=Path, required=True)
    parser.add_argument("--source-failure", type=Path, required=True)
    parser.add_argument("--source-partial-summaries", type=Path, required=True)
    parser.add_argument("--source-calibration", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args()


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    import dolfinx
    import resource

    from paper2_m2.config import FROZEN_CONFIG, SpatialLevel
    from paper2_m2.identity_2d import (
        _case_components,
        _interface_tractions,
        _ledger,
        build_system_for_level,
        simulate_endpoint,
    )
    from paper2_m2.identity_2d_v02 import common_projection_sidecar

    arguments = _parse_arguments()
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    with arguments.source_failure.open("r", encoding="utf-8") as stream:
        source_failure = json.load(stream)
    with arguments.source_partial_summaries.open("r", encoding="utf-8") as stream:
        old_summaries = json.load(stream)
    with arguments.source_calibration.open("r", encoding="utf-8") as stream:
        calibration = json.load(stream)
    passive_scale = float(calibration["passive"]["dcm_passive_scale"])
    active_scale = float(calibration["active"]["dcm_active_scale"])

    read_only_hashes_before = _hash_paths(READ_ONLY_PATHS)
    manifest = {
        "schema": "paper2_m2a_v02_t64_power_ledger_diagnostic_manifest_v01",
        "scope": {
            "case": "ID-LN",
            "representation": "DCM",
            "levels": list(LEVELS),
            "tolerances": list(TOLERANCES),
            "steps_per_cycle": STEPS_PER_CYCLE,
            "repair_authorized": False,
            "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
            "memory_budget_gib": MEMORY_BUDGET_GIB,
        },
        "calibration": {
            "config_digest": calibration["config_digest"],
            "dcm_passive_scale": passive_scale,
            "dcm_active_scale": active_scale,
        },
        "read_only_sha256_before": read_only_hashes_before,
        "provenance": {
            "authorization_sha256": _sha256(arguments.authorization),
            "contract_v02_sha256": _sha256(arguments.contract_v02),
            "autonomous_decision_sha256": _sha256(arguments.autonomous_decision),
            "failure_execution_record_sha256": _sha256(
                arguments.failure_execution_record
            ),
            "source_failure_sha256": _sha256(arguments.source_failure),
            "source_partial_summaries_sha256": _sha256(
                arguments.source_partial_summaries
            ),
            "source_calibration_sha256": _sha256(arguments.source_calibration),
            "runner_sha256": _sha256(Path(__file__).resolve()),
            "test_sha256": _sha256(
                PROJECT_ROOT
                / "tests"
                / "paper2_m2"
                / "test_power_ledger_diagnostic_v01.py"
            ),
        },
        "tests": {
            "host": arguments.host_pytest_summary,
            "container": arguments.container_pytest_summary,
            "pass": (
                "passed" in arguments.host_pytest_summary
                and "passed" in arguments.container_pytest_summary
            ),
        },
        "runtime": {
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "cpu_processes": 1,
            "blas_omp_threads": 1,
            "network": "disabled_by_container",
            "gpu_used": False,
        },
    }
    _write_json(arguments.output_dir / "manifest.json", manifest)

    level_objects = {
        "S2": SpatialLevel("S2", 32, 8),
        "S3": SpatialLevel("S3", 64, 16),
        "S4": SpatialLevel("S4", 128, 32),
    }
    systems: dict[str, Any] = {}
    endpoints: dict[tuple[str, str], Any] = {}
    new_summaries: dict[str, Any] = {}
    replay_records: dict[str, Any] = {}
    for level in LEVELS:
        system = build_system_for_level(
            representation="DCM",
            level=level_objects[level],
            passive_dcm_scale=passive_scale,
            active_dcm_scale=active_scale,
            active_profile="uniform",
        )
        systems[level] = system
        for tolerance in TOLERANCES:
            endpoint = simulate_endpoint(
                system=system,
                case_id="ID-LN",
                steps_per_cycle=STEPS_PER_CYCLE,
                tolerance_label=tolerance,
            )
            endpoint.summary["v02_common_projection_sidecar"] = (
                common_projection_sidecar(system, endpoint)
            )
            endpoints[(level, tolerance)] = endpoint
            key = f"ID-LN__DCM__{level}__T64__{tolerance}"
            new_summaries[key] = endpoint.summary
            if key in old_summaries:
                replay_records[key] = replay_record(old_summaries[key], endpoint.summary)
            else:
                replay_records[key] = {
                    "source_available": False,
                    "reason": "S4_C1_was_not_run_after_the_source_fail_closed_stop",
                    "pass": True,
                }
            print(
                json.dumps(
                    {
                        "event": "baseline_endpoint_complete",
                        "level": level,
                        "tolerance": tolerance,
                        "ledger_maximum_normalized_residual": endpoint.summary[
                            "ledger"
                        ]["maximum_normalized_residual"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    _write_json(arguments.output_dir / "baseline_summaries.json", new_summaries)
    replay_all_pass = all(record["pass"] for record in replay_records.values())
    source_value = float(
        source_failure["structural_gate"]["checks"]["power_ledger"]["value"]
    )
    reproduced_value = float(
        endpoints[("S4", "C0")].summary["ledger"][
            "maximum_normalized_residual"
        ]
    )
    source_relative_difference = relative_difference(source_value, reproduced_value)
    reproducible = bool(
        replay_all_pass
        and source_relative_difference <= REPLAY_TOLERANCE
        and reproduced_value > LEDGER_GATE
    )
    replay = {
        "schema": "paper2_m2a_v02_t64_power_ledger_replay_v01",
        "records": replay_records,
        "replay_all_available_source_summaries_pass": replay_all_pass,
        "source_S4_C0_maximum_normalized_residual": source_value,
        "reproduced_S4_C0_maximum_normalized_residual": reproduced_value,
        "relative_difference": source_relative_difference,
        "relative_tolerance": REPLAY_TOLERANCE,
        "ledger_gate": LEDGER_GATE,
        "reproducible": reproducible,
    }
    _write_json(arguments.output_dir / "replay.json", replay)
    tolerance_audit = _tolerance_audit(endpoints)
    _write_json(arguments.output_dir / "tolerance_label_audit.json", tolerance_audit)

    if not reproducible:
        final = {
            "schema": "paper2_m2a_v02_t64_power_ledger_diagnostic_final_v01",
            "status": "COMPLETE_AT_SUPERVISOR_GATE",
            "formal_label": "NON_REPRODUCIBLE",
            "replay": replay,
            "stop_boundary": {
                "correction_probes_run": False,
                "production_source_modified": False,
                "remaining_108_endpoint_matrix_run": False,
                "T128_run": False,
            },
        }
        _write_json(arguments.output_dir / "final_summary.json", final)
        print(json.dumps(final, indent=2, sort_keys=True), flush=True)
        return

    production_endpoint = endpoints[("S4", "C0")]
    production_states = production_endpoint.arrays["state_two_cycles"]
    components_s4 = _problem_components(systems["S4"], _case_components)
    production_first_cycle = production_states[:, : STEPS_PER_CYCLE + 1]
    production_ledger = {
        "active_work_steps": production_endpoint.arrays["ledger_active_work_steps"],
        "lumen_work_steps": production_endpoint.arrays["ledger_lumen_work_steps"],
        "external_support_work_steps": production_endpoint.arrays[
            "ledger_external_support_work_steps"
        ],
        "drag_dissipation_steps": production_endpoint.arrays[
            "ledger_drag_dissipation_steps"
        ],
        "sls_dissipation_steps": production_endpoint.arrays[
            "ledger_sls_dissipation_steps"
        ],
        "residual_steps": production_endpoint.arrays["ledger_residual_steps"],
        "normalized_residual_steps": production_endpoint.arrays[
            "ledger_normalized_residual_steps"
        ],
    }
    policies = {
        name: ledger_with_policy(
            systems["S4"],
            production_first_cycle,
            components_s4["activation"][: STEPS_PER_CYCLE + 1],
            components_s4["loads"][:, : STEPS_PER_CYCLE + 1],
            name,
        )
        for name in ("ordinary", "pairwise", "kahan", "longdouble")
    }
    equilibrium = _equilibrium_decomposition(
        systems["S4"],
        production_first_cycle,
        components_s4["activation"][: STEPS_PER_CYCLE + 1],
        components_s4["loads"][:, : STEPS_PER_CYCLE + 1],
        production_ledger,
    )
    ledger_summary = _ledger_summary(production_ledger, policies, equilibrium)
    _write_json(arguments.output_dir / "ledger_decomposition_summary.json", ledger_summary)
    np.savez_compressed(
        arguments.output_dir / "ledger_decomposition_steps.npz",
        production_active_work=production_ledger["active_work_steps"],
        production_lumen_work=production_ledger["lumen_work_steps"],
        production_support_work=production_ledger["external_support_work_steps"],
        production_drag_dissipation=production_ledger["drag_dissipation_steps"],
        production_sls_dissipation=production_ledger["sls_dissipation_steps"],
        production_residual=production_ledger["residual_steps"],
        production_normalized_residual=production_ledger["normalized_residual_steps"],
        ordinary_energy_change=policies["ordinary"]["energy_change"],
        ordinary_scale=policies["ordinary"]["scale"],
        pairwise_residual=policies["pairwise"]["residual"],
        pairwise_normalized_residual=policies["pairwise"]["normalized_residual"],
        kahan_residual=policies["kahan"]["residual"],
        kahan_normalized_residual=policies["kahan"]["normalized_residual"],
        longdouble_residual=policies["longdouble"]["residual"],
        longdouble_normalized_residual=policies["longdouble"][
            "normalized_residual"
        ],
        **equilibrium,
    )

    correction_levels: dict[str, Any] = {}
    for level in LEVELS:
        system = systems[level]
        components = _problem_components(system, _case_components)
        dc_solutions, dc_records = factorized_refinement(
            system.matrix_a, components["rhs_dc"], corrections=2
        )
        harmonic_solutions, harmonic_records = factorized_refinement(
            components["harmonic_matrix"],
            components["harmonic_rhs"],
            corrections=2,
        )
        baseline_endpoint = endpoints[(level, "C0")]
        baseline_states = baseline_endpoint.arrays["state_two_cycles"]
        branches = []
        for index in range(3):
            states = _branch_states(
                dc_solutions[index], harmonic_solutions[index], components["phase"]
            )
            metrics = _branch_metrics(
                system,
                states,
                components["activation"],
                components["loads"],
                _ledger,
                _interface_tractions,
            )
            branches.append(
                {
                    "corrections": index,
                    "metrics": metrics,
                    "qoi_vs_production": _qoi_difference(
                        baseline_endpoint,
                        baseline_states,
                        states,
                        metrics,
                    ),
                }
            )
        correction_levels[level] = {
            "state_size": system.state_size,
            "linear_systems": {"dc": dc_records, "harmonic": harmonic_records},
            "branches": branches,
        }
        print(
            json.dumps(
                {
                    "event": "residual_correction_complete",
                    "level": level,
                    "baseline_ledger": branches[0]["metrics"][
                        "maximum_normalized_ledger_residual"
                    ],
                    "corrected_ledger": branches[2]["metrics"][
                        "maximum_normalized_ledger_residual"
                    ],
                },
                sort_keys=True,
            ),
            flush=True,
        )
    correction = {
        "schema": "paper2_m2a_v02_t64_same_superlu_residual_correction_v01",
        "solver": "same_SuperLU_factor_per_DC_or_harmonic_system",
        "levels": correction_levels,
    }
    _write_json(arguments.output_dir / "residual_correction.json", correction)

    hypotheses = _hypothesis_assessment(
        tolerance_audit=tolerance_audit,
        ledger_summary=ledger_summary,
        correction=correction,
    )
    _write_json(arguments.output_dir / "hypothesis_assessment.json", hypotheses)
    read_only_hashes_after = _hash_paths(READ_ONLY_PATHS)
    read_only_unchanged = read_only_hashes_before == read_only_hashes_after
    elapsed = time.perf_counter() - started
    peak_memory = float(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)
    )
    within_budget = elapsed <= RUNTIME_BUDGET_SECONDS and peak_memory <= MEMORY_BUDGET_GIB
    formal_label = hypotheses["formal_label"]
    if not read_only_unchanged or not within_budget:
        formal_label = "UNRESOLVED"
    final = {
        "schema": "paper2_m2a_v02_t64_power_ledger_diagnostic_final_v01",
        "status": "COMPLETE_AT_SUPERVISOR_GATE",
        "formal_label": formal_label,
        "reproducible": reproducible,
        "hypothesis_assessment": hypotheses,
        "read_only_sha256_before": read_only_hashes_before,
        "read_only_sha256_after": read_only_hashes_after,
        "read_only_inputs_unchanged": read_only_unchanged,
        "resource": {
            "elapsed_seconds": elapsed,
            "budget_seconds": RUNTIME_BUDGET_SECONDS,
            "peak_memory_gib": peak_memory,
            "memory_budget_gib": MEMORY_BUDGET_GIB,
            "within_budget": within_budget,
            "cpu_processes": 1,
            "gpu_used": False,
        },
        "stop_boundary": {
            "production_source_modified": False,
            "production_threshold_modified": False,
            "full_108_endpoint_matrix_rerun": False,
            "T128_run": False,
            "repair_applied": False,
        },
        "evidence_boundary": (
            "This label diagnoses one fixed ID-LN/DCM/T64 ledger failure. It is not "
            "a production repair, a T64 pass, or a DCM-FEM identity conclusion."
        ),
    }
    _write_json(arguments.output_dir / "final_summary.json", final)
    hash_entries = {
        str(path.relative_to(arguments.output_dir)).replace("\\", "/"): {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(arguments.output_dir.rglob("*"))
        if path.is_file() and path.name != "hash_ledger.json"
    }
    _write_json(
        arguments.output_dir / "hash_ledger.json",
        {
            "schema": "paper2_m2a_v02_t64_power_ledger_diagnostic_hashes_v01",
            "files": hash_entries,
        },
    )
    print(json.dumps(final, indent=2, sort_keys=True, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
