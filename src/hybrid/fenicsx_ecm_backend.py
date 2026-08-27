"""Reusable DOLFINx backend for the owned finite-strain ECM energy.

The module is imported only in the pinned FEniCSx container.  Its public
``energy_force`` method intentionally matches ``route_h.ecm_finite_strain`` so
the existing DCM/interface mechanics can be exercised without changing the
scientific model.
"""

from __future__ import annotations

import time

import basix.ufl
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fem_petsc
from mpi4py import MPI
import numpy as np
from numpy.typing import NDArray
from petsc4py import PETSc
from scipy.sparse import csr_matrix
import ufl

from route_h.ecm_finite_strain import ECMReference


FloatArray = NDArray[np.float64]


def _coordinate_key(coordinate: FloatArray) -> tuple[float, float, float]:
    return tuple(np.round(coordinate, decimals=13).tolist())


class FenicsxECMBackend:
    """Cached serial UFL assembly of the project's exact ECM functional."""

    def __init__(self, reference: ECMReference) -> None:
        if MPI.COMM_WORLD.size != 1:
            raise RuntimeError("the controlled backend spike is serial")
        self._reference = reference
        self._evaluation_count = 0
        self._assembly_seconds = 0.0
        self._tangent_count = 0
        self._tangent_seconds = 0.0
        self._tangent_setup_seconds = 0.0
        self._setup_started = time.perf_counter()

        coordinate_element = basix.ufl.element(
            "Lagrange", "tetrahedron", 1, shape=(3,)
        )
        ufl_domain = ufl.Mesh(coordinate_element)
        self._domain = mesh.create_mesh(
            MPI.COMM_WORLD,
            np.asarray(reference.tetrahedra, dtype=np.int64),
            ufl_domain,
            np.asarray(reference.vertices, dtype=np.float64),
        )
        self._displacement_space = fem.functionspace(
            self._domain, ("Lagrange", 1, (3,))
        )
        self._displacement = fem.Function(self._displacement_space)
        self._input_vertex_ids = self._map_vertex_blocks()
        self._input_cell_ids = self._original_cell_ids()

        self._z_space = fem.functionspace(self._domain, ("DG", 0))
        self._z_components = tuple(
            tuple(fem.Function(self._z_space) for _ in range(3))
            for _ in range(3)
        )
        self._cached_internal_z: FloatArray | None = None
        z_field = ufl.as_tensor(self._z_components)

        self._mu_eq = fem.Constant(self._domain, PETSc.ScalarType(1.0))
        self._kappa_eq = fem.Constant(self._domain, PETSc.ScalarType(20.0))
        self._mu_ve = fem.Constant(self._domain, PETSc.ScalarType(0.5))
        identity = ufl.Identity(3)
        deformation = identity + ufl.grad(self._displacement)
        determinant = ufl.det(deformation)
        right_cauchy_green = deformation.T * deformation
        c_bar = determinant ** (-2.0 / 3.0) * right_cauchy_green
        q_tensor = ufl.dev(c_bar) - z_field
        equilibrium_density = 0.5 * self._mu_eq * (ufl.tr(c_bar) - 3.0) + 0.5 * self._kappa_eq * ufl.ln(
            determinant
        ) ** 2
        viscoelastic_density = 0.25 * self._mu_ve * ufl.inner(
            q_tensor, q_tensor
        )
        integration = ufl.Measure(
            "dx", domain=self._domain, metadata={"quadrature_degree": 1}
        )
        self._equilibrium_form = fem.form(equilibrium_density * integration)
        self._viscoelastic_form = fem.form(viscoelastic_density * integration)
        total_energy = (equilibrium_density + viscoelastic_density) * integration
        test_function = ufl.TestFunction(self._displacement_space)
        residual = ufl.derivative(
            total_energy, self._displacement, test_function
        )
        self._residual_expression = residual
        self._residual_form = fem.form(residual)
        self._tangent_form = None
        self._setup_seconds = time.perf_counter() - self._setup_started

    def _map_vertex_blocks(self) -> NDArray[np.int64]:
        if self._displacement_space.dofmap.bs != 3:
            raise RuntimeError("expected a blocked three-component P1 space")
        coordinate_to_input = {
            _coordinate_key(coordinate): vertex_id
            for vertex_id, coordinate in enumerate(self._reference.vertices)
        }
        dof_coordinates = self._displacement_space.tabulate_dof_coordinates()
        input_ids = np.empty(len(dof_coordinates), dtype=np.int64)
        for block_id, coordinate in enumerate(dof_coordinates):
            try:
                input_ids[block_id] = coordinate_to_input[
                    _coordinate_key(coordinate)
                ]
            except KeyError as error:
                raise RuntimeError(
                    f"unmatched DOLFINx node {coordinate}"
                ) from error
        if len(input_ids) != len(self._reference.vertices):
            raise RuntimeError("unexpected serial DOLFINx vertex count")
        if len(np.unique(input_ids)) != len(input_ids):
            raise RuntimeError("DOLFINx/input vertex map is not one-to-one")
        return input_ids

    def _original_cell_ids(self) -> NDArray[np.int64]:
        original = getattr(self._domain.topology, "original_cell_index", None)
        if original is None:
            raise RuntimeError("DOLFINx did not expose original_cell_index")
        input_ids = np.asarray(original, dtype=np.int64)
        if len(input_ids) != len(self._reference.tetrahedra):
            raise RuntimeError("unexpected serial DOLFINx cell count")
        if len(np.unique(input_ids)) != len(input_ids):
            raise RuntimeError("DOLFINx/input cell map is not one-to-one")
        return input_ids

    def _assign_displacement(self, vertices: FloatArray) -> None:
        displacement = vertices - self._reference.vertices
        for block_id, input_id in enumerate(self._input_vertex_ids):
            self._displacement.x.array[
                3 * block_id : 3 * block_id + 3
            ] = displacement[input_id]
        self._displacement.x.scatter_forward()

    def _assign_internal_z(self, internal_z: FloatArray) -> None:
        if (
            self._cached_internal_z is not None
            and np.array_equal(internal_z, self._cached_internal_z)
        ):
            return
        for row in range(3):
            for column in range(3):
                coefficient = self._z_components[row][column]
                for local_cell, input_cell in enumerate(self._input_cell_ids):
                    dofs = self._z_space.dofmap.cell_dofs(local_cell)
                    if len(dofs) != 1:
                        raise RuntimeError("DG0 must have one scalar dof per cell")
                    coefficient.x.array[dofs[0]] = internal_z[
                        input_cell, row, column
                    ]
                coefficient.x.scatter_forward()
        self._cached_internal_z = internal_z.copy()

    def _force_to_input_order(self, residual: PETSc.Vec) -> FloatArray:
        with residual.localForm() as local:
            flat = np.asarray(local.array, dtype=np.float64).copy()
        if len(flat) != 3 * len(self._input_vertex_ids):
            raise RuntimeError("unexpected blocked residual length")
        force = np.empty_like(self._reference.vertices)
        for block_id, input_id in enumerate(self._input_vertex_ids):
            force[input_id] = -flat[3 * block_id : 3 * block_id + 3]
        return force

    def _jacobians(self, vertices: FloatArray) -> FloatArray:
        local = vertices[self._reference.tetrahedra]
        current_edges = np.stack(
            (
                local[:, 1] - local[:, 0],
                local[:, 2] - local[:, 0],
                local[:, 3] - local[:, 0],
            ),
            axis=2,
        )
        deformation = np.einsum(
            "tij,tjk->tik", current_edges, self._reference.dm_inverse
        )
        return np.linalg.det(deformation)

    def _prepare_state(
        self,
        vertices: FloatArray,
        reference: ECMReference,
        internal_z: FloatArray | None,
        *,
        mu_eq: float,
        kappa_eq: float,
        mu_ve: float,
    ) -> tuple[FloatArray, FloatArray]:
        vertices = np.asarray(vertices, dtype=np.float64)
        if vertices.shape != self._reference.vertices.shape:
            raise ValueError("invalid ECM vertex shape")
        if (
            reference is not self._reference
            and (
                not np.array_equal(reference.vertices, self._reference.vertices)
                or not np.array_equal(
                    reference.tetrahedra, self._reference.tetrahedra
                )
            )
        ):
            raise ValueError("backend called with a different ECM reference")
        selected_z = (
            np.zeros(
                (len(self._reference.tetrahedra), 3, 3), dtype=np.float64
            )
            if internal_z is None
            else np.asarray(internal_z, dtype=np.float64)
        )
        if selected_z.shape != (len(self._reference.tetrahedra), 3, 3):
            raise ValueError("invalid ECM internal-variable shape")
        if not np.allclose(
            selected_z, selected_z.transpose(0, 2, 1), atol=1e-12
        ):
            raise ValueError("ECM Z must be symmetric")
        if np.max(
            np.abs(np.trace(selected_z, axis1=1, axis2=2))
        ) > 1.0e-12:
            raise ValueError("ECM Z must be traceless")

        jacobians = self._jacobians(vertices)
        if float(jacobians.min()) <= 0.0:
            raise ValueError("ECM J must remain strictly positive")
        self._assign_displacement(vertices)
        self._assign_internal_z(selected_z)
        self._mu_eq.value = PETSc.ScalarType(mu_eq)
        self._kappa_eq.value = PETSc.ScalarType(kappa_eq)
        self._mu_ve.value = PETSc.ScalarType(mu_ve)
        return vertices, jacobians

    def _matrix_to_input_order(self, matrix: PETSc.Mat) -> csr_matrix:
        row_offsets, column_ids, values = matrix.getValuesCSR()
        local = csr_matrix(
            (
                np.asarray(values, dtype=np.float64).copy(),
                np.asarray(column_ids, dtype=np.int64).copy(),
                np.asarray(row_offsets, dtype=np.int64).copy(),
            ),
            shape=matrix.getSize(),
        )
        dolfinx_to_input = np.empty(3 * len(self._input_vertex_ids), dtype=np.int64)
        for block_id, input_id in enumerate(self._input_vertex_ids):
            for component in range(3):
                dolfinx_to_input[3 * block_id + component] = (
                    3 * input_id + component
                )
        coordinate = local.tocoo()
        return csr_matrix(
            (
                coordinate.data,
                (
                    dolfinx_to_input[coordinate.row],
                    dolfinx_to_input[coordinate.col],
                ),
            ),
            shape=local.shape,
        )

    def energy_force(
        self,
        vertices: FloatArray,
        reference: ECMReference,
        internal_z: FloatArray | None = None,
        *,
        mu_eq: float = 1.0,
        kappa_eq: float = 20.0,
        mu_ve: float = 0.5,
    ) -> tuple[dict[str, float], FloatArray, FloatArray]:
        """Match ``ecm_energy_force`` using cached UFL forms and AD residuals."""
        _, jacobians = self._prepare_state(
            vertices,
            reference,
            internal_z,
            mu_eq=mu_eq,
            kappa_eq=kappa_eq,
            mu_ve=mu_ve,
        )

        started = time.perf_counter()
        equilibrium = float(fem.assemble_scalar(self._equilibrium_form))
        viscoelastic = float(fem.assemble_scalar(self._viscoelastic_form))
        residual = fem_petsc.assemble_vector(self._residual_form)
        residual.ghostUpdate(
            addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE
        )
        force = self._force_to_input_order(residual)
        self._assembly_seconds += time.perf_counter() - started
        self._evaluation_count += 1
        return (
            {
                "ecm_equilibrium": equilibrium,
                "ecm_viscoelastic": viscoelastic,
                "ecm_total": equilibrium + viscoelastic,
            },
            force,
            jacobians,
        )

    def energy_hessian(
        self,
        vertices: FloatArray,
        reference: ECMReference,
        internal_z: FloatArray | None = None,
        *,
        mu_eq: float = 1.0,
        kappa_eq: float = 20.0,
        mu_ve: float = 0.5,
    ) -> csr_matrix:
        """Assemble the AD Hessian of stored energy in input-node ordering."""
        self._prepare_state(
            vertices,
            reference,
            internal_z,
            mu_eq=mu_eq,
            kappa_eq=kappa_eq,
            mu_ve=mu_ve,
        )
        if self._tangent_form is None:
            setup_started = time.perf_counter()
            trial_function = ufl.TrialFunction(self._displacement_space)
            tangent_expression = ufl.derivative(
                self._residual_expression,
                self._displacement,
                trial_function,
            )
            self._tangent_form = fem.form(tangent_expression)
            self._tangent_setup_seconds += (
                time.perf_counter() - setup_started
            )
        started = time.perf_counter()
        tangent = fem_petsc.assemble_matrix(self._tangent_form)
        tangent.assemble()
        result = self._matrix_to_input_order(tangent)
        self._tangent_seconds += time.perf_counter() - started
        self._tangent_count += 1
        return result

    def diagnostics(self) -> dict[str, float | int | str]:
        """Return non-scientific backend timing and environment metadata."""
        mean = (
            self._assembly_seconds / self._evaluation_count
            if self._evaluation_count
            else 0.0
        )
        tangent_mean = (
            self._tangent_seconds / self._tangent_count
            if self._tangent_count
            else 0.0
        )
        return {
            "backend": "fenicsx_ufl_ad_serial_v02_lazy_tangent",
            "dolfinx_version": __import__("dolfinx").__version__,
            "petsc_version": ".".join(str(value) for value in PETSc.Sys.getVersion()),
            "setup_and_jit_seconds": self._setup_seconds,
            "evaluation_count": self._evaluation_count,
            "assembly_seconds": self._assembly_seconds,
            "mean_assembly_seconds": mean,
            "tangent_count": self._tangent_count,
            "tangent_setup_and_jit_seconds": self._tangent_setup_seconds,
            "tangent_seconds": self._tangent_seconds,
            "mean_tangent_seconds": tangent_mean,
        }
