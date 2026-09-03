from __future__ import annotations

import copy

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.identity_2d_v02 import endpoint_key, metrics_for_case, t64_numerical_gate
from paper2_m2.protocol_v02 import FROZEN_PROTOCOL_V02


def _synthetic_summaries() -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    level_scale = {"S2": 1.0, "S3": 1.004, "S4": 1.006}
    for case_id in FROZEN_CONFIG.cases:
        for representation in FROZEN_PROTOCOL_V02.representations:
            for spatial_label in ("S2", "S3", "S4"):
                for tolerance_label in FROZEN_PROTOCOL_V02.tolerance_labels:
                    value = level_scale[spatial_label]
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
                        "v02_common_projection_sidecar": {
                            "available": spatial_label != "S2",
                            "values": {
                                "myocardium_ecm_traction_l2": value,
                                "endocardium_ecm_traction_l2": value,
                            },
                        },
                    }
                    summaries[
                        endpoint_key(
                            case_id, representation, spatial_label, tolerance_label
                        )
                    ] = summary
    return summaries


def test_v02_t64_gate_counts_and_passes_a_bounded_nested_sequence() -> None:
    result = t64_numerical_gate(_synthetic_summaries())
    assert result["pass"] is True
    assert result["counts"] == {
        "spatial": 148,
        "C0_C1": 222,
        "hotspot": 4,
        "cycle": 108,
        "spatial_pass": 148,
        "C0_C1_pass": 222,
        "hotspot_pass": 4,
        "cycle_pass": 108,
    }
    assert result["projection_sidecar"]["observable_conclusion_differences"] == []


def test_v02_gate_fails_on_native_traction_even_if_projection_sidecar_passes() -> None:
    summaries = _synthetic_summaries()
    changed = copy.deepcopy(summaries)
    key = endpoint_key("ID-A2", "FEM", "S4", "C1")
    changed[key]["myocardium_ecm_traction_l2"] = 1.03
    result = t64_numerical_gate(changed)
    assert result["pass"] is False
    assert "spatial:ID-A2:FEM:C1:myocardium_ecm_traction_l2" in result["failures"]
    assert "ID-A2:FEM:C1:myocardium_ecm_traction_l2" in result[
        "projection_sidecar"
    ]["observable_conclusion_differences"]


def test_case_metric_partition_is_unchanged_from_v01() -> None:
    assert metrics_for_case("ID-P0") == ("maximum_state_norm",)
    assert metrics_for_case("ID-P1") == ("passive_tangent",)
    assert len(metrics_for_case("ID-A2")) == 5
