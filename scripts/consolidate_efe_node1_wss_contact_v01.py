from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from consolidate_efe_node1_pressure_contact_v01 import (
    add_ecm_displacement,
    add_uniform_surface,
    configure_3d_axis,
    contact_points,
)
from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _full_external_force,
    build_exact_volume_coordinates,
    contact_kkt_audit,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/hybrid/efe_node1_wss_path_v01_20260818"
SOURCES = (
    (
        0.000,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v01_20260817/active_only/step_00.npz",
        None,
    ),
    *tuple(
        (
            wss,
            ROOT
            / (
                "results/hybrid/"
                f"efe_node1_wss_spectral_v{version:02d}_20260818/"
                "activation_000_state.npz"
            ),
            ROOT
            / (
                "results/hybrid/"
                f"efe_node1_wss_spectral_v{version:02d}_20260818/"
                "summary.json"
            ),
        )
        for wss, version in zip(
            (0.004, 0.006, 0.008, 0.012, 0.016, 0.020),
            range(1, 7),
            strict=True,
        )
    ),
)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    coordinates = build_exact_volume_coordinates(model)
    reference_endocardium = model.endocardium.vertices
    reference_ecm = model.ecm_reference.vertices
    records: list[dict[str, object]] = []
    states: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    multiplier_states: dict[float, np.ndarray] = {}
    consolidated_arrays: dict[str, np.ndarray] = {}
    for wss_x, state_path, source_summary_path in SOURCES:
        arrays = np.load(state_path)
        state = (
            np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
            np.asarray(arrays["ecm_vertices"], dtype=np.float64),
            np.asarray(arrays["endocardial_vertices"], dtype=np.float64),
        )
        wss_command = np.asarray([wss_x, 0.0, 0.0], dtype=np.float64)
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=0.0,
            pressure=0.0,
            wss_command=wss_command,
            reject_penetration=False,
        )
        contact_multipliers = (
            np.asarray(arrays["contact_multipliers"], dtype=np.float64)
            if "contact_multipliers" in arrays
            else np.zeros(
                len(model.myocyte_interface.tethers)
                + len(model.endocardial_interface.tethers),
                dtype=np.float64,
            )
        )
        external_force = _full_external_force(
            model,
            coordinates,
            state[2],
            pressure=0.0,
            wss_command=wss_command,
        )
        _, kkt, gaps, complementarity = contact_kkt_audit(
            model,
            coordinates,
            evaluation,
            state[0],
            state[1],
            state[2],
            external_force,
            contact_multipliers,
        )
        source_summary = (
            None
            if source_summary_path is None
            else json.loads(source_summary_path.read_text(encoding="utf-8"))
        )
        follower_residual = (
            0.0
            if source_summary is None
            else float(source_summary["follower_residual"])
        )
        volume_residual = max(
            abs(evaluation.myocyte_volume_ratio - 1.0),
            abs(evaluation.endocardial_volume_ratio - 1.0),
        )
        myocyte_count = len(model.myocyte_interface.tethers)
        active_myocyte = int(
            np.count_nonzero(contact_multipliers[:myocyte_count] > 1.0e-10)
        )
        active_endocardial = int(
            np.count_nonzero(contact_multipliers[myocyte_count:] > 1.0e-10)
        )
        endocardial_displacement = state[2] - reference_endocardium
        ecm_displacement = state[1] - reference_ecm
        passed = bool(
            kkt <= 1.0e-5
            and follower_residual <= 1.0e-7
            and volume_residual <= 1.0e-8
            and float(np.min(gaps)) >= -1.0e-12
            and complementarity <= 1.0e-8
            and evaluation.minimum_ecm_jacobian >= 0.5
            and evaluation.minimum_myocyte_face_area_ratio >= 0.05
            and evaluation.minimum_endocardial_face_area_ratio >= 0.05
        )
        records.append(
            {
                "wss_x": wss_x,
                "source_state": str(state_path),
                "source_summary": (
                    None
                    if source_summary_path is None
                    else str(source_summary_path)
                ),
                "endocardial_rms_tangential_displacement": float(
                    np.sqrt(np.mean(endocardial_displacement[:, 0] ** 2))
                ),
                "endocardial_rms_normal_displacement": float(
                    np.sqrt(np.mean(endocardial_displacement[:, 1] ** 2))
                ),
                "ecm_rms_tangential_displacement": float(
                    np.sqrt(np.mean(ecm_displacement[:, 0] ** 2))
                ),
                "active_myocyte_contacts": active_myocyte,
                "active_endocardial_contacts": active_endocardial,
                "maximum_contact_multiplier": float(
                    np.max(contact_multipliers)
                ),
                "normalized_kkt_residual": kkt,
                "follower_residual": follower_residual,
                "volume_constraint_residual": volume_residual,
                "minimum_gap": float(np.min(gaps)),
                "contact_complementarity": complementarity,
                "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
                "minimum_endocardial_face_area_ratio": (
                    evaluation.minimum_endocardial_face_area_ratio
                ),
                "passed": passed,
            }
        )
        states[wss_x] = state
        multiplier_states[wss_x] = contact_multipliers
        key = f"w{round(1000 * wss_x):03d}"
        consolidated_arrays[f"{key}_myocyte_vertices"] = state[0]
        consolidated_arrays[f"{key}_ecm_vertices"] = state[1]
        consolidated_arrays[f"{key}_endocardial_vertices"] = state[2]
        consolidated_arrays[f"{key}_contact_multipliers"] = contact_multipliers

    status = (
        "passed_wss_only_d0_e0_path_to_0020"
        if all(bool(record["passed"]) for record in records)
        else "failed_wss_only_consolidation_gate"
    )
    summary = {
        "schema_version": "efe_node1_wss_contact_v01",
        "status": status,
        "scope": (
            "D0/E0 WSS-only development path; prescribed follower traction, "
            "not bidirectional FSI, not mesh-converged or physiological calibration"
        ),
        "records": records,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    np.savez_compressed(OUTPUT / "states.npz", **consolidated_arrays)

    loads = np.asarray([float(record["wss_x"]) for record in records])
    endocardial_tangential = np.asarray(
        [
            float(record["endocardial_rms_tangential_displacement"])
            for record in records
        ]
    )
    endocardial_normal = np.asarray(
        [
            float(record["endocardial_rms_normal_displacement"])
            for record in records
        ]
    )
    ecm_tangential = np.asarray(
        [
            float(record["ecm_rms_tangential_displacement"])
            for record in records
        ]
    )
    contact_counts = np.asarray(
        [
            int(record["active_myocyte_contacts"])
            + int(record["active_endocardial_contacts"])
            for record in records
        ]
    )
    maximum_multiplier = np.asarray(
        [float(record["maximum_contact_multiplier"]) for record in records]
    )
    kkt = np.asarray(
        [float(record["normalized_kkt_residual"]) for record in records]
    )
    minimum_j = np.asarray(
        [float(record["minimum_ecm_jacobian"]) for record in records]
    )
    endocardial_area = np.asarray(
        [float(record["minimum_endocardial_face_area_ratio"]) for record in records]
    )
    ecm_displacements = np.concatenate(
        [
            np.linalg.norm(state[1] - reference_ecm, axis=1)
            for state in states.values()
        ]
    )
    displacement_normalizer = mpl.colors.Normalize(
        vmin=0.0,
        vmax=float(ecm_displacements.max()),
    )
    contact_maximum = max(
        float(np.max(values)) for values in multiplier_states.values()
    )
    contact_normalizer = mpl.colors.Normalize(vmin=0.0, vmax=contact_maximum)
    reference_all = np.vstack(
        (model.myocyte.vertices, reference_ecm, model.endocardium.vertices)
    )
    bounds = (reference_all.min(axis=0), reference_all.max(axis=0))
    ecm_faces = np.vstack((model.ecm_myocyte_faces, model.ecm_endocardial_faces))

    figure = plt.figure(figsize=(14.6, 7.8), constrained_layout=True)
    figure.get_layout_engine().set(rect=(0.02, 0.075, 0.98, 0.925))
    grid = figure.add_gridspec(2, 3, height_ratios=(1.25, 0.75))
    top_axes = []
    for index, wss_x in enumerate((0.0, 0.008, 0.020)):
        axis = figure.add_subplot(grid[0, index], projection="3d")
        top_axes.append(axis)
        state = states[wss_x]
        add_uniform_surface(axis, state[0], model.myocyte.faces, "#d95f5f", 0.78)
        add_ecm_displacement(
            axis,
            state[1],
            reference_ecm,
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
        points, values = contact_points(
            model,
            state[1],
            multiplier_states[wss_x],
        )
        if len(points):
            axis.scatter(
                points[:, 0],
                points[:, 1],
                points[:, 2],
                c=values,
                cmap="magma",
                norm=contact_normalizer,
                s=18,
                edgecolor="black",
                linewidth=0.25,
                depthshade=False,
            )
        if wss_x > 0.0:
            axis.quiver(
                0.12,
                1.03,
                0.92,
                0.26,
                0.0,
                0.0,
                color="#244f9e",
                linewidth=2.0,
                arrow_length_ratio=0.22,
            )
        configure_3d_axis(axis, bounds)
        record = records[list(loads).index(wss_x)]
        total_contacts = int(record["active_myocyte_contacts"]) + int(
            record["active_endocardial_contacts"]
        )
        axis.set_title(
            f"WSS x-command = {wss_x:.3f}\n"
            f"active contacts = {total_contacts}"
        )
    scalar = mpl.cm.ScalarMappable(norm=displacement_normalizer, cmap="YlGn")
    colorbar = figure.colorbar(
        scalar,
        ax=top_axes,
        shrink=0.67,
        pad=0.01,
        aspect=24,
    )
    colorbar.set_label("ECM nodal displacement magnitude")

    response_axis = figure.add_subplot(grid[1, 0])
    response_axis.plot(
        loads,
        endocardial_tangential,
        "o-",
        color="#2588a6",
        lw=1.8,
        label="endocardium |u_x| RMS",
    )
    response_axis.plot(
        loads,
        ecm_tangential,
        "s-",
        color="#3f7f4d",
        lw=1.8,
        label="ECM |u_x| RMS",
    )
    response_axis.plot(
        loads,
        endocardial_normal,
        "^--",
        color="#a65a2e",
        lw=1.4,
        label="endocardium |u_y| RMS",
    )
    response_axis.set_xlabel("Prescribed WSS x-command")
    response_axis.set_ylabel("RMS displacement component")
    response_axis.set_title("Tangential transmission and normal coupling")
    response_axis.grid(alpha=0.25)
    response_axis.legend(frameon=False, fontsize=7)

    contact_axis = figure.add_subplot(grid[1, 1])
    contact_axis.step(loads, contact_counts, where="mid", color="#6a3d9a", lw=1.8)
    contact_axis.scatter(loads, contact_counts, color="#6a3d9a", s=25)
    contact_axis.set_xlabel("Prescribed WSS x-command")
    contact_axis.set_ylabel("Total active contacts", color="#6a3d9a")
    multiplier_axis = contact_axis.twinx()
    multiplier_axis.plot(
        loads,
        maximum_multiplier,
        "o--",
        color="#c0392b",
        lw=1.4,
    )
    multiplier_axis.set_ylabel("Maximum contact multiplier", color="#c0392b")
    contact_axis.set_title("Contact-zone migration under shear")
    contact_axis.grid(alpha=0.25)

    audit_axis = figure.add_subplot(grid[1, 2])
    audit_axis.semilogy(loads, kkt, "o-", color="#284f8f", lw=1.8)
    audit_axis.axhline(1.0e-5, color="#b3261e", ls="--", lw=1.2)
    audit_axis.set_xlabel("Prescribed WSS x-command")
    audit_axis.set_ylabel("Normalized KKT", color="#284f8f")
    geometry_axis = audit_axis.twinx()
    geometry_axis.plot(loads, minimum_j, "s-", color="#2f7d4b", label="min ECM J")
    geometry_axis.plot(
        loads,
        endocardial_area,
        "^-",
        color="#c07a19",
        label="min endocardial face ratio",
    )
    geometry_axis.set_ylabel("Geometry quality ratio")
    geometry_axis.legend(frameon=False, fontsize=7, loc="lower left")
    audit_axis.set_title("Equilibrium and geometry gates")
    audit_axis.grid(alpha=0.25, which="both")

    figure.suptitle(
        "EFE Node 1 N1-1 · WSS-only path with shear-to-normal geometric coupling",
        fontsize=14.5,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: myocardial DCM · green scale: shared 3D ECM displacement · "
            "cyan: passive endocardial DCM · blue arrow: WSS direction · "
            "dark markers: active contacts. D0/E0 prescribed-traction evidence only."
        ),
        ha="center",
        fontsize=8.3,
    )
    figure.savefig(
        OUTPUT / "wss_only_stage_figure_v01.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    figure.savefig(
        OUTPUT / "wss_only_stage_figure_v01.svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)
    print(json.dumps({"status": status, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
