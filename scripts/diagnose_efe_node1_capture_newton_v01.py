from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from hybrid.efe_fast_trilayer import build_fast_trilayer_model
from hybrid.efe_fast_trilayer_solver import solve_fast_trilayer_equilibrium


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--activation", type=float, required=True)
    parser.add_argument("--dcm-level", choices=("D0", "D1"), default="D0")
    parser.add_argument(
        "--ecm-level", choices=("E0", "E1", "E2"), default="E0"
    )
    parser.add_argument("--ecm-footprint-scale", type=float, default=1.5)
    parser.add_argument("--optimizer-iterations", type=int, default=30)
    parser.add_argument("--newton-iterations", type=int, default=20)
    arguments = parser.parse_args()

    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(
        dcm_level=arguments.dcm_level,
        ecm_level=arguments.ecm_level,
        ecm_footprint_scale=arguments.ecm_footprint_scale,
    )
    arrays = np.load(arguments.input.resolve())
    started = time.perf_counter()
    solution = solve_fast_trilayer_equilibrium(
        model,
        initial_variables=np.asarray(arrays["variables"], dtype=np.float64),
        activation=arguments.activation,
        ecm_internal_z=np.asarray(
            arrays["ecm_internal_z"], dtype=np.float64
        ),
        maximum_iterations=arguments.optimizer_iterations,
        maximum_newton_iterations=arguments.newton_iterations,
        maximum_follower_iterations=1,
    )
    elapsed = time.perf_counter() - started
    report = {
        "status": (
            "passed_capture_newton_diagnostic"
            if solution.mechanical_converged
            else "failed_capture_newton_diagnostic"
        ),
        "input": str(arguments.input.resolve()),
        "activation": arguments.activation,
        "dcm_level": model.dcm_level,
        "ecm_level": model.ecm_level,
        "ecm_footprint_scale": model.ecm_footprint_scale,
        "optimizer_iterations_allowed": arguments.optimizer_iterations,
        "newton_iterations_allowed": arguments.newton_iterations,
        "optimizer_success": solution.optimizer_success,
        "optimizer_message": solution.optimizer_message,
        "optimizer_iterations": solution.optimizer_iterations,
        "optimizer_evaluations": solution.optimizer_evaluations,
        "newton_success": solution.newton_success,
        "newton_message": solution.newton_message,
        "newton_iterations": solution.newton_iterations,
        "newton_evaluations": solution.newton_evaluations,
        "normalized_kkt_residual": solution.normalized_kkt_residual,
        "volume_constraint_residual": solution.volume_constraint_residual,
        "minimum_ecm_jacobian": solution.evaluation.minimum_ecm_jacobian,
        "minimum_gap": solution.evaluation.minimum_gap,
        "minimum_myocyte_face_area_ratio": (
            solution.evaluation.minimum_myocyte_face_area_ratio
        ),
        "minimum_endocardial_face_area_ratio": (
            solution.evaluation.minimum_endocardial_face_area_ratio
        ),
        "elapsed_seconds": elapsed,
        "passed": solution.mechanical_converged,
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    np.savez_compressed(
        output_path / "state.npz",
        activation=np.asarray(arguments.activation),
        variables=solution.variables,
        myocyte_vertices=solution.myocyte_vertices,
        ecm_vertices=solution.ecm_vertices,
        endocardial_vertices=solution.endocardial_vertices,
        ecm_internal_z=np.asarray(arrays["ecm_internal_z"], dtype=np.float64),
        contact_multipliers=np.asarray(
            arrays["contact_multipliers"], dtype=np.float64
        ),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
