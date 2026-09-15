"""Render solver-derived figures and an offline evidence index for Z1-BIOFORM-MYO-A v02."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image

from ventricle_bioform_myo_common import (
    PROJECT_ROOT,
    load_condition,
    sha256_file,
    write_json,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "ventricle_z1" / "z1_bioform_myo_a_v02_20260913"
FIGURE_STEMS = ["model_structure", "morphology_timepoints", "mechanical_fields", "validation_gates"]


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 9,
    }
)


def mesh_snapshot(condition_dir: Path, snapshot_index: int) -> dict[str, Any]:
    kernel, node_groups, face_groups = load_condition(condition_dir)
    nodes = node_groups[snapshot_index]
    local_ids = [int(row["node_index"]) for row in nodes]
    index_map = {local_id: index for index, local_id in enumerate(local_ids)}
    points = np.array([[float(row[name]) for name in ("x", "y", "z")] for row in nodes])
    triangles = np.array(
        [[index_map[int(row[name])] for name in ("n1", "n2", "n3")] for row in face_groups[snapshot_index]],
        dtype=int,
    )
    fields = {
        name: np.array([float(row[name]) for row in nodes])
        for name in ("curvature", "internal_pressure", "cytoskeleton_traction", "total_traction")
    }
    return {
        "kernel": kernel,
        "node_rows": nodes,
        "points": points,
        "triangles": triangles,
        "fields": fields,
        "phase": nodes[0]["phase"],
        "solver_coordinate": float(nodes[0]["solver_coordinate"]),
        "load_fraction": float(nodes[0]["load_fraction"]),
        "relaxation_fraction": float(nodes[0]["relaxation_fraction"]),
    }


def add_mesh(
    axis: Any,
    mesh: dict[str, Any],
    field: str | None = None,
    cmap: str = "viridis",
    shared_norm: colors.Normalize | None = None,
) -> ScalarMappable | None:
    points = mesh["points"]
    triangles = mesh["triangles"]
    polygons = points[triangles]
    if field is None:
        face_colors: Any = "#65b8b1"
        mapper = None
    else:
        values = mesh["fields"][field]
        face_values = values[triangles].mean(axis=1)
        norm = shared_norm or colors.Normalize(vmin=float(np.min(face_values)), vmax=float(np.max(face_values)) + 1e-30)
        mapper = ScalarMappable(norm=norm, cmap=cmap)
        face_colors = mapper.to_rgba(face_values)
    collection = Poly3DCollection(
        polygons,
        facecolors=face_colors,
        edgecolors=(0.18, 0.22, 0.25, 0.42),
        linewidths=0.22,
        alpha=0.96,
    )
    axis.add_collection3d(collection)
    center = points.mean(axis=0)
    span = float(np.max(np.ptp(points, axis=0)))
    radius = 0.58 * span if span > 0 else 1.0
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=21, azim=-58)
    axis.set_axis_off()
    return mapper


def save_figure(figure: plt.Figure, output: Path, stem: str) -> None:
    figure.savefig(output / f"{stem}.png", dpi=190, bbox_inches="tight", facecolor="white")
    figure.savefig(output / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(figure)


def render_model_structure(output: Path) -> None:
    figure, axis = plt.subplots(figsize=(12.0, 6.6))
    axis.set_xlim(0, 12)
    axis.set_ylim(0, 7)
    axis.axis("off")
    axis.text(0.3, 6.62, "SCHEMATIC — single free myocardial cell; not a solver result", fontsize=14, weight="bold")
    axis.text(0.3, 6.25, "No neighbour · no ECM · no lumen pressure · no clamp · no target final geometry", color="#5c6670")
    ellipse = matplotlib.patches.Ellipse((3.25, 3.35), 4.55, 2.75, facecolor="#d9f1ee", edgecolor="#187c75", linewidth=2.2)
    axis.add_patch(ellipse)
    axis.annotate("p  long axis", xy=(5.4, 3.35), xytext=(1.1, 3.35), arrowprops={"arrowstyle": "->", "lw": 2.3, "color": "#bf3f36"}, color="#9f2f28", weight="bold")
    axis.annotate("q  transverse", xy=(3.25, 4.65), xytext=(3.25, 2.15), arrowprops={"arrowstyle": "->", "lw": 2.0, "color": "#3f6eb3"}, ha="center", color="#345d96")
    axis.text(3.25, 1.35, "r = thickness (out of page)", ha="center", color="#5a4a8a")
    axis.text(3.25, 5.10, "Active normal shape traction", ha="center", weight="bold")
    sigma = r"$\Sigma_{cyt}=s(p\otimes p-0.15q\otimes q-0.85r\otimes r)$"
    axis.text(3.25, 0.65, sigma, ha="center", fontsize=12)
    blocks = [
        (7.0, 4.95, "ACTIVE", "normal projection of\ncytoskeletal deviatoric stress", "#f8d7d2", "#b54338"),
        (7.0, 3.10, "PASSIVE", "cortical tension + bending\narea elasticity + volume pressure", "#dce9f7", "#3d6f9e"),
        (7.0, 1.25, "NUMERICAL", "overdamped relaxation +\ndynamic quality-controlled remeshing", "#e5ead8", "#6b7d36"),
    ]
    for x_value, y_value, title, text_value, face_color, edge_color in blocks:
        box = matplotlib.patches.FancyBboxPatch((x_value, y_value), 4.35, 1.28, boxstyle="round,pad=0.16", facecolor=face_color, edgecolor=edge_color, linewidth=1.7)
        axis.add_patch(box)
        axis.text(x_value + 0.25, y_value + 0.91, title, weight="bold", color=edge_color)
        axis.text(x_value + 0.25, y_value + 0.26, text_value, va="bottom")
    axis.text(11.65, 0.22, "Z1-BIOFORM-MYO-A v02", ha="right", color="#6b747d")
    save_figure(figure, output, "model_structure")


def render_morphology(output: Path) -> None:
    condition_dir = output / "raw" / "FULL_M320_DT020"
    snapshots = [0, 2, 4, 6, 8]
    figure = plt.figure(figsize=(16.0, 4.1))
    for panel, snapshot_index in enumerate(snapshots, start=1):
        axis = figure.add_subplot(1, 5, panel, projection="3d")
        mesh = mesh_snapshot(condition_dir, snapshot_index)
        add_mesh(axis, mesh)
        label = f"state {snapshot_index}\n{mesh['phase']}  λ={mesh['solver_coordinate']:.0f}"
        axis.set_title(label, fontsize=10, pad=4)
    figure.suptitle("Solver states: myocardial intrinsic-shape formation", fontsize=14, weight="bold", y=0.98)
    figure.text(0.5, 0.015, "λ is algorithmic loading / relaxation coordinate, not physiological time", ha="center", color="#5d6670")
    figure.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.10, wspace=0.0)
    save_figure(figure, output, "morphology_timepoints")


def render_fields(output: Path) -> None:
    mesh = mesh_snapshot(output / "raw" / "FULL_M320_DT020", 8)
    panels = [
        ("curvature", "Curvature", "coolwarm"),
        ("internal_pressure", "Internal pressure", "Blues"),
        ("cytoskeleton_traction", "Cytoskeleton traction", "magma"),
        ("total_traction", "Total traction", "viridis"),
    ]
    figure = plt.figure(figsize=(15.0, 4.3))
    for panel, (field, title, cmap) in enumerate(panels, start=1):
        axis = figure.add_subplot(1, 4, panel, projection="3d")
        mapper = add_mesh(axis, mesh, field=field, cmap=cmap)
        axis.set_title(title, fontsize=11, pad=4)
        if mapper is not None:
            figure.colorbar(mapper, ax=axis, fraction=0.035, pad=0.01, shrink=0.62)
    figure.suptitle("Final solver state: mapped mechanical fields", fontsize=14, weight="bold", y=0.98)
    figure.text(0.5, 0.015, "Fields are nodal/face-interpolated solver outputs; values are synthetic nondimensional quantities", ha="center", color="#5d6670")
    figure.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.10, wspace=0.03)
    save_figure(figure, output, "mechanical_fields")


def render_validation(output: Path, verification: dict[str, Any]) -> None:
    metrics = verification["condition_metrics"]
    figure, axes = plt.subplots(2, 2, figsize=(13.4, 8.0))
    selected = ["FULL_M320_DT020", "ABLATION_M320_DT020", "PERTURBED_M320_DT020", "ROTATED37_M320_DT020"]
    labels = ["Full", "Ablation", "Perturbed", "Rotated"]
    x_values = np.arange(len(selected))
    e_values = [metrics[item]["final"]["E_pq"] for item in selected]
    f_values = [metrics[item]["final"]["F_qr"] for item in selected]
    width = 0.36
    axes[0, 0].bar(x_values - width / 2, e_values, width, label="E_pq", color="#d66a5d")
    axes[0, 0].bar(x_values + width / 2, f_values, width, label="F_qr", color="#4f88b8")
    axes[0, 0].axhline(1.20, color="#d66a5d", linestyle="--", linewidth=1)
    axes[0, 0].axhline(1.15, color="#4f88b8", linestyle=":", linewidth=1)
    axes[0, 0].set_xticks(x_values, labels)
    axes[0, 0].set_ylabel("shape ratio")
    axes[0, 0].set_title("Mechanism controls")
    axes[0, 0].legend(frameon=False, ncol=2)

    resolution_ids = ["FULL_M080_DT020", "FULL_M320_DT020", "FULL_M1280_DT020"]
    resolution_labels = ["80", "320", "1280"]
    axes[0, 1].plot(resolution_labels, [metrics[item]["final"]["E_pq"] for item in resolution_ids], "o-", label="E_pq", color="#d66a5d")
    axes[0, 1].plot(resolution_labels, [metrics[item]["final"]["F_qr"] for item in resolution_ids], "s-", label="F_qr", color="#4f88b8")
    axes[0, 1].set_xlabel("requested initial faces")
    axes[0, 1].set_ylabel("shape ratio")
    axes[0, 1].set_title("Mesh trend")
    axes[0, 1].legend(frameon=False)

    step_ids = ["FULL_M320_DT040", "FULL_M320_DT020", "FULL_M320_DT010"]
    step_labels = ["0.040", "0.020", "0.010"]
    axes[1, 0].plot(step_labels, [metrics[item]["final"]["E_pq"] for item in step_ids], "o-", label="E_pq", color="#d66a5d")
    axes[1, 0].plot(step_labels, [metrics[item]["final"]["F_qr"] for item in step_ids], "s-", label="F_qr", color="#4f88b8")
    axes[1, 0].set_xlabel("numerical step")
    axes[1, 0].set_ylabel("shape ratio")
    axes[1, 0].set_title("Step-size trend")
    axes[1, 0].legend(frameon=False)

    gate_groups = ["prerequisite", "common_numerical", "mechanism", "discretization"]
    gate_status = verification["gate_group_status"]
    values = [1 if gate_status[group] else 0 for group in gate_groups]
    colors_values = ["#3b8f72" if value else "#c64f45" for value in values]
    axes[1, 1].barh(np.arange(4), [1, 1, 1, 1], color=colors_values)
    axes[1, 1].set_yticks(np.arange(4), ["Prerequisite", "Numerical", "Mechanism", "Discretization"])
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set_xticks([])
    for index, value in enumerate(values):
        axes[1, 1].text(0.5, index, "PASS" if value else "FAIL", ha="center", va="center", color="white", weight="bold")
    axes[1, 1].set_title("Frozen gate groups")
    figure.suptitle(f"Independent qualification: {verification['verdict']}", fontsize=15, weight="bold")
    figure.tight_layout(rect=(0, 0.02, 1, 0.94))
    save_figure(figure, output, "validation_gates")


def render_index(output: Path, summary: dict[str, Any]) -> None:
    status = html.escape(str(summary["status"]))
    failed = int(summary["failed_gate_count"])
    cards = "\n".join(
        f'<section class="figure"><h2>{html.escape(stem.replace("_", " ").title())}</h2><img src="{stem}.png" alt="{stem}"><p><a href="{stem}.svg">SVG</a></p></section>'
        for stem in FIGURE_STEMS
    )
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Z1-BIOFORM-MYO-A v02</title><style>
body{{font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;background:#f4f6f7;color:#1d2933}}main{{max-width:1180px;margin:auto;padding:28px}}
.hero,.figure{{background:white;border-radius:14px;padding:22px;margin-bottom:20px;box-shadow:0 3px 14px #1d293315}}.status{{display:inline-block;padding:7px 11px;border-radius:999px;background:#e0efe8;color:#246a54;font-weight:700}}
img{{width:100%;height:auto;border:1px solid #e3e8eb;border-radius:8px}}a{{color:#176f76}}code{{background:#edf1f2;padding:2px 5px;border-radius:4px}}
</style></head><body><main><section class="hero"><h1>Z1-BIOFORM-MYO-A v02</h1><p class="status">{status}</p>
<p>单个自由心肌细胞的合成内禀形态机制资格。结果不代表生物学参数已标定，父 Z1 仍为 <code>blocked</code>。</p>
<p>正式矩阵：8 个条件；失败门：{failed}；生物学验证：<code>blocked_data</code>。</p>
<p><a href="report.md">报告</a> · <a href="summary.json">摘要 JSON</a> · <a href="verification/independent_verification.json">独立核验</a> · <a href="run_ledger.json">运行账本</a></p></section>
{cards}</main></body></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if any((output / f"{stem}.png").exists() or (output / f"{stem}.svg").exists() for stem in FIGURE_STEMS):
        raise SystemExit("create-only render outputs already exist")
    verification = json.loads((output / "verification" / "independent_verification.json").read_text(encoding="utf-8"))
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    render_model_structure(output)
    render_morphology(output)
    render_fields(output)
    render_validation(output, verification)
    render_index(output, summary)

    visual_checks = []
    for stem in FIGURE_STEMS:
        png = output / f"{stem}.png"
        svg = output / f"{stem}.svg"
        with Image.open(png) as image:
            width, height = image.size
        visual_checks.append(
            {
                "stem": stem,
                "png_exists": png.is_file(),
                "svg_exists": svg.is_file(),
                "png_dimensions": [width, height],
                "dimension_gate_pass": width >= 1200 and height >= 600,
            }
        )
    write_json(
        output / "visual_qa.json",
        {
            "schema_version": 1,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "programmatic_checks": visual_checks,
            "all_programmatic_checks_pass": all(item["dimension_gate_pass"] for item in visual_checks),
            "human_visual_review": "pending",
        },
    )
    manifest_paths = [
        output / "index.html",
        output / "summary.json",
        output / "report.md",
        output / "visual_qa.json",
    ] + [output / f"{stem}.{extension}" for stem in FIGURE_STEMS for extension in ("png", "svg")]
    write_json(
        output / "render_manifest.json",
        {
            "schema_version": 1,
            "files": [
                {"path": str(path.relative_to(output)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                for path in manifest_paths
            ],
        },
    )
    print(json.dumps({"output": str(output), "figures": FIGURE_STEMS}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
