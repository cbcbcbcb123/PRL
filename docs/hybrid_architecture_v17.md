---
architecture_id: PRL-HYBRID-ARCH-V17
status: frozen_x1_k_v04_failed_family_B_shape_regularity
contract: CONTRACT-PRL-HYBRID-X1-K-V04-DIAGNOSTIC
contract_commit: 4314566
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserved_x1_k_status: failed_instantaneous_smooth_surface_refinement
---

# Hybrid architecture v17 — cache precision repair 与参数化族失败

## 受控 fork 修改

fork 仅把 `surface_tension_energy_` 成员、getter 和 reset 提升为 double。legacy 公式仍是 `0.5*gamma*A`，仍为 excluded plotting owner；真实 surface-tension 面积梯度、节点力、registered `gamma*A`、dual-area damping 和 v02 evaluator 均未修改。

```text
fork RED: float getter + level-5 ratio error 2.3612e-6
                         |
                         v
minimal instrumentation repair (float -> double)
                         |
                         v
fork GREEN: ratio error 1.7986e-14; mechanics baseline unchanged
                         |
                         v
Family A levels 2-5 ---------------- PASS
                         |
                         v
Family B fixed SPD levels 1-4
  direction/cache/global L2/net ----- pass
  orientation/topology/q/area ratio - pass
  h_max/h_min <= 2.0 ---------------- FAIL on levels 2-4
                         |
                         X stop; no trajectory
```

## Family B 失败边界

固定 `M` 映射后的 `h_max/h_min` 为 `1.9269, 2.0460, 2.1116, 2.1345`。第一个失败发生在 source level 2。它只说明该预注册参数化网格族未满足 v03 的 edge-ratio shape-regularity proxy；不能事后放宽阈值，也不能据此否定 surface-tension 离散。

Family B 的 class count 为 `21,81,321,1281`，最大 class size 全为 `2`，相对标准 Family A 的 `4,10,30,102` 与最大 `60,120,120,120`，支持固定映射打破原离散对称；但 mesh gate 失败使 v04 整体不能通过。

## 点态风险

标准 A 的 12 个 valence-5 点 absolute normal error mean 仍为 `0.1345,0.1430,0.1452,0.1457`；B 为 `0.1085,0.1428,0.1519,0.1542`。两族均没有 extraordinary-vertex 点态 normal convergence。全局面积加权 L2 收敛不得升级为 uniform/pointwise convergence。

未来任何轨迹 acceptance 在执行前必须先冻结 extraordinary-vertex 局部质量与速度审计；v04 不实现该轨迹门禁。

## 系统边界

X1-K 仍未通过。Route H Gate A v01 仍为 `failed_invalid_numerics`。smooth S1、R1、C1、F1、ECM/flow、参数标定和机制 claim 均未授权。
