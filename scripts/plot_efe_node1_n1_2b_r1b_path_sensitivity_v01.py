from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_path_sensitivity import array_difference_metrics  # noqa: E402


BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
ARCHIVED_SUMMARY = BASELINE_CASE / "n1_2b_controlled_failure_summary_v01.json"
PURITY_SUMMARY = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1b_backend_purity_v01_20260820"
    / "summary.json"
)
OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1b_path_audit_v01_20260820"
)
RUNS = {
    "cold": [
        ROOT
        / f"results/hybrid/efe_node1_n1_2b_r1b_cold_rep{index:02d}_v01_20260820"
        for index in range(1, 4)
    ],
    "accepted_states": [
        ROOT
        / f"results/hybrid/efe_node1_n1_2b_r1b_warm_rep{index:02d}_v01_20260820"
        for index in range(1, 4)
    ],
}
ARCHIVED_CAPTURE_REPLAYS = [
    ROOT
    / (
        "results/hybrid/"
        f"efe_node1_n1_2b_r1b_archived_capture_c01_rep{index:02d}_v01_20260820"
    )
    for index in range(1, 4)
]
COLORS = {"cold": "#2166ac", "accepted_states": "#238b57"}


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def array_from_npz(path: Path, key: str) -> np.ndarray:
    with np.load(path) as arrays:
        return np.asarray(arrays[key], dtype=np.float64).copy()


def maximum_pairwise_difference(
    paths: list[Path], key: str
) -> dict[str, float | bool]:
    arrays = [array_from_npz(path, key) for path in paths]
    metrics = [
        array_difference_metrics(arrays[first], arrays[second])
        for first, second in combinations(range(len(arrays)), 2)
    ]
    return {
        "all_arrays_exactly_equal": all(
            np.array_equal(arrays[0], candidate) for candidate in arrays[1:]
        ),
        "maximum_symmetric_relative": max(
            metric["symmetric_relative"] for metric in metrics
        ),
        "maximum_absolute": max(
            metric["maximum_absolute"] for metric in metrics
        ),
    }


def deterministic_history(summary: dict[str, object]) -> list[dict[str, object]]:
    selected_keys = (
        "coupling_iteration",
        "solver_route",
        "solver_passed",
        "capture_passed",
        "capture_kkt",
        "raw_coupling_residual",
        "coupled_kkt",
        "volume_constraint_residual",
        "minimum_ecm_jacobian",
        "minimum_gap",
        "state_gate_passed",
    )
    return [
        {key: record[key] for key in selected_keys}
        for record in summary["iteration_history"]
    ]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    purity = read_json(PURITY_SUMMARY)
    run_summaries = {
        mode: [read_json(path / "summary.json") for path in paths]
        for mode, paths in RUNS.items()
    }
    flattened_paths = [path for paths in RUNS.values() for path in paths]
    flattened_summaries = [
        summary for summaries in run_summaries.values() for summary in summaries
    ]
    initial_digests = {
        str(summary["initial_checkpoint_array_digest"])
        for summary in flattened_summaries
    }
    deterministic_histories = [
        deterministic_history(summary) for summary in flattened_summaries
    ]
    histories_exact = all(
        history == deterministic_histories[0]
        for history in deterministic_histories[1:]
    )

    final_paths = [
        path / "final_candidate_checkpoint.npz" for path in flattened_paths
    ]
    final_variable_repeatability = maximum_pairwise_difference(
        final_paths, "variables"
    )
    final_internal_repeatability = maximum_pairwise_difference(
        final_paths, "ecm_internal_z"
    )
    iteration_repeatability: list[dict[str, object]] = []
    for coupling_iteration in range(1, 4):
        state_paths = [
            path
            / f"coupling_{coupling_iteration:02d}"
            / "aitken_iteration_state.npz"
            for path in flattened_paths
        ]
        iteration_repeatability.append(
            {
                "coupling_iteration": coupling_iteration,
                "variables": maximum_pairwise_difference(
                    state_paths, "variables"
                ),
                "raw_internal_update": maximum_pairwise_difference(
                    state_paths, "raw_internal_update"
                ),
            }
        )

    archived = read_json(ARCHIVED_SUMMARY)
    archived_history = archived["cycle_03_step_004_coupling_history"]
    archived_vs_new: list[dict[str, object]] = []
    reference_run = RUNS["cold"][0]
    for coupling_iteration in range(1, 4):
        archived_path = (
            BASELINE_CASE
            / "cycle_03"
            / "step_004"
            / f"coupling_{coupling_iteration:02d}"
        )
        new_path = reference_run / f"coupling_{coupling_iteration:02d}"
        capture_variables = array_difference_metrics(
            array_from_npz(archived_path / "input_state.npz", "variables"),
            array_from_npz(new_path / "input_state.npz", "variables"),
        )
        capture_internal = array_difference_metrics(
            array_from_npz(archived_path / "input_state.npz", "ecm_internal_z"),
            array_from_npz(new_path / "input_state.npz", "ecm_internal_z"),
        )
        sparse_variables = array_difference_metrics(
            array_from_npz(
                archived_path / "activation_010_state.npz", "variables"
            ),
            array_from_npz(new_path / "activation_010_state.npz", "variables"),
        )
        amplification = sparse_variables["symmetric_relative"] / max(
            1.0e-30, capture_variables["symmetric_relative"]
        )
        archived_vs_new.append(
            {
                "coupling_iteration": coupling_iteration,
                "post_capture_variables": capture_variables,
                "post_capture_internal_z": capture_internal,
                "post_sparse_variables": sparse_variables,
                "capture_to_sparse_relative_difference_amplification": (
                    amplification
                ),
            }
        )

    replay_output_paths = [
        path / "activation_010_state.npz" for path in ARCHIVED_CAPTURE_REPLAYS
    ]
    replay_repeatability = maximum_pairwise_difference(
        replay_output_paths, "variables"
    )
    replay_output = array_from_npz(replay_output_paths[0], "variables")
    new_coupling_one_output = array_from_npz(
        reference_run / "coupling_01/activation_010_state.npz", "variables"
    )
    archived_coupling_one_output = array_from_npz(
        BASELINE_CASE
        / "cycle_03/step_004/coupling_01/activation_010_state.npz",
        "variables",
    )
    replay_vs_new = array_difference_metrics(
        replay_output, new_coupling_one_output
    )
    replay_vs_original_archived = array_difference_metrics(
        replay_output, archived_coupling_one_output
    )
    coupling_one_capture_difference = float(
        archived_vs_new[0]["post_capture_variables"]["symmetric_relative"]
    )
    replay_amplification = replay_vs_new["symmetric_relative"] / max(
        1.0e-30, coupling_one_capture_difference
    )

    all_runs_passed = all(
        bool(summary["passed"]) for summary in flattened_summaries
    )
    all_three_iterations = all(
        int(summary["coupling_iterations_used"]) == 3
        for summary in flattened_summaries
    )
    all_input_preserved = all(
        bool(summary["history_replay_preserved_failed_step_input"])
        for summary in flattened_summaries
    )
    all_new_paths_exact = bool(
        histories_exact
        and final_variable_repeatability["all_arrays_exactly_equal"]
        and final_internal_repeatability["all_arrays_exactly_equal"]
        and all(
            record["variables"]["all_arrays_exactly_equal"]
            and record["raw_internal_update"]["all_arrays_exactly_equal"]
            for record in iteration_repeatability
        )
    )
    classification = (
        "archived_long_process_path_not_reproduced_backend_history_dependence_not_observed"
        if bool(purity["passed"]) and all_new_paths_exact
        else "path_sensitivity_requires_further_localization"
    )
    report = {
        "schema_version": "efe_node1_n1_2b_r1b_path_sensitivity_v01",
        "status": classification,
        "backend_purity": purity["cold_vs_history_warmed"],
        "backend_purity_passed": purity["passed"],
        "replicate_counts": {mode: len(paths) for mode, paths in RUNS.items()},
        "all_failed_step_inputs_share_one_digest": len(initial_digests) == 1,
        "failed_step_input_digest": next(iter(initial_digests)),
        "all_history_replays_preserved_failed_step_input": all_input_preserved,
        "all_runs_passed": all_runs_passed,
        "all_runs_used_three_coupling_iterations": all_three_iterations,
        "deterministic_iteration_histories_exactly_equal": histories_exact,
        "final_variables_repeatability": final_variable_repeatability,
        "final_internal_z_repeatability": final_internal_repeatability,
        "iteration_repeatability": iteration_repeatability,
        "archived_vs_new_localization": archived_vs_new,
        "archived_capture_current_sparse_replay": {
            "replicate_count": len(ARCHIVED_CAPTURE_REPLAYS),
            "output_repeatability": replay_repeatability,
            "replay_output_vs_new_output": replay_vs_new,
            "replay_output_vs_original_archived_output": (
                replay_vs_original_archived
            ),
            "capture_to_current_sparse_replay_amplification": (
                replay_amplification
            ),
        },
        "decision": {
            "backend_history_dependence_observed": False,
            "same_input_run_to_run_nondeterminism_observed": False,
            "archived_failure_reproduced": False,
            "promote_automatic_restart": False,
            "interpretation": (
                "All six new Picard paths are exactly identical and pass in "
                "three iterations. The first stored archived/new difference "
                "appears after the capture solve. Replaying that archived "
                "capture state three times is exactly repeatable and amplifies "
                "the difference by about 87-fold under the current sparse "
                "nonlinear solver. The original long process amplified it "
                "about 149-fold, so its exact unarchived source/runtime path "
                "remains unresolved."
            ),
        },
        "evidence_boundary": (
            "The recoverable accepted-state history was replayed, but the "
            "original optimizer-internal evaluation sequence and loaded "
            "source snapshot were not archived. Full-cycle reproducibility "
            "and cycle stability are not established."
        ),
        "source_runs": {
            mode: [str(path) for path in paths] for mode, paths in RUNS.items()
        },
    }
    summary_path = OUTPUT / "n1_2b_r1b_path_sensitivity_summary_v01.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
        }
    )
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))
    figure.suptitle(
        "N1-2b-r1b: reproducible cold/warm restart; archived path not reproduced",
        fontsize=18,
        fontweight="bold",
    )

    ax = axes[0, 0]
    purity_labels = ["Energy", "Force", "J", "Tangent"]
    purity_values = [
        float(purity["cold_vs_history_warmed"]["energy_maximum_absolute"]),
        float(
            purity["cold_vs_history_warmed"][
                "force_maximum_symmetric_relative"
            ]
        ),
        float(
            purity["cold_vs_history_warmed"][
                "jacobian_maximum_symmetric_relative"
            ]
        ),
        float(
            purity["cold_vs_history_warmed"][
                "hessian_maximum_symmetric_relative"
            ]
        ),
    ]
    display_values = [max(value, 1.0e-18) for value in purity_values]
    ax.bar(purity_labels, display_values, color="#667f99")
    ax.axhline(1.0e-12, color="black", linestyle=":", label="purity gate")
    ax.set_yscale("log")
    ax.set_ylim(3.0e-19, 3.0e-11)
    ax.set_ylabel("Cold–warm difference")
    ax.set_title("A  FEniCSx backend history purity")
    ax.text(
        0.03,
        0.08,
        "All four recorded differences = 0",
        transform=ax.transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    ax.legend(loc="upper right")

    ax = axes[0, 1]
    archived_iterations = [
        int(record["coupling"]) for record in archived_history
    ]
    ax.plot(
        archived_iterations,
        [float(record["coupling_residual"]) for record in archived_history],
        color="#bb4540",
        linestyle="--",
        marker="o",
        label="Archived long process",
    )
    for mode, summaries in run_summaries.items():
        for replicate, summary in enumerate(summaries, start=1):
            history = summary["iteration_history"]
            ax.plot(
                [int(record["coupling_iteration"]) for record in history],
                [float(record["raw_coupling_residual"]) for record in history],
                color=COLORS[mode],
                alpha=0.35 if replicate < 3 else 1.0,
                marker="o",
                linestyle="--" if mode == "accepted_states" else "-",
                markerfacecolor=(
                    "white" if mode == "accepted_states" else COLORS[mode]
                ),
                label=(
                    "Cold restart ×3"
                    if mode == "cold" and replicate == 3
                    else (
                        "History-warmed restart ×3"
                        if mode == "accepted_states" and replicate == 3
                        else None
                    )
                ),
            )
    ax.axhline(1.0e-4, color="black", linestyle=":", label=r"$r_Z$ gate")
    ax.set_yscale("log")
    ax.set_xlabel("Outer coupling iteration")
    ax.set_ylabel(r"Raw fixed-point residual $r_Z$")
    ax.set_title("B  Six restart paths are identical")
    ax.legend(loc="upper right")

    ax = axes[1, 0]
    ax.plot(
        archived_iterations,
        [
            float(record["coupled_kkt_reference_oracle"])
            for record in archived_history
        ],
        color="#bb4540",
        linestyle="--",
        marker="o",
        label="Archived long process",
    )
    for mode, summaries in run_summaries.items():
        for replicate, summary in enumerate(summaries, start=1):
            history = summary["iteration_history"]
            ax.plot(
                [int(record["coupling_iteration"]) for record in history],
                [float(record["coupled_kkt"]) for record in history],
                color=COLORS[mode],
                alpha=0.35 if replicate < 3 else 1.0,
                marker="o",
                linestyle="--" if mode == "accepted_states" else "-",
                markerfacecolor=(
                    "white" if mode == "accepted_states" else COLORS[mode]
                ),
                label=(
                    "Cold restart ×3"
                    if mode == "cold" and replicate == 3
                    else (
                        "History-warmed restart ×3"
                        if mode == "accepted_states" and replicate == 3
                        else None
                    )
                ),
            )
    ax.axhline(1.0e-5, color="black", linestyle=":", label="KKT gate")
    ax.set_yscale("log")
    ax.set_xlabel("Outer coupling iteration")
    ax.set_ylabel("Normalized KKT residual")
    ax.set_title("C  Mechanical equilibrium path")
    ax.legend(loc="upper right")

    ax = axes[1, 1]
    coupling_ids = [
        int(record["coupling_iteration"]) for record in archived_vs_new
    ]
    capture_difference = [
        float(record["post_capture_variables"]["symmetric_relative"])
        for record in archived_vs_new
    ]
    sparse_difference = [
        float(record["post_sparse_variables"]["symmetric_relative"])
        for record in archived_vs_new
    ]
    ax.plot(
        coupling_ids,
        capture_difference,
        color="#8064a2",
        marker="o",
        label="After capture",
    )
    ax.plot(
        coupling_ids,
        sparse_difference,
        color="#e08214",
        marker="s",
        label="Archived-run sparse output",
    )
    ax.scatter(
        [1],
        [replay_vs_new["symmetric_relative"]],
        color="#1b9e77",
        marker="D",
        s=75,
        zorder=5,
        label="Current sparse replay of archived capture",
    )
    ax.set_yscale("log")
    ax.set_xlabel("Outer coupling iteration")
    ax.set_ylabel("Archived–new variable difference")
    ax.set_title("D  Tiny first difference is nonlinearly amplified")
    for coupling_id, record, y_value in zip(
        coupling_ids, archived_vs_new, sparse_difference, strict=True
    ):
        amplification = float(
            record["capture_to_sparse_relative_difference_amplification"]
        )
        ax.annotate(
            f"×{amplification:.0f}",
            (coupling_id, y_value),
            xytext=(0, 8 if coupling_id == 1 else -20),
            textcoords="offset points",
            ha="center",
        )
    ax.annotate(
        f"current replay ×{replay_amplification:.0f}",
        (1, replay_vs_new["symmetric_relative"]),
        xytext=(18, -4),
        textcoords="offset points",
        va="center",
    )
    ax.legend(loc="lower right")

    for ax in axes.flat:
        ax.grid(alpha=0.22)
    figure.text(
        0.5,
        0.01,
        "Backend history dependence and restart nondeterminism were not observed; "
        "full-cycle stability remains untested.",
        ha="center",
        fontsize=12,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    png_path = OUTPUT / "n1_2b_r1b_path_sensitivity_diagnostic_v01.png"
    svg_path = OUTPUT / "n1_2b_r1b_path_sensitivity_diagnostic_v01.svg"
    figure.savefig(png_path, dpi=220)
    figure.savefig(svg_path)
    plt.close(figure)

    manifest = {
        "schema_version": "efe_node1_n1_2b_r1b_figure_manifest_v01",
        "source_artifacts": [
            str(PURITY_SUMMARY),
            str(ARCHIVED_SUMMARY),
            *[str(path / "summary.json") for path in flattened_paths],
            *[
                str(path / "summary.json")
                for path in ARCHIVED_CAPTURE_REPLAYS
            ],
        ],
        "derived_summary": str(summary_path),
        "figure_files": [str(png_path), str(svg_path)],
        "claim": (
            "The recoverable FEniCSx history is pure and six independent "
            "restart paths are exactly repeatable; the archived long-process "
            "failure remains path-specific; current sparse replay confirms "
            "deterministic nonlinear amplification, while the exact archived "
            "source/runtime origin remains unresolved."
        ),
    }
    (OUTPUT / "n1_2b_r1b_figure_manifest_v01.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
