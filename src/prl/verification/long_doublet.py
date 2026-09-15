"""Independent scalar-ledger verification for the retained long doublet."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


DEFAULT_RESULT = Path(
    "results/ventricle_z1/z1_myo_long_doublet_v01_20260914"
)
EXPECTED_CASES = (
    "END_DT0.02",
    "END_DT0.01",
    "SIDE_DT0.02",
    "SIDE_DT0.01",
)
EQUILIBRIUM_FORCE_LIMIT = 0.001
SOURCE_FILTER_MAP = Path(
    "project_control/evidence/repository_cleanup_v01/batch05a_source_filter_map_v01.json"
)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _close(left: float, right: float, *, absolute: float = 1e-10) -> bool:
    return math.isclose(left, right, rel_tol=1e-10, abs_tol=absolute)


def _root_commit(workspace: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=workspace,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    commits = completed.stdout.decode("ascii", errors="replace").splitlines()
    return commits[0].strip() if len(commits) == 1 else None


def _git_blob_sha256(workspace: Path, revision: str | None, relative: str) -> str | None:
    if revision is None:
        return None
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=workspace,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return hashlib.sha256(completed.stdout).hexdigest()


def _source_identity(workspace: Path, result: Path) -> dict:
    recorded = _read_json(result / "source_hashes_before.json")
    checks: list[dict] = []
    root = workspace.resolve(strict=True)
    root_commit = _root_commit(root)
    filter_map_path = root / SOURCE_FILTER_MAP
    filter_mappings: dict[str, dict] = {}
    if filter_map_path.is_file():
        payload = _read_json(filter_map_path)
        if payload.get("first_clean_baseline_commit") == root_commit:
            filter_mappings = {item["path"]: item for item in payload.get("mappings", [])}
    for relative, expected in recorded.items():
        normalized = relative.replace("\\", "/")
        candidate = (root / Path(normalized)).resolve(strict=False)
        try:
            candidate.relative_to(root)
            inside_workspace = True
        except ValueError:
            inside_workspace = False
        working_tree_exists = inside_workspace and candidate.is_file()
        working_tree_sha256 = _sha256(candidate) if working_tree_exists else None
        root_commit_sha256 = _git_blob_sha256(root, root_commit, normalized)
        mapped = filter_mappings.get(normalized)
        mapped_match = bool(
            mapped
            and mapped.get("raw_worktree_sha256") == expected
            and mapped.get("first_commit_blob_sha256") == root_commit_sha256
        )
        if working_tree_sha256 == expected:
            matched_from = "working_tree"
            actual = working_tree_sha256
        elif root_commit_sha256 == expected:
            matched_from = "first_clean_baseline_commit"
            actual = root_commit_sha256
        elif mapped_match:
            matched_from = "first_commit_clean_filter_mapping"
            actual = expected
        else:
            matched_from = None
            actual = working_tree_sha256 or root_commit_sha256
        checks.append(
            {
                "path": normalized,
                "working_tree_exists": working_tree_exists,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "working_tree_sha256": working_tree_sha256,
                "root_commit_sha256": root_commit_sha256,
                "filter_mapping_applied": mapped_match,
                "matched_from": matched_from,
                "matches": matched_from is not None,
            }
        )
    return {
        "status": "passed" if checks and all(item["matches"] for item in checks) else "failed",
        "files_checked": len(checks),
        "first_clean_baseline_commit": root_commit,
        "checks": checks,
    }


def _case_metrics(case_path: Path) -> dict:
    states = _read_csv(case_path / "states.csv")
    separation = _read_csv(case_path / "separation.csv")
    audits = _read_csv(case_path / "step_audits.csv")
    cells = _read_csv(case_path / "cells.csv")
    geometry = _read_json(case_path / "geometry_monitor.json")
    if not states or not separation or not cells or not geometry.get("states"):
        raise ValueError(f"Incomplete retained ledgers in {case_path}")

    cell_rows: dict[int, list[dict[str, str]]] = {}
    for row in cells:
        cell_rows.setdefault(int(row["cell"]), []).append(row)
    per_cell = []
    for cell_id, rows in sorted(cell_rows.items()):
        first, last = rows[0], rows[-1]
        per_cell.append(
            {
                "cell": cell_id,
                **{
                    f"{axis}_strain": float(last[axis]) / float(first[axis]) - 1.0
                    for axis in ("length", "width", "thickness")
                },
            }
        )

    monitored_cells = [
        cell
        for state in geometry["states"]
        for cell in state.get("cells", [])
    ]
    final_state = states[-1]
    final_force = float(final_state["max_free_force"])
    return {
        "states": len(states),
        "final_coordinate": float(final_state["coordinate"]),
        "minimum_gap": min(float(row["intercell_distance"]) for row in separation),
        "final_gap": float(separation[-1]["intercell_distance"]),
        "minimum_angle": min(float(cell["min_angle"]) for cell in monitored_cells),
        "minimum_adjacent_cosine": min(
            float(cell["adjacent_cosine"]) for cell in monitored_cells
        ),
        "maximum_volume_error": max(
            float(cell["volume_error"]) for cell in monitored_cells
        ),
        "maximum_work_residual": max(
            (float(row["work_residual"]) for row in audits), default=0.0
        ),
        "final_force": final_force,
        "static_equilibrium": (
            "passed" if final_force <= EQUILIBRIUM_FORCE_LIMIT else "failed"
        ),
        "monitor_first_failure": geometry.get("first_failure"),
        "monitor_states": len(geometry["states"]),
        "per_cell": per_cell,
    }


def _compare_case(actual: dict, frozen: dict) -> dict[str, bool]:
    checks = {
        "state_count": actual["states"] == frozen["states"],
        "monitor_state_count": actual["monitor_states"] == frozen["states"],
        "monitor_has_no_failure": actual["monitor_first_failure"] is None,
        "final_coordinate": _close(actual["final_coordinate"], frozen["final_coordinate"]),
        "minimum_gap": _close(actual["minimum_gap"], frozen["minimum_gap"]),
        "final_gap": _close(actual["final_gap"], frozen["final_gap"]),
        "minimum_angle": _close(actual["minimum_angle"], frozen["minimum_angle"]),
        "minimum_adjacent_cosine": _close(
            actual["minimum_adjacent_cosine"], frozen["minimum_adjacent_cosine"]
        ),
        "maximum_volume_error": _close(
            actual["maximum_volume_error"], frozen["maximum_volume_error"]
        ),
        "maximum_work_residual": _close(
            actual["maximum_work_residual"], frozen["maximum_work_residual"]
        ),
        "final_force": _close(actual["final_force"], frozen["final_force"]),
        "static_equilibrium": (
            actual["static_equilibrium"] == frozen["static_equilibrium"]
        ),
    }
    actual_cells = {item["cell"]: item for item in actual["per_cell"]}
    frozen_cells = {item["cell"]: item for item in frozen["per_cell"]}
    checks["cell_ids"] = actual_cells.keys() == frozen_cells.keys()
    for cell_id in sorted(actual_cells.keys() & frozen_cells.keys()):
        for axis in ("length", "width", "thickness"):
            key = f"{axis}_strain"
            checks[f"cell_{cell_id}_{key}"] = _close(
                actual_cells[cell_id][key], frozen_cells[cell_id][key]
            )
    return checks


def verify_long_doublet(
    workspace: Path,
    result_path: Path | None = None,
) -> dict:
    """Verify retained scalar ledgers without importing historical run scripts."""

    root = workspace.resolve(strict=True)
    if result_path is None:
        result = root / DEFAULT_RESULT
    else:
        result = result_path if result_path.is_absolute() else root / result_path
    result = result.resolve(strict=True)
    result.relative_to(root)

    frozen_long = _read_json(result / "long_verdict.json")
    frozen_overall = _read_json(result / "verdict.json")
    execution_status = _read_json(result / "execution_status.json")
    ledger = _read_json(result / "execution_ledger.json")
    frozen_details = {item["case"]: item for item in frozen_long["details"]}

    ledger_cases = {item.get("case") for item in ledger}
    matrix_complete = (
        len(ledger) == len(EXPECTED_CASES)
        and ledger_cases == set(EXPECTED_CASES)
        and all(
            item.get("returncode") == 0 and item.get("first_failure") is None
            for item in ledger
        )
        and execution_status.get("status") == "passed"
        and execution_status.get("cases_run") == len(EXPECTED_CASES)
        and not execution_status.get("cases_not_run")
    )

    cases: list[dict] = []
    for case_name in EXPECTED_CASES:
        actual = _case_metrics(result / case_name)
        frozen = frozen_details[case_name]
        checks = _compare_case(actual, frozen)
        cases.append(
            {
                "case": case_name,
                "status": "passed" if all(checks.values()) else "failed",
                "checks": checks,
                "metrics": actual,
            }
        )

    source_identity = _source_identity(root, result)
    status_agreement = {
        "long_doublet_numerical": (
            frozen_overall.get("long_doublet_numerical") == frozen_long.get("status")
        ),
        "static_equilibrium": (
            frozen_overall.get("static_equilibrium")
            == frozen_long.get("static_equilibrium")
        ),
        "parent_z1_remains_blocked": frozen_overall.get("parent_Z1") == "blocked",
        "biological_validation_remains_blocked": (
            frozen_overall.get("biological_validation") == "blocked"
        ),
        "sixteen_cell_dynamics_not_run": (
            frozen_overall.get("sixteen_cell_dynamics") == "not_run"
        ),
    }
    checks = {
        "source_identity": source_identity["status"] == "passed",
        "matrix_complete": matrix_complete,
        "case_scalar_ledgers": all(case["status"] == "passed" for case in cases),
        "frozen_status_agreement": all(status_agreement.values()),
    }
    return {
        "schema_version": "prl.long_doublet_verification.v1",
        "status": "passed" if all(checks.values()) else "failed",
        "workspace": str(root),
        "result_path": str(result),
        "checks": checks,
        "source_identity": source_identity,
        "matrix_complete": matrix_complete,
        "status_agreement": status_agreement,
        "frozen_status": {
            "long_doublet_numerical": frozen_overall.get("long_doublet_numerical"),
            "static_equilibrium": frozen_overall.get("static_equilibrium"),
            "parent_Z1": frozen_overall.get("parent_Z1"),
            "biological_validation": frozen_overall.get("biological_validation"),
            "sixteen_cell_dynamics": frozen_overall.get("sixteen_cell_dynamics"),
        },
        "cases": cases,
        "not_recomputed": [
            "node-level END/SIDE displacement-refinement norms",
            "node/triangle containment and crossing predicates",
            "all possible incident-vertex fold configurations",
        ],
        "scope": (
            "independent source-hash, execution-ledger, retained geometry-monitor, "
            "scalar-state, separation, work-residual and per-cell deformation checks; "
            "no solver execution and no biological validation"
        ),
    }
