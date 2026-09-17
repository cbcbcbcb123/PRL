"""Create-only CPU runner for the regular 2x2 DCM load-hold qualification."""

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


RESULT = Path("results/ventricle_z1/z1_regular_2x2_load_hold_v01_20260916")
BUILD = Path("b/myo-mechanics-v01")
EXECUTABLE = (
    BUILD
    / "src/ventricle_simucell3d_m0/Release/prl_myo_regular_patch_relaxation_v01.exe"
)
SOURCE = Path("src/ventricle_simucell3d_m0/myo_crowded_box_relaxation_v01.cpp")
CONTRACT = Path("project_control/ventricle_regular_2x2_load_hold_contract_v01.md")
PARENT_CONTRACT = Path(
    "project_control/ventricle_regular_dcm_fem_common_limit_contract_v01.md"
)
SOURCE_RESULT = Path(
    "results/ventricle_z1/z1_bioform_myo_r_v03_20260913/raw/FULL_M320_DT020"
)
LOAD_LEVELS = (0.00, 0.20, 0.28, 0.34, 0.40)
INITIAL_GAP = 0.14
INITIAL_WALL_MARGIN = 0.45
TARGET_VOLUME = 167.875410364543
TARGET_ISOPERIMETRIC_RATIO = 114.4451078881478
TARGET_AREA = float(np.cbrt(TARGET_ISOPERIMETRIC_RATIO * TARGET_VOLUME**2))
REQUESTED_STEP = 0.25
MAXIMUM_REQUESTED_STEPS = 1200
WALL_SECONDS_PER_LEVEL = 300
STAGE_BUDGET = 192 * MIB
STOP_RESERVE = 64 * MIB


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _environment(root: Path) -> dict[str, str]:
    runtime = root / BUILD / "runtime_tmp"
    runtime.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        OMP_NUM_THREADS="1",
        OMP_DYNAMIC="FALSE",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
        TEMP=str(runtime),
        TMP=str(runtime),
    )
    return environment


def _call(root: Path, command: list[object], timeout: int) -> dict[str, object]:
    normalized = [str(value) for value in command]
    began = time.monotonic()
    try:
        completed = subprocess.run(
            normalized,
            cwd=root,
            env=_environment(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "command": normalized,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": time.monotonic() - began,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": normalized,
            "return_code": None,
            "stdout": str(error.stdout or ""),
            "stderr": str(error.stderr or ""),
            "elapsed_seconds": time.monotonic() - began,
            "status": "failed",
            "reason": "wall timeout; no retry",
        }


def _source_mesh(root: Path) -> tuple[np.ndarray, np.ndarray]:
    with (root / SOURCE_RESULT / "nodes.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = [
            row for row in csv.DictReader(stream) if int(row["snapshot_index"]) == 8
        ]
    rows.sort(key=lambda row: int(row["node_index"]))
    points = np.asarray(
        [[float(row[name]) for name in ("x", "y", "z")] for row in rows],
        dtype=float,
    )
    with (root / SOURCE_RESULT / "faces.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        face_rows = [
            row for row in csv.DictReader(stream) if int(row["snapshot_index"]) == 8
        ]
    face_rows.sort(key=lambda row: int(row["face_local_id"]))
    faces = np.asarray(
        [[int(row[name]) for name in ("n1", "n2", "n3")] for row in face_rows],
        dtype=int,
    )
    if points.shape != (162, 3) or faces.shape != (320, 3):
        raise RuntimeError("retained long-axis source mesh has unexpected dimensions")
    return points, faces


def _mesh_measures(points: np.ndarray, faces: np.ndarray) -> tuple[float, float]:
    triangles = points[faces]
    volume = float(
        np.einsum(
            "ij,ij->i",
            triangles[:, 0],
            np.cross(triangles[:, 1], triangles[:, 2]),
        ).sum()
        / 6.0
    )
    area = float(
        0.5
        * np.linalg.norm(
            np.cross(
                triangles[:, 1] - triangles[:, 0],
                triangles[:, 2] - triangles[:, 0],
            ),
            axis=1,
        ).sum()
    )
    if not (volume > 0.0 and area > 0.0):
        raise RuntimeError("regular-patch mesh is not closed and outward-oriented")
    return volume, area


def _initial_cells(source: np.ndarray) -> list[np.ndarray]:
    centered = source - source.mean(axis=0)
    span = np.ptp(centered, axis=0)
    x_offset = 0.5 * (span[0] + INITIAL_GAP)
    y_offset = 0.5 * (span[1] + INITIAL_GAP)
    return [
        centered + np.asarray((x_sign * x_offset, y_sign * y_offset, 0.0))
        for y_sign in (-1.0, 1.0)
        for x_sign in (-1.0, 1.0)
    ]


def _initial_box(cells: list[np.ndarray]) -> np.ndarray:
    points = np.concatenate(cells)
    lower = points.min(axis=0) - INITIAL_WALL_MARGIN
    upper = points.max(axis=0) + INITIAL_WALL_MARGIN
    return np.asarray(
        (lower[0], upper[0], lower[1], upper[1], lower[2], upper[2]),
        dtype=float,
    )


def _box_at(base: np.ndarray, planar_approach: float) -> np.ndarray:
    result = base.copy()
    for low, high in ((0, 1), (2, 3)):
        result[low] += 0.5 * planar_approach
        result[high] -= 0.5 * planar_approach
    return result


def _write_mesh(path: Path, cells: list[np.ndarray], faces: np.ndarray) -> None:
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(f"{len(cells)}\n")
        for points in cells:
            stream.write(f"{len(points)} {len(faces)}\n")
            np.savetxt(stream, points, fmt="%.17g")
            np.savetxt(stream, faces, fmt="%d")


def _write_heterogeneity(path: Path) -> None:
    columns = (
        "cell_id,row,column,length_scale,width_scale,thickness_scale,"
        "side_wave_amplitude,wave_phase,rotation_deg,jitter_x,jitter_y,"
        "bulk_modulus_factor,surface_tension_factor,area_modulus_factor,"
        "prestress_factor\n"
    )
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(columns)
        for cell_id in range(4):
            row, column = divmod(cell_id, 2)
            stream.write(
                f"{cell_id},{row},{column},1,1,1,0,0,0,0,0,1,1,1,1\n"
            )


def _write_box(path: Path, bounds: np.ndarray) -> None:
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write("state,xmin,xmax,ymin,ymax,zmin,zmax\n")
        values = ",".join(f"{value:.17g}" for value in bounds)
        stream.write(f"initial,{values}\n")
        stream.write(f"target,{values}\n")


def _write_targets(path: Path, cells: list[np.ndarray], faces: np.ndarray) -> None:
    header = (
        "condition,cell_id,initial_volume,initial_area,target_volume,"
        "target_area_at_target_volume,target_isoperimetric_ratio,volume_factor,"
        "area_factor,maximum_initial_volume_relative_change\n"
    )
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(header)
        for cell_id, points in enumerate(cells):
            volume, area = _mesh_measures(points, faces)
            stream.write(
                "REGULAR_2X2_LOAD_HOLD,"
                f"{cell_id},{volume:.17g},{area:.17g},{TARGET_VOLUME:.17g},"
                f"{TARGET_AREA:.17g},{TARGET_ISOPERIMETRIC_RATIO:.17g},"
                f"{TARGET_VOLUME / volume:.17g},{TARGET_AREA / area:.17g},0.02\n"
            )


def _write_control(path: Path) -> None:
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(
            "stage_name,target_start_fraction,target_ramp_steps,contact_maximum_edge,"
            "motion_fraction,bulk_modulus_scale,maximum_backtracks,minimum_trial_gap,"
            "output_budget_bytes\n"
        )
        stream.write(
            "Z1-REGULAR-2X2-LOAD-HOLD-R0B,1,0,0.20,0.02,1,12,1e-8,67108864\n"
        )


def _final_cells(raw: Path) -> list[np.ndarray]:
    with (raw / "nodes.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    final_snapshot = max(int(row["snapshot_index"]) for row in rows)
    result: list[np.ndarray] = []
    for cell_id in range(4):
        selected = sorted(
            (
                row
                for row in rows
                if int(row["snapshot_index"]) == final_snapshot
                and int(row["cell_id"]) == cell_id
            ),
            key=lambda row: int(row["node_index"]),
        )
        points = np.asarray(
            [[float(row[name]) for name in ("x", "y", "z")] for row in selected]
        )
        if points.shape != (162, 3):
            raise RuntimeError("regular-patch final state is incomplete")
        result.append(points)
    return result


def run_regular_2x2_load_hold(root: Path) -> dict[str, object]:
    """Execute each preregistered load level once and stop at the first failed gate."""

    root = root.resolve(strict=True)
    output = root / RESULT
    if output.exists():
        raise FileExistsError(f"create-only: {output}")
    admission = evaluate_storage(
        scan_workspace(root),
        planned_new_bytes=STAGE_BUDGET,
        stop_reserve_bytes=STOP_RESERVE,
    )
    if not admission["can_start"]:
        return {"status": "blocked", "reason": "storage admission", "storage": admission}

    output.mkdir(parents=True)
    inputs = output / "inputs"
    raw_root = output / "raw"
    inputs.mkdir()
    raw_root.mkdir()
    _write_json(
        output / "ownership.json",
        {
            "owner": "Codex",
            "purpose": "regular 2x2 DCM load-hold qualification",
            "threads": 1,
            "gpu": False,
            "automatic_retries": 0,
            "maximum_new_bytes": STAGE_BUDGET,
            "stop_reserve_bytes": STOP_RESERVE,
        },
    )
    _write_json(output / "storage_preflight.json", admission)
    _write_json(
        output / "configuration.json",
        {
            "stage": "Z1-REGULAR-2X2-LOAD-HOLD-R0B",
            "contract": CONTRACT.as_posix(),
            "parent_contract": PARENT_CONTRACT.as_posix(),
            "source_result": SOURCE_RESULT.as_posix(),
            "cell_grid": [2, 2],
            "cell_count": 4,
            "initial_gap": INITIAL_GAP,
            "initial_wall_margin": INITIAL_WALL_MARGIN,
            "planar_approach_levels": list(LOAD_LEVELS),
            "requested_step": REQUESTED_STEP,
            "maximum_requested_steps_per_level": MAXIMUM_REQUESTED_STEPS,
            "wall_seconds_per_level": WALL_SECONDS_PER_LEVEL,
            "target_volume": TARGET_VOLUME,
            "target_isoperimetric_ratio": TARGET_ISOPERIMETRIC_RATIO,
            "shape_stress": 0.060,
            "contraction_enabled": False,
            "heterogeneity_enabled": False,
            "fem_status": "not_run_by_user_instruction",
            "coordinate_semantics": "algorithmic_relaxation_not_physiological_time",
        },
    )

    source_points, faces = _source_mesh(root)
    cells = _initial_cells(source_points)
    base_box = _initial_box(cells)
    _write_heterogeneity(inputs / "heterogeneity.csv")
    _write_control(inputs / "relaxation_control.csv")

    source_files = [
        CONTRACT,
        PARENT_CONTRACT,
        SOURCE,
        Path("src/ventricle_simucell3d_m0/CMakeLists.txt"),
        Path("external/simucell3d/include/contact_models/surface_separation_guard.hpp"),
        Path(__file__).resolve().relative_to(root),
        Path("src/prl/verification/regular_2x2_load_hold.py"),
        Path("src/prl/rendering/regular_2x2_load_hold.py"),
        SOURCE_RESULT / "nodes.csv",
        SOURCE_RESULT / "faces.csv",
    ]
    _write_json(
        output / "source_hashes_before.json",
        {
            path.as_posix(): hashlib.sha256((root / path).read_bytes()).hexdigest()
            for path in source_files
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
            "prl_myo_regular_patch_relaxation_v01",
            "--parallel",
            "1",
        ],
        600,
    )
    _write_json(output / "build.json", build)
    if build["return_code"] != 0:
        return finalize_regular_2x2_load_hold(root)
    _write_json(
        output / "binary.json",
        {
            "path": EXECUTABLE.as_posix(),
            "sha256": hashlib.sha256((root / EXECUTABLE).read_bytes()).hexdigest(),
        },
    )

    executions: list[dict[str, object]] = []
    for level_index, approach in enumerate(LOAD_LEVELS):
        label = f"L{level_index:02d}_A{approach:.2f}".replace(".", "P")
        mesh_path = inputs / f"{label}.mesh"
        box_path = inputs / f"{label}_box.csv"
        target_path = inputs / f"{label}_targets.csv"
        _write_mesh(mesh_path, cells, faces)
        _write_box(box_path, _box_at(base_box, approach))
        _write_targets(target_path, cells, faces)
        raw = raw_root / label
        record = _call(
            root,
            [
                root / EXECUTABLE,
                mesh_path,
                inputs / "heterogeneity.csv",
                box_path,
                raw,
                REQUESTED_STEP,
                MAXIMUM_REQUESTED_STEPS,
                1,
                WALL_SECONDS_PER_LEVEL,
                target_path,
                inputs / "relaxation_control.csv",
            ],
            WALL_SECONDS_PER_LEVEL + 20,
        )
        record.update(
            level_index=level_index,
            planar_approach=approach,
            label=label,
            automatic_retry=False,
        )
        executions.append(record)
        _write_json(output / "execution.json", executions)
        if record["return_code"] != 0 or not (raw / "kernel_metrics.json").is_file():
            break
        kernel = json.loads((raw / "kernel_metrics.json").read_text(encoding="utf-8"))
        record["kernel_static_equilibrium"] = kernel.get("static_equilibrium")
        _write_json(output / "execution.json", executions)
        if kernel.get("static_equilibrium") != "passed":
            break
        cells = _final_cells(raw)
        if sum(path.stat().st_size for path in output.rglob("*") if path.is_file()) > STAGE_BUDGET:
            record["post_level_gate"] = "stage output budget exceeded"
            _write_json(output / "execution.json", executions)
            break

    return finalize_regular_2x2_load_hold(root)


def finalize_regular_2x2_load_hold(root: Path) -> dict[str, object]:
    """Verify and render retained evidence without invoking the solver."""

    root = root.resolve(strict=True)
    output = (root / RESULT).resolve(strict=True)
    from ..rendering.regular_2x2_load_hold import render_regular_2x2_load_hold
    from ..verification.regular_2x2_load_hold import verify_regular_2x2_load_hold

    verification = verify_regular_2x2_load_hold(output)
    _write_json(output / "verification.json", verification)
    try:
        rendering = render_regular_2x2_load_hold(output)
    except Exception as error:
        rendering = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
    _write_json(output / "rendering.json", rendering)
    postflight = evaluate_storage(
        scan_workspace(root), planned_new_bytes=0, stop_reserve_bytes=STOP_RESERVE
    )
    _write_json(output / "storage_postflight.json", postflight)
    return verification


__all__ = [
    "LOAD_LEVELS",
    "RESULT",
    "finalize_regular_2x2_load_hold",
    "run_regular_2x2_load_hold",
]
