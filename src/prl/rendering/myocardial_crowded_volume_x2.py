"""Render true states and baseline comparisons for doubled volume targets."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

from .cb_plot_unified_style import (
    DEFAULT_STYLE,
    add_top_information,
    create_figure_with_axis_box,
    export_figure,
)
from .myocardial_crowded_box import (
    GRID,
    _draw_structure_3d,
    _field_normalizer,
    _read_csv,
    _snapshot_cells,
    _state_bounds,
    _style,
)
from .myocardial_crowded_target_pair import (
    _draw_shared_field,
    _save_scientific_layout,
)


CONDITION = "HETEROGENEOUS_TARGETS_X2_VOLUME"
PARENT_CONDITION = "HETEROGENEOUS_TARGETS"


def _final_rows(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(path)
    final_snapshot = max(int(row["snapshot_index"]) for row in rows)
    return sorted(
        (row for row in rows if int(row["snapshot_index"]) == final_snapshot),
        key=lambda row: int(row["cell_id"]),
    )


def _paired_figure(
    figures: Path,
    metric: str,
    ylabel: str,
    baseline_rows: list[dict[str, str]],
    doubled_rows: list[dict[str, str]],
) -> list[Path]:
    figure, axis = create_figure_with_axis_box(
        style=DEFAULT_STYLE,
        margins_in=(3.00, 0.85, 1.75, 1.20),
    )
    baseline = np.asarray([float(row[metric]) for row in baseline_rows])
    doubled = np.asarray([float(row[metric]) for row in doubled_rows])
    for before, after in zip(baseline, doubled, strict=True):
        axis.plot(
            [0.0, 1.0],
            [before, after],
            color="#6F7B80",
            alpha=0.25,
            linewidth=DEFAULT_STYLE.data_line_width,
            marker="o",
            markersize=7.0,
            markerfacecolor="#FFFFFF",
            markeredgecolor="#6F7B80",
        )
    axis.plot(
        [0.0, 1.0],
        [float(baseline.mean()), float(doubled.mean())],
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
    axis.set_xticks([0.0, 1.0], ["Baseline", "2× volume target"])
    axis.set_xlabel("Frozen reference-target condition")
    axis.set_ylabel(ylabel)
    add_top_information(axis, "n = 25 paired cell IDs", style=DEFAULT_STYLE)
    paths = export_figure(
        figure,
        axis,
        figures / f"paired_baseline_vs_x2_{metric}",
        style=DEFAULT_STYLE,
    )
    plt.close(figure)
    return [paths.png, paths.svg, paths.manifest]


def _render_failure_package(
    result: Path,
    figures: Path,
    raw: Path,
    states: list[dict[str, str]],
    nodes: list[dict[str, str]],
    faces: list[dict[str, str]],
    parent_states: list[dict[str, str]],
    parent_nodes: list[dict[str, str]],
    parent_faces: list[dict[str, str]],
) -> dict[str, object]:
    """Render only retained evidence when the solver stops before nine states."""

    snapshots = sorted({int(row["snapshot_index"]) for row in nodes})
    initial_cells = _snapshot_cells(nodes, faces, snapshots[0])
    parent_snapshot = max(int(row["snapshot_index"]) for row in parent_nodes)
    parent_cells = _snapshot_cells(parent_nodes, parent_faces, parent_snapshot)
    all_paths: list[Path] = []

    structure = plt.figure(figsize=(9.6, 4.8))
    for panel, (cells, bounds, title) in enumerate(
        (
            (
                initial_cells,
                _state_bounds(states[0]),
                "a  Doubled target | only retained state 0",
            ),
            (
                parent_cells,
                _state_bounds(parent_states[-1]),
                "b  Parent heterogeneous target | completed final state",
            ),
        ),
        start=1,
    ):
        axis = structure.add_subplot(1, 2, panel, projection="3d")
        _draw_structure_3d(axis, cells, bounds, title)
    structure.suptitle(
        "Doubled-target run stopped before state 1; no formed x2 structure exists",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    structure.subplots_adjust(
        left=0.035, right=0.98, bottom=0.06, top=0.87, wspace=0.08
    )
    all_paths.extend(
        _save_scientific_layout(
            structure,
            figures / "failure_structure_state0",
            reason="The failed run retained only one true 3D state; the completed parent is shown as context.",
        )
    )
    plt.close(structure)

    target_rows = _read_csv(result / "targets" / f"{CONDITION}.csv")
    target_figure, target_axes = plt.subplots(1, 2, figsize=(8.2, 3.8))
    target_specs = (
        (
            np.asarray([float(row["volume_factor"]) for row in target_rows]).reshape(5, 5),
            "a  Doubled V₀ / parent mean V₀",
        ),
        (
            np.asarray([float(row["area_factor"]) for row in target_rows]).reshape(5, 5),
            "b  Scaled A₀ / parent mean A₀",
        ),
    )
    for axis, (values, title) in zip(target_axes, target_specs, strict=True):
        image = axis.imshow(values, cmap="RdBu_r")
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
        "Applied frozen targets (q preserved cell by cell)",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    target_figure.subplots_adjust(
        left=0.08, right=0.94, bottom=0.10, top=0.84, wspace=0.28
    )
    all_paths.extend(
        _save_scientific_layout(
            target_figure,
            figures / "failure_applied_target_maps",
            reason="The applied 5x5 target matrices are frozen inputs to the failed run.",
        )
    )
    plt.close(target_figure)

    combined_pressure = np.concatenate(
        [
            np.asarray(
                [
                    float(row["internal_pressure"])
                    for cell in collection
                    for row in cell["rows"]
                ]
            )
            for collection in (parent_cells, initial_cells)
        ]
    )
    combined_contact = np.concatenate(
        [
            np.asarray(
                [
                    float(row["contact_traction"])
                    for cell in collection
                    for row in cell["rows"]
                ]
            )
            for collection in (parent_cells, initial_cells)
        ]
    )
    field_figure, field_axes = plt.subplots(2, 2, figsize=(9.2, 6.8))
    pressure_norm = _field_normalizer(combined_pressure, signed=True)
    contact_norm = _field_normalizer(combined_contact, signed=False)
    for column, (cells, bounds, label) in enumerate(
        zip(
            (parent_cells, initial_cells),
            (_state_bounds(parent_states[-1]), _state_bounds(states[0])),
            ("Parent final", "Doubled-target state 0"),
            strict=True,
        )
    ):
        pressure_collection = _draw_shared_field(
            field_axes[0, column],
            cells,
            bounds,
            "internal_pressure",
            f"{chr(97 + column)}  {label} | pressure",
            normalizer=pressure_norm,
            cmap="coolwarm",
        )
        contact_collection = _draw_shared_field(
            field_axes[1, column],
            cells,
            bounds,
            "contact_traction",
            f"{chr(99 + column)}  {label} | contact traction",
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
        "Retained true-mesh fields; doubled-target panel is state 0, not a final result",
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
            figures / "failure_state0_pressure_contact_fields",
            reason="Only the true retained state 0 can be compared with the completed parent fields.",
        )
    )
    plt.close(field_figure)

    audits = _read_csv(raw / "step_audits.csv")
    audit_figure, audit_axes = plt.subplots(2, 2, figsize=(8.8, 6.8))
    audit_specs = (
        ("max_free_force", "max nodal force", True),
        ("max_initial_volume_relative_change", "max volume change from initial", False),
        ("contact_active_cell_pairs", "active cell pairs", False),
        ("min_wall_clearance", "minimum wall clearance", False),
    )
    coordinates = np.asarray([float(row["coordinate"]) for row in audits])
    for axis, (field, ylabel, logarithmic) in zip(
        audit_axes.flat, audit_specs, strict=True
    ):
        values = np.asarray([float(row[field]) for row in audits])
        if logarithmic:
            axis.semilogy(coordinates, np.maximum(values, 1.0e-16), "o-", color="#C95855")
        else:
            axis.plot(coordinates, values, "o-", color="#C95855")
        axis.set_xlabel("accepted algorithmic coordinate")
        axis.set_ylabel(ylabel)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=GRID, lw=0.55)
    audit_figure.suptitle(
        "Accepted substeps before positive-gap barrier failure",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    audit_figure.subplots_adjust(
        left=0.11, right=0.96, bottom=0.09, top=0.89, wspace=0.32, hspace=0.36
    )
    all_paths.extend(
        _save_scientific_layout(
            audit_figure,
            figures / "failure_substep_diagnostics",
            reason="Four pre-failure numerical diagnostics are shown without extrapolating a missing final state.",
        )
    )
    plt.close(audit_figure)

    manifest = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-VOLUME-X2-A",
        "status": "passed",
        "stage_outcome": "failed_before_solver_state_1",
        "source": "one retained solver state and four accepted substep audits plus retained parent baseline",
        "saved_state_count": len(states),
        "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physiological_time",
        "files": [str(path.relative_to(result).as_posix()) for path in all_paths],
        "quantitative_style_manifests": [],
        "spatial_layout_exceptions": [
            "failure_structure_state0",
            "failure_applied_target_maps",
            "failure_state0_pressure_contact_fields",
            "failure_substep_diagnostics",
        ],
    }
    (figures / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def render_myocardial_crowded_volume_x2(result: Path) -> dict[str, object]:
    result = result.resolve(strict=True)
    root = result.parents[2]
    configuration = json.loads(
        (result / "configuration.json").read_text(encoding="utf-8")
    )
    parent = root / configuration["parent_result"]
    figures = result / "figures"
    figures.mkdir(exist_ok=True)
    _style()

    raw = result / "raw" / CONDITION
    parent_raw = parent / "raw" / PARENT_CONDITION
    states = sorted(
        _read_csv(raw / "state_metrics.csv"),
        key=lambda row: int(row["snapshot_index"]),
    )
    nodes = _read_csv(raw / "nodes.csv")
    faces = _read_csv(raw / "faces.csv")
    parent_states = sorted(
        _read_csv(parent_raw / "state_metrics.csv"),
        key=lambda row: int(row["snapshot_index"]),
    )
    parent_nodes = _read_csv(parent_raw / "nodes.csv")
    parent_faces = _read_csv(parent_raw / "faces.csv")
    snapshots = sorted({int(row["snapshot_index"]) for row in nodes})
    final_snapshot = snapshots[-1]
    midpoint_snapshot = snapshots[len(snapshots) // 2]
    initial_cells = _snapshot_cells(nodes, faces, snapshots[0])
    midpoint_cells = _snapshot_cells(nodes, faces, midpoint_snapshot)
    final_cells = _snapshot_cells(nodes, faces, final_snapshot)
    parent_final_snapshot = max(int(row["snapshot_index"]) for row in parent_nodes)
    parent_final_cells = _snapshot_cells(
        parent_nodes, parent_faces, parent_final_snapshot
    )
    if len(states) != 9 or not (raw / "kernel_metrics.json").is_file():
        return _render_failure_package(
            result,
            figures,
            raw,
            states,
            nodes,
            faces,
            parent_states,
            parent_nodes,
            parent_faces,
        )

    all_paths: list[Path] = []
    structure = plt.figure(figsize=(15.4, 4.7))
    structure_specs = (
        (
            initial_cells,
            _state_bounds(states[0]),
            "a  2× target | state 0",
        ),
        (
            midpoint_cells,
            _state_bounds(states[len(states) // 2]),
            f"b  2× target | state {midpoint_snapshot}",
        ),
        (
            final_cells,
            _state_bounds(states[-1]),
            f"c  2× target | final state {final_snapshot}",
        ),
        (
            parent_final_cells,
            _state_bounds(parent_states[-1]),
            "d  Parent heterogeneous target | final",
        ),
    )
    for panel, (cells, bounds, title) in enumerate(structure_specs, start=1):
        axis = structure.add_subplot(1, 4, panel, projection="3d")
        _draw_structure_3d(axis, cells, bounds, title)
    structure.suptitle(
        "True 5×5 cardiomyocyte meshes under doubled heterogeneous volume targets",
        fontsize=11.5,
        fontweight="bold",
        y=0.98,
    )
    structure.subplots_adjust(
        left=0.018, right=0.988, bottom=0.06, top=0.87, wspace=0.08
    )
    all_paths.extend(
        _save_scientific_layout(
            structure,
            figures / "model_structure_volume_x2",
            reason=(
                "True 3D triangulated states and the retained baseline require a "
                "four-panel transparent-box layout."
            ),
        )
    )
    plt.close(structure)

    parent_targets = _read_csv(parent / "targets/HETEROGENEOUS_TARGETS.csv")
    targets = _read_csv(result / "targets" / f"{CONDITION}.csv")
    target_figure, target_axes = plt.subplots(2, 2, figsize=(8.4, 7.0))
    target_specs = (
        (
            np.asarray([float(row["volume_factor"]) for row in parent_targets]).reshape(5, 5),
            "a  Parent V₀ / parent mean V₀",
            0.94,
            1.06,
        ),
        (
            np.asarray([float(row["volume_factor"]) for row in targets]).reshape(5, 5),
            "b  Doubled V₀ / parent mean V₀",
            1.88,
            2.12,
        ),
        (
            np.asarray([float(row["area_factor"]) for row in parent_targets]).reshape(5, 5),
            "c  Parent A₀ / parent mean A₀",
            0.94,
            1.06,
        ),
        (
            np.asarray([float(row["area_factor"]) for row in targets]).reshape(5, 5),
            "d  Scaled A₀ / parent mean A₀",
            1.49,
            1.68,
        ),
    )
    for axis, (values, title, lower, upper) in zip(
        target_axes.flat, target_specs, strict=True
    ):
        image = axis.imshow(values, cmap="RdBu_r", vmin=lower, vmax=upper)
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
        "Frozen target maps: V₀ × 2 and A₀ × 2²ᐟ³ preserve each cell's q",
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
            figures / "reference_target_maps_volume_x2",
            reason="Frozen 5x5 target matrices require discrete spatial heat maps.",
        )
    )
    plt.close(target_figure)

    combined_pressure = np.concatenate(
        [
            np.asarray(
                [
                    float(row["internal_pressure"])
                    for cell in collection
                    for row in cell["rows"]
                ]
            )
            for collection in (parent_final_cells, final_cells)
        ]
    )
    combined_contact = np.concatenate(
        [
            np.asarray(
                [
                    float(row["contact_traction"])
                    for cell in collection
                    for row in cell["rows"]
                ]
            )
            for collection in (parent_final_cells, final_cells)
        ]
    )
    field_figure, field_axes = plt.subplots(2, 2, figsize=(9.2, 6.8))
    pressure_norm = _field_normalizer(combined_pressure, signed=True)
    contact_norm = _field_normalizer(combined_contact, signed=False)
    collections = (parent_final_cells, final_cells)
    state_bounds = (_state_bounds(parent_states[-1]), _state_bounds(states[-1]))
    labels = ("Parent heterogeneous target", "2× volume target")
    for column, (cells, bounds, label) in enumerate(
        zip(collections, state_bounds, labels, strict=True)
    ):
        pressure_collection = _draw_shared_field(
            field_axes[0, column],
            cells,
            bounds,
            "internal_pressure",
            f"{chr(97 + column)}  {label} | pressure",
            normalizer=pressure_norm,
            cmap="coolwarm",
        )
        contact_collection = _draw_shared_field(
            field_axes[1, column],
            cells,
            bounds,
            "contact_traction",
            f"{chr(99 + column)}  {label} | contact traction",
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
        "Final true-mesh fields; color scales are shared within each row",
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
            figures / "baseline_vs_x2_pressure_contact_fields",
            reason="True surface fields require equal-aspect panels and shared colorbars.",
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
    series = (
        (parent_states, "Parent", "#2474A6"),
        (states, "2× volume target", "#C95855"),
    )
    for axis, (field, ylabel, logarithmic) in zip(
        progress_axes.flat, progress_specs, strict=True
    ):
        for rows, label, color in series:
            coordinates = np.asarray([float(row["coordinate"]) for row in rows])
            values = np.asarray([float(row[field]) for row in rows])
            if logarithmic:
                axis.semilogy(
                    coordinates,
                    np.maximum(values, 1.0e-16),
                    "o-",
                    color=color,
                    lw=1.35,
                    ms=3.8,
                    label=label,
                )
            else:
                axis.plot(
                    coordinates,
                    values,
                    "o-",
                    color=color,
                    lw=1.35,
                    ms=3.8,
                    label=label,
                )
        axis.set_xlabel("algorithmic loading / relaxation coordinate")
        axis.set_ylabel(ylabel)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=GRID, lw=0.55)
    progress_axes[0, 0].axhline(1.0e-3, color="#8F2F2B", ls="--", lw=1.0)
    progress_axes[0, 0].legend(frameon=False, fontsize=7.0)
    progress_figure.suptitle(
        "Algorithmic progress; coordinate is not physiological time",
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
            figures / "baseline_vs_x2_algorithmic_progress",
            reason="Four coupled solver diagnostics require a compact engineering view.",
        )
    )
    plt.close(progress_figure)

    baseline_final = _final_rows(parent_raw / "cell_metrics.csv")
    doubled_final = _final_rows(raw / "cell_metrics.csv")
    paired_specs = (
        ("pressure", "Final intracellular pressure"),
        ("volume", "Final cell volume"),
        ("x_span", "Final long-axis span"),
        ("mean_contact_traction", "Final mean contact traction"),
    )
    quantitative_manifests: list[str] = []
    for metric, ylabel in paired_specs:
        exported = _paired_figure(
            figures, metric, ylabel, baseline_final, doubled_final
        )
        all_paths.extend(exported)
        quantitative_manifests.append(exported[-1].name)

    manifest = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-VOLUME-X2-A",
        "status": "passed",
        "source": "one retained nine-state doubled-target sequence plus retained parent baseline",
        "coordinate_semantics": (
            "algorithmic_loading_and_relaxation_not_physiological_time"
        ),
        "files": [str(path.relative_to(result).as_posix()) for path in all_paths],
        "quantitative_style_manifests": quantitative_manifests,
        "spatial_layout_exceptions": [
            "model_structure_volume_x2",
            "reference_target_maps_volume_x2",
            "baseline_vs_x2_pressure_contact_fields",
            "baseline_vs_x2_algorithmic_progress",
        ],
    }
    (figures / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
