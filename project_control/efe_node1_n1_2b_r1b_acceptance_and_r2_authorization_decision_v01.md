---
decision_id: DECISION-EFE-NODE1-N1-2B-R1B-ACCEPTANCE-R2-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r2_transactional_step_worker_plan_v01.md
related_inspection: project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_review_request_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2b-r1b 验收及 r2 授权决定 v01

## Decision

人类终审于 2026-08-20 明确回复“批准，继续”。据此：

1. 接受 r1b 为有效、可复算的路径敏感性审计；
2. 接受在可恢复历史范围内未观察到 FEniCSx 状态污染；
3. 接受当前稀疏非线性路径会确定性放大极小捕获差异；
4. 批准 r2 仅实现和验证一个事务性 time-step worker 单步集成 seam；
5. 不批准完整周期恢复或周期稳态声明。

## Frozen boundary

- 输入仍为周期 3 已接受 step 3，目标仍为 step 4、激活 `0.10`；
- D0/E0/F150、`dt=1/16`、未松弛 Picard 和全部原硬门；
- 3 次独立新进程成功事务，要求与 r1b 终态逐元素一致；
- 1 次受控失败注入，要求候选不提交且输入检查点不变；
- 主进程在 worker 完成后独立复核硬门，复核通过后才生成唯一接受检查点。

## Boundary

不授权完整周期 3/4、自动失败重试生产策略、Aitken、门限修改、T32/T64、
D1/E1、F200、参数扫描、N1-3、Node 2、实验拟合、Git 或发布。
