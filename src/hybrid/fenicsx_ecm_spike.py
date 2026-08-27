"""Exchange contract for the controlled FEniCSx ECM backend spike.

This module deliberately contains no FEniCSx imports.  It prepares identical
tetrahedral states for the owned NumPy reference implementation and for the
containerised DOLFINx implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np
from numpy.typing import NDArray

from route_h.ecm_finite_strain import ECMReference, ecm_energy_force


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ECMSpikeCase:
    """One immutable ECM state passed between the two backends."""

    name: str
    reference_vertices: FloatArray
    current_vertices: FloatArray
    tetrahedra: NDArray[np.int64]
    internal_z: FloatArray


def affine_deformation() -> FloatArray:
    """Return the registered nontrivial positive-J patch deformation."""
    return np.asarray(
        (
            (1.04, 0.03, -0.01),
            (0.01, 0.97, 0.02),
            (0.00, -0.01, 1.02),
        ),
        dtype=np.float64,
    )


def affine_internal_variable(tetrahedron_count: int) -> FloatArray:
    """Return a symmetric traceless DG0 state that exercises the SLS branch."""
    tensor = np.asarray(
        (
            (0.012, 0.003, -0.002),
            (0.003, -0.005, 0.001),
            (-0.002, 0.001, -0.007),
        ),
        dtype=np.float64,
    )
    if not np.allclose(tensor, tensor.T, atol=1.0e-15):
        raise AssertionError("registered affine Z must be symmetric")
    if abs(float(np.trace(tensor))) > 1.0e-15:
        raise AssertionError("registered affine Z must be traceless")
    return np.repeat(tensor[None, :, :], tetrahedron_count, axis=0)


def build_affine_case(reference: ECMReference) -> ECMSpikeCase:
    """Build the full-footprint affine patch case about the mesh centroid."""
    deformation = affine_deformation()
    determinant = float(np.linalg.det(deformation))
    if determinant <= 0.0:
        raise AssertionError("registered affine deformation must have positive J")
    centre = reference.vertices.mean(axis=0)
    current = centre + (reference.vertices - centre) @ deformation.T
    return ECMSpikeCase(
        name="affine_patch",
        reference_vertices=reference.vertices.copy(),
        current_vertices=current,
        tetrahedra=reference.tetrahedra.copy(),
        internal_z=affine_internal_variable(len(reference.tetrahedra)),
    )


def build_m0_case(reference: ECMReference) -> ECMSpikeCase:
    """Build the undeformed, zero-memory reference-state check."""
    return ECMSpikeCase(
        name="m0_reference",
        reference_vertices=reference.vertices.copy(),
        current_vertices=reference.vertices.copy(),
        tetrahedra=reference.tetrahedra.copy(),
        internal_z=np.zeros((len(reference.tetrahedra), 3, 3), dtype=np.float64),
    )


def evaluate_reference_case(
    case: ECMSpikeCase,
    reference: ECMReference,
    *,
    mu_eq: float,
    kappa_eq: float,
    mu_ve: float,
    warm_repeats: int = 7,
) -> tuple[dict[str, float], FloatArray, FloatArray, dict[str, float]]:
    """Evaluate and time the owned NumPy backend without changing its equations."""
    if warm_repeats < 2:
        raise ValueError("warm_repeats must include at least one warm measurement")
    timings: list[float] = []
    energies: dict[str, float] | None = None
    force: FloatArray | None = None
    jacobians: FloatArray | None = None
    for _ in range(warm_repeats):
        started = time.perf_counter()
        energies, force, jacobians = ecm_energy_force(
            case.current_vertices,
            reference,
            case.internal_z,
            mu_eq=mu_eq,
            kappa_eq=kappa_eq,
            mu_ve=mu_ve,
        )
        timings.append(time.perf_counter() - started)
    if energies is None or force is None or jacobians is None:
        raise AssertionError("reference backend did not execute")
    warm = np.asarray(timings[1:], dtype=np.float64)
    benchmark = {
        "cold_seconds": float(timings[0]),
        "warm_mean_seconds": float(warm.mean()),
        "warm_median_seconds": float(np.median(warm)),
        "warm_min_seconds": float(warm.min()),
        "warm_max_seconds": float(warm.max()),
        "warm_repeats": int(len(warm)),
    }
    return energies, force, jacobians, benchmark
