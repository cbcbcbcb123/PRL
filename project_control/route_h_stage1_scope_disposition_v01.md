---
record_id: SCOPE-PRL-ROUTE-H-STAGE1-V01
status: terminal
contract_id: CONTRACT-PRL-ROUTE-H-STAGE0-V05
authorization_id: DEC-PRL-ROUTE-H-STAGE1-AUTHORIZATION-V01
recorded_at: 2026-07-30T20:48:00+08:00
---

# Route H Stage 1 注册项范围处置 v01

## 结论

Stage 1 v05 registry 共有 40 个 `stage=1` 条目，全部具有可审计终态：

- `passed`：37；
- `not_run_stage2_not_authorized`：2；
- `not_run_full_trajectory_not_authorized`：1。

未运行项不是失败修饰，也没有继承 pass：

| test_id | 终态 | 原因 |
|---|---|---|
| `ENERGY-ACTIVE-DERIVATIVE` | `not_run_stage2_not_authorized` | preferred-length active mechanism 属于 Stage 2 |
| `ACTIVE-ZERO-MOMENT` | `not_run_stage2_not_authorized` | preferred-length active mechanism 属于 Stage 2 |
| `TIME-REFINEMENT` | `not_run_full_trajectory_not_authorized` | Stage 1 明确禁止 active/full-patch trajectory |

## Stage 1 通过边界

Stage 1 的完成依据是计划第 1.2 节的被动模块/制造解 tests：

- reference geometry 与 bundle seal；
- DCM area/bending/volume 能量—力；
- finite-strain viscoelastic ECM；
- material tether 与 dynamic steric；
- action–reaction、objectivity、proper-crossing guard；
- pressure/WSS、fixed support、gauge、source-map 和 mechanical ledger。

`POWER-INTEGRATED-RESIDUAL` 在 Stage 1 只通过已登记的静态保守、黏性松弛和固定支撑
制造账本验证；没有把 Gate A–E 的时间轨迹或 time refinement 标为已运行。

`CONTACT-PENETRATION` 在 reference/manufactured 状态验证 signed gap、零 reference
penetration 和阈值执行路径；没有声称完整 patch trajectory 中的最大穿透结果。

因此 37 个 `passed` 只表示 Stage 1 被动内核和制造证据通过，不表示 Stage 2 cases、
主动传播、时间收敛、空间收敛、生理标定或完整 patch response 通过。

