---
plan_id: PLAN-EFE-NODE1-N1-2B-R5-FINAL-REPERIODIZATION-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b-r5 最后一次解析周期化验证计划 v01

## Goal

以 r4 cycle 6 的高度重复几何历史完成最后一次外层周期化修正，并用 cycle
7–8 判定 D0/E0/F150、T16 的完全耦合周期映射是否达到五项预登记门。

## Inputs

- `results/hybrid/efe_node1_n1_2b_r4_transactional_cycle_v01_20260820/`
  `cycle_06` 的状态、时序和末态检查点；
- r4 已通过的周期暖启动父审计、事务 worker、父 oracle 和提交 seam；
- D0/E0/F150、`T=1`、16 steps/cycle、峰值激活 `0.20`；
- `mu_ve=eta_ve=0.5`、Picard 上限 12、FEniCSx v0.11.0。

## Outputs

1. cycle 6 几何对应的解析周期 `Z` 与 phase 0 接受检查点；
2. cycle 7–8 的 32 个事务、状态、时序和周期摘要；
3. cycle 7→8 的五项周期门；
4. 科研审阅图、执行报告和人类终审请求。

## Implementation Steps

1. 仅参数化既有 r4 暖启动入口的运行标签、首周期和授权路径，默认 r4 行为
   保持不变；
2. 使用 cycle 6 的 17 相位 ECM 几何构造解析周期 `Z`，冻结几何周期残差
   `<=1e-12`；
3. phase 0 重平衡后复核原 KKT、体积、`J`、gap、面面积和 `Z` 结构门，
   通过后才 create-only 提交；
4. 从接受暖启动执行 cycle 7–8，每步继续使用新鲜 worker、父 oracle、SLS/
   耗散一致性和 create-only 提交；
5. 对 cycle 7→8 应用原四条波形和周期末完整 `Z` 的 `<=1e-3` 门；
6. 生成结果图和终审材料。失败即停止，不追加周期或再次暖启动。

## Impacted Files Or Modules

- 参数化 r4 暖启动入口和事务周期入口的 `r5` 标签；
- 对应周期窗口与默认行为测试；
- 新增 r5 结果、审阅图和 `project_control` 记录。

## Test Plan

- `validation_cycle_indices(7)==(7,8)`；
- r3/r4 默认行为和 r4 暖启动默认标签保持不变；
- 暖启动源路径/指纹只指向正式 r4 cycle 6；
- phase 0 全部门通过后才存在正式暖启动；
- cycle 7/8 各 17 相位、16 个提交检查点，32 个 PID 唯一；
- 相关 pytest、Ruff、JSON/CSV/NPZ 和图版本包核验通过。

## Risks

- 完全耦合周期固定点可能不能通过一次外层 Picard 修正达到；
- 敏感相位可能再次接近 KKT 或 `r_Z` 门；
- 若两项 `Z` 门仍失败，必须转向显式周期 shooting，不能继续追阈值。

## Acceptance Criteria

暖启动沿用 r4 全部父门。动态周期要求 32 个事务全部通过；cycle 7→8 的
轴向缩短、最大界面牵引、总储能、`Z` 范数波形和周期末完整 `Z` 均
`<=1e-3`，才形成 N1-2 T16 周期稳态候选。

## Out Of Scope

- 第三验证周期或第三次解析暖启动；
- 算法、门限、材料、加载或网格改变；
- T32/T64、D1/E1、F200、参数扫描、N1-3、Node 2；
- 实验拟合、论文终稿、Git 与发布。

## Required Memory Updates

只有人类终审接受 r5 后，才能记录 T16 周期稳态候选或 r5 失败边界。当前
同一任务的执行、自检和绘图不构成人类终审。

