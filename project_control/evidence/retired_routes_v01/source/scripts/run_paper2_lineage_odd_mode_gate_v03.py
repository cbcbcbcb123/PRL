"""Executable-cache adapter for the frozen lineage odd-mode gate v02.

The v02 module remains the scientific implementation.  This adapter only
changes the create-only version identity, freezes the current evidence inputs,
and adds a fail-closed check for the approved executable /root/.cache tmpfs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import run_paper2_lineage_odd_mode_gate_v02 as core


SCHEMA = "paper2_lineage_odd_mode_gate_v03"
EXPECTED_BASE_COMMIT = "b45650a9e370be138a70acf305b6c3a21e6a7ed2"
EXPECTED_PROJECT_ROOT = Path("/workspace")
EXPECTED_CONTAINER_OUTPUT = Path("/output/summary.json")
LOGICAL_OUTPUT = Path(
    "results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json"
)
RUNNER_PATH = "scripts/run_paper2_lineage_odd_mode_gate_v03.py"
CORE_PATH = "scripts/run_paper2_lineage_odd_mode_gate_v02.py"
CORE_SHA256 = "54f07dfdb1b51286c129ec41404e31945492532e1346fc5728893b06b17f752a"
ROOT_CACHE_TMPFS_BYTES = 536_870_912
ROOT_CACHE_REQUESTED_OPTIONS = "rw,exec,nosuid,nodev,size=536870912"

SOURCE_HASHES = {
    "plan/active/EXP-20260909-001-paper2-lineage-ecm/source/review-and-execution-plan.html": (
        "5e83c8bcf043355e833391d05bbebfe076913e07f2d07b974e945897ed2aa826"
    ),
    "project_control/external_guidance_adoption_EXP-20260909-001-paper2-lineage-ecm_v01.md": (
        "af902621622576236097d2abc168f97bf7b6ae07ba27acc331333b7bcee6d9b6"
    ),
    "project_control/paper2_lineage_ecm_active_execution_plan_v01.md": (
        "d8d9f3aad3d5344e16a742719af626c2a2d8eb24e94b0bb605925517f7cce95a"
    ),
    "project_control/paper2_lineage_odd_mode_gate_execution_contract_v02.md": (
        "eb6c88e762a60b75d0abe9a259ac6ca32286d6013a96d477f08349f0748ef5d0"
    ),
    "project_control/paper2_lineage_odd_mode_gate_v03_execution_contract_v01.md": (
        "bb70d49b8a22082cb21b5733178ac6a8f8241b8463b1c63c83e7b77bc79d02b2"
    ),
    "project_control/paper2_lineage_odd_mode_gate_v03_runtime_repair_proposal_v01.md": (
        "76fb60a944c17bd9fb5db9b07ee8da40c2b60781a0592ab4c71d9da9d44c6fca"
    ),
    "project_control/paper2_lineage_odd_mode_gate_v02_failure_record_v01.md": (
        "f27e37a1e5b541ee801af33c4106cc33ee3bf4e764fafa45dfd0be42ba0de095"
    ),
    "project_control/CURRENT_STATUS.md": (
        "969615a125be6e7f889f6bc575afacb7390f2499bacc04fe27c33aaaa227eaf2"
    ),
    "project_control/prl_independent_theory_mainline_plan_v04.md": (
        "b41fb16926375f31ae7b457575a21f61f806e3e2a680fc0f43d1457411615d20"
    ),
    "results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json": (
        "b2202f295d3521741523c00902e965d3622a2fad41ef2180c0618c3348cc4cf3"
    ),
    "results/paper2_science_pilot/v01_20260905/science_brief.md": (
        "5ac3a1c017e1fe288e3229f7ff0e96cfd45717985f1f52d3c3c9f74efd8d9f86"
    ),
    "scripts/run_paper2_division_dipole_gate_v01.py": (
        "aa59b306377e50352c4b3a3e1b1b0c36b76aae2d42698031e63ca3a67fb291b2"
    ),
    "scripts/run_paper2_lineage_odd_mode_gate_v01.py": (
        "a4c5e641eee1109334ee7d448f60decce21205c07c659ca621581aa76446887a"
    ),
    CORE_PATH: CORE_SHA256,
    "src/paper2_hybrid/config.py": (
        "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe"
    ),
    "src/paper2_hybrid/model.py": (
        "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800"
    ),
    "src/paper2_hybrid/numerics.py": (
        "620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4"
    ),
}


def _size_option_bytes(options: set[str]) -> int | None:
    size_options = [item.split("=", 1)[1] for item in options if item.startswith("size=")]
    if len(size_options) != 1:
        return None
    raw = size_options[0].lower()
    multipliers = {"k": 1024, "m": 1024**2, "g": 1024**3}
    if raw[-1:] in multipliers:
        return int(raw[:-1]) * multipliers[raw[-1]]
    return int(raw)


def _root_cache_gate(mount_lines: list[str] | None = None) -> dict[str, Any]:
    lines = (
        Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
        if mount_lines is None
        else mount_lines
    )
    matching = []
    for line in lines:
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/root/.cache":
            matching.append(fields)
    if len(matching) != 1:
        return {
            "pass": False,
            "error": "expected exactly one /root/.cache mount",
            "matching_mount_count": len(matching),
            "requested_options": ROOT_CACHE_REQUESTED_OPTIONS,
        }

    fields = matching[0]
    options = set(fields[3].split(","))
    observed_size_bytes = _size_option_bytes(options)
    required_options_present = {"rw", "nosuid", "nodev"}.issubset(options)
    exec_allowed = "noexec" not in options
    passed = bool(
        fields[2] == "tmpfs"
        and required_options_present
        and exec_allowed
        and observed_size_bytes == ROOT_CACHE_TMPFS_BYTES
    )
    return {
        "pass": passed,
        "observed_device": fields[0],
        "observed_destination": fields[1],
        "observed_filesystem": fields[2],
        "observed_options": sorted(options),
        "observed_size_bytes": observed_size_bytes,
        "required_size_bytes": ROOT_CACHE_TMPFS_BYTES,
        "required_options_present": required_options_present,
        "exec_allowed": exec_allowed,
        "requested_options": ROOT_CACHE_REQUESTED_OPTIONS,
    }


_ORIGINAL_RESOURCE_GATE = core._container_resource_gate


def _adapted_resource_gate() -> dict[str, Any]:
    record = _ORIGINAL_RESOURCE_GATE()
    cache_gate = _root_cache_gate()
    record["root_cache_tmpfs"] = cache_gate
    record["pass"] = bool(record["pass"] and cache_gate["pass"])
    return record


def _configure_core() -> None:
    core.SCHEMA = SCHEMA
    core.EXPECTED_BASE_COMMIT = EXPECTED_BASE_COMMIT
    core.EXPECTED_PROJECT_ROOT = EXPECTED_PROJECT_ROOT
    core.EXPECTED_CONTAINER_OUTPUT = EXPECTED_CONTAINER_OUTPUT
    core.LOGICAL_OUTPUT = LOGICAL_OUTPUT
    core.RUNNER_PATH = RUNNER_PATH
    core.SOURCE_HASHES = SOURCE_HASHES
    core._container_resource_gate = _adapted_resource_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--runner-sha256", required=True)
    arguments = parser.parse_args()
    _configure_core()
    return core.run(arguments.output, arguments.base_commit, arguments.runner_sha256)


if __name__ == "__main__":
    sys.exit(main())
