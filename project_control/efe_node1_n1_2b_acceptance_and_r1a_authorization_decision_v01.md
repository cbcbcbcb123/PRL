---
decision_id: DECISION-EFE-NODE1-N1-2B-ACCEPTANCE-R1A-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r1a_fixed_point_repair_plan_v01.md
related_inspection: project_control/efe_node1_n1_2b_cycle_stability_review_request_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2b 负结果验收及 r1a 授权决定 v01

## Decision

人类终审在收到精确决策请求后，于 2026-08-20 明确回复“同意，继续”。据此：

1. 接受 N1-2b 为有效、可复算的受控负结果；
2. 不接受 D0/E0/F150、T16 已达到周期稳态；
3. 接受当前直接 Picard 分块耦合在周期 3 step 4 的 `Z`—几何固定点门
   受阻，不把它误判为 ECM 反转或接触失效；
4. 批准 N1-2b-r1a：只从已接受的周期 3 step 3 检查点复演激活 `0.10`
   的失败步，并比较冻结 Picard 基线与受保护的自适应固定点加速；
5. 批准补齐根级失败摘要，但不批准完整周期重算。

## Frozen scientific boundary

- D0/E0/F150、`T=1`、`dt=1/16`、激活 `0.10`；
- `mu_ve=0.5`、`eta_ve=0.5`；
- KKT `<=1e-5`、原始未松弛 `r_Z<=1e-4`、`min J>=0.5`、
  `min gap>=-1e-12`；
- 外层最多 12 次；
- 加速只改变迭代猜测，不改变原始固定点方程和最终验收量。

## Boundary

不授权放宽门限、增加外层迭代、重跑周期 3/4、T32/T64、D1/E1、F200、
N1-3、Node 2、实验拟合、Git 或发布。
