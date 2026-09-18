"""Independent audit of a retained mixed-matrix diagnostic package.

This module never factorizes the matrix and never invokes DOLFINx or Docker.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse

from .fenicsx_linear_system import sparse_metrics


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _identities(root, records):
    return {
        item["path"]: (root / item["path"]).is_file()
        and _digest(root / item["path"]) == item["sha256"]
        for item in records
    }


def verify_linear_system_result(root, workspace=None, save=False):
    """Audit saved assembly evidence without another solve or factorization."""
    root = Path(root).resolve(strict=True)
    archive = np.load(root / "matrix_csr.npz")
    size = len(archive["rhs"])
    matrix = sparse.csr_matrix(
        (archive["data"], archive["indices"], archive["indptr"]),
        shape=(size, size),
    )
    metrics = sparse_metrics(
        matrix,
        archive["residual"],
        archive["displacement"],
        archive["pressure"],
        archive["displacement_cells"],
        archive["pressure_cells"],
        archive["fixed"],
    )
    formal = _load_json(root / "formal_invocation_manifest.json")
    formal_identity = _identities(root, formal["files"])
    execution = _load_json(root / "execution.json")
    started = _load_json(root / "diagnostic_started.json")
    configuration = _load_json(root / "configuration.json")
    failure = _load_json(root / "failure.json")
    zero_metadata = _load_json(root / "source_f6s1r/M0_state_passive_0.json")
    failed_metadata = _load_json(root / "source_f6s1r/M0_state_passive_1.json")
    zero_state = np.load(root / "source_f6s1r/M0_state_passive_0.npz")
    failed_state = np.load(root / "source_f6s1r/M0_state_passive_1.npz")

    source_identity = {}
    for absolute, expected in _load_json(root / "source_result_preflight.json").items():
        path = Path(absolute)
        source_identity[absolute] = path.is_file() and _digest(path) == expected
    parent_identity = {}
    if workspace is not None:
        workspace = Path(workspace).resolve(strict=True)
        for relative, expected in _load_json(root / "protected_preflight.json").items():
            path = workspace / relative
            parent_identity[relative] = path.is_file() and _digest(path) == expected

    pressure_per_cell = int(archive["pressure_cells"].shape[1])
    rank_histogram = metrics["pressure_displacement_local_rank_histogram"]
    weak_mode_lower_bound = sum(
        (pressure_per_cell - int(rank)) * count
        for rank, count in rank_histogram.items()
    )
    scale_ratio = (
        metrics["maximum_abs_diagonal"]
        / metrics["pressure_block"]["minimum_cell_singular_value"]
    )
    block_norm_ratio = (
        metrics["block_frobenius_norms"]["uu"]
        / metrics["block_frobenius_norms"]["pp"]
    )
    state_chain = bool(
        np.array_equal(failed_state["initial_mixed"], zero_state["mixed_state"])
        and np.array_equal(archive["initial"], failed_state["initial_mixed"])
    )
    serializer_failure = (
        failure.get("error", {}).get("type") == "ValueError"
        and "Out of range float values" in failure.get("error", {}).get("message", "")
    )
    checks = {
        "formal_invocation_files_unchanged": all(formal_identity.values()),
        "source_result_unchanged": all(source_identity.values()),
        "protected_parent_unchanged": bool(parent_identity) and all(parent_identity.values()),
        "single_container_failed_without_retry": execution.get("status") == "failed"
        and execution.get("diagnostic_container_invocations") == 1
        and execution.get("automatic_retries") == 0,
        "no_nonlinear_equilibrium_solve_declared": started.get("nonlinear_equilibrium_solves") == 0
        and execution.get("nonlinear_equilibrium_solves") == 0
        and configuration.get("nonlinear_equilibrium_solves") == 0,
        "zero_gpu": execution.get("gpu") == 0 and configuration["resources"].get("gpu") == 0,
        "retained_initial_state_chain": state_chain,
        "original_failure_is_first_nonzero_state": zero_metadata.get("iterations") == 0
        and failed_metadata.get("iterations") == 0
        and failed_metadata.get("snes_reason") == -3,
        "matrix_entries_finite": metrics["finite_entries"],
        "matrix_structurally_full_rank": metrics["structural_rank"] == size,
        "matrix_has_no_zero_rows_or_columns": metrics["zero_rows"] == 0
        and metrics["zero_columns"] == 0,
        "pressure_cell_blocks_full_rank": metrics["pressure_block"]["all_cells_full_rank"],
        "strict_json_failure_retained": serializer_failure and not (root / "diagnosis.json").exists(),
    }
    verification_status = "passed" if all(checks.values()) else "failed"
    report = {
        "verification_status": verification_status,
        "execution_status": "failed",
        "diagnostic_delivery_status": "failed",
        "scientific_root_cause_status": "not_evaluable",
        "checks": checks,
        "matrix": metrics,
        "derived": {
            "pressure_dofs_per_cell": pressure_per_cell,
            "weakly_coupled_pressure_mode_lower_bound": int(weak_mode_lower_bound),
            "maximum_diagonal_to_minimum_pressure_cell_singular_ratio": float(scale_ratio),
            "uu_to_pp_frobenius_norm_ratio": float(block_norm_ratio),
        },
        "failure_localization": {
            "class": "nonfinite_mumps_diagnostic_value_not_serialized",
            "basis": "all independently recomputed matrix metrics are finite and the executed SuperLU path guards a nonfinite condition estimate; an unguarded MUMPS scalar remained",
            "exact_field": "unknown",
            "ksp_reason": "not_retained",
            "pc_failed_reason": "not_retained",
            "mumps_infog": "not_retained",
            "superlu_outcome": "not_retained",
        },
        "bounded_interpretation": {
            "excluded": [
                "structural rank deficiency",
                "zero assembled row or column",
                "singular per-cell finite-bulk pressure mass block",
            ],
            "supported_hypothesis": "severe mixed-block scaling or numerical pivot difficulty",
            "confirmed_solver_root_cause": False,
            "reason": "the exact MUMPS and SuperLU reports were lost at strict JSON serialization and the approved run was not repeated",
        },
        "state_after_factorization": "not_evaluable_no_post_state_was_persisted",
        "new_equilibria": 0,
        "new_factorizations_in_post_verification": 0,
        "contour": "not_run",
        "three_dimensional_model": "not_run",
        "fsi": "not_run",
        "growth": "not_run",
    }
    if save:
        target = root / "post_verification.json"
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return report
