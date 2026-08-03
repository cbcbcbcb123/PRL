from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


STRUCTURAL_HEADER = [
    "family",
    "source_level",
    "vertex_count",
    "face_count",
    "initial_h_rms",
    "surface_area",
    "dual_area_sum",
    "dual_area_to_surface_area_ratio",
    "homogeneity_force_contraction",
    "exact_homogeneity_force_contraction",
    "normalized_homogeneity_residual",
    "mean_radial_velocity",
    "exact_mean_radial_velocity",
    "normalized_mean_radial_velocity_residual",
    "normalized_net_force_residual",
    "maximum_relative_radius_deviation",
    "maximum_position_displacement",
    "position_hash_before",
    "position_hash_after",
    "state_hash_before",
    "state_hash_after",
    "maximum_force_buffer_norm_after",
    "force_buffers_cleared",
    "passed",
]

STEP_HEADER = [
    "family",
    "source_level",
    "time_step",
    "step",
    "time",
    "initial_h_rms",
    "exact_radius",
    "control_area_mean_radius",
    "control_area_mean_radius_ratio",
    "area_ratio",
    "volume_ratio",
    "registered_energy_ratio",
    "normalized_surface_centroid_drift",
    "minimum_oriented_face_alignment",
    "minimum_triangle_quality",
    "minimum_face_area_ratio",
    "maximum_normalized_cache_residual",
]

LOCAL_HEADER = [
    "family",
    "source_level",
    "time_step",
    "step",
    "time",
    "maximum_valence_five_excursion_error",
    "rms_valence_five_radial_error",
    "maximum_closed_one_ring_excursion_error",
    "rms_closed_one_ring_radial_error",
    "maximum_valence_five_error_over_initial_h",
    "maximum_closed_one_ring_error_over_initial_h",
    "maximum_closed_one_ring_edge_scaling_error",
    "local_minimum_triangle_quality",
    "local_minimum_triangle_quality_ratio",
    "valence_five_normal_error_energy_fraction",
    "valence_five_normal_error_relative_rms",
    "valence_five_normal_error_pointwise_maximum",
    "closed_one_ring_normal_error_energy_fraction",
    "closed_one_ring_normal_error_relative_rms",
    "closed_one_ring_normal_error_pointwise_maximum",
    "force_buffers_cleared",
]

ENERGY_INPUT_HEADER = [
    "family",
    "source_level",
    "time_step",
    "step",
    "time",
    "registered_surface_energy",
    "viscous_dissipation",
    "delta_psi_plus_d_zeta",
]

ENERGY_HEADER = [
    *ENERGY_INPUT_HEADER[:5],
    "registered_surface_energy",
    "delta_psi",
    "viscous_dissipation",
    "delta_psi_plus_d_zeta",
    "positive_delta_psi_plus_d_zeta",
    "cumulative_positive_delta_psi_plus_d_zeta",
]

TIME_HEADER = [
    "family",
    "source_level",
    "initial_h_rms",
    "exact_mean_radius_response",
    "response_dt_4e_4",
    "response_dt_2e_4",
    "response_dt_1e_4",
    "response_dt_5e_5",
    "difference_4e_4_to_2e_4",
    "difference_2e_4_to_1e_4",
    "difference_1e_4_to_5e_5",
    "observed_order_0",
    "observed_order_1",
    "richardson_response",
    "richardson_error",
    "area_ratio_dt_4e_4",
    "area_ratio_dt_2e_4",
    "area_ratio_dt_1e_4",
    "area_ratio_dt_5e_5",
    "volume_ratio_dt_4e_4",
    "volume_ratio_dt_2e_4",
    "volume_ratio_dt_1e_4",
    "volume_ratio_dt_5e_5",
    "registered_energy_ratio_dt_4e_4",
    "registered_energy_ratio_dt_2e_4",
    "registered_energy_ratio_dt_1e_4",
    "registered_energy_ratio_dt_5e_5",
    "common_roundoff_plateau",
    "differences_strictly_decreased",
    "time_orders_passed",
    "richardson_passed",
    "minimum_oriented_face_alignment",
    "minimum_triangle_quality",
    "minimum_face_area_ratio",
    "maximum_normalized_cache_residual",
    "maximum_normalized_centroid_drift",
    "maximum_normalized_positive_energy_residual",
    "maximum_valence_five_excursion_error",
    "maximum_closed_one_ring_excursion_error",
    "maximum_valence_five_error_over_initial_h",
    "maximum_closed_one_ring_error_over_initial_h",
    "maximum_closed_one_ring_edge_scaling_error",
    "minimum_local_triangle_quality_ratio",
    "force_buffers_cleared",
    "readonly_controls_passed",
    "passed",
]


def prefixed_rows(log_path: Path, prefix: str) -> list[list[str]]:
    rows: list[list[str]] = []
    with log_path.open("r", encoding="utf-8") as source:
        for raw_line in source:
            line = raw_line.strip()
            if line.startswith(prefix + ","):
                rows.append(next(csv.reader([line]))[1:])
    return rows


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def require_width(rows: list[list[str]], width: int, label: str) -> None:
    if any(len(row) != width for row in rows):
        raise RuntimeError(f"v07 {label} row width changed")


def parse_key_value_tail(
    row: list[str], fixed_width: int, expected_keys: list[str], label: str
) -> list[str]:
    if len(row) != fixed_width + 2 * len(expected_keys):
        raise RuntimeError(f"v07 {label} row width changed")
    values = dict(zip(row[fixed_width::2], row[fixed_width + 1 :: 2], strict=True))
    if list(values) != expected_keys:
        raise RuntimeError(f"v07 {label} key sequence changed")
    return [*row[:fixed_width], *(values[key] for key in expected_keys)]


def bool_value(raw: str) -> bool:
    if raw not in {"0", "1"}:
        raise RuntimeError(f"unexpected C++ bool serialization: {raw}")
    return raw == "1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen X1-K v07 mean-radius diagnostic evidence."
    )
    parser.add_argument("--structural-log", type=Path, required=True)
    parser.add_argument("--time-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    structural_rows = prefixed_rows(args.structural_log, "v07_structural")
    step_rows = prefixed_rows(args.time_log, "v07_step")
    local_rows = prefixed_rows(args.time_log, "v07_local")
    energy_rows = prefixed_rows(args.time_log, "v07_energy")
    time_input_rows = prefixed_rows(args.time_log, "v07_time_level")
    gate_input_rows = prefixed_rows(args.time_log, "v07_time_gate")
    if (
        len(structural_rows) != 4
        or len(step_rows) != 1508
        or len(local_rows) != 1508
        or len(energy_rows) != 1508
        or len(time_input_rows) != 2
        or len(gate_input_rows) != 1
    ):
        raise RuntimeError("v07 logs do not contain one complete frozen response batch")
    require_width(structural_rows, len(STRUCTURAL_HEADER), "structural")
    require_width(step_rows, len(STEP_HEADER), "step")
    require_width(local_rows, len(LOCAL_HEADER), "local")
    require_width(energy_rows, len(ENERGY_INPUT_HEADER), "energy")
    for step_row, local_row, energy_row in zip(
        step_rows, local_rows, energy_rows, strict=True
    ):
        if step_row[:5] != local_row[:5] or step_row[:5] != energy_row[:5]:
            raise RuntimeError("v07 per-step global/local/energy keys diverged")

    expected_time_keys = [
        "plateau",
        "strict",
        "orders",
        "richardson",
        "min_alignment",
        "min_q",
        "min_face_ratio",
        "max_cache",
        "max_centroid",
        "max_energy",
        "max_v5_excursion",
        "max_ring_excursion",
        "max_v5_h",
        "max_ring_h",
        "max_edge",
        "min_local_q_ratio",
        "buffers",
        "controls",
        "passed",
    ]
    time_rows = [
        parse_key_value_tail(row, 27, expected_time_keys, "time-level")
        for row in time_input_rows
    ]
    expected_gate_keys = [
        "exact",
        "trajectories",
        "time_levels",
        "cross_difference",
        "cross_passed",
        "controls",
        "passed",
    ]
    gate_row = parse_key_value_tail(
        gate_input_rows[0], 1, expected_gate_keys, "time-gate"
    )
    gate = dict(zip(expected_gate_keys, gate_row[1:], strict=True))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "structural_identity.csv", STRUCTURAL_HEADER, structural_rows)
    write_csv(args.output_dir / "global_step_metrics.csv", STEP_HEADER, step_rows)
    write_csv(args.output_dir / "local_step_metrics.csv", LOCAL_HEADER, local_rows)

    expected_counts = {
        "0.00040000000000000002": 51,
        "0.00020000000000000001": 101,
        "0.0001": 201,
        "5.0000000000000002e-05": 401,
    }
    filenames = {
        "0.00040000000000000002": "dt_4e-4",
        "0.00020000000000000001": "dt_2e-4",
        "0.0001": "dt_1e-4",
        "5.0000000000000002e-05": "dt_5e-5",
    }
    run_rows: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
    for row in step_rows:
        run_rows[(row[1], row[2])].append(row)
    if set(run_rows) != {
        (level, time_step)
        for level in {"1", "4"}
        for time_step in expected_counts
    }:
        raise RuntimeError("v07 time-response run matrix changed")
    for (level, time_step), rows in run_rows.items():
        expected_count = expected_counts[time_step]
        if len(rows) != expected_count or [int(row[3]) for row in rows] != list(
            range(expected_count)
        ):
            raise RuntimeError("v07 trajectory step sequence changed")
        write_csv(
            args.output_dir / f"family_c_level_{level}_{filenames[time_step]}_steps.csv",
            STEP_HEADER,
            rows,
        )

    energy_ledger: list[list[Any]] = []
    previous_energy: dict[tuple[str, str, str], float] = {}
    cumulative_positive: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in energy_rows:
        run_key = (row[0], row[1], row[2])
        energy = float(row[5])
        delta_psi = (
            0.0 if run_key not in previous_energy else energy - previous_energy[run_key]
        )
        residual = float(row[7])
        if abs(delta_psi + float(row[6]) - residual) > 1.0e-12 * max(
            1.0, abs(energy)
        ):
            raise RuntimeError("v07 exported energy ledger does not recompute")
        positive_residual = max(0.0, residual)
        cumulative_positive[run_key] += positive_residual
        energy_ledger.append(
            [
                *row[:5],
                row[5],
                f"{delta_psi:.17g}",
                row[6],
                row[7],
                f"{positive_residual:.17g}",
                f"{cumulative_positive[run_key]:.17g}",
            ]
        )
        previous_energy[run_key] = energy
    write_csv(args.output_dir / "energy_ledger.csv", ENERGY_HEADER, energy_ledger)
    write_csv(args.output_dir / "time_diagnosis.csv", TIME_HEADER, time_rows)
    write_csv(
        args.output_dir / "raw_time_gate.csv",
        ["criterion", "observed"],
        [[key, value] for key, value in gate.items()],
    )

    criteria_rows: list[list[Any]] = []
    for row in structural_rows:
        level = row[1]
        structural_criteria = [
            ("homogeneity_residual", "less_equal", "1e-12", row[10]),
            ("mean_velocity_residual", "less_equal", "1e-12", row[13]),
            ("dual_area_closure", "less_equal", "1e-12", abs(float(row[7]) - 1.0)),
            ("net_force_residual", "less_equal", "1e-12", row[14]),
            ("radius_consistency", "less_equal", "1e-12", row[15]),
            ("maximum_position_displacement", "equal", "0", row[16]),
            ("position_hash_unchanged", "equal", "true", str(row[17] == row[18]).lower()),
            ("state_hash_unchanged", "equal", "true", str(row[19] == row[20]).lower()),
            ("force_buffer_norm_after", "equal", "0", row[21]),
            ("force_buffers_cleared", "equal", "true", str(bool_value(row[22])).lower()),
        ]
        for criterion, operator, threshold, observed in structural_criteria:
            criteria_rows.append(
                [f"structural_level_{level}", criterion, operator, threshold, observed, "true"]
            )

    for row in time_rows:
        level = row[1]
        criteria_rows.extend(
            [
                [f"time_level_{level}", "common_roundoff_plateau", "equal", "false", str(bool_value(row[27])).lower(), str(not bool_value(row[27])).lower()],
                [f"time_level_{level}", "differences_strictly_decreased", "equal", "true", str(bool_value(row[28])).lower(), row[28]],
                [f"time_level_{level}", "minimum_time_order", "greater_equal", "0.75", min(float(row[11]), float(row[12])), row[29]],
                [f"time_level_{level}", "maximum_time_order", "less_equal", "1.25", max(float(row[11]), float(row[12])), row[29]],
                [f"time_level_{level}", "richardson_error", "less_equal", "1e-10", row[14], row[30]],
                [f"time_level_{level}", "minimum_oriented_alignment", "greater_than", "0", row[31], "true"],
                [f"time_level_{level}", "minimum_triangle_quality", "greater_equal", "0.05", row[32], "true"],
                [f"time_level_{level}", "minimum_face_area_ratio", "greater_equal", "1e-4", row[33], "true"],
                [f"time_level_{level}", "maximum_cache_residual", "less_equal", "1e-12", row[34], "true"],
                [f"time_level_{level}", "maximum_centroid_drift", "less_equal", "1e-2", row[35], "true"],
                [f"time_level_{level}", "maximum_positive_energy_residual", "less_equal", "1e-3", row[36], "true"],
                [f"time_level_{level}", "maximum_local_excursion_error", "less_equal", "0.25", max(float(row[37]), float(row[38])), "true"],
                [f"time_level_{level}", "maximum_local_radial_error_over_h", "less_equal", "5e-4", max(float(row[39]), float(row[40])), "true"],
                [f"time_level_{level}", "maximum_local_edge_scaling_error", "less_equal", "5e-4", row[41], "true"],
                [f"time_level_{level}", "minimum_local_quality_ratio", "greater_equal", "0.90", row[42], "true"],
                [f"time_level_{level}", "readonly_controls", "equal", "true", str(bool_value(row[44])).lower(), row[44]],
                [f"time_level_{level}", "overall", "equal", "true", str(bool_value(row[45])).lower(), row[45]],
            ]
        )
    criteria_rows.extend(
        [
            ["time_cross_mesh", "richardson_difference", "less_equal", "1e-10", gate["cross_difference"], gate["cross_passed"]],
            ["v07", "overall", "equal", "true", str(bool_value(gate["passed"])).lower(), gate["passed"]],
        ]
    )
    write_csv(
        args.output_dir / "criteria.csv",
        ["scope", "criterion", "operator", "threshold", "observed", "passed"],
        criteria_rows,
    )

    structural = {int(row[1]): row for row in structural_rows}
    time_by_level = {int(row[1]): row for row in time_rows}
    exact = float(gate["exact"])
    if not math.isclose(exact, math.sqrt(1.0 - 4.0 * 0.02 * 0.02 / 10.0), rel_tol=0.0, abs_tol=1.0e-15):
        raise RuntimeError("v07 exact response changed")
    if not all(bool_value(row[23]) for row in structural_rows):
        raise RuntimeError("v07 structural gate did not pass")
    if not bool_value(gate["passed"]):
        raise RuntimeError("v07 time-floor gate did not pass")

    summary = {
        "contract_id": "CONTRACT-PRL-HYBRID-X1-K-V07-DIAGNOSIS",
        "contract_commit": "668465c9f554850d0624eef474c49b8514c21cce",
        "result_package_commit": "f4df24c840f357fc06a45c4406bc55b9817199b9",
        "status": "passed_structural_mean_radius_identity_and_time_floor_diagnosis",
        "x1_k_passed": False,
        "downstream_authorized": False,
        "structural_identity": {
            "source_levels": [1, 2, 3, 4],
            "maximum_homogeneity_residual": max(float(row[10]) for row in structural_rows),
            "maximum_mean_velocity_residual": max(float(row[13]) for row in structural_rows),
            "maximum_dual_area_closure_residual": max(abs(float(row[7]) - 1.0) for row in structural_rows),
            "maximum_net_force_residual": max(float(row[14]) for row in structural_rows),
            "maximum_radius_inconsistency": max(float(row[15]) for row in structural_rows),
            "maximum_position_displacement": max(float(row[16]) for row in structural_rows),
            "force_buffers_cleared": all(bool_value(row[22]) for row in structural_rows),
            "position_and_state_hashes_unchanged": all(row[17] == row[18] and row[19] == row[20] for row in structural_rows),
            "claim_scope": "initial equal-radius sphere only; Euler uniform-scaling identity, not a full gradient or full-trajectory identity",
        },
        "time_floor_diagnosis": {
            "source_levels": [1, 4],
            "time_steps": [4.0e-4, 2.0e-4, 1.0e-4, 5.0e-5],
            "step_counts": [50, 100, 200, 400],
            "final_time": 2.0e-2,
            "exact_mean_radius_response": exact,
            "levels": {
                str(level): {
                    "initial_h_rms": float(time_by_level[level][2]),
                    "responses": [float(value) for value in time_by_level[level][4:8]],
                    "adjacent_time_differences": [float(value) for value in time_by_level[level][8:11]],
                    "observed_time_orders": [float(value) for value in time_by_level[level][11:13]],
                    "richardson_response": float(time_by_level[level][13]),
                    "richardson_error": float(time_by_level[level][14]),
                    "roundoff_plateau": bool_value(time_by_level[level][27]),
                    "readonly_controls_passed": bool_value(time_by_level[level][44]),
                    "passed": bool_value(time_by_level[level][45]),
                }
                for level in [1, 4]
            },
            "cross_mesh_richardson_difference": float(gate["cross_difference"]),
            "passed": bool_value(gate["passed"]),
        },
        "frozen_model": {
            "family": "C",
            "M_C": [[1.0, 0.05, 0.025], [0.05, 1.05, 0.04], [0.025, 0.04, 0.95]],
            "reference_radius": 1.0,
            "surface_tension": 0.02,
            "damping_per_area": 10.0,
            "damping_measure": "barycentric_dual_area",
            "topology": "fixed",
        },
        "coverage": {
            "energy": "surface_tension_only",
            "registered": ["gamma*A", "D_zeta"],
            "excluded": [
                "legacy_0.5_gamma_A_cache",
                "membrane_elasticity",
                "bending",
                "pressure",
                "contact",
                "active",
                "ECM",
                "flow",
            ],
        },
        "preserved_history": {
            "v02_D1": "failed_instantaneous_smooth_surface_refinement",
            "v04_Family_B": "failed_family_B_parameterized_diagnosis",
            "v05": "passed_quality_controlled_symmetry_broken_global_L2_diagnosis",
            "v06": {
                "status": "failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic",
                "mean_radius_errors": [1.0439287051472873e-7, 1.6965749578041943e-7, 1.931183453395129e-7, 1.984083464348854e-7],
                "observed_spatial_orders": [-0.7305866503451734, -0.1888361880551532, -0.03909027092934956],
                "rejudged_by_v07": False,
            },
            "route_h_gate_a_v01": "failed_invalid_numerics",
        },
        "verification": {
            "parent_cpp": {
                "passed": 52,
                "total": 55,
                "expected_frozen_failures": [
                    "prl_x1k_sphere_instantaneous_velocity_refinement",
                    "prl_x1k_v04_family_b_parameterized_diagnosis",
                    "prl_x1k_v06_family_c_short_trajectory_gate",
                ],
                "unexpected_failures": 0,
                "v07_passed": 4,
                "v07_total": 4,
            },
            "controlled_fork": {"passed": 134, "total": 134},
            "owned_prl_core_strict_build": {
                "status": "passed",
                "flags": "-Wall -Wextra -Wpedantic -Werror",
            },
            "python_pytest": {"passed": 63, "total": 63},
            "python_ruff": "passed",
            "exporter": {
                "structural_rows": 4,
                "global_rows": 1508,
                "local_rows": 1508,
                "energy_rows": 1508,
                "energy_ledger_recomputed": True,
            },
        },
        "not_executed": [
            "R1_remesh_on",
            "C1_contact",
            "F1_failure_persistence",
            "ECM_flow_long_coupling",
            "parameter_calibration",
        ],
        "claim_guard": "v07 supports only the frozen initial structural identity and bounded two-mesh time-floor diagnosis. X1-K remains failed; long-time stability, physiology, cell-ECM/FSI, EFE, calibration, and developmental-mechanism claims are not allowed.",
        "structural_levels": {
            str(level): {
                "h_rms": float(structural[level][4]),
                "homogeneity_residual": float(structural[level][10]),
                "mean_velocity_residual": float(structural[level][13]),
            }
            for level in [1, 2, 3, 4]
        },
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as target:
        json.dump(summary, target, indent=2, ensure_ascii=False)
        target.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
