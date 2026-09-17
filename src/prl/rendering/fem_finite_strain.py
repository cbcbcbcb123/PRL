"""Render retained 3-D finite-strain qualification states; never call a solver.

Orthogonal views are explicitly projections of 3-D Q2/Q1 engineering meshes,
not 2-D mechanics or a reconstructed heart.  Spatial interpolation draws Q2
element edges from saved nodes; no temporal frames or displacements are made up.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.ticker import FixedLocator
import numpy as np

from prl.rendering.cb_plot_unified_style import add_top_information, apply_axes_style
from prl.rendering.fem_measured_contour import (
    _axes, _bounded_ticks, _colorbar, _compact_style, _export, _load,
)


BLUE = "#225A80"
ORANGE = "#C87837"
GREEN = "#368267"
RED = "#B3463E"
GREY = "#6C7880"


def _surface_polygons(payload, positions, normal_axis=2):
    """Q2 element face boundaries at the lowest reference coordinate plane.

    Every face uses all nine saved Q2 nodes.  The twelve points per edge only
    evaluate its spatial shape functions; they are not extra FEM/time states.
    Returned IDs locate the owning 3-D element for element-average coloring.
    """
    reference = payload["coordinates"]
    minimum = float(np.min(reference[:, normal_axis]))
    t = np.linspace(-1.0, 1.0, 13)
    uv = np.concatenate((np.column_stack((t, -np.ones_like(t))),
                         np.column_stack((np.ones_like(t), t)),
                         np.column_stack((t[::-1], np.ones_like(t))),
                         np.column_stack((-np.ones_like(t), t[::-1]))))

    def q2(values):
        return np.column_stack((values * (values - 1) / 2, 1 - values**2,
                                values * (values + 1) / 2))

    first, second = q2(uv[:, 0]), q2(uv[:, 1])
    view_axes = [index for index in range(3) if index != normal_axis]
    polygons, element_ids = [], []
    for element_id, indices in enumerate(payload["cells"]):
        face = np.take(indices.reshape(3, 3, 3), 0, axis=normal_axis)
        if not np.allclose(reference[face, normal_axis], minimum, atol=1e-12, rtol=0):
            continue
        curve = np.einsum("pa,pb,abj->pj", first, second, positions[face])
        polygons.append(curve[:, view_axes])
        element_ids.append(element_id)
    if not polygons:
        raise ValueError("No saved Q2 face was found for the requested 3-D projection")
    return polygons, np.asarray(element_ids, dtype=int)


def _surface(axis, payload, positions, normal_axis=2, *, values=None, norm=None, reference=False):
    polygons, element_ids = _surface_polygons(payload, positions, normal_axis)
    if reference:
        collection = PolyCollection(polygons, facecolors="none", edgecolors=GREY,
                                    linewidths=0.85, linestyles="--", zorder=4)
    elif values is None:
        collection = PolyCollection(polygons, facecolors="#D7E7EF", edgecolors=BLUE,
                                    linewidths=0.9)
    else:
        collection = PolyCollection(polygons, array=np.asarray(values)[element_ids],
                                    norm=norm, cmap="magma", edgecolors="#40545F",
                                    linewidths=0.55)
    axis.add_collection(collection)
    return collection


def _square_bounds(points, padding=0.14):
    low, high = points.min(axis=0), points.max(axis=0)
    middle = (low + high) / 2
    half = 0.5 * float(np.max(high - low)) * (1 + 2 * padding)
    return (float(middle[0] - half), float(middle[0] + half),
            float(middle[1] - half), float(middle[1] + half))


def _spatial(axis, bounds, style, vertical="y"):
    axis.set_xlim(bounds[0], bounds[1])
    axis.set_ylim(bounds[2], bounds[3])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (model length)")
    axis.set_ylabel(f"{vertical} (model length)")
    _bounded_ticks(axis.xaxis, bounds[0], bounds[1], bins=3)
    _bounded_ticks(axis.yaxis, bounds[2], bounds[3], bins=3)
    apply_axes_style(axis, style=style)


def _quantitative(axis, style, xlabel, ylabel):
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    _bounded_ticks(axis.xaxis, *axis.get_xlim(), bins=4)
    _bounded_ticks(axis.yaxis, *axis.get_ylim(), bins=4)
    apply_axes_style(axis, style=style)


def _gauss_mean(values):
    """Reference-volume average on each affine 3x3x3 Gauss element."""
    weights = np.polynomial.legendre.leggauss(3)[1]
    weights = np.einsum("a,b,c->abc", weights, weights, weights).ravel() / 8.0
    return np.einsum("...eq,q->...e", np.asarray(values), weights)


def _active_fiber_cauchy(payload, fiber):
    direction = np.asarray(fiber, dtype=float)
    direction /= np.linalg.norm(direction)
    current = payload["F"] @ direction
    magnitude = np.sum(current * current, axis=-1)
    magnitude *= payload["activation"][:, None, None] / payload["J"]
    return _gauss_mean(magnitude)


def _total_von_mises(payload):
    stress = payload["Cauchy"]
    deviator = stress - np.trace(stress, axis1=-2, axis2=-1)[..., None, None] * np.eye(3) / 3
    return _gauss_mean(np.sqrt(1.5 * np.sum(deviator * deviator, axis=(-2, -1))))


def render_fem_finite_strain(result: Path) -> dict[str, Any]:
    """Render complete retained cases without hiding an incomplete stage.

    A registered case may contain a valid prefix after a solver failure.  Its
    missing states are never interpolated; every case actually plotted below
    must still have all its registered states.  The stage verdict is read from
    the independent verification and cannot be upgraded by rendering.
    """
    result = Path(result).resolve()
    config = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification = json.loads((result / "verification.json").read_text(encoding="utf-8"))
    status = str(verification.get("status", "unknown"))
    cases = config["cases"]
    data = {name: _load(result / "raw" / f"{name}.npz") for name in cases}
    incomplete_cases = {}
    for name, payload in data.items():
        expected = np.asarray(cases[name]["phases"])
        actual = payload["phases"]
        if actual.ndim != 1 or not 0 < len(actual) <= len(expected) or not np.allclose(actual, expected[:len(actual)], rtol=0, atol=1e-14):
            raise ValueError(f"{name}: saved states are not an exact registered prefix")
        if len(actual) != len(expected):
            incomplete_cases[name] = {"retained_states": len(actual), "registered_states": len(expected)}
        if payload["cells"].ndim != 2 or payload["cells"].shape[1] != 27 or payload["coordinates"].shape[1] != 3:
            raise ValueError(f"{name}: expected a saved 3-D Q2 mesh")
        for key in ("coordinates", "displacements", "F", "Cauchy", "J", "reaction"):
            if not np.all(np.isfinite(payload[key])):
                raise ValueError(f"{name}: nonfinite saved {key}")
    if incomplete_cases and status == "passed":
        raise ValueError("An incomplete registered stage cannot have a passed qualification")
    if any(name != "nh_rigid_rotation" for name in incomplete_cases):
        raise ValueError("A case required by the three evidence figures is incomplete; no replacement states will be made")

    def metrics(name):
        return verification["cases"][name]["metrics"]

    def nominal_reaction(name):
        area = cases[name]["lengths"][1] * cases[name]["lengths"][2]
        return np.asarray(metrics(name)["axial_reaction"]) / area

    active_name = "guccione_active_k1000"
    active = data[active_name]
    positions = active["coordinates"][None] + active["displacements"]
    active_color = _active_fiber_cauchy(active, cases[active_name]["fiber"])
    active_norm = Normalize(0.0, max(float(np.max(active_color)), 1e-14))
    active_bounds = _square_bounds(positions[..., :2].reshape(-1, 2))
    snapshots = [0, 2, 4, 6, 8]
    if len(active["phases"]) != 9:
        raise ValueError("The registered active Guccione case must contain nine actual states")
    figure_folder = result / "figures"
    figure_folder.mkdir(exist_ok=True)
    exports = []

    # Geometry/load panels are direct projections of the actual saved 3-D mesh.
    style, overrides = _compact_style(4.0)
    figure = plt.figure(figsize=(14.5, 12.4))
    axes = [_axes(figure, 1.5, 7.15, 4.0), _axes(figure, 8.0, 7.15, 4.0),
            _axes(figure, 1.5, 1.8, 4.0), _axes(figure, 8.0, 1.8, 4.0)]
    for axis, normal, label in ((axes[0], 2, "A  3-D block: XY surface view"),
                                 (axes[1], 1, "B  Same 3-D block: XZ view")):
        _surface(axis, active, active["coordinates"], normal)
        projected = active["coordinates"][:, [0, 1 if normal == 2 else 2]]
        _spatial(axis, _square_bounds(projected), style, "y" if normal == 2 else "z")
        add_top_information(axis, label, style=style)
        axis.plot([0, 0], [0, 1], color=RED, lw=2)
        axis.plot([0, 2], [0, 0], color=RED, lw=2)
        axis.annotate("", xy=(1.65, .55), xytext=(.4, .55),
                      arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 1.8})
        axis.text(.08, .92, "Reference fiber: x", transform=axis.transAxes, va="top")
        axis.text(.08, .08, "Normal symmetry constraints", transform=axis.transAxes)
    beam_name = "nh_bending_fine_k1000"
    beam = data[beam_name]
    beam_positions = beam["coordinates"] + beam["displacements"][-1]
    beam_bounds = _square_bounds(np.concatenate((beam["coordinates"][:, :2], beam_positions[:, :2])))
    _surface(axes[2], beam, beam["coordinates"], 1)
    _spatial(axes[2], _square_bounds(beam["coordinates"][:, [0, 2]]), style, "z")
    add_top_information(axes[2], "C  3-D beam: reference XZ view", style=style)
    axes[2].plot([0, 0], [0, 1], color=RED, lw=3)
    axes[2].text(.06, .89, "x = 0: all displacement fixed", transform=axes[2].transAxes)
    axes[2].text(.06, .08, "Tip load: +y (out of this plane)", transform=axes[2].transAxes)
    beam_stress = _total_von_mises(beam)[-1]
    beam_norm = Normalize(0.0, max(float(np.max(beam_stress)), 1e-14))
    collection = _surface(axes[3], beam, beam_positions, values=beam_stress, norm=beam_norm)
    _surface(axes[3], beam, beam["coordinates"], reference=True)
    _spatial(axes[3], beam_bounds, style)
    add_top_information(axes[3], "D  Loaded beam: XY view; 1×", style=style)
    _colorbar(figure, collection, (12.35, 1.8, .16, 4.0), "Total 3-D von Mises (relative)", style)
    figure.text(.5, .075, "3-D Q2 displacement / Q1 pressure; dimensionless engineering blocks, NOT a heart", ha="center")
    figure.text(.5, .038, "Red: constraints; dashed: reference; color: element-averaged total stress in D", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "model_structure", style, overrides))

    style, overrides = _compact_style(4.2)
    figure = plt.figure(figsize=(14.5, 12.8))
    axes = [_axes(figure, 1.5, 7.45, 4.2), _axes(figure, 8.0, 7.45, 4.2),
            _axes(figure, 1.5, 1.9, 4.2), _axes(figure, 8.0, 1.9, 4.2)]
    for bulk, color, marker in ((100, ORANGE, "s"), (1000, BLUE, "o")):
        fine_name = f"nh_stretch_fine_k{bulk}"
        stretch = data[fine_name]["prescribed_stretch"]
        analytic = verification["cases"][fine_name]["analytic_reference"]["nominal_axial_stress"]
        axes[0].plot(stretch, analytic, color=color, ls="--", lw=1.5, label=f"Analytic κ={bulk}")
        axes[0].plot(stretch, nominal_reaction(fine_name), color=color, marker=marker,
                     mfc="white", ls="none", markersize=6, label=f"FEM κ={bulk}")
    _quantitative(axes[0], style, "Prescribed axial stretch λ", "Nominal axial stress (relative)")
    add_top_information(axes[0], "A  NH stretch: finite-κ analytic check", style=style)
    axes[0].legend(loc="upper left", frameon=False)
    for direction, color in (("fiber_x", BLUE), ("fiber_y", ORANGE)):
        name = f"guccione_stretch_{direction}"
        axes[1].plot(data[name]["prescribed_stretch"], nominal_reaction(name), color=color,
                     marker="o", lw=1.5, label="Fiber along x" if direction == "fiber_x" else "Fiber along y")
    _quantitative(axes[1], style, "Prescribed axial stretch λ", "Nominal axial stress (relative)")
    add_top_information(axes[1], "B  Guccione: prescribed fiber direction", style=style)
    axes[1].legend(loc="upper left", frameon=False)
    mean_f = np.asarray(metrics(active_name)["mean_F"])
    directional_stretch = np.linalg.norm(mean_f, axis=1)
    for component, color, label in ((0, BLUE, "Fiber stretch λx"), (1, ORANGE, "Transverse λy"),
                                     (2, GREEN, "Transverse λz")):
        axes[2].plot(active["phases"], directional_stretch[:, component], color=color, marker="o",
                     lw=1.5, ls="--" if component == 2 else "-", label=label)
    axes[2].set_xlim(0, 1)
    _quantitative(axes[2], style, "Prescribed activation phase", "Solved directional stretch")
    add_top_information(axes[2], "C  Active Guccione: nine equilibria", style=style)
    axes[2].legend(loc="center", frameon=False)
    beam_tips = {}
    for bulk, color in ((100, ORANGE), (1000, BLUE)):
        names = [f"nh_bending_{level}_k{bulk}" for level in ("coarse", "fine")]
        counts = [len(data[name]["cells"]) for name in names]
        tips = [float(metrics(name)["tip_mean_uy"][-1]) for name in names]
        beam_tips[str(bulk)] = {"hex_counts": counts, "mean_tip_uy": tips}
        axes[3].plot(counts, tips, color=color, marker="o", lw=1.5, label=f"κ/μ = {bulk}")
    _quantitative(axes[3], style, "Q2/Q1 hexahedra", "Mean tip-face displacement uy")
    axes[3].xaxis.set_major_locator(FixedLocator(counts))
    add_top_information(axes[3], "D  Beam: mesh / bulk sensitivity", style=style)
    axes[3].legend(loc="best", frameon=False)
    stage_note = " · rigid-rotation solve incomplete" if incomplete_cases else ""
    figure.text(.5, .075, f"Engineering qualification {status.upper()}{stage_note} · gates in verification.json", ha="center")
    figure.text(.5, .04, "Parameters uncalibrated; markers are solved states; connecting lines are guides, not physiological time", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "mechanics_results", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(18.4, 5.8))
    axes = []
    for panel, state in enumerate(snapshots):
        axis = _axes(figure, 1.0 + 3.2 * panel, 1.65, 2.3)
        axes.append(axis)
        collection = _surface(axis, active, positions[state], values=active_color[state], norm=active_norm)
        _surface(axis, active, active["coordinates"], reference=True)
        _spatial(axis, active_bounds, style)
        add_top_information(axis, f"Phase {active['phases'][state]:.2f}\nλx = {directional_stretch[state, 0]:.3f}", style=style)
    _colorbar(figure, collection, (16.5, 1.65, .15, 2.3), "Active fiber Cauchy (relative)", style)
    figure.text(.48, .12, "Five actual 3-D Guccione states, XY surface projection · 1× displacement · fixed axes and color scale", ha="center")
    figure.text(.48, .07, "Color = active component T |F f0|² / J, NOT total stress; phase is not seconds or heart rate", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "five_states", style, overrides))

    report = {
        "schema_version": "prl.fem_finite_strain_rendering.v1", "status": "passed",
        "qualification_status": status, "case_count": len(cases),
        "complete_case_count": len(cases) - len(incomplete_cases), "incomplete_cases": incomplete_cases,
        "state_counts": {name: len(payload["phases"]) for name, payload in data.items()},
        "biological_validation": "not_run", "heart_geometry": "not_run",
        "snapshot_case": active_name, "snapshot_indices": snapshots,
        "snapshot_phases": active["phases"][snapshots].tolist(),
        "deformation_scale": 1.0, "snapshot_projection": "XY surface of 3-D Q2/Q1 solid",
        "snapshot_bounds": list(active_bounds),
        "active_color_bounds": [float(active_norm.vmin), float(active_norm.vmax)],
        "active_color_definition": "reference-volume element mean of T*|F*f0|^2/J; active Cauchy fiber component, not total stress",
        "beam_color_definition": "reference-volume element mean of sqrt(3/2 dev(total Cauchy):dev(total Cauchy))",
        "directional_stretch": directional_stretch.tolist(), "beam_tip_comparison": beam_tips,
        "beam_tip_definition": "Q2 reference-face-area weighted mean of saved tip y displacement, from independent verifier",
        "source_state_values": "raw files and independent verification metrics only; renderer calls no solver",
        "spatial_display_interpolation": "quadratic saved Q2 node interpolation along visible element edges",
        "exports": [path.relative_to(result).as_posix() for path in exports],
        "gif": "not_run; five selected true states shown, all nine retained in raw",
        "interpretation": "3-D finite-strain engineering blocks and beams, not a zebrafish ventricle. Materials uncalibrated. Prescribed active load phase is not physiological time.",
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = "".join(f"<tr><td>{escape(name)}</td><td>{len(payload['cells'])}</td><td>{len(payload['phases'])} / {len(cases[name]['phases'])}</td><td>{escape(str(verification['cases'][name].get('status', 'unknown')))}</td></tr>"
                   for name, payload in data.items())
    incomplete_note = ""
    if incomplete_cases:
        retained = incomplete_cases["nh_rigid_rotation"]["retained_states"]
        requested = incomplete_cases["nh_rigid_rotation"]["registered_states"]
        angles = cases["nh_rigid_rotation"]["rotation_degrees"]
        saved_angles = "、".join(f"{angle:g}°" for angle in angles[:retained])
        missing_angles = "、".join(f"{angle:g}°" for angle in angles[retained:])
        incomplete_note = f"<p class=\"note\">本阶段整体为 failed，不能因下方部分图件正常而改为通过。{len(cases)-len(incomplete_cases)}个工况保存完整；刚体转动工况仅保存 {retained}/{requested} 个状态（{saved_angles}）。{missing_angles}均没有已求解的有效状态，本页不生成或展示这些缺失帧。停止原因见 <a href=\"failure.json\">原始失败记录</a>。刚转求解资格未完成，不否定材料点客观性单独检查，也不能用后者替代前者。</p>"
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F3-B 三维有限变形 FEM 工程资格</title><style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;color:#263d4b}}img{{max-width:100%}}.note{{background:#f2f5f7;border-left:4px solid #a9453b;padding:16px}}table{{border-collapse:collapse}}th,td{{padding:7px 18px;border-bottom:1px solid #d8dfe3}}a{{color:#1b608b}}</style>
<h1>F3-B｜三维有限变形 FEM 工程资格</h1>
<p class="note">独立数值资格：<strong>{escape(status)}</strong>。本阶段是三维工程块和梁，不是三维心室，不代表已吻合斑马鱼实验。
各子门及失败以 <a href="verification.json">verification.json</a> 为准，绘图完成不改变数值裁决。</p>
{incomplete_note}
<p>使用 Q2 位移 / Q1 压力混合实体单元，有限变形、等容 Neo-Hookean / Guccione 被动能及体积约束。
NH μ=1；Guccione C=1、bff=8、bxx=2、bfx=4 均为未标定工程参数。κ=100/1000 是近不可压敏感性条件，不是实验测得模量。</p>
<p>主动项为 Wact=T(|Ff0|²−1)/2，拉格朗日主动张力 T 由规定相位给出，不是恒定 Cauchy 应力、秒或实测心率。
自由主动块可在接近零总应力时明显缩短和增厚，因此五状态图着色的是 <strong>主动 Cauchy 纤维分量 T|Ff0|²/J</strong>，不可误读为总应力。
全部网格图采用真实1倍位移。XY/XZ只是三维实体的正交表面视图，不是二维平面应变解。</p>
<figure><img src="figures/model_structure.png" alt="三维工程块及梁的实际网格、约束与变形梁应力"><figcaption>红色标出约束。块的三个零坐标面分别限制法向位移；拉伸时右端规定x位移，其余未约束分量自由。梁左端全夹持，右端施加+y参考面死牵引；没有腔面压力、血流或心脏几何。D为总三维von Mises应力的单元平均，不是主动分量。</figcaption></figure>
<figure><img src="figures/mechanics_results.png" alt="解析拉伸、方向性、主动形变及梁网格和体积模量对照"><figcaption>解析参考来自独立验证器；反力为右端x反力除以参考横截面积。主动伸长取独立重算平均F的列向量长度；梁末端位移是Q2参考面面积加权的末端面y位移均值。曲线连线只用于阅读，不是额外求解状态或生理时间。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="Guccione主动三维块五个实际有限变形状态"><figcaption>从完整九状态中取0/2/4/6/8，固定坐标、固定色标、虚线参考网格。颜色只表示主动Cauchy纤维分量；无显示插值帧。原始九状态及全部Gauss点字段保留。</figcaption></figure>
<table><thead><tr><th>工况</th><th>六面体数</th><th>已保存 / 预登记状态数</th><th>独立检查状态</th></tr></thead><tbody>{rows}</tbody></table>
<p><a href="configuration.json">冻结配置</a> · <a href="verification.json">独立验证与所有门</a> · <a href="rendering.json">图件记录</a> · <a href="raw/guccione_active_k1000.npz">主动块完整原状态</a> · <a href="raw/nh_bending_fine_k1000.npz">细网格梁原状态</a></p></html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    size = sum(path.stat().st_size for path in result.rglob("*") if path.is_file())
    if size > int(config["resources"]["stage_bytes"]):
        raise RuntimeError("Saved finite-strain package exceeds its stage cap after rendering; no files deleted")
    return report
