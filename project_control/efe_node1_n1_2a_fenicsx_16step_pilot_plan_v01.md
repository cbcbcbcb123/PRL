---
plan_id: PLAN-EFE-NODE1-N1-2A-FENICSX-16STEP-PILOT-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-19
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2a FEniCSx 16-step pilot 计划 v01

## Goal

在候选 FEniCSx ECM 后端上首次走通 D0/E0/F150 完全耦合的一个黏弹性
心搏周期，验证几何平衡、SLS 内变量和时间推进可以在同一路径中连续运行。

## Inputs

- P1 验收决定；
- D0 心肌/内膜离散、E0 ECM 网格、F150 横向足迹；
- `T=1`、峰值激活 `0.20` 的平滑余弦波；
- ECM 参数沿用冻结模型：`mu_ve=0.5`、`eta_ve=0.5`；
- `fenicsx_ufl_ad_serial_v02_lazy_tangent` ECM 后端。

## Outputs

1. 17 个相位（含周期两端）的接受状态、ECM `Z` 与检查点；
2. 周期时序、单周期摘要、失败/中断记录；
3. 起始、上升、峰值、下降和周期末的三层状态图；
4. 激活、缩短、牵引、能量、`J`、KKT、耦合残差与耗散诊断图；
5. 执行报告和人类终审请求。

## Implementation Steps

1. 为周期 runner 增加显式 `--ecm-backend`，把同一后端注入直接捕获、
   状态审计及稀疏精化子进程；
2. 保持参考后端为默认值，运行相关回归与 Ruff；
3. 在固定 D0/E0/F150 上执行 `16-step`、一个 warmup cycle；
4. 每步先用最多 80 次捕获优化；严格 KKT 未通过时才进入最多 20 次稀疏
   Newton 精化；
5. 用每步几何与上一步 `Z` 解析更新 SLS 内变量，最多 8 次固定点耦合；
6. 成功后从 `cycle_states.npz` 与 `cycle_timeseries.csv` 生成阶段诊断图；
7. 封存结果并提交人类终审，不自行启动下一层级。

## Impacted Files Or Modules

- `scripts/run_efe_node1_n1_2_periodic_case_v01.py`；
- N1-2a 阶段绘图脚本；
- 相关 hybrid tests；
- `project_control` 中 N1-2a 的执行与终审记录。

## Test Plan

- 参考后端默认路径保持不变；
- FEniCSx 后端在直接捕获、状态评估和精化子进程中均被显式使用；
- 相关测试通过，修改文件 Ruff 通过；
- JSON/CSV/NPZ 可读取，图像非空且能正常渲染。

## Risks

- 完全耦合固定点可能在激活上升段超过 8 次；
- 当前全系统切线仍由有限差分组装，单步成本可能较高；
- 一个周期可能存在明显残余 `Z`，不能误称周期稳态；
- 首周期起点是无历史零态，起点与终点不应预期重合。

## Acceptance Criteria

每个接受相位必须同时满足：

- normalized KKT `<=1e-5`；
- 心肌/内膜体积残差 `<=1e-8`；
- ECM `min J >=0.5`；
- `min gap >=-1e-12`；
- 两层最小面面积比 `>=0.05`；
- SLS 固定点残差 `<=1e-4`；
- 单步耗散 `>=-1e-14`；
- `Z` 对称与零迹残差 `<=1e-12`；
- 16 个时间步全部完成并输出完整状态。

## Out Of Scope

- 周期稳态声明；
- 16/32/64 时间收敛；
- D1/E1、F200、厚度/容差矩阵；
- PETSc SNES 全系统迁移；
- N1-3、Node 2、实验与论文终稿图。

## Required Memory Updates

pilot 经人类终审后，才可把“完全耦合周期已接通”写入稳定项目状态；本轮
执行不自行接受科学证据。
