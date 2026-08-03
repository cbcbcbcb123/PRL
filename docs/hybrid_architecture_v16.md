---
architecture_id: PRL-HYBRID-ARCH-V16
status: frozen_x1_k_v03_failed_family_A_legacy_cache_precision
contract: CONTRACT-PRL-HYBRID-X1-K-V03-DIAGNOSTIC
contract_commit: 354972f75638c641abd1c28efb3256ad5724d262
preserved_x1_k_status: failed_instantaneous_smooth_surface_refinement
---

# Hybrid architecture v16 — mesh-family asymptotic diagnosis

## 新增的只读诊断 seam

v16 只扩展 `audit_spherical_surface_tension_instantaneous` 的输出，不改变真实 surface-tension force、`gamma*A` owner、dual-area damping 或 v02 evaluator：

- `h_min/h_rms/h_max`；
- closed two-manifold、Euler、signed volume、strict outward/star-shaped face proxy；
- triangle quality、face-area ratio、radius residual；
- 每顶点 valence、control-area ratio、normal/tangential error；
- 由响应前几何定义的 quantized symmetry-class ID；
- 逐 valence 与逐 class 的 mean/max/RMS 分布。

## v03 执行图

```text
v02 frozen failure regression (unchanged)
              |
              v
Family A standard levels 2,3,4,5
  mesh quality ---------------- pass
  normal/tangential asymptotic - pass
  one-direction gamma*A audit -- consistency plateau
  net force -------------------- pass
  excluded legacy 0.5 gamma*A -- FAIL at level 5 float accumulation
              |
              X stop
Family B fixed-SPD mapped family -- not executed
trajectory/R1/C1/F1 -------------- not executed
```

Family A 的 normal L2 阶为 `0.957, 0.990, 0.997`，tangential L2 阶为 `1.175, 1.379, 1.446`；finest 分别为 `0.0044003` 与 `0.00068764`。这些仅支持所选标准族的全局面积加权渐近段，不恢复 X1-K。

## 分布诊断边界

标准族 symmetry-class count 随 level 为 `4,10,30,102`，最大 class size 为 `60,120,120,120`。12 个 valence-5 extraordinary vertices 的 absolute normal error mean 为 `0.1345,0.1430,0.1452,0.1457`，并未逐点趋零；global L2 的约一阶下降主要来自固定数量异常点的面积权重随 refinement 缩小，以及 valence-6 主体误差下降。因此不得把全局 L2 渐近结果写成 uniform/pointwise convergence。

## 硬失败与系统边界

level 5 的 legacy cache / registered energy 为 `0.5000023612048187`，偏离 `0.5` 达 `2.3612e-6`，超过合同阈值 `1e-6`。该 cache 是 upstream float plotting instrumentation，仍被排除；失败不等于 `gamma*A` force gradient 失败。由于它被预注册为硬审计，Family A 和 v03 必须失败。

受控 fork 未修改；Route H Gate A v01 仍为 `failed_invalid_numerics`。Family B、smooth S1、R1、C1、F1、ECM/flow、参数标定和机制 claim 均未授权执行。
