---
deviation_id: DEV-PRL-P6-T128-001
status: contained_and_repaired
recorded_at: 2026-08-27
related_plan: project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md
authorization: project_control/prl_independent_theory_mainline_decision_v01.md
---

# PRL P6 T128 DEV001：宿主环境误启动

## 事件

P1 首次调用由宿主 `F:\python\python.exe` 启动。重采样与 129 相位审计已通过，
但内部暖启动在导入 `basix.ufl` 时返回 `ModuleNotFoundError`，未进入周期求解。

## 影响

- 无 T128 动态 step transaction 被执行；
- 无失败状态被提交为暖启动检查点；
- 模型、参数、网格、门限和已冻结证据均未改变；
- 失败目录 `results/hybrid/prl_p6_t128_warm_start_v01_20260827/` 保留。

## 有界修复

按原合同改用已冻结的 CPU 镜像 `dolfinx/dolfinx:v0.11.0`，新输出使用
`prl_p6_t128_warm_start_v02_20260827`。禁止覆盖或清理 v01，禁止借此改变任何
科学或数值门。
