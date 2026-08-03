---
architecture_id: PRL-HYBRID-ARCH-V18
status: frozen_x1_k_v05_family_c_global_l2_diagnosis_passed
contract: CONTRACT-PRL-HYBRID-X1-K-V05-DIAGNOSTIC
contract_commit: 4d2cad4ab77cb4d9410348283e07212092d31c24
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserved_x1_k_status: failed_instantaneous_smooth_surface_refinement
---

# Hybrid architecture v18 — 质量受控对称破缺 Family C

## 本切片的只读诊断 seam

v05 没有修改 SimuCell3D fork、surface-tension 力、dual-area damping、legacy cache 或 registered `gamma*A` owner。父仓的瞬时球面审计仅新增三项每节点只读量：实际 barycentric control area、物理法向速度误差，以及在调用真实力入口前由拓扑确定的 valence-5 closed-one-ring 标志。聚合器据此计算区域误差能量和响应前几何对称类门禁。

```text
projected icosphere levels 1-4
              |
              v
x' = normalize(M_C x), fixed SPD M_C
              |
              v
response-pre topology/geometry audit
  valence + closed one-ring + geometry signature classes
              |
              v
real surface-tension public force entry
  Psi_registered = gamma A
  zeta_i = zeta_A A_i
              |
              v
instantaneous velocity + global L2 + local error-energy audit
              |
              +-- old v03/v04 gates ---------------- PASS
              +-- class size/count gate ------------- PASS
              +-- finite/nonnegative/partition ledger PASS
              |
              X stop; no trajectory and no X1-K promotion
```

## Family C 的质量与渐近结果

`M_C=I+0.5(M_B-I)`，谱条件数为 `1.172614478`。四层 `h_max/h_min` 为 `1.4785, 1.5498, 1.5878, 1.5980`，全部满足冻结的 `<=2.0`；最小三角质量为 `0.9375`，最小 face/mean-area ratio 为 `0.7056`。几何类数为 `21,81,321,1281`，最大类尺寸全为 `2`，恰好保留对映点成对的几何等价类。

area-weighted global relative L2 的 normal 误差从 `0.05854` 降到 `0.009008`，相邻实际 `h` 阶为 `0.7995,0.9563,0.9898`；tangential 从 `0.02408` 降到 `0.001935`，阶为 `0.9409,1.3250,1.4280`。方向残差全部处在 `1e-7` consistency plateau 内；net force、cache、orientation、topology 与 shape-regularity 门禁均通过。

## extraordinary-vertex 局部风险

valence-5 的 pointwise maximum relative normal error 为 `0.1096,0.1380,0.1468,0.1491`，并未收敛。与此同时，`E_v5=sum A_i e_i^2` 的阶为 `1.2067,1.8276,1.9583`，且其总误差能量占比从 `75.18%` 增至 `97.45%`。这说明绝对误差能量下降主要受 extraordinary-vertex control area 随加密收缩影响，不能解释为点态误差下降。

closed one-ring 的 error-energy 阶为 `1.5826,1.8750,1.9619`，但 pointwise maximum 同样升至 `0.1491`。因此 v05 只支持“质量受控对称破缺族上的面积加权 global L2 诊断通过”，不支持 uniform/pointwise convergence 或完整动力学有效性。

## 系统边界

X1-K 仍未通过；v02 D1 与 v04 Family B 仍保持冻结失败，Route H Gate A v01 仍为 `failed_invalid_numerics`。v05 未授权 smooth S1、R1、C1、F1、ECM/flow、参数标定、长期稳定、生理有效或 EFE 机制 claim。
