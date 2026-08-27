from __future__ import annotations

import argparse
import csv
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
from hybrid.efe_fast_trilayer import (  # noqa: E402
    ECMEnergyForceBackend,
    FastTrilayerModel,
    MaterialInterface,
    SurfaceLayerReference,
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    _kkt_audit,
    build_exact_volume_coordinates,
    solve_fast_trilayer_equilibrium,
    unpack_exact_volume_variables,
)
from route_h.contact_adhesion import (  # noqa: E402
    material_tether_energy_force_with_reference,
)
from route_h.distributed_active_dynamics import (  # noqa: E402
    smooth_periodic_activation,
)
from route_h.ecm_finite_strain import (  # noqa: E402
    deformation_gradient,
    relax_internal_variable_exact,
)

DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"
DEFAULT_OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_2_periodic_case_v01_20260819"
)
STEADY_SIGNALS = (
    "axial_shortening",
    "maximum_discrete_interface_traction",
    "total_stored_energy",
    "ecm_internal_z_norm",
)


def update_ecm_internal_state(
    model: FastTrilayerModel,
    ecm_vertices: np.ndarray,
    previous_internal_z: np.ndarray,
    time_step: float,
) -> tuple[np.ndarray, float]:
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


def relative_array_difference(first: np.ndarray, second: np.ndarray) -> float:
    if first.shape != second.shape:
        raise ValueError("arrays must have identical shapes")
    return float(
        np.linalg.norm(first - second)
        / max(
            1.0e-12,
            float(np.linalg.norm(first)),
            float(np.linalg.norm(second)),
        )
    )


def interface_traction_values(
    model: FastTrilayerModel,
    interface: MaterialInterface,
    layer: SurfaceLayerReference,
    layer_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> np.ndarray:
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    values: list[float] = []
    for tether in interface.tethers:
        row = row_by_id[tether.material_point_id]
        layer_face = layer.faces[int(interface.registry.face_ids[row])]
        ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
        reference_weight = float(interface.registry.reference_weights[row])
        _, layer_force, _, _ = material_tether_energy_force_with_reference(
            layer_vertices,
            layer_face,
            ecm_vertices,
            ecm_face,
            reference_master_vertices=layer.vertices,
            reference_slave_vertices=model.ecm_reference.vertices,
            master_barycentric=interface.registry.barycentric[row],
            slave_barycentric=tether.ecm_barycentric,
            reference_weight=reference_weight,
            g0_pair=tether.reference_gap,
            normal_orientation_sign=tether.normal_orientation_sign,
            reference_t1=tether.reference_t1,
            reference_t2=tether.reference_t2,
            adhesion_work=tether.adhesion_work,
            opening_cutoff=tether.opening_cutoff,
            tangential_stiffness=tether.tangential_stiffness,
        )
        values.append(
            float(np.linalg.norm(layer_force.sum(axis=0)) / reference_weight)
        )
    return np.asarray(values, dtype=np.float64)


def write_checkpoint(
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


def load_checkpoint(
    path: Path,
    model: FastTrilayerModel,
    variable_count: int,
    contact_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arrays = np.load(path)
    variables = np.asarray(arrays["variables"], dtype=np.float64).copy()
    internal_z = np.asarray(
        arrays["ecm_internal_z"], dtype=np.float64
    ).copy()
    contact_multipliers = np.asarray(
        arrays["contact_multipliers"], dtype=np.float64
    ).copy()
    if variables.shape != (variable_count,):
        raise ValueError("checkpoint variable shape mismatch")
    if internal_z.shape != (len(model.ecm_reference.tetrahedra), 3, 3):
        raise ValueError("checkpoint internal-variable shape mismatch")
    if contact_multipliers.shape != (contact_count,):
        raise ValueError("checkpoint contact-multiplier shape mismatch")
    return variables, internal_z, contact_multipliers


def run_solver(
    input_path: Path,
    output_path: Path,
    *,
    activation: float,
    dcm_level: str,
    ecm_level: str,
    footprint_scale: float,
    maximum_iterations: int,
    ecm_backend_name: str,
    method: str = "krylov",
    coarse_iterations: int = 0,
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
        "--dcm-level",
        dcm_level,
        "--ecm-level",
        ecm_level,
        "--ecm-footprint-scale",
        f"{footprint_scale:.17g}",
        "--ecm-backend",
        ecm_backend_name,
        "--skip-sparse-spectral",
        "--method",
        method,
        "--newton-iterations",
        str(maximum_iterations),
        "--maximum-follower-iterations",
        "1",
        "--maximum-contact-iterations",
        "1",
        "--contact-penalty",
        "10",
    ]
    if coarse_iterations > 0:
        command.extend(("--coarse-iterations", str(coarse_iterations)))
    else:
        command.append("--skip-coarse")
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    inherited_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_path
        if not inherited_path
        else os.pathsep.join((source_path, inherited_path))
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
    state_path = output_path / (
        f"activation_{round(100 * activation):03d}_state.npz"
    )
    return report, state_path, elapsed


def record_sample(
    model: FastTrilayerModel,
    variables: np.ndarray,
    internal_z: np.ndarray,
    *,
    cycle_index: int,
    step_index: int,
    steps_per_cycle: int,
    time_value: float,
    activation: float,
    activation_rate: float,
    coupling_iterations: int,
    coupling_residual: float,
    coupling_tolerance: float,
    dissipation_step: float,
    cumulative_dissipation: float,
    solve_seconds: float,
    ecm_backend: ECMEnergyForceBackend | None = None,
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
        ecm_backend=ecm_backend,
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
    myocyte_traction = interface_traction_values(
        model,
        model.myocyte_interface,
        model.myocyte,
        state[0],
        state[1],
    )
    endocardial_traction = interface_traction_values(
        model,
        model.endocardial_interface,
        model.endocardium,
        state[2],
        state[1],
    )
    combined_traction = np.concatenate(
        (myocyte_traction, endocardial_traction)
    )
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
        and evaluation.minimum_ecm_jacobian >= 0.5
        and evaluation.minimum_gap >= -1.0e-12
        and evaluation.minimum_myocyte_face_area_ratio >= 0.05
        and evaluation.minimum_endocardial_face_area_ratio >= 0.05
        and coupling_residual <= coupling_tolerance
        and dissipation_step >= -1.0e-14
        and symmetry_residual <= 1.0e-12
        and trace_residual <= 1.0e-12
    )
    sample = {
        "cycle": cycle_index,
        "step": step_index,
        "t_over_T": step_index / steps_per_cycle,
        "time": time_value,
        "activation": activation,
        "activation_rate": activation_rate,
        "axial_shortening": axial_shortening,
        "maximum_discrete_interface_traction": float(
            np.max(combined_traction)
        ),
        "p95_discrete_interface_traction": float(
            np.percentile(combined_traction, 95.0)
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


def write_timeseries(path: Path, samples: list[dict[str, object]]) -> None:
    fields = tuple(key for key in samples[0] if key != "volume_multipliers")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-id")
    parser.add_argument("--dcm-level", choices=("D0", "D1"), default="D0")
    parser.add_argument(
        "--ecm-level", choices=("E0", "E1", "E2"), default="E0"
    )
    parser.add_argument("--ecm-footprint-scale", type=float, default=1.5)
    parser.add_argument("--period", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--peak-activation", type=float, default=0.20)
    parser.add_argument("--cycle-tolerance", type=float, default=1.0e-3)
    parser.add_argument("--coupling-tolerance", type=float, default=1.0e-4)
    parser.add_argument("--minimum-cycles", type=int, default=2)
    parser.add_argument("--maximum-cycles", type=int, default=8)
    parser.add_argument("--warmup-only", action="store_true")
    parser.add_argument("--maximum-coupling-iterations", type=int, default=8)
    parser.add_argument("--capture-iterations", type=int, default=40)
    parser.add_argument("--maximum-solver-iterations", type=int, default=20)
    parser.add_argument("--fallback-capture-iterations", type=int, default=0)
    parser.add_argument(
        "--fallback-residual-evaluations", type=int, default=0
    )
    parser.add_argument(
        "--ecm-backend",
        choices=("reference", "fenicsx"),
        default="reference",
    )
    parser.add_argument("--initial-checkpoint", type=Path)
    arguments = parser.parse_args()

    if arguments.steps < 4 or arguments.steps % 2:
        raise ValueError("steps must be even and at least four")
    if arguments.period <= 0.0:
        raise ValueError("period must be positive")
    if arguments.minimum_cycles < 2 and not arguments.warmup_only:
        raise ValueError("minimum cycles must be at least two")
    if arguments.maximum_cycles < arguments.minimum_cycles:
        raise ValueError("maximum cycles must not be smaller than minimum")
    if arguments.warmup_only and arguments.maximum_cycles != 1:
        raise ValueError("warmup-only mode requires exactly one cycle")
    if not 0.0 < arguments.coupling_tolerance <= 1.0e-3:
        raise ValueError("coupling tolerance is outside the N1-2 range")
    if not 0.0 < arguments.cycle_tolerance <= 1.0e-3:
        raise ValueError("cycle tolerance is outside the N1-2 range")
    if min(
        arguments.fallback_capture_iterations,
        arguments.fallback_residual_evaluations,
    ) < 0:
        raise ValueError("fallback iteration counts must be nonnegative")

    case_id = arguments.case_id or (
        f"{arguments.dcm_level}_{arguments.ecm_level}_"
        f"F{round(100 * arguments.ecm_footprint_scale):03d}_"
        f"T{arguments.steps:03d}_C{arguments.coupling_tolerance:.0e}"
    )
    output_path = arguments.output.resolve() / case_id
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
    if arguments.initial_checkpoint is None:
        variables = np.zeros(len(coordinates.free_indices), dtype=np.float64)
        internal_z = np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
        )
        contact_multipliers = np.zeros(contact_count, dtype=np.float64)
    else:
        variables, internal_z, contact_multipliers = load_checkpoint(
            arguments.initial_checkpoint.resolve(),
            model,
            len(coordinates.free_indices),
            contact_count,
        )

    time_step = arguments.period / arguments.steps
    relaxation_time = 2.0 * model.eta_ve / model.mu_ve
    all_samples: list[dict[str, object]] = []
    cycle_summaries: list[dict[str, object]] = []
    previous_samples: list[dict[str, object]] | None = None
    previous_end_internal = internal_z.copy()
    status = "running_n1_2_periodic_case"
    started_all = time.perf_counter()

    for cycle_index in range(1, arguments.maximum_cycles + 1):
        cycle_path = output_path / f"cycle_{cycle_index:02d}"
        cycle_path.mkdir(parents=True, exist_ok=True)
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
            steps_per_cycle=arguments.steps,
            time_value=(cycle_index - 1) * arguments.period,
            activation=0.0,
            activation_rate=0.0,
            coupling_iterations=0,
            coupling_residual=0.0,
            coupling_tolerance=arguments.coupling_tolerance,
            dissipation_step=0.0,
            cumulative_dissipation=0.0,
            solve_seconds=0.0,
            ecm_backend=selected_ecm_backend,
        )
        samples.append(initial_sample)
        variables_history.append(variables.copy())
        myocyte_history.append(initial_state[0].copy())
        ecm_history.append(initial_state[1].copy())
        endocardial_history.append(initial_state[2].copy())
        internal_history.append(internal_z.copy())

        for step_index in range(1, arguments.steps + 1):
            phase_time = step_index * time_step
            time_value = (cycle_index - 1) * arguments.period + phase_time
            activation, activation_rate = smooth_periodic_activation(
                phase_time,
                period=arguments.period,
                peak_activation=arguments.peak_activation,
            )
            previous_internal_z = internal_z.copy()
            internal_guess = previous_internal_z.copy()
            coupling_residual = float("inf")
            solve_seconds = 0.0
            accepted_variables: np.ndarray | None = None
            accepted_internal: np.ndarray | None = None
            accepted_contact: np.ndarray | None = None
            accepted_kkt = float("inf")
            solver_passed = False

            for coupling_iteration in range(
                1, arguments.maximum_coupling_iterations + 1
            ):
                coupling_path = (
                    cycle_path
                    / f"step_{step_index:03d}"
                    / f"coupling_{coupling_iteration:02d}"
                )
                coupling_path.mkdir(parents=True, exist_ok=True)
                solver_input = coupling_path / "input_state.npz"
                capture_seconds = 0.0
                capture_kkt: float | None = None
                capture_passed = False
                capture = None
                fallback_used = "none"
                if arguments.capture_iterations > 0:
                    capture_started = time.perf_counter()
                    capture = solve_fast_trilayer_equilibrium(
                        model,
                        initial_variables=variables,
                        activation=activation,
                        pressure=0.0,
                        wss_command=np.zeros(3, dtype=np.float64),
                        ecm_internal_z=internal_guess,
                        ecm_backend=selected_ecm_backend,
                        maximum_iterations=arguments.capture_iterations,
                        maximum_newton_iterations=0,
                        maximum_follower_iterations=1,
                    )
                    capture_seconds = time.perf_counter() - capture_started
                    capture_kkt = capture.normalized_kkt_residual
                    capture_passed = bool(
                        capture.mechanical_converged
                        and capture.normalized_kkt_residual <= 1.0e-7
                        and capture.evaluation.minimum_ecm_jacobian >= 0.5
                        and capture.evaluation.minimum_gap >= -1.0e-12
                        and capture.evaluation.minimum_myocyte_face_area_ratio
                        >= 0.05
                        and capture.evaluation.minimum_endocardial_face_area_ratio
                        >= 0.05
                    )
                    variables = capture.variables.copy()
                local_seconds = 0.0
                if capture_passed and capture is not None:
                    candidate_variables = capture.variables.copy()
                    candidate_contact = contact_multipliers.copy()
                    candidate_geometry = (
                        capture.myocyte_vertices,
                        capture.ecm_vertices,
                        capture.endocardial_vertices,
                    )
                    solver_passed = True
                    (coupling_path / "capture_summary.json").write_text(
                        json.dumps(
                            {
                                "status": (
                                    "passed_strict_capture_without_sparse_refinement"
                                ),
                                "normalized_kkt_residual": capture_kkt,
                                "optimizer_iterations": capture.optimizer_iterations,
                                "optimizer_evaluations": capture.optimizer_evaluations,
                                "capture_seconds": capture_seconds,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    np.savez_compressed(
                        coupling_path / "capture_state.npz",
                        activation=np.asarray(activation),
                        variables=candidate_variables,
                        myocyte_vertices=candidate_geometry[0],
                        ecm_vertices=candidate_geometry[1],
                        endocardial_vertices=candidate_geometry[2],
                        contact_multipliers=candidate_contact,
                        ecm_internal_z=internal_guess,
                    )
                else:
                    write_checkpoint(
                        solver_input,
                        variables=variables,
                        internal_z=internal_guess,
                        contact_multipliers=contact_multipliers,
                    )
                    report, state_path, local_seconds = run_solver(
                        solver_input,
                        coupling_path,
                        activation=activation,
                        dcm_level=arguments.dcm_level,
                        ecm_level=arguments.ecm_level,
                        footprint_scale=arguments.ecm_footprint_scale,
                        maximum_iterations=arguments.maximum_solver_iterations,
                        ecm_backend_name=arguments.ecm_backend,
                    )
                    solver_passed = bool(report["passed"])
                    if (
                        not solver_passed
                        and arguments.fallback_capture_iterations > 0
                        and coupling_iteration
                        in {8, arguments.maximum_coupling_iterations}
                    ):
                        fallback_path = coupling_path / "fallback_capture"
                        (
                            fallback_report,
                            fallback_state_path,
                            fallback_seconds,
                        ) = run_solver(
                            state_path,
                            fallback_path,
                            activation=activation,
                            dcm_level=arguments.dcm_level,
                            ecm_level=arguments.ecm_level,
                            footprint_scale=arguments.ecm_footprint_scale,
                            maximum_iterations=max(
                                40, arguments.maximum_solver_iterations
                            ),
                            ecm_backend_name=arguments.ecm_backend,
                            method="krylov",
                            coarse_iterations=(
                                arguments.fallback_capture_iterations
                            ),
                        )
                        local_seconds += fallback_seconds
                        fallback_used = "extended_capture"
                        report = fallback_report
                        state_path = fallback_state_path
                        solver_passed = bool(report["passed"])
                    if (
                        not solver_passed
                        and fallback_used != "none"
                        and arguments.fallback_residual_evaluations > 0
                    ):
                        residual_path = coupling_path / "fallback_residual"
                        (
                            residual_report,
                            residual_state_path,
                            residual_seconds,
                        ) = run_solver(
                            state_path,
                            residual_path,
                            activation=activation,
                            dcm_level=arguments.dcm_level,
                            ecm_level=arguments.ecm_level,
                            footprint_scale=arguments.ecm_footprint_scale,
                            maximum_iterations=(
                                arguments.fallback_residual_evaluations
                            ),
                            ecm_backend_name=arguments.ecm_backend,
                            method="df_sane",
                        )
                        local_seconds += residual_seconds
                        fallback_used = "extended_capture_then_df_sane"
                        report = residual_report
                        state_path = residual_state_path
                        solver_passed = bool(report["passed"])
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
                solve_seconds += capture_seconds + local_seconds
                internal_candidate, _ = update_ecm_internal_state(
                    model,
                    candidate_geometry[1],
                    previous_internal_z,
                    time_step,
                )
                coupling_residual = relative_array_difference(
                    internal_candidate, internal_guess
                )
                candidate_evaluation = evaluate_fast_trilayer_state(
                    model,
                    *candidate_geometry,
                    activation=activation,
                    pressure=0.0,
                    wss_command=np.zeros(3, dtype=np.float64),
                    ecm_internal_z=internal_candidate,
                    ecm_backend=selected_ecm_backend,
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
                accepted_variables = candidate_variables
                accepted_internal = internal_candidate
                accepted_contact = candidate_contact
                variables = candidate_variables
                contact_multipliers = candidate_contact
                internal_guess = internal_candidate
                print(
                    f"{case_id} cycle={cycle_index:02d} "
                    f"step={step_index:03d}/{arguments.steps:03d} "
                    f"coupling={coupling_iteration} a={activation:.6f} "
                    f"solver_pass={solver_passed} "
                    f"capture_only={capture_passed} "
                    f"capture_KKT={capture_kkt} "
                    f"fallback={fallback_used} "
                    f"rZ={coupling_residual:.3e} "
                    f"KKT={accepted_kkt:.3e} "
                    f"seconds={capture_seconds + local_seconds:.1f}",
                    flush=True,
                )
                if (
                    solver_passed
                    and coupling_residual <= arguments.coupling_tolerance
                    and accepted_kkt <= 1.0e-5
                ):
                    break

            if (
                accepted_variables is None
                or accepted_internal is None
                or accepted_contact is None
            ):
                raise RuntimeError("coupling loop did not produce a candidate")
            if not (
                solver_passed
                and coupling_residual <= arguments.coupling_tolerance
                and accepted_kkt <= 1.0e-5
            ):
                status = (
                    f"failed_cycle_{cycle_index:02d}_step_{step_index:03d}_"
                    "coupling_gate"
                )
                failure_report = {
                    "schema_version": (
                        "efe_node1_n1_2_coupling_failure_summary_v01"
                    ),
                    "status": status,
                    "case_id": case_id,
                    "cycle": cycle_index,
                    "step": step_index,
                    "activation": activation,
                    "coupling_iterations": coupling_iteration,
                    "solver_passed": solver_passed,
                    "normalized_kkt_residual": accepted_kkt,
                    "kkt_tolerance": 1.0e-5,
                    "coupling_residual": coupling_residual,
                    "coupling_tolerance": arguments.coupling_tolerance,
                    "minimum_ecm_jacobian": (
                        candidate_evaluation.minimum_ecm_jacobian
                    ),
                    "minimum_gap": candidate_evaluation.minimum_gap,
                    "minimum_myocyte_face_area_ratio": (
                        candidate_evaluation.minimum_myocyte_face_area_ratio
                    ),
                    "minimum_endocardial_face_area_ratio": (
                        candidate_evaluation.minimum_endocardial_face_area_ratio
                    ),
                    "ecm_backend": arguments.ecm_backend,
                    "failed_coupling_directory": str(coupling_path),
                    "completed_cycle_summaries": cycle_summaries,
                    "passed": False,
                }
                (output_path / "failure_summary.json").write_text(
                    json.dumps(failure_report, indent=2), encoding="utf-8"
                )
                raise RuntimeError(status)

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
                cycle_index=cycle_index,
                step_index=step_index,
                steps_per_cycle=arguments.steps,
                time_value=time_value,
                activation=activation,
                activation_rate=activation_rate,
                coupling_iterations=coupling_iteration,
                coupling_residual=coupling_residual,
                coupling_tolerance=arguments.coupling_tolerance,
                dissipation_step=dissipation_step,
                cumulative_dissipation=cumulative_dissipation,
                solve_seconds=solve_seconds,
                ecm_backend=selected_ecm_backend,
            )
            samples.append(sample)
            variables_history.append(variables.copy())
            myocyte_history.append(state[0].copy())
            ecm_history.append(state[1].copy())
            endocardial_history.append(state[2].copy())
            internal_history.append(internal_z.copy())
            write_checkpoint(
                cycle_path / f"accepted_step_{step_index:03d}.npz",
                variables=variables,
                internal_z=internal_z,
                contact_multipliers=contact_multipliers,
            )
            if not bool(sample["passed"]):
                status = (
                    f"failed_cycle_{cycle_index:02d}_step_{step_index:03d}_"
                    "state_gate"
                )
                raise RuntimeError(status)

        np.savez_compressed(
            cycle_path / "cycle_states.npz",
            variables=np.asarray(variables_history),
            myocyte_vertices=np.asarray(myocyte_history),
            ecm_vertices=np.asarray(ecm_history),
            endocardial_vertices=np.asarray(endocardial_history),
            ecm_internal_z=np.asarray(internal_history),
        )
        write_timeseries(cycle_path / "cycle_timeseries.csv", samples)
        write_checkpoint(
            cycle_path / "cycle_end_checkpoint.npz",
            variables=variables,
            internal_z=internal_z,
            contact_multipliers=contact_multipliers,
        )
        waveform_delta = (
            None
            if previous_samples is None
            else waveform_differences(
                previous_samples, samples, STEADY_SIGNALS
            )
        )
        end_internal_delta = relative_array_difference(
            previous_end_internal, internal_z
        )
        maximum_waveform_delta = (
            None
            if waveform_delta is None
            else max(waveform_delta.values())
        )
        cycle_stable = bool(
            cycle_index >= arguments.minimum_cycles
            and maximum_waveform_delta is not None
            and maximum_waveform_delta <= arguments.cycle_tolerance
            and end_internal_delta <= arguments.cycle_tolerance
        )
        cycle_summary = {
            "cycle": cycle_index,
            "waveform_normalized_l2": waveform_delta,
            "maximum_waveform_normalized_l2": maximum_waveform_delta,
            "cycle_end_internal_z_relative_difference": end_internal_delta,
            "cycle_dissipation": cumulative_dissipation,
            "maximum_kkt": max(
                float(sample["normalized_kkt_residual"])
                for sample in samples
            ),
            "minimum_ecm_jacobian": min(
                float(sample["minimum_ecm_jacobian"])
                for sample in samples
            ),
            "minimum_gap": min(float(sample["minimum_gap"]) for sample in samples),
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
        if cycle_stable:
            status = "passed_n1_2_cycle_stability"
            break

        progress = {
            "schema_version": "efe_node1_n1_2_periodic_case_v01",
            "case_id": case_id,
            "status": status,
            "cycle_summaries": cycle_summaries,
        }
        (output_path / "progress.json").write_text(
            json.dumps(progress, indent=2), encoding="utf-8"
        )

    if arguments.warmup_only and len(cycle_summaries) == 1:
        status = "completed_n1_2_warmup_cycle_not_cycle_stability_evidence"
    elif status == "running_n1_2_periodic_case":
        status = "failed_n1_2_cycle_stability_within_maximum_cycles"
    write_timeseries(output_path / "cycle_timeseries.csv", all_samples)
    report = {
        "schema_version": "efe_node1_n1_2_periodic_case_v01",
        "status": status,
        "case_id": case_id,
        "authorization": (
            "project_control/efe_node1_n1_2_authorization_decision_v01.md"
        ),
        "dcm_level": model.dcm_level,
        "dcm_vertex_count_per_layer": len(model.myocyte.vertices),
        "dcm_face_count_per_layer": len(model.myocyte.faces),
        "ecm_level": model.ecm_level,
        "ecm_divisions": list(model.ecm_divisions),
        "ecm_vertex_count": len(model.ecm_reference.vertices),
        "ecm_tetrahedron_count": len(model.ecm_reference.tetrahedra),
        "ecm_footprint_scale": model.ecm_footprint_scale,
        "period": arguments.period,
        "steps_per_cycle": arguments.steps,
        "time_step": time_step,
        "peak_activation": arguments.peak_activation,
        "waveform_definition": "0.5*A*(1-cos(2*pi*t/T))",
        "phase_origin": "zero activation at t/T=0; peak at t/T=0.5",
        "mu_ve": model.mu_ve,
        "eta_ve": model.eta_ve,
        "relaxation_time_2eta_over_mu": relaxation_time,
        "de_tau_over_period": relaxation_time / arguments.period,
        "omega_tau": 2.0 * np.pi * relaxation_time / arguments.period,
        "cycle_tolerance": arguments.cycle_tolerance,
        "steady_signals": list(STEADY_SIGNALS),
        "waveform_difference_rule": (
            "linear interpolation to 4097 shared phases; symmetric L2 "
            "difference normalized by max of the two waveform L2 norms"
        ),
        "coupling_tolerance": arguments.coupling_tolerance,
        "maximum_coupling_iterations": arguments.maximum_coupling_iterations,
        "capture_iterations": arguments.capture_iterations,
        "maximum_solver_iterations": arguments.maximum_solver_iterations,
        "fallback_capture_iterations": (
            arguments.fallback_capture_iterations
        ),
        "fallback_residual_evaluations": (
            arguments.fallback_residual_evaluations
        ),
        "ecm_backend": arguments.ecm_backend,
        "ecm_backend_diagnostics": (
            None if fenicsx_backend is None else fenicsx_backend.diagnostics()
        ),
        "minimum_cycles": arguments.minimum_cycles,
        "maximum_cycles": arguments.maximum_cycles,
        "cycle_summaries": cycle_summaries,
        "elapsed_seconds": time.perf_counter() - started_all,
        "warmup_only": arguments.warmup_only,
        "passed": status == "passed_n1_2_cycle_stability",
        "completed": status
        in {
            "passed_n1_2_cycle_stability",
            "completed_n1_2_warmup_cycle_not_cycle_stability_evidence",
        },
        "scope": (
            "N1-2 active-only J0 periodic-state case; no N1-3 parameter "
            "screening, physiological calibration, or bidirectional FSI"
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"case_id": case_id, "status": status}, indent=2))
    if not report["completed"]:
        raise RuntimeError(status)


if __name__ == "__main__":
    main()
