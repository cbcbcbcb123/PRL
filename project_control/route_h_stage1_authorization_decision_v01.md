---
decision_id: DEC-PRL-ROUTE-H-STAGE1-AUTHORIZATION-V01
status: approved
decider: user
decided_at: 2026-07-30T19:52:50+08:00
phase: Phase 1
stage: Stage 1
working_branch: codex/stage1-passive-kernel
related_plan: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
stage0_contract: CONTRACT-PRL-ROUTE-H-STAGE0-V04
stage0_review: INSPECT-PRL-ROUTE-H-STAGE0-V04-V01
---

# Route H Stage 1 授权决定 v01

## 授权

用户在 Stage 0 v04 已冻结且检查状态为 `accepted_with_caveats` 后，明确回复
“批准，继续”，据此批准进入 Phase 1 / Stage 1。

本次授权覆盖：

- 物化并封存 Stage 0 v04 指定的确定性 reference bundle；
- 实现被动 DCM、有限变形黏弹 ECM、动态 steric、固定 material tether；
- 实现细胞—ECM 来源映射的零通量路径、血流载荷、固定 Kelvin–Voigt 支撑和功率账本；
- 建立并运行 Stage 1 被动模块与制造解测试，在原路线内修复失败；
- 形成 Stage 1 执行、测试、冻结和只读检查记录；
- 在 `codex/stage1-passive-kernel` 工作分支提交并阶段性推送 GitHub。

## 明确不授权

- 不启用或验证主动收缩机制；
- 不运行 Stage 2 Gate A–E 的主动或完整 patch trajectory；
- 不进行生理参数标定、turnover、非零 `j_myo`、空间加密族或 periodic image；
- 不修改任何 Stage 0 v04 冻结件；
- 不发布论文图、稿件、release 或对外科学结论；
- 不删除项目材料、不重写 Git 历史、不 force push。

## 阶段内停机条件

仅在以下情况中断并重新请示：

1. 必须改变 Stage 0 v04 的核心科学路线、接触形式、证据解释或冻结参数；
2. 已触发注册 falsifier，继续必须在多个科学方案间选择；
3. 需要扩大数据、研究对象、外部发布或执行难恢复操作；
4. Stage 1 检查完成，需用户决定是否接受并另行授权 Stage 2。

本记录只解除 Stage 1 的执行门禁，不改变 Stage 0 v04 文件内容或 Stage 2 的
`not authorized` 状态。
