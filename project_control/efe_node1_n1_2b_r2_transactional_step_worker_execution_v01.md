---
execution_id: EXEC-EFE-NODE1-N1-2B-R2-TRANSACTIONAL-STEP-WORKER-V01
plan_id: PLAN-EFE-NODE1-N1-2B-R2-TRANSACTIONAL-STEP-WORKER-V01
executor: codex_current_task
started_at: 2026-08-20T09:45:00+08:00
completed_at: 2026-08-20T11:28:00+08:00
status: completed_transactional_step_pilot_pending_human_review
deviation_records: []
---

# EFE Node 1 N1-2b-r2 事务性 time-step worker 执行报告 v01

## Approved scope

按人类终审批复的
`project_control/efe_node1_n1_2b_r2_transactional_step_worker_plan_v01.md` 执行。
输入固定为周期 3 `accepted_step_003.npz`，目标固定为 step 4、激活
`0.10`、`dt=1/16`、D0/E0/F150、未松弛 Picard 和原有全部硬门。本阶段
只执行 3 次成功单步事务和 1 次失败负控；未恢复完整周期。

## Outcome

r2 已把完全耦合时间步实现并验证为显式的“计算候选—父进程复核—提交”
事务边界：

1. 3 个不同 PID 的全新 worker 均从同一冻结输入启动，均在第 3 次外层
   Picard 迭代通过；
2. 三个候选的变量、完整 ECM 内变量 `Z` 和接触乘子逐元素完全相同，并与
   r1b 冻结参考终态逐元素完全相同；
3. 父进程没有信任 worker 的单一 `passed` 标签，而是重新装配并复核 KKT、
   原始 `r_Z`、体积、ECM `J`、gap、两层面面积和 `Z` 结构门；
4. 只有父进程全部复核通过后才以 create-only 方式创建
   `accepted_step_004.npz`；候选与提交检查点的数组摘要完全一致；
5. 对每个成功事务再次提交同一目标路径均被拒绝，证明既有接受状态不会被
   覆盖；
6. 第 4 个全新 worker 被限制为一次外层迭代且禁用回退，按预期非零退出；
   staging 候选被保留，但没有生成接受检查点，输入摘要前后不变。

根级状态为 `passed_three_commits_and_failure_rollback`。这说明局部事务 seam
满足批准合同；它尚不是完整周期稳态证据。

## Successful transactions

| 重复 | worker PID | 墙钟时间 / s | 最终原始 `r_Z` | 父进程 KKT | 与 r1b / commit |
|---:|---:|---:|---:|---:|---|
| 1 | 7 | `74.8321` | `5.245516e-5` | `4.435545e-8` | 逐元素相同 |
| 2 | 39 | `69.8864` | `5.245516e-5` | `4.435545e-8` | 逐元素相同 |
| 3 | 51 | `70.3998` | `5.245516e-5` | `4.435545e-8` | 逐元素相同 |

三个父进程 oracle 还共同得到：

- 体积约束残差 `0`；
- `min J = 0.9930518339`；
- `min gap = 0.0268578542`；
- 心肌/内膜最小面面积比分别为 `0.9353173263` 和 `0.9982126802`；
- `Z` 对称残差 `0`，迹残差 `3.469447e-18`。

全部值通过预登记硬门，输入数组摘要保持为
`791adad054a7d47ae2eb9793bf7d836517e0d68a19de4c8b46c0a0b9704b262a`；
三个候选、r1b 参考和三个提交态的摘要共同为
`66c2f4140760a2c419ce944c07f55cd20afe544972e6b4c217dee18dcac683fc`。

## Controlled failure transaction

失败负控 worker PID 为 63，返回码为 1，墙钟 `28.4267 s`。第一次外层迭代
的原始 `r_Z=4.736095e-3`、KKT `7.341618e-3`，未达到合同门，因此：

- `worker_staging/final_candidate_checkpoint.npz` 被保留用于诊断；
- `failure_control/accepted_step_004.npz` 不存在；
- 输入摘要在 worker 前后完全相同；
- 负控被根级父进程登记为正确拒绝，而不是被误记为科学成功。

## Implementation

- `src/hybrid/efe_step_transaction.py`：稳定数组摘要、父进程候选门审计、内存
  NPZ 序列化和 create-only 检查点提交；
- `tests/hybrid/test_efe_step_transaction.py`：摘要、非有限输入、序列化和逐门
  拒绝测试；
- `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`：增加显式
  `1..12` 外层上限、仅用于负控的禁用回退、PID 和 gate-critical 源码指纹；
- `scripts/run_efe_node1_n1_2b_r2_transactional_step_pilot_v01.py`：三个成功
  事务、父进程 FEniCSx oracle、独占提交和失败负控；
- `scripts/plot_efe_node1_n1_2b_r2_transactional_step_v01.py`：派生摘要、
  四面板阶段诊断图和图证据清单。

## Runtime, tests and checks

- 容器：`prl-n1-2b-r2-transaction-v01`；
- 镜像：`dolfinx/dolfinx:v0.11.0`；
- 容器退出码 0，容器与所有 staging/commit 证据均保留；
- 相关完整回归：`62 passed in 21.56s`；
- 本轮相关模块、测试、runner 和绘图脚本 Ruff：通过；
- 根级 JSON、四个事务摘要和全部 NPZ 可读取；
- PNG 已人工视觉核验，SVG、派生 JSON 和 figure manifest 已生成。

## Deviations

无未批准科学偏差。失败 worker 的非零退出是预登记负控，不是执行异常。

## Outputs

所有原始和派生证据位于：

`results/hybrid/efe_node1_n1_2b_r2_transactional_step_v01_20260820`

关键文件包括：

- `summary.json`；
- `success_replicate_01..03/transaction_summary.json`；
- `failure_control/transaction_summary.json`；
- `n1_2b_r2_transactional_step_derived_v01.json`；
- `n1_2b_r2_transactional_step_diagnostic_v01.png/.svg`；
- `n1_2b_r2_figure_manifest_v01.json`。

## Evidence boundary

r2 证明的是单机、本地文件系统上的一个隔离时间步可以在父进程复核后
create-only 提交，且受控 worker 失败不会改变接受输入。它不等于跨主机
分布式事务或断电级原子协议，也没有验证周期 driver 的 32 个连续事务、
跨周期耗散账本或周期稳态。

正式 N1-2 周期稳态证据仍为 `not_accepted`。当前由同一 Codex 任务实现和
自检，没有伪称独立 Inspector；是否把该 seam 接入周期主线由人类终审决定。

