"""Independent checks for the heterogeneous myocardial-row equilibrium package."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _gate(value: float | int | bool, passed: bool, criterion: str) -> dict[str, object]:
    return {"value": value, "criterion": criterion, "passed": bool(passed)}


def verify_myocardial_row(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    required = [
        result / "execution.json",
        result / "heterogeneity.csv",
        result / "raw/kernel_metrics.json",
        result / "raw/nodes.csv",
        result / "raw/faces.csv",
        result / "raw/state_metrics.csv",
        result / "raw/cell_metrics.csv",
        result / "raw/step_audits.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "failed", "reason": "missing evidence", "missing": missing}

    execution = json.loads((result / "execution.json").read_text(encoding="utf-8"))
    kernel = json.loads((result / "raw/kernel_metrics.json").read_text(encoding="utf-8"))
    states = _read_csv(result / "raw/state_metrics.csv")
    cells = _read_csv(result / "raw/cell_metrics.csv")
    nodes = _read_csv(result / "raw/nodes.csv")
    heterogeneity = _read_csv(result / "heterogeneity.csv")
    if len(states) < 2 or len(cells) != 5 * len(states) or not nodes:
        return {
            "status": "failed",
            "reason": "incomplete state ledger",
            "state_rows": len(states),
            "cell_rows": len(cells),
            "node_rows": len(nodes),
        }

    final_snapshot = max(int(row["snapshot_index"]) for row in states)
    final_state = next(row for row in states if int(row["snapshot_index"]) == final_snapshot)
    previous_state = next(row for row in states if int(row["snapshot_index"]) == final_snapshot - 1)
    final_cells = sorted(
        (row for row in cells if int(row["snapshot_index"]) == final_snapshot),
        key=lambda row: int(row["cell_id"]),
    )

    contraction_maximum = max(float(row["contraction_traction"]) for row in nodes)
    final_force = float(final_state["max_free_force"])
    current_span = float(final_state["strip_x_span"])
    previous_span = float(previous_state["strip_x_span"])
    span_drift = abs(current_span - previous_span) / max(abs(previous_span), 1.0e-30)
    maximum_volume_error = float(kernel["maximum_volume_relative_error"])
    minimum_angle = float(kernel["minimum_triangle_angle_deg"])
    fixed_displacement = float(kernel["maximum_fixed_displacement"])
    junction_residual = max(float(row["junction_balance_residual"]) for row in states)
    work_residual = float(kernel["maximum_work_relative_residual"])

    shape_columns = [
        "length_scale",
        "width_scale",
        "thickness_scale",
        "side_wave_amplitude",
        "center_y",
    ]
    mechanics_columns = [
        "bulk_modulus_factor",
        "surface_tension_factor",
        "area_modulus_factor",
        "prestress_factor",
    ]
    shape_variation = max(
        float(np.std([float(row[column]) for row in heterogeneity])) for column in shape_columns
    )
    mechanics_variation = max(
        float(np.std([float(row[column]) for row in heterogeneity])) for column in mechanics_columns
    )
    final_spans = np.asarray(
        [[float(row[axis]) for axis in ("p_span", "q_span", "r_span")] for row in final_cells]
    )
    final_span_cv = np.std(final_spans, axis=0) / np.maximum(np.mean(final_spans, axis=0), 1.0e-30)

    gates = {
        "execution_completed": _gate(
            execution.get("return_code") == 0,
            execution.get("return_code") == 0,
            "return_code == 0",
        ),
        "contraction_disabled": _gate(
            contraction_maximum, contraction_maximum <= 1.0e-15, "maximum contraction traction <= 1e-15"
        ),
        "final_force": _gate(final_force, final_force <= 1.0e-3, "final max free force <= 1e-3"),
        "terminal_span_drift": _gate(span_drift, span_drift <= 2.0e-3, "last-block span drift <= 2e-3"),
        "volume": _gate(maximum_volume_error, maximum_volume_error <= 0.02, "maximum relative volume error <= 2%"),
        "mesh_angle": _gate(minimum_angle, minimum_angle >= 15.0, "minimum triangle angle >= 15 deg"),
        "fixed_boundary": _gate(fixed_displacement, fixed_displacement <= 1.0e-10, "fixed displacement <= 1e-10"),
        "junction_balance": _gate(junction_residual, junction_residual <= 1.0e-12, "junction action-reaction residual <= 1e-12"),
        "work_dissipation": _gate(work_residual, work_residual <= 1.0e-10, "work-dissipation residual <= 1e-10"),
        "shape_input_variation": _gate(shape_variation, shape_variation > 1.0e-6, "nonzero frozen shape variation"),
        "mechanics_input_variation": _gate(mechanics_variation, mechanics_variation > 1.0e-6, "nonzero frozen mechanics variation"),
        "final_shape_variation": _gate(
            float(np.max(final_span_cv)),
            float(np.max(final_span_cv)) > 1.0e-3,
            "at least one final span coefficient of variation > 0.1%",
        ),
        "saved_states": _gate(len(states), len(states) == 9, "exactly 9 solver states"),
        "five_cells": _gate(len(final_cells), len(final_cells) == 5, "exactly 5 final cells"),
    }
    failures = [name for name, gate in gates.items() if not gate["passed"]]
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-HETERO-ROW-EQ-A",
        "status": "passed" if not failures else "failed",
        "failed_gates": failures,
        "gates": gates,
        "terminal": {
            "snapshot": final_snapshot,
            "max_free_force": final_force,
            "strip_x_span": current_span,
            "last_block_relative_span_drift": span_drift,
            "maximum_volume_relative_error": maximum_volume_error,
            "minimum_triangle_angle_deg": minimum_angle,
            "final_span_cv": final_span_cv.tolist(),
        },
        "claim_boundary": {
            "mechanical_equilibrium": "qualified only if status is passed",
            "biological_validation": "not_run",
            "contraction": "not_run",
            "heterogeneity": "synthetic fixed sensitivity inputs",
        },
    }

