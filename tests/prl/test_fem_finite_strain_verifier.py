"""Closed-form fixtures: these tests do not import a FE solver or its material."""

import copy
import itertools
import json

import numpy as np
import pytest
from scipy.optimize import brentq

from prl.verification.fem_finite_strain import (
    _energy_derivative,
    _expected_boundary,
    _frozen_matrix_matches,
    _stored_energy,
    verify_case,
)


def _homogeneous_fixture():
    coordinates = np.array(list(itertools.product([0.0, 1.0, 2.0], [0.0, 0.5, 1.0], [0.0, 0.5, 1.0])))
    pressure_coordinates = np.array(list(itertools.product([0.0, 2.0], [0.0, 1.0], [0.0, 1.0])))
    phases = np.linspace(0.0, 1.0, 5)
    stretches = 1.0 + 0.3 * phases
    config = {"kind": "stretch", "material": {"model": "neo_hookean", "mu": 1.0},
              "bulk": 1000.0, "fiber": [1.0, 0.0, 0.0], "lengths": [2.0, 1.0, 1.0],
              "subdivisions": [1, 1, 1], "phases": phases.tolist(), "T_values": [0.0] * 5,
              "stretch_values": stretches.tolist(), "traction_values": [0.0] * 5,
              "rotation_degrees": [0.0] * 5}
    fixed_mask = coordinates == 0.0
    fixed_mask[:, 0] |= coordinates[:, 0] == 2.0
    fixed = np.flatnonzero(fixed_mask.ravel())
    payload = {"coordinates": coordinates, "cells": np.arange(27)[None],
               "pressure_coordinates": pressure_coordinates, "pressure_cells": np.arange(8)[None],
               "phases": phases, "activation": np.zeros(5), "prescribed_stretch": stretches,
               "fixed_dofs": fixed, "external_forces": np.zeros((5, 81)), "newton_residual": np.zeros(5)}
    records = {key: [] for key in ("displacements", "pressure_dofs", "fixed_values", "F", "P", "Cauchy", "Green", "J", "energy", "reaction")}
    for axial in stretches:
        def transverse_force(transverse):
            determinant = axial * transverse ** 2
            invariant = axial ** 2 + 2.0 * transverse ** 2
            return determinant ** (-2.0 / 3.0) * (transverse - invariant / (3.0 * transverse)) + 1000.0 * (determinant - 1.0) * determinant / transverse
        transverse = brentq(transverse_force, 0.5, 1.5, xtol=1.0e-14)
        F = np.diag([axial, transverse, transverse])
        determinant = np.linalg.det(F)
        invariant = float(np.sum(F ** 2))
        pressure = 1000.0 * (determinant - 1.0)
        P = determinant ** (-2.0 / 3.0) * (F - invariant / 3.0 * np.linalg.inv(F).T) + pressure * determinant * np.linalg.inv(F).T
        displacement = coordinates @ (F - np.eye(3)).T
        reaction = np.zeros_like(coordinates)
        simpson = np.array([1.0, 4.0, 1.0]) / 6.0
        # Exact surface tractions of the uniform analytical stress field.
        for node, point in enumerate(coordinates):
            for normal in range(3):
                if point[normal] not in (0.0, config["lengths"][normal]):
                    continue
                other_axes = [axis for axis in range(3) if axis != normal]
                factor = 1.0 if point[normal] > 0 else -1.0
                for axis in other_axes:
                    factor *= simpson[int(round(point[axis] / config["lengths"][axis] * 2.0))] * config["lengths"][axis]
                reaction[node] += factor * P[:, normal]
        records["displacements"].append(displacement)
        records["pressure_dofs"].append(np.full(8, pressure))
        records["fixed_values"].append(displacement.ravel()[fixed])
        for field, value in (("F", F), ("P", P), ("Cauchy", P @ F.T / determinant), ("Green", (F.T @ F - np.eye(3)) / 2.0)):
            records[field].append(np.broadcast_to(value, (1, 27, 3, 3)).copy())
        records["J"].append(np.full((1, 27), determinant))
        records["energy"].append(np.full((1, 27), 0.5 * (determinant ** (-2.0 / 3.0) * invariant - 3.0)))
        records["reaction"].append(reaction.ravel())
    payload.update({key: np.array(value) for key, value in records.items()})
    return payload, config


def test_closed_form_stretch_passes_all_independent_checks():
    payload, config = _homogeneous_fixture()
    result = verify_case(payload, config)
    assert result["status"] == "passed", result
    assert result["maximum_nh_analytic_error"] < 1.0e-9
    assert len(result["analytic_reference"]["F"]) == 5


def test_saved_displacement_tamper_rejected():
    payload, config = _homogeneous_fixture()
    payload["displacements"][-1, 13, 1] += 1.0e-3
    result = verify_case(payload, config)
    assert result["status"] == "failed"
    assert not result["checks"]["kinematics_independently_recomputed"]


def test_saved_stress_tamper_rejected():
    payload, config = _homogeneous_fixture()
    payload["P"][-1, 0, 0, 0, 0] += 0.03
    result = verify_case(payload, config)
    assert result["status"] == "failed"
    assert not result["checks"]["state_4_stress_fields_match"]


def test_saved_external_load_tamper_rejected():
    payload, config = _homogeneous_fixture()
    payload["external_forces"][-1, 40] = 0.01
    result = verify_case(payload, config)
    assert result["status"] == "failed"
    assert not result["checks"]["external_dead_load_independently_rebuilt"]


def test_missing_actual_state_cannot_be_reported_passed():
    payload, config = _homogeneous_fixture()
    for field in list(payload):
        if field not in ("coordinates", "cells", "pressure_coordinates", "pressure_cells", "fixed_dofs"):
            payload[field] = payload[field][:-1]
    with pytest.raises(ValueError, match="all frozen actual phase"):
        verify_case(payload, config)


def test_q2_local_connectivity_order_is_not_trusted():
    payload, config = _homogeneous_fixture()
    payload["cells"] = payload["cells"][:, ::-1]
    payload["pressure_cells"] = payload["pressure_cells"][:, ::-1]
    assert verify_case(payload, config)["status"] == "passed"


def test_duplicate_mesh_node_rejected():
    payload, config = _homogeneous_fixture()
    payload["coordinates"][13] = payload["coordinates"][12]
    with pytest.raises(ValueError, match="complete structured lattice"):
        verify_case(payload, config)


def test_pressure_dof_tamper_rejected():
    payload, config = _homogeneous_fixture()
    payload["pressure_dofs"][-1, 0] += 0.1
    result = verify_case(payload, config)
    assert result["status"] == "failed"
    assert not result["checks"]["independent_pressure_weak_residual"]


def test_nontrivial_rotation_and_active_stress_energy_identity():
    F = np.array([[[1.13, 0.07, 0.01], [0.02, 0.94, 0.03], [0.0, -0.01, 1.01]]])
    fiber = np.array([1.0, 0.0, 0.0])
    angle = 0.8
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    for material in ({"model": "neo_hookean", "mu": 1.0}, {"model": "guccione", "C": 1.0, "bff": 8.0, "bxx": 2.0, "bfx": 4.0}):
        P = _energy_derivative(F, np.zeros(1), material, fiber, 2.0)
        rotated = rotation @ F
        np.testing.assert_allclose(_stored_energy(rotated, material, fiber, 2.0), _stored_energy(F, material, fiber, 2.0), atol=1.0e-12)
        np.testing.assert_allclose(_energy_derivative(rotated, np.zeros(1), material, fiber, 2.0), rotation @ P, atol=1.0e-8)


def test_shortened_frozen_case_manifest_rejected():
    _, config = _homogeneous_fixture()
    assert not _frozen_matrix_matches({"nh_stretch_coarse_k1000": copy.deepcopy(config)})


def test_dead_traction_is_integrated_over_reference_face_not_equal_node_forces():
    payload, config = _homogeneous_fixture()
    config["kind"] = "bending"
    config["traction_values"] = np.linspace(0.0, 0.005, 5).tolist()
    _, _, external = _expected_boundary(payload, config)
    final_force = external[-1].reshape(-1, 3)
    np.testing.assert_allclose(final_force.sum(axis=0), [0.0, 0.005, 0.0], atol=1.0e-14)
    top = payload["coordinates"][:, 0] == 2.0
    assert np.all(final_force[~top] == 0.0)
    assert np.unique(final_force[top, 1]).size == 3


def test_normalized_newton_tolerance_is_not_rescaled_again():
    payload, config = _homogeneous_fixture()
    payload["newton_residual"][-1] = 1.01e-9
    result = verify_case(payload, config)
    assert result["status"] == "failed"
    assert not result["checks"]["saved_newton_residual_meets_contract"]


def test_illegal_material_and_tension_are_rejected():
    F = np.eye(3)[None]
    fiber = np.array([1.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="mu must be positive"):
        _stored_energy(F, {"model": "neo_hookean", "mu": -1.0}, fiber, 0.0)
    with pytest.raises(ValueError, match="nonnegative"):
        _stored_energy(F, {"model": "neo_hookean", "mu": 1.0}, fiber, -1.0)
    F[0, 0, 0] = -1.0
    with pytest.raises(ValueError, match="nonpositive"):
        _stored_energy(F, {"model": "neo_hookean", "mu": 1.0}, fiber, 0.0)


@pytest.mark.parametrize("save", [False, True])
def test_save_report_serializes_numpy_scalars_without_running_solver(monkeypatch, save):
    """Both public return and save are JSON native, with no real temp files."""
    import prl.verification.fem_finite_strain as verifier

    payload, config = _homogeneous_fixture()
    captured = {}

    class MemoryPath:
        def __init__(self, value):
            self.value = str(value)

        def __truediv__(self, component):
            return MemoryPath(self.value + "/" + str(component))

        def resolve(self):
            return self

        def is_relative_to(self, _):
            return True

        def read_text(self, **_):
            return json.dumps({"cases": {"one_case": config}, "material_probes": []})

        def write_text(self, text, **_):
            captured[self.value] = text
            return len(text)

    class MemoryArrays(dict):
        files = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(verifier, "Path", MemoryPath)
    monkeypatch.setattr(verifier.np, "load", lambda *args, **kwargs: MemoryArrays(payload))
    monkeypatch.setattr(verifier, "verify_case", lambda *args: {
        "status": "passed", "checks": {"some_check": np.bool_(True)},
        "diagnostic_scalar": np.float32(0.125),
    })
    monkeypatch.setattr(verifier, "_verify_material_points", lambda *args: {
        "status": "passed", "groups": {"probe": {
            "checks": {"nontrivial_superposed_rotation_objectivity": np.bool_(True)},
        }},
    })
    returned = verifier.verify_fem_finite_strain("E:/Temp-Projects/PRL/in_memory_test_only", save=save)
    report = json.loads(json.dumps(returned, allow_nan=False))  # Public CLI uses no custom encoder.
    if save:
        assert json.loads(next(iter(captured.values()))) == report
    else:
        assert not captured
    assert report["cases"]["one_case"]["checks"]["some_check"] is True
    assert report["cases"]["one_case"]["diagnostic_scalar"] == 0.125
    assert report["status"] == "failed"  # Serialization cannot upgrade an incomplete matrix.
