#!/usr/bin/env python3
"""Fixed 15-right-side Bloch-cell check of frozen small-wave predictions."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = Path("results/paper2_cell_bloch_asymptotic_probe/v01_20260905/summary.json")
FROZEN_HEAD = "beacb2c17abb1b6abceb954efa0b8a6a8aab0ae3"
PLAN_SHA256 = "a7ad2d1c6cff174cfa38e1fc5c0667cbb5e241373ba3a50c60c62be0ab0355a0"
BRIEF_SHA256 = "4eabd5d5f3ea264c08a4c839d7c1357d6c3202ffdd20e991dce98c3c24b51883"
V01_PHYSICS_RUNNER_SHA256 = "9a0b9e738624e92559421064f99aae8979ae065dd67d112ad0bb681f85dd9eec"
OLD_V02_JSON_SHA256 = "bfed516d30c234b529a8f0da0dc5c722ec263b20536e99205ad10ba929e91e8f"
SOURCE_PATHS = {
    "project_control/prl_independent_theory_mainline_plan_v04.md": PLAN_SHA256,
    "results/paper2_science_pilot/v01_20260905/science_brief.md": BRIEF_SHA256,
    "scripts/run_paper2_closed_cell_ritz_probe_v01.py": V01_PHYSICS_RUNNER_SHA256,
    "results/paper2_closed_cell_ritz_probe/v02_20260905/summary.json": OLD_V02_JSON_SHA256,
}

A_CELL = 0.5
B_CELL = 0.1
AREA0 = A_CELL * B_CELL
K_AREA = 10.0
K_EDGE = 1.0
KAPPA = 0.1
K_CC = 1.0
K_CE = 1.0
INPUT_AMPLITUDE = 1.0e-5
C1_FROZEN = -0.15569169929705198
C2_FROZEN = -0.01545240115523241
DISPLACEMENT_ABS_FLOOR = 1.0e-12 * B_CELL
OUTPUT_ABS_FLOOR = 1.0e-12
DOF_COUNT = 8
COORDINATES = np.array(
    [[-A_CELL, 0.0], [0.0, 0.0], [0.0, B_CELL], [-A_CELL, B_CELL]],
    dtype=np.float64,
)
WRITER_AUDIT: dict[str, Any] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    git_path = REPO_ROOT / ".git"
    if git_path.is_file():
        marker = git_path.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir: "):
            raise RuntimeError("unrecognized .git file")
        git_path = (REPO_ROOT / marker[8:]).resolve()
    head = (git_path / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    reference = head[5:]
    loose = git_path / reference
    if loose.exists():
        return loose.read_text(encoding="utf-8").strip()
    for line in (git_path / "packed-refs").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "^")):
            commit, name = line.split(" ", 1)
            if name == reference:
                return commit
    raise RuntimeError("HEAD reference was not resolved")


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float rejected")
        return value
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported JSON type: {type(value).__name__}")


def _json_boundary_regression() -> dict[str, Any]:
    finite = {
        "boolean": np.bool_(True),
        "integer": np.int64(3),
        "float": np.float64(0.25),
        "array": np.array([[1.0, 2.0]]),
        "nested": [np.bool_(False), {"x": np.float32(1.5)}],
    }
    converted = _json_ready(finite)
    if json.loads(json.dumps(converted, allow_nan=False)) != converted:
        raise RuntimeError("finite JSON boundary regression failed")

    class Unknown:
        pass

    rejected = {}
    for name, value in {
        "NaN": float("nan"),
        "positive_infinity": float("inf"),
        "negative_infinity": -float("inf"),
        "array_with_NaN": np.array([np.nan]),
        "unknown_type": Unknown(),
        "native_complex": 1.0 + 1.0j,
    }.items():
        try:
            json.dumps(_json_ready(value), allow_nan=False)
        except (TypeError, ValueError):
            rejected[name] = True
        else:
            rejected[name] = False
    if not all(rejected.values()):
        raise RuntimeError("unsafe JSON boundary value was accepted")
    return {
        "finite_numpy_nested_round_trip": True,
        "invalid_or_unknown_rejected_without_string_fallback": rejected,
        "allow_nan": False,
        "model_right_sides": 0,
    }


def _verify_sources() -> dict[str, Any]:
    actual = {relative: _sha256(REPO_ROOT / relative) for relative in SOURCE_PATHS}
    if actual != SOURCE_PATHS:
        raise RuntimeError(f"direct source mismatch: expected={SOURCE_PATHS}, actual={actual}")
    head = _git_head()
    if head != FROZEN_HEAD:
        raise RuntimeError(f"HEAD mismatch: expected={FROZEN_HEAD}, actual={head}")
    return {"frozen_HEAD": head, "sha256": actual, "all_match": True}


def _load_frozen_cell_jacobians() -> dict[str, list[np.ndarray]]:
    sys.dont_write_bytecode = True
    source = REPO_ROOT / "scripts/run_paper2_closed_cell_ritz_probe_v01.py"
    specification = importlib.util.spec_from_file_location("frozen_closed_cell_v01", source)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load frozen cell Jacobian source")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    rows16 = module._cell_jacobians(0)
    rows8 = {
        family: [np.asarray(row[:DOF_COUNT], dtype=np.float64) for row in rows]
        for family, rows in rows16.items()
    }
    return rows8


def _internal_terms(rows: dict[str, list[np.ndarray]]) -> dict[str, np.ndarray]:
    terms = {
        family: np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.complex128)
        for family in ("area", "edge", "angle")
    }
    terms["area"] += (K_AREA / AREA0**2) * np.outer(rows["area"][0], rows["area"][0])
    reference_lengths = (A_CELL, B_CELL, A_CELL, B_CELL)
    for row, reference_length in zip(rows["edge"], reference_lengths):
        terms["edge"] += (K_EDGE / reference_length**2) * np.outer(row, row)
    for row in rows["angle"]:
        terms["angle"] += KAPPA * np.outer(row, row)
    return terms


def _matrix_terms(
    theta: float,
    rows: dict[str, list[np.ndarray]],
    pair_stiffness: float,
) -> tuple[dict[str, np.ndarray], complex]:
    terms = _internal_terms(rows)
    terms["cell_pair"] = np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.complex128)
    terms["basal_attachment"] = np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.complex128)
    phase = np.exp(1.0j * theta)
    for left, right in ((0, 1), (3, 2)):
        for component in range(2):
            jump = np.zeros(DOF_COUNT, dtype=np.complex128)
            jump[2 * right + component] = 1.0
            jump[2 * left + component] = -phase
            terms["cell_pair"] += (pair_stiffness / B_CELL**2) * np.outer(jump.conj(), jump)
    exact_mass = (A_CELL / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])
    factor = K_CE / (A_CELL * B_CELL**2)
    for component in range(2):
        indices = (component, 2 + component)
        terms["basal_attachment"][np.ix_(indices, indices)] += factor * exact_mass
    return terms, phase


def _source(
    theta: float,
    direction: str,
    amplitude_factor: float,
    order: int,
) -> tuple[np.ndarray, float]:
    nodes, weights = np.polynomial.legendre.leggauss(order)
    half = A_CELL / 2.0
    midpoint = -A_CELL / 2.0
    x_values = midpoint + half * nodes
    shape = np.column_stack((-x_values / A_CELL, (x_values + A_CELL) / A_CELL))
    field_scalar = amplitude_factor * INPUT_AMPLITUDE * np.exp(1.0j * (theta / A_CELL) * x_values)
    source = np.zeros(DOF_COUNT, dtype=np.complex128)
    factor = K_CE / (A_CELL * B_CELL**2)
    component = 1 if direction == "N" else 0
    for local, vertex in enumerate((0, 1)):
        source[2 * vertex + component] = factor * np.sum(
            half * weights * shape[:, local] * field_scalar
        )
    constant = 0.5 * factor * np.sum(half * weights * np.abs(field_scalar) ** 2)
    return source, float(constant)


def _complex_scalar(value: complex, phase_floor: float) -> dict[str, Any]:
    number = complex(value)
    magnitude = abs(number)
    return {
        "real": float(number.real),
        "imag": float(number.imag),
        "magnitude": float(magnitude),
        "phase_rad": float(np.angle(number)) if magnitude > phase_floor else None,
        "phase_omitted_when_near_zero": magnitude <= phase_floor,
    }


def _complex_array(value: np.ndarray) -> dict[str, Any]:
    array = np.asarray(value, dtype=np.complex128)
    return {"shape": list(array.shape), "real": array.real.tolist(), "imag": array.imag.tolist()}


def _observables(displacement: np.ndarray, phase: complex) -> dict[str, Any]:
    vertices = displacement.reshape(4, 2)
    lower_jump = vertices[1] - phase * vertices[0]
    upper_jump = vertices[2] - phase * vertices[3]
    output_y = (
        (vertices[2, 1] - vertices[1, 1])
        + phase * (vertices[3, 1] - vertices[0, 1])
    ) / (2.0 * B_CELL)
    gain = B_CELL * output_y / INPUT_AMPLITUDE
    return {
        "all_vertex_displacements": _complex_array(vertices),
        "lower_pair_jump_u1_minus_z_u0": _complex_array(lower_jump),
        "upper_pair_jump_u2_minus_z_u3": _complex_array(upper_jump),
        "Y": _complex_scalar(output_y, OUTPUT_ABS_FLOOR),
        "G_equals_bY_over_A": _complex_scalar(gain, OUTPUT_ABS_FLOOR),
        "right_connection_physical_phase_x_equals_n_a": True,
    }


def _energy(
    displacement: np.ndarray,
    source: np.ndarray,
    constant: float,
    terms: dict[str, np.ndarray],
) -> dict[str, Any]:
    matrix = sum(terms.values(), np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.complex128))
    term_values = {
        name: float(0.5 * np.vdot(displacement, term @ displacement).real)
        for name, term in terms.items()
    }
    u_star_K_u = np.vdot(displacement, matrix @ displacement)
    u_star_f = np.vdot(displacement, source)
    f_star_u = np.vdot(source, displacement)
    return {
        "quadratic_term_energies": term_values,
        "quadratic_energy_total": float(sum(term_values.values())),
        "prescribed_input_constant": constant,
        "u_star_K_u": _complex_scalar(u_star_K_u, 1.0e-30),
        "u_star_f": _complex_scalar(u_star_f, 1.0e-30),
        "f_star_u": _complex_scalar(f_star_u, 1.0e-30),
        "total_potential_real": float(0.5 * u_star_K_u.real - u_star_f.real + constant),
        "spatial_complex_amplitude_energy_not_cycle_dissipation": True,
    }


def _case_specs() -> list[dict[str, Any]]:
    cases = []
    for theta in (0.0, 0.02, 0.04, 0.08):
        for direction in ("N", "T"):
            cases.append({"name": f"theta_{theta:g}_{direction}", "theta": theta, "direction": direction, "amplitude_factor": 1.0, "K_cc": K_CC})
    for direction in ("N", "T"):
        cases.append({"name": f"theta_-0.04_{direction}", "theta": -0.04, "direction": direction, "amplitude_factor": 1.0, "K_cc": K_CC})
    for direction in ("N", "T"):
        cases.append({"name": f"theta_pi_{direction}", "theta": math.pi, "direction": direction, "amplitude_factor": 1.0, "K_cc": K_CC})
    cases.extend(
        [
            {"name": "theta_0.04_half_N", "theta": 0.04, "direction": "N", "amplitude_factor": 0.5, "K_cc": K_CC},
            {"name": "theta_0.04_zero", "theta": 0.04, "direction": "N", "amplitude_factor": 0.0, "K_cc": K_CC},
            {"name": "theta_0.04_Kcc0_N", "theta": 0.04, "direction": "N", "amplitude_factor": 1.0, "K_cc": 0.0},
        ]
    )
    if len(cases) != 15 or len({case["name"] for case in cases}) != 15:
        raise RuntimeError("fixed case ledger is not exactly 15 unique right sides")
    return cases


def _objectivity(rows: dict[str, list[np.ndarray]]) -> dict[str, Any]:
    center = np.mean(COORDINATES, axis=0)
    modes = {}
    for name in ("translation_x", "translation_y", "rotation"):
        mode = np.zeros(DOF_COUNT)
        for vertex, point in enumerate(COORDINATES):
            if name == "translation_x":
                mode[2 * vertex] = 1.0
            elif name == "translation_y":
                mode[2 * vertex + 1] = 1.0
            else:
                relative = point - center
                mode[2 * vertex : 2 * vertex + 2] = [-relative[1], relative[0]]
        actions = {
            family: [float(row @ mode) for row in family_rows]
            for family, family_rows in rows.items()
        }
        modes[name] = {
            "jacobian_actions": actions,
            "maximum_absolute": max(abs(item) for values in actions.values() for item in values),
        }
    return modes


def _safe_write(path: Path, payload: dict[str, Any]) -> None:
    if path.as_posix() != OUTPUT_RELATIVE.as_posix() or path.exists():
        raise RuntimeError("authorized output path is occupied or changed")
    preopen_start = datetime.now(timezone.utc)
    preopen_timer = time.perf_counter()
    payload["runtime"]["output_stage"] = {
        "preopen_full_payload_validation_started_at_utc": preopen_start.isoformat(),
        "allow_nan": False,
        "open_mode": "x",
        "postsave_readback_required": True,
        "write_and_postsave_times_reported_externally_after_immutable_creation": True,
    }
    provisional = _json_ready(payload)
    provisional_text = json.dumps(provisional, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(provisional_text) != provisional:
        raise RuntimeError("preopen full payload round-trip mismatch")
    validation_finish = datetime.now(timezone.utc)
    payload["runtime"]["output_stage"].update(
        {
            "preopen_full_payload_validation_finished_at_utc": validation_finish.isoformat(),
            "preopen_full_payload_validation_elapsed_seconds": time.perf_counter() - preopen_timer,
        }
    )
    final_payload = _json_ready(payload)
    final_text = json.dumps(final_payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if json.loads(final_text) != final_payload:
        raise RuntimeError("final preopen JSON round-trip mismatch")
    final_serialized = datetime.now(timezone.utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_start = datetime.now(timezone.utc)
    write_timer = time.perf_counter()
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(final_text)
        handle.flush()
        os.fsync(handle.fileno())
    write_finish = datetime.now(timezone.utc)
    saved_text = path.read_text(encoding="utf-8")
    if saved_text != final_text or json.loads(saved_text) != final_payload:
        raise RuntimeError("postsave text/JSON readback mismatch")
    verify_finish = datetime.now(timezone.utc)
    WRITER_AUDIT.update(
        {
            "final_serialization_finished_at_utc": final_serialized.isoformat(),
            "write_started_at_utc": write_start.isoformat(),
            "write_finished_at_utc": write_finish.isoformat(),
            "write_only_elapsed_from_timestamps_seconds": (write_finish - write_start).total_seconds(),
            "write_plus_postsave_readback_elapsed_seconds": time.perf_counter() - write_timer,
            "postsave_readback_verified_at_utc": verify_finish.isoformat(),
            "postsave_readback_pass": True,
            "output_bytes": path.stat().st_size,
            "output_sha256": _sha256(path),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_RELATIVE))
    parser.add_argument("--preparation-start-utc", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if output.as_posix() != OUTPUT_RELATIVE.as_posix() or output.exists():
        raise RuntimeError("authorized output path is occupied or changed")
    preparation_start = datetime.fromisoformat(arguments.preparation_start_utc)
    if preparation_start.tzinfo is None:
        raise RuntimeError("preparation start must include a timezone")
    calculation_start = datetime.now(timezone.utc)
    preparation_seconds = (calculation_start - preparation_start.astimezone(timezone.utc)).total_seconds()
    if not (0.0 <= preparation_seconds <= 1800.0):
        raise RuntimeError("preparation time budget failed")
    calculation_timer = time.perf_counter()

    source_verification = _verify_sources()
    json_regression = _json_boundary_regression()
    rows = _load_frozen_cell_jacobians()
    old_v02 = json.loads(
        (REPO_ROOT / "results/paper2_closed_cell_ritz_probe/v02_20260905/summary.json").read_text(encoding="utf-8")
    )
    old_c1_N = np.asarray(old_v02["right_sides_and_solutions"]["full"]["N"]["u"][:8], dtype=np.float64)
    old_c1_T = np.asarray(old_v02["right_sides_and_solutions"]["full"]["T"]["u"][:8], dtype=np.float64)

    case_data: dict[str, dict[str, Any]] = {}
    raw: dict[str, dict[str, Any]] = {}
    all_checks: dict[str, Any] = {}
    for specification in _case_specs():
        name = specification["name"]
        theta = float(specification["theta"])
        terms, phase = _matrix_terms(theta, rows, float(specification["K_cc"]))
        matrix = sum(terms.values(), np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.complex128))
        source16, constant16 = _source(theta, specification["direction"], float(specification["amplitude_factor"]), 16)
        source32, constant32 = _source(theta, specification["direction"], float(specification["amplitude_factor"]), 32)
        solution = np.linalg.solve(matrix, source32)
        residual = matrix @ solution - source32
        source_norm = float(np.linalg.norm(source32))
        quadrature_difference = float(np.linalg.norm(source32 - source16))
        hermitian_error = float(np.linalg.norm(matrix - matrix.conj().T) / np.linalg.norm(matrix))
        cholesky_pass = True
        try:
            np.linalg.cholesky(matrix)
        except np.linalg.LinAlgError:
            cholesky_pass = False
        residual_relative = float(np.linalg.norm(residual) / source_norm) if source_norm > 0.0 else None
        energy_data = _energy(solution, source32, constant32, terms)
        energy_scale = max(
            energy_data["u_star_K_u"]["magnitude"],
            energy_data["u_star_f"]["magnitude"],
            1.0e-30,
        )
        energy_closure = abs(
            complex(energy_data["u_star_K_u"]["real"], energy_data["u_star_K_u"]["imag"])
            - complex(energy_data["u_star_f"]["real"], energy_data["u_star_f"]["imag"])
        ) / energy_scale
        observables = _observables(solution, phase)
        case_checks = {
            "Hermitian_relative_error": hermitian_error,
            "Hermitian_tolerance": 1.0e-12,
            "Cholesky_positive_definite": cholesky_pass,
            "minimum_eigenvalue": float(np.min(np.linalg.eigvalsh(matrix))),
            "residual_absolute_norm": float(np.linalg.norm(residual)),
            "residual_relative_norm": residual_relative,
            "nonzero_residual_tolerance": 1.0e-10,
            "energy_closure_relative": float(energy_closure),
            "energy_closure_tolerance": 1.0e-10,
            "source_16_32_absolute_difference_norm": quadrature_difference,
            "source_16_32_relative_to_whole_source_norm": quadrature_difference / source_norm if source_norm > 0.0 else None,
            "source_relative_tolerance": 1.0e-12,
            "source_near_zero_component_indices": [
                index for index, value in enumerate(source32)
                if source_norm > 0.0 and abs(value) <= 1.0e-13 * source_norm
            ],
            "no_componentwise_relative_error_for_near_zero_source": True,
            "constant_16_32_absolute_difference": abs(constant32 - constant16),
        }
        case_checks["pass"] = (
            hermitian_error <= 1.0e-12
            and cholesky_pass
            and ((residual_relative is not None and residual_relative <= 1.0e-10) or (source_norm == 0.0 and np.max(np.abs(solution)) <= DISPLACEMENT_ABS_FLOOR))
            and energy_closure <= 1.0e-10
            and ((source_norm > 0.0 and quadrature_difference / source_norm <= 1.0e-12) or (source_norm == 0.0 and quadrature_difference == 0.0))
            and abs(constant32 - constant16) <= 1.0e-12 * max(abs(constant32), 1.0e-30)
        )
        case_data[name] = {
            "specification": {
                **specification,
                "k_equals_theta_over_a": theta / A_CELL,
                "z_exp_i_theta": _complex_scalar(phase, 0.0),
                "right_connection_phase_convention": "physical x=n*a",
            },
            "K_8x8": _complex_array(matrix),
            "K_terms_8x8": {term_name: _complex_array(term) for term_name, term in terms.items()},
            "f": _complex_array(source32),
            "u": _complex_array(solution),
            "observables": observables,
            "energy": energy_data,
            "checks": case_checks,
        }
        raw[name] = {"K": matrix, "f": source32, "u": solution, "G": complex(observables["G_equals_bY_over_A"]["real"], observables["G_equals_bY_over_A"]["imag"])}
        all_checks[name] = case_checks["pass"]

    theta0_checks = {}
    for direction, component in (("N", 1), ("T", 0)):
        solution = raw[f"theta_0_{direction}"]["u"].reshape(4, 2)
        target = np.zeros((4, 2), dtype=np.complex128)
        target[:, component] = INPUT_AMPLITUDE
        maximum_error = float(np.max(np.abs(solution - target)))
        gain = raw[f"theta_0_{direction}"]["G"]
        theta0_checks[direction] = {
            "maximum_displacement_error": maximum_error,
            "normalized_by_A": maximum_error / INPUT_AMPLITUDE,
            "G_absolute": abs(gain),
            "pass": maximum_error / INPUT_AMPLITUDE <= 1.0e-10 and abs(gain) <= OUTPUT_ABS_FLOOR,
        }

    plus_N = raw["theta_0.04_N"]
    plus_T = raw["theta_0.04_T"]
    minus_N = raw["theta_-0.04_N"]
    minus_T = raw["theta_-0.04_T"]
    parity_scale_N = max(abs(plus_N["G"]), abs(minus_N["G"]), OUTPUT_ABS_FLOOR)
    parity_scale_T = max(abs(plus_T["G"]), abs(minus_T["G"]), OUTPUT_ABS_FLOOR)
    parity_checks = {
        "G_N_even": {
            "absolute_error": abs(plus_N["G"] - minus_N["G"]),
            "relative_to_whole_G_scale": abs(plus_N["G"] - minus_N["G"]) / parity_scale_N,
            "imaginary_absolute_maximum": max(abs(plus_N["G"].imag), abs(minus_N["G"].imag)),
        },
        "G_T_odd": {
            "absolute_error": abs(plus_T["G"] + minus_T["G"]),
            "relative_to_whole_G_scale": abs(plus_T["G"] + minus_T["G"]) / parity_scale_T,
            "real_absolute_maximum": max(abs(plus_T["G"].real), abs(minus_T["G"].real)),
        },
        "relative_tolerance": 1.0e-10,
        "absolute_floor": OUTPUT_ABS_FLOOR,
    }
    parity_checks["pass"] = (
        parity_checks["G_N_even"]["relative_to_whole_G_scale"] <= 1.0e-10
        and parity_checks["G_T_odd"]["relative_to_whole_G_scale"] <= 1.0e-10
        and parity_checks["G_N_even"]["imaginary_absolute_maximum"] <= max(1.0e-10 * parity_scale_N, OUTPUT_ABS_FLOOR)
        and parity_checks["G_T_odd"]["real_absolute_maximum"] <= max(1.0e-10 * parity_scale_T, OUTPUT_ABS_FLOOR)
    )

    half_u_error = float(np.max(np.abs(raw["theta_0.04_half_N"]["u"] - 0.5 * plus_N["u"])))
    half_f_error = float(np.max(np.abs(raw["theta_0.04_half_N"]["f"] - 0.5 * plus_N["f"])))
    energy_full = case_data["theta_0.04_N"]["energy"]["quadratic_energy_total"]
    energy_half = case_data["theta_0.04_half_N"]["energy"]["quadratic_energy_total"]
    half_energy_error = abs(energy_half - 0.25 * energy_full) / max(abs(0.25 * energy_full), 1.0e-30)
    scaling_checks = {
        "half_N_displacement_absolute_error": half_u_error,
        "half_N_displacement_normalized_by_A": half_u_error / INPUT_AMPLITUDE,
        "half_N_source_absolute_error": half_f_error,
        "half_N_quadratic_energy_quarter_relative_error": half_energy_error,
        "zero_input_maximum_absolute_displacement": float(np.max(np.abs(raw["theta_0.04_zero"]["u"]))),
        "relative_tolerance": 1.0e-10,
        "near_zero_displacement_absolute_floor": DISPLACEMENT_ABS_FLOOR,
    }
    scaling_checks["pass"] = (
        half_u_error / INPUT_AMPLITUDE <= 1.0e-10
        and half_f_error <= 1.0e-10 * max(np.max(np.abs(plus_N["f"])), 1.0e-30)
        and half_energy_error <= 1.0e-10
        and scaling_checks["zero_input_maximum_absolute_displacement"] <= DISPLACEMENT_ABS_FLOOR
    )

    pi_N_error = float(np.max(np.abs(raw["theta_pi_N"]["u"].real - old_c1_N)))
    pi_T_error = float(np.max(np.abs(raw["theta_pi_T"]["u"].imag - old_c1_T)))
    old_special_case = {
        "N_real_part_maximum_absolute_displacement_error": pi_N_error,
        "T_imaginary_part_maximum_absolute_displacement_error": pi_T_error,
        "N_error_normalized_by_A": pi_N_error / INPUT_AMPLITUDE,
        "T_error_normalized_by_A": pi_T_error / INPUT_AMPLITUDE,
        "tolerance": 1.0e-10,
        "old_16DOF_model_not_rerun": True,
        "pass": pi_N_error / INPUT_AMPLITUDE <= 1.0e-10 and pi_T_error / INPUT_AMPLITUDE <= 1.0e-10,
    }

    kcc0_gain = raw["theta_0.04_Kcc0_N"]["G"]
    kcc0_check = {
        "G": _complex_scalar(kcc0_gain, OUTPUT_ABS_FLOOR),
        "absolute_magnitude": abs(kcc0_gain),
        "absolute_tolerance": 1.0e-10,
        "relative_error_not_computed": True,
        "Kcc0_is_mathematical_limit_not_physiology": True,
        "pass": abs(kcc0_gain) <= 1.0e-10,
    }

    asymptotic = {}
    for theta in (0.02, 0.04, 0.08):
        gain_T = raw[f"theta_{theta:g}_T"]["G"]
        gain_N = raw[f"theta_{theta:g}_N"]["G"]
        estimate_T = gain_T / (1.0j * theta)
        estimate_N = gain_N / theta**2
        asymptotic[f"theta_{theta:g}"] = {
            "G_T": _complex_scalar(gain_T, OUTPUT_ABS_FLOOR),
            "G_N": _complex_scalar(gain_N, OUTPUT_ABS_FLOOR),
            "c1_estimate_G_T_over_i_theta": _complex_scalar(estimate_T, OUTPUT_ABS_FLOOR),
            "c2_estimate_G_N_over_theta_squared": _complex_scalar(estimate_N, OUTPUT_ABS_FLOOR),
            "c1_absolute_difference": abs(estimate_T - C1_FROZEN),
            "c1_relative_difference": abs(estimate_T - C1_FROZEN) / abs(C1_FROZEN),
            "c2_absolute_difference": abs(estimate_N - C2_FROZEN),
            "c2_relative_difference": abs(estimate_N - C2_FROZEN) / abs(C2_FROZEN),
            "coefficients_are_frozen_predictions_not_fits": True,
        }
    exploratory = {
        "theta": 0.02,
        "relative_threshold": 0.05,
        "c1_relative_difference": asymptotic["theta_0.02"]["c1_relative_difference"],
        "c2_relative_difference": asymptotic["theta_0.02"]["c2_relative_difference"],
        "near_zero_G_disables_relative_gate": False,
    }
    exploratory["pass"] = (
        exploratory["c1_relative_difference"] <= 0.05
        and exploratory["c2_relative_difference"] <= 0.05
    )
    approach = {
        "c1_error_decreases_as_theta_0.08_to_0.04_to_0.02": (
            asymptotic["theta_0.02"]["c1_relative_difference"]
            <= asymptotic["theta_0.04"]["c1_relative_difference"]
            <= asymptotic["theta_0.08"]["c1_relative_difference"]
        ),
        "c2_error_decreases_as_theta_0.08_to_0.04_to_0.02": (
            asymptotic["theta_0.02"]["c2_relative_difference"]
            <= asymptotic["theta_0.04"]["c2_relative_difference"]
            <= asymptotic["theta_0.08"]["c2_relative_difference"]
        ),
        "three_points_are_not_a_continuous_spectrum_or_formal_convergence_study": True,
    }

    objectivity = _objectivity(rows)
    objectivity_maximum = max(item["maximum_absolute"] for item in objectivity.values())
    objectivity_check = {
        "per_rigid_mode": objectivity,
        "maximum_absolute_jacobian_action": objectivity_maximum,
        "tolerance": 1.0e-12,
        "pass": objectivity_maximum <= 1.0e-12,
    }
    calculation_finish = datetime.now(timezone.utc)
    calculation_seconds = time.perf_counter() - calculation_timer
    overall_pass = (
        all(all_checks.values())
        and all(record["pass"] for record in theta0_checks.values())
        and parity_checks["pass"]
        and scaling_checks["pass"]
        and old_special_case["pass"]
        and kcc0_check["pass"]
        and exploratory["pass"]
        and objectivity_check["pass"]
        and calculation_seconds <= 30.0
    )
    payload = {
        "schema": "paper2_cell_bloch_asymptotic_probe_v01",
        "status": "COMPLETED_BOUNDED_BLOCH_ASYMPTOTIC_PROBE" if overall_pass else "ABORTED_FAIL_CLOSED_CHECK_OR_BUDGET",
        "scientific_question": "Does the fixed 8-DOF complex Bloch cell reproduce the frozen small-theta coefficients and the old theta=pi two-cell special case?",
        "claim_boundary": {
            "ideal_dimensionless_linear_single_cell_problem": True,
            "not_a_v02_rerun_or_new_platform": True,
            "not_physiological_calibration_or_Kcc0_physiology": True,
            "not_DCM_necessity_or_Nature_Physics_mechanism_evidence": True,
            "not_ECM_FEM_fluid_nonlinear_3D_or_biological_feedback": True,
            "fifteen_points_include_controls_not_a_spectrum_scan": True,
            "five_percent_is_exploratory_implementation_acceptance_not_innovation_gate": True,
            "scientific_acceptance_pending_supervisor_independent_review": True,
        },
        "preregistration": {
            "frozen_HEAD": FROZEN_HEAD,
            "main_plan_section_35_sha256": PLAN_SHA256,
            "science_brief_section_59_sha256": BRIEF_SHA256,
            "frozen_c1": C1_FROZEN,
            "frozen_c2": C2_FROZEN,
            "no_coefficient_fit": True,
        },
        "direct_source_verification": source_verification,
        "json_boundary_regression": json_regression,
        "fixed_model": {
            "cell_domain": "[-a,0] x [0,b]",
            "a": A_CELL,
            "b": B_CELL,
            "A": INPUT_AMPLITUDE,
            "vertices_counterclockwise": COORDINATES.tolist(),
            "dof_order": "[u0x,u0y,u1x,u1y,u2x,u2y,u3x,u3y]",
            "parameters": {"K_A": K_AREA, "K_l": K_EDGE, "kappa": KAPPA, "K_cc": K_CC, "K_ce": K_CE},
            "Bloch_phase": "z=exp(i*theta), k=theta/a",
            "pair_jumps_counted_once": ["u1-z*u0", "u2-z*u3"],
            "basal_input": "U_E=A*exp(i*k*x)*e_x or e_y",
            "exact_P1_mass_each_base": ((A_CELL / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])).tolist(),
            "source_integration": "32-point Gauss-Legendre with whole-source 16/32 check",
            "output": "Y=[(u2y-u1y)+z*(u3y-u0y)]/(2b), G=bY/A",
            "right_connection_physical_phase": "x=n*a",
        },
        "case_count": 15,
        "cases": case_data,
        "aggregate_checks": {
            "all_case_structure_residual_energy_and_source": {"per_case_pass": all_checks, "pass": all(all_checks.values())},
            "theta_zero_uniform_translation_and_zero_G": {"per_direction": theta0_checks, "pass": all(record["pass"] for record in theta0_checks.values())},
            "G_parity_and_real_imaginary_structure": parity_checks,
            "half_amplitude_zero_and_quarter_energy": scaling_checks,
            "theta_pi_old_v02_special_case": old_special_case,
            "Kcc_zero_normal_boundary": kcc0_check,
            "bare_cell_internal_objectivity": objectivity_check,
            "theta_0.02_exploratory_five_percent": exploratory,
            "all_pass": overall_pass,
        },
        "asymptotic_comparison": {
            "predictions": {
                "G_T": "i*c1*theta + O(theta^3)",
                "G_N": "c2*theta^2 + O(theta^4)",
                "c1": C1_FROZEN,
                "c2": C2_FROZEN,
            },
            "positive_small_theta": asymptotic,
            "approach_as_theta_decreases": approach,
            "not_fitted_and_not_a_formal_error_order_claim": True,
        },
        "runtime": {
            "preparation_started_at_utc": preparation_start.astimezone(timezone.utc).isoformat(),
            "calculation_started_at_utc": calculation_start.isoformat(),
            "calculation_finished_at_utc": calculation_finish.isoformat(),
            "preparation_elapsed_seconds": preparation_seconds,
            "preparation_budget_seconds": 1800.0,
            "calculation_elapsed_seconds": calculation_seconds,
            "calculation_budget_seconds": 30.0,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "python_executable": sys.executable,
            "entry_path": "scripts/run_paper2_cell_bloch_asymptotic_probe_v01.py",
            "entry_sha256": _sha256(Path(__file__)),
            "cpu_threads": 1,
            "memory_limit_gib": 8,
            "bytecode_cache": "disabled",
            "gpu": "not_used",
            "network": "not_used",
            "container": "not_used",
            "FEM_ECM_old_cases_and_holdouts": "not_run_or_read",
        },
        "compute_ledger": {
            "existing_conservative_reserved_seconds_including_old_failed_preparation": 516.89440824,
            "existing_periodic_cases": 46,
            "existing_static_FEM_right_sides": 30,
            "old_cell_v01_failed_attempted_right_sides": 6,
            "old_cell_v02_accepted_right_sides": 6,
            "new_complex_cell_right_sides": 15,
            "new_calculation_seconds_recorded_separately": calculation_seconds,
            "project_stop_reestimate_seconds": 7200.0,
        },
        "next_gate": "SUPERVISOR_INDEPENDENT_RECOMPUTATION_STOP",
    }
    _safe_write(output, payload)
    print(
        f"CELL_BLOCH_DONE status={payload['status']} prep={preparation_seconds:.3f}s "
        f"calculation={calculation_seconds:.6f}s"
    )
    print("POSTSAVE_AUDIT " + json.dumps(WRITER_AUDIT, sort_keys=True, allow_nan=False))
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
