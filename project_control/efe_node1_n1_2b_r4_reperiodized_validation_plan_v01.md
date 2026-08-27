---
plan_id: PLAN-EFE-NODE1-N1-2B-R4-REPERIODIZED-VALIDATION-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b-r4 解析周期化与事务验证计划 v01

## Goal

消除 r3 cycle 4 中主要由 SLS 初始历史造成的慢瞬态，并以两个连续、完全
耦合的事务周期检验 D0/E0/F150、T16 是否达到预登记周期稳态。

## Inputs

- 正式 r3 cycle 4 的 `cycle_states.npz`、`cycle_timeseries.csv` 和
  `cycle_end_checkpoint.npz`；
- 原 SLS 精确更新、本构参数 `mu_ve=eta_ve=0.5`；
- D0/E0/F150、`T=1`、16 steps/cycle、峰值激活 `0.20`；
- r3 已验证的 Picard worker、父进程 oracle 和 create-only 提交 seam；
- FEniCSx/dolfinx v0.11.0 固定运行环境。

## Outputs

1. 由 r3 cycle 4 实际 ECM 几何历史构造的解析周期 `Z`；
2. 通过全部原状态门的 phase 0 机械重平衡检查点；
3. 两个连续验证周期的 32 个事务、34 相位状态、时序和周期摘要；
4. 第一验证周期到第二验证周期的五项预登记周期差；
5. 科研审阅图、执行报告和人类终审请求。

## Implementation Steps

1. 对冻结 cycle 4 几何计算一周期仿射 SLS 映射及其解析固定点，冻结几何
   周期残差要求 `<=1e-12`；
2. 使用 cycle 4 phase 0/末相位几何、解析周期 `Z` 和原接触状态完成零激活
   机械重平衡；
3. 父进程复核 KKT、体积、`J`、gap、两层面面积、`Z` 对称/零迹以及候选
   `Z` 与解析固定点的一致性，通过后才 create-only 提交暖启动；
4. 让事务周期入口接受显式前一周期目录和起始周期编号，同时证明默认 r3
   行为不变；
5. 从接受暖启动运行 cycle 5–6，每步均使用新鲜 worker、父 oracle、解析
   SLS/耗散复核和 create-only 提交；
6. 仅以 cycle 5→6 的四条登记波形及周期末完整 `Z` 应用 `<=1e-3` 门；
7. 生成阶段审阅图并运行相关回归；结果提交人类终审。

## Impacted Files Or Modules

- 扩展 `src/hybrid/efe_step_transaction.py` 的周期暖启动父审计；
- 扩展 `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py` 的显式
  前一周期/起始周期参数，默认 r3 行为保持不变；
- 新增 r4 暖启动父 driver、阶段绘图脚本和对应测试；
- 新增 `project_control` 中的授权、计划、执行和终审记录。

## Test Plan

- 周期暖启动审计对登记通过值接受，并逐项拒绝周期残差、候选 `Z` 差和原
  状态门失败；
- r3 入口默认目标仍为 cycle 3–4，默认前一周期仍为原 baseline cycle 2；
- r4 暖启动源路径和摘要指纹指向正式 r3 v02 cycle 4；
- phase 0 全部状态门通过后才存在正式暖启动检查点；
- cycle 5/6 各 17 相位、16 个提交检查点，32 个 worker PID 唯一；
- 相关 pytest、Ruff、JSON/CSV/NPZ 读取和 PNG 视觉核验通过。

## Risks

- cycle 4 几何只是近周期几何，解析 `Z` 仅为加速初猜，不保证完全耦合周期
  固定点；最终证据仍必须来自两个动态周期；
- phase 0 重平衡可能改变几何，使冻结几何周期态失配；这正是后续两个动态
  周期需要检验的量；
- 32 个新鲜进程会产生约 30–50 分钟墙钟时间；
- 若仍未过周期门，本阶段只能报告受控负结果。

## Acceptance Criteria

暖启动：

- 冻结几何周期残差和正式候选 `Z` 差均 `<=1e-12`；
- KKT `<=1e-5`、体积残差 `<=1e-8`、`min J>=0.5`、
  `min gap>=-1e-12`、两层最小面面积比 `>=0.05`；
- `Z` 对称/零迹残差 `<=1e-12`；
- 全部门通过后才 create-only 提交正式暖启动。

动态验证：

- cycle 5 和 cycle 6 各完成 16 个接受步骤，全部原事务和状态门通过；
- cycle 5→6 的 `axial_shortening`、最大界面牵引、总储能、`Z` 范数波形
  对称归一化 L2 差均 `<=1e-3`；
- cycle 5→6 周期末完整 `Z` 相对差 `<=1e-3`；
- 任一失败则保留为 r4 受控负结果，不声称周期稳定。

## Out Of Scope

- 改变 Picard 算法、迭代上限、材料参数、门限或加载；
- 第三个及以后验证周期；
- T32/T64、D1/E1、F200、参数扫描；
- N1-3、Node 2、实验拟合、论文终稿、Git 与发布。

## Required Memory Updates

只有人类终审接受 r4 后，才能把 T16 周期稳态候选或 r4 受控负结果写入稳定
项目状态。同一任务的实现和自检不构成独立人类终审。

