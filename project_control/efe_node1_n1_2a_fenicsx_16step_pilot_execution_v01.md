---
execution_id: EXEC-EFE-NODE1-N1-2A-FENICSX-16STEP-PILOT-V01
plan_id: PLAN-EFE-NODE1-N1-2A-FENICSX-16STEP-PILOT-V01
executor: codex_current_task
started_at: 2026-08-19
completed_at: 2026-08-19
status: accepted_by_human_final_reviewer_with_engineering_deviations
deviation_records:
  - DEV-N1-2A-001-residual-monotonicity-safeguard
  - DEV-N1-2A-002-maximum-coupling-iterations-8-to-12
---

# EFE Node 1 N1-2a FEniCSx 16-step pilot 执行报告 v01

## Approved plan reference

按已批准计划
`project_control/efe_node1_n1_2a_fenicsx_16step_pilot_plan_v01.md` 执行
D0/E0/F150、16-step、单个完全耦合黏弹性 warmup cycle。

## Outcome

pilot 已完整完成 16 个时间步和 17 个接受相位。所有接受相位通过 KKT、
体积、正 Jacobian、间隙、面面积、SLS 固定点、耗散及 `Z` 对称/零迹硬门。

本结果证明“DCM 心肌主动收缩—FEniCSx 黏弹性 ECM—内膜”单周期动态主线
已经接通，但不是周期稳态、时间收敛或空间收敛证据。

## Commands or tools used

- 固定镜像 `dolfinx/dolfinx:v0.11.0`；
- 周期入口 `scripts/run_efe_node1_n1_2_periodic_case_v01.py`；
- ECM 后端 `fenicsx_ufl_ad_serial_v02_lazy_tangent`；
- 默认 80 次能量捕获，未过严格捕获门时使用稀疏 Krylov 精化；
- Matplotlib 阶段绘图脚本
  `scripts/plot_efe_node1_n1_2a_pilot_v01.py`；
- 本地 pytest、Ruff、JSON/CSV/NPZ 读取和 PNG 视觉核查。

Docker Desktop 在开始前处于 manually paused；执行中只做了 restart 以恢复
运行，没有删除容器、镜像或历史结果。

## Scientific and numerical results

| 指标 | 结果 | 合同门 | 状态 |
|---|---:|---:|---|
| 完成时间步 | `16/16` | `16/16` | 通过 |
| 接受相位 | `17/17` | 全部通过 | 通过 |
| 最大接受态 KKT | `7.6761e-8` | `<=1e-5` | 通过 |
| 最大接受态 SLS 固定点残差 | `2.5611e-5` | `<=1e-4` | 通过 |
| 最小 ECM `J` | `0.9885237` | `>=0.5` | 通过 |
| 最大 ECM `J` | `1.0087955` | 记录 | 通过 |
| 最小层间隙 | `0.0150825` | `>=-1e-12` | 通过 |
| 峰值轴向缩短 | `0.1168672`（`11.69%`） | 记录 | 通过 |
| 峰值离散界面牵引 | `0.1001610` | 记录 | 通过 |
| 单周期 ECM 耗散 | `6.2945e-6` | `>=0` | 通过 |
| FEniCSx 平均 ECM 组装 | `0.002528 s` | 记录 | 通过 |
| 总用时 | `986.76 s` | 记录 | 完成 |

周期末激活回到 0，但仍有：`||Z||=0.14899`、界面峰值牵引
`7.4334e-4`、ECM 黏弹能 `5.1616e-7`。轴向缩短只剩
`8.96e-6`，说明强支撑使几何几乎恢复，而 ECM 内变量仍保留首周期记忆。

同为激活 `a=0.10`：

- 上升支缩短 `0.06692496`，下降支 `0.06693093`；
- 下降支峰值界面牵引比上升支低 `7.8756e-4`；
- 下降支黏弹能比上升支低 `2.4604e-6`；
- `||Z||` 从 `0.02315` 增至 `0.15142`。

这些只作为首周期记忆信号，不接受为稳态滞回结论。

## Deviations and repair

### v01 retained failure

首次运行在第 `7/16` 步、激活 `0.192388` 处停止。8 次外层耦合后 KKT
仍为 `2.49e-4`、`Z` 残差 `1.21e-3`，未过门。该结果完整保留在
`results/hybrid/efe_node1_n1_2a_fenicsx_pilot_v01_20260819`。

诊断发现：稀疏 Krylov 即使返回比输入更大的残差，诊断入口仍无条件保存
其候选，导致后续外层耦合以更差状态继续。高迭代捕获、modified Newton 和
谱残差探针均保留为负结果；没有降低 KKT 或 SLS 门限。

### DEV-N1-2A-001

给非谱接触路线增加残差单调保护：只有候选缩小 scaled residual norm 才接受，
否则保留输入状态并记录 safeguard。v02 中该保护在第 4 步触发 2 次，阻止了
v01 曾出现的 KKT `3.95e-2` 爆跳。

### DEV-N1-2A-002

外层耦合上限由计划中的 8 增至 12，不改变 `1e-4` 固定点门。第 4 步需要
10 次耦合后同时通过；其余接受步最多 4 次。预设的 1000 次延长捕获和 2000
次谱残差回退在最终 v02 中一次也未启用。

这两项是工程求解策略偏差，不改变几何、材料、加载、时间步或科学判据。

## Files changed

- `scripts/run_efe_node1_n1_2_periodic_case_v01.py`：显式 FEniCSx seam、
  后端记录及受控失败回退；
- `scripts/diagnose_efe_node1_sparse_preconditioner_v01.py`：可移植入口、
  `df_sane` 诊断路线及残差保护；
- `scripts/plot_efe_node1_n1_2a_pilot_v01.py`：可复算阶段状态/诊断图；
- 本执行报告和终审请求。

## Tests or checks run

- 相关回归：`21 passed in 13.48s`；
- 修改 Python 文件 Ruff：通过；
- summary、17 行时序、状态 NPZ、检查点：可读取；
- PNG/SVG 文件非空；
- 两张 PNG 已人工视觉核查：布局、图例、色标和门限线可读。

## Outputs produced

- 主结果：
  `results/hybrid/efe_node1_n1_2a_fenicsx_pilot_v02_20260819/N1_2A_D0_E0_F150_T016/summary.json`；
- 完整周期状态：同目录 `cycle_01/cycle_states.npz`；
- 时序：同目录 `cycle_01/cycle_timeseries.csv`；
- 五相位状态图：同目录 `n1_2a_16step_state_montage_v01.png/.svg`；
- 诊断图：同目录 `n1_2a_16step_diagnostics_v01.png/.svg`；
- 图证据清单：同目录 `stage_figure_manifest_v01.json`。

## Blockers and evidence boundary

无工程 blocker。由于只有首个 warmup cycle，`cycle_stable=false`，周期末
`Z` 相对初始零态差为 1。当前不得声称周期稳定、时间收敛、网格收敛或 EFE
疾病机制已经验证。

本轮由当前 Codex 任务执行和自检，没有伪称独立 Inspector。人类终审于
2026-08-20 接受 N1-2a 及两项已披露工程偏差，并批准进入 N1-2b；接受记录见
`project_control/efe_node1_n1_2a_acceptance_and_n1_2b_authorization_decision_v01.md`。
