---
architecture_id: ARCH-PRL-HYBRID-V10
status: frozen_x1_g_active_overdamped_step
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V09
cell_engine_commit: 7a709a8353e83c43847a4853414068033217b906
---

# PRL 自有长期混合架构 v10

本版本冻结 X1-G：X1-E 的主动心肌能量与节点力、X1-F 的真实 `node.force_` 装配 seam，现已接入一次由 PRL 拥有的原子过阻尼位置更新。该路径在真实 cell-engine `cell` 上产生可核验位移并消费力缓冲区，但尚不是连续时间轨迹，也没有接入 stock `solver::run_iteration`。

## 单步合同

对一个由单 worker 独占的非静态 cell，已有 `node.force_` 被解释为预先装配的被动力或接触力，主动心肌力作为额外增量加入。对每个 used vertex：

\[
\mathbf F_i = \mathbf F_i^{\mathrm{pre}} + \mathbf F_i^{\mathrm{act}},
\qquad
\Delta\mathbf x_i = \frac{\Delta t}{\zeta}\mathbf F_i,
\qquad
\mathbf x_i^{n+1}=\mathbf x_i^n+\Delta\mathbf x_i,
\]

其中 `Δt > 0`，阻尼系数 `ζ > 0`。公共入口为：

- 父项目：`prl::cell_engine::advance_active_cell_overdamped_one_step`；
- 受控 fork：`prl::cell_engine::advance_surface_overdamped`。

执行顺序冻结为：

```text
real cell + revision-matched material + frozen contraction units
        │ capture current surface snapshot
        ▼
evaluate_active_contraction()
        │ active energy / input power / persistent-vertex forces
        ▼
advance_surface_overdamped()
        │ validate revision, ownership assumptions, parameters, IDs,
        │ current state, every total force, displacement and resulting position
        ▼
atomic commit: node.pos_ = pending position; node.force_ = 0
        │
        ▼
ActiveCellOverdampedStepAudit
        └── STOP: no loop, no automatic remesh, no ECM or flow
```

## 原子性与职责边界

父项目拥有心肌特异的激活、纤维、preferred-length contraction unit、主动能量和输入功率。fork 只拥有生物学无关的 surface-force/position primitive。

所有可能失败的主动求值、主动能量—功率账本有限性检查、revision/ID/状态有限性检查以及 pending position 构造均发生在写入前。成功提交后，父入口不再执行可能抛异常的“后状态主动求值”；后状态能量由测试或上层 driver 在成功返回后独立计算。因此，陈旧材料、陈旧目标 revision、未知或重复顶点、非有限状态或主动账本、非正 `Δt/ζ` 均不得留下部分位置更新或部分力缓冲区清零。

同一 cell 在调用期间仍遵守 one-cell/one-owner 规则；本版本不宣告同一 cell 的并发 step 安全。不同 cell 的调度继承 X1-D 的所有权模型。

## 离散账本

fork 在同一次预提交遍历中记录：

\[
W_F = \sum_i \mathbf F_i\cdot\Delta\mathbf x_i,
\qquad
D_\zeta = \frac{\zeta}{\Delta t}\sum_i\lVert\Delta\mathbf x_i\rVert^2,
\qquad
r_{WD}=|W_F-D_\zeta|.
\]

对冻结的 forward-Euler 公式，`W_F = D_ζ` 是代数恒等式；测试要求残差不超过 `1e-12`。主动账本另记录步前能量 `Ψ_act^n`、输入功率 `P_act^n` 和一步控制能估计 `Δt P_act^n`。X1-G 的平台激活算例满足 `P_act=0`，并独立验证 `Ψ_act^{n+1}<Ψ_act^n`。这不是有限步长下 `ΔΨ + D = 0` 的宣告；显式 Euler 的能量差包含预期的二阶截断项。

## 制造算例与重网格组合

真实八节点 cell、一个 contraction unit、`activation=0.1`、`activation_rate=0`、`Δt=1e-3`、`ζ=1` 的结果为：

| 量 | 值 |
|---|---:|
| reference/current contraction length | `0.9290452088031024` |
| active energy before | `0.04315625` |
| active nodal-force L2 norm | `0.5984955095905065` |
| displacement L2 norm | `0.0005984955095905065` |
| force work | `0.000358196875` |
| viscous dissipation | `0.000358196875` |
| contraction length after | `0.9286596550414490` |
| active energy after | `0.04279879638351551` |

合力平衡使质心位移残差不超过 `1e-12`。真实 edge swap 后，mesh 与材料迁移 revision 均为 1；同一冻结 contraction unit 可再次完成单步，保持 persistent vertex identity、能量下降、work–dissipation 恒等式和力缓冲区清零。

## 缓存、solver 与未宣告项

`advance_surface_overdamped` 只提交节点位置并重置 used-node force buffers，不刷新 centroid、face normal、area、volume 等派生几何缓存。未来 orchestration 在再次装配依赖这些缓存的被动力前，必须显式刷新几何状态。该限制已写入 fork 公共接口注释。

X1-G 没有修改 stock `solver::run_iteration`，没有调用真实被动力模型，没有时间循环、步长收敛或长时稳定性证据，也没有 ECM、接触参数标定、血流或生理结论。Route H Stage 2 Gate A 仍保持 `failed_invalid_numerics`。

下一安全切片建议为 X1-H：在 PRL owned driver 中显式接入真实被动力装配与派生几何缓存刷新，仍只验收单步顺序和失败传播；在此之后才进入短轨迹与时间步收敛门槛。
