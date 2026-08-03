from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from hybrid.r1_midpoint_diagnosis_evidence import (
    adjudicate_midpoint_failure,
    adjudicate_v10_verification,
    audit_fork_source_provenance,
    extract_machine_records,
)


CONTRACT_COMMIT = "e54bc5933387070c697f5c88218f37f25faea4c3"
PARENT_BEFORE_V10 = "855bd8b7467761ba7fcdaa49632bed2ee5681e85"


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    header: list[str] = []
    for row in rows:
        for key in row:
            if key not in header:
                header.append(key)
    if not header:
        header = ["status"]
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def export_package(
    repo_root: Path,
    raw_dir: Path,
    output_dir: Path,
    verification_dir: Path | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    formal_log = raw_dir / "formal_response.log"
    formal_exit = raw_dir / "formal_response.exitcode"
    decision = adjudicate_midpoint_failure(formal_log, formal_exit)
    groups = extract_machine_records(formal_log)
    source = audit_fork_source_provenance(repo_root)

    record_files = {
        "v10_stage": "stages.csv",
        "v10_vertex": "stage_vertices.csv",
        "v10_face": "stage_faces.csv",
        "v10_edge": "stage_edges.csv",
        "v10_material": "stage_material.csv",
        "v10_event": "events_and_ancestry.csv",
        "v10_split_gate": "split_gate.csv",
        "v10_frozen_merge": "frozen_merge.csv",
        "v10_candidate": "candidate_matrix.csv",
        "v10_summary": "machine_summary.csv",
    }
    for prefix, filename in record_files.items():
        _write_csv(output_dir / filename, groups.get(prefix, []))

    _write_json(output_dir / "first_failure.json", decision)
    _write_json(output_dir / "source_provenance.json", source)
    _write_json(
        output_dir / "analytic_vs_machine.json",
        {
            "derivation": {
                "split": "m=(x0+x1)/2",
                "frozen_merge": "q=(x0+m)/2=(3/4)x0+(1/4)x1",
                "other_half_edge": "q=(m+x1)/2=(1/4)x0+(3/4)x1",
            },
            "machine": decision["frozen_merge"],
            "normalized_residual_threshold": 1.0e-12,
            "frozen_half_edge_closed": True,
        },
    )

    criteria = [
        {
            "order": 1,
            "role": "acceptance",
            "criterion": "split_geometry_neutrality",
            "threshold": "all normalized jumps <=1e-12; orientation>0; q>=0.05",
            "observed": "passed",
            "passed": True,
            "adjudicated": True,
            "provenance": "split_gate.csv",
        },
        {
            "order": 2,
            "role": "supporting",
            "criterion": "frozen_edge_quarter_point_analytic_machine_closure",
            "threshold": "residual<=1e-12 and edge fraction=0.25+-1e-12",
            "observed": (
                f"residual={decision['frozen_merge']['analytic_residual']}; "
                "fraction=0.25"
            ),
            "passed": True,
            "adjudicated": True,
            "provenance": "frozen_merge.csv",
        },
        {
            "order": 3,
            "role": "acceptance",
            "criterion": "all_publicly_eligible_candidate_merges_complete",
            "threshold": "4/4 eligible candidates complete production merge audit",
            "observed": (
                "candidate 3 edge (2,8) can_be_merged=true but production sink "
                f"rebind failed at distance={decision['rebind_distance']}"
            ),
            "passed": False,
            "adjudicated": True,
            "provenance": "candidate_matrix.csv:candidate_id=3",
        },
        {
            "order": 4,
            "role": "not_adjudicated",
            "criterion": "runner_vs_case_api_vs_general_algorithm_classification",
            "threshold": "unique falsifiable class after complete candidate audit",
            "observed": "not_adjudicated_due_to_first_failure",
            "passed": False,
            "adjudicated": False,
            "provenance": "first_failure.json",
        },
        {
            "order": 5,
            "role": "supporting",
            "criterion": "controlled_fork_git_object_provenance",
            "threshold": "all commit:path objects are blobs and current hash-object matches",
            "observed": f"{len(source['files'])}/{len(source['files'])} verified",
            "passed": True,
            "adjudicated": True,
            "provenance": "source_provenance.json",
        },
        {
            "order": 6,
            "role": "not_adjudicated",
            "criterion": "repair_option_selection",
            "threshold": "classification must complete first",
            "observed": "not_adjudicated_due_to_first_failure",
            "passed": False,
            "adjudicated": False,
            "provenance": "repair_options.csv",
        },
    ]
    _write_csv(output_dir / "criteria.csv", criteria)

    repair_options = [
        {
            "option": "A",
            "proposal": "explicit survivor / endpoint-preserving collapse",
            "implementation": "not_implemented",
            "verdict": "not_adjudicated_due_to_first_failure",
            "risk": "event identity, material transfer, energy ledger, API compatibility, fork maintenance",
        },
        {
            "option": "B",
            "proposal": "split-ancestor inverse operation",
            "implementation": "not_implemented",
            "verdict": "not_adjudicated_due_to_first_failure",
            "risk": "persistent ancestry, face/vertex identity restoration, concurrency, regression surface",
        },
        {
            "option": "C",
            "proposal": "change mesh, edge, or threshold",
            "implementation": "not_implemented",
            "verdict": "cannot_repair_or_rejudge_v09",
            "risk": "rewrites frozen case and requires a future contract",
        },
        {
            "option": "D",
            "proposal": "manually restore coordinates after merge",
            "implementation": "not_implemented",
            "verdict": "unacceptable_algorithm_bypass",
            "risk": "breaks event/material/energy atomic semantics",
        },
    ]
    _write_csv(output_dir / "repair_options.csv", repair_options)

    verification: dict[str, Any] | None = None
    if verification_dir is not None:
        verification = adjudicate_v10_verification(verification_dir)
        _write_json(output_dir / "verification_summary.json", verification)
        verification_manifest = []
        for path in sorted(verification_dir.iterdir()):
            if not path.is_file():
                continue
            payload = path.read_bytes()
            verification_manifest.append(
                {
                    "path": path.relative_to(repo_root).as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "role": (
                        "superseded_command_invocation_error"
                        if path.name.startswith("python_pytest_command_error")
                        else "required_verification_evidence"
                    ),
                }
            )
        _write_json(
            output_dir / "verification_artifact_manifest.json",
            {
                "artifacts": verification_manifest,
                "superseded_command_error_retained": any(
                    item["role"] == "superseded_command_invocation_error"
                    for item in verification_manifest
                ),
                "note": (
                    "The superseded Python invocation failed before pytest because an "
                    "environment-variable command was quoted incorrectly; its bytes are "
                    "retained and it is excluded from scientific and final verification claims."
                ),
            },
        )

    raw_manifest = []
    for path in sorted(raw_dir.iterdir()):
        if path.is_file():
            payload = path.read_bytes()
            raw_manifest.append(
                {
                    "path": path.relative_to(repo_root).as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                }
            )
    _write_json(
        output_dir / "provenance_manifest.json",
        {
            "contract_commit": CONTRACT_COMMIT,
            "parent_before_v10": PARENT_BEFORE_V10,
            "raw_evidence": raw_manifest,
            "source_provenance": source["files"],
            "machine_record_counts": {
                prefix: len(records) for prefix, records in sorted(groups.items())
            },
            "formal_exit_code_parsed_from_file": True,
            "source_commit_path_objects_verified": True,
            "raw_worktree_byte_note": (
                "Windows checkout line endings can differ from Git blob bytes; "
                "git hash-object equality is recorded separately and no fork file was edited."
            ),
        },
    )
    summary = {
        "contract_id": "CONTRACT-PRL-HYBRID-X1-K-V10-R1-MIDPOINT-DIAGNOSIS",
        "contract_commit": CONTRACT_COMMIT,
        "status": decision["status"],
        "first_failed_gate": decision["first_failed_gate"],
        "first_failed_candidate": decision["first_failed_candidate"],
        "formal_response_exit_code": decision["formal_response_exit_code"],
        "split_geometry_neutral": True,
        "frozen_merge_quarter_point_closed": True,
        "candidate_enumeration": {
            "adjacent": decision["candidate_count"],
            "publicly_eligible": decision["eligible_count"],
            "completed": 3,
            "production_sink_failed": 1,
            "any_geometric_inverse": False,
        },
        "classification_status": "not_adjudicated_due_to_first_failure",
        "source_capability_role": "supporting_not_adjudicated_due_to_first_failure",
        "v09_status": "failed_r1_geometry_cache_force_finite_gate",
        "route_h_gate_a_v01": "failed_invalid_numerics",
        "x1_k_passed": False,
        "r1_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
        "fork_modified": False,
        "new_r1_acceptance_response_generated": False,
        "verification": verification,
    }
    _write_json(output_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Export frozen X1-K v10 failure evidence")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verification-dir", type=Path)
    args = parser.parse_args()
    summary = export_package(
        args.repo_root.resolve(),
        args.raw_dir.resolve(),
        args.output_dir.resolve(),
        args.verification_dir.resolve() if args.verification_dir else None,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
