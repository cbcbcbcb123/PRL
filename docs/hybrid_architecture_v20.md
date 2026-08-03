---
architecture_id: PRL-HYBRID-ARCH-V20
status: frozen_x1_k_v07_mean_radius_diagnosis_passed_without_x1_k_pass
contract: CONTRACT-PRL-HYBRID-X1-K-V07-DIAGNOSIS
contract_commit: 668465c9f554850d0624eef474c49b8514c21cce
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
---

# Hybrid architecture v20 — mean-radius 结构与时间底噪诊断

## v07 的只读审计层

v07 没有修改受控 SimuCell3D fork、真实 surface-tension force、barycentric dual-area damping、registered `gamma*A` owner 或任何主离散。新增实现位于 PRL-owned audit/test/export/docs/results 层：

```text
Family C projected icosphere
M_C fixed; source levels 1–4; R0=1
                   |
                   +--> initial read-only structural audit (levels 1–4)
                   |      independent A and barycentric dual areas
                   |      real public surface-tension force
                   |      Euler contraction r_H and mean velocity r_v
                   |      position/state hashes + cleared force buffers
                   |
                   +--> fixed-topology trajectories (levels 1 and 4)
                          dt = 4e-4, 2e-4, 1e-4, 5e-5
                          T = 0.02; no retry/adaptation
                                     |
                                     v
                          raw time differences and orders
                          first-order Richardson extrapolation
                          v06 global/local/energy controls [read-only]
                                     |
                                     v
                          bounded v07 diagnosis PASS
                          X1-K remains FAIL; stop before R1/C1/F1
```

结构审计调用真实 `cell::apply_internal_forces(0)` 获取节点力。调用前确认 force buffers 为空，调用后清空 force buffers 并刷新聚合几何缓存；位置和状态 hash 必须恢复一致。该 seam 不提交位置，也不改变轨迹或主力学路径。

## 结构恒等式的作用域

固定拓扑面积在统一缩放下满足 `A(lambda x)=lambda^2 A(x)`。因此 Euler 定理给出

```text
sum_i x_i · grad_i A = 2A,
sum_i x_i · F_i = -2 gamma A,
F_i = -grad_i(gamma A).
```

当初始所有 `r_i=R0` 时，control-area mean radius `Rbar=sum_i A_i r_i/sum_i A_i` 的权重导数项相消，故

```text
dRbar/dt = sum_i A_i(v_i·n_i)/sum_i A_i
          = -2 gamma/(zeta_A R0).
```

这只是初始等半径球面和统一缩放方向上的结构关系，不是逐自由度完整梯度证明，也不是非球网格或全轨迹的解析恒等式。

## 时间底噪诊断

source levels 1 和 4 的三组相邻时间差均严格递减，两个观测阶分别约为 `1.00010,0.99983` 和 `1.00032,0.99959`，且没有进入合同定义的共同 `1e-13` raw 舍入平台。一阶 Richardson 误差分别为 `7.7320e-12` 和 `1.3256e-13`，跨网格 Richardson 差为 `7.5995e-12`。

这些结果支持 v06 mean-radius raw 差异受一阶时间误差底影响，但不改写 v06 的冻结空间失败。v06 的 excursion-normalized 四层误差和负阶仍原样保留。

## 系统边界

能量 coverage 仍为 `surface_tension_only`；legacy `0.5*gamma*A` cache、membrane、bending、pressure、contact、active、ECM 和 flow 全部排除。v07 没有运行 R1、C1、F1，也不授权 remesh/contact、ECM/flow 长耦合、参数标定、长期稳定、生理、FSI、EFE 或心脏发育机制结论。
