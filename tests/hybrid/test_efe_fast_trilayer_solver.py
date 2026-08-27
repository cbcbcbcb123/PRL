from __future__ import annotations

import numpy as np
import pytest

from hybrid.efe_fast_trilayer import build_fast_trilayer_model
from hybrid.efe_fast_trilayer_solver import (
    augmented_contact_energy_gradient,
    build_exact_volume_coordinates,
    reduce_gradient_to_exact_volume_manifold,
    solve_fast_trilayer_equilibrium,
    trilayer_gap_constraints,
    unpack_exact_volume_variables,
)


@pytest.fixture(scope="module")
def model():
    return build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")


def test_exact_volume_coordinates_preserve_both_closed_layers(model) -> None:
    coordinates = build_exact_volume_coordinates(model)
    rng = np.random.default_rng(20260817)
    variables = 1.0e-4 * rng.normal(size=len(coordinates.free_indices))
    myocyte, _, endocardium = unpack_exact_volume_variables(
        model,
        coordinates,
        variables,
    )
    from route_h.dcm_cell import surface_volume_and_gradient

    myocyte_volume, _ = surface_volume_and_gradient(myocyte, model.myocyte.faces)
    endocardial_volume, _ = surface_volume_and_gradient(
        endocardium,
        model.endocardium.faces,
    )
    assert myocyte_volume / model.myocyte.cell.volume0 == pytest.approx(
        1.0, abs=1.0e-13
    )
    assert endocardial_volume / model.endocardium.cell.volume0 == pytest.approx(
        1.0, abs=1.0e-13
    )


def test_exact_volume_reduced_gradient_matches_finite_difference(model) -> None:
    coordinates = build_exact_volume_coordinates(model)
    rng = np.random.default_rng(17)
    variables = 1.0e-4 * rng.normal(size=len(coordinates.free_indices))
    direction = rng.normal(size=len(variables))
    direction /= np.linalg.norm(direction)

    def stored_energy(current: np.ndarray) -> float:
        from hybrid.efe_fast_trilayer import evaluate_fast_trilayer_state

        state = unpack_exact_volume_variables(model, coordinates, current)
        return evaluate_fast_trilayer_state(
            model,
            *state,
            activation=0.02,
            reject_penetration=False,
        ).total_stored_energy

    from hybrid.efe_fast_trilayer import evaluate_fast_trilayer_state

    myocyte, ecm, endocardium = unpack_exact_volume_variables(
        model,
        coordinates,
        variables,
    )
    evaluation = evaluate_fast_trilayer_state(
        model,
        myocyte,
        ecm,
        endocardium,
        activation=0.02,
        reject_penetration=False,
    )
    full_gradient = np.concatenate(
        (
            evaluation.myocyte_energy_gradient.reshape(-1),
            evaluation.ecm_energy_gradient.reshape(-1),
            evaluation.endocardial_energy_gradient.reshape(-1),
        )
    )
    reduced_gradient = reduce_gradient_to_exact_volume_manifold(
        model,
        coordinates,
        full_gradient,
        myocyte,
        endocardium,
    )
    epsilon = 1.0e-7
    finite_difference = (
        stored_energy(variables + epsilon * direction)
        - stored_energy(variables - epsilon * direction)
    ) / (2.0 * epsilon)
    analytic = float(np.dot(reduced_gradient, direction))
    assert analytic == pytest.approx(finite_difference, rel=1.0e-5, abs=1.0e-8)


def test_double_interface_gap_jacobian_matches_finite_difference(model) -> None:
    coordinates = build_exact_volume_coordinates(model)
    rng = np.random.default_rng(20260818)
    variables = 1.0e-5 * rng.normal(size=len(coordinates.free_indices))
    direction = rng.normal(size=len(variables))
    direction /= np.linalg.norm(direction)
    gaps, jacobian = trilayer_gap_constraints(model, coordinates, variables)
    epsilon = 1.0e-7
    plus = trilayer_gap_constraints(
        model,
        coordinates,
        variables + epsilon * direction,
    )[0]
    minus = trilayer_gap_constraints(
        model,
        coordinates,
        variables - epsilon * direction,
    )[0]
    finite_difference = (plus - minus) / (2.0 * epsilon)
    analytic = jacobian @ direction
    assert len(gaps) == (
        len(model.myocyte_interface.tethers)
        + len(model.endocardial_interface.tethers)
    )
    np.testing.assert_allclose(
        analytic,
        finite_difference,
        rtol=2.0e-5,
        atol=2.0e-8,
    )


def test_augmented_contact_opposes_manufactured_endocardial_intrusion(model) -> None:
    coordinates = build_exact_volume_coordinates(model)
    variables = np.zeros(len(coordinates.free_indices), dtype=np.float64)
    endocardial_start = (
        coordinates.myocyte_coordinate_count + coordinates.ecm_coordinate_count
    )
    full_direction = np.zeros_like(coordinates.reference_flat)
    full_direction[endocardial_start + 1 :: 3] = -1.0
    direction = full_direction[coordinates.free_indices]
    intruded = variables + 0.08 * direction
    gaps, jacobian = trilayer_gap_constraints(model, coordinates, intruded)
    multipliers = np.zeros_like(gaps)
    energy, gradient, updated = augmented_contact_energy_gradient(
        gaps,
        jacobian,
        multipliers,
        penalty=10.0,
    )
    assert float(np.min(gaps)) < 0.0
    assert energy > 0.0
    assert float(np.max(updated)) > 0.0
    assert float(np.dot(gradient, direction)) > 0.0

    epsilon = 1.0e-7

    def contact_energy(current: np.ndarray) -> float:
        current_gaps, current_jacobian = trilayer_gap_constraints(
            model,
            coordinates,
            current,
        )
        return augmented_contact_energy_gradient(
            current_gaps,
            current_jacobian,
            multipliers,
            penalty=10.0,
        )[0]

    finite_difference = (
        contact_energy(intruded + epsilon * direction)
        - contact_energy(intruded - epsilon * direction)
    ) / (2.0 * epsilon)
    assert float(np.dot(gradient, direction)) == pytest.approx(
        finite_difference,
        rel=2.0e-5,
        abs=2.0e-8,
    )


def test_zero_load_equilibrium_passes_n1_1_hard_gates(model) -> None:
    result = solve_fast_trilayer_equilibrium(
        model,
        maximum_iterations=5,
        maximum_newton_iterations=0,
    )
    assert result.optimizer_success
    assert result.mechanical_converged
    assert result.volume_constraint_residual <= 1.0e-12
    assert result.normalized_kkt_residual <= 1.0e-10
    assert result.evaluation.minimum_ecm_jacobian >= 0.5
    assert result.evaluation.minimum_gap >= -1.0e-12
    assert result.evaluation.minimum_myocyte_face_area_ratio >= 0.05
    assert result.evaluation.minimum_endocardial_face_area_ratio >= 0.05
