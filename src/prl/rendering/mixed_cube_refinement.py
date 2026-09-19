"""Portable, render-only evidence page for the frozen n4/n8/n12 refinement."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

FINE_CASE = "mms_p3p2_n12"
GRID_LEVELS = (4, 8, 12)
METRICS = (("u_L2", "relative_u_L2", "u L2", 3.5),
           ("u_H1", "relative_u_H1", "u H1", 2.5),
           ("pressure_L2", "relative_pressure_L2", "p L2", 2.5))


def _prepare_plot_data(report, arrays):
    """Validate retained data and independently recompute the non-dyadic EOC."""
    convergence = report.get("convergence", {})
    if convergence.get("primary_pair", [8, 12]) != [8, 12]:
        raise ValueError("The frozen primary pair is n8 to n12")
    if convergence.get("grid_levels", [4, 8, 12]) != [4, 8, 12]:
        raise ValueError("The frozen grid sequence is n4, n8, n12")
    rows = {}
    for row in report["cases"]:
        n = int(row["n"])
        if n not in GRID_LEVELS or n in rows:
            raise ValueError("Expected one retained row per registered n4/n8/n12 case")
        if row.get("u_degree", 3) != 3 or row.get("p_degree", 2) != 2:
            raise ValueError("Refinement plot supports only P3/P2")
        if row.get("kind", "mms") != "mms":
            raise ValueError("Refinement plot supports only the original MMS")
        rows[n] = row
    curves, primary, historical = {}, {}, {}
    for label, metric, _, _ in METRICS:
        values = {}
        for n, row in rows.items():
            if row.get("equilibrium") == "not_run" or not row.get("metrics"):
                continue
            value = row["metrics"].get(metric)
            if value is None:
                continue
            value = float(value)
            if not np.isfinite(value) or value < 0:
                raise ValueError("Retained errors must be finite and nonnegative")
            values[n] = value
        curves[label] = values
        primary[label] = (float(np.log(values[8] / values[12]) / np.log(12 / 8))
                          if values.get(8, 0) > 0 and values.get(12, 0) > 0 else None)
        historical[label] = (float(np.log(values[4] / values[8]) / np.log(8 / 4))
                             if values.get(4, 0) > 0 and values.get(8, 0) > 0 else None)
        reported = convergence.get("primary_EOC", {}).get(label)
        if reported is not None and (primary[label] is None or not np.isfinite(reported)
                                      or abs(float(reported) - primary[label]) > 1e-10):
            raise ValueError("Reported primary EOC disagrees with ln(E8/E12)/ln(1.5)")
    result = {"curves": curves, "primary_EOC": primary, "historical_EOC": historical,
              "reference": None, "slice": None, "states": []}
    if FINE_CASE + "_coordinates" not in arrays:
        return result
    coordinates = np.asarray(arrays[FINE_CASE + "_coordinates"], dtype=float)
    faces = np.asarray(arrays[FINE_CASE + "_boundary_faces"])
    tags = np.asarray(arrays[FINE_CASE + "_boundary_tags"])
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.isfinite(coordinates).all():
        raise ValueError("Saved n12 coordinates must be finite N-by-3")
    if (faces.ndim != 2 or faces.shape[1] < 3 or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0
            or faces.max() >= len(coordinates) or tags.shape != (len(faces),)
            or not np.isin(tags, np.arange(1, 7)).all()):
        raise ValueError("Saved n12 boundary connectivity/tags are invalid")
    result["reference"] = {"coordinates": coordinates, "faces": faces[:, :3], "tags": tags}
    indices = np.asarray(arrays.get(FINE_CASE + "_iterations", []))
    if indices.ndim != 1 or (len(indices) and (not np.issubdtype(indices.dtype, np.integer)
            or indices.min() < 0 or np.any(np.diff(indices) <= 0))):
        raise ValueError("Saved iteration indices must be unique increasing integers")
    if not len(indices):
        return result
    entries = report.get("iterate_diagnostics", {}).get(FINE_CASE, [])
    history = {int(entry["iteration"]): entry for entry in entries}
    if len(history) != len(entries) or set(history) != set(indices.tolist()):
        raise ValueError("Saved iteration array and report history must agree exactly")
    selected = np.flatnonzero(np.isclose(coordinates[:, 2], .5, atol=1e-12, rtol=0))
    if len(selected) < 3 or np.linalg.matrix_rank(coordinates[selected, :2] - coordinates[selected[0], :2]) < 2:
        raise ValueError("No actual two-dimensional saved-node slice at reference Z/L=0.5")
    result["slice"] = coordinates[selected, :2]
    for position in sorted({0, len(indices) // 2, len(indices) - 1}):
        index = int(indices[position])
        displacement = np.asarray(arrays[FINE_CASE + f"_u_{index}"], dtype=float)
        residual = float(history[index]["residual"])
        if displacement.shape != coordinates.shape or not np.isfinite(displacement).all():
            raise ValueError("Saved displacement does not match the finite n12 coordinates")
        if not np.isfinite(residual) or residual < 0:
            raise ValueError("Saved Newton residual must be finite and nonnegative")
        result["states"].append({"iteration": index, "residual": residual, "u": displacement[selected]})
    return result


def draw_refinement(report, arrays, style_module, output_png, output_svg,
                    axis_box_size_in=(4.0, 4.0), deformation_scale=30.0, export_dpi=160):
    """Export real n12 geometry/states and n4/n8/n12 errors; never run a solver."""
    prepared = _prepare_plot_data(report, arrays)
    output_png, output_svg = Path(output_png), Path(output_svg)
    if output_png.parent.resolve() != output_svg.parent.resolve():
        raise ValueError("PNG/SVG must belong to one working figure package")
    if output_png.suffix.lower() != ".png" or output_svg.suffix.lower() != ".svg":
        raise ValueError("Explicit PNG/SVG file extensions are required")
    dimensions = np.asarray(axis_box_size_in, dtype=float)
    if dimensions.shape != (2,) or not np.isfinite(dimensions).all() or np.any(dimensions <= 0):
        raise ValueError("Axis-box dimensions must be positive and finite")
    if not np.isfinite(deformation_scale) or deformation_scale <= 0:
        raise ValueError("Geometry display scale must be positive and finite")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator, LogFormatterSciNotation, NullFormatter
    from matplotlib.tri import Triangulation

    style = style_module.StyleSpec(
        axis_box_size_in=tuple(dimensions), tick_label_size=14., axis_label_size=17.,
        annotation_font_size=14., sample_size_and_stat_font_size=14., legend_font_size=12.,
        axes_line_width=1.4, major_tick_length_pt=5., major_tick_width_pt=1.,
        minor_tick_length_pt=3., minor_tick_width_pt=.8, data_line_width=1.5,
        tick_label_pad_pt=4., axis_label_pad_pt=8., export_dpi=export_dpi)
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(field=key, reason=
        "Approved compact exploratory refinement page: fixed 4x4-inch axes and 160 dpi; not publication final.")
        for key, value in asdict(style).items() if value != defaults[key]]
    axis_width, axis_height = dimensions
    left, gap, bottom, row_gap, top, right = 1.25, 2.25, 3., 1.4, 1.7, 2.25
    width, height = left + 3 * axis_width + 2 * gap + right, bottom + 2 * axis_height + row_gap + top
    figure = plt.figure(figsize=(width, height))
    positions = [(left + column * (axis_width + gap), y)
                 for y in (bottom + axis_height + row_gap, bottom) for column in range(3)]
    axes = [figure.add_axes([x / width, y / height, axis_width / width, axis_height / height])
            for x, y in positions]
    titles = ["A  Actual n=12 reference / boundary tags", "B  P3/P2 retained field errors",
              "C  Primary observed order: n=8 to 12"]

    def unavailable(axis, message):
        axis.text(.5, .5, message, transform=axis.transAxes, ha="center", va="center")
        axis.set(xlim=(0, 1), ylim=(0, 1))

    def equal_limits(axis, lower, upper):
        center = (np.asarray(lower) + np.asarray(upper)) / 2
        span = np.asarray(upper) - np.asarray(lower)
        scale = max(span[0] / axis_width, span[1] / axis_height) * 1.10
        half = scale * dimensions / 2
        axis.set(xlim=(center[0] - half[0], center[0] + half[0]),
                 ylim=(center[1] - half[1], center[1] + half[1]), aspect="equal")

    reference = prepared["reference"]
    if reference is None:
        unavailable(axes[0], "Actual n=12 reference: not_run")
    else:
        view = np.array([-1.8, -2.4, 1.6]); view /= np.linalg.norm(view)
        horizontal = np.cross([0., 0., 1.], view); horizontal /= np.linalg.norm(horizontal)
        projection = np.stack([horizontal, np.cross(view, horizontal)], axis=1)
        triangles = reference["coordinates"][reference["faces"]]
        order = np.argsort(triangles.mean(axis=1) @ view)
        colors = np.where(reference["tags"] == 1, "#C97065", "#9CC5D5")
        axes[0].add_collection(PolyCollection((triangles @ projection)[order], facecolors=colors[order],
                                             edgecolors="#324B54", linewidths=.2))
        xy = reference["coordinates"] @ projection
        equal_limits(axes[0], xy.min(axis=0), xy.max(axis=0))
        axes[0].set(xlabel="Projected X / L", ylabel="Projected height / L")

    palette = ("#207052", "#A76335", "#397DA6")
    error_values = []
    for (label, _, readable, _), color, marker in zip(METRICS, palette, ("o", "s", "^")):
        values = {n: error for n, error in prepared["curves"][label].items() if error > 0}
        levels = sorted(values)
        errors = [values[n] for n in levels]
        axes[1].plot(levels, errors, color=color, marker=marker, linewidth=1.5, markersize=6,
                     linestyle="-" if len(levels) == 3 else "none", label=readable)
        error_values.extend(errors)
    axes[1].set(xlabel="Grid divisions n", ylabel="Relative field error")
    if error_values:
        axes[1].set_xscale("log"); axes[1].set_xlim(3.5, 13.7)
        axes[1].set_xticks([4, 8, 12], ["4", "8", "12"])
        axes[1].set_yscale("log")
        axes[1].legend(loc="upper right")
    else:
        unavailable(axes[1], "Retained field errors: not_run")
    measured = [prepared["primary_EOC"][label] for label, _, _, _ in METRICS]
    for index, ((_, _, _, threshold), color, value) in enumerate(zip(METRICS, palette, measured)):
        axes[2].plot([index - .2, index + .2], [threshold, threshold], color="#666666",
                     linestyle="--", linewidth=1.5, label="Original order limit" if index == 0 else None)
        if value is not None:
            axes[2].plot(index, value, marker="o", color=color, markersize=8, linestyle="none")
            axes[2].annotate(f"{value:.3f}", (index, value), xytext=(0, 11), textcoords="offset points", ha="center")
    if not any(value is not None for value in measured):
        axes[2].text(.5, .35, "Primary order unavailable", transform=axes[2].transAxes, ha="center")
    extrema = [0., 3.5, *[value for value in measured if value is not None]]
    axes[2].set(xlim=(-.6, 2.6), ylim=(min(extrema) - .4, max(extrema) + 1.), ylabel="Observed order")
    axes[2].set_xticks(range(3), [row[2] for row in METRICS]); axes[2].legend(loc="lower right")

    states = prepared["states"]
    if states:
        xy = prepared["slice"]
        triangle_indices = Triangulation(xy[:, 0], xy[:, 1]).triangles
        values = np.concatenate([state["u"][:, 0] for state in states])
        low, high = float(values.min()), float(values.max())
        if low == high:
            padding = max(abs(low) * .01, np.finfo(float).eps)
            low, high = low - padding, high + padding
        norm = Normalize(low, high)
        deformed = [xy + deformation_scale * state["u"][:, :2] for state in states]
        bounds = np.concatenate([xy, *deformed])
        for panel, (state, current) in enumerate(zip(states, deformed), start=3):
            colors = plt.colormaps["viridis"](norm(state["u"][triangle_indices, 0].mean(axis=1)))
            axes[panel].add_collection(PolyCollection(current[triangle_indices], facecolors=colors, edgecolors="none"))
            lower, upper = xy.min(axis=0), xy.max(axis=0)
            axes[panel].plot([lower[0], upper[0], upper[0], lower[0], lower[0]],
                             [lower[1], lower[1], upper[1], upper[1], lower[1]],
                             color="#555555", linestyle="--", linewidth=.8)
            equal_limits(axes[panel], bounds.min(axis=0), bounds.max(axis=0))
            axes[panel].set(xlabel="X / L", ylabel="Y / L")
            titles.append(f"{chr(65 + panel)}  n=12 saved Newton iteration {state['iteration']}\n"
                          f"Residual = {state['residual']:.2e}")
        color_axis = figure.add_axes([(positions[5][0] + axis_width + .4) / width,
                                      bottom / height, .16 / width, axis_height / height])
        color_bar = figure.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap="viridis"), cax=color_axis)
        color_bar.set_label("Numerical u_x / L (unscaled)", fontsize=14, labelpad=8)
        color_bar.ax.tick_params(labelsize=12)
    for panel in range(3 + len(states), 6):
        unavailable(axes[panel], "Saved state unavailable\nnot_run / not retained")
        titles.append(f"{chr(65 + panel)}  No synthesized state")
    for axis, title in zip(axes, titles):
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, title, style=style)
    if error_values:
        low, high = min(error_values) / 1.5, max(error_values) * 1.5
        powers = range(int(np.floor(np.log10(low))), int(np.ceil(np.log10(high))) + 1)
        major = [10. ** exponent for exponent in powers if low <= 10. ** exponent <= high]
        if not major:
            major = [float(np.sqrt(low * high))]
        minor = [factor * 10. ** exponent for exponent in powers for factor in range(2, 10)
                 if low <= factor * 10. ** exponent <= high]
        axes[1].set_ylim(low, high)
        axes[1].yaxis.set_major_locator(FixedLocator(major))
        axes[1].yaxis.set_minor_locator(FixedLocator(minor))
        axes[1].yaxis.set_major_formatter(LogFormatterSciNotation())
        axes[1].xaxis.set_minor_locator(FixedLocator([5, 6, 7, 9, 10, 11]))
        axes[1].xaxis.set_minor_formatter(NullFormatter())
    historical = ", ".join(f"{readable}={prepared['historical_EOC'][label]:.3f}"
                           if prepared["historical_EOC"][label] is not None else f"{readable}=not_run"
                           for label, _, readable, _ in METRICS)
    status = report.get("convergence", {}).get("status", "unknown")
    footer = [
        f"Registered n=4/8/12 qualification: {status}. Prior 2/4/8 L2-order failure and ventricular failure remain unchanged.",
        "A: actual n=12 mesh; red X=0 exact displacement; other faces exact reference traction with compatible body force.",
        "B-C: mu=1, kappa=100, P3/P2 and Q8 unchanged. Primary order uses ln(E8/E12) / ln(1.5), not ln(2).",
        f"Historical n=4 to 8 orders: {historical}. Missing/zero errors are not log-plotted; no fabricated states.",
        f"D-F: retained reference Z/L=0.5 nodes, geometry x{deformation_scale:g}, colors unscaled; piecewise-linear display.",
        "Newton iterations are algorithm progress, NOT physiological time. 160 dpi exploratory page, not publication final.",
    ]
    for y_in, content in zip((1.85, 1.55, 1.25, .95, .65, .35), footer):
        figure.text(left / width, y_in / height, content, fontsize=12)
    try:
        exported = style_module.export_figure(figure, axes, output_png.with_suffix(""), style=style, overrides=overrides)
        if exported.svg.resolve() != output_svg.resolve():
            exported.svg.replace(output_svg)
        manifest = json.loads(exported.manifest.read_text(encoding="utf-8"))
        manifest["exports"]["svg"] = str(output_svg.resolve())
        manifest["evidence_selection"] = {
            "reference_case": FINE_CASE if reference is not None else None,
            "state_case": FINE_CASE if states else None,
            "selected_saved_iterations": [state["iteration"] for state in states],
            "primary_pair": [8, 12], "primary_mesh_ratio": 1.5,
            "primary_EOC_recomputed": prepared["primary_EOC"], "historical_EOC": prepared["historical_EOC"],
            "state_synthesis": False, "physiological_time": False,
            "deformation_display_scale": deformation_scale, "field_values_scaled": False,
        }
        exported.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"png": str(exported.png), "svg": str(output_svg), "manifest": str(exported.manifest)}
    finally:
        plt.close(figure)
