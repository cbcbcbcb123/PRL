from __future__ import annotations

from pathlib import Path

from paper2_m2.protocol_v05 import FROZEN_PROTOCOL_V05
from paper2_m2.protocol_v05_1 import (
    FROZEN_RESOURCE_PROTOCOL_V05_1,
    OBSERVED_V05_FAILURE_RUNTIME_SECONDS,
    validate_v05_failure_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_v05_1_changes_only_resource_version_and_endpoint_runtime_gate() -> None:
    base = FROZEN_PROTOCOL_V05.checked()
    resource = FROZEN_RESOURCE_PROTOCOL_V05_1.checked()
    payload = resource.canonical_payload()
    assert resource.base_scientific_protocol_digest == base.digest()
    assert payload["scientific_protocol"] == base.canonical_payload()
    assert payload["scientific_protocol_unchanged"] is True
    assert payload["three_level_time_algorithm_unchanged"] is True
    assert payload["allowed_differences_from_v05"] == {
        "version_identifier": ["v05", "v05_1"],
        "endpoint_runtime_budget_seconds": [30.0, 60.0],
    }
    assert resource.endpoint_runtime_budget_seconds == 60.0
    assert resource.stage_runtime_budget_seconds == base.runtime_budget_seconds == 5400.0
    assert resource.memory_budget_gib == base.memory_budget_gib == 16.0
    assert resource.cpu_processes == base.cpu_processes == 1
    assert resource.gpu_used is False


def test_v05_failure_package_replays_exactly() -> None:
    source = (
        PROJECT_ROOT
        / "results"
        / "paper2_m2"
        / "identity_2d_v05_t256_v01_20260904"
    )
    lock = validate_v05_failure_result(source)
    assert lock["pass"] is True
    assert lock["failure_replayed"] is True
    assert lock["partial_endpoint_count"] == 18
    assert lock["all_partial_structural_gates_pass"] is True
    assert lock["observed_runtime_seconds"] == OBSERVED_V05_FAILURE_RUNTIME_SECONDS
    assert lock["old_threshold_seconds"] == 30.0
    assert lock["hash_ledger_entries"] == 11
    assert lock["json_files"] == 12
