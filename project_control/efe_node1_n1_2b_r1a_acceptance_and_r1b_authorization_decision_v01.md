---
decision_id: DECISION-EFE-NODE1-N1-2B-R1A-ACCEPTANCE-R1B-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_plan_v01.md
related_inspection: project_control/efe_node1_n1_2b_r1a_fixed_point_repair_review_request_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2b-r1a 验收及 r1b 授权决定 v01

## Decision

人类终审于 2026-08-20 明确回复“同意，开始”。据此：

1. 接受 r1a 为有效诊断结果；
2. 接受失败步可在冷检查点重启后求解，且新 Picard 与 Aitken 收敛到同一
   固定点；
3. 不采用 Aitken 作为生产默认耦合器；
4. 批准 r1b 仅审计同一失败步的冷/热后端路径敏感性和重复性；
5. 不批准完整周期重算或周期稳态声明。

## Frozen boundary

- 周期 3 已接受 step 3 检查点，目标仍为 step 4、激活 `0.10`；
- D0/E0/F150、`dt=1/16`、`mu_ve=eta_ve=0.5`；
- Picard、最多 12 次外层迭代，原 KKT、`r_Z`、`J` 和 gap 门全部不变；
- 冷路径和可恢复历史预热路径各至少 3 次；
- 只定位后端状态依赖、重复性和非线性路径放大，不修改本构或求解门。

## Boundary

不授权 Aitken 生产化、事务性自动重启生产化、完整周期 3/4、T32/T64、
D1/E1、F200、参数扫描、N1-3、Node 2、实验拟合、Git 或发布。
