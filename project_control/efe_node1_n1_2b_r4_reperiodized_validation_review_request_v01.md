---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-R4-V01
status: pending_human_final_review
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r4_reperiodized_validation_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_r4_reperiodized_validation_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b-r4 解析周期化与事务验证终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 r4 暖启动及两个事务周期为有效、可复算执行；
2. 接受 32/32 单步事务、状态门和 create-only 提交全部通过；
3. 接受 cycle 5→6 的缩短、牵引和储能波形达到周期门；
4. 接受 `Z` 范数波形 `3.85e-3`、周期末完整 `Z` `3.59e-3` 未达到
   `1e-3`；
5. 不接受 N1-2 已达到 T16 周期稳态；
6. 批准 `N1-2b-r5` 进行一次、也是最后一次外层周期化修正：使用 cycle 6
   实际 ECM 几何历史重新构造解析周期 `Z`，phase 0 重平衡后运行两个事务
   周期 7–8。

## Why one bounded outer correction is justified

r4 的解析 `Z` 对冻结 cycle 4 几何是 `5.54e-16` 周期的，但 phase 0 机械
重平衡和随后的完全耦合运动会改变几何历史，所以它不是完整耦合周期映射的
固定点。到 cycle 5→6，三个宏观波形已经在 `1.63e-4` 或更低，说明几何
历史本身已经高度重复；用 cycle 6 几何再做一次解析修正，是对耦合周期映射
的一次外层固定点迭代，而不是改方程或放宽门。

按当前瞬态收缩率直接追加周期，预计仍需约 3–4 个周期；一次解析修正加两个
验证周期只需 32 个 worker。为避免事后反复追逐阈值，r5 预登记为最后一次
这种修正：若 cycle 7→8 仍未过五项门，不再重复暖启动，而转入显式耦合周期
shooting/fixed-point 求解器的独立新合同。

## Proposed r5 frozen boundary

- 源几何只使用正式 r4 cycle 6 的 17 相位 ECM 顶点历史；
- 暖启动和 phase 0 使用 r4 的全部父审计门，不修改容差；
- 两个动态周期仍为新鲜 worker、父 oracle、SLS/耗散一致性和 create-only
  提交；
- 只运行 cycle 7–8；第二周期相对第一周期的五项门全部 `<=1e-3` 才形成
  T16 周期稳态候选；
- 任一步失败或任一周期门失败即保留受控负结果；
- r5 后返回人类终审，不自动进入 T32、D1/E1、参数扫描、N1-3 或 Node 2。

## Exact human gate

请求人类终审明确回复是否接受：

> 接受 r4 的有效执行及“宏观周期闭合、ECM 内部记忆仍未过门”的结论；
> 不接受 N1-2 已达 T16 稳态；批准 r5 使用 cycle 6 几何进行最后一次解析
> 周期化修正，并运行两个事务验证周期 7–8。

在获得明确批准前，不执行 r5 或新增动态周期。

