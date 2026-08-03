from __future__ import annotations

import hashlib
import math
import re
import subprocess
from pathlib import Path
from typing import Any


FROZEN_FAILURE_STATUS = (
    "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind"
)
TOLERANCE = 1.0e-12
FORK_COMMIT = "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a"
SOURCE_PATHS = (
    "include/triangulation_modules/local_mesh_refiner.hpp",
    "src/triangulation_modules/local_mesh_refiner.cpp",
    "include/mesh/cell.hpp",
    "src/mesh/cell.cpp",
    "include/prl_cell_engine/remesh_contract.hpp",
)
EXPECTED_PARENT_FAILURES = {
    "prl_x1k_sphere_instantaneous_velocity_refinement",
    "prl_x1k_v04_family_b_parameterized_diagnosis",
    "prl_x1k_v06_family_c_short_trajectory_gate",
}


class V10EvidenceError(RuntimeError):
    """A required v10 raw-evidence invariant is absent or inconsistent."""


def _value(text: str) -> Any:
    if text == "true":
        return True
    if text == "false":
        return False
    if text in {"inf", "-inf", "nan"}:
        return text
    try:
        if re.fullmatch(r"[-+]?\d+", text):
            return int(text)
        return float(text)
    except ValueError:
        return text


def _record(line: str, prefix: str) -> dict[str, Any]:
    fields = line.rstrip("\r\n").split(",")
    if not fields or fields[0] != prefix:
        raise V10EvidenceError(f"unexpected record prefix for {prefix}")
    payload = fields[1:]
    if len(payload) % 2:
        raise V10EvidenceError(f"unclosed key/value schema for {prefix}")
    result: dict[str, Any] = {}
    for index in range(0, len(payload), 2):
        key = payload[index]
        if not key or key in result:
            raise V10EvidenceError(f"duplicate or empty key in {prefix}: {key}")
        result[key] = _value(payload[index + 1])
    return result


def _required_single(lines: list[str], prefix: str) -> dict[str, Any]:
    matches = [line for line in lines if line.startswith(f"{prefix},")]
    if len(matches) != 1:
        raise V10EvidenceError(
            f"expected one {prefix} record, observed {len(matches)}"
        )
    return _record(matches[0], prefix)


def _finite_number(record: dict[str, Any], key: str) -> float:
    value = record.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise V10EvidenceError(f"{key} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise V10EvidenceError(f"{key} is not finite")
    return result


def _sha_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def adjudicate_midpoint_failure(log_path: Path, exit_path: Path) -> dict[str, Any]:
    """Recompute the frozen v10 failure directly from the formal raw response."""
    if not log_path.is_file() or not exit_path.is_file():
        raise V10EvidenceError("formal response log or exit code is missing")
    try:
        output = log_path.read_text(encoding="utf-8")
        exit_code = int(exit_path.read_text(encoding="ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise V10EvidenceError("formal response evidence cannot be decoded") from error
    if exit_code != 1:
        raise V10EvidenceError(
            f"formal response exit code must preserve failure 1, observed {exit_code}"
        )

    lines = output.splitlines()
    split_gate = _required_single(lines, "v10_split_gate")
    frozen_merge = _required_single(lines, "v10_frozen_merge")
    summary = _required_single(lines, "v10_summary")
    candidates = [
        _record(line, "v10_candidate")
        for line in lines
        if line.startswith("v10_candidate,")
    ]
    candidates.sort(key=lambda row: int(row["candidate_id"]))

    if split_gate.get("passed") is not True:
        raise V10EvidenceError("split neutrality gate is not preserved")
    split_bounds = (
        "midpoint_residual",
        "original_vertex_position_residual",
        "area_jump",
        "volume_jump",
        "centroid_jump",
        "axis_jump",
        "active_energy_jump",
    )
    if any(_finite_number(split_gate, key) > TOLERANCE for key in split_bounds):
        raise V10EvidenceError("split neutrality raw values exceed the frozen tolerance")

    analytic_residual = _finite_number(frozen_merge, "analytic_residual")
    quarter_fraction = _finite_number(
        frozen_merge, "distance_from_x0_over_original_edge"
    )
    if analytic_residual > TOLERANCE:
        raise V10EvidenceError("frozen merge analytic/machine residual exceeds tolerance")
    if abs(quarter_fraction - 0.25) > TOLERANCE:
        raise V10EvidenceError("frozen merge quarter-point identity is not preserved")
    if frozen_merge.get("passed_analytic") is not True:
        raise V10EvidenceError("frozen merge analytic gate is not marked passed")

    if [row.get("candidate_id") for row in candidates] != [1, 2, 3, 4]:
        raise V10EvidenceError("candidate IDs are incomplete or non-unique")
    if any(row.get("can_be_merged") is not True for row in candidates):
        raise V10EvidenceError("the frozen four candidates are not all publicly eligible")
    for row in (candidates[0], candidates[1], candidates[3]):
        if (
            row.get("merge_succeeded") is not True
            or row.get("topology_legal") is not True
            or _finite_number(row, "analytic_residual") > TOLERANCE
        ):
            raise V10EvidenceError(
                f"completed candidate {row['candidate_id']} no longer closes"
            )
    failed = candidates[2]
    if (
        failed.get("local_0") != 2
        or failed.get("local_1") != 8
        or failed.get("merge_succeeded") is not False
    ):
        raise V10EvidenceError("first eligible-candidate failure moved from edge (2,8)")
    exception = failed.get("exception")
    if not isinstance(exception, str):
        raise V10EvidenceError("candidate 3 material-rebind exception is missing")
    match = re.fullmatch(
        r"material point cannot be rebound within the configured distance: "
        r"id=101; distance=([0-9.eE+-]+)",
        exception,
    )
    if match is None:
        raise V10EvidenceError("candidate 3 material-rebind exception changed")
    rebind_distance = float(match.group(1))
    if not math.isfinite(rebind_distance) or rebind_distance <= TOLERANCE:
        raise V10EvidenceError("candidate 3 rebind distance is not a finite hard failure")
    failed["rebind_distance"] = rebind_distance

    if summary.get("status") != FROZEN_FAILURE_STATUS:
        raise V10EvidenceError("machine summary failure status changed")
    if (
        summary.get("candidate_count") != len(candidates)
        or summary.get("eligible_count") != 4
        or summary.get("first_failed_candidate") != 3
        or summary.get("all_eligible_completed") is not False
        or summary.get("any_geometric_inverse") is not False
        or summary.get("classification_input_ready") is not False
    ):
        raise V10EvidenceError("machine summary does not close against candidate records")
    if any(row.get("geometric_inverse") is not False for row in candidates):
        raise V10EvidenceError("candidate records contradict the no-inverse summary")

    return {
        "status": FROZEN_FAILURE_STATUS,
        "first_failed_gate": "eligible_candidate_production_merge_completion",
        "first_failed_candidate": 3,
        "failure_reason": exception,
        "rebind_distance": rebind_distance,
        "threshold": TOLERANCE,
        "split_gate": split_gate,
        "frozen_merge": frozen_merge,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "eligible_count": 4,
        "any_geometric_inverse": False,
        "classification_status": "not_adjudicated_due_to_first_failure",
        "repairability_verdict": "not_adjudicated_due_to_first_failure",
        "formal_response_exit_code": exit_code,
        "raw_evidence": [_sha_record(log_path), _sha_record(exit_path)],
        "v09_status": "failed_r1_geometry_cache_force_finite_gate",
        "route_h_gate_a_v01": "failed_invalid_numerics",
        "x1_k_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
    }


def extract_machine_records(log_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Return all versioned v10 records, grouped by their machine prefix."""
    if not log_path.is_file():
        raise V10EvidenceError(f"machine log is missing: {log_path}")
    output = log_path.read_text(encoding="utf-8")
    groups: dict[str, list[dict[str, Any]]] = {}
    for line in output.splitlines():
        if not line.startswith("v10_"):
            continue
        prefix = line.split(",", 1)[0]
        groups.setdefault(prefix, []).append(_record(line, prefix))
    return groups


def _git(repo: Path, *arguments: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise V10EvidenceError(f"Git provenance command failed: {detail}")
    if binary:
        return completed.stdout
    return completed.stdout.decode("ascii").strip()


def audit_fork_source_provenance(repo_root: Path) -> dict[str, Any]:
    """Verify the audited fork files against immutable commit:path blobs."""
    fork = repo_root.resolve() / "external/simucell3d"
    head = str(_git(fork, "rev-parse", "HEAD"))
    upstream = str(_git(fork, "rev-parse", "@{upstream}"))
    if head != FORK_COMMIT or upstream != FORK_COMMIT:
        raise V10EvidenceError("controlled-fork HEAD/upstream does not match v10 contract")
    if str(_git(fork, "status", "--short")):
        raise V10EvidenceError("controlled fork is dirty")

    records: list[dict[str, Any]] = []
    source_text: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        object_name = f"{FORK_COMMIT}:{relative}"
        object_type = str(_git(fork, "cat-file", "-t", object_name))
        blob_id = str(_git(fork, "rev-parse", object_name))
        blob = _git(fork, "cat-file", "blob", object_name, binary=True)
        if not isinstance(blob, bytes):
            raise V10EvidenceError(f"Git blob read was not binary for {relative}")
        current_path = fork / relative
        current = current_path.read_bytes()
        current_blob_id = str(_git(fork, "hash-object", relative))
        raw_bytes_equal = blob == current
        verified = object_type == "blob" and blob_id == current_blob_id
        if not verified:
            raise V10EvidenceError(f"source blob verification failed for {relative}")
        try:
            source_text[relative] = current.decode("utf-8")
        except UnicodeDecodeError as error:
            raise V10EvidenceError(f"audited source is not UTF-8: {relative}") from error
        records.append(
            {
                "source_commit": FORK_COMMIT,
                "path": relative,
                "object_type": object_type,
                "source_blob_id": blob_id,
                "current_blob_id": current_blob_id,
                "sha256": hashlib.sha256(current).hexdigest(),
                "bytes": len(current),
                "source_blob_verified": verified,
                "raw_worktree_bytes_equal": raw_bytes_equal,
                "git_clean_filter_equivalent": blob_id == current_blob_id,
            }
        )

    header = source_text[SOURCE_PATHS[0]]
    implementation = source_text[SOURCE_PATHS[1]]
    contract = source_text[SOURCE_PATHS[4]]
    public_signatures = re.findall(
        r"^\s*(?:bool|void)\s+(?:can_be_merged|split_edge|merge_edge)\([^;]+;",
        header,
        re.MULTILINE,
    )
    if len(public_signatures) != 3:
        raise V10EvidenceError("public refiner signature audit did not close")
    midpoint_statement = "const vec3 n_i_pos = (n_b.pos() + n_a.pos()) * 0.5;"
    replace_first = "c->replace_node(e_ab, id_n_a, id_n_i)"
    replace_second = "c->replace_node(e_bi, id_n_b, id_n_i)"
    if any(
        marker not in implementation
        for marker in (midpoint_statement, replace_first, replace_second)
    ):
        raise V10EvidenceError("midpoint/delete-both implementation markers changed")
    event_has_identity_control = any(
        token in contract
        for token in (
            "survivor_vertex",
            "survivor_id",
            "split_ancestor",
            "collapse_position",
        )
    )
    public_header_has_identity_control = any(
        token in header.lower()
        for token in (
            "survivor",
            "ancestor",
            "endpoint_preserving",
            "collapse_position",
            "projection",
        )
    )
    return {
        "fork_commit": FORK_COMMIT,
        "head": head,
        "upstream": upstream,
        "fork_clean": True,
        "files": records,
        "public_signatures": [" ".join(item.split()) for item in public_signatures],
        "midpoint_statement_verified": True,
        "both_endpoints_replaced_verified": True,
        "public_header_identity_control_found": public_header_has_identity_control,
        "event_identity_control_found": event_has_identity_control,
        "source_capability_observation": (
            "public merge is midpoint coarsening with no survivor, ancestor-inverse, "
            "or collapse-position parameter in the audited interfaces"
        ),
        "classification_role": "supporting_not_adjudicated_due_to_first_failure",
    }


def adjudicate_v10_verification(evidence_dir: Path) -> dict[str, Any]:
    """Parse real command outputs and accept only the frozen v10 failure regression."""
    command_names = (
        "focused_build",
        "formal_response",
        "focused_regression",
        "parent_ctest",
        "fork_ctest",
        "strict_prl",
        "python_pytest",
        "ruff",
    )
    raw: dict[str, tuple[str, int, dict[str, Any]]] = {}
    for name in command_names:
        log_path = evidence_dir / f"{name}.log"
        exit_path = evidence_dir / f"{name}.exitcode"
        if not log_path.is_file() or not exit_path.is_file():
            raise V10EvidenceError(f"verification evidence missing for {name}")
        payload = log_path.read_bytes()
        try:
            output = payload.decode("utf-8")
            exit_code = int(exit_path.read_text(encoding="ascii").strip())
        except (UnicodeDecodeError, ValueError) as error:
            raise V10EvidenceError(f"verification evidence invalid for {name}") from error
        raw[name] = (
            output,
            exit_code,
            {
                "log_path": f"verification/{name}.log",
                "exitcode_path": f"verification/{name}.exitcode",
                "log_sha256": hashlib.sha256(payload).hexdigest(),
                "log_bytes": len(payload),
                "exit_code": exit_code,
            },
        )

    commands: dict[str, dict[str, Any]] = {}
    for name, marker in (
        ("focused_build", "Built target prl_x1k_v10_midpoint_collapse_diagnostic_test"),
        ("focused_regression", "v10_regression,status,passed_frozen_failure_regression"),
        ("strict_prl", "Built target prl_core"),
        ("ruff", "All checks passed!"),
    ):
        output, exit_code, record = raw[name]
        if exit_code != 0 or marker not in output:
            raise V10EvidenceError(f"verification marker/exit mismatch for {name}")
        commands[name] = {**record, "verified": True}

    formal_output, formal_exit, formal_record = raw["formal_response"]
    if formal_exit != 1 or f"v10_summary,status,{FROZEN_FAILURE_STATUS}" not in formal_output:
        raise V10EvidenceError("formal response did not preserve the frozen nonzero failure")
    commands["formal_response"] = {**formal_record, "verified": True}

    def ctest_summary(output: str, name: str) -> tuple[int, int, int]:
        matches = re.findall(
            r"\d+% tests passed,\s*(\d+) tests failed out of (\d+)", output
        )
        if not matches:
            raise V10EvidenceError(f"CTest summary missing for {name}")
        failed, total = (int(value) for value in matches[-1])
        return total - failed, failed, total

    parent_output, parent_exit, parent_record = raw["parent_ctest"]
    parent_passed, parent_failed, parent_total = ctest_summary(
        parent_output, "parent_ctest"
    )
    parent_failures = set(
        re.findall(
            r"^\s*\d+\s+-\s+(.+?)\s+\(Failed\)\s*$",
            parent_output,
            re.MULTILINE,
        )
    )
    if (
        parent_exit == 0
        or parent_failed != 3
        or parent_failures != EXPECTED_PARENT_FAILURES
        or "prl_x1k_v10_midpoint_collapse_microprobe" in parent_failures
    ):
        raise V10EvidenceError("parent regression failure set changed")
    commands["parent_ctest"] = {
        **parent_record,
        "passed": parent_passed,
        "failed": parent_failed,
        "total": parent_total,
        "failures": sorted(parent_failures),
        "v10_frozen_failure_regression_passed": True,
        "verified": True,
    }

    fork_output, fork_exit, fork_record = raw["fork_ctest"]
    fork_passed, fork_failed, fork_total = ctest_summary(fork_output, "fork_ctest")
    if fork_exit != 0 or fork_failed != 0 or fork_total <= 0:
        raise V10EvidenceError("controlled-fork regression is not all green")
    commands["fork_ctest"] = {
        **fork_record,
        "passed": fork_passed,
        "failed": fork_failed,
        "total": fork_total,
        "verified": True,
    }

    pytest_output, pytest_exit, pytest_record = raw["python_pytest"]
    pytest_matches = re.findall(r"(?:^|\s)(\d+) passed(?:[,\s]|$)", pytest_output)
    if pytest_exit != 0 or not pytest_matches:
        raise V10EvidenceError("Python regression evidence is incomplete")
    commands["python_pytest"] = {
        **pytest_record,
        "passed": int(pytest_matches[-1]),
        "verified": True,
    }
    return {
        "status": "passed_software_regression_with_frozen_v10_failure",
        "commands": commands,
        "counts_parsed_from_raw_logs": True,
        "hardcoded_verification_counts_used": False,
    }
