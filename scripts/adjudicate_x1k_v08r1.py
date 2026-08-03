from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hybrid.fixed_topology_adjudication import (
    AdjudicationDecision,
    adjudicate_fixed_topology_evidence_after_repair,
)
from hybrid.verification_evidence import adjudicate_verification_evidence


CONTRACT_ID = "CONTRACT-PRL-HYBRID-X1-K-V08R1-ADJUDICATOR-REPAIR"
CONTRACT_COMMIT = "a500893e86c2d5415a48a8458a8a0c2f7eb721ce"
RESULT_PACKAGE_COMMIT = "d457d558757c8b107e92ed43b24985cecbc99fad"


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _decision_rows(decision: AdjudicationDecision) -> list[list[Any]]:
    return [
        [
            record.role,
            record.scope,
            record.criterion,
            record.operator,
            record.threshold,
            json.dumps(record.observed, ensure_ascii=False, sort_keys=True),
            str(record.passed).lower(),
            ";".join(record.provenance),
            record.notes,
        ]
        for record in decision.decisions
    ]


def write_package(
    output_dir: Path,
    decision: AdjudicationDecision,
    verification: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    header = [
        "role",
        "scope",
        "criterion",
        "operator",
        "threshold",
        "observed",
        "passed",
        "provenance",
        "notes",
    ]
    rows = _decision_rows(decision)
    _write_csv(output_dir / "decision_matrix.csv", header, rows)
    _write_csv(
        output_dir / "criteria.csv",
        header,
        [row for row in rows if row[0] in {"revised_acceptance", "limitation"}],
    )
    _write_json(
        output_dir / "provenance_manifest.json",
        {
            "contract_id": CONTRACT_ID,
            "contract_commit": CONTRACT_COMMIT,
            "required_file_count": len(decision.provenance),
            "files": [asdict(record) for record in decision.provenance],
            "checks": {
                "sha256_rows_schema": decision.evidence_integrity_passed,
                "source_commit_path_blobs": all(
                    record.source_blob_verified for record in decision.provenance
                ),
                "source_and_current_blob_ids_equal": all(
                    record.source_blob_id == record.current_blob_id
                    for record in decision.provenance
                ),
                "finite_values": decision.evidence_integrity_passed,
                "run_and_region_keys_closed": decision.evidence_integrity_passed,
                "global_local_energy_keys_closed": decision.evidence_integrity_passed,
                "ledger_recomputed": all(
                    record["ledger_recomputed"]
                    for record in decision.ledger_recomputations.values()
                ),
            },
        },
    )
    _write_json(output_dir / "ledger_recomputation.json", decision.ledger_recomputations)
    _write_json(output_dir / "verification_summary.json", verification)
    summary = {
        "contract_id": CONTRACT_ID,
        "contract_commit": CONTRACT_COMMIT,
        "result_package_commit": RESULT_PACKAGE_COMMIT,
        "status": decision.status,
        "v08_rejection_status": "failed_adjudicator_contract_incomplete",
        "historical_evidence_status": decision.historical_statuses,
        "revised_acceptance": {
            "evidence_integrity_passed": decision.evidence_integrity_passed,
            "d1_passed": decision.revised_d1_passed,
            "s1_passed": decision.revised_s1_passed,
        },
        "x1_k_passed": decision.x1_k_passed,
        "r1_c1_f1": decision.r1_c1_f1_status,
        "downstream_authorized": decision.downstream_authorized,
        "limitations": {
            "pointwise_convergence_claim_allowed": (
                decision.pointwise_convergence_claim_allowed
            ),
            "uniform_convergence_claim_allowed": (
                decision.uniform_convergence_claim_allowed
            ),
            "v05_valence_5_pointwise_maxima": decision.metrics["revised_d1"][
                "valence_5_pointwise_maxima"
            ],
            "role_in_acceptance_aggregate": False,
            "interpretation": (
                "The sequence is mandatory provenance but cannot gate D1 or "
                "authorize pointwise/uniform convergence claims."
            ),
        },
        "metrics": decision.metrics,
        "ledger_recomputations": decision.ledger_recomputations,
        "provenance_file_count": len(decision.provenance),
        "decision_count": len(decision.decisions),
        "revised_acceptance_failure_count": sum(
            1
            for record in decision.decisions
            if record.role == "revised_acceptance" and not record.passed
        ),
        "verification": verification,
        "not_executed": [
            "R1_remesh_on",
            "C1_contact",
            "F1_failure_persistence",
            "ECM_flow_long_coupling",
            "parameter_calibration",
        ],
        "claim_guard": (
            "v08r1 repairs the fixed-topology evidence adjudicator only. v08 "
            "remains rejected; X1-K and downstream mechanistic, long-time, "
            "physiological, FSI, EFE and calibration claims are not authorized."
        ),
    }
    _write_json(output_dir / "summary.json", summary)
    with (output_dir / "passing_evidence.txt").open(
        "w", encoding="utf-8", newline="\n"
    ) as target:
        target.write(
            "\n".join(
                [
                    "X1-K v08r1 repaired adjudication evidence",
                    f"status: {decision.status}",
                    "v08: failed_adjudicator_contract_incomplete",
                    "historical v02/v04/v06: failed, unchanged",
                    f"required raw evidence files: {len(decision.provenance)}",
                    "source/current Git blobs verified: true",
                    "v05 fraction/global-L2/error-order semantics recomputed: true",
                    "limitation included in D1 acceptance aggregate: false",
                    f"machine verification: {verification['status']}",
                    f"revised D1 passed: {str(decision.revised_d1_passed).lower()}",
                    f"revised S1 passed: {str(decision.revised_s1_passed).lower()}",
                    f"X1-K passed: {str(decision.x1_k_passed).lower()}",
                    f"R1/C1/F1: {decision.r1_c1_f1_status}",
                    f"downstream authorized: {str(decision.downstream_authorized).lower()}",
                    "",
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the repaired X1-K v08r1 raw-evidence adjudicator."
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--verification-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    decision = adjudicate_fixed_topology_evidence_after_repair(
        args.workspace.resolve()
    )
    verification = adjudicate_verification_evidence(
        args.verification_dir.resolve()
    )
    write_package(args.output_dir, decision, verification)
    print(decision.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
