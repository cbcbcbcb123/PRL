---
decision_id: DEC-PAPER2-M2A-V03-T64-ACCEPT-T128-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_execution: project_control/paper2_m2a_v03_ledger_repair_and_t64_execution_record_v01.md
accepted_result: results/paper2_m2/identity_2d_v03_t64_v01_20260903/
next_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v04_t128_full_numerical_stage_only
---

# Paper 2 M2A v03 T64 验收与 T128 执行决定 v01

## 1. Supervisor acceptance

Supervisor 接受 `T64_NUMERICAL_PASS_V03`。独立复核结果：

| 检查 | 复核结果 |
|---|---:|
| 唯一端点 | 54/54 |
| 结构门 | 54/54 |
| 空间主量门 | 74/74 |
| 周期门 | 54/54 |
| 热点门 | 2/2 |
| Phase R / T64 hash ledger | 12/12、23/23 |
| JSON / NPZ | 22/22 可解析；15 个 NPZ 的 450 个数组全有限 |
| v01/v02 只读输入 | 0 项哈希漂移 |

独立重算的最坏值与执行记录一致：空间差 `0.00939753939133803 < 0.01`；功率账本
`4.5625235815361454e-09 < 1e-08`；离散闭合
`2.30777539556273e-14 < 1e-10`；D0 相对残差
`2.9681468104030423e-08 < 1e-07`；后向误差
`1.0172675692304304e-15 < 1e-12`。

该验收只确认 T64 数值层。它不是 DCM–FEM identity 结论。

## 2. T128 authorization

按 `paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md` 执行完整 T128
数值阶段：九工况、两表示、S2/S3/S4、单一 D0，共 54 个端点。

本阶段必须：

- 逐值锁定 v03 公式、校准、空间梯度、D0 双残差门及所有结构门；
- 在 T128 内重新通过 S3→S4 的 1% 空间门、周期门和热点门；
- 对 S4/D0 的 74 个主量输出 T64→T128 配对差，但不得用两个时间层宣称时间收敛；
- 保存 12 个 S4/D0 动态留出端点供 T256/最终时间门使用；
- 任一硬门失败立即 fail-closed。

## 3. Stop boundary

即使 T128 全门通过，本决定也不授权 T256、三时间层方向/最细层收敛裁决、跨表示
identity gate、M2B、三维、整心房、流体或 GPU。执行完成后停止在 Supervisor Gate。

不允许修改 v01–v03 文件或旧结果，不允许重新校准、恢复 C0/C1、改变 1%/功率/闭合
阈值或引入新求解器。
