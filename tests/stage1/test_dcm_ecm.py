from __future__ import annotations

import numpy as np

from route_h.dcm_cell import (
    area_energy_gradient,
    bending_energy_gradient,
    build_cell_reference,
    passive_energy_force,
    volume_energy_gradient,
)
from route_h.ecm_finite_strain import (
    build_ecm_reference,
    deformation_gradient,
    ecm_energy_force,
    internal_variable_rate,
    relax_internal_variable_exact,
    relaxation_dissipation,
)
from route_h.solver import evaluate_passive_reference


def _directional_error(energy, gradient, state, direction, step=1e-7):
    plus = energy(state + step * direction)
    minus = energy(state - step * direction)
    finite = (plus - minus) / (2.0 * step)
    analytic = float(np.sum(gradient * direction))
    return abs(finite - analytic) / max(1.0, abs(finite), abs(analytic))


def test_reference_passive_force_and_energy_are_zero():
    result = evaluate_passive_reference()
    assert result.total_energy < 1e-25
    assert result.maximum_cell_force < 1e-12
    assert result.maximum_ecm_force < 1e-12
    assert result.minimum_ecm_jacobian == 1.0
    assert not result.active_enabled
    assert not result.trajectory_run


def test_cell_area_bending_volume_analytic_directional_derivatives(bundle):
    arrays, _ = bundle
    vertices0 = arrays["cell_vertices"][6]
    reference = build_cell_reference(
        vertices0,
        arrays["cell_faces"][6],
        arrays["cell_primary_identity"][6],
        arrays["cell_directional_identity"][6],
    )
    rng = np.random.default_rng(20260728)
    state = vertices0 + 2e-3 * rng.standard_normal(vertices0.shape)
    direction = rng.standard_normal(vertices0.shape)
    direction /= np.linalg.norm(direction)
    components = (
        (area_energy_gradient, 1.0),
        (bending_energy_gradient, 0.01),
        (volume_energy_gradient, 100.0),
    )
    for function, stiffness in components:
        value, gradient = function(state, reference, stiffness)
        assert np.isfinite(value)
        error = _directional_error(
            lambda trial: function(trial, reference, stiffness)[0],
            gradient,
            state,
            direction,
        )
        assert error < 1e-5


def test_cell_rigid_motion_objectivity(bundle):
    arrays, _ = bundle
    vertices0 = arrays["cell_vertices"][6]
    reference = build_cell_reference(
        vertices0,
        arrays["cell_faces"][6],
        arrays["cell_primary_identity"][6],
        arrays["cell_directional_identity"][6],
    )
    rng = np.random.default_rng(40)
    state = vertices0 + 1e-3 * rng.standard_normal(vertices0.shape)
    angle = 0.43
    rotation = np.array([
        [np.cos(angle), -np.sin(angle), 0.0],
        [np.sin(angle), np.cos(angle), 0.0],
        [0.0, 0.0, 1.0],
    ])
    translation = np.array([0.7, -0.3, 0.9])
    energy, force = passive_energy_force(state, reference)
    rotated_reference = build_cell_reference(
        vertices0 @ rotation.T + translation,
        reference.faces,
        reference.primary,
        reference.directional,
    )
    rotated_energy, rotated_force = passive_energy_force(
        state @ rotation.T + translation, rotated_reference
    )
    assert abs(energy["cell_total"] - rotated_energy["cell_total"]) < 1e-12
    assert np.linalg.norm(rotated_force - force @ rotation.T) < 1e-9


def test_ecm_force_matches_directional_derivative_on_one_tetra(bundle):
    arrays, _ = bundle
    tet = arrays["ecm_tetrahedra"][0]
    reference_vertices = arrays["ecm_vertices"][tet]
    reference = build_ecm_reference(reference_vertices, np.array([[0, 1, 2, 3]]))
    deformation = np.array([[1.05, 0.03, 0.0], [0.01, 0.97, 0.02], [0.0, 0.01, 1.04]])
    state = reference_vertices[0] + (reference_vertices - reference_vertices[0]) @ deformation.T
    z_value = np.array([[[0.02, 0.01, 0.0], [0.01, -0.01, 0.0], [0.0, 0.0, -0.01]]])
    energies, force, jacobians = ecm_energy_force(state, reference, z_value)
    rng = np.random.default_rng(8)
    direction = rng.standard_normal(state.shape)
    direction -= direction.mean(axis=0)
    direction /= np.linalg.norm(direction)
    gradient = -force
    error = _directional_error(
        lambda trial: ecm_energy_force(trial, reference, z_value)[0]["ecm_total"],
        gradient,
        state,
        direction,
        step=2e-7,
    )
    assert error < 1e-5
    assert energies["ecm_total"] > 0.0
    assert jacobians[0] > 0.0


def test_ecm_relaxation_preserves_symmetric_traceless_and_dissipates(bundle):
    arrays, _ = bundle
    tet = arrays["ecm_tetrahedra"][0]
    reference = build_ecm_reference(arrays["ecm_vertices"][tet], np.array([[0, 1, 2, 3]]))
    state = arrays["ecm_vertices"][tet].copy()
    state[1] += np.array([0.01, 0.02, 0.0])
    deformation = deformation_gradient(state, reference.dm_inverse[0])
    z0 = np.zeros((3, 3))
    rate = internal_variable_rate(deformation, z0)
    z1 = relax_internal_variable_exact(deformation, z0, 0.1)
    assert np.allclose(z1, z1.T, atol=1e-15)
    assert abs(np.trace(z1)) < 1e-15
    assert relaxation_dissipation(rate) >= 0.0


def test_ecm_rejects_nonpositive_jacobian(bundle):
    arrays, _ = bundle
    tet = arrays["ecm_tetrahedra"][0]
    reference = build_ecm_reference(arrays["ecm_vertices"][tet], np.array([[0, 1, 2, 3]]))
    inverted = arrays["ecm_vertices"][tet].copy()
    inverted[[1, 2]] = inverted[[2, 1]]
    import pytest
    with pytest.raises(ValueError, match="strictly positive"):
        ecm_energy_force(inverted, reference)

