---
decision_id: DECISION-PRL-FIG2-SPATIAL-TOLERANCE-ST1-WARM-START-V02-REPAIR-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-01
related_plan: project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_contract_v01.md
related_inspection: project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_execution_and_human_gate_v01.md
memory_target: none
---

# PRL Figure 2 ST1：批准暖启动 v02 修复

## 人类决定

人类终审在收到相位 0 KKT 诊断及其证据边界后回复“批准，继续”。本决定记录为：

1. 接受“原单段 80 次 capture 预算偏紧，但累计两段后仅擦线过门”的诊断；
2. 批准建立空间暖启动 v02 入口；
3. 从 accepted R0 T64 cycle 的原始几何重新构造 E0→E1 映射和目标网格周期 SLS
   状态，不复用诊断 checkpoint；
4. 固定执行两个连续的 80-iteration C0 capture block，并逐 block 记录状态；
5. 保留 KKT 门 `1e-5`，不允许自动第三 block、Newton、fallback、门限放宽或算法
   切换；
6. E1 暖启动通过后，可按既有 ST1 授权进入 A1；A1 任一事务硬门失败即停止，不
   自动进入 B1。

## 未扩大范围

本决定不新增 A1/B1/A2/B2 之外的端点，不授权 A3–B4、T128、T256、GPU、新
求解器、参数扫描或 Figure 2 新冻结。E2 不在 E1 暖启动和 A1 行为确认前提前运行。
