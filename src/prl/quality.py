"""Explicit, bounded engineering checks for the current PRL application layer."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any, Iterable

from .workspace import find_workspace


QUICK_SUITE_SCHEMA = "prl.current_quick_suite.v1"
DEFAULT_MANIFEST = Path("tests/prl/quick_suite_v01.txt")
ALLOWED_TEST_PREFIX = PurePosixPath("tests/prl")
FORBIDDEN_IMPORT_ROOTS = {
    "basix",
    "dolfinx",
    "ncs_m1",
    "paper2_figure2",
    "paper2_hybrid",
    "paper2_m1",
    "scripts",
}
CONTAINER_ADAPTER_FILES = {'src/prl/fem/fenicsx_probe.py', 'src/prl/fem/fenicsx_ring.py'}
CONTAINER_IMPORT_ROOTS = {'basix', 'dolfinx', 'ffcx', 'ufl', 'mpi4py', 'petsc4py'}
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class QuickSuiteContractError(RuntimeError):
    """Raised when a quick-suite path violates the frozen repository boundary."""


def _is_reparse_point(path: Path) -> bool:
    metadata = path.lstat()
    return bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _checked_relative_file(workspace: Path, relative: str) -> Path:
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise QuickSuiteContractError(f"unsafe relative path: {relative}")
    if normalized.suffix != ".py":
        raise QuickSuiteContractError(f"quick-suite entry is not Python: {relative}")
    if normalized.parts[: len(ALLOWED_TEST_PREFIX.parts)] != ALLOWED_TEST_PREFIX.parts:
        raise QuickSuiteContractError(f"quick-suite entry is outside tests/prl: {relative}")

    candidate = workspace.joinpath(*normalized.parts)
    current = workspace
    for part in normalized.parts:
        current = current / part
        if current.exists() and _is_reparse_point(current):
            raise QuickSuiteContractError(f"quick-suite path crosses reparse point: {relative}")
    if not candidate.is_file():
        raise QuickSuiteContractError(f"quick-suite entry is missing: {relative}")
    try:
        candidate.resolve(strict=True).relative_to(workspace.resolve(strict=True))
    except ValueError as error:
        raise QuickSuiteContractError(f"quick-suite entry escapes workspace: {relative}") from error
    return candidate


def load_quick_suite(
    workspace: Path | str | None = None,
    manifest: Path | str | None = None,
) -> tuple[Path, list[str]]:
    root = find_workspace(workspace)
    manifest_relative = Path(manifest) if manifest is not None else DEFAULT_MANIFEST
    if manifest_relative.is_absolute():
        try:
            manifest_path = manifest_relative.resolve(strict=True)
            manifest_path.relative_to(root.resolve(strict=True))
        except (FileNotFoundError, ValueError) as error:
            raise QuickSuiteContractError("manifest must be an existing workspace file") from error
    else:
        if ".." in manifest_relative.parts:
            raise QuickSuiteContractError("manifest cannot escape the workspace")
        manifest_path = (root / manifest_relative).resolve(strict=True)
        try:
            manifest_path.relative_to(root.resolve(strict=True))
        except ValueError as error:
            raise QuickSuiteContractError("manifest escapes the workspace") from error
    if _is_reparse_point(manifest_path):
        raise QuickSuiteContractError("manifest cannot be a reparse point")

    entries = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not entries:
        raise QuickSuiteContractError("quick-suite manifest is empty")
    if len(entries) != len(set(entries)):
        raise QuickSuiteContractError("quick-suite manifest contains duplicate paths")
    for entry in entries:
        _checked_relative_file(root, entry)
    return manifest_path, entries


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _python_boundary_errors(path: Path, workspace: Path) -> list[str]:
    relative = path.relative_to(workspace).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    except (OSError, UnicodeError, SyntaxError) as error:
        return [f"{relative}: unreadable Python source: {error}"]

    errors: list[str] = []
    allowed_roots = set(sys.stdlib_module_names) | {
        "PIL",
        "matplotlib",
        "mpl_toolkits",
        "numpy",
        "prl",
        "scipy",
    }
    for node in ast.walk(tree):
        imported: Iterable[str] = ()
        if isinstance(node, ast.Import):
            imported = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported = (node.module,)
        for name in imported:
            root_name = name.split(".", 1)[0]
            if relative in CONTAINER_ADAPTER_FILES and root_name in CONTAINER_IMPORT_ROOTS:
                continue
            if root_name in FORBIDDEN_IMPORT_ROOTS:
                errors.append(f"{relative}:{node.lineno}: forbidden import {name}")
            elif root_name not in allowed_roots:
                errors.append(f"{relative}:{node.lineno}: undeclared import {name}")

        if isinstance(node, ast.Attribute) and _qualified_name(node) == "sys.path":
            errors.append(f"{relative}:{node.lineno}: sys.path mutation/access is forbidden")
        if isinstance(node, ast.Call) and _qualified_name(node.func) in {
            "importlib.util.spec_from_file_location",
            "runpy.run_path",
        }:
            errors.append(f"{relative}:{node.lineno}: dynamic file import is forbidden")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if WINDOWS_ABSOLUTE_PATH.match(node.value) or node.value.startswith(chr(92) * 2):
                errors.append(f"{relative}:{node.lineno}: machine-absolute path literal is forbidden")
    return errors


def _protected_identity_errors(workspace: Path) -> list[str]:
    baseline_path = (
        workspace
        / "project_control/evidence/repository_cleanup_v01"
        / "batch04_candidate03_exit_safe_slice_identity.json"
    )
    override_path = (
        workspace
        / "project_control/evidence/repository_cleanup_v01"
        / "final_closure_identity_overrides_v01.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    override_payload = json.loads(override_path.read_text(encoding="utf-8"))
    override_items = override_payload["protected_identity_overrides"]
    override_by_path = {item["path"]: item for item in override_items}
    errors: list[str] = []
    baseline_paths = {item["path"] for item in baseline["protected_unchanged"]}
    if len(override_by_path) != len(override_items):
        errors.append("protected identity overrides contain duplicate paths")
    unknown_overrides = sorted(set(override_by_path) - baseline_paths)
    if unknown_overrides:
        errors.append(
            "protected identity overrides contain unknown paths: "
            + ", ".join(unknown_overrides)
        )
    # Current application/package files are deliberately changed by the
    # authorized mainline refactor.  The immutable identity gate applies to
    # the selected retired-route evidence copies; pre-refactor identities of
    # active C++ sources are retained in the first root Git commit instead.
    protected_items = [
        item
        for item in baseline["protected_unchanged"]
        if item["path"].startswith("project_control/evidence/retired_routes_v01/")
    ]
    for item in protected_items:
        item = override_by_path.get(item["path"], item)
        path = workspace / item["path"]
        if not path.is_file():
            errors.append(f"protected path missing: {item['path']}")
            continue
        if path.stat().st_size != item["bytes"]:
            errors.append(f"protected byte count changed: {item['path']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            errors.append(f"protected SHA-256 changed: {item['path']}")
    return errors


def validate_quick_suite(
    workspace: Path | str | None = None,
    manifest: Path | str | None = None,
) -> dict[str, Any]:
    root = find_workspace(workspace)
    errors: list[str] = []
    try:
        manifest_path, entries = load_quick_suite(root, manifest)
    except (OSError, UnicodeError, QuickSuiteContractError) as error:
        manifest_path = root / (Path(manifest) if manifest is not None else DEFAULT_MANIFEST)
        entries = []
        errors.append(str(error))

    scanned_paths = sorted((root / "src/prl").rglob("*.py"))
    for entry in entries:
        scanned_paths.append(root.joinpath(*PurePosixPath(entry).parts))
    for path in scanned_paths:
        errors.extend(_python_boundary_errors(path, root))
    try:
        errors.extend(_protected_identity_errors(root))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"protected baseline unreadable: {error}")

    return {
        "schema_version": QUICK_SUITE_SCHEMA,
        "status": "passed" if not errors else "failed",
        "workspace": str(root),
        "manifest": manifest_path.relative_to(root).as_posix(),
        "test_paths": entries,
        "scanned_python_files": len(scanned_paths),
        "checks": {
            "explicit_files_only": bool(entries),
            "workspace_path_boundary": not any("path" in error for error in errors),
            "import_boundary": not any("import" in error or "sys.path" in error for error in errors),
            "protected_identity": not any("protected" in error for error in errors),
        },
        "errors": errors,
    }


def _pytest_command(test_paths: list[str]) -> list[str]:
    return [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-q",
        *test_paths,
    ]


def _captured_text(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output or ""


def run_quick_suite(
    workspace: Path | str | None = None,
    manifest: Path | str | None = None,
    *,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    root = find_workspace(workspace)
    contract = validate_quick_suite(root, manifest)
    if contract["status"] != "passed":
        return {
            **contract,
            "execution": "not_run",
            "return_code": None,
            "stdout": "",
            "stderr": "",
        }

    command = _pytest_command(contract["test_paths"])
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            **contract,
            "status": "failed",
            "execution": "timed_out",
            "return_code": None,
            "stdout": _captured_text(error.stdout),
            "stderr": _captured_text(error.stderr),
        }
    return {
        **contract,
        "status": "passed" if completed.returncode == 0 else "failed",
        "execution": "completed",
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
