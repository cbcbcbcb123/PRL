"""Independent frozen-gate verifier for Z1-MYO-STRIP-CYCLE-AMP-A v01."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_cycle_amp_v01_20260913"
LEGACY_ROOT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_myo_strip_l5_a_v01_20260913" / "raw"
CASE_SPECS = (
    ("CENTER_EPS020", "CENTER", 0.02, "new"),
    ("CENTER_EPS050", "CENTER", 0.05, "reused"),
    ("CENTER_EPS100", "CENTER", 0.10, "new"),
    ("SYNC_EPS020", "SYNC", 0.02, "new"),
    ("SYNC_EPS050", "SYNC", 0.05, "reused"),
    ("SYNC_EPS100", "SYNC", 0.10, "new"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_directory(output: Path, case: str, pattern: str, source: str) -> Path:
    if source == "reused":
        return LEGACY_ROOT / pattern
    return output / "raw" / case


def finite_rows(rows: list[dict[str, str]], columns: tuple[str, ...]) -> bool:
    try:
        return all(math.isfinite(float(row[column])) for row in rows for column in columns)
    except (KeyError, TypeError, ValueError):
        return False


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_case(directory: Path, expected_pattern: str, expected_strain: float) -> dict[str, Any]:
    kernel = read_json(directory / "kernel_metrics.json")
    states = read_csv(directory / "state_metrics.csv")
    nodes = read_csv(directory / "nodes.csv")
    faces = read_csv(directory / "faces.csv")
    cells = read_csv(directory / "cell_metrics.csv")
    peak_state = max(states, key=lambda row: float(row["activation"]))
    peak_index = int(peak_state["snapshot_index"])
    peak_nodes = [row for row in nodes if int(row["snapshot_index"]) == peak_index]
    baseline_reaction = float(states[0]["end_reaction"])
    peak_reaction = float(peak_state["end_reaction"])
    active_increment = peak_reaction - baseline_reaction
    final_reaction = float(states[-1]["end_reaction"])
    recovery_error = abs(final_reaction - baseline_reaction)
    p0 = float(states[0]["mean_p_span"])
    q0 = float(states[0]["mean_q_span"])
    r0 = float(states[0]["mean_r_span"])
    p_peak = float(peak_state["mean_p_span"])
    q_peak = float(peak_state["mean_q_span"])
    r_peak = float(peak_state["mean_r_span"])

    node_counts: dict[tuple[int, int], int] = {}
    face_counts: dict[tuple[int, int], int] = {}
    for row in nodes:
        key = (int(row["snapshot_index"]), int(row["cell_id"]))
        node_counts[key] = node_counts.get(key, 0) + 1
    for row in faces:
        key = (int(row["snapshot_index"]), int(row["cell_id"]))
        face_counts[key] = face_counts.get(key, 0) + 1

    finite = finite_rows(
        nodes,
        (
            "x", "y", "z", "nodal_area", "curvature", "internal_pressure",
            "shape_traction", "contraction_traction", "adhesion_traction", "total_traction",
            "shape_fx", "shape_fy", "shape_fz", "contraction_fx", "contraction_fy",
            "contraction_fz", "adhesion_fx", "adhesion_fy", "adhesion_fz",
        ),
    ) and finite_rows(
        states,
        (
            "phase", "activation", "end_reaction", "mean_p_span", "mean_q_span", "mean_r_span",
            "max_volume_relative_error", "min_triangle_angle_deg", "max_fixed_displacement",
            "max_free_force", "junction_balance_residual", "passive_energy", "contraction_energy",
            "adhesion_energy",
        ),
    ) and finite_rows(cells, ("p_span", "q_span", "r_span", "area", "volume", "volume_relative_error"))

    contraction_values = [float(row["contraction_traction"]) for row in peak_nodes]
    adhesion_values = [float(row["adhesion_traction"]) for row in peak_nodes]
    return {
        "directory": str(directory.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "kernel_metadata_ok": (
            kernel.get("condition") == expected_pattern
            and abs(float(kernel.get("contraction_strain", -1.0)) - expected_strain) <= 1.0e-15
            and kernel.get("snapshot_count") == 9
            and kernel.get("requested_step") == 0.02
            and kernel.get("settle_steps") == 1000
            and kernel.get("ramp_steps_per_segment") == 50
            and kernel.get("hold_steps_per_segment") == 2000
        ),
        "finite": finite,
        "topology_ok": (
            len(node_counts) == 45
            and len(face_counts) == 45
            and set(node_counts.values()) == {162}
            and set(face_counts.values()) == {320}
        ),
        "baseline_reaction": baseline_reaction,
        "peak_reaction": peak_reaction,
        "active_increment": active_increment,
        "final_reaction": final_reaction,
        "recovery_error": recovery_error,
        "recovery_fraction": recovery_error / max(abs(active_increment), 1.0e-12),
        "peak_snapshot_index": peak_index,
        "peak_phase": float(peak_state["phase"]),
        "peak_activation": float(peak_state["activation"]),
        "peak_p_strain": p_peak / p0 - 1.0,
        "peak_q_strain": q_peak / q0 - 1.0,
        "peak_r_strain": r_peak / r0 - 1.0,
        "peak_long_axis_shortening": 1.0 - p_peak / p0,
        "max_saved_volume_error": max(
            float(kernel["maximum_volume_relative_error"]),
            max(float(row["max_volume_relative_error"]) for row in states),
        ),
        "min_saved_angle": min(
            float(kernel["minimum_triangle_angle_deg"]),
            min(float(row["min_triangle_angle_deg"]) for row in states),
        ),
        "max_fixed_displacement": max(
            float(kernel["maximum_fixed_displacement"]),
            max(float(row["max_fixed_displacement"]) for row in states),
        ),
        "max_saved_free_force": max(float(row["max_free_force"]) for row in states),
        "max_junction_balance": max(float(row["junction_balance_residual"]) for row in states),
        "max_work_relative_residual": float(kernel["maximum_work_relative_residual"]),
        "junction_count": int(kernel["junction_count"]),
        "peak_contraction_traction_max": max(contraction_values),
        "peak_contraction_traction_p95": percentile(contraction_values, 0.95),
        "peak_adhesion_traction_max": max(adhesion_values),
        "peak_adhesion_traction_p95": percentile(adhesion_values, 0.95),
    }


def gate(gate_id: str, description: str, value: Any, passed: bool) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "description": description,
        "value": value,
        "status": "passed" if passed else "failed",
    }


def verify(output: Path) -> dict[str, Any]:
    locations = {
        case: case_directory(output, case, pattern, source)
        for case, pattern, _, source in CASE_SPECS
    }
    required_names = ("kernel_metrics.json", "state_metrics.csv", "cell_metrics.csv", "nodes.csv", "faces.csv")
    missing = [
        str(directory / name)
        for directory in locations.values()
        for name in required_names
        if not (directory / name).is_file()
    ]
    if missing:
        return {
            "schema_version": 1,
            "stage": "Z1-MYO-STRIP-CYCLE-AMP-A",
            "status": "blocked",
            "missing": missing,
            "failed_gates": [],
            "gates": [],
        }

    summaries: dict[str, dict[str, Any]] = {}
    case_metadata: dict[str, dict[str, Any]] = {}
    for case, pattern, strain, source in CASE_SPECS:
        summaries[case] = summarize_case(locations[case], pattern, strain)
        case_metadata[case] = {"pattern": pattern, "strain": strain, "source": source}

    gates: list[dict[str, Any]] = []
    for case, summary in summaries.items():
        gates.extend(
            [
                gate(f"{case}_METADATA", "kernel metadata matches the frozen case", summary["kernel_metadata_ok"], summary["kernel_metadata_ok"]),
                gate(f"{case}_FINITE", "all saved geometry, field, state, and cell values are finite", summary["finite"], summary["finite"]),
                gate(f"{case}_TOPOLOGY", "five cells retain 162 nodes and 320 faces in nine states", summary["topology_ok"], summary["topology_ok"]),
                gate(f"{case}_VOLUME", "maximum relative volume error <= 0.02", summary["max_saved_volume_error"], summary["max_saved_volume_error"] <= 0.02),
                gate(f"{case}_ANGLE", "minimum triangle angle >= 15 deg", summary["min_saved_angle"], summary["min_saved_angle"] >= 15.0),
                gate(f"{case}_CLAMP", "maximum fixed-node displacement <= 1e-10", summary["max_fixed_displacement"], summary["max_fixed_displacement"] <= 1.0e-10),
                gate(f"{case}_SAVED_RESIDUAL", "maximum saved free-node force <= 1e-3", summary["max_saved_free_force"], summary["max_saved_free_force"] <= 1.0e-3),
                gate(f"{case}_WORK", "maximum substep work residual <= 1e-10", summary["max_work_relative_residual"], summary["max_work_relative_residual"] <= 1.0e-10),
                gate(f"{case}_LINK_BALANCE", "junction action-reaction residual <= 1e-12", summary["max_junction_balance"], summary["max_junction_balance"] <= 1.0e-12),
                gate(f"{case}_LINK_COUNT", "persistent junction-link count equals 28", summary["junction_count"], summary["junction_count"] == 28),
                gate(f"{case}_LONG_AXIS", "mean long-axis span does not increase at peak activation", summary["peak_p_strain"], summary["peak_p_strain"] <= 1.0e-4),
                gate(
                    f"{case}_TRANSVERSE",
                    "mean transverse or thickness span does not decrease at peak activation",
                    {"q": summary["peak_q_strain"], "r": summary["peak_r_strain"]},
                    summary["peak_q_strain"] >= -1.0e-4 or summary["peak_r_strain"] >= -1.0e-4,
                ),
                gate(f"{case}_RECOVERY", "end reaction recovers within 10 percent of active increment", summary["recovery_fraction"], summary["recovery_fraction"] <= 0.10),
            ]
        )

    for pattern in ("CENTER", "SYNC"):
        pattern_cases = [f"{pattern}_EPS020", f"{pattern}_EPS050", f"{pattern}_EPS100"]
        reactions = [summaries[name]["active_increment"] for name in pattern_cases]
        shortenings = [summaries[name]["peak_long_axis_shortening"] for name in pattern_cases]
        gates.append(gate(f"{pattern}_REACTION_MONOTONIC", "peak active reaction increases with contraction strain", reactions, reactions[0] < reactions[1] < reactions[2]))
        gates.append(gate(f"{pattern}_SHORTENING_MONOTONIC", "peak long-axis shortening increases with contraction strain", shortenings, shortenings[0] < shortenings[1] < shortenings[2]))

    for suffix in ("020", "050", "100"):
        center_value = summaries[f"CENTER_EPS{suffix}"]["active_increment"]
        sync_value = summaries[f"SYNC_EPS{suffix}"]["active_increment"]
        gates.append(
            gate(
                f"SYNC_GT_CENTER_EPS{suffix}",
                "five-cell synchronous activation produces more peak end reaction than center-only activation",
                {"center": center_value, "sync": sync_value},
                sync_value > center_value,
            )
        )

    failed = [item["gate_id"] for item in gates if item["status"] != "passed"]
    return {
        "schema_version": 1,
        "stage": "Z1-MYO-STRIP-CYCLE-AMP-A",
        "status": "passed_synthetic_activation_count_amplitude_response" if not failed else "failed",
        "physics_status": "passed" if not failed else "failed",
        "visualization_status": "not_evaluated_by_numerical_verifier",
        "experimental_comparison_status": "qualitative_consistency_only",
        "biological_validation_status": "blocked_data",
        "coordinate_semantics": "algorithmic_activation_phase_not_physiological_time",
        "failed_gates": failed,
        "gates": gates,
        "case_metadata": case_metadata,
        "case_values": summaries,
    }


def write_metrics(output: Path, verdict: dict[str, Any]) -> None:
    fields = (
        "case", "pattern", "contraction_strain", "source", "baseline_reaction", "peak_reaction",
        "active_increment", "recovery_error", "recovery_fraction", "peak_p_strain", "peak_q_strain",
        "peak_r_strain", "peak_long_axis_shortening", "peak_contraction_traction_max",
        "peak_contraction_traction_p95", "peak_adhesion_traction_max", "peak_adhesion_traction_p95",
        "max_saved_volume_error", "min_saved_angle", "max_saved_free_force", "max_fixed_displacement",
    )
    with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case, _, _, _ in CASE_SPECS:
            metadata = verdict["case_metadata"][case]
            values = verdict["case_values"][case]
            writer.writerow(
                {
                    "case": case,
                    "pattern": metadata["pattern"],
                    "contraction_strain": metadata["strain"],
                    "source": metadata["source"],
                    **{field: values[field] for field in fields if field in values},
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    verdict = verify(output)
    (output / "verdict.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if "case_values" in verdict:
        write_metrics(output, verdict)
    print(json.dumps({"status": verdict["status"], "failed_gates": verdict.get("failed_gates", [])}, ensure_ascii=False))
    return 0 if verdict["status"] == "passed_synthetic_activation_count_amplitude_response" else 1


if __name__ == "__main__":
    raise SystemExit(main())
