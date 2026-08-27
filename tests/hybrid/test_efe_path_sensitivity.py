from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from hybrid.efe_path_sensitivity import (
    array_difference_metrics,
    sparse_difference_metrics,
    summarize_array_replicates,
    summarize_scalar_replicates,
)


def test_array_difference_is_zero_and_scale_symmetric() -> None:
    first = np.asarray([1.0, -2.0, 3.0])
    identical = array_difference_metrics(first, first.copy())
    assert identical == {"symmetric_relative": 0.0, "maximum_absolute": 0.0}

    second = np.asarray([1.0, -1.5, 2.5])
    forward = array_difference_metrics(first, second)
    reverse = array_difference_metrics(second, first)
    assert forward == reverse


def test_array_difference_rejects_shape_and_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="identical shapes"):
        array_difference_metrics(np.zeros(2), np.zeros(3))
    with pytest.raises(ValueError, match="finite"):
        array_difference_metrics(np.asarray([np.nan]), np.zeros(1))


def test_sparse_difference_matches_dense_result() -> None:
    first = np.asarray([[2.0, 0.0], [1.0, 3.0]])
    second = np.asarray([[2.0, 0.0], [1.5, 3.0]])
    sparse_metrics = sparse_difference_metrics(
        csr_matrix(first), csr_matrix(second)
    )
    dense_metrics = array_difference_metrics(first, second)
    assert sparse_metrics == pytest.approx(dense_metrics)


def test_replicate_summary_reports_worst_pair() -> None:
    summary = summarize_array_replicates(
        [np.zeros(2), np.asarray([1.0, 0.0]), np.asarray([2.0, 0.0])]
    )
    assert summary["replicate_count"] == 3
    assert summary["pair_count"] == 3
    assert summary["maximum_absolute"] == pytest.approx(2.0)
    assert summary["maximum_symmetric_relative"] == pytest.approx(1.0)


def test_scalar_replicate_summary_requires_finite_pair() -> None:
    summary = summarize_scalar_replicates([2.0, 2.5, 3.0])
    assert summary["range"] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="at least two"):
        summarize_scalar_replicates([1.0])
    with pytest.raises(ValueError, match="finite"):
        summarize_scalar_replicates([1.0, np.inf])
