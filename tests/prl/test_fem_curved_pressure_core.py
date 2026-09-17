"""In-memory isoparametric/pressure qualification of the public core seam."""

import numpy as np
import pytest

from prl.fem.follower_pressure import assemble_pressure, validate_faces
from prl.fem.mixed_hex import assemble, precompute, solve, structured_mesh


def curved_mesh(counts=(1, 1, 1)):
    mesh = structured_mesh(counts, lengths=(2, 1, 1))
    def warp(points):
        result = points.copy()
        result[:, 1] += 0.12 * (points[:, 0] / 2)**2
        result[:, 2] += 0.08 * (points[:, 0] / 2) * points[:, 1]
        return result
    mesh["nodes"] = warp(mesh["nodes"])
    mesh["pressure_nodes"] = warp(mesh["pressure_nodes"])
    mesh["geometry_mapping"] = "isoparametric"
    return mesh


def state_vector(mesh, F=None):
    vector = np.zeros(3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
    if F is not None:
        vector[:3 * len(mesh["nodes"])] = (mesh["nodes"] @ (F - np.eye(3)).T).ravel()
    return vector


def test_curved_reference_mapping_reproduces_physical_affine_F_and_volume():
    mesh = curved_mesh((2, 1, 1))
    prepared = precompute(mesh)
    F = np.array([[1.03, .02, 0], [0, .98, .01], [.01, 0, 1.02]])
    evaluated = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 100, state_vector(mesh, F))
    np.testing.assert_allclose(evaluated["F"], np.broadcast_to(F, evaluated["F"].shape), atol=2e-15)
    assert prepared["weights"].sum() == pytest.approx(2, abs=3e-15)
    assert prepared["gradients"].shape == (2, 27, 27, 3)
    assert np.ptp(prepared["reference_jacobians"][..., 1, 0]) > .01


def test_curved_reference_rigid_rotation_has_zero_strain_and_stress():
    mesh = curved_mesh()
    angle = .7
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    evaluated = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 1000, state_vector(mesh, rotation))
    np.testing.assert_allclose(evaluated["Green"], 0, atol=3e-15)
    np.testing.assert_allclose(evaluated["P"], 0, atol=1e-14)
    np.testing.assert_allclose(evaluated["J"], 1, atol=3e-15)


def test_explicit_box_isoparametric_matches_legacy_affine_and_none_pressure_is_unchanged():
    mesh = structured_mesh((1, 1, 1), lengths=(2, 1, 1))
    vector = np.random.default_rng(11).normal(0, .004, 3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
    old = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 100, vector)
    explicit_none = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 100, vector, follower_pressure=None)
    np.testing.assert_array_equal(old["residual"], explicit_none["residual"])
    np.testing.assert_array_equal(old["tangent"].toarray(), explicit_none["tangent"].toarray())
    mesh["geometry_mapping"] = "isoparametric"
    mapped = assemble(mesh, {"model": "neo_hookean", "mu": 1}, 100, vector)
    np.testing.assert_allclose(old["residual"], mapped["residual"], atol=2e-15)
    np.testing.assert_allclose(old["tangent"].toarray(), mapped["tangent"].toarray(), atol=8e-15)


@pytest.mark.parametrize("bad", ["reverse", "collapse", "nan"])
def test_invalid_reference_jacobian_is_rejected_not_absoluted(bad):
    mesh = curved_mesh()
    if bad == "reverse":
        mesh["nodes"][:, 0] *= -1
    elif bad == "collapse":
        mesh["nodes"][:, 0] = 0
    else:
        mesh["nodes"][0, 0] = np.nan
    with pytest.raises(ValueError):
        precompute(mesh)


@pytest.mark.parametrize("axis,side", [(axis, side) for axis in range(3) for side in (-1, 1)])
def test_pressure_sign_and_reference_face_area(axis, side):
    mesh = structured_mesh((1, 1, 1), lengths=(2, 1, 1))
    pressure = 0.7
    result = assemble_pressure(mesh, np.zeros_like(mesh["nodes"]), [(0, axis, side)], pressure)
    area = 2 / mesh["lengths"][axis]
    expected = np.zeros(3)
    expected[axis] = -pressure * side * area
    np.testing.assert_allclose(result["resultant"], expected, atol=5e-15)
    assert result["current_area"] == pytest.approx(area)
    assert not result["energy_available"]


def test_pressure_force_covaries_with_rotation_and_current_area_scaling():
    mesh = curved_mesh()
    faces = [(0, 1, 1), (0, 2, -1)]
    X = mesh["nodes"]
    base = assemble_pressure(mesh, np.zeros_like(X), faces, .3)
    angle = .6
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    rotated = assemble_pressure(mesh, X @ rotation.T - X + [.2, -.1, .03], faces, .3)
    np.testing.assert_allclose(rotated["force"].reshape(-1, 3), base["force"].reshape(-1, 3) @ rotation.T, atol=2e-15)
    scaled = assemble_pressure(mesh, 0.4 * X, faces, .3)
    np.testing.assert_allclose(scaled["force"], 1.4**2 * base["force"], atol=2e-15)
    assert scaled["current_area"] == pytest.approx(1.4**2 * base["current_area"])


def test_curved_pressure_tangent_and_complete_mixed_residual_tangent_match_FD():
    mesh = curved_mesh()
    random = np.random.default_rng(890)
    vector = random.normal(0, .003, len(state_vector(mesh)))
    direction = random.normal(size=len(vector))
    direction /= np.linalg.norm(direction)
    material = {"model": "neo_hookean", "mu": 1}
    load = {"faces": [(0, 1, 1), (0, 2, -1)], "pressure": .2}
    ndisp = 3 * len(mesh["nodes"])
    step = 1e-6
    pressure = assemble_pressure(mesh, vector[:ndisp], **load)
    plus = assemble_pressure(mesh, (vector + step * direction)[:ndisp], **load, with_tangent=False)
    minus = assemble_pressure(mesh, (vector - step * direction)[:ndisp], **load, with_tangent=False)
    np.testing.assert_allclose(pressure["tangent"] @ direction[:ndisp], (plus["force"] - minus["force"]) / (2 * step),
                               rtol=2e-7, atol=3e-10)
    evaluated = assemble(mesh, material, 100, vector, follower_pressure=load)
    plus_mixed = assemble(mesh, material, 100, vector + step * direction, follower_pressure=load, with_tangent=False)
    minus_mixed = assemble(mesh, material, 100, vector - step * direction, follower_pressure=load, with_tangent=False)
    np.testing.assert_allclose(evaluated["tangent"] @ direction,
                               (plus_mixed["residual"] - minus_mixed["residual"]) / (2 * step), rtol=2e-7, atol=2e-9)
    assert not evaluated["energy_is_total_potential"]
    np.testing.assert_array_equal(evaluated["total_external_forces"][:ndisp], pressure["force"])
    # Open follower faces need not give a symmetric all-DOF tangent.
    assert np.linalg.norm(pressure["tangent"].toarray() - pressure["tangent"].toarray().T) > .01


def test_closed_pressure_surface_has_zero_resultant_and_moment():
    mesh = curved_mesh()
    faces = [(0, axis, side) for axis in range(3) for side in (-1, 1)]
    result = assemble_pressure(mesh, .03 * mesh["nodes"], faces, .7)
    np.testing.assert_allclose(result["resultant"], 0, atol=2e-15)
    np.testing.assert_allclose(np.cross(1.03 * mesh["nodes"], result["force"].reshape(-1, 3)).sum(axis=0), 0, atol=3e-15)


@pytest.mark.parametrize("faces", [[(0, 0, 1)], [(0, 2, 1), (0, 2, 1)], [(0, 3, 1)],
                                   [(0, 1, 0)], [(-1, 2, 1)], [(2, 2, 1)], [(0., 2, 1)]])
def test_internal_duplicate_or_invalid_faces_rejected(faces):
    mesh = structured_mesh((2, 1, 1))
    with pytest.raises(ValueError):
        validate_faces(mesh, faces)


def test_pressure_surface_rejects_inverted_current_jacobian():
    mesh = curved_mesh()
    displacement = np.zeros_like(mesh["nodes"])
    displacement[:, 0] = -2 * mesh["nodes"][:, 0]
    with pytest.raises(ValueError, match="Jacobian"):
        assemble_pressure(mesh, displacement, [(0, 1, 1)], .1)


def test_pressure_surface_rejects_finite_coordinates_with_overflowing_jacobian_determinant():
    mesh = structured_mesh((1, 1, 1))
    mesh["nodes"] *= [1e250, 1e50, 1e50]
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="Jacobian"):
            assemble_pressure(mesh, np.zeros_like(mesh["nodes"]), [(0, 0, 1)], .1)


def test_small_curved_pressure_solve_uses_consistent_load_and_original_residual_gate():
    mesh = curved_mesh()
    fixed = {3 * int(node) + component: 0 for node in np.flatnonzero(mesh["nodes"][:, 0] == 0)
             for component in range(3)}
    load = {"faces": [(0, 0, 1)], "pressure": .002}
    result = solve(mesh, {"model": "neo_hookean", "mu": 1}, 100,
                   dirichlet=fixed, follower_pressure=load)
    assert result["converged"]
    assert result["normalized_free_residual"] <= 1e-9
    assert result["iterations"] > 0
    np.testing.assert_array_equal(result["external_forces"], 0)  # legacy key is dead load only
    assert np.linalg.norm(result["pressure_forces"]) > 0
    np.testing.assert_array_equal(result["total_external_forces"], result["pressure_forces"])
    assert not result["energy_is_total_potential"]
