"""Compressible finite-strain viscoelastic tetrahedral ECM."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class ECMReference:
    vertices: FloatArray
    tetrahedra: IntArray
    dm_inverse: FloatArray
    volume0: FloatArray


def dev(tensor: FloatArray) -> FloatArray:
    return tensor - np.eye(3) * np.trace(tensor) / 3.0


def build_ecm_reference(vertices: FloatArray, tetrahedra: IntArray) -> ECMReference:
    inverse = np.empty((len(tetrahedra), 3, 3), dtype=np.float64)
    volumes = np.empty(len(tetrahedra), dtype=np.float64)
    for tet_id, tet in enumerate(tetrahedra):
        dm = np.column_stack((
            vertices[tet[1]] - vertices[tet[0]],
            vertices[tet[2]] - vertices[tet[0]],
            vertices[tet[3]] - vertices[tet[0]],
        ))
        determinant = float(np.linalg.det(dm))
        if determinant <= 0.0:
            raise ValueError(f"nonpositive reference tetrahedron {tet_id}")
        inverse[tet_id] = np.linalg.inv(dm)
        volumes[tet_id] = determinant / 6.0
    return ECMReference(
        np.asarray(vertices, dtype=np.float64).copy(),
        np.asarray(tetrahedra, dtype=np.int64).copy(),
        inverse,
        volumes,
    )


def deformation_gradient(local_vertices: FloatArray, dm_inverse: FloatArray) -> FloatArray:
    ds = np.column_stack((
        local_vertices[1] - local_vertices[0],
        local_vertices[2] - local_vertices[0],
        local_vertices[3] - local_vertices[0],
    ))
    return ds @ dm_inverse


def density_and_first_piola(
    deformation: FloatArray,
    internal_z: FloatArray,
    *,
    mu_eq: float = 1.0,
    kappa_eq: float = 20.0,
    mu_ve: float = 0.5,
) -> tuple[dict[str, float], FloatArray]:
    determinant = float(np.linalg.det(deformation))
    if determinant <= 0.0:
        raise ValueError("ECM J must remain strictly positive")
    inverse_transpose = np.linalg.inv(deformation).T
    c_tensor = deformation.T @ deformation
    i1 = float(np.trace(c_tensor))
    scale = determinant ** (-2.0 / 3.0)
    c_bar = scale * c_tensor
    q_tensor = dev(c_bar) - internal_z
    if not np.allclose(internal_z, internal_z.T, atol=1e-12):
        raise ValueError("ECM Z must be symmetric")
    if abs(float(np.trace(internal_z))) > 1e-12:
        raise ValueError("ECM Z must be traceless")
    log_j = math.log(determinant)
    equilibrium = 0.5 * mu_eq * (float(np.trace(c_bar)) - 3.0) + 0.5 * kappa_eq * log_j * log_j
    viscoelastic = 0.25 * mu_ve * float(np.sum(q_tensor * q_tensor))
    p_equilibrium = (
        mu_eq * scale * (deformation - (i1 / 3.0) * inverse_transpose)
        + kappa_eq * log_j * inverse_transpose
    )
    q_contract_c = float(np.sum(q_tensor * c_tensor))
    p_viscoelastic = mu_ve * scale * (
        deformation @ q_tensor - (q_contract_c / 3.0) * inverse_transpose
    )
    return {
        "ecm_equilibrium_density": equilibrium,
        "ecm_viscoelastic_density": viscoelastic,
        "J": determinant,
    }, p_equilibrium + p_viscoelastic


def ecm_energy_force(
    vertices: FloatArray,
    reference: ECMReference,
    internal_z: FloatArray | None = None,
    *,
    mu_eq: float = 1.0,
    kappa_eq: float = 20.0,
    mu_ve: float = 0.5,
) -> tuple[dict[str, float], FloatArray, FloatArray]:
    if internal_z is None:
        internal_z = np.zeros((len(reference.tetrahedra), 3, 3), dtype=np.float64)
    if internal_z.shape != (len(reference.tetrahedra), 3, 3):
        raise ValueError("invalid ECM internal-variable shape")
    force = np.zeros_like(vertices)
    equilibrium = 0.0
    viscoelastic = 0.0
    jacobians = np.empty(len(reference.tetrahedra), dtype=np.float64)
    for tet_id, tet in enumerate(reference.tetrahedra):
        deformation = deformation_gradient(vertices[tet], reference.dm_inverse[tet_id])
        densities, first_piola = density_and_first_piola(
            deformation,
            internal_z[tet_id],
            mu_eq=mu_eq,
            kappa_eq=kappa_eq,
            mu_ve=mu_ve,
        )
        volume = reference.volume0[tet_id]
        equilibrium += volume * densities["ecm_equilibrium_density"]
        viscoelastic += volume * densities["ecm_viscoelastic_density"]
        jacobians[tet_id] = densities["J"]
        ds_gradient = volume * first_piola @ reference.dm_inverse[tet_id].T
        local_gradient = np.empty((4, 3), dtype=np.float64)
        local_gradient[1:] = ds_gradient.T
        local_gradient[0] = -ds_gradient.sum(axis=1)
        force[tet] -= local_gradient
    return {
        "ecm_equilibrium": equilibrium,
        "ecm_viscoelastic": viscoelastic,
        "ecm_total": equilibrium + viscoelastic,
    }, force, jacobians


def internal_variable_rate(
    deformation: FloatArray,
    internal_z: FloatArray,
    *,
    mu_ve: float = 0.5,
    eta_ve: float = 0.5,
) -> FloatArray:
    determinant = float(np.linalg.det(deformation))
    if determinant <= 0.0:
        raise ValueError("ECM J must remain strictly positive")
    c_bar = determinant ** (-2.0 / 3.0) * (deformation.T @ deformation)
    return (mu_ve / (2.0 * eta_ve)) * (dev(c_bar) - internal_z)


def relax_internal_variable_exact(
    deformation: FloatArray,
    internal_z: FloatArray,
    time_step: float,
    *,
    mu_ve: float = 0.5,
    eta_ve: float = 0.5,
) -> FloatArray:
    determinant = float(np.linalg.det(deformation))
    if determinant <= 0.0:
        raise ValueError("ECM J must remain strictly positive")
    target = dev(determinant ** (-2.0 / 3.0) * (deformation.T @ deformation))
    decay = math.exp(-mu_ve * time_step / (2.0 * eta_ve))
    updated = target + (internal_z - target) * decay
    return 0.5 * (updated + updated.T) - np.eye(3) * np.trace(updated) / 3.0


def relaxation_dissipation(rate: FloatArray, eta_ve: float = 0.5) -> float:
    return float(eta_ve * np.sum(rate * rate))
