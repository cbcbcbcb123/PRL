---
execution_id: EXEC-EFE-NODE1-N1-2B-R4-REPERIODIZED-VALIDATION-V01
plan_id: PLAN-EFE-NODE1-N1-2B-R4-REPERIODIZED-VALIDATION-V01
executor: codex_current_task
started_at: 2026-08-20T18:20:00+08:00
completed_at: 2026-08-20T19:14:00+08:00
status: completed_controlled_negative_pending_human_review
deviation_records: []
---

# EFE Node 1 N1-2b-r4 解析周期化与事务验证执行报告 v01

## Approved plan reference

按人类终审批复的
`project_control/efe_node1_n1_2b_r4_reperiodized_validation_plan_v01.md`
执行。输入只取正式 r3 v02 cycle 4；未改变 D0/E0/F150、T16、主动加载、
SLS 本构、Picard 上限或任何状态/周期门。

## Outcome

r4 完成了批准的解析周期化和两个完全耦合事务周期，但未达到预登记周期门：

1. 冻结 r3 cycle 4 实际三维 ECM 几何的解析周期 `Z` 通过；
2. phase 0 机械重平衡和全部父进程硬门通过后，暖启动才 create-only 提交；
3. cycle 5 和 cycle 6 各 16 个时间步，共 32 个新鲜 worker 全部通过并提交；
4. cycle 5→6 的轴向缩短、最大界面牵引和总储能波形通过 `1e-3` 门；
5. `Z` 范数波形和周期末完整 `Z` 分别为 `3.850592e-3` 和
   `3.593647e-3`，未通过；
6. 因此正式状态为 `completed_r4_two_cycles_not_stable`，不得声称 N1-2
   已达到 T16 周期稳态。

## Re-periodized warm start

| 指标 | 结果 | 门 | 状态 |
|---|---:|---:|---|
| 冻结几何周期残差 | `5.539159e-16` | `<=1e-12` | 通过 |
| 候选 `Z` 与解析固定点差 | `0` | `<=1e-12` | 通过 |
| phase 0 KKT | `3.774898e-8` | `<=1e-5` | 通过 |
| 体积残差 | `2.220446e-16` | `<=1e-8` | 通过 |
| 最小 ECM `J` | `0.9990335` | `>=0.5` | 通过 |
| 最小 gap | `0.0391368` | `>=-1e-12` | 通过 |
| `Z` 对称/零迹 | `0` / `6.94e-18` | `<=1e-12` | 通过 |

正式暖启动摘要和 create-only 检查点位于：

`results/hybrid/efe_node1_n1_2b_r4_reperiodized_warm_start_v01_20260820`

## Transaction and state gates

| 指标 | cycle 5 | cycle 6 | 登记门 |
|---|---:|---:|---:|
| 接受事务数 | 16 | 16 | 16 |
| 最大 KKT | `6.913687e-6` | `8.185702e-6` | `<=1e-5` |
| 最大原始 `r_Z` | `8.713301e-5` | `8.587305e-5` | `<=1e-4` |
| 最小 ECM `J` | `0.9877293` | `0.9877279` | `>=0.5` |
| 最小 gap | `0.0155179` | `0.0155196` | `>=-1e-12` |
| 周期耗散 | `2.490019e-6` | `2.488512e-6` | 非负 |

32 个 worker PID 全部唯一，32 个候选都通过父 oracle、SLS 更新一致性和
非负耗散门后才提交。cycle 5 step 12 和 cycle 6 step 14 的 KKT 分别为
`6.91e-6` 与 `8.19e-6`，属于通过但相对敏感的相位，已在审阅图中标出。

## Preregistered cycle differences

| 登记量 | cycle 4→5 诊断 | cycle 5→6 决策 | 门 | 决策状态 |
|---|---:|---:|---:|---|
| 轴向缩短波形 | `1.298845e-5` | `2.118563e-6` | `<=1e-3` | 通过 |
| 最大界面牵引波形 | `1.976532e-3` | `1.634431e-4` | `<=1e-3` | 通过 |
| 总储能波形 | `1.966957e-5` | `1.682812e-6` | `<=1e-3` | 通过 |
| ECM `||Z||` 波形 | `4.459691e-2` | `3.850592e-3` | `<=1e-3` | 未通过 |
| 周期末完整 `Z` | `5.097780e-3` | `3.593647e-3` | `<=1e-3` | 未通过 |

解析周期化显著降低了历史漂移，并使牵引波形通过，但 phase 0 机械重平衡及
完全耦合几何更新使冻结几何解析态不再是完整耦合周期映射的精确固定点。
因此当前结果支持“残余差异集中在 ECM 内部记忆”，但尚不足以将其上升为
论文机制结论。

## Commands or tools used

- 固定镜像 `dolfinx/dolfinx:v0.11.0`；
- 暖启动容器 `prl-n1-2b-r4-warm-v01`，退出码 0；
- 周期容器 `prl-n1-2b-r4-cycles-v01`，退出码 0；
- 暖启动入口
  `scripts/run_efe_node1_n1_2b_r4_reperiodized_warm_start_v01.py`；
- 周期入口
  `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py` 的显式 r4
  窗口；
- 论文图版本包 Notebook 执行、自动核验和代理视觉验收。

暖启动内部初始化约 `28.43 s`；两个动态周期 driver 墙钟
`2441.01 s`（约 40.7 min）。两个容器和全部证据均保留，未删除历史结果。

## Files changed

- `src/hybrid/efe_step_transaction.py`：增加周期暖启动父审计和连续验证周期
  窗口函数；
- `tests/hybrid/test_efe_step_transaction.py`：增加周期暖启动逐门拒绝和 r3/r4
  周期窗口测试；
- `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py`：增加显式前一
  周期、首周期、运行标签和授权参数，默认 r3 行为保持不变；
- 新增 r4 暖启动父 driver；
- 新增 r4 冻结定量审阅图版本包 v02；
- 新增 r4 授权、计划、执行和终审记录。

## Tests or checks run

- 周期事务单元测试：`20 passed`；
- 相关模型/事务回归：`49 passed in 14.17s`；
- 相关源码、测试、入口和绘图辅助脚本 Ruff：全部通过；
- 图版本包 Notebook 自动执行与核验：通过；
- PNG 人工/代理目检：通过；v02 与已目检 v01 像素一致；
- 32 个 `transaction_summary.json` 存在，根摘要记录 32 个唯一 PID 与
  32 个接受事务。

## Deviations

无求解或科学偏差。未重试失败事务、未改门、未追加第三周期。

图工作流 v01 自动环境记录只列出 IPython；按工作流保留 v01 并创建 v02，
补齐 Python、Matplotlib、NumPy 和 Pandas 版本后重新执行和目检。v01 仅列为
清理候选，未删除；数值和图像像素未改变。

## Blockers

N1-2 T16 周期稳态候选仍未形成。阻塞量只剩 `Z` 范数波形和周期末完整
`Z`，不是宏观变形、牵引、能量、网格、接触或单步耦合门。

## Outputs produced

正式动态结果：

`results/hybrid/efe_node1_n1_2b_r4_transactional_cycle_v01_20260820`

冻结审阅图版本包：

`02_图表/Figures/Fig2_r4_reperiodized_validation/`
`Fig2_r4_reperiodized_validation_v02_20260820`

## Evidence boundary

r4 证明解析周期化能够显著缩短慢历史瞬态，并使宏观变形、牵引和能量达到
登记周期门；它同时证明一次冻结几何周期化不足以使完全耦合 `Z` 达到
`1e-3`。本结果不证明 T16 稳态、时间/空间收敛或 EFE 机制。

