"""Independent verifier for Z1-BIOFORM-MYO-A v02."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ventricle_bioform_myo_common import (
    CONDITION_MATRIX,
    EQUIVALENT_RADIUS,
    PROJECT_ROOT,
    condition_metrics,
    final_points,
    relative_difference,
    sha256_file,
    symmetric_chamfer_rms,
    write_json,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_a_v02_20260913"


def gate(name: str, value: Any, threshold: str, passed: bool, group: str) -> dict[str, Any]:
    return {"name": name, "value": value, "threshold": threshold, "passed": bool(passed), "group": group}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    verification_dir = output / "verification"
    if verification_dir.exists() or (output / "summary.json").exists():
        raise SystemExit("create-only verification output already exists")
    preregistration = json.loads((output / "preregistration.json").read_text(encoding="utf-8"))
    ledger = json.loads((output / "run_ledger.json").read_text(encoding="utf-8"))
    selection = json.loads((output / "pilot_selection.json").read_text(encoding="utf-8"))
    verification_dir.mkdir()

    hash_checks = []
    stored_hashes = json.loads((output / "source_hashes.json").read_text(encoding="utf-8"))
    for relative_path, expected_hash in stored_hashes.items():
        if relative_path == "git_status_snapshot.txt":
            continue
        path = PROJECT_ROOT / relative_path
        current_hash = sha256_file(path) if path.is_file() else None
        hash_checks.append(
            {
                "path": relative_path,
                "expected_sha256": expected_hash,
                "current_sha256": current_hash,
                "match": current_hash == expected_hash,
            }
        )
    source_hashes_match = all(item["match"] for item in hash_checks)

    expected_ids = [item["id"] for item in CONDITION_MATRIX]
    ledger_records = {item.get("id"): item for item in ledger.get("formal", [])}
    raw_complete = ledger.get("formal_attempt_consumed") is True and all(
        condition_id in ledger_records and ledger_records[condition_id].get("status") == "completed"
        for condition_id in expected_ids
    )
    metrics: dict[str, dict[str, Any]] = {}
    if raw_complete:
        for condition_id in expected_ids:
            metrics[condition_id] = condition_metrics(output / "raw" / condition_id)

    gates: list[dict[str, Any]] = [
        gate("source_hashes_match_preregistration", source_hashes_match, "true", source_hashes_match, "prerequisite"),
        gate("formal_matrix_complete", raw_complete, "8/8 completed", raw_complete, "prerequisite"),
    ]
    if raw_complete:
        for condition_id in expected_ids:
            item = metrics[condition_id]
            kernel = item["kernel"]
            gates.extend(
                [
                    gate(f"{condition_id}:finite_saved_states", item["all_saved_states_finite"], "true", item["all_saved_states_finite"], "common_numerical"),
                    gate(f"{condition_id}:sphere_topology", item["all_saved_states_sphere_topology"], "true", item["all_saved_states_sphere_topology"], "common_numerical"),
                    gate(f"{condition_id}:max_volume_error", kernel["max_volume_relative_error"], "<=0.02", kernel["max_volume_relative_error"] <= 0.02, "common_numerical"),
                    gate(f"{condition_id}:min_saved_angle_deg", item["minimum_saved_triangle_angle_deg"], ">=15", item["minimum_saved_triangle_angle_deg"] >= 15.0, "common_numerical"),
                    gate(f"{condition_id}:cyt_force_residual", kernel["max_cytoskeleton_relative_force_residual"], "<=1e-10", kernel["max_cytoskeleton_relative_force_residual"] <= 1e-10, "common_numerical"),
                    gate(f"{condition_id}:cyt_moment_residual", kernel["max_cytoskeleton_relative_moment_residual"], "<=1e-10", kernel["max_cytoskeleton_relative_moment_residual"] <= 1e-10, "common_numerical"),
                    gate(f"{condition_id}:work_residual", kernel["max_work_dissipation_relative_residual"], "<=1e-12", kernel["max_work_dissipation_relative_residual"] <= 1e-12, "common_numerical"),
                ]
            )

        main_metrics = metrics["FULL_M320_DT020"]
        ablation = metrics["ABLATION_M320_DT020"]
        perturbed = metrics["PERTURBED_M320_DT020"]
        rotated = metrics["ROTATED37_M320_DT020"]
        fine_mesh = metrics["FULL_M1280_DT020"]
        fine_step = metrics["FULL_M320_DT010"]
        main_final = main_metrics["final"]
        ablation_final = ablation["final"]
        perturbed_final = perturbed["final"]
        rotated_final = rotated["final"]
        mesh_e_difference = relative_difference(main_final["E_pq"], fine_mesh["final"]["E_pq"])
        mesh_f_difference = relative_difference(main_final["F_qr"], fine_mesh["final"]["F_qr"])
        step_e_difference = relative_difference(main_final["E_pq"], fine_step["final"]["E_pq"])
        step_f_difference = relative_difference(main_final["F_qr"], fine_step["final"]["F_qr"])
        perturb_e_difference = relative_difference(main_final["E_pq"], perturbed_final["E_pq"])
        perturb_f_difference = relative_difference(main_final["F_qr"], perturbed_final["F_qr"])
        rotation_e_difference = relative_difference(main_final["E_pq"], rotated_final["E_pq"])
        rotation_f_difference = relative_difference(main_final["F_qr"], rotated_final["F_qr"])
        chamfer = symmetric_chamfer_rms(
            final_points(output / "raw" / "FULL_M320_DT020"),
            final_points(output / "raw" / "ROTATED37_M320_DT020", inverse_rotation_degrees=37.0),
        )
        normalized_chamfer = chamfer / EQUIVALENT_RADIUS
        gates.extend(
            [
                gate("main:final_to_peak_force_ratio", main_metrics["kernel"]["final_to_peak_free_force_ratio"], "<=0.05", main_metrics["kernel"]["final_to_peak_free_force_ratio"] <= 0.05, "common_numerical"),
                gate("main:E_pq", main_final["E_pq"], ">=1.20", main_final["E_pq"] >= 1.20, "mechanism"),
                gate("main:F_qr", main_final["F_qr"], ">=1.15", main_final["F_qr"] >= 1.15, "mechanism"),
                gate("ablation:E_pq", ablation_final["E_pq"], "<=1.05", ablation_final["E_pq"] <= 1.05, "mechanism"),
                gate("ablation:F_qr", ablation_final["F_qr"], "<=1.05", ablation_final["F_qr"] <= 1.05, "mechanism"),
                gate("main_minus_ablation:E_pq", main_final["E_pq"] - ablation_final["E_pq"], ">=0.15", main_final["E_pq"] - ablation_final["E_pq"] >= 0.15, "mechanism"),
                gate("main_minus_ablation:F_qr", main_final["F_qr"] - ablation_final["F_qr"], ">=0.10", main_final["F_qr"] - ablation_final["F_qr"] >= 0.10, "mechanism"),
                gate("perturbation:E_pq_relative_difference", perturb_e_difference, "<=0.05", perturb_e_difference <= 0.05, "mechanism"),
                gate("perturbation:F_qr_relative_difference", perturb_f_difference, "<=0.05", perturb_f_difference <= 0.05, "mechanism"),
                gate("rotation:E_pq_relative_difference", rotation_e_difference, "<=0.02", rotation_e_difference <= 0.02, "mechanism"),
                gate("rotation:F_qr_relative_difference", rotation_f_difference, "<=0.02", rotation_f_difference <= 0.02, "mechanism"),
                gate("rotation:inverse_chamfer_over_radius", normalized_chamfer, "<=0.02", normalized_chamfer <= 0.02, "mechanism"),
                gate("rotation:major_axis_angle_deg", rotated_final["major_axis_angle_to_p_deg"], "<=5", rotated_final["major_axis_angle_to_p_deg"] <= 5.0, "mechanism"),
                gate("mesh_320_to_1280:E_pq_relative_difference", mesh_e_difference, "<=0.05", mesh_e_difference <= 0.05, "discretization"),
                gate("mesh_320_to_1280:F_qr_relative_difference", mesh_f_difference, "<=0.05", mesh_f_difference <= 0.05, "discretization"),
                gate("dt_020_to_010:E_pq_relative_difference", step_e_difference, "<=0.02", step_e_difference <= 0.02, "discretization"),
                gate("dt_020_to_010:F_qr_relative_difference", step_f_difference, "<=0.02", step_f_difference <= 0.02, "discretization"),
            ]
        )

    prerequisite_pass = all(item["passed"] for item in gates if item["group"] == "prerequisite")
    common_pass = prerequisite_pass and all(item["passed"] for item in gates if item["group"] == "common_numerical")
    mechanism_pass = common_pass and all(item["passed"] for item in gates if item["group"] == "mechanism")
    discretization_pass = common_pass and all(item["passed"] for item in gates if item["group"] == "discretization")
    if not prerequisite_pass:
        verdict = "not_resolved"
    elif not common_pass:
        verdict = "failed_numerical"
    elif mechanism_pass and discretization_pass:
        verdict = "passed_synthetic_mechanism"
    else:
        verdict = "failed_mechanism"

    payload = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-A",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "biological_validation_status": "blocked_data",
        "parent_Z1_status": "blocked",
        "selected_stress_amplitude": selection.get("selected_stress_amplitude"),
        "source_hashes_match": source_hashes_match,
        "hash_checks": hash_checks,
        "gates": gates,
        "condition_metrics": metrics,
        "gate_group_status": {
            "prerequisite": prerequisite_pass,
            "common_numerical": common_pass,
            "mechanism": mechanism_pass,
            "discretization": discretization_pass,
        },
    }
    write_json(verification_dir / "independent_verification.json", payload)
    with (verification_dir / "condition_metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["condition", "E_pq", "F_qr", "max_volume_error", "min_saved_angle_deg", "force_ratio", "final_faces"])
        for condition_id in expected_ids:
            if condition_id not in metrics:
                continue
            item = metrics[condition_id]
            writer.writerow(
                [
                    condition_id,
                    item["final"]["E_pq"],
                    item["final"]["F_qr"],
                    item["kernel"]["max_volume_relative_error"],
                    item["minimum_saved_triangle_angle_deg"],
                    item["kernel"]["final_to_peak_free_force_ratio"],
                    item["final"]["face_count"],
                ]
            )

    failed_gates = [item for item in gates if not item["passed"]]
    summary = {
        "schema_version": 1,
        "stage": "Z1-BIOFORM-MYO-A",
        "status": verdict,
        "scientific_scope": "single_free_myocardial_cell_synthetic_intrinsic_shape_mechanism",
        "biological_validation_status": "blocked_data",
        "parent_Z1_status": "blocked",
        "formal_matrix_completed": raw_complete,
        "selected_stress_amplitude": selection.get("selected_stress_amplitude"),
        "failed_gate_count": len(failed_gates),
        "failed_gates": failed_gates,
        "main_final": metrics.get("FULL_M320_DT020", {}).get("final"),
        "evidence": {
            "verification": "verification/independent_verification.json",
            "condition_metrics": "verification/condition_metrics.csv",
            "run_ledger": "run_ledger.json",
        },
    }
    write_json(output / "summary.json", summary)
    report_lines = [
        "# Z1-BIOFORM-MYO-A v02 独立核验报告",
        "",
        f"- 合成机制裁决：`{verdict}`",
        "- 生物学验证：`blocked_data`",
        "- 父 Z1：`blocked`（本阶段不会提升父阶段）",
        f"- 正式矩阵：{'8/8 completed' if raw_complete else 'incomplete'}",
        f"- 失败门数：{len(failed_gates)}",
    ]
    if metrics.get("FULL_M320_DT020"):
        main_final = metrics["FULL_M320_DT020"]["final"]
        report_lines.extend(
            [
                "",
                "## 主轨迹末态",
                "",
                f"- `E_pq={main_final['E_pq']:.6f}`",
                f"- `F_qr={main_final['F_qr']:.6f}`",
                f"- 轴向外包络：`{main_final['axis_extents']}`",
            ]
        )
    report_lines.extend(["", "## 未通过门", ""])
    if failed_gates:
        report_lines.extend(f"- `{item['name']}`: {item['value']}，要求 {item['threshold']}" for item in failed_gates)
    else:
        report_lines.append("- 无。所有冻结的数值、机制与离散门均通过。")
    report_lines.extend(
        [
            "",
            "## 主张边界",
            "",
            "该结果只回答合成的单细胞内禀形态机制是否数值可行。没有同期三维实验轴长数据，因此不得称为真实心肌形态已验证；也不得据此宣称心内膜、ECM 或三层组织已完成。",
        ]
    )
    (output / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if verdict == "passed_synthetic_mechanism" else 2


if __name__ == "__main__":
    sys.exit(main())
