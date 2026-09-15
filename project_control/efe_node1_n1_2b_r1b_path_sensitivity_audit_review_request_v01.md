---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-R1B-PATH-SENSITIVITY-AUDIT-V01
status: approved_by_human_final_reviewer
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b-r1b 路径敏感性审计终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 r1b 为有效、可复算的路径敏感性审计；
2. 接受“未观察到 FEniCSx 可恢复历史状态依赖”；
3. 接受“当前冻结环境中的三次冷、三次预热 Picard 完全可重复，均 3 次
   外层迭代通过”；
4. 接受“稀疏非线性精化会确定性放大捕获层的极小差异”；
5. 保留历史 12 次失败为路径特有负结果，不再把它归因于后端缓存或固定点
   不可解；
6. 不接受 N1-2 已达到周期稳态；
7. 批准下一步仅执行 `N1-2b-r2` 事务性 time-step worker 集成 pilot。

## Proposed r2 boundary

r2 把一个时间步变成可复算的事务单元：

- 主周期 driver 只提供最后接受检查点、激活、`dt` 和冻结求解合同；
- 新鲜子进程完成该步的全部 Picard 固定点迭代；
- worker 写出输入数组摘要、逐轮证据、候选检查点和根级结果；
- driver 只有在 KKT、原始 `r_Z`、`J`、gap 和其他硬门全部通过后才提交
  候选；失败时保持最后接受检查点不变；
- 先只对周期 3 step 4 做 3 次集成复演，要求与 r1b 确定性终态逐元素一致；
- r2 完成后再次提交人类终审，再决定是否从周期 3 step 3 恢复周期 3/4。

该路线不把“失败后重试”当成数值修复，而是把每个时间步的运行环境和提交
边界显式化，从源头避免长生命周期隐藏状态进入科学证据。

## Why not resume the full cycle now

失败步局部可重复已经成立，但生产周期 runner 仍在长生命周期主进程中执行
捕获阶段。若现在直接恢复周期，仍可能重现未封存的路径微差，且无法保证
失败时严格回滚。先完成一个单步事务集成 pilot，成本远小于再次运行整周期，
也能为后续通用 DCM–FEM 框架提供可复算的 step-level seam。

## Not requested

- 不请求采用 Aitken；
- 不请求放宽任何状态门或周期门；
- 不请求本轮直接运行周期 3/4、T32/T64、D1/E1 或参数扫描；
- 不请求 N1-3、Node 2、实验拟合、论文终稿、Git 或发布。

## Exact human gate

请求人类终审明确回复是否接受：

> 接受 r1b 审计结论；批准 r2 事务性 time-step worker 单步集成 pilot。

在获得明确批准前，r2 和完整周期均不启动。

## Human decision

人类终审于 2026-08-20 明确回复“批准，继续”，接受 r1b 审计结论并批准
r2 事务性 time-step worker 单步集成 pilot。完整周期、T32 和 D1/E1 仍未
授权。
