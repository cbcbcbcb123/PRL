from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from hybrid.efe_fast_trilayer import (
    FastTrilayerModel,
    MaterialInterface,
    SurfaceLayerReference,
    build_fast_trilayer_model,
)
from route_h.contact_adhesion import material_tether_energy_force_with_reference


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818"
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
            edgecolor=(0.10, 0.10, 0.10, 0.26),
            linewidth=0.13,
            alpha=alpha,
        )
    )


def add_scalar_surface(
    axis,
    vertices: np.ndarray,
    faces: np.ndarray,
    nodal_values: np.ndarray,
    *,
    color_map: str,
    normalizer: mpl.colors.Normalize,
    alpha: float,
) -> None:
    face_values = nodal_values[faces].mean(axis=1)
    axis.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolor=mpl.colormaps[color_map](normalizer(face_values)),
            edgecolor=(0.08, 0.18, 0.10, 0.30),
            linewidth=0.22,
            alpha=alpha,
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
    axis.set_xlabel("x (fiber)", labelpad=-3)
    axis.set_ylabel("y (layer normal)", labelpad=-3)
    axis.set_zlabel("z", labelpad=-3)
    axis.tick_params(labelsize=6.5, pad=0)


def tetrahedral_to_nodal_scalar(
    tetrahedra: np.ndarray,
    tetrahedral_values: np.ndarray,
    vertex_count: int,
) -> np.ndarray:
    values = np.zeros(vertex_count, dtype=np.float64)
    counts = np.zeros(vertex_count, dtype=np.float64)
    for tetrahedron, value in zip(
        tetrahedra, tetrahedral_values, strict=True
    ):
        np.add.at(values, tetrahedron, value)
        np.add.at(counts, tetrahedron, 1.0)
    return values / np.maximum(counts, 1.0)


def material_interface_traction(
    model: FastTrilayerModel,
    interface: MaterialInterface,
    layer: SurfaceLayerReference,
    layer_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return material-point positions and pair force per reference area."""
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    points: list[np.ndarray] = []
    traction: list[float] = []
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
        points.append(
            interface.registry.barycentric[row] @ layer_vertices[layer_face]
        )
        traction.append(
            float(np.linalg.norm(layer_force.sum(axis=0)) / reference_weight)
        )
    return np.asarray(points), np.asarray(traction)


def write_source_data(
    samples: list[dict[str, object]],
    maximum_traction: np.ndarray,
    dominant_interface: list[str],
) -> None:
    fields = (
        "step_index",
        "time",
        "activation",
        "activation_rate",
        "axial_shortening",
        "interface_force_proxy",
        "maximum_discrete_interface_traction",
        "dominant_traction_interface",
        "ecm_internal_z_norm",
        "ecm_dissipation_step",
        "cumulative_ecm_dissipation",
        "normalized_kkt_residual",
        "volume_constraint_residual",
        "minimum_ecm_jacobian",
        "minimum_gap",
        "minimum_myocyte_face_area_ratio",
        "minimum_endocardial_face_area_ratio",
        "coupling_iterations",
        "coupling_residual",
        "passed",
    )
    with (OUTPUT / "cycle_figure_source_data.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for sample, traction, interface_name in zip(
            samples, maximum_traction, dominant_interface, strict=True
        ):
            row = dict(sample)
            row["maximum_discrete_interface_traction"] = traction
            row["dominant_traction_interface"] = interface_name
            writer.writerow(row)


def main() -> None:
    summary = json.loads((OUTPUT / "summary.json").read_text("utf-8"))
    if not bool(summary["completed"]):
        raise RuntimeError("cannot plot an incomplete development cycle")
    arrays = np.load(OUTPUT / "cycle_states.npz")
    myocyte_states = np.asarray(arrays["myocyte_vertices"], dtype=np.float64)
    ecm_states = np.asarray(arrays["ecm_vertices"], dtype=np.float64)
    endocardial_states = np.asarray(
        arrays["endocardial_vertices"], dtype=np.float64
    )
    internal_states = np.asarray(arrays["ecm_internal_z"], dtype=np.float64)
    samples = summary["samples"]

    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    times = np.asarray([float(sample["time"]) for sample in samples])
    activation = np.asarray(
        [float(sample["activation"]) for sample in samples]
    )
    shortening = 100.0 * np.asarray(
        [float(sample["axial_shortening"]) for sample in samples]
    )
    internal_norm = np.asarray(
        [float(sample["ecm_internal_z_norm"]) for sample in samples]
    )
    cumulative_dissipation = np.asarray(
        [float(sample["cumulative_ecm_dissipation"]) for sample in samples]
    )
    kkt = np.asarray(
        [float(sample["normalized_kkt_residual"]) for sample in samples]
    )
    minimum_j = np.asarray(
        [float(sample["minimum_ecm_jacobian"]) for sample in samples]
    )
    minimum_gap = np.asarray(
        [float(sample["minimum_gap"]) for sample in samples]
    )
    peak_shortening_step = int(np.argmax(shortening))
    end_step = len(samples) - 1

    myocyte_points_by_step: list[np.ndarray] = []
    myocyte_traction_by_step: list[np.ndarray] = []
    endocardial_points_by_step: list[np.ndarray] = []
    endocardial_traction_by_step: list[np.ndarray] = []
    maximum_traction: list[float] = []
    dominant_interface: list[str] = []
    for step in range(len(samples)):
        myocyte_points, myocyte_traction = material_interface_traction(
            model,
            model.myocyte_interface,
            model.myocyte,
            myocyte_states[step],
            ecm_states[step],
        )
        endocardial_points, endocardial_traction = material_interface_traction(
            model,
            model.endocardial_interface,
            model.endocardium,
            endocardial_states[step],
            ecm_states[step],
        )
        myocyte_points_by_step.append(myocyte_points)
        myocyte_traction_by_step.append(myocyte_traction)
        endocardial_points_by_step.append(endocardial_points)
        endocardial_traction_by_step.append(endocardial_traction)
        myocyte_maximum = float(np.max(myocyte_traction))
        endocardial_maximum = float(np.max(endocardial_traction))
        if myocyte_maximum >= endocardial_maximum:
            maximum_traction.append(myocyte_maximum)
            dominant_interface.append("myocyte_ecm")
        else:
            maximum_traction.append(endocardial_maximum)
            dominant_interface.append("ecm_endocardium")
    maximum_traction_array = np.asarray(maximum_traction)
    peak_traction_step = int(np.argmax(maximum_traction_array))
    write_source_data(samples, maximum_traction_array, dominant_interface)

    ecm_faces = np.vstack((model.ecm_myocyte_faces, model.ecm_endocardial_faces))
    all_reference = np.vstack(
        (model.myocyte.vertices, model.ecm_reference.vertices, model.endocardium.vertices)
    )
    bounds = (all_reference.min(axis=0), all_reference.max(axis=0))
    displacement = np.linalg.norm(
        ecm_states[peak_shortening_step] - model.ecm_reference.vertices,
        axis=1,
    )
    displacement_normalizer = mpl.colors.Normalize(
        vmin=0.0, vmax=float(displacement.max())
    )

    peak_myocyte_traction = myocyte_traction_by_step[peak_traction_step]
    peak_endocardial_traction = endocardial_traction_by_step[
        peak_traction_step
    ]
    traction_normalizer = mpl.colors.Normalize(
        vmin=0.0,
        vmax=float(
            max(np.max(peak_myocyte_traction), np.max(peak_endocardial_traction))
        ),
    )

    end_tetrahedral_memory = np.linalg.norm(
        internal_states[end_step], axis=(1, 2)
    )
    end_nodal_memory = tetrahedral_to_nodal_scalar(
        model.ecm_reference.tetrahedra,
        end_tetrahedral_memory,
        len(model.ecm_reference.vertices),
    )
    memory_normalizer = mpl.colors.Normalize(
        vmin=0.0, vmax=float(end_nodal_memory.max())
    )

    figure = plt.figure(figsize=(16.2, 8.9), constrained_layout=True)
    figure.get_layout_engine().set(rect=(0.015, 0.075, 0.985, 0.925))
    grid = figure.add_gridspec(2, 4, height_ratios=(1.28, 0.72))
    top_axes = []

    baseline_axis = figure.add_subplot(grid[0, 0], projection="3d")
    top_axes.append(baseline_axis)
    add_uniform_surface(
        baseline_axis,
        myocyte_states[0],
        model.myocyte.faces,
        "#d95f5f",
        0.78,
    )
    add_uniform_surface(
        baseline_axis,
        ecm_states[0],
        ecm_faces,
        "#8ac58e",
        0.42,
    )
    add_uniform_surface(
        baseline_axis,
        endocardial_states[0],
        model.endocardium.faces,
        "#55b9d0",
        0.64,
    )
    configure_3d_axis(baseline_axis, bounds)
    baseline_axis.set_title("A  Reference state\nt/T = 0, activation = 0")

    contraction_axis = figure.add_subplot(grid[0, 1], projection="3d")
    top_axes.append(contraction_axis)
    add_uniform_surface(
        contraction_axis,
        myocyte_states[peak_shortening_step],
        model.myocyte.faces,
        "#d95f5f",
        0.78,
    )
    add_scalar_surface(
        contraction_axis,
        ecm_states[peak_shortening_step],
        ecm_faces,
        displacement,
        color_map="YlGn",
        normalizer=displacement_normalizer,
        alpha=0.62,
    )
    add_uniform_surface(
        contraction_axis,
        endocardial_states[peak_shortening_step],
        model.endocardium.faces,
        "#55b9d0",
        0.58,
    )
    configure_3d_axis(contraction_axis, bounds)
    contraction_axis.set_title(
        "B  Peak contraction\n"
        f"t/T = {times[peak_shortening_step]:.3g}, "
        f"shortening = {shortening[peak_shortening_step]:.2f}%"
    )
    displacement_map = mpl.cm.ScalarMappable(
        norm=displacement_normalizer, cmap="YlGn"
    )
    displacement_bar = figure.colorbar(
        displacement_map,
        ax=contraction_axis,
        shrink=0.50,
        pad=0.015,
        aspect=18,
    )
    displacement_bar.set_label("ECM |u|", fontsize=7)
    displacement_bar.ax.tick_params(labelsize=6)

    transfer_axis = figure.add_subplot(grid[0, 2], projection="3d")
    top_axes.append(transfer_axis)
    add_uniform_surface(
        transfer_axis,
        myocyte_states[peak_traction_step],
        model.myocyte.faces,
        "#d95f5f",
        0.35,
    )
    add_uniform_surface(
        transfer_axis,
        ecm_states[peak_traction_step],
        ecm_faces,
        "#8ac58e",
        0.32,
    )
    add_uniform_surface(
        transfer_axis,
        endocardial_states[peak_traction_step],
        model.endocardium.faces,
        "#55b9d0",
        0.42,
    )
    transfer_axis.scatter(
        myocyte_points_by_step[peak_traction_step][:, 0],
        myocyte_points_by_step[peak_traction_step][:, 1],
        myocyte_points_by_step[peak_traction_step][:, 2],
        c=peak_myocyte_traction,
        cmap="magma",
        norm=traction_normalizer,
        s=20,
        linewidth=0.15,
        edgecolor="black",
        depthshade=False,
        label="myocyte–ECM",
    )
    transfer_axis.scatter(
        endocardial_points_by_step[peak_traction_step][:, 0],
        endocardial_points_by_step[peak_traction_step][:, 1],
        endocardial_points_by_step[peak_traction_step][:, 2],
        c=peak_endocardial_traction,
        cmap="magma",
        norm=traction_normalizer,
        marker="^",
        s=22,
        linewidth=0.15,
        edgecolor="black",
        depthshade=False,
        label="ECM–endocardium",
    )
    configure_3d_axis(transfer_axis, bounds)
    transfer_axis.set_title(
        "C  Peak discrete interface traction\n"
        f"t/T = {times[peak_traction_step]:.3g} "
        f"({'coincides with B' if peak_traction_step == peak_shortening_step else 'distinct from B'})"
    )
    transfer_axis.legend(frameon=False, fontsize=6, loc="upper left")
    traction_map = mpl.cm.ScalarMappable(
        norm=traction_normalizer, cmap="magma"
    )
    traction_bar = figure.colorbar(
        traction_map,
        ax=transfer_axis,
        shrink=0.50,
        pad=0.015,
        aspect=18,
    )
    traction_bar.set_label("pair force / reference area", fontsize=7)
    traction_bar.ax.tick_params(labelsize=6)

    end_axis = figure.add_subplot(grid[0, 3], projection="3d")
    top_axes.append(end_axis)
    add_uniform_surface(
        end_axis,
        myocyte_states[end_step],
        model.myocyte.faces,
        "#d95f5f",
        0.72,
    )
    add_scalar_surface(
        end_axis,
        ecm_states[end_step],
        ecm_faces,
        end_nodal_memory,
        color_map="viridis",
        normalizer=memory_normalizer,
        alpha=0.65,
    )
    add_uniform_surface(
        end_axis,
        endocardial_states[end_step],
        model.endocardium.faces,
        "#55b9d0",
        0.58,
    )
    configure_3d_axis(end_axis, bounds)
    end_axis.set_title(
        "D  Cycle end\n"
        f"activation = 0, residual shortening = {shortening[end_step]:.4f}%"
    )
    memory_map = mpl.cm.ScalarMappable(norm=memory_normalizer, cmap="viridis")
    memory_bar = figure.colorbar(
        memory_map,
        ax=end_axis,
        shrink=0.50,
        pad=0.015,
        aspect=18,
    )
    memory_bar.set_label("ECM residual |Z|", fontsize=7)
    memory_bar.ax.tick_params(labelsize=6)

    response_axis = figure.add_subplot(grid[1, 0])
    response_axis.plot(times, shortening, "o-", color="#a33a3a", lw=1.6, ms=3)
    response_axis.set_xlabel("Cycle phase t/T")
    response_axis.set_ylabel("Axial shortening (%)", color="#a33a3a")
    activation_axis = response_axis.twinx()
    activation_axis.plot(
        times, activation, "--", color="#314e86", lw=1.4
    )
    activation_axis.set_ylabel("Activation", color="#314e86")
    response_axis.set_title("Active command and contraction")
    response_axis.grid(alpha=0.22)

    hysteresis_axis = figure.add_subplot(grid[1, 1])
    split = peak_shortening_step + 1
    hysteresis_axis.plot(
        activation[:split],
        shortening[:split],
        "o-",
        color="#bd4a4a",
        lw=1.6,
        ms=3,
        label="contraction",
    )
    hysteresis_axis.plot(
        activation[peak_shortening_step:],
        shortening[peak_shortening_step:],
        "s--",
        color="#3977a8",
        lw=1.4,
        ms=3,
        label="relaxation",
    )
    hysteresis_axis.set_xlabel("Activation")
    hysteresis_axis.set_ylabel("Axial shortening (%)")
    hysteresis_axis.set_title("Cycle response path")
    hysteresis_axis.legend(frameon=False, fontsize=7)
    hysteresis_axis.grid(alpha=0.22)

    memory_axis = figure.add_subplot(grid[1, 2])
    memory_axis.plot(times, internal_norm, "o-", color="#5d3c8f", lw=1.6, ms=3)
    memory_axis.set_xlabel("Cycle phase t/T")
    memory_axis.set_ylabel("ECM internal-variable norm", color="#5d3c8f")
    dissipation_axis = memory_axis.twinx()
    dissipation_axis.plot(
        times,
        cumulative_dissipation,
        "-",
        color="#c47a22",
        lw=1.5,
    )
    dissipation_axis.set_ylabel("Cumulative dissipation proxy", color="#c47a22")
    memory_axis.set_title("Viscoelastic memory and dissipation")
    memory_axis.grid(alpha=0.22)

    audit_axis = figure.add_subplot(grid[1, 3])
    audit_axis.semilogy(times, kkt, "o-", color="#284f8f", lw=1.5, ms=3)
    audit_axis.axhline(1.0e-5, color="#b3261e", ls="--", lw=1.1)
    audit_axis.set_xlabel("Cycle phase t/T")
    audit_axis.set_ylabel("Normalized KKT", color="#284f8f")
    geometry_axis = audit_axis.twinx()
    geometry_axis.plot(times, minimum_j, "s-", color="#2f7d4b", ms=3)
    geometry_axis.plot(times, minimum_gap, "^-", color="#8d5c9e", ms=3)
    geometry_axis.set_ylabel("min J / min gap")
    audit_axis.set_title("Equilibrium and geometry gates")
    audit_axis.grid(alpha=0.22, which="both")

    figure.suptitle(
        "EFE Node 1 · N1-1 single-cycle route connection (3D DCM–SLS ECM–DCM)",
        fontsize=14.2,
        weight="bold",
    )
    figure.text(
        0.5,
        0.016,
        (
            "Red: active myocardial DCM · green/viridis: shared 3D viscoelastic "
            "cardiac-jelly ECM · cyan: passive endocardial DCM. "
            "16-step development cycle only; not time-step converged, "
            "cycle-stable, mesh-converged, or physiologically calibrated."
        ),
        ha="center",
        fontsize=8.4,
    )
    figure.savefig(
        OUTPUT / "n1_1_development_cycle_stage_figure_v01.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    figure.savefig(
        OUTPUT / "n1_1_development_cycle_stage_figure_v01.svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)

    figure_report = {
        "schema_version": "efe_node1_n1_1_stage_figure_v01",
        "source_summary": str(OUTPUT / "summary.json"),
        "source_states": str(OUTPUT / "cycle_states.npz"),
        "peak_shortening_step": peak_shortening_step,
        "peak_interface_traction_step": peak_traction_step,
        "peak_interface_traction": float(
            maximum_traction_array[peak_traction_step]
        ),
        "dominant_traction_interface": dominant_interface[
            peak_traction_step
        ],
        "traction_definition": (
            "magnitude of each material-pair force divided by its frozen "
            "reference quadrature area weight"
        ),
        "peak_events_coincide": peak_shortening_step == peak_traction_step,
        "output_png": str(
            OUTPUT / "n1_1_development_cycle_stage_figure_v01.png"
        ),
        "output_svg": str(
            OUTPUT / "n1_1_development_cycle_stage_figure_v01.svg"
        ),
    }
    (OUTPUT / "stage_figure_manifest_v01.json").write_text(
        json.dumps(figure_report, indent=2), encoding="utf-8"
    )
    print(json.dumps(figure_report, indent=2))


if __name__ == "__main__":
    main()
