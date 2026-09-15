from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from prl.cli import main


ROOT = Path(__file__).resolve().parents[2]


class CommandLinePublicInterfaceTests(unittest.TestCase):
    def test_long_doublet_command_emits_machine_readable_report(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(
                ["verify", "long-doublet", "--workspace", str(ROOT)]
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


if __name__ == "__main__":
    unittest.main()
