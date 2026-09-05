"""Run the preregistered 12-endpoint impedance-shift experiment.

Only the endocardial axial stiffness and the six frozen ECM thicknesses vary.
The production FEM and previously accepted extraction/transfer helpers are
reused without modification.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np

import analyze_paper2_mean_normal_transfer_v01 as normal_transfer
import run_paper2_science_pilot_v01 as pilot
import run_paper2_transverse_notch_v02 as notch


SCHEMA = "paper2_impedance_shift_v01"
CASE_SCHEMA = "paper2_impedance_shift_case_v01"
SUMMARY_SCHEMA = "paper2_impedance_shift_summary_v01"
PREDICTION_COMMIT = "225c5a9dc7ecfc45e2c1b4a54d40a69f7dacecc9"
EXPECTED_RUNTIME_SOURCE_VERSION = PREDICTION_COMMIT
PREDICTION_PATH = Path("results/paper2_science_pilot/v01_20260905/science_brief.md")
PREDICTION_SHA256 = "2b677d44a42a863e9e38456cb66520c88130c66983aa58bb60045441718bb319"
EXPECTED_PROJECT_ROOT = Path("/workspace")
EXPECTED_OUTPUT_ROOT = Path("/output")
HOST_OUTPUT_RELATIVE = "results/paper2_impedance_shift/v01_20260905"
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
EXPECTED_CONTAINER_NAME = "prl-paper2-impedance-shift-v01-20260905"
EXPECTED_PYTHONPATH = (
    "/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:"
    "/usr/local/lib:"
)
PRIOR_FEM_SUMMARY = Path("results/paper2_transverse_notch/v02_20260905/summary.json")
PRIOR_FEM_SUMMARY_SHA256 = (
    "7b8d7b51be37f1d0693a7ffc14cafa7fc348dc26bc1a8281bae85f95a40e3125"
)
PRIOR_FEM_CUMULATIVE_SECONDS = 104.44878690800397
EXPECTED_SOURCE_HASHES = {
    "src/paper2_hybrid/config.py": "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe",
    "src/paper2_hybrid/model.py": "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800",
    "src/paper2_hybrid/numerics.py": "620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4",
    "src/paper2_hybrid/validation.py": "6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5",
    "scripts/run_paper2_science_pilot_v01.py": "2675b91436dacc43ed9ad3121b8a24dfd8826f93440db184bbd7abad597002e7",
    "scripts/run_paper2_transverse_notch_v02.py": "13f0699cb28e7b2ee2c14e90811b75f55c43b0ab82279b2e1687d886a72e9d79",
    "scripts/analyze_paper2_mean_normal_transfer_v01.py": "5b6e9e0ec423403e0d8c34a57be242b87bfcd0d7c5df3162fbe188ad36762bc3",
}
BATCH_WALL_BUDGET_SECONDS = 900.0
PROJECT_WALL_BUDGET_SECONDS = 7200.0
FLOOR = 1.0e-12
CIDFILE_NAME = "container.cid"
FROZEN_POINTS = {
    0.6: (0.168283976, 0.198283976, 0.228283976),
    1.0: (0.284541897, 0.314541897, 0.344541897),
}
FROZEN_SOURCE_AMPLITUDES = {
    0.6: (9.727928e-5, 2.038394e-5, 8.994924e-5),
    1.0: (7.703323e-5, 3.634705e-5, 7.357345e-5),
}


@dataclass(frozen=True)
class ImpedanceCaseSpec:
    key: str
    group: str
    de: float
    thickness_ratio: float
    endocardial_axial_stiffness: float
    case_id: str
    active_profile: str
    spatial_label: str
    steps_per_cycle: int
    activation_peak: float


def _token(value: float) -> str:
    return f"{value:.9f}".rstrip("0").rstrip(".").replace(".", "p")


def _case_specs() -> tuple[ImpedanceCaseSpec, ...]:
    cases: list[ImpedanceCaseSpec] = []
    for stiffness, thicknesses in FROZEN_POINTS.items():
        for thickness in thicknesses:
            for spatial in ("S2", "S3"):
                key = "__".join(
                    (
                        "impedance_shift",
                        f"k{_token(stiffness)}",
                        "de0p2",
                        f"h{_token(thickness)}",
                        "a1",
                        spatial.lower(),
                        "t128",
                        "a0p1",
                    )
                )
                cases.append(
                    ImpedanceCaseSpec(
                        key=key,
                        group="impedance_shift",
                        de=0.2,
                        thickness_ratio=thickness,
                        endocardial_axial_stiffness=stiffness,
                        case_id="A1",
                        active_profile="uniform",
                        spatial_label=spatial,
                        steps_per_cycle=128,
                        activation_peak=0.1,
                    )
                )
    return tuple(cases)


CASE_SPECS = _case_specs()


def _validate_plan() -> None:
    if len(CASE_SPECS) != 12 or len({spec.key for spec in CASE_SPECS}) != 12:
        raise RuntimeError("the frozen plan must contain 12 unique endpoints")
    actual = {
        (
            spec.endocardial_axial_stiffness,
            spec.thickness_ratio,
            spec.spatial_label,
        )
        for spec in CASE_SPECS
    }
    expected = {
        (stiffness, thickness, spatial)
        for stiffness, thicknesses in FROZEN_POINTS.items()
        for thickness in thicknesses
        for spatial in ("S2", "S3")
    }
    if actual != expected:
        raise RuntimeError("frozen stiffness/thickness point drift")
    for spec in CASE_SPECS:
        if (
            spec.de != 0.2
            or spec.case_id != "A1"
            or spec.active_profile != "uniform"
            or spec.steps_per_cycle != 128
            or spec.activation_peak != 0.1
            or spec.endocardial_axial_stiffness == 0.8
        ):
            raise RuntimeError(f"case scope drift in {spec.key}")
        if (spec.de, spec.thickness_ratio, spec.case_id) in pilot.HOLDOUT_SIGNATURES:
            raise RuntimeError(f"holdout leakage in {spec.key}")


def _verify_inputs(repo_root: Path, prediction_commit: str, runtime_version: str) -> dict[str, Any]:
    if prediction_commit != PREDICTION_COMMIT:
        raise RuntimeError("prediction commit drift")
    if runtime_version != EXPECTED_RUNTIME_SOURCE_VERSION:
        raise RuntimeError("runtime source version drift")
    brief_hash = pilot._sha256(repo_root / PREDICTION_PATH)
    if brief_hash != PREDICTION_SHA256:
        raise RuntimeError("prediction brief hash drift")
    source_hashes = {
        path: pilot._sha256(repo_root / path) for path in EXPECTED_SOURCE_HASHES
    }
    if source_hashes != EXPECTED_SOURCE_HASHES:
        raise RuntimeError("direct source hash drift")
    prior_hash = pilot._sha256(repo_root / PRIOR_FEM_SUMMARY)
    if prior_hash != PRIOR_FEM_SUMMARY_SHA256:
        raise RuntimeError("prior FEM summary hash drift")
    with (repo_root / PRIOR_FEM_SUMMARY).open("r", encoding="utf-8") as handle:
        prior = json.load(handle)
    if (
        prior.get("status") != "COMPLETED"
        or prior.get("cumulative_completed_case_count") != 34
        or prior.get("holdouts") != "LOCKED_NOT_RUN"
        or not math.isclose(
            float(prior.get("project_cumulative_elapsed_seconds")),
            PRIOR_FEM_CUMULATIVE_SECONDS,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise RuntimeError("prior FEM count/budget/holdout evidence drift")
    return {
        "prediction_commit": prediction_commit,
        "prediction_path": PREDICTION_PATH.as_posix(),
        "prediction_sha256": brief_hash,
        "runtime_source_version": runtime_version,
        "source_hashes": source_hashes,
        "prior_fem_summary": PRIOR_FEM_SUMMARY.as_posix(),
        "prior_fem_summary_sha256": prior_hash,
        "prior_completed_endpoint_count": 34,
        "prior_fem_cumulative_seconds": PRIOR_FEM_CUMULATIVE_SECONDS,
        "holdouts": "LOCKED_NOT_RUN",
    }


def _check_prediction(repo_root: Path) -> None:
    if pilot._sha256(repo_root / PREDICTION_PATH) != PREDICTION_SHA256:
        raise RuntimeError("prediction brief changed during execution")


def _source_preflight(active_config: Any) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    activation_coefficient = complex(-0.05, 0.0)
    for stiffness, thicknesses in FROZEN_POINTS.items():
        for index, thickness in enumerate(thicknesses):
            config = replace(
                active_config,
                endocardial_axial_stiffness=stiffness,
                ecm_thickness=thickness * active_config.length,
                ecm_relaxation_time=0.2 * active_config.period,
                activation_peak=0.1,
            ).checked()
            transfer = normal_transfer._transfer_coefficients(
                {**asdict(config), "config_digest": config.digest()}, 128
            )
            source_strain = -transfer["chi0"] * activation_coefficient
            source_c0 = (
                transfer["p_epsilon"] * source_strain
                + transfer["p_activation"] * activation_coefficient
            )
            expected = FROZEN_SOURCE_AMPLITUDES[stiffness][index]
            relative_difference = abs(abs(source_c0) - expected) / expected
            records.append(
                {
                    "endocardial_axial_stiffness": stiffness,
                    "thickness_ratio": thickness,
                    "source_c0": notch._complex_record(source_c0),
                    "expected_rounded_amplitude": expected,
                    "relative_difference_from_rounded_table": relative_difference,
                    "pass": relative_difference <= 5.0e-7,
                }
            )
    return {
        "pass": all(record["pass"] for record in records),
        "activation_fundamental_used": notch._complex_record(activation_coefficient),
        "records": records,
        "note": "source-only check before FEM; no actual macro strain or response was used to move any point",
    }


def _comparison(prediction: complex, actual: complex) -> dict[str, Any]:
    residual = prediction - actual
    interpretable = abs(actual) > FLOOR and abs(prediction) > FLOOR
    return {
        "prediction": notch._complex_record(prediction),
        "prediction_minus_actual": notch._complex_record(residual),
        "absolute_complex_residual": float(abs(residual)),
        "relative_complex_residual_using_actual_c0": (
            float(abs(residual) / abs(actual)) if abs(actual) > FLOOR else None
        ),
        "phase_prediction_minus_actual_deg": (
            math.degrees(float(np.angle(prediction / actual))) if interpretable else None
        ),
        "phase_interpretable": interpretable,
        "floor": FLOOR,
    }


def _gate(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_point = {
        (
            float(record["spec"]["endocardial_axial_stiffness"]),
            float(record["spec"]["thickness_ratio"]),
            record["spec"]["spatial_label"],
        ): record
        for record in records
    }
    stiffness_groups: list[dict[str, Any]] = []
    all_sides: list[dict[str, Any]] = []
    for stiffness, thicknesses in FROZEN_POINTS.items():
        center_h = thicknesses[1]
        center_fine = by_point[(stiffness, center_h, "S3")]
        center_coarse = by_point[(stiffness, center_h, "S2")]
        center_actual = _complex_from_mode(center_fine, "c0")
        center_error = abs(center_actual - _complex_from_mode(center_coarse, "c0"))
        sides: list[dict[str, Any]] = []
        for side_h in (thicknesses[0], thicknesses[2]):
            side_fine = by_point[(stiffness, side_h, "S3")]
            side_coarse = by_point[(stiffness, side_h, "S2")]
            side_actual = _complex_from_mode(side_fine, "c0")
            side_error = abs(side_actual - _complex_from_mode(side_coarse, "c0"))
            difference = abs(side_actual) - abs(center_actual)
            combined_error = side_error + center_error

            side_source = _complex_from_record(side_fine["diagnostic"]["source_c0"])
            center_source = _complex_from_record(center_fine["diagnostic"]["source_c0"])
            side_delta = _complex_from_record(side_fine["diagnostic"]["actual_minus_source_strain"])
            center_delta = _complex_from_record(center_fine["diagnostic"]["actual_minus_source_strain"])
            side_p = _complex_from_record(side_fine["diagnostic"]["p_epsilon"])
            center_p = _complex_from_record(center_fine["diagnostic"]["p_epsilon"])
            source_difference = abs(side_source) - abs(center_source)
            macro_margin = (
                source_difference
                - abs(side_p * side_delta)
                - abs(center_p * center_delta)
            )
            record = {
                "endocardial_axial_stiffness": stiffness,
                "side_thickness_ratio": side_h,
                "center_thickness_ratio": center_h,
                "A_side": float(abs(side_actual)),
                "A_center": float(abs(center_actual)),
                "D_side_minus_center": float(difference),
                "e_side": float(side_error),
                "e_center": float(center_error),
                "E_sum": float(combined_error),
                "two_E": float(2.0 * combined_error),
                "pass_inequality_D_gt_2E": difference > 2.0 * combined_error,
                "pass_floor": difference > FLOOR and abs(side_actual) > FLOOR,
                "fail_inequality_D_lt_minus_2E": difference < -2.0 * combined_error,
                "fail_floor": -difference > FLOOR,
                "macro_sufficient_condition_diagnostic": {
                    "D_source_side_minus_center": float(source_difference),
                    "M_side": float(macro_margin),
                    "M_side_minus_2E": float(macro_margin - 2.0 * combined_error),
                    "role": "post-hoc sufficient-condition diagnostic only; its sign does not change the position gate",
                },
            }
            sides.append(record)
            all_sides.append(record)
        stiffness_groups.append(
            {
                "endocardial_axial_stiffness": stiffness,
                "frozen_window": list(thicknesses),
                "sides": sides,
            }
        )
    if all(
        side["pass_inequality_D_gt_2E"] and side["pass_floor"]
        for side in all_sides
    ):
        status = "PASS"
    elif any(
        side["fail_inequality_D_lt_minus_2E"] and side["fail_floor"]
        for side in all_sides
    ):
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return {
        "status": status,
        "floor": FLOOR,
        "stiffness_groups": stiffness_groups,
        "interpretation": (
            "exploratory discrete three-point minima in two non-overlapping preregistered windows only; "
            "not exact, unique, global, or continuous-minimum certification"
        ),
        "macro_condition_is_not_part_of_position_gate": True,
    }


def _complex_from_record(record: dict[str, Any]) -> complex:
    return complex(float(record["real"]), float(record["imag"]))


def _complex_from_mode(record: dict[str, Any], name: str) -> complex:
    return _complex_from_record(record["spatial_modes"][name])


def _write_failure_summary(output_root: Path, error: BaseException) -> None:
    summary_path = output_root / "summary.json"
    if summary_path.exists():
        return
    completed = (
        sorted((output_root / "cases").glob("*.json"))
        if (output_root / "cases").is_dir()
        else []
    )
    pilot._create_json(
        summary_path,
        {
            "schema": SUMMARY_SCHEMA,
            "status": "ABORTED_FAIL_CLOSED",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "completed_endpoint_count": len(completed),
            "position_gate": "NOT_EVALUATED",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "holdouts": "LOCKED_NOT_RUN",
            "no_automatic_retry_or_point_change": True,
        },
    )


def run(
    output_root: Path,
    prediction_commit: str,
    runtime_source_version: str,
) -> int:
    start = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root.resolve() != EXPECTED_PROJECT_ROOT.resolve():
        raise RuntimeError("project mount drift")
    if output_root.resolve() != EXPECTED_OUTPUT_ROOT.resolve():
        raise RuntimeError("output mount drift")
    if not output_root.is_dir():
        raise RuntimeError("output mount is missing")
    unexpected = [item.name for item in output_root.iterdir() if item.name != CIDFILE_NAME]
    if unexpected:
        raise RuntimeError(f"create-only output is not empty: {unexpected}")
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-CPU environment drift: {variable}")
    if os.environ.get("PAPER2_IMAGE_ID") != EXPECTED_IMAGE_ID:
        raise RuntimeError("container image identity drift")
    if os.environ.get("PAPER2_CONTAINER_NAME") != EXPECTED_CONTAINER_NAME:
        raise RuntimeError("container name drift")
    if os.environ.get("PYTHONPATH") != EXPECTED_PYTHONPATH:
        raise RuntimeError("PYTHONPATH drift")

    _validate_plan()
    identity = _verify_inputs(repo_root, prediction_commit, runtime_source_version)
    fourier_test = notch._self_test()
    transfer_test = normal_transfer._self_test()
    if not fourier_test["pass"] or not transfer_test["pass"]:
        raise RuntimeError("pre-FEM extraction/transfer self-test failed")

    import paper2_hybrid
    import dolfinx
    import scipy

    paper2_path = Path(paper2_hybrid.__file__).resolve()
    dolfinx_path = Path(dolfinx.__file__).resolve()
    expected_paper2 = (repo_root / "src" / "paper2_hybrid").resolve()
    expected_dolfinx = Path(
        "/usr/local/dolfinx-real/lib/python3.12/dist-packages/dolfinx"
    ).resolve()
    if not str(paper2_path).startswith(str(expected_paper2) + os.sep):
        raise RuntimeError("paper2_hybrid import path drift")
    if not str(dolfinx_path).startswith(str(expected_dolfinx) + os.sep):
        raise RuntimeError("dolfinx import path drift")

    from paper2_hybrid.config import ACTIVE_CONFIG
    from paper2_hybrid.model import build_system
    from paper2_hybrid.numerics import endpoint_structural_gate, simulate_endpoint
    from paper2_hybrid.validation import (
        global_structural_checks,
        interface_action_reaction_manufactured_check,
    )

    source_preflight = _source_preflight(ACTIVE_CONFIG)
    if not source_preflight["pass"]:
        raise RuntimeError("frozen source-point preflight failed")
    manufactured = interface_action_reaction_manufactured_check()
    if not manufactured["pass"]:
        raise RuntimeError("interface manufactured check failed")

    manifest = {
        "schema": SCHEMA,
        "status": "STARTED_FAIL_CLOSED_WITH_FINAL_STATUS_IN_SUMMARY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "preregistered_forward_exploratory_window_test",
        "prediction": {
            "commit": identity["prediction_commit"],
            "brief_path": identity["prediction_path"],
            "brief_sha256": identity["prediction_sha256"],
            "points": {str(key): list(value) for key, value in FROZEN_POINTS.items()},
            "source_amplitudes": {
                str(key): list(value) for key, value in FROZEN_SOURCE_AMPLITUDES.items()
            },
        },
        "runtime_source": {
            "git_version_at_launch": identity["runtime_source_version"],
            "source_hashes": identity["source_hashes"],
        },
        "runner": {
            "path": "scripts/run_paper2_impedance_shift_v01.py",
            "sha256": pilot._sha256(Path(__file__)),
        },
        "container": {
            "image": "dolfinx/dolfinx:v0.11.0",
            "image_id": EXPECTED_IMAGE_ID,
            "container_name": EXPECTED_CONTAINER_NAME,
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "network": "none",
            "root_filesystem": "read_only",
            "project_mount": "read_only",
            "only_writable_bind_mount": "/output",
            "gpu": "not_requested",
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "dolfinx": dolfinx.__version__,
            "platform": platform.platform(),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "dependency_import_regression": {
                "checked_before_any_FEM": True,
                "paper2_hybrid_path": paper2_path.as_posix(),
                "dolfinx_path": dolfinx_path.as_posix(),
                "pass": True,
            },
        },
        "budget": {
            "batch_wall_seconds": BATCH_WALL_BUDGET_SECONDS,
            "project_wall_seconds": PROJECT_WALL_BUDGET_SECONDS,
            "prior_fem_cumulative_seconds": PRIOR_FEM_CUMULATIVE_SECONDS,
            "prior_small_matrix_and_postprocessing_time_separate": True,
        },
        "case_count": 12,
        "cases": [asdict(spec) for spec in CASE_SPECS],
        "holdouts": "LOCKED_NOT_RUN",
        "source_point_preflight": source_preflight,
        "fourier_self_test": fourier_test,
        "normal_transfer_self_test": transfer_test,
        "manufactured_interface_check": manufactured,
        "claim_boundary": {
            "K0p8_not_rerun": True,
            "no_S1_or_frequency_axis_or_new_physics": True,
            "actual_macro_strain_not_used_to_move_points": True,
            "position_gate_independent_of_macro_sufficient_condition": True,
            "not_continuous_unique_global_or_novelty_certification": True,
        },
    }
    pilot._create_json(output_root / "run_manifest.json", manifest)
    case_dir = output_root / "cases"
    case_dir.mkdir(parents=False, exist_ok=False)

    records: list[dict[str, Any]] = []
    for position, spec in enumerate(CASE_SPECS, start=1):
        _check_prediction(repo_root)
        elapsed_before = time.perf_counter() - start
        if elapsed_before >= BATCH_WALL_BUDGET_SECONDS:
            raise RuntimeError("900-second batch budget reached before endpoint")
        if PRIOR_FEM_CUMULATIVE_SECONDS + elapsed_before >= PROJECT_WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second project budget reached before endpoint")
        print(f"CASE_START {position}/12 {spec.key}", flush=True)
        case_start = time.perf_counter()
        config = replace(
            ACTIVE_CONFIG,
            endocardial_axial_stiffness=spec.endocardial_axial_stiffness,
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
        if not all(check["pass"] for check in system_checks.values()):
            pilot._create_json(
                case_dir / f"{spec.key}.json",
                {
                    "schema": CASE_SCHEMA,
                    "status": "FAILED_GLOBAL_STRUCTURAL_CHECK",
                    "spec": asdict(spec),
                    "actual_config": {**asdict(config), "config_digest": config.digest()},
                    "system_checks": system_checks,
                },
            )
            raise RuntimeError(f"global structural check failed for {spec.key}")
        endpoint = simulate_endpoint(
            system=system,
            case_id=spec.case_id,
            steps_per_cycle=spec.steps_per_cycle,
        )
        structural_gate = endpoint_structural_gate(endpoint.summary)
        observables, derived_arrays = pilot._extract_observables(system, endpoint, spec)
        arrays = {
            **{name: np.asarray(value) for name, value in endpoint.arrays.items()},
            **derived_arrays,
        }
        nonfinite = [
            name for name, value in arrays.items() if not np.all(np.isfinite(value))
        ]
        array_path = case_dir / f"{spec.key}.npz"
        np.savez_compressed(array_path, **arrays)
        array_hash = pilot._sha256(array_path)
        if nonfinite:
            pilot._create_json(
                case_dir / f"{spec.key}.json",
                {
                    "schema": CASE_SCHEMA,
                    "status": "FAILED_NONFINITE_ARRAY",
                    "spec": asdict(spec),
                    "nonfinite_array_keys": nonfinite,
                    "arrays": {
                        "path": array_path.relative_to(output_root).as_posix(),
                        "sha256": array_hash,
                    },
                },
            )
            raise RuntimeError(f"non-finite arrays for {spec.key}")

        x_nodes = np.asarray(derived_arrays["x_interface_nodes"], dtype=np.float64)
        traction_complex = (
            np.asarray(
                derived_arrays["endocardium_ecm_traction_fundamental_real"],
                dtype=np.float64,
            )
            + 1.0j
            * np.asarray(
                derived_arrays["endocardium_ecm_traction_fundamental_imag"],
                dtype=np.float64,
            )
        )
        spatial_modes = notch._exact_p1_spatial_modes(
            x_nodes, traction_complex[:, 1], config.length
        )
        mode_values = spatial_modes.pop("complex_values")
        activation = complex(
            pilot._harmonic_coefficient(
                np.asarray(endpoint.arrays["activation_two_cycles"], dtype=np.float64),
                spec.steps_per_cycle,
            )
        ) * float(system.active_profile_average)
        shortening = complex(
            pilot._harmonic_coefficient(
                np.asarray(endpoint.arrays["limited_shortening_two_cycles"], dtype=np.float64),
                spec.steps_per_cycle,
            )
        )
        actual_strain = -shortening
        actual_c0 = mode_values["c0"]
        transfer = normal_transfer._transfer_coefficients(
            {**asdict(config), "config_digest": config.digest()},
            spec.steps_per_cycle,
        )
        source_strain = -transfer["chi0"] * activation
        conditional_c0 = (
            transfer["p_epsilon"] * actual_strain
            + transfer["p_activation"] * activation
        )
        source_c0 = (
            transfer["p_epsilon"] * source_strain
            + transfer["p_activation"] * activation
        )
        diagnostic = {
            "actual_macro_strain": notch._complex_record(actual_strain),
            "source_macro_strain": notch._complex_record(source_strain),
            "actual_minus_source_strain": notch._complex_record(
                actual_strain - source_strain
            ),
            "actual_c0": notch._complex_record(actual_c0),
            "conditional_c0": notch._complex_record(conditional_c0),
            "source_c0": notch._complex_record(source_c0),
            "conditional_comparison": _comparison(conditional_c0, actual_c0),
            "source_comparison": _comparison(source_c0, actual_c0),
            "p_epsilon": notch._complex_record(transfer["p_epsilon"]),
            "p_activation": notch._complex_record(transfer["p_activation"]),
            "chi0": notch._complex_record(transfer["chi0"]),
            "role": "post-hoc error attribution only; not used to relocate any frozen H or alter the position gate",
        }
        case_elapsed = time.perf_counter() - case_start
        record = {
            "schema": CASE_SCHEMA,
            "status": (
                "COMPLETED" if structural_gate["pass"] else "FAILED_ENDPOINT_STRUCTURAL_GATE"
            ),
            "spec": asdict(spec),
            "actual_config": {**asdict(config), "config_digest": config.digest()},
            "system": {
                "state_size": system.state_size,
                "spatial_label": system.spatial_label,
                "active_profile": system.active_profile,
                "active_profile_average": system.active_profile_average,
            },
            "system_checks": system_checks,
            "endpoint_structural_gate": structural_gate,
            "endpoint_summary": endpoint.summary,
            "observables": observables,
            "spatial_modes": spatial_modes,
            "diagnostic": diagnostic,
            "raw_active_work": float(endpoint.summary["ledger"]["total_active_work"]),
            "overall_shortening_fundamental": notch._complex_record(shortening),
            "B1": float(spatial_modes["B1"]),
            "arrays": {
                "path": array_path.relative_to(output_root).as_posix(),
                "sha256": array_hash,
                "key_count": len(arrays),
            },
            "runtime_seconds": case_elapsed,
            "batch_cumulative_elapsed_seconds": time.perf_counter() - start,
            "project_fem_cumulative_elapsed_seconds": (
                PRIOR_FEM_CUMULATIVE_SECONDS + time.perf_counter() - start
            ),
        }
        case_json_path = case_dir / f"{spec.key}.json"
        pilot._create_json(case_json_path, record)
        record["case_json"] = {
            "path": case_json_path.relative_to(output_root).as_posix(),
            "sha256": pilot._sha256(case_json_path),
        }
        records.append(record)
        print(
            f"CASE_DONE {position}/12 {spec.key} seconds={case_elapsed:.3f} "
            f"structural_pass={structural_gate['pass']}",
            flush=True,
        )
        if not structural_gate["pass"]:
            raise RuntimeError(f"endpoint structural gate failed for {spec.key}")
        endpoint = None
        system = None
        arrays = None
        derived_arrays = None
        gc.collect()
        _check_prediction(repo_root)
        elapsed_after = time.perf_counter() - start
        if elapsed_after > BATCH_WALL_BUDGET_SECONDS:
            raise RuntimeError("900-second batch budget exceeded after endpoint")
        if PRIOR_FEM_CUMULATIVE_SECONDS + elapsed_after > PROJECT_WALL_BUDGET_SECONDS:
            raise RuntimeError("7200-second project budget exceeded after endpoint")

    position_gate = _gate(records)
    _check_prediction(repo_root)
    total_elapsed = time.perf_counter() - start
    final_summary = {
        "schema": SUMMARY_SCHEMA,
        "status": "COMPLETED",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "preregistered_forward_exploratory_window_test",
        "case_count": 12,
        "prior_completed_endpoint_count": 34,
        "cumulative_completed_endpoint_count": 46,
        "holdouts": "LOCKED_NOT_RUN",
        "all_structural_gates_pass": all(
            record["endpoint_structural_gate"]["pass"] for record in records
        ),
        "all_arrays_finite": True,
        "position_gate": position_gate,
        "batch_elapsed_seconds": total_elapsed,
        "batch_budget_seconds": BATCH_WALL_BUDGET_SECONDS,
        "prior_fem_cumulative_seconds": PRIOR_FEM_CUMULATIVE_SECONDS,
        "project_fem_cumulative_seconds": PRIOR_FEM_CUMULATIVE_SECONDS + total_elapsed,
        "cases": [
            {
                "key": record["spec"]["key"],
                "endocardial_axial_stiffness": record["spec"][
                    "endocardial_axial_stiffness"
                ],
                "thickness_ratio": record["spec"]["thickness_ratio"],
                "spatial_label": record["spec"]["spatial_label"],
                "structural_pass": record["endpoint_structural_gate"]["pass"],
                "raw_active_work": record["raw_active_work"],
                "overall_shortening_fundamental": record[
                    "overall_shortening_fundamental"
                ],
                "spatial_modes": record["spatial_modes"],
                "diagnostic": record["diagnostic"],
                "runtime_seconds": record["runtime_seconds"],
                "case_json": record["case_json"],
                "arrays": record["arrays"],
            }
            for record in records
        ],
        "claim_boundary": {
            "position_gate_only_uses_actual_c0_and_pointwise_S2_S3_differences": True,
            "macro_sufficient_condition_is_separate_diagnostic": True,
            "nonpositive_macro_margin_does_not_force_position_FAIL": True,
            "not_equal_active_work": True,
            "not_full_field_unloading": True,
            "not_continuous_unique_global_or_novelty_certification": True,
            "S2_S3_difference_is_not_a_strict_error_bound": True,
            "no_holdout_or_K0p8_read": True,
        },
    }
    pilot._create_json(output_root / "summary.json", final_summary)
    print(
        f"RUN_DONE cases=12 position_gate={position_gate['status']} "
        f"seconds={total_elapsed:.3f}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prediction-commit")
    parser.add_argument("--runtime-source-version")
    arguments = parser.parse_args()
    if arguments.self_test:
        _validate_plan()
        report = {
            "plan_case_count": len(CASE_SPECS),
            "fourier": notch._self_test(),
            "normal_transfer": normal_transfer._self_test(),
        }
        report["pass"] = report["fourier"]["pass"] and report["normal_transfer"]["pass"]
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if (
        arguments.output is None
        or arguments.prediction_commit is None
        or arguments.runtime_source_version is None
    ):
        parser.error(
            "--output, --prediction-commit, and --runtime-source-version are required"
        )
    try:
        return run(
            arguments.output,
            arguments.prediction_commit,
            arguments.runtime_source_version,
        )
    except BaseException as error:
        try:
            if arguments.output.is_dir():
                _write_failure_summary(arguments.output, error)
        except BaseException as summary_error:
            print(
                f"FAILURE_SUMMARY_ERROR {type(summary_error).__name__}: {summary_error}",
                file=sys.stderr,
            )
        print(f"RUN_ABORTED {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
