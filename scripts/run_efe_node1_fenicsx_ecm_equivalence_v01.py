"""Run inside the pinned DOLFINx v0.11.0 container.

The script reconstructs the exact owned ECM energy in UFL and compares its
assembled energy and nodal force with the immutable NumPy exchange files.
It is intentionally a field-evaluation spike, not yet a coupled equilibrium
solver and not formal N1-2 evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import time

import basix.ufl
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fem_petsc
from mpi4py import MPI
import numpy as np
from petsc4py import PETSc
import ufl


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def coordinate_key(coordinate: np.ndarray) -> tuple[float, float, float]:
    return tuple(np.round(coordinate, decimals=13).tolist())


def relative_error(actual: np.ndarray | float, expected: np.ndarray | float) -> float:
    difference = float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)))
    scale = max(
        1.0e-14,
        float(np.linalg.norm(np.asarray(actual))),
        float(np.linalg.norm(np.asarray(expected))),
    )
    return difference / scale


def make_mesh(reference_vertices: np.ndarray, tetrahedra: np.ndarray):
    coordinate_element = basix.ufl.element(
        "Lagrange", "tetrahedron", 1, shape=(3,)
    )
    domain = ufl.Mesh(coordinate_element)
    return mesh.create_mesh(
        MPI.COMM_WORLD,
        np.asarray(tetrahedra, dtype=np.int64),
        domain,
        np.asarray(reference_vertices, dtype=np.float64),
    )


def map_vertex_blocks(function_space, reference_vertices: np.ndarray) -> np.ndarray:
    if function_space.dofmap.bs != 3:
        raise RuntimeError("expected a blocked three-component P1 space")
    coordinate_to_input = {
        coordinate_key(coordinate): vertex_id
        for vertex_id, coordinate in enumerate(reference_vertices)
    }
    dof_coordinates = function_space.tabulate_dof_coordinates()
    input_ids = np.empty(len(dof_coordinates), dtype=np.int64)
    for block_id, coordinate in enumerate(dof_coordinates):
        try:
            input_ids[block_id] = coordinate_to_input[coordinate_key(coordinate)]
        except KeyError as error:
            raise RuntimeError(f"unmatched DOLFINx node {coordinate}") from error
    if len(np.unique(input_ids)) != len(reference_vertices):
        raise RuntimeError("DOLFINx/input vertex map is not one-to-one in serial")
    return input_ids


def original_cell_ids(domain, tetrahedra: np.ndarray) -> np.ndarray:
    original = getattr(domain.topology, "original_cell_index", None)
    if original is not None:
        result = np.asarray(original, dtype=np.int64)
        if len(result) == len(tetrahedra):
            return result
    domain.topology.create_connectivity(domain.topology.dim, 0)
    connectivity = domain.topology.connectivity(domain.topology.dim, 0)
    geometry_dofmap = domain.geometry.dofmap
    input_lookup = {
        tuple(sorted(cell.tolist())): cell_id
        for cell_id, cell in enumerate(np.asarray(tetrahedra, dtype=np.int64))
    }
    coordinate_to_input = {
        coordinate_key(coordinate): vertex_id
        for vertex_id, coordinate in enumerate(domain.geometry.x)
    }
    result = np.empty(len(tetrahedra), dtype=np.int64)
    for cell_id in range(len(tetrahedra)):
        geometry_nodes = geometry_dofmap[cell_id]
        input_vertices = tuple(
            sorted(
                coordinate_to_input[coordinate_key(domain.geometry.x[node])]
                for node in geometry_nodes
            )
        )
        if input_vertices not in input_lookup:
            topological_vertices = connectivity.links(cell_id)
            input_vertices = tuple(sorted(int(value) for value in topological_vertices))
        result[cell_id] = input_lookup[input_vertices]
    return result


def assign_dg0_components(domain, internal_z: np.ndarray, cell_ids: np.ndarray):
    scalar_space = fem.functionspace(domain, ("DG", 0))
    components = []
    for row in range(3):
        component_row = []
        for column in range(3):
            coefficient = fem.Function(scalar_space)
            for local_cell, input_cell in enumerate(cell_ids):
                dofs = scalar_space.dofmap.cell_dofs(local_cell)
                if len(dofs) != 1:
                    raise RuntimeError("DG0 must have one scalar dof per cell")
                coefficient.x.array[dofs[0]] = internal_z[input_cell, row, column]
            coefficient.x.scatter_forward()
            component_row.append(coefficient)
        components.append(component_row)
    return ufl.as_tensor(components)


def vector_to_input_order(
    vector: PETSc.Vec,
    input_ids: np.ndarray,
    vertex_count: int,
) -> np.ndarray:
    with vector.localForm() as local:
        flat = np.asarray(local.array, dtype=np.float64).copy()
    if len(flat) != 3 * len(input_ids):
        raise RuntimeError("unexpected blocked vector length")
    output = np.empty((vertex_count, 3), dtype=np.float64)
    for block_id, input_id in enumerate(input_ids):
        output[input_id] = flat[3 * block_id : 3 * block_id + 3]
    return output


def evaluate_case(path: Path, output_path: Path, warm_repeats: int) -> dict[str, object]:
    arrays = np.load(path)
    reference_vertices = np.asarray(arrays["reference_vertices"], dtype=np.float64)
    current_vertices = np.asarray(arrays["current_vertices"], dtype=np.float64)
    tetrahedra = np.asarray(arrays["tetrahedra"], dtype=np.int64)
    internal_z = np.asarray(arrays["internal_z"], dtype=np.float64)
    expected_force = np.asarray(arrays["expected_force"], dtype=np.float64)
    expected_j = np.asarray(arrays["expected_jacobians"], dtype=np.float64)
    expected_energies = {
        "equilibrium": float(arrays["expected_equilibrium_energy"]),
        "viscoelastic": float(arrays["expected_viscoelastic_energy"]),
        "total": float(arrays["expected_total_energy"]),
    }
    mu_eq = float(arrays["mu_eq"])
    kappa_eq = float(arrays["kappa_eq"])
    mu_ve = float(arrays["mu_ve"])

    setup_started = time.perf_counter()
    domain = make_mesh(reference_vertices, tetrahedra)
    displacement_space = fem.functionspace(domain, ("Lagrange", 1, (3,)))
    displacement = fem.Function(displacement_space)
    input_ids = map_vertex_blocks(displacement_space, reference_vertices)
    displacement_values = current_vertices - reference_vertices
    for block_id, input_id in enumerate(input_ids):
        displacement.x.array[3 * block_id : 3 * block_id + 3] = displacement_values[
            input_id
        ]
    displacement.x.scatter_forward()
    cell_ids = original_cell_ids(domain, tetrahedra)
    internal_z_field = assign_dg0_components(domain, internal_z, cell_ids)

    identity = ufl.Identity(3)
    deformation = identity + ufl.grad(displacement)
    determinant = ufl.det(deformation)
    right_cauchy_green = deformation.T * deformation
    c_bar = determinant ** (-2.0 / 3.0) * right_cauchy_green
    q_tensor = ufl.dev(c_bar) - internal_z_field
    equilibrium_density = 0.5 * mu_eq * (ufl.tr(c_bar) - 3.0) + 0.5 * kappa_eq * ufl.ln(
        determinant
    ) ** 2
    viscoelastic_density = 0.25 * mu_ve * ufl.inner(q_tensor, q_tensor)
    integration = ufl.Measure("dx", domain=domain, metadata={"quadrature_degree": 1})
    equilibrium_energy_form = fem.form(equilibrium_density * integration)
    viscoelastic_energy_form = fem.form(viscoelastic_density * integration)
    total_energy_ufl = (equilibrium_density + viscoelastic_density) * integration
    test_function = ufl.TestFunction(displacement_space)
    residual_form = fem.form(ufl.derivative(total_energy_ufl, displacement, test_function))
    setup_and_jit_seconds = time.perf_counter() - setup_started

    assembly_timings = []
    actual_force = None
    actual_energies = None
    for _ in range(warm_repeats):
        assembly_started = time.perf_counter()
        equilibrium_energy = fem.assemble_scalar(equilibrium_energy_form)
        viscoelastic_energy = fem.assemble_scalar(viscoelastic_energy_form)
        residual = fem_petsc.assemble_vector(residual_form)
        residual.ghostUpdate(
            addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE
        )
        assembly_timings.append(time.perf_counter() - assembly_started)
        actual_force = -vector_to_input_order(
            residual, input_ids, len(reference_vertices)
        )
        actual_energies = {
            "equilibrium": float(equilibrium_energy),
            "viscoelastic": float(viscoelastic_energy),
            "total": float(equilibrium_energy + viscoelastic_energy),
        }
    if actual_force is None or actual_energies is None:
        raise AssertionError("FEniCSx assembly did not execute")

    # P1 tetrahedra make F and J elementwise constant.  Reconstructing J from
    # the displacement values also supplies an independent node/cell-map check.
    actual_j = np.empty(len(tetrahedra), dtype=np.float64)
    for input_cell, tetrahedron in enumerate(tetrahedra):
        reference_local = reference_vertices[tetrahedron]
        current_local = current_vertices[tetrahedron]
        reference_edges = np.column_stack(
            (
                reference_local[1] - reference_local[0],
                reference_local[2] - reference_local[0],
                reference_local[3] - reference_local[0],
            )
        )
        current_edges = np.column_stack(
            (
                current_local[1] - current_local[0],
                current_local[2] - current_local[0],
                current_local[3] - current_local[0],
            )
        )
        actual_j[input_cell] = np.linalg.det(
            current_edges @ np.linalg.inv(reference_edges)
        )

    expected_resultant = expected_force.sum(axis=0)
    actual_resultant = actual_force.sum(axis=0)
    centre = reference_vertices.mean(axis=0)
    expected_moment = np.cross(current_vertices - centre, expected_force).sum(axis=0)
    actual_moment = np.cross(current_vertices - centre, actual_force).sum(axis=0)
    warm = np.asarray(assembly_timings[1:], dtype=np.float64)
    if len(warm) == 0:
        raise ValueError("warm_repeats must be at least two")
    metrics = {
        "equilibrium_energy_relative_error": relative_error(
            actual_energies["equilibrium"], expected_energies["equilibrium"]
        ),
        "viscoelastic_energy_relative_error": relative_error(
            actual_energies["viscoelastic"], expected_energies["viscoelastic"]
        ),
        "total_energy_relative_error": relative_error(
            actual_energies["total"], expected_energies["total"]
        ),
        "nodal_force_relative_l2_error": relative_error(actual_force, expected_force),
        "resultant_force_absolute_error": float(
            np.linalg.norm(actual_resultant - expected_resultant)
        ),
        "resultant_force_scaled_error": float(
            np.linalg.norm(actual_resultant - expected_resultant)
            / max(1.0e-14, float(np.linalg.norm(expected_force)))
        ),
        "resultant_moment_absolute_error": float(
            np.linalg.norm(actual_moment - expected_moment)
        ),
        "resultant_moment_scaled_error": float(
            np.linalg.norm(actual_moment - expected_moment)
            / max(1.0e-14, float(np.linalg.norm(expected_force)))
        ),
        "jacobian_maximum_absolute_error": float(np.max(np.abs(actual_j - expected_j))),
        "minimum_j": float(actual_j.min()),
        "maximum_j": float(actual_j.max()),
    }
    m0 = str(arrays["case_name"]) == "m0_reference"
    if m0:
        # A relative force error is undefined as both implementations are at
        # floating-point zero.  The registered M0 gate is therefore absolute.
        passed = bool(
            float(np.linalg.norm(actual_force)) <= 1.0e-11
            and abs(actual_energies["total"]) <= 1.0e-12
            and metrics["jacobian_maximum_absolute_error"] <= 1.0e-12
        )
    else:
        passed = bool(
            metrics["total_energy_relative_error"] <= 1.0e-8
            and metrics["nodal_force_relative_l2_error"] <= 1.0e-8
            and metrics["resultant_force_scaled_error"] <= 1.0e-8
            and metrics["jacobian_maximum_absolute_error"] <= 1.0e-12
        )
    record = {
        "schema_version": "efe_node1_fenicsx_ecm_equivalence_case_v01",
        "case": str(arrays["case_name"]),
        "input_sha256": sha256(path),
        "passed": passed,
        "expected_energies": expected_energies,
        "actual_energies": actual_energies,
        "expected_force_l2": float(np.linalg.norm(expected_force)),
        "actual_force_l2": float(np.linalg.norm(actual_force)),
        "metrics": metrics,
        "timing": {
            "setup_and_jit_seconds": setup_and_jit_seconds,
            "first_assembly_seconds": float(assembly_timings[0]),
            "warm_mean_seconds": float(warm.mean()),
            "warm_median_seconds": float(np.median(warm)),
            "warm_min_seconds": float(warm.min()),
            "warm_max_seconds": float(warm.max()),
            "warm_repeats": int(len(warm)),
        },
    }
    np.savez_compressed(
        output_path / f"{record['case']}_fenicsx_fields.npz",
        actual_force=actual_force,
        actual_jacobians=actual_j,
        expected_force=expected_force,
        expected_jacobians=expected_j,
    )
    (output_path / f"{record['case']}_summary.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warm-repeats", type=int, default=7)
    arguments = parser.parse_args()
    if MPI.COMM_WORLD.size != 1:
        raise RuntimeError("this controlled equivalence spike is serial")
    if arguments.warm_repeats < 2:
        raise ValueError("warm-repeats must be at least two")
    input_path = arguments.input_directory.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    records = [
        evaluate_case(path, output_path, arguments.warm_repeats)
        for path in sorted(input_path.glob("*.npz"))
    ]
    if not records:
        raise RuntimeError("no ECM exchange files found")
    report = {
        "schema_version": "efe_node1_fenicsx_ecm_equivalence_v01",
        "status": "passed" if all(record["passed"] for record in records) else "failed",
        "evidence_class": "backend_spike_phase_a_not_formal_n1_2_evidence",
        "environment": {
            "python": platform.python_version(),
            "dolfinx": __import__("dolfinx").__version__,
            "petsc": PETSc.Sys.getVersion(),
            "mpi_size": MPI.COMM_WORLD.size,
        },
        "cases": records,
        "boundary": (
            "This result verifies ECM energy/residual field evaluation only. "
            "It does not yet verify a coupled DCM-FEM equilibrium solve, KKT, "
            "global shortening, or production-backend speedup."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("FEniCSx ECM equivalence gate failed")


if __name__ == "__main__":
    main()
