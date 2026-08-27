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
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _kkt_audit,
    build_exact_volume_coordinates,
    solve_fast_trilayer_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"
DEFAULT_OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v01_20260818"
)


def write_reference_state(
    path: Path,
    model,
    coordinates,
) -> dict[str, object]:
    variables = np.zeros(len(coordinates.free_indices), dtype=np.float64)
    evaluation = evaluate_fast_trilayer_state(
        model,
        model.myocyte.vertices,
        model.ecm_reference.vertices,
        model.endocardium.vertices,
        activation=0.0,
    )
    multipliers, kkt = _kkt_audit(
        model,
        coordinates,
        evaluation,
        model.myocyte.vertices,
        model.endocardium.vertices,
        np.zeros_like(coordinates.reference_flat),
    )
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    np.savez_compressed(
        path,
        activation=np.asarray(0.0),
        variables=variables,
        myocyte_vertices=model.myocyte.vertices,
        ecm_vertices=model.ecm_reference.vertices,
        endocardial_vertices=model.endocardium.vertices,
        volume_multipliers=multipliers,
        contact_multipliers=np.zeros(contact_count, dtype=np.float64),
        ecm_internal_z=np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
        ),
    )
    return {
        "step_index": 0,
        "activation": 0.0,
        "source_state": str(path),
        "axial_shortening": 0.0,
        "normalized_kkt_residual": kkt,
        "volume_constraint_residual": 0.0,
        "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
        "maximum_ecm_jacobian": evaluation.maximum_ecm_jacobian,
        "minimum_gap": evaluation.minimum_gap,
        "minimum_myocyte_face_area_ratio": 1.0,
        "minimum_endocardial_face_area_ratio": 1.0,
        "solve_seconds": 0.0,
        "passed": True,
    }


def audit_input_state(
    path: Path,
    model,
    coordinates,
    activation: float,
) -> dict[str, object]:
    arrays = np.load(path)
    state = (
        np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
        np.asarray(arrays["ecm_vertices"], dtype=np.float64),
        np.asarray(arrays["endocardial_vertices"], dtype=np.float64),
    )
    evaluation = evaluate_fast_trilayer_state(
        model,
        *state,
        activation=activation,
        reject_penetration=False,
    )
    _, kkt = _kkt_audit(
        model,
        coordinates,
        evaluation,
        state[0],
        state[2],
        np.zeros_like(coordinates.reference_flat),
    )
    volume_residual = max(
        abs(evaluation.myocyte_volume_ratio - 1.0),
        abs(evaluation.endocardial_volume_ratio - 1.0),
    )
    return {
        "step_index": 0,
        "activation": activation,
        "source_state": str(path),
        "axial_shortening": float(
            1.0
            - np.ptp(state[0][:, 0]) / np.ptp(model.myocyte.vertices[:, 0])
        ),
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
        "solve_seconds": 0.0,
        "passed": bool(
            kkt <= 1.0e-5
            and volume_residual <= 1.0e-8
            and evaluation.minimum_ecm_jacobian > 0.0
            and evaluation.minimum_gap >= -1.0e-12
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--initial-state", type=Path)
    parser.add_argument("--start-activation", type=float, default=0.0)
    parser.add_argument("--activation-step", type=float, default=0.02)
    parser.add_argument("--capture-iterations", type=int, default=60)
    parser.add_argument("--newton-iterations", type=int, default=12)
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
    coordinates = build_exact_volume_coordinates(model)
    if arguments.initial_state is None:
        reference_state = output_path / "step_00.npz"
        records = [write_reference_state(reference_state, model, coordinates)]
        previous_state = reference_state
        start_activation = 0.0
    else:
        previous_state = arguments.initial_state.resolve()
        start_activation = float(arguments.start_activation)
        records = [
            audit_input_state(
                previous_state,
                model,
                coordinates,
                start_activation,
            )
        ]
    activation_values = np.arange(
        start_activation + arguments.activation_step,
        0.20 + 0.5 * arguments.activation_step,
        arguments.activation_step,
    )
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    inherited_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_path
        if not inherited_path
        else os.pathsep.join((source_path, inherited_path))
    )
    status = "running_sparse_active_path"

    for step_index, activation in enumerate(activation_values, start=1):
        solver_output = output_path / f"solver_step_{step_index:02d}"
        solver_output.mkdir(parents=True, exist_ok=True)
        previous_arrays = np.load(previous_state)
        capture_started = time.perf_counter()
        capture = solve_fast_trilayer_equilibrium(
            model,
            initial_variables=np.asarray(
                previous_arrays["variables"], dtype=np.float64
            ),
            activation=float(activation),
            maximum_iterations=arguments.capture_iterations,
            maximum_newton_iterations=0,
            maximum_follower_iterations=1,
        )
        capture_seconds = time.perf_counter() - capture_started
        contact_count = len(model.myocyte_interface.tethers) + len(
            model.endocardial_interface.tethers
        )
        capture_state = solver_output / "capture_state.npz"
        np.savez_compressed(
            capture_state,
            activation=np.asarray(activation),
            variables=capture.variables,
            myocyte_vertices=capture.myocyte_vertices,
            ecm_vertices=capture.ecm_vertices,
            endocardial_vertices=capture.endocardial_vertices,
            volume_multipliers=capture.volume_multipliers,
            contact_multipliers=np.zeros(contact_count, dtype=np.float64),
            ecm_internal_z=np.zeros(
                (len(model.ecm_reference.tetrahedra), 3, 3),
                dtype=np.float64,
            ),
        )
        command = [
            sys.executable,
            str(DIAGNOSTIC),
            "--input",
            str(capture_state),
            "--output",
            str(solver_output),
            "--activation",
            f"{activation:.17g}",
            "--ecm-footprint-scale",
            f"{scale:.17g}",
            "--skip-coarse",
            "--skip-sparse-spectral",
            "--method",
            "krylov",
            "--newton-iterations",
            str(arguments.newton_iterations),
        ]
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
            status = f"failed_solver_at_a_{activation:.3f}"
            (solver_output / "wrapper_failure.json").write_text(
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
            break
        solver_report = json.loads(
            (solver_output / "summary.json").read_text("utf-8")
        )
        solver_state = (
            solver_output
            / f"activation_{round(100 * activation):03d}_state.npz"
        )
        arrays = np.load(solver_state)
        myocyte_vertices = np.asarray(
            arrays["myocyte_vertices"], dtype=np.float64
        )
        axial_shortening = float(
            1.0
            - np.ptp(myocyte_vertices[:, 0])
            / np.ptp(model.myocyte.vertices[:, 0])
        )
        record = {
            "step_index": step_index,
            "activation": float(activation),
            "source_state": str(solver_state),
            "source_summary": str(solver_output / "summary.json"),
            "axial_shortening": axial_shortening,
            "normalized_kkt_residual": solver_report[
                "normalized_kkt_residual"
            ],
            "volume_constraint_residual": solver_report[
                "volume_constraint_residual"
            ],
            "minimum_ecm_jacobian": solver_report[
                "minimum_ecm_jacobian"
            ],
            "minimum_gap": solver_report["minimum_gap"],
            "minimum_myocyte_face_area_ratio": solver_report[
                "minimum_myocyte_face_area_ratio"
            ],
            "minimum_endocardial_face_area_ratio": solver_report[
                "minimum_endocardial_face_area_ratio"
            ],
            "tangent_nonzeros": solver_report["tangent_nonzeros"],
            "tangent_assembly_seconds": solver_report[
                "tangent_assembly_seconds"
            ],
            "factor_seconds": solver_report["factor_seconds"],
            "newton_iterations": solver_report["newton_iterations"],
            "newton_evaluations": solver_report["newton_evaluations"],
            "capture_iterations": capture.optimizer_iterations,
            "capture_evaluations": capture.optimizer_evaluations,
            "capture_kkt": capture.normalized_kkt_residual,
            "capture_seconds": capture_seconds,
            "solve_seconds": elapsed,
            "total_step_seconds": capture_seconds + elapsed,
            "passed": bool(solver_report["passed"]),
        }
        records.append(record)
        previous_state = solver_state
        print(
            f"{case_id} step={step_index:02d} a={activation:.3f} "
            f"shortening={100 * axial_shortening:.3f}% "
            f"KKT={float(record['normalized_kkt_residual']):.3e} "
            f"Jmin={float(record['minimum_ecm_jacobian']):.6f} "
            f"pass={record['passed']} "
            f"seconds={capture_seconds + elapsed:.1f}",
            flush=True,
        )
        progress = {
            "schema_version": "efe_node1_n1_1a_sparse_footprint_path_v01",
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
        if not bool(record["passed"]):
            status = f"failed_gate_at_a_{activation:.3f}"
            break

    if len(records) == len(activation_values) + 1 and all(
        bool(record["passed"]) for record in records
    ):
        status = "passed_sparse_active_path_to_020"
    report = {
        "schema_version": "efe_node1_n1_1a_sparse_footprint_path_v01",
        "case_id": case_id,
        "status": status,
        "scope": (
            "D0/E0 active-only lateral-footprint audit; not N1-2, not "
            "formal mesh/time convergence or physiological calibration"
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
    if status != "passed_sparse_active_path_to_020":
        raise RuntimeError(f"{case_id} path did not pass: {status}")


if __name__ == "__main__":
    main()
