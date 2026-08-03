---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V02
status: frozen_before_v02_response_generation
frozen_at: 2026-08-03
parent_commit_before_v02_results: 713cbf77ef8c95b2358ba8560f633a8bad88688a
cell_engine_commit_before_v02_results: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
supersedes_acceptance_role_of: CONTRACT-PRL-HYBRID-X1-K-V01-S1-only
preserves_v01_failure: failed_spatial_refinement_nonconvergent_area_energy
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# Hybrid X1-K v02 光滑球面制造解监督验收合同

本合同在产生任何 X1-K v02 数值响应前冻结。它不覆盖、不改写或重新解释 commits `1241d80`、`713cbf77` 及 `results/hybrid/x1_k_short_trajectory_v01/`。v01 cube 失败继续是有效的科学失败；v02 只检验光滑表面。禁止按结果改变网格层数、`dt`、`T`、阈值、比较量、解析解、roundoff 规则或失败顺序。

任一硬门禁失败时立即停止，冻结首个失败及其原始数据；不得运行尚未开始的后续 case。只有 smooth S1 全部通过后，才按 R1、C1、F1 的顺序继续。Route H Gate A v01 始终保持 `failed_invalid_numerics`。

## 1. 连续模型、符号与注册能量

注册表面能唯一取

`Psi_surface = gamma A`。

实际表面张力节点力必须通过方向导数证明满足 `F_i=-partial(Psi_surface)/partial(x_i)`。上游 `surface_tension_energy_ = 0.5 gamma A` 是 legacy plotting cache；v02 必须报告它，但将其明确列入 excluded owner，绝不用于能量、误差或通过判据。

采用外法向 `n`。曲率和定义为 `kappa_sum=kappa_1+kappa_2=2/R>0`；平均曲率为 `H=kappa_sum/2=1/R`。面积一阶变分与表面力密度约定为 `delta A = integral(kappa_sum u_n dA)`、`f_n=-gamma kappa_sum`。面积阻尼密度为 `zeta_A`，因此外法向速度

`v_n = dR/dt = -2 gamma/(zeta_A R)`，

并得到制造解

`R(t)^2 = R0^2 - 4 gamma t/zeta_A`。

相应解析 QoI 为 `A(t)/A0=(R/R0)^2`、`V(t)/V0=(R/R0)^3`、`Psi(t)/Psi0=(R/R0)^2`。

冻结无量纲参数：`R0=1`、`gamma=0.02`、`zeta_A=10`。所有轨迹显式使用 `barycentric_dual_area` damping；禁止 legacy uniform-per-vertex 重载。

## 2. 光滑网格族与实际空间尺度

使用以原点为中心、所有顶点逐层径向投影到 `R0=1` 的 outward-oriented icosphere：

| level | vertices | triangles |
|---:|---:|---:|
| 0 / coarse | 12 | 20 |
| 1 / base | 42 | 80 |
| 2 / fine | 162 | 320 |
| 3 / finest | 642 | 1280 |

每次 subdivision 对每条无向边只创建一个 midpoint，然后投影到单位球；子面继承 outward orientation。禁止用 cube、非投影 midpoint 或不同半径替代。

代表网格尺度冻结为初始网格全部唯一边的无量纲 RMS chord length：

`h = sqrt(sum_e |x_a-x_b|^2 / N_edge) / R0`。

同时报告 `h_max=max_e |x_a-x_b|/R0`，但观测阶只使用上述实际 `h`，不得假设层间比恰为 2。

对于有解析真值的误差 `e_i`，相邻层阶为 `p_ij=log(e_i/e_j)/log(h_i/h_j)`。对于只做相邻网格自收敛的差 `d_ij=|Q_i-Q_j|`，三层广义阶 `p` 由

`d_01/d_12=(h_0^p-h_1^p)/(h_1^p-h_2^p)`

在 `p in [0,16]` 上求唯一根；无根即失败。四层产生 `(0,1,2)` 和 `(1,2,3)` 两个审计值。若相关误差或相邻差全部不超过该 gate 的 roundoff plateau，则记录 plateau，不伪造阶。

## 3. D0：非光滑 cube 奇异族诊断回归

保留 v01 的单位 cube、`8/12`、`26/48`、`98/192`、`gamma=0.02`、`zeta_A=10`、`dt=1e-4`、`T=2e-3`。它不再是 smooth-cell acceptance gate，但测试必须显式重现并保存：

- area-ratio order 在 `[-1.05,-0.95]`；
- registered-energy-ratio order 在 `[-1.05,-0.95]`；
- volume-ratio order 在 `[0.90,1.10]`；
- area 与 registered energy 的 base-fine 差严格大于 coarse-base 差；
- legacy cache 仍被排除，注册 owner 仍为 `gamma A`。

D0 失败码为 `failed_cube_singularity_diagnostic_regression`。它只支持“尖锐棱边面积 L2 梯度流呈奇异负阶响应”，不得用于否定光滑表面上的 force–damping 离散。

## 4. D1：半离散瞬时力—能量与速度门禁

每个 icosphere level 在初始几何上只装配一次真实 surface-tension force，不推进位置。

### 4.1 方向导数

在每个顶点 `x_i` 定义 `n_i=x_i/|x_i|`、`a_i=0.25+0.10 x_i+0.07 y_i-0.05 z_i`、`t_i=e_z-(e_z dot n_i)n_i`，并取原始方向 `d_i=a_i n_i+0.05 t_i`；所有 `d_i` 再除以全局 `max_i |d_i|`。中心差分步长冻结为 `epsilon=1e-6 h`：

`D_FD=[Psi(x+epsilon d)-Psi(x-epsilon d)]/(2 epsilon)`，

`D_force=-sum_i F_i dot d_i`。

归一化残差为 `e_dir=|D_FD-D_force|/max(|D_FD|,|D_force|,Psi,1e-30)`。每层还报告 `legacy_cache/Psi`，其与 `0.5` 的绝对偏差必须 `<=1e-6`，但该 cache 仍为 excluded owner。

方向导数硬门禁：finest `e_dir<=1e-6`；若四层全部 `e_dir<=1e-7`，记 consistency plateau 并通过阶判据；否则误差须随 `h` 非增，所有非 plateau 相邻解析阶 `p>=0.5`。

### 4.2 瞬时速度

节点控制面积取当前几何 `A_i=(1/3) sum_{f incident i} A_f`，速度为 `v_i=F_i/(zeta_A A_i)`。使用解析球面法向 `n_i=x_i/|x_i|`，冻结面积加权误差：

`e_normal = sqrt(sum_i A_i[(v_i dot n_i)-v_exact]^2/sum_i A_i)/|v_exact|`，

`e_tangent = sqrt(sum_i A_i|v_i-(v_i dot n_i)n_i|^2/sum_i A_i)/|v_exact|`，

其中 `v_exact=-2 gamma/(zeta_A R0)=-0.004`。

两项误差均须随 `h` 非增；非 plateau 相邻阶均 `>=0.5`，roundoff plateau=`1e-10`；finest `e_normal<=2e-2` 且 `e_tangent<=2e-2`。同时要求净力范数除以 `gamma A0/R0` `<=1e-12`。

D1 失败码依次为 `failed_surface_force_directional_derivative`、`failed_instantaneous_smooth_surface_refinement`。任何一项失败即停止。

## 5. S1：光滑球面短轨迹制造解门禁

四层空间族共同使用 `dt=1e-4`、`T=2e-2`、200 steps；finest 额外使用 `dt=5e-5`、400 steps。不得 adaptive retry 或静默缩短。

每步独立重算并保存：control-area mean radius `sum_i A_i |x_i|/sum_i A_i`、area ratio、volume ratio、registered `gamma A` energy ratio、surface centroid、orientation、triangle quality、minimum face-area ratio、cache residual、`Delta Psi_surface+D_zeta`。mean radius 使用固定制造解中心原点，不用移动质心替代。

### 5.1 解析误差与空间阶

最终时刻比较 `mean_radius/R0`、area ratio、volume ratio、registered energy ratio 与第 1 节解析值。四项误差须随 `h` 非增；非 plateau 的每个相邻解析阶 `p>=0.5`；roundoff plateau=`1e-10`；每项 finest 归一化误差 `<=2e-2`。

### 5.2 相邻网格自收敛

对四项 QoI 计算三组相邻差及第 2 节两个广义阶。差须随 refinement 非增；非 plateau 广义阶均 `>=0.5`；plateau=`1e-10`。禁止节点逐点比较。

### 5.3 时间污染

对 finest 的 `dt` 与 `dt/2` 比较四项最终 QoI。定义 `delta_time=|Q_dt-Q_dt/2|`、`e_space_proxy=|Q_dt/2-Q_exact|`。若二者均 `<=1e-10`，按 plateau 通过；否则必须 `delta_time<=0.25 e_space_proxy`。任何一项失败码为 `failed_time_error_pollution`。

### 5.4 几何、缓存与 coverage 能量

- 所有层/所有步 minimum oriented face alignment `>0`；
- `q=4 sqrt(3) A/(l1^2+l2^2+l3^2)` 的全局最小值 `>=0.05`；
- minimum face-area relative to that run's initial minimum face area `>=1e-4`；
- independent geometry-vs-cache normalized residual `<=1e-12`；
- surface-centroid drift `/R0<=1e-2`；
- 每层 `sum max(0,Delta Psi_surface+D_zeta)/Psi0<=1e-3`。

这里只声明 `surface_tension_only` energy coverage。registered owner 是 `gamma A` 与 `D_zeta`；excluded owners 明列 legacy `0.5 gamma A` cache、membrane elasticity、bending、pressure、contact、active、ECM 和 flow。不得称作 full owned-step total-energy inequality。S1 失败码为 `failed_smooth_surface_short_trajectory_refinement`；失败即冻结 v02 并停止。

## 6. S1 通过后的顺序恢复

只有 D0、D1、S1 全部通过，才依次执行：

1. R1 remesh-on robustness：完全沿用 v01 的 `dt=6.25e-4`、`T=5e-3`、step 2 split、step 3 merge、客观 QoI 差 `<=2e-3`，以及 J1 绝对缺陷/纤维/rebind/事件数阈值；
2. C1 contact：完全沿用 v01 的平面 `z=-0.995`、初始 `z_min=-1`、penetration `<=1e-2`、力/矩残差 `<=1e-10`、声明 coverage 残差 `<=1e-10`；
3. F1 failure persistence：完全沿用 v01 的 `dt=max_double` 首步失败、status=`failed_non_finite_state`、step=`1`、time=`0`、配置/状态 hash 和位置/force/cache 原子不变门禁。

R1、C1 或 F1 任一失败，立即停止并持久化，不进入下一项。v01 的 ShortTrajectoryStatus 固定集合继续有效。

## 7. 阶段结果、交付与 claim guard

v02 阶段结果代码冻结为：

- `passed_frozen_cases`；
- `failed_cube_singularity_diagnostic_regression`；
- `failed_surface_force_directional_derivative`；
- `failed_instantaneous_smooth_surface_refinement`；
- `failed_smooth_surface_short_trajectory_refinement`；
- `failed_time_error_pollution`；
- v01 R1/C1/F1 已冻结 failure status。

交付必须新增且不得覆盖 v01：架构 v15、中文 v02 报告、机器可读 summary、D0/D1/S1/R1/C1/F1 criteria、逐步 CSV、解析误差/相邻自收敛/时间污染表、网格 `h/h_max`、registered/excluded owners 和从冻结提交复算的命令。

即使结果为 `passed_frozen_cases`，唯一允许的结论仍是“X1-K v02 冻结无量纲 case 的短时、声明 coverage 数值门禁通过”。禁止进入 ECM/血流、参数标定、长期稳定、生理预测、完整 cell–ECM/FSI、EFE 双稳态/机械记忆或发育机制 claim，除非收到后续独立授权。
