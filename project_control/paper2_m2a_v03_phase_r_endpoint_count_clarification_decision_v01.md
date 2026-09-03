---
decision_id: DEC-PAPER2-M2A-V03-PHASE-R-ENDPOINT-COUNT-CLARIFICATION-V01
status: effective_correction_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
clarifies_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md
clarifies_decision: project_control/paper2_m2a_v02_diagnostic_acceptance_and_v03_repair_decision_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A v03 Phase R 端点数量澄清决定 v01

## Correction

v03 已正式撤销 C0/C1，并定义唯一直接解验证级 D0。因此 Phase R 的明确矩阵

`ID-LN × DCM × S2/S3/S4 × T64 × D0`

包含 `1 × 1 × 3 × 1 × 1 = 3` 个唯一端点。

原 v03 合同和验收决定中的“六端点”是从 v02 的 C0/C1 双标签诊断继承而来的文字笔误。
该词组由本决定更正为“三端点”；不得为凑足六个而重复计算相同的 SuperLU 直接解。

## Effect on execution

- Phase R 按 3 个唯一端点执行；
- Phase T64 仍为 `9 × 2 × 3 × 1 = 54` 个端点；
- 离散能量公式、功率门 `1e-8`、闭合门 `1e-10`、D0 双残差门、校准、输出路径、资源
  预算和停止边界均不改变；
- 执行记录将此项记为 `contract_clarification_applied`，不记为科学偏差或执行越界。

本决定是追加澄清，不回写或删除已提交的 v03 合同与验收决定，从而保留完整审计链。
