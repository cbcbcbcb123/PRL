"""Stable command-line interface for PRL repository operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .quality import run_quick_suite
from .runs import run_contact_performance_equilibrium
from .storage import evaluate_storage, scan_workspace
from .verification import verify_contact_performance_equilibrium, verify_long_doublet
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
    contact_verify = verify_commands.add_parser(
        "contact-performance-equilibrium",
        help="verify the frozen contact performance/equilibrium task",
    )
    contact_verify.add_argument("--workspace", type=Path)
    contact_verify.add_argument("--result", type=Path)
    contact_verify.add_argument(
        "--phase", choices=("q", "equilibrium"), default="q"
    )

    run = commands.add_parser("run", help="bounded active-mainline scientific runs")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    contact_run = run_commands.add_parser(
        "contact-performance-equilibrium",
        help="run one create-only phase of the frozen CPU task",
    )
    contact_run.add_argument("--workspace", type=Path)
    contact_run.add_argument("--result", type=Path)
    contact_run.add_argument(
        "--phase", choices=("q", "equilibrium"), default="q"
    )

    render = commands.add_parser("render", help="render retained results and cockpit")
    render_commands = render.add_subparsers(dest="render_command", required=True)
    contact_render = render_commands.add_parser(
        "contact-performance-equilibrium",
        help="render the frozen contact performance/equilibrium task",
    )
    contact_render.add_argument("--workspace", type=Path)
    contact_render.add_argument("--result", type=Path)
    cockpit_render = render_commands.add_parser("cockpit", help="render the project cockpit")
    cockpit_render.add_argument("--workspace", type=Path)

    validate = commands.add_parser("validate", help="strict project metadata checks")
    validate_commands = validate.add_subparsers(dest="validate_command", required=True)
    cockpit_validate = validate_commands.add_parser("cockpit", help="validate all cockpit links")
    cockpit_validate.add_argument("--workspace", type=Path)

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
    elif (
        parsed.command == "verify"
        and parsed.verify_command == "contact-performance-equilibrium"
    ):
        report = verify_contact_performance_equilibrium(
            workspace, parsed.result, phase=parsed.phase
        )
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "contact-performance-equilibrium":
        report = run_contact_performance_equilibrium(
            workspace, parsed.result, phase=parsed.phase
        )
        exit_code = 0 if report["status"] == "passed" else 1
    elif (
        parsed.command == "render"
        and parsed.render_command == "contact-performance-equilibrium"
    ):
        from .rendering import render_contact_performance_equilibrium

        report = render_contact_performance_equilibrium(workspace, parsed.result)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "cockpit":
        from .cockpit import render_cockpit

        report = render_cockpit(workspace)
        exit_code = 0
    elif parsed.command == "validate" and parsed.validate_command == "cockpit":
        from .cockpit import validate_cockpit_links

        report = validate_cockpit_links(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "test" and parsed.test_command == "quick":
        report = run_quick_suite(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    else:  # pragma: no cover - argparse prevents this branch
        raise AssertionError("Unhandled command")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code
