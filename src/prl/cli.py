"""Stable command-line interface for PRL repository operations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from .diagnostics import diagnose_terminal_residual
from .quality import run_quick_suite
from .runs import run_contact_performance_equilibrium
from .storage import evaluate_storage, scan_workspace
from .verification import (
    verify_contact_performance_equilibrium,
    verify_long_doublet,
    verify_terminal_residual_diagnosis,
)
from .workspace import find_workspace


FEM_RUN_COMMANDS = frozenset({
    "fem-active-ellipse", "fem-synthetic-orientation", "fem-measured-contour",
    "fem-fixed-mesh", "fem-finite-strain", "fem-rotation", "fem-curved-pressure", "fem-contour-pressure",
    "fem-fenicsx-ring", "fem-fenicsx-contour",
})
FEM_ONLY_DECISION = "project_control/ventricle_fem_only_measured_contour_decision_v01.md"


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
    terminal_verify = verify_commands.add_parser(
        "terminal-residual-diagnosis",
        help="independently verify the retained terminal-residual diagnosis",
    )
    terminal_verify.add_argument("--workspace", type=Path)
    terminal_verify.add_argument("--result", type=Path)

    passive_verify = verify_commands.add_parser("passive-mechanics", help="independent real-kernel force-energy verification")
    passive_verify.add_argument("--workspace", type=Path)
    passive_verify.add_argument("--result", type=Path)
    passive_verify.add_argument("--phase", choices=("red", "green"), default="green")
    sheet_verify = verify_commands.add_parser("myocardial-sheet", help="independent paired sheet qualification")
    sheet_verify.add_argument("--workspace", type=Path)
    row_verify = verify_commands.add_parser(
        "myocardial-row", help="independently verify the heterogeneous five-cell equilibrium"
    )
    row_verify.add_argument("--workspace", type=Path)
    row_verify.add_argument("--result", type=Path)
    crowded_box_verify = verify_commands.add_parser(
        "myocardial-crowded-box",
        help="independently verify the retained 5x5 crowded-box pilot",
    )
    crowded_box_verify.add_argument("--workspace", type=Path)
    crowded_box_verify.add_argument("--result", type=Path)
    target_pair_verify = verify_commands.add_parser(
        "myocardial-crowded-target-pair",
        help="independently verify the matched 5x5 reference-target comparison",
    )
    target_pair_verify.add_argument("--workspace", type=Path)
    target_pair_verify.add_argument("--result", type=Path)
    volume_x2_verify = verify_commands.add_parser(
        "myocardial-crowded-volume-x2",
        help="independently verify the 5x5 doubled-volume-target response",
    )
    volume_x2_verify.add_argument("--workspace", type=Path)
    volume_x2_verify.add_argument("--result", type=Path)
    quasistatic_verify = verify_commands.add_parser(
        "myocardial-crowded-quasistatic-growth",
        help="independently verify quasistatic doubled-target growth",
    )
    quasistatic_verify.add_argument("--workspace", type=Path)
    quasistatic_verify.add_argument("--result", type=Path)
    common_limit_verify = verify_commands.add_parser(
        "regular-dcm-fem-common-limit",
        help="verify the staged DCM--FEM common-limit engineering evidence",
    )
    common_limit_verify.add_argument("--workspace", type=Path)
    common_limit_verify.add_argument("--result", type=Path)
    regular_patch_verify = verify_commands.add_parser(
        "regular-2x2-load-hold",
        help="independently verify the regular 2x2 DCM load-hold stage",
    )
    regular_patch_verify.add_argument("--workspace", type=Path)
    regular_patch_verify.add_argument("--result", type=Path)
    fem_verify = verify_commands.add_parser(
        "fem-active-ellipse",
        help="independently verify the synthetic active elliptic FEM pilot",
    )
    fem_verify.add_argument("--workspace", type=Path)
    fem_verify.add_argument("--result", type=Path)
    orientation_verify = verify_commands.add_parser(
        "fem-synthetic-orientation",
        help="independently verify the synthetic myocardial orientation-field gate",
    )
    orientation_verify.add_argument("--workspace", type=Path)
    orientation_verify.add_argument("--result", type=Path)
    contour_verify = verify_commands.add_parser(
        "fem-measured-contour", help="independently verify the image-derived outer-contour FEM pilot"
    )
    contour_verify.add_argument("--workspace", type=Path)
    contour_verify.add_argument("--result", type=Path)
    fixed_mesh_verify = verify_commands.add_parser(
        "fem-fixed-mesh", help="independently verify retained fixed-domain FEM refinement states"
    )
    fixed_mesh_verify.add_argument("--workspace", type=Path)
    fixed_mesh_verify.add_argument("--result", type=Path)
    finite_strain_verify = verify_commands.add_parser(
        "fem-finite-strain", help="independently verify saved 3-D finite-strain FEM engineering states"
    )
    finite_strain_verify.add_argument("--workspace", type=Path)
    finite_strain_verify.add_argument("--result", type=Path)
    rotation_verify = verify_commands.add_parser(
        "fem-rotation", help="independently verify the retained finite-strain rotation repair"
    )
    rotation_verify.add_argument("--workspace", type=Path)
    rotation_verify.add_argument("--result", type=Path)
    curved_pressure_verify = verify_commands.add_parser(
        "fem-curved-pressure", help="independently verify retained curved-wall follower-pressure states"
    )
    curved_pressure_verify.add_argument("--workspace", type=Path)
    curved_pressure_verify.add_argument("--result", type=Path)
    contour_pressure_verify = verify_commands.add_parser(
        "fem-contour-pressure", help="independently verify saved image-outline finite-deformation pressure states"
    )
    contour_pressure_verify.add_argument("--workspace", type=Path)
    contour_pressure_verify.add_argument("--result", type=Path)

    run = commands.add_parser("run", help="bounded FEM-only runs; historical DCM entries reject execution")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    sheet_run = run_commands.add_parser("myocardial-sheet", help="bounded regular/irregular sheet phase")
    sheet_run.add_argument("--workspace", type=Path)
    sheet_run.add_argument("--phase", choices=("static", "pilot"), default="static")
    row_run = run_commands.add_parser(
        "myocardial-row", help="run the create-only heterogeneous five-cell equilibrium"
    )
    row_run.add_argument("--workspace", type=Path)
    crowded_box_run = run_commands.add_parser(
        "myocardial-crowded-box",
        help="run the create-only 5x5 passive crowded-box pilot",
    )
    crowded_box_run.add_argument("--workspace", type=Path)
    target_pair_run = run_commands.add_parser(
        "myocardial-crowded-target-pair",
        help="run the create-only two-condition 5x5 reference-target comparison",
    )
    target_pair_run.add_argument("--workspace", type=Path)
    volume_x2_run = run_commands.add_parser(
        "myocardial-crowded-volume-x2",
        help="run the create-only 5x5 doubled-volume-target condition",
    )
    volume_x2_run.add_argument("--workspace", type=Path)
    quasistatic_run = run_commands.add_parser(
        "myocardial-crowded-quasistatic-growth",
        help="run the bounded quasistatic doubled-target qualification",
    )
    quasistatic_run.add_argument("--workspace", type=Path)
    regular_patch_run = run_commands.add_parser(
        "regular-2x2-load-hold",
        help="run the create-only regular 2x2 DCM load-hold qualification",
    )
    regular_patch_run.add_argument("--workspace", type=Path)
    contact_run = run_commands.add_parser(
        "contact-performance-equilibrium",
        help="run one create-only phase of the frozen CPU task",
    )
    contact_run.add_argument("--workspace", type=Path)
    contact_run.add_argument("--result", type=Path)
    contact_run.add_argument(
        "--phase", choices=("q", "equilibrium"), default="q"
    )
    fem_run = run_commands.add_parser(
        "fem-active-ellipse",
        help="run the create-only synthetic active elliptic FEM pilot",
    )
    fem_run.add_argument("--workspace", type=Path)
    orientation_run = run_commands.add_parser(
        "fem-synthetic-orientation",
        help="run the create-only paired synthetic orientation-field FEM gate",
    )
    orientation_run.add_argument("--workspace", type=Path)
    contour_run = run_commands.add_parser(
        "fem-measured-contour", help="run the bounded create-only image-derived outer-contour FEM pilot"
    )
    contour_run.add_argument("--workspace", type=Path)
    fixed_mesh_run = run_commands.add_parser(
        "fem-fixed-mesh", help="run the bounded create-only fixed-domain FEM refinement gate"
    )
    fixed_mesh_run.add_argument("--workspace", type=Path)
    finite_strain_run = run_commands.add_parser(
        "fem-finite-strain", help="run the bounded create-only 3-D finite-strain FEM qualification"
    )
    finite_strain_run.add_argument("--workspace", type=Path)
    rotation_run = run_commands.add_parser(
        "fem-rotation", help="run only the bounded create-only rotation qualification repair"
    )
    rotation_run.add_argument("--workspace", type=Path)
    curved_pressure_run = run_commands.add_parser(
        "fem-curved-pressure", help="run the bounded create-only curved-wall follower-pressure qualification"
    )
    curved_pressure_run.add_argument("--workspace", type=Path)
    contour_pressure_run = run_commands.add_parser(
        "fem-contour-pressure", help="run only the bounded create-only image-outline pressure controller"
    )
    contour_pressure_run.add_argument("--workspace", type=Path)

    diagnose = commands.add_parser("diagnose", help="bounded diagnostics over retained evidence")
    diagnose_commands = diagnose.add_subparsers(dest="diagnose_command", required=True)
    terminal_residual = diagnose_commands.add_parser(
        "terminal-residual",
        help="diagnose the retained doublet residual without running a solver",
    )
    terminal_residual.add_argument("--workspace", type=Path)
    terminal_residual.add_argument("--source", type=Path)
    terminal_residual.add_argument("--output", type=Path)

    passive_diagnosis = diagnose_commands.add_parser("passive-mechanics", help="bounded RED/GREEN kernel qualification, not tissue dynamics")
    passive_diagnosis.add_argument("--workspace", type=Path)
    passive_diagnosis.add_argument("--phase", choices=("red", "green", "regressions"), required=True)

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
    row_render = render_commands.add_parser(
        "myocardial-row", help="render the retained heterogeneous five-cell equilibrium"
    )
    row_render.add_argument("--workspace", type=Path)
    row_render.add_argument("--result", type=Path)
    crowded_box_render = render_commands.add_parser(
        "myocardial-crowded-box",
        help="render the retained 5x5 crowded-box pilot",
    )
    crowded_box_render.add_argument("--workspace", type=Path)
    crowded_box_render.add_argument("--result", type=Path)
    target_pair_render = render_commands.add_parser(
        "myocardial-crowded-target-pair",
        help="render the retained matched 5x5 reference-target comparison",
    )
    target_pair_render.add_argument("--workspace", type=Path)
    target_pair_render.add_argument("--result", type=Path)
    volume_x2_render = render_commands.add_parser(
        "myocardial-crowded-volume-x2",
        help="render the retained 5x5 doubled-volume-target result",
    )
    volume_x2_render.add_argument("--workspace", type=Path)
    volume_x2_render.add_argument("--result", type=Path)
    quasistatic_render = render_commands.add_parser(
        "myocardial-crowded-quasistatic-growth",
        help="render retained quasistatic doubled-target results",
    )
    quasistatic_render.add_argument("--workspace", type=Path)
    quasistatic_render.add_argument("--result", type=Path)
    common_limit_render = render_commands.add_parser(
        "regular-dcm-fem-common-limit",
        help="render actual retained states from the staged DCM--FEM work",
    )
    common_limit_render.add_argument("--workspace", type=Path)
    common_limit_render.add_argument("--result", type=Path)
    regular_patch_render = render_commands.add_parser(
        "regular-2x2-load-hold",
        help="render actual retained regular 2x2 DCM states",
    )
    regular_patch_render.add_argument("--workspace", type=Path)
    regular_patch_render.add_argument("--result", type=Path)
    fem_render = render_commands.add_parser(
        "fem-active-ellipse",
        help="render retained states from the active elliptic FEM pilot",
    )
    fem_render.add_argument("--workspace", type=Path)
    fem_render.add_argument("--result", type=Path)
    orientation_render = render_commands.add_parser(
        "fem-synthetic-orientation",
        help="render retained paired synthetic orientation-field FEM states",
    )
    orientation_render.add_argument("--workspace", type=Path)
    orientation_render.add_argument("--result", type=Path)
    contour_render = render_commands.add_parser(
        "fem-measured-contour", help="render retained image-derived outer-contour FEM states"
    )
    contour_render.add_argument("--workspace", type=Path)
    contour_render.add_argument("--result", type=Path)
    fixed_mesh_render = render_commands.add_parser(
        "fem-fixed-mesh", help="render saved fixed-domain FEM refinement states without solving"
    )
    fixed_mesh_render.add_argument("--workspace", type=Path)
    fixed_mesh_render.add_argument("--result", type=Path)
    finite_strain_render = render_commands.add_parser(
        "fem-finite-strain", help="render saved 3-D finite-strain engineering states without solving"
    )
    finite_strain_render.add_argument("--workspace", type=Path)
    finite_strain_render.add_argument("--result", type=Path)
    rotation_render = render_commands.add_parser(
        "fem-rotation", help="render saved rotation and perturbation-recovery evidence without solving"
    )
    rotation_render.add_argument("--workspace", type=Path)
    rotation_render.add_argument("--result", type=Path)
    curved_pressure_render = render_commands.add_parser(
        "fem-curved-pressure", help="render retained curved-wall pressure states without solving"
    )
    curved_pressure_render.add_argument("--workspace", type=Path)
    curved_pressure_render.add_argument("--result", type=Path)
    contour_pressure_render = render_commands.add_parser(
        "fem-contour-pressure", help="render saved image-outline pressure states without solving"
    )
    contour_pressure_render.add_argument("--workspace", type=Path)
    contour_pressure_render.add_argument("--result", type=Path)

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
    fenicsx_run = run_commands.add_parser('fem-fenicsx-ring', help='one bounded F6-S0 invocation after G0')
    fenicsx_run.add_argument('--workspace', type=Path)
    fenicsx_run.add_argument('--complete-active', action='store_true', help='only the 16 uncomputed G2 states; reuse G1')
    fenicsx_verify = verify_commands.add_parser('fem-fenicsx-ring', help='independent saved-state P2/P1 audit')
    fenicsx_verify.add_argument('--workspace', type=Path)
    fenicsx_verify.add_argument('--result', type=Path)
    fenicsx_verify.add_argument('--stage', choices=['passive','all'], default='all')
    fenicsx_render = render_commands.add_parser('fem-fenicsx-ring', help='render saved FEniCSx states')
    fenicsx_render.add_argument('--workspace', type=Path)
    fenicsx_render.add_argument('--result', type=Path)
    for group in [run_commands,verify_commands,render_commands]:
        contour=group.add_parser('fem-fenicsx-contour',help='F6-S1 image-derived passive contour')
        contour.add_argument('--workspace',type=Path)
        contour_mode=contour.add_mutually_exclusive_group()
        contour_mode.add_argument('--repair-thin-mesh',action='store_true',help='F6-S1-M bounded thin-layer mesh repair')
        contour_mode.add_argument('--retained-passive',action='store_true',help='F6-S1-P reuse qualified mesh, 800 MiB stage')
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = _parser().parse_args(arguments)
    if (
        parsed.command == "run" and parsed.run_command not in FEM_RUN_COMMANDS
    ) or (
        parsed.command == "diagnose" and parsed.diagnose_command == "passive-mechanics"
    ):
        print(json.dumps({
            "status": "blocked",
            "execution": "not_run",
            "reason": "FEM-only: 当前项目不再运行 DCM；历史证据的 verify/render 入口仍保留。",
            "decision": FEM_ONLY_DECISION,
            "solver_calls": 0,
        }, ensure_ascii=False, indent=2))
        return 1
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
    elif parsed.command == "verify" and parsed.verify_command == "terminal-residual-diagnosis":
        report = verify_terminal_residual_diagnosis(workspace, parsed.result)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-sheet":
        from .runs.myocardial_sheet import RESULT
        from .verification.myocardial_sheet import verify_sheet
        report = verify_sheet(workspace / RESULT)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-sheet":
        from .runs.myocardial_sheet import run_sheet
        report = run_sheet(workspace, parsed.phase)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-row":
        from .runs.myocardial_row import run_myocardial_row

        report = run_myocardial_row(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-crowded-box":
        from .runs.myocardial_crowded_box import run_myocardial_crowded_box

        report = run_myocardial_crowded_box(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-crowded-target-pair":
        from .runs.myocardial_crowded_target_pair import run_myocardial_crowded_target_pair

        report = run_myocardial_crowded_target_pair(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-crowded-volume-x2":
        from .runs.myocardial_crowded_volume_x2 import run_myocardial_crowded_volume_x2

        report = run_myocardial_crowded_volume_x2(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "myocardial-crowded-quasistatic-growth":
        from .runs.myocardial_crowded_quasistatic_growth import (
            run_myocardial_crowded_quasistatic_growth,
        )

        report = run_myocardial_crowded_quasistatic_growth(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "regular-2x2-load-hold":
        from .runs.regular_2x2_load_hold import run_regular_2x2_load_hold

        report = run_regular_2x2_load_hold(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif ((parsed.command=='run' and parsed.run_command=='fem-fenicsx-contour') or
          (parsed.command=='verify' and parsed.verify_command=='fem-fenicsx-contour') or
          (parsed.command=='render' and parsed.render_command=='fem-fenicsx-contour')):
        from .runs.fenicsx_contour import RESULT,REPAIR_RESULT,PASSIVE_RESULT,run_contour
        contour_result=workspace/(PASSIVE_RESULT if parsed.retained_passive else REPAIR_RESULT if parsed.repair_thin_mesh else RESULT)
        if parsed.command=='run':
            report=run_contour(workspace,repair=parsed.repair_thin_mesh,retained=parsed.retained_passive)
        elif parsed.command=='verify':
            from .verification.fenicsx_contour import verify_contour,verify_mesh_repair
            report=verify_mesh_repair(contour_result) if parsed.repair_thin_mesh else verify_contour(contour_result)
        else:
            from .rendering.fenicsx_contour import render_contour
            report=render_contour(contour_result)
        exit_code=0 if report['status']=='passed' else 1
    elif parsed.command == 'run' and parsed.run_command == 'fem-fenicsx-ring':
        from .runs.fenicsx_ring import run_fenicsx_ring, run_active_completion

        report = run_active_completion(workspace) if parsed.complete_active else run_fenicsx_ring(workspace)
        exit_code = 0 if report['status']=='passed' else 1
    elif parsed.command == 'verify' and parsed.verify_command == 'fem-fenicsx-ring':
        from .runs.fenicsx_runtime import RESULT
        from .verification.fenicsx_ring import verify_fenicsx_ring

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fenicsx_ring(result_path, stage=parsed.stage)
        exit_code = 0 if report['status']=='passed' else 1
    elif parsed.command == 'render' and parsed.render_command == 'fem-fenicsx-ring':
        from .runs.fenicsx_runtime import RESULT
        from .rendering.fenicsx_ring import render_fenicsx_ring

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fenicsx_ring(result_path)
        exit_code = 0 if report['status']=='passed' else 1
    elif parsed.command == "run" and parsed.run_command == "fem-active-ellipse":
        from .runs.fem_active_ellipse import run_fem_active_ellipse

        report = run_fem_active_ellipse(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "fem-synthetic-orientation":
        from .runs.fem_synthetic_orientation import run_fem_synthetic_orientation

        report = run_fem_synthetic_orientation(workspace)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command in ("fem-measured-contour", "fem-fixed-mesh", "fem-finite-strain", "fem-rotation", "fem-curved-pressure", "fem-contour-pressure"):
        # Always enter the controller, never its worker. It owns the single-thread
        # environment, inner wall-time limit, storage admission and create-only path.
        # The public CLI gives the controller 60 s beyond its frozen worker cap.
        module_name, outer_timeout = {
            "fem-measured-contour": ("prl.runs.fem_measured_contour", 660),
            "fem-fixed-mesh": ("prl.runs.fem_fixed_mesh", 960),
            "fem-finite-strain": ("prl.runs.fem_finite_strain", 1260),
            "fem-rotation": ("prl.runs.fem_rotation", 360),
            "fem-curved-pressure": ("prl.runs.fem_curved_pressure", 660),
            "fem-contour-pressure": ("prl.runs.fem_contour_pressure", 1260),
        }[parsed.run_command]
        command = [sys.executable, "-B", "-X", "utf8", "-m",
                   module_name, "--workspace", str(workspace)]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(workspace / "src")
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            environment[key] = "1"
        try:
            completed = subprocess.run(
                command, cwd=workspace, env=environment, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=outer_timeout, check=False,
            )
            exit_code = 0 if completed.returncode == 0 else 1
            report = {
                "status": "passed" if exit_code == 0 else "failed",
                "execution": "bounded_fem_controller_completed",
                "return_code": completed.returncode,
                "stdout": completed.stdout, "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired:
            exit_code = 1
            report = {"status": "failed", "execution": "controller_timeout",
                      "reason": f"FEM controller exceeded its {outer_timeout} s outer guard; no retry"}
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-row":
        from .runs.myocardial_row import RESULT
        from .verification.myocardial_row import verify_myocardial_row

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_myocardial_row(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-crowded-box":
        from .runs.myocardial_crowded_box import RESULT
        from .verification.myocardial_crowded_box import verify_myocardial_crowded_box

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_myocardial_crowded_box(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-crowded-target-pair":
        from .runs.myocardial_crowded_target_pair import RESULT
        from .verification.myocardial_crowded_target_pair import verify_myocardial_crowded_target_pair

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_myocardial_crowded_target_pair(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-crowded-volume-x2":
        from .runs.myocardial_crowded_volume_x2 import RESULT
        from .verification.myocardial_crowded_volume_x2 import verify_myocardial_crowded_volume_x2

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_myocardial_crowded_volume_x2(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "myocardial-crowded-quasistatic-growth":
        from .runs.myocardial_crowded_quasistatic_growth import RESULT
        from .verification.myocardial_crowded_quasistatic_growth import (
            verify_myocardial_crowded_quasistatic_growth,
        )

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_myocardial_crowded_quasistatic_growth(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "passive-mechanics":
        from .diagnostics.passive_mechanics import RESULT
        from .verification.passive_mechanics import verify_passive_mechanics

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_passive_mechanics(result_path, parsed.phase)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "regular-dcm-fem-common-limit":
        from .verification.regular_dcm_fem_common_limit import (
            RESULT,
            verify_regular_dcm_fem_common_limit,
        )

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_regular_dcm_fem_common_limit(result_path, save=True)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "regular-2x2-load-hold":
        from .runs.regular_2x2_load_hold import RESULT
        from .verification.regular_2x2_load_hold import verify_regular_2x2_load_hold

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_regular_2x2_load_hold(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-active-ellipse":
        from .runs.fem_active_ellipse import RESULT
        from .verification.fem_active_ellipse import verify_fem_active_ellipse

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_active_ellipse(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-synthetic-orientation":
        from .runs.fem_synthetic_orientation import RESULT
        from .verification.fem_synthetic_orientation import (
            verify_fem_synthetic_orientation,
        )

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_synthetic_orientation(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-measured-contour":
        from .runs.fem_measured_contour import RESULT
        from .verification.fem_measured_contour import verify_fem_measured_contour

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_measured_contour(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-fixed-mesh":
        from .runs.fem_fixed_mesh import RESULT
        from .verification.fem_fixed_mesh import verify_fem_fixed_mesh

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_fixed_mesh(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-finite-strain":
        from .runs.fem_finite_strain import RESULT
        from .verification.fem_finite_strain import verify_fem_finite_strain

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_finite_strain(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-rotation":
        from .runs.fem_rotation import RESULT
        from .verification.fem_rotation import verify_fem_rotation

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_rotation(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-curved-pressure":
        from .runs.fem_curved_pressure import RESULT
        from .verification.fem_curved_pressure import verify_fem_curved_pressure

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_curved_pressure(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "verify" and parsed.verify_command == "fem-contour-pressure":
        from .runs.fem_contour_pressure import RESULT
        from .verification.fem_contour_pressure import verify_fem_contour_pressure

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = verify_fem_contour_pressure(result_path, save=False)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "run" and parsed.run_command == "contact-performance-equilibrium":
        report = run_contact_performance_equilibrium(
            workspace, parsed.result, phase=parsed.phase
        )
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "diagnose" and parsed.diagnose_command == "terminal-residual":
        report = diagnose_terminal_residual(workspace, parsed.source, parsed.output)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "diagnose" and parsed.diagnose_command == "passive-mechanics":
        from .diagnostics.passive_mechanics import run_audit, run_regressions

        report = run_regressions(workspace) if parsed.phase == "regressions" else run_audit(parsed.phase, workspace)
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
    elif parsed.command == "render" and parsed.render_command == "myocardial-row":
        from .rendering.myocardial_row import render_myocardial_row
        from .runs.myocardial_row import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_myocardial_row(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "myocardial-crowded-box":
        from .rendering.myocardial_crowded_box import render_myocardial_crowded_box
        from .runs.myocardial_crowded_box import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_myocardial_crowded_box(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "myocardial-crowded-target-pair":
        from .rendering.myocardial_crowded_target_pair import render_myocardial_crowded_target_pair
        from .runs.myocardial_crowded_target_pair import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_myocardial_crowded_target_pair(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "myocardial-crowded-volume-x2":
        from .rendering.myocardial_crowded_volume_x2 import render_myocardial_crowded_volume_x2
        from .runs.myocardial_crowded_volume_x2 import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_myocardial_crowded_volume_x2(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "myocardial-crowded-quasistatic-growth":
        from .rendering.myocardial_crowded_quasistatic_growth import (
            render_myocardial_crowded_quasistatic_growth,
        )
        from .runs.myocardial_crowded_quasistatic_growth import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_myocardial_crowded_quasistatic_growth(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "regular-dcm-fem-common-limit":
        from .rendering.regular_dcm_fem_common_limit import (
            render_regular_dcm_fem_common_limit,
        )
        from .verification.regular_dcm_fem_common_limit import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_regular_dcm_fem_common_limit(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "regular-2x2-load-hold":
        from .rendering.regular_2x2_load_hold import render_regular_2x2_load_hold
        from .runs.regular_2x2_load_hold import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_regular_2x2_load_hold(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-active-ellipse":
        from .rendering.fem_active_ellipse import render_fem_active_ellipse
        from .runs.fem_active_ellipse import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_active_ellipse(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-synthetic-orientation":
        from .rendering.fem_synthetic_orientation import render_fem_synthetic_orientation
        from .runs.fem_synthetic_orientation import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_synthetic_orientation(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-measured-contour":
        from .rendering.fem_measured_contour import render_fem_measured_contour
        from .runs.fem_measured_contour import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_measured_contour(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-fixed-mesh":
        from .rendering.fem_fixed_mesh import render_fem_fixed_mesh
        from .runs.fem_fixed_mesh import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_fixed_mesh(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-finite-strain":
        from .rendering.fem_finite_strain import render_fem_finite_strain
        from .runs.fem_finite_strain import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_finite_strain(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-rotation":
        from .rendering.fem_rotation import render_fem_rotation
        from .runs.fem_rotation import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_rotation(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-curved-pressure":
        from .rendering.fem_curved_pressure import render_fem_curved_pressure
        from .runs.fem_curved_pressure import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_curved_pressure(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
    elif parsed.command == "render" and parsed.render_command == "fem-contour-pressure":
        from .rendering.fem_contour_pressure import render_fem_contour_pressure
        from .runs.fem_contour_pressure import RESULT

        result_path = parsed.result or RESULT
        if not result_path.is_absolute():
            result_path = workspace / result_path
        report = render_fem_contour_pressure(result_path)
        exit_code = 0 if report["status"] == "passed" else 1
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
