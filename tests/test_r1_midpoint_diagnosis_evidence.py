from __future__ import annotations

from pathlib import Path

import pytest

from hybrid.r1_midpoint_diagnosis_evidence import (
    V10EvidenceError,
    adjudicate_midpoint_failure,
    adjudicate_v10_verification,
    audit_fork_source_provenance,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw"


def test_v10_raw_response_freezes_the_first_eligible_candidate_failure() -> None:
    decision = adjudicate_midpoint_failure(
        RAW / "formal_response.log",
        RAW / "formal_response.exitcode",
    )

    assert decision["status"] == (
        "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind"
    )
    assert decision["split_gate"]["passed"] is True
    assert decision["frozen_merge"]["analytic_residual"] == 0.0
    assert decision["frozen_merge"]["distance_from_x0_over_original_edge"] == 0.25
    assert decision["candidate_count"] == 4
    assert decision["eligible_count"] == 4
    assert decision["first_failed_candidate"] == 3
    assert decision["candidates"][2]["local_0"] == 2
    assert decision["candidates"][2]["local_1"] == 8
    assert decision["candidates"][2]["can_be_merged"] is True
    assert decision["candidates"][2]["merge_succeeded"] is False
    assert decision["candidates"][2]["rebind_distance"] == pytest.approx(
        0.047434164902525666
    )
    assert decision["any_geometric_inverse"] is False
    assert decision["classification_status"] == "not_adjudicated_due_to_first_failure"
    assert decision["x1_k_passed"] is False
    assert decision["c1_f1"] == "not_executed"


def test_v10_adjudicator_fails_closed_if_quarter_point_is_changed(
    tmp_path: Path,
) -> None:
    payload = (RAW / "formal_response.log").read_text(encoding="utf-8")
    changed = payload.replace(
        "distance_from_x0_over_original_edge,0.25",
        "distance_from_x0_over_original_edge,0.24",
        1,
    )
    log_path = tmp_path / "formal_response.log"
    exit_path = tmp_path / "formal_response.exitcode"
    log_path.write_text(changed, encoding="utf-8")
    exit_path.write_text("1\n", encoding="ascii")

    with pytest.raises(V10EvidenceError, match="quarter-point"):
        adjudicate_midpoint_failure(log_path, exit_path)


def test_v10_adjudicator_requires_the_nonzero_formal_exit(tmp_path: Path) -> None:
    log_path = tmp_path / "formal_response.log"
    exit_path = tmp_path / "formal_response.exitcode"
    log_path.write_bytes((RAW / "formal_response.log").read_bytes())
    exit_path.write_text("0\n", encoding="ascii")

    with pytest.raises(V10EvidenceError, match="exit code"):
        adjudicate_midpoint_failure(log_path, exit_path)


def test_v10_source_provenance_closes_against_the_controlled_fork() -> None:
    provenance = audit_fork_source_provenance(ROOT)

    assert provenance["fork_commit"] == (
        "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a"
    )
    assert provenance["head"] == provenance["upstream"]
    assert provenance["fork_clean"] is True
    assert len(provenance["files"]) == 5
    assert all(item["source_blob_verified"] for item in provenance["files"])
    assert provenance["midpoint_statement_verified"] is True
    assert provenance["both_endpoints_replaced_verified"] is True
    assert provenance["public_header_identity_control_found"] is False
    assert provenance["event_identity_control_found"] is False
    assert provenance["classification_role"] == (
        "supporting_not_adjudicated_due_to_first_failure"
    )


def test_v10_verification_is_parsed_from_real_logs() -> None:
    verification = adjudicate_v10_verification(
        ROOT
        / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/verification"
    )

    assert verification["status"] == (
        "passed_software_regression_with_frozen_v10_failure"
    )
    assert verification["commands"]["parent_ctest"]["passed"] == 54
    assert verification["commands"]["parent_ctest"]["failed"] == 3
    assert verification["commands"]["parent_ctest"]["total"] == 57
    assert verification["commands"]["parent_ctest"][
        "v10_frozen_failure_regression_passed"
    ]
    assert verification["commands"]["fork_ctest"]["passed"] == 134
    assert verification["commands"]["python_pytest"]["passed"] >= 82
    assert verification["hardcoded_verification_counts_used"] is False
