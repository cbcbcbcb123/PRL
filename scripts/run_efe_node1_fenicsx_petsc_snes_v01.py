from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from petsc4py import PETSc
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.fenicsx_ecm_backend import FenicsxECMBackend  # noqa: E402
from route_h.ecm_finite_strain import build_ecm_reference  # noqa: E402


DEFAULT_INPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819/inputs"
    / "f150_d0_e0_activation_020_peak.npz"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819"
    / "fenicsx_p1_petsc_snes_v01"
)


def anchor_dofs(reference_vertices: np.ndarray) -> np.ndarray:
    minima = reference_vertices.min(axis=0)
    maxima = reference_vertices.max(axis=0)
    targets = (
        minima,
        np.asarray((maxima[0], minima[1], minima[2])),
        np.asarray((minima[0], maxima[1], minima[2])),
    )
    vertex_ids = [
        int(np.argmin(np.linalg.norm(reference_vertices - target, axis=1)))
        for target in targets
    ]
    if len(set(vertex_ids)) != 3:
        raise RuntimeError("failed to select three independent anchor vertices")
    return np.asarray(
        (
            3 * vertex_ids[0],
            3 * vertex_ids[0] + 1,
            3 * vertex_ids[0] + 2,
            3 * vertex_ids[1] + 1,
            3 * vertex_ids[1] + 2,
            3 * vertex_ids[2] + 2,
        ),
        dtype=np.int32,
    )


def constrained_residual(
    gradient: np.ndarray,
    target_gradient: np.ndarray,
    variables: np.ndarray,
    target_variables: np.ndarray,
    constrained: np.ndarray,
) -> np.ndarray:
    residual = gradient - target_gradient
    residual[constrained] = variables[constrained] - target_variables[constrained]
    return residual


def constrained_tangent(tangent: csr_matrix, constrained: np.ndarray) -> csr_matrix:
    modified = tangent.tolil(copy=True)
    for dof in constrained.tolist():
        modified[dof, :] = 0.0
        modified[:, dof] = 0.0
        modified[dof, dof] = 1.0
    result = modified.tocsr()
    result.eliminate_zeros()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--initial-fraction", type=float, default=0.5)
    parser.add_argument("--maximum-iterations", type=int, default=20)
    arguments = parser.parse_args()
    if not 0.0 <= arguments.initial_fraction < 1.0:
        raise ValueError("initial-fraction must be in [0, 1)")
    if arguments.maximum_iterations < 1:
        raise ValueError("maximum-iterations must be positive")

    input_path = arguments.input.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    arrays = np.load(input_path)
    reference_vertices = np.asarray(arrays["reference_vertices"], dtype=np.float64)
    target_vertices = np.asarray(arrays["current_vertices"], dtype=np.float64)
    tetrahedra = np.asarray(arrays["tetrahedra"], dtype=np.int64)
    internal_z = np.asarray(arrays["internal_z"], dtype=np.float64)
    parameters = {
        "mu_eq": float(arrays["mu_eq"]),
        "kappa_eq": float(arrays["kappa_eq"]),
        "mu_ve": float(arrays["mu_ve"]),
    }
    reference = build_ecm_reference(reference_vertices, tetrahedra)
    backend = FenicsxECMBackend(reference)
    _, target_force, _ = backend.energy_force(
        target_vertices, reference, internal_z, **parameters
    )
    target_gradient = -target_force.reshape(-1)
    target_variables = (target_vertices - reference_vertices).reshape(-1)
    constrained = anchor_dofs(reference_vertices)
    initial = arguments.initial_fraction * target_variables
    initial[constrained] = target_variables[constrained]

    function_evaluations = 0
    jacobian_evaluations = 0

    def evaluate_residual(variables: np.ndarray) -> np.ndarray:
        nonlocal function_evaluations
        current_vertices = reference_vertices + variables.reshape(-1, 3)
        _, force, _ = backend.energy_force(
            current_vertices, reference, internal_z, **parameters
        )
        function_evaluations += 1
        return constrained_residual(
            -force.reshape(-1),
            target_gradient,
            variables,
            target_variables,
            constrained,
        )

    def evaluate_tangent(variables: np.ndarray) -> csr_matrix:
        nonlocal jacobian_evaluations
        current_vertices = reference_vertices + variables.reshape(-1, 3)
        tangent = backend.energy_hessian(
            current_vertices, reference, internal_z, **parameters
        )
        jacobian_evaluations += 1
        return constrained_tangent(tangent, constrained)

    dimension = len(initial)
    initial_tangent = evaluate_tangent(initial)
    petsc_matrix = PETSc.Mat().createAIJ(
        size=(dimension, dimension),
        csr=(
            initial_tangent.indptr,
            initial_tangent.indices,
            initial_tangent.data,
        ),
        comm=PETSc.COMM_SELF,
    )
    petsc_matrix.setOption(PETSc.Mat.Option.NEW_NONZERO_ALLOCATION_ERR, False)
    solution = PETSc.Vec().createSeq(dimension, comm=PETSc.COMM_SELF)
    solution.array[:] = initial
    residual_vector = solution.duplicate()
    snes_history: list[dict[str, float | int]] = []

    def snes_function(_snes, variables, residual) -> None:
        values = np.asarray(variables.getArray(readonly=True), dtype=np.float64)
        residual.array[:] = evaluate_residual(values)

    def snes_jacobian(_snes, variables, jacobian, preconditioner) -> None:
        values = np.asarray(variables.getArray(readonly=True), dtype=np.float64)
        tangent = evaluate_tangent(values)
        for matrix in (jacobian, preconditioner):
            matrix.zeroEntries()
            matrix.setValuesCSR(
                tangent.indptr,
                tangent.indices,
                tangent.data,
            )
            matrix.assemble()

    snes = PETSc.SNES().create(PETSc.COMM_SELF)
    snes.setType("newtonls")
    snes.setFunction(snes_function, residual_vector)
    snes.setJacobian(snes_jacobian, petsc_matrix, petsc_matrix)
    snes.setTolerances(
        atol=1.0e-10,
        rtol=1.0e-10,
        stol=1.0e-12,
        max_it=arguments.maximum_iterations,
    )
    snes.getLineSearch().setType("bt")
    linear_solver = snes.getKSP()
    linear_solver.setType("preonly")
    linear_solver.getPC().setType("lu")
    snes.setMonitor(
        lambda solver, iteration, residual_norm: snes_history.append(
            {
                "iteration": int(iteration),
                "residual_norm": float(residual_norm),
                "linear_iterations": int(solver.getLinearSolveIterations()),
            }
        )
    )
    snes_started = time.perf_counter()
    snes.solve(None, solution)
    snes_seconds = time.perf_counter() - snes_started
    snes_variables = solution.array.copy()
    snes_residual = evaluate_residual(snes_variables)
    snes_reason = int(snes.getConvergedReason())

    scipy_variables = initial.copy()
    scipy_history = []
    scipy_started = time.perf_counter()
    scipy_converged = False
    for iteration in range(arguments.maximum_iterations + 1):
        residual = evaluate_residual(scipy_variables)
        residual_norm = float(np.linalg.norm(residual))
        scipy_history.append(
            {"iteration": iteration, "residual_norm": residual_norm}
        )
        if residual_norm <= 1.0e-10:
            scipy_converged = True
            break
        tangent = evaluate_tangent(scipy_variables)
        direction = spsolve(tangent, -residual)
        step_length = 1.0
        accepted = False
        for _ in range(20):
            candidate = scipy_variables + step_length * direction
            candidate[constrained] = target_variables[constrained]
            try:
                candidate_residual = evaluate_residual(candidate)
            except ValueError:
                step_length *= 0.5
                continue
            if np.linalg.norm(candidate_residual) < residual_norm:
                scipy_variables = candidate
                accepted = True
                break
            step_length *= 0.5
        scipy_history[-1]["step_length"] = step_length
        scipy_history[-1]["accepted"] = accepted
        if not accepted:
            break
    scipy_seconds = time.perf_counter() - scipy_started
    scipy_residual = evaluate_residual(scipy_variables)

    snes_recovery_error = float(
        np.linalg.norm(snes_variables - target_variables)
        / max(1.0e-14, float(np.linalg.norm(target_variables)))
    )
    scipy_recovery_error = float(
        np.linalg.norm(scipy_variables - target_variables)
        / max(1.0e-14, float(np.linalg.norm(target_variables)))
    )
    snes_passed = bool(
        snes_reason > 0
        and np.linalg.norm(snes_residual) <= 1.0e-8
        and snes_recovery_error <= 1.0e-6
    )
    scipy_passed = bool(
        scipy_converged
        and np.linalg.norm(scipy_residual) <= 1.0e-8
        and scipy_recovery_error <= 1.0e-6
    )
    report = {
        "schema_version": "efe_node1_fenicsx_petsc_snes_v01",
        "status": "passed" if snes_passed and scipy_passed else "failed",
        "evidence_class": "solver_recovery_test_not_formal_n1_2_evidence",
        "problem": (
            "Recover the accepted F150 peak ECM displacement from its exact "
            "nodal internal-force vector with six rigid-body anchors."
        ),
        "dof_count": dimension,
        "constrained_dofs": constrained.tolist(),
        "initial_fraction": arguments.initial_fraction,
        "petsc_snes": {
            "passed": snes_passed,
            "converged_reason": snes_reason,
            "iterations": int(snes.getIterationNumber()),
            "linear_iterations": int(snes.getLinearSolveIterations()),
            "final_residual_norm": float(np.linalg.norm(snes_residual)),
            "recovery_relative_l2": snes_recovery_error,
            "seconds": snes_seconds,
            "history": snes_history,
        },
        "scipy_sparse_newton": {
            "passed": scipy_passed,
            "converged": scipy_converged,
            "iterations": len(scipy_history) - 1,
            "final_residual_norm": float(np.linalg.norm(scipy_residual)),
            "recovery_relative_l2": scipy_recovery_error,
            "seconds": scipy_seconds,
            "history": scipy_history,
        },
        "backend_calls": {
            "residual": function_evaluations,
            "jacobian": jacobian_evaluations,
        },
        "backend_diagnostics": backend.diagnostics(),
        "boundary": (
            "This is an ECM-only nonlinear solver recovery test. A pass does "
            "not establish full DCM-FEM SNES production readiness."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("PETSc SNES ECM recovery test failed")


if __name__ == "__main__":
    main()
