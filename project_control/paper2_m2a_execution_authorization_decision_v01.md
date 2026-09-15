---
decision_id: DEC-PAPER2-M2A-EXECUTION-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-03
related_plan: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
authorized_scope: m2a_true_2d_identity_conversion_only
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A 执行授权决定 v01

## Decision

人类终审批准执行 M2A：在二维平面应变层状理想域中，只改变心肌表示，比较旧
preferred-length 心肌 DCM 与主动本征应变心肌 FEM。

## Authorized scope

- 执行合同中 `ID-P0/P1/A1/A2/LN/LS/C0/CQ/S1` 九个预注册工况；
- 使用三层嵌套空间路径、`T64/T128/T256`、C0/C1 和周期门；
- 只允许两个校准量：被动切线刚度与一个基准周期总主动功；
- 其余缩短、牵引、相位、能量、耗散、组合载荷和热点均为留出端点；
- 仅使用 CPU 和现有已批准求解器路径；
- 允许在新 `src/paper2_m2`、`tests/paper2_m2`、独立脚本和版本化结果目录内实现；
- 完成或首个硬门失败后停在独立检查与 Human Gate。

## Explicit exclusions

本决定不授权 M2B 三维执行、GPU、CFD、单向/双向 FSI、圆环/椭圆/真实心室、
De–H–Pi_f–Delta_phi 扫描、实验拟合、修改共享核心、覆盖旧结果、Git 提交/推送或发布。

若现有求解器路径不可用、预计资源超过预检预算、需要修改共享核心、需要新增工况或
需要改变阈值，Executor 必须 fail closed 并记录 deviation，不得自行调整。
