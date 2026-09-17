"""Saved-state views of the 3-D rotation repair, with no solver calls.

Boundary-only and predicted vectors are shown solely as initial guesses.  The
five equilibrium frames come from rotation.npz, and the zero-degree frame is
explicitly identified as retained parent evidence, not a repeated solve.
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
from matplotlib.ticker import FixedLocator, NullFormatter
import numpy as np

from prl.rendering.cb_plot_unified_style import add_top_information, apply_axes_style
from prl.rendering.fem_measured_contour import (
    _axes, _bounded_ticks, _colorbar, _compact_style, _export, _load,
)
from prl.rendering.fem_finite_strain import _spatial, _square_bounds


BLUE = "#225A80"
RED = "#B3463E"
ORANGE = "#C87837"
GREY = "#6C7880"
GREEN_LIMIT = 1e-10
STRESS_LIMIT = 2e-7
NEWTON_LIMIT = 1e-9


def _midplane_faces(payload):
    """Read the actual Q2 XY middle section, keeping internal nodes visible."""
    coordinates = payload["coordinates"]
    middle = 0.5 * (coordinates[:, 2].min() + coordinates[:, 2].max())
    faces, element_ids, seen = [], [], set()
    for element_id, indices in enumerate(payload["cells"]):
        for local_index in range(3):
            face = indices.reshape(3, 3, 3)[:, :, local_index]
            identity = tuple(sorted(int(index) for index in face.ravel()))
            if identity in seen or not np.allclose(coordinates[face, 2], middle, rtol=0, atol=1e-12):
                continue
            faces.append(face)
            element_ids.append(element_id)
            seen.add(identity)
    if not faces:
        raise ValueError("Saved mesh has no exact XY middle plane; no substitute geometry is allowed")
    return faces, np.flatnonzero(np.isclose(coordinates[:, 2], middle, rtol=0, atol=1e-12)), float(middle), np.asarray(element_ids)


def _section(axis, faces, positions, *, fill="#D7E7EF", outline=BLUE, dashed=False):
    # All node positions are saved values.  For this pure-rotation qualification
    # each Q2 edge is affine at equilibrium; its midpoint is retained explicitly.
    edge = ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1))
    polygons = [positions[np.asarray([face[first, second] for first, second in edge]), :2]
                for face in faces]
    collection = PolyCollection(polygons, facecolors=fill, edgecolors=outline,
                                linewidths=.8, linestyles="--" if dashed else "-")
    axis.add_collection(collection)
    return collection


def _node_marks(axis, positions, section_nodes, fixed_nodes):
    prescribed = section_nodes[np.isin(section_nodes, fixed_nodes)]
    free = section_nodes[~np.isin(section_nodes, fixed_nodes)]
    axis.scatter(positions[prescribed, 0], positions[prescribed, 1], color=RED,
                 marker="s", s=20, zorder=5, label="Prescribed boundary")
    axis.scatter(positions[free, 0], positions[free, 1], color=BLUE,
                 marker="o", s=25, zorder=5, label="Free interior")


def _log_axis(axis, style, xlabel, ylabel):
    axis.set_yscale("log")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    _bounded_ticks(axis.xaxis, *axis.get_xlim(), bins=4)
    apply_axes_style(axis, style=style)
    # LogLocator can return ticks outside the retained limits, and its automatic
    # subs selection may omit minor ticks across many decades.  Freeze only
    # in-range decades/subdecades after style application, without changing the
    # data limits or the numerical values to make the display validator pass.
    lower, upper = axis.get_ylim()
    if not 0 < lower < upper or not np.all(np.isfinite([lower, upper])):
        raise ValueError("Log display requires finite increasing positive limits")
    exponents = np.arange(int(np.floor(np.log10(lower))), int(np.ceil(np.log10(upper))) + 1)
    decades = np.power(10.0, exponents)
    major_ticks = decades[(decades >= lower) & (decades <= upper)]
    candidates = (decades[:, None] * np.arange(2.0, 10.0)[None, :]).ravel()
    minor_ticks = candidates[(candidates >= lower) & (candidates <= upper)]
    if not len(minor_ticks):
        raise ValueError("Registered logarithmic display has no in-range subdecade ticks")
    axis.yaxis.set_major_locator(FixedLocator(major_ticks))
    axis.yaxis.set_minor_locator(FixedLocator(minor_ticks))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.tick_params(axis="y", which="minor", left=True, right=True, direction="out",
                     length=style.minor_tick_length_pt, width=style.minor_tick_width_pt)


def render_fem_rotation(result: Path) -> dict[str, Any]:
    """Export real structure, equilibrium and Newton-recovery evidence."""
    result = Path(result).resolve()
    config = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification = json.loads((result / "verification.json").read_text(encoding="utf-8"))
    data = _load(result / "raw/rotation.npz")
    initials = _load(result / "raw/rotation_initials.npz")
    recovery = _load(result / "raw/perturbed_recovery.npz")
    history = json.loads((result / "raw/perturbed_recovery_newton.json").read_text(encoding="utf-8"))
    status = str(verification.get("status", "unknown"))
    case = config["case"]
    angles = np.asarray(case["rotation_degrees"], dtype=float)
    if not np.array_equal(angles, [0, 15, 30, 45, 60]):
        raise ValueError("The renderer accepts only the registered five rotation angles")
    if data["phases"].shape != (5,) or not np.allclose(data["phases"], case["phases"], atol=1e-14, rtol=0):
        raise ValueError("Five saved equilibria are required; missing rotation states are never fabricated")
    if "angles" in data and not np.array_equal(data["angles"], angles):
        raise ValueError("Saved angles differ from the frozen configuration")
    if not np.array_equal(initials["angles"], angles[1:]):
        raise ValueError("Initial guesses must match the four new registered angles")
    for key in ("coordinates", "displacements", "F", "Green", "Cauchy", "J"):
        if not np.all(np.isfinite(data[key])):
            raise ValueError(f"Nonfinite saved rotation field: {key}")
    if data["coordinates"].shape[1] != 3 or data["cells"].shape[1] != 27:
        raise ValueError("Only actual 3-D Q2/Q1 meshes may be shown")
    coordinates = data["coordinates"]
    positions = coordinates[None] + data["displacements"]
    faces, section_nodes, middle_z, face_element_ids = _midplane_faces(data)
    fixed_dofs = np.asarray(data["fixed_dofs"])
    if fixed_dofs.ndim == 2:
        if not np.all(fixed_dofs == fixed_dofs[0]):
            raise ValueError("The saved rotation constraint set must remain fixed")
        fixed_dofs = fixed_dofs[0]
    fixed_nodes = np.unique(fixed_dofs // 3)
    free_nodes = np.setdiff1d(np.arange(len(coordinates)), fixed_nodes)
    scalar_green = np.max(np.abs(data["Green"]), axis=(1, 2, 3, 4))
    scalar_stress = np.max(np.abs(data["Cauchy"]), axis=(1, 2, 3, 4))
    cell_stress = np.max(np.abs(data["Cauchy"]), axis=(2, 3, 4))
    scalar_volume = np.max(np.abs(data["J"] - 1), axis=(1, 2))
    boundary_guess = coordinates + initials["boundary_only_vectors"][0, :3*len(coordinates)].reshape(-1, 3)
    predicted_guess = coordinates + initials["predicted_vectors"][0, :3*len(coordinates)].reshape(-1, 3)
    bounds = _square_bounds(np.concatenate((positions[:, section_nodes, :2].reshape(-1, 2),
                                            boundary_guess[section_nodes, :2], predicted_guess[section_nodes, :2])))
    iterations = np.asarray([item["iteration"] for item in history], dtype=float)
    residuals = np.asarray([item["normalized_free_residual"] for item in history], dtype=float)
    if not len(history) or not np.all(np.isfinite(residuals)) or np.any(residuals < 0):
        raise ValueError("A finite actual perturbation-recovery Newton history is required")
    figure_folder = result / "figures"
    figure_folder.mkdir(exist_ok=True)
    exports = []

    style, overrides = _compact_style(4.0)
    figure = plt.figure(figsize=(14.4, 12.4))
    axes = [_axes(figure, 1.45, 7.15, 4.0), _axes(figure, 8.0, 7.15, 4.0),
            _axes(figure, 1.45, 1.8, 4.0), _axes(figure, 8.0, 1.8, 4.0)]
    displays = (
        (positions[0], "A  0° equilibrium: retained parent", "#D7E7EF"),
        (positions[-1], "B  60° actual equilibrium", "#D7E7EF"),
        (boundary_guess, "C  15° boundary-only INITIAL guess", "#F6DED2"),
        (predicted_guess, "D  15° lifted INITIAL guess", "#D9EADD"),
    )
    for axis, (shown_positions, label, fill) in zip(axes, displays):
        _section(axis, faces, shown_positions, fill=fill)
        _node_marks(axis, shown_positions, section_nodes, fixed_nodes)
        _spatial(axis, bounds, style)
        add_top_information(axis, label, style=style)
    axes[0].legend(loc="upper left", frameon=False)
    axes[1].text(.04, .05, "Interior DOFs remain free", transform=axes[1].transAxes)
    axes[2].text(.04, .05, "Not an equilibrium or checkpoint", transform=axes[2].transAxes)
    axes[3].text(.04, .05, "Prediction is not a constraint", transform=axes[3].transAxes)
    figure.text(.5, .075, f"Actual 3-D Q2/Q1 block: XY midslice z0={middle_z:g}; {len(fixed_nodes)} boundary / {len(free_nodes)} interior nodes overall", ha="center")
    figure.text(.5, .038, "1× displacements; C/D are saved initial guesses, NOT additional solved states or physiological time", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "model_structure", style, overrides))

    style, overrides = _compact_style(4.2)
    figure = plt.figure(figsize=(14.4, 7.1))
    axes = [_axes(figure, 1.45, 1.7, 4.2), _axes(figure, 8.0, 1.7, 4.2)]
    error_floor = 1e-12
    for values, limit, color, label in ((scalar_green, GREEN_LIMIT, BLUE, "Green strain / 1e-10"),
                                        (scalar_stress, STRESS_LIMIT, ORANGE, "Total stress / 2e-7")):
        axes[0].plot(angles, np.maximum(values/limit, error_floor), color=color, marker="o", lw=1.5, label=label)
    axes[0].axhline(1, color=RED, ls="--", lw=1.5, label="Frozen acceptance limit")
    axes[0].set_xlim(-2, 62)
    axes[0].set_ylim(error_floor*.4, 20)
    _log_axis(axes[0], style, "Prescribed rotation angle (degrees)", "Error / frozen limit (log scale)")
    axes[0].xaxis.set_major_locator(FixedLocator(angles))
    axes[0].legend(loc="upper left", frameon=False)
    add_top_information(axes[0], "A  Pure rotation: no physical strain/stress", style=style)
    residual_floor = 1e-16
    axes[1].plot(iterations, np.maximum(residuals, residual_floor), color=BLUE, marker="o", lw=1.5, label="Saved Newton residual")
    axes[1].axhline(NEWTON_LIMIT, color=RED, ls="--", lw=1.5, label="Frozen solve tolerance")
    axes[1].set_xlim(float(iterations.min())-.2, float(iterations.max())+.2)
    axes[1].set_ylim(max(min(float(np.min(residuals[residuals > 0]))*.2 if np.any(residuals > 0) else residual_floor, NEWTON_LIMIT*.2), residual_floor*.2),
                     max(float(residuals.max())*5, NEWTON_LIMIT*10))
    _log_axis(axes[1], style, "Accepted Newton iteration", "Normalized free residual")
    axes[1].xaxis.set_major_locator(FixedLocator(iterations))
    axes[1].legend(loc="upper right", frameon=False)
    add_top_information(axes[1], "B  Perturbed interior: actual recovery", style=style)
    figure.text(.5, .11, f"Rotation-repair qualification {status.upper()}; max |J−1| = {np.max(scalar_volume):.2e}; engineering block, NOT a heart", ha="center")
    figure.text(.5, .057, "Log display floors only: normalized errors 1e-12, residuals 1e-16; unchanged raw values and gates retained", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "rotation_results", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(18.5, 6.1))
    axes = []
    stress_norm = Normalize(0, STRESS_LIMIT)
    for state, angle in enumerate(angles):
        axis = _axes(figure, 1.0 + 3.2*state, 1.65, 2.3)
        axes.append(axis)
        collection = _section(axis, faces, positions[state], outline=GREY)
        # Pure rotation is expected to be stress-free.  A fixed physical-zero to
        # acceptance-limit color scale prevents amplifying roundoff into a field.
        collection.set_cmap("YlGnBu")
        collection.set_norm(stress_norm)
        collection.set_array(cell_stress[state, face_element_ids])
        _spatial(axis, bounds, style)
        origin = "parent retained" if state == 0 else "actual equilibrium"
        add_top_information(axis, f"{angle:g}° · {origin}\nmax |E| = {scalar_green[state]:.1e}", style=style)
    _colorbar(figure, collection, (16.55, 1.65, .15, 2.3), "Max total stress (relative)", style)
    figure.text(.48, .105, "Five real equilibria; 0° retained from F3-B, four new solved angles; XY midslice of 3-D solid; 1× displacement", ha="center")
    figure.text(.48, .057, "Color: cellwise max |total Cauchy| from saved Gauss values; fixed 0-to-acceptance-limit scale, no roundoff amplification", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "five_states", style, overrides))

    parent = config.get("parent", config.get("parent_result", {}))
    parent_href = escape(str(parent.get("path", "../f3b_finite_strain_v01_20260917")).rstrip("/") + "/index.html", quote=True)
    report = {
        "schema_version": "prl.fem_rotation_rendering.v1", "status": "passed", "qualification_status": status,
        "combined_qualification_status": verification.get("combined_qualification", {}).get("status", "unknown"),
        "parent_original_status": verification.get("parent_evidence", {}).get("original_stage_status", "unknown"),
        "angles": angles.tolist(), "actual_equilibrium_states": 5, "new_rotation_solves": 4,
        "equilibrium_origins": ["parent_retained", "new_solved", "new_solved", "new_solved", "new_solved"],
        "displayed_initial_guesses": {"angle": 15, "sources": ["boundary_only_vectors[0]", "predicted_vectors[0]"], "equilibria": False},
        "projection": "XY exact middle section of a 3-D Q2 solid", "reference_section_z": middle_z,
        "boundary_nodes_total": len(fixed_nodes), "interior_nodes_total": len(free_nodes),
        "section_node_count": len(section_nodes), "deformation_scale": 1.0, "fixed_bounds": list(bounds),
        "max_abs_Green": scalar_green.tolist(), "max_abs_total_Cauchy": scalar_stress.tolist(),
        "max_abs_J_minus_1": scalar_volume.tolist(),
        "error_normalization_limits": {"Green": GREEN_LIMIT, "total_Cauchy": STRESS_LIMIT},
        "stress_color_interpretation": "per-cell max(abs(total Cauchy)) over stored Gauss points, mapped to the exact middle-section face; lower adjacent cell owns each shared face",
        "middle_section_owning_elements": face_element_ids.tolist(),
        "stress_color_range": [0.0, STRESS_LIMIT],
        "perturbed_recovery_history": {"iteration": iterations.tolist(), "normalized_free_residual": residuals.tolist(),
                                        "final_recovery_max_abs_Green": float(np.max(np.abs(recovery["Green"])))},
        "biological_validation": "not_run", "physiological_time": "not_run", "heart_geometry": "not_run",
        "exports": [path.relative_to(result).as_posix() for path in exports],
        "gif": "not_run; only actual saved equilibria shown",
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = "".join(f"<tr><td>{angle:g}°</td><td>{'旧包保留' if state == 0 else '本次实际求解'}</td><td>{scalar_green[state]:.3e}</td><td>{scalar_stress[state]:.3e}</td><td>{scalar_volume[state]:.3e}</td></tr>"
                   for state, angle in enumerate(angles))
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F3-C 三维刚转预测修复资格</title><style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;color:#263d4b}}img{{max-width:100%}}.note{{background:#f2f5f7;border-left:4px solid #a9453b;padding:16px}}table{{border-collapse:collapse}}th,td{{padding:7px 18px;border-bottom:1px solid #d8dfe3}}a{{color:#1b608b}}</style>
<h1>F3-C｜可行内部预测与三维刚转资格补充</h1>
<p class="note">本次独立资格：<strong>{escape(status)}</strong>。这是三维工程块的刚体转动，不是心脏收缩，也不是三维真实心室。原F3-B失败记录保持failed；本页只报告新批准的补充资格，不改写<a href="{parent_href}">原始证据</a>。</p>
<p>同一2×1×1块、Q2位移/Q1压力、Neo-Hookean μ=1、κ=1000、无主动张力。全外边界规定绕z轴转动，{len(free_nodes)}个内部节点依然自由；预测只提供Newton起点，不把内部改为约束。
五状态中0°来自旧包保留，15°/30°/45°/60°为新求解状态。角度不是生理时间，没有真实材料标定、心率或心室压力。</p>
<figure><img src="figures/model_structure.png" alt="三维块中截面的边界和内部自由节点及初猜对照"><figcaption>真实三维网格的z0={middle_z:g}中截面；红方点为规定边界，蓝圆点为自由内部节点。A/B是实际平衡态；C/D仅展示保存的初始猜测，不能当作平衡态或物理过程。位移均为1倍，没有显示放大。</figcaption></figure>
<figure><img src="figures/rotation_results.png" alt="刚转应变应力及真实扰动Newton恢复残差"><figcaption>纯刚体转动应保持零材料应变和应力。左图用冻结门限归一显示数值误差，右图读取扰动内部初猜后的真实Newton记录，不能用解析刚转初猜直接满足平衡来替代该恢复检查。日志显示地板仅用于画图，原值和门限不变。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="零至六十度的五个真实三维刚转状态"><figcaption>固定空间坐标、真实1倍位移。颜色取相邻三维单元所有积分点的最大绝对总Cauchy应力，分片常数映射到中截面，共享面由较低z侧单元提供字段；固定0到2e−7色标避免把舍入误差放大成貌似明显的机械场。</figcaption></figure>
<table><thead><tr><th>角度</th><th>来源</th><th>max|Green|</th><th>max|总Cauchy|</th><th>max|J−1|</th></tr></thead><tbody>{rows}</tbody></table>
<p><a href="configuration.json">冻结配置</a> · <a href="verification.json">独立验证</a> · <a href="rendering.json">渲染定义</a> · <a href="raw/rotation.npz">五平衡状态</a> · <a href="raw/rotation_initials.npz">非平衡初猜</a> · <a href="raw/perturbed_recovery.npz">扰动恢复</a> · <a href="raw/perturbed_recovery_newton.json">Newton记录</a></p></html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    cap = int(config.get("resources", {}).get("stage_bytes", 32*1024**2))
    size = sum(path.stat().st_size for path in result.rglob("*") if path.is_file())
    if size > cap:
        raise RuntimeError("Rotation evidence exceeded its stage output budget; no files were deleted")
    return report
