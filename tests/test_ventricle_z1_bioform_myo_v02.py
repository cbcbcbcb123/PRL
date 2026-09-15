from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ventricle_bioform_myo_common import (  # noqa: E402
    CONDITION_MATRIX,
    snapshot_geometry,
    symmetric_chamfer_rms,
)


class BioformMyocardiumContractTests(unittest.TestCase):
    def test_formal_matrix_is_exactly_frozen_eight_conditions(self) -> None:
        self.assertEqual(
            [item["id"] for item in CONDITION_MATRIX],
            [
                "FULL_M320_DT020",
                "ABLATION_M320_DT020",
                "PERTURBED_M320_DT020",
                "ROTATED37_M320_DT020",
                "FULL_M080_DT020",
                "FULL_M1280_DT020",
                "FULL_M320_DT040",
                "FULL_M320_DT010",
            ],
        )

    def test_contract_and_source_exclude_target_geometry(self) -> None:
        contract = (PROJECT_ROOT / "project_control" / "ventricle_bioform_myocardium_free_state_contract_v02.md").read_text(encoding="utf-8")
        source = (PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_bioform_myo.cpp").read_text(encoding="utf-8")
        self.assertIn("reference_edge_shape_terms = 0", contract)
        self.assertIn("reference_face_metric_terms = 0", contract)
        self.assertIn("target_geometry_used = false", contract)
        self.assertIn('\\"reference_edge_shape_terms\\": 0', source)
        self.assertNotIn("reference_edge_length", source)

    def test_source_contains_normal_shape_traction_and_rigid_mode_correction(self) -> None:
        source = (PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_bioform_myo.cpp").read_text(encoding="utf-8")
        self.assertIn("dot(normal, stress_traction)", source)
        self.assertIn("translation_correction", source)
        self.assertIn("rotation_correction", source)
        self.assertIn("0.55", source)

    def test_snapshot_geometry_detects_closed_sphere_topology(self) -> None:
        points = np.array(
            [
                [1.3, 0.0, 0.0],
                [-1.3, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, -1.0, 0.0],
                [0.0, 0.0, 0.7],
                [0.0, 0.0, -0.7],
            ]
        )
        faces = [
            (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
            (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
        ]
        base_fields = {
            "nodal_area": "1", "curvature": "1", "internal_pressure": "0",
            "passive_fx": "0", "passive_fy": "0", "passive_fz": "0",
            "cytoskeleton_fx": "0", "cytoskeleton_fy": "0", "cytoskeleton_fz": "0",
            "total_fx": "0", "total_fy": "0", "total_fz": "0",
            "cytoskeleton_traction": "0", "total_traction": "0",
        }
        node_rows = []
        for index, point in enumerate(points):
            row = {
                "snapshot_index": "0", "phase": "initial", "solver_coordinate": "0",
                "load_fraction": "0", "relaxation_fraction": "0", "node_index": str(index),
                "x": str(point[0]), "y": str(point[1]), "z": str(point[2]),
            }
            row.update(base_fields)
            node_rows.append(row)
        face_rows = [
            {"snapshot_index": "0", "n1": str(a), "n2": str(b), "n3": str(c)}
            for a, b, c in faces
        ]
        metrics = snapshot_geometry(
            node_rows,
            face_rows,
            (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])),
        )
        self.assertTrue(metrics["closed_manifold"])
        self.assertEqual(metrics["euler_characteristic"], 2)
        self.assertTrue(metrics["sphere_topology"])
        self.assertGreater(metrics["E_pq"], 1.0)
        self.assertGreater(metrics["F_qr"], 1.0)

    def test_symmetric_chamfer_is_zero_for_identical_clouds(self) -> None:
        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertAlmostEqual(symmetric_chamfer_rms(points, points.copy()), 0.0, places=15)

    def test_runner_verifier_and_renderer_import(self) -> None:
        for filename in (
            "run_ventricle_z1_bioform_myo_v02.py",
            "verify_ventricle_z1_bioform_myo_v02.py",
            "render_ventricle_z1_bioform_myo_v02.py",
        ):
            specification = importlib.util.spec_from_file_location(filename, SCRIPTS / filename)
            self.assertIsNotNone(specification)


if __name__ == "__main__":
    unittest.main()
