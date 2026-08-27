from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


FROZEN_PROVENANCE_TEST = "test_r1_midpoint_diagnosis_evidence.py"
FORK_GITLINK_PATH = "external/simucell3d"


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout.strip()


def _gitlink(repo_root: Path) -> str:
    line = _git(repo_root, "ls-tree", "HEAD", FORK_GITLINK_PATH)
    metadata, path = line.split("\t", 1)
    mode, object_type, object_id = metadata.split()
    if mode != "160000" or object_type != "commit" or path != FORK_GITLINK_PATH:
        raise RuntimeError("controlled-fork Gitlink record is invalid")
    return object_id


class _ControlledForkRoot:
    def __init__(self, parent_root: Path) -> None:
        self.parent_root = parent_root

    def pytest_collection_modifyitems(self, items: list[Any]) -> None:
        for item in items:
            module_path = Path(item.module.__file__)
            if module_path.name == FROZEN_PROVENANCE_TEST:
                item.module.ROOT = self.parent_root


def _record(prefix: str, payload: dict[str, Any]) -> None:
    print(prefix, json.dumps(payload, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full Python suite with an explicit, read-only controlled-fork "
            "preflight and machine-readable identity records."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--controlled-parent-root", type=Path, required=True)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    controlled_parent_root = args.controlled_parent_root.resolve()
    fork_root = controlled_parent_root / FORK_GITLINK_PATH
    pytest_args = args.pytest_args or ["-q"]
    if pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    invocation = {
        "argv": sys.argv,
        "repo_root": str(repo_root),
        "controlled_parent_root": str(controlled_parent_root),
        "fork_root": str(fork_root),
        "pytest_args": pytest_args,
    }
    _record("V10R2_INVOCATION_JSON", invocation)

    head = _git(fork_root, "rev-parse", "HEAD")
    upstream = _git(fork_root, "rev-parse", "@{upstream}")
    tracked_status_text = _git(
        fork_root,
        "status",
        "--short",
        "--untracked-files=no",
    )
    tracked_status = [line for line in tracked_status_text.splitlines() if line]
    gitlink = _gitlink(repo_root)
    preflight = {
        "fork_head": head,
        "fork_upstream": upstream,
        "fork_tracked_clean": not tracked_status,
        "fork_tracked_status": tracked_status,
        "gitlink": gitlink,
    }
    _record("V10R2_PREFLIGHT_JSON", preflight)
    if head != upstream or head != gitlink or tracked_status:
        _record(
            "V10R2_RESULT_JSON",
            {"pytest_exit_code": 2, "wrapper_exit_code": 2},
        )
        return 2

    pytest_exit_code = int(
        pytest.main(
            pytest_args,
            plugins=[_ControlledForkRoot(controlled_parent_root)],
        )
    )
    _record(
        "V10R2_RESULT_JSON",
        {
            "pytest_exit_code": pytest_exit_code,
            "wrapper_exit_code": pytest_exit_code,
        },
    )
    return pytest_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
