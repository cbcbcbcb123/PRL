from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from hybrid.efe_fast_trilayer import build_fast_trilayer_model
from hybrid.efe_fast_trilayer_solver import solve_fast_trilayer_equilibrium


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/hybrid/efe_node1_n1_1a_footprint_v01_20260818"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--activation-step", type=float, default=0.02)
    parser.add_argument("--maximum-iterations", type=int, default=240)
    parser.add_argument("--maximum-newton-iterations", type=int, default=0)
    arguments = parser.parse_args()

    scale = float(arguments.scale)
    case_id = f"F{round(100 * scale):03d}"
    output_path = arguments.output.resolve() / case_id
    output_path.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(
        dcm_level="D0",
        ecm_level="E0",
        ecm_footprint_scale=scale,
    )
    activation_values = np.arange(
        0.0,
        0.20 + 0.5 * arguments.activation_step,
        arguments.activation_step,
    )
    variables: np.ndarray | None = None
    records: list[dict[str, object]] = []
    status = "running"

    for step_index, activation in enumerate(activation_values):
        started = time.perf_counter()
        try:
            equilibrium = solve_fast_trilayer_equilibrium(
                model,
                initial_variables=variables,
                activation=float(activation),
                maximum_iterations=arguments.maximum_iterations,
                maximum_newton_iterations=arguments.maximum_newton_iterations,
                maximum_follower_iterations=1,
            )
        except Exception as error:
            status = f"failed_exception_at_a_{activation:.3f}"
            failure = {
                "case_id": case_id,
                "activation": float(activation),
                "error_type": type(error).__name__,
                "error": str(error),
            }
            (output_path / f"failure_step_{step_index:02d}.json").write_text(
                json.dumps(failure, indent=2), encoding="utf-8"
            )
            break
        elapsed = time.perf_counter() - started
        variables = equilibrium.variables.copy()
        evaluation = equilibrium.evaluation
        axial_shortening = float(
            1.0
            - np.ptp(equilibrium.myocyte_vertices[:, 0])
            / np.ptp(model.myocyte.vertices[:, 0])
        )
        passed = bool(
            equilibrium.mechanical_converged
            and equilibrium.normalized_kkt_residual <= 1.0e-5
            and equilibrium.volume_constraint_residual <= 1.0e-8
            and evaluation.minimum_ecm_jacobian > 0.0
            and evaluation.minimum_gap >= -1.0e-12
            and evaluation.minimum_myocyte_face_area_ratio > 0.2
            and evaluation.minimum_endocardial_face_area_ratio > 0.2
            and evaluation.pair_force_residual_mj <= 1.0e-10
            and evaluation.pair_moment_residual_mj <= 1.0e-10
            and evaluation.pair_force_residual_je <= 1.0e-10
            and evaluation.pair_moment_residual_je <= 1.0e-10
        )
        record = {
            "step_index": step_index,
            "activation": float(activation),
            "axial_shortening": axial_shortening,
            "normalized_kkt_residual": equilibrium.normalized_kkt_residual,
            "volume_constraint_residual": equilibrium.volume_constraint_residual,
            "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
            "maximum_ecm_jacobian": evaluation.maximum_ecm_jacobian,
            "minimum_gap": evaluation.minimum_gap,
            "minimum_myocyte_face_area_ratio": (
                evaluation.minimum_myocyte_face_area_ratio
            ),
            "minimum_endocardial_face_area_ratio": (
                evaluation.minimum_endocardial_face_area_ratio
            ),
            "ecm_equilibrium_energy": evaluation.energy_components[
                "ecm_equilibrium"
            ],
            "ecm_viscoelastic_energy": evaluation.energy_components[
                "ecm_viscoelastic"
            ],
            "interface_myocyte_jelly_energy": evaluation.energy_components[
                "interface_myocyte_jelly"
            ],
            "interface_jelly_endocardium_energy": evaluation.energy_components[
                "interface_jelly_endocardium"
            ],
            "pair_force_residual_mj": evaluation.pair_force_residual_mj,
            "pair_moment_residual_mj": evaluation.pair_moment_residual_mj,
            "pair_force_residual_je": evaluation.pair_force_residual_je,
            "pair_moment_residual_je": evaluation.pair_moment_residual_je,
            "optimizer_success": equilibrium.optimizer_success,
            "optimizer_message": equilibrium.optimizer_message,
            "optimizer_iterations": equilibrium.optimizer_iterations,
            "optimizer_evaluations": equilibrium.optimizer_evaluations,
            "newton_success": equilibrium.newton_success,
            "newton_message": equilibrium.newton_message,
            "newton_iterations": equilibrium.newton_iterations,
            "newton_evaluations": equilibrium.newton_evaluations,
            "solve_seconds": elapsed,
            "passed": passed,
        }
        records.append(record)
        np.savez_compressed(
            output_path / f"step_{step_index:02d}.npz",
            activation=np.asarray(activation),
            variables=variables,
            myocyte_vertices=equilibrium.myocyte_vertices,
            ecm_vertices=equilibrium.ecm_vertices,
            endocardial_vertices=equilibrium.endocardial_vertices,
            volume_multipliers=equilibrium.volume_multipliers,
        )
        print(
            f"{case_id} step={step_index:02d} a={activation:.3f} "
            f"shortening={100 * axial_shortening:.3f}% "
            f"KKT={equilibrium.normalized_kkt_residual:.3e} "
            f"Jmin={evaluation.minimum_ecm_jacobian:.6f} "
            f"pass={passed} seconds={elapsed:.1f}",
            flush=True,
        )
        progress = {
            "schema_version": "efe_node1_n1_1a_footprint_path_v01",
            "case_id": case_id,
            "status": status,
            "ecm_footprint_scale": scale,
            "ecm_divisions": model.ecm_divisions,
            "ecm_vertex_count": len(model.ecm_reference.vertices),
            "ecm_tetrahedron_count": len(model.ecm_reference.tetrahedra),
            "records": records,
        }
        (output_path / "progress.json").write_text(
            json.dumps(progress, indent=2), encoding="utf-8"
        )
        if not passed:
            status = f"failed_gate_at_a_{activation:.3f}"
            break

    if len(records) == len(activation_values) and all(
        bool(record["passed"]) for record in records
    ):
        status = "passed_active_path_to_020"
    report = {
        "schema_version": "efe_node1_n1_1a_footprint_path_v01",
        "case_id": case_id,
        "status": status,
        "scope": (
            "D0/E0 active-only footprint audit; not N1-2, not time- or "
            "mesh-converged, not physiological calibration"
        ),
        "ecm_footprint_scale": scale,
        "ecm_divisions": model.ecm_divisions,
        "ecm_vertex_count": len(model.ecm_reference.vertices),
        "ecm_tetrahedron_count": len(model.ecm_reference.tetrahedra),
        "records": records,
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"case_id": case_id, "status": status}, indent=2))
    if status != "passed_active_path_to_020":
        raise RuntimeError(f"{case_id} path did not pass: {status}")


if __name__ == "__main__":
    main()
