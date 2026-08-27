from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import (  # noqa: E402
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    _kkt_audit,
    build_exact_volume_coordinates,
    unpack_exact_volume_variables,
)
from hybrid.efe_path_sensitivity import array_difference_metrics  # noqa: E402
from hybrid.efe_step_transaction import (  # noqa: E402
    StepOracleMetrics,
    audit_transaction_candidate,
    checkpoint_array_digest,
    file_sha256,
    write_checkpoint_exclusive,
)
from run_efe_node1_n1_2_periodic_case_v01 import load_checkpoint  # noqa: E402


WORKER = ROOT / "scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py"
DEFAULT_BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
DEFAULT_INPUT = DEFAULT_BASELINE_CASE / "cycle_03/accepted_step_003.npz"
DEFAULT_REFERENCE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1b_cold_rep01_v01_20260820"
    / "final_candidate_checkpoint.npz"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r2_transactional_step_v01_20260820"
)
ACTIVATION = 0.1
SUCCESS_REPLICATES = 3
GATE_CRITICAL_SOURCES = (
    WORKER,
    ROOT / "src/hybrid/efe_fast_trilayer_solver.py",
    ROOT / "src/hybrid/fenicsx_ecm_backend.py",
    ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py",
)


def worker_command(
    *,
    input_path: Path,
    baseline_case: Path,
    output_path: Path,
    maximum_coupling_iterations: int,
    disable_fallback: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(WORKER),
        "--input",
        str(input_path),
        "--baseline-case-directory",
        str(baseline_case),
        "--output",
        str(output_path),
        "--dcm-level",
        "D0",
        "--ecm-level",
        "E0",
        "--ecm-footprint-scale",
        "1.5",
        "--ecm-backend",
        "fenicsx",
        "--algorithm",
        "picard",
        "--backend-history-mode",
        "cold",
        "--maximum-coupling-iterations",
        str(maximum_coupling_iterations),
    ]
    if disable_fallback:
        command.append("--disable-fallback")
    return command


def run_worker_process(command: list[str], evidence_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    record = {
        "command": command,
        "returncode": result.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    evidence_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def oracle_metrics(
    model,
    coordinates,
    variables: np.ndarray,
    internal_z: np.ndarray,
    raw_coupling_residual: float,
) -> StepOracleMetrics:
    from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

    backend = FenicsxECMBackend(model.ecm_reference)
    geometry = unpack_exact_volume_variables(model, coordinates, variables)
    evaluation = evaluate_fast_trilayer_state(
        model,
        *geometry,
        activation=ACTIVATION,
        ecm_internal_z=internal_z,
        ecm_backend=backend.energy_force,
        reject_penetration=False,
    )
    _, normalized_kkt = _kkt_audit(
        model,
        coordinates,
        evaluation,
        geometry[0],
        geometry[2],
        np.zeros_like(coordinates.reference_flat),
    )
    return StepOracleMetrics(
        normalized_kkt_residual=normalized_kkt,
        raw_coupling_residual=raw_coupling_residual,
        volume_constraint_residual=max(
            abs(evaluation.myocyte_volume_ratio - 1.0),
            abs(evaluation.endocardial_volume_ratio - 1.0),
        ),
        minimum_ecm_jacobian=evaluation.minimum_ecm_jacobian,
        minimum_gap=evaluation.minimum_gap,
        minimum_myocyte_face_area_ratio=(
            evaluation.minimum_myocyte_face_area_ratio
        ),
        minimum_endocardial_face_area_ratio=(
            evaluation.minimum_endocardial_face_area_ratio
        ),
        internal_symmetry_residual=float(
            np.max(np.abs(internal_z - np.swapaxes(internal_z, 1, 2)))
        ),
        internal_trace_residual=float(
            np.max(np.abs(np.trace(internal_z, axis1=1, axis2=2)))
        ),
    )


def exact_reference_comparison(
    candidate: tuple[np.ndarray, np.ndarray, np.ndarray],
    reference: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> dict[str, object]:
    labels = ("variables", "ecm_internal_z", "contact_multipliers")
    comparisons = {
        label: {
            "exactly_equal": bool(np.array_equal(candidate_array, reference_array)),
            **array_difference_metrics(candidate_array, reference_array),
        }
        for label, candidate_array, reference_array in zip(
            labels, candidate, reference, strict=True
        )
    }
    return {
        "arrays": comparisons,
        "all_arrays_exactly_equal": all(
            bool(record["exactly_equal"]) for record in comparisons.values()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument(
        "--baseline-case-directory", type=Path, default=DEFAULT_BASELINE_CASE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    input_path = arguments.input.resolve()
    reference_path = arguments.reference.resolve()
    baseline_case = arguments.baseline_case_directory.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    coordinates = build_exact_volume_coordinates(model)
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    input_arrays = load_checkpoint(
        input_path, model, len(coordinates.free_indices), contact_count
    )
    expected_input_digest = checkpoint_array_digest(*input_arrays)
    reference_arrays = load_checkpoint(
        reference_path, model, len(coordinates.free_indices), contact_count
    )
    reference_digest = checkpoint_array_digest(*reference_arrays)
    expected_source_fingerprints = {
        str(path.relative_to(ROOT)): file_sha256(path)
        for path in GATE_CRITICAL_SOURCES
    }

    successful_transactions: list[dict[str, object]] = []
    worker_process_ids: list[int] = []
    for replicate in range(1, SUCCESS_REPLICATES + 1):
        replicate_path = output_path / f"success_replicate_{replicate:02d}"
        replicate_path.mkdir(parents=True, exist_ok=True)
        staging_path = replicate_path / "worker_staging"
        command = worker_command(
            input_path=input_path,
            baseline_case=baseline_case,
            output_path=staging_path,
            maximum_coupling_iterations=12,
            disable_fallback=False,
        )
        process_record = run_worker_process(
            command, replicate_path / "worker_process.json"
        )
        if int(process_record["returncode"]) != 0:
            raise RuntimeError(f"success worker {replicate} exited nonzero")
        worker_summary = json.loads(
            (staging_path / "summary.json").read_text(encoding="utf-8")
        )
        worker_process_ids.append(
            int(worker_summary["runtime_identity"]["process_id"])
        )
        candidate_arrays = load_checkpoint(
            staging_path / "final_candidate_checkpoint.npz",
            model,
            len(coordinates.free_indices),
            contact_count,
        )
        candidate_digest = checkpoint_array_digest(*candidate_arrays)
        post_worker_input = load_checkpoint(
            input_path, model, len(coordinates.free_indices), contact_count
        )
        post_worker_input_digest = checkpoint_array_digest(*post_worker_input)
        metrics = oracle_metrics(
            model,
            coordinates,
            candidate_arrays[0],
            candidate_arrays[1],
            float(worker_summary["final_raw_coupling_residual"]),
        )
        audit = audit_transaction_candidate(
            worker_passed=bool(worker_summary["passed"]),
            expected_input_digest=expected_input_digest,
            worker_input_digest=str(
                worker_summary["initial_checkpoint_array_digest"]
            ),
            post_worker_input_digest=post_worker_input_digest,
            metrics=metrics,
        )
        reference_comparison = exact_reference_comparison(
            candidate_arrays, reference_arrays
        )
        source_match = (
            worker_summary["source_fingerprints"]
            == expected_source_fingerprints
        )
        transaction_passed = bool(
            audit["passed"]
            and reference_comparison["all_arrays_exactly_equal"]
            and source_match
            and bool(worker_summary["final_solver_passed"])
        )
        if not transaction_passed:
            raise RuntimeError(
                f"parent oracle rejected success worker {replicate}"
            )
        commit_path = replicate_path / "accepted_step_004.npz"
        commit_record = write_checkpoint_exclusive(
            commit_path,
            variables=candidate_arrays[0],
            internal_z=candidate_arrays[1],
            contact_multipliers=candidate_arrays[2],
        )
        second_commit_rejected = False
        try:
            write_checkpoint_exclusive(
                commit_path,
                variables=candidate_arrays[0],
                internal_z=candidate_arrays[1],
                contact_multipliers=candidate_arrays[2],
            )
        except FileExistsError:
            second_commit_rejected = True
        if not second_commit_rejected:
            raise RuntimeError("create-only checkpoint accepted a second commit")
        committed_arrays = load_checkpoint(
            commit_path, model, len(coordinates.free_indices), contact_count
        )
        committed_digest = checkpoint_array_digest(*committed_arrays)
        transaction_record = {
            "replicate": replicate,
            "worker_process": process_record,
            "worker_process_id": worker_process_ids[-1],
            "worker_parent_process_id": int(
                worker_summary["runtime_identity"]["parent_process_id"]
            ),
            "worker_summary": str(staging_path / "summary.json"),
            "input_digest": expected_input_digest,
            "candidate_digest": candidate_digest,
            "reference_digest": reference_digest,
            "parent_oracle": audit,
            "reference_comparison": reference_comparison,
            "source_fingerprints_match": source_match,
            "commit": commit_record,
            "committed_digest": committed_digest,
            "candidate_commit_digest_match": (
                candidate_digest == committed_digest
            ),
            "second_commit_rejected": second_commit_rejected,
            "passed": True,
        }
        (replicate_path / "transaction_summary.json").write_text(
            json.dumps(transaction_record, indent=2), encoding="utf-8"
        )
        successful_transactions.append(transaction_record)
        print(
            f"r2 success transaction {replicate}/3 committed "
            f"pid={worker_process_ids[-1]}",
            flush=True,
        )

    failure_path = output_path / "failure_control"
    failure_path.mkdir(parents=True, exist_ok=True)
    failure_staging = failure_path / "worker_staging"
    failure_command = worker_command(
        input_path=input_path,
        baseline_case=baseline_case,
        output_path=failure_staging,
        maximum_coupling_iterations=1,
        disable_fallback=True,
    )
    failure_process = run_worker_process(
        failure_command, failure_path / "worker_process.json"
    )
    failure_summary = json.loads(
        (failure_staging / "summary.json").read_text(encoding="utf-8")
    )
    worker_process_ids.append(
        int(failure_summary["runtime_identity"]["process_id"])
    )
    failure_candidate_exists = (
        failure_staging / "final_candidate_checkpoint.npz"
    ).is_file()
    failure_commit_path = failure_path / "accepted_step_004.npz"
    post_failure_input = load_checkpoint(
        input_path, model, len(coordinates.free_indices), contact_count
    )
    post_failure_input_digest = checkpoint_array_digest(*post_failure_input)
    failure_control_passed = bool(
        int(failure_process["returncode"]) != 0
        and not bool(failure_summary["passed"])
        and failure_candidate_exists
        and not failure_commit_path.exists()
        and post_failure_input_digest == expected_input_digest
        and failure_summary["source_fingerprints"]
        == expected_source_fingerprints
    )
    failure_record = {
        "worker_process": failure_process,
        "worker_process_id": worker_process_ids[-1],
        "worker_summary": str(failure_staging / "summary.json"),
        "worker_reported_pass": failure_summary["passed"],
        "worker_candidate_preserved": failure_candidate_exists,
        "accepted_checkpoint_exists": failure_commit_path.exists(),
        "input_digest_before": expected_input_digest,
        "input_digest_after": post_failure_input_digest,
        "passed": failure_control_passed,
    }
    (failure_path / "transaction_summary.json").write_text(
        json.dumps(failure_record, indent=2), encoding="utf-8"
    )
    if not failure_control_passed:
        raise RuntimeError("failure control did not preserve transaction boundary")
    print(
        f"r2 failure control rejected pid={worker_process_ids[-1]}", flush=True
    )

    all_worker_process_ids_unique = (
        len(set(worker_process_ids)) == len(worker_process_ids)
    )
    passed = bool(
        len(successful_transactions) == SUCCESS_REPLICATES
        and all(record["passed"] for record in successful_transactions)
        and failure_control_passed
        and all_worker_process_ids_unique
    )
    report = {
        "schema_version": "efe_node1_n1_2b_r2_transactional_step_v01",
        "status": (
            "passed_three_commits_and_failure_rollback"
            if passed
            else "failed_transactional_step_pilot"
        ),
        "input_checkpoint": str(input_path),
        "reference_checkpoint": str(reference_path),
        "input_array_digest": expected_input_digest,
        "reference_array_digest": reference_digest,
        "source_fingerprints": expected_source_fingerprints,
        "successful_transactions": successful_transactions,
        "failure_control": failure_record,
        "worker_process_ids": worker_process_ids,
        "all_worker_process_ids_unique": all_worker_process_ids_unique,
        "successful_commit_count": len(successful_transactions),
        "failure_controls_rejected_without_commit": 1,
        "passed": passed,
        "evidence_boundary": (
            "This validates one isolated step transaction and create-only "
            "commit behavior. It does not establish full-cycle stability or "
            "authorize periodic-driver migration."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "passed": passed}, indent=2))
    if not passed:
        raise RuntimeError(str(report["status"]))


if __name__ == "__main__":
    main()
