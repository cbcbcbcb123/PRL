"""Numerical comparison helpers for the EFE path-sensitivity audit."""

from __future__ import annotations

from itertools import combinations

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import spmatrix
from scipy.sparse.linalg import norm as sparse_norm


FloatArray = NDArray[np.float64]


def array_difference_metrics(
    first: FloatArray,
    second: FloatArray,
) -> dict[str, float]:
    """Return scale-symmetric relative and maximum absolute differences."""
    first_array = np.asarray(first, dtype=np.float64)
    second_array = np.asarray(second, dtype=np.float64)
    if first_array.shape != second_array.shape:
        raise ValueError("arrays must have identical shapes")
    if not np.all(np.isfinite(first_array)) or not np.all(
        np.isfinite(second_array)
    ):
        raise ValueError("comparison arrays must be finite")
    delta = first_array - second_array
    denominator = max(
        1.0e-30,
        float(np.linalg.norm(first_array)),
        float(np.linalg.norm(second_array)),
    )
    return {
        "symmetric_relative": float(np.linalg.norm(delta) / denominator),
        "maximum_absolute": (
            0.0 if delta.size == 0 else float(np.max(np.abs(delta)))
        ),
    }


def sparse_difference_metrics(
    first: spmatrix,
    second: spmatrix,
) -> dict[str, float]:
    """Return the same metrics for two sparse matrices."""
    if first.shape != second.shape:
        raise ValueError("sparse matrices must have identical shapes")
    first_csr = first.tocsr()
    second_csr = second.tocsr()
    if not np.all(np.isfinite(first_csr.data)) or not np.all(
        np.isfinite(second_csr.data)
    ):
        raise ValueError("comparison matrices must be finite")
    delta = (first_csr - second_csr).tocsr()
    denominator = max(
        1.0e-30,
        float(sparse_norm(first_csr)),
        float(sparse_norm(second_csr)),
    )
    return {
        "symmetric_relative": float(sparse_norm(delta) / denominator),
        "maximum_absolute": (
            0.0 if delta.nnz == 0 else float(np.max(np.abs(delta.data)))
        ),
    }


def summarize_array_replicates(
    arrays: list[FloatArray],
) -> dict[str, float | int]:
    """Summarize the worst pairwise difference among repeated arrays."""
    if len(arrays) < 2:
        raise ValueError("at least two replicate arrays are required")
    metrics = [
        array_difference_metrics(arrays[first], arrays[second])
        for first, second in combinations(range(len(arrays)), 2)
    ]
    return {
        "replicate_count": len(arrays),
        "pair_count": len(metrics),
        "maximum_symmetric_relative": max(
            metric["symmetric_relative"] for metric in metrics
        ),
        "maximum_absolute": max(
            metric["maximum_absolute"] for metric in metrics
        ),
    }


def summarize_scalar_replicates(values: list[float]) -> dict[str, float | int]:
    """Summarize the range of repeated finite scalar observations."""
    selected = np.asarray(values, dtype=np.float64)
    if len(selected) < 2:
        raise ValueError("at least two scalar replicates are required")
    if not np.all(np.isfinite(selected)):
        raise ValueError("scalar replicates must be finite")
    return {
        "replicate_count": len(values),
        "minimum": float(np.min(selected)),
        "maximum": float(np.max(selected)),
        "range": float(np.ptp(selected)),
    }
