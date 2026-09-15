"""Create-only CPU runner for the frozen Z1-BIOFORM-MYO-R v03 contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ventricle_bioform_myo_common import (
    CONDITION_MATRIX,
    PROJECT_ROOT,
    condition_metrics,
    sha256_file,
    write_json,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_r_v03_20260913"
CONTRACT = PROJECT_ROOT / "project_control" / "ventricle_bioform_myocardium_repair_contract_v03.md"
AUTHORIZATION = PROJECT_ROOT / "project_control" / "ventricle_bioform_myocardium_repair_authorization_v03.md"
DIAGNOSIS = PROJECT_ROOT / "project_control" / "ventricle_bioform_myocardium_repair_diagnosis_v03.md"
SOURCE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_bioform_myo_v03.cpp"
CMAKE_SOURCE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "CMakeLists.txt"
REFINER_HEADER = PROJECT_ROOT / "external" / "simucell3d" / "include" / "triangulation_modules" / "local_mesh_refiner.hpp"
REFINER_SOURCE = PROJECT_ROOT / "external" / "simucell3d" / "src" / "triangulation_modules" / "local_mesh_refiner.cpp"
EXECUTABLE = PROJECT_ROOT / "b" / "z1_bioform_myo" / "Release" / "prl_ventricle_bioform_myo_v03.exe"
REGRESSION_BUILD = PROJECT_ROOT / "b" / "simucell3d_regression_v02"
RUNNER = Path(__file__).resolve()
COMMON = PROJECT_ROOT / "scripts" / "ventricle_bioform_myo_common.py"
REPAIR_HELPER = PROJECT_ROOT / "scripts" / "ventricle_bioform_myo_repair.py"
VERIFIER = PROJECT_ROOT / "scripts" / "verify_ventricle_z1_bioform_myo_v03.py"
RENDERER = PROJECT_ROOT / "scripts" / "render_ventricle_z1_bioform_myo_v03.py"
TEST_SOURCE = PROJECT_ROOT / "tests" / "test_ventricle_z1_bioform_myo_repair_v03.py"
FROZEN_FILES = (
    CONTRACT,
    AUTHORIZATION,
    DIAGNOSIS,
    SOURCE,
    CMAKE_SOURCE,
    REFINER_HEADER,
    REFINER_SOURCE,
    RUNNER,
    COMMON,
    REPAIR_HELPER,
    VERIFIER,
    RENDERER,
    TEST_SOURCE,
    EXECUTABLE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_text(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def run_condition(
    output_dir: Path,
    mode: str,
    faces: int,
    dt: float,
    stress: float,
    command_log: list[str],
) -> dict[str, Any]:
    command = [str(EXECUTABLE), str(output_dir), mode, str(faces), f"{dt:.6f}", f"{stress:.6f}"]
    command_log.append(subprocess.list2cmdline(command))
    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1200,
        check=False,
    )
    elapsed = time.perf_counter() - started
    (output_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    record: dict[str, Any] = {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "completed_at": utc_now(),
    }
    if completed.returncode == 0:
        record["status"] = "completed"
        record["metrics"] = condition_metrics(output_dir)
    else:
        record["status"] = "failed"
        record["error_tail"] = (completed.stderr or completed.stdout)[-4000:]
    return record


def _legacy_v02_main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise SystemExit(f"create-only output already exists: {output}")
    missing = [path for path in FROZEN_FILES if not path.is_file()]
    if missing:
        raise SystemExit("missing prerequisites: " + ", ".join(str(path) for path in missing))

    output.mkdir(parents=True)
    (output / "pilot").mkdir()
    (output / "raw").mkdir()
    command_log: list[str] = []
    git_code, git_commit = run_text(["git", "rev-parse", "HEAD"])
    status_code, git_status = run_text(["git", "status", "--porcelain=v1"])
    (output / "git_status_snapshot.txt").write_text(git_status, encoding="utf-8")
    source_hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): sha256_file(path)
        for path in FROZEN_FILES
    }
    source_hashes["git_status_snapshot.txt"] = sha256_file(output / "git_status_snapshot.txt")
    write_json(output / "source_hashes.json", source_hashes)
    preregistration = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-A",
        "contract_version": "v02",
        "created_at": utc_now(),
        "execution_class": "cpu_single_thread_create_only",
        "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physical_time",
        "contract_path": str(CONTRACT),
        "contract_sha256": source_hashes[str(CONTRACT.relative_to(PROJECT_ROOT)).replace("\\", "/")],
        "authorization_path": str(AUTHORIZATION),
        "git_commit": git_commit.strip() if git_code == 0 else "unknown",
        "git_status_command_status": status_code,
        "model": {
            "target_volume": 167.875410364543,
            "surface_tension": 0.160,
            "bending_modulus": 0.010,
            "area_elasticity_modulus": 0.050,
            "bulk_modulus": 30.0,
            "surface_damping_density": 1.0,
            "ramp_coordinate": 10.0,
            "hold_coordinate": 400.0,
            "stress_principal_ratios": [1.0, -0.15, -0.85],
            "normal_shape_traction_only": True,
            "rigid_mode_force_correction": True,
            "target_geometry_used": False,
            "reference_edge_shape_terms": 0,
            "reference_face_metric_terms": 0,
        },
        "remeshing": {
            "enabled": True,
            "edge_length_band_relative_to_nominal": [0.45, 1.60],
            "triangle_quality_score_floor": 0.55,
            "requested_faces_are_initial_resolution": True,
        },
        "pilot": {"faces": 320, "dt": 0.020, "stress_amplitudes": [0.020, 0.040, 0.060]},
        "formal_matrix": CONDITION_MATRIX,
        "gates": {
            "E_pq_min": 1.20,
            "F_qr_min": 1.15,
            "max_volume_relative_error": 0.02,
            "minimum_saved_triangle_angle_deg": 15.0,
            "max_force_residual": 1e-10,
            "max_moment_residual": 1e-10,
            "max_work_residual": 1e-12,
            "max_final_to_peak_force_ratio": 0.05,
        },
        "biological_validation_status": "blocked_data",
    }
    write_json(output / "preregistration.json", preregistration)

    preflight_commands = [
        [sys.executable, "-X", "utf8", "-m", "unittest", str(TEST_SOURCE), "-v"],
        [
            "ctest",
            "--test-dir",
            str(REGRESSION_BUILD),
            "-C",
            "Release",
            "-R",
            "triangulation_modules_local_mesh_refiner",
            "--output-on-failure",
        ],
    ]
    preflight_results = []
    for command in preflight_commands:
        command_log.append(subprocess.list2cmdline(command))
        returncode, combined_output = run_text(command)
        preflight_results.append(
            {"command": command, "returncode": returncode, "output": combined_output}
        )
    write_json(
        output / "preflight_tests.json",
        {
            "all_passed": all(item["returncode"] == 0 for item in preflight_results),
            "results": preflight_results,
        },
    )
    if not all(item["returncode"] == 0 for item in preflight_results):
        (output / "commands.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
        raise SystemExit("preflight tests failed; no pilot or formal condition started")

    ledger: dict[str, Any] = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-A",
        "started_at": utc_now(),
        "formal_attempt_consumed": False,
        "pilot": [],
        "formal": [],
    }
    selected: float | None = None
    for amplitude in (0.020, 0.040, 0.060):
        pilot_dir = output / "pilot" / f"S{int(round(amplitude * 1000)):03d}"
        record = run_condition(pilot_dir, "PILOT", 320, 0.020, amplitude, command_log)
        if record["status"] == "completed":
            metrics = record["metrics"]
            final = metrics["final"]
            kernel = metrics["kernel"]
            passed = (
                final["E_pq"] >= 1.20
                and final["F_qr"] >= 1.15
                and kernel["max_volume_relative_error"] <= 0.02
                and metrics["minimum_saved_triangle_angle_deg"] >= 15.0
                and metrics["all_saved_states_finite"]
                and metrics["all_saved_states_sphere_topology"]
            )
            record["pilot_gate_pass"] = passed
            if passed and selected is None:
                selected = amplitude
        else:
            record["pilot_gate_pass"] = False
        ledger["pilot"].append(record)
        write_json(output / "run_ledger.json", ledger)

    selection = {
        "schema_version": 1,
        "ordered_candidates": [0.020, 0.040, 0.060],
        "selected_stress_amplitude": selected,
        "selection_rule": "smallest amplitude satisfying all frozen pilot gates",
        "status": "selected" if selected is not None else "failed_numerical_or_mechanism",
        "pilot_gate_results": [
            {
                "stress_amplitude": record["command"][-1],
                "status": record["status"],
                "pilot_gate_pass": record.get("pilot_gate_pass", False),
                "E_pq": record.get("metrics", {}).get("final", {}).get("E_pq"),
                "F_qr": record.get("metrics", {}).get("final", {}).get("F_qr"),
            }
            for record in ledger["pilot"]
        ],
    }
    write_json(output / "pilot_selection.json", selection)
    if selected is None:
        ledger["completed_at"] = utc_now()
        ledger["stage_status"] = "failed_numerical_or_mechanism"
        write_json(output / "run_ledger.json", ledger)
        (output / "commands.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
        print(json.dumps(selection, ensure_ascii=False, indent=2))
        return 2

    ledger["formal_attempt_consumed"] = True
    ledger["formal_started_at"] = utc_now()
    write_json(output / "run_ledger.json", ledger)
    for condition in CONDITION_MATRIX:
        condition_dir = output / "raw" / condition["id"]
        record = run_condition(
            condition_dir,
            str(condition["mode"]),
            int(condition["faces"]),
            float(condition["dt"]),
            selected,
            command_log,
        )
        record["id"] = condition["id"]
        ledger["formal"].append(record)
        write_json(output / "run_ledger.json", ledger)

    ledger["completed_at"] = utc_now()
    ledger["stage_status"] = "raw_matrix_completed" if all(item["status"] == "completed" for item in ledger["formal"]) else "raw_matrix_failed"
    write_json(output / "run_ledger.json", ledger)
    (output / "commands.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": ledger["stage_status"], "selected_stress": selected}, ensure_ascii=False, indent=2))
    return 0 if ledger["stage_status"] == "raw_matrix_completed" else 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise SystemExit(f"create-only output already exists: {output}")
    missing = [path for path in FROZEN_FILES if not path.is_file()]
    if missing:
        raise SystemExit("missing prerequisites: " + ", ".join(str(path) for path in missing))

    output.mkdir(parents=True)
    (output / "raw").mkdir()
    command_log: list[str] = []
    git_code, git_commit = run_text(["git", "rev-parse", "HEAD"])
    status_code, git_status = run_text(["git", "status", "--porcelain=v1"])
    (output / "git_status_snapshot.txt").write_text(git_status, encoding="utf-8")
    source_hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): sha256_file(path)
        for path in FROZEN_FILES
    }
    source_hashes["git_status_snapshot.txt"] = sha256_file(output / "git_status_snapshot.txt")
    write_json(output / "source_hashes.json", source_hashes)
    preregistration = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-R",
        "contract_version": "v03",
        "created_at": utc_now(),
        "execution_class": "cpu_single_thread_per_condition_create_only",
        "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physical_time",
        "contract_path": str(CONTRACT),
        "contract_sha256": source_hashes[str(CONTRACT.relative_to(PROJECT_ROOT)).replace("\\", "/")],
        "authorization_path": str(AUTHORIZATION),
        "diagnosis_path": str(DIAGNOSIS),
        "git_commit": git_commit.strip() if git_code == 0 else "unknown",
        "git_status_command_status": status_code,
        "model": {
            "target_volume": 167.875410364543,
            "surface_tension": 0.160,
            "bending_modulus": 0.0,
            "bending_status": "disabled_after_failed_rigid_invariance_diagnostic",
            "area_elasticity_modulus": 0.050,
            "bulk_modulus": 30.0,
            "surface_damping_density": 1.0,
            "ramp_coordinate": 10.0,
            "hold_coordinate": 400.0,
            "stress_amplitude": 0.060,
            "stress_principal_ratios": [1.0, -0.15, -0.85],
            "normal_shape_drive": True,
            "active_force_space_correction": False,
            "total_velocity_rigid_mode_projection": "area_weighted_translation_and_rotation",
            "target_geometry_used": False,
            "reference_edge_shape_terms": 0,
            "reference_face_metric_terms": 0,
        },
        "integration": {
            "adaptive_substepping": True,
            "maximum_edge_fraction_per_substep": 0.10,
        },
        "remeshing": {
            "enabled": True,
            "edge_length_band_relative_to_nominal": [0.45, 1.60],
            "triangle_quality_score_floor": 0.55,
            "requested_faces_are_initial_resolution": True,
        },
        "formal_matrix": CONDITION_MATRIX,
        "gates": {
            "E_pq_min": 1.20,
            "F_qr_min": 1.15,
            "max_volume_relative_error": 0.02,
            "minimum_triangle_angle_deg": 15.0,
            "max_velocity_rigid_residual": 1e-12,
            "max_work_residual": 1e-12,
            "max_centroid_drift_over_radius": 0.005,
            "max_final_to_peak_force_ratio": 0.05,
        },
        "biological_validation_status": "blocked_data",
    }
    write_json(output / "preregistration.json", preregistration)
    write_json(
        output / "repair_selection.json",
        {
            "schema_version": 1,
            "status": "frozen_from_bounded_root_cause_controls",
            "stress_amplitude": 0.060,
            "bending_modulus": 0.0,
            "active_force_space_correction": False,
            "total_velocity_rigid_mode_projection": True,
            "evidence": str(DIAGNOSIS),
            "no_parameter_rescan": True,
        },
    )

    preflight_commands = [
        [sys.executable, "-X", "utf8", "-m", "unittest", str(TEST_SOURCE), "-v"],
        [
            "ctest",
            "--test-dir",
            str(REGRESSION_BUILD),
            "-C",
            "Release",
            "-R",
            "triangulation_modules_local_mesh_refiner",
            "--output-on-failure",
        ],
    ]
    preflight_results = []
    for command in preflight_commands:
        command_log.append(subprocess.list2cmdline(command))
        returncode, combined_output = run_text(command)
        preflight_results.append(
            {"command": command, "returncode": returncode, "output": combined_output}
        )
    write_json(
        output / "preflight_tests.json",
        {
            "all_passed": all(item["returncode"] == 0 for item in preflight_results),
            "results": preflight_results,
        },
    )
    if not all(item["returncode"] == 0 for item in preflight_results):
        (output / "commands.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
        raise SystemExit("preflight tests failed; no formal condition started")

    ledger: dict[str, Any] = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-R",
        "started_at": utc_now(),
        "formal_attempt_consumed": True,
        "formal": [],
    }
    write_json(output / "run_ledger.json", ledger)
    for condition in CONDITION_MATRIX:
        condition_dir = output / "raw" / condition["id"]
        record = run_condition(
            condition_dir,
            str(condition["mode"]),
            int(condition["faces"]),
            float(condition["dt"]),
            0.060,
            command_log,
        )
        record["id"] = condition["id"]
        ledger["formal"].append(record)
        write_json(output / "run_ledger.json", ledger)

    ledger["completed_at"] = utc_now()
    ledger["stage_status"] = (
        "raw_matrix_completed"
        if all(item["status"] == "completed" for item in ledger["formal"])
        else "raw_matrix_failed"
    )
    write_json(output / "run_ledger.json", ledger)
    (output / "commands.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"output": str(output), "status": ledger["stage_status"], "stress": 0.060},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ledger["stage_status"] == "raw_matrix_completed" else 3


if __name__ == "__main__":
    sys.exit(main())
