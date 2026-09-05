"""Run the bounded Paper 2 science-first pilot.

This is an exploratory runner.  It varies only ECM relaxation time and ECM
thickness, plus the preregistered zero-drive and half-amplitude controls.  It
does not alter the production model, defaults, or formal Figure 2 gates.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np


SCHEMA = "paper2_science_pilot_v01"
EXPECTED_RELATIVE_OUTPUT = Path(
    "results/paper2_science_pilot/v01_20260905/numerical"
)
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
WALL_BUDGET_SECONDS = 7200.0
PHASE_AMPLITUDE_FLOOR = 1.0e-12
AMPLITUDE_REFINEMENT_TOLERANCE = 0.05
PHASE_REFINEMENT_TOLERANCE_DEG = 5.0


@dataclass(frozen=True)
class CaseSpec:
    key: str
    group: str
    de: float
    thickness_ratio: float
    case_id: str
    active_profile: str
    spatial_label: str
    steps_per_cycle: int
    activation_peak: float


def _number_token(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def _case(
    group: str,
    de: float,
    thickness_ratio: float,
    case_id: str,
    active_profile: str,
    spatial_label: str,
    steps_per_cycle: int,
    activation_peak: float = 0.10,
) -> CaseSpec:
    key = "__".join(
        (
            group,
            f"de{_number_token(de)}",
            f"h{_number_token(thickness_ratio)}",
            case_id.lower(),
            spatial_label.lower(),
            f"t{steps_per_cycle}",
            f"a{_number_token(activation_peak)}",
        )
    )
    return CaseSpec(
        key=key,
        group=group,
        de=de,
        thickness_ratio=thickness_ratio,
        case_id=case_id,
        active_profile=active_profile,
        spatial_label=spatial_label,
        steps_per_cycle=steps_per_cycle,
        activation_peak=activation_peak,
    )


def _case_specs() -> tuple[CaseSpec, ...]:
    cases: list[CaseSpec] = []
    for de in (0.02, 0.2, 2.0):
        for thickness_ratio in (0.1, 0.3, 0.6):
            cases.append(
                _case("basic", de, thickness_ratio, "A1", "uniform", "S2", 128)
            )
            cases.append(
                _case("basic", de, thickness_ratio, "S1", "S1", "S2", 128)
            )
    for de, thickness_ratio in ((0.02, 0.1), (0.2, 0.3), (2.0, 0.6)):
        cases.append(
            _case("space", de, thickness_ratio, "S1", "S1", "S3", 128)
        )
        cases.append(
            _case("time", de, thickness_ratio, "S1", "S1", "S2", 256)
        )
    cases.append(_case("zero", 0.2, 0.3, "P0", "uniform", "S2", 128))
    cases.append(
        _case("half", 0.2, 0.3, "A1", "uniform", "S2", 128, 0.05)
    )
    return tuple(cases)


CASE_SPECS = _case_specs()
HOLDOUT_SIGNATURES = {
    (0.07, 0.2, "A1"),
    (0.07, 0.2, "S1"),
    (0.7, 0.45, "A1"),
    (0.7, 0.45, "S1"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _create_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            _jsonable(payload),
            handle,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write("\n")


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                _jsonable(payload),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        handle.write("\n")


def _harmonic_coefficient(signal: np.ndarray, steps_per_cycle: int) -> np.ndarray:
    values = np.asarray(signal[..., :steps_per_cycle], dtype=np.float64)
    centered = values - np.mean(values, axis=-1, keepdims=True)
    return (2.0 / steps_per_cycle) * np.fft.rfft(centered, axis=-1)[..., 1]


def _relative_phase(
    coefficient: np.ndarray,
    activation_coefficient: complex,
    floor: float = PHASE_AMPLITUDE_FLOOR,
) -> np.ndarray:
    amplitude = np.abs(coefficient)
    phase = np.full(amplitude.shape, np.nan, dtype=np.float64)
    if abs(activation_coefficient) <= floor:
        return phase
    mask = amplitude > floor
    phase[mask] = np.angle(coefficient[mask] / activation_coefficient)
    return phase


def _peak_field_record(
    coefficient: np.ndarray,
    phase: np.ndarray,
    x_values: np.ndarray,
    field_kind: str,
) -> dict[str, Any]:
    amplitude = np.abs(coefficient)
    flat_index = int(np.argmax(amplitude))
    index = np.unravel_index(flat_index, amplitude.shape)
    phase_value = float(phase[index]) if np.isfinite(phase[index]) else None
    record: dict[str, Any] = {
        "field_kind": field_kind,
        "amplitude": float(amplitude[index]),
        "phase_relative_to_activation_rad": phase_value,
        "phase_relative_to_activation_deg": (
            math.degrees(phase_value) if phase_value is not None else None
        ),
        "phase_interpretable": phase_value is not None,
        "x": float(x_values[index[0]]),
    }
    if len(index) > 1:
        record["component"] = ("x", "y")[index[1]]
    return record


def _scalar_harmonic_record(
    signal: np.ndarray,
    activation_coefficient: complex,
    steps_per_cycle: int,
) -> tuple[dict[str, Any], complex]:
    coefficient = complex(_harmonic_coefficient(signal, steps_per_cycle))
    amplitude = abs(coefficient)
    if amplitude > PHASE_AMPLITUDE_FLOOR and abs(activation_coefficient) > PHASE_AMPLITUDE_FLOOR:
        phase_value: float | None = float(
            np.angle(coefficient / activation_coefficient)
        )
    else:
        phase_value = None
    return (
        {
            "coefficient_real": float(coefficient.real),
            "coefficient_imag": float(coefficient.imag),
            "amplitude": float(amplitude),
            "phase_relative_to_activation_rad": phase_value,
            "phase_relative_to_activation_deg": (
                math.degrees(phase_value) if phase_value is not None else None
            ),
            "phase_interpretable": phase_value is not None,
        },
        coefficient,
    )


def _extract_observables(system: Any, endpoint: Any, spec: CaseSpec) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    steps = spec.steps_per_cycle
    arrays = endpoint.arrays
    activation = np.asarray(arrays["activation_two_cycles"], dtype=np.float64)
    activation_coefficient = complex(_harmonic_coefficient(activation, steps))
    states = np.asarray(arrays["state_two_cycles"], dtype=np.float64)
    endocardial_displacement = np.asarray(
        system.endocardium_transform @ states
    ).reshape(len(system.interface_weights), 2, -1)
    x_nodes = np.asarray(
        system.myocardium_mesh.dof_coordinates[system.myocardium_mesh.top_nodes, 0],
        dtype=np.float64,
    )
    x_segments = 0.5 * (x_nodes[:-1] + x_nodes[1:])
    endocardial_axial_strain = np.diff(endocardial_displacement[:, 0, :], axis=0)
    endocardial_axial_strain /= np.diff(x_nodes)[:, None]
    myo_traction = np.asarray(
        arrays["myocardium_ecm_traction_two_cycles"], dtype=np.float64
    ).reshape(len(x_nodes), 2, -1)
    endo_traction = np.asarray(
        arrays["endocardium_ecm_traction_two_cycles"], dtype=np.float64
    ).reshape(len(x_nodes), 2, -1)

    shortening_record, shortening_coefficient = _scalar_harmonic_record(
        np.asarray(arrays["limited_shortening_two_cycles"], dtype=np.float64),
        activation_coefficient,
        steps,
    )
    strain_coefficient = _harmonic_coefficient(endocardial_axial_strain, steps)
    myo_traction_coefficient = _harmonic_coefficient(myo_traction, steps)
    endo_traction_coefficient = _harmonic_coefficient(endo_traction, steps)
    state_coefficient = _harmonic_coefficient(states, steps)
    strain_phase = _relative_phase(strain_coefficient, activation_coefficient)
    myo_traction_phase = _relative_phase(
        myo_traction_coefficient, activation_coefficient
    )
    endo_traction_phase = _relative_phase(
        endo_traction_coefficient, activation_coefficient
    )

    summary = endpoint.summary
    ledger = summary["ledger"]
    observables = {
        "definitions": {
            "fundamental": "2/N times first rFFT coefficient after temporal mean removal",
            "phase_reference": "activation fundamental; omitted below amplitude floor",
            "endocardial_local_strain": "first difference of axial chain displacement divided by reference segment length",
            "traction_sign": "production convention: positive on first named domain",
            "active_work": "raw signed production discrete-ledger active work",
        },
        "activation": {
            "fundamental_coefficient_real": float(activation_coefficient.real),
            "fundamental_coefficient_imag": float(activation_coefficient.imag),
            "fundamental_amplitude": float(abs(activation_coefficient)),
        },
        "overall_shortening": {
            **shortening_record,
            "peak": float(summary["peak_limited_shortening"]),
            "minimum": float(summary["minimum_limited_shortening"]),
            "waveform_l2": float(summary["shortening_waveform_l2"]),
        },
        "endocardial_local_axial_strain_peak_fundamental": _peak_field_record(
            strain_coefficient, strain_phase, x_segments, "segment_axial_strain"
        ),
        "myocardium_ecm_traction_peak_fundamental": _peak_field_record(
            myo_traction_coefficient,
            myo_traction_phase,
            x_nodes,
            "nodal_vector_traction",
        ),
        "endocardium_ecm_traction_peak_fundamental": _peak_field_record(
            endo_traction_coefficient,
            endo_traction_phase,
            x_nodes,
            "nodal_vector_traction",
        ),
        "state_fundamental_l2_amplitude": float(np.linalg.norm(state_coefficient)),
        "work_and_dissipation": {
            "active_input_work_raw": float(ledger["total_active_work"]),
            "active_input_work_magnitude": abs(float(ledger["total_active_work"])),
            "ecm_sls_dissipation": float(ledger["total_sls_dissipation"]),
            "other_drag_dissipation": float(ledger["total_drag_dissipation"]),
            "external_support_work": float(ledger["total_external_support_work"]),
            "lumen_work": float(ledger["total_lumen_work"]),
            "cycle_discrete_energy_change": float(
                ledger["cycle_discrete_energy_change"]
            ),
        },
        "existing_summary_observables": {
            "peak_absolute_mean_endocardial_tangential_displacement": float(
                summary["peak_absolute_mean_endocardial_tangential_displacement"]
            ),
            "peak_absolute_mean_endocardial_normal_displacement": float(
                summary["peak_absolute_mean_endocardial_normal_displacement"]
            ),
            "maximum_myocardium_ecm_traction": float(
                summary["maximum_myocardium_ecm_traction"]
            ),
            "maximum_endocardium_ecm_traction": float(
                summary["maximum_endocardium_ecm_traction"]
            ),
            "maximum_ecm_von_mises_proxy": float(
                summary["maximum_ecm_von_mises_proxy"]
            ),
        },
    }
    derived_arrays = {
        "x_interface_nodes": x_nodes,
        "x_endocardial_segments": x_segments,
        "endocardial_displacement_two_cycles": endocardial_displacement,
        "endocardial_axial_strain_two_cycles": endocardial_axial_strain,
        "endocardial_axial_strain_fundamental_real": strain_coefficient.real,
        "endocardial_axial_strain_fundamental_imag": strain_coefficient.imag,
        "endocardial_axial_strain_fundamental_amplitude": np.abs(
            strain_coefficient
        ),
        "endocardial_axial_strain_phase_relative_to_activation_rad": np.nan_to_num(
            strain_phase, nan=0.0
        ),
        "endocardial_axial_strain_phase_interpretable": np.isfinite(strain_phase),
        "myocardium_ecm_traction_fundamental_real": myo_traction_coefficient.real,
        "myocardium_ecm_traction_fundamental_imag": myo_traction_coefficient.imag,
        "myocardium_ecm_traction_fundamental_amplitude": np.abs(
            myo_traction_coefficient
        ),
        "myocardium_ecm_traction_phase_relative_to_activation_rad": np.nan_to_num(
            myo_traction_phase, nan=0.0
        ),
        "myocardium_ecm_traction_phase_interpretable": np.isfinite(
            myo_traction_phase
        ),
        "endocardium_ecm_traction_fundamental_real": endo_traction_coefficient.real,
        "endocardium_ecm_traction_fundamental_imag": endo_traction_coefficient.imag,
        "endocardium_ecm_traction_fundamental_amplitude": np.abs(
            endo_traction_coefficient
        ),
        "endocardium_ecm_traction_phase_relative_to_activation_rad": np.nan_to_num(
            endo_traction_phase, nan=0.0
        ),
        "endocardium_ecm_traction_phase_interpretable": np.isfinite(
            endo_traction_phase
        ),
        "state_fundamental_real": state_coefficient.real,
        "state_fundamental_imag": state_coefficient.imag,
        "shortening_fundamental_real_imag": np.asarray(
            (shortening_coefficient.real, shortening_coefficient.imag),
            dtype=np.float64,
        ),
    }
    return observables, derived_arrays


def _amplitude_difference(first: float, second: float) -> float:
    return abs(first - second) / max(abs(first), abs(second), PHASE_AMPLITUDE_FLOOR)


def _phase_difference_deg(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    difference = math.degrees(math.atan2(math.sin(first - second), math.cos(first - second)))
    return abs(difference)


def _metric_pairs(record: dict[str, Any]) -> dict[str, tuple[float, float | None]]:
    observables = record["observables"]
    return {
        "overall_shortening": (
            observables["overall_shortening"]["amplitude"],
            observables["overall_shortening"]["phase_relative_to_activation_rad"],
        ),
        "endocardial_local_axial_strain_peak": (
            observables["endocardial_local_axial_strain_peak_fundamental"]["amplitude"],
            observables["endocardial_local_axial_strain_peak_fundamental"]["phase_relative_to_activation_rad"],
        ),
        "myocardium_ecm_traction_peak": (
            observables["myocardium_ecm_traction_peak_fundamental"]["amplitude"],
            observables["myocardium_ecm_traction_peak_fundamental"]["phase_relative_to_activation_rad"],
        ),
        "endocardium_ecm_traction_peak": (
            observables["endocardium_ecm_traction_peak_fundamental"]["amplitude"],
            observables["endocardium_ecm_traction_peak_fundamental"]["phase_relative_to_activation_rad"],
        ),
    }


def _resolution_comparison(
    reference: dict[str, Any], candidate: dict[str, Any], comparison: str
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name, (reference_amplitude, reference_phase) in _metric_pairs(reference).items():
        candidate_amplitude, candidate_phase = _metric_pairs(candidate)[name]
        amplitude_change = _amplitude_difference(reference_amplitude, candidate_amplitude)
        phase_change = _phase_difference_deg(reference_phase, candidate_phase)
        phase_pass = (
            None if phase_change is None else phase_change <= PHASE_REFINEMENT_TOLERANCE_DEG
        )
        metrics[name] = {
            "reference_amplitude": reference_amplitude,
            "candidate_amplitude": candidate_amplitude,
            "relative_amplitude_change": amplitude_change,
            "amplitude_tolerance": AMPLITUDE_REFINEMENT_TOLERANCE,
            "amplitude_pass": amplitude_change <= AMPLITUDE_REFINEMENT_TOLERANCE,
            "reference_phase_rad": reference_phase,
            "candidate_phase_rad": candidate_phase,
            "absolute_phase_change_deg": phase_change,
            "phase_tolerance_deg": PHASE_REFINEMENT_TOLERANCE_DEG,
            "phase_interpretable": phase_change is not None,
            "phase_pass": phase_pass,
        }
    passed = all(
        item["amplitude_pass"] and item["phase_pass"] is not False
        for item in metrics.values()
    )
    return {"comparison": comparison, "pass": passed, "metrics": metrics}


def _scaling_check(full: dict[str, Any], half: dict[str, Any]) -> dict[str, Any]:
    amplitude_values = {
        "state_fundamental_l2_amplitude": (
            full["observables"]["state_fundamental_l2_amplitude"],
            half["observables"]["state_fundamental_l2_amplitude"],
        ),
        **{
            name: (
                _metric_pairs(full)[name][0],
                _metric_pairs(half)[name][0],
            )
            for name in _metric_pairs(full)
        },
    }
    work_values = {
        name: (
            abs(full["observables"]["work_and_dissipation"][name]),
            abs(half["observables"]["work_and_dissipation"][name]),
        )
        for name in (
            "active_input_work_raw",
            "ecm_sls_dissipation",
            "other_drag_dissipation",
        )
    }
    amplitude_checks: dict[str, Any] = {}
    for name, (full_value, half_value) in amplitude_values.items():
        ratio = half_value / max(full_value, PHASE_AMPLITUDE_FLOOR)
        amplitude_checks[name] = {
            "full": full_value,
            "half": half_value,
            "ratio": ratio,
            "expected_ratio": 0.5,
            "absolute_error": abs(ratio - 0.5),
            "pass": abs(ratio - 0.5) <= 1.0e-8,
        }
    work_checks: dict[str, Any] = {}
    for name, (full_value, half_value) in work_values.items():
        ratio = half_value / max(full_value, PHASE_AMPLITUDE_FLOOR)
        work_checks[name] = {
            "full_magnitude": full_value,
            "half_magnitude": half_value,
            "ratio": ratio,
            "expected_ratio": 0.25,
            "absolute_error": abs(ratio - 0.25),
            "pass": abs(ratio - 0.25) <= 1.0e-8,
        }
    return {
        "pass": all(item["pass"] for item in (*amplitude_checks.values(), *work_checks.values())),
        "amplitude_checks": amplitude_checks,
        "work_and_dissipation_checks": work_checks,
    }


def _source_hashes(repo_root: Path) -> dict[str, str]:
    paths = (
        "src/paper2_hybrid/config.py",
        "src/paper2_hybrid/model.py",
        "src/paper2_hybrid/numerics.py",
        "src/paper2_hybrid/validation.py",
        "scripts/run_paper2_science_pilot_v01.py",
    )
    return {path: _sha256(repo_root / path) for path in paths}


def _validate_plan() -> None:
    if len(CASE_SPECS) != 26:
        raise RuntimeError(f"expected 26 non-holdout cases, got {len(CASE_SPECS)}")
    if len({spec.key for spec in CASE_SPECS}) != len(CASE_SPECS):
        raise RuntimeError("case keys are not unique")
    counts = {group: sum(spec.group == group for spec in CASE_SPECS) for group in ("basic", "space", "time", "zero", "half")}
    if counts != {"basic": 18, "space": 3, "time": 3, "zero": 1, "half": 1}:
        raise RuntimeError(f"case group count drift: {counts}")
    actual_signatures = {(spec.de, spec.thickness_ratio, spec.case_id) for spec in CASE_SPECS}
    if actual_signatures & HOLDOUT_SIGNATURES:
        raise RuntimeError("holdout leakage into non-holdout case plan")


def _plot_overview(output_root: Path, records: list[dict[str, Any]]) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = output_root / "science_pilot_overview.png"
    if path.exists():
        raise FileExistsError(path)
    basic = [record for record in records if record["spec"]["group"] == "basic"]
    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.5), constrained_layout=True)
    panels = (
        ("overall_shortening", "Global shortening amplitude"),
        ("endocardial_local_axial_strain_peak", "Peak local endocardial strain amplitude"),
        ("endocardium_ecm_traction_peak", "Peak endocardium-ECM traction amplitude"),
    )
    colors = {0.02: "#2b6cb0", 0.2: "#d97706", 2.0: "#9b2c2c"}
    markers = {"A1": "o", "S1": "s"}
    for axis, (metric, title) in zip(axes.flat[:3], panels):
        for case_id in ("A1", "S1"):
            for de in (0.02, 0.2, 2.0):
                selected = sorted(
                    (
                        record
                        for record in basic
                        if record["spec"]["case_id"] == case_id
                        and record["spec"]["de"] == de
                    ),
                    key=lambda item: item["spec"]["thickness_ratio"],
                )
                x_values = [item["spec"]["thickness_ratio"] for item in selected]
                y_values = [_metric_pairs(item)[metric][0] for item in selected]
                axis.plot(
                    x_values,
                    y_values,
                    color=colors[de],
                    marker=markers[case_id],
                    linestyle="-" if case_id == "A1" else "--",
                    label=f"{case_id}, De={de:g}",
                )
        axis.set_title(title)
        axis.set_xlabel("ECM thickness ratio H")
        axis.set_ylabel("fundamental amplitude")
        axis.grid(alpha=0.25)
    axis = axes.flat[3]
    for case_id in ("A1", "S1"):
        for de in (0.02, 0.2, 2.0):
            selected = sorted(
                (
                    record
                    for record in basic
                    if record["spec"]["case_id"] == case_id
                    and record["spec"]["de"] == de
                ),
                key=lambda item: item["spec"]["thickness_ratio"],
            )
            x_values = [item["spec"]["thickness_ratio"] for item in selected]
            fractions = []
            for item in selected:
                work = item["observables"]["work_and_dissipation"]
                total = work["ecm_sls_dissipation"] + work["other_drag_dissipation"]
                fractions.append(work["ecm_sls_dissipation"] / max(total, 1.0e-30))
            axis.plot(
                x_values,
                fractions,
                color=colors[de],
                marker=markers[case_id],
                linestyle="-" if case_id == "A1" else "--",
                label=f"{case_id}, De={de:g}",
            )
    axis.set_title("ECM viscoelastic share of total dissipation")
    axis.set_xlabel("ECM thickness ratio H")
    axis.set_ylabel("SLS / (SLS + drag)")
    axis.set_ylim(0.0, 1.05)
    axis.grid(alpha=0.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.01),
        ncol=6,
        fontsize=8,
    )
    figure.suptitle("Paper 2 science-first pilot: non-holdout cases")
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def run(output_root: Path, code_version: str) -> int:
    _validate_plan()
    repo_root = Path(__file__).resolve().parents[1]
    expected_root = (repo_root / EXPECTED_RELATIVE_OUTPUT).resolve()
    if output_root.resolve() != expected_root:
        raise RuntimeError(f"output boundary mismatch: {output_root.resolve()} != {expected_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise RuntimeError("create-only numerical output root is not empty")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise RuntimeError(f"single-CPU environment drift: {name}={os.environ.get(name)!r}")
    image_id = os.environ.get("PAPER2_IMAGE_ID", "")
    if image_id != EXPECTED_IMAGE_ID:
        raise RuntimeError(f"container image identity drift: {image_id!r}")

    from paper2_hybrid.config import ACTIVE_CONFIG
    from paper2_hybrid.model import build_system
    from paper2_hybrid.numerics import endpoint_structural_gate, simulate_endpoint
    from paper2_hybrid.validation import (
        global_structural_checks,
        interface_action_reaction_manufactured_check,
    )
    import scipy
    import dolfinx

    start = time.perf_counter()
    event_path = output_root / "events.jsonl"
    manifest = {
        "schema": SCHEMA,
        "status": "RUNNING",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "exploratory_scientific_feasibility",
        "code_version": code_version,
        "source_hashes": _source_hashes(repo_root),
        "container": {
            "image": "dolfinx/dolfinx:v0.11.0",
            "image_id": image_id,
            "container_name": os.environ.get("PAPER2_CONTAINER_NAME"),
            "network": "none",
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "root_filesystem": "read_only",
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "dolfinx": dolfinx.__version__,
            "platform": platform.platform(),
        },
        "wall_budget_seconds": WALL_BUDGET_SECONDS,
        "case_count": len(CASE_SPECS),
        "cases": [asdict(spec) for spec in CASE_SPECS],
        "holdouts": {
            "status": "LOCKED_NOT_RUN",
            "signatures": [list(item) for item in sorted(HOLDOUT_SIGNATURES)],
        },
        "parameter_rule": {
            "period_fixed": ACTIVE_CONFIG.period,
            "ecm_relaxation_time": "De * period",
            "ecm_thickness": "H * length",
            "not_a_frequency_scan": True,
        },
        "scientific_cautions": {
            "translation_invariance": "not assumed; affine macro displacement, bottom support and body drag require separate theoretical interpretation",
            "a1_s1_equality": "not assumed and not used as a pass condition",
            "uniform_activation_uniform_field": "not assumed",
            "p0": "constructed zero state and output-pipeline check, not an independent solve validation",
            "interface_action_reaction": "structural identity check; the production endpoint summary uses a fixed zero numerator rather than an independent force-balance measurement",
        },
    }
    _create_json(output_root / "run_manifest.json", manifest)
    _append_event(event_path, {"event": "run_started", "elapsed_seconds": 0.0})

    manufactured = interface_action_reaction_manufactured_check()
    _create_json(output_root / "manufactured_interface_check.json", manufactured)
    if not manufactured["pass"]:
        raise RuntimeError("interface action-reaction manufactured check failed")

    case_dir = output_root / "cases"
    case_dir.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    structural_failures: list[str] = []
    for position, spec in enumerate(CASE_SPECS, start=1):
        elapsed_before = time.perf_counter() - start
        if elapsed_before >= WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second cumulative wall budget reached before next case")
        print(f"CASE_START {position}/26 {spec.key}", flush=True)
        case_start = time.perf_counter()
        config = replace(
            ACTIVE_CONFIG,
            ecm_thickness=spec.thickness_ratio * ACTIVE_CONFIG.length,
            ecm_relaxation_time=spec.de * ACTIVE_CONFIG.period,
            activation_peak=spec.activation_peak,
        ).checked()
        system = build_system(
            spatial_label=spec.spatial_label,
            active_profile=spec.active_profile,
            config=config,
        )
        system_checks = global_structural_checks(system)
        if not all(item["pass"] for item in system_checks.values()):
            raise RuntimeError(f"global structural check failed for {spec.key}")
        endpoint = simulate_endpoint(
            system=system,
            case_id=spec.case_id,
            steps_per_cycle=spec.steps_per_cycle,
        )
        structural_gate = endpoint_structural_gate(endpoint.summary)
        if not structural_gate["pass"]:
            structural_failures.append(spec.key)
        observables, derived_arrays = _extract_observables(system, endpoint, spec)
        all_arrays = {
            **{name: np.asarray(values) for name, values in endpoint.arrays.items()},
            **derived_arrays,
        }
        if not all(np.all(np.isfinite(values)) for values in all_arrays.values()):
            raise RuntimeError(f"non-finite array in {spec.key}")
        array_path = case_dir / f"{spec.key}.npz"
        if array_path.exists():
            raise FileExistsError(array_path)
        np.savez_compressed(array_path, **all_arrays)
        array_hash = _sha256(array_path)
        case_elapsed = time.perf_counter() - case_start
        record = {
            "schema": "paper2_science_pilot_case_v01",
            "spec": asdict(spec),
            "actual_config": {
                "length": config.length,
                "period": config.period,
                "ecm_thickness": config.ecm_thickness,
                "ecm_relaxation_time": config.ecm_relaxation_time,
                "activation_peak": config.activation_peak,
                "config_digest": config.digest(),
            },
            "system": {
                "state_size": system.state_size,
                "spatial_label": system.spatial_label,
                "active_profile": system.active_profile,
                "active_profile_average": system.active_profile_average,
            },
            "system_checks": system_checks,
            "endpoint_structural_gate": structural_gate,
            "structural_gate_evidence_boundaries": {
                "p0_direct_solver": (
                    "constructed zero residual; not an independent solve validation"
                    if spec.case_id == "P0"
                    else "nonzero production direct-solve assurance"
                ),
                "interface_action_reaction": "structural identity check with fixed zero numerator in the production endpoint summary",
            },
            "endpoint_summary": endpoint.summary,
            "observables": observables,
            "arrays": {
                "path": array_path.relative_to(output_root).as_posix(),
                "sha256": array_hash,
                "key_count": len(all_arrays),
            },
            "runtime_seconds": case_elapsed,
            "cumulative_elapsed_seconds": time.perf_counter() - start,
        }
        case_json_path = case_dir / f"{spec.key}.json"
        _create_json(case_json_path, record)
        record["case_json"] = {
            "path": case_json_path.relative_to(output_root).as_posix(),
            "sha256": _sha256(case_json_path),
        }
        records.append(record)
        _append_event(
            event_path,
            {
                "event": "case_completed",
                "position": position,
                "case_key": spec.key,
                "structural_pass": structural_gate["pass"],
                "runtime_seconds": case_elapsed,
                "cumulative_elapsed_seconds": time.perf_counter() - start,
            },
        )
        print(
            f"CASE_DONE {position}/26 {spec.key} seconds={case_elapsed:.3f} "
            f"structural_pass={structural_gate['pass']}",
            flush=True,
        )
        del endpoint, system, all_arrays, derived_arrays
        gc.collect()
        if time.perf_counter() - start > WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second cumulative wall budget exceeded after case")

    by_key = {record["spec"]["key"]: record for record in records}
    zero_record = next(record for record in records if record["spec"]["group"] == "zero")
    zero_check = {
        "case_key": zero_record["spec"]["key"],
        "maximum_state_norm": zero_record["endpoint_summary"]["maximum_state_norm"],
        "threshold": ACTIVE_CONFIG.zero_state_absolute_tolerance,
        "pass": (
            zero_record["endpoint_summary"]["maximum_state_norm"]
            <= ACTIVE_CONFIG.zero_state_absolute_tolerance
        ),
        "evidence_role": "constructed zero response and output-pipeline check; not an independent solver validation",
    }
    full_record = next(
        record
        for record in records
        if record["spec"]["group"] == "basic"
        and record["spec"]["de"] == 0.2
        and record["spec"]["thickness_ratio"] == 0.3
        and record["spec"]["case_id"] == "A1"
    )
    half_record = next(record for record in records if record["spec"]["group"] == "half")
    half_scaling = _scaling_check(full_record, half_record)

    resolution_checks: list[dict[str, Any]] = []
    for de, thickness_ratio in ((0.02, 0.1), (0.2, 0.3), (2.0, 0.6)):
        reference = next(
            record
            for record in records
            if record["spec"]["group"] == "basic"
            and record["spec"]["de"] == de
            and record["spec"]["thickness_ratio"] == thickness_ratio
            and record["spec"]["case_id"] == "S1"
        )
        spatial = next(
            record
            for record in records
            if record["spec"]["group"] == "space"
            and record["spec"]["de"] == de
            and record["spec"]["thickness_ratio"] == thickness_ratio
        )
        temporal = next(
            record
            for record in records
            if record["spec"]["group"] == "time"
            and record["spec"]["de"] == de
            and record["spec"]["thickness_ratio"] == thickness_ratio
        )
        resolution_checks.append(
            {
                "de": de,
                "thickness_ratio": thickness_ratio,
                **_resolution_comparison(reference, spatial, "S2_T128_to_S3_T128"),
            }
        )
        resolution_checks.append(
            {
                "de": de,
                "thickness_ratio": thickness_ratio,
                **_resolution_comparison(reference, temporal, "S2_T128_to_S2_T256"),
            }
        )

    plot_path = _plot_overview(output_root, records)
    all_resolution_pass = all(item["pass"] for item in resolution_checks)
    all_structural_pass = not structural_failures
    scientific_checks_pass = zero_check["pass"] and half_scaling["pass"] and all_resolution_pass
    status = (
        "COMPLETED_ALL_EXPLORATORY_CHECKS_PASS"
        if all_structural_pass and scientific_checks_pass
        else "COMPLETED_WITH_RECORDED_CHECK_FAILURES"
    )
    final_summary = {
        "schema": "paper2_science_pilot_summary_v01",
        "status": status,
        "evidence_level": "exploratory_scientific_feasibility",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(records),
        "group_counts": {
            group: sum(record["spec"]["group"] == group for record in records)
            for group in ("basic", "space", "time", "zero", "half")
        },
        "holdouts": "LOCKED_NOT_RUN",
        "all_structural_pass": all_structural_pass,
        "structural_failures": structural_failures,
        "zero_drive_check": zero_check,
        "half_amplitude_scaling": half_scaling,
        "resolution_checks": resolution_checks,
        "all_resolution_checks_pass": all_resolution_pass,
        "scientific_checks_pass": scientific_checks_pass,
        "total_elapsed_seconds": time.perf_counter() - start,
        "wall_budget_seconds": WALL_BUDGET_SECONDS,
        "overview_plot": {
            "path": plot_path.relative_to(output_root).as_posix(),
            "sha256": _sha256(plot_path),
        },
        "cases": [
            {
                "key": record["spec"]["key"],
                "group": record["spec"]["group"],
                "structural_pass": record["endpoint_structural_gate"]["pass"],
                "runtime_seconds": record["runtime_seconds"],
                "case_json": record["case_json"],
                "arrays": record["arrays"],
                "observables": record["observables"],
            }
            for record in records
        ],
        "claim_boundary": {
            "not_formal_figure2_certification": True,
            "not_continuous_time_analytic_truth": True,
            "not_physiological_calibration": True,
            "not_disease_prediction": True,
            "not_frequency_scan": True,
            "s1_is_now_seen_exploratory_control": True,
            "a1_s1_equality_not_assumed": True,
            "uniform_activation_uniform_field_not_assumed": True,
            "translation_invariance_requires_separate_theory_check": True,
            "p0_and_interface_balance_are_not_independent_solve_measurements": True,
        },
    }
    _create_json(output_root / "summary.json", final_summary)
    _append_event(
        event_path,
        {
            "event": "run_completed",
            "status": status,
            "case_count": len(records),
            "total_elapsed_seconds": time.perf_counter() - start,
        },
    )
    print(
        f"RUN_DONE cases={len(records)} status={status} "
        f"seconds={time.perf_counter() - start:.3f}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-version", required=True)
    arguments = parser.parse_args()
    return run(arguments.output, arguments.code_version)


if __name__ == "__main__":
    sys.exit(main())
