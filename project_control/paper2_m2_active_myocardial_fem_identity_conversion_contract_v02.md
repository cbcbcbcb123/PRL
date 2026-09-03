---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V02
status: approved_under_human_standing_authority
planner: supervisor
approved_by: supervisor_under_human_standing_authority
approved_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
base_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
evidence_decision: project_control/paper2_m2a_s4_supervisor_acceptance_and_v02_ladder_decision_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: t64_full_numerical_gate_only
---

# Paper 2 M2：主动心肌 DCM→FEM 身份转换增量合同 v02

## 1. Contract relation

本文件是 v01 的增量合同。除本文件明确改写的空间梯度、阶段执行方式和证据标签外，
v01 的模型方程、三域身份、端口、九个工况、误差定义、硬门、身份门和禁止范围继续
有效。v01 及其失败结果保持不可覆盖，不改写为通过版本。

## 2. Frozen v02 production protocol

### Spatial ladder

生产空间梯度从 v01 的 S0/S1/S2 改为严格嵌套的：

| 标签 | `nx` | 每层 `ny` | 相对 S2 线性加密 |
|---|---:|---:|---:|
| S2 | 32 | 8 | 1× |
| S3 | 64 | 16 | 2× |
| S4 | 128 | 32 | 4× |

空间门使用最细两层 S3→S4；全部主端点相对差必须 `<=1%`，方向一致，热点不得跨共同
单元异常跳变。热点距离门改用 S4 共同单元宽度 `1/128`。原生节点/弹簧 traction L2
仍是生产指标，64 段共同投影只作为旁证。

### Unchanged protocol

- 时间梯度仍为 `T64→T128→T256`；
- 容差仍为 C0/C1，主端点差 `<=0.5%`；
- 结构、周期、功率、耗散和 identity 阈值完全沿用 v01；
- 心内膜 DCM、ECM SLS FEM、界面、边界条件、载荷和心肌 DCM/FEM 方程不变；
- 只使用既有 `dolfinx/dolfinx:v0.11.0` CPU 路径。

### Calibration freeze

不重新拟合。直接读取 v01 `calibration.json`，要求配置摘要和两个尺度逐值匹配：

- 配置摘要 `431bf176833b975af26f6ac05810f6956f2d678dbe6da13f8c11e84d817f46f9`；
- `dcm_passive_scale=2.4532573887517564`；
- `dcm_active_scale=0.8891803904091895`。

旧 S1=(16,4/层) 仅是冻结校准参考层，不再属于 v02 生产空间梯度。

## 3. Stagewise execution

完整 v02 仍最多包含 324 个端点，但必须按时间层分阶段执行并逐层 fail-closed：

1. T64：108 个端点及完整结构/空间/C0-C1/周期/热点门；
2. T128：仅在 T64 通过并形成新决定后运行；
3. T256：仅在 T128 通过并形成新决定后运行；
4. 时间门和正式 identity gate：仅在三层时间均通过后计算。

当前只授权第 1 步。T64 阶段不得输出跨表示 GO/MAYBE/NO-GO。

## 4. T64 implementation boundary

允许新增：

- `src/paper2_m2/protocol_v02.py`：只冻结 v02 梯度、源校准引用、阶段和门；
- `src/paper2_m2/identity_2d_v02.py`：仅承载 v02 阶段门和可复用编排；
- `scripts/run_paper2_m2_identity_2d_t64_v02.py`；
- `tests/paper2_m2/test_protocol_v02.py` 与必要的 v02 定向测试；
- create-only 结果包
  `results/paper2_m2/identity_2d_v02_t64_v01_20260903/`；
- T64 执行记录和 `CURRENT_STATUS.md` 更新。

不得修改 v01 的 `config.py`、`identity_2d.py`、`interface_projection.py` 或旧 runner；
若新协议无法在只新增 v02 模块的条件下实现，停止并记录偏差。

## 5. T64 gates and outputs

必须输出：

- 不可变 run manifest、源校准和核心模块 hash；
- 108 个端点摘要及逐端点结构门；
- S2/S3/S4 的空间门、C0/C1 门、周期门和 S1 热点门；
- 供后续时间门使用的 S4/C1 动态留出端点数组；
- failure 或 stage summary，所有 JSON 禁止 NaN/Inf；
- gate-critical 文件 SHA-256 和执行记录。

T64 通过条件是全部结构门与全部 T64 数值门通过。任一门失败即停止，不进入 T128。

## 6. Resources and checks

- CPU 单进程、BLAS/OMP 单线程、容器禁网、无 GPU；
- T64 总预算 `3600 s`、峰值内存 `16 GiB`；
- 先运行宿主单元测试、容器单元测试与 S4 装配探针；
- 回归测试至少覆盖 M1、M2 v01 的配置/核心接口及 S4 投影；
- 结束时确认 v01 三个冻结模块 hash 不变。

## 7. Evidence labels

- `ID-A2/ID-S1`：参数留出，但已用于数值梯度开发；
- `ID-LN/ID-LS/ID-C0/ID-CQ`：主要数值协议留出；
- 任何 T64 通过只证明 v02 数值门，不证明 DCM–FEM 身份等价；
- 理想二维结果不证明生理真实性、三维适用性、整心房适用性或 EFE 机制。

## 8. Out of scope for the current stage

T128/T256、正式 identity gate、重新校准、S5、阈值调整、观测量替换、M2B、三维、
整心房、真实几何、流体、CFD/FSI、GPU、新求解器和参数扫描均不在当前 T64 授权内。
