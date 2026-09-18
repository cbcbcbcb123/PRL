"""Render a preserved mixed-tangent failure without running a solver.

The F6-S1-S diagnostic assembled and saved ``matrix_csr.npz`` before its
JSON report failed on a non-finite value.  This module deliberately limits
itself to read-only sparse-matrix summaries and figure export.  In
particular, it does not reconstruct or repeat the lost KSP/MUMPS solve.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import sparse


_REQUIRED_ARRAYS = {
    "indptr",
    "indices",
    "data",
    "rhs",
    "residual",
    "displacement",
    "pressure",
    "pressure_cells",
}


def load_saved_matrix(path: str | Path) -> tuple[sparse.csr_matrix, dict[str, np.ndarray]]:
    """Load and validate the create-only CSR evidence package."""

    source = Path(path)
    with np.load(source, allow_pickle=False) as archive:
        missing = _REQUIRED_ARRAYS.difference(archive.files)
        if missing:
            raise ValueError(f"Saved tangent is missing arrays: {sorted(missing)}")
        arrays = {name: np.asarray(archive[name]) for name in archive.files}

    residual = np.asarray(arrays["residual"], dtype=float)
    size = residual.size
    matrix = sparse.csr_matrix(
        (
            np.asarray(arrays["data"], dtype=float),
            np.asarray(arrays["indices"], dtype=np.int64),
            np.asarray(arrays["indptr"], dtype=np.int64),
        ),
        shape=(size, size),
    )
    if arrays["rhs"].shape != residual.shape:
        raise ValueError("Saved right-hand side and residual have different shapes")
    if not np.all(np.isfinite(matrix.data)) or not np.all(np.isfinite(residual)):
        raise ValueError("Saved tangent or residual contains a non-finite value")
    return matrix, arrays


def matrix_diagnostics(
    matrix: sparse.csr_matrix,
    displacement: np.ndarray,
    pressure: np.ndarray,
    pressure_cells: np.ndarray,
    *,
    sparsity_bins: int = 256,
) -> dict[str, object]:
    """Compute plotting summaries only; no global solve or factorization."""

    matrix = sparse.csr_matrix(matrix)
    displacement = np.asarray(displacement, dtype=np.int64).ravel()
    pressure = np.asarray(pressure, dtype=np.int64).ravel()
    pressure_cells = np.asarray(pressure_cells, dtype=np.int64)
    size = matrix.shape[0]
    if matrix.shape != (size, size):
        raise ValueError("Expected a square mixed tangent")
    ordering = np.concatenate((displacement, pressure))
    if ordering.size != size or not np.array_equal(np.sort(ordering), np.arange(size)):
        raise ValueError("Displacement and pressure maps must partition the tangent")
    if pressure_cells.ndim != 2 or pressure_cells.shape[0] == 0:
        raise ValueError("Expected a non-empty two-dimensional pressure-cell map")
    if not np.all(np.isin(pressure_cells, pressure)):
        raise ValueError("Pressure-cell map contains a non-pressure degree of freedom")

    inverse_order = np.empty(size, dtype=np.int64)
    inverse_order[ordering] = np.arange(size, dtype=np.int64)
    coo = matrix.tocoo(copy=False)
    nonzero = np.asarray(coo.data) != 0
    bin_count = min(max(int(sparsity_bins), 8), size)
    rows = inverse_order[np.asarray(coo.row)[nonzero]] * bin_count // size
    columns = inverse_order[np.asarray(coo.col)[nonzero]] * bin_count // size
    occupancy = np.zeros((bin_count, bin_count), dtype=np.int64)
    np.add.at(occupancy, (rows, columns), 1)

    row_norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
    diagonal = np.abs(matrix.diagonal())
    cell_singular_values = np.empty(pressure_cells.shape, dtype=float)
    for index, cell_dofs in enumerate(pressure_cells):
        local = matrix[cell_dofs][:, cell_dofs].toarray()
        cell_singular_values[index] = np.linalg.svd(local, compute_uv=False)

    if not np.all(np.isfinite(cell_singular_values)):
        raise ValueError("A pressure-cell singular value is non-finite")
    return {
        "occupancy": occupancy,
        "row_norms": row_norms,
        "diagonal": diagonal,
        "pressure_cell_singular_values": cell_singular_values,
        "size": int(size),
        "stored_terms": int(matrix.nnz),
        "numerical_nonzeros": int(np.count_nonzero(matrix.data)),
        "displacement_dofs": int(displacement.size),
        "pressure_dofs": int(pressure.size),
        "pressure_cells": int(pressure_cells.shape[0]),
        "pressure_modes_per_cell": int(pressure_cells.shape[1]),
        "zero_rows": int(np.count_nonzero(row_norms == 0)),
        "zero_diagonal_entries": int(np.count_nonzero(diagonal == 0)),
    }


def _load_failure_status(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    failure = json.loads((root / "failure.json").read_text(encoding="utf-8"))
    execution = json.loads((root / "execution.json").read_text(encoding="utf-8"))
    error = failure.get("error", {})
    serialization_failure = (
        failure.get("status") == "failed"
        and error.get("type") == "ValueError"
        and "Out of range float values are not JSON compliant: inf"
        in str(error.get("message", ""))
    )
    if not serialization_failure:
        raise ValueError("This renderer is specific to the retained JSON-inf failure")
    if execution.get("nonlinear_equilibrium_solves") != 0:
        raise ValueError("Execution record does not certify zero equilibrium solves")
    return failure, execution


def _positive_sorted(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    positive = np.sort(np.asarray(values, dtype=float)[np.asarray(values) > 0])
    if positive.size == 0:
        raise ValueError("Expected at least one positive matrix scale")
    percentile = np.linspace(0.0, 100.0, positive.size)
    return percentile, positive


def render(
    result_root: str | Path,
    png_path: str | Path | None = None,
    svg_path: str | Path | None = None,
    *,
    dpi: int = 300,
) -> dict[str, object]:
    """Export the honest 2x2 F6-S1-S diagnostic from saved evidence only."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    root = Path(result_root).resolve(strict=True)
    _failure, execution = _load_failure_status(root)
    matrix, arrays = load_saved_matrix(root / "matrix_csr.npz")
    diagnostics = matrix_diagnostics(
        matrix,
        arrays["displacement"],
        arrays["pressure"],
        arrays["pressure_cells"],
    )

    if png_path is None:
        png_path = root / "figures" / "FigS1S_linear_system_diagnosis_v02_20260918.png"
    if svg_path is None:
        svg_path = root / "figures" / "FigS1S_linear_system_diagnosis_v02_20260918.svg"
    png = Path(png_path)
    svg = Path(svg_path)
    if png.exists() or svg.exists():
        raise FileExistsError("Diagnostic figure export is create-only")
    png.parent.mkdir(parents=True, exist_ok=True)
    svg.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(2, 2, figsize=(13.2, 10.2), constrained_layout=True)
    panel_a, panel_b, panel_c, panel_d = axes.ravel()

    occupancy = np.asarray(diagnostics["occupancy"])
    occupied_values = occupancy[occupancy > 0]
    upper = int(occupied_values.max()) if occupied_values.size else 1
    panel_a.imshow(
        np.ma.masked_equal(occupancy, 0),
        origin="upper",
        interpolation="nearest",
        cmap="magma",
        norm=LogNorm(vmin=1, vmax=max(upper, 1)),
        aspect="equal",
    )
    boundary = (
        diagnostics["displacement_dofs"] / diagnostics["size"] * occupancy.shape[0]
        - 0.5
    )
    panel_a.axhline(boundary, color="#1F78B4", linewidth=1.3, linestyle="--")
    panel_a.axvline(boundary, color="#1F78B4", linewidth=1.3, linestyle="--")
    ticks = [0, boundary, occupancy.shape[0] - 1]
    labels = ["0", f"u={diagnostics['displacement_dofs']}", f"n={diagnostics['size']}"]
    panel_a.set_xticks(ticks, labels)
    panel_a.set_yticks(ticks, labels)
    panel_a.set_xlabel("column DOF after [u, p] reordering")
    panel_a.set_ylabel("row DOF after [u, p] reordering")
    panel_a.set_title("A  Downsampled mixed-tangent sparsity")
    panel_a.text(
        0.02,
        0.02,
        "color = log-scaled stored terms per bin",
        transform=panel_a.transAxes,
        fontsize=9,
        color="#333333",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85},
    )

    row_x, row_y = _positive_sorted(np.asarray(diagnostics["row_norms"]))
    diagonal_x, diagonal_y = _positive_sorted(np.asarray(diagnostics["diagonal"]))
    panel_b.plot(row_x, row_y, color="#1F78B4", linewidth=2.0, label=r"row $\ell_2$ norm")
    panel_b.plot(
        diagonal_x,
        diagonal_y,
        color="#E66101",
        linewidth=2.0,
        label=r"$|A_{ii}|$ (nonzero)",
    )
    panel_b.set_yscale("log")
    panel_b.set_xlabel("empirical percentile (%)")
    panel_b.set_ylabel("matrix scale")
    panel_b.set_title("B  Row and diagonal scales")
    panel_b.legend(frameon=False, loc="best")
    panel_b.text(
        0.03,
        0.05,
        f"zero rows = {diagnostics['zero_rows']}\n"
        f"zero diagonals = {diagnostics['zero_diagonal_entries']}",
        transform=panel_b.transAxes,
        fontsize=10,
        va="bottom",
    )

    singular_values = np.asarray(diagnostics["pressure_cell_singular_values"])
    mode = np.arange(1, singular_values.shape[1] + 1)
    q05, median, q95 = np.percentile(singular_values, [5, 50, 95], axis=0)
    panel_c.fill_between(mode, q05, q95, color="#7FCDBB", alpha=0.55, label="cellwise 5-95%")
    panel_c.plot(mode, median, "o-", color="#006D5B", linewidth=2.0, label="cellwise median")
    panel_c.set_yscale("log")
    panel_c.set_xticks(mode)
    panel_c.set_xlabel("local DG2 pressure mode (largest to smallest)")
    panel_c.set_ylabel("singular value of local p-p block")
    panel_c.set_title("C  Finite-bulk pressure-block spectrum")
    panel_c.legend(frameon=False, loc="best")
    panel_c.text(
        0.03,
        0.05,
        f"{diagnostics['pressure_cells']} cells; "
        f"min = {singular_values.min():.3e}\n"
        "Local spectra do not establish global stability.",
        transform=panel_c.transAxes,
        fontsize=10,
        va="bottom",
    )

    residual_norm = float(np.linalg.norm(np.asarray(arrays["residual"], dtype=float)))
    status_lines = [
        "F6-S1-S STATUS",
        "",
        "Engineering package: FAILED",
        "Failure stage: diagnosis.json serialization",
        "Saved tangent: AVAILABLE",
        f"Shape / stored terms: {diagnostics['size']:,} x {diagnostics['size']:,}",
        f"                         {diagnostics['stored_terms']:,}",
        f"Saved residual norm: {residual_norm:.6e}",
        "",
        "Nonlinear equilibrium solves: 0",
        "Newton state updates: 0",
        "MUMPS/KSP details: NOT RETAINED",
        "Reason: non-finite `inf` rejected by JSON",
        "",
        "Scientific status: DG2 equilibrium remains FAILED",
        "Root cause: UNKNOWN from this preserved package",
    ]
    panel_d.axis("off")
    panel_d.set_title("D  Evidence boundary")
    panel_d.text(
        0.03,
        0.97,
        "\n".join(status_lines),
        transform=panel_d.transAxes,
        va="top",
        ha="left",
        fontsize=11.5,
        family="monospace",
        linespacing=1.35,
        bbox={"boxstyle": "round,pad=0.8", "facecolor": "#F5F5F5", "edgecolor": "#888888"},
    )

    for axis in (panel_a, panel_b, panel_c):
        axis.tick_params(direction="out", width=1.0, length=4)
        for spine in axis.spines.values():
            spine.set_linewidth(1.0)
    figure.suptitle(
        "Saved P2/DG2 mixed tangent at the first pressured initial state",
        fontsize=17,
    )
    figure.savefig(png, dpi=dpi, facecolor="white", edgecolor="white")
    figure.savefig(svg, format="svg", facecolor="white", edgecolor="white")
    plt.close(figure)

    return {
        "status": "passed",
        "scientific_status": "failed",
        "root_cause": "unknown_due_to_unretained_mumps_details",
        "png": str(png.resolve()),
        "svg": str(svg.resolve()),
        "matrix_shape": [diagnostics["size"], diagnostics["size"]],
        "stored_terms": diagnostics["stored_terms"],
        "pressure_cell_minimum_singular_value": float(singular_values.min()),
        "nonlinear_equilibrium_solves": int(execution["nonlinear_equilibrium_solves"]),
        "newton_state_updates": 0,
        "global_solver_or_factorization_during_rendering": 0,
        "local_pressure_block_svd_count": diagnostics["pressure_cells"],
        "mumps_details": "not_retained_due_to_json_inf_serialization_failure",
    }
