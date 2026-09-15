"""Render the final v03 high-amplitude repair evidence package."""

from __future__ import annotations

from pathlib import Path

import render_ventricle_myo_strip_high_amplitude_v01 as base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
V01 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_v01_20260913"
V02 = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_high_amp_deformability_repair_v02_20260913"


def main() -> int:
    def mapped_directory(output: Path, case: str, reference: Path | None) -> Path:
        mapping = {
            "CENTER_EPS100": base.CENTER_REFERENCE,
            "CENTER_EPS150": V02 / "raw" / "CENTER_EPS150",
            "CENTER_EPS200": output / "raw" / "CENTER_EPS200",
            "SYNC_EPS100": base.SYNC_REFERENCE,
            "SYNC_EPS150": V01 / "raw" / "SYNC_EPS150",
            "SYNC_EPS200": V01 / "raw" / "SYNC_EPS200",
        }
        return mapping[case]

    base.case_directory = mapped_directory
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
