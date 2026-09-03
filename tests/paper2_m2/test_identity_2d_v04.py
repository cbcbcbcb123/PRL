from __future__ import annotations

import numpy as np

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.identity_2d import build_system_for_level
from paper2_m2.identity_2d_v03 import metrics_for_case
from paper2_m2.identity_2d_v04 import (
    endpoint_key,
    endpoint_structural_gate,
    simulate_endpoint_v04,
    t128_numerical_gate,
    t64_t128_pair_audit,
)
from paper2_m2.protocol_v04 import (
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    FROZEN_PROTOCOL_V04,
)


def test_real_s4_t128_endpoint_passes_ledger_and_d0_gates() -> None:
    system = build_system_for_level(
        representation="DCM",
        level=FROZEN_PROTOCOL_V04.spatial("S4"),
        passive_dcm_scale=EXPECTED_DCM_PASSIVE_SCALE,
        active_dcm_scale=EXPECTED_DCM_ACTIVE_SCALE,
        active_profile="uniform",
    )
    endpoint = simulate_endpoint_v04(
        system=system,
        case_id="ID-LN",
    )
    gate = endpoint_structural_gate(endpoint.summary)
    assert endpoint.summary["steps_per_cycle"] == 128
    assert endpoint.summary["solver_level"] == "D0"
    assert endpoint.summary["solver"]["maximum_relative_residual"] <= 1.0e-7
    assert endpoint.summary["solver"]["maximum_normwise_backward_error"] <= 1.0e-12
    assert endpoint.summary["ledger"]["maximum_normalized_residual"] <= 1.0e-8
    assert (
        endpoint.summary["ledger"][
            "maximum_ledger_minus_equilibrium_work_relative"
        ]
        <= 1.0e-10
    )
    assert gate["pass"] is True
    assert all(np.all(np.isfinite(values)) for values in endpoint.arrays.values())


def _synthetic_summaries(steps: int) -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    level_scale = {"S2": 1.0, "S3": 1.004, "S4": 1.006}
    for case_id in FROZEN_CONFIG.cases:
        for representation in FROZEN_PROTOCOL_V04.representations:
            for spatial_label in ("S2", "S3", "S4"):
                value = level_scale[spatial_label] * (1.0005 if steps == 128 else 1.0)
                summary = {
                    "maximum_state_norm": 0.0 if case_id == "ID-P0" else value,
                    "passive_tangent": value,
                    "peak_limited_shortening": value,
                    "shortening_waveform_l2": value,
                    "myocardium_ecm_traction_l2": value,
                    "endocardium_ecm_traction_l2": value,
                    "ledger": {
                        "total_drag_dissipation": 0.4 * value,
                        "total_sls_dissipation": 0.6 * value,
                    },
                    "cycle_state_relative_difference": 0.0,
                    "hotspot_x": 0.0,
                    "v04_common_projection_sidecar": {
                        "available": spatial_label != "S2",
                        "values": {
                            "myocardium_ecm_traction_l2": value,
                            "endocardium_ecm_traction_l2": value,
                        },
                    },
                }
                key = (
                    endpoint_key(case_id, representation, spatial_label)
                    if steps == 128
                    else "__".join(
                        (case_id, representation, spatial_label, "T64", "D0")
                    )
                )
                summaries[key] = summary
    return summaries


def test_v04_gate_and_pair_audit_have_frozen_counts() -> None:
    t128 = _synthetic_summaries(128)
    t64 = _synthetic_summaries(64)
    stage = t128_numerical_gate(t128)
    pairs = t64_t128_pair_audit(t64, t128)
    assert stage["pass"] is True
    assert stage["counts"] == {
        "spatial": 74,
        "hotspot": 2,
        "cycle": 54,
        "spatial_pass": 74,
        "hotspot_pass": 2,
        "cycle_pass": 54,
    }
    assert pairs["pass"] is True
    assert pairs["label"] == "T64_T128_PAIR_AUDIT_ONLY"
    assert pairs["record_count"] == 74
    assert all(record["direction_pending_T256"] for record in pairs["records"])
    assert all("threshold" not in record for record in pairs["records"])
    assert all("__T128__D0" in key for key in t128)
    assert all("__C0" not in key and "__C1" not in key for key in t128)
    assert sum(len(metrics_for_case(case_id)) for case_id in FROZEN_CONFIG.cases) * 2 == 74
