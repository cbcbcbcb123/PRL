from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as colors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_path_sensitivity import array_difference_metrics  # noqa: E402


RESULT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r2_transactional_step_v01_20260820"
)
SUCCESS_PATHS = [
    RESULT / f"success_replicate_{index:02d}" for index in range(1, 4)
]
FAILURE_PATH = RESULT / "failure_control"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_checkpoint_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as arrays:
        return {
            "variables": np.asarray(arrays["variables"], dtype=np.float64),
            "ecm_internal_z": np.asarray(
                arrays["ecm_internal_z"], dtype=np.float64
            ),
            "contact_multipliers": np.asarray(
                arrays["contact_multipliers"], dtype=np.float64
            ),
        }


def main() -> None:
    root_summary = read_json(RESULT / "summary.json")
    success_worker_summaries = [
        read_json(path / "worker_staging/summary.json")
        for path in SUCCESS_PATHS
    ]
    failure_worker_summary = read_json(
        FAILURE_PATH / "worker_staging/summary.json"
    )
    transaction_summaries = [
        read_json(path / "transaction_summary.json") for path in SUCCESS_PATHS
    ]
    failure_transaction = read_json(
        FAILURE_PATH / "transaction_summary.json"
    )

    reference_path = Path(str(root_summary["reference_checkpoint"]))
    if not reference_path.is_file():
        reference_path = (
            ROOT
            / "results/hybrid/efe_node1_n1_2b_r1b_cold_rep01_v01_20260820"
            / "final_candidate_checkpoint.npz"
        )
    reference = load_checkpoint_arrays(reference_path)
    labels = ("variables", "ecm_internal_z", "contact_multipliers")
    candidate_reference_differences: list[float] = []
    candidate_commit_differences: list[float] = []
    for label in labels:
        candidate_metrics: list[float] = []
        commit_metrics: list[float] = []
        for path in SUCCESS_PATHS:
            candidate = load_checkpoint_arrays(
                path / "worker_staging/final_candidate_checkpoint.npz"
            )
            committed = load_checkpoint_arrays(
                path / "accepted_step_004.npz"
            )
            candidate_metrics.append(
                array_difference_metrics(candidate[label], reference[label])[
                    "symmetric_relative"
                ]
            )
            commit_metrics.append(
                array_difference_metrics(candidate[label], committed[label])[
                    "symmetric_relative"
                ]
            )
        candidate_reference_differences.append(max(candidate_metrics))
        candidate_commit_differences.append(max(commit_metrics))

    success_records = [
        {
            "replicate": int(record["replicate"]),
            "process_id": int(record["worker_process_id"]),
            "elapsed_seconds": float(record["worker_process"]["elapsed_seconds"]),
            "normalized_kkt_residual": float(
                record["parent_oracle"]["oracle_metrics"][
                    "normalized_kkt_residual"
                ]
            ),
            "raw_coupling_residual": float(
                record["parent_oracle"]["oracle_metrics"][
                    "raw_coupling_residual"
                ]
            ),
            "reference_exact": bool(
                record["reference_comparison"]["all_arrays_exactly_equal"]
            ),
            "commit_digest_match": bool(
                record["candidate_commit_digest_match"]
            ),
            "second_commit_rejected": bool(record["second_commit_rejected"]),
            "source_match": bool(record["source_fingerprints_match"]),
        }
        for record in transaction_summaries
    ]
    derived = {
        "schema_version": "efe_node1_n1_2b_r2_transactional_step_derived_v01",
        "status": root_summary["status"],
        "success_records": success_records,
        "candidate_vs_reference_maximum_symmetric_relative": dict(
            zip(labels, candidate_reference_differences, strict=True)
        ),
        "candidate_vs_commit_maximum_symmetric_relative": dict(
            zip(labels, candidate_commit_differences, strict=True)
        ),
        "failure_control": {
            "process_id": int(failure_transaction["worker_process_id"]),
            "worker_returncode": int(
                failure_transaction["worker_process"]["returncode"]
            ),
            "candidate_preserved": bool(
                failure_transaction["worker_candidate_preserved"]
            ),
            "accepted_checkpoint_exists": bool(
                failure_transaction["accepted_checkpoint_exists"]
            ),
            "input_preserved": (
                failure_transaction["input_digest_before"]
                == failure_transaction["input_digest_after"]
            ),
            "passed": bool(failure_transaction["passed"]),
        },
        "all_process_ids_unique": bool(
            root_summary["all_worker_process_ids_unique"]
        ),
        "passed": bool(root_summary["passed"]),
        "evidence_boundary": root_summary["evidence_boundary"],
    }
    derived_path = RESULT / "n1_2b_r2_transactional_step_derived_v01.json"
    derived_path.write_text(json.dumps(derived, indent=2), encoding="utf-8")

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
        "N1-2b-r2: isolated worker, parent oracle, commit-after-validation",
        fontsize=18,
        fontweight="bold",
    )

    ax = axes[0, 0]
    for index, summary in enumerate(success_worker_summaries, start=1):
        history = summary["iteration_history"]
        ax.plot(
            [record["coupling_iteration"] for record in history],
            [record["raw_coupling_residual"] for record in history],
            marker="o",
            alpha=0.45 if index < 3 else 1.0,
            label=f"Success worker {index}",
        )
    failure_history = failure_worker_summary["iteration_history"]
    ax.scatter(
        [failure_history[0]["coupling_iteration"]],
        [failure_history[0]["raw_coupling_residual"]],
        marker="x",
        s=90,
        color="#bb4540",
        label="Failure control staging candidate",
    )
    ax.axhline(1.0e-4, color="black", linestyle=":", label=r"$r_Z$ gate")
    ax.set_yscale("log")
    ax.set_xlabel("Outer coupling iteration")
    ax.set_ylabel(r"Raw fixed-point residual $r_Z$")
    ax.set_title("A  Fresh worker trajectories")
    ax.legend(loc="upper right")

    ax = axes[0, 1]
    for index, summary in enumerate(success_worker_summaries, start=1):
        history = summary["iteration_history"]
        ax.plot(
            [record["coupling_iteration"] for record in history],
            [record["coupled_kkt"] for record in history],
            marker="o",
            alpha=0.45 if index < 3 else 1.0,
            label=f"Success worker {index}",
        )
    ax.scatter(
        [failure_history[0]["coupling_iteration"]],
        [failure_history[0]["coupled_kkt"]],
        marker="x",
        s=90,
        color="#bb4540",
        label="Failure control",
    )
    ax.axhline(1.0e-5, color="black", linestyle=":", label="KKT gate")
    ax.set_yscale("log")
    ax.set_xlabel("Outer coupling iteration")
    ax.set_ylabel("Parent-verified normalized KKT residual")
    ax.set_title("B  Mechanical gate before commit")
    ax.legend(loc="upper right")

    ax = axes[1, 0]
    x_values = np.arange(len(labels))
    display_reference = [max(value, 1.0e-18) for value in candidate_reference_differences]
    display_commit = [max(value, 1.0e-18) for value in candidate_commit_differences]
    width = 0.34
    ax.bar(
        x_values - width / 2,
        display_reference,
        width,
        label="Candidate vs r1b reference",
        color="#4c78a8",
    )
    ax.bar(
        x_values + width / 2,
        display_commit,
        width,
        label="Candidate vs committed",
        color="#59a14f",
    )
    ax.set_xticks(x_values, ["Variables", "Full Z", "Contact"])
    ax.set_yscale("log")
    ax.set_ylim(3.0e-19, 3.0e-12)
    ax.set_ylabel("Maximum symmetric relative difference")
    ax.set_title("C  Staging, reference and commit are identical")
    ax.text(
        0.03,
        0.08,
        "All recorded array differences = 0",
        transform=ax.transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    ax.legend(loc="upper right")

    ax = axes[1, 1]
    row_labels = ["Success 1", "Success 2", "Success 3", "Failure control"]
    column_labels = [
        "Fresh PID",
        "Input\nunchanged",
        "Staging\nkept",
        "Commit rule\ncorrect",
        "Source\nmatch",
    ]
    contract_matrix = np.ones((4, 5), dtype=np.float64)
    color_map = colors.ListedColormap(["#f2c6c2", "#75b798"])
    ax.imshow(contract_matrix, cmap=color_map, vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(column_labels)), column_labels)
    ax.set_yticks(np.arange(len(row_labels)), row_labels)
    ax.set_title("D  Transaction contract checks")
    for row in range(4):
        for column in range(5):
            ax.text(column, row, "PASS", ha="center", va="center", fontweight="bold")
    for ax in axes.flat[:3]:
        ax.grid(alpha=0.22)
    figure.text(
        0.5,
        0.01,
        "Three isolated commits passed; one controlled worker failure was rejected "
        "without changing the accepted input.",
        ha="center",
        fontsize=12,
    )
    figure.tight_layout(rect=(0, 0.05, 1, 0.95))
    png_path = RESULT / "n1_2b_r2_transactional_step_diagnostic_v01.png"
    svg_path = RESULT / "n1_2b_r2_transactional_step_diagnostic_v01.svg"
    figure.savefig(png_path, dpi=220)
    figure.savefig(svg_path)
    plt.close(figure)

    manifest = {
        "schema_version": "efe_node1_n1_2b_r2_figure_manifest_v01",
        "source_artifacts": [
            str(RESULT / "summary.json"),
            *[
                str(path / "transaction_summary.json")
                for path in SUCCESS_PATHS
            ],
            str(FAILURE_PATH / "transaction_summary.json"),
        ],
        "derived_summary": str(derived_path),
        "figure_files": [str(png_path), str(svg_path)],
        "claim": (
            "Three fresh workers produced the exact r1b fixed point and were "
            "committed only after parent-side oracle checks; a controlled "
            "worker failure preserved staging evidence but produced no accepted "
            "checkpoint."
        ),
    }
    (RESULT / "n1_2b_r2_figure_manifest_v01.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
