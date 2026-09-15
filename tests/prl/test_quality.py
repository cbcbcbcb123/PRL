from pathlib import Path
import tomllib
import unittest

from prl.quality import (
    QuickSuiteContractError,
    _captured_text,
    _checked_relative_file,
    _pytest_command,
    load_quick_suite,
    validate_quick_suite,
)


ROOT = Path(__file__).resolve().parents[2]


class CurrentQuickSuiteContractTests(unittest.TestCase):
    def test_manifest_is_explicit_and_stays_inside_current_test_boundary(self):
        manifest, entries = load_quick_suite(ROOT)
        self.assertEqual(manifest, ROOT / "tests/prl/quick_suite_v01.txt")
        self.assertEqual(
            entries,
            [
                "tests/prl/test_cli.py",
                "tests/prl/test_cpp_support_boundary.py",
                "tests/prl/test_long_doublet_verification.py",
                "tests/prl/test_quality.py",
                "tests/prl/test_storage.py",
            ],
        )

    def test_strict_import_path_and_protected_identity_contract_passes(self):
        report = validate_quick_suite(ROOT)
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertTrue(all(report["checks"].values()))

    def test_parent_escape_is_rejected_without_touching_filesystem(self):
        with self.assertRaises(QuickSuiteContractError):
            _checked_relative_file(ROOT, "tests/prl/../test_escape.py")

    def test_pytest_command_disables_cache_and_uses_only_manifest_paths(self):
        _, entries = load_quick_suite(ROOT)
        command = _pytest_command(entries)
        self.assertIn("no:cacheprovider", command)
        self.assertEqual(command[-len(entries) :], entries)

    def test_timeout_output_remains_json_serializable_text(self):
        self.assertEqual(_captured_text(b"passed\xff"), "passed\ufffd")
        self.assertEqual(_captured_text(None), "")

    def test_default_project_configuration_points_only_to_current_mainline(self):
        configuration = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            configuration["tool"]["setuptools"]["packages"]["find"]["include"],
            ["prl*"],
        )
        pytest_options = configuration["tool"]["pytest"]["ini_options"]
        self.assertEqual(pytest_options["testpaths"], ["tests/prl"])
        self.assertIn("no:cacheprovider", pytest_options["addopts"])
        self.assertEqual(configuration["project"]["scripts"]["prl"], "prl.cli:main")

    def test_root_readme_exposes_current_commands_not_retired_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("START_HERE.md", readme)
        self.assertIn("python -B -X utf8 -m prl test quick --workspace .", readme)
        self.assertNotIn("pytest -q tests/hybrid", readme)
        self.assertNotIn("run_hybrid_x0_probe.py", readme)


if __name__ == "__main__":
    unittest.main()
