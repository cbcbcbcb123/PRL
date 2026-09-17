from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from prl.cli import main


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/prl/fixtures/long_doublet_compact_v01"


class CommandLinePublicInterfaceTests(unittest.TestCase):
    @patch("prl.verification.passive_mechanics.verify_passive_mechanics")
    def test_passive_mechanics_has_read_only_independent_entry(self, verify):
        verify.return_value = {"status": "passed", "scope": "static qualification"}
        output = StringIO()
        with redirect_stdout(output):
            code = main(["verify", "passive-mechanics", "--workspace", str(ROOT)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["scope"], "static qualification")
        self.assertEqual(verify.call_args.args[1], "green")

    def test_long_doublet_command_emits_machine_readable_report(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "verify",
                    "long-doublet",
                    "--workspace",
                    str(ROOT),
                    "--result",
                    str(FIXTURE),
                ]
            )
        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["schema_version"], "prl.long_doublet_verification.v1")
        self.assertEqual(report["status"], "passed")

    def test_new_package_has_no_historical_runner_or_codex_skill_imports(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "src/prl").rglob("*.py"))
        )
        self.assertNotIn("scripts.run_", source)
        self.assertNotIn(".codex/skills", source.replace("\\", "/"))

    @patch("prl.cli.run_quick_suite")
    def test_quick_test_command_preserves_machine_readable_cli(self, quick):
        quick.return_value = {
            "schema_version": "prl.current_quick_suite.v1",
            "status": "passed",
            "test_paths": ["tests/prl/test_cli.py"],
        }
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["test", "quick", "--workspace", str(ROOT)])
        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "passed")
        quick.assert_called_once_with(ROOT)

    @patch("prl.cli.run_contact_performance_equilibrium")
    def test_contact_run_is_blocked_by_latest_fem_only_decision(self, run):
        run.return_value = {"status": "passed", "phase": "q", "calls": 39}
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "run",
                    "contact-performance-equilibrium",
                    "--workspace",
                    str(ROOT),
                    "--phase",
                    "q",
                ]
            )
        self.assertEqual(exit_code, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["execution"], "not_run")
        self.assertEqual(report["solver_calls"], 0)
        self.assertIn("FEM-only", report["reason"])
        run.assert_not_called()

    @patch("prl.runs.fem_active_ellipse.run_fem_active_ellipse")
    def test_fem_pilot_has_one_bounded_public_run_entry(self, run):
        run.return_value = {
            "status": "passed",
            "result": "results/ventricle_fem/f0_active_elliptic_pilot_v01_20260916",
        }
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                ["run", "fem-active-ellipse", "--workspace", str(ROOT)]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "passed")
        run.assert_called_once_with(ROOT)

    @patch("prl.runs.fem_synthetic_orientation.run_fem_synthetic_orientation")
    def test_synthetic_orientation_has_one_bounded_public_run_entry(self, run):
        run.return_value = {
            "status": "passed",
            "result": "results/ventricle_fem/f1s_synthetic_orientation_v01_20260916",
        }
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                ["run", "fem-synthetic-orientation", "--workspace", str(ROOT)]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "passed")
        run.assert_called_once_with(ROOT)

    @patch("prl.cli.diagnose_terminal_residual")
    def test_terminal_residual_diagnosis_is_a_separate_non_solver_command(self, diagnose):
        diagnose.return_value = {"status": "passed", "solver_calls": 0}
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["diagnose", "terminal-residual", "--workspace", str(ROOT)])
        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["solver_calls"], 0)
        diagnose.assert_called_once_with(ROOT, None, None)

    @patch("prl.cli.verify_terminal_residual_diagnosis")
    def test_terminal_residual_verification_has_an_independent_entry(self, verify):
        verify.return_value = {"status": "passed", "scope": "independent"}
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                ["verify", "terminal-residual-diagnosis", "--workspace", str(ROOT)]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["scope"], "independent")
        verify.assert_called_once_with(ROOT, None)


if __name__ == "__main__":
    unittest.main()
