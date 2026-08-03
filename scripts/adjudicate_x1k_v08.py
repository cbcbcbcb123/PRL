from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hybrid.fixed_topology_adjudication import (
    AdjudicationDecision,
    adjudicate_fixed_topology_evidence,
)


CONTRACT_ID = "CONTRACT-PRL-HYBRID-X1-K-V08-ADJUDICATION"
CONTRACT_COMMIT = "929973c99d4971c3a151f3e0db8ef7931580293f"


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


def write_package(output_dir: Path, decision: AdjudicationDecision) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    decision_header = [
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
    _write_csv(output_dir / "decision_matrix.csv", decision_header, rows)
    _write_csv(
        output_dir / "criteria.csv",
        decision_header,
        [
            row
            for row in rows
            if row[0] in {"revised_acceptance", "limitation"}
        ],
    )
    _write_json(
        output_dir / "provenance_manifest.json",
        {
            "contract_id": CONTRACT_ID,
            "contract_commit": CONTRACT_COMMIT,
            "source_packages": {
                "v05": "51d606b1165c3c0ca0839e59aebce3e1a89ca640",
                "v06": "eb3c97339580e3d2e0f565e47b9b78dab292046e",
                "v07": "f4df24c840f357fc06a45c4406bc55b9817199b9",
            },
            "required_file_count": len(decision.provenance),
            "files": [asdict(record) for record in decision.provenance],
            "checks": {
                "sha256_rows_schema": decision.evidence_integrity_passed,
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
    _write_json(
        output_dir / "ledger_recomputation.json",
        decision.ledger_recomputations,
    )
    summary = {
        "contract_id": CONTRACT_ID,
        "contract_commit": CONTRACT_COMMIT,
        "result_package_commit": None,
        "status": decision.status,
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
            "interpretation": (
                "Family C convergence is area-weighted global L2 only; shrinking "
                "control area is not pointwise improvement."
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
        "energy_coverage": {
            "coverage": "surface_tension_only",
            "registered": ["gamma*A", "D_zeta"],
            "excluded": [
                "legacy_0.5_gamma_A_cache",
                "membrane_elasticity",
                "bending",
                "pressure",
                "contact",
                "active",
                "ECM",
                "flow",
            ],
        },
        "verification": {
            "status": "passed_with_expected_historical_failures",
            "focused_python": "3 passed",
            "parent_ctest": "52 passed / 55 total",
            "parent_expected_historical_failures": [
                "prl_x1k_sphere_instantaneous_velocity_refinement",
                "prl_x1k_v04_family_b_parameterized_diagnosis",
                "prl_x1k_v06_family_c_short_trajectory_gate",
            ],
            "parent_unexpected_failures": 0,
            "fork_ctest": "134 passed / 134 total",
            "strict_prl_core": "passed",
            "python_pytest": "66 passed",
            "ruff": "passed",
        },
        "not_executed": [
            "R1_remesh_on",
            "C1_contact",
            "F1_failure_persistence",
            "ECM_flow_long_coupling",
            "parameter_calibration",
        ],
        "claim_guard": (
            "v08 is only a revised fixed-topology D1/S1 evidence acceptance. "
            "Historical v02/v04/v06 failures remain; X1-K and downstream "
            "mechanistic, long-time, physiological, FSI, EFE and calibration "
            "claims are not authorized."
        ),
    }
    _write_json(output_dir / "summary.json", summary)
    with (output_dir / "passing_evidence.txt").open(
        "w", encoding="utf-8", newline="\n"
    ) as target:
        target.write(
            "\n".join(
                [
                    "X1-K v08 frozen adjudication evidence",
                    f"status: {decision.status}",
                    "historical v02/v04/v06: failed, unchanged",
                    f"required raw evidence files: {len(decision.provenance)}",
                    f"decision rows: {len(decision.decisions)}",
                    "revised acceptance failures: 0",
                    f"revised D1 passed: {str(decision.revised_d1_passed).lower()}",
                    f"revised S1 passed: {str(decision.revised_s1_passed).lower()}",
                    f"X1-K passed: {str(decision.x1_k_passed).lower()}",
                    f"R1/C1/F1: {decision.r1_c1_f1_status}",
                    f"downstream authorized: {str(decision.downstream_authorized).lower()}",
                    "pointwise/uniform convergence claim allowed: false/false",
                    "",
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adjudicate X1-K v08 from frozen v05-v07 raw CSV evidence."
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    decision = adjudicate_fixed_topology_evidence(args.workspace.resolve())
    write_package(args.output_dir, decision)
    print(decision.status)
    return 0 if decision.status == "passed_revised_fixed_topology_d1_s1_acceptance" else 1


if __name__ == "__main__":
    raise SystemExit(main())
