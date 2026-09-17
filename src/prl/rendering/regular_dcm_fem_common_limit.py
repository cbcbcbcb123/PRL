"""Render the executed R0-A DCM engineering state without inventing FEM output."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def _table(path: Path) -> np.ndarray:
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))


def _state(nodes: np.ndarray, snapshot: int, cell_id: int) -> np.ndarray:
    selected = nodes[
        (nodes["snapshot"].astype(int) == snapshot)
        & (nodes["cell"].astype(int) == cell_id)
    ]
    return selected[np.argsort(selected["node"].astype(int))]


def _faces(faces: np.ndarray, cell_id: int) -> np.ndarray:
    selected = faces[faces["cell"].astype(int) == cell_id]
    selected = selected[np.argsort(selected["face"].astype(int))]
    return np.column_stack([selected[name].astype(int) for name in ("a", "b", "c")])


def _reaction_curve(nodes: np.ndarray, snapshots: np.ndarray) -> np.ndarray:
    result = []
    for snapshot in snapshots:
        current = nodes[nodes["snapshot"].astype(int) == snapshot]
        ends = []
        for cell_id in (0, 1):
            selected = current[
                (current["cell"].astype(int) == cell_id) & (current["fixed"] > 0.5)
            ]
            ends.append(abs(float(np.sum(selected["rfx"]))))
        result.append(0.5 * sum(ends))
    return np.asarray(result)


def _surface(axis, nodes: np.ndarray, faces: np.ndarray, color: str, alpha: float) -> None:
    points = np.column_stack([nodes[name] for name in ("x", "y", "z")])
    collection = Poly3DCollection(
        points[faces], facecolor=color, edgecolor="#334155", linewidth=0.18, alpha=alpha
    )
    axis.add_collection3d(collection)


def render_regular_dcm_fem_common_limit(result: Path) -> dict:
    raw = result / "raw" / "dcm_two_cell_compression"
    nodes = _table(raw / "nodes.csv")
    faces = _table(raw / "faces.csv")
    states = _table(raw / "states.csv")
    separation = _table(raw / "separation.csv")
    snapshots = np.unique(nodes["snapshot"].astype(int))
    if len(snapshots) < 2:
        raise ValueError("at least two retained solver states are required")
    figure_directory = result / "figures"
    figure_directory.mkdir(exist_ok=False)
    colors = ("#4C78A8", "#F58518")

    structure_path = figure_directory / "r0a_model_structure.png"
    structure_svg = structure_path.with_suffix(".svg")
    figure = plt.figure(figsize=(14, 6), constrained_layout=True)
    for panel, snapshot in enumerate((int(snapshots[0]), int(snapshots[-1])), start=1):
        axis = figure.add_subplot(1, 2, panel, projection="3d")
        all_points = []
        for cell_id in (0, 1):
            current = _state(nodes, snapshot, cell_id)
            connectivity = _faces(faces, cell_id)
            _surface(axis, current, connectivity, colors[cell_id], 0.50)
            points = np.column_stack([current[name] for name in ("x", "y", "z")])
            all_points.append(points)
            fixed = current["fixed"] > 0.5
            axis.scatter(
                current["x"][fixed], current["y"][fixed], current["z"][fixed],
                c="#C62828", s=8, depthshade=False,
            )
        points = np.vstack(all_points)
        low, high = points.min(axis=0), points.max(axis=0)
        center, span = (low + high) / 2, max(high - low)
        axis.set_xlim(center[0] - span / 2, center[0] + span / 2)
        axis.set_ylim(center[1] - span / 2, center[1] + span / 2)
        axis.set_zlim(center[2] - span / 2, center[2] + span / 2)
        axis.set_box_aspect((1, 0.55, 0.42))
        axis.view_init(elev=22, azim=-62)
        axis.set_xlabel("long axis x")
        axis.set_ylabel("width y")
        axis.set_zlabel("thickness z")
        title = "State 0: positive-gap doublet" if panel == 1 else "State 20: prescribed end approach"
        axis.set_title(title)
        axis.text2D(
            0.02, 0.02,
            "red nodes: prescribed clamps\ntransparent surfaces: DCM cells",
            transform=axis.transAxes, fontsize=9,
        )
    figure.suptitle(
        "R0-A model structure | DCM surface cells + passive mechanics + explicit contact",
        fontsize=15,
    )
    figure.savefig(structure_path, dpi=220, bbox_inches="tight")
    figure.savefig(structure_svg, bbox_inches="tight")
    plt.close(figure)

    result_path = figure_directory / "r0a_engineering_result.png"
    result_svg = result_path.with_suffix(".svg")
    figure, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    coordinate = states["coordinate"]
    approach = 0.2 * coordinate / coordinate[-1]
    reaction = _reaction_curve(nodes, snapshots)
    axes[0, 0].plot(approach, separation["intercell_distance"], "o-", color="#2E7D32")
    axes[0, 0].axhline(1.0e-8, color="#C62828", linestyle="--", label="old distance floor")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_xlabel("prescribed total end approach")
    axes[0, 0].set_ylabel("exact intercell distance")
    axes[0, 0].set_title("A  Separation stayed positive")
    axes[0, 0].legend(frameon=False)

    axes[0, 1].plot(approach, states["max_free_force"], "o-", label="max free-node force")
    axes[0, 1].plot(approach, reaction, "s-", label="mean end reaction")
    axes[0, 1].axhline(1.0e-3, color="#C62828", linestyle="--", label="equilibrium gate")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_xlabel("prescribed total end approach")
    axes[0, 1].set_ylabel("model force")
    axes[0, 1].set_title("B  Transient did not reach equilibrium")
    axes[0, 1].legend(frameon=False, fontsize=9)

    final_snapshot = int(snapshots[-1])
    scatter = None
    for cell_id in (0, 1):
        current = _state(nodes, final_snapshot, cell_id)
        traction = np.sqrt(current["cfx"] ** 2 + current["cfy"] ** 2 + current["cfz"] ** 2) / current["area"]
        scatter = axes[1, 0].scatter(
            current["x"], current["y"], c=traction, s=10, cmap="magma", vmin=0,
        )
    figure.colorbar(scatter, ax=axes[1, 0], label="contact traction proxy |Fc|/area")
    axes[1, 0].set_aspect("equal", adjustable="box")
    axes[1, 0].set_xlabel("x")
    axes[1, 0].set_ylabel("y")
    axes[1, 0].set_title("C  Final contact-traction field")

    curvature_scatter = None
    pressure_text = []
    for cell_id in (0, 1):
        current = _state(nodes, final_snapshot, cell_id)
        curvature_scatter = axes[1, 1].scatter(
            current["x"], current["z"], c=current["curvature"], s=10,
            cmap="coolwarm",
        )
        pressure_text.append(f"cell {cell_id}: pressure={float(np.mean(current['pressure'])):.3g}")
    figure.colorbar(curvature_scatter, ax=axes[1, 1], label="nodal curvature")
    axes[1, 1].set_aspect("equal", adjustable="box")
    axes[1, 1].set_xlabel("x")
    axes[1, 1].set_ylabel("z")
    axes[1, 1].set_title("D  Curvature mesh + cell pressure")
    axes[1, 1].text(0.02, 0.02, "\n".join(pressure_text), transform=axes[1, 1].transAxes, fontsize=9)

    figure.suptitle(
        "R0-A engineering result | algorithmic transient, FEM and equilibrium not run",
        fontsize=15,
    )
    figure.savefig(result_path, dpi=220, bbox_inches="tight")
    figure.savefig(result_svg, bbox_inches="tight")
    plt.close(figure)

    report = {
        "status": "passed",
        "figures": [
            structure_path.relative_to(result).as_posix(),
            structure_svg.relative_to(result).as_posix(),
            result_path.relative_to(result).as_posix(),
            result_svg.relative_to(result).as_posix(),
        ],
        "fem_visualization": "not_run",
        "scope": "actual retained DCM states only; no conceptual FEM panel",
    }
    target = result / "rendering.json"
    if target.exists():
        raise FileExistsError(f"create-only: {target}")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


__all__ = ["render_regular_dcm_fem_common_limit"]
