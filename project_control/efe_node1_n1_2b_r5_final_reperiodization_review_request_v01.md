---
review_id: REVIEW-EFE-NODE1-N1-2B-R5-FINAL-REPERIODIZATION-V01
status: pending_human_final_review
requested_at: 2026-08-20
requester: codex_current_task
execution_report: project_control/efe_node1_n1_2b_r5_final_reperiodization_execution_v01.md
reviewer: human_final_reviewer
---

# EFE Node 1 N1-2b-r5 人类终审请求 v01

## Requested decision

请人类终审决定是否：

1. 接受 R5 为严格按授权执行、可复算且有效的两周期事务计算；
2. 接受 D0/E0/F150、T16 已形成 **周期稳态候选**；
3. 明确不把该接受解释为时间、空间或参数域收敛；
4. 批准起草 N1-2c 的 T32 时间细化合同，但在新合同获批前不执行。

## Reviewer evidence

- 五项周期门：cycle 7→8 全部通过，最大值为 `5.9357e-4 < 1e-3`；
- 32/32 个事务通过，worker PID 全部唯一，提交均为 create-only；
- Cycle 8 最小 ECM Jacobian `0.987725`、最小 gap `0.0155228`；
- Cycle 8 最大 KKT `9.4701e-6 < 1e-5`，但裕量较小；
- 回归测试 49/49 通过，审阅图版本包已冻结；
- R5 没有修改物理模型、算法、门限、材料、加载或网格。

## Inspector recommendation

建议接受第 1–3 项，并批准**只起草** N1-2c T32 合同。T32 的合同应：

- 固定 D0/E0/F150 与全部物理参数；
- 只改变时间离散至 32 steps/cycle；
- 从 R5 接受周期态构造可审计的 T32 初态；
- 预登记 T16↔T32 的时间细化误差，不用周期门代替离散误差门；
- 保留 cycle 8 step 4 和 step 11 对应相位的求解器边界诊断；
- 先估算计算成本和失败停止条件，再申请执行批准。

理由：R5 已解决“同一 T16 离散下是否达到周期态”的问题；下一项科学问题应是
“这个周期态是否对时间步足够稳定”。直接开展参数扫描会混淆周期误差、时间离散
误差与参数效应。

## Prohibited interpretation

终审若接受 R5，正式表述只能是：

> D0/E0/F150 模型在 T16 离散下形成满足预登记周期门的稳态候选。

不得表述为“模型已收敛”“Node 1 已完成”“EFE 机制已证实”或“结果可直接用于
Nature Physics 稿件结论”。

## Approval phrase

如同意，可回复：

> 接受 R5，批准起草 N1-2c T32 时间细化合同。

