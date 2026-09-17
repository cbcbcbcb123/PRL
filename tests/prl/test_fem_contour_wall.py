"""In-memory geometry and pressure checks; never solve a formal F5 load."""

from itertools import product
import json

import numpy as np
import pytest

from prl.fem.contour_wall import build_contour_wall
from prl.fem.follower_pressure import assemble_pressure, validate_faces
from prl.fem.mixed_hex import precompute


def source_fixture():
    theta = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    center = np.array([17., 29.])
    radius = 1 + .07 * np.cos(3 * theta)
    curve = center + 4 * radius[:, None] * np.column_stack((1.4 * np.cos(theta), np.sin(theta)))
    return {"smooth_contour_um": curve, "center_um": center, "length_scale_um": np.asarray(4.)}


def test_default_geometry_counts_layers_and_minimal_gauges():
    source = source_fixture()
    before = {key: value.copy() for key, value in source.items()}
    result = build_contour_wall(source, (1, 1, 2))
    mesh, fixed, metadata = result["mesh"], result["fixed"], result["metadata"]
    assert mesh["nodes"].shape == (9 * 72 * 3, 3)
    assert mesh["pressure_nodes"].shape == (5 * 36 * 2, 3)
    assert mesh["elements"].shape == (144, 27)
    assert mesh["pressure_elements"].shape == (144, 8)
    assert mesh["counts"] == (4, 36, 1)
    assert mesh["geometry_mapping"] == "isoparametric"
    assert mesh["periodic_axis"] == 1
    assert metadata["node_shape"] == list(mesh["node_shape"])
    assert metadata["pressure_shape"] == list(mesh["pressure_shape"])
    np.testing.assert_array_equal(metadata["inner_midplane_nodes"], 3 * np.arange(72) + 1)
    np.testing.assert_array_equal(metadata["outer_midplane_nodes"], 8 * 72 * 3 + 3 * np.arange(72) + 1)
    np.testing.assert_array_equal(np.bincount(result["layer_ids"]), [36, 36, 72])
    assert len(fixed) == len(mesh["nodes"]) + 3
    assert all(fixed[3 * node + 2] == 0 for node in range(len(mesh["nodes"])))
    anchor = metadata["anchor_node_ids"]
    expected = [3 * anchor["A"], 3 * anchor["A"] + 1, 3 * anchor["B"] + 1]
    assert sorted(key for key in fixed if key % 3 != 2) == sorted(expected)
    assert 3 * anchor["B"] not in fixed
    np.testing.assert_allclose(mesh["nodes"][[anchor["A"], anchor["B"]], 2], .25, atol=0)
    assert abs(mesh["nodes"][anchor["B"], 1] - mesh["nodes"][anchor["A"], 1]) < 1e-14
    assert mesh["nodes"][anchor["B"], 0] > mesh["nodes"][anchor["A"], 0]
    for key in source:
        np.testing.assert_array_equal(source[key], before[key])
    json.dumps(metadata, allow_nan=False)
    fine = build_contour_wall(source, (2, 2, 4))
    assert fine["mesh"]["nodes"].shape == (17 * 72 * 3, 3)
    assert fine["mesh"]["pressure_nodes"].shape == (9 * 36 * 2, 3)
    assert fine["mesh"]["elements"].shape == (288, 27)
    assert fine["mesh"]["pressure_elements"].shape == (288, 8)
    np.testing.assert_array_equal(np.bincount(fine["layer_ids"]), [72, 72, 144])


def test_q2_q1_periodic_seam_shares_ids_and_has_no_coincident_nodes():
    result = build_contour_wall(source_fixture(), (1, 1, 2), segments=12)
    mesh = result["mesh"]
    for order, key in ((2, "elements"), (1, "pressure_elements")):
        local = np.array(list(product(range(order + 1), repeat=3)))
        for radial in range(4):
            first, last = mesh[key][12 * radial], mesh[key][12 * radial + 11]
            np.testing.assert_array_equal(first[local[:, 1] == 0], last[local[:, 1] == order])
        assert len(np.unique(mesh[key])) == len(mesh["nodes" if order == 2 else "pressure_nodes"])
    for key in ("nodes", "pressure_nodes"):
        assert len(np.unique(mesh[key], axis=0)) == len(mesh[key])
    assert len(validate_faces(mesh, result["inner_faces"])) == 12
    with pytest.raises(ValueError, match="internal"):
        validate_faces(mesh, [(11, 1, 1)])
    with pytest.raises(ValueError, match="internal"):
        validate_faces(mesh, [(0, 0, 1)])


def test_radial_refinement_preserves_curve_interfaces_and_exact_domain():
    coarse = build_contour_wall(source_fixture(), (1, 1, 2), segments=12)
    fine = build_contour_wall(source_fixture(), (2, 2, 4), segments=12)
    for key in ("outer_curve_nodes", "outer_curve_nodes_um", "radial_boundary_fractions"):
        np.testing.assert_array_equal(coarse["metadata"][key], fine["metadata"][key])
    coarse_grid = coarse["mesh"]["nodes"].reshape(9, 24, 3, 3)
    fine_grid = fine["mesh"]["nodes"].reshape(17, 24, 3, 3)
    np.testing.assert_allclose(fine_grid[::2], coarse_grid, rtol=0, atol=5e-16)
    for result in (coarse, fine):
        for fraction in (20 / 27, 21 / 27, 22 / 27, 1.):
            assert fraction in result["metadata"]["radial_q1_fractions"]
        prepared = precompute(result["mesh"])
        assert prepared["reference_jacobian_determinants"].min() > 0
        expected = result["metadata"]["exact_outer_area"] * (1 - (20 / 27)**2) * .5
        assert prepared["weights"].sum() == pytest.approx(expected, rel=2e-15)
    assert precompute(coarse["mesh"])["weights"].sum() == pytest.approx(
        precompute(fine["mesh"])["weights"].sum(), rel=2e-15)


def test_closed_inner_pressure_has_zero_resultant_and_moment_and_positive_virtual_area_work():
    result = build_contour_wall(source_fixture(), (1, 1, 2), segments=12)
    mesh = result["mesh"]
    evaluated = assemble_pressure(mesh, np.zeros_like(mesh["nodes"]), result["inner_faces"], .08,
                                  with_tangent=False)
    forces = evaluated["force"].reshape(-1, 3)
    np.testing.assert_allclose(forces.sum(axis=0), 0, atol=2e-15)
    np.testing.assert_allclose(np.cross(mesh["nodes"], forces).sum(axis=0), 0, atol=2e-15)
    virtual = mesh["nodes"].copy()
    virtual[:, 2] = 0
    work = np.sum(forces * virtual)
    assert work == pytest.approx(.08 * .5 * 2 * result["metadata"]["exact_inner_area"], rel=3e-15)


def test_source_rotation_translation_covariance_and_inverse_mapping():
    source = source_fixture()
    base = build_contour_wall(source, (1, 1, 2), segments=12)
    angle = .71
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    shift = np.array([31., -13.])
    changed = {**source, "smooth_contour_um": source["smooth_contour_um"] @ rotation.T + shift,
               "center_um": source["center_um"] @ rotation.T + shift}
    moved = build_contour_wall(changed, (1, 1, 2), segments=12)
    np.testing.assert_allclose(moved["mesh"]["nodes"], base["mesh"]["nodes"], atol=8e-15, rtol=0)
    metadata = moved["metadata"]
    recovered = (np.array(metadata["outer_curve_nodes"]) @ np.array(metadata["solver_to_source_rotation"]).T
                 * metadata["length_scale_um"] + metadata["center_um"])
    np.testing.assert_allclose(recovered, metadata["outer_curve_nodes_um"], atol=1e-14)
    assert np.linalg.det(metadata["source_to_solver_rotation"]) == pytest.approx(1.)


def test_exact_orientation_minimum_includes_between_node_extrema():
    result = build_contour_wall(source_fixture(), (1, 1, 2), segments=12)
    boundary = np.array(result["metadata"]["outer_curve_nodes"])
    cells = np.stack([boundary[(2 * np.arange(12) + offset) % 24] for offset in range(3)], axis=1)
    xi = np.linspace(-1, 1, 2001)
    basis = np.column_stack((xi * (xi - 1) / 2, 1 - xi**2, xi * (xi + 1) / 2))
    derivative = np.column_stack((xi - .5, -2 * xi, xi + .5))
    points = np.einsum("qa,eai->eqi", basis, cells)
    tangents = np.einsum("qa,eai->eqi", derivative, cells)
    dense_min = np.min(points[..., 0] * tangents[..., 1] - points[..., 1] * tangents[..., 0])
    exact_min = result["metadata"]["minimum_orientation_cross"]
    assert 0 < exact_min <= dense_min + 1e-15
    assert abs(exact_min - dense_min) < 2e-8


def test_twice_wound_source_contour_is_not_a_valid_closed_wall():
    source = source_fixture()
    source["smooth_contour_um"] = np.tile(source["smooth_contour_um"], (2, 1))
    with pytest.raises(ValueError, match="winding"):
        build_contour_wall(source, (1, 1, 2), segments=12)


@pytest.mark.parametrize("intervals", [(1, 1), (1, 0, 2), (1, -1, 2), (1, True, 2), (1., 1, 2)])
def test_invalid_radial_intervals_rejected(intervals):
    with pytest.raises(ValueError):
        build_contour_wall(source_fixture(), intervals)


@pytest.mark.parametrize("segments", [0, -1, 3, 4.5, True])
def test_invalid_segment_counts_rejected(segments):
    with pytest.raises(ValueError):
        build_contour_wall(source_fixture(), (1, 1, 2), segments=segments)


@pytest.mark.parametrize("height", [0, -1, np.nan, np.inf, True, 1j])
def test_invalid_height_rejected(height):
    with pytest.raises(ValueError):
        build_contour_wall(source_fixture(), (1, 1, 2), height=height)


@pytest.mark.parametrize("bad", ["nan", "reverse", "outside_center", "zero_scale", "nan_scale", "complex",
                                "duplicate_endpoint", "wrong_shape", "missing"])
def test_invalid_source_rejected(bad):
    source = source_fixture()
    if bad == "nan":
        source["smooth_contour_um"][0, 0] = np.nan
    elif bad == "reverse":
        source["smooth_contour_um"] = source["smooth_contour_um"][::-1]
    elif bad == "outside_center":
        source["center_um"] = np.array([100., 100.])
    elif bad == "zero_scale":
        source["length_scale_um"] = 0
    elif bad == "nan_scale":
        source["length_scale_um"] = np.nan
    elif bad == "complex":
        source["smooth_contour_um"] = source["smooth_contour_um"].astype(complex)
    elif bad == "duplicate_endpoint":
        source["smooth_contour_um"] = np.vstack((source["smooth_contour_um"], source["smooth_contour_um"][0]))
    elif bad == "wrong_shape":
        source["smooth_contour_um"] = source["smooth_contour_um"].ravel()
    else:
        source.pop("center_um")
    with pytest.raises(ValueError):
        build_contour_wall(source, (1, 1, 2), segments=12)
