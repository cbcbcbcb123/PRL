from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


V10_CONTRACT_COMMIT = "e54bc5933387070c697f5c88218f37f25faea4c3"
V10_RESULT_COMMIT = "2919a5df50d9fa287fe823ee5a1bb9169c438f65"
V10R1_CONTRACT_COMMIT = "785796d409b9f43ef9657b7d6b44a10d36d5eef1"
APPROVED_BASELINE_COMMIT = "ddd663d461da7b25aefd5cf3fbecff488800053e"
FROZEN_LIFECYCLE_COMMITS = (
    "f7701d59ce3e1c94737e3b0a276205ed70fae6f8",
    "10bb2c2602b499b5a75ba2d57a35ba717e156616",
    "855bd8b7467761ba7fcdaa49632bed2ee5681e85",
    V10_CONTRACT_COMMIT,
    V10_RESULT_COMMIT,
    APPROVED_BASELINE_COMMIT,
)
V10_CONTRACT_PATH = (
    "project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_contract_v10.md"
)
V10_RUNNER_PATH = "cpp/tests/r1_midpoint_collapse_diagnostic_test.cpp"
V10_RAW_LOG_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/"
    "formal_response.log"
)
V10_RAW_EXIT_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/"
    "formal_response.exitcode"
)
V10_CANDIDATE_MATRIX_PATH = (
    "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/"
    "candidate_matrix.csv"
)
V10R1_CONTRACT_PATH = (
    "project_control/"
    "hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_"
    "contract_v10r1.md"
)
V10R1_REPORT_PATH = (
    "project_control/"
    "hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_"
    "report_v10r1.md"
)
REBINDS_DISTANCE_PATTERN = re.compile(
    r"material point cannot be rebound within the configured distance: "
    r"id=101; distance=([0-9.eE+-]+)"
)
REQUIRED_FINAL_VERIFICATION_STEMS = {
    "focused_exporter_recompute_final",
    "focused_python_final",
    "full_python_with_controlled_fork_final",
    "ruff_final",
}
EXPECTED_RED_STEMS = {
    "tdd_red_binary_topology_semantics",
    "tdd_red_integrity_seam_missing",
    "tdd_red_missing_configuration_valid",
    "tdd_red_missing_packaging_artifacts",
    "tdd_red_missing_provenance_manifest",
    "tdd_red_semantic_seam_missing",
}
SUPERSEDED_VERIFICATION_ROLES = {
    "full_python": "superseded_uninitialized_worktree_layout",
    "full_python_with_controlled_fork": "superseded_argument_invocation",
    "tdd_green_integrity_gate": "intermediate_green_regression_failure",
    "tdd_green_packaging_artifacts": "intermediate_green_syntax_failure",
    "tdd_red_missing_configuration": "superseded_environment_invocation",
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header: list[str] = []
    for row in rows:
        for key in row:
            if key not in header:
                header.append(key)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        target.write(content)


def _verification_role(stem: str, exit_code: int) -> str:
    if stem in REQUIRED_FINAL_VERIFICATION_STEMS:
        return "required_final_verification"
    if stem in EXPECTED_RED_STEMS:
        return "expected_tdd_red"
    if stem in SUPERSEDED_VERIFICATION_ROLES:
        return SUPERSEDED_VERIFICATION_ROLES[stem]
    if exit_code == 0:
        return "supporting_green_verification"
    return "retained_intermediate_failure"


def _write_verification_evidence(output_dir: Path) -> list[str]:
    verification_dir = output_dir / "verification"
    if not verification_dir.is_dir():
        return []
    artifacts = []
    commands: dict[str, dict[str, Any]] = {}
    for exit_path in sorted(verification_dir.glob("*.exitcode")):
        stem = exit_path.stem
        log_path = verification_dir / f"{stem}.log"
        if not log_path.is_file():
            raise ValueError(f"verification log is missing for {stem}")
        exit_code = int(exit_path.read_text(encoding="ascii").strip())
        role = _verification_role(stem, exit_code)
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        passed_match = re.search(r"(\d+) passed", log_text)
        commands[stem] = {
            "exit_code": exit_code,
            "role": role,
            "passed": int(passed_match.group(1)) if passed_match else None,
        }
        for path in (exit_path, log_path):
            payload = path.read_bytes()
            artifacts.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "role": role,
                }
            )
    required = {
        stem: commands.get(stem) for stem in sorted(REQUIRED_FINAL_VERIFICATION_STEMS)
    }
    required_passed = all(
        item is not None and item["exit_code"] == 0 for item in required.values()
    )
    summary = {
        "status": (
            "passed_packaging_software_verification"
            if required_passed
            else "incomplete_packaging_software_verification"
        ),
        "required": required,
        "all_commands": commands,
        "controlled_fork_commit": "e2ed64a26bb5d7c2d878772564fb5ffcca343c3a",
        "scientific_response_commands_executed": False,
        "counts_parsed_from_logs": True,
    }
    _write_json(
        output_dir / "verification_artifact_manifest.json",
        {"artifacts": artifacts},
    )
    _write_json(output_dir / "verification_summary.json", summary)
    return ["verification_artifact_manifest.json", "verification_summary.json"]


def _citation(
    commit: str,
    path: str,
    locator: str,
    value: Any,
) -> dict[str, Any]:
    return {
        "commit": commit,
        "path": path,
        "locator": locator,
        "source_value": value,
    }


def _coerce_csv_value(value: str) -> Any:
    if value == "":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if value.lower() in {"inf", "+inf", "-inf", "nan"}:
        return value
    try:
        return float(value)
    except ValueError:
        return value


def _git_text(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise ValueError(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout


def _tree_entries(repo_root: Path, commit: str, paths: list[str]) -> dict[str, str]:
    output = _git_text(repo_root, "ls-tree", "-r", commit, "--", *paths)
    entries: dict[str, str] = {}
    for line in output.splitlines():
        metadata, path = line.split("\t", 1)
        _mode, object_type, object_id = metadata.split()
        if object_type == "blob":
            entries[path] = object_id
    return entries


def verify_frozen_v10_integrity(repo_root: Path) -> dict[str, Any]:
    """Verify frozen v09/v10 Git objects and the 28 manifest entries."""
    frozen_paths: set[str] = set()
    for commit in FROZEN_LIFECYCLE_COMMITS:
        changed = _git_text(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        )
        frozen_paths.update(path for path in changed.splitlines() if path)
    ordered_paths = sorted(frozen_paths)
    baseline_entries = _tree_entries(
        repo_root,
        APPROVED_BASELINE_COMMIT,
        ordered_paths,
    )
    current_entries = _tree_entries(repo_root, "HEAD", ordered_paths)
    mismatches = [
        {
            "path": path,
            "baseline_blob": baseline_entries.get(path),
            "current_blob": current_entries.get(path),
        }
        for path in sorted(set(baseline_entries) | set(current_entries))
        if baseline_entries.get(path) != current_entries.get(path)
    ]
    worktree_output = _git_text(
        repo_root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        *ordered_paths,
    )
    worktree_changes = [line for line in worktree_output.splitlines() if line]

    v10_dir = repo_root / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10"
    raw_manifest = json.loads(
        (v10_dir / "provenance_manifest.json").read_text(encoding="utf-8")
    )["raw_evidence"]
    verification_manifest = json.loads(
        (v10_dir / "verification_artifact_manifest.json").read_text(
            encoding="utf-8"
        )
    )["artifacts"]
    entries = [*raw_manifest, *verification_manifest]
    verified = 0
    manifest_mismatches = []
    for entry in entries:
        artifact_path = repo_root / entry["path"]
        payload = artifact_path.read_bytes()
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        actual_bytes = len(payload)
        if (
            actual_sha256 == entry["sha256"]
            and actual_bytes == entry["bytes"]
        ):
            verified += 1
        else:
            manifest_mismatches.append(
                {
                    "path": entry["path"],
                    "expected_sha256": entry["sha256"],
                    "actual_sha256": actual_sha256,
                    "expected_bytes": entry["bytes"],
                    "actual_bytes": actual_bytes,
                }
            )
    repaired_candidates = repair_candidate_topology_semantics(
        repo_root / V10_CANDIDATE_MATRIX_PATH
    )
    failed = repaired_candidates[2]
    result = {
        "status": "passed_frozen_v10_v09_integrity",
        "baseline_commit": APPROVED_BASELINE_COMMIT,
        "frozen_git": {
            "lifecycle_commits": list(FROZEN_LIFECYCLE_COMMITS),
            "files_verified": len(baseline_entries),
            "mismatches": mismatches,
            "worktree_changes": worktree_changes,
        },
        "manifest_entries": {
            "expected": 28,
            "observed": len(entries),
            "verified": verified,
            "raw_evidence": len(raw_manifest),
            "verification_evidence": len(verification_manifest),
        },
        "manifest_mismatches": manifest_mismatches,
        "candidate_3_frozen_observation": {
            "merge_succeeded": failed["merge_succeeded"],
            "legacy_topology_legal_serialized": failed[
                "legacy_topology_legal_serialized"
            ],
            "rebind_distance": failed["rebind_distance"],
            "rebind_distance_threshold": failed["rebind_distance_threshold"],
            "rebind_distance_exceeded": failed["rebind_distance_exceeded"],
        },
    }
    if (
        mismatches
        or worktree_changes
        or manifest_mismatches
        or len(entries) != 28
        or verified != 28
    ):
        result["status"] = "failed_frozen_v10_v09_integrity"
    return result


def repair_candidate_topology_semantics(
    candidate_matrix_path: Path,
) -> list[dict[str, Any]]:
    """Parse the frozen matrix into the v10r1 candidate schema."""
    with candidate_matrix_path.open("r", encoding="utf-8", newline="") as source:
        rows = [
            {key: _coerce_csv_value(value) for key, value in row.items()}
            for row in csv.DictReader(source)
        ]
    if [row.get("candidate_id") for row in rows] != [1, 2, 3, 4]:
        raise ValueError("frozen v10 candidate IDs are incomplete or reordered")
    for row in rows:
        legacy_topology_value = row["topology_legal"]
        row["legacy_topology_legal_serialized"] = legacy_topology_value
        exception = row.get("exception")
        if row["merge_succeeded"] is False:
            if row["candidate_id"] != 3 or not isinstance(exception, str):
                raise ValueError("unexpected incomplete frozen v10 candidate")
            match = REBINDS_DISTANCE_PATTERN.fullmatch(exception)
            if match is None:
                raise ValueError("candidate 3 production sink exception changed")
            row["topology_status"] = (
                "not_adjudicated_due_to_production_sink_exception"
            )
            row["topology_legal"] = None
            row["rebind_distance"] = float(match.group(1))
            row["rebind_distance_threshold"] = 1.0e-12
            row["rebind_distance_exceeded"] = True
        elif legacy_topology_value is True:
            row["topology_status"] = "adjudicated_legal"
        else:
            row["topology_status"] = "adjudicated_illegal"
    return rows


def _build_configuration() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    passive_parameters = [
        {"field": "face.name", "value": "v10_zero_passive_surface"},
        {"field": "face.global_type_id", "value": 0},
        {"field": "face.surface_tension", "value": 0.0},
        {"field": "face.adherence_strength", "value": 0.0},
        {"field": "face.repulsion_strength", "value": 0.0},
        {"field": "face.bending_modulus", "value": 0.0},
        {"field": "cell.name", "value": "v10_midpoint_probe_cell"},
        {"field": "cell.global_type_id", "value": 2},
        {"field": "cell.mass_density", "value": 1.0},
        {"field": "cell.bulk_modulus", "value": 0.0},
        {"field": "cell.max_pressure", "value": 1.0e6},
        {"field": "cell.initial_pressure", "value": 0.0},
        {"field": "cell.area_elasticity_modulus", "value": 0.0},
        {"field": "cell.avg_division_volume", "value": 1.0e6},
        {"field": "cell.std_division_volume", "value": 0.0},
        {"field": "cell.avg_growth_rate", "value": 0.0},
        {"field": "cell.std_growth_rate", "value": 0.0},
        {"field": "cell.minimum_volume", "value": 1.0e-12},
        {"field": "cell.angle_regularization_factor", "value": 0.0},
        {"field": "cell.target_isoperimetric_ratio", "value": 150.0},
        {"field": "cell.surface_coupling_max_curvature", "value": 1.0e6},
    ]
    vertices = [
        [0.0, 0.0, 0.0],
        [0.0, -3.0, 0.0],
        [-1.0, -1.5, 0.0],
        [1.0, -1.5, 0.0],
        [0.0, 0.0, -1.0],
        [0.0, -3.0, -1.0],
        [-1.0, -1.5, -1.0],
        [1.0, -1.5, -1.0],
    ]
    faces = [
        [0, 1, 2],
        [0, 1, 3],
        [0, 4, 2],
        [2, 6, 4],
        [2, 6, 5],
        [5, 1, 2],
        [0, 3, 7],
        [7, 4, 0],
        [3, 1, 5],
        [5, 7, 3],
        [4, 5, 6],
        [4, 5, 7],
    ]
    material_points = [
        {
            "id": 101,
            "surface_region": "apical",
            "fiber_direction": [1.0, 0.0, 0.0],
            "activation": 0.05,
            "activation_rate": 0.0,
            "host": [0, 1, 2],
            "barycentric": [0.2, 0.3, 0.5],
            "reference_value": 0.17,
        },
        {
            "id": 205,
            "surface_region": "basal",
            "fiber_direction": [1.0, 0.0, 0.0],
            "activation": 0.0,
            "activation_rate": 0.0,
            "host": [0, 1, 3],
            "barycentric": [0.4, 0.25, 0.35],
            "reference_value": 0.23,
        },
    ]
    production_path = [
        "production MyocardialMaterialTransferSink",
        "public local_mesh_refiner",
        "public split_edge / can_be_merged / merge_edge",
        "synchronous RemeshEvent",
        "public capture_surface_snapshot and material-state getters",
    ]
    disabled_dynamics = [
        "mechanics_advance",
        "passive",
        "contact",
        "pressure",
        "ecm",
        "flow",
        "adaptive_remesh",
        "retry",
    ]
    configuration = {
        "tolerance": 1.0e-12,
        "initial_state": {
            "cell_id": 17,
            "revision": 0,
            "vertex_count": 8,
            "face_count": 12,
            "vertices": vertices,
            "faces": faces,
            "passive_parameters": passive_parameters,
            "material_points": material_points,
        },
        "material_transfer": {
            "implementation": "production MyocardialMaterialTransferSink",
            "maximum_rebind_distance": 1.0e-12,
        },
        "refiner": {
            "implementation": "public local_mesh_refiner",
            "edge_length_threshold": 0.1,
            "curvature_threshold": 10.0,
            "enable_edge_swap": True,
        },
        "active_contraction": {
            "unit_id": 501,
            "minus_material_point_id": 101,
            "plus_material_point_id": 205,
            "activation_material_point_id": 101,
            "stiffness": 10.0,
            "minimum_axis_fiber_alignment": 0.9,
        },
        "execution": {
            "production_path": production_path,
            "disabled_dynamics_and_couplings": disabled_dynamics,
            "candidate_order": "ascending local endpoint pair",
            "output_precision_digits": 17,
            "new_microprobe_run": False,
            "new_formal_response_run": False,
            "new_physical_data_generated": False,
        },
        "formal_response": {
            "expected_exit_code": 1,
            "frozen_candidate_count": 4,
            "frozen_publicly_eligible_count": 4,
            "first_failed_candidate": 3,
        },
    }

    runner_lines = {
        "configuration.tolerance": "line 33",
        "configuration.initial_state.cell_id": "lines 119-120 and 138-139",
        "configuration.initial_state.revision": "lines 138-140",
        "configuration.initial_state.vertex_count": "lines 104-113",
        "configuration.initial_state.face_count": "lines 114-118",
        "configuration.initial_state.vertices": "lines 104-113",
        "configuration.initial_state.faces": "lines 114-118",
        "configuration.initial_state.passive_parameters": "lines 73-99",
        "configuration.initial_state.material_points": "lines 131-164",
        "configuration.material_transfer.implementation": "lines 457-463",
        "configuration.material_transfer.maximum_rebind_distance": "lines 33 and 457-459",
        "configuration.refiner.implementation": "lines 595-600, 640-645, and 846-851",
        "configuration.refiner.edge_length_threshold": "lines 597, 643, and 849; argument 1",
        "configuration.refiner.curvature_threshold": "lines 597, 643, and 849; argument 2",
        "configuration.refiner.enable_edge_swap": "lines 597, 643, and 849; argument 3",
        "configuration.active_contraction.unit_id": "lines 446-455; argument contraction_unit_id",
        "configuration.active_contraction.minus_material_point_id": "lines 446-455; argument minus_material_point_id",
        "configuration.active_contraction.plus_material_point_id": "lines 446-455; argument plus_material_point_id",
        "configuration.active_contraction.activation_material_point_id": "lines 446-455; argument activation_material_point_id",
        "configuration.active_contraction.stiffness": "lines 446-455; argument stiffness",
        "configuration.active_contraction.minimum_axis_fiber_alignment": "lines 446-455; argument minimum_axis_fiber_alignment",
        "configuration.execution.output_precision_digits": "line 1037",
    }
    contract_lines = {
        "configuration.execution.production_path": "lines 34-41",
        "configuration.execution.disabled_dynamics_and_couplings": "line 32",
        "configuration.execution.candidate_order": "lines 79-83",
    }
    v10r1_contract_lines = {
        "configuration.execution.new_microprobe_run": "line 24",
        "configuration.execution.new_formal_response_run": "line 24",
        "configuration.execution.new_physical_data_generated": "line 24",
    }
    raw_locators = {
        "configuration.formal_response.expected_exit_code": (
            V10_RAW_EXIT_PATH,
            "entire file",
        ),
        "configuration.formal_response.frozen_candidate_count": (
            V10_RAW_LOG_PATH,
            "record v10_summary; key candidate_count",
        ),
        "configuration.formal_response.frozen_publicly_eligible_count": (
            V10_RAW_LOG_PATH,
            "record v10_summary; key eligible_count",
        ),
        "configuration.formal_response.first_failed_candidate": (
            V10_RAW_LOG_PATH,
            "record v10_summary; key first_failed_candidate",
        ),
    }
    values: dict[str, Any] = {}

    def collect(value: Any, prefix: str = "configuration") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                collect(child, f"{prefix}.{key}")
            return
        values[prefix] = value

    collect(configuration)
    field_provenance = []
    for field, value in values.items():
        if field in runner_lines:
            citations = [
                _citation(
                    V10_RESULT_COMMIT,
                    V10_RUNNER_PATH,
                    runner_lines[field],
                    value,
                )
            ]
        elif field in contract_lines:
            citations = [
                _citation(
                    V10_CONTRACT_COMMIT,
                    V10_CONTRACT_PATH,
                    contract_lines[field],
                    value,
                )
            ]
        elif field in v10r1_contract_lines:
            citations = [
                _citation(
                    V10R1_CONTRACT_COMMIT,
                    V10R1_CONTRACT_PATH,
                    v10r1_contract_lines[field],
                    value,
                )
            ]
        else:
            source_path, locator = raw_locators[field]
            citations = [
                _citation(V10_RESULT_COMMIT, source_path, locator, value)
            ]
        field_provenance.append(
            {"field": field, "value": value, "sources": citations}
        )
    return configuration, field_provenance


def export_v10r1_package(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    """Export the append-only v10r1 packaging repair from frozen v10 inputs."""
    integrity = verify_frozen_v10_integrity(repo_root)
    if integrity["status"] != "passed_frozen_v10_v09_integrity":
        raise ValueError("frozen v09/v10 integrity gate failed")
    configuration, field_provenance = _build_configuration()
    configuration_payload = {
        "schema_version": "x1-k-v10r1-configuration-1",
        "artifact_status": (
            "reconstructed_after_v10_freeze_for_v10r1_packaging_repair"
        ),
        "historical_v10_delivery_claim": False,
        "new_scientific_response_generated": False,
        "reconstruction_sources": {
            "v10_contract_commit": V10_CONTRACT_COMMIT,
            "v10_result_commit": V10_RESULT_COMMIT,
            "v10r1_contract_commit": V10R1_CONTRACT_COMMIT,
        },
        "configuration": configuration,
        "field_provenance": field_provenance,
    }
    _write_json(output_dir / "configuration.json", configuration_payload)

    candidates = repair_candidate_topology_semantics(
        repo_root / V10_CANDIDATE_MATRIX_PATH
    )
    candidate_payload = {
        "schema_version": "x1-k-v10r1-candidate-matrix-1",
        "source": {
            "commit": V10_RESULT_COMMIT,
            "path": V10_CANDIDATE_MATRIX_PATH,
        },
        "topology_status_vocabulary": {
            "adjudicated_legal": (
                "production merge completed and the frozen post-merge topology audit passed"
            ),
            "not_adjudicated_due_to_production_sink_exception": (
                "production merge raised before the post-merge topology audit"
            ),
            "adjudicated_illegal": (
                "reserved for a completed post-merge topology audit that fails; unused here"
            ),
        },
        "candidates": candidates,
    }
    _write_json(output_dir / "candidate_matrix_v10r1.json", candidate_payload)
    _write_csv(output_dir / "candidate_matrix_v10r1.csv", candidates)

    failed = candidates[2]
    erratum = {
        "erratum_id": "ERRATUM-PRL-HYBRID-X1-K-V10R1-CANDIDATE-3-TOPOLOGY",
        "scope": "evidence_packaging_semantic_repair_only",
        "source": {
            "commit": V10_RESULT_COMMIT,
            "runner_path": V10_RUNNER_PATH,
            "runner_default_locator": "lines 617-625",
            "runner_exception_locator": "lines 691-711",
            "runner_post_merge_audit_locator": "lines 714-750",
            "raw_path": V10_RAW_LOG_PATH,
            "raw_locator": "record v10_candidate; candidate_id=3",
            "candidate_matrix_path": V10_CANDIDATE_MATRIX_PATH,
            "candidate_matrix_locator": "candidate_id=3",
        },
        "original_serialization": {
            "merge_succeeded": False,
            "topology_legal": False,
            "exception": failed["exception"],
            "rebind_distance": failed["rebind_distance"],
        },
        "cause": (
            "CandidateResult.topology_legal was default-initialized to false; the production "
            "sink exception returned before the post-merge topology audit, and the exception "
            "branch serialized that default boolean."
        ),
        "corrected_semantics": {
            "merge_succeeded": False,
            "topology_status": (
                "not_adjudicated_due_to_production_sink_exception"
            ),
            "topology_legal": None,
            "exception": failed["exception"],
            "rebind_distance": failed["rebind_distance"],
            "rebind_distance_threshold": 1.0e-12,
        },
        "preservation": {
            "frozen_v10_bytes_modified": False,
            "legacy_serialized_value_retained_as_provenance": True,
            "merge_succeeded_rewritten": False,
            "candidate_declared_legal": False,
            "new_scientific_adjudication": False,
        },
    }
    _write_json(output_dir / "semantic_erratum.json", erratum)

    criteria = [
        {
            "order": 1,
            "role": "packaging_repair",
            "criterion": "configuration_artifact_reconstructed_with_field_provenance",
            "observed": f"{len(field_provenance)} fields closed",
            "passed": True,
            "scientific_adjudication": False,
            "provenance": "configuration.json",
        },
        {
            "order": 2,
            "role": "semantic_repair",
            "criterion": "candidate_topology_status_is_exception_aware",
            "observed": "1/2/4 adjudicated_legal; 3 not_adjudicated_due_to_production_sink_exception",
            "passed": True,
            "scientific_adjudication": False,
            "provenance": "candidate_matrix_v10r1.csv; semantic_erratum.json",
        },
        {
            "order": 3,
            "role": "scientific_state_preservation",
            "criterion": "frozen_v10_failure_and_non_authorization_preserved",
            "observed": "v10 failed; classification not adjudicated; downstream false",
            "passed": True,
            "scientific_adjudication": False,
            "provenance": "summary.json",
        },
    ]
    _write_csv(output_dir / "criteria.csv", criteria)

    summary = {
        "contract_id": (
            "CONTRACT-PRL-HYBRID-X1-K-V10R1-EVIDENCE-PACKAGING-SEMANTIC-REPAIR"
        ),
        "contract_commit": V10R1_CONTRACT_COMMIT,
        "v10_contract_commit": V10_CONTRACT_COMMIT,
        "v10_result_commit": V10_RESULT_COMMIT,
        "status": "packaging_repair_complete_scientific_failure_preserved",
        "v10_scientific_status": (
            "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind"
        ),
        "classification_status": "not_adjudicated_due_to_first_failure",
        "candidate_3_topology_status": (
            "not_adjudicated_due_to_production_sink_exception"
        ),
        "candidate_3_merge_succeeded": False,
        "candidate_3_rebind_distance": 0.047434164902525666,
        "candidate_3_rebind_distance_threshold": 1.0e-12,
        "x1_k_passed": False,
        "r1_passed": False,
        "c1_f1": "not_executed",
        "downstream_authorized": False,
        "new_microprobe_run": False,
        "new_formal_response_run": False,
        "new_physical_data_generated": False,
        "frozen_v10_modified": False,
        "configuration_artifact_status": (
            "reconstructed_after_v10_freeze_for_v10r1_packaging_repair"
        ),
        "historical_v10_configuration_delivery_claim": False,
    }
    _write_json(output_dir / "summary.json", summary)
    _write_text(
        output_dir / "reproduction_commands.md",
        """# X1-K v10r1 packaging repair recomputation commands

本包只读取并核验冻结 v10 文件；无需也不得重跑 C++ 科学响应、microprobe 或 formal R1 response。

```powershell
$env:PYTHONPATH = "src"
python scripts/export_x1k_r1_v10r1.py --repo-root . --output-dir results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1
python -m pytest tests/test_r1_midpoint_packaging_repair.py -q
$controlledParentRoot = "PATH_TO_EXISTING_PARENT_WORKTREE_WITH_POPULATED_CONTROLLED_FORK"
python scripts/run_x1k_v10r1_python_tests.py --controlled-parent-root $controlledParentRoot -- -q
ruff check .
```
""",
    )
    _write_json(output_dir / "frozen_integrity.json", integrity)

    configuration_fields = {item["field"]: item["value"] for item in field_provenance}
    fields_closed = 0
    source_objects: set[tuple[str, str]] = set()
    for item in field_provenance:
        if all(
            citation["source_value"] == configuration_fields[item["field"]]
            for citation in item["sources"]
        ):
            fields_closed += 1
        for citation in item["sources"]:
            source_objects.add((citation["commit"], citation["path"]))
    for commit, path in sorted(source_objects):
        _git_text(repo_root, "cat-file", "-e", f"{commit}:{path}")

    verification_names = _write_verification_evidence(output_dir)
    generated_names = [
        "candidate_matrix_v10r1.csv",
        "candidate_matrix_v10r1.json",
        "configuration.json",
        "criteria.csv",
        "frozen_integrity.json",
        "reproduction_commands.md",
        "semantic_erratum.json",
        "summary.json",
        *verification_names,
    ]
    generated_artifacts = []
    for name in generated_names:
        payload = (output_dir / name).read_bytes()
        generated_artifacts.append(
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    report_path = repo_root / V10R1_REPORT_PATH
    if report_path.is_file():
        report_payload = report_path.read_bytes()
        generated_artifacts.append(
            {
                "path": V10R1_REPORT_PATH,
                "sha256": hashlib.sha256(report_payload).hexdigest(),
                "bytes": len(report_payload),
            }
        )
    manifest = {
        "schema_version": "x1-k-v10r1-provenance-manifest-1",
        "status": "passed_v10r1_provenance_closure",
        "contract_commit": V10R1_CONTRACT_COMMIT,
        "approved_baseline_commit": APPROVED_BASELINE_COMMIT,
        "v10_contract_commit": V10_CONTRACT_COMMIT,
        "v10_result_commit": V10_RESULT_COMMIT,
        "frozen_manifest_entries": {
            "expected": 28,
            "observed": integrity["manifest_entries"]["observed"],
            "verified": integrity["manifest_entries"]["verified"],
        },
        "configuration_provenance": {
            "fields": len(field_provenance),
            "fields_closed": fields_closed,
            "source_objects_verified": len(source_objects),
        },
        "generated_artifacts": generated_artifacts,
        "manifest_exclusions": [
            "provenance_manifest.json (self-referential hash)",
            "remote_sync.json (third-stage artifact)",
        ],
        "frozen_inputs_copied": False,
        "new_scientific_response_generated": False,
    }
    if fields_closed != len(field_provenance):
        manifest["status"] = "failed_v10r1_provenance_closure"
        raise ValueError("configuration field provenance is not closed")
    _write_json(output_dir / "provenance_manifest.json", manifest)
    return summary
