"""Render true solver states for the heterogeneous myocardial-row equilibrium."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


CELL_COLORS = ["#2878B5", "#5BA3A3", "#67A95B", "#E6A23C", "#D95F59"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def _snapshot_arrays(
    node_rows: list[dict[str, str]], face_rows: list[dict[str, str]], snapshot: int
) -> list[dict[str, object]]:
    result = []
    for cell_id in range(5):
        selected_nodes = sorted(
            (
                row
                for row in node_rows
                if int(row["snapshot_index"]) == snapshot and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        selected_faces = sorted(
            (
                row
                for row in face_rows
                if int(row["snapshot_index"]) == snapshot and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["face_local_id"]),
        )
        points = np.asarray(
            [[float(row[axis]) for axis in ("x", "y", "z")] for row in selected_nodes], dtype=float
        )
        triangles = np.asarray(
            [[int(row[key]) for key in ("n1", "n2", "n3")] for row in selected_faces], dtype=int
        )
        result.append({"points": points, "triangles": triangles, "rows": selected_nodes})
    return result


def _limits(cells: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray]:
    points = np.concatenate([cell["points"] for cell in cells])
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    padding = np.maximum((upper - lower) * np.array([0.025, 0.08, 0.08]), 0.05)
    return lower - padding, upper + padding


def _format_3d(ax, cells: list[dict[str, object]], title: str) -> None:
    lower, upper = _limits(cells)
    ax.set_xlim(lower[0], upper[0])
    ax.set_ylim(lower[1], upper[1])
    ax.set_zlim(lower[2], upper[2])
    span = upper - lower
    ax.set_box_aspect((span[0], span[1], span[2]))
    ax.view_init(elev=24, azim=-67)
    ax.set_xlabel("long axis")
    ax.set_ylabel("transverse")
    ax.set_zlabel("thickness")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(False)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.fill = False
        axis.pane.set_edgecolor("#D5DADF")


def _draw_structure(ax, cells: list[dict[str, object]], title: str) -> None:
    for cell_id, cell in enumerate(cells):
        points = cell["points"]
        triangles = cell["triangles"]
        collection = Poly3DCollection(
            points[triangles],
            facecolor=CELL_COLORS[cell_id],
            edgecolor=(0.12, 0.15, 0.18, 0.32),
            linewidth=0.22,
            alpha=0.90,
        )
        ax.add_collection3d(collection)
        center = points.mean(axis=0)
        ax.text(center[0], center[1], points[:, 2].max() + 0.25, f"C{cell_id + 1}", ha="center", fontsize=8)

    for interface in range(4):
        first = cells[interface]["points"]
        second = cells[interface + 1]["points"]
        right_ids = np.argsort(first[:, 0])[-7:]
        available = list(np.argsort(second[:, 0])[:7])
        for first_id in right_ids:
            second_id = min(
                available,
                key=lambda candidate: float(np.linalg.norm(first[first_id, 1:] - second[candidate, 1:])),
            )
            available.remove(second_id)
            segment = np.vstack((first[first_id], second[second_id]))
            ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color="#30343B", lw=0.65, alpha=0.8)

    fixed_points = []
    for cell in cells:
        for point, row in zip(cell["points"], cell["rows"], strict=True):
            if int(row["fixed"]) == 1:
                fixed_points.append(point)
    if fixed_points:
        fixed = np.asarray(fixed_points)
        ax.scatter(fixed[:, 0], fixed[:, 1], fixed[:, 2], marker="s", s=11, color="#9D1C20", depthshade=False)
    _format_3d(ax, cells, title)


def _normalizer(values: np.ndarray, signed: bool) -> colors.Normalize:
    minimum = float(np.nanmin(values))
    maximum = float(np.nanmax(values))
    if np.isclose(minimum, maximum):
        delta = max(abs(minimum) * 0.05, 1.0e-12)
        return colors.Normalize(minimum - delta, maximum + delta)
    if signed and minimum < 0.0 < maximum:
        extent = max(abs(minimum), abs(maximum))
        return colors.TwoSlopeNorm(vmin=-extent, vcenter=0.0, vmax=extent)
    return colors.Normalize(vmin=minimum, vmax=maximum)


def _draw_field(ax, cells: list[dict[str, object]], field: str, title: str, cmap: str, signed: bool) -> None:
    all_values = np.concatenate(
        [np.asarray([float(row[field]) for row in cell["rows"]], dtype=float) for cell in cells]
    )
    normalizer = _normalizer(all_values, signed)
    color_map = plt.get_cmap(cmap)
    for cell in cells:
        points = cell["points"]
        triangles = cell["triangles"]
        nodal = np.asarray([float(row[field]) for row in cell["rows"]], dtype=float)
        face_values = nodal[triangles].mean(axis=1)
        collection = Poly3DCollection(
            points[triangles],
            facecolors=color_map(normalizer(face_values)),
            edgecolor=(0.08, 0.10, 0.12, 0.25),
            linewidth=0.18,
            alpha=0.96,
        )
        ax.add_collection3d(collection)
    _format_3d(ax, cells, title)
    scalar = matplotlib.cm.ScalarMappable(norm=normalizer, cmap=color_map)
    scalar.set_array([])
    plt.colorbar(scalar, ax=ax, shrink=0.48, pad=0.015, aspect=18)


def render_myocardial_row(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    raw = result / "raw"
    node_rows = _read_csv(raw / "nodes.csv")
    face_rows = _read_csv(raw / "faces.csv")
    state_rows = _read_csv(raw / "state_metrics.csv")
    heterogeneity_rows = _read_csv(result / "heterogeneity.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in node_rows})
    if not snapshots:
        return {"status": "failed", "reason": "no snapshots"}
    initial = _snapshot_arrays(node_rows, face_rows, snapshots[0])
    final = _snapshot_arrays(node_rows, face_rows, snapshots[-1])
    figures = result / "figures"
    figures.mkdir()
    _style()

    structure_path = figures / "model_structure_initial_to_equilibrium.png"
    figure = plt.figure(figsize=(15.0, 5.2), constrained_layout=True)
    initial_axis = figure.add_subplot(1, 2, 1, projection="3d")
    final_axis = figure.add_subplot(1, 2, 2, projection="3d")
    _draw_structure(initial_axis, initial, "a  Initial heterogeneous row")
    _draw_structure(final_axis, final, "b  Passive mechanical equilibrium")
    figure.suptitle("Five connected cardiomyocytes | red squares: end clamps | black lines: material junctions", fontsize=11)
    figure.savefig(structure_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    field_path = figures / "equilibrium_mechanical_fields.png"
    figure = plt.figure(figsize=(15.0, 9.2), constrained_layout=True)
    field_specs = [
        ("curvature", "a  Surface curvature", "coolwarm", True),
        ("internal_pressure", "b  Intracellular pressure", "coolwarm", True),
        ("shape_traction", "c  Cytoskeletal-shape traction", "viridis", False),
        ("total_traction", "d  Total traction incl. reactions", "magma", False),
    ]
    for panel, (field, title, cmap, signed) in enumerate(field_specs, start=1):
        axis = figure.add_subplot(2, 2, panel, projection="3d")
        _draw_field(axis, final, field, title, cmap, signed)
    figure.suptitle("True final solver mesh and retained mechanical fields", fontsize=11)
    figure.savefig(field_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    relaxation_path = figures / "equilibrium_relaxation_history.png"
    state_rows = sorted(state_rows, key=lambda row: int(row["snapshot_index"]))
    progress = np.asarray([int(row["snapshot_index"]) / (len(state_rows) - 1) for row in state_rows])
    force = np.asarray([float(row["max_free_force"]) for row in state_rows])
    volume = 100.0 * np.asarray([float(row["max_volume_relative_error"]) for row in state_rows])
    angle = np.asarray([float(row["min_triangle_angle_deg"]) for row in state_rows])
    figure, axes = plt.subplots(1, 3, figsize=(11.8, 3.4), constrained_layout=True)
    axes[0].semilogy(progress, np.maximum(force, 1.0e-16), "o-", color="#2878B5", lw=1.4, ms=4)
    axes[0].axhline(1.0e-3, color="#9D1C20", ls="--", lw=1, label="gate")
    axes[0].set_ylabel("max free-node force")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(progress, volume, "o-", color="#D97A24", lw=1.4, ms=4)
    axes[1].axhline(2.0, color="#9D1C20", ls="--", lw=1)
    axes[1].set_ylabel("max volume error (%)")
    axes[2].plot(progress, angle, "o-", color="#4C956C", lw=1.4, ms=4)
    axes[2].axhline(15.0, color="#9D1C20", ls="--", lw=1)
    axes[2].set_ylabel("minimum triangle angle (deg)")
    for label, axis in zip(("a", "b", "c"), axes, strict=True):
        axis.set_xlabel("normalized numerical relaxation progress")
        axis.set_title(label, loc="left", fontweight="bold")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="#E5E8EB", lw=0.6)
    figure.savefig(relaxation_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    heterogeneity_path = figures / "frozen_cell_heterogeneity.png"
    shape_names = ["length_scale", "width_scale", "thickness_scale", "side_wave_amplitude", "center_y"]
    mechanics_names = ["bulk_modulus_factor", "surface_tension_factor", "area_modulus_factor", "prestress_factor"]
    shape_values = np.asarray([[float(row[name]) for name in shape_names] for row in heterogeneity_rows])
    mechanics_values = np.asarray([[float(row[name]) for name in mechanics_names] for row in heterogeneity_rows])
    shape_display = shape_values.copy()
    shape_display[:, 3] /= np.mean(shape_display[:, 3])
    shape_display[:, 4] = 1.0 + shape_display[:, 4] / 0.12 * 0.1
    figure, axes = plt.subplots(2, 1, figsize=(8.3, 5.2), constrained_layout=True)
    for axis, values, names, title in (
        (axes[0], shape_display, ["length", "width", "thickness", "wave*", "offset*"], "a  Frozen morphology inputs"),
        (axes[1], mechanics_values, ["bulk", "surface tension", "area modulus", "prestress"], "b  Frozen mechanics factors"),
    ):
        image = axis.imshow(values.T, cmap="RdBu_r", vmin=0.88, vmax=1.12, aspect="auto")
        axis.set_xticks(range(5), [f"C{index}" for index in range(1, 6)])
        axis.set_yticks(range(len(names)), names)
        axis.set_title(title, loc="left", fontweight="bold")
        for row_index in range(values.shape[1]):
            for column_index in range(values.shape[0]):
                axis.text(column_index, row_index, f"{values[column_index, row_index]:.3f}", ha="center", va="center", fontsize=7)
        plt.colorbar(image, ax=axis, pad=0.015, shrink=0.8, label="relative factor")
    figure.text(0.01, 0.01, "* wave and offset are rescaled only for this visual; exact values are retained in heterogeneity.csv", fontsize=7)
    figure.savefig(heterogeneity_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    manifest = {
        "status": "passed",
        "figures": [
            structure_path.relative_to(result).as_posix(),
            field_path.relative_to(result).as_posix(),
            relaxation_path.relative_to(result).as_posix(),
            heterogeneity_path.relative_to(result).as_posix(),
        ],
        "snapshot_indices": snapshots,
        "field_source": "raw/nodes.csv on true solver meshes",
        "time_semantics": "algorithmic relaxation progress, not physiological time",
    }
    (result / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest

