from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
SCRIPTS_DIRECTORY = str(ROOT / "scripts")
for directory in (SOURCE_DIRECTORY, SCRIPTS_DIRECTORY):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from hybrid.efe_step_transaction import (  # noqa: E402
    checkpoint_array_digest,
    file_sha256,
    write_checkpoint_exclusive,
)
from hybrid.efe_time_refinement import (  # noqa: E402
    resample_cycle_state_arrays,
    resample_uniform_cycle_history,
    validate_steps_per_cycle,
)


DEFAULT_SOURCE_CYCLE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820"
    / "cycle_08"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2c_t32_warm_start_v01_20260826"
)
AUTHORIZATION = (
    "project_control/efe_node1_n1_2c_p0_p2_authorization_decision_v01.md"
)
BASE_WARM_DRIVER = (
    ROOT / "scripts/run_efe_node1_n1_2b_r4_reperiodized_warm_start_v01.py"
)
REFINEMENT_MODULE = ROOT / "src/hybrid/efe_time_refinement.py"
WRAPPER = Path(__file__).resolve()
TARGET_STEPS = 32
PERIOD = 1.0
PEAK_ACTIVATION = 0.2


def read_cycle_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    if not fields or len(rows) < 2:
        raise ValueError("source cycle time series is incomplete")
    return fields, rows


def resample_cycle_csv(source: Path, target: Path) -> dict[str, object]:
    fields, rows = read_cycle_csv(source)
    source_steps = len(rows) - 1
    validate_steps_per_cycle(source_steps)
    if source_steps >= TARGET_STEPS:
        raise ValueError("N1-2c T32 warm start requires a coarser source cycle")

    numeric_histories: dict[str, np.ndarray] = {}
    passthrough_fields: set[str] = set()
    for field in fields:
        try:
            numeric_histories[field] = np.asarray(
                [float(row[field]) for row in rows], dtype=np.float64
            )
        except (TypeError, ValueError):
            passthrough_fields.add(field)

    refined = {
        field: resample_uniform_cycle_history(
            values, target_steps_per_cycle=TARGET_STEPS
        )
        for field, values in numeric_histories.items()
    }
    source_start_time = float(rows[0]["time"])
    cycle_index = int(round(float(rows[-1]["cycle"])))
    target_rows: list[dict[str, object]] = []
    for step_index in range(TARGET_STEPS + 1):
        phase = step_index / TARGET_STEPS
        angle = 2.0 * math.pi * phase
        record: dict[str, object] = {}
        for field in fields:
            if field in refined:
                record[field] = f"{float(refined[field][step_index]):.17g}"
            elif field == "passed":
                record[field] = "True"
            else:
                record[field] = rows[min(step_index // 2, source_steps)][field]
        record["cycle"] = str(cycle_index)
        record["step"] = str(step_index)
        record["t_over_T"] = f"{phase:.17g}"
        record["time"] = f"{source_start_time + phase * PERIOD:.17g}"
        record["activation"] = f"{0.5 * PEAK_ACTIVATION * (1.0 - math.cos(angle)):.17g}"
        record["activation_rate"] = (
            f"{PEAK_ACTIVATION * math.pi / PERIOD * math.sin(angle):.17g}"
        )
        record["passed"] = "True"
        target_rows.append(record)

    with target.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(target_rows)
    return {
        "source_steps_per_cycle": source_steps,
        "target_steps_per_cycle": TARGET_STEPS,
        "source_row_count": len(rows),
        "target_row_count": len(target_rows),
        "passthrough_fields": sorted(passthrough_fields),
    }


def relative_name(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-cycle-directory", type=Path, default=DEFAULT_SOURCE_CYCLE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--authorization", default=AUTHORIZATION)
    arguments = parser.parse_args()

    source_cycle = arguments.source_cycle_directory.resolve()
    output_path = arguments.output.resolve()
    if output_path.exists():
        raise FileExistsError(f"T32 warm-start output already exists: {output_path}")
    required_source_files = (
        source_cycle / "cycle_states.npz",
        source_cycle / "cycle_timeseries.csv",
        source_cycle / "cycle_end_checkpoint.npz",
        source_cycle / "cycle_summary.json",
    )
    missing = [str(path) for path in required_source_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"source cycle is missing required files: {missing}")

    output_path.mkdir(parents=True)
    resampled_source = output_path / "resampled_source_cycle"
    resampled_source.mkdir()
    inner_output = output_path / "inner_warm_engine"
    started = time.perf_counter()

    with np.load(source_cycle / "cycle_states.npz") as source_archive:
        source_arrays = {
            name: np.asarray(source_archive[name], dtype=np.float64).copy()
            for name in source_archive.files
        }
    refined_arrays = resample_cycle_state_arrays(
        source_arrays, target_steps_per_cycle=TARGET_STEPS
    )
    np.savez_compressed(
        resampled_source / "cycle_states.npz", **refined_arrays
    )

    with np.load(source_cycle / "cycle_end_checkpoint.npz") as source_checkpoint:
        end_variables = np.asarray(source_checkpoint["variables"], dtype=np.float64)
        end_internal = np.asarray(
            source_checkpoint["ecm_internal_z"], dtype=np.float64
        )
        end_multipliers = np.asarray(
            source_checkpoint["contact_multipliers"], dtype=np.float64
        )
    end_commit = write_checkpoint_exclusive(
        resampled_source / "cycle_end_checkpoint.npz",
        variables=end_variables,
        internal_z=end_internal,
        contact_multipliers=end_multipliers,
    )
    csv_audit = resample_cycle_csv(
        source_cycle / "cycle_timeseries.csv",
        resampled_source / "cycle_timeseries.csv",
    )

    common_phase_audit: dict[str, object] = {}
    for name, refined in refined_arrays.items():
        source_array = source_arrays[name]
        exact = bool(np.array_equal(refined[::2], source_array))
        common_phase_audit[name] = {
            "source_shape": list(source_array.shape),
            "target_shape": list(refined.shape),
            "common_source_phases_bitwise_equal": exact,
            "maximum_common_phase_absolute_difference": float(
                np.max(np.abs(refined[::2] - source_array))
            ),
        }
        if not exact:
            raise RuntimeError(f"common phase preservation failed for {name}")

    resampling_summary = {
        "schema_version": "efe_node1_n1_2c_t16_to_t32_resampling_v01",
        "source_cycle_directory": str(source_cycle),
        "target_directory": str(resampled_source),
        "method": "piecewise linear interpolation on the inclusive uniform phase grid",
        "source_steps_per_cycle": 16,
        "target_steps_per_cycle": TARGET_STEPS,
        "common_phase_stride": 2,
        "state_array_audit": common_phase_audit,
        "csv_audit": csv_audit,
        "source_fingerprints": {
            relative_name(path): file_sha256(path) for path in required_source_files
        },
        "resampled_fingerprints": {
            relative_name(path): file_sha256(path)
            for path in (
                resampled_source / "cycle_states.npz",
                resampled_source / "cycle_timeseries.csv",
                resampled_source / "cycle_end_checkpoint.npz",
            )
        },
        "end_checkpoint_commit": end_commit,
        "passed": True,
        "evidence_boundary": (
            "Interpolated intermediate phases initialize the T32 frozen-geometry "
            "warm calculation only; they are not accepted T32 dynamic states."
        ),
    }
    (output_path / "resampling_summary.json").write_text(
        json.dumps(resampling_summary, indent=2), encoding="utf-8"
    )

    command = [
        sys.executable,
        str(BASE_WARM_DRIVER),
        "--source-cycle-directory",
        str(resampled_source),
        "--output",
        str(inner_output),
        "--period",
        f"{PERIOD:.17g}",
        "--steps",
        str(TARGET_STEPS),
        "--run-label",
        "r5",
        "--first-cycle-index",
        "1",
        "--authorization",
        arguments.authorization,
    ]
    process_started = time.perf_counter()
    process = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    process_record = {
        "command": command,
        "returncode": process.returncode,
        "elapsed_seconds": time.perf_counter() - process_started,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    (output_path / "inner_warm_process.json").write_text(
        json.dumps(process_record, indent=2), encoding="utf-8"
    )
    if process.returncode != 0:
        failure = {
            "schema_version": "efe_node1_n1_2c_t32_warm_start_failure_v01",
            "status": "failed_inner_warm_engine",
            "authorization": arguments.authorization,
            "inner_process": str(output_path / "inner_warm_process.json"),
            "passed": False,
        }
        (output_path / "failure_summary.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise RuntimeError("T32 inner warm engine failed")

    inner_summary_path = inner_output / "summary.json"
    inner_summary = json.loads(inner_summary_path.read_text(encoding="utf-8"))
    if not bool(inner_summary.get("passed")):
        raise RuntimeError("T32 inner warm engine did not pass its gate")
    inner_checkpoint = inner_output / "periodic_warm_start_checkpoint.npz"
    with np.load(inner_checkpoint) as checkpoint:
        variables = np.asarray(checkpoint["variables"], dtype=np.float64)
        internal_z = np.asarray(checkpoint["ecm_internal_z"], dtype=np.float64)
        multipliers = np.asarray(
            checkpoint["contact_multipliers"], dtype=np.float64
        )
    root_commit = write_checkpoint_exclusive(
        output_path / "periodic_warm_start_checkpoint.npz",
        variables=variables,
        internal_z=internal_z,
        contact_multipliers=multipliers,
    )
    expected_digest = checkpoint_array_digest(variables, internal_z, multipliers)
    if root_commit["array_digest"] != expected_digest:
        raise RuntimeError("T32 root warm checkpoint digest mismatch")

    report = {
        "schema_version": "efe_node1_n1_2c_t32_warm_start_v01",
        "status": "passed_t32_reperiodized_warm_start",
        "authorization": arguments.authorization,
        "source_cycle_directory": str(source_cycle),
        "steps_per_cycle": TARGET_STEPS,
        "period": PERIOD,
        "resampling_summary": str(output_path / "resampling_summary.json"),
        "inner_engine_summary": str(inner_summary_path),
        "inner_engine_summary_sha256": file_sha256(inner_summary_path),
        "source_fingerprints": {
            relative_name(path): file_sha256(path)
            for path in (WRAPPER, REFINEMENT_MODULE, BASE_WARM_DRIVER)
        },
        "phase_zero_sample": inner_summary["phase_zero_sample"],
        "parent_audit": inner_summary["parent_audit"],
        "commit": root_commit,
        "elapsed_seconds": time.perf_counter() - started,
        "passed": True,
        "evidence_boundary": (
            "This is a T32 frozen-geometry viscoelastic fixed-point warm start. "
            "It is not T32 cycle-stability or time-convergence evidence; two "
            "fully coupled T32 transactional cycles remain required."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
