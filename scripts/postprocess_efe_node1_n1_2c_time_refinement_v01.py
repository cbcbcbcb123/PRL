from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import (  # noqa: E402
    MaterialInterface,
    SurfaceLayerReference,
    build_fast_trilayer_model,
)
from hybrid.efe_time_refinement import (  # noqa: E402
    dense_cycle_integral,
    dense_cycle_peak,
    dense_linear_cycle,
    dense_waveform_relative_difference,
    richardson_extrapolation,
    step_for_registered_phase,
    symmetric_relative_difference,
    uniform_cycle_phases,
)
from route_h.contact_adhesion import (  # noqa: E402
    material_tether_energy_force_with_reference,
)
from route_h.ecm_finite_strain import (  # noqa: E402
    deformation_gradient,
    density_and_first_piola,
)


AUTHORIZATION = (
    "project_control/"
    "efe_node1_n1_2c_t64_acceptance_and_p5_authorization_decision_v01.md"
)
OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2c_time_adjudication_v01_20260826"
)
COMMON_PHASES = (0.0, 0.25, 0.5, 0.75, 1.0)
DENSE_SAMPLE_COUNT = 4097
WAVEFORM_GATE = 0.02
INTEGRAL_GATE = 0.02
PEAK_AMPLITUDE_GATE = 0.02
PEAK_PHASE_GATE = 0.01
DISSIPATION_GATE = 0.05
FIELD_GATE = 0.05
FIELD_P95_GATE = 0.05

WAVEFORM_COLUMNS = (
    "axial_shortening",
    "maximum_discrete_interface_traction",
    "p95_discrete_interface_traction",
    "total_stored_energy",
    "ecm_equilibrium_energy",
    "ecm_viscoelastic_energy",
    "ecm_internal_z_norm",
)


@dataclass(frozen=True)
class TimeLevel:
    label: str
    steps: int
    cycle: int
    directory: Path
    run_summary_path: Path


LEVELS = (
    TimeLevel(
        "T16",
        16,
        8,
        ROOT
        / "results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820"
        / "cycle_08",
        ROOT
        / "results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820"
        / "summary.json",
    ),
    TimeLevel(
        "T32",
        32,
        2,
        ROOT
        / "results/hybrid/efe_node1_n1_2c_t32_transactional_cycle_v01_20260826"
        / "transaction_engine/cycle_02",
        ROOT
        / "results/hybrid/efe_node1_n1_2c_t32_transactional_cycle_v01_20260826"
        / "summary.json",
    ),
    TimeLevel(
        "T64",
        64,
        2,
        ROOT
        / "results/hybrid/efe_node1_n1_2c_t64_transactional_cycle_v01_20260826"
        / "transaction_engine/cycle_02",
        ROOT
        / "results/hybrid/efe_node1_n1_2c_t64_transactional_cycle_v01_20260826"
        / "summary.json",
    ),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_timeseries(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    if not records:
        raise ValueError(f"empty timeseries: {path}")
    columns: dict[str, np.ndarray] = {}
    for key in records[0]:
        if key == "passed":
            columns[key] = np.asarray(
                [record[key].lower() == "true" for record in records],
                dtype=np.bool_,
            )
        else:
            columns[key] = np.asarray(
                [float(record[key]) for record in records],
                dtype=np.float64,
            )
    return columns


def load_level(level: TimeLevel) -> dict[str, Any]:
    timeseries_path = level.directory / "cycle_timeseries.csv"
    states_path = level.directory / "cycle_states.npz"
    cycle_summary_path = level.directory / "cycle_summary.json"
    for path in (
        timeseries_path,
        states_path,
        cycle_summary_path,
        level.run_summary_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    timeseries = read_timeseries(timeseries_path)
    expected_phases = uniform_cycle_phases(level.steps)
    if not np.array_equal(timeseries["t_over_T"], expected_phases):
        raise ValueError(f"{level.label} phases do not match the registered grid")
    if len(timeseries["step"]) != level.steps + 1:
        raise ValueError(f"{level.label} does not contain one inclusive cycle")
    if not np.all(timeseries["passed"]):
        raise ValueError(f"{level.label} contains a failed accepted sample")

    with np.load(states_path) as archive:
        states = {name: np.asarray(archive[name]).copy() for name in archive.files}
    required = {
        "variables",
        "myocyte_vertices",
        "ecm_vertices",
        "endocardial_vertices",
        "ecm_internal_z",
    }
    if required.difference(states):
        raise ValueError(f"{level.label} state archive is incomplete")
    if any(states[name].shape[0] != level.steps + 1 for name in required):
        raise ValueError(f"{level.label} state phase dimensions are inconsistent")

    run_summary = read_json(level.run_summary_path)
    if not bool(run_summary.get("passed")):
        raise ValueError(f"{level.label} run summary did not pass")
    matching = [
        item
        for item in run_summary["cycle_summaries"]
        if int(item["cycle"]) == level.cycle
    ]
    if len(matching) != 1 or not bool(matching[0].get("cycle_stable")):
        raise ValueError(f"{level.label} selected cycle is not stable")
    cycle_summary = read_json(cycle_summary_path)
    if int(cycle_summary["cycle"]) != level.cycle:
        raise ValueError(f"{level.label} cycle summary identity mismatch")
    if not bool(cycle_summary.get("cycle_stable")):
        raise ValueError(f"{level.label} cycle summary is not stable")

    recorded_dissipation = float(matching[0]["cycle_dissipation"])
    csv_dissipation = float(timeseries["cumulative_ecm_dissipation"][-1])
    if not np.isclose(recorded_dissipation, csv_dissipation, rtol=1.0e-12):
        raise ValueError(f"{level.label} dissipation mismatch")
    return {
        "spec": level,
        "timeseries": timeseries,
        "states": states,
        "run_summary": run_summary,
        "cycle_summary": matching[0],
        "input_hashes": {
            "timeseries": file_sha256(timeseries_path),
            "states": file_sha256(states_path),
            "cycle_summary": file_sha256(cycle_summary_path),
            "run_summary": file_sha256(level.run_summary_path),
        },
    }


def scalar_relative_difference(first: float, second: float) -> float:
    values = np.asarray([first], dtype=np.float64)
    other = np.asarray([second], dtype=np.float64)
    return symmetric_relative_difference(values, other)


def reconstruct_ecm_fields(
    model: Any,
    vertices: np.ndarray,
    internal_z: np.ndarray,
    previous_internal_z: np.ndarray | None,
    time_step: float,
) -> dict[str, np.ndarray]:
    reference = model.ecm_reference
    count = len(reference.tetrahedra)
    jacobian = np.empty(count, dtype=np.float64)
    principal_strain = np.empty(count, dtype=np.float64)
    principal_stress = np.empty(count, dtype=np.float64)
    equilibrium_density = np.empty(count, dtype=np.float64)
    viscoelastic_density = np.empty(count, dtype=np.float64)
    dissipation_density = np.zeros(count, dtype=np.float64)
    identity = np.eye(3, dtype=np.float64)
    for tet_id, tetrahedron in enumerate(reference.tetrahedra):
        deformation = deformation_gradient(
            vertices[tetrahedron],
            reference.dm_inverse[tet_id],
        )
        densities, first_piola = density_and_first_piola(
            deformation,
            internal_z[tet_id],
            mu_eq=model.mu_eq,
            kappa_eq=model.kappa_eq,
            mu_ve=model.mu_ve,
        )
        determinant = float(densities["J"])
        green_lagrange = 0.5 * (deformation.T @ deformation - identity)
        cauchy = first_piola @ deformation.T / determinant
        jacobian[tet_id] = determinant
        principal_strain[tet_id] = float(np.linalg.eigvalsh(green_lagrange)[-1])
        principal_stress[tet_id] = float(np.linalg.eigvalsh(cauchy)[-1])
        equilibrium_density[tet_id] = float(
            densities["ecm_equilibrium_density"]
        )
        viscoelastic_density[tet_id] = float(
            densities["ecm_viscoelastic_density"]
        )
        if previous_internal_z is not None:
            rate = (internal_z[tet_id] - previous_internal_z[tet_id]) / time_step
            dissipation_density[tet_id] = model.eta_ve * float(np.sum(rate * rate))
    return {
        "ecm_jacobian": jacobian,
        "ecm_max_principal_green_lagrange_strain": principal_strain,
        "ecm_max_principal_cauchy_stress": principal_stress,
        "ecm_equilibrium_energy_density": equilibrium_density,
        "ecm_viscoelastic_energy_density": viscoelastic_density,
        "ecm_dissipation_density": dissipation_density,
    }


def reconstruct_interface_tractions(
    interface: MaterialInterface,
    cell_reference: SurfaceLayerReference,
    ecm_reference: Any,
    cell_vertices: np.ndarray,
    ecm_vertices: np.ndarray,
) -> dict[str, np.ndarray]:
    row_by_id = {
        int(point_id): row
        for row, point_id in enumerate(interface.registry.point_ids.tolist())
    }
    normal_values: list[float] = []
    tangential_values: list[float] = []
    magnitude_values: list[float] = []
    for tether in interface.tethers:
        row = row_by_id[tether.material_point_id]
        cell_face = cell_reference.faces[int(interface.registry.face_ids[row])]
        ecm_face = interface.ecm_boundary_faces[tether.ecm_face_id]
        _, local_cell_force, _, state = material_tether_energy_force_with_reference(
            cell_vertices,
            cell_face,
            ecm_vertices,
            ecm_face,
            reference_master_vertices=cell_reference.vertices,
            reference_slave_vertices=ecm_reference.vertices,
            master_barycentric=interface.registry.barycentric[row],
            slave_barycentric=tether.ecm_barycentric,
            reference_weight=float(interface.registry.reference_weights[row]),
            g0_pair=tether.reference_gap,
            normal_orientation_sign=tether.normal_orientation_sign,
            reference_t1=tether.reference_t1,
            reference_t2=tether.reference_t2,
            adhesion_work=tether.adhesion_work,
            opening_cutoff=tether.opening_cutoff,
            tangential_stiffness=tether.tangential_stiffness,
        )
        reference_weight = float(interface.registry.reference_weights[row])
        if reference_weight <= 0.0:
            raise ValueError("interface reference weight must be positive")
        traction = np.sum(local_cell_force, axis=0) / reference_weight
        normal = np.asarray(state["normal"], dtype=np.float64)
        t1 = np.asarray(state["t1"], dtype=np.float64)
        t2 = np.asarray(state["t2"], dtype=np.float64)
        normal_component = float(np.dot(traction, normal))
        tangential_component = float(
            np.hypot(np.dot(traction, t1), np.dot(traction, t2))
        )
        normal_values.append(normal_component)
        tangential_values.append(tangential_component)
        magnitude_values.append(float(np.linalg.norm(traction)))
    return {
        "normal": np.asarray(normal_values, dtype=np.float64),
        "tangential": np.asarray(tangential_values, dtype=np.float64),
        "magnitude": np.asarray(magnitude_values, dtype=np.float64),
    }


def reconstruct_common_phase_fields(
    level_data: dict[str, Any],
    model: Any,
) -> dict[str, dict[str, np.ndarray]]:
    level: TimeLevel = level_data["spec"]
    states = level_data["states"]
    result: dict[str, dict[str, np.ndarray]] = {}
    phase_zero_myocyte = states["myocyte_vertices"][0]
    phase_zero_ecm = states["ecm_vertices"][0]
    phase_zero_endocardial = states["endocardial_vertices"][0]
    for phase in COMMON_PHASES:
        step = step_for_registered_phase(phase, level.steps)
        previous_z = None if step == 0 else states["ecm_internal_z"][step - 1]
        ecm_fields = reconstruct_ecm_fields(
            model,
            states["ecm_vertices"][step],
            states["ecm_internal_z"][step],
            previous_z,
            1.0 / level.steps,
        )
        myocyte_tractions = reconstruct_interface_tractions(
            model.myocyte_interface,
            model.myocyte,
            model.ecm_reference,
            states["myocyte_vertices"][step],
            states["ecm_vertices"][step],
        )
        endocardial_tractions = reconstruct_interface_tractions(
            model.endocardial_interface,
            model.endocardium,
            model.ecm_reference,
            states["endocardial_vertices"][step],
            states["ecm_vertices"][step],
        )
        result[f"{phase:.4f}"] = {
            "myocyte_displacement": (
                states["myocyte_vertices"][step] - phase_zero_myocyte
            ),
            "ecm_displacement": states["ecm_vertices"][step] - phase_zero_ecm,
            "endocardial_displacement": (
                states["endocardial_vertices"][step] - phase_zero_endocardial
            ),
            "ecm_internal_z": states["ecm_internal_z"][step],
            **ecm_fields,
            "myocyte_jelly_normal_traction": myocyte_tractions["normal"],
            "myocyte_jelly_tangential_traction": myocyte_tractions[
                "tangential"
            ],
            "myocyte_jelly_traction_magnitude": myocyte_tractions["magnitude"],
            "jelly_endocardium_normal_traction": endocardial_tractions["normal"],
            "jelly_endocardium_tangential_traction": endocardial_tractions[
                "tangential"
            ],
            "jelly_endocardium_traction_magnitude": endocardial_tractions[
                "magnitude"
            ],
        }
    return result


def p95_magnitude(values: np.ndarray) -> float:
    selected = np.asarray(values, dtype=np.float64)
    if selected.ndim > 1 and selected.shape[-1] == 3:
        selected = np.linalg.norm(selected, axis=-1)
    return float(np.quantile(np.abs(selected).reshape(-1), 0.95))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write an empty table: {path}")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def global_rows(level_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    labels = ("T16", "T32", "T64")
    phases = {
        label: level_data[label]["timeseries"]["t_over_T"] for label in labels
    }
    values = {
        label: level_data[label]["timeseries"] for label in labels
    }

    for quantity in WAVEFORM_COLUMNS:
        difference_16_32 = dense_waveform_relative_difference(
            phases["T16"], values["T16"][quantity],
            phases["T32"], values["T32"][quantity],
        )
        difference_32_64 = dense_waveform_relative_difference(
            phases["T32"], values["T32"][quantity],
            phases["T64"], values["T64"][quantity],
        )
        rows.append({
            "kind": "waveform_normalized_l2",
            "quantity": quantity,
            "T16": "",
            "T32": "",
            "T64": "",
            "T16_T32_difference": difference_16_32,
            "T32_T64_difference": difference_32_64,
            "gate": WAVEFORM_GATE,
            "gate_unit": "relative",
            "passed_T32_T64": difference_32_64 <= WAVEFORM_GATE,
            "order_status": "not_applicable_to_waveform_norm",
            "observed_order": "",
            "richardson_extrapolated": "",
        })

    scalar_triplets: list[tuple[str, str, tuple[float, float, float], float, str]] = []
    for quantity in WAVEFORM_COLUMNS:
        integrals = tuple(
            dense_cycle_integral(phases[label], values[label][quantity])
            for label in labels
        )
        scalar_triplets.append((
            "cycle_integral", quantity, integrals, INTEGRAL_GATE, "relative"
        ))
        peaks = tuple(
            dense_cycle_peak(phases[label], values[label][quantity])
            for label in labels
        )
        scalar_triplets.append((
            "peak_amplitude",
            quantity,
            tuple(peak.value for peak in peaks),
            PEAK_AMPLITUDE_GATE,
            "relative",
        ))
        scalar_triplets.append((
            "peak_phase",
            quantity,
            tuple(peak.phase for peak in peaks),
            PEAK_PHASE_GATE,
            "absolute_phase",
        ))

    dissipations = tuple(
        float(level_data[label]["cycle_summary"]["cycle_dissipation"])
        for label in labels
    )
    scalar_triplets.append((
        "cycle_dissipation",
        "ecm_dissipation",
        dissipations,
        DISSIPATION_GATE,
        "relative",
    ))

    for kind, quantity, triplet, gate, gate_unit in scalar_triplets:
        if gate_unit == "absolute_phase":
            difference_16_32 = abs(triplet[0] - triplet[1])
            difference_32_64 = abs(triplet[1] - triplet[2])
        else:
            difference_16_32 = scalar_relative_difference(triplet[0], triplet[1])
            difference_32_64 = scalar_relative_difference(triplet[1], triplet[2])
        richardson = richardson_extrapolation(*triplet)
        rows.append({
            "kind": kind,
            "quantity": quantity,
            "T16": triplet[0],
            "T32": triplet[1],
            "T64": triplet[2],
            "T16_T32_difference": difference_16_32,
            "T32_T64_difference": difference_32_64,
            "gate": gate,
            "gate_unit": gate_unit,
            "passed_T32_T64": difference_32_64 <= gate,
            "order_status": richardson.status,
            "observed_order": (
                "" if richardson.order is None else richardson.order
            ),
            "richardson_extrapolated": (
                "" if richardson.extrapolated is None else richardson.extrapolated
            ),
        })
    return rows


def dense_waveform_rows(
    level_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    dense_by_level: dict[str, dict[str, np.ndarray]] = {}
    dense_phase: np.ndarray | None = None
    for label in ("T16", "T32", "T64"):
        timeseries = level_data[label]["timeseries"]
        level_values: dict[str, np.ndarray] = {}
        for quantity in WAVEFORM_COLUMNS:
            current_phase, current_values = dense_linear_cycle(
                timeseries["t_over_T"],
                timeseries[quantity],
                sample_count=DENSE_SAMPLE_COUNT,
            )
            if dense_phase is None:
                dense_phase = current_phase
            elif not np.array_equal(dense_phase, current_phase):
                raise RuntimeError("dense phase grid drift")
            level_values[quantity] = current_values
        dense_by_level[label] = level_values
    if dense_phase is None:
        raise RuntimeError("dense phase grid was not constructed")
    rows: list[dict[str, Any]] = []
    for index, phase in enumerate(dense_phase):
        row: dict[str, Any] = {"t_over_T": float(phase)}
        for label in ("T16", "T32", "T64"):
            for quantity in WAVEFORM_COLUMNS:
                row[f"{label}_{quantity}"] = float(
                    dense_by_level[label][quantity][index]
                )
        rows.append(row)
    return rows


def field_rows(
    fields: dict[str, dict[str, dict[str, np.ndarray]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for phase in COMMON_PHASES:
        phase_key = f"{phase:.4f}"
        field_names = sorted(fields["T16"][phase_key])
        for field_name in field_names:
            arrays = {
                label: fields[label][phase_key][field_name]
                for label in ("T16", "T32", "T64")
            }
            difference_16_32 = symmetric_relative_difference(
                arrays["T16"], arrays["T32"]
            )
            difference_32_64 = symmetric_relative_difference(
                arrays["T32"], arrays["T64"]
            )
            rows.append({
                "phase": phase,
                "field": field_name,
                "summary": "normalized_l2",
                "T16": "",
                "T32": "",
                "T64": "",
                "T16_T32_difference": difference_16_32,
                "T32_T64_difference": difference_32_64,
                "gate": FIELD_GATE,
                "passed_T32_T64": difference_32_64 <= FIELD_GATE,
            })
            p95 = {
                label: p95_magnitude(arrays[label])
                for label in ("T16", "T32", "T64")
            }
            p95_difference_16_32 = scalar_relative_difference(
                p95["T16"], p95["T32"]
            )
            p95_difference_32_64 = scalar_relative_difference(
                p95["T32"], p95["T64"]
            )
            rows.append({
                "phase": phase,
                "field": field_name,
                "summary": "absolute_p95",
                "T16": p95["T16"],
                "T32": p95["T32"],
                "T64": p95["T64"],
                "T16_T32_difference": p95_difference_16_32,
                "T32_T64_difference": p95_difference_32_64,
                "gate": FIELD_P95_GATE,
                "passed_T32_T64": p95_difference_32_64 <= FIELD_P95_GATE,
            })
    return rows


def sensitive_phase_rows(
    level_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    registered = (0.25, 0.6875, 0.8125, 0.875)
    rows: list[dict[str, Any]] = []
    for label in ("T16", "T32", "T64"):
        spec: TimeLevel = level_data[label]["spec"]
        series = level_data[label]["timeseries"]
        for phase in registered:
            step = step_for_registered_phase(phase, spec.steps)
            rows.append({
                "level": label,
                "phase": phase,
                "step": step,
                "normalized_kkt_residual": float(
                    series["normalized_kkt_residual"][step]
                ),
                "coupling_residual": float(series["coupling_residual"][step]),
                "coupling_iterations": int(series["coupling_iterations"][step]),
                "minimum_ecm_jacobian": float(
                    series["minimum_ecm_jacobian"][step]
                ),
                "minimum_gap": float(series["minimum_gap"][step]),
            })
    # T64 step 15 is the new repeated local coupling-sensitive phase.
    series64 = level_data["T64"]["timeseries"]
    rows.append({
        "level": "T64",
        "phase": 15.0 / 64.0,
        "step": 15,
        "normalized_kkt_residual": float(
            series64["normalized_kkt_residual"][15]
        ),
        "coupling_residual": float(series64["coupling_residual"][15]),
        "coupling_iterations": int(series64["coupling_iterations"][15]),
        "minimum_ecm_jacobian": float(
            series64["minimum_ecm_jacobian"][15]
        ),
        "minimum_gap": float(series64["minimum_gap"][15]),
    })
    return rows


def save_peak_field_archive(
    path: Path,
    level_data: dict[str, dict[str, Any]],
    fields: dict[str, dict[str, dict[str, np.ndarray]]],
    model: Any,
) -> None:
    peak_phase = dense_cycle_peak(
        level_data["T64"]["timeseries"]["t_over_T"],
        level_data["T64"]["timeseries"]["axial_shortening"],
    ).phase
    if not np.isclose(peak_phase, 0.5, atol=1.0 / (DENSE_SAMPLE_COUNT - 1)):
        raise ValueError("T64 contraction peak is not the registered common phase 0.5")
    phase_key = "0.5000"
    states32 = level_data["T32"]["states"]
    states64 = level_data["T64"]["states"]
    step32 = step_for_registered_phase(0.5, 32)
    step64 = step_for_registered_phase(0.5, 64)
    displacement32 = fields["T32"][phase_key]["ecm_displacement"]
    displacement64 = fields["T64"][phase_key]["ecm_displacement"]
    np.savez_compressed(
        path,
        reference_ecm_vertices=model.ecm_reference.vertices,
        ecm_tetrahedra=model.ecm_reference.tetrahedra,
        t32_ecm_vertices=states32["ecm_vertices"][step32],
        t64_ecm_vertices=states64["ecm_vertices"][step64],
        t64_myocyte_vertices=states64["myocyte_vertices"][step64],
        t64_endocardial_vertices=states64["endocardial_vertices"][step64],
        t64_ecm_displacement_magnitude=np.linalg.norm(displacement64, axis=1),
        t32_t64_ecm_displacement_difference_magnitude=np.linalg.norm(
            displacement64 - displacement32,
            axis=1,
        ),
        t64_ecm_jacobian=fields["T64"][phase_key]["ecm_jacobian"],
        t64_ecm_max_principal_cauchy_stress=fields["T64"][phase_key][
            "ecm_max_principal_cauchy_stress"
        ],
        t32_t64_ecm_jacobian_difference=(
            fields["T64"][phase_key]["ecm_jacobian"]
            - fields["T32"][phase_key]["ecm_jacobian"]
        ),
        peak_phase=np.asarray([peak_phase], dtype=np.float64),
    )


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"create-only output already exists: {OUTPUT}")
    level_data = {level.label: load_level(level) for level in LEVELS}
    model = build_fast_trilayer_model(
        dcm_level="D0",
        ecm_level="E0",
        ecm_footprint_scale=1.5,
    )
    expected_shapes = {
        "myocyte_vertices": model.myocyte.vertices.shape,
        "ecm_vertices": model.ecm_reference.vertices.shape,
        "endocardial_vertices": model.endocardium.vertices.shape,
        "ecm_internal_z": (len(model.ecm_reference.tetrahedra), 3, 3),
    }
    for label, data in level_data.items():
        for name, spatial_shape in expected_shapes.items():
            if data["states"][name].shape[1:] != spatial_shape:
                raise ValueError(f"{label} {name} does not match frozen D0/E0/F150")

    global_table = global_rows(level_data)
    dense_table = dense_waveform_rows(level_data)
    fields = {
        label: reconstruct_common_phase_fields(level_data[label], model)
        for label in ("T16", "T32", "T64")
    }
    field_table = field_rows(fields)
    sensitive_table = sensitive_phase_rows(level_data)

    global_gate_passed = all(
        bool(row["passed_T32_T64"]) for row in global_table
    )
    field_gate_passed = all(
        bool(row["passed_T32_T64"]) for row in field_table
    )
    within_level_periodic = all(
        bool(level_data[label]["cycle_summary"]["cycle_stable"])
        for label in ("T16", "T32", "T64")
    )
    safety = {
        label: {
            "minimum_ecm_jacobian": float(
                level_data[label]["cycle_summary"]["minimum_ecm_jacobian"]
            ),
            "minimum_gap": float(
                level_data[label]["cycle_summary"]["minimum_gap"]
            ),
            "maximum_kkt": float(
                level_data[label]["cycle_summary"]["maximum_kkt"]
            ),
            "maximum_coupling_residual": float(
                level_data[label]["cycle_summary"]["maximum_coupling_residual"]
            ),
        }
        for label in ("T16", "T32", "T64")
    }
    safety_gate_passed = all(
        values["minimum_ecm_jacobian"] >= 0.5
        and values["minimum_gap"] >= -1.0e-12
        and values["maximum_kkt"] <= 1.0e-5
        and values["maximum_coupling_residual"] <= 1.0e-4
        for values in safety.values()
    )
    order_counts: dict[str, int] = {}
    for row in global_table:
        status = str(row["order_status"])
        order_counts[status] = order_counts.get(status, 0) + 1

    OUTPUT.mkdir(parents=True, exist_ok=False)
    write_csv(OUTPUT / "global_metric_table.csv", global_table)
    write_csv(OUTPUT / "field_metric_table.csv", field_table)
    write_csv(OUTPUT / "dense_waveforms.csv", dense_table)
    write_csv(OUTPUT / "sensitive_phase_table.csv", sensitive_table)
    save_peak_field_archive(
        OUTPUT / "peak_field_difference.npz",
        level_data,
        fields,
        model,
    )

    summary = {
        "schema_version": "efe_node1_n1_2c_time_adjudication_v01",
        "status": (
            "passed_registered_time_convergence_gate"
            if (
                within_level_periodic
                and global_gate_passed
                and field_gate_passed
                and safety_gate_passed
            )
            else "failed_registered_time_convergence_gate"
        ),
        "authorization": AUTHORIZATION,
        "levels": {
            label: {
                "steps_per_cycle": data["spec"].steps,
                "selected_cycle": data["spec"].cycle,
                "directory": str(data["spec"].directory.relative_to(ROOT)),
                "input_hashes": data["input_hashes"],
            }
            for label, data in level_data.items()
        },
        "comparison_rules": {
            "dense_sample_count": DENSE_SAMPLE_COUNT,
            "waveform_interpolation": "linear",
            "integral_rule": "dense-linear trapezoid",
            "common_field_phases": list(COMMON_PHASES),
            "relative_difference": (
                "symmetric L2 normalized by max norm with 1e-12 guard"
            ),
            "field_derivation_authorization": AUTHORIZATION,
        },
        "gates": {
            "waveform": WAVEFORM_GATE,
            "integral": INTEGRAL_GATE,
            "peak_amplitude": PEAK_AMPLITUDE_GATE,
            "peak_phase": PEAK_PHASE_GATE,
            "dissipation": DISSIPATION_GATE,
            "field": FIELD_GATE,
            "field_p95": FIELD_P95_GATE,
        },
        "checks": {
            "within_level_periodic": within_level_periodic,
            "global_time_gate": global_gate_passed,
            "field_time_gate": field_gate_passed,
            "safety_gate": safety_gate_passed,
        },
        "maximum_differences": {
            "global_T16_T32": max(
                float(row["T16_T32_difference"])
                for row in global_table
                if row["gate_unit"] == "relative"
            ),
            "global_T32_T64": max(
                float(row["T32_T64_difference"])
                for row in global_table
                if row["gate_unit"] == "relative"
            ),
            "field_T16_T32": max(
                float(row["T16_T32_difference"]) for row in field_table
            ),
            "field_T32_T64": max(
                float(row["T32_T64_difference"]) for row in field_table
            ),
        },
        "failed_global_rows": [
            {"kind": row["kind"], "quantity": row["quantity"]}
            for row in global_table
            if not bool(row["passed_T32_T64"])
        ],
        "failed_field_rows": [
            {
                "phase": row["phase"],
                "field": row["field"],
                "summary": row["summary"],
                "difference": row["T32_T64_difference"],
            }
            for row in field_table
            if not bool(row["passed_T32_T64"])
        ],
        "observed_order_status_counts": order_counts,
        "safety": safety,
        "source_fingerprints": {
            str(Path(__file__).resolve().relative_to(ROOT)): file_sha256(
                Path(__file__).resolve()
            ),
            "src/hybrid/efe_time_refinement.py": file_sha256(
                ROOT / "src/hybrid/efe_time_refinement.py"
            ),
        },
        "outputs": {
            name: file_sha256(OUTPUT / name)
            for name in (
                "global_metric_table.csv",
                "field_metric_table.csv",
                "dense_waveforms.csv",
                "sensitive_phase_table.csv",
                "peak_field_difference.npz",
            )
        },
        "passed": (
            within_level_periodic
            and global_gate_passed
            and field_gate_passed
            and safety_gate_passed
        ),
        "evidence_boundary": (
            "This is the preregistered T16/T32/T64 temporal adjudication for "
            "the fixed D0/E0/F150 baseline. It does not establish spatial or "
            "parameter convergence, biological validity, or the necessity of "
            "DCM-FEM, and it does not authorize T128 or N1-2d."
        ),
    }
    summary_path = OUTPUT / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
