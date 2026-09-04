"""Resource-only v05.1 overlay for the frozen M2A v05 T256 protocol."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .config import FROZEN_CONFIG
from .protocol_v05 import FROZEN_PROTOCOL_V05


OLD_ENDPOINT_RUNTIME_BUDGET_SECONDS = 30.0
ENDPOINT_RUNTIME_BUDGET_SECONDS = 60.0
OBSERVED_V05_FAILURE_RUNTIME_SECONDS = 30.38510538799892
EXPECTED_V05_FAILURE_SHA256 = (
    "c98eb9c2af4e1412449c453acce938c86000bea8c719bbfdb41015df2242b32f"
)
EXPECTED_V05_PARTIAL_SUMMARIES_SHA256 = (
    "56116df09b677f2447aee95fb724323c95d6b111545b9744970b3c8645c81cbc"
)
EXPECTED_V05_STRUCTURAL_GATES_SHA256 = (
    "01d0ac1b278f9f9b172358a09e28fe995adf8c1c31fbdf626f85f0e8fbabf3ee"
)
EXPECTED_V05_RUN_MANIFEST_SHA256 = (
    "d7d3b72bdd73f8f5d5abe4f509f79af7e586a2bb5f44cc9ae5007d3ec888352e"
)
EXPECTED_V05_HASH_LEDGER_SHA256 = (
    "73b11028032d0654ca7c841d03b25abdf30f7f41ffd5b6e3f1ed38b06e4eebf1"
)
EXPECTED_V05_LEDGER_ENTRY_COUNT = 11
EXPECTED_V05_JSON_COUNT = 12
EXPECTED_V05_PARTIAL_ENDPOINT_COUNT = 18


@dataclass(frozen=True)
class M2AV051ResourceProtocol:
    schema: str = "paper2_m2a_resource_protocol_v05_1"
    base_scientific_protocol_schema: str = "paper2_m2a_protocol_v05"
    base_scientific_protocol_digest: str = FROZEN_PROTOCOL_V05.digest()
    old_endpoint_runtime_budget_seconds: float = OLD_ENDPOINT_RUNTIME_BUDGET_SECONDS
    endpoint_runtime_budget_seconds: float = ENDPOINT_RUNTIME_BUDGET_SECONDS
    stage_runtime_budget_seconds: float = FROZEN_PROTOCOL_V05.runtime_budget_seconds
    memory_budget_gib: float = FROZEN_PROTOCOL_V05.memory_budget_gib
    cpu_processes: int = FROZEN_PROTOCOL_V05.cpu_processes
    gpu_used: bool = False

    def checked(self) -> "M2AV051ResourceProtocol":
        FROZEN_PROTOCOL_V05.checked()
        if FROZEN_CONFIG.endpoint_runtime_budget_seconds != 30.0:
            raise ValueError("the frozen v05 endpoint runtime gate changed")
        if self.old_endpoint_runtime_budget_seconds != 30.0:
            raise ValueError("the v05 baseline endpoint runtime gate must remain 30 s")
        if self.endpoint_runtime_budget_seconds != 60.0:
            raise ValueError("the v05.1 endpoint runtime gate must remain 60 s")
        if self.stage_runtime_budget_seconds != FROZEN_PROTOCOL_V05.runtime_budget_seconds:
            raise ValueError("the v05.1 stage runtime budget changed")
        if self.memory_budget_gib != FROZEN_PROTOCOL_V05.memory_budget_gib:
            raise ValueError("the v05.1 memory budget changed")
        if self.cpu_processes != 1 or self.gpu_used:
            raise ValueError("v05.1 must remain CPU-only and single-process")
        if self.base_scientific_protocol_digest != FROZEN_PROTOCOL_V05.digest():
            raise ValueError("the frozen v05 scientific protocol digest changed")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self.checked())
        payload["allowed_differences_from_v05"] = {
            "version_identifier": ["v05", "v05_1"],
            "endpoint_runtime_budget_seconds": [30.0, 60.0],
        }
        payload["scientific_protocol"] = FROZEN_PROTOCOL_V05.canonical_payload()
        payload["scientific_protocol_unchanged"] = True
        payload["three_level_time_algorithm_unchanged"] = True
        return payload

    def digest(self) -> str:
        serialized = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


def endpoint_runtime_gate(runtime_seconds: float) -> dict[str, Any]:
    finite = math.isfinite(runtime_seconds)
    passed = bool(finite and runtime_seconds <= ENDPOINT_RUNTIME_BUDGET_SECONDS)
    return {
        "runtime_seconds": runtime_seconds if finite else None,
        "threshold_seconds": ENDPOINT_RUNTIME_BUDGET_SECONDS,
        "finite": finite,
        "pass": passed,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_json(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_json(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    return False


def validate_v05_failure_result(source_dir: Path) -> dict[str, Any]:
    expected_hashes = {
        "failure.json": EXPECTED_V05_FAILURE_SHA256,
        "endpoint_summaries_partial.json": EXPECTED_V05_PARTIAL_SUMMARIES_SHA256,
        "structural_gates_partial.json": EXPECTED_V05_STRUCTURAL_GATES_SHA256,
        "run_manifest.json": EXPECTED_V05_RUN_MANIFEST_SHA256,
        "hash_ledger.json": EXPECTED_V05_HASH_LEDGER_SHA256,
    }
    hashes: dict[str, Any] = {}
    for name, expected in expected_hashes.items():
        actual = _sha256(source_dir / name)
        hashes[name] = {"expected": expected, "actual": actual, "pass": actual == expected}

    with (source_dir / "failure.json").open("r", encoding="utf-8") as stream:
        failure = json.load(stream)
    with (source_dir / "endpoint_summaries_partial.json").open(
        "r", encoding="utf-8"
    ) as stream:
        summaries = json.load(stream)
    with (source_dir / "structural_gates_partial.json").open(
        "r", encoding="utf-8"
    ) as stream:
        structural = json.load(stream)
    with (source_dir / "hash_ledger.json").open("r", encoding="utf-8") as stream:
        ledger = json.load(stream)

    ledger_failures: list[str] = []
    for relative_path, record in ledger.get("files", {}).items():
        path = source_dir / relative_path
        if not path.is_file():
            ledger_failures.append(f"missing:{relative_path}")
            continue
        if _sha256(path) != record.get("sha256"):
            ledger_failures.append(f"sha256:{relative_path}")
        if path.stat().st_size != record.get("bytes"):
            ledger_failures.append(f"bytes:{relative_path}")

    json_paths = sorted(source_dir.rglob("*.json"))
    json_finite = True
    for path in json_paths:
        with path.open("r", encoding="utf-8") as stream:
            json_finite = json_finite and _finite_json(json.load(stream))
    endpoint_keys_pass = bool(
        len(summaries) == EXPECTED_V05_PARTIAL_ENDPOINT_COUNT
        and all(key.endswith("__T256__D0") for key in summaries)
    )
    structural_pass = bool(
        len(structural) == EXPECTED_V05_PARTIAL_ENDPOINT_COUNT
        and all(record.get("pass") is True for record in structural.values())
    )
    failure_replayed = bool(
        failure.get("stage") == "T256_endpoint"
        and failure.get("endpoint") == "ID-A1__FEM__S4__T256__D0"
        and failure.get("completed_endpoints") == EXPECTED_V05_PARTIAL_ENDPOINT_COUNT
        and failure.get("endpoint_runtime_seconds")
        == OBSERVED_V05_FAILURE_RUNTIME_SECONDS
        and failure.get("endpoint_runtime_budget_seconds")
        == OLD_ENDPOINT_RUNTIME_BUDGET_SECONDS
        and failure.get("structural_gate", {}).get("pass") is True
    )
    passed = bool(
        all(record["pass"] for record in hashes.values())
        and not ledger_failures
        and len(ledger.get("files", {})) == EXPECTED_V05_LEDGER_ENTRY_COUNT
        and len(json_paths) == EXPECTED_V05_JSON_COUNT
        and json_finite
        and endpoint_keys_pass
        and structural_pass
        and failure_replayed
    )
    if not passed:
        raise ValueError("the frozen v05 failure package failed its v05.1 replay lock")
    return {
        "schema": "paper2_m2a_v05_1_source_v05_failure_lock_v01",
        "hashes": hashes,
        "hash_ledger_entries": len(ledger["files"]),
        "hash_ledger_failures": ledger_failures,
        "json_files": len(json_paths),
        "json_finite": json_finite,
        "partial_endpoint_count": len(summaries),
        "all_partial_keys_T256_D0": endpoint_keys_pass,
        "all_partial_structural_gates_pass": structural_pass,
        "observed_runtime_seconds": failure["endpoint_runtime_seconds"],
        "old_threshold_seconds": failure["endpoint_runtime_budget_seconds"],
        "failure_replayed": failure_replayed,
        "pass": True,
    }


FROZEN_RESOURCE_PROTOCOL_V05_1 = M2AV051ResourceProtocol().checked()
