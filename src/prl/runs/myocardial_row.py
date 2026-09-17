"""Create-only single-CPU run for the heterogeneous five-cell steady row."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from ..storage import MIB, evaluate_storage, scan_workspace


RESULT = Path("results/ventricle_z1/z1_myo_heterogeneous_row_equilibrium_v01_20260916")
BUILD = Path("b/myo-mechanics-v01")
EXECUTABLE = BUILD / "src/ventricle_bioform_myo/Release/prl_ventricle_myo_strip_v01.exe"
SOURCE = Path("src/ventricle_bioform_myo/ventricle_myo_strip_v01.cpp")
CONTRACT = Path("project_control/ventricle_myocardial_heterogeneous_row_equilibrium_contract_v01.md")
SOURCE_RESULT = Path("results/ventricle_z1/z1_bioform_myo_r_v03_20260913/raw/FULL_M320_DT020")
SEED = 20260916
REQUESTED_STEP = 0.02
STEPS_PER_BLOCK = 500
BLOCK_COUNT = 8


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalized(values: np.ndarray) -> np.ndarray:
    return values / values.mean()


def generate_heterogeneity() -> list[dict[str, float | int]]:
    """Draw once, normalize population means, and freeze the five cell records."""

    generator = np.random.default_rng(SEED)
    sampled = {
        "length_scale": _normalized(generator.uniform(0.94, 1.06, 5)),
        "width_scale": _normalized(generator.uniform(0.94, 1.06, 5)),
        "thickness_scale": _normalized(generator.uniform(0.96, 1.04, 5)),
        "side_wave_amplitude": generator.uniform(0.015, 0.045, 5),
        "center_y": generator.uniform(-0.12, 0.12, 5),
        "bulk_modulus_factor": _normalized(generator.uniform(0.92, 1.08, 5)),
        "surface_tension_factor": _normalized(generator.uniform(0.90, 1.10, 5)),
        "area_modulus_factor": _normalized(generator.uniform(0.90, 1.10, 5)),
        "prestress_factor": _normalized(generator.uniform(0.90, 1.10, 5)),
        "wave_phase": generator.uniform(0.0, 2.0 * np.pi, 5),
    }
    return [
        {"cell_id": cell_id, **{name: float(values[cell_id]) for name, values in sampled.items()}}
        for cell_id in range(5)
    ]


def write_heterogeneity(path: Path, records: list[dict[str, float | int]]) -> None:
    columns = [
        "cell_id",
        "length_scale",
        "width_scale",
        "thickness_scale",
        "side_wave_amplitude",
        "center_y",
        "wave_phase",
        "bulk_modulus_factor",
        "surface_tension_factor",
        "area_modulus_factor",
        "prestress_factor",
    ]
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        OMP_NUM_THREADS="1",
        OMP_DYNAMIC="FALSE",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
        CUDA_VISIBLE_DEVICES="",
    )
    return environment


def _call(root: Path, command: list[object], timeout: int) -> dict[str, object]:
    command_text = [str(value) for value in command]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command_text,
            cwd=root,
            env=_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "command": command_text,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": time.monotonic() - started,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": command_text,
            "return_code": None,
            "stdout": str(error.stdout),
            "stderr": str(error.stderr),
            "elapsed_seconds": time.monotonic() - started,
            "status": "failed",
            "reason": "wall timeout; no retry",
        }


def run_myocardial_row(root: Path) -> dict[str, object]:
    """Build once, execute once, verify independently, and render retained states."""

    root = root.resolve(strict=True)
    output = root / RESULT
    if output.exists():
        raise FileExistsError(f"create-only result already exists: {output}")
    admission = evaluate_storage(
        scan_workspace(root), planned_new_bytes=256 * MIB, stop_reserve_bytes=64 * MIB
    )
    if not admission["can_start"]:
        return {"status": "blocked", "reason": "storage admission", "storage": admission}

    output.mkdir(parents=True)
    _write_json(output / "storage_preflight.json", admission)
    _write_json(
        output / "ownership.json",
        {
            "owner": "Codex",
            "purpose": "heterogeneous five-cell myocardial row passive equilibrium",
            "gpu": False,
            "threads": 1,
            "automatic_retries": 0,
            "maximum_new_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )
    heterogeneity = generate_heterogeneity()
    write_heterogeneity(output / "heterogeneity.csv", heterogeneity)
    _write_json(
        output / "configuration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-HETERO-ROW-EQ-A",
            "contract": CONTRACT.as_posix(),
            "source_result": SOURCE_RESULT.as_posix(),
            "seed": SEED,
            "condition": "PASSIVE",
            "boundary_mode": "ISOMETRIC",
            "contraction_strain": 0.0,
            "requested_step": REQUESTED_STEP,
            "blocks": BLOCK_COUNT,
            "steps_per_block": STEPS_PER_BLOCK,
            "hold_steps_per_block": 1,
            "coordinate_semantics": "algorithmic_relaxation_progress_not_physiological_time",
            "heterogeneity_semantics": "quenched_synthetic_sensitivity_not_experimental_calibration",
        },
    )

    source_files = [
        CONTRACT,
        SOURCE,
        Path(__file__).resolve().relative_to(root),
        Path("src/prl/verification/myocardial_row.py"),
        Path("src/prl/rendering/myocardial_row.py"),
        SOURCE_RESULT / "nodes.csv",
        SOURCE_RESULT / "faces.csv",
    ]
    _write_json(
        output / "source_hashes.json",
        {
            item.as_posix(): hashlib.sha256((root / item).read_bytes()).hexdigest()
            for item in source_files
        },
    )

    build = _call(
        root,
        [
            "cmake",
            "--build",
            root / BUILD,
            "--config",
            "Release",
            "--target",
            "prl_ventricle_myo_strip_v01",
            "--parallel",
            "1",
        ],
        600,
    )
    _write_json(output / "build.json", build)
    if build["return_code"] != 0:
        return {"status": "failed", "reason": "build", "result": str(output)}
    _write_json(
        output / "binary.json",
        {
            "path": EXECUTABLE.as_posix(),
            "sha256": hashlib.sha256((root / EXECUTABLE).read_bytes()).hexdigest(),
        },
    )

    execution = _call(
        root,
        [
            root / EXECUTABLE,
            output / "raw",
            "PASSIVE",
            root / SOURCE_RESULT / "nodes.csv",
            root / SOURCE_RESULT / "faces.csv",
            REQUESTED_STEP,
            0.0,
            0,
            STEPS_PER_BLOCK,
            1,
            "ISOMETRIC",
            0.0,
            output / "heterogeneity.csv",
        ],
        600,
    )
    _write_json(output / "execution.json", execution)

    from ..rendering.myocardial_row import render_myocardial_row
    from ..verification.myocardial_row import verify_myocardial_row

    verification = verify_myocardial_row(output)
    _write_json(output / "verification.json", verification)
    rendering = render_myocardial_row(output) if (output / "raw/nodes.csv").is_file() else {
        "status": "not_run",
        "reason": "no retained node states",
    }
    _write_json(output / "rendering.json", rendering)
    postflight = evaluate_storage(scan_workspace(root), planned_new_bytes=0, stop_reserve_bytes=64 * MIB)
    _write_json(output / "storage_postflight.json", postflight)
    final_status = verification["status"]
    if not postflight["can_start"]:
        final_status = "blocked"
    summary = {
        "schema_version": 1,
        "stage": "Z1-MYO-HETERO-ROW-EQ-A",
        "status": final_status,
        "scientific_scope": "synthetic heterogeneous passive-equilibrium qualification",
        "contraction_status": "not_run",
        "verification": verification,
        "rendering": rendering,
        "storage": postflight,
    }
    _write_json(output / "summary.json", summary)
    return summary

