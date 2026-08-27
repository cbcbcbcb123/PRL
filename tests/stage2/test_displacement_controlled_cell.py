"""Behavior checks for the displacement-controlled M1 development probe."""

from __future__ import annotations

import numpy as np
import pytest

from route_h.displacement_controlled_cell import (
    run_displacement_controlled_compression,
)


def test_displacement_boundary_enforces_requested_anchor_shortening() -> None:
    run = run_displacement_controlled_compression(
        target_shortening=0.02,
        step_count=2,
        k_area=0.0,
    )
    final = run.samples[-1]
    assert run.status == "completed"
    assert final.imposed_shortening == pytest.approx(0.02)
    assert final.measured_anchor_shortening == pytest.approx(
        0.02,
        abs=1.0e-14,
    )
    assert final.area_energy == 0.0
    assert final.geometry.flipped_face_count == 0
    assert final.geometry.degenerate_face_count == 0
    assert np.all(np.isfinite(final.vertices))


def test_invalid_compression_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="target shortening"):
        run_displacement_controlled_compression(target_shortening=1.0)
    with pytest.raises(ValueError, match="volume stiffness"):
        run_displacement_controlled_compression(k_volume=0.0)
