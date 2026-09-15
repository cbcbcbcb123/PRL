---
check_id: CHECK-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04-V01
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
checker: Codex current task
checked_at: 2026-08-09
status: ready_for_human_review_failed_gate
independent_inspection: false
---

# Route H Stage 2 Gate A M1 v04 交付前只读自检

## 独立性说明

本记录是同一执行任务的只读自检，不冒充独立 Inspector。用户仍是阶段终审者。

## 合同完成度

- v04 只修改 `maxcor: 20 → 40`，未改方程、几何、材料参数、激活、时间步或门槛；
- RED–GREEN 公共行为测试完成，原 step 86 已通过全部门槛；
- 正式套件在首个新失败 step 194 fail-fast，没有运行后续时间步或继续调参；
- accepted trajectory、rejected candidate 和失败 JSON 在内存语义与持久文件中分离；
- 因四条正式轨迹不完整，Gate A 正确报告为 `failed_invalid_numerics`。

## 证据核验

- Stage 2 tests：`8/8` 通过；相关 Ruff 通过；
- A0 完整到 `t=5.0`；A1 coarse 接受到 `t=3.86`，失败发生于 `t=3.88`；
- 所有已接受 residual `<=1e-8`、gauge `<=1e-12`，几何有限、正体积、0 翻面、0 退化；
- 最大绝对体积误差 `0.01586%`，远低于冻结 `0.5%` 数值门槛；
- v03 failure manifest `51/51` 一致；
- Figure Notebook 自动执行、数据链校验、统一风格校验和代理目检均通过，尚未标记 final。

## 可支持与不可支持的结论

可支持：曲率记忆不足是 v03 step 86 的具体数值因素；`maxcor=40` 修复该失效并覆盖一个激活上升、平台及大部分舒张回程。新失效仍是 residual 失效，不是几何或体积崩坏。

不可支持：Gate A 已通过、完整 5 秒轨迹稳定、时间步收敛、生理参数有效、主动加载机制已验证、ECM/血流耦合或 Nature Physics 级机制结论。

## 人工终审请求

请用户查看 v04 状态图，并决定是否：

1. 接受 M1 v04 为“显著推进但 Gate 仍失败”的阶段结果；
2. 批准起草 M1 v05，其范围应转向求解 projected force balance 的尺度/预条件，而不是继续增加 L-BFGS 记忆或放松体积/残差门槛；
3. 或先要求解释图中细胞状态、形变曲线和新失败证据。
