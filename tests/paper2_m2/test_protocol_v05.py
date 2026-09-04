from __future__ import annotations

from pathlib import Path

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.protocol_v04 import validate_source_t64_result
from paper2_m2.protocol_v05 import (
    EXPECTED_T128_ENDPOINT_SUMMARIES_SHA256,
    EXPECTED_T128_HASH_LEDGER_SHA256,
    EXPECTED_T128_PASS_SUMMARY_SHA256,
    FROZEN_PROTOCOL_V05,
    validate_source_t128_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_v05_protocol_freezes_t256_and_three_level_gate() -> None:
    protocol = FROZEN_PROTOCOL_V05.checked()
    assert [(level.label, level.nx, level.ny_per_layer) for level in protocol.spatial_levels] == [
        ("S2", 32, 8),
        ("S3", 64, 16),
        ("S4", 128, 32),
    ]
    assert protocol.steps_per_cycle == 256
    assert protocol.solver_levels == ("D0",)
    assert protocol.expected_endpoint_count == 54
    assert protocol.expected_three_level_time_records == 74
    payload = protocol.canonical_payload()
    assert "tolerance_labels" not in payload
    assert payload["matrix"]["solver_levels"] == ["D0"]
    assert payload["matrix"]["steps_per_cycle"] == 256
    assert payload["three_level_time_gate"]["source_levels"] == ["T64", "T128"]
    assert payload["three_level_time_gate"]["target"] == "T256"
    assert payload["three_level_time_gate"]["finest_relative_tolerance"] == 0.01


def test_v05_source_locks_match_t64_and_t128_results() -> None:
    source_t64 = (
        PROJECT_ROOT / "results" / "paper2_m2" / "identity_2d_v03_t64_v01_20260903"
    )
    source_t128 = (
        PROJECT_ROOT / "results" / "paper2_m2" / "identity_2d_v04_t128_v02_20260903"
    )
    lock_t64 = validate_source_t64_result(source_t64)
    lock_t128 = validate_source_t128_result(source_t128)
    assert lock_t64["pass"] is True
    assert lock_t64["endpoint_count"] == 54
    assert lock_t128["pass"] is True
    assert lock_t128["endpoint_count"] == 54
    assert lock_t128["hash_ledger_entries"] == 25
    assert lock_t128["selected_dynamic_holdout_npz"] == 12
    assert lock_t128["hashes"]["endpoint_summaries.json"]["actual"] == (
        EXPECTED_T128_ENDPOINT_SUMMARIES_SHA256
    )
    assert lock_t128["hashes"]["hash_ledger.json"]["actual"] == (
        EXPECTED_T128_HASH_LEDGER_SHA256
    )
    assert lock_t128["hashes"]["pass_summary.json"]["actual"] == (
        EXPECTED_T128_PASS_SUMMARY_SHA256
    )
    assert len(FROZEN_CONFIG.cases) == 9

