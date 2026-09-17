"""Pure geometry and analytic state fixtures; no production solver is called."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from prl.verification.fem_contour_pressure import (
    _CASES, _EVIDENCE_BOUNDARY, _FRACTIONS, _GEOMETRY_BOUNDARY, _LOADS,
    _PREFLIGHT, _SOLVER, _SOURCE_SHA, _THRESHOLDS, _surface_pressure,
    _area_average, _check_configuration, _quadrature, _state,
    boundary_safety, orientation_minimum, q2_area, reference_mesh,
    source_diagnostics, verify_contour_case, verify_fem_contour_pressure,
)


def _source_fixture():
    theta = np.arange(720) * 2.0 * np.pi / 720
    center = np.array([48.0, 48.0])
    smooth = center + 30.0 * np.column_stack((np.cos(theta), np.sin(theta)))
    raw_theta = np.arange(7200) * 2.0 * np.pi / 7200
    raw = center + 30.0 * np.column_stack((np.cos(raw_theta), np.sin(raw_theta)))
    rows, columns = np.indices((96, 96))
    mask = (rows - center[1])**2 + (columns - center[0])**2 < 30**2
    return {"smooth_contour_um": smooth, "raw_contour_um": raw,
            "center_um": center, "length_scale_um": np.asarray(10.0),
            "slice_mask": mask, "source_slice_mask": mask.copy(),
            "voxel_um": np.array([1.0, 1.0, 1.0]), "slice_z_index": np.asarray(39)}


@pytest.fixture(scope="module")
def zero_data():
    source = _source_fixture()
    mesh = reference_mesh(source, [1, 1, 2])
    nodes, elements, pressures = len(mesh["coordinates"]), len(mesh["cells"]), len(mesh["pressure_coordinates"])
    F = np.broadcast_to(np.eye(3), (5, elements, 27, 3, 3)).copy()
    payload = {**mesh, "loads": _LOADS.copy(), "displacements": np.zeros((5, nodes, 3)),
        "pressure_dofs": np.zeros((5, pressures)), "fixed_values": np.zeros((5, len(mesh["fixed_dofs"]))),
        "initial_vectors": np.zeros((5, 3 * nodes + pressures)),
        "external_forces": np.zeros((5, 3 * nodes)), "reaction": np.zeros((5, 3 * nodes)),
        "newton_residual": np.zeros(5), "F": F, "J": np.ones((5, elements, 27)),
        "Green": np.zeros_like(F), "P": np.zeros_like(F), "Cauchy": np.zeros_like(F),
        "energy": np.zeros((5, elements, 27))}
    history = [[{"iteration": 0, "normalized_free_residual": 0.0, "min_J": 1.0,
                 "step_length": 0.0, "line_search_trials": 0}] for _ in range(5)]
    quadrature = _quadrature(payload, mesh)
    return source, payload, history, quadrature


def _configuration():
    return {**copy.deepcopy(_EVIDENCE_BOUNDARY), "solver": copy.deepcopy(_SOLVER),
        "cases": copy.deepcopy(_CASES), "material": {"model": "neo_hookean", "mu": 1.0},
        "kappa": 1000.0, "loads": _LOADS.tolist(), "thresholds": copy.deepcopy(_THRESHOLDS),
        "geometry": {**copy.deepcopy(_GEOMETRY_BOUNDARY), "segments": 36, "height": 0.5, "radial_boundary_fractions": _FRACTIONS.tolist(),
            "source_result": "results/ventricle_fem/f2_measured_contour_v01_20260917",
            "source_geometry": "results/ventricle_fem/f2_measured_contour_v01_20260917/geometry_source.npz",
            "source_geometry_sha256": _SOURCE_SHA, "frozen_preflight": copy.deepcopy(_PREFLIGHT)},
        "resources": {"threads": 1, "gpu": 0, "dcm": 0, "seconds": 1200,
                      "stage_bytes": 67108864, "reserve_bytes": 67108864, "automatic_retries": 0}}


def test_reference_mesh_has_shared_periodic_q2_q1_nodes_and_only_three_gauges(zero_data):
    _, payload, _, _ = zero_data
    assert payload["coordinates"].shape == (9 * 72 * 3, 3)
    assert payload["pressure_coordinates"].shape == (5 * 36 * 2, 3)
    assert payload["cells"].shape == (144, 27)
    assert len(np.unique(payload["coordinates"], axis=0)) == len(payload["coordinates"])
    assert len(np.unique(payload["pressure_coordinates"], axis=0)) == len(payload["pressure_coordinates"])
    assert len(np.intersect1d(payload["cells"][0], payload["cells"][35])) == 9
    assert len(np.intersect1d(payload["pressure_cells"][0], payload["pressure_cells"][35])) == 4
    gauge = payload["fixed_dofs"][payload["fixed_dofs"] % 3 != 2]
    first, second = payload["anchor_node_ids"]
    assert np.array_equal(gauge, [3 * first, 3 * first + 1, 3 * second + 1])
    assert 3 * second not in payload["fixed_dofs"]


def test_curved_gradient_reproduces_linear_physical_fields(zero_data):
    _, payload, _, quadrature = zero_data
    recovered = np.einsum("eai,eqaj->eqij", payload["coordinates"][payload["cells"]], quadrature["gradients"])
    assert np.max(np.abs(recovered - np.eye(3))) < 1e-12
    assert quadrature["geometry"]["status"] == "passed"
    assert abs(quadrature["geometry"]["reference_volume"] / quadrature["geometry"]["area_based_reference_volume"] - 1.0) < 1e-12


def test_radial_refinement_preserves_the_complete_reference_domain(zero_data):
    source, coarse, _, coarse_quadrature = zero_data
    fine = reference_mesh(source, [2, 2, 4])
    fine_quadrature = _quadrature(fine, fine)
    assert np.array_equal(coarse["outer_curve_q2"], fine["outer_curve_q2"])
    assert np.allclose(coarse["radial_fractions"], fine["radial_fractions"][::2], atol=1e-15, rtol=0.0)
    for field in ("reference_inner_area", "reference_outer_area", "reference_volume"):
        assert abs(coarse_quadrature["geometry"][field] / fine_quadrature["geometry"][field] - 1) < 1e-12


@pytest.mark.parametrize("field", ["cells", "pressure_cells", "inner_faces", "layer_ids", "anchor_node_ids", "radial_fractions", "outer_curve_q2", "source_to_solver_rotation"])
def test_tampered_topology_geometry_or_metadata_is_rejected(zero_data, field):
    source, payload, _, _ = zero_data
    corrupted = {name: value.copy() for name, value in payload.items()}
    corrupted[field].flat[0] += 1
    with pytest.raises(ValueError, match="frozen mesh|saved"):
        _quadrature(corrupted, reference_mesh(source, [1, 1, 2]))


def test_q2_area_obeys_translation_rotation_and_affine_determinant(zero_data):
    nodes = zero_data[1]["outer_curve_q2"]
    angle = 0.37
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    assert q2_area(nodes @ rotation.T + [3, -2]) == pytest.approx(q2_area(nodes), rel=1e-13)
    assert q2_area(nodes @ np.diag([1.2, 0.8])) == pytest.approx(0.96 * q2_area(nodes), rel=1e-13)


def test_analytic_orientation_minimum_detects_reverse_curve(zero_data):
    curve = zero_data[1]["outer_curve_q2"]
    assert orientation_minimum(curve) > 0
    assert orientation_minimum(curve[::-1]) < 0


def test_boundary_safety_rejects_crossing_and_unnested_cavities(zero_data):
    curve = zero_data[1]["outer_curve_q2"]
    assert boundary_safety(0.74 * curve, curve)
    assert not boundary_safety(1.1 * curve, curve)
    crossed = curve.copy()
    crossed[[10, 44]] = crossed[[44, 10]]
    assert not boundary_safety(0.74 * curve, crossed)


def test_independent_source_scanline_and_distance_accept_known_circle():
    report = source_diagnostics(_source_fixture())
    assert report["status"] == "passed", report
    assert report["source_mask_iou"] > 0.99
    assert report["raw_contour_hausdorff_um"] < 0.05
    assert report["frozen_preflight"] == _PREFLIGHT
    assert "not a bitwise target" in report["preflight_comparison_method"]
    for key, value in _PREFLIGHT.items():
        assert report["independent_minus_frozen_preflight"][key] == report[key] - value


def test_zero_pressure_reference_state_passes_independent_mechanics(zero_data):
    _, payload, _, quadrature = zero_data
    state = _state(payload, 0, quadrature)
    assert state["geometry_status"] == "passed", state
    assert state["fields_status"] == "passed", state
    assert state["equilibrium_status"] == "passed", state
    assert abs(state["cavity_area_change_fraction"]) < 1e-14


def test_closed_surface_force_moment_and_virtual_work_are_independent(zero_data):
    _, payload, _, quadrature = zero_data
    # Deliberately unbalanced under nonzero pressure: only its load identities pass.
    state = _state(payload, 1, quadrature)
    assert state["pressure_resultant_norm"] < 1e-12
    assert abs(state["pressure_moment_z"]) < 1e-12
    assert state["virtual_work_relative_error"] < 2e-5
    assert state["equilibrium_status"] == "failed"
    assert not state["field_checks"]["current_external_force_recomputed"]


@pytest.mark.parametrize("transpose", [False, True])
def test_internal_n_by_three_force_maps_to_saved_node_major_flat_force(zero_data, transpose):
    _, payload, _, quadrature = zero_data
    force = _surface_pressure(payload, payload["displacements"][1], float(_LOADS[1]), quadrature)["force"]
    assert force.shape == payload["coordinates"].shape
    assert np.max(np.abs(force)) > 1e-4
    modified = dict(payload)
    modified["external_forces"] = payload["external_forces"].copy()
    modified["external_forces"][1] = (force.T if transpose else force).ravel()
    matches = _state(modified, 1, quadrature)["field_checks"]["current_external_force_recomputed"]
    assert matches == (not transpose)


def test_saved_n_by_three_external_force_is_rejected_instead_of_broadcast(zero_data):
    source, payload, history, _ = zero_data
    modified = dict(payload)
    modified["external_forces"] = payload["external_forces"].reshape(5, -1, 3)
    with pytest.raises(ValueError, match="external_forces"):
        verify_contour_case(modified, source, [1, 1, 2], history)


def test_height_average_area_is_not_assumed_to_equal_midplane(zero_data):
    _, payload, _, _ = zero_data
    grid = payload["coordinates"].reshape(9, 72, 3, 3)
    boundary = grid[0].copy()
    assert _area_average(boundary) == pytest.approx(q2_area(boundary[:, 1, :2]), rel=1e-13)
    boundary[:, 0, :2] *= 1.1
    assert abs(_area_average(boundary) - q2_area(boundary[:, 1, :2])) > 0.01


def test_saved_zero_residual_cannot_hide_unbalanced_positive_load_or_zero_area_response(zero_data):
    source, payload, history, _ = zero_data
    report = verify_contour_case(payload, source, [1, 1, 2], history)
    assert report["status"] == "failed"
    assert report["gates"]["history_initial_chain"] == "passed"
    assert report["gates"]["equilibrium"] == "failed"
    assert report["gates"]["monotone_cavity_response"] == "failed"


def test_saved_stress_corruption_is_not_hidden_by_a_zero_saved_residual(zero_data):
    _, payload, _, quadrature = zero_data
    corrupted = dict(payload)
    corrupted["P"] = payload["P"].copy()
    corrupted["P"][0, 0, 0, 0, 0] = 0.001
    assert not _state(corrupted, 0, quadrature)["field_checks"]["stress_recomputed"]


def test_uz_zero_alone_does_not_allow_unverified_in_plane_z_variation(zero_data):
    _, payload, _, quadrature = zero_data
    corrupted = dict(payload)
    corrupted["displacements"] = payload["displacements"].copy()
    corrupted["displacements"][0, :, 0] = 1e-4 * (payload["coordinates"][:, 2] - 0.25)
    state = _state(corrupted, 0, quadrature)
    assert not state["field_checks"]["plane_strain_in_plane_z_independence"]
    assert state["maximum_in_plane_z_variation"] > 1e-10


@pytest.mark.parametrize("change", ["nondecreasing", "negative_step", "no_backtrack_trial", "wrong_final_J", "saved_residual_mismatch"])
def test_history_corruption_fails_its_own_gate(zero_data, change):
    source, payload, original, _ = zero_data
    history = copy.deepcopy(original)
    history[1] = [{"iteration": 0, "normalized_free_residual": 0.01, "min_J": 1.0,
                   "step_length": 0.0, "line_search_trials": 0},
                  {"iteration": 1, "normalized_free_residual": 0.0, "min_J": 1.0,
                   "step_length": 1.0, "line_search_trials": 1}]
    if change == "nondecreasing":
        history[1][0]["normalized_free_residual"] = 0.0
    elif change == "negative_step":
        history[1][-1]["step_length"] = -0.1
    elif change == "no_backtrack_trial":
        history[1][-1]["line_search_trials"] = 0
    elif change == "wrong_final_J":
        history[1][-1]["min_J"] = 0.9
    else:
        history[1][-1]["normalized_free_residual"] = 1e-11
    assert verify_contour_case(payload, source, [1, 1, 2], history)["gates"]["history_initial_chain"] == "failed"


@pytest.mark.parametrize("field", ["loads", "initial_vectors", "displacements", "F"])
def test_partial_arrays_are_not_a_complete_five_state_run(zero_data, field):
    source, payload, history, _ = zero_data
    corrupted = dict(payload)
    corrupted[field] = payload[field][:-1]
    with pytest.raises(ValueError, match="partial"):
        verify_contour_case(corrupted, source, [1, 1, 2], history)


def test_initial_chain_must_use_saved_previous_u_and_p(zero_data):
    source, payload, history, _ = zero_data
    corrupted = dict(payload)
    corrupted["initial_vectors"] = payload["initial_vectors"].copy()
    corrupted["initial_vectors"][1, 1] = 0.001
    with pytest.raises(ValueError, match="initial state chain"):
        verify_contour_case(corrupted, source, [1, 1, 2], history)


@pytest.mark.parametrize("key,value", [("kappa", 100.0), ("loads", [0] * 5), ("cases", _CASES[:1])])
def test_scientific_configuration_drift_is_rejected(key, value):
    config = _configuration()
    config[key] = value
    with pytest.raises(ValueError, match="frozen scientific"):
        _check_configuration(config)


@pytest.mark.parametrize("field", list(_EVIDENCE_BOUNDARY) + ["solver"])
def test_evidence_boundary_and_solver_metadata_are_frozen(field):
    config = _configuration()
    _check_configuration(config)
    config[field] = "unapproved replacement"
    with pytest.raises(ValueError, match=field):
        _check_configuration(config)


@pytest.mark.parametrize("field", list(_GEOMETRY_BOUNDARY))
def test_image_provenance_and_constructed_anatomy_disclosures_are_frozen(field):
    config = _configuration()
    config["geometry"][field] = "measured real-heart anatomy"
    with pytest.raises(ValueError, match=field):
        _check_configuration(config)


@pytest.mark.parametrize("field", ["same_reference_domain_relative", "in_plane_z_variation",
                                  "midplane_average_area_relative", "zero_pressure_stress"])
def test_explicit_domain_and_plane_strain_thresholds_cannot_drift(field):
    config = _configuration()
    config["thresholds"][field] *= 10
    with pytest.raises(ValueError, match="thresholds"):
        _check_configuration(config)


def test_changing_expected_metadata_cannot_relax_a_judgment():
    config = _configuration()
    config["thresholds"]["stress_absolute"] = 1.0
    with pytest.raises(ValueError, match="thresholds"):
        _check_configuration(config)
    config = _configuration()
    config["geometry"]["frozen_preflight"]["minimum_orientation_cross"] = 1.0
    with pytest.raises(ValueError, match="frozen_preflight"):
        _check_configuration(config)


@pytest.mark.parametrize("save", [False, True])
def test_missing_package_is_native_failed_json_without_any_real_file_write(monkeypatch, save):
    written = []
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("in-memory fixture")))
    monkeypatch.setattr(Path, "write_text", lambda path, content, **kwargs: written.append(content))
    report = verify_fem_contour_pressure(Path.cwd() / "tmp" / "in_memory_contour_fixture", save=save)
    assert report["status"] == "failed"
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert len(written) == int(save)
