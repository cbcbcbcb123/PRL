---
decision_id: DECISION-EFE-NODE1-N1-2A-ACCEPTANCE-N1-2B-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_cycle_stability_plan_v01.md
related_inspection: project_control/efe_node1_n1_2a_fenicsx_16step_pilot_review_request_v01.md
memory_target: project_control/efe_node1_n1_2_execution_v01.md
---

# EFE Node 1 N1-2a 验收及 N1-2b 授权决定 v01

## Decision

人类终审在收到“接受 N1-2a，并批准 N1-2b 周期稳态验证”的精确决策请求后，
于 2026-08-20 明确回复“批准，继续”。据此：

1. 接受 N1-2a 已走通 D0/E0/F150、T16、完全耦合黏弹性单周期主线；
2. 接受残差单调保护与最大耦合迭代 `8 -> 12` 两项已披露工程偏差；
3. 批准执行 N1-2b：解析周期 `Z` 暖启动及最多 4 个连续完全耦合 T16
   验证周期；
4. 只在相邻两周期四条登记波形及周期末 `Z` 相对差均 `<=1e-3` 时，提交
   周期稳定候选；
5. 若 4 个验证周期内仍未通过，保留负结果并返回人类终审，不自行延长。

## Evidence boundary

N1-2a 的接受只支持“单周期动态耦合主线已接通”。本决定不预先接受 N1-2b
结果，也不构成时间或空间收敛、EFE 参数效应或疾病机制证据。

## Boundary

不授权 T32/T64、D1/E1、F200、N1-3、Node 2、实验拟合、论文终稿、Git
发布或清理历史容器与失败结果。
