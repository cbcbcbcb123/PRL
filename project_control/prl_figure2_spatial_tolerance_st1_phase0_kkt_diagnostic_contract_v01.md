---
plan_id: PRL-FIG2-SPATIAL-TOLERANCE-ST1-PHASE0-KKT-DIAGNOSTIC-V01
status: approved
planner: codex_supervisor
approved_by: human_final_reviewer
approved_at: 2026-09-01
executor: codex_current_task
inspector: focused_self_check_only
related_memory_entries: []
---

# PRL Figure 2 ST1：相位 0 KKT 诊断合同 v01

## Goal

在不运行 T64 周期、不改变物理模型和接受门的前提下，判断 E1 空间暖启动 v03
的 KKT 失败是否可由一次额外、配置完全相同的 80-iteration L-BFGS continuation
消除。

## Inputs

- `results/hybrid/prl_figure2_spatial_tolerance_st1_warm_e1_v03_20260901/summary.json`；
- 同目录 `periodic_warm_start_checkpoint.npz`；
- D0/E1/F150、相位 0、activation/pressure/WSS 均为 0；
- 原 `dolfinx/dolfinx:v0.11.0` CPU 后端；
- 冻结 C0 profile 与 KKT 门 `1e-5`。

## Outputs

- 一个 create-only 诊断目录；
- 输入指纹、初末 KKT、优化器状态、体积与几何硬门、精确配置和结论分类；
- 诊断 checkpoint 仅作审计，不自动成为 A1 起点。

## Implementation Steps

1. 校验 v03 状态、目标工况、C0 profile digest 和 checkpoint array digest；
2. 从 v03 variables、周期 SLS `Z` 与 contact multipliers 恢复；
3. 使用与 v03 完全相同的 C0 capture 配置追加一次 80-iteration 相位 0 求解；
4. 按原 KKT、体积、Jacobian、间隙和面积比门裁决；
5. 记录结果后停止，不进入 A1/E2。

## Impacted Files Or Modules

- 新增一个诊断入口脚本；
- 扩展 ST1 entry 的静态合同测试；
- 新增 create-only 诊断结果和执行记录；
- 不修改求解器、C0/C1 profile、暖启动 v01 或事务 engine。

## Test Plan

- 静态测试确认诊断入口固定 E1、相位 0、C0、单次 continuation 和诊断证据边界；
- 运行既有 ST1/ST0/transaction/T128 相关回归测试；
- 在原 FEniCSx CPU 镜像中执行一次真实诊断。

## Risks

- continuation 通过只能证明当前离散系统在追加同算法预算后可达门，不能证明跨网格
  初值无误差；
- continuation 不通过不能单独证明物理不相容，只能说明原算法与本次追加预算仍未
  解决，需要另行批准更深诊断；
- 诊断 checkpoint 若未经新决定直接用作 A1 起点，会破坏入口 provenance。

## Acceptance Criteria

- 配置与 v03/C0 完全一致；
- 没有阈值放宽、算法切换、Newton、新预条件器或 fallback；
- 完整报告初末 KKT 与全部几何硬门；
- 无论结果如何均不启动正式周期，并返回 Human Diagnostic Gate。

## Out Of Scope

E2、A1/B1/A2/B2 周期、A3–B4、T128、T256、GPU、新后端、求解器扫描、参数扫描
和 Figure 2 新冻结均不在本合同内。

## Required Memory Updates

无。只有人类接受诊断结论后，才考虑项目内稳定记录；不写 Codex 长期记忆。
