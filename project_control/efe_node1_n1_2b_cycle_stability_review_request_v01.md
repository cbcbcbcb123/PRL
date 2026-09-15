---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-CYCLE-STABILITY-V01
status: approved_by_human_final_reviewer
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_cycle_stability_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_cycle_stability_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b 周期稳态验证终审请求 v01

## Recommended decision

建议人类终审：

1. 接受本次 N1-2b 为有效、可复算的受控负结果；
2. 不接受“D0/E0/F150、T16 已达到周期稳态”的结论；
3. 接受“几何/能量近重复早于黏弹历史态闭合”作为当前数值观察，但不升级
   为论文机制结论；
4. 接受当前 blocker 是分块 `Z`—几何固定点算法，不是 ECM 反转或接触失效；
5. 批准下一步仅执行 `N1-2b-r1a` 失败步求解器修复 pilot：
   - 从周期 3 已接受的 step 3 检查点复现激活 `0.10` 的同一时间步；
   - 对 `Z`—几何外层固定点增加有残差保护的自适应 Aitken/Anderson
     松弛候选；
   - KKT、`r_Z`、`J`、gap 和 12 次外层上限全部不变；
   - 只比较原 Picard 与受保护加速的残差轨迹、求解次数和状态等价性；
   - 同时补齐中途失败时的根级摘要，但不重跑完整周期；
   - pilot 完成后再次提交人类终审，再决定是否恢复周期 3/4。

## Why not simply run more cycles

周期 1 -> 2 的完整 `Z` 差仍为 `4.98e-2`，远高于 `1e-3`；而周期 3 已在
单步固定点门停止。直接扩大周期数既不能修复单步求解失败，也会把求解器
伪影混入周期收敛判断。

## Longer-term numerical route

若 r1a 证明受保护分块加速可靠，后续仍应评估把解析 SLS 更新并入一致切线或
单周期 Poincare 固定点求解，避免靠大量瞬态周期逼近。这是后续计划，不在
本次请求的执行授权内。

## Not requested

- 不请求放宽 `1e-4` 耦合门或 `1e-3` 周期门；
- 不请求直接重跑周期 3/4；
- 不请求超过 4 周期、T32/T64、D1/E1、F200 或参数扫描；
- 不请求 N1-3、Node 2、实验拟合、论文终稿、Git 或发布；
- 不请求删除任何容器、失败目录或中间结果。

## Human gate

人类终审于 2026-08-20 明确回复“同意，继续”，接受本请求中的精确决策门：
“接受 N1-2b 受控负结果，并批准 N1-2b-r1a 失败步固定点修复 pilot”。
决定记录见
`project_control/efe_node1_n1_2b_acceptance_and_r1a_authorization_decision_v01.md`。

完整周期重算、T32 和 D1/E1 仍未授权。
