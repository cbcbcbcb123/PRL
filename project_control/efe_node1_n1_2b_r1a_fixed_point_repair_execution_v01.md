---
execution_id: EXEC-EFE-NODE1-N1-2B-R1A-FIXED-POINT-REPAIR-V01
plan_id: PLAN-EFE-NODE1-N1-2B-R1A-FIXED-POINT-REPAIR-V01
executor: codex_current_task
started_at: 2026-08-20T08:35:00+08:00
completed_at: 2026-08-20T09:09:00+08:00
status: completed_with_diagnostic_result_pending_human_review
deviation_records:
  - DEV-N1-2B-R1A-001-contemporaneous-picard-control
  - DEV-N1-2B-R1A-002-raw-picard-status-label-erratum
---

# EFE Node 1 N1-2b-r1a 失败步固定点修复执行报告 v01

## Approved scope

按人类终审批复的
`project_control/efe_node1_n1_2b_r1a_fixed_point_repair_plan_v01.md` 执行，仅从
周期 3 已接受的 step 3 检查点复演 step 4：D0/E0/F150、激活 `0.10`、
`dt=1/16`、`mu_ve=eta_ve=0.5`。机械子问题安排、12 次外层上限及全部
物理门保持不变；未重算完整周期、T32、D1/E1 或后续节点。

## Outcome

r1a 证明失败步在冷检查点重启后可解，但否定了“Aitken 是修复原因”：

1. 受保护向量 Aitken 分支在第 4 次外层迭代通过；
2. 同一新 runner、同一镜像、同一检查点的未松弛 Picard 对照在第 3 次通过；
3. 两个新分支在发生松弛差异前的前两次原始机械/SLS 结果完全一致；
4. 两个分支收敛到数值上相同的固定点，Aitken 没有改变解，但也没有加速；
5. 历史 Picard 在长生命周期周期 runner 中 12 次未过，而新 Picard 3 次即过，
   说明当前 blocker 是冷/热执行路径敏感性，不是 Picard 固定点本身不可解；
6. 具体敏感性来源尚未隔离，不能据此恢复完整周期或声明周期稳定。

因此建议保留 Aitken 实现和测试作为诊断工具，但不提升为生产默认算法。

## Frozen acceptance gates

| 指标 | 门 |
|---|---:|
| 机械 KKT | `<=1e-5` |
| 未松弛原始 SLS 固定点残差 `r_Z` | `<=1e-4` |
| ECM 最小 `J` | `>=0.5` |
| 最小间隙 | `>=-1e-12` |
| 外层机械调用 | `<=12` |

最终接受仍使用未松弛解析 SLS 映射，没有用松弛残差替代合同量。

## Archived versus fresh trajectories

| 分支 | 结果 | 外层迭代 | 最终原始 `r_Z` | 最终耦合 KKT |
|---|---|---:|---:|---:|
| 历史 Picard | 未通过 | 12 | `2.616198e-4` | `9.400118e-6` |
| 新 Picard 对照 | 通过 | 3 | `5.245516e-5` | `4.435545e-8` |
| 受保护 Aitken | 通过 | 4 | `3.083799e-5` | `2.612489e-8` |

Aitken 应用权重依次为 `1.0`、`0.4159048484`、`1.0`；最终一轮已经达到
原始映射门，不再应用下一次松弛。新 Picard 比 Aitken 少一次机械调用，故
没有生产化 Aitken 的证据。

## Final-state equivalence

Aitken 相对新 Picard 的终态对称相对差为：

| 量 | 相对差 |
|---|---:|
| 全变量向量 | `1.185789e-6` |
| 完整 `Z` | `2.023880e-7` |
| 轴向缩短 | `3.470560e-9` |
| 界面牵引 | `8.015247e-7` |
| 总能量 | `4.408898e-11` |

两个分支的体积门、面面积门、`Z` 对称/零迹门、`J` 和接触间隙门均通过。
Aitken 分支的 `min J=0.99305183`、最小间隙 `0.02685788`；没有 ECM
反转或接触穿透。

## Path-sensitivity evidence

历史分支与新分支在第一次机械捕获输入上的变量相对差仅约 `1.20e-7`，稀疏
输出差约 `1.79e-5`；到第二次耦合时，输入差放大到约 `1.41e-3`，稀疏输出
差约 `1.21e-1`。新 Picard 与 Aitken 在前两轮则完全一致。这支持以下有限
结论：非线性求解路径会放大极小状态差，且历史周期进程与冷检查点重启并非
当前数值实现下的等价执行路径。

本次没有证明差异来自 FEniCSx 后端缓存、求解器历史、进程状态或其他具体
机制；这些备选原因必须通过后续冷/热后端隔离审计判别。

## Implementation

- `src/hybrid/efe_cycle_convergence.py`：增加有界向量 Aitken、残差增长保护、
  对称零迹投影和非有限输入拒绝；
- `tests/hybrid/test_efe_cycle_convergence.py`：增加权重公式、边界、退化回退及
  `Z` 投影测试；
- `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`：新增失败步 Aitken/
  Picard 双模式 pilot、逐迭代证据和根级摘要；
- `scripts/run_efe_node1_n1_2_periodic_case_v01.py`：耦合门失败时先写根级
  `failure_summary.json`；
- `scripts/plot_efe_node1_n1_2b_r1a_fixed_point_comparison_v01.py`：生成派生摘要、
  对照图和图证据清单。

## Runtime evidence

- Aitken 容器：`prl-n1-2b-r1a-aitken-v01`，退出码 0，墙钟 `76.79 s`；
- 新 Picard 容器：`prl-n1-2b-r1a-picard-v01`，退出码 0；
- 固定镜像：`dolfinx/dolfinx:v0.11.0`；
- 两个容器、历史失败目录和全部逐迭代结果均原样保留。

## Tests and checks

- Aitken 聚焦测试：`8 passed`；
- 相关完整回归：`46 passed in 22.29s`；
- 修改的 Python 模块、测试、runner 和绘图脚本 Ruff：通过；
- 派生 JSON 可读取，PNG 已人工视觉核验，SVG 与 manifest 已生成。

## Deviations

### DEV-N1-2B-R1A-001

批准计划要求与冻结历史 Picard 轨迹比较。Aitken 冷重启第一轮与历史第一轮
出现微小差异后，追加了同 runner、同镜像、同检查点的新 Picard 对照，以免
把冷启动效应误归因于算法。该对照属于已批准的 Picard–加速比较，没有改变
模型、门限或外层上限。它直接改变了科学结论：Aitken 不优于 Picard。

### DEV-N1-2B-R1A-002

新 Picard 原始 `summary.json` 的 `algorithm`、逐迭代数据和通过状态均正确，
但成功状态文本沿用了 Aitken 标签。发现后修正了生成脚本；为保持原始证据
不可追写，没有改写已生成摘要，而是在派生比较 JSON 中记录明确勘误。

## Outputs

- Aitken：
  `results/hybrid/efe_node1_n1_2b_r1a_aitken_pilot_v01_20260820`；
- 新 Picard：
  `results/hybrid/efe_node1_n1_2b_r1a_picard_control_v01_20260820`；
- 对照摘要、PNG/SVG 和 manifest：
  `results/hybrid/efe_node1_n1_2b_r1a_comparison_v01_20260820`。

## Evidence boundary

本阶段只证明周期 3 step 4 可在冷检查点重启后满足原合同固定点和物理门。
它不证明热后端与冷后端等价，不证明完整周期可复现，也不构成 N1-2 周期
稳态证据。当前结果等待人类终审。
