"""Independent F3-C rotation repair audit; does not invoke a mechanics solver.

The former independent verifier supplies only its independently implemented
basis and scalar-energy checks.  Existing F3-B evidence is hash-checked and read,
never rewritten or recomputed into a new scientific trajectory.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .fem_finite_strain import (
    _REQUIRED,
    _energy_derivative,
    _expected_boundary,
    _numpy_json_scalar,
    _quadrature,
    _stored_energy,
    verify_case,
)


_PARENT_SHA = "76167e61c4cdaf38011f6cd11ab4f329fa4d4439d9f3bf5a40dfc213acd79dc3"
_KINEMATICS_TOLERANCE = 1.0e-10
_STRESS_TOLERANCE = 2.0e-7
_MESH_FIELDS = ("coordinates", "cells", "pressure_coordinates", "pressure_cells")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as saved:
        arrays = {key: np.asarray(saved[key]) for key in saved.files}
    if any(not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)) for value in arrays.values()):
        raise ValueError("all raw arrays must be finite and numeric")
    return arrays


def _rotation(degrees: float) -> np.ndarray:
    angle = np.deg2rad(degrees)
    cosine, sine = np.cos(angle), np.sin(angle)
    return np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])


def _expected_case(case: dict[str, Any]) -> bool:
    fixed = {"kind": "rotation", "material": {"model": "neo_hookean", "mu": 1.0},
             "fiber": [1, 0, 0], "bulk": 1000.0, "subdivisions": [2, 2, 2],
             "lengths": [2.0, 1.0, 1.0], "phases": [0.0, 0.25, 0.5, 0.75, 1.0],
             "T_values": [0.0] * 5, "stretch_values": [1.0] * 5,
             "traction_values": [0.0] * 5, "rotation_degrees": [0.0, 15.0, 30.0, 45.0, 60.0],
             "rotation_center": [0.0, 0.0, 0.0]}
    return all(case.get(key) == value for key, value in fixed.items())


def _kinematics(vector: np.ndarray, mesh: dict[str, np.ndarray], quadrature: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    nodes, pressure_nodes = len(mesh["coordinates"]), len(mesh["pressure_coordinates"])
    if vector.shape != (3 * nodes + pressure_nodes,) or not np.all(np.isfinite(vector)):
        raise ValueError("mixed vector must concatenate u.ravel() followed by pressure DOFs")
    displacement = vector[:3 * nodes].reshape(nodes, 3)
    F = np.eye(3) + np.einsum("eai,eqaj->eqij", displacement[quadrature["cells"]], quadrature["gradients"])
    J = np.linalg.det(F)
    pressure = np.einsum("eqb,eb->eq", quadrature["pressure_basis"], vector[3 * nodes:][quadrature["pressure_cells"]])
    return displacement, F, J, pressure


def verify_rotation_states(payload: dict[str, np.ndarray], case: dict[str, Any]) -> dict[str, Any]:
    """Audit all five actual states and exact rigid-rotation displacement."""
    original = verify_case(payload, case)
    points = payload["coordinates"]
    exact = np.array([points @ _rotation(degrees).T - points for degrees in case["rotation_degrees"]])
    displacement_error = float(np.max(np.abs(payload["displacements"] - exact)))
    checks = {
        "frozen_rotation_case": _expected_case(case),
        "existing_independent_five_state_audit": original["status"] == "passed",
        "exact_rigid_displacement": displacement_error <= _KINEMATICS_TOLERANCE,
        "green_strain_zero": float(np.max(np.abs(payload["Green"]))) <= _KINEMATICS_TOLERANCE,
        "first_piola_stress_zero": float(np.max(np.abs(payload["P"]))) <= _STRESS_TOLERANCE,
        "cauchy_stress_zero": float(np.max(np.abs(payload["Cauchy"]))) <= _STRESS_TOLERANCE,
        "unit_jacobian": float(np.max(np.abs(payload["J"] - 1.0))) <= _KINEMATICS_TOLERANCE,
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "maximum_rigid_displacement_error": displacement_error,
            "maximum_abs_green": float(np.max(np.abs(payload["Green"]))),
            "maximum_abs_P": float(np.max(np.abs(payload["P"]))),
            "maximum_abs_cauchy": float(np.max(np.abs(payload["Cauchy"]))),
            "maximum_abs_J_minus_one": float(np.max(np.abs(payload["J"] - 1.0))),
            "independent_five_state_verification": original}


def verify_rotation_predictors(payload: dict[str, np.ndarray], states: dict[str, np.ndarray], case: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the harmonic increment weak residual without importing its solver."""
    quadrature = _quadrature(payload, case)
    for field in _MESH_FIELDS:
        if not np.array_equal(payload[field], states[field]):
            raise ValueError(f"predictor {field} differs from the five-state mesh")
    points = payload["coordinates"]
    nodes, size = len(points), 3 * len(points) + len(payload["pressure_coordinates"])
    for field in ("previous_vectors", "predicted_vectors", "boundary_only_vectors"):
        if payload[field].shape != (4, size):
            raise ValueError(f"{field} must contain precisely four mixed initial vectors")
    fixed, fixed_values, _ = _expected_boundary(states, case)
    if not np.array_equal(payload["fixed_dofs"], fixed) or payload["fixed_values"].shape != (4, len(fixed)):
        raise ValueError("predictor fixed DOFs or value shape differs from the boundary contract")
    free = np.ones(3 * nodes, dtype=bool)
    free[fixed] = False
    checks = {
        "four_angles_exact": np.array_equal(payload["angles"], [15.0, 30.0, 45.0, 60.0]),
        "fixed_values_match_registered_rotations": np.max(np.abs(payload["fixed_values"] - fixed_values[1:])) <= _KINEMATICS_TOLERANCE,
    }
    metrics = []
    for index in range(4):
        previous = payload["previous_vectors"][index]
        predicted = payload["predicted_vectors"][index]
        boundary_only = payload["boundary_only_vectors"][index]
        saved_previous = np.concatenate((states["displacements"][index].ravel(), states["pressure_dofs"][index]))
        expected_boundary_only = previous.copy()
        expected_boundary_only[fixed] = fixed_values[index + 1]
        _, _, previous_J, _ = _kinematics(previous, payload, quadrature)
        _, _, predicted_J, _ = _kinematics(predicted, payload, quadrature)
        _, _, boundary_J, _ = _kinematics(boundary_only, payload, quadrature)
        delta = (predicted[:3 * nodes] - previous[:3 * nodes]).reshape(nodes, 3)
        delta_gradient = np.einsum("eai,eqaj->eqij", delta[quadrature["cells"]], quadrature["gradients"])
        local_weak = np.einsum("eqij,eqaj,eq->eai", delta_gradient, quadrature["gradients"], quadrature["weights"])
        weak = np.zeros((nodes, 3))
        np.add.at(weak, quadrature["cells"].ravel(), local_weak.reshape(-1, 3))
        harmonic_residual = float(np.linalg.norm(weak.ravel()[free]))
        checks.update({
            f"step_{index + 1}_previous_is_actual_saved_state": np.array_equal(previous, saved_previous),
            f"step_{index + 1}_boundary_only_guess_reproduced": np.array_equal(boundary_only, expected_boundary_only),
            f"step_{index + 1}_predictor_boundary_exact": np.max(np.abs(predicted[fixed] - fixed_values[index + 1])) <= _KINEMATICS_TOLERANCE,
            f"step_{index + 1}_predictor_pressure_unchanged": np.array_equal(predicted[3 * nodes:], previous[3 * nodes:]),
            f"step_{index + 1}_harmonic_free_increment_residual": harmonic_residual <= _KINEMATICS_TOLERANCE,
            f"step_{index + 1}_positive_previous_and_predicted_J": bool(np.min(previous_J) > 0 and np.min(predicted_J) > 0),
        })
        metrics.append({"angle": float(payload["angles"][index]),
                        "harmonic_free_residual": harmonic_residual,
                        "previous_minimum_J": float(np.min(previous_J)),
                        "predicted_minimum_J": float(np.min(predicted_J)),
                        "boundary_only_minimum_J": float(np.min(boundary_J)),
                        "boundary_only_nonpositive_quadrature_count": int(np.sum(boundary_J <= 0))})
    checks["old_direct_boundary_injection_failure_reproduced"] = metrics[0]["boundary_only_nonpositive_quadrature_count"] > 0
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "increments": metrics,
            "old_direct_boundary_injection_failure_reproduced": metrics[0]["boundary_only_nonpositive_quadrature_count"] > 0,
            "boundary_only_guess_is_not_an_accepted_state": True}


def verify_perturbed_recovery(payload: dict[str, np.ndarray], states: dict[str, np.ndarray], configuration: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    case, perturbation = configuration["case"], configuration["perturbation"]
    expected_perturbation = {"amplitude": 0.002, "components": [1.0, -0.7, 0.5],
                             "definition": "product_sin_pi_X_over_L", "length_scale": 1.0,
                             "boundary_bubble_exactly_zero": True}
    if perturbation != expected_perturbation:
        raise ValueError("the registered deterministic perturbation changed")
    for field in _MESH_FIELDS:
        if not np.array_equal(payload[field], states[field]):
            raise ValueError(f"recovery {field} differs from the rotation mesh")
    quadrature = _quadrature(payload, case)
    points, lengths = payload["coordinates"], np.asarray(case["lengths"], dtype=float)
    nodes = len(points)
    initial, final = payload["initial_vector"], payload["final_vector"]
    initial_u, initial_F, initial_J, initial_pressure = _kinematics(initial, payload, quadrature)
    final_u, F, J, pressure = _kinematics(final, payload, quadrature)
    if np.any(J <= 0) or np.any(initial_J <= 0):
        raise ValueError("initial or recovered state has a nonpositive Jacobian")
    target_u = points @ _rotation(60.0).T - points
    last_vector = np.concatenate((states["displacements"][-1].ravel(), states["pressure_dofs"][-1]))
    bubble = np.prod(np.sin(np.pi * points / lengths), axis=1)
    boundary = np.any(np.isclose(points, 0.0, atol=1.0e-10, rtol=0) | np.isclose(points, lengths, atol=1.0e-10, rtol=0), axis=1)
    bubble[boundary] = 0.0
    delta = 0.002 * bubble[:, None] * np.asarray([1.0, -0.7, 0.5])
    expected_initial = last_vector.copy()
    expected_initial[:3 * nodes] += delta.ravel()
    fixed, prescribed, expected_external = _expected_boundary(states, case)
    free = np.ones(3 * nodes, dtype=bool)
    free[fixed] = False
    P = _energy_derivative(F, pressure, case["material"], np.asarray(case["fiber"], dtype=float), 0.0)
    green = (np.einsum("eqki,eqkj->eqij", F, F) - np.eye(3)) / 2.0
    cauchy = np.einsum("eqik,eqjk->eqij", P, F) / J[..., None, None]
    energy = _stored_energy(F, case["material"], np.asarray(case["fiber"], dtype=float), 0.0)
    local_force = np.einsum("eqij,eqaj,eq->eai", P, quadrature["gradients"], quadrature["weights"])
    force = np.zeros((nodes, 3))
    np.add.at(force, quadrature["cells"].ravel(), local_force.reshape(-1, 3))
    local_pressure_residual = np.einsum("eqb,eq,eq->eb", quadrature["pressure_basis"], J - 1.0 - pressure / case["bulk"], quadrature["weights"])
    pressure_residual = np.zeros(len(payload["pressure_coordinates"]))
    np.add.at(pressure_residual, quadrature["pressure_cells"].ravel(), local_pressure_residual.ravel())
    initial_P = _energy_derivative(initial_F, initial_pressure, case["material"], np.asarray(case["fiber"], dtype=float), 0.0)
    initial_force = np.zeros((nodes, 3))
    initial_local_force = np.einsum("eqij,eqaj,eq->eai", initial_P, quadrature["gradients"], quadrature["weights"])
    np.add.at(initial_force, quadrature["cells"].ravel(), initial_local_force.reshape(-1, 3))
    initial_pressure_weak = np.zeros(len(payload["pressure_coordinates"]))
    initial_local_pressure = np.einsum("eqb,eq,eq->eb", quadrature["pressure_basis"], initial_J - 1.0 - initial_pressure / case["bulk"], quadrature["weights"])
    np.add.at(initial_pressure_weak, quadrature["pressure_cells"].ravel(), initial_local_pressure.ravel())
    initial_combined_residual = float(np.linalg.norm(np.concatenate((initial_force.ravel()[free], initial_pressure_weak))))
    if not isinstance(history, list) or not history or any(not isinstance(item, dict) for item in history):
        raise ValueError("recovery Newton history must contain iteration records")
    residuals = np.asarray([item["normalized_free_residual"] for item in history], dtype=float)
    iterations = np.asarray([item["iteration"] for item in history], dtype=int)
    accepted_steps = sum(int(item.get("line_search_trials", 0) > 0 and item.get("step_length", 0.0) > 0) for item in history)
    saved_fields = {"F": F, "J": J, "Green": green, "P": P, "Cauchy": cauchy, "energy": energy}
    errors = {}
    for name, independent in saved_fields.items():
        if payload[name].shape != independent.shape:
            raise ValueError(f"recovery field {name} has an unexpected shape")
        errors[name] = float(np.max(np.abs(payload[name] - independent)))
    displacement_error = float(np.max(np.abs(final_u - target_u)))
    initial_difference = float(np.max(np.abs(initial_u - target_u)))
    free_residual = float(np.linalg.norm(force.ravel()[free]))
    pressure_weak = float(np.linalg.norm(pressure_residual))
    checks = {
        "initial_is_saved_60_degree_state_plus_registered_bubble": np.max(np.abs(initial - expected_initial)) <= _KINEMATICS_TOLERANCE,
        "nontrivial_interior_initial_perturbation": initial_difference > 1.0e-4,
        "initial_boundary_unperturbed": np.max(np.abs(initial_u[boundary] - target_u[boundary])) <= _KINEMATICS_TOLERANCE,
        "pressure_initial_unchanged": np.array_equal(initial[3 * nodes:], last_vector[3 * nodes:]),
        "fixed_dofs_match_boundary_contract": np.array_equal(payload["fixed_dofs"], fixed),
        "fixed_values_match_boundary_contract": payload["fixed_values"].shape == prescribed[-1].shape and np.max(np.abs(payload["fixed_values"] - prescribed[-1])) <= _KINEMATICS_TOLERANCE,
        "external_force_is_zero": payload["external_forces"].shape == expected_external[-1].shape and np.array_equal(payload["external_forces"], expected_external[-1]),
        "at_least_one_accepted_newton_update": accepted_steps >= 1 and int(iterations[-1]) >= 1,
        "newton_iteration_and_backtrack_limits_unchanged": int(iterations[-1]) <= 30 and all(0 <= int(item.get("line_search_trials", 0)) <= 16 for item in history),
        "newton_history_finite_and_positive_J": bool(np.all(np.isfinite(residuals)) and np.all(residuals >= 0) and all(float(item["min_J"]) > 0 for item in history)),
        "newton_history_iteration_sequence": np.array_equal(iterations, np.arange(len(iterations))),
        "newton_residual_decreases": bool(np.all(np.diff(residuals) < 0)),
        "initial_state_has_nonzero_independent_residual": initial_combined_residual > 1.0e-9,
        "initial_history_residual_independently_recomputed": abs(initial_combined_residual - float(residuals[0])) <= 2.0e-6,
        "final_newton_tolerance_unchanged": bool(0 <= float(payload["newton_residual"]) <= 1.0e-9 and residuals[-1] <= 1.0e-9),
        "final_history_matches_saved_newton_residual": abs(float(payload["newton_residual"]) - float(residuals[-1])) <= 1.0e-14,
        "exact_60_degree_displacement_recovered": displacement_error <= _KINEMATICS_TOLERANCE,
        "final_u_matches_unperturbed_60_degree_state": float(np.max(np.abs(final[:3 * nodes] - last_vector[:3 * nodes]))) <= _KINEMATICS_TOLERANCE,
        "final_p_matches_unperturbed_60_degree_state": float(np.max(np.abs(final[3 * nodes:] - last_vector[3 * nodes:]))) <= _STRESS_TOLERANCE,
        "saved_kinematics_independently_recomputed": max(errors[name] for name in ("F", "J", "Green")) <= _KINEMATICS_TOLERANCE,
        "saved_stress_independently_recomputed": max(errors[name] for name in ("P", "Cauchy")) <= _STRESS_TOLERANCE,
        "saved_energy_independently_recomputed": errors["energy"] <= _KINEMATICS_TOLERANCE,
        "zero_green_strain": float(np.max(np.abs(green))) <= _KINEMATICS_TOLERANCE,
        "zero_stress": max(float(np.max(np.abs(P))), float(np.max(np.abs(cauchy)))) <= _STRESS_TOLERANCE,
        "unit_jacobian": float(np.max(np.abs(J - 1.0))) <= _KINEMATICS_TOLERANCE,
        "independent_free_displacement_residual": free_residual <= 2.0e-6,
        "independent_pressure_weak_residual": pressure_weak <= 1.0e-8,
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "maximum_initial_displacement_error": initial_difference,
            "maximum_final_rigid_displacement_error": displacement_error,
            "initial_minimum_J": float(np.min(initial_J)), "final_minimum_J": float(np.min(J)),
            "maximum_abs_green": float(np.max(np.abs(green))),
            "maximum_abs_P": float(np.max(np.abs(P))), "maximum_abs_cauchy": float(np.max(np.abs(cauchy))),
            "maximum_abs_J_minus_one": float(np.max(np.abs(J - 1.0))),
            "accepted_newton_updates": accepted_steps, "newton_residuals": residuals.tolist(),
            "independent_initial_combined_residual": initial_combined_residual,
            "initial_history_residual_absolute_difference": abs(initial_combined_residual - float(residuals[0])),
            "maximum_final_vector_difference_from_unperturbed": float(np.max(np.abs(final - last_vector))),
            "maximum_final_u_difference_from_unperturbed": float(np.max(np.abs(final[:3 * nodes] - last_vector[:3 * nodes]))),
            "maximum_final_p_difference_from_unperturbed": float(np.max(np.abs(final[3 * nodes:] - last_vector[3 * nodes:]))),
            "independent_free_residual": free_residual, "independent_pressure_residual": pressure_weak,
            "saved_field_errors": errors}


def _parent_evidence(package: Path, configuration: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    parent = configuration["parent"]
    expected_path = "../f3b_finite_strain_v01_20260917"
    if (parent["path"] != expected_path or parent["path_base"] != "package"
            or parent["manifest_sha256"] != _PARENT_SHA or parent["expected_manifest_files"] != 62):
        raise ValueError("parent evidence does not match the frozen F3-B manifest")
    directory = (package / expected_path).resolve()
    if directory.parent != package.resolve().parent:
        raise ValueError("parent evidence escaped its allowed sibling directory")
    manifest_path = directory / "manifest.json"
    if _sha256(manifest_path) != _PARENT_SHA:
        raise ValueError("parent manifest SHA-256 differs from its frozen value")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    if len(files) != 62 or len({item["path"] for item in files}) != 62:
        raise ValueError("parent manifest must contain exactly 62 distinct files")
    mismatches = []
    for item in files:
        relative = Path(item["path"])
        target = (directory / relative).resolve()
        if relative.is_absolute() or not target.is_relative_to(directory):
            raise ValueError("parent manifest contains an escaping path")
        if not target.is_file() or target.stat().st_size != item["bytes"] or _sha256(target) != item["sha256"]:
            mismatches.append(item["path"])
    prior = json.loads((directory / "verification.json").read_text(encoding="utf-8"))
    expected_complete = {f"nh_stretch_{level}_k{bulk}" for bulk in (100, 1000) for level in ("coarse", "fine")}
    expected_complete.update({f"guccione_stretch_fiber_{axis}" for axis in ("x", "y")})
    expected_complete.update({"nh_active_k100", "nh_active_k1000", "guccione_active_k1000"})
    expected_complete.update({f"nh_bending_{level}_k{bulk}" for bulk in (100, 1000) for level in ("coarse", "fine")})
    prior_cases = prior["cases"]
    configuration_prior = json.loads((directory / "configuration.json").read_text(encoding="utf-8"))
    checks = {
        "all_62_manifest_entries_intact": not mismatches,
        "original_13_complete_cases_passed": set(prior_cases) == expected_complete | {"nh_rigid_rotation"} and all(prior_cases[name]["status"] == "passed" for name in expected_complete),
        "original_stage_failure_preserved": prior["status"] == "failed" and prior_cases["nh_rigid_rotation"]["status"] == "failed",
        "new_rotation_case_equals_original": configuration["case"] == configuration_prior["cases"]["nh_rigid_rotation"],
        "prior_material_mesh_bulk_gates_passed": all(prior["gates"][name] == "passed" for name in ("material_points", "mesh", "incompressibility")),
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "manifest_sha256": _PARENT_SHA, "verified_manifest_files": 62,
            "mismatched_paths": mismatches, "retained_complete_case_count": 13,
            "original_stage_status": prior["status"], "parent_report_rewritten": False}, directory


def verify_fem_rotation(path: Path | str, *, save: bool = False) -> dict[str, Any]:
    package = Path(path)
    configuration = json.loads((package / "configuration.json").read_text(encoding="utf-8"))
    sections = {}
    try:
        parent, parent_path = _parent_evidence(package, configuration)
        sections["parent_evidence"] = parent
        case = configuration["case"]
        if not _expected_case(case):
            raise ValueError("rotation case differs from the frozen material/geometry/angles")
        states = _load(package / "raw/rotation.npz")
        sections["rotation"] = verify_rotation_states(states, case)
        old_zero = _load(parent_path / "raw/nh_rigid_rotation.npz")
        static_fields = set(_MESH_FIELDS) | {"fixed_dofs"}
        zero_checks = {field: np.array_equal(states[field] if field in static_fields else states[field][:1], old_zero[field]) for field in _REQUIRED}
        sections["zero_state_provenance"] = {"status": "passed" if all(zero_checks.values()) else "failed", "fields_bitwise_equal": zero_checks}
        history = json.loads((package / "raw/rotation_newton.json").read_text(encoding="utf-8"))
        prior_history = json.loads((parent_path / "raw/nh_rigid_rotation_newton.json").read_text(encoding="utf-8"))
        history_checks = {"five_actual_history_lists": isinstance(history, list) and len(history) == 5,
                          "zero_degree_history_identical_to_prior": bool(history and history[0] == prior_history[0])}
        if len(history) == 5:
            history_checks["four_new_states_have_converged_history"] = all(bool(item) and float(item[-1]["normalized_free_residual"]) <= 1.0e-9 for item in history[1:])
        sections["rotation_history"] = {"status": "passed" if all(history_checks.values()) else "failed", "checks": history_checks}
        sections["predictors"] = verify_rotation_predictors(_load(package / "raw/rotation_initials.npz"), states, case)
        recovery_history = json.loads((package / "raw/perturbed_recovery_newton.json").read_text(encoding="utf-8"))
        sections["recovery"] = verify_perturbed_recovery(_load(package / "raw/perturbed_recovery.npz"), states, configuration, recovery_history)
    except (ValueError, KeyError, OSError, FloatingPointError, IndexError, TypeError) as error:
        sections["audit_error"] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    required = {"parent_evidence", "rotation", "zero_state_provenance", "rotation_history", "predictors", "recovery"}
    passed = required.issubset(sections) and all(section["status"] == "passed" for section in sections.values())
    answer = {"schema_version": "prl.fem_rotation_verification.v1", "status": "passed" if passed else "failed",
              "gates": {name: section["status"] for name, section in sections.items()}, **sections,
              "combined_qualification": {"status": "passed" if passed else "failed",
                                         "basis": "13 previously passed cases retained by hash plus repaired rotation and perturbed recovery",
                                         "parent_stage_status": "failed", "parent_report_rewritten": False,
                                         "does_not_relabel_historical_failure": True},
              "scientific_scope": "synthetic finite-strain block qualification only",
              "not_run": ["real_ventricle", "material_calibration", "physiologic_time", "follower_cavity_pressure", "blood_flow", "growth", "complete_Land_benchmark"]}
    serialized = json.dumps(answer, indent=2, allow_nan=False, default=_numpy_json_scalar)
    if save:
        (package / "verification.json").write_text(serialized + "\n", encoding="utf-8")
    return json.loads(serialized)
