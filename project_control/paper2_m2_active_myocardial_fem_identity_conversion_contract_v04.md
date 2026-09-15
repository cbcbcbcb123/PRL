---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V04
status: approved_under_human_standing_authority
planner: supervisor
approved_by: supervisor_under_human_standing_authority
approved_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
base_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
spatial_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
ledger_and_solver_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md
authorization: project_control/paper2_m2a_v03_t64_supervisor_acceptance_and_t128_decision_v01.md
source_t64_result: results/paper2_m2/identity_2d_v03_t64_v01_20260903/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: t128_full_numerical_stage_only
---

# Paper 2 M2：主动心肌 DCM→FEM 身份转换增量合同 v04（T128）

## 1. Contract relation

本文件只把 v03 已通过的模型与数值协议推进到 T128。九工况、两表示、S2/S3/S4、D0、
离散功率账本、全部硬门、观测量和校准均不变。v01–v03 的合同、实现、失败包和通过包
保持只读。

## 2. Frozen T128 matrix

正式矩阵为

`9 cases × 2 representations × 3 spatial levels × T128 × 1 D0 = 54 endpoints`。

端点键必须显式包含 `T128` 和 `D0`。C0/C1 不得重新出现为生产轴。每个端点仍使用
SuperLU direct，不允许残差修正或新求解器。

## 3. Endpoint and within-stage gates

每个端点必须通过 v03 的全部结构门：

- 直接解相对残差 `<=1e-7`；
- normwise backward error `<=1e-12`；
- 功率账本最大归一化 residual `<=1e-8`；
- `ledger residual-r_eq dot Delta x` 最大相对尺度误差 `<=1e-10`；
- 作用—反作用、有限值、非负耗散、周期及 P0/P1 制造门保持原阈值。

T128 内重新计算：

- 74 个 S3→S4 主量空间门，最细两层相对差 `<=1%` 且方向一致；
- 54 个周期门；
- 2 个 S1 热点门；
- 64 段共同投影仍为 sidecar，不替代原生 traction 生产门。

任一门失败立即输出部分摘要、failure 和 hash ledger，停止。

## 4. T64→T128 paired audit

读取 v03 T64 `endpoint_summaries.json`，对 S4/D0 的同工况、同表示主量形成 74 个严格
配对记录：T64 值、T128 值、冻结绝对 floor、相对差和方向待定标签。

只有两个时间层，不能判断三层方向一致，也不能使用 T128→T256 最细层 1% 门。因此该
配对只标记为 `T64_T128_PAIR_AUDIT_ONLY`，不得输出 `TIME_CONVERGED`。若配对缺失、键不
唯一、源 hash 不符或出现非有限值，则阶段 fail-closed；数值差本身不在本阶段新增临时
阈值。

## 5. Stage label and outputs

全部 54 个端点、T128 内结构/空间/周期/热点门和配对完整性门通过时，唯一正式标签为
`T128_STAGE_PASS_V04`。它不等于三时间层收敛，也不等于 identity 通过。

必须输出：

- run manifest、源 T64 hash、源校准锁和实现 hash；
- 54 个端点摘要、结构门和 T128 stage gate；
- 74 个 T64→T128 配对审计；
- 12 个 S4/D0 动态留出 NPZ 及有限值审计；
- pass/failure、资源记录和完整 hash ledger；
- 执行记录与 `CURRENT_STATUS.md` 更新。

create-only 结果包：
`results/paper2_m2/identity_2d_v04_t128_v01_20260903/`。

## 6. Implementation boundary

允许新增：

- `src/paper2_m2/protocol_v04.py`；
- `src/paper2_m2/identity_2d_v04.py`；
- `scripts/run_paper2_m2_identity_2d_t128_v04.py`；
- `tests/paper2_m2/test_protocol_v04.py`；
- `tests/paper2_m2/test_identity_2d_v04.py`；
- 指定结果包、T128 执行记录并更新 `CURRENT_STATUS.md`。

允许复用 v03 的通用离散账本与直接解审计函数，但不得修改 v03。T128 的共同投影、端点
键和阶段门必须由 v04 明确承载，不能误用硬编码 T64 的 v03 键或协议字段。

## 7. Tests and provenance

测试至少覆盖：

- T128/54 端点协议计数和无 C0/C1；
- 一个真实 T128 S4 端点的功率、闭合与 D0 双残差门；
- 74 个空间记录、54 个周期记录、2 个热点记录、74 个时间配对记录的合成计数；
- T64 源摘要/哈希锁、校准锁和有限值；
- v03 旧失败回归与已通过测试不退化。

所有 JSON 禁止 NaN/Inf。v01–v03 关键文件在运行前后必须逐项哈希一致。

## 8. Resources and stop boundary

- CPU 单进程、BLAS/OMP 单线程、固定 DOLFINx CPU 环境、禁网、无 GPU；
- 总预算 `5400 s`、峰值内存 `16 GiB`；
- 不授权 T256、三层时间收敛裁决、identity gate、重新校准、S5、M2B、三维、整心房、
  真实几何、流体、CFD/FSI、GPU、新求解器或参数扫描。

## 9. Evidence boundary

`T128_STAGE_PASS_V04` 只证明冻结理想二维模型在 T128 层的结构与空间数值门通过，并形成
与 T64 的完整配对。它不证明时间收敛、DCM–FEM identity、生理真实性或器官级可迁移性。
