---
execution_id: EXEC-EFE-NODE1-N1-2B-R1B-PATH-SENSITIVITY-AUDIT-V01
plan_id: PLAN-EFE-NODE1-N1-2B-R1B-PATH-SENSITIVITY-AUDIT-V01
executor: codex_current_task
started_at: 2026-08-20T09:10:00+08:00
completed_at: 2026-08-20T09:43:00+08:00
status: completed_with_path_specific_finding_pending_human_review
deviation_records: []
---

# EFE Node 1 N1-2b-r1b 冷/热路径敏感性审计执行报告 v01

## Approved plan reference

按人类终审批复的
`project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_plan_v01.md` 执行。
范围固定为周期 3 已接受 step 3 到 step 4、D0/E0/F150、激活 `0.10`、
未松弛 Picard 和原有全部硬门；未运行完整周期。

## Outcome

r1b 排除了两个主要嫌疑，并确认了一个数值敏感环节：

1. 未观察到 FEniCSx ECM 后端的历史状态依赖；
2. 未观察到相同输入下冷/热重启的运行间不确定性；
3. 三次冷 Picard 与三次历史预热 Picard 的逐轮变量、完整 `Z` 和终态数组
   逐元素完全相同，均在第 3 次外层迭代通过；
4. 历史长进程失败没有被复现；
5. 历史分支与新分支的第一个封存差异出现在第 1 轮捕获后，变量相对差仅
   `1.200374e-7`；稀疏非线性精化会确定性放大这一微差；
6. 原历史进程中该微差的确切来源仍未解决，因为当时没有封存优化器内部
   评价序列和运行时源码快照。

因此，历史 12 次失败应保留为有效的路径特有负结果，但不能继续归因于
FEniCSx 缓存错误、Picard 固定点不可解或随机求解器漂移。

## Backend history-purity audit

建立 3 个全新 FEniCSx 后端和 3 个按时间顺序重放 35 个可恢复接受态的后端；
每个后端对同一目标几何和 `Z` 再重复装配 3 次。

| 量 | 冷/热最大差 | 门 | 状态 |
|---|---:|---:|---|
| ECM 总能量绝对差 | `0` | `<=1e-12` | 通过 |
| ECM 力对称相对差 | `0` | `<=1e-12` | 通过 |
| ECM `J` 对称相对差 | `0` | `<=1e-12` | 通过 |
| ECM 稀疏切线对称相对差 | `0` | `<=1e-12` | 通过 |

组内三次重复的上述差异也全部为 `0`。显式位移场、DG0 `Z` 系数、材料常数
及 AD 装配在可恢复历史范围内是历史纯的。

## Six complete failed-step replays

| 路径 | 重复数 | 每次外层迭代 | 通过数 | 组内逐数组最大差 |
|---|---:|---:|---:|---:|
| 全新后端冷重启 | 3 | 3 | 3 | `0` |
| 35 个接受态预热后重启 | 3 | 3 | 3 | `0` |

六次输入数组摘要均为
`791adad054a7d47ae2eb9793bf7d836517e0d68a19de4c8b46c0a0b9704b262a`；
预热前后输入摘要一致。六条确定性轨迹共同为：

| 外层迭代 | 原始 `r_Z` | 耦合 KKT | 结果 |
|---:|---:|---:|---|
| 1 | `4.736095e-3` | `7.341618e-3` | 继续 |
| 2 | `6.207395e-3` | `4.925560e-6` | KKT 过、`r_Z` 未过 |
| 3 | `5.245516e-5` | `4.435545e-8` | 通过 |

终态变量和完整 `Z` 在六次复演间逐元素相同；物理门、体积门、面面积门、
`Z` 对称/零迹门均保持通过。

## Localization of nonlinear amplification

历史分支相对新确定性分支：

| 外层迭代 | 捕获后变量差 | 原历史稀疏后变量差 | 表观放大 |
|---:|---:|---:|---:|
| 1 | `1.200374e-7` | `1.787679e-5` | `148.93x` |
| 2 | `1.411672e-3` | `1.212241e-1` | `85.87x` |
| 3 | `1.164502e-1` | `1.162780e-1` | `1.00x` |

为验证第 1 轮放大不是旧结果之间的偶然相关，使用历史第 1 轮捕获状态作为
完全相同输入，独立执行 3 次当前稀疏 Krylov 路径：

- 三次输出逐元素完全相同；
- 相对新分支输出差为 `1.049898e-5`；
- 从 `1.200374e-7` 放大约 `87.46x`；
- 当前复演输出与原历史稀疏输出仍差 `7.378521e-6`。

这证明当前稀疏非线性映射本身会确定性放大极小捕获差异；原历史进程的
`148.93x` 精确轨迹还含有未封存的源码/运行时或内部求解路径差异。

三次稀疏子问题局部门显示 `passed=false` 是预期结果：它们只是固定点每轮的
机械候选，KKT 约 `7.3415e-3`，与原 runner 一样需要后续外层迭代；这不代表
r1b 审计失败。

## Implementation

- `src/hybrid/efe_path_sensitivity.py`：新增数组、标量和稀疏矩阵重复性比较；
- `tests/hybrid/test_efe_path_sensitivity.py`：新增 5 个比较工具测试；
- `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`：增加显式
  `cold/accepted_states` 后端历史模式、35 态顺序重放及输入摘要保护；
- `scripts/run_efe_node1_n1_2b_r1b_backend_purity_v01.py`：新增后端纯度审计；
- `scripts/plot_efe_node1_n1_2b_r1b_path_sensitivity_v01.py`：新增证据汇总和
  四面板诊断图。

## Runtime evidence

- 后端纯度容器：`prl-n1-2b-r1b-purity-v01`；
- 冷复演容器：`prl-n1-2b-r1b-cold-r01-v01` 至 `r03`；
- 预热复演容器：`prl-n1-2b-r1b-warm-r01-v01` 至 `r03`；
- 历史捕获稀疏复演容器：`prl-n1-2b-r1b-archcap-c01-r01-v01` 至 `r03`；
- 固定镜像：`dolfinx/dolfinx:v0.11.0`。

所有容器均退出码 0 并保留；所有原始与派生结果均在项目目录内。

## Tests and checks

- 新增比较工具聚焦测试：`13 passed`（含既有 Aitken 测试）；
- 相关完整回归：`51 passed in 22.66s`；
- 本轮相关 Python 模块、测试、runner 和绘图脚本 Ruff：通过；
- 后端纯度 JSON、九条运行摘要和全部 NPZ 可读取；
- PNG 已人工视觉核验，SVG 与 figure manifest 已生成。

## Deviations

无未批准科学偏差。历史优化器内部评价点和当时加载的源码快照原本没有封存，
按批准计划以“全部可恢复接受态顺序重放”审计，并在证据边界中明确保留该
限制。追加的三次历史捕获稀疏复演属于计划内的局部放大定位。

## Outputs produced

- 后端纯度证据：
  `results/hybrid/efe_node1_n1_2b_r1b_backend_purity_v01_20260820`；
- 3 次冷复演：
  `results/hybrid/efe_node1_n1_2b_r1b_cold_rep*_v01_20260820`；
- 3 次预热复演：
  `results/hybrid/efe_node1_n1_2b_r1b_warm_rep*_v01_20260820`；
- 3 次历史捕获稀疏复演：
  `results/hybrid/efe_node1_n1_2b_r1b_archived_capture_c01_rep*_v01_20260820`；
- 派生摘要、PNG/SVG 和清单：
  `results/hybrid/efe_node1_n1_2b_r1b_path_audit_v01_20260820`。

## Evidence boundary and blocker

r1b 只证明同一失败步在当前冻结源码和环境下可重复冷启动，并证明可恢复
FEniCSx 历史不改变装配或固定点。它不证明原长进程的逐调用历史可重建，
不证明完整周期可重复，也不构成周期稳态证据。

当前由同一 Codex 任务执行和自检，没有伪称独立 Inspector。任何事务性
step worker、自动重启或完整周期恢复均等待人类终审新授权。
