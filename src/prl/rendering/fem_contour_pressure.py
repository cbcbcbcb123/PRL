"""Saved-state figures for an image-outline, passive plane-strain FEM wall.

No computational module is imported.  The renderer reads the source image,
the frozen spatial Q2 curve and actual saved equilibria.  Independent metrics
are read verbatim from verification.json; absent states are never interpolated.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import FixedLocator, NullFormatter
import numpy as np

from prl.rendering.cb_plot_unified_style import add_top_information
from prl.rendering.fem_measured_contour import _axes, _colorbar, _compact_style, _export, _load
from prl.rendering.fem_finite_strain import _spatial, _square_bounds
from prl.rendering.fem_rotation import _midplane_faces
from prl.rendering.fem_curved_pressure import (
    _basis, _cell_von_mises, _curved_section, _linear, _load_retained, _missing,
)


BLUE = "#225A80"
ORANGE = "#C87837"
GREY = "#6C7880"
RED = "#B3463E"
LAYER_COLORS = np.array(["#72ABBA", "#D9BE73", "#81A78B"])
CASE_NAMES = ("radial_coarse", "radial_fine")
RESIDUAL_LIMIT = 2e-6
RESIDUAL_LINTHRESH = 1e-14


def _q2_closed_curve(nodes, samples_per_segment=17):
    """Spatial Q2 interpolation of one retained closed boundary, not a fit."""
    nodes = np.asarray(nodes, dtype=float)
    if nodes.ndim != 2 or nodes.shape[1] != 2 or len(nodes) < 6 or len(nodes) % 2:
        raise ValueError("Closed Q2 curve needs an even number of ordered 2-D nodes")
    if not np.all(np.isfinite(nodes)):
        raise ValueError("Closed Q2 curve contains nonfinite coordinates")
    parameter = np.linspace(-1., 1., samples_per_segment, endpoint=False)
    segments = np.array([nodes[(2*index+np.arange(3)) % len(nodes)] for index in range(len(nodes)//2)])
    points = np.einsum("qa,eai->eqi", _basis(parameter), segments).reshape(-1, 2)
    return np.vstack((points, points[0]))


def _image_coordinates(solver_points, payload):
    rotation = np.asarray(payload["source_to_solver_rotation"], dtype=float)
    center = np.asarray(payload["image_center_um"], dtype=float)
    scale = float(payload["length_scale_um"])
    if (rotation.shape != (2, 2) or center.shape != (2,) or not np.all(np.isfinite(rotation))
            or not np.all(np.isfinite(center)) or not np.isfinite(scale) or scale <= 0
            or not np.allclose(rotation @ rotation.T, np.eye(2), atol=1e-12, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-12, rtol=0)):
        raise ValueError("Saved image/solver transform is not a proper rigid rotation and positive scale")
    return np.asarray(solver_points) @ rotation * scale + center


def _independent_metric(verification, name, loads, key):
    states = verification.get("cases", {}).get(name, {}).get("states", [])
    values = np.full(len(loads), np.nan)
    for state, load in enumerate(loads):
        matches = [item for item in states if isinstance(item, dict)
                   and isinstance(item.get("load"), (int, float))
                   and np.isclose(item["load"], load, atol=1e-14, rtol=0)]
        if len(matches) == 1:
            value = matches[0].get(key)
            if isinstance(value, (int, float)) and np.isfinite(value):
                values[state] = float(value)
    return values


def _select_states(payloads, expected):
    """The registered five-state panel always belongs to fine, even if absent."""
    fine = payloads.get("radial_fine")
    count = len(fine["loads"]) if fine is not None else 0
    return [state if state < count else None for state in range(len(expected))]


def _residual_tick_plan(values, *, limit=RESIDUAL_LIMIT, linthresh=RESIDUAL_LINTHRESH):
    """Return finite in-range symlog ticks without altering residual values."""
    values = np.asarray(values, dtype=float).ravel()
    finite = values[np.isfinite(values)]
    if np.any(finite < 0) or not np.isfinite(limit) or limit <= 0 or not np.isfinite(linthresh) or linthresh <= 0:
        raise ValueError("Residual display requires nonnegative data and positive finite limits")
    largest = max(float(np.max(finite)) if len(finite) else 0., float(limit))
    upper = max(2.5*largest, 100.*linthresh)
    lower_exponent = int(np.floor(np.log10(linthresh)))
    upper_exponent = int(np.floor(np.log10(upper)))
    decades = np.power(10., np.arange(lower_exponent, upper_exponent+1))
    decades = decades[(decades > 0) & (decades <= upper)]
    stride = max(1, int(np.ceil(len(decades)/5)))
    major_positive = decades[::stride]
    if len(decades) and (not len(major_positive) or major_positive[-1] != decades[-1]):
        major_positive = np.append(major_positive, decades[-1])
    major = np.concatenate(([0.], major_positive))
    subdivisions = (decades[:, None]*np.arange(2., 10.)[None, :]).ravel()
    skipped_decades = decades[~np.isin(decades, major_positive)]
    minor = np.unique(np.concatenate((skipped_decades, subdivisions)))
    minor = minor[(minor > 0) & (minor < upper) & ~np.isin(minor, major_positive)]
    if not len(minor):
        raise ValueError("Registered residual display has no in-range minor ticks")
    return upper, major, minor


def _configure_residual_axis(axis, values, style):
    """Freeze only visible symlog ticks after the common linear-axis styling."""
    upper, major, minor = _residual_tick_plan(values)
    axis.set_yscale("symlog", linthresh=RESIDUAL_LINTHRESH)
    axis.set_ylim(0., upper)
    # Matplotlib's automatic symmetric-log locator may emit negative or
    # out-of-range decades for nonnegative residual data, and may omit minor
    # ticks. Explicit in-range locators preserve the true data and gate while
    # preventing off-canvas labels; no display floor is applied to the data.
    axis.yaxis.set_major_locator(FixedLocator(major))
    axis.yaxis.set_minor_locator(FixedLocator(minor))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.tick_params(axis="y", which="minor", left=True, right=True, direction="out",
                     length=style.minor_tick_length_pt, width=style.minor_tick_width_pt)


def _validate_geometry(payload):
    curve = np.asarray(payload["outer_curve_q2"])
    if curve.shape != (72, 2):
        raise ValueError("F5 requires the frozen 72-node / 36-segment Q2 outer curve")
    _q2_closed_curve(curve)
    _image_coordinates(curve, payload)
    radial = np.asarray(payload["radial_boundary_fractions"])
    if radial.shape != (4,) or not np.allclose(radial, [20/27, 21/27, 22/27, 1.], atol=1e-14, rtol=0):
        raise ValueError("Saved assumed layer fractions differ from the F5 contract")
    labels = np.asarray(payload["layer_ids"])
    if labels.shape != (len(payload["cells"]),) or labels.dtype.kind not in "iu" or np.any((labels < 0) | (labels > 2)):
        raise ValueError("Expected three geometric labels per element, not three material assignments")
    for key in ("inner_midplane_nodes", "outer_midplane_nodes", "anchor_node_ids"):
        ids = np.asarray(payload[key])
        if ids.ndim != 1 or ids.dtype.kind not in "iu" or np.any(ids < 0) or np.any(ids >= len(payload["coordinates"])):
            raise ValueError(f"Invalid saved node identities: {key}")
    if len(payload["anchor_node_ids"]) != 2:
        raise ValueError("The registered gauge needs exactly the two saved A/B nodes")


def _pressure_and_gauge(axis, payload, bounds):
    coordinates = payload["coordinates"]
    arrow_length = .055*(bounds[1]-bounds[0])
    faces = payload["inner_faces"]
    for element, direction, side in faces[::max(1, len(faces)//6)]:
        if direction != 0 or side != -1:
            raise ValueError("Only the registered inner radial pressure faces may be annotated")
        edge = coordinates[payload["cells"][int(element)].reshape(3, 3, 3)[0, :, 1], :2]
        tangent = .5*(edge[2]-edge[0])
        normal = np.array([tangent[1], -tangent[0]])/np.linalg.norm(tangent)
        axis.annotate("", xy=edge[1]+.12*arrow_length*normal, xytext=edge[1]-.88*arrow_length*normal,
                      arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.5})
    anchors = payload["anchor_node_ids"]
    axis.scatter(coordinates[anchors, 0], coordinates[anchors, 1], marker="s", s=32, c=RED, zorder=5)
    for node, label in zip(anchors, ("A", "B")):
        axis.annotate(label, xy=coordinates[node, :2], xytext=(7, 7), textcoords="offset points", color=RED)


def _curve_lines(axis, payload, positions, *, layers=False):
    if layers:
        outer = payload["outer_curve_q2"]
        for fraction, label, color in zip(payload["radial_boundary_fractions"],
                                           ("Cavity 20/27", "Interface 21/27", "Interface 22/27", "Outer 1"),
                                           (BLUE, ORANGE, GREY, BLUE)):
            points = _q2_closed_curve(outer*fraction)
            axis.plot(points[:, 0], points[:, 1], lw=1.5, color=color, label=label)
    else:
        for key in ("inner_midplane_nodes", "outer_midplane_nodes"):
            points = _q2_closed_curve(positions[payload[key], :2])
            axis.plot(points[:, 0], points[:, 1], lw=1.5, color=GREY, ls="--")


def render_fem_contour_pressure(result: Path) -> dict[str, Any]:
    result = Path(result).resolve()
    config = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification_path = result / "verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.is_file() else {}
    qualification = str(verification.get("status", "unknown"))
    expected = np.asarray(config["loads"], dtype=float)
    if expected.shape != (5,) or not np.allclose(expected, [0., .02, .04, .06, .08], atol=1e-14, rtol=0):
        raise ValueError("Saved loading configuration differs from the registered five pressure levels")
    if tuple(case["name"] for case in config["cases"]) != CASE_NAMES:
        raise ValueError("Registered cases must be radial_coarse and radial_fine")
    payloads = _load_retained(result, config)
    if not payloads:
        return {"schema_version": "prl.fem_contour_pressure_rendering.v1", "status": "blocked",
                "qualification_status": qualification, "reason": "No saved equilibrium; no fabricated model/results"}
    for payload in payloads.values():
        _validate_geometry(payload)
    source = _load(result / "geometry_input.npz")
    counts = {name: len(payloads[name]["loads"]) if name in payloads else 0 for name in CASE_NAMES}
    complete = all(count == len(expected) for count in counts.values())
    if qualification == "passed" and not complete:
        raise ValueError("Passing qualification conflicts with missing raw states")
    # Either case may supply an existing reference mesh, but fine state panels
    # never silently substitute coarse equilibria or fill missing frames.
    model_name = "radial_fine" if "radial_fine" in payloads else "radial_coarse"
    model = payloads[model_name]
    model_faces, _, middle_z, model_elements = _midplane_faces(model)
    positions = {name: payload["coordinates"][None]+payload["displacements"] for name, payload in payloads.items()}
    bounds = _square_bounds(np.concatenate([values[..., :2].reshape(-1, 2) for values in positions.values()]), padding=.15)
    image_curve = _image_coordinates(_q2_closed_curve(model["outer_curve_q2"]), model)
    image_bounds = _square_bounds(np.concatenate((source["raw_contour_um"], image_curve)), padding=.12)
    metric_keys = ("cavity_area_change_fraction", "outer_area_change_fraction", "maximum_abs_J_minus_one", "free_force_residual")
    metrics = {name: {key: _independent_metric(verification, name, payload["loads"], key) for key in metric_keys}
               for name, payload in payloads.items()}
    stress = {name: _cell_von_mises(payload) for name, payload in payloads.items()}
    stress_maximum = max(float(values.max()) for values in stress.values())
    # Retain a zero-to-engineering-tolerance floor if only a zero-pressure state
    # exists; never amplify roundoff into a prominent apparent stress pattern.
    stress_upper = max(stress_maximum, 2e-7)
    norm = Normalize(0., stress_upper)
    warnings = []
    for name in CASE_NAMES:
        if counts[name] < len(expected):
            warnings.append(f"{name}: {counts[name]}/5 retained states; missing states not_run")
        if name in metrics:
            for key, values in metrics[name].items():
                if not np.all(np.isfinite(values)):
                    warnings.append(f"{name}: independent {key} missing; no substitute computed")
    folder = result / "figures"
    folder.mkdir(exist_ok=True)
    exports = []

    style, overrides = _compact_style(4.)
    figure = plt.figure(figsize=(14.4, 12.4))
    axes = [_axes(figure, 1.45, 7.15, 4.), _axes(figure, 8., 7.15, 4.),
            _axes(figure, 1.45, 1.8, 4.), _axes(figure, 8., 1.8, 4.)]
    mask = source["slice_mask"]
    voxel = source["voxel_um"]
    axes[0].imshow(mask, origin="lower", cmap="Greys", vmin=0, vmax=1, alpha=.22,
                   extent=(-.5*voxel[0], (mask.shape[1]-.5)*voxel[0],
                           -.5*voxel[1], (mask.shape[0]-.5)*voxel[1]), interpolation="nearest")
    for points, color, label, line_style in ((source["raw_contour_um"], GREY, "Raw outline", "-"),
                                            (source["smooth_contour_um"], ORANGE, "Retained smooth", "-"),
                                            (image_curve, BLUE, "Frozen 36 Q2 segments", "--")):
        closed = np.vstack((points, points[0]))
        axes[0].plot(closed[:, 0], closed[:, 1], color=color, lw=1.5, ls=line_style, label=label)
    _spatial(axes[0], image_bounds, style)
    axes[0].set_xlabel("Image x (µm)")
    axes[0].set_ylabel("Image y (µm)")
    axes[0].legend(loc="upper left", frameon=False)
    add_top_information(axes[0], "A  Fish 4, 72 hpf, XY slice 39\nGrey background: retained tissue mask", style=style)
    _curved_section(axes[1], model_faces, model["coordinates"],
                    fill=LAYER_COLORS[model["layer_ids"][model_elements]], outline="none")
    _curve_lines(axes[1], model, model["coordinates"], layers=True)
    _pressure_and_gauge(axes[1], model, bounds)
    _spatial(axes[1], bounds, style)
    add_top_information(axes[1], "B  Assumed cavity and layer interfaces\nOne homogeneous passive material", style=style)
    for axis, name, letter in zip(axes[2:], CASE_NAMES, ("C", "D")):
        if name in payloads:
            payload = payloads[name]
            faces, _, _, owning_elements = _midplane_faces(payload)
            _curved_section(axis, faces, payload["coordinates"],
                            fill=LAYER_COLORS[payload["layer_ids"][owning_elements]], outline=GREY)
            label = f"{letter}  {name.replace('_', ' ')}: {len(payload['cells'])} hex\nShared periodic seam; all uz=0"
        else:
            _missing(axis, f"{name.replace('_', ' ')}\nNo saved reference mesh")
            label = f"{letter}  Missing / NOT_RUN"
        _spatial(axis, bounds, style)
        add_top_information(axis, label, style=style)
    figure.text(.5, .077, "Layer radii: 20/27 cavity, 21/27 and 22/27 interfaces, outer 1; colors are geometric labels, NOT material differences", ha="center")
    figure.text(.5, .043, "A: ux=uy=0; B: uy=0, ux free; three in-plane gauge DOFs only. All nodes uz=0; arrows indicate pressure direction", ha="center")
    exports.extend(_export(figure, axes, folder / "model_structure", style, overrides))

    style, overrides = _compact_style(4.)
    figure = plt.figure(figsize=(14.4, 12.4))
    axes = [_axes(figure, 1.45, 7.15, 4.), _axes(figure, 8., 7.15, 4.),
            _axes(figure, 1.45, 1.8, 4.), _axes(figure, 8., 1.8, 4.)]
    plot_specs = (
        ("cavity_area_change_fraction", 100.0),
        ("maximum_abs_J_minus_one", 100.0),
        ("free_force_residual", 1.0),
    )
    residual_values = np.concatenate([values["free_force_residual"] for values in metrics.values()])
    finite_residuals = residual_values[np.isfinite(residual_values)]
    for name, color in zip(CASE_NAMES, (ORANGE, BLUE)):
        if name not in payloads:
            continue
        for axis, (key, scale) in zip(axes[:3], plot_specs):
            values = metrics[name][key]
            if np.any(np.isfinite(values)):
                axis.plot(payloads[name]["loads"], scale*values, color=color, marker="o", lw=1.5,
                          label=name.replace("radial_", "Radial "))
    matching_loads, differences = [], []
    if all(name in payloads for name in CASE_NAMES):
        for state, load in enumerate(payloads["radial_fine"]["loads"]):
            matches = np.flatnonzero(np.isclose(payloads["radial_coarse"]["loads"], load, atol=1e-14, rtol=0))
            fine_value = metrics["radial_fine"]["cavity_area_change_fraction"][state]
            if len(matches) == 1:
                coarse_value = metrics["radial_coarse"]["cavity_area_change_fraction"][matches[0]]
                if np.isfinite(fine_value) and np.isfinite(coarse_value):
                    matching_loads.append(float(load))
                    differences.append(100*abs(coarse_value-fine_value))
    if differences:
        axes[3].plot(matching_loads, differences, color=BLUE, marker="o", lw=1.5, label="Absolute cavity-response difference")
    axes[2].axhline(2e-6, color=RED, lw=1.5, ls="--", label="2e-6 qualification limit")
    axes[3].axhline(.2, color=RED, lw=1.5, ls="--", label="0.2 pp end-load limit")
    labels = (("A  Constructed cavity area response", "Cavity area change (%)"),
              ("B  Local volume ratio", "Maximum |J−1| (%)"),
              ("C  Independent force balance", "Free-force residual"),
              ("D  Same geometry: radial check only", "Cavity-response difference (pp)"))
    for index, (axis, (title, ylabel)) in enumerate(zip(axes, labels)):
        if index < 3:
            key = plot_specs[index][0]
            available = any(name in metrics and np.any(np.isfinite(metrics[name][key]))
                            for name in CASE_NAMES)
        else:
            available = bool(differences)
        if not available:
            _missing(axis, "Independent metric unavailable")
        if index != 2:
            axis.set_ylim(bottom=min(0., axis.get_ylim()[0]))
        _linear(axis, style, "Cavity pressure / μ", ylabel, expected)
        if index == 2:
            _configure_residual_axis(axis, finite_residuals, style)
        add_top_information(axis, title, style=style)
        if axis.get_lines():
            axis.legend(loc="upper left", frameon=False)
    residual_text = f"max independent free-force residual={np.max(finite_residuals):.2e}" if len(finite_residuals) else "independent residual unavailable"
    figure.text(.5, .077, f"Qualification {qualification.upper()}; {residual_text}; local stress peaks are reported, NOT convergence-qualified", ha="center")
    figure.text(.5, .043, "Only wall-thickness resolution changes; no circumferential convergence or cylindrical analytic truth; pressure is NOT physiological time", ha="center")
    exports.extend(_export(figure, axes, folder / "mechanics_results", style, overrides))

    style, overrides = _compact_style(2.3, small=True)
    figure = plt.figure(figsize=(18.5, 6.1))
    axes, collection = [], None
    retained_indices = _select_states(payloads, expected)
    fine = payloads.get("radial_fine")
    fine_faces, fine_elements = None, None
    if fine is not None:
        fine_faces, _, _, fine_elements = _midplane_faces(fine)
    for index, load in enumerate(expected):
        axis = _axes(figure, 1.+3.2*index, 1.65, 2.3)
        axes.append(axis)
        retained = retained_indices[index]
        if retained is None:
            _missing(axis, "NOT_RUN\nNo fine equilibrium")
            label = f"p/μ={load:g}\nfine state missing"
        else:
            collection = _curved_section(axis, fine_faces, positions["radial_fine"][retained],
                                        values=stress["radial_fine"][retained, fine_elements], norm=norm, outline=GREY)
            value = metrics["radial_fine"]["cavity_area_change_fraction"][retained]
            area_text = f"cavity ΔA/A0={100*value:.2f}%" if np.isfinite(value) else "independent area unavailable"
            label = f"p/μ={load:g} · real fine state\n{area_text}"
        _spatial(axis, bounds, style)
        add_top_information(axis, label, style=style)
    if collection is not None:
        _colorbar(figure, collection, (16.55, 1.65, .15, 2.3), "Total von Mises / μ", style)
    figure.text(.48, .105, f"Fine: {counts['radial_fine']}/5 actual states; 1× displacement and identical spatial/color scales; 3-D formulation with all uz=0", ha="center")
    figure.text(.48, .057, "Color: cell maximum total 3-D Cauchy von Mises over 27 Gauss points, including sigma_zz; not active tension or cavity pressure", ha="center")
    exports.extend(_export(figure, axes, folder / "five_states", style, overrides))

    report = {
        "schema_version": "prl.fem_contour_pressure_rendering.v1", "status": "passed",
        "qualification_status": qualification, "saved_state_counts": counts,
        "all_registered_states_available": complete, "warnings": warnings,
        "display_case": "radial_fine", "display_state_indices": retained_indices,
        "reference_model_source_case": model_name, "deformation_scale": 1.,
        "xy_bounds_solver_units": list(bounds), "reference_section_z": middle_z,
        "source_image": "geometry_input.npz, retained F2 source arrays; no resegmentation or smoothing",
        "curve": "72 saved nodes / 36 periodic Q2 segments, spatial interpolation only",
        "reference_shape_assumption": "static arrested source outline assumed zero-pressure stress-free; not established by image",
        "constructed_radial_interfaces": [20/27, 21/27, 22/27, 1.],
        "layer_colors": "geometric labels only; all elements share one passive material",
        "stress_field": "per-element max 3-D total Cauchy von Mises over all 27 stored Gauss points, including sigma_zz",
        "stress_color_range": [0., stress_upper], "stress_display_floor": 2e-7,
        "area_metric_source": "independent verification of the actual Q2 closed curves; not straight-node polygons",
        "residual_display": "independent free-force residual on a symmetric-log scale; qualification limit 2e-6",
        "radial_difference_percentage_points": {"loads": matching_loads, "values": differences},
        "mesh_claim": "radial-only resolution check; circumferential and stress-peak convergence not_run",
        "heart_volume_or_ejection_fraction": "not_run", "physiological_time": "not_run", "biological_validation": "not_run",
        "exports": [path.relative_to(result).as_posix() for path in exports],
    }
    (result / "rendering.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    warning_html = "".join(f"<li>{escape(item)}</li>" for item in warnings)
    links = " · ".join(f'<a href="raw/{name}.npz">{name} 原始状态</a>' for name in payloads)
    verifier_link = '<a href="verification.json">独立验证</a>' if verification_path.is_file() else '独立验证缺失（unknown）'
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F5 图像外轮廓的被动有限变形</title><style>body{{font:17px/1.65 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;color:#263d4b}}img{{max-width:100%}}.note{{background:#f2f5f7;border-left:4px solid #a9453b;padding:16px}}a{{color:#1b608b}}</style>
<h1>F5｜图像来源外轮廓的被动有限变形</h1>
<p class="note">独立资格：<strong>{escape(qualification)}</strong>；厚向 coarse 保存 {counts['radial_coarse']}/5 态，fine 保存 {counts['radial_fine']}/5 态。
渲染通过不等于科学验证通过。本页是三维实体单元的<strong>平面应变挤出模型</strong>，不是自由三维真实心室，也不是实验心动周期。</p>
<p>来源为已保留的72 hpf Fish 4组织mask最大占据XY切片39；未重新分割、平滑、拟合或修改旧结果。
仅外轮廓来自图像，36段Q2曲线是已冻结的空间离散。内腔20/27及21/27、22/27层界为相对于来源中心的同心缩放，不是实测内腔、恒法向壁厚或真实组织层界。
三种颜色只是几何标签，本阶段全部采用同一未标定被动Neo-Hookean μ=1、κ=1000；无主动张力、分层材料、ECM反馈或血流。</p>
<p><strong>参考态假设：</strong>把停跳静态图像外形假定为零压无应力构形；图像本身不能证明这一点。
挤出高度H=0.5是计算假设，不是实测心室纵深。所有uz=0；仅A点ux/uy和B点uy三个平面内刚体规范，B点ux自由，没有F4对称切面或心壁夹持。
内腔正压力随当前法向和面积更新，外壁无牵引，无端盖压力。p/μ=0至0.08是无量纲准静态加载级，不是Pa、时间或心率。</p>
<ul>{warning_html}</ul>
<figure><img src="figures/model_structure.png" alt="来源mask和轮廓、构造层界、周期曲面网格及约束"><figcaption>A：原mask、原轮廓、保留平滑轮廓与冻结Q2曲线经刚体逆变换在图像坐标叠加。B：构造腔和几何层界、两个锚点及压力方向；箭头仅示载荷方向，不表示零压时有力。C/D：真实三维网格中截面，两档仅厚向1/1/2与2/2/4细分；周向位移和压力节点真正共享，没有人工切缝。所有节点uz=0。</figcaption></figure>
<figure><img src="figures/mechanics_results.png" alt="独立腔面积响应、局部体积变化、自由力残差及厚向网格差"><figcaption>面积由独立验证对实际Q2闭曲线积分得到，不使用直线多边形替代。D为两档腔面积相对响应之差，单位为百分点；合同还要求末态差不超过fine幅度的5%，所有门以独立验证为准。
 C面板以对称对数轴显示独立自由力残差及2e-6合同门限。这里只检查厚向离散，周向形状完全相同；不能声称周向或局部应力热点已收敛。非圆轮廓不套用F4圆柱解析解。构造腔面积变化不是射血分数或实测心室体积。</figcaption></figure>
<figure><img src="figures/five_states.png" alt="fine网格五级压力真实状态，缺失级明确标注"><figcaption>只展示fine真实保存的五级状态，缺失级不插值、不替换coarse、不补帧。形变均为1倍，空间和应力色标固定。颜色为每个三维单元27个积分点中最大总Cauchy von Mises应力，包含σzz，映射为分片常数；不是主动应力，也不是边界腔压或混合压力变量。</figcaption></figure>
<p><a href="geometry_input.npz">保留图像几何输入</a> · <a href="geometry_adaptation.json">几何适配审计</a> · <a href="configuration.json">冻结配置</a> · {verifier_link} · <a href="rendering.json">渲染定义</a> · {links}</p></html>"""
    (result / "index.html").write_text(page, encoding="utf-8")
    size = sum(path.stat().st_size for path in result.rglob("*") if path.is_file())
    cap = int(config.get("resources", {}).get("stage_bytes", 64*1024**2))
    if size > cap:
        raise RuntimeError("Contour-pressure evidence exceeded its stage budget; no deletion or retry")
    return report
