---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2A-16STEP-PILOT-V01
status: approved_by_human_final_reviewer
requested_at: 2026-08-19
related_plan: project_control/efe_node1_n1_2a_fenicsx_16step_pilot_plan_v01.md
related_execution: project_control/efe_node1_n1_2a_fenicsx_16step_pilot_execution_v01.md
formal_n1_2_evidence: n1_2a_single_cycle_mainline_accepted
---

# EFE Node 1 N1-2a 16-step pilot 终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 N1-2a “完全耦合单周期主线已接通”的技术结论；
2. 接受残差单调保护修复，以及外层耦合上限 `8 -> 12` 的工程偏差；
3. 明确不接受本结果为周期稳态、16/32/64 时间收敛或 D0/D1、E0/E1
   空间收敛证据；
4. 保留 v01 失败、modified Newton、高捕获和谱残差探针；
5. 批准下一步仅执行 `N1-2b`：
   - 用本次完整 T16 几何构造冻结几何下解析周期 `Z` warm start；
   - 把 warm-start 工具接入显式 FEniCSx seam 和残差保护；
   - 从 warm start 连续运行至少两个完全耦合 T16 周期；
   - 只有相邻两周期四个登记波形和周期末 `Z` 均满足归一化
     `L2 <=1e-3`，才提交周期稳定候选；
   - 若 4 个验证周期内仍不稳定，保留失败并返回终审，不自行扩大周期数；
   - 输出跨周期波形叠加和滞回诊断图。

## Not requested

- 不请求立即启动 T32/T64；
- 不请求 D1/E1、F200 或厚度/容差矩阵；
- 不请求 N1-3、Node 2、实验拟合、论文终稿、Git 或发布；
- 不请求删除任何容器、失败目录或探针结果。

## Human gate

人类终审于 2026-08-20 明确回复“批准，继续”，接受本请求中上一轮提出的
精确决策门：“接受 N1-2a，并批准 N1-2b 周期稳态验证”。接受与授权记录见
`project_control/efe_node1_n1_2a_acceptance_and_n1_2b_authorization_decision_v01.md`。

T32 和 D1/E1 仍未授权。
