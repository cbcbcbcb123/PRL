---
decision_id: DECISION-EFE-NODE1-N1-2C-T32-ACCEPT-P3-P4-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-26
related_plan: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
related_inspection: project_control/efe_node1_n1_2c_t32_execution_and_review_request_v01.md
memory_target: efe_node1_n1_2_lifecycle
---

# EFE Node 1 N1-2c T32 接受与 P3–P4 授权决定 v01

人类终审回复“批准，继续”。结合紧邻的 Human Gate 建议，解释并冻结为：

1. 接受 N1-2c T32 周期稳态候选；
2. 接受 T16→T32 重采样只用于暖启动、正式 T32 证据来自 64 个重新求解事务的
   证据边界；
3. 接受并冻结 T32 阶段图 v01 为当前 FINAL；
4. 批准 P3：从接受的 T32 cycle 2 构造可审计 T64 暖启动；
5. 批准 P4：执行两个 T64 事务周期，共 128 个顺序 CPU worker；
6. P4 完成后停在 Human Gate T64；本授权不包含 P5 三档时间裁决与正式 Figure 2；
7. 不授权 T128、空间细化、参数扫描、N1-2d、N1-3、Node 2、GPU worker或新
   外部求解器；
8. 任一步硬门失败、两个周期未稳态、来源漂移或成本越界时 fail-closed，不自动
   追加周期、改变门限、执行 P5 或进入 T128。

本决定把 T32 升级为 P3 的正式粗级输入，但不把它升级为时间收敛结论。
