from pathlib import Path
import unittest

import numpy as np

from prl.runs.contact_performance_equilibrium import (
    ContactTaskContractError,
    _bounded_result,
)
from prl.verification.contact_performance_equilibrium import (
    _adjacent_normal_minimum,
    _balance,
    _mesh_metrics,
)


ROOT = Path(__file__).resolve().parents[2]


class ContactTaskContractTests(unittest.TestCase):
    def test_result_must_remain_inside_workspace(self):
        self.assertEqual(_bounded_result(ROOT, "results/example"), ROOT / "results/example")
        with self.assertRaises(ContactTaskContractError):
            _bounded_result(ROOT, ROOT.parent / "outside")

    def test_independent_geometry_metrics_on_closed_tetrahedron(self):
        points = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        triangles = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        metrics = _mesh_metrics(points, triangles)
        self.assertAlmostEqual(metrics["volume"], 1.0 / 6.0)
        self.assertGreater(metrics["min_angle"], 44.9)
        self.assertEqual(metrics["adjacent_cosine"], _adjacent_normal_minimum(points, triangles))

    def test_force_and_torque_balance_is_independently_recomputed(self):
        dtype = [(name, float) for name in ("x", "y", "z", "fx", "fy", "fz")]
        nodes = np.zeros(2, dtype=dtype)
        nodes["x"] = (-1, 1)
        nodes["fy"] = (2, -2)
        force_residual, torque_residual = _balance(nodes)
        self.assertEqual(force_residual, 0.0)
        self.assertEqual(torque_residual, 1.0)


if __name__ == "__main__":
    unittest.main()
