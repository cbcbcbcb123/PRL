"""Independent R0-A adjudication for the staged DCM--FEM common-limit work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

RESULT = Path("results/ventricle_z1/z1_regular_dcm_fem_common_limit_v01_20260916")


def _table(path: Path) -> np.ndarray:
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_regular_dcm_fem_common_limit(result: Path, *, save: bool = False) -> dict:
    root = result.parents[2]
    raw = result / "raw" / "dcm_two_cell_compression"
    run = json.loads((raw / "run.json").read_text(encoding="utf-8"))
    execution = json.loads((result / "execution.json").read_text(encoding="utf-8"))
    self_tests = json.loads((result / "self_tests.json").read_text(encoding="utf-8"))
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    recorded_hashes = json.loads(
        (result / "source_hashes_before.json").read_text(encoding="utf-8")
    )
    states = _table(raw / "states.csv")
    separation = _table(raw / "separation.csv")
    audits = _table(raw / "step_audits.csv")
    nodes = _table(raw / "nodes.csv")

    source_checks = {
        path: (root / path).is_file() and _sha256(root / path) == expected
        for path, expected in recorded_hashes.items()
    }
    snapshots = np.unique(nodes["snapshot"].astype(int))
    reaction = []
    for snapshot in snapshots:
        current = nodes[nodes["snapshot"].astype(int) == snapshot]
        per_cell = []
        for cell_id in (0, 1):
            selected = current[
                (current["cell"].astype(int) == cell_id) & (current["fixed"] > 0.5)
            ]
            per_cell.append(abs(float(np.sum(selected["rfx"]))))
        reaction.append(0.5 * sum(per_cell))
    reaction_array = np.asarray(reaction)
    initial_gap = float(separation["intercell_distance"][0])
    final_gap = float(separation["intercell_distance"][-1])
    minimum_gap = float(np.min(separation["intercell_distance"]))
    checks = {
        "native_self_tests": self_tests.get("status") == "passed"
        and all(call.get("return_code") == 0 for call in self_tests.get("calls", [])),
        "single_authorized_execution": execution.get("return_code") == 0
        and execution.get("automatic_retries") == 0,
        "solver_completed": run.get("execution_status") == "passed"
        and int(run.get("completed_steps", -1)) == 20,
        "twenty_one_real_states": len(snapshots) == 21
        and int(run.get("snapshots", -1)) == 21,
        "source_and_binary_hashes": all(source_checks.values()),
        "finite_ledgers": all(
            np.isfinite(table[name]).all()
            for table in (states, separation, audits, nodes)
            for name in table.dtype.names
        ),
        "positive_surface_separation": minimum_gap > 0.0
        and float(np.min(separation["nonincident_distance"])) > 1.0e-8
        and float(np.min(separation["min_height"])) > 1.0e-8,
        "mesh_and_volume_safety": float(np.min(states["min_angle"])) >= 15.0
        and float(np.max(states["max_volume_error"])) <= 0.02,
        "prescribed_clamp_exact": float(np.max(states["max_fixed_displacement"]))
        <= 1.0e-12,
        "step_work_identity": float(np.max(np.abs(audits["work_residual"])))
        <= 1.0e-10,
        "contact_was_active": float(np.min(states["contact_support_area"])) > 0.0,
    }
    report = {
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "R0-A contact/rollback engineering probe only",
        "checks": {name: bool(value) for name, value in checks.items()},
        "source_checks": source_checks,
        "metrics": {
            "initial_exact_intercell_gap": initial_gap,
            "minimum_exact_intercell_gap": minimum_gap,
            "final_exact_intercell_gap": final_gap,
            "final_maximum_free_nodal_force": float(states["max_free_force"][-1]),
            "maximum_volume_relative_error": float(
                np.max(states["max_volume_error"])
            ),
            "minimum_triangle_angle_degrees": float(np.min(states["min_angle"])),
            "maximum_clamp_error": float(
                np.max(states["max_fixed_displacement"])
            ),
            "initial_mean_end_reaction": float(reaction_array[0]),
            "final_mean_end_reaction": float(reaction_array[-1]),
            "maximum_mean_end_reaction": float(np.max(reaction_array)),
        },
        "scientific_gates": {
            "near_zero_contact_event_exercised": "not_run",
            "regular_patch_equilibrium": "not_run",
            "matched_cell_resolved_fem": "not_run",
            "homogenized_fem": "not_run",
            "dcm_advantage": "not_run",
            "biological_validation": "not_run",
        },
        "interpretation": (
            "The repaired executable completed one bounded approach without the old "
            "distance-floor stop. The exact gap increased rather than entering near-zero "
            "contact, and the final free force is far above the equilibrium gate; this "
            "therefore does not qualify the regular layer or any DCM--FEM comparison."
        ),
        "configuration": configuration,
    }
    if save:
        target = result / "verification.json"
        if target.exists():
            raise FileExistsError(f"create-only: {target}")
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


__all__ = ["RESULT", "verify_regular_dcm_fem_common_limit"]
