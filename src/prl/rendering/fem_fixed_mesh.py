"""Render saved fixed-geometry FEM refinement evidence without new solves."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FixedLocator
import numpy as np

from prl.rendering.cb_plot_unified_style import add_top_information, apply_axes_style
from prl.rendering.fem_measured_contour import (
    LAYER_COLORS, LAYER_NAMES, _axes, _bounded_ticks, _closed, _colorbar,
    _compact_style, _export, _load, _mesh, _reference, _spatial_axis,
)


LABELS = ("L0", "L1", "L2")
COLORS = ("#7197B7", "#C57535", "#174E71")


def _raster_mesh(positions, cells, **kwargs):
    collection = _mesh(positions, cells, **kwargs)
    collection.set_rasterized(True)
    if len(cells) > 20000:
        collection.set_linewidth(0.025)
    return collection


def _square_bounds(points: np.ndarray, padding: float = 0.565):
    low, high = points.min(axis=0), points.max(axis=0)
    middle = (low + high) / 2
    half = float(np.max(high - low)) * padding
    return (float(middle[0]-half), float(middle[0]+half),
            float(middle[1]-half), float(middle[1]+half))


def _count_axis(axis, counts, style):
    axis.set_xscale("log")
    axis.set_xlim(float(min(counts)) / 1.65, float(max(counts)) * 1.7)
    axis.xaxis.set_major_locator(FixedLocator(counts))
    axis.set_xticklabels([f"{count/1000:.1f}" for count in counts])
    axis.set_xlabel("Triangles (thousands; log scale)")
    _bounded_ticks(axis.yaxis, *axis.get_ylim())
    apply_axes_style(axis, style=style)


def render_fem_fixed_mesh(result: Path) -> dict[str, Any]:
    """Render L0/L1/L2 arrays, preserving physical bounds and deformation scale."""
    result = Path(result).resolve()
    config = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification = json.loads((result / "verification.json").read_text(encoding="utf-8"))
    status = str(verification.get("status", "unknown"))
    quality = f"Qualification {status.upper()}"
    data = {label: _load(result / "raw" / f"{label}.npz") for label in LABELS}
    phases = np.asarray([0.0, .25, .5, .75, 1.0])
    for label, payload in data.items():
        if payload["phases"].shape != (5,) or not np.allclose(payload["phases"], phases, atol=1e-14, rtol=0):
            raise ValueError(f"{label} must contain exactly the five registered states")
        for key in ("coordinates", "displacements", "equivalent_stress", "strains"):
            if not np.all(np.isfinite(payload[key])):
                raise ValueError(f"{label}: nonfinite {key}")
    scale = float(config["geometry"]["length_scale_um"])
    center = np.asarray(config["geometry"]["center_um"], dtype=float)
    positions = {label: payload["coordinates"] * scale + center for label, payload in data.items()}
    states = {label: positions[label][None] + payload["displacements"] * scale for label, payload in data.items()}
    bounds = _square_bounds(np.concatenate([item.reshape(-1, 2) for item in states.values()]))
    peak = int(np.argmax(data["L2"]["activation"]))
    norm = Normalize(0.0, max(float(np.max(data["L2"]["equivalent_stress"])), 1e-14))
    counts = [len(data[label]["cells"]) for label in LABELS]
    cavity = [float(data[label]["lumen_fraction_change"][peak] * 100) for label in LABELS]
    maximum_strain = [float(np.max(np.abs(data[label]["strains"])) * 100) for label in LABELS]
    workspace = next((folder for folder in result.parents if (folder / "START_HERE.md").is_file()), None)
    source_path = Path(config["source_path"])
    if not source_path.is_absolute():
        if workspace is None:
            raise ValueError("Cannot resolve declared F2 source without the PRL workspace")
        source_path = workspace / source_path
    old_data = {label: _load(source_path.parent / f"{label}.npz") for label in ("G0", "G1")}
    old_counts = [len(old_data[label]["cells"]) for label in ("G0", "G1")]
    old_cavity = [float(old_data[label]["lumen_fraction_change"][int(np.argmax(old_data[label]["activation"]))] * 100)
                  for label in ("G0", "G1")]
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    exports: list[Path] = []

    # Fixed source patch is selected by the retained L0 maximum strain, not by
    # the refined result; neither contour nor active directions are regenerated.
    coarse = data["L0"]
    patch_cell = int(np.argmax(np.max(np.abs(coarse["strains"][peak]), axis=1)))
    patch_center = np.mean(positions["L0"][coarse["cells"][patch_cell]], axis=0)
    half_patch = 10.0
    patch_bounds = (float(patch_center[0]-half_patch), float(patch_center[0]+half_patch),
                    float(patch_center[1]-half_patch), float(patch_center[1]+half_patch))
    style, overrides = _compact_style(3.6)
    figure = plt.figure(figsize=(15.9, 6.4))
    axes = [_axes(figure, 1.25 + index*4.9, 1.75, 3.6) for index in range(3)]
    axes[0].add_collection(_raster_mesh(positions["L0"], coarse["cells"], layers=coarse["cell_layers"]))
    axes[0].add_patch(Rectangle((patch_bounds[0], patch_bounds[2]), 20, 20,
                               fill=False, edgecolor="#B23439", linewidth=1.5))
    _spatial_axis(axes[0], bounds, style)
    add_top_information(axes[0], "A  Frozen geometry and three layers", style=style)
    for axis, label, panel in zip(axes[1:], ("L0", "L2"), ("B", "C")):
        payload = data[label]
        axis.add_collection(_raster_mesh(positions[label], payload["cells"], layers=payload["cell_layers"]))
        _spatial_axis(axis, patch_bounds, style)
        add_top_information(axis, f"{panel}  {label}: same 20 µm patch", style=style)
    figure.legend(handles=[Patch(facecolor=color, label=name) for color, name in zip(LAYER_COLORS, LAYER_NAMES)],
                  loc="lower center", bbox_to_anchor=(.5, .12), ncol=3, frameon=False)
    figure.text(.5, .060, "Only elements subdivided; geometry, layers and active tensor held fixed", ha="center")
    figure.text(.5, .021, f"{quality} · synthetic materials · free boundaries; no lumen pressure", ha="center")
    # Bottom text uses explicit margin inside the canvas, not automatic cropping.
    figure.texts[-1].set_y(.048)
    figure.texts[-2].set_y(.088)
    exports.extend(_export(figure, axes, figures / "model_structure", style, overrides))

    style, overrides = _compact_style(4.2)
    figure = plt.figure(figsize=(14.3, 12.5))
    axes = [_axes(figure, 1.15, 7.2, 4.2), _axes(figure, 7.65, 7.2, 4.2),
            _axes(figure, 1.15, 1.8, 4.2), _axes(figure, 7.65, 1.8, 4.2)]
    axes[0].plot(old_counts, old_cavity, color="#858585", marker="D", mfc="white", ls="--", lw=1.5,
                 label="Prior F2: geometry + load vary")
    axes[0].plot(counts, cavity, color=COLORS[2], marker="o", lw=1.5, label="L0–L2: fixed geometry + load")
    axes[0].set_ylabel("Peak cavity area change (%)")
    _count_axis(axes[0], sorted(set(old_counts+counts)), style)
    add_top_information(axes[0], "A  Global response; two distinct series", style=style)
    axes[0].legend(loc="upper left", frameon=False)
    payload = data["L2"]
    collection = _raster_mesh(states["L2"][peak], payload["cells"], values=payload["equivalent_stress"][peak], norm=norm)
    axes[1].add_collection(collection)
    _reference(axes[1], positions["L2"], payload["inner_nodes"], payload["outer_nodes"])
    _spatial_axis(axes[1], bounds, style)
    add_top_information(axes[1], "B  L2 peak small-strain stress; 1×", style=style)
    _colorbar(figure, collection, (12.15, 7.2, .16, 4.2), "2-D equivalent stress (relative)", style)
    for label, color in zip(LABELS, COLORS):
        axes[2].plot(phases, data[label]["lumen_fraction_change"]*100, marker="o", color=color, lw=1.5, label=label)
    axes[2].set_xlim(0, 1)
    axes[2].set_xlabel("Prescribed activation phase")
    axes[2].set_ylabel("Cavity area change (%)")
    _bounded_ticks(axes[2].xaxis, 0, 1)
    _bounded_ticks(axes[2].yaxis, *axes[2].get_ylim())
    apply_axes_style(axes[2], style=style)
    axes[2].legend(loc="lower right", frameon=False)
    add_top_information(axes[2], "C  Five solved states per resolution", style=style)
    axes[3].plot(counts, maximum_strain, marker="o", color="#B33A3A", lw=1.5, label="Maximum strain component")
    axes[3].axhline(5.0, color="#555555", ls="--", lw=1.5, label="Frozen 5% applicability gate")
    axes[3].set_ylabel("Maximum absolute strain (%)")
    _count_axis(axes[3], counts, style)
    add_top_information(axes[3], "D  Small-strain validity kept separate", style=style)
    axes[3].legend(loc="upper left", frameon=False)
    figure.text(.5, .050, f"{quality} · assumed cavity/layers · uncalibrated materials and stress", ha="center")
    figure.text(.5, .023, "Prescribed phase is not physiological time; connecting lines are only guides", ha="center")
    exports.extend(_export(figure, axes, figures / "fem_result", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(17.8, 5.2))
    axes = []
    for index, phase in enumerate(phases):
        axis = _axes(figure, .85+index*3.15, 1.4, 2.3)
        axes.append(axis)
        collection = _raster_mesh(states["L2"][index], payload["cells"], values=payload["equivalent_stress"][index], norm=norm)
        axis.add_collection(collection)
        _reference(axis, positions["L2"], payload["inner_nodes"], payload["outer_nodes"])
        _spatial_axis(axis, bounds, style)
        add_top_information(axis, f"Phase {phase:.2f}\nΔA cavity = {100*payload['lumen_fraction_change'][index]:.2f}%", style=style)
    _colorbar(figure, collection, (16.05, 1.4, .15, 2.3), "2-D stress (relative)", style)
    figure.text(.46, .09, f"{quality} · five actual L2 states · 1× displacement · fixed scales", ha="center")
    exports.extend(_export(figure, axes, figures / "five_states", style, overrides))

    report = {
        "schema_version": "prl.fem_fixed_mesh_rendering.v1", "status": "passed",
        "fem_qualification_status": status,
        "engineering_consistency": verification.get("engineering_consistency", "unknown"),
        "mesh_response_convergence": verification.get("mesh_response_convergence", "unknown"),
        "small_strain_applicability": verification.get("small_strain_applicability", "unknown"),
        "levels": list(LABELS), "triangle_counts": counts, "actual_state_count_per_level": 5,
        "snapshot_indices": list(range(5)), "snapshot_phases": phases.tolist(),
        "deformation_scale": 1.0, "fixed_spatial_bounds_um": list(bounds),
        "fixed_equivalent_stress_bounds": [float(norm.vmin), float(norm.vmax)],
        "structure_patch": {"selection": "peak maximum absolute L0 strain component", "source_cell": patch_cell,
                            "bounds_um": list(patch_bounds)},
        "peak_cavity_area_change_percent": dict(zip(LABELS, cavity)),
        "maximum_absolute_strain_percent": dict(zip(LABELS, maximum_strain)),
        "prior_F2_reference": {"source": str(source_path.parent), "triangle_counts": old_counts,
                               "peak_cavity_area_change_percent": old_cavity,
                               "scope": "distinct reference: geometry and active tensor changed together"},
        "exports": [path.relative_to(result).as_posix() for path in exports],
        "dense_mesh_svg_rasterized": True, "svg_text_and_axes_editable": True,
        "gif": "not_run; no invented intermediate states",
        "interpretation": "Only the outer contour is measured. Cavity and layers are assumed; materials and activation are synthetic. "
                          "Five states are prescribed static loads, not physiological time. Equivalent stress is the declared 2-D invariant, "
                          "not full 3-D von Mises. Global mesh-response qualification does not imply local peak-stress convergence.",
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = "".join(f"<tr><td>{label}</td><td>{count:,}</td><td>{change:.4f}%</td><td>{strain:.4f}%</td></tr>"
                   for label, count, change, strain in zip(LABELS, counts, cavity, maximum_strain))
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F3-A 固定几何 FEM 网格资格</title><style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;color:#263d4b}}img{{max-width:100%}}.note{{background:#f2f5f7;border-left:4px solid #a9453b;padding:16px}}table{{border-collapse:collapse}}th,td{{padding:7px 18px;border-bottom:1px solid #d8dfe3}}a{{color:#1b608b}}</style>
<h1>F3-A｜同一真实外轮廓上的固定几何 FEM 网格资格</h1>
<p class="note">整体资格：<strong>{escape(status)}</strong>；工程重算 {escape(str(report['engineering_consistency']))}，全局网格响应 {escape(str(report['mesh_response_convergence']))}，小应变适用性 {escape(str(report['small_strain_applicability']))}。
求解和绘图完成不等于物理适用性通过，更不等于斑马鱼生物验证。</p>
<p>固定 F2 G1 的多边形、材料区域和主动张量，只将三角形四分。材料 E/E_ref=1/0.5/2.5、nu=0.30 是合成假设；二维平面应变，不是三维心脏。
峰值3%激活由规定余弦函数给出，五个相位各自求静力平衡，没有秒或心率。外轮廓来自真实图像，内部腔面和分层仍是假设。</p>
<table><thead><tr><th>级别</th><th>三角形</th><th>峰值腔面积变化</th><th>最大应变</th></tr></thead><tbody>{rows}</tbody></table>
<figure><img src="figures/model_structure.png" alt="固定三层形状与同一区域网格四分"><figcaption>红框在各级对应同一20 µm区域。细化不改善原有三角形最小角，也不增加真实解剖信息。</figcaption></figure>
<figure><img src="figures/fem_result.png" alt="固定几何收敛、局部应力、五相位响应及小应变门"><figcaption>灰色F2参照改变了几何和载荷，不与蓝色固定几何序列混作同一收敛曲线。应力为未标定相对量。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="L2五个实际求解状态"><figcaption>五个真实静力状态、固定坐标和色标、真实1倍位移；虚线是初始轮廓。没有显示插值或虚构动态帧。</figcaption></figure>
<p><a href="configuration.json">配置与参数来源</a> · <a href="verification.json">独立验证</a> · <a href="rendering.json">渲染记录</a> ·
<a href="raw/L0.npz">L0原状态</a> · <a href="raw/L1.npz">L1原状态</a> · <a href="raw/L2.npz">L2原状态</a></p></html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    return report
