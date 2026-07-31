---
decision_id: DEC-PRL-ROUTE-H-STAGE2-AUTHORIZATION-V01
status: approved
decider: user
decided_at: 2026-07-31T09:14:24+08:00
phase: Phase 2
stage: Stage 2
working_branch: codex/stage2-gates-a-e
related_plan: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
accepted_stage1: DEC-PRL-ROUTE-H-STAGE1-ACCEPTANCE-V01
stage0_contract: CONTRACT-PRL-ROUTE-H-STAGE0-V05
stage1_inspection: INSPECT-PRL-ROUTE-H-STAGE1-V02
---

# Route H Stage 2 Gate A–E 授权决定 v01

## 授权

用户在接受 Stage 1 v02 后明确回复：

> 接受，继续

会话中已即时说明把“继续”解释为对下一阶段 Stage 2 Gate A–E 的明确授权；用户没有撤回
或缩小该授权。因此允许进入 Phase 2 / Stage 2，并严格按以下顺序推进：

1. Gate A：单心肌细胞主动收缩；
2. Gate B：心肌链相位传播；
3. Gate C：心肌–ECM 夹层；
4. Gate D：内皮–ECM 夹层；
5. Gate E：最小耦合组织片。

只有当前 gate 通过，才允许运行下一 gate。阶段内部的普通数值修复、回归测试、版本递增、
冻结、只读检查以及当前工作分支的正常 commit/push 不再逐项请示。

## 授权边界

- 只允许实现和运行 `CONTRACT-PRL-ROUTE-H-STAGE0-V05`、对应冻结 cases、ledger、
  geometry specification 与 verification registry 已定义的机制和用例。
- 主动机制只允许预注册的 preferred-length 路线；不得在同一阶段静默切换为主动应力、
  主动曲率或其他替代路线。
- 参数保持无量纲验证参数；不得进行生理标定或形成生理有效性结论。
- 不授权 turnover、非零 `j_myo`、新增 periodic family、空间加密族或冻结范围外的新机制。
- 不授权 Phase 3、论文图/稿件、release 或任何对外科学结论。
- 不允许删除项目材料、重写 Git 历史或 force push。

## 强制停机条件

出现以下任一情况时，停止当前 gate 及所有下游 gate，并向用户报告：

1. 命中预注册 falsifier 或 gate 验收阈值失败；
2. 继续工作必须改变冻结机制、参数、几何、接触定义、功率账本或证据解释；
3. 需要在多个核心科学路线之间重新选择；
4. 需要扩大研究对象、执行难恢复操作或对外发布。

本授权只解除 Stage 2 Gate A–E 的进入门禁，不预先宣告任何 gate 通过。
