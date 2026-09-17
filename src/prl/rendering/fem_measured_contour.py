"""Render FEM states driven by an image-derived zebrafish outer contour.

Only the outer contour is measured. The cavity and layer interfaces are
homothetic assumptions, and the saved cycle is quasi-static activation phase.
"""

from __future__ import annotations

from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, MaxNLocator
import numpy as np
from PIL import Image

from prl.rendering.cb_plot_unified_style import (
    DEFAULT_STYLE,
    StyleOverride,
    StyleSpec,
    add_top_information,
    apply_axes_style,
    enforce_figure_typography,
    export_figure,
    validate_figure,
)


LAYER_COLORS = ("#4C9F70", "#D6B656", "#5B8DB8")
LAYER_NAMES = ("Assumed endocardium", "Assumed ECM", "Assumed myocardium")
BOUNDARY_COLOR = "#BA3E34"
REFERENCE_COLOR = "#56616B"


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as payload:
        return {key: payload[key] for key in payload.files}


def _compact_style(side: float, *, small: bool = False) -> tuple[StyleSpec, list[StyleOverride]]:
    """Keep final panel dimensions fixed and record every compact-style choice."""
    style = StyleSpec(
        axis_box_size_in=(side, side),
        tick_label_size=12.0 if small else 16.0,
        axis_label_size=14.0 if small else 18.0,
        annotation_font_size=13.0 if small else 16.0,
        sample_size_and_stat_font_size=12.0 if small else 14.0,
        legend_font_size=12.0 if small else 14.0,
        axes_line_width=1.5,
        major_tick_length_pt=5.0,
        major_tick_width_pt=1.0,
        minor_tick_length_pt=3.0,
        minor_tick_width_pt=0.8,
        data_line_width=1.5,
        tick_label_pad_pt=4.0,
        axis_label_pad_pt=8.0,
    )
    original = asdict(DEFAULT_STYLE)
    overrides = [
        StyleOverride(
            field=key,
            reason=(
                "Compact spatial FEM engineering multipanel; fixed square panel, "
                "equal physical x/y scale, explicit margins and readable typography. "
                "Triangle edges are fine mesh marks rather than quantitative data lines."
            ),
        )
        for key, value in asdict(style).items()
        if value != original[key]
    ]
    return style, overrides


def _axes(figure: plt.Figure, x: float, y: float, side: float) -> plt.Axes:
    width, height = figure.get_size_inches()
    return figure.add_axes((x / width, y / height, side / width, side / height))


def _spatial_axis(
    axis: plt.Axes, bounds: tuple[float, float, float, float], style: StyleSpec
) -> None:
    axis.set_xlim(bounds[0], bounds[1])
    axis.set_ylim(bounds[2], bounds[3])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (µm)")
    axis.set_ylabel("y (µm)")
    _bounded_ticks(axis.xaxis, bounds[0], bounds[1], bins=3)
    _bounded_ticks(axis.yaxis, bounds[2], bounds[3], bins=3)
    apply_axes_style(axis, style=style)


def _bounded_ticks(axis_object: Any, lower: float, upper: float, *, bins: int = 4) -> None:
    """Keep only visible major ticks; locators may otherwise return outside ticks."""
    proposed = MaxNLocator(nbins=bins).tick_values(lower, upper)
    inside = proposed[(proposed >= lower) & (proposed <= upper)]
    if not len(inside):
        inside = np.linspace(lower, upper, 3)[1:-1]
    axis_object.set_major_locator(FixedLocator(inside))


def _closed(points: np.ndarray) -> np.ndarray:
    return np.vstack((points, points[0]))


def _mesh(
    positions: np.ndarray,
    cells: np.ndarray,
    *,
    values: np.ndarray | None = None,
    layers: np.ndarray | None = None,
    norm: Normalize | None = None,
    cmap: str = "magma",
) -> PolyCollection:
    if values is None:
        if layers is None:
            raise ValueError("Layer IDs are required for an uncolored structure mesh.")
        return PolyCollection(
            positions[cells],
            facecolors=[LAYER_COLORS[int(layer)] for layer in layers],
            edgecolors=(0.08, 0.11, 0.13, 0.24),
            linewidths=0.13,
        )
    return PolyCollection(
        positions[cells],
        array=np.asarray(values),
        cmap=cmap,
        norm=norm,
        edgecolors=(0.08, 0.11, 0.13, 0.17),
        linewidths=0.11,
    )


def _reference(
    axis: plt.Axes,
    positions: np.ndarray,
    inner: np.ndarray,
    outer: np.ndarray,
) -> None:
    for node_ids in (inner, outer):
        curve = _closed(positions[node_ids])
        axis.plot(curve[:, 0], curve[:, 1], color=REFERENCE_COLOR, lw=1.1, ls="--", alpha=0.8)


def _colorbar(
    figure: plt.Figure,
    collection: PolyCollection,
    position: tuple[float, float, float, float],
    label: str,
    style: StyleSpec,
) -> None:
    width, height = figure.get_size_inches()
    x, y, bar_width, bar_height = position
    axis = figure.add_axes((x / width, y / height, bar_width / width, bar_height / height))
    colorbar = figure.colorbar(collection, cax=axis)
    colorbar.set_label(label, fontsize=style.axis_label_size, labelpad=8)
    colorbar.ax.tick_params(labelsize=style.tick_label_size, direction="out", length=4)
    proposed = MaxNLocator(nbins=4).tick_values(collection.norm.vmin, collection.norm.vmax)
    colorbar.locator = FixedLocator(proposed[(proposed >= collection.norm.vmin) & (proposed <= collection.norm.vmax)])
    colorbar.update_ticks()
    colorbar.outline.set_linewidth(1.0)


def _export(
    figure: plt.Figure,
    axes: list[plt.Axes],
    path: Path,
    style: StyleSpec,
    overrides: list[StyleOverride],
) -> list[Path]:
    paths = export_figure(figure, axes, path, style=style, overrides=overrides)
    plt.close(figure)
    return [paths.png, paths.svg, paths.manifest]


def render_fem_measured_contour(result: Path) -> dict[str, Any]:
    """Export measured-source geometry and saved FEM states without amplifying motion."""
    result = result.resolve()
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification_path = result / "verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else {}
    qualification_status = str(verification.get("status", "unknown"))
    qualification_label = f"Qualification {qualification_status.upper()}"
    data = _load(result / "raw" / "G1.npz")
    source = _load(result / "geometry_source.npz")
    scale = float(configuration["geometry"]["length_scale_um"])
    center = np.asarray(configuration["geometry"]["center_um"], dtype=float)
    if not np.isfinite(scale) or scale <= 0 or center.shape != (2,):
        raise ValueError("Geometry scale and center must define a valid physical mapping.")
    coordinates = np.asarray(data["coordinates"], dtype=float) * scale + center
    displacements = np.asarray(data["displacements"], dtype=float) * scale
    states = coordinates[None, :, :] + displacements
    cells = data["cells"].astype(np.int64)
    layers = data["cell_layers"].astype(np.int64)
    phases = data["phases"]
    activation = data["activation"]
    inner = data["inner_nodes"].astype(np.int64)
    outer = data["outer_nodes"].astype(np.int64)
    equivalent = data["equivalent_stress"]
    pressure = data["pressure"]
    lumen_change = data["lumen_fraction_change"]
    outer_change = data["outer_fraction_change"]
    if len(phases) != 41 or len(states) != 41:
        raise ValueError("The measured-contour cycle requires 41 saved FEM states.")
    if not all(np.all(np.isfinite(array)) for array in (states, equivalent, pressure)):
        raise ValueError("Nonfinite FEM states cannot be rendered as valid results.")
    peak = int(np.argmax(activation))
    snapshot_indices = np.linspace(0, len(phases) - 1, 5, dtype=int)
    raw_contour = source["raw_contour_um"]
    smooth_contour = source["smooth_contour_um"]
    all_positions = np.vstack((states.reshape(-1, 2), raw_contour, smooth_contour))
    extent_min = np.min(all_positions, axis=0)
    extent_max = np.max(all_positions, axis=0)
    plot_center = (extent_min + extent_max) * 0.5
    plot_half_side = float(np.max(extent_max - extent_min)) * 0.565
    bounds = (
        float(plot_center[0] - plot_half_side), float(plot_center[0] + plot_half_side),
        float(plot_center[1] - plot_half_side), float(plot_center[1] + plot_half_side),
    )
    stress_limit = max(float(np.max(equivalent)), 1.0e-14)
    pressure_limit = max(float(np.max(np.abs(pressure))), 1.0e-14)
    displacement_magnitude = np.linalg.norm(displacements, axis=2)
    displacement_cells = np.mean(displacement_magnitude[:, cells], axis=2)
    displacement_limit = max(float(np.max(displacement_cells)), 1.0e-14)
    stress_norm = Normalize(0.0, stress_limit)
    pressure_norm = TwoSlopeNorm(vmin=-pressure_limit, vcenter=0.0, vmax=pressure_limit)
    displacement_norm = Normalize(0.0, displacement_limit)
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    exported: list[Path] = []

    style, overrides = _compact_style(4.4)
    figure = plt.figure(figsize=(12.3, 7.25))
    axes = [_axes(figure, 1.05, 2.0, 4.4), _axes(figure, 6.7, 2.0, 4.4)]
    voxel = np.asarray(source["voxel_um"], dtype=float)
    mask = source["slice_mask"].astype(bool)
    axes[0].imshow(
        mask, origin="lower", interpolation="nearest", cmap="Greys", vmin=0, vmax=2.2,
        extent=(-0.5 * voxel[0], (mask.shape[1] - 0.5) * voxel[0],
                -0.5 * voxel[1], (mask.shape[0] - 0.5) * voxel[1]),
    )
    for contour, color, label in (
        (raw_contour, "#737C83", "Measured mask contour"),
        (smooth_contour, BOUNDARY_COLOR, "Smoothed FEM outer contour"),
    ):
        closed_contour = _closed(contour)
        axes[0].plot(closed_contour[:, 0], closed_contour[:, 1], color=color, lw=1.5, label=label)
    axes[1].add_collection(_mesh(coordinates, cells, layers=layers))
    outer_curve = _closed(coordinates[outer])
    axes[1].plot(outer_curve[:, 0], outer_curve[:, 1], color=BOUNDARY_COLOR, lw=1.5)
    centroids = np.mean(coordinates[cells], axis=1)
    myocardial_indices = np.flatnonzero(layers == 2)
    if len(myocardial_indices):
        angle_order = np.argsort(np.arctan2(
            centroids[myocardial_indices, 1] - center[1],
            centroids[myocardial_indices, 0] - center[0],
        ))
        chosen = myocardial_indices[angle_order[np.linspace(0, len(angle_order) - 1, 20, dtype=int)]]
        tangent = np.asarray(data["active_tangents"], dtype=float)[chosen]
        tangent = tangent / np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1.0e-14)
        half_length = 0.021 * (2.0 * plot_half_side)
        segments = np.stack((centroids[chosen] - half_length * tangent,
                             centroids[chosen] + half_length * tangent), axis=1)
        axes[1].add_collection(LineCollection(segments, colors="#721E33", linewidths=1.6))
    for axis in axes:
        _spatial_axis(axis, bounds, style)
    add_top_information(
        axes[0], f"A  Image-derived section; slice {int(source['slice_z_index'])}", style=style,
    )
    add_top_information(axes[1], "B  FEM mesh; assumed internal layers", style=style)
    figure.legend(
        handles=[Line2D([0], [0], color="#737C83", lw=1.5, label="Measured mask contour"),
                 Line2D([0], [0], color=BOUNDARY_COLOR, lw=1.5, label="Smoothed outer contour"),
                 Line2D([0], [0], color="#721E33", lw=1.6, label="Assumed active direction")],
        loc="lower center", bbox_to_anchor=(0.5, 0.112), ncol=3, frameon=False,
    )
    figure.legend(
        handles=[Patch(facecolor=color, label=name) for color, name in zip(LAYER_COLORS, LAYER_NAMES)],
        loc="lower center", bbox_to_anchor=(0.5, 0.04), ncol=3, frameon=False,
    )
    exported.extend(_export(figure, axes, figures / "model_structure", style, overrides))

    style, overrides = _compact_style(4.2)
    figure = plt.figure(figsize=(14.2, 12.0))
    axes = [_axes(figure, 1.1, 6.7, 4.2), _axes(figure, 7.5, 6.7, 4.2),
            _axes(figure, 1.1, 1.3, 4.2), _axes(figure, 7.5, 1.3, 4.2)]
    axes[0].plot(phases, 100.0 * lumen_change, color="#1F4E79", lw=1.5, label="Assumed cavity")
    axes[0].plot(phases, 100.0 * outer_change, color="#BA3E34", lw=1.5, label="Outer section")
    axes[0].set_xlabel("Prescribed activation phase")
    axes[0].set_ylabel("Area change (%)")
    axes[0].set_xlim(float(phases[0]), float(phases[-1]))
    _bounded_ticks(axes[0].xaxis, *axes[0].get_xlim())
    _bounded_ticks(axes[0].yaxis, *axes[0].get_ylim())
    apply_axes_style(axes[0], style=style)
    axes[0].legend(loc="lower left", frameon=False)
    add_top_information(axes[0], "A  Quasi-static contraction / relaxation", style=style)
    field_specs = (
        (axes[1], equivalent[peak], stress_norm, "magma", (12.0, 6.7, 0.16, 4.2),
         "2-D equivalent stress (relative)", "B  Peak 2-D equivalent stress"),
        (axes[2], displacement_cells[peak], displacement_norm, "viridis", (5.65, 1.3, 0.16, 4.2),
         "Displacement magnitude (µm)", "C  Peak displacement; 1× geometry"),
        (axes[3], pressure[peak], pressure_norm, "coolwarm", (12.0, 1.3, 0.16, 4.2),
         "In-plane pressure (relative)", "D  Peak pressure: −tr(σ) / 2"),
    )
    for axis, values, norm, cmap, bar_position, label, heading in field_specs:
        collection = _mesh(states[peak], cells, values=values, norm=norm, cmap=cmap)
        axis.add_collection(collection)
        _reference(axis, coordinates, inner, outer)
        _spatial_axis(axis, bounds, style)
        add_top_information(axis, heading, style=style)
        _colorbar(figure, collection, bar_position, label, style)
    figure.text(0.5, 0.035, f"{qualification_label} · dashed reference contours · phase is not physiological time", ha="center")
    exported.extend(_export(figure, axes, figures / "fem_result", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(17.8, 5.2))
    axes = []
    for panel_index, state_index in enumerate(snapshot_indices):
        axis = _axes(figure, 0.85 + panel_index * 3.15, 1.4, 2.3)
        axes.append(axis)
        collection = _mesh(states[state_index], cells, values=equivalent[state_index], norm=stress_norm)
        axis.add_collection(collection)
        _reference(axis, coordinates, inner, outer)
        _spatial_axis(axis, bounds, style)
        add_top_information(axis, f"Phase {phases[state_index]:.2f}\nΔA cavity = {100*lumen_change[state_index]:.2f}%", style=style)
    _colorbar(figure, collection, (16.05, 1.4, 0.15, 2.3), "2-D stress (relative)", style)
    figure.text(0.46, 0.09, f"{qualification_label} · five saved states · actual 1× displacement · fixed scales", ha="center")
    exported.extend(_export(figure, axes, figures / "five_states", style, overrides))

    style, overrides = _compact_style(4.4)
    figure = plt.figure(figsize=(7.9, 7.4))
    axis = _axes(figure, 1.0, 1.4, 4.4)
    _spatial_axis(axis, bounds, style)
    collection = _mesh(states[0], cells, values=equivalent[0], norm=stress_norm)
    axis.add_collection(collection)
    _reference(axis, coordinates, inner, outer)
    _colorbar(figure, collection, (5.75, 1.4, 0.18, 4.4), "2-D equivalent stress (relative)", style)
    phase_text = add_top_information(axis, "", style=style, y=1.05)
    figure.text(0.5, 0.075, f"{qualification_label} · 1× deformation; dashed reference", ha="center")
    figure.text(0.5, 0.035, "Prescribed phase, not physiological time", ha="center")

    def update(frame: int) -> tuple[Any, ...]:
        collection.set_verts(states[frame][cells])
        collection.set_array(equivalent[frame])
        phase_text.set_text(
            f"Phase {phases[frame]:.2f}  |  activation {activation[frame]:.3f}\n"
            f"Assumed cavity area change {100*lumen_change[frame]:.2f}%"
        )
        return collection, phase_text

    update(peak)
    enforce_figure_typography(figure, [axis], style=style)
    gif_layout = validate_figure(figure, [axis], style=style, overrides=overrides)
    if not gif_layout.passed:
        plt.close(figure)
        raise ValueError("GIF layout validation failed: " + "; ".join(gif_layout.issues))
    animation = FuncAnimation(figure, update, frames=len(phases), interval=100, blit=False)
    gif_path = figures / "fem_active_cycle.gif"
    animation.save(gif_path, writer=PillowWriter(fps=10), dpi=100)
    plt.close(figure)
    with Image.open(gif_path) as gif_image:
        gif_frames = int(getattr(gif_image, "n_frames", 1))
        gif_size = list(gif_image.size)
    if gif_frames != len(phases):
        raise ValueError(f"GIF contains {gif_frames} frames; expected all {len(phases)} saved states.")
    exported.append(gif_path)

    interpretation = (
        "The outer contour comes from a real zebrafish tissue-mask section. "
        "The cavity, internal layer interfaces and active directions are model assumptions. "
        "Small-strain, two-dimensional FEM fields use relative material/stress units; "
        "in-plane pressure is -tr(sigma)/2, not cavity or blood pressure. "
        "The 2-D equivalent stress is not a reconstructed 3-D von Mises stress. "
        "No blood flow or physiological time/material calibration is included."
    )
    report = {
        "schema_version": "prl.fem_measured_contour_rendering.v1",
        "status": "passed",
        "fem_qualification_status": qualification_status,
        "source_level": "G1",
        "actual_state_count": int(len(phases)),
        "snapshot_indices": snapshot_indices.tolist(),
        "snapshot_phases": phases[snapshot_indices].tolist(),
        "deformation_scale": 1.0,
        "physical_length_unit": "µm",
        "fixed_spatial_bounds_um": list(bounds),
        "fixed_equivalent_stress_bounds": [0.0, stress_limit],
        "fixed_in_plane_pressure_bounds": [-pressure_limit, pressure_limit],
        "gif": {"frames": gif_frames, "pixels": gif_size, "fps": 10, "layout": gif_layout.as_dict()},
        "peak_phase": float(phases[peak]),
        "peak_lumen_area_change_percent": float(100 * lumen_change[peak]),
        "peak_outer_area_change_percent": float(100 * outer_change[peak]),
        "peak_maximum_displacement_um": float(np.max(displacement_magnitude[peak])),
        "figures": [path.relative_to(result).as_posix() for path in exported],
        "interpretation_boundary": interpretation,
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failure_text = ""
    if qualification_status == "failed":
        failure_text = (
            "<p class=\"note\"><strong>Qualification FAILED：本次力学资格验收未通过。</strong>"
            "以下图像保留失败试算的真实状态，用于诊断，不构成已验证的斑马鱼收缩结果。"
            "局部应变超出本试算的小应变门限，且两级网格的腔面积变化尚未收敛。</p>"
        )
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>斑马鱼真实外轮廓 FEM</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1150px;margin:32px auto;padding:0 24px;color:#243442}}img{{max-width:100%;height:auto}}figure{{margin:25px 0}}.note{{background:#f1f5f7;padding:18px;border-left:4px solid #377392}}a{{color:#1f5b86}}</style>
<h1>真实斑马鱼外轮廓驱动的二维 FEM</h1>
{failure_text}
<p class="note">使用真实组织掩膜截面的外轮廓。腔室、心内膜/ECM/心肌层厚度和主动方向均为建模假设。
这是小应变、准静态 FEM 工程试算，尚未标定生理时间、材料参数或血流；分割单个细胞不是本试算的前提。</p>
<p>数值独立验证：{escape(qualification_status)}。保存 {len(phases)} 个状态；下图位移均为真实 1× 显示。
峰值假设腔面积变化 {100*lumen_change[peak]:.3f}%，外轮廓包围面积变化 {100*outer_change[peak]:.3f}%，
最大位移 {np.max(displacement_magnitude[peak]):.3f} µm。</p>
<figure><img src="figures/model_structure.png" alt="真实掩膜外轮廓与假设三层 FEM 网格"><figcaption>真实输入和建模假设同时展示。各层是连续有限元材料区。</figcaption></figure>
<figure><img src="figures/fem_active_cycle.gif" alt="41个 FEM 状态，固定坐标及应力色标，1倍位移"><figcaption>41 状态动画：固定视野与色标，虚线为参考轮廓。phase 是指定的激活相位。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="五个保存状态的实际形变与应力"><figcaption>五个真实求解器状态，采用相同空间范围和应力范围。</figcaption></figure>
<figure><img src="figures/fem_result.png" alt="面积变化、应力、位移及平面压力"><figcaption>应力为相对量；平面压力 −tr(σ)/2 不是腔压，二维等效应力不代表完整三维 von Mises 应力。</figcaption></figure>
<p><a href="configuration.json">配置与假设</a> · <a href="verification.json">独立验证</a> · <a href="rendering.json">渲染记录</a> · <a href="raw/G1.npz">41个原始 FEM 状态</a> · <a href="geometry_source.npz">几何来源</a></p>
</html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    return report
