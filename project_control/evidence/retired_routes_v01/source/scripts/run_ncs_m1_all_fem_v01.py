#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import scipy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ncs_m1.baseline import (  # noqa: E402
    EPS_REF,
    LEVELS,
    U_REF,
    W_REF,
    build_flat_system,
    build_annulus_system,
    annulus_frequency,
    annulus_reference,
    annulus_reference_gate,
    annulus_rotation_gate,
    annulus_spatial_gate,
    flat_frequency,
    jsonable,
    mirror_gate,
    patch_and_zero_checks,
    run_flat_trajectory,
    run_annulus_trajectory,
    spatial_gate,
    uniform_reference,
    uniform_reference_gate,
)


RUNNER_RELATIVE = "scripts/run_ncs_m1_all_fem_v01.py"
SPEC_RELATIVE = "project_control/ncs_m1_frozen_spec_v01.md"
PLAN_RELATIVE = "project_control/ncs_m1_all_fem_baseline_plan_v01.md"
M0_RELATIVE = "project_control/ncs_m0_report_v01.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_text(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=PROJECT_ROOT, text=True, encoding="utf-8"
    ).strip()


def protocol_summary(result: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "q_harmonic",
        "strain_harmonic",
        "displacement_harmonic",
        "time",
        "alpha",
        "ebar",
        "top_l2",
        "layer_strain",
        "local_values",
        "energy",
        "active_work_steps",
        "dissipation_steps",
        "energy_residual_steps",
        "local_harmonic",
        "layer_strain_harmonic",
        "state_harmonic",
        "layer_polar_strain_harmonic",
        "polar_strain_harmonic",
    }
    return {key: jsonable(value) for key, value in result.items() if key not in excluded}


def save_protocol(stage_directory: Path, protocol_id: str, result: dict[str, Any]) -> None:
    array_keys = [
        key for key, value in result.items()
        if isinstance(value, np.ndarray)
    ]
    np.savez_compressed(
        stage_directory / f"{protocol_id}_data.npz",
        **{key: result[key] for key in array_keys},
    )
    (stage_directory / f"{protocol_id}_summary.json").write_text(
        json.dumps(protocol_summary(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def time_gate_against_reference(
    results: dict[int, dict[str, Any]], reference_value: complex
) -> dict[str, Any]:
    errors = {
        nt: abs(complex(result["ebar_harmonic"]) - reference_value)
        for nt, result in results.items()
    }
    orders = {
        "64_to_128": float(np.log2(errors[64] / errors[128])),
        "128_to_256": float(np.log2(errors[128] / errors[256])),
    }
    error_floor = errors[256] <= 1.0e-7
    passed = errors[256] / EPS_REF <= 1.0e-3 and (
        error_floor or all(1.8 <= value <= 2.2 for value in orders.values())
    )
    return {
        "absolute_errors": errors,
        "orders": orders,
        "error_floor_rule_applied": error_floor,
        "pass": passed,
    }


def run_m1a(output_root: Path) -> int:
    stage_directory = output_root / "m1a"
    if stage_directory.exists():
        raise RuntimeError(f"create-only stage directory already exists: {stage_directory}")
    stage_directory.mkdir(parents=True)
    started = time.perf_counter()
    protocol_results: dict[str, dict[str, Any]] = {}
    systems: dict[tuple[str, str, str], Any] = {}

    def system(level: str, profile: str, orientation: str = "slash"):
        key = (level, profile, orientation)
        if key not in systems:
            systems[key] = build_flat_system(level, profile, orientation)
        return systems[key]

    def execute(protocol_id: str, level: str, profile: str, nt: int, orientation: str = "slash") -> None:
        print(f"START {protocol_id}", flush=True)
        result = run_flat_trajectory(system(level, profile, orientation), nt)
        protocol_results[protocol_id] = result
        save_protocol(stage_directory, protocol_id, result)
        print(
            f"END {protocol_id} wall={result['wall_seconds']:.3f}s cycles={result['cycles']} "
            f"rhs={result['rhs_count']}",
            flush=True,
        )

    for profile in ("U", "H"):
        for level in ("G0", "G1", "G2"):
            execute(f"{profile}-{level}-T256", level, profile, 256)
    for profile in ("U", "H"):
        for nt in (64, 128):
            execute(f"{profile}-G2-T{nt}", "G2", profile, nt)
    for level in ("G1", "G2"):
        execute(f"H-{level}-MIRROR", level, "H", 256, "backslash")

    checks = patch_and_zero_checks()
    (stage_directory / "ZERO_PATCH_summary.json").write_text(
        json.dumps(jsonable(checks), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    frequency_protocols = {
        "ELASTIC": (0.20, False),
        "TAU-FAST": (0.01, True),
        "TAU-SLOW": (10.0, True),
    }
    frequency_gates: dict[str, Any] = {}
    for protocol_id, (tau, maxwell) in frequency_protocols.items():
        print(f"START {protocol_id}", flush=True)
        result = flat_frequency(system("G0", "U"), tau=tau, maxwell=maxwell)
        protocol_results[protocol_id] = result
        save_protocol(stage_directory, protocol_id, result)
        reference = uniform_reference(tau=tau, maxwell=maxwell)
        error = abs(complex(result["ebar_harmonic"]) - reference["ebar_harmonic"]) / max(
            abs(reference["ebar_harmonic"]), EPS_REF
        )
        frequency_gates[protocol_id] = {
            "ebar_error": float(error),
            "maximum_backward_residual": result["maximum_backward_residual"],
            "pass": error <= 1.0e-3 and result["maximum_backward_residual"] <= 1.0e-10,
        }
        print(f"END {protocol_id} wall={result['wall_seconds']:.3f}s", flush=True)

    u_reference = uniform_reference_gate(protocol_results["U-G2-T256"])
    u_time = time_gate_against_reference(
        {nt: protocol_results[f"U-G2-T{nt}"] for nt in (64, 128, 256)},
        uniform_reference()["ebar_harmonic"],
    )
    h_frequency = flat_frequency(system("G2", "H"))
    h_time = time_gate_against_reference(
        {nt: protocol_results[f"H-G2-T{nt}"] for nt in (64, 128, 256)},
        complex(h_frequency["ebar_harmonic"]),
    )
    h_spatial = spatial_gate(
        {level: protocol_results[f"H-{level}-T256"] for level in ("G0", "G1", "G2")}
    )
    mirrors = {
        level: mirror_gate(
            protocol_results[f"H-{level}-T256"],
            protocol_results[f"H-{level}-MIRROR"],
            system(level, "H", "slash"),
            system(level, "H", "backslash"),
        )
        for level in ("G1", "G2")
    }

    time_results = [result for result in protocol_results.values() if result["kind"] == "time_domain"]
    maximum_backward = max(float(item["maximum_backward_residual"]) for item in protocol_results.values())
    maximum_constraint = max(float(item["maximum_constraint_residual"]) for item in protocol_results.values())
    maximum_energy = max(float(item["energy_relative_residual"]) for item in time_results)
    minimum_dissipation = min(float(item["minimum_dissipation"]) for item in time_results)
    maximum_interface = max(
        max(
            float(item["interface_max_force_mismatch"]),
            float(item["interface_max_moment_mismatch"]),
            float(item["interface_max_power_mismatch"]),
        )
        for item in time_results
    )
    maximum_cycle_difference = max(float(item["cycle_difference"]) for item in time_results)
    maximum_strain = max(float(item["max_abs_strain"]) for item in time_results)
    protocol_count = len(protocol_results) + int(checks["protocol_count"])
    protocol_wall = sum(float(item["wall_seconds"]) for item in protocol_results.values()) + float(checks["wall_seconds"])
    max_protocol_wall = max(
        max(float(item["wall_seconds"]) for item in protocol_results.values()),
        float(checks["wall_seconds"]),
    )
    factorization_count = sum(int(item["factorizations"]) for item in protocol_results.values()) + int(checks["factorizations"])
    rhs_count = sum(int(item["rhs_count"]) for item in protocol_results.values()) + int(checks["rhs_count"])

    gates = {
        "zero_patch": {"pass": checks["zero_pass"] and checks["patch_pass"], **checks},
        "linear_algebra": {
            "maximum_backward_residual": maximum_backward,
            "maximum_constraint_residual": maximum_constraint,
            "pass": maximum_backward <= 1.0e-10 and maximum_constraint <= 1.0e-10,
        },
        "uniform_independent_reference": u_reference,
        "time_convergence_U": u_time,
        "time_convergence_H": h_time,
        "spatial_H": h_spatial,
        "mirror": {"levels": mirrors, "pass": all(item["pass"] for item in mirrors.values())},
        "physical_ledger": {
            "maximum_relative_residual": maximum_energy,
            "minimum_dissipation": minimum_dissipation,
            "pass": maximum_energy <= 1.0e-8 and minimum_dissipation >= -1.0e-16,
        },
        "interface": {
            "maximum_normalized_mismatch": maximum_interface,
            "pass": maximum_interface <= 1.0e-8,
        },
        "steady_state_and_assumption": {
            "maximum_cycle_difference": maximum_cycle_difference,
            "maximum_absolute_strain": maximum_strain,
            "pass": maximum_cycle_difference <= 1.0e-6 and maximum_strain <= 0.05,
        },
        "relaxation_limits": {
            "protocols": frequency_gates,
            "pass": all(item["pass"] for item in frequency_gates.values()),
        },
        "budget": {
            "protocol_count": protocol_count,
            "expected_protocol_count": 17,
            "zero_patch_accounting": checks["accounting_note"],
            "protocol_wall_seconds": protocol_wall,
            "maximum_protocol_wall_seconds": max_protocol_wall,
            "factorizations": factorization_count,
            "rhs_count": rhs_count,
            "pass": protocol_count == 17 and protocol_wall <= 1800.0 and max_protocol_wall <= 120.0,
        },
    }
    all_pass = all(bool(item["pass"]) for item in gates.values())
    failed = [name for name, item in gates.items() if not item["pass"]]
    classification = "PASS" if all_pass else (
        "FAIL" if any(name in failed for name in ("zero_patch", "linear_algebra", "mirror", "physical_ledger", "interface", "budget"))
        else "NOT_RESOLVED"
    )
    summary = {
        "schema_version": "ncs_m1_all_fem.v01",
        "stage": "M1a",
        "execution_status": "passed" if all_pass else ("failed" if classification == "FAIL" else "unknown"),
        "scientific_classification": classification,
        "scope": "two_dimensional_planar_three_layer_all_FEM_synthetic_benchmark",
        "method_novelty": "unknown",
        "m1b_authorized_by_gate": all_pass,
        "gates": gates,
        "failed_or_unresolved_gates": failed,
        "ledger": {
            "protocol_count": protocol_count,
            "factorizations": factorization_count,
            "rhs_count": rhs_count,
            "protocol_wall_seconds": protocol_wall,
            "end_to_end_wall_seconds": time.perf_counter() - started,
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "cpu_threads_requested": 1,
            "gpu": False,
            "network_during_formal_run": False,
        },
        "git": {
            "branch": git_text("branch", "--show-current"),
            "head": git_text("rev-parse", "HEAD"),
            "dirty": bool(git_text("status", "--porcelain")),
        },
        "input_hashes": {
            relative: sha256(PROJECT_ROOT / relative)
            for relative in (RUNNER_RELATIVE, SPEC_RELATIVE, PLAN_RELATIVE, M0_RELATIVE)
        },
        "interpretation_boundary": "M1a PASS only validates the frozen planar all-FEM synthetic baseline; it does not establish DCM advantage, event consistency, biological validity, or publication readiness.",
    }
    (stage_directory / "summary.json").write_text(
        json.dumps(jsonable(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (stage_directory / "manifest.json").write_text(
        json.dumps(
            {
                "protocol_ids": [*list(protocol_results), "ZERO", "PATCH"],
                "files": sorted(path.name for path in stage_directory.iterdir()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(jsonable({
        "stage": "M1a",
        "classification": classification,
        "failed_or_unresolved_gates": failed,
        "ledger": summary["ledger"],
    }), ensure_ascii=False), flush=True)
    return 0 if all_pass else 2


def run_m1b(output_root: Path, m1a_summary_override: Path | None = None) -> int:
    m1a_summary_path = m1a_summary_override or (output_root / "m1a" / "summary.json")
    if not m1a_summary_path.is_absolute():
        m1a_summary_path = PROJECT_ROOT / m1a_summary_path
    if not m1a_summary_path.exists():
        raise RuntimeError("M1a summary is missing")
    m1a_summary = json.loads(m1a_summary_path.read_text(encoding="utf-8"))
    if not (
        m1a_summary.get("execution_status") == "passed"
        and m1a_summary.get("m1b_authorized_by_gate") is True
    ):
        raise RuntimeError("M1a gate did not authorize M1b")
    stage_directory = output_root / "m1b"
    if stage_directory.exists():
        raise RuntimeError(f"create-only stage directory already exists: {stage_directory}")
    stage_directory.mkdir(parents=True)
    started = time.perf_counter()
    systems: dict[tuple[str, float], Any] = {}
    results: dict[str, dict[str, Any]] = {}

    def system(level: str, rotation: float = 0.0):
        key = (level, rotation)
        if key not in systems:
            systems[key] = build_annulus_system(level, rotation)
        return systems[key]

    for level in ("G0", "G1", "G2"):
        protocol_id = f"R-{level}-F"
        print(f"START {protocol_id}", flush=True)
        result = annulus_frequency(system(level))
        results[protocol_id] = result
        save_protocol(stage_directory, protocol_id, result)
        print(f"END {protocol_id} wall={result['wall_seconds']:.3f}s", flush=True)

    for nt in (64, 128, 256):
        protocol_id = f"R-G2-T{nt}"
        print(f"START {protocol_id}", flush=True)
        result = run_annulus_trajectory(system("G2"), nt)
        results[protocol_id] = result
        save_protocol(stage_directory, protocol_id, result)
        print(
            f"END {protocol_id} wall={result['wall_seconds']:.3f}s cycles={result['cycles']} rhs={result['rhs_count']}",
            flush=True,
        )

    print("START R-G1-ROT17", flush=True)
    rotated = annulus_frequency(system("G1", 17.0))
    results["R-G1-ROT17"] = rotated
    save_protocol(stage_directory, "R-G1-ROT17", rotated)
    print(f"END R-G1-ROT17 wall={rotated['wall_seconds']:.3f}s", flush=True)

    reference = annulus_reference()
    reference_gate_frequency = annulus_reference_gate(results["R-G2-F"], reference)
    reference_gate_time = annulus_reference_gate(results["R-G2-T256"], reference)
    spatial = annulus_spatial_gate(
        {level: results[f"R-{level}-F"] for level in ("G0", "G1", "G2")}
    )
    rotation = annulus_rotation_gate(results["R-G1-F"], rotated, 17.0)

    def time_gate(readout: str, scale: float) -> dict[str, Any]:
        # Hold the G2 spatial discretization fixed so this gate measures only
        # CN time error. The independent analytic reference is checked in the
        # two separate total-error gates above.
        reference_value = complex(results["R-G2-F"][readout])
        errors = {
            nt: abs(complex(results[f"R-G2-T{nt}"][readout]) - reference_value)
            for nt in (64, 128, 256)
        }
        orders = {
            "64_to_128": float(np.log2(errors[64] / errors[128])),
            "128_to_256": float(np.log2(errors[128] / errors[256])),
        }
        floor_case = errors[256] <= scale * 1.0e-5
        return {
            "absolute_errors": errors,
            "orders": orders,
            "error_floor_rule_applied": floor_case,
            "pass": errors[256] / scale <= 1.0e-3
            and (floor_case or all(1.8 <= value <= 2.2 for value in orders.values())),
        }

    time_convergence = time_gate("inner_radial_harmonic", U_REF)
    time_results = [results[f"R-G2-T{nt}"] for nt in (64, 128, 256)]
    maximum_backward = max(float(item["maximum_backward_residual"]) for item in results.values())
    maximum_constraint = max(float(item["maximum_constraint_residual"]) for item in results.values())
    maximum_energy = max(float(item["energy_relative_residual"]) for item in time_results)
    minimum_dissipation = min(float(item["minimum_dissipation"]) for item in time_results)
    maximum_interface = max(float(item["interface_max_mismatch"]) for item in time_results)
    maximum_cycle = max(float(item["cycle_difference"]) for item in time_results)
    maximum_strain = max(float(item["max_abs_strain"]) for item in time_results)
    protocol_wall = sum(float(item["wall_seconds"]) for item in results.values())
    maximum_protocol_wall = max(float(item["wall_seconds"]) for item in results.values())
    factorizations = sum(int(item["factorizations"]) for item in results.values())
    rhs_count = sum(int(item["rhs_count"]) for item in results.values())
    gates = {
        "linear_algebra": {
            "maximum_backward_residual": maximum_backward,
            "maximum_constraint_residual": maximum_constraint,
            "pass": maximum_backward <= 1.0e-10 and maximum_constraint <= 1.0e-10,
        },
        "independent_reference_frequency": reference_gate_frequency,
        "independent_reference_time": reference_gate_time,
        "time_convergence": time_convergence,
        "spatial": spatial,
        "rotation": rotation,
        "physical_ledger": {
            "maximum_relative_residual": maximum_energy,
            "minimum_dissipation": minimum_dissipation,
            "pass": maximum_energy <= 1.0e-8 and minimum_dissipation >= -1.0e-16,
        },
        "interface": {
            "maximum_normalized_mismatch": maximum_interface,
            "pass": maximum_interface <= 1.0e-8,
        },
        "steady_state_and_assumption": {
            "maximum_cycle_difference": maximum_cycle,
            "maximum_absolute_strain": maximum_strain,
            "pass": maximum_cycle <= 1.0e-6 and maximum_strain <= 0.05,
        },
        "budget": {
            "protocol_count": len(results),
            "protocol_wall_seconds": protocol_wall,
            "maximum_protocol_wall_seconds": maximum_protocol_wall,
            "factorizations": factorizations,
            "rhs_count": rhs_count,
            "pass": len(results) == 7 and protocol_wall <= 900.0 and maximum_protocol_wall <= 120.0,
        },
    }
    all_pass = all(bool(item["pass"]) for item in gates.values())
    failed = [name for name, item in gates.items() if not item["pass"]]
    classification = "PASS" if all_pass else (
        "FAIL" if any(name in failed for name in ("linear_algebra", "rotation", "physical_ledger", "interface", "budget"))
        else "NOT_RESOLVED"
    )
    summary = {
        "schema_version": "ncs_m1_all_fem.v01",
        "stage": "M1b",
        "execution_status": "passed" if all_pass else ("failed" if classification == "FAIL" else "unknown"),
        "scientific_classification": classification,
        "scope": "two_dimensional_plane_strain_three_layer_annulus_synthetic_benchmark",
        "m1_overall_status": "passed" if all_pass else "not_resolved",
        "method_novelty": "unknown",
        "gates": gates,
        "failed_or_unresolved_gates": failed,
        "reference": jsonable(reference),
        "ledger": {
            "protocol_count": len(results),
            "factorizations": factorizations,
            "rhs_count": rhs_count,
            "protocol_wall_seconds": protocol_wall,
            "end_to_end_wall_seconds": time.perf_counter() - started,
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "cpu_threads_requested": 1,
            "gpu": False,
            "network_during_formal_run": False,
        },
        "git": {
            "branch": git_text("branch", "--show-current"),
            "head": git_text("rev-parse", "HEAD"),
            "dirty": bool(git_text("status", "--porcelain")),
        },
        "input_hashes": {
            relative: sha256(PROJECT_ROOT / relative)
            for relative in (RUNNER_RELATIVE, SPEC_RELATIVE, PLAN_RELATIVE, M0_RELATIVE)
        },
        "m1a_summary": {
            "path": str(m1a_summary_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256(m1a_summary_path),
        },
        "interpretation_boundary": "M1 PASS validates only the frozen planar and annular all-FEM synthetic baselines. M2, event consistency, DCM advantage, biological validity, novelty, and publication readiness remain untested or unknown.",
    }
    (stage_directory / "summary.json").write_text(
        json.dumps(jsonable(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (stage_directory / "manifest.json").write_text(
        json.dumps(
            {
                "protocol_ids": list(results),
                "files": sorted(path.name for path in stage_directory.iterdir()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(jsonable({
        "stage": "M1b",
        "classification": classification,
        "failed_or_unresolved_gates": failed,
        "ledger": summary["ledger"],
    }), ensure_ascii=False), flush=True)
    return 0 if all_pass else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("m1a", "m1b"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--m1a-summary", type=Path)
    arguments = parser.parse_args()
    output_root = arguments.output
    if not output_root.is_absolute():
        output_root = PROJECT_ROOT / output_root
    return (
        run_m1a(output_root)
        if arguments.stage == "m1a"
        else run_m1b(output_root, arguments.m1a_summary)
    )


if __name__ == "__main__":
    raise SystemExit(main())
