---
decision_id: DECISION-EFE-NODE1-N1-2B-R2-ACCEPTANCE-R3-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r3_transactional_cycle_plan_v01.md
related_inspection: project_control/efe_node1_n1_2b_r2_transactional_step_worker_review_request_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2b-r2 验收及 r3 授权决定 v01

## Decision

人类终审于 2026-08-20 明确回复“同意，继续”。据此：

1. 接受 r2 为有效、可复算的单步事务 seam；
2. 接受 3 个独立 worker 的确定性复现、父进程 oracle 和 create-only 提交；
3. 接受受控失败不改变接受输入的负控结果；
4. 批准 r3 将该 seam 接入周期 driver；
5. 批准从原 N1-2b 已接受 cycle 2 末态连续重算 cycle 3 和 cycle 4；
6. 是否达到周期稳态仍由 r3 结果和后续人类终审决定。

## Frozen boundary

- D0/E0/F150、T16、周期 `T=1`、峰值激活 `0.20`；
- `mu_ve=eta_ve=0.5`，未松弛 Picard，最多 12 次外层迭代；
- 每个时间步由新鲜 worker 生成 staging 候选，父进程复核原全部硬门后
  create-only 提交；
- 任一步失败即停止、保留证据，不自动重试或改变算法；
- 只计算 cycle 3–4，并使用原登记周期差判据；
- r3 完成后提交人类终审。

## Boundary

不授权门限修改、Aitken/Anderson、T32/T64、D1/E1、F200、参数扫描、
N1-3、Node 2、实验拟合、Git 或发布。

