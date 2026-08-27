from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_cycle_convergence import (  # noqa: E402
    relax_symmetric_traceless_internal_state,
    safeguarded_vector_aitken_factor,
)
from hybrid.efe_step_transaction import (  # noqa: E402
    checkpoint_array_digest,
    cycle_phase_spec,
    file_sha256,
)
from hybrid.efe_fast_trilayer import (  # noqa: E402
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    _kkt_audit,
    build_exact_volume_coordinates,
    solve_fast_trilayer_equilibrium,
    unpack_exact_volume_variables,
)
from route_h.distributed_active_dynamics import (  # noqa: E402
    smooth_periodic_activation,
)
from run_efe_node1_n1_2_periodic_case_v01 import (  # noqa: E402
    load_checkpoint,
    record_sample,
    relative_array_difference,
    run_solver,
    update_ecm_internal_state,
    write_checkpoint,
)


DEFAULT_BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
DEFAULT_INPUT = DEFAULT_BASELINE_CASE / "cycle_03/accepted_step_003.npz"
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1a_aitken_pilot_v01_20260820"
)
DEFAULT_CYCLE_INDEX = 3
DEFAULT_STEP_INDEX = 4
DEFAULT_STEPS_PER_CYCLE = 16
DEFAULT_PERIOD = 1.0
DEFAULT_PEAK_ACTIVATION = 0.2
KKT_TOLERANCE = 1.0e-5
COUPLING_TOLERANCE = 1.0e-4
MAXIMUM_COUPLING_ITERATIONS = 12
CAPTURE_ITERATIONS = 80
MAXIMUM_SOLVER_ITERATIONS = 20
FALLBACK_CAPTURE_ITERATIONS = 1000
FALLBACK_RESIDUAL_EVALUATIONS = 2000
GATE_CRITICAL_SOURCES = (
    Path(__file__).resolve(),
    ROOT / "src/hybrid/efe_fast_trilayer_solver.py",
    ROOT / "src/hybrid/fenicsx_ecm_backend.py",
    ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py",
)


def accepted_history_checkpoint_paths(baseline_case: Path) -> list[Path]:
    """Return the recoverable accepted-state history before cycle 3 step 4."""
    paths: list[Path] = []
    for cycle_index, final_step in ((1, 16), (2, 16), (3, 3)):
        cycle_path = baseline_case / f"cycle_{cycle_index:02d}"
        for step_index in range(1, final_step + 1):
            checkpoint = cycle_path / f"accepted_step_{step_index:03d}.npz"
            if not checkpoint.is_file():
                raise FileNotFoundError(
                    f"missing recoverable history checkpoint: {checkpoint}"
                )
            paths.append(checkpoint)
    return paths


def replay_accepted_state_history(
    model,
    coordinates,
    baseline_case: Path,
    selected_ecm_backend,
    *,
    variable_count: int,
    contact_count: int,
) -> dict[str, object]:
    """Warm one backend with all recoverable accepted states in time order."""
    history_paths = accepted_history_checkpoint_paths(baseline_case)
    final_digest = ""
    for checkpoint in history_paths:
        history_variables, history_internal_z, history_contact = load_checkpoint(
            checkpoint,
            model,
            variable_count,
            contact_count,
        )
        history_geometry = unpack_exact_volume_variables(
            model, coordinates, history_variables
        )
        step_index = int(checkpoint.stem.rsplit("_", maxsplit=1)[1])
        activation, _ = smooth_periodic_activation(
            step_index / 16.0,
            period=1.0,
            peak_activation=0.2,
        )
        evaluate_fast_trilayer_state(
            model,
            *history_geometry,
            activation=activation,
            ecm_internal_z=history_internal_z,
            ecm_backend=selected_ecm_backend,
            reject_penetration=False,
        )
        final_digest = checkpoint_array_digest(
            history_variables,
            history_internal_z,
            history_contact,
        )
    return {
        "mode": "accepted_state_history",
        "recoverable_state_count": len(history_paths),
        "first_checkpoint": str(history_paths[0]),
        "last_checkpoint": str(history_paths[-1]),
        "last_checkpoint_array_digest": final_digest,
        "history_limit": (
            "Accepted-state calls are recoverable; optimizer-internal "
            "evaluation points were not archived."
        ),
    }


def chosen_baseline_state(baseline_case: Path) -> Path:
    return (
        baseline_case
        / "cycle_03/step_004/coupling_12/fallback_residual"
        / "activation_010_state.npz"
    )


def relative_state_differences(
    model,
    coordinates,
    variables: np.ndarray,
    internal_z: np.ndarray,
    baseline_variables: np.ndarray,
    baseline_internal_z: np.ndarray,
) -> dict[str, float]:
    state = unpack_exact_volume_variables(model, coordinates, variables)
    baseline_state = unpack_exact_volume_variables(
        model, coordinates, baseline_variables
    )
    return {
        "variables": relative_array_difference(variables, baseline_variables),
        "myocyte_vertices": relative_array_difference(
            state[0], baseline_state[0]
        ),
        "ecm_vertices": relative_array_difference(state[1], baseline_state[1]),
        "endocardial_vertices": relative_array_difference(
            state[2], baseline_state[2]
        ),
        "ecm_internal_z": relative_array_difference(
            internal_z, baseline_internal_z
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--baseline-case-directory", type=Path, default=DEFAULT_BASELINE_CASE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dcm-level", choices=("D0", "D1"), default="D0")
    parser.add_argument(
        "--ecm-level", choices=("E0", "E1", "E2"), default="E0"
    )
    parser.add_argument("--ecm-footprint-scale", type=float, default=1.5)
    parser.add_argument(
        "--ecm-backend", choices=("reference", "fenicsx"), default="fenicsx"
    )
    parser.add_argument(
        "--algorithm", choices=("aitken", "picard"), default="aitken"
    )
    parser.add_argument(
        "--backend-history-mode",
        choices=("cold", "accepted_states"),
        default="cold",
    )
    parser.add_argument(
        "--maximum-coupling-iterations",
        type=int,
        default=MAXIMUM_COUPLING_ITERATIONS,
    )
    parser.add_argument("--disable-fallback", action="store_true")
    parser.add_argument("--cycle-index", type=int, default=DEFAULT_CYCLE_INDEX)
    parser.add_argument("--step-index", type=int, default=DEFAULT_STEP_INDEX)
    parser.add_argument(
        "--steps-per-cycle", type=int, default=DEFAULT_STEPS_PER_CYCLE
    )
    parser.add_argument("--period", type=float, default=DEFAULT_PERIOD)
    parser.add_argument(
        "--peak-activation", type=float, default=DEFAULT_PEAK_ACTIVATION
    )
    parser.add_argument(
        "--execution-context",
        choices=("r1a_failed_step", "transactional_cycle"),
        default="r1a_failed_step",
    )
    parser.add_argument("--minimum-factor", type=float, default=0.1)
    parser.add_argument("--maximum-factor", type=float, default=1.0)
    arguments = parser.parse_args()
    if not 1 <= arguments.maximum_coupling_iterations <= 12:
        raise ValueError("maximum coupling iterations must be in [1, 12]")
    phase = cycle_phase_spec(
        cycle_index=arguments.cycle_index,
        step_index=arguments.step_index,
        steps_per_cycle=arguments.steps_per_cycle,
        period=arguments.period,
        peak_activation=arguments.peak_activation,
    )
    activation = phase.activation
    time_step = phase.time_step

    input_path = arguments.input.resolve()
    baseline_case = arguments.baseline_case_directory.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(
        dcm_level=arguments.dcm_level,
        ecm_level=arguments.ecm_level,
        ecm_footprint_scale=arguments.ecm_footprint_scale,
    )
    fenicsx_backend = None
    selected_ecm_backend = None
    if arguments.ecm_backend == "fenicsx":
        from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

        fenicsx_backend = FenicsxECMBackend(model.ecm_reference)
        selected_ecm_backend = fenicsx_backend.energy_force
    coordinates = build_exact_volume_coordinates(model)
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    variables, previous_internal_z, contact_multipliers = load_checkpoint(
        input_path,
        model,
        len(coordinates.free_indices),
        contact_count,
    )
    initial_array_digest = checkpoint_array_digest(
        variables, previous_internal_z, contact_multipliers
    )
    history_report: dict[str, object] = {
        "mode": "cold",
        "recoverable_state_count": 0,
    }
    if arguments.backend_history_mode == "accepted_states":
        history_report = replay_accepted_state_history(
            model,
            coordinates,
            baseline_case,
            selected_ecm_backend,
            variable_count=len(coordinates.free_indices),
            contact_count=contact_count,
        )
        if history_report["last_checkpoint_array_digest"] != initial_array_digest:
            raise RuntimeError(
                "history terminal state does not match the failed-step input"
            )
    post_history_array_digest = checkpoint_array_digest(
        variables, previous_internal_z, contact_multipliers
    )
    if post_history_array_digest != initial_array_digest:
        raise RuntimeError("backend history replay mutated failed-step inputs")
    internal_guess = previous_internal_z.copy()
    previous_residual_tensor: np.ndarray | None = None
    previous_factor = 1.0
    iteration_history: list[dict[str, object]] = []
    passed = False
    status = "running_n1_2b_r1a_aitken_pilot"
    started = time.perf_counter()
    final_variables = variables.copy()
    final_internal_z = previous_internal_z.copy()
    final_contact_multipliers = contact_multipliers.copy()
    final_state = unpack_exact_volume_variables(model, coordinates, variables)
    final_evaluation = evaluate_fast_trilayer_state(
        model,
        *final_state,
        activation=activation,
        ecm_internal_z=final_internal_z,
        ecm_backend=selected_ecm_backend,
        reject_penetration=False,
    )
    final_kkt = float("inf")
    final_coupling_residual = float("inf")
    final_solver_passed = False

    for coupling_iteration in range(
        1, arguments.maximum_coupling_iterations + 1
    ):
        coupling_path = output_path / f"coupling_{coupling_iteration:02d}"
        coupling_path.mkdir(parents=True, exist_ok=True)
        solver_input = coupling_path / "input_state.npz"
        capture_started = time.perf_counter()
        capture = solve_fast_trilayer_equilibrium(
            model,
            initial_variables=variables,
            activation=activation,
            pressure=0.0,
            wss_command=np.zeros(3, dtype=np.float64),
            ecm_internal_z=internal_guess,
            ecm_backend=selected_ecm_backend,
            maximum_iterations=CAPTURE_ITERATIONS,
            maximum_newton_iterations=0,
            maximum_follower_iterations=1,
        )
        capture_seconds = time.perf_counter() - capture_started
        capture_passed = bool(
            capture.mechanical_converged
            and capture.normalized_kkt_residual <= 1.0e-7
            and capture.evaluation.minimum_ecm_jacobian >= 0.5
            and capture.evaluation.minimum_gap >= -1.0e-12
            and capture.evaluation.minimum_myocyte_face_area_ratio >= 0.05
            and capture.evaluation.minimum_endocardial_face_area_ratio >= 0.05
        )
        variables = capture.variables.copy()
        local_seconds = 0.0
        fallback_used = "none"
        solver_report: dict[str, object] | None = None
        if capture_passed:
            candidate_variables = capture.variables.copy()
            candidate_contact = contact_multipliers.copy()
            candidate_geometry = (
                capture.myocyte_vertices,
                capture.ecm_vertices,
                capture.endocardial_vertices,
            )
            solver_passed = True
            solver_route = "strict_capture"
        else:
            write_checkpoint(
                solver_input,
                variables=variables,
                internal_z=internal_guess,
                contact_multipliers=contact_multipliers,
            )
            solver_report, state_path, local_seconds = run_solver(
                solver_input,
                coupling_path,
                activation=activation,
                dcm_level=arguments.dcm_level,
                ecm_level=arguments.ecm_level,
                footprint_scale=arguments.ecm_footprint_scale,
                maximum_iterations=MAXIMUM_SOLVER_ITERATIONS,
                ecm_backend_name=arguments.ecm_backend,
            )
            solver_passed = bool(solver_report["passed"])
            if (
                not solver_passed
                and not arguments.disable_fallback
                and coupling_iteration
                in {8, arguments.maximum_coupling_iterations}
            ):
                fallback_path = coupling_path / "fallback_capture"
                (
                    solver_report,
                    state_path,
                    fallback_seconds,
                ) = run_solver(
                    state_path,
                    fallback_path,
                    activation=activation,
                    dcm_level=arguments.dcm_level,
                    ecm_level=arguments.ecm_level,
                    footprint_scale=arguments.ecm_footprint_scale,
                    maximum_iterations=MAXIMUM_SOLVER_ITERATIONS,
                    ecm_backend_name=arguments.ecm_backend,
                    method="krylov",
                    coarse_iterations=FALLBACK_CAPTURE_ITERATIONS,
                )
                local_seconds += fallback_seconds
                fallback_used = "extended_capture"
                solver_passed = bool(solver_report["passed"])
            if not solver_passed and fallback_used != "none":
                fallback_path = coupling_path / "fallback_residual"
                (
                    solver_report,
                    state_path,
                    fallback_seconds,
                ) = run_solver(
                    state_path,
                    fallback_path,
                    activation=activation,
                    dcm_level=arguments.dcm_level,
                    ecm_level=arguments.ecm_level,
                    footprint_scale=arguments.ecm_footprint_scale,
                    maximum_iterations=FALLBACK_RESIDUAL_EVALUATIONS,
                    ecm_backend_name=arguments.ecm_backend,
                    method="df_sane",
                )
                local_seconds += fallback_seconds
                fallback_used = "extended_capture_then_df_sane"
                solver_passed = bool(solver_report["passed"])
            solver_state = np.load(state_path)
            candidate_variables = np.asarray(
                solver_state["variables"], dtype=np.float64
            ).copy()
            candidate_contact = np.asarray(
                solver_state["contact_multipliers"], dtype=np.float64
            ).copy()
            candidate_geometry = unpack_exact_volume_variables(
                model, coordinates, candidate_variables
            )
            solver_route = (
                fallback_used if fallback_used != "none" else "sparse_krylov"
            )

        raw_internal_update, _ = update_ecm_internal_state(
            model,
            candidate_geometry[1],
            previous_internal_z,
            time_step,
        )
        raw_residual_tensor = raw_internal_update - internal_guess
        raw_coupling_residual = relative_array_difference(
            raw_internal_update, internal_guess
        )
        candidate_evaluation = evaluate_fast_trilayer_state(
            model,
            *candidate_geometry,
            activation=activation,
            pressure=0.0,
            wss_command=np.zeros(3, dtype=np.float64),
            ecm_internal_z=raw_internal_update,
            ecm_backend=selected_ecm_backend,
            reject_penetration=False,
        )
        _, coupled_kkt = _kkt_audit(
            model,
            coordinates,
            candidate_evaluation,
            candidate_geometry[0],
            candidate_geometry[2],
            np.zeros_like(coordinates.reference_flat),
        )
        volume_residual = max(
            abs(candidate_evaluation.myocyte_volume_ratio - 1.0),
            abs(candidate_evaluation.endocardial_volume_ratio - 1.0),
        )
        raw_symmetry_residual = float(
            np.max(
                np.abs(
                    raw_internal_update
                    - np.swapaxes(raw_internal_update, axis1=1, axis2=2)
                )
            )
        )
        raw_trace_residual = float(
            np.max(
                np.abs(np.trace(raw_internal_update, axis1=1, axis2=2))
            )
        )
        state_gate_passed = bool(
            solver_passed
            and coupled_kkt <= KKT_TOLERANCE
            and raw_coupling_residual <= COUPLING_TOLERANCE
            and volume_residual <= 1.0e-8
            and candidate_evaluation.minimum_ecm_jacobian >= 0.5
            and candidate_evaluation.minimum_gap >= -1.0e-12
            and candidate_evaluation.minimum_myocyte_face_area_ratio >= 0.05
            and candidate_evaluation.minimum_endocardial_face_area_ratio >= 0.05
            and raw_symmetry_residual <= 1.0e-12
            and raw_trace_residual <= 1.0e-12
        )

        if state_gate_passed:
            relaxation_factor = None
            aitken_unconstrained = None
            aitken_clipped = False
            growth_safeguard = False
            degenerate_fallback = False
            relaxed_internal = raw_internal_update.copy()
        elif arguments.algorithm == "picard":
            relaxation_factor = 1.0
            aitken_unconstrained = None
            aitken_clipped = False
            growth_safeguard = False
            degenerate_fallback = False
            relaxed_internal = relax_symmetric_traceless_internal_state(
                internal_guess, raw_internal_update, relaxation_factor
            )
        elif previous_residual_tensor is None:
            relaxation_factor = 1.0
            aitken_unconstrained = None
            aitken_clipped = False
            growth_safeguard = False
            degenerate_fallback = False
            relaxed_internal = relax_symmetric_traceless_internal_state(
                internal_guess, raw_internal_update, relaxation_factor
            )
        else:
            decision = safeguarded_vector_aitken_factor(
                previous_residual_tensor,
                raw_residual_tensor,
                previous_factor,
                minimum_factor=arguments.minimum_factor,
                maximum_factor=arguments.maximum_factor,
            )
            relaxation_factor = decision.factor
            aitken_unconstrained = decision.unconstrained_factor
            aitken_clipped = decision.clipped
            growth_safeguard = decision.residual_growth_safeguard
            degenerate_fallback = decision.degenerate_fallback
            relaxed_internal = relax_symmetric_traceless_internal_state(
                internal_guess, raw_internal_update, relaxation_factor
            )

        symmetry_residual = float(
            np.max(
                np.abs(
                    relaxed_internal
                    - np.swapaxes(relaxed_internal, axis1=1, axis2=2)
                )
            )
        )
        trace_residual = float(
            np.max(np.abs(np.trace(relaxed_internal, axis1=1, axis2=2)))
        )
        iteration_record = {
            "coupling_iteration": coupling_iteration,
            "solver_route": solver_route,
            "solver_passed": solver_passed,
            "capture_passed": capture_passed,
            "capture_kkt": capture.normalized_kkt_residual,
            "raw_coupling_residual": raw_coupling_residual,
            "coupled_kkt": coupled_kkt,
            "volume_constraint_residual": volume_residual,
            "raw_internal_symmetry_residual": raw_symmetry_residual,
            "raw_internal_trace_residual": raw_trace_residual,
            "minimum_ecm_jacobian": (
                candidate_evaluation.minimum_ecm_jacobian
            ),
            "minimum_gap": candidate_evaluation.minimum_gap,
            "relaxation_factor": relaxation_factor,
            "aitken_unconstrained_factor": aitken_unconstrained,
            "aitken_clipped": aitken_clipped,
            "residual_growth_safeguard": growth_safeguard,
            "degenerate_aitken_fallback": degenerate_fallback,
            "relaxed_symmetry_residual": symmetry_residual,
            "relaxed_trace_residual": trace_residual,
            "capture_seconds": capture_seconds,
            "sparse_seconds": local_seconds,
            "state_gate_passed": state_gate_passed,
        }
        iteration_history.append(iteration_record)
        np.savez_compressed(
            coupling_path / "aitken_iteration_state.npz",
            input_internal_z=internal_guess,
            raw_internal_update=raw_internal_update,
            raw_residual_tensor=raw_residual_tensor,
            relaxed_internal_z=relaxed_internal,
            variables=candidate_variables,
            myocyte_vertices=candidate_geometry[0],
            ecm_vertices=candidate_geometry[1],
            endocardial_vertices=candidate_geometry[2],
            contact_multipliers=candidate_contact,
        )
        (coupling_path / "aitken_iteration_summary.json").write_text(
            json.dumps(iteration_record, indent=2), encoding="utf-8"
        )
        print(
            f"r1a algorithm={arguments.algorithm} "
            f"coupling={coupling_iteration:02d}/"
            f"{arguments.maximum_coupling_iterations:02d} "
            f"solver_pass={solver_passed} route={solver_route} "
            f"rZ={raw_coupling_residual:.3e} KKT={coupled_kkt:.3e} "
            f"omega={relaxation_factor} "
            f"seconds={capture_seconds + local_seconds:.1f}",
            flush=True,
        )

        final_variables = candidate_variables.copy()
        final_internal_z = raw_internal_update.copy()
        final_contact_multipliers = candidate_contact.copy()
        final_state = candidate_geometry
        final_evaluation = candidate_evaluation
        final_kkt = coupled_kkt
        final_coupling_residual = raw_coupling_residual
        final_solver_passed = solver_passed
        if state_gate_passed:
            passed = True
            if arguments.execution_context == "transactional_cycle":
                status = "passed_n1_2b_transactional_cycle_step_worker"
            else:
                status = (
                    "passed_n1_2b_r1a_aitken_failed_step_pilot"
                    if arguments.algorithm == "aitken"
                    else "passed_n1_2b_r1a_picard_control"
                )
            break

        variables = candidate_variables.copy()
        contact_multipliers = candidate_contact.copy()
        internal_guess = relaxed_internal.copy()
        previous_residual_tensor = raw_residual_tensor.copy()
        previous_factor = float(relaxation_factor)

    if not passed:
        if arguments.execution_context == "transactional_cycle":
            status = (
                "failed_n1_2b_transactional_cycle_step_worker_within_"
                f"{arguments.maximum_coupling_iterations}_couplings"
            )
        else:
            status = (
                "failed_n1_2b_r1a_aitken_within_"
                f"{arguments.maximum_coupling_iterations}_couplings"
                if arguments.algorithm == "aitken"
                else "failed_n1_2b_r1a_picard_control_within_"
                f"{arguments.maximum_coupling_iterations}_couplings"
            )

    write_checkpoint(
        output_path / "final_candidate_checkpoint.npz",
        variables=final_variables,
        internal_z=final_internal_z,
        contact_multipliers=final_contact_multipliers,
    )
    state_differences = None
    if arguments.execution_context == "r1a_failed_step":
        with np.load(chosen_baseline_state(baseline_case)) as baseline_arrays:
            baseline_variables = np.asarray(
                baseline_arrays["variables"], dtype=np.float64
            )
        baseline_geometry = unpack_exact_volume_variables(
            model, coordinates, baseline_variables
        )
        baseline_internal_z, _ = update_ecm_internal_state(
            model,
            baseline_geometry[1],
            previous_internal_z,
            time_step,
        )
        state_differences = relative_state_differences(
            model,
            coordinates,
            final_variables,
            final_internal_z,
            baseline_variables,
            baseline_internal_z,
        )
    recomputed_final_internal_z, final_dissipation_step = (
        update_ecm_internal_state(
            model,
            final_state[1],
            previous_internal_z,
            time_step,
        )
    )
    final_sls_recomputation_difference = relative_array_difference(
        final_internal_z, recomputed_final_internal_z
    )
    final_sample, _ = record_sample(
        model,
        final_variables,
        final_internal_z,
        cycle_index=phase.cycle_index,
        step_index=phase.step_index,
        steps_per_cycle=phase.steps_per_cycle,
        time_value=phase.time_value,
        activation=activation,
        activation_rate=phase.activation_rate,
        coupling_iterations=len(iteration_history),
        coupling_residual=final_coupling_residual,
        coupling_tolerance=COUPLING_TOLERANCE,
        dissipation_step=final_dissipation_step,
        cumulative_dissipation=final_dissipation_step,
        solve_seconds=sum(
            float(record["capture_seconds"])
            + float(record["sparse_seconds"])
            for record in iteration_history
        ),
        ecm_backend=selected_ecm_backend,
    )
    report = {
        "schema_version": (
            "efe_node1_n1_2b_transaction_step_worker_v01"
            if arguments.execution_context == "transactional_cycle"
            else "efe_node1_n1_2b_r1a_aitken_pilot_v01"
        ),
        "status": status,
        "input_checkpoint": str(input_path),
        "baseline_case_directory": str(baseline_case),
        "dcm_level": model.dcm_level,
        "ecm_level": model.ecm_level,
        "ecm_footprint_scale": model.ecm_footprint_scale,
        "execution_context": arguments.execution_context,
        "cycle_index": phase.cycle_index,
        "step_index": phase.step_index,
        "steps_per_cycle": phase.steps_per_cycle,
        "period": phase.period,
        "phase_time": phase.phase_time,
        "time_value": phase.time_value,
        "activation": activation,
        "activation_rate": phase.activation_rate,
        "peak_activation": arguments.peak_activation,
        "time_step": time_step,
        "ecm_backend": arguments.ecm_backend,
        "ecm_backend_diagnostics": (
            None if fenicsx_backend is None else fenicsx_backend.diagnostics()
        ),
        "algorithm": (
            "safeguarded_bounded_vector_aitken"
            if arguments.algorithm == "aitken"
            else "unrelaxed_picard_control"
        ),
        "backend_history": history_report,
        "initial_checkpoint_array_digest": initial_array_digest,
        "post_history_checkpoint_array_digest": post_history_array_digest,
        "history_replay_preserved_failed_step_input": (
            initial_array_digest == post_history_array_digest
        ),
        "minimum_relaxation_factor": arguments.minimum_factor,
        "maximum_relaxation_factor": arguments.maximum_factor,
        "maximum_coupling_iterations": (
            arguments.maximum_coupling_iterations
        ),
        "fallback_disabled": arguments.disable_fallback,
        "runtime_identity": {
            "process_id": os.getpid(),
            "parent_process_id": os.getppid(),
        },
        "source_fingerprints": {
            str(path.relative_to(ROOT)): file_sha256(path)
            for path in GATE_CRITICAL_SOURCES
        },
        "acceptance_uses_unrelaxed_raw_sls_map": True,
        "kkt_tolerance": KKT_TOLERANCE,
        "coupling_tolerance": COUPLING_TOLERANCE,
        "iteration_history": iteration_history,
        "coupling_iterations_used": len(iteration_history),
        "final_solver_passed": final_solver_passed,
        "final_raw_coupling_residual": final_coupling_residual,
        "final_coupled_kkt": final_kkt,
        "final_minimum_ecm_jacobian": (
            final_evaluation.minimum_ecm_jacobian
        ),
        "final_minimum_gap": final_evaluation.minimum_gap,
        "final_sample": final_sample,
        "final_dissipation_step": final_dissipation_step,
        "final_sls_recomputation_difference": (
            final_sls_recomputation_difference
        ),
        "relative_to_archived_picard_final_candidate": state_differences,
        "final_checkpoint": str(
            output_path / "final_candidate_checkpoint.npz"
        ),
        "passed": passed,
        "evidence_boundary": (
            "This is one isolated transactional-cycle step candidate. The "
            "parent driver must revalidate and commit it; worker success alone "
            "does not establish cycle stability."
            if arguments.execution_context == "transactional_cycle"
            else "This is a single failed-step solver repair pilot. Passing "
            "does not establish cycle stability or authorize a full-cycle "
            "rerun."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    summary_path = output_path / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "passed": passed}, indent=2))
    if not passed:
        raise RuntimeError(status)


if __name__ == "__main__":
    main()
