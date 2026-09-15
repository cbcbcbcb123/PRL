from pathlib import Path
import unittest

from prl.verification import verify_long_doublet


ROOT = Path(__file__).resolve().parents[2]


class LongDoubletVerificationPublicInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verify_long_doublet(ROOT)

    def test_retained_evidence_and_source_identity_pass(self):
        self.assertEqual(self.report["status"], "passed")
        self.assertTrue(self.report["checks"]["source_identity"])
        self.assertTrue(self.report["checks"]["matrix_complete"])
        self.assertEqual(len(self.report["cases"]), 4)

    def test_scientific_failure_and_blocked_states_are_preserved(self):
        frozen = self.report["frozen_status"]
        self.assertEqual(frozen["long_doublet_numerical"], "passed")
        self.assertEqual(frozen["static_equilibrium"], "failed")
        self.assertEqual(frozen["parent_Z1"], "blocked")
        self.assertEqual(frozen["biological_validation"], "blocked")
        self.assertEqual(frozen["sixteen_cell_dynamics"], "not_run")

    def test_per_cell_deformation_is_recomputed_not_averaged(self):
        cases = {item["case"]: item for item in self.report["cases"]}
        end_cells = cases["END_DT0.01"]["metrics"]["per_cell"]
        side_cells = cases["SIDE_DT0.01"]["metrics"]["per_cell"]
        self.assertEqual([item["cell"] for item in end_cells], [0, 1])
        self.assertEqual([item["cell"] for item in side_cells], [0, 1])
        self.assertAlmostEqual(end_cells[0]["length_strain"], 0.06361266144087763)
        self.assertAlmostEqual(side_cells[1]["length_strain"], 0.12213476772706655)


if __name__ == "__main__":
    unittest.main()
