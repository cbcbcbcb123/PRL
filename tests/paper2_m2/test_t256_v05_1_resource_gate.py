from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from paper2_m2.config import FROZEN_CONFIG
from paper2_m2.protocol_v05_1 import (
    ENDPOINT_RUNTIME_BUDGET_SECONDS,
    OBSERVED_V05_FAILURE_RUNTIME_SECONDS,
    endpoint_runtime_gate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_paper2_m2_identity_2d_t256_v05_1.py"
EXPECTED_V05_HASHES = {
    "src/paper2_m2/protocol_v05.py": "c133c834c5559104e87b4c84eb639256401400409b92ea453d8332759c07b97b",
    "src/paper2_m2/identity_2d_v05.py": "1f06242f89b231b61ca73d31097cd35eca700f1fd6d4f36ca6c7f537ea1d0be7",
    "scripts/run_paper2_m2_identity_2d_t256_v05.py": "2fd2fda0e0d7999b786e9d372a9dcd9353e48ab4819cd390b43f097681e0b039",
    "tests/paper2_m2/test_protocol_v05.py": "8694cd7d316b3e0a751656558fd187abf4e35ef606eb54ee643b43f91cf6cf28",
    "tests/paper2_m2/test_identity_2d_v05.py": "4c4459fe1769f4dc5cc9fb220329bad77c6cb2df3b3ffe6b9f0051462628de48",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runner():
    spec = importlib.util.spec_from_file_location("paper2_m2_t256_v05_1_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_observed_runtime_fails_old_gate_and_passes_v05_1_gate() -> None:
    assert FROZEN_CONFIG.endpoint_runtime_budget_seconds == 30.0
    assert OBSERVED_V05_FAILURE_RUNTIME_SECONDS > FROZEN_CONFIG.endpoint_runtime_budget_seconds
    assert endpoint_runtime_gate(OBSERVED_V05_FAILURE_RUNTIME_SECONDS)["pass"] is True
    assert endpoint_runtime_gate(ENDPOINT_RUNTIME_BUDGET_SECONDS)["pass"] is True
    assert endpoint_runtime_gate(ENDPOINT_RUNTIME_BUDGET_SECONDS + 1.0e-9)["pass"] is False
    assert endpoint_runtime_gate(float("nan"))["pass"] is False


def test_v05_implementation_hashes_remain_frozen() -> None:
    assert {
        relative: _sha256(PROJECT_ROOT / relative)
        for relative in EXPECTED_V05_HASHES
    } == EXPECTED_V05_HASHES


def test_v05_1_runner_normalizes_paths_before_output_or_production_load() -> None:
    runner = _load_runner()
    output = Path("results/paper2_m2/v05_1_order_probe_never_created")
    arguments = [
        str(RUNNER_PATH),
        "--output-dir",
        str(output),
        "--contract-v05",
        "project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md",
        "--authorization",
        "project_control/paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md",
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
    assert audit["normalization_completed_before_production_load"] is True
    assert audit["normalization_completed_before_output_creation"] is True
    for index, value in enumerate(normalized):
        if index > 0 and normalized[index - 1] in runner.PROJECT_PATH_FLAGS:
            resolved = Path(value)
            assert resolved.is_absolute()
            assert resolved.is_relative_to(PROJECT_ROOT)
    outside = PROJECT_ROOT.parent / "outside-project-probe"
    try:
        runner.normalize_project_path(outside)
    except ValueError as error:
        assert "outside project root" in str(error)
    else:
        raise AssertionError("project-external path was not rejected")
    assert not (PROJECT_ROOT / output).exists()


def test_v05_1_files_have_exactly_one_terminal_newline() -> None:
    files = (
        PROJECT_ROOT / "src" / "paper2_m2" / "protocol_v05_1.py",
        RUNNER_PATH,
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_protocol_v05_1.py",
        PROJECT_ROOT / "tests" / "paper2_m2" / "test_t256_v05_1_resource_gate.py",
    )
    for path in files:
        data = path.read_bytes()
        assert data.endswith(b"\n")
        assert not data.endswith(b"\n\n")
