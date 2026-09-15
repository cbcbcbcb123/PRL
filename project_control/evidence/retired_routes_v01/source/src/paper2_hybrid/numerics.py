"""Direct-solve assurance and exact discrete power bookkeeping."""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np
import scipy.sparse.linalg as sparse_linalg

from .config import ACTIVE_CONFIG
from .model import (
    Endpoint,
    _case_components,
    _material_energy,
    simulate_endpoint as solve_base_endpoint,
)
from .protocol import ACTIVE_PROTOCOL


def discrete_material_energy_increment(
    system: Any,
    state_start: np.ndarray,
    state_end: np.ndarray,
    activation_start: float,
    activation_end: float,
) -> float:
    """Exact increment for the frozen quadratic-bilinear material energy."""
    increment = state_end - state_start
    midpoint = 0.5 * (state_start + state_end)
    activation_midpoint = 0.5 * (activation_start + activation_end)
    activation_increment = activation_end - activation_start
    state_conjugate = (
        system.matrix_material @ midpoint
        + system.active_vector_h * activation_midpoint
    )
    activation_conjugate = (
        np.dot(system.active_vector_h, midpoint)
        + system.active_scalar_c * activation_midpoint
    )
    return float(
        np.dot(state_conjugate, increment)
        + activation_conjugate * activation_increment
    )


def _loads_for_endpoint(
    system: Any,
    case_id: str,
    steps_per_cycle: int,
    state_shape: tuple[int, int],
) -> np.ndarray:
    if case_id in {"P0", "P1"}:
        return np.zeros(state_shape, dtype=np.float64)
    active_dc, active_harmonic, load_dc, load_harmonic, profile = _case_components(
        case_id, system
    )
    del active_dc, active_harmonic
    if profile != system.active_profile:
        raise RuntimeError("active profile/system mismatch")
    times = np.linspace(
        0.0, 2.0 * system.config.period, 2 * steps_per_cycle + 1
    )
    phase = np.exp(1j * 2.0 * math.pi * times / system.config.period)
    return load_dc[:, None] + np.real(load_harmonic[:, None] * phase[None, :])


def _normwise_backward_error(matrix: Any, solution: np.ndarray, rhs: np.ndarray) -> float:
    residual = matrix @ solution - rhs
    numerator = float(np.linalg.norm(residual, ord=np.inf))
    row_sums = np.asarray(np.abs(matrix).sum(axis=1)).ravel()
    matrix_norm = float(np.max(row_sums)) if row_sums.size else 0.0
    denominator = (
        matrix_norm * float(np.linalg.norm(solution, ord=np.inf))
        + float(np.linalg.norm(rhs, ord=np.inf))
    )
    return numerator / max(denominator, 1.0e-30)


def _relative_residual(matrix: Any, solution: np.ndarray, rhs: np.ndarray) -> float:
    residual = matrix @ solution - rhs
    return float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1.0e-30))


def direct_solver_assurance(
    system: Any,
    case_id: str,
    steps_per_cycle: int,
) -> dict[str, Any]:
    """Audit the same SuperLU direct systems without residual correction."""
    protocol = ACTIVE_PROTOCOL
    if case_id in {"P0", "P1"}:
        dc_relative = 0.0
        harmonic_relative = 0.0
        dc_backward = 0.0
        harmonic_backward = 0.0
    else:
        active_dc, active_harmonic, load_dc, load_harmonic, profile = (
            _case_components(case_id, system)
        )
        if profile != system.active_profile:
            raise RuntimeError("active profile/system mismatch")
        rhs_dc = load_dc - system.active_vector_h * active_dc
        rhs_harmonic = load_harmonic - system.active_vector_h * active_harmonic
        time_step = system.config.period / steps_per_cycle
        omega = 2.0 * math.pi / system.config.period
        zeta = np.exp(1j * omega * time_step)
        harmonic_matrix = (
            ((zeta - 1.0) / time_step) * system.matrix_g
            + 0.5 * (zeta + 1.0) * system.matrix_a
        ).tocsc()
        harmonic_rhs = 0.5 * (1.0 + zeta) * rhs_harmonic
        matrix_dc = system.matrix_a.tocsc()
        dc_state = sparse_linalg.spsolve(matrix_dc, rhs_dc)
        harmonic_state = sparse_linalg.spsolve(harmonic_matrix, harmonic_rhs)
        dc_relative = _relative_residual(matrix_dc, dc_state, rhs_dc)
        harmonic_relative = _relative_residual(
            harmonic_matrix, harmonic_state, harmonic_rhs
        )
        dc_backward = _normwise_backward_error(matrix_dc, dc_state, rhs_dc)
        harmonic_backward = _normwise_backward_error(
            harmonic_matrix, harmonic_state, harmonic_rhs
        )
    maximum_relative = max(dc_relative, harmonic_relative)
    maximum_backward = max(dc_backward, harmonic_backward)
    return {
        "name": "scipy_superlu_direct",
        "solver_level": "D0",
        "residual_correction_steps": 0,
        "dc_relative_residual": dc_relative,
        "harmonic_relative_residual": harmonic_relative,
        "maximum_relative_residual": maximum_relative,
        "relative_residual_tolerance": protocol.direct_relative_residual_tolerance,
        "relative_residual_pass": bool(
            maximum_relative <= protocol.direct_relative_residual_tolerance
        ),
        "dc_normwise_backward_error": dc_backward,
        "harmonic_normwise_backward_error": harmonic_backward,
        "maximum_normwise_backward_error": maximum_backward,
        "normwise_backward_error_tolerance": protocol.direct_backward_error_tolerance,
        "normwise_backward_error_pass": bool(
            maximum_backward <= protocol.direct_backward_error_tolerance
        ),
        "pass": bool(
            maximum_relative <= protocol.direct_relative_residual_tolerance
            and maximum_backward <= protocol.direct_backward_error_tolerance
        ),
    }


def discrete_ledger(
    system: Any,
    states: np.ndarray,
    activation: np.ndarray,
    loads: np.ndarray,
    steps_per_cycle: int,
) -> dict[str, Any]:
    """Evaluate the frozen power identity with the exact discrete increment."""
    time_step = system.config.period / steps_per_cycle
    energy = np.asarray(
        [
            _material_energy(system, states[:, index], activation[index])
            for index in range(steps_per_cycle + 1)
        ],
        dtype=np.float64,
    )
    terms = {
        name: np.zeros(steps_per_cycle, dtype=np.float64)
        for name in (
            "active_work_steps",
            "lumen_work_steps",
            "external_support_work_steps",
            "drag_dissipation_steps",
            "sls_dissipation_steps",
            "discrete_energy_change_steps",
            "endpoint_energy_change_steps",
            "endpoint_subtraction_gap_steps",
            "residual_steps",
            "normalization_scale_steps",
            "normalized_residual_steps",
            "equilibrium_defect_work_steps",
            "ledger_minus_equilibrium_work_steps",
            "ledger_minus_equilibrium_work_relative_steps",
        )
    }
    for step in range(steps_per_cycle):
        state_start = states[:, step]
        state_end = states[:, step + 1]
        increment = state_end - state_start
        midpoint = 0.5 * (state_start + state_end)
        activation_midpoint = 0.5 * (activation[step] + activation[step + 1])
        activation_increment = activation[step + 1] - activation[step]
        load_midpoint = 0.5 * (loads[:, step] + loads[:, step + 1])
        active_conjugate = (
            np.dot(system.active_vector_h, midpoint)
            + system.active_scalar_c * activation_midpoint
        )
        active_work = active_conjugate * activation_increment
        lumen_work = np.dot(load_midpoint, increment)
        support_work = -np.dot(system.matrix_support @ midpoint, increment)
        drag_dissipation = (
            increment @ (system.matrix_drag @ increment) / time_step
        )
        sls_dissipation = (
            increment @ (system.matrix_sls_dissipation @ increment) / time_step
        )
        discrete_energy_change = discrete_material_energy_increment(
            system,
            state_start,
            state_end,
            float(activation[step]),
            float(activation[step + 1]),
        )
        endpoint_energy_change = energy[step + 1] - energy[step]
        residual = (
            active_work
            + lumen_work
            + support_work
            - discrete_energy_change
            - drag_dissipation
            - sls_dissipation
        )
        scale = max(
            abs(active_work)
            + abs(lumen_work)
            + abs(support_work)
            + abs(discrete_energy_change)
            + abs(drag_dissipation)
            + abs(sls_dissipation),
            1.0e-14,
        )
        rhs_midpoint = load_midpoint - system.active_vector_h * activation_midpoint
        equilibrium_defect = (
            rhs_midpoint
            - system.matrix_a @ midpoint
            - system.matrix_g @ increment / time_step
        )
        equilibrium_work = np.dot(equilibrium_defect, increment)
        closure_difference = residual - equilibrium_work

        terms["active_work_steps"][step] = active_work
        terms["lumen_work_steps"][step] = lumen_work
        terms["external_support_work_steps"][step] = support_work
        terms["drag_dissipation_steps"][step] = drag_dissipation
        terms["sls_dissipation_steps"][step] = sls_dissipation
        terms["discrete_energy_change_steps"][step] = discrete_energy_change
        terms["endpoint_energy_change_steps"][step] = endpoint_energy_change
        terms["endpoint_subtraction_gap_steps"][step] = (
            endpoint_energy_change - discrete_energy_change
        )
        terms["residual_steps"][step] = residual
        terms["normalization_scale_steps"][step] = scale
        terms["normalized_residual_steps"][step] = abs(residual) / scale
        terms["equilibrium_defect_work_steps"][step] = equilibrium_work
        terms["ledger_minus_equilibrium_work_steps"][step] = closure_difference
        terms["ledger_minus_equilibrium_work_relative_steps"][step] = (
            abs(closure_difference) / scale
        )

    all_arrays = [energy, *terms.values()]
    return {
        "energy": energy,
        **terms,
        "total_active_work": float(np.sum(terms["active_work_steps"])),
        "total_lumen_work": float(np.sum(terms["lumen_work_steps"])),
        "total_external_support_work": float(
            np.sum(terms["external_support_work_steps"])
        ),
        "total_drag_dissipation": float(
            np.sum(terms["drag_dissipation_steps"])
        ),
        "total_sls_dissipation": float(
            np.sum(terms["sls_dissipation_steps"])
        ),
        "cycle_discrete_energy_change": float(
            np.sum(terms["discrete_energy_change_steps"])
        ),
        "cycle_endpoint_energy_change": float(energy[-1] - energy[0]),
        "cycle_energy_change": float(
            np.sum(terms["discrete_energy_change_steps"])
        ),
        "maximum_absolute_endpoint_subtraction_gap": float(
            np.max(np.abs(terms["endpoint_subtraction_gap_steps"]))
        ),
        "maximum_normalized_residual": float(
            np.max(terms["normalized_residual_steps"])
        ),
        "maximum_ledger_minus_equilibrium_work_relative": float(
            np.max(terms["ledger_minus_equilibrium_work_relative_steps"])
        ),
        "minimum_physical_dissipation": float(
            min(
                np.min(terms["drag_dissipation_steps"]),
                np.min(terms["sls_dissipation_steps"]),
            )
        ),
        "all_arrays_finite": bool(
            all(np.all(np.isfinite(values)) for values in all_arrays)
        ),
    }


def _ledger_summary(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if not isinstance(value, np.ndarray)
    }


def finalize_endpoint(
    *,
    system: Any,
    case_id: str,
    steps_per_cycle: int,
    base_endpoint: Endpoint,
) -> Endpoint:
    """Apply exact discrete power bookkeeping without changing physical arrays."""
    states = base_endpoint.arrays["state_two_cycles"]
    activation = base_endpoint.arrays["activation_two_cycles"]
    loads = _loads_for_endpoint(system, case_id, steps_per_cycle, states.shape)
    first_cycle = slice(0, steps_per_cycle + 1)
    repaired_ledger = discrete_ledger(
        system,
        states[:, first_cycle],
        activation[first_cycle],
        loads[:, first_cycle],
        steps_per_cycle,
    )

    summary = copy.deepcopy(base_endpoint.summary)
    legacy_ledger_summary = copy.deepcopy(summary["ledger"])
    summary.pop("tolerance_label", None)
    summary["solver_level"] = "D0"
    summary["solver"] = direct_solver_assurance(system, case_id, steps_per_cycle)
    summary["base_endpoint_subtraction_ledger"] = legacy_ledger_summary
    summary["ledger"] = _ledger_summary(repaired_ledger)
    summary["ledger"]["energy_increment"] = "exact_midpoint_quadratic_bilinear"
    summary["ledger"]["endpoint_energy_role"] = "audit_sidecar_only"

    arrays = dict(base_endpoint.arrays)
    arrays["ledger_energy"] = repaired_ledger["energy"]
    for key in (
        "active_work_steps",
        "lumen_work_steps",
        "external_support_work_steps",
        "drag_dissipation_steps",
        "sls_dissipation_steps",
        "residual_steps",
        "normalized_residual_steps",
    ):
        arrays[f"ledger_{key}"] = repaired_ledger[key]
    for key in (
        "discrete_energy_change_steps",
        "endpoint_energy_change_steps",
        "endpoint_subtraction_gap_steps",
        "normalization_scale_steps",
        "equilibrium_defect_work_steps",
        "ledger_minus_equilibrium_work_steps",
        "ledger_minus_equilibrium_work_relative_steps",
    ):
        arrays[f"ledger_{key}"] = repaired_ledger[key]
    return Endpoint(summary=summary, arrays=arrays)


def simulate_endpoint(
    *,
    system: Any,
    case_id: str,
    steps_per_cycle: int,
) -> Endpoint:
    base_endpoint = solve_base_endpoint(
        system=system,
        case_id=case_id,
        steps_per_cycle=steps_per_cycle,
    )
    return finalize_endpoint(
        system=system,
        case_id=case_id,
        steps_per_cycle=steps_per_cycle,
        base_endpoint=base_endpoint,
    )


def endpoint_structural_gate(summary: dict[str, Any]) -> dict[str, Any]:
    config = ACTIVE_CONFIG
    protocol = ACTIVE_PROTOCOL
    checks = {
        "direct_relative_residual": {
            "value": summary["solver"]["maximum_relative_residual"],
            "threshold": protocol.direct_relative_residual_tolerance,
            "pass": summary["solver"]["relative_residual_pass"],
        },
        "direct_normwise_backward_error": {
            "value": summary["solver"]["maximum_normwise_backward_error"],
            "threshold": protocol.direct_backward_error_tolerance,
            "pass": summary["solver"]["normwise_backward_error_pass"],
        },
        "interface_action_reaction": {
            "value": summary["interface_action_reaction_relative_error"],
            "threshold": config.action_reaction_relative_tolerance,
            "pass": summary["interface_action_reaction_relative_error"]
            <= config.action_reaction_relative_tolerance,
        },
        "power_ledger": {
            "value": summary["ledger"]["maximum_normalized_residual"],
            "threshold": config.power_ledger_relative_tolerance,
            "pass": summary["ledger"]["maximum_normalized_residual"]
            <= config.power_ledger_relative_tolerance,
        },
        "discrete_ledger_closure": {
            "value": summary["ledger"][
                "maximum_ledger_minus_equilibrium_work_relative"
            ],
            "threshold": protocol.discrete_ledger_closure_tolerance,
            "pass": summary["ledger"][
                "maximum_ledger_minus_equilibrium_work_relative"
            ]
            <= protocol.discrete_ledger_closure_tolerance,
        },
        "finite_ledger": {
            "value": summary["ledger"]["all_arrays_finite"],
            "threshold": True,
            "pass": summary["ledger"]["all_arrays_finite"],
        },
        "nonnegative_dissipation": {
            "value": summary["ledger"]["minimum_physical_dissipation"],
            "threshold": config.dissipation_lower_tolerance,
            "pass": summary["ledger"]["minimum_physical_dissipation"]
            >= config.dissipation_lower_tolerance,
        },
        "cycle_state": {
            "value": summary["cycle_state_relative_difference"],
            "threshold": config.cycle_state_relative_tolerance,
            "pass": summary["cycle_state_relative_difference"]
            <= config.cycle_state_relative_tolerance,
        },
    }
    if summary["case_id"] == "P0":
        checks["zero_state"] = {
            "value": summary["maximum_state_norm"],
            "threshold": config.zero_state_absolute_tolerance,
            "pass": summary["maximum_state_norm"] <= config.zero_state_absolute_tolerance,
        }
    if summary["case_id"] == "P1":
        checks["uniform_strain_manufactured_solution"] = {
            "value": summary["manufactured_uniform_strain_relative_error"],
            "threshold": config.manufactured_solution_relative_tolerance,
            "pass": summary["manufactured_uniform_strain_relative_error"]
            <= config.manufactured_solution_relative_tolerance,
        }
    return {"pass": all(check["pass"] for check in checks.values()), "checks": checks}
