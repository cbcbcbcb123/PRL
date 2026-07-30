"""Create the append-only Stage 0 v05 floating-tie erratum package.

This script never edits v04.  It performs only versioned mechanical transforms
plus the single reviewed face-classification clarification.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATED = "2026-07-30T20:08:00+08:00"
FROZEN = "2026-07-30T20:12:00+08:00"
REVIEWED = "2026-07-30T20:15:00+08:00"


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_text_lf(relative: str, text: str) -> None:
    (ROOT / relative).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def write_json(relative: str, value: dict) -> None:
    write_text_lf(
        relative,
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )


def digest(relative: str) -> tuple[int, str]:
    payload = (ROOT / relative).read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest().upper()


def replace_version_text(text: str) -> str:
    return text.replace("V04", "V05").replace("v04", "v05")


def create_geometry() -> str:
    geometry = read_json("data/route_h/route_h_reference_geometry_spec_v04.json")
    geometry["geometry_spec_id"] = "GEOMETRY-PRL-ROUTE-H-STAGE0-V05"
    geometry["schema_version"] = "5.0.0"
    geometry["created_at"] = CREATED
    geometry["status"] = "frozen_stage0_specification_not_materialized"
    geometry["supersedes"] = "GEOMETRY-PRL-ROUTE-H-STAGE0-V04"
    identity = geometry["material_face_identity"]
    identity["floating_tie_rule"] = {
        "comparison_tolerance": "8*eps_binary64 where eps_binary64=2^-52",
        "dominance_priority": ["abs(u_bar_z)", "abs(u_bar_x)", "abs(u_bar_y)"],
        "rule": (
            "Components whose absolute values differ by no more than "
            "8*eps_binary64 are a tie. Resolve a three- or two-way tie by "
            "z before x before y. Otherwise apply the listed dominant-z and "
            "lateral x/y rules."
        ),
        "reason": (
            "The eight mathematically symmetric corner directions must retain "
            "mirror-consistent material identity despite binary64 roundoff."
        ),
        "materialization_falsifier_closed": (
            "Faces 63 and 159 and their six symmetric partners receive the "
            "same z-dominant priority; no x-neighbor master ray is forced onto "
            "an apical/basal slave face."
        ),
    }
    geometry["reference_state_registry"]["reference_bundle_seal"]["materialization_authorized"] = False
    path = "data/route_h/route_h_reference_geometry_spec_v05.json"
    write_json(path, geometry)
    return digest(path)[1]


def create_contract(geometry_hash: str) -> None:
    contract = read_json("src/route_h/route_h_contract_v04.json")
    contract["contract_id"] = "CONTRACT-PRL-ROUTE-H-STAGE0-V05"
    contract["schema_version"] = "5.0.0"
    contract["created_at"] = CREATED
    contract["status"] = "frozen_stage0_pending_readonly_inspection"
    contract["lifecycle_state"] = "stage0_v05_frozen"
    contract["version_policy"]["supersedes_for_future_work"] = "CONTRACT-PRL-ROUTE-H-STAGE0-V04"
    contract["version_policy"]["v01_v02_and_v03_are_immutable_historical_records"] = False
    contract["version_policy"]["v01_through_v04_are_immutable_historical_records"] = True
    contract["version_policy"]["future_solver_target_if_separately_authorized"] = "CONTRACT-PRL-ROUTE-H-STAGE0-V05"
    contract["authority"] = {
        "user_instruction": "批准，继续",
        "contextual_scope": (
            "Execute approved Stage 1 passive materialization and repair ordinary "
            "same-route implementation blockers without repeated approval."
        ),
        "authorized": [
            "Create an append-only Stage 0 erratum when reference materialization exposes a deterministic specification defect",
            "Materialize the Stage 1 passive reference bundle after the erratum is frozen and checked",
            "Implement and test the passive Stage 1 kernel",
        ],
        "not_authorized": [
            "Modify any v04 frozen artifact",
            "Change the scientific object or contact mechanism",
            "Enable active contraction or Stage 2",
            "Run a full-patch trajectory",
        ],
    }
    geometry_input = contract["direct_inputs"][-1]
    geometry_input["path"] = "data/route_h/route_h_reference_geometry_spec_v05.json"
    geometry_input["sha256"] = geometry_hash
    contract["direct_inputs"].extend([
        {
            "path": "project_control/route_h_stage0_v04_freeze_record.md",
            "sha256": digest("project_control/route_h_stage0_v04_freeze_record.md")[1],
            "role": "immutable v04 freeze baseline",
        },
        {
            "path": "project_control/route_h_stage0_v04_readonly_scientific_review_v01.md",
            "sha256": digest("project_control/route_h_stage0_v04_readonly_scientific_review_v01.md")[1],
            "role": "accepted-with-caveats v04 specification review",
        },
        {
            "path": "project_control/route_h_stage1_authorization_decision_v01.md",
            "sha256": digest("project_control/route_h_stage1_authorization_decision_v01.md")[1],
            "role": "user authorization for Stage 1 passive materialization and implementation",
        },
    ])
    contract["review_finding_resolutions"]["V05-FACE-TIE-001"] = (
        "Binary64 near-equal component comparisons use an 8*eps tie band and "
        "the fixed z-x-y priority, restoring mirror-consistent corner identities "
        "without changing topology, coordinates, mechanics or parameters."
    )
    contract["completion_gate"] = {
        "stage0_v05_contract_frozen": True,
        "reference_geometry_materialized": False,
        "stage1_authorized_by_separate_decision": True,
        "stage2_authorized": False,
        "next_required_action": "read-only v05 erratum inspection, then Stage 1 reference materialization",
    }
    write_json("src/route_h/route_h_contract_v05.json", contract)


def create_specialization(geometry_hash: str) -> None:
    specialization = read_json("src/route_h/route_h_model_specialization_v04.json")
    specialization["specialization_id"] = "SPECIALIZATION-PRL-ROUTE-H-STAGE0-V05"
    specialization["schema_version"] = "5.0.0"
    specialization["contract_id"] = "CONTRACT-PRL-ROUTE-H-STAGE0-V05"
    specialization["created_at"] = CREATED
    specialization["status"] = "frozen_stage0_not_executed"
    specialization["supersedes"] = "SPECIALIZATION-PRL-ROUTE-H-STAGE0-V04"
    specialization["geometry"]["spec_path"] = "data/route_h/route_h_reference_geometry_spec_v05.json"
    specialization["geometry"]["spec_sha256"] = geometry_hash
    specialization["stage1_authorized"] = True
    specialization["stage1_authorization_path"] = "project_control/route_h_stage1_authorization_decision_v01.md"
    specialization["stage2_authorized"] = False
    write_json("src/route_h/route_h_model_specialization_v05.json", specialization)


def create_cases() -> None:
    cases = read_json("data/route_h/route_h_cases_v04.json")
    cases["registry_id"] = "CASES-PRL-ROUTE-H-STAGE0-V05"
    cases["schema_version"] = "5.0.0"
    cases["contract_id"] = "CONTRACT-PRL-ROUTE-H-STAGE0-V05"
    cases["specialization_id"] = "SPECIALIZATION-PRL-ROUTE-H-STAGE0-V05"
    cases["geometry_spec_id"] = "GEOMETRY-PRL-ROUTE-H-STAGE0-V05"
    cases["created_at"] = CREATED
    cases["status"] = "frozen_stage0_stage1_passive_only"
    cases["supersedes"] = "CASES-PRL-ROUTE-H-STAGE0-V04"
    cases["global_rules"]["geometry_materialization_authorized"] = True
    cases["global_rules"]["stage1_authorized"] = True
    cases["global_rules"]["stage2_authorized"] = False
    write_json("data/route_h/route_h_cases_v05.json", cases)


def create_docs_and_registries() -> None:
    coordinate = (ROOT / "docs/route_h/route_h_coordinate_and_sign_convention_v04.md").read_text(encoding="utf-8")
    coordinate = replace_version_text(coordinate)
    coordinate += (
        "\n\n## v05 binary64 face-identity erratum\n\n"
        "When two absolute components of `u_bar` differ by at most `8*eps_binary64`, "
        "they are treated as tied. Dominance is resolved in the fixed priority "
        "`z → x → y`. This affects only the eight mathematically symmetric corner "
        "directions and restores mirror-consistent material labels; it changes no "
        "vertex, face, tetrahedron, equation, parameter, load, or contact law.\n"
    )
    write_text_lf(
        "docs/route_h/route_h_coordinate_and_sign_convention_v05.md", coordinate
    )

    ledger = (ROOT / "docs/route_h/route_h_port_and_power_ledger_v04.csv").read_text(encoding="utf-8")
    write_text_lf(
        "docs/route_h/route_h_port_and_power_ledger_v05.csv",
        replace_version_text(ledger),
    )

    source = ROOT / "tests/route_h/route_h_verification_registry_v04.csv"
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fieldnames = list(rows[0])
    rows = [
        {
            key: replace_version_text(value) if isinstance(value, str) else value
            for key, value in row.items()
        }
        for row in rows
    ]
    rows.append({
        "test_id": "GEOM-FLOAT-TIE-SYMMETRY",
        "stage": "1",
        "gate": "PreA",
        "requirement": (
            "The eight mathematically equal corner directions use the frozen "
            "8*eps z-x-y tie rule and all cell-neighbor master rays hit the "
            "required mirrored slave subtype"
        ),
        "metric": "identity or ray-coverage violations",
        "threshold": "0",
        "units": "count",
        "case_ids": "all",
        "frozen_status": "registered_not_run_authorized_stage1",
        "failure_action": "block Stage 1",
        "review_mapping": "V05-FACE-TIE-001",
    })
    with (ROOT / "tests/route_h/route_h_verification_registry_v05.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_execution_log() -> None:
    text = f"""---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V05
executor: Codex current task; approved single-task Stage 1 repair
started_at: {CREATED}
completed_at: {FROZEN}
status: completed
deviation_records: []
---

# Route H Stage 0 v05 浮点并列勘误执行记录

## 1. 触发

Stage 1 reference materialization 在任何 solver 或 response 之前触发
`V05-FACE-TIE-001`：数学上三轴等权的角方向受到 binary64 舍入影响，
使 face 159 被标为 `lateral_x_plus`，其镜像 face 63 却被标为
`apical_lumen`（心肌模板为 `basal_ecm`）。

在 998 个 cell-neighbor master-face ray 检查中，共有 10 个重复实例因此不能命中
合同要求的 mirrored slave subtype。故 v04 的 reference bundle seal 不能成立。

## 2. 修订

新增而不覆盖 v04：

- 绝对分量差不超过 `8*eps_binary64` 时视为并列；
- 固定按 `z → x → y` 解析并列；
- 非并列方向继续使用 v04 原规则。

该修订只影响 8 个数学对称角方向的 material face identity。cell/ECM 坐标、
拓扑、方程、参数、载荷、contact/adhesion、source-map 和测试阈值均不变。

## 3. 制造检查

- corner directions in tie band：8；
- z-dominant corner identities：8/8；
- lateral directional counts：x-/x+/y-/y+ 各 52；
- registered same-layer neighbor master rays：998；
- illegal or missing required-subtype hit：0；
- v04 frozen files modified：0。

## 4. 授权边界

本次是已批准 Stage 1 内的同路线普通阻断修复，不改变科学对象或接触机制。
Stage 1 reference materialization 可在 v05 只读检查通过后继续；Stage 2 仍未授权。
"""
    write_text_lf(
        "project_control/route_h_stage0_v05_revision_execution_log.md", text
    )


def create_freeze_record(paths: list[str]) -> str:
    rows = []
    for index, path in enumerate(paths, start=1):
        size, checksum = digest(path)
        rows.append(f"| {index} | `{path}` | {size} | `{checksum}` |")
    text = f"""# Route H Stage 0 v05 冻结记录

## 1. 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE0-V05`
- frozen at：`{FROZEN}`
- contract：`CONTRACT-PRL-ROUTE-H-STAGE0-V05`
- specialization：`SPECIALIZATION-PRL-ROUTE-H-STAGE0-V05`
- cases：`CASES-PRL-ROUTE-H-STAGE0-V05`
- geometry：`GEOMETRY-PRL-ROUTE-H-STAGE0-V05`
- scope：仅 `V05-FACE-TIE-001` binary64 material-identity tie erratum
- Stage 1：已由独立用户决定授权被动实现
- Stage 2：未授权

## 2. 冻结清单

| # | 路径 | 字节数 | SHA-256 |
|---:|---|---:|---|
{chr(10).join(rows)}

冻结算法为 SHA-256。v01–v04 保持不可变。本清单任一文件发生字节变化即使本冻结失效。

## 3. 退出检查

- JSON/CSV 可解析；
- v05 cross-reference 指向 v05；
- v04 freeze hash 8/8 保持一致；
- 8 个 corner tie 采用 z 优先；
- 998/998 neighbor master rays 命中要求的 mirrored slave subtype；
- 无方程、参数、拓扑、contact、load、owner 或 threshold 变化；
- active/full-patch/Stage 2 未授权。

下一步只允许新增 v05 只读检查；检查通过后才重新开始 Stage 1 materialization。
"""
    path = ROOT / "project_control/route_h_stage0_v05_freeze_record.md"
    write_text_lf("project_control/route_h_stage0_v05_freeze_record.md", text)
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def create_review(freeze_hash: str, paths: list[str]) -> None:
    checks = "\n".join(
        f"- `{path}`: `{digest(path)[1]}`" for path in paths
    )
    text = f"""---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V05-V01
inspector: Codex current task; single-worker read-only audit after freeze
inspected_at: {REVIEWED}
status: accepted_with_caveats
---

# Route H Stage 0 v05 只读科学检查报告 v01

## 1. 结论

`accepted_with_caveats`。`V05-FACE-TIE-001` 已以最小、确定且镜像对称的规则关闭。
未发现需要改变科学对象、接触形式、参数、载荷或证据解释的新阻断项。

v05 freeze record SHA-256：`{freeze_hash}`。

## 2. 只读复核

冻结后对下列 8 个技术件复算，全部与 freeze record 一致：

{checks}

v04 冻结清单亦复算为 8/8 一致；未覆盖旧版本。

## 3. 反例与修订充分性

v04 的二进制比较使 face 159 的 `|u_x|` 比 `|u_z|` 大 1 ULP，而镜像 face 63
的 `|u_z|` 比另一分量大 1 ULP。相同数学方向因此获得不同 material identity。

v05 的 `8*eps_binary64` tie band：

- 只捕获 8 个数学角方向；没有捕获其他 face；
- 统一按 z 优先将其归入 apical/basal；
- 使 x-/x+/y-/y+ lateral face 数完全相等（各 52）；
- 使全部 998 个登记 neighbor master rays 都命中要求的 slave subtype。

因此该修订既充分关闭 materialization 阻断，也没有扩大模型。

## 4. Caveat

本检查与实现者是同一工作者，不是人员独立复核。其证据级别为单工作者、
冻结后只读、可复算检查。该限制不阻断已授权的 Stage 1 被动验证，但必须保留在
Stage 1 最终 inspection 中。

## 5. 下一状态

允许以 v05 为 Stage 1 frozen input 重新 materialize reference bundle。
Stage 2 仍未授权。
"""
    write_text_lf(
        "project_control/route_h_stage0_v05_readonly_scientific_review_v01.md",
        text,
    )


def main() -> None:
    geometry_hash = create_geometry()
    create_contract(geometry_hash)
    create_specialization(geometry_hash)
    create_cases()
    create_docs_and_registries()
    create_execution_log()
    technical = [
        "data/route_h/route_h_reference_geometry_spec_v05.json",
        "src/route_h/route_h_contract_v05.json",
        "src/route_h/route_h_model_specialization_v05.json",
        "data/route_h/route_h_cases_v05.json",
        "docs/route_h/route_h_coordinate_and_sign_convention_v05.md",
        "docs/route_h/route_h_port_and_power_ledger_v05.csv",
        "tests/route_h/route_h_verification_registry_v05.csv",
        "project_control/route_h_stage0_v05_revision_execution_log.md",
    ]
    freeze_hash = create_freeze_record(technical)
    create_review(freeze_hash, technical)
    print(json.dumps({
        "geometry_sha256": geometry_hash,
        "freeze_sha256": freeze_hash,
        "technical_artifacts": {path: digest(path)[1] for path in technical},
    }, indent=2))


if __name__ == "__main__":
    main()
