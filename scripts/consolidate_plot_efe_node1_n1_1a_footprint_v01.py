from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from hybrid.efe_fast_trilayer import (
    FastTrilayerModel,
    MaterialInterface,
    SurfaceLayerReference,
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _kkt_audit,
    build_exact_volume_coordinates,
)
from route_h.contact_adhesion import material_tether_energy_force_with_reference


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_1a_footprint_audit_v01_20260818"
)
F100_SUMMARY = (
    ROOT / "results/hybrid/efe_node1_active_spectral_v01_20260818/summary.json"
)
F200_SUMMARY = (
    ROOT
    / "results/hybrid/efe_node1_n1_1a_f200_cross_initialized_v01_20260818"
    / "summary.json"
)
F150_SOURCES = (
    (
        0.02,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v02_20260818"
        / "F150/solver_step_01/activation_002_state.npz",
    ),
    (
        0.04,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v02_20260818"
        / "F150/solver_step_02/activation_004_state.npz",
    ),
    (
        0.06,
        ROOT
        / "results/hybrid/efe_node1_n1_1a_footprint_v08_20260818"
        / "F150_a006_refined/activation_006_state.npz",
    ),
    *tuple(
        (
            activation,
            ROOT
            / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v03_20260818"
            / f"F150/solver_step_{step:02d}"
            / f"activation_{round(100 * activation):03d}_state.npz",
        )
        for step, activation in enumerate(
            np.arange(0.08, 0.201, 0.02), start=1
        )
    ),
)


def interface_traction(
    model: FastTrilayerModel,
    interface: MaterialInterface,
    layer: SurfaceLayerReference,
    layer_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> np.ndarray:
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    values: list[float] = []
    for tether in interface.tethers:
        row = row_by_id[tether.material_point_id]
        layer_face = layer.faces[int(interface.registry.face_ids[row])]
        ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
        reference_weight = float(interface.registry.reference_weights[row])
        _, layer_force, _, _ = material_tether_energy_force_with_reference(
            layer_vertices,
            layer_face,
            ecm_vertices,
            ecm_face,
            reference_master_vertices=layer.vertices,
            reference_slave_vertices=model.ecm_reference.vertices,
            master_barycentric=interface.registry.barycentric[row],
            slave_barycentric=tether.ecm_barycentric,
            reference_weight=reference_weight,
            g0_pair=tether.reference_gap,
            normal_orientation_sign=tether.normal_orientation_sign,
            reference_t1=tether.reference_t1,
            reference_t2=tether.reference_t2,
            adhesion_work=tether.adhesion_work,
            opening_cutoff=tether.opening_cutoff,
            tangential_stiffness=tether.tangential_stiffness,
        )
        values.append(
            float(np.linalg.norm(layer_force.sum(axis=0)) / reference_weight)
        )
    return np.asarray(values)


def load_state(
    model: FastTrilayerModel,
    source: Path | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if source is None:
        return (
            model.myocyte.vertices.copy(),
            model.ecm_reference.vertices.copy(),
            model.endocardium.vertices.copy(),
        )
    arrays = np.load(source)
    return (
        np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
        np.asarray(arrays["ecm_vertices"], dtype=np.float64),
        np.asarray(arrays["endocardial_vertices"], dtype=np.float64),
    )


def displacement_interpolator(
    model: FastTrilayerModel,
    ecm_vertices: np.ndarray,
) -> RegularGridInterpolator:
    reference = model.ecm_reference.vertices
    x_values = np.unique(reference[:, 0])
    y_values = np.unique(reference[:, 1])
    z_values = np.unique(reference[:, 2])
    displacement = (ecm_vertices - reference).reshape(
        len(x_values), len(y_values), len(z_values), 3
    )
    return RegularGridInterpolator(
        (x_values, y_values, z_values),
        displacement,
        bounds_error=False,
        fill_value=None,
    )


def audit_path(
    case_id: str,
    scale: float,
    sources: list[tuple[float, Path | None]],
) -> tuple[list[dict[str, object]], dict[float, tuple[np.ndarray, ...]]]:
    model = build_fast_trilayer_model(ecm_footprint_scale=scale)
    coordinates = build_exact_volume_coordinates(model)
    records: list[dict[str, object]] = []
    states: dict[float, tuple[np.ndarray, ...]] = {}
    for activation, source in sources:
        state = load_state(model, source)
        states[activation] = state
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=activation,
            reject_penetration=False,
        )
        _, kkt = _kkt_audit(
            model,
            coordinates,
            evaluation,
            state[0],
            state[2],
            np.zeros_like(coordinates.reference_flat),
        )
        myocyte_traction = interface_traction(
            model,
            model.myocyte_interface,
            model.myocyte,
            state[0],
            state[1],
        )
        endocardial_traction = interface_traction(
            model,
            model.endocardial_interface,
            model.endocardium,
            state[2],
            state[1],
        )
        volume_residual = max(
            abs(evaluation.myocyte_volume_ratio - 1.0),
            abs(evaluation.endocardial_volume_ratio - 1.0),
        )
        record = {
            "case_id": case_id,
            "ecm_footprint_scale": scale,
            "activation": activation,
            "source_state": None if source is None else str(source),
            "axial_shortening": float(
                1.0
                - np.ptp(state[0][:, 0]) / np.ptp(model.myocyte.vertices[:, 0])
            ),
            "maximum_myocyte_ecm_traction": float(np.max(myocyte_traction)),
            "maximum_ecm_endocardium_traction": float(
                np.max(endocardial_traction)
            ),
            "maximum_interface_traction": float(
                max(np.max(myocyte_traction), np.max(endocardial_traction))
            ),
            "ecm_equilibrium_energy": evaluation.energy_components[
                "ecm_equilibrium"
            ],
            "ecm_viscoelastic_energy": evaluation.energy_components[
                "ecm_viscoelastic"
            ],
            "normalized_kkt_residual": kkt,
            "volume_constraint_residual": volume_residual,
            "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
            "minimum_gap": evaluation.minimum_gap,
            "minimum_myocyte_face_area_ratio": (
                evaluation.minimum_myocyte_face_area_ratio
            ),
            "minimum_endocardial_face_area_ratio": (
                evaluation.minimum_endocardial_face_area_ratio
            ),
            "passed": bool(
                kkt <= 1.0e-5
                and volume_residual <= 1.0e-8
                and evaluation.minimum_ecm_jacobian > 0.0
                and evaluation.minimum_gap >= -1.0e-12
                and evaluation.minimum_myocyte_face_area_ratio > 0.2
                and evaluation.minimum_endocardial_face_area_ratio > 0.2
                and evaluation.pair_force_residual_mj <= 1.0e-10
                and evaluation.pair_moment_residual_mj <= 1.0e-10
                and evaluation.pair_force_residual_je <= 1.0e-10
                and evaluation.pair_moment_residual_je <= 1.0e-10
            ),
        }
        records.append(record)
    return records, states


def relative_change(reference: float, candidate: float) -> float:
    return abs(candidate - reference) / max(1.0e-14, abs(reference))


def add_uniform_surface(axis, vertices, faces, color, alpha) -> None:
    axis.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolor=color,
            edgecolor=(0.10, 0.10, 0.10, 0.25),
            linewidth=0.12,
            alpha=alpha,
        )
    )


def add_ecm_surface(axis, model, vertices, normalizer) -> None:
    faces = np.vstack((model.ecm_myocyte_faces, model.ecm_endocardial_faces))
    displacement = np.linalg.norm(
        vertices - model.ecm_reference.vertices, axis=1
    )
    values = displacement[faces].mean(axis=1)
    axis.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolor=mpl.colormaps["YlGn"](normalizer(values)),
            edgecolor=(0.08, 0.22, 0.10, 0.32),
            linewidth=0.22,
            alpha=0.58,
        )
    )


def configure_3d_axis(axis, bounds) -> None:
    lower, upper = bounds
    centre = 0.5 * (lower + upper)
    half_span = 0.54 * float(np.max(upper - lower))
    axis.set_xlim(centre[0] - half_span, centre[0] + half_span)
    axis.set_ylim(centre[1] - half_span, centre[1] + half_span)
    axis.set_zlim(centre[2] - half_span, centre[2] + half_span)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=21, azim=-57)
    axis.set_xlabel("x", labelpad=-3)
    axis.set_ylabel("y", labelpad=-3)
    axis.set_zlabel("z", labelpad=-3)
    axis.tick_params(labelsize=6, pad=0)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    f100_source_summary = json.loads(F100_SUMMARY.read_text("utf-8"))
    f100_sources = [
        (
            float(record["activation"]),
            Path(record["source_state"]),
        )
        for record in f100_source_summary["records"]
    ]
    f150_sources: list[tuple[float, Path | None]] = [(0.0, None)]
    f150_sources.extend(F150_SOURCES)
    f200_source_summary = json.loads(F200_SUMMARY.read_text("utf-8"))
    f200_sources: list[tuple[float, Path | None]] = [(0.0, None)]
    f200_sources.extend(
        (
            float(record["activation"]),
            Path(record["source_state"]),
        )
        for record in f200_source_summary["records"][1:]
    )

    paths: dict[str, list[dict[str, object]]] = {}
    states_by_case: dict[str, dict[float, tuple[np.ndarray, ...]]] = {}
    for case_id, scale, sources in (
        ("F100", 1.0, f100_sources),
        ("F150", 1.5, f150_sources),
        ("F200", 2.0, f200_sources),
    ):
        paths[case_id], states_by_case[case_id] = audit_path(
            case_id, scale, sources
        )

    models = {
        case_id: build_fast_trilayer_model(ecm_footprint_scale=scale)
        for case_id, scale in (("F100", 1.0), ("F150", 1.5), ("F200", 2.0))
    }
    peak_records = {case_id: records[-1] for case_id, records in paths.items()}
    peak_states = {
        case_id: states_by_case[case_id][0.20] for case_id in paths
    }

    common_x = np.linspace(0.0, 1.0, 21)
    common_y = np.linspace(0.64, 0.94, 5)
    common_z = np.linspace(0.20, 0.76, 13)
    common_points = np.asarray(
        [
            [x_value, y_value, z_value]
            for x_value in common_x
            for y_value in common_y
            for z_value in common_z
        ]
    )
    common_displacement = {
        case_id: np.asarray(
            displacement_interpolator(models[case_id], peak_states[case_id][1])(
                common_points
            )
        )
        for case_id in paths
    }
    common_rms = {
        case_id: float(
            np.sqrt(np.mean(np.sum(displacement * displacement, axis=1)))
        )
        for case_id, displacement in common_displacement.items()
    }
    f150_f200_field_difference = float(
        np.linalg.norm(common_displacement["F150"] - common_displacement["F200"])
        / max(1.0e-14, np.linalg.norm(common_displacement["F200"]))
    )
    shortening_change = relative_change(
        float(peak_records["F200"]["axial_shortening"]),
        float(peak_records["F150"]["axial_shortening"]),
    )
    traction_change = relative_change(
        float(peak_records["F200"]["maximum_interface_traction"]),
        float(peak_records["F150"]["maximum_interface_traction"]),
    )
    global_gate_passed = shortening_change <= 0.02
    interface_gate_passed = traction_change <= 0.10
    recommended = global_gate_passed and interface_gate_passed
    status = (
        "passed_recommend_f150_production_footprint"
        if recommended and all(
            bool(record["passed"])
            for records in paths.values()
            for record in records
        )
        else "failed_f150_production_footprint_gate"
    )

    all_records = [record for records in paths.values() for record in records]
    with (OUTPUT / "footprint_path_source_data.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_records[0]))
        writer.writeheader()
        writer.writerows(all_records)

    report = {
        "schema_version": "efe_node1_n1_1a_footprint_audit_v01",
        "status": status,
        "scope": (
            "D0 active-only lateral-footprint audit with density-preserving "
            "ECM enlargement; not formal D1/E1 convergence or N1-2"
        ),
        "cases": {
            case_id: {
                "scale": models[case_id].ecm_footprint_scale,
                "divisions": models[case_id].ecm_divisions,
                "ecm_vertices": len(models[case_id].ecm_reference.vertices),
                "ecm_tetrahedra": len(
                    models[case_id].ecm_reference.tetrahedra
                ),
                "peak": peak_records[case_id],
                "common_overlap_rms_displacement": common_rms[case_id],
            }
            for case_id in paths
        },
        "f150_to_f200": {
            "peak_shortening_relative_change": shortening_change,
            "peak_shortening_gate": 0.02,
            "peak_shortening_gate_passed": global_gate_passed,
            "maximum_interface_traction_relative_change": traction_change,
            "maximum_interface_traction_gate": 0.10,
            "maximum_interface_traction_gate_passed": interface_gate_passed,
            "common_overlap_displacement_relative_l2_difference": (
                f150_f200_field_difference
            ),
        },
        "recommendation": (
            "adopt_1.5x_for_global_cycle_production_keep_2.0x_for_local_field_audit_and_1.0x_as_narrow_control"
            if recommended
            else "retain_2.0x_or_expand_far_boundary_audit"
        ),
        "local_field_caveat": (
            "F150-to-F200 common-overlap displacement L2 difference is not a "
            "formal convergence pass; final hotspot/local-field claims must "
            "retain an F200 control"
        ),
        "paths": paths,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    maximum_displacement = max(
        float(
            np.max(
                np.linalg.norm(
                    peak_states[case_id][1]
                    - models[case_id].ecm_reference.vertices,
                    axis=1,
                )
            )
        )
        for case_id in paths
    )
    displacement_normalizer = mpl.colors.Normalize(
        vmin=0.0, vmax=maximum_displacement
    )
    f200_reference = np.vstack(
        (
            models["F200"].myocyte.vertices,
            models["F200"].ecm_reference.vertices,
            models["F200"].endocardium.vertices,
        )
    )
    bounds = (f200_reference.min(axis=0), f200_reference.max(axis=0))

    figure = plt.figure(figsize=(15.8, 8.7), constrained_layout=True)
    figure.get_layout_engine().set(rect=(0.015, 0.075, 0.985, 0.93))
    grid = figure.add_gridspec(2, 3, height_ratios=(1.22, 0.78))
    top_axes = []
    for column, case_id in enumerate(("F100", "F150", "F200")):
        axis = figure.add_subplot(grid[0, column], projection="3d")
        top_axes.append(axis)
        model = models[case_id]
        state = peak_states[case_id]
        add_uniform_surface(
            axis, state[0], model.myocyte.faces, "#d95f5f", 0.76
        )
        add_ecm_surface(axis, model, state[1], displacement_normalizer)
        add_uniform_surface(
            axis, state[2], model.endocardium.faces, "#55b9d0", 0.58
        )
        configure_3d_axis(axis, bounds)
        peak = peak_records[case_id]
        axis.set_title(
            f"{case_id}: {float(peak['ecm_footprint_scale']):.1f}× ECM footprint\n"
            f"shortening = {100 * float(peak['axial_shortening']):.3f}% · "
            f"max traction = {float(peak['maximum_interface_traction']):.4f}"
        )
    scalar = mpl.cm.ScalarMappable(
        norm=displacement_normalizer, cmap="YlGn"
    )
    colorbar = figure.colorbar(
        scalar, ax=top_axes, shrink=0.64, pad=0.012, aspect=24
    )
    colorbar.set_label("ECM nodal displacement magnitude")

    response_axis = figure.add_subplot(grid[1, 0])
    colors = {"F100": "#8e3b46", "F150": "#3182a8", "F200": "#3b7f4a"}
    for case_id, records in paths.items():
        response_axis.plot(
            [float(record["activation"]) for record in records],
            [100 * float(record["axial_shortening"]) for record in records],
            "o-",
            color=colors[case_id],
            lw=1.6,
            ms=3,
            label=case_id,
        )
    response_axis.set_xlabel("Active command")
    response_axis.set_ylabel("Axial shortening (%)")
    response_axis.set_title("Global response is footprint-stable")
    response_axis.legend(frameon=False, fontsize=7)
    response_axis.grid(alpha=0.23)

    profile_axis = figure.add_subplot(grid[1, 1])
    for case_id in ("F100", "F150", "F200"):
        model = models[case_id]
        x_values = np.linspace(
            float(model.ecm_reference.vertices[:, 0].min()),
            float(model.ecm_reference.vertices[:, 0].max()),
            121,
        )
        points = np.column_stack(
            (
                x_values,
                np.full_like(x_values, 0.79),
                np.full_like(x_values, 0.48),
            )
        )
        displacement = displacement_interpolator(
            model, peak_states[case_id][1]
        )(points)
        profile_axis.plot(
            x_values,
            np.linalg.norm(displacement, axis=1),
            color=colors[case_id],
            lw=1.6,
            label=case_id,
        )
    profile_axis.axvspan(0.0, 1.0, color="#d95f5f", alpha=0.08)
    profile_axis.set_xlabel("x at ECM mid-plane")
    profile_axis.set_ylabel("ECM |u|")
    profile_axis.set_title("Added ECM moves the side boundary away")
    profile_axis.legend(frameon=False, fontsize=7)
    profile_axis.grid(alpha=0.23)

    gate_axis = figure.add_subplot(grid[1, 2])
    metric_names = ("shortening", "max traction", "common field L2")
    f100_f150 = (
        100
        * relative_change(
            float(peak_records["F150"]["axial_shortening"]),
            float(peak_records["F100"]["axial_shortening"]),
        ),
        100
        * relative_change(
            float(peak_records["F150"]["maximum_interface_traction"]),
            float(peak_records["F100"]["maximum_interface_traction"]),
        ),
        100
        * float(
            np.linalg.norm(
                common_displacement["F100"] - common_displacement["F150"]
            )
            / max(1.0e-14, np.linalg.norm(common_displacement["F150"]))
        ),
    )
    f150_f200 = (
        100 * shortening_change,
        100 * traction_change,
        100 * f150_f200_field_difference,
    )
    positions = np.arange(len(metric_names))
    width = 0.34
    gate_axis.bar(
        positions - width / 2,
        f100_f150,
        width,
        color="#6e87aa",
        label="F100→F150",
    )
    gate_axis.bar(
        positions + width / 2,
        f150_f200,
        width,
        color="#4d8f63",
        label="F150→F200",
    )
    gate_axis.axhline(2.0, color="#b3261e", ls="--", lw=1.0)
    gate_axis.axhline(10.0, color="#8b5a00", ls=":", lw=1.0)
    gate_axis.set_xticks(positions, metric_names)
    gate_axis.set_ylabel("Relative change (%)")
    gate_axis.set_title("Boundary-sensitivity audit")
    gate_axis.legend(frameon=False, fontsize=7)
    gate_axis.grid(alpha=0.20, axis="y")

    figure.suptitle(
        "EFE Node 1 N1-1A · ECM lateral-footprint audit at peak contraction",
        fontsize=14.2,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: myocardial DCM · green: 3D ECM displacement · cyan: passive "
            "endocardial DCM. Thickness remains 0.30; x/z element size is "
            "preserved as the footprint expands. Development boundary audit "
            "only, not formal D1/E1 convergence or N1-2."
        ),
        ha="center",
        fontsize=8.3,
    )
    figure.savefig(
        OUTPUT / "n1_1a_ecm_footprint_stage_figure_v01.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    figure.savefig(
        OUTPUT / "n1_1a_ecm_footprint_stage_figure_v01.svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)
    print(json.dumps({"status": status, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
