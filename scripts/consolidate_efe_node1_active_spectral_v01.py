from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _kkt_audit,
    build_exact_volume_coordinates,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_active_spectral_v01_20260818"
)
SOURCES = (
    (
        0.00,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v01_20260817/active_only/step_00.npz",
        None,
    ),
    (
        0.02,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v02_20260817/active_only/step_00.npz",
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v02_20260817/active_only/summary.json",
    ),
    (
        0.04,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v04_20260817/active_only/step_00.npz",
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v04_20260817/active_only/summary.json",
    ),
    *tuple(
        (
            activation,
            ROOT
            / (
                "results/hybrid/"
                f"efe_node1_sparse_preconditioner_diagnostic_v{version:02d}_20260818/"
                f"activation_{round(100 * activation):03d}_state.npz"
            ),
            ROOT
            / (
                "results/hybrid/"
                f"efe_node1_sparse_preconditioner_diagnostic_v{version:02d}_20260818/"
                "summary.json"
            ),
        )
        for activation, version in zip(
            np.arange(0.06, 0.201, 0.02),
            range(8, 16),
            strict=True,
        )
    ),
)


def add_uniform_surface(
    axis,
    vertices: np.ndarray,
    faces: np.ndarray,
    color: str,
    alpha: float,
) -> None:
    axis.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolor=color,
            edgecolor=(0.12, 0.12, 0.12, 0.30),
            linewidth=0.14,
            alpha=alpha,
        )
    )


def add_ecm_displacement(
    axis,
    vertices: np.ndarray,
    reference_vertices: np.ndarray,
    faces: np.ndarray,
    normalizer: mpl.colors.Normalize,
) -> None:
    displacement = np.linalg.norm(vertices - reference_vertices, axis=1)
    face_values = displacement[faces].mean(axis=1)
    colors = mpl.colormaps["YlGn"](normalizer(face_values))
    axis.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolor=colors,
            edgecolor=(0.08, 0.24, 0.10, 0.38),
            linewidth=0.30,
            alpha=0.50,
        )
    )


def configure_3d_axis(axis, bounds: tuple[np.ndarray, np.ndarray]) -> None:
    lower, upper = bounds
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
    OUTPUT.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    coordinates = build_exact_volume_coordinates(model)
    records: list[dict[str, object]] = []
    states: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    consolidated_arrays: dict[str, np.ndarray] = {}
    for activation, state_path, source_summary in SOURCES:
        arrays = np.load(state_path)
        state = (
            np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
            np.asarray(arrays["ecm_vertices"], dtype=np.float64),
            np.asarray(arrays["endocardial_vertices"], dtype=np.float64),
        )
        states[float(activation)] = state
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=float(activation),
            reject_penetration=False,
        )
        multipliers, kkt = _kkt_audit(
            model,
            coordinates,
            evaluation,
            state[0],
            state[2],
            np.zeros_like(coordinates.reference_flat),
        )
        volume_residual = max(
            abs(evaluation.myocyte_volume_ratio - 1.0),
            abs(evaluation.endocardial_volume_ratio - 1.0),
        )
        shortening = float(
            1.0
            - np.ptp(state[0][:, 0])
            / np.ptp(model.myocyte.vertices[:, 0])
        )
        passed = bool(
            kkt <= 1.0e-5
            and volume_residual <= 1.0e-8
            and evaluation.minimum_ecm_jacobian >= 0.5
            and evaluation.minimum_gap >= -1.0e-12
            and evaluation.minimum_myocyte_face_area_ratio >= 0.05
            and evaluation.minimum_endocardial_face_area_ratio >= 0.05
            and evaluation.pair_force_residual_mj <= 1.0e-10
            and evaluation.pair_moment_residual_mj <= 1.0e-10
            and evaluation.pair_force_residual_je <= 1.0e-10
            and evaluation.pair_moment_residual_je <= 1.0e-10
        )
        records.append(
            {
                "activation": float(activation),
                "source_state": str(state_path),
                "source_summary": (
                    None if source_summary is None else str(source_summary)
                ),
                "axial_shortening": shortening,
                "myocyte_area_ratio": evaluation.myocyte_area_ratio,
                "endocardial_area_ratio": evaluation.endocardial_area_ratio,
                "volume_constraint_residual": volume_residual,
                "normalized_kkt_residual": kkt,
                "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
                "minimum_gap": evaluation.minimum_gap,
                "minimum_myocyte_face_area_ratio": (
                    evaluation.minimum_myocyte_face_area_ratio
                ),
                "minimum_endocardial_face_area_ratio": (
                    evaluation.minimum_endocardial_face_area_ratio
                ),
                "pair_force_residual_mj": evaluation.pair_force_residual_mj,
                "pair_moment_residual_mj": evaluation.pair_moment_residual_mj,
                "pair_force_residual_je": evaluation.pair_force_residual_je,
                "pair_moment_residual_je": evaluation.pair_moment_residual_je,
                "volume_multipliers": multipliers.tolist(),
                "passed": passed,
            }
        )
        key = f"a{round(100 * activation):03d}"
        consolidated_arrays[f"{key}_myocyte_vertices"] = state[0]
        consolidated_arrays[f"{key}_ecm_vertices"] = state[1]
        consolidated_arrays[f"{key}_endocardial_vertices"] = state[2]

    status = (
        "passed_active_only_d0_e0_spectral_path_to_020"
        if all(bool(record["passed"]) for record in records)
        else "failed_active_only_consolidation_gate"
    )
    summary = {
        "schema_version": "efe_node1_active_spectral_v01",
        "status": status,
        "scope": (
            "D0/E0 active-only development path; not mesh-converged, "
            "not physiological calibration, not complete N1-1"
        ),
        "records": records,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    np.savez_compressed(OUTPUT / "states.npz", **consolidated_arrays)

    activations = np.asarray([float(record["activation"]) for record in records])
    shortening = 100.0 * np.asarray(
        [float(record["axial_shortening"]) for record in records]
    )
    kkt = np.asarray(
        [float(record["normalized_kkt_residual"]) for record in records]
    )
    minimum_j = np.asarray(
        [float(record["minimum_ecm_jacobian"]) for record in records]
    )
    minimum_gap = np.asarray(
        [float(record["minimum_gap"]) for record in records]
    )
    ecm_displacements = np.concatenate(
        [
            np.linalg.norm(state[1] - model.ecm_reference.vertices, axis=1)
            for state in states.values()
        ]
    )
    displacement_normalizer = mpl.colors.Normalize(
        vmin=0.0,
        vmax=float(ecm_displacements.max()),
    )
    reference_all = np.vstack(
        (
            model.myocyte.vertices,
            model.ecm_reference.vertices,
            model.endocardium.vertices,
        )
    )
    bounds = (reference_all.min(axis=0), reference_all.max(axis=0))
    ecm_faces = np.vstack(
        (model.ecm_myocyte_faces, model.ecm_endocardial_faces)
    )

    figure = plt.figure(figsize=(14.6, 7.8), constrained_layout=True)
    figure.get_layout_engine().set(rect=(0.02, 0.075, 0.98, 0.925))
    grid = figure.add_gridspec(2, 3, height_ratios=(1.25, 0.75))
    top_axes = []
    for index, activation in enumerate((0.0, 0.10, 0.20)):
        axis = figure.add_subplot(grid[0, index], projection="3d")
        top_axes.append(axis)
        state = states[activation]
        add_uniform_surface(
            axis,
            state[0],
            model.myocyte.faces,
            "#d95f5f",
            0.78,
        )
        add_ecm_displacement(
            axis,
            state[1],
            model.ecm_reference.vertices,
            ecm_faces,
            displacement_normalizer,
        )
        add_uniform_surface(
            axis,
            state[2],
            model.endocardium.faces,
            "#55b9d0",
            0.64,
        )
        configure_3d_axis(axis, bounds)
        row = records[int(round(activation / 0.02))]
        axis.set_title(
            f"activation = {activation:.2f}\n"
            f"shortening = {100 * float(row['axial_shortening']):.2f}%"
        )
    scalar = mpl.cm.ScalarMappable(
        norm=displacement_normalizer,
        cmap="YlGn",
    )
    colorbar = figure.colorbar(
        scalar,
        ax=top_axes,
        shrink=0.67,
        pad=0.01,
        aspect=24,
    )
    colorbar.set_label("ECM nodal displacement magnitude")

    response_axis = figure.add_subplot(grid[1, 0])
    response_axis.plot(activations, shortening, "o-", color="#a33a3a", lw=1.8)
    response_axis.set_xlabel("Active command")
    response_axis.set_ylabel("Axial shortening (%)")
    response_axis.set_title("Monotonic cell response")
    response_axis.grid(alpha=0.25)

    audit_axis = figure.add_subplot(grid[1, 1])
    audit_axis.semilogy(activations, kkt, "o-", color="#284f8f", lw=1.8)
    audit_axis.axhline(1.0e-5, color="#b3261e", ls="--", lw=1.2)
    audit_axis.text(
        0.005,
        1.25e-5,
        "contract gate 1e-5",
        color="#b3261e",
        fontsize=8,
    )
    audit_axis.set_xlabel("Active command")
    audit_axis.set_ylabel("Normalized KKT")
    audit_axis.set_title("All equilibria pass")
    audit_axis.grid(alpha=0.25, which="both")

    geometry_axis = figure.add_subplot(grid[1, 2])
    geometry_axis.plot(
        activations,
        minimum_j,
        "o-",
        color="#2f7d4b",
    )
    geometry_axis.axhline(0.5, color="#2f7d4b", ls="--", lw=1.0, alpha=0.6)
    geometry_axis.set_xlabel("Active command")
    geometry_axis.set_ylabel("Minimum ECM J", color="#2f7d4b")
    twin_axis = geometry_axis.twinx()
    twin_axis.plot(
        activations,
        minimum_gap,
        "s-",
        color="#86529c",
    )
    twin_axis.axhline(0.0, color="#86529c", ls="--", lw=1.0, alpha=0.6)
    twin_axis.set_ylabel("Minimum interface gap", color="#86529c")
    geometry_axis.set_title("No inversion or penetration")
    geometry_axis.grid(alpha=0.25)

    figure.suptitle(
        "EFE Node 1 N1-1 · active-only path reaches the registered 0.20 peak",
        fontsize=14.5,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: myocardial DCM · green scale: shared 3D ECM displacement · "
            "cyan: passive endocardial DCM. D0/E0 development evidence only; "
            "pressure, WSS and cycle-end states remain pending."
        ),
        ha="center",
        fontsize=8.5,
    )
    figure.savefig(
        OUTPUT / "active_only_stage_figure_v01.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    figure.savefig(
        OUTPUT / "active_only_stage_figure_v01.svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)
    print(json.dumps({"status": status, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
