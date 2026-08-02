---
architecture_id: ARCH-PRL-HYBRID-V12
status: frozen_x1_i_spatially_consistent_surface_damping
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V11
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# PRL 自有长期混合架构 v12

本版本冻结 X1-I：PRL owned driver 和受控 cell-engine fork 均新增显式阻尼律接口。新的连续轨迹候选路径采用三角形表面的重心双面积（barycentric dual area）加权阻尼；X1-G/H 的统一每顶点标量阻尼仅作为历史重放接口保留，不被静默改义。

## 空间离散合同

对于当前几何中的 used vertex `i`，控制面积与有效节点阻尼定义为

```text
A_i^n = (1/3) * sum(area_f^n),  f incident on i
zeta_i^n = zeta_A * A_i^n
x_i^(n+1) = x_i^n + dt * F_i^n / zeta_i^n
```

其中 `zeta_A` 是单位表面积阻尼系数。控制面积从本步当前坐标重新计算，不依赖可能陈旧的派生缓存；每个 used vertex 必须具有有限正控制面积，所有有效节点阻尼及 `dt/zeta_i` 必须有限且为正。随后仍沿用 X1-H 的 pending geometry 验证、原子位置/力提交和 face/node/cell 缓存刷新合同。

fork 公共类型为 `SurfaceDampingLaw` / `SurfaceDampingMeasure`，PRL owned 配置为 `CellSurfaceDampingLaw` / `CellSurfaceDampingMeasure`。两层审计均记录：

- 阻尼空间度量；
- 单位面积或单位节点的输入系数；
- 控制面积总和；
- 最小与最大有效节点阻尼；
- 力功、黏性耗散及其代数残差。

## 制造解门禁

对同一单位立方体闭合表面采用 coarse/base/fine 三层网格，三角形数为 `12/36/108`，顶点数为 `8/20/56`。施加恒定面力 `t=(0.4,-0.2,0.1)`，以独立计算的控制面积离散为 `F_i=A_i t`，并取 `dt=0.1`、`zeta_A=2`。解析位移为

```text
Delta x_i = dt * t / zeta_A = (0.02, -0.01, 0.005)
```

三层网格的每个顶点均在 `1e-12` 容差内满足该位移。控制面积总和保持表面积 6，力功在三层均为 0.063；因此该阻尼离散不会仅因节点数变化而改变此制造面力问题的动力学时间尺度。

`displacement_l2_norm` 会随顶点数增长，因为它是未面积加权的节点向量范数；它不是空间一致性指标。门禁使用逐顶点位移误差、控制面积分片和网格间力功一致性。

## owned 单步接线

`advance_owned_active_cell_overdamped_one_step` 接受显式 `CellSurfaceDampingLaw`，并把它传入真实接触/被动/主动装配后的 cell-engine 位移原语。八顶点真实被动＋主动单步得到控制面积总和 `13.211102550927979`、有效节点阻尼范围 `11.009252125773315–22.018504251546631`，完成位置提交、派生几何刷新和力缓冲区清理。

旧 `double damping_coefficient` 重载仍精确映射为 `uniform_per_vertex`，用于复算 X1-G/H 冻结结果。X1-I 以后任何新轨迹必须显式传入 `barycentric_dual_area`；不得把旧重载作为已经证明空间一致的路径。

## 功率解释与后续边界

双面积模式的离散耗散记为

```text
D_zeta = sum_i zeta_i * ||Delta x_i||^2 / dt
```

在显式更新 `Delta x_i=dt F_i/zeta_i` 下，`W_F=sum_i F_i dot Delta x_i` 与 `D_zeta` 相等仍是代数恒等式。X1-I 不把该相等解释为显式 Euler 稳定性、时间收敛、能量不等式或连续轨迹有效性证据。

下一阶段必须先执行 X1-J：为 split/swap/merge 建立 `DeltaPsi_remesh` 算法缺陷账本及循环重网格能量/功/纤维漂移门禁；随后才是 X1-K 短轨迹的时间与空间 refinement、体积、质心、质量、穿透、能量不等式和失败持久化门禁。X1-K 通过前仍禁止进入 ECM/血流长耦合、参数标定或论文机制 claim。Route H Gate A v01 保持 `failed_invalid_numerics`。
