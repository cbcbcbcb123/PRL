import csv
import hashlib
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from hybrid.fixed_topology_adjudication import (
    EVIDENCE_SPECS,
    EvidenceSpec,
    EvidenceIntegrityError,
    adjudicate_fixed_topology_evidence_after_repair,
    adjudicate_fixed_topology_evidence,
)
from hybrid.verification_evidence import (
    VerificationEvidenceError,
    adjudicate_verification_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _commit_evidence_copy(
    tmp_path: Path,
    mutate: Callable[[Path], None],
) -> tuple[EvidenceSpec, ...]:
    for spec in EVIDENCE_SPECS:
        target = tmp_path / spec.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((PROJECT_ROOT / spec.path).read_bytes())
    mutate(tmp_path)
    commands = (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "v08r1-test"],
        ["git", "config", "user.email", "v08r1-test@example.invalid"],
        ["git", "add", "--", "results"],
        ["git", "commit", "-q", "-m", "freeze test evidence"],
    )
    for command in commands:
        subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return tuple(
        replace(
            spec,
            source_commit=commit,
            source_path=spec.path,
            sha256=hashlib.sha256((tmp_path / spec.path).read_bytes()).hexdigest(),
        )
        for spec in EVIDENCE_SPECS
    )


def _rewrite_csv(
    path: Path,
    mutate: Callable[[list[dict[str, str]]], None],
) -> None:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = tuple(reader.fieldnames or ())
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_v08r1_fails_closed_when_source_commit_object_is_missing() -> None:
    specs = (
        replace(EVIDENCE_SPECS[0], source_commit="0" * 40),
        *EVIDENCE_SPECS[1:],
    )

    with pytest.raises(EvidenceIntegrityError) as captured:
        adjudicate_fixed_topology_evidence(PROJECT_ROOT, evidence_specs=specs)

    assert captured.value.reason == "source_commit_missing"
    assert captured.value.path == EVIDENCE_SPECS[0].path


def test_v08r1_verifies_source_blob_bytes_and_rejects_replaced_source_path() -> None:
    decision = adjudicate_fixed_topology_evidence(PROJECT_ROOT)

    assert all(record.source_blob_verified for record in decision.provenance)
    assert all(
        record.source_blob_id == record.current_blob_id
        for record in decision.provenance
    )

    with pytest.raises(EvidenceIntegrityError) as captured:
        specs = (
            replace(EVIDENCE_SPECS[0], source_path=EVIDENCE_SPECS[1].path),
            *EVIDENCE_SPECS[1:],
        )
        adjudicate_fixed_topology_evidence(PROJECT_ROOT, evidence_specs=specs)

    assert captured.value.reason == "source_blob_mismatch"
    assert captured.value.path == EVIDENCE_SPECS[0].path


def test_v08r1_recomputes_each_v05_error_region_fraction(
    tmp_path: Path,
) -> None:
    region_path = Path(
        "results/hybrid/x1_k_mesh_family_v05/family_c_error_regions.csv"
    )

    def mutate(root: Path) -> None:
        def change(rows: list[dict[str, str]]) -> None:
            level_one = {
                row["region"]: row
                for row in rows
                if row["source_level"] == "1"
            }
            level_one["valence_5"]["fraction_of_total_error_energy"] = str(
                float(level_one["valence_5"]["fraction_of_total_error_energy"])
                + 0.01
            )
            level_one["valence_6"]["fraction_of_total_error_energy"] = str(
                float(level_one["valence_6"]["fraction_of_total_error_energy"])
                - 0.01
            )

        _rewrite_csv(root / region_path, change)

    specs = _commit_evidence_copy(tmp_path, mutate)
    with pytest.raises(EvidenceIntegrityError) as captured:
        adjudicate_fixed_topology_evidence(tmp_path, evidence_specs=specs)

    assert captured.value.reason == "v05_region_fraction_mismatch"
    assert captured.value.path == region_path.as_posix()


def test_v08r1_rebuilds_global_normal_l2_from_region_energy(
    tmp_path: Path,
) -> None:
    levels_path = Path(
        "results/hybrid/x1_k_mesh_family_v05/family_c_levels.csv"
    )

    def mutate(root: Path) -> None:
        def change(rows: list[dict[str, str]]) -> None:
            rows[0]["normal_velocity_relative_l2"] = str(
                float(rows[0]["normal_velocity_relative_l2"]) * 1.1
            )

        _rewrite_csv(root / levels_path, change)

    specs = _commit_evidence_copy(tmp_path, mutate)
    with pytest.raises(EvidenceIntegrityError) as captured:
        adjudicate_fixed_topology_evidence(tmp_path, evidence_specs=specs)

    assert captured.value.reason == "v05_global_l2_mismatch"
    assert captured.value.path == levels_path.as_posix()


def test_v08r1_recomputes_each_v05_error_energy_order(
    tmp_path: Path,
) -> None:
    order_path = Path(
        "results/hybrid/x1_k_mesh_family_v05/family_c_error_energy_orders.csv"
    )

    def mutate(root: Path) -> None:
        def change(rows: list[dict[str, str]]) -> None:
            rows[1]["valence_5_closed_one_ring_error_energy_order"] = str(
                float(rows[1]["valence_5_closed_one_ring_error_energy_order"])
                + 0.1
            )

        _rewrite_csv(root / order_path, change)

    specs = _commit_evidence_copy(tmp_path, mutate)
    with pytest.raises(EvidenceIntegrityError) as captured:
        adjudicate_fixed_topology_evidence(tmp_path, evidence_specs=specs)

    assert captured.value.reason == "v05_error_energy_order_mismatch"
    assert captured.value.path == order_path.as_posix()


def test_v08r1_pointwise_limitation_does_not_gate_revised_d1(
    tmp_path: Path,
) -> None:
    region_path = Path(
        "results/hybrid/x1_k_mesh_family_v05/family_c_error_regions.csv"
    )
    improving = [0.15, 0.14, 0.13, 0.12]

    def mutate(root: Path) -> None:
        def change(rows: list[dict[str, str]]) -> None:
            for row in rows:
                if row["region"] == "valence_5":
                    row["maximum_pointwise_relative_error"] = str(
                        improving[int(row["source_level"]) - 1]
                    )

        _rewrite_csv(root / region_path, change)

    specs = _commit_evidence_copy(tmp_path, mutate)
    decision = adjudicate_fixed_topology_evidence(tmp_path, evidence_specs=specs)
    limitations = [
        record for record in decision.decisions if record.role == "limitation"
    ]

    assert decision.revised_d1_passed
    assert len(limitations) == 1
    assert limitations[0].observed == improving
    assert not decision.pointwise_convergence_claim_allowed
    assert not decision.uniform_convergence_claim_allowed


def test_v08r1_verification_fails_closed_without_real_command_evidence(
    tmp_path: Path,
) -> None:
    with pytest.raises(VerificationEvidenceError) as captured:
        adjudicate_verification_evidence(tmp_path)

    assert captured.value.reason == "verification_log_missing"
    assert captured.value.path == "parent_ctest.log"


def test_v08r1_verification_summary_is_parsed_from_logs_and_exit_codes(
    tmp_path: Path,
) -> None:
    logs = {
        "parent_ctest": (
            1,
            "95% tests passed, 3 tests failed out of 55\n"
            "The following tests FAILED:\n"
            " 39 - prl_x1k_sphere_instantaneous_velocity_refinement (Failed)\n"
            " 44 - prl_x1k_v04_family_b_parameterized_diagnosis (Failed)\n"
            " 48 - prl_x1k_v06_family_c_short_trajectory_gate (Failed)\n",
        ),
        "fork_ctest": (0, "100% tests passed, 0 tests failed out of 134\n"),
        "strict_prl_core": (0, "[100%] Built target prl_core\n"),
        "python_pytest": (0, "72 passed in 12.34s\n"),
        "ruff": (0, "All checks passed!\n"),
    }
    for command, (exit_code, output) in logs.items():
        (tmp_path / f"{command}.log").write_text(output, encoding="utf-8")
        (tmp_path / f"{command}.exitcode").write_text(
            f"{exit_code}\n", encoding="ascii"
        )

    result = adjudicate_verification_evidence(tmp_path)

    assert result["status"] == "passed_with_expected_historical_failures"
    assert result["commands"]["parent_ctest"]["passed"] == 52
    assert result["commands"]["parent_ctest"]["total"] == 55
    assert result["commands"]["fork_ctest"]["passed"] == 134
    assert result["commands"]["python_pytest"]["passed"] == 72
    assert all(record["log_sha256"] for record in result["commands"].values())


def test_v08r1_repaired_entrypoint_preserves_v08_rejection_and_stops_at_d1_s1() -> None:
    decision = adjudicate_fixed_topology_evidence_after_repair(PROJECT_ROOT)

    assert (
        decision.status
        == "passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair"
    )
    assert (
        decision.historical_statuses["v08"]
        == "failed_adjudicator_contract_incomplete"
    )
    assert decision.revised_d1_passed
    assert decision.revised_s1_passed
    assert not decision.x1_k_passed
    assert decision.r1_c1_f1_status == "not_executed"
    assert not decision.downstream_authorized
