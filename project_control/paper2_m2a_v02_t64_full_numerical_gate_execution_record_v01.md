---
execution_id: EXE-PAPER2-M2A-V02-T64-FULL-NUMERICAL-GATE-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V02
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_fail_closed_at_supervisor_gate
deviation_records: []
---

# Paper 2 M2A v02 T64 全工况数值门执行记录 v01

## Approved plan reference

- 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md`；
- Supervisor 授权：
  `project_control/paper2_m2a_s4_supervisor_acceptance_and_v02_ladder_decision_v01.md`；
- 持续自主执行边界：
  `project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md`；
- v01 基础合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`；
- create-only 失败结果包：
  `results/paper2_m2/identity_2d_v02_t64_v01_20260903/`。

## Formal outcome

正式标签为：`FAIL_CLOSED_AT_T64_ENDPOINT`。

执行在第 `53/108` 个端点
`ID-LN__DCM__S4__T64__C0` 停止。该端点的功率账本最大归一化残差为
`1.465114585633258e-07`，高于冻结硬门 `1e-08`。按合同，没有继续计算该工况 C1 或
剩余 55 个端点，没有形成 T64 stage gate，也没有进入 T128 或身份裁决。

## Failure localization

失败只发生在该端点的功率账本门：

| 检查 | 数值 | 阈值 | 判定 |
|---|---:|---:|---|
| 求解相对残差 | 2.5781233298e-08 | 1e-07 | 通过 |
| 界面作用—反作用 | 0 | 1e-10 | 通过 |
| 功率账本归一化残差 | 1.4651145856e-07 | 1e-08 | 失败 |
| 最小物理耗散 | 9.7810400913e-10 | >= -1e-12 | 通过 |
| 周期状态差 | 2.1218260890e-16 | 1e-03 | 通过 |

同一 `ID-LN/DCM/C0` 路径上，该残差由 S2 的 `4.3024265918e-10`、S3 的
`5.5071162818e-09` 增至 S4 的 `1.4651145856e-07`。这是清晰的细网格功率账本失配
信号，但本次授权只允许 fail-closed 定位，不能据此自行改变残差定义、阈值、求解容差
或模型。

在失败前完成的 52 个端点中，功率账本最大残差为 `5.5071162817565274e-09`，均低于
硬门。第 53 个端点的其他结构门仍通过，因此当前证据定位为“细网格法向载荷下的功率
账本门失败”，而不是求解器残差、作用—反作用、耗散或周期门失败。

## Calibration and protocol lock

v01 校准直接读取并逐值通过锁定，未重新拟合：

- 配置摘要：
  `431bf176833b975af26f6ac05810f6956f2d678dbe6da13f8c11e84d817f46f9`；
- `dcm_passive_scale=2.4532573887517564`；
- `dcm_active_scale=0.8891803904091895`。

v02 协议摘要为
`86b704cf7be3f408dc8d9353f4a1de4aedc92dce0ed8a9541fcfcb4fc3d9939b`。
生产梯度为 S2/S3/S4，时间仅 T64，生产指标仍为原生节点/弹簧 traction；64 段投影仅为
旁证，没有替换生产指标或参与掩盖本次失败。

## Tests, preflight and resources

1. 宿主回归测试：`19 passed in 3.61 s`；
2. 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器回归：
   `19 passed in 4.36 s`；
3. S3→64、S4→64 共同投影制造检查通过；
4. S4 FEM 装配探针通过：状态自由度 `41729`，UFL/手工矩阵相对误差
   `1.03217118583013e-15 < 1e-06`；
5. 停止时正式 runner 累计耗时 `162.3791 s < 3600 s`，峰值内存
   `0.8066 GiB < 16 GiB`；
6. CPU 单进程、BLAS/OMP 单线程、容器禁网、无 GPU。

失败包含 53 个端点摘要和 53 个逐端点结构门。由于 fail-closed 发生在全部端点完成前，
没有生成 `stage_T64_gate.json`、`finite_value_audit.json` 或 `pass_summary.json`；这三项缺失
是预期停止行为，不得补写成通过结果。已保存两个在停止前合法完成的 A2 S4/C1 动态
留出 NPZ，二者均只含有限数值；其余动态留出没有补算。

## Files added

- `src/paper2_m2/protocol_v02.py`；
- `src/paper2_m2/identity_2d_v02.py`；
- `scripts/run_paper2_m2_identity_2d_t64_v02.py`；
- `tests/paper2_m2/test_protocol_v02.py`；
- `tests/paper2_m2/test_identity_2d_v02.py`；
- create-only 失败结果包、本执行记录和 `CURRENT_STATUS.md` 更新。

没有修改 v01 `config.py`、`identity_2d.py`、`interface_projection.py` 或旧 runner。

## Frozen-core verification

执行前后复核值一致：

- `src/paper2_m2/config.py`：
  `6e5913a250f75cee7dbc1cba01468cf4b71d5f41f2d4c6f6f3f524e8c394380d`；
- `src/paper2_m2/identity_2d.py`：
  `ee76c46ca15ee0ca69a216239c0f8b9c1c1c877ba0238edec245f93f389d32aa`；
- `src/paper2_m2/interface_projection.py`：
  `17dc24b9f4d113faca7c9a3d4494420a4b267dd340940bb6bdb367bbe044ac5e`；
- `scripts/run_paper2_m2_identity_2d_v01.py`：
  `6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4`。

## Gate-critical hashes

- `assembly_probe.json`：
  `8d88119d48c52d7966986581ed2dfab00affc60a9f57e2731eb8a1fe52a178a2`；
- `endpoint_summaries_partial.json`：
  `1d61b503e4a9e6536ae8c329028d517542efe61961123fdc2434fec460bd097b`；
- `failure.json`：
  `e8fd42bde9c6816baed21a3e17b40d25b3160355c1128460ccf517d5149699af`；
- `global_structural_checks.json`：
  `e7441e3eb738440e89047715989b8d40ccd4029d0bebfd8a27dfad2267e27dd2`；
- `hash_ledger.json`：
  `d92ae044dfb9824b2026d841ed6f8a9a57107d7e2ccc03dbff1afa3595a98142`；
- `preflight_tests.json`：
  `a249a3926330eee5d4b71ca54ccc14d12045c6a9de86676a68e6f0cd7e19bb62`；
- `projection_preflight.json`：
  `96d0047931072fe37f4c62a4b178b6b39922500916cfbb10cd3066f1f880d861`；
- `run_manifest.json`：
  `3ad9d8f641ae7c6c989773e6d942ad5e8522a45eca12b0fec9a2dca9e95dac90`；
- `source_calibration_lock.json`：
  `efcb980b6d37cacbe62bf9fa094a5040c7ecd7b8ba9b802455d491cbe7ee652d`；
- `structural_gates_partial.json`：
  `cbf2d15b4307622934dbb19f7b0e0d74846791a141aa5b9d7c51f0a2548e4904`。

两个已保存 NPZ 的 SHA-256 为：

- `ID-A2__DCM__S4__T64__C1.npz`：
  `1828eb79f8a911ab251e52cd4af17e4665f8649b75bb5a9bd67b3bbbc178c37e`；
- `ID-A2__FEM__S4__T64__C1.npz`：
  `5caa662214e59fd000791ecd6efa13a14a10c5727ddb7d00d2cad7ae26eed66c`。

## Deviations and stop boundary

无执行范围偏差；本次停止由预注册硬门触发。未运行端点 54–108，未形成 T64
`T64_NUMERICAL_PASS`，未进入 T128/T256，未计算或发布 GO/MAYBE/NO-GO，未运行
M2B、三维、整心房、真实几何、CFD/FSI、GPU、新求解器或参数扫描；未修改阈值、
观测量或校准；未提交或推送 Git。

执行已停止在 Supervisor Gate。下一步若要区分功率账本离散误差、累计舍入误差或细网格
法向载荷实现问题，必须由 Supervisor 另立只读或最小诊断决定；本记录不授权自动重算、
修复或继续全矩阵。
