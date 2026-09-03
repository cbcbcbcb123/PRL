---
execution_id: EXE-PAPER2-M2A-S4-TERMINAL-SPATIAL-DIAGNOSTIC-V01
plan_id: DEC-PAPER2-M2A-S4-TERMINAL-SPATIAL-DIAGNOSTIC-V01
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_at_human_gate
deviation_records:
  - three_pre_result_container_invocations_replaced_the_image_pythonpath_and_failed_at_dolfinx_import_then_corrected_by_preserving_the_image_pythonpath_without_code_model_or_result_change
---

# Paper 2 M2A S4 终止型空间诊断执行记录 v01

## Approved scope

- 授权决定：
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_authorization_decision_v01.md`；
- 持续自主执行边界：
  `project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md`；
- 上游合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`；
- 上游 S3 执行记录：
  `project_control/paper2_m2a_s3_interface_traction_diagnostic_execution_record_v01.md`；
- create-only 结果包：
  `results/paper2_m2/s4_terminal_spatial_diagnostic_v01_20260903/`。

本次只执行 `T64/C1`、`ID-A2/ID-S1`、`DCM/FEM`、`S3=(64,16/层)` 与
`S4=(128,32/层)`。共同观测量固定为 S3 的 64 个界面分段；未修改生产 traction、
1% 门、校准值、模型方程、材料、几何、载荷或求解器。

## Formal outcome

正式终局标签为：`DIAGNOSTIC_PASS`。

全部八项界面指标在原生节点量和 64 段保守共同投影量下均进入 `1%` 空间门；相对历史
S2→S3 的细化方向在两种观测量下均一致，且两种观测量没有产生不同的通过/失败结论。
该标签只表示固定 T64 的 S3→S4 终止型空间诊断通过，不是 M2A 跨表示身份等价通过，
也不把 S3/S4 自动登记为新的生产空间梯度。

## S3/S4 traction results

表中为 S3→S4 空间—时间 traction L2 相对差；门限为 `1%`。

| 工况 | 表示 | 界面 | 原生量 | 64 段共同投影 | 原生方向 | 投影方向 | 判定 |
|---|---|---|---:|---:|---|---|---|
| ID-A2 | DCM | myocardium–ECM | 0.1362% | 0.1628% | 一致 | 一致 | 通过 |
| ID-A2 | DCM | endocardium–ECM | 0.0257% | 0.0162% | 一致 | 一致 | 通过 |
| ID-A2 | FEM | myocardium–ECM | 0.6595% | 0.7269% | 一致 | 一致 | 通过 |
| ID-A2 | FEM | endocardium–ECM | 0.0399% | 0.0186% | 一致 | 一致 | 通过 |
| ID-S1 | DCM | myocardium–ECM | 0.9053% | 0.8461% | 一致 | 一致 | 通过 |
| ID-S1 | DCM | endocardium–ECM | 0.1652% | 0.2207% | 一致 | 一致 | 通过 |
| ID-S1 | FEM | myocardium–ECM | 0.9398% | 0.8800% | 一致 | 一致 | 通过 |
| ID-S1 | FEM | endocardium–ECM | 0.2124% | 0.2725% | 一致 | 一致 | 通过 |

原生量最大相对差为 `0.9397539391%`，共同投影量最大相对差为
`0.8799665418%`。最接近门限的是 `ID-S1/FEM/myocardium–ECM`，因此通过裕量仍需在
后续身份裁决中保守解释。

## Replay and observable boundary

- 同一新包内重新计算了四个 S3 与四个 S4 端点，没有拼接旧数组；
- 四个新 S3 端点摘要逐项重放旧 S3 摘要：每个端点比较 36 个数值路径和 7 个精确
  路径，最大数值相对差均为 `0`；仅跳过非确定性的端点运行时间；
- 旧 S3 包的共同投影使用 S2 的 32 段，本次按新授权使用 S3 的 64 段。因此旧包投影
  绝对值仅用于 S2→S3 方向基线，不作为 64 段绝对值重放门；本次 S3 与 S4 的正式
  比较均由同一新包、同一 64 段定义重算。

这一区分是观测网格的证据边界，不是生产 traction 或投影算法的变更。

## Tests and structural gates

1. 宿主环境定向测试：`6 passed in 0.74 s`；
2. 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器内定向测试：
   `6 passed in 0.58 s`；
3. S3→common-S3 与 S4→common-S3 常牵引制造检查的常场、总力、符号和离散功误差
   均达到机器精度并通过；
4. S4 单端点装配探针：状态自由度 `41729`、矩阵非零项 `496324`、UFL/手工矩阵
   相对误差 `1.03217118583013e-15 < 1e-6`，通过；
5. 八个端点结构门全部通过：最大求解相对残差
   `9.462387135741788e-11`，作用—反作用最大相对误差 `0`，功率账本最大归一化残差
   `3.377665065631151e-10`，最小物理耗散 `3.3629007238518256e-09`，最大周期状态差
   `2.2425646095306227e-16`，最大制造解误差 `1.03217118583013e-15`；
6. 八个 JSON 均可解析且只含有限数值；八个端点 NPZ 数组均为有限数值。

## Resources and runtime deviation

- 固定 DOLFINx 0.11.0 CPU 容器、禁网、单进程、BLAS/OMP 单线程、无 GPU；
- 正式 runner 内部耗时 `90.1334 s < 900 s`；
- 峰值内存 `0.9081 GiB < 16 GiB`；
- S4 装配探针耗时 `5.3783 s`，已包含在正式 runner 总时间中。

正式运行前有三次容器入口调用在导入阶段退出：它们把镜像原有 `PYTHONPATH` 替换为
项目路径，导致 `dolfinx` 不可见。三次均在创建结果目录和进入模型前失败。最终入口改为
在镜像原有 `PYTHONPATH` 前追加 `/workspace/src`，随后重新确认 DOLFINx 版本与容器测试
并正式运行。该修正没有修改 runner、模型、参数、判据或任何既有结果。

## Frozen-core and prohibited-scope verification

三个冻结模块在正式运行前后 SHA-256 完全一致：

- `src/paper2_m2/config.py`：
  `6e5913a250f75cee7dbc1cba01468cf4b71d5f41f2d4c6f6f3f524e8c394380d`；
- `src/paper2_m2/identity_2d.py`：
  `ee76c46ca15ee0ca69a216239c0f8b9c1c1c877ba0238edec245f93f389d32aa`；
- `src/paper2_m2/interface_projection.py`：
  `17dc24b9f4d113faca7c9a3d4494420a4b267dd340940bb6bdb367bbe044ac5e`。

未运行 S5、T128、T256、完整 324 端点矩阵或 M2B；未做三维、整心房、真实几何、
CFD/FSI、新求解器、参数扫描、GPU、M2A GO/MAYBE/NO-GO；未修改生产空间梯度或
生产观测量；未提交、推送或发布。

## Gate-critical hashes

- `assembly_probe.json`：
  `c34682aaea6593d47c5462096743c89c56259ce7f94a8e77c9b90d04945a7434`；
- `diagnostic_summary.json`：
  `1bd83df32e01068eef095e7f85157663e76fbe987dc09685da8b6242ae197834`；
- `endpoint_summaries.json`：
  `05629d0bf498db48a9728eca9537f387084dd4d6f232dd3003f2a7d4c95d25b7`；
- `manifest.json`：
  `471e217c1e5cacf699e78dae8abe4dc21b6cd0fdad1faaf1f66358f66bcb31f7`；
- `preflight_tests.json`：
  `884c015a8e1bc519dca15369eb1473ecf424c0b6c8ca5fafd634b263b2c9b56f`；
- `projection_manufactured_checks.json`：
  `d2f64a9ceafefbea8240a9e3ef7857ac4ee9ab7e7934609b12dbd1abbd1d7b43`；
- `s3_replay.json`：
  `8b97c28f71258b833924e4cf54aa2d5456e2fcd289560f867cacae31d42d5c6a`；
- `structural_gates.json`：
  `1205fbb3412baba257ebd797b6783620869456e9c972a024c8e40befd80cc766`。

八个端点数组均保存在结果包 `endpoints/`，SHA-256 为：

- `ID-A2__DCM__S3.npz`：
  `704f1a5a4f6ce5d019528a67d3868576842809db6e07620ffe024cfb18a205f3`；
- `ID-A2__DCM__S4.npz`：
  `1828eb79f8a911ab251e52cd4af17e4665f8649b75bb5a9bd67b3bbbc178c37e`；
- `ID-A2__FEM__S3.npz`：
  `ad4073e0ea4b479ae05cd9dd30d234a4126acfee06cc230be680cff522a67dd0`；
- `ID-A2__FEM__S4.npz`：
  `5caa662214e59fd000791ecd6efa13a14a10c5727ddb7d00d2cad7ae26eed66c`；
- `ID-S1__DCM__S3.npz`：
  `57c4e2c6b44b2393bf78a7b423ce24aa3b239c48d96ee41093062df6cdc2086a`；
- `ID-S1__DCM__S4.npz`：
  `d51c09fb2d2379d9c977f529d8da14d4810e7ea602aeb5f51e8e4ad8ba2caf3f`；
- `ID-S1__FEM__S3.npz`：
  `e7cc277d612cadf52b40c785963243a5ff99706f9fe44e727d11a6ea8787902f`；
- `ID-S1__FEM__S4.npz`：
  `d5f3dd469b56796b1738be1f69cd81274782fb49e5bf1725a23c4dbde3955e2b`。

runner SHA-256 为
`10ce4c9d94b9ce639e84277fbdf59aa7be6528fb51211638ceccde370571a853`，定向测试文件为
`c3c4c9c4f10a858ce937ef15f0eedfd0c78100a54977e3acbcecdf8038d2691c`。

## Stop and evidence boundary

本执行在 `DIAGNOSTIC_PASS` 后停止于 Human Gate。结果不证明 DCM 与 FEM 在全部指标、
全部网格或连续极限下等价；不证明生理真实性；不授权三维、EFE、流体或器官尺度外推。
下一步只能由新的 Supervisor/Human 决定解释 S4 通过、修订生产空间梯度或终止身份转换
路线，不得由本执行记录自动启动。
