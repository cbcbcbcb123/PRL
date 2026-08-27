from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from hybrid.efe_fast_trilayer import (
    FastTrilayerModel,
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
    evaluate_material_interface,
)
from hybrid.efe_fast_trilayer_solver import (
    _kkt_audit,
    build_exact_volume_coordinates,
    unpack_exact_volume_variables,
)
from route_h.distributed_active_dynamics import smooth_periodic_activation
from route_h.ecm_finite_strain import (
    deformation_gradient,
    relax_internal_variable_exact,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "results/hybrid/efe_node1_fast_trilayer_v01_20260817"
    / "active_only/step_00.npz"
)
DEFAULT_OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818"
)
DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"


def update_ecm_internal_state(
    model: FastTrilayerModel,
    ecm_vertices: np.ndarray,
    previous_internal_z: np.ndarray,
    time_step: float,
) -> tuple[np.ndarray, float]:
    """Relax the SLS branch exactly at fixed end-step deformation."""
    if not np.isfinite(time_step) or time_step <= 0.0:
        raise ValueError("time step must be finite and positive")
    reference = model.ecm_reference
    expected_shape = (len(reference.tetrahedra), 3, 3)
    if previous_internal_z.shape != expected_shape:
        raise ValueError("invalid ECM internal-variable shape")
    updated = np.empty_like(previous_internal_z)
    dissipation = 0.0
    for tetrahedron_id, tetrahedron in enumerate(reference.tetrahedra):
        deformation = deformation_gradient(
            ecm_vertices[tetrahedron],
            reference.dm_inverse[tetrahedron_id],
        )
        updated[tetrahedron_id] = relax_internal_variable_exact(
            deformation,
            previous_internal_z[tetrahedron_id],
            time_step,
            mu_ve=model.mu_ve,
            eta_ve=model.eta_ve,
        )
        discrete_rate = (
            updated[tetrahedron_id] - previous_internal_z[tetrahedron_id]
        ) / time_step
        dissipation += (
            time_step
            * reference.volume0[tetrahedron_id]
            * model.eta_ve
            * float(np.sum(discrete_rate * discrete_rate))
        )
    return updated, float(dissipation)


def relative_internal_residual(
    candidate: np.ndarray,
    guess: np.ndarray,
) -> float:
    return float(
        np.linalg.norm(candidate - guess)
        / max(
            1.0e-12,
            float(np.linalg.norm(candidate)),
            float(np.linalg.norm(guess)),
        )
    )


def interface_force_proxy(
    model: FastTrilayerModel,
    myocyte_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> float:
    interface = evaluate_material_interface(
        model.myocyte_interface,
        model.myocyte,
        model.ecm_reference,
        myocyte_vertices,
        ecm_vertices,
        reject_penetration=False,
    )
    return float(np.max(np.linalg.norm(interface.cell_force, axis=1)))


def write_solver_input(
    path: Path,
    *,
    variables: np.ndarray,
    internal_z: np.ndarray,
    contact_multipliers: np.ndarray,
) -> None:
    np.savez_compressed(
        path,
        variables=variables,
        ecm_internal_z=internal_z,
        contact_multipliers=contact_multipliers,
    )


def run_solver(
    input_path: Path,
    output_path: Path,
    *,
    activation: float,
    maximum_iterations: int,
) -> tuple[dict[str, object], Path, float]:
    command = [
        sys.executable,
        str(DIAGNOSTIC),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--activation",
        f"{activation:.17g}",
        "--pressure",
        "0",
        "--wss-x",
        "0",
        "--skip-coarse",
        "--method",
        "spectral_lbfgs",
        "--newton-iterations",
        str(maximum_iterations),
        "--maximum-follower-iterations",
        "1",
        "--maximum-contact-iterations",
        "2",
        "--contact-penalty",
        "10",
        "--optimizer-ftol",
        "1e-15",
        "--optimizer-gtol",
        "1e-8",
    ]
    environment = os.environ.copy()
    existing_python_path = environment.get("PYTHONPATH", "")
    source_path = str(ROOT / "src")
    environment["PYTHONPATH"] = (
        source_path
        if not existing_python_path
        else os.pathsep.join((source_path, existing_python_path))
    )
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        (output_path / "solver_failure.json").write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "command": command,
                    "stdout_tail": result.stdout[-8000:],
                    "stderr_tail": result.stderr[-8000:],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        raise RuntimeError(
            f"equilibrium solver failed in {output_path}; "
            "see solver_failure.json"
        )
    report = json.loads((output_path / "summary.json").read_text("utf-8"))
    state_path = output_path / f"activation_{round(100 * activation):03d}_state.npz"
    return report, state_path, elapsed


def record_sample(
    model: FastTrilayerModel,
    variables: np.ndarray,
    internal_z: np.ndarray,
    *,
    step_index: int,
    time_value: float,
    activation: float,
    activation_rate: float,
    coupling_iterations: int,
    coupling_residual: float,
    dissipation_step: float,
    cumulative_dissipation: float,
    solve_seconds: float,
) -> tuple[dict[str, object], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    coordinates = build_exact_volume_coordinates(model)
    state = unpack_exact_volume_variables(model, coordinates, variables)
    evaluation = evaluate_fast_trilayer_state(
        model,
        *state,
        activation=activation,
        pressure=0.0,
        wss_command=np.zeros(3, dtype=np.float64),
        ecm_internal_z=internal_z,
        reject_penetration=False,
    )
    volume_multipliers, kkt = _kkt_audit(
        model,
        coordinates,
        evaluation,
        state[0],
        state[2],
        np.zeros_like(coordinates.reference_flat),
    )
    reference_span = float(np.ptp(model.myocyte.vertices[:, 0]))
    current_span = float(np.ptp(state[0][:, 0]))
    axial_shortening = 1.0 - current_span / reference_span
    symmetry_residual = float(
        np.max(np.abs(internal_z - np.swapaxes(internal_z, 1, 2)))
    )
    trace_residual = float(
        np.max(np.abs(np.trace(internal_z, axis1=1, axis2=2)))
    )
    volume_residual = max(
        abs(evaluation.myocyte_volume_ratio - 1.0),
        abs(evaluation.endocardial_volume_ratio - 1.0),
    )
    passed = bool(
        kkt <= 1.0e-5
        and volume_residual <= 1.0e-8
        and evaluation.minimum_ecm_jacobian > 0.0
        and evaluation.minimum_gap >= -1.0e-12
        and evaluation.minimum_myocyte_face_area_ratio > 0.2
        and evaluation.minimum_endocardial_face_area_ratio > 0.2
        and coupling_residual <= 5.0e-4
        and dissipation_step >= -1.0e-14
        and symmetry_residual <= 1.0e-12
        and trace_residual <= 1.0e-12
    )
    sample = {
        "step_index": step_index,
        "time": time_value,
        "activation": activation,
        "activation_rate": activation_rate,
        "axial_shortening": axial_shortening,
        "interface_force_proxy": interface_force_proxy(
            model, state[0], state[1]
        ),
        "total_stored_energy": evaluation.total_stored_energy,
        "ecm_equilibrium_energy": evaluation.energy_components[
            "ecm_equilibrium"
        ],
        "ecm_viscoelastic_energy": evaluation.energy_components[
            "ecm_viscoelastic"
        ],
        "ecm_internal_z_norm": float(np.linalg.norm(internal_z)),
        "ecm_dissipation_step": dissipation_step,
        "cumulative_ecm_dissipation": cumulative_dissipation,
        "coupling_iterations": coupling_iterations,
        "coupling_residual": coupling_residual,
        "solve_seconds": solve_seconds,
        "normalized_kkt_residual": kkt,
        "volume_constraint_residual": volume_residual,
        "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
        "maximum_ecm_jacobian": evaluation.maximum_ecm_jacobian,
        "minimum_gap": evaluation.minimum_gap,
        "minimum_myocyte_face_area_ratio": (
            evaluation.minimum_myocyte_face_area_ratio
        ),
        "minimum_endocardial_face_area_ratio": (
            evaluation.minimum_endocardial_face_area_ratio
        ),
        "internal_symmetry_residual": symmetry_residual,
        "internal_trace_residual": trace_residual,
        "volume_multipliers": volume_multipliers.tolist(),
        "passed": passed,
    }
    return sample, state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--period", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--peak-activation", type=float, default=0.20)
    parser.add_argument("--coupling-tolerance", type=float, default=5.0e-4)
    parser.add_argument("--maximum-coupling-iterations", type=int, default=6)
    parser.add_argument("--maximum-solver-iterations", type=int, default=100)
    arguments = parser.parse_args()

    if arguments.steps < 4 or arguments.steps % 2:
        raise ValueError("steps must be even and at least four")
    if arguments.period <= 0.0:
        raise ValueError("period must be positive")
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    coordinates = build_exact_volume_coordinates(model)
    initial = np.load(arguments.input.resolve())
    variables = np.asarray(initial["variables"], dtype=np.float64).copy()
    internal_z = np.zeros(
        (len(model.ecm_reference.tetrahedra), 3, 3),
        dtype=np.float64,
    )
    reference_gaps = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    contact_multipliers = np.zeros(reference_gaps, dtype=np.float64)
    time_step = arguments.period / arguments.steps
    relaxation_time = 2.0 * model.eta_ve / model.mu_ve
    cumulative_dissipation = 0.0

    samples: list[dict[str, object]] = []
    variables_history: list[np.ndarray] = []
    myocyte_history: list[np.ndarray] = []
    ecm_history: list[np.ndarray] = []
    endocardial_history: list[np.ndarray] = []
    internal_history: list[np.ndarray] = []

    initial_sample, initial_state = record_sample(
        model,
        variables,
        internal_z,
        step_index=0,
        time_value=0.0,
        activation=0.0,
        activation_rate=0.0,
        coupling_iterations=0,
        coupling_residual=0.0,
        dissipation_step=0.0,
        cumulative_dissipation=0.0,
        solve_seconds=0.0,
    )
    samples.append(initial_sample)
    variables_history.append(variables.copy())
    myocyte_history.append(initial_state[0].copy())
    ecm_history.append(initial_state[1].copy())
    endocardial_history.append(initial_state[2].copy())
    internal_history.append(internal_z.copy())

    status = "running_n1_1_development_cycle"
    for step_index in range(1, arguments.steps + 1):
        time_value = step_index * time_step
        activation, activation_rate = smooth_periodic_activation(
            time_value,
            period=arguments.period,
            peak_activation=arguments.peak_activation,
        )
        previous_internal_z = internal_z.copy()
        internal_guess = previous_internal_z.copy()
        coupling_residual = float("inf")
        solve_seconds = 0.0
        accepted_state_path: Path | None = None
        accepted_variables: np.ndarray | None = None
        accepted_internal: np.ndarray | None = None
        accepted_contact: np.ndarray | None = None

        for coupling_iteration in range(
            1, arguments.maximum_coupling_iterations + 1
        ):
            coupling_path = (
                output_path
                / f"step_{step_index:02d}"
                / f"coupling_{coupling_iteration:02d}"
            )
            coupling_path.mkdir(parents=True, exist_ok=True)
            solver_input = coupling_path / "input_state.npz"
            write_solver_input(
                solver_input,
                variables=variables,
                internal_z=internal_guess,
                contact_multipliers=contact_multipliers,
            )
            report, state_path, local_seconds = run_solver(
                solver_input,
                coupling_path,
                activation=activation,
                maximum_iterations=arguments.maximum_solver_iterations,
            )
            solve_seconds += local_seconds
            solver_state = np.load(state_path)
            candidate_variables = np.asarray(
                solver_state["variables"], dtype=np.float64
            ).copy()
            candidate_contact = np.asarray(
                solver_state["contact_multipliers"], dtype=np.float64
            ).copy()
            candidate_geometry = unpack_exact_volume_variables(
                model,
                coordinates,
                candidate_variables,
            )
            internal_candidate, _ = update_ecm_internal_state(
                model,
                candidate_geometry[1],
                previous_internal_z,
                time_step,
            )
            coupling_residual = relative_internal_residual(
                internal_candidate,
                internal_guess,
            )
            candidate_evaluation = evaluate_fast_trilayer_state(
                model,
                *candidate_geometry,
                activation=activation,
                pressure=0.0,
                wss_command=np.zeros(3, dtype=np.float64),
                ecm_internal_z=internal_candidate,
                reject_penetration=False,
            )
            _, accepted_kkt = _kkt_audit(
                model,
                coordinates,
                candidate_evaluation,
                candidate_geometry[0],
                candidate_geometry[2],
                np.zeros_like(coordinates.reference_flat),
            )
            print(
                f"step={step_index:02d}/{arguments.steps:02d} "
                f"coupling={coupling_iteration} a={activation:.6f} "
                f"solver_pass={bool(report['passed'])} "
                f"rZ={coupling_residual:.3e} KKT(Znew)={accepted_kkt:.3e} "
                f"seconds={local_seconds:.1f}",
                flush=True,
            )
            accepted_state_path = state_path
            accepted_variables = candidate_variables
            accepted_internal = internal_candidate
            accepted_contact = candidate_contact
            variables = candidate_variables
            contact_multipliers = candidate_contact
            internal_guess = internal_candidate
            if (
                bool(report["passed"])
                and coupling_residual <= arguments.coupling_tolerance
                and accepted_kkt <= 1.0e-5
            ):
                break

        if (
            accepted_state_path is None
            or accepted_variables is None
            or accepted_internal is None
            or accepted_contact is None
        ):
            raise RuntimeError("coupling loop did not produce a candidate")

        variables = accepted_variables
        internal_z = accepted_internal
        contact_multipliers = accepted_contact
        _, dissipation_step = update_ecm_internal_state(
            model,
            unpack_exact_volume_variables(model, coordinates, variables)[1],
            previous_internal_z,
            time_step,
        )
        cumulative_dissipation += dissipation_step
        sample, state = record_sample(
            model,
            variables,
            internal_z,
            step_index=step_index,
            time_value=float(time_value),
            activation=activation,
            activation_rate=activation_rate,
            coupling_iterations=coupling_iteration,
            coupling_residual=coupling_residual,
            dissipation_step=dissipation_step,
            cumulative_dissipation=cumulative_dissipation,
            solve_seconds=solve_seconds,
        )
        samples.append(sample)
        variables_history.append(variables.copy())
        myocyte_history.append(state[0].copy())
        ecm_history.append(state[1].copy())
        endocardial_history.append(state[2].copy())
        internal_history.append(internal_z.copy())
        accepted_checkpoint = output_path / f"accepted_step_{step_index:02d}.npz"
        write_solver_input(
            accepted_checkpoint,
            variables=variables,
            internal_z=internal_z,
            contact_multipliers=contact_multipliers,
        )
        if not bool(sample["passed"]):
            status = f"failed_at_step_{step_index:02d}"
            break

        progress_report = {
            "schema_version": "efe_node1_n1_1_development_cycle_v01",
            "status": status,
            "completed_steps": step_index,
            "requested_steps": arguments.steps,
            "samples": samples,
        }
        (output_path / "progress.json").write_text(
            json.dumps(progress_report, indent=2), encoding="utf-8"
        )

    completed = len(samples) == arguments.steps + 1 and all(
        bool(sample["passed"]) for sample in samples
    )
    if completed:
        status = "passed_n1_1_single_development_cycle_d0_e0"
    elif status == "running_n1_1_development_cycle":
        status = "incomplete_n1_1_development_cycle"

    np.savez_compressed(
        output_path / "cycle_states.npz",
        variables=np.asarray(variables_history),
        myocyte_vertices=np.asarray(myocyte_history),
        ecm_vertices=np.asarray(ecm_history),
        endocardial_vertices=np.asarray(endocardial_history),
        ecm_internal_z=np.asarray(internal_history),
    )
    report = {
        "schema_version": "efe_node1_n1_1_development_cycle_v01",
        "status": status,
        "scope": (
            "D0/E0, active-only, one 16-step development cycle with staggered "
            "SLS internal-variable coupling; not time-step converged, not "
            "cycle-stable, not physiological calibration, not N1-2"
        ),
        "period": arguments.period,
        "steps_per_cycle": arguments.steps,
        "time_step": time_step,
        "peak_activation": arguments.peak_activation,
        "mu_ve": model.mu_ve,
        "eta_ve": model.eta_ve,
        "relaxation_time_2eta_over_mu": relaxation_time,
        "de_tau_over_period": relaxation_time / arguments.period,
        "omega_tau": 2.0 * np.pi * relaxation_time / arguments.period,
        "coupling_tolerance": arguments.coupling_tolerance,
        "maximum_coupling_iterations": arguments.maximum_coupling_iterations,
        "completed": completed,
        "samples": samples,
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": status, "completed": completed}, indent=2))
    if not completed:
        raise RuntimeError(f"development cycle did not pass: {status}")


if __name__ == "__main__":
    main()
