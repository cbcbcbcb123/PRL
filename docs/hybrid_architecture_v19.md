---
architecture_id: PRL-HYBRID-ARCH-V19
status: frozen_x1_k_v06_family_c_short_trajectory_failed
contract: CONTRACT-PRL-HYBRID-X1-K-V06-S1
contract_commit: ae80a0b6c77309fcfc6c3b2a19d8dbeb68af90b8
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
---

# Hybrid architecture v19 — Family C 短轨迹失败冻结

## v06 新增的 PRL-owned seam

v06 没有修改受控 SimuCell3D fork、surface-tension force、barycentric dual-area damping、legacy cache 或 registered `gamma*A` owner。新增代码只在 PRL-owned 层把 v05 的 Family C 网格接入固定拓扑短轨迹，并逐步记录全局、能量和 extraordinary-vertex 局部审计。

```text
Family C projected icosphere, source levels 1–4
M_C fixed; topology fixed; no remesh/contact/active
                         |
                         v
real cell::apply_internal_forces(dt)
  registered owner: Psi = gamma A
                         |
                         v
advance_surface_overdamped
  zeta_i = zeta_A * barycentric_dual_area_i
  atomic position + geometry-cache commit
                         |
                         v
per-step independent audit
  global geometry/cache/centroid
  DeltaPsi + D_zeta [surface_tension_only]
  V5 + fixed closed-one-ring geometry
  current-force local normal-error risk ledger
                         |
                         v
four-level analytic + generalized self convergence
finest dt/2 time pollution + global/local gates
                         |
                         X mean-radius analytic monotonicity FAIL
                           stop; no R1/C1/F1
```

轨迹 runner 每个物理步只通过既有公共入口装配真实力并调用 owned overdamped step。逐步 normal-error 诊断再次调用同一公共力入口，但在调用前确认 force buffers 为空、调用后清空 buffers，且不提交位置；因此诊断不会改变轨迹状态。

## 冻结的失败

四层实际 `h_rms/R0` 为 `0.5846466,0.3007587,0.1514741,0.0758752`。control-area mean-radius ratio 的 excursion-normalized 解析误差为

```text
1.04393e-7, 1.69657e-7, 1.93118e-7, 1.98408e-7,
```

相邻阶为 `-0.73059,-0.18884,-0.03909`。误差不在冻结的 normalized `1e-10` common plateau，且随加密增加，因此 v06 硬失败。面积、体积与 registered-energy ratio 的解析/自收敛门禁通过；四个 QoI 的 finest 时间污染门禁也通过。

该半径误差的 raw 量级只有 `8.35e-12` 至 `1.59e-11`，与 finest `dt`/`dt/2` 差异 `8.00e-12` 同量级，说明当前结果更像近似不变量中的抵消和时间/舍入误差底，而不是已证明的空间离散或物理不稳定。合同对空间解析误差使用 excursion-normalized plateau，故仍必须失败，不能事后改判。

## extraordinary-vertex 风险边界

全轨迹最大 valence-5/closed-one-ring radial excursion error 为 `0.14907<=0.25`；最大 radial error/initial local `h` 为 `1.8533e-4<=5e-4`；最大一环边缩放误差为 `8.116e-6<=5e-4`；最低局部质量相对初值为 `0.999996>=0.90`。这些只说明冻结短轨迹局部风险界未被突破。

每步保存的 normal-error energy fraction 和 pointwise maximum 继续显示 extraordinary vertices 是主要风险源。面积权重 global L2 或有限时程局部门禁通过都不得解释为 pointwise/uniform convergence。

## 系统边界

X1-K 不通过；R1、C1、F1 未运行。v02 D1、v04 Family B 和 Route H Gate A v01 的历史失败保持不变，v05 仍只是一项 global L2 mesh-family 诊断通过。未授权 ECM/flow、标定、长期稳定、生理、FSI、EFE 或发育机制结论。
