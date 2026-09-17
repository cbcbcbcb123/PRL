"""Render true solver states for the 5x5 myocardial crowded-box pilot."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy.spatial import ConvexHull


ROW_COLORS = ["#2474A6", "#319A83", "#79A946", "#D99A31", "#C95855"]
BOX_COLOR = "#79B7C8"
INK = "#263238"
GRID = "#DCE3E6"
GATE = "#A33A36"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": ["Arial", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 8.5,
            "axes.linewidth": 0.8,
            "axes.edgecolor": INK,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def _snapshot_cells(
    node_rows: list[dict[str, str]],
    face_rows: list[dict[str, str]],
    snapshot: int,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for cell_id in range(25):
        selected_nodes = sorted(
            (
                row
                for row in node_rows
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        selected_faces = sorted(
            (
                row
                for row in face_rows
                if int(row["snapshot_index"]) == snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["face_local_id"]),
        )
        points = np.asarray(
            [[float(row[axis]) for axis in ("x", "y", "z")] for row in selected_nodes],
            dtype=float,
        )
        triangles = np.asarray(
            [[int(row[key]) for key in ("n1", "n2", "n3")] for row in selected_faces],
            dtype=int,
        )
        result.append(
            {
                "cell_id": cell_id,
                "row": int(selected_nodes[0]["row"]),
                "column": int(selected_nodes[0]["column"]),
                "points": points,
                "triangles": triangles,
                "rows": selected_nodes,
            }
        )
    return result


def _state_bounds(state: dict[str, str]) -> np.ndarray:
    return np.asarray(
        [float(state[name]) for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")],
        dtype=float,
    )


def _box_faces(bounds: np.ndarray) -> list[list[list[float]]]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    corners = np.asarray(
        [
            [xmin, ymin, zmin],
            [xmax, ymin, zmin],
            [xmax, ymax, zmin],
            [xmin, ymax, zmin],
            [xmin, ymin, zmax],
            [xmax, ymin, zmax],
            [xmax, ymax, zmax],
            [xmin, ymax, zmax],
        ]
    )
    return [
        corners[[0, 1, 2, 3]].tolist(),
        corners[[4, 5, 6, 7]].tolist(),
        corners[[0, 1, 5, 4]].tolist(),
        corners[[1, 2, 6, 5]].tolist(),
        corners[[2, 3, 7, 6]].tolist(),
        corners[[3, 0, 4, 7]].tolist(),
    ]


def _draw_box_3d(axis, bounds: np.ndarray) -> None:
    collection = Poly3DCollection(
        _box_faces(bounds),
        facecolor=(*matplotlib.colors.to_rgb(BOX_COLOR), 0.035),
        edgecolor=(*matplotlib.colors.to_rgb(BOX_COLOR), 0.55),
        linewidth=0.65,
    )
    axis.add_collection3d(collection)


def _format_3d(axis, bounds: np.ndarray, title: str) -> None:
    axis.set_xlim(bounds[0], bounds[1])
    axis.set_ylim(bounds[2], bounds[3])
    axis.set_zlim(bounds[4], bounds[5])
    span = np.asarray(
        [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
    )
    axis.set_box_aspect(span)
    axis.view_init(elev=28, azim=-62)
    axis.set_xlabel("long-axis x")
    axis.set_ylabel("sheet y")
    axis.set_zlabel("thin-layer z")
    axis.set_title(title, loc="left", fontweight="bold")
    axis.grid(False)
    for pane in (axis.xaxis, axis.yaxis, axis.zaxis):
        pane.pane.fill = False
        pane.pane.set_edgecolor(GRID)


def _draw_structure_3d(axis, cells: list[dict[str, object]], bounds: np.ndarray, title: str) -> None:
    _draw_box_3d(axis, bounds)
    for cell in cells:
        points = cell["points"]
        triangles = cell["triangles"]
        row = int(cell["row"])
        collection = Poly3DCollection(
            points[triangles],
            facecolor=ROW_COLORS[row],
            edgecolor=(0.10, 0.13, 0.15, 0.30),
            linewidth=0.16,
            alpha=0.87,
        )
        axis.add_collection3d(collection)
    _format_3d(axis, bounds, title)


def _draw_top(axis, cells: list[dict[str, object]], bounds: np.ndarray, title: str) -> None:
    axis.add_patch(
        plt.Rectangle(
            (bounds[0], bounds[2]),
            bounds[1] - bounds[0],
            bounds[3] - bounds[2],
            facecolor=(*matplotlib.colors.to_rgb(BOX_COLOR), 0.045),
            edgecolor=BOX_COLOR,
            linewidth=1.0,
        )
    )
    for cell in cells:
        points = cell["points"]
        hull = ConvexHull(points[:, :2])
        polygon = points[hull.vertices, :2]
        axis.fill(
            polygon[:, 0],
            polygon[:, 1],
            facecolor=ROW_COLORS[int(cell["row"])],
            edgecolor=INK,
            linewidth=0.55,
            alpha=0.82,
        )
        center = points[:, :2].mean(axis=0)
        axis.text(
            center[0], center[1], str(int(cell["cell_id"]) + 1),
            ha="center", va="center", fontsize=5.5, color="white", fontweight="bold"
        )
    axis.set_xlim(bounds[0], bounds[1])
    axis.set_ylim(bounds[2], bounds[3])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("long-axis x")
    axis.set_ylabel("sheet y")
    axis.set_title(title, loc="left", fontweight="bold")
    axis.spines[["top", "right"]].set_visible(False)


def _field_normalizer(values: np.ndarray, signed: bool) -> colors.Normalize:
    minimum = float(np.nanmin(values))
    maximum = float(np.nanmax(values))
    if np.isclose(minimum, maximum):
        delta = max(abs(minimum) * 0.05, 1.0e-12)
        return colors.Normalize(minimum - delta, maximum + delta)
    if signed and minimum < 0.0 < maximum:
        extent = max(abs(minimum), abs(maximum))
        return colors.TwoSlopeNorm(vmin=-extent, vcenter=0.0, vmax=extent)
    if minimum >= 0.0:
        return colors.PowerNorm(gamma=0.55, vmin=minimum, vmax=maximum)
    return colors.Normalize(vmin=minimum, vmax=maximum)


def _draw_top_field(
    axis,
    cells: list[dict[str, object]],
    bounds: np.ndarray,
    field: str,
    title: str,
    cmap: str,
    signed: bool,
) -> matplotlib.cm.ScalarMappable:
    all_values = np.concatenate(
        [np.asarray([float(row[field]) for row in cell["rows"]]) for cell in cells]
    )
    normalizer = _field_normalizer(all_values, signed)
    color_map = plt.get_cmap(cmap)
    polygons: list[np.ndarray] = []
    face_values: list[float] = []
    for cell in cells:
        points = cell["points"]
        triangles = cell["triangles"]
        nodal = np.asarray([float(row[field]) for row in cell["rows"]])
        polygons.extend(points[triangles][:, :, :2])
        face_values.extend(nodal[triangles].mean(axis=1))
    collection = PolyCollection(
        polygons,
        array=np.asarray(face_values),
        cmap=color_map,
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
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_title(title, loc="left", fontweight="bold")
    axis.spines[["top", "right"]].set_visible(False)
    scalar = matplotlib.cm.ScalarMappable(norm=normalizer, cmap=color_map)
    scalar.set_array([])
    return scalar


def _save_dual(figure: plt.Figure, base: Path) -> list[str]:
    png = base.with_suffix(".png")
    svg = base.with_suffix(".svg")
    figure.savefig(png, dpi=220)
    figure.savefig(svg)
    return [png.name, svg.name]


def render_myocardial_crowded_box(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    raw = result / "raw"
    node_rows = _read_csv(raw / "nodes.csv")
    face_rows = _read_csv(raw / "faces.csv")
    state_rows = sorted(
        _read_csv(raw / "state_metrics.csv"),
        key=lambda row: int(row["snapshot_index"]),
    )
    cell_rows = _read_csv(raw / "cell_metrics.csv")
    heterogeneity = _read_csv(result / "heterogeneity.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in node_rows})
    if len(snapshots) < 2:
        return {"status": "failed", "reason": "fewer than two retained solver states"}
    figures = result / "figures"
    figures.mkdir()
    _style()

    selected = [snapshots[0], snapshots[len(snapshots) // 2], snapshots[-1]]
    selected_cells = {
        snapshot: _snapshot_cells(node_rows, face_rows, snapshot) for snapshot in selected
    }
    selected_states = {
        int(row["snapshot_index"]): row
        for row in state_rows
        if int(row["snapshot_index"]) in selected
    }

    structure_base = figures / "model_structure_transparent_box"
    figure = plt.figure(figsize=(15.2, 9.6))
    for panel, (snapshot, label) in enumerate(
        zip(selected, ("a  Initial disjoint grid", "b  End of box loading", "c  Final retained state"), strict=True),
        start=1,
    ):
        axis = figure.add_subplot(2, 2, panel, projection="3d")
        state = selected_states[snapshot]
        _draw_structure_3d(
            axis,
            selected_cells[snapshot],
            _state_bounds(state),
            f"{label} | solver state {snapshot}",
        )
    top_axis = figure.add_subplot(2, 2, 4)
    final_snapshot = selected[-1]
    _draw_top(
        top_axis,
        selected_cells[final_snapshot],
        _state_bounds(selected_states[final_snapshot]),
        "d  Final top view | labels are cell IDs",
    )
    figure.suptitle(
        "5×5 cardiomyocyte crowding in a thin transparent rigid box\n"
        "true solver meshes; x/y box dimensions shrink 5%, z height is fixed",
        fontsize=12,
        fontweight="bold",
        y=0.985,
    )
    figure.subplots_adjust(left=0.045, right=0.975, bottom=0.06, top=0.91, wspace=0.16, hspace=0.22)
    structure_files = _save_dual(figure, structure_base)
    plt.close(figure)

    final_cells = selected_cells[final_snapshot]
    final_bounds = _state_bounds(selected_states[final_snapshot])
    fields_base = figures / "final_mechanical_fields"
    figure, axes = plt.subplots(2, 2, figsize=(13.0, 9.2))
    field_specs = [
        ("curvature", "a  Surface curvature", "coolwarm", True),
        ("internal_pressure", "b  Intracellular pressure", "coolwarm", True),
        ("contact_traction", "c  Cell-cell contact traction", "magma", False),
        ("wall_traction", "d  Box-wall traction", "viridis", False),
    ]
    for axis, specification in zip(axes.flat, field_specs, strict=True):
        scalar = _draw_top_field(axis, final_cells, final_bounds, *specification)
        figure.colorbar(scalar, ax=axis, fraction=0.030, pad=0.018)
    figure.suptitle(
        "Final retained mechanical fields on the true triangulated surfaces",
        fontsize=12,
        fontweight="bold",
        y=0.975,
    )
    figure.subplots_adjust(left=0.07, right=0.95, bottom=0.07, top=0.91, wspace=0.22, hspace=0.28)
    field_files = _save_dual(figure, fields_base)
    plt.close(figure)

    progress = np.asarray([float(row["coordinate"]) for row in state_rows])
    force = np.asarray([float(row["max_free_force"]) for row in state_rows])
    volume = 100.0 * np.asarray(
        [float(row["max_volume_relative_error"]) for row in state_rows]
    )
    angle = np.asarray([float(row["min_triangle_angle_deg"]) for row in state_rows])
    occupancy = np.asarray([float(row["projected_occupancy"]) for row in state_rows])
    pairs = np.asarray([int(row["contact_active_cell_pairs"]) for row in state_rows])
    wall = np.asarray([float(row["total_wall_reaction"]) for row in state_rows])
    separation = np.asarray(
        [float(row["min_intercell_separation"]) for row in state_rows]
    )
    progress_base = figures / "crowding_numerical_progress"
    figure, axes = plt.subplots(3, 2, figsize=(10.5, 9.2))
    axes[0, 0].semilogy(progress, np.maximum(force, 1.0e-16), "o-", color="#2474A6", lw=1.45, ms=4)
    axes[0, 0].axhline(1.0e-3, color=GATE, ls="--", lw=1.0, label="equilibrium criterion")
    axes[0, 0].legend(frameon=False, fontsize=7.5)
    axes[0, 0].set_ylabel("max nodal force")
    axes[0, 1].plot(progress, occupancy, "o-", color="#319A83", lw=1.45, ms=4)
    axes[0, 1].set_ylabel("projected occupancy")
    axes[1, 0].plot(progress, volume, "o-", color="#D9882E", lw=1.45, ms=4)
    axes[1, 0].axhline(2.0, color=GATE, ls="--", lw=1.0)
    axes[1, 0].set_ylabel("max volume error (%)")
    axes[1, 1].plot(progress, angle, "o-", color="#79A946", lw=1.45, ms=4)
    axes[1, 1].axhline(15.0, color=GATE, ls="--", lw=1.0)
    axes[1, 1].set_ylabel("minimum angle (deg)")
    axes[2, 0].plot(progress, pairs, "o-", color="#8E5BA6", lw=1.45, ms=4)
    axes[2, 0].set_ylabel("active cell pairs")
    wall_axis = axes[2, 1]
    wall_axis.plot(progress, wall, "o-", color="#C95855", lw=1.45, ms=4, label="wall reaction")
    wall_axis.set_ylabel("wall reaction", color="#C95855")
    wall_axis.tick_params(axis="y", labelcolor="#C95855")
    separation_axis = wall_axis.twinx()
    separation_axis.plot(progress, separation, "s--", color="#4C6670", lw=1.1, ms=3.5, label="minimum gap")
    separation_axis.set_ylabel("minimum cell gap", color="#4C6670")
    separation_axis.tick_params(axis="y", labelcolor="#4C6670")
    panel_labels = ("a", "b", "c", "d", "e", "f")
    for label, axis in zip(panel_labels, axes.flat, strict=True):
        axis.set_xlabel("algorithmic loading / relaxation coordinate")
        axis.set_title(label, loc="left", fontweight="bold")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=GRID, lw=0.55)
    figure.suptitle(
        "Crowding progress and numerical safety indicators",
        fontsize=12,
        fontweight="bold",
        y=0.98,
    )
    figure.subplots_adjust(left=0.09, right=0.89, bottom=0.07, top=0.92, wspace=0.34, hspace=0.42)
    progress_files = _save_dual(figure, progress_base)
    plt.close(figure)

    final_cell_rows = sorted(
        (row for row in cell_rows if int(row["snapshot_index"]) == final_snapshot),
        key=lambda row: int(row["cell_id"]),
    )
    length_scale = np.asarray([float(row["length_scale"]) for row in heterogeneity]).reshape(5, 5)
    rotation = np.asarray([float(row["rotation_deg"]) for row in heterogeneity]).reshape(5, 5)
    prestress = np.asarray([float(row["prestress_factor"]) for row in heterogeneity]).reshape(5, 5)
    final_pressure = np.asarray([float(row["pressure"]) for row in final_cell_rows]).reshape(5, 5)
    heterogeneity_base = figures / "cellwise_heterogeneity_and_response"
    figure, axes = plt.subplots(2, 2, figsize=(8.6, 7.5))
    specifications = [
        (length_scale, "a  Initial length factor", "RdBu_r"),
        (rotation, "b  Initial long-axis angle (deg)", "coolwarm"),
        (prestress, "c  Cytoskeletal prestress factor", "RdBu_r"),
        (final_pressure, "d  Final intracellular pressure", "coolwarm"),
    ]
    for axis, (values, title, cmap) in zip(axes.flat, specifications, strict=True):
        image = axis.imshow(values, cmap=cmap, aspect="equal")
        axis.set_xticks(range(5), [f"C{column + 1}" for column in range(5)])
        axis.set_yticks(range(5), [f"R{row + 1}" for row in range(5)])
        axis.set_title(title, loc="left", fontweight="bold")
        for row in range(5):
            for column in range(5):
                axis.text(column, row, f"{values[row, column]:.2f}", ha="center", va="center", fontsize=6.5)
        figure.colorbar(image, ax=axis, fraction=0.043, pad=0.025)
    figure.suptitle(
        "Frozen cell-to-cell differences and one final mechanical response",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    figure.subplots_adjust(left=0.08, right=0.94, bottom=0.07, top=0.91, wspace=0.27, hspace=0.30)
    heterogeneity_files = _save_dual(figure, heterogeneity_base)
    plt.close(figure)

    relative_files = [
        *(f"figures/{name}" for name in structure_files),
        *(f"figures/{name}" for name in field_files),
        *(f"figures/{name}" for name in progress_files),
        *(f"figures/{name}" for name in heterogeneity_files),
    ]
    manifest = {
        "status": "passed",
        "figures": relative_files,
        "snapshot_indices": snapshots,
        "structure_snapshots": selected,
        "field_snapshot": final_snapshot,
        "field_source": "raw/nodes.csv on true solver meshes",
        "box_source": "raw/state_metrics.csv analytic six-plane bounds",
        "time_semantics": "algorithmic loading and relaxation, not physiological time",
        "style": "CB unified quantitative style v01; 3D panels use explicit scientific-layout exception",
        "svg_note": "editable vector companions accompany every PNG",
    }
    (result / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest

