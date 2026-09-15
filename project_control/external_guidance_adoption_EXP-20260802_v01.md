---
record_id: PRL-EXTERNAL-GUIDANCE-ADOPTION-EXP-20260802-V01
status: active_with_source_gap
recorded_at: 2026-09-09
guidance_id: EXP-20260802-scientific-review-v01
source_original_status: unknown
derived_constraint: project_control/external_scientific_review_constraints_v01.md
---

# EXP-20260802 外部指导采纳与来源记录

## 结论

现有项目记录足以确认 `project_control/external_scientific_review_constraints_v01.md` 自 2026-08-02 起被登记为 `frozen_active`，但不足以确认专家身份、原始文件、来源渠道和逐字原文。本记录只重建项目内部已经发生的采纳状态，不补造外部来源。

## 采纳矩阵

| 指导项 | 处置 | 当前含义 | 执行入口 |
|---|---|---|---|
| 软件、数值、生物学证据分线 | `accept` | 持续适用；任何一条通过不得替代其他证据线 | 当前任务合同与结果记录 |
| 历史 X1-H → X1-K 顺序 | `modify` | 作为对应历史范围的约束保留；后续 Paper 2 执行顺序须服从适用范围内的更新决定 | `CURRENT_STATUS.md` 与当前主线 |
| 未过门禁前限制长耦合、标定和机制主张 | `accept` | 在对应模型和证据范围内持续适用 | 各门禁与失败冻结记录 |
| ECM、传感器、谱系和记忆语义边界 | `accept` | 结论必须保留条件、替代机制和未验证项 | 理论合同、论文主张与审查记录 |
| 改变约束须新建版本并记录授权 | `accept` | 不静默改写历史文件 | 新决定或新约束版本 |
| 专家身份和原始措辞 | `needs_user_decision` | 当前无原件，不能对外声称已核验 | `plan/.../source/README.md` |

## 执行规则

1. 执行者先读取 `plan/INDEX.md` 和该指导包；
2. 再读取 `project_control/CURRENT_STATUS.md` 及当前主线；
3. 对具体任务定位最新适用合同、失败冻结和授权；
4. 如专家指导与最新用户决定在同一适用范围内冲突，停止扩大范围并提交用户裁决；
5. 没有专家原件时，只能引用“项目内已冻结约束”，不得引用不存在的专家姓名或原话。

## 证据状态

- 派生约束文件存在与哈希：`passed`；
- 项目内采纳状态：`passed`；
- 专家原件核验：`unknown`；
- 专家身份核验：`unknown`；
- 本轮科学或数值再验证：`not_run`。
