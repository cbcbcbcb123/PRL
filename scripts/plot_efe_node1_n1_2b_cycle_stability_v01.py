from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import (  # noqa: E402
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    _kkt_audit,
    build_exact_volume_coordinates,
    unpack_exact_volume_variables,
)
from route_h.ecm_finite_strain import (  # noqa: E402
    deformation_gradient,
    relax_internal_variable_exact,
)


DEFAULT_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
GATE = 1.0e-3
COUPLING_GATE = 1.0e-4
KKT_GATE = 1.0e-5
COLORS = ("#657786", "#1769aa")


def read_cycle(case_path: Path, cycle: int) -> list[dict[str, float]]:
    path = case_path / f"cycle_{cycle:02d}" / "cycle_timeseries.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            {
                key: (
                    1.0
                    if value == "True"
                    else 0.0
                    if value == "False"
                    else float(value)
                )
                for key, value in row.items()
            }
            for row in csv.DictReader(stream)
        ]


def values(rows: list[dict[str, float]], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in rows], dtype=np.float64)


def relative_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(
        np.linalg.norm(first - second)
        / max(
            1.0e-12,
            float(np.linalg.norm(first)),
            float(np.linalg.norm(second)),
        )
    )


def update_internal_state(
    model,
    ecm_vertices: np.ndarray,
    previous_internal_z: np.ndarray,
    time_step: float,
) -> np.ndarray:
    updated = np.empty_like(previous_internal_z)
    for tetrahedron_id, tetrahedron in enumerate(
        model.ecm_reference.tetrahedra
    ):
        deformation = deformation_gradient(
            ecm_vertices[tetrahedron],
            model.ecm_reference.dm_inverse[tetrahedron_id],
        )
        updated[tetrahedron_id] = relax_internal_variable_exact(
            deformation,
            previous_internal_z[tetrahedron_id],
            time_step,
            mu_ve=model.mu_ve,
            eta_ve=model.eta_ve,
        )
    return updated


def chosen_solver_artifact(coupling_path: Path) -> tuple[Path, Path, str]:
    for relative, route in (
        ("fallback_residual", "extended_capture_then_df_sane"),
        ("fallback_capture", "extended_capture"),
    ):
        candidate = coupling_path / relative
        if (candidate / "summary.json").exists():
            return (
                candidate / "summary.json",
                candidate / "activation_010_state.npz",
                route,
            )
    return (
        coupling_path / "summary.json",
        coupling_path / "activation_010_state.npz",
        "standard_krylov",
    )


def analyze_failed_coupling(case_path: Path) -> list[dict[str, object]]:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    coordinates = build_exact_volume_coordinates(model)
    accepted = np.load(case_path / "cycle_03/accepted_step_003.npz")
    previous_internal_z = np.asarray(
        accepted["ecm_internal_z"], dtype=np.float64
    )
    step_path = case_path / "cycle_03/step_004"
    records: list[dict[str, object]] = []
    for coupling in range(1, 13):
        coupling_path = step_path / f"coupling_{coupling:02d}"
        input_arrays = np.load(coupling_path / "input_state.npz")
        internal_guess = np.asarray(
            input_arrays["ecm_internal_z"], dtype=np.float64
        )
        report_path, state_path, route = chosen_solver_artifact(coupling_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        state_arrays = np.load(state_path)
        variables = np.asarray(state_arrays["variables"], dtype=np.float64)
        state = unpack_exact_volume_variables(model, coordinates, variables)
        candidate_internal = update_internal_state(
            model, state[1], previous_internal_z, 1.0 / 16.0
        )
        coupling_residual = relative_difference(
            candidate_internal, internal_guess
        )
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=0.1,
            pressure=0.0,
            wss_command=np.zeros(3, dtype=np.float64),
            ecm_internal_z=candidate_internal,
            reject_penetration=False,
        )
        _, coupled_kkt = _kkt_audit(
            model,
            coordinates,
            evaluation,
            state[0],
            state[2],
            np.zeros_like(coordinates.reference_flat),
        )
        records.append(
            {
                "coupling": coupling,
                "route": route,
                "solver_report_passed": bool(report["passed"]),
                "solver_report_kkt": float(
                    report["normalized_kkt_residual"]
                ),
                "coupled_kkt_reference_oracle": coupled_kkt,
                "coupling_residual": coupling_residual,
                "minimum_ecm_jacobian": (
                    evaluation.minimum_ecm_jacobian
                ),
                "minimum_gap": evaluation.minimum_gap,
                "residual_safeguard_triggered": bool(
                    report["residual_safeguard_triggered"]
                ),
            }
        )
    return records


def style_axis(axis: plt.Axes, panel: str, title: str) -> None:
    axis.set_title(f"{panel}  {title}", loc="left", fontweight="bold")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.18, linewidth=0.7)


def add_direction_markers(
    axis: plt.Axes, x: np.ndarray, y: np.ndarray, color: str
) -> None:
    for start in (3, 11):
        axis.annotate(
            "",
            xy=(x[start + 1], y[start + 1]),
            xytext=(x[start], y[start]),
            arrowprops={"arrowstyle": "->", "color": color, "lw": 1.2},
        )


def plot_cycle_overlay(
    case_path: Path,
    cycles: list[list[dict[str, float]]],
    cycle_two_summary: dict[str, object],
) -> list[Path]:
    figure, axes = plt.subplots(2, 3, figsize=(14.4, 8.4))
    figure.suptitle(
        "N1-2b T16: two completed fully coupled cycles",
        fontsize=15,
        fontweight="bold",
    )
    phases = [values(rows, "t_over_T") for rows in cycles]
    axes[0, 0].plot(
        phases[0], values(cycles[0], "activation"), color="#222222", lw=2
    )
    style_axis(axes[0, 0], "A", "Prescribed activation")
    axes[0, 0].set_ylabel("Activation")

    panels = (
        ("axial_shortening", "Axial shortening", "Shortening (%)", 100.0),
        (
            "maximum_discrete_interface_traction",
            "Peak interface traction",
            "Traction (model units)",
            1.0,
        ),
        (
            "total_stored_energy",
            "Total stored energy",
            "Energy (model units)",
            1.0,
        ),
        ("ecm_internal_z_norm", "ECM history norm", r"$\Vert Z\Vert_F$", 1.0),
    )
    for axis, panel, specification in zip(
        axes.flat[1:5], "BCDE", panels, strict=True
    ):
        key, title, ylabel, scale = specification
        for cycle_index, rows in enumerate(cycles, start=1):
            axis.plot(
                phases[cycle_index - 1],
                scale * values(rows, key),
                color=COLORS[cycle_index - 1],
                lw=2.0,
                marker="o",
                ms=3.5,
                label=f"Cycle {cycle_index}",
            )
        style_axis(axis, panel, title)
        axis.set_ylabel(ylabel)
        axis.legend(frameon=False, fontsize=8)

    differences = cycle_two_summary["waveform_normalized_l2"]
    labels = ("Shortening", "Traction", "Energy", r"$\Vert Z\Vert$", "End $Z$")
    metrics = np.asarray(
        [
            differences["axial_shortening"],
            differences["maximum_discrete_interface_traction"],
            differences["total_stored_energy"],
            differences["ecm_internal_z_norm"],
            cycle_two_summary["cycle_end_internal_z_relative_difference"],
        ],
        dtype=np.float64,
    )
    colors = ["#2f8f5b" if metric <= GATE else "#c84a4a" for metric in metrics]
    axis = axes[1, 2]
    axis.bar(np.arange(len(metrics)), metrics, color=colors, width=0.72)
    axis.axhline(GATE, color="#111111", ls="--", lw=1.3, label=r"Gate $10^{-3}$")
    axis.set_yscale("log")
    axis.set_xticks(np.arange(len(metrics)), labels, rotation=20, ha="right")
    axis.set_ylabel("Symmetric normalized difference")
    axis.legend(frameon=False, fontsize=8)
    style_axis(axis, "F", "Cycle 1 -> 2 convergence gates")

    for axis in axes.flat[:5]:
        axis.set_xlabel(r"Phase $t/T$")
        axis.set_xlim(0.0, 1.0)
    figure.text(
        0.5,
        0.012,
        "Geometry and energy are nearly repeatable, but traction and the viscoelastic history state are not yet periodic.",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.035, 1, 0.955))
    outputs = [
        case_path / "n1_2b_cycle_overlay_v01.png",
        case_path / "n1_2b_cycle_overlay_v01.svg",
    ]
    figure.savefig(outputs[0], dpi=220, bbox_inches="tight")
    figure.savefig(outputs[1], bbox_inches="tight")
    plt.close(figure)
    return outputs


def plot_hysteresis(
    case_path: Path, cycles: list[list[dict[str, float]]]
) -> list[Path]:
    figure, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))
    figure.suptitle(
        "N1-2b dynamic loops before periodic closure",
        fontsize=15,
        fontweight="bold",
    )
    for cycle_index, rows in enumerate(cycles, start=1):
        shortening = 100.0 * values(rows, "axial_shortening")
        traction = values(rows, "maximum_discrete_interface_traction")
        activation = values(rows, "activation")
        internal_norm = values(rows, "ecm_internal_z_norm")
        color = COLORS[cycle_index - 1]
        axes[0].plot(
            shortening,
            traction,
            color=color,
            lw=2,
            marker="o",
            ms=3.5,
            label=f"Cycle {cycle_index}",
        )
        axes[1].plot(
            activation,
            internal_norm,
            color=color,
            lw=2,
            marker="o",
            ms=3.5,
            label=f"Cycle {cycle_index}",
        )
        add_direction_markers(axes[0], shortening, traction, color)
        add_direction_markers(axes[1], activation, internal_norm, color)
        for axis, x, y in (
            (axes[0], shortening, traction),
            (axes[1], activation, internal_norm),
        ):
            axis.scatter(x[0], y[0], s=45, facecolors="white", edgecolors=color, zorder=4)
            axis.scatter(x[8], y[8], s=40, marker="D", color=color, zorder=4)
            axis.scatter(x[-1], y[-1], s=45, marker="s", color=color, zorder=4)
    style_axis(axes[0], "A", "Mechanical hysteresis")
    axes[0].set_xlabel("Axial shortening (%)")
    axes[0].set_ylabel("Peak interface traction (model units)")
    style_axis(axes[1], "B", "ECM memory loop")
    axes[1].set_xlabel("Activation")
    axes[1].set_ylabel(r"$\Vert Z\Vert_F$")
    for axis in axes:
        axis.legend(frameon=False)
    figure.text(
        0.5,
        0.015,
        "Open circle: cycle start; diamond: peak activation; square: cycle end. Arrows mark time direction.",
        ha="center",
        fontsize=9.5,
    )
    figure.tight_layout(rect=(0, 0.045, 1, 0.94))
    outputs = [
        case_path / "n1_2b_hysteresis_v01.png",
        case_path / "n1_2b_hysteresis_v01.svg",
    ]
    figure.savefig(outputs[0], dpi=220, bbox_inches="tight")
    figure.savefig(outputs[1], bbox_inches="tight")
    plt.close(figure)
    return outputs


def plot_failure(
    case_path: Path, records: list[dict[str, object]]
) -> list[Path]:
    coupling = np.asarray([record["coupling"] for record in records])
    solver_kkt = np.asarray([record["solver_report_kkt"] for record in records])
    coupled_kkt = np.asarray(
        [record["coupled_kkt_reference_oracle"] for record in records]
    )
    coupling_residual = np.asarray(
        [record["coupling_residual"] for record in records]
    )
    figure, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))
    figure.suptitle(
        "N1-2b controlled stop: cycle 3, step 4 (activation = 0.10)",
        fontsize=15,
        fontweight="bold",
    )
    axes[0].semilogy(
        coupling,
        solver_kkt,
        color="#888888",
        marker="o",
        lw=1.6,
        label="Equilibrium report KKT",
    )
    axes[0].semilogy(
        coupling,
        coupled_kkt,
        color="#b63f3f",
        marker="s",
        lw=2,
        label="KKT after SLS update (oracle)",
    )
    axes[0].axhline(KKT_GATE, color="#111111", ls="--", lw=1.3, label=r"KKT gate $10^{-5}$")
    axes[0].set_ylabel("Normalized KKT residual")
    axes[0].legend(frameon=False, fontsize=8)
    style_axis(axes[0], "A", "Mechanical equilibrium")

    axes[1].semilogy(
        coupling,
        coupling_residual,
        color="#1769aa",
        marker="o",
        lw=2,
    )
    axes[1].axhline(
        COUPLING_GATE,
        color="#111111",
        ls="--",
        lw=1.3,
        label=r"$Z$-geometry gate $10^{-4}$",
    )
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].set_ylabel(r"Fixed-point residual $r_Z$")
    style_axis(axes[1], "B", "Partitioned coupling")
    for axis in axes:
        axis.set_xlabel("Outer coupling iteration")
        axis.set_xticks(np.arange(1, 13))
        for location in (8, 12):
            axis.axvspan(location - 0.25, location + 0.25, color="#efb366", alpha=0.22)
    figure.text(
        0.5,
        0.012,
        r"At iteration 12, KKT passes but $r_Z=2.62\times10^{-4}$ fails; the stop is a coupling-convergence failure, not ECM inversion.",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.94))
    outputs = [
        case_path / "n1_2b_failure_diagnostic_v01.png",
        case_path / "n1_2b_failure_diagnostic_v01.svg",
    ]
    figure.savefig(outputs[0], dpi=220, bbox_inches="tight")
    figure.savefig(outputs[1], bbox_inches="tight")
    plt.close(figure)
    return outputs


def main() -> None:
    case_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_CASE
    cycles = [read_cycle(case_path, cycle) for cycle in (1, 2)]
    cycle_two_summary = json.loads(
        (case_path / "cycle_02/cycle_summary.json").read_text(encoding="utf-8")
    )
    failure_records = analyze_failed_coupling(case_path)
    final_record = failure_records[-1]
    overlay_outputs = plot_cycle_overlay(case_path, cycles, cycle_two_summary)
    hysteresis_outputs = plot_hysteresis(case_path, cycles)
    failure_outputs = plot_failure(case_path, failure_records)

    failure_summary = {
        "schema_version": "efe_node1_n1_2b_controlled_failure_v01",
        "status": "failed_cycle_03_step_004_coupling_gate",
        "completed_fully_coupled_cycles": 2,
        "incomplete_cycle": 3,
        "accepted_steps_in_incomplete_cycle": 3,
        "failed_step": 4,
        "failed_activation": 0.1,
        "maximum_coupling_iterations": 12,
        "failure_gate": "coupling_residual",
        "coupling_residual_gate": COUPLING_GATE,
        "final_coupling_residual": final_record["coupling_residual"],
        "kkt_gate": KKT_GATE,
        "final_coupled_kkt_reference_oracle": final_record[
            "coupled_kkt_reference_oracle"
        ],
        "final_minimum_ecm_jacobian": final_record[
            "minimum_ecm_jacobian"
        ],
        "final_minimum_gap": final_record["minimum_gap"],
        "cycle_01_to_02_waveform_normalized_l2": cycle_two_summary[
            "waveform_normalized_l2"
        ],
        "cycle_01_to_02_end_internal_z_relative_difference": (
            cycle_two_summary["cycle_end_internal_z_relative_difference"]
        ),
        "cycle_03_step_004_coupling_history": failure_records,
        "passed_n1_2b_cycle_stability": False,
        "evidence_boundary": (
            "Two complete cycles are valid dynamic trajectories, but they do "
            "not satisfy the preregistered periodicity gate. Cycle 3 stopped "
            "at an unpassed within-step Z-geometry fixed point."
        ),
    }
    summary_path = case_path / "n1_2b_controlled_failure_summary_v01.json"
    summary_path.write_text(
        json.dumps(failure_summary, indent=2), encoding="utf-8"
    )
    manifest = {
        "schema_version": "efe_node1_n1_2b_stage_figure_manifest_v01",
        "source_cycle_directories": [
            str(case_path / "cycle_01"),
            str(case_path / "cycle_02"),
        ],
        "failure_source": str(case_path / "cycle_03/step_004"),
        "figures": [
            {
                "claim": "cycle-overlaid registered waveforms and convergence gates",
                "files": [str(path) for path in overlay_outputs],
            },
            {
                "claim": "mechanical and viscoelastic loops before periodic closure",
                "files": [str(path) for path in hysteresis_outputs],
            },
            {
                "claim": "controlled stop caused by the Z-geometry fixed-point gate",
                "files": [str(path) for path in failure_outputs],
            },
        ],
        "derived_summary": str(summary_path),
    }
    manifest_path = case_path / "n1_2b_stage_figure_manifest_v01.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
