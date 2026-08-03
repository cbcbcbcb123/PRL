from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from hybrid.r1_remesh_robustness_evidence import (
    R1EvidenceError,
    adjudicate_r1_focused_failure,
)


EXPECTED_PARENT_FAILURES = {
    "prl_x1k_sphere_instantaneous_velocity_refinement",
    "prl_x1k_v04_family_b_parameterized_diagnosis",
    "prl_x1k_v06_family_c_short_trajectory_gate",
}

COMMANDS = (
    "parent_ctest",
    "fork_ctest",
    "strict_prl",
    "python_pytest",
    "ruff",
)


def _command_evidence(directory: Path, command: str) -> tuple[str, int, dict[str, Any]]:
    log_path = directory / f"{command}.log"
    exit_path = directory / f"{command}.exitcode"
    if not log_path.is_file() or not exit_path.is_file():
        raise R1EvidenceError(f"R1 verification evidence is missing for {command}")
    payload = log_path.read_bytes()
    try:
        output = payload.decode("utf-8-sig")
        exit_code = int(exit_path.read_text(encoding="ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise R1EvidenceError(f"R1 verification evidence is invalid for {command}") from error
    return output, exit_code, {
        "log_path": f"verification/{command}.log",
        "exitcode_path": f"verification/{command}.exitcode",
        "log_sha256": hashlib.sha256(payload).hexdigest(),
        "log_bytes": len(payload),
        "exit_code": exit_code,
    }


def _ctest_summary(output: str, command: str) -> tuple[int, int, int]:
    matches = re.findall(
        r"\d+% tests passed,\s*(\d+) tests failed out of (\d+)", output
    )
    if not matches:
        raise R1EvidenceError(f"R1 {command} CTest summary is absent")
    failed, total = (int(value) for value in matches[-1])
    return total - failed, failed, total


def adjudicate_r1_verification_evidence(evidence_dir: Path) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    focused = adjudicate_r1_focused_failure(evidence_dir)
    focused.pop("parsed")
    raw = {
        command: _command_evidence(evidence_dir, command) for command in COMMANDS
    }
    results: dict[str, Any] = {}

    parent_output, parent_exit, parent_record = raw["parent_ctest"]
    parent_passed, parent_failed, parent_total = _ctest_summary(
        parent_output, "parent"
    )
    parent_failures = set(
        re.findall(
            r"^\s*\d+\s+-\s+(.+?)\s+\(Failed\)\s*$",
            parent_output,
            re.MULTILINE,
        )
    )
    if (
        parent_exit == 0
        or parent_failed != len(EXPECTED_PARENT_FAILURES)
        or parent_failures != EXPECTED_PARENT_FAILURES
        or "prl_x1k_v09_r1_real_remesh_robustness" in parent_failures
    ):
        raise R1EvidenceError(
            "R1 parent regression does not preserve exactly the historical failures"
        )
    results["parent_ctest"] = {
        **parent_record,
        "passed": parent_passed,
        "failed": parent_failed,
        "total": parent_total,
        "failures": sorted(parent_failures),
        "v09_regression_passed": True,
    }

    fork_output, fork_exit, fork_record = raw["fork_ctest"]
    fork_passed, fork_failed, fork_total = _ctest_summary(fork_output, "fork")
    if fork_exit != 0 or fork_failed != 0 or fork_total <= 0:
        raise R1EvidenceError("R1 controlled-fork regression is not all green")
    results["fork_ctest"] = {
        **fork_record,
        "passed": fork_passed,
        "failed": fork_failed,
        "total": fork_total,
    }

    strict_output, strict_exit, strict_record = raw["strict_prl"]
    if strict_exit != 0 or "Built target prl_core" not in strict_output:
        raise R1EvidenceError("R1 strict PRL compilation did not complete")
    results["strict_prl"] = {
        **strict_record,
        "prl_core_built": True,
        "r1_source_and_regression_werror_compile": True,
    }

    pytest_output, pytest_exit, pytest_record = raw["python_pytest"]
    pytest_matches = re.findall(r"(?:^|\s)(\d+) passed(?:[,\s]|$)", pytest_output)
    if pytest_exit != 0 or not pytest_matches:
        raise R1EvidenceError("R1 Python regression did not complete successfully")
    results["python_pytest"] = {
        **pytest_record,
        "passed": int(pytest_matches[-1]),
    }

    ruff_output, ruff_exit, ruff_record = raw["ruff"]
    if ruff_exit != 0 or "All checks passed!" not in ruff_output:
        raise R1EvidenceError("R1 tracked-Python Ruff evidence did not pass")
    results["ruff"] = {**ruff_record, "passed": True}

    return {
        "status": "passed_software_regression_with_frozen_r1_failure",
        "focused_scientific_response": focused,
        "commands": results,
        "counts_parsed_from_raw_logs": True,
        "hardcoded_verification_counts_used": False,
    }
