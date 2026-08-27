from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
AITKEN_RESULT = (
    ROOT / "results/hybrid/efe_node1_n1_2b_r1a_aitken_pilot_v01_20260820"
)
PICARD_RESULT = (
    ROOT / "results/hybrid/efe_node1_n1_2b_r1a_picard_control_v01_20260820"
)
OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_2b_r1a_comparison_v01_20260820"
)
KKT_GATE = 1.0e-5
COUPLING_GATE = 1.0e-4


def relative_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(
        np.linalg.norm(first - second)
        / max(
            1.0e-12,
            float(np.linalg.norm(first)),
            float(np.linalg.norm(second)),
        )
    )


def scalar_relative_difference(first: float, second: float) -> float:
    return abs(first - second) / max(1.0e-12, abs(first), abs(second))


def style_axis(axis: plt.Axes, panel: str, title: str) -> None:
    axis.set_title(f"{panel}  {title}", loc="left", fontweight="bold")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.18, linewidth=0.7)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    archived = json.loads(
        (ARCHIVED_CASE / "n1_2b_controlled_failure_summary_v01.json").read_text(
            encoding="utf-8"
        )
    )
    aitken = json.loads((AITKEN_RESULT / "summary.json").read_text("utf-8"))
    picard = json.loads((PICARD_RESULT / "summary.json").read_text("utf-8"))

    archived_history = archived["cycle_03_step_004_coupling_history"]
    histories = {
        "Archived Picard": {
            "iteration": np.asarray(
                [record["coupling"] for record in archived_history]
            ),
            "rz": np.asarray(
                [record["coupling_residual"] for record in archived_history]
            ),
            "kkt": np.asarray(
                [
                    record["coupled_kkt_reference_oracle"]
                    for record in archived_history
                ]
            ),
            "color": "#b54444",
            "style": "--",
            "passed": False,
        },
        "Fresh Picard": {
            "iteration": np.asarray(
                [
                    record["coupling_iteration"]
                    for record in picard["iteration_history"]
                ]
            ),
            "rz": np.asarray(
                [
                    record["raw_coupling_residual"]
                    for record in picard["iteration_history"]
                ]
            ),
            "kkt": np.asarray(
                [record["coupled_kkt"] for record in picard["iteration_history"]]
            ),
            "color": "#2f8f5b",
            "style": "-",
            "passed": True,
        },
        "Aitken": {
            "iteration": np.asarray(
                [
                    record["coupling_iteration"]
                    for record in aitken["iteration_history"]
                ]
            ),
            "rz": np.asarray(
                [
                    record["raw_coupling_residual"]
                    for record in aitken["iteration_history"]
                ]
            ),
            "kkt": np.asarray(
                [record["coupled_kkt"] for record in aitken["iteration_history"]]
            ),
            "color": "#1769aa",
            "style": "-",
            "passed": True,
        },
    }

    aitken_checkpoint = np.load(AITKEN_RESULT / "final_candidate_checkpoint.npz")
    picard_checkpoint = np.load(PICARD_RESULT / "final_candidate_checkpoint.npz")
    state_differences = {
        "Variables": relative_difference(
            aitken_checkpoint["variables"], picard_checkpoint["variables"]
        ),
        r"Full $Z$": relative_difference(
            aitken_checkpoint["ecm_internal_z"],
            picard_checkpoint["ecm_internal_z"],
        ),
        "Shortening": scalar_relative_difference(
            aitken["final_sample"]["axial_shortening"],
            picard["final_sample"]["axial_shortening"],
        ),
        "Traction": scalar_relative_difference(
            aitken["final_sample"]["maximum_discrete_interface_traction"],
            picard["final_sample"]["maximum_discrete_interface_traction"],
        ),
        "Energy": scalar_relative_difference(
            aitken["final_sample"]["total_stored_energy"],
            picard["final_sample"]["total_stored_energy"],
        ),
    }

    first_two_match = all(
        np.array_equal(
            np.asarray(
                [
                    aitken["iteration_history"][index][key]
                    for key in ("raw_coupling_residual", "coupled_kkt")
                ]
            ),
            np.asarray(
                [
                    picard["iteration_history"][index][key]
                    for key in ("raw_coupling_residual", "coupled_kkt")
                ]
            ),
        )
        for index in (0, 1)
    )
    comparison = {
        "schema_version": "efe_node1_n1_2b_r1a_comparison_v01",
        "status": (
            "completed_both_fresh_branches_passed_aitken_not_superior_"
            "archived_picard_path_sensitive"
        ),
        "archived_picard": {
            "passed": False,
            "iterations": 12,
            "final_raw_coupling_residual": archived[
                "final_coupling_residual"
            ],
            "final_coupled_kkt": archived[
                "final_coupled_kkt_reference_oracle"
            ],
        },
        "fresh_picard": {
            "passed": bool(picard["passed"]),
            "iterations": picard["coupling_iterations_used"],
            "final_raw_coupling_residual": picard[
                "final_raw_coupling_residual"
            ],
            "final_coupled_kkt": picard["final_coupled_kkt"],
            "raw_status_label_erratum": (
                "The generated raw summary used the Aitken success label, "
                "but its algorithm field and all iteration data correctly "
                "identify the unrelaxed Picard control. The source label was "
                "fixed after this run."
            ),
        },
        "aitken": {
            "passed": bool(aitken["passed"]),
            "iterations": aitken["coupling_iterations_used"],
            "final_raw_coupling_residual": aitken[
                "final_raw_coupling_residual"
            ],
            "final_coupled_kkt": aitken["final_coupled_kkt"],
            "relaxation_factors": [
                record["relaxation_factor"]
                for record in aitken["iteration_history"]
            ],
        },
        "fresh_branches_identical_before_relaxation_divergence": first_two_match,
        "aitken_vs_fresh_picard_final_state_relative_differences": (
            state_differences
        ),
        "decision": {
            "promote_aitken_to_production": False,
            "reason": (
                "Fresh Picard reached the same fixed point in three outer "
                "iterations, while Aitken required four. The archived failure "
                "is sensitive to the cold-checkpoint restart path."
            ),
        },
        "evidence_boundary": (
            "The failed step is locally solvable after a cold checkpoint "
            "restart. This does not establish full-cycle reproducibility or "
            "cycle stability."
        ),
    }
    summary_path = OUTPUT / "n1_2b_r1a_comparison_summary_v01.json"
    summary_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    figure, axes = plt.subplots(2, 2, figsize=(13.2, 8.8))
    figure.suptitle(
        "N1-2b-r1a: cold-restart path sensitivity, not an Aitken advantage",
        fontsize=15,
        fontweight="bold",
    )
    for label, history in histories.items():
        for axis, key in ((axes[0, 0], "rz"), (axes[0, 1], "kkt")):
            axis.semilogy(
                history["iteration"],
                history[key],
                color=history["color"],
                ls=history["style"],
                marker="o",
                lw=2,
                ms=5,
                label=label,
            )
            if history["passed"]:
                axis.scatter(
                    history["iteration"][-1],
                    history[key][-1],
                    marker="*",
                    s=120,
                    color=history["color"],
                    zorder=4,
                )
    axes[0, 0].axhline(
        COUPLING_GATE, color="#111111", ls=":", lw=1.4, label=r"$r_Z$ gate"
    )
    axes[0, 0].set_ylabel(r"Unrelaxed fixed-point residual $r_Z$")
    style_axis(axes[0, 0], "A", "Original fixed-point gate")
    axes[0, 1].axhline(
        KKT_GATE, color="#111111", ls=":", lw=1.4, label="KKT gate"
    )
    axes[0, 1].set_ylabel("Normalized KKT residual")
    style_axis(axes[0, 1], "B", "Mechanical equilibrium gate")
    for axis in axes[0]:
        axis.set_xlabel("Outer coupling iteration")
        axis.set_xticks(np.arange(1, 13))
        axis.legend(frameon=False, fontsize=8)

    aitken_iterations = np.asarray(
        [record["coupling_iteration"] for record in aitken["iteration_history"]]
    )
    aitken_factors = np.asarray(
        [
            np.nan
            if record["relaxation_factor"] is None
            else record["relaxation_factor"]
            for record in aitken["iteration_history"]
        ]
    )
    axes[1, 0].plot(
        aitken_iterations,
        aitken_factors,
        color="#1769aa",
        marker="o",
        lw=2,
    )
    axes[1, 0].axhline(1.0, color="#888888", ls="--", lw=1.2)
    axes[1, 0].set_ylim(0.0, 1.08)
    axes[1, 0].set_xticks(aitken_iterations)
    axes[1, 0].set_xlabel("Outer coupling iteration")
    axes[1, 0].set_ylabel("Applied relaxation factor")
    style_axis(axes[1, 0], "C", "Aitken path")
    axes[1, 0].text(
        0.04,
        0.08,
        "Fresh Picard: 3 iterations\nAitken: 4 iterations",
        transform=axes[1, 0].transAxes,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#cccccc"},
    )

    labels = list(state_differences)
    metrics = np.asarray(list(state_differences.values()))
    axes[1, 1].bar(
        np.arange(len(metrics)), metrics, color="#5f7f9d", width=0.72
    )
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_xticks(
        np.arange(len(metrics)), labels, rotation=18, ha="right"
    )
    axes[1, 1].set_ylabel("Symmetric relative difference")
    style_axis(axes[1, 1], "D", "Same fixed point after restart")

    figure.text(
        0.5,
        0.012,
        "Both fresh branches pass the unchanged raw-map gates; Picard is faster, so Aitken is not promoted.",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.035, 1, 0.95))
    png_path = OUTPUT / "n1_2b_r1a_picard_aitken_comparison_v01.png"
    svg_path = OUTPUT / "n1_2b_r1a_picard_aitken_comparison_v01.svg"
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    manifest = {
        "schema_version": "efe_node1_n1_2b_r1a_figure_manifest_v01",
        "source_artifacts": [
            str(
                ARCHIVED_CASE / "n1_2b_controlled_failure_summary_v01.json"
            ),
            str(AITKEN_RESULT / "summary.json"),
            str(PICARD_RESULT / "summary.json"),
        ],
        "derived_summary": str(summary_path),
        "figure_files": [str(png_path), str(svg_path)],
        "claim": (
            "The failed step is cold-restart path sensitive; bounded Aitken "
            "does not outperform the contemporaneous Picard control."
        ),
    }
    (OUTPUT / "n1_2b_r1a_figure_manifest_v01.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
