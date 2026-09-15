---
plan_id: EXP-20260802-scientific-review-v01
document_type: normalized_guidance_summary
source_fidelity: derived_from_existing_project_constraint
original_expert_wording_available: false
status: active_constraint_only
---

# 外部科学评审指导摘要

本文件不是专家原文。它仅为现有 `project_control/external_scientific_review_constraints_v01.md` 的导航性摘要；发生任何差异时，以该冻结约束文件及当前适用的更新决定为准。

## 已登记指导

1. 软件一致性、数值有效性和生物学验证作为三条独立证据线管理；局部测试或代数恒等式不能替代完整轨迹与科学验证。
2. 历史 Hybrid X1 主线按 X1-H、X1-I、X1-J、X1-K 的顺序建立完整单步、阻尼空间一致性、重网格能量账本和短轨迹门禁。
3. 在相应门禁通过前，不把规定载荷描述为双向 FSI，不把全局命令量描述为局部传感器，也不开展未经授权的长耦合、参数标定或论文级机制主张。
4. ECM、谱系来源、反馈变量和机械记忆的语义边界必须按证据等级表达，并保留竞争机制或来源假设。
5. 后续版本应显式引用约束；改变执行顺序或科学语义时，应建立新决定并记录用户授权。

## 当前适用说明

项目后来形成了新的 Paper 2 主线和版本化决定。执行时不能只按本摘要恢复历史 X1 顺序，而应同时读取：

- `project_control/CURRENT_STATUS.md`；
- `project_control/prl_independent_theory_mainline_plan_v04.md`；
- 当前任务对应的最新合同或失败记录。

本指导仍用于约束证据等级、失败保全和主张边界；具体执行顺序由适用范围内的最新用户决定和 `project_control` 记录裁定。
