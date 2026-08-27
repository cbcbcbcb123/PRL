"""Homogeneous isochoric displacement loading for M1 shape previews."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .activation import anchor_length_axis
from .dcm_cell import surface_volume_and_gradient
from .geometry import triangle_geometry
from .stage2_gate_a import _build_reference
from .stage2_gate_a_v02_observability import (
    GeometryDiagnostics,
    _geometry_diagnostics,
)


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class IsochoricDisplacementState:
    imposed_shortening: float
    deformation_gradient: FloatArray
    vertices: FloatArray
    measured_anchor_shortening: float
    transverse_stretch: float
    volume_ratio: float
    total_area_ratio: float
    area_group_ratios: FloatArray
    geometry: GeometryDiagnostics


def impose_isochoric_axial_shortening(
    shortening: float,
) -> IsochoricDisplacementState:
    """Prescribe axial shortening and the equal transverse isochoric stretch."""
    if not 0.0 <= shortening < 1.0:
        raise ValueError("shortening must lie inside [0,1)")
    reference = _build_reference()
    axial_stretch = 1.0 - shortening
    transverse_stretch = 1.0 / np.sqrt(axial_stretch)
    deformation_gradient = np.diag(
        [axial_stretch, transverse_stretch, transverse_stretch]
    ).astype(np.float64)
    centre = 0.5 * (
        reference.active.minus_weights @ reference.vertices
        + reference.active.plus_weights @ reference.vertices
    )
    vertices = (
        (reference.vertices - centre) @ deformation_gradient.T + centre
    )
    length, _ = anchor_length_axis(vertices, reference.active)
    volume, _ = surface_volume_and_gradient(vertices, reference.faces)
    areas, _ = triangle_geometry(vertices, reference.faces)
    group_codes = (
        reference.cell.primary * 10 + reference.cell.directional
    )
    group_areas = np.asarray(
        [
            areas[group_codes == key].sum()
            for key in reference.cell.area_group_keys
        ],
        dtype=np.float64,
    )
    return IsochoricDisplacementState(
        imposed_shortening=shortening,
        deformation_gradient=deformation_gradient,
        vertices=vertices,
        measured_anchor_shortening=(
            1.0 - length / reference.active.length0
        ),
        transverse_stretch=float(transverse_stretch),
        volume_ratio=float(volume / reference.cell.volume0),
        total_area_ratio=float(areas.sum() / reference.cell.area0.sum()),
        area_group_ratios=group_areas / reference.cell.area0,
        geometry=_geometry_diagnostics(vertices, reference),
    )
