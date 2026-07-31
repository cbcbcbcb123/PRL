"""Create the Stage 0 v06 spatial-discretization contract artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CREATED_AT = "2026-07-31T09:35:21+08:00"
CONTRACT_ID = "CONTRACT-PRL-ROUTE-H-STAGE0-V06"
SPECIALIZATION_ID = "SPECIALIZATION-PRL-ROUTE-H-STAGE0-V06"
GEOMETRY_ID = "GEOMETRY-FAMILY-PRL-ROUTE-H-STAGE0-V06"
CASES_ID = "CASES-PRL-ROUTE-H-STAGE0-V06"
FAMILY_ID = "DISCRETIZATION-FAMILY-PRL-ROUTE-H-STAGE0-V06"


def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_json(relative: str, value: dict[str, Any]) -> None:
    (ROOT / relative).write_bytes(
        (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    )


def write_text(relative: str, value: str) -> None:
    (ROOT / relative).write_bytes(value.replace("\r\n", "\n").encode())


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()


def create_geometry_spec() -> dict[str, Any]:
    family_manifest = read_json(
        "data/route_h/stage0_v06_discretization_family/manifest.json"
    )
    level_specs = []
    expected = {
        "coarse": (42, 80, 105, 288),
        "base": (162, 320, 351, 1152),
        "fine": (642, 1280, 2125, 9216),
    }
    for record in family_manifest["levels"]:
        counts = expected[record["name"]]
        level_specs.append(
            {
                **record,
                "expected_cell_count": 15,
                "expected_vertices_per_cell": counts[0],
                "expected_faces_per_cell": counts[1],
                "expected_ECM_vertices": counts[2],
                "expected_ECM_tetrahedra": counts[3],
            }
        )
    geometry = {
        "geometry_spec_id": GEOMETRY_ID,
        "schema_version": "6.0.0",
        "created_at": CREATED_AT,
        "status": "approved_materialized_candidate_pending_freeze",
        "evidence_level": (
            "deterministic_dimensionless_spatial_discretization_family_no_solver_response"
        ),
        "supersedes_for_future_work": (
            "GEOMETRY-PRL-ROUTE-H-STAGE0-V05 base-only topology"
        ),
        "authority": {
            "decision": (
                "project_control/"
                "route_h_stage0_v06_discretization_authorization_decision_v01.md"
            ),
            "decision_sha256": sha256(
                "project_control/"
                "route_h_stage0_v06_discretization_authorization_decision_v01.md"
            ),
            "preflight": (
                "project_control/"
                "route_h_stage2_preflight_discretization_block_v01.md"
            ),
            "preflight_sha256": sha256(
                "project_control/"
                "route_h_stage2_preflight_discretization_block_v01.md"
            ),
        },
        "inherited_reference": {
            "base_geometry_spec": (
                "data/route_h/route_h_reference_geometry_spec_v05.json"
            ),
            "base_geometry_spec_sha256": sha256(
                "data/route_h/route_h_reference_geometry_spec_v05.json"
            ),
            "base_reference_bundle": (
                "data/route_h/stage1_reference_bundle_v01/manifest.json"
            ),
            "base_reference_bundle_sha256": (
                family_manifest["base_reuse"]["source_bundle_sha256"]
            ),
            "all_22_base_arrays_byte_exact": (
                family_manifest["base_reuse"]["all_22_arrays_byte_exact"]
            ),
        },
        "family_manifest": {
            "path": (
                "data/route_h/stage0_v06_discretization_family/manifest.json"
            ),
            "sha256": sha256(
                "data/route_h/stage0_v06_discretization_family/manifest.json"
            ),
            "family_sha256": family_manifest["family_sha256"],
        },
        "levels": level_specs,
        "generator_contract": {
            "cell_surface": (
                "Use the v05 ordered icosahedron, binary64 normalization, child-face "
                "order, superellipsoid map and 8*eps z-x-y face-identity tie rule; "
                "subdivision levels are 1, 2 and 3."
            ),
            "ECM": (
                "Use v05 bounds [0,3]x[0,1.8]x[0,0.2], structured vertex/brick IDs "
                "and six-tetra pattern with intervals 6x4x2, 12x8x2 and 24x16x4."
            ),
            "base_rule": (
                "The base level uses the scalar v05 ray search and every serialized "
                "array must be byte-identical to the frozen Stage 1 v01 bundle."
            ),
            "coarse_fine_ray_rule": (
                "The same nearest-distance then smallest-face-ID rule is evaluated "
                "with deterministic vectorized binary64 arithmetic; replay must be "
                "byte exact."
            ),
            "coarse_fine_reference_plane_snap": (
                "Before identity and tether generation, analytic cell-coordinate "
                "extrema within 8*eps of a rounded 15-decimal reference plane are "
                "snapped to that plane. This removes one-ULP false transverse "
                "crossings; it is disabled at base so all v05 arrays remain byte exact."
            ),
            "canonical_serialization": (
                "signed little-endian int64 or IEEE-754 binary64 C-order; negative "
                "zero canonicalized; UTF-8 sorted canonical JSON; SHA-256."
            ),
        },
        "material_tether_discretization_admission": {
            "cell_ECM_maximum_reference_natural_gap": 0.075,
            "cell_cell_maximum_reference_natural_gap": 0.15,
            "reason": (
                "The coarse planar face barycenter has a registered maximum cell-ECM "
                "natural gap of 0.06348416662201481. The v06 family therefore seals a "
                "0.075 geometry-admission ceiling before any response is run."
            ),
            "mechanical_effect": False,
            "stored_pair_rule": (
                "Every exact g0_pair remains serialized per tether and delta_g=g-g0_pair; "
                "the admission ceiling is never read by energy, force or solver code."
            ),
            "adhesion_or_steric_potential_change": False,
        },
        "seal_gates": [
            "all three levels contain exactly 22 canonical arrays",
            "base arrays byte-match the v05 frozen bundle",
            "cell surfaces are oriented watertight 2-manifolds with quality >=0.30",
            "all cell signed volumes and ECM tetra determinants are positive",
            "ECM has at least two tetrahedral layers through thickness",
            "material-tether and myocardial-source-map coverage are exact",
            "boundary owner and gauge arrays are complete and positive where required",
            "passive reference energy and force thresholds pass at every level",
            "reference material forces and moments pass at every level",
            "closed-surface steric energy is zero and proper intersections are absent",
            "a fresh generator replay reproduces every serialized array byte exactly",
            "fine myocardial/ECM analytic tangencies contain no proper intersections",
        ],
        "spatial_response_protocol": {
            "execution_stage": "Stage 2 after this family is frozen and inspected",
            "registered_cases": ["E0_ZERO", "E4_COMBINED"],
            "levels": ["coarse", "base", "fine"],
            "comparison": "base versus fine; coarse is retained as a trend diagnostic",
            "relative_metric": (
                "|q_base-q_fine|/max(1e-8,|q_base|,|q_fine|)"
            ),
            "relative_threshold": 0.03,
            "exact_zero_policy": (
                "Use the pre-existing absolute tolerance for registered exact-zero "
                "metrics; never convert a near-zero quantity to a relative pass."
            ),
            "observables": [
                "peak myocardial axial shortening",
                "peak positive transverse scale change",
                "maximum relative cell-volume error",
                "minimum ECM J",
                "maximum physical penetration",
                "peak ECM tangential traction",
                "peak pressure and WSS resultants when enabled",
                "integrated active work",
                "integrated pressure work",
                "integrated WSS work",
                "total dissipation",
                "integrated normalized power residual",
            ],
        },
        "explicit_exclusions": [
            "periodic geometry or periodic image contact",
            "new cell count or patch bounds",
            "mechanical parameter sweep or response-dependent threshold adjustment",
            "turnover, nonzero j_myo, physiological calibration or claim-bearing output",
        ],
    }
    write_json(
        "data/route_h/route_h_spatial_discretization_family_v06.json",
        geometry,
    )
    return geometry


def create_contract(geometry: dict[str, Any]) -> None:
    contract = read_json("src/route_h/route_h_contract_v05.json")
    contract["contract_id"] = CONTRACT_ID
    contract["schema_version"] = "6.0.0"
    contract["created_at"] = CREATED_AT
    contract["status"] = "approved_v06_candidate_pending_freeze"
    contract["lifecycle_state"] = "stage0_v06_discretization_materialized"
    contract["evidence_level"] = (
        "preregistered_dimensionless_mechanistic_contract_with_sealed_spatial_family_no_response"
    )
    contract["authority"] = {
        "user_instruction": "批准 v06 方案，继续",
        "decision": (
            "DEC-PRL-ROUTE-H-STAGE0-V06-DISCRETIZATION-V01"
        ),
        "authorized": [
            "Materialize, verify, freeze and inspect the v06 coarse/base/fine family",
            "Close the pre-Stage-2 discretization block after a passing v06 inspection",
            "Execute Stage 2 Gate A-E in strict order under its separate authorization",
        ],
        "not_authorized": [
            "Modify v01-v05 frozen files or the Stage 1 v02 evidence",
            "Change equations, mechanical parameters, contact potentials or load ledger",
            "Add periodic geometry, turnover, nonzero j_myo or a parameter sweep",
            "Publish a physiological or claim-bearing result",
        ],
    }
    contract["version_policy"] = {
        "supersedes_for_future_work": "CONTRACT-PRL-ROUTE-H-STAGE0-V05",
        "v01_through_v05_are_immutable_historical_records": True,
        "prior_pass_or_result_inheritance": False,
        "inherited_base_arrays_must_be_byte_exact": True,
        "stage2_solver_target": CONTRACT_ID,
    }
    contract["direct_inputs"] = [
        {
            "path": "src/route_h/route_h_contract_v05.json",
            "sha256": sha256("src/route_h/route_h_contract_v05.json"),
            "role": "immutable scientific mechanism and base contract",
        },
        {
            "path": (
                "project_control/"
                "route_h_stage2_preflight_discretization_block_v01.md"
            ),
            "sha256": sha256(
                "project_control/"
                "route_h_stage2_preflight_discretization_block_v01.md"
            ),
            "role": "registered PreStage2 block and approved repair scope",
        },
        {
            "path": (
                "project_control/"
                "route_h_stage0_v06_discretization_authorization_decision_v01.md"
            ),
            "sha256": sha256(
                "project_control/"
                "route_h_stage0_v06_discretization_authorization_decision_v01.md"
            ),
            "role": "user authorization for v06 and continued Stage 2 execution",
        },
        {
            "path": (
                "data/route_h/"
                "route_h_spatial_discretization_family_v06.json"
            ),
            "sha256": sha256(
                "data/route_h/"
                "route_h_spatial_discretization_family_v06.json"
            ),
            "role": "identity-bearing coarse/base/fine geometry family",
        },
    ]
    contract["reference_geometry_and_state"]["geometry_spec"] = (
        "data/route_h/route_h_spatial_discretization_family_v06.json"
    )
    contract["reference_geometry_and_state"]["geometry_spec_sha256"] = (
        sha256("data/route_h/route_h_spatial_discretization_family_v06.json")
    )
    contract["reference_geometry_and_state"]["materialization_authorized"] = True
    contract["reference_geometry_and_state"]["discretization_family"] = FAMILY_ID
    contract["topology_and_material_identity"]["ECM_representation"] = (
        "independent structured six-tetra-per-brick volume mesh at the sealed "
        "coarse/base/fine intervals"
    )
    contract["verification_metric_definitions"][
        "spatial_refinement_relative_difference"
    ] = "|q_base-q_fine|/max(1e-8,|q_base|,|q_fine|)"
    contract["spatial_refinement_observables"] = geometry[
        "spatial_response_protocol"
    ]["observables"]
    contract["spatial_refinement_policy"] = {
        "registered_in_v06": True,
        "family_id": FAMILY_ID,
        "levels": ["coarse", "base", "fine"],
        "registered_cases": ["E0_ZERO", "E4_COMBINED"],
        "last_two_level_relative_difference_max": 0.03,
        "exact_zero_policy": (
            "Use the already registered absolute tolerance for exact-zero metrics."
        ),
        "required_before_stage2": True,
        "prestage2_requirement_satisfied_only_after_v06_freeze_and_inspection": True,
    }
    contract["review_finding_resolutions"]["V06-DISCRETIZATION-001"] = (
        "The separately approved coarse/base/fine identity-bearing family exists; "
        "base is byte-exact to v05 and response observables are preregistered."
    )
    contract["review_finding_resolutions"]["V06-FLOAT-INTERFACE-SNAP-001"] = (
        "A one-ULP fine myocardial vertex below the analytic ECM plane produced six "
        "false transverse pair flags. Coarse/fine analytic extrema now use the frozen "
        "8*eps reference-plane snap; base remains byte exact and all mechanics are unchanged."
    )
    contract["completion_gate"] = {
        "stage0_v06_contract_candidate": True,
        "spatial_family_materialized": True,
        "stage2_authorized_by_separate_decision": True,
        "stage2_scientific_runs_before_v06_freeze": 0,
        "next_required_action": (
            "v06 verification, freeze and read-only inspection; then Stage 2 Gate A"
        ),
    }
    write_json("src/route_h/route_h_contract_v06.json", contract)


def create_specialization() -> None:
    specialization = read_json(
        "src/route_h/route_h_model_specialization_v05.json"
    )
    specialization["specialization_id"] = SPECIALIZATION_ID
    specialization["schema_version"] = "6.0.0"
    specialization["created_at"] = CREATED_AT
    specialization["status"] = "approved_v06_candidate_pending_freeze"
    specialization["contract_id"] = CONTRACT_ID
    specialization["geometry_spec_id"] = GEOMETRY_ID
    specialization["supersedes"] = (
        "SPECIALIZATION-PRL-ROUTE-H-STAGE0-V05"
    )
    numerical = specialization["numerical_preregistration"]
    numerical["space_refinement_registered"] = True
    numerical["spatial_discretization_family"] = {
        "family_id": FAMILY_ID,
        "cell_surface_subdivision_levels": [1, 2, 3],
        "ECM_intervals": [[6, 4, 2], [12, 8, 2], [24, 16, 4]],
        "registered_cases": ["E0_ZERO", "E4_COMBINED"],
    }
    specialization["acceptance_thresholds"][
        "space_refinement_relative_difference_max"
    ] = 0.03
    specialization["deferred_before_stage2"] = [
        item
        for item in specialization.get("deferred_before_stage2", [])
        if item != "coarse/base/fine spatial discretization family"
    ]
    specialization["stage2_authorized"] = True
    write_json(
        "src/route_h/route_h_model_specialization_v06.json",
        specialization,
    )


def create_cases() -> None:
    cases = read_json("data/route_h/route_h_cases_v05.json")
    cases["registry_id"] = CASES_ID
    cases["schema_version"] = "6.0.0"
    cases["contract_id"] = CONTRACT_ID
    cases["specialization_id"] = SPECIALIZATION_ID
    cases["geometry_spec_id"] = GEOMETRY_ID
    cases["created_at"] = CREATED_AT
    cases["status"] = "approved_v06_candidate_pending_freeze"
    cases["supersedes"] = "CASES-PRL-ROUTE-H-STAGE0-V05"
    rules = cases["global_rules"]
    rules["space_refinement_registered"] = True
    rules["space_refinement_required_before_stage2"] = True
    rules["space_refinement_family_id"] = FAMILY_ID
    rules["stage2_authorized"] = True
    rules["prestage2_discretization_block_closes_only_after_v06_inspection"] = True
    cases["spatial_refinement_registry"] = {
        "family_id": FAMILY_ID,
        "levels": ["coarse", "base", "fine"],
        "registered_case_ids": ["E0_ZERO", "E4_COMBINED"],
        "comparison": "base versus fine; coarse retained as a trend diagnostic",
        "relative_difference_max": 0.03,
        "exact_zero_metrics_use_absolute_thresholds": True,
        "parameter_or_threshold_change_after_response": False,
    }
    for case in cases["cases"]:
        case["initial_status"] = "not_run_stage2_preexecution"
        if case["case_id"] in {"E0_ZERO", "E4_COMBINED"}:
            case["spatial_refinement"] = ["coarse", "base", "fine"]
    for gate in cases["gates"]:
        if gate["gate_id"] == "E":
            gate["claim_guard"] = (
                "Passing the sealed base/fine response comparison is mechanistic "
                "verification only and is not physiological validation."
            )
    write_json("data/route_h/route_h_cases_v06.json", cases)


def create_registry() -> None:
    source = ROOT / "tests/route_h/route_h_verification_registry_v05.csv"
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        if row["test_id"] == "AUTH-STAGE1-LOCK":
            row.update(
                {
                    "test_id": "AUTH-STAGE2-GATE",
                    "requirement": (
                        "Stage 2 execution is authorized only after Stage 1 acceptance "
                        "and the separately approved v06 discretization seal"
                    ),
                    "case_ids": "all",
                    "frozen_status": "verified_static_at_v06_freeze",
                    "failure_action": "block Stage 2",
                    "review_mapping": "S2-PREFLIGHT-DISCRETIZATION-001",
                }
            )
        elif row["test_id"] == "SPACE-REFINEMENT-DEFERRED":
            row.update(
                {
                    "test_id": "SPACE-FAMILY-SPEC",
                    "requirement": (
                        "The v06 coarse/base/fine family levels identities hashes "
                        "cross-mesh observables and 3 percent threshold are explicit"
                    ),
                    "frozen_status": "verified_static_at_v06_freeze",
                    "failure_action": "do not freeze v06",
                    "review_mapping": "V06-DISCRETIZATION-001",
                }
            )
        elif row["test_id"] == "STAGE2-DISCRETIZATION-BLOCK":
            row.update(
                {
                    "test_id": "STAGE2-DISCRETIZATION-SEAL",
                    "stage": "0",
                    "requirement": (
                        "No Stage 2 scientific execution occurred before the separately "
                        "approved coarse/base/fine family was materialized and sealed"
                    ),
                    "frozen_status": "verified_static_at_v06_freeze",
                    "failure_action": "block Stage 2",
                    "review_mapping": "S2-PREFLIGHT-DISCRETIZATION-001",
                }
            )
        elif row["frozen_status"] == "registered_not_run_unauthorized":
            row["frozen_status"] = "registered_not_run_stage2_preexecution"
    additions = [
        {
            "test_id": "SPACE-LEVEL-COUNTS",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Cell and ECM counts exactly match the approved coarse/base/fine table"
            ),
            "metric": "count mismatches",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-BASE-BYTE-REUSE",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "All 22 base arrays are byte-identical to the v05 Stage 1 bundle"
            ),
            "metric": "unequal arrays",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-GEOMETRY-VALIDITY",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Every level is watertight oriented quality-controlled and has "
                "positive ECM tetra determinants with at least two thickness layers"
            ),
            "metric": "invalid levels",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-MAP-COVERAGE",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Every level has exact tether source-map owner anchor and gauge coverage"
            ),
            "metric": "coverage errors",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-DETERMINISTIC-REPLAY",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Fresh generation reproduces all 22 arrays at every level byte exactly"
            ),
            "metric": "unequal arrays",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-REFERENCE-SEAL",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Every level has passive reference force moment and steric zero with "
                "no proper intersections"
            ),
            "metric": "failed levels",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
        {
            "test_id": "SPACE-FLOAT-INTERFACE-SNAP",
            "stage": "0",
            "gate": "PreStage2",
            "requirement": (
                "Coarse/fine analytic cell extrema are snapped within 8*eps so "
                "myocardial-ECM tangencies have zero proper intersections while base "
                "arrays remain byte exact"
            ),
            "metric": "proper intersection or base-array changes",
            "threshold": "0",
            "units": "count",
            "case_ids": "all",
            "frozen_status": "registered_v06_materialization",
            "failure_action": "do not freeze v06",
            "review_mapping": "V06-FLOAT-INTERFACE-SNAP-001",
        },
        {
            "test_id": "SPACE-REFINEMENT",
            "stage": "2",
            "gate": "E",
            "requirement": (
                "All frozen nonzero observables agree between base and fine while "
                "exact-zero metrics meet their absolute thresholds"
            ),
            "metric": "maximum relative difference",
            "threshold": "0.03",
            "units": "dimensionless",
            "case_ids": "E0_ZERO;E4_COMBINED",
            "frozen_status": "registered_not_run_stage2_preexecution",
            "failure_action": "fail Gate E",
            "review_mapping": "V06-DISCRETIZATION-001",
        },
    ]
    rows.extend(additions)
    target = ROOT / "tests/route_h/route_h_verification_registry_v06.csv"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_protocol_document() -> None:
    text = """# Route H Stage 0 v06 空间离散验证协议

## 目的

本协议只关闭 v05 的 `STAGE2-DISCRETIZATION-BLOCK`。它不运行主动响应、不改变模型方程，
也不把无量纲验证解释成生理标定。

## 冻结离散族

| level | cell subdivision | 每细胞 vertices/faces | ECM intervals |
|---|---:|---:|---:|
| coarse | 1 | 42 / 80 | 6 / 4 / 2 |
| base | 2 | 162 / 320 | 12 / 8 / 2 |
| fine | 3 | 642 / 1280 | 24 / 16 / 4 |

base 的 22 个二进制数组必须与 Stage 1 v01 reference bundle 逐字节一致。coarse/fine 使用
与 v05 相同的 patch bounds、实体数、拓扑生成顺序、材料身份、作用—反作用 owner 与
canonical serialization。

## coarse 几何 admission erratum

coarse 平面三角形的界面 barycenter 比 base/fine 更远离真实 superellipsoid 界面；
预响应 materialization 显示 cell–ECM 最大自然间隙为
`0.06348416662201481`，超过 v05 为单一 base topology 设置的 `0.05`。

v06 因而在任何求解前冻结 `0.075` 作为三层共同的 cell–ECM **geometry admission
ceiling**。该量只决定 reference tether 是否允许写入 bundle：

- 它不进入 adhesion、steric、support、ECM 或 cell energy；
- 它不进入力、功率账本或求解器；
- 每对 tether 仍使用自身封存的 `g0_pair` 和 `delta_g=g-g0_pair`；
- cell–cell admission ceiling 保持 `0.15`；
- 接触/黏附势、无量纲机械参数和所有 Stage 2 载荷均不变。

## fine reference-plane binary64 erratum

首次 fine seal audit 发现 6 个 myocardial–ECM entity pairs 被标记为 proper
intersection。逐三角形检查表明：每个事件都来自解析上应为 `z=0.2` 的 myocardial
极点被 binary64 计算为 `0.19999999999999996`，而相邻 fine 顶点略高于 ECM 平面，
使静态判据把一个 one-ULP 切触误认为横穿。

v06 在 coarse/fine identity 与 tether 生成前加入冻结的 reference-plane snap：
若 cell 坐标极值与按 15 位小数规范化的解析参考平面相差不超过
`8*eps*max(1,|coordinate|)`，则写为该参考平面。base 禁用该修订以保持 v05 的
22 个数组逐字节不变。修订后 fine `min myocardial z=0.2`，proper intersection
计数为 0；它不改变方程、参数、势能或响应。

## PreStage2 封存门

每个 level 必须同时通过：

1. 数量、ID、canonical hash 与 fresh replay；
2. cell watertight/orientation/quality/positive volume；
3. ECM positive tetra 与至少两个厚度单元层；
4. tether、source map、owner、anchor、gauge 完整覆盖；
5. 被动 reference energy/force、材料 pair force/moment；
6. closed-surface steric energy 为零且无 proper intersection；
7. v06 冻结清单无 hash mismatch。

任一失败均保持 Stage 2 科学运行数为零。

## Stage 2 空间响应协议

- 注册 cases：`E0_ZERO` 与 `E4_COMBINED`；
- 三层都运行，coarse 用于趋势诊断，正式阈值比较 base 与 fine；
- 非零关键量采用
  `|q_base-q_fine|/max(1e-8,|q_base|,|q_fine|) <= 0.03`；
- exact-zero 指标继续使用其原有绝对阈值，不能改用相对误差获得通过；
- 参数、阈值、case 或 observable 均不得在看到响应后调整。

## 明确排除

不注册 periodic geometry，不改变 patch bounds 或细胞数，不运行 parameter sweep、
turnover、非零 `j_myo`、生理标定、论文图或外部科学结论。
"""
    write_text(
        "docs/route_h/route_h_spatial_discretization_protocol_v06.md",
        text,
    )


def main() -> None:
    geometry = create_geometry_spec()
    create_contract(geometry)
    create_specialization()
    create_cases()
    create_registry()
    create_protocol_document()
    outputs = [
        "data/route_h/route_h_spatial_discretization_family_v06.json",
        "src/route_h/route_h_contract_v06.json",
        "src/route_h/route_h_model_specialization_v06.json",
        "data/route_h/route_h_cases_v06.json",
        "tests/route_h/route_h_verification_registry_v06.csv",
        "docs/route_h/route_h_spatial_discretization_protocol_v06.md",
    ]
    print(
        json.dumps(
            {
                "outputs": [
                    {
                        "path": path,
                        "sha256": sha256(path),
                    }
                    for path in outputs
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
