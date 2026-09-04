from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from paper2_m2.identity_gate_v06 import endpoint_key
from paper2_m2.identity_no_go_diagnostic_v07 import (
    NORM_FLOOR,
    _temporal_decomposition,
    build_pure_mode_transfer_audit,
    build_signed_permutation_basis_audit,
    build_source_formula_audit,
    classify_diagnostic_conditions,
    common_widths,
    component_record,
    finite_tree,
    mode_decomposition_record,
    signed_permutation_matrices,
    superposition_modal_record,
    traction_record_diagnostic,
    weighted_space_time_norm,
)


PROJECT_ROOT = Path(__file__).parents[2]


def _load_runner():
    path = PROJECT_ROOT / "scripts/run_paper2_m2_identity_no_go_diagnostic_v07.py"
    specification = importlib.util.spec_from_file_location("v07_runner", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _traction(scale: float = 1.0, steps: int = 256) -> np.ndarray:
    x = np.linspace(-0.5, 0.5, 64, endpoint=False) + 1.0 / 128.0
    angle = 2.0 * np.pi * np.arange(steps) / steps
    field = np.zeros((64, 2, steps), dtype=float)
    field[:, 0, :] = scale * (1.0 + 0.2 * x[:, None]) * (
        0.5 + np.cos(angle)[None, :]
    )
    field[:, 1, :] = scale * (0.7 - 0.1 * x[:, None]) * (
        0.2 + np.sin(angle)[None, :]
    )
    return field


def _observation(case_id: str, representation: str, steps: int = 256) -> dict:
    angle = 2.0 * np.pi * np.arange(steps) / steps
    arm_scale = 1.0 if representation == "DCM" else 1.1
    case_scale = {
        "ID-A2": 1.0,
        "ID-LN": 0.7,
        "ID-LS": 0.4,
        "ID-C0": 1.7,
        "ID-CQ": 1.3,
        "ID-S1": 1.2,
    }[case_id]
    return {
        "time": np.arange(steps, dtype=float) / steps,
        "activation": 0.5 * (1.0 - np.cos(angle)),
        "limited_shortening": arm_scale * case_scale * (0.1 + 0.02 * np.cos(angle)),
        "mean_endocardial_normal_displacement": arm_scale
        * case_scale
        * (0.03 + 0.01 * np.cos(angle)),
        "mean_endocardial_tangential_displacement": arm_scale
        * case_scale
        * (0.02 + 0.01 * np.sin(angle)),
        "common_x": np.linspace(-0.5, 0.5, 65),
        "myocardium_ecm_common_traction": _traction(
            arm_scale * case_scale, steps
        ),
        "endocardium_ecm_common_traction": _traction(
            0.8 * arm_scale * case_scale, steps
        ),
        "fields": {},
    }


def test_weighted_norm_uses_space_widths_and_equal_time_weights() -> None:
    widths = np.asarray([0.25, 0.75])
    field = np.ones((2, 2, 4))
    assert weighted_space_time_norm(field, widths) == pytest.approx(math.sqrt(2.0))


def test_optimal_real_scale_removes_a_pure_global_factor() -> None:
    dcm = _traction()
    fem = 2.0 * dcm
    record = traction_record_diagnostic(
        case_id="ID-A2",
        interface="myocardium_ecm",
        dcm=dcm,
        fem=fem,
        common_x=np.linspace(-0.5, 0.5, 65),
    )
    assert record["per_record_optimal_real_scale"] == pytest.approx(2.0)
    assert record["optimal_scale_residual_over_fem_norm"] < 1.0e-14
    assert record["weighted_cosine"] == pytest.approx(1.0)
    assert record["normalized_l2_difference"] == pytest.approx(0.5)


def test_near_zero_component_reports_absolute_norm_without_relative_classification() -> None:
    zeros = np.zeros((64, 256))
    record = component_record(
        zeros,
        zeros,
        np.full(64, 1.0 / 64.0),
        total_dcm_energy=0.0,
        total_fem_energy=0.0,
    )
    assert record["status"] == "NEAR_ZERO_COMPONENT"
    assert record["normalized_l2_difference"] is None
    assert record["absolute_difference_norm"] == 0.0


def test_signed_permutation_set_is_exactly_eight_and_identity_is_best_for_equal_fields() -> None:
    candidates = signed_permutation_matrices()
    assert len(candidates) == 8
    assert len({tuple(item["matrix"].ravel()) for item in candidates}) == 8
    assert sum(item["is_identity"] for item in candidates) == 1
    dcm = _traction()
    failed = [
        (
            "ID-A2__myocardium_ecm",
            dcm,
            dcm.copy(),
            np.full(64, 1.0 / 64.0),
        )
    ]
    audit = build_signed_permutation_basis_audit(failed)
    assert audit["candidate_count"] == 8
    assert audit["common_best"]["is_identity"] is True
    assert audit["common_best"]["maximum_record_residual"] == 0.0
    assert audit["general_rotation_or_affine_search_used"] is False


@pytest.mark.parametrize(
    "signal_kind",
    ["dc", "sine", "cosine", "mixed"],
)
def test_temporal_decomposition_parseval_for_manufactured_signals(
    signal_kind: str,
) -> None:
    angle = 2.0 * np.pi * np.arange(256) / 256
    signals = {
        "dc": np.ones(256),
        "sine": np.sin(angle),
        "cosine": np.cos(angle),
        "mixed": 0.4 + np.cos(angle) + 0.3 * np.sin(3.0 * angle),
    }
    field = np.repeat(signals[signal_kind][None, :], 64, axis=0)
    parts = _temporal_decomposition(field)
    widths = np.full(64, 1.0 / 64.0)
    total_energy = weighted_space_time_norm(field, widths) ** 2
    parts_energy = sum(
        weighted_space_time_norm(parts[name], widths) ** 2
        for name in ("dc", "fundamental", "higher_harmonics")
    )
    assert abs(parts_energy - total_energy) / max(total_energy, NORM_FLOOR**2) < 1.0e-12


def test_mode_decomposition_closes_spatial_and_temporal_energy() -> None:
    dcm = _traction()[:, 0, :]
    fem = 1.1 * dcm
    record = mode_decomposition_record(
        case_id="ID-A2",
        interface="myocardium_ecm",
        component="x",
        dcm=dcm,
        fem=fem,
        common_x=np.linspace(-0.5, 0.5, 65),
    )
    assert record["temporal"]["dcm_parseval_relative_error"] < 1.0e-12
    assert record["temporal"]["fem_parseval_relative_error"] < 1.0e-12
    assert record["spatial"]["dcm_energy_closure_relative_error"] < 1.0e-12
    assert record["spatial"]["fem_energy_closure_relative_error"] < 1.0e-12


def test_pure_mode_transfer_keeps_physical_quantities_separate() -> None:
    observations = {
        case_id: {
            representation: _observation(case_id, representation)
            for representation in ("DCM", "FEM")
        }
        for case_id in ("ID-A2", "ID-LN", "ID-LS")
    }
    summaries = {}
    for case_id in observations:
        for representation in ("DCM", "FEM"):
            summaries[endpoint_key(case_id, representation, "S4", 256)] = {
                "ledger": {
                    "total_drag_dissipation": 0.4,
                    "total_sls_dissipation": 0.1,
                    "cycle_energy_change": 1.0e-15,
                }
            }
    audit = build_pure_mode_transfer_audit(observations, summaries)
    assert set(audit["cases"]) == {"ID-A2", "ID-LN", "ID-LS"}
    assert audit["different_physical_quantities_combined_into_one_norm"] is False
    assert audit["cases"]["ID-A2"]["entries"]["myocardium_ecm"]["x"][
        "unit"
    ] == "nondimensional_interface_traction_density"


def test_complex_quarter_phase_superposition_is_reconstructed_exactly() -> None:
    angle = 2.0 * np.pi * np.arange(256) / 256
    active = 0.3 + np.cos(angle)
    normal = 0.2 + 0.5 * np.cos(angle)
    combined = 0.5 + np.cos(angle) - 0.5 * np.sin(angle)
    record = superposition_modal_record(
        observed=combined,
        active=active,
        normal=normal,
        normal_phase_multiplier=1.0j,
        coarse_observed=combined[::2],
        widths=None,
    )
    assert record["dc_difference"]["normalized_l2_difference"] < 1.0e-14
    assert record["fundamental_difference"]["normalized_l2_difference"] < 1.0e-14
    assert (
        record["combined_dc_fundamental_difference"]["normalized_l2_difference"]
        < 1.0e-14
    )
    assert record["T128_to_T256_change"]["normalized_l2_difference"] == 0.0


def test_zero_superposition_component_uses_absolute_near_zero_reporting() -> None:
    zero = np.zeros(256)
    record = superposition_modal_record(
        observed=zero,
        active=zero,
        normal=zero,
        normal_phase_multiplier=1.0j,
        coarse_observed=zero[::2],
        widths=None,
    )
    for key in (
        "dc_difference",
        "fundamental_difference",
        "combined_dc_fundamental_difference",
        "T128_to_T256_change",
    ):
        assert record[key]["status"] == "NEAR_ZERO_COMPONENT"
        assert record[key]["normalized_l2_difference"] is None
        assert record[key]["absolute_difference_norm"] == 0.0


@pytest.mark.parametrize(
    ("conditions", "expected"),
    [
        ({"NORMALIZATION_DOMINANT": True}, "NORMALIZATION_DOMINANT"),
        ({"COMPONENT_BASIS_CANDIDATE": True}, "COMPONENT_BASIS_CANDIDATE"),
        (
            {"EXTRACTION_IMPLEMENTATION_CANDIDATE": True},
            "EXTRACTION_IMPLEMENTATION_CANDIDATE",
        ),
        (
            {"MODE_SELECTIVE_CONSTITUTIVE_MISMATCH": True},
            "MODE_SELECTIVE_CONSTITUTIVE_MISMATCH",
        ),
        (
            {"NORMALIZATION_DOMINANT": True, "MODE_SELECTIVE_CONSTITUTIVE_MISMATCH": True},
            "MIXED",
        ),
        ({}, "INCONCLUSIVE"),
    ],
)
def test_diagnostic_classification_boundaries(
    conditions: dict[str, bool], expected: str
) -> None:
    assert classify_diagnostic_conditions(conditions) == expected


def test_source_formula_audit_finds_shared_clean_extraction_and_conservation() -> None:
    audit = build_source_formula_audit(PROJECT_ROOT)
    assert audit["extraction_audit_clean"] is True
    assert audit["unexpected_inconsistencies"] == []
    assert audit["stress_or_traction_measure"]["Cauchy_or_Piola_conversion_used"] is False
    assert audit["coordinate_convention"]["shared_by_DCM_and_FEM"] is True
    assert audit["projection_conservation_check"]["pass"] is True
    assert all(record["line_end"] >= record["line_start"] for record in audit["evidence"].values())


def test_identity_result_source_lock_passes_and_missing_package_fails_closed(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    lock, snapshot = runner._validate_ledger_package(
        PROJECT_ROOT / runner.EXPECTED_IDENTITY_RESULT
    )
    assert lock["pass"] is True
    assert lock["hash_ledger_entries"] == 10
    assert "hash_ledger.json" in snapshot
    missing_lock, missing_snapshot = runner._validate_ledger_package(tmp_path)
    assert missing_lock["pass"] is False
    assert missing_snapshot == {}


def test_json_writer_is_create_only_and_finite_tree_rejects_nonfinite(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    path = tmp_path / "record.json"
    runner._write_json(path, {"value": 1.0})
    with pytest.raises(FileExistsError):
        runner._write_json(path, {"value": 2.0})
    assert finite_tree({"value": 1.0}) is True
    assert finite_tree({"value": float("nan")}) is False


def test_common_widths_requires_exact_64_segment_grid() -> None:
    widths = common_widths(np.linspace(-0.5, 0.5, 65))
    assert len(widths) == 64
    assert np.sum(widths) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="64 common"):
        common_widths(np.linspace(-0.5, 0.5, 33))
