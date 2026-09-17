"""Render true meshes and diagnostics for quasistatic crowded growth."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from .myocardial_crowded_box import (
    GRID,
    _draw_structure_3d,
    _field_normalizer,
    _read_csv,
    _snapshot_cells,
    _state_bounds,
    _style,
)
from .myocardial_crowded_target_pair import (
    _draw_shared_field,
    _save_scientific_layout,
)


CONDITIONS = ("QS_COARSE_K30", "QS_REFINED_K30", "QS_REFINED_K15")
LABELS = {
    "QS_COARSE_K30": "K30 coarse contact",
    "QS_REFINED_K30": "K30 refined contact",
    "QS_REFINED_K15": "K15 refined contact",
}
COLORS = {
    "QS_COARSE_K30": "#6C8798",
    "QS_REFINED_K30": "#2474A6",
    "QS_REFINED_K15": "#C95855",
}


def _condition_data(result: Path, condition: str) -> dict[str, object] | None:
    raw = result / "raw" / condition
    required = ("state_metrics.csv", "nodes.csv", "faces.csv", "cell_metrics.csv")
    if any(not (raw / name).is_file() for name in required):
        return None
    states = sorted(
        _read_csv(raw / "state_metrics.csv"), key=lambda row: int(row["snapshot_index"])
    )
    nodes = _read_csv(raw / "nodes.csv")
    faces = _read_csv(raw / "faces.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in nodes})
    if not states or not snapshots:
        return None
    return {
        "raw": raw,
        "states": states,
        "nodes": nodes,
        "faces": faces,
        "snapshots": snapshots,
        "cells": _read_csv(raw / "cell_metrics.csv"),
        "audits": (
            _read_csv(raw / "step_audits.csv")
            if (raw / "step_audits.csv").is_file()
            else []
        ),
        "rejections": (
            _read_csv(raw / "trial_rejections.csv")
            if (raw / "trial_rejections.csv").is_file()
            else []
        ),
    }


def _render_gif(path: Path, data: dict[str, object]) -> None:
    states = data["states"]
    nodes = data["nodes"]
    faces = data["faces"]
    snapshots = data["snapshots"]
    assert isinstance(states, list) and isinstance(nodes, list)
    assert isinstance(faces, list) and isinstance(snapshots, list)
    frames: list[Image.Image] = []
    for snapshot in snapshots:
        state = states[snapshot]
        cells = _snapshot_cells(nodes, faces, snapshot)
        figure = plt.figure(figsize=(6.4, 4.8), dpi=130)
        axis = figure.add_subplot(111, projection="3d")
        fraction = float(state["applied_target_fraction_of_final"])
        _draw_structure_3d(
            axis,
            cells,
            _state_bounds(state),
            f"Refined K30 | state {snapshot} | target fraction {fraction:.3f}",
        )
        figure.suptitle(
            "True solver states; algorithmic progress, not physiological time",
            fontsize=10.5,
            fontweight="bold",
            y=0.97,
        )
        figure.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.88)
        figure.canvas.draw()
        frame = Image.fromarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3].copy())
        frames.append(frame)
        plt.close(figure)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=650,
        loop=0,
        optimize=True,
    )


def _write_navigation(result: Path, manifest: dict[str, object]) -> None:
    verification = json.loads((result / "verification.json").read_text(encoding="utf-8"))
    condition_lines = []
    for condition in CONDITIONS:
        evidence = verification.get("conditions", {}).get(condition, {})
        condition_lines.append(
            f"<tr><td>{condition}</td><td>{evidence.get('numerical_saved_state_safety', 'unknown')}</td>"
            f"<td>{evidence.get('static_equilibrium', 'unknown')}</td>"
            f"<td>{evidence.get('contact_network', 'unknown')}</td></tr>"
        )
    animation = manifest.get("animation", {})
    animation_html = (
        '<h2>真实状态动画</h2><img src="figures/quasistatic_growth_refined_k30.gif" alt="animation">'
        if isinstance(animation, dict) and animation.get("status") == "passed"
        else '<h2>真实状态动画</h2><p class="bad">not_run：求解器在第二个网格状态保存前停止；不以重复状态0冒充时间序列。</p>'
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>PRL quasistatic growth</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1180px;margin:30px auto;color:#263238}}img{{max-width:100%;border:1px solid #d8e0e3}}table{{border-collapse:collapse}}td,th{{border:1px solid #c8d1d5;padding:7px 10px}}.bad{{color:#a52a2a}}</style></head>
<body><h1>5×5 心肌细胞双倍目标准静态增长</h1>
<p><b>阶段状态：</b>{verification.get('status', 'unknown')}；算法坐标不是生理时间。数值安全、静力平衡和接触网络分开裁决。</p>
<table><tr><th>条件</th><th>保存态安全</th><th>静力平衡</th><th>接触网络</th></tr>{''.join(condition_lines)}</table>
<h2>模型结构与时间点</h2><img src="figures/quasistatic_growth_structure.png" alt="structure">
{animation_html}
<h2>压力与接触牵引</h2><img src="figures/quasistatic_growth_fields.png" alt="fields">
<h2>数值进展</h2><img src="figures/quasistatic_growth_progress.png" alt="progress">
<h2>粗细收敛</h2><img src="figures/quasistatic_growth_convergence.png" alt="convergence">
<p>原始数据位于 <code>raw/</code>，独立裁决见 <a href="verification.json">verification.json</a>。本页为离线结果导航，不是交互式三维查看器。</p>
</body></html>"""
    (result / "index.html").write_text(html, encoding="utf-8")
    readme = f"""# 5×5 心肌细胞双倍目标准静态增长

状态：`{verification.get('status', 'unknown')}`。

本结果将父异质参考目标逐步延拓到2倍，盒子固定，算法坐标不是生理时间。保存态安全、粗细收敛、静力平衡和接触网络分别见 `verification.json`。

- 结构图：`figures/quasistatic_growth_structure.png`
- 真实状态GIF：`{animation.get('status', 'not_run')}`；若未完成第二个网格保存态，不生成或引用动画
- 场图：`figures/quasistatic_growth_fields.png`
- 进展图：`figures/quasistatic_growth_progress.png`
- 收敛图：`figures/quasistatic_growth_convergence.png`
- 离线导航：`index.html`

图件渲染通过不替代科学门；生物学验证与主动收缩均为 `not_run`。
"""
    (result / "README.md").write_text(readme, encoding="utf-8")


def render_myocardial_crowded_quasistatic_growth(
    result: Path,
) -> dict[str, object]:
    result = result.resolve(strict=True)
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    _style()
    available = {
        condition: data
        for condition in CONDITIONS
        if (data := _condition_data(result, condition)) is not None
    }
    if not available:
        return {"status": "failed", "reason": "no retained solver states"}
    primary_name = (
        "QS_REFINED_K30" if "QS_REFINED_K30" in available else next(iter(available))
    )
    primary = available[primary_name]
    states = primary["states"]
    nodes = primary["nodes"]
    faces = primary["faces"]
    snapshots = primary["snapshots"]
    assert isinstance(states, list) and isinstance(nodes, list)
    assert isinstance(faces, list) and isinstance(snapshots, list)
    all_paths: list[Path] = []

    selected = list(
        dict.fromkeys(
            snapshots[index]
            for index in (
                0,
                min(2, len(snapshots) - 1),
                min(4, len(snapshots) - 1),
                len(snapshots) - 1,
            )
        )
    )
    structure = plt.figure(figsize=(max(6.4, 3.75 * len(selected)), 4.8))
    for panel, snapshot in enumerate(selected, start=1):
        axis = structure.add_subplot(1, len(selected), panel, projection="3d")
        state = states[snapshot]
        fraction = float(state["applied_target_fraction_of_final"])
        _draw_structure_3d(
            axis,
            _snapshot_cells(nodes, faces, snapshot),
            _state_bounds(state),
            f"{chr(96 + panel)}  state {snapshot} | target {fraction:.3f}",
        )
    structure.suptitle(
        (
            "True 5×5 cardiomyocyte meshes during quasistatic target growth"
            if len(selected) > 1
            else "Initial true 5×5 mesh; solver stopped before the next retained mesh state"
        ),
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    structure.subplots_adjust(left=0.018, right=0.99, bottom=0.05, top=0.87, wspace=0.06)
    all_paths.extend(
        _save_scientific_layout(
            structure,
            figures / "quasistatic_growth_structure",
            reason=(
                "Distinct true 3D states show loading and hold phases in the transparent fixed box."
                if len(selected) > 1
                else "Only state 0 was retained; the panel is the model structure, not a completed growth result."
            ),
        )
    )
    plt.close(structure)

    field_names = [name for name in ("QS_REFINED_K30", "QS_REFINED_K15") if name in available]
    if len(field_names) < 2:
        field_names = list(available)[:2] if len(available) >= 2 else [primary_name, primary_name]
    field_cells = []
    field_bounds = []
    for name in field_names:
        data = available[name]
        data_states = data["states"]
        data_nodes = data["nodes"]
        data_faces = data["faces"]
        data_snapshots = data["snapshots"]
        assert isinstance(data_states, list) and isinstance(data_nodes, list)
        assert isinstance(data_faces, list) and isinstance(data_snapshots, list)
        snapshot = data_snapshots[-1]
        field_cells.append(_snapshot_cells(data_nodes, data_faces, snapshot))
        field_bounds.append(_state_bounds(data_states[-1]))
    pressure_values = np.concatenate(
        [
            np.asarray([float(row["internal_pressure"]) for cell in cells for row in cell["rows"]])
            for cells in field_cells
        ]
    )
    contact_values = np.concatenate(
        [
            np.asarray([float(row["contact_traction"]) for cell in cells for row in cell["rows"]])
            for cells in field_cells
        ]
    )
    field_figure, field_axes = plt.subplots(2, 2, figsize=(9.4, 6.9))
    for column, (name, cells, bounds) in enumerate(
        zip(field_names, field_cells, field_bounds, strict=True)
    ):
        pressure = _draw_shared_field(
            field_axes[0, column],
            cells,
            bounds,
            "internal_pressure",
            f"{chr(97 + column)}  {LABELS[name]} | pressure",
            normalizer=_field_normalizer(pressure_values, signed=True),
            cmap="coolwarm",
        )
        contact = _draw_shared_field(
            field_axes[1, column],
            cells,
            bounds,
            "contact_traction",
            f"{chr(99 + column)}  {LABELS[name]} | contact traction",
            normalizer=_field_normalizer(contact_values, signed=False),
            cmap="magma",
        )
        field_figure.colorbar(pressure, ax=field_axes[0, column], fraction=0.034, pad=0.018)
        field_figure.colorbar(contact, ax=field_axes[1, column], fraction=0.034, pad=0.018)
    retained_field_state = max(
        int(data["snapshots"][-1])  # type: ignore[index]
        for data in (available[name] for name in field_names)
    )
    field_figure.suptitle(
        f"Latest retained true-mesh fields (state {retained_field_state}); row-wise shared color scales",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    field_figure.subplots_adjust(left=0.07, right=0.94, bottom=0.07, top=0.90, wspace=0.25, hspace=0.32)
    all_paths.extend(
        _save_scientific_layout(
            field_figure,
            figures / "quasistatic_growth_fields",
            reason="Pressure and contact traction are mapped on retained true meshes.",
        )
    )
    plt.close(field_figure)

    progress, axes = plt.subplots(2, 2, figsize=(8.9, 6.8))
    specs = (
        ("max_free_force", "max nodal force", True),
        ("applied_target_fraction_of_final", "target fraction of final", False),
        ("contact_active_cell_pairs", "active cell pairs", False),
        ("min_intercell_separation", "minimum intercell separation", True),
    )
    for axis, (field, ylabel, logarithmic) in zip(axes.flat, specs, strict=True):
        for name, data in available.items():
            rows = data["audits"] or data["states"]
            assert isinstance(rows, list)
            x = np.asarray([float(row["coordinate"]) for row in rows])
            y = np.asarray([float(row[field]) for row in rows])
            if logarithmic:
                axis.semilogy(x, np.maximum(y, 1.0e-16), "o-", color=COLORS[name], label=LABELS[name])
            else:
                axis.plot(x, y, "o-", color=COLORS[name], label=LABELS[name])
        axis.set_xlabel("algorithmic loading / relaxation coordinate")
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", color=GRID, lw=0.55)
        axis.spines[["top", "right"]].set_visible(False)
    axes[0, 0].axhline(1.0e-3, color="#8F2F2B", ls="--", lw=1.0)
    axes[1, 1].axhline(1.0e-8, color="#8F2F2B", ls="--", lw=1.0)
    axes[0, 0].legend(frameon=False, fontsize=6.8)
    progress.suptitle("Quasistatic loading diagnostics; coordinate is not physiological time", fontsize=11.5, fontweight="bold", y=0.98)
    progress.subplots_adjust(left=0.10, right=0.96, bottom=0.09, top=0.90, wspace=0.31, hspace=0.36)
    all_paths.extend(
        _save_scientific_layout(
            progress,
            figures / "quasistatic_growth_progress",
            reason="Accepted-substep diagnostics expose the contact-limited stop even when no later mesh snapshot exists.",
        )
    )
    plt.close(progress)

    gate_path = result / "numerical_convergence_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else {}
    convergence, axis = plt.subplots(figsize=(7.4, 4.8))
    values = gate.get("global_relative_differences", {})
    if values:
        labels = list(values)
        percentages = 100.0 * np.asarray([float(values[label]) for label in labels])
        axis.barh(np.arange(len(labels)), percentages, color="#4F8199")
        axis.set_yticks(np.arange(len(labels)), [label.replace("_", " ") for label in labels])
        axis.axvline(2.0, color="#A43D39", ls="--", lw=1.2, label="2% global gate")
        axis.legend(frameon=False)
        axis.set_xlabel("coarse vs refined relative difference (%)")
    else:
        axis.text(0.5, 0.5, f"Convergence gate: {gate.get('status', 'not available')}", ha="center", va="center", transform=axis.transAxes)
        axis.set_axis_off()
    axis.spines[["top", "right"]].set_visible(False)
    convergence.suptitle("Preregistered coarse/refined numerical comparison", fontsize=11.5, fontweight="bold", y=0.98)
    convergence.subplots_adjust(left=0.30, right=0.95, bottom=0.14, top=0.87)
    all_paths.extend(
        _save_scientific_layout(
            convergence,
            figures / "quasistatic_growth_convergence",
            reason="Global coarse/refined differences are shown against the frozen two-percent gate.",
        )
    )
    plt.close(convergence)

    if len(snapshots) >= 2:
        gif_path = figures / "quasistatic_growth_refined_k30.gif"
        _render_gif(gif_path, primary)
        all_paths.append(gif_path)
        animation: dict[str, object] = {
            "status": "passed",
            "file": str(gif_path.relative_to(result).as_posix()),
            "state_count": len(snapshots),
        }
    else:
        animation = {
            "status": "not_run",
            "reason": "solver stopped before a second retained mesh state",
            "state_count": len(snapshots),
        }
    manifest = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-QUASISTATIC-GROWTH-B",
        "status": "passed",
        "source": "retained true solver states and accepted-substep audits",
        "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physiological_time",
        "primary_animation_condition": primary_name,
        "retained_mesh_state_counts": {
            name: len(data["snapshots"]) for name, data in available.items()
        },
        "animation": animation,
        "files": [str(path.relative_to(result).as_posix()) for path in all_paths],
        "interactive_3d_viewer": "not_run",
        "spatial_layout_exceptions": [
            "quasistatic_growth_structure",
            "quasistatic_growth_fields",
            "quasistatic_growth_progress",
            "quasistatic_growth_convergence",
        ],
    }
    (figures / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_navigation(result, manifest)
    return manifest
