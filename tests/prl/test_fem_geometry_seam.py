"""Geometry-seam regression and affine patch tests (no biological claims)."""

import unittest

import numpy as np

from prl.fem.active_ellipse import (
    MeshLevel,
    assemble_model,
    build_model,
    solve_cycle,
    solve_model_cycle,
)


def perturbed_model():
    reference = build_model("G0")
    coordinates = reference.coordinates.copy()
    angle = np.arctan2(coordinates[:, 1], coordinates[:, 0] / 1.25)
    coordinates *= (1.0 + 0.06 * np.cos(3.0 * angle))[:, None]
    coordinates[:, 0] += 0.04 * coordinates[:, 1] ** 2
    # Translation exercises the rigid-motion gauge away from the origin.
    coordinates += np.asarray([0.7, -0.4])
    eigenstrain = np.tile([-1.0, 0.3, 0.2], (len(reference.cells), 1))
    return assemble_model(
        MeshLevel("nonelliptic_patch", 48, (2, 2, 4)),
        coordinates,
        reference.cells,
        reference.cell_layers,
        reference.inner_nodes,
        reference.outer_nodes,
        eigenstrain,
    )


class FemGeometrySeamTests(unittest.TestCase):
    def test_elliptic_f0_regression_is_unchanged(self):
        # Frozen before extracting the general geometry seam, from the original
        # F0 implementation with five engineering-test phases.
        result = solve_cycle("G0", phase_count=5)
        expected = {
            "maximum_abs_strain": 0.046143160150212914,
            "maximum_equivalent_stress": 0.03809577680334276,
            "peak_inner_long_span": 2.3975319240431485,
            "peak_inner_short_span": 1.9615345955140189,
        }
        for key, value in expected.items():
            np.testing.assert_allclose(result[key], value, rtol=1.0e-11, atol=1.0e-13)
        expected_peak = {
            "lumen_area": 3.680704598400096,
            "outer_area": 6.818548739342008,
            "lumen_fraction_change": -0.06003422613323277,
            "outer_fraction_change": -0.04455544718015755,
            "stored_energy": 0.0003796641401467549,
            "minimum_triangle_area": 0.001996882817949284,
        }
        for key, value in expected_peak.items():
            np.testing.assert_allclose(result[key][2], value, rtol=1.0e-11, atol=1.0e-13)
        expected_displacements = [
            [-0.0512340379784262, -2.3462754256547702e-05],
            [0.0001856143504732523, -0.019232702242989362],
            [-0.05087534948829268, -2.2163537866820027e-05],
            [0.050550642194392675, 2.2613988502031445e-05],
            [-0.05012597055042722, 0.004519550745337751],
        ]
        np.testing.assert_allclose(
            result["displacements"][2, [0, 12, 48, 120, 431]],
            expected_displacements,
            rtol=1.0e-11,
            atol=1.0e-13,
        )
        direct = solve_model_cycle(result["model"], phase_count=5)
        for key, values in result.items():
            if isinstance(values, np.ndarray):
                np.testing.assert_array_equal(direct[key], values)
        self.assertEqual(direct["level"], "G0")

    def test_nonelliptic_mesh_preserves_rigid_modes_and_affine_strain(self):
        model = perturbed_model()
        coordinates = model.coordinates
        rigid_modes = [
            np.tile([1.0, 0.0], len(coordinates)),
            np.tile([0.0, 1.0], len(coordinates)),
            np.column_stack([-coordinates[:, 1], coordinates[:, 0]]).ravel(),
        ]
        stiffness_scale = np.max(np.asarray(abs(model.stiffness).sum(axis=1)))
        for motion in rigid_modes:
            residual = np.max(np.abs(model.stiffness @ motion))
            self.assertLess(residual / (stiffness_scale * np.max(abs(motion))), 1.0e-13)
        gradient = np.asarray([[0.012, 0.008], [-0.002, -0.009]])
        displacement = (coordinates @ gradient.T + [0.01, -0.03]).ravel()
        computed = np.einsum(
            "eij,ej->ei", model.strain_matrices, displacement[model.cell_dofs]
        )
        expected = np.tile([0.012, -0.009, 0.006], (len(model.cells), 1))
        np.testing.assert_allclose(computed, expected, atol=1.0e-13, rtol=0)

    def test_nonelliptic_uniform_eigenstrain_has_zero_elastic_stress(self):
        # A uniform compatible eigenstrain has an affine, stress-free solution
        # for any geometry and heterogeneous elastic material assignment.
        model = perturbed_model()
        result = solve_model_cycle(model, phase_count=5)
        expected = result["activation"][:, None, None] * model.active_strain_unit[None]
        np.testing.assert_allclose(result["strains"], expected, atol=2.0e-12, rtol=0)
        np.testing.assert_allclose(result["stresses"], 0.0, atol=2.0e-11, rtol=0)
        self.assertLess(result["maximum_backward_residual"], 1.0e-12)
        self.assertLess(result["maximum_constraint_residual"], 1.0e-12)
        self.assertGreater(np.min(result["minimum_triangle_area"]), 0.0)
        self.assertEqual(result["level"], "nonelliptic_patch")

    def test_invalid_geometry_and_fields_fail_before_assembly(self):
        reference = build_model("G0")
        arguments = dict(
            level=reference.level,
            coordinates=reference.coordinates,
            cells=reference.cells,
            cell_layers=reference.cell_layers,
            inner_nodes=reference.inner_nodes,
            outer_nodes=reference.outer_nodes,
            active_strain_unit=reference.active_strain_unit,
        )
        invalid_coordinates = reference.coordinates.copy()
        invalid_coordinates[0, 0] = np.nan
        inverted_cells = reference.cells.copy()
        inverted_cells[0] = inverted_cells[0, ::-1]
        invalid_values = (
            ("coordinates", invalid_coordinates),
            ("cells", inverted_cells),
            ("cells", reference.cells.astype(float)),
            ("cell_layers", np.full(len(reference.cells), 3)),
            ("inner_nodes", reference.inner_nodes[::-1]),
            ("active_strain_unit", np.zeros((len(reference.cells), 2))),
        )
        for name, values in invalid_values:
            with self.subTest(name=name), self.assertRaises(ValueError):
                assemble_model(**{**arguments, name: values})


if __name__ == "__main__":
    unittest.main()
