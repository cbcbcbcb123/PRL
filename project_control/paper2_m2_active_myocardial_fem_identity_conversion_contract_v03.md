---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V03
status: approved_under_human_standing_authority
planner: supervisor
approved_by: supervisor_under_human_standing_authority
approved_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
base_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
incremental_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
repair_decision: project_control/paper2_m2a_v02_diagnostic_acceptance_and_v03_repair_decision_v01.md
diagnostic_record: project_control/paper2_m2a_v02_t64_power_ledger_diagnostic_execution_record_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: repair_pilot_then_t64_full_numerical_gate
---

# Paper 2 M2：主动心肌 DCM→FEM 身份转换增量合同 v03

## 1. Contract relation

本文件在 v01/v02 上只改写功率账本离散增量、直接解验证协议和相应端点数量。v02 的
S2/S3/S4 空间梯度、九个工况、两种表示、校准、主观测量、空间门、周期门、身份门和
证据边界继续有效。v01/v02 的失败包不可覆盖，也不得追溯改写为通过。

## 2. Frozen ledger repair

材料能量保持

`E(x,a)=0.5 x^T M x + a h^T x + 0.5 c a^2`。

每个 Crank–Nicolson 步的生产能量增量必须直接计算为

`Delta E_discrete = (M x_mid + h a_mid)^T Delta x
                    + (h^T x_mid + c a_mid) Delta a`。

其中 `x_mid=(x_n+x_{n+1})/2`、`a_mid=(a_n+a_{n+1})/2`。功率账本使用
`Delta E_discrete`，不得使用两个绝对端点能量的浮点相减。端点能量和
`Delta E_endpoint=E_{n+1}-E_n` 只作为审计旁证，并输出
`endpoint_subtraction_gap=Delta E_endpoint-Delta E_discrete`。

生产 residual 仍为主动功、腔侧功、支撑功、材料能量增量、drag 与 SLS 耗散的同一物理
恒等式，不改变任何功项符号、边界条件、矩阵、载荷或阈值。

## 3. Ledger repair gates

除既有功率账本最大归一化 residual `<=1e-8` 外，新增一致性审计：

- 每步重新计算平衡缺陷功 `r_eq dot Delta x`；
- `ledger residual-r_eq dot Delta x` 相对同一步账本尺度的最大值 `<=1e-10`；
- 所有离散能量、功项、residual、scale 与审计数组必须有限；
- 保留旧端点差分账本的失败复现作为回归对照，不得删除或覆盖。

## 4. Direct-solver assurance D0

v03 不再包含 C0/C1 轴。唯一生产级为 `D0=scipy_superlu_direct`，每个非平凡端点同时满足：

- DC 与 harmonic 最大相对残差 `<=1e-7`；
- DC 与 harmonic 最大 normwise backward error `<=1e-12`。

P0/P1 制造工况的相应解析/零解残差按零处理。不得把 C0/C1 改名为 D0、不得人为扰动
解以制造“容差差异”、不得将诊断残差修正并入生产算法。v01/v02 的 C0/C1 零差异只能
引用为 non-operational protocol audit。

## 5. v03 T64 matrix and gates

T64 正式矩阵为 `9 cases × 2 representations × 3 spatial levels × 1 D0 = 54` 个端点。
端点键必须显式含 `D0`。阶段门包括：

- 全部 54 个端点结构门；
- S3→S4 的全部主量 `<=1%`、方向一致与冻结热点门；
- 功率账本、离散闭合、后向误差、周期、耗散、作用—反作用及制造解门；
- S4/D0 的 12 个动态留出数组，供后续时间层使用；
- 不再生成或声明 C0/C1 0.5% 收敛结论。

任一端点失败立即写 create-only failure 和部分摘要，停止。T64 全部通过时只允许输出
`T64_NUMERICAL_PASS_V03`，不得输出 DCM–FEM 的 GO/MAYBE/NO-GO。

## 6. Two-phase execution

### Phase R — repair pilot

仅运行 `ID-LN/DCM`、S2/S3/S4、T64、D0。要求：

1. 状态、traction、shortening、耗散等非账本物理数组与 v02 对应 C0 逐值一致；
2. 旧端点差分账本逐值复现来源失败；
3. 新离散账本和离散闭合门全部通过；
4. S4 的旧失败值保留为回归证据，新值不得通过阈值修改获得；
5. 测试先证明旧 seam 失败，再证明新 seam 通过。

create-only 输出：
`results/paper2_m2/ledger_repair_v03_pilot_v01_20260903/`。

### Phase T64 — full numerical gate

Phase R 全部通过后可在同一授权下自动运行 54 个端点。create-only 输出：
`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`。

## 7. Implementation boundary

允许新增：

- `src/paper2_m2/protocol_v03.py`；
- `src/paper2_m2/identity_2d_v03.py`；
- `scripts/run_paper2_m2a_v03_ledger_repair_pilot_v01.py`；
- `scripts/run_paper2_m2_identity_2d_t64_v03.py`；
- `tests/paper2_m2/test_protocol_v03.py`；
- `tests/paper2_m2/test_identity_2d_v03.py`；
- 两个指定 create-only 结果包、v03 执行记录和 `CURRENT_STATUS.md` 更新。

不得修改 v01/v02 源码、runner、测试或旧结果。若无法通过只新增 v03 模块实现，停止并
记录偏差。

## 8. Calibration and provenance lock

不重新拟合，逐值读取 v01 校准：

- 配置摘要 `431bf176833b975af26f6ac05810f6956f2d678dbe6da13f8c11e84d817f46f9`；
- `dcm_passive_scale=2.4532573887517564`；
- `dcm_active_scale=0.8891803904091895`。

manifest 必须记录 v01/v02/v03 模块、合同、决定、诊断结果和源校准 SHA-256；JSON 禁止
NaN/Inf，结果包需有独立 hash ledger。

## 9. Resources and stop boundary

- CPU 单进程、BLAS/OMP 单线程、固定 DOLFINx CPU 环境、禁网、无 GPU；
- Phase R `900 s/16 GiB`，Phase T64 `3600 s/16 GiB`；
- 宿主与固定环境测试通过后才运行；
- T128/T256、identity gate、重新校准、S5、M2B、三维、整心房、真实几何、流体、
  CFD/FSI、GPU、新求解器和参数扫描均不授权。

## 10. Evidence boundary

v03 旨在恢复离散能量恒等式并建立真实的直接解质量证据。即使 T64 通过，也只证明冻结
理想二维模型的当前数值层；不证明生理真实性、病理机制、三维或整心房可迁移性。
