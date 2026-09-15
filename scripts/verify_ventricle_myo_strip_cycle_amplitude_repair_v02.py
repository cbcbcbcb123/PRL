"""Composite verifier using only the repaired CENTER 10% trajectory from v02."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import verify_ventricle_myo_strip_cycle_amplitude_v01 as base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_repair_v02_20260913"
PRIMARY_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_v01_20260913"


def write_metrics(path: Path, result: dict[str, Any]) -> None:
    columns = (
        "case", "pattern", "contraction_strain", "source", "active_increment",
        "peak_p_strain", "peak_q_strain", "peak_r_strain", "recovery_fraction",
        "max_saved_free_force", "max_saved_volume_error", "min_saved_angle",
        "peak_contraction_traction_p95", "peak_adhesion_traction_p95",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for case, metadata in result["case_metadata"].items():
            values = result["case_values"][case]
            writer.writerow(
                {
                    "case": case,
                    "pattern": metadata["pattern"],
                    "contraction_strain": metadata["strain"],
                    "source": "v02_targeted_repair" if case == "CENTER_EPS100" else metadata["source"],
                    "active_increment": values["active_increment"],
                    "peak_p_strain": values["peak_p_strain"],
                    "peak_q_strain": values["peak_q_strain"],
                    "peak_r_strain": values["peak_r_strain"],
                    "recovery_fraction": values["recovery_fraction"],
                    "max_saved_free_force": values["max_saved_free_force"],
                    "max_saved_volume_error": values["max_saved_volume_error"],
                    "min_saved_angle": values["min_saved_angle"],
                    "peak_contraction_traction_p95": values["peak_contraction_traction_p95"],
                    "peak_adhesion_traction_p95": values["peak_adhesion_traction_p95"],
                }
            )


def verify(output: Path) -> dict[str, Any]:
    repaired_directory = output / "raw" / "CENTER_EPS100"
    original_case_directory = base.case_directory
    original_summarize_case = base.summarize_case

    def composite_case_directory(_output: Path, case: str, pattern: str, source: str) -> Path:
        if case == "CENTER_EPS100":
            return repaired_directory
        return original_case_directory(PRIMARY_OUTPUT, case, pattern, source)

    def composite_summarize_case(directory: Path, expected_pattern: str, expected_strain: float) -> dict[str, Any]:
        summary = original_summarize_case(directory, expected_pattern, expected_strain)
        if directory.resolve() == repaired_directory.resolve():
            kernel = base.read_json(directory / "kernel_metrics.json")
            summary["kernel_metadata_ok"] = (
                kernel.get("condition") == "CENTER"
                and abs(float(kernel.get("contraction_strain", -1.0)) - 0.10) <= 1.0e-15
                and kernel.get("snapshot_count") == 9
                and kernel.get("requested_step") == 0.02
                and kernel.get("settle_steps") == 1000
                and kernel.get("ramp_steps_per_segment") == 50
                and kernel.get("hold_steps_per_segment") == 3000
            )
        return summary

    try:
        base.case_directory = composite_case_directory
        base.summarize_case = composite_summarize_case
        result = base.verify(output)
    finally:
        base.case_directory = original_case_directory
        base.summarize_case = original_summarize_case

    result["composite_version"] = "v02_targeted_convergence_repair"
    result["primary_failed_verdict"] = str((PRIMARY_OUTPUT / "verdict.json").relative_to(PROJECT_ROOT)).replace("\\", "/")
    result["repaired_case"] = {
        "case": "CENTER_EPS100",
        "directory": str(repaired_directory.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "hold_steps_per_segment": 3000,
        "thresholds_changed": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    result = verify(output)
    (output / "verdict.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if "case_values" in result:
        write_metrics(output / "metrics.csv", result)
    print(json.dumps({"status": result["status"], "failed_gates": result.get("failed_gates", [])}, ensure_ascii=False))
    return 0 if result["status"] == "passed_synthetic_activation_count_amplitude_response" else 1


if __name__ == "__main__":
    raise SystemExit(main())
