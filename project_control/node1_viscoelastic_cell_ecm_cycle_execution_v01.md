---
execution_id: NODE1-VISCOELASTIC-CELL-ECM-CYCLE-EXECUTION-V01
plan_id: RESEARCH-MAINLINE-THREE-NODE-V01
executor: codex_primary_single_agent
started_at: 2026-08-12
completed_at: 2026-08-12
status: completed
deviation_records:
  - route_connection_mesh_reduced_for_runtime
human_gate: pending
---

# Node 1 可调控细胞—黏弹性 cardiac jelly 单周期执行记录 v01

## Approved plan reference

执行依据：`project_control/research_mainline_three_node_plan_v01.md`。本次只执行 Node 1；Node 2 心肌细胞层尚未启动。

## Implemented physics

- 心肌细胞：原三维固定拓扑 DCM 细胞，分布式轴向主动纤维，激活为平滑 `0 → 0.20 → 0` 单周期。
- cardiac jelly：三维四面体有限应变连续介质；平衡支路 `mu_eq=1.0, kappa_eq=20.0`，黏弹支路 `mu_ve=0.5, eta_ve=0.125`。
- 松弛时间：`tau=2 eta_ve/mu_ve=0.5T`，即 `De=tau/T=0.5`。该值用于机制性主线 pilot，尚无实验标定。
- 动态口径：忽略惯性；每个时间节点交错求解细胞—ECM 机械平衡和 ECM 内变量精确松弛，直到相对耦合残差 `<=5e-4`。
- 界面：复用单侧 52 个材料 tether，远端 ECM 面固定。

## Numerical pilot

- 单周期：`8` 个时间步，连同参考态共 `9` 个状态；
- 细胞：`162` 个顶点、`320` 个三角面；
- ECM：`8` 个顶点、`6` 个四面体；
- 计算时间：`523.62 s`；
- 每个非零时间节点最多使用 `4` 次耦合迭代；
- 最大耦合残差：`1.5067e-4`；
- 最大 KKT 残差：`4.6549e-6`；
- ECM Jacobian 范围：`0.999380–1.000025`。

## Route-connection result

- 峰值激活 `alpha=0.20` 与离散峰值缩短同在 `t/T=0.5`；峰值缩短 `15.6178%`。
- 周期末细胞残余缩短仅 `0.0004076%`，几何基本恢复。
- ECM 内变量范数在 `t/T=0.75` 达到 `0.01939`，周期末仍为 `0.01463`；说明几何恢复不等于材料记忆消失。
- 累计离散 ECM 耗散代理为 `2.5844e-6`，逐步保持非负。
- 峰值界面力范数为 `0.003148`；周期末激活为零时仍有小的界面力 `1.8698e-5`。
- 力—缩短有符号环面积代理为 `1.3799e-6`。
- 8步离散结果未观察到缩短峰值相对激活峰值的时间滞后。当前证据支持“ECM 存在内变量记忆和耗散”，但不支持“全局细胞缩短已有可分辨相位滞后”。

## Gates

以下门全部通过：

- 完整周期和样本数；
- 细胞体积误差 `<=1e-8`；
- ECM 正 Jacobian；
- 非穿透 gap；
- 界面 pair force/moment；
- ECM 内变量对称与无迹；
- 非负离散耗散；
- 黏弹—机械耦合残差。

## Files changed

- `src/hybrid/cell_ecm_coupling.py`：支持外部时间态 `Z` 和 `eta_ve`；
- `src/hybrid/fixed_topology_active_cell_ecm.py`：将时间态 `Z` 传入联合平衡评价，并分解 ECM 平衡/黏弹能；
- `src/hybrid/viscoelastic_cell_ecm_cycle.py`：Node 1 单周期交错耦合求解器；
- `tests/hybrid/test_viscoelastic_cell_ecm_cycle.py`：本构状态传递与耗散测试；
- `scripts/run_node1_viscoelastic_cell_ecm_cycle_v01.py`：正式 pilot；
- `scripts/export_node1_viscoelastic_cycle_geometry_v01.py`：图件几何源；
- `scripts/build_node1_viscoelastic_cell_ecm_figure_v01.py`：阶段图重算与绘制。

## Outputs produced

- 数值结果：`results/hybrid/node1_viscoelastic_cell_ecm_cycle_v01/`；
- 汇总：`results/hybrid/node1_viscoelastic_cell_ecm_cycle_v01/summary.json`；
- 图件版本包：`results/hybrid/node1_viscoelastic_cell_ecm_cycle_v01/Figures/FigN1_viscoelastic_cycle/FigN1_viscoelastic_cycle_v01_20260812/`；
- PNG/SVG 与已执行 Notebook 均通过自动核验和代理视觉检查；版本包保持“工作版本”，等待人类终审，不标记为最终包。

## Tests and checks

- 原 ECM、固定拓扑耦合及新增黏弹状态相关测试通过；
- 图件 Notebook 可从版本包内源数据、几何和本构快照重新执行生成 PNG/SVG；
- 三维状态使用实际位移尺度；应力为归一化模型单位。

## Deviations

最初尝试 `(2,1,2)` ECM 冒烟网格，4时相耦合探针在 `124 s` 工具时限内未完成，随后停止遗留计算进程。为遵守“先接通主线”的目标，正式 pilot 改用 `(1,1,1)` 真三维六四面体网格。该调整不改变本构和双向耦合接口，但明确降低空间场分辨率，因此本结果不能作为网格收敛、应力分布或定量材料结论。

## Evidence boundary and next gate

本阶段只证明：可调控三维 DCM 心肌细胞已经与具有有限松弛时间、记忆和耗散的三维 cardiac jelly 双向接入单周期。

在进入 Node 2 前需要人类图形审阅。若接受 Node 1 主线，下一步只起草心肌细胞层的最小邻接、细胞—细胞连接、激活同步/传播和共享 ECM 几何合同；不会继续细化 Node 1 参数，除非人类要求。
