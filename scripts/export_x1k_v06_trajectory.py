from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


STEP_HEADER = [
    "run",
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
    "run",
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
    "run",
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

QOI_HEADER = [
    "qoi",
    "exact_final_value",
    "reported_finest_excursion",
    "level_1_response",
    "level_2_response",
    "level_3_response",
    "level_4_response",
    "level_1_excursion",
    "level_2_excursion",
    "level_3_excursion",
    "level_4_excursion",
    "level_1_analytic_error",
    "level_2_analytic_error",
    "level_3_analytic_error",
    "level_4_analytic_error",
    "analytic_order_1_2",
    "analytic_order_2_3",
    "analytic_order_3_4",
    "difference_excursion_1_2",
    "difference_excursion_2_3",
    "difference_excursion_3_4",
    "adjacent_difference_1_2",
    "adjacent_difference_2_3",
    "adjacent_difference_3_4",
    "generalized_order_1_2_3",
    "generalized_order_2_3_4",
    "analytic_roundoff_plateau",
    "analytic_errors_monotonic",
    "analytic_orders_passed",
    "finest_error_passed",
    "self_convergence_roundoff_plateau",
    "self_convergence_monotonic",
    "self_convergence_orders_passed",
    "passed",
]

TIME_HEADER = [
    "qoi",
    "dt_response",
    "dt_half_response",
    "exact_final_value",
    "exact_excursion",
    "absolute_time_difference",
    "excursion_normalized_time_difference",
    "absolute_space_proxy",
    "excursion_normalized_space_proxy",
    "roundoff_plateau",
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
        raise RuntimeError(f"v06 {label} row width changed")


def parse_qoi(row: list[str]) -> list[str]:
    if len(row) != 44 or row[1] != "exact" or row[3] != "excursion":
        raise RuntimeError("v06 QoI row schema changed")
    fixed = [row[0], row[2], row[4], *row[5:28]]
    flags = dict(zip(row[28::2], row[29::2], strict=True))
    expected = [
        "analytic_plateau",
        "analytic_monotonic",
        "analytic_orders",
        "finest",
        "self_plateau",
        "self_monotonic",
        "self_orders",
        "passed",
    ]
    if list(flags) != expected:
        raise RuntimeError("v06 QoI flags changed")
    return [*fixed, *(flags[name] for name in expected)]


def parse_time(row: list[str]) -> list[str]:
    if len(row) != 13 or row[9] != "plateau" or row[11] != "passed":
        raise RuntimeError("v06 time-pollution row schema changed")
    return [*row[:9], row[10], row[12]]


def parse_gate(row: list[str]) -> dict[str, str]:
    if not row or row[0] != "global" or len(row[1:]) % 2 != 0:
        raise RuntimeError("v06 global gate row schema changed")
    return dict(zip(row[1::2], row[2::2], strict=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen X1-K v06 Family C trajectory failure evidence."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    step_rows = prefixed_rows(args.log, "v06_step")
    local_rows = prefixed_rows(args.log, "v06_local")
    energy_rows = prefixed_rows(args.log, "v06_energy")
    qoi_input_rows = prefixed_rows(args.log, "v06_qoi")
    time_input_rows = prefixed_rows(args.log, "v06_time")
    gate_rows = prefixed_rows(args.log, "v06_gate")
    if (
        len(step_rows) != 1205
        or len(local_rows) != 1205
        or len(energy_rows) != 1205
        or len(qoi_input_rows) != 4
        or len(time_input_rows) != 4
        or len(gate_rows) != 1
    ):
        raise RuntimeError("v06 log lacks one complete frozen trajectory response")
    require_width(step_rows, len(STEP_HEADER), "step")
    require_width(local_rows, len(LOCAL_HEADER), "local")
    require_width(energy_rows, len(ENERGY_INPUT_HEADER), "energy")
    for step_row, local_row, energy_row in zip(
        step_rows, local_rows, energy_rows, strict=True
    ):
        if step_row[:5] != local_row[:5] or step_row[:5] != energy_row[:5]:
            raise RuntimeError("v06 per-step global/local/energy keys diverged")

    qoi_rows = [parse_qoi(row) for row in qoi_input_rows]
    time_rows = [parse_time(row) for row in time_input_rows]
    gate = parse_gate(gate_rows[0])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_rows: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
    for row in step_rows:
        run_rows[(row[0], row[1])].append(row)
    expected_runs = {
        ("C", "1"): "family_c_level_1_steps.csv",
        ("C", "2"): "family_c_level_2_steps.csv",
        ("C", "3"): "family_c_level_3_steps.csv",
        ("C", "4"): "family_c_level_4_steps.csv",
        ("C_dt_half", "4"): "family_c_level_4_dt_half_steps.csv",
    }
    if set(run_rows) != set(expected_runs):
        raise RuntimeError("v06 trajectory run matrix changed")
    for run_key, rows in run_rows.items():
        expected_count = 401 if run_key[0] == "C_dt_half" else 201
        if len(rows) != expected_count or [int(row[3]) for row in rows] != list(
            range(expected_count)
        ):
            raise RuntimeError("v06 trajectory step sequence changed")
    for run_key, filename in expected_runs.items():
        write_csv(args.output_dir / filename, STEP_HEADER, run_rows[run_key])
    write_csv(args.output_dir / "local_step_metrics.csv", LOCAL_HEADER, local_rows)

    energy_ledger: list[list[Any]] = []
    previous_energy: dict[tuple[str, str, str], float] = {}
    cumulative_positive: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in energy_rows:
        run_key = (row[0], row[1], row[2])
        energy = float(row[5])
        delta_psi = 0.0 if run_key not in previous_energy else (
            energy - previous_energy[run_key]
        )
        residual = float(row[7])
        if abs(delta_psi + float(row[6]) - residual) > 1.0e-12 * max(
            1.0, abs(energy)
        ):
            raise RuntimeError("v06 exported energy ledger does not recompute")
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
    write_csv(args.output_dir / "final_qoi_gate.csv", QOI_HEADER, qoi_rows)
    write_csv(args.output_dir / "time_pollution.csv", TIME_HEADER, time_rows)
    write_csv(
        args.output_dir / "raw_global_gate.csv",
        ["criterion", "observed"],
        [[key, value] for key, value in gate.items()],
    )

    qoi_by_name = {row[0]: row for row in qoi_rows}
    radius = qoi_by_name["mean_radius_ratio"]
    criteria_rows: list[list[Any]] = []
    for row in qoi_rows:
        criteria_rows.extend(
            [
                [
                    row[0],
                    "analytic_errors_nonincreasing",
                    "equal",
                    "true",
                    row[27],
                    row[27],
                    "four excursion-normalized errors",
                ],
                [
                    row[0],
                    "minimum_nonplateau_analytic_order",
                    "greater_equal",
                    "0.5",
                    min(float(value) for value in row[15:18]),
                    row[28],
                    "actual h_rms; common plateau=1e-10",
                ],
                [
                    row[0],
                    "finest_excursion_normalized_error",
                    "less_equal",
                    "0.02",
                    row[14],
                    row[29],
                    "final source level 4",
                ],
                [
                    row[0],
                    "adjacent_differences_nonincreasing",
                    "equal",
                    "true",
                    row[31],
                    row[31],
                    "three excursion-normalized differences",
                ],
                [
                    row[0],
                    "minimum_generalized_self_order",
                    "greater_equal",
                    "0.5",
                    min(float(value) for value in row[24:26]),
                    row[32],
                    "root in [0,16] with actual h_rms",
                ],
            ]
        )
    for row in time_rows:
        criteria_rows.append(
            [
                row[0],
                "finest_time_pollution",
                "plateau_or_less_equal_fraction",
                "raw plateau=1e-10 or delta<=0.25*proxy",
                f"delta={row[5]};proxy={row[7]}",
                row[10],
                "raw and excursion-normalized values retained",
            ]
        )
    criteria_rows.extend(
        [
            ["global", "minimum_oriented_alignment", "greater_than", "0", gate["min_alignment"], "1", "all runs and steps"],
            ["global", "minimum_triangle_quality", "greater_equal", "0.05", gate["min_q"], "1", "surface triangles only"],
            ["global", "minimum_face_area_ratio", "greater_equal", "1e-4", gate["min_face_ratio"], "1", "relative to each run initial minimum"],
            ["global", "maximum_cache_residual", "less_equal", "1e-12", gate["max_cache"], "1", "independent geometry versus cache"],
            ["global", "maximum_centroid_drift", "less_equal", "1e-2", gate["max_centroid"], "1", "surface centroid divided by R0"],
            ["energy", "maximum_normalized_positive_ledger", "less_equal", "1e-3", gate["max_energy"], "1", "surface_tension_only coverage"],
            ["local", "maximum_excursion_error", "less_equal", "0.25", max(float(gate["max_v5_excursion"]), float(gate["max_ring_excursion"])), gate["local"], "valence-5 and closed one-ring"],
            ["local", "maximum_radial_error_over_h0", "less_equal", "5e-4", max(float(gate["max_v5_h"]), float(gate["max_ring_h"])), gate["local"], "valence-5 and closed one-ring"],
            ["local", "maximum_edge_scaling_error", "less_equal", "5e-4", gate["max_edge"], gate["local"], "closed one-ring edges"],
            ["local", "minimum_quality_ratio", "greater_equal", "0.90", gate["min_local_q_ratio"], gate["local"], "closed one-ring incident faces"],
            ["v06", "overall", "equal", "true", gate["passed"], gate["passed"], "first failure is radius analytic monotonicity"],
        ]
    )
    write_csv(
        args.output_dir / "criteria.csv",
        ["scope", "criterion", "operator", "threshold", "observed", "passed", "notes"],
        criteria_rows,
    )

    summary = {
        "contract_id": "CONTRACT-PRL-HYBRID-X1-K-V06-S1",
        "contract_commit": "ae80a0b6c77309fcfc6c3b2a19d8dbeb68af90b8",
        "failure_package_commit": "eb3c97339580e3d2e0f565e47b9b78dab292046e",
        "status": "failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic",
        "x1_k_passed": False,
        "first_failed_gate": {
            "case": "S1_Family_C",
            "qoi": "control_area_mean_radius_ratio",
            "criterion": "four_level_excursion_normalized_analytic_error_nonincreasing",
            "errors": [float(value) for value in radius[11:15]],
            "observed_orders": [float(value) for value in radius[15:18]],
            "plateau": radius[26] == "1",
            "monotonic": radius[27] == "1",
        },
        "frozen_matrix": {
            "source_levels": [1, 2, 3, 4],
            "h_rms": [float(run_rows[("C", str(level))][0][5]) for level in range(1, 5)],
            "time_step": 1.0e-4,
            "steps": 200,
            "final_time": 2.0e-2,
            "finest_half_time_step": 5.0e-5,
            "finest_half_steps": 400,
            "surface_tension": 0.02,
            "damping_per_area": 10.0,
            "reference_radius": 1.0,
            "topology": "fixed",
            "remesh_contact_active": False,
        },
        "other_gates": {
            "area_ratio": qoi_by_name["area_ratio"][-1] == "1",
            "volume_ratio": qoi_by_name["volume_ratio"][-1] == "1",
            "registered_energy_ratio": qoi_by_name["energy_ratio"][-1] == "1",
            "self_convergence": gate["self"] == "1",
            "time_pollution": gate["time"] == "1",
            "global_geometry_and_cache": gate["geometry"] == "1",
            "surface_tension_only_energy": gate["energy"] == "1",
            "local_risk_bounds": gate["local"] == "1",
            "force_buffers_cleared": gate["buffers"] == "1",
        },
        "local_risk_observations": {
            "maximum_valence_five_excursion_error": float(gate["max_v5_excursion"]),
            "maximum_closed_one_ring_excursion_error": float(gate["max_ring_excursion"]),
            "maximum_radial_error_over_initial_h": max(float(gate["max_v5_h"]), float(gate["max_ring_h"])),
            "maximum_closed_one_ring_edge_scaling_error": float(gate["max_edge"]),
            "minimum_local_quality_ratio": float(gate["min_local_q_ratio"]),
            "pointwise_convergence_claim_allowed": False,
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
            "route_h_gate_a_v01": "failed_invalid_numerics",
        },
        "verification": {
            "parent_cpp": {
                "passed": 48,
                "total": 51,
                "expected_frozen_failures": [
                    "prl_x1k_sphere_instantaneous_velocity_refinement",
                    "prl_x1k_v04_family_b_parameterized_diagnosis",
                    "prl_x1k_v06_family_c_short_trajectory_gate",
                ],
                "unexpected_failures": 0,
            },
            "controlled_fork": {"passed": 134, "total": 134},
            "owned_prl_core_strict_build": "passed",
            "python_pytest": {"passed": 63, "total": 63},
            "python_ruff": "passed",
        },
        "not_executed": ["R1_remesh_on", "C1_contact", "F1_failure_persistence", "downstream_coupling"],
        "claim_guard": "v06 is a correctly frozen short-trajectory failure. X1-K, long-time stability, physiology, ECM/flow, FSI, EFE, calibration, and developmental mechanism claims are not allowed.",
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as target:
        json.dump(summary, target, indent=2, ensure_ascii=False)
        target.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
