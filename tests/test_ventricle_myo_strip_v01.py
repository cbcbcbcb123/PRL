from __future__ import annotations

import csv
import math
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_myo_strip_v01.cpp"
CMAKE = PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "CMakeLists.txt"
INPUT_NODES = (
    PROJECT_ROOT
    / "results"
    / "ventricle_z1"
    / "z1_bioform_myo_r_v03_20260913"
    / "raw"
    / "FULL_M320_DT020"
    / "nodes.csv"
)
INPUT_FACES = INPUT_NODES.with_name("faces.csv")


class MyocardialStripContractTests(unittest.TestCase):
    def test_production_target_is_registered_and_excludes_shape_reference_terms(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        cmake = CMAKE.read_text(encoding="utf-8")
        self.assertIn("add_executable(prl_ventricle_myo_strip_v01", cmake)
        self.assertIn("PRL_MYO_BENDING_MODULUS=0.0", cmake.split("add_executable(prl_ventricle_myo_strip_v01", 1)[1])
        self.assertIn("reference_edge_shape_terms", source)
        self.assertIn("reference_face_metric_terms", source)
        self.assertIn("target_geometry_used", source)
        self.assertIn('<< "  \\"reference_edge_shape_terms\\": 0,', source)
        self.assertIn('<< "  \\"target_geometry_used\\": false,', source)
        self.assertIn("kStripDampingDensity = 1.0", source)

    def test_frozen_conditions_and_material_links_are_explicit(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for condition in ("PASSIVE", "SYNC", "CENTER", "CENTER_NO_LINK"):
            self.assertIn(f'"{condition}"', source)
        self.assertIn("config.junctions_enabled = config.condition != \"CENTER_NO_LINK\"", source)
        self.assertIn("field[spring.body_a][spring.node_a] = add", source)
        self.assertIn("field[spring.body_b][spring.node_b] = subtract", source)
        self.assertIn("target_geometry_used", source)

    def test_activation_is_zero_at_ends_and_one_at_midcycle(self) -> None:
        activation = lambda phase: math.sin(math.pi * phase) ** 2
        self.assertAlmostEqual(activation(0.0), 0.0)
        self.assertAlmostEqual(activation(0.5), 1.0)
        self.assertAlmostEqual(activation(1.0), 0.0, places=14)

    def test_frozen_snapshot_has_expected_topology_and_seven_node_caps(self) -> None:
        with INPUT_NODES.open(encoding="utf-8", newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if int(row["snapshot_index"]) == 8]
        with INPUT_FACES.open(encoding="utf-8", newline="") as stream:
            faces = [row for row in csv.DictReader(stream) if int(row["snapshot_index"]) == 8]
        self.assertEqual(len(rows), 162)
        self.assertEqual(len(faces), 320)
        xs = [float(row["x"]) for row in rows]
        cap = 0.88 * max(xs)
        self.assertEqual(sum(value >= cap for value in xs), 7)
        self.assertEqual(sum(value <= -cap for value in xs), 7)


if __name__ == "__main__":
    unittest.main()
