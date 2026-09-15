---
execution_id: EXE-PAPER2-M2A-V03-LEDGER-REPAIR-T64-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V03
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_at_supervisor_gate
formal_stage_label: T64_NUMERICAL_PASS_V03
contract_clarification_applied: true
scientific_or_scope_deviations: none
---

# Paper 2 M2A v03 离散账本修复与 T64 执行记录 v01

## 1. Scope and clarification

本执行依据：

- `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md`；
- `project_control/paper2_m2a_v02_diagnostic_acceptance_and_v03_repair_decision_v01.md`；
- `project_control/paper2_m2a_v03_phase_r_endpoint_count_clarification_decision_v01.md`。

Phase R 按正式澄清后的明确矩阵
`ID-LN × DCM × S2/S3/S4 × T64 × D0` 执行 3 个唯一端点。原“六端点”为撤销 C0/C1
后未同步清理的文字笔误；本次记为 `contract_clarification_applied`，不是科学或执行偏差。
Phase T64 保持 `9 × 2 × 3 × 1 = 54` 个端点。

v01/v02 源码、runner、测试和旧结果全部只读。没有修改载荷、矩阵、功项符号、校准、
阈值或直接求解器，也没有引入残差修正。

## 2. Repair and regression seam

新增 v03 层只改变生产账本的材料能量增量。冻结材料能量

`E(x,a)=0.5 x^T M x + a h^T x + 0.5 c a^2`

不变；每步使用精确的二次—双线性中点增量

`Delta E = (M x_mid + h a_mid) dot Delta x
           + (h dot x_mid + c a_mid) Delta a`。

端点绝对能量仍保留为旁证，并序列化
`endpoint_subtraction_gap=Delta E_endpoint-Delta E_discrete`。生产 residual 使用精确离散
增量；逐步另算 `r_eq dot Delta x` 并核对二者差。

回归测试在真实 `ID-LN/DCM/S4/T64` 端点同时断言：

- 旧端点相减账本精确复现 `1.465114585633258e-07 > 1e-08`；
- v03 非账本物理数组与旧路径逐值一致；
- 新账本通过 `1e-08`，且 `ledger residual-r_eq dot Delta x` 相对尺度通过 `1e-10`；
- D0 只使用原 SuperLU direct 解，不执行残差修正。

## 3. Tests

- 宿主可运行的 v02/v03 协议测试：`5 passed in 0.64 s`；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 环境的 v02+v03 回归：
  `11 passed in 31.23 s`；
- v03 定向测试在正式执行前为 `5 passed in 33.78 s`；
- Python 语法编译和 `git diff --check` 通过。

固定镜像必须通过 login shell 激活其 DOLFINx Python 路径；最初两次直接调用 Python 的
容器预检未加载 `dolfinx`，未产生科学结果。正式测试与计算均在正确的冻结环境中执行。

## 4. Phase R result

正式标签：`LEDGER_REPAIR_PILOT_PASS_V03`。

- 3/3 唯一端点通过；
- S4 旧失败来源值与回放值均为 `1.465114585633258e-07`，逐值相同；
- 三个端点的新账本最大归一化 residual 为 `3.952820919598728e-09`；
- 最大离散闭合相对误差为 `1.985680215833659e-14`；
- 最大端点相减缺口为 `9.836716537885495e-12`；
- 非账本状态、traction、shortening 和耗散与 v02 C0 路径逐值一致；
- 运行 `40.1788 s < 900 s`，峰值内存 `0.6987 GiB < 16 GiB`。

Phase R create-only 包：
`results/paper2_m2/ledger_repair_v03_pilot_v01_20260903/`。

## 5. Phase T64 result

正式阶段标签：`T64_NUMERICAL_PASS_V03`。

- 54/54 端点结构门通过；
- 74/74 个空间主量门通过；
- 54/54 个周期门通过；
- 2/2 个热点门通过；
- 最大 S3→S4 相对差为 `0.00939753939133803 < 0.01`，出现在
  `ID-S1/FEM/myocardium_ecm_traction_l2`；
- 最大 D0 相对方程残差为 `2.9681468104030423e-08 < 1e-07`，出现在
  `ID-LN/FEM/S4`；
- 最大 normwise backward error 为 `1.0172675692304304e-15 < 1e-12`，出现在
  `ID-CQ/FEM/S3`；
- 最大功率账本归一化 residual 为 `4.5625235815361454e-09 < 1e-08`，出现在
  `ID-LN/FEM/S4`；
- 最大离散闭合相对误差为 `2.30777539556273e-14 < 1e-10`，出现在
  `ID-LN/FEM/S3`；
- 最大端点相减缺口仍为 `9.836716537885495e-12`，出现在旧失败端点
  `ID-LN/DCM/S4`；
- 12 个 S4/D0 动态留出 NPZ 已生成且全部有限；共同投影 sidecar 与原生门没有结论冲突；
- 运行 `466.7943 s < 3600 s`，峰值内存 `0.8461 GiB < 16 GiB`。

Phase T64 create-only 包：
`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`。

## 6. Integrity and hashes

两个结果包共 22 个 JSON 均可严格解析，15 个 NPZ 的全部数组均为有限值；两个包的
hash ledger 已逐项复算通过。v01/v02 只读输入的运行前后 SHA-256 完全一致。

关键结果哈希：

- Phase R `pass_summary.json`：
  `32698642f12794bf04f3cb9fe47642669b75b3001e373341e0195610bb9d02da`；
- Phase R `hash_ledger.json`：
  `eeb9dfa83c3eaf42bfedc842c58caa38249d37b98ca6c9fe7e9836d91df98cf3`；
- T64 `pass_summary.json`：
  `753f4b320381ea62b82f139ad2913943dca081bb1e6d7ac3dab9d93084eb9ff7`；
- T64 `stage_T64_gate.json`：
  `b2859aba4d25bb6e75744946e9393436bbca47497b6b2f82b99aad5eea91f6fb`；
- T64 `hash_ledger.json`：
  `9701c68ee97c3f370ab8533ee0b2b14241a02fc4e1ba75425135183d1cf0b4b2`。

新增实现与测试 SHA-256：

- `protocol_v03.py`：
  `37bf794a2e77313ff8d3c43f2b2cebf7469f96b57f3a32ffb61bf54917105924`；
- `identity_2d_v03.py`：
  `932eed14574a0577703d0a884365adb2442b341c053b0716d598985c773ee35e`；
- Phase R runner：
  `3a6c474228bdec13585c44bb60200b7d9132fac964bb0dabb1327f06b033f0e7`；
- T64 runner：
  `89d49b29235a1c0a42b82f968fe8144c9695bef2ab079d99bfeda9a0a379c17c`；
- v03 protocol test：
  `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`；
- v03 identity test：
  `85aa2eb8b9ee76ef2e56e17bdcd472a6692c9f8d245789772da40a5560f4d216`。

## 7. Resource and cleanup record

正式计算均为 CPU 单进程、BLAS/OMP 单线程、禁网、无 GPU。未创建 `[DEBUG-...]` 临时
日志。为遵守“删除需另行确认”，本次产生的停止态 Docker 测试/执行容器未删除，作为
后续可清理候选保留；没有在项目目录外新建普通文件或文件夹。

## 8. Stop boundary and evidence boundary

执行已停在 Supervisor Gate。没有运行 T128/T256、identity gate、M2B、三维、整心房、
真实几何、CFD/FSI、GPU、新求解器或参数扫描，也没有执行 Git commit/push。

`T64_NUMERICAL_PASS_V03` 只证明冻结理想二维模型在当前空间梯度、直接解质量和离散账本
门下获得数值可信度；它不是 DCM–FEM identity 结论，不证明生理真实性、EFE 机制或向
三维/整心房/流体的可迁移性。
