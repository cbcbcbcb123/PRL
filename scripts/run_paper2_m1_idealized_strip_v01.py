"""Run and freeze the CPU-only Paper 2 M1 idealized strip validation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paper2_m1.idealized_strip import SimulationResult, run_validation_suite  # noqa: E402


DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "paper2_m1"
    / "idealized_strip_v03_20260903"
)


def _create_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"create-only output already exists: {path}")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _create_npz(path: Path, result: SimulationResult) -> None:
    if path.exists():
        raise FileExistsError(f"create-only output already exists: {path}")
    np.savez_compressed(path, **result.arrays)


def _file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _create_diagnostic_figure(
    path: Path,
    active: SimulationResult,
    pressure: SimulationResult,
) -> None:
    if path.exists():
        raise FileExistsError(f"create-only output already exists: {path}")
    active_arrays = active.arrays
    pressure_arrays = pressure.arrays
    time = active_arrays["time"]
    peak_index = int(np.argmax(active_arrays["activation"]))
    coordinates = np.linspace(0.0, 1.0, active.config.node_count)
    displacement_scale = 3.0

    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.6), constrained_layout=True)
    axis = axes[0, 0]
    layer_payload = (
        (
            "Endocardial DCM",
            active_arrays["endocardium_displacement"][peak_index],
            2.0,
            "#b33b46",
            "o",
        ),
        (
            "Viscoelastic ECM FEM",
            active_arrays["ecm_displacement"][peak_index],
            1.0,
            "#2c7fb8",
            "s",
        ),
        (
            "Active myocardium FEM",
            active_arrays["myocardium_displacement"][peak_index],
            0.0,
            "#d98c2b",
            "^",
        ),
    )
    for label, displacement, base_height, color, marker in layer_payload:
        axis.plot(
            coordinates + displacement_scale * displacement[:, 0],
            base_height + displacement_scale * displacement[:, 1],
            color=color,
            marker=marker,
            linewidth=1.8,
            markersize=4.5,
            label=label,
        )
    axis.set_title("A  Peak-active strip state (3x displacement)")
    axis.set_xlabel("tangential coordinate")
    axis.set_ylabel("layer position")
    axis.set_yticks((0.0, 1.0, 2.0))
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)

    axis = axes[0, 1]
    axis.plot(
        time,
        active_arrays["activation"],
        color="#6b6b6b",
        linewidth=1.4,
        label="activation a(t)",
    )
    axis.plot(
        time,
        active_arrays["myocardial_shortening"],
        color="#d98c2b",
        linewidth=1.8,
        label="myocardial shortening",
    )
    axis.plot(
        time,
        np.max(
            np.abs(active_arrays["traction_ecm_on_endocardium"]), axis=(1, 2)
        ),
        color="#b33b46",
        linewidth=1.3,
        label="max endocardial-interface traction",
    )
    axis.set_title("B  Active transfer through ECM")
    axis.set_xlabel("time / period")
    axis.set_ylabel("nondimensional response")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)

    axis = axes[1, 0]
    weights = np.ones(pressure.config.node_count)
    weights[[0, -1]] = 0.5
    for label, key, color in (
        ("endocardium", "endocardium_displacement", "#b33b46"),
        ("ECM", "ecm_displacement", "#2c7fb8"),
        ("myocardium", "myocardium_displacement", "#d98c2b"),
    ):
        mean_normal = np.average(
            pressure_arrays[key][:, :, 1], axis=1, weights=weights
        )
        axis.plot(
            pressure_arrays["time"],
            mean_normal,
            color=color,
            linewidth=1.5,
            label=label,
        )
    axis.plot(
        pressure_arrays["time"],
        -pressure_arrays["pressure"],
        color="#333333",
        linestyle="--",
        linewidth=1.1,
        label="-pressure input",
    )
    axis.set_title("C  Lumen-normal load transmission")
    axis.set_xlabel("time / period")
    axis.set_ylabel("normal displacement / traction")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)

    axis = axes[1, 1]
    cumulative_active = np.cumsum(active_arrays["work_active"])
    cumulative_dissipation = np.cumsum(
        active_arrays["dissipation_ecm"]
        + active_arrays["dissipation_endocardium"]
        + active_arrays["dissipation_myocardium"]
    )
    cumulative_left = (
        active_arrays["stored_energy"][1:]
        - active_arrays["stored_energy"][0]
        + cumulative_dissipation
    )
    step_time = active_arrays["time"][1:]
    axis.plot(
        step_time,
        cumulative_active,
        color="#3a923a",
        linewidth=1.7,
        label="cumulative active work",
    )
    axis.plot(
        step_time,
        cumulative_left,
        color="#2c5aa0",
        linestyle="--",
        linewidth=1.5,
        label="Delta stored + dissipation",
    )
    axis.set_title("D  Integrated power ledger")
    axis.set_xlabel("time / period")
    axis.set_ylabel("nondimensional work")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.suptitle(
        "Paper 2 M1 idealized identity/port validation — not physiological calibration",
        fontsize=12,
    )
    figure.savefig(path, dpi=180, facecolor="white")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    suite = run_validation_suite()
    case_results: dict[str, SimulationResult] = suite.pop("cases")
    sensitivity_results: dict[str, SimulationResult] = suite.pop(
        "sensitivity_cases"
    )

    created_files: list[Path] = []
    for name, result in {**case_results, **sensitivity_results}.items():
        array_path = output / f"{name}.npz"
        summary_path = output / f"{name}_summary.json"
        _create_npz(array_path, result)
        _create_json(
            summary_path,
            {
                "config": asdict(result.config),
                "drive": asdict(result.drive),
                "summary": result.summary,
            },
        )
        created_files.extend((array_path, summary_path))

    suite_path = output / "validation_summary.json"
    _create_json(suite_path, suite)
    created_files.append(suite_path)
    figure_path = output / "m1_diagnostic_summary.png"
    _create_diagnostic_figure(
        figure_path,
        case_results["active_only"],
        case_results["lumen_normal_only"],
    )
    created_files.append(figure_path)

    manifest_path = output / "manifest.json"
    manifest = {
        "schema_version": "paper2_m1_idealized_strip_manifest_v01",
        "status": suite["status"],
        "create_only": True,
        "files": {
            path.name: {
                "sha256": _file_digest(path),
                "bytes": path.stat().st_size,
            }
            for path in created_files
        },
    }
    _create_json(manifest_path, manifest)
    print(json.dumps({"output": str(output), **manifest}, indent=2))
    return 0 if suite["status"] == "passed_m1_human_gate_candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
