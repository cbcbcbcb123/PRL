from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.identity_2d import build_system_for_level
from paper2_m2.identity_2d_v03 import metrics_for_case
from paper2_m2.identity_2d_v05 import (
    endpoint_key,
    endpoint_structural_gate,
    evaluate_three_level_time_record,
    simulate_endpoint_v05,
    t256_numerical_gate,
    three_level_time_gate,
    time_nodes_nested,
)
from paper2_m2.protocol_v05 import (
    EXPECTED_DCM_ACTIVE_SCALE,
    EXPECTED_DCM_PASSIVE_SCALE,
    FROZEN_PROTOCOL_V05,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t256_v05.py"


def test_real_s4_t256_endpoint_passes_ledger_and_d0_gates() -> None:
    system = build_system_for_level(
        representation="DCM",
        level=FROZEN_PROTOCOL_V05.spatial("S4"),
        passive_dcm_scale=EXPECTED_DCM_PASSIVE_SCALE,
        active_dcm_scale=EXPECTED_DCM_ACTIVE_SCALE,
        active_profile="uniform",
    )
    endpoint = simulate_endpoint_v05(system=system, case_id="ID-LN")
    gate = endpoint_structural_gate(endpoint.summary)
    assert endpoint.summary["steps_per_cycle"] == 256
    assert endpoint.summary["solver_level"] == "D0"
    assert endpoint.summary["solver"]["maximum_relative_residual"] <= 1.0e-7
    assert endpoint.summary["solver"]["maximum_normwise_backward_error"] <= 1.0e-12
    assert endpoint.summary["ledger"]["maximum_normalized_residual"] <= 1.0e-8
    assert (
        endpoint.summary["ledger"]["maximum_ledger_minus_equilibrium_work_relative"]
        <= 1.0e-10
    )
    assert gate["pass"] is True
    assert all(np.all(np.isfinite(values)) for values in endpoint.arrays.values())


def _synthetic_summaries(steps: int) -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    level_scale = {"S2": 1.0, "S3": 1.004, "S4": 1.006}
    time_scale = {64: 1.0, 128: 1.0005, 256: 1.00075}[steps]
    for case_id in FROZEN_CONFIG.cases:
        for representation in FROZEN_PROTOCOL_V05.representations:
            for spatial_label in ("S2", "S3", "S4"):
                value = level_scale[spatial_label] * time_scale
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
                    "v05_common_projection_sidecar": {
                        "available": spatial_label != "S2",
                        "values": {
                            "myocardium_ecm_traction_l2": value,
                            "endocardium_ecm_traction_l2": value,
                        },
                    },
                }
                key = "__".join(
                    (case_id, representation, spatial_label, f"T{steps}", "D0")
                )
                summaries[key] = summary
    return summaries


def test_v05_stage_and_three_level_gate_have_frozen_counts() -> None:
    t64 = _synthetic_summaries(64)
    t128 = _synthetic_summaries(128)
    t256 = _synthetic_summaries(256)
    stage = t256_numerical_gate(t256)
    time_gate = three_level_time_gate(t64, t128, t256)
    assert stage["pass"] is True
    assert stage["counts"] == {
        "spatial": 74,
        "hotspot": 2,
        "cycle": 54,
        "spatial_pass": 74,
        "hotspot_pass": 2,
        "cycle_pass": 54,
    }
    assert time_gate["pass"] is True
    assert time_gate["record_count"] == 74
    assert len({(r["case_id"], r["representation"], r["metric"]) for r in time_gate["records"]}) == 74
    assert all(record["pass"] for record in time_gate["records"])
    assert all("__T256__D0" in key for key in t256)
    assert all("__C0" not in key and "__C1" not in key for key in t256)
    assert sum(len(metrics_for_case(case_id)) for case_id in FROZEN_CONFIG.cases) * 2 == 74


@pytest.mark.parametrize(
    ("values", "expected", "failed_check"),
    [
        ((1.0, 1.005, 1.007, 1.0e-10), True, None),
        ((1.0, 1.005, 1.001, 1.0e-10), True, None),
        ((1.0, 1.02, 1.01, 1.0e-10), False, "direction_same_or_both_small"),
        ((1.0, 1.001, 1.003, 1.0e-10), False, "change_nonincreasing"),
        ((1.0, 1.02, 1.04, 1.0e-10), False, "finest_relative_pass"),
        ((0.0, 0.005, -0.004, 1.0), True, None),
        ((1.0, float("nan"), 1.0, 1.0e-10), False, "finite"),
    ],
)
def test_three_level_time_record_rules(values, expected, failed_check) -> None:
    record = evaluate_three_level_time_record(*values)
    assert record["pass"] is expected
    if failed_check is not None:
        assert record[failed_check] is False


def test_t128_time_nodes_are_nested_in_t256_nodes() -> None:
    source = np.linspace(0.0, 2.0, 257)
    target = np.linspace(0.0, 2.0, 513)
    assert time_nodes_nested(source, target)["pass"] is True
    assert time_nodes_nested(source, target[:-1])["pass"] is False


def _load_runner():
    spec = importlib.util.spec_from_file_location("paper2_m2_t256_v05_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v05_runner_normalizes_all_paths_before_output_creation() -> None:
    runner = _load_runner()
    output = Path("results/paper2_m2/v05_order_probe_never_created")
    arguments = [
        str(RUNNER_PATH),
        "--output-dir",
        str(output),
        "--contract-v05",
        "project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md",
        "--authorization",
        "project_control/paper2_m2a_v04_t128_supervisor_acceptance_and_t256_decision_v01.md",
        "--source-t64-dir",
        "results/paper2_m2/identity_2d_v03_t64_v01_20260903",
        "--source-t128-dir",
        "results/paper2_m2/identity_2d_v04_t128_v02_20260903",
        "--source-calibration",
        "results/paper2_m2/identity_2d_v01_20260903/calibration.json",
        "--v04-execution-record",
        "project_control/paper2_m2a_v04_t128_path_repair_retry_execution_record_v01.md",
    ]
    normalized, audit = runner.normalize_cli_project_paths(arguments)
    assert audit["normalization_completed_before_runtime_imports"] is True
    assert audit["normalization_completed_before_output_creation"] is True
    for index, value in enumerate(normalized):
        if index > 0 and normalized[index - 1] in runner.PROJECT_PATH_FLAGS:
            resolved = Path(value)
            assert resolved.is_absolute()
            assert resolved.is_relative_to(PROJECT_ROOT)
    with pytest.raises(ValueError, match="outside project root"):
        runner.normalize_project_path(PROJECT_ROOT.parent / "outside-project-probe")
    assert not (PROJECT_ROOT / output).exists()

