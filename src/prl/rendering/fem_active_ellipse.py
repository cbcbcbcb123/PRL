"""Render actual states from the active elliptic FEM pilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import PolyCollection
import numpy as np


LAYER_COLORS = ("#4C9F70", "#D6B656", "#5B8DB8")


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as payload:
        return {name: payload[name] for name in payload.files}


def _mesh_collection(
    coordinates: np.ndarray,
    cells: np.ndarray,
    values: np.ndarray | None = None,
    *,
    layers: np.ndarray | None = None,
    cmap: str = "viridis",
) -> PolyCollection:
    polygons = coordinates[cells]
    if values is None:
        assert layers is not None
        colors = [LAYER_COLORS[int(layer)] for layer in layers]
        return PolyCollection(
            polygons,
            facecolors=colors,
            edgecolors="#2D3748",
            linewidths=0.18,
            alpha=0.82,
        )
    collection = PolyCollection(
        polygons,
        array=np.asarray(values),
        cmap=cmap,
        edgecolors=(0.1, 0.1, 0.1, 0.16),
        linewidths=0.12,
    )
    return collection


def _format_axis(axis: plt.Axes) -> None:
    axis.set_aspect("equal")
    axis.set_xlabel("normalized x")
    axis.set_ylabel("normalized y")
    axis.spines[["top", "right"]].set_visible(False)


def _curvature(points: np.ndarray) -> np.ndarray:
    previous = np.roll(points, 1, axis=0)
    following = np.roll(points, -1, axis=0)
    a = np.linalg.norm(points - previous, axis=1)
    b = np.linalg.norm(following - points, axis=1)
    c = np.linalg.norm(following - previous, axis=1)
    twice_area = np.abs(
        (points[:, 0] - previous[:, 0]) * (following[:, 1] - previous[:, 1])
        - (points[:, 1] - previous[:, 1]) * (following[:, 0] - previous[:, 0])
    )
    return 2.0 * twice_area / np.maximum(a * b * c, 1.0e-30)


def render_fem_active_ellipse(result: Path) -> dict[str, Any]:
    result = result.resolve()
    data = _load(result / "raw" / "G1.npz")
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    coordinates = data["coordinates"]
    cells = data["cells"].astype(np.int64)
    layers = data["cell_layers"].astype(np.int64)
    displacement = data["displacements"]
    equivalent = data["equivalent_stress"]
    pressure = data["pressure"]
    phases = data["phases"]
    activation = data["activation"]
    inner_nodes = data["inner_nodes"].astype(np.int64)
    lumen_change = data["lumen_fraction_change"]
    peak = int(np.argmax(activation))
    peak_coordinates = coordinates + displacement[peak]

    figure, axes = plt.subplots(1, 2, figsize=(11.0, 5.0), constrained_layout=True)
    for axis, state_coordinates, title in (
        (axes[0], coordinates, "Initial mesh (actual state)"),
        (axes[1], peak_coordinates, f"Peak activation, phase={phases[peak]:.2f} (1x deformation)"),
    ):
        axis.add_collection(
            _mesh_collection(state_coordinates, cells, layers=layers)
        )
        axis.autoscale_view()
        _format_axis(axis)
        axis.set_title(title)
    axes[0].text(
        0.02,
        0.02,
        "Free inner/outer surfaces\nKKT removes rigid x/y/rotation only",
        transform=axes[0].transAxes,
        fontsize=8,
        va="bottom",
        bbox={"facecolor": "white", "alpha": 0.86, "edgecolor": "none"},
    )
    arrow_angles = np.linspace(0.0, 2.0 * np.pi, 12, endpoint=False)
    arrow_radius = 1.23
    arrow_x = 1.25 * arrow_radius * np.cos(arrow_angles)
    arrow_y = arrow_radius * np.sin(arrow_angles)
    arrow_u = -1.25 * np.sin(arrow_angles)
    arrow_v = np.cos(arrow_angles)
    arrow_norm = np.hypot(arrow_u, arrow_v)
    axes[0].quiver(
        arrow_x,
        arrow_y,
        arrow_u / arrow_norm,
        arrow_v / arrow_norm,
        color="#A63D40",
        angles="xy",
        scale_units="xy",
        scale=7.0,
        width=0.006,
        label="myocardial active tangent",
    )
    axes[0].legend(loc="upper right", frameon=False, fontsize=8)
    axes[1].legend(
        handles=[
            plt.Line2D([0], [0], color=color, lw=7, label=name)
            for color, name in zip(LAYER_COLORS, ("endocardium", "ECM", "myocardium"), strict=True)
        ],
        loc="upper right",
        frameon=False,
    )
    figure.suptitle("F0 FEM model: synthetic three-layer elliptic ventricular section")
    model_png = figures / "f0_fem_model_structure.png"
    model_svg = figures / "f0_fem_model_structure.svg"
    figure.savefig(model_png, dpi=220)
    figure.savefig(model_svg)
    plt.close(figure)

    figure, axes = plt.subplots(2, 2, figsize=(12.0, 9.0), constrained_layout=True)
    axes[0, 0].plot(phases, 100.0 * lumen_change, color="#1F4E79", lw=2.2)
    axes[0, 0].axvline(phases[peak], color="#C44E52", ls="--", lw=1.0)
    axes[0, 0].set(
        xlabel="prescribed activation phase (not physiological time)",
        ylabel="lumen area change (%)",
        title="Quasi-static contraction–relaxation response",
    )
    axes[0, 0].spines[["top", "right"]].set_visible(False)

    stress_collection = _mesh_collection(
        peak_coordinates, cells, equivalent[peak], cmap="magma"
    )
    axes[0, 1].add_collection(stress_collection)
    axes[0, 1].autoscale_view()
    _format_axis(axes[0, 1])
    axes[0, 1].set_title("Peak 2-D equivalent stress (dimensionless)")
    figure.colorbar(stress_collection, ax=axes[0, 1], shrink=0.80)

    pressure_scale = float(np.max(np.abs(pressure[peak])))
    pressure_collection = _mesh_collection(
        peak_coordinates, cells, pressure[peak], cmap="coolwarm"
    )
    pressure_collection.set_clim(-pressure_scale, pressure_scale)
    axes[1, 0].add_collection(pressure_collection)
    axes[1, 0].autoscale_view()
    _format_axis(axes[1, 0])
    axes[1, 0].set_title("Peak in-plane pressure, -tr(sigma)/2")
    figure.colorbar(pressure_collection, ax=axes[1, 0], shrink=0.80)

    inner = peak_coordinates[inner_nodes]
    curvature = _curvature(inner)
    angles = np.degrees(np.unwrap(np.arctan2(inner[:, 1], inner[:, 0])))
    order = np.argsort(angles)
    axes[1, 1].plot(angles[order], curvature[order], color="#4C9F70", lw=1.8)
    axes[1, 1].set(
        xlabel="inner-boundary polar angle (degrees)",
        ylabel="discrete curvature (1 / normalized length)",
        title="Peak inner-boundary curvature",
    )
    axes[1, 1].spines[["top", "right"]].set_visible(False)
    figure.suptitle(
        "F0 active FEM result — engineering feasibility only; zebrafish calibration not run"
    )
    result_png = figures / "f0_fem_engineering_result.png"
    result_svg = figures / "f0_fem_engineering_result.svg"
    figure.savefig(result_png, dpi=220)
    figure.savefig(result_svg)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(6.4, 5.4), constrained_layout=True)
    maximum_stress = float(np.max(equivalent))

    def update(frame: int):
        axis.clear()
        current = coordinates + displacement[frame]
        collection = _mesh_collection(current, cells, equivalent[frame], cmap="magma")
        collection.set_clim(0.0, maximum_stress)
        axis.add_collection(collection)
        axis.autoscale_view()
        _format_axis(axis)
        axis.set_title(
            f"phase={phases[frame]:.2f}  activation={activation[frame]:.4f}\n"
            f"lumen area change={100.0*lumen_change[frame]:.2f}%"
        )
        return (collection,)

    animation = FuncAnimation(figure, update, frames=len(phases), interval=90, blit=False)
    gif_path = figures / "f0_fem_active_cycle.gif"
    animation.save(gif_path, writer=PillowWriter(fps=10), dpi=115)
    plt.close(figure)
    report = {
        "schema_version": "prl.fem_active_ellipse_rendering.v1",
        "status": "passed",
        "source_level": "G1",
        "actual_state_count": int(len(phases)),
        "deformation_scale": 1.0,
        "figures": [
            model_png.relative_to(result).as_posix(),
            model_svg.relative_to(result).as_posix(),
            result_png.relative_to(result).as_posix(),
            result_svg.relative_to(result).as_posix(),
            gif_path.relative_to(result).as_posix(),
        ],
        "interpretation_boundary": "All fields come from saved FEM states; phase is prescribed and not physiological time.",
    }
    (result / "rendering.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
