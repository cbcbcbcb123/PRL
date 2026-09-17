"""Independent consistency checks for the PRL F1-Seg-A result package.

This verifier does not import segmentation code.  It recomputes configuration
hashes, pixel areas, label-table completeness, cross-fish summary ratios, image
readability, and the storage cap from saved artifacts.  A passing verdict means
the engineering evidence package is internally consistent; it does not supply
human instance truth or validate cell identities.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


EXPECTED_SCHEMA = "prl.f1seg.surface_cell_candidate.v1"
SAMPLES = ("fish3", "fish4", "fish5")
PIXEL_AREA_UM2 = 0.2071606**2
RESULT_CAP_BYTES = 64 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    return parser.parse_args()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def add_check(checks: dict[str, dict[str, Any]], name: str, passed: bool, detail: Any) -> None:
    checks[name] = {"status": "passed" if passed else "failed", "detail": detail}


def main() -> int:
    args = parse_args()
    result = args.result.resolve()
    checks: dict[str, dict[str, Any]] = {}

    frozen = json.loads((result / "frozen_config.json").read_text(encoding="utf-8"))
    summary = json.loads((result / "run_summary.json").read_text(encoding="utf-8"))
    calculated_hash = canonical_hash(frozen["configuration"])
    expected_hash = str(frozen["configuration_sha256"])
    add_check(
        checks,
        "frozen_configuration_hash",
        calculated_hash == expected_hash == summary["configuration_sha256"],
        {"calculated": calculated_hash, "recorded": expected_hash},
    )
    add_check(
        checks,
        "frozen_development_design",
        frozen["development_sample"] == "fish4"
        and frozen["holdout_samples"] == ["fish3", "fish5"]
        and frozen["configuration_count_evaluated"] == 12,
        {
            "development": frozen["development_sample"],
            "holdouts": frozen["holdout_samples"],
            "configuration_count": frozen["configuration_count_evaluated"],
        },
    )

    area_medians: dict[str, float] = {}
    aspect_medians: dict[str, float] = {}
    recomputed_counts: dict[str, dict[str, int]] = {}
    for sample_id in SAMPLES:
        candidate_rows = read_csv(result / f"{sample_id}_candidates.csv")
        roi_rows = read_csv(result / f"{sample_id}_roi_quality.csv")
        with np.load(result / f"{sample_id}_candidate_arrays.npz", allow_pickle=False) as arrays:
            schema_value = str(arrays["schema_version"].item())
            array_hash = str(arrays["config_hash"].item())
            raw = arrays["raw_signal"]
            response = arrays["membrane_response"]
            tissue = arrays["tissue_mask"]
            labels = arrays["candidate_labels"]
            centers = arrays["roi_centers_um"]

        add_check(
            checks,
            f"{sample_id}_array_schema_and_shape",
            schema_value == EXPECTED_SCHEMA
            and raw.shape[0] == 3
            and raw.shape == response.shape == tissue.shape == labels.shape
            and centers.shape == (3, 3),
            {
                "schema": schema_value,
                "raw_shape": list(raw.shape),
                "center_shape": list(centers.shape),
            },
        )
        add_check(
            checks,
            f"{sample_id}_finite_arrays",
            bool(
                np.all(np.isfinite(raw))
                and np.all(np.isfinite(response))
                and np.all(np.isfinite(centers))
                and np.all((response >= 0) & (response <= 1))
            ),
            "raw/response/center finite; response in [0,1]",
        )
        row_hashes = {row["configuration_sha256"] for row in candidate_rows}
        add_check(
            checks,
            f"{sample_id}_configuration_identity",
            array_hash == expected_hash and row_hashes == {expected_hash},
            {"array_hash": array_hash, "row_hashes": sorted(row_hashes)},
        )
        add_check(
            checks,
            f"{sample_id}_roi_count_and_orthogonality",
            len(roi_rows) == 3
            and all(float(row["orthonormality_max_error"]) < 1e-6 for row in roi_rows),
            {
                "roi_count": len(roi_rows),
                "max_error": max(
                    (float(row["orthonormality_max_error"]) for row in roi_rows),
                    default=float("inf"),
                ),
            },
        )

        label_table_complete = True
        pixel_area_consistent = True
        unique_keys: set[tuple[str, int]] = set()
        for roi_index in range(3):
            roi_id = f"roi{roi_index + 1}"
            roi_candidates = [row for row in candidate_rows if row["roi_id"] == roi_id]
            table_labels = {int(row["candidate_label"]) for row in roi_candidates}
            image_labels = set(int(value) for value in np.unique(labels[roi_index])) - {0}
            label_table_complete &= table_labels == image_labels
            for row in roi_candidates:
                label_id = int(row["candidate_label"])
                unique_keys.add((roi_id, label_id))
                recomputed_area = float(np.count_nonzero(labels[roi_index] == label_id) * PIXEL_AREA_UM2)
                pixel_area_consistent &= math_isclose(
                    recomputed_area, float(row["area_um2"]), absolute_tolerance=1e-8
                )
        label_table_complete &= len(unique_keys) == len(candidate_rows)
        add_check(
            checks,
            f"{sample_id}_label_table_complete",
            label_table_complete,
            {"table_rows": len(candidate_rows), "unique_roi_label_keys": len(unique_keys)},
        )
        add_check(
            checks,
            f"{sample_id}_pixel_area_recomputed",
            pixel_area_consistent,
            f"pixel area {PIXEL_AREA_UM2:.12g} µm²",
        )

        kept = [row for row in candidate_rows if row["keep"].lower() == "true"]
        kept_valid = all(
            20.0 <= float(row["area_um2"]) <= 600.0
            and 0.0 < float(row["aspect_ratio"]) <= 8.0
            and row["exclusion_reasons"] == ""
            and row["touches_patch_edge"].lower() == "false"
            and row["touches_tissue_edge"].lower() == "false"
            for row in kept
        )
        add_check(
            checks,
            f"{sample_id}_kept_candidate_rules",
            len(kept) >= 15 and kept_valid,
            {"kept": len(kept), "all": len(candidate_rows)},
        )
        areas = np.array([float(row["area_um2"]) for row in kept], dtype=float)
        aspects = np.array([float(row["aspect_ratio"]) for row in kept], dtype=float)
        area_medians[sample_id] = float(np.median(areas))
        aspect_medians[sample_id] = float(np.median(aspects))
        recomputed_counts[sample_id] = {"all": len(candidate_rows), "kept": len(kept)}

    area_ratio = max(area_medians.values()) / min(area_medians.values())
    aspect_ratio = max(aspect_medians.values()) / min(aspect_medians.values())
    add_check(
        checks,
        "cross_fish_median_ratios",
        area_ratio <= 2.0
        and aspect_ratio <= 2.0
        and abs(area_ratio - float(summary["cross_fish"]["area_median_max_min_ratio"])) < 1e-12
        and abs(aspect_ratio - float(summary["cross_fish"]["aspect_median_max_min_ratio"])) < 1e-12,
        {"area_ratio": area_ratio, "aspect_ratio": aspect_ratio},
    )
    add_check(
        checks,
        "summary_counts_recomputed",
        all(
            recomputed_counts[sample_id]["all"]
            == int(summary["per_fish"][sample_id]["all_candidate_count"])
            and recomputed_counts[sample_id]["kept"]
            == int(summary["per_fish"][sample_id]["kept_candidate_count"])
            for sample_id in SAMPLES
        ),
        recomputed_counts,
    )
    add_check(
        checks,
        "declared_gate_boundary",
        summary["gates"]["G0_surface_extraction"]["status"] == "passed"
        and summary["gates"]["G1_engineering_candidates"]["status"] == "passed"
        and summary["gates"]["G2_independent_human_holdout"]["status"] == "not_run"
        and summary["overall_status"] == "blocked_human_validation",
        {
            "G0": summary["gates"]["G0_surface_extraction"]["status"],
            "G1": summary["gates"]["G1_engineering_candidates"]["status"],
            "G2": summary["gates"]["G2_independent_human_holdout"]["status"],
            "overall": summary["overall_status"],
        },
    )

    image_details: dict[str, Any] = {}
    image_ok = True
    for name in (
        "surface_tangent_structure.png",
        "candidate_segmentation_audit.png",
        "candidate_summary.png",
    ):
        with Image.open(result / name) as image:
            image.verify()
        with Image.open(result / name) as image:
            width, height = image.size
            image_details[name] = {"width": width, "height": height, "mode": image.mode}
            image_ok &= width >= 1000 and height >= 600
    add_check(checks, "images_readable", image_ok, image_details)

    result_bytes_before_verification = sum(
        path.stat().st_size
        for path in result.rglob("*")
        if path.is_file() and path.name != "independent_verification.json"
    )
    add_check(
        checks,
        "result_storage_cap",
        result_bytes_before_verification < RESULT_CAP_BYTES,
        {
            "bytes_before_verification": result_bytes_before_verification,
            "cap_bytes": RESULT_CAP_BYTES,
        },
    )
    passed = all(check["status"] == "passed" for check in checks.values())
    verification = {
        "schema_version": "prl.f1seg.surface_cell_candidate.verification.v1",
        "status": "passed" if passed else "failed",
        "scope": "independent artifact consistency only; no human cell-instance truth",
        "checks": checks,
        "recomputed": {
            "counts": recomputed_counts,
            "area_medians_um2": area_medians,
            "aspect_medians": aspect_medians,
            "area_median_ratio": area_ratio,
            "aspect_median_ratio": aspect_ratio,
        },
        "scientific_boundary": "A passed verifier does not change G2=not_run or overall=blocked_human_validation.",
    }
    (result / "independent_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    return 0 if passed else 1


def math_isclose(value_a: float, value_b: float, absolute_tolerance: float) -> bool:
    return abs(value_a - value_b) <= absolute_tolerance


if __name__ == "__main__":
    raise SystemExit(main())
