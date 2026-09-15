import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "src/prl_ventricle_support"
BASELINE = (
    ROOT
    / "project_control/evidence/repository_cleanup_v01"
    / "batch04_candidate02_source_baseline.json"
)


class CppSupportBoundaryTests(unittest.TestCase):
    def test_new_support_library_has_no_kernel_or_implementation_includes(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(SUPPORT.rglob("*.cpp"))
            + sorted(SUPPORT.rglob("*.hpp"))
        )
        self.assertNotIn('#include "cell.hpp"', source)
        self.assertNotIn("external/simucell3d", source.replace("\\", "/"))
        self.assertNotIn('#include "ventricle_simucell3d_m0.cpp"', source)
        self.assertNotIn('#include "ventricle_bioform_myo_v03.cpp"', source)

    def test_ten_frozen_implementation_sources_match_prechange_baseline(self):
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(baseline["status"], "passed")
        self.assertEqual(len(baseline["files"]), 10)
        for item in baseline["files"]:
            path = ROOT / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"], item["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )

    def test_safe_slice_builds_seam_without_switching_old_applications(self):
        cmake = (ROOT / "src/ventricle_simucell3d_m0/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("../prl_ventricle_support", cmake)
        old_application_links = [
            line
            for line in cmake.splitlines()
            if "target_link_libraries" in line
            and "prl_ventricle_support" in line
        ]
        self.assertEqual(old_application_links, [])


if __name__ == "__main__":
    unittest.main()
