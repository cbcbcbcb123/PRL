from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib import cm, colors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402


DEFAULT_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2a_fenicsx_pilot_v02_20260819"
    / "N1_2A_D0_E0_F150_T016"
)


def boundary_faces_with_cells(
    tetrahedra: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    face_specs = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))
    records: dict[tuple[int, int, int], list[object]] = {}
    for cell_id, tetrahedron in enumerate(tetrahedra):
        for local_face in face_specs:
            face = tuple(int(tetrahedron[index]) for index in local_face)
            key = tuple(sorted(face))
            if key in records:
                records[key][2] = int(records[key][2]) + 1
            else:
                records[key] = [face, cell_id, 1]
    boundary = [record for record in records.values() if record[2] == 1]
    return (
        np.asarray([record[0] for record in boundary], dtype=np.int64),
        np.asarray([record[1] for record in boundary], dtype=np.int64),
    )


def tetrahedron_jacobians(
    vertices: np.ndarray,
    tetrahedra: np.ndarray,
    dm_inverse: np.ndarray,
) -> np.ndarray:
    local = vertices[tetrahedra]
    current_edges = np.stack(
        (
            local[:, 1] - local[:, 0],
            local[:, 2] - local[:, 0],
            local[:, 3] - local[:, 0],
        ),
        axis=2,
    )
    deformation = np.einsum("tij,tjk->tik", current_edges, dm_inverse)
    return np.linalg.det(deformation)


def clean_3d_axis(axis, bounds: np.ndarray) -> None:
    centre = bounds.mean(axis=0)
    spans = bounds[1] - bounds[0]
    half = 0.53 * spans
    axis.set_xlim(centre[0] - half[0], centre[0] + half[0])
    axis.set_ylim(centre[1] - half[1], centre[1] + half[1])
    axis.set_zlim(centre[2] - half[2], centre[2] + half[2])
    axis.set_box_aspect(np.maximum(spans, 1.0e-12))
    axis.view_init(elev=22.0, azim=-62.0)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_zticks([])
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_zlabel("z")
    axis.grid(False)
    for local_axis in (axis.xaxis, axis.yaxis, axis.zaxis):
        local_axis.pane.set_alpha(0.0)


def state_montage(
    case_path: Path,
    model,
    timeseries: np.ndarray,
    states: np.lib.npyio.NpzFile,
) -> dict[str, object]:
    selected_steps = (0, 4, 8, 12, 16)
    myocyte_history = np.asarray(states["myocyte_vertices"])
    ecm_history = np.asarray(states["ecm_vertices"])
    endocardial_history = np.asarray(states["endocardial_vertices"])
    boundary_faces, boundary_cells = boundary_faces_with_cells(
        model.ecm_reference.tetrahedra
    )
    selected_jacobians = {
        step: tetrahedron_jacobians(
            ecm_history[step],
            model.ecm_reference.tetrahedra,
            model.ecm_reference.dm_inverse,
        )
        for step in selected_steps
    }
    maximum_deviation = max(
        float(np.max(np.abs(jacobians - 1.0)))
        for jacobians in selected_jacobians.values()
    )
    colour_span = max(0.012, maximum_deviation)
    colour_norm = colors.Normalize(1.0 - colour_span, 1.0 + colour_span)
    colour_map = plt.get_cmap("coolwarm")

    selected_indices = np.asarray(selected_steps, dtype=np.int64)
    all_vertices = np.concatenate(
        (
            myocyte_history[selected_indices].reshape(-1, 3),
            ecm_history[selected_indices].reshape(-1, 3),
            endocardial_history[selected_indices].reshape(-1, 3),
        )
    )
    bounds = np.vstack((all_vertices.min(axis=0), all_vertices.max(axis=0)))
    figure = plt.figure(figsize=(18.0, 4.5), constrained_layout=True)
    axes = [
        figure.add_subplot(1, len(selected_steps), index + 1, projection="3d")
        for index in range(len(selected_steps))
    ]
    phase_names = ("start", "rising", "peak", "falling", "cycle end")
    for axis, step, phase_name in zip(
        axes, selected_steps, phase_names, strict=True
    ):
        ecm_vertices = ecm_history[step]
        face_jacobians = selected_jacobians[step][boundary_cells]
        ecm_collection = Poly3DCollection(
            ecm_vertices[boundary_faces],
            facecolors=colour_map(colour_norm(face_jacobians)),
            edgecolors=(0.32, 0.36, 0.40, 0.26),
            linewidths=0.20,
            alpha=0.24,
        )
        axis.add_collection3d(ecm_collection)
        myocyte_collection = Poly3DCollection(
            myocyte_history[step][model.myocyte.faces],
            facecolors=(0.88, 0.23, 0.12, 0.62),
            edgecolors=(0.55, 0.08, 0.04, 0.28),
            linewidths=0.18,
        )
        endocardial_collection = Poly3DCollection(
            endocardial_history[step][model.endocardium.faces],
            facecolors=(0.08, 0.55, 0.78, 0.56),
            edgecolors=(0.02, 0.27, 0.48, 0.26),
            linewidths=0.18,
        )
        axis.add_collection3d(myocyte_collection)
        axis.add_collection3d(endocardial_collection)
        clean_3d_axis(axis, bounds)
        axis.set_title(
            f"{phase_name}\nt/T={timeseries['t_over_T'][step]:.2f}, "
            f"a={timeseries['activation'][step]:.3f}\n"
            f"shortening={100 * timeseries['axial_shortening'][step]:.1f}%",
            fontsize=10,
            pad=0,
        )
    scalar = cm.ScalarMappable(norm=colour_norm, cmap=colour_map)
    scalar.set_array([])
    colour_bar = figure.colorbar(
        scalar, ax=axes, shrink=0.68, pad=0.015, aspect=25
    )
    colour_bar.set_label("ECM local volume ratio  J = det(F)")
    figure.suptitle(
        "N1-2a: one fully coupled 16-step warmup cycle\n"
        "red = myocyte, translucent field = viscoelastic ECM, blue = endocardium",
        fontsize=14,
    )
    png_path = case_path / "n1_2a_16step_state_montage_v01.png"
    svg_path = case_path / "n1_2a_16step_state_montage_v01.svg"
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    return {
        "selected_steps": list(selected_steps),
        "png": str(png_path),
        "svg": str(svg_path),
        "selected_minimum_j": min(
            float(np.min(value)) for value in selected_jacobians.values()
        ),
        "selected_maximum_j": max(
            float(np.max(value)) for value in selected_jacobians.values()
        ),
    }


def diagnostic_figure(
    case_path: Path, timeseries: np.ndarray
) -> dict[str, object]:
    phase = timeseries["t_over_T"]
    figure, axes = plt.subplots(2, 3, figsize=(15.5, 8.5), constrained_layout=True)

    axis = axes[0, 0]
    axis.plot(phase, timeseries["activation"], color="#a71930", lw=2.0)
    axis.set_ylabel("activation", color="#a71930")
    twin = axis.twinx()
    twin.plot(
        phase,
        100.0 * timeseries["axial_shortening"],
        color="#1565a8",
        lw=2.0,
    )
    twin.set_ylabel("axial shortening (%)", color="#1565a8")
    axis.set_title("command and cell response")

    axis = axes[0, 1]
    axis.plot(
        phase,
        timeseries["maximum_discrete_interface_traction"],
        label="maximum",
        color="#bf4b30",
        lw=2.0,
    )
    axis.plot(
        phase,
        timeseries["p95_discrete_interface_traction"],
        label="p95",
        color="#e69f00",
        lw=1.8,
    )
    axis.set_ylabel("interface traction")
    axis.set_title("load transmission")
    axis.legend(frameon=False)

    axis = axes[0, 2]
    axis.plot(
        phase,
        timeseries["ecm_equilibrium_energy"],
        label="ECM equilibrium",
        color="#287c55",
        lw=2.0,
    )
    axis.plot(
        phase,
        timeseries["ecm_viscoelastic_energy"],
        label="ECM viscoelastic",
        color="#7b4fa3",
        lw=2.0,
    )
    axis.set_ylabel("ECM stored energy")
    axis.set_title("viscoelastic energy storage")
    axis.legend(frameon=False)

    axis = axes[1, 0]
    axis.fill_between(
        phase,
        timeseries["minimum_ecm_jacobian"],
        timeseries["maximum_ecm_jacobian"],
        color="#6a8fb3",
        alpha=0.30,
    )
    axis.plot(
        phase,
        timeseries["minimum_ecm_jacobian"],
        color="#1f5b85",
        lw=1.8,
        label="min J",
    )
    axis.plot(
        phase,
        timeseries["maximum_ecm_jacobian"],
        color="#4d8db7",
        lw=1.8,
        label="max J",
    )
    axis.axhline(1.0, color="0.3", lw=0.8, ls="--")
    axis.set_ylabel("J = det(F)")
    axis.set_title("ECM volume redistribution")
    axis.legend(frameon=False)

    axis = axes[1, 1]
    kkt = np.maximum(timeseries["normalized_kkt_residual"], 1.0e-16)
    coupling = np.maximum(timeseries["coupling_residual"], 1.0e-16)
    axis.semilogy(phase, kkt, label="KKT", color="#1b1b1b", lw=1.8)
    axis.semilogy(
        phase, coupling, label="SLS fixed point", color="#cc6677", lw=1.8
    )
    axis.axhline(1.0e-5, color="#1b1b1b", ls="--", lw=0.9)
    axis.axhline(1.0e-4, color="#cc6677", ls="--", lw=0.9)
    axis.set_ylabel("residual")
    axis.set_title("accepted-state numerical gates")
    axis.legend(frameon=False)

    axis = axes[1, 2]
    axis.plot(
        phase,
        timeseries["cumulative_ecm_dissipation"],
        color="#d17b0f",
        lw=2.0,
        label="cumulative dissipation",
    )
    axis.set_ylabel("cumulative dissipation", color="#d17b0f")
    twin = axis.twinx()
    twin.plot(
        phase,
        timeseries["ecm_internal_z_norm"],
        color="#6941a5",
        lw=2.0,
        label="||Z||",
    )
    twin.set_ylabel("ECM memory  ||Z||", color="#6941a5")
    axis.set_title("dissipation and retained memory")

    for axis in axes.reshape(-1):
        axis.set_xlabel("phase  t/T")
        axis.set_xlim(0.0, 1.0)
        axis.grid(True, color="0.90", lw=0.7)
    figure.suptitle(
        "N1-2a numerical and mechanical diagnostics\n"
        "completed warmup cycle; not yet a cycle-stability result",
        fontsize=14,
    )
    png_path = case_path / "n1_2a_16step_diagnostics_v01.png"
    svg_path = case_path / "n1_2a_16step_diagnostics_v01.svg"
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    return {"png": str(png_path), "svg": str(svg_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    arguments = parser.parse_args()
    case_path = arguments.case.resolve()
    cycle_path = case_path / "cycle_01"
    timeseries = np.genfromtxt(
        cycle_path / "cycle_timeseries.csv",
        delimiter=",",
        names=True,
        dtype=None,
        encoding="utf-8",
    )
    if len(timeseries) != 17:
        raise RuntimeError("expected 17 accepted phase records")
    states = np.load(cycle_path / "cycle_states.npz")
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    montage = state_montage(case_path, model, timeseries, states)
    diagnostics = diagnostic_figure(case_path, timeseries)
    manifest = {
        "schema_version": "efe_node1_n1_2a_pilot_stage_figures_v01",
        "evidence_class": "stage_diagnostic_not_formal_n1_2_evidence",
        "source_timeseries": str(cycle_path / "cycle_timeseries.csv"),
        "source_states": str(cycle_path / "cycle_states.npz"),
        "state_montage": montage,
        "diagnostics": diagnostics,
        "maximum_accepted_kkt": float(
            np.max(timeseries["normalized_kkt_residual"])
        ),
        "maximum_accepted_coupling_residual": float(
            np.max(timeseries["coupling_residual"])
        ),
        "minimum_ecm_jacobian": float(
            np.min(timeseries["minimum_ecm_jacobian"])
        ),
        "all_states_passed": bool(np.all(timeseries["passed"])),
    }
    manifest_path = case_path / "stage_figure_manifest_v01.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
