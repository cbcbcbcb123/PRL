from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
SCRIPTS_DIRECTORY = str(ROOT / "scripts")
for directory in (SOURCE_DIRECTORY, SCRIPTS_DIRECTORY):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from hybrid.efe_step_transaction import file_sha256  # noqa: E402
from hybrid.efe_time_refinement import validate_steps_per_cycle  # noqa: E402
import run_efe_node1_n1_2b_r3_transactional_cycle_v01 as engine  # noqa: E402


DEFAULT_INPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2c_t32_warm_start_v01_20260826"
    / "periodic_warm_start_checkpoint.npz"
)
DEFAULT_PREVIOUS_CYCLE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820"
    / "cycle_08"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2c_t32_transactional_cycle_v01_20260826"
)
AUTHORIZATION = (
    "project_control/efe_node1_n1_2c_p0_p2_authorization_decision_v01.md"
)
WRAPPER = Path(__file__).resolve()
REFINEMENT_MODULE = ROOT / "src/hybrid/efe_time_refinement.py"
TARGET_STEPS = 32


def relative_name(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def count_passed_transactions(inner_output: Path) -> int:
    count = 0
    for cycle_index in (1, 2):
        cycle_path = inner_output / f"cycle_{cycle_index:02d}"
        for step_index in range(1, TARGET_STEPS + 1):
            summary_path = (
                cycle_path
                / f"step_{step_index:03d}"
                / "transaction_summary.json"
            )
            transaction = json.loads(summary_path.read_text(encoding="utf-8"))
            if not bool(transaction.get("passed")):
                raise RuntimeError(f"transaction did not pass: {summary_path}")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--previous-cycle-directory", type=Path, default=DEFAULT_PREVIOUS_CYCLE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--authorization", default=AUTHORIZATION)
    arguments = parser.parse_args()

    validate_steps_per_cycle(TARGET_STEPS)
    input_path = arguments.input.resolve()
    previous_cycle = arguments.previous_cycle_directory.resolve()
    output_path = arguments.output.resolve()
    if output_path.exists():
        raise FileExistsError(f"T32 cycle output already exists: {output_path}")
    if not input_path.is_file():
        raise FileNotFoundError(f"T32 warm checkpoint is missing: {input_path}")
    if not (previous_cycle / "cycle_timeseries.csv").is_file():
        raise FileNotFoundError("T16 comparison cycle is incomplete")

    output_path.mkdir(parents=True)
    inner_output = output_path / "transaction_engine"
    started = time.perf_counter()
    base_parent_source_set = tuple(engine.PARENT_SOURCE_SET)
    engine.STEPS_PER_CYCLE = TARGET_STEPS
    engine.PARENT_SOURCE_SET = (
        WRAPPER,
        REFINEMENT_MODULE,
        *base_parent_source_set,
    )
    original_argv = list(sys.argv)
    sys.argv = [
        str(Path(engine.__file__).resolve()),
        "--input",
        str(input_path),
        "--previous-cycle-directory",
        str(previous_cycle),
        "--output",
        str(inner_output),
        "--first-cycle-index",
        "1",
        "--run-label",
        "r5",
        "--authorization",
        arguments.authorization,
    ]
    try:
        engine.main()
    except Exception as error:
        failure = {
            "schema_version": "efe_node1_n1_2c_t32_transactional_failure_v01",
            "status": "failed_inner_transaction_engine",
            "authorization": arguments.authorization,
            "error_type": type(error).__name__,
            "error": str(error),
            "inner_output": str(inner_output),
            "passed": False,
        }
        (output_path / "failure_summary.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise
    finally:
        sys.argv = original_argv

    inner_summary_path = inner_output / "summary.json"
    inner_summary = json.loads(inner_summary_path.read_text(encoding="utf-8"))
    if int(inner_summary.get("steps_per_cycle", -1)) != TARGET_STEPS:
        raise RuntimeError("inner transaction engine did not execute T32")
    if list(inner_summary.get("target_cycles", ())) != [1, 2]:
        raise RuntimeError("inner transaction engine did not execute two cycles")
    passed_transactions = count_passed_transactions(inner_output)
    if passed_transactions != 2 * TARGET_STEPS:
        raise RuntimeError("T32 accepted transaction count is incomplete")
    if int(inner_summary.get("accepted_transaction_count", -1)) != passed_transactions:
        raise RuntimeError("inner accepted transaction count does not match files")
    if not bool(inner_summary.get("all_worker_process_ids_unique")):
        raise RuntimeError("T32 transaction workers were not process isolated")

    report = {
        "schema_version": "efe_node1_n1_2c_t32_transactional_cycle_v01",
        "status": inner_summary["status"],
        "authorization": arguments.authorization,
        "input_checkpoint": str(input_path),
        "previous_t16_cycle_directory": str(previous_cycle),
        "inner_engine_output": str(inner_output),
        "inner_engine_summary": str(inner_summary_path),
        "inner_engine_summary_sha256": file_sha256(inner_summary_path),
        "runtime_overrides": {
            "steps_per_cycle": TARGET_STEPS,
            "parent_source_set_prepended": [
                relative_name(WRAPPER),
                relative_name(REFINEMENT_MODULE),
            ],
            "unchanged_engine_schema_label": "r5",
            "console_step_denominator_note": (
                "The inherited progress-only console string prints /16; all "
                "worker commands, phase records, accepted files, and summaries "
                "use the audited runtime value 32."
            ),
        },
        "source_fingerprints": {
            relative_name(path): file_sha256(path)
            for path in (WRAPPER, REFINEMENT_MODULE, Path(engine.__file__).resolve())
        },
        "steps_per_cycle": TARGET_STEPS,
        "time_step": 1.0 / TARGET_STEPS,
        "target_cycles": [1, 2],
        "accepted_transaction_count": passed_transactions,
        "all_worker_process_ids_unique": inner_summary[
            "all_worker_process_ids_unique"
        ],
        "cycle_summaries": inner_summary["cycle_summaries"],
        "elapsed_seconds": time.perf_counter() - started,
        "completed": True,
        "passed": bool(inner_summary["passed"]),
        "evidence_boundary": (
            "This result tests within-level T32 cycle stability and supplies a "
            "T16-to-T32 preview only. It does not establish formal temporal or "
            "spatial convergence and stops at the T32 Human Gate."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
