---
decision_id: DEC-PAPER2-M2A-S3-TRACTION-DIAGNOSTIC-V01
status: approved_under_human_routine_autonomy
decider: supervisor_applying_human_standing_authorization
decided_at: 2026-09-03
related_plan: project_control/paper2_m2a_t64_spatial_failure_and_human_gate_v01.md#6-human-gate-所需决定
related_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A S3 界面牵引诊断授权决定 v01

## Decision

依据人类在
`project_control/paper2_m2a_runtime_recovery_and_routine_autonomy_decision_v01.md`
授予的常规自主执行权限，批准执行 M2A T64 空间失败记录第 6 节提出的最小 S3
诊断。该诊断用于区分“尚未进入渐近区”与“节点 traction 离散量收敛较慢”，不修改
原生产合同，不接受任何跨表示身份结论。

## Authorized diagnostic scope

- 保留 S0/S1/S2、两项校准值、模型参数、1% 空间门和全部结构门不变；
- 新增严格嵌套诊断层 S3=`64 x 16/层`；
- 仅运行 `T64/C1` 的 `ID-A2`、`ID-S1`，心肌 `DCM/FEM` 两种表示；
- 为避免把旧结果与新观测定义混合，S2 与 S3 均在同一新版本结果包内重算；
- 同时输出原节点/弹簧 traction L2 与预先冻结的共同界面分段投影 traction L2；
- 在常牵引制造解上验证投影守恒、符号和离散界面功一致性；
- 仅 CPU、单进程、容器禁网；不使用 GPU；诊断总预算不超过 900 秒和 16 GiB；
- 新代码、测试和结果仅写入已批准的 `src/paper2_m2`、`tests/paper2_m2`、`scripts`
  及 create-only 版本化 `results/paper2_m2` 目录；保留旧失败证据。

## Mandatory stop rules

- S2→S3 任一主 traction 指标仍大于 1%、方向不一致或结构/功率门失败：停止；
- 节点 traction 未过而共同投影 traction 通过：只报告“观测量离散敏感”候选，不得
  自行替换生产指标；
- 两种 traction 均通过：只提出将 S1/S2/S3 重新登记为生产空间梯度的合同修订；
- 不论结果如何，均不得自动运行完整 324 端点、T128/T256 或形成 GO/MAYBE/NO-GO；
- 改 traction 定义、改生产空间梯度、改 1% 阈值或接受 M2A 结论均属于重大科学决定，
  必须返回人类门。

## Required outputs

- create-only S3 诊断结果包及其摘要/hash；
- 投影制造解/界面功测试结果；
- 执行记录，逐项报告 S2/S3、节点量/投影量、两种表示和两个工况；
- 明确的 `DIAGNOSTIC_PASS`、`DIAGNOSTIC_FAIL` 或 `OBSERVABLE_DEPENDENT`，不得写成
  M2A 通过。

本授权不进入 M2B、整心房、真实几何、CFD/FSI、参数扫描、GPU、Git 提交/推送或发布。
