"""Independent adjudication of the frozen contact performance/equilibrium task."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
from typing import Any

import numpy as np

from ..runs.contact_performance_equilibrium import (
    BARRIER_RELATIVE,
    RESULT_RELATIVE,
)
from ..workspace import find_workspace


def _read_csv(path: Path) -> np.ndarray:
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _relative_scalar(first: float, second: float) -> float:
    return abs(first - second) / max(abs(first), abs(second), 1.0e-300)


def _force_error(first: np.ndarray, second: np.ndarray) -> float:
    first_force = np.column_stack([first[key] for key in ("fx", "fy", "fz")])
    second_force = np.column_stack([second[key] for key in ("fx", "fy", "fz")])
    difference = np.linalg.norm(first_force - second_force, axis=1)
    scale = np.maximum(
        np.maximum(np.linalg.norm(first_force, axis=1), np.linalg.norm(second_force, axis=1)),
        1.0e-12,
    )
    return float(np.max(difference / scale, initial=0.0))


def _balance(nodes: np.ndarray) -> tuple[float, float]:
    position = np.column_stack([nodes[key] for key in ("x", "y", "z")])
    force = np.column_stack([nodes[key] for key in ("fx", "fy", "fz")])
    force_scale = max(float(np.linalg.norm(force, axis=1).sum()), 1.0e-12)
    force_residual = float(np.linalg.norm(force.sum(axis=0)) / force_scale)
    torque = np.cross(position - position.mean(axis=0), force)
    torque_scale = max(float(np.linalg.norm(torque, axis=1).sum()), 1.0e-12)
    torque_residual = float(np.linalg.norm(torque.sum(axis=0)) / torque_scale)
    return force_residual, torque_residual


def _source_hashes_unchanged(workspace: Path, result: Path) -> bool:
    recorded = _read_json(result / "source_hashes_before.json")
    for relative, expected in recorded.items():
        path = workspace / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return False
    return True


def _verify_q(workspace: Path, result: Path) -> dict[str, Any]:
    q_root = result / "Q"
    execution = _read_json(q_root / "execution_status.json")
    ledger = _read_json(q_root / "execution_ledger.json")
    scaling = [item for item in ledger if item["kind"] == "scaling"]
    regression = [item for item in ledger if item["kind"] == "regression"]
    details: list[dict[str, Any]] = []
    gates: dict[str, bool] = {
        "raw_execution": execution.get("status") == "passed",
        "source_hashes_unchanged": _source_hashes_unchanged(workspace, result),
        "eighteen_scaling_calls": len(scaling) == 18,
        "twenty_one_regression_calls": len(regression) == 21,
    }

    medians: dict[str, dict[str, float]] = {}
    for count in (2, 4, 16):
        medians[str(count)] = {}
        for implementation in ("baseline", "candidate"):
            records = [
                item
                for item in scaling
                if item["cells"] == count and item["implementation"] == implementation
            ]
            times: list[float] = []
            for item in records:
                output = result / item["output"]
                if item["return_code"] == 0 and (output / "contact.json").is_file():
                    times.append(float(_read_json(output / "contact.json")["contact_seconds"]))
            medians[str(count)][implementation] = (
                statistics.median(times) if len(times) == 3 else float("inf")
            )

        for repetition in range(1, 4):
            pair = {
                item["implementation"]: item
                for item in scaling
                if item["cells"] == count and item["repetition"] == repetition
            }
            pair_ok = set(pair) == {"baseline", "candidate"}
            record: dict[str, Any] = {"cells": count, "repetition": repetition}
            if pair_ok:
                baseline_dir = result / pair["baseline"]["output"]
                candidate_dir = result / pair["candidate"]["output"]
                baseline_contact = _read_json(baseline_dir / "contact.json")
                candidate_contact = _read_json(candidate_dir / "contact.json")
                baseline_nodes = _read_csv(baseline_dir / "nodes.csv")
                candidate_nodes = _read_csv(candidate_dir / "nodes.csv")
                ordering = np.array_equal(baseline_nodes[["cell", "node"]], candidate_nodes[["cell", "node"]])
                force_error = _force_error(baseline_nodes, candidate_nodes) if ordering else float("inf")
                force_balance, torque_balance = _balance(candidate_nodes)
                record.update(
                    {
                        "active_samples_equal": baseline_contact["active_samples"]
                        == candidate_contact["active_samples"],
                        "energy_relative_error": _relative_scalar(
                            baseline_contact["contact_energy"], candidate_contact["contact_energy"]
                        ),
                        "support_relative_error": _relative_scalar(
                            baseline_contact["quadrature_support_area"],
                            candidate_contact["quadrature_support_area"],
                        ),
                        "force_max_relative_error": force_error,
                        "force_balance_relative": force_balance,
                        "torque_balance_relative": torque_balance,
                    }
                )
                pair_ok = (
                    record["active_samples_equal"]
                    and record["energy_relative_error"] <= 1.0e-12
                    and record["support_relative_error"] <= 1.0e-12
                    and force_error <= 1.0e-12
                    and force_balance <= 1.0e-10
                    and torque_balance <= 1.0e-10
                )
            record["passed"] = pair_ok
            details.append(record)
    gates["numerical_equivalence"] = len(details) == 9 and all(item["passed"] for item in details)
    gates["sixteen_cell_performance"] = (
        medians["16"]["baseline"] / medians["16"]["candidate"] >= 2.0
        or medians["16"]["candidate"] <= 6.075
    )
    gates["two_cell_no_material_regression"] = (
        medians["2"]["candidate"] <= 1.2 * medians["2"]["baseline"]
    )

    frozen_root = workspace / BARRIER_RELATIVE / "S"
    frozen_verdict = _read_json(frozen_root / "verdict.json")
    regression_details: list[dict[str, Any]] = []
    regression_ok = frozen_verdict.get("status") == "passed"
    for item in regression:
        case_ok = item["return_code"] == item["expected_return_code"]
        detail: dict[str, Any] = {"case": item["case"], "return_code_ok": case_ok}
        if item["expected_return_code"] == 0 and item["case"] != "geometry_self_test":
            candidate_dir = result / item["output"]
            frozen_dir = frozen_root / item["case"]
            current_contact = _read_json(candidate_dir / "contact.json")
            frozen_contact = _read_json(frozen_dir / "contact.json")
            current_nodes = _read_csv(candidate_dir / "nodes.csv")
            frozen_nodes = _read_csv(frozen_dir / "nodes.csv")
            ordering = np.array_equal(current_nodes[["cell", "node"]], frozen_nodes[["cell", "node"]])
            detail.update(
                {
                    "active_samples_equal": current_contact["active_samples"]
                    == frozen_contact["active_samples"],
                    "energy_relative_error": _relative_scalar(
                        current_contact["contact_energy"], frozen_contact["contact_energy"]
                    ),
                    "support_relative_error": _relative_scalar(
                        current_contact["quadrature_support_area"],
                        frozen_contact["quadrature_support_area"],
                    ),
                    "force_max_relative_error": _force_error(current_nodes, frozen_nodes)
                    if ordering
                    else float("inf"),
                }
            )
            case_ok = case_ok and detail["active_samples_equal"] and all(
                detail[key] <= 1.0e-12
                for key in (
                    "energy_relative_error",
                    "support_relative_error",
                    "force_max_relative_error",
                )
            )
        detail["passed"] = case_ok
        regression_details.append(detail)
        regression_ok = regression_ok and case_ok
    gates["retained_contact_regressions"] = regression_ok and len(regression_details) == 21
    status = "passed" if all(gates.values()) else "failed"
    if gates["numerical_equivalence"] and gates["retained_contact_regressions"] and not (
        gates["sixteen_cell_performance"] and gates["two_cell_no_material_regression"]
    ):
        failure_class = "failed_performance"
    elif status == "passed":
        failure_class = None
    else:
        failure_class = "failed_equivalence_or_regression"
    verdict = {
        "schema_version": "prl.contact_performance_equilibrium.q_verdict.v1",
        "status": status,
        "failure_class": failure_class,
        "gates": gates,
        "timing_medians_seconds": medians,
        "sixteen_cell_speedup": medians["16"]["baseline"] / medians["16"]["candidate"],
        "two_cell_slowdown_ratio": medians["2"]["candidate"] / medians["2"]["baseline"],
        "equivalence": details,
        "regressions": regression_details,
        "scope": "single-thread static assembly timing and numerical equivalence; not tissue dynamics",
    }
    _write_json(q_root / "verdict.json", verdict)
    return verdict


def _points(rows: np.ndarray) -> np.ndarray:
    return np.column_stack([rows[key] for key in ("x", "y", "z")])


def _adjacent_normal_minimum(points: np.ndarray, triangles: np.ndarray) -> float:
    coordinates = points[triangles]
    normals = np.cross(coordinates[:, 1] - coordinates[:, 0], coordinates[:, 2] - coordinates[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths <= 1.0e-14):
        return -1.0
    normals /= lengths[:, None]
    edge_owner: dict[tuple[int, int], int] = {}
    pairs: list[tuple[int, int]] = []
    for face_id, node_ids in enumerate(triangles):
        for edge in range(3):
            key = tuple(sorted((int(node_ids[edge]), int(node_ids[(edge + 1) % 3]))))
            if key in edge_owner:
                pairs.append((edge_owner[key], face_id))
            else:
                edge_owner[key] = face_id
    return min((float(normals[first] @ normals[second]) for first, second in pairs), default=1.0)


def _mesh_metrics(points: np.ndarray, triangles: np.ndarray) -> dict[str, float]:
    coordinates = points[triangles]
    volume = float(
        np.einsum("ij,ij->i", coordinates[:, 0], np.cross(coordinates[:, 1], coordinates[:, 2])).sum()
        / 6.0
    )
    angles: list[float] = []
    for vertex in range(3):
        first = coordinates[:, (vertex + 1) % 3] - coordinates[:, vertex]
        second = coordinates[:, (vertex + 2) % 3] - coordinates[:, vertex]
        cosine = np.einsum("ij,ij->i", first, second) / (
            np.linalg.norm(first, axis=1) * np.linalg.norm(second, axis=1)
        )
        angles.append(float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))).min()))
    return {
        "volume": volume,
        "min_angle": min(angles),
        "adjacent_cosine": _adjacent_normal_minimum(points, triangles),
    }


def _nearest_distance(point: np.ndarray, triangles: np.ndarray) -> float:
    first_edge = triangles[:, 1] - triangles[:, 0]
    second_edge = triangles[:, 2] - triangles[:, 0]
    delta = point - triangles[:, 0]
    aa = np.einsum("ij,ij->i", first_edge, first_edge)
    ab = np.einsum("ij,ij->i", first_edge, second_edge)
    bb = np.einsum("ij,ij->i", second_edge, second_edge)
    da = np.einsum("ij,ij->i", delta, first_edge)
    db = np.einsum("ij,ij->i", delta, second_edge)
    denominator = aa * bb - ab * ab
    u = (bb * da - ab * db) / denominator
    v = (aa * db - ab * da) / denominator
    distances = np.full(len(triangles), np.inf)
    inside = (u >= 0) & (v >= 0) & (u + v <= 1)
    distances[inside] = np.linalg.norm(
        delta[inside] - u[inside, None] * first_edge[inside] - v[inside, None] * second_edge[inside],
        axis=1,
    )
    for edge_index in range(3):
        edge = triangles[:, (edge_index + 1) % 3] - triangles[:, edge_index]
        edge_delta = point - triangles[:, edge_index]
        fraction = np.clip(
            np.einsum("ij,ij->i", edge, edge_delta) / np.einsum("ij,ij->i", edge, edge),
            0,
            1,
        )
        distances = np.minimum(
            distances, np.linalg.norm(edge_delta - fraction[:, None] * edge, axis=1)
        )
    return float(distances.min())


def _contained_witnesses(points: np.ndarray, triangles: np.ndarray) -> int:
    selected = np.flatnonzero(
        np.all(
            (points > triangles.min(axis=(0, 1)) - 1.0e-9)
            & (points < triangles.max(axis=(0, 1)) + 1.0e-9),
            axis=1,
        )
    )
    witnesses = 0
    for index in selected:
        a, b, c = (triangles[:, vertex] - points[index] for vertex in range(3))
        la, lb, lc = (np.linalg.norm(value, axis=1) for value in (a, b, c))
        numerator = np.einsum("ij,ij->i", a, np.cross(b, c))
        denominator = (
            la * lb * lc
            + np.einsum("ij,ij->i", a, b) * lc
            + np.einsum("ij,ij->i", b, c) * la
            + np.einsum("ij,ij->i", c, a) * lb
        )
        winding = float(np.sum(2 * np.arctan2(numerator, denominator)) / (4 * np.pi))
        if abs(winding) > 0.5 and _nearest_distance(points[index], triangles) > 1.0e-8:
            witnesses += 1
    return witnesses


def _crossing_count(
    first: np.ndarray,
    second: np.ndarray,
    first_ids: np.ndarray | None = None,
    second_ids: np.ndarray | None = None,
) -> int:
    overlap = np.all(first.min(axis=1)[:, None, :] <= second.max(axis=1)[None, :, :] + 1.0e-10, axis=2)
    overlap &= np.all(second.min(axis=1)[None, :, :] <= first.max(axis=1)[:, None, :] + 1.0e-10, axis=2)
    first_index, second_index = np.where(overlap)
    if first_ids is not None and second_ids is not None:
        keep = (first_index < second_index) & ~np.any(
            first_ids[first_index, :, None] == second_ids[second_index, None, :], axis=(1, 2)
        )
        first_index, second_index = first_index[keep], second_index[keep]
    if not len(first_index):
        return 0
    first_triangles, second_triangles = first[first_index], second[second_index]
    hit = np.zeros(len(first_index), dtype=bool)
    for source, target in ((first_triangles, second_triangles), (second_triangles, first_triangles)):
        edge_one = target[:, 1] - target[:, 0]
        edge_two = target[:, 2] - target[:, 0]
        for vertex in range(3):
            start = source[:, vertex]
            direction = source[:, (vertex + 1) % 3] - start
            h = np.cross(direction, edge_two)
            determinant = np.einsum("ij,ij->i", edge_one, h)
            valid = abs(determinant) > 1.0e-12
            inverse = np.divide(1.0, determinant, out=np.zeros_like(determinant), where=valid)
            delta = start - target[:, 0]
            u = inverse * np.einsum("ij,ij->i", delta, h)
            q = np.cross(delta, edge_one)
            v = inverse * np.einsum("ij,ij->i", direction, q)
            fraction = inverse * np.einsum("ij,ij->i", edge_two, q)
            hit |= (
                valid
                & (u >= -1.0e-9)
                & (v >= -1.0e-9)
                & (u + v <= 1 + 1.0e-9)
                & (fraction > 1.0e-8)
                & (fraction < 1 - 1.0e-8)
            )
    return int(hit.sum())


def _event_witnesses(nodes: np.ndarray, faces: np.ndarray) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for snapshot in np.unique(nodes["snapshot"]):
        rows = nodes[nodes["snapshot"] == snapshot]
        coordinate = float(rows["coordinate"][0])
        if not any(abs(coordinate - event) <= 1.0e-8 for event in (0, 5, 10, 15, 20)):
            continue
        meshes = []
        for cell_id in (0, 1):
            cell_rows = rows[rows["cell"] == cell_id]
            triangles = np.column_stack(
                [faces[faces["cell"] == cell_id][key] for key in ("a", "b", "c")]
            ).astype(int)
            points = _points(cell_rows)
            meshes.append((points, triangles, points[triangles]))
        first_points, first_ids, first_triangles = meshes[0]
        second_points, second_ids, second_triangles = meshes[1]
        records.append(
            {
                "coordinate": coordinate,
                "contained_nodes": _contained_witnesses(first_points, second_triangles)
                + _contained_witnesses(second_points, first_triangles),
                "crossing_pairs": _crossing_count(first_triangles, second_triangles),
                "self_crossing_pairs": _crossing_count(
                    first_triangles, first_triangles, first_ids, first_ids
                )
                + _crossing_count(second_triangles, second_triangles, second_ids, second_ids),
            }
        )
    return records


def _verify_e(workspace: Path, result: Path) -> dict[str, Any]:
    q_verdict = _read_json(result / "Q/verdict.json")
    e_root = result / "E"
    execution = _read_json(e_root / "execution_status.json")
    ledger = _read_json(e_root / "execution_ledger.json")
    gates: dict[str, bool] = {
        "q_passed": q_verdict.get("status") == "passed",
        "four_processes_completed": execution.get("status") == "passed" and len(ledger) == 4,
        "output_within_256_mib": execution.get("output_bytes", 256 * 1024**2 + 1) <= 256 * 1024**2,
    }
    details: list[dict[str, Any]] = []
    endpoints: dict[str, np.ndarray] = {}
    safe_trajectories = True
    equilibrium = True
    for item in ledger:
        case = e_root / item["case"]
        required = ["run.json", "nodes.csv", "faces.csv", "states.csv", "cells.csv", "step_audits.csv", "separation.csv"]
        files_ok = all((case / name).is_file() for name in required)
        detail: dict[str, Any] = {"case": item["case"], "files_complete": files_ok}
        if not files_ok:
            safe_trajectories = False
            equilibrium = False
            details.append(detail)
            continue
        nodes = _read_csv(case / "nodes.csv")
        faces = _read_csv(case / "faces.csv")
        states = _read_csv(case / "states.csv")
        audits = _read_csv(case / "step_audits.csv")
        separation = _read_csv(case / "separation.csv")
        snapshots = np.unique(nodes["snapshot"])
        initial_volume: dict[int, float] = {}
        maximum_volume_error = 0.0
        minimum_angle = 180.0
        minimum_adjacent_cosine = 1.0
        finite = all(np.isfinite(nodes[key]).all() for key in nodes.dtype.names or ())
        for snapshot in snapshots:
            for cell_id in (0, 1):
                rows = nodes[(nodes["snapshot"] == snapshot) & (nodes["cell"] == cell_id)]
                triangle_ids = np.column_stack(
                    [faces[faces["cell"] == cell_id][key] for key in ("a", "b", "c")]
                ).astype(int)
                metrics = _mesh_metrics(_points(rows), triangle_ids)
                if cell_id not in initial_volume:
                    initial_volume[cell_id] = metrics["volume"]
                maximum_volume_error = max(
                    maximum_volume_error,
                    abs(metrics["volume"] / initial_volume[cell_id] - 1.0),
                )
                minimum_angle = min(minimum_angle, metrics["min_angle"])
                minimum_adjacent_cosine = min(
                    minimum_adjacent_cosine, metrics["adjacent_cosine"]
                )
        witnesses = _event_witnesses(nodes, faces)
        coordinates = sorted(float(value) for value in np.unique(nodes["coordinate"]))
        event_coordinates = all(
            any(abs(value - event) <= 1.0e-8 for value in coordinates)
            for event in (0, 5, 10, 15, 20)
        )
        final_rows = nodes[nodes["snapshot"] == snapshots[-1]]
        initial_rows = nodes[nodes["snapshot"] == snapshots[0]]
        endpoints[item["case"]] = _points(final_rows) - _points(initial_rows)
        final_force = float(states["max_free_force"][-1])
        safe = (
            finite
            and event_coordinates
            and len(witnesses) == 5
            and all(
                witness["contained_nodes"]
                + witness["crossing_pairs"]
                + witness["self_crossing_pairs"]
                == 0
                for witness in witnesses
            )
            and float(np.min(separation["intercell_distance"])) > 1.0e-8
            and maximum_volume_error <= 0.02
            and minimum_angle >= 15.0
            and minimum_adjacent_cosine > -0.95
            and float(np.max(audits["work_residual"], initial=0.0)) <= 1.0e-10
            and not np.any(nodes["fixed"])
            and len(faces) == 768
        )
        detail.update(
            {
                "passed_safety": bool(safe),
                "saved_mesh_states": len(snapshots),
                "saved_coordinates": coordinates,
                "minimum_gap": float(np.min(separation["intercell_distance"])),
                "maximum_volume_error": maximum_volume_error,
                "minimum_angle_degrees": minimum_angle,
                "minimum_adjacent_face_cosine": minimum_adjacent_cosine,
                "maximum_work_residual": float(np.max(audits["work_residual"], initial=0.0)),
                "final_max_free_force": final_force,
                "event_witnesses": witnesses,
            }
        )
        safe_trajectories = safe_trajectories and safe
        equilibrium = equilibrium and final_force <= 1.0e-3
        details.append(detail)
    gates["all_trajectories_safe"] = len(details) == 4 and safe_trajectories
    comparisons: list[dict[str, Any]] = []
    dt_agreement = True
    for direction in ("END", "SIDE"):
        coarse = endpoints.get(f"{direction}_DT0.02")
        fine = endpoints.get(f"{direction}_DT0.01")
        if coarse is None or fine is None:
            dt_agreement = False
            continue
        relative = float(np.linalg.norm(coarse - fine) / max(np.linalg.norm(fine), 1.0e-12))
        comparisons.append({"direction": direction, "displacement_relative_error": relative})
        dt_agreement = dt_agreement and relative <= 0.02
    gates["coarse_fine_agreement"] = dt_agreement and len(comparisons) == 2
    gates["static_residual"] = equilibrium and len(details) == 4
    status = "passed" if all(gates.values()) else "failed"
    if gates.get("all_trajectories_safe") and gates.get("coarse_fine_agreement") and not gates.get("static_residual"):
        failure_class = "failed_equilibrium"
    elif status == "passed":
        failure_class = None
    else:
        failure_class = "failed_safety_or_completeness"
    verdict = {
        "schema_version": "prl.contact_performance_equilibrium.e_verdict.v1",
        "status": status,
        "failure_class": failure_class,
        "gates": gates,
        "details": details,
        "comparisons": comparisons,
        "scope": "algorithmic coordinate relaxation; not physiological time or biological validation",
    }
    _write_json(e_root / "verdict.json", verdict)
    _write_json(
        result / "verdict.json",
        {
            "schema_version": "prl.contact_performance_equilibrium.verdict.v1",
            "status": status,
            "q_status": q_verdict["status"],
            "equilibrium_status": status,
            "failure_class": failure_class,
        },
    )
    return verdict


def verify_contact_performance_equilibrium(
    workspace: Path | str | None = None,
    result: Path | str | None = None,
    *,
    phase: str = "q",
) -> dict[str, Any]:
    root = find_workspace(workspace)
    target = root / RESULT_RELATIVE if result is None else Path(result)
    if not target.is_absolute():
        target = root / target
    target = target.resolve(strict=True)
    try:
        target.relative_to(root.resolve(strict=True))
    except ValueError as error:
        raise ValueError("result path must stay inside the workspace") from error
    if phase == "q":
        return _verify_q(root, target)
    if phase == "equilibrium":
        return _verify_e(root, target)
    raise ValueError(f"unknown phase: {phase}")
