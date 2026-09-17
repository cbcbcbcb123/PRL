"""Independent finite-strain qualification, rebuilt from saved Q2/Q1 states.

This module deliberately imports no FE assembler, constitutive implementation,
or runner.  Its stresses are numerical derivatives of a separately written
energy; shape functions are inferred from each saved structured cell's points.
The qualification is a synthetic block/beam test, not cardiac validation.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq, root


_FIELD_TOL = 1.0e-10
_STRESS_REL_TOL = 2.0e-6
_STRESS_ABS_TOL = 2.0e-7
_DISPLACEMENT_RESIDUAL_TOL = 2.0e-6
_PRESSURE_RESIDUAL_TOL = 1.0e-8
_ANALYTIC_TOL = 1.0e-6
_REQUIRED = (
    "coordinates", "cells", "pressure_coordinates", "pressure_cells", "phases",
    "activation", "prescribed_stretch", "displacements", "pressure_dofs",
    "fixed_dofs", "fixed_values", "external_forces", "F", "P", "Cauchy", "Green",
    "J", "energy", "newton_residual", "reaction",
)


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(actual - expected)) / (1.0 + np.max(np.abs(expected))))


def _stress_matches(actual: np.ndarray, expected: np.ndarray) -> bool:
    difference = float(np.max(np.abs(actual - expected)))
    scale = float(np.max(np.abs(expected)))
    return difference <= _STRESS_ABS_TOL + _STRESS_REL_TOL * scale


def _fiber_frame(fiber: np.ndarray) -> np.ndarray:
    if fiber.shape != (3,) or not np.all(np.isfinite(fiber)):
        raise ValueError("fiber must contain three finite reference components")
    if abs(np.linalg.norm(fiber) - 1.0) > _FIELD_TOL:
        raise ValueError("reference fiber must have unit length")
    coordinate_axis = np.eye(3)[int(np.argmin(np.abs(fiber)))]
    sheet = coordinate_axis - np.dot(coordinate_axis, fiber) * fiber
    sheet /= np.linalg.norm(sheet)
    return np.column_stack((fiber, sheet, np.cross(fiber, sheet)))


def _stored_energy(F: np.ndarray, material: dict[str, Any], fiber: np.ndarray,
                   tension: float) -> np.ndarray:
    """Separately implemented scalar W_iso + W_act; no pressure energy."""
    if not np.isfinite(tension) or tension < 0:
        raise ValueError("active tension must be finite and nonnegative")
    J = np.linalg.det(F)
    if np.any(J <= 0) or not np.all(np.isfinite(J)):
        raise ValueError("nonpositive or nonfinite deformation determinant")
    C = np.einsum("...ki,...kj->...ij", F, F)
    Cbar = J[..., None, None] ** (-2.0 / 3.0) * C
    model = material.get("model")
    if model == "neo_hookean":
        mu = float(material["mu"])
        if not np.isfinite(mu) or mu <= 0:
            raise ValueError("mu must be positive")
        passive = 0.5 * mu * (np.trace(Cbar, axis1=-2, axis2=-1) - 3.0)
    elif model == "guccione":
        values = [float(material[key]) for key in ("C", "bff", "bxx", "bfx")]
        if not np.all(np.isfinite(values)) or min(values) <= 0:
            raise ValueError("Guccione constants must be positive")
        coefficient, bff, bxx, bfx = values
        frame = _fiber_frame(fiber)
        Ebar = (Cbar - np.eye(3)) / 2.0
        local = np.einsum("ia,...ij,jb->...ab", frame, Ebar, frame)
        exponent = (bff * local[..., 0, 0] ** 2
                    + bxx * np.sum(local[..., 1:, 1:] ** 2, axis=(-2, -1))
                    + bfx * (np.sum(local[..., 0, 1:] ** 2, axis=-1)
                             + np.sum(local[..., 1:, 0] ** 2, axis=-1)))
        passive = 0.5 * coefficient * np.expm1(exponent)
    else:
        raise ValueError(f"unsupported material model: {model!r}")
    deformed_fiber = np.einsum("...ij,j->...i", F, fiber)
    return passive + 0.5 * tension * (np.sum(deformed_fiber ** 2, axis=-1) - 1.0)


def _energy_derivative(F: np.ndarray, pressure: np.ndarray,
                       material: dict[str, Any], fiber: np.ndarray,
                       tension: float) -> np.ndarray:
    """Five-point central energy derivative of W_iso + W_act + p(J-1)."""
    result = np.empty_like(F)
    for first in range(3):
        for second in range(3):
            step = 2.0e-5 * np.maximum(1.0, np.abs(F[..., first, second]))
            energies = []
            for multiple in (-2.0, -1.0, 1.0, 2.0):
                candidate = F.copy()
                candidate[..., first, second] += multiple * step
                energies.append(_stored_energy(candidate, material, fiber, tension)
                                + pressure * (np.linalg.det(candidate) - 1.0))
            result[..., first, second] = (energies[0] - 8.0 * energies[1]
                                         + 8.0 * energies[2] - energies[3]) / (12.0 * step)
    return result


def _lagrange_at(points: np.ndarray, nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Direct product definition, independent of the solver's basis tables."""
    basis = np.ones((len(points), len(nodes)))
    derivative = np.zeros_like(basis)
    for selected, node in enumerate(nodes):
        others = [index for index in range(len(nodes)) if index != selected]
        for other in others:
            basis[:, selected] *= (points - nodes[other]) / (node - nodes[other])
        for differentiated in others:
            term = np.full(len(points), 1.0 / (node - nodes[differentiated]))
            for other in others:
                if other != differentiated:
                    term *= (points - nodes[other]) / (node - nodes[other])
            derivative[:, selected] += term
    return basis, derivative


def _quadrature(payload: dict[str, np.ndarray], config: dict[str, Any]) -> dict[str, np.ndarray]:
    coordinates = payload["coordinates"]
    cells = payload["cells"].astype(np.int64)
    pressure_coordinates = payload["pressure_coordinates"]
    pressure_cells = payload["pressure_cells"].astype(np.int64)
    divisions = np.asarray(config["subdivisions"], dtype=int)
    lengths = np.asarray(config["lengths"], dtype=float)
    if divisions.shape != (3,) or np.any(divisions < 1) or lengths.shape != (3,) or np.any(lengths <= 0):
        raise ValueError("positive three-dimensional subdivisions and lengths are required")
    if not np.all(payload["cells"] == cells) or not np.all(payload["pressure_cells"] == pressure_cells):
        raise ValueError("connectivity must consist of integer indices")
    if coordinates.shape != (int(np.prod(2 * divisions + 1)), 3):
        raise ValueError("Q2 coordinate count disagrees with frozen subdivisions")
    if pressure_coordinates.shape != (int(np.prod(divisions + 1)), 3):
        raise ValueError("Q1 coordinate count disagrees with frozen subdivisions")
    elements = int(np.prod(divisions))
    if cells.shape != (elements, 27) or pressure_cells.shape != (elements, 8):
        raise ValueError("Q2/Q1 cell connectivity shape mismatch")
    if cells.min() < 0 or cells.max() >= len(coordinates) or pressure_cells.min() < 0 or pressure_cells.max() >= len(pressure_coordinates):
        raise ValueError("out-of-range cell connectivity")
    for points, lattice_divisions in ((coordinates, 2 * divisions), (pressure_coordinates, divisions)):
        integer_positions = points / lengths * lattice_divisions
        rounded = np.rint(integer_positions)
        if (np.max(np.abs(integer_positions - rounded)) > _FIELD_TOL
                or np.any(rounded < 0) or np.any(rounded > lattice_divisions)
                or len(np.unique(rounded, axis=0)) != len(points)):
            raise ValueError("coordinates are not the frozen complete structured lattice")
    abscissae = np.array([-np.sqrt(3.0 / 5.0), 0.0, np.sqrt(3.0 / 5.0)])
    one_weights = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0])
    quadrature_indices = np.array(list(itertools.product(range(3), repeat=3)))
    reference_points = abscissae[quadrature_indices]
    reference_weights = np.prod(one_weights[quadrature_indices], axis=1)
    basis_q2, gradient_q2 = [], []
    basis_q1 = []
    for axis in range(3):
        values, gradients = _lagrange_at(reference_points[:, axis], np.array([-1.0, 0.0, 1.0]))
        basis_q2.append(values)
        gradient_q2.append(gradients)
        basis_q1.append(_lagrange_at(reference_points[:, axis], np.array([-1.0, 1.0]))[0])
    all_gradients = np.zeros((elements, 27, 27, 3))
    all_pressure_basis = np.zeros((elements, 27, 8))
    all_weights = np.zeros((elements, 27))
    element_indices = []
    for index in range(elements):
        points = coordinates[cells[index]]
        low, high = points.min(axis=0), points.max(axis=0)
        widths = high - low
        if np.max(np.abs(widths - lengths / divisions)) > _FIELD_TOL:
            raise ValueError("element dimensions disagree with frozen structured mesh")
        element_indices.append(np.rint(low / lengths * divisions).astype(int))
        local = (points - low) / widths * 2.0 - 1.0
        local_integer = np.rint(local).astype(int)
        if np.max(np.abs(local - local_integer)) > _FIELD_TOL or len(np.unique(local_integer, axis=0)) != 27:
            raise ValueError("cell does not contain all 27 distinct Q2 tensor nodes")
        pressure_local = (pressure_coordinates[pressure_cells[index]] - low) / widths * 2.0 - 1.0
        if (np.max(np.abs(np.abs(pressure_local) - 1.0)) > _FIELD_TOL
                or len(np.unique(pressure_local, axis=0)) != 8):
            raise ValueError("pressure cell is not the corresponding eight Q1 corners")
        q2_indices = local_integer + 1
        q1_indices = np.rint((pressure_local + 1.0) / 2.0).astype(int)
        for node in range(27):
            for derivative_axis in range(3):
                value = np.ones(27)
                for axis in range(3):
                    table = gradient_q2[axis] if axis == derivative_axis else basis_q2[axis]
                    value *= table[:, q2_indices[node, axis]]
                all_gradients[index, :, node, derivative_axis] = value * 2.0 / widths[derivative_axis]
        for node in range(8):
            all_pressure_basis[index, :, node] = np.prod(
                [basis_q1[axis][:, q1_indices[node, axis]] for axis in range(3)], axis=0)
        all_weights[index] = reference_weights * np.prod(widths) / 8.0
    if len(np.unique(np.asarray(element_indices), axis=0)) != elements:
        raise ValueError("duplicate structured cells leave gaps in the domain")
    return {"gradients": all_gradients, "pressure_basis": all_pressure_basis,
            "weights": all_weights, "cells": cells, "pressure_cells": pressure_cells}


def _face_weights(payload: dict[str, np.ndarray], config: dict[str, Any]) -> np.ndarray:
    """Reference-area integral of each Q2 basis on the x=max face."""
    points = payload["coordinates"]
    lengths = np.asarray(config["lengths"], dtype=float)
    answer = np.zeros(len(points))
    one_integrals = np.array([1.0 / 3.0, 4.0 / 3.0, 1.0 / 3.0])
    for cell in payload["cells"].astype(int):
        local_points = points[cell]
        low, high = local_points.min(axis=0), local_points.max(axis=0)
        if abs(high[0] - lengths[0]) > _FIELD_TOL:
            continue
        widths = high - low
        for node in cell:
            if abs(points[node, 0] - lengths[0]) <= _FIELD_TOL:
                positions = np.rint((points[node, 1:] - low[1:]) / widths[1:] * 2.0).astype(int)
                answer[node] += np.prod(one_integrals[positions]) * np.prod(widths[1:]) / 4.0
    return answer


def _expected_boundary(payload: dict[str, np.ndarray], config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = payload["coordinates"]
    lengths = np.asarray(config["lengths"], dtype=float)
    states = len(payload["phases"])
    fixed_mask = np.zeros(points.shape, dtype=bool)
    values = np.zeros((states, len(points), 3))
    external = np.zeros_like(values)
    zero = np.isclose(points, 0.0, atol=_FIELD_TOL, rtol=0)
    top = np.isclose(points, lengths, atol=_FIELD_TOL, rtol=0)
    kind = config["kind"]
    if kind == "stretch":
        fixed_mask[:, 0] = zero[:, 0] | top[:, 0]
        fixed_mask[:, 1] = zero[:, 1]
        fixed_mask[:, 2] = zero[:, 2]
        values[:, top[:, 0], 0] = (np.asarray(config["stretch_values"])[:, None] - 1.0) * lengths[0]
    elif kind == "active":
        fixed_mask = zero
    elif kind == "bending":
        fixed_mask[zero[:, 0], :] = True
        external[:, :, 1] = np.asarray(config["traction_values"])[:, None] * _face_weights(payload, config)[None, :]
    elif kind == "rotation":
        fixed_mask[np.any(zero | top, axis=1), :] = True
        center = np.asarray(config.get("rotation_center", [0.0, 0.0, 0.0]), dtype=float)
        for state, degrees in enumerate(config["rotation_degrees"]):
            angle = np.deg2rad(degrees)
            cosine, sine = np.cos(angle), np.sin(angle)
            rotation = np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])
            values[state] = (points - center) @ rotation.T + center - points
    else:
        raise ValueError(f"unsupported boundary case {kind!r}")
    fixed = np.flatnonzero(fixed_mask.ravel())
    return fixed, values.reshape(states, -1)[:, fixed], external.reshape(states, -1)


def _nh_diagonal_reference(stretch: float, tension: float, bulk: float,
                           mu: float, active: bool) -> tuple[np.ndarray, float, float]:
    """Independent scalar force balance, not a discretized FE solution."""
    def diagonal_stress(axial: float, transverse: float) -> tuple[float, float, float]:
        determinant = axial * transverse ** 2
        invariant = axial ** 2 + 2.0 * transverse ** 2
        pressure = bulk * (determinant - 1.0)
        factor = mu * determinant ** (-2.0 / 3.0)
        first = factor * (axial - invariant / (3.0 * axial)) + pressure * determinant / axial + tension * axial
        second = factor * (transverse - invariant / (3.0 * transverse)) + pressure * determinant / transverse
        return first, second, pressure
    if active:
        guess = -np.log1p(tension / mu) / 3.0
        solved = root(lambda values: diagonal_stress(*np.exp(values))[:2], [guess, -guess / 2.0], tol=1.0e-12)
        if not solved.success and np.linalg.norm(solved.fun) > 1.0e-10:
            raise ValueError("independent NH active scalar equilibrium did not converge")
        axial, transverse = np.exp(solved.x)
    else:
        axial = stretch
        transverse = brentq(lambda value: diagonal_stress(axial, value)[1], 0.1, 3.0, xtol=1.0e-14)
    first, _, pressure = diagonal_stress(axial, transverse)
    return np.diag([axial, transverse, transverse]), pressure, first


def verify_case(payload: dict[str, np.ndarray], case_config: dict[str, Any]) -> dict[str, Any]:
    """Audit one complete case. Invalid schemas raise; numerical failures report failed."""
    arrays = {key: np.asarray(payload[key]) for key in _REQUIRED}
    if any(not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)) for value in arrays.values()):
        raise ValueError("all required raw fields must be finite numeric arrays")
    quadrature = _quadrature(arrays, case_config)
    cells, pressure_cells = quadrature["cells"], quadrature["pressure_cells"]
    states, elements = len(arrays["phases"]), len(cells)
    nodes, pressure_nodes = len(arrays["coordinates"]), len(arrays["pressure_coordinates"])
    expected_shapes = {
        "activation": (states,), "prescribed_stretch": (states,),
        "displacements": (states, nodes, 3), "pressure_dofs": (states, pressure_nodes),
        "external_forces": (states, 3 * nodes), "reaction": (states, 3 * nodes),
        "newton_residual": (states,), "F": (states, elements, 27, 3, 3),
        "P": (states, elements, 27, 3, 3), "Cauchy": (states, elements, 27, 3, 3),
        "Green": (states, elements, 27, 3, 3), "J": (states, elements, 27),
        "energy": (states, elements, 27),
    }
    for field, shape in expected_shapes.items():
        if arrays[field].shape != shape:
            raise ValueError(f"{field} expected {shape}, got {arrays[field].shape}")
    phases = np.asarray(case_config["phases"], dtype=float)
    tensions = np.asarray(case_config["T_values"], dtype=float)
    stretches = np.asarray(case_config["stretch_values"], dtype=float)
    if states < 5 or phases.shape != (states,) or tensions.shape != (states,) or stretches.shape != (states,):
        raise ValueError("all frozen actual phase states and input values must be present")
    if not np.all(np.isfinite(tensions)) or np.any(tensions < 0) or not np.all(np.isfinite(stretches)) or np.any(stretches <= 0):
        raise ValueError("invalid frozen tension or stretch values")
    material = case_config["material"]
    if "active_tension" in material:
        raise ValueError("active tension belongs in the frozen T_values, not passive material")
    fiber = np.asarray(case_config["fiber"], dtype=float)
    _fiber_frame(fiber)
    bulk = float(case_config["bulk"])
    if not np.isfinite(bulk) or bulk <= 0:
        raise ValueError("bulk modulus must be positive")
    fixed, prescribed, external = _expected_boundary(arrays, case_config)
    saved_fixed = arrays["fixed_dofs"].astype(int)
    if arrays["fixed_dofs"].ndim != 1 or not np.array_equal(saved_fixed, arrays["fixed_dofs"]):
        raise ValueError("fixed_dofs must be one-dimensional integer indices")
    if arrays["fixed_values"].shape != (states, len(saved_fixed)):
        raise ValueError("fixed_values shape mismatch")
    # Accept a permutation of the frozen DOF list, never a different set.
    fixed_order = np.argsort(saved_fixed)
    boundary_same = np.array_equal(saved_fixed[fixed_order], fixed)
    boundary_values_same = bool(boundary_same and _relative_error(arrays["fixed_values"][:, fixed_order], prescribed) <= _FIELD_TOL)
    free = np.ones(3 * nodes, dtype=bool)
    free[fixed] = False
    checks = {
        "all_requested_phases_present": bool(np.array_equal(arrays["phases"], phases)),
        "frozen_tensions_unchanged": bool(np.array_equal(arrays["activation"], tensions)),
        "frozen_prescribed_stretches_unchanged": bool(np.array_equal(arrays["prescribed_stretch"], stretches)),
        "boundary_dof_set_matches_contract": boundary_same,
        "prescribed_boundary_values_match_contract": boundary_values_same,
        "actual_boundary_values_match_contract": _relative_error(arrays["displacements"].reshape(states, -1)[:, fixed], prescribed) <= _FIELD_TOL,
        "external_dead_load_independently_rebuilt": _relative_error(arrays["external_forces"], external) <= _FIELD_TOL,
    }
    errors = {name: 0.0 for name in ("F", "J", "Green", "P", "Cauchy", "energy", "reaction")}
    displacement_residual, pressure_residual = [], []
    determinant_minima, volume_changes, maximum_local_volume_changes, mean_F, axial_reactions, tip_displacements = [], [], [], [], [], []
    energy_integrals, analytic_errors, analytic_reaction_errors, objectivity_errors = [], [], [], []
    analytic_F, analytic_pressure, analytic_stress = [], [], []
    gradients, q1_basis, weights = quadrature["gradients"], quadrature["pressure_basis"], quadrature["weights"]
    face_weights = _face_weights(arrays, case_config)
    fiber_rotation_angle = 0.713
    rotation = np.array([[np.cos(fiber_rotation_angle), -np.sin(fiber_rotation_angle), 0.0],
                         [np.sin(fiber_rotation_angle), np.cos(fiber_rotation_angle), 0.0], [0.0, 0.0, 1.0]])
    pure_rotation_ok = True
    for state in range(states):
        displacement = arrays["displacements"][state]
        F = np.eye(3) + np.einsum("eai,eqaj->eqij", displacement[cells], gradients)
        J = np.linalg.det(F)
        if np.any(J <= 0):
            raise ValueError("saved displacement produces a nonpositive quadrature determinant")
        pressure = np.einsum("eqb,eb->eq", q1_basis, arrays["pressure_dofs"][state][pressure_cells])
        P = _energy_derivative(F, pressure, material, fiber, tensions[state])
        green = (np.einsum("eqki,eqkj->eqij", F, F) - np.eye(3)) / 2.0
        cauchy = np.einsum("eqik,eqjk->eqij", P, F) / J[..., None, None]
        energy = _stored_energy(F, material, fiber, tensions[state])
        local_force = np.einsum("eqij,eqaj,eq->eai", P, gradients, weights)
        internal = np.zeros((nodes, 3))
        np.add.at(internal, cells.ravel(), local_force.reshape(-1, 3))
        residual = internal.ravel() - external[state]
        pressure_local = np.einsum("eqb,eq,eq->eb", q1_basis, J - 1.0 - pressure / bulk, weights)
        pressure_global = np.zeros(pressure_nodes)
        np.add.at(pressure_global, pressure_cells.ravel(), pressure_local.ravel())
        # Runner preserves the entire internal-minus-external vector.  Only
        # constrained entries are physical reactions; free entries are residuals.
        rebuilt_reaction = residual
        for field, rebuilt in (("F", F), ("J", J), ("Green", green), ("P", P),
                               ("Cauchy", cauchy), ("energy", energy), ("reaction", rebuilt_reaction)):
            errors[field] = max(errors[field], _relative_error(arrays[field][state], rebuilt))
        checks[f"state_{state}_stress_fields_match"] = bool(
            _stress_matches(arrays["P"][state], P) and _stress_matches(arrays["Cauchy"][state], cauchy))
        displacement_residual.append(float(np.linalg.norm(residual[free]) / (1.0 + np.linalg.norm(external[state]))))
        pressure_residual.append(float(np.linalg.norm(pressure_global)))
        determinant_minima.append(float(J.min()))
        volume_changes.append(float(np.sum(weights * (J - 1.0)) / np.sum(weights)))
        maximum_local_volume_changes.append(float(np.max(np.abs(J - 1.0))))
        mean_F.append(np.sum(weights[..., None, None] * F, axis=(0, 1)) / weights.sum())
        axial_reactions.append(float(np.sum(rebuilt_reaction.reshape(nodes, 3)[face_weights > 0, 0])))
        tip_displacements.append(float(np.dot(face_weights, displacement[:, 1]) / face_weights.sum()))
        energy_integrals.append(float(np.sum(weights * energy)))
        # Superpose a rotation on a nontrivial deformation, preserving reference fiber.
        rotated_F = np.einsum("ij,eqjk->eqik", rotation, F)
        rotated_energy = _stored_energy(rotated_F, material, fiber, tensions[state])
        rotated_P = _energy_derivative(rotated_F, pressure, material, fiber, tensions[state])
        objectivity_errors.append(max(_relative_error(rotated_energy, energy),
                                      _relative_error(rotated_P, np.einsum("ij,eqjk->eqik", rotation, P))))
        if case_config["kind"] == "rotation":
            pure_rotation_ok = bool(pure_rotation_ok and np.max(np.abs(green)) <= _FIELD_TOL
                                    and np.max(np.abs(P)) <= _STRESS_ABS_TOL)
        if material["model"] == "neo_hookean" and case_config["kind"] in ("stretch", "active"):
            reference_F, reference_pressure, reference_axial = _nh_diagonal_reference(
                stretches[state], tensions[state], bulk, float(material["mu"]), case_config["kind"] == "active")
            reference_u = arrays["coordinates"] @ (reference_F - np.eye(3)).T
            analytic_F.append(reference_F.tolist())
            analytic_pressure.append(float(reference_pressure))
            analytic_stress.append(float(reference_axial))
            analytic_errors.append(max(_relative_error(displacement, reference_u), _relative_error(F, reference_F),
                                       _relative_error(pressure, np.asarray(reference_pressure))))
            if case_config["kind"] == "stretch":
                face_area = float(np.prod(case_config["lengths"][1:]))
                analytic_reaction_errors.append(abs(axial_reactions[-1] - reference_axial * face_area)
                                                / (1.0 + abs(reference_axial * face_area)))
    checks.update({
        "kinematics_independently_recomputed": max(errors[name] for name in ("F", "J", "Green")) <= _FIELD_TOL,
        "passive_plus_active_energy_recomputed": errors["energy"] <= _FIELD_TOL,
        "full_internal_minus_external_vector_recomputed": errors["reaction"] <= _STRESS_REL_TOL,
        "positive_jacobian_all_states": min(determinant_minima) > 0,
        "independent_free_displacement_residual": max(displacement_residual) <= _DISPLACEMENT_RESIDUAL_TOL,
        "independent_pressure_weak_residual": max(pressure_residual) <= _PRESSURE_RESIDUAL_TOL,
        "saved_newton_residual_meets_contract": bool(np.all((arrays["newton_residual"] >= 0) & (arrays["newton_residual"] <= 1.0e-9))),
        "superposed_rotation_objectivity": max(objectivity_errors) <= 1.0e-8,
        "pure_rotation_zero_strain_stress": pure_rotation_ok,
        "nh_independent_scalar_equilibrium": max(analytic_errors, default=0.0) <= _ANALYTIC_TOL,
        "nh_independent_axial_reaction": max(analytic_reaction_errors, default=0.0) <= _ANALYTIC_TOL,
    })
    return {
        "status": "passed" if all(checks.values()) else "failed", "checks": checks,
        "errors": errors, "maximum_free_displacement_residual": max(displacement_residual),
        "maximum_pressure_weak_residual": max(pressure_residual),
        "maximum_nh_analytic_error": max(analytic_errors, default=0.0),
        "maximum_nh_reaction_error": max(analytic_reaction_errors, default=0.0),
        "maximum_objectivity_error": max(objectivity_errors),
        "cycle_return_diagnostic": {
            "applicable": case_config["kind"] == "active",
            "maximum_u_difference": float(np.max(np.abs(arrays["displacements"][-1] - arrays["displacements"][0]))),
            "maximum_pressure_difference": float(np.max(np.abs(arrays["pressure_dofs"][-1] - arrays["pressure_dofs"][0]))),
            "is_frozen_acceptance_gate": False,
        },
        "analytic_reference": {"status": "passed" if analytic_F else "not_run",
                               "F": analytic_F, "pressure": analytic_pressure,
                               "nominal_axial_stress": analytic_stress},
        "metrics": {"phases": phases.tolist(), "activation": tensions.tolist(),
                    "minimum_J": determinant_minima, "volume_change_fraction": volume_changes,
                    "maximum_local_absolute_volume_change": maximum_local_volume_changes,
                    "mean_F": np.asarray(mean_F).tolist(), "axial_reaction": axial_reactions,
                    "tip_mean_uy": tip_displacements, "stored_energy_integral": energy_integrals},
        "scope": "synthetic_three_dimensional_finite_strain_qualification_not_a_heart",
    }


def _verify_material_points(payload: dict[str, np.ndarray], configurations: list[dict[str, Any]]) -> dict[str, Any]:
    arrays = {key: np.asarray(payload[key]) for key in ("F", "energy", "P", "tangent", "J")}
    shapes = {"F": (4, 4, 3, 3), "energy": (4, 4), "P": (4, 4, 3, 3),
              "tangent": (4, 4, 3, 3, 3, 3), "J": (4, 4)}
    for name, shape in shapes.items():
        if arrays[name].shape != shape or not np.all(np.isfinite(arrays[name])):
            raise ValueError(f"invalid material point array {name}")
    if len(configurations) != 4:
        raise ValueError("all four frozen material/tension groups are required")
    angle = np.pi / 3.0
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0],
                         [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    base = np.array([[1.12, 0.09, 0.02], [0.03, 0.93, 0.04], [0.02, -0.01, 1.05]])
    frozen_F = np.array([np.eye(3), rotation, base, rotation @ base])
    groups = {}
    for index, configuration in enumerate(configurations):
        material = configuration["material"]
        tension = float(material["active_tension"])
        expected_model = "neo_hookean" if index < 2 else "guccione"
        expected_tension = float(2 * (index % 2))
        expected_material = ({"model": "neo_hookean", "mu": 1.0, "active_tension": expected_tension}
                             if index < 2 else {"model": "guccione", "C": 1.0, "bff": 8.0, "bxx": 2.0, "bfx": 4.0, "active_tension": expected_tension})
        if material != expected_material or configuration["name"] != f"{expected_model}_T{int(expected_tension)}":
            raise ValueError("material probe model, constants, group name, or tension changed")
        fiber = np.asarray(configuration["fiber"], dtype=float)
        _fiber_frame(fiber)
        if not np.array_equal(fiber, [1.0, 0.0, 0.0]):
            raise ValueError("material probe reference fiber changed")
        F = arrays["F"][index]
        energy = _stored_energy(F, material, fiber, tension)
        P = _energy_derivative(F, np.zeros(4), material, fiber, tension)
        tangent = np.empty((4, 3, 3, 3, 3))
        for first in range(3):
            for second in range(3):
                step = 1.0e-4
                positive, negative = F.copy(), F.copy()
                positive[:, first, second] += step
                negative[:, first, second] -= step
                tangent[..., first, second] = (
                    _energy_derivative(positive, np.zeros(4), material, fiber, tension)
                    - _energy_derivative(negative, np.zeros(4), material, fiber, tension)) / (2.0 * step)
        objective_energy = abs(energy[2] - energy[3]) / (1.0 + abs(energy[2]))
        objective_stress = _relative_error(P[3], rotation @ P[2])
        tangent_error = _relative_error(arrays["tangent"][index], tangent)
        zero_passive = tension != 0.0 or (np.max(np.abs(P[:2])) <= _STRESS_ABS_TOL
                                         and np.max(np.abs(energy[:2])) <= _FIELD_TOL)
        checks = {
            "frozen_four_gradients": _relative_error(F, frozen_F) <= _FIELD_TOL,
            "positive_and_recomputed_J": bool(np.all(arrays["J"][index] > 0) and _relative_error(arrays["J"][index], np.linalg.det(F)) <= _FIELD_TOL),
            "scalar_energy": _relative_error(arrays["energy"][index], energy) <= _FIELD_TOL,
            "stress_energy_derivative": _stress_matches(arrays["P"][index], P),
            "tangent_independent_difference": tangent_error <= 2.0e-5,
            "passive_zero_stress_at_identity_and_rotation": bool(zero_passive),
            "nontrivial_superposed_rotation_objectivity": max(objective_energy, objective_stress) <= 1.0e-8,
        }
        groups[configuration["name"]] = {"status": "passed" if all(checks.values()) else "failed",
                                          "checks": checks, "tangent_relative_error": tangent_error,
                                          "objectivity_relative_error": max(objective_energy, objective_stress)}
    return {"status": "passed" if all(group["status"] == "passed" for group in groups.values()) else "failed",
            "groups": groups}


def _frozen_matrix_matches(configurations: dict[str, Any]) -> bool:
    """Check case contents, not merely their count; never trust a smaller manifest."""
    expected = {}
    for bulk in (100, 1000):
        for level, mesh in (("coarse", [1, 1, 1]), ("fine", [2, 2, 2])):
            expected[f"nh_stretch_{level}_k{bulk}"] = ("stretch", "neo_hookean", mesh, bulk, [1, 0, 0])
    for direction, fiber in (("fiber_x", [1, 0, 0]), ("fiber_y", [0, 1, 0])):
        expected[f"guccione_stretch_{direction}"] = ("stretch", "guccione", [2, 2, 2], 1000, fiber)
    for bulk in (100, 1000):
        expected[f"nh_active_k{bulk}"] = ("active", "neo_hookean", [2, 2, 2], bulk, [1, 0, 0])
    expected["guccione_active_k1000"] = ("active", "guccione", [2, 2, 2], 1000, [1, 0, 0])
    for bulk in (100, 1000):
        for level, mesh in (("coarse", [2, 1, 1]), ("fine", [4, 2, 2])):
            expected[f"nh_bending_{level}_k{bulk}"] = ("bending", "neo_hookean", mesh, bulk, [1, 0, 0])
    expected["nh_rigid_rotation"] = ("rotation", "neo_hookean", [2, 2, 2], 1000, [1, 0, 0])
    if set(configurations) != set(expected):
        return False
    for name, (kind, model, mesh, bulk, fiber) in expected.items():
        actual = configurations[name]
        material = {"model": "neo_hookean", "mu": 1.0} if model == "neo_hookean" else {"model": "guccione", "C": 1.0, "bff": 8.0, "bxx": 2.0, "bfx": 4.0}
        if (actual["kind"] != kind or actual["material"] != material
                or actual["subdivisions"] != mesh or actual["bulk"] != bulk or actual["fiber"] != fiber
                or actual["lengths"] != [4.0 if kind == "bending" else 2.0, 1.0, 1.0]):
            return False
        phases = np.linspace(0.0, 1.0, 9 if kind == "active" else 5)
        arrays = {"phases": phases,
                  "T_values": 1.0 - np.cos(2.0 * np.pi * phases) if kind == "active" else np.zeros(len(phases)),
                  "stretch_values": 1.0 + 0.3 * phases if kind == "stretch" else np.ones(len(phases)),
                  "traction_values": 0.005 * phases if kind == "bending" else np.zeros(len(phases)),
                  "rotation_degrees": 60.0 * phases if kind == "rotation" else np.zeros(len(phases))}
        if any(np.asarray(actual[key]).shape != value.shape or np.max(np.abs(np.asarray(actual[key]) - value)) > 1.0e-14 for key, value in arrays.items()):
            return False
    return True


def _paired_gates(cases: dict[str, dict[str, Any]], configurations: dict[str, Any]) -> dict[str, Any]:
    comparisons: dict[str, dict[str, Any]] = {}
    def select(kind: str, bulk: float) -> list[str]:
        return [name for name, config in configurations.items()
                if config["kind"] == kind and config["material"]["model"] == "neo_hookean"
                and float(config["bulk"]) == bulk and name in cases and cases[name].get("metrics")]
    def relative(first: float, second: float) -> float:
        # Fine mesh / higher bulk is the reference, never a favorable denominator.
        return abs(first - second) / max(abs(second), 1.0e-12)
    for kind in ("stretch", "bending"):
        for bulk in (100.0, 1000.0):
            names = sorted(select(kind, bulk), key=lambda name: np.prod(configurations[name]["subdivisions"]))
            key = f"{kind}_mesh_bulk_{int(bulk)}"
            if len(names) != 2:
                comparisons[key] = {"status": "failed", "reason": "required coarse/fine pair unavailable"}
                continue
            low, high = [cases[name]["metrics"] for name in names]
            if kind == "stretch":
                reaction_difference = abs(low["axial_reaction"][-1] - high["axial_reaction"][-1]) / (1.0 + abs(high["axial_reaction"][-1]))
                stretch_difference = _relative_error(np.asarray(low["mean_F"][-1]), np.asarray(high["mean_F"][-1]))
                difference, limit = max(reaction_difference, stretch_difference), _ANALYTIC_TOL
            else:
                difference, limit = relative(low["tip_mean_uy"][-1], high["tip_mean_uy"][-1]), 0.05
            comparisons[key] = {"status": "passed" if difference <= limit else "failed",
                                "cases": names, "relative_difference": difference, "limit": limit}
    for kind in ("stretch", "active"):
        selected = []
        for bulk in (100.0, 1000.0):
            names = sorted(select(kind, bulk), key=lambda name: np.prod(configurations[name]["subdivisions"]))
            if names:
                selected.append(names[-1])
        key = f"{kind}_incompressibility"
        if len(selected) != 2:
            comparisons[key] = {"status": "failed", "reason": "required bulk sensitivity pair unavailable"}
            continue
        peak_index = -1 if kind == "stretch" else int(np.argmax(cases[selected[1]]["metrics"]["activation"]))
        deviations = [abs(cases[name]["metrics"]["volume_change_fraction"][peak_index]) for name in selected]
        maximum_local = cases[selected[1]]["metrics"]["maximum_local_absolute_volume_change"][peak_index]
        passed = deviations[1] < deviations[0] and maximum_local < 0.01
        comparisons[key] = {"status": "passed" if passed else "failed", "cases": selected,
                            "absolute_volume_change": deviations, "fine_bulk_maximum_local_volume_change": maximum_local,
                            "fine_bulk_limit": 0.01}
    names = []
    for bulk in (100.0, 1000.0):
        matching = sorted(select("bending", bulk), key=lambda name: np.prod(configurations[name]["subdivisions"]))
        if matching:
            names.append(matching[-1])
    if len(names) == 2:
        difference = relative(*(cases[name]["metrics"]["tip_mean_uy"][-1] for name in names))
        comparisons["beam_bulk_sensitivity"] = {"status": "passed" if difference <= 0.05 else "failed",
                                               "cases": names, "relative_difference": difference, "limit": 0.05}
    else:
        comparisons["beam_bulk_sensitivity"] = {"status": "failed", "reason": "required beam bulk pair unavailable"}
    return comparisons


def _numpy_json_scalar(value: Any) -> Any:
    """Convert NumPy scalars only; preserve the report's existing decisions."""
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported report value: {type(value).__name__}")


def verify_fem_finite_strain(path: Path | str, *, save: bool = False) -> dict[str, Any]:
    """Verify a complete frozen qualification package without running a solver."""
    package = Path(path)
    configuration = json.loads((package / "configuration.json").read_text(encoding="utf-8"))
    configurations = configuration["cases"]
    results = {}
    for name, case_config in configurations.items():
        raw_path = package / case_config.get("raw_path", f"raw/{name}.npz")
        if not raw_path.resolve().is_relative_to(package.resolve()):
            results[name] = {"status": "failed", "error": "raw path escapes result package"}
            continue
        try:
            with np.load(raw_path, allow_pickle=False) as saved:
                payload = {key: np.asarray(saved[key]) for key in _REQUIRED}
            results[name] = verify_case(payload, case_config)
        except (ValueError, KeyError, OSError, FloatingPointError) as error:
            results[name] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    paired = _paired_gates(results, configurations)
    nonengineering_checks = {"nh_independent_scalar_equilibrium", "nh_independent_axial_reaction",
                             "superposed_rotation_objectivity", "pure_rotation_zero_strain_stress"}
    engineering = bool(results) and all("checks" in result and all(value for key, value in result["checks"].items()
                                                                  if key not in nonengineering_checks) for result in results.values())
    complete_matrix = _frozen_matrix_matches(configurations)
    try:
        with np.load(package / "raw/material_points.npz", allow_pickle=False) as saved:
            material_points = _verify_material_points({key: np.asarray(saved[key]) for key in saved.files}, configuration["material_probes"])
    except (ValueError, KeyError, OSError, FloatingPointError) as error:
        material_points = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
    def case_check_group(check_names: tuple[str, ...]) -> str:
        passed = bool(results) and all("checks" in result and all(result["checks"].get(name, False) for name in check_names) for result in results.values())
        return "passed" if passed else "failed"
    gates = {
        "engineering": "passed" if engineering else "failed",
        "complete_frozen_case_matrix": "passed" if complete_matrix else "failed",
        "material_points": material_points["status"],
        "analytic": case_check_group(("nh_independent_scalar_equilibrium", "nh_independent_axial_reaction")),
        "objectivity": case_check_group(("superposed_rotation_objectivity", "pure_rotation_zero_strain_stress")),
        "mesh": "passed" if all(value["status"] == "passed" for key, value in paired.items() if "mesh" in key) else "failed",
        "incompressibility": "passed" if all(value["status"] == "passed" for key, value in paired.items() if "mesh" not in key) else "failed",
    }
    if "groups" not in material_points or not all(group["checks"]["nontrivial_superposed_rotation_objectivity"]
                                                  for group in material_points["groups"].values()):
        gates["objectivity"] = "failed"
    answer = {"schema_version": "prl.fem_finite_strain_verification.v1",
              "status": "passed" if all(value == "passed" for value in gates.values()) else "failed",
              "gates": gates, "cases": results, "paired_comparisons": paired, "material_points": material_points,
              "independence": "Q2/Q1 interpolation and energy finite differences rebuilt without solver/material/runner imports",
              "not_run": ["real_ventricle", "measured_material_calibration", "physiologic_time", "follower_cavity_pressure", "blood_flow", "complete_Land_benchmark"]}
    serialized = json.dumps(answer, indent=2, allow_nan=False, default=_numpy_json_scalar)
    if save:
        (package / "verification.json").write_text(serialized + "\n", encoding="utf-8")
    return json.loads(serialized)
