import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "src/prl_ventricle_support"
FIRST_BASELINE_COMMIT = "d53ca553fd8bba9965d850106fd9305da76be668"
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

    def test_ten_prechange_sources_are_preserved_in_first_root_commit(self):
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(baseline["status"], "passed")
        self.assertEqual(len(baseline["files"]), 10)
        for item in baseline["files"]:
            completed = subprocess.run(
                ["git", "show", f"{FIRST_BASELINE_COMMIT}:{item['path']}"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            )
            payload = completed.stdout
            self.assertEqual(len(payload), item["bytes"], item["path"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                item["sha256"],
                item["path"],
            )

    def test_current_applications_use_headers_and_shared_model_libraries(self):
        applications = [
            ROOT / "src/ventricle_bioform_myo/ventricle_myo_strip_v01.cpp",
            *sorted((ROOT / "src/ventricle_simucell3d_m0").glob("myo_*probe_v0*.cpp")),
            ROOT / "src/ventricle_simucell3d_m0/myo_sheet_relaxation_v01.cpp",
            ROOT / "src/ventricle_simucell3d_m0/myo_contact_barrier_relaxation_v01.cpp",
        ]
        self.assertEqual(len(applications), 8)
        for path in applications:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn('#include "ventricle_simucell3d_m0.cpp"', source)
            self.assertNotIn('#include "ventricle_bioform_myo_v03.cpp"', source)
        m0_cmake = (ROOT / "src/ventricle_simucell3d_m0/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        bioform_cmake = (ROOT / "src/ventricle_bioform_myo/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("add_library(prl_m0_model", m0_cmake)
        self.assertIn("add_library(prl_bioform_model", bioform_cmake)
        self.assertTrue((ROOT / "CMakeLists.txt").is_file())


if __name__ == "__main__":
    unittest.main()
