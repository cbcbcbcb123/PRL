---
execution_id: EXE-PAPER2-M2A-V05-T256-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V05
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: blocked
formal_stage_label: none_failure_before_t256_stage_gate
failure_classification: T256_ENDPOINT_RUNTIME_BUDGET_EXCEEDED
deviation_records: []
---

# Paper 2 M2A v05 T256 执行记录 v01

## 1. Approved plan reference

本执行依据：

- v05 合同：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md`；
- Supervisor 验收与 T256 决定：
  `project_control/paper2_m2a_v04_t128_supervisor_acceptance_and_t256_decision_v01.md`；
- 持续授权：`project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md`；
- 冻结 T64 源：`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`；
- 冻结 T128 源：`results/paper2_m2/identity_2d_v04_t128_v02_20260903/`。

授权范围只包括 54 个 T256/D0 端点、T256 内 74/54/2 数值门、74 个
T64/T128/T256 三层时间记录、12 个动态留出和规定审计。任一资源门失败必须立即
fail-closed，不得放宽阈值或重跑占用的 create-only 目录。

## 2. Commands or tools used

- 宿主执行 v03-v05 协议、源锁和路径回归；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器执行 v03/v04/v04.1/v05 全回归及真实
  S4/T64、S4/T128、S4/T256 端点；
- 固定容器启动正式 T256：CPU 单进程、BLAS/OMP 单线程、16 GiB、禁网、无 GPU；
- 使用严格 JSON 解析、SHA-256、字节数和当前文件复算审计部分失败包及冻结输入。

## 3. Files changed

新增：

- `src/paper2_m2/protocol_v05.py`；
- `src/paper2_m2/identity_2d_v05.py`；
- `scripts/run_paper2_m2_identity_2d_t256_v05.py`；
- `tests/paper2_m2/test_protocol_v05.py`；
- `tests/paper2_m2/test_identity_2d_v05.py`；
- create-only 失败包
  `results/paper2_m2/identity_2d_v05_t256_v01_20260904/`；
- 本执行记录。

按合同更新 `project_control/CURRENT_STATUS.md`。未修改 v01-v04 文件、首次 v04 失败包、
T64/T128 成功包或工作树中 7 项既有无关 tracked 修改。未执行 Git add/commit/push。

## 4. Tests or checks run

- v05 协议和 T64/T128 源锁：`2 passed in 3.92 s`；
- v05 三层时间门合成规则：`9 passed, 2 deselected in 3.58 s`；
- 宿主 v03-v05 协议、v04.1 路径回归：`10 passed in 5.09 s`；
- 固定 DOLFINx CPU 容器完整回归：`26 passed in 123.99 s`；
- 真实 T256/S4/D0 定向测试通过功率账本、离散闭合、相对残差、后向误差和有限值门；
- Python 语法编译与 `git diff --check` 通过；
- 正式失败包 12 个 JSON 均可解析且数值有限，hash ledger 11/11 条目 SHA-256 与字节数
  一致；
- 18 个部分端点键全部为 `T256/D0`，18/18 科学结构门通过；
- manifest 锁定的 80 个 v01-v04/T64/T128 只读文件当前 SHA-256 与运行前值一致；
- v05 的 5 个实现/测试文件当前 SHA-256 与 manifest 一致。

## 5. Deviations

无科学、实现或范围偏差。正式运行按冻结的 v03/v04 单端点运行时间门
`30.0 s` 检查资源；没有在失败后放宽门限、改变模型、换求解器或继续端点。

## 6. Blockers

正式运行在第 18 个端点 `ID-A1__FEM__S4__T256__D0` 完成后触发资源门：

- 单端点运行时间：`30.38510538799892 s`；
- 冻结单端点预算：`30.0 s`；
- 超出：`0.38510538799892 s`，约 `1.284%`；
- 当时总耗时：`148.80722830200102 s < 5400 s`；
- 当时峰值内存：`1.1217727661132812 GiB < 16 GiB`。

该端点的全部科学结构门通过：相对残差 `3.122497222609623e-11`、后向误差
`2.4755197436675512e-17`、功率账本 residual `1.1990711241050467e-11`、离散闭合
`2.743376042460784e-15`，均低于合同阈值。失败分类因此是
`T256_ENDPOINT_RUNTIME_BUDGET_EXCEEDED`，不是力学、账本、周期或求解器失败。

按 fail-closed 规则，第 19 个端点及以后未运行。create-only 结果目录已被失败证据占用；
任何重试都需要新的 Supervisor 决定和新结果路径。

## 7. Outputs produced

失败包：`results/paper2_m2/identity_2d_v05_t256_v01_20260904/`。

包内保留 18 个端点摘要、18 个结构门、T64/T128/校准源锁、运行 manifest、装配与投影
预检、failure 和 hash ledger。由于失败发生在首个动态留出工况 `ID-A2` 之前，未生成
动态 NPZ；也未计算 T256 空间/周期/热点汇总门或三层时间门。

关键 SHA-256：

- `failure.json`：
  `c98eb9c2af4e1412449c453acce938c86000bea8c719bbfdb41015df2242b32f`；
- `endpoint_summaries_partial.json`：
  `56116df09b677f2447aee95fb724323c95d6b111545b9744970b3c8645c81cbc`；
- `structural_gates_partial.json`：
  `01d0ac1b278f9f9b172358a09e28fe995adf8c1c31fbdf626f85f0e8fbabf3ee`；
- `run_manifest.json`：
  `d7d3b72bdd73f8f5d5abe4f509f79af7e586a2bb5f44cc9ae5007d3ec888352e`；
- `hash_ledger.json`：
  `73b11028032d0654ca7c841d03b25abdf30f7f41ffd5b6e3f1ed38b06e4eebf1`。

v05 实现与测试 SHA-256：

- `protocol_v05.py`：
  `c133c834c5559104e87b4c84eb639256401400409b92ea453d8332759c07b97b`；
- `identity_2d_v05.py`：
  `1f06242f89b231b61ca73d31097cd35eca700f1fd6d4f36ca6c7f537ea1d0be7`；
- T256 runner：
  `2fd2fda0e0d7999b786e9d372a9dcd9353e48ab4819cd390b43f097681e0b039`；
- `test_protocol_v05.py`：
  `8694cd7d316b3e0a751656558fd187abf4e35ef606eb54ee643b43f91cf6cf28`；
- `test_identity_2d_v05.py`：
  `4c4459fe1769f4dc5cc9fb220329bad77c6cb2df3b3ffe6b9f0051462628de48`。

## 8. Evidence boundary and stop state

本包只证明 v05 源锁、测试与前 18 个 T256 端点的科学结构门通过，并记录一次近阈值的
端点资源门失败。它不包含完整 T256 数值阶段、74 个三层时间记录或时间收敛结论，不能
输出 `T256_TIME_CONVERGENCE_PASS_V05`，也不支持 DCM-FEM identity。

执行已停止在 Supervisor Gate。未运行 identity gate、M2B、S5、三维、整心房、真实
几何、流体/CFD/FSI、GPU、新求解器或参数扫描。停止态测试与正式 Docker 容器均保留，
未执行删除。
