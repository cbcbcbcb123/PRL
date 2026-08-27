from __future__ import annotations

# The container entry point appends the repository source tree while preserving
# the image-owned DOLFINx path.
# ruff: noqa: E402

import argparse
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

from hybrid.efe_fast_trilayer import (
    MaterialInterface,
    SurfaceLayerReference,
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _full_external_force,
    _kkt_audit,
    build_exact_volume_coordinates,
    solve_fast_trilayer_equilibrium,
)
from hybrid.fenicsx_ecm_backend import FenicsxECMBackend
from route_h.contact_adhesion import material_tether_energy_force_with_reference


BASELINE_ROOT = (
    ROOT
    / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v03_20260818/F150"
)
DEFAULT_SOURCE = BASELINE_ROOT / "solver_step_06/activation_018_state.npz"
DEFAULT_TARGET = BASELINE_ROOT / "solver_step_07/activation_020_state.npz"
DEFAULT_REFERENCE_CAPTURE = BASELINE_ROOT / "solver_step_07/capture_state.npz"
DEFAULT_REFERENCE_SUMMARY = BASELINE_ROOT / "solver_step_07/summary.json"
DEFAULT_REFERENCE_PROGRESS = BASELINE_ROOT / "progress.json"
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819"
    / "fenicsx_phase_b_coupled_peak_v01"
)
DIAGNOSTIC = ROOT / "scripts/diagnose_efe_node1_sparse_preconditioner_v01.py"


def relative_error(actual: np.ndarray | float, expected: np.ndarray | float) -> float:
    difference = float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)))
    scale = max(
        1.0e-14,
        float(np.linalg.norm(np.asarray(actual))),
        float(np.linalg.norm(np.asarray(expected))),
    )
    return difference / scale


def axial_shortening(model, myocyte_vertices: np.ndarray) -> float:
    return float(
        1.0
        - np.ptp(myocyte_vertices[:, 0])
        / np.ptp(model.myocyte.vertices[:, 0])
    )


def interface_force_metrics(
    interface: MaterialInterface,
    cell_reference: SurfaceLayerReference,
    ecm_reference,
    cell_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> dict[str, object]:
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    transmitted_forces = []
    traction_magnitudes = []
    for tether in interface.tethers:
        row = row_by_id[tether.material_point_id]
        cell_face = cell_reference.faces[int(interface.registry.face_ids[row])]
        ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
        _, local_cell_force, _, _ = material_tether_energy_force_with_reference(
            cell_vertices,
            cell_face,
            ecm_vertices,
            ecm_face,
            reference_master_vertices=cell_reference.vertices,
            reference_slave_vertices=ecm_reference.vertices,
            master_barycentric=interface.registry.barycentric[row],
            slave_barycentric=tether.ecm_barycentric,
            reference_weight=float(interface.registry.reference_weights[row]),
            g0_pair=tether.reference_gap,
            normal_orientation_sign=tether.normal_orientation_sign,
            reference_t1=tether.reference_t1,
            reference_t2=tether.reference_t2,
            adhesion_work=tether.adhesion_work,
            opening_cutoff=tether.opening_cutoff,
            tangential_stiffness=tether.tangential_stiffness,
        )
        transmitted = local_cell_force.sum(axis=0)
        transmitted_forces.append(transmitted)
        traction_magnitudes.append(
            float(np.linalg.norm(transmitted))
            / float(interface.registry.reference_weights[row])
        )
    forces = np.asarray(transmitted_forces, dtype=np.float64)
    tractions = np.asarray(traction_magnitudes, dtype=np.float64)
    return {
        "resultant": forces.sum(axis=0),
        "integrated_force_magnitude": float(
            np.linalg.norm(forces, axis=1).sum()
        ),
        "traction_p95": float(np.percentile(tractions, 95.0)),
        "maximum_traction": float(tractions.max()),
        "material_point_count": int(len(tractions)),
    }


def state_metrics(model, arrays, evaluation) -> dict[str, object]:
    myocyte = np.asarray(arrays["myocyte_vertices"], dtype=np.float64)
    ecm = np.asarray(arrays["ecm_vertices"], dtype=np.float64)
    endocardium = np.asarray(arrays["endocardial_vertices"], dtype=np.float64)
    myocyte_interface = interface_force_metrics(
        model.myocyte_interface,
        model.myocyte,
        model.ecm_reference,
        myocyte,
        ecm,
    )
    endocardial_interface = interface_force_metrics(
        model.endocardial_interface,
        model.endocardium,
        model.ecm_reference,
        endocardium,
        ecm,
    )
    return {
        "axial_shortening": axial_shortening(model, myocyte),
        "ecm_energy": float(evaluation.energy_components["ecm"]),
        "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
        "maximum_ecm_jacobian": evaluation.maximum_ecm_jacobian,
        "minimum_gap": evaluation.minimum_gap,
        "myocyte_volume_ratio": evaluation.myocyte_volume_ratio,
        "endocardial_volume_ratio": evaluation.endocardial_volume_ratio,
        "myocyte_interface": {
            **myocyte_interface,
            "resultant": myocyte_interface["resultant"].tolist(),
        },
        "endocardial_interface": {
            **endocardial_interface,
            "resultant": endocardial_interface["resultant"].tolist(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--reference-capture", type=Path, default=DEFAULT_REFERENCE_CAPTURE
    )
    parser.add_argument(
        "--reference-summary", type=Path, default=DEFAULT_REFERENCE_SUMMARY
    )
    parser.add_argument(
        "--reference-progress", type=Path, default=DEFAULT_REFERENCE_PROGRESS
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--capture-iterations", type=int, default=240)
    parser.add_argument("--newton-iterations", type=int, default=12)
    arguments = parser.parse_args()

    source_path = arguments.source.resolve()
    target_path = arguments.target.resolve()
    reference_capture_path = arguments.reference_capture.resolve()
    reference_summary_path = arguments.reference_summary.resolve()
    reference_progress_path = arguments.reference_progress.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    for required in (
        source_path,
        target_path,
        reference_capture_path,
        reference_summary_path,
        reference_progress_path,
    ):
        if not required.is_file():
            raise FileNotFoundError(required)

    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    coordinates = build_exact_volume_coordinates(model)
    backend = FenicsxECMBackend(model.ecm_reference)
    source = np.load(source_path)

    capture_started = time.perf_counter()
    capture = solve_fast_trilayer_equilibrium(
        model,
        initial_variables=np.asarray(source["variables"], dtype=np.float64),
        activation=0.20,
        ecm_backend=backend.energy_force,
        maximum_iterations=arguments.capture_iterations,
        maximum_newton_iterations=0,
        maximum_follower_iterations=1,
    )
    capture_seconds = time.perf_counter() - capture_started
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    capture_path = output_path / "capture_state.npz"
    np.savez_compressed(
        capture_path,
        activation=np.asarray(0.20),
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

    command = [
        sys.executable,
        str(DIAGNOSTIC),
        "--input",
        str(capture_path),
        "--output",
        str(output_path / "sparse_refinement"),
        "--activation",
        "0.20",
        "--ecm-footprint-scale",
        "1.5",
        "--skip-coarse",
        "--skip-sparse-spectral",
        "--method",
        "krylov",
        "--newton-iterations",
        str(arguments.newton_iterations),
        "--ecm-backend",
        "fenicsx",
    ]
    environment = os.environ.copy()
    source_directory = str(ROOT / "src")
    inherited_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_directory
        if not inherited_path
        else os.pathsep.join((source_directory, inherited_path))
    )
    refinement_started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    refinement_seconds = time.perf_counter() - refinement_started
    (output_path / "refinement_stdout.log").write_text(
        process.stdout, encoding="utf-8"
    )
    (output_path / "refinement_stderr.log").write_text(
        process.stderr, encoding="utf-8"
    )
    if process.returncode != 0:
        failure = {
            "status": "failed_fenicsx_sparse_refinement",
            "returncode": process.returncode,
            "capture_seconds": capture_seconds,
            "refinement_seconds": refinement_seconds,
            "stdout_tail": process.stdout[-8000:],
            "stderr_tail": process.stderr[-8000:],
            "backend": backend.diagnostics(),
        }
        (output_path / "failure.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        print(json.dumps(failure, indent=2))
        raise RuntimeError("FEniCSx coupled peak refinement failed")

    refinement_path = output_path / "sparse_refinement"
    refinement_summary = json.loads(
        (refinement_path / "summary.json").read_text("utf-8")
    )
    final_path = refinement_path / "activation_020_state.npz"
    final = np.load(final_path)
    target = np.load(target_path)
    zero_z = np.zeros(
        (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
    )
    final_evaluation = evaluate_fast_trilayer_state(
        model,
        np.asarray(final["myocyte_vertices"], dtype=np.float64),
        np.asarray(final["ecm_vertices"], dtype=np.float64),
        np.asarray(final["endocardial_vertices"], dtype=np.float64),
        activation=0.20,
        ecm_internal_z=zero_z,
        ecm_backend=backend.energy_force,
        reject_penetration=False,
    )
    target_evaluation = evaluate_fast_trilayer_state(
        model,
        np.asarray(target["myocyte_vertices"], dtype=np.float64),
        np.asarray(target["ecm_vertices"], dtype=np.float64),
        np.asarray(target["endocardial_vertices"], dtype=np.float64),
        activation=0.20,
        ecm_internal_z=zero_z,
        ecm_backend=backend.energy_force,
        reject_penetration=False,
    )
    zero_external = _full_external_force(
        model,
        coordinates,
        np.asarray(final["endocardial_vertices"], dtype=np.float64),
        pressure=0.0,
        wss_command=np.zeros(3, dtype=np.float64),
    )
    _, final_kkt = _kkt_audit(
        model,
        coordinates,
        final_evaluation,
        np.asarray(final["myocyte_vertices"], dtype=np.float64),
        np.asarray(final["endocardial_vertices"], dtype=np.float64),
        zero_external,
    )
    target_metrics = state_metrics(model, target, target_evaluation)
    final_metrics = state_metrics(model, final, final_evaluation)

    final_resultants = np.asarray(
        (
            final_metrics["myocyte_interface"]["resultant"],
            final_metrics["endocardial_interface"]["resultant"],
        ),
        dtype=np.float64,
    )
    target_resultants = np.asarray(
        (
            target_metrics["myocyte_interface"]["resultant"],
            target_metrics["endocardial_interface"]["resultant"],
        ),
        dtype=np.float64,
    )
    final_p95 = np.asarray(
        (
            final_metrics["myocyte_interface"]["traction_p95"],
            final_metrics["endocardial_interface"]["traction_p95"],
        ),
        dtype=np.float64,
    )
    target_p95 = np.asarray(
        (
            target_metrics["myocyte_interface"]["traction_p95"],
            target_metrics["endocardial_interface"]["traction_p95"],
        ),
        dtype=np.float64,
    )
    state_displacement = np.concatenate(
        (
            np.asarray(final["myocyte_vertices"])
            - np.asarray(target["myocyte_vertices"]),
            np.asarray(final["ecm_vertices"])
            - np.asarray(target["ecm_vertices"]),
            np.asarray(final["endocardial_vertices"])
            - np.asarray(target["endocardial_vertices"]),
        )
    )
    target_deformation = np.concatenate(
        (
            np.asarray(target["myocyte_vertices"]) - model.myocyte.vertices,
            np.asarray(target["ecm_vertices"]) - model.ecm_reference.vertices,
            np.asarray(target["endocardial_vertices"])
            - model.endocardium.vertices,
        )
    )
    comparison = {
        "global_shortening_relative_error": relative_error(
            final_metrics["axial_shortening"],
            target_metrics["axial_shortening"],
        ),
        "ecm_energy_relative_error": relative_error(
            final_metrics["ecm_energy"], target_metrics["ecm_energy"]
        ),
        "interface_resultant_raw_relative_error": relative_error(
            final_resultants, target_resultants
        ),
        "interface_resultant_scaled_error": float(
            np.linalg.norm(final_resultants - target_resultants)
            / max(
                1.0e-14,
                sum(
                    float(final_metrics[name]["integrated_force_magnitude"])
                    for name in ("myocyte_interface", "endocardial_interface")
                ),
                sum(
                    float(target_metrics[name]["integrated_force_magnitude"])
                    for name in ("myocyte_interface", "endocardial_interface")
                ),
            )
        ),
        "interface_traction_p95_relative_error": relative_error(
            final_p95, target_p95
        ),
        "interface_traction_p95_max_relative_error": float(
            np.max(
                np.abs(final_p95 - target_p95)
                / np.maximum(
                    1.0e-14,
                    np.maximum(np.abs(final_p95), np.abs(target_p95)),
                )
            )
        ),
        "minimum_j_absolute_error": abs(
            float(final_metrics["minimum_ecm_jacobian"])
            - float(target_metrics["minimum_ecm_jacobian"])
        ),
        "full_state_displacement_relative_l2": float(
            np.linalg.norm(state_displacement)
            / max(1.0e-14, float(np.linalg.norm(target_deformation)))
        ),
    }

    reference_summary = json.loads(reference_summary_path.read_text("utf-8"))
    reference_progress = json.loads(reference_progress_path.read_text("utf-8"))
    reference_step = reference_progress["records"][-1]
    reference_total_seconds = float(reference_step["total_step_seconds"])
    fenicsx_total_seconds = capture_seconds + refinement_seconds
    parent_backend_diagnostics = backend.diagnostics()
    cold_fenicsx_total_seconds = fenicsx_total_seconds + float(
        parent_backend_diagnostics["setup_and_jit_seconds"]
    )
    amortized_speedup = reference_total_seconds / fenicsx_total_seconds
    cold_start_speedup = reference_total_seconds / cold_fenicsx_total_seconds
    physics_passed = bool(
        comparison["global_shortening_relative_error"] <= 0.01
        and comparison["ecm_energy_relative_error"] <= 0.01
        and comparison["interface_resultant_scaled_error"] <= 0.05
        and comparison["interface_traction_p95_max_relative_error"] <= 0.05
        and comparison["minimum_j_absolute_error"] <= 0.01
        and final_kkt <= 1.0e-5
        and abs(float(final_metrics["myocyte_volume_ratio"]) - 1.0) <= 1.0e-8
        and abs(float(final_metrics["endocardial_volume_ratio"]) - 1.0) <= 1.0e-8
        and float(final_metrics["minimum_ecm_jacobian"]) >= 0.5
        and float(final_metrics["minimum_gap"]) >= -1.0e-12
        and bool(refinement_summary["passed"])
    )
    speed_passed = bool(cold_start_speedup >= 5.0)
    report = {
        "schema_version": "efe_node1_fenicsx_coupled_peak_v01",
        "status": (
            "passed_backend_spike"
            if physics_passed and speed_passed
            else "failed_backend_spike"
        ),
        "evidence_class": "backend_spike_not_formal_n1_2_evidence",
        "source_state": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "target_state": str(target_path.relative_to(ROOT)).replace("\\", "/"),
        "reference_capture": str(reference_capture_path.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "target_metrics": target_metrics,
        "fenicsx_metrics": final_metrics,
        "comparison": comparison,
        "capture_iterations": arguments.capture_iterations,
        "kkt": {
            "target": float(reference_summary["normalized_kkt_residual"]),
            "fenicsx": final_kkt,
        },
        "timing": {
            "reference_capture_seconds": float(reference_step["capture_seconds"]),
            "reference_refinement_seconds": float(reference_step["solve_seconds"]),
            "reference_total_seconds": reference_total_seconds,
            "fenicsx_capture_seconds": capture_seconds,
            "fenicsx_refinement_seconds": refinement_seconds,
            "fenicsx_amortized_total_seconds": fenicsx_total_seconds,
            "fenicsx_cold_start_total_seconds": cold_fenicsx_total_seconds,
            "amortized_end_to_end_speedup": amortized_speedup,
            "cold_start_end_to_end_speedup": cold_start_speedup,
            "reference_tangent_assembly_seconds": float(
                reference_summary["tangent_assembly_seconds"]
            ),
            "fenicsx_tangent_assembly_seconds": float(
                refinement_summary["tangent_assembly_seconds"]
            ),
        },
        "parent_backend_diagnostics": parent_backend_diagnostics,
        "refinement_backend_diagnostics": refinement_summary[
            "ecm_backend_diagnostics"
        ],
        "physics_gates_passed": physics_passed,
        "speed_gate_passed": speed_passed,
        "passed": bool(physics_passed and speed_passed),
        "boundary": (
            "This is an authorized F150/D0/E0/a=0.20 backend spike. It is not "
            "formal N1-2 convergence evidence and does not authorize D1/E1."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise RuntimeError("FEniCSx coupled peak spike did not pass all gates")


if __name__ == "__main__":
    main()
