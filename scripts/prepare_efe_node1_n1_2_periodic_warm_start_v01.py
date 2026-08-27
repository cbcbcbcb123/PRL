from __future__ import annotations

import argparse
import json
import math
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

from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    solve_fast_trilayer_equilibrium,
)
from route_h.ecm_finite_strain import (  # noqa: E402
    deformation_gradient,
    relax_internal_variable_exact,
)


DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"


def apply_frozen_geometry_cycle(
    model,
    ecm_history: np.ndarray,
    initial_z: np.ndarray,
    time_step: float,
) -> np.ndarray:
    internal_z = initial_z.copy()
    for ecm_vertices in ecm_history[1:]:
        updated = np.empty_like(internal_z)
        for tetrahedron_id, tetrahedron in enumerate(
            model.ecm_reference.tetrahedra
        ):
            deformation = deformation_gradient(
                ecm_vertices[tetrahedron],
                model.ecm_reference.dm_inverse[tetrahedron_id],
            )
            updated[tetrahedron_id] = relax_internal_variable_exact(
                deformation,
                internal_z[tetrahedron_id],
                time_step,
                mu_ve=model.mu_ve,
                eta_ve=model.eta_ve,
            )
        internal_z = updated
    return internal_z


def relative_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(
        np.linalg.norm(first - second)
        / max(
            1.0e-12,
            float(np.linalg.norm(first)),
            float(np.linalg.norm(second)),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dcm-level", choices=("D0", "D1"), default="D0")
    parser.add_argument(
        "--ecm-level", choices=("E0", "E1", "E2"), default="E0"
    )
    parser.add_argument("--ecm-footprint-scale", type=float, default=1.5)
    parser.add_argument("--period", type=float, default=1.0)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--capture-iterations", type=int, default=60)
    parser.add_argument("--newton-iterations", type=int, default=20)
    parser.add_argument(
        "--ecm-backend",
        choices=("reference", "fenicsx"),
        default="reference",
    )
    arguments = parser.parse_args()

    cycle_directory = arguments.cycle_directory.resolve()
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
    arrays = np.load(cycle_directory / "cycle_states.npz")
    ecm_history = np.asarray(arrays["ecm_vertices"], dtype=np.float64)
    variables_history = np.asarray(arrays["variables"], dtype=np.float64)
    if len(ecm_history) != arguments.steps + 1:
        raise ValueError("source cycle does not match requested step count")
    zero_z = np.zeros(
        (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
    )
    time_step = arguments.period / arguments.steps
    zero_start_end = apply_frozen_geometry_cycle(
        model, ecm_history, zero_z, time_step
    )
    cycle_decay = math.exp(
        -model.mu_ve * arguments.period / (2.0 * model.eta_ve)
    )
    periodic_z = zero_start_end / (1.0 - cycle_decay)
    frozen_end = apply_frozen_geometry_cycle(
        model, ecm_history, periodic_z, time_step
    )
    frozen_periodicity_residual = relative_difference(periodic_z, frozen_end)

    source_end = np.load(cycle_directory / "cycle_end_checkpoint.npz")
    contact_multipliers = np.asarray(
        source_end["contact_multipliers"], dtype=np.float64
    )
    started = time.perf_counter()
    capture = solve_fast_trilayer_equilibrium(
        model,
        initial_variables=variables_history[-1],
        activation=0.0,
        ecm_internal_z=periodic_z,
        ecm_backend=selected_ecm_backend,
        maximum_iterations=arguments.capture_iterations,
        maximum_newton_iterations=0,
        maximum_follower_iterations=1,
    )
    capture_seconds = time.perf_counter() - started
    capture_passed = bool(
        capture.mechanical_converged
        and capture.normalized_kkt_residual <= 1.0e-5
        and capture.evaluation.minimum_ecm_jacobian >= 0.5
        and capture.evaluation.minimum_gap >= -1.0e-12
        and capture.evaluation.minimum_myocyte_face_area_ratio >= 0.05
        and capture.evaluation.minimum_endocardial_face_area_ratio >= 0.05
    )
    capture_checkpoint = output_path / "capture_checkpoint.npz"
    np.savez_compressed(
        capture_checkpoint,
        variables=capture.variables,
        ecm_internal_z=periodic_z,
        contact_multipliers=contact_multipliers,
    )
    sparse_seconds = 0.0
    if capture_passed:
        final_checkpoint = output_path / "periodic_warm_start_checkpoint.npz"
        np.savez_compressed(
            final_checkpoint,
            variables=capture.variables,
            ecm_internal_z=periodic_z,
            contact_multipliers=contact_multipliers,
        )
        final_kkt = capture.normalized_kkt_residual
        final_minimum_j = capture.evaluation.minimum_ecm_jacobian
        final_minimum_gap = capture.evaluation.minimum_gap
        sparse_report = None
    else:
        sparse_path = output_path / "sparse_refinement"
        command = [
            sys.executable,
            str(DIAGNOSTIC),
            "--input",
            str(capture_checkpoint),
            "--output",
            str(sparse_path),
            "--activation",
            "0",
            "--dcm-level",
            arguments.dcm_level,
            "--ecm-level",
            arguments.ecm_level,
            "--ecm-footprint-scale",
            f"{arguments.ecm_footprint_scale:.17g}",
            "--ecm-backend",
            arguments.ecm_backend,
            "--skip-coarse",
            "--skip-sparse-spectral",
            "--method",
            "krylov",
            "--newton-iterations",
            str(arguments.newton_iterations),
            "--maximum-follower-iterations",
            "1",
            "--maximum-contact-iterations",
            "1",
            "--contact-penalty",
            "10",
        ]
        environment = os.environ.copy()
        source_path = str(ROOT / "src")
        inherited_path = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            source_path
            if not inherited_path
            else os.pathsep.join((source_path, inherited_path))
        )
        sparse_started = time.perf_counter()
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        sparse_seconds = time.perf_counter() - sparse_started
        if result.returncode != 0:
            (output_path / "failure.json").write_text(
                json.dumps(
                    {
                        "status": "failed_periodic_warm_start_refinement",
                        "returncode": result.returncode,
                        "stdout_tail": result.stdout[-8000:],
                        "stderr_tail": result.stderr[-8000:],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            raise RuntimeError("periodic warm-start sparse refinement failed")
        sparse_report = json.loads(
            (sparse_path / "summary.json").read_text("utf-8")
        )
        sparse_state = np.load(sparse_path / "activation_000_state.npz")
        final_checkpoint = output_path / "periodic_warm_start_checkpoint.npz"
        np.savez_compressed(
            final_checkpoint,
            variables=np.asarray(sparse_state["variables"], dtype=np.float64),
            ecm_internal_z=periodic_z,
            contact_multipliers=np.asarray(
                sparse_state["contact_multipliers"], dtype=np.float64
            ),
        )
        final_kkt = float(sparse_report["normalized_kkt_residual"])
        final_minimum_j = float(sparse_report["minimum_ecm_jacobian"])
        final_minimum_gap = float(sparse_report["minimum_gap"])

    passed = bool(
        frozen_periodicity_residual <= 1.0e-12
        and final_kkt <= 1.0e-5
        and final_minimum_j >= 0.5
        and final_minimum_gap >= -1.0e-12
        and (sparse_report is None or bool(sparse_report["passed"]))
    )
    report = {
        "schema_version": "efe_node1_n1_2_periodic_warm_start_v02",
        "status": (
            "passed_periodic_warm_start"
            if passed
            else "failed_periodic_warm_start"
        ),
        "source_cycle_directory": str(cycle_directory),
        "dcm_level": model.dcm_level,
        "ecm_level": model.ecm_level,
        "ecm_footprint_scale": model.ecm_footprint_scale,
        "ecm_backend": arguments.ecm_backend,
        "ecm_backend_diagnostics": (
            None if fenicsx_backend is None else fenicsx_backend.diagnostics()
        ),
        "steps_per_cycle": arguments.steps,
        "cycle_decay": cycle_decay,
        "zero_start_end_internal_z_norm": float(
            np.linalg.norm(zero_start_end)
        ),
        "periodic_internal_z_norm": float(np.linalg.norm(periodic_z)),
        "frozen_geometry_periodicity_residual": frozen_periodicity_residual,
        "capture_seconds": capture_seconds,
        "capture_kkt": capture.normalized_kkt_residual,
        "capture_mechanical_converged": capture.mechanical_converged,
        "capture_passed": capture_passed,
        "sparse_seconds": sparse_seconds,
        "sparse_method": (
            None if sparse_report is None else sparse_report["solver_method"]
        ),
        "sparse_residual_safeguard_triggered": (
            None
            if sparse_report is None
            else sparse_report["residual_safeguard_triggered"]
        ),
        "final_kkt": final_kkt,
        "final_minimum_ecm_jacobian": final_minimum_j,
        "final_minimum_gap": final_minimum_gap,
        "final_checkpoint": str(final_checkpoint),
        "passed": passed,
        "evidence_boundary": (
            "This analytically periodic SLS state is a warm start under the "
            "frozen source-cycle geometry. N1-2 cycle stability still requires "
            "two subsequent consecutive fully coupled cycles to pass the "
            "registered waveform L2 gate."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if not passed:
        raise RuntimeError("periodic warm start did not pass")


if __name__ == "__main__":
    main()
