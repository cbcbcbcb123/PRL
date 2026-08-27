---
decision_id: DECISION-EFE-THEORY-MAINLINE-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-13
related_plan: project_control/efe_theory_mainline_node_plan_v01.md
supersedes:
  - project_control/publication_three_node_single_paper_decision_v01.md
  - project_control/research_mainline_three_node_plan_v02.md
preserves:
  - project_control/external_scientific_review_constraints_v01.md
---

# EFE 理论主线授权决定 v01

## Decision

项目主应用正式切换为 EFE（endocardial fibroelastosis）。先执行纯理论路线，按 Node 0–4 逐级推进，并由人类终审在每个 Node 后决定保留、修改、替换或停止。

本决定只授权执行 **Node 0：EFE 最小理论合同**。它不授权 Node 1 的完整 DCM–FEM 长耦合、参数标定、斑马鱼数据拟合、双向 FSI 或论文级 EFE 机制结论。

## Consequences

- 旧的“心内膜褶皱”与普通心肌间质纤维化主线转为历史备选，不删除、不覆盖；
- 既有快速三层力学降级为 EFE 慢性重塑的驱动内核；
- EFE 细胞来源采用 EndMT、既有间充质/心外膜来源和混合来源的竞争框架；
- 现有 X1-K 失败状态及 `project_control/external_scientific_review_constraints_v01.md` 的证据边界保持有效；
- 只有 Node 0 通过 Human Gate 0 后，才可另行批准 Node 1。

## Publication Boundary

Nature Physics 仍是最高目标，但只有在后续证明可复现的普适物理规律、完成替代机制检验并取得至少一个未参与拟合的疾病模型预测后，才允许使用该投稿定位。Node 数量或软件完成度不等于投稿资格。
