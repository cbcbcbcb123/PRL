import unittest

import numpy as np

from prl.fem.active_ellipse import build_model, solve_cycle


class ActiveEllipticFemTests(unittest.TestCase):
    def test_g0_mesh_is_conforming_and_positive(self):
        model = build_model("G0")

        self.assertEqual(model.coordinates.shape, (432, 2))
        self.assertEqual(model.cells.shape, (768, 3))
        self.assertEqual(set(model.cell_layers.tolist()), {0, 1, 2})
        self.assertGreater(float(np.min(model.areas)), 0.0)
        self.assertEqual(model.constraints.shape, (3, 864))

    def test_g0_active_cycle_has_bounded_nonzero_response(self):
        result = solve_cycle("G0", phase_count=9)
        peak = int(result["peak_index"])

        self.assertLessEqual(float(result["lumen_fraction_change"][peak]), -0.005)
        self.assertLessEqual(float(result["maximum_abs_strain"]), 0.05)
        self.assertLessEqual(float(result["maximum_backward_residual"]), 1.0e-10)
        self.assertLessEqual(float(result["maximum_constraint_residual"]), 1.0e-10)
        self.assertGreater(float(np.min(result["minimum_triangle_area"])), 0.0)
        np.testing.assert_allclose(result["displacements"][0], 0.0, atol=1.0e-13)
        np.testing.assert_allclose(result["displacements"][-1], 0.0, atol=1.0e-13)


if __name__ == "__main__":
    unittest.main()
