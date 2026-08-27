from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from hybrid.efe_fast_trilayer import build_fast_trilayer_model


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = (
    ROOT
    / "results"
    / "hybrid"
    / "efe_node1_fast_trilayer_v04_20260817"
    / "active_only"
)
STATES = (
    (
        "Reference",
        0.00,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v01_20260817/active_only/step_00.npz",
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v01_20260817/active_only/summary.json",
        0,
    ),
    (
        "First accepted load",
        0.02,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v02_20260817/active_only/step_00.npz",
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v02_20260817/active_only/summary.json",
        0,
    ),
    (
        "Current frontier",
        0.04,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v04_20260817/active_only/step_00.npz",
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v04_20260817/active_only/summary.json",
        0,
    ),
)


def add_surface(
    axis,
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    color: str,
    alpha: float,
    linewidth: float,
) -> None:
    collection = Poly3DCollection(
        vertices[faces],
        facecolor=color,
        edgecolor=(0.15, 0.15, 0.15, 0.32),
        linewidth=linewidth,
        alpha=alpha,
    )
    axis.add_collection3d(collection)


def add_ecm_layer(axis, vertices: np.ndarray, faces: np.ndarray) -> None:
    collection = Poly3DCollection(
        vertices[faces],
        facecolor="#8fcf9a",
        edgecolor=(0.10, 0.28, 0.13, 0.38),
        linewidth=0.35,
        alpha=0.30,
    )
    axis.add_collection3d(collection)


def configure_axis(axis, all_vertices: np.ndarray) -> None:
    lower = all_vertices.min(axis=0)
    upper = all_vertices.max(axis=0)
    centre = 0.5 * (lower + upper)
    half_span = 0.55 * float(np.max(upper - lower))
    axis.set_xlim(centre[0] - half_span, centre[0] + half_span)
    axis.set_ylim(centre[1] - half_span, centre[1] + half_span)
    axis.set_zlim(centre[2] - half_span, centre[2] + half_span)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=20, azim=-56)
    axis.set_xlabel("x (fiber)", labelpad=-2)
    axis.set_ylabel("y (layer normal)", labelpad=-2)
    axis.set_zlabel("z", labelpad=-2)
    axis.tick_params(labelsize=7, pad=0)


def main() -> None:
    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    rows: list[dict[str, float | bool | str]] = []
    loaded_states: list[tuple[str, float, dict[str, np.ndarray]]] = []
    for label, activation, checkpoint, summary_path, record_index in STATES:
        arrays = dict(np.load(checkpoint))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        record = summary["records"][record_index]
        gate = record["hard_gates"]
        rows.append(
            {
                "label": label,
                "activation": activation,
                "shortening": float(record["axial_shortening"]),
                "kkt": float(gate["normalized_kkt_residual"]),
                "min_j": float(gate["minimum_ecm_jacobian"]),
                "gap": float(gate["minimum_gap"]),
                "raw_newton": bool(record["newton_success"]),
            }
        )
        loaded_states.append((label, activation, arrays))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 11,
            "axes.labelsize": 8,
        }
    )
    figure = plt.figure(figsize=(14.2, 7.6), constrained_layout=True)
    figure.get_layout_engine().set(rect=(0.02, 0.075, 0.98, 0.925))
    grid = figure.add_gridspec(2, 3, height_ratios=(1.25, 0.75))
    for index, (label, activation, arrays) in enumerate(loaded_states):
        axis = figure.add_subplot(grid[0, index], projection="3d")
        myocyte = arrays["myocyte_vertices"]
        ecm = arrays["ecm_vertices"]
        endocardium = arrays["endocardial_vertices"]
        add_surface(
            axis,
            myocyte,
            model.myocyte.faces,
            color="#d95f5f",
            alpha=0.78,
            linewidth=0.16,
        )
        ecm_faces = np.vstack(
            (model.ecm_myocyte_faces, model.ecm_endocardial_faces)
        )
        add_ecm_layer(axis, ecm, ecm_faces)
        add_surface(
            axis,
            endocardium,
            model.endocardium.faces,
            color="#55b9d0",
            alpha=0.66,
            linewidth=0.14,
        )
        configure_axis(axis, np.vstack((myocyte, ecm, endocardium)))
        axis.set_title(f"{label}\nactivation = {activation:.2f}")

    activation = np.asarray([row["activation"] for row in rows])
    shortening = 100.0 * np.asarray([row["shortening"] for row in rows])
    kkt = np.asarray([row["kkt"] for row in rows])
    minimum_j = np.asarray([row["min_j"] for row in rows])
    minimum_gap = np.asarray([row["gap"] for row in rows])

    response_axis = figure.add_subplot(grid[1, 0])
    response_axis.plot(activation, shortening, "o-", color="#a33a3a", lw=1.8)
    response_axis.set_xlabel("Active command")
    response_axis.set_ylabel("Axial shortening (%)")
    response_axis.set_title("Shape response")
    response_axis.grid(alpha=0.25)

    audit_axis = figure.add_subplot(grid[1, 1])
    audit_axis.semilogy(activation, kkt, "o-", color="#284f8f", lw=1.8)
    audit_axis.axhline(1.0e-5, color="#b3261e", ls="--", lw=1.2)
    audit_axis.text(
        0.001,
        1.18e-5,
        "contract gate 1e-5",
        color="#b3261e",
        fontsize=8,
    )
    audit_axis.set_xlabel("Active command")
    audit_axis.set_ylabel("Normalized KKT")
    audit_axis.set_title("Audited mechanical convergence")
    audit_axis.grid(alpha=0.25, which="both")

    geometry_axis = figure.add_subplot(grid[1, 2])
    geometry_axis.plot(
        activation,
        minimum_j,
        "o-",
        color="#2f7d4b",
        label="min ECM J",
    )
    twin_axis = geometry_axis.twinx()
    twin_axis.plot(
        activation,
        minimum_gap,
        "s-",
        color="#86529c",
        label="min gap",
    )
    geometry_axis.axhline(0.5, color="#2f7d4b", ls="--", lw=1.0, alpha=0.6)
    twin_axis.axhline(0.0, color="#86529c", ls="--", lw=1.0, alpha=0.6)
    geometry_axis.set_xlabel("Active command")
    geometry_axis.set_ylabel("Minimum ECM J", color="#2f7d4b")
    twin_axis.set_ylabel("Minimum interface gap", color="#86529c")
    geometry_axis.set_title("Geometry remains valid")
    geometry_axis.grid(alpha=0.25)

    figure.suptitle(
        "EFE Node 1 N1-1 · active-only development frontier",
        fontsize=15,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: active myocardial DCM · green: shared 3D viscoelastic-ECM "
            "reference layer · cyan: passive endocardial DCM. D0/E0 development "
            "states; not a mesh-converged or physiological calibration result."
        ),
        ha="center",
        fontsize=8.5,
    )
    output_png = OUTPUT_DIRECTORY / "n1_1_active_path_stage_diagnostic_v01.png"
    output_svg = OUTPUT_DIRECTORY / "n1_1_active_path_stage_diagnostic_v01.svg"
    figure.savefig(output_png, dpi=220, bbox_inches="tight", facecolor="white")
    figure.savefig(output_svg, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(output_png)
    print(output_svg)


if __name__ == "__main__":
    main()
