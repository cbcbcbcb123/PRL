"""Render retained curved-pressure equilibria, never invoking a solver.

The three-dimensional Q2 solid is constrained to plane strain.  Its plotted
sections interpolate only the spatial Q2 basis, never missing load states.
Quantitative radial displacement comes from independent reference-face area
integration in verification.json, not an inconsistent nodal average.
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
import numpy as np

from prl.rendering.cb_plot_unified_style import add_top_information, apply_axes_style
from prl.rendering.fem_measured_contour import (
    _axes, _bounded_ticks, _colorbar, _compact_style, _export, _load,
)
from prl.rendering.fem_finite_strain import _spatial, _square_bounds
from prl.rendering.fem_rotation import _midplane_faces


BLUE = "#225A80"
ORANGE = "#C87837"
RED = "#B3463E"
GREY = "#6C7880"


def _basis(parameter):
    return np.stack((.5*parameter*(parameter-1), 1-parameter**2,
                     .5*parameter*(parameter+1)), axis=-1)


def _q2_polygon(face, positions, projection="xy"):
    """Sample the actual quadratic face boundary, retaining curved geometry."""
    parameter = np.linspace(-1., 1., 13)
    first = np.concatenate((parameter, np.ones(13), parameter[::-1], -np.ones(13)))
    second = np.concatenate((-np.ones(13), parameter, np.ones(13), parameter[::-1]))
    points = np.einsum("pa,pb,abj->pj", _basis(first), _basis(second), positions[face])
    if projection == "xy":
        return points[:, :2]
    if projection == "rz":
        return np.column_stack((np.linalg.norm(points[:, :2], axis=1), points[:, 2]))
    raise ValueError("Unregistered section projection")


def _curved_section(axis, faces, positions, *, values=None, norm=None,
                    outline=BLUE, fill="#D7E7EF", dashed=False, projection="xy"):
    polygons = [_q2_polygon(face, positions, projection) for face in faces]
    options = {"edgecolors": outline, "linewidths": .65,
               "linestyles": "--" if dashed else "-"}
    if values is None:
        collection = PolyCollection(polygons, facecolors=fill, **options)
    else:
        collection = PolyCollection(polygons, array=np.asarray(values), norm=norm,
                                    cmap="YlGnBu", **options)
    axis.add_collection(collection)
    return collection


def _midangle_faces(payload, angle):
    coordinates = payload["coordinates"]
    angles = np.arctan2(coordinates[:, 1], coordinates[:, 0])
    faces, seen = [], set()
    for indices in payload["cells"]:
        for local_index in range(3):
            face = indices.reshape(3, 3, 3)[:, local_index, :]
            identity = tuple(sorted(int(index) for index in face.ravel()))
            if identity not in seen and np.allclose(angles[face], angle, atol=1e-12, rtol=0):
                faces.append(face)
                seen.add(identity)
    if not faces:
        raise ValueError("Saved Q2 mesh has no registered middle-angle section")
    return faces


def _load_retained(result, config):
    expected = np.asarray(config["loads"], dtype=float)
    payloads = {}
    for case in config["cases"]:
        name = str(case["name"])
        path = result / "raw" / f"{name}.npz"
        if not path.is_file():
            continue
        data = _load(path)
        loads = np.asarray(data["loads"], dtype=float)
        if not len(loads):
            continue
        if loads.ndim != 1 or len(loads) > len(expected) or not np.allclose(
                loads, expected[:len(loads)], rtol=0, atol=1e-14):
            raise ValueError(f"{name}: retained states are not a frozen load prefix")
        coordinates, cells = data["coordinates"], data["cells"]
        if coordinates.ndim != 2 or coordinates.shape[1] != 3 or cells.ndim != 2 or cells.shape[1] != 27:
            raise ValueError(f"{name}: expected an actual 3-D Q2 mesh")
        if data["displacements"].shape != (len(loads), len(coordinates), 3):
            raise ValueError(f"{name}: saved displacement shape disagrees with loads")
        for key in ("coordinates", "displacements", "Cauchy", "Green", "J"):
            if not np.all(np.isfinite(data[key])):
                raise ValueError(f"{name}: nonfinite saved {key}; invalid states are not plotted")
        if data["Cauchy"].shape != (len(loads), len(cells), 27, 3, 3):
            raise ValueError(f"{name}: expected saved 3-D Gauss-point total stress")
        if data["J"].shape != (len(loads), len(cells), 27):
            raise ValueError(f"{name}: expected saved volume ratios")
        payloads[name] = data
    return payloads


def _independent_radial(verification, name, loads):
    records = verification.get("cases", {}).get(name, {}).get("states", [])
    result = np.full(len(loads), np.nan)
    for state, load in enumerate(loads):
        matches = [item for item in records if isinstance(item, dict)
                   and isinstance(item.get("load"), (int, float))
                   and np.isclose(item["load"], load, atol=1e-14, rtol=0)]
        if len(matches) == 1:
            value = matches[0].get("inner_radial_displacement")
            if isinstance(value, (int, float)) and np.isfinite(value):
                result[state] = float(value)
    return result


def _reference_at(verification, loads):
    reference = verification.get("analytic_reference", {})
    pressures = np.asarray(reference.get("pressures", []), dtype=float)
    displacements = np.asarray(reference.get("inner_radial_displacement", []), dtype=float)
    values = np.full(len(loads), np.nan)
    if pressures.ndim != 1 or displacements.shape != pressures.shape:
        return values
    for index, load in enumerate(loads):
        matches = np.flatnonzero(np.isclose(pressures, load, atol=1e-14, rtol=0))
        if len(matches) == 1 and np.isfinite(displacements[matches[0]]):
            values[index] = displacements[matches[0]]
    return values


def _cell_von_mises(data):
    stress = data["Cauchy"]
    deviator = stress - np.trace(stress, axis1=-2, axis2=-1)[..., None, None]*np.eye(3)/3
    return np.max(np.sqrt(1.5*np.sum(deviator**2, axis=(-2, -1))), axis=2)


def _boundary_marks(axis, data):
    coordinates = data["coordinates"]
    middle_z = (coordinates[:, 2].min()+coordinates[:, 2].max())/2
    middle = np.isclose(coordinates[:, 2], middle_z, atol=1e-12, rtol=0)
    for component in (0, 1):
        ids = np.flatnonzero(middle & np.isclose(coordinates[:, component], 0, atol=1e-12, rtol=0))
        ids = ids[np.argsort(np.linalg.norm(coordinates[ids, :2], axis=1))]
        axis.plot(coordinates[ids, 0], coordinates[ids, 1], color=RED, lw=2.0)
    # Tangent of the saved isoparametric inner edge determines its normal.
    # Arrows show loading direction, not a force vector at the zero-load state.
    for element, direction, side in data["inner_faces"]:
        if int(direction) != 0 or int(side) != -1:
            raise ValueError("Only registered radial inner faces are supported")
        edge = coordinates[data["cells"][int(element)].reshape(3, 3, 3)[0, :, 1], :2]
        tangent = .5*(edge[2]-edge[0])
        normal = np.array([tangent[1], -tangent[0]])/np.linalg.norm(tangent)
        tail, head = edge[1]-.17*normal, edge[1]+.025*normal
        axis.annotate("", xy=head, xytext=tail,
                      arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.5})


def _linear(axis, style, xlabel, ylabel, loads):
    lower, upper = axis.get_ylim()
    if not np.isfinite(lower+upper) or lower == upper:
        lower, upper = -.05, 1.05
    axis.set_ylim(lower, upper)
    axis.set_xlim(-.025*float(loads[-1]), 1.025*float(loads[-1]))
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    _bounded_ticks(axis.xaxis, *axis.get_xlim(), bins=4)
    _bounded_ticks(axis.yaxis, *axis.get_ylim(), bins=4)
    apply_axes_style(axis, style=style)


def _missing(axis, text="No saved equilibrium"):
    axis.text(.5, .5, text, transform=axis.transAxes, ha="center", va="center", color=RED)


def render_fem_curved_pressure(result: Path) -> dict[str, Any]:
    """Export only retained equilibria; independent qualification is unchanged."""
    result = Path(result).resolve()
    config = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification_path = result / "verification.json"
    verification = (json.loads(verification_path.read_text(encoding="utf-8"))
                    if verification_path.is_file() else {})
    status = str(verification.get("status", "unknown"))
    expected = np.asarray(config["loads"], dtype=float)
    if not np.allclose(expected, [0, .02, .04, .06, .08], rtol=0, atol=1e-14):
        raise ValueError("Unregistered pressure states cannot be silently relabelled")
    payloads = _load_retained(result, config)
    if not payloads:
        return {"schema_version": "prl.fem_curved_pressure_rendering.v1", "status": "blocked",
                "qualification_status": status, "reason": "No retained equilibrium; no model/results fabricated"}
    case_names = [str(case["name"]) for case in config["cases"]]
    counts = {name: len(payloads[name]["loads"]) if name in payloads else 0 for name in case_names}
    complete = all(value == len(expected) for value in counts.values())
    if status == "passed" and not complete:
        raise ValueError("Passing verification conflicts with missing retained states")
    selected_name = max(payloads, key=lambda name: (len(payloads[name]["loads"]), name == "fine"))
    selected = payloads[selected_name]
    selected_positions = selected["coordinates"][None]+selected["displacements"]
    faces, _, middle_z, element_ids = _midplane_faces(selected)
    all_positions = np.concatenate([(data["coordinates"][None]+data["displacements"])[..., :2].reshape(-1, 2)
                                    for data in payloads.values()])
    bounds = _square_bounds(all_positions, padding=.13)
    radial = {name: _independent_radial(verification, name, data["loads"]) for name, data in payloads.items()}
    scalar = {name: _cell_von_mises(data) for name, data in payloads.items()}
    maximum_stress = max(float(value.max()) for value in scalar.values())
    stress_upper = maximum_stress if maximum_stress > 0 else 1.
    stress_norm = Normalize(0., stress_upper)
    reference = _reference_at(verification, expected)
    warnings = []
    for name in case_names:
        if counts[name] < len(expected):
            warnings.append(f"{name}: {counts[name]}/{len(expected)} saved states; missing states not_run")
        if name in radial and not np.all(np.isfinite(radial[name])):
            warnings.append(f"{name}: independent area-weighted displacement missing; no nodal substitute")
    if not np.all(np.isfinite(reference)):
        warnings.append("Independent incompressible reference missing or incomplete")
    figure_folder = result / "figures"
    figure_folder.mkdir(exist_ok=True)
    exports = []

    style, overrides = _compact_style(4.)
    figure = plt.figure(figsize=(14.4, 12.4))
    axes = [_axes(figure, 1.45, 7.15, 4.), _axes(figure, 8., 7.15, 4.),
            _axes(figure, 1.45, 1.8, 4.), _axes(figure, 8., 1.8, 4.)]
    for axis, name, letter in zip(axes[:2], ("coarse", "fine"), ("A", "B")):
        if name in payloads:
            data = payloads[name]
            case_faces, _, _, _ = _midplane_faces(data)
            _curved_section(axis, case_faces, data["coordinates"])
            _boundary_marks(axis, data)
            label = f"{letter}  {name}: {len(data['cells'])} curved Q2 hex\nReference XY middle section"
        else:
            _missing(axis, f"{name}: no saved mesh/state")
            label = f"{letter}  {name}: NOT_RUN / missing"
        _spatial(axis, bounds, style)
        add_top_information(axis, label, style=style)
        axis.text(.06, .21, "uy=0 at y=0\nux=0 at x=0\nOuter wall: free", transform=axis.transAxes)
    rz_faces = _midangle_faces(selected, float(config["geometry"]["angle"])/2)
    _curved_section(axes[2], rz_faces, selected_positions[-1], projection="rz")
    _curved_section(axes[2], rz_faces, selected["coordinates"], projection="rz", fill="none", outline=GREY, dashed=True)
    rz_points = np.column_stack((np.linalg.norm(selected_positions[..., :2], axis=-1).ravel(),
                                 selected_positions[..., 2].ravel()))
    rz_bounds = _square_bounds(rz_points, padding=.13)
    _spatial(axes[2], rz_bounds, style)
    axes[2].set_xlabel("r (model length)")
    axes[2].set_ylabel("z (model length)")
    add_top_information(axes[2], "C  Actual r-z middle-angle section\nAll nodes: uz=0 (plane strain)", style=style)
    axes[2].text(.03, .04, "Dashed: reference; solid: last state", transform=axes[2].transAxes)
    collection = _curved_section(axes[3], faces, selected_positions[-1],
                                  values=scalar[selected_name][-1, element_ids], norm=stress_norm, outline=GREY)
    _curved_section(axes[3], faces, selected["coordinates"], fill="none", outline=GREY, dashed=True)
    _spatial(axes[3], bounds, style)
    add_top_information(axes[3], f"D  {selected_name}: p/μ={selected['loads'][-1]:g}\nLast saved equilibrium, 1× displacement", style=style)
    _colorbar(figure, collection, (12.35, 1.8, .16, 4.), "Total von Mises / μ", style)
    figure.text(.5, .073, "3-D Q2/Q1 solid constrained to plane strain; red arrows: pressure direction only; red cuts: symmetry conditions", ha="center")
    figure.text(.5, .037, f"Engineering μ=1, κ=1000; no active tension or end-cap pressure; qualification {status.upper()}; NOT a ventricle", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "model_structure", style, overrides))

    style, overrides = _compact_style(4.)
    figure = plt.figure(figsize=(14.4, 12.4))
    axes = [_axes(figure, 1.45, 7.15, 4.), _axes(figure, 8., 7.15, 4.),
            _axes(figure, 1.45, 1.8, 4.), _axes(figure, 8., 1.8, 4.)]
    if np.any(np.isfinite(reference)):
        axes[0].plot(expected, reference, color=GREY, ls="--", lw=1.5, label="Incompressible limit")
    for name, color in (("coarse", ORANGE), ("fine", BLUE)):
        if name not in payloads:
            continue
        data, values = payloads[name], radial[name]
        loads = data["loads"]
        if np.any(np.isfinite(values)):
            axes[0].plot(loads, values, color=color, marker="o", lw=1.5, label=name)
        ref_values = _reference_at(verification, loads)
        usable = (loads > 0) & np.isfinite(values) & np.isfinite(ref_values) & (np.abs(ref_values) > 0)
        if np.any(usable):
            axes[1].plot(loads[usable], 100*np.abs(values[usable]-ref_values[usable])/np.abs(ref_values[usable]),
                         color=color, marker="o", lw=1.5, label=name)
        axes[2].plot(loads, 100*np.max(np.abs(data["J"]-1), axis=(1, 2)),
                     color=color, marker="o", lw=1.5, label=name)
    differences, matched_loads = [], []
    if "coarse" in radial and "fine" in radial:
        for state, load in enumerate(payloads["fine"]["loads"]):
            matches = np.flatnonzero(np.isclose(payloads["coarse"]["loads"], load, rtol=0, atol=1e-14))
            fine_value = radial["fine"][state]
            if load > 0 and len(matches) == 1 and np.isfinite(fine_value) and abs(fine_value) > 0:
                coarse_value = radial["coarse"][matches[0]]
                if np.isfinite(coarse_value):
                    matched_loads.append(float(load))
                    differences.append(100*abs(coarse_value-fine_value)/abs(fine_value))
    if differences:
        axes[3].plot(matched_loads, differences, color=BLUE, marker="o", lw=1.5, label="Coarse-fine / |fine|")
    axes[3].axhline(5., color=RED, ls="--", lw=1.5, label="5% end-load gate")
    labels = (("A  Independent inner-wall displacement", "Area-weighted radial displacement"),
              ("B  Difference from incompressible limit", "Absolute relative difference (%)"),
              ("C  Volume ratio at all saved Gauss points", "Maximum |J−1| (%)"),
              ("D  Mesh-pair displacement sensitivity", "Absolute relative difference (%)"))
    for axis, (title, ylabel) in zip(axes, labels):
        has_values = bool(axis.get_lines())
        if not has_values:
            _missing(axis, "Independent metric unavailable")
        axis.set_ylim(bottom=min(0., axis.get_ylim()[0]))
        _linear(axis, style, "Cavity pressure / μ", ylabel, expected)
        add_top_information(axis, title, style=style)
        if has_values:
            axis.legend(loc="upper left", frameon=False)
    if not differences:
        _missing(axes[3], "Matched metrics unavailable")
    figure.text(.5, .073, "Radial displacement: reference-face area-weighted projection u·er; analytic curve: exact-incompressibility limit", ha="center")
    figure.text(.5, .037, "Finite κ=1000 is not the analytic material; discrepancies include compressibility, curved mapping and FE error", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "mechanics_results", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(18.5, 6.1))
    axes = []
    collection = None
    for state, load in enumerate(expected):
        axis = _axes(figure, 1.+3.2*state, 1.65, 2.3)
        axes.append(axis)
        if state < len(selected["loads"]):
            collection = _curved_section(axis, faces, selected_positions[state],
                                          values=scalar[selected_name][state, element_ids], norm=stress_norm, outline=GREY)
            value = radial[selected_name][state]
            annotation = f"area-weighted ur={value:.4f}" if np.isfinite(value) else "independent ur unavailable"
            label = f"p/μ={load:g} · saved equilibrium\n{annotation}"
        else:
            _missing(axis, "NOT_RUN\nNo saved equilibrium")
            label = f"p/μ={load:g} · missing"
        _spatial(axis, bounds, style)
        add_top_information(axis, label, style=style)
    if collection is not None:
        _colorbar(figure, collection, (16.55, 1.65, .15, 2.3), "Total von Mises / μ", style)
    figure.text(.48, .105, f"{selected_name}: {len(selected['loads'])}/5 real saved states; XY middle section of constrained 3-D solid; 1× displacement", ha="center")
    figure.text(.48, .057, "Cellwise maximum 3-D von Mises stress over 27 Gauss points; fixed color/space scales; pressure steps are NOT physiological time", ha="center")
    exports.extend(_export(figure, axes, figure_folder / "five_states", style, overrides))

    report = {
        "schema_version": "prl.fem_curved_pressure_rendering.v1", "status": "passed",
        "qualification_status": status, "all_registered_states_available": complete,
        "saved_state_counts": counts, "requested_states_per_case": len(expected),
        "display_case": selected_name, "actual_display_states": len(selected["loads"]),
        "warnings": warnings, "deformation_scale": 1., "fixed_xy_bounds": list(bounds),
        "section": "saved Q2 XY z-middle section; Q2 spatial edges, no temporal interpolation",
        "reference_section_z": middle_z, "middle_section_owning_elements": element_ids.tolist(),
        "stress_field": "cellwise maximum full 3-D total Cauchy von Mises over 27 Gauss points, including sigma_zz",
        "stress_color_range": [0., stress_upper], "all_zero_stress_display_fallback": maximum_stress == 0,
        "displacement_metric": "verification.json: reference inner-face area-weighted integral of u dot er_ref",
        "analytic_reference_kind": verification.get("analytic_reference", {}).get("kind", "unknown"),
        "mesh_relative_differences_percent": {"loads": matched_loads, "values": differences},
        "biological_validation": "not_run", "physiological_time": "not_run", "heart_geometry": "not_run",
        "exports": [path.relative_to(result).as_posix() for path in exports],
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    count_text = "；".join(f"{escape(name)}：{counts[name]}/5" for name in case_names)
    warning_text = "".join(f"<li>{escape(item)}</li>" for item in warnings)
    evidence_links = " · ".join(f'<a href="raw/{escape(name, quote=True)}.npz">{escape(name)} 原始状态</a>' for name in payloads)
    verification_link = '<a href="verification.json">独立验证</a>' if verification_path.is_file() else '独立验证缺失（unknown）'
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F4 曲面压力非线性 FEM 资格</title><style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;color:#263d4b}}img{{max-width:100%}}.note{{background:#f2f5f7;border-left:4px solid #a9453b;padding:16px}}a{{color:#1b608b}}</style>
<h1>F4｜曲面压力与非线性有限元资格</h1>
<p class="note">独立资格状态：<strong>{escape(status)}</strong>；保存状态：{count_text}。本页渲染通过不等于数值资格通过，更不是实验验证。
这是三维 Q2 位移 / Q1 压力的四分之一圆柱壁段，所有节点 uz=0 的<strong>平面应变约束</strong>资格算例，不是自由三维心室。既有失败及刚转补充包均不改写。</p>
<p>参考内半径 A=1、外半径 B=1.25、高度 0.5；θ=0 面 uy=0，θ=π/2 面 ux=0，全部 uz=0；外壁无牵引，无端盖压力。
内壁正腔压沿当前固体内壁外法线的反方向加载，随当前曲面法线与面积更新。红箭头仅表示压力方向，不代表零载荷状态存在非零力。
材料为未标定工程 Neo-Hookean μ=1、κ=1000，无主动张力。五级 p/μ=0、0.02、0.04、0.06、0.08 是准静态压力延拓，不是生理时间或心动周期。</p>
<ul>{warning_text}</ul>
<figure><img src="figures/model_structure.png" alt="实际三维曲面网格中截面、压力方向和约束"><figcaption>A/B：保存的粗细 Q2 曲面网格 XY 中截面，红色径向边是对称约束；C：真实 r-z 中角度截面，全部 z 位移固定；D：最后保存状态 1 倍形变及总 von Mises 场。灰虚线为参考网格。曲边按同一 Q2 空间插值显示，不把圆弧假装成精确几何。</figcaption></figure>
<figure><img src="figures/mechanics_results.png" alt="内壁面积加权径向位移、不可压解析极限、体积变化及网格对比"><figcaption>位移来自独立验证对参考内壁面积积分的 ∫(u·er_ref)dA0/∫dA0，不是节点算术平均或位移后半径差。解析线是无限长平面应变 Neo-Hookean 圆柱的精确不可压极限，并非相同有限 κ 的精确解。粗细网格差仅为本载荷范围的资格检查，不声称一般网格收敛。网格差 5% 门只针对合同规定的末级载荷。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="五个压力级的真实保存状态，缺失级明确标记"><figcaption>优先展示具有最多真实状态的网格（同数量优先 fine），当前为 {escape(selected_name)}。
所有状态 1 倍位移、相同空间范围与色标。颜色为每个三维单元 27 个保存积分点中最大总 Cauchy von Mises 应力，包含 σzz，分片常数映射到截面；不是主动张力，也不是混合压力自由度。缺失状态不插值、不制造。</figcaption></figure>
<p><a href="configuration.json">配置</a> · {verification_link} · <a href="rendering.json">渲染定义</a> · {evidence_links}</p></html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    cap = int(config.get("resources", {}).get("stage_bytes", 32*1024**2))
    size = sum(path.stat().st_size for path in result.rglob("*") if path.is_file())
    if size > cap:
        raise RuntimeError("Curved-pressure evidence exceeds its stage budget; no files were deleted")
    return report
