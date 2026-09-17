"""Render true solver states and matched cellwise responses for the target pair."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.ticker import MaxNLocator
import numpy as np

from .cb_plot_unified_style import (
    DEFAULT_STYLE,
    add_top_information,
    create_figure_with_axis_box,
    export_figure,
)
from .myocardial_crowded_box import (
    BOX_COLOR,
    GRID,
    INK,
    _draw_structure_3d,
    _field_normalizer,
    _read_csv,
    _snapshot_cells,
    _state_bounds,
    _style,
)


CONDITIONS = ("UNIFORM_TARGETS", "HETEROGENEOUS_TARGETS")
CONDITION_LABELS = {
    "UNIFORM_TARGETS": "Uniform targets",
    "HETEROGENEOUS_TARGETS": "Heterogeneous targets",
}


def _save_scientific_layout(
    figure: plt.Figure, base: Path, *, reason: str
) -> list[Path]:
    png = base.with_suffix(".png")
    svg = base.with_suffix(".svg")
    manifest = base.with_name(f"{base.name}_style_manifest.json")
    figure.savefig(png, dpi=600, facecolor="white", edgecolor="white")
    figure.savefig(svg, format="svg", facecolor="white", edgecolor="white")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "layout": "scientific_mesh_or_multipanel_exception",
                "reason": reason,
                "exports": {
                    "png": str(png.resolve()),
                    "svg": str(svg.resolve()),
                    "png_dpi": 600,
                    "svg_fonttype": matplotlib.rcParams["svg.fonttype"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return [png, svg, manifest]


def _draw_shared_field(
    axis,
    cells: list[dict[str, object]],
    bounds: np.ndarray,
    field: str,
    title: str,
    *,
    normalizer,
    cmap: str,
):
    polygons: list[np.ndarray] = []
    face_values: list[float] = []
    for cell in cells:
        points = np.asarray(cell["points"])
        triangles = np.asarray(cell["triangles"])
        nodal = np.asarray([float(row[field]) for row in cell["rows"]])
        polygons.extend(points[triangles][:, :, :2])
        face_values.extend(nodal[triangles].mean(axis=1))
    collection = PolyCollection(
        polygons,
        array=np.asarray(face_values),
        cmap=plt.get_cmap(cmap),
        norm=normalizer,
        edgecolor=(0.12, 0.14, 0.16, 0.18),
        linewidth=0.10,
    )
    axis.add_collection(collection)
    axis.add_patch(
        plt.Rectangle(
            (bounds[0], bounds[2]),
            bounds[1] - bounds[0],
            bounds[3] - bounds[2],
            fill=False,
            edgecolor=BOX_COLOR,
            linewidth=0.9,
        )
    )
    axis.set_xlim(bounds[0], bounds[1])
    axis.set_ylim(bounds[2], bounds[3])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("long-axis x")
    axis.set_ylabel("sheet y")
    axis.set_title(title, loc="left", fontweight="bold")
    axis.spines[["top", "right"]].set_visible(False)
    return collection


def _final_rows(result: Path, condition: str) -> list[dict[str, str]]:
    rows = _read_csv(result / "raw" / condition / "cell_metrics.csv")
    final_snapshot = max(int(row["snapshot_index"]) for row in rows)
    return sorted(
        (row for row in rows if int(row["snapshot_index"]) == final_snapshot),
        key=lambda row: int(row["cell_id"]),
    )


def _paired_figure(
    figures: Path,
    metric: str,
    ylabel: str,
    uniform_rows: list[dict[str, str]],
    heterogeneous_rows: list[dict[str, str]],
) -> list[Path]:
    figure, axis = create_figure_with_axis_box(
        style=DEFAULT_STYLE,
        margins_in=(3.00, 0.85, 1.75, 1.20),
    )
    uniform_values = np.asarray([float(row[metric]) for row in uniform_rows])
    heterogeneous_values = np.asarray(
        [float(row[metric]) for row in heterogeneous_rows]
    )
    for uniform_value, heterogeneous_value in zip(
        uniform_values, heterogeneous_values, strict=True
    ):
        axis.plot(
            [0.0, 1.0],
            [uniform_value, heterogeneous_value],
            color="#6F7B80",
            alpha=0.24,
            linewidth=DEFAULT_STYLE.data_line_width,
            marker="o",
            markersize=7.0,
            markerfacecolor="#FFFFFF",
            markeredgecolor="#6F7B80",
        )
    axis.plot(
        [0.0, 1.0],
        [float(uniform_values.mean()), float(heterogeneous_values.mean())],
        color="#C54B45",
        linewidth=DEFAULT_STYLE.data_line_width,
        marker="D",
        markersize=10.0,
        markerfacecolor="#C54B45",
        markeredgecolor="#C54B45",
        zorder=5,
    )
    axis.set_xlim(-0.35, 1.35)
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))
    axis.set_xticks([0.0, 1.0], ["Uniform", "Heterogeneous"])
    axis.set_xlabel("Reference-target condition")
    axis.set_ylabel(ylabel)
    add_top_information(
        axis,
        "n = 25 paired cells",
        style=DEFAULT_STYLE,
    )
    paths = export_figure(
        figure,
        axis,
        figures / f"paired_final_{metric}",
        style=DEFAULT_STYLE,
    )
    plt.close(figure)
    return [paths.png, paths.svg, paths.manifest]


def render_myocardial_crowded_target_pair(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    _style()

    state_rows: dict[str, list[dict[str, str]]] = {}
    node_rows: dict[str, list[dict[str, str]]] = {}
    face_rows: dict[str, list[dict[str, str]]] = {}
    final_cells: dict[str, list[dict[str, object]]] = {}
    final_states: dict[str, dict[str, str]] = {}
    for condition in CONDITIONS:
        raw = result / "raw" / condition
        state_rows[condition] = sorted(
            _read_csv(raw / "state_metrics.csv"),
            key=lambda row: int(row["snapshot_index"]),
        )
        node_rows[condition] = _read_csv(raw / "nodes.csv")
        face_rows[condition] = _read_csv(raw / "faces.csv")
        final_snapshot = max(
            int(row["snapshot_index"]) for row in node_rows[condition]
        )
        final_cells[condition] = _snapshot_cells(
            node_rows[condition], face_rows[condition], final_snapshot
        )
        final_states[condition] = state_rows[condition][-1]

    all_paths: list[Path] = []
    structure_figure = plt.figure(figsize=(13.2, 4.8))
    initial_cells = _snapshot_cells(
        node_rows["UNIFORM_TARGETS"], face_rows["UNIFORM_TARGETS"], 0
    )
    structure_specs = [
        (
            initial_cells,
            _state_bounds(state_rows["UNIFORM_TARGETS"][0]),
            "a  Shared initial high-crowding grid | solver state 0",
        ),
        (
            final_cells["UNIFORM_TARGETS"],
            _state_bounds(final_states["UNIFORM_TARGETS"]),
            "b  Final | identical V0 and A0 for all cells",
        ),
        (
            final_cells["HETEROGENEOUS_TARGETS"],
            _state_bounds(final_states["HETEROGENEOUS_TARGETS"]),
            "c  Final | cellwise V0 and A0 around same means",
        ),
    ]
    for panel, (cells, bounds, title) in enumerate(structure_specs, start=1):
        axis = structure_figure.add_subplot(1, 3, panel, projection="3d")
        _draw_structure_3d(axis, cells, bounds, title)
    structure_figure.suptitle(
        "Matched 5×5 cardiomyocyte crowding comparison in the same transparent thin box",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    structure_figure.subplots_adjust(
        left=0.025, right=0.985, bottom=0.06, top=0.88, wspace=0.12
    )
    all_paths.extend(
        _save_scientific_layout(
            structure_figure,
            figures / "model_structure_target_pair",
            reason="True 3D triangulated surfaces and transparent box require a three-panel spatial layout.",
        )
    )
    plt.close(structure_figure)

    target_rows = {
        condition: _read_csv(result / "targets" / f"{condition}.csv")
        for condition in CONDITIONS
    }
    target_figure, target_axes = plt.subplots(2, 2, figsize=(8.2, 7.0))
    target_specs = []
    for condition in CONDITIONS:
        rows = target_rows[condition]
        target_specs.extend(
            [
                (
                    np.asarray([float(row["volume_factor"]) for row in rows]).reshape(5, 5),
                    f"{CONDITION_LABELS[condition]} | V₀ / mean V₀",
                ),
                (
                    np.asarray([float(row["area_factor"]) for row in rows]).reshape(5, 5),
                    f"{CONDITION_LABELS[condition]} | A₀ / mean A₀",
                ),
            ]
        )
    for axis, (values, title) in zip(target_axes.flat, target_specs, strict=True):
        image = axis.imshow(values, cmap="RdBu_r", vmin=0.94, vmax=1.06)
        axis.set_xticks(range(5), [f"C{index + 1}" for index in range(5)])
        axis.set_yticks(range(5), [f"R{index + 1}" for index in range(5)])
        axis.set_title(title, loc="left", fontweight="bold")
        for row in range(5):
            for column in range(5):
                axis.text(
                    column,
                    row,
                    f"{values[row, column]:.3f}",
                    ha="center",
                    va="center",
                    fontsize=6.0,
                )
        target_figure.colorbar(image, ax=axis, fraction=0.043, pad=0.025)
    target_figure.suptitle(
        "Frozen reference targets: equal population means, different cellwise distributions",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    target_figure.subplots_adjust(
        left=0.08, right=0.94, bottom=0.07, top=0.90, wspace=0.30, hspace=0.33
    )
    all_paths.extend(
        _save_scientific_layout(
            target_figure,
            figures / "reference_target_maps",
            reason="The 5x5 spatial input maps are discrete scientific matrices rather than standalone quantitative axes.",
        )
    )
    plt.close(target_figure)

    combined_pressure = np.concatenate(
        [
            np.asarray(
                [float(row["internal_pressure"]) for cell in final_cells[condition] for row in cell["rows"]]
            )
            for condition in CONDITIONS
        ]
    )
    combined_contact = np.concatenate(
        [
            np.asarray(
                [float(row["contact_traction"]) for cell in final_cells[condition] for row in cell["rows"]]
            )
            for condition in CONDITIONS
        ]
    )
    field_figure, field_axes = plt.subplots(2, 2, figsize=(9.2, 6.8))
    pressure_norm = _field_normalizer(combined_pressure, signed=True)
    contact_norm = _field_normalizer(combined_contact, signed=False)
    for column, condition in enumerate(CONDITIONS):
        pressure_collection = _draw_shared_field(
            field_axes[0, column],
            final_cells[condition],
            _state_bounds(final_states[condition]),
            "internal_pressure",
            f"{chr(97 + column)}  {CONDITION_LABELS[condition]} | pressure",
            normalizer=pressure_norm,
            cmap="coolwarm",
        )
        contact_collection = _draw_shared_field(
            field_axes[1, column],
            final_cells[condition],
            _state_bounds(final_states[condition]),
            "contact_traction",
            f"{chr(99 + column)}  {CONDITION_LABELS[condition]} | contact traction",
            normalizer=contact_norm,
            cmap="magma",
        )
        field_figure.colorbar(
            pressure_collection, ax=field_axes[0, column], fraction=0.034, pad=0.018
        )
        field_figure.colorbar(
            contact_collection, ax=field_axes[1, column], fraction=0.034, pad=0.018
        )
    field_figure.suptitle(
        "Final true-mesh mechanical fields with shared color scales within each row",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    field_figure.subplots_adjust(
        left=0.07, right=0.94, bottom=0.07, top=0.90, wspace=0.25, hspace=0.32
    )
    all_paths.extend(
        _save_scientific_layout(
            field_figure,
            figures / "final_pressure_contact_fields",
            reason="True surface fields require equal-aspect spatial panels and shared scientific colorbars.",
        )
    )
    plt.close(field_figure)

    progress_figure, progress_axes = plt.subplots(2, 2, figsize=(8.8, 6.8))
    progress_specs = (
        ("max_free_force", "max nodal force", True),
        ("projected_occupancy", "projected occupancy", False),
        ("contact_active_cell_pairs", "active cell pairs", False),
        ("total_wall_reaction", "total wall reaction", False),
    )
    colors = {"UNIFORM_TARGETS": "#2474A6", "HETEROGENEOUS_TARGETS": "#C95855"}
    for axis, (field, ylabel, logarithmic) in zip(
        progress_axes.flat, progress_specs, strict=True
    ):
        for condition in CONDITIONS:
            coordinates = np.asarray(
                [float(row["coordinate"]) for row in state_rows[condition]]
            )
            values = np.asarray(
                [float(row[field]) for row in state_rows[condition]]
            )
            if logarithmic:
                axis.semilogy(
                    coordinates,
                    np.maximum(values, 1.0e-16),
                    "o-",
                    color=colors[condition],
                    lw=1.35,
                    ms=3.8,
                    label=CONDITION_LABELS[condition],
                )
            else:
                axis.plot(
                    coordinates,
                    values,
                    "o-",
                    color=colors[condition],
                    lw=1.35,
                    ms=3.8,
                    label=CONDITION_LABELS[condition],
                )
        axis.set_xlabel("algorithmic loading / relaxation coordinate")
        axis.set_ylabel(ylabel)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=GRID, lw=0.55)
    progress_axes[0, 0].axhline(1.0e-3, color="#8F2F2B", ls="--", lw=1.0)
    progress_axes[0, 0].legend(frameon=False, fontsize=7.0)
    progress_figure.suptitle(
        "Matched numerical progress; coordinate is not physiological time",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    progress_figure.subplots_adjust(
        left=0.10, right=0.96, bottom=0.09, top=0.90, wspace=0.30, hspace=0.35
    )
    all_paths.extend(
        _save_scientific_layout(
            progress_figure,
            figures / "paired_algorithmic_progress",
            reason="Four coupled solver diagnostics require a compact multipanel engineering view.",
        )
    )
    plt.close(progress_figure)

    uniform_final = _final_rows(result, "UNIFORM_TARGETS")
    heterogeneous_final = _final_rows(result, "HETEROGENEOUS_TARGETS")
    paired_specs = (
        ("pressure", "Final intracellular pressure"),
        ("volume", "Final cell volume"),
        ("x_span", "Final long-axis span"),
        ("mean_contact_traction", "Final mean contact traction"),
    )
    quantitative_manifests: list[str] = []
    for metric, ylabel in paired_specs:
        exported = _paired_figure(
            figures, metric, ylabel, uniform_final, heterogeneous_final
        )
        all_paths.extend(exported)
        quantitative_manifests.append(exported[-1].name)

    manifest = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-TARGET-PAIR-A",
        "status": "passed",
        "source": "two retained nine-state solver sequences",
        "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physiological_time",
        "files": [str(path.relative_to(result).as_posix()) for path in all_paths],
        "quantitative_style_manifests": quantitative_manifests,
        "spatial_layout_exceptions": [
            "model_structure_target_pair",
            "reference_target_maps",
            "final_pressure_contact_fields",
            "paired_algorithmic_progress",
        ],
    }
    (figures / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
