---
decision_id: DECISION-EFE-NODE1-N1-2-FENICSX-MIGRATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-19
related_plan: project_control/efe_node1_n1_2_backend_productionization_p1_plan_v01.md
related_inspection: null
memory_target: null
---

# EFE Node 1 N1-2 FEniCSx 后端迁移决定 v01

## Decision

人类终审指示“同意，继续”，据此：

1. 追认近零界面净合力采用总传递载荷归一化的尺度误差；
2. 接受 FEniCSx 受控 spike 技术通过；
3. 批准执行 `N1-2 backend productionization P1`；
4. P1 完成后必须再次提交人类终审，才可决定是否执行正式
   `D0/E0 -> D1/E1 -> 32-step` N1-2 收敛矩阵。

## Authorized scope

- 建立显式 ECM backend seam，取消运行时 monkeypatch；
- 接入并验证 ECM UFL 自动微分 Jacobian；
- 评估 PETSc SNES，并保留现有稀疏 Newton 对照；
- 回归 M0、仿射态、F150 峰值及一个短 SLS 周期；
- 保留 Python 参考后端作为 oracle。

## Boundary

本决定不授权正式 `D1/E1/32-step`、N1-3、Node 2、实验拟合、发布、
删除 Docker 证据容器或废弃参考后端。
