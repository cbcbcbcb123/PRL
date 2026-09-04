"""Apply the approved 60 s resource overlay, then run frozen M2A v05."""

from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t256_v05.py"
RESOURCE_DECISION = (
    PROJECT_ROOT
    / "project_control"
    / "paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md"
)
SOURCE_V05_FAILURE_DIR = (
    PROJECT_ROOT
    / "results"
    / "paper2_m2"
    / "identity_2d_v05_t256_v01_20260904"
)
PROJECT_PATH_FLAGS = frozenset(
    {
        "--output-dir",
        "--contract-v05",
        "--authorization",
        "--source-t64-dir",
        "--source-t128-dir",
        "--source-calibration",
        "--v04-execution-record",
    }
)


def normalize_project_path(value: str | Path) -> Path:
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
        "schema": "paper2_m2a_v05_1_path_normalization_audit_v01",
        "project_root": str(PROJECT_ROOT.resolve()),
        "paths": records,
        "all_project_path_flags_seen": True,
        "all_canonical_paths_inside_project": True,
        "normalization_completed_before_production_load": True,
        "normalization_completed_before_output_creation": True,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def _hash_paths(paths: tuple[Path, ...]) -> dict[str, str]:
    return {_project_path(path): _sha256(path) for path in paths}


def _load_base_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "paper2_m2_identity_2d_t256_v05_frozen_runner", BASE_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the frozen v05 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v05_frozen_paths() -> tuple[Path, ...]:
    fixed = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v05.py",
        PROJECT_ROOT / "src" / "paper2_m2" / "identity_2d_v05.py",
        BASE_RUNNER,
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v05.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_identity_2d_v05.py",
        PROJECT_ROOT / "project_control" / "paper2_m2a_v05_t256_execution_record_v01.md",
        RESOURCE_DECISION,
    )
    failure_files = tuple(
        path for path in sorted(SOURCE_V05_FAILURE_DIR.rglob("*")) if path.is_file()
    )
    return fixed + failure_files


def _install_resource_manifest_overlay(
    base_runner: Any,
    *,
    path_audit: dict[str, Any],
    frozen_paths: tuple[Path, ...],
    frozen_before: dict[str, str],
    failure_lock: dict[str, Any],
) -> None:
    from paper2_m2.protocol_v05_1 import FROZEN_RESOURCE_PROTOCOL_V05_1

    original_write_json = base_runner._write_json
    implementation_paths = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v05_1.py",
        Path(__file__).resolve(),
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v05_1.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_t256_v05_1_resource_gate.py",
    )

    def write_json_with_resource_provenance(path: Path, payload: Any) -> None:
        payload = copy.deepcopy(payload)
        if path.name == "run_manifest.json":
            payload["path_normalization"] = path_audit
            payload["resource_protocol_v05_1"] = (
                FROZEN_RESOURCE_PROTOCOL_V05_1.canonical_payload()
            )
            payload["resource_protocol_v05_1_digest"] = (
                FROZEN_RESOURCE_PROTOCOL_V05_1.digest()
            )
            payload["source_v05_failure_lock"] = failure_lock
            payload["v05_1_read_only_sha256_before"] = frozen_before
            payload["implementation_sha256"].update(_hash_paths(implementation_paths))
            payload["provenance"]["resource_decision_sha256"] = _sha256(
                RESOURCE_DECISION
            )
            payload["evidence_labels"]["resource_revision"] = (
                "V05_1_ENDPOINT_RUNTIME_60_SECONDS_ONLY"
            )
        if path.name in {"pass_summary.json", "failure.json"}:
            frozen_after = _hash_paths(frozen_paths)
            payload["v05_1_resource_repair"] = {
                "schema": "paper2_m2a_v05_1_resource_repair_result_v01",
                "old_endpoint_runtime_budget_seconds": 30.0,
                "endpoint_runtime_budget_seconds": 60.0,
                "stage_runtime_budget_seconds": 5400.0,
                "memory_budget_gib": 16.0,
                "scientific_protocol_unchanged": True,
                "identity_2d_v05_reused_read_only": True,
                "source_v05_failure_lock": failure_lock,
                "read_only_sha256_before": frozen_before,
                "read_only_sha256_after": frozen_after,
                "read_only_unchanged": frozen_before == frozen_after,
            }
            if "resource" in payload:
                payload["resource"]["endpoint_runtime_budget_seconds"] = 60.0
        if path.name == "hash_ledger.json":
            payload["schema"] = "paper2_m2a_v05_1_t256_hash_ledger_v01"
        original_write_json(path, payload)

    base_runner._write_json = write_json_with_resource_provenance


def _run(normalized_argv: list[str], path_audit: dict[str, Any]) -> None:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    import paper2_m2.config as config_module
    import paper2_m2.identity_2d_v05  # noqa: F401
    import paper2_m2.protocol_v05  # noqa: F401
    from paper2_m2.protocol_v05_1 import (
        FROZEN_RESOURCE_PROTOCOL_V05_1,
        validate_v05_failure_result,
    )

    resource_protocol = FROZEN_RESOURCE_PROTOCOL_V05_1.checked()
    failure_lock = validate_v05_failure_result(SOURCE_V05_FAILURE_DIR)
    frozen_paths = _v05_frozen_paths()
    frozen_before = _hash_paths(frozen_paths)

    base_runner = _load_base_runner()
    _install_resource_manifest_overlay(
        base_runner,
        path_audit=path_audit,
        frozen_paths=frozen_paths,
        frozen_before=frozen_before,
        failure_lock=failure_lock,
    )
    config_module.FROZEN_CONFIG = replace(
        config_module.FROZEN_CONFIG,
        endpoint_runtime_budget_seconds=resource_protocol.endpoint_runtime_budget_seconds,
    )
    base_runner._run(normalized_argv, path_audit)


def main() -> None:
    try:
        normalized_argv, path_audit = normalize_cli_project_paths(sys.argv)
    except ValueError as error:
        print(
            json.dumps(
                {
                    "schema": "paper2_m2a_v05_1_path_gate_failure_v01",
                    "status": "FAIL_CLOSED_BEFORE_OUTPUT_CREATION",
                    "reason": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
        raise SystemExit(2) from error
    _run(normalized_argv, path_audit)


if __name__ == "__main__":
    main()
