"""Displacement-controlled single-cell compression development probe.

This module deliberately contains no active-force term.  The two registered
fiber-anchor patches are clamped and moved toward the cell centre, while the
remaining surface nodes relax under the passive cell energy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .activation import anchor_length_axis
from .dcm_cell import passive_energy_force, surface_volume_and_gradient
from .geometry import triangle_geometry
from .stage2_gate_a import _build_reference
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class CompressionSample:
    imposed_shortening: float
    measured_anchor_shortening: float
    vertices: FloatArray
    volume_ratio: float
    total_area_ratio: float
    area_group_ratios: FloatArray
    area_energy: float
    bending_energy: float
    volume_energy: float
    free_gradient_l2: float
    boundary_reaction_l2: float
    optimizer_iterations: int
    optimizer_evaluations: int
    optimizer_success: bool
    optimizer_message: str
    geometry: GeometryDiagnostics


@dataclass(frozen=True)
class CompressionRun:
    status: str
    target_shortening: float
    area_stiffness: float
    volume_stiffness: float
    bending_stiffness: float
    fixed_vertex_ids: IntArray
    samples: tuple[CompressionSample, ...]


def _area_group_ratios(vertices: FloatArray, reference: object) -> FloatArray:
    areas, _ = triangle_geometry(vertices, reference.faces)
    codes = reference.cell.primary * 10 + reference.cell.directional
    current = np.asarray(
        [
            areas[codes == key].sum()
            for key in reference.cell.area_group_keys
        ],
        dtype=np.float64,
    )
    return current / reference.cell.area0


def _make_sample(
    vertices: FloatArray,
    reference: object,
    *,
    imposed_shortening: float,
    fixed_vertex_ids: IntArray,
    free_vertex_ids: IntArray,
    k_area: float,
    k_bend: float,
    k_volume: float,
    optimizer_iterations: int,
    optimizer_evaluations: int,
    optimizer_success: bool,
    optimizer_message: str,
) -> CompressionSample:
    energies, force = passive_energy_force(
        vertices,
        reference.cell,
        k_area=k_area,
        k_bend=k_bend,
        k_volume=k_volume,
    )
    length, _ = anchor_length_axis(vertices, reference.active)
    volume, _ = surface_volume_and_gradient(vertices, reference.faces)
    areas, _ = triangle_geometry(vertices, reference.faces)
    return CompressionSample(
        imposed_shortening=imposed_shortening,
        measured_anchor_shortening=(
            1.0 - length / reference.active.length0
        ),
        vertices=vertices.copy(),
        volume_ratio=volume / reference.cell.volume0,
        total_area_ratio=float(areas.sum() / reference.cell.area0.sum()),
        area_group_ratios=_area_group_ratios(vertices, reference),
        area_energy=float(energies["cell_area"]),
        bending_energy=float(energies["cell_bend"]),
        volume_energy=float(energies["cell_volume"]),
        free_gradient_l2=float(np.linalg.norm(force[free_vertex_ids])),
        boundary_reaction_l2=float(np.linalg.norm(force[fixed_vertex_ids])),
        optimizer_iterations=optimizer_iterations,
        optimizer_evaluations=optimizer_evaluations,
        optimizer_success=optimizer_success,
        optimizer_message=optimizer_message,
        geometry=_geometry_diagnostics(vertices, reference),
    )


def run_displacement_controlled_compression(
    *,
    target_shortening: float = 0.2,
    step_count: int = 20,
    k_area: float = 0.0,
    k_bend: float = 0.01,
    k_volume: float = 100.0,
) -> CompressionRun:
    """Clamp both end patches and prescribe their axial separation.

    All three coordinates of the end-patch nodes are clamped.  Their axial
    coordinates follow the imposed shortening, while their transverse
    coordinates retain their reference values.  Every other node is free.
    """
    if not 0.0 < target_shortening < 1.0:
        raise ValueError("target shortening must lie strictly inside (0,1)")
    if step_count <= 0:
        raise ValueError("step count must be positive")
    if min(k_area, k_bend, k_volume) < 0.0:
        raise ValueError("passive stiffnesses must be nonnegative")
    if k_volume <= 0.0:
        raise ValueError("volume stiffness must remain positive")

    reference = _build_reference()
    minus_ids = np.flatnonzero(reference.active.minus_weights > 0.0)
    plus_ids = np.flatnonzero(reference.active.plus_weights > 0.0)
    fixed_ids = np.unique(np.concatenate((minus_ids, plus_ids))).astype(
        np.int64
    )
    all_ids = np.arange(len(reference.vertices), dtype=np.int64)
    free_ids = np.setdiff1d(all_ids, fixed_ids, assume_unique=True)
    if len(free_ids) == 0:
        raise RuntimeError("compression probe requires free surface vertices")

    centre_x = float(
        0.5
        * (
            reference.active.minus_weights @ reference.vertices[:, 0]
            + reference.active.plus_weights @ reference.vertices[:, 0]
        )
    )
    current = reference.vertices.copy()
    samples: list[CompressionSample] = [
        _make_sample(
            current,
            reference,
            imposed_shortening=0.0,
            fixed_vertex_ids=fixed_ids,
            free_vertex_ids=free_ids,
            k_area=k_area,
            k_bend=k_bend,
            k_volume=k_volume,
            optimizer_iterations=0,
            optimizer_evaluations=1,
            optimizer_success=True,
            optimizer_message="reference_state",
        )
    ]
    previous_fraction = 0.0
    status = "completed"

    for fraction in np.linspace(
        target_shortening / step_count,
        target_shortening,
        step_count,
    ):
        fraction = float(fraction)
        incremental_scale = (1.0 - fraction) / (1.0 - previous_fraction)
        initial = current.copy()
        initial[:, 0] = centre_x + incremental_scale * (
            initial[:, 0] - centre_x
        )

        boundary = reference.vertices[fixed_ids].copy()
        boundary[:, 0] = centre_x + (1.0 - fraction) * (
            boundary[:, 0] - centre_x
        )
        initial[fixed_ids] = boundary

        def unpack(coordinates: FloatArray) -> FloatArray:
            vertices = initial.copy()
            vertices[free_ids] = coordinates.reshape((-1, 3))
            vertices[fixed_ids] = boundary
            return vertices

        def objective(coordinates: FloatArray) -> tuple[float, FloatArray]:
            vertices = unpack(coordinates)
            energies, force = passive_energy_force(
                vertices,
                reference.cell,
                k_area=k_area,
                k_bend=k_bend,
                k_volume=k_volume,
            )
            value = float(energies["cell_total"])
            gradient = -force[free_ids].reshape(-1)
            return value, gradient

        result = minimize(
            objective,
            initial[free_ids].reshape(-1),
            method="L-BFGS-B",
            jac=True,
            options={
                "maxiter": 1000,
                "maxls": 100,
                "maxcor": 40,
                "ftol": 1.0e-15,
                "gtol": 1.0e-9,
            },
        )
        candidate = unpack(np.asarray(result.x, dtype=np.float64))
        sample = _make_sample(
            candidate,
            reference,
            imposed_shortening=fraction,
            fixed_vertex_ids=fixed_ids,
            free_vertex_ids=free_ids,
            k_area=k_area,
            k_bend=k_bend,
            k_volume=k_volume,
            optimizer_iterations=int(result.nit),
            optimizer_evaluations=int(result.nfev),
            optimizer_success=bool(result.success),
            optimizer_message=str(result.message),
        )
        samples.append(sample)
        if (
            not sample.geometry.finite
            or sample.geometry.signed_volume <= 0.0
            or sample.geometry.flipped_face_count > 0
            or sample.geometry.degenerate_face_count > 0
        ):
            status = "failed_geometry_gate"
            break
        current = candidate
        previous_fraction = fraction

    if samples[-1].imposed_shortening < target_shortening:
        status = "failed_before_target"
    return CompressionRun(
        status=status,
        target_shortening=target_shortening,
        area_stiffness=k_area,
        volume_stiffness=k_volume,
        bending_stiffness=k_bend,
        fixed_vertex_ids=fixed_ids,
        samples=tuple(samples),
    )
