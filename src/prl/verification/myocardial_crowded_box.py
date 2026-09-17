"""Independent checks for the retained 5x5 myocardial crowding pilot."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _gate(value: object, passed: bool, criterion: str) -> dict[str, object]:
    return {"value": value, "criterion": criterion, "passed": bool(passed)}


def _mesh_measures(points: np.ndarray, faces: np.ndarray) -> tuple[float, float]:
    triangles = points[faces]
    signed_volume = float(
        np.einsum(
            "ij,ij->i",
            triangles[:, 0],
            np.cross(triangles[:, 1], triangles[:, 2]),
        ).sum()
        / 6.0
    )
    vectors = np.stack(
        (
            triangles[:, 1] - triangles[:, 0],
            triangles[:, 2] - triangles[:, 1],
            triangles[:, 0] - triangles[:, 2],
        ),
        axis=1,
    )
    lengths = np.linalg.norm(vectors, axis=2)
    minimum_angle = 180.0
    for vertex in range(3):
        first = -vectors[:, (vertex - 1) % 3]
        second = vectors[:, vertex]
        cosine = np.einsum("ij,ij->i", first, second) / (
            np.linalg.norm(first, axis=1) * np.linalg.norm(second, axis=1)
        )
        angles = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        minimum_angle = min(minimum_angle, float(angles.min()))
    if float(lengths.min()) <= 0.0:
        minimum_angle = 0.0
    return signed_volume, minimum_angle


def _segment_triangle_hits(
    first: np.ndarray, second: np.ndarray, triangle: np.ndarray
) -> bool:
    direction = second - first
    edge_first = triangle[1] - triangle[0]
    edge_second = triangle[2] - triangle[0]
    h = np.cross(direction, edge_second)
    determinant = float(np.dot(edge_first, h))
    scale = (
        float(np.linalg.norm(direction))
        * float(np.linalg.norm(edge_first))
        * float(np.linalg.norm(edge_second))
    )
    if abs(determinant) <= 1.0e-11 * max(scale, 1.0e-30):
        return False
    inverse = 1.0 / determinant
    offset = first - triangle[0]
    u = inverse * float(np.dot(offset, h))
    if u < -1.0e-10 or u > 1.0 + 1.0e-10:
        return False
    q = np.cross(offset, edge_first)
    v = inverse * float(np.dot(direction, q))
    if v < -1.0e-10 or u + v > 1.0 + 1.0e-10:
        return False
    parameter = inverse * float(np.dot(edge_second, q))
    return -1.0e-10 <= parameter <= 1.0 + 1.0e-10


def _triangle_pair_intersects(first: np.ndarray, second: np.ndarray) -> bool:
    for edge in range(3):
        if _segment_triangle_hits(first[edge], first[(edge + 1) % 3], second):
            return True
        if _segment_triangle_hits(second[edge], second[(edge + 1) % 3], first):
            return True
    return False


def _candidate_intersection_count(
    first_points: np.ndarray,
    first_faces: np.ndarray,
    second_points: np.ndarray,
    second_faces: np.ndarray,
    *,
    same_mesh: bool,
) -> int:
    first_triangles = first_points[first_faces]
    second_triangles = second_points[second_faces]
    first_centers = first_triangles.mean(axis=1)
    second_centers = second_triangles.mean(axis=1)
    first_radii = np.linalg.norm(
        first_triangles - first_centers[:, None, :], axis=2
    ).max(axis=1)
    second_radii = np.linalg.norm(
        second_triangles - second_centers[:, None, :], axis=2
    ).max(axis=1)
    tree = cKDTree(second_centers)
    maximum_second_radius = float(second_radii.max())
    intersections = 0
    for first_id, (center, radius) in enumerate(
        zip(first_centers, first_radii, strict=True)
    ):
        candidates = tree.query_ball_point(center, float(radius + maximum_second_radius))
        for second_id in candidates:
            if same_mesh:
                if second_id <= first_id:
                    continue
                if np.intersect1d(
                    first_faces[first_id], second_faces[second_id], assume_unique=True
                ).size:
                    continue
            center_distance = float(
                np.linalg.norm(center - second_centers[second_id])
            )
            if center_distance > float(radius + second_radii[second_id]):
                continue
            if _triangle_pair_intersects(
                first_triangles[first_id], second_triangles[second_id]
            ):
                intersections += 1
    return intersections


def _snapshot_meshes(
    node_rows: list[dict[str, str]],
    face_rows: list[dict[str, str]],
    snapshot: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    result: list[tuple[np.ndarray, np.ndarray]] = []
    for cell_id in range(25):
        selected_nodes = sorted(
            (
                row
                for row in node_rows
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        selected_faces = sorted(
            (
                row
                for row in face_rows
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["face_local_id"]),
        )
        points = np.asarray(
            [[float(row[axis]) for axis in ("x", "y", "z")] for row in selected_nodes],
            dtype=float,
        )
        faces = np.asarray(
            [[int(row[key]) for key in ("n1", "n2", "n3")] for row in selected_faces],
            dtype=int,
        )
        result.append((points, faces))
    return result


def verify_myocardial_crowded_box(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    required = [
        result / "configuration.json",
        result / "execution.json",
        result / "heterogeneity.csv",
        result / "box_schedule.csv",
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

    configuration = json.loads(
        (result / "configuration.json").read_text(encoding="utf-8")
    )
    execution = json.loads((result / "execution.json").read_text(encoding="utf-8"))
    kernel = json.loads(
        (result / "raw/kernel_metrics.json").read_text(encoding="utf-8")
    )
    states = sorted(
        _read_csv(result / "raw/state_metrics.csv"),
        key=lambda row: int(row["snapshot_index"]),
    )
    cells = _read_csv(result / "raw/cell_metrics.csv")
    nodes = _read_csv(result / "raw/nodes.csv")
    faces = _read_csv(result / "raw/faces.csv")
    heterogeneity = _read_csv(result / "heterogeneity.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in nodes})
    if snapshots != list(range(9)) or len(states) != 9:
        return {
            "status": "failed",
            "reason": "incomplete retained state sequence",
            "snapshots": snapshots,
            "state_rows": len(states),
        }

    maximum_recomputed_volume_error = 0.0
    minimum_recomputed_angle = 180.0
    minimum_recomputed_wall_clearance = float("inf")
    independent_intersections = 0
    initial_shapes: list[np.ndarray] | None = None
    final_nonrigid_rms: list[float] = []
    target_volumes = {
        int(row["cell_id"]): float(row["target_volume"])
        for row in cells
        if int(row["snapshot_index"]) == 0
    }
    for snapshot, state in zip(snapshots, states, strict=True):
        meshes = _snapshot_meshes(nodes, faces, snapshot)
        if any(points.shape != (162, 3) or triangles.shape != (320, 3) for points, triangles in meshes):
            return {
                "status": "failed",
                "reason": "wrong retained mesh dimensions",
                "snapshot": snapshot,
            }
        bounds = np.asarray(
            [float(state[name]) for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")]
        )
        for cell_id, (points, triangles) in enumerate(meshes):
            signed_volume, angle = _mesh_measures(points, triangles)
            maximum_recomputed_volume_error = max(
                maximum_recomputed_volume_error,
                abs(signed_volume - target_volumes[cell_id]) / target_volumes[cell_id],
            )
            minimum_recomputed_angle = min(minimum_recomputed_angle, angle)
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
            minimum_recomputed_wall_clearance = min(
                minimum_recomputed_wall_clearance, float(clearances.min())
            )
            independent_intersections += _candidate_intersection_count(
                points, triangles, points, triangles, same_mesh=True
            )
        for first_cell in range(25):
            first_points, first_faces = meshes[first_cell]
            for second_cell in range(first_cell + 1, 25):
                second_points, second_faces = meshes[second_cell]
                separated_axis = any(
                    float(first_points[:, axis].max()) < float(second_points[:, axis].min())
                    or float(second_points[:, axis].max()) < float(first_points[:, axis].min())
                    for axis in range(3)
                )
                if not separated_axis:
                    independent_intersections += _candidate_intersection_count(
                        first_points,
                        first_faces,
                        second_points,
                        second_faces,
                        same_mesh=False,
                    )
        centered = [points - points.mean(axis=0) for points, _ in meshes]
        if initial_shapes is None:
            initial_shapes = centered
        if snapshot == snapshots[-1]:
            final_nonrigid_rms = [
                float(np.sqrt(np.mean(np.sum((current - initial) ** 2, axis=1))))
                for current, initial in zip(centered, initial_shapes, strict=True)
            ]

    final_state = states[-1]
    initial_state = states[0]
    contraction_maximum = max(float(row["contraction_traction"]) for row in nodes)
    initial_area = float(initial_state["box_planar_area"])
    final_area = float(final_state["box_planar_area"])
    area_ratio = final_area / initial_area
    occupancy_change = float(final_state["projected_occupancy"]) - float(
        initial_state["projected_occupancy"]
    )
    reported_minimum_separation = min(
        float(row["min_intercell_separation"]) for row in states
    )
    reported_minimum_nonincident = min(
        float(row["min_nonincident_separation"]) for row in states
    )
    final_force = float(final_state["max_free_force"])
    mechanics_variation = max(
        float(np.std([float(row[column]) for row in heterogeneity]))
        for column in (
            "bulk_modulus_factor",
            "surface_tension_factor",
            "area_modulus_factor",
            "prestress_factor",
        )
    )
    shape_variation = max(
        float(np.std([float(row[column]) for row in heterogeneity]))
        for column in (
            "length_scale",
            "width_scale",
            "thickness_scale",
            "side_wave_amplitude",
            "rotation_deg",
        )
    )

    gates = {
        "execution_completed": _gate(
            execution.get("return_code"),
            execution.get("return_code") == 0,
            "single solver invocation return_code == 0",
        ),
        "saved_states": _gate(len(states), len(states) == 9, "exactly 9 solver states"),
        "twenty_five_cells": _gate(
            len(cells), len(cells) == 25 * 9, "25 cells at each of 9 states"
        ),
        "contraction_disabled": _gate(
            contraction_maximum,
            configuration.get("contraction_enabled") is False
            and contraction_maximum <= 1.0e-15,
            "active contraction disabled and maximum contraction traction <= 1e-15",
        ),
        "material_junctions_disabled": _gate(
            configuration.get("material_junctions_enabled"),
            configuration.get("material_junctions_enabled") is False,
            "no permanent intercell material links",
        ),
        "box_planar_compression": _gate(
            area_ratio,
            abs(area_ratio - 0.95**2) <= 1.0e-10,
            "final planar box area / initial area == 0.95^2",
        ),
        "occupancy_increased": _gate(
            occupancy_change, occupancy_change > 0.0, "projected occupancy increases"
        ),
        "contact_engaged": _gate(
            int(final_state["contact_active_cell_pairs"]),
            max(int(row["contact_active_cell_pairs"]) for row in states) > 0,
            "at least one active cell pair is resolved",
        ),
        "reported_surface_separation": _gate(
            reported_minimum_separation,
            reported_minimum_separation > 1.0e-8,
            "saved-state full triangle intercell separation > 1e-8",
        ),
        "reported_self_separation": _gate(
            reported_minimum_nonincident,
            reported_minimum_nonincident > 1.0e-8,
            "saved-state nonincident self separation > 1e-8",
        ),
        "independent_intersection_screen": _gate(
            independent_intersections,
            independent_intersections == 0,
            "independent broad-phase plus segment-triangle screen finds zero intersections",
        ),
        "independent_wall_clearance": _gate(
            minimum_recomputed_wall_clearance,
            minimum_recomputed_wall_clearance >= -1.0e-6,
            "recomputed wall clearance >= -1e-6",
        ),
        "independent_volume": _gate(
            maximum_recomputed_volume_error,
            maximum_recomputed_volume_error <= 0.02,
            "recomputed maximum relative volume error <= 2%",
        ),
        "independent_mesh_angle": _gate(
            minimum_recomputed_angle,
            minimum_recomputed_angle >= 15.0,
            "recomputed minimum triangle angle >= 15 degrees",
        ),
        "work_dissipation": _gate(
            float(kernel["maximum_work_relative_residual"]),
            float(kernel["maximum_work_relative_residual"]) <= 1.0e-10,
            "maximum work-dissipation relative residual <= 1e-10",
        ),
        "shape_input_variation": _gate(
            shape_variation, shape_variation > 1.0e-6, "nonzero fixed cellwise shape variation"
        ),
        "mechanics_input_variation": _gate(
            mechanics_variation,
            mechanics_variation > 1.0e-6,
            "nonzero fixed cellwise mechanics variation",
        ),
        "measurable_shape_response": _gate(
            float(np.mean(final_nonrigid_rms)),
            float(np.mean(final_nonrigid_rms)) > 1.0e-4,
            "mean centroid-removed nodal RMS change > 1e-4",
        ),
    }
    failures = [name for name, gate in gates.items() if not gate["passed"]]
    static_equilibrium = "passed" if final_force <= 1.0e-3 else "failed"
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-BOX-PILOT-A",
        "status": "passed" if not failures else "failed",
        "failed_gates": failures,
        "gates": gates,
        "static_equilibrium": static_equilibrium,
        "terminal": {
            "snapshot": snapshots[-1],
            "max_free_force": final_force,
            "box_planar_area_ratio": area_ratio,
            "projected_occupancy_initial": float(initial_state["projected_occupancy"]),
            "projected_occupancy_final": float(final_state["projected_occupancy"]),
            "contact_active_cell_pairs": int(final_state["contact_active_cell_pairs"]),
            "total_wall_reaction": float(final_state["total_wall_reaction"]),
            "minimum_intercell_separation": float(final_state["min_intercell_separation"]),
            "mean_nonrigid_rms_change": float(np.mean(final_nonrigid_rms)),
            "nonrigid_rms_change_range": [
                float(np.min(final_nonrigid_rms)),
                float(np.max(final_nonrigid_rms)),
            ],
        },
        "claim_boundary": {
            "numerical_saved_state_safety": "qualified only if status is passed",
            "static_equilibrium": static_equilibrium,
            "biological_validation": "not_run",
            "contraction": "not_run",
            "contact_resolution": "exploratory 0.40 maximum-edge quadrature",
            "heterogeneity": "synthetic fixed sensitivity inputs",
        },
    }

