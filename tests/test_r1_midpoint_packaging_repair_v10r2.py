from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from hybrid.r1_midpoint_packaging_repair_v10r2 import (
    V10R2EvidenceError,
    build_count_reconciliation,
    build_v10r2_configuration,
    parse_combined_verification,
    verify_configuration_sources,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v10r2_locator_verifier_reads_frozen_blob_instead_of_json_echo() -> None:
    payload = build_v10r2_configuration(ROOT)
    report = verify_configuration_sources(ROOT, payload)

    assert report["status"] == "passed_configuration_source_resolution"
    assert report["canonical_leaf_count"] == 32
    assert report["resolved_leaf_count"] == 32
    assert len(report["resolved_fields"]) == 32

    tampered = copy.deepcopy(payload)
    target = next(
        item
        for item in tampered["field_provenance"]
        if item["field"] == "configuration.execution.production_path"
    )
    target["sources"][0]["locator"] = {
        "kind": "line_range",
        "start": 1,
        "end": 1,
        "parser": "v10_production_pipeline",
    }
    target["sources"][0]["source_value"] = target["value"]

    with pytest.raises(V10R2EvidenceError, match="resolved value"):
        verify_configuration_sources(ROOT, tampered)


def test_v10r2_count_reconciliation_recomputes_unique_canonical_sets() -> None:
    configuration = build_v10r2_configuration(ROOT)
    reconciliation = build_count_reconciliation(ROOT, configuration)

    configuration_count = reconciliation["canonical_counts"]["configuration"]
    assert configuration_count["definition"] == (
        "recursively expand mappings; treat each array as one leaf"
    )
    assert configuration_count["count"] == 32
    assert configuration_count["items"] == sorted(configuration_count["items"])
    assert len(configuration_count["items"]) == len(
        set(configuration_count["items"])
    )
    assert set(configuration_count["items"]) == {
        item["field"] for item in configuration["field_provenance"]
    }

    lifecycle = reconciliation["canonical_counts"]["frozen_lifecycle_blobs"]
    assert lifecycle["definition"] == (
        "unique changed paths across the six frozen v09/v10 lifecycle commits"
    )
    assert len(lifecycle["source_commits"]) == 6
    assert lifecycle["count"] == 102
    paths = [item["path"] for item in lifecycle["items"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert all(item["source_commits"] for item in lifecycle["items"])

    for label in ("37", "105"):
        interim = reconciliation["superseded_interim_counts"][label]
        assert interim["status"] == (
            "non_versioned_interim_miscount_superseded_non_reconstructable"
        )
        assert interim["entered_frozen_summary"] is False
        assert interim["entered_frozen_manifest"] is False
        assert interim["entered_gate"] is False


def test_combined_verification_parser_uses_logged_identity_and_pytest_count(
    tmp_path: Path,
) -> None:
    fork_identity = "a" * 40
    invocation = {
        "argv": ["wrapper", "--", "-q"],
        "repo_root": "C:/repo",
        "controlled_parent_root": "E:/controlled",
        "fork_root": "E:/controlled/external/simucell3d",
        "pytest_args": ["-q"],
    }
    preflight = {
        "fork_head": fork_identity,
        "fork_upstream": fork_identity,
        "fork_tracked_clean": True,
        "fork_tracked_status": [],
        "gitlink": fork_identity,
    }
    result = {"pytest_exit_code": 0, "wrapper_exit_code": 0}
    log_path = tmp_path / "combined.log"
    exitcode_path = tmp_path / "combined.exitcode"
    log_path.write_text(
        "\n".join(
            [
                f"V10R2_INVOCATION_JSON {json.dumps(invocation)}",
                f"V10R2_PREFLIGHT_JSON {json.dumps(preflight)}",
                "....... [100%]",
                "7 passed in 1.23s",
                f"V10R2_RESULT_JSON {json.dumps(result)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    exitcode_path.write_text("0\n", encoding="utf-8")

    parsed = parse_combined_verification(log_path, exitcode_path)

    assert parsed["status"] == "passed_combined_controlled_fork_verification"
    assert parsed["fork_identity"] == fork_identity
    assert parsed["pytest"]["passed"] == 7
    assert parsed["pytest"]["exit_code"] == 0
    assert parsed["invocation"] == invocation

    preflight["fork_upstream"] = "b" * 40
    log_path.write_text(
        "\n".join(
            [
                f"V10R2_INVOCATION_JSON {json.dumps(invocation)}",
                f"V10R2_PREFLIGHT_JSON {json.dumps(preflight)}",
                "7 passed in 1.23s",
                f"V10R2_RESULT_JSON {json.dumps(result)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(V10R2EvidenceError, match="identity"):
        parse_combined_verification(log_path, exitcode_path)
