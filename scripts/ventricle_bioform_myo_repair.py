"""Numerical repair primitives and v02 evidence diagnostics for myocardial bioform.

The linear-algebra routines are an executable reference specification for the
matching C++ implementation.  They do not alter the frozen v02 result package.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V02 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_a_v02_20260913"


def _as_vectors(values: np.ndarray, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 2 or result.shape[1] != 3 or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a finite N x 3 array")
    return result


def equilibrate_normal_forces(
    points: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    raw_forces: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Project normal nodal forces onto the zero-force/zero-moment subspace.

    The correction minimizes the area-integrated squared traction correction,
    while every corrected nodal force remains exactly parallel to its normal.
    """

    x = _as_vectors(points, "points")
    n = _as_vectors(normals, "normals")
    force = _as_vectors(raw_forces, "raw_forces")
    weights = np.asarray(areas, dtype=float)
    if x.shape != n.shape or x.shape != force.shape or weights.shape != (len(x),):
        raise ValueError("normal-equilibration inputs have incompatible shapes")
    if not np.isfinite(weights).all() or np.any(weights <= 0.0):
        raise ValueError("areas must be finite and positive")
    n_norm = np.linalg.norm(n, axis=1)
    if np.any(n_norm <= 0.0):
        raise ValueError("normals must be nonzero")
    n = n / n_norm[:, None]
    center = np.sum(x * weights[:, None], axis=0) / weights.sum()
    arms = x - center
    columns = np.concatenate((n, np.cross(arms, n)), axis=1)
    raw_resultant = np.concatenate((force.sum(axis=0), np.cross(arms, force).sum(axis=0)))
    gram = (columns.T * weights) @ columns
    multiplier = np.linalg.pinv(gram, rcond=1.0e-13) @ raw_resultant
    scalar_correction = -weights * (columns @ multiplier)
    corrected = force + n * scalar_correction[:, None]
    net_force = corrected.sum(axis=0)
    net_moment = np.cross(arms, corrected).sum(axis=0)
    force_scale = float(np.linalg.norm(corrected, axis=1).sum())
    moment_scale = float(np.linalg.norm(np.cross(arms, corrected), axis=1).sum())
    characteristic_length = math.sqrt(float(np.sum(weights * np.sum(arms * arms, axis=1)) / weights.sum()))
    residual_floor = max(characteristic_length * force_scale, 1.0)
    return corrected, {
        "net_force_norm": float(np.linalg.norm(net_force)),
        "net_moment_norm": float(np.linalg.norm(net_moment)),
        "relative_force_residual": float(np.linalg.norm(net_force)) / max(force_scale, 1.0e-30),
        "relative_moment_residual": float(np.linalg.norm(net_moment)) / max(moment_scale, residual_floor * 1.0e-15, 1.0e-30),
        "constraint_rank": float(np.linalg.matrix_rank(gram, tol=1.0e-12)),
        "correction_l2_norm": float(np.linalg.norm(scalar_correction)),
    }


def remove_rigid_velocity(
    points: np.ndarray,
    areas: np.ndarray,
    velocities: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Remove the area-weighted best-fit rigid translation and rotation."""

    x = _as_vectors(points, "points")
    velocity = _as_vectors(velocities, "velocities")
    weights = np.asarray(areas, dtype=float)
    if x.shape != velocity.shape or weights.shape != (len(x),):
        raise ValueError("rigid-velocity inputs have incompatible shapes")
    if not np.isfinite(weights).all() or np.any(weights <= 0.0):
        raise ValueError("areas must be finite and positive")
    center = np.sum(x * weights[:, None], axis=0) / weights.sum()
    arms = x - center
    translation = np.sum(velocity * weights[:, None], axis=0) / weights.sum()
    inertia = np.zeros((3, 3), dtype=float)
    angular_rhs = np.zeros(3, dtype=float)
    for arm, current_velocity, weight in zip(arms, velocity, weights, strict=True):
        inertia += weight * (float(np.dot(arm, arm)) * np.eye(3) - np.outer(arm, arm))
        angular_rhs += weight * np.cross(arm, current_velocity - translation)
    omega = np.linalg.pinv(inertia, rcond=1.0e-13) @ angular_rhs
    rigid = translation + np.cross(np.broadcast_to(omega, arms.shape), arms)
    shape = velocity - rigid
    translation_residual = np.sum(shape * weights[:, None], axis=0)
    rotation_residual = np.sum(np.cross(arms, shape) * weights[:, None], axis=0)
    return shape, {
        "translation_speed": float(np.linalg.norm(translation)),
        "angular_speed": float(np.linalg.norm(omega)),
        "weighted_translation_residual": float(np.linalg.norm(translation_residual)),
        "weighted_rotation_residual": float(np.linalg.norm(rotation_residual)),
    }


def choose_adaptive_step(
    *,
    requested_step: float,
    remaining_step: float,
    minimum_edge_length: float,
    maximum_speed: float,
    displacement_fraction: float,
) -> float:
    values = (requested_step, remaining_step, minimum_edge_length, displacement_fraction)
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("step, remaining interval, edge length, and fraction must be positive")
    if not math.isfinite(maximum_speed) or maximum_speed < 0.0:
        raise ValueError("maximum speed must be finite and nonnegative")
    motion_limited = math.inf if maximum_speed == 0.0 else displacement_fraction * minimum_edge_length / maximum_speed
    accepted = min(requested_step, remaining_step, motion_limited)
    if not math.isfinite(accepted) or accepted <= 0.0:
        raise ValueError("adaptive step is not finite and positive")
    return accepted


def _rows_by_snapshot(path: Path) -> dict[int, list[dict[str, str]]]:
    result: dict[int, list[dict[str, str]]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            result.setdefault(int(row["snapshot_index"]), []).append(row)
    return result


def _snapshot_force_audit(node_rows: list[dict[str, str]], face_rows: list[dict[str, str]]) -> dict[str, Any]:
    node_ids = [int(row["node_index"]) for row in node_rows]
    lookup = {node_id: index for index, node_id in enumerate(node_ids)}
    points = np.asarray([[float(row[key]) for key in ("x", "y", "z")] for row in node_rows])
    areas = np.zeros(len(points), dtype=float)
    normal_accumulator = np.zeros_like(points)
    for row in face_rows:
        ids = [int(row[key]) for key in ("n1", "n2", "n3")]
        indices = [lookup[node_id] for node_id in ids]
        a, b, c = points[indices]
        area_vector = 0.5 * np.cross(b - a, c - a)
        area = float(np.linalg.norm(area_vector))
        for index in indices:
            areas[index] += area / 3.0
            normal_accumulator[index] += area_vector
    normal_lengths = np.linalg.norm(normal_accumulator, axis=1)
    normals = normal_accumulator / normal_lengths[:, None]
    center = np.sum(points * areas[:, None], axis=0) / areas.sum()
    arms = points - center

    def field(prefix: str) -> np.ndarray:
        return np.asarray([[float(row[f"{prefix}_{axis}"]) for axis in ("fx", "fy", "fz")] for row in node_rows])

    payload: dict[str, Any] = {
        "snapshot_index": int(node_rows[0]["snapshot_index"]),
        "solver_coordinate": float(node_rows[0]["solver_coordinate"]),
        "face_count": len(face_rows),
        "center_norm": float(np.linalg.norm(center)),
    }
    for label, prefix in (("passive", "passive"), ("cytoskeleton", "cytoskeleton"), ("total", "total")):
        forces = field(prefix)
        resultant = forces.sum(axis=0)
        moment = np.cross(arms, forces).sum(axis=0)
        payload[f"{label}_net_force_norm"] = float(np.linalg.norm(resultant))
        payload[f"{label}_net_moment_norm"] = float(np.linalg.norm(moment))
        payload[f"{label}_force_l1_scale"] = float(np.linalg.norm(forces, axis=1).sum())
        if label == "cytoskeleton":
            normal_part = normals * np.sum(forces * normals, axis=1)[:, None]
            payload["cytoskeleton_tangent_l2_fraction"] = float(
                np.linalg.norm(forces - normal_part) / max(np.linalg.norm(forces), 1.0e-30)
            )
    return payload


def diagnose_v02(result_root: Path = DEFAULT_V02) -> dict[str, Any]:
    raw_root = result_root / "raw"
    conditions: dict[str, Any] = {}
    for condition_dir in sorted(path for path in raw_root.iterdir() if path.is_dir()):
        node_path = condition_dir / "nodes.csv"
        face_path = condition_dir / "faces.csv"
        audit_path = condition_dir / "step_audits.csv"
        if not node_path.is_file() or not face_path.is_file():
            continue
        node_groups = _rows_by_snapshot(node_path)
        face_groups = _rows_by_snapshot(face_path)
        snapshots = [
            _snapshot_force_audit(node_groups[index], face_groups[index])
            for index in sorted(set(node_groups) & set(face_groups))
        ]
        step_summary: dict[str, Any] = {}
        if audit_path.is_file():
            with audit_path.open("r", encoding="utf-8", newline="") as stream:
                audit_rows = list(csv.DictReader(stream))
            if audit_rows:
                force_values = np.asarray([float(row["total_force_l2"]) for row in audit_rows])
                area_values = np.asarray([float(row["minimum_face_area"]) for row in audit_rows])
                displacement_values = np.asarray([float(row["displacement_l2"]) for row in audit_rows])
                last = audit_rows[-1]
                step_summary = {
                    "completed_steps": len(audit_rows),
                    "last_step": int(last["step"]),
                    "last_solver_coordinate": float(last["solver_coordinate"]),
                    "peak_total_force_l2": float(force_values.max()),
                    "peak_displacement_l2": float(displacement_values.max()),
                    "minimum_step_face_area": float(area_values.min()),
                    "last_total_force_l2": float(force_values[-1]),
                    "last_displacement_l2": float(displacement_values[-1]),
                    "last_minimum_face_area": float(area_values[-1]),
                }
        conditions[condition_dir.name] = {"snapshots": snapshots, "step_summary": step_summary}
    return {
        "schema_version": 1,
        "source_result": str(result_root.resolve()),
        "diagnostic_status": "evidence_only_not_a_scientific_verdict",
        "conditions": conditions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_V02)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    payload = diagnose_v02(arguments.input.resolve())
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is not None:
        output = arguments.output.resolve()
        if output.exists():
            raise SystemExit("create-only diagnostic output already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
