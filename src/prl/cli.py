"""Stable command-line interface for PRL repository operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .quality import run_quick_suite
from .storage import evaluate_storage, scan_workspace
from .verification import verify_long_doublet
from .workspace import find_workspace


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m prl")
    commands = parser.add_subparsers(dest="command", required=True)

    storage = commands.add_parser("storage", help="repository storage operations")
    storage_commands = storage.add_subparsers(dest="storage_command", required=True)
    storage_status = storage_commands.add_parser("status", help="show storage admission status")
    storage_status.add_argument("--workspace", type=Path)
    storage_status.add_argument("--planned-new-bytes", type=int)
    storage_status.add_argument("--stop-reserve-bytes", type=int)

    verify = commands.add_parser("verify", help="independent evidence verification")
    verify_commands = verify.add_subparsers(dest="verify_command", required=True)
    long_doublet = verify_commands.add_parser(
        "long-doublet", help="verify retained long-doublet scalar ledgers"
    )
    long_doublet.add_argument("--workspace", type=Path)
    long_doublet.add_argument("--result", type=Path)

    tests = commands.add_parser("test", help="bounded engineering test suites")
    test_commands = tests.add_subparsers(dest="test_command", required=True)
    quick = test_commands.add_parser(
        "quick", help="run the explicit current application quick suite"
    )
    quick.add_argument("--workspace", type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = _parser().parse_args(arguments)
    workspace = find_workspace(parsed.workspace)
    if parsed.command == "storage" and parsed.storage_command == "status":
        report = evaluate_storage(
            scan_workspace(workspace),
            planned_new_bytes=parsed.planned_new_bytes,
            stop_reserve_bytes=parsed.stop_reserve_bytes,
        )
        exit_code = 0
    elif parsed.command == "verify" and parsed.verify_command == "long-doublet":
        report = verify_long_doublet(workspace, parsed.result)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "test" and parsed.test_command == "quick":
        report = run_quick_suite(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    else:  # pragma: no cover - argparse prevents this branch
        raise AssertionError("Unhandled command")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code
