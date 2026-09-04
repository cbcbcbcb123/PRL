from __future__ import annotations

from dataclasses import replace

import pytest

from paper2_m2.protocol_v06 import FROZEN_PROTOCOL_V06


def test_v06_protocol_freezes_roles_endpoint_and_resources() -> None:
    protocol = FROZEN_PROTOCOL_V06.checked()
    assert protocol.structural_control_cases == ("ID-P0",)
    assert protocol.calibration_audit_only_cases == ("ID-P1", "ID-A1")
    assert protocol.holdout_cases == (
        "ID-A2",
        "ID-LN",
        "ID-LS",
        "ID-C0",
        "ID-CQ",
        "ID-S1",
    )
    assert (protocol.spatial_level, protocol.steps_per_cycle, protocol.solver_level) == (
        "S4",
        256,
        "D0",
    )
    assert protocol.common_projection_segments == 64
    assert protocol.total_runtime_budget_seconds == 600.0
    assert protocol.peak_memory_budget_gib == 8.0
    assert protocol.cpu_processes == 1
    assert protocol.gpu_used is False


def test_v06_protocol_reuses_frozen_v01_combined_gain_operator() -> None:
    protocol = FROZEN_PROTOCOL_V06
    assert protocol.combined_gain_operator_source == (
        "scripts/run_paper2_m2_identity_2d_v01.py:545-568"
    )
    assert protocol.combined_gain_operator_source_sha256 == (
        "6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4"
    )
    assert protocol.as_dict()["phase_signal_by_case"] == {
        "ID-A2": "limited_shortening",
        "ID-LN": "negative_mean_endocardial_normal_displacement",
        "ID-LS": "mean_endocardial_tangential_displacement",
        "ID-C0": "limited_shortening",
        "ID-CQ": "limited_shortening",
        "ID-S1": "limited_shortening",
    }


def test_v06_protocol_rejects_threshold_or_grid_changes() -> None:
    with pytest.raises(ValueError, match="identity threshold"):
        replace(FROZEN_PROTOCOL_V06, traction_relative_tolerance=0.051).checked()
    with pytest.raises(ValueError, match="64 segments"):
        replace(FROZEN_PROTOCOL_V06, common_projection_segments=32).checked()

