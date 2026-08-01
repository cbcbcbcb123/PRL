"""Run and persist the X1-D multicell remesh/material-transfer baseline."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--parallel-threads",
        type=int,
        default=min(4, os.cpu_count() or 1),
    )
    parser.add_argument(
        "--environment-label",
        default="unspecified",
    )
    parser.add_argument("--build-type", default="unspecified")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/hybrid/x1_d_multicell_baseline_v01/summary.json"),
    )
    arguments = parser.parse_args()
    if arguments.repetitions < 1:
        parser.error("--repetitions must be positive")
    if arguments.parallel_threads < 1:
        parser.error("--parallel-threads must be positive")
    return arguments


def run_once(
    executable: Path,
    *,
    cells: int,
    operations_per_cell: int,
    threads: int,
    verify_determinism: bool = False,
    operation_pattern: str = "alternating_swap",
) -> dict[str, Any]:
    command = [
        str(executable),
        "--cells",
        str(cells),
        "--operations-per-cell",
        str(operations_per_cell),
        "--threads",
        str(threads),
    ]
    if verify_determinism:
        command.extend(("--verify-determinism", "true"))
    if operation_pattern != "alternating_swap":
        command.extend(("--operation-pattern", operation_pattern))
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    result = json.loads(completed.stdout)
    if result["status"] != "passed" or not result["invariants_verified"]:
        raise RuntimeError(f"benchmark invariant failure: {result}")
    return result


def summarize_scenario(
    executable: Path,
    *,
    name: str,
    cells: int,
    operations_per_cell: int,
    threads: int,
    repetitions: int,
    operation_pattern: str = "alternating_swap",
) -> dict[str, Any]:
    runs = [
        run_once(
            executable,
            cells=cells,
            operations_per_cell=operations_per_cell,
            threads=threads,
            operation_pattern=operation_pattern,
        )
        for _ in range(repetitions)
    ]
    digests = {run["semantic_digest"] for run in runs}
    if len(digests) != 1:
        raise RuntimeError(f"non-deterministic repeated digest in {name}: {digests}")
    return {
        "name": name,
        "cell_count": cells,
        "operations_per_cell": operations_per_cell,
        "operation_pattern": operation_pattern,
        "requested_threads": threads,
        "total_events": cells * operations_per_cell,
        "repetitions": repetitions,
        "median_setup_seconds": statistics.median(run["setup_seconds"] for run in runs),
        "median_remesh_seconds": statistics.median(run["remesh_seconds"] for run in runs),
        "median_events_per_second": statistics.median(
            run["events_per_second"] for run in runs
        ),
        "maximum_peak_rss_kib": max(run["peak_rss_kib"] for run in runs),
        "semantic_digest": runs[0]["semantic_digest"],
        "raw_runs": runs,
    }


def compiler_version() -> str:
    try:
        completed = subprocess.run(
            ["c++", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return completed.stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unavailable"


def main() -> None:
    arguments = parse_args()
    executable = arguments.executable.resolve()
    if not executable.is_file():
        raise SystemExit(f"benchmark executable not found: {executable}")

    parallel_threads = arguments.parallel_threads
    scenario_specs = (
        ("frequency_128x8_serial", 128, 8, 1, "alternating_swap"),
        ("frequency_128x128_serial", 128, 128, 1, "alternating_swap"),
        ("frequency_128x128_parallel", 128, 128, parallel_threads, "alternating_swap"),
        ("scale_1024x32_serial", 1024, 32, 1, "alternating_swap"),
        ("scale_1024x32_parallel", 1024, 32, parallel_threads, "alternating_swap"),
        ("scale_4096x32_parallel", 4096, 32, parallel_threads, "alternating_swap"),
        ("split_merge_1024_serial", 1024, 2, 1, "split_merge"),
        ("split_merge_1024_parallel", 1024, 2, parallel_threads, "split_merge"),
        ("split_merge_4096_parallel", 4096, 2, parallel_threads, "split_merge"),
    )
    scenarios = [
        summarize_scenario(
            executable,
            name=name,
            cells=cells,
            operations_per_cell=operations,
            threads=threads,
            repetitions=arguments.repetitions,
            operation_pattern=operation_pattern,
        )
        for name, cells, operations, threads, operation_pattern in scenario_specs
    ]
    by_name = {scenario["name"]: scenario for scenario in scenarios}

    frequency_serial = by_name["frequency_128x128_serial"]
    frequency_parallel = by_name["frequency_128x128_parallel"]
    scale_serial = by_name["scale_1024x32_serial"]
    scale_parallel = by_name["scale_1024x32_parallel"]
    largest_scale = by_name["scale_4096x32_parallel"]
    split_merge_serial = by_name["split_merge_1024_serial"]
    split_merge_parallel = by_name["split_merge_1024_parallel"]
    largest_split_merge = by_name["split_merge_4096_parallel"]
    if frequency_serial["semantic_digest"] != frequency_parallel["semantic_digest"]:
        raise RuntimeError("frequency serial/parallel semantic digests differ")
    if scale_serial["semantic_digest"] != scale_parallel["semantic_digest"]:
        raise RuntimeError("scale serial/parallel semantic digests differ")
    if split_merge_serial["semantic_digest"] != split_merge_parallel["semantic_digest"]:
        raise RuntimeError("split/merge serial/parallel semantic digests differ")

    determinism = run_once(
        executable,
        cells=128,
        operations_per_cell=32,
        threads=parallel_threads,
        verify_determinism=True,
    )
    if not determinism["determinism_verified"]:
        raise RuntimeError("explicit serial/parallel determinism check did not run")

    incremental_cells = largest_scale["cell_count"] - scale_parallel["cell_count"]
    incremental_rss = (
        largest_scale["maximum_peak_rss_kib"]
        - scale_parallel["maximum_peak_rss_kib"]
    )
    summary = {
        "baseline_id": "PRL-HYBRID-X1-D-MULTICELL-BASELINE-V01",
        "status": "passed",
        "environment": {
            "label": arguments.environment_label,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "parallel_threads": parallel_threads,
            "compiler": compiler_version(),
            "build_type": arguments.build_type,
            "executable": str(executable),
        },
        "method": {
            "timed_region": (
                "real alternating edge swaps or one split/merge pair per cell, plus "
                "synchronous material transfer"
            ),
            "setup_excluded_from_throughput": True,
            "peak_memory_scope": "whole process high-water RSS",
            "repetitions_per_scenario": arguments.repetitions,
            "throughput_statistic": "median",
            "absolute_performance_gate": None,
        },
        "scenarios": scenarios,
        "comparisons": {
            "frequency_parallel_speedup": (
                frequency_parallel["median_events_per_second"]
                / frequency_serial["median_events_per_second"]
            ),
            "scale_parallel_speedup": (
                scale_parallel["median_events_per_second"]
                / scale_serial["median_events_per_second"]
            ),
            "split_merge_parallel_speedup": (
                split_merge_parallel["median_events_per_second"]
                / split_merge_serial["median_events_per_second"]
            ),
            "largest_cell_count": largest_scale["cell_count"],
            "largest_total_events": largest_scale["total_events"],
            "largest_median_events_per_second": largest_scale[
                "median_events_per_second"
            ],
            "largest_maximum_peak_rss_kib": largest_scale["maximum_peak_rss_kib"],
            "largest_split_merge_cell_count": largest_split_merge["cell_count"],
            "largest_split_merge_total_events": largest_split_merge["total_events"],
            "largest_split_merge_median_events_per_second": largest_split_merge[
                "median_events_per_second"
            ],
            "largest_split_merge_maximum_peak_rss_kib": largest_split_merge[
                "maximum_peak_rss_kib"
            ],
            "estimated_incremental_rss_kib_per_cell": incremental_rss / incremental_cells,
            "serial_parallel_digest_match": True,
            "split_merge_serial_parallel_digest_match": True,
        },
        "determinism_check": determinism,
        "claim_guard": (
            "This microbenchmark isolates real cell-surface edge swaps and material-state "
            "transfer on small 8-node cells. It is not a full timestep, contact, active "
            "mechanics, volumetric ECM, flow-coupling, or physiological-scale benchmark."
        ),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
