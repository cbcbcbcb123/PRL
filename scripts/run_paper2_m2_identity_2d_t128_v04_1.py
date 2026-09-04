"""Normalize project paths, then delegate to the frozen v04 T128 runner."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNNER = PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t128_v04.py"
REPAIR_DECISION = (
    PROJECT_ROOT
    / "project_control"
    / "paper2_m2a_v04_t128_path_normalization_repair_and_retry_decision_v01.md"
)
PROJECT_PATH_FLAGS = frozenset(
    {
        "--output-dir",
        "--contract-v04",
        "--authorization",
        "--source-t64-dir",
        "--source-calibration",
        "--v03-execution-record",
    }
)


def normalize_project_path(value: str | Path) -> Path:
    """Return an absolute canonical project path or reject the input."""
    input_path = Path(value)
    candidate = (
        input_path if input_path.is_absolute() else PROJECT_ROOT / input_path
    ).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"path is outside project root: {value}") from error
    return candidate


def normalize_cli_project_paths(argv: list[str]) -> tuple[list[str], dict[str, Any]]:
    """Normalize every path argument before the frozen runner can create output."""
    normalized = list(argv)
    records: dict[str, Any] = {}
    seen: set[str] = set()
    for index, token in enumerate(argv):
        if token not in PROJECT_PATH_FLAGS:
            continue
        if token in seen:
            raise ValueError(f"duplicate project path flag: {token}")
        if index + 1 >= len(argv):
            raise ValueError(f"missing value for project path flag: {token}")
        seen.add(token)
        raw_value = argv[index + 1]
        canonical = normalize_project_path(raw_value)
        normalized[index + 1] = str(canonical)
        records[token] = {
            "input": raw_value,
            "canonical": str(canonical),
            "inside_project_root": True,
        }
    missing = sorted(PROJECT_PATH_FLAGS - seen)
    if missing:
        raise ValueError(f"missing project path flags: {missing}")
    return normalized, {
        "schema": "paper2_m2a_v04_1_path_normalization_audit_v01",
        "project_root": str(PROJECT_ROOT.resolve()),
        "paths": records,
        "all_project_path_flags_seen": True,
        "all_canonical_paths_inside_project": True,
        "normalization_completed_before_base_runner": True,
    }


def _load_original_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "paper2_m2_identity_2d_t128_v04_frozen_runner", ORIGINAL_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the frozen v04 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_manifest_injection(base_runner: Any, path_audit: dict[str, Any]) -> None:
    original_write_json = base_runner._write_json
    contract_path = Path(
        path_audit["paths"]["--contract-v04"]["canonical"]
    )

    def write_json_with_repair_provenance(path: Path, payload: Any) -> None:
        if path.name == "run_manifest.json":
            payload = copy.deepcopy(payload)
            repair_record = {
                "schema": "paper2_m2a_v04_1_path_repair_provenance_v01",
                "path_audit": path_audit,
                "original_runner": {
                    "path": base_runner._project_path(ORIGINAL_RUNNER),
                    "sha256": base_runner._sha256(ORIGINAL_RUNNER),
                },
                "new_runner": {
                    "path": base_runner._project_path(Path(__file__).resolve()),
                    "sha256": base_runner._sha256(Path(__file__).resolve()),
                },
                "repair_decision": {
                    "path": base_runner._project_path(REPAIR_DECISION),
                    "sha256": base_runner._sha256(REPAIR_DECISION),
                },
                "v04_contract": {
                    "path": base_runner._project_path(contract_path),
                    "sha256": base_runner._sha256(contract_path),
                },
            }
            payload["path_normalization_repair"] = repair_record
            payload["implementation_sha256"][
                base_runner._project_path(ORIGINAL_RUNNER)
            ] = base_runner._sha256(ORIGINAL_RUNNER)
            payload["implementation_sha256"][
                base_runner._project_path(Path(__file__).resolve())
            ] = base_runner._sha256(Path(__file__).resolve())
            payload["provenance"]["path_repair_decision_sha256"] = (
                base_runner._sha256(REPAIR_DECISION)
            )
        original_write_json(path, payload)

    base_runner._write_json = write_json_with_repair_provenance


def main() -> None:
    try:
        normalized_argv, path_audit = normalize_cli_project_paths(sys.argv)
    except ValueError as error:
        print(
            json.dumps(
                {
                    "schema": "paper2_m2a_v04_1_path_gate_failure_v01",
                    "status": "FAIL_CLOSED_BEFORE_OUTPUT_CREATION",
                    "reason": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
        raise SystemExit(2) from error

    sys.argv[:] = normalized_argv
    base_runner = _load_original_runner()
    _install_manifest_injection(base_runner, path_audit)
    base_runner.main()


if __name__ == "__main__":
    main()
