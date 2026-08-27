---
plan_id: PLAN-EFE-NODE1-N1-2B-R3-TRANSACTIONAL-CYCLE-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b-r3 事务性周期重算计划 v01

## Goal

把 r2 已验证的单步事务 seam 接入周期主线，从原 N1-2b 已接受 cycle 2
末态连续重算 cycle 3–4，并用预登记判据判断 D0/E0/F150、T16 的完全耦合
黏弹性系统是否达到极限周期。

## Inputs

- `results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820/`
  `N1_2B_D0_E0_F150_T016/cycle_02/accepted_step_016.npz`；
- 原 cycle 2 `cycle_timeseries.csv`、`cycle_summary.json` 和末态 `Z`；
- r2 的事务摘要、父进程 oracle、create-only 检查点工具；
- D0/E0/F150、`T=1`、16 steps/cycle、峰值激活 `0.20`；
- `mu_ve=eta_ve=0.5`、FEniCSx v0.11.0、未松弛 Picard。

## Outputs

1. 可接受任意周期相位、仍保持 r1a 默认行为的通用事务 worker 接口；
2. r3 父周期 driver、逐步 staging/transaction/accepted 证据和源码指纹；
3. 新 cycle 3、cycle 4 的 17 相位状态、时序、检查点和周期摘要；
4. cycle 2→3 与 cycle 3→4 的五项预登记周期差；
5. 含周期波形、收敛门和三维状态快照的阶段图；
6. 执行报告与下一人类终审请求。

## Implementation Steps

1. 将 r1a 单步 kernel 参数化为 cycle、step、period、steps/cycle 和峰值激活；
   默认参数必须逐项复现原 cycle 3 step 4 行为；
2. 在周期事务上下文中禁用仅服务于 r1a 历史失败比较的派生诊断，同时保留
   输入摘要、逐轮固定点、候选、PID 和源码指纹；
3. 新建 r3 父 driver，从 cycle 2 `accepted_step_016.npz` 建立 cycle 3
   step 0，并依次启动 16 个新鲜 worker；
4. 每步父进程重新计算 KKT、原始 `r_Z`、体积、`J`、gap、两层面面积、
   `Z` 对称/零迹、解析 SLS 更新一致性和非负耗散；
5. 全部门通过后独占创建该步接受检查点，再更新周期账本；任一失败立即写
   根级失败摘要并停止；
6. cycle 3 完成后生成周期时序、状态包和与原 cycle 2 的周期差，再以其
   接受末态同样推进 cycle 4；
7. 对 cycle 3→4 的四条登记波形和周期末 `Z` 应用原 `<=1e-3` 判据；
8. 生成阶段诊断图、运行回归并提交人类终审，不进入更高分辨率。

## Impacted Files Or Modules

- 参数化 `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`；
- 新增 `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py`；
- 必要时扩展 `src/hybrid/efe_step_transaction.py` 和对应测试；
- 新增 r3 阶段绘图脚本；
- `project_control` 中的授权、计划、执行和终审记录。

## Test Plan

- r1a 默认 cycle 3 step 4 的激活、时间步和记录时间不变；
- 任意 step 的激活及激活率与解析周期函数一致；
- 父 oracle 对 SLS 更新不一致、负耗散、摘要漂移和每个既有硬门逐项拒绝；
- create-only 提交不可覆盖，输入摘要在 worker 前后不变；
- 32 个成功 worker PID 在各自父进程生命周期内唯一；
- cycle 3/4 各含 17 个相位、16 个提交检查点和完整 transaction ledger；
- 相关 pytest、Ruff、JSON/CSV/NPZ 读取及 PNG 视觉核验通过。

## Risks

- 32 个新鲜进程会增加启动/JIT 墙钟，但这是隔离隐藏状态的批准代价；
- 任一相位仍可能出现固定点或机械门失败，此时应作为有效负结果停止；
- cycle 4 仍可能未过周期门；这不构成数值错误，但不能声称周期稳定；
- 本地 create-only 不是跨主机或断电级分布式事务。

## Acceptance Criteria

逐步接受：

- worker 成功且加载预期输入，输入摘要前后不变；
- 父进程复核 KKT `<=1e-5`、原始 `r_Z<=1e-4`、体积残差 `<=1e-8`、
  `min J>=0.5`、`min gap>=-1e-12`、两层最小面面积比 `>=0.05`；
- `Z` 对称/零迹残差 `<=1e-12`，候选与父进程解析 SLS 更新一致；
- 单步耗散 `>=-1e-14`；
- 通过后才 create-only 提交，提交摘要等于候选摘要。

周期稳定候选：

- cycle 3 和 cycle 4 各完成 16 个接受步骤，所有状态门通过；
- cycle 3→4 的 `axial_shortening`、最大界面牵引、总储能和 `Z` 范数
  波形对称归一化 L2 差分别 `<=1e-3`；
- cycle 3→4 周期末完整 `Z` 相对差 `<=1e-3`；
- 任一项未过则保留为 r3 受控负结果，不声明周期稳定。

## Out Of Scope

- 自动重试、门限或求解算法调整；
- cycle 5 及以后；
- T32/T64、D1/E1、F200、参数扫描；
- N1-3、Node 2、实验拟合、论文终稿、Git 与发布。

## Required Memory Updates

只有人类终审接受 r3 后，才能把“事务周期 driver 可用”以及可能的 T16 周期
稳定性结论写入稳定项目状态。当前任务自检不构成独立 Inspector 验收。

