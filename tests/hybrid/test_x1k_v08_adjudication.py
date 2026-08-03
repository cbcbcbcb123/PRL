from pathlib import Path
from shutil import copy2

import pytest

from hybrid.fixed_topology_adjudication import (
    EvidenceIntegrityError,
    adjudicate_fixed_topology_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_v08_adjudicator_fails_closed_when_required_raw_evidence_is_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        EvidenceIntegrityError,
        match=r"missing required evidence.*family_c_levels\.csv",
    ):
        adjudicate_fixed_topology_evidence(tmp_path)


def test_v08_adjudicator_recomputes_revised_d1_s1_from_frozen_raw_csv() -> None:
    decision = adjudicate_fixed_topology_evidence(PROJECT_ROOT)

    assert decision.status == "passed_revised_fixed_topology_d1_s1_acceptance"
    assert decision.evidence_integrity_passed
    assert decision.revised_d1_passed
    assert decision.revised_s1_passed
    assert len(decision.provenance) == 23
    assert decision.historical_statuses == {
        "route_h_gate_a_v01": "failed_invalid_numerics",
        "v02_d1": "failed_instantaneous_smooth_surface_refinement",
        "v04_family_b": "failed_family_B_parameterized_diagnosis",
        "v06_mean_radius_spatial": (
            "failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic"
        ),
    }
    assert len(
        [record for record in decision.decisions if record.role == "historical_evidence"]
    ) == 4
    assert not decision.x1_k_passed
    assert decision.r1_c1_f1_status == "not_executed"
    assert not decision.downstream_authorized
    assert not decision.pointwise_convergence_claim_allowed
    assert not decision.uniform_convergence_claim_allowed


def test_v08_adjudicator_reports_the_first_tampered_raw_evidence(
    tmp_path: Path,
) -> None:
    baseline = adjudicate_fixed_topology_evidence(PROJECT_ROOT)
    for record in baseline.provenance:
        target = tmp_path / record.path
        target.parent.mkdir(parents=True, exist_ok=True)
        copy2(PROJECT_ROOT / record.path, target)
    tampered_path = baseline.provenance[0].path
    target = tmp_path / tampered_path
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(EvidenceIntegrityError) as captured:
        adjudicate_fixed_topology_evidence(tmp_path)

    assert captured.value.reason == "sha256_mismatch"
    assert captured.value.path == tampered_path
