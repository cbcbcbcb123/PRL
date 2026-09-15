---
decision_id: DECISION-EFE-NODE1-N1-2C-P0-P2-AUTH-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-26
related_plan: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
related_inspection: human_review_in_codex_task
memory_target: efe_node1_n1_2_lifecycle
---

# EFE Node 1 N1-2c P0–P2 授权决定 v01

人类终审回复“同意，开始”。结合紧邻的精确请求，解释并冻结为：

1. 接受 R5 为 D0/E0/F150、T16 的周期稳态候选；
2. 明确该接受不代表时间、空间、参数域或生物学验证；
3. 批准 N1-2c P0：建立独立时间细化入口、重采样与测试，不修改 R5 正式
   gate-critical 脚本；
4. 批准 P1：以接受的 R5 cycle 8 构造可审计 T32 暖启动；
5. 批准 P2：执行两个 T32 事务周期并生成 T16↔T32 预览和阶段审阅材料；
6. 在 Human Gate T32 停止，不授权 T64、T128、空间细化、参数扫描、N1-2d、
   N1-3、Node 2、GPU worker 或外部求解器；
7. 任一步硬门失败、两个周期未稳态、来源漂移或成本越界时 fail-closed，不在
   本授权内修复后续跑。

本决定使 R5 T16 候选可作为 N1-2c 正式输入，但不把它升级为时间收敛结论。

