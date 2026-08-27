---
report_id: REPORT-EFE-NODE1-N1-2-FENICSX-BACKEND-SPIKE-V01
status: completed_pending_human_migration_decision
reported_at: 2026-08-19
authorization: project_control/efe_node1_n1_2_fem_backend_spike_authorization_v01.md
proposal: project_control/efe_node1_n1_2_fem_backend_spike_proposal_v01.md
formal_n1_2_evidence: not_started
---

# EFE Node 1 N1-2 FEniCSx 后端受控试验报告 v01

## 结论

`F150/D0/E0/a=0.20` 受控试验达到物理一致性门和冷启动速度门。建议接受
FEniCSx 为 N1-2 的候选 ECM 后端，但先执行一个受控生产化步骤，不直接启动
正式 `D1/E1/32-step` 收敛矩阵。

当前实现是 `FEniCSx UFL 自动微分残量 + PETSc 向量组装 + 既有 SciPy
稀疏 Newton/SuperLU`。它还不是完整 PETSc SNES 生产实现，也没有把 ECM
解析切线接入全系统 Jacobian；因此本报告只证明候选后端可行，不把它表述成
完整求解器迁移已经完成。

## 冻结环境

- 镜像：`dolfinx/dolfinx:v0.11.0`；
- OCI digest：
  `sha256:58b27e84a2f26b98ce2d9ccc537b0ee6a59e2fcfdf386626d5ed9ddf43425ece`；
- DOLFINx：`0.11.0.post0`；PETSc：`3.25.1`；
- 网格：315 个 ECM 节点、1152 个四面体，`(8, 4, 6)`；
- 本构未改变：`mu_eq=1`、`kappa_eq=20`、`mu_ve=0.5`；
- 峰值参考状态：已接受的 `F150/D0/E0/a=0.20` 状态。

## Phase A：ECM 场评估等价性

| 工况 | 关键判据 | 结果 | 状态 |
|---|---:|---:|---|
| M0 零态 | `||f|| <= 1e-11` | `3.18e-17` | 通过 |
| M0 零态 | `|E| <= 1e-12` | `0` | 通过 |
| 均匀仿射 patch | 总能相对误差 `<=1e-8` | `6.38e-15` | 通过 |
| 均匀仿射 patch | 节点内力相对 L2 `<=1e-8` | `5.41e-15` | 通过 |
| 均匀仿射 patch | `J` 最大绝对误差 `<=1e-12` | `2.22e-16` | 通过 |
| F150 峰值场 | 总能相对误差 `<=1e-8` | `8.69e-15` | 通过 |
| F150 峰值场 | 节点内力相对 L2 `<=1e-8` | `1.98e-13` | 通过 |
| F150 峰值场 | `J` 最大绝对误差 `<=1e-12` | `2.22e-16` | 通过 |

参考 Python ECM 每次暖评估约 `0.255 s`；FEniCSx 暖组装约
`0.0018–0.0022 s`。这是 ECM 子模块速度，不等同于完整耦合速度。

## Phase B：完整 DCM—ECM—内膜峰值耦合

最终采用 80 次捕获优化后接稀疏 Newton；与参考后端同一加载步比较：

| 判据 | 合同门 | 结果 | 状态 |
|---|---:|---:|---|
| 全局轴向缩短相对误差 | `<=1%` | `6.40e-10` | 通过 |
| ECM 总能相对误差 | `<=1%` | `1.17e-8` | 通过 |
| 界面合力尺度误差 | `<=5%` | `9.01e-9` | 通过* |
| 两界面牵引 p95 最大相对误差 | `<=5%` | `2.11e-5` | 通过 |
| `min J` 绝对差 | `<=0.01` | `6.87e-10` | 通过 |
| FEniCSx KKT | `<=1e-5` | `8.81e-8` | 通过 |
| 心肌/内膜体积残差 | `<=1e-8` | `0 / 1.11e-16` | 通过 |
| FEniCSx `min J` | `>=0.5` | `0.9887395334` | 通过 |
| FEniCSx `min gap` | `>=-1e-12` | `0.0149705099` | 通过 |
| 冷启动端到端加速 | `>=5x` | `5.64x` | 通过 |
| 已编译/摊销端到端加速 | 记录项 | `6.49x` | 记录 |

参考后端同一加载步用时 `128.45 s`。FEniCSx 路线的捕获与精化为
`19.81 s`；再计入首次 UFL JIT `2.98 s` 后为 `22.79 s`。

`*` 两界面的净合力都因几何对称而接近数值零。直接以两个近零数互除会给出
`0.93` 的无意义“相对误差”。本报告采用
`||R_new-R_ref|| / max(两端界面逐材料点传递力模之和)`，同时保留原始近零
相对数，未隐藏该口径变更。此归一化仍需人类终审明确追认。

## 保留的负结果

1. 首次容器运行因 DOLFINx v0.11 `create_mesh` 参数顺序变化而停止；
2. Phase A v02 用相对误差比较两个机器零值，造成 M0 假失败；
3. 240 次捕获路线物理等价，但热态仅 `3.86x`，未过速度门；
4. 从 `a=0.18` 直接做单次固定切线 Newton 未进入收敛域，KKT 为
   `4.49e-2`；
5. 100 次捕获路线通过，冷启动约 `4.76x`（早期计时口径）或在后续运行中
   接近门值；最终采用重复通过的 80 次捕获路线，并显式纳入 JIT。

这些目录和停止状态均保留，未删除或覆盖。

## 代码与证据

- 无 FEniCSx 依赖的交换合同：`src/hybrid/fenicsx_ecm_spike.py`；
- 容器 ECM 适配器：`src/hybrid/fenicsx_ecm_backend.py`；
- 输入封存：`scripts/export_efe_node1_fenicsx_spike_v01.py`；
- Phase A：`scripts/run_efe_node1_fenicsx_ecm_equivalence_v01.py`；
- Phase B：`scripts/run_efe_node1_fenicsx_coupled_peak_v01.py`；
- 稀疏诊断的可选后端入口：
  `scripts/diagnose_efe_node1_sparse_preconditioner_v01.py`；
- Phase A 最终证据：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_phase_a_v03/summary.json`；
- Phase B 最终证据：
  `results/hybrid/efe_node1_fenicsx_spike_v01_20260819/fenicsx_phase_b_coupled_peak_capture080_v04/summary.json`。

回归检查：`19 passed`；相关新增/修改文件 Ruff 全部通过。

## 证据边界

- 本结果不是正式 N1-2 周期稳定、时间收敛或空间收敛证据；
- 尚未执行 `D1/E1/32-step`；
- 尚未验证多周期 SLS 内变量更新接入新后端；
- 尚未完成持久后端接口、ECM 解析切线和 PETSc SNES；
- 参考后端必须保留为 D0/E0 回归 oracle。
