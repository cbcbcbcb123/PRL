"""Independent verification for the matched crowded myocardial target pair."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .myocardial_crowded_box import (
    _candidate_intersection_count,
    _mesh_measures,
    _read_csv,
    _snapshot_meshes,
)


CONDITIONS = ("UNIFORM_TARGETS", "HETEROGENEOUS_TARGETS")


def _gate(value: object, passed: bool, criterion: str) -> dict[str, object]:
    return {"value": value, "criterion": criterion, "passed": bool(passed)}


def _grid_pairs() -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for row in range(5):
        for column in range(5):
            cell_id = row * 5 + column
            if column < 4:
                result.add((cell_id, cell_id + 1))
            if row < 4:
                result.add((cell_id, cell_id + 5))
    return result


def _target_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="ascii") as stream:
        return list(csv.DictReader(stream))


def _verify_condition(result: Path, condition: str) -> dict[str, object]:
    raw = result / "raw" / condition
    required = [
        result / f"execution_{condition}.json",
        result / "targets" / f"{condition}.csv",
        raw / "kernel_metrics.json",
        raw / "nodes.csv",
        raw / "faces.csv",
        raw / "state_metrics.csv",
        raw / "cell_metrics.csv",
        raw / "contact_pairs.csv",
        raw / "step_audits.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "reason": "missing evidence",
            "missing": missing,
        }

    execution = json.loads(
        (result / f"execution_{condition}.json").read_text(encoding="utf-8")
    )
    kernel = json.loads((raw / "kernel_metrics.json").read_text(encoding="utf-8"))
    states = sorted(
        _read_csv(raw / "state_metrics.csv"),
        key=lambda row: int(row["snapshot_index"]),
    )
    cell_rows = _read_csv(raw / "cell_metrics.csv")
    node_rows = _read_csv(raw / "nodes.csv")
    face_rows = _read_csv(raw / "faces.csv")
    pair_rows = _read_csv(raw / "contact_pairs.csv")
    targets = _target_rows(result / "targets" / f"{condition}.csv")
    safety_limits = {
        float(row.get("maximum_initial_volume_relative_change") or 0.12)
        for row in targets
    }
    if len(safety_limits) != 1:
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "reason": "inconsistent initial-volume safety limits",
            "limits": sorted(safety_limits),
        }
    initial_volume_change_limit = safety_limits.pop()
    snapshots = sorted({int(row["snapshot_index"]) for row in node_rows})
    if snapshots != list(range(9)) or len(states) != 9:
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "reason": "incomplete retained state sequence",
            "snapshots": snapshots,
            "state_rows": len(states),
        }

    target_by_cell = {int(row["cell_id"]): row for row in targets}
    initial_volume_by_cell = {
        cell_id: float(row["initial_volume"])
        for cell_id, row in target_by_cell.items()
    }
    target_volume_by_cell = {
        cell_id: float(row["target_volume"])
        for cell_id, row in target_by_cell.items()
    }
    maximum_initial_volume_change = 0.0
    maximum_target_mismatch = 0.0
    minimum_angle = 180.0
    minimum_wall_clearance = float("inf")
    intersections = 0
    positive_volumes = True
    for snapshot, state in zip(snapshots, states, strict=True):
        meshes = _snapshot_meshes(node_rows, face_rows, snapshot)
        if any(
            points.shape != (162, 3) or triangles.shape != (320, 3)
            for points, triangles in meshes
        ):
            return {
                "status": "failed",
                "numerical_saved_state_safety": "failed",
                "static_equilibrium": "unknown",
                "contact_network": "unknown",
                "reason": "wrong retained mesh dimensions",
                "snapshot": snapshot,
            }
        bounds = np.asarray(
            [
                float(state[name])
                for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")
            ]
        )
        for cell_id, (points, triangles) in enumerate(meshes):
            volume, angle = _mesh_measures(points, triangles)
            positive_volumes = positive_volumes and volume > 0.0
            maximum_initial_volume_change = max(
                maximum_initial_volume_change,
                abs(volume - initial_volume_by_cell[cell_id])
                / initial_volume_by_cell[cell_id],
            )
            maximum_target_mismatch = max(
                maximum_target_mismatch,
                abs(volume - target_volume_by_cell[cell_id])
                / target_volume_by_cell[cell_id],
            )
            minimum_angle = min(minimum_angle, angle)
            clearances = np.column_stack(
                (
                    points[:, 0] - bounds[0],
                    bounds[1] - points[:, 0],
                    points[:, 1] - bounds[2],
                    bounds[3] - points[:, 1],
                    points[:, 2] - bounds[4],
                    bounds[5] - points[:, 2],
                )
            )
            minimum_wall_clearance = min(
                minimum_wall_clearance, float(clearances.min())
            )
            intersections += _candidate_intersection_count(
                points, triangles, points, triangles, same_mesh=True
            )
        for first_cell in range(25):
            first_points, first_faces = meshes[first_cell]
            for second_cell in range(first_cell + 1, 25):
                second_points, second_faces = meshes[second_cell]
                separated_axis = any(
                    float(first_points[:, axis].max())
                    < float(second_points[:, axis].min())
                    or float(second_points[:, axis].max())
                    < float(first_points[:, axis].min())
                    for axis in range(3)
                )
                if not separated_axis:
                    intersections += _candidate_intersection_count(
                        first_points,
                        first_faces,
                        second_points,
                        second_faces,
                        same_mesh=False,
                    )

    initial_cell_rows = {
        int(row["cell_id"]): row
        for row in cell_rows
        if int(row["snapshot_index"]) == 0
    }
    target_application_error = 0.0
    for cell_id, target in target_by_cell.items():
        reported = initial_cell_rows[cell_id]
        for target_column, reported_column in (
            ("target_volume", "target_volume"),
            ("target_area_at_target_volume", "target_area_at_target_volume"),
            ("target_isoperimetric_ratio", "target_isoperimetric_ratio"),
        ):
            expected = float(target[target_column])
            actual = float(reported[reported_column])
            target_application_error = max(
                target_application_error, abs(actual - expected) / expected
            )

    final_snapshot = snapshots[-1]
    final_state = states[-1]
    final_pairs = {
        tuple(sorted((int(row["cell_a"]), int(row["cell_b"]))))
        for row in pair_rows
        if int(row["snapshot_index"]) == final_snapshot
    }
    grid_pairs = _grid_pairs()
    active_grid_pairs = final_pairs & grid_pairs
    contacted_cells = {cell for pair in final_pairs for cell in pair}
    isolated_cells = sorted(set(range(25)) - contacted_cells)
    contact_network = (
        "passed"
        if len(active_grid_pairs) >= 32 and not isolated_cells
        else "failed"
    )
    final_force = float(final_state["max_free_force"])
    static_equilibrium = "passed" if final_force <= 1.0e-3 else "failed"
    contraction_maximum = max(float(row["contraction_traction"]) for row in node_rows)
    reported_separation = min(float(row["min_intercell_separation"]) for row in states)
    reported_self_separation = min(
        float(row["min_nonincident_separation"]) for row in states
    )
    initial_planar_area = float(states[0]["box_planar_area"])
    final_planar_area = float(final_state["box_planar_area"])
    gates = {
        "execution_completed": _gate(
            execution.get("return_code"),
            execution.get("return_code") == 0,
            "one requested condition invocation return_code == 0",
        ),
        "saved_states": _gate(len(states), len(states) == 9, "exactly 9 solver states"),
        "twenty_five_cells": _gate(
            len(cell_rows), len(cell_rows) == 225, "25 cells at each of 9 states"
        ),
        "positive_volumes": _gate(
            positive_volumes, positive_volumes, "all independently recomputed volumes > 0"
        ),
        "initial_volume_change": _gate(
            maximum_initial_volume_change,
            maximum_initial_volume_change <= initial_volume_change_limit,
            "maximum change from each cell's own initial volume "
            f"<= {initial_volume_change_limit:.6g}",
        ),
        "mesh_angle": _gate(
            minimum_angle, minimum_angle >= 15.0, "minimum triangle angle >= 15 degrees"
        ),
        "wall_clearance": _gate(
            minimum_wall_clearance,
            minimum_wall_clearance >= -1.0e-6,
            "independently recomputed wall clearance >= -1e-6",
        ),
        "surface_intersections": _gate(
            intersections,
            intersections == 0,
            "independent broad-phase and segment-triangle screen finds zero intersections",
        ),
        "reported_separation": _gate(
            reported_separation,
            reported_separation > 1.0e-8,
            "saved-state full-triangle intercell separation > 1e-8",
        ),
        "reported_self_separation": _gate(
            reported_self_separation,
            reported_self_separation > 1.0e-8,
            "saved-state nonincident self separation > 1e-8",
        ),
        "work_dissipation": _gate(
            float(kernel["maximum_work_relative_residual"]),
            float(kernel["maximum_work_relative_residual"]) <= 1.0e-10,
            "maximum work-dissipation relative residual <= 1e-10",
        ),
        "target_application": _gate(
            target_application_error,
            target_application_error <= 1.0e-12,
            "solver-reported target V, area, and q match manifest",
        ),
        "contraction_disabled": _gate(
            contraction_maximum,
            contraction_maximum <= 1.0e-15,
            "maximum active contraction traction <= 1e-15",
        ),
        "box_planar_compression": _gate(
            final_planar_area / initial_planar_area,
            abs(final_planar_area / initial_planar_area - 0.95**2) <= 1.0e-10,
            "final planar box area / initial area == 0.95^2",
        ),
    }
    failed_gates = [name for name, gate in gates.items() if not gate["passed"]]
    final_cells = sorted(
        (
            row
            for row in cell_rows
            if int(row["snapshot_index"]) == final_snapshot
        ),
        key=lambda row: int(row["cell_id"]),
    )
    return {
        "status": "passed" if not failed_gates else "failed",
        "numerical_saved_state_safety": "passed" if not failed_gates else "failed",
        "static_equilibrium": static_equilibrium,
        "contact_network": contact_network,
        "failed_gates": failed_gates,
        "gates": gates,
        "terminal": {
            "max_free_force": final_force,
            "projected_occupancy": float(final_state["projected_occupancy"]),
            "maximum_target_volume_mismatch": maximum_target_mismatch,
            "maximum_initial_volume_change": maximum_initial_volume_change,
            "maximum_initial_volume_change_limit": initial_volume_change_limit,
            "minimum_triangle_angle_deg": minimum_angle,
            "minimum_wall_clearance": minimum_wall_clearance,
            "active_cell_pairs": len(final_pairs),
            "active_grid_neighbor_pairs": len(active_grid_pairs),
            "registered_grid_neighbor_pairs": 40,
            "isolated_cells": isolated_cells,
            "total_wall_reaction": float(final_state["total_wall_reaction"]),
        },
        "final_cells": [
            {
                "cell_id": int(row["cell_id"]),
                "pressure": float(row["pressure"]),
                "volume": float(row["volume"]),
                "area": float(row["area"]),
                "x_span": float(row["x_span"]),
                "y_span": float(row["y_span"]),
                "z_span": float(row["z_span"]),
                "mean_contact_traction": float(row["mean_contact_traction"]),
                "mean_wall_traction": float(row["mean_wall_traction"]),
            }
            for row in final_cells
        ],
    }


def verify_myocardial_crowded_target_pair(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    required = [
        result / "configuration.json",
        result / "target_summary.json",
        result / "heterogeneity.csv",
        result / "box_schedule.csv",
        result / "targets" / "UNIFORM_TARGETS.csv",
        result / "targets" / "HETEROGENEOUS_TARGETS.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "failed", "reason": "missing shared evidence", "missing": missing}

    target_rows = {
        condition: _target_rows(result / "targets" / f"{condition}.csv")
        for condition in CONDITIONS
    }
    target_values: dict[str, dict[str, np.ndarray]] = {}
    for condition, rows in target_rows.items():
        target_values[condition] = {
            "volume": np.asarray([float(row["target_volume"]) for row in rows]),
            "area": np.asarray(
                [float(row["target_area_at_target_volume"]) for row in rows]
            ),
        }
    uniform = target_values["UNIFORM_TARGETS"]
    heterogeneous = target_values["HETEROGENEOUS_TARGETS"]
    mean_volume_difference = abs(float(uniform["volume"].mean() - heterogeneous["volume"].mean()))
    mean_area_difference = abs(float(uniform["area"].mean() - heterogeneous["area"].mean()))
    target_gates = {
        "complete_targets": _gate(
            {name: len(rows) for name, rows in target_rows.items()},
            all(len(rows) == 25 for rows in target_rows.values()),
            "25 target rows per condition",
        ),
        "matched_volume_mean": _gate(
            mean_volume_difference,
            mean_volume_difference <= 1.0e-12 * float(uniform["volume"].mean()),
            "condition target-volume means match to relative 1e-12",
        ),
        "matched_area_mean": _gate(
            mean_area_difference,
            mean_area_difference <= 1.0e-12 * float(uniform["area"].mean()),
            "condition target-area means match to relative 1e-12",
        ),
        "uniform_targets_identical": _gate(
            {
                "volume_sd": float(uniform["volume"].std()),
                "area_sd": float(uniform["area"].std()),
            },
            float(uniform["volume"].std()) <= 1.0e-13
            and float(uniform["area"].std()) <= 1.0e-13,
            "uniform condition has identical target volume and area",
        ),
        "heterogeneous_targets_vary": _gate(
            {
                "volume_cv": float(heterogeneous["volume"].std() / heterogeneous["volume"].mean()),
                "area_cv": float(heterogeneous["area"].std() / heterogeneous["area"].mean()),
            },
            float(heterogeneous["volume"].std()) > 0.0
            and float(heterogeneous["area"].std()) > 0.0,
            "heterogeneous condition has nonzero cellwise target variation",
        ),
    }
    conditions = {
        condition: _verify_condition(result, condition) for condition in CONDITIONS
    }
    uniform_cells = conditions["UNIFORM_TARGETS"].get("final_cells", [])
    heterogeneous_cells = conditions["HETEROGENEOUS_TARGETS"].get("final_cells", [])
    paired_metrics: dict[str, object] = {}
    if len(uniform_cells) == len(heterogeneous_cells) == 25:
        for metric in (
            "pressure",
            "volume",
            "area",
            "x_span",
            "y_span",
            "z_span",
            "mean_contact_traction",
            "mean_wall_traction",
        ):
            differences = np.asarray(
                [
                    float(heterogeneous_row[metric]) - float(uniform_row[metric])
                    for uniform_row, heterogeneous_row in zip(
                        uniform_cells, heterogeneous_cells, strict=True
                    )
                ]
            )
            paired_metrics[metric] = {
                "heterogeneous_minus_uniform_mean": float(differences.mean()),
                "heterogeneous_minus_uniform_sd": float(differences.std()),
                "minimum": float(differences.min()),
                "maximum": float(differences.max()),
                "cellwise": differences.tolist(),
            }
    target_failures = [name for name, gate in target_gates.items() if not gate["passed"]]
    numerical_passed = all(
        conditions[condition].get("numerical_saved_state_safety") == "passed"
        for condition in CONDITIONS
    )
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-TARGET-PAIR-A",
        "status": "passed" if numerical_passed and not target_failures else "failed",
        "status_semantics": "paired target contract and numerical saved-state safety only",
        "target_failed_gates": target_failures,
        "target_gates": target_gates,
        "conditions": conditions,
        "paired_comparison": paired_metrics,
        "claim_boundary": {
            "static_equilibrium": {
                condition: conditions[condition].get("static_equilibrium", "unknown")
                for condition in CONDITIONS
            },
            "contact_network": {
                condition: conditions[condition].get("contact_network", "unknown")
                for condition in CONDITIONS
            },
            "biological_validation": "not_run",
            "contraction": "not_run",
            "random_seed_replication": "not_run",
            "contact_resolution": "exploratory 0.40 maximum-edge quadrature",
        },
    }
