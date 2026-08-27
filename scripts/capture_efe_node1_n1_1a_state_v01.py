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
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--activation", type=float, required=True)
    parser.add_argument("--iterations", type=int, default=240)
    arguments = parser.parse_args()

    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(
        dcm_level="D0",
        ecm_level="E0",
        ecm_footprint_scale=arguments.scale,
    )
    arrays = np.load(arguments.input.resolve())
    started = time.perf_counter()
    result = solve_fast_trilayer_equilibrium(
        model,
        initial_variables=np.asarray(arrays["variables"], dtype=np.float64),
        activation=arguments.activation,
        maximum_iterations=arguments.iterations,
        maximum_newton_iterations=0,
        maximum_follower_iterations=1,
    )
    elapsed = time.perf_counter() - started
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    state_path = output_path / "capture_state.npz"
    np.savez_compressed(
        state_path,
        activation=np.asarray(arguments.activation),
        variables=result.variables,
        myocyte_vertices=result.myocyte_vertices,
        ecm_vertices=result.ecm_vertices,
        endocardial_vertices=result.endocardial_vertices,
        volume_multipliers=result.volume_multipliers,
        contact_multipliers=np.zeros(contact_count, dtype=np.float64),
        ecm_internal_z=np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
        ),
    )
    report = {
        "schema_version": "efe_node1_n1_1a_capture_state_v01",
        "input": str(arguments.input.resolve()),
        "output": str(state_path),
        "ecm_footprint_scale": arguments.scale,
        "activation": arguments.activation,
        "iterations_requested": arguments.iterations,
        "optimizer_success": result.optimizer_success,
        "optimizer_message": result.optimizer_message,
        "optimizer_iterations": result.optimizer_iterations,
        "optimizer_evaluations": result.optimizer_evaluations,
        "normalized_kkt_residual": result.normalized_kkt_residual,
        "minimum_ecm_jacobian": result.evaluation.minimum_ecm_jacobian,
        "minimum_gap": result.evaluation.minimum_gap,
        "elapsed_seconds": elapsed,
        "disposition": "capture_only_not_accepted_equilibrium",
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
