from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WARM_WRAPPER = ROOT / "scripts/prepare_prl_p6_t128_warm_start_v01.py"
CYCLE_WRAPPER = ROOT / "scripts/run_prl_p6_t128_transactional_cycle_v01.py"
TRANSACTION_ENGINE = (
    ROOT / "scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py"
)


def assigned_integer(source: str, name: str) -> int:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                return node.value.value
    raise AssertionError(f"missing integer assignment for {name}")


def test_t128_wrappers_are_registered_and_keep_t64_as_the_frozen_parent() -> None:
    warm_source = WARM_WRAPPER.read_text(encoding="utf-8")
    cycle_source = CYCLE_WRAPPER.read_text(encoding="utf-8")
    assert assigned_integer(warm_source, "TARGET_STEPS") == 128
    assert assigned_integer(cycle_source, "TARGET_STEPS") == 128
    assert "efe_node1_n1_2c_t64_transactional_cycle_v01_20260826" in warm_source
    assert "efe_node1_n1_2c_t64_transactional_cycle_v01_20260826" in cycle_source
    assert "prl_independent_theory_mainline_decision_v01.md" in warm_source
    assert "prl_independent_theory_mainline_decision_v01.md" in cycle_source


def test_t128_wrappers_preserve_create_only_and_256_transaction_guards() -> None:
    warm_source = WARM_WRAPPER.read_text(encoding="utf-8")
    cycle_source = CYCLE_WRAPPER.read_text(encoding="utf-8")
    assert "if output_path.exists():" in warm_source
    assert "raise FileExistsError" in warm_source
    assert "if output_path.exists():" in cycle_source
    assert "raise FileExistsError" in cycle_source
    assert "expected_two_cycle_transaction_count(TARGET_STEPS)" in cycle_source
    assert "for cycle_index in (1, 2):" in cycle_source


def test_transaction_engine_evidence_boundary_uses_the_actual_time_grid() -> None:
    engine_source = TRANSACTION_ENGINE.read_text(encoding="utf-8")
    assert "at T16 only" not in engine_source
    assert "T{STEPS_PER_CYCLE}" in engine_source
