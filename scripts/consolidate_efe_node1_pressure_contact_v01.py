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
    _full_external_force,
    build_exact_volume_coordinates,
    contact_kkt_audit,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/hybrid/efe_node1_pressure_path_v01_20260818"
SOURCES = (
    (
        0.00,
        ROOT
        / "results/hybrid/efe_node1_fast_trilayer_v01_20260817/active_only/step_00.npz",
        None,
    ),
    (
        0.01,
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v04_20260818/pressure_001_strict_contact_state.npz",
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v04_20260818/summary.json",
    ),
    (
        0.02,
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v06_20260818/pressure_001_strict_contact_state.npz",
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v06_20260818/summary.json",
    ),
    (
        0.03,
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v09_20260818/activation_000_state.npz",
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v09_20260818/summary.json",
    ),
    (
        0.04,
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v10_20260818/activation_000_state.npz",
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v10_20260818/summary.json",
    ),
    (
        0.05,
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v17_20260818/active_set_equilibrium_state.npz",
        ROOT
        / "results/hybrid/efe_node1_pressure_spectral_v17_20260818/summary.json",
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


def contact_points(
    model,
    ecm_vertices: np.ndarray,
    multipliers: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    points: list[np.ndarray] = []
    values: list[float] = []
    tether_index = 0
    for interface in (model.myocyte_interface, model.endocardial_interface):
        for tether in interface.tethers:
            multiplier = float(multipliers[tether_index])
            if multiplier > 1.0e-10:
                face = interface.ecm_boundary_faces[tether.ecm_face_id]
                points.append(tether.ecm_barycentric @ ecm_vertices[face])
                values.append(multiplier)
            tether_index += 1
    if not points:
        return np.empty((0, 3)), np.empty(0)
    return np.asarray(points), np.asarray(values)


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
    for pressure, state_path, source_summary_path in SOURCES:
        arrays = np.load(state_path)
        state = (
            np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
            np.asarray(arrays["ecm_vertices"], dtype=np.float64),
            np.asarray(arrays["endocardial_vertices"], dtype=np.float64),
        )
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=0.0,
            pressure=pressure,
            wss_command=np.zeros(3),
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
            pressure=pressure,
            wss_command=np.zeros(3),
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
            else float(
                source_summary.get(
                    "audited_follower_residual",
                    source_summary.get("follower_residual", 0.0),
                )
            )
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
                "pressure": pressure,
                "source_state": str(state_path),
                "source_summary": (
                    None
                    if source_summary_path is None
                    else str(source_summary_path)
                ),
                "endocardial_rms_displacement": float(
                    np.sqrt(np.mean(np.sum((state[2] - reference_endocardium) ** 2, axis=1)))
                ),
                "ecm_rms_displacement": float(
                    np.sqrt(np.mean(np.sum((state[1] - reference_ecm) ** 2, axis=1)))
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
        states[pressure] = state
        multiplier_states[pressure] = contact_multipliers
        key = f"p{round(100 * pressure):03d}"
        consolidated_arrays[f"{key}_myocyte_vertices"] = state[0]
        consolidated_arrays[f"{key}_ecm_vertices"] = state[1]
        consolidated_arrays[f"{key}_endocardial_vertices"] = state[2]
        consolidated_arrays[f"{key}_contact_multipliers"] = contact_multipliers

    status = (
        "passed_pressure_only_d0_e0_path_to_005"
        if all(bool(record["passed"]) for record in records)
        else "failed_pressure_only_consolidation_gate"
    )
    summary = {
        "schema_version": "efe_node1_pressure_contact_v01",
        "status": status,
        "scope": (
            "D0/E0 pressure-only development path; prescribed follower load, "
            "not bidirectional FSI, not mesh-converged or physiological calibration"
        ),
        "records": records,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    np.savez_compressed(OUTPUT / "states.npz", **consolidated_arrays)

    pressures = np.asarray([float(record["pressure"]) for record in records])
    endocardial_rms = np.asarray(
        [float(record["endocardial_rms_displacement"]) for record in records]
    )
    ecm_rms = np.asarray(
        [float(record["ecm_rms_displacement"]) for record in records]
    )
    contact_counts = np.asarray(
        [int(record["active_endocardial_contacts"]) for record in records]
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
    for index, pressure in enumerate((0.0, 0.03, 0.05)):
        axis = figure.add_subplot(grid[0, index], projection="3d")
        top_axes.append(axis)
        state = states[pressure]
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
            multiplier_states[pressure],
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
        configure_3d_axis(axis, bounds)
        record = records[int(round(pressure / 0.01))]
        total_contacts = int(record["active_myocyte_contacts"]) + int(
            record["active_endocardial_contacts"]
        )
        axis.set_title(
            f"pressure = {pressure:.2f}\n"
            f"active contacts = {total_contacts} "
            f"(endocardial: {record['active_endocardial_contacts']})"
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
        pressures,
        endocardial_rms,
        "o-",
        color="#2588a6",
        lw=1.8,
        label="endocardium",
    )
    response_axis.plot(
        pressures,
        ecm_rms,
        "s-",
        color="#3f7f4d",
        lw=1.8,
        label="ECM",
    )
    response_axis.set_xlabel("Prescribed pressure command")
    response_axis.set_ylabel("RMS displacement")
    response_axis.set_title("Pressure transmission")
    response_axis.grid(alpha=0.25)
    response_axis.legend(frameon=False, fontsize=8)

    contact_axis = figure.add_subplot(grid[1, 1])
    contact_axis.step(
        pressures,
        contact_counts,
        where="mid",
        color="#6a3d9a",
        lw=1.8,
    )
    contact_axis.scatter(pressures, contact_counts, color="#6a3d9a", s=25)
    contact_axis.set_xlabel("Prescribed pressure command")
    contact_axis.set_ylabel("Active endocardial contacts", color="#6a3d9a")
    multiplier_axis = contact_axis.twinx()
    multiplier_axis.plot(
        pressures,
        maximum_multiplier,
        "o--",
        color="#c0392b",
        lw=1.4,
    )
    multiplier_axis.set_ylabel("Maximum contact multiplier", color="#c0392b")
    contact_axis.set_title("Contact-zone recruitment")
    contact_axis.grid(alpha=0.25)

    audit_axis = figure.add_subplot(grid[1, 2])
    audit_axis.semilogy(pressures, kkt, "o-", color="#284f8f", lw=1.8)
    audit_axis.axhline(1.0e-5, color="#b3261e", ls="--", lw=1.2)
    audit_axis.set_xlabel("Prescribed pressure command")
    audit_axis.set_ylabel("Normalized KKT", color="#284f8f")
    geometry_axis = audit_axis.twinx()
    geometry_axis.plot(
        pressures,
        minimum_j,
        "s-",
        color="#2f7d4b",
        label="minimum ECM J",
    )
    geometry_axis.plot(
        pressures,
        endocardial_area,
        "^-",
        color="#c07a19",
        label="minimum endocardial face ratio",
    )
    geometry_axis.set_ylabel("Geometry quality ratio")
    geometry_axis.legend(frameon=False, fontsize=7, loc="lower left")
    audit_axis.set_title("Equilibrium and geometry gates")
    audit_axis.grid(alpha=0.25, which="both")

    figure.suptitle(
        "EFE Node 1 N1-1 · pressure-only path with strict unilateral contact",
        fontsize=14.5,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: myocardial DCM · green scale: shared 3D ECM displacement · "
            "cyan: passive endocardial DCM · dark markers: active material-contact points. "
            "D0/E0 development evidence; prescribed pressure is not bidirectional FSI."
        ),
        ha="center",
        fontsize=8.3,
    )
    figure.savefig(
        OUTPUT / "pressure_only_stage_figure_v01.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    figure.savefig(
        OUTPUT / "pressure_only_stage_figure_v01.svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)
    print(json.dumps({"status": status, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
