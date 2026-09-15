"""Render the v02 composite matrix with only CENTER 10% replaced by its repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import render_ventricle_myo_strip_cycle_amplitude_v01 as base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_repair_v02_20260913"
PRIMARY_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_v01_20260913"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    directory = output / "figures"
    if directory.exists():
        raise SystemExit(f"create-only figures directory already exists: {directory}")
    directory.mkdir()

    cases = {}
    for case, pattern, strain, source in base.CASE_SPECS:
        source_output = output if case == "CENTER_EPS100" else PRIMARY_OUTPUT
        cases[case] = base.load_case(source_output, case, pattern, strain, source)
        if case == "CENTER_EPS100":
            cases[case]["source"] = "v02_targeted_repair"

    limits = base.coordinate_limits(cases)
    base.render_structure(directory)
    base.render_peak_deformation(cases, directory, limits)
    base.render_peak_tractions(cases, directory, limits)
    base.render_cycle_response(cases, directory)
    base.render_amplitude_response(output, directory)
    base.render_animation(
        cases, directory, limits, "displacement_magnitude", "viridis",
        "displacement from phase 0 (model length units)", "deformation_cycle",
    )
    base.render_animation(
        cases, directory, limits, "contraction_traction", "inferno",
        "intracellular contraction traction (model force / area)", "active_traction_cycle",
    )
    base.render_animation(
        cases, directory, limits, "adhesion_traction", "YlOrBr",
        "junction adhesion traction (model force / area)", "junction_traction_cycle",
    )
    base.write_summary(output)
    base.write_index(output)
    visual_qa = {
        "automated_asset_generation": "passed",
        "static_png_svg_pairs": 5,
        "true_snapshot_gif_count": 3,
        "gif_frame_count_each": 9,
        "shared_scale_policy": "one scale per field across all six cases and all animation frames",
        "center_eps100_source": "v02_targeted_repair_hold3000",
        "manual_visual_qa": "not_run",
        "offline_index": "index.html",
    }
    (output / "visual_qa.json").write_text(json.dumps(visual_qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        path.name: {"sha256": base.sha256(path), "bytes": path.stat().st_size}
        for path in sorted(directory.iterdir()) if path.is_file()
    }
    (output / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rendered": sorted(manifest), "status": "completed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
