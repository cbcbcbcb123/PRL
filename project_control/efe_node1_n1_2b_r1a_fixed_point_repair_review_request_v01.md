---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-R1A-FIXED-POINT-REPAIR-V01
status: approved_by_human_final_reviewer
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r1a_fixed_point_repair_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_r1a_fixed_point_repair_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b-r1a 固定点修复终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 r1a 为有效、可复算的诊断结果；
2. 接受“失败步在冷检查点重启后可解，且新 Picard 与 Aitken 收敛到同一
   固定点”；
3. 不接受“Aitken 修复了失败”，不把 Aitken 提升为生产默认算法；
4. 把历史失败重新归类为待隔离的冷/热执行路径敏感性，不再归类为 Picard
   固定点不可解；
5. 不恢复完整周期 3/4，不接受 N1-2 周期稳态；
6. 批准下一步仅执行 `N1-2b-r1b` 冷/热后端路径敏感性审计。

## Proposed r1b boundary

r1b 只做确定性隔离，不改变模型和科学工况：

- 固定同一个周期 3 step 3 检查点和 step 4 目标；
- 对比全新后端与经历冻结历史调用序列的热后端；
- 对完全相同的输入重复评估 ECM 能量、力、KKT 和机械输出，区分后端状态
  依赖与非线性求解器初值/全局化敏感性；
- 每条关键路径至少重复 3 次，并比较逐轮输入输出差及最终固定点；
- 若确认冷重启可复现且不选择不同固定点，再单独提出一次“失败步事务性
  冷重启”生产策略；
- r1b 完成后再次提交人类终审，仍不直接运行完整周期。

## Why r1b precedes full-cycle continuation

新 Picard 3 次通过，而历史 Picard 12 次失败；这一差异远大于 Aitken 与新
Picard 终态差。若直接恢复周期，数值路径可能再次改变结论，并把执行历史
伪影混入 EFE 黏弹机制。先证明求解器/后端的事务性与可重复性，是继续周期
稳定性论证的最低条件。

## Not requested

- 不请求采用 Aitken 作为默认耦合器；
- 不请求放宽 KKT、`r_Z`、`J`、gap 或周期门；
- 不请求完整周期重算、T32/T64、D1/E1、F200 或参数扫描；
- 不请求 N1-3、Node 2、实验拟合、论文终稿、Git 或发布。

## Exact human gate

请求人类终审明确回复是否接受：

> 接受 r1a 诊断结论，不采用 Aitken；批准 r1b 冷/热后端路径敏感性审计。

在获得明确批准前，r1b 和完整周期均不启动。

## Human decision

人类终审于 2026-08-20 明确回复“同意，开始”，接受本请求中的精确决策门：
接受 r1a 诊断结论、不采用 Aitken，并批准 r1b 冷/热后端路径敏感性审计。
完整周期、T32 和 D1/E1 仍未授权。
