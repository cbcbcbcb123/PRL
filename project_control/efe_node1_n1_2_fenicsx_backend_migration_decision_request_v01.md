---
decision_id: DECISION-REQUEST-EFE-NODE1-N1-2-FENICSX-MIGRATION-V01
status: approved
requested_at: 2026-08-19
approved_at: 2026-08-19
decision_record: project_control/efe_node1_n1_2_fenicsx_backend_migration_decision_v01.md
related_report: project_control/efe_node1_n1_2_fenicsx_backend_spike_report_v01.md
parent_authorization: project_control/efe_node1_n1_2_fem_backend_spike_authorization_v01.md
---

# EFE Node 1 N1-2 FEniCSx 后端迁移决策请求 v01

## 推荐决定

建议人类终审：

1. 追认“近零界面净合力”采用总传递载荷归一化的尺度误差；
2. 接受 FEniCSx 受控 spike 技术通过；
3. 批准下一步只做 `N1-2 backend productionization P1`：
   - 将运行时替换改成显式 backend seam；
   - 接入 ECM 自动微分 Jacobian；
   - 评估 PETSc SNES，保留当前稀疏 Newton 作为对照；
   - 完成零态、仿射态、F150 峰值和一个短 SLS 周期回归；
   - 保留参考 Python 后端作为 oracle；
4. P1 完成并经人类复核后，再单独决定是否执行正式
   `D0/E0 -> D1/E1 -> 32-step` N1-2 收敛矩阵。

## 本次不请求

- 不请求立即启动正式 `D1/E1/32-step`；
- 不请求废弃参考后端；
- 不请求 N1-3、Node 2、实验拟合或发布；
- 不请求删除本次产生的 Docker 镜像或停止容器记录。

## 待人类终审

人类终审已于 2026-08-19 指示“同意，继续”。批准记录见
`project_control/efe_node1_n1_2_fenicsx_backend_migration_decision_v01.md`。
