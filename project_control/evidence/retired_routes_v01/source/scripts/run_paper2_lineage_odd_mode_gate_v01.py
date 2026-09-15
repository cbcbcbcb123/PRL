"""Run the frozen Paper 2 lineage odd-mode rank-opening gate.

This runner is intentionally standalone and bounded.  It constructs paired
mirror triangulations without changing the production API, evaluates only the
pre-registered A1 harmonic problem, and writes one create-only JSON record.
It does not implement a DCM division, feedback, fluid mechanics, 3D mechanics,
nonlinearity, parameter scans, or any downstream figure.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
from typing import Any, Iterator


WALL_BUDGET_SECONDS = 60.0
PROCESS_WALL_STARTED = time.perf_counter()
PROCESS_ALARM_AVAILABLE = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
PROCESS_PREVIOUS_ALARM_HANDLER: Any = None


def _process_wall_timeout(_signum: int, _frame: Any) -> None:
    raise TimeoutError("60-second complete-process wall-clock budget exceeded")


if __name__ == "__main__":
    if not PROCESS_ALARM_AVAILABLE:
        raise RuntimeError("hard complete-process wall-clock alarm is unavailable")
    PROCESS_PREVIOUS_ALARM_HANDLER = signal.signal(signal.SIGALRM, _process_wall_timeout)
    signal.setitimer(signal.ITIMER_REAL, WALL_BUDGET_SECONDS)


import numpy as np
import scipy
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg


SCHEMA = "paper2_lineage_odd_mode_gate_v01"
EXPECTED_BASE_COMMIT = "b45650a9e370be138a70acf305b6c3a21e6a7ed2"
EXPECTED_PROJECT_ROOT = Path("/workspace")
EXPECTED_CONTAINER_OUTPUT = Path("/output/summary.json")
LOGICAL_OUTPUT = Path(
    "results/paper2_lineage_odd_mode_gate/v01_20260908/summary.json"
)
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
EXPECTED_PYTHONPATH_PREFIX = (
    "/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:"
    "/usr/local/lib:"
)
RUNNER_PATH = "scripts/run_paper2_lineage_odd_mode_gate_v01.py"
SOURCE_HASHES = {
    "project_control/CURRENT_STATUS.md": (
        "5e648339c743cb227563c63ff61bb689b15d79631cd0f2be3da9d3c4963a9583"
    ),
    "project_control/prl_independent_theory_mainline_plan_v04.md": (
        "b41fb16926375f31ae7b457575a21f61f806e3e2a680fc0f43d1457411615d20"
    ),
    "results/paper2_science_pilot/v01_20260905/science_brief.md": (
        "5ac3a1c017e1fe288e3229f7ff0e96cfd45717985f1f52d3c3c9f74efd8d9f86"
    ),
    "src/paper2_hybrid/config.py": (
        "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe"
    ),
    "src/paper2_hybrid/model.py": (
        "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800"
    ),
    "src/paper2_hybrid/numerics.py": (
        "620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4"
    ),
    "scripts/run_paper2_division_dipole_gate_v01.py": (
        "aa59b306377e50352c4b3a3e1b1b0c36b76aae2d42698031e63ca3a67fb291b2"
    ),
}

SPATIAL_LEVELS = ("S2", "S3")
ORIENTATIONS = ("slash", "backslash")
STEPS_PER_CYCLE = 128
FOOTPRINT_COUNT = 8
LEFT_FOOTPRINT = 3
RIGHT_FOOTPRINT = 4
DEPTH_BAND_COUNT = 8
ALPHA_0 = 0.10
FD_AMPLITUDES = (1.0e-4, 5.0e-5)
STRAIN_WEIGHT = np.diag((1.0, 1.0, 0.5))

SOLVE_BUDGET_SECONDS = 30.0
RELATIVE_RESIDUAL_TOLERANCE = 1.0e-7
BACKWARD_ERROR_TOLERANCE = 1.0e-12
STRAIN_NEAR_ZERO_TOLERANCE = 1.0e-10
FD_NEAR_ZERO_TOLERANCE = 1.0e-10
FD_RELATIVE_TOLERANCE = 1.0e-2
FD_ABSOLUTE_TOLERANCE = 1.0e-8
MIRROR_ABSOLUTE_TOLERANCE = 1.0e-10
MIRROR_RELATIVE_TOLERANCE = 1.0e-8
CROSS_GRID_RELATIVE_TOLERANCE = 5.0e-2
NOISE_MULTIPLIER = 100.0
ROBUST_NO_GO_TOLERANCE = 1.0e-8


class NearZeroReadout(RuntimeError):
    """The preregistered RMS derivative is undefined in an included cell."""

    def __init__(self, record: dict[str, Any]):
        super().__init__("included ECM cell has preregistered RMS at or below 1e-10")
        self.record = record


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_hash(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(str(value.shape).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(np.real(value)), "imag": float(np.imag(value))}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite floating-point value in JSON payload")
        return number
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, complex):
        return _complex_record(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _first_existing_text(paths: tuple[Path, ...]) -> tuple[str | None, str | None]:
    for path in paths:
        if path.is_file():
            return path.as_posix(), path.read_text(encoding="utf-8").strip()
    return None, None


def _container_resource_gate() -> dict[str, Any]:
    cpu_path, cpu_text = _first_existing_text(
        (
            Path("/sys/fs/cgroup/cpu.max"),
            Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
        )
    )
    cpu_limit: float | None = None
    cpu_period_path: str | None = None
    cpu_period_text: str | None = None
    if cpu_path and cpu_path.endswith("cpu.max") and cpu_text:
        cpu_tokens = cpu_text.split()
        if len(cpu_tokens) == 2 and cpu_tokens[0] != "max":
            cpu_limit = float(cpu_tokens[0]) / float(cpu_tokens[1])
    elif cpu_path and cpu_text:
        cpu_period_path, cpu_period_text = _first_existing_text(
            (Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),)
        )
        if cpu_period_text and int(cpu_text) > 0:
            cpu_limit = float(cpu_text) / float(cpu_period_text)
    cpu_pass = cpu_limit is not None and math.isclose(
        cpu_limit, 1.0, rel_tol=0.0, abs_tol=1.0e-9
    )

    memory_path, memory_text = _first_existing_text(
        (
            Path("/sys/fs/cgroup/memory.max"),
            Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
        )
    )
    memory_limit_bytes: int | None = None
    if memory_text and memory_text != "max":
        memory_limit_bytes = int(memory_text)
    expected_memory_bytes = 8 * 1024**3
    memory_pass = memory_limit_bytes == expected_memory_bytes

    network_root = Path("/sys/class/net")
    network_interfaces = (
        sorted(path.name for path in network_root.iterdir())
        if network_root.is_dir()
        else []
    )
    network_pass = network_interfaces == ["lo"]

    root_flags = os.statvfs("/").f_flag
    root_read_only = bool(root_flags & getattr(os, "ST_RDONLY", 1))

    gpu_device_paths = sorted(
        {
            path.as_posix()
            for pattern in (
                "/dev/nvidia*",
                "/dev/dri/card*",
                "/dev/dri/renderD*",
            )
            for path in Path("/").glob(pattern.lstrip("/"))
        }
    )
    nvidia_visible = os.environ.get("NVIDIA_VISIBLE_DEVICES", "")
    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    gpu_pass = (
        not gpu_device_paths
        and nvidia_visible.lower() in ("", "none", "void")
        and cuda_visible.lower() in ("", "-1", "none", "void")
    )

    record = {
        "cpu": {
            "cgroup_path": cpu_path,
            "raw": cpu_text,
            "period_path": cpu_period_path,
            "period_raw": cpu_period_text,
            "effective_cpu_limit": cpu_limit,
            "expected": 1.0,
            "pass": cpu_pass,
        },
        "memory": {
            "cgroup_path": memory_path,
            "raw": memory_text,
            "limit_bytes": memory_limit_bytes,
            "expected_bytes": expected_memory_bytes,
            "pass": memory_pass,
        },
        "network": {
            "interfaces": network_interfaces,
            "expected": ["lo"],
            "pass": network_pass,
        },
        "root_filesystem": {
            "statvfs_flags": int(root_flags),
            "read_only": root_read_only,
            "pass": root_read_only,
        },
        "gpu": {
            "device_paths": gpu_device_paths,
            "NVIDIA_VISIBLE_DEVICES": nvidia_visible,
            "CUDA_VISIBLE_DEVICES": cuda_visible,
            "pass": gpu_pass,
        },
    }
    record["pass"] = bool(
        cpu_pass and memory_pass and network_pass and root_read_only and gpu_pass
    )
    return record


def _interval_contains_zero(interval: tuple[float, float]) -> bool:
    return interval[0] <= 0.0 <= interval[1]


def _interval_excludes_zero(interval: tuple[float, float]) -> bool:
    return interval[0] > 0.0 or interval[1] < 0.0


def _interval_product(
    first: tuple[float, float], second: tuple[float, float]
) -> tuple[float, float]:
    values = (
        first[0] * second[0],
        first[0] * second[1],
        first[1] * second[0],
        first[1] * second[1],
    )
    return min(values), max(values)


def _determinant_interval(
    a_interval: tuple[float, float],
    little_a_interval: tuple[float, float],
    b_interval: tuple[float, float],
    g_interval: tuple[float, float],
) -> tuple[float, float]:
    ag = _interval_product(a_interval, g_interval)
    little_ab = _interval_product(little_a_interval, b_interval)
    return ag[0] - little_ab[1], ag[1] - little_ab[0]


class SolveLedger:
    def __init__(self, wall_started: float) -> None:
        self.wall_started = wall_started
        self.solve_elapsed_seconds = 0.0
        self.factorization_count = 0
        self.rhs_count = 0
        self.records: list[dict[str, Any]] = []

    def _check_budgets(self, stage: str) -> None:
        if self.solve_elapsed_seconds > SOLVE_BUDGET_SECONDS:
            raise TimeoutError(f"linear-solve budget exceeded at {stage}")
        if time.perf_counter() - self.wall_started > WALL_BUDGET_SECONDS:
            raise TimeoutError(f"runner wall budget exceeded at {stage}")

    def factor(self, matrix: sparse.spmatrix, label: str) -> Any:
        self._check_budgets(f"before factorization {label}")
        started = time.perf_counter()
        factor = sparse_linalg.splu(matrix.tocsc())
        elapsed = time.perf_counter() - started
        self.solve_elapsed_seconds += elapsed
        self.factorization_count += 1
        self.records.append(
            {"kind": "factorization", "label": label, "seconds": elapsed}
        )
        self._check_budgets(f"after factorization {label}")
        return factor

    def solve(self, factor: Any, rhs: np.ndarray, label: str) -> np.ndarray:
        self._check_budgets(f"before RHS {label}")
        started = time.perf_counter()
        solution = np.asarray(factor.solve(rhs))
        elapsed = time.perf_counter() - started
        columns = 1 if rhs.ndim == 1 else int(rhs.shape[1])
        self.solve_elapsed_seconds += elapsed
        self.rhs_count += columns
        self.records.append(
            {
                "kind": "triangular_solve",
                "label": label,
                "rhs_columns": columns,
                "seconds": elapsed,
            }
        )
        self._check_budgets(f"after RHS {label}")
        return solution


def _residual_record(
    matrix: sparse.spmatrix, solution: np.ndarray, rhs: np.ndarray
) -> dict[str, float]:
    residual = np.asarray(matrix @ solution - rhs)
    relative = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1.0e-30))
    denominator = float(sparse_linalg.norm(matrix, ord=np.inf)) * float(
        np.linalg.norm(solution, ord=np.inf)
    )
    denominator += float(np.linalg.norm(rhs, ord=np.inf))
    backward = float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30))
    return {"relative": relative, "backward": backward}


def _structured_mesh_arrays(
    orientation: str,
    length: float,
    thickness: float,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray]:
    if orientation not in ORIENTATIONS:
        raise ValueError(f"unknown mesh orientation: {orientation}")
    x_axis = np.linspace(-0.5 * length, 0.5 * length, nx + 1)
    y_axis = np.linspace(0.0, thickness, ny + 1)
    coordinates = np.asarray(
        [(x_value, y_value) for y_value in y_axis for x_value in x_axis],
        dtype=np.float64,
    )

    def vertex(ix: int, iy: int) -> int:
        return iy * (nx + 1) + ix

    cells: list[tuple[int, int, int]] = []
    for iy in range(ny):
        for ix in range(nx):
            lower_left = vertex(ix, iy)
            lower_right = vertex(ix + 1, iy)
            upper_left = vertex(ix, iy + 1)
            upper_right = vertex(ix + 1, iy + 1)
            if orientation == "slash":
                cells.extend(
                    (
                        (lower_left, lower_right, upper_right),
                        (lower_left, upper_right, upper_left),
                    )
                )
            else:
                cells.extend(
                    (
                        (lower_left, lower_right, upper_left),
                        (lower_right, upper_right, upper_left),
                    )
                )
    return coordinates, np.asarray(cells, dtype=np.int64)


def _signed_twice_areas(coordinates: np.ndarray, cells: np.ndarray) -> np.ndarray:
    first = coordinates[cells[:, 1]] - coordinates[cells[:, 0]]
    second = coordinates[cells[:, 2]] - coordinates[cells[:, 0]]
    return first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]


def _footprint_values(x_values: np.ndarray, length: float) -> np.ndarray:
    footprint_length = length / FOOTPRINT_COUNT
    indices = np.floor((x_values + 0.5 * length) / footprint_length).astype(int)
    indices = np.clip(indices, 0, FOOTPRINT_COUNT - 1)
    values = np.zeros(len(x_values), dtype=np.float64)
    values[indices == LEFT_FOOTPRINT] = 1.0
    values[indices == RIGHT_FOOTPRINT] = -1.0
    return values


def _mesh_pair_precheck(length: float, thickness: float, nx: int, ny: int) -> dict[str, Any]:
    slash_coordinates, slash_cells = _structured_mesh_arrays(
        "slash", length, thickness, nx, ny
    )
    back_coordinates, back_cells = _structured_mesh_arrays(
        "backslash", length, thickness, nx, ny
    )
    coordinates_identical = bool(np.array_equal(slash_coordinates, back_coordinates))
    slash_areas = _signed_twice_areas(slash_coordinates, slash_cells)
    back_areas = _signed_twice_areas(back_coordinates, back_cells)
    positive_areas = bool(np.all(slash_areas > 0.0) and np.all(back_areas > 0.0))

    reflection_nodes = np.empty(len(slash_coordinates), dtype=np.int64)
    for iy in range(ny + 1):
        for ix in range(nx + 1):
            reflection_nodes[iy * (nx + 1) + ix] = iy * (nx + 1) + (nx - ix)
    back_sets = {tuple(sorted(cell)): index for index, cell in enumerate(back_cells)}
    reflected_cell_map = np.asarray(
        [back_sets.get(tuple(sorted(reflection_nodes[cell])), -1) for cell in slash_cells],
        dtype=np.int64,
    )
    strict_mirror = bool(
        np.all(reflected_cell_map >= 0)
        and len(np.unique(reflected_cell_map)) == len(slash_cells)
    )

    slash_centroids = np.mean(slash_coordinates[slash_cells], axis=1)
    back_centroids = np.mean(back_coordinates[back_cells], axis=1)
    centroid_error = float(
        np.max(
            np.abs(
                back_centroids[reflected_cell_map]
                - np.column_stack((-slash_centroids[:, 0], slash_centroids[:, 1]))
            )
        )
    ) if strict_mirror else math.inf
    slash_p = _footprint_values(slash_centroids[:, 0], length)
    back_p = _footprint_values(back_centroids[:, 0], length)
    physical_dipole_mirror_error = float(
        np.max(np.abs(back_p[reflected_cell_map] + slash_p))
    ) if strict_mirror else math.inf

    def coordinate_set(mask: np.ndarray, values: np.ndarray) -> list[tuple[float, float]]:
        return sorted((float(x), float(y)) for x, y in values[mask])

    x_min = -0.5 * length
    x_max = 0.5 * length
    slash_sets = {
        "left": coordinate_set(np.isclose(slash_coordinates[:, 0], x_min), slash_coordinates),
        "right": coordinate_set(np.isclose(slash_coordinates[:, 0], x_max), slash_coordinates),
        "bottom": coordinate_set(np.isclose(slash_coordinates[:, 1], 0.0), slash_coordinates),
        "top": coordinate_set(np.isclose(slash_coordinates[:, 1], thickness), slash_coordinates),
    }
    back_sets_coordinates = {
        "left": coordinate_set(np.isclose(back_coordinates[:, 0], x_min), back_coordinates),
        "right": coordinate_set(np.isclose(back_coordinates[:, 0], x_max), back_coordinates),
        "bottom": coordinate_set(np.isclose(back_coordinates[:, 1], 0.0), back_coordinates),
        "top": coordinate_set(np.isclose(back_coordinates[:, 1], thickness), back_coordinates),
    }
    boundary_sets_identical = slash_sets == back_sets_coordinates
    endpoint_y_match = [item[1] for item in slash_sets["left"]] == [
        item[1] for item in slash_sets["right"]
    ]
    passed = bool(
        coordinates_identical
        and positive_areas
        and strict_mirror
        and centroid_error <= 1.0e-14
        and physical_dipole_mirror_error == 0.0
        and boundary_sets_identical
        and endpoint_y_match
    )
    return {
        "pass": passed,
        "coordinates_identical": coordinates_identical,
        "all_triangles_positive_area": positive_areas,
        "backslash_is_strict_x_reflection_of_slash": strict_mirror,
        "maximum_reflected_centroid_error": centroid_error,
        "physical_p_M_reflection_error": physical_dipole_mirror_error,
        "periodic_endpoint_y_coordinates_match": endpoint_y_match,
        "top_bottom_and_endpoint_coordinate_sets_identical": boundary_sets_identical,
        "node_count": int(len(slash_coordinates)),
        "cell_count": int(len(slash_cells)),
        "hashes": {
            "coordinates": _array_hash(slash_coordinates),
            "slash_connectivity": _array_hash(slash_cells),
            "backslash_connectivity": _array_hash(back_cells),
            "reflection_node_permutation": _array_hash(reflection_nodes),
            "reflection_cell_permutation": _array_hash(reflected_cell_map),
        },
    }


@contextmanager
def _bounded_mesh_patch(model_module: Any, orientation: str) -> Iterator[dict[str, int]]:
    original = model_module._structured_mesh_arrays
    tracker = {"call_count": 0}

    def replacement(
        length: float, thickness: float, nx: int, ny: int
    ) -> tuple[np.ndarray, np.ndarray]:
        tracker["call_count"] += 1
        return _structured_mesh_arrays(orientation, length, thickness, nx, ny)

    model_module._structured_mesh_arrays = replacement
    try:
        yield tracker
    finally:
        model_module._structured_mesh_arrays = original
        if model_module._structured_mesh_arrays is not original:
            raise RuntimeError("bounded mesh patch did not restore production helper")


def _build_oriented_system(
    model_module: Any, label: str, orientation: str, config: Any
) -> tuple[Any, dict[str, Any]]:
    with _bounded_mesh_patch(model_module, orientation) as tracker:
        system = model_module.build_system(
            spatial_label=label, active_profile="uniform", config=config
        )
    if tracker["call_count"] != 2:
        raise RuntimeError(
            f"mesh patch expected myocardium and ECM calls, observed {tracker['call_count']}"
        )
    return system, {
        "bounded_patch_call_count": tracker["call_count"],
        "production_helper_restored": True,
        "myocardium_connectivity_hash": _array_hash(system.myocardium_mesh.cells),
        "ecm_connectivity_hash": _array_hash(system.ecm_mesh.cells),
        "myocardium_coordinate_hash": _array_hash(system.myocardium_mesh.coordinates),
        "ecm_coordinate_hash": _array_hash(system.ecm_mesh.coordinates),
    }


def _footprint_stiffnesses(system: Any) -> tuple[list[sparse.csr_matrix], dict[str, Any]]:
    length = float(system.config.length)
    footprint_length = length / FOOTPRINT_COUNT
    x_centroids = np.asarray(system.ecm_mesh.cell_centroids[:, 0], dtype=np.float64)
    footprint_index = np.floor((x_centroids + 0.5 * length) / footprint_length).astype(int)
    footprint_index = np.clip(footprint_index, 0, FOOTPRINT_COUNT - 1)
    strain_global = (system.ecm_strain_operator_full @ system.ecm_transform).tocsr()
    stiffnesses: list[sparse.csr_matrix] = []
    counts: list[int] = []
    areas: list[float] = []
    for footprint in range(FOOTPRINT_COUNT):
        mask = footprint_index == footprint
        counts.append(int(np.count_nonzero(mask)))
        areas.append(float(np.sum(system.ecm_mesh.cell_areas[mask])))
        blocks = [
            area * system.ecm_constitutive_equilibrium
            if selected
            else np.zeros((3, 3), dtype=np.float64)
            for area, selected in zip(system.ecm_mesh.cell_areas, mask, strict=True)
        ]
        weighted = sparse.block_diag(blocks, format="csr")
        stiffnesses.append((strain_global.T @ weighted @ strain_global).tocsr())
    summed = sum(stiffnesses[1:], stiffnesses[0].copy()).tocsr()
    reference = system.component_matrices["ecm_equilibrium"]
    partition_error = float(
        sparse_linalg.norm(summed - reference)
        / max(float(sparse_linalg.norm(reference)), 1.0e-30)
    )
    return stiffnesses, {
        "definition": "E_eq=E_eq,0*(1+m*p_M); p_M=+1 on I3, -1 on I4",
        "footprint_cell_counts": counts,
        "footprint_areas": areas,
        "partition_relative_error": partition_error,
        "partition_pass": partition_error <= 1.0e-12,
    }


def _rms_strain(system: Any, state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    displacement = np.asarray(system.ecm_transform @ state).ravel()
    strain = np.asarray(system.ecm_strain_operator_full @ displacement).reshape(-1, 3)
    squared = 0.5 * np.real(
        np.einsum("ni,ij,nj->n", np.conjugate(strain), STRAIN_WEIGHT, strain)
    )
    if float(np.min(squared)) < -1.0e-18:
        raise RuntimeError("RMS strain quadratic form became materially negative")
    return np.sqrt(np.maximum(squared, 0.0)), strain


def _rms_strain_derivative(
    baseline_rms: np.ndarray,
    baseline_strain: np.ndarray,
    derivative_strain: np.ndarray,
) -> np.ndarray:
    numerator = np.real(
        np.einsum(
            "ni,ij,nj->n",
            np.conjugate(baseline_strain),
            STRAIN_WEIGHT,
            derivative_strain,
        )
    )
    result = np.zeros_like(baseline_rms)
    positive = baseline_rms > 0.0
    result[positive] = numerator[positive] / (2.0 * baseline_rms[positive])
    return result


def _cell_partition(system: Any) -> dict[str, Any]:
    centroids = np.asarray(system.ecm_mesh.cell_centroids, dtype=np.float64)
    length = float(system.config.length)
    thickness = float(system.config.ecm_thickness)
    footprint_length = length / FOOTPRINT_COUNT
    footprint = np.floor((centroids[:, 0] + 0.5 * length) / footprint_length).astype(int)
    footprint = np.clip(footprint, 0, FOOTPRINT_COUNT - 1)
    z_over_h = 1.0 - centroids[:, 1] / thickness
    band = np.floor(DEPTH_BAND_COUNT * z_over_h).astype(int)
    band = np.clip(band, 0, DEPTH_BAND_COUNT - 1)
    masks: dict[str, list[np.ndarray]] = {"plus": [], "minus": []}
    records = []
    for band_index in range(DEPTH_BAND_COUNT):
        plus = (footprint == LEFT_FOOTPRINT) & (band == band_index)
        minus = (footprint == RIGHT_FOOTPRINT) & (band == band_index)
        plus_area = float(np.sum(system.ecm_mesh.cell_areas[plus]))
        minus_area = float(np.sum(system.ecm_mesh.cell_areas[minus]))
        if not np.any(plus) or not np.any(minus) or plus_area <= 0.0 or minus_area <= 0.0:
            raise RuntimeError(f"empty daughter/depth band {band_index}")
        if not math.isclose(plus_area, minus_area, rel_tol=0.0, abs_tol=1.0e-14):
            raise RuntimeError(f"unequal daughter areas in depth band {band_index}")
        masks["plus"].append(plus)
        masks["minus"].append(minus)
        records.append(
            {
                "band": band_index,
                "z_over_h_interval": [band_index / 8.0, (band_index + 1) / 8.0],
                "plus_cell_count": int(np.count_nonzero(plus)),
                "minus_cell_count": int(np.count_nonzero(minus)),
                "plus_area": plus_area,
                "minus_area": minus_area,
            }
        )
    included = np.logical_or.reduce(masks["plus"] + masks["minus"])
    return {
        "masks": masks,
        "included": included,
        "z_over_h_definition": "1-y/h; z=0 at endocardium and z=1 at myocardium",
        "records": records,
    }


def _band_means(
    values: np.ndarray, areas: np.ndarray, partition: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    result: dict[str, list[float]] = {"plus": [], "minus": []}
    for daughter in ("plus", "minus"):
        for mask in partition["masks"][daughter]:
            result[daughter].append(
                float(np.sum(areas[mask] * values[mask]) / np.sum(areas[mask]))
            )
    return np.asarray(result["plus"]), np.asarray(result["minus"])


def _four_outputs(
    baseline_plus: np.ndarray,
    baseline_minus: np.ndarray,
    derivative_plus: np.ndarray,
    derivative_minus: np.ndarray,
) -> dict[str, np.ndarray]:
    return {
        "A": (baseline_plus + baseline_minus) / (2.0 * ALPHA_0),
        "B": (baseline_plus - baseline_minus) / ALPHA_0,
        "a": (derivative_plus + derivative_minus) / 2.0,
        "g": derivative_plus - derivative_minus,
    }


def _fd_gate(analytic: float, finite_difference: float) -> dict[str, Any]:
    absolute_error = abs(finite_difference - analytic)
    if abs(analytic) > FD_NEAR_ZERO_TOLERANCE:
        relative_error = absolute_error / abs(analytic)
        return {
            "classification": "resolved",
            "absolute_error": absolute_error,
            "relative_error": relative_error,
            "tolerance": FD_RELATIVE_TOLERANCE,
            "pass": relative_error <= FD_RELATIVE_TOLERANCE,
        }
    return {
        "classification": "near_zero",
        "absolute_error": absolute_error,
        "relative_error": None,
        "tolerance": FD_ABSOLUTE_TOLERANCE,
        "pass": absolute_error <= FD_ABSOLUTE_TOLERANCE,
    }


def _one_discretization(
    model_module: Any,
    config: Any,
    level: str,
    orientation: str,
    ledger: SolveLedger,
) -> dict[str, Any]:
    label = f"{level}:{orientation}"
    started = time.perf_counter()
    system, patch_record = _build_oriented_system(model_module, level, orientation, config)
    active_dc, active_harmonic, load_dc, load_harmonic, profile = (
        model_module._case_components("A1", system)
    )
    if profile != "uniform" or np.any(load_dc) or np.any(load_harmonic):
        raise RuntimeError("A1 source contract drift")
    if not math.isclose(float(active_dc), 0.5 * ALPHA_0, abs_tol=1.0e-15):
        raise RuntimeError("A1 active DC amplitude drift")
    if abs(active_harmonic - complex(-0.5 * ALPHA_0)) > 1.0e-15:
        raise RuntimeError("A1 active harmonic amplitude drift")

    dt = config.period / STEPS_PER_CYCLE
    omega = 2.0 * math.pi / config.period
    zeta = np.exp(1j * omega * dt)
    delta_t = (zeta - 1.0) / dt
    mu = 0.5 * (zeta + 1.0)
    harmonic_matrix = (delta_t * system.matrix_g + mu * system.matrix_a).tocsr()
    physical_source = load_harmonic - system.active_vector_h * active_harmonic
    harmonic_rhs = mu * physical_source
    factor = ledger.factor(harmonic_matrix, f"{label}:baseline")
    harmonic_state = ledger.solve(factor, harmonic_rhs, f"{label}:baseline")
    baseline_residual = _residual_record(harmonic_matrix, harmonic_state, harmonic_rhs)

    baseline_rms, baseline_strain = _rms_strain(system, harmonic_state)
    partition = _cell_partition(system)
    included_rms = baseline_rms[partition["included"]]
    if np.any(included_rms <= STRAIN_NEAR_ZERO_TOLERANCE):
        raise NearZeroReadout(
            {
                "level": level,
                "orientation": orientation,
                "minimum_included_s_e": float(np.min(included_rms)),
                "threshold": STRAIN_NEAR_ZERO_TOLERANCE,
                "included_cell_count": int(len(included_rms)),
            }
        )
    baseline_plus, baseline_minus = _band_means(
        baseline_rms, system.ecm_mesh.cell_areas, partition
    )

    stiffnesses, stiffness_partition = _footprint_stiffnesses(system)
    if not stiffness_partition["partition_pass"]:
        raise RuntimeError("ECM footprint stiffness partition failed")
    dipole_stiffness = (stiffnesses[LEFT_FOOTPRINT] - stiffnesses[RIGHT_FOOTPRINT]).tocsr()
    sensitivity_rhs = -mu * (dipole_stiffness @ harmonic_state)
    sensitivity_state = ledger.solve(
        factor, sensitivity_rhs, f"{label}:analytic_m_derivative"
    )
    sensitivity_residual = _residual_record(
        harmonic_matrix, sensitivity_state, sensitivity_rhs
    )
    derivative_displacement = np.asarray(system.ecm_transform @ sensitivity_state).ravel()
    derivative_strain = np.asarray(
        system.ecm_strain_operator_full @ derivative_displacement
    ).reshape(-1, 3)
    derivative_rms = _rms_strain_derivative(
        baseline_rms, baseline_strain, derivative_strain
    )
    derivative_plus, derivative_minus = _band_means(
        derivative_rms, system.ecm_mesh.cell_areas, partition
    )
    analytic = _four_outputs(
        baseline_plus, baseline_minus, derivative_plus, derivative_minus
    )

    fd_outputs: dict[str, list[np.ndarray]] = {"a": [], "g": []}
    fd_records = []
    residuals = [baseline_residual, sensitivity_residual]
    for amplitude in FD_AMPLITUDES:
        perturbed_rms: dict[int, np.ndarray] = {}
        amplitude_residuals: dict[str, Any] = {}
        for sign_value in (-1, 1):
            m_value = sign_value * amplitude
            perturbed_matrix = (
                harmonic_matrix + m_value * mu * dipole_stiffness
            ).tocsr()
            perturbed_factor = ledger.factor(
                perturbed_matrix, f"{label}:m={m_value:+.1e}"
            )
            perturbed_state = ledger.solve(
                perturbed_factor, harmonic_rhs, f"{label}:m={m_value:+.1e}"
            )
            residual = _residual_record(
                perturbed_matrix, perturbed_state, harmonic_rhs
            )
            residuals.append(residual)
            amplitude_residuals[str(sign_value)] = residual
            perturbed_rms[sign_value], _ = _rms_strain(system, perturbed_state)
        fd_cell = (perturbed_rms[1] - perturbed_rms[-1]) / (2.0 * amplitude)
        fd_plus, fd_minus = _band_means(
            fd_cell, system.ecm_mesh.cell_areas, partition
        )
        fd_four = _four_outputs(
            baseline_plus, baseline_minus, fd_plus, fd_minus
        )
        fd_outputs["a"].append(fd_four["a"])
        fd_outputs["g"].append(fd_four["g"])
        comparisons = {
            quantity: [
                _fd_gate(float(analytic[quantity][band]), float(fd_four[quantity][band]))
                for band in range(DEPTH_BAND_COUNT)
            ]
            for quantity in ("a", "g")
        }
        fd_records.append(
            {
                "amplitude": amplitude,
                "outputs": {"a": fd_four["a"], "g": fd_four["g"]},
                "comparisons": comparisons,
                "linear_residuals": amplitude_residuals,
            }
        )

    maximum_relative_residual = max(item["relative"] for item in residuals)
    maximum_backward_error = max(item["backward"] for item in residuals)
    residual_pass = bool(
        maximum_relative_residual <= RELATIVE_RESIDUAL_TOLERANCE
        and maximum_backward_error <= BACKWARD_ERROR_TOLERANCE
    )
    fd_pass = all(
        comparison["pass"]
        for record in fd_records
        for quantity in ("a", "g")
        for comparison in record["comparisons"][quantity]
    )

    tangent_plus = baseline_plus / ALPHA_0
    tangent_minus = baseline_minus / ALPHA_0
    baseline_scale = np.maximum.reduce(
        (np.abs(tangent_plus), np.abs(tangent_minus), np.full(8, 1.0e-30))
    )
    raw_noise = {
        "A": np.maximum(baseline_scale * baseline_residual["relative"], 1.0e-30),
        "B": np.maximum(baseline_scale * baseline_residual["relative"], 1.0e-30),
    }
    for quantity in ("a", "g"):
        fd_stack = np.vstack(fd_outputs[quantity])
        maximum_fd_error = np.max(
            np.abs(fd_stack - analytic[quantity][None, :]), axis=0
        )
        derivative_scale = np.maximum.reduce(
            (
                np.abs(derivative_plus),
                np.abs(derivative_minus),
                np.abs(analytic[quantity]),
                np.max(np.abs(fd_stack), axis=0),
                np.full(8, 1.0e-30),
            )
        )
        raw_noise[quantity] = np.maximum.reduce(
            (
                maximum_fd_error,
                derivative_scale * maximum_relative_residual,
                np.full(8, 1.0e-30),
            )
        )

    return {
        "level": level,
        "orientation": orientation,
        "elapsed_wall_seconds": time.perf_counter() - started,
        "mesh_patch": patch_record,
        "mesh": {
            "nx": int(config.spatial(level).nx),
            "ny_per_layer": int(config.spatial(level).ny_per_layer),
            "state_size": int(system.state_size),
            "ecm_cell_count": int(len(system.ecm_mesh.cells)),
            "depth_partition": {
                "definition": partition["z_over_h_definition"],
                "bands": partition["records"],
            },
        },
        "harmonic_system": {
            "dt": dt,
            "zeta": _complex_record(complex(zeta)),
            "delta_t": _complex_record(complex(delta_t)),
            "mu": _complex_record(complex(mu)),
            "peak_phasor_convention": "e(t)=e_dc+Re[e_hat*exp(i*omega*t)]",
            "strain_order": ["epsilon_xx", "epsilon_yy", "gamma_xy"],
            "strain_weight": STRAIN_WEIGHT,
            "baseline_residual": baseline_residual,
        },
        "ECM_dipole": {
            "normalization": "E_eq(x;m)=E_eq,0*(1+m*p_M(x))",
            "p_M": {"I3": 1.0, "I4": -1.0, "all_other_footprints": 0.0},
            "dimensionless_FD_amplitudes": list(FD_AMPLITUDES),
            "K_definition": "K_I3-K_I4; equilibrium Young-modulus branch only",
            "K_frobenius_norm": float(sparse_linalg.norm(dipole_stiffness)),
            "footprint_partition": stiffness_partition,
        },
        "daughter_band_values": {
            "baseline_S_plus": baseline_plus,
            "baseline_S_minus": baseline_minus,
            "analytic_delta_S_plus": derivative_plus,
            "analytic_delta_S_minus": derivative_minus,
        },
        "outputs": analytic,
        "analytic_derivative": {
            "state_formula": "delta_q=-H_T^-1*mu*(K_I3-K_I4)*q_hat",
            "rms_formula": "delta_s=Re[e_hat^* W delta_e_hat]/(2*s)",
            "linear_residual": sensitivity_residual,
        },
        "finite_difference": {
            "records": fd_records,
            "relative_tolerance": FD_RELATIVE_TOLERANCE,
            "near_zero_threshold": FD_NEAR_ZERO_TOLERANCE,
            "absolute_tolerance": FD_ABSOLUTE_TOLERANCE,
            "pass": fd_pass,
        },
        "linear_residual_gate": {
            "maximum_relative_residual": maximum_relative_residual,
            "maximum_backward_error": maximum_backward_error,
            "relative_tolerance": RELATIVE_RESIDUAL_TOLERANCE,
            "backward_tolerance": BACKWARD_ERROR_TOLERANCE,
            "pass": residual_pass,
        },
        "raw_numerical_noise": raw_noise,
        "all_local_gates_pass": bool(residual_pass and fd_pass),
    }


def _paired_analysis(discretizations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    per_level: dict[str, Any] = {}
    mirror_pass = True
    for level in SPATIAL_LEVELS:
        slash = discretizations[level]["slash"]
        backslash = discretizations[level]["backslash"]
        fields: dict[str, Any] = {}
        for quantity in ("A", "B", "a", "g"):
            slash_values = np.asarray(slash["outputs"][quantity])
            back_values = np.asarray(backslash["outputs"][quantity])
            if quantity in ("A", "g"):
                mismatch = np.abs(slash_values - back_values)
                relation = "same"
            else:
                mismatch = np.abs(slash_values + back_values)
                relation = "opposite"
            tolerance = np.maximum(
                MIRROR_ABSOLUTE_TOLERANCE,
                MIRROR_RELATIVE_TOLERANCE
                * np.maximum(np.abs(slash_values), np.abs(back_values)),
            )
            passes = mismatch <= tolerance
            mirror_pass = bool(mirror_pass and np.all(passes))
            fields[quantity] = {
                "expected_parity": relation,
                "slash": slash_values,
                "backslash": back_values,
                "physical_candidate": 0.5 * (slash_values + back_values),
                "parity_half_mismatch": 0.5 * mismatch,
                "absolute_mismatch": mismatch,
                "tolerance": tolerance,
                "pass_by_band": passes.tolist(),
                "pass": bool(np.all(passes)),
            }
        per_level[level] = fields

    band_records = []
    cross_grid_pass = True
    expected_zero_pass = True
    for band in range(DEPTH_BAND_COUNT):
        intervals: dict[str, tuple[float, float]] = {}
        values: dict[str, Any] = {}
        for quantity in ("A", "B", "a", "g"):
            s2 = float(per_level["S2"][quantity]["physical_candidate"][band])
            s3 = float(per_level["S3"][quantity]["physical_candidate"][band])
            cross_difference = abs(s3 - s2)
            raw_noise = max(
                float(discretizations[level][orientation]["raw_numerical_noise"][quantity][band])
                for level in SPATIAL_LEVELS
                for orientation in ORIENTATIONS
            )
            s3_half_mismatch = float(
                per_level["S3"][quantity]["parity_half_mismatch"][band]
            )
            radius = NOISE_MULTIPLIER * raw_noise + s3_half_mismatch + cross_difference
            interval = (s3 - radius, s3 + radius)
            intervals[quantity] = interval
            above_noise = abs(s3) > NOISE_MULTIPLIER * raw_noise
            relative_change = cross_difference / max(abs(s3), abs(s2), 1.0e-30)
            if quantity == "A":
                convergence_required = True
                convergence_pass = bool(
                    above_noise and relative_change <= CROSS_GRID_RELATIVE_TOLERANCE
                )
            elif quantity == "g":
                convergence_required = above_noise
                convergence_pass = bool(
                    (not convergence_required)
                    or relative_change <= CROSS_GRID_RELATIVE_TOLERANCE
                )
            else:
                convergence_required = False
                convergence_pass = _interval_contains_zero(interval)
                expected_zero_pass = bool(expected_zero_pass and convergence_pass)
            cross_grid_pass = bool(cross_grid_pass and convergence_pass)
            values[quantity] = {
                "S2_physical": s2,
                "S3_physical": s3,
                "cross_grid_absolute_difference": cross_difference,
                "cross_grid_relative_change": relative_change,
                "raw_noise_maximum": raw_noise,
                "above_100x_noise": above_noise,
                "S3_parity_half_mismatch": s3_half_mismatch,
                "empirical_error_radius": radius,
                "empirical_interval": interval,
                "convergence_required": convergence_required,
                "convergence_pass": convergence_pass,
            }
        determinant = _determinant_interval(
            intervals["A"], intervals["a"], intervals["B"], intervals["g"]
        )
        center_matrix = np.asarray(
            (
                (values["A"]["S3_physical"], values["a"]["S3_physical"]),
                (values["B"]["S3_physical"], values["g"]["S3_physical"]),
            ),
            dtype=np.float64,
        )
        condition_number = float(np.linalg.cond(center_matrix))
        band_records.append(
            {
                "band": band,
                "z_over_h_interval": [band / 8.0, (band + 1) / 8.0],
                "quantities": values,
                "determinant": {
                    "formula": "A*g-a*B",
                    "center": float(np.linalg.det(center_matrix)),
                    "empirical_interval": determinant,
                    "interval_excludes_zero": _interval_excludes_zero(determinant),
                },
                "center_matrix_condition": {
                    "value": condition_number if math.isfinite(condition_number) else None,
                    "status": "finite" if math.isfinite(condition_number) else "singular",
                    "descriptive_only": True,
                },
            }
        )

    residual_pass = all(
        discretizations[level][orientation]["linear_residual_gate"]["pass"]
        for level in SPATIAL_LEVELS
        for orientation in ORIENTATIONS
    )
    fd_pass = all(
        discretizations[level][orientation]["finite_difference"]["pass"]
        for level in SPATIAL_LEVELS
        for orientation in ORIENTATIONS
    )
    return {
        "mirror": {"levels": per_level, "pass": mirror_pass},
        "cross_grid": {
            "relative_tolerance": CROSS_GRID_RELATIVE_TOLERANCE,
            "pass": cross_grid_pass,
        },
        "expected_zero_B_a": {"pass": expected_zero_pass},
        "linear_residuals_pass": residual_pass,
        "finite_difference_pass": fd_pass,
        "bands": band_records,
    }


def _classify(geometry_pass: bool, paired: dict[str, Any]) -> dict[str, Any]:
    bands = paired["bands"]
    if not geometry_pass or not paired["mirror"]["pass"]:
        return {
            "status": "SYMMETRY_OR_IMPLEMENTATION_FAIL",
            "subtype": "MIRROR_IMPLEMENTATION_FAIL",
            "bounded_claim": "paired mesh or parity implementation did not pass",
        }
    if not paired["linear_residuals_pass"] or not paired["finite_difference_pass"]:
        return {
            "status": "NOT_RESOLVED",
            "bounded_claim": "linear residual or analytic-to-FD gate did not pass",
        }
    if any(
        _interval_excludes_zero(tuple(band["quantities"]["a"]["empirical_interval"]))
        for band in bands
    ):
        return {
            "status": "SYMMETRY_OR_IMPLEMENTATION_FAIL",
            "bounded_claim": "mother-average odd derivative is inconsistent with zero",
        }
    if not paired["cross_grid"]["pass"] or not paired["expected_zero_B_a"]["pass"]:
        return {
            "status": "NOT_RESOLVED",
            "bounded_claim": "two-grid empirical convergence or expected-zero gate did not pass",
        }

    a_positive = all(
        band["quantities"]["A"]["empirical_interval"][0] > 0.0 for band in bands
    )
    b_and_a_zero = all(
        _interval_contains_zero(tuple(band["quantities"][quantity]["empirical_interval"]))
        for band in bands
        for quantity in ("B", "a")
    )
    g_positive = all(
        band["quantities"]["g"]["empirical_interval"][0] > 0.0 for band in bands
    )
    g_negative = all(
        band["quantities"]["g"]["empirical_interval"][1] < 0.0 for band in bands
    )
    rank_open_by_band = [
        bool(
            band["quantities"]["A"]["empirical_interval"][0] > 0.0
            and all(
                _interval_contains_zero(
                    tuple(band["quantities"][quantity]["empirical_interval"])
                )
                for quantity in ("B", "a")
            )
            and _interval_excludes_zero(
                tuple(band["quantities"]["g"]["empirical_interval"])
            )
            and band["determinant"]["interval_excludes_zero"]
        )
        for band in bands
    ]
    if a_positive and b_and_a_zero and (g_positive or g_negative) and all(rank_open_by_band):
        return {
            "status": "ROBUST_GO_LINEAGE_ODD_MODE",
            "bounded_claim": (
                "rank-opening and g sign are robust only within the two-grid empirical "
                "envelope and piecewise-constant nonnegative depth-kernel class"
            ),
        }

    g_intervals = [
        tuple(band["quantities"]["g"]["empirical_interval"]) for band in bands
    ]
    signs = [1 if item[0] > 0.0 else -1 if item[1] < 0.0 else 0 for item in g_intervals]
    if all(
        item[0] >= -ROBUST_NO_GO_TOLERANCE
        and item[1] <= ROBUST_NO_GO_TOLERANCE
        for item in g_intervals
    ):
        return {
            "status": "ROBUST_NUMERICAL_NO_GO",
            "bounded_claim": (
                "the current scalar, geometry, parameter point and first depth-kernel class "
                "are near zero only within the two-grid empirical envelope"
            ),
        }
    rank_open_signs = [
        signs[index] for index, rank_open in enumerate(rank_open_by_band) if rank_open
    ]
    if any(rank_open_by_band) and (
        (1 in rank_open_signs and -1 in rank_open_signs)
        or not all(rank_open_by_band)
    ):
        return {
            "status": "CONDITIONAL_GO_NEEDS_DEPTH_EXPERIMENT",
            "bounded_claim": (
                "complete rank-opening is resolved only in a depth-dependent subset or "
                "changes sign across depth"
            ),
            "rank_open_by_band": rank_open_by_band,
        }
    return {
        "status": "NOT_RESOLVED",
        "bounded_claim": "the preregistered empirical gates do not support a signed conclusion",
    }


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def run(output: Path, base_commit: str, approved_runner_sha256: str) -> int:
    wall_started = PROCESS_WALL_STARTED
    alarm_available = PROCESS_ALARM_AVAILABLE
    previous_handler = PROCESS_PREVIOUS_ALARM_HANDLER
    if not alarm_available:
        raise RuntimeError("hard complete-process wall-clock alarm is unavailable")
    if __name__ != "__main__":
        remaining_wall_seconds = WALL_BUDGET_SECONDS - (
            time.perf_counter() - wall_started
        )
        if remaining_wall_seconds <= 0.0:
            raise TimeoutError("complete-process wall-clock budget already exhausted")
        previous_handler = signal.signal(signal.SIGALRM, _process_wall_timeout)
        signal.setitimer(signal.ITIMER_REAL, remaining_wall_seconds)
    if base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError(
            f"base commit drift: {base_commit} != {EXPECTED_BASE_COMMIT}"
        )
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root.resolve() != EXPECTED_PROJECT_ROOT:
        raise RuntimeError(f"project mount drift: {repo_root.resolve()}")
    if output.resolve() != EXPECTED_CONTAINER_OUTPUT:
        raise RuntimeError(f"container output boundary mismatch: {output.resolve()}")
    if not output.parent.exists() or output.exists() or any(output.parent.iterdir()):
        raise RuntimeError("create-only output mount must exist and be empty")

    actual_head = _git_head(repo_root)
    if actual_head != EXPECTED_BASE_COMMIT:
        raise RuntimeError(f"HEAD drift: {actual_head} != {EXPECTED_BASE_COMMIT}")
    actual_source_hashes = {
        relative: _sha256(repo_root / relative) for relative in SOURCE_HASHES
    }
    if actual_source_hashes != SOURCE_HASHES:
        raise RuntimeError("gate-critical tracked source hash drift")
    runner_sha256 = _sha256(repo_root / RUNNER_PATH)
    if runner_sha256 != approved_runner_sha256.lower():
        raise RuntimeError("runner SHA256 does not match execution authorization")

    ledger = SolveLedger(wall_started)
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "logical_output": LOGICAL_OUTPUT,
        "source_version": {
            "accepted_contract_commit": EXPECTED_BASE_COMMIT,
            "actual_HEAD": actual_head,
            "runner_sha256": runner_sha256,
            "approved_runner_sha256": approved_runner_sha256.lower(),
            "tracked_source_hashes": actual_source_hashes,
            "tracked_source_hash_gate_pass": True,
        },
        "frozen_scope": {
            "case": "A1 uniform prescribed active strain",
            "alpha_0": ALPHA_0,
            "H": 0.3,
            "De": 0.2,
            "T": STEPS_PER_CYCLE,
            "spatial_levels": list(SPATIAL_LEVELS),
            "orientations": list(ORIENTATIONS),
            "daughter_left": "I3",
            "daughter_right": "I4",
            "depth_coordinate": "z/h=1-y/h",
            "depth_bands": DEPTH_BAND_COUNT,
            "FD_amplitudes": list(FD_AMPLITUDES),
            "S4_run": False,
            "division_DCM_implemented": False,
            "feedback_fluid_3D_nonlinear_parameter_scan": False,
        },
        "frozen_gates": {
            "relative_residual": RELATIVE_RESIDUAL_TOLERANCE,
            "backward_error": BACKWARD_ERROR_TOLERANCE,
            "strain_near_zero": STRAIN_NEAR_ZERO_TOLERANCE,
            "FD_near_zero": FD_NEAR_ZERO_TOLERANCE,
            "FD_relative": FD_RELATIVE_TOLERANCE,
            "FD_absolute": FD_ABSOLUTE_TOLERANCE,
            "mirror_absolute": MIRROR_ABSOLUTE_TOLERANCE,
            "mirror_relative": MIRROR_RELATIVE_TOLERANCE,
            "cross_grid_relative": CROSS_GRID_RELATIVE_TOLERANCE,
            "noise_multiplier": NOISE_MULTIPLIER,
            "robust_no_go_absolute": ROBUST_NO_GO_TOLERANCE,
            "linear_solve_seconds": SOLVE_BUDGET_SECONDS,
            "runner_wall_seconds": WALL_BUDGET_SECONDS,
        },
    }
    summary["execution"] = {
        "status": "RUNNING",
        "runtime": {
            "container_name": os.environ.get("PAPER2_CONTAINER_NAME"),
            "container_image": "dolfinx/dolfinx:v0.11.0",
            "container_image_id": os.environ.get("PAPER2_IMAGE_ID"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "complete_process_wall_alarm_enabled": True,
        },
    }
    return_code = 1
    try:
        for variable in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            if os.environ.get(variable) != "1":
                raise RuntimeError(
                    f"single-CPU environment drift: {variable}={os.environ.get(variable)!r}"
                )
        if os.environ.get("PAPER2_IMAGE_ID") != EXPECTED_IMAGE_ID:
            raise RuntimeError("container image identity drift")
        if not os.environ.get("PYTHONPATH", "").startswith(EXPECTED_PYTHONPATH_PREFIX):
            raise RuntimeError("PYTHONPATH drift")
        resource_gate = _container_resource_gate()
        summary["execution"]["runtime"]["resource_gate"] = resource_gate
        if not resource_gate["pass"]:
            raise RuntimeError("container resource boundary verification failed")

        import dolfinx
        from paper2_hybrid.config import ACTIVE_CONFIG
        import paper2_hybrid.model as model_module

        dolfinx_path = Path(dolfinx.__file__).resolve()
        expected_dolfinx_root = Path(
            "/usr/local/dolfinx-real/lib/python3.12/dist-packages/dolfinx"
        )
        if not str(dolfinx_path).startswith(str(expected_dolfinx_root) + os.sep):
            raise RuntimeError(f"dolfinx import path drift: {dolfinx_path}")

        config = replace(
            ACTIVE_CONFIG,
            ecm_thickness=0.3 * ACTIVE_CONFIG.length,
            ecm_relaxation_time=0.2 * ACTIVE_CONFIG.period,
            activation_peak=ALPHA_0,
        ).checked()
        summary["parameters"] = {**asdict(config), "config_digest": config.digest()}
        summary["execution"]["runtime"].update(
            {
                "dolfinx": dolfinx.__version__,
                "dolfinx_path": dolfinx_path.as_posix(),
            }
        )

        mesh_prechecks = {}
        for level in SPATIAL_LEVELS:
            spatial = config.spatial(level)
            mesh_prechecks[level] = _mesh_pair_precheck(
                config.length,
                config.ecm_thickness,
                spatial.nx,
                spatial.ny_per_layer,
            )
        geometry_pass = all(item["pass"] for item in mesh_prechecks.values())
        summary["mesh_pair_prechecks"] = mesh_prechecks
        if not geometry_pass:
            summary["scientific_interpretation"] = {
                "status": "SYMMETRY_OR_IMPLEMENTATION_FAIL",
                "subtype": "MIRROR_IMPLEMENTATION_FAIL",
                "bounded_claim": "strict mirror connectivity precheck failed before solve",
            }
        else:
            discretizations: dict[str, dict[str, Any]] = {}
            for level in SPATIAL_LEVELS:
                discretizations[level] = {}
                for orientation in ORIENTATIONS:
                    discretizations[level][orientation] = _one_discretization(
                        model_module, config, level, orientation, ledger
                    )
            summary["discretizations"] = discretizations
            if ledger.factorization_count != 20 or ledger.rhs_count != 24:
                raise RuntimeError(
                    "solve-count contract drift: expected 20 factorizations and 24 RHS"
                )
            paired = _paired_analysis(discretizations)
            summary["paired_analysis"] = paired
            summary["depth_kernel_convex_hull"] = {
                "class": "nonnegative probability kernels constant within each of eight bands",
                "g_interval": [
                    min(
                        band["quantities"]["g"]["empirical_interval"][0]
                        for band in paired["bands"]
                    ),
                    max(
                        band["quantities"]["g"]["empirical_interval"][1]
                        for band in paired["bands"]
                    ),
                ],
                "not_a_continuous_depth_limit": True,
            }
            summary["scientific_interpretation"] = _classify(
                geometry_pass, paired
            )
        summary["scientific_interpretation"].update(
            {
                "not_a_real_division_simulation": True,
                "not_DCM_necessity": True,
                "not_experimental_truth_or_calibration": True,
                "full_feedback_sign_requires": "q_s*q_e*c_a*c_m",
                "two_grid_difference_is_not_a_rigorous_continuum_error_bound": True,
                "independent_human_acceptance_required": True,
            }
        )
        summary["status"] = "COMPLETED"
        summary["execution"]["status"] = "PASS"
        return_code = 0
    except NearZeroReadout as error:
        summary["status"] = "COMPLETED_NOT_EVALUABLE"
        summary.setdefault("execution", {})["status"] = "PASS"
        summary["scientific_interpretation"] = {
            "status": "NOT_EVALUABLE_NEAR_ZERO",
            "bounded_claim": "the preregistered RMS derivative is undefined in an included cell",
            "record": error.record,
            "not_a_scientific_negative_result": True,
        }
        return_code = 0
    except BaseException as error:
        summary["status"] = "FAILED_CLOSED"
        summary.setdefault("execution", {})["status"] = "FAIL"
        summary["execution"].update(
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        summary.setdefault(
            "scientific_interpretation",
            {
                "status": "NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE",
                "not_a_scientific_negative_result": True,
            },
        )
    finally:
        total_wall = time.perf_counter() - wall_started
        summary.setdefault("execution", {})["completed_at_utc"] = datetime.now(
            timezone.utc
        ).isoformat()
        summary["execution"]["solve_ledger"] = {
            "budget_seconds": SOLVE_BUDGET_SECONDS,
            "elapsed_seconds": ledger.solve_elapsed_seconds,
            "factorization_count": ledger.factorization_count,
            "rhs_count": ledger.rhs_count,
            "records": ledger.records,
        }
        summary["execution"]["total_wall_seconds"] = total_wall
        summary["execution"]["wall_budget_seconds"] = WALL_BUDGET_SECONDS
        summary["execution"]["peak_rss_gib"] = float(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ) / (1024.0**2)
        safe_summary = _json_safe(summary)
        encoded = json.dumps(
            safe_summary, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
        ) + "\n"
        json.loads(encoded)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    wall_at_output_close = time.perf_counter() - wall_started
    signal.setitimer(signal.ITIMER_REAL, 0.0)
    if previous_handler is not None:
        signal.signal(signal.SIGALRM, previous_handler)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "scientific_interpretation": summary["scientific_interpretation"]["status"],
                "factorization_count": ledger.factorization_count,
                "rhs_count": ledger.rhs_count,
                "solve_seconds": ledger.solve_elapsed_seconds,
                "wall_seconds_to_summary_encoding": summary["execution"]["total_wall_seconds"],
                "wall_seconds_to_output_close": wall_at_output_close,
            },
            indent=2,
        )
    )
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--runner-sha256", required=True)
    arguments = parser.parse_args()
    return run(arguments.output, arguments.base_commit, arguments.runner_sha256)


if __name__ == "__main__":
    sys.exit(main())
