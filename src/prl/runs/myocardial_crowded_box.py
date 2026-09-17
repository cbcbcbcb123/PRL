"""Create-only single-CPU 5x5 myocardial crowding pilot."""

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


RESULT = Path("results/ventricle_z1/z1_myo_crowded_box_pilot_v01_20260916")
BUILD = Path("b/myo-mechanics-v01")
EXECUTABLE = (
    BUILD
    / "src/ventricle_simucell3d_m0/Release/prl_myo_crowded_box_relaxation_v01.exe"
)
SOURCE = Path("src/ventricle_simucell3d_m0/myo_crowded_box_relaxation_v01.cpp")
CONTACT_SOURCE = Path(
    "external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp"
)
CONTACT_HEADER = Path(
    "external/simucell3d/include/contact_models/contact_node_face_via_spring.hpp"
)
CONTRACT = Path(
    "project_control/ventricle_myocardial_crowded_box_pilot_contract_v01.md"
)
SOURCE_RESULT = Path(
    "results/ventricle_z1/z1_bioform_myo_r_v03_20260913/raw/FULL_M320_DT020"
)
SEED = 20260916
REQUESTED_STEP = 0.02
REQUESTED_STEPS = 240
SHRINK_STEPS = 120
INITIAL_GAP = 0.24
INITIAL_WALL_MARGIN = 0.45
TARGET_PLANAR_SCALE = 0.95


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _normalized(values: np.ndarray) -> np.ndarray:
    return values / values.mean()


def generate_heterogeneity() -> list[dict[str, float | int]]:
    """Generate one deterministic set of cellwise geometry and mechanics inputs."""

    generator = np.random.default_rng(SEED)
    count = 25
    sampled = {
        "length_scale": _normalized(generator.uniform(0.97, 1.03, count)),
        "width_scale": _normalized(generator.uniform(0.96, 1.04, count)),
        "thickness_scale": _normalized(generator.uniform(0.97, 1.03, count)),
        "side_wave_amplitude": generator.uniform(0.012, 0.035, count),
        "wave_phase": generator.uniform(0.0, 2.0 * np.pi, count),
        "rotation_deg": generator.uniform(-3.0, 3.0, count),
        "jitter_x": generator.uniform(-0.08, 0.08, count),
        "jitter_y": generator.uniform(-0.08, 0.08, count),
        "bulk_modulus_factor": _normalized(generator.uniform(0.92, 1.08, count)),
        "surface_tension_factor": _normalized(generator.uniform(0.90, 1.10, count)),
        "area_modulus_factor": _normalized(generator.uniform(0.90, 1.10, count)),
        "prestress_factor": _normalized(generator.uniform(0.90, 1.10, count)),
    }
    result: list[dict[str, float | int]] = []
    for cell_id in range(count):
        result.append(
            {
                "cell_id": cell_id,
                "row": cell_id // 5,
                "column": cell_id % 5,
                **{
                    name: float(values[cell_id])
                    for name, values in sampled.items()
                },
            }
        )
    return result


def _load_source_mesh(root: Path) -> tuple[np.ndarray, np.ndarray]:
    with (root / SOURCE_RESULT / "nodes.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = [
            row
            for row in csv.DictReader(stream)
            if int(row["snapshot_index"]) == 8
        ]
    rows.sort(key=lambda row: int(row["node_index"]))
    points = np.asarray(
        [[float(row[axis]) for axis in ("x", "y", "z")] for row in rows],
        dtype=float,
    )
    with (root / SOURCE_RESULT / "faces.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        face_rows = [
            row
            for row in csv.DictReader(stream)
            if int(row["snapshot_index"]) == 8
        ]
    face_rows.sort(key=lambda row: int(row["face_local_id"]))
    faces = np.asarray(
        [[int(row[key]) for key in ("n1", "n2", "n3")] for row in face_rows],
        dtype=int,
    )
    if points.shape != (162, 3) or faces.shape != (320, 3):
        raise ValueError("frozen myocardial source must contain 162 nodes and 320 faces")
    return points, faces


def _transform_cell(
    source: np.ndarray, record: dict[str, float | int]
) -> np.ndarray:
    centered = source - source.mean(axis=0)
    minimum_x = float(centered[:, 0].min())
    axial_span = float(np.ptp(centered[:, 0]))
    axial_coordinate = np.clip((centered[:, 0] - minimum_x) / axial_span, 0.0, 1.0)
    envelope = np.sin(np.pi * axial_coordinate)
    phase = float(record["wave_phase"])
    amplitude = float(record["side_wave_amplitude"])
    transverse_wave = 1.0 + amplitude * envelope * np.cos(
        2.0 * np.pi * axial_coordinate + phase
    )
    thickness_wave = 1.0 + 0.5 * amplitude * envelope * np.sin(
        2.0 * np.pi * axial_coordinate + phase
    )
    transformed = centered.copy()
    transformed[:, 0] *= float(record["length_scale"])
    transformed[:, 1] *= float(record["width_scale"]) * transverse_wave
    transformed[:, 2] *= float(record["thickness_scale"]) * thickness_wave
    angle = np.deg2rad(float(record["rotation_deg"]))
    cosine = np.cos(angle)
    sine = np.sin(angle)
    rotated = transformed.copy()
    rotated[:, 0] = cosine * transformed[:, 0] - sine * transformed[:, 1]
    rotated[:, 1] = sine * transformed[:, 0] + cosine * transformed[:, 1]
    return rotated


def _axis_centers(
    negative_extents: np.ndarray,
    positive_extents: np.ndarray,
    initial_gap: float,
) -> np.ndarray:
    centers = np.zeros(5, dtype=float)
    for index in range(1, 5):
        centers[index] = (
            centers[index - 1]
            + positive_extents[index - 1]
            + negative_extents[index]
            + initial_gap
        )
    return centers - 0.5 * (centers[0] + centers[-1])


def prepare_geometry(
    root: Path,
    records: list[dict[str, float | int]],
    *,
    initial_gap: float = INITIAL_GAP,
    initial_wall_margin: float = INITIAL_WALL_MARGIN,
    target_planar_scale: float = TARGET_PLANAR_SCALE,
) -> tuple[list[np.ndarray], np.ndarray, dict[str, np.ndarray | float]]:
    """Transform and place cells with a guaranteed AABB gap between grid lines."""

    source, faces = _load_source_mesh(root)
    local_cells = [_transform_cell(source, record) for record in records]
    column_negative = np.zeros(5)
    column_positive = np.zeros(5)
    row_negative = np.zeros(5)
    row_positive = np.zeros(5)
    for points, record in zip(local_cells, records, strict=True):
        column = int(record["column"])
        row = int(record["row"])
        jitter_x = float(record["jitter_x"])
        jitter_y = float(record["jitter_y"])
        column_negative[column] = max(
            column_negative[column], -(float(points[:, 0].min()) + jitter_x)
        )
        column_positive[column] = max(
            column_positive[column], float(points[:, 0].max()) + jitter_x
        )
        row_negative[row] = max(
            row_negative[row], -(float(points[:, 1].min()) + jitter_y)
        )
        row_positive[row] = max(
            row_positive[row], float(points[:, 1].max()) + jitter_y
        )
    if initial_gap <= 0.0 or initial_wall_margin <= 0.0:
        raise ValueError("crowded geometry requires positive gap and wall margin")
    if not 0.0 < target_planar_scale <= 1.0:
        raise ValueError("target planar scale must lie in (0, 1]")
    column_centers = _axis_centers(
        column_negative, column_positive, initial_gap
    )
    row_centers = _axis_centers(row_negative, row_positive, initial_gap)
    placed: list[np.ndarray] = []
    for points, record in zip(local_cells, records, strict=True):
        translated = points.copy()
        translated[:, 0] += (
            column_centers[int(record["column"])] + float(record["jitter_x"])
        )
        translated[:, 1] += (
            row_centers[int(record["row"])] + float(record["jitter_y"])
        )
        placed.append(translated)
    all_points = np.concatenate(placed)
    xy_center = 0.5 * (all_points[:, :2].min(axis=0) + all_points[:, :2].max(axis=0))
    for points in placed:
        points[:, :2] -= xy_center
    all_points = np.concatenate(placed)
    lower = all_points.min(axis=0) - initial_wall_margin
    upper = all_points.max(axis=0) + initial_wall_margin
    initial = np.asarray(
        [lower[0], upper[0], lower[1], upper[1], lower[2], upper[2]],
        dtype=float,
    )
    target = initial.copy()
    for axis in (0, 1):
        low_index = 2 * axis
        high_index = low_index + 1
        center = 0.5 * (initial[low_index] + initial[high_index])
        half = 0.5 * (initial[high_index] - initial[low_index])
        target[low_index] = center - target_planar_scale * half
        target[high_index] = center + target_planar_scale * half
    x_gaps = []
    y_gaps = []
    for row in range(5):
        selected = [placed[row * 5 + column] for column in range(5)]
        x_gaps.extend(
            float(selected[column + 1][:, 0].min() - selected[column][:, 0].max())
            for column in range(4)
        )
    for column in range(5):
        selected = [placed[row * 5 + column] for row in range(5)]
        y_gaps.extend(
            float(selected[row + 1][:, 1].min() - selected[row][:, 1].max())
            for row in range(4)
        )
    return placed, faces, {
        "initial": initial,
        "target": target,
        "minimum_adjacent_aabb_gap": min(x_gaps + y_gaps),
    }


def write_heterogeneity(
    path: Path, records: list[dict[str, float | int]]
) -> None:
    columns = [
        "cell_id",
        "row",
        "column",
        "length_scale",
        "width_scale",
        "thickness_scale",
        "side_wave_amplitude",
        "wave_phase",
        "rotation_deg",
        "jitter_x",
        "jitter_y",
        "bulk_modulus_factor",
        "surface_tension_factor",
        "area_modulus_factor",
        "prestress_factor",
    ]
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def write_mesh(path: Path, cells: list[np.ndarray], faces: np.ndarray) -> None:
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(f"{len(cells)}\n")
        for points in cells:
            stream.write(f"{len(points)} {len(faces)}\n")
            for point in points:
                stream.write(" ".join(f"{value:.17g}" for value in point) + "\n")
            for triangle in faces:
                stream.write(" ".join(str(int(value)) for value in triangle) + "\n")


def write_box(path: Path, box: dict[str, np.ndarray | float]) -> None:
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.writer(stream)
        writer.writerow(["state", "xmin", "xmax", "ymin", "ymax", "zmin", "zmax"])
        for state in ("initial", "target"):
            writer.writerow([state, *[f"{value:.17g}" for value in box[state]]])


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


def run_myocardial_crowded_box(root: Path) -> dict[str, object]:
    """Prepare once, execute once, verify independently, and render true states."""

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
            "purpose": "5x5 myocardial passive crowding in a thin rigid box",
            "gpu": False,
            "threads": 1,
            "automatic_retries": 0,
            "maximum_new_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )
    records = generate_heterogeneity()
    cells, faces, box = prepare_geometry(root, records)
    if float(box["minimum_adjacent_aabb_gap"]) < INITIAL_GAP - 1.0e-10:
        raise RuntimeError("prepared grid does not preserve the frozen positive gap")
    write_heterogeneity(output / "heterogeneity.csv", records)
    write_mesh(output / "initial_cells.mesh", cells, faces)
    write_box(output / "box_schedule.csv", box)
    _write_json(
        output / "configuration.json",
        {
            "schema_version": 1,
            "stage": "Z1-MYO-CROWD-BOX-PILOT-A",
            "contract": CONTRACT.as_posix(),
            "source_result": SOURCE_RESULT.as_posix(),
            "seed": SEED,
            "cell_grid": [5, 5],
            "cell_count": 25,
            "condition": "PASSIVE_CROWDING",
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
            "coordinate_semantics": "algorithmic_loading_and_relaxation_not_physiological_time",
            "heterogeneity_semantics": "quenched_synthetic_sensitivity_not_experimental_calibration",
            "box_semantics": "six_frictionless_rigid_repulsive_planes_transparent_only_in_rendering",
        },
    )

    source_files = [
        CONTRACT,
        SOURCE,
        CONTACT_SOURCE,
        CONTACT_HEADER,
        Path(__file__).resolve().relative_to(root),
        Path("src/prl/verification/myocardial_crowded_box.py"),
        Path("src/prl/rendering/myocardial_crowded_box.py"),
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

    execution = _call(
        root,
        [
            root / EXECUTABLE,
            output / "initial_cells.mesh",
            output / "heterogeneity.csv",
            output / "box_schedule.csv",
            output / "raw",
            REQUESTED_STEP,
            REQUESTED_STEPS,
            SHRINK_STEPS,
            780,
        ],
        800,
    )
    _write_json(output / "execution.json", execution)

    from ..rendering.myocardial_crowded_box import render_myocardial_crowded_box
    from ..verification.myocardial_crowded_box import verify_myocardial_crowded_box

    verification = verify_myocardial_crowded_box(output)
    _write_json(output / "verification.json", verification)
    rendering = (
        render_myocardial_crowded_box(output)
        if (output / "raw/nodes.csv").is_file()
        else {"status": "not_run", "reason": "no retained node states"}
    )
    _write_json(output / "rendering.json", rendering)
    postflight = evaluate_storage(
        scan_workspace(root), planned_new_bytes=0, stop_reserve_bytes=64 * MIB
    )
    _write_json(output / "storage_postflight.json", postflight)
    final_status = verification["status"]
    if not postflight["can_start"]:
        final_status = "blocked"
    summary = {
        "schema_version": 1,
        "stage": "Z1-MYO-CROWD-BOX-PILOT-A",
        "status": final_status,
        "scientific_scope": "exploratory passive 5x5 crowding pilot",
        "static_equilibrium": verification.get("static_equilibrium", "unknown"),
        "biological_validation": "not_run",
        "contraction": "not_run",
        "verification": verification,
        "rendering": rendering,
        "storage": postflight,
    }
    _write_json(output / "summary.json", summary)
    return summary
