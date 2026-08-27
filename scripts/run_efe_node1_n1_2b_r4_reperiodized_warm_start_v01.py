from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    build_exact_volume_coordinates,
)
from hybrid.efe_step_transaction import (  # noqa: E402
    PeriodicWarmStartMetrics,
    audit_periodic_warm_start,
    checkpoint_array_digest,
    file_sha256,
    write_checkpoint_exclusive,
)
from prepare_efe_node1_n1_2_periodic_warm_start_v01 import (  # noqa: E402
    apply_frozen_geometry_cycle,
    relative_difference,
)
from run_efe_node1_n1_2_periodic_case_v01 import (  # noqa: E402
    load_checkpoint,
    record_sample,
)


DEFAULT_SOURCE_CYCLE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v02_20260820"
    / "cycle_04"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r4_reperiodized_warm_start_v01_20260820"
)
INITIALIZER = (
    ROOT / "scripts/prepare_efe_node1_n1_2_periodic_warm_start_v01.py"
)
TRANSACTION_MODULE = ROOT / "src/hybrid/efe_step_transaction.py"
PERIODIC_RUNNER = ROOT / "scripts/run_efe_node1_n1_2_periodic_case_v01.py"
AUTHORIZATION = (
    "project_control/"
    "efe_node1_n1_2b_r3_acceptance_and_r4_authorization_decision_v01.md"
)
WARM_DRIVER = Path(__file__).resolve()


def run_initializer(command: list[str], evidence_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    record = {
        "command": command,
        "returncode": process.returncode,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    evidence_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-cycle-directory", type=Path, default=DEFAULT_SOURCE_CYCLE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--period", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--run-label", choices=("r4", "r5"), default="r4")
    parser.add_argument("--first-cycle-index", type=int, default=5)
    parser.add_argument("--authorization", default=AUTHORIZATION)
    arguments = parser.parse_args()

    source_cycle = arguments.source_cycle_directory.resolve()
    output_path = arguments.output.resolve()
    run_label = arguments.run_label
    if arguments.first_cycle_index < 1:
        raise ValueError("first cycle index must be positive")
    if output_path.exists():
        raise FileExistsError(
            f"{run_label} warm-start output already exists: {output_path}"
        )
    if arguments.period <= 0.0 or arguments.steps < 1:
        raise ValueError("period and steps must be positive")
    output_path.mkdir(parents=True)
    staging_path = output_path / "initializer_staging"

    initializer_command = [
        sys.executable,
        str(INITIALIZER),
        "--cycle-directory",
        str(source_cycle),
        "--output",
        str(staging_path),
        "--dcm-level",
        "D0",
        "--ecm-level",
        "E0",
        "--ecm-footprint-scale",
        "1.5",
        "--period",
        f"{arguments.period:.17g}",
        "--steps",
        str(arguments.steps),
        "--ecm-backend",
        "fenicsx",
    ]
    initializer_record = run_initializer(
        initializer_command, output_path / "initializer_process.json"
    )
    if int(initializer_record["returncode"]) != 0:
        failure = {
            "schema_version": (
                f"efe_node1_n1_2b_{run_label}_warm_start_failure_v01"
            ),
            "status": "failed_initializer",
            "initializer_process": str(output_path / "initializer_process.json"),
            "passed": False,
        }
        (output_path / "failure_summary.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise RuntimeError(f"{run_label} periodic initializer failed")

    initializer_summary = json.loads(
        (staging_path / "summary.json").read_text(encoding="utf-8")
    )
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

    fenicsx_backend = FenicsxECMBackend(model.ecm_reference)
    with np.load(source_cycle / "cycle_states.npz") as source_states:
        ecm_history = np.asarray(
            source_states["ecm_vertices"], dtype=np.float64
        ).copy()
    if len(ecm_history) != arguments.steps + 1:
        raise ValueError("source cycle does not match requested step count")

    zero_z = np.zeros(
        (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
    )
    time_step = arguments.period / arguments.steps
    zero_cycle_end = apply_frozen_geometry_cycle(
        model, ecm_history, zero_z, time_step
    )
    cycle_decay = math.exp(
        -model.mu_ve * arguments.period / (2.0 * model.eta_ve)
    )
    periodic_z = zero_cycle_end / (1.0 - cycle_decay)
    frozen_cycle_end = apply_frozen_geometry_cycle(
        model, ecm_history, periodic_z, time_step
    )
    frozen_periodicity_residual = relative_difference(
        periodic_z, frozen_cycle_end
    )

    coordinates = build_exact_volume_coordinates(model)
    variable_count = len(coordinates.free_indices)
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    staging_checkpoint = staging_path / "periodic_warm_start_checkpoint.npz"
    variables, candidate_internal, contact_multipliers = load_checkpoint(
        staging_checkpoint,
        model,
        variable_count,
        contact_count,
    )
    candidate_internal_difference = relative_difference(
        periodic_z, candidate_internal
    )
    phase_zero_sample, _ = record_sample(
        model,
        variables,
        candidate_internal,
        cycle_index=arguments.first_cycle_index,
        step_index=0,
        steps_per_cycle=arguments.steps,
        time_value=(arguments.first_cycle_index - 1) * arguments.period,
        activation=0.0,
        activation_rate=0.0,
        coupling_iterations=0,
        coupling_residual=0.0,
        coupling_tolerance=1.0e-4,
        dissipation_step=0.0,
        cumulative_dissipation=0.0,
        solve_seconds=0.0,
        ecm_backend=fenicsx_backend.energy_force,
    )
    warm_start_metrics = PeriodicWarmStartMetrics(
        frozen_periodicity_residual=frozen_periodicity_residual,
        candidate_internal_relative_difference=candidate_internal_difference,
        normalized_kkt_residual=float(
            phase_zero_sample["normalized_kkt_residual"]
        ),
        volume_constraint_residual=float(
            phase_zero_sample["volume_constraint_residual"]
        ),
        minimum_ecm_jacobian=float(
            phase_zero_sample["minimum_ecm_jacobian"]
        ),
        minimum_gap=float(phase_zero_sample["minimum_gap"]),
        minimum_myocyte_face_area_ratio=float(
            phase_zero_sample["minimum_myocyte_face_area_ratio"]
        ),
        minimum_endocardial_face_area_ratio=float(
            phase_zero_sample["minimum_endocardial_face_area_ratio"]
        ),
        internal_symmetry_residual=float(
            phase_zero_sample["internal_symmetry_residual"]
        ),
        internal_trace_residual=float(
            phase_zero_sample["internal_trace_residual"]
        ),
    )
    parent_audit = audit_periodic_warm_start(warm_start_metrics)
    initializer_passed = bool(initializer_summary["passed"])
    passed_before_commit = bool(
        initializer_passed
        and parent_audit["passed"]
        and bool(phase_zero_sample["passed"])
    )
    audit_record = {
        "schema_version": (
            f"efe_node1_n1_2b_{run_label}_warm_start_audit_v01"
        ),
        "authorization": arguments.authorization,
        "source_cycle_directory": str(source_cycle),
        "source_fingerprints": {
            str(path.relative_to(ROOT)): file_sha256(path)
            for path in (
                source_cycle / "cycle_states.npz",
                source_cycle / "cycle_timeseries.csv",
                source_cycle / "cycle_end_checkpoint.npz",
                WARM_DRIVER,
                INITIALIZER,
                TRANSACTION_MODULE,
                PERIODIC_RUNNER,
            )
        },
        "initializer_summary": initializer_summary,
        "staging_checkpoint": str(staging_checkpoint),
        "staging_checkpoint_digest": checkpoint_array_digest(
            variables, candidate_internal, contact_multipliers
        ),
        "cycle_decay": cycle_decay,
        "zero_cycle_end_internal_z_norm": float(np.linalg.norm(zero_cycle_end)),
        "periodic_internal_z_norm": float(np.linalg.norm(periodic_z)),
        "parent_audit": parent_audit,
        "phase_zero_sample": phase_zero_sample,
        "passed_before_commit": passed_before_commit,
    }
    (output_path / "warm_start_audit.json").write_text(
        json.dumps(audit_record, indent=2), encoding="utf-8"
    )
    if not passed_before_commit:
        failure = {
            "schema_version": (
                f"efe_node1_n1_2b_{run_label}_warm_start_failure_v01"
            ),
            "status": "failed_parent_warm_start_gate",
            "audit": str(output_path / "warm_start_audit.json"),
            "passed": False,
        }
        (output_path / "failure_summary.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise RuntimeError(
            f"{run_label} periodic warm start failed parent gate"
        )

    commit = write_checkpoint_exclusive(
        output_path / "periodic_warm_start_checkpoint.npz",
        variables=variables,
        internal_z=candidate_internal,
        contact_multipliers=contact_multipliers,
    )
    report = {
        "schema_version": (
            f"efe_node1_n1_2b_{run_label}_reperiodized_warm_start_v01"
        ),
        "status": f"passed_{run_label}_reperiodized_warm_start",
        "authorization": arguments.authorization,
        "source_cycle_directory": str(source_cycle),
        "steps_per_cycle": arguments.steps,
        "period": arguments.period,
        "cycle_decay": cycle_decay,
        "frozen_geometry_periodicity_residual": frozen_periodicity_residual,
        "candidate_internal_relative_difference": candidate_internal_difference,
        "phase_zero_sample": phase_zero_sample,
        "parent_audit": parent_audit,
        "commit": commit,
        "ecm_backend_diagnostics": fenicsx_backend.diagnostics(),
        "passed": True,
        "evidence_boundary": (
            "This accepted state is an analytically re-periodized SLS warm "
            "start under the frozen source-cycle ECM geometry. It is not cycle-"
            "stability evidence; two consecutive fully coupled transactional "
            "cycles remain required."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
