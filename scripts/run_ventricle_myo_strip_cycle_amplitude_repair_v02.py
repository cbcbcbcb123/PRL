"""Create-only targeted convergence repair for CENTER at 10 percent strain."""

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
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_repair_v02_20260913"
PRIMARY_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_v01_20260913"
EXECUTABLE = PROJECT_ROOT / "b" / "z1_bioform_myo" / "Release" / "prl_ventricle_myo_strip_v01.exe"
INPUT_ROOT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_r_v03_20260913" / "raw" / "FULL_M320_DT020"
INPUT_NODES = INPUT_ROOT / "nodes.csv"
INPUT_FACES = INPUT_ROOT / "faces.csv"
SOURCE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_myo_strip_v01.cpp"
CMAKE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "CMakeLists.txt"
CONTRACT = PROJECT_ROOT / "project_control" / "ventricle_myocardial_strip_cycle_amplitude_repair_contract_v02.md"
BASE_CONTRACT = PROJECT_ROOT / "project_control" / "ventricle_myocardial_strip_cycle_amplitude_contract_v01.md"
BASE_TEST = PROJECT_ROOT / "tests" / "test_ventricle_myo_strip_v01.py"
RUNNER = Path(__file__).resolve()
VERIFIER = PROJECT_ROOT / "scripts" / "verify_ventricle_myo_strip_cycle_amplitude_repair_v02.py"
RENDERER = PROJECT_ROOT / "scripts" / "render_ventricle_myo_strip_cycle_amplitude_repair_v02.py"
BASE_VERIFIER = PROJECT_ROOT / "scripts" / "verify_ventricle_myo_strip_cycle_amplitude_v01.py"
BASE_RENDERER = PROJECT_ROOT / "scripts" / "render_ventricle_myo_strip_cycle_amplitude_v01.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def validate_primary_failure() -> dict[str, Any]:
    verdict_path = PRIMARY_OUTPUT / "verdict.json"
    source_hash_path = PRIMARY_OUTPUT / "source_hashes.json"
    if not verdict_path.is_file() or not source_hash_path.is_file():
        raise RuntimeError("primary v01 failure evidence is missing")
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    expected_failed = {"CENTER_EPS100_SAVED_RESIDUAL", "CENTER_EPS100_RECOVERY"}
    if verdict.get("status") != "failed" or set(verdict.get("failed_gates", [])) != expected_failed:
        raise RuntimeError("primary v01 no longer has the exact two repair-eligible failed gates")
    old_hashes = json.loads(source_hash_path.read_text(encoding="utf-8"))
    core_paths = (EXECUTABLE, INPUT_NODES, INPUT_FACES, SOURCE, CMAKE)
    core_checks = {}
    for path in core_paths:
        key = relative(path)
        observed = sha256_file(path)
        expected = old_hashes.get(key)
        core_checks[key] = {"expected": expected, "observed": observed, "matches": expected == observed}
        if expected != observed:
            raise RuntimeError(f"core drift prevents targeted repair: {key}")
    primary_case = PRIMARY_OUTPUT / "raw" / "CENTER_EPS100"
    primary_hashes = {
        name: sha256_file(primary_case / name)
        for name in ("kernel_metrics.json", "state_metrics.csv", "cell_metrics.csv", "nodes.csv", "faces.csv", "step_audits.csv")
    }
    return {
        "validation_status": "eligible_for_targeted_convergence_repair",
        "checked_at": utc_now(),
        "primary_verdict": relative(verdict_path),
        "primary_verdict_sha256": sha256_file(verdict_path),
        "failed_gates": sorted(expected_failed),
        "core_hash_checks": core_checks,
        "primary_center_eps100_hashes": primary_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise SystemExit(f"create-only output already exists: {output}")

    frozen_files = (
        EXECUTABLE, INPUT_NODES, INPUT_FACES, SOURCE, CMAKE, CONTRACT, BASE_CONTRACT,
        BASE_TEST, RUNNER, VERIFIER, RENDERER, BASE_VERIFIER, BASE_RENDERER,
    )
    missing = [path for path in frozen_files if not path.is_file()]
    if missing:
        raise SystemExit("missing prerequisites: " + ", ".join(str(path) for path in missing))
    try:
        primary_evidence = validate_primary_failure()
    except Exception as error:
        raise SystemExit(str(error)) from error

    output.mkdir(parents=True)
    (output / "raw").mkdir()
    write_json(output / "primary_evidence.json", primary_evidence)
    write_json(output / "source_hashes.json", {relative(path): sha256_file(path) for path in frozen_files})
    git_code, git_commit = run_text(["git", "rev-parse", "HEAD"])
    status_code, git_status = run_text(["git", "status", "--porcelain=v1"])
    (output / "git_status_snapshot.txt").write_text(git_status, encoding="utf-8")
    write_json(
        output / "preregistration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-STRIP-CYCLE-AMP-A",
            "version": "v02_targeted_convergence_repair",
            "created_at": utc_now(),
            "execution_class": "cpu_single_thread_create_only",
            "git_commit": git_commit.strip() if git_code == 0 else "unknown",
            "git_status_command_status": status_code,
            "only_rerun_case": "CENTER_EPS100",
            "condition": "CENTER",
            "contraction_strain": 0.10,
            "solver_change": {"hold_steps_per_segment": {"from": 2000, "to": 3000}},
            "unchanged": [
                "model", "mesh", "input", "dt", "settle_steps", "ramp_steps_per_segment",
                "material_parameters", "boundary_conditions", "junction_links", "all_gate_thresholds",
            ],
            "coordinate_semantics": "algorithmic_activation_phase_not_physiological_time",
        },
    )

    commands: list[str] = []
    test_command = [sys.executable, "-X", "utf8", "-m", "unittest", str(BASE_TEST), "-v"]
    commands.append(subprocess.list2cmdline(test_command))
    test_code, test_output = run_text(test_command)
    compile_command = [
        sys.executable, "-X", "utf8", "-m", "py_compile",
        str(RUNNER), str(VERIFIER), str(RENDERER), str(BASE_VERIFIER), str(BASE_RENDERER),
    ]
    commands.append(subprocess.list2cmdline(compile_command))
    compile_code, compile_output = run_text(compile_command)
    write_json(
        output / "preflight_tests.json",
        {
            "base_model_test": {"returncode": test_code, "output": test_output},
            "python_compile": {"returncode": compile_code, "output": compile_output},
            "primary_failure_eligibility": primary_evidence["validation_status"],
        },
    )
    if test_code != 0 or compile_code != 0:
        (output / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
        raise SystemExit("repair preflight failed; formal repair not started")

    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        }
    )
    case_dir = output / "raw" / "CENTER_EPS100"
    command = [
        str(EXECUTABLE), str(case_dir), "CENTER", str(INPUT_NODES), str(INPUT_FACES),
        "0.02", "0.10", "1000", "50", "3000",
    ]
    commands.append(subprocess.list2cmdline(command))
    print(f"START CENTER_EPS100_REPAIR {utc_now()}", flush=True)
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
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    ledger: dict[str, Any] = {
        "schema_version": 1,
        "stage": "Z1-MYO-STRIP-CYCLE-AMP-A",
        "version": "v02_targeted_convergence_repair",
        "formal_attempt_consumed": True,
        "gpu_count": 0,
        "case": "CENTER_EPS100",
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "status": "completed" if completed.returncode == 0 else "failed",
    }
    if completed.returncode == 0:
        ledger["kernel_metrics"] = json.loads((case_dir / "kernel_metrics.json").read_text(encoding="utf-8"))
    else:
        ledger["error_tail"] = (completed.stderr or completed.stdout)[-4000:]
    write_json(output / "execution_ledger.json", ledger)
    print(f"END CENTER_EPS100_REPAIR code={completed.returncode} elapsed={elapsed:.2f}s", flush=True)
    if completed.returncode != 0:
        (output / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
        return 2

    verify_command = [sys.executable, "-X", "utf8", str(VERIFIER), "--output", str(output)]
    commands.append(subprocess.list2cmdline(verify_command))
    verify_code, verify_output = run_text(verify_command)
    (output / "verification_stdout.txt").write_text(verify_output, encoding="utf-8")
    render_command = [sys.executable, "-X", "utf8", str(RENDERER), "--output", str(output)]
    commands.append(subprocess.list2cmdline(render_command))
    render_code, render_output = run_text(render_command)
    (output / "render_stdout.txt").write_text(render_output, encoding="utf-8")
    (output / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
    print(f"VERIFY code={verify_code}", flush=True)
    print(f"RENDER code={render_code}", flush=True)
    return 0 if verify_code == 0 and render_code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
