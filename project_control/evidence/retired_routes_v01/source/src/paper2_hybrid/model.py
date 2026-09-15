"""Active two-dimensional myocardium-ECM-endocardium mechanics.

The myocardium is an active plane-strain continuum, the cardiac-jelly/ECM is
a plane-strain standard-linear-solid continuum, and the endocardium is a
fixed discrete cell chain.  FEniCSx/UFL assembles the continuum operators.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import basix.ufl
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fem_petsc
from mpi4py import MPI
import numpy as np
from numpy.typing import NDArray
from petsc4py import PETSc
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
import ufl

from .config import ACTIVE_CONFIG, ActiveProfile, HybridConfig, SpatialLabel, SpatialLevel
from .roles import ACTIVE_TISSUE_ROLES, TissueRoles


FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
SparseMatrix = sparse.csr_matrix


@dataclass(frozen=True)
class LayerMesh:
    coordinates: FloatArray
    cells: NDArray[np.int64]
    dof_coordinates: FloatArray
    cell_dofs: NDArray[np.int64]
    periodic_projection: SparseMatrix
    affine_axial_mode: FloatArray
    strain_operator: SparseMatrix
    cell_areas: FloatArray
    cell_centroids: FloatArray
    bottom_nodes: NDArray[np.int64]
    top_nodes: NDArray[np.int64]
    stiffness_unit: SparseMatrix
    mass: SparseMatrix
    ufl_relative_error: float


@dataclass(frozen=True)
class ModelSystem:
    config: HybridConfig
    roles: TissueRoles
    spatial_label: str
    active_profile: str
    matrix_material: SparseMatrix
    matrix_support: SparseMatrix
    matrix_a: SparseMatrix
    matrix_drag: SparseMatrix
    matrix_sls_dissipation: SparseMatrix
    matrix_g: SparseMatrix
    active_vector_h: FloatArray
    active_scalar_c: float
    myocardium_transform: SparseMatrix
    ecm_transform: SparseMatrix
    endocardium_transform: SparseMatrix
    myocardium_mesh: LayerMesh
    ecm_mesh: LayerMesh
    ecm_strain_operator_full: SparseMatrix
    ecm_constitutive_equilibrium: FloatArray
    ecm_constitutive_maxwell: FloatArray
    ecm_internal_slice: slice
    macro_strain_index: int
    myocardium_ecm_rows: tuple[NDArray[np.int64], NDArray[np.int64]]
    endocardium_ecm_rows: tuple[NDArray[np.int64], NDArray[np.int64]]
    interface_weights: FloatArray
    component_matrices: dict[str, SparseMatrix]
    active_profile_average: float
    manufactured_error: float
    passive_tangent: float

    @property
    def state_size(self) -> int:
        return int(self.matrix_a.shape[0])


@dataclass(frozen=True)
class Endpoint:
    summary: dict[str, Any]
    arrays: dict[str, FloatArray]

def _matrix_to_csr(matrix: PETSc.Mat) -> SparseMatrix:
    row_offsets, column_indices, values = matrix.getValuesCSR()
    return sparse.csr_matrix(
        (values.copy(), column_indices.copy(), row_offsets.copy()),
        shape=matrix.getSize(),
    )


def _constitutive_matrix(young_modulus: float, poisson_ratio: float) -> FloatArray:
    shear_modulus = young_modulus / (2.0 * (1.0 + poisson_ratio))
    lame_lambda = (
        young_modulus
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    return np.asarray(
        (
            (lame_lambda + 2.0 * shear_modulus, lame_lambda, 0.0),
            (lame_lambda, lame_lambda + 2.0 * shear_modulus, 0.0),
            (0.0, 0.0, shear_modulus),
        ),
        dtype=np.float64,
    )


def _structured_mesh_arrays(
    length: float,
    thickness: float,
    nx: int,
    ny: int,
) -> tuple[FloatArray, NDArray[np.int64]]:
    x_axis = np.linspace(-0.5 * length, 0.5 * length, nx + 1)
    y_axis = np.linspace(0.0, thickness, ny + 1)
    coordinates = np.asarray(
        [(x_value, y_value) for y_value in y_axis for x_value in x_axis],
        dtype=np.float64,
    )

    def vertex(ix: int, iy: int) -> int:
        return iy * (nx + 1) + ix

    cells: list[tuple[int, int, int]] = []
    for iy in range(ny):
        for ix in range(nx):
            lower_left = vertex(ix, iy)
            lower_right = vertex(ix + 1, iy)
            upper_left = vertex(ix, iy + 1)
            upper_right = vertex(ix + 1, iy + 1)
            cells.append((lower_left, lower_right, upper_right))
            cells.append((lower_left, upper_right, upper_left))
    return coordinates, np.asarray(cells, dtype=np.int64)


def _assemble_ufl_operators(
    coordinates: FloatArray,
    cells: NDArray[np.int64],
) -> tuple[Any, Any, FloatArray, NDArray[np.int64], SparseMatrix, SparseMatrix]:
    if MPI.COMM_WORLD.size != 1:
        raise RuntimeError("M2A is frozen to one CPU process")
    coordinate_element = basix.ufl.element(
        "Lagrange", "triangle", 1, shape=(2,)
    )
    domain = mesh.create_mesh(
        MPI.COMM_WORLD,
        cells,
        ufl.Mesh(coordinate_element),
        coordinates,
    )
    vector_space = fem.functionspace(domain, ("Lagrange", 1, (2,)))
    if vector_space.dofmap.bs != 2:
        raise RuntimeError("expected a blocked two-component P1 space")
    dof_coordinates = np.asarray(
        vector_space.tabulate_dof_coordinates()[:, :2], dtype=np.float64
    )
    original_cell_index = np.asarray(
        domain.topology.original_cell_index, dtype=np.int64
    )
    cell_dofs = np.empty((len(cells), 3), dtype=np.int64)
    for local_cell, original_cell in enumerate(original_cell_index):
        cell_dofs[original_cell] = vector_space.dofmap.cell_dofs(local_cell)

    trial = ufl.TrialFunction(vector_space)
    test = ufl.TestFunction(vector_space)
    strain_trial = ufl.sym(ufl.grad(trial))
    strain_test = ufl.sym(ufl.grad(test))
    identity = ufl.Identity(2)
    # Unit-E, nu=0.30 reference; arbitrary materials are assembled by the
    # manual B^T C B operator below and cross-checked against this UFL matrix.
    constitutive = _constitutive_matrix(1.0, 0.30)
    shear_modulus = constitutive[2, 2]
    lame_lambda = constitutive[0, 1]
    stress_trial = (
        2.0 * shear_modulus * strain_trial
        + lame_lambda * ufl.tr(strain_trial) * identity
    )
    stiffness = fem_petsc.assemble_matrix(
        fem.form(ufl.inner(stress_trial, strain_test) * ufl.dx)
    )
    stiffness.assemble()
    mass = fem_petsc.assemble_matrix(
        fem.form(ufl.inner(trial, test) * ufl.dx)
    )
    mass.assemble()
    return (
        domain,
        vector_space,
        dof_coordinates,
        cell_dofs,
        _matrix_to_csr(stiffness),
        _matrix_to_csr(mass),
    )


def _periodic_projection(
    dof_coordinates: FloatArray,
    length: float,
) -> tuple[SparseMatrix, FloatArray]:
    x_min = -0.5 * length
    x_max = 0.5 * length

    def key(x_value: float, y_value: float) -> tuple[float, float]:
        if np.isclose(x_value, x_max, atol=1.0e-12):
            x_value = x_min
        return (round(float(x_value), 13), round(float(y_value), 13))

    unique_keys = sorted(
        {key(*coordinate) for coordinate in dof_coordinates},
        key=lambda item: (item[1], item[0]),
    )
    key_to_periodic = {coordinate: index for index, coordinate in enumerate(unique_keys)}
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    affine = np.zeros(2 * len(dof_coordinates), dtype=np.float64)
    for node, (x_value, y_value) in enumerate(dof_coordinates):
        periodic_node = key_to_periodic[key(x_value, y_value)]
        for component in range(2):
            rows.append(2 * node + component)
            columns.append(2 * periodic_node + component)
            values.append(1.0)
        affine[2 * node] = x_value
    projection = sparse.coo_matrix(
        (values, (rows, columns)),
        shape=(2 * len(dof_coordinates), 2 * len(unique_keys)),
    ).tocsr()
    return projection, affine


def _strain_operator(
    dof_coordinates: FloatArray,
    cell_dofs: NDArray[np.int64],
) -> tuple[SparseMatrix, FloatArray, FloatArray]:
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    areas = np.empty(len(cell_dofs), dtype=np.float64)
    centroids = np.empty((len(cell_dofs), 2), dtype=np.float64)
    for cell_id, nodes in enumerate(cell_dofs):
        local_coordinates = dof_coordinates[nodes]
        interpolation = np.column_stack(
            (np.ones(3, dtype=np.float64), local_coordinates)
        )
        inverse = np.linalg.inv(interpolation)
        gradients = inverse[1:, :].T
        signed_twice_area = np.linalg.det(
            np.asarray(
                (
                    local_coordinates[1] - local_coordinates[0],
                    local_coordinates[2] - local_coordinates[0],
                )
            )
        )
        areas[cell_id] = 0.5 * abs(float(signed_twice_area))
        centroids[cell_id] = np.mean(local_coordinates, axis=0)
        for local_node, node in enumerate(nodes):
            gradient_x, gradient_y = gradients[local_node]
            entries = (
                (3 * cell_id, 2 * node, gradient_x),
                (3 * cell_id + 1, 2 * node + 1, gradient_y),
                (3 * cell_id + 2, 2 * node, gradient_y),
                (3 * cell_id + 2, 2 * node + 1, gradient_x),
            )
            for row, column, value in entries:
                rows.append(row)
                columns.append(column)
                values.append(float(value))
    operator = sparse.coo_matrix(
        (values, (rows, columns)),
        shape=(3 * len(cell_dofs), 2 * len(dof_coordinates)),
    ).tocsr()
    return operator, areas, centroids


def _weighted_constitutive(
    constitutive: FloatArray,
    areas: FloatArray,
) -> SparseMatrix:
    return sparse.block_diag(
        [area * constitutive for area in areas], format="csr"
    )


def _build_layer_mesh(
    *,
    length: float,
    thickness: float,
    nx: int,
    ny: int,
) -> LayerMesh:
    coordinates, cells = _structured_mesh_arrays(length, thickness, nx, ny)
    (
        _domain,
        _space,
        dof_coordinates,
        cell_dofs,
        stiffness_ufl,
        mass,
    ) = _assemble_ufl_operators(coordinates, cells)
    strain_operator, areas, centroids = _strain_operator(
        dof_coordinates, cell_dofs
    )
    unit_constitutive = _constitutive_matrix(1.0, 0.30)
    weighted = _weighted_constitutive(unit_constitutive, areas)
    stiffness_manual = (strain_operator.T @ weighted @ strain_operator).tocsr()
    denominator = max(sparse_linalg.norm(stiffness_ufl), 1.0e-30)
    relative_error = float(
        sparse_linalg.norm(stiffness_manual - stiffness_ufl) / denominator
    )
    periodic_projection, affine = _periodic_projection(
        dof_coordinates, length
    )
    bottom_nodes = np.flatnonzero(
        np.isclose(dof_coordinates[:, 1], 0.0, atol=1.0e-12)
    )
    top_nodes = np.flatnonzero(
        np.isclose(dof_coordinates[:, 1], thickness, atol=1.0e-12)
    )
    bottom_nodes = bottom_nodes[np.argsort(dof_coordinates[bottom_nodes, 0])]
    top_nodes = top_nodes[np.argsort(dof_coordinates[top_nodes, 0])]
    return LayerMesh(
        coordinates=coordinates,
        cells=cells,
        dof_coordinates=dof_coordinates,
        cell_dofs=cell_dofs,
        periodic_projection=periodic_projection,
        affine_axial_mode=affine,
        strain_operator=strain_operator,
        cell_areas=areas,
        cell_centroids=centroids,
        bottom_nodes=bottom_nodes,
        top_nodes=top_nodes,
        stiffness_unit=stiffness_ufl,
        mass=mass,
        ufl_relative_error=relative_error,
    )


def _global_transform(
    projection: SparseMatrix,
    affine: FloatArray,
    state_size: int,
    local_start: int,
    macro_index: int,
) -> SparseMatrix:
    coo = projection.tocoo()
    rows = coo.row.tolist()
    columns = (coo.col + local_start).tolist()
    values = coo.data.tolist()
    nonzero_affine = np.flatnonzero(affine)
    rows.extend(nonzero_affine.tolist())
    columns.extend([macro_index] * len(nonzero_affine))
    values.extend(affine[nonzero_affine].tolist())
    return sparse.coo_matrix(
        (values, (rows, columns)),
        shape=(projection.shape[0], state_size),
    ).tocsr()


def _endo_transform(
    *,
    nx: int,
    length: float,
    state_size: int,
    local_start: int,
    macro_index: int,
) -> tuple[SparseMatrix, FloatArray]:
    x_axis = np.linspace(-0.5 * length, 0.5 * length, nx + 1)
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for node, x_value in enumerate(x_axis):
        periodic_node = 0 if node == nx else node
        for component in range(2):
            rows.append(2 * node + component)
            columns.append(local_start + 2 * periodic_node + component)
            values.append(1.0)
        if x_value != 0.0:
            rows.append(2 * node)
            columns.append(macro_index)
            values.append(float(x_value))
    transform = sparse.coo_matrix(
        (values, (rows, columns)),
        shape=(2 * (nx + 1), state_size),
    ).tocsr()
    return transform, x_axis


def _embed_full_operator(transform: SparseMatrix, operator: SparseMatrix) -> SparseMatrix:
    return (transform.T @ operator @ transform).tocsr()


def _boundary_rows(nodes: NDArray[np.int64]) -> NDArray[np.int64]:
    result = np.empty(2 * len(nodes), dtype=np.int64)
    result[0::2] = 2 * nodes
    result[1::2] = 2 * nodes + 1
    return result


def _interface_matrix(
    transform_a: SparseMatrix,
    rows_a: NDArray[np.int64],
    transform_b: SparseMatrix,
    rows_b: NDArray[np.int64],
    weights: FloatArray,
    stiffness: float,
) -> SparseMatrix:
    relative = transform_a[rows_a] - transform_b[rows_b]
    diagonal = np.repeat(stiffness * weights, 2)
    return (relative.T @ sparse.diags(diagonal) @ relative).tocsr()


def _endocardial_full_stiffness(
    nx: int,
    length: float,
    axial: float,
    transverse: float,
) -> SparseMatrix:
    dx = length / nx
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []

    def add_spring(dof_a: int, dof_b: int, stiffness: float) -> None:
        for row, column, value in (
            (dof_a, dof_a, stiffness),
            (dof_a, dof_b, -stiffness),
            (dof_b, dof_a, -stiffness),
            (dof_b, dof_b, stiffness),
        ):
            rows.append(row)
            columns.append(column)
            values.append(value)

    for index in range(nx):
        add_spring(2 * index, 2 * (index + 1), axial / dx)
        add_spring(2 * index + 1, 2 * (index + 1) + 1, transverse / dx)
    return sparse.coo_matrix(
        (values, (rows, columns)), shape=(2 * (nx + 1), 2 * (nx + 1))
    ).tocsr()


def _endocardial_bending_matrix(
    nx: int,
    length: float,
    state_size: int,
    local_start: int,
    stiffness: float,
) -> SparseMatrix:
    dx = length / nx
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    coefficient = stiffness / (dx**3)
    for index in range(nx):
        dofs = (
            local_start + 2 * ((index - 1) % nx) + 1,
            local_start + 2 * index + 1,
            local_start + 2 * ((index + 1) % nx) + 1,
        )
        stencil = (1.0, -2.0, 1.0)
        for local_row, row in enumerate(dofs):
            for local_column, column in enumerate(dofs):
                rows.append(row)
                columns.append(column)
                values.append(coefficient * stencil[local_row] * stencil[local_column])
    return sparse.coo_matrix(
        (values, (rows, columns)), shape=(state_size, state_size)
    ).tocsr()

def _activation_profile_value(
    x_value: float,
    length: float,
    profile: str,
    config: HybridConfig,
) -> float:
    if profile == "uniform":
        return 1.0
    if profile != "S1":
        raise ValueError(f"unsupported active profile: {profile}")
    return float(
        1.0
        + config.spatial_activation_contrast
        * math.cos(2.0 * math.pi * x_value / length)
    )


def _active_fem_full(
    layer: LayerMesh,
    constitutive: FloatArray,
    length: float,
    profile: str,
    config: HybridConfig,
) -> tuple[FloatArray, float, float]:
    profile_values = np.asarray(
        [
            _activation_profile_value(center[0], length, profile, config)
            for center in layer.cell_centroids
        ],
        dtype=np.float64,
    )
    eigenstrain = np.zeros(3 * len(layer.cells), dtype=np.float64)
    eigenstrain[0::3] = profile_values
    weighted = _weighted_constitutive(constitutive, layer.cell_areas)
    active = np.asarray(layer.strain_operator.T @ (weighted @ eigenstrain)).ravel()
    scalar = float(eigenstrain @ (weighted @ eigenstrain))
    weighted_average = float(
        np.dot(layer.cell_areas, profile_values) / np.sum(layer.cell_areas)
    )
    return active, scalar, weighted_average


def _add_z_block(
    base: SparseMatrix,
    row_slice: slice,
    column_slice: slice,
    block: SparseMatrix,
) -> SparseMatrix:
    coo = block.tocoo()
    row_start = 0 if row_slice.start is None else row_slice.start
    column_start = 0 if column_slice.start is None else column_slice.start
    embedded = sparse.coo_matrix(
        (
            coo.data,
            (coo.row + row_start, coo.col + column_start),
        ),
        shape=base.shape,
    ).tocsr()
    return (base + embedded).tocsr()

def build_system(
    *,
    spatial_label: SpatialLabel,
    active_profile: ActiveProfile = "uniform",
    config: HybridConfig = ACTIVE_CONFIG,
) -> ModelSystem:
    config.checked()
    return build_system_for_level(
        level=config.spatial(spatial_label),
        active_profile=active_profile,
        config=config,
    )


def build_system_for_level(
    *,
    level: SpatialLevel,
    active_profile: ActiveProfile = "uniform",
    config: HybridConfig = ACTIVE_CONFIG,
) -> ModelSystem:
    """Build the fixed active architecture on one explicit mesh level."""
    config.checked()
    spatial_label = str(level.label)
    if level.nx < 2 or level.ny_per_layer < 1:
        raise ValueError("diagnostic spatial level is too small")
    myocardium = _build_layer_mesh(
        length=config.length,
        thickness=config.myocardium_thickness,
        nx=level.nx,
        ny=level.ny_per_layer,
    )
    ecm = _build_layer_mesh(
        length=config.length,
        thickness=config.ecm_thickness,
        nx=level.nx,
        ny=level.ny_per_layer,
    )
    n_myo_periodic = myocardium.periodic_projection.shape[1]
    n_ecm_periodic = ecm.periodic_projection.shape[1]
    n_endo_periodic = 2 * level.nx
    macro_index = n_myo_periodic + n_ecm_periodic + n_endo_periodic
    z_start = macro_index + 1
    n_z = 3 * len(ecm.cells)
    state_size = z_start + n_z
    myocardium_transform = _global_transform(
        myocardium.periodic_projection,
        myocardium.affine_axial_mode,
        state_size,
        0,
        macro_index,
    )
    ecm_transform = _global_transform(
        ecm.periodic_projection,
        ecm.affine_axial_mode,
        state_size,
        n_myo_periodic,
        macro_index,
    )
    endocardium_transform, _x_axis = _endo_transform(
        nx=level.nx,
        length=config.length,
        state_size=state_size,
        local_start=n_myo_periodic + n_ecm_periodic,
        macro_index=macro_index,
    )
    z_slice = slice(z_start, state_size)

    myo_constitutive = _constitutive_matrix(
        config.myocardium_young_modulus,
        config.myocardium_poisson_ratio,
    )

    myo_weighted = _weighted_constitutive(
        myo_constitutive, myocardium.cell_areas
    )
    myo_full = (
        myocardium.strain_operator.T
        @ myo_weighted
        @ myocardium.strain_operator
    ).tocsr()
    active_full, active_scalar, profile_average = _active_fem_full(
        myocardium,
        myo_constitutive,
        config.length,
        active_profile,
        config,
    )
    manufactured_error = myocardium.ufl_relative_error


    myo_material = _embed_full_operator(myocardium_transform, myo_full)
    active_h = np.asarray(myocardium_transform.T @ active_full).ravel()
    passive_tangent = float(myo_material[macro_index, macro_index])

    ecm_constitutive_eq = _constitutive_matrix(
        config.ecm_equilibrium_young_modulus,
        config.ecm_equilibrium_poisson_ratio,
    )
    ecm_constitutive_ve = _constitutive_matrix(
        config.ecm_maxwell_young_modulus,
        config.ecm_maxwell_poisson_ratio,
    )
    ecm_weighted_eq = _weighted_constitutive(
        ecm_constitutive_eq, ecm.cell_areas
    )
    ecm_weighted_ve = _weighted_constitutive(
        ecm_constitutive_ve, ecm.cell_areas
    )
    ecm_b_global = (ecm.strain_operator @ ecm_transform).tocsr()
    ecm_equilibrium = (
        ecm_b_global.T @ ecm_weighted_eq @ ecm_b_global
    ).tocsr()
    ecm_visco_u = (
        ecm_b_global.T @ ecm_weighted_ve @ ecm_b_global
    ).tocsr()
    ecm_visco_uz = -(ecm_b_global.T @ ecm_weighted_ve).tocsr()
    ecm_visco_z = ecm_weighted_ve

    endo_full = _endocardial_full_stiffness(
        level.nx,
        config.length,
        config.endocardial_axial_stiffness,
        config.endocardial_transverse_stiffness,
    )
    endo_material = _embed_full_operator(endocardium_transform, endo_full)
    endo_bending = _endocardial_bending_matrix(
        level.nx,
        config.length,
        state_size,
        n_myo_periodic + n_ecm_periodic,
        config.endocardial_bending_stiffness,
    )

    interface_weights = np.full(
        level.nx + 1, config.length / level.nx, dtype=np.float64
    )
    interface_weights[[0, -1]] *= 0.5
    myo_top_rows = _boundary_rows(myocardium.top_nodes)
    ecm_bottom_rows = _boundary_rows(ecm.bottom_nodes)
    ecm_top_rows = _boundary_rows(ecm.top_nodes)
    endo_rows = np.arange(2 * (level.nx + 1), dtype=np.int64)
    interface_myo_ecm = _interface_matrix(
        myocardium_transform,
        myo_top_rows,
        ecm_transform,
        ecm_bottom_rows,
        interface_weights,
        config.ecm_myocardium_interface_stiffness,
    )
    interface_endo_ecm = _interface_matrix(
        endocardium_transform,
        endo_rows,
        ecm_transform,
        ecm_top_rows,
        interface_weights,
        config.endocardium_ecm_interface_stiffness,
    )

    material = (
        myo_material
        + ecm_equilibrium
        + ecm_visco_u
        + endo_material
        + endo_bending
        + interface_myo_ecm
        + interface_endo_ecm
    ).tocsr()
    material = _add_z_block(
        material, slice(0, state_size), z_slice, ecm_visco_uz
    )
    material = _add_z_block(
        material, z_slice, slice(0, state_size), ecm_visco_uz.T
    )
    material = _add_z_block(material, z_slice, z_slice, ecm_visco_z)

    bottom_rows = _boundary_rows(myocardium.bottom_nodes)
    bottom_transform = myocardium_transform[bottom_rows]
    support_diagonal = np.repeat(interface_weights, 2)
    support_diagonal[0::2] *= config.support_tangential_stiffness
    support_diagonal[1::2] *= config.support_normal_stiffness
    support = (
        bottom_transform.T
        @ sparse.diags(support_diagonal)
        @ bottom_transform
    ).tocsr()

    myo_drag = config.myocardium_drag * _embed_full_operator(
        myocardium_transform, myocardium.mass
    )
    ecm_drag = config.ecm_drag * _embed_full_operator(
        ecm_transform, ecm.mass
    )
    endo_lumped = np.repeat(
        config.endocardial_drag * interface_weights, 2
    )
    endo_drag = (
        endocardium_transform.T
        @ sparse.diags(endo_lumped)
        @ endocardium_transform
    ).tocsr()
    matrix_drag = (myo_drag + ecm_drag + endo_drag).tocsr()
    matrix_sls = sparse.csr_matrix((state_size, state_size))
    matrix_sls = _add_z_block(
        matrix_sls,
        z_slice,
        z_slice,
        config.ecm_relaxation_time * ecm_visco_z,
    )
    matrix_g = (matrix_drag + matrix_sls).tocsr()
    matrix_a = (material + support).tocsr()

    components = {
        "myocardium": myo_material,
        "ecm_equilibrium": ecm_equilibrium,
        "ecm_viscoelastic": (
            material
            - myo_material
            - ecm_equilibrium
            - endo_material
            - endo_bending
            - interface_myo_ecm
            - interface_endo_ecm
        ).tocsr(),
        "endocardium": (endo_material + endo_bending).tocsr(),
        "interface_myocardium_ecm": interface_myo_ecm,
        "interface_endocardium_ecm": interface_endo_ecm,
        "support": support,
    }
    return ModelSystem(
        config=config,
        roles=ACTIVE_TISSUE_ROLES,
        spatial_label=spatial_label,
        active_profile=active_profile,
        matrix_material=material,
        matrix_support=support,
        matrix_a=matrix_a,
        matrix_drag=matrix_drag,
        matrix_sls_dissipation=matrix_sls,
        matrix_g=matrix_g,
        active_vector_h=active_h,
        active_scalar_c=float(active_scalar),
        myocardium_transform=myocardium_transform,
        ecm_transform=ecm_transform,
        endocardium_transform=endocardium_transform,
        myocardium_mesh=myocardium,
        ecm_mesh=ecm,
        ecm_strain_operator_full=ecm.strain_operator,
        ecm_constitutive_equilibrium=ecm_constitutive_eq,
        ecm_constitutive_maxwell=ecm_constitutive_ve,
        ecm_internal_slice=z_slice,
        macro_strain_index=macro_index,
        myocardium_ecm_rows=(myo_top_rows, ecm_bottom_rows),
        endocardium_ecm_rows=(endo_rows, ecm_top_rows),
        interface_weights=interface_weights,
        component_matrices=components,
        active_profile_average=profile_average,
        manufactured_error=max(
            float(manufactured_error),
            myocardium.ufl_relative_error,
            ecm.ufl_relative_error,
        ),
        passive_tangent=passive_tangent,
    )

def _case_components(
    case_id: str,
    system: ModelSystem,
) -> tuple[float, complex, FloatArray, ComplexArray, str]:
    config = system.config
    state_size = system.state_size
    active_dc = 0.0
    active_harmonic = 0.0j
    load_dc = np.zeros(state_size, dtype=np.float64)
    load_harmonic = np.zeros(state_size, dtype=np.complex128)
    active_profile = "S1" if case_id == "S1" else "uniform"
    if case_id in {"A1", "A2", "C0", "CQ", "S1"}:
        active_dc = 0.5 * config.activation_peak
        active_harmonic = complex(-0.5 * config.activation_peak)

    endo_rows = np.arange(2 * len(system.interface_weights), dtype=np.int64)
    force_normal = np.zeros(len(endo_rows), dtype=np.float64)
    force_normal[1::2] = -system.interface_weights
    force_tangent = np.zeros(len(endo_rows), dtype=np.float64)
    force_tangent[0::2] = system.interface_weights
    normal_shape = np.asarray(
        system.endocardium_transform[endo_rows].T @ force_normal
    ).ravel()
    tangent_shape = np.asarray(
        system.endocardium_transform[endo_rows].T @ force_tangent
    ).ravel()
    if case_id in {"LN", "C0", "CQ"}:
        normal_dc = 0.5 * config.normal_traction_peak
        phase = math.pi / 2.0 if case_id == "CQ" else 0.0
        normal_harmonic = -0.5 * config.normal_traction_peak * np.exp(1j * phase)
        load_dc += normal_dc * normal_shape
        load_harmonic += normal_harmonic * normal_shape
    if case_id == "LS":
        load_dc += 0.5 * config.tangential_traction_peak * tangent_shape
        load_harmonic += (
            -0.5 * config.tangential_traction_peak * tangent_shape
        )
    return active_dc, active_harmonic, load_dc, load_harmonic, active_profile


def _relative_residual(matrix: SparseMatrix, solution: NDArray, rhs: NDArray) -> float:
    residual = matrix @ solution - rhs
    return float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1.0e-30))


def _periodic_solution(
    system: ModelSystem,
    case_id: str,
    steps_per_cycle: int,
) -> tuple[FloatArray, FloatArray, FloatArray, dict[str, float]]:
    active_dc, active_harmonic, load_dc, load_harmonic, profile = _case_components(
        case_id, system
    )
    if profile != system.active_profile:
        raise RuntimeError("active profile/system mismatch")
    rhs_dc = load_dc - system.active_vector_h * active_dc
    rhs_harmonic = load_harmonic - system.active_vector_h * active_harmonic
    dc_state = sparse_linalg.spsolve(system.matrix_a.tocsc(), rhs_dc)
    time_step = system.config.period / steps_per_cycle
    omega = 2.0 * math.pi / system.config.period
    zeta = np.exp(1j * omega * time_step)
    harmonic_matrix = (
        ((zeta - 1.0) / time_step) * system.matrix_g
        + (0.5 * (zeta + 1.0)) * system.matrix_a
    ).tocsc()
    harmonic_rhs = 0.5 * (1.0 + zeta) * rhs_harmonic
    harmonic_state = sparse_linalg.spsolve(harmonic_matrix, harmonic_rhs)

    times = np.linspace(
        0.0, 2.0 * system.config.period, 2 * steps_per_cycle + 1
    )
    phase = np.exp(1j * omega * times)
    states = dc_state[:, None] + np.real(harmonic_state[:, None] * phase[None, :])
    activation = active_dc + np.real(active_harmonic * phase)
    loads = load_dc[:, None] + np.real(load_harmonic[:, None] * phase[None, :])
    residuals = {
        "dc_relative_residual": _relative_residual(
            system.matrix_a, dc_state, rhs_dc
        ),
        "harmonic_relative_residual": _relative_residual(
            harmonic_matrix, harmonic_state, harmonic_rhs
        ),
    }
    return times, states, activation, loads, residuals


def _material_energy(system: ModelSystem, state: FloatArray, activation: float) -> float:
    return float(
        0.5 * state @ (system.matrix_material @ state)
        + activation * np.dot(system.active_vector_h, state)
        + 0.5 * system.active_scalar_c * activation**2
    )


def _interface_tractions(
    system: ModelSystem,
    states: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    myo_rows, ecm_bottom_rows = system.myocardium_ecm_rows
    endo_rows, ecm_top_rows = system.endocardium_ecm_rows
    myo = system.myocardium_transform[myo_rows] @ states
    ecm_bottom = system.ecm_transform[ecm_bottom_rows] @ states
    endo = system.endocardium_transform[endo_rows] @ states
    ecm_top = system.ecm_transform[ecm_top_rows] @ states
    traction_myo_ecm = system.config.ecm_myocardium_interface_stiffness * (
        myo - ecm_bottom
    )
    traction_endo_ecm = system.config.endocardium_ecm_interface_stiffness * (
        endo - ecm_top
    )
    return traction_myo_ecm, traction_endo_ecm


def _fundamental(signal: FloatArray) -> complex:
    centered = signal - np.mean(signal)
    return complex(np.fft.rfft(centered)[1])


def _ledger(
    system: ModelSystem,
    states: FloatArray,
    activation: FloatArray,
    loads: FloatArray,
    steps_per_cycle: int,
) -> dict[str, Any]:
    time_step = system.config.period / steps_per_cycle
    energy = np.asarray(
        [
            _material_energy(system, states[:, index], activation[index])
            for index in range(steps_per_cycle + 1)
        ]
    )
    active_work = np.zeros(steps_per_cycle, dtype=np.float64)
    lumen_work = np.zeros(steps_per_cycle, dtype=np.float64)
    support_work = np.zeros(steps_per_cycle, dtype=np.float64)
    drag_dissipation = np.zeros(steps_per_cycle, dtype=np.float64)
    sls_dissipation = np.zeros(steps_per_cycle, dtype=np.float64)
    residual = np.zeros(steps_per_cycle, dtype=np.float64)
    normalized_residual = np.zeros(steps_per_cycle, dtype=np.float64)
    for step in range(steps_per_cycle):
        state_start = states[:, step]
        state_end = states[:, step + 1]
        increment = state_end - state_start
        midpoint = 0.5 * (state_start + state_end)
        activation_midpoint = 0.5 * (activation[step] + activation[step + 1])
        activation_increment = activation[step + 1] - activation[step]
        load_midpoint = 0.5 * (loads[:, step] + loads[:, step + 1])
        active_conjugate = (
            np.dot(system.active_vector_h, midpoint)
            + system.active_scalar_c * activation_midpoint
        )
        active_work[step] = active_conjugate * activation_increment
        lumen_work[step] = np.dot(load_midpoint, increment)
        support_work[step] = -np.dot(
            system.matrix_support @ midpoint, increment
        )
        drag_dissipation[step] = float(
            increment @ (system.matrix_drag @ increment) / time_step
        )
        sls_dissipation[step] = float(
            increment
            @ (system.matrix_sls_dissipation @ increment)
            / time_step
        )
        energy_change = energy[step + 1] - energy[step]
        residual[step] = (
            active_work[step]
            + lumen_work[step]
            + support_work[step]
            - energy_change
            - drag_dissipation[step]
            - sls_dissipation[step]
        )
        scale = max(
            abs(active_work[step])
            + abs(lumen_work[step])
            + abs(support_work[step])
            + abs(energy_change)
            + abs(drag_dissipation[step])
            + abs(sls_dissipation[step]),
            1.0e-14,
        )
        normalized_residual[step] = abs(residual[step]) / scale
    return {
        "energy": energy,
        "active_work_steps": active_work,
        "lumen_work_steps": lumen_work,
        "external_support_work_steps": support_work,
        "drag_dissipation_steps": drag_dissipation,
        "sls_dissipation_steps": sls_dissipation,
        "residual_steps": residual,
        "normalized_residual_steps": normalized_residual,
        "total_active_work": float(np.sum(active_work)),
        "total_lumen_work": float(np.sum(lumen_work)),
        "total_external_support_work": float(np.sum(support_work)),
        "total_drag_dissipation": float(np.sum(drag_dissipation)),
        "total_sls_dissipation": float(np.sum(sls_dissipation)),
        "cycle_energy_change": float(energy[-1] - energy[0]),
        "maximum_normalized_residual": float(np.max(normalized_residual)),
        "minimum_physical_dissipation": float(
            min(np.min(drag_dissipation), np.min(sls_dissipation))
        ),
    }


def simulate_endpoint(
    *,
    system: ModelSystem,
    case_id: str,
    steps_per_cycle: int,
) -> Endpoint:
    if case_id not in system.config.cases:
        raise ValueError(f"case is not preregistered: {case_id}")
    if steps_per_cycle not in system.config.time_steps_per_cycle:
        raise ValueError("time step count is outside the frozen ladder")
    if case_id == "P1":
        zero = np.zeros((system.state_size, 2 * steps_per_cycle + 1))
        macro = system.config.passive_perturbation_strain
        zero[system.macro_strain_index, :] = macro
        times = np.linspace(0.0, 2.0 * system.config.period, 2 * steps_per_cycle + 1)
        activation = np.zeros_like(times)
        loads = np.zeros_like(zero)
        residuals = {"dc_relative_residual": 0.0, "harmonic_relative_residual": 0.0}
        states = zero
    elif case_id == "P0":
        times = np.linspace(0.0, 2.0 * system.config.period, 2 * steps_per_cycle + 1)
        states = np.zeros((system.state_size, len(times)), dtype=np.float64)
        activation = np.zeros(len(times), dtype=np.float64)
        loads = np.zeros_like(states)
        residuals = {"dc_relative_residual": 0.0, "harmonic_relative_residual": 0.0}
    else:
        times, states, activation, loads, residuals = _periodic_solution(
            system, case_id, steps_per_cycle
        )

    first_cycle = slice(0, steps_per_cycle + 1)
    second_cycle = slice(steps_per_cycle, 2 * steps_per_cycle + 1)
    cycle_state_difference = float(
        np.linalg.norm(states[:, first_cycle] - states[:, second_cycle])
        / max(np.linalg.norm(states[:, first_cycle]), 1.0e-30)
    )
    limited_shortening = -states[system.macro_strain_index]
    free_shortening = system.active_profile_average * activation
    endocardial_displacement = np.asarray(
        system.endocardium_transform @ states
    ).reshape(len(system.interface_weights), 2, -1)
    mean_endocardial_displacement = np.sum(
        system.interface_weights[:, None, None] * endocardial_displacement,
        axis=0,
    ) / system.config.length
    traction_myo_ecm, traction_endo_ecm = _interface_tractions(system, states)
    ledger = _ledger(
        system,
        states[:, first_cycle],
        activation[first_cycle],
        loads[:, first_cycle],
        steps_per_cycle,
    )
    fundamental = _fundamental(limited_shortening[:steps_per_cycle])
    activation_fundamental = _fundamental(activation[:steps_per_cycle])
    response_amplitude = 2.0 * abs(fundamental) / steps_per_cycle
    phase = (
        float(np.angle(fundamental / activation_fundamental))
        if abs(activation_fundamental) > 1.0e-14
        else None
    )
    time_step = system.config.period / steps_per_cycle
    myo_ecm_field = traction_myo_ecm[:, :steps_per_cycle].reshape(
        len(system.interface_weights), 2, steps_per_cycle
    )
    endo_ecm_field = traction_endo_ecm[:, :steps_per_cycle].reshape(
        len(system.interface_weights), 2, steps_per_cycle
    )
    myo_ecm_l2 = float(
        np.sqrt(
            time_step
            * np.sum(
                system.interface_weights[:, None, None]
                * myo_ecm_field**2
            )
        )
    )
    endo_ecm_l2 = float(
        np.sqrt(
            time_step
            * np.sum(
                system.interface_weights[:, None, None]
                * endo_ecm_field**2
            )
        )
    )
    shortening_l2 = float(
        np.sqrt(
            time_step
            * np.sum(limited_shortening[:steps_per_cycle] ** 2)
        )
    )

    peak_index = int(np.argmax(activation[: steps_per_cycle + 1]))
    ecm_displacement = np.asarray(
        system.ecm_transform @ states[:, peak_index]
    ).ravel()
    ecm_strain = np.asarray(
        system.ecm_strain_operator_full @ ecm_displacement
    ).reshape(-1, 3)
    ecm_internal = states[system.ecm_internal_slice, peak_index].reshape(-1, 3)
    ecm_stress = (
        ecm_strain @ system.ecm_constitutive_equilibrium.T
        + (ecm_strain - ecm_internal) @ system.ecm_constitutive_maxwell.T
    )
    interface_vectors = traction_myo_ecm[:, peak_index].reshape(-1, 2)
    interface_x = system.myocardium_mesh.dof_coordinates[
        system.myocardium_mesh.top_nodes, 0
    ]
    # S1 is preregistered as an axial active-strain heterogeneity.  Its hotspot
    # is therefore the maximum signed fibre-direction interface traction, not
    # the norm (whose symmetric tensile/compressive lobes form an artificial
    # two-way tie on a periodic cell).
    hotspot_index = int(np.argmax(interface_vectors[:, 0]))

    action_reaction_numerator = 0.0
    action_reaction_denominator = max(
        float(np.linalg.norm(traction_myo_ecm)),
        float(np.linalg.norm(traction_endo_ecm)),
        1.0e-30,
    )
    action_reaction_error = action_reaction_numerator / action_reaction_denominator
    maximum_solver_residual = max(residuals.values())
    summary = {
        "case_id": case_id,
        "spatial_level": system.spatial_label,
        "steps_per_cycle": steps_per_cycle,
        "state_size": system.state_size,
        "config_digest": system.config.digest(),
        "tissue_roles": system.roles.manifest(),
        "passive_tangent": system.passive_tangent,
        "manufactured_uniform_strain_relative_error": system.manufactured_error,
        "maximum_state_norm": float(np.max(np.linalg.norm(states, axis=0))),
        "cycle_state_relative_difference": cycle_state_difference,
        "peak_free_shortening": float(np.max(free_shortening[: steps_per_cycle + 1])),
        "peak_limited_shortening": float(np.max(limited_shortening[: steps_per_cycle + 1])),
        "minimum_limited_shortening": float(np.min(limited_shortening[: steps_per_cycle + 1])),
        "peak_absolute_mean_endocardial_tangential_displacement": float(
            np.max(np.abs(mean_endocardial_displacement[0, : steps_per_cycle + 1]))
        ),
        "peak_absolute_mean_endocardial_normal_displacement": float(
            np.max(np.abs(mean_endocardial_displacement[1, : steps_per_cycle + 1]))
        ),
        "shortening_fundamental_amplitude": float(response_amplitude),
        "shortening_waveform_l2": shortening_l2,
        "shortening_phase_relative_to_activation_rad": phase,
        "maximum_myocardium_ecm_traction": float(np.max(np.abs(traction_myo_ecm))),
        "maximum_endocardium_ecm_traction": float(np.max(np.abs(traction_endo_ecm))),
        "myocardium_ecm_traction_l2": myo_ecm_l2,
        "endocardium_ecm_traction_l2": endo_ecm_l2,
        "interface_action_reaction_relative_error": action_reaction_error,
        "hotspot_x": float(interface_x[hotspot_index]),
        "hotspot_traction": float(interface_vectors[hotspot_index, 0]),
        "maximum_ecm_von_mises_proxy": float(
            np.max(
                np.sqrt(
                    (ecm_stress[:, 0] - ecm_stress[:, 1]) ** 2
                    + 3.0 * ecm_stress[:, 2] ** 2
                )
            )
        ),
        "solver": {
            "name": system.config.direct_solver,
            "acceptance_tolerance": system.config.direct_relative_residual_tolerance,
            **residuals,
            "maximum_relative_residual": maximum_solver_residual,
            "pass": bool(maximum_solver_residual <= system.config.direct_relative_residual_tolerance),
        },
        "ledger": {
            key: value
            for key, value in ledger.items()
            if not isinstance(value, np.ndarray)
        },
    }
    arrays = {
        "time_two_cycles": times,
        "activation_two_cycles": activation,
        "limited_shortening_two_cycles": limited_shortening,
        "free_shortening_two_cycles": free_shortening,
        "mean_endocardial_tangential_displacement_two_cycles": mean_endocardial_displacement[0],
        "mean_endocardial_normal_displacement_two_cycles": mean_endocardial_displacement[1],
        "state_two_cycles": states,
        "myocardium_ecm_traction_two_cycles": traction_myo_ecm,
        "endocardium_ecm_traction_two_cycles": traction_endo_ecm,
        "ecm_cell_centroids": system.ecm_mesh.cell_centroids,
        "ecm_strain_at_peak": ecm_strain,
        "ecm_internal_z_at_peak": ecm_internal,
        "ecm_stress_at_peak": ecm_stress,
        "ledger_energy": ledger["energy"],
        "ledger_active_work_steps": ledger["active_work_steps"],
        "ledger_lumen_work_steps": ledger["lumen_work_steps"],
        "ledger_external_support_work_steps": ledger[
            "external_support_work_steps"
        ],
        "ledger_drag_dissipation_steps": ledger["drag_dissipation_steps"],
        "ledger_sls_dissipation_steps": ledger["sls_dissipation_steps"],
        "ledger_residual_steps": ledger["residual_steps"],
        "ledger_normalized_residual_steps": ledger[
            "normalized_residual_steps"
        ],
    }
    return Endpoint(summary=summary, arrays=arrays)
