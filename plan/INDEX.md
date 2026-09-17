---
index_id: PRL-EXTERNAL-EXPERT-PLAN-INDEX
status: current
updated_at: 2026-09-17
---

# 外部专家指导方案索引

| 方案 ID | 主题 | 状态 | 原件 | 适用范围 | 采纳/约束记录 |
|---|---|---|---|---|---|
| `PRL_Codex_Stage_Contracts_v03` | 三维细胞分辨心室 Z0–Z11 分阶段执行合同 | `retired_forward_execution_evidence_preserved` | `plan/active/PRL_Codex_Stage_Contracts_v03/`，原件及原哈希保留 | 2026-09-17用户明确取消所有DCM前向运行、恢复、扩展和DCM--FEM比较，改为FEM唯一主线。该包仍用于解释历史结果；其内核和执行顺序不再约束当前FEM。路径保留在active中不等于当前有效；未改写专家原件。 | `project_control/ventricle_fem_only_measured_contour_decision_v01.md`；历史采纳：`project_control/ventricle_stage_contracts_v03_adoption_v01.md`；历史执行：`project_control/ventricle_simucell3d_trilayer_shape_formation_execution_record_v01.md` |
| `EXP-20260802-scientific-review-v01` | Hybrid X1-H 以后科学与软件主张约束 | `retired_evidence_only` | `unknown`，当前工作区未定位到 | Hybrid已退出前向主线；原约束仅用于解释精选历史证据，不再授予执行权限 | `project_control/external_guidance_adoption_EXP-20260802_v01.md`；`project_control/external_scientific_review_constraints_v01.md`；`project_control/repository_cleanup_retired_path_map_v01.md` |
| `EXP-20260909-001-paper2-lineage-ecm` | Paper 2 分裂可见性、有限心内膜细胞层与 ECM 选择性记忆 | `retired_evidence_only` | `plan/active/EXP-20260909-001-paper2-lineage-ecm/source/review-and-execution-plan.html` | 专家原件保留但Paper2前向执行已被用户当前主线决定取代；仅保留谱系奇模态精选结果和治理记录 | `project_control/external_guidance_adoption_EXP-20260909-001-paper2-lineage-ecm_v01.md`；`project_control/paper2_lineage_ecm_active_execution_plan_v01.md`；`project_control/repository_cleanup_retired_path_map_v01.md` |

## 使用规则

1. 先检查方案状态和适用范围；
2. 再读取对应的 `project_control` 采纳决定；
3. 与当前主线、冻结失败和最新用户决定核对；
4. 只有存在明确执行合同或当前授权时才实施；
5. 计划、模板或局部检查不得被标为完整集成或科学验证通过。

`PRL_Codex_Stage_Contracts_v03` 的外部专家原件及哈希保持不变。历次局部条款取代记录继续保留；当前前向适用性以2026-09-17的FEM唯一主线决定为准，不回写或伪造专家原文。

2026-09-09 的 Paper 2 方案按原文件与原哈希归档；项目采纳和执行授权另存于 `project_control/`，不改写专家源文件中的历史 `reviewed` 状态。
