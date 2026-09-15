---
decision_id: DECISION-EFE-NODE1-N1-2-BACKEND-P1-ACCEPTANCE-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-19
related_plan: project_control/efe_node1_n1_2_backend_productionization_p1_plan_v01.md
related_inspection: project_control/efe_node1_n1_2_backend_productionization_p1_execution_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2 backend productionization P1 验收决定 v01

## Decision

人类终审明确指示“接受 P1，批准 N1-2a 16-step pilot”。据此：

1. 接受 P1 执行检查通过；
2. 接受 `fenicsx_ufl_ad_serial_v02_lazy_tangent` 为候选 ECM 生产后端；
3. 保留 Python ECM oracle 与现有 SciPy 稀疏 Newton；
4. 接受 PETSc SNES 当前仅证明 ECM 子问题技术可用、不替换全系统 Newton；
5. 批准执行 D0/E0/F150、16-step 的完全耦合黏弹性单周期 pilot。

## Boundary

本决定不接受 16-step pilot 为周期稳态或收敛证据，不授权立即执行 32-step、
D1/E1、N1-3、Node 2、实验拟合、远程 Git 或发布。
