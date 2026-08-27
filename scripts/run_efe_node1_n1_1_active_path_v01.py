from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from hybrid.efe_fast_trilayer import build_fast_trilayer_model
from hybrid.efe_fast_trilayer_solver import solve_fast_trilayer_equilibrium


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "hybrid"
    / "efe_node1_fast_trilayer_v01_20260817"
    / "active_only"
)


def hard_gate_record(result) -> dict[str, float | bool]:
    evaluation = result.evaluation
    solver_success = result.mechanical_converged
    values: dict[str, float | bool] = {
        "solver_success": solver_success,
        "volume_constraint_residual": result.volume_constraint_residual,
        "normalized_kkt_residual": result.normalized_kkt_residual,
        "minimum_myocyte_face_area_ratio": (
            evaluation.minimum_myocyte_face_area_ratio
        ),
        "minimum_endocardial_face_area_ratio": (
            evaluation.minimum_endocardial_face_area_ratio
        ),
        "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
        "minimum_gap": evaluation.minimum_gap,
        "pair_force_residual_mj": evaluation.pair_force_residual_mj,
        "pair_moment_residual_mj": evaluation.pair_moment_residual_mj,
        "pair_force_residual_je": evaluation.pair_force_residual_je,
        "pair_moment_residual_je": evaluation.pair_moment_residual_je,
    }
    values["passed"] = bool(
        solver_success
        and values["volume_constraint_residual"] <= 1.0e-8
        and values["normalized_kkt_residual"] <= 1.0e-5
        and values["minimum_myocyte_face_area_ratio"] >= 0.05
        and values["minimum_endocardial_face_area_ratio"] >= 0.05
        and values["minimum_ecm_jacobian"] >= 0.5
        and values["minimum_gap"] >= -1.0e-12
        and values["pair_force_residual_mj"] <= 1.0e-10
        and values["pair_moment_residual_mj"] <= 1.0e-10
        and values["pair_force_residual_je"] <= 1.0e-10
        and values["pair_moment_residual_je"] <= 1.0e-10
    )
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--start-activation", type=float, default=0.0)
    parser.add_argument("--maximum-iterations", type=int, default=60)
    parser.add_argument("--maximum-newton-iterations", type=int, default=24)
    arguments = parser.parse_args()

    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    activation_levels = np.linspace(0.0, 0.20, 11)
    activation_levels = activation_levels[
        activation_levels >= arguments.start_activation - 1.0e-12
    ]
    variables = (
        None
        if arguments.initial_checkpoint is None
        else np.asarray(
            np.load(arguments.initial_checkpoint.resolve())["variables"],
            dtype=np.float64,
        )
    )
    records: list[dict[str, object]] = []
    status = "running"
    for step_index, activation in enumerate(activation_levels):
        start = time.perf_counter()
        result = solve_fast_trilayer_equilibrium(
            model,
            initial_variables=variables,
            activation=float(activation),
            maximum_iterations=arguments.maximum_iterations,
            maximum_newton_iterations=arguments.maximum_newton_iterations,
        )
        elapsed = time.perf_counter() - start
        variables = result.variables.copy()
        gate = hard_gate_record(result)
        axial_shortening = float(
            1.0
            - np.ptp(result.myocyte_vertices[:, 0])
            / np.ptp(model.myocyte.vertices[:, 0])
        )
        record: dict[str, object] = {
            "step_index": step_index,
            "activation": float(activation),
            "elapsed_seconds": elapsed,
            "axial_shortening": axial_shortening,
            "myocyte_area_ratio": result.evaluation.myocyte_area_ratio,
            "endocardial_area_ratio": result.evaluation.endocardial_area_ratio,
            "optimizer_success": result.optimizer_success,
            "optimizer_message": result.optimizer_message,
            "optimizer_iterations": result.optimizer_iterations,
            "optimizer_evaluations": result.optimizer_evaluations,
            "newton_success": result.newton_success,
            "newton_message": result.newton_message,
            "newton_iterations": result.newton_iterations,
            "newton_evaluations": result.newton_evaluations,
            "mechanical_converged": result.mechanical_converged,
            "preconditioner_block_scales": (
                result.preconditioner_block_scales.tolist()
            ),
            "hard_gates": gate,
        }
        records.append(record)
        np.savez_compressed(
            output / f"step_{step_index:02d}.npz",
            activation=np.asarray(activation),
            variables=result.variables,
            myocyte_vertices=result.myocyte_vertices,
            ecm_vertices=result.ecm_vertices,
            endocardial_vertices=result.endocardial_vertices,
            volume_multipliers=result.volume_multipliers,
        )
        status = "running" if gate["passed"] else "failed_hard_gate"
        summary = {
            "schema_version": "efe_node1_n1_1_active_path_v01",
            "status": status,
            "claim_scope": "D0/E0 development continuation; not mesh convergence",
            "activation_definition": (
                f"0.02-spaced continuation from {activation_levels[0]:.2f} "
                "to 0.20"
            ),
            "initial_checkpoint": (
                None
                if arguments.initial_checkpoint is None
                else str(arguments.initial_checkpoint.resolve())
            ),
            "records": records,
        }
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "step": step_index,
                    "activation": float(activation),
                    "elapsed_seconds": round(elapsed, 3),
                    "axial_shortening": axial_shortening,
                    "kkt": result.normalized_kkt_residual,
                    "newton_success": result.newton_success,
                    "passed": gate["passed"],
                }
            ),
            flush=True,
        )
        if not gate["passed"]:
            break
    if len(records) == len(activation_levels) and all(
        bool(record["hard_gates"]["passed"]) for record in records
    ):
        status = "passed_active_only_d0_e0_development_path"
        summary["status"] = status
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
    print(json.dumps({"status": status, "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()
