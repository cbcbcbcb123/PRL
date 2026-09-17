"""Render actual F1-S synthetic orientation-field FEM states."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image


LAYER_COLORS = ("#4C9F70", "#D6B656", "#D9E3F0")


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as payload:
        return {name: payload[name] for name in payload.files}


def _format_axis(axis: plt.Axes) -> None:
    axis.set_aspect("equal")
    axis.set_xlabel("normalized x")
    axis.set_ylabel("normalized y")
    axis.spines[["top", "right"]].set_visible(False)


def _mesh_collection(
    coordinates: np.ndarray,
    cells: np.ndarray,
    values: np.ndarray,
    *,
    cmap: str,
    norm: Normalize | None = None,
) -> PolyCollection:
    return PolyCollection(
        coordinates[cells],
        array=np.asarray(values),
        cmap=cmap,
        norm=norm,
        edgecolors=(0.08, 0.10, 0.13, 0.13),
        linewidths=0.10,
    )


def _draw_patch_boundaries(axis: plt.Axes, aspect_x: float, aspect_y: float) -> None:
    angle = np.linspace(0.0, 2.0 * np.pi, 361)
    for radius in (1.10, 1.225, 1.35):
        axis.plot(
            aspect_x * radius * np.cos(angle),
            aspect_y * radius * np.sin(angle),
            color="#263238",
            lw=0.42 if radius == 1.225 else 0.65,
            alpha=0.70,
        )
    for boundary in np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False):
        axis.plot(
            [aspect_x * 1.10 * np.cos(boundary), aspect_x * 1.35 * np.cos(boundary)],
            [aspect_y * 1.10 * np.sin(boundary), aspect_y * 1.35 * np.sin(boundary)],
            color="#263238",
            lw=0.35,
            alpha=0.58,
        )


def _draw_patch_axes(axis: plt.Axes, data: dict[str, np.ndarray]) -> None:
    cells = data["cells"].astype(np.int64)
    myocardium = data["cell_layers"].astype(np.int64) == 2
    centroids = np.mean(data["coordinates"][cells], axis=1)
    patch_ids = data["patch_ids"].astype(np.int64)
    angles = data["orientation_angles"]
    for patch_id in range(48):
        selected = myocardium & (patch_ids == patch_id)
        center = np.average(
            centroids[selected], axis=0, weights=data["reference_areas"][selected]
        )
        vector = np.average(
            np.column_stack((np.cos(angles[selected]), np.sin(angles[selected]))),
            axis=0,
            weights=data["reference_areas"][selected],
        )
        vector /= np.linalg.norm(vector)
        half_length = 0.055
        axis.plot(
            [center[0] - half_length * vector[0], center[0] + half_length * vector[0]],
            [center[1] - half_length * vector[1], center[1] + half_length * vector[1]],
            color="#7A1F2B",
            lw=1.25,
            solid_capstyle="round",
        )


def render_fem_synthetic_orientation(result: Path) -> dict[str, Any]:
    result = result.resolve()
    configuration = json.loads((result / "configuration.json").read_text(encoding="utf-8"))
    verification = json.loads((result / "verification.json").read_text(encoding="utf-8"))
    uniform = _load(result / "raw" / "uniform" / "G1.npz")
    random = _load(result / "raw" / "synthetic_random" / "G1.npz")
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    coordinates = uniform["coordinates"]
    cells = uniform["cells"].astype(np.int64)
    layers = uniform["cell_layers"].astype(np.int64)
    myocardium = layers == 2
    offset_norm = TwoSlopeNorm(vmin=-18.0, vcenter=0.0, vmax=18.0)

    figure, axes = plt.subplots(1, 2, figsize=(12.6, 5.6), constrained_layout=True)
    for axis, data, title in (
        (axes[0], uniform, "Uniform field: local myocardial tangent"),
        (axes[1], random, "Controlled synthetic field: frozen seed 20260916"),
    ):
        values = np.zeros(len(cells), dtype=np.float64)
        patch_offsets = data["patch_offsets_degrees"].reshape(-1)
        values[myocardium] = patch_offsets[data["patch_ids"][myocardium].astype(np.int64)]
        facecolors = matplotlib.cm.get_cmap("coolwarm")(offset_norm(values))
        for layer_id, color in enumerate(LAYER_COLORS[:2]):
            facecolors[layers == layer_id] = matplotlib.colors.to_rgba(color, 0.82)
        collection = PolyCollection(
            coordinates[cells],
            facecolors=facecolors,
            edgecolors=(0.10, 0.12, 0.14, 0.12),
            linewidths=0.10,
        )
        axis.add_collection(collection)
        _draw_patch_boundaries(
            axis,
            float(configuration["geometry"]["aspect_x"]),
            float(configuration["geometry"]["aspect_y"]),
        )
        _draw_patch_axes(axis, data)
        axis.autoscale_view()
        _format_axis(axis)
        axis.set_title(title)
    colorbar = figure.colorbar(
        matplotlib.cm.ScalarMappable(norm=offset_norm, cmap="coolwarm"),
        ax=axes,
        shrink=0.78,
        label="long-axis offset from local tangent (degrees)",
    )
    colorbar.ax.axhline(colorbar.norm(0.0), color="#202124", lw=0.5)
    figure.legend(
        handles=[
            Line2D([0], [0], color="#7A1F2B", lw=2.2, label="nematic long axis (no polarity)"),
            Line2D([0], [0], color="#263238", lw=0.8, label="material-patch boundary"),
        ],
        loc="lower center",
        ncol=2,
        frameon=False,
    )
    figure.suptitle(
        "F1-S model input — 2×24 material patches, not explicit or measured cells"
    )
    model_png = figures / "f1s_model_structure.png"
    model_svg = figures / "f1s_model_structure.svg"
    figure.savefig(model_png, dpi=220)
    figure.savefig(model_svg)
    plt.close(figure)

    peak = int(np.argmax(uniform["activation"]))
    uniform_peak = coordinates + uniform["displacements"][peak]
    random_peak = coordinates + random["displacements"][peak]
    stress_max = float(
        max(np.max(uniform["equivalent_stress"][peak]), np.max(random["equivalent_stress"][peak]))
    )
    stress_norm = Normalize(vmin=0.0, vmax=stress_max)
    difference = random["equivalent_stress"][peak] - uniform["equivalent_stress"][peak]
    difference_max = float(np.max(np.abs(difference)))
    difference_norm = TwoSlopeNorm(
        vmin=-difference_max, vcenter=0.0, vmax=difference_max
    )
    figure, axes = plt.subplots(2, 3, figsize=(15.0, 9.2), constrained_layout=True)
    for axis, state, values, title in (
        (
            axes[0, 0],
            uniform_peak,
            uniform["equivalent_stress"][peak],
            "Uniform peak equivalent stress",
        ),
        (
            axes[0, 1],
            random_peak,
            random["equivalent_stress"][peak],
            "Synthetic-random peak equivalent stress",
        ),
    ):
        collection = _mesh_collection(state, cells, values, cmap="magma", norm=stress_norm)
        axis.add_collection(collection)
        axis.autoscale_view()
        _format_axis(axis)
        axis.set_title(title)
    figure.colorbar(
        matplotlib.cm.ScalarMappable(norm=stress_norm, cmap="magma"),
        ax=[axes[0, 0], axes[0, 1]],
        shrink=0.78,
        label="2-D equivalent stress (dimensionless)",
    )
    difference_collection = _mesh_collection(
        random_peak, cells, difference, cmap="coolwarm", norm=difference_norm
    )
    axes[0, 2].add_collection(difference_collection)
    axes[0, 2].autoscale_view()
    _format_axis(axes[0, 2])
    axes[0, 2].set_title("Stress difference: random − uniform")
    figure.colorbar(
        difference_collection,
        ax=axes[0, 2],
        shrink=0.78,
        label="equivalent-stress difference",
    )

    phases = uniform["phases"]
    axes[1, 0].plot(
        phases,
        100.0 * uniform["lumen_fraction_change"],
        color="#1F4E79",
        lw=2.2,
        label="uniform",
    )
    axes[1, 0].plot(
        phases,
        100.0 * random["lumen_fraction_change"],
        color="#A63D40",
        lw=2.0,
        label="synthetic random",
    )
    axes[1, 0].set(
        xlabel="prescribed phase (not physiological time)",
        ylabel="lumen area change (%)",
        title="Global response remains closely mean-matched",
    )
    axes[1, 0].legend(frameon=False)
    axes[1, 0].spines[["top", "right"]].set_visible(False)

    paired = verification["paired_sensitivity"]
    mesh_difference = verification["sensitivity_mesh_differences"]
    labels = ("Displacement field", "Myocardial stress field")
    effects = np.asarray(
        [
            paired["G1"]["peak_relative_displacement_l2"],
            paired["G1"]["peak_myocardial_equivalent_stress_relative_l2"],
        ]
    )
    uncertainty = 2.0 * np.asarray(
        [
            mesh_difference["peak_relative_displacement_l2"],
            mesh_difference["peak_myocardial_equivalent_stress_relative_l2"],
        ]
    )
    positions = np.arange(2)
    width = 0.36
    axes[1, 1].bar(
        positions - width / 2,
        100.0 * effects,
        width,
        color="#3B7EA1",
        label="G1 paired effect",
    )
    axes[1, 1].bar(
        positions + width / 2,
        100.0 * uncertainty,
        width,
        color="#A7B6C2",
        label="2× |G1−G0|",
    )
    axes[1, 1].axhline(1.0, color="#A63D40", ls="--", lw=1.2, label="1% effect gate")
    axes[1, 1].set_xticks(positions, labels, rotation=8)
    axes[1, 1].set_ylabel("relative magnitude (%)")
    axes[1, 1].set_title("Pre-registered sensitivity gate")
    axes[1, 1].legend(frameon=False, fontsize=8)
    axes[1, 1].spines[["top", "right"]].set_visible(False)

    stress_cv = [
        paired["G1"]["uniform_peak_myocardial_stress_cv"],
        paired["G1"]["synthetic_random_peak_myocardial_stress_cv"],
    ]
    outer_cv = [
        paired["G1"]["uniform_peak_outer_displacement_cv"],
        paired["G1"]["synthetic_random_peak_outer_displacement_cv"],
    ]
    positions = np.arange(2)
    axes[1, 2].bar(
        positions - width / 2,
        stress_cv,
        width,
        color="#6C8EBF",
        label="myocardial stress CV",
    )
    axes[1, 2].bar(
        positions + width / 2,
        outer_cv,
        width,
        color="#82B366",
        label="outer-displacement CV",
    )
    axes[1, 2].set_xticks(positions, ("uniform", "synthetic random"))
    axes[1, 2].set_ylabel("coefficient of variation")
    axes[1, 2].set_title("Auxiliary spatial heterogeneity readouts")
    axes[1, 2].legend(frameon=False, fontsize=8)
    axes[1, 2].spines[["top", "right"]].set_visible(False)
    figure.suptitle(
        "F1-S result — sensitivity to a synthetic direction field, not zebrafish validation"
    )
    result_png = figures / "f1s_orientation_sensitivity_result.png"
    result_svg = figures / "f1s_orientation_sensitivity_result.svg"
    figure.savefig(result_png, dpi=220)
    figure.savefig(result_svg)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(11.6, 5.4), constrained_layout=True)

    def update(frame: int):
        artists: list[Any] = []
        for axis, data, title in (
            (axes[0], uniform, "uniform"),
            (axes[1], random, "synthetic random"),
        ):
            axis.clear()
            current = coordinates + data["displacements"][frame]
            collection = _mesh_collection(
                current,
                cells,
                data["equivalent_stress"][frame],
                cmap="magma",
                norm=stress_norm,
            )
            axis.add_collection(collection)
            axis.autoscale_view()
            _format_axis(axis)
            axis.set_title(
                f"{title}\nphase={data['phases'][frame]:.2f}; "
                f"lumen={100.0*data['lumen_fraction_change'][frame]:.2f}%"
            )
            artists.append(collection)
        figure.suptitle("F1-S actual quasi-static states; deformation 1×")
        return tuple(artists)

    animation = FuncAnimation(figure, update, frames=len(phases), interval=90, blit=False)
    gif_path = figures / "f1s_orientation_sensitivity.gif"
    animation.save(gif_path, writer=PillowWriter(fps=10), dpi=110)
    plt.close(figure)

    image_checks: dict[str, Any] = {}
    for path in (model_png, result_png):
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_checks[path.name] = {"width": image.width, "height": image.height}
    with Image.open(gif_path) as image:
        gif_frames = int(getattr(image, "n_frames", 1))
        gif_size = {"width": image.width, "height": image.height}
    report = {
        "schema_version": "prl.fem_synthetic_orientation_rendering.v1",
        "status": "passed" if gif_frames == 41 else "failed",
        "source_level": "G1",
        "actual_state_count": int(len(phases)),
        "gif_frame_count": gif_frames,
        "gif_size": gif_size,
        "deformation_scale": 1.0,
        "image_checks": image_checks,
        "figures": [
            model_png.relative_to(result).as_posix(),
            model_svg.relative_to(result).as_posix(),
            result_png.relative_to(result).as_posix(),
            result_svg.relative_to(result).as_posix(),
            gif_path.relative_to(result).as_posix(),
        ],
        "interpretation_boundary": (
            "All fields come from saved FEM states. Material patches are not explicit "
            "cells; phase is prescribed and not physiological time."
        ),
    }
    (result / "rendering.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
