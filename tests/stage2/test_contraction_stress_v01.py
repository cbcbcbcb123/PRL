"""Regression checks for opt-in high-contraction development probes."""

from __future__ import annotations

import numpy as np
import pytest

from route_h.activation import active_energy_force
from route_h.stage2_gate_a import _build_reference
from route_h.stage2_gate_a_v04 import run_gate_a_v04_trajectory


def test_high_activation_requires_explicit_limit() -> None:
    gate_reference = _build_reference()
    with pytest.raises(ValueError, match="activation must remain"):
        active_energy_force(
            gate_reference.vertices,
            gate_reference.active,
            alpha=0.5,
        )

    energy, force, state = active_energy_force(
        gate_reference.vertices,
        gate_reference.active,
        alpha=0.5,
        alpha_limit=0.5,
    )
    assert energy > 0.0
    assert np.all(np.isfinite(force))
    assert state.preferred_length == pytest.approx(
        0.5 * gate_reference.active.length0
    )


def test_default_v04_trajectory_remains_on_frozen_ten_percent_peak() -> None:
    run = run_gate_a_v04_trajectory(
        "A1_ACTIVE",
        dt=0.02,
        duration=1.02,
    )
    assert run.trajectory.alpha[-1] < 0.001


def test_fifty_percent_probe_is_explicitly_configurable() -> None:
    run = run_gate_a_v04_trajectory(
        "A1_ACTIVE",
        dt=0.02,
        duration=1.02,
        alpha_peak=0.5,
        activation_limit=0.5,
    )
    assert run.trajectory.alpha[-1] > 0.0004
