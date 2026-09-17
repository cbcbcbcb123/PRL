"""Independent geometry/closed-form fixtures: no scientific solver is run."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from prl.verification.fem_curved_pressure import (
    _CASES, _GEOMETRY, _LOADS, _RESOURCES, _check_configuration, _verify_state,
    curved_quadrature, cylinder_reference, follower_pressure,
    incompressible_radial_reference, verify_curved_case, verify_fem_curved_pressure,
)


def _configuration():
    return {"cases": copy.deepcopy(_CASES), "geometry": copy.deepcopy(_GEOMETRY),
            "material": {"model": "neo_hookean", "mu": 1.0}, "kappa": 1000.0,
            "loads": _LOADS.tolist(), "resources": copy.deepcopy(_RESOURCES),
            "scope": "quarter-cylinder plane-strain curved pressure qualification"}


def _zero_fixture():
    mesh = cylinder_reference([2, 4, 1])
    nodes, elements, pressures = len(mesh["coordinates"]), len(mesh["cells"]), len(mesh["pressure_coordinates"])
    F = np.broadcast_to(np.eye(3), (5, elements, 27, 3, 3)).copy()
    payload = {**mesh, "loads": _LOADS.copy(), "displacements": np.zeros((5, nodes, 3)),
               "pressure_dofs": np.zeros((5, pressures)), "fixed_values": np.zeros((5, len(mesh["fixed_dofs"]))),
               "external_forces": np.zeros((5, 3 * nodes)), "reaction": np.zeros((5, 3 * nodes)),
               "newton_residual": np.zeros(5), "F": F, "J": np.ones((5, elements, 27)),
               "Green": np.zeros_like(F), "P": np.zeros_like(F), "Cauchy": np.zeros_like(F),
               "energy": np.zeros((5, elements, 27))}
    # Deliberately fabricated histories are negative fixtures for nonzero loads.
    histories = [[{"iteration": 0, "normalized_free_residual": 0.0, "min_J": 1.0,
                   "step_length": 0.0, "line_search_trials": 0}] for _ in range(5)]
    return payload, histories


def test_curved_quadrature_reproduces_linear_physical_fields():
    mesh = cylinder_reference([2, 4, 1])
    quadrature = curved_quadrature(mesh, [2, 4, 1])
    assert np.max(np.abs(np.sum(quadrature["gradients"], axis=2))) < 1.0e-12
    identity = np.einsum("eai,eqaj->eqij", mesh["coordinates"][mesh["cells"]], quadrature["gradients"])
    assert np.max(np.abs(identity - np.eye(3))) < 1.0e-12
    assert quadrature["reference_volume_relative_error"] < 0.001
    assert np.min(quadrature["reference_determinants"]) > 0.0
    assert np.ptp(quadrature["reference_determinants"][0]) > 0.0


def test_finer_isoparametric_circular_geometry_reduces_volume_error():
    errors = [curved_quadrature(cylinder_reference(counts), counts)["reference_volume_relative_error"]
              for counts in ([2, 4, 1], [3, 8, 1])]
    assert 0.0 < errors[1] < errors[0] < 0.001


@pytest.mark.parametrize("field", ["coordinates", "cells", "pressure_coordinates", "inner_faces", "fixed_dofs"])
def test_geometry_and_boundary_metadata_corruption_is_rejected(field):
    mesh = cylinder_reference([2, 4, 1])
    mesh[field].flat[0] += 1
    with pytest.raises(ValueError, match="frozen|saved"):
        curved_quadrature(mesh, [2, 4, 1])


def test_pressure_uses_inward_solid_normal_and_current_area():
    mesh = cylinder_reference([2, 4, 1])
    quadrature = curved_quadrature(mesh, [2, 4, 1])
    zero = np.zeros_like(mesh["coordinates"])
    initial = follower_pressure(mesh, zero, 0.08, quadrature)
    # Integral of the radial area vector is exactly [A*H, A*H, 0].
    assert np.allclose(initial["resultant"], [0.04, 0.04, 0.0], atol=1.0e-14, rtol=0.0)
    scaled = follower_pressure(mesh, 0.1 * mesh["coordinates"], 0.08, quadrature)
    assert np.allclose(scaled["force"], 1.1**2 * initial["force"], atol=1.0e-14, rtol=0.0)
    assert scaled["current_area"] == pytest.approx(1.1**2 * initial["reference_area"], rel=1.0e-13)
    assert np.max(np.abs(scaled["force"] - initial["force"])) > 1.0e-4


def test_current_pressure_force_rotates_covariantly():
    mesh = cylinder_reference([2, 4, 1])
    quadrature = curved_quadrature(mesh, [2, 4, 1])
    angle = 0.35
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    original = follower_pressure(mesh, np.zeros_like(mesh["coordinates"]), 0.08, quadrature)
    rotated = follower_pressure(mesh, mesh["coordinates"] @ rotation.T - mesh["coordinates"], 0.08, quadrature)
    assert np.allclose(rotated["force"], original["force"] @ rotation.T, atol=1.0e-14, rtol=0.0)


def test_radial_mean_is_reference_surface_gauss_area_weighted():
    mesh = cylinder_reference([2, 4, 1])
    quadrature = curved_quadrature(mesh, [2, 4, 1])
    # Constant Cartesian shift gives the analytic quarter-cylinder projection.
    displacement = np.tile([0.01, 0.0, 0.0], (len(mesh["coordinates"]), 1))
    result = follower_pressure(mesh, displacement, 0.0, quadrature)
    assert result["inner_radial_displacement"] == pytest.approx(0.01 * 2.0 / np.pi, rel=0.001)


@pytest.mark.parametrize("pressure", [0.0, 0.02, 0.04, 0.06, 0.08])
def test_independent_integral_root_matches_closed_form_cylinder_formula(pressure):
    reference = incompressible_radial_reference(pressure)
    inner, outer = reference["inner_deformed_radius"], reference["outer_deformed_radius"]
    shift = inner**2 - 1.0
    closed_form = np.log(1.25 * inner / outer) + shift / 2.0 * (1.0 / inner**2 - 1.0 / outer**2)
    assert abs(closed_form - pressure) < 2.0e-14
    assert abs(reference["reintegrated_pressure"] - pressure) < 2.0e-14
    assert abs(outer**2 - inner**2 - (1.25**2 - 1.0)) < 1.0e-14


@pytest.mark.parametrize("pressure", [-0.01, np.nan, 0.23])
def test_analytic_reference_rejects_invalid_or_nonexistent_finite_inflation_branch(pressure):
    with pytest.raises(ValueError):
        incompressible_radial_reference(pressure)


def test_undeformed_zero_pressure_state_passes_independent_fields_and_equilibrium():
    payload, _ = _zero_fixture()
    state = _verify_state(payload, 0, curved_quadrature(payload, [2, 4, 1]))
    assert state["fields_status"] == "passed", state
    assert state["equilibrium_status"] == "passed", state
    assert state["analytic_status"] == "passed"


def test_reported_zero_residual_cannot_hide_unequilibrated_positive_pressure():
    payload, histories = _zero_fixture()
    case = verify_curved_case(payload, [2, 4, 1], histories)
    assert case["status"] == "failed"
    assert case["gates"]["complete_history"] == "passed"
    assert case["gates"]["equilibrium"] == "failed"
    assert case["gates"]["fields"] == "failed"
    assert case["gates"]["analytic"] == "failed"
    assert case["states"][0]["fields_status"] == "passed"


def test_saved_stress_corruption_is_rejected_even_when_saved_residual_is_zero():
    payload, _ = _zero_fixture()
    payload["P"][0, 0, 0, 0, 0] = 1.0e-3
    state = _verify_state(payload, 0, curved_quadrature(payload, [2, 4, 1]))
    assert state["fields_status"] == "failed"
    assert not state["field_checks"]["stress_independently_recomputed"]


def test_mixed_pressure_and_nh_stress_are_recomputed_from_u_and_p():
    payload, _ = _zero_fixture()
    deformation = np.diag([1.04, 1.02, 1.0])
    jacobian = np.linalg.det(deformation)
    invariant = np.sum(deformation**2)
    pressure = 0.2
    stress = jacobian**(-2.0 / 3.0) * (deformation - invariant / 3.0 * np.linalg.inv(deformation).T)
    stress += pressure * jacobian * np.linalg.inv(deformation).T
    payload["displacements"][1] = payload["coordinates"] @ deformation.T - payload["coordinates"]
    payload["pressure_dofs"][1] = pressure
    payload["F"][1] = deformation
    payload["J"][1] = jacobian
    payload["Green"][1] = (deformation.T @ deformation - np.eye(3)) / 2.0
    payload["P"][1] = stress
    payload["Cauchy"][1] = stress @ deformation.T / jacobian
    payload["energy"][1] = 0.5 * (jacobian**(-2.0 / 3.0) * invariant - 3.0)
    state = _verify_state(payload, 1, curved_quadrature(payload, [2, 4, 1]))
    assert state["field_checks"]["kinematics_independently_recomputed"]
    assert state["field_checks"]["stress_independently_recomputed"]
    assert state["equilibrium_status"] == "failed"


@pytest.mark.parametrize("field", ["loads", "displacements", "J", "newton_residual"])
def test_partial_state_arrays_are_not_complete_qualification(field):
    payload, histories = _zero_fixture()
    payload[field] = payload[field][:-1]
    with pytest.raises(ValueError, match="partial"):
        verify_curved_case(payload, [2, 4, 1], histories)


def test_corrupt_load_and_optional_gauss_pressure_are_rejected():
    payload, histories = _zero_fixture()
    payload["loads"][1] += 0.001
    with pytest.raises(ValueError, match="pressure ramp"):
        verify_curved_case(payload, [2, 4, 1], histories)
    payload["loads"] = _LOADS.copy()
    payload["pressure_gauss"] = np.ones_like(payload["J"])
    state = _verify_state(payload, 0, curved_quadrature(payload, [2, 4, 1]))
    assert not state["field_checks"]["saved_pressure_gauss_recomputed"]


@pytest.mark.parametrize("change", ["increased_residual", "negative_step", "oversized_step", "missing_trial", "fractional_trial", "nonfinite_J", "wrong_final_J", "history_mismatch"])
def test_invalid_newton_history_cannot_pass_complete_history_gate(change):
    payload, histories = _zero_fixture()
    histories[1] = [{"iteration": 0, "normalized_free_residual": 0.01, "min_J": 1.0,
                     "step_length": 0.0, "line_search_trials": 0},
                    {"iteration": 1, "normalized_free_residual": 0.0, "min_J": 1.0,
                     "step_length": 1.0, "line_search_trials": 1}]
    last = histories[1][-1]
    if change == "increased_residual":
        histories[1][0]["normalized_free_residual"] = 0.0
    elif change == "negative_step":
        last["step_length"] = -0.1
    elif change == "oversized_step":
        last["step_length"] = 1.1
    elif change == "missing_trial":
        last["line_search_trials"] = 0
    elif change == "fractional_trial":
        last["line_search_trials"] = 1.5
    elif change == "nonfinite_J":
        last["min_J"] = np.nan
    elif change == "wrong_final_J":
        last["min_J"] = 1.1
    else:
        payload["newton_residual"][1] = 1.0e-11
    result = verify_curved_case(payload, [2, 4, 1], histories)
    assert result["gates"]["complete_history"] == "failed"


@pytest.mark.parametrize("field", ["displacements", "J"])
def test_complex_raw_field_is_not_a_real_mechanical_state(field):
    payload, histories = _zero_fixture()
    payload[field] = payload[field].astype(complex)
    with pytest.raises(ValueError, match="raw field"):
        verify_curved_case(payload, [2, 4, 1], histories)


def test_initial_vectors_must_be_zero_then_the_preceding_retained_state():
    payload, histories = _zero_fixture()
    payload["initial_vectors"] = np.zeros((5, 3 * len(payload["coordinates"]) + len(payload["pressure_coordinates"])))
    case = verify_curved_case(payload, [2, 4, 1], histories)
    assert case["initial_vectors_provenance"] == "passed"
    payload["initial_vectors"][1, 0] = 0.001
    with pytest.raises(ValueError, match="initial vectors"):
        verify_curved_case(payload, [2, 4, 1], histories)


def test_partial_initial_vectors_are_rejected():
    payload, histories = _zero_fixture()
    payload["initial_vectors"] = np.zeros((4, 3 * len(payload["coordinates"]) + len(payload["pressure_coordinates"])))
    with pytest.raises(ValueError, match="initial_vectors"):
        verify_curved_case(payload, [2, 4, 1], histories)


@pytest.mark.parametrize("key,value", [("kappa", 100.0), ("material", {"model": "neo_hookean", "mu": 2.0}),
                                      ("loads", [0.0] * 5), ("cases", [{"name": "coarse", "counts": [2, 4, 1]}])])
def test_frozen_scientific_configuration_drift_is_rejected(key, value):
    config = _configuration()
    config[key] = value
    with pytest.raises(ValueError, match="frozen scientific"):
        _check_configuration(config)


def test_prose_metadata_does_not_supply_mechanics_answers():
    config = _configuration()
    config.update({"element": "display prose", "expected_status": "passed", "units": "uncalibrated"})
    _check_configuration(config)
    payload, histories = _zero_fixture()
    assert verify_curved_case(payload, [2, 4, 1], histories)["status"] == "failed"


@pytest.mark.parametrize("save", [False, True])
def test_missing_package_returns_native_failed_json_without_solver_or_files(monkeypatch, save):
    written = []
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("in-memory missing fixture")))
    monkeypatch.setattr(Path, "write_text", lambda path, content, **kwargs: written.append((path, content)))
    report = verify_fem_curved_pressure(Path.cwd() / "tmp" / "in_memory_f4_verifier_fixture", save=save)
    assert report["status"] == "failed"
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert len(written) == int(save)
    if save:
        assert json.loads(written[0][1]) == report
