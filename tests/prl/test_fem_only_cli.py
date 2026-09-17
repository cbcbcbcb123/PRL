"""FEM-only public CLI policy; all execution and rendering are mocked."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from prl.cli import main


ROOT = Path(__file__).resolve().parents[2]


def invoke(arguments):
    stream = StringIO()
    with redirect_stdout(stream):
        code = main([*arguments, "--workspace", str(ROOT)])
    return code, json.loads(stream.getvalue())


class FemOnlyCliTests(unittest.TestCase):
    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_all_historical_dcm_run_entries_stop_before_workspace_or_execution(self, launch, workspace):
        names = ("myocardial-sheet", "myocardial-row", "myocardial-crowded-box",
                 "myocardial-crowded-target-pair", "myocardial-crowded-volume-x2",
                 "myocardial-crowded-quasistatic-growth", "regular-2x2-load-hold",
                 "contact-performance-equilibrium")
        for name in names:
            with self.subTest(name=name):
                code, report = invoke(["run", name])
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(report["execution"], "not_run")
                self.assertEqual(report["solver_calls"], 0)
                self.assertIn("FEM-only", report["reason"])
        workspace.assert_not_called()
        launch.assert_not_called()

    @patch("prl.cli.find_workspace")
    def test_dcm_passive_diagnostic_phases_are_blocked_before_dispatch(self, workspace):
        for phase in ("red", "green", "regressions"):
            with self.subTest(phase=phase):
                code, report = invoke(["diagnose", "passive-mechanics", "--phase", phase])
                self.assertEqual(code, 1)
                self.assertEqual(report["solver_calls"], 0)
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_measured_run_uses_controller_and_never_worker_or_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-measured-contour"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        command = launch.call_args.args[0]
        self.assertIn("prl.runs.fem_measured_contour", command)
        self.assertNotIn("--worker", command)
        self.assertEqual(launch.call_args.kwargs["timeout"], 660)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["OMP_NUM_THREADS"], "1")

    @patch("prl.cli.subprocess.run")
    def test_nonzero_controller_exit_remains_failed(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "gate failed")
        code, report = invoke(["run", "fem-measured-contour"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        launch.assert_called_once()

    @patch("prl.cli.subprocess.run")
    def test_controller_timeout_is_failure_without_retry(self, launch):
        launch.side_effect = subprocess.TimeoutExpired("controller", 660)
        code, report = invoke(["run", "fem-measured-contour"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        launch.assert_called_once()

    def test_measured_verify_is_read_only_and_render_uses_retained_path(self):
        result = Path("results/fem-retained-test-placeholder")
        runner = ModuleType("prl.runs.fem_measured_contour")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_measured_contour")
        verifier.verify_fem_measured_contour = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_measured_contour")
        renderer.render_fem_measured_contour = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-measured-contour"])[0], 0)
            self.assertEqual(invoke(["render", "fem-measured-contour", "--result", "results/custom-fem"])[0], 0)
        verifier.verify_fem_measured_contour.assert_called_once_with(ROOT / result, save=False)
        renderer.render_fem_measured_contour.assert_called_once_with(ROOT / "results/custom-fem")

    @patch("prl.cli.subprocess.run")
    def test_fixed_mesh_run_uses_bounded_single_thread_controller(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-fixed-mesh"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], [
            sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_fixed_mesh",
            "--workspace", str(ROOT),
        ])
        self.assertEqual(launch.call_args.kwargs["timeout"], 960)
        self.assertEqual(launch.call_args.kwargs["cwd"], ROOT)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(environment[name], "1")

    @patch("prl.cli.subprocess.run")
    def test_fixed_mesh_failure_and_timeout_never_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "qualification failed")
        code, report = invoke(["run", "fem-fixed-mesh"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["stderr"], "qualification failed")
        launch.assert_called_once()
        launch.reset_mock()
        launch.side_effect = subprocess.TimeoutExpired("fixed-mesh-controller", 960)
        code, report = invoke(["run", "fem-fixed-mesh"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        self.assertIn("960 s", report["reason"])
        self.assertIn("no retry", report["reason"])
        launch.assert_called_once()

    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_fixed_mesh_public_parser_cannot_bypass_controller_or_change_run_target(self, launch, workspace):
        for extra in (["--worker"], ["--result", "results/unregistered"]):
            with self.subTest(extra=extra), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                invoke(["run", "fem-fixed-mesh", *extra])
            self.assertEqual(raised.exception.code, 2)
        launch.assert_not_called()
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_fixed_mesh_verify_and_render_dispatch_only_to_saved_results(self, launch):
        result = Path("results/ventricle_fem/f3a_fixed_mesh_v01_20260917")
        runner = ModuleType("prl.runs.fem_fixed_mesh")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_fixed_mesh")
        verifier.verify_fem_fixed_mesh = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_fixed_mesh")
        renderer.render_fem_fixed_mesh = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-fixed-mesh"])[0], 0)
            verifier.verify_fem_fixed_mesh.assert_called_once_with(ROOT / result, save=False)
            verifier.verify_fem_fixed_mesh.reset_mock()
            custom = ROOT / "results/custom-fixed-fem"
            self.assertEqual(invoke(["verify", "fem-fixed-mesh", "--result", str(custom)])[0], 0)
            verifier.verify_fem_fixed_mesh.assert_called_once_with(custom, save=False)
            self.assertEqual(invoke(["render", "fem-fixed-mesh"])[0], 0)
            renderer.render_fem_fixed_mesh.assert_called_once_with(ROOT / result)
            renderer.render_fem_fixed_mesh.reset_mock()
            self.assertEqual(invoke(["render", "fem-fixed-mesh", "--result", "results/custom-fixed-fem"])[0], 0)
            renderer.render_fem_fixed_mesh.assert_called_once_with(custom)
            verifier.verify_fem_fixed_mesh.return_value = {"status": "failed"}
            renderer.render_fem_fixed_mesh.return_value = {"status": "failed"}
            self.assertEqual(invoke(["verify", "fem-fixed-mesh"])[0], 1)
            self.assertEqual(invoke(["render", "fem-fixed-mesh"])[0], 1)
        launch.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_finite_strain_uses_bounded_single_thread_controller(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-finite-strain"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], [
            sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_finite_strain",
            "--workspace", str(ROOT),
        ])
        self.assertEqual(launch.call_args.kwargs["timeout"], 1260)
        self.assertEqual(launch.call_args.kwargs["cwd"], ROOT)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(environment[name], "1")

    @patch("prl.cli.subprocess.run")
    def test_finite_strain_failure_and_timeout_never_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "qualification failed")
        code, report = invoke(["run", "fem-finite-strain"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        launch.assert_called_once()
        launch.reset_mock()
        launch.side_effect = subprocess.TimeoutExpired("finite-strain-controller", 1260)
        code, report = invoke(["run", "fem-finite-strain"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        self.assertIn("1260 s", report["reason"])
        self.assertIn("no retry", report["reason"])
        launch.assert_called_once()

    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_finite_strain_parser_has_no_worker_or_target_bypass(self, launch, workspace):
        for extra in (["--worker"], ["--result", "results/unregistered"]):
            with self.subTest(extra=extra), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                invoke(["run", "fem-finite-strain", *extra])
            self.assertEqual(raised.exception.code, 2)
        launch.assert_not_called()
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_finite_strain_verify_read_only_and_render_only_saved_states(self, launch):
        result = Path("results/ventricle_fem/f3b_finite_strain_v01_20260917")
        runner = ModuleType("prl.runs.fem_finite_strain")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_finite_strain")
        verifier.verify_fem_finite_strain = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_finite_strain")
        renderer.render_fem_finite_strain = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-finite-strain"])[0], 0)
            verifier.verify_fem_finite_strain.assert_called_once_with(ROOT / result, save=False)
            verifier.verify_fem_finite_strain.reset_mock()
            custom = ROOT / "results/custom-finite-fem"
            self.assertEqual(invoke(["verify", "fem-finite-strain", "--result", str(custom)])[0], 0)
            verifier.verify_fem_finite_strain.assert_called_once_with(custom, save=False)
            self.assertEqual(invoke(["render", "fem-finite-strain"])[0], 0)
            renderer.render_fem_finite_strain.assert_called_once_with(ROOT / result)
            renderer.render_fem_finite_strain.reset_mock()
            self.assertEqual(invoke(["render", "fem-finite-strain", "--result", "results/custom-finite-fem"])[0], 0)
            renderer.render_fem_finite_strain.assert_called_once_with(custom)
            verifier.verify_fem_finite_strain.return_value = {"status": "failed"}
            renderer.render_fem_finite_strain.return_value = {"status": "failed"}
            self.assertEqual(invoke(["verify", "fem-finite-strain"])[0], 1)
            self.assertEqual(invoke(["render", "fem-finite-strain"])[0], 1)
        launch.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_rotation_uses_360_second_controller_and_single_threads(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-rotation"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], [
            sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_rotation",
            "--workspace", str(ROOT),
        ])
        self.assertEqual(launch.call_args.kwargs["timeout"], 360)
        self.assertEqual(launch.call_args.kwargs["cwd"], ROOT)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(environment[name], "1")

    @patch("prl.cli.subprocess.run")
    def test_rotation_failure_and_timeout_never_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "rotation gate failed")
        code, report = invoke(["run", "fem-rotation"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        launch.assert_called_once()
        launch.reset_mock()
        launch.side_effect = subprocess.TimeoutExpired("rotation-controller", 360)
        code, report = invoke(["run", "fem-rotation"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        self.assertIn("360 s", report["reason"])
        self.assertIn("no retry", report["reason"])
        launch.assert_called_once()

    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_rotation_parser_blocks_worker_and_unregistered_run_target(self, launch, workspace):
        for extra in (["--worker"], ["--result", "results/unregistered"]):
            with self.subTest(extra=extra), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                invoke(["run", "fem-rotation", *extra])
            self.assertEqual(raised.exception.code, 2)
        launch.assert_not_called()
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_rotation_verify_read_only_and_render_only_retained_states(self, launch):
        result = Path("results/ventricle_fem/f3c_rotation_repair_v01_20260917")
        runner = ModuleType("prl.runs.fem_rotation")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_rotation")
        verifier.verify_fem_rotation = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_rotation")
        renderer.render_fem_rotation = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-rotation"])[0], 0)
            verifier.verify_fem_rotation.assert_called_once_with(ROOT / result, save=False)
            verifier.verify_fem_rotation.reset_mock()
            custom = ROOT / "results/custom-rotation-fem"
            self.assertEqual(invoke(["verify", "fem-rotation", "--result", str(custom)])[0], 0)
            verifier.verify_fem_rotation.assert_called_once_with(custom, save=False)
            self.assertEqual(invoke(["render", "fem-rotation"])[0], 0)
            renderer.render_fem_rotation.assert_called_once_with(ROOT / result)
            renderer.render_fem_rotation.reset_mock()
            self.assertEqual(invoke(["render", "fem-rotation", "--result", "results/custom-rotation-fem"])[0], 0)
            renderer.render_fem_rotation.assert_called_once_with(custom)
            verifier.verify_fem_rotation.return_value = {"status": "failed"}
            renderer.render_fem_rotation.return_value = {"status": "failed"}
            self.assertEqual(invoke(["verify", "fem-rotation"])[0], 1)
            self.assertEqual(invoke(["render", "fem-rotation"])[0], 1)
        launch.assert_not_called()


    @patch("prl.cli.subprocess.run")
    def test_curved_pressure_uses_660_second_controller_and_single_threads(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-curved-pressure"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], [
            sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_curved_pressure",
            "--workspace", str(ROOT),
        ])
        self.assertEqual(launch.call_args.kwargs["timeout"], 660)
        self.assertEqual(launch.call_args.kwargs["cwd"], ROOT)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(environment[name], "1")

    @patch("prl.cli.subprocess.run")
    def test_curved_pressure_failure_and_timeout_never_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "pressure gate failed")
        code, report = invoke(["run", "fem-curved-pressure"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        launch.assert_called_once()
        launch.reset_mock()
        launch.side_effect = subprocess.TimeoutExpired("curved-pressure-controller", 660)
        code, report = invoke(["run", "fem-curved-pressure"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        self.assertIn("660 s", report["reason"])
        self.assertIn("no retry", report["reason"])
        launch.assert_called_once()

    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_curved_pressure_parser_has_no_worker_or_run_target_bypass(self, launch, workspace):
        for extra in (["--worker"], ["--result", "results/unregistered"]):
            with self.subTest(extra=extra), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                invoke(["run", "fem-curved-pressure", *extra])
            self.assertEqual(raised.exception.code, 2)
        launch.assert_not_called()
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_curved_pressure_verify_read_only_and_render_only_retained_states(self, launch):
        result = Path("results/ventricle_fem/f4_curved_pressure_v01_20260917")
        runner = ModuleType("prl.runs.fem_curved_pressure")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_curved_pressure")
        verifier.verify_fem_curved_pressure = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_curved_pressure")
        renderer.render_fem_curved_pressure = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-curved-pressure"])[0], 0)
            verifier.verify_fem_curved_pressure.assert_called_once_with(ROOT / result, save=False)
            verifier.verify_fem_curved_pressure.reset_mock()
            custom = ROOT / "results/custom-curved-pressure-fem"
            self.assertEqual(invoke(["verify", "fem-curved-pressure", "--result", str(custom)])[0], 0)
            verifier.verify_fem_curved_pressure.assert_called_once_with(custom, save=False)
            self.assertEqual(invoke(["render", "fem-curved-pressure"])[0], 0)
            renderer.render_fem_curved_pressure.assert_called_once_with(ROOT / result)
            renderer.render_fem_curved_pressure.reset_mock()
            self.assertEqual(invoke(["render", "fem-curved-pressure", "--result", "results/custom-curved-pressure-fem"])[0], 0)
            renderer.render_fem_curved_pressure.assert_called_once_with(custom)
            verifier.verify_fem_curved_pressure.return_value = {"status": "failed"}
            renderer.render_fem_curved_pressure.return_value = {"status": "failed"}
            self.assertEqual(invoke(["verify", "fem-curved-pressure"])[0], 1)
            self.assertEqual(invoke(["render", "fem-curved-pressure"])[0], 1)
        launch.assert_not_called()


    @patch("prl.cli.subprocess.run")
    def test_contour_pressure_uses_1260_second_controller_and_single_threads(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 0, '{"status":"passed"}', "")
        code, report = invoke(["run", "fem-contour-pressure"])
        self.assertEqual(code, 0)
        self.assertEqual(report["execution"], "bounded_fem_controller_completed")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], [
            sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_contour_pressure",
            "--workspace", str(ROOT),
        ])
        self.assertEqual(launch.call_args.kwargs["timeout"], 1260)
        self.assertEqual(launch.call_args.kwargs["cwd"], ROOT)
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(environment[name], "1")

    @patch("prl.cli.subprocess.run")
    def test_contour_pressure_failure_and_timeout_never_retry(self, launch):
        launch.return_value = subprocess.CompletedProcess([], 1, "", "contour pressure gate failed")
        code, report = invoke(["run", "fem-contour-pressure"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        launch.assert_called_once()
        launch.reset_mock()
        launch.side_effect = subprocess.TimeoutExpired("contour-pressure-controller", 1260)
        code, report = invoke(["run", "fem-contour-pressure"])
        self.assertEqual(code, 1)
        self.assertEqual(report["execution"], "controller_timeout")
        self.assertIn("1260 s", report["reason"])
        self.assertIn("no retry", report["reason"])
        launch.assert_called_once()

    @patch("prl.cli.find_workspace")
    @patch("prl.cli.subprocess.run")
    def test_contour_pressure_parser_blocks_worker_and_run_target_bypass(self, launch, workspace):
        for extra in (["--worker"], ["--result", "results/unregistered"]):
            with self.subTest(extra=extra), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                invoke(["run", "fem-contour-pressure", *extra])
            self.assertEqual(raised.exception.code, 2)
        launch.assert_not_called()
        workspace.assert_not_called()

    @patch("prl.cli.subprocess.run")
    def test_contour_pressure_verify_read_only_and_render_only_saved_states(self, launch):
        result = Path("results/ventricle_fem/f5_contour_pressure_v01_20260917")
        runner = ModuleType("prl.runs.fem_contour_pressure")
        runner.RESULT = result
        verifier = ModuleType("prl.verification.fem_contour_pressure")
        verifier.verify_fem_contour_pressure = Mock(return_value={"status": "passed"})
        renderer = ModuleType("prl.rendering.fem_contour_pressure")
        renderer.render_fem_contour_pressure = Mock(return_value={"status": "passed"})
        with patch.dict(sys.modules, {runner.__name__: runner, verifier.__name__: verifier,
                                      renderer.__name__: renderer}):
            self.assertEqual(invoke(["verify", "fem-contour-pressure"])[0], 0)
            verifier.verify_fem_contour_pressure.assert_called_once_with(ROOT / result, save=False)
            verifier.verify_fem_contour_pressure.reset_mock()
            custom = ROOT / "results/custom-contour-pressure-fem"
            self.assertEqual(invoke(["verify", "fem-contour-pressure", "--result", str(custom)])[0], 0)
            verifier.verify_fem_contour_pressure.assert_called_once_with(custom, save=False)
            self.assertEqual(invoke(["render", "fem-contour-pressure"])[0], 0)
            renderer.render_fem_contour_pressure.assert_called_once_with(ROOT / result)
            renderer.render_fem_contour_pressure.reset_mock()
            self.assertEqual(invoke(["render", "fem-contour-pressure", "--result", "results/custom-contour-pressure-fem"])[0], 0)
            renderer.render_fem_contour_pressure.assert_called_once_with(custom)
            verifier.verify_fem_contour_pressure.return_value = {"status": "failed"}
            renderer.render_fem_contour_pressure.return_value = {"status": "failed"}
            self.assertEqual(invoke(["verify", "fem-contour-pressure"])[0], 1)
            self.assertEqual(invoke(["render", "fem-contour-pressure"])[0], 1)
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
