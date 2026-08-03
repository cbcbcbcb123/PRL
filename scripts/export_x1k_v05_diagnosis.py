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
    "positive_signed_volume",
    "all_face_origin_contributions_positive",
    "no_self_intersection_proxy_passed",
    "symmetry_class_count",
    "maximum_symmetry_class_size",
    "exact_normal_velocity",
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

REGION_HEADER = [
    "family",
    "source_level",
    "region",
    "vertex_count",
    "control_area",
    "normal_error_energy",
    "fraction_of_total_error_energy",
    "area_weighted_relative_rms",
    "maximum_pointwise_relative_error",
]

SYMMETRY_HEADER = [
    "family",
    "source_level",
    "vertex_count",
    "symmetry_class_count",
    "maximum_symmetry_class_size",
    "minimum_required_class_count",
    "class_size_passed",
    "class_count_passed",
    "passed",
]

ENERGY_ORDER_HEADER = [
    "family",
    "coarse_source_level",
    "fine_source_level",
    "total_error_energy_order",
    "valence_5_error_energy_order",
    "valence_6_error_energy_order",
    "valence_5_closed_one_ring_error_energy_order",
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


def require_width(rows: list[list[str]], header: list[str], label: str) -> None:
    if any(len(row) != len(header) for row in rows):
        raise RuntimeError(f"v05 {label} row width changed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen X1-K v05 Family C diagnostic rows."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    level_rows = prefixed_rows(args.log, "v05_level")
    valence_rows = prefixed_rows(args.log, "v05_valence")
    class_rows = prefixed_rows(args.log, "v05_class")
    region_rows = prefixed_rows(args.log, "v05_region")
    symmetry_rows = prefixed_rows(args.log, "v05_symmetry")
    energy_order_rows = prefixed_rows(args.log, "v05_energy_order")
    gate_rows = prefixed_rows(args.log, "v05_gate")
    if (
        len(level_rows) != 4
        or len(valence_rows) != 8
        or len(class_rows) != 1704
        or len(region_rows) != 12
        or len(symmetry_rows) != 4
        or len(energy_order_rows) != 3
        or len(gate_rows) != 1
    ):
        raise RuntimeError("v05 log lacks one complete Family C diagnosis")
    require_width(level_rows, LEVEL_HEADER, "level")
    require_width(valence_rows, VALENCE_HEADER, "valence")
    require_width(class_rows, CLASS_HEADER, "symmetry-class")
    require_width(region_rows, REGION_HEADER, "error-region")
    require_width(symmetry_rows, SYMMETRY_HEADER, "symmetry-gate")
    require_width(energy_order_rows, ENERGY_ORDER_HEADER, "energy-order")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "family_c_levels.csv", LEVEL_HEADER, level_rows)
    write_csv(args.output_dir / "family_c_valence.csv", VALENCE_HEADER, valence_rows)
    write_csv(
        args.output_dir / "family_c_symmetry_classes.csv",
        CLASS_HEADER,
        class_rows,
    )
    write_csv(
        args.output_dir / "family_c_error_regions.csv",
        REGION_HEADER,
        region_rows,
    )
    write_csv(
        args.output_dir / "family_c_valence5_one_ring.csv",
        REGION_HEADER,
        [row for row in region_rows if row[2] == "valence_5_closed_one_ring"],
    )
    write_csv(
        args.output_dir / "family_c_symmetry_gate.csv",
        SYMMETRY_HEADER,
        symmetry_rows,
    )
    write_csv(
        args.output_dir / "family_c_error_energy_orders.csv",
        ENERGY_ORDER_HEADER,
        energy_order_rows,
    )
    write_csv(
        args.output_dir / "raw_gate.csv",
        [f"field_{index}" for index in range(len(gate_rows[0]))],
        gate_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
