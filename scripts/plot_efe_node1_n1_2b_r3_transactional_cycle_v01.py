from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402


BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
RESULT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v02_20260820"
)
SIGNALS = (
    ("axial_shortening", "Axial shortening", "fraction"),
    (
        "maximum_discrete_interface_traction",
        "Maximum interface traction",
        "model units",
    ),
    ("total_stored_energy", "Total stored energy", "model units"),
    ("ecm_internal_z_norm", r"ECM internal state $\|Z\|$", "model units"),
)
COLORS = {2: "#7a7a7a", 3: "#4c78a8", 4: "#d55e42"}


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_timeseries(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            {
                key: float(value)
                for key, value in row.items()
                if key != "passed"
            }
            for row in csv.DictReader(stream)
        ]


def boundary_faces(tetrahedra: np.ndarray) -> np.ndarray:
    face_map: dict[tuple[int, int, int], tuple[np.ndarray, int]] = {}
    for tetrahedron in np.asarray(tetrahedra, dtype=np.int64):
        local_faces = (
            tetrahedron[[0, 1, 2]],
            tetrahedron[[0, 1, 3]],
            tetrahedron[[0, 2, 3]],
            tetrahedron[[1, 2, 3]],
        )
        for face in local_faces:
            key = tuple(sorted(int(value) for value in face))
            if key in face_map:
                stored, count = face_map[key]
                face_map[key] = (stored, count + 1)
            else:
                face_map[key] = (face.copy(), 1)
    return np.asarray(
        [face for face, count in face_map.values() if count == 1],
        dtype=np.int64,
    )


def transaction_iterations(cycle_index: int) -> np.ndarray:
    values: list[int] = []
    for step_index in range(1, 17):
        transaction = read_json(
            RESULT
            / f"cycle_{cycle_index:02d}"
            / f"step_{step_index:03d}"
            / "transaction_summary.json"
        )
        values.append(int(transaction["parent_sample"]["coupling_iterations"]))
    return np.asarray(values, dtype=np.int64)


def plot_cycle_diagnostic() -> tuple[Path, Path, Path]:
    samples = {
        2: read_timeseries(BASELINE_CASE / "cycle_02/cycle_timeseries.csv"),
        3: read_timeseries(RESULT / "cycle_03/cycle_timeseries.csv"),
        4: read_timeseries(RESULT / "cycle_04/cycle_timeseries.csv"),
    }
    summaries = {
        3: read_json(RESULT / "cycle_03/cycle_summary.json"),
        4: read_json(RESULT / "cycle_04/cycle_summary.json"),
    }
    figure, axes = plt.subplots(2, 3, figsize=(17, 9.5))
    for panel_index, (signal, title, units) in enumerate(SIGNALS):
        ax = axes.flat[panel_index]
        for cycle_index in (2, 3, 4):
            phase = [row["t_over_T"] for row in samples[cycle_index]]
            values = [row[signal] for row in samples[cycle_index]]
            ax.plot(
                phase,
                values,
                marker="o",
                markersize=3.5,
                linewidth=1.8,
                color=COLORS[cycle_index],
                label=f"Cycle {cycle_index}",
            )
        ax.set_title(f"{chr(65 + panel_index)}  {title}")
        ax.set_xlabel(r"Phase $t/T$")
        ax.set_ylabel(units)
        ax.grid(alpha=0.22)
        if panel_index == 0:
            ax.legend(frameon=False)

    ax = axes[1, 1]
    metric_labels = ["Shortening", "Traction", "Energy", r"$\|Z\|$", "End $Z$"]
    values_23 = [
        float(summaries[3]["waveform_normalized_l2"][key])
        for key, _, _ in SIGNALS
    ] + [float(summaries[3]["cycle_end_internal_z_relative_difference"])]
    values_34 = [
        float(summaries[4]["waveform_normalized_l2"][key])
        for key, _, _ in SIGNALS
    ] + [float(summaries[4]["cycle_end_internal_z_relative_difference"])]
    x_positions = np.arange(len(metric_labels), dtype=np.float64)
    width = 0.36
    ax.bar(
        x_positions - width / 2,
        values_23,
        width,
        color=COLORS[3],
        label="Cycle 2→3",
    )
    ax.bar(
        x_positions + width / 2,
        values_34,
        width,
        color=COLORS[4],
        label="Cycle 3→4",
    )
    ax.axhline(1.0e-3, color="black", linestyle=":", linewidth=2, label="Gate")
    ax.set_yscale("log")
    ax.set_xticks(x_positions, metric_labels)
    ax.set_ylabel("Symmetric normalized difference")
    ax.set_title("E  Preregistered cycle-stability gates")
    ax.grid(axis="y", alpha=0.22)
    ax.legend(frameon=False, fontsize=9)

    ax = axes[1, 2]
    phases = np.arange(1, 17, dtype=np.float64) / 16.0
    for cycle_index in (3, 4):
        ax.plot(
            phases,
            transaction_iterations(cycle_index),
            marker="o",
            linewidth=1.8,
            color=COLORS[cycle_index],
            label=f"Cycle {cycle_index}",
        )
    ax.axhline(12, color="black", linestyle=":", label="Maximum allowed")
    ax.set_xlabel(r"Phase $t/T$")
    ax.set_ylabel("Picard iterations per accepted step")
    ax.set_ylim(0, 12.8)
    ax.set_yticks(np.arange(0, 13, 2))
    ax.set_title("F  Transaction-worker effort")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)

    figure.suptitle(
        "N1-2b-r3: mechanics nearly repeats, but ECM memory remains transient",
        fontsize=19,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.012,
        "All 32 time-step transactions passed. Cycle 3→4 fails the registered "
        "limit-cycle gate because the viscoelastic internal state remains 2–3% apart.",
        ha="center",
        fontsize=11.5,
    )
    figure.tight_layout(rect=(0, 0.045, 1, 0.94))
    png_path = RESULT / "n1_2b_r3_cycle_stability_diagnostic_v01.png"
    svg_path = RESULT / "n1_2b_r3_cycle_stability_diagnostic_v01.svg"
    figure.savefig(png_path, dpi=220)
    figure.savefig(svg_path)
    plt.close(figure)

    derived = {
        "schema_version": "efe_node1_n1_2b_r3_derived_v01",
        "cycle_2_to_3": {
            "waveform_normalized_l2": summaries[3]["waveform_normalized_l2"],
            "cycle_end_internal_z_relative_difference": summaries[3][
                "cycle_end_internal_z_relative_difference"
            ],
        },
        "cycle_3_to_4": {
            "waveform_normalized_l2": summaries[4]["waveform_normalized_l2"],
            "cycle_end_internal_z_relative_difference": summaries[4][
                "cycle_end_internal_z_relative_difference"
            ],
        },
        "cycle_tolerance": 1.0e-3,
        "accepted_transaction_count": 32,
        "cycle_3_iterations": transaction_iterations(3).tolist(),
        "cycle_4_iterations": transaction_iterations(4).tolist(),
        "claim": (
            "The deformation and stored-energy waveforms are nearly periodic, "
            "whereas the cardiac-jelly internal variable remains transient."
        ),
    }
    derived_path = RESULT / "n1_2b_r3_derived_v01.json"
    derived_path.write_text(json.dumps(derived, indent=2), encoding="utf-8")
    return png_path, svg_path, derived_path


def plot_cycle_four_states() -> tuple[Path, Path]:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    with np.load(RESULT / "cycle_04/cycle_states.npz") as states:
        myocyte_states = np.asarray(states["myocyte_vertices"], dtype=np.float64)
        ecm_states = np.asarray(states["ecm_vertices"], dtype=np.float64)
        endocardial_states = np.asarray(
            states["endocardial_vertices"], dtype=np.float64
        )
    ecm_faces = boundary_faces(model.ecm_reference.tetrahedra)
    snapshot_indices = (0, 8, 16)
    snapshot_titles = (
        r"A  Start, $t/T=0$",
        r"B  Peak activation, $t/T=0.5$",
        r"C  End, $t/T=1$",
    )
    all_vertices = np.concatenate(
        (
            myocyte_states[list(snapshot_indices)].reshape(-1, 3),
            ecm_states[list(snapshot_indices)].reshape(-1, 3),
            endocardial_states[list(snapshot_indices)].reshape(-1, 3),
        ),
        axis=0,
    )
    lower = np.min(all_vertices, axis=0)
    upper = np.max(all_vertices, axis=0)
    center = 0.5 * (lower + upper)
    span = upper - lower
    padded_span = 1.08 * span
    figure = plt.figure(figsize=(17, 5.2))
    for panel_index, (state_index, title) in enumerate(
        zip(snapshot_indices, snapshot_titles, strict=True), start=1
    ):
        ax = figure.add_subplot(1, 3, panel_index, projection="3d")
        ecm_collection = Poly3DCollection(
            ecm_states[state_index][ecm_faces],
            facecolor="#e0ad46",
            edgecolor="#9b762a",
            linewidth=0.18,
            alpha=0.15,
        )
        ax.add_collection3d(ecm_collection)
        myocyte_collection = Poly3DCollection(
            myocyte_states[state_index][model.myocyte.faces],
            facecolor="#c84b44",
            edgecolor="#7f2825",
            linewidth=0.28,
            alpha=0.82,
        )
        ax.add_collection3d(myocyte_collection)
        endocardial_collection = Poly3DCollection(
            endocardial_states[state_index][model.endocardium.faces],
            facecolor="#42a6b8",
            edgecolor="#236b78",
            linewidth=0.28,
            alpha=0.75,
        )
        ax.add_collection3d(endocardial_collection)
        ax.set_xlim(
            center[0] - padded_span[0] / 2,
            center[0] + padded_span[0] / 2,
        )
        ax.set_ylim(
            center[1] - padded_span[1] / 2,
            center[1] + padded_span[1] / 2,
        )
        ax.set_zlim(
            center[2] - padded_span[2] / 2,
            center[2] + padded_span[2] / 2,
        )
        ax.set_box_aspect(tuple(padded_span))
        ax.view_init(elev=20, azim=-58)
        ax.set_axis_off()
        ax.set_title(title, fontsize=14, pad=2)
    legend_handles = (
        Patch(facecolor="#c84b44", label="Myocyte layer"),
        Patch(facecolor="#e0ad46", alpha=0.4, label="3D viscoelastic ECM"),
        Patch(facecolor="#42a6b8", label="Endocardial layer"),
    )
    figure.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=11,
    )
    figure.suptitle(
        "Cycle 4 three-dimensional cell–ECM states",
        fontsize=19,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.055,
        "The outer cell layer shortens at peak activation while the enlarged "
        "volumetric cardiac-jelly mesh transmits deformation to the inner layer.",
        ha="center",
        fontsize=11,
    )
    figure.tight_layout(rect=(0, 0.11, 1, 0.91))
    png_path = RESULT / "n1_2b_r3_cycle4_3d_states_v01.png"
    svg_path = RESULT / "n1_2b_r3_cycle4_3d_states_v01.svg"
    figure.savefig(png_path, dpi=220)
    figure.savefig(svg_path)
    plt.close(figure)
    return png_path, svg_path


def main() -> None:
    diagnostic_png, diagnostic_svg, derived_path = plot_cycle_diagnostic()
    states_png, states_svg = plot_cycle_four_states()
    manifest = {
        "schema_version": "efe_node1_n1_2b_r3_figure_manifest_v01",
        "source_artifacts": [
            str(BASELINE_CASE / "cycle_02/cycle_timeseries.csv"),
            str(RESULT / "summary.json"),
            str(RESULT / "cycle_03/cycle_timeseries.csv"),
            str(RESULT / "cycle_03/cycle_summary.json"),
            str(RESULT / "cycle_04/cycle_timeseries.csv"),
            str(RESULT / "cycle_04/cycle_summary.json"),
            str(RESULT / "cycle_04/cycle_states.npz"),
        ],
        "derived_summary": str(derived_path),
        "figure_files": [
            str(diagnostic_png),
            str(diagnostic_svg),
            str(states_png),
            str(states_svg),
        ],
        "claim": (
            "All transactional steps passed, but the fourth cycle remains "
            "outside the preregistered limit-cycle gate because ECM memory "
            "has not converged."
        ),
    }
    manifest_path = RESULT / "n1_2b_r3_figure_manifest_v01.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
