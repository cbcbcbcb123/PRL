from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Any


class R1EvidenceError(RuntimeError):
    """The frozen R1 focused evidence is absent, malformed, or inconsistent."""


REQUIRED_FILES = (
    "focused_build.log",
    "focused_build.exitcode",
    "focused_response.log",
    "focused_response.exitcode",
    "final_build.log",
    "final_build.exitcode",
    "formal_response.log",
    "formal_response.exitcode",
    "focused_regression.log",
    "focused_regression.exitcode",
)

SAMPLE_FIELDS = {
    "run",
    "step",
    "time",
    "revision",
    "vertex_count",
    "face_count",
    "axis_length",
    "surface_area",
    "area_ratio",
    "volume",
    "volume_ratio",
    "centroid_x",
    "centroid_y",
    "centroid_z",
    "normalized_centroid_drift",
    "registered_active_energy",
    "active_control_work",
    "viscous_dissipation",
    "energy_balance_residual",
    "minimum_oriented_face_alignment",
    "minimum_triangle_quality",
    "minimum_face_area_ratio",
    "maximum_normalized_cache_residual",
    "force_buffer_l2_norm",
    "finite",
    "state_hash",
}


def _read_evidence_file(directory: Path, name: str) -> tuple[bytes, dict[str, Any]]:
    path = directory / name
    if not path.is_file():
        raise R1EvidenceError(f"required R1 evidence file is missing: {name}")
    payload = path.read_bytes()
    return payload, {
        "path": f"verification/{name}",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _read_exit_code(directory: Path, name: str) -> tuple[int, dict[str, Any]]:
    if not (directory / name).is_file():
        raise R1EvidenceError(f"required R1 exit code evidence file is missing: {name}")
    payload, manifest = _read_evidence_file(directory, name)
    try:
        value = int(payload.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise R1EvidenceError(f"R1 evidence exit code is invalid: {name}") from error
    manifest["exit_code"] = value
    return value, manifest


def _decode_log(payload: bytes) -> str:
    encodings = (
        ("utf-8-sig", "utf-16")
        if payload.startswith((b"\xff\xfe", b"\xfe\xff"))
        else ("utf-8-sig",)
    )
    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise R1EvidenceError("R1 focused evidence log has an unsupported encoding")


def _pairs(row: list[str], tag: str) -> dict[str, str]:
    if len(row) < 3 or len(row[1:]) % 2 != 0:
        raise R1EvidenceError(f"{tag} machine record is not key/value closed")
    keys = row[1::2]
    if len(keys) != len(set(keys)):
        raise R1EvidenceError(f"{tag} machine record contains duplicate keys")
    return dict(zip(keys, row[2::2], strict=True))


def _finite_float(record: dict[str, str], key: str) -> float:
    try:
        value = float(record[key])
    except (KeyError, ValueError) as error:
        raise R1EvidenceError(f"R1 numeric field is invalid: {key}") from error
    if not math.isfinite(value):
        raise R1EvidenceError(f"R1 numeric field is non-finite: {key}")
    return value


def _integer(record: dict[str, str], key: str) -> int:
    try:
        return int(record[key])
    except (KeyError, ValueError) as error:
        raise R1EvidenceError(f"R1 integer field is invalid: {key}") from error


def _machine_records(text: str) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {
        "r1_config": [],
        "r1_sample": [],
        "r1_event": [],
        "r1_transfer": [],
        "r1_qoi": [],
        "r1_ledger": [],
        "r1_gate": [],
    }
    for line in text.splitlines():
        if not line.startswith("r1_"):
            continue
        row = next(csv.reader([line]))
        tag = row[0]
        if tag not in result:
            continue
        result[tag].append(_pairs(row, tag))
    return result


def parse_r1_focused_evidence(evidence_dir: Path) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    manifests: list[dict[str, Any]] = []
    build_payload, build_manifest = _read_evidence_file(
        evidence_dir, "focused_build.log"
    )
    manifests.append(build_manifest)
    build_exit, build_exit_manifest = _read_exit_code(
        evidence_dir, "focused_build.exitcode"
    )
    manifests.append(build_exit_manifest)
    response_payload, response_manifest = _read_evidence_file(
        evidence_dir, "focused_response.log"
    )
    manifests.append(response_manifest)
    response_exit, response_exit_manifest = _read_exit_code(
        evidence_dir, "focused_response.exitcode"
    )
    manifests.append(response_exit_manifest)
    final_build_payload, final_build_manifest = _read_evidence_file(
        evidence_dir, "final_build.log"
    )
    manifests.append(final_build_manifest)
    final_build_exit, final_build_exit_manifest = _read_exit_code(
        evidence_dir, "final_build.exitcode"
    )
    manifests.append(final_build_exit_manifest)
    formal_payload, formal_manifest = _read_evidence_file(
        evidence_dir, "formal_response.log"
    )
    manifests.append(formal_manifest)
    formal_exit, formal_exit_manifest = _read_exit_code(
        evidence_dir, "formal_response.exitcode"
    )
    manifests.append(formal_exit_manifest)
    regression_payload, regression_manifest = _read_evidence_file(
        evidence_dir, "focused_regression.log"
    )
    manifests.append(regression_manifest)
    regression_exit, regression_exit_manifest = _read_exit_code(
        evidence_dir, "focused_regression.exitcode"
    )
    manifests.append(regression_exit_manifest)
    build_text = _decode_log(build_payload)
    response_text = _decode_log(response_payload)
    final_build_text = _decode_log(final_build_payload)
    formal_text = _decode_log(formal_payload)
    regression_text = _decode_log(regression_payload)
    if build_exit != 0 or "Built target prl_x1k_r1_remesh_robustness" not in build_text:
        raise R1EvidenceError("R1 focused build did not complete successfully")
    if response_exit != 1:
        raise R1EvidenceError(
            "R1 focused response exit code must preserve the frozen scientific failure"
        )
    if (
        final_build_exit != 0
        or "Built target prl_x1k_r1_remesh_robustness" not in final_build_text
    ):
        raise R1EvidenceError("R1 final focused build did not complete successfully")
    if formal_exit != 1:
        raise R1EvidenceError("R1 formal response did not preserve exact exit code 1")
    if (
        regression_exit != 0
        or "100% tests passed, 0 tests failed out of 1" not in regression_text
        or "passed_frozen_failure_regression" not in regression_text
    ):
        raise R1EvidenceError("R1 frozen-failure regression did not pass")

    records = _machine_records(response_text)
    if _machine_records(formal_text) != records:
        raise R1EvidenceError(
            "R1 final formal response differs from the first frozen raw response"
        )
    for singleton in ("r1_config", "r1_ledger", "r1_gate"):
        if len(records[singleton]) != 1:
            raise R1EvidenceError(f"R1 evidence requires one {singleton} record")
    if len(records["r1_event"]) != 2 or len(records["r1_transfer"]) != 2:
        raise R1EvidenceError("R1 evidence requires two real event/transfer records")
    if records["r1_qoi"]:
        raise R1EvidenceError("R1 QoI gate ran after the first hard safety failure")

    config = records["r1_config"][0]
    if (
        _finite_float(config, "time_step") != 6.25e-4
        or _integer(config, "step_count") != 8
        or _integer(config, "split_step") != 2
        or _integer(config, "merge_step") != 3
        or _integer(config, "qoi_unit") != 501
        or config.get("damping_measure") != "barycentric_dual_area"
        or _finite_float(config, "damping_coefficient") != 10.0
        or _finite_float(config, "maximum_qoi_difference") != 2.0e-3
        or _finite_float(config, "maximum_remesh_defect") != 1.0e-12
    ):
        raise R1EvidenceError("R1 response does not match the frozen v09 configuration")
    if _integer(config, "fixed_initial_state_hash") != _integer(
        config, "remesh_initial_state_hash"
    ):
        raise R1EvidenceError("R1 fixed/remesh initial state hashes differ")
    if _finite_float(config, "initial_active_energy") <= 1.0e-2:
        raise R1EvidenceError("R1 initial active stored energy is trivial")

    samples: dict[str, list[dict[str, str]]] = {"fixed": [], "remesh": []}
    for sample in records["r1_sample"]:
        if set(sample) != SAMPLE_FIELDS:
            raise R1EvidenceError("R1 sample schema differs from the frozen schema")
        run = sample["run"]
        if run not in samples:
            raise R1EvidenceError(f"R1 sample has unknown run: {run}")
        for key in SAMPLE_FIELDS - {
            "run",
            "step",
            "revision",
            "vertex_count",
            "face_count",
            "finite",
            "state_hash",
        }:
            _finite_float(sample, key)
        for key in (
            "step",
            "revision",
            "vertex_count",
            "face_count",
            "finite",
            "state_hash",
        ):
            _integer(sample, key)
        samples[run].append(sample)
    for run in samples:
        samples[run].sort(key=lambda row: _integer(row, "step"))
    if [_integer(row, "step") for row in samples["fixed"]] != list(range(9)):
        raise R1EvidenceError("R1 fixed trajectory does not contain steps 0..8")
    if [_integer(row, "step") for row in samples["remesh"]] != list(range(4)):
        raise R1EvidenceError("R1 failed remesh trajectory does not stop at step 3")

    events = sorted(records["r1_event"], key=lambda row: _integer(row, "event_id"))
    if [row["operation"] for row in events] != ["edge_split", "edge_merge"]:
        raise R1EvidenceError("R1 real event order is not split then merge")
    if [(_integer(row, "before_revision"), _integer(row, "after_revision")) for row in events] != [
        (0, 1),
        (1, 2),
    ]:
        raise R1EvidenceError("R1 real event revisions are not 0->1->2")
    if [_integer(row, "scheduled_step") for row in events] != [2, 3]:
        raise R1EvidenceError("R1 real event schedule differs from the contract")

    ledger = records["r1_ledger"][0]
    if (
        _integer(ledger, "event_count") != 2
        or _integer(ledger, "split_event_count") != 1
        or _integer(ledger, "swap_event_count") != 0
        or _integer(ledger, "merge_event_count") != 1
    ):
        raise R1EvidenceError("R1 remesh ledger event counts are inconsistent")
    for key in ledger:
        _finite_float(ledger, key)

    gate = records["r1_gate"][0]
    expected_status = "failed_r1_geometry_cache_force_finite_gate"
    if gate.get("status") != expected_status or _integer(gate, "first_failure_step") != 3:
        raise R1EvidenceError("R1 gate did not preserve the first step-3 safety failure")
    if any(_integer(gate, key) != 0 for key in ("qoi_gate_passed", "j1_gate_passed", "passed")):
        raise R1EvidenceError("R1 downstream gates ran or passed after the first failure")

    last = samples["remesh"][-1]
    safety_checks = {
        "finite": _integer(last, "finite") == 1,
        "minimum_oriented_face_alignment": (
            _finite_float(last, "minimum_oriented_face_alignment") > 0.0
        ),
        "minimum_triangle_quality": (
            _finite_float(last, "minimum_triangle_quality") >= 0.05
        ),
        "minimum_face_area_ratio": (
            _finite_float(last, "minimum_face_area_ratio") >= 1.0e-4
        ),
        "maximum_normalized_cache_residual": (
            _finite_float(last, "maximum_normalized_cache_residual") <= 1.0e-12
        ),
        "normalized_surface_centroid_drift": (
            _finite_float(last, "normalized_centroid_drift") <= 1.0e-2
        ),
        "volume_ratio": 0.5 <= _finite_float(last, "volume_ratio") <= 1.5,
        "force_buffer_l2_norm": (
            _finite_float(last, "force_buffer_l2_norm") <= 1.0e-12
        ),
    }
    failed_safety = [name for name, passed in safety_checks.items() if not passed]
    if failed_safety != ["normalized_surface_centroid_drift"]:
        raise R1EvidenceError(
            f"R1 first failed safety criterion changed: {failed_safety}"
        )

    diagnostic_qoi: list[dict[str, Any]] = []
    initial_axis = _finite_float(config, "initial_axis_length")
    initial_energy = _finite_float(config, "initial_active_energy")
    for fixed, remesh in zip(samples["fixed"], samples["remesh"], strict=False):
        if _integer(fixed, "step") != _integer(remesh, "step"):
            raise R1EvidenceError("R1 diagnostic QoI sample keys do not close")
        diagnostic_qoi.append(
            {
                "step": _integer(fixed, "step"),
                "normalized_axis_difference": abs(
                    _finite_float(remesh, "axis_length")
                    - _finite_float(fixed, "axis_length")
                )
                / initial_axis,
                "area_ratio_difference": abs(
                    _finite_float(remesh, "area_ratio")
                    - _finite_float(fixed, "area_ratio")
                ),
                "volume_ratio_difference": abs(
                    _finite_float(remesh, "volume_ratio")
                    - _finite_float(fixed, "volume_ratio")
                ),
                "normalized_active_energy_difference": abs(
                    _finite_float(remesh, "registered_active_energy")
                    - _finite_float(fixed, "registered_active_energy")
                )
                / initial_energy,
                "adjudicated": False,
                "role": "diagnostic_only_after_first_failure",
            }
        )

    return {
        "manifest": manifests,
        "config": config,
        "samples": samples,
        "events": events,
        "transfers": sorted(
            records["r1_transfer"], key=lambda row: _integer(row, "event_id")
        ),
        "ledger": ledger,
        "gate": gate,
        "safety_checks": safety_checks,
        "diagnostic_qoi": diagnostic_qoi,
    }


def adjudicate_r1_focused_failure(evidence_dir: Path) -> dict[str, Any]:
    parsed = parse_r1_focused_evidence(evidence_dir)
    last = parsed["samples"]["remesh"][-1]
    return {
        "status": parsed["gate"]["status"],
        "first_failure_step": _integer(parsed["gate"], "first_failure_step"),
        "first_failed_criterion": "normalized_surface_centroid_drift",
        "observed": _finite_float(last, "normalized_centroid_drift"),
        "threshold": 1.0e-2,
        "fixed_sample_count": len(parsed["samples"]["fixed"]),
        "remesh_sample_count": len(parsed["samples"]["remesh"]),
        "event_count": len(parsed["events"]),
        "qoi_gate_status": "not_adjudicated_due_to_first_failure",
        "j1_gate_status": "not_adjudicated_due_to_first_failure",
        "x1_k_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
        "parsed": parsed,
    }
