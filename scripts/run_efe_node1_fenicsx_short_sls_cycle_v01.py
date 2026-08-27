from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import (  # noqa: E402
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.fenicsx_ecm_backend import FenicsxECMBackend  # noqa: E402
from route_h.ecm_finite_strain import (  # noqa: E402
    deformation_gradient,
    internal_variable_rate,
    relaxation_dissipation,
    relax_internal_variable_exact,
)


BASELINE = (
    ROOT
    / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v03_20260818"
    / "F150"
)
DEFAULT_A010 = BASELINE / "solver_step_02/activation_010_state.npz"
DEFAULT_A020 = BASELINE / "solver_step_07/activation_020_state.npz"
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819"
    / "fenicsx_p1_short_sls_cycle_v01"
)


def relative_error(actual: np.ndarray | float, expected: np.ndarray | float) -> float:
    return float(
        np.linalg.norm(np.asarray(actual) - np.asarray(expected))
        / max(
            1.0e-14,
            float(np.linalg.norm(np.asarray(actual))),
            float(np.linalg.norm(np.asarray(expected))),
        )
    )


def full_stored_gradient(evaluation) -> np.ndarray:
    return np.concatenate(
        (
            evaluation.myocyte_energy_gradient.reshape(-1),
            evaluation.ecm_energy_gradient.reshape(-1),
            evaluation.endocardial_energy_gradient.reshape(-1),
        )
    )


def advance_internal_z(
    model,
    ecm_vertices: np.ndarray,
    internal_z: np.ndarray,
    time_step: float,
) -> tuple[np.ndarray, float]:
    updated = np.empty_like(internal_z)
    integrated_dissipation = 0.0
    for tetrahedron_id, tetrahedron in enumerate(
        model.ecm_reference.tetrahedra
    ):
        deformation = deformation_gradient(
            ecm_vertices[tetrahedron],
            model.ecm_reference.dm_inverse[tetrahedron_id],
        )
        rate = internal_variable_rate(
            deformation,
            internal_z[tetrahedron_id],
            mu_ve=model.mu_ve,
            eta_ve=model.eta_ve,
        )
        integrated_dissipation += model.ecm_reference.volume0[
            tetrahedron_id
        ] * relaxation_dissipation(rate, model.eta_ve)
        updated[tetrahedron_id] = relax_internal_variable_exact(
            deformation,
            internal_z[tetrahedron_id],
            time_step,
            mu_ve=model.mu_ve,
            eta_ve=model.eta_ve,
        )
    return updated, float(integrated_dissipation)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a010", type=Path, default=DEFAULT_A010)
    parser.add_argument("--a020", type=Path, default=DEFAULT_A020)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--period", type=float, default=1.0)
    arguments = parser.parse_args()
    if arguments.period <= 0.0:
        raise ValueError("period must be positive")

    a010_path = arguments.a010.resolve()
    a020_path = arguments.a020.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    a010 = np.load(a010_path)
    a020 = np.load(a020_path)
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    backend = FenicsxECMBackend(model.ecm_reference)
    reference_state = {
        "myocyte": model.myocyte.vertices,
        "ecm": model.ecm_reference.vertices,
        "endocardium": model.endocardium.vertices,
    }

    def loaded_state(arrays) -> dict[str, np.ndarray]:
        return {
            "myocyte": np.asarray(arrays["myocyte_vertices"], dtype=np.float64),
            "ecm": np.asarray(arrays["ecm_vertices"], dtype=np.float64),
            "endocardium": np.asarray(
                arrays["endocardial_vertices"], dtype=np.float64
            ),
        }

    state_a010 = loaded_state(a010)
    state_a020 = loaded_state(a020)
    phases = (
        ("reference_start", 0.00, reference_state),
        ("ascending_a010", 0.10, state_a010),
        ("peak_a020", 0.20, state_a020),
        ("descending_a010", 0.10, state_a010),
        ("reference_end", 0.00, reference_state),
    )
    time_step = arguments.period / (len(phases) - 1)
    internal_z = np.zeros(
        (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
    )
    records = []
    z_history = []
    for phase_id, (name, activation, state) in enumerate(phases):
        z_history.append(internal_z.copy())
        reference_evaluation = evaluate_fast_trilayer_state(
            model,
            state["myocyte"],
            state["ecm"],
            state["endocardium"],
            activation=activation,
            ecm_internal_z=internal_z,
            reject_penetration=False,
        )
        fenicsx_evaluation = evaluate_fast_trilayer_state(
            model,
            state["myocyte"],
            state["ecm"],
            state["endocardium"],
            activation=activation,
            ecm_internal_z=internal_z,
            ecm_backend=backend.energy_force,
            reject_penetration=False,
        )
        reference_gradient = full_stored_gradient(reference_evaluation)
        fenicsx_gradient = full_stored_gradient(fenicsx_evaluation)
        energy_absolute_error = abs(
            fenicsx_evaluation.total_stored_energy
            - reference_evaluation.total_stored_energy
        )
        energy_relative_error = relative_error(
            fenicsx_evaluation.total_stored_energy,
            reference_evaluation.total_stored_energy,
        )
        force_absolute_error = float(
            np.linalg.norm(fenicsx_gradient - reference_gradient)
        )
        force_relative_error = relative_error(
            fenicsx_gradient, reference_gradient
        )
        energy_scale = max(
            abs(fenicsx_evaluation.total_stored_energy),
            abs(reference_evaluation.total_stored_energy),
        )
        force_scale = max(
            float(np.linalg.norm(fenicsx_gradient)),
            float(np.linalg.norm(reference_gradient)),
        )
        energy_passed = (
            energy_absolute_error <= 1.0e-12
            if energy_scale <= 1.0e-10
            else energy_relative_error <= 1.0e-8
        )
        force_passed = (
            force_absolute_error <= 1.0e-11
            if force_scale <= 1.0e-10
            else force_relative_error <= 1.0e-8
        )
        j_error = max(
            abs(
                fenicsx_evaluation.minimum_ecm_jacobian
                - reference_evaluation.minimum_ecm_jacobian
            ),
            abs(
                fenicsx_evaluation.maximum_ecm_jacobian
                - reference_evaluation.maximum_ecm_jacobian
            ),
        )
        updated_z, dissipation = advance_internal_z(
            model, state["ecm"], internal_z, time_step
        )
        records.append(
            {
                "phase_id": phase_id,
                "name": name,
                "activation": activation,
                "z_norm_before": float(np.linalg.norm(internal_z)),
                "z_norm_after": float(np.linalg.norm(updated_z)),
                "reference_total_energy": reference_evaluation.total_stored_energy,
                "fenicsx_total_energy": fenicsx_evaluation.total_stored_energy,
                "reference_ecm_viscoelastic_energy": reference_evaluation.energy_components[
                    "ecm_viscoelastic"
                ],
                "energy_absolute_error": energy_absolute_error,
                "energy_relative_error": energy_relative_error,
                "force_absolute_error": force_absolute_error,
                "force_relative_error": force_relative_error,
                "jacobian_maximum_absolute_error": j_error,
                "integrated_relaxation_dissipation": dissipation,
                "passed": bool(
                    energy_passed and force_passed and j_error <= 1.0e-12
                ),
            }
        )
        internal_z = updated_z

    ascending = records[1]
    descending = records[3]
    memory_energy_difference = abs(
        float(descending["reference_ecm_viscoelastic_energy"])
        - float(ascending["reference_ecm_viscoelastic_energy"])
    )
    memory_z_difference = float(
        np.linalg.norm(z_history[3] - z_history[1])
    )
    memory_detected = bool(
        memory_energy_difference > 1.0e-12 and memory_z_difference > 1.0e-12
    )
    report = {
        "schema_version": "efe_node1_fenicsx_short_sls_cycle_v01",
        "status": (
            "passed"
            if all(record["passed"] for record in records) and memory_detected
            else "failed"
        ),
        "evidence_class": "prescribed_geometry_sls_regression_not_formal_n1_2_evidence",
        "phase_sequence": [record["activation"] for record in records],
        "period": arguments.period,
        "time_step": time_step,
        "records": records,
        "memory_check": {
            "same_geometry": "accepted F150 a=0.10 state",
            "ascending_viscoelastic_energy": ascending[
                "reference_ecm_viscoelastic_energy"
            ],
            "descending_viscoelastic_energy": descending[
                "reference_ecm_viscoelastic_energy"
            ],
            "energy_difference": memory_energy_difference,
            "z_state_l2_difference": memory_z_difference,
            "memory_detected": memory_detected,
        },
        "backend_diagnostics": backend.diagnostics(),
        "boundary": (
            "The geometry sequence is prescribed from accepted static F150 "
            "states. This verifies SLS memory transfer through the backend seam, "
            "not a fully coupled limit cycle."
        ),
    }
    np.savez_compressed(
        output_path / "trajectory.npz",
        activations=np.asarray(report["phase_sequence"], dtype=np.float64),
        internal_z=np.asarray(z_history, dtype=np.float64),
        final_internal_z=internal_z,
    )
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("short prescribed-geometry SLS regression failed")


if __name__ == "__main__":
    main()
