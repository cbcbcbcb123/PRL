"""Lightweight CPU preflight for the Paper-2 M2A FEniCSx identity model.

This script deliberately does not instantiate any M2A biological case.  It
assembles a representative two-dimensional plane-strain operator on the three
candidate nested meshes, exercises the frozen C0/C1 linear tolerances, and
writes a create-only JSON resource record.  It is intended to run inside the
pinned ``dolfinx/dolfinx:v0.11.0`` container.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import dolfinx
import numpy as np
import scipy
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
import ufl
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fem_petsc
from mpi4py import MPI
from petsc4py import PETSc


@dataclass(frozen=True)
class CandidateLevel:
    label: str
    nx: int
    ny_per_layer: int


@dataclass(frozen=True)
class ToleranceProfile:
    label: str
    coupling_tolerance: float
    maximum_coupling_iterations: int
    lbfgs_gtol: float
    newton_fatol: float
    follower_tolerance: float
    kkt_tolerance: float


LEVELS = (
    CandidateLevel("S0", nx=8, ny_per_layer=2),
    CandidateLevel("S1", nx=16, ny_per_layer=4),
    CandidateLevel("S2", nx=32, ny_per_layer=8),
)

TOLERANCES = (
    ToleranceProfile("C0", 1.0e-4, 12, 2.0e-7, 1.0e-7, 1.0e-7, 1.0e-5),
    ToleranceProfile("C1", 1.0e-5, 24, 2.0e-8, 1.0e-8, 1.0e-8, 1.0e-6),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _to_csr(matrix: PETSc.Mat) -> sparse.csr_matrix:
    row_offsets, column_indices, values = matrix.getValuesCSR()
    return sparse.csr_matrix(
        (values.copy(), column_indices.copy(), row_offsets.copy()),
        shape=matrix.getSize(),
    )


def _assemble_representative_operator(level: CandidateLevel) -> tuple[sparse.csr_matrix, dict]:
    start = time.perf_counter()
    domain = mesh.create_rectangle(
        MPI.COMM_WORLD,
        [np.array([0.0, 0.0]), np.array([4.0, 1.0])],
        [level.nx, 2 * level.ny_per_layer],
        cell_type=mesh.CellType.triangle,
    )
    vector_space = fem.functionspace(domain, ("Lagrange", 1, (2,)))
    trial = ufl.TrialFunction(vector_space)
    test = ufl.TestFunction(vector_space)
    identity = ufl.Identity(2)
    strain_trial = ufl.sym(ufl.grad(trial))
    strain_test = ufl.sym(ufl.grad(test))

    # Plane-strain Lamé coefficients for a representative nondimensional solid.
    young_modulus = 1.0
    poisson_ratio = 0.30
    shear_modulus = young_modulus / (2.0 * (1.0 + poisson_ratio))
    lame_lambda = (
        young_modulus
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    stress_trial = (
        2.0 * shear_modulus * strain_trial
        + lame_lambda * ufl.tr(strain_trial) * identity
    )
    stiffness_form = fem.form(ufl.inner(stress_trial, strain_test) * ufl.dx)
    mass_form = fem.form(ufl.inner(trial, test) * ufl.dx)

    stiffness = fem_petsc.assemble_matrix(stiffness_form)
    stiffness.assemble()
    mass = fem_petsc.assemble_matrix(mass_form)
    mass.assemble()
    operator = _to_csr(stiffness) + 0.15 * _to_csr(mass)
    operator = (0.5 * (operator + operator.T)).tocsr()
    assembly_seconds = time.perf_counter() - start

    n_triangles = 4 * level.nx * level.ny_per_layer
    n_nodes_per_layer = (level.nx + 1) * (level.ny_per_layer + 1)
    estimated_m2a_state_dofs = (
        4 * n_nodes_per_layer
        + 2 * (level.nx + 1)
        + 6 * level.nx * level.ny_per_layer
    )
    metadata = {
        "assembled_vector_dofs": int(operator.shape[0]),
        "assembled_nonzeros": int(operator.nnz),
        "triangles_two_layer_probe": int(n_triangles),
        "estimated_m2a_state_dofs": int(estimated_m2a_state_dofs),
        "assembly_seconds": assembly_seconds,
    }
    return operator, metadata


def _solve_probe(
    operator: sparse.csr_matrix,
    profile: ToleranceProfile,
) -> dict:
    rng = np.random.default_rng(20260903)
    right_hand_side = rng.standard_normal(operator.shape[0])
    iterations = 0

    def count_iteration(_: np.ndarray) -> None:
        nonlocal iterations
        iterations += 1

    start = time.perf_counter()
    solution, info = sparse_linalg.cg(
        operator,
        right_hand_side,
        rtol=profile.newton_fatol,
        atol=profile.newton_fatol * 1.0e-3,
        maxiter=2000,
        callback=count_iteration,
    )
    solve_seconds = time.perf_counter() - start
    residual = operator @ solution - right_hand_side
    relative_residual = float(
        np.linalg.norm(residual) / max(np.linalg.norm(right_hand_side), 1.0e-30)
    )
    return {
        "converged": bool(info == 0),
        "solver_info": int(info),
        "iterations": int(iterations),
        "solve_seconds": solve_seconds,
        "relative_residual": relative_residual,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    if MPI.COMM_WORLD.size != 1:
        raise RuntimeError("M2A preflight is frozen to one CPU process")
    if arguments.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=False)

    level_records: list[dict] = []
    all_converged = True
    maximum_fine_solve_seconds = 0.0
    for level in LEVELS:
        operator, metadata = _assemble_representative_operator(level)
        solves = {}
        for profile in TOLERANCES:
            result = _solve_probe(operator, profile)
            solves[profile.label] = result
            all_converged = all_converged and result["converged"]
            if level.label == "S2":
                maximum_fine_solve_seconds = max(
                    maximum_fine_solve_seconds,
                    result["solve_seconds"],
                )
        level_records.append(
            {
                "level": asdict(level),
                "metadata": metadata,
                "solves": solves,
            }
        )

    # The production model has at most three real harmonic solves per endpoint;
    # the factor of twelve covers block growth, assembly, diagnostics and I/O.
    estimated_endpoint_seconds = max(1.0, 12.0 * maximum_fine_solve_seconds)
    endpoint_count = 9 * 2 * 3 * 3 * 2
    estimated_matrix_seconds = endpoint_count * estimated_endpoint_seconds
    resource_envelope = {
        "endpoint_count": endpoint_count,
        "estimated_seconds_per_finest_endpoint": estimated_endpoint_seconds,
        "estimated_total_seconds": estimated_matrix_seconds,
        "execution_budget_seconds_per_endpoint": 30.0,
        "execution_budget_seconds_total": 7200.0,
        "within_budget": bool(
            estimated_endpoint_seconds <= 30.0
            and estimated_matrix_seconds <= 7200.0
        ),
        "maximum_resident_memory_budget_gib": 16.0,
        "cpu_processes": 1,
        "gpu_used": False,
    }

    payload = {
        "schema": "paper2_m2a_fenicsx_2d_preflight_v01",
        "status": (
            "PASS"
            if all_converged and resource_envelope["within_budget"]
            else "FAIL"
        ),
        "purpose": "assembly_and_resource_probe_only_no_biological_case",
        "geometry": {
            "length": 4.0,
            "total_thickness": 1.0,
            "plane_strain": True,
        },
        "candidate_nested_levels": [asdict(level) for level in LEVELS],
        "time_ladder": [64, 128, 256],
        "tolerance_profiles": [asdict(profile) for profile in TOLERANCES],
        "levels": level_records,
        "resource_envelope": resource_envelope,
        "provenance": {
            "contract": str(arguments.contract),
            "contract_sha256": _sha256(arguments.contract),
            "authorization": str(arguments.authorization),
            "authorization_sha256": _sha256(arguments.authorization),
            "script": str(Path(__file__).resolve()),
            "script_sha256": _sha256(Path(__file__).resolve()),
            "python": platform.python_version(),
            "dolfinx": dolfinx.__version__,
            "scipy": scipy.__version__,
            "petsc": PETSc.Sys.getVersionInfo(),
            "platform": platform.platform(),
            "logical_cpus_visible": os.cpu_count(),
        },
    }

    output_path = arguments.output_dir / "preflight.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
