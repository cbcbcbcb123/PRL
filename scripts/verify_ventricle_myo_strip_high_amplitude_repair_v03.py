"""Independent combined verifier for the final v03 high-amplitude repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_ventricle_myo_strip_high_amplitude_v01 as base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_repair_v03_20260913"
V01 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_v01_20260913"
V02 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_repair_v02_20260913"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    base.CASE_SPECS = (
        ("CENTER_EPS100", "CENTER", 0.10, "reference", base.CENTER_REFERENCE, 3000),
        ("CENTER_EPS150", "CENTER", 0.15, "new", None, 6000),
        ("CENTER_EPS200", "CENTER", 0.20, "new", None, 7000),
        ("SYNC_EPS100", "SYNC", 0.10, "reference", base.SYNC_REFERENCE, 2000),
        ("SYNC_EPS150", "SYNC", 0.15, "new", None, 3000),
        ("SYNC_EPS200", "SYNC", 0.20, "new", None, 3000),
    )
    mapped = {
        "CENTER_EPS100": base.CENTER_REFERENCE,
        "CENTER_EPS150": V02 / "raw" / "CENTER_EPS150",
        "CENTER_EPS200": output / "raw" / "CENTER_EPS200",
        "SYNC_EPS100": base.SYNC_REFERENCE,
        "SYNC_EPS150": V01 / "raw" / "SYNC_EPS150",
        "SYNC_EPS200": V01 / "raw" / "SYNC_EPS200",
    }

    def mapped_directory(_output: Path, case: str, _source: str, _reference: Path | None) -> Path:
        return mapped[case]

    base.case_directory = mapped_directory
    verdict = base.verify(output)
    verdict["version"] = "v03_final_targeted_convergence_repair"
    verdict["preserved_predecessors"] = [
        str((V01 / "verdict.json").relative_to(PROJECT_ROOT)).replace("\\", "/"),
        str((V02 / "verdict.json").relative_to(PROJECT_ROOT)).replace("\\", "/"),
    ]
    (output / "verdict.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if "case_values" in verdict:
        base.write_metrics(output, verdict)
    print(json.dumps({"status": verdict["status"], "failed_gates": verdict.get("failed_gates", [])}, ensure_ascii=False))
    return 0 if verdict["status"] == "passed_synthetic_isometric_high_amplitude_response" else 1


if __name__ == "__main__":
    raise SystemExit(main())
