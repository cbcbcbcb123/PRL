---
index_id: PRL-EXTERNAL-EXPERT-PLAN-INDEX
status: current
updated_at: 2026-09-14
---

# 外部专家指导方案索引

| 方案 ID | 主题 | 状态 | 原件 | 适用范围 | 采纳/约束记录 |
|---|---|---|---|---|---|
| `PRL_Codex_Stage_Contracts_v03` | 三维细胞分辨心室 Z0–Z11 分阶段执行合同 | `active_user_selected` | `plan/active/PRL_Codex_Stage_Contracts_v03/`，35/35 文件与项目内保全副本哈希一致 | 主分阶段框架继续有效；MeshCell3D 已按用户决定停止作为当前前向内核，其全部历史结果原状态保留。受控 SimuCell3D 的 Z1-TF2-M0 七门通过，仅构成换核资格。Z1-TF2-B 已按冻结合同完成唯一一次 `2×7` 矩阵，裁决为 `failed_numerical`：2 条 `NO_LUMEN` 轨迹完整、12 条含腔压轨迹触发体积停止门，形成/维持/消融形态门均 `not_run`。下一修订资格片尚未形成合同或获得授权；父 Z1 仍为 `UNRESOLVED`，Z2–Z11 均 NOT_RUN | `project_control/ventricle_stage_contracts_v03_adoption_v01.md`；`project_control/ventricle_simucell3d_kernel_transition_decision_v01.md`；`project_control/ventricle_simucell3d_kernel_migration_precheck_execution_record_v01.md`；`project_control/ventricle_simucell3d_trilayer_shape_formation_contract_v01.md`；`project_control/ventricle_simucell3d_trilayer_shape_formation_execution_record_v01.md` |
| `EXP-20260802-scientific-review-v01` | Hybrid X1-H 以后科学与软件主张约束 | `retired_evidence_only` | `unknown`，当前工作区未定位到 | Hybrid已退出前向主线；原约束仅用于解释精选历史证据，不再授予执行权限 | `project_control/external_guidance_adoption_EXP-20260802_v01.md`；`project_control/external_scientific_review_constraints_v01.md`；`project_control/repository_cleanup_retired_path_map_v01.md` |
| `EXP-20260909-001-paper2-lineage-ecm` | Paper 2 分裂可见性、有限心内膜细胞层与 ECM 选择性记忆 | `retired_evidence_only` | `plan/active/EXP-20260909-001-paper2-lineage-ecm/source/review-and-execution-plan.html` | 专家原件保留但Paper2前向执行已被用户当前主线决定取代；仅保留谱系奇模态精选结果和治理记录 | `project_control/external_guidance_adoption_EXP-20260909-001-paper2-lineage-ecm_v01.md`；`project_control/paper2_lineage_ecm_active_execution_plan_v01.md`；`project_control/repository_cleanup_retired_path_map_v01.md` |

## 使用规则

1. 先检查方案状态和适用范围；
2. 再读取对应的 `project_control` 采纳决定；
3. 与当前主线、冻结失败和最新用户决定核对；
4. 只有存在明确执行合同或当前授权时才实施；
5. 计划、模板或局部检查不得被标为完整集成或科学验证通过。

`PRL_Codex_Stage_Contracts_v03` 的外部专家原件及哈希保持不变。其“薄层 ECM 网络”条款只在前向执行适用范围内被最新用户决定 v05 取代；该取代记录位于 `project_control/`，不回写或伪造专家原文。

2026-09-09 的 Paper 2 方案按原文件与原哈希归档；项目采纳和执行授权另存于 `project_control/`，不改写专家源文件中的历史 `reviewed` 状态。
