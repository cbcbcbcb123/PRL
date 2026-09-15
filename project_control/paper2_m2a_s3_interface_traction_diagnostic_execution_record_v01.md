---
execution_id: EXE-PAPER2-M2A-S3-TRACTION-DIAGNOSTIC-V01
plan_id: DEC-PAPER2-M2A-S3-TRACTION-DIAGNOSTIC-V01
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed
deviation_records:
  - container_pytest_first_invocation_missing_pythonpath_then_corrected_without_code_or_model_change
---

# Paper 2 M2A S3 界面牵引诊断执行记录 v01

## Approved plan reference

- 授权决定：`project_control/paper2_m2a_s3_interface_traction_diagnostic_authorization_decision_v01.md`
- 上位失败：`project_control/paper2_m2a_t64_spatial_failure_and_human_gate_v01.md`
- 原合同：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`
- 结果包：`results/paper2_m2/s3_interface_traction_diagnostic_v01_20260903/`

## Outcome

正式诊断标签：`OBSERVABLE_DEPENDENT`。

共同分段投影没有普遍消除空间误差，因此原 T64 失败不能解释成单纯的节点 traction
观测伪影；但 `ID-S1/FEM/endocardium-ECM` 恰好跨越 1% 判据，节点量为 `0.8788%`
而共同投影量为 `1.1180%`，故裁决确实对观测定义存在一个边界敏感项。按授权，不得
自行替换生产观测量，也不得继续 T128/T256 或跨表示身份判定。

## Frozen projection definition

- 共同网格：S2 的 32 个界面分段；
- 原生 traction：各层节点上的分片线性向量场；
- 投影：在每个共同分段上取原生 P1 traction 的精确积分平均，得到保守 P0 向量；
- 空间—时间 L2：共同分段长度权重与 T64 左端点周期采样；
- S2、S3 使用同一实现和同一共同分段，不做插值调参。

常牵引制造检查在 S2→common-S2 与 S3→common-S2 上均得到：常场误差 `0`、总力误差
`0`、离散界面功误差 `0`，正负分量符号保持。

## S2/S3 results

下表数值均为 T64/C1 空间—时间 traction L2 的 S2→S3 相对差；门限保持 `1%`。

| 工况 | 表示 | 界面 | 原节点量 | 共同投影量 | 方向 | 结论 |
|---|---|---|---:|---:|---|---|
| ID-A2 | DCM | myocardium–ECM | 0.5337% | 0.6335% | 一致 | 两者通过 |
| ID-A2 | DCM | endocardium–ECM | 0.0838% | 0.0453% | 一致 | 两者通过 |
| ID-A2 | FEM | myocardium–ECM | 2.5400% | 2.7993% | 一致 | 两者失败 |
| ID-A2 | FEM | endocardium–ECM | 0.0514% | 0.1842% | 一致 | 两者通过 |
| ID-S1 | DCM | myocardium–ECM | 3.2475% | 3.0155% | 一致 | 两者失败 |
| ID-S1 | DCM | endocardium–ECM | 0.6633% | 0.8840% | 一致 | 两者通过 |
| ID-S1 | FEM | myocardium–ECM | 3.3627% | 3.1288% | 一致 | 两者失败 |
| ID-S1 | FEM | endocardium–ECM | 0.8788% | 1.1180% | 一致 | 观测量依赖 |

所有原生 S2 重算值与原生产失败包中的 S2 值逐值相同，相对重放差为 `0`。从历史
S1→S2 到新 S2→S3 的原生量方向全部一致。

## Tests and checks run

1. 宿主环境投影单元测试：`3 passed`；
2. 固定 DOLFINx 容器内投影单元测试：`3 passed`；
3. 容器 S3 装配探针：状态自由度 `10625`，UFL/手工矩阵相对误差
   `8.447645152316956e-16`；
4. 八个授权端点的求解残差、界面作用—反作用、功率账本、非负耗散、周期状态和
   UFL/手工装配门全部通过；
5. 运行耗时 `19.2393 s < 900 s`，峰值内存 `0.3613 GiB < 16 GiB`；
6. CPU 单进程、容器禁网、无 GPU。

容器内首次 pytest 命令因没有设置 `PYTHONPATH=/workspace/src` 在收集阶段退出；随后只
补充该环境变量重跑，3 项全部通过。该修正没有改变代码、模型、参数或证据数据。

## Files changed

- `src/paper2_m2/interface_projection.py`：保守共同分段投影与制造检查；
- `src/paper2_m2/identity_2d.py`：增加显式授权层级入口，原生产入口与冻结配置不变；
- `tests/paper2_m2/test_interface_projection.py`：守恒、符号、功与非嵌套拒绝测试；
- `scripts/run_paper2_m2a_s3_interface_traction_diagnostic_v01.py`：create-only 诊断入口；
- 本执行记录与 `CURRENT_STATUS.md`。

没有修改原生产结果、1% 门、两项校准值、材料/几何/载荷参数或原冻结配置摘要。

## Outputs and hashes

- `manifest.json`：
  `9b67138bc49dd99779929d39f84e5a8a4393ef2dca2900eea0558eef81fad170`
- `projection_manufactured_checks.json`：
  `96a0490481297b0ccc5cbe95852977b4b3eec48296f13afddb51c7a4e8b4b035`
- `endpoint_summaries.json`：
  `d13a8273af626e3a8ee96b7f6cf841e9d53774dfbc8bf59a993503ab3fe6ebf8`
- `structural_gates.json`：
  `bd1eca3fc046b9a02a0e2db7f0a5d22b60d63e9586ff312d9bf4916f1ff6347e`
- `diagnostic_summary.json`：
  `0e4e8d63ddb296c62289acba665eaa8e042a2d926a264c3b38686655965af74a`

八个端点数组保存在结果包 `endpoints/`，不覆盖原 S2 失败证据。

## Deviations and blockers

- 无科学或授权范围偏差；
- 当前阻塞：FEM 的 A2 myocardium–ECM 以及 DCM/FEM 的 S1 myocardium–ECM 在共同
  投影后仍为 `2.80%/3.02%/3.13%`，尚未进入 1% 渐近带；
- 下一步必须由人类决定：继续更细网格诊断、改变界面离散/观测合同，或停止该身份
  转换路线。本执行记录不提出自动修复，也不授权任何后续计算。

## Evidence boundary

本结果只说明固定 T64 的 S2/S3 traction 空间诊断。它不证明 M2A 身份等价、不改变
原 T64 fail-closed 结论，也不产生 M2B、EFE、三维或流体结论。
