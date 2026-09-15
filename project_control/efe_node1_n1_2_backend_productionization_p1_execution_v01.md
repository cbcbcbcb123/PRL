---
execution_id: EXEC-EFE-NODE1-N1-2-BACKEND-PRODUCTIONIZATION-P1-V01
status: accepted_by_human_final_reviewer
plan: project_control/efe_node1_n1_2_backend_productionization_p1_plan_v01.md
authorization: project_control/efe_node1_n1_2_fenicsx_backend_migration_decision_v01.md
executor: codex_current_task
inspector: human_final_reviewer
started_at: 2026-08-19
completed_at: 2026-08-19
formal_n1_2_evidence: not_started
---

# EFE Node 1 N1-2 backend productionization P1 执行报告 v01

## 执行结论

P1 的执行检查全部通过，现提交人类终审。FEniCSx 已从受控 monkeypatch
试验改成显式可注入 ECM 后端；UFL 二阶自动微分 Hessian 经三类状态验证；
PETSc SNES 能稳定恢复峰值 ECM 状态；短 SLS 序列能通过同一后端 seam 保留
内变量记忆。Python 参考后端及现有 SciPy 稀疏 Newton 均未废弃。

本报告不是正式 N1-2 周期稳定、时间收敛或空间收敛证据，也不授权
`D1/E1/32-step`。

## 1. 显式 backend seam

- `evaluate_fast_trilayer_state`、对角预条件器和 equilibrium solver 均接受
  可选 `ecm_backend`；
- 默认值仍调用原 Python `ecm_energy_force`，原行为不变；
- 诊断与 FEniCSx 峰值入口通过参数显式传递后端，不再修改模块全局函数；
- 注入测试分别验证默认等价性与 solver 全链路传播。

## 2. 自动微分 Hessian

后端导出输入节点/分量顺序的 `945 x 945` CSR stored-energy Hessian，每个
状态 `32967` 个非零元。M0、均匀仿射 patch 和 F150 峰值的结果如下：

| 检查 | 合同门 | 最差结果 | 状态 |
|---|---:|---:|---|
| 中心差分方向导数相对误差 | `<=1e-5` | `1.06e-9` | 通过 |
| Hessian 对称残差 | `<=1e-10` | `4.42e-17` | 通过 |
| 三个平移刚体模态残差 | `<=1e-10` | `7.53e-18` | 通过 |

最终实现按需编译 Hessian：普通能量/内力路径首次 JIT 约 `2.4--3.4 s`；
只有第一次请求 Hessian 时才额外编译切线，约 `11.8--12.1 s`。切线暖组装
约 `0.017--0.033 s/次`。

## 3. 完整峰值耦合回归

显式 seam 下重跑 `F150/D0/E0/a=0.20`，80 次捕获后接稀疏 Newton：

| 判据 | 结果 | 状态 |
|---|---:|---|
| 全局缩短相对误差 | `6.40e-10` | 通过 |
| ECM 能量相对误差 | `1.17e-8` | 通过 |
| 界面合力尺度误差 | `9.01e-9` | 通过 |
| 界面牵引 p95 最大相对误差 | `2.11e-5` | 通过 |
| `min J` 绝对误差 | `6.87e-10` | 通过 |
| FEniCSx KKT | `8.81e-8` | 通过 |
| 冷启动端到端加速 | `5.62x` | 通过 |
| 暖态/摊销端到端加速 | `6.30x` | 记录 |

## 4. PETSc SNES 适用性

在 945 自由度、6 个刚体约束的 ECM-only 目标内力恢复问题上：

| 求解器 | 迭代 | 最终残量 | 恢复相对 L2 | 暖求解时间 |
|---|---:|---:|---:|---:|
| PETSc SNES `newtonls + LU` | 4 | `3.03e-13` | `3.22e-10` | `0.242 s` |
| SciPy sparse Newton | 4 | `3.03e-13` | `3.22e-10` | `0.213 s` |

SNES 技术上可用，但在当前小型串行子问题上没有速度优势。P1 的结论是保留
现有完整耦合 SciPy Newton；暂不把 ECM-only 成功外推为完整 DCM--FEM
SNES 生产就绪。

## 5. 短 SLS 记忆回归

对接受的 F150 几何执行
`a=0 -> 0.10 -> 0.20 -> 0.10 -> 0`、`dt=0.25` 的规定形变序列：

- 非零态能量最大相对误差 `6.47e-16`；
- 非零态节点力最大相对 L2 误差 `9.97e-15`；
- 所有相位 `J` 最大绝对误差为 `0`；
- 同一 `a=0.10` 几何的上升/下降支黏弹能差为 `3.1261e-6`，`Z` 状态
  L2 差为 `0.12088`，确认记忆被传递；
- 零态力为机器零，按绝对误差门 `<=1e-11` 判断，实际约 `3.24e-16`。

该序列是规定几何的工程回归，不是完全耦合稳态极限环。

## 6. 保留的负结果与修正

第一次把 Hessian 在后端初始化时提前编译，使完整峰值冷启动 JIT 从约
`3 s` 增至 `14.40 s`，冷启动加速降到 `3.76x`，速度门失败。失败结果被
保留；随后把切线改为首次 `energy_hessian` 调用时才编译。修正后物理结果
不变，冷启动加速恢复为 `5.62x`。

## 7. 验证与环境

- 本地相关回归：`21 passed in 15.19s`；
- 新增/修改 Python 文件：Ruff 通过；
- 容器镜像：`dolfinx/dolfinx:v0.11.0`；
- 当前 repo digest：
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- DOLFINx `0.11.0.post0`，PETSc `3.25.1`；
- 所有成功、失败和停止容器均保留，未执行删除操作。

本轮由当前 Codex 任务执行，没有伪称独立检查；独立终审角色为人类终审。

## 8. 结果位置

- Jacobian 最终回归：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_p1_jacobian_lazy_v02/summary.json`；
- SNES 最终回归：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_p1_petsc_snes_lazy_v02/summary.json`；
- 短 SLS 最终回归：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_p1_short_sls_cycle_lazy_v02/summary.json`；
- 完整峰值最终回归：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_p1_explicit_seam_peak_lazy_v02/summary.json`；
- 提前编译 Hessian 的失败回归：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_p1_explicit_seam_peak_v01/summary.json`。

## 9. 待人类终审

建议接受 P1 技术通过，并只授权下一小步 `N1-2a`：在 D0/E0 上接通一个
完全耦合的黏弹性动态心搏周期，先执行 16-step pilot，再根据收敛与运行时
决定是否进入正式 32-step 及 D1/E1。正式证据、后续网格和 Node 1 下一阶段
仍需分门批准。
