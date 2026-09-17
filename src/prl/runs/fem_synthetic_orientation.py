"""Bounded runner for the F1-S synthetic long-axis sensitivity gate."""

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
)
from prl.fem.synthetic_orientation import (
    CONDITIONS,
    MAX_OFFSET_DEGREES,
    PATCH_BANDS,
    PATCH_COUNT,
    PATCH_SECTORS,
    RANDOM_SEED,
    paired_sensitivity,
    solve_orientation_cycle,
)
from prl.storage import evaluate_storage, scan_workspace


RESULT = Path("results/ventricle_fem/f1s_synthetic_orientation_v01_20260916")
CONTRACT = Path(
    "project_control/ventricle_fem_synthetic_orientation_sensitivity_contract_v01.md"
)
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


def _save_case(path: Path, result: dict[str, Any]) -> None:
    model = result["model"]
    base = model.base
    np.savez_compressed(
        path,
        coordinates=base.coordinates,
        cells=base.cells,
        cell_layers=base.cell_layers,
        reference_areas=base.areas,
        inner_nodes=base.inner_nodes,
        outer_nodes=base.outer_nodes,
        patch_ids=model.patch_ids,
        patch_offsets_degrees=model.patch_offsets_degrees,
        orientation_angles=model.orientation_angles,
        active_strain_unit=model.active_strain_unit,
        phases=result["phases"],
        activation=result["activation"],
        displacements=result["displacements"],
        multipliers=result["multipliers"],
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


def _case_summary(result: dict[str, Any]) -> dict[str, Any]:
    base = result["model"].base
    peak = int(result["peak_index"])
    return {
        "nodes": int(len(base.coordinates)),
        "triangles": int(len(base.cells)),
        "states": int(len(result["phases"])),
        "degrees_of_freedom": int(2 * len(base.coordinates)),
        "peak_phase": float(result["phases"][peak]),
        "peak_activation": float(result["activation"][peak]),
        "peak_lumen_fraction_change": float(result["lumen_fraction_change"][peak]),
        "peak_outer_fraction_change": float(result["outer_fraction_change"][peak]),
        "maximum_abs_strain": float(result["maximum_abs_strain"]),
        "maximum_equivalent_stress": float(result["maximum_equivalent_stress"]),
        "pressure_range": result["pressure_range"],
        "minimum_deformed_triangle_area": float(np.min(result["minimum_triangle_area"])),
        "maximum_backward_residual": float(result["maximum_backward_residual"]),
        "maximum_constraint_residual": float(result["maximum_constraint_residual"]),
        "factor_seconds": float(result["factor_seconds"]),
        "solve_seconds": float(result["solve_seconds"]),
        "wall_seconds": float(result["wall_seconds"]),
    }


def _write_phase_metrics(path: Path, results: dict[tuple[str, str], dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "level",
                "condition",
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
        for level in ("G0", "G1"):
            for condition in CONDITIONS:
                result = results[(level, condition)]
                for index, phase in enumerate(result["phases"]):
                    writer.writerow(
                        [
                            level,
                            condition,
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


def _write_paired_metrics(path: Path, metrics: dict[str, dict[str, float]]) -> None:
    names = list(metrics["G0"].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "G0", "G1", "absolute_mesh_difference"])
        for name in names:
            coarse = float(metrics["G0"][name])
            fine = float(metrics["G1"][name])
            writer.writerow([name, f"{coarse:.12g}", f"{fine:.12g}", f"{abs(fine-coarse):.12g}"])


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
        "schema_version": "prl.fem_synthetic_orientation_manifest.v1",
        "files": files,
        "file_count_excluding_manifest": len(files),
        "logical_bytes_excluding_manifest": sum(item["bytes"] for item in files),
    }


def _write_index(result_root: Path, status: str) -> None:
    html = f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>F1-S 合成长轴方向场敏感性</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1180px;margin:0 auto;padding:28px;color:#17202a;background:#f6f8fa}}main{{background:white;padding:28px;border-radius:12px}}h1{{margin-top:0}}.badge{{display:inline-block;padding:5px 10px;border-radius:999px;background:#e8f5e9;color:#1b5e20;font-weight:700}}.warning{{border-left:5px solid #c47f17;background:#fff7e6;padding:14px}}img{{max-width:100%;height:auto;border:1px solid #d0d7de;margin:12px 0}}code{{background:#eef1f4;padding:2px 5px}}li{{margin:7px 0}}</style></head>
<body><main><h1>F1-S｜合成长轴方向场敏感性</h1><p><span class=\"badge\">{status}</span></p>
<div class=\"warning\"><b>证据边界：</b>48 个区域是材料赋值斑块，不是显式细胞，也不是实验测得的斑马鱼细胞形态。相位是准静态规定相位，不是生理时间。</div>
<h2>这一步问什么</h2><p>保持几何、材料、主动幅度和边界完全相同，只改变心肌长轴方向场，位移和应力差异能否超过两级网格不确定度。</p>
<h2>模型与真实状态</h2><img src=\"figures/f1s_model_structure.png\" alt=\"模型结构\">
<h2>实际结果与裁决</h2><img src=\"figures/f1s_orientation_sensitivity_result.png\" alt=\"方向敏感性结果\">
<p><a href=\"figures/f1s_orientation_sensitivity.gif\">打开 41 状态并列 GIF</a></p>
<h2>验收证据</h2><ul><li><a href=\"verification.json\">独立验证</a></li><li><a href=\"summary.json\">摘要</a></li><li><a href=\"configuration.json\">配置</a></li><li><a href=\"paired_metrics.csv\">配对指标</a></li><li><a href=\"manifest.json\">文件清单与哈希</a></li></ul>
<h2>下一步但不执行</h2><p>真实细胞图像场仍需从带尺度的膜/核成像中提取；面积、长宽比、生长和 ECM 反馈均未在本阶段运行。</p>
</main></body></html>"""
    (result_root / "index.html").write_text(html, encoding="utf-8")


def run_fem_synthetic_orientation(workspace: Path) -> dict[str, Any]:
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
    raw_root = result_root / "raw"
    raw_root.mkdir()
    _write_json(result_root / "storage_preflight.json", preflight)
    configuration = {
        "schema_version": "prl.fem_synthetic_orientation_configuration.v1",
        "model": "2-D plane-strain conforming three-layer elliptic annulus with myocardial material patches",
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
        "orientation_field": {
            "conditions": list(CONDITIONS),
            "patch_bands": PATCH_BANDS,
            "patch_sectors": PATCH_SECTORS,
            "patch_count": PATCH_COUNT,
            "patch_semantics": "material labels only; not explicit cells or interfaces",
            "random_generator": "NumPy PCG64",
            "seed": RANDOM_SEED,
            "smoothing": "0.50 center + 0.20 left + 0.20 right + 0.10 other band",
            "mean_centering": "arithmetic mean removed",
            "maximum_absolute_offset_degrees": MAX_OFFSET_DEGREES,
            "mechanical_coupling": "orientation of myocardial active eigenstrain only",
        },
        "active_strain": {
            "layer": "myocardium",
            "waveform": "0.5*peak*(1-cos(2*pi*phase))",
            "peak": PEAK_ACTIVATION,
            "magnitude_identical_between_conditions": True,
        },
        "boundaries": {
            "inner": "traction-free; no cavity pressure",
            "outer": "traction-free",
            "gauge": "exact mean-x, mean-y and mean-rotation KKT constraints",
        },
        "levels": {
            label: {"ntheta": level.ntheta, "radial_intervals": list(level.radial_intervals)}
            for label, level in LEVELS.items()
        },
        "phase_count": 41,
        "sensitivity_thresholds": {
            "minimum_G1_relative_displacement_l2": 0.01,
            "minimum_G1_relative_stress_l2": 0.01,
            "effect_to_mesh_difference_ratio_strictly_greater_than": 2.0,
        },
        "resources": {"cpu_threads": 1, "gpu": 0, "automatic_retries": 0},
        "scientific_scope": {
            "measured_cell_shape_field": "not_available",
            "zebrafish_calibration": "not_run",
            "growth": "not_run",
            "ecm_feedback": "not_run",
            "fsi": "not_run",
        },
    }
    _write_json(result_root / "configuration.json", configuration)
    _write_json(result_root / "preregistration.json", configuration)

    source_paths = [
        CONTRACT,
        Path("src/prl/cli.py"),
        Path("src/prl/fem/active_ellipse.py"),
        Path("src/prl/fem/synthetic_orientation.py"),
        Path("src/prl/runs/fem_synthetic_orientation.py"),
        Path("src/prl/verification/fem_synthetic_orientation.py"),
        Path("src/prl/rendering/fem_synthetic_orientation.py"),
        Path("tests/prl/test_fem_synthetic_orientation.py"),
        Path("tests/prl/test_cli.py"),
        Path("tests/prl/test_quality.py"),
        Path("tests/prl/quick_suite_v01.txt"),
    ]
    _write_json(
        result_root / "source_hashes.json",
        {path.as_posix(): _sha256(workspace / path) for path in source_paths},
    )
    (result_root / "commands.md").write_text(
        "# Commands\n\nOfficial run (one call, CPU only):\n\n"
        "```powershell\n"
        "$env:PYTHONPATH='src'\n"
        "$env:OMP_NUM_THREADS='1'\n"
        "$env:OPENBLAS_NUM_THREADS='1'\n"
        "$env:MKL_NUM_THREADS='1'\n"
        "$env:NUMEXPR_NUM_THREADS='1'\n"
        "$env:CUDA_VISIBLE_DEVICES='-1'\n"
        "python -B -X utf8 -m prl run fem-synthetic-orientation --workspace .\n"
        "```\n",
        encoding="utf-8",
    )

    results = {
        (level, condition): solve_orientation_cycle(level, condition, phase_count=41)
        for level in ("G0", "G1")
        for condition in CONDITIONS
    }
    for (level, condition), result in results.items():
        condition_root = raw_root / condition
        condition_root.mkdir(exist_ok=True)
        _save_case(condition_root / f"{level}.npz", result)
    _write_phase_metrics(result_root / "metrics.csv", results)
    paired = {
        level: paired_sensitivity(
            results[(level, "uniform")], results[(level, "synthetic_random")]
        )
        for level in ("G0", "G1")
    }
    _write_paired_metrics(result_root / "paired_metrics.csv", paired)
    cases = {
        level: {
            condition: _case_summary(results[(level, condition)])
            for condition in CONDITIONS
        }
        for level in ("G0", "G1")
    }
    summary = {
        "schema_version": "prl.fem_synthetic_orientation_summary.v1",
        "status": "completed_pending_independent_verification",
        "scope": "synthetic myocardial long-axis field sensitivity; not measured cell geometry",
        "official_stage_invocations": 1,
        "fem_condition_level_solves": 4,
        "cases": cases,
        "paired_sensitivity": paired,
        "scientific_status": {
            "engineering": "pending_verification",
            "synthetic_orientation_sensitivity": "pending_verification",
            "measured_cell_shape_field": "not_run",
            "zebrafish_calibration": "not_run",
            "biological_validation": "not_run",
            "growth": "not_run",
            "ecm_feedback": "not_run",
            "fsi": "not_run",
        },
    }
    _write_json(result_root / "summary.json", summary)

    from prl.rendering.fem_synthetic_orientation import render_fem_synthetic_orientation
    from prl.verification.fem_synthetic_orientation import verify_fem_synthetic_orientation

    verification = verify_fem_synthetic_orientation(result_root, save=True)
    rendering = render_fem_synthetic_orientation(result_root)
    final_status = (
        "passed"
        if verification["status"] == "passed" and rendering["status"] == "passed"
        else "failed"
    )
    summary["status"] = final_status
    summary["scientific_status"] = verification["scientific_gates"]
    summary["verification"] = "verification.json"
    summary["rendering"] = "rendering.json"
    _write_json(result_root / "summary.json", summary)
    (result_root / "README.md").write_text(
        "# F1-S synthetic myocardial orientation-field sensitivity\n\n"
        f"Stage verdict: **{final_status}**.\n\n"
        "The 2 x 24 regions are material-assignment patches, not explicit cells and "
        "not a measured zebrafish cell-shape field. Only the myocardial active-strain "
        "direction differs between the paired conditions.\n\n"
        "Open `index.html` for the model, paired result, animation, and evidence links.\n",
        encoding="utf-8",
    )
    _write_index(result_root, final_status)
    postflight = evaluate_storage(
        scan_workspace(workspace), planned_new_bytes=0, stop_reserve_bytes=STOP_RESERVE_BYTES
    )
    _write_json(result_root / "storage_postflight.json", postflight)
    _write_json(result_root / "manifest.json", _manifest(result_root))
    return {
        "status": final_status,
        "result": str(result_root),
        "verification": verification,
        "rendering": rendering,
        "storage": postflight,
    }
