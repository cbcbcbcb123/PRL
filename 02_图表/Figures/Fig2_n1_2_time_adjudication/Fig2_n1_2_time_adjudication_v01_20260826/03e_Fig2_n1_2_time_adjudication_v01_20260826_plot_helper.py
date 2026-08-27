from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np


PREFIX = "Fig2_n1_2_time_adjudication_v01_20260826"
LEVELS = ("T16", "T32", "T64")
LEVEL_COLORS = {"T16": "#9A9A9A", "T32": "#E58B2A", "T64": "#2676A9"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_dense(path: Path) -> dict[str, np.ndarray]:
    rows = read_rows(path)
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        for key in rows[0]
    }


def select_one(rows: list[dict[str, str]], **conditions: str) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if all(row[key] == value for key, value in conditions.items())
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one row for {conditions}, found {len(matches)}")
    return matches[0]


def short_quantity(name: str) -> str:
    return {
        "axial_shortening": "shortening",
        "maximum_discrete_interface_traction": "max traction",
        "p95_discrete_interface_traction": "p95 traction",
        "total_stored_energy": "total energy",
        "ecm_equilibrium_energy": "ECM eq. energy",
        "ecm_viscoelastic_energy": "ECM VE energy",
        "ecm_internal_z_norm": r"ECM $||Z||$",
    }[name]


def panel_label(axis: Any, label: str) -> None:
    axis.text(
        -0.11,
        1.12,
        label,
        transform=axis.transAxes,
        fontsize=15,
        fontweight="bold",
        va="top",
    )


def plot_waveforms(axis: Any, dense: dict[str, np.ndarray]) -> None:
    phase = dense["t_over_T"]
    for level in LEVELS:
        axis.plot(
            phase,
            100.0 * dense[f"{level}_axial_shortening"],
            color=LEVEL_COLORS[level],
            linewidth=2.1,
            label=level,
        )
    axis.set_xlabel(r"Cardiac phase  $t/T$")
    axis.set_ylabel("Axial shortening (%)")
    axis.set_title("Cell-scale contraction converges monotonically", loc="left")
    axis.legend(frameon=False, ncol=3, loc="upper center")
    panel_label(axis, "A")


def plot_memory_phase(
    axis: Any,
    dense: dict[str, np.ndarray],
    global_rows: list[dict[str, str]],
) -> None:
    phase = dense["t_over_T"]
    peak_row = select_one(
        global_rows,
        kind="peak_phase",
        quantity="ecm_internal_z_norm",
    )
    for level in LEVELS:
        values = dense[f"{level}_ecm_internal_z_norm"]
        axis.plot(
            phase,
            values,
            color=LEVEL_COLORS[level],
            linewidth=2.0,
            label=level,
        )
        peak_phase = float(peak_row[level])
        peak_value = float(np.interp(peak_phase, phase, values))
        axis.scatter(
            [peak_phase],
            [peak_value],
            s=36,
            color=LEVEL_COLORS[level],
            edgecolor="white",
            linewidth=0.7,
            zorder=5,
        )
    axis.axvspan(
        float(peak_row["T32"]),
        float(peak_row["T64"]),
        color="#C64A43",
        alpha=0.13,
    )
    axis.text(
        0.04,
        0.08,
        r"$|\Delta\phi_{32\to64}|=0.015625>0.01$",
        transform=axis.transAxes,
        color="#B13E38",
        fontsize=10.5,
    )
    axis.set_xlabel(r"Cardiac phase  $t/T$")
    axis.set_ylabel(r"ECM memory  $||Z||_F$")
    axis.set_title(
        "Memory amplitude converges; peak phase misses the gate",
        loc="left",
    )
    panel_label(axis, "B")


def category_gate_ratios(
    global_rows: list[dict[str, str]],
    field_rows: list[dict[str, str]],
) -> tuple[list[str], np.ndarray]:
    def maximum_ratio(kind: str) -> float:
        selected = [row for row in global_rows if row["kind"] == kind]
        return max(
            float(row["T32_T64_difference"]) / float(row["gate"])
            for row in selected
        )

    displacement_fields = {
        "myocyte_displacement",
        "ecm_displacement",
        "endocardial_displacement",
    }
    physical_fields = [
        row
        for row in field_rows
        if not (row["phase"] == "1.0" and row["field"] in displacement_fields)
    ]
    physical_field_ratio = max(
        float(row["T32_T64_difference"]) / float(row["gate"])
        for row in physical_fields
    )
    closure_rows = [
        row
        for row in field_rows
        if row["phase"] == "1.0" and row["field"] in displacement_fields
    ]
    closure_ratio = max(
        float(row["T32_T64_difference"]) / float(row["gate"])
        for row in closure_rows
    )
    labels = [
        "waveform",
        "integral",
        "peak\namplitude",
        "dissipation",
        "physical\nfields",
        "peak\nphase",
        "phase-1\nclosure rel.",
    ]
    ratios = np.asarray([
        maximum_ratio("waveform_normalized_l2"),
        maximum_ratio("cycle_integral"),
        maximum_ratio("peak_amplitude"),
        maximum_ratio("cycle_dissipation"),
        physical_field_ratio,
        maximum_ratio("peak_phase"),
        closure_ratio,
    ])
    return labels, ratios


def plot_gate_overview(
    axis: Any,
    global_rows: list[dict[str, str]],
    field_rows: list[dict[str, str]],
) -> None:
    labels, ratios = category_gate_ratios(global_rows, field_rows)
    colors = ["#2F8F62" if value <= 1.0 else "#C64A43" for value in ratios]
    positions = np.arange(len(labels))
    axis.bar(positions, ratios, color=colors, width=0.72)
    axis.axhline(1.0, color="#B13E38", linestyle="--", linewidth=1.5)
    axis.set_yscale("log")
    axis.set_ylim(0.03, max(25.0, 1.35 * float(ratios.max())))
    axis.set_xticks(positions, labels, rotation=20, ha="right", fontsize=8.8)
    axis.set_ylabel("T32→T64 error / registered gate")
    axis.set_title(
        "Five evidence classes pass; two strict classes fail",
        loc="left",
    )
    for position, value in zip(positions, ratios, strict=True):
        axis.text(
            position,
            value * (1.16 if value >= 1.0 else 1.25),
            f"{value:.2g}×",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#9D302C" if value > 1.0 else "#236B49",
        )
    panel_label(axis, "C")


def plot_peak_phase_gate(axis: Any, global_rows: list[dict[str, str]]) -> None:
    rows = [row for row in global_rows if row["kind"] == "peak_phase"]
    differences = np.asarray(
        [float(row["T32_T64_difference"]) for row in rows]
    )
    positions = np.arange(len(rows))
    colors = ["#2F8F62" if value <= 0.01 else "#C64A43" for value in differences]
    axis.barh(positions, differences, color=colors, height=0.68)
    axis.axvline(0.01, color="#B13E38", linestyle="--", linewidth=1.5)
    axis.set_yticks(positions, [short_quantity(row["quantity"]) for row in rows])
    axis.invert_yaxis()
    axis.set_xlabel(r"Peak-phase difference  $|\Delta\phi_{32\to64}|$")
    axis.set_title(
        "Two memory-related phase observables remain unresolved",
        loc="left",
    )
    axis.set_xlim(0.0, 0.0185)
    for position, value in zip(positions, differences, strict=True):
        if value > 0.0:
            axis.text(value + 0.00035, position, f"{value:.5f}", va="center", fontsize=8.7)
    panel_label(axis, "D")


def plot_closure_residual(axis: Any, field_rows: list[dict[str, str]]) -> None:
    field_labels = {
        "myocyte_displacement": "myocyte",
        "ecm_displacement": "ECM",
        "endocardial_displacement": "endocardium",
    }
    colors = {
        "myocyte_displacement": "#D0524F",
        "ecm_displacement": "#2F8F62",
        "endocardial_displacement": "#4D9DB8",
    }
    x = np.arange(3)
    for field, label in field_labels.items():
        row = select_one(
            field_rows,
            phase="1.0",
            field=field,
            summary="absolute_p95",
        )
        values = np.asarray([float(row[level]) for level in LEVELS])
        axis.plot(
            x,
            values,
            marker="o",
            linewidth=2.0,
            color=colors[field],
            label=label,
        )
    axis.set_yscale("log")
    axis.set_xticks(x, LEVELS)
    axis.set_ylabel("Phase-1 displacement p95 (absolute model units)")
    axis.set_title(
        "Closure residuals decrease; relative-to-zero ratios fail",
        loc="left",
    )
    axis.legend(frameon=False, ncol=3, fontsize=9)
    axis.text(
        0.03,
        0.04,
        "The strict failure is a normalization warning,\nnot growing physical drift.",
        transform=axis.transAxes,
        fontsize=9.5,
        color="#555555",
    )
    panel_label(axis, "E")


def plot_peak_fields(container: Any, peak_field_path: Path) -> None:
    nested = container.subgridspec(1, 2, wspace=0.30)
    figure = plt.gcf()
    left = figure.add_subplot(nested[0, 0], projection="3d")
    right = figure.add_subplot(nested[0, 1], projection="3d")
    with np.load(peak_field_path) as data:
        tets = data["ecm_tetrahedra"]
        vertices = data["t64_ecm_vertices"]
        centroids = vertices[tets].mean(axis=1)
        stress = data["t64_ecm_max_principal_cauchy_stress"]
        displacement_difference = data[
            "t32_t64_ecm_displacement_difference_magnitude"
        ]
        myocyte = data["t64_myocyte_vertices"]
        endocardial = data["t64_endocardial_vertices"]

    stress_norm = Normalize(
        vmin=float(np.quantile(stress, 0.02)),
        vmax=float(np.quantile(stress, 0.98)),
    )
    stress_plot = left.scatter(
        centroids[:, 0],
        centroids[:, 2],
        centroids[:, 1],
        c=stress,
        cmap="viridis",
        norm=stress_norm,
        s=5,
        alpha=0.85,
    )
    left.scatter(
        myocyte[:, 0], myocyte[:, 2], myocyte[:, 1],
        s=2, color="#D0524F", alpha=0.35,
    )
    left.scatter(
        endocardial[:, 0], endocardial[:, 2], endocardial[:, 1],
        s=2, color="#4D9DB8", alpha=0.35,
    )
    left.set_title("T64 peak stress", fontsize=9.2)
    figure.colorbar(
        stress_plot,
        ax=left,
        fraction=0.035,
        pad=0.01,
        label=r"$\sigma_{max}$",
    )

    difference_plot = right.scatter(
        vertices[:, 0],
        vertices[:, 2],
        vertices[:, 1],
        c=displacement_difference,
        cmap="magma",
        s=8,
        alpha=0.90,
    )
    right.set_title(r"T32–T64 peak $|\Delta u|$", fontsize=9.2)
    figure.colorbar(
        difference_plot,
        ax=right,
        fraction=0.035,
        pad=0.01,
        label=r"$|\Delta u|$",
    )
    for axis in (left, right):
        axis.set_xlabel("x", labelpad=-3)
        axis.set_ylabel("z", labelpad=-3)
        axis.set_zlabel("y", labelpad=-3)
        axis.tick_params(labelsize=7, pad=-2)
        axis.view_init(elev=22, azim=-61)
    left.text2D(
        -0.14,
        1.07,
        "F",
        transform=left.transAxes,
        fontsize=15,
        fontweight="bold",
    )


def build_figure(revision_dir: Path) -> tuple[Path, Path]:
    global_rows = read_rows(revision_dir / f"01_{PREFIX}_data.csv")
    dense = read_dense(revision_dir / f"01a_{PREFIX}_data_dense.csv")
    field_rows = read_rows(revision_dir / f"01b_{PREFIX}_data_field.csv")
    peak_field_path = revision_dir / f"03c_{PREFIX}_peak_field.npz"

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "semibold",
        "axes.grid": True,
        "grid.alpha": 0.18,
        "grid.linewidth": 0.7,
    })
    figure = plt.figure(figsize=(18.2, 10.8))
    grid = figure.add_gridspec(
        2,
        3,
        left=0.065,
        right=0.99,
        bottom=0.135,
        top=0.895,
        wspace=0.28,
        hspace=0.38,
    )
    axis_a = figure.add_subplot(grid[0, 0])
    axis_b = figure.add_subplot(grid[0, 1])
    axis_c = figure.add_subplot(grid[0, 2])
    axis_d = figure.add_subplot(grid[1, 0])
    axis_e = figure.add_subplot(grid[1, 1])

    plot_waveforms(axis_a, dense)
    plot_memory_phase(axis_b, dense, global_rows)
    plot_gate_overview(axis_c, global_rows, field_rows)
    plot_peak_phase_gate(axis_d, global_rows)
    plot_closure_residual(axis_e, field_rows)
    plot_peak_fields(grid[1, 2], peak_field_path)

    figure.suptitle(
        "N1-2c formal time-grid adjudication: bulk observables pass, strict registered gate not fully passed",
        fontsize=18,
        fontweight="bold",
        y=0.965,
    )
    figure.text(
        0.065,
        0.045,
        "Registered verdict: NOT FULLY PASSED. T32→T64 waveforms, amplitudes, integrals, dissipation and physical-phase fields pass;\n"
        "two memory peak phases and relative phase-1 closure metrics fail. P5 used frozen T16/T32/T64 states only; T128 was not performed.",
        fontsize=10.0,
        color="#8E302D",
        weight="semibold",
    )

    png_path = revision_dir / f"04_{PREFIX}.png"
    svg_path = revision_dir / f"05_{PREFIX}.svg"
    figure.savefig(png_path, dpi=220, facecolor="white")
    figure.savefig(svg_path, facecolor="white")
    plt.close(figure)
    return png_path, svg_path


if __name__ == "__main__":
    build_figure(Path.cwd().resolve())
