from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import pytest


FORK_COMMIT = "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a"
FROZEN_PROVENANCE_TEST = "test_r1_midpoint_diagnosis_evidence.py"


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


class _ControlledForkRoot:
    def __init__(self, parent_root: Path) -> None:
        self.parent_root = parent_root

    def pytest_collection_modifyitems(self, items: list[Any]) -> None:
        for item in items:
            module_path = Path(item.module.__file__)
            if module_path.name == FROZEN_PROVENANCE_TEST:
                item.module.ROOT = self.parent_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full Python suite while the frozen v10 provenance test reads "
            "an existing controlled-fork worktree."
        )
    )
    parser.add_argument("--controlled-parent-root", type=Path, required=True)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    parent_root = args.controlled_parent_root.resolve()
    fork = parent_root / "external/simucell3d"
    head = _git(fork, "rev-parse", "HEAD")
    upstream = _git(fork, "rev-parse", "@{upstream}")
    tracked_status = _git(fork, "status", "--short", "--untracked-files=no")
    if head != FORK_COMMIT or upstream != FORK_COMMIT or tracked_status:
        raise RuntimeError(
            "controlled fork must be clean at the frozen v10 Gitlink commit"
        )
    pytest_args = args.pytest_args or ["-q"]
    if pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    return pytest.main(pytest_args, plugins=[_ControlledForkRoot(parent_root)])


if __name__ == "__main__":
    raise SystemExit(main())
