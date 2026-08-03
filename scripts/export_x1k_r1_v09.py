from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from hybrid.r1_remesh_robustness_evidence import (
    adjudicate_r1_focused_failure,
)
from hybrid.r1_verification_evidence import adjudicate_r1_verification_evidence


CONTRACT_COMMIT = "f7701d59ce3e1c94737e3b0a276205ed70fae6f8"
PARENT_BEFORE_R1 = "3d0a8217e869213e34223d7206f4588e7b6e9aca"
CELL_ENGINE_COMMIT = "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a"


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _records_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        _write_csv(path, ["status"], [])
        return
    header = list(records[0])
    if any(set(record) != set(header) for record in records):
        raise RuntimeError(f"record schemas do not close for {path.name}")
    _write_csv(path, header, [[record[key] for key in header] for record in records])


def write_failure_package(output_dir: Path, evidence_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    decision = adjudicate_r1_focused_failure(evidence_dir)
    parsed = decision.pop("parsed")
    config = parsed["config"]
    samples = parsed["samples"]
    events = parsed["events"]
    transfers = parsed["transfers"]
    ledger = parsed["ledger"]
    gate = parsed["gate"]
    diagnostic_qoi = parsed["diagnostic_qoi"]
    last = samples["remesh"][-1]

    frozen_thresholds = {
        "maximum_qoi_difference": 2.0e-3,
        "maximum_remesh_defect": 1.0e-12,
        "minimum_initial_active_energy_strict": 1.0e-2,
        "minimum_fiber_alignment": 1.0 - 1.0e-12,
        "maximum_rebind_error": 1.0e-12,
        "minimum_oriented_face_alignment_strict": 0.0,
        "minimum_triangle_quality": 0.05,
        "minimum_face_area_ratio": 1.0e-4,
        "maximum_normalized_cache_residual": 1.0e-12,
        "maximum_normalized_surface_centroid_drift": 1.0e-2,
        "volume_ratio_interval": [0.5, 1.5],
        "maximum_force_buffer_l2_norm": 1.0e-12,
        "maximum_normalized_positive_energy_residual": 5.0e-3,
    }
    config_payload = {
        "contract_commit": CONTRACT_COMMIT,
        "parent_before_r1": PARENT_BEFORE_R1,
        "cell_engine_commit": CELL_ENGINE_COMMIT,
        "time_step": float(config["time_step"]),
        "step_count": int(config["step_count"]),
        "terminal_time": float(config["time_step"]) * int(config["step_count"]),
        "split_step": int(config["split_step"]),
        "merge_step": int(config["merge_step"]),
        "swap_count": 0,
        "qoi_contraction_unit_id": int(config["qoi_unit"]),
        "damping_measure": config["damping_measure"],
        "damping_coefficient": float(config["damping_coefficient"]),
        "adaptive_remesh": False,
        "adaptive_retry": False,
        "configuration_hash": config["configuration_hash"],
        "fixed_initial_state_hash": config["fixed_initial_state_hash"],
        "remesh_initial_state_hash": config["remesh_initial_state_hash"],
        "characteristic_length": float(config["characteristic_length"]),
        "initial_axis_length": float(config["initial_axis_length"]),
        "initial_active_energy": float(config["initial_active_energy"]),
        "thresholds": frozen_thresholds,
    }
    _write_json(output_dir / "config.json", config_payload)
    _records_csv(output_dir / "fixed_steps.csv", samples["fixed"])
    _records_csv(output_dir / "remesh_steps.csv", samples["remesh"])
    _records_csv(output_dir / "events.csv", events)
    _records_csv(output_dir / "material_transfer.csv", transfers)
    _records_csv(output_dir / "remesh_energy_ledger.csv", [ledger])
    _records_csv(output_dir / "qoi_comparison.csv", diagnostic_qoi)

    criteria = [
        [
            "acceptance",
            "remesh_step_3",
            "normalized_surface_centroid_drift",
            "<=",
            "0.01",
            last["normalized_centroid_drift"],
            "false",
            "true",
            "remesh_steps.csv:step=3",
            "first hard gate failure",
        ],
        [
            "control",
            "remesh_step_3",
            "finite_orientation_quality_face_cache_volume_force",
            "all frozen bounds",
            "see config.json",
            json.dumps(
                {
                    key: value
                    for key, value in parsed["safety_checks"].items()
                    if key != "normalized_surface_centroid_drift"
                },
                sort_keys=True,
            ),
            "true",
            "true",
            "remesh_steps.csv:step=3",
            "all peer safety checks passed",
        ],
        [
            "not_adjudicated",
            "R1_QoI",
            "fixed_vs_remesh_four_QoI",
            "<=",
            "0.002",
            "diagnostic rows only",
            "false",
            "false",
            "qoi_comparison.csv",
            "not adjudicated after first safety failure",
        ],
        [
            "not_adjudicated",
            "J1",
            "real_split_merge_energy_cycle",
            "frozen J1 thresholds",
            "see config.json",
            "raw ledger preserved",
            "false",
            "false",
            "remesh_energy_ledger.csv",
            "not adjudicated after first safety failure",
        ],
    ]
    _write_csv(
        output_dir / "criteria.csv",
        [
            "role",
            "scope",
            "criterion",
            "operator",
            "threshold",
            "observed",
            "passed",
            "adjudicated",
            "provenance",
            "notes",
        ],
        criteria,
    )

    qoi_maxima = {
        key: max(float(row[key]) for row in diagnostic_qoi)
        for key in (
            "normalized_axis_difference",
            "area_ratio_difference",
            "volume_ratio_difference",
            "normalized_active_energy_difference",
        )
    }
    first_failure = {
        **decision,
        "failure_reason": gate["failure_reason"],
        "peer_safety_checks": parsed["safety_checks"],
        "step_3_mesh": {
            "revision": int(last["revision"]),
            "vertex_count": int(last["vertex_count"]),
            "face_count": int(last["face_count"]),
            "surface_area_ratio": float(last["area_ratio"]),
            "volume_ratio": float(last["volume_ratio"]),
            "normalized_surface_centroid_drift": float(
                last["normalized_centroid_drift"]
            ),
        },
    }
    _write_json(output_dir / "first_failure.json", first_failure)
    _write_json(
        output_dir / "provenance_manifest.json",
        {
            "contract_commit": CONTRACT_COMMIT,
            "source_evidence": parsed["manifest"],
            "machine_record_counts": {
                "fixed_samples": len(samples["fixed"]),
                "remesh_samples": len(samples["remesh"]),
                "events": len(events),
                "material_transfers": len(transfers),
                "ledger": 1,
                "adjudicated_qoi_rows": 0,
                "diagnostic_qoi_rows": len(diagnostic_qoi),
            },
            "schema_and_key_closure_verified": True,
            "finite_values_verified": True,
            "exit_codes_parsed_from_files": True,
        },
    )
    verification = adjudicate_r1_verification_evidence(evidence_dir)
    _write_json(output_dir / "verification_summary.json", verification)
    summary = {
        "contract_id": "CONTRACT-PRL-HYBRID-X1-K-V09-R1",
        "contract_commit": CONTRACT_COMMIT,
        "status": decision["status"],
        "first_failure": first_failure,
        "focused_build_exit_code": next(
            item["exit_code"]
            for item in parsed["manifest"]
            if item["path"].endswith("focused_build.exitcode")
        ),
        "focused_response_exit_code": next(
            item["exit_code"]
            for item in parsed["manifest"]
            if item["path"].endswith("focused_response.exitcode")
        ),
        "formal_response_exit_code": next(
            item["exit_code"]
            for item in parsed["manifest"]
            if item["path"].endswith("formal_response.exitcode")
        ),
        "focused_regression_exit_code": next(
            item["exit_code"]
            for item in parsed["manifest"]
            if item["path"].endswith("focused_regression.exitcode")
        ),
        "verification": verification,
        "fixed_trajectory_status": "completed_8_steps",
        "remesh_trajectory_status": "stopped_at_first_hard_gate_step_3",
        "real_events": ["edge_split:0->1@step2", "edge_merge:1->2@step3"],
        "qoi_gate_status": decision["qoi_gate_status"],
        "j1_gate_status": decision["j1_gate_status"],
        "diagnostic_only_qoi_maxima": qoi_maxima,
        "historical_evidence_status": {
            "route_h_gate_a_v01": "failed_invalid_numerics",
            "x1_k_v02_d1": "failed_historical_unchanged",
            "x1_k_v04_family_b": "failed_historical_unchanged",
            "x1_k_v06_mean_radius": "failed_historical_unchanged",
            "x1_k_v08": "failed_adjudicator_contract_incomplete",
            "x1_k_v08r1": (
                "passed_revised_fixed_topology_d1_s1_acceptance_"
                "after_adjudicator_repair"
            ),
        },
        "x1_k_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
        "claim_guard": (
            "v09 is a correctly frozen R1 scientific failure. It does not "
            "authorize C1, F1, ECM/flow coupling, calibration, long-time, "
            "physiological, FSI, EFE, or developmental-mechanism claims."
        ),
    }
    _write_json(output_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze the X1-K v09 R1 failure.")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = write_failure_package(args.output_dir, args.evidence_dir)
    print(summary["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
