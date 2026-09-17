"""Algebraic and geometric refinement checks; no measured-data solve or files."""

from dataclasses import replace
import unittest

import numpy as np

from prl.fem.active_ellipse import MeshLevel, assemble_model, polygon_area
from prl.fem.refinement import geometric_quality, refine_model


def tiny_annulus():
    count = 8
    angle = np.arange(count) * (2.0 * np.pi / count)
    outline = np.column_stack((1.2 * np.cos(angle), np.sin(angle)))
    outline *= (1.0 + 0.04 * np.sin(3.0 * angle))[:, None]
    coordinates = np.concatenate([radius * outline for radius in (1.0, 1.2, 1.4, 1.8)])
    coordinates += [0.3, -0.2]
    cells, layers = [], []
    for layer in range(3):
        for index in range(count):
            following = (index + 1) % count
            first, second = layer * count + index, layer * count + following
            third, fourth = first + count, second + count
            cells.extend(([first, third, fourth], [first, fourth, second]))
            layers.extend((layer, layer))
    layers = np.asarray(layers, dtype=np.int64)
    eigenstrain = np.zeros((len(cells), 3))
    for index in np.flatnonzero(layers == 2):
        tangent = np.asarray([np.cos(0.11 * index), np.sin(0.11 * index)])
        eigenstrain[index] = [-tangent[0] ** 2, -tangent[1] ** 2, -2 * np.prod(tangent)]
    return assemble_model(
        MeshLevel("tiny", count, (1, 1, 1)),
        coordinates,
        np.asarray(cells, dtype=np.int64),
        layers,
        np.arange(count, dtype=np.int64),
        np.arange(3 * count, 4 * count, dtype=np.int64),
        eigenstrain,
    )


def unique_edges(cells):
    # Independent test-side edge accounting, not the production helper.
    pairs = []
    for first, second, third in cells:
        pairs.extend((sorted((first, second)), sorted((second, third)), sorted((third, first))))
    return np.unique(np.asarray(pairs), axis=0, return_counts=True)


def strain_and_energy(model, displacement, alpha=0.023):
    strain = np.einsum(
        "eij,ej->ei", model.strain_matrices, displacement.ravel()[model.cell_dofs]
    )
    elastic = strain - alpha * model.active_strain_unit
    constitutive = np.asarray(model.material_matrices)[model.cell_layers]
    energy = 0.5 * np.sum(model.areas * np.einsum("ei,eij,ej->e", elastic, constitutive, elastic))
    return strain, energy


class FemRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = tiny_annulus()
        cls.refined, cls.parent_ids = refine_model(cls.parent, "tiny-R1")

    def test_exact_parent_geometry_area_and_field_inheritance(self):
        parent, refined, indices = self.parent, self.refined, self.parent_ids
        self.assertEqual(len(refined.cells), 4 * len(parent.cells))
        np.testing.assert_array_equal(refined.coordinates[:len(parent.coordinates)], parent.coordinates)
        np.testing.assert_array_equal(indices, np.repeat(np.arange(len(parent.cells)), 4))
        np.testing.assert_array_equal(refined.cell_layers, parent.cell_layers[indices])
        np.testing.assert_array_equal(refined.active_strain_unit, parent.active_strain_unit[indices])
        np.testing.assert_allclose(refined.areas, parent.areas[indices] / 4, rtol=2e-14, atol=2e-16)
        for layer in range(3):
            self.assertAlmostEqual(
                float(np.sum(parent.areas[parent.cell_layers == layer])),
                float(np.sum(refined.areas[refined.cell_layers == layer])), places=14
            )
        self.assertGreater(float(np.min(refined.areas)), 0)
        for name in ("inner_nodes", "outer_nodes"):
            coarse_loop, fine_loop = getattr(parent, name), getattr(refined, name)
            self.assertEqual(len(fine_loop), 2 * len(coarse_loop))
            np.testing.assert_array_equal(fine_loop[::2], coarse_loop)
            expected = 0.5 * (parent.coordinates[coarse_loop] + np.roll(parent.coordinates[coarse_loop], -1, axis=0))
            np.testing.assert_array_equal(refined.coordinates[fine_loop[1::2]], expected)
            self.assertAlmostEqual(polygon_area(parent.coordinates[coarse_loop]), polygon_area(refined.coordinates[fine_loop]), places=14)

    def test_shared_midpoints_form_conforming_mesh_without_extra_boundaries(self):
        parent_edges, _ = unique_edges(self.parent.cells)
        self.assertEqual(len(self.refined.coordinates), len(self.parent.coordinates) + len(parent_edges))
        np.testing.assert_array_equal(
            self.refined.coordinates[len(self.parent.coordinates):],
            np.mean(self.parent.coordinates[parent_edges], axis=1),
        )
        refined_edges, counts = unique_edges(self.refined.cells)
        self.assertTrue(np.all((counts == 1) | (counts == 2)))
        actual_boundary = set(map(tuple, refined_edges[counts == 1].tolist()))
        declared_boundary = set()
        for loop in (self.refined.inner_nodes, self.refined.outer_nodes):
            declared_boundary.update(tuple(sorted((int(first), int(second)))) for first, second in zip(loop, np.roll(loop, -1)))
        self.assertEqual(actual_boundary, declared_boundary)
        # Annulus Euler characteristic is zero; no unexpected holes appeared.
        self.assertEqual(len(self.refined.coordinates) - len(refined_edges) + len(self.refined.cells), 0)

    def test_affine_strain_and_energy_are_identical(self):
        gradient = np.asarray([[0.017, -0.008], [0.003, -0.011]])
        expected_strain = [0.017, -0.011, -0.005]
        energies = []
        works = []
        for model in (self.parent, self.refined):
            displacement = model.coordinates @ gradient.T + [0.031, -0.023]
            strain, energy = strain_and_energy(model, displacement)
            np.testing.assert_allclose(strain, np.tile(expected_strain, (len(model.cells), 1)), atol=1e-15, rtol=0)
            energies.append(energy)
            works.append(float(displacement.ravel() @ model.active_load_unit))
        np.testing.assert_allclose(energies[0], energies[1], rtol=1e-13, atol=1e-16)
        np.testing.assert_allclose(works[0], works[1], rtol=1e-13, atol=1e-16)

    def test_arbitrary_parent_p1_field_is_exactly_nested(self):
        displacement = np.random.default_rng(73).normal(scale=0.001, size=self.parent.coordinates.shape)
        parent_edges, _ = unique_edges(self.parent.cells)
        fine_displacement = np.concatenate((displacement, np.mean(displacement[parent_edges], axis=1)))
        coarse_strain, coarse_energy = strain_and_energy(self.parent, displacement)
        fine_strain, fine_energy = strain_and_energy(self.refined, fine_displacement)
        np.testing.assert_allclose(fine_strain, coarse_strain[self.parent_ids], rtol=1e-12, atol=1e-15)
        np.testing.assert_allclose(fine_energy, coarse_energy, rtol=1e-13, atol=1e-16)
        self.assertAlmostEqual(
            float(displacement.ravel() @ self.parent.stiffness @ displacement.ravel()),
            float(fine_displacement.ravel() @ self.refined.stiffness @ fine_displacement.ravel()), places=14
        )

    def test_deterministic_refinement_preserves_not_improves_angles(self):
        second, second_indices = refine_model(self.parent, "tiny-R1-repeat")
        for name in ("coordinates", "cells", "cell_layers", "active_strain_unit", "inner_nodes", "outer_nodes"):
            np.testing.assert_array_equal(getattr(second, name), getattr(self.refined, name))
        np.testing.assert_array_equal(second_indices, self.parent_ids)
        coarse_quality, fine_quality = geometric_quality(self.parent), geometric_quality(self.refined)
        for name in ("minimum_mean_ratio", "median_mean_ratio", "minimum_angle_degrees", "maximum_edge_aspect_ratio"):
            self.assertAlmostEqual(coarse_quality[name], fine_quality[name], places=11)

    def test_rigid_gauge_is_extended_without_changing_the_parent_frame(self):
        original_dofs = 2 * len(self.parent.coordinates)
        np.testing.assert_array_equal(
            self.refined.constraints[:, :original_dofs].toarray(),
            self.parent.constraints.toarray(),
        )
        self.assertEqual(self.refined.constraints[:, original_dofs:].nnz, 0)
        gauge_matrices = []
        for model in (self.parent, self.refined):
            coordinates = model.coordinates
            motions = np.column_stack((
                np.tile([1.0, 0.0], len(coordinates)),
                np.tile([0.0, 1.0], len(coordinates)),
                np.column_stack((-coordinates[:, 1], coordinates[:, 0])).ravel(),
            ))
            gauge = model.constraints @ motions
            self.assertEqual(np.linalg.matrix_rank(gauge), 3)
            gauge_matrices.append(gauge)
            scale = float(np.max(np.asarray(abs(model.stiffness).sum(axis=1))))
            self.assertLess(float(np.max(np.abs(model.stiffness @ motions))) / scale, 1e-14)
        np.testing.assert_array_equal(gauge_matrices[0], gauge_matrices[1])

    def test_incomplete_boundary_and_changed_material_fail_explicitly(self):
        invalid_loop = self.parent.inner_nodes.copy()
        invalid_loop[[1, 2]] = invalid_loop[[2, 1]]
        with self.assertRaisesRegex(ValueError, "boundary"):
            refine_model(replace(self.parent, inner_nodes=invalid_loop), "invalid-loop")
        material_matrices = tuple(matrix * 2 for matrix in self.parent.material_matrices)
        with self.assertRaisesRegex(ValueError, "material"):
            refine_model(replace(self.parent, material_matrices=material_matrices), "invalid-material")
        with self.assertRaisesRegex(ValueError, "label"):
            refine_model(self.parent, " ")


if __name__ == "__main__":
    unittest.main()
