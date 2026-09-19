"""Portable figure renderer for persisted mixed-cube representation evidence.

Only NumPy, Matplotlib and the copied unified-style module are required.  No
solver, analytical solution, report builder or external project path is used.
"""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np


PATCH_CASE = "patch_cubic_volume_p3p2"
FINE_CASE = "mms_p3p2_n8"


def _prepare_plot_data(report, arrays):
    """Validate persisted inputs and choose real first/middle/last iterates.

    This part is intentionally independent of Matplotlib and file writes, so
    evidence selection can be tested without generating a figure or cache.
    Missing cases remain missing; no state or error is reconstructed here.
    """
    result = {"curves": {}, "reference": None, "slice": None, "states": []}
    for degree in (1, 2):
        rows = sorted(
            (row for row in report["cases"]
             if row.get("kind") == "mms" and row.get("u_degree") == 3
             and row.get("p_degree") == degree),
            key=lambda row: row["n"],
        )
        points = []
        for row in rows:
            if row.get("equilibrium") == "not_run" or not row.get("metrics"):
                continue
            dof = float(row["DOF"])
            if not np.isfinite(dof) or dof <= 0:
                raise ValueError("A retained error requires a positive finite DOF count")
            errors = {}
            for key in ("relative_u_H1", "relative_pressure_L2"):
                value = row["metrics"].get(key)
                if value is None:
                    continue
                value = float(value)
                if not np.isfinite(value) or value < 0:
                    raise ValueError("A retained error must be finite and nonnegative")
                errors[key] = value
            points.append({"n": int(row["n"]), "DOF": dof, "errors": errors})
        result["curves"][degree] = points

    def coordinates_for(name):
        coordinates = np.asarray(arrays[name + "_coordinates"], dtype=float)
        if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.isfinite(coordinates).all():
            raise ValueError("Saved coordinates must be a finite N-by-3 array")
        return coordinates

    if PATCH_CASE + "_coordinates" in arrays:
        coordinates = coordinates_for(PATCH_CASE)
        faces = np.asarray(arrays[PATCH_CASE + "_boundary_faces"])
        tags = np.asarray(arrays[PATCH_CASE + "_boundary_tags"])
        if (faces.ndim != 2 or faces.shape[1] < 3 or not len(faces)
                or not np.issubdtype(faces.dtype, np.integer)
                or faces.min() < 0 or faces.max() >= len(coordinates)
                or tags.shape != (len(faces),) or not np.isin(tags, np.arange(1, 7)).all()):
            raise ValueError("Saved boundary connectivity/tags are invalid")
        result["reference"] = {"coordinates": coordinates, "faces": faces[:, :3], "tags": tags}

    if FINE_CASE + "_coordinates" not in arrays:
        return result
    coordinates = coordinates_for(FINE_CASE)
    saved_indices = np.asarray(arrays.get(FINE_CASE + "_iterations", []))
    if saved_indices.ndim != 1 or (len(saved_indices) and (
            not np.issubdtype(saved_indices.dtype, np.integer)
            or saved_indices.min() < 0 or np.any(np.diff(saved_indices) <= 0))):
        raise ValueError("Saved iteration numbers must be unique increasing integers")
    if not len(saved_indices):
        return result
    histories = report.get("iterate_diagnostics", {}).get(FINE_CASE, [])
    history = {int(entry["iteration"]): entry for entry in histories}
    if len(history) != len(histories) or set(history) != set(saved_indices.tolist()):
        raise ValueError("Saved-state iterations and report history must agree exactly")
    slice_indices = np.flatnonzero(np.isclose(coordinates[:, 2], 0.5, atol=1e-12, rtol=0))
    if len(slice_indices) < 3 or np.linalg.matrix_rank(
            coordinates[slice_indices, :2] - coordinates[slice_indices[0], :2]) < 2:
        raise ValueError("No two-dimensional saved-node slice at Z/L=0.5")
    result["slice"] = coordinates[slice_indices, :2]
    selected_positions = sorted({0, len(saved_indices) // 2, len(saved_indices) - 1})
    for position in selected_positions:
        iteration = int(saved_indices[position])
        displacement = np.asarray(arrays[FINE_CASE + f"_u_{iteration}"], dtype=float)
        if displacement.shape != coordinates.shape or not np.isfinite(displacement).all():
            raise ValueError("Saved displacement must match the finite coordinate array")
        residual = float(history[iteration]["residual"])
        if not np.isfinite(residual) or residual < 0:
            raise ValueError("Saved residual must be finite and nonnegative")
        result["states"].append({"iteration": iteration, "residual": residual,
                                 "u": displacement[slice_indices]})
    return result


def draw_representation(report, arrays, style_module, output_png, output_svg,
                        axis_box_size_in=(4.0, 4.0), deformation_scale=30.0,
                        export_dpi=160):
    """Draw actual geometry, two error/cost curves and three saved Newton states.

    ``report`` is delivery_analysis.json loaded as a dictionary; ``arrays`` is
    figure_states.npz loaded with allow_pickle=False.  Keys use the full case
    name prefixes retained by mixed_cube_representation_delivery.  State panels
    select actual first/middle/last stored indices, never interpolated states.
    An absent case is labelled not_run; fewer than three saved states leave
    explicitly unavailable panels.  The slice uses existing Z=0.5L nodes only.

    The caller supplies a copied cb_plot_unified_style module and PNG/SVG paths
    inside one working figure package.  The 160 dpi compact layout is the
    approved exploratory exception, not publication-quality acceptance.
    """
    prepared = _prepare_plot_data(report, arrays)
    output_png, output_svg = Path(output_png), Path(output_svg)
    if output_png.parent.resolve() != output_svg.parent.resolve():
        raise ValueError("PNG and SVG must belong to the same figure package")
    if output_png.suffix.lower() != ".png" or output_svg.suffix.lower() != ".svg":
        raise ValueError("Explicit PNG and SVG output paths are required")
    axis_size = np.asarray(axis_box_size_in, dtype=float)
    if axis_size.shape != (2,) or not np.isfinite(axis_size).all() or np.any(axis_size <= 0):
        raise ValueError("Axis-box dimensions must be two positive finite numbers")
    if not np.isfinite(deformation_scale) or deformation_scale <= 0:
        raise ValueError("Deformation display scale must be positive and finite")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator, LogFormatterSciNotation
    from matplotlib.tri import Triangulation

    style = style_module.StyleSpec(
        axis_box_size_in=tuple(axis_size), tick_label_size=14.0,
        axis_label_size=17.0, annotation_font_size=14.0,
        sample_size_and_stat_font_size=14.0, legend_font_size=12.0,
        axes_line_width=1.4, major_tick_length_pt=5.0, major_tick_width_pt=1.0,
        minor_tick_length_pt=3.0, minor_tick_width_pt=0.8,
        data_line_width=1.5, tick_label_pad_pt=4.0, axis_label_pad_pt=8.0,
        export_dpi=export_dpi,
    )
    defaults = asdict(style_module.DEFAULT_STYLE)
    overrides = [style_module.StyleOverride(
        field=key,
        reason="Approved compact exploratory multi-panel representation page; "
               "saved model data and 160 dpi preview, not publication final.",
    ) for key, value in asdict(style).items() if value != defaults[key]]
    # Physical axis sizes remain fixed; all spacing is explicit in inches.
    axis_width, axis_height = axis_size
    left, column_gap, bottom, row_gap, top, right = 1.25, 2.25, 3.0, 1.4, 1.7, 2.25
    width = left + 3 * axis_width + 2 * column_gap + right
    height = bottom + 2 * axis_height + row_gap + top
    figure = plt.figure(figsize=(width, height))
    positions = [(left + column * (axis_width + column_gap), y)
                 for y in (bottom + axis_height + row_gap, bottom) for column in range(3)]
    axes = [figure.add_axes([x / width, y / height, axis_width / width, axis_height / height])
            for x, y in positions]
    titles = ["A  Actual reference mesh / boundary tags",
              "B  Displacement H1 error / cost",
              "C  Pressure L2 error / cost"]

    def unavailable(axis, message):
        axis.text(0.5, 0.5, message, transform=axis.transAxes, ha="center", va="center")
        axis.set(xlim=(0, 1), ylim=(0, 1))

    def equal_limits(axis, lower, upper):
        center = (np.asarray(lower) + np.asarray(upper)) / 2
        span = np.asarray(upper) - np.asarray(lower)
        scale = max(span[0] / axis_width, span[1] / axis_height) * 1.10
        half = scale * axis_size / 2
        axis.set(xlim=(center[0] - half[0], center[0] + half[0]),
                 ylim=(center[1] - half[1], center[1] + half[1]), aspect="equal")

    reference = prepared["reference"]
    if reference is None:
        unavailable(axes[0], "Reference mesh: not_run")
    else:
        view = np.array([-1.8, -2.4, 1.6])
        view /= np.linalg.norm(view)
        horizontal = np.cross([0.0, 0.0, 1.0], view)
        horizontal /= np.linalg.norm(horizontal)
        projection = np.stack([horizontal, np.cross(view, horizontal)], axis=1)
        triangles = reference["coordinates"][reference["faces"]]
        order = np.argsort(triangles.mean(axis=1) @ view)
        face_colors = np.where(reference["tags"] == 1, "#C97065", "#9CC5D5")
        axes[0].add_collection(PolyCollection((triangles @ projection)[order],
                                             facecolors=face_colors[order],
                                             edgecolors="#324B54", linewidths=0.5))
        projected = reference["coordinates"] @ projection
        equal_limits(axes[0], projected.min(axis=0), projected.max(axis=0))
        axes[0].set(xlabel="Projected X / L", ylabel="Projected height / L")

    def log_ticks(axis, values, direction):
        positive = np.asarray([value for value in values if value > 0], dtype=float)
        if not len(positive):
            return
        low, high = positive.min() / 1.45, positive.max() * 1.45
        if high / low < 3:
            low, high = positive.min() / 2, positive.max() * 2
        powers = np.arange(int(np.floor(np.log10(low))), int(np.ceil(np.log10(high))) + 1)
        major = [10.0 ** power for power in powers if low <= 10.0 ** power <= high]
        if not major:
            major = [float(np.sqrt(low * high))]
        minor = [factor * 10.0 ** power for power in powers for factor in range(2, 10)
                 if low <= factor * 10.0 ** power <= high]
        getattr(axis, "set_" + direction + "scale")("log")
        getattr(axis, "set_" + direction + "lim")((low, high))
        coordinate_axis = getattr(axis, direction + "axis")
        coordinate_axis.set_major_locator(FixedLocator(major))
        coordinate_axis.set_minor_locator(FixedLocator(minor))
        coordinate_axis.set_major_formatter(LogFormatterSciNotation())

    missing_notes = []
    gate_config = report.get("config", {}).get("mms_gates", {})
    for axis, key, gate_key, label in (
            (axes[1], "relative_u_H1", "fine_relative_u_H1", "Relative displacement H1 error"),
            (axes[2], "relative_pressure_L2", "fine_relative_pressure_L2", "Relative pressure L2 error")):
        all_x, all_y = [], []
        for degree, color, marker in ((1, "#A76335", "s"), (2, "#207052", "o")):
            points = [point for point in prepared["curves"][degree]
                      if point["errors"].get(key, 0) > 0]
            if len(points) < 3:
                missing_notes.append(f"P3/P{degree}: {len(points)}/3 {key}")
            x = [point["DOF"] for point in points]
            y = [point["errors"][key] for point in points]
            axis.plot(x, y, marker=marker, color=color, linewidth=1.5, markersize=6,
                      linestyle="-" if len(points) == 3 else "none",
                      label=f"P3/P{degree} ({len(points)}/3 grids)")
            all_x.extend(x)
            all_y.extend(y)
        gate = gate_config.get(gate_key)
        if gate is not None and np.isfinite(gate) and gate > 0:
            axis.axhline(gate, color="#666666", linestyle="--", linewidth=1.0,
                         label="Original n=8 limit")
            all_y.append(gate)
        if all_x:
            log_ticks(axis, all_x, "x")
            log_ticks(axis, all_y, "y")
            axis.legend(loc="upper right")
        else:
            unavailable(axis, "Error/cost comparison: not_run")
        axis.set(xlabel="Total mixed DOF", ylabel=label)

    states = prepared["states"]
    if states:
        xy = prepared["slice"]
        triangle_indices = Triangulation(xy[:, 0], xy[:, 1]).triangles
        all_colors = np.concatenate([state["u"][:, 0] for state in states])
        color_min, color_max = float(all_colors.min()), float(all_colors.max())
        # A constant retained field needs a nonzero display range, not invented values.
        if color_min == color_max:
            display_pad = max(abs(color_min) * 0.01, np.finfo(float).eps)
            color_min, color_max = color_min - display_pad, color_max + display_pad
        norm = Normalize(color_min, color_max)
        cmap = "viridis"
        shown_coordinates = [xy + deformation_scale * state["u"][:, :2] for state in states]
        bounds = np.concatenate([xy, *shown_coordinates])
        for panel, (state, current) in enumerate(zip(states, shown_coordinates), start=3):
            axis = axes[panel]
            colors = plt.colormaps[cmap](norm(state["u"][triangle_indices, 0].mean(axis=1)))
            axis.add_collection(PolyCollection(current[triangle_indices], facecolors=colors,
                                               edgecolors="none"))
            # Outline uses the actual reference cross-section, not a result field.
            lower, upper = xy.min(axis=0), xy.max(axis=0)
            axis.plot([lower[0], upper[0], upper[0], lower[0], lower[0]],
                      [lower[1], lower[1], upper[1], upper[1], lower[1]],
                      color="#555555", linestyle="--", linewidth=0.8)
            equal_limits(axis, bounds.min(axis=0), bounds.max(axis=0))
            axis.set(xlabel="X / L", ylabel="Y / L")
            titles.append(f"{chr(65 + panel)}  Saved Newton iteration {state['iteration']}\n"
                          f"Residual = {state['residual']:.2e}")
        color_x = positions[5][0] + axis_width + 0.4
        color_axis = figure.add_axes([color_x / width, bottom / height, 0.16 / width,
                                      axis_height / height])
        color_bar = figure.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=color_axis)
        color_bar.set_label("Numerical u_x / L (unscaled)", fontsize=14, labelpad=8)
        color_bar.ax.tick_params(labelsize=12)
    for panel in range(3 + len(states), 6):
        unavailable(axes[panel], "Saved state unavailable\nnot_run / not retained")
        titles.append(f"{chr(65 + panel)}  No synthesized state")

    for axis, title in zip(axes, titles):
        style_module.apply_axes_style(axis, style=style)
        style_module.add_top_information(axis, title, style=style)
    # apply_axes_style enables minor ticks; retain bounded log locators explicitly.
    for axis in axes[1:3]:
        if axis.get_xscale() == "log":
            x_values = [point["DOF"] for points in prepared["curves"].values() for point in points]
            log_ticks(axis, x_values, "x")
            key = "relative_u_H1" if axis is axes[1] else "relative_pressure_L2"
            y_values = [point["errors"][key] for points in prepared["curves"].values()
                        for point in points if point["errors"].get(key, 0) > 0]
            gate = gate_config.get("fine_" + key)
            if gate is not None and np.isfinite(gate) and gate > 0:
                y_values.append(gate)
            log_ticks(axis, y_values, "y")
    candidate_status = report.get("convergence", {}).get("groups", {}).get(
        "candidate_p3p2", {}).get("status", "unknown")
    control_rows = sorted((row for row in report["cases"]
                           if row.get("kind") == "mms" and row.get("u_degree") == 3
                           and row.get("p_degree") == 1), key=lambda row: row["n"])
    control_status = "; ".join(f"n={row['n']}: {row.get('equilibrium', 'unknown')}"
                               for row in control_rows) or "not_run"
    footer = [
        f"Candidate kappa=100 qualification: {candidate_status}. Original ventricular qualification remains failed.",
        f"P3/P1 equilibrium / safety status: {control_status}. Missing grid points are not connected.",
        "A: actual n=2 reference mesh; red X=0 exact displacement, other faces exact reference traction; compatible body force.",
        "B-C: same manufactured load and P3 displacement; n=2, 4, 8. Mixed DOF differ. Missing/zero errors are not log-plotted.",
        f"D-F: nodes at reference Z/L=0.5; geometry x{deformation_scale:g}, colors unscaled; piecewise-linear nodal display.",
        "Saved Newton iterations are algorithm progress, NOT physiological time. 160 dpi exploratory page, not publication final.",
    ]
    for y_in, text in zip((1.85, 1.55, 1.25, 0.95, 0.65, 0.35), footer):
        figure.text(left / width, y_in / height, text, fontsize=12)
    try:
        exported = style_module.export_figure(figure, axes, output_png.with_suffix(""),
                                              style=style, overrides=overrides)
        if exported.svg.resolve() != output_svg.resolve():
            exported.svg.replace(output_svg)
        manifest = json.loads(exported.manifest.read_text(encoding="utf-8"))
        manifest["exports"]["svg"] = str(output_svg.resolve())
        manifest["evidence_selection"] = {
            "reference_case": PATCH_CASE if reference is not None else None,
            "state_case": FINE_CASE if states else None,
            "selected_saved_iterations": [state["iteration"] for state in states],
            "slice_reference_z_over_L": 0.5, "deformation_display_scale": deformation_scale,
            "field_values_scaled": False, "missing_curve_entries": missing_notes,
            "state_synthesis": False, "physiological_time": False,
        }
        exported.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
        return {"png": str(exported.png), "svg": str(output_svg), "manifest": str(exported.manifest)}
    finally:
        plt.close(figure)
