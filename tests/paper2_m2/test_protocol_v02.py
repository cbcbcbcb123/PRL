from __future__ import annotations

import copy

import pytest

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.protocol_v02 import (
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    EXPECTED_V01_CONFIG_DIGEST,
    FROZEN_PROTOCOL_V02,
    validate_source_calibration,
)


def _calibration_payload() -> dict:
    return {
        "config_digest": EXPECTED_V01_CONFIG_DIGEST,
        "passive": {"dcm_passive_scale": EXPECTED_DCM_PASSIVE_SCALE},
        "active": {"dcm_active_scale": EXPECTED_DCM_ACTIVE_SCALE},
    }


def test_v02_protocol_freezes_the_authorized_t64_matrix() -> None:
    protocol = FROZEN_PROTOCOL_V02.checked()
    assert FROZEN_CONFIG.digest() == EXPECTED_V01_CONFIG_DIGEST
    assert [(level.label, level.nx, level.ny_per_layer) for level in protocol.spatial_levels] == [
        ("S2", 32, 8),
        ("S3", 64, 16),
        ("S4", 128, 32),
    ]
    assert protocol.steps_per_cycle == 64
    assert protocol.expected_endpoint_count == 108
    assert protocol.common_projection_segments == 64


def test_v02_calibration_lock_accepts_only_exact_source_values() -> None:
    accepted = validate_source_calibration(_calibration_payload())
    assert accepted["pass"] is True

    changed = copy.deepcopy(_calibration_payload())
    changed["active"]["dcm_active_scale"] += 1.0e-12
    with pytest.raises(ValueError, match="calibration"):
        validate_source_calibration(changed)


def test_protocol_payload_preserves_native_gate_and_sidecar_roles() -> None:
    payload = FROZEN_PROTOCOL_V02.canonical_payload()
    assert payload["spatial_gate"]["production_observable"] == (
        "native_nodal_or_spring_traction"
    )
    assert payload["spatial_gate"]["finest_pair"] == ["S3", "S4"]
    assert payload["spatial_gate"]["hotspot_cell_width"] == pytest.approx(1.0 / 128.0)
