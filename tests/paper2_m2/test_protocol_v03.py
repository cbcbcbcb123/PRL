from __future__ import annotations

import copy

import pytest

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.protocol_v03 import (
    DIRECT_BACKWARD_ERROR_TOLERANCE,
    DIRECT_RELATIVE_RESIDUAL_TOLERANCE,
    DISCRETE_LEDGER_CLOSURE_TOLERANCE,
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    EXPECTED_V01_CONFIG_DIGEST,
    FROZEN_PROTOCOL_V03,
    validate_source_calibration,
)


def _calibration_payload() -> dict:
    return {
        "config_digest": EXPECTED_V01_CONFIG_DIGEST,
        "passive": {"dcm_passive_scale": EXPECTED_DCM_PASSIVE_SCALE},
        "active": {"dcm_active_scale": EXPECTED_DCM_ACTIVE_SCALE},
    }


def test_v03_protocol_has_one_operational_direct_solver_axis() -> None:
    protocol = FROZEN_PROTOCOL_V03.checked()
    assert FROZEN_CONFIG.digest() == EXPECTED_V01_CONFIG_DIGEST
    assert [(level.label, level.nx, level.ny_per_layer) for level in protocol.spatial_levels] == [
        ("S2", 32, 8),
        ("S3", 64, 16),
        ("S4", 128, 32),
    ]
    assert protocol.steps_per_cycle == 64
    assert protocol.solver_levels == ("D0",)
    assert protocol.expected_endpoint_count == 54
    assert DIRECT_RELATIVE_RESIDUAL_TOLERANCE == 1.0e-7
    assert DIRECT_BACKWARD_ERROR_TOLERANCE == 1.0e-12
    assert DISCRETE_LEDGER_CLOSURE_TOLERANCE == 1.0e-10


def test_v03_calibration_lock_remains_byte_value_exact() -> None:
    assert validate_source_calibration(_calibration_payload())["pass"] is True
    changed = copy.deepcopy(_calibration_payload())
    changed["passive"]["dcm_passive_scale"] += 1.0e-12
    with pytest.raises(ValueError, match="calibration"):
        validate_source_calibration(changed)
