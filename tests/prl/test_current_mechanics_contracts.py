from pathlib import Path
import unittest

import numpy as np

from prl.verification.contact_performance_equilibrium import _adjacent_normal_minimum


ROOT = Path(__file__).resolve().parents[2]


class CurrentMechanicsContractTests(unittest.TestCase):
    def test_shared_edge_fold_monitor_rejects_inverted_neighbor(self):
        points = np.array([[0.0, 0, 0], [1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0]])
        triangles = np.array([[0, 1, 2], [1, 0, 3]])
        self.assertAlmostEqual(_adjacent_normal_minimum(points, triangles), 1.0)
        points[3] = [0, 0.8, 0]
        self.assertLessEqual(_adjacent_normal_minimum(points, triangles), -0.95)

    def test_bioform_model_keeps_directional_skeleton_without_target_shape(self):
        source = (ROOT / "src/ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp").read_text(
            encoding="utf-8"
        )
        cmake = (ROOT / "src/ventricle_bioform_myo/CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("project_shape_velocity", source)
        self.assertIn("choose_adaptive_substep", source)
        self.assertIn("relative_rotation_residual", source)
        self.assertIn("PRL_MYO_BENDING_MODULUS=0.0", cmake)
        self.assertIn("PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1", cmake)

    def test_strip_conditions_and_material_links_remain_explicit(self):
        source = (ROOT / "src/ventricle_bioform_myo/ventricle_myo_strip_v01.cpp").read_text(
            encoding="utf-8"
        )
        for condition in ("PASSIVE", "SYNC", "CENTER", "CENTER_NO_LINK"):
            self.assertIn(f'"{condition}"', source)
        self.assertIn('config.junctions_enabled = config.condition != "CENTER_NO_LINK"', source)
        self.assertIn("target_geometry_used", source)
        self.assertIn("kStripDampingDensity = 1.0", source)

    def test_contact_uses_positive_gap_barrier_and_area_derivative(self):
        source = (
            ROOT / "external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp"
        ).read_text(encoding="utf-8")
        self.assertIn("positive-gap barrier requires disjoint surfaces", source)
        self.assertIn("grouped_voxel_faces", source)
        self.assertIn("area_gradient[vertex]*(fraction*potential)", source)


if __name__ == "__main__":
    unittest.main()
