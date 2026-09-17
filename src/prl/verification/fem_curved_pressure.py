"""Independent curved Q2/Q1 pressure qualification from retained raw states.

No solver, production constitutive law, or runner is imported. Reference
geometry and current-surface forces are rebuilt here; NH stress is obtained
from the separate verification energy by numerical differentiation. The
analytical comparison is an incompressible infinite plane-strain cylinder,
not an exact finite-kappa or biological reference.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq

from .fem_finite_strain import (
    _energy_derivative, _lagrange_at, _numpy_json_scalar, _stored_energy,
)


_GEOMETRY = {"inner_radius": 1.0, "outer_radius": 1.25,
             "angle": float(np.pi / 2.0), "height": 0.5}
_LOADS = np.array([0.0, 0.02, 0.04, 0.06, 0.08])
_CASES = [{"name": "coarse", "counts": [2, 4, 1]},
          {"name": "fine", "counts": [3, 8, 1]}]
_RESOURCES = {"threads": 1, "gpu": 0, "dcm": 0, "seconds": 600,
              "stage_bytes": 33554432, "reserve_bytes": 67108864,
              "automatic_retries": 0}
_PARENTS = (
    ("f3b_finite_strain_v01_20260917", 62,
     "76167e61c4cdaf38011f6cd11ab4f329fa4d4439d9f3bf5a40dfc213acd79dc3"),
    ("f3c_rotation_repair_v01_20260917", 38,
     "705f478f81818e5cc26de499a21ca8596372e816a8b773330293f070373ebf73"),
)
_MESH_FIELDS = ("coordinates", "cells", "pressure_coordinates", "pressure_cells")


def _check_configuration(configuration: dict[str, Any]) -> None:
    expected = {"cases": _CASES, "geometry": _GEOMETRY,
                "material": {"model": "neo_hookean", "mu": 1.0},
                "kappa": 1000.0, "loads": _LOADS.tolist(),
                "scope": "quarter-cylinder plane-strain curved pressure qualification",
                "resources": _RESOURCES}
    for name, value in expected.items():
        if configuration.get(name) != value:
            raise ValueError(f"frozen scientific configuration changed: {name}")
    # Prose metadata is not evidence and never supplies a mechanics threshold.


def cylinder_reference(counts: list[int] | tuple[int, int, int]) -> dict[str, np.ndarray]:
    """Frozen analytic node locations and z-fast connectivity, without a mesher."""
    divisions = np.asarray(counts, dtype=int)
    if divisions.shape != (3,) or np.any(divisions <= 0) or not np.array_equal(divisions, counts):
        raise ValueError("counts must contain three positive integers")
    A, B, angle, height = (_GEOMETRY[key] for key in ("inner_radius", "outer_radius", "angle", "height"))
    grids, coordinates = [], []
    for order in (2, 1):
        widths = order * divisions + 1
        parametric = np.array(list(itertools.product(
            np.linspace(A, B, widths[0]), np.linspace(0.0, angle, widths[1]),
            np.linspace(0.0, height, widths[2]))))
        points = np.column_stack((parametric[:, 0] * np.cos(parametric[:, 1]),
                                  parametric[:, 0] * np.sin(parametric[:, 1]),
                                  parametric[:, 2]))
        coordinates.append(points)
        grids.append(np.arange(len(points)).reshape(tuple(widths)))
    cells, pressure_cells, faces = [], [], []
    for element, index in enumerate(itertools.product(*(range(value) for value in divisions))):
        for order, grid, collection in ((2, grids[0], cells), (1, grids[1], pressure_cells)):
            collection.append([grid[tuple(order * np.asarray(index) + offset)]
                               for offset in itertools.product(range(order + 1), repeat=3)])
        if index[0] == 0:
            faces.append((element, 0, -1))
    points = coordinates[0]
    fixed = np.zeros_like(points, dtype=bool)
    fixed[:, 2] = True
    fixed[np.isclose(points[:, 1], 0.0, atol=1.0e-12, rtol=0.0), 1] = True
    fixed[np.isclose(points[:, 0], 0.0, atol=1.0e-12, rtol=0.0), 0] = True
    return {"coordinates": points, "cells": np.asarray(cells, dtype=int),
            "pressure_coordinates": coordinates[1], "pressure_cells": np.asarray(pressure_cells, dtype=int),
            "inner_faces": np.asarray(faces, dtype=int), "fixed_dofs": np.flatnonzero(fixed.ravel())}


def _tensor_basis(points: np.ndarray, order: int) -> tuple[np.ndarray, np.ndarray]:
    positions = np.linspace(-1.0, 1.0, order + 1)
    tables = [_lagrange_at(points[:, axis], positions) for axis in range(3)]
    indices = list(itertools.product(range(order + 1), repeat=3))
    values = np.zeros((len(points), len(indices)))
    gradients = np.zeros((len(points), len(indices), 3))
    for node, index in enumerate(indices):
        values[:, node] = np.prod([tables[axis][0][:, index[axis]] for axis in range(3)], axis=0)
        for derivative_axis in range(3):
            gradients[:, node, derivative_axis] = np.prod([
                tables[axis][int(axis == derivative_axis)][:, index[axis]] for axis in range(3)], axis=0)
    return values, gradients


def curved_quadrature(payload: dict[str, np.ndarray], counts: list[int]) -> dict[str, Any]:
    expected = cylinder_reference(counts)
    for field in (*_MESH_FIELDS, "inner_faces", "fixed_dofs"):
        if field not in payload or payload[field].shape != expected[field].shape:
            raise ValueError(f"missing or incorrect shape for frozen geometry field {field}")
        if "coordinates" in field:
            matches = payload[field].dtype.kind in "iuf" and np.all(np.isfinite(payload[field])) and np.max(np.abs(payload[field] - expected[field])) <= 1.0e-12
        else:
            matches = payload[field].dtype.kind in "iu" and np.array_equal(payload[field], expected[field])
        if not matches:
            raise ValueError(f"saved {field} differs from frozen curved geometry/boundaries")
    points, cells = payload["coordinates"], expected["cells"]
    abscissae = np.array([-np.sqrt(3.0 / 5.0), 0.0, np.sqrt(3.0 / 5.0)])
    weights = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0])
    indices = np.array(list(itertools.product(range(3), repeat=3)))
    sites = abscissae[indices]
    basis, reference_gradients = _tensor_basis(sites, 2)
    pressure_basis = _tensor_basis(sites, 1)[0]
    jacobian = np.einsum("eai,qaj->eqij", points[cells], reference_gradients)
    determinants = np.linalg.det(jacobian)
    if not np.all(np.isfinite(determinants)) or np.any(determinants <= 0.0):
        raise ValueError("nonpositive or nonfinite reference isoparametric Jacobian")
    gradients = np.einsum("qaj,eqji->eqai", reference_gradients, np.linalg.inv(jacobian))
    volume_weights = determinants * np.prod(weights[indices], axis=1)[None, :]
    face_indices = np.array(list(itertools.product(range(3), repeat=2)))
    face_sites = np.column_stack((-np.ones(9), abscissae[face_indices]))
    face_basis, face_derivatives = _tensor_basis(face_sites, 2)
    analytic_volume = 0.5 * (_GEOMETRY["outer_radius"] ** 2 - _GEOMETRY["inner_radius"] ** 2) * _GEOMETRY["angle"] * _GEOMETRY["height"]
    return {"cells": cells, "pressure_cells": expected["pressure_cells"],
            "basis": basis, "pressure_basis": pressure_basis, "gradients": gradients,
            "weights": volume_weights, "reference_jacobians": jacobian,
            "reference_determinants": determinants, "face_basis": face_basis,
            "face_derivatives": face_derivatives,
            "face_weights": np.prod(weights[face_indices], axis=1),
            "inner_faces": expected["inner_faces"],
            "reference_volume": float(np.sum(volume_weights)), "analytic_reference_volume": analytic_volume,
            "reference_volume_relative_error": abs(float(np.sum(volume_weights)) / analytic_volume - 1.0)}


def follower_pressure(payload: dict[str, np.ndarray], displacement: np.ndarray,
                      pressure: float, quadrature: dict[str, Any]) -> dict[str, Any]:
    """Pressure acts opposite the solid's inner outward normal, using current area."""
    points = payload["coordinates"]
    if displacement.shape != points.shape or not np.all(np.isfinite(displacement)) or not np.isfinite(pressure):
        raise ValueError("invalid displacement/pressure for follower-surface integration")
    faces = quadrature["inner_faces"][:, 0]
    face_cells = quadrature["cells"][faces]
    reference = points[face_cells]
    current = (points + displacement)[face_cells]
    derivative = quadrature["face_derivatives"]
    reference_tangents = np.einsum("fai,qaj->fqij", reference, derivative)
    current_tangents = np.einsum("fai,qaj->fqij", current, derivative)
    # r/theta/z ordering: d x / d eta cross d x / d zeta points +radial.
    reference_cross = np.cross(reference_tangents[..., 1], reference_tangents[..., 2])
    current_cross = np.cross(current_tangents[..., 1], current_tangents[..., 2])
    reference_measure = np.linalg.norm(reference_cross, axis=-1)
    current_measure = np.linalg.norm(current_cross, axis=-1)
    if np.any(reference_measure <= 0) or np.any(current_measure <= 0):
        raise ValueError("degenerate reference/current pressure surface")
    basis, weights = quadrature["face_basis"], quadrature["face_weights"]
    local_forces = pressure * np.einsum("qa,fqi,q->fai", basis, current_cross, weights)
    force = np.zeros_like(points)
    np.add.at(force, face_cells.ravel(), local_forces.reshape(-1, 3))
    reference_sites = np.einsum("qa,fai->fqi", basis, reference)
    site_displacements = np.einsum("qa,fai->fqi", basis, displacement[face_cells])
    radial = reference_sites.copy()
    radial[..., 2] = 0.0
    radial /= np.linalg.norm(radial, axis=-1)[..., None]
    reference_area_weights = reference_measure * weights[None, :]
    mean_radial = np.sum(np.sum(site_displacements * radial, axis=-1) * reference_area_weights) / np.sum(reference_area_weights)
    return {"force": force, "inner_radial_displacement": float(mean_radial),
            "reference_area": float(np.sum(reference_area_weights)),
            "current_area": float(np.sum(current_measure * weights)),
            "minimum_current_area_density": float(np.min(current_measure)),
            "resultant": np.sum(force, axis=0)}


def incompressible_radial_reference(pressure: float) -> dict[str, float]:
    """Integrate radial equilibrium in reference R and solve for inner radius a.

    r^2=R^2+a^2-A^2, lambda_z=1, lambda_theta=r/R,
    lambda_r=R/r. With zero outer radial traction,
    p=mu*integral_A^B [1/R - R^3/(R^2+a^2-A^2)^2] dR.
    """
    A, B, mu = 1.0, 1.25, 1.0
    if not np.isfinite(pressure) or pressure < 0 or pressure >= mu * np.log(B / A):
        raise ValueError("pressure lies outside the finite inflation branch of this reference")
    sites, weights = np.polynomial.legendre.leggauss(64)
    radii = A + (sites + 1.0) * (B - A) / 2.0
    def load(inner: float) -> float:
        shift = inner * inner - A * A
        integrand = 1.0 / radii - radii ** 3 / (radii ** 2 + shift) ** 2
        return float(mu * np.dot(weights, integrand) * (B - A) / 2.0)
    if pressure == 0.0:
        inner = A
    else:
        upper = 2.0 * A
        while load(upper) < pressure:
            upper *= 2.0
        inner = float(brentq(lambda value: load(value) - pressure, A, upper, xtol=5.0e-15, rtol=1.0e-14))
    return {"pressure": float(pressure), "inner_radial_displacement": inner - A,
            "inner_deformed_radius": inner, "outer_deformed_radius": float(np.sqrt(B * B + inner * inner - A * A)),
            "reintegrated_pressure": load(inner)}


def _verify_state(payload: dict[str, np.ndarray], index: int, quadrature: dict[str, Any]) -> dict[str, Any]:
    points, cells = payload["coordinates"], quadrature["cells"]
    displacement = payload["displacements"][index]
    pressure = np.einsum("qb,eb->eq", quadrature["pressure_basis"], payload["pressure_dofs"][index][quadrature["pressure_cells"]])
    F = np.eye(3) + np.einsum("eai,eqaj->eqij", displacement[cells], quadrature["gradients"])
    J = np.linalg.det(F)
    if np.any(J <= 0) or not np.all(np.isfinite(F)):
        raise ValueError("saved displacement gives nonpositive/nonfinite deformation Jacobian")
    material, fiber = {"model": "neo_hookean", "mu": 1.0}, np.array([1.0, 0.0, 0.0])
    P = _energy_derivative(F, pressure, material, fiber, 0.0)
    green = (np.einsum("eqki,eqkj->eqij", F, F) - np.eye(3)) / 2.0
    cauchy = np.einsum("eqik,eqjk->eqij", P, F) / J[..., None, None]
    energy = _stored_energy(F, material, fiber, 0.0)
    errors = {name: float(np.max(np.abs(payload[name][index] - value)))
              for name, value in {"F": F, "J": J, "P": P, "Cauchy": cauchy, "Green": green, "energy": energy}.items()}
    surface = follower_pressure(payload, displacement, float(_LOADS[index]), quadrature)
    external = surface["force"].ravel()
    local_force = np.einsum("eqij,eqaj,eq->eai", P, quadrature["gradients"], quadrature["weights"])
    internal = np.zeros_like(points)
    np.add.at(internal, cells.ravel(), local_force.reshape(-1, 3))
    residual = internal.ravel() - external
    local_pressure = np.einsum("qb,eq,eq->eb", quadrature["pressure_basis"], J - 1.0 - pressure / 1000.0, quadrature["weights"])
    pressure_residual = np.zeros(len(payload["pressure_coordinates"]))
    np.add.at(pressure_residual, quadrature["pressure_cells"].ravel(), local_pressure.ravel())
    free = np.ones(3 * len(points), dtype=bool)
    free[payload["fixed_dofs"].astype(int)] = False
    displacement_residual = float(np.linalg.norm(residual[free]))
    pressure_norm = float(np.linalg.norm(pressure_residual))
    combined = float(np.linalg.norm(np.concatenate((residual[free], pressure_residual))) / (1.0 + np.linalg.norm(external)))
    field_checks = {"kinematics_independently_recomputed": max(errors[name] for name in ("F", "J", "Green", "energy")) <= 1.0e-10,
                    "stress_independently_recomputed": max(errors[name] for name in ("P", "Cauchy")) <= 2.0e-7,
                    "current_surface_force_independently_recomputed": float(np.max(np.abs(payload["external_forces"][index] - external))) <= 1.0e-10,
                    "reaction_independently_recomputed": float(np.max(np.abs(payload["reaction"][index] - residual))) <= 2.0e-6,
                    "fixed_values_zero": bool(np.all(payload["fixed_values"][index] == 0.0)),
                    "prescribed_dofs_and_plane_strain_satisfied": float(np.max(np.abs(displacement.ravel()[~free]))) <= 1.0e-10}
    if "pressure_gauss" in payload:
        field_checks["saved_pressure_gauss_recomputed"] = float(np.max(np.abs(payload["pressure_gauss"][index] - pressure))) <= 1.0e-10
    if index == 0:
        field_checks["zero_load_reference_state"] = max(float(np.max(np.abs(displacement))), float(np.max(np.abs(payload["pressure_dofs"][index])))) <= 1.0e-10
        field_checks["zero_load_stress"] = max(float(np.max(np.abs(P))), float(np.max(np.abs(cauchy)))) <= 2.0e-7
    equilibrium_checks = {"independent_free_force_residual": displacement_residual <= 2.0e-6,
                          "independent_pressure_weak_residual": pressure_norm <= 1.0e-8,
                          "saved_newton_residual": 0.0 <= float(payload["newton_residual"][index]) <= 1.0e-9}
    reference = incompressible_radial_reference(float(_LOADS[index]))
    radial = surface["inner_radial_displacement"]
    analytic_error = abs(radial / reference["inner_radial_displacement"] - 1.0) if index else abs(radial)
    return {"load": float(_LOADS[index]), "fields_status": "passed" if all(field_checks.values()) else "failed",
            "equilibrium_status": "passed" if all(equilibrium_checks.values()) else "failed",
            "field_checks": field_checks, "equilibrium_checks": equilibrium_checks,
            "saved_field_errors": errors, "minimum_J": float(np.min(J)),
            "maximum_abs_J_minus_one": float(np.max(np.abs(J - 1.0))),
            "independent_free_residual": displacement_residual, "independent_pressure_residual": pressure_norm,
            "independent_normalized_combined_residual": combined,
            "inner_radial_displacement": radial, "analytic_relative_error": analytic_error,
            "analytic_status": "passed" if analytic_error <= (0.05 if index else 1.0e-10) else "failed",
            "reference_inner_area": surface["reference_area"], "current_inner_area": surface["current_area"],
            "current_pressure_resultant": surface["resultant"].tolist(),
            "maximum_saved_external_force_error": float(np.max(np.abs(payload["external_forces"][index] - external)))}


def verify_curved_case(payload: dict[str, np.ndarray], counts: list[int], history: list[Any]) -> dict[str, Any]:
    quadrature = curved_quadrature(payload, counts)
    nodes, elements, pressures = len(payload["coordinates"]), len(payload["cells"]), len(payload["pressure_coordinates"])
    shapes = {"loads": (5,), "displacements": (5, nodes, 3), "pressure_dofs": (5, pressures),
              "fixed_values": (5, len(payload["fixed_dofs"])), "external_forces": (5, 3 * nodes),
              "reaction": (5, 3 * nodes), "J": (5, elements, 27), "energy": (5, elements, 27),
              "newton_residual": (5,)}
    shapes.update({name: (5, elements, 27, 3, 3) for name in ("F", "P", "Cauchy", "Green")})
    if "pressure_gauss" in payload:
        shapes["pressure_gauss"] = (5, elements, 27)
    if "initial_vectors" in payload:
        shapes["initial_vectors"] = (5, 3 * nodes + pressures)
    for name, shape in shapes.items():
        if (name not in payload or payload[name].shape != shape or payload[name].dtype.kind not in "iuf"
                or not np.all(np.isfinite(payload[name]))):
            raise ValueError(f"missing, partial or nonfinite raw field: {name}")
    if not np.array_equal(payload["loads"], _LOADS):
        raise ValueError("saved pressure ramp differs from the frozen five loads")
    if "initial_vectors" in payload:
        previous = np.concatenate((payload["displacements"][:-1].reshape(4, -1), payload["pressure_dofs"][:-1]), axis=1)
        expected_initials = np.vstack((np.zeros((1, 3 * nodes + pressures)), previous))
        if not np.array_equal(payload["initial_vectors"], expected_initials):
            raise ValueError("initial vectors are not zero followed by the preceding saved equilibria")
    if not isinstance(history, list) or len(history) != 5:
        raise ValueError("five complete Newton history lists are required")
    history_checks = []
    for index, records in enumerate(history):
        if not isinstance(records, list) or not records:
            raise ValueError("empty or invalid Newton history")
        residuals = np.asarray([entry["normalized_free_residual"] for entry in records], dtype=float)
        iterations = np.asarray([entry["iteration"] for entry in records])
        history_checks.append(bool(np.all(np.isfinite(residuals)) and np.all(residuals >= 0)
            and np.array_equal(iterations, np.arange(len(records))) and iterations[-1] <= 30
            and np.all(np.diff(residuals) < 0.0)
            and residuals[-1] <= 1.0e-9 and abs(float(residuals[-1]) - float(payload["newton_residual"][index])) <= 1.0e-14
            and abs(float(records[-1]["min_J"]) - float(np.min(payload["J"][index]))) <= 1.0e-10
            and all(float(entry["min_J"]) > 0 and np.isfinite(float(entry["min_J"]))
                    for entry in records)
            and float(records[0]["step_length"]) == 0.0 and int(records[0]["line_search_trials"]) == 0
            and all(np.isfinite(float(entry["step_length"])) and 0.0 < float(entry["step_length"]) <= 1.0
                    and 1 <= int(entry["line_search_trials"]) <= 16
                    and int(entry["line_search_trials"]) == entry["line_search_trials"] for entry in records[1:])))
    states = [_verify_state(payload, index, quadrature) for index in range(5)]
    geometry = {"status": "passed" if quadrature["reference_volume_relative_error"] <= 0.001 else "failed",
                "minimum_reference_determinant": float(np.min(quadrature["reference_determinants"])),
                "reference_volume": quadrature["reference_volume"],
                "analytic_reference_volume": quadrature["analytic_reference_volume"],
                "relative_volume_error": quadrature["reference_volume_relative_error"],
                "frozen_nodes_connectivity_faces_and_constraints": True}
    gates = {"geometry": geometry["status"], "complete_history": "passed" if all(history_checks) else "failed"}
    gates.update({name: "passed" if all(state[f"{name}_status"] == "passed" for state in states) else "failed"
                  for name in ("fields", "equilibrium", "analytic")})
    return {"status": "passed" if all(value == "passed" for value in gates.values()) else "failed",
            "gates": gates, "geometry": geometry, "states": states,
            "newton_histories_passed": history_checks,
            "initial_vectors_provenance": "passed" if "initial_vectors" in payload else "not_run",
            "radial_metric_definition": "reference-inner-area weighted u dot er_ref at isoparametric surface Gauss points"}


def _protected_evidence(package: Path) -> dict[str, Any]:
    summaries = {}
    for name, count, expected_hash in _PARENTS:
        directory = (package.parent / name).resolve()
        manifest_path = directory / "manifest.json"
        actual_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"protected {name} manifest SHA-256 changed")
        files = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
        if len(files) != count or len({entry["path"] for entry in files}) != count:
            raise ValueError(f"protected {name} manifest count changed")
        for entry in files:
            target = (directory / entry["path"]).resolve()
            if not target.is_relative_to(directory) or not target.is_file():
                raise ValueError(f"protected evidence escaped or disappeared: {entry['path']}")
            if target.stat().st_size != entry["bytes"] or hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"protected evidence content changed: {name}/{entry['path']}")
        summaries[name] = {"status": "passed", "verified_files": count, "manifest_sha256": actual_hash}
    for filename in ("protected_evidence_preflight.json", "protected_evidence_postflight.json"):
        retained = json.loads((package / filename).read_text(encoding="utf-8"))
        if retained != summaries:
            raise ValueError(f"protected evidence audit record differs from independently recomputed inventory: {filename}")
    return {"status": "passed", "packages": summaries, "parent_science_not_rerun": True,
            "preflight_and_postflight_records_independently_confirmed": True}


def verify_fem_curved_pressure(result: Path | str, *, save: bool = False) -> dict[str, Any]:
    package = Path(result)
    cases: dict[str, Any] = {}
    gates: dict[str, str] = {}
    extra: dict[str, Any] = {}
    try:
        configuration = json.loads((package / "configuration.json").read_text(encoding="utf-8"))
        _check_configuration(configuration)
        gates["configuration"] = "passed"
        extra["protected_evidence"] = _protected_evidence(package)
        gates["protected_evidence"] = extra["protected_evidence"]["status"]
        for case in _CASES:
            name = case["name"]
            try:
                with np.load(package / "raw" / f"{name}.npz", allow_pickle=False) as archive:
                    payload = {key: archive[key] for key in archive.files}
                history = json.loads((package / "raw" / f"{name}_newton.json").read_text(encoding="utf-8"))
                cases[name] = verify_curved_case(payload, case["counts"], history)
            except (ValueError, KeyError, OSError, IndexError, TypeError, FloatingPointError) as error:
                cases[name] = {"status": "failed", "error": f"{type(error).__name__}: {error}"}
        for gate in ("geometry", "complete_history", "fields", "equilibrium", "analytic"):
            gates[gate] = "passed" if all(cases[name].get("gates", {}).get(gate) == "passed" for name in ("coarse", "fine")) else "failed"
        if all("states" in cases[name] for name in ("coarse", "fine")):
            coarse, fine = (cases[name]["states"][-1]["inner_radial_displacement"] for name in ("coarse", "fine"))
            difference = abs(coarse - fine) / max(abs(fine), 1.0e-14)
            extra["mesh_comparison"] = {"coarse_peak_radial_displacement": coarse,
                                        "fine_peak_radial_displacement": fine,
                                        "relative_difference": difference,
                                        "status": "passed" if fine > 0 and difference <= 0.05 else "failed"}
            gates["mesh"] = extra["mesh_comparison"]["status"]
        else:
            gates["mesh"] = "failed"
    except (ValueError, KeyError, OSError, IndexError, TypeError, FloatingPointError) as error:
        gates["input_audit"] = "failed"
        extra["audit_error"] = f"{type(error).__name__}: {error}"
    analytic = [incompressible_radial_reference(float(load)) for load in _LOADS]
    expected_gates = {"configuration", "protected_evidence", "geometry", "complete_history", "fields", "equilibrium", "analytic", "mesh"}
    passed = expected_gates.issubset(gates) and all(value == "passed" for value in gates.values())
    report = {"schema_version": "prl.fem_curved_pressure_verification.v1", "status": "passed" if passed else "failed",
              "gates": gates, "cases": cases, **extra,
              "analytic_reference": {"pressures": _LOADS.tolist(),
                 "inner_radial_displacement": [entry["inner_radial_displacement"] for entry in analytic],
                 "inner_deformed_radius": [entry["inner_deformed_radius"] for entry in analytic],
                 "kind": "incompressible_limit",
                 "description": "Infinite plane-strain NH cylinder; exact incompressibility, not a matched finite-kappa reference"},
              "scientific_scope": "synthetic quarter-cylinder plane-strain qualification only",
              "not_run": ["real_ventricle", "material_calibration", "physiologic_time", "free_3d_ventricular_motion", "blood_flow", "growth", "ECM_feedback"]}
    serialized = json.dumps(report, indent=2, allow_nan=False, default=_numpy_json_scalar)
    if save:
        (package / "verification.json").write_text(serialized + "\n", encoding="utf-8")
    return json.loads(serialized)
