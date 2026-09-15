---
execution_id: EXE-PAPER2-M2A-V02-T64-POWER-LEDGER-DIAGNOSTIC-V01
plan_id: DEC-PAPER2-M2A-V02-T64-POWER-LEDGER-DIAGNOSTIC-V01
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_with_portability_caveat_at_supervisor_gate
deviation_records:
  - linux_longdouble_step_array_is_readable_and_finite_in_frozen_container_but_not_deserializable_by_the_windows_host_numpy_build
---

# Paper 2 M2A v02 T64 功率账本失败诊断执行记录 v01

## Approved scope

- 诊断授权：
  `project_control/paper2_m2a_v02_t64_power_ledger_failure_diagnostic_authorization_decision_v01.md`；
- 来源失败：
  `project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md`；
- v02 合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md`；
- create-only 结果包：
  `results/paper2_m2/power_ledger_diagnostic_v01_20260903/`。

本阶段只重算 `ID-LN/DCM` 的 S2/S3/S4、T64、C0/C1 六个端点，并执行账本分解、同一
SuperLU 因子的 0/1/2 次残差修正和求和精度对照。没有修改或修复生产实现。

## Formal outcome

正式诊断标签：`DISCRETE_LEDGER_MISMATCH_CONFIRMED`。

失败可精确复现，但代数残差、归一化分母和普通浮点求和都不足以解释主要非闭合。最坏
步的生产账本 residual 几乎全部来自“账本 residual 与 `r_eq·Delta x` 的差”，即离散
能量增量和中点平衡功之间的实现非闭合。该结果定位了诊断 seam，但不包含生产修复。

## Reproduction gate

- S2/C0、S2/C1、S3/C0、S3/C1、S4/C0 对旧失败包逐项重放；除运行时间外，每个可用
  摘要比较 35–38 个数值路径和 10 个精确路径，最大相对差均为 `0`；
- S4/C1 因旧执行在 S4/C0 fail-closed 而没有旧摘要，本次只作为新诊断端点；
- S4/C0 重新得到功率账本最大归一化残差
  `1.465114585633258e-07`，与来源值相对差 `0`，并再次超过 `1e-08` 门；
- 因此反馈环状态为 reproducible，没有触发 `NON_REPRODUCIBLE` 停止。

## H1–H5 assessment

| 假设 | 结论 | 关键证据 |
|---|---|---|
| H1 代数求解缺陷 | 证伪 | 两次修正的线性残差只改善 3.276 倍；账本残差仅改善 1.043 倍且不单调；原始 normwise backward error 已为约 1e-16 |
| H2 C0/C1 不作用于 direct solve | 确认 | 三个空间层的全部状态、账本及输出数组逐值相同且 hash 相同；只改变验收阈值 |
| H3 归一化伪影 | 证伪 | 最坏步尺度为周期中位数的 0.0881，但原始 residual 为 3.651e-12、全周期最大为 9.866e-12，不满足近机器误差判据 |
| H4 离散账本实现失配 | 确认 | 最坏步 `r_eq·Delta x=-4.175e-15`，而账本 residual=`3.651e-12`；二者差 `3.655e-12`，最大差占最大账本 residual 的 99.70% |
| H5 浮点求和限制 | 证伪 | ordinary、pairwise、Kahan、long-double 的最大归一化 residual 均约 1.4651e-7，最佳改善因子约 1.0 |

H2 是求解协议属性，不是正式原因标签：当前 direct solve 不读取 C0/C1 来改变数值解，
只用其 `acceptance_tolerance` 判定。S4 的同一解在 C0 下求解残差门通过，在 C1 下因
`2.5781233298e-08 > 1e-08` 而失败。因此以后不得把 C0/C1 的零 QoI 差异写成独立
代数容差收敛证据。

## Worst-step ledger decomposition

最坏步为 step `42`：

| 项 | 数值 |
|---|---:|
| active work | 0 |
| lumen work | 5.4192183632e-07 |
| support work | -1.2115805740e-05 |
| energy change | -1.1917955420e-05 |
| drag dissipation | 7.8882367838e-08 |
| SLS dissipation | 2.6518549780e-07 |
| raw ledger residual | 3.6510290459e-12 |
| normalization scale | 2.4919750862e-05 |
| normalized residual | 1.4651145856e-07 |
| equilibrium-defect work `r_eq·Delta x` | -4.1752117718e-15 |
| ledger minus defect work | 3.6552042577e-12 |

全周期最大绝对 ledger residual 为 `9.8658409459e-12`，最大绝对 equilibrium-defect
work 为 `5.0550533809e-13`；最大非闭合差为 `9.8367149561e-12`。由离散方程可知，
`ledger residual-r_eq·Delta x` 等于材料中点功与单独计算能量差之间的缺口，因此当前
问题被定位在离散能量增量/账本实现，而不是外力、支撑或黏性项未进入平衡方程。

## Same-factor residual correction

S4 DC 相对残差由 `2.5781e-08` 降至 `7.8702e-09`，harmonic 相对残差由
`1.8500e-08` 降至 `5.7658e-09`；但账本最大归一化 residual 的序列为：

- 0 次：`1.4651145856e-07`；
- 1 次：`4.1305583680e-08`；
- 2 次：`1.4045567074e-07`。

响应没有可见变化：两次修正后主要 QoI 最大相对变化为 `2.4714e-09`，全状态数组相对
变化约 `8.994e-07`。账本残差不随线性残差单调下降，支持 H4、反对 H1。

## Tests and resources

- 宿主定向测试：`4 passed in 0.78 s`；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器：`4 passed in 1.56 s`；
- 正式诊断耗时 `57.3642 s < 900 s`；
- 峰值内存 `0.8260 GiB < 16 GiB`；
- CPU 单进程、BLAS/OMP 单线程、容器禁网、无 GPU；
- 所有 JSON 可解析且只含有限数值；固定 Linux 容器内复核逐步 NPZ 的 19 个数组均为
  有限数值。

所有被声明为只读的现有源码、runner 和测试在运行前后 SHA-256 完全一致。

## Gate-critical hashes

- `baseline_summaries.json`：
  `382d322a08f252b65edb9e9b227b9970e092352d25da1dfd89c8ada5c2d95948`；
- `final_summary.json`：
  `b4387c91c4dac9f1c0c8e5bb186d1d8a047a89c9f4cafc0ee436f8212a69881d`；
- `hash_ledger.json`：
  `9fe225ae7e850b3eced58a08024a0cbd261255fe6261571795852e981637af35`；
- `hypothesis_assessment.json`：
  `74c3a560b37b16905b9cc1923fb15d84c7701645155fc1810ffe24866fa3ac7f`；
- `ledger_decomposition_steps.npz`：
  `d8baa359305683678dd5bd372fb61e2b21cf84d23a2db40513bfe028b497f19a`；
- `ledger_decomposition_summary.json`：
  `a97810df67694c633face564d0906a009faaac589fc6daea52ede11298e1cdab`；
- `manifest.json`：
  `e3fa5a0987e1d1e109eba9e44437f774b2b873e5f1ab0f1e78a39dd9123ccd9b`；
- `replay.json`：
  `e8eff7bdb3a78183c58fded7548bfc296cdf7f5ae686122b0c1e17c77bec2590`；
- `residual_correction.json`：
  `f97c90790c17b22ba2c4b2628e5feb7960958caee197b83bdb122ac7b632e353`；
- `tolerance_label_audit.json`：
  `ecf33ce0b59eb977e14c633f1a552ebc48ebe71b9a0839eac3d0b15c05352980`。

诊断脚本 SHA-256 为
`0fbea032e7f8cf93de4b95b07aa6ab261968b45e571d59f167d5412d30891cee`，测试文件为
`196e29fded4aee2e84521ca25727abecd77a9fe9f03ceeccdc45b5c26d7ae5a3`。

## Deviations and stop boundary

无科学或授权范围偏差。一个交付可移植性 caveat 是：逐步 NPZ 中的 long-double 数组使用
Linux `<f16` 描述符，冻结 Linux 容器可正常读取且 19/19 数组均为有限数值，但当前
Windows 宿主 NumPy 构建不能直接反序列化该 dtype。JSON 摘要与正式标签不受影响；按
create-only 规则没有覆盖或改写该证据包。

没有修改生产源码、生产阈值、校准、求解器或观测量；没有重跑 108 端点、
没有进入 T128/T256、identity gate、M2B、三维、整心房、CFD/FSI、GPU 或参数扫描；
没有提交或推送 Git。

本诊断停止在 Supervisor Gate。任何修复必须另立失败回归测试和最小修复合同；本记录
不授权把一次残差修正作为生产算法，也不授权直接恢复 T64 全矩阵。
