"""Shared, independent readers and geometry metrics for Z1-BIOFORM-MYO-A."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_VOLUME = 167.875410364543
EQUIVALENT_RADIUS = (3.0 * TARGET_VOLUME / (4.0 * math.pi)) ** (1.0 / 3.0)

CONDITION_MATRIX = [
    {"id": "FULL_M320_DT020", "mode": "FULL", "faces": 320, "dt": 0.020},
    {"id": "ABLATION_M320_DT020", "mode": "ABLATION", "faces": 320, "dt": 0.020},
    {"id": "PERTURBED_M320_DT020", "mode": "PERTURBED", "faces": 320, "dt": 0.020},
    {"id": "ROTATED37_M320_DT020", "mode": "ROTATED37", "faces": 320, "dt": 0.020},
    {"id": "FULL_M080_DT020", "mode": "FULL", "faces": 80, "dt": 0.020},
    {"id": "FULL_M1280_DT020", "mode": "FULL", "faces": 1280, "dt": 0.020},
    {"id": "FULL_M320_DT040", "mode": "FULL", "faces": 320, "dt": 0.040},
    {"id": "FULL_M320_DT010", "mode": "FULL", "faces": 320, "dt": 0.010},
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_grouped_csv(path: Path, key: str = "snapshot_index") -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, str]]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            grouped.setdefault(int(row[key]), []).append(row)
    return grouped


def load_condition(condition_dir: Path) -> tuple[dict[str, Any], dict[int, list[dict[str, str]]], dict[int, list[dict[str, str]]]]:
    kernel = load_json(condition_dir / "kernel_metrics.json")
    nodes = _read_grouped_csv(condition_dir / "nodes.csv")
    faces = _read_grouped_csv(condition_dir / "faces.csv")
    if sorted(nodes) != list(range(9)) or sorted(faces) != list(range(9)):
        raise ValueError(f"{condition_dir}: expected snapshots 0..8")
    return kernel, nodes, faces


def _triangle_minimum_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    lengths = np.array(
        [np.linalg.norm(b - c), np.linalg.norm(a - c), np.linalg.norm(a - b)],
        dtype=float,
    )
    angles = []
    for corner in range(3):
        adjacent_1 = lengths[(corner + 1) % 3]
        adjacent_2 = lengths[(corner + 2) % 3]
        opposite = lengths[corner]
        denominator = 2.0 * adjacent_1 * adjacent_2
        if denominator <= 0.0:
            return 0.0
        cosine = np.clip(
            (adjacent_1**2 + adjacent_2**2 - opposite**2) / denominator,
            -1.0,
            1.0,
        )
        angles.append(math.degrees(math.acos(float(cosine))))
    return min(angles)


def snapshot_geometry(
    node_rows: list[dict[str, str]],
    face_rows: list[dict[str, str]],
    axes: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> dict[str, Any]:
    node_ids = [int(row["node_index"]) for row in node_rows]
    points = np.array([[float(row[name]) for name in ("x", "y", "z")] for row in node_rows])
    positions = {node_id: points[index] for index, node_id in enumerate(node_ids)}
    point_lookup = {node_id: index for index, node_id in enumerate(node_ids)}
    nodal_areas = np.zeros(len(points), dtype=float)
    edge_counts: dict[tuple[int, int], int] = {}
    total_area = 0.0
    signed_volume = 0.0
    minimum_angle = math.inf
    valid_face_count = 0

    for row in face_rows:
        ids = [int(row[name]) for name in ("n1", "n2", "n3")]
        if any(node_id not in positions for node_id in ids):
            raise ValueError(f"face references missing node: {ids}")
        a, b, c = (positions[node_id] for node_id in ids)
        cross_value = np.cross(b - a, c - a)
        face_area = 0.5 * float(np.linalg.norm(cross_value))
        total_area += face_area
        signed_volume += float(np.dot(a, np.cross(b, c))) / 6.0
        minimum_angle = min(minimum_angle, _triangle_minimum_angle(a, b, c))
        for node_id in ids:
            nodal_areas[point_lookup[node_id]] += face_area / 3.0
        for first, second in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
        valid_face_count += 1

    weight_sum = float(nodal_areas.sum())
    if not (weight_sum > 0.0):
        raise ValueError("non-positive nodal area sum")
    center = np.sum(points * nodal_areas[:, None], axis=0) / weight_sum
    centered = points - center
    covariance = (centered * nodal_areas[:, None]).T @ centered / weight_sum
    p_axis, q_axis, r_axis = axes
    variances = [float(axis @ covariance @ axis) for axis in axes]
    if min(variances) <= 0.0:
        raise ValueError("non-positive directional variance")
    e_pq = math.sqrt(variances[0] / variances[1])
    f_qr = math.sqrt(variances[1] / variances[2])
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    major_axis = eigenvectors[:, int(np.argmax(eigenvalues))]
    major_axis_angle = math.degrees(
        math.acos(float(np.clip(abs(np.dot(major_axis, p_axis)), 0.0, 1.0)))
    )
    extents = [2.0 * float(np.max(np.abs(centered @ axis))) for axis in axes]
    closed_manifold = bool(edge_counts) and all(count == 2 for count in edge_counts.values())
    euler_characteristic = len(points) - len(edge_counts) + valid_face_count
    numeric_fields = [
        "x", "y", "z", "nodal_area", "curvature", "internal_pressure",
        "passive_fx", "passive_fy", "passive_fz", "cytoskeleton_fx",
        "cytoskeleton_fy", "cytoskeleton_fz", "total_fx", "total_fy",
        "total_fz", "cytoskeleton_traction", "total_traction",
    ]
    finite_fields = all(
        math.isfinite(float(row[field])) for row in node_rows for field in numeric_fields
    )
    return {
        "snapshot_index": int(node_rows[0]["snapshot_index"]),
        "phase": node_rows[0]["phase"],
        "solver_coordinate": float(node_rows[0]["solver_coordinate"]),
        "load_fraction": float(node_rows[0]["load_fraction"]),
        "relaxation_fraction": float(node_rows[0]["relaxation_fraction"]),
        "node_count": len(points),
        "face_count": valid_face_count,
        "edge_count": len(edge_counts),
        "surface_area": total_area,
        "signed_volume": signed_volume,
        "volume": abs(signed_volume),
        "volume_relative_error": abs(abs(signed_volume) - TARGET_VOLUME) / TARGET_VOLUME,
        "minimum_triangle_angle_deg": minimum_angle,
        "closed_manifold": closed_manifold,
        "euler_characteristic": euler_characteristic,
        "sphere_topology": closed_manifold and euler_characteristic == 2,
        "finite_fields": finite_fields,
        "center": center.tolist(),
        "covariance": covariance.tolist(),
        "E_pq": e_pq,
        "F_qr": f_qr,
        "axis_extents": {"p": extents[0], "q": extents[1], "r": extents[2]},
        "major_axis_angle_to_p_deg": major_axis_angle,
        "curvature_range": [
            min(float(row["curvature"]) for row in node_rows),
            max(float(row["curvature"]) for row in node_rows),
        ],
        "pressure_range": [
            min(float(row["internal_pressure"]) for row in node_rows),
            max(float(row["internal_pressure"]) for row in node_rows),
        ],
    }


def condition_metrics(condition_dir: Path) -> dict[str, Any]:
    kernel, node_groups, face_groups = load_condition(condition_dir)
    axes = tuple(np.asarray(kernel[name], dtype=float) for name in ("long_axis", "transverse_axis", "thickness_axis"))
    snapshots = [snapshot_geometry(node_groups[index], face_groups[index], axes) for index in range(9)]
    return {
        "condition": kernel["condition"],
        "kernel": kernel,
        "snapshots": snapshots,
        "final": snapshots[-1],
        "max_saved_volume_relative_error": max(item["volume_relative_error"] for item in snapshots),
        "minimum_saved_triangle_angle_deg": min(item["minimum_triangle_angle_deg"] for item in snapshots),
        "all_saved_states_finite": all(item["finite_fields"] for item in snapshots),
        "all_saved_states_sphere_topology": all(item["sphere_topology"] for item in snapshots),
    }


def relative_difference(first: float, second: float) -> float:
    return abs(first - second) / max(abs(first), 1.0e-30)


def final_points(condition_dir: Path, inverse_rotation_degrees: float = 0.0) -> np.ndarray:
    _, node_groups, _ = load_condition(condition_dir)
    rows = node_groups[8]
    points = np.array([[float(row[name]) for name in ("x", "y", "z")] for row in rows])
    if inverse_rotation_degrees:
        angle = math.radians(-inverse_rotation_degrees)
        cosine, sine = math.cos(angle), math.sin(angle)
        rotation = np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])
        points = points @ rotation.T
    return points - points.mean(axis=0)


def symmetric_chamfer_rms(first: np.ndarray, second: np.ndarray) -> float:
    first_distances = cKDTree(second).query(first, k=1)[0]
    second_distances = cKDTree(first).query(second, k=1)[0]
    return math.sqrt(
        0.5 * (float(np.mean(first_distances**2)) + float(np.mean(second_distances**2)))
    )
