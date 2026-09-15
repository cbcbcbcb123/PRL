---
execution_id: EXEC-EFE-NODE1-N1-2B-R3-TRANSACTIONAL-CYCLE-V01
plan_id: PLAN-EFE-NODE1-N1-2B-R3-TRANSACTIONAL-CYCLE-V01
executor: codex_current_task
started_at: 2026-08-20T11:30:00+08:00
completed_at: 2026-08-20T14:17:00+08:00
status: completed_two_transactional_cycles_not_stable_pending_human_review
deviation_records:
  - DEV-EFE-NODE1-N1-2B-R3-001-JSON-BOOL-SERIALIZATION
---

# EFE Node 1 N1-2b-r3 事务性周期重算执行报告 v01

## Approved plan reference

按人类终审批复的
`project_control/efe_node1_n1_2b_r3_transactional_cycle_plan_v01.md` 执行。
从原 N1-2b 已接受 cycle 2 `accepted_step_016.npz` 启动，只重算
D0/E0/F150、T16 的 cycle 3–4；未改变模型、未松弛 Picard、12 次外层上限
和全部状态/周期门。

## Outcome

r3 完成了批准的两个完整事务周期：

1. cycle 3 和 cycle 4 各 16 个时间步，共 32 个新鲜 worker；
2. 32 个 worker PID 全部不同，32 个候选均通过父进程 oracle、解析 SLS
   一致性和非负耗散门；
3. 32 个候选均在复核后 create-only 提交，候选摘要与提交摘要完全一致；
4. 历史问题相位 cycle 3 step 4 在 3 次 Picard 后通过；cycle 4 step 4
   需要 7 次，但仍在原 12 次上限内通过；
5. 两个周期的所有机械、体积、接触、网格、黏弹结构和耗散门均通过；
6. cycle 3→4 的宏观变形和储能波形已高度重复，但 ECM 内变量仍未达到
   预登记周期门，因此正式结论为“完成、未稳态”。

根级状态为 `completed_r3_two_cycles_not_stable`，不是运行错误，也不得解释为
N1-2 已达到极限周期。

## Transaction and state gates

| 指标 | cycle 3 | cycle 4 | 登记门 |
|---|---:|---:|---:|
| 接受事务数 | 16 | 16 | 16 |
| 最大 KKT | `5.051941e-6` | `8.655056e-8` | `<=1e-5` |
| 最大原始 `r_Z` | `5.789369e-5` | `7.158579e-5` | `<=1e-4` |
| 最小 ECM `J` | `0.9877731` | `0.9877567` | `>=0.5` |
| 最小 gap | `0.0154851` | `0.0154970` | `>=-1e-12` |
| 周期耗散 | `2.535297e-6` | `2.512914e-6` | 非负 |

所有候选的父进程 SLS 更新差为 0，`Z` 对称/零迹门和两层面面积门也全部
通过。32 个 transaction summary 的 `parent_oracle`、`cycle_consistency` 和
根级 `passed_before_commit` 均为真。

## Preregistered cycle differences

| 登记量 | cycle 2→3 | cycle 3→4 | 门 | cycle 3→4 状态 |
|---|---:|---:|---:|---|
| 轴向缩短波形 | `1.055248e-5` | `7.389441e-6` | `<=1e-3` | 通过 |
| 最大界面牵引波形 | `1.597274e-3` | `1.106283e-3` | `<=1e-3` | 未通过 |
| 总储能波形 | `1.634485e-5` | `1.123308e-5` | `<=1e-3` | 通过 |
| ECM `||Z||` 波形 | `3.915114e-2` | `2.643996e-2` | `<=1e-3` | 未通过 |
| 周期末完整 `Z` | `3.350454e-2` | `2.281097e-2` | `<=1e-3` | 未通过 |

cycle 4 峰值轴向缩短为 `0.11688095`，峰值界面牵引为 `0.09787001`。宏观
几何和储能基本周期化，但 `Z` 仍保留显著跨周期漂移。`Z` 波形差和末态差
相对上一对周期的衰减比分别约为 `0.675` 和 `0.681`；这与冻结几何 SLS 的
单周期衰减因子 `exp(-T/tau)=exp(-0.5)=0.6065` 同量级，支持“剩余差异主要是
黏弹记忆瞬态”的有限解释。

## Implementation

- `src/hybrid/efe_step_transaction.py`：增加冻结周期相位规格和父进程 SLS/
  耗散一致性门；
- `tests/hybrid/test_efe_step_transaction.py`：增加相位默认等价性、非法相位和
  SLS/耗散门测试；
- `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`：参数化任意
  cycle/step，同时保持 r1a 默认相位；
- `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py`：逐步新进程、
  父 oracle、create-only 提交、周期账本和五项周期门；
- `scripts/plot_efe_node1_n1_2b_r3_transactional_cycle_v01.py`：可复算的周期
  诊断图和 cycle 4 三维状态图。

## Runtime, tests and checks

- 正式容器：`prl-n1-2b-r3-cycle-v02`，镜像
  `dolfinx/dolfinx:v0.11.0`，退出码 0；
- 正式 driver 墙钟 `2284.56 s`（约 38.1 min）；
- 32 个 transaction summary 全部通过，32 个 PID 唯一；
- 相关完整回归：`69 passed in 21.55s`；
- 本轮相关模块、测试、runner 和绘图脚本 Ruff：通过；
- JSON/CSV/NPZ 可读取，两个 PNG 已人工视觉核验，SVG 和 manifest 已生成；
- 两个正式/偏差容器和所有证据均保留在项目目录内。

## Deviations

`DEV-EFE-NODE1-N1-2B-R3-001-JSON-BOOL-SERIALIZATION`：首次 v01 运行的
cycle 3 step 1 通过物理门并 create-only 提交后，父记录中的 NumPy 布尔值
无法由标准 JSON encoder 序列化，driver 退出。该目录没有完整事务账本或
周期证据，未被拼接或复用。修正为 Python `bool` 后，使用全新 v02 目录从
原 cycle 2 末态完整重启。模型、算法和门限未改变。详见：

`project_control/efe_node1_n1_2b_r3_deviation_dev001_v01.md`

## Outputs produced

正式结果：

`results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v02_20260820`

偏差保留结果：

`results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v01_20260820`

关键正式产物包括根级 `summary.json`、32 个 `transaction_summary.json`、
cycle 3/4 的状态包、时序、周期摘要、派生 JSON、两组 PNG/SVG 和 figure
manifest。

## Evidence boundary

r3 证明了事务周期 driver 可连续完成两个 T16 周期，并给出了有效的受控
未稳态结果。它不证明 T16 周期稳定，更不证明时间或空间收敛。宏观力学已近
周期而 `Z` 未收敛是当前模型参数和初值下的数值/物理现象；其是否作为论文
机制结论仍需后续稳态求解与参数比较。

当前由同一 Codex 任务实现和自检，没有伪称独立 Inspector。正式周期稳态
证据保持 `not_accepted`，等待人类终审决定下一步。

