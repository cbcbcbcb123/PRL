from __future__ import annotations

import argparse
import csv
from pathlib import Path


LEVEL_HEADER = [
    "family",
    "source_level",
    "vertices",
    "triangles",
    "h_min",
    "h_rms",
    "h_max",
    "directional_residual",
    "legacy_cache_ratio",
    "normal_velocity_relative_l2",
    "tangential_velocity_relative_l2",
    "normalized_net_force_residual",
    "minimum_triangle_quality",
    "minimum_outward_alignment",
    "minimum_face_to_mean_area_ratio",
    "maximum_radius_deviation",
    "euler_characteristic",
    "closed_two_manifold",
    "no_self_intersection_proxy_passed",
    "symmetry_class_count",
    "maximum_symmetry_class_size",
]

DISTRIBUTION_HEADER = [
    "family",
    "source_level",
    "group_id",
    "valence",
    "vertex_count",
    "normal_absolute_error_mean",
    "normal_absolute_error_maximum",
    "normal_absolute_error_rms",
    "tangential_speed_mean",
    "tangential_speed_maximum",
    "tangential_speed_rms",
]

VALENCE_HEADER = [
    "family",
    "source_level",
    "valence",
    "vertex_count",
    "normal_absolute_error_mean",
    "normal_absolute_error_maximum",
    "normal_absolute_error_rms",
    "tangential_speed_mean",
    "tangential_speed_maximum",
    "tangential_speed_rms",
]


def prefixed_rows(log_path: Path, prefix: str) -> list[list[str]]:
    rows: list[list[str]] = []
    with log_path.open("r", encoding="utf-8") as source:
        for raw_line in source:
            line = raw_line.strip()
            if line.startswith(prefix + ","):
                rows.append(next(csv.reader([line]))[1:])
    return rows


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen X1-K v03 CTest diagnostic rows."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    level_rows = prefixed_rows(args.log, "v03_level")
    valence_rows = prefixed_rows(args.log, "v03_valence")
    class_rows = prefixed_rows(args.log, "v03_class")
    if len(level_rows) != 4 or len(valence_rows) != 8 or not class_rows:
        raise RuntimeError(
            "v03 log does not contain one complete frozen Family A diagnosis"
        )
    if any(len(row) != len(LEVEL_HEADER) for row in level_rows):
        raise RuntimeError("v03 level row width changed")
    if any(len(row) != len(VALENCE_HEADER) for row in valence_rows):
        raise RuntimeError("v03 valence row width changed")
    if any(len(row) != len(DISTRIBUTION_HEADER) for row in class_rows):
        raise RuntimeError("v03 class row width changed")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "family_a_levels.csv", LEVEL_HEADER, level_rows)
    write_csv(args.output_dir / "family_a_valence.csv", VALENCE_HEADER, valence_rows)
    write_csv(
        args.output_dir / "family_a_symmetry_classes.csv",
        DISTRIBUTION_HEADER,
        class_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
