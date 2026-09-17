"""Create-only 5x5 myocardial crowding run with doubled volume targets."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

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
    TARGET_PLANAR_SCALE,
    generate_heterogeneity,
    prepare_geometry,
    write_box,
    write_heterogeneity,
    write_mesh,
)
from .myocardial_crowded_target_pair import (
    INITIAL_GAP,
    INITIAL_WALL_MARGIN,
    _call,
    _write_json,
    generate_reference_targets,
)


RESULT = Path("results/ventricle_z1/z1_myo_crowded_volume_x2_v01_20260916")
PARENT_RESULT = Path(
    "results/ventricle_z1/z1_myo_crowded_target_pair_v01_20260916"
)
CONTRACT = Path(
    "project_control/ventricle_myocardial_crowded_volume_x2_contract_v01.md"
)
CONDITION = "HETEROGENEOUS_TARGETS_X2_VOLUME"
VOLUME_SCALE = 2.0
AREA_SCALE = VOLUME_SCALE ** (2.0 / 3.0)
MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE = 1.25
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
    "maximum_initial_volume_relative_change",
)


def generate_doubled_reference_targets(
    cells: list[np.ndarray], faces: np.ndarray
) -> list[dict[str, float | int | str]]:
    """Scale the frozen heterogeneous targets while preserving each cell's q."""

    baseline = generate_reference_targets(cells, faces)["HETEROGENEOUS_TARGETS"]
    doubled: list[dict[str, float | int | str]] = []
    for source in baseline:
        target_volume = VOLUME_SCALE * float(source["target_volume"])
        target_area = AREA_SCALE * float(source["target_area_at_target_volume"])
        doubled.append(
            {
                "condition": CONDITION,
                "cell_id": int(source["cell_id"]),
                "initial_volume": float(source["initial_volume"]),
                "initial_area": float(source["initial_area"]),
                "target_volume": target_volume,
                "target_area_at_target_volume": target_area,
                "target_isoperimetric_ratio": float(
                    source["target_isoperimetric_ratio"]
                ),
                "volume_factor": VOLUME_SCALE * float(source["volume_factor"]),
                "area_factor": AREA_SCALE * float(source["area_factor"]),
                "maximum_initial_volume_relative_change": (
                    MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE
                ),
            }
        )
    return doubled


def write_doubled_reference_targets(
    path: Path, records: list[dict[str, float | int | str]]
) -> None:
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: f"{value:.17g}" if isinstance(value, float) else value
                    for key, value in record.items()
                }
            )


def _target_summary(records: list[dict[str, float | int | str]]) -> dict[str, object]:
    volumes = np.asarray([float(row["target_volume"]) for row in records])
    areas = np.asarray(
        [float(row["target_area_at_target_volume"]) for row in records]
    )
    initial_volumes = np.asarray([float(row["initial_volume"]) for row in records])
    ratios = volumes / initial_volumes
    return {
        "condition": CONDITION,
        "cell_count": len(records),
        "global_volume_scale_from_parent": VOLUME_SCALE,
        "global_area_scale_from_parent": AREA_SCALE,
        "target_volume_mean": float(volumes.mean()),
        "target_volume_cv": float(volumes.std() / volumes.mean()),
        "target_area_mean": float(areas.mean()),
        "target_area_cv": float(areas.std() / areas.mean()),
        "target_to_own_initial_volume_minimum": float(ratios.min()),
        "target_to_own_initial_volume_maximum": float(ratios.max()),
        "maximum_initial_volume_relative_change_gate": (
            MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE
        ),
    }


def _source_files(root: Path, parent: Path) -> list[Path]:
    return [
        root / CONTRACT,
        root / SOURCE,
        root / CONTACT_SOURCE,
        root / CONTACT_HEADER,
        Path(__file__).resolve(),
        root / "src/prl/verification/myocardial_crowded_volume_x2.py",
        root / "src/prl/rendering/myocardial_crowded_volume_x2.py",
        root / "src/prl/rendering/cb_plot_unified_style.py",
        parent / "initial_cells.mesh",
        parent / "targets/HETEROGENEOUS_TARGETS.csv",
        parent / "verification.json",
    ]


def _write_source_hashes(root: Path, output: Path, parent: Path) -> None:
    payload: dict[str, str] = {}
    for path in _source_files(root, parent):
        resolved = path.resolve(strict=True)
        payload[resolved.relative_to(root).as_posix()] = hashlib.sha256(
            resolved.read_bytes()
        ).hexdigest()
    _write_json(output / "source_hashes.json", payload)


def _execute_scientific_once(root: Path, output: Path) -> dict[str, object]:
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
    execution = _call(
        root,
        [
            root / EXECUTABLE,
            output / "initial_cells.mesh",
            output / "heterogeneity.csv",
            output / "box_schedule.csv",
            raw_directory / CONDITION,
            REQUESTED_STEP,
            REQUESTED_STEPS,
            SHRINK_STEPS,
            780,
            output / "targets" / f"{CONDITION}.csv",
        ],
        800,
    )
    _write_json(output / f"execution_{CONDITION}.json", execution)
    return finalize_myocardial_crowded_volume_x2(root)


def run_myocardial_crowded_volume_x2(root: Path) -> dict[str, object]:
    """Build once, execute exactly once, then independently verify and render."""

    root = root.resolve(strict=True)
    output = root / RESULT
    parent = root / PARENT_RESULT
    if output.exists():
        return resume_myocardial_crowded_volume_x2_pre_solver(root)
    if not (parent / "verification.json").is_file():
        return {
            "status": "blocked",
            "reason": "retained heterogeneous parent evidence is missing",
            "parent": str(parent),
        }
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
            "purpose": "5x5 myocardial crowding response to doubled heterogeneous volume targets",
            "gpu": False,
            "threads": 1,
            "solver_invocations": 1,
            "automatic_retries": 0,
            "maximum_new_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )
    heterogeneity = generate_heterogeneity()
    cells, faces, box = prepare_geometry(
        root,
        heterogeneity,
        initial_gap=INITIAL_GAP,
        initial_wall_margin=INITIAL_WALL_MARGIN,
        target_planar_scale=TARGET_PLANAR_SCALE,
    )
    if float(box["minimum_adjacent_aabb_gap"]) < INITIAL_GAP - 1.0e-10:
        raise RuntimeError("prepared doubled-target grid does not preserve the frozen gap")
    write_heterogeneity(output / "heterogeneity.csv", heterogeneity)
    write_mesh(output / "initial_cells.mesh", cells, faces)
    write_box(output / "box_schedule.csv", box)
    parent_mesh = parent / "initial_cells.mesh"
    if (output / "initial_cells.mesh").read_bytes() != parent_mesh.read_bytes():
        raise RuntimeError("doubled-target initial mesh differs from the retained parent")

    targets = generate_doubled_reference_targets(cells, faces)
    targets_directory = output / "targets"
    targets_directory.mkdir()
    write_doubled_reference_targets(targets_directory / f"{CONDITION}.csv", targets)
    _write_json(output / "target_summary.json", _target_summary(targets))
    _write_json(
        output / "configuration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-CROWD-VOLUME-X2-A",
            "contract": CONTRACT.as_posix(),
            "parent_result": PARENT_RESULT.as_posix(),
            "condition": CONDITION,
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
            "global_volume_scale_from_parent": VOLUME_SCALE,
            "global_area_scale_from_parent": AREA_SCALE,
            "shape_index_policy": "cellwise_target_isoperimetric_ratio_preserved",
            "target_application_policy": "fixed_from_solver_state_zero_not_growth_time_history",
            "maximum_initial_volume_relative_change": (
                MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE
            ),
            "heterogeneity_semantics": "same_frozen_synthetic_parent_heterogeneity",
            "coordinate_semantics": (
                "algorithmic_loading_and_relaxation_not_physiological_time"
            ),
        },
    )

    _write_source_hashes(root, output, parent)
    return _execute_scientific_once(root, output)


def resume_myocardial_crowded_volume_x2_pre_solver(root: Path) -> dict[str, object]:
    """Resume only a strictly verified preparation failure before any solver call."""

    root = root.resolve(strict=True)
    output = (root / RESULT).resolve(strict=True)
    parent = (root / PARENT_RESULT).resolve(strict=True)
    forbidden = [
        output / "raw",
        output / f"execution_{CONDITION}.json",
        output / "build.json",
        output / "binary.json",
        output / "source_hashes.json",
    ]
    present = [str(path) for path in forbidden if path.exists()]
    if present:
        raise FileExistsError(
            "create-only result is not a pre-solver preparation package: "
            + ", ".join(present)
        )
    ownership = json.loads((output / "ownership.json").read_text(encoding="utf-8"))
    configuration = json.loads(
        (output / "configuration.json").read_text(encoding="utf-8")
    )
    if (
        ownership.get("solver_invocations") != 1
        or ownership.get("automatic_retries") != 0
        or configuration.get("stage") != "Z1-MYO-CROWD-VOLUME-X2-A"
        or configuration.get("condition") != CONDITION
    ):
        raise RuntimeError("pre-solver package ownership or configuration drifted")
    if (output / "initial_cells.mesh").read_bytes() != (
        parent / "initial_cells.mesh"
    ).read_bytes():
        raise RuntimeError("pre-solver initial mesh differs from the retained parent")
    with (output / "targets" / f"{CONDITION}.csv").open(
        newline="", encoding="ascii"
    ) as stream:
        target_rows = list(csv.DictReader(stream))
    if (
        len(target_rows) != 25
        or {row["condition"] for row in target_rows} != {CONDITION}
        or {
            float(row["maximum_initial_volume_relative_change"])
            for row in target_rows
        }
        != {MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE}
    ):
        raise RuntimeError("pre-solver target manifest drifted")
    _write_json(
        output / "pre_solver_recovery.json",
        {
            "status": "passed",
            "reason": "source-hash key normalization failed before build or solver launch",
            "solver_invocations_before_recovery": 0,
            "raw_directory_before_recovery": False,
            "targets_reused_without_regeneration": True,
            "automatic_retries": 0,
        },
    )
    _write_source_hashes(root, output, parent)
    return _execute_scientific_once(root, output)


def finalize_myocardial_crowded_volume_x2(root: Path) -> dict[str, object]:
    """Resume verification/rendering only; never invoke the scientific solver."""

    root = root.resolve(strict=True)
    output = (root / RESULT).resolve(strict=True)
    raw = output / "raw" / CONDITION
    from ..rendering.myocardial_crowded_volume_x2 import (
        render_myocardial_crowded_volume_x2,
    )
    from ..verification.myocardial_crowded_volume_x2 import (
        verify_myocardial_crowded_volume_x2,
    )

    verification = verify_myocardial_crowded_volume_x2(output)
    _write_json(output / "verification.json", verification)
    figure_manifest = output / "figures/figure_manifest.json"
    if figure_manifest.is_file():
        rendering = json.loads(figure_manifest.read_text(encoding="utf-8"))
    elif (raw / "nodes.csv").is_file() and (raw / "state_metrics.csv").is_file():
        try:
            rendering = render_myocardial_crowded_volume_x2(output)
        except Exception as error:
            rendering = {
                "status": "failed",
                "reason": "rendering exception; solver was not rerun",
                "error_type": type(error).__name__,
                "error": str(error),
            }
    else:
        rendering = {
            "status": "not_run",
            "reason": "complete retained solver sequence is required",
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
        "stage": "Z1-MYO-CROWD-VOLUME-X2-A",
        "status": final_status,
        "scientific_scope": "fixed doubled heterogeneous volume-target sensitivity",
        "numerical_saved_state_safety": verification.get(
            "numerical_saved_state_safety", "unknown"
        ),
        "static_equilibrium": verification.get("static_equilibrium", "unknown"),
        "contact_network": verification.get("contact_network", "unknown"),
        "baseline_comparison": verification.get("baseline_comparison", {}),
        "failure_diagnosis": verification.get("failure_diagnosis", {}),
        "biological_validation": "not_run",
        "contraction": "not_run",
        "rendering": rendering,
        "storage": postflight,
    }
    _write_json(output / "summary.json", summary)
    return summary
