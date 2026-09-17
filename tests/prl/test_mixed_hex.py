"""In-memory checks for the public mixed-Q2/Q1 assembly and solve seam."""

from itertools import product

import numpy as np
import pytest

from prl.fem.mixed_hex import (
    MixedSolveError, assemble, precompute, shape_functions, solve, structured_mesh,
)


def test_shape_partition_gradient_and_linear_reproduction():
    points = np.array([[-0.7, 0.2, 0.4], [0, 0, 0], [0.8, -0.3, -0.9]])
    shape = shape_functions(points)
    local_coordinates = np.array(list(product((-1, 0, 1), repeat=3)))
    np.testing.assert_allclose(shape["q2"].sum(axis=1), 1, atol=1e-15)
    np.testing.assert_allclose(shape["q1"].sum(axis=1), 1, atol=1e-15)
    np.testing.assert_allclose(shape["q2_derivatives"].sum(axis=1), 0, atol=1e-15)
    np.testing.assert_allclose(shape["q2"] @ local_coordinates, points, atol=1e-15)
    np.testing.assert_allclose(np.einsum("qaj,ai->qij", shape["q2_derivatives"], local_coordinates),
                               np.broadcast_to(np.eye(3), (3, 3, 3)), atol=1e-15)


def test_conforming_mesh_quadrature_and_affine_geometry():
    mesh = structured_mesh((2, 1, 1), lengths=(4, 2, 3))
    prepared = precompute(mesh)
    assert len(np.intersect1d(*mesh["elements"])) == 9
    assert len(np.intersect1d(*mesh["pressure_elements"])) == 4
    assert len(prepared["weights"]) == 27
    assert prepared["weights"].sum() * len(mesh["elements"]) == pytest.approx(24)
    jacobian = np.einsum("eai,qaJ->eqiJ", mesh["nodes"][mesh["elements"]], prepared["gradients"])
    np.testing.assert_allclose(jacobian, np.broadcast_to(np.eye(3), jacobian.shape), atol=2e-15)


def test_zero_state_has_zero_stress_and_residual():
    mesh = structured_mesh((1, 1, 1))
    vector = np.zeros(3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
    evaluated = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 1000, vector)
    np.testing.assert_allclose(evaluated["residual"], 0, atol=1e-14)
    np.testing.assert_allclose(evaluated["cauchy_stress"], 0, atol=1e-14)
    np.testing.assert_allclose(evaluated["Green"], 0, atol=1e-14)
    assert evaluated["energy"] == pytest.approx(0, abs=1e-14)


def test_uniform_affine_patch_has_balanced_interior_and_pressure_equations():
    mesh = structured_mesh((2, 1, 1), lengths=(2, 1, 1))
    F = np.array([[1.08, 0.04, 0.01], [0, 0.96, 0.02], [0, 0, 1.02]])
    kappa = 100
    displacement = mesh["nodes"] @ (F - np.eye(3)).T
    pressure = np.full(len(mesh["pressure_nodes"]), kappa * (np.linalg.det(F) - 1))
    vector = np.concatenate((displacement.ravel(), pressure))
    evaluated = assemble(mesh, {"model": "neo_hookean", "mu": 1}, kappa, vector, active_tension=0.2)
    interior = np.all((mesh["nodes"] > 0) & (mesh["nodes"] < mesh["lengths"]), axis=1)
    interior_dofs = (3 * np.flatnonzero(interior)[:, None] + np.arange(3)).ravel()
    np.testing.assert_allclose(evaluated["F"], np.broadcast_to(F, evaluated["F"].shape), atol=3e-15)
    np.testing.assert_allclose(evaluated["residual"][interior_dofs], 0, atol=2e-14)
    np.testing.assert_allclose(evaluated["residual"][3 * len(mesh["nodes"]):], 0, atol=2e-14)


@pytest.mark.parametrize("material", [
    {"model": "neo_hookean", "mu": 1.3},
    {"model": "guccione", "C": 1.2, "bff": 8, "bxx": 2, "bfx": 4},
])
def test_mixed_tangent_and_potential_derivative(material):
    mesh = structured_mesh((1, 1, 1))
    random = np.random.default_rng(731)
    vector = random.normal(0, 0.007, 3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
    vector[-8:] *= 10
    direction = random.normal(size=len(vector))
    direction /= np.linalg.norm(direction)
    active = 0.3
    evaluated = assemble(mesh, material, 100, vector, active_tension=active)
    step = 2e-6
    plus = assemble(mesh, material, 100, vector + step * direction, active_tension=active, with_tangent=False)
    minus = assemble(mesh, material, 100, vector - step * direction, active_tension=active, with_tangent=False)
    finite_difference = (plus["residual"] - minus["residual"]) / (2 * step)
    np.testing.assert_allclose(evaluated["tangent"] @ direction, finite_difference, rtol=3e-7, atol=3e-9)
    assert (plus["energy"] - minus["energy"]) / (2 * step) == pytest.approx(
        evaluated["residual"] @ direction, rel=3e-7, abs=3e-10)
    np.testing.assert_allclose(evaluated["tangent"].toarray(), evaluated["tangent"].toarray().T, atol=1e-13)


def test_small_axial_stretch_solves_free_lateral_response():
    mesh = structured_mesh((1, 1, 1), lengths=(2, 1, 1))
    prescribed = {}
    for node, coordinates in enumerate(mesh["nodes"]):
        for axis in range(3):
            if coordinates[axis] == 0:
                prescribed[3 * node + axis] = 0.0
        if coordinates[0] == 2:
            prescribed[3 * node] = 0.1
    result = solve(mesh, {"model": "neo_hookean", "mu": 1}, 1000, dirichlet=prescribed)
    assert result["converged"]
    assert result["normalized_free_residual"] < 1e-9
    assert result["J"].min() > 0
    assert result["iterations"] <= 30
    # Symmetry gives a homogeneous solution without prescribing lateral strain.
    gradients = result["F"].reshape(-1, 3, 3)
    np.testing.assert_allclose(gradients, np.broadcast_to(gradients[0], gradients.shape), atol=2e-9)
    assert gradients[0, 0, 0] == pytest.approx(1.05)
    assert 0.95 < gradients[0, 1, 1] < 1
    assert gradients[0, 1, 1] == pytest.approx(gradients[0, 2, 2], abs=1e-10)
    residual_history = [item["normalized_free_residual"] for item in result["history"]]
    assert all(later < earlier for earlier, later in zip(residual_history, residual_history[1:]))
    np.testing.assert_array_equal(result["u"], result["displacement"])
    np.testing.assert_array_equal(result["p"], result["pressure"])


def test_inverted_initial_state_is_rejected_and_retained():
    mesh = structured_mesh((1, 1, 1))
    initial = np.zeros(3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
    initial[:3 * len(mesh["nodes"])].reshape(-1, 3)[:, 0] = -2 * mesh["nodes"][:, 0]
    with pytest.raises(MixedSolveError) as captured:
        solve(mesh, {"model": "neo_hookean", "mu": 1}, 1000, initial=initial)
    np.testing.assert_array_equal(captured.value.last_state["vector"], initial)
    assert not captured.value.last_state["converged"]
    assert captured.value.last_state["history"] == []


def test_invalid_bounds_and_pressure_external_force_rejected():
    mesh = structured_mesh((1, 1, 1))
    with pytest.raises(ValueError, match="line-search"):
        solve(mesh, {"model": "neo_hookean", "mu": 1}, 1000, max_line_search=17)
    size = 3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"])
    forces = np.zeros(size)
    forces[-1] = 1
    with pytest.raises(ValueError, match="pressure equations"):
        assemble(mesh, {"model": "neo_hookean", "mu": 1}, 1000, np.zeros(size), external_forces=forces)
