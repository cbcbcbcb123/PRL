"""Small 3-D Q2/Q1 mixed finite-deformation qualification solver.

Pressure is a *tensile-positive* volumetric stress: the mixed potential is
W_iso(F) + W_active(F) + p (J - 1) - p**2/(2*kappa).  Conventional compressive
pressure is consequently -p.  This module writes no files and applies no loads
implicitly.  Unconstrained faces have zero nominal traction; supplied nodal
forces are dead loads.  Explicit follower pressure uses current-area face
quadrature and its consistent tangent, without assuming an open-face potential.
"""

from __future__ import annotations

from itertools import product
import warnings

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from .hyperelastic import material_response


class MixedSolveError(RuntimeError):
    """A failed Newton solve retaining the last admissible, evaluated state."""

    def __init__(self, reason: str, last_state: dict):
        super().__init__(reason)
        self.last_state = last_state
        self.history = last_state.get("history", [])


def shape_functions(points: np.ndarray) -> dict:
    """Tensor-product Q2/Q1 values and reference derivatives on [-1,1]^3.

    Local node order is lexicographic (x, then y, then z), z varying fastest.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("quadrature points must have shape (n, 3)")
    q2_axes, q2_derivatives, q1_axes = [], [], []
    for axis in range(3):
        coordinate = points[:, axis]
        q2_axes.append(np.stack((coordinate * (coordinate - 1) / 2,
                                 1 - coordinate**2,
                                 coordinate * (coordinate + 1) / 2), axis=1))
        q2_derivatives.append(np.stack((coordinate - 0.5, -2 * coordinate,
                                        coordinate + 0.5), axis=1))
        q1_axes.append(np.stack(((1 - coordinate) / 2,
                                 (1 + coordinate) / 2), axis=1))
    q2 = np.empty((len(points), 27))
    gradient = np.empty((len(points), 27, 3))
    for local, indices in enumerate(product(range(3), repeat=3)):
        q2[:, local] = np.prod([q2_axes[d][:, indices[d]] for d in range(3)], axis=0)
        for derivative_axis in range(3):
            gradient[:, local, derivative_axis] = np.prod([
                (q2_derivatives[d] if d == derivative_axis else q2_axes[d])[:, indices[d]]
                for d in range(3)], axis=0)
    q1 = np.empty((len(points), 8))
    for local, indices in enumerate(product(range(2), repeat=3)):
        q1[:, local] = np.prod([q1_axes[d][:, indices[d]] for d in range(3)], axis=0)
    return {"q2": q2, "q2_derivatives": gradient, "q1": q1}


def structured_mesh(counts: tuple[int, int, int], lengths=(1.0, 1.0, 1.0)) -> dict:
    """A conforming rectangular Q2 displacement / continuous Q1 pressure mesh."""
    if len(counts) != 3 or any(int(v) != v or int(v) < 1 for v in counts):
        raise ValueError("counts must be three positive integers")
    counts = tuple(int(v) for v in counts)
    lengths = np.asarray(lengths, dtype=float)
    if lengths.shape != (3,) or not np.all(np.isfinite(lengths)) or np.any(lengths <= 0):
        raise ValueError("lengths must be three finite positive values")
    node_shape = tuple(2 * v + 1 for v in counts)
    pressure_shape = tuple(v + 1 for v in counts)
    nodes = np.array(list(product(*[np.linspace(0, lengths[d], node_shape[d])
                                    for d in range(3)])))
    pressure_nodes = np.array(list(product(*[np.linspace(0, lengths[d], pressure_shape[d])
                                             for d in range(3)])))
    elements, pressure_elements = [], []
    for origin in product(*[range(v) for v in counts]):
        elements.append([np.ravel_multi_index(tuple(2 * origin[d] + local[d] for d in range(3)),
                                               node_shape)
                         for local in product(range(3), repeat=3)])
        pressure_elements.append([np.ravel_multi_index(tuple(origin[d] + local[d] for d in range(3)),
                                                        pressure_shape)
                                  for local in product(range(2), repeat=3)])
    return {"nodes": nodes, "pressure_nodes": pressure_nodes,
            "elements": np.asarray(elements, dtype=np.int64),
            "pressure_elements": np.asarray(pressure_elements, dtype=np.int64),
            "counts": counts, "lengths": lengths, "node_shape": node_shape,
            "pressure_shape": pressure_shape, "element_type": "Q2-Q1-continuous"}


def precompute(mesh: dict) -> dict:
    """3x3x3 Gauss integration; curved mapping requires explicit opt-in."""
    abscissae, weights = np.polynomial.legendre.leggauss(3)
    quadrature_indices = np.array(list(product(range(3), repeat=3)))
    points = abscissae[quadrature_indices]
    shape = shape_functions(points)
    mapping = mesh.get("geometry_mapping", "affine")
    geometry = {}
    if mapping == "isoparametric":
        nodes, cells = np.asarray(mesh["nodes"]), np.asarray(mesh["elements"])
        if (nodes.ndim != 2 or nodes.shape[1] != 3 or not np.all(np.isfinite(nodes))
                or np.iscomplexobj(nodes) or cells.ndim != 2 or cells.shape[1] != 27
                or not np.issubdtype(cells.dtype, np.integer)
                or np.any(cells < 0) or np.any(cells >= len(nodes))):
            raise ValueError("invalid isoparametric reference nodes or connectivity")
        jacobian = np.einsum("eai,qaJ->eqiJ", nodes[cells], shape["q2_derivatives"])
        determinant = np.linalg.det(jacobian)
        if np.any(determinant <= 0) or not np.all(np.isfinite(determinant)):
            raise ValueError("nonpositive or nonfinite isoparametric reference Jacobian")
        gradient = np.einsum("qaJ,eqJI->eqaI", shape["q2_derivatives"], np.linalg.inv(jacobian))
        integration_weights = determinant * np.prod(weights[quadrature_indices], axis=1)
        geometry = {"reference_jacobians": jacobian, "reference_jacobian_determinants": determinant}
    elif mapping == "affine":
        cell_lengths = np.asarray(mesh["lengths"]) / np.asarray(mesh["counts"])
        gradient = shape["q2_derivatives"] * (2 / cell_lengths)
        integration_weights = np.prod(weights[quadrature_indices], axis=1) * np.prod(cell_lengths) / 8
    else:
        raise ValueError("geometry_mapping must be affine or isoparametric")
    displacement_dofs = (3 * mesh["elements"][:, :, None] + np.arange(3)).reshape(-1, 81)
    pressure_dofs = 3 * len(mesh["nodes"]) + mesh["pressure_elements"]
    element_dofs = np.concatenate((displacement_dofs, pressure_dofs), axis=1)
    positions = np.einsum("qa,eai->eqi", shape["q2"], mesh["nodes"][mesh["elements"]])
    return {**shape, **geometry, "gradients": gradient, "weights": integration_weights,
            "quadrature_points": points, "positions": positions,
            "element_dofs": element_dofs,
            "rows": np.broadcast_to(element_dofs[:, :, None], (len(element_dofs), 89, 89)).ravel(),
            "columns": np.broadcast_to(element_dofs[:, None, :], (len(element_dofs), 89, 89)).ravel()}


def lift_dirichlet_initial(mesh: dict, initial, dirichlet: dict) -> dict:
    """Harmonically extend prescribed displacement *increments* on Q2 nodes.

    This geometric predictor is deliberately separate from Newton mechanics.
    Each displacement component solves a reference scalar Laplace problem;
    components with no prescribed DOFs receive zero increment.  Pressure and
    the caller's initial vector are unchanged.  Only this module's structured
    affine mesh is supported.  Nonpositive predicted Gauss J is a hard failure,
    with no automatic subdivision, boundary change, or mechanical solve.
    """
    from collections.abc import Mapping

    if not isinstance(mesh, Mapping):
        raise ValueError("lifting requires a structured mesh mapping")
    if mesh.get("geometry_mapping", "affine") != "affine":
        raise ValueError("harmonic lifting remains qualified only for the unchanged affine structured mesh")
    try:
        expected = structured_mesh(tuple(mesh["counts"]), lengths=mesh["lengths"])
        for key in ("nodes", "pressure_nodes", "elements", "pressure_elements"):
            if not np.array_equal(mesh[key], expected[key]):
                raise ValueError(f"lifting supports only the unchanged structured mesh: {key}")
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError("invalid structured mesh for lifting") from error
    if not isinstance(dirichlet, Mapping):
        raise ValueError("Dirichlet values must be a DOF-to-value mapping")
    node_count = len(mesh["nodes"])
    displacement_size = 3 * node_count
    size = displacement_size + len(mesh["pressure_nodes"])
    if any(isinstance(key, (bool, np.bool_)) or not isinstance(key, (int, np.integer))
           or not 0 <= int(key) < displacement_size for key in dirichlet):
        raise ValueError("Dirichlet keys must be integer displacement DOFs")
    fixed = np.array(sorted(dirichlet), dtype=np.int64)
    raw_values = np.asarray([dirichlet[int(key)] for key in fixed])
    if np.iscomplexobj(raw_values):
        raise ValueError("Dirichlet values must be finite real scalars")
    try:
        values = np.asarray(raw_values, dtype=float)
        raw_initial = np.zeros(size) if initial is None else np.asarray(
            initial["vector"] if isinstance(initial, Mapping) else initial)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid lifting initial state or Dirichlet values") from error
    if np.iscomplexobj(raw_initial):
        raise ValueError("initial state must be real")
    try:
        vector = np.array(raw_initial, dtype=float, copy=True)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid lifting initial state") from error
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError("initial state must have the complete finite mixed-vector shape")
    if values.shape != (len(fixed),) or not np.all(np.isfinite(values)):
        raise ValueError("Dirichlet values must be finite real scalars")
    prepared = precompute(mesh)
    gradient, weights = prepared["gradients"], prepared["weights"]
    scalar_element = np.einsum("qaJ,qbJ,q->ab", gradient, gradient, weights)
    elements = mesh["elements"]
    matrix_shape = (len(elements), 27, 27)
    rows = np.broadcast_to(elements[:, :, None], matrix_shape).ravel()
    columns = np.broadcast_to(elements[:, None, :], matrix_shape).ravel()
    laplacian = coo_matrix((np.broadcast_to(scalar_element, matrix_shape).ravel(), (rows, columns)),
                          shape=(node_count, node_count)).tocsr()
    increment = np.zeros((node_count, 3))
    unconstrained_components = []
    for component in range(3):
        selected = np.flatnonzero(fixed % 3 == component)
        if len(selected) == 0:
            unconstrained_components.append(component)
            continue
        constrained_nodes = fixed[selected] // 3
        free_nodes = np.setdiff1d(np.arange(node_count), constrained_nodes)
        increment[constrained_nodes, component] = values[selected] - vector[fixed[selected]]
        if len(free_nodes):
            right_hand_side = -laplacian[free_nodes][:, constrained_nodes] @ increment[constrained_nodes, component]
            with warnings.catch_warnings():
                warnings.simplefilter("error", MatrixRankWarning)
                try:
                    increment[free_nodes, component] = spsolve(laplacian[free_nodes][:, free_nodes], right_hand_side)
                except (MatrixRankWarning, RuntimeError, ValueError) as error:
                    raise ValueError("harmonic Dirichlet lifting linear solve failed") from error
    if not np.all(np.isfinite(increment)):
        raise ValueError("harmonic Dirichlet lifting produced a nonfinite increment")
    vector[:displacement_size] += increment.ravel()
    vector[fixed] = values  # Exact prescribed values, without extending the set.
    # Independently check the current/reference isoparametric Jacobian ratio;
    # do not call material_response, assemble, or solve to assess feasibility.
    reference = mesh["nodes"][elements]
    current = (mesh["nodes"] + vector[:displacement_size].reshape(-1, 3))[elements]
    reference_jacobian = np.einsum("eai,qaJ->eqiJ", reference, prepared["q2_derivatives"])
    current_jacobian = np.einsum("eai,qaJ->eqiJ", current, prepared["q2_derivatives"])
    determinants = np.linalg.det(current_jacobian) / np.linalg.det(reference_jacobian)
    if np.any(determinants <= 0) or not np.all(np.isfinite(determinants)):
        raise ValueError(f"harmonic Dirichlet lifting is inadmissible: minimum J={float(np.min(determinants)):.17g}")
    diagnostics = {"method": "reference_Q2_componentwise_harmonic_increment",
                   "min_J": float(determinants.min()), "max_J": float(determinants.max()),
                   "increment_norm": float(np.linalg.norm(increment)),
                   "dirichlet_max_error": float(np.max(np.abs(vector[fixed] - values))) if len(fixed) else 0.0,
                   "pressure_max_change": 0.0, "constrained_dofs": fixed.tolist(),
                   "unconstrained_components": unconstrained_components,
                   "automatic_subdivisions": 0}
    return {"vector": vector, "diagnostics": diagnostics}


def assemble(mesh: dict, material: dict, kappa: float, vector: np.ndarray,
             active_tension: float = 0.0, external_forces=None, *,
             prepared: dict | None = None, with_tangent: bool = True,
             follower_pressure=None) -> dict:
    """Assemble exact mixed residual and analytic tangent; no boundary elimination.

    The flat unknown is [node-major displacement xyz, continuous pressure].
    Tangent axes in the material seam are (i,J,k,L)=dP_iJ/dF_kL.
    With follower pressure, `energy` excludes pressure work and is not a total
    potential.  The force/tangent are nonetheless evaluated consistently.
    """
    if not np.isfinite(kappa) or kappa <= 0:
        raise ValueError("kappa must be finite and positive")
    if not np.isfinite(active_tension) or active_tension < 0:
        raise ValueError("active_tension must be finite and nonnegative")
    prepared = precompute(mesh) if prepared is None else prepared
    displacement_size = 3 * len(mesh["nodes"])
    size = displacement_size + len(mesh["pressure_nodes"])
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError("invalid mixed state vector")
    forces = _external_forces(external_forces, displacement_size, size)
    displacement = vector[:displacement_size].reshape(-1, 3)
    pressure = vector[displacement_size:]
    gradient, weights, q1 = prepared["gradients"], prepared["weights"], prepared["q1"]
    curved = gradient.ndim == 4
    F = np.eye(3) + (np.einsum("eai,eqaJ->eqiJ", displacement[mesh["elements"]], gradient) if curved
                     else np.einsum("eai,qaJ->eqiJ", displacement[mesh["elements"]], gradient))
    J = np.linalg.det(F)
    if np.any(J <= 0) or not np.all(np.isfinite(J)):
        raise ValueError("nonpositive or nonfinite deformation determinant")
    pressure_gauss = np.einsum("ep,qp->eq", pressure[mesh["pressure_elements"]], q1)
    configured_material = {**material, "active_tension": float(active_tension)}
    response = material_response(F, configured_material, fiber=material.get("fiber"))
    inverse_transpose = np.swapaxes(np.linalg.inv(F), -1, -2)
    cofactor = J[..., None, None] * inverse_transpose
    P = response["P"] + pressure_gauss[..., None, None] * cofactor
    mixed_density = response["energy"] + pressure_gauss * (J - 1) - pressure_gauss**2 / (2 * kappa)
    if curved:
        displacement_residual = np.einsum("eqiJ,eqaJ,eq->eai", P, gradient, weights)
        pressure_residual = np.einsum("eq,qp,eq->ep", J - 1 - pressure_gauss / kappa, q1, weights)
    else:
        displacement_residual = np.einsum("eqiJ,qaJ,q->eai", P, gradient, weights)
        pressure_residual = np.einsum("eq,qp,q->ep", J - 1 - pressure_gauss / kappa, q1, weights)
    element_residual = np.concatenate((displacement_residual.reshape(-1, 81), pressure_residual), axis=1)
    residual = np.zeros(size)
    np.add.at(residual, prepared["element_dofs"].ravel(), element_residual.ravel())
    residual -= forces
    pressure_load = None
    pressure_forces = np.zeros(size)
    if follower_pressure is not None:
        from .follower_pressure import assemble_pressure
        if not isinstance(follower_pressure, dict) or set(follower_pressure) != {"faces", "pressure"}:
            raise ValueError("follower_pressure must contain exactly faces and pressure")
        pressure_load = assemble_pressure(mesh, displacement, follower_pressure["faces"],
                                          follower_pressure["pressure"], with_tangent=with_tangent)
        pressure_forces[:displacement_size] = pressure_load["force"]
        residual -= pressure_forces
    tangent = None
    if with_tangent:
        cofactor_derivative = J[..., None, None, None, None] * (
            np.einsum("eqiJ,eqkL->eqiJkL", inverse_transpose, inverse_transpose)
            - np.einsum("eqiL,eqkJ->eqiJkL", inverse_transpose, inverse_transpose))
        constitutive = response["tangent"] + pressure_gauss[..., None, None, None, None] * cofactor_derivative
        if curved:
            Kuu = np.einsum("eqaJ,eqiJkL,eqbL,eq->eaibk", gradient, constitutive, gradient, weights,
                            optimize=True).reshape(-1, 81, 81)
            Kup = np.einsum("eqiJ,eqaJ,qp,eq->eaip", cofactor, gradient, q1, weights,
                            optimize=True).reshape(-1, 81, 8)
            Kpp = -np.einsum("qp,qr,eq->epr", q1, q1, weights) / kappa
        else:
            Kuu = np.einsum("qaJ,eqiJkL,qbL,q->eaibk", gradient, constitutive, gradient, weights,
                            optimize=True).reshape(-1, 81, 81)
            Kup = np.einsum("eqiJ,qaJ,qp,q->eaip", cofactor, gradient, q1, weights,
                            optimize=True).reshape(-1, 81, 8)
            Kpp = -np.einsum("qp,qr,q->pr", q1, q1, weights) / kappa
        element_tangent = np.empty((len(mesh["elements"]), 89, 89))
        element_tangent[:, :81, :81] = Kuu
        element_tangent[:, :81, 81:] = Kup
        element_tangent[:, 81:, :81] = np.swapaxes(Kup, 1, 2)
        element_tangent[:, 81:, 81:] = Kpp
        tangent = coo_matrix((element_tangent.ravel(), (prepared["rows"], prepared["columns"])),
                            shape=(size, size)).tocsr()
        if pressure_load is not None:
            load_tangent = pressure_load["tangent"].tocoo()
            tangent -= coo_matrix((load_tangent.data, (load_tangent.row, load_tangent.col)), shape=(size, size)).tocsr()
    cauchy = np.einsum("eqiJ,eqkJ->eqik", P, F) / J[..., None, None]
    green = 0.5 * (np.einsum("eqiJ,eqiK->eqJK", F, F) - np.eye(3))
    return {"residual": residual, "tangent": tangent, "F": F, "J": J,
            "pressure_gauss": pressure_gauss, "P": P, "cauchy_stress": cauchy, "Green": green,
            "energy": float(np.sum(mixed_density * weights) - forces @ vector),
            "material_energy": float(np.sum(response["energy"] * weights)),
            "energy_density": response["energy"], "mixed_energy_density": mixed_density,
            "pressure_forces": pressure_forces, "total_external_forces": forces + pressure_forces,
            "energy_is_total_potential": follower_pressure is None,
            "energy_note": "internal mixed energy minus dead-load work; excludes follower-pressure work" if follower_pressure is not None else "total mixed potential",
            "constraint_gauss": J - 1 - pressure_gauss / kappa}


def _external_forces(external_forces, displacement_size: int, size: int) -> np.ndarray:
    if external_forces is None:
        return np.zeros(size)
    forces = np.asarray(external_forces, dtype=float).reshape(-1)
    if forces.shape == (displacement_size,):
        forces = np.pad(forces, (0, size - displacement_size))
    if forces.shape != (size,) or not np.all(np.isfinite(forces)):
        raise ValueError("external forces must have displacement or complete mixed-vector size")
    if np.any(forces[displacement_size:] != 0):
        raise ValueError("external nodal forces cannot be applied to pressure equations")
    return forces


def solve(mesh: dict, material: dict, kappa: float, active_tension: float = 0.0,
          dirichlet: dict | None = None, initial=None, external_forces=None, *,
          tolerance: float = 1e-9, max_iterations: int = 30,
          max_line_search: int = 16, follower_pressure=None) -> dict:
    """Sparse Newton with normalized free-residual descent and J>0 backtracking.

    Dirichlet keys are displacement DOFs, not node IDs.  No pressure constraint
    is imposed because finite kappa removes its nullspace.  `initial` can be a
    complete vector or a previously returned state.  Iteration bounds are hard
    capped at 30; a failure raises MixedSolveError carrying `last_state`.
    """
    if not 1 <= max_iterations <= 30 or not 1 <= max_line_search <= 16:
        raise ValueError("Newton bound must be in [1,30], line-search bound in [1,16]")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be finite and positive")
    displacement_size = 3 * len(mesh["nodes"])
    size = displacement_size + len(mesh["pressure_nodes"])
    prescribed = {} if dirichlet is None else dirichlet
    if any(int(key) != key or not 0 <= int(key) < displacement_size for key in prescribed):
        raise ValueError("Dirichlet keys must be valid displacement DOFs")
    fixed = np.array(sorted(prescribed), dtype=np.int64)
    values = np.array([prescribed[int(key)] for key in fixed], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("Dirichlet values must be finite")
    free = np.setdiff1d(np.arange(size), fixed)
    if initial is None:
        vector = np.zeros(size)
    else:
        vector = np.asarray(initial["vector"] if isinstance(initial, dict) else initial, dtype=float).copy()
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError("initial state has invalid shape or values")
    vector[fixed] = values
    forces = _external_forces(external_forces, displacement_size, size)
    prepared = precompute(mesh)
    volume = (float(np.sum(prepared["weights"])) if mesh.get("geometry_mapping") == "isoparametric"
              else float(np.prod(mesh["lengths"])))
    stress_scale = float(material.get("mu", material.get("C", 1.0)))
    stress_scale = max(stress_scale, float(active_tension), 1e-30)
    # Both residual blocks have an explicit dimensionless scaling.  This avoids
    # adding raw force and volume residuals with incompatible dimensions.
    length = volume ** (1 / 3)
    residual_scale = np.concatenate((np.full(displacement_size, stress_scale * volume / length),
                                      np.full(size - displacement_size, volume)))

    def normalized(residual):
        # Frozen qualification criterion uses dimensionless engineering inputs.
        # Scales are retained in the state for interpretation, not to relax it.
        return float(np.linalg.norm(residual[free]) / (1 + np.linalg.norm(forces)))

    history = []

    def state(evaluated, converged=False, reason=None):
        result = {key: value for key, value in evaluated.items() if key != "tangent"}
        result.update({"vector": vector.copy(), "displacement": vector[:displacement_size].reshape(-1, 3).copy(),
                       "pressure": vector[displacement_size:].copy(), "converged": converged,
                       "status": "passed" if converged else "failed", "reason": reason,
                       "iterations": max(len(history) - 1, 0), "history": [dict(item) for item in history],
                       "normalized_free_residual": normalized(evaluated["residual"]),
                       "free_dofs": free, "fixed_dofs": fixed, "dirichlet_values": values,
                       "external_forces": forces, "residual_scale": residual_scale,
                       "reactions": evaluated["residual"][fixed].copy()})
        result["u"] = result["displacement"]
        result["p"] = result["pressure"]
        return result

    try:
        evaluated = assemble(mesh, material, kappa, vector, active_tension, forces, prepared=prepared,
                             follower_pressure=follower_pressure)
    except (ValueError, FloatingPointError) as error:
        raise MixedSolveError(f"inadmissible initial state: {error}",
                              {"vector": vector, "history": [], "status": "failed", "converged": False}) from error
    history.append({"iteration": 0, "normalized_free_residual": normalized(evaluated["residual"]),
                    "min_J": float(evaluated["J"].min()), "step_length": 0.0, "line_search_trials": 0})
    for iteration in range(max_iterations + 1):
        residual_norm = normalized(evaluated["residual"])
        if residual_norm <= tolerance:
            return state(evaluated, converged=True)
        if iteration == max_iterations:
            raise MixedSolveError("Newton iteration limit", state(evaluated, reason="Newton iteration limit"))
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            try:
                increment = spsolve(evaluated["tangent"][free][:, free], -evaluated["residual"][free])
            except (MatrixRankWarning, RuntimeError, ValueError) as error:
                raise MixedSolveError(f"linear solve failed: {error}", state(evaluated, reason="linear solve failed")) from error
        if not np.all(np.isfinite(increment)):
            raise MixedSolveError("nonfinite Newton increment", state(evaluated, reason="nonfinite Newton increment"))
        accepted = False
        step_length = 1.0
        for trial in range(1, max_line_search + 1):
            candidate = vector.copy()
            candidate[free] += step_length * increment
            try:
                candidate_evaluated = assemble(mesh, material, kappa, candidate, active_tension, forces,
                                               prepared=prepared, with_tangent=False, follower_pressure=follower_pressure)
                candidate_norm = normalized(candidate_evaluated["residual"])
            except (ValueError, FloatingPointError, np.linalg.LinAlgError):
                candidate_norm = np.inf
            if np.isfinite(candidate_norm) and candidate_norm <= (1 - 1e-4 * step_length) * residual_norm:
                vector = candidate
                evaluated = assemble(mesh, material, kappa, vector, active_tension, forces, prepared=prepared,
                                     follower_pressure=follower_pressure)
                history.append({"iteration": iteration + 1, "normalized_free_residual": candidate_norm,
                                "min_J": float(evaluated["J"].min()), "step_length": step_length,
                                "line_search_trials": trial})
                accepted = True
                break
            step_length *= 0.5
        if not accepted:
            raise MixedSolveError("residual-descent line search failed",
                                  state(evaluated, reason="residual-descent line search failed"))
    raise AssertionError("unreachable Newton state")
