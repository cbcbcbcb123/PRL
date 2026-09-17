"""Render actual retained states for the regular 2x2 DCM qualification."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _mesh(raw: Path, snapshot: int, cell_id: int) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    node_rows = sorted(
        (
            row
            for row in _rows(raw / "nodes.csv")
            if int(row["snapshot_index"]) == snapshot
            and int(row["cell_id"]) == cell_id
        ),
        key=lambda row: int(row["node_index"]),
    )
    face_rows = sorted(
        (
            row
            for row in _rows(raw / "faces.csv")
            if int(row["snapshot_index"]) == snapshot
            and int(row["cell_id"]) == cell_id
        ),
        key=lambda row: int(row["face_local_id"]),
    )
    points = np.asarray(
        [[float(row[name]) for name in ("x", "y", "z")] for row in node_rows]
    )
    faces = np.asarray(
        [[int(row[name]) for name in ("n1", "n2", "n3")] for row in face_rows],
        dtype=int,
    )
    return points, faces, node_rows


def _snapshots(raw: Path) -> list[int]:
    return sorted({int(row["snapshot_index"]) for row in _rows(raw / "nodes.csv")})


def _surface(axis, points: np.ndarray, faces: np.ndarray, color: str) -> None:
    axis.add_collection3d(
        Poly3DCollection(
            points[faces],
            facecolor=color,
            edgecolor="#334155",
            linewidth=0.16,
            alpha=0.56,
        )
    )


def _box_edges(axis, bounds: np.ndarray) -> None:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    corners = np.asarray(
        [
            (x, y, z)
            for z in (zmin, zmax)
            for y in (ymin, ymax)
            for x in (xmin, xmax)
        ]
    )
    edges = (
        (0, 1), (0, 2), (1, 3), (2, 3),
        (4, 5), (4, 6), (5, 7), (6, 7),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    for first, second in edges:
        axis.plot(*corners[[first, second]].T, color="#64748B", linewidth=0.8, alpha=0.65)


def _bounds(state: dict[str, str]) -> np.ndarray:
    return np.asarray(
        [float(state[name]) for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")]
    )


def render_regular_2x2_load_hold(result: Path) -> dict[str, object]:
    executions = json.loads((result / "execution.json").read_text(encoding="utf-8"))
    complete = [
        execution
        for execution in executions
        if execution.get("return_code") == 0
        and (result / "raw" / execution["label"] / "state_metrics.csv").is_file()
    ]
    if not complete:
        raise ValueError("no complete regular-patch DCM level is available to render")
    first_raw = result / "raw" / complete[0]["label"]
    last_raw = result / "raw" / complete[-1]["label"]
    first_snapshot = _snapshots(first_raw)[0]
    last_snapshot = _snapshots(last_raw)[-1]
    first_state = _rows(first_raw / "state_metrics.csv")[0]
    last_state = _rows(last_raw / "state_metrics.csv")[-1]
    figure_directory = result / "figures"
    figure_directory.mkdir(exist_ok=False)
    colors = ("#4C78A8", "#72B7B2", "#F58518", "#E45756")

    structure = figure_directory / "r0b_model_structure.png"
    structure_svg = structure.with_suffix(".svg")
    figure = plt.figure(figsize=(14, 6), constrained_layout=True)
    for panel, (raw, snapshot, state, title) in enumerate(
        (
            (first_raw, first_snapshot, first_state, "Initial regular 2×2 patch"),
            (
                last_raw,
                last_snapshot,
                last_state,
                f"Last executed level: approach {float(complete[-1]['planar_approach']):.2f}",
            ),
        ),
        start=1,
    ):
        axis = figure.add_subplot(1, 2, panel, projection="3d")
        all_points = []
        for cell_id in range(4):
            points, faces, _ = _mesh(raw, snapshot, cell_id)
            _surface(axis, points, faces, colors[cell_id])
            all_points.append(points)
        bounds = _bounds(state)
        _box_edges(axis, bounds)
        points = np.concatenate(all_points)
        center = points.mean(axis=0)
        span = max(np.ptp(points, axis=0)) * 1.18
        axis.set_xlim(center[0] - span / 2, center[0] + span / 2)
        axis.set_ylim(center[1] - span / 2, center[1] + span / 2)
        axis.set_zlim(center[2] - span / 3, center[2] + span / 3)
        axis.set_box_aspect((1.0, 0.78, 0.38))
        axis.view_init(elev=26, azim=-58)
        axis.set_xlabel("long axis x")
        axis.set_ylabel("in-plane y")
        axis.set_zlabel("thickness z")
        axis.set_title(title)
    figure.suptitle(
        "R0-B DCM model | four identical long-axis cells in a transparent load-hold box",
        fontsize=14,
    )
    figure.savefig(structure, dpi=220, bbox_inches="tight")
    figure.savefig(structure_svg, bbox_inches="tight")
    plt.close(figure)

    approaches: list[float] = []
    forces: list[float] = []
    reactions: list[float] = []
    active_pairs: list[int] = []
    for execution in complete:
        raw = result / "raw" / execution["label"]
        final = _rows(raw / "state_metrics.csv")[-1]
        approaches.append(float(execution["planar_approach"]))
        forces.append(float(final["max_free_force"]))
        reactions.append(float(final["total_wall_reaction"]))
        active_pairs.append(int(final["contact_active_cell_pairs"]))

    result_figure = figure_directory / "r0b_load_hold_result.png"
    result_svg = result_figure.with_suffix(".svg")
    figure, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    axes[0, 0].plot(approaches, forces, "o-", color="#355C7D", label="final max nodal force")
    axes[0, 0].axhline(1.0e-3, color="#C62828", linestyle="--", label="equilibrium gate")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_xlabel("total x/y box approach")
    axes[0, 0].set_ylabel("force")
    axes[0, 0].set_title("A  Load-level equilibrium")
    axes[0, 0].legend(frameon=False)

    axes[0, 1].plot(approaches, reactions, "s-", color="#2E7D32", label="wall reaction")
    second = axes[0, 1].twinx()
    second.plot(approaches, active_pairs, "o--", color="#F58518", label="active pairs")
    axes[0, 1].set_xlabel("total x/y box approach")
    axes[0, 1].set_ylabel("summed wall reaction")
    second.set_ylabel("active cell pairs")
    axes[0, 1].set_title("B  Boundary load and contact network")

    contact_scatter = None
    curvature_scatter = None
    pressure_lines = []
    for cell_id in range(4):
        points, _, rows = _mesh(last_raw, last_snapshot, cell_id)
        contact = np.asarray([float(row["contact_traction"]) for row in rows])
        curvature = np.asarray([float(row["curvature"]) for row in rows])
        contact_scatter = axes[1, 0].scatter(
            points[:, 0], points[:, 1], c=contact, s=10, cmap="magma", vmin=0
        )
        curvature_scatter = axes[1, 1].scatter(
            points[:, 0], points[:, 1], c=curvature, s=10, cmap="coolwarm"
        )
        pressure_lines.append(
            f"cell {cell_id}: p={np.mean([float(row['internal_pressure']) for row in rows]):.3g}"
        )
    figure.colorbar(contact_scatter, ax=axes[1, 0], label="contact traction")
    axes[1, 0].set_aspect("equal", adjustable="box")
    axes[1, 0].set_xlabel("x")
    axes[1, 0].set_ylabel("y")
    axes[1, 0].set_title("C  Final contact-traction mesh")
    figure.colorbar(curvature_scatter, ax=axes[1, 1], label="nodal curvature")
    axes[1, 1].set_aspect("equal", adjustable="box")
    axes[1, 1].set_xlabel("x")
    axes[1, 1].set_ylabel("y")
    axes[1, 1].set_title("D  Final curvature and cell pressure")
    axes[1, 1].text(
        0.02, 0.02, "\n".join(pressure_lines), transform=axes[1, 1].transAxes, fontsize=8
    )
    figure.suptitle(
        "R0-B actual DCM states | FEM not run",
        fontsize=15,
    )
    figure.savefig(result_figure, dpi=220, bbox_inches="tight")
    figure.savefig(result_svg, bbox_inches="tight")
    plt.close(figure)

    return {
        "status": "passed",
        "last_executed_planar_approach": approaches[-1],
        "figures": [
            structure.relative_to(result).as_posix(),
            structure_svg.relative_to(result).as_posix(),
            result_figure.relative_to(result).as_posix(),
            result_svg.relative_to(result).as_posix(),
        ],
        "fem_visualization": "not_run",
        "scope": "actual retained DCM states only",
    }


__all__ = ["render_regular_2x2_load_hold"]
