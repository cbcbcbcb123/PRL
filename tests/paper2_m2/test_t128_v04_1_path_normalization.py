from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t128_v04_1.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("paper2_m2_t128_v04_1_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_old_relative_path_failure_seam_is_reproduced() -> None:
    relative_source = Path(
        "results/paper2_m2/identity_2d_v03_t64_v01_20260903/pass_summary.json"
    )
    with pytest.raises(ValueError):
        relative_source.relative_to(PROJECT_ROOT)


def test_relative_and_absolute_project_paths_normalize_to_same_target() -> None:
    runner = _load_runner()
    relative = Path("results/paper2_m2/identity_2d_v03_t64_v01_20260903")
    absolute = PROJECT_ROOT / relative
    assert runner.normalize_project_path(relative) == absolute.resolve()
    assert runner.normalize_project_path(absolute) == absolute.resolve()


def test_project_external_path_is_rejected() -> None:
    runner = _load_runner()
    outside = PROJECT_ROOT.parent / "outside-project-probe"
    with pytest.raises(ValueError, match="outside project root"):
        runner.normalize_project_path(outside)


def test_all_path_arguments_are_normalized_before_base_runner_is_called() -> None:
    runner = _load_runner()
    output = Path("results/paper2_m2/v04_1_order_probe_never_created")
    arguments = [
        str(RUNNER_PATH),
        "--output-dir",
        str(output),
        "--contract-v04",
        "project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md",
        "--authorization",
        "project_control/paper2_m2a_v03_t64_supervisor_acceptance_and_t128_decision_v01.md",
        "--source-t64-dir",
        "results/paper2_m2/identity_2d_v03_t64_v01_20260903",
        "--source-calibration",
        "results/paper2_m2/identity_2d_v01_20260903/calibration.json",
        "--v03-execution-record",
        "project_control/paper2_m2a_v03_ledger_repair_and_t64_execution_record_v01.md",
    ]
    normalized, audit = runner.normalize_cli_project_paths(arguments)
    assert audit["normalization_completed_before_base_runner"] is True
    for index, value in enumerate(normalized):
        if index > 0 and normalized[index - 1] in runner.PROJECT_PATH_FLAGS:
            resolved = Path(value)
            assert resolved.is_absolute()
            assert resolved.is_relative_to(PROJECT_ROOT)
    assert not (PROJECT_ROOT / output).exists()
