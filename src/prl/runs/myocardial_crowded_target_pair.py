"""Create-only paired 5x5 myocardial crowding run with matched target means."""

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
from .myocardial_crowded_box import (
    BUILD,
    CONTACT_HEADER,
    CONTACT_SOURCE,
    EXECUTABLE,
    REQUESTED_STEP,
    REQUESTED_STEPS,
    SHRINK_STEPS,
    SOURCE,
    SOURCE_RESULT,
    TARGET_PLANAR_SCALE,
    generate_heterogeneity,
    prepare_geometry,
    write_box,
    write_heterogeneity,
    write_mesh,
)


RESULT = Path("results/ventricle_z1/z1_myo_crowded_target_pair_v01_20260916")
CONTRACT = Path(
    "project_control/ventricle_myocardial_crowded_target_pair_contract_v01.md"
)
TARGET_SEED = 20260917
INITIAL_GAP = 0.14
INITIAL_WALL_MARGIN = 0.45
CONDITIONS = ("UNIFORM_TARGETS", "HETEROGENEOUS_TARGETS")
TARGET_COLUMNS = (
    "condition",
    "cell_id",
    "initial_volume",
    "initial_area",
    "target_volume",
    "target_area_at_target_volume",
    "target_isoperimetric_ratio",
    "volume_factor",
    "area_factor",
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


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


def _mesh_volume_area(points: np.ndarray, faces: np.ndarray) -> tuple[float, float]:
    triangles = points[faces]
    cross_products = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    area = 0.5 * float(np.linalg.norm(cross_products, axis=1).sum())
    volume = float(
        np.einsum(
            "ij,ij->i",
            triangles[:, 0],
            np.cross(triangles[:, 1], triangles[:, 2]),
        ).sum()
        / 6.0
    )
    if volume <= 0.0 or area <= 0.0:
        raise ValueError("reference-target inputs must be closed positive meshes")
    return volume, area


def _normalize_exact(values: np.ndarray) -> np.ndarray:
    normalized = np.asarray(values, dtype=float) / float(np.mean(values))
    normalized[-1] = float(normalized.size) - float(normalized[:-1].sum())
    if np.any(normalized <= 0.0):
        raise ValueError("normalization produced a nonpositive target factor")
    return normalized


def generate_reference_targets(
    cells: list[np.ndarray], faces: np.ndarray
) -> dict[str, list[dict[str, float | int | str]]]:
    """Create deterministic equal-mean uniform and heterogeneous target lists."""

    measures = [_mesh_volume_area(points, faces) for points in cells]
    initial_volumes = np.asarray([value[0] for value in measures], dtype=float)
    initial_areas = np.asarray([value[1] for value in measures], dtype=float)
    mean_volume = float(initial_volumes.mean())
    mean_area = float(initial_areas.mean())

    generator = np.random.default_rng(TARGET_SEED)
    heterogeneous_volume_factors = _normalize_exact(
        generator.uniform(0.95, 1.05, len(cells))
    )
    surface_residual = generator.uniform(0.98, 1.02, len(cells))
    heterogeneous_area_factors = _normalize_exact(
        heterogeneous_volume_factors ** (2.0 / 3.0) * surface_residual
    )
    factor_sets = {
        "UNIFORM_TARGETS": (np.ones(len(cells)), np.ones(len(cells))),
        "HETEROGENEOUS_TARGETS": (
            heterogeneous_volume_factors,
            heterogeneous_area_factors,
        ),
    }
    result: dict[str, list[dict[str, float | int | str]]] = {}
    for condition, (volume_factors, area_factors) in factor_sets.items():
        records: list[dict[str, float | int | str]] = []
        for cell_id, (initial_volume, initial_area) in enumerate(measures):
            target_volume = mean_volume * float(volume_factors[cell_id])
            target_area = mean_area * float(area_factors[cell_id])
            records.append(
                {
                    "condition": condition,
                    "cell_id": cell_id,
                    "initial_volume": initial_volume,
                    "initial_area": initial_area,
                    "target_volume": target_volume,
                    "target_area_at_target_volume": target_area,
                    "target_isoperimetric_ratio": target_area**3 / target_volume**2,
                    "volume_factor": float(volume_factors[cell_id]),
                    "area_factor": float(area_factors[cell_id]),
                }
            )
        result[condition] = records
    return result


def write_reference_targets(
    path: Path, records: list[dict[str, float | int | str]]
) -> None:
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: (
                        f"{value:.17g}" if isinstance(value, float) else value
                    )
                    for key, value in record.items()
                }
            )


def _target_summary(
    targets: dict[str, list[dict[str, float | int | str]]]
) -> dict[str, object]:
    summary: dict[str, object] = {"seed": TARGET_SEED, "conditions": {}}
    for condition, records in targets.items():
        volumes = np.asarray([float(row["target_volume"]) for row in records])
        areas = np.asarray(
            [float(row["target_area_at_target_volume"]) for row in records]
        )
        summary["conditions"][condition] = {
            "target_volume_mean": float(volumes.mean()),
            "target_volume_sum": float(volumes.sum()),
            "target_volume_cv": float(volumes.std() / volumes.mean()),
            "target_area_mean": float(areas.mean()),
            "target_area_sum": float(areas.sum()),
            "target_area_cv": float(areas.std() / areas.mean()),
        }
    return summary


def run_myocardial_crowded_target_pair(root: Path) -> dict[str, object]:
    """Build once, run both requested conditions once, verify, and render."""

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
            "purpose": "matched 5x5 myocardial crowding target-distribution comparison",
            "gpu": False,
            "threads": 1,
            "solver_invocations": 2,
            "automatic_retries": 0,
            "maximum_new_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )
    records = generate_heterogeneity()
    cells, faces, box = prepare_geometry(
        root,
        records,
        initial_gap=INITIAL_GAP,
        initial_wall_margin=INITIAL_WALL_MARGIN,
        target_planar_scale=TARGET_PLANAR_SCALE,
    )
    if float(box["minimum_adjacent_aabb_gap"]) < INITIAL_GAP - 1.0e-10:
        raise RuntimeError("prepared paired grid does not preserve the frozen gap")
    write_heterogeneity(output / "heterogeneity.csv", records)
    write_mesh(output / "initial_cells.mesh", cells, faces)
    write_box(output / "box_schedule.csv", box)
    targets = generate_reference_targets(cells, faces)
    targets_directory = output / "targets"
    targets_directory.mkdir()
    for condition in CONDITIONS:
        write_reference_targets(
            targets_directory / f"{condition}.csv", targets[condition]
        )
    target_summary = _target_summary(targets)
    _write_json(output / "target_summary.json", target_summary)
    _write_json(
        output / "configuration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-CROWD-TARGET-PAIR-A",
            "contract": CONTRACT.as_posix(),
            "source_result": SOURCE_RESULT.as_posix(),
            "geometry_seed": 20260916,
            "target_seed": TARGET_SEED,
            "conditions": list(CONDITIONS),
            "cell_grid": [5, 5],
            "cell_count": 25,
            "contraction_enabled": False,
            "contraction_strain": 0.0,
            "material_junctions_enabled": False,
            "requested_step": REQUESTED_STEP,
            "requested_steps": REQUESTED_STEPS,
            "shrink_steps": SHRINK_STEPS,
            "snapshot_interval_steps": 30,
            "initial_adjacent_aabb_gap": float(box["minimum_adjacent_aabb_gap"]),
            "initial_wall_margin": INITIAL_WALL_MARGIN,
            "target_planar_scale": TARGET_PLANAR_SCALE,
            "target_semantics": "homeostatic_area_at_target_volume_with_current_volume_two_thirds_scaling",
            "heterogeneity_semantics": "quenched_synthetic_sensitivity_not_experimental_calibration",
            "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physiological_time",
        },
    )

    source_files = [
        CONTRACT,
        SOURCE,
        CONTACT_SOURCE,
        CONTACT_HEADER,
        Path(__file__).resolve().relative_to(root),
        Path("src/prl/verification/myocardial_crowded_target_pair.py"),
        Path("src/prl/rendering/myocardial_crowded_target_pair.py"),
        Path("src/prl/rendering/cb_plot_unified_style.py"),
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
            "prl_myo_crowded_box_relaxation_v01",
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

    raw_directory = output / "raw"
    raw_directory.mkdir()
    executions: dict[str, dict[str, object]] = {}
    for condition in CONDITIONS:
        execution = _call(
            root,
            [
                root / EXECUTABLE,
                output / "initial_cells.mesh",
                output / "heterogeneity.csv",
                output / "box_schedule.csv",
                raw_directory / condition,
                REQUESTED_STEP,
                REQUESTED_STEPS,
                SHRINK_STEPS,
                780,
                targets_directory / f"{condition}.csv",
            ],
            800,
        )
        executions[condition] = execution
        _write_json(output / f"execution_{condition}.json", execution)

    return finalize_myocardial_crowded_target_pair(root)


def finalize_myocardial_crowded_target_pair(root: Path) -> dict[str, object]:
    """Resume verification/rendering only; this function never calls the solver."""

    root = root.resolve(strict=True)
    output = (root / RESULT).resolve(strict=True)
    raw_directory = output / "raw"
    from ..rendering.myocardial_crowded_target_pair import (
        render_myocardial_crowded_target_pair,
    )
    from ..verification.myocardial_crowded_target_pair import (
        verify_myocardial_crowded_target_pair,
    )

    verification = verify_myocardial_crowded_target_pair(output)
    _write_json(output / "verification.json", verification)
    figure_manifest = output / "figures/figure_manifest.json"
    if figure_manifest.is_file():
        rendering = json.loads(figure_manifest.read_text(encoding="utf-8"))
    elif all(
        (raw_directory / condition / "nodes.csv").is_file()
        for condition in CONDITIONS
    ):
        try:
            rendering = render_myocardial_crowded_target_pair(output)
        except Exception as error:  # preserve raw evidence and make the stop explicit
            rendering = {
                "status": "failed",
                "reason": "rendering exception; solver was not rerun",
                "error_type": type(error).__name__,
                "error": str(error),
            }
    else:
        rendering = {
            "status": "not_run",
            "reason": "both complete retained node sequences are required",
        }
    _write_json(output / "rendering.json", rendering)
    postflight = evaluate_storage(
        scan_workspace(root), planned_new_bytes=0, stop_reserve_bytes=64 * MIB
    )
    _write_json(output / "storage_postflight.json", postflight)
    final_status = verification["status"]
    if rendering.get("status") != "passed":
        final_status = "failed"
    if not postflight["can_start"]:
        final_status = "blocked"
    summary = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-TARGET-PAIR-A",
        "status": final_status,
        "scientific_scope": "synthetic matched paired target-distribution sensitivity",
        "condition_status": verification.get("conditions", {}),
        "paired_comparison": verification.get("paired_comparison", {}),
        "biological_validation": "not_run",
        "contraction": "not_run",
        "rendering": rendering,
        "storage": postflight,
    }
    _write_json(output / "summary.json", summary)
    return summary
