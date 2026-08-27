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
    _full_external_force,
    _full_stored_gradient,
    build_exact_volume_coordinates,
    contact_kkt_audit,
    reduce_gradient_to_exact_volume_manifold,
    trilayer_gap_constraints,
    unpack_exact_volume_variables,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-iterations", type=int, default=8)
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
    contact_multipliers = np.asarray(
        source["contact_multipliers"],
        dtype=np.float64,
    ).copy()
    source_state = unpack_exact_volume_variables(model, coordinates, variables)
    source_external_force = _full_external_force(
        model,
        coordinates,
        source_state[2],
        pressure=pressure,
        wss_command=wss_command,
    )

    history: list[dict[str, float | int | bool]] = []
    for iteration in range(1, arguments.maximum_iterations + 1):
        gaps, jacobian = trilayer_gap_constraints(
            model,
            coordinates,
            variables,
        )
        active_ids = np.flatnonzero(
            (contact_multipliers > 1.0e-10) | (gaps < 0.0)
        )
        if len(active_ids) == 0:
            break
        active_gaps = gaps[active_ids]
        maximum_active_gap = float(np.max(np.abs(active_gaps)))
        if maximum_active_gap <= 1.0e-14:
            break
        active_jacobian = jacobian[active_ids]
        gram = active_jacobian @ active_jacobian.T
        correction = -active_jacobian.T @ np.linalg.lstsq(
            gram,
            active_gaps,
            rcond=1.0e-12,
        )[0]
        step_length = 1.0
        accepted = False
        for _ in range(20):
            candidate = variables + step_length * correction
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
            candidate_active_gap = float(
                np.max(np.abs(candidate_gaps[active_ids]))
            )
            if (
                candidate_evaluation.minimum_ecm_jacobian >= 0.5
                and candidate_active_gap < maximum_active_gap
            ):
                variables = candidate
                accepted = True
                break
            step_length *= 0.5
        history.append(
            {
                "iteration": iteration,
                "active_contact_count": len(active_ids),
                "maximum_active_gap_before": maximum_active_gap,
                "step_length": step_length,
                "accepted": accepted,
            }
        )
        if not accepted:
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
        (contact_multipliers > 1.0e-10) | (np.abs(gaps) <= 1.0e-10)
    )
    full_gradient = _full_stored_gradient(evaluation) - external_force
    reduced_gradient = reduce_gradient_to_exact_volume_manifold(
        model,
        coordinates,
        full_gradient,
        state[0],
        state[2],
    )
    contact_multipliers = np.zeros_like(gaps)
    if len(active_ids):
        fitted_multipliers, _ = nnls(
            jacobian[active_ids].T,
            reduced_gradient,
        )
        contact_multipliers[active_ids] = fitted_multipliers
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
    volume_residual = max(
        abs(evaluation.myocyte_volume_ratio - 1.0),
        abs(evaluation.endocardial_volume_ratio - 1.0),
    )
    follower_projection_residual = float(
        np.linalg.norm(external_force - source_external_force)
        / max(
            1.0,
            float(np.linalg.norm(external_force)),
            float(np.linalg.norm(source_external_force)),
        )
    )
    source_follower_residual = float(
        source_summary.get("follower_residual", 0.0)
    )
    follower_history = source_summary.get("follower_history", [])
    if follower_history:
        source_follower_residual = max(
            source_follower_residual,
            float(follower_history[-1]["follower_residual"]),
        )
    audited_follower_residual = max(
        source_follower_residual,
        follower_projection_residual,
    )
    passed = bool(
        normalized_kkt <= 1.0e-5
        and audited_follower_residual <= 1.0e-7
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
            "passed_strict_active_contact_projection"
            if passed
            else "failed_strict_active_contact_projection"
        ),
        "source_state": str(arguments.input.resolve()),
        "activation": activation,
        "pressure": pressure,
        "wss_command": wss_command.tolist(),
        "projection_history": history,
        "active_contact_count": int(
            np.count_nonzero(contact_multipliers > 1.0e-10)
        ),
        "minimum_gap": float(np.min(audited_gaps)),
        "maximum_contact_multiplier": float(
            np.max(contact_multipliers)
        ),
        "contact_complementarity": complementarity,
        "normalized_kkt_residual": normalized_kkt,
        "follower_projection_residual": follower_projection_residual,
        "source_follower_residual": source_follower_residual,
        "audited_follower_residual": audited_follower_residual,
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
        output / "pressure_001_strict_contact_state.npz",
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
