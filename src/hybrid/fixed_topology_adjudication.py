from __future__ import annotations

import csv
import hashlib
import io
import math
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


class EvidenceIntegrityError(RuntimeError):
    """A required frozen evidence input is absent or inconsistent."""

    def __init__(
        self,
        message: str,
        *,
        reason: str = "evidence_integrity_failure",
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.path = path


@dataclass(frozen=True)
class EvidenceSpec:
    path: str
    source_commit: str
    sha256: str
    row_count: int
    schema: tuple[str, ...]
    source_path: str | None = None


@dataclass(frozen=True)
class ProvenanceRecord:
    path: str
    source_commit: str
    sha256: str
    row_count: int
    schema: tuple[str, ...]
    source_blob_id: str
    current_blob_id: str
    source_blob_verified: bool
    verified: bool


@dataclass(frozen=True)
class DecisionRecord:
    role: str
    scope: str
    criterion: str
    operator: str
    threshold: str
    observed: Any
    passed: bool
    provenance: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class AdjudicationDecision:
    status: str
    evidence_integrity_passed: bool
    revised_d1_passed: bool
    revised_s1_passed: bool
    provenance: tuple[ProvenanceRecord, ...]
    decisions: tuple[DecisionRecord, ...]
    metrics: dict[str, Any]
    ledger_recomputations: dict[str, Any]
    historical_statuses: dict[str, str]
    x1_k_passed: bool
    r1_c1_f1_status: str
    downstream_authorized: bool
    pointwise_convergence_claim_allowed: bool
    uniform_convergence_claim_allowed: bool


V05_COMMIT = "51d606b1165c3c0ca0839e59aebce3e1a89ca640"
V06_COMMIT = "eb3c97339580e3d2e0f565e47b9b78dab292046e"
V07_COMMIT = "f4df24c840f357fc06a45c4406bc55b9817199b9"

V05_PREFIX = "results/hybrid/x1_k_mesh_family_v05/"
V06_PREFIX = "results/hybrid/x1_k_family_c_trajectory_v06/"
V07_PREFIX = "results/hybrid/x1_k_mean_radius_v07/"

LEVEL_SCHEMA = tuple(
    "family,source_level,vertices,triangles,h_min,h_rms,h_max,"
    "directional_residual,legacy_cache_ratio,normal_velocity_relative_l2,"
    "tangential_velocity_relative_l2,normalized_net_force_residual,"
    "minimum_triangle_quality,minimum_outward_alignment,"
    "minimum_face_to_mean_area_ratio,maximum_radius_deviation,"
    "euler_characteristic,closed_two_manifold,positive_signed_volume,"
    "all_face_origin_contributions_positive,no_self_intersection_proxy_passed,"
    "symmetry_class_count,maximum_symmetry_class_size,exact_normal_velocity".split(",")
)
V05_CRITERIA_SCHEMA = tuple(
    "family,criterion,operator,threshold,observed,passed,notes".split(",")
)
ERROR_REGION_SCHEMA = tuple(
    "family,source_level,region,vertex_count,control_area,normal_error_energy,"
    "fraction_of_total_error_energy,area_weighted_relative_rms,"
    "maximum_pointwise_relative_error".split(",")
)
VALENCE_SCHEMA = tuple(
    "family,source_level,valence,vertex_count,normal_absolute_error_mean,"
    "normal_absolute_error_maximum,normal_absolute_error_rms,"
    "tangential_speed_mean,tangential_speed_maximum,tangential_speed_rms".split(",")
)
ERROR_ORDER_SCHEMA = tuple(
    "family,coarse_source_level,fine_source_level,total_error_energy_order,"
    "valence_5_error_energy_order,valence_6_error_energy_order,"
    "valence_5_closed_one_ring_error_energy_order".split(",")
)
SYMMETRY_CLASS_SCHEMA = tuple(
    "family,source_level,group_id,valence,vertex_count,"
    "normal_absolute_error_mean,normal_absolute_error_maximum,"
    "normal_absolute_error_rms,tangential_speed_mean,"
    "tangential_speed_maximum,tangential_speed_rms".split(",")
)
SYMMETRY_GATE_SCHEMA = tuple(
    "family,source_level,vertex_count,symmetry_class_count,"
    "maximum_symmetry_class_size,minimum_required_class_count,"
    "class_size_passed,class_count_passed,passed".split(",")
)
QOI_SCHEMA = tuple(
    "qoi,exact_final_value,reported_finest_excursion,level_1_response,"
    "level_2_response,level_3_response,level_4_response,level_1_excursion,"
    "level_2_excursion,level_3_excursion,level_4_excursion,"
    "level_1_analytic_error,level_2_analytic_error,level_3_analytic_error,"
    "level_4_analytic_error,analytic_order_1_2,analytic_order_2_3,"
    "analytic_order_3_4,difference_excursion_1_2,difference_excursion_2_3,"
    "difference_excursion_3_4,adjacent_difference_1_2,"
    "adjacent_difference_2_3,adjacent_difference_3_4,"
    "generalized_order_1_2_3,generalized_order_2_3_4,"
    "analytic_roundoff_plateau,analytic_errors_monotonic,"
    "analytic_orders_passed,finest_error_passed,"
    "self_convergence_roundoff_plateau,self_convergence_monotonic,"
    "self_convergence_orders_passed,passed".split(",")
)
TIME_POLLUTION_SCHEMA = tuple(
    "qoi,dt_response,dt_half_response,exact_final_value,exact_excursion,"
    "absolute_time_difference,excursion_normalized_time_difference,"
    "absolute_space_proxy,excursion_normalized_space_proxy,"
    "roundoff_plateau,passed".split(",")
)
RAW_GATE_SCHEMA = ("criterion", "observed")
GLOBAL_STEP_SCHEMA_V06 = tuple(
    "run,source_level,time_step,step,time,initial_h_rms,exact_radius,"
    "control_area_mean_radius,control_area_mean_radius_ratio,area_ratio,"
    "volume_ratio,registered_energy_ratio,normalized_surface_centroid_drift,"
    "minimum_oriented_face_alignment,minimum_triangle_quality,"
    "minimum_face_area_ratio,maximum_normalized_cache_residual".split(",")
)
GLOBAL_STEP_SCHEMA_V07 = ("family", *GLOBAL_STEP_SCHEMA_V06[1:])
LOCAL_STEP_SCHEMA_V06 = tuple(
    "run,source_level,time_step,step,time,"
    "maximum_valence_five_excursion_error,rms_valence_five_radial_error,"
    "maximum_closed_one_ring_excursion_error,"
    "rms_closed_one_ring_radial_error,maximum_valence_five_error_over_initial_h,"
    "maximum_closed_one_ring_error_over_initial_h,"
    "maximum_closed_one_ring_edge_scaling_error,"
    "local_minimum_triangle_quality,local_minimum_triangle_quality_ratio,"
    "valence_five_normal_error_energy_fraction,"
    "valence_five_normal_error_relative_rms,"
    "valence_five_normal_error_pointwise_maximum,"
    "closed_one_ring_normal_error_energy_fraction,"
    "closed_one_ring_normal_error_relative_rms,"
    "closed_one_ring_normal_error_pointwise_maximum,force_buffers_cleared".split(",")
)
LOCAL_STEP_SCHEMA_V07 = ("family", *LOCAL_STEP_SCHEMA_V06[1:])
ENERGY_SCHEMA_V06 = tuple(
    "run,source_level,time_step,step,time,registered_surface_energy,delta_psi,"
    "viscous_dissipation,delta_psi_plus_d_zeta,"
    "positive_delta_psi_plus_d_zeta,"
    "cumulative_positive_delta_psi_plus_d_zeta".split(",")
)
ENERGY_SCHEMA_V07 = ("family", *ENERGY_SCHEMA_V06[1:])
STRUCTURAL_SCHEMA = tuple(
    "family,source_level,vertex_count,face_count,initial_h_rms,surface_area,"
    "dual_area_sum,dual_area_to_surface_area_ratio,"
    "homogeneity_force_contraction,exact_homogeneity_force_contraction,"
    "normalized_homogeneity_residual,mean_radial_velocity,"
    "exact_mean_radial_velocity,normalized_mean_radial_velocity_residual,"
    "normalized_net_force_residual,maximum_relative_radius_deviation,"
    "maximum_position_displacement,position_hash_before,position_hash_after,"
    "state_hash_before,state_hash_after,maximum_force_buffer_norm_after,"
    "force_buffers_cleared,passed".split(",")
)
TIME_DIAGNOSIS_SCHEMA = tuple(
    "family,source_level,initial_h_rms,exact_mean_radius_response,"
    "response_dt_4e_4,response_dt_2e_4,response_dt_1e_4,response_dt_5e_5,"
    "difference_4e_4_to_2e_4,difference_2e_4_to_1e_4,"
    "difference_1e_4_to_5e_5,observed_order_0,observed_order_1,"
    "richardson_response,richardson_error,area_ratio_dt_4e_4,"
    "area_ratio_dt_2e_4,area_ratio_dt_1e_4,area_ratio_dt_5e_5,"
    "volume_ratio_dt_4e_4,volume_ratio_dt_2e_4,volume_ratio_dt_1e_4,"
    "volume_ratio_dt_5e_5,registered_energy_ratio_dt_4e_4,"
    "registered_energy_ratio_dt_2e_4,registered_energy_ratio_dt_1e_4,"
    "registered_energy_ratio_dt_5e_5,common_roundoff_plateau,"
    "differences_strictly_decreased,time_orders_passed,richardson_passed,"
    "minimum_oriented_face_alignment,minimum_triangle_quality,"
    "minimum_face_area_ratio,maximum_normalized_cache_residual,"
    "maximum_normalized_centroid_drift,"
    "maximum_normalized_positive_energy_residual,"
    "maximum_valence_five_excursion_error,"
    "maximum_closed_one_ring_excursion_error,"
    "maximum_valence_five_error_over_initial_h,"
    "maximum_closed_one_ring_error_over_initial_h,"
    "maximum_closed_one_ring_edge_scaling_error,"
    "minimum_local_triangle_quality_ratio,force_buffers_cleared,"
    "readonly_controls_passed,passed".split(",")
)


def _spec(
    prefix: str,
    name: str,
    commit: str,
    sha256: str,
    rows: int,
    schema: tuple[str, ...],
) -> EvidenceSpec:
    return EvidenceSpec(prefix + name, commit, sha256, rows, schema)


EVIDENCE_SPECS = (
    _spec(V05_PREFIX, "family_c_levels.csv", V05_COMMIT, "8cecf41ecef3e9a14c24d41f64c86e19cc78eab65182870b0d3ec8d1524d9eec", 4, LEVEL_SCHEMA),
    _spec(V05_PREFIX, "criteria.csv", V05_COMMIT, "09bbbb1f4934a483c5074fc3c920588b42278e6567811337cb99ef854eacd5e1", 23, V05_CRITERIA_SCHEMA),
    _spec(V05_PREFIX, "family_c_error_regions.csv", V05_COMMIT, "23f2990fd188c42ce85ef03ec1285e9f55f81fcb982786f23da23b630d087a07", 12, ERROR_REGION_SCHEMA),
    _spec(V05_PREFIX, "family_c_valence.csv", V05_COMMIT, "9e2cc640cc358d78403b43897cdc6cdefbdbe86a3d88d2b3f25f214d56bb8bbb", 8, VALENCE_SCHEMA),
    _spec(V05_PREFIX, "family_c_valence5_one_ring.csv", V05_COMMIT, "0b529e924766d9c2310628769cdef74f82245d1fa1977b858f817a5558c52de1", 4, ERROR_REGION_SCHEMA),
    _spec(V05_PREFIX, "family_c_error_energy_orders.csv", V05_COMMIT, "a472eb71b98bc2f89ba0a65d4b1f9ba40937472664cc28bf41fa9b3bb2d794ab", 3, ERROR_ORDER_SCHEMA),
    _spec(V05_PREFIX, "family_c_symmetry_classes.csv", V05_COMMIT, "c841a56700db051c5b5b230532c4694f1e1c77491a0a0db1bc3dafd07c2127a9", 1704, SYMMETRY_CLASS_SCHEMA),
    _spec(V05_PREFIX, "family_c_symmetry_gate.csv", V05_COMMIT, "a5e9fc8c61b6d0e59959bbe7782fd4a08a8752ba0c408a41d8951950b3cecffd", 4, SYMMETRY_GATE_SCHEMA),
    _spec(V06_PREFIX, "final_qoi_gate.csv", V06_COMMIT, "6857f1f6d9f415ee17d7c829e98aa835f4d78bf4739b4dd5a83933700ae67699", 4, QOI_SCHEMA),
    _spec(V06_PREFIX, "time_pollution.csv", V06_COMMIT, "9b93ad99a1b0b4843f2af45938a36c6dbad60ed33759f6245358a76a3fd931e0", 4, TIME_POLLUTION_SCHEMA),
    _spec(V06_PREFIX, "raw_global_gate.csv", V06_COMMIT, "3f6bb4f9001d784d5be73812f7bf54f0b8db2e64e852abac3f7cdd1d88d5dcea", 22, RAW_GATE_SCHEMA),
    _spec(V06_PREFIX, "family_c_level_1_steps.csv", V06_COMMIT, "265783f2784e87aa688047f8169e26d4688443c46c30615a493220431b7cc53f", 201, GLOBAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "family_c_level_2_steps.csv", V06_COMMIT, "9b989dbba0d1b9324b69f050c9f5b00b1cc0f371285177be20c320eea0582f46", 201, GLOBAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "family_c_level_3_steps.csv", V06_COMMIT, "9f62870379142191123bb36396b869af1953c3b9372b8a7ca2992f6ef5005de1", 201, GLOBAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "family_c_level_4_steps.csv", V06_COMMIT, "28ff835aefda74346f3a7fdb203da567fad5c4089e7d53dc16c9346365792690", 201, GLOBAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "family_c_level_4_dt_half_steps.csv", V06_COMMIT, "f8094a551499093745172c2e054c72ec3bdebdb346b4f38f97ab35043e15e21d", 401, GLOBAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "local_step_metrics.csv", V06_COMMIT, "76315a41a338c017b676f1149dfd8f8b34ea87ff443ade7267f1192c585e28c8", 1205, LOCAL_STEP_SCHEMA_V06),
    _spec(V06_PREFIX, "energy_ledger.csv", V06_COMMIT, "9731e54fce82ff9946ebb78decc52f5914f87a221a7ea7c804f0c98b67c8c68e", 1205, ENERGY_SCHEMA_V06),
    _spec(V07_PREFIX, "structural_identity.csv", V07_COMMIT, "8c8e2c3de7c8ff878e1b4758113fe8825f51f2cf1484f885e5f5ac114cd74f05", 4, STRUCTURAL_SCHEMA),
    _spec(V07_PREFIX, "time_diagnosis.csv", V07_COMMIT, "927773dfdde391b12938b36d1b9b02a3b9002b3b6b8e1266dacb95a5f81d6c3d", 2, TIME_DIAGNOSIS_SCHEMA),
    _spec(V07_PREFIX, "global_step_metrics.csv", V07_COMMIT, "dd2c1d1430cd459f7fdd1eeed8435e55818d2983ebfaba200cc87f973c628aab", 1508, GLOBAL_STEP_SCHEMA_V07),
    _spec(V07_PREFIX, "local_step_metrics.csv", V07_COMMIT, "e20a8ce622dc46e90153a734fa6ccf6baa891d5a4945aa0e92995a43394aa128", 1508, LOCAL_STEP_SCHEMA_V07),
    _spec(V07_PREFIX, "energy_ledger.csv", V07_COMMIT, "f345a6451c6dd065665a0c3c9729a7d255f197807eb45cc3ed4d569a739890be", 1508, ENERGY_SCHEMA_V07),
)

HISTORICAL_STATUSES = {
    "route_h_gate_a_v01": "failed_invalid_numerics",
    "v02_d1": "failed_instantaneous_smooth_surface_refinement",
    "v04_family_b": "failed_family_B_parameterized_diagnosis",
    "v06_mean_radius_spatial": (
        "failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic"
    ),
}


def _fail_integrity(
    message: str,
    *,
    reason: str = "evidence_integrity_failure",
    path: str | None = None,
) -> None:
    raise EvidenceIntegrityError(message, reason=reason, path=path)


def _as_float(row: dict[str, str], field: str, path: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        _fail_integrity(f"invalid numeric field {field} in {path}: {error}")
    if not math.isfinite(value):
        _fail_integrity(f"non-finite field {field} in {path}")
    return value


def _as_int(row: dict[str, str], field: str, path: str) -> int:
    value = _as_float(row, field, path)
    integer = int(value)
    if value != integer:
        _fail_integrity(f"non-integral field {field} in {path}")
    return integer


def _close(left: float, right: float, scale: float = 1.0) -> bool:
    return abs(left - right) <= 1.0e-12 * max(scale, abs(left), abs(right))


def _git(
    workspace_root: Path,
    arguments: list[str],
    *,
    text_output: bool = True,
) -> subprocess.CompletedProcess[Any]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=workspace_root,
            capture_output=True,
            check=False,
            text=text_output,
        )
    except OSError as error:
        _fail_integrity(
            f"git object verification could not run: {error}",
            reason="git_object_verification_unavailable",
        )


def _load_evidence(
    workspace_root: Path,
    evidence_specs: tuple[EvidenceSpec, ...],
) -> tuple[dict[str, list[dict[str, str]]], tuple[ProvenanceRecord, ...]]:
    loaded: dict[str, list[dict[str, str]]] = {}
    provenance: list[ProvenanceRecord] = []
    forbidden = {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}
    for spec in evidence_specs:
        path = workspace_root / spec.path
        if not path.is_file():
            _fail_integrity(f"missing required evidence: {spec.path}")
        payload = path.read_bytes()
        observed_hash = hashlib.sha256(payload).hexdigest()
        if observed_hash != spec.sha256:
            _fail_integrity(
                f"sha256 mismatch for {spec.path}: expected {spec.sha256}, observed {observed_hash}",
                reason="sha256_mismatch",
                path=spec.path,
            )
        commit_check = _git(
            workspace_root,
            ["rev-parse", "--verify", f"{spec.source_commit}^{{commit}}"],
        )
        if commit_check.returncode != 0:
            _fail_integrity(
                f"source commit does not exist for {spec.path}: "
                f"{spec.source_commit}",
                reason="source_commit_missing",
                path=spec.path,
            )
        source_path = spec.source_path or spec.path
        source_ref = f"{spec.source_commit}:{source_path}"
        source_id_result = _git(
            workspace_root,
            ["rev-parse", "--verify", source_ref],
        )
        if source_id_result.returncode != 0:
            _fail_integrity(
                f"source path does not exist at frozen commit for {spec.path}: "
                f"{source_ref}",
                reason="source_path_missing",
                path=spec.path,
            )
        source_blob_id = source_id_result.stdout.strip()
        source_type_result = _git(workspace_root, ["cat-file", "-t", source_ref])
        if (
            source_type_result.returncode != 0
            or source_type_result.stdout.strip() != "blob"
        ):
            _fail_integrity(
                f"source object is not a blob for {spec.path}: {source_ref}",
                reason="source_object_not_blob",
                path=spec.path,
            )
        source_bytes_result = _git(
            workspace_root,
            ["cat-file", "blob", source_ref],
            text_output=False,
        )
        if source_bytes_result.returncode != 0:
            _fail_integrity(
                f"source blob could not be read for {spec.path}: {source_ref}",
                reason="source_blob_unreadable",
                path=spec.path,
            )
        current_id_result = _git(
            workspace_root,
            ["hash-object", "--no-filters", "--", spec.path],
        )
        if current_id_result.returncode != 0:
            _fail_integrity(
                f"current blob id could not be computed for {spec.path}",
                reason="current_blob_unreadable",
                path=spec.path,
            )
        current_blob_id = current_id_result.stdout.strip()
        if source_bytes_result.stdout != payload or source_blob_id != current_blob_id:
            _fail_integrity(
                f"source blob differs from current evidence for {spec.path}: "
                f"source {source_blob_id}, current {current_blob_id}",
                reason="source_blob_mismatch",
                path=spec.path,
            )
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            _fail_integrity(f"invalid UTF-8 in {spec.path}: {error}")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if tuple(reader.fieldnames or ()) != spec.schema:
            _fail_integrity(
                f"schema mismatch for {spec.path}: expected {spec.schema}, observed {reader.fieldnames}"
            )
        rows = list(reader)
        if len(rows) != spec.row_count:
            _fail_integrity(
                f"row-count mismatch for {spec.path}: expected {spec.row_count}, observed {len(rows)}"
            )
        for row_index, row in enumerate(rows, start=1):
            if None in row or any(value is None for value in row.values()):
                _fail_integrity(f"ragged CSV row {row_index} in {spec.path}")
            for value in row.values():
                if value.strip().lower() in forbidden:
                    _fail_integrity(
                        f"non-finite token at row {row_index} in {spec.path}"
                    )
        loaded[spec.path] = rows
        provenance.append(
            ProvenanceRecord(
                path=spec.path,
                source_commit=spec.source_commit,
                sha256=observed_hash,
                row_count=len(rows),
                schema=spec.schema,
                source_blob_id=source_blob_id,
                current_blob_id=current_blob_id,
                source_blob_verified=True,
                verified=True,
            )
        )
    return loaded, tuple(provenance)


def _unique_map(
    rows: list[dict[str, str]],
    key_fields: tuple[str, ...],
    path: str,
) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key in result:
            _fail_integrity(f"duplicate key {key} in {path}")
        result[key] = row
    return result


def _step_key(row: dict[str, str], owner_field: str) -> tuple[str, ...]:
    return tuple(row[field] for field in (owner_field, "source_level", "time_step", "step", "time"))


def _validate_run_matrix(
    global_rows: list[dict[str, str]],
    local_rows: list[dict[str, str]],
    energy_rows: list[dict[str, str]],
    owner_field: str,
    expected: dict[tuple[str, int, float], int],
    label: str,
) -> None:
    run_groups: dict[tuple[str, int, float], list[dict[str, str]]] = {}
    global_keys: set[tuple[str, ...]] = set()
    for row in global_rows:
        owner = row[owner_field]
        level = _as_int(row, "source_level", label)
        time_step = _as_float(row, "time_step", label)
        run_key = (owner, level, time_step)
        run_groups.setdefault(run_key, []).append(row)
        key = _step_key(row, owner_field)
        if key in global_keys:
            _fail_integrity(f"duplicate global step key {key} in {label}")
        global_keys.add(key)
    if set(run_groups) != set(expected):
        _fail_integrity(
            f"run matrix mismatch in {label}: expected {set(expected)}, observed {set(run_groups)}"
        )
    for run_key, rows in run_groups.items():
        rows.sort(key=lambda row: _as_int(row, "step", label))
        expected_count = expected[run_key]
        if len(rows) != expected_count:
            _fail_integrity(f"run length mismatch for {run_key} in {label}")
        initial_h = _as_float(rows[0], "initial_h_rms", label)
        for expected_step, row in enumerate(rows):
            step = _as_int(row, "step", label)
            time = _as_float(row, "time", label)
            time_step = _as_float(row, "time_step", label)
            if step != expected_step or not _close(time, step * time_step):
                _fail_integrity(f"non-contiguous step/time for {run_key} in {label}")
            if not _close(_as_float(row, "initial_h_rms", label), initial_h):
                _fail_integrity(f"initial h changed for {run_key} in {label}")
        if not _close(_as_float(rows[-1], "time", label), 2.0e-2):
            _fail_integrity(f"final time changed for {run_key} in {label}")
    local_keys = {_step_key(row, owner_field) for row in local_rows}
    energy_keys = {_step_key(row, owner_field) for row in energy_rows}
    if len(local_keys) != len(local_rows) or len(energy_keys) != len(energy_rows):
        _fail_integrity(f"duplicate local or energy key in {label}")
    if global_keys != local_keys or global_keys != energy_keys:
        _fail_integrity(f"global/local/energy keys do not close in {label}")


def _recompute_ledger(
    rows: list[dict[str, str]], owner_field: str, label: str
) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row[owner_field], row["source_level"], row["time_step"])
        groups.setdefault(key, []).append(row)
    maximum_normalized_positive = 0.0
    for run_key, run_rows in groups.items():
        run_rows.sort(key=lambda row: _as_int(row, "step", label))
        initial_energy = _as_float(run_rows[0], "registered_surface_energy", label)
        if initial_energy <= 0.0:
            _fail_integrity(f"non-positive initial registered energy for {run_key}")
        previous_energy: float | None = None
        cumulative = 0.0
        for row in run_rows:
            energy = _as_float(row, "registered_surface_energy", label)
            reported_delta = _as_float(row, "delta_psi", label)
            dissipation = _as_float(row, "viscous_dissipation", label)
            residual = _as_float(row, "delta_psi_plus_d_zeta", label)
            positive = _as_float(row, "positive_delta_psi_plus_d_zeta", label)
            reported_cumulative = _as_float(
                row, "cumulative_positive_delta_psi_plus_d_zeta", label
            )
            delta = 0.0 if previous_energy is None else energy - previous_energy
            tolerance_scale = max(1.0, abs(energy))
            if not _close(delta, reported_delta, tolerance_scale):
                _fail_integrity(f"delta_psi does not recompute for {run_key}")
            if not _close(delta + dissipation, residual, tolerance_scale):
                _fail_integrity(f"energy residual does not recompute for {run_key}")
            expected_positive = max(0.0, residual)
            if not _close(expected_positive, positive, tolerance_scale):
                _fail_integrity(f"positive energy residual changed for {run_key}")
            cumulative += expected_positive
            if not _close(cumulative, reported_cumulative, tolerance_scale):
                _fail_integrity(f"cumulative energy residual changed for {run_key}")
            previous_energy = energy
        maximum_normalized_positive = max(
            maximum_normalized_positive, cumulative / initial_energy
        )
    return {
        "rows": len(rows),
        "runs": len(groups),
        "maximum_normalized_cumulative_positive_residual": maximum_normalized_positive,
        "ledger_recomputed": True,
        "coverage": "surface_tension_only",
    }


def _observed_order(
    coarse_error: float, fine_error: float, coarse_h: float, fine_h: float
) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0 or coarse_h <= fine_h:
        return math.nan
    return math.log(coarse_error / fine_error) / math.log(coarse_h / fine_h)


def _generalized_order(
    coarse_difference: float,
    fine_difference: float,
    coarse_h: float,
    middle_h: float,
    fine_h: float,
) -> float:
    if (
        coarse_difference <= 0.0
        or fine_difference <= 0.0
        or not coarse_h > middle_h > fine_h > 0.0
    ):
        return math.nan
    target = coarse_difference / fine_difference

    def ratio(order: float) -> float:
        if abs(order) < 1.0e-10:
            return math.log(coarse_h / middle_h) / math.log(middle_h / fine_h)
        return (coarse_h**order - middle_h**order) / (
            middle_h**order - fine_h**order
        )

    def residual(order: float) -> float:
        current = ratio(order)
        if not math.isfinite(current) or current <= 0.0:
            return math.nan
        return math.log(current / target)

    left = 0.0
    left_residual = residual(left)
    for index in range(1, 4097):
        right = 16.0 * index / 4096.0
        right_residual = residual(right)
        if (
            math.isfinite(left_residual)
            and math.isfinite(right_residual)
            and (
                left_residual == 0.0
                or right_residual == 0.0
                or math.copysign(1.0, left_residual)
                != math.copysign(1.0, right_residual)
            )
        ):
            bracket_left = left
            bracket_right = right
            for _ in range(100):
                middle = 0.5 * (bracket_left + bracket_right)
                middle_residual = residual(middle)
                if not math.isfinite(middle_residual):
                    break
                if (
                    middle_residual == 0.0
                    or abs(bracket_right - bracket_left) <= 1.0e-12
                ):
                    return middle
                bracket_left_residual = residual(bracket_left)
                if math.copysign(1.0, bracket_left_residual) != math.copysign(
                    1.0, middle_residual
                ):
                    bracket_right = middle
                else:
                    bracket_left = middle
            return 0.5 * (bracket_left + bracket_right)
        left = right
        left_residual = right_residual
    return math.nan


def _record(
    decisions: list[DecisionRecord],
    role: str,
    scope: str,
    criterion: str,
    operator: str,
    threshold: str,
    observed: Any,
    passed: bool,
    provenance: tuple[str, ...],
    notes: str = "",
) -> None:
    decisions.append(
        DecisionRecord(
            role,
            scope,
            criterion,
            operator,
            threshold,
            observed,
            bool(passed),
            provenance,
            notes,
        )
    )


def _validate_v05_keys(data: dict[str, list[dict[str, str]]]) -> None:
    levels_path = V05_PREFIX + "family_c_levels.csv"
    levels = data[levels_path]
    if [row["source_level"] for row in levels] != ["1", "2", "3", "4"] or any(
        row["family"] != "C" for row in levels
    ):
        _fail_integrity("v05 Family C level keys changed")
    criteria_path = V05_PREFIX + "criteria.csv"
    criteria = _unique_map(data[criteria_path], ("family", "criterion"), criteria_path)
    expected_criteria = {
        "h_rms_strictly_decreasing",
        "maximum_radius_deviation",
        "closed_manifold_euler_outward_proxy",
        "minimum_triangle_quality",
        "minimum_face_to_mean_area_ratio",
        "maximum_edge_ratio_level_1",
        "maximum_edge_ratio_level_2",
        "maximum_edge_ratio_level_3",
        "maximum_edge_ratio_level_4",
        "directional_consistency_plateau",
        "maximum_legacy_ratio_error",
        "normal_errors_nonincreasing",
        "minimum_normal_order",
        "finest_normal_error",
        "tangential_errors_nonincreasing",
        "minimum_tangential_order",
        "finest_tangential_error",
        "maximum_normalized_net_force",
        "maximum_symmetry_class_size",
        "minimum_symmetry_class_count",
        "error_energy_finite_nonnegative",
        "valence_5_plus_valence_6_partition_closed",
        "overall",
    }
    if {key[1] for key in criteria} != expected_criteria:
        _fail_integrity("v05 criteria registry changed")
    regions_path = V05_PREFIX + "family_c_error_regions.csv"
    region_keys = _unique_map(
        data[regions_path], ("family", "source_level", "region"), regions_path
    )
    expected_regions = {
        ("C", str(level), region)
        for level in range(1, 5)
        for region in ("valence_5", "valence_6", "valence_5_closed_one_ring")
    }
    if set(region_keys) != expected_regions:
        _fail_integrity("v05 error-region keys changed")
    valence_path = V05_PREFIX + "family_c_valence.csv"
    valence_keys = _unique_map(
        data[valence_path], ("family", "source_level", "valence"), valence_path
    )
    if set(valence_keys) != {
        ("C", str(level), str(valence))
        for level in range(1, 5)
        for valence in (5, 6)
    }:
        _fail_integrity("v05 valence keys changed")
    ring_path = V05_PREFIX + "family_c_valence5_one_ring.csv"
    ring_keys = _unique_map(
        data[ring_path], ("family", "source_level", "region"), ring_path
    )
    if set(ring_keys) != {
        ("C", str(level), "valence_5_closed_one_ring") for level in range(1, 5)
    }:
        _fail_integrity("v05 one-ring keys changed")
    order_path = V05_PREFIX + "family_c_error_energy_orders.csv"
    order_keys = _unique_map(
        data[order_path], ("family", "coarse_source_level", "fine_source_level"), order_path
    )
    if set(order_keys) != {
        ("C", "1", "2"),
        ("C", "2", "3"),
        ("C", "3", "4"),
    }:
        _fail_integrity("v05 error-energy order keys changed")


def _validate_v06_v07_keys(
    data: dict[str, list[dict[str, str]]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    v06_global = [
        row
        for name in (
            "family_c_level_1_steps.csv",
            "family_c_level_2_steps.csv",
            "family_c_level_3_steps.csv",
            "family_c_level_4_steps.csv",
            "family_c_level_4_dt_half_steps.csv",
        )
        for row in data[V06_PREFIX + name]
    ]
    v06_local = data[V06_PREFIX + "local_step_metrics.csv"]
    v06_energy = data[V06_PREFIX + "energy_ledger.csv"]
    _validate_run_matrix(
        v06_global,
        v06_local,
        v06_energy,
        "run",
        {
            ("C", 1, 1.0e-4): 201,
            ("C", 2, 1.0e-4): 201,
            ("C", 3, 1.0e-4): 201,
            ("C", 4, 1.0e-4): 201,
            ("C_dt_half", 4, 5.0e-5): 401,
        },
        "v06",
    )
    qoi_path = V06_PREFIX + "final_qoi_gate.csv"
    if set(_unique_map(data[qoi_path], ("qoi",), qoi_path)) != {
        ("mean_radius_ratio",),
        ("area_ratio",),
        ("volume_ratio",),
        ("energy_ratio",),
    }:
        _fail_integrity("v06 QoI keys changed")
    time_path = V06_PREFIX + "time_pollution.csv"
    if set(_unique_map(data[time_path], ("qoi",), time_path)) != {
        ("mean_radius_ratio",),
        ("area_ratio",),
        ("volume_ratio",),
        ("energy_ratio",),
    }:
        _fail_integrity("v06 time-pollution keys changed")
    raw_path = V06_PREFIX + "raw_global_gate.csv"
    _unique_map(data[raw_path], ("criterion",), raw_path)

    v07_global = data[V07_PREFIX + "global_step_metrics.csv"]
    v07_local = data[V07_PREFIX + "local_step_metrics.csv"]
    v07_energy = data[V07_PREFIX + "energy_ledger.csv"]
    _validate_run_matrix(
        v07_global,
        v07_local,
        v07_energy,
        "family",
        {
            ("C", level, time_step): count
            for level in (1, 4)
            for time_step, count in (
                (4.0e-4, 51),
                (2.0e-4, 101),
                (1.0e-4, 201),
                (5.0e-5, 401),
            )
        },
        "v07",
    )
    structural_path = V07_PREFIX + "structural_identity.csv"
    structural = _unique_map(
        data[structural_path], ("family", "source_level"), structural_path
    )
    if set(structural) != {("C", str(level)) for level in range(1, 5)}:
        _fail_integrity("v07 structural keys changed")
    diagnosis_path = V07_PREFIX + "time_diagnosis.csv"
    diagnosis = _unique_map(
        data[diagnosis_path], ("family", "source_level"), diagnosis_path
    )
    if set(diagnosis) != {("C", "1"), ("C", "4")}:
        _fail_integrity("v07 time-diagnosis keys changed")
    return (
        _recompute_ledger(v06_energy, "run", "v06 energy ledger"),
        _recompute_ledger(v07_energy, "family", "v07 energy ledger"),
    )


def _adjudicate_d1(
    data: dict[str, list[dict[str, str]]], decisions: list[DecisionRecord]
) -> dict[str, Any]:
    levels_path = V05_PREFIX + "family_c_levels.csv"
    levels = data[levels_path]
    h = [_as_float(row, "h_rms", levels_path) for row in levels]
    normal = [_as_float(row, "normal_velocity_relative_l2", levels_path) for row in levels]
    tangent = [_as_float(row, "tangential_velocity_relative_l2", levels_path) for row in levels]
    normal_orders = [
        _observed_order(normal[index], normal[index + 1], h[index], h[index + 1])
        for index in range(3)
    ]
    tangent_orders = [
        _observed_order(tangent[index], tangent[index + 1], h[index], h[index + 1])
        for index in range(3)
    ]
    source = (levels_path,)
    checks = [
        ("h_rms_strictly_decreasing", "equal", "true", h, all(h[index] > h[index + 1] > 0.0 for index in range(3))),
        ("minimum_triangle_quality", ">=", "0.05", min(_as_float(row, "minimum_triangle_quality", levels_path) for row in levels), min(_as_float(row, "minimum_triangle_quality", levels_path) for row in levels) >= 0.05),
        ("minimum_face_to_mean_area_ratio", ">=", "0.01", min(_as_float(row, "minimum_face_to_mean_area_ratio", levels_path) for row in levels), min(_as_float(row, "minimum_face_to_mean_area_ratio", levels_path) for row in levels) >= 0.01),
        ("maximum_edge_ratio", "<=", "2.0", max(_as_float(row, "h_max", levels_path) / _as_float(row, "h_min", levels_path) for row in levels), all(_as_float(row, "h_max", levels_path) / _as_float(row, "h_min", levels_path) <= 2.0 for row in levels)),
        ("maximum_directional_residual", "<=", "1e-7", max(_as_float(row, "directional_residual", levels_path) for row in levels), max(_as_float(row, "directional_residual", levels_path) for row in levels) <= 1.0e-7),
        ("maximum_legacy_excluded_cache_ratio_error", "<=", "1e-6", max(abs(_as_float(row, "legacy_cache_ratio", levels_path) - 0.5) for row in levels), max(abs(_as_float(row, "legacy_cache_ratio", levels_path) - 0.5) for row in levels) <= 1.0e-6),
        ("maximum_normalized_net_force", "<=", "1e-12", max(_as_float(row, "normalized_net_force_residual", levels_path) for row in levels), max(_as_float(row, "normalized_net_force_residual", levels_path) for row in levels) <= 1.0e-12),
        ("normal_errors_nonincreasing", "equal", "true", normal, all(normal[index + 1] <= normal[index] for index in range(3))),
        ("minimum_normal_actual_h_order", ">=", "0.5", normal_orders, all(math.isfinite(value) and value >= 0.5 for value in normal_orders)),
        ("finest_normal_error", "<", "0.02", normal[-1], normal[-1] < 0.02),
        ("tangential_errors_nonincreasing", "equal", "true", tangent, all(tangent[index + 1] <= tangent[index] for index in range(3))),
        ("minimum_tangential_actual_h_order", ">=", "0.5", tangent_orders, all(math.isfinite(value) and value >= 0.5 for value in tangent_orders)),
        ("finest_tangential_error", "<", "0.02", tangent[-1], tangent[-1] < 0.02),
    ]
    for criterion, operator, threshold, observed, passed in checks:
        _record(decisions, "revised_acceptance", "D1_global_L2", criterion, operator, threshold, observed, passed, source)

    symmetry_path = V05_PREFIX + "family_c_symmetry_classes.csv"
    symmetry_rows = data[symmetry_path]
    class_counts: list[int] = []
    maximum_class_sizes: list[int] = []
    for level_index, level_row in enumerate(levels, start=1):
        rows = [row for row in symmetry_rows if row["source_level"] == str(level_index)]
        class_counts.append(len(rows))
        maximum_class_sizes.append(max(_as_int(row, "vertex_count", symmetry_path) for row in rows))
        if sum(_as_int(row, "vertex_count", symmetry_path) for row in rows) != _as_int(level_row, "vertices", levels_path):
            _fail_integrity(f"v05 symmetry classes do not cover source level {level_index}")
    symmetry_passed = all(
        maximum_class_sizes[index] <= 2
        and class_counts[index] >= _as_int(levels[index], "vertices", levels_path) // 2
        for index in range(4)
    )
    _record(
        decisions,
        "revised_acceptance",
        "D1_global_L2",
        "quality_controlled_symmetry_breaking",
        "max_size<=2 and count>=floor(N/2)",
        "true",
        {"class_counts": class_counts, "maximum_class_sizes": maximum_class_sizes},
        symmetry_passed,
        (symmetry_path, V05_PREFIX + "family_c_symmetry_gate.csv"),
    )

    region_path = V05_PREFIX + "family_c_error_regions.csv"
    regions = data[region_path]
    valence_path = V05_PREFIX + "family_c_valence.csv"
    valence_rows = data[valence_path]
    ring_path = V05_PREFIX + "family_c_valence5_one_ring.csv"
    ring_rows = data[ring_path]
    partition_passed = True
    pointwise_v5: list[float] = []
    error_energy_by_level: dict[int, dict[str, float]] = {}
    region_semantic_closure: list[dict[str, Any]] = []
    for level_index, level_row in enumerate(levels, start=1):
        level_regions = {
            row["region"]: row for row in regions if row["source_level"] == str(level_index)
        }
        v5 = level_regions["valence_5"]
        v6 = level_regions["valence_6"]
        v5_energy = _as_float(v5, "normal_error_energy", region_path)
        v6_energy = _as_float(v6, "normal_error_energy", region_path)
        total = v5_energy + v6_energy
        if total <= 0.0:
            _fail_integrity(
                f"non-positive v05 regional error energy at source level {level_index}",
                reason="v05_region_energy_nonpositive",
                path=region_path,
            )
        v5_fraction = _as_float(v5, "fraction_of_total_error_energy", region_path)
        v6_fraction = _as_float(v6, "fraction_of_total_error_energy", region_path)
        if not _close(v5_fraction, v5_energy / total) or not _close(
            v6_fraction, v6_energy / total
        ):
            _fail_integrity(
                f"v05 regional error fractions do not recompute at source level "
                f"{level_index}",
                reason="v05_region_fraction_mismatch",
                path=region_path,
            )
        total_area = _as_float(v5, "control_area", region_path) + _as_float(
            v6, "control_area", region_path
        )
        exact_velocity = abs(
            _as_float(level_row, "exact_normal_velocity", levels_path)
        )
        if total_area <= 0.0 or exact_velocity <= 0.0:
            _fail_integrity(
                f"v05 global L2 reconstruction has a non-positive denominator "
                f"at source level {level_index}",
                reason="v05_global_l2_denominator_nonpositive",
                path=levels_path,
            )
        rebuilt_global_l2 = math.sqrt(total / total_area) / exact_velocity
        reported_global_l2 = _as_float(
            level_row, "normal_velocity_relative_l2", levels_path
        )
        if not _close(rebuilt_global_l2, reported_global_l2):
            _fail_integrity(
                f"v05 global normal L2 does not rebuild from regional energy "
                f"at source level {level_index}",
                reason="v05_global_l2_mismatch",
                path=levels_path,
            )
        region_semantic_closure.append(
            {
                "source_level": level_index,
                "total_error_energy": total,
                "total_control_area": total_area,
                "reported_valence_5_fraction": v5_fraction,
                "recomputed_valence_5_fraction": v5_energy / total,
                "reported_valence_6_fraction": v6_fraction,
                "recomputed_valence_6_fraction": v6_energy / total,
                "reported_global_normal_l2": reported_global_l2,
                "recomputed_global_normal_l2": rebuilt_global_l2,
            }
        )
        fractions = _as_float(v5, "fraction_of_total_error_energy", region_path) + _as_float(v6, "fraction_of_total_error_energy", region_path)
        counts = _as_int(v5, "vertex_count", region_path) + _as_int(v6, "vertex_count", region_path)
        partition_passed = partition_passed and _close(fractions, 1.0) and counts == _as_int(level_row, "vertices", levels_path)
        for row in level_regions.values():
            partition_passed = partition_passed and all(
                _as_float(row, field, region_path) >= 0.0
                for field in (
                    "control_area",
                    "normal_error_energy",
                    "fraction_of_total_error_energy",
                    "area_weighted_relative_rms",
                    "maximum_pointwise_relative_error",
                )
            )
        if total < 0.0:
            partition_passed = False
        ring = next(row for row in ring_rows if row["source_level"] == str(level_index))
        registered_ring = level_regions["valence_5_closed_one_ring"]
        partition_passed = partition_passed and all(
            ring[field] == registered_ring[field] for field in ERROR_REGION_SCHEMA
        )
        error_energy_by_level[level_index] = {
            "total_error_energy_order": total,
            "valence_5_error_energy_order": v5_energy,
            "valence_6_error_energy_order": v6_energy,
            "valence_5_closed_one_ring_error_energy_order": _as_float(
                registered_ring, "normal_error_energy", region_path
            ),
        }
        pointwise_v5.append(_as_float(v5, "maximum_pointwise_relative_error", region_path))
        matching_valence = [row for row in valence_rows if row["source_level"] == str(level_index)]
        partition_passed = partition_passed and sum(_as_int(row, "vertex_count", valence_path) for row in matching_valence) == _as_int(level_row, "vertices", levels_path)
    _record(
        decisions,
        "revised_acceptance",
        "D1_global_L2",
        "valence_error_region_partition_and_one_ring_closure",
        "equal",
        "true",
        partition_passed,
        partition_passed,
        (region_path, valence_path, ring_path, V05_PREFIX + "family_c_error_energy_orders.csv"),
    )
    order_path = V05_PREFIX + "family_c_error_energy_orders.csv"
    order_rows = _unique_map(
        data[order_path],
        ("family", "coarse_source_level", "fine_source_level"),
        order_path,
    )
    recomputed_energy_orders: list[dict[str, float | int]] = []
    for coarse_level in range(1, 4):
        fine_level = coarse_level + 1
        row = order_rows[("C", str(coarse_level), str(fine_level))]
        recomputed_row: dict[str, float | int] = {
            "coarse_source_level": coarse_level,
            "fine_source_level": fine_level,
        }
        for field in (
            "total_error_energy_order",
            "valence_5_error_energy_order",
            "valence_6_error_energy_order",
            "valence_5_closed_one_ring_error_energy_order",
        ):
            expected_order = _observed_order(
                error_energy_by_level[coarse_level][field],
                error_energy_by_level[fine_level][field],
                h[coarse_level - 1],
                h[fine_level - 1],
            )
            recomputed_row[field] = expected_order
            if not math.isfinite(expected_order) or not _close(
                expected_order, _as_float(row, field, order_path)
            ):
                _fail_integrity(
                    f"v05 error-energy order {field} does not recompute for "
                    f"levels {coarse_level}->{fine_level}",
                    reason="v05_error_energy_order_mismatch",
                    path=order_path,
                )
        recomputed_energy_orders.append(recomputed_row)
    _record(
        decisions,
        "evidence_integrity",
        "D1_global_L2",
        "v05_region_fraction_and_global_l2_semantic_closure",
        "recomputed",
        "1e-12 relative/absolute tolerance",
        region_semantic_closure,
        True,
        (region_path, levels_path),
    )
    _record(
        decisions,
        "evidence_integrity",
        "D1_global_L2",
        "v05_error_energy_orders_semantic_closure",
        "recomputed with actual h",
        "1e-12 relative/absolute tolerance",
        recomputed_energy_orders,
        True,
        (region_path, order_path, levels_path),
    )
    pointwise_trend = (
        "improved"
        if pointwise_v5[-1] < pointwise_v5[0]
        else "not_improved"
    )
    _record(
        decisions,
        "limitation",
        "D1_extraordinary_vertices",
        "valence_5_pointwise_sequence_reported",
        "report_only",
        "claim_allowed=false",
        pointwise_v5,
        True,
        (region_path,),
        f"observed_trend={pointwise_trend}; global L2 convergence does not "
        "authorize pointwise or uniform convergence claims",
    )
    return {
        "h_rms": h,
        "normal_errors": normal,
        "normal_orders": normal_orders,
        "tangential_errors": tangent,
        "tangential_orders": tangent_orders,
        "valence_5_pointwise_maxima": pointwise_v5,
        "region_semantic_closure": region_semantic_closure,
        "recomputed_error_energy_orders": recomputed_energy_orders,
        "pointwise_convergence_claim_allowed": False,
        "uniform_convergence_claim_allowed": False,
    }


def _trajectory_controls(
    global_rows: list[dict[str, str]],
    local_rows: list[dict[str, str]],
    ledger: dict[str, Any],
    owner: str,
    label: str,
    decisions: list[DecisionRecord],
    provenance: tuple[str, ...],
) -> dict[str, float | bool]:
    global_metrics = {
        "minimum_oriented_alignment": min(_as_float(row, "minimum_oriented_face_alignment", label) for row in global_rows),
        "minimum_triangle_quality": min(_as_float(row, "minimum_triangle_quality", label) for row in global_rows),
        "minimum_face_area_ratio": min(_as_float(row, "minimum_face_area_ratio", label) for row in global_rows),
        "maximum_cache_residual": max(_as_float(row, "maximum_normalized_cache_residual", label) for row in global_rows),
        "maximum_centroid_drift": max(_as_float(row, "normalized_surface_centroid_drift", label) for row in global_rows),
        "maximum_local_excursion": max(max(_as_float(row, "maximum_valence_five_excursion_error", label), _as_float(row, "maximum_closed_one_ring_excursion_error", label)) for row in local_rows),
        "maximum_local_radial_error_over_h": max(max(_as_float(row, "maximum_valence_five_error_over_initial_h", label), _as_float(row, "maximum_closed_one_ring_error_over_initial_h", label)) for row in local_rows),
        "maximum_local_edge_scaling_error": max(_as_float(row, "maximum_closed_one_ring_edge_scaling_error", label) for row in local_rows),
        "minimum_local_quality_ratio": min(_as_float(row, "local_minimum_triangle_quality_ratio", label) for row in local_rows),
        "force_buffers_cleared": all(row["force_buffers_cleared"] == "1" for row in local_rows),
        "maximum_normalized_positive_energy": float(ledger["maximum_normalized_cumulative_positive_residual"]),
    }
    checks = [
        ("minimum_oriented_alignment", ">", "0", global_metrics["minimum_oriented_alignment"], global_metrics["minimum_oriented_alignment"] > 0),
        ("minimum_triangle_quality", ">=", "0.05", global_metrics["minimum_triangle_quality"], global_metrics["minimum_triangle_quality"] >= 0.05),
        ("minimum_face_area_ratio", ">=", "1e-4", global_metrics["minimum_face_area_ratio"], global_metrics["minimum_face_area_ratio"] >= 1.0e-4),
        ("maximum_cache_residual", "<=", "1e-12", global_metrics["maximum_cache_residual"], global_metrics["maximum_cache_residual"] <= 1.0e-12),
        ("maximum_centroid_drift", "<=", "1e-2", global_metrics["maximum_centroid_drift"], global_metrics["maximum_centroid_drift"] <= 1.0e-2),
        ("maximum_surface_tension_only_energy_residual", "<=", "1e-3", global_metrics["maximum_normalized_positive_energy"], global_metrics["maximum_normalized_positive_energy"] <= 1.0e-3),
        ("maximum_local_excursion", "<=", "0.25", global_metrics["maximum_local_excursion"], global_metrics["maximum_local_excursion"] <= 0.25),
        ("maximum_local_radial_error_over_h", "<=", "5e-4", global_metrics["maximum_local_radial_error_over_h"], global_metrics["maximum_local_radial_error_over_h"] <= 5.0e-4),
        ("maximum_local_edge_scaling_error", "<=", "5e-4", global_metrics["maximum_local_edge_scaling_error"], global_metrics["maximum_local_edge_scaling_error"] <= 5.0e-4),
        ("minimum_local_quality_ratio", ">=", "0.90", global_metrics["minimum_local_quality_ratio"], global_metrics["minimum_local_quality_ratio"] >= 0.90),
        ("force_buffers_cleared", "equal", "true", global_metrics["force_buffers_cleared"], bool(global_metrics["force_buffers_cleared"])),
    ]
    for criterion, operator, threshold, observed, passed in checks:
        _record(decisions, "revised_acceptance", owner, criterion, operator, threshold, observed, passed, provenance)
    return global_metrics


def _adjudicate_s1(
    data: dict[str, list[dict[str, str]]],
    decisions: list[DecisionRecord],
    ledgers: dict[str, Any],
) -> dict[str, Any]:
    structural_path = V07_PREFIX + "structural_identity.csv"
    structural_rows = data[structural_path]
    structural_metrics: list[dict[str, float | int | bool]] = []
    for row in structural_rows:
        homogeneity = _as_float(row, "homogeneity_force_contraction", structural_path)
        exact_homogeneity = _as_float(row, "exact_homogeneity_force_contraction", structural_path)
        mean_velocity = _as_float(row, "mean_radial_velocity", structural_path)
        exact_velocity = _as_float(row, "exact_mean_radial_velocity", structural_path)
        r_h = abs(homogeneity - exact_homogeneity) / abs(exact_homogeneity)
        r_v = abs(mean_velocity - exact_velocity) / abs(exact_velocity)
        supporting = (
            abs(_as_float(row, "dual_area_to_surface_area_ratio", structural_path) - 1.0) <= 1.0e-12
            and _as_float(row, "normalized_net_force_residual", structural_path) <= 1.0e-12
            and _as_float(row, "maximum_relative_radius_deviation", structural_path) <= 1.0e-12
            and _as_float(row, "maximum_position_displacement", structural_path) == 0.0
            and row["position_hash_before"] == row["position_hash_after"]
            and row["state_hash_before"] == row["state_hash_after"]
            and _as_float(row, "maximum_force_buffer_norm_after", structural_path) == 0.0
            and row["force_buffers_cleared"] == "1"
        )
        structural_metrics.append(
            {
                "source_level": _as_int(row, "source_level", structural_path),
                "r_H": r_h,
                "r_v": r_v,
                "supporting_controls_passed": supporting,
            }
        )
    _record(decisions, "revised_acceptance", "S1_mean_radius", "maximum_structural_r_H", "<=", "1e-12", max(float(item["r_H"]) for item in structural_metrics), all(float(item["r_H"]) <= 1.0e-12 for item in structural_metrics), (structural_path,))
    _record(decisions, "revised_acceptance", "S1_mean_radius", "maximum_structural_r_v", "<=", "1e-12", max(float(item["r_v"]) for item in structural_metrics), all(float(item["r_v"]) <= 1.0e-12 for item in structural_metrics), (structural_path,))
    _record(decisions, "revised_acceptance", "S1_mean_radius", "structural_readonly_supporting_controls", "equal", "true", all(bool(item["supporting_controls_passed"]) for item in structural_metrics), all(bool(item["supporting_controls_passed"]) for item in structural_metrics), (structural_path,))

    v07_global_path = V07_PREFIX + "global_step_metrics.csv"
    v07_global = data[v07_global_path]
    final_by_run: dict[tuple[int, float], dict[str, str]] = {}
    for row in v07_global:
        key = (
            _as_int(row, "source_level", v07_global_path),
            _as_float(row, "time_step", v07_global_path),
        )
        if key not in final_by_run or _as_int(row, "step", v07_global_path) > _as_int(final_by_run[key], "step", v07_global_path):
            final_by_run[key] = row
    exact_radius_response = math.sqrt(1.0 - 4.0 * 0.02 * 0.02 / 10.0)
    time_metrics: dict[str, Any] = {}
    richardson: dict[int, float] = {}
    for level in (1, 4):
        responses = [
            _as_float(final_by_run[(level, time_step)], "control_area_mean_radius_ratio", v07_global_path)
            for time_step in (4.0e-4, 2.0e-4, 1.0e-4, 5.0e-5)
        ]
        differences = [abs(responses[index] - responses[index + 1]) for index in range(3)]
        orders = [math.log2(differences[index] / differences[index + 1]) for index in range(2)]
        plateau = all(value <= 1.0e-13 for value in differences)
        richardson[level] = 2.0 * responses[3] - responses[2]
        passed = (
            not plateau
            and differences[0] > differences[1] > differences[2]
            and all(0.75 <= value <= 1.25 for value in orders)
            and abs(richardson[level] - exact_radius_response) <= 1.0e-10
        )
        time_metrics[str(level)] = {
            "responses": responses,
            "differences": differences,
            "orders": orders,
            "roundoff_plateau": plateau,
            "richardson_response": richardson[level],
            "richardson_error": abs(richardson[level] - exact_radius_response),
        }
        _record(decisions, "revised_acceptance", "S1_mean_radius", f"level_{level}_time_consistency", "strict D decrease, p in [0.75,1.25], Richardson<=1e-10", "true", time_metrics[str(level)], passed, (v07_global_path, V07_PREFIX + "time_diagnosis.csv"))
    cross_richardson = abs(richardson[1] - richardson[4])
    _record(decisions, "revised_acceptance", "S1_mean_radius", "cross_mesh_richardson_difference", "<=", "1e-10", cross_richardson, cross_richardson <= 1.0e-10, (v07_global_path, V07_PREFIX + "time_diagnosis.csv"))

    qoi_path = V06_PREFIX + "final_qoi_gate.csv"
    qoi_rows = {row["qoi"]: row for row in data[qoi_path]}
    historical_radius = qoi_rows["mean_radius_ratio"]
    historical_errors = [
        _as_float(historical_radius, f"level_{level}_analytic_error", qoi_path)
        for level in range(1, 5)
    ]
    historical_orders = [
        _as_float(historical_radius, name, qoi_path)
        for name in ("analytic_order_1_2", "analytic_order_2_3", "analytic_order_3_4")
    ]
    _record(
        decisions,
        "historical_evidence",
        "v06_mean_radius_spatial",
        "historical_failed_not_rejudged",
        "equal",
        "failed",
        {"errors": historical_errors, "orders": historical_orders},
        False,
        (qoi_path,),
        "excluded from revised S1 acceptance logic",
    )

    v06_global_paths = tuple(
        V06_PREFIX + name
        for name in (
            "family_c_level_1_steps.csv",
            "family_c_level_2_steps.csv",
            "family_c_level_3_steps.csv",
            "family_c_level_4_steps.csv",
            "family_c_level_4_dt_half_steps.csv",
        )
    )
    v06_runs = [data[path] for path in v06_global_paths]
    base_runs = v06_runs[:4]
    h = [_as_float(rows[0], "initial_h_rms", v06_global_paths[index]) for index, rows in enumerate(base_runs)]
    qoi_columns = {
        "area_ratio": "area_ratio",
        "volume_ratio": "volume_ratio",
        "energy_ratio": "registered_energy_ratio",
    }
    spatial_metrics: dict[str, Any] = {}
    for qoi, column in qoi_columns.items():
        reported = qoi_rows[qoi]
        exact = _as_float(reported, "exact_final_value", qoi_path)
        initial = [_as_float(rows[0], column, v06_global_paths[index]) for index, rows in enumerate(base_runs)]
        responses = [_as_float(rows[-1], column, v06_global_paths[index]) for index, rows in enumerate(base_runs)]
        excursions = [max(abs(exact - value), 1.0e-12) for value in initial]
        errors = [abs(responses[index] - exact) / excursions[index] for index in range(4)]
        orders = [_observed_order(errors[index], errors[index + 1], h[index], h[index + 1]) for index in range(3)]
        differences = [abs(responses[index] - responses[index + 1]) / excursions[index] for index in range(3)]
        generalized = [_generalized_order(differences[index], differences[index + 1], h[index], h[index + 1], h[index + 2]) for index in range(2)]
        passed = (
            all(errors[index + 1] <= errors[index] for index in range(3))
            and all(math.isfinite(value) and value >= 0.5 for value in orders)
            and errors[-1] < 0.02
            and all(differences[index + 1] <= differences[index] for index in range(2))
            and all(math.isfinite(value) and value >= 0.5 for value in generalized)
        )
        spatial_metrics[qoi] = {
            "exact": exact,
            "responses": responses,
            "errors": errors,
            "orders": orders,
            "adjacent_differences": differences,
            "generalized_orders": generalized,
        }
        _record(decisions, "revised_acceptance", f"S1_{qoi}", "analytic_and_self_spatial_convergence", "monotonic, actual-h orders>=0.5, finest<0.02", "true", spatial_metrics[qoi], passed, (qoi_path, *v06_global_paths[:4]))

    time_path = V06_PREFIX + "time_pollution.csv"
    time_rows = {row["qoi"]: row for row in data[time_path]}
    time_metrics_v06: dict[str, Any] = {}
    for qoi, column in qoi_columns.items():
        dt_response = _as_float(v06_runs[3][-1], column, v06_global_paths[3])
        half_response = _as_float(v06_runs[4][-1], column, v06_global_paths[4])
        exact = spatial_metrics[qoi]["exact"]
        delta = abs(dt_response - half_response)
        proxy = abs(half_response - exact)
        plateau = delta <= 1.0e-10 and proxy <= 1.0e-10
        passed = plateau or delta <= 0.25 * proxy
        time_metrics_v06[qoi] = {
            "delta_time": delta,
            "space_proxy": proxy,
            "roundoff_plateau": plateau,
        }
        reported = time_rows[qoi]
        if not _close(delta, _as_float(reported, "absolute_time_difference", time_path)) or not _close(proxy, _as_float(reported, "absolute_space_proxy", time_path)):
            _fail_integrity(f"v06 reported time pollution does not match raw steps for {qoi}")
        _record(decisions, "revised_acceptance", f"S1_{qoi}", "finest_time_pollution", "raw plateau or delta<=0.25*proxy", "true", time_metrics_v06[qoi], passed, (time_path, v06_global_paths[3], v06_global_paths[4]))

    v06_global = [row for rows in v06_runs for row in rows]
    v06_controls = _trajectory_controls(
        v06_global,
        data[V06_PREFIX + "local_step_metrics.csv"],
        ledgers["v06"],
        "S1_v06_step_controls",
        "v06 controls",
        decisions,
        (*v06_global_paths, V06_PREFIX + "local_step_metrics.csv", V06_PREFIX + "energy_ledger.csv"),
    )
    v07_controls = _trajectory_controls(
        data[v07_global_path],
        data[V07_PREFIX + "local_step_metrics.csv"],
        ledgers["v07"],
        "S1_v07_step_controls",
        "v07 controls",
        decisions,
        (v07_global_path, V07_PREFIX + "local_step_metrics.csv", V07_PREFIX + "energy_ledger.csv"),
    )
    return {
        "structural": structural_metrics,
        "mean_radius_time": time_metrics,
        "mean_radius_cross_mesh_richardson_difference": cross_richardson,
        "v06_historical_mean_radius_errors": historical_errors,
        "v06_historical_mean_radius_orders": historical_orders,
        "v06_spatial_qois": spatial_metrics,
        "v06_time_pollution": time_metrics_v06,
        "v06_step_controls": v06_controls,
        "v07_step_controls": v07_controls,
        "energy_coverage": {
            "coverage": "surface_tension_only",
            "registered": ["gamma*A", "D_zeta"],
            "excluded": [
                "legacy_0.5_gamma_A_cache",
                "membrane_elasticity",
                "bending",
                "pressure",
                "contact",
                "active",
                "ECM",
                "flow",
            ],
        },
    }


def _result(
    status: str,
    provenance: tuple[ProvenanceRecord, ...],
    decisions: list[DecisionRecord],
    metrics: dict[str, Any],
    ledgers: dict[str, Any],
    d1_passed: bool,
    s1_passed: bool,
) -> AdjudicationDecision:
    return AdjudicationDecision(
        status=status,
        evidence_integrity_passed=True,
        revised_d1_passed=d1_passed,
        revised_s1_passed=s1_passed,
        provenance=provenance,
        decisions=tuple(decisions),
        metrics=metrics,
        ledger_recomputations=ledgers,
        historical_statuses=dict(HISTORICAL_STATUSES),
        x1_k_passed=False,
        r1_c1_f1_status="not_executed",
        downstream_authorized=False,
        pointwise_convergence_claim_allowed=False,
        uniform_convergence_claim_allowed=False,
    )


def adjudicate_fixed_topology_evidence(
    workspace_root: Path,
    *,
    evidence_specs: tuple[EvidenceSpec, ...] = EVIDENCE_SPECS,
) -> AdjudicationDecision:
    """Recompute the bounded v08 decision directly from frozen raw CSV evidence."""
    data, provenance = _load_evidence(workspace_root, evidence_specs)
    _validate_v05_keys(data)
    v06_ledger, v07_ledger = _validate_v06_v07_keys(data)
    ledgers = {"v06": v06_ledger, "v07": v07_ledger}
    decisions: list[DecisionRecord] = []
    metrics: dict[str, Any] = {}

    for scope in ("route_h_gate_a_v01", "v02_d1", "v04_family_b"):
        _record(
            decisions,
            "historical_evidence",
            scope,
            "preserved_failure_status",
            "equal",
            "unchanged historical failure",
            HISTORICAL_STATUSES[scope],
            False,
            (),
            "status is preserved by the v08 contract and excluded from revised acceptance logic",
        )

    metrics["revised_d1"] = _adjudicate_d1(data, decisions)
    d1_records = [
        record
        for record in decisions
        if record.role == "revised_acceptance" and record.scope.startswith("D1")
    ]
    if not all(record.passed for record in d1_records):
        first = next(record for record in d1_records if not record.passed)
        return _result(
            f"failed_revised_d1_{first.criterion}",
            provenance,
            decisions,
            metrics,
            ledgers,
            False,
            False,
        )

    metrics["revised_s1"] = _adjudicate_s1(data, decisions, ledgers)
    s1_records = [
        record
        for record in decisions
        if record.role == "revised_acceptance" and record.scope.startswith("S1")
    ]
    if not all(record.passed for record in s1_records):
        first = next(record for record in s1_records if not record.passed)
        return _result(
            f"failed_revised_s1_{first.criterion}",
            provenance,
            decisions,
            metrics,
            ledgers,
            True,
            False,
        )
    return _result(
        "passed_revised_fixed_topology_d1_s1_acceptance",
        provenance,
        decisions,
        metrics,
        ledgers,
        True,
        True,
    )


def adjudicate_fixed_topology_evidence_after_repair(
    workspace_root: Path,
    *,
    evidence_specs: tuple[EvidenceSpec, ...] = EVIDENCE_SPECS,
) -> AdjudicationDecision:
    """Run the repaired v08r1 contract while preserving the rejected v08 state."""
    decision = adjudicate_fixed_topology_evidence(
        workspace_root,
        evidence_specs=evidence_specs,
    )
    historical_statuses = {
        **decision.historical_statuses,
        "v08": "failed_adjudicator_contract_incomplete",
    }
    status = decision.status
    if status == "passed_revised_fixed_topology_d1_s1_acceptance":
        status = (
            "passed_revised_fixed_topology_d1_s1_acceptance_"
            "after_adjudicator_repair"
        )
    return replace(
        decision,
        status=status,
        historical_statuses=historical_statuses,
    )
