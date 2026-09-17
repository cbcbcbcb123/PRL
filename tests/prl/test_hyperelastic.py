"""In-memory constitutive checks independent of any organ-scale simulation."""

import unittest

import numpy as np

from prl.fem.hyperelastic import material_response


MATERIALS = (
    {"model": "neo_hookean", "mu": 1.3},
    {"model": "guccione", "C": 1.1, "bff": 8.0, "bxx": 2.0, "bfx": 4.0},
)


def rotation(angle=0.67):
    axis = np.array([1.0, 2.0, -1.0]) / np.sqrt(6.0)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * cross @ cross


def independent_energy(gradient, material, fiber=(1.0, 0.0, 0.0)):
    """Test-side scalar invariant expression, not a production helper."""
    determinant = np.linalg.det(gradient)
    strain = 0.5 * (gradient.T @ gradient / determinant ** (2.0 / 3.0) - np.eye(3))
    if material["model"] == "neo_hookean":
        energy = material["mu"] * np.trace(strain)
    else:
        # These tests use f=e1.  Write all nine terms explicitly.
        exponent = (
            material["bff"] * strain[0, 0] ** 2
            + material["bxx"] * (strain[1, 1] ** 2 + strain[2, 2] ** 2 + strain[1, 2] ** 2 + strain[2, 1] ** 2)
            + material["bfx"] * (strain[0, 1] ** 2 + strain[1, 0] ** 2 + strain[0, 2] ** 2 + strain[2, 0] ** 2)
        )
        energy = 0.5 * material["C"] * np.expm1(exponent)
    f0 = np.array(fiber, dtype=float)
    f0 /= np.linalg.norm(f0)
    return energy + 0.5 * material.get("active_tension", 0.0) * (np.dot(gradient @ f0, gradient @ f0) - 1.0)


class HyperelasticTests(unittest.TestCase):
    def setUp(self):
        self.gradient = np.array([[1.17, 0.11, -0.03], [0.04, 0.91, 0.08], [0.01, -0.02, 1.06]])
        self.variation = np.array([[0.4, -0.2, 0.1], [0.3, -0.1, 0.25], [0.1, 0.2, -0.2]])

    def test_stress_free_identity_and_uniform_dilatation(self):
        for material in MATERIALS:
            for scale in (0.7, 1.0, 1.3):
                with self.subTest(material=material["model"], scale=scale):
                    response = material_response(scale * np.eye(3), material)
                    self.assertAlmostEqual(float(response["energy"]), 0.0, places=13)
                    np.testing.assert_allclose(response["P"], 0.0, atol=2e-14)

    def test_energy_first_derivative_by_all_component_difference(self):
        step = 2e-6
        for baseline in MATERIALS:
            for tension in (0.0, 0.31):
                material = dict(baseline, active_tension=tension)
                response = material_response(self.gradient, material)
                differentiated = np.empty((3, 3))
                for first in range(3):
                    for second in range(3):
                        perturbation = np.zeros((3, 3))
                        perturbation[first, second] = step
                        differentiated[first, second] = (
                            independent_energy(self.gradient + perturbation, material)
                            - independent_energy(self.gradient - perturbation, material)
                        ) / (2.0 * step)
                np.testing.assert_allclose(response["P"], differentiated, rtol=2e-7, atol=2e-9)

    def test_consistent_tangent_by_all_component_difference(self):
        step = 2e-6
        for baseline in MATERIALS:
            material = dict(baseline, active_tension=0.23)
            response = material_response(self.gradient, material, fiber=[2.0, -1.0, 0.5])
            differentiated = np.empty((3, 3, 3, 3))
            for first in range(3):
                for second in range(3):
                    perturbation = np.zeros((3, 3))
                    perturbation[first, second] = step
                    differentiated[..., first, second] = (
                        material_response(self.gradient + perturbation, material, fiber=[2.0, -1.0, 0.5])["P"]
                        - material_response(self.gradient - perturbation, material, fiber=[2.0, -1.0, 0.5])["P"]
                    ) / (2.0 * step)
            np.testing.assert_allclose(response["tangent"], differentiated, rtol=3e-7, atol=3e-9)

    def test_energy_second_directional_difference(self):
        step = 1e-4
        for baseline in MATERIALS:
            material = dict(baseline, active_tension=0.3)
            response = material_response(self.gradient, material)
            predicted = np.einsum("iJ,iJkL,kL->", self.variation, response["tangent"], self.variation)
            observed = (
                independent_energy(self.gradient + step * self.variation, material)
                - 2.0 * independent_energy(self.gradient, material)
                + independent_energy(self.gradient - step * self.variation, material)
            ) / step ** 2
            np.testing.assert_allclose(predicted, observed, rtol=3e-6, atol=1e-7)

    def test_major_tangent_symmetry(self):
        for material in MATERIALS:
            tangent = material_response(self.gradient, dict(material, active_tension=0.17))["tangent"]
            np.testing.assert_allclose(tangent, tangent.transpose(2, 3, 0, 1), rtol=2e-13, atol=3e-13)

    def test_frame_indifference_with_passive_and_active_parts(self):
        spatial_rotation = rotation()
        for material in MATERIALS:
            material = dict(material, active_tension=0.2)
            reference = material_response(self.gradient, material, fiber=[1.0, 0.7, 0.3])
            rotated = material_response(spatial_rotation @ self.gradient, material, fiber=[1.0, 0.7, 0.3])
            np.testing.assert_allclose(rotated["energy"], reference["energy"], atol=2e-14)
            np.testing.assert_allclose(rotated["P"], spatial_rotation @ reference["P"], atol=2e-13)
            reference_increment = np.einsum("iJkL,kL->iJ", reference["tangent"], self.variation)
            rotated_increment = np.einsum("iJkL,kL->iJ", rotated["tangent"], spatial_rotation @ self.variation)
            np.testing.assert_allclose(rotated_increment, spatial_rotation @ reference_increment, atol=3e-13)

    def test_rigid_rotation_is_stress_free_when_inactive(self):
        for material in MATERIALS:
            response = material_response(rotation(1.9), material)
            np.testing.assert_allclose(response["energy"], 0.0, atol=1e-14)
            np.testing.assert_allclose(response["P"], 0.0, atol=4e-14)

    def test_active_lagrangian_tension_is_not_constant_cauchy_tension(self):
        tension = 0.4
        stretch = 0.8
        gradient = np.diag([stretch, stretch ** -0.5, stretch ** -0.5])
        inactive = material_response(gradient, MATERIALS[0])
        active = material_response(gradient, dict(MATERIALS[0], active_tension=tension))
        piola_increment = active["P"] - inactive["P"]
        np.testing.assert_allclose(piola_increment, np.diag([tension * stretch, 0.0, 0.0]), atol=1e-14)
        cauchy_increment = piola_increment @ gradient.T / active["J"]
        self.assertAlmostEqual(cauchy_increment[0, 0], tension * stretch ** 2)
        self.assertNotAlmostEqual(cauchy_increment[0, 0], tension)

    def test_neo_hookean_isotropy_and_guccione_directionality(self):
        fiber_stretch = np.diag([1.2, 1.2 ** -0.5, 1.2 ** -0.5])
        cross_stretch = fiber_stretch[np.ix_([1, 0, 2], [1, 0, 2])]
        first = material_response(fiber_stretch, MATERIALS[0])["energy"]
        second = material_response(cross_stretch, MATERIALS[0])["energy"]
        np.testing.assert_allclose(first, second, atol=1e-14)
        first = material_response(fiber_stretch, MATERIALS[1])["energy"]
        second = material_response(cross_stretch, MATERIALS[1])["energy"]
        self.assertGreater(first, second)

    def test_fiber_normalization_and_sign_invariance(self):
        for material in MATERIALS:
            material = dict(material, active_tension=0.13)
            first = material_response(self.gradient, material, fiber=[1.0, 0.5, -0.3])
            second = material_response(self.gradient, material, fiber=[-10.0, -5.0, 3.0])
            for key in first:
                np.testing.assert_allclose(first[key], second[key], rtol=2e-13, atol=2e-13)

    def test_batch_matches_separate_material_points(self):
        gradients = np.stack([self.gradient, rotation() @ self.gradient, np.eye(3), 1.4 * self.gradient]).reshape(2, 2, 3, 3)
        for material in MATERIALS:
            batch = material_response(gradients, material)
            self.assertEqual(batch["energy"].shape, (2, 2))
            self.assertEqual(batch["tangent"].shape, (2, 2, 3, 3, 3, 3))
            for first in range(2):
                for second in range(2):
                    scalar = material_response(gradients[first, second], material)
                    for key in scalar:
                        np.testing.assert_allclose(batch[key][first, second], scalar[key], atol=1e-13)

    def test_rejects_invalid_deformation_gradient(self):
        invalid = (np.eye(2), np.zeros((3, 3)), np.diag([-1.0, 1.0, 1.0]), np.full((3, 3), np.nan), np.eye(3) * (1.0 + 1e-5j))
        for gradient in invalid:
            with self.subTest(gradient=gradient):
                with self.assertRaises(ValueError):
                    material_response(gradient, MATERIALS[0])

    def test_rejects_invalid_material_values(self):
        invalid = (None, {}, {"model": "linear"}, {"model": "neo_hookean"})
        for material in invalid:
            with self.assertRaises(ValueError):
                material_response(np.eye(3), material)
        for baseline in MATERIALS:
            for key in (set(baseline) - {"model"}):
                for value in (0.0, -1.0, np.nan, np.inf, True, "not_numeric"):
                    with self.assertRaises(ValueError):
                        material_response(np.eye(3), dict(baseline, **{key: value}))
            for value in (-1.0, np.nan, np.inf, True):
                with self.assertRaises(ValueError):
                    material_response(np.eye(3), dict(baseline, active_tension=value))

    def test_rejects_invalid_fibers(self):
        for fiber in ([0.0, 0.0, 0.0], [1.0, 0.0], [1.0, np.nan, 0.0], [1.0, 0.0, 1j]):
            with self.assertRaises(ValueError):
                material_response(np.eye(3), MATERIALS[1], fiber=fiber)

    def test_rejects_exponential_overflow(self):
        with self.assertRaises(ValueError):
            material_response(np.diag([20.0, 0.5, 0.5]), MATERIALS[1])


if __name__ == "__main__":
    unittest.main()
