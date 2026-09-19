"""Behavioral guards: no Desktop starts, no engine mutation, no remote endpoint."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import runtime_doctor as doctor


def fixture(healthy=False, acl_error=None):
    return {"schema_version": doctor.SCHEMA, "endpoint": doctor.LOCAL_ENDPOINT,
            "engine": {"returncode": 0 if healthy else 1,
                       "server": {"Version": "test", "Os": "linux"} if healthy else None},
            "host": {"roots": [
                {"status": "passed", "path": "runtime-a", "entries": [
                    {"path": "runtime-a/socket", "bytes": 0, "attributes": "Archive, ReparsePoint", "acl_error": acl_error}]},
                {"status": "absent", "path": "runtime-b", "entries": []}]},
            "image": {"status": "not_run"}, "probe_errors": []}


class Decisions(unittest.TestCase):
    def test_1920_blocks_before_start(self):
        result = doctor.classify(fixture(acl_error="Method failed with unexpected error code 1920."))
        self.assertEqual(result["startup_decision"], "stop_known_signature_before_start")
        self.assertEqual(result["error_1920_paths"], ["runtime-a/socket"])
        self.assertFalse(result["repair_authorized_by_this_tool"])

    def test_recurrence_stops_rotation(self):
        result = doctor.classify(fixture(acl_error="error 1920"), prior_repair_recurred=True)
        self.assertEqual(result["startup_decision"], "stop_recurrence_no_directory_rotation")
        self.assertEqual(result["deep_recurrence_cause"], "unknown")

    def test_missing_pipe_does_not_prove_corruption(self):
        result = doctor.classify(fixture())
        self.assertEqual(result["error_1920_paths"], [])
        self.assertEqual(result["preflight_status"], "blocked")
        self.assertEqual(result["startup_decision"], "diagnose_and_check_current_startup_authority")

    def test_zero_byte_reparse_object_and_old_log_do_not_fail_healthy_engine(self):
        data = fixture(healthy=True)
        data["backend_log"] = {"socket_lines": ["OLD initializing Ingest server error 1920"]}
        result = doctor.classify(data)
        self.assertEqual(result["preflight_status"], "passed")
        self.assertEqual(result["science_status"], "not_run")

    def test_healthy_api_anomaly_is_not_permission_to_restart(self):
        result = doctor.classify(fixture(healthy=True, acl_error="1920"))
        self.assertEqual(result["runtime_api_status"], "passed")
        self.assertEqual(result["preflight_status"], "blocked")
        self.assertEqual(result["startup_decision"], "not_needed_review_anomalies")

    def test_process_is_not_readiness(self):
        data = fixture()
        data["host"]["processes"] = [{"name": "com.docker.backend", "pid": 42}]
        self.assertEqual(doctor.classify(data)["runtime_api_status"], "blocked")

    def test_incomplete_inspection_blocks(self):
        data = fixture(healthy=True)
        data["host"]["roots"] = []
        self.assertEqual(doctor.classify(data)["preflight_status"], "blocked")

    def test_acl_probe_failure_is_not_diagnosed_as_1920_or_allowed_to_start(self):
        result = doctor.classify(fixture(acl_error="Get-Acl module could not be loaded"))
        self.assertEqual(result["error_1920_paths"], [])
        self.assertEqual(result["startup_decision"], "stop_incomplete_preflight")

    def test_wrong_image_blocks(self):
        data = fixture(healthy=True)
        data["image"]["status"] = "failed"
        self.assertEqual(doctor.classify(data)["preflight_status"], "blocked")

    def test_unknown_image_status_blocks(self):
        data = fixture(healthy=True)
        data["image"]["status"] = "unknown"
        self.assertEqual(doctor.classify(data)["preflight_status"], "blocked")

    def test_remote_snapshot_cannot_pass(self):
        data = fixture(healthy=True)
        data["endpoint"] = "ssh://other-host"
        self.assertEqual(doctor.classify(data)["preflight_status"], "blocked")

    def test_windows_engine_cannot_pass(self):
        data = fixture(healthy=True)
        data["engine"]["server"]["Os"] = "windows"
        self.assertEqual(doctor.classify(data)["runtime_api_status"], "blocked")


class Collection(unittest.TestCase):
    def test_cli_replays_its_own_report_without_live_access(self):
        saved = {"snapshot": fixture(acl_error="error 1920"), "assessment": {"stale": True}}
        output = io.StringIO()
        with patch.object(Path, "read_text", return_value=json.dumps(saved)), \
                patch.object(doctor, "collect_live") as live, patch("sys.stdout", output):
            exit_code = doctor.main(["--snapshot", "supplied.json", "--prior-repair-recurred"])
        live.assert_not_called()
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["assessment"]["startup_decision"],
                         "stop_recurrence_no_directory_rotation")

    def test_timeout_is_reported_without_retry(self):
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 15)) as mocked:
            result = doctor.invoke(["probe"], {})
        self.assertEqual(mocked.call_count, 1)
        self.assertIsNone(result["returncode"])
        self.assertIsNotNone(result["error"])

    @unittest.skipUnless(os.name == "nt", "live collector is Windows-only")
    def test_only_readonly_commands_and_local_pipe_despite_remote_environment(self):
        environment = dict(os.environ)
        environment.update(DOCKER_HOST="ssh://remote", DOCKER_CONTEXT="remote", DOCKER_TLS_VERIFY="1",
                           PSModulePath="PowerShell7-only-modules")
        original = deepcopy(environment)
        calls = []

        def fake_runner(command, child_environment):
            calls.append(command)
            self.assertNotIn("DOCKER_HOST", child_environment)
            self.assertNotIn("DOCKER_CONTEXT", child_environment)
            if command[0] == "powershell.exe":
                self.assertNotIn("PSModulePath", child_environment)
                stdout = json.dumps(fixture(healthy=True)["host"])
            elif "version" in command:
                stdout = json.dumps({"Version": "test", "Os": "linux"})
            elif "inspect" in command:
                stdout = "sha256:actual"
            else:
                stdout = "Stopped"
            return {"returncode": 0, "stdout": stdout, "stderr": "", "error": None}

        # No real processes, logs, sockets, files, or Docker API are accessed in this test.
        with patch.object(doctor, "check_local_path", side_effect=lambda path: Path(path)), \
                patch.object(Path, "open", side_effect=FileNotFoundError):
            snapshot = doctor.collect_live("pinned:tag", "sha256:expected", fake_runner, environment)
        self.assertEqual(environment, original)
        self.assertEqual(snapshot["actions_performed"], doctor.ZERO_ACTIONS)
        self.assertEqual(snapshot["image"]["status"], "failed")
        docker_calls = [command for command in calls if command[0] == "docker.exe"]
        self.assertEqual(docker_calls, [
            ["docker.exe", "--host", doctor.LOCAL_ENDPOINT, "version", "--format", "{{json .Server}}"],
            ["docker.exe", "--host", doctor.LOCAL_ENDPOINT, "image", "inspect", "pinned:tag", "--format", "{{.Id}}"]])
        self.assertEqual(len(calls), 4)

    def test_image_inputs_are_paired(self):
        if os.name != "nt":
            self.skipTest("Windows only")
        calls = []
        with self.assertRaises(ValueError):
            doctor.collect_live("tag", None, lambda *args: calls.append(args))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
