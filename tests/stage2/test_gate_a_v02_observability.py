from __future__ import annotations

import json

import numpy as np
import pytest

from route_h.stage2_gate_a_v02_observability import (
    run_gate_a_observability,
)


def test_observability_preserves_last_accepted_state_and_rejected_candidate():
    run = run_gate_a_observability(
        "A1_ACTIVE",
        dt=0.02,
        duration=1.58,
    )

    assert run.status == "failed_invalid_numerics"
    assert run.accepted_steps == 78
    assert run.time[-1] == pytest.approx(1.56, abs=1.0e-15)
    assert run.vertices.shape[0] == 79
    assert np.all(np.isfinite(run.vertices))

    failure = run.failure
    assert failure is not None
    assert failure.step_index == 79
    assert failure.time == pytest.approx(1.58, abs=1.0e-15)
    assert failure.reason == "physical_projected_overdamped_residual_above_limit"
    assert 1.0e-8 < failure.projected_residual < 2.0e-8
    assert failure.gauge_increment_residual < 1.0e-12
    assert not failure.optimizer_reported_success
    assert "ABNORMAL" in failure.optimizer_message
    assert np.all(np.isfinite(failure.candidate_vertices))
    assert failure.geometry.finite
    assert failure.geometry.signed_volume > 0.0
    assert failure.geometry.flipped_face_count == 0
    assert failure.geometry.degenerate_face_count == 0
    assert len(failure.optimizer_trace) == failure.optimizer_evaluations
    json.dumps(run.summary(), allow_nan=False)
