---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V05
status: approved_under_human_standing_authority
planner: supervisor
approved_by: supervisor_under_human_standing_authority
approved_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
base_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
spatial_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
ledger_and_solver_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md
t128_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md
authorization: project_control/paper2_m2a_v04_t128_supervisor_acceptance_and_t256_decision_v01.md
source_t64_result: results/paper2_m2/identity_2d_v03_t64_v01_20260903/
source_t128_result: results/paper2_m2/identity_2d_v04_t128_v02_20260903/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: t256_full_numerical_and_three_level_time_gate_only
---

# Paper 2 M2：主动心肌 DCM→FEM 身份转换增量合同 v05（T256 与三层时间门）

## 1. Goal and contract relation

本文件只把 v04 已通过的冻结二维理想模型推进到 T256，并完成 T64/T128/T256 三层时间
裁决。九工况、两表示、S2/S3/S4、D0、离散功率账本、观测量、校准、绝对 floor 和全部
既有阈值均不变。v01-v04 的合同、实现、测试、失败包和成功包保持只读。

本阶段回答的唯一问题是：在冻结空间梯度与 D0 直接求解语义下，预注册主量是否进入
方向一致、相邻层变化不反增且最细时间差不超过 1% 的数值带。它不计算跨表示 identity。

## 2. Frozen T256 matrix

正式矩阵为：

`9 cases × 2 representations × 3 spatial levels × T256 × 1 D0 = 54 endpoints`。

端点键必须显式包含 `T256` 和 `D0`。C0/C1 不得重新出现为生产轴。每个端点仍使用
SuperLU direct；不允许残差修正、新求解器、重新校准或参数搜索。

## 3. Frozen inputs and preflight

计算前必须锁定并复核：

- v03 T64 成功包的 `endpoint_summaries.json`、`pass_summary.json` 与 hash ledger；
- v04.1 T128 成功包的同类文件、12 个动态留出 NPZ 与 hash ledger；
- 原校准文件、v01-v04 合同及 v03-v04 生产实现；
- v04.1 路径修复 runner 与定向测试。

所有项目路径必须在创建输出目录、写 manifest 或加载生产 runner 前规范化为项目内绝对
路径；任何项目外路径立即 fail-closed。源锁、键唯一性、JSON 严格解析或有限值检查失败
时不得开始 54 端点矩阵。

## 4. Endpoint and within-stage gates

每个 T256 端点必须通过 v03/v04 的全部结构门：

- D0 相对方程残差 `<=1e-7`；
- normwise backward error `<=1e-12`；
- 功率账本最大归一化 residual `<=1e-8`；
- `ledger residual-r_eq dot Delta x` 最大相对尺度误差 `<=1e-10`；
- 作用—反作用、有限值、非负耗散、周期及 P0/P1 制造门保持原阈值。

T256 内重新计算并全部通过：

- 74 个 S3→S4 主量空间门，最细两层相对差 `<=1%` 且方向一致；
- 54 个周期门；
- 2 个 S1 热点门；
- 64 段共同投影仍只作 sidecar，不替代原生 traction 生产门。

任一门失败立即保存部分摘要、failure 与 hash ledger，并停止。

## 5. T64/T128/T256 three-level time gate

只对 S4/D0 的同工况、同表示、同主量形成 74 个唯一三层记录。每个主量使用 v03/v04
已冻结的绝对 floor `f_q`。定义：

`delta_01 = q_T128 - q_T64`

`delta_12 = q_T256 - q_T128`

`r_01 = abs(delta_01) / max(abs(q_T64), abs(q_T128), f_q)`

`r_12 = abs(delta_12) / max(abs(q_T128), abs(q_T256), f_q)`

每条记录必须同时满足：

1. `r_12 <= 0.01`；
2. `delta_01 * delta_12 >= 0`，或两段变化均不超过
   `0.01 * max(abs(q_T64), abs(q_T128), abs(q_T256), f_q)`；
3. `abs(delta_12) <= abs(delta_01) + f_q`，即在冻结 floor 的分辨率内不允许相邻层变化反增；
4. 三个值、两个相对差和 floor 全部有限，来源键唯一且 hash 锁一致。

必须输出 74/74 记录、逐条原始值、两段变化、两段相对差、方向判定、变化不反增判定和
最终判定。任何一条失败均不得输出时间收敛通过标签，也不得进入 identity gate。

本门只证明这些预注册标量主量的三层数值行为；不拟合或宣称时间收敛阶。

## 6. Outputs and formal label

必须输出：

- run manifest、T64/T128 源锁、校准锁、v05 协议摘要和实现 hash；
- 54 个端点摘要、结构门和 T256 stage gate；
- 74 个三层时间门记录；
- 12 个 S4/D0 动态留出 NPZ、T128→T256 时间节点嵌套检查及有限值审计；
- pass/failure、资源记录和完整 hash ledger；
- 执行记录与 `CURRENT_STATUS.md` 更新。

create-only 结果包：
`results/paper2_m2/identity_2d_v05_t256_v01_20260904/`。

仅当 54 个端点、T256 内全部结构/空间/周期/热点门、74 个三层时间门、源锁、有限值和
hash 门全部通过时，唯一正式标签为 `T256_TIME_CONVERGENCE_PASS_V05`。该标签仍不等于
DCM–FEM identity 通过。

## 7. Implementation boundary

允许新增：

- `src/paper2_m2/protocol_v05.py`；
- `src/paper2_m2/identity_2d_v05.py`；
- `scripts/run_paper2_m2_identity_2d_t256_v05.py`；
- `tests/paper2_m2/test_protocol_v05.py`；
- `tests/paper2_m2/test_identity_2d_v05.py`；
- 指定 create-only 结果包、v05 执行记录并更新 `CURRENT_STATUS.md`。

允许复用 v04/v04.1 的读取、路径归一化、封存与通用数值门逻辑，但不得修改 v01-v04
任何文件。v05 必须显式承载 T256 键、三层时间记录与正式标签，不能通过字符串替换误用
T128 协议。

## 8. Test plan and provenance

测试至少覆盖：

- T256/54 端点协议计数、唯一键和无 C0/C1；
- 一个真实 T256 S4 端点的功率、闭合与 D0 双残差门；
- 74 个空间、54 个周期、2 个热点和 74 个三层时间记录的合成计数；
- 时间门的同向、双小量、反向、变化反增、最细差越界、近零 floor 与非有限值样例；
- T64/T128 源摘要与 hash 锁、校准锁、T128→T256 时间节点嵌套和动态 NPZ 有限值；
- v03/v04/v04.1 已通过测试不退化，旧失败证据不改变。

所有 JSON 禁止 NaN/Inf。v01-v04 关键文件必须在运行前后逐项哈希一致。

## 9. Resources and stop boundary

- CPU 单进程、BLAS/OMP 单线程、固定 DOLFINx CPU 环境、禁网、无 GPU；
- 总预算 `5400 s`、峰值内存 `16 GiB`；
- 不授权 identity gate、GO-ID/MAYBE-ID/NO-GO-ID、重新校准、S5、M2B、三维、整心房、
  真实几何、流体、CFD/FSI、GPU、新求解器或参数扫描。

## 10. Risks and evidence boundary

T256 可能暴露方向翻转、相邻层变化反增、最细差越界或资源超限；任一情况都必须保留为
失败证据，不得通过放宽门限或删改旧层数据修复。即使
`T256_TIME_CONVERGENCE_PASS_V05` 成立，也只说明冻结二维理想模型的预注册数值主量通过
三层时间门；它不证明跨表示身份、生理真实性、EFE 机制、三维/整心房迁移性或流体耦合
有效性。
