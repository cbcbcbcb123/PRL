from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import (
    _diagonal_preconditioner,
    _full_external_force,
    _full_stored_gradient,
    build_exact_volume_coordinates,
    contact_kkt_audit,
    reduce_gradient_to_exact_volume_manifold,
    trilayer_gap_constraints,
    unpack_exact_volume_variables,
)


def flattened_state(state: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    return np.concatenate(tuple(block.reshape(-1) for block in state))


def project_active_gaps(
    model,
    coordinates,
    variables: np.ndarray,
    active_ids: np.ndarray,
) -> np.ndarray:
    projected = variables.copy()
    for _ in range(5):
        gaps, jacobian = trilayer_gap_constraints(
            model,
            coordinates,
            projected,
        )
        active_gaps = gaps[active_ids]
        if float(np.max(np.abs(active_gaps))) <= 1.0e-14:
            break
        active_jacobian = jacobian[active_ids]
        projected -= active_jacobian.T @ np.linalg.lstsq(
            active_jacobian @ active_jacobian.T,
            active_gaps,
            rcond=1.0e-12,
        )[0]
    return projected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-iterations", type=int, default=40)
    arguments = parser.parse_args()

    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = np.load(arguments.input.resolve())
    source_summary = json.loads(
        arguments.summary.resolve().read_text(encoding="utf-8")
    )
    activation = float(source_summary["activation"])
    pressure = float(source_summary["pressure"])
    wss_command = np.asarray(source_summary["wss_command"], dtype=np.float64)

    model = build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")
    coordinates = build_exact_volume_coordinates(model)
    variables = np.asarray(source["variables"], dtype=np.float64).copy()
    source_multipliers = np.asarray(
        source["contact_multipliers"],
        dtype=np.float64,
    )
    variable_scales, block_scales = _diagonal_preconditioner(
        model,
        coordinates,
    )
    inverse_tangent_diagonal = variable_scales * variable_scales
    source_state = unpack_exact_volume_variables(model, coordinates, variables)
    previous_external_force = _full_external_force(
        model,
        coordinates,
        source_state[2],
        pressure=pressure,
        wss_command=wss_command,
    )
    follower_residual = float(source_summary.get("follower_residual", 0.0))
    history: list[dict[str, float | int | bool]] = []
    solver_success = True

    for iteration in range(1, arguments.maximum_iterations + 1):
        state = unpack_exact_volume_variables(model, coordinates, variables)
        evaluation = evaluate_fast_trilayer_state(
            model,
            *state,
            activation=activation,
            pressure=pressure,
            wss_command=wss_command,
            reject_penetration=False,
        )
        external_force = _full_external_force(
            model,
            coordinates,
            state[2],
            pressure=pressure,
            wss_command=wss_command,
        )
        follower_residual = float(
            np.linalg.norm(external_force - previous_external_force)
            / max(
                1.0,
                float(np.linalg.norm(external_force)),
                float(np.linalg.norm(previous_external_force)),
            )
        )
        gaps, jacobian = trilayer_gap_constraints(
            model,
            coordinates,
            variables,
        )
        active_ids = np.flatnonzero(
            (source_multipliers > 1.0e-10) | (np.abs(gaps) <= 1.0e-10)
        )
        active_jacobian = jacobian[active_ids]
        full_gradient = _full_stored_gradient(evaluation) - external_force
        reduced_gradient = reduce_gradient_to_exact_volume_manifold(
            model,
            coordinates,
            full_gradient,
            state[0],
            state[2],
        )
        fitted_active_multipliers, _ = nnls(
            active_jacobian.T,
            reduced_gradient,
        )
        contact_multipliers = np.zeros_like(gaps)
        contact_multipliers[active_ids] = fitted_active_multipliers
        (
            _,
            normalized_kkt,
            _,
            complementarity,
        ) = contact_kkt_audit(
            model,
            coordinates,
            evaluation,
            state[0],
            state[1],
            state[2],
            external_force,
            contact_multipliers,
        )
        if (
            normalized_kkt <= 1.0e-5
            and follower_residual <= 1.0e-7
            and float(np.min(gaps)) >= -1.0e-12
            and complementarity <= 1.0e-8
        ):
            break

        weighted_gradient = inverse_tangent_diagonal * reduced_gradient
        weighted_constraint_transpose = (
            inverse_tangent_diagonal[:, None] * active_jacobian.T
        )
        schur = active_jacobian @ weighted_constraint_transpose
        direction = (
            -weighted_gradient
            + weighted_constraint_transpose
            @ np.linalg.solve(
                schur,
                active_jacobian @ weighted_gradient,
            )
        )
        slope = float(np.dot(reduced_gradient, direction))
        if not np.isfinite(slope) or slope >= 0.0:
            tangent_residual = (
                reduced_gradient
                - active_jacobian.T
                @ np.linalg.lstsq(
                    active_jacobian @ active_jacobian.T,
                    active_jacobian @ reduced_gradient,
                    rcond=1.0e-12,
                )[0]
            )
            direction = -tangent_residual
            slope = -float(np.dot(tangent_residual, tangent_residual))

        potential = evaluation.total_stored_energy - float(
            np.dot(
                external_force,
                flattened_state(state) - coordinates.reference_flat,
            )
        )
        accepted = False
        step_length = 1.0
        candidate_kkt = normalized_kkt
        for _ in range(20):
            candidate = project_active_gaps(
                model,
                coordinates,
                variables + step_length * direction,
                active_ids,
            )
            try:
                candidate_state = unpack_exact_volume_variables(
                    model,
                    coordinates,
                    candidate,
                )
                candidate_evaluation = evaluate_fast_trilayer_state(
                    model,
                    *candidate_state,
                    activation=activation,
                    reject_penetration=False,
                )
            except ValueError:
                step_length *= 0.5
                continue
            candidate_gaps, _ = trilayer_gap_constraints(
                model,
                coordinates,
                candidate,
            )
            candidate_potential = (
                candidate_evaluation.total_stored_energy
                - float(
                    np.dot(
                        external_force,
                        flattened_state(candidate_state)
                        - coordinates.reference_flat,
                    )
                )
            )
            if (
                candidate_evaluation.minimum_ecm_jacobian >= 0.5
                and float(np.min(candidate_gaps)) >= -1.0e-12
                and candidate_potential
                <= potential + 1.0e-4 * step_length * slope
            ):
                variables = candidate
                accepted = True
                break
            step_length *= 0.5
        history.append(
            {
                "iteration": iteration,
                "active_contact_count": len(active_ids),
                "normalized_kkt_before": normalized_kkt,
                "follower_residual_before": follower_residual,
                "slope": slope,
                "step_length": step_length,
                "accepted": accepted,
                "candidate_kkt": candidate_kkt,
            }
        )
        previous_external_force = external_force
        if not accepted:
            solver_success = False
            break

    state = unpack_exact_volume_variables(model, coordinates, variables)
    evaluation = evaluate_fast_trilayer_state(
        model,
        *state,
        activation=activation,
        pressure=pressure,
        wss_command=wss_command,
        reject_penetration=False,
    )
    external_force = _full_external_force(
        model,
        coordinates,
        state[2],
        pressure=pressure,
        wss_command=wss_command,
    )
    gaps, jacobian = trilayer_gap_constraints(
        model,
        coordinates,
        variables,
    )
    active_ids = np.flatnonzero(
        (source_multipliers > 1.0e-10) | (np.abs(gaps) <= 1.0e-10)
    )
    reduced_gradient = reduce_gradient_to_exact_volume_manifold(
        model,
        coordinates,
        _full_stored_gradient(evaluation) - external_force,
        state[0],
        state[2],
    )
    fitted_active_multipliers, _ = nnls(
        jacobian[active_ids].T,
        reduced_gradient,
    )
    contact_multipliers = np.zeros_like(gaps)
    contact_multipliers[active_ids] = fitted_active_multipliers
    (
        volume_multipliers,
        normalized_kkt,
        audited_gaps,
        complementarity,
    ) = contact_kkt_audit(
        model,
        coordinates,
        evaluation,
        state[0],
        state[1],
        state[2],
        external_force,
        contact_multipliers,
    )
    follower_residual = float(
        np.linalg.norm(external_force - previous_external_force)
        / max(
            1.0,
            float(np.linalg.norm(external_force)),
            float(np.linalg.norm(previous_external_force)),
        )
    )
    volume_residual = max(
        abs(evaluation.myocyte_volume_ratio - 1.0),
        abs(evaluation.endocardial_volume_ratio - 1.0),
    )
    passed = bool(
        solver_success
        and normalized_kkt <= 1.0e-5
        and follower_residual <= 1.0e-7
        and volume_residual <= 1.0e-8
        and float(np.min(audited_gaps)) >= -1.0e-12
        and complementarity <= 1.0e-8
        and float(np.min(contact_multipliers)) >= -1.0e-12
        and evaluation.minimum_ecm_jacobian >= 0.5
        and evaluation.minimum_myocyte_face_area_ratio >= 0.05
        and evaluation.minimum_endocardial_face_area_ratio >= 0.05
    )
    report = {
        "status": (
            "passed_active_set_equilibrium_refinement"
            if passed
            else "failed_active_set_equilibrium_refinement"
        ),
        "source_state": str(arguments.input.resolve()),
        "activation": activation,
        "pressure": pressure,
        "wss_command": wss_command.tolist(),
        "block_scales": block_scales.tolist(),
        "iteration_history": history,
        "solver_success": solver_success,
        "active_contact_count": int(
            np.count_nonzero(contact_multipliers > 1.0e-10)
        ),
        "minimum_gap": float(np.min(audited_gaps)),
        "maximum_contact_multiplier": float(
            np.max(contact_multipliers)
        ),
        "contact_complementarity": complementarity,
        "normalized_kkt_residual": normalized_kkt,
        "follower_residual": follower_residual,
        "volume_constraint_residual": volume_residual,
        "minimum_ecm_jacobian": evaluation.minimum_ecm_jacobian,
        "minimum_myocyte_face_area_ratio": (
            evaluation.minimum_myocyte_face_area_ratio
        ),
        "minimum_endocardial_face_area_ratio": (
            evaluation.minimum_endocardial_face_area_ratio
        ),
        "passed": passed,
    }
    (output / "summary.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    np.savez_compressed(
        output / "active_set_equilibrium_state.npz",
        activation=np.asarray(activation),
        pressure=np.asarray(pressure),
        variables=variables,
        myocyte_vertices=state[0],
        ecm_vertices=state[1],
        endocardial_vertices=state[2],
        volume_multipliers=volume_multipliers,
        contact_multipliers=contact_multipliers,
        contact_gaps=audited_gaps,
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
