"""Exact six-constraint zero-power gauge for otherwise unsupported cases."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def _cross_matrix(vector: FloatArray) -> FloatArray:
    x, y, z = vector
    return np.asarray([
        [0.0, -z, y],
        [z, 0.0, -x],
        [-y, x, 0.0],
    ])


def gauge_matrix(reference_vertices: FloatArray, weights: FloatArray) -> FloatArray:
    if len(reference_vertices) != len(weights) or np.any(weights < 0.0):
        raise ValueError("invalid gauge weights")
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("gauge weights must have positive sum")
    centroid = np.sum(weights[:, None] * reference_vertices, axis=0) / total
    matrix = np.zeros((6, 3 * len(reference_vertices)), dtype=np.float64)
    for vertex_id, (point, weight) in enumerate(zip(reference_vertices, weights, strict=True)):
        columns = slice(3 * vertex_id, 3 * vertex_id + 3)
        matrix[:3, columns] = (weight / total) * np.eye(3)
        matrix[3:, columns] = weight * _cross_matrix(point - centroid)
    if np.linalg.matrix_rank(matrix) != 6:
        raise ValueError("gauge matrix is rank deficient")
    return matrix


def project_zero_gauge_rate(
    velocity: FloatArray,
    reference_vertices: FloatArray,
    weights: FloatArray,
) -> FloatArray:
    matrix = gauge_matrix(reference_vertices, weights)
    flat = velocity.reshape(-1)
    correction = matrix.T @ np.linalg.solve(matrix @ matrix.T, matrix @ flat)
    return (flat - correction).reshape(velocity.shape)


def gauge_rate_and_power(
    velocity: FloatArray,
    reference_vertices: FloatArray,
    weights: FloatArray,
    multipliers: FloatArray,
) -> tuple[FloatArray, float]:
    matrix = gauge_matrix(reference_vertices, weights)
    rate = matrix @ velocity.reshape(-1)
    if multipliers.shape != (6,):
        raise ValueError("gauge multiplier must have six entries")
    return rate, float(np.dot(multipliers, rate))
