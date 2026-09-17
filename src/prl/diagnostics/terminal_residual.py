"""Diagnose the retained doublet terminal residual without running a solver."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from ..workspace import find_workspace


SOURCE_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915"
)
OUTPUT_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_terminal_residual_diagnosis_v01_20260915"
)
CONTRACT_RELATIVE = Path(
    "project_control/ventricle_terminal_residual_diagnosis_contract_v01.md"
)
CASES = ("END_DT0.02", "END_DT0.01", "SIDE_DT0.02", "SIDE_DT0.01")
TRAINING_WINDOWS = ((10.0, 15.0), (10.0, 17.0))
MODEL_NAMES = (
    "single_exponential_zero",
    "exponential_floor",
    "double_exponential_zero",
    "shifted_power_zero",
)


class TerminalResidualDiagnosisError(RuntimeError):
    """Raised before writing when retained evidence violates the contract."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> np.ndarray:
    data = np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))
    if not data.dtype.names or len(data) == 0:
        raise TerminalResidualDiagnosisError(f"empty or invalid CSV: {path}")
    for name in data.dtype.names:
        if not np.isfinite(data[name]).all():
            raise TerminalResidualDiagnosisError(f"non-finite field {name}: {path}")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_existing(workspace: Path, value: Path | str | None, default: Path) -> Path:
    candidate = workspace / default if value is None else Path(value)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(workspace.resolve(strict=True))
    except ValueError as error:
        raise TerminalResidualDiagnosisError("source must stay inside the workspace") from error
    return resolved


def _bounded_create_only(workspace: Path, value: Path | str | None) -> Path:
    candidate = workspace / OUTPUT_RELATIVE if value is None else Path(value)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    try:
        resolved.relative_to(workspace.resolve(strict=True))
    except ValueError as error:
        raise TerminalResidualDiagnosisError("output must stay inside the workspace") from error
    if resolved.exists():
        raise TerminalResidualDiagnosisError(f"create-only output exists: {resolved}")
    return resolved


def _model_function(name: str) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    if name == "single_exponential_zero":
        return lambda parameters, coordinate: np.exp(
            parameters[0] - np.exp(parameters[1]) * coordinate
        )
    if name == "exponential_floor":
        return lambda parameters, coordinate: parameters[0] + np.exp(
            parameters[1] - np.exp(parameters[2]) * coordinate
        )
    if name == "double_exponential_zero":
        return lambda parameters, coordinate: np.exp(
            parameters[0] - np.exp(parameters[1]) * coordinate
        ) + np.exp(parameters[2] - np.exp(parameters[3]) * coordinate)
    if name == "shifted_power_zero":
        return lambda parameters, coordinate: np.exp(parameters[0]) * (
            coordinate + np.exp(parameters[1])
        ) ** (-np.exp(parameters[2]))
    raise ValueError(f"unknown model: {name}")


def _fit_one_model(name: str, coordinate: np.ndarray, force: np.ndarray) -> dict[str, Any]:
    predict = _model_function(name)
    minimum = float(np.min(force))
    if name == "single_exponential_zero":
        starts = [[np.log(force[0]), np.log(rate)] for rate in (0.05, 0.1, 0.2)]
        bounds = ([-30.0, -14.0], [10.0, 2.0])
    elif name == "exponential_floor":
        starts = [
            [fraction * minimum, np.log(max(force[0], 1.0e-12)), np.log(rate)]
            for fraction in (0.0, 0.4, 0.8)
            for rate in (0.08, 0.15, 0.25)
        ]
        bounds = ([0.0, -30.0, -14.0], [minimum, 10.0, 2.0])
    elif name == "double_exponential_zero":
        floor_fit = _fit_one_model("exponential_floor", coordinate, force)
        floor = floor_fit["parameters"]["floor"]
        fast_amplitude = floor_fit["parameters"]["amplitude"]
        fast_rate = floor_fit["parameters"]["rate"]
        starts = [
            [
                np.log(max(fast_amplitude, 1.0e-12)),
                np.log(fast_rate),
                np.log(max(floor, 1.0e-12)),
                np.log(slow_rate),
            ]
            for slow_rate in (1.0e-6, 1.0e-4, 0.003, 0.015, 0.04)
        ]
        bounds = ([-30.0, -14.0, -30.0, -14.0], [10.0, 2.0, 10.0, 2.0])
    elif name == "shifted_power_zero":
        starts = [
            [np.log(force[0]), np.log(shift), np.log(power)]
            for shift in (1.0, 5.0, 20.0)
            for power in (0.5, 1.0, 2.0)
        ]
        bounds = ([-30.0, -8.0, -8.0], [30.0, 8.0, 4.0])
    else:  # pragma: no cover - guarded by MODEL_NAMES
        raise ValueError(name)

    best = None
    for start in starts:
        candidate = least_squares(
            lambda parameters: predict(parameters, coordinate) - force,
            start,
            bounds=bounds,
            max_nfev=50_000,
            xtol=1.0e-13,
            ftol=1.0e-13,
            gtol=1.0e-13,
        )
        residual = predict(candidate.x, coordinate) - force
        rss = float(np.dot(residual, residual))
        if best is None or rss < best[0]:
            best = (rss, candidate.x)
    assert best is not None
    raw = best[1]
    if name == "single_exponential_zero":
        parameters = {"amplitude": float(np.exp(raw[0])), "rate": float(np.exp(raw[1]))}
    elif name == "exponential_floor":
        parameters = {
            "floor": float(raw[0]),
            "amplitude": float(np.exp(raw[1])),
            "rate": float(np.exp(raw[2])),
        }
    elif name == "double_exponential_zero":
        terms = sorted(
            (
                (float(np.exp(raw[1])), float(np.exp(raw[0]))),
                (float(np.exp(raw[3])), float(np.exp(raw[2]))),
            )
        )
        parameters = {
            "slow_rate": terms[0][0],
            "slow_amplitude": terms[0][1],
            "fast_rate": terms[1][0],
            "fast_amplitude": terms[1][1],
        }
    else:
        parameters = {
            "amplitude": float(np.exp(raw[0])),
            "shift": float(np.exp(raw[1])),
            "power": float(np.exp(raw[2])),
        }
    return {"raw": raw, "parameters": parameters, "train_rss": best[0]}


def fit_tail_models(
    coordinate: np.ndarray,
    force: np.ndarray,
    train_start: float,
    train_end: float,
) -> list[dict[str, Any]]:
    """Fit frozen candidates and score only coordinates after the training window."""
    training = (coordinate >= train_start - 1.0e-12) & (coordinate <= train_end + 1.0e-12)
    testing = coordinate > train_end + 1.0e-12
    if int(training.sum()) < 20 or int(testing.sum()) < 20:
        raise TerminalResidualDiagnosisError("tail fit lacks training or held-out samples")
    records: list[dict[str, Any]] = []
    for name in MODEL_NAMES:
        fitted = _fit_one_model(name, coordinate[training], force[training])
        predicted = _model_function(name)(fitted["raw"], coordinate[testing])
        difference = predicted - force[testing]
        records.append(
            {
                "model": name,
                "train_start": train_start,
                "train_end": train_end,
                "train_samples": int(training.sum()),
                "test_samples": int(testing.sum()),
                "train_rss": fitted["train_rss"],
                "test_rmse": float(np.sqrt(np.mean(difference * difference))),
                "predicted_at_20": float(
                    _model_function(name)(fitted["raw"], np.array([20.0]))[0]
                ),
                "parameters": fitted["parameters"],
                "raw_parameters": [float(value) for value in fitted["raw"]],
            }
        )
    return records


def _mesh_measures(points: np.ndarray, triangles: np.ndarray) -> tuple[float, float]:
    first = points[triangles[:, 0]]
    second = points[triangles[:, 1]]
    third = points[triangles[:, 2]]
    area = float(np.linalg.norm(np.cross(second - first, third - first), axis=1).sum() / 2.0)
    volume = float(abs(np.einsum("ij,ij->i", first, np.cross(second, third)).sum() / 6.0))
    return area, volume


def _initial_isoperimetric(nodes: np.ndarray, faces: np.ndarray) -> dict[int, float]:
    result: dict[int, float] = {}
    for cell_id in (0, 1):
        rows = nodes[(nodes["snapshot"] == 0) & (nodes["cell"] == cell_id)]
        points = np.column_stack([rows[key] for key in ("x", "y", "z")])
        selected = faces[faces["cell"] == cell_id]
        triangles = np.column_stack([selected[key] for key in ("a", "b", "c")]).astype(int)
        area, volume = _mesh_measures(points, triangles)
        result[cell_id] = area**3 / volume**2
    return result


def _reconstruct_cell_passive(
    rows: np.ndarray,
    faces: np.ndarray,
    target_isoperimetric_ratio: float,
) -> tuple[np.ndarray, np.ndarray]:
    points = np.column_stack([rows[key] for key in ("x", "y", "z")])
    pressure_force = np.zeros_like(points)
    surface_force = np.zeros_like(points)
    triangles = np.column_stack([faces[key] for key in ("a", "b", "c")]).astype(int)
    area, volume = _mesh_measures(points, triangles)
    target_area = np.cbrt(target_isoperimetric_ratio * volume * volume)
    membrane_factor = -(0.050 / target_area) * (area / target_area - 1.0)
    force_factor = -0.160 + membrane_factor
    pressure = float(rows["pressure"][0])
    for triangle in triangles:
        first, second, third = points[triangle]
        cross_product = np.cross(second - first, third - first)
        face_area = float(np.linalg.norm(cross_product) / 2.0)
        normal = cross_product / (2.0 * face_area)
        for node_index in triangle:
            pressure_force[node_index] += normal * pressure * face_area / 3.0
        gradients = (
            -0.5 * np.cross(normal, second - third),
            -0.5 * np.cross(normal, third - first),
            -0.5 * np.cross(normal, first - second),
        )
        for node_index, gradient in zip(triangle, gradients, strict=True):
            surface_force[node_index] += gradient * force_factor
    return pressure_force, surface_force


def decompose_snapshot(
    rows: np.ndarray,
    faces: np.ndarray,
    target_isoperimetric: dict[int, float],
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Independently reconstruct passive forces and compute area-damped power."""
    total = np.column_stack([rows[key] for key in ("fx", "fy", "fz")])
    contact = np.column_stack([rows[key] for key in ("cfx", "cfy", "cfz")])
    skeleton = np.column_stack([rows[key] for key in ("sfx", "sfy", "sfz")])
    reaction = np.column_stack([rows[key] for key in ("rfx", "rfy", "rfz")])
    if np.any(rows["fixed"]) or float(np.linalg.norm(reaction, axis=1).max()) > 1.0e-14:
        raise TerminalResidualDiagnosisError("diagnosis requires the frozen all-free doublet")
    pressure = np.zeros_like(total)
    surface = np.zeros_like(total)
    for cell_id in (0, 1):
        indices = np.flatnonzero(rows["cell"].astype(int) == cell_id)
        cell_rows = rows[indices]
        cell_faces = faces[faces["cell"].astype(int) == cell_id]
        pressure_cell, surface_cell = _reconstruct_cell_passive(
            cell_rows, cell_faces, target_isoperimetric[cell_id]
        )
        pressure[indices] = pressure_cell
        surface[indices] = surface_cell
    stored_passive = total - contact - skeleton
    reconstructed_passive = pressure + surface
    reconstruction_error = stored_passive - reconstructed_passive
    relative_error = float(
        np.linalg.norm(reconstruction_error)
        / max(float(np.linalg.norm(stored_passive)), 1.0e-30)
    )
    area = rows["area"]
    dissipation_rate = float(np.sum(np.einsum("ij,ij->i", total, total) / area))
    components = {
        "skeleton": skeleton,
        "surface": surface,
        "pressure": pressure,
        "contact": contact,
    }
    powers = {
        name: float(np.sum(np.einsum("ij,ij->i", values, total) / area))
        for name, values in components.items()
    }
    magnitudes = np.linalg.norm(total, axis=1)
    maximum_index = int(np.argmax(magnitudes))
    record: dict[str, Any] = {
        "snapshot": int(rows["snapshot"][0]),
        "step": int(rows["step"][0]),
        "coordinate": float(rows["coordinate"][0]),
        "maximum_total_force": float(magnitudes[maximum_index]),
        "maximum_cell": int(rows["cell"][maximum_index]),
        "maximum_node": int(rows["node"][maximum_index]),
        "maximum_node_contact_force": float(np.linalg.norm(contact[maximum_index])),
        "contact_active_nodes": int(np.sum(np.linalg.norm(contact, axis=1) > 1.0e-12)),
        "instantaneous_dissipation_rate": dissipation_rate,
        "reconstruction_maximum_absolute_error": float(
            np.linalg.norm(reconstruction_error, axis=1).max()
        ),
        "reconstruction_relative_l2_error": relative_error,
    }
    for name, values in components.items():
        record[f"{name}_maximum_force"] = float(np.linalg.norm(values, axis=1).max())
        record[f"{name}_power"] = powers[name]
        record[f"{name}_power_fraction"] = powers[name] / dissipation_rate
        record[f"{name}_force_at_maximum_node"] = float(np.linalg.norm(values[maximum_index]))
    fields = {"total": total, **components}
    return record, fields


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        raise TerminalResidualDiagnosisError(f"refusing to write empty table: {path}")
    fieldnames = list(records[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, dict)
                    else value
                    for key, value in record.items()
                }
            )


def _style(axis: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.18, linewidth=0.6)


def _parameters_to_raw(model: str, parameters: dict[str, float]) -> np.ndarray:
    if model == "single_exponential_zero":
        return np.array([np.log(parameters["amplitude"]), np.log(parameters["rate"])])
    if model == "exponential_floor":
        return np.array(
            [parameters["floor"], np.log(parameters["amplitude"]), np.log(parameters["rate"])]
        )
    if model == "double_exponential_zero":
        return np.array(
            [
                np.log(parameters["fast_amplitude"]),
                np.log(parameters["fast_rate"]),
                np.log(parameters["slow_amplitude"]),
                np.log(parameters["slow_rate"]),
            ]
        )
    return np.array(
        [
            np.log(parameters["amplitude"]),
            np.log(parameters["shift"]),
            np.log(parameters["power"]),
        ]
    )


def _save_pair(figure: plt.Figure, figures: Path, name: str) -> list[Path]:
    outputs = [figures / f"{name}.png", figures / f"{name}.svg"]
    figure.savefig(outputs[0], dpi=180, bbox_inches="tight", facecolor="white")
    figure.savefig(outputs[1], bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return outputs


def _render_tail(
    case_data: dict[str, dict[str, np.ndarray]],
    tail_records: list[dict[str, Any]],
    figures: Path,
) -> list[Path]:
    figure, axes = plt.subplots(1, 2, figsize=(13.2, 4.8), constrained_layout=True)
    colors = {
        "single_exponential_zero": "#64748b",
        "exponential_floor": "#dc2626",
        "double_exponential_zero": "#7c3aed",
    }
    labels = {
        "single_exponential_zero": "single exp → 0",
        "exponential_floor": "exp + apparent floor",
        "double_exponential_zero": "two exp → 0 (slow mode)",
    }
    for axis, direction in zip(axes, ("END", "SIDE"), strict=True):
        fine = case_data[f"{direction}_DT0.01"]["states"]
        coarse = case_data[f"{direction}_DT0.02"]["states"]
        axis.semilogy(coarse["coordinate"], coarse["max_free_force"], color="#93c5fd", linewidth=1.0, label="dt 0.02 observed")
        axis.semilogy(fine["coordinate"], fine["max_free_force"], color="#0f172a", linewidth=1.5, label="dt 0.01 observed")
        grid = np.linspace(10.0, 20.0, 401)
        selected = [
            record
            for record in tail_records
            if record["case"] == f"{direction}_DT0.01"
            and record["train_start"] == 10.0
            and record["train_end"] == 15.0
            and record["model"] in colors
        ]
        for record in selected:
            raw = _parameters_to_raw(record["model"], record["parameters"])
            axis.semilogy(
                grid,
                _model_function(record["model"])(raw, grid),
                color=colors[record["model"]],
                linestyle="--" if record["model"] != "exponential_floor" else "-.",
                linewidth=1.4,
                label=labels[record["model"]],
            )
        axis.axvspan(15.0, 20.0, color="#f1f5f9", zorder=-2, label="held-out 15–20")
        axis.axhline(1.0e-3, color="#b91c1c", linestyle=":", linewidth=1.2, label="equilibrium gate")
        axis.set_xlim(10.0, 20.0)
        _style(axis, f"{direction}: finite-horizon tail", "Algorithmic coordinate (not time)", "Maximum free force")
    handles, legend_labels = axes[1].get_legend_handles_labels()
    figure.legend(handles, legend_labels, loc="outside lower center", ncol=3, frameon=False)
    return _save_pair(figure, figures, "tail_model_holdout")


def _render_power(component_records: list[dict[str, Any]], figures: Path) -> list[Path]:
    figure, axes = plt.subplots(1, 2, figsize=(13.2, 4.6), constrained_layout=True)
    colors = {"skeleton": "#dc2626", "surface": "#2563eb", "pressure": "#16a34a", "contact": "#7c3aed"}
    labels = {"skeleton": "cytoskeleton", "surface": "surface tension + area", "pressure": "volume pressure", "contact": "contact"}
    for axis, direction in zip(axes, ("END", "SIDE"), strict=True):
        selected = [record for record in component_records if record["case"] == f"{direction}_DT0.01"]
        coordinate = np.array([record["coordinate"] for record in selected])
        for component in ("skeleton", "surface", "pressure", "contact"):
            values = np.array([record[f"{component}_power_fraction"] for record in selected])
            axis.plot(coordinate, values, marker="o", color=colors[component], label=labels[component])
        axis.axhline(0.0, color="#334155", linewidth=0.8)
        _style(axis, f"{direction}: force power share", "Algorithmic coordinate (not time)", "P_component / dissipation")
    handles, legend_labels = axes[1].get_legend_handles_labels()
    figure.legend(handles, legend_labels, loc="outside lower center", ncol=4, frameon=False)
    return _save_pair(figure, figures, "force_component_power")


def _render_localization(
    case_data: dict[str, dict[str, np.ndarray]],
    figures: Path,
) -> list[Path]:
    figure, axes = plt.subplots(1, 2, figsize=(13.2, 4.8), constrained_layout=True)
    for axis, direction in zip(axes, ("END", "SIDE"), strict=True):
        nodes = case_data[f"{direction}_DT0.01"]["nodes"]
        snapshot = int(np.max(nodes["snapshot"]))
        rows = nodes[nodes["snapshot"] == snapshot]
        total = np.column_stack([rows[key] for key in ("fx", "fy", "fz")])
        contact = np.column_stack([rows[key] for key in ("cfx", "cfy", "cfz")])
        traction_proxy = np.linalg.norm(total, axis=1) / rows["area"]
        active = np.linalg.norm(contact, axis=1) > 1.0e-12
        image = axis.scatter(rows["x"], rows["y"], c=traction_proxy, s=13, cmap="magma")
        axis.scatter(rows["x"][active], rows["y"][active], facecolors="none", edgecolors="#22c55e", s=30, linewidths=0.8, label="contact-active")
        maximum = int(np.argmax(np.linalg.norm(total, axis=1)))
        axis.scatter(rows["x"][maximum], rows["y"][maximum], marker="*", color="#22d3ee", edgecolors="#0f172a", s=180, linewidths=0.8, label="max residual")
        axis.set_aspect("equal", adjustable="box")
        _style(axis, f"{direction}: coordinate 20", "x", "y")
        axis.legend(frameon=False, loc="best")
        colorbar = figure.colorbar(image, ax=axis, shrink=0.76)
        colorbar.set_label("|node force| / dual area (traction proxy)")
    return _save_pair(figure, figures, "terminal_residual_localization")


def diagnose_terminal_residual(
    workspace: Path | str | None = None,
    source: Path | str | None = None,
    output: Path | str | None = None,
) -> dict[str, Any]:
    """Create one bounded diagnosis package from retained solver evidence."""
    root = find_workspace(workspace)
    source_root = _bounded_existing(root, source, SOURCE_RELATIVE)
    output_root = _bounded_create_only(root, output)
    verdict = _json(source_root / "E/verdict.json")
    if verdict.get("failure_class") != "failed_equilibrium":
        raise TerminalResidualDiagnosisError("source is not the frozen failed-equilibrium result")

    required_names = (
        "run.json",
        "nodes.csv",
        "faces.csv",
        "states.csv",
        "cells.csv",
        "step_audits.csv",
        "separation.csv",
    )
    source_files = [source_root / "E/verdict.json"]
    case_data: dict[str, dict[str, np.ndarray]] = {}
    for case in CASES:
        case_root = source_root / "E" / case
        for name in required_names:
            path = case_root / name
            if not path.is_file():
                raise TerminalResidualDiagnosisError(f"missing source file: {path}")
            source_files.append(path)
        case_data[case] = {
            "nodes": _read_csv(case_root / "nodes.csv"),
            "faces": _read_csv(case_root / "faces.csv"),
            "states": _read_csv(case_root / "states.csv"),
            "cells": _read_csv(case_root / "cells.csv"),
        }

    provenance = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in source_files
    ]
    implementation_files = [
        root / CONTRACT_RELATIVE,
        Path(__file__).resolve(strict=True),
        root / "src/ventricle_simucell3d_m0/myo_contact_barrier_relaxation_v01.cpp",
        root / "src/ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp",
        root / "external/simucell3d/src/mesh/cell.cpp",
    ]
    implementation = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in implementation_files
    ]

    tail_records: list[dict[str, Any]] = []
    full_tail_floor: dict[str, float] = {}
    for case, data in case_data.items():
        states = data["states"]
        coordinate = states["coordinate"]
        force = states["max_free_force"]
        for start, end in TRAINING_WINDOWS:
            records = fit_tail_models(coordinate, force, start, end)
            for record in records:
                record["case"] = case
                tail_records.append(record)
        full = (coordinate >= 10.0 - 1.0e-12) & (coordinate <= 20.0 + 1.0e-12)
        floor_fit = _fit_one_model("exponential_floor", coordinate[full], force[full])
        full_tail_floor[case] = float(floor_fit["parameters"]["floor"])

    component_records: list[dict[str, Any]] = []
    terminal_fields: dict[str, dict[str, np.ndarray]] = {}
    for case, data in case_data.items():
        nodes, faces = data["nodes"], data["faces"]
        target_isoperimetric = _initial_isoperimetric(nodes, faces)
        for snapshot in np.unique(nodes["snapshot"]).astype(int):
            rows = nodes[nodes["snapshot"] == snapshot]
            record, fields = decompose_snapshot(rows, faces, target_isoperimetric)
            record["case"] = case
            component_records.append(record)
            if snapshot == int(np.max(nodes["snapshot"])):
                terminal_fields[case] = fields

    by_fit = {
        (record["case"], record["train_end"], record["model"]): record
        for record in tail_records
    }
    single_scale_inadequate = all(
        by_fit[(case, end, "exponential_floor")]["test_rmse"]
        <= 0.25 * by_fit[(case, end, "single_exponential_zero")]["test_rmse"]
        for case in CASES
        for _, end in TRAINING_WINDOWS
    )
    slow_zero_competitive = all(
        by_fit[(case, end, "double_exponential_zero")]["test_rmse"]
        <= 1.25 * by_fit[(case, end, "exponential_floor")]["test_rmse"]
        and by_fit[(case, end, "double_exponential_zero")]["parameters"]["slow_rate"]
        <= 1.0e-4
        for case in CASES
        for _, end in TRAINING_WINDOWS
    )
    terminal = [record for record in component_records if abs(record["coordinate"] - 20.0) <= 1.0e-8]
    contact_not_limiting = len(terminal) == 4 and all(
        record["maximum_node_contact_force"] <= 1.0e-12
        and abs(record["contact_power_fraction"]) <= 0.02
        for record in terminal
    )
    skeleton_dominant = len(terminal) == 4 and all(
        record["skeleton_power_fraction"] > 0.50 for record in terminal
    )
    reconstruction_maximum = max(
        record["reconstruction_maximum_absolute_error"] for record in component_records
    )
    reconstruction_relative = max(
        record["reconstruction_relative_l2_error"] for record in component_records
    )
    reconstruction_passed = reconstruction_maximum <= 1.0e-12 and reconstruction_relative <= 1.0e-12
    if not reconstruction_passed:
        raise TerminalResidualDiagnosisError("independent passive-force reconstruction failed")

    output_root.mkdir()
    figures = output_root / "figures"
    figures.mkdir()
    _write_csv(output_root / "tail_models.csv", tail_records)
    _write_csv(output_root / "component_snapshots.csv", component_records)
    figure_paths: list[Path] = []
    figure_paths.extend(_render_tail(case_data, tail_records, figures))
    figure_paths.extend(_render_power(component_records, figures))
    figure_paths.extend(_render_localization(case_data, figures))

    direction_floor_ranges = {
        direction: {
            "minimum": min(full_tail_floor[f"{direction}_DT0.02"], full_tail_floor[f"{direction}_DT0.01"]),
            "maximum": max(full_tail_floor[f"{direction}_DT0.02"], full_tail_floor[f"{direction}_DT0.01"]),
            "equilibrium_gate": 1.0e-3,
        }
        for direction in ("END", "SIDE")
    }
    diagnosis = {
        "schema_version": "prl.terminal_residual_diagnosis.v1",
        "status": "passed",
        "scientific_status": "blocked",
        "solver_calls": 0,
        "gpu": False,
        "source_result": source_root.relative_to(root).as_posix(),
        "output": output_root.relative_to(root).as_posix(),
        "analysis_checks": {
            "source_complete": True,
            "four_cases_present": len(case_data) == 4,
            "independent_passive_force_reconstruction": reconstruction_passed,
            "maximum_reconstruction_absolute_error": reconstruction_maximum,
            "maximum_reconstruction_relative_l2_error": reconstruction_relative,
        },
        "findings": {
            "single_scale_zero_asymptote_inadequate": single_scale_inadequate,
            "slow_zero_mode_competitive_with_positive_floor": slow_zero_competitive,
            "tail_classification": "unresolved_positive_floor_vs_slow_zero_mode"
            if single_scale_inadequate and slow_zero_competitive
            else "not_resolved_by_frozen_rules",
            "apparent_floor_from_full_10_to_20_fit": direction_floor_ranges,
            "contact_is_terminal_rate_limiting": False if contact_not_limiting else "not_resolved",
            "terminal_power_driver": "persistent_cytoskeleton_dominant"
            if skeleton_dominant
            else "not_resolved",
            "terminal_cases": terminal,
            "interpretation": (
                "The finite tail rejects a one-rate exponential to zero, but cannot distinguish "
                "a positive residual floor from an arbitrarily slow zero-asymptote mode. Contact "
                "is active geometrically yet is not co-located with the maximum residual and does "
                "not dominate terminal power. No automatic extension or physical revision follows."
            ),
        },
        "provenance": provenance,
        "implementation": implementation,
        "scope": "existing solver states only; algorithmic coordinate is not physiological time",
    }
    (output_root / "diagnosis.json").write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_files = [
        output_root / "tail_models.csv",
        output_root / "component_snapshots.csv",
        output_root / "diagnosis.json",
        *figure_paths,
    ]
    manifest = {
        "schema_version": "prl.terminal_residual_diagnosis.outputs.v1",
        "status": "passed",
        "actual_solver_states": True,
        "new_solver_calls": 0,
        "files": [
            {
                "path": path.relative_to(output_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in manifest_files
        ],
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    readme = """# 双胞末态残力诊断 v01

本包只重算既有四条轨迹，不含新求解器调用。程序诊断 `passed` 表示输入、力重建和输出完整；静态平衡与父Z1仍为 `blocked`。

- `figures/tail_model_holdout.png`：坐标10–15拟合、15–20留出；双指数慢模态可在有限区间模拟正平台，因此渐近类别未解析。
- `figures/force_component_power.png`：面积阻尼下各力对当前数值速度的功率份额。
- `figures/terminal_residual_localization.png`：坐标20真实网格上的残力牵引代理与接触活跃节点；牵引代理不是Cauchy应力。
- `diagnosis.json`、`tail_models.csv`、`component_snapshots.csv`：机器可读结果。

横轴均为算法松弛坐标，不是秒或生理时间。模型结构沿用源包 `figures/model_structure.png`。
"""
    (output_root / "README.md").write_text(readme, encoding="utf-8")
    return diagnosis

