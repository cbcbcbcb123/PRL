"""Independent nodal polynomial reconstruction, no Basix/UFL or production imports.

For degree <= 3 on an affine triangle/tetrahedron. Supplied local reference
nodes define the nodal order; this is not a native DOF-map qualification.
"""
from itertools import product
from math import comb

import numpy as np


def powers(dimension, degree):
    if dimension not in (2, 3) or degree not in (1, 2, 3):
        raise ValueError('Only triangle/tetrahedron degrees 1, 2, 3 are supported')
    return np.array([item for total in range(degree + 1)
                     for item in product(range(total + 1), repeat=dimension)
                     if sum(item) == total], dtype=int)


def equispaced_nodes(dimension, degree):
    """Test nodes only. A native export must supply/check its own reference nodes."""
    powers(dimension, degree)
    return np.array([item for item in product(range(degree + 1), repeat=dimension)
                     if sum(item) <= degree], dtype=float) / degree


class SimplexLagrange:
    def __init__(self, nodes, degree):
        nodes = np.array(nodes, dtype=float, copy=True)
        if nodes.ndim != 2 or nodes.shape[1] not in (2, 3):
            raise ValueError('Expected local simplex reference nodes')
        self.dimension = nodes.shape[1]
        self.exponents = powers(self.dimension, degree)
        if nodes.shape[0] != comb(degree + self.dimension, self.dimension):
            raise ValueError('Node count does not match polynomial degree')
        if (not np.isfinite(nodes).all() or nodes.min() < -1e-12
                or np.max(nodes.sum(axis=1)) > 1 + 1e-12):
            raise ValueError('Invalid simplex reference nodes')
        matrix = self._monomials(nodes)
        condition = float(np.linalg.cond(matrix))
        if not np.isfinite(condition) or condition > 1e8:
            raise ValueError('Singular or ill-conditioned nodal interpolation')
        self.coefficients = np.linalg.solve(matrix, np.eye(len(nodes)))
        self.nodes = nodes
        self.degree = degree

    def _monomials(self, points):
        return np.prod(points[:, None, :] ** self.exponents[None, :, :], axis=-1)

    def tabulate(self, points):
        points = np.asarray(points, dtype=float)
        if (points.ndim != 2 or points.shape[1] != self.dimension
                or not np.isfinite(points).all()):
            raise ValueError('Invalid evaluation points')
        values = self._monomials(points) @ self.coefficients
        derivatives = []
        for axis in range(self.dimension):
            exponents = self.exponents.copy()
            factor = exponents[:, axis].copy()
            exponents[:, axis] = np.maximum(0, factor - 1)
            derivative = np.prod(points[:, None, :] ** exponents[None, :, :], axis=-1)
            derivatives.append((derivative * factor) @ self.coefficients)
        return values, np.stack(derivatives, axis=-1)
