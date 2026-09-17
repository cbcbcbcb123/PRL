"""In-memory regression for admissible nonhomogeneous Dirichlet prediction."""

import numpy as np
import pytest

from prl.fem import mixed_hex


def rotation_boundary(mesh, degrees):
    angle = np.deg2rad(degrees)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    xyz = mesh["nodes"]
    on_boundary = np.any(np.isclose(xyz, 0) | np.isclose(xyz, mesh["lengths"]), axis=1)
    displacement = xyz @ rotation.T - xyz
    prescribed = {3 * int(node) + component: float(displacement[node, component])
                  for node in np.flatnonzero(on_boundary) for component in range(3)}
    return prescribed, displacement


def test_previous_zero_state_to_15_degree_boundary_is_lifted_without_inversion():
    mesh = mixed_hex.structured_mesh((2, 2, 2), lengths=(2, 1, 1))
    zero_boundary, _ = rotation_boundary(mesh, 0)
    boundary, expected = rotation_boundary(mesh, 15)
    material = {"model": "neo_hookean", "mu": 1.0}
    previous = mixed_hex.solve(mesh, material, 1000, dirichlet=zero_boundary)
    # Reproduce the actual failed path first: only boundary values were changed.
    with pytest.raises(mixed_hex.MixedSolveError, match="inadmissible initial"):
        mixed_hex.solve(mesh, material, 1000, dirichlet=boundary, initial=previous)
    lifted = mixed_hex.lift_dirichlet_initial(mesh, previous, boundary)
    np.testing.assert_allclose(lifted["vector"][:3 * len(mesh["nodes"])].reshape(-1, 3), expected, atol=2e-14)
    assert lifted["diagnostics"]["min_J"] > 1 - 2e-13
    assert lifted["diagnostics"]["max_J"] < 1 + 2e-13
    assert lifted["diagnostics"]["dirichlet_max_error"] == 0
    assert lifted["diagnostics"]["constrained_dofs"] == sorted(boundary)
    np.testing.assert_array_equal(previous["vector"], 0)


def test_random_perturbation_satisfies_default_residual_not_strict_rotation_gate():
    mesh = mixed_hex.structured_mesh((2, 2, 2), lengths=(2, 1, 1))
    boundary, expected = rotation_boundary(mesh, 15)
    lifted = mixed_hex.lift_dirichlet_initial(mesh, None, boundary)
    n = len(mesh["nodes"])
    free_dofs = np.setdiff1d(np.arange(3 * n), np.array(sorted(boundary)))
    perturbation = np.random.default_rng(3105).normal(0, 0.0008, len(free_dofs))
    perturbed = lifted["vector"].copy()
    perturbed[free_dofs] += perturbation
    predicted = mixed_hex.lift_dirichlet_initial(mesh, perturbed, boundary)
    np.testing.assert_array_equal(predicted["vector"], perturbed)
    assert predicted["diagnostics"]["min_J"] > 0.9
    material = {"model": "neo_hookean", "mu": 1.0}
    recovered = mixed_hex.solve(mesh, material, 1000, initial=predicted["vector"], dirichlet=boundary)
    assert recovered["converged"]
    assert recovered["iterations"] > 0
    assert recovered["normalized_free_residual"] <= 1e-9
    np.testing.assert_allclose(recovered["u"], expected, atol=1e-9)
    # This extra, non-frozen random diagnostic had max Green = 1.59302016e-10
    # at the default residual stop, above the strict 1e-10 rotation gate.
    # It tests the stated residual behavior, NOT strict rotation qualification.
    np.testing.assert_array_equal(recovered["fixed_dofs"], sorted(boundary))


def test_frozen_60_degree_bubble_perturbation_recovers_strict_rigid_rotation():
    mesh = mixed_hex.structured_mesh((2, 2, 2), lengths=(2, 1, 1))
    boundary, expected = rotation_boundary(mesh, 60)
    lifted = mixed_hex.lift_dirichlet_initial(mesh, None, boundary)
    n = len(mesh["nodes"])
    bubble = np.prod(np.sin(np.pi * mesh["nodes"] / np.asarray(mesh["lengths"])), axis=1)
    perturbation = 0.002 * bubble[:, None] * np.array([1.0, -0.7, 0.5])
    perturbation.reshape(-1)[np.array(sorted(boundary))] = 0
    perturbed = lifted["vector"].copy()
    perturbed[:3 * n] += perturbation.ravel()
    predicted = mixed_hex.lift_dirichlet_initial(mesh, perturbed, boundary)
    np.testing.assert_array_equal(predicted["vector"], perturbed)
    assert predicted["diagnostics"]["min_J"] > 0
    recovered = mixed_hex.solve(mesh, {"model": "neo_hookean", "mu": 1}, 1000,
                                initial=predicted["vector"], dirichlet=boundary, tolerance=1e-9)
    assert recovered["converged"]
    assert recovered["iterations"] > 0
    np.testing.assert_allclose(recovered["u"], expected, atol=1e-10)
    np.testing.assert_allclose(recovered["Green"], 0, atol=1e-10)
    np.testing.assert_allclose(recovered["cauchy_stress"], 0, atol=2e-7)
    np.testing.assert_array_equal(recovered["fixed_dofs"], sorted(boundary))


def test_pressure_and_unconstrained_components_are_preserved_without_aliasing():
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    n = len(mesh["nodes"])
    initial = np.zeros(3 * n + len(mesh["pressure_nodes"]))
    initial[1:3 * n:3] = 0.007 * mesh["nodes"][:, 0]
    initial[3 * n:] = np.linspace(-0.2, 0.3, len(mesh["pressure_nodes"]))
    before = initial.copy()
    boundary = {3 * int(node): 0.02 for node in np.flatnonzero(mesh["nodes"][:, 0] == 0)}
    lifted = mixed_hex.lift_dirichlet_initial(mesh, initial, boundary)
    np.testing.assert_array_equal(initial, before)
    np.testing.assert_array_equal(lifted["vector"][3 * n:], initial[3 * n:])
    np.testing.assert_array_equal(lifted["vector"][1:3 * n:3], initial[1:3 * n:3])
    np.testing.assert_array_equal(lifted["vector"][2:3 * n:3], initial[2:3 * n:3])
    np.testing.assert_allclose(lifted["vector"][:3 * n:3], 0.02, atol=3e-16)
    assert not np.shares_memory(initial, lifted["vector"])
    assert lifted["diagnostics"]["unconstrained_components"] == [1, 2]
    assert lifted["diagnostics"]["pressure_max_change"] == 0
    assert lifted["diagnostics"]["constrained_dofs"] == sorted(boundary)


@pytest.mark.parametrize("initial_kind", ["wrong_shape", "nan", "complex", "missing_vector"])
def test_illegal_initial_state_is_rejected(initial_kind):
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    size = 3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"])
    initial = np.zeros(size)
    if initial_kind == "wrong_shape":
        initial = initial[:-1]
    elif initial_kind == "nan":
        initial[-1] = np.nan
    elif initial_kind == "complex":
        initial = initial.astype(complex)
    else:
        initial = {"not_vector": initial}
    with pytest.raises(ValueError):
        mixed_hex.lift_dirichlet_initial(mesh, initial, {0: 0})


@pytest.mark.parametrize("boundary", [{-1: 0}, {99999: 0}, {0.0: 0}, {True: 0},
                                       {0: np.nan}, {0: np.inf}, {0: 1j}, {0: [0, 1]}, []])
def test_illegal_boundary_is_rejected(boundary):
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    with pytest.raises(ValueError):
        mixed_hex.lift_dirichlet_initial(mesh, None, boundary)


def test_modified_reference_geometry_is_rejected():
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    mesh["nodes"][0, 0] = 0.01
    with pytest.raises(ValueError, match="unchanged structured mesh"):
        mixed_hex.lift_dirichlet_initial(mesh, None, {0: 0})


def test_inadmissible_lift_is_rejected_without_automatic_subdivision():
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    xyz = mesh["nodes"]
    boundary = {3 * int(node): -2 * float(xyz[node, 0]) for node in range(len(xyz))}
    with pytest.raises(ValueError, match="lifting is inadmissible"):
        mixed_hex.lift_dirichlet_initial(mesh, None, boundary)


def test_no_constraints_leaves_initial_unchanged_and_calls_no_material(monkeypatch):
    mesh = mixed_hex.structured_mesh((1, 1, 1))
    size = 3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"])
    initial = np.zeros(size)
    initial[:3 * len(mesh["nodes"])].reshape(-1, 3)[:, 0] = 0.01 * mesh["nodes"][:, 0]
    def forbidden(*args, **kwargs):
        raise AssertionError("lifting must not evaluate a constitutive law")
    monkeypatch.setattr(mixed_hex, "material_response", forbidden)
    result = mixed_hex.lift_dirichlet_initial(mesh, initial, {})
    np.testing.assert_array_equal(result["vector"], initial)
    assert result["diagnostics"]["unconstrained_components"] == [0, 1, 2]
    assert result["diagnostics"]["automatic_subdivisions"] == 0
