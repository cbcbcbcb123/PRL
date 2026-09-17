"""Independent closed-form rotation fixtures; no mechanics solver is imported."""

import copy
import itertools
import json

import numpy as np
import pytest

from prl.verification.fem_finite_strain import _quadrature

from prl.verification.fem_rotation import (
    _expected_case,
    _rotation,
    verify_perturbed_recovery,
    verify_rotation_predictors,
    verify_rotation_states,
)


def _fixture():
    points = np.array(list(itertools.product(np.linspace(0, 2, 5), np.linspace(0, 1, 5), np.linspace(0, 1, 5))))
    pressure_points = np.array(list(itertools.product(np.linspace(0, 2, 3), np.linspace(0, 1, 3), np.linspace(0, 1, 3))))
    node_grid = np.arange(125).reshape(5, 5, 5)
    pressure_grid = np.arange(27).reshape(3, 3, 3)
    cells, pressure_cells = [], []
    for x, y, z in itertools.product(range(2), repeat=3):
        cells.append([node_grid[2*x+i, 2*y+j, 2*z+k] for i, j, k in itertools.product(range(3), repeat=3)])
        pressure_cells.append([pressure_grid[x+i, y+j, z+k] for i, j, k in itertools.product(range(2), repeat=3)])
    angles = [0.0, 15.0, 30.0, 45.0, 60.0]
    case = {"kind": "rotation", "material": {"model": "neo_hookean", "mu": 1.0},
            "fiber": [1, 0, 0], "bulk": 1000.0, "subdivisions": [2, 2, 2],
            "lengths": [2.0, 1.0, 1.0], "phases": [0.0, 0.25, 0.5, 0.75, 1.0],
            "T_values": [0.0] * 5, "stretch_values": [1.0] * 5,
            "traction_values": [0.0] * 5, "rotation_degrees": angles,
            "rotation_center": [0.0, 0.0, 0.0]}
    boundary = np.any((points == 0) | (points == [2, 1, 1]), axis=1)
    fixed = np.flatnonzero(np.repeat(boundary, 3))
    displacements = np.array([points @ _rotation(angle).T - points for angle in angles])
    F = np.array([np.broadcast_to(_rotation(angle), (8, 27, 3, 3)) for angle in angles])
    states = {"coordinates": points, "cells": np.asarray(cells), "pressure_coordinates": pressure_points,
              "pressure_cells": np.asarray(pressure_cells), "phases": np.asarray(case["phases"]),
              "activation": np.zeros(5), "prescribed_stretch": np.ones(5),
              "displacements": displacements, "pressure_dofs": np.zeros((5, 27)),
              "fixed_dofs": fixed, "fixed_values": displacements.reshape(5, -1)[:, fixed],
              "external_forces": np.zeros((5, 375)), "F": F,
              "P": np.zeros_like(F), "Cauchy": np.zeros_like(F), "Green": np.zeros_like(F),
              "J": np.ones((5, 8, 27)), "energy": np.zeros((5, 8, 27)),
              "newton_residual": np.zeros(5), "reaction": np.zeros((5, 375))}
    mesh = {name: states[name] for name in ("coordinates", "cells", "pressure_coordinates", "pressure_cells")}
    vectors = np.concatenate((displacements.reshape(5, -1), np.zeros((5, 27))), axis=1)
    direct = vectors[:-1].copy()
    direct[:, fixed] = states["fixed_values"][1:]
    predictors = {**mesh, "previous_vectors": vectors[:-1].copy(), "predicted_vectors": vectors[1:].copy(),
                  "boundary_only_vectors": direct, "angles": np.asarray(angles[1:]),
                  "fixed_dofs": fixed, "fixed_values": states["fixed_values"][1:]}
    perturbation = {"amplitude": 0.002, "components": [1.0, -0.7, 0.5],
                    "definition": "product_sin_pi_X_over_L", "length_scale": 1.0,
                    "boundary_bubble_exactly_zero": True}
    initial = vectors[-1].copy()
    bubble = np.prod(np.sin(np.pi * points / [2, 1, 1]), axis=1)
    bubble[boundary] = 0.0
    initial[:375] += (0.002 * bubble[:, None] * np.array([1.0, -0.7, 0.5])).ravel()
    recovery = {**mesh, "initial_vector": initial, "final_vector": vectors[-1].copy(),
                "fixed_dofs": fixed, "fixed_values": states["fixed_values"][-1],
                "external_forces": np.zeros(375), "newton_residual": np.asarray(0.0)}
    for name in ("F", "J", "Green", "P", "Cauchy", "energy"):
        recovery[name] = states[name][-1].copy()
    # Analytic NH stress supplies the initial residual fixture, without a solver.
    quadrature = _quadrature(states, case)
    gradient = quadrature["gradients"]
    weights = quadrature["weights"]
    initial_F = np.eye(3) + np.einsum("eai,eqaj->eqij", initial[:375].reshape(125, 3)[states["cells"]], gradient)
    initial_J = np.linalg.det(initial_F)
    invariant = np.sum(initial_F ** 2, axis=(-2, -1))
    analytic_P = initial_J[..., None, None] ** (-2.0 / 3.0) * (initial_F - invariant[..., None, None] / 3.0 * np.linalg.inv(initial_F).swapaxes(-1, -2))
    local_force = np.einsum("eqij,eqaj,eq->eai", analytic_P, gradient, weights)
    initial_force = np.zeros((125, 3))
    np.add.at(initial_force, states["cells"].ravel(), local_force.reshape(-1, 3))
    local_pressure = np.einsum("eqb,eq,eq->eb", quadrature["pressure_basis"], initial_J - 1.0, weights)
    initial_pressure = np.zeros(27)
    np.add.at(initial_pressure, states["pressure_cells"].ravel(), local_pressure.ravel())
    free = np.ones(375, dtype=bool)
    free[fixed] = False
    initial_residual = float(np.linalg.norm(np.concatenate((initial_force.ravel()[free], initial_pressure))))
    # These are synthetic metadata fixtures, not claims that a solver ran.
    history = [{"iteration": 0, "normalized_free_residual": initial_residual, "min_J": float(initial_J.min()),
                "step_length": 0.0, "line_search_trials": 0},
               {"iteration": 1, "normalized_free_residual": 0.0, "min_J": 1.0,
                "step_length": 1.0, "line_search_trials": 1}]
    return states, case, predictors, recovery, {"case": case, "perturbation": perturbation}, history


def test_all_five_exact_rigid_rotations_pass_independent_fields():
    states, case, *_ = _fixture()
    result = verify_rotation_states(states, case)
    assert result["status"] == "passed", result
    assert result["maximum_rigid_displacement_error"] == 0.0


def test_harmonic_predictors_have_free_zero_laplacian_and_old_guess_flips():
    states, case, predictors, *_ = _fixture()
    result = verify_rotation_predictors(predictors, states, case)
    assert result["status"] == "passed", result
    assert result["old_direct_boundary_injection_failure_reproduced"]
    assert result["increments"][0]["boundary_only_nonpositive_quadrature_count"] == 12
    assert max(item["harmonic_free_residual"] for item in result["increments"]) < 1.0e-12


def test_corrupt_interior_rotation_displacement_is_not_hidden_by_boundary():
    states, case, *_ = _fixture()
    states["displacements"][-1, 62, 0] += 0.001
    result = verify_rotation_states(states, case)
    assert result["status"] == "failed"
    assert not result["checks"]["exact_rigid_displacement"]


def test_altering_predictor_pressure_is_rejected():
    states, case, predictors, *_ = _fixture()
    predictors["predicted_vectors"][0, -1] = 0.002
    result = verify_rotation_predictors(predictors, states, case)
    assert result["status"] == "failed"
    assert not result["checks"]["step_1_predictor_pressure_unchanged"]


def test_old_boundary_only_failure_is_a_required_regression_check():
    states, case, predictors, *_ = _fixture()
    predictors["boundary_only_vectors"][0] = predictors["predicted_vectors"][0]
    result = verify_rotation_predictors(predictors, states, case)
    assert result["status"] == "failed"
    assert not result["checks"]["old_direct_boundary_injection_failure_reproduced"]


def test_arbitrary_interior_predictor_fails_independent_harmonic_equation():
    states, case, predictors, *_ = _fixture()
    predictors["predicted_vectors"][0, 3*62] += 0.002
    result = verify_rotation_predictors(predictors, states, case)
    assert result["status"] == "failed"
    assert not result["checks"]["step_1_harmonic_free_increment_residual"]


def test_recovery_checks_exact_final_against_registered_nontrivial_initial():
    states, _, _, recovery, config, history = _fixture()
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "passed", result
    assert result["maximum_initial_displacement_error"] > 1.0e-4
    assert result["accepted_newton_updates"] == 1


def test_recovery_cannot_substitute_unperturbed_initial_and_zero_iterations():
    states, _, _, recovery, config, history = _fixture()
    recovery["initial_vector"] = recovery["final_vector"].copy()
    history = [history[-1] | {"iteration": 0, "step_length": 0.0, "line_search_trials": 0}]
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "failed"
    assert not result["checks"]["nontrivial_interior_initial_perturbation"]
    assert not result["checks"]["at_least_one_accepted_newton_update"]


def test_recovery_saved_stress_tamper_is_rejected():
    states, _, _, recovery, config, history = _fixture()
    recovery["P"][0, 0, 0, 0] = 0.01
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "failed"
    assert not result["checks"]["saved_stress_independently_recomputed"]


def test_recovery_u_and_pressure_use_their_separate_frozen_tolerances():
    states, _, _, recovery, config, history = _fixture()
    recovery["final_vector"][375:] += 2.0e-8
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "passed", result
    assert result["maximum_final_vector_difference_from_unperturbed"] > 1.0e-10
    assert result["checks"]["final_p_matches_unperturbed_60_degree_state"]


def test_initial_history_residual_cannot_be_fabricated():
    states, _, _, recovery, config, history = _fixture()
    history[0]["normalized_free_residual"] += 0.1
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "failed"
    assert not result["checks"]["initial_history_residual_independently_recomputed"]


def test_final_saved_newton_residual_must_match_history():
    states, _, _, recovery, config, history = _fixture()
    recovery["newton_residual"] = np.asarray(1.0e-10)
    result = verify_perturbed_recovery(recovery, states, config, history)
    assert result["status"] == "failed"
    assert not result["checks"]["final_history_matches_saved_newton_residual"]


def test_missing_rotation_state_rejected():
    states, case, *_ = _fixture()
    states["displacements"] = states["displacements"][:-1]
    with pytest.raises(ValueError, match="displacements expected"):
        verify_rotation_states(states, case)


def test_case_drift_and_perturbation_amplitude_drift_rejected():
    states, case, _, recovery, config, history = _fixture()
    changed = copy.deepcopy(case)
    changed["rotation_degrees"][-1] = 59.0
    assert not _expected_case(changed)
    config["perturbation"]["amplitude"] = 0.0002
    with pytest.raises(ValueError, match="perturbation changed"):
        verify_perturbed_recovery(recovery, states, config, history)


@pytest.mark.parametrize("save", [False, True])
def test_incomplete_package_returns_json_native_failed_without_files(monkeypatch, save):
    import prl.verification.fem_rotation as verifier

    captured = {}

    class MemoryPath:
        def __init__(self, text):
            self.text = str(text)

        def __truediv__(self, other):
            return MemoryPath(self.text + "/" + str(other))

        def read_text(self, **_):
            return "{}"

        def write_text(self, text, **_):
            captured[self.text] = text
            return len(text)

    monkeypatch.setattr(verifier, "Path", MemoryPath)
    def missing_parent(*_):
        raise ValueError("missing frozen parent manifest")
    monkeypatch.setattr(verifier, "_parent_evidence", missing_parent)
    report = verifier.verify_fem_rotation("E:/Temp-Projects/PRL/in_memory_rotation_test", save=save)
    assert report["status"] == "failed"
    assert report["combined_qualification"]["parent_stage_status"] == "failed"
    assert json.loads(json.dumps(report)) == report
    assert bool(captured) == save
