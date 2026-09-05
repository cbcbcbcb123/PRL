"""One-shot cache-mount retry adapter for the frozen static-mode screen v01.

The scientific assembly, five right-hand sides, observables, matrices, and
gates remain implemented by the byte-locked v01 entry.  This adapter changes
only result/container identity, remaining budget accounting, and retry
provenance after the v01 read-only-cache launch failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import run_paper2_static_mode_screen_v01 as core


SCHEMA = "paper2_static_mode_screen_v02"
ACTUAL_LAUNCH_CHECKOUT = "78b5d1997082fc2e5c2cf6ab5ad30c6073a2ec33"
CURRENT_STATUS_RELATIVE = Path("project_control/CURRENT_STATUS.md")
CURRENT_STATUS_SHA256 = "af6363358000ef97832cf49f9a6be0eb49ba15bc0c60c57be249ed5f37e4ec70"
CORE_RELATIVE = Path("scripts/run_paper2_static_mode_screen_v01.py")
CORE_SHA256 = "50d8df82a03e8969493c4eeda64a233873cc2a7ca623cef92568b7ddafa3a3ca"
V01_SUMMARY_RELATIVE = Path("results/paper2_static_mode_screen/v01_20260905/summary.json")
V01_SUMMARY_SHA256 = "68535babafd6652d1b0de2b58c3d387b92fd7208222afdb9c7175d2fa9e37201"
V01_MANIFEST_RELATIVE = Path("results/paper2_static_mode_screen/v01_20260905/manifest.json")
V01_MANIFEST_SHA256 = "6b361b64b21788fdd6f8e4f4743271aee4facc0740d8317fc2ec05859cdcf987"
RESULT_RELATIVE = Path("results/paper2_static_mode_screen/v02_20260905")
CONTAINER_NAME = "prl-paper2-static-mode-screen-v02-20260905"
V01_CHARGE_SECONDS = 0.05188476701732725
V02_REMAINING_BUDGET_SECONDS = 299.9481152329827
RETRY_START_CUMULATIVE_SECONDS = 161.92011524902773
ROOT_CACHE_TMPFS_BYTES = 536_870_912


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_retry_inputs(repo_root: Path) -> None:
    expected = {
        CURRENT_STATUS_RELATIVE: CURRENT_STATUS_SHA256,
        CORE_RELATIVE: CORE_SHA256,
        V01_SUMMARY_RELATIVE: V01_SUMMARY_SHA256,
        V01_MANIFEST_RELATIVE: V01_MANIFEST_SHA256,
    }
    for relative_path, expected_hash in expected.items():
        actual_hash = _sha256(repo_root / relative_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"retry input hash mismatch: {relative_path.as_posix()} "
                f"expected={expected_hash} actual={actual_hash}"
            )
    with (repo_root / V01_SUMMARY_RELATIVE).open("r", encoding="utf-8") as handle:
        failed_summary = json.load(handle)
    if not (
        failed_summary.get("status") == "ABORTED_FAIL_CLOSED"
        and failed_summary["execution_count_ledger"]["new_completed_static_system_assemblies"] == 0
        and failed_summary["execution_count_ledger"]["new_completed_static_rhs"] == 0
        and abs(
            float(failed_summary["resource_accounting"]["batch_numerical_elapsed_seconds"])
            - V01_CHARGE_SECONDS
        )
        <= 1.0e-15
    ):
        raise RuntimeError("v01 failure classification/count/budget drift")


def _root_cache_mount() -> dict[str, Any]:
    mount_lines = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    matching = []
    for line in mount_lines:
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/root/.cache":
            matching.append(fields)
    if len(matching) != 1:
        raise RuntimeError("expected exactly one /root/.cache mount")
    fields = matching[0]
    options = set(fields[3].split(","))
    if fields[2] != "tmpfs" or not {"rw", "nosuid", "nodev"}.issubset(options):
        raise RuntimeError("/root/.cache is not the approved writable tmpfs")
    if "noexec" in options:
        raise RuntimeError("/root/.cache tmpfs is noexec; JIT shared libraries cannot be loaded")
    return {
        "observed_device": fields[0],
        "observed_destination": fields[1],
        "observed_filesystem": fields[2],
        "observed_options": sorted(options),
        "required_size_bytes": ROOT_CACHE_TMPFS_BYTES,
        "rw_nosuid_nodev_and_exec_allowed": True,
    }


def _retry_metadata(repo_root: Path, mount_record: dict[str, Any]) -> dict[str, Any]:
    adapter_relative = Path(__file__).resolve().relative_to(repo_root)
    return {
        "authorization": {
            "record": CURRENT_STATUS_RELATIVE.as_posix(),
            "sha256": CURRENT_STATUS_SHA256,
            "scope": "one minimal cache-mount retry; no v03 on failure",
        },
        "version_identity": {
            "scientific_preregistration_and_production_baseline": core.EXPECTED_CODE_VERSION,
            "actual_checkout_at_retry_launch": ACTUAL_LAUNCH_CHECKOUT,
            "v01_scientific_core": {
                "path": CORE_RELATIVE.as_posix(),
                "sha256": CORE_SHA256,
                "unchanged_for_retry": True,
                "not_claimed_to_exist_in_frozen_production_baseline": True,
            },
            "v02_operational_adapter": {
                "path": adapter_relative.as_posix(),
                "sha256": _sha256(Path(__file__).resolve()),
                "not_part_of_frozen_scientific_baseline": True,
            },
        },
        "v01_failed_attempt": {
            "classification": "READ_ONLY_ROOT_CACHE_PATH_FAILURE_NOT_SCIENTIFIC_NEGATIVE",
            "completed_assemblies": 0,
            "completed_static_rhs": 0,
            "charged_seconds": V01_CHARGE_SECONDS,
            "summary": {
                "path": V01_SUMMARY_RELATIVE.as_posix(),
                "sha256": V01_SUMMARY_SHA256,
            },
            "manifest": {
                "path": V01_MANIFEST_RELATIVE.as_posix(),
                "sha256": V01_MANIFEST_SHA256,
            },
            "preserved_without_overwrite_or_container_removal": True,
        },
        "budget": {
            "original_two_attempt_static_budget_seconds": 300.0,
            "v01_charged_seconds": V01_CHARGE_SECONDS,
            "v02_remaining_budget_seconds": V02_REMAINING_BUDGET_SECONDS,
            "retry_start_cumulative_fem_and_failure_charge_seconds": (
                RETRY_START_CUMULATIVE_SECONDS
            ),
        },
        "only_operational_change": {
            "description": "add an executable writable in-memory tmpfs at /root/.cache",
            "root_cache_mount_observed": mount_record,
            "home_environment_not_changed": True,
            "scientific_matrices_metrics_thresholds_and_points_unchanged": True,
        },
    }


def _configure_core() -> None:
    core.SCHEMA = SCHEMA
    core.RESULT_RELATIVE = RESULT_RELATIVE
    core.EXPECTED_CONTAINER_NAME = CONTAINER_NAME
    core.EXPECTED_LAUNCH_CHECKOUT = ACTUAL_LAUNCH_CHECKOUT
    core.NUMERICAL_BUDGET_SECONDS = V02_REMAINING_BUDGET_SECONDS
    core.OLD_FEM_AND_FAILURE_CHARGE_SECONDS = RETRY_START_CUMULATIVE_SECONDS


def _install_metadata_hooks(metadata: dict[str, Any], repo_root: Path) -> None:
    original_json_writer = core._write_json_exclusive
    original_source_ledger = core._source_ledger

    def adapted_json_writer(path: Path, payload: Any) -> None:
        if path.name in {"summary.json", "manifest.json"}:
            payload["retry_provenance"] = metadata
        original_json_writer(path, payload)

    def adapted_source_ledger(root: Path) -> dict[str, dict[str, str]]:
        ledger = original_source_ledger(root)
        extra_paths = (
            Path(__file__).resolve().relative_to(repo_root),
            CURRENT_STATUS_RELATIVE,
            V01_SUMMARY_RELATIVE,
            V01_MANIFEST_RELATIVE,
        )
        for relative_path in extra_paths:
            ledger[relative_path.as_posix()] = {"sha256": _sha256(root / relative_path)}
        return ledger

    core._write_json_exclusive = adapted_json_writer
    core._source_ledger = adapted_source_ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--code-version")
    arguments = parser.parse_args()
    if arguments.self_test:
        report = core._self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if arguments.output is None or arguments.code_version is None:
        parser.error("--output and --code-version are required unless --self-test is used")

    repo_root = Path(__file__).resolve().parents[1]
    _verify_retry_inputs(repo_root)
    if os.environ.get("PAPER2_STATIC_ACTUAL_CHECKOUT") != ACTUAL_LAUNCH_CHECKOUT:
        raise RuntimeError("retry checkout environment mismatch")
    mount_record = _root_cache_mount()
    _configure_core()
    metadata = _retry_metadata(repo_root, mount_record)
    _install_metadata_hooks(metadata, repo_root)
    return core.run(arguments.output, arguments.code_version)


if __name__ == "__main__":
    sys.exit(main())
