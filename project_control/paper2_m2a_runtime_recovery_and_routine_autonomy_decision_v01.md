---
decision_id: DEC-PAPER2-M2A-RUNTIME-RECOVERY-AUTONOMY-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-03
related_plan: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
related_failure: project_control/paper2_m2a_preflight_failure_and_human_gate_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A 运行时恢复与常规自主执行决定 v01

## Decision

人类终审批准启动 Docker Desktop，恢复合同指定的
`dolfinx/dolfinx:v0.11.0` CPU 求解路径，并允许 Executor 从 M2A 预检阶段继续。

同时，人类授权项目后续在既有已批准合同和证据边界内，对常规、可逆、非破坏性执行步骤
自动放行，不再逐项请求确认；遇到重大决策时仍须停止并提请人类裁决。

## 当前恢复范围

- 可启动 Docker Desktop Linux engine；
- 仅使用既定 `dolfinx/dolfinx:v0.11.0` CPU 容器；
- 恢复 M2A 预检、轻量装配/计时探针、网格与自由度冻结；
- 资源门通过后，继续既有 M2A 九个预注册工况；
- 可在原 M2A 授权的新目录和版本化结果目录内实施、测试和记录；
- 完成或首个合同硬门失败后，仍停在独立检查与 Human Gate。

## 自动放行的常规事项

- 已批准合同内的只读检查、预检、测试、计时探针和 CPU 计算；
- 合同允许目录内的可追溯实现、修复、测试和版本化结果写入；
- 不改变科学问题、模型身份、校准量、验收阈值和证据边界的工程性处理；
- 失败后的证据保存、偏差记录和 fail-closed 停止。

## 仍需人类明确裁决的重大事项

- 启动 GPU worker；
- 进入 M2B 三维、整心房、真实几何、CFD 或单向/双向 FSI；
- 更换或新增求解器、更新关键运行时、修改共享核心；
- 改变模型身份、科学主张、校准/留出划分、硬门阈值或预注册工况；
- 超出已批准资源包络的大计算或参数海；
- 覆盖/删除/移动既有证据，清理 dirty worktree，Git 提交、推送或发布；
- 任何不可逆、破坏性或会显著扩大项目范围的操作。

本决定不改变 M2A 原合同内容，不授权 M2B，也不授权 GPU。
