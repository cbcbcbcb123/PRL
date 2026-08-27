---
execution_id: EXEC-EFE-NODE1-N1-2B-CYCLE-STABILITY-V01
plan_id: PLAN-EFE-NODE1-N1-2B-CYCLE-STABILITY-V01
executor: codex_current_task
started_at: 2026-08-20T07:42:46+08:00
completed_at: 2026-08-20T08:32:01+08:00
status: completed_with_controlled_negative_result_pending_human_review
deviation_records:
  - DEV-N1-2B-001-local-pytest-source-path-retry
  - DEV-N1-2B-002-stage-plot-boolean-csv-parser-repair
---

# EFE Node 1 N1-2b 周期稳态验证执行报告 v01

## Approved plan reference

按人类终审批复的
`project_control/efe_node1_n1_2b_cycle_stability_plan_v01.md` 执行。范围仅含
D0/E0/F150、T16 的解析周期暖启动和最多 4 个完全耦合验证周期；未启动
T32、D1/E1 或后续节点。

## Outcome

N1-2b 没有通过周期稳态验收，执行按硬门受控停止：

1. 冻结 N1-2a 几何下的解析周期 `Z` 暖启动通过；
2. 从暖启动出发的周期 1、2 均完整完成，34 个接受相位全部通过状态硬门；
3. 周期 1 -> 2 的缩短和总能量波形已低于 `1e-3`，但界面牵引、`Z`
   范数波形和周期末 `Z` 未通过；
4. 周期 3 的前三步通过，第 4 步（激活 `0.10`）在 12 次外层耦合后，
   KKT 已通过而 SLS `Z`—几何固定点残差仍未通过，runner 以退出码 1
   主动停止；
5. 因此当前不能声称周期稳态，也没有继续周期 4。

## Periodic warm start

| 指标 | 结果 | 门 | 状态 |
|---|---:|---:|---|
| 冻结几何周期残差 | `5.6034e-16` | `<=1e-12` | 通过 |
| 解析周期 `||Z||` | `0.3786515` | 记录 | — |
| 直接捕获 KKT | `1.6968e-4` | `<=1e-5` | 拒绝 |
| 稀疏精化后 KKT | `4.2091e-11` | `<=1e-5` | 通过 |
| 最小 ECM `J` | `0.9991616` | `>=0.5` | 通过 |
| 最小间隙 | `0.0392790` | `>=-1e-12` | 通过 |

直接捕获没有因优化器返回而被误接受；FEniCSx Krylov 精化后才生成正式
暖启动检查点。该检查点只作为初值，不作为周期稳态证据。

## Two completed cycles

| 指标 | 周期 1 | 周期 2 |
|---|---:|---:|
| 周期末 `Z` 相对前一周期起点差 | `7.5289e-2` | `4.9779e-2` |
| 周期耗散 | `2.6679e-6` | `2.5794e-6` |
| 最大接受态 KKT | `4.3009e-6` | `3.6476e-6` |
| 最小 ECM `J` | `0.9878355` | `0.9877979` |
| 最小间隙 | `0.0154422` | `0.0154677` |
| 最大接受态耦合残差 | `4.8946e-5` | `8.7636e-5` |
| 峰值轴向缩短 | `0.1168789` | `0.1168799` |
| 峰值界面牵引 | `0.0982020` | `0.0980488` |
| 求解时间 | `1001.42 s` | `893.09 s` |

周期 1 -> 2 的预登记差：

| 登记量 | 对称归一化 L2 | `1e-3` 门 |
|---|---:|---|
| 轴向缩短 | `1.5606e-5` | 通过 |
| 最大离散界面牵引 | `2.3243e-3` | 未通过 |
| 总储能 | `2.3954e-5` | 通过 |
| ECM `||Z||` | `5.8744e-2` | 未通过 |
| 周期末完整 `Z` | `4.9779e-2` | 未通过 |

几何和总能量已经几乎重合，但黏弹历史状态仍明显平移；牵引对小的历史态
差异比宏观缩短更敏感。由于 `2*eta_ve/mu_ve=2T`，多周期记忆是预期的，
但这不能替代数值周期门。

## Controlled failure at cycle 3

周期 3 前三步通过。第 4 步的直接分块固定点从：

- coupling 1：KKT `7.3414e-3`、`r_Z=4.7360e-3`；
- coupling 7：KKT `4.1807e-4`、`r_Z=4.1658e-4`；
- coupling 8 兜底：KKT `1.6962e-5`、`r_Z=1.8017e-3`；
- coupling 11：KKT `2.4372e-5`、`r_Z=1.0032e-4`；
- coupling 12 兜底：KKT `9.4001e-6`、`r_Z=2.6162e-4`。

最终 KKT 已过 `1e-5`，但 `r_Z` 仍高于 `1e-4`；最小 `J=0.9930559`、
最小间隙 `0.0268148`。因此失败不是 ECM 反转、接触穿透或机械平衡失效，
而是当前分块 `Z`—几何固定点在允许迭代内未闭合。第 8、12 次延长捕获和
DF-SANE 均未改变硬门。

## Scientific interpretation

本结果建立了一个重要但有限的结论：宏观几何重复不等于黏弹内部状态已达
周期态。若只观察缩短曲线，会错误地提前判定稳态；预登记的 `Z` 波形和
周期末完整张量门成功阻止了该误判。

同时，当前直接 Picard 型分块耦合在激活 `0.10` 附近出现非单调残差和兜底
后反弹，不宜作为后续正式参数扫描的生产求解器。下一步应先修复耦合算法，
而不是增加周期数或放宽门限。

## Commands or tools used

- 固定镜像 `dolfinx/dolfinx:v0.11.0`；
- 暖启动容器 `prl-n1-2b-warm-v01`，退出码 0，完整保留；
- 周期容器 `prl-n1-2b-cycles-v01`，退出码 1，完整保留；
- 主入口 `scripts/run_efe_node1_n1_2_periodic_case_v01.py`；
- 暖启动入口
  `scripts/prepare_efe_node1_n1_2_periodic_warm_start_v01.py`；
- 阶段图入口
  `scripts/plot_efe_node1_n1_2b_cycle_stability_v01.py`。

周期容器墙钟时间约 `48 min 3 s`。未删除容器、失败目录或任何历史结果。

## Files changed

- 暖启动脚本：显式 FEniCSx seam、严格 KKT 捕获门和后端诊断；
- N1-2b 阶段绘图/负结果整合脚本；
- N1-2a 验收决定、N1-2b 批准计划、本执行报告、终审请求及生命周期记录。

## Tests or checks run

- 相关回归：`42 passed in 22.07s`；
- 4 个相关脚本 Ruff：通过；
- 首次本地 pytest 未显式加入 `src`，7 个模块在收集阶段失败；加入本次
  进程 `PYTHONPATH` 后通过，未改测试内容；
- 两周期各 17 行、全部 `passed=True`；
- 重新计算四波形差与封存摘要完全一致；
- 两个 `cycle_states.npz` 的几何、变量和 `Z` 维度完整；
- 3 张 PNG/SVG 已生成，PNG 已人工视觉核查。

## Deviations

### DEV-N1-2B-001

本地测试入口第一次因 `src` 未进入模块路径而在收集阶段停止；使用项目既有
源码路径设置后原样重跑并通过。无模型或测试逻辑变更。

### DEV-N1-2B-002

阶段图读取器第一次把 CSV 的布尔 `passed` 列强制转浮点而停止；增加布尔值
兼容后重跑。无原始数据或定量结果变更。

没有求解器科学偏差：未修改材料、几何、时间步、耦合上限或任一验收门。

## Outputs produced

- 暖启动摘要与检查点：
  `results/hybrid/efe_node1_n1_2b_periodic_warm_start_v01_20260820`；
- 周期与失败证据：
  `results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820/N1_2B_D0_E0_F150_T016`；
- 派生负结果摘要：同目录
  `n1_2b_controlled_failure_summary_v01.json`；
- 波形叠加、滞回与失败诊断图：同目录 `n1_2b_*_v01.png/.svg`；
- 图证据清单：同目录 `n1_2b_stage_figure_manifest_v01.json`。

## Blockers and evidence boundary

N1-2b 的周期稳态候选未形成。当前由同一 Codex 任务执行和自检，没有伪称
独立 Inspector；任何算法修订或重算均等待人类终审新授权。
