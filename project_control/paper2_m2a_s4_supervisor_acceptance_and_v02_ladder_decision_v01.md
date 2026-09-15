---
decision_id: DEC-PAPER2-M2A-S4-ACCEPT-V02-LADDER-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
related_execution: project_control/paper2_m2a_s4_terminal_spatial_diagnostic_execution_record_v01.md
next_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
---

# Paper 2 M2A S4 验收与 v02 生产空间梯度决定 v01

## 1. Supervisor acceptance

Supervisor 对 S4 结果进行了独立复核并接受正式标签 `DIAGNOSTIC_PASS`：

- 定向测试 `6/6` 通过；
- 8/8 JSON 与 8/8 NPZ 均可解析且只含有限数值；
- gate-critical JSON、runner、测试和三个冻结核心模块的 SHA-256 与执行记录一致；
- S3 摘要逐项重放最大相对差为 `0`；
- 八项原生 traction 的 S3→S4 最大差为 `0.9397539391%`；
- 八项 64 段投影 traction 的最大差为 `0.8799665418%`；
- 两种观测量均 8/8 通过 `1%` 门，细化方向 8/8 一致；
- 正式运行 `90.1334 s < 900 s`、`0.9081 GiB < 16 GiB`，无 GPU；
- `config.py`、`identity_2d.py`、`interface_projection.py` 未改动。

接受附带一个明确边界：最接近阈值的原生指标仅有约 `0.0602` 个百分点裕量，因此
这是生产空间梯度候选证据，不是跨表示身份结论，也不是高精度渐近阶证明。

## 2. Scientific decision

依据 S2→S3 未过门而 S3→S4 通过，批准把 M2A v02 的生产空间梯度登记为：

- `S2=(32, 8/层)`；
- `S3=(64, 16/层)`；
- `S4=(128, 32/层)`。

原生节点/弹簧 traction 继续作为生产指标；共同分段投影只作诊断和稳健性旁证，不替换
生产观测量。`1%` 空间门、`0.5%` C0/C1 门及所有结构、周期和身份阈值保持不变。

两项既有校准值继续逐值冻结，不重新拟合：

- `dcm_passive_scale=2.4532573887517564`；
- `dcm_active_scale=0.8891803904091895`；
- 源配置摘要：`431bf176833b975af26f6ac05810f6956f2d678dbe6da13f8c11e84d817f46f9`。

这避免在观察空间失败后通过重新校准改变比较问题。

## 3. Evidence-boundary update

`ID-A2` 与 `ID-S1` 已用于选择数值空间梯度，因此在 v02 中应标为“参数留出、数值协议
开发压力测试”，不得再称为完全协议盲的留出。其余 `ID-LN/ID-LS/ID-C0/ID-CQ`
未参与 S3/S4 梯度选择，继续作为主要的数值协议留出。尚未计算正式跨表示 identity gate，
因此本决定没有依据 DCM–FEM 身份差来调参或改阈值。

## 4. Next authorized stage

批准按 v02 增量合同从头执行一个独立的 T64 全工况数值门：

- 9 个预注册工况；
- DCM/FEM 两种表示；
- S2/S3/S4 三层生产空间梯度；
- C0/C1 两种容差；
- 共 108 个 T64 端点；
- 只裁决结构、空间、C0/C1、周期与热点数值门，不形成身份 GO/MAYBE/NO-GO。

T64 通过后，Supervisor 可依据持续自主授权另立 T128 阶段决定；T64 失败则 fail-closed，
先定位失败项，不自动放宽阈值或改观测量。

## 5. Git and handoff

S4 验收与本决定形成一个独立、轻量、可审查的阶段快照后，可非强制同步当前远端分支；
原始 NPZ 继续保留在本地证据包，不进入轻量 Git 快照。同步完成后再下发 T64 v02，避免
把诊断证据与下一阶段实现混入同一提交。
