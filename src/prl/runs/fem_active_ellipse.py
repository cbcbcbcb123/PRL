"""Bounded official runner for the synthetic active elliptic FEM pilot."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from prl.fem.active_ellipse import (
    ASPECT_X,
    ASPECT_Y,
    LAYER_NAMES,
    LEVELS,
    MATERIALS,
    PEAK_ACTIVATION,
    RADIAL_BOUNDARIES,
    solve_cycle,
)
from prl.storage import evaluate_storage, scan_workspace


RESULT = Path("results/ventricle_fem/f0_active_elliptic_pilot_v01_20260916")
CONTRACT = Path("project_control/ventricle_fem_active_elliptic_pilot_contract_v01.md")
PLANNED_BYTES = 64 * 1024 * 1024
STOP_RESERVE_BYTES = 64 * 1024 * 1024


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _save_level(path: Path, result: dict[str, Any]) -> None:
    model = result["model"]
    np.savez_compressed(
        path,
        coordinates=model.coordinates,
        cells=model.cells,
        cell_layers=model.cell_layers,
        areas=model.areas,
        inner_nodes=model.inner_nodes,
        outer_nodes=model.outer_nodes,
        phases=result["phases"],
        activation=result["activation"],
        displacements=result["displacements"],
        strains=result["strains"],
        stresses=result["stresses"],
        equivalent_stress=result["equivalent_stress"],
        pressure=result["pressure"],
        lumen_area=result["lumen_area"],
        outer_area=result["outer_area"],
        lumen_fraction_change=result["lumen_fraction_change"],
        outer_fraction_change=result["outer_fraction_change"],
        stored_energy=result["stored_energy"],
        minimum_triangle_area=result["minimum_triangle_area"],
    )


def _level_summary(result: dict[str, Any]) -> dict[str, Any]:
    model = result["model"]
    peak = int(result["peak_index"])
    return {
        "nodes": int(len(model.coordinates)),
        "triangles": int(len(model.cells)),
        "states": int(len(result["phases"])),
        "degrees_of_freedom": int(2 * len(model.coordinates)),
        "peak_phase": float(result["phases"][peak]),
        "peak_activation": float(result["activation"][peak]),
        "peak_lumen_fraction_change": float(result["lumen_fraction_change"][peak]),
        "peak_outer_fraction_change": float(result["outer_fraction_change"][peak]),
        "peak_inner_long_span": float(result["peak_inner_long_span"]),
        "peak_inner_short_span": float(result["peak_inner_short_span"]),
        "maximum_abs_strain": float(result["maximum_abs_strain"]),
        "maximum_equivalent_stress": float(result["maximum_equivalent_stress"]),
        "pressure_range": result["pressure_range"],
        "minimum_deformed_triangle_area": float(np.min(result["minimum_triangle_area"])),
        "maximum_backward_residual": float(result["maximum_backward_residual"]),
        "maximum_constraint_residual": float(result["maximum_constraint_residual"]),
        "peak_gauge_multipliers": result["peak_gauge_multipliers"].tolist(),
        "factor_seconds": float(result["factor_seconds"]),
        "solve_seconds": float(result["solve_seconds"]),
        "wall_seconds": float(result["wall_seconds"]),
    }


def _write_metrics(path: Path, result: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "phase",
                "activation",
                "lumen_area",
                "lumen_fraction_change",
                "outer_area",
                "outer_fraction_change",
                "maximum_displacement",
                "maximum_abs_strain",
                "maximum_equivalent_stress",
                "minimum_pressure",
                "maximum_pressure",
                "stored_energy",
                "minimum_triangle_area",
            ]
        )
        for index, phase in enumerate(result["phases"]):
            writer.writerow(
                [
                    f"{phase:.10g}",
                    f"{result['activation'][index]:.10g}",
                    f"{result['lumen_area'][index]:.10g}",
                    f"{result['lumen_fraction_change'][index]:.10g}",
                    f"{result['outer_area'][index]:.10g}",
                    f"{result['outer_fraction_change'][index]:.10g}",
                    f"{np.max(np.linalg.norm(result['displacements'][index], axis=1)):.10g}",
                    f"{np.max(np.abs(result['strains'][index])):.10g}",
                    f"{np.max(result['equivalent_stress'][index]):.10g}",
                    f"{np.min(result['pressure'][index]):.10g}",
                    f"{np.max(result['pressure'][index]):.10g}",
                    f"{result['stored_energy'][index]:.10g}",
                    f"{result['minimum_triangle_area'][index]:.10g}",
                ]
            )


def _manifest(result_root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(result_root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(result_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": "prl.fem_active_ellipse_manifest.v1",
        "files": files,
        "file_count_excluding_manifest": len(files),
        "logical_bytes_excluding_manifest": sum(item["bytes"] for item in files),
    }


def run_fem_active_ellipse(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    result_root = workspace / RESULT
    if result_root.exists():
        raise FileExistsError(f"create-only FEM result already exists: {result_root}")
    contract = workspace / CONTRACT
    if not contract.is_file():
        raise FileNotFoundError(contract)
    preflight = evaluate_storage(
        scan_workspace(workspace),
        planned_new_bytes=PLANNED_BYTES,
        stop_reserve_bytes=STOP_RESERVE_BYTES,
    )
    if not preflight["can_start"]:
        return {"status": "blocked", "reason": "storage admission failed", "storage": preflight}

    result_root.mkdir(parents=True, exist_ok=False)
    raw = result_root / "raw"
    raw.mkdir()
    _write_json(result_root / "storage_preflight.json", preflight)
    configuration = {
        "schema_version": "prl.fem_active_ellipse_configuration.v1",
        "model": "2-D plane-strain, conforming three-layer elliptic annulus",
        "units": "dimensionless synthetic",
        "geometry": {
            "aspect_x": ASPECT_X,
            "aspect_y": ASPECT_Y,
            "radial_boundaries": list(RADIAL_BOUNDARIES),
            "layers_inner_to_outer": list(LAYER_NAMES),
        },
        "materials": {
            name: {"young": MATERIALS[name][0], "poisson": MATERIALS[name][1]}
            for name in LAYER_NAMES
        },
        "active_strain": {
            "layer": "myocardium",
            "direction": "local elliptic tangent",
            "waveform": "0.5*peak*(1-cos(2*pi*phase))",
            "peak": PEAK_ACTIVATION,
        },
        "boundaries": {
            "inner": "traction-free; no cavity pressure",
            "outer": "traction-free",
            "gauge": "exact mean-x, mean-y and mean-rotation KKT constraints",
        },
        "levels": {
            label: {
                "ntheta": level.ntheta,
                "radial_intervals": list(level.radial_intervals),
            }
            for label, level in LEVELS.items()
        },
        "phase_count": 41,
        "resources": {"cpu_threads": 1, "gpu": 0, "automatic_retries": 0},
        "experimental_data": {
            "status": "not_used_for_calibration",
            "reason": "available public stacks lack frozen scale, registration and ventricular segmentation",
            "evidence": "results/ventricle_z0/v01_20260911/data_gaps.md",
        },
    }
    _write_json(result_root / "configuration.json", configuration)
    _write_json(result_root / "preregistration.json", configuration)

    source_paths = [
        CONTRACT,
        Path("src/prl/cli.py"),
        Path("src/prl/fem/active_ellipse.py"),
        Path("src/prl/runs/fem_active_ellipse.py"),
        Path("src/prl/verification/fem_active_ellipse.py"),
        Path("src/prl/rendering/fem_active_ellipse.py"),
        Path("tests/prl/test_fem_active_ellipse.py"),
        Path("tests/prl/test_cli.py"),
        Path("tests/prl/quick_suite_v01.txt"),
        Path("results/ventricle_z0/v01_20260911/data_gaps.md"),
    ]
    _write_json(
        result_root / "source_hashes.json",
        {path.as_posix(): _sha256(workspace / path) for path in source_paths},
    )
    (result_root / "commands.md").write_text(
        "# Commands\n\n"
        "Official run (one call, CPU only):\n\n"
        "```powershell\n"
        "$env:PYTHONPATH='src'\n"
        "$env:OMP_NUM_THREADS='1'\n"
        "$env:OPENBLAS_NUM_THREADS='1'\n"
        "$env:MKL_NUM_THREADS='1'\n"
        "$env:NUMEXPR_NUM_THREADS='1'\n"
        "$env:CUDA_VISIBLE_DEVICES='-1'\n"
        "python -B -X utf8 -m prl run fem-active-ellipse --workspace .\n"
        "```\n",
        encoding="utf-8",
    )

    results = {label: solve_cycle(label, phase_count=41) for label in ("G0", "G1")}
    for label, result in results.items():
        _save_level(raw / f"{label}.npz", result)
    _write_metrics(result_root / "metrics.csv", results["G1"])
    level_summaries = {label: _level_summary(item) for label, item in results.items()}
    mesh_difference = abs(
        level_summaries["G1"]["peak_lumen_fraction_change"]
        - level_summaries["G0"]["peak_lumen_fraction_change"]
    )
    summary = {
        "schema_version": "prl.fem_active_ellipse_summary.v1",
        "status": "completed_pending_independent_verification",
        "scope": "2-D synthetic active elliptic three-layer FEM engineering feasibility",
        "official_stage_invocations": 1,
        "fem_level_solves": 2,
        "levels": level_summaries,
        "mesh_peak_lumen_change_absolute_difference": mesh_difference,
        "maximum_backward_residual": max(
            item["maximum_backward_residual"] for item in level_summaries.values()
        ),
        "maximum_constraint_residual": max(
            item["maximum_constraint_residual"] for item in level_summaries.values()
        ),
        "scientific_status": {
            "fem_engineering_feasibility": "pending_verification",
            "zebrafish_calibration": "not_run",
            "biological_validation": "not_run",
            "fsi": "not_run",
            "dcm_comparison": "not_run",
        },
    }
    _write_json(result_root / "summary.json", summary)

    from prl.rendering.fem_active_ellipse import render_fem_active_ellipse
    from prl.verification.fem_active_ellipse import verify_fem_active_ellipse

    verification = verify_fem_active_ellipse(result_root, save=True)
    rendering = render_fem_active_ellipse(result_root)
    summary["status"] = verification["status"]
    summary["scientific_status"]["fem_engineering_feasibility"] = verification["status"]
    summary["verification"] = "verification.json"
    summary["rendering"] = "rendering.json"
    _write_json(result_root / "summary.json", summary)
    (result_root / "README.md").write_text(
        "# F0 active elliptic FEM pilot\n\n"
        f"Engineering verdict: **{verification['status']}**.\n\n"
        "This is a dimensionless, two-dimensional, small-strain, quasi-static active "
        "three-layer elliptic ring. It is not calibrated to zebrafish data, has no "
        "cavity pressure or blood flow, and does not establish a DCM advantage.\n\n"
        "See `figures/f0_fem_model_structure.png`, "
        "`figures/f0_fem_engineering_result.png`, and "
        "`figures/f0_fem_active_cycle.gif`.\n",
        encoding="utf-8",
    )
    postflight = evaluate_storage(
        scan_workspace(workspace), planned_new_bytes=0, stop_reserve_bytes=STOP_RESERVE_BYTES
    )
    _write_json(result_root / "storage_postflight.json", postflight)
    _write_json(result_root / "manifest.json", _manifest(result_root))
    return {
        "status": verification["status"] if rendering["status"] == "passed" else "failed",
        "result": str(result_root),
        "verification": verification,
        "rendering": rendering,
        "storage": postflight,
    }
