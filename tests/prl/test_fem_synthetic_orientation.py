import unittest

import numpy as np

from prl.fem.active_ellipse import build_model
from prl.fem.synthetic_orientation import (
    MAX_OFFSET_DEGREES,
    PATCH_COUNT,
    build_orientation_model,
    generate_patch_offsets,
    paired_sensitivity,
    solve_orientation_cycle,
)


class SyntheticOrientationFemTests(unittest.TestCase):
    def test_frozen_random_field_has_registered_statistics(self):
        first = generate_patch_offsets("synthetic_random")
        second = generate_patch_offsets("synthetic_random")

        np.testing.assert_array_equal(first, second)
        self.assertLessEqual(abs(float(np.mean(first))), 1.0e-12)
        self.assertGreaterEqual(float(np.sqrt(np.mean(first**2))), 4.0)
        self.assertAlmostEqual(float(np.max(np.abs(first))), MAX_OFFSET_DEGREES)

    def test_uniform_field_reproduces_f0_active_directions(self):
        baseline = build_model("G0")
        uniform = build_orientation_model("G0", "uniform")
        myocardium = baseline.cell_layers == 2

        np.testing.assert_allclose(
            uniform.active_strain_unit[myocardium],
            baseline.active_strain_unit[myocardium],
            atol=1.0e-14,
        )
        self.assertEqual(
            set(uniform.patch_ids[myocardium].tolist()), set(range(PATCH_COUNT))
        )
        self.assertTrue(np.all(uniform.patch_ids[~myocardium] == -1))

    def test_paired_g0_cycle_is_safe_and_nonzero(self):
        uniform = solve_orientation_cycle("G0", "uniform", phase_count=9)
        random = solve_orientation_cycle("G0", "synthetic_random", phase_count=9)
        metrics = paired_sensitivity(uniform, random)

        self.assertLessEqual(uniform["maximum_abs_strain"], 0.05)
        self.assertLessEqual(random["maximum_abs_strain"], 0.05)
        self.assertGreater(float(np.min(uniform["minimum_triangle_area"])), 0.0)
        self.assertGreater(float(np.min(random["minimum_triangle_area"])), 0.0)
        self.assertLessEqual(uniform["maximum_backward_residual"], 1.0e-10)
        self.assertLessEqual(random["maximum_backward_residual"], 1.0e-10)
        self.assertGreater(metrics["peak_relative_displacement_l2"], 0.01)
        self.assertGreater(
            metrics["peak_myocardial_equivalent_stress_relative_l2"], 0.01
        )
        np.testing.assert_allclose(uniform["displacements"][0], 0.0, atol=1.0e-13)
        np.testing.assert_allclose(random["displacements"][-1], 0.0, atol=1.0e-13)


if __name__ == "__main__":
    unittest.main()
