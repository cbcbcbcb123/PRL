---
decision_id: DEC-PAPER2-M2A-V06-1-NO-GO-ACCEPT-V07-DIAGNOSTIC-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_execution: project_control/paper2_m2a_v06_1_identity_gate_retry_execution_record_v01.md
accepted_result: results/paper2_m2/identity_gate_v06_v02_20260904/
accepted_decision: NO-GO-ID
next_contract: project_control/paper2_m2_active_myocardial_fem_identity_failure_diagnostic_contract_v07.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v07_read_only_existing_evidence_discrepancy_decomposition_only
---

# Paper 2 M2A v06.1 `NO-GO-ID` Supervisor 验收与 v07 诊断决定 v01

## 1. Supervisor 决定

Supervisor 在人类持续授权范围内接受 v06.1 的正式结论 `NO-GO-ID`。冻结二维
S4/T256/D0 身份门共 45 条正式记录，其中 `35 pass / 4 maybe / 6 no_go`；六个预注册
留出工况中只有 `ID-LS` 全部适用门通过。

该结论意味着当前 DCM 与主动心肌 FEM 不能作为全观测量可互换表示。不得以数值包络、
重新归一化、坐标变换或选择部分通过观测量把它改判为 `GO-ID` 或 `MAYBE-ID`。

同时授权 v07：只读分解既有失配并审计牵引提取源公式，以判别最可能的差异来源。v07
是已知失败后的解释性诊断，不是新的前瞻 identity 检验，不得产生新的身份裁决。

## 2. 独立验收结果

| 检查项 | 独立复核结果 | 结论 |
|---|---:|---|
| T64 EOF 单例兼容 | 18/18 精确条件通过；原文件未修改 | PASS |
| 正式 identity 记录 | 45 条，`35 pass / 4 maybe / 6 no_go` | PASS |
| 分类独立复算 | `NO-GO-ID` | PASS |
| 六个留出工况 | 仅 `ID-LS` 全部门通过 | PASS |
| 关键 NO-GO 与数值包络 | `ID-A2`、`ID-LN`、`ID-S1` 均显著超过包络 | PASS |
| 正式 JSON | 11/11 可解析且全部数值有限 | PASS |
| hash ledger | 10/10 文件集合、字节数与 SHA-256 一致 | PASS |
| 源包只读锁 | T64/T128/T256 运行前后哈希一致 | PASS |
| 独立数组复算 | 12 个 T256 动态档案；冻结投影与指标不一致数 0 | PASS |
| 资源与边界 | CPU 后处理；无 solver、GPU、网络或新端点 | PASS |

关键正式失配为：

- `ID-A2` 心肌–ECM / 心内膜–ECM 共同牵引差为
  `80.4031% / 80.3362%`；
- `ID-LN` 峰值 / 波形缩短差为 `18.3367% / 18.0161%`；
- `ID-S1` 心肌–ECM / 心内膜–ECM 共同牵引差为
  `15.0255% / 25.5128%`。

这些值对应的合并数值变化包络分别远小于 identity 差异，因此不能把 NO-GO 解释为
尚未达到空间或时间收敛。

## 3. v07 授权边界

v07 只允许：

1. 读取冻结 T256 动态留出、T128 数值变化资料、v06.1 正式结果与相关只读源码；
2. 对六个正式留出工况的两条共同界面牵引作幅值、方向、分量、空间与时间模态分解；
3. 审计 DCM/FEM 的牵引提取、符号、单位、测度、界面权重与共同投影代码路径；
4. 对纯主动、纯法向、纯切向与组合载荷作只读传递和叠加残差审计；
5. 在新 create-only 目录输出 JSON、hash ledger 与执行记录；
6. 给出且只给出 v07 合同定义的诊断标签，然后停止在 Supervisor Gate。

资源上限为 CPU 总时间 `600 s`、峰值内存 `8 GiB`。不使用 GPU、网络、Docker、外部
求解器，不重跑任何端点，不生成新 NPZ。

## 4. 明确不授权

本决定不授权：

- 修改 DCM 或 FEM 方程、本构、边界条件、参数、单位、符号或牵引提取实现；
- 拟合比例系数、按工况校准、改变共同投影、替换生产观测量或调整 identity 阈值；
- 把任何诊断性重标度或基变换作为修复并回写正式结果；
- M2B、S5、三维、整心房、真实几何、EFE、实验、流体/CFD/FSI 或参数扫描。

若 v07 指向代码缺陷、表示映射变更或模型结构修订，均属于新的重大决策：必须先形成
候选修复合同并向人类报告，不得在 v07 内实施。

## 5. 证据边界

接受 `NO-GO-ID` 不等于判定 DCM 或 FEM 错误。它只否定冻结理想化二维体系中“两个表示
对全部预注册观测量可直接互换”这一更强命题。v07 的任何诊断标签也只能说明既有差异
最符合哪类机制，不能外推到三维、整心房、生理标定、EFE 疾病机制、实验或流体耦合。
