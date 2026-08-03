from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


class VerificationEvidenceError(RuntimeError):
    """A required machine-verification artifact is absent or invalid."""

    def __init__(self, message: str, *, reason: str, path: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.path = path


REQUIRED_COMMANDS = (
    "parent_ctest",
    "fork_ctest",
    "strict_prl_core",
    "python_pytest",
    "ruff",
)

EXPECTED_PARENT_FAILURES = {
    "prl_x1k_sphere_instantaneous_velocity_refinement",
    "prl_x1k_v04_family_b_parameterized_diagnosis",
    "prl_x1k_v06_family_c_short_trajectory_gate",
}


def _fail(message: str, *, reason: str, path: str) -> None:
    raise VerificationEvidenceError(message, reason=reason, path=path)


def _read_command(evidence_dir: Path, command: str) -> tuple[str, int, dict[str, Any]]:
    log_name = f"{command}.log"
    exit_name = f"{command}.exitcode"
    log_path = evidence_dir / log_name
    exit_path = evidence_dir / exit_name
    if not log_path.is_file():
        _fail(
            f"missing verification log: {log_name}",
            reason="verification_log_missing",
            path=log_name,
        )
    if not exit_path.is_file():
        _fail(
            f"missing verification exit code: {exit_name}",
            reason="verification_exitcode_missing",
            path=exit_name,
        )
    payload = log_path.read_bytes()
    try:
        output = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(
            f"verification log is not UTF-8: {log_name}: {error}",
            reason="verification_log_not_utf8",
            path=log_name,
        )
    try:
        exit_code = int(exit_path.read_text(encoding="ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        _fail(
            f"verification exit code is invalid: {exit_name}: {error}",
            reason="verification_exitcode_invalid",
            path=exit_name,
        )
    return output, exit_code, {
        "log_path": log_name,
        "exitcode_path": exit_name,
        "log_sha256": hashlib.sha256(payload).hexdigest(),
        "log_bytes": len(payload),
        "exit_code": exit_code,
    }


def _ctest_summary(output: str, command: str) -> tuple[int, int, int]:
    matches = re.findall(
        r"\d+% tests passed,\s*(\d+) tests failed out of (\d+)", output
    )
    if not matches:
        _fail(
            f"CTest completion summary is missing from {command}.log",
            reason="verification_summary_unparseable",
            path=f"{command}.log",
        )
    failed, total = (int(value) for value in matches[-1])
    return total - failed, failed, total


def adjudicate_verification_evidence(evidence_dir: Path) -> dict[str, Any]:
    """Parse versioned command logs; never infer verification from constants."""
    raw: dict[str, tuple[str, int, dict[str, Any]]] = {
        command: _read_command(evidence_dir, command)
        for command in REQUIRED_COMMANDS
    }
    commands: dict[str, dict[str, Any]] = {}

    parent_output, parent_exit, parent_record = raw["parent_ctest"]
    parent_passed, parent_failed, parent_total = _ctest_summary(
        parent_output, "parent_ctest"
    )
    parent_failures = set(
        re.findall(r"^\s*\d+\s+-\s+(.+?)\s+\(Failed\)\s*$", parent_output, re.MULTILINE)
    )
    if (
        parent_exit == 0
        or (parent_passed, parent_failed, parent_total) != (52, 3, 55)
        or parent_failures != EXPECTED_PARENT_FAILURES
    ):
        _fail(
            "parent CTest does not contain exactly the three frozen historical failures",
            reason="parent_ctest_unexpected_result",
            path="parent_ctest.log",
        )
    commands["parent_ctest"] = {
        **parent_record,
        "passed": parent_passed,
        "failed": parent_failed,
        "total": parent_total,
        "expected_historical_failures": sorted(parent_failures),
        "unexpected_failures": [],
        "verified": True,
    }

    fork_output, fork_exit, fork_record = raw["fork_ctest"]
    fork_passed, fork_failed, fork_total = _ctest_summary(fork_output, "fork_ctest")
    if fork_exit != 0 or (fork_passed, fork_failed, fork_total) != (134, 0, 134):
        _fail(
            "controlled fork CTest did not pass 134/134",
            reason="fork_ctest_unexpected_result",
            path="fork_ctest.log",
        )
    commands["fork_ctest"] = {
        **fork_record,
        "passed": fork_passed,
        "failed": fork_failed,
        "total": fork_total,
        "verified": True,
    }

    strict_output, strict_exit, strict_record = raw["strict_prl_core"]
    if strict_exit != 0 or "Built target prl_core" not in strict_output:
        _fail(
            "strict prl_core build completion is absent or failed",
            reason="strict_build_unexpected_result",
            path="strict_prl_core.log",
        )
    commands["strict_prl_core"] = {
        **strict_record,
        "passed": True,
        "verified": True,
    }

    pytest_output, pytest_exit, pytest_record = raw["python_pytest"]
    pytest_matches = re.findall(r"(?:^|\s)(\d+) passed(?:[,\s]|$)", pytest_output)
    if pytest_exit != 0 or not pytest_matches:
        _fail(
            "Python pytest completion summary is absent or failed",
            reason="python_pytest_unexpected_result",
            path="python_pytest.log",
        )
    commands["python_pytest"] = {
        **pytest_record,
        "passed": int(pytest_matches[-1]),
        "verified": True,
    }

    ruff_output, ruff_exit, ruff_record = raw["ruff"]
    if ruff_exit != 0 or "All checks passed!" not in ruff_output:
        _fail(
            "Ruff completion marker is absent or failed",
            reason="ruff_unexpected_result",
            path="ruff.log",
        )
    commands["ruff"] = {
        **ruff_record,
        "passed": True,
        "verified": True,
    }

    return {
        "status": "passed_with_expected_historical_failures",
        "commands": commands,
        "all_required_command_evidence_verified": True,
    }
