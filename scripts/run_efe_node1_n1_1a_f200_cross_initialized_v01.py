from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _kkt_audit,
    build_exact_volume_coordinates,
    solve_fast_trilayer_equilibrium,
    unpack_exact_volume_variables,
)


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"
OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_1a_f200_cross_initialized_v01_20260818"
)
F150_SOURCES = (
    (
        0.02,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v02_20260818"
        / "F150/solver_step_01/activation_002_state.npz",
    ),
    (
        0.04,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v02_20260818"
        / "F150/solver_step_02/activation_004_state.npz",
    ),
    (
        0.06,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_footprint_v08_20260818"
        / "F150_a006_refined/activation_006_state.npz",
    ),
    *tuple(
        (
            activation,
            ROOT
            / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v03_20260818"
            / f"F150/solver_step_{step:02d}"
            / f"activation_{round(100 * activation):03d}_state.npz",
        )
        for step, activation in enumerate(
            np.arange(0.08, 0.201, 0.02), start=1
        )
    ),
)


def transfer_ecm_displacement(
    source_reference: np.ndarray,
    source_current: np.ndarray,
    target_reference: np.ndarray,
) -> np.ndarray:
    x_values = np.unique(source_reference[:, 0])
    y_values = np.unique(source_reference[:, 1])
    z_values = np.unique(source_reference[:, 2])
    displacement = (source_current - source_reference).reshape(
        len(x_values), len(y_values), len(z_values), 3
    )
    clipped = target_reference.copy()
    clipped[:, 0] = np.clip(clipped[:, 0], x_values[0], x_values[-1])
    clipped[:, 1] = np.clip(clipped[:, 1], y_values[0], y_values[-1])
    clipped[:, 2] = np.clip(clipped[:, 2], z_values[0], z_values[-1])
    interpolator = RegularGridInterpolator(
        (x_values, y_values, z_values),
        displacement,
        bounds_error=False,
        fill_value=None,
    )
    transferred = np.asarray(interpolator(clipped), dtype=np.float64)
    target_x = np.unique(target_reference[:, 0])
    target_z = np.unique(target_reference[:, 2])
    taper = np.ones(len(target_reference), dtype=np.float64)
    left = target_reference[:, 0] < x_values[0]
    right = target_reference[:, 0] > x_values[-1]
    lower = target_reference[:, 2] < z_values[0]
    upper = target_reference[:, 2] > z_values[-1]
    taper[left] *= (target_reference[left, 0] - target_x[0]) / (
        x_values[0] - target_x[0]
    )
    taper[right] *= (target_x[-1] - target_reference[right, 0]) / (
        target_x[-1] - x_values[-1]
    )
    taper[lower] *= (target_reference[lower, 2] - target_z[0]) / (
        z_values[0] - target_z[0]
    )
    taper[upper] *= (target_z[-1] - target_reference[upper, 2]) / (
        target_z[-1] - z_values[-1]
    )
    return target_reference + np.clip(taper, 0.0, 1.0)[:, None] * transferred


def transferred_state(
    source_model,
    target_model,
    target_coordinates,
    source_path: Path,
    output_path: Path,
) -> tuple[Path, dict[str, float]]:
    arrays = np.load(source_path)
    myocyte = np.asarray(arrays["myocyte_vertices"], dtype=np.float64)
    endocardium = np.asarray(
        arrays["endocardial_vertices"], dtype=np.float64
    )
    ecm = transfer_ecm_displacement(
        source_model.ecm_reference.vertices,
        np.asarray(arrays["ecm_vertices"], dtype=np.float64),
        target_model.ecm_reference.vertices,
    )
    full = np.concatenate(
        (myocyte.reshape(-1), ecm.reshape(-1), endocardium.reshape(-1))
    )
    variables = (
        full[target_coordinates.free_indices]
        - target_coordinates.reference_flat[target_coordinates.free_indices]
    )
    state = unpack_exact_volume_variables(
        target_model, target_coordinates, variables
    )
    evaluation = evaluate_fast_trilayer_state(
        target_model,
        *state,
        activation=float(arrays["activation"]),
        reject_penetration=False,
    )
    _, kkt = _kkt_audit(
        target_model,
        target_coordinates,
        evaluation,
        state[0],
        state[2],
        np.zeros_like(target_coordinates.reference_flat),
    )
    contact_count = len(target_model.myocyte_interface.tethers) + len(
        target_model.endocardial_interface.tethers
    )
    np.savez_compressed(
        output_path,
        activation=np.asarray(arrays["activation"]),
        variables=variables,
        myocyte_vertices=state[0],
        ecm_vertices=state[1],
        endocardial_vertices=state[2],
        contact_multipliers=np.zeros(contact_count, dtype=np.float64),
        ecm_internal_z=np.zeros(
            (len(target_model.ecm_reference.tetrahedra), 3, 3),
            dtype=np.float64,
        ),
    )
    return output_path, {
        "transfer_kkt": kkt,
        "transfer_minimum_j": evaluation.minimum_ecm_jacobian,
        "transfer_minimum_gap": evaluation.minimum_gap,
    }


def write_capture_state(path: Path, model, capture) -> None:
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    np.savez_compressed(
        path,
        activation=np.asarray(capture.activation),
        variables=capture.variables,
        myocyte_vertices=capture.myocyte_vertices,
        ecm_vertices=capture.ecm_vertices,
        endocardial_vertices=capture.endocardial_vertices,
        volume_multipliers=capture.volume_multipliers,
        contact_multipliers=np.zeros(contact_count, dtype=np.float64),
        ecm_internal_z=np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
        ),
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_model = build_fast_trilayer_model(ecm_footprint_scale=1.5)
    target_model = build_fast_trilayer_model(ecm_footprint_scale=2.0)
    coordinates = build_exact_volume_coordinates(target_model)
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    inherited_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_path
        if not inherited_path
        else os.pathsep.join((source_path, inherited_path))
    )
    records: list[dict[str, object]] = []

    reference_evaluation = evaluate_fast_trilayer_state(
        target_model,
        target_model.myocyte.vertices,
        target_model.ecm_reference.vertices,
        target_model.endocardium.vertices,
    )
    records.append(
        {
            "activation": 0.0,
            "source_state": None,
            "axial_shortening": 0.0,
            "normalized_kkt_residual": 0.0,
            "minimum_ecm_jacobian": reference_evaluation.minimum_ecm_jacobian,
            "minimum_gap": reference_evaluation.minimum_gap,
            "passed": True,
        }
    )
    status = "running_f200_cross_initialized_path"

    for step_index, (activation, source_state) in enumerate(
        F150_SOURCES, start=1
    ):
        step_path = OUTPUT / f"step_{step_index:02d}"
        step_path.mkdir(parents=True, exist_ok=True)
        transfer_path, transfer_audit = transferred_state(
            source_model,
            target_model,
            coordinates,
            source_state,
            step_path / "transfer_state.npz",
        )
        attempt_history: list[dict[str, object]] = []
        accepted_report: dict[str, object] | None = None
        accepted_state: Path | None = None
        solver_input = transfer_path
        total_seconds = 0.0
        for attempt_index, capture_iterations in enumerate((0, 60, 240), start=1):
            attempt_path = step_path / f"attempt_{attempt_index:02d}"
            attempt_path.mkdir(parents=True, exist_ok=True)
            capture_seconds = 0.0
            capture_kkt: float | None = None
            if capture_iterations:
                input_arrays = np.load(transfer_path)
                capture_started = time.perf_counter()
                capture = solve_fast_trilayer_equilibrium(
                    target_model,
                    initial_variables=np.asarray(
                        input_arrays["variables"], dtype=np.float64
                    ),
                    activation=float(activation),
                    maximum_iterations=capture_iterations,
                    maximum_newton_iterations=0,
                    maximum_follower_iterations=1,
                )
                capture_seconds = time.perf_counter() - capture_started
                capture_kkt = capture.normalized_kkt_residual
                solver_input = attempt_path / "capture_state.npz"
                write_capture_state(solver_input, target_model, capture)
            command = [
                sys.executable,
                str(DIAGNOSTIC),
                "--input",
                str(solver_input),
                "--output",
                str(attempt_path),
                "--activation",
                f"{activation:.17g}",
                "--ecm-footprint-scale",
                "2.0",
                "--skip-coarse",
                "--skip-sparse-spectral",
                "--method",
                "krylov",
                "--newton-iterations",
                "16",
            ]
            solver_started = time.perf_counter()
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            solver_seconds = time.perf_counter() - solver_started
            total_seconds += capture_seconds + solver_seconds
            if result.returncode != 0:
                attempt_history.append(
                    {
                        "attempt": attempt_index,
                        "capture_iterations": capture_iterations,
                        "capture_kkt": capture_kkt,
                        "returncode": result.returncode,
                        "passed": False,
                    }
                )
                continue
            report = json.loads(
                (attempt_path / "summary.json").read_text("utf-8")
            )
            attempt_history.append(
                {
                    "attempt": attempt_index,
                    "capture_iterations": capture_iterations,
                    "capture_kkt": capture_kkt,
                    "normalized_kkt_residual": report[
                        "normalized_kkt_residual"
                    ],
                    "capture_seconds": capture_seconds,
                    "solver_seconds": solver_seconds,
                    "passed": bool(report["passed"]),
                }
            )
            if bool(report["passed"]):
                accepted_report = report
                accepted_state = (
                    attempt_path
                    / f"activation_{round(100 * activation):03d}_state.npz"
                )
                break
        if accepted_report is None or accepted_state is None:
            status = f"failed_f200_at_a_{activation:.3f}"
            (step_path / "attempt_history.json").write_text(
                json.dumps(attempt_history, indent=2), encoding="utf-8"
            )
            break
        arrays = np.load(accepted_state)
        shortening = float(
            1.0
            - np.ptp(arrays["myocyte_vertices"][:, 0])
            / np.ptp(target_model.myocyte.vertices[:, 0])
        )
        record = {
            "activation": float(activation),
            "source_f150_state": str(source_state),
            "source_state": str(accepted_state),
            "axial_shortening": shortening,
            "normalized_kkt_residual": accepted_report[
                "normalized_kkt_residual"
            ],
            "volume_constraint_residual": accepted_report[
                "volume_constraint_residual"
            ],
            "minimum_ecm_jacobian": accepted_report[
                "minimum_ecm_jacobian"
            ],
            "minimum_gap": accepted_report["minimum_gap"],
            "minimum_myocyte_face_area_ratio": accepted_report[
                "minimum_myocyte_face_area_ratio"
            ],
            "minimum_endocardial_face_area_ratio": accepted_report[
                "minimum_endocardial_face_area_ratio"
            ],
            "transfer_audit": transfer_audit,
            "attempt_history": attempt_history,
            "total_seconds": total_seconds,
            "passed": True,
        }
        records.append(record)
        print(
            f"F200 step={step_index:02d} a={activation:.3f} "
            f"shortening={100 * shortening:.3f}% "
            f"KKT={float(record['normalized_kkt_residual']):.3e} "
            f"Jmin={float(record['minimum_ecm_jacobian']):.6f} "
            f"attempts={len(attempt_history)} seconds={total_seconds:.1f}",
            flush=True,
        )
        (OUTPUT / "progress.json").write_text(
            json.dumps(
                {
                    "schema_version": (
                        "efe_node1_n1_1a_f200_cross_initialized_v01"
                    ),
                    "status": status,
                    "records": records,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    if len(records) == len(F150_SOURCES) + 1 and all(
        bool(record["passed"]) for record in records
    ):
        status = "passed_f200_active_path_to_020"
    summary = {
        "schema_version": "efe_node1_n1_1a_f200_cross_initialized_v01",
        "status": status,
        "scope": (
            "D0 surface / density-preserving 2.0x ECM footprint audit; F150 "
            "fields are initialization only; every F200 state is independently "
            "equilibrated and gated"
        ),
        "ecm_footprint_scale": 2.0,
        "ecm_divisions": target_model.ecm_divisions,
        "ecm_vertex_count": len(target_model.ecm_reference.vertices),
        "ecm_tetrahedron_count": len(target_model.ecm_reference.tetrahedra),
        "records": records,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": status}, indent=2))
    if status != "passed_f200_active_path_to_020":
        raise RuntimeError(f"F200 path did not pass: {status}")


if __name__ == "__main__":
    main()
