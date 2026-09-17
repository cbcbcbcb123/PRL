"""Independent verification for the doubled-volume crowded myocardial run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .myocardial_crowded_box import _read_csv
from .myocardial_crowded_target_pair import _gate, _target_rows, _verify_condition


CONDITION = "HETEROGENEOUS_TARGETS_X2_VOLUME"
PARENT_CONDITION = "HETEROGENEOUS_TARGETS"
VOLUME_SCALE = 2.0
AREA_SCALE = VOLUME_SCALE ** (2.0 / 3.0)
SAFETY_LIMIT = 1.25


def _relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), np.finfo(float).tiny)


def _final_rows(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(path)
    snapshot = max(int(row["snapshot_index"]) for row in rows)
    return sorted(
        (row for row in rows if int(row["snapshot_index"]) == snapshot),
        key=lambda row: int(row["cell_id"]),
    )


def _final_state(path: Path) -> dict[str, str]:
    rows = _read_csv(path)
    return max(rows, key=lambda row: int(row["snapshot_index"]))


def verify_myocardial_crowded_volume_x2(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    root = result.parents[2]
    configuration_path = result / "configuration.json"
    if not configuration_path.is_file():
        return {"status": "failed", "reason": "missing configuration"}
    configuration = json.loads(configuration_path.read_text(encoding="utf-8"))
    parent = root / configuration["parent_result"]
    target_path = result / "targets" / f"{CONDITION}.csv"
    parent_target_path = parent / "targets/HETEROGENEOUS_TARGETS.csv"
    required = [
        result / "initial_cells.mesh",
        result / "target_summary.json",
        target_path,
        parent / "initial_cells.mesh",
        parent_target_path,
        parent / "verification.json",
        parent / f"raw/{PARENT_CONDITION}/state_metrics.csv",
        parent / f"raw/{PARENT_CONDITION}/cell_metrics.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "failed", "reason": "missing shared evidence", "missing": missing}

    targets = _target_rows(target_path)
    parent_targets = _target_rows(parent_target_path)
    targets_by_cell = {int(row["cell_id"]): row for row in targets}
    parent_by_cell = {int(row["cell_id"]): row for row in parent_targets}
    volume_errors: list[float] = []
    area_errors: list[float] = []
    q_errors: list[float] = []
    initial_errors: list[float] = []
    target_ratios: list[float] = []
    if set(targets_by_cell) == set(parent_by_cell) == set(range(25)):
        for cell_id in range(25):
            current = targets_by_cell[cell_id]
            baseline = parent_by_cell[cell_id]
            volume_errors.append(
                _relative_error(
                    float(current["target_volume"]),
                    VOLUME_SCALE * float(baseline["target_volume"]),
                )
            )
            area_errors.append(
                _relative_error(
                    float(current["target_area_at_target_volume"]),
                    AREA_SCALE * float(baseline["target_area_at_target_volume"]),
                )
            )
            q_errors.append(
                _relative_error(
                    float(current["target_isoperimetric_ratio"]),
                    float(baseline["target_isoperimetric_ratio"]),
                )
            )
            initial_errors.extend(
                [
                    _relative_error(
                        float(current["initial_volume"]),
                        float(baseline["initial_volume"]),
                    ),
                    _relative_error(
                        float(current["initial_area"]),
                        float(baseline["initial_area"]),
                    ),
                ]
            )
            target_ratios.append(
                float(current["target_volume"]) / float(current["initial_volume"])
            )
    else:
        volume_errors = area_errors = q_errors = initial_errors = [float("inf")]

    safety_limits = {
        float(row.get("maximum_initial_volume_relative_change") or float("nan"))
        for row in targets
    }
    mesh_digest = hashlib.sha256((result / "initial_cells.mesh").read_bytes()).hexdigest()
    parent_mesh_digest = hashlib.sha256(
        (parent / "initial_cells.mesh").read_bytes()
    ).hexdigest()
    target_gates = {
        "complete_cell_ids": _gate(
            sorted(targets_by_cell),
            set(targets_by_cell) == set(parent_by_cell) == set(range(25)),
            "new and parent manifests contain exactly cell IDs 0..24",
        ),
        "condition_identity": _gate(
            sorted({row["condition"] for row in targets}),
            {row["condition"] for row in targets} == {CONDITION},
            f"all rows use {CONDITION}",
        ),
        "same_initial_mesh": _gate(
            mesh_digest,
            mesh_digest == parent_mesh_digest,
            "initial mesh bytes equal retained heterogeneous baseline",
        ),
        "same_initial_measures": _gate(
            max(initial_errors),
            max(initial_errors) <= 1.0e-12,
            "per-cell initial volume and area unchanged to relative 1e-12",
        ),
        "volume_scale": _gate(
            max(volume_errors),
            max(volume_errors) <= 1.0e-12,
            "every target volume equals 2x the retained heterogeneous target",
        ),
        "area_scale": _gate(
            max(area_errors),
            max(area_errors) <= 1.0e-12,
            "every target area equals 2^(2/3)x the retained heterogeneous target",
        ),
        "shape_index_preserved": _gate(
            max(q_errors),
            max(q_errors) <= 1.0e-12,
            "every target isoperimetric ratio q is unchanged",
        ),
        "frozen_safety_limit": _gate(
            sorted(safety_limits),
            safety_limits == {SAFETY_LIMIT},
            "all target rows carry the preregistered 1.25 initial-volume-change limit",
        ),
    }
    target_failures = [name for name, gate in target_gates.items() if not gate["passed"]]
    condition = _verify_condition(result, CONDITION)
    execution_path = result / f"execution_{CONDITION}.json"
    execution = (
        json.loads(execution_path.read_text(encoding="utf-8"))
        if execution_path.is_file()
        else {}
    )
    raw = result / "raw" / CONDITION
    retained_states = (
        _read_csv(raw / "state_metrics.csv")
        if (raw / "state_metrics.csv").is_file()
        else []
    )
    audits = (
        _read_csv(raw / "step_audits.csv")
        if (raw / "step_audits.csv").is_file()
        else []
    )
    failure_text = (
        (raw / "failure.txt").read_text(encoding="utf-8").strip()
        if (raw / "failure.txt").is_file()
        else ""
    )
    failure_diagnosis: dict[str, object] = {
        "solver_return_code": execution.get("return_code"),
        "solver_elapsed_seconds": execution.get("elapsed_seconds"),
        "failure": failure_text or "none_recorded",
        "retained_state_count": len(retained_states),
        "accepted_substep_count": len(audits),
        "complete_nine_state_sequence": len(retained_states) == 9,
    }
    if retained_states:
        failure_diagnosis["last_retained_state"] = {
            "snapshot_index": int(retained_states[-1]["snapshot_index"]),
            "coordinate": float(retained_states[-1]["coordinate"]),
            "max_free_force": float(retained_states[-1]["max_free_force"]),
            "maximum_initial_volume_change": float(
                retained_states[-1]["max_initial_volume_relative_change"]
            ),
            "minimum_intercell_separation": float(
                retained_states[-1]["min_intercell_separation"]
            ),
            "active_cell_pairs": int(
                float(retained_states[-1]["contact_active_cell_pairs"])
            ),
        }
    if audits:
        last_audit = audits[-1]
        failure_diagnosis["last_accepted_substep"] = {
            "coordinate": float(last_audit["coordinate"]),
            "accepted_step": float(last_audit["accepted_step"]),
            "max_free_force": float(last_audit["max_free_force"]),
            "maximum_initial_volume_change": float(
                last_audit["max_initial_volume_relative_change"]
            ),
            "minimum_triangle_angle_deg": float(last_audit["min_triangle_angle_deg"]),
            "minimum_wall_clearance": float(last_audit["min_wall_clearance"]),
            "maximum_work_relative_residual": float(
                last_audit["max_work_relative_residual"]
            ),
            "active_cell_pairs": int(float(last_audit["contact_active_cell_pairs"])),
        }
        failure_diagnosis["maximum_pre_failure_force"] = max(
            float(row["max_free_force"]) for row in audits
        )

    baseline_verification = json.loads(
        (parent / "verification.json").read_text(encoding="utf-8")
    )
    baseline_condition = baseline_verification["conditions"][PARENT_CONDITION]
    baseline_cells = _final_rows(parent / f"raw/{PARENT_CONDITION}/cell_metrics.csv")
    doubled_cells = condition.get("final_cells", [])
    paired_metrics: dict[str, object] = {}
    if len(baseline_cells) == len(doubled_cells) == 25:
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
            baseline_values = np.asarray(
                [float(row[metric]) for row in baseline_cells], dtype=float
            )
            doubled_values = np.asarray(
                [float(row[metric]) for row in doubled_cells], dtype=float
            )
            differences = doubled_values - baseline_values
            paired_metrics[metric] = {
                "baseline_mean": float(baseline_values.mean()),
                "doubled_target_mean": float(doubled_values.mean()),
                "doubled_minus_baseline_mean": float(differences.mean()),
                "doubled_minus_baseline_sd": float(differences.std()),
                "minimum": float(differences.min()),
                "maximum": float(differences.max()),
                "cellwise": differences.tolist(),
            }

    baseline_state = _final_state(
        parent / f"raw/{PARENT_CONDITION}/state_metrics.csv"
    )
    terminal_comparison: dict[str, object] = {
        "baseline": {
            "projected_occupancy": float(baseline_state["projected_occupancy"]),
            "max_free_force": float(baseline_state["max_free_force"]),
            "active_cell_pairs": int(float(baseline_state["contact_active_cell_pairs"])),
            "active_grid_neighbor_pairs": baseline_condition["terminal"][
                "active_grid_neighbor_pairs"
            ],
            "isolated_cells": baseline_condition["terminal"]["isolated_cells"],
            "total_wall_reaction": float(baseline_state["total_wall_reaction"]),
            "minimum_intercell_separation": min(
                float(row["min_intercell_separation"])
                for row in _read_csv(
                    parent / f"raw/{PARENT_CONDITION}/state_metrics.csv"
                )
            ),
        },
        "doubled_target": condition.get("terminal", {}),
        "paired_cell_metrics": paired_metrics,
    }
    if target_ratios:
        terminal_comparison["target_to_own_initial_volume_range"] = [
            float(min(target_ratios)),
            float(max(target_ratios)),
        ]

    numerical_passed = condition.get("numerical_saved_state_safety") == "passed"
    status = "passed" if numerical_passed and not target_failures else "failed"
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-VOLUME-X2-A",
        "status": status,
        "status_semantics": "target-scaling contract and numerical saved-state safety only",
        "numerical_saved_state_safety": condition.get(
            "numerical_saved_state_safety", "unknown"
        ),
        "static_equilibrium": condition.get("static_equilibrium", "unknown"),
        "contact_network": condition.get("contact_network", "unknown"),
        "target_failed_gates": target_failures,
        "target_gates": target_gates,
        "condition": condition,
        "baseline_comparison": terminal_comparison,
        "failure_diagnosis": failure_diagnosis,
        "claim_boundary": {
            "target_attainment": "reported_not_a_package_pass_gate",
            "biological_validation": "not_run",
            "contraction": "not_run",
            "random_seed_replication": "not_run",
            "growth_time_model": "not_run",
            "contact_resolution": "exploratory 0.40 maximum-edge quadrature",
        },
    }
