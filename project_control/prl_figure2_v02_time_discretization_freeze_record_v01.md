---
freeze_id: FREEZE-PRL-FIG2-V02-TIME-DISCRETIZATION-V01
status: frozen_time_discretization_stage_final
frozen_by: human_final_reviewer
frozen_at: 2026-08-30
decision: project_control/prl_p6_t128_acceptance_and_spatial_tolerance_drafting_authorization_decision_v01.md
package: 02_图表/Figures/Fig2_n1_2_time_adjudication/Fig2_n1_2_time_adjudication_v02_20260827
supersedes_as_current_time_stage: Fig2_n1_2_time_adjudication_v01_20260826
---

# PRL Figure 2 v02 时间离散阶段冻结记录 v01

## 冻结身份

人类终审确认 Figure 2 v02 为 **时间离散阶段 FINAL**。v01 继续作为 P5 严格
失败的历史 FINAL 证据保留；v02 成为当前时间离散阶段的主版本，但不覆盖、删除
或重写 v01。

该冻结不等于论文最终 Figure 2。空间、边界、容差与周期功率闭合证据完成后，
应另建 v03 工作包并再次经过 Figure Decision Gate。

## 冻结主张

本图只支持固定 D0/E0/F150 基线在 T64→T128 下通过 P6 时间离散门。它不支持
空间收敛、容差独立性、材料标定、DCM–FEM 普适优势、EFE 机制或实验一致性。

## 冻结指纹

| 文件 | SHA-256 |
|---|---|
| P6 裁决 summary JSON | `5a039dde50790a787a7b54db13e41b4135d31df2109f5ff25a72e56bd84c4e17` |
| methods/finalization record | `66e4fd19904ccb1988aa761b5784c11cfd0ccbe42d57ca8b6a5b5070b237a2e3` |
| executed Notebook | `6b45cf63bf84a2231d3e78c0a2d9a3b19db99c29dd997e39770f1eb26cc7c387` |
| PNG | `d6ac70c28fc26dc7740ae8ec9145c9b7bb941a82e1e4f11c453631c625c103db` |
| SVG | `2f57dcec2b62854451c3b79dfc7dd30a6c4ce175aa57f2e3f58cce84cd5134a0` |
| T128 provenance correction JSON | `3cdec83ce3ecdf9e9a897e500975802917b5b62482fc89af9867ef53b524797c` |

PNG、SVG、Notebook 和裁决 summary 与终审前哈希一致。冻结时只把 methods 中的
包状态从工作版本改为时间离散阶段最终包，并记录人类决定；未重新计算或修改任何
数值、场数据或图形像素。

## 后续边界

任何 Figure 2 v03 必须新增版本包，不得静默覆盖 v02。当前只批准起草空间与
容差验证合同，没有批准合同执行。
