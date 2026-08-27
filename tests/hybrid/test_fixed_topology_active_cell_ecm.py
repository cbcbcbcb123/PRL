from __future__ import annotations

import numpy as np
import pytest

from hybrid.fixed_topology_active_cell_ecm import (
    build_fixed_topology_model,
    evaluate_variables,
    gap_constraints,
    initial_variables,
    pack_variables,
    prescribed_ecm_affine_shear_response,
    prescribed_ecm_translation_response,
    sample_saved_state,
    unpack_variables,
)


@pytest.fixture(scope="module")
def topology_models():
    settings = {
        "patch_divisions": (3, 1, 2),
        "tangential_stiffness": 1.0,
    }
    return {
        topology: build_fixed_topology_model(topology, **settings)
        for topology in ("basal", "apical", "symmetric")
    }


def test_contact_weight_and_signed_polarity_are_matched(topology_models) -> None:
    basal = topology_models["basal"]
    apical = topology_models["apical"]
    symmetric = topology_models["symmetric"]
    assert basal.tether_weight_sum == pytest.approx(
        apical.tether_weight_sum,
        abs=1.0e-14,
    )
    assert basal.tether_weight_sum == pytest.approx(
        symmetric.tether_weight_sum,
        abs=1.0e-14,
    )
    assert basal.contact_polarity_y == pytest.approx(
        -apical.contact_polarity_y,
        abs=1.0e-14,
    )
    assert abs(basal.contact_polarity_y) > 0.9
    assert symmetric.contact_polarity_y == pytest.approx(0.0, abs=1.0e-14)


@pytest.mark.parametrize("topology", ("basal", "apical", "symmetric"))
def test_reference_state_has_zero_gradient_and_valid_geometry(
    topology_models,
    topology: str,
) -> None:
    model = topology_models[topology]
    evaluation = evaluate_variables(
        model,
        initial_variables(model),
        activation=0.0,
    )
    assert np.linalg.norm(evaluation.variable_gradient) <= 1.0e-10
    assert evaluation.volume_ratio == pytest.approx(1.0, abs=1.0e-14)
    np.testing.assert_allclose(
        evaluation.interface.ecm_jacobians,
        1.0,
        atol=1.0e-14,
        rtol=0.0,
    )
    assert evaluation.interface.minimum_gap > 0.0
    assert evaluation.interface.pair_force_residual <= 1.0e-12
    assert evaluation.interface.pair_moment_residual <= 1.0e-12


def test_joint_dcm_fem_gradient_matches_directional_derivative(
    topology_models,
) -> None:
    model = topology_models["basal"]
    rng = np.random.default_rng(20260811)
    variables = initial_variables(model)
    perturbation = rng.standard_normal(variables.shape)
    perturbation /= np.linalg.norm(perturbation)
    variables = variables + 1.0e-5 * perturbation
    direction = rng.standard_normal(variables.shape)
    direction /= np.linalg.norm(direction)
    step = 1.0e-7
    plus = evaluate_variables(
        model,
        variables + step * direction,
        activation=0.03,
    ).total_energy
    minus = evaluate_variables(
        model,
        variables - step * direction,
        activation=0.03,
    ).total_energy
    finite = (plus - minus) / (2.0 * step)
    evaluation = evaluate_variables(model, variables, activation=0.03)
    analytic = float(np.dot(evaluation.variable_gradient, direction))
    residual = abs(finite - analytic) / max(1.0, abs(finite), abs(analytic))
    assert residual <= 1.0e-5


def test_tether_gap_jacobian_matches_directional_derivative(
    topology_models,
) -> None:
    model = topology_models["basal"]
    rng = np.random.default_rng(20260812)
    variables = initial_variables(model)
    variables += 1.0e-5 * rng.standard_normal(variables.shape)
    direction = rng.standard_normal(variables.shape)
    direction /= np.linalg.norm(direction)
    step = 1.0e-7
    plus = gap_constraints(model, variables + step * direction)[0]
    minus = gap_constraints(model, variables - step * direction)[0]
    finite = (plus - minus) / (2.0 * step)
    _, jacobian = gap_constraints(model, variables)
    analytic = jacobian @ direction
    np.testing.assert_allclose(analytic, finite, atol=1.0e-7, rtol=1.0e-5)


def test_fixed_far_ecm_nodes_are_not_optimization_variables(
    topology_models,
) -> None:
    model = topology_models["symmetric"]
    variables = initial_variables(model)
    variables[-1] = 1.0e-4
    _, ecm_vertices = unpack_variables(model, variables)
    reference = model.vertical_slice.ecm_reference.vertices
    np.testing.assert_allclose(
        ecm_vertices[model.ecm_fixed_vertex_ids],
        reference[model.ecm_fixed_vertex_ids],
        atol=0.0,
        rtol=0.0,
    )


def test_saved_state_round_trip_and_constrained_audit(topology_models) -> None:
    model = topology_models["basal"]
    variables = initial_variables(model)
    cell_vertices, ecm_vertices = unpack_variables(model, variables)
    recovered = pack_variables(model, cell_vertices, ecm_vertices)
    np.testing.assert_allclose(recovered, variables, atol=1.0e-14, rtol=0.0)
    sample = sample_saved_state(
        model,
        cell_vertices,
        ecm_vertices,
        activation=0.0,
        optimizer_success=True,
        optimizer_message="reference_state",
        optimizer_iterations=0,
        optimizer_evaluations=1,
    )
    assert sample.kkt_residual <= 1.0e-10
    assert sample.active_gap_constraint_count == 0
    assert sample.maximum_gap_complementarity == 0.0


@pytest.mark.parametrize("displacement", (1.0e-4, 1.0e-3, 5.0e-3))
def test_symmetric_ecm_half_modulus_matches_single_patch(
    displacement: float,
) -> None:
    settings = {
        "patch_divisions": (5, 1, 4),
        "tangential_stiffness": 1.0,
        "mu_ve": 0.0,
    }
    basal = build_fixed_topology_model(
        "basal",
        mu_eq=1.0,
        kappa_eq=20.0,
        **settings,
    )
    symmetric_raw = build_fixed_topology_model(
        "symmetric",
        mu_eq=1.0,
        kappa_eq=20.0,
        **settings,
    )
    symmetric_calibrated = build_fixed_topology_model(
        "symmetric",
        mu_eq=0.5,
        kappa_eq=10.0,
        **settings,
    )
    single = prescribed_ecm_translation_response(basal, displacement)
    raw = prescribed_ecm_translation_response(symmetric_raw, displacement)
    calibrated = prescribed_ecm_translation_response(
        symmetric_calibrated,
        displacement,
    )
    assert raw.energy == pytest.approx(2.0 * single.energy, rel=1.0e-12)
    assert raw.reaction == pytest.approx(2.0 * single.reaction, rel=1.0e-12)
    assert calibrated.energy == pytest.approx(single.energy, rel=1.0e-12)
    assert calibrated.reaction == pytest.approx(single.reaction, rel=1.0e-12)


def test_affine_ecm_shear_is_independent_of_thickness_subdivision() -> None:
    settings = {
        "tangential_stiffness": 1.0,
        "mu_eq": 1.0,
        "kappa_eq": 20.0,
        "mu_ve": 0.0,
    }
    one_layer = build_fixed_topology_model(
        "basal",
        patch_divisions=(5, 1, 4),
        **settings,
    )
    two_layers = build_fixed_topology_model(
        "basal",
        patch_divisions=(5, 2, 4),
        **settings,
    )
    first = prescribed_ecm_affine_shear_response(one_layer, 1.0e-3)
    second = prescribed_ecm_affine_shear_response(two_layers, 1.0e-3)
    assert one_layer.vertical_slice.ecm_reference.volume0.sum() == pytest.approx(
        two_layers.vertical_slice.ecm_reference.volume0.sum(),
        abs=1.0e-14,
    )
    assert second.energy == pytest.approx(first.energy, rel=1.0e-10)
    assert second.reaction == pytest.approx(first.reaction, rel=1.0e-10)


def test_ecm_footprint_scale_changes_only_outer_patch_extent() -> None:
    settings = {
        "patch_divisions": (5, 4, 4),
        "tangential_stiffness": 1.0,
        "mu_eq": 1.0,
        "kappa_eq": 20.0,
        "mu_ve": 0.0,
    }
    baseline = build_fixed_topology_model(
        "basal",
        ecm_footprint_scale=1.0,
        **settings,
    )
    expanded = build_fixed_topology_model(
        "basal",
        ecm_footprint_scale=1.5,
        **settings,
    )
    baseline_vertices = baseline.vertical_slice.ecm_reference.vertices
    expanded_vertices = expanded.vertical_slice.ecm_reference.vertices
    baseline_span = np.ptp(baseline_vertices[:, [0, 2]], axis=0)
    expanded_span = np.ptp(expanded_vertices[:, [0, 2]], axis=0)
    np.testing.assert_allclose(
        expanded_span,
        1.5 * baseline_span,
        atol=1.0e-14,
        rtol=0.0,
    )
    assert expanded.tether_weight_sum == pytest.approx(
        baseline.tether_weight_sum,
        abs=1.0e-14,
    )
    assert len(expanded.vertical_slice.tethers) == len(
        baseline.vertical_slice.tethers
    )
    expanded_volume = expanded.vertical_slice.ecm_reference.volume0.sum()
    baseline_volume = baseline.vertical_slice.ecm_reference.volume0.sum()
    assert expanded_volume == pytest.approx(2.25 * baseline_volume, rel=1.0e-12)


def test_ecm_geometry_scaling_matches_affine_shear_law() -> None:
    settings = {
        "patch_divisions": (5, 4, 4),
        "tangential_stiffness": 1.0,
        "mu_eq": 1.0,
        "kappa_eq": 20.0,
        "mu_ve": 0.0,
    }
    baseline = build_fixed_topology_model("basal", **settings)
    expanded = build_fixed_topology_model(
        "basal",
        ecm_footprint_scale=1.5,
        **settings,
    )
    thicker = build_fixed_topology_model(
        "basal",
        ecm_thickness=0.45,
        **settings,
    )
    baseline_response = prescribed_ecm_affine_shear_response(
        baseline,
        1.0e-3,
    )
    expanded_response = prescribed_ecm_affine_shear_response(
        expanded,
        1.0e-3,
    )
    thicker_response = prescribed_ecm_affine_shear_response(
        thicker,
        1.0e-3,
    )
    assert expanded_response.energy == pytest.approx(
        2.25 * baseline_response.energy,
        rel=1.0e-10,
    )
    assert expanded_response.reaction == pytest.approx(
        2.25 * baseline_response.reaction,
        rel=1.0e-10,
    )
    assert thicker_response.energy == pytest.approx(
        baseline_response.energy / 1.5,
        rel=1.0e-10,
    )
    assert thicker_response.reaction == pytest.approx(
        baseline_response.reaction / 1.5,
        rel=1.0e-10,
    )
