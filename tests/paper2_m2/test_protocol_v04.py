from __future__ import annotations

from pathlib import Path

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.protocol_v04 import (
    EXPECTED_T64_ENDPOINT_SUMMARIES_SHA256,
    EXPECTED_T64_HASH_LEDGER_SHA256,
    EXPECTED_T64_PASS_SUMMARY_SHA256,
    FROZEN_PROTOCOL_V04,
    validate_source_t64_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_v04_protocol_freezes_t128_and_one_d0_axis() -> None:
    protocol = FROZEN_PROTOCOL_V04.checked()
    assert [(level.label, level.nx, level.ny_per_layer) for level in protocol.spatial_levels] == [
        ("S2", 32, 8),
        ("S3", 64, 16),
        ("S4", 128, 32),
    ]
    assert protocol.steps_per_cycle == 128
    assert protocol.solver_levels == ("D0",)
    assert protocol.expected_endpoint_count == 54
    payload = protocol.canonical_payload()
    assert "tolerance_labels" not in payload
    assert payload["matrix"]["solver_levels"] == ["D0"]
    assert payload["time_pair_audit"]["label"] == "T64_T128_PAIR_AUDIT_ONLY"
    assert payload["time_pair_audit"]["expected_records"] == 74


def test_v04_source_t64_lock_matches_the_frozen_result() -> None:
    source_dir = (
        PROJECT_ROOT
        / "results"
        / "paper2_m2"
        / "identity_2d_v03_t64_v01_20260903"
    )
    result = validate_source_t64_result(source_dir)
    assert result["pass"] is True
    assert result["endpoint_count"] == 54
    assert result["all_keys_T64_D0"] is True
    assert result["hashes"]["endpoint_summaries.json"]["actual"] == (
        EXPECTED_T64_ENDPOINT_SUMMARIES_SHA256
    )
    assert result["hashes"]["hash_ledger.json"]["actual"] == (
        EXPECTED_T64_HASH_LEDGER_SHA256
    )
    assert result["hashes"]["pass_summary.json"]["actual"] == (
        EXPECTED_T64_PASS_SUMMARY_SHA256
    )
    assert len(FROZEN_CONFIG.cases) == 9
