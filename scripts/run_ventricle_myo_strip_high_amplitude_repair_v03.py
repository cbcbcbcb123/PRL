"""Create-only final convergence repair for the CENTER 20% strip case."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_repair_v03_20260913"
V01 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_v01_20260913"
V02 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_repair_v02_20260913"
EXECUTABLE = PROJECT_ROOT / "b" / "z1_bioform_myo" / "Release" / "prl_ventricle_myo_strip_v01.exe"
INPUT_ROOT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_r_v03_20260913" / "raw" / "FULL_M320_DT020"
INPUT_NODES = INPUT_ROOT / "nodes.csv"
INPUT_FACES = INPUT_ROOT / "faces.csv"
CONTRACT = PROJECT_ROOT / "project_control" / "ventricle_myocardial_strip_high_amplitude_deformability_repair_contract_v03.md"
SOURCE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_myo_strip_v01.cpp"
CMAKE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "CMakeLists.txt"
BASE_TEST = PROJECT_ROOT / "tests" / "test_ventricle_myo_strip_v01.py"
RUNNER = Path(__file__).resolve()
VERIFIER = PROJECT_ROOT / "scripts" / "verify_ventricle_myo_strip_high_amplitude_repair_v03.py"
RENDERER = PROJECT_ROOT / "scripts" / "render_ventricle_myo_strip_high_amplitude_repair_v03.py"
RAW_NAMES = ("kernel_metrics.json", "state_metrics.csv", "cell_metrics.csv", "nodes.csv", "faces.csv", "step_audits.csv")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_text(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return completed.returncode, completed.stdout


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def validate_predecessors() -> dict[str, Any]:
    v02_verdict_path = V02 / "verdict.json"
    v02_verdict = json.loads(v02_verdict_path.read_text(encoding="utf-8"))
    if v02_verdict.get("status") != "failed" or v02_verdict.get("failed_gates") != ["CENTER_EPS200_SAVED_RESIDUAL"]:
        raise RuntimeError("v02 predecessor no longer has the single frozen CENTER 20 percent residual failure")
    v02_hashes = json.loads((V02 / "source_hashes.json").read_text(encoding="utf-8"))
    current = {
        relative(EXECUTABLE): EXECUTABLE,
        relative(INPUT_NODES): INPUT_NODES,
        relative(INPUT_FACES): INPUT_FACES,
        relative(SOURCE): SOURCE,
        relative(CMAKE): CMAKE,
    }
    core_checks: dict[str, Any] = {}
    for key, path in current.items():
        expected = v02_hashes.get(key)
        observed = sha256_file(path)
        core_checks[key] = {"expected": expected, "observed": observed, "matches": observed == expected}
        if expected is None or observed != expected:
            raise RuntimeError(f"core/input hash drift prevents final repair: {key}")
    reused: dict[str, Any] = {}
    for case, directory in (
        ("CENTER_EPS150", V02 / "raw" / "CENTER_EPS150"),
        ("SYNC_EPS150", V01 / "raw" / "SYNC_EPS150"),
        ("SYNC_EPS200", V01 / "raw" / "SYNC_EPS200"),
    ):
        hashes: dict[str, str] = {}
        for name in RAW_NAMES:
            path = directory / name
            if not path.is_file():
                raise RuntimeError(f"missing predecessor evidence: {path}")
            hashes[name] = sha256_file(path)
        reused[case] = {"directory": relative(directory), "file_hashes": hashes}
    return {
        "v01_verdict": relative(V01 / "verdict.json"),
        "v01_verdict_sha256": sha256_file(V01 / "verdict.json"),
        "v02_verdict": relative(v02_verdict_path),
        "v02_verdict_sha256": sha256_file(v02_verdict_path),
        "core_hash_checks": core_checks,
        "reused_cases": reused,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise SystemExit(f"create-only output already exists: {output}")
    prerequisites = (
        EXECUTABLE,
        INPUT_NODES,
        INPUT_FACES,
        CONTRACT,
        SOURCE,
        CMAKE,
        BASE_TEST,
        RUNNER,
        VERIFIER,
        RENDERER,
        V01 / "verdict.json",
        V01 / "reference_evidence.json",
        V02 / "verdict.json",
        V02 / "source_hashes.json",
    )
    missing = [path for path in prerequisites if not path.is_file()]
    if missing:
        raise SystemExit("missing prerequisites: " + ", ".join(str(path) for path in missing))
    try:
        predecessors = validate_predecessors()
    except Exception as error:
        raise SystemExit(str(error)) from error

    output.mkdir(parents=True)
    (output / "raw").mkdir()
    write_json(output / "primary_evidence.json", predecessors)
    write_json(output / "reference_evidence.json", json.loads((V01 / "reference_evidence.json").read_text(encoding="utf-8")))
    frozen_files = (EXECUTABLE, INPUT_NODES, INPUT_FACES, CONTRACT, SOURCE, CMAKE, BASE_TEST, RUNNER, VERIFIER, RENDERER)
    write_json(output / "source_hashes.json", {relative(path): sha256_file(path) for path in frozen_files})
    status_code, git_status = run_text(["git", "status", "--porcelain=v1"])
    (output / "git_status_snapshot.txt").write_text(git_status, encoding="utf-8")
    write_json(
        output / "preregistration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-STRIP-DEFORMABILITY-HI-A",
            "version": "v03_final_targeted_convergence_repair",
            "created_at": utc_now(),
            "execution_class": "cpu_single_thread_create_only",
            "repair_scope": ["CENTER_EPS200"],
            "only_change": {"hold_steps_per_segment": {"from": 6000, "to": 7000}},
            "unchanged": ["material", "active_strain", "contraction_stiffness", "shape_stress", "junctions", "clamps", "time_step", "ramp_steps", "all_gates"],
            "solver": {"requested_step": 0.02, "settle_steps": 1000, "ramp_steps_per_segment": 50, "hold_steps_per_segment": 7000, "segments": 8, "saved_state_count": 9, "gpu_count": 0},
            "frozen_gates": {"maximum_volume_relative_error": 0.02, "minimum_triangle_angle_deg": 15.0, "maximum_fixed_displacement": 1.0e-10, "maximum_saved_free_force": 1.0e-3, "maximum_work_relative_residual": 1.0e-10, "maximum_junction_balance_residual": 1.0e-12, "maximum_recovery_fraction": 0.10},
            "retry_policy": "third_and_final_attempt_for_this_question",
            "deformability_identifiability": "not_identifiable_from_isometric_amplitude_sweep",
            "git_status_command_status": status_code,
        },
    )

    commands: list[str] = []
    test_command = [sys.executable, "-X", "utf8", "-m", "unittest", str(BASE_TEST), "-v"]
    compile_command = [sys.executable, "-X", "utf8", "-m", "py_compile", str(RUNNER), str(VERIFIER), str(RENDERER)]
    commands.extend((subprocess.list2cmdline(test_command), subprocess.list2cmdline(compile_command)))
    test_code, test_output = run_text(test_command)
    compile_code, compile_output = run_text(compile_command)
    write_json(output / "preflight_tests.json", {"base_model_test": {"returncode": test_code, "output": test_output}, "python_compile": {"returncode": compile_code, "output": compile_output}, "v02_failure_signature": "passed", "core_and_input_hashes": "passed"})
    if test_code != 0 or compile_code != 0:
        (output / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
        raise SystemExit("final repair preflight failed; no formal trajectory started")

    environment = os.environ.copy()
    environment.update({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    case_dir = output / "raw" / "CENTER_EPS200"
    command = [str(EXECUTABLE), str(case_dir), "CENTER", str(INPUT_NODES), str(INPUT_FACES), "0.02", "0.20", "1000", "50", "7000"]
    commands.append(subprocess.list2cmdline(command))
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1500, check=False)
        elapsed = time.perf_counter() - started
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (case_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
        record: dict[str, Any] = {"case": "CENTER_EPS200", "condition": "CENTER", "contraction_strain": 0.20, "command": subprocess.list2cmdline(command), "returncode": completed.returncode, "elapsed_seconds": elapsed, "status": "completed" if completed.returncode == 0 else "failed"}
        if completed.returncode == 0:
            record["kernel_metrics"] = json.loads((case_dir / "kernel_metrics.json").read_text(encoding="utf-8"))
        else:
            record["error_tail"] = (completed.stderr or completed.stdout)[-4000:]
    except subprocess.TimeoutExpired as error:
        elapsed = time.perf_counter() - started
        case_dir.mkdir(parents=True, exist_ok=True)
        stdout = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode("utf-8", errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        (case_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (case_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        record = {"case": "CENTER_EPS200", "condition": "CENTER", "contraction_strain": 0.20, "command": subprocess.list2cmdline(command), "elapsed_seconds": elapsed, "status": "stopped_budget", "error_tail": stderr[-4000:]}
    ledger = {"schema_version": 1, "stage": "Z1-MYO-STRIP-DEFORMABILITY-HI-A", "version": "v03_final_targeted_convergence_repair", "formal_attempt_consumed": True, "gpu_count": 0, "case": record, "raw_execution_status": record["status"]}
    write_json(output / "execution_ledger.json", ledger)

    verify_command = [sys.executable, "-X", "utf8", str(VERIFIER), "--output", str(output)]
    render_command = [sys.executable, "-X", "utf8", str(RENDERER), "--output", str(output)]
    commands.append(subprocess.list2cmdline(verify_command))
    verify_code, verify_output = run_text(verify_command)
    (output / "verification_stdout.txt").write_text(verify_output, encoding="utf-8")
    commands.append(subprocess.list2cmdline(render_command))
    render_code, render_output = run_text(render_command)
    (output / "render_stdout.txt").write_text(render_output, encoding="utf-8")
    (output / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
    print(json.dumps({"verify_code": verify_code, "render_code": render_code, "raw": record["status"]}, ensure_ascii=False))
    return 0 if record["status"] == "completed" and verify_code == 0 and render_code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
