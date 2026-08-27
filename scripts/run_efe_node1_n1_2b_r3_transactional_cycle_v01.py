from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_cycle_convergence import waveform_differences  # noqa: E402
from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    build_exact_volume_coordinates,
    unpack_exact_volume_variables,
)
from hybrid.efe_step_transaction import (  # noqa: E402
    CycleStepConsistencyMetrics,
    StepOracleMetrics,
    audit_cycle_step_consistency,
    audit_transaction_candidate,
    checkpoint_array_digest,
    cycle_phase_spec,
    file_sha256,
    validation_cycle_indices,
    write_checkpoint_exclusive,
)
from run_efe_node1_n1_2_periodic_case_v01 import (  # noqa: E402
    STEADY_SIGNALS,
    load_checkpoint,
    record_sample,
    relative_array_difference,
    update_ecm_internal_state,
    write_timeseries,
)


BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
DEFAULT_INPUT = BASELINE_CASE / "cycle_02/accepted_step_016.npz"
DEFAULT_PREVIOUS_CYCLE_DIRECTORY = BASELINE_CASE / "cycle_02"
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v01_20260820"
)
DEFAULT_AUTHORIZATION = (
    "project_control/"
    "efe_node1_n1_2b_r2_acceptance_and_r3_authorization_decision_v01.md"
)
WORKER = ROOT / "scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py"
PERIODIC_RUNNER = ROOT / "scripts/run_efe_node1_n1_2_periodic_case_v01.py"
TRANSACTION_MODULE = ROOT / "src/hybrid/efe_step_transaction.py"
SOLVER_MODULE = ROOT / "src/hybrid/efe_fast_trilayer_solver.py"
BACKEND_MODULE = ROOT / "src/hybrid/fenicsx_ecm_backend.py"
DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"
WORKER_SOURCE_SET = (WORKER, SOLVER_MODULE, BACKEND_MODULE, DIAGNOSTIC)
PARENT_SOURCE_SET = (
    Path(__file__).resolve(),
    WORKER,
    PERIODIC_RUNNER,
    TRANSACTION_MODULE,
    SOLVER_MODULE,
    BACKEND_MODULE,
    DIAGNOSTIC,
)
STEPS_PER_CYCLE = 16
PERIOD = 1.0
PEAK_ACTIVATION = 0.2
COUPLING_TOLERANCE = 1.0e-4
CYCLE_TOLERANCE = 1.0e-3
MAXIMUM_COUPLING_ITERATIONS = 12


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_timeseries(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def run_worker_process(
    command: list[str], evidence_path: Path
) -> dict[str, object]:
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()
    record = {
        "command": command,
        "spawned_process_id": process.pid,
        "returncode": process.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout": stdout,
        "stderr": stderr,
    }
    evidence_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def worker_command(
    *,
    input_path: Path,
    staging_path: Path,
    cycle_index: int,
    step_index: int,
) -> list[str]:
    return [
        sys.executable,
        str(WORKER),
        "--input",
        str(input_path),
        "--baseline-case-directory",
        str(BASELINE_CASE),
        "--output",
        str(staging_path),
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
        str(MAXIMUM_COUPLING_ITERATIONS),
        "--cycle-index",
        str(cycle_index),
        "--step-index",
        str(step_index),
        "--steps-per-cycle",
        str(STEPS_PER_CYCLE),
        "--period",
        f"{PERIOD:.17g}",
        "--peak-activation",
        f"{PEAK_ACTIVATION:.17g}",
        "--execution-context",
        "transactional_cycle",
    ]


def write_failure_summary(
    output_path: Path,
    *,
    status: str,
    cycle_index: int,
    step_index: int,
    details: dict[str, object],
    run_label: str,
) -> None:
    report = {
        "schema_version": f"efe_node1_n1_2b_{run_label}_failure_v01",
        "status": status,
        "cycle": cycle_index,
        "step": step_index,
        "details": details,
        "passed": False,
        "evidence_boundary": (
            "The failed transaction was not committed. No automatic retry or "
            "gate change was attempted."
        ),
    }
    (output_path / "failure_summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--previous-cycle-directory",
        type=Path,
        default=DEFAULT_PREVIOUS_CYCLE_DIRECTORY,
    )
    parser.add_argument("--first-cycle-index", type=int, default=3)
    parser.add_argument(
        "--run-label", choices=("r3", "r4", "r5"), default="r3"
    )
    parser.add_argument("--authorization", default=DEFAULT_AUTHORIZATION)
    arguments = parser.parse_args()

    input_path = arguments.input.resolve()
    output_path = arguments.output.resolve()
    previous_cycle_directory = arguments.previous_cycle_directory.resolve()
    target_cycles = validation_cycle_indices(arguments.first_cycle_index)
    run_label = arguments.run_label
    if output_path.exists():
        raise FileExistsError(
            f"{run_label} output path already exists: {output_path}"
        )
    output_path.mkdir(parents=True)

    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

    fenicsx_backend = FenicsxECMBackend(model.ecm_reference)
    selected_ecm_backend = fenicsx_backend.energy_force
    coordinates = build_exact_volume_coordinates(model)
    variable_count = len(coordinates.free_indices)
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    variables, internal_z, contact_multipliers = load_checkpoint(
        input_path,
        model,
        variable_count,
        contact_count,
    )
    initial_input_digest = checkpoint_array_digest(
        variables, internal_z, contact_multipliers
    )
    previous_samples = read_timeseries(
        previous_cycle_directory / "cycle_timeseries.csv"
    )
    previous_end_internal = internal_z.copy()
    worker_source_fingerprints = {
        str(path.relative_to(ROOT)): file_sha256(path)
        for path in WORKER_SOURCE_SET
    }
    parent_source_fingerprints = {
        str(path.relative_to(ROOT)): file_sha256(path)
        for path in PARENT_SOURCE_SET
    }
    cycle_summaries: list[dict[str, object]] = []
    all_samples: list[dict[str, object]] = []
    worker_process_ids: list[int] = []
    accepted_transaction_count = 0
    started = time.perf_counter()

    for cycle_index in target_cycles:
        cycle_path = output_path / f"cycle_{cycle_index:02d}"
        cycle_path.mkdir(parents=True)
        samples: list[dict[str, object]] = []
        variables_history: list[np.ndarray] = []
        myocyte_history: list[np.ndarray] = []
        ecm_history: list[np.ndarray] = []
        endocardial_history: list[np.ndarray] = []
        internal_history: list[np.ndarray] = []
        cumulative_dissipation = 0.0

        initial_sample, initial_state = record_sample(
            model,
            variables,
            internal_z,
            cycle_index=cycle_index,
            step_index=0,
            steps_per_cycle=STEPS_PER_CYCLE,
            time_value=(cycle_index - 1) * PERIOD,
            activation=0.0,
            activation_rate=0.0,
            coupling_iterations=0,
            coupling_residual=0.0,
            coupling_tolerance=COUPLING_TOLERANCE,
            dissipation_step=0.0,
            cumulative_dissipation=0.0,
            solve_seconds=0.0,
            ecm_backend=selected_ecm_backend,
        )
        if not bool(initial_sample["passed"]):
            status = f"failed_cycle_{cycle_index:02d}_initial_state_gate"
            write_failure_summary(
                output_path,
                status=status,
                cycle_index=cycle_index,
                step_index=0,
                details={"initial_sample": initial_sample},
                run_label=run_label,
            )
            raise RuntimeError(status)
        samples.append(initial_sample)
        variables_history.append(variables.copy())
        myocyte_history.append(initial_state[0].copy())
        ecm_history.append(initial_state[1].copy())
        endocardial_history.append(initial_state[2].copy())
        internal_history.append(internal_z.copy())

        for step_index in range(1, STEPS_PER_CYCLE + 1):
            phase = cycle_phase_spec(
                cycle_index=cycle_index,
                step_index=step_index,
                steps_per_cycle=STEPS_PER_CYCLE,
                period=PERIOD,
                peak_activation=PEAK_ACTIVATION,
            )
            step_path = cycle_path / f"step_{step_index:03d}"
            staging_path = step_path / "worker_staging"
            step_path.mkdir(parents=True)
            expected_input_digest = checkpoint_array_digest(
                variables, internal_z, contact_multipliers
            )
            process_record = run_worker_process(
                worker_command(
                    input_path=input_path,
                    staging_path=staging_path,
                    cycle_index=cycle_index,
                    step_index=step_index,
                ),
                step_path / "worker_process.json",
            )
            if int(process_record["returncode"]) != 0:
                status = (
                    f"failed_cycle_{cycle_index:02d}_step_{step_index:03d}_"
                    "worker"
                )
                write_failure_summary(
                    output_path,
                    status=status,
                    cycle_index=cycle_index,
                    step_index=step_index,
                    details={"worker_process": process_record},
                    run_label=run_label,
                )
                raise RuntimeError(status)

            worker_summary = read_json(staging_path / "summary.json")
            worker_pid = int(worker_summary["runtime_identity"]["process_id"])
            worker_process_ids.append(worker_pid)
            if len(worker_process_ids) != len(set(worker_process_ids)):
                status = f"failed_{run_label}_worker_process_id_reuse"
                write_failure_summary(
                    output_path,
                    status=status,
                    cycle_index=cycle_index,
                    step_index=step_index,
                    details={"worker_process_ids": worker_process_ids},
                    run_label=run_label,
                )
                raise RuntimeError(status)

            candidate_path = staging_path / "final_candidate_checkpoint.npz"
            candidate_arrays = load_checkpoint(
                candidate_path,
                model,
                variable_count,
                contact_count,
            )
            candidate_variables, candidate_internal, candidate_contact = (
                candidate_arrays
            )
            candidate_digest = checkpoint_array_digest(*candidate_arrays)
            post_worker_input = load_checkpoint(
                input_path,
                model,
                variable_count,
                contact_count,
            )
            post_worker_input_digest = checkpoint_array_digest(
                *post_worker_input
            )
            candidate_state = unpack_exact_volume_variables(
                model, coordinates, candidate_variables
            )
            parent_internal, dissipation_step = update_ecm_internal_state(
                model,
                candidate_state[1],
                internal_z,
                phase.time_step,
            )
            internal_update_difference = relative_array_difference(
                candidate_internal, parent_internal
            )
            coupling_count = int(worker_summary["coupling_iterations_used"])
            final_iteration_path = (
                staging_path
                / f"coupling_{coupling_count:02d}"
                / "aitken_iteration_state.npz"
            )
            with np.load(final_iteration_path) as iteration_state:
                iteration_input_internal = np.asarray(
                    iteration_state["input_internal_z"], dtype=np.float64
                )
                iteration_candidate_digest = checkpoint_array_digest(
                    np.asarray(iteration_state["variables"], dtype=np.float64),
                    np.asarray(
                        iteration_state["raw_internal_update"],
                        dtype=np.float64,
                    ),
                    np.asarray(
                        iteration_state["contact_multipliers"],
                        dtype=np.float64,
                    ),
                )
            parent_raw_coupling_residual = relative_array_difference(
                candidate_internal, iteration_input_internal
            )
            proposed_cumulative_dissipation = (
                cumulative_dissipation + dissipation_step
            )
            parent_sample, candidate_state = record_sample(
                model,
                candidate_variables,
                candidate_internal,
                cycle_index=cycle_index,
                step_index=step_index,
                steps_per_cycle=STEPS_PER_CYCLE,
                time_value=phase.time_value,
                activation=phase.activation,
                activation_rate=phase.activation_rate,
                coupling_iterations=coupling_count,
                coupling_residual=parent_raw_coupling_residual,
                coupling_tolerance=COUPLING_TOLERANCE,
                dissipation_step=dissipation_step,
                cumulative_dissipation=proposed_cumulative_dissipation,
                solve_seconds=float(process_record["elapsed_seconds"]),
                ecm_backend=selected_ecm_backend,
            )
            oracle_metrics = StepOracleMetrics(
                normalized_kkt_residual=float(
                    parent_sample["normalized_kkt_residual"]
                ),
                raw_coupling_residual=parent_raw_coupling_residual,
                volume_constraint_residual=float(
                    parent_sample["volume_constraint_residual"]
                ),
                minimum_ecm_jacobian=float(
                    parent_sample["minimum_ecm_jacobian"]
                ),
                minimum_gap=float(parent_sample["minimum_gap"]),
                minimum_myocyte_face_area_ratio=float(
                    parent_sample["minimum_myocyte_face_area_ratio"]
                ),
                minimum_endocardial_face_area_ratio=float(
                    parent_sample["minimum_endocardial_face_area_ratio"]
                ),
                internal_symmetry_residual=float(
                    parent_sample["internal_symmetry_residual"]
                ),
                internal_trace_residual=float(
                    parent_sample["internal_trace_residual"]
                ),
            )
            oracle_audit = audit_transaction_candidate(
                worker_passed=bool(worker_summary["passed"]),
                expected_input_digest=expected_input_digest,
                worker_input_digest=str(
                    worker_summary["initial_checkpoint_array_digest"]
                ),
                post_worker_input_digest=post_worker_input_digest,
                metrics=oracle_metrics,
            )
            consistency_audit = audit_cycle_step_consistency(
                CycleStepConsistencyMetrics(
                    internal_update_symmetric_relative=(
                        internal_update_difference
                    ),
                    dissipation_step=dissipation_step,
                )
            )
            phase_checks = {
                "execution_context": (
                    worker_summary["execution_context"]
                    == "transactional_cycle"
                ),
                "cycle_index": int(worker_summary["cycle_index"])
                == cycle_index,
                "step_index": int(worker_summary["step_index"])
                == step_index,
                "activation": bool(
                    np.isclose(
                        float(worker_summary["activation"]),
                        phase.activation,
                        rtol=0.0,
                        atol=1.0e-15,
                    )
                ),
                "activation_rate": bool(
                    np.isclose(
                        float(worker_summary["activation_rate"]),
                        phase.activation_rate,
                        rtol=0.0,
                        atol=1.0e-15,
                    )
                ),
                "time_step": bool(
                    np.isclose(
                        float(worker_summary["time_step"]),
                        phase.time_step,
                        rtol=0.0,
                        atol=1.0e-15,
                    )
                ),
            }
            worker_contract_checks = {
                "spawned_pid_matches_worker": worker_pid
                == int(process_record["spawned_process_id"]),
                "worker_parent_pid_matches_driver": int(
                    worker_summary["runtime_identity"]["parent_process_id"]
                )
                == os.getpid(),
                "worker_sources_match": (
                    worker_summary["source_fingerprints"]
                    == worker_source_fingerprints
                ),
                "phase_metadata_match": all(phase_checks.values()),
                "candidate_matches_final_iteration": (
                    candidate_digest == iteration_candidate_digest
                ),
                "worker_raw_residual_matches_parent": bool(
                    np.isclose(
                        float(worker_summary["final_raw_coupling_residual"]),
                        parent_raw_coupling_residual,
                        rtol=0.0,
                        atol=1.0e-15,
                    )
                ),
                "worker_sls_recomputation_matches_parent": bool(
                    np.isclose(
                        float(
                            worker_summary[
                                "final_sls_recomputation_difference"
                            ]
                        ),
                        internal_update_difference,
                        rtol=0.0,
                        atol=1.0e-15,
                    )
                ),
                "parent_sample_gate": bool(parent_sample["passed"]),
            }
            transaction_passed = bool(
                oracle_audit["passed"]
                and consistency_audit["passed"]
                and all(worker_contract_checks.values())
            )
            transaction_record: dict[str, object] = {
                "schema_version": (
                    f"efe_node1_n1_2b_{run_label}_step_transaction_v01"
                ),
                "cycle": cycle_index,
                "step": step_index,
                "phase": asdict(phase),
                "input_checkpoint": str(input_path),
                "input_digest": expected_input_digest,
                "worker_process": process_record,
                "worker_summary": str(staging_path / "summary.json"),
                "worker_process_id": worker_pid,
                "candidate_checkpoint": str(candidate_path),
                "candidate_digest": candidate_digest,
                "parent_oracle": oracle_audit,
                "cycle_consistency": consistency_audit,
                "phase_checks": phase_checks,
                "worker_contract_checks": worker_contract_checks,
                "parent_sample": parent_sample,
                "passed_before_commit": transaction_passed,
            }
            if not transaction_passed:
                transaction_record["commit"] = None
                (step_path / "transaction_summary.json").write_text(
                    json.dumps(transaction_record, indent=2), encoding="utf-8"
                )
                status = (
                    f"failed_cycle_{cycle_index:02d}_step_{step_index:03d}_"
                    "parent_transaction_gate"
                )
                write_failure_summary(
                    output_path,
                    status=status,
                    cycle_index=cycle_index,
                    step_index=step_index,
                    details={
                        "transaction_summary": str(
                            step_path / "transaction_summary.json"
                        )
                    },
                    run_label=run_label,
                )
                raise RuntimeError(status)

            commit_path = cycle_path / f"accepted_step_{step_index:03d}.npz"
            commit_record = write_checkpoint_exclusive(
                commit_path,
                variables=candidate_variables,
                internal_z=candidate_internal,
                contact_multipliers=candidate_contact,
            )
            transaction_record["commit"] = commit_record
            transaction_record["passed"] = True
            (step_path / "transaction_summary.json").write_text(
                json.dumps(transaction_record, indent=2), encoding="utf-8"
            )
            accepted_transaction_count += 1
            variables = candidate_variables
            internal_z = candidate_internal
            contact_multipliers = candidate_contact
            input_path = commit_path
            cumulative_dissipation = proposed_cumulative_dissipation
            samples.append(parent_sample)
            variables_history.append(variables.copy())
            myocyte_history.append(candidate_state[0].copy())
            ecm_history.append(candidate_state[1].copy())
            endocardial_history.append(candidate_state[2].copy())
            internal_history.append(internal_z.copy())
            progress = {
                "schema_version": (
                    f"efe_node1_n1_2b_{run_label}_progress_v01"
                ),
                "cycle": cycle_index,
                "step": step_index,
                "accepted_transaction_count": accepted_transaction_count,
                "last_accepted_checkpoint": str(commit_path),
                "last_accepted_digest": str(commit_record["array_digest"]),
            }
            (step_path / "accepted_progress.json").write_text(
                json.dumps(progress, indent=2), encoding="utf-8"
            )
            print(
                f"{run_label} cycle={cycle_index:02d} "
                f"step={step_index:02d}/16 "
                f"pid={worker_pid} coupling={coupling_count} "
                f"rZ={parent_raw_coupling_residual:.3e} "
                f"KKT={float(parent_sample['normalized_kkt_residual']):.3e} "
                f"Jmin={float(parent_sample['minimum_ecm_jacobian']):.6f} "
                f"seconds={float(process_record['elapsed_seconds']):.1f}",
                flush=True,
            )

        np.savez_compressed(
            cycle_path / "cycle_states.npz",
            variables=np.asarray(variables_history),
            myocyte_vertices=np.asarray(myocyte_history),
            ecm_vertices=np.asarray(ecm_history),
            endocardial_vertices=np.asarray(endocardial_history),
            ecm_internal_z=np.asarray(internal_history),
        )
        write_timeseries(cycle_path / "cycle_timeseries.csv", samples)
        cycle_end_record = write_checkpoint_exclusive(
            cycle_path / "cycle_end_checkpoint.npz",
            variables=variables,
            internal_z=internal_z,
            contact_multipliers=contact_multipliers,
        )
        waveform_delta = waveform_differences(
            previous_samples, samples, STEADY_SIGNALS
        )
        end_internal_delta = relative_array_difference(
            previous_end_internal, internal_z
        )
        maximum_waveform_delta = max(waveform_delta.values())
        cycle_stable = bool(
            maximum_waveform_delta <= CYCLE_TOLERANCE
            and end_internal_delta <= CYCLE_TOLERANCE
        )
        cycle_summary = {
            "schema_version": (
                f"efe_node1_n1_2b_{run_label}_cycle_summary_v01"
            ),
            "cycle": cycle_index,
            "compared_with_cycle": cycle_index - 1,
            "waveform_normalized_l2": waveform_delta,
            "maximum_waveform_normalized_l2": maximum_waveform_delta,
            "cycle_end_internal_z_relative_difference": end_internal_delta,
            "cycle_dissipation": cumulative_dissipation,
            "maximum_kkt": max(
                float(sample["normalized_kkt_residual"])
                for sample in samples
            ),
            "minimum_ecm_jacobian": min(
                float(sample["minimum_ecm_jacobian"]) for sample in samples
            ),
            "minimum_gap": min(
                float(sample["minimum_gap"]) for sample in samples
            ),
            "maximum_coupling_residual": max(
                float(sample["coupling_residual"]) for sample in samples
            ),
            "peak_axial_shortening": max(
                float(sample["axial_shortening"]) for sample in samples
            ),
            "peak_interface_traction": max(
                float(sample["maximum_discrete_interface_traction"])
                for sample in samples
            ),
            "solve_seconds": sum(
                float(sample["solve_seconds"]) for sample in samples
            ),
            "accepted_transaction_count": STEPS_PER_CYCLE,
            "cycle_end_commit": cycle_end_record,
            "cycle_stable": cycle_stable,
        }
        (cycle_path / "cycle_summary.json").write_text(
            json.dumps(cycle_summary, indent=2), encoding="utf-8"
        )
        cycle_summaries.append(cycle_summary)
        all_samples.extend(samples)
        previous_samples = samples
        previous_end_internal = internal_z.copy()
        print(json.dumps(cycle_summary, indent=2), flush=True)

    final_cycle_stable = bool(cycle_summaries[-1]["cycle_stable"])
    status = (
        "passed_n1_2_cycle_stability_transactional"
        if final_cycle_stable
        else f"completed_{run_label}_two_cycles_not_stable"
    )
    write_timeseries(output_path / "cycle_timeseries.csv", all_samples)
    report = {
        "schema_version": (
            f"efe_node1_n1_2b_{run_label}_transactional_cycle_v01"
        ),
        "status": status,
        "authorization": arguments.authorization,
        "input_checkpoint": str(arguments.input.resolve()),
        "previous_cycle_directory": str(previous_cycle_directory),
        "initial_input_digest": initial_input_digest,
        "dcm_level": "D0",
        "ecm_level": "E0",
        "ecm_footprint_scale": 1.5,
        "period": PERIOD,
        "steps_per_cycle": STEPS_PER_CYCLE,
        "time_step": PERIOD / STEPS_PER_CYCLE,
        "peak_activation": PEAK_ACTIVATION,
        "mu_ve": model.mu_ve,
        "eta_ve": model.eta_ve,
        "coupling_tolerance": COUPLING_TOLERANCE,
        "cycle_tolerance": CYCLE_TOLERANCE,
        "maximum_coupling_iterations": MAXIMUM_COUPLING_ITERATIONS,
        "target_cycles": list(target_cycles),
        "steady_signals": list(STEADY_SIGNALS),
        "waveform_difference_rule": (
            "linear interpolation to 4097 shared phases; symmetric L2 "
            "difference normalized by max of the two waveform L2 norms"
        ),
        "worker_source_fingerprints": worker_source_fingerprints,
        "parent_source_fingerprints": parent_source_fingerprints,
        "driver_process_id": os.getpid(),
        "worker_process_ids": worker_process_ids,
        "all_worker_process_ids_unique": len(worker_process_ids)
        == len(set(worker_process_ids)),
        "accepted_transaction_count": accepted_transaction_count,
        "cycle_summaries": cycle_summaries,
        "ecm_backend_diagnostics": fenicsx_backend.diagnostics(),
        "elapsed_seconds": time.perf_counter() - started,
        "completed": True,
        "passed": final_cycle_stable,
        "evidence_boundary": (
            "This run evaluates D0/E0/F150 at T16 only. A stable result does "
            "not establish temporal or spatial convergence and requires human "
            "final review before entering formal project memory."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": status, "passed": final_cycle_stable}, indent=2))


if __name__ == "__main__":
    main()
