from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import scipy.sparse as sparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT / "scripts" / "diagnose_paper2_m2a_v02_t64_power_ledger_v01.py"
)
SPEC = importlib.util.spec_from_file_location("power_ledger_diagnostic_v01", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_replay_comparison_skips_runtime_only() -> None:
    old = {"runtime_seconds": 1.0, "nested": {"value": 2.0}, "label": "same"}
    new = {"runtime_seconds": 9.0, "nested": {"value": 2.0}, "label": "same"}
    record = MODULE.replay_record(old, new)
    assert record["pass"] is True
    assert record["maximum_numeric_relative_difference"] == 0.0

    changed = {"runtime_seconds": 9.0, "nested": {"value": 2.1}, "label": "same"}
    assert MODULE.replay_record(old, changed)["pass"] is False


def test_cancellation_summation_policies_are_finite_and_compensated() -> None:
    values = np.asarray((1.0e16, 1.0, -1.0e16, 2.0), dtype=np.float64)
    ordinary = float(MODULE._sum_values(values, "ordinary"))
    pairwise = float(MODULE._sum_values(values, "pairwise"))
    kahan = float(MODULE._sum_values(values, "kahan"))
    longdouble = float(MODULE._sum_values(values, "longdouble"))
    assert all(np.isfinite(value) for value in (ordinary, pairwise, kahan, longdouble))
    assert abs(longdouble - 3.0) <= abs(ordinary - 3.0)
    assert abs(kahan - 3.0) <= abs(ordinary - 3.0)


def test_same_factor_residual_refinement_returns_three_auditable_states() -> None:
    matrix = sparse.csc_matrix(
        np.asarray(
            (
                (1.0, 0.25, 0.0),
                (0.25, 2.0, 0.5),
                (0.0, 0.5, 3.0),
            )
        )
    )
    rhs = np.asarray((1.0, -2.0, 0.5))
    solutions, records = MODULE.factorized_refinement(matrix, rhs, corrections=2)
    assert len(solutions) == 3
    assert [record["corrections"] for record in records] == [0, 1, 2]
    assert all(np.isfinite(record["normwise_backward_error"]) for record in records)


def test_formal_label_mapping_excludes_h2_from_primary_cause() -> None:
    base = {"H1": False, "H2": True, "H3": False, "H4": False, "H5": False}
    assert MODULE.classify_hypotheses(base) == "UNRESOLVED"
    base["H1"] = True
    assert MODULE.classify_hypotheses(base) == "ALGEBRAIC_SOLVE_DEFECT_CONFIRMED"
    base["H3"] = True
    assert MODULE.classify_hypotheses(base) == "MULTIFACTOR"
