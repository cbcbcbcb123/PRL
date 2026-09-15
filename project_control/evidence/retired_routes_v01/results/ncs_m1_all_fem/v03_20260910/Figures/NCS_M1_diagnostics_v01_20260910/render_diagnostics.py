from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, FixedLocator, LogLocator
import numpy as np


REVISION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ncs_m1.baseline import build_annulus_system, build_flat_system  # noqa: E402


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_npz(relative: str) -> dict[str, np.ndarray]:
    path = PROJECT_ROOT / relative
    with np.load(path, allow_pickle=False) as payload:
        return {key: payload[key] for key in payload.files}


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))


STYLE_MODULE = load_module(REVISION_DIR / "cb_plot_unified_style.py", "ncs_m1_cb_style")
STYLE = STYLE_MODULE.StyleSpec(axis_box_size_in=(10.0, 5.0))
OVERRIDES: list[Any] = []


def base_axis(xlabel: str, ylabel: str):
    canvas_width = 14.8
    canvas_height = 8.1
    figure = plt.figure(figsize=(canvas_width, canvas_height), facecolor="white")
    axis = figure.add_axes(
        [3.3 / canvas_width, 1.65 / canvas_height, 10.0 / canvas_width, 5.0 / canvas_height]
    )
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.xaxis.set_minor_locator(AutoMinorLocator())
    axis.yaxis.set_minor_locator(AutoMinorLocator())
    STYLE_MODULE.apply_axes_style(axis, style=STYLE)
    return figure, axis


def export(figure: Any, axis: Any, stem: str) -> dict[str, str]:
    output = STYLE_MODULE.export_figure(
        figure, axis, REVISION_DIR / stem, style=STYLE, overrides=OVERRIDES
    )
    plt.close(figure)
    return {
        "png": str(output.png),
        "svg": str(output.svg),
        "manifest": str(output.manifest),
    }


def response_figure() -> dict[str, str]:
    uniform = load_npz("results/ncs_m1_all_fem/v02_20260910/m1a/U-G2-T256_data.npz")
    heterogeneous = load_npz("results/ncs_m1_all_fem/v02_20260910/m1a/H-G2-T256_data.npz")
    figure, axis = base_axis("Cycle phase", "Macroscopic axial strain (%)")
    time = uniform["time"]
    uniform_signal = uniform["layer_strain"][:, 1, 0]
    heterogeneous_signal = heterogeneous["local_values"][:, 0, 0]
    axis.plot(time, 100.0 * uniform_signal, color="#2166AC", linewidth=3.0)
    axis.plot(time, 100.0 * heterogeneous_signal, color="#B2182B", linewidth=3.0)
    axis.set_xlim(0.0, 1.0)
    axis.text(0.66, 100.0 * uniform_signal[-87], "U: ECM mean", color="#2166AC")
    axis.text(0.72, 100.0 * heterogeneous_signal[-72], "H: local ECM", color="#B2182B")
    STYLE_MODULE.add_top_information(
        axis, "M1a v02 | G2, Nt = 256 | final periodic cycle", style=STYLE
    )
    return export(figure, axis, "01_flat_U_H_response")


def convergence_figure() -> dict[str, str]:
    m1a = load_json("results/ncs_m1_all_fem/v02_20260910/m1a/summary.json")
    m1b = load_json("results/ncs_m1_all_fem/v03_20260910/m1b/summary.json")
    figure, axis = base_axis("Resolution transition", "Normalized error")
    flat_raw = [
        m1a["gates"]["spatial_H"]["readouts"]["local_0_0"]["g0_g1"],
        m1a["gates"]["spatial_H"]["readouts"]["local_0_0"]["g1_g2"],
    ]
    flat_values = [max(value, 1.0e-6) for value in flat_raw]
    ring_values = [
        m1b["gates"]["spatial"]["readouts"]["inner_radial"]["g0_g1"],
        m1b["gates"]["spatial"]["readouts"]["inner_radial"]["g1_g2"],
    ]
    x = np.arange(2)
    axis.semilogy(x, flat_values, marker="o", markersize=10, linewidth=3.0, color="#2166AC")
    axis.semilogy(x, ring_values, marker="s", markersize=10, linewidth=3.0, color="#B2182B")
    axis.set_xticks(x, ["G0→G1", "G1→G2"])
    axis.set_xlim(-0.15, 1.55)
    axis.set_ylim(1.0e-6, 1.0e-2)
    axis.yaxis.set_major_locator(FixedLocator([1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2]))
    axis.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(2.0, 5.0)))
    axis.text(
        0.96,
        0.72,
        "Annulus: inner uᵣ",
        color="#B2182B",
        ha="right",
        transform=axis.transAxes,
    )
    axis.text(
        0.96,
        0.63,
        "Flat H: local εₓₓ",
        color="#2166AC",
        ha="right",
        transform=axis.transAxes,
    )
    STYLE_MODULE.add_top_information(
        axis, "Frozen spatial gates | polygon error included", style=STYLE
    )
    return export(figure, axis, "02_spatial_convergence")


def ledger_figure() -> dict[str, str]:
    annulus = load_npz("results/ncs_m1_all_fem/v03_20260910/m1b/R-G2-T256_data.npz")
    nt = len(annulus["active_work_steps"])
    phase = np.arange(nt + 1) / nt
    active = np.concatenate([[0.0], np.cumsum(annulus["active_work_steps"])])
    dissipation = np.concatenate([[0.0], np.cumsum(annulus["dissipation_steps"])])
    residual = np.concatenate([[0.0], np.cumsum(annulus["energy_residual_steps"])])
    figure, axis = base_axis("Cycle phase", "Cumulative work / energy")
    axis.plot(phase, active, color="#B2182B", linewidth=3.0, label="Active input")
    axis.plot(phase, dissipation, color="#238B8D", linewidth=3.0, label="Maxwell dissipation")
    axis.plot(phase, residual, color="#303030", linewidth=3.0, label="Residual")
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.40 * max(float(np.max(active)), float(np.max(dissipation))))
    axis.legend(loc="upper right", frameon=False)
    STYLE_MODULE.add_top_information(
        axis, "M1b v03 | G2, Nt = 256 | discrete midpoint ledger", style=STYLE
    )
    return export(figure, axis, "03_annulus_energy_ledger")


def geometry_figure() -> dict[str, str]:
    flat = build_flat_system("G2", "H")
    flat_data = load_npz("results/ncs_m1_all_fem/v02_20260910/m1a/H-G2-T256_data.npz")
    ring = build_annulus_system("G2")
    ring_data = load_npz("results/ncs_m1_all_fem/v03_20260910/m1b/R-G2-F_data.npz")
    multiplier = 20.0
    flat_deformed = flat.coordinates + multiplier * np.real(flat_data["displacement_harmonic"])
    ring_deformed = ring.coordinates + multiplier * np.real(ring_data["displacement_harmonic"])
    ring_shift = np.asarray([2.0, 0.25])
    figure, axis = base_axis("x / L", "y / L")
    flat_nx = flat.level.nx
    flat_rows = flat.level.ny_myo + flat.level.ny_ecm + flat.level.ny_endo + 1
    for row in (0, flat.level.ny_myo, flat.level.ny_myo + flat.level.ny_ecm, flat_rows - 1):
        nodes = row * (flat_nx + 1) + np.arange(flat_nx + 1)
        axis.plot(flat_deformed[nodes, 0], flat_deformed[nodes, 1], color="#2166AC", linewidth=1.5)
    for column in range(0, flat_nx + 1, 8):
        nodes = column + np.arange(flat_rows) * (flat_nx + 1)
        axis.plot(flat_deformed[nodes, 0], flat_deformed[nodes, 1], color="#2166AC", linewidth=0.8)
    ring_ntheta = ring.level.ntheta
    ring_rows = ring.level.nr_endo + ring.level.nr_ecm + ring.level.nr_myo + 1
    for row in (0, ring.level.nr_endo, ring.level.nr_endo + ring.level.nr_ecm, ring_rows - 1):
        nodes = row * ring_ntheta + np.arange(ring_ntheta)
        closed = np.append(nodes, nodes[0])
        axis.plot(
            ring_deformed[closed, 0] + ring_shift[0],
            ring_deformed[closed, 1] + ring_shift[1],
            color="#B2182B",
            linewidth=1.5,
        )
    for column in range(0, ring_ntheta, 8):
        nodes = column + np.arange(ring_rows) * ring_ntheta
        axis.plot(
            ring_deformed[nodes, 0] + ring_shift[0],
            ring_deformed[nodes, 1] + ring_shift[1],
            color="#B2182B",
            linewidth=0.8,
        )
    axis.text(-0.45, 0.68, "Flat H", color="#2166AC")
    axis.text(2.75, 1.76, "Annulus", color="#B2182B", ha="center")
    axis.set_xlim(-2.2, 5.2)
    axis.set_ylim(-1.6, 2.1)
    axis.set_xticks([-2.0, 0.0, 2.0, 4.0])
    axis.set_yticks([-1.0, 0.0, 1.0, 2.0])
    STYLE_MODULE.add_top_information(
        axis, "Harmonic displacement ×20 (visual multiplier)", style=STYLE
    )
    return export(figure, axis, "04_model_and_deformation_x20")


def main() -> None:
    outputs = {
        "response": response_figure(),
        "convergence": convergence_figure(),
        "ledger": ledger_figure(),
        "geometry": geometry_figure(),
    }
    inputs = [
        "results/ncs_m1_all_fem/v02_20260910/m1a/U-G2-T256_data.npz",
        "results/ncs_m1_all_fem/v02_20260910/m1a/H-G2-T256_data.npz",
        "results/ncs_m1_all_fem/v02_20260910/m1a/summary.json",
        "results/ncs_m1_all_fem/v03_20260910/m1b/R-G2-T256_data.npz",
        "results/ncs_m1_all_fem/v03_20260910/m1b/R-G2-F_data.npz",
        "results/ncs_m1_all_fem/v03_20260910/m1b/summary.json",
    ]
    payload = {
        "status": "passed",
        "figure_role": "diagnostic_display_not_publication_figure",
        "axis_box_size_in": [10.0, 5.0],
        "deformation_multiplier": 20.0,
        "inputs": {relative: sha256(PROJECT_ROOT / relative) for relative in inputs},
        "outputs": outputs,
    }
    (REVISION_DIR / "figure_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
