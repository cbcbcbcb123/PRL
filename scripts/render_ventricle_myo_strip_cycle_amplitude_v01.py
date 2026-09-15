"""Render static and animated solver evidence for the strip amplitude matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors, patches
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


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
PANEL_CASES = (
    ("CENTER_EPS020", "CENTER_EPS050", "CENTER_EPS100"),
    ("SYNC_EPS020", "SYNC_EPS050", "SYNC_EPS100"),
)
CELL_COLORS = ("#2d817c", "#48a09a", "#74bbb0", "#48a09a", "#2d817c")
AMPLITUDE_COLORS = {0.02: "#3f7fbf", 0.05: "#dc8434", 0.10: "#a93632"}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def case_directory(output: Path, case: str, pattern: str, source: str) -> Path:
    return LEGACY_ROOT / pattern if source == "reused" else output / "raw" / case


def load_case(output: Path, case: str, pattern: str, strain: float, source: str) -> dict[str, Any]:
    directory = case_directory(output, case, pattern, source)
    state_rows = read_csv(directory / "state_metrics.csv")
    node_rows = read_csv(directory / "nodes.csv")
    face_rows = read_csv(directory / "faces.csv")
    baseline_by_cell: dict[int, np.ndarray] = {}
    for cell_id in range(5):
        baseline = sorted(
            (
                row for row in node_rows
                if int(row["snapshot_index"]) == 0 and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        baseline_by_cell[cell_id] = np.array(
            [[float(row[axis]) for axis in ("x", "y", "z")] for row in baseline], dtype=float
        )

    snapshots: list[list[dict[str, Any]]] = []
    for snapshot_index in range(9):
        cells: list[dict[str, Any]] = []
        for cell_id in range(5):
            local_nodes = sorted(
                (
                    row for row in node_rows
                    if int(row["snapshot_index"]) == snapshot_index and int(row["cell_id"]) == cell_id
                ),
                key=lambda row: int(row["node_index"]),
            )
            points = np.array(
                [[float(row[axis]) for axis in ("x", "y", "z")] for row in local_nodes], dtype=float
            )
            triangles = np.array(
                [
                    [int(row[name]) for name in ("n1", "n2", "n3")]
                    for row in face_rows
                    if int(row["snapshot_index"]) == snapshot_index and int(row["cell_id"]) == cell_id
                ],
                dtype=int,
            )
            fields = {
                name: np.array([float(row[name]) for row in local_nodes], dtype=float)
                for name in ("contraction_traction", "adhesion_traction", "total_traction")
            }
            fields["displacement_magnitude"] = np.linalg.norm(points - baseline_by_cell[cell_id], axis=1)
            cells.append(
                {
                    "points": points,
                    "triangles": triangles,
                    "fields": fields,
                    "fixed": np.array([int(row["fixed"]) for row in local_nodes], dtype=bool),
                }
            )
        snapshots.append(cells)
    return {
        "case": case,
        "pattern": pattern,
        "strain": strain,
        "source": source,
        "states": state_rows,
        "snapshots": snapshots,
    }


def load_all_cases(output: Path) -> dict[str, dict[str, Any]]:
    return {
        case: load_case(output, case, pattern, strain, source)
        for case, pattern, strain, source in CASE_SPECS
    }


def coordinate_limits(cases: dict[str, dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    points = np.vstack(
        [cell["points"] for case in cases.values() for snapshot in case["snapshots"] for cell in snapshot]
    )
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    padding = np.array([0.018, 0.08, 0.08]) * np.maximum(upper - lower, 1.0)
    return lower - padding, upper + padding


def field_max(cases: dict[str, dict[str, Any]], field: str, peak_only: bool = False) -> float:
    values = []
    for case in cases.values():
        snapshots = [case["snapshots"][4]] if peak_only else case["snapshots"]
        for snapshot in snapshots:
            values.extend(float(value) for cell in snapshot for value in cell["fields"][field])
    observed = max(values) if values else 0.0
    return observed if observed > 1.0e-15 else 1.0e-15


def style_axis(axis: Any, limits: tuple[np.ndarray, np.ndarray]) -> None:
    lower, upper = limits
    axis.set_xlim(lower[0], upper[0])
    axis.set_ylim(lower[1], upper[1])
    axis.set_zlim(lower[2], upper[2])
    axis.set_box_aspect((5.4, 1.0, 0.82))
    axis.view_init(elev=23, azim=-67)
    axis.set_axis_off()


def add_mesh(
    axis: Any,
    cells: list[dict[str, Any]],
    limits: tuple[np.ndarray, np.ndarray],
    field: str | None = None,
    norm: colors.Normalize | None = None,
    cmap: str = "viridis",
    show_fixed: bool = False,
) -> None:
    mapper = ScalarMappable(norm=norm, cmap=cmap) if field is not None and norm is not None else None
    for cell_id, cell in enumerate(cells):
        polygons = cell["points"][cell["triangles"]]
        if mapper is None or field is None:
            face_colors: Any = CELL_COLORS[cell_id]
        else:
            node_values = cell["fields"][field]
            face_values = node_values[cell["triangles"]].mean(axis=1)
            face_colors = mapper.to_rgba(face_values)
        collection = Poly3DCollection(
            polygons,
            facecolors=face_colors,
            edgecolors=(0.10, 0.13, 0.15, 0.34),
            linewidths=0.18,
            alpha=0.98,
        )
        axis.add_collection3d(collection)
        if show_fixed and np.any(cell["fixed"]):
            fixed_points = cell["points"][cell["fixed"]]
            axis.scatter(
                fixed_points[:, 0], fixed_points[:, 1], fixed_points[:, 2],
                s=7, c="#20262b", depthshade=False,
            )
    style_axis(axis, limits)


def save_pair(figure: plt.Figure, directory: Path, stem: str, dpi: int = 180) -> None:
    figure.savefig(directory / f"{stem}.png", dpi=dpi, bbox_inches="tight")
    figure.savefig(directory / f"{stem}.svg", bbox_inches="tight")
    plt.close(figure)


def render_structure(directory: Path) -> None:
    figure, axis = plt.subplots(figsize=(15.4, 6.2))
    axis.set_xlim(0, 15.4)
    axis.set_ylim(0, 6.2)
    axis.axis("off")
    axis.text(0.25, 5.85, "MODEL STRUCTURE — activation count × contraction amplitude", fontsize=15, weight="bold")
    axis.text(0.25, 5.50, "Schematic only · both conditions use the same five-cell strip, junctions, and isometric end clamps", color="#59636d")
    centers = np.linspace(2.0, 13.3, 5)
    for row_index, (label, active_ids, y) in enumerate((("CENTER: one active cell", {2}, 3.85), ("SYNC: five active cells", set(range(5)), 1.65))):
        axis.text(0.2, y, label, ha="left", va="center", weight="bold", color="#273139")
        for cell_id, center in enumerate(centers):
            active = cell_id in active_ids
            ellipse = patches.Ellipse(
                (center, y), 2.25, 1.15,
                facecolor="#b43b34" if active else "#87b8b3",
                edgecolor="#71251f" if active else "#326f6b",
                linewidth=1.5,
            )
            axis.add_patch(ellipse)
            axis.text(center, y + 0.03, str(cell_id + 1), ha="center", va="center", color="white", weight="bold")
            if active:
                axis.annotate(
                    "", xy=(center + 0.63, y - 0.20), xytext=(center - 0.63, y - 0.20),
                    arrowprops={"arrowstyle": "<->", "color": "#5d1714", "lw": 1.7},
                )
        for left, right in zip(centers[:-1], centers[1:]):
            axis.plot([left + 1.07, right - 1.07], [y, y], color="#d48a20", lw=2.5)
        for x in (0.87, 14.43):
            axis.add_patch(patches.Rectangle((x - 0.11, y - 0.70), 0.22, 1.40, facecolor="#242b30"))
    axis.text(7.65, 0.38, "epsilon = 2%, 5%, 10% · a(phi)=sin²(pi phi) · phi is not physiological time", ha="center", color="#59636d")
    save_pair(figure, directory, "model_structure")


def render_peak_deformation(
    cases: dict[str, dict[str, Any]], directory: Path, limits: tuple[np.ndarray, np.ndarray]
) -> None:
    maximum = field_max(cases, "displacement_magnitude", peak_only=True)
    norm = colors.Normalize(vmin=0.0, vmax=maximum)
    mapper = ScalarMappable(norm=norm, cmap="viridis")
    figure = plt.figure(figsize=(16.0, 7.8))
    axes = []
    for row_index, case_row in enumerate(PANEL_CASES):
        for column_index, case_name in enumerate(case_row):
            axis = figure.add_subplot(2, 3, row_index * 3 + column_index + 1, projection="3d")
            axes.append(axis)
            case = cases[case_name]
            add_mesh(axis, case["snapshots"][4], limits, "displacement_magnitude", norm, "viridis", show_fixed=True)
            axis.set_title(
                f"{case['pattern']} · epsilon={100 * case['strain']:.0f}%",
                fontsize=10, pad=-2,
            )
    colorbar = figure.colorbar(mapper, ax=axes, fraction=0.017, pad=0.012, shrink=0.72, aspect=28)
    colorbar.set_label("node displacement from phase 0 (model length units)")
    figure.suptitle("Peak activation: actual deformation mesh with one shared displacement scale", fontsize=15, weight="bold", y=0.98)
    figure.text(0.5, 0.018, "Actual geometry, no deformation magnification · black dots mark fixed end-cap nodes", ha="center", color="#59636d")
    figure.subplots_adjust(left=0.005, right=0.91, top=0.91, bottom=0.07, hspace=0.02, wspace=0.01)
    save_pair(figure, directory, "peak_deformation_mesh_grid")


def render_peak_tractions(
    cases: dict[str, dict[str, Any]], directory: Path, limits: tuple[np.ndarray, np.ndarray]
) -> None:
    contraction_norm = colors.Normalize(vmin=0.0, vmax=field_max(cases, "contraction_traction", peak_only=True))
    adhesion_norm = colors.Normalize(vmin=0.0, vmax=field_max(cases, "adhesion_traction", peak_only=True))
    figure = plt.figure(figsize=(16.2, 13.0))
    contraction_axes = []
    adhesion_axes = []
    row_index = 0
    for pattern_row in PANEL_CASES:
        for field, norm, cmap, label in (
            ("contraction_traction", contraction_norm, "inferno", "intracellular contraction traction"),
            ("adhesion_traction", adhesion_norm, "YlOrBr", "junction adhesion traction"),
        ):
            for column_index, case_name in enumerate(pattern_row):
                axis = figure.add_subplot(4, 3, row_index * 3 + column_index + 1, projection="3d")
                case = cases[case_name]
                add_mesh(axis, case["snapshots"][4], limits, field, norm, cmap)
                if field == "contraction_traction":
                    contraction_axes.append(axis)
                else:
                    adhesion_axes.append(axis)
                axis.set_title(
                    f"{case['pattern']} · {label}\nepsilon={100 * case['strain']:.0f}%",
                    fontsize=9, pad=-1,
                )
            row_index += 1
    contraction_mapper = ScalarMappable(norm=contraction_norm, cmap="inferno")
    adhesion_mapper = ScalarMappable(norm=adhesion_norm, cmap="YlOrBr")
    first_bar = figure.colorbar(contraction_mapper, ax=contraction_axes, fraction=0.010, pad=0.008, shrink=0.76, aspect=38)
    first_bar.set_label("contraction traction (model force / area)")
    second_bar = figure.colorbar(adhesion_mapper, ax=adhesion_axes, fraction=0.010, pad=0.008, shrink=0.76, aspect=38)
    second_bar.set_label("adhesion traction (model force / area)")
    figure.suptitle("Peak activation: traction fields on the actual triangular mesh", fontsize=15, weight="bold", y=0.99)
    figure.text(0.5, 0.012, "Separate shared scales for the two defined fields · traction proxies, not 3D Cauchy stress", ha="center", color="#59636d")
    figure.subplots_adjust(left=0.005, right=0.91, top=0.94, bottom=0.045, hspace=0.08, wspace=0.01)
    save_pair(figure, directory, "peak_traction_mesh_grid")


def states_as_arrays(case: dict[str, Any]) -> dict[str, np.ndarray]:
    fields = ("phase", "activation", "end_reaction", "mean_p_span", "mean_q_span", "mean_r_span")
    return {name: np.array([float(row[name]) for row in case["states"]], dtype=float) for name in fields}


def render_cycle_response(cases: dict[str, dict[str, Any]], directory: Path) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(13.2, 8.6), sharex=True)
    for column, pattern in enumerate(("CENTER", "SYNC")):
        for strain in (0.02, 0.05, 0.10):
            case = cases[f"{pattern}_EPS{int(round(strain * 1000)):03d}"]
            arrays = states_as_arrays(case)
            color = AMPLITUDE_COLORS[strain]
            axes[0, column].plot(
                arrays["phase"], arrays["end_reaction"] - arrays["end_reaction"][0],
                marker="o", ms=4, lw=2, color=color, label=f"epsilon={100 * strain:.0f}%",
            )
            axes[1, column].plot(
                arrays["phase"], 100.0 * (arrays["mean_p_span"] / arrays["mean_p_span"][0] - 1.0),
                marker="o", ms=4, lw=2, color=color,
            )
        axes[0, column].set_title(f"{pattern}: end reaction above baseline")
        axes[1, column].set_title(f"{pattern}: mean long-axis deformation")
        axes[0, column].set_ylabel("delta end reaction (model force)")
        axes[1, column].set_ylabel("mean p-span strain (%)")
        axes[1, column].set_xlabel("algorithmic phase phi")
        axes[0, column].legend(frameon=False)
    for axis in axes.flat:
        axis.axvline(0.5, color="#9ba3a8", lw=0.8, ls="--")
        axis.grid(axis="y", color="#dfe3e6", lw=0.7)
        axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle("One active cell versus five synchronized cells across contraction amplitudes", fontsize=15, weight="bold")
    figure.tight_layout(rect=(0, 0.02, 1, 0.96))
    save_pair(figure, directory, "cycle_response")


def render_amplitude_response(output: Path, directory: Path) -> None:
    verdict = json.loads((output / "verdict.json").read_text(encoding="utf-8"))
    values = verdict["case_values"]
    figure, axes = plt.subplots(2, 2, figsize=(12.8, 8.5))
    pattern_colors = {"CENTER": "#2f6fa3", "SYNC": "#b43b34"}
    for pattern in ("CENTER", "SYNC"):
        case_names = [f"{pattern}_EPS020", f"{pattern}_EPS050", f"{pattern}_EPS100"]
        x_values = np.array([2.0, 5.0, 10.0])
        reaction = np.array([values[name]["active_increment"] for name in case_names])
        p_strain = np.array([100.0 * values[name]["peak_p_strain"] for name in case_names])
        contraction = np.array([values[name]["peak_contraction_traction_p95"] for name in case_names])
        adhesion = np.array([values[name]["peak_adhesion_traction_p95"] for name in case_names])
        for axis, data in zip(axes.flat, (reaction, p_strain, contraction, adhesion)):
            axis.plot(x_values, data, marker="o", ms=6, lw=2.1, color=pattern_colors[pattern], label=pattern)
    axes[0, 0].set(title="Peak active end reaction", ylabel="reaction increment (model force)")
    axes[0, 1].set(title="Peak mean long-axis strain", ylabel="p-span strain (%)")
    axes[1, 0].set(title="Peak contraction traction, node p95", ylabel="model force / area")
    axes[1, 1].set(title="Peak adhesion traction, node p95", ylabel="model force / area")
    for axis in axes.flat:
        axis.set_xlabel("maximum active reference shortening epsilon (%)")
        axis.set_xticks([2, 5, 10])
        axis.grid(axis="y", color="#dfe3e6", lw=0.7)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(frameon=False)
    figure.suptitle("Amplitude-response summary with the same material and boundary conditions", fontsize=15, weight="bold")
    figure.tight_layout(rect=(0, 0.01, 1, 0.96))
    save_pair(figure, directory, "amplitude_response")


def render_animation(
    cases: dict[str, dict[str, Any]],
    directory: Path,
    limits: tuple[np.ndarray, np.ndarray],
    field: str,
    cmap: str,
    label: str,
    stem: str,
) -> None:
    maximum = field_max(cases, field, peak_only=False)
    norm = colors.Normalize(vmin=0.0, vmax=maximum)
    mapper = ScalarMappable(norm=norm, cmap=cmap)
    figure = plt.figure(figsize=(14.5, 7.3))
    axes = [figure.add_subplot(2, 3, index + 1, projection="3d") for index in range(6)]
    ordered_cases = [name for row in PANEL_CASES for name in row]
    colorbar = figure.colorbar(mapper, ax=axes, fraction=0.018, pad=0.012, shrink=0.73, aspect=28)
    colorbar.set_label(label)
    phase_text = figure.text(0.5, 0.028, "", ha="center", color="#4f5961")

    def update(frame_index: int) -> list[Any]:
        for axis, case_name in zip(axes, ordered_cases):
            axis.clear()
            case = cases[case_name]
            add_mesh(
                axis, case["snapshots"][frame_index], limits,
                field=field, norm=norm, cmap=cmap, show_fixed=field == "displacement_magnitude",
            )
            axis.set_title(f"{case['pattern']} · epsilon={100 * case['strain']:.0f}%", fontsize=9, pad=-2)
        state = cases["SYNC_EPS050"]["states"][frame_index]
        phase_text.set_text(
            f"solver state {frame_index}/8 · phi={float(state['phase']):.3f} · activation={float(state['activation']):.3f} · not physiological time"
        )
        return [phase_text]

    figure.suptitle(stem.replace("_", " ").upper(), fontsize=14, weight="bold", y=0.985)
    figure.subplots_adjust(left=0.005, right=0.89, top=0.92, bottom=0.08, hspace=0.02, wspace=0.01)
    movie = animation.FuncAnimation(figure, update, frames=9, interval=700, blit=False, repeat=True)
    movie.save(directory / f"{stem}.gif", writer=animation.PillowWriter(fps=1.4), dpi=105)
    plt.close(figure)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_summary(output: Path) -> None:
    verdict = json.loads((output / "verdict.json").read_text(encoding="utf-8"))
    values = verdict["case_values"]
    response_rows = []
    for case, pattern, strain, source in CASE_SPECS:
        value = values[case]
        response_rows.append(
            {
                "case": case,
                "pattern": pattern,
                "contraction_strain": strain,
                "source": source,
                "peak_reaction_increment": value["active_increment"],
                "peak_p_strain_percent": 100.0 * value["peak_p_strain"],
                "peak_q_strain_percent": 100.0 * value["peak_q_strain"],
                "peak_r_strain_percent": 100.0 * value["peak_r_strain"],
                "peak_contraction_traction_p95": value["peak_contraction_traction_p95"],
                "peak_adhesion_traction_p95": value["peak_adhesion_traction_p95"],
                "recovery_fraction": value["recovery_fraction"],
            }
        )
    summary = {
        "schema_version": 1,
        "stage": "Z1-MYO-STRIP-CYCLE-AMP-A",
        "status": verdict["status"],
        "physics_status": verdict["physics_status"],
        "visualization_status": "generated_static_and_true_snapshot_gif_pending_manual_qa",
        "claims_status": "synthetic_mechanics_only",
        "experimental_comparison_status": "qualitative_consistency_only",
        "biological_validation_status": "blocked_data",
        "coordinate_semantics": "algorithmic_activation_phase_not_physiological_time",
        "response": response_rows,
        "failed_gates": verdict["failed_gates"],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Z1-MYO-STRIP-CYCLE-AMP-A v01 result summary",
        "",
        f"- Stage status: `{verdict['status']}`",
        "- Comparison: one active center cell in the five-cell strip versus five synchronized active cells.",
        "- Amplitudes: 2%, 5%, and 10% active reference-length shortening; the 5% raw trajectories are hash-verified reused evidence.",
        "- Coordinate: algorithmic activation phase, not physiological time.",
        "- Field boundary: contraction and adhesion traction are model force/area proxies, not 3D Cauchy stress.",
        "",
        "| Pattern | epsilon | peak reaction increment | peak p strain | peak q strain | peak r strain |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in response_rows:
        lines.append(
            f"| {row['pattern']} | {100 * row['contraction_strain']:.0f}% | "
            f"{row['peak_reaction_increment']:.8g} | {row['peak_p_strain_percent']:.4f}% | "
            f"{row['peak_q_strain_percent']:.4f}% | {row['peak_r_strain_percent']:.4f}% |"
        )
    lines.extend(
        [
            "",
            "This stage tests only the synthetic activation-count and amplitude response under fixed material links and rigid isometric end clamps. It does not calibrate physiological strain, force, beat period, intercalated-disc mechanics, or experimental agreement.",
            "",
        ]
    )
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_index(output: Path) -> None:
    html = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Z1-MYO-STRIP-CYCLE-AMP-A</title>
<style>
body{font-family:"Microsoft YaHei",Arial,sans-serif;margin:0;background:#f5f7f8;color:#20272c}main{max-width:1180px;margin:auto;padding:28px}h1{margin:0 0 8px}h2{margin-top:32px}.status{padding:12px 16px;background:#e5f2ea;border-left:5px solid #2d7653}.note{color:#59636d}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px}figure{margin:0;background:white;padding:12px;border:1px solid #d8dee2}img{width:100%;height:auto}figcaption{padding-top:8px;color:#4e5961}a{color:#155b8a}code{background:#e9edef;padding:2px 4px}</style>
</head>
<body><main>
<h1>Z1-MYO-STRIP-CYCLE-AMP-A</h1>
<p class="status">同一五细胞等长条带：中心单细胞激活 vs 五细胞同步激活；收缩幅度 2%、5%、10%。</p>
<p class="note">动画由 9 个真实求解器状态生成；phi 是算法激活相位，不是生理时间。张力字段为模型牵引代理，不是三维 Cauchy 应力。</p>
<h2>模型与峰值结果</h2>
<div class="grid">
<figure><img src="figures/model_structure.png" alt="模型结构"><figcaption>模型结构示意，不是求解器结果。</figcaption></figure>
<figure><img src="figures/peak_deformation_mesh_grid.png" alt="峰值形变网格"><figcaption>实际网格形变与统一位移色标。</figcaption></figure>
<figure><img src="figures/peak_traction_mesh_grid.png" alt="峰值张力网格"><figcaption>胞内胞内收缩牵引与界面黏附牵引分开显示。</figcaption></figure>
<figure><img src="figures/amplitude_response.png" alt="幅度响应"><figcaption>反力、长轴形变与牵引随幅度变化。</figcaption></figure>
</div>
<h2>真实快照动画</h2>
<div class="grid">
<figure><img src="figures/deformation_cycle.gif" alt="形变动画"><figcaption>实际网格形变，颜色为相对本工况 phase 0 的节点位移。</figcaption></figure>
<figure><img src="figures/active_traction_cycle.gif" alt="胞内收缩牵引动画"><figcaption>胞内收缩牵引。</figcaption></figure>
<figure><img src="figures/junction_traction_cycle.gif" alt="界面黏附牵引动画"><figcaption>固定材料链接传递到界面的牵引。</figcaption></figure>
</div>
<h2>证据</h2>
<ul>
<li><a href="summary.md">结果摘要</a></li><li><a href="metrics.csv">逐工况指标</a></li>
<li><a href="verdict.json">冻结门裁决</a></li><li><a href="reused_evidence.json">5% 复用证据哈希</a></li>
<li><a href="commands.txt">实际命令</a></li><li><a href="field_dictionary.json">字段定义</a></li>
</ul>
</main></body></html>
"""
    (output / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    directory = output / "figures"
    if directory.exists():
        raise SystemExit(f"create-only figures directory already exists: {directory}")
    directory.mkdir()

    cases = load_all_cases(output)
    limits = coordinate_limits(cases)
    render_structure(directory)
    render_peak_deformation(cases, directory, limits)
    render_peak_tractions(cases, directory, limits)
    render_cycle_response(cases, directory)
    render_amplitude_response(output, directory)
    render_animation(
        cases, directory, limits, "displacement_magnitude", "viridis",
        "displacement from phase 0 (model length units)", "deformation_cycle",
    )
    render_animation(
        cases, directory, limits, "contraction_traction", "inferno",
        "intracellular contraction traction (model force / area)", "active_traction_cycle",
    )
    render_animation(
        cases, directory, limits, "adhesion_traction", "YlOrBr",
        "junction adhesion traction (model force / area)", "junction_traction_cycle",
    )
    write_summary(output)
    write_index(output)
    write_json = lambda path, value: path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_json(
        output / "visual_qa.json",
        {
            "automated_asset_generation": "passed",
            "static_png_svg_pairs": 5,
            "true_snapshot_gif_count": 3,
            "gif_frame_count_each": 9,
            "shared_scale_policy": "one scale per field across all six cases and all animation frames",
            "manual_visual_qa": "not_run",
            "offline_index": "index.html",
        },
    )
    manifest = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(directory.iterdir()) if path.is_file()
    }
    write_json(output / "figure_manifest.json", manifest)
    print(json.dumps({"rendered": sorted(manifest), "status": "completed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
