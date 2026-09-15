---
decision_id: DEC-PAPER2-M2A-V02-T64-POWER-LEDGER-DIAGNOSTIC-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
source_failure: project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md
source_result: results/paper2_m2/identity_2d_v02_t64_v01_20260903/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A v02 T64 功率账本失败最小诊断授权 v01

## 1. Goal

只诊断 `ID-LN/DCM/S4/T64/C0` 的功率账本残差为何随网格加密增大，并区分：

1. 稀疏直接求解的代数残差经功率恒等式放大；
2. C0/C1 只是验收标签、没有改变实际求解精度；
3. 归一化分母在某个时刻塌缩，导致相对残差放大；
4. 中点/梯形离散功率恒等式存在实现失配；
5. 大自由度求和的浮点消减误差。

本阶段只定位原因，不修复生产实现，不继续 T64 矩阵。

## 2. Reproducible feedback loop

在同一个 create-only 新包内重算：

- `ID-LN/DCM`；
- S2/S3/S4；
- T64；
- C0/C1。

要求 S2/S3/S4 的基线摘要重放原失败包，除运行时间外数值相对差 `<=1e-12`。S4/C0
必须复现功率账本失败；若不能复现，正式标签为 `NON_REPRODUCIBLE` 并停止。

## 3. Ranked falsifiable hypotheses

### H1 — algebraic solve defect

若代数求解误差是原因，则逐步平衡缺陷

`r_eq = f_mid - h a_mid - A x_mid - G Δx/Δt`

与账本原始残差应通过 `r_eq · Δx` 闭合；对 DC 与 harmonic 系统做 1–2 次残差修正后，
求解残差和账本残差应同步下降，而物理 QoI 不应发生可见改变。

### H2 — non-operational C0/C1

若 C0/C1 只改变验收阈值，则同一空间层的 C0/C1 状态数组、求解残差和账本数组应逐值
相同。此时不得把原 C0/C1 差写成独立的代数容差收敛证据。

### H3 — normalization artifact

若归一化分母塌缩是主因，则最大相对残差所在步的绝对残差仍接近机器误差，而分母
显著小于周期内典型能量/功尺度。必须同时报告原始残差、分母、各功项和周期积分残差。

### H4 — discrete ledger mismatch

若中点离散恒等式实现失配，则即使代数平衡缺陷显著降低，账本残差也不随之下降，且
`ledger residual - r_eq·Δx` 留下系统性非零项。应按每一功项定位，不得修改定义。

### H5 — floating summation limit

若主要是求和消减，则相同逐步项使用普通、pairwise/Kahan 与 long-double 后处理时差异
应解释残差；否则排除此假设。

## 4. Authorized probes

- 基线 `scipy_superlu` 结果；
- 使用同一 SuperLU 因子对 DC/harmonic 方程做 1 次和 2 次残差修正，仅作为诊断分支；
- 每步输出能量变化、主动功、腔侧功、支撑功、drag/SLS 耗散、原始残差、归一化尺度、
  平衡缺陷功和二者差；
- 输出矩阵/RHS/解的范数、相对残差与 normwise backward error；
- 比较 C0/C1 数组 hash 和最大逐值差；
- 普通、补偿求和和 long-double 后处理比较。

不得引入新的求解器家族、改变矩阵、边界条件、时间步、载荷、阈值、校准或模型。

## 5. Write and resource boundary

只允许新增：

- `scripts/diagnose_paper2_m2a_v02_t64_power_ledger_v01.py`；
- `tests/paper2_m2/test_power_ledger_diagnostic_v01.py`；
- create-only 结果包
  `results/paper2_m2/power_ledger_diagnostic_v01_20260903/`；
- `project_control/paper2_m2a_v02_t64_power_ledger_diagnostic_execution_record_v01.md`；
- 完成后更新 `project_control/CURRENT_STATUS.md`。

所有现有源码、runner、测试和旧结果保持只读。仅 CPU 单进程、容器禁网、无 GPU；总预算
`900 s`、峰值内存 `16 GiB`。

## 6. Decision labels and stop rule

正式标签只能是：

- `ALGEBRAIC_SOLVE_DEFECT_CONFIRMED`；
- `NORMALIZATION_ARTIFACT_CONFIRMED`；
- `DISCRETE_LEDGER_MISMATCH_CONFIRMED`；
- `FLOAT_SUMMATION_LIMIT_CONFIRMED`；
- `MULTIFACTOR`；
- `NON_REPRODUCIBLE`；
- `UNRESOLVED`。

完成诊断后停止在 Supervisor Gate。不得在同一阶段修改生产核心、重跑 108 端点或进入
T128；修复必须另立版本化合同、失败回归测试和最小修复决定。
