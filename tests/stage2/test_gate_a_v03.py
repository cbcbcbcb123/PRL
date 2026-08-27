from __future__ import annotations

import numpy as np
import pytest

from route_h.stage2_gate_a import (
    GAUGE_RESIDUAL_LIMIT,
    PROJECTED_RESIDUAL_LIMIT,
)
from route_h.stage2_gate_a_v03 import run_gate_a_v03_trajectory


def test_v03_accepts_the_former_step_79_trial_only_after_all_physical_gates():
    run = run_gate_a_v03_trajectory(
        "A1_ACTIVE",
        dt=0.02,
        duration=1.58,
    )

    assert run.status == "completed"
    assert run.failure is None
    trajectory = run.trajectory
    assert trajectory.time[-1] == pytest.approx(1.58, abs=1.0e-15)
    assert len(trajectory.time) == 80
    assert np.all(np.isfinite(trajectory.vertices))

    audit = run.step_audits[-1]
    assert audit.step_index == 79
    assert audit.acceptance_source == "objective_evaluation_physical_gate"
    assert audit.accepted_objective < audit.initial_objective
    assert audit.projected_residual <= PROJECTED_RESIDUAL_LIMIT
    assert audit.gauge_increment_residual <= GAUGE_RESIDUAL_LIMIT
    assert audit.geometry.finite
    assert audit.geometry.signed_volume > 0.0
    assert audit.geometry.flipped_face_count == 0
    assert audit.geometry.degenerate_face_count == 0
    assert not audit.optimizer_reported_success
    assert audit.qualifying_evaluation_index > 0
