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

CLASS_HEADER = [
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


def rows_for_family(rows: list[list[str]], family: str) -> list[list[str]]:
    return [row for row in rows if row and row[0] == family]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen X1-K v04 Family A/B diagnostic rows."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    level_rows = prefixed_rows(args.log, "v04_level")
    valence_rows = prefixed_rows(args.log, "v04_valence")
    class_rows = prefixed_rows(args.log, "v04_class")
    for family in ("A", "B"):
        family_levels = rows_for_family(level_rows, family)
        family_valences = rows_for_family(valence_rows, family)
        family_classes = rows_for_family(class_rows, family)
        if len(family_levels) != 4 or len(family_valences) != 8 or not family_classes:
            raise RuntimeError(f"v04 log lacks one complete Family {family} diagnosis")
        if any(len(row) != len(LEVEL_HEADER) for row in family_levels):
            raise RuntimeError(f"v04 Family {family} level row width changed")
        if any(len(row) != len(VALENCE_HEADER) for row in family_valences):
            raise RuntimeError(f"v04 Family {family} valence row width changed")
        if any(len(row) != len(CLASS_HEADER) for row in family_classes):
            raise RuntimeError(f"v04 Family {family} class row width changed")

        prefix = f"family_{family.lower()}"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(args.output_dir / f"{prefix}_levels.csv", LEVEL_HEADER, family_levels)
        write_csv(
            args.output_dir / f"{prefix}_valence.csv",
            VALENCE_HEADER,
            family_valences,
        )
        write_csv(
            args.output_dir / f"{prefix}_symmetry_classes.csv",
            CLASS_HEADER,
            family_classes,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
