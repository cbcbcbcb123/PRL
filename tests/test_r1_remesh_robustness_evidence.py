from __future__ import annotations

from pathlib import Path

import pytest

from hybrid.r1_remesh_robustness_evidence import (
    R1EvidenceError,
    adjudicate_r1_focused_failure,
)
from hybrid.r1_verification_evidence import adjudicate_r1_verification_evidence


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/hybrid/x1_k_r1_remesh_robustness_v09/verification"


def test_v09_focused_raw_evidence_freezes_the_first_centroid_failure() -> None:
    decision = adjudicate_r1_focused_failure(EVIDENCE)

    assert decision["status"] == "failed_r1_geometry_cache_force_finite_gate"
    assert decision["first_failure_step"] == 3
    assert decision["first_failed_criterion"] == "normalized_surface_centroid_drift"
    assert decision["observed"] == pytest.approx(0.08373679738719757)
    assert decision["threshold"] == 1.0e-2
    assert decision["fixed_sample_count"] == 9
    assert decision["remesh_sample_count"] == 4
    assert decision["event_count"] == 2
    assert decision["qoi_gate_status"] == "not_adjudicated_due_to_first_failure"
    assert decision["j1_gate_status"] == "not_adjudicated_due_to_first_failure"
    assert decision["x1_k_passed"] is False
    assert decision["downstream_authorized"] is False


def test_v09_focused_evidence_fails_closed_without_real_exit_code(tmp_path: Path) -> None:
    (tmp_path / "focused_build.log").write_text("Built target\n", encoding="utf-8")
    (tmp_path / "focused_build.exitcode").write_text("0\n", encoding="ascii")
    (tmp_path / "focused_response.log").write_text("r1_gate,status,failed\n")

    with pytest.raises(R1EvidenceError, match="exit code"):
        adjudicate_r1_focused_failure(tmp_path)


def test_v09_verification_counts_are_parsed_from_real_logs() -> None:
    verification = adjudicate_r1_verification_evidence(EVIDENCE)

    assert verification["status"] == (
        "passed_software_regression_with_frozen_r1_failure"
    )
    assert verification["commands"]["parent_ctest"]["failed"] == 3
    assert (
        verification["commands"]["parent_ctest"]["passed"]
        + verification["commands"]["parent_ctest"]["failed"]
        == verification["commands"]["parent_ctest"]["total"]
    )
    assert verification["commands"]["parent_ctest"]["v09_regression_passed"]
    assert verification["commands"]["fork_ctest"]["failed"] == 0
    assert verification["commands"]["fork_ctest"]["total"] > 0
    assert verification["commands"]["python_pytest"]["passed"] > 0
    assert verification["hardcoded_verification_counts_used"] is False
