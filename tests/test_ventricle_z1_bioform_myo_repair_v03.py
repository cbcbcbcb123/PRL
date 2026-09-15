from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ventricle_bioform_myo_repair import (  # noqa: E402
    choose_adaptive_step,
    equilibrate_normal_forces,
    remove_rigid_velocity,
)


class BioformMyocardiumRepairTests(unittest.TestCase):
    def test_production_target_freezes_rigid_gauge_and_excludes_failed_bending_term(self) -> None:
        cmake = (PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "CMakeLists.txt").read_text(encoding="utf-8")
        source = (PROJECT_ROOT / "src" / "ventricle_bioform_myo" / "ventricle_bioform_myo_v03.cpp").read_text(encoding="utf-8")
        production = cmake.split("add_executable(prl_ventricle_bioform_myo_v03 ", 1)[1].split(
            "add_executable(prl_ventricle_bioform_myo_v03_nobend ", 1
        )[0]
        self.assertIn("PRL_MYO_BENDING_MODULUS=0.0", production)
        self.assertIn("PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1", production)
        self.assertIn("project_shape_velocity", source)
        self.assertIn("choose_adaptive_substep", source)
        self.assertIn("relative_rotation_residual", source)

    def test_normal_equilibration_keeps_forces_normal_and_removes_rigid_resultants(self) -> None:
        points = np.array(
            [
                [1.2, 0.1, 0.2], [-0.8, 0.4, 0.1], [0.2, 1.4, -0.2],
                [0.1, -0.9, 0.5], [0.3, 0.2, 1.1], [-0.4, -0.3, -1.0],
                [0.9, -0.6, -0.4], [-0.7, 0.8, 0.6],
            ],
            dtype=float,
        )
        normals = points / np.linalg.norm(points, axis=1)[:, None]
        areas = np.array([1.0, 0.8, 1.2, 0.9, 1.1, 0.7, 1.3, 0.85])
        amplitudes = np.array([0.8, -0.2, 0.5, 0.1, -0.7, 0.4, 0.9, -0.3])
        raw = normals * amplitudes[:, None] * areas[:, None]

        corrected, audit = equilibrate_normal_forces(points, normals, areas, raw)

        tangent = corrected - normals * np.sum(corrected * normals, axis=1)[:, None]
        self.assertLess(float(np.linalg.norm(tangent)), 1.0e-12)
        self.assertLess(audit["net_force_norm"], 1.0e-11)
        self.assertLess(audit["net_moment_norm"], 1.0e-11)

    def test_rigid_velocity_projection_removes_translation_and_rotation_only(self) -> None:
        points = np.array(
            [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, 0.7], [0.0, 0.0, -0.7]],
            dtype=float,
        )
        areas = np.array([1.0, 1.2, 0.8, 1.1, 0.9, 1.3])
        translation = np.array([0.3, -0.2, 0.1])
        omega = np.array([0.07, -0.04, 0.09])
        center = np.sum(points * areas[:, None], axis=0) / areas.sum()
        rigid = translation + np.cross(np.broadcast_to(omega, points.shape), points - center)

        shape_velocity, audit = remove_rigid_velocity(points, areas, rigid)

        self.assertLess(float(np.linalg.norm(shape_velocity)), 1.0e-11)
        self.assertLess(audit["weighted_translation_residual"], 1.0e-11)
        self.assertLess(audit["weighted_rotation_residual"], 1.0e-11)

    def test_adaptive_step_caps_the_largest_nodal_motion(self) -> None:
        accepted = choose_adaptive_step(
            requested_step=0.02,
            remaining_step=0.02,
            minimum_edge_length=0.2,
            maximum_speed=4.0,
            displacement_fraction=0.10,
        )
        self.assertAlmostEqual(accepted, 0.005, places=14)
        self.assertLessEqual(accepted * 4.0, 0.10 * 0.2 + 1.0e-15)


if __name__ == "__main__":
    unittest.main()
