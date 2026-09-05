#!/usr/bin/env python3
"""Bounded linear closed-cell versus two-coordinate Ritz probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


FROZEN_COMMIT = "7d4166f48d8261b69be76dfc2217df39b01ef497"
EXPECTED_OUTPUT = Path("results/paper2_closed_cell_ritz_probe/v01_20260905/summary.json")
PLAN_SHA256 = "e9dfd0da0960b0b46e91edf66ed94626d449ee64db85691fbe2f24bfbea68cc9"
BRIEF_SHA256 = "35ecad1fa8939a0b258b45e1a4fef95bb39cfe1cb3a4576c5595987e1df38ae4"
LENGTH = 1.0
CELL_WIDTH = 0.5
CELL_HEIGHT = 0.1
AREA0 = CELL_WIDTH * CELL_HEIGHT
K_AREA = 10.0
K_EDGE = 1.0
K_ANGLE = 0.1
K_CC = 1.0
K_CE = 1.0
EPSILON = 1.0e-4
AMPLITUDE = EPSILON * CELL_HEIGHT
DOF_COUNT = 16
ABS_DISPLACEMENT_SCALE = 1.0e-12 * CELL_HEIGHT

COORDINATES = np.array(
    [
        [[-0.5, 0.0], [0.0, 0.0], [0.0, 0.1], [-0.5, 0.1]],
        [[0.0, 0.0], [0.5, 0.0], [0.5, 0.1], [0.0, 0.1]],
    ],
    dtype=np.float64,
)
PAIRING = (
    ("internal_lower", 1, 4),
    ("internal_upper", 2, 7),
    ("periodic_outer_lower", 0, 5),
    ("periodic_outer_upper", 3, 6),
)
BOTTOM_EDGES = ((0, 1, -0.5, 0.0), (4, 5, 0.0, 0.5))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _global_vertex(cell: int, local_vertex: int) -> int:
    return 4 * cell + local_vertex


def _row() -> np.ndarray:
    return np.zeros(DOF_COUNT, dtype=np.float64)


def _put(row: np.ndarray, vertex: int, value: np.ndarray) -> None:
    row[2 * vertex : 2 * vertex + 2] += value


def _cell_jacobians(cell: int) -> dict[str, list[np.ndarray]]:
    points = COORDINATES[cell]
    area_row = _row()
    for index in range(4):
        previous = points[(index - 1) % 4]
        following = points[(index + 1) % 4]
        gradient = 0.5 * np.array(
            [following[1] - previous[1], previous[0] - following[0]]
        )
        _put(area_row, _global_vertex(cell, index), gradient)

    edge_rows: list[np.ndarray] = []
    angle_rows: list[np.ndarray] = []
    for index in range(4):
        following_index = (index + 1) % 4
        edge = points[following_index] - points[index]
        unit = edge / np.linalg.norm(edge)
        edge_row = _row()
        _put(edge_row, _global_vertex(cell, index), -unit)
        _put(edge_row, _global_vertex(cell, following_index), unit)
        edge_rows.append(edge_row)

        previous_index = (index - 1) % 4
        incoming = points[index] - points[previous_index]
        outgoing = points[following_index] - points[index]
        incoming_rotation = np.array([-incoming[1], incoming[0]]) / np.dot(
            incoming, incoming
        )
        outgoing_rotation = np.array([-outgoing[1], outgoing[0]]) / np.dot(
            outgoing, outgoing
        )
        angle_row = _row()
        _put(
            angle_row,
            _global_vertex(cell, previous_index),
            -incoming_rotation,
        )
        _put(
            angle_row,
            _global_vertex(cell, index),
            incoming_rotation + outgoing_rotation,
        )
        _put(
            angle_row,
            _global_vertex(cell, following_index),
            -outgoing_rotation,
        )
        angle_rows.append(angle_row)
    return {"area": [area_row], "edge": edge_rows, "angle": angle_rows}


def _assemble() -> tuple[dict[str, np.ndarray], dict[int, dict[str, list[np.ndarray]]]]:
    terms = {
        name: np.zeros((DOF_COUNT, DOF_COUNT), dtype=np.float64)
        for name in ("area", "edge", "angle", "cell_pair", "basal_attachment")
    }
    cell_rows: dict[int, dict[str, list[np.ndarray]]] = {}
    for cell in range(2):
        rows = _cell_jacobians(cell)
        cell_rows[cell] = rows
        terms["area"] += (K_AREA / AREA0**2) * np.outer(rows["area"][0], rows["area"][0])
        reference_lengths = (CELL_WIDTH, CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
        for edge_row, reference_length in zip(rows["edge"], reference_lengths):
            terms["edge"] += (K_EDGE / reference_length**2) * np.outer(edge_row, edge_row)
        for angle_row in rows["angle"]:
            terms["angle"] += K_ANGLE * np.outer(angle_row, angle_row)

    for _, first, second in PAIRING:
        for component in range(2):
            pair_row = _row()
            pair_row[2 * first + component] = 1.0
            pair_row[2 * second + component] = -1.0
            terms["cell_pair"] += (K_CC / CELL_HEIGHT**2) * np.outer(pair_row, pair_row)

    exact_mass = (CELL_WIDTH / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])
    foundation_factor = K_CE / (CELL_WIDTH * CELL_HEIGHT**2)
    for first, second, _, _ in BOTTOM_EDGES:
        for component in range(2):
            indices = (2 * first + component, 2 * second + component)
            terms["basal_attachment"][np.ix_(indices, indices)] += foundation_factor * exact_mass
    return terms, cell_rows


def _input_field(kind: str, x_values: np.ndarray) -> np.ndarray:
    field = np.zeros((len(x_values), 2), dtype=np.float64)
    if kind in {"N", "N_plus_T", "half_N"}:
        factor = 0.5 if kind == "half_N" else 1.0
        field[:, 1] += factor * AMPLITUDE * np.cos(2.0 * np.pi * x_values / LENGTH)
    if kind in {"T", "N_plus_T"}:
        field[:, 0] += AMPLITUDE * np.sin(2.0 * np.pi * x_values / LENGTH)
    return field


def _source(kind: str, order: int) -> tuple[np.ndarray, float]:
    nodes, weights = np.polynomial.legendre.leggauss(order)
    source = np.zeros(DOF_COUNT, dtype=np.float64)
    constant = 0.0
    factor = K_CE / (CELL_WIDTH * CELL_HEIGHT**2)
    for first, second, left, right in BOTTOM_EDGES:
        half_length = 0.5 * (right - left)
        midpoint = 0.5 * (right + left)
        x_values = midpoint + half_length * nodes
        shape = np.column_stack(((right - x_values) / (right - left), (x_values - left) / (right - left)))
        field = _input_field(kind, x_values)
        weighted = half_length * weights
        for local, vertex in enumerate((first, second)):
            for component in range(2):
                source[2 * vertex + component] += factor * np.sum(
                    weighted * shape[:, local] * field[:, component]
                )
        constant += 0.5 * factor * np.sum(weighted * np.sum(field * field, axis=1))
    return source, float(constant)


def _ritz_embedding() -> np.ndarray:
    embedding = np.zeros((DOF_COUNT, 2), dtype=np.float64)
    for cell in range(2):
        for local in range(4):
            vertex = _global_vertex(cell, local)
            x_value, y_value = COORDINATES[cell, local]
            mode = 4.0 * abs(x_value) / LENGTH - 1.0
            embedding[2 * vertex + 1, 0 if y_value == 0.0 else 1] = mode
    return embedding


def _cell_measures(displacement: np.ndarray, cell_rows: dict[int, dict[str, list[np.ndarray]]]) -> list[dict[str, object]]:
    records = []
    for cell in range(2):
        points = COORDINATES[cell]
        vertex_ids = [4 * cell + index for index in range(4)]
        local_u = displacement.reshape(8, 2)[vertex_ids]
        centered_points = points - np.mean(points, axis=0)
        centered_u = local_u - np.mean(local_u, axis=0)
        rotation = float(
            np.sum(centered_points[:, 0] * centered_u[:, 1] - centered_points[:, 1] * centered_u[:, 0])
            / np.sum(centered_points * centered_points)
        )
        rows = cell_rows[cell]
        reference_lengths = (CELL_WIDTH, CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
        records.append(
            {
                "cell": cell + 1,
                "area_fraction_change": float(rows["area"][0] @ displacement / AREA0),
                "edge_relative_extensions": [
                    float(row @ displacement / reference)
                    for row, reference in zip(rows["edge"], reference_lengths)
                ],
                "interior_angle_changes_rad": [float(row @ displacement) for row in rows["angle"]],
                "centroid_displacement": np.mean(local_u, axis=0).tolist(),
                "least_squares_infinitesimal_rotation_rad": rotation,
            }
        )
    return records


def _observables(displacement: np.ndarray, cell_rows: dict[int, dict[str, list[np.ndarray]]]) -> dict[str, object]:
    vertex_u = displacement.reshape(8, 2)

    def vertical_strain(lower: int, upper: int) -> float:
        return float((vertex_u[upper, 1] - vertex_u[lower, 1]) / CELL_HEIGHT)

    internal_sides = [vertical_strain(1, 2), vertical_strain(4, 7)]
    outer_sides = [vertical_strain(0, 3), vertical_strain(5, 6)]
    pair_data = {}
    for name, first, second in PAIRING:
        relative = vertex_u[first] - vertex_u[second]
        pair_data[name] = {
            "relative_displacement": relative.tolist(),
            "opening_x": float(relative[0]),
            "misalignment_y": float(relative[1]),
        }
    return {
        "all_vertex_displacements": vertex_u.tolist(),
        "bottom_displacements": {"C1": vertex_u[[0, 1]].tolist(), "C2": vertex_u[[4, 5]].tolist()},
        "top_displacements": {"C1": vertex_u[[3, 2]].tolist(), "C2": vertex_u[[7, 6]].tolist()},
        "connection_vertical_relative_extension": {
            "internal_side_values": internal_sides,
            "internal_mean": float(np.mean(internal_sides)),
            "periodic_outer_side_values": outer_sides,
            "periodic_outer_mean": float(np.mean(outer_sides)),
        },
        "pair_opening_and_misalignment": pair_data,
        "cell_linearized_shape_and_rotation": _cell_measures(displacement, cell_rows),
    }


def _energy_record(
    displacement: np.ndarray,
    source: np.ndarray,
    prescribed_constant: float,
    terms: dict[str, np.ndarray],
) -> dict[str, object]:
    quadratic = {
        name: float(0.5 * displacement @ matrix @ displacement)
        for name, matrix in terms.items()
    }
    work = float(source @ displacement)
    quadratic_total = float(sum(quadratic.values()))
    basal_full = quadratic["basal_attachment"] - work + prescribed_constant
    return {
        "quadratic_terms": quadratic,
        "quadratic_total": quadratic_total,
        "source_work_f_dot_u": work,
        "prescribed_input_constant": prescribed_constant,
        "basal_attachment_full_including_input": basal_full,
        "total_potential_including_input": quadratic_total - work + prescribed_constant,
        "u_dot_K_u_minus_f_dot_u": None,
    }


def _rigid_objectivity(cell_rows: dict[int, dict[str, list[np.ndarray]]]) -> dict[str, object]:
    result = {}
    for cell in range(2):
        points = COORDINATES[cell]
        center = np.mean(points, axis=0)
        modes = {}
        for name in ("translation_x", "translation_y", "rotation"):
            mode = np.zeros(DOF_COUNT, dtype=np.float64)
            for local in range(4):
                vertex = _global_vertex(cell, local)
                if name == "translation_x":
                    mode[2 * vertex] = 1.0
                elif name == "translation_y":
                    mode[2 * vertex + 1] = 1.0
                else:
                    relative = points[local] - center
                    mode[2 * vertex : 2 * vertex + 2] = [-relative[1], relative[0]]
            values = {
                family: [float(row @ mode) for row in rows]
                for family, rows in cell_rows[cell].items()
            }
            modes[name] = {
                "jacobian_actions": values,
                "maximum_absolute_action": max(abs(value) for family in values.values() for value in family),
            }
        result[f"C{cell + 1}"] = modes
    return result


def _write_exclusive(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(EXPECTED_OUTPUT))
    parser.add_argument("--preparation-start-utc", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if output.as_posix() != EXPECTED_OUTPUT.as_posix() or output.exists():
        raise RuntimeError("unique authorized output path is occupied or changed")
    preparation_start = datetime.fromisoformat(arguments.preparation_start_utc)
    if preparation_start.tzinfo is None:
        raise RuntimeError("preparation start must include a UTC offset")
    execution_start = datetime.now(timezone.utc)
    preparation_seconds = (execution_start - preparation_start.astimezone(timezone.utc)).total_seconds()
    if not (0.0 <= preparation_seconds <= 1800.0):
        raise RuntimeError("preparation budget exceeded or timestamp invalid")
    timer = time.perf_counter()

    terms, cell_rows = _assemble()
    stiffness = sum(terms.values(), np.zeros((DOF_COUNT, DOF_COUNT)))
    embedding = _ritz_embedding()
    ritz_stiffness = embedding.T @ stiffness @ embedding
    source_records = {}
    sources = {}
    constants = {}
    source_checks = {}
    for kind in ("N", "T", "N_plus_T", "zero", "half_N"):
        source16, constant16 = _source(kind, 16)
        source32, constant32 = _source(kind, 32)
        sources[kind] = source32
        constants[kind] = constant32
        source_norm = float(np.linalg.norm(source32))
        difference_norm = float(np.linalg.norm(source32 - source16))
        constant_difference = abs(constant32 - constant16)
        source_checks[kind] = {
            "source_norm": source_norm,
            "gauss16_32_absolute_difference_norm": difference_norm,
            "gauss16_32_relative_to_whole_source_norm": difference_norm / source_norm if source_norm > 0.0 else None,
            "constant_gauss16_32_absolute_difference": constant_difference,
            "near_zero_component_absolute_threshold": 1.0e-13 * source_norm if source_norm > 0.0 else 0.0,
            "near_zero_component_indices": [
                index for index, value in enumerate(source32)
                if source_norm > 0.0 and abs(value) <= 1.0e-13 * source_norm
            ],
            "no_componentwise_relative_error_for_near_zero_terms": True,
        }
        source_records[kind] = source32.tolist()

    solutions = {}
    residuals = {}
    for kind in ("N", "T", "N_plus_T", "zero", "half_N"):
        solution = np.linalg.solve(stiffness, sources[kind])
        solutions[kind] = solution
        residual = stiffness @ solution - sources[kind]
        residuals[kind] = {
            "absolute_norm": float(np.linalg.norm(residual)),
            "relative_norm": float(np.linalg.norm(residual) / np.linalg.norm(sources[kind])) if np.linalg.norm(sources[kind]) > 0.0 else None,
        }

    ritz_source = embedding.T @ sources["N"]
    ritz_coordinates = np.linalg.solve(ritz_stiffness, ritz_source)
    ritz_solution = embedding @ ritz_coordinates
    ritz_residual = ritz_stiffness @ ritz_coordinates - ritz_source

    energies = {}
    observables = {}
    for kind, solution in solutions.items():
        energies[kind] = _energy_record(solution, sources[kind], constants[kind], terms)
        energies[kind]["u_dot_K_u_minus_f_dot_u"] = float(solution @ stiffness @ solution - sources[kind] @ solution)
        observables[kind] = _observables(solution, cell_rows)
    energies["Ritz_N"] = _energy_record(ritz_solution, sources["N"], constants["N"], terms)
    energies["Ritz_N"]["u_dot_K_u_minus_f_dot_u"] = float(ritz_solution @ stiffness @ ritz_solution - sources["N"] @ ritz_solution)
    observables["Ritz_N"] = _observables(ritz_solution, cell_rows)

    half_displacement_error = float(np.linalg.norm(solutions["half_N"] - 0.5 * solutions["N"]))
    superposition_error = float(np.linalg.norm(solutions["N_plus_T"] - solutions["N"] - solutions["T"]))
    half_energy_errors = {}
    for name, value in energies["N"]["quadratic_terms"].items():
        target = 0.25 * value
        observed = energies["half_N"]["quadratic_terms"][name]
        half_energy_errors[name] = {
            "absolute": abs(observed - target),
            "relative_when_target_nonzero": abs(observed - target) / abs(target) if target != 0.0 else None,
        }
    for name in ("quadratic_total", "source_work_f_dot_u", "prescribed_input_constant", "basal_attachment_full_including_input", "total_potential_including_input"):
        target = 0.25 * float(energies["N"][name])
        observed = float(energies["half_N"][name])
        half_energy_errors[name] = {
            "absolute": abs(observed - target),
            "relative_when_target_nonzero": abs(observed - target) / abs(target) if target != 0.0 else None,
        }

    compliance_full = float(sources["N"] @ solutions["N"])
    compliance_ritz = float(sources["N"] @ ritz_solution)
    internal_full = observables["N"]["connection_vertical_relative_extension"]
    internal_ritz = observables["Ritz_N"]["connection_vertical_relative_extension"]
    comparison = {
        "full_minus_Ritz_displacement_norm": float(np.linalg.norm(solutions["N"] - ritz_solution)),
        "relative_to_full_displacement_norm": float(np.linalg.norm(solutions["N"] - ritz_solution) / np.linalg.norm(solutions["N"])),
        "full_x_displacement_norm": float(np.linalg.norm(solutions["N"].reshape(8, 2)[:, 0])),
        "Ritz_x_displacement_norm_by_definition": float(np.linalg.norm(ritz_solution.reshape(8, 2)[:, 0])),
        "connection_vertical_relative_extension": {
            "internal_full": internal_full["internal_mean"],
            "internal_Ritz": internal_ritz["internal_mean"],
            "internal_full_minus_Ritz": internal_full["internal_mean"] - internal_ritz["internal_mean"],
            "periodic_outer_full": internal_full["periodic_outer_mean"],
            "periodic_outer_Ritz": internal_ritz["periodic_outer_mean"],
            "periodic_outer_full_minus_Ritz": internal_full["periodic_outer_mean"] - internal_ritz["periodic_outer_mean"],
        },
        "compliance_f_dot_u": {
            "full": compliance_full,
            "Ritz": compliance_ritz,
            "full_minus_Ritz": compliance_full - compliance_ritz,
            "Ritz_fraction_of_full": compliance_ritz / compliance_full,
        },
        "no_scientific_pass_threshold_predeclared": True,
    }

    symmetry_error = float(np.linalg.norm(stiffness - stiffness.T) / np.linalg.norm(stiffness))
    full_cholesky = True
    ritz_cholesky = True
    try:
        np.linalg.cholesky(stiffness)
    except np.linalg.LinAlgError:
        full_cholesky = False
    try:
        np.linalg.cholesky(ritz_stiffness)
    except np.linalg.LinAlgError:
        ritz_cholesky = False
    objectivity = _rigid_objectivity(cell_rows)
    maximum_objectivity_error = max(
        mode["maximum_absolute_action"]
        for cell in objectivity.values()
        for mode in cell.values()
    )
    maximum_nonzero_residual = max(
        residuals[name]["relative_norm"] for name in ("N", "T", "N_plus_T", "half_N")
    )
    maximum_half_energy_relative = max(
        item["relative_when_target_nonzero"]
        for item in half_energy_errors.values()
        if item["relative_when_target_nonzero"] is not None
    )
    quadrature_pass = all(
        (
            item["gauss16_32_relative_to_whole_source_norm"] <= 1.0e-12
            and item["constant_gauss16_32_absolute_difference"] <= 1.0e-12 * max(constants[name], 1.0e-30)
        )
        if item["source_norm"] > 0.0
        else item["gauss16_32_absolute_difference_norm"] == 0.0
        for name, item in source_checks.items()
    )
    checks = {
        "stiffness_symmetry": {"relative_error": symmetry_error, "tolerance": 1.0e-12, "pass": symmetry_error <= 1.0e-12},
        "positive_definiteness": {
            "full_cholesky_pass": full_cholesky,
            "Ritz_cholesky_pass": ritz_cholesky,
            "full_minimum_eigenvalue": float(np.min(np.linalg.eigvalsh(stiffness))),
            "Ritz_minimum_eigenvalue": float(np.min(np.linalg.eigvalsh(ritz_stiffness))),
            "pass": full_cholesky and ritz_cholesky,
        },
        "nonzero_solution_residual": {"per_case": residuals, "maximum_relative": maximum_nonzero_residual, "tolerance": 1.0e-10, "pass": maximum_nonzero_residual <= 1.0e-10},
        "Ritz_reduced_residual": {
            "absolute_norm": float(np.linalg.norm(ritz_residual)),
            "relative_norm": float(np.linalg.norm(ritz_residual) / np.linalg.norm(ritz_source)),
            "full_space_residual_is_not_a_Ritz_failure": float(np.linalg.norm(stiffness @ ritz_solution - sources["N"])),
            "tolerance": 1.0e-10,
            "pass": np.linalg.norm(ritz_residual) / np.linalg.norm(ritz_source) <= 1.0e-10,
        },
        "zero_response": {
            "maximum_absolute_displacement": float(np.max(np.abs(solutions["zero"]))),
            "absolute_tolerance": ABS_DISPLACEMENT_SCALE,
            "pass": np.max(np.abs(solutions["zero"])) <= ABS_DISPLACEMENT_SCALE,
        },
        "linearity": {
            "half_N_absolute_displacement_error": half_displacement_error,
            "half_N_relative_error": half_displacement_error / max(np.linalg.norm(0.5 * solutions["N"]), ABS_DISPLACEMENT_SCALE),
            "N_plus_T_absolute_superposition_error": superposition_error,
            "N_plus_T_relative_error": superposition_error / max(np.linalg.norm(solutions["N"] + solutions["T"]), ABS_DISPLACEMENT_SCALE),
            "relative_tolerance": 1.0e-10,
            "near_zero_absolute_scale": ABS_DISPLACEMENT_SCALE,
        },
        "half_amplitude_energy_quarter": {
            "per_energy": half_energy_errors,
            "maximum_nonzero_relative_error": maximum_half_energy_relative,
            "pass": maximum_half_energy_relative <= 1.0e-10,
        },
        "source_quadrature": {"per_case": source_checks, "relative_tolerance": 1.0e-12, "pass": quadrature_pass},
        "bare_cell_internal_objectivity": {
            "per_cell_and_rigid_mode": objectivity,
            "maximum_absolute_jacobian_action": maximum_objectivity_error,
            "pairs_and_attachment_excluded": True,
            "pass": maximum_objectivity_error <= 1.0e-12,
        },
        "full_Ritz_variational_relation": {
            "f_dot_u_full": compliance_full,
            "f_dot_u_Ritz": compliance_ritz,
            "full_minus_Ritz": compliance_full - compliance_ritz,
            "numerical_tolerance": 1.0e-12 * max(abs(compliance_full), 1.0e-30),
            "pass": compliance_full + 1.0e-12 * max(abs(compliance_full), 1.0e-30) >= compliance_ritz,
        },
    }
    checks["linearity"]["pass"] = (
        checks["linearity"]["half_N_relative_error"] <= 1.0e-10
        and checks["linearity"]["N_plus_T_relative_error"] <= 1.0e-10
    )
    all_checks_pass = all(record["pass"] for record in checks.values())
    execution_finish = datetime.now(timezone.utc)
    execution_seconds = time.perf_counter() - timer
    payload = {
        "schema": "paper2_closed_cell_ritz_probe_v01",
        "status": "COMPLETED_BOUNDED_IDEAL_PROTOTYPE" if all_checks_pass else "ABORTED_FAIL_CLOSED_CHECK_FAILURE",
        "scientific_question": "Does a 16-DOF pair of closed rectangular cells differ from the same-energy two-coordinate Ritz restriction in common connection extension and cell deformation?",
        "claim_boundary": {
            "ideal_dimensionless_linear_reference_problem": True,
            "not_physiologically_calibrated_or_extrapolated": True,
            "not_new_trilayer_coupling_or_DCM_solution": True,
            "not_DCM_necessity_or_Nature_Physics_mechanism_pass": True,
            "invalid_withdrawn_ratio_I_not_implemented": True,
            "Ritz_forced_zero_quantities_not_used_as_positive_gate": True,
            "scientific_acceptance_pending_independent_supervisor_review": True,
        },
        "preregistration": {
            "frozen_commit": FROZEN_COMMIT,
            "main_plan_section_31_sha256": PLAN_SHA256,
            "science_brief_sections_53_54_sha256": BRIEF_SHA256,
            "section_54_controls_on_conflict": True,
        },
        "runtime": {
            "preparation_started_at_utc": preparation_start.astimezone(timezone.utc).isoformat(),
            "execution_started_at_utc": execution_start.isoformat(),
            "execution_finished_at_utc": execution_finish.isoformat(),
            "preparation_elapsed_seconds": preparation_seconds,
            "preparation_budget_seconds": 1800.0,
            "execution_elapsed_seconds": execution_seconds,
            "execution_budget_seconds": 30.0,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "python_executable": sys.executable,
            "cpu_threads": 1,
            "memory_limit_gib": 8,
            "matrix_and_solution_bytes": int(stiffness.nbytes + ritz_stiffness.nbytes + embedding.nbytes + sum(value.nbytes for value in sources.values()) + sum(value.nbytes for value in solutions.values()) + ritz_solution.nbytes),
            "bytecode_cache": "disabled",
            "gpu": "not_used",
            "network": "not_used",
            "container": "not_used",
            "production_FEM_and_old_cases": "not_imported_or_read",
            "entry_path": "scripts/run_paper2_closed_cell_ritz_probe_v01.py",
            "entry_sha256": _sha256(Path(__file__)),
        },
        "fixed_model": {
            "L": LENGTH,
            "a": CELL_WIDTH,
            "b": CELL_HEIGHT,
            "epsilon": EPSILON,
            "input_amplitude_epsilon_times_b": AMPLITUDE,
            "parameters": {"K_A": K_AREA, "K_l": K_EDGE, "kappa": K_ANGLE, "K_cc": K_CC, "K_ce": K_CE},
            "vertices_counterclockwise": {"C1": COORDINATES[0].tolist(), "C2": COORDINATES[1].tolist()},
            "vertex_identity_merged": False,
            "dof_order": "[C1v0x,C1v0y,...,C1v3y,C2v0x,...,C2v3y]",
            "pairing_counted_once": [{"name": name, "first_global_vertex": first, "second_global_vertex": second} for name, first, second in PAIRING],
            "periodic_outer_reference_offset_L_handled_by_comparing_displacements": True,
            "bottom_edges_global_vertices": [[first, second] for first, second, _, _ in BOTTOM_EDGES],
            "top_unclamped_and_unloaded": True,
            "no_macro_strain_damping_or_prestress": True,
            "input_fields": {
                "N": "epsilon*b*cos(2*pi*x/L)*e_y",
                "T": "epsilon*b*sin(2*pi*x/L)*e_x",
            },
            "linearization": "direct first Jacobians of area, each edge length, and each interior angle at the reference rectangles; no nonlinear relaxation",
            "interior_angle_linearization": "difference of adjacent oriented-edge infinitesimal rotations",
            "exact_bottom_P1_mass_matrix_each_edge": ((CELL_WIDTH / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])).tolist(),
            "source_integration": "Gauss-Legendre 32 used; 16/32 checked against whole source norm",
        },
        "matrices": {
            "K_full_16x16": stiffness.tolist(),
            "K_term_16x16": {name: matrix.tolist() for name, matrix in terms.items()},
            "B_16x2": embedding.tolist(),
            "K_Ritz_2x2_equals_BtKB": ritz_stiffness.tolist(),
        },
        "right_sides_and_solutions": {
            "full": {
                name: {"f": source_records[name], "u": solutions[name].tolist()}
                for name in ("N", "T", "N_plus_T", "zero", "half_N")
            },
            "Ritz_N": {
                "f_full": source_records["N"],
                "f_Ritz_equals_Btf": ritz_source.tolist(),
                "coordinates_delta_eta": ritz_coordinates.tolist(),
                "u_full_space_equals_Bq": ritz_solution.tolist(),
            },
            "algebraic_right_side_count": 6,
            "not_added_to_old_FEM_ledger": True,
        },
        "observables": observables,
        "energies": energies,
        "full_Ritz_N_comparison": comparison,
        "checks": checks,
        "existing_compute_ledger_unchanged": {
            "completed_periodic_cases": 46,
            "completed_static_FEM_right_sides": 30,
            "FEM_and_failure_seconds": 170.24076614002115,
            "new_cell_algebraic_right_sides": 6,
            "new_cell_algebraic_seconds_recorded_separately": execution_seconds,
        },
        "next_gate": "SUPERVISOR_INDEPENDENT_RECOMPUTATION_STOP",
    }
    if execution_seconds > 30.0:
        payload["status"] = "ABORTED_FAIL_CLOSED_EXECUTION_BUDGET"
        all_checks_pass = False
    _write_exclusive(output, payload)
    print(
        f"CLOSED_CELL_RITZ_DONE status={payload['status']} "
        f"prep={preparation_seconds:.3f}s execution={execution_seconds:.6f}s"
    )
    return 0 if all_checks_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
