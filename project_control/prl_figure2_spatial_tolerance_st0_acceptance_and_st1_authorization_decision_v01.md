---
decision_id: DECISION-PRL-FIG2-SPATIAL-TOLERANCE-ST0-ACCEPT-ST1-AUTH-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-01
related_plan: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
related_inspection: project_control/prl_figure2_spatial_tolerance_st0_execution_and_human_gate_review_v01.md
authorization: st1_a1_a2_b1_b2_only
next_gate: prl_figure2_spatial_tolerance_st1_human_gate
---

# PRL Figure 2：接受 ST0 并授权 ST1

## 人类决定

人类终审在收到 ST0 v03 诊断、证据边界和下一门说明后回复“继续执行”。结合紧邻
选项，本决定记录为：

1. 接受 ST0 Human Gate；
2. 接受材料射线表面映射用于当前空间阶段，同时保留 `0.0312 L/0.0281 L`
   几何投影距离为解释 caveat；
3. 仅授权 ST1 的 A1、A2、B1、B2，每个工况最多两个完整 T64 事务周期；
4. 完成 ECM 网格与容差裁决图后停止在 ST1 Human Gate。

## 获准范围

- 构造 D0/E1/F150 与 D0/E2/F150 的可审计空间暖启动；
- 执行 A1=`D0/E1/F150/T64/C0`、B1=`.../C1`；
- 执行 A2=`D0/E2/F150/T64/C0`、B2=`.../C1`；
- 应用合同冻结的硬门、共同求积、容差比较、周期稳定和功率账本；
- 输出 ECM 4/6/8 层与 C0/C1 审阅图及执行记录。

## 明确未授权

不授权 A3、A4、B3、B4、D1、F200N 完整周期、细网格 T128、T256、GPU、新外部
求解器、自动第三周期、阈值回退、参数扫描、N1-3、Figure 2 v03 冻结或 ST2。

任一事务或硬门失败时必须 fail closed，保留失败证据并返回人类门。
