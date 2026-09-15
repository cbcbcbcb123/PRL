---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V06-S1
status: frozen_before_family_c_short_trajectory_response
frozen_at: 2026-08-03
parent_commit_before_v06: 203e27984efe059fbdd00ca33406c2592fedf81c
cell_engine_commit_before_v06: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserves_x1_k_status: failed_instantaneous_smooth_surface_refinement
preserves_v05_status: passed_quality_controlled_symmetry_broken_global_L2_diagnosis
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# X1-K v06 Family C smooth-sphere short-trajectory 监督合同

v06 只执行 X1-K 内部有界的 Family C 固定拓扑 smooth S1。它不是 X1-K 总验收，不授权 R1、C1、F1、ECM/flow、参数标定或机制 claim。本合同必须先提交并推送，之后才能产生任何 v06 轨迹响应。

不得覆盖或改写 v01–v05 的合同、原始结果、报告与失败语义。Route H Gate A v01 继续是 `failed_invalid_numerics`；v02 D1 继续是 `failed_instantaneous_smooth_surface_refinement`；v04 Family B 继续是 `failed_family_B_parameterized_diagnosis`；v05 只保持 `passed_quality_controlled_symmetry_broken_global_L2_diagnosis`。受控 fork 固定为 `e2ed64a`，禁止修改 fork、真实 surface-tension force、barycentric dual-area damping、legacy cache、registered owner、旧测试或旧阈值。

执行顺序冻结为：合同提交并推送 → TDD RED → 最小新轨迹审计 seam → 四层共同 `dt` 轨迹 → finest `dt/2` 轨迹 → 预注册门禁。任一全局、解析、自收敛、时间污染、能量或局部门禁失败，立即冻结 v06 失败并停止。全部通过时唯一允许状态为 `passed_family_c_smooth_short_trajectory_with_local_risk_bounds`；X1-K 仍不通过并返回导师。

## 1. 模型、网格与时间矩阵

沿用 v02 连续制造解和 v05 Family C，不作任何响应后调整：

```text
R0 = 1,
gamma = 0.02,
zeta_A = 10,
dR/dt = -2 gamma/(zeta_A R),
R(t)^2 = 1 - 4 gamma t/zeta_A.
```

网格只使用 v05 已冻结的 projected icosphere source levels 1、2、3、4，以及

```text
M_C = [[1.000, 0.050, 0.025],
       [0.050, 1.050, 0.040],
       [0.025, 0.040, 0.950]],
x' = normalize(M_C x).
```

四层均固定拓扑、无 remesh/contact/active，使用 `dt=1e-4`、`T=2e-2`、200 steps。source level 4 另以同一初始网格运行 `dt=5e-5`、400 steps。禁止 adaptive retry、静默缩短时程、删步或调矩阵。

最终解析值预注册为：

```text
R(T)^2       = 0.99984,
R(T)/R0      = 0.999919996799744,
A(T)/A0      = 0.99984,
V(T)/V0      = 0.999760009600256,
Psi(T)/Psi0  = 0.99984.
```

代表空间尺度继续使用每个初始 Family C 网格全部唯一边的 `h_rms/R0`，观测阶不得假设层间倍率为 2。

## 2. 每步全局账本

每个 run 的 step 0 至终步均保存：

- control-area mean radius `Rbar=sum_i A_i |x_i|/sum_i A_i`，并报告 `Rbar/R0`；
- independent surface area、signed volume、registered `Psi=gamma*A` 及各自相对该 run 初值的 ratio；
- surface centroid 及 `|c(t)-c(0)|/R0`；
- minimum oriented face alignment、全局 minimum triangle quality `q=4sqrt(3)A/sum(l_i^2)`；
- minimum face area / 该 run step-0 minimum face area；
- independent geometry-vs-cache normalized residual；
- `DeltaPsi=Psi_n-Psi_(n-1)`、本步 `D_zeta` 与 `DeltaPsi+D_zeta`。

step 0 的 `DeltaPsi`、`D_zeta` 与 ledger residual 均记为 0。能量 coverage 只允许 `surface_tension_only`：registered owners 为 `gamma*A` 和 `D_zeta`；excluded owners 为 legacy `0.5*gamma*A` cache、membrane elasticity、bending、pressure、contact、active、ECM 和 flow。

## 3. excursion-normalized 解析误差

对四个最终 QoI：`Rbar/R0`、area ratio、volume ratio、registered-energy ratio，冻结

```text
e_Q(h) = |Q_h(T)-Q_exact(T)|
         / max(|Q_exact(T)-Q_h(0)|, 1e-12).
```

该定义使用每个 run 实际 step-0 QoI；不得用接近 1 的 QoI 本身作误差归一化。每个 QoI 的四层 `e_Q` 必须非增；除四层均 `<=1e-10` 的共同 plateau 外，每个相邻解析阶

```text
p_ij = log(e_i/e_j)/log(h_i/h_j)
```

必须 `>=0.5`；finest `e_Q<=0.02`。

## 4. excursion-normalized 相邻网格自收敛

每个 QoI 的三组相邻差冻结为

```text
d_ij = |Q_i(T)-Q_j(T)|
       / max(|Q_exact(T)-Q_i(0)|, 1e-12).
```

由于全部初始 Family C QoI 的解析目标和 step-0 值相同，四层使用同一解析 excursion；仍逐行保存实际分母。三组 `d_01,d_12,d_23` 必须非增。除三组均 `<=1e-10` 的共同 plateau 外，两个广义阶分别用 triples `(0,1,2)` 与 `(1,2,3)` 解唯一 `p in [0,16]`：

```text
d_01/d_12 = (h_0^p-h_1^p)/(h_1^p-h_2^p),
d_12/d_23 = (h_1^p-h_2^p)/(h_2^p-h_3^p).
```

无唯一根或任一广义阶 `<0.5` 即失败。

## 5. finest 时间污染

对 finest `dt=1e-4` 与 `dt/2=5e-5` 的四个最终 QoI，保存：

```text
delta_time_raw = |Q_dt-Q_dt/2|,
e_space_proxy_raw = |Q_dt/2-Q_exact|,
delta_time_excursion = delta_time_raw/excursion,
e_space_proxy_excursion = e_space_proxy_raw/excursion.
```

若 `delta_time_raw` 与 `e_space_proxy_raw` 同时 `<=1e-10`，按 v02 共同 plateau 通过；否则必须 `delta_time_raw<=0.25*e_space_proxy_raw`。禁止用归一化前后数值差异改变通过语义。

## 6. 全局几何、缓存和能量门禁

所有 run、所有步必须满足：

- minimum oriented face alignment `>0`；
- global minimum triangle quality `>=0.05`；
- minimum face area / 该 run 初始 minimum face area `>=1e-4`；
- maximum normalized cache residual `<=1e-12`；
- surface centroid drift `/R0<=1e-2`；
- `sum_n max(0,DeltaPsi_n+D_zeta_n)/Psi0<=1e-3`。

不得把本 coverage 写成 full owned-step total-energy inequality。

## 7. extraordinary-vertex 响应前集合与每步局部账本

每个 run 在 step 0、任何力或位移响应前，用初始固定拓扑冻结：

- `V5={i: valence(i)=5}`；
- `N5_closed=V5` 与所有通过一条初始边邻接 `V5` 的顶点；
- closed-one-ring edges 为两个端点均属于 `N5_closed` 的所有唯一初始边；
- closed-one-ring incident faces 为至少一个顶点属于 `N5_closed` 的所有初始三角面；
- `h_i(0)` 为节点 `i` 的初始 incident-edge mean length。

固定拓扑下这些集合、边、面和初始尺度不得随时间重分类。每步对 `V5` 和 `N5_closed` 保存：顶点数、最大/均方根径向解析偏差、初始 `h_i` 归一化偏差；对 closed-one-ring edges 保存相对解析均匀缩放偏差；对 incident faces 保存局部 minimum quality 及其相对 step-0 局部 minimum quality。

局部硬门禁冻结为：

```text
max_(i in V5 or N5_closed) ||x_i|-R_exact(t)|
  / max(|R_exact(t)-R0|,1e-12) <= 0.25,

max_(e in closed-one-ring edges)
  |(l_e(t)/l_e(0))/(R_exact(t)/R0)-1| <= 5e-4,

max_(i in V5 or N5_closed) ||x_i|-R_exact(t)|/h_i(0) <= 5e-4,

minimum_q_(closed-one-ring incident faces)(t)
  >= 0.90 * minimum_q_(closed-one-ring incident faces)(0).
```

在 `t=0`，两个径向偏差归一化指标单独强制记录为 0；其余局部指标按定义记录。

每步另通过真实 surface-tension 公共力入口、当前 barycentric control area 和解析 `v_exact(t)=-2gamma/(zeta_A R_exact(t))` 计算 normal-error energy `sum A_i e_i^2`。分别保存 `V5` 与 `N5_closed` 的 error-energy fraction、area-weighted relative RMS 和 pointwise maximum relative error。该诊断调用后必须清空 force buffers，且不得改变位置。面积权重下降不得解释为 pointwise convergence。

## 8. TDD、失败和交付

RED 先通过公共 seam 要求目前尚缺失的轨迹行为：control-area mean radius、响应前 fixed local sets、逐步局部几何与 normal-error ledger，以及 excursion-normalized analytic/self-convergence/time-pollution gate。RED 必须因缺失行为失败，不得先运行 Family C 轨迹。

GREEN 只允许在 PRL-owned 层新增上述 runner、只读审计类型、门禁 evaluator、测试与导出器；不得修改 fork 或旧力学路径。若任一门禁失败，冻结首个失败及原始时序并停止；若全部通过，状态只能为 `passed_family_c_smooth_short_trajectory_with_local_risk_bounds`。

新增且不覆盖旧版的交付为：v06 合同、架构、中文报告、machine summary/criteria、四层逐步 CSV、finest `dt/2` 逐步 CSV、局部逐步 CSV、最终解析误差/自收敛/时间污染表、逐步能量 ledger、TDD 证据、复算命令、全量 parent/fork/strict/Python/Ruff 验证与远端同步证据。

不得触碰既有未跟踪的 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 或 `scripts/insert_efe_figure_mockups_docx.py`。
