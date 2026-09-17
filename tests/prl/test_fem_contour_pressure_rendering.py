"""Pure in-memory renderer transforms without Matplotlib/cache/result writes."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/prl/rendering/fem_contour_pressure.py"
NAMES = {
    "_q2_closed_curve", "_image_coordinates", "_independent_metric", "_select_states",
    "_validate_geometry", "_residual_tick_plan",
}


def transforms():
    namespace = {"np": np, "RESIDUAL_LIMIT": 2e-6, "RESIDUAL_LINTHRESH": 1e-14}
    for path, names in ((ROOT / "src/prl/rendering/fem_curved_pressure.py", {"_basis"}), (SOURCE, NAMES)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def geometry_fixture():
    angle = np.arange(72)*2*np.pi/72
    curve = np.column_stack((np.cos(angle), np.sin(angle)))
    return {"outer_curve_q2": curve, "source_to_solver_rotation": np.eye(2),
            "image_center_um": np.array([100., 150.]), "length_scale_um": np.array(45.),
            "radial_boundary_fractions": np.array([20/27, 21/27, 22/27, 1.]),
            "layer_ids": np.array([0, 1, 2]), "cells": np.zeros((3, 27), dtype=int),
            "coordinates": np.column_stack((curve, np.zeros(72))),
            "inner_midplane_nodes": np.arange(72), "outer_midplane_nodes": np.arange(72),
            "anchor_node_ids": np.array([0, 36])}


class ContourPressureRenderingTests(unittest.TestCase):
    def setUp(self):
        self.functions = transforms()

    def test_q2_curve_preserves_control_vertices_midpoints_and_closure(self):
        nodes = geometry_fixture()["outer_curve_q2"]
        curve = self.functions["_q2_closed_curve"](nodes, samples_per_segment=4)
        np.testing.assert_allclose(curve[:-1:4], nodes[::2], atol=1e-15)
        np.testing.assert_allclose(curve[2:-1:4], nodes[1::2], atol=1e-15)
        np.testing.assert_array_equal(curve[0], curve[-1])
        self.assertEqual(curve.shape, (145, 2))

    def test_image_mapping_is_exact_inverse_of_saved_rigid_transform(self):
        payload = geometry_fixture()
        angle = .4
        rotation = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])
        payload["source_to_solver_rotation"] = rotation
        original = np.array([[112., 145.], [130., 172.]])
        solver = (original-payload["image_center_um"])/float(payload["length_scale_um"]) @ rotation.T
        restored = self.functions["_image_coordinates"](solver, payload)
        np.testing.assert_allclose(restored, original, rtol=0, atol=2e-14)

    def test_reflection_or_scaling_cannot_masquerade_as_source_rotation(self):
        payload = geometry_fixture()
        for invalid in (np.diag([1., -1.]), np.eye(2)*2, np.ones((3, 3))):
            payload["source_to_solver_rotation"] = invalid
            with self.subTest(transform=invalid), self.assertRaises(ValueError):
                self.functions["_image_coordinates"]([[0., 0.]], payload)

    def test_independent_area_metrics_are_not_recomputed_or_interpolated(self):
        record = {"cases": {"radial_fine": {"states": [
            {"load": 0., "cavity_area_change_fraction": 0.},
            {"load": .04, "cavity_area_change_fraction": .082},
        ]}}}
        values = self.functions["_independent_metric"](record, "radial_fine", [0., .02, .04], "cavity_area_change_fraction")
        np.testing.assert_array_equal(values[[0, 2]], [0., .082])
        self.assertTrue(np.isnan(values[1]))
        self.assertTrue(np.all(np.isnan(self.functions["_independent_metric"](record, "radial_fine", [0., .04], "outer_area_change_fraction"))))

    def test_duplicate_independent_records_are_unavailable(self):
        record = {"cases": {"radial_fine": {"states": [{"load": .02, "metric": 1.}, {"load": .02, "metric": 1.}]}}}
        self.assertTrue(np.isnan(self.functions["_independent_metric"](record, "radial_fine", [.02], "metric")[0]))

    def test_five_states_never_substitute_complete_coarse_for_missing_fine(self):
        coarse = {"radial_coarse": {"loads": np.arange(5)}}
        self.assertEqual(self.functions["_select_states"](coarse, np.arange(5)), [None]*5)
        partial = {**coarse, "radial_fine": {"loads": np.array([0., .02])}}
        self.assertEqual(self.functions["_select_states"](partial, np.arange(5)), [0, 1, None, None, None])

    def test_registered_geometry_display_schema(self):
        payload = geometry_fixture()
        self.functions["_validate_geometry"](payload)
        payload["radial_boundary_fractions"][0] = .5
        with self.assertRaisesRegex(ValueError, "layer fractions"):
            self.functions["_validate_geometry"](payload)

    def test_curve_and_layer_corruption_are_not_silently_drawn(self):
        for key, value in (("outer_curve_q2", np.zeros((70, 2))),
                           ("layer_ids", np.array([0, 1, 3])),
                           ("anchor_node_ids", np.array([0, 1000]))):
            payload = geometry_fixture()
            payload[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.functions["_validate_geometry"](payload)

    def test_no_computational_imports_or_render_side_effect_on_import(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith(("prl.fem", "prl.runs", "prl.verification")) for name in imports))
        top_calls = [node for node in tree.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
        self.assertEqual(len(top_calls), 1)
        self.assertEqual(ast.unparse(top_calls[0].value.func), "matplotlib.use")

    def test_mechanics_figure_contains_contract_required_residual_curve(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('(\"free_force_residual\", 1.0)', source)
        self.assertIn('axis.set_yscale(\"symlog\", linthresh=RESIDUAL_LINTHRESH)', source)
        self.assertIn("axis.yaxis.set_major_locator(FixedLocator(major))", source)
        self.assertIn("axis.yaxis.set_minor_locator(FixedLocator(minor))", source)
        self.assertIn('2e-6 qualification limit', source)

    def test_residual_tick_plan_is_nonnegative_in_range_and_keeps_minor_ticks(self):
        values = np.array([4.7e-12, 9.2e-11, 8.0e-12, 7.4e-12, 1.0e-11])
        upper, major, minor = self.functions["_residual_tick_plan"](values)
        self.assertGreater(upper, 2e-6)
        self.assertGreater(upper, float(values.max()))
        self.assertEqual(major[0], 0.)
        self.assertTrue(np.all((major >= 0) & (major <= upper)))
        self.assertTrue(np.all((minor > 0) & (minor < upper)))
        self.assertGreater(len(minor), 0)
        self.assertFalse(np.any(np.isin(minor, major)))

    def test_residual_tick_plan_does_not_hide_gate_failure_or_zero(self):
        upper, major, minor = self.functions["_residual_tick_plan"]([0., 8e-6])
        self.assertGreater(upper, 8e-6)
        self.assertIn(0., major)
        self.assertTrue(np.all(minor < upper))


if __name__ == "__main__":
    unittest.main()
