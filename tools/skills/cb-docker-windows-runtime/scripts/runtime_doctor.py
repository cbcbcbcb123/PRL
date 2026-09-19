"""Read-only, local-only Docker Desktop preflight; JSON to stdout, no retries."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

LOCAL_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
SCHEMA = "cb.docker.windows.preflight.v1"
ZERO_ACTIONS = {key: 0 for key in (
    "desktop_starts", "repairs", "moves", "deletions", "acl_changes", "pulls",
    "installs", "containers", "jit_tests", "solves", "gpu_tasks")}

# Literal, read-only PowerShell. No recursion, startup, repair, or file output.
HOST_PROBE = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$runtimeRoots = @()
foreach ($runtimeSuffix in @('Docker\run', 'docker-secrets-engine')) {
    $runtimePath = Join-Path $env:LOCALAPPDATA $runtimeSuffix
    $rootReport = [ordered]@{path=$runtimePath; status='unknown'; entries=@(); error=$null}
    try {
        $rootItem = Get-Item -LiteralPath $runtimePath -Force -ErrorAction Stop
        if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Linked runtime root; not traversed'
        }
        $runtimeItems = @(Get-ChildItem -LiteralPath $runtimePath -Force -ErrorAction Stop | Select-Object -First 129)
        if ($runtimeItems.Count -gt 128) { throw 'Runtime entry bound exceeded; no partial pass' }
        foreach ($runtimeItem in $runtimeItems) {
            $aclIssue = $null
            try { $null = Get-Acl -LiteralPath $runtimeItem.FullName -ErrorAction Stop }
            catch { $aclIssue = $_.Exception.Message }
            $rootReport.entries += [ordered]@{
                path=$runtimeItem.FullName; attributes=[string]$runtimeItem.Attributes
                bytes=$(if ($runtimeItem.PSIsContainer) {$null} else {$runtimeItem.Length})
                modified_utc=$runtimeItem.LastWriteTimeUtc.ToString('o'); acl_error=$aclIssue
            }
        }
        $rootReport.status = 'passed'
    } catch [System.Management.Automation.ItemNotFoundException] {
        $rootReport.status = 'absent'
    } catch { $rootReport.status = 'unknown'; $rootReport.error = $_.Exception.Message }
    $runtimeRoots += $rootReport
}
$dockerProcesses = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @('Docker Desktop','com.docker.backend','com.docker.build','vmmemWSL')
} | Select-Object @{n='name';e={$_.ProcessName}},@{n='pid';e={$_.Id}})
$dockerService = Get-Service -Name 'com.docker.service' -ErrorAction SilentlyContinue
[ordered]@{
    roots=$runtimeRoots; processes=$dockerProcesses
    service_status=$(if ($null -eq $dockerService) {'unknown'} else {[string]$dockerService.Status})
} | ConvertTo-Json -Depth 8 -Compress
"""


def invoke(command, environment):
    """Exactly one bounded child; inherited environment is never mutated."""
    try:
        completed = subprocess.run(command, env=environment, capture_output=True,
                                   timeout=15, check=False)
        def decode(value):
            encoding = "utf-16-le" if b"\x00" in value else "utf-8-sig"
            return value.decode(encoding, errors="replace").strip()
        return {"returncode": completed.returncode, "stdout": decode(completed.stdout),
                "stderr": decode(completed.stderr), "error": None}
    except (OSError, subprocess.TimeoutExpired) as problem:
        return {"returncode": None, "stdout": "", "stderr": "", "error": str(problem)}


def check_local_path(path):
    """Refuse UNC/relative paths and linked existing ancestors, without resolving links."""
    path = Path(path)
    if not path.is_absolute() or str(path).startswith(("\\\\", "//")):
        raise ValueError("A local absolute path is required")
    for ancestor in reversed((path, *path.parents)):
        try:
            metadata = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 1024:
            raise ValueError("Linked ancestor not traversed: " + str(ancestor))
    return path


def collect_live(image=None, expected_image_id=None, runner=invoke, environment=None):
    if os.name != "nt":
        raise ValueError("Live collection is Windows-only; use --snapshot elsewhere")
    if bool(image) != bool(expected_image_id):
        raise ValueError("Image tag and expected image ID must be supplied together")
    child_environment = dict(os.environ if environment is None else environment)
    for key in tuple(child_environment):
        if key.upper() in {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY",
                           "DOCKER_CERT_PATH", "DOCKER_API_VERSION"}:
            child_environment.pop(key)
    snapshot = {"schema_version": SCHEMA, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                "endpoint": LOCAL_ENDPOINT, "actions_performed": dict(ZERO_ACTIONS),
                "host": {"roots": []}, "probe_errors": [], "image": {"status": "not_run"}}
    try:
        local_root = check_local_path(child_environment["LOCALAPPDATA"])
        for suffix in ("Docker/run", "docker-secrets-engine"):
            check_local_path(local_root / suffix)
        # PowerShell 7 can export its module search path to Windows PowerShell 5.1.
        # Let this child rebuild its native defaults; never change user/module configuration.
        powershell_environment = {key: value for key, value in child_environment.items()
                                  if key.upper() != "PSMODULEPATH"}
        probe = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", HOST_PROBE], powershell_environment)
        if probe["returncode"] != 0:
            raise ValueError(probe["error"] or probe["stderr"] or "Host probe failed")
        snapshot["host"] = json.loads(probe["stdout"])
    except (OSError, ValueError, KeyError) as problem:
        snapshot["probe_errors"].append("host: " + str(problem))
    # Explicit local named pipe avoids accidentally contacting a selected remote context.
    prefix = ["docker.exe", "--host", LOCAL_ENDPOINT]
    probe = runner(prefix + ["version", "--format", "{{json .Server}}"], child_environment)
    server = None
    if probe["returncode"] == 0:
        try:
            server = json.loads(probe["stdout"])
        except ValueError:
            snapshot["probe_errors"].append("Engine returned invalid JSON")
    snapshot["engine"] = {"server": server, "returncode": probe["returncode"],
                          "error": (probe["error"] or probe["stderr"])[:2000] or None}
    wsl_probe = runner(["wsl.exe", "--list", "--verbose"], child_environment)
    snapshot["wsl"] = {"returncode": wsl_probe["returncode"], "listing": wsl_probe["stdout"][:4000],
                       "error": wsl_probe["error"] or wsl_probe["stderr"] or None}
    # Read a bounded tail of the usual backend log, never runtime socket contents.
    try:
        log_path = check_local_path(Path(child_environment["LOCALAPPDATA"]) / "Docker/log/host/com.docker.backend.exe.log")
        with log_path.open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 131072))
            lines = stream.read(131072).decode("utf-8", errors="replace").splitlines()
        if size > 131072:
            lines = lines[1:]
        snapshot["backend_log"] = {"path": str(log_path), "bytes": size,
            "scope": "bounded tail; timestamps require correlation; not used for classification",
            "socket_lines": [line[:2000] for line in lines if re.search(
                r"Ingest|Secrets Engine|1920|cannot be accessed by the system|backend crashed", line, re.I)][-12:]}
    except (OSError, ValueError, KeyError) as problem:
        snapshot["backend_log"] = {"status": "unknown", "error": str(problem)}
    if image and isinstance(server, dict) and server.get("Os") == "linux" and probe["returncode"] == 0:
        image_probe = runner(prefix + ["image", "inspect", image, "--format", "{{.Id}}"], child_environment)
        actual_id = image_probe["stdout"] if image_probe["returncode"] == 0 else None
        snapshot["image"] = {"status": "passed" if actual_id == expected_image_id else "failed",
            "tag": image, "expected_id": expected_image_id, "actual_id": actual_id,
            "error": image_probe["error"] or image_probe["stderr"] or None}
    elif image:
        snapshot["image"] = {"status": "blocked", "tag": image, "expected_id": expected_image_id}
    return snapshot


def classify(snapshot, prior_repair_recurred=False):
    if snapshot.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported snapshot schema")
    engine = snapshot.get("engine", {})
    server = engine.get("server")
    api_ready = (engine.get("returncode") == 0 and isinstance(server, dict)
                 and bool(server.get("Version")) and server.get("Os") == "linux")
    roots = snapshot.get("host", {}).get("roots", [])
    accessible = len(roots) == 2 and all(root.get("status") in ("passed", "absent") for root in roots)
    issues = []
    for root in roots:
        if root.get("error"):
            issues.append({"path": root.get("path"), "error": root["error"]})
        issues.extend({"path": entry.get("path"), "error": entry["acl_error"]}
                      for entry in root.get("entries", []) if entry.get("acl_error"))
    error_1920 = [issue for issue in issues if re.search(r"\b1920\b", issue["error"])]
    reasons = []
    if snapshot.get("endpoint") != LOCAL_ENDPOINT:
        reasons.append("not_the_verified_local_linux_endpoint")
    if not api_ready:
        reasons.append("linux_engine_api_unavailable")
    if not accessible or snapshot.get("probe_errors"):
        reasons.append("incomplete_read_only_preflight")
    if issues:
        reasons.append("runtime_object_access_error")
    if error_1920:
        reasons.append("runtime_acl_error_1920")
    image_status = snapshot.get("image", {}).get("status", "not_run")
    if image_status not in ("not_run", "passed"):
        reasons.append("local_image_not_qualified")
    if api_ready:
        startup_decision = "not_needed_review_anomalies" if reasons else "not_needed"
    elif error_1920:
        startup_decision = "stop_recurrence_no_directory_rotation" if prior_repair_recurred else "stop_known_signature_before_start"
    elif not accessible or snapshot.get("probe_errors") or issues:
        startup_decision = "stop_incomplete_preflight"
    else:
        startup_decision = "diagnose_and_check_current_startup_authority"
    return {"runtime_api_status": "passed" if api_ready else "blocked",
            "preflight_status": "blocked" if reasons else "passed",
            "local_image_status": image_status, "science_status": "not_run",
            "startup_decision": startup_decision, "reason_codes": reasons,
            "error_1920_paths": [issue["path"] for issue in error_1920],
            "deep_recurrence_cause": "unknown", "repair_authorized_by_this_tool": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--snapshot", type=Path)
    parser.add_argument("--image")
    parser.add_argument("--expected-image-id")
    parser.add_argument("--prior-repair-recurred", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.snapshot and (arguments.image or arguments.expected_image_id):
        parser.error("Image options apply only to --live")
    try:
        snapshot = collect_live(arguments.image, arguments.expected_image_id) if arguments.live else json.loads(
            arguments.snapshot.read_text(encoding="utf-8-sig"))
        # Accept a raw snapshot or the full JSON report emitted by this command.
        if isinstance(snapshot, dict) and "snapshot" in snapshot:
            snapshot = snapshot["snapshot"]
        result = {"snapshot": snapshot, "assessment": classify(snapshot, arguments.prior_repair_recurred)}
    except (OSError, ValueError, KeyError, TypeError) as problem:
        result = {"assessment": {"preflight_status": "unknown", "science_status": "not_run"}, "error": str(problem)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["assessment"]["preflight_status"] == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
