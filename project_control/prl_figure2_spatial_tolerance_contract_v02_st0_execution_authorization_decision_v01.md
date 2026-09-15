---
decision_id: DECISION-PRL-FIG2-SPATIAL-TOLERANCE-V02-ST0-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-01
related_plan: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
related_inspection: project_control/prl_figure2_spatial_tolerance_contract_v02_independent_review_v01.md
authorization: st0_only
next_gate: prl_figure2_spatial_tolerance_st0_human_gate
---

# PRL Figure 2 空间与容差合同 v02：ST0 执行授权

## 人类决定

在人类终审已接受 T128 Human Gate、确认 Figure 2 v02 为时间离散阶段 FINAL，
并批准起草空间与容差验证合同但暂不计算之后，项目提交了合同 v02、独立只读审阅
和单一当前状态索引。人类于 2026-09-01 回复“继续”。结合紧邻的 Human Gate
说明，本决定将其记录为：**批准合同 v02，但只授权执行 ST0**。

## 获准范围

1. 实现并测试 F150 中央域在 F200N 中的 byte-exact 嵌套；
2. 建立 C0/C1 唯一配置入口，并贯穿 worker、父审计与 provenance；
3. 实现并测试共同求积、守恒投影和跨网格映射硬门；
4. 建立与实际 staggered/exponential SLS 更新一致的离散功率账本及制造测试；
5. 执行零载荷或单步 CPU 成本、内存与存储预检，形成诊断图；
6. 记录所有失败并在 ST0 Human Gate 停止。

## 明确未授权

本决定不授权 A1–B4 完整周期、D1/E2/F200N/C1/T128、T256、空间或参数扫描、
N1-2d、N1-3、原 EFE Node 2–4、GPU worker、新外部求解器、双向 FSI、器官级
几何扩展或 Figure 2 v03 冻结。

ST0 的实现和预检结果本身不构成空间收敛、容差独立或联合时间—空间稳健性结论。
