"""Render actual saved states from the contact performance/equilibrium task."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from ..runs.contact_performance_equilibrium import RESULT_RELATIVE
from ..workspace import find_workspace


COLORS = ("#2563eb", "#dc2626")


def _read(path: Path) -> np.ndarray:
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_pair(figure: plt.Figure, root: Path, name: str) -> list[Path]:
    outputs = [root / f"{name}.png", root / f"{name}.svg"]
    figure.savefig(outputs[0], dpi=180, bbox_inches="tight", facecolor="white")
    figure.savefig(outputs[1], bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return outputs


def _style(axis: plt.Axes, title: str, x: str, y: str) -> None:
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel(x)
    axis.set_ylabel(y)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.18, linewidth=0.6)


def _render_performance(result: Path, figures: Path) -> list[Path]:
    verdict = _json(result / "Q/verdict.json")
    counts = np.array([2, 4, 16])
    baseline = np.array([verdict["timing_medians_seconds"][str(value)]["baseline"] for value in counts])
    candidate = np.array([verdict["timing_medians_seconds"][str(value)]["candidate"] for value in counts])
    figure, axis = plt.subplots(figsize=(8.4, 5.0), constrained_layout=True)
    positions = np.arange(len(counts))
    axis.bar(positions - 0.18, baseline, width=0.36, color="#94a3b8", label="Frozen baseline")
    axis.bar(positions + 0.18, candidate, width=0.36, color="#2563eb", label="Indexed candidate")
    axis.axhline(6.075, color="#dc2626", linestyle="--", linewidth=1.2, label="16-cell ceiling")
    axis.set_xticks(positions, [str(value) for value in counts])
    _style(axis, f"Q performance gate — {verdict['status'].upper()}", "Cells", "Contact assembly (s)")
    axis.legend(frameon=False)
    axis.text(
        0.99,
        0.97,
        f"16-cell speedup {verdict['sixteen_cell_speedup']:.2f}×\n2-cell ratio {verdict['two_cell_slowdown_ratio']:.3f}",
        transform=axis.transAxes,
        ha="right",
        va="top",
    )
    return _save_pair(figure, figures, "performance_gate")


def _render_structure(result: Path, figures: Path) -> list[Path]:
    figure, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)
    for axis, count in zip(axes, (2, 4, 16), strict=True):
        nodes = _read(result / f"Q/scaling/{count}_cells_candidate_r1/nodes.csv")
        for cell_id in np.unique(nodes["cell"]).astype(int):
            rows = nodes[nodes["cell"] == cell_id]
            axis.scatter(rows["x"], rows["y"], s=2.0, alpha=0.75)
        axis.set_aspect("equal", adjustable="box")
        _style(axis, f"{count} cells", "Long axis x", "Sheet axis y")
    figure.suptitle("Actual meshes used for Q static assembly", fontweight="bold")
    return _save_pair(figure, figures, "model_structure")


def _available_cases(result: Path) -> list[Path]:
    e_root = result / "E"
    if not e_root.is_dir():
        return []
    return [
        e_root / tag
        for tag in ("END_DT0.02", "END_DT0.01", "SIDE_DT0.02", "SIDE_DT0.01")
        if (e_root / tag / "nodes.csv").is_file()
    ]


def _render_equilibrium_series(result: Path, figures: Path, cases: list[Path]) -> list[Path]:
    outputs: list[Path] = []
    figure, axis = plt.subplots(figsize=(8.6, 5.0), constrained_layout=True)
    for case in cases:
        states = _read(case / "states.csv")
        axis.semilogy(states["coordinate"], np.maximum(states["max_free_force"], 1.0e-16), label=case.name)
    axis.axhline(1.0e-3, color="#dc2626", linestyle="--", label="Equilibrium gate")
    _style(axis, "Residual force over algorithmic coordinate", "Algorithmic coordinate", "Maximum free force")
    axis.legend(frameon=False, ncol=2)
    outputs.extend(_save_pair(figure, figures, "residual_vs_coordinate"))

    figure, axes = plt.subplots(1, 3, figsize=(13.8, 4.2), constrained_layout=True)
    for case in cases:
        states = _read(case / "states.csv")
        separation = _read(case / "separation.csv")
        axes[0].plot(separation["coordinate"], separation["intercell_distance"], label=case.name)
        axes[1].plot(states["coordinate"], 100 * states["max_volume_error"], label=case.name)
        axes[2].plot(states["coordinate"], states["min_angle"], label=case.name)
    _style(axes[0], "Surface gap", "Algorithmic coordinate", "Minimum gap")
    _style(axes[1], "Volume conservation", "Algorithmic coordinate", "Maximum error (%)")
    _style(axes[2], "Mesh angle", "Algorithmic coordinate", "Minimum angle (deg)")
    axes[0].axhline(1.0e-8, color="#dc2626", linestyle="--")
    axes[1].axhline(2.0, color="#dc2626", linestyle="--")
    axes[2].axhline(15.0, color="#dc2626", linestyle="--")
    axes[2].legend(frameon=False, fontsize=8)
    outputs.extend(_save_pair(figure, figures, "gap_and_mesh_quality"))
    return outputs


def _render_fields(result: Path, figures: Path, cases: list[Path]) -> list[Path]:
    preferred = [case for case in cases if case.name.endswith("DT0.01")]
    if not preferred:
        preferred = cases[:2]
    figure, axes = plt.subplots(len(preferred), 3, figsize=(13.5, 4.2 * max(1, len(preferred))), squeeze=False, constrained_layout=True)
    for row_index, case in enumerate(preferred):
        nodes = _read(case / "nodes.csv")
        final = nodes[nodes["snapshot"] == np.max(nodes["snapshot"])]
        traction = np.linalg.norm(
            np.column_stack([final[key] for key in ("cfx", "cfy", "cfz")]), axis=1
        ) / np.maximum(final["area"], 1.0e-15)
        values = (final["curvature"], final["pressure"], traction)
        titles = ("Curvature", "Pressure", "Contact traction")
        for column, (value, title) in enumerate(zip(values, titles, strict=True)):
            axis = axes[row_index, column]
            image = axis.scatter(final["x"], final["y"], c=value, s=8, cmap="viridis")
            axis.set_aspect("equal", adjustable="box")
            _style(axis, f"{case.name}: {title}", "x", "y")
            figure.colorbar(image, ax=axis, shrink=0.72)
    return _save_pair(figure, figures, "curvature_pressure_contact_traction")


def _render_gif(case: Path, output: Path) -> None:
    nodes = _read(case / "nodes.csv")
    images: list[Image.Image] = []
    all_x, all_y = nodes["x"], nodes["y"]
    x_margin = max(float(np.ptp(all_x)) * 0.05, 0.1)
    y_margin = max(float(np.ptp(all_y)) * 0.05, 0.1)
    for event in (0, 5, 10, 15, 20):
        snapshot_ids = np.unique(nodes["snapshot"])
        coordinates = np.array(
            [float(nodes[nodes["snapshot"] == snap]["coordinate"][0]) for snap in snapshot_ids]
        )
        snapshot = snapshot_ids[int(np.argmin(abs(coordinates - event)))]
        rows = nodes[nodes["snapshot"] == snapshot]
        figure, axis = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
        for cell_id in (0, 1):
            selected = rows[rows["cell"] == cell_id]
            axis.scatter(selected["x"], selected["y"], s=7, color=COLORS[cell_id], alpha=0.8)
        axis.set_xlim(float(all_x.min()) - x_margin, float(all_x.max()) + x_margin)
        axis.set_ylim(float(all_y.min()) - y_margin, float(all_y.max()) + y_margin)
        axis.set_aspect("equal", adjustable="box")
        _style(axis, f"{case.name} — coordinate {coordinates[int(np.argmin(abs(coordinates-event)))]:.3f}", "x", "y")
        figure.canvas.draw()
        rgba = np.asarray(figure.canvas.buffer_rgba()).copy()
        images.append(Image.fromarray(rgba).convert("P", palette=Image.Palette.ADAPTIVE))
        plt.close(figure)
    images[0].save(output, save_all=True, append_images=images[1:], duration=650, loop=0, optimize=False)


def render_contact_performance_equilibrium(
    workspace: Path | str | None = None, result: Path | str | None = None
) -> dict[str, Any]:
    root = find_workspace(workspace)
    target = root / RESULT_RELATIVE if result is None else Path(result)
    if not target.is_absolute():
        target = root / target
    target = target.resolve(strict=True)
    target.relative_to(root.resolve(strict=True))
    if not (target / "Q/verdict.json").is_file():
        raise ValueError("Q verdict is missing")
    figures = target / "figures"
    if figures.exists():
        raise ValueError(f"create-only figures directory exists: {figures}")
    figures.mkdir()
    outputs = _render_performance(target, figures)
    outputs.extend(_render_structure(target, figures))
    cases = _available_cases(target)
    if cases:
        outputs.extend(_render_equilibrium_series(target, figures, cases))
        outputs.extend(_render_fields(target, figures, cases))
        for direction in ("END", "SIDE"):
            candidates = [case for case in cases if case.name == f"{direction}_DT0.01"]
            if not candidates:
                candidates = [case for case in cases if case.name.startswith(direction)]
            if candidates:
                path = figures / f"{direction.lower()}_five_states.gif"
                _render_gif(candidates[0], path)
                outputs.append(path)
    manifest = {
        "schema_version": "prl.contact_performance_equilibrium.figures.v1",
        "status": "passed",
        "actual_solver_states": True,
        "physiological_time": False,
        "files": [
            {
                "path": path.relative_to(target).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in outputs
        ],
    }
    (figures / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
