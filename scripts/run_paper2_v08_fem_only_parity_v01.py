#!/usr/bin/env python3
"""Run the create-only v08 active-architecture migration parity gate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

EXPECTED_EXECUTION_HEAD = "b6f1c16a1fcc04856d4ac10cd4745160ff666644"
RETIRED_HISTORY_ANCHOR = "34908b299475ee81d9cb2fccca0b191e22fa965a"
EXPECTED_REFERENCE = "results/paper2_m2/identity_2d_v03_t64_v01_20260903"
EXPECTED_OUTPUT = "results/paper2_v08/fem_only_architecture_parity_v01_20260904"
EXPECTED_CONTRACT = (
    "project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md"
)
EXPECTED_DECISION = (
    "project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md"
)
PARITY_CASES = ("A2", "LN", "LS", "C0", "CQ", "S1")
ARRAY_KEYS = (
    "time_two_cycles",
    "activation_two_cycles",
    "limited_shortening_two_cycles",
    "free_shortening_two_cycles",
    "mean_endocardial_tangential_displacement_two_cycles",
    "mean_endocardial_normal_displacement_two_cycles",
    "state_two_cycles",
    "myocardium_ecm_traction_two_cycles",
    "endocardium_ecm_traction_two_cycles",
    "ecm_cell_centroids",
    "ecm_strain_at_peak",
    "ecm_internal_z_at_peak",
    "ecm_stress_at_peak",
    "ledger_energy",
    "ledger_active_work_steps",
    "ledger_lumen_work_steps",
    "ledger_external_support_work_steps",
    "ledger_drag_dissipation_steps",
    "ledger_sls_dissipation_steps",
    "ledger_residual_steps",
    "ledger_normalized_residual_steps",
    "ledger_discrete_energy_change_steps",
    "ledger_endpoint_energy_change_steps",
    "ledger_endpoint_subtraction_gap_steps",
    "ledger_normalization_scale_steps",
    "ledger_equilibrium_defect_work_steps",
    "ledger_ledger_minus_equilibrium_work_steps",
    "ledger_ledger_minus_equilibrium_work_relative_steps",
)
FIELD_KEYS = (
    "ecm_cell_centroids",
    "ecm_strain_at_peak",
    "ecm_internal_z_at_peak",
    "ecm_stress_at_peak",
)
SCALAR_PATHS = (
    ("cycle_state_relative_difference",),
    ("passive_tangent",),
    ("manufactured_uniform_strain_relative_error",),
    ("maximum_state_norm",),
    ("peak_free_shortening",),
    ("peak_limited_shortening",),
    ("minimum_limited_shortening",),
    ("peak_absolute_mean_endocardial_tangential_displacement",),
    ("peak_absolute_mean_endocardial_normal_displacement",),
    ("shortening_fundamental_amplitude",),
    ("shortening_waveform_l2",),
    ("shortening_phase_relative_to_activation_rad",),
    ("maximum_myocardium_ecm_traction",),
    ("maximum_endocardium_ecm_traction",),
    ("myocardium_ecm_traction_l2",),
    ("endocardium_ecm_traction_l2",),
    ("interface_action_reaction_relative_error",),
    ("hotspot_x",),
    ("hotspot_traction",),
    ("maximum_ecm_von_mises_proxy",),
    ("solver", "dc_relative_residual"),
    ("solver", "harmonic_relative_residual"),
    ("solver", "maximum_relative_residual"),
    ("solver", "dc_normwise_backward_error"),
    ("solver", "harmonic_normwise_backward_error"),
    ("solver", "maximum_normwise_backward_error"),
    ("ledger", "total_active_work"),
    ("ledger", "total_lumen_work"),
    ("ledger", "total_external_support_work"),
    ("ledger", "total_drag_dissipation"),
    ("ledger", "total_sls_dissipation"),
    ("ledger", "cycle_discrete_energy_change"),
    ("ledger", "cycle_endpoint_energy_change"),
    ("ledger", "cycle_energy_change"),
    ("ledger", "maximum_absolute_endpoint_subtraction_gap"),
    ("ledger", "maximum_normalized_residual"),
    ("ledger", "maximum_ledger_minus_equilibrium_work_relative"),
    ("ledger", "minimum_physical_dissipation"),
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--host-pytest-summary", required=True)
    parser.add_argument("--container-pytest-summary", required=True)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def _strict_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )


def _finite_tree(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int, np.integer)):
        return True
    if isinstance(value, (float, np.floating)):
        return math.isfinite(float(value))
    if isinstance(value, dict):
        return all(_finite_tree(key) and _finite_tree(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(item) for item in value)
    return False


def _write_json(path: Path, payload: Any) -> None:
    if not _finite_tree(payload):
        raise ValueError(f"non-finite or unsupported JSON payload for {path}")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _git_revision(reference: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", reference],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _project_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _snapshot(paths: list[Path]) -> dict[str, dict[str, int | str]]:
    records: dict[str, dict[str, int | str]] = {}
    for path in sorted(set(item.resolve() for item in paths)):
        records[_project_path(path)] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return records


def _retired_code_paths() -> list[Path]:
    paths = list((PROJECT_ROOT / "src" / "paper2_m2").glob("*.py"))
    paths.extend((PROJECT_ROOT / "tests" / "paper2_m2").glob("*.py"))
    paths.extend((PROJECT_ROOT / "scripts").glob("*paper2_m2*.py"))
    return paths


def _active_paths() -> list[Path]:
    paths = list((PROJECT_ROOT / "src" / "paper2_hybrid").glob("*.py"))
    paths.extend((PROJECT_ROOT / "tests" / "paper2_hybrid").glob("*.py"))
    paths.append(Path(__file__).resolve())
    return paths


def _reference_lock(reference_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[str] = []
    ledger_path = reference_dir / "hash_ledger.json"
    ledger = _strict_json(ledger_path)
    expected = set(ledger.get("files", {}))
    actual = {
        path.relative_to(reference_dir).as_posix()
        for path in reference_dir.rglob("*")
        if path.is_file() and path.name != "hash_ledger.json"
    }
    if expected != actual:
        failures.append("reference_file_set_mismatch")
    snapshot: dict[str, Any] = {}
    for relative, record in sorted(ledger.get("files", {}).items()):
        path = reference_dir / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        actual_record = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        snapshot[relative] = actual_record
        if actual_record != {
            "bytes": record.get("bytes"),
            "sha256": record.get("sha256"),
        }:
            failures.append(f"hash_or_size:{relative}")
    snapshot["hash_ledger.json"] = {
        "bytes": ledger_path.stat().st_size,
        "sha256": _sha256(ledger_path),
    }
    pass_summary = _strict_json(reference_dir / "pass_summary.json")
    if pass_summary.get("decision") != "T64_NUMERICAL_PASS_V03":
        failures.append("reference_stage_not_passed")
    summaries = _strict_json(reference_dir / "endpoint_summaries.json")
    for case_id in PARITY_CASES:
        key = f"ID-{case_id}__FEM__S4__T64__D0"
        if key not in summaries:
            failures.append(f"missing_summary:{key}")
        archive = reference_dir / "selected_dynamic_holdouts" / f"{key}.npz"
        if not archive.is_file():
            failures.append(f"missing_archive:{key}")
    return (
        {
            "schema": "paper2_v08_retired_reference_lock",
            "reference_dir": _project_path(reference_dir),
            "ledger_entries": len(expected),
            "file_set_match": expected == actual,
            "failures": failures,
            "pass": not failures,
        },
        snapshot,
    )


def _active_source_audit() -> dict[str, Any]:
    forbidden = (
        "representation",
        "_dcm_network_full",
        "passive_dcm_scale",
        "active_dcm_scale",
        "calibration",
        "go-id",
        "maybe-id",
        "no-go-id",
        "paper2_m2",
    )
    failures: list[str] = []
    files: dict[str, Any] = {}
    for path in sorted((PROJECT_ROOT / "src" / "paper2_hybrid").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        tokens = [token for token in forbidden if token in lowered]
        imports: list[str] = []
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(name.name for name in node.names)
        retired_imports = [name for name in imports if name.startswith("paper2_m2")]
        if tokens:
            failures.append(f"forbidden_tokens:{path.name}:{','.join(tokens)}")
        if retired_imports:
            failures.append(f"retired_import:{path.name}")
        files[_project_path(path)] = {
            "forbidden_tokens": tokens,
            "retired_imports": retired_imports,
            "sha256": _sha256(path),
        }
    return {
        "schema": "paper2_v08_active_source_audit",
        "files": files,
        "failures": failures,
        "pass": not failures,
    }


def _value_at(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        value = value[key]
    return value


def _scalar_parity(new_value: Any, reference_value: Any) -> dict[str, Any]:
    if new_value is None or reference_value is None:
        passed = new_value is None and reference_value is None
        return {
            "new": new_value,
            "reference": reference_value,
            "status": "BOTH_NOT_APPLICABLE" if passed else "APPLICABILITY_MISMATCH",
            "absolute_error": None,
            "normalized_error": None,
            "pass": passed,
        }
    new_number = float(new_value)
    reference_number = float(reference_value)
    absolute = abs(new_number - reference_number)
    normalized = absolute / max(abs(new_number), abs(reference_number), 1.0e-30)
    return {
        "new": new_number,
        "reference": reference_number,
        "absolute_error": absolute,
        "normalized_error": normalized,
        "pass": bool(absolute <= 1.0e-12 or normalized <= 1.0e-10),
    }


def _array_parity(new_values: np.ndarray, reference_values: np.ndarray) -> dict[str, Any]:
    new_values = np.asarray(new_values)
    reference_values = np.asarray(reference_values)
    if new_values.shape != reference_values.shape:
        return {
            "new_shape": list(new_values.shape),
            "reference_shape": list(reference_values.shape),
            "pass": False,
            "failure": "shape_mismatch",
        }
    flat_new = new_values.ravel()
    flat_reference = reference_values.ravel()
    difference_energy = 0.0
    new_energy = 0.0
    reference_energy = 0.0
    maximum_absolute = 0.0
    finite = True
    chunk = 1_000_000
    for start in range(0, flat_new.size, chunk):
        stop = min(start + chunk, flat_new.size)
        part_new = flat_new[start:stop]
        part_reference = flat_reference[start:stop]
        difference = part_new - part_reference
        finite = bool(
            finite
            and np.all(np.isfinite(part_new))
            and np.all(np.isfinite(part_reference))
            and np.all(np.isfinite(difference))
        )
        if difference.size:
            maximum_absolute = max(maximum_absolute, float(np.max(np.abs(difference))))
        difference_energy += float(np.dot(difference, difference))
        new_energy += float(np.dot(part_new, part_new))
        reference_energy += float(np.dot(part_reference, part_reference))
    difference_norm = math.sqrt(max(difference_energy, 0.0))
    new_norm = math.sqrt(max(new_energy, 0.0))
    reference_norm = math.sqrt(max(reference_energy, 0.0))
    normalized = difference_norm / max(new_norm, reference_norm, 1.0e-30)
    return {
        "shape": list(new_values.shape),
        "new_norm": new_norm,
        "reference_norm": reference_norm,
        "difference_norm": difference_norm,
        "maximum_absolute_error": maximum_absolute,
        "normalized_l2_error": normalized,
        "finite": finite,
        "pass": bool(
            finite and (maximum_absolute <= 1.0e-12 or normalized <= 1.0e-10)
        ),
    }


def _write_hash_ledger(output_dir: Path) -> dict[str, Any]:
    entries = {
        path.relative_to(output_dir).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name != "hash_ledger.json"
    }
    payload = {"schema": "paper2_v08_hash_ledger", "files": entries}
    _write_json(output_dir / "hash_ledger.json", payload)
    return payload


def _peak_memory_gib() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0))


def _tests_pass(summary: str) -> bool:
    lowered = summary.lower()
    return "passed" in lowered and "failed" not in lowered and "error" not in lowered


def main() -> None:
    arguments = _arguments()
    started = time.perf_counter()
    reference_dir = arguments.reference_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    contract = arguments.contract.resolve()
    decision = arguments.decision.resolve()
    expected = {
        "reference": (PROJECT_ROOT / EXPECTED_REFERENCE).resolve(),
        "output": (PROJECT_ROOT / EXPECTED_OUTPUT).resolve(),
        "contract": (PROJECT_ROOT / EXPECTED_CONTRACT).resolve(),
        "decision": (PROJECT_ROOT / EXPECTED_DECISION).resolve(),
    }
    actual = {
        "reference": reference_dir,
        "output": output_dir,
        "contract": contract,
        "decision": decision,
    }
    path_failures = [name for name in expected if expected[name] != actual[name]]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")

    reference_lock: dict[str, Any] = {"pass": False}
    reference_before: dict[str, Any] = {}
    retired_before: dict[str, Any] = {}
    active_before: dict[str, Any] = {}
    try:
        head = _git_revision("HEAD")
        upstream = _git_revision("@{upstream}")
        reference_lock, reference_before = _reference_lock(reference_dir)
        retired_before = _snapshot(_retired_code_paths())
        active_before = _snapshot(_active_paths())
        source_audit = _active_source_audit()
        preflight = {
            "schema": "paper2_v08_preflight",
            "execution_head": head,
            "expected_execution_head": EXPECTED_EXECUTION_HEAD,
            "retired_history_anchor": RETIRED_HISTORY_ANCHOR,
            "upstream_head": upstream,
            "path_failures": path_failures,
            "reference_lock": reference_lock,
            "active_source_audit": source_audit,
            "host_pytest_summary": arguments.host_pytest_summary,
            "container_pytest_summary": arguments.container_pytest_summary,
            "pass": bool(
                not path_failures
                and head == EXPECTED_EXECUTION_HEAD
                and upstream == EXPECTED_EXECUTION_HEAD
                and reference_lock["pass"]
                and source_audit["pass"]
                and _tests_pass(arguments.host_pytest_summary)
                and _tests_pass(arguments.container_pytest_summary)
            ),
        }
        if not preflight["pass"]:
            raise RuntimeError("v08 preflight failed")

        from paper2_hybrid.config import ACTIVE_CONFIG
        from paper2_hybrid.model import build_system
        from paper2_hybrid.numerics import endpoint_structural_gate, simulate_endpoint
        from paper2_hybrid.projection import (
            constant_traction_projection_manufactured_check,
            project_piecewise_linear_to_common_segments,
        )
        from paper2_hybrid.protocol import ACTIVE_PROTOCOL, endpoint_key
        from paper2_hybrid.roles import ACTIVE_TISSUE_ROLES
        from paper2_hybrid.validation import (
            common_projection_sidecar,
            global_structural_checks,
            interface_action_reaction_manufactured_check,
        )

        reference_summaries = _strict_json(reference_dir / "endpoint_summaries.json")
        uniform_system = build_system(spatial_label="S4", active_profile="uniform")
        heterogeneous_system = build_system(spatial_label="S4", active_profile="S1")
        global_checks = global_structural_checks(uniform_system)
        action_reaction = interface_action_reaction_manufactured_check()
        projection_check = constant_traction_projection_manufactured_check(
            native_segments=128, common_segments=64
        )
        structural_preflight = {
            "schema": "paper2_v08_structural_preflight",
            "global_checks": global_checks,
            "interface_action_reaction_manufactured": action_reaction,
            "common_projection_manufactured": projection_check,
            "pass": bool(
                all(record["pass"] for record in global_checks.values())
                and action_reaction["pass"]
                and projection_check["pass"]
            ),
        }

        parity_by_case: dict[str, Any] = {}
        field_summary_by_case: dict[str, Any] = {}
        completed_cases = 0
        for case_id in PARITY_CASES:
            system = heterogeneous_system if case_id == "S1" else uniform_system
            endpoint_started = time.perf_counter()
            endpoint = simulate_endpoint(
                system=system,
                case_id=case_id,
                steps_per_cycle=ACTIVE_PROTOCOL.steps_per_cycle,
            )
            endpoint_runtime = time.perf_counter() - endpoint_started
            endpoint.summary["common_projection"] = common_projection_sidecar(
                system, endpoint
            )
            structural = endpoint_structural_gate(endpoint.summary)
            forbidden_summary_keys = sorted(
                set(endpoint.summary)
                & {"representation", "passive_dcm_scale", "active_dcm_scale"}
            )
            retired_key = f"ID-{case_id}__FEM__S4__T64__D0"
            reference_summary = reference_summaries[retired_key]
            scalar_records = {
                ".".join(path): _scalar_parity(
                    _value_at(endpoint.summary, path),
                    _value_at(reference_summary, path),
                )
                for path in SCALAR_PATHS
            }
            archive_path = (
                reference_dir / "selected_dynamic_holdouts" / f"{retired_key}.npz"
            )
            array_records: dict[str, Any] = {}
            field_records: dict[str, Any] = {}
            projection_records: dict[str, Any] = {}
            with np.load(archive_path, allow_pickle=False) as archive:
                missing = sorted(set(ARRAY_KEYS) - set(archive.files))
                if missing:
                    raise RuntimeError(f"retired archive missing arrays: {missing}")
                for name in ARRAY_KEYS:
                    array_records[name] = _array_parity(endpoint.arrays[name], archive[name])
                for name in FIELD_KEYS:
                    new_values = endpoint.arrays[name]
                    reference_values = archive[name]
                    field_records[name] = {
                        "new_sha256": _array_sha256(new_values),
                        "reference_sha256": _array_sha256(reference_values),
                        "byte_hash_equal": bool(
                            _array_sha256(new_values) == _array_sha256(reference_values)
                        ),
                        "new_norm": float(np.linalg.norm(new_values)),
                        "reference_norm": float(np.linalg.norm(reference_values)),
                        "parity": array_records[name],
                    }
                native_x = system.myocardium_mesh.dof_coordinates[
                    system.myocardium_mesh.top_nodes, 0
                ]
                common_x = np.linspace(-0.5, 0.5, 65)
                for interface, name in (
                    ("myocardium_ecm", "myocardium_ecm_traction_two_cycles"),
                    ("endocardium_ecm", "endocardium_ecm_traction_two_cycles"),
                ):
                    new_native = endpoint.arrays[name].reshape(129, 2, -1)[:, :, :64]
                    reference_native = archive[name].reshape(129, 2, -1)[:, :, :64]
                    new_projected = project_piecewise_linear_to_common_segments(
                        native_x, new_native, common_x
                    )
                    reference_projected = project_piecewise_linear_to_common_segments(
                        native_x, reference_native, common_x
                    )
                    projection_records[interface] = _array_parity(
                        new_projected, reference_projected
                    )
            projection_scalar_records = {
                metric: _scalar_parity(
                    endpoint.summary["common_projection"]["values"][metric],
                    reference_summary["v03_common_projection_sidecar"]["values"][metric],
                )
                for metric in (
                    "myocardium_ecm_traction_l2",
                    "endocardium_ecm_traction_l2",
                )
            }
            case_pass = bool(
                structural_preflight["pass"]
                and structural["pass"]
                and not forbidden_summary_keys
                and all(record["pass"] for record in scalar_records.values())
                and all(record["pass"] for record in array_records.values())
                and all(record["pass"] for record in projection_records.values())
                and all(record["pass"] for record in projection_scalar_records.values())
            )
            key = endpoint_key(case_id)
            parity_by_case[key] = {
                "case_id": case_id,
                "retired_reference_key": retired_key,
                "endpoint_runtime_seconds": endpoint_runtime,
                "structural_gate": structural,
                "forbidden_summary_keys": forbidden_summary_keys,
                "scalar_records": scalar_records,
                "array_records": array_records,
                "projected_traction_records": projection_records,
                "projected_traction_norm_records": projection_scalar_records,
                "pass": case_pass,
            }
            field_summary_by_case[key] = field_records
            completed_cases += 1
            print(
                json.dumps(
                    {
                        "event": "parity_case_complete",
                        "case": case_id,
                        "completed": completed_cases,
                        "expected": len(PARITY_CASES),
                        "pass": case_pass,
                        "runtime_seconds": endpoint_runtime,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

        reference_lock_after, reference_after = _reference_lock(reference_dir)
        retired_after = _snapshot(_retired_code_paths())
        active_after = _snapshot(_active_paths())
        elapsed = time.perf_counter() - started
        peak_memory = _peak_memory_gib()
        resource_pass = bool(elapsed <= 1200.0 and peak_memory <= 8.0)
        old_evidence_unchanged = bool(
            reference_lock_after["pass"]
            and reference_before == reference_after
            and retired_before == retired_after
        )
        active_implementation_unchanged = active_before == active_after
        complete = completed_cases == len(PARITY_CASES)
        parity_pass = bool(
            complete
            and structural_preflight["pass"]
            and all(record["pass"] for record in parity_by_case.values())
            and old_evidence_unchanged
            and active_implementation_unchanged
            and resource_pass
        )
        label = (
            "FEM_ONLY_ARCHITECTURE_PASS_V08"
            if parity_pass
            else "FEM_ONLY_PARITY_FAIL_V08"
        )
        architecture_manifest = {
            "schema": "paper2_v08_active_architecture_manifest",
            "tissue_roles": ACTIVE_TISSUE_ROLES.manifest(),
            "fluid_present": False,
            "active_cases": list(ACTIVE_CONFIG.cases),
            "endpoint_key_fields": [
                "case",
                "spatial_level",
                "time_level",
                "tolerance_level",
            ],
            "example_endpoint_key": endpoint_key("A2"),
            "source_audit": source_audit,
            "pass": source_audit["pass"],
        }
        parity_payload = {
            "schema": "paper2_v08_fem_to_fem_migration_parity",
            "absolute_tolerance": 1.0e-12,
            "normalized_l2_tolerance": 1.0e-10,
            "completed_cases": completed_cases,
            "expected_cases": len(PARITY_CASES),
            "cases": parity_by_case,
            "all_cases_pass": all(record["pass"] for record in parity_by_case.values()),
        }
        field_payload = {
            "schema": "paper2_v08_ecm_field_summary_audit",
            "cases": field_summary_by_case,
            "all_field_parity_pass": all(
                field["parity"]["pass"]
                for case in field_summary_by_case.values()
                for field in case.values()
            ),
        }
        provenance = {
            "schema": "paper2_v08_provenance",
            "contract": _project_path(contract),
            "contract_sha256": _sha256(contract),
            "decision": _project_path(decision),
            "decision_sha256": _sha256(decision),
            "execution_head": head,
            "upstream_head": upstream,
            "retired_history_anchor": RETIRED_HISTORY_ANCHOR,
            "reference_lock_before": reference_lock,
            "reference_lock_after": reference_lock_after,
            "reference_snapshot_before": reference_before,
            "reference_snapshot_after": reference_after,
            "retired_code_snapshot_before": retired_before,
            "retired_code_snapshot_after": retired_after,
            "active_implementation_before": active_before,
            "active_implementation_after": active_after,
            "old_evidence_unchanged": old_evidence_unchanged,
            "active_implementation_unchanged": active_implementation_unchanged,
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
                "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
                "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            },
        }
        summary = {
            "schema": "paper2_v08_pass_summary",
            "status": "COMPLETE_AT_SUPERVISOR_GATE",
            "formal_label": label,
            "completed_cases": completed_cases,
            "expected_cases": len(PARITY_CASES),
            "all_parity_cases_pass": parity_payload["all_cases_pass"],
            "all_structural_checks_pass": structural_preflight["pass"],
            "old_evidence_unchanged": old_evidence_unchanged,
            "active_implementation_unchanged": active_implementation_unchanged,
            "resource": {
                "elapsed_seconds": elapsed,
                "budget_seconds": 1200.0,
                "peak_memory_gib": peak_memory,
                "memory_budget_gib": 8.0,
                "within_budget": resource_pass,
                "cpu_processes": 1,
                "gpu_used": False,
                "network_used": False,
                "docker_socket_mounted": False,
            },
            "stop_boundary": {
                "parameter_scan": False,
                "three_dimensional_run": False,
                "whole_atrium_run": False,
                "fluid_run": False,
                "GPU_used": False,
                "retired_route_restored": False,
            },
            "evidence_boundary": (
                "This migration gate tests whether the active code reproduces the frozen "
                "historical FEM-arm observables. It is not physiological validation, a new "
                "mechanistic result, or evidence for three-dimensional, atrial, fluid, EFE, "
                "experimental, or clinical claims."
            ),
        }
        artifacts = {
            "preflight.json": preflight,
            "architecture_manifest.json": architecture_manifest,
            "structural_checks.json": structural_preflight,
            "parity_by_case.json": parity_payload,
            "ecm_field_summary_audit.json": field_payload,
            "provenance.json": provenance,
            "pass_summary.json": summary,
        }
        if not all(_finite_tree(payload) for payload in artifacts.values()):
            raise ValueError("non-finite result before formal write")
        output_dir.mkdir(parents=True, exist_ok=False)
        for name, payload in artifacts.items():
            _write_json(output_dir / name, payload)
        finite_audit = {
            "schema": "paper2_v08_finite_value_audit",
            "json_files_checked": sorted(artifacts),
            "all_json_parse_and_finite": all(
                _finite_tree(_strict_json(output_dir / name)) for name in artifacts
            ),
            "new_npz_created": False,
            "pass": True,
        }
        _write_json(output_dir / "finite_value_audit.json", finite_audit)
        _write_hash_ledger(output_dir)
        print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
        if label != "FEM_ONLY_ARCHITECTURE_PASS_V08":
            raise SystemExit(2)
    except SystemExit:
        raise
    except Exception as error:
        failure = {
            "schema": "paper2_v08_failure_summary",
            "status": "FAIL_CLOSED_AT_SUPERVISOR_GATE",
            "formal_label": "BLOCKED",
            "reason": f"{type(error).__name__}: {error}",
            "elapsed_seconds": time.perf_counter() - started,
            "peak_memory_gib": _peak_memory_gib(),
            "completed_cases": 0,
            "gpu_used": False,
            "network_used": False,
        }
        if output_dir.exists():
            raise
        output_dir.mkdir(parents=True, exist_ok=False)
        _write_json(output_dir / "failure_summary.json", failure)
        _write_json(
            output_dir / "source_lock_context.json",
            {
                "reference_lock": reference_lock,
                "reference_snapshot_before": reference_before,
                "retired_code_snapshot_before": retired_before,
                "active_implementation_before": active_before,
            },
        )
        _write_hash_ledger(output_dir)
        print(json.dumps(failure, indent=2, sort_keys=True), flush=True)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
