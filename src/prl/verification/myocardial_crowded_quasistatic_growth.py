"""Independent verification for quasistatic crowded myocardial growth."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from .myocardial_crowded_box import (
    _candidate_intersection_count,
    _mesh_measures,
    _read_csv,
    _snapshot_meshes,
)
from .myocardial_crowded_target_pair import _gate, _grid_pairs


CONDITIONS = ("QS_COARSE_K30", "QS_REFINED_K30", "QS_REFINED_K15")
EXPECTED_FRACTIONS = np.asarray(
    [0.5, 0.625, 0.75, 0.875, 1.0, 1.0, 1.0, 1.0, 1.0]
)
VOLUME_SCALE = 2.0
AREA_SCALE = VOLUME_SCALE ** (2.0 / 3.0)


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="ascii") as stream:
        return list(csv.DictReader(stream))


def _execution(result: Path, condition: str) -> dict[str, object]:
    path = result / f"execution_{condition}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _final_rows(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(path)
    snapshot = max(int(row["snapshot_index"]) for row in rows)
    return sorted(
        (row for row in rows if int(row["snapshot_index"]) == snapshot),
        key=lambda row: int(row["cell_id"]),
    )


def _final_pairs(path: Path) -> set[tuple[int, int]]:
    rows = _read_csv(path)
    if not rows:
        return set()
    snapshot = max(int(row["snapshot_index"]) for row in rows)
    return {
        tuple(sorted((int(row["cell_a"]), int(row["cell_b"]))))
        for row in rows
        if int(row["snapshot_index"]) == snapshot
    }


def _quick_completed(result: Path, condition: str) -> bool:
    raw = result / "raw" / condition
    required = [
        raw / "kernel_metrics.json",
        raw / "state_metrics.csv",
        raw / "cell_metrics.csv",
        raw / "contact_pairs.csv",
    ]
    if _execution(result, condition).get("return_code") != 0 or any(
        not path.is_file() for path in required
    ):
        return False
    states = _read_csv(raw / "state_metrics.csv")
    if len(states) != 9:
        return False
    return all(
        float(row["min_intercell_separation"]) > 1.0e-8
        and float(row["min_nonincident_separation"]) > 1.0e-8
        and float(row["min_triangle_height"]) > 1.0e-8
        and float(row["min_triangle_angle_deg"]) >= 15.0
        and float(row["min_wall_clearance"]) >= -1.0e-6
        for row in states
    )


def _relative_difference(coarse: float, refined: float, floor: float = 0.0) -> float:
    return abs(coarse - refined) / max(abs(refined), floor, np.finfo(float).tiny)


def _rms_difference(
    coarse: np.ndarray, refined: np.ndarray, *, component_floor: float = 0.0
) -> float:
    numerator = float(np.linalg.norm(coarse - refined))
    denominator = max(
        float(np.linalg.norm(refined)),
        math.sqrt(refined.size) * component_floor,
        np.finfo(float).tiny,
    )
    return numerator / denominator


def evaluate_numerical_convergence(result: Path) -> dict[str, object]:
    """Evaluate the frozen coarse/refined gate without running a solver."""

    result = result.resolve(strict=True)
    coarse_name, refined_name = CONDITIONS[:2]
    if not all(_quick_completed(result, name) for name in (coarse_name, refined_name)):
        return {
            "status": "failed",
            "reason": "both K30 controls must complete nine safe retained states",
        }
    coarse_raw = result / "raw" / coarse_name
    refined_raw = result / "raw" / refined_name
    coarse_state = _read_csv(coarse_raw / "state_metrics.csv")[-1]
    refined_state = _read_csv(refined_raw / "state_metrics.csv")[-1]
    coarse_cells = _final_rows(coarse_raw / "cell_metrics.csv")
    refined_cells = _final_rows(refined_raw / "cell_metrics.csv")
    global_values: dict[str, float] = {}
    for metric in ("projected_occupancy",):
        global_values[metric] = _relative_difference(
            float(coarse_state[metric]), float(refined_state[metric])
        )
    for metric in ("volume", "pressure", "x_span", "y_span", "z_span"):
        coarse = np.asarray([float(row[metric]) for row in coarse_cells])
        refined = np.asarray([float(row[metric]) for row in refined_cells])
        floor = 1.0 if metric == "pressure" else 0.0
        global_values[f"mean_{metric}"] = _relative_difference(
            float(coarse.mean()), float(refined.mean()), floor
        )
    global_values["total_volume"] = _relative_difference(
        sum(float(row["volume"]) for row in coarse_cells),
        sum(float(row["volume"]) for row in refined_cells),
    )

    cellwise_values: dict[str, float] = {}
    for metric in ("volume", "pressure", "x_span", "y_span", "z_span"):
        coarse = np.asarray([float(row[metric]) for row in coarse_cells])
        refined = np.asarray([float(row[metric]) for row in refined_cells])
        cellwise_values[metric] = _rms_difference(
            coarse, refined, component_floor=1.0 if metric == "pressure" else 0.0
        )

    coarse_pairs = _final_pairs(coarse_raw / "contact_pairs.csv")
    refined_pairs = _final_pairs(refined_raw / "contact_pairs.csv")
    union = coarse_pairs | refined_pairs
    jaccard = len(coarse_pairs & refined_pairs) / len(union) if union else 1.0
    gates = {
        "global_two_percent": _gate(
            max(global_values.values()),
            max(global_values.values()) <= 0.02,
            "all preregistered global differences <= 2%",
        ),
        "cellwise_five_percent": _gate(
            max(cellwise_values.values()),
            max(cellwise_values.values()) <= 0.05,
            "all preregistered cellwise normalized RMS differences <= 5%",
        ),
        "contact_pair_jaccard": _gate(
            jaccard, jaccard >= 0.8, "final active-pair Jaccard >= 0.8"
        ),
    }
    failed = [name for name, gate in gates.items() if not gate["passed"]]
    return {
        "status": "passed" if not failed else "failed",
        "failed_gates": failed,
        "gates": gates,
        "global_relative_differences": global_values,
        "cellwise_normalized_rms_differences": cellwise_values,
        "contact_pairs": {
            "coarse": sorted(coarse_pairs),
            "refined": sorted(refined_pairs),
            "jaccard": jaccard,
        },
    }


def _verify_condition(result: Path, condition: str) -> dict[str, object]:
    execution_path = result / f"execution_{condition}.json"
    if not execution_path.is_file():
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "missing": [str(execution_path)],
        }
    execution = _execution(result, condition)
    if execution.get("status") == "not_run":
        return {
            "status": "not_run",
            "numerical_saved_state_safety": "not_run",
            "static_equilibrium": "not_run",
            "contact_network": "not_run",
            "reason": execution.get("reason", "conditional condition was not run"),
        }
    raw = result / "raw" / condition
    required = [
        result / "targets" / f"{condition}.csv",
        result / "controls" / f"{condition}.csv",
        raw / "kernel_metrics.json",
        raw / "nodes.csv",
        raw / "faces.csv",
        raw / "state_metrics.csv",
        raw / "cell_metrics.csv",
        raw / "contact_pairs.csv",
        raw / "step_audits.csv",
        raw / "trial_rejections.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        states = (
            _read_csv(raw / "state_metrics.csv")
            if (raw / "state_metrics.csv").is_file()
            else []
        )
        audits = (
            _read_csv(raw / "step_audits.csv")
            if (raw / "step_audits.csv").is_file()
            else []
        )
        rejections = (
            _read_csv(raw / "trial_rejections.csv")
            if (raw / "trial_rejections.csv").is_file()
            else []
        )
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "missing": missing,
            "execution_return_code": execution.get("return_code"),
            "termination_stderr": execution.get("stderr", ""),
            "retained_state_rows": len(states),
            "accepted_substeps": len(audits),
            "rejected_trials": len(rejections),
            "last_accepted_substep": audits[-1] if audits else None,
        }
    kernel = json.loads((raw / "kernel_metrics.json").read_text(encoding="utf-8"))
    states = sorted(
        _read_csv(raw / "state_metrics.csv"), key=lambda row: int(row["snapshot_index"])
    )
    nodes = _read_csv(raw / "nodes.csv")
    faces = _read_csv(raw / "faces.csv")
    cells = _read_csv(raw / "cell_metrics.csv")
    targets = _csv(result / "targets" / f"{condition}.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in nodes})
    if snapshots != list(range(9)) or len(states) != 9 or len(cells) != 225:
        return {
            "status": "failed",
            "numerical_saved_state_safety": "failed",
            "static_equilibrium": "unknown",
            "contact_network": "unknown",
            "reason": "incomplete retained state sequence",
            "snapshots": snapshots,
            "state_rows": len(states),
            "cell_rows": len(cells),
        }

    targets_by_cell = {int(row["cell_id"]): row for row in targets}
    initial_volumes = {
        cell_id: float(row["initial_volume"])
        for cell_id, row in targets_by_cell.items()
    }
    maximum_initial_change = 0.0
    minimum_angle = 180.0
    minimum_wall_clearance = float("inf")
    intersection_count = 0
    positive_volumes = True
    finite_values = True
    for snapshot, state in zip(snapshots, states, strict=True):
        meshes = _snapshot_meshes(nodes, faces, snapshot)
        bounds = np.asarray(
            [float(state[key]) for key in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")]
        )
        for cell_id, (points, triangles) in enumerate(meshes):
            volume, angle = _mesh_measures(points, triangles)
            positive_volumes = positive_volumes and volume > 0.0
            finite_values = finite_values and bool(np.isfinite(points).all())
            maximum_initial_change = max(
                maximum_initial_change,
                abs(volume - initial_volumes[cell_id]) / initial_volumes[cell_id],
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
            intersection_count += _candidate_intersection_count(
                points, triangles, points, triangles, same_mesh=True
            )
        for first in range(25):
            first_points, first_faces = meshes[first]
            for second in range(first + 1, 25):
                second_points, second_faces = meshes[second]
                separated = any(
                    float(first_points[:, axis].max())
                    < float(second_points[:, axis].min())
                    or float(second_points[:, axis].max())
                    < float(first_points[:, axis].min())
                    for axis in range(3)
                )
                if not separated:
                    intersection_count += _candidate_intersection_count(
                        first_points,
                        first_faces,
                        second_points,
                        second_faces,
                        same_mesh=False,
                    )

    state_fraction_error = max(
        abs(float(row["applied_target_fraction_of_final"]) - expected)
        for row, expected in zip(states, EXPECTED_FRACTIONS, strict=True)
    )
    fraction_by_snapshot = {
        int(row["snapshot_index"]): float(row["applied_target_fraction_of_final"])
        for row in states
    }
    target_application_error = 0.0
    for row in cells:
        target = targets_by_cell[int(row["cell_id"])]
        fraction = fraction_by_snapshot[int(row["snapshot_index"])]
        expected_volume = fraction * float(target["target_volume"])
        expected_area = fraction ** (2.0 / 3.0) * float(
            target["target_area_at_target_volume"]
        )
        target_application_error = max(
            target_application_error,
            abs(float(row["target_volume"]) - expected_volume) / expected_volume,
            abs(float(row["target_area_at_target_volume"]) - expected_area)
            / expected_area,
        )

    planar_areas = np.asarray([float(row["box_planar_area"]) for row in states])
    min_intercell = min(float(row["min_intercell_separation"]) for row in states)
    min_nonincident = min(float(row["min_nonincident_separation"]) for row in states)
    min_height = min(float(row["min_triangle_height"]) for row in states)
    contraction = max(float(row["contraction_traction"]) for row in nodes)
    final_force = float(states[-1]["max_free_force"])
    final_pairs = _final_pairs(raw / "contact_pairs.csv")
    grid_pairs = _grid_pairs()
    active_grid_pairs = final_pairs & grid_pairs
    contacted = {cell for pair in final_pairs for cell in pair}
    isolated = sorted(set(range(25)) - contacted)
    contact_network = (
        "passed" if len(active_grid_pairs) >= 32 and not isolated else "failed"
    )
    static_equilibrium = "passed" if final_force <= 1.0e-3 else "failed"
    gates = {
        "execution_completed": _gate(
            execution.get("return_code"),
            execution.get("return_code") == 0,
            "single preregistered invocation return_code == 0",
        ),
        "saved_states": _gate(len(states), len(states) == 9, "exactly nine states"),
        "positive_finite_geometry": _gate(
            positive_volumes and finite_values,
            positive_volumes and finite_values,
            "all independent volumes are positive and coordinates finite",
        ),
        "initial_volume_change": _gate(
            maximum_initial_change,
            maximum_initial_change <= 1.25,
            "maximum change from own initial volume <= 1.25",
        ),
        "mesh_angle": _gate(
            minimum_angle, minimum_angle >= 15.0, "minimum triangle angle >= 15 degrees"
        ),
        "wall_clearance": _gate(
            minimum_wall_clearance,
            minimum_wall_clearance >= -1.0e-6,
            "independent wall clearance >= -1e-6",
        ),
        "surface_intersections": _gate(
            intersection_count,
            intersection_count == 0,
            "independent segment-triangle screen finds zero intersections",
        ),
        "surface_separation": _gate(
            min(min_intercell, min_nonincident, min_height),
            min(min_intercell, min_nonincident, min_height) > 1.0e-8,
            "saved full-triangle separation and height > 1e-8",
        ),
        "work_dissipation": _gate(
            float(kernel["maximum_work_relative_residual"]),
            float(kernel["maximum_work_relative_residual"]) <= 1.0e-10,
            "maximum work-dissipation residual <= 1e-10",
        ),
        "fixed_box": _gate(
            float(np.max(np.abs(planar_areas / planar_areas[0] - 1.0))),
            bool(np.max(np.abs(planar_areas / planar_areas[0] - 1.0)) <= 1.0e-12),
            "box planar area remains fixed to relative 1e-12",
        ),
        "target_schedule": _gate(
            state_fraction_error,
            state_fraction_error <= 1.0e-12,
            "saved target fractions match the preregistered sequence",
        ),
        "target_application": _gate(
            target_application_error,
            target_application_error <= 1.0e-12,
            "cellwise applied V and A targets match the saved fraction",
        ),
        "contraction_disabled": _gate(
            contraction, contraction <= 1.0e-15, "active contraction traction is zero"
        ),
    }
    failed = [name for name, gate in gates.items() if not gate["passed"]]
    final_cells = _final_rows(raw / "cell_metrics.csv")
    return {
        "status": "passed" if not failed else "failed",
        "numerical_saved_state_safety": "passed" if not failed else "failed",
        "static_equilibrium": static_equilibrium,
        "contact_network": contact_network,
        "failed_gates": failed,
        "gates": gates,
        "terminal": {
            "max_free_force": final_force,
            "projected_occupancy": float(states[-1]["projected_occupancy"]),
            "minimum_intercell_separation": min_intercell,
            "active_cell_pairs": len(final_pairs),
            "active_grid_neighbor_pairs": len(active_grid_pairs),
            "isolated_cells": isolated,
            "cumulative_backtracks": int(kernel["cumulative_backtracks"]),
            "minimum_accepted_step": float(kernel["minimum_accepted_step"]),
        },
        "final_cells": [
            {
                key: int(row[key]) if key == "cell_id" else float(row[key])
                for key in (
                    "cell_id",
                    "pressure",
                    "volume",
                    "area",
                    "x_span",
                    "y_span",
                    "z_span",
                    "mean_contact_traction",
                    "mean_wall_traction",
                )
            }
            for row in final_cells
        ],
    }


def _verify_final_targets(result: Path) -> dict[str, object]:
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    parent = result.parents[2] / configuration["parent_result"]
    parent_rows = _csv(parent / "targets/HETEROGENEOUS_TARGETS.csv")
    parent_by_cell = {int(row["cell_id"]): row for row in parent_rows}
    errors: list[float] = []
    identities: list[bool] = []
    for condition in CONDITIONS:
        rows = _csv(result / "targets" / f"{condition}.csv")
        identities.append({row["condition"] for row in rows} == {condition})
        for row in rows:
            baseline = parent_by_cell[int(row["cell_id"])]
            for actual, expected in (
                (
                    float(row["target_volume"]),
                    VOLUME_SCALE * float(baseline["target_volume"]),
                ),
                (
                    float(row["target_area_at_target_volume"]),
                    AREA_SCALE * float(baseline["target_area_at_target_volume"]),
                ),
                (
                    float(row["target_isoperimetric_ratio"]),
                    float(baseline["target_isoperimetric_ratio"]),
                ),
            ):
                errors.append(abs(actual - expected) / max(abs(expected), np.finfo(float).tiny))
    maximum = max(errors)
    return {
        "status": "passed" if maximum <= 1.0e-12 and all(identities) else "failed",
        "maximum_relative_error": maximum,
        "condition_identity": all(identities),
        "criterion": "all conditions preserve Vx2, Ax2^(2/3), q and condition identity",
    }


def _material_sensitivity(
    refined: dict[str, object], soft: dict[str, object]
) -> dict[str, object]:
    if refined.get("status") != "passed" or soft.get("status") != "passed":
        return {"status": "not_evaluable", "reason": "K30 or K15 safety failed"}
    k30 = refined["final_cells"]
    k15 = soft["final_cells"]
    assert isinstance(k30, list) and isinstance(k15, list)
    result: dict[str, object] = {"status": "evaluated", "paired_metrics": {}}
    paired = result["paired_metrics"]
    assert isinstance(paired, dict)
    for metric in ("pressure", "volume", "x_span", "y_span", "z_span", "mean_contact_traction"):
        before = np.asarray([float(row[metric]) for row in k30])
        after = np.asarray([float(row[metric]) for row in k15])
        difference = after - before
        paired[metric] = {
            "K30_mean": float(before.mean()),
            "K15_mean": float(after.mean()),
            "K15_minus_K30_mean": float(difference.mean()),
            "K15_minus_K30_sd": float(difference.std()),
        }
    return result


def verify_myocardial_crowded_quasistatic_growth(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    required = [
        result / "configuration.json",
        result / "target_summary.json",
        result / "initial_cells.mesh",
        result / "heterogeneity.csv",
        result / "box_schedule.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "failed", "reason": "missing shared evidence", "missing": missing}
    conditions = {condition: _verify_condition(result, condition) for condition in CONDITIONS}
    convergence = evaluate_numerical_convergence(result)
    final_targets = _verify_final_targets(result)
    all_safe = all(
        conditions[name].get("numerical_saved_state_safety") == "passed"
        for name in CONDITIONS
    )
    qualification = (
        "passed"
        if all_safe
        and convergence.get("status") == "passed"
        and final_targets.get("status") == "passed"
        else "failed"
    )
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-QUASISTATIC-GROWTH-B",
        "status": qualification,
        "status_semantics": "saved-state safety plus preregistered numerical convergence",
        "numerical_qualification": qualification,
        "final_target_gates": final_targets,
        "conditions": conditions,
        "numerical_convergence": convergence,
        "material_sensitivity": _material_sensitivity(
            conditions["QS_REFINED_K30"], conditions["QS_REFINED_K15"]
        ),
        "claim_boundary": {
            "static_equilibrium": {
                name: conditions[name].get("static_equilibrium", "unknown")
                for name in CONDITIONS
            },
            "contact_network": {
                name: conditions[name].get("contact_network", "unknown")
                for name in CONDITIONS
            },
            "biological_validation": "not_run",
            "growth_time_model": "not_run",
            "contraction": "not_run",
        },
    }
