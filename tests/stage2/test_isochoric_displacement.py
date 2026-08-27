"""Checks for the homogeneous isochoric displacement preview."""

from __future__ import annotations

import numpy as np
import pytest

from route_h.isochoric_displacement import (
    impose_isochoric_axial_shortening,
)


def test_twenty_percent_shortening_is_exact_and_isochoric() -> None:
    state = impose_isochoric_axial_shortening(0.2)
    assert state.measured_anchor_shortening == pytest.approx(
        0.2,
        abs=1.0e-14,
    )
    assert state.transverse_stretch == pytest.approx(1.0 / np.sqrt(0.8))
    assert np.linalg.det(state.deformation_gradient) == pytest.approx(1.0)
    assert state.volume_ratio == pytest.approx(1.0, abs=1.0e-14)
    assert state.geometry.flipped_face_count == 0
    assert state.geometry.degenerate_face_count == 0
    assert state.geometry.minimum_face_area_ratio > 0.8


def test_invalid_shortening_is_rejected() -> None:
    with pytest.raises(ValueError, match="shortening"):
        impose_isochoric_axial_shortening(1.0)
