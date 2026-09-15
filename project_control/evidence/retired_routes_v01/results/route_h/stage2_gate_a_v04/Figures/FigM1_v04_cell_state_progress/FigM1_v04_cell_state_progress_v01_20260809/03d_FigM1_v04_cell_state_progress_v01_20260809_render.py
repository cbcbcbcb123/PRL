"""Render the M1 v04 accepted cell states and response trajectory."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_time_series(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("time series is empty")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        for key in rows[0]
    }


def _nearest_index(time: np.ndarray, target: float) -> int:
    return int(np.argmin(np.abs(time - target)))


def _add_cell_state(
    axis: Any,
    vertices: np.ndarray,
    faces: np.ndarray,
    displacement: np.ndarray,
    *,
    normalization: Normalize,
    cmap: Any,
    label: str,
) -> None:
    face_values = displacement[faces].mean(axis=1)
    surface = Poly3DCollection(
        vertices[faces],
        facecolors=cmap(normalization(face_values)),
        edgecolors=(0.10, 0.10, 0.10, 0.28),
        linewidths=0.38,
        antialiased=True,
        shade=False,
    )
    axis.add_collection3d(surface)
    axis.set_xlim(-0.57, 0.57)
    axis.set_ylim(-0.36, 0.36)
    axis.set_zlim(-0.34, 0.34)
    axis.set_box_aspect((1.0, 0.63, 0.60))
    axis.view_init(elev=19.0, azim=-62.0)
    axis.set_proj_type("ortho")
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_zticks([])
    axis.xaxis.set_visible(False)
    axis.yaxis.set_visible(False)
    axis.zaxis.set_visible(False)
    axis.set_axis_off()
    axis.text2D(
        0.5,
        1.02,
        label,
        transform=axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=18,
        color="#111111",
    )


def render(revision_dir: Path, prefix: str) -> dict[str, float | str]:
    revision_dir = revision_dir.resolve()
    vertices = np.load(
        revision_dir / f"01_{prefix}_data.npy",
        allow_pickle=False,
    )
    faces = np.load(
        revision_dir / f"01a_{prefix}_data_faces.npy",
        allow_pickle=False,
    )
    series = _read_time_series(
        revision_dir / f"01d_{prefix}_data_time_series.csv"
    )
    failure = json.loads(
        (revision_dir / f"01b_{prefix}_data_failure.json").read_text(
            encoding="utf-8"
        )
    )
    if vertices.shape[0] != series["time"].size:
        raise ValueError("vertices and time-series nodes do not match")

    style_module = _load_module(
        revision_dir / f"03c_{prefix}_style.py",
        f"{prefix}_style",
    )
    style = style_module.StyleSpec(
        axis_box_size_in=(10.0, 5.0),
        legend_font_size=22.0,
    )
    overrides = [
        style_module.StyleOverride(
            field="legend_font_size",
            reason=(
                "Four long mechanical-series labels are placed in a dedicated "
                "right margin so the response curves remain unobscured."
            ),
        )
    ]

    time = series["time"]
    snapshot_targets = (0.0, 2.0, 3.0, float(time[-1]))
    snapshot_indices = [_nearest_index(time, target) for target in snapshot_targets]
    snapshot_labels = (
        "Reference\nt = 0.00",
        "Peak activation\nt = 2.00",
        "Peak shortening\nt = 3.00",
        f"Last accepted\nt = {time[-1]:.2f}",
    )
    reference_vertices = vertices[0]
    reference_center = reference_vertices.mean(axis=0)
    fiber_length0 = float(series["fiber_length"][0])
    displacement = (
        np.linalg.norm(vertices[snapshot_indices] - reference_vertices, axis=2)
        / fiber_length0
        * 100.0
    )
    normalization = Normalize(vmin=0.0, vmax=float(np.max(displacement)))
    cmap = mpl.colormaps["viridis"]

    canvas_width = 18.0
    canvas_height = 13.0
    figure = plt.figure(
        figsize=(canvas_width, canvas_height),
        facecolor="white",
    )
    snapshot_lefts = (1.12, 4.48, 7.84, 11.20)
    snapshot_axes = []
    for left, index, values, label in zip(
        snapshot_lefts,
        snapshot_indices,
        displacement,
        snapshot_labels,
        strict=True,
    ):
        axis_3d = figure.add_axes(
            [left / canvas_width, 8.35 / canvas_height, 2.82 / canvas_width, 3.0 / canvas_height],
            projection="3d",
        )
        _add_cell_state(
            axis_3d,
            vertices[index] - reference_center,
            faces,
            values,
            normalization=normalization,
            cmap=cmap,
            label=label,
        )
        snapshot_axes.append(axis_3d)

    color_axis = figure.add_axes(
        [15.05 / canvas_width, 8.67 / canvas_height, 0.24 / canvas_width, 2.35 / canvas_height]
    )
    colorbar = figure.colorbar(
        mpl.cm.ScalarMappable(norm=normalization, cmap=cmap),
        cax=color_axis,
    )
    colorbar.set_label("Vertex displacement / $L_0$ (%)", fontsize=17, labelpad=10)
    colorbar.ax.tick_params(labelsize=15, width=1.3, length=5)
    colorbar.outline.set_linewidth(1.4)

    response_axis = figure.add_axes(
        [3.00 / canvas_width, 2.10 / canvas_height, 10.0 / canvas_width, 5.0 / canvas_height]
    )
    response_axis.plot(
        time,
        100.0 * series["alpha"],
        color="#303030",
        linewidth=3.0,
        linestyle=(0, (7, 4)),
        label="Activation",
    )
    response_axis.plot(
        time,
        100.0 * series["axial_shortening"],
        color="#C33C54",
        linewidth=3.0,
        label="Axial shortening",
    )
    response_axis.plot(
        time,
        100.0 * series["transverse_scale_change_1"],
        color="#238B8D",
        linewidth=3.0,
        label="Transverse scale 1",
    )
    response_axis.plot(
        time,
        100.0 * series["transverse_scale_change_2"],
        color="#3B6FB6",
        linewidth=3.0,
        label="Transverse scale 2",
    )
    failure_time = float(failure["time"])
    response_axis.axvspan(
        failure_time,
        5.0,
        facecolor="#ECECEC",
        alpha=0.90,
        edgecolor="none",
        zorder=0,
    )
    response_axis.axvline(
        failure_time,
        color="#B2182B",
        linewidth=2.2,
        linestyle=(0, (5, 3)),
        zorder=2,
    )
    response_axis.text(
        4.42,
        10.7,
        "not accepted",
        ha="center",
        va="top",
        color="#777777",
        fontsize=18,
    )
    response_axis.set_xlim(0.0, 5.0)
    response_axis.set_ylim(-1.5, 11.5)
    response_axis.set_xlabel("Simulation time")
    response_axis.set_ylabel("Activation or deformation (%)")
    response_axis.xaxis.set_major_locator(MultipleLocator(1.0))
    response_axis.xaxis.set_minor_locator(AutoMinorLocator(2))
    response_axis.yaxis.set_major_locator(MultipleLocator(2.0))
    response_axis.yaxis.set_minor_locator(AutoMinorLocator(2))
    handles, labels = response_axis.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="center left",
        bbox_to_anchor=(13.45 / canvas_width, 4.45 / canvas_height),
        frameon=False,
        ncols=1,
    )
    style_module.apply_axes_style(response_axis, style=style)
    style_module.add_top_information(
        response_axis,
        (
            f"valid t ≤ {time[-1]:.2f}   |   "
            f"max |ΔV|/V₀ = {100.0 * np.max(np.abs(series['volume_error'])):.4f}%   |   "
            f"r_fail = {float(failure['projected_residual']):.2e}"
        ),
        style=style,
    )

    figure.text(0.032, 0.950, "A", fontsize=32, ha="left", va="top")
    figure.text(0.032, 0.555, "B", fontsize=32, ha="left", va="top")

    output_prefix = revision_dir / f"04_{prefix}"
    exports = style_module.export_figure(
        figure,
        response_axis,
        output_prefix,
        style=style,
        overrides=overrides,
    )
    required_svg = revision_dir / f"05_{prefix}.svg"
    shutil.copyfile(exports.svg, required_svg)
    plt.close(figure)

    return {
        "last_accepted_time": float(time[-1]),
        "failure_time": failure_time,
        "failure_residual": float(failure["projected_residual"]),
        "maximum_absolute_volume_error_percent": float(
            100.0 * np.max(np.abs(series["volume_error"]))
        ),
        "peak_axial_shortening_percent": float(
            100.0 * np.max(series["axial_shortening"])
        ),
        "png": str(exports.png),
        "svg": str(required_svg),
        "style_manifest": str(exports.manifest),
    }
