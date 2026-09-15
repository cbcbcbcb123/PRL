---
decision_id: DEC-PAPER2-M2A-V02-DIAGNOSTIC-ACCEPT-V03-REPAIR-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
diagnostic_record: project_control/paper2_m2a_v02_t64_power_ledger_diagnostic_execution_record_v01.md
diagnostic_result: results/paper2_m2/power_ledger_diagnostic_v01_20260903/
superseded_execution_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
new_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v03_ledger_repair_pilot_then_t64_full_gate
---

# Paper 2 M2A v02 诊断验收与 v03 最小修复决定 v01

## 1. Supervisor acceptance

Supervisor 独立复核并接受正式诊断标签
`DISCRETE_LEDGER_MISMATCH_CONFIRMED`：

- `ID-LN/DCM/S4/T64/C0` 精确复现
  `1.465114585633258e-07 > 1e-08`；
- 最坏步账本 residual 的 `99.70%` 不能由 `r_eq·Delta x` 解释；
- 同因子残差修正、归一化尺度与普通/pairwise/Kahan/long-double 求和均不能解释主要失配；
- C0/C1 的状态、求解残差、账本及输出数组逐值相同，只改变事后验收阈值。

独立复核包括：9/9 结果哈希一致、9/9 JSON 可解析、脚本与测试 SHA-256 一致、宿主与
固定 CPU 环境定向测试均为 4/4 通过。Linux long-double NPZ 的 Windows 读取限制只属于
可移植性 caveat，不改变科学结论。

## 2. Accepted root cause

现有生产账本先分别计算两个绝对材料能量，再以
`E(x_{n+1},a_{n+1})-E(x_n,a_n)` 相减。细网格时绝对能量相对单步增量很大，端点相减
把浮点消减误差带入账本。对当前二次—双线性能量，精确的中点离散增量为

`Delta E = (M x_mid + h a_mid) dot Delta x
           + (h dot x_mid + c a_mid) Delta a`。

该式在精确算术下与端点能量差恒等，并与 Crank–Nicolson 中点平衡完全同构。生产账本
应使用这一离散增量；端点能量仍可保留为可审计输出，但不得再作为细网格功率门的差分
计算路径。

## 3. Solver-label decision

C0/C1 不是当前 SuperLU 直接解的可操作容差，因此 v03 正式撤销它们作为独立数值收敛
轴，不把两个相同解重复计算并包装成 0.5% 容差证据。历史 v01/v02 的 C0/C1 记录原样
保留并明确标注为 non-operational。

v03 使用唯一直接解验证级 `D0`：

- 相对方程残差 `<=1e-7`；
- normwise backward error `<=1e-12`；
- 不引入新求解器、迭代容差或残差修正作为生产算法。

这不是放宽失败门：功率账本 `1e-8`、空间 `1%`、周期、耗散、作用—反作用和后续身份
门均保持不变。

## 4. Authorized progression

按 `paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md` 连续执行：

1. 先运行 `ID-LN/DCM` 的 S2/S3/S4、T64、D0 六端点修复试验；
2. 只有六端点全部通过修复合同，才自动进入 v03 T64 全 54 端点门；
3. 任一硬门失败立即 fail-closed，并停在 Supervisor Gate；
4. 即使 T64 全门通过，也不得在本决定下进入 T128、T256 或 identity gate。

允许新增 v03 模块、runner、测试、create-only 结果包、执行记录并更新
`CURRENT_STATUS.md`。v01/v02 源码、旧结果、阈值和校准保持只读。

## 5. Evidence boundary

本决定修复数值账本并移除虚假的容差重复，不预设 DCM–FEM 等价。任何 T64 通过只表示
当前理想二维模型在冻结门下获得数值可信度；不证明生理真实性、三维/整心房可扩展性、
EFE 机制或流体耦合结论。
