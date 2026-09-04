from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from paper2_m2.identity_gate_v06 import (
    _phase_envelope,
    calibration_audit_only,
    classify_identity_records,
    combined_load_gain,
    evaluate_identity_gate,
    first_cycle,
    hotspot_descriptor,
    hotspot_gate_record,
    normalized_l2_difference,
    phase_gate_record,
    project_traction_first_cycle,
    scalar_gate_record,
    wrapped_phase_difference,
)
from paper2_m2.interface_projection import (
    common_segment_integral,
    piecewise_linear_integral,
)
from paper2_m2.protocol_v06 import FROZEN_PROTOCOL_V06


def _cycle(amplitude: float, steps: int = 256, phase: float = 0.0) -> np.ndarray:
    angle = 2.0 * np.pi * np.arange(steps) / steps + phase
    return amplitude * np.cos(angle)


def _summary(case_id: str, representation: str) -> dict:
    return {
        "case_id": case_id,
        "representation": representation,
        "peak_limited_shortening": 0.02,
        "passive_tangent": 0.67,
        "shortening_fundamental_amplitude": 0.02,
        "shortening_phase_relative_to_activation_rad": 0.1,
        "hotspot_x": -0.25,
        "ledger": {
            "total_active_work": 0.01,
            "total_drag_dissipation": 0.006,
            "total_sls_dissipation": 0.004,
            "cycle_energy_change": 0.0,
        },
    }


def _observation(case_id: str, *, traction_scale: float = 1.0) -> dict:
    steps = 256
    time = np.arange(steps, dtype=float) / steps
    activation = 0.5 * (1.0 - np.cos(2.0 * np.pi * time))
    common_x = np.linspace(-0.5, 0.5, 65)
    traction = np.zeros((64, 2, steps), dtype=float)
    traction[:, 0, :] = traction_scale * _cycle(1.0)[None, :]
    shortening = _cycle(0.02)
    return {
        "time": time,
        "activation": activation,
        "limited_shortening": shortening,
        "mean_endocardial_tangential_displacement": _cycle(0.03),
        "mean_endocardial_normal_displacement": -_cycle(0.04),
        "common_x": common_x,
        "myocardium_ecm_common_traction": traction.copy(),
        "endocardium_ecm_common_traction": traction.copy(),
        "fields": {},
    }


def test_conservative_projection_preserves_each_vector_component() -> None:
    native_x = np.linspace(-0.5, 0.5, 129)
    common_x = np.linspace(-0.5, 0.5, 65)
    nodal = np.zeros((129, 2, 257), dtype=float)
    nodal[:, 0, :] = (2.0 + native_x)[:, None]
    nodal[:, 1, :] = (-1.0 + 0.5 * native_x)[:, None]
    returned_x, projected = project_traction_first_cycle(nodal, 256, 64)
    assert np.array_equal(returned_x, common_x)
    native_integral = piecewise_linear_integral(native_x, nodal[:, :, :256])
    projected_integral = common_segment_integral(common_x, projected)
    assert np.allclose(projected_integral, native_integral, atol=1.0e-14)


def test_first_cycle_excludes_repeated_endpoint() -> None:
    values = np.arange(513, dtype=float)
    observed = first_cycle(values, 256)
    assert observed.shape == (256,)
    assert observed[-1] == 255.0


def test_normalized_l2_and_near_zero_absolute_rule() -> None:
    value_a = np.asarray([1.0, 0.0])
    value_b = np.asarray([0.0, 0.0])
    assert normalized_l2_difference(value_a, value_b, 1.0e-10) == pytest.approx(1.0)
    record = scalar_gate_record(
        case_id="ID-LS",
        metric="peak_limited_shortening",
        dcm=5.0e-7,
        fem=-5.0e-7,
        floor=1.0e-6,
        threshold=0.05,
        no_go_threshold=0.15,
    )
    assert record["near_zero_absolute_rule_applied"] is True
    assert record["relative_difference"] is None
    assert record["pass"] is True


def test_phase_wrap_and_nonapplicable_amplitude_rule() -> None:
    difference = wrapped_phase_difference(
        np.exp(1j * (math.pi - 0.01)), np.exp(1j * (-math.pi + 0.01))
    )
    assert difference == pytest.approx(0.02)
    record = phase_gate_record(
        case_id="ID-A2",
        signal_name="limited_shortening",
        signal_dcm=np.zeros(256),
        signal_fem=np.zeros(256),
    )
    assert record["applicable"] is False
    assert record["pass"] is True


def test_frozen_combined_gain_matches_v01_operator() -> None:
    result = combined_load_gain(
        _cycle(3.0), _cycle(1.0), _cycle(0.5), FROZEN_PROTOCOL_V06.shortening_floor
    )
    assert result["combined_amplitude"] == pytest.approx(3.0)
    assert result["active_ID_A2_amplitude"] == pytest.approx(1.0)
    assert result["normal_ID_LN_amplitude"] == pytest.approx(0.5)
    assert result["gain"] == pytest.approx(2.0)


def test_two_interfaces_are_gated_separately() -> None:
    protocol = FROZEN_PROTOCOL_V06
    summaries = {}
    observations = {}
    for case_id in protocol.holdout_cases:
        observations[case_id] = {}
        for representation in protocol.representations:
            summaries[f"{case_id}__{representation}__S4__T256__D0"] = _summary(
                case_id, representation
            )
            observations[case_id][representation] = _observation(case_id)
    observations["ID-A2"]["FEM"]["myocardium_ecm_common_traction"] *= 2.0
    result = evaluate_identity_gate(
        summaries_t256=summaries, observations_t256=observations
    )
    records = {
        record["metric"]: record for record in result["cases"]["ID-A2"]["records"]
    }
    assert records["myocardium_ecm_common_traction_normalized_L2"]["severity"] == "no_go"
    assert records["endocardium_ecm_common_traction_normalized_L2"]["pass"] is True


def test_hotspot_split_is_no_go() -> None:
    protocol = FROZEN_PROTOCOL_V06
    common_x = np.linspace(-0.5, 0.5, 65)
    activation = np.zeros(256)
    activation[100] = 1.0
    single = np.zeros((64, 2, 256))
    split = np.zeros((64, 2, 256))
    single[10, 0, 100] = 2.0
    split[10, 0, 100] = 2.0
    split[30, 0, 100] = 2.0
    dcm = hotspot_descriptor(single, activation, common_x, protocol)
    fem = hotspot_descriptor(split, activation, common_x, protocol)
    record = hotspot_gate_record(dcm, fem, protocol)
    assert fem["split"] is True
    assert record["severity"] == "no_go"


@pytest.mark.parametrize(
    ("preconditions", "severity", "expected"),
    [
        (True, "pass", "GO-ID"),
        (True, "maybe", "MAYBE-ID"),
        (True, "no_go", "NO-GO-ID"),
        (False, "pass", "BLOCKED"),
    ],
)
def test_decision_boundaries(preconditions: bool, severity: str, expected: str) -> None:
    assert (
        classify_identity_records(
            [{"severity": severity}], preconditions_complete=preconditions
        )
        == expected
    )


def test_calibration_cases_are_audit_only() -> None:
    summaries = {}
    for case_id in ("ID-P1", "ID-A1"):
        for representation in ("DCM", "FEM"):
            summaries[f"{case_id}__{representation}__S4__T256__D0"] = _summary(
                case_id, representation
            )
    audit = calibration_audit_only(summaries)
    assert audit["identity_gate_applied"] is False
    assert all(record["pass"] is None for record in audit["records"])


@pytest.mark.parametrize("case_id", ["ID-LN", "ID-LS"])
def test_custom_displacement_phase_envelope_never_uses_shortening_summary(
    case_id: str,
) -> None:
    observations_t128 = {case_id: {}}
    observations_t256 = {case_id: {}}
    summaries_t128 = {}
    summaries_t256 = {}
    for representation in ("DCM", "FEM"):
        coarse = _observation(case_id)
        coarse = {
            **coarse,
            "time": coarse["time"][:128],
            "activation": coarse["activation"][:128],
            "limited_shortening": coarse["limited_shortening"][:128],
            "mean_endocardial_tangential_displacement": coarse[
                "mean_endocardial_tangential_displacement"
            ][:128],
            "mean_endocardial_normal_displacement": coarse[
                "mean_endocardial_normal_displacement"
            ][:128],
            "myocardium_ecm_common_traction": coarse[
                "myocardium_ecm_common_traction"
            ][:, :, :128],
            "endocardium_ecm_common_traction": coarse[
                "endocardium_ecm_common_traction"
            ][:, :, :128],
        }
        observations_t128[case_id][representation] = coarse
        observations_t256[case_id][representation] = _observation(case_id)
        for level in ("S3", "S4"):
            key = f"{case_id}__{representation}__{level}__T256__D0"
            summaries_t256[key] = {
                "shortening_phase_relative_to_activation_rad": 2.5
            }
        summaries_t128[f"{case_id}__{representation}__S4__T128__D0"] = {
            "shortening_phase_relative_to_activation_rad": -2.5
        }
    envelope = _phase_envelope(
        case_id=case_id,
        observations_t128=observations_t128,
        observations_t256=observations_t256,
        summaries_t128=summaries_t128,
        summaries_t256=summaries_t256,
        protocol=FROZEN_PROTOCOL_V06,
    )
    assert envelope["spatial_component_complete"] is False
    for arm in envelope["by_representation"].values():
        assert arm["spatial_S3_to_S4_frozen_summary_phase_abs_rad"] is None
        assert arm["frozen_summary_T128_to_T256_phase_abs_rad"] is None


def test_source_lock_fails_closed_for_missing_package(tmp_path: Path) -> None:
    runner_path = Path(__file__).parents[2] / "scripts/run_paper2_m2_identity_gate_v06.py"
    specification = importlib.util.spec_from_file_location("v06_runner", runner_path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    lock, summaries, structural, snapshot = module._validate_source_package(
        label="T64",
        source_dir=tmp_path,
        spec=module.SOURCE_SPECS["T64"],
    )
    assert lock["pass"] is False
    assert summaries == {}
    assert structural == {}
    assert snapshot == {}

