"""Independent adjudication for the regular 2x2 DCM load-hold stage."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .myocardial_crowded_box import (
    _candidate_intersection_count,
    _mesh_measures,
)


EXPECTED_LEVELS = (0.00, 0.20, 0.28, 0.34, 0.40)
EXPECTED_NEIGHBORS = {(0, 1), (0, 2), (1, 3), (2, 3)}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_meshes(raw: Path, snapshot: int) -> list[tuple[np.ndarray, np.ndarray]]:
    nodes = _rows(raw / "nodes.csv")
    faces = _rows(raw / "faces.csv")
    result: list[tuple[np.ndarray, np.ndarray]] = []
    for cell_id in range(4):
        selected_nodes = sorted(
            (
                row
                for row in nodes
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        selected_faces = sorted(
            (
                row
                for row in faces
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["face_local_id"]),
        )
        points = np.asarray(
            [[float(row[name]) for name in ("x", "y", "z")] for row in selected_nodes]
        )
        triangles = np.asarray(
            [[int(row[name]) for name in ("n1", "n2", "n3")] for row in selected_faces],
            dtype=int,
        )
        result.append((points, triangles))
    return result


def _independent_intersections(raw: Path) -> int:
    node_rows = _rows(raw / "nodes.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in node_rows})
    intersections = 0
    for snapshot in snapshots:
        meshes = _snapshot_meshes(raw, snapshot)
        for points, triangles in meshes:
            if points.shape != (162, 3) or triangles.shape != (320, 3):
                return -1
            intersections += _candidate_intersection_count(
                points, triangles, points, triangles, same_mesh=True
            )
        for first in range(4):
            first_points, first_faces = meshes[first]
            for second in range(first + 1, 4):
                second_points, second_faces = meshes[second]
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
    return intersections


def _final_pairs(raw: Path) -> set[tuple[int, int]]:
    rows = _rows(raw / "contact_pairs.csv")
    if not rows:
        return set()
    final_snapshot = max(int(row["snapshot_index"]) for row in rows)
    return {
        tuple(sorted((int(row["cell_a"]), int(row["cell_b"]))))
        for row in rows
        if int(row["snapshot_index"]) == final_snapshot
    }


def verify_regular_2x2_load_hold(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    root = result.parents[2]
    configuration = json.loads(
        (result / "configuration.json").read_text(encoding="utf-8")
    )
    executions = json.loads((result / "execution.json").read_text(encoding="utf-8"))
    recorded_hashes = json.loads(
        (result / "source_hashes_before.json").read_text(encoding="utf-8")
    )
    source_checks = {
        path: (root / path).is_file() and _sha256(root / path) == expected
        for path, expected in recorded_hashes.items()
    }

    level_reports: list[dict[str, object]] = []
    all_intersections = 0
    for execution in executions:
        label = str(execution["label"])
        raw = result / "raw" / label
        required = [
            raw / "kernel_metrics.json",
            raw / "state_metrics.csv",
            raw / "cell_metrics.csv",
            raw / "nodes.csv",
            raw / "faces.csv",
            raw / "contact_pairs.csv",
            raw / "step_audits.csv",
        ]
        if execution.get("return_code") != 0 or not all(path.is_file() for path in required):
            level_reports.append(
                {
                    "label": label,
                    "planar_approach": execution.get("planar_approach"),
                    "status": "failed",
                    "reason": "solver did not retain a complete level",
                    "return_code": execution.get("return_code"),
                }
            )
            break
        kernel = json.loads((raw / "kernel_metrics.json").read_text(encoding="utf-8"))
        states = _rows(raw / "state_metrics.csv")
        audits = _rows(raw / "step_audits.csv")
        intersections = _independent_intersections(raw)
        all_intersections += max(intersections, 0)
        minimum_angle = min(float(row["min_triangle_angle_deg"]) for row in states)
        maximum_volume_change = max(
            float(row["max_initial_volume_relative_change"]) for row in states
        )
        minimum_wall_clearance = min(
            float(row["min_wall_clearance"]) for row in states
        )
        minimum_nonincident = min(
            float(row["min_nonincident_separation"]) for row in states
        )
        minimum_height = min(float(row["min_triangle_height"]) for row in states)
        finite_contact_gaps = [
            float(row["minimum_contact_quadrature_gap"])
            for row in states
            if np.isfinite(float(row["minimum_contact_quadrature_gap"]))
        ]
        minimum_contact_gap = min(finite_contact_gaps) if finite_contact_gaps else float("inf")
        maximum_work_residual = max(
            abs(float(row["max_work_relative_residual"])) for row in audits
        )
        final_force = float(states[-1]["max_free_force"])
        equilibrium = (
            kernel.get("static_equilibrium") == "passed"
            and final_force <= 1.0e-3
            and int(kernel.get("final_consecutive_equilibrium_steps", 0)) >= 8
        )
        safe = (
            intersections == 0
            and minimum_angle >= 15.0
            and maximum_volume_change <= 0.02
            and minimum_wall_clearance >= -1.0e-6
            and minimum_nonincident > 1.0e-8
            and minimum_height > 1.0e-8
            and minimum_contact_gap > 1.0e-8
            and maximum_work_residual <= 1.0e-10
        )
        level_reports.append(
            {
                "label": label,
                "planar_approach": float(execution["planar_approach"]),
                "status": "passed" if safe and equilibrium else "failed",
                "retained_states": len(states),
                "completed_requested_steps": int(
                    kernel.get("completed_requested_step_count", -1)
                ),
                "final_maximum_nodal_force": final_force,
                "minimum_triangle_angle_degrees": minimum_angle,
                "maximum_relative_volume_change_from_level_input": maximum_volume_change,
                "minimum_wall_clearance": minimum_wall_clearance,
                "minimum_nonincident_separation": minimum_nonincident,
                "minimum_triangle_height": minimum_height,
                "minimum_contact_quadrature_gap": minimum_contact_gap,
                "maximum_work_relative_residual": maximum_work_residual,
                "independent_intersections": intersections,
                "active_pairs_at_final_state": sorted(_final_pairs(raw)),
                "wall_seconds": float(execution.get("elapsed_seconds", 0.0)),
            }
        )
        if not (safe and equilibrium):
            break

    approaches = tuple(
        float(report["planar_approach"]) for report in level_reports
    )
    final_pairs = (
        set(map(tuple, level_reports[-1].get("active_pairs_at_final_state", [])))
        if level_reports
        else set()
    )
    checks = {
        "single_attempt_per_conditional_level": all(
            execution.get("automatic_retry") is False for execution in executions
        ),
        "source_hashes_unchanged": all(source_checks.values()),
        "all_five_levels_executed": approaches == EXPECTED_LEVELS,
        "all_levels_safe_and_equilibrated": len(level_reports) == len(EXPECTED_LEVELS)
        and all(report["status"] == "passed" for report in level_reports),
        "independent_intersection_screen": all_intersections == 0
        and all(report.get("independent_intersections") == 0 for report in level_reports),
        "final_four_neighbor_network": EXPECTED_NEIGHBORS.issubset(final_pairs),
        "fem_not_run": configuration.get("fem_status") == "not_run_by_user_instruction",
    }
    status = "passed" if all(checks.values()) else "failed"
    return {
        "status": status,
        "scope": "regular 2x2 DCM load-hold qualification; FEM not run",
        "checks": checks,
        "source_checks": source_checks,
        "levels": level_reports,
        "final_neighbor_pairs": sorted(final_pairs),
        "required_neighbor_pairs": sorted(EXPECTED_NEIGHBORS),
        "scientific_gates": {
            "regular_2x2_dcm": status,
            "regular_5x5_dcm": "not_run",
            "heterogeneous_dcm": "not_run",
            "cell_resolved_fem": "not_run",
            "homogenized_fem": "not_run",
            "dcm_advantage": "not_run",
            "biological_validation": "not_run",
        },
        "interpretation": (
            "This stage only qualifies a uniform four-cell DCM patch. It cannot establish "
            "experimental realism or a DCM advantage over FEM."
        ),
    }


__all__ = ["verify_regular_2x2_load_hold"]
