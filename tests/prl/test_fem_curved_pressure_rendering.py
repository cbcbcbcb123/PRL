"""In-memory rendering transforms; no Matplotlib cache, plots or science runs.

Extract the pure functions from the real source AST so these unit checks never
initialize Matplotlib or create an output package before the authorized run.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

import numpy as np


SOURCE = Path(__file__).resolve().parents[2] / "src/prl/rendering/fem_curved_pressure.py"
NAMES = {"_basis", "_q2_polygon", "_load_retained", "_independent_radial", "_reference_at", "_cell_von_mises"}


def transforms():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
    namespace = {"np": np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class CurvedPressureRenderingTests(unittest.TestCase):
    def setUp(self):
        self.functions = transforms()

    def test_q2_curved_edge_interpolation_preserves_saved_nodes(self):
        coordinates = np.asarray([[radius*np.cos(angle), radius*np.sin(angle), .25]
                                  for radius in (1., 1.125, 1.25)
                                  for angle in (0., np.pi/4, np.pi/2)])
        face = np.arange(9).reshape(3, 3)
        polygon = self.functions["_q2_polygon"](face, coordinates)
        np.testing.assert_allclose(polygon[[0, 6, 12]], coordinates[[0, 3, 6], :2], atol=1e-15)
        np.testing.assert_allclose(polygon[[13, 19, 25]], coordinates[[6, 7, 8], :2], atol=1e-15)
        # The midpoint lies on the saved quadratic arc, not the corner chord.
        self.assertGreater(float(polygon[19].sum()), float(polygon[13].sum()))
        self.assertEqual(polygon.shape, (52, 2))
        radial = self.functions["_q2_polygon"](face, coordinates, "rz")
        np.testing.assert_allclose(radial[[13, 19, 25], 0], 1.25, atol=1e-15)
        np.testing.assert_allclose(radial[:, 1], .25, atol=1e-15)

    def test_radial_metric_is_independent_record_not_a_nodal_substitute(self):
        record = {"cases": {"fine": {"states": [{"load": 0., "inner_radial_displacement": 0.},
                                                {"load": .02, "inner_radial_displacement": .034}]}}}
        values = self.functions["_independent_radial"](record, "fine", np.array([0., .02, .04]))
        np.testing.assert_array_equal(values[:2], [0., .034])
        self.assertTrue(np.isnan(values[2]))
        self.assertTrue(np.all(np.isnan(self.functions["_independent_radial"]({}, "fine", [0., .02]))))

    def test_duplicate_or_invalid_independent_records_are_unavailable(self):
        states = [{"load": .02, "inner_radial_displacement": .03},
                  {"load": .02, "inner_radial_displacement": .04},
                  {"load": .04, "inner_radial_displacement": float("nan")}]
        values = self.functions["_independent_radial"]({"cases": {"fine": {"states": states}}}, "fine", [.02, .04])
        self.assertTrue(np.all(np.isnan(values)))

    def test_reference_uses_only_matched_retained_independent_loads(self):
        record = {"analytic_reference": {"pressures": [0., .04], "inner_radial_displacement": [0., .07]}}
        values = self.functions["_reference_at"](record, [0., .02, .04])
        np.testing.assert_array_equal(values[[0, 2]], [0., .07])
        self.assertTrue(np.isnan(values[1]))

    def test_total_von_mises_includes_out_of_plane_stress(self):
        stress = np.zeros((2, 1, 27, 3, 3))
        stress[0] = np.eye(3)*7.
        stress[1, 0, 9, 2, 2] = 3.
        values = self.functions["_cell_von_mises"]({"Cauchy": stress})
        np.testing.assert_allclose(values, [[0.], [3.]], atol=1e-15)

    def test_failed_prefix_and_missing_other_case_are_retained_without_padding(self):
        coordinates = np.zeros((27, 3))
        payload = {"loads": np.array([0., .02]), "coordinates": coordinates,
                   "cells": np.arange(27).reshape(1, 27), "displacements": np.zeros((2, 27, 3)),
                   "Cauchy": np.zeros((2, 1, 27, 3, 3)), "Green": np.zeros((2, 1, 27, 3, 3)),
                   "J": np.ones((2, 1, 27))}
        path = Mock()
        path.__truediv__ = Mock(return_value=path)
        path.is_file.side_effect = [True, False]
        self.functions["_load"] = Mock(return_value=payload)
        config = {"loads": [0., .02, .04, .06, .08], "cases": [{"name": "coarse"}, {"name": "fine"}]}
        result = self.functions["_load_retained"](path, config)
        self.assertEqual(set(result), {"coarse"})
        self.assertEqual(len(result["coarse"]["loads"]), 2)
        payload["loads"] = np.array([0., .04])
        path.is_file.side_effect = [True]
        with self.assertRaisesRegex(ValueError, "frozen load prefix"):
            self.functions["_load_retained"](path, config)

    def test_renderer_does_not_import_computational_modules(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith(("prl.fem", "prl.runs", "prl.verification")) for name in imports))


if __name__ == "__main__":
    unittest.main()
