---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V01
status: frozen_before_trajectory_results
frozen_at: 2026-08-03
parent_commit_before_results: d32232e8a3338779cf7a08557c0948ca78c14b77
cell_engine_commit_before_results: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# Hybrid X1-K 短轨迹监督验收合同 v01

本合同在查看任何 X1-K trajectory 结果之前冻结。后续不得按响应放宽阈值、缩短终止时刻、删除失败 case，或用 adaptive retry 覆盖首个失败。任一硬门禁失败时，X1-K 以失败状态停止并保留原始时序、配置和首个失败证据。

## 统一无量纲与比较规则

- 长度尺度 `L0 = V0^(1/3)`；若 case 不使用体积，则退化为 `sqrt(A0)`；
- 状态误差为同拓扑、同 persistent vertex ID 的位置 RMS 除以 `L0`；不同空间网格禁止逐节点比较；
- 轴向收缩 `c=(L_axis-L_axis,0)/L_axis,0`；面积比 `A/A0`；体积比 `V/V0`；
- 质心采用面积加权三角形表面质心，漂移除以 `L0`；它不是体积质心；
- 缓存残差由独立三角几何重算与 cell cache 比较；体积比是物理 QoI，不称为 volume error；
- 三角质量 `q=4 sqrt(3) A/(l1^2+l2^2+l3^2)`；定向门禁使用当前 face normal 与该 case 初始同 face normal 的归一化点积，不声称 tetrahedral Jacobian；
- 时间/空间三层自收敛采用 `p=log2(e_coarse/e_fine)`，其中误差为相邻层差；两级差均不超过 `1e-12` 时记为 roundoff plateau，不伪造观测阶；
- 新轨迹一律显式使用 `barycentric_dual_area` 与每面积阻尼系数；禁止调用 legacy uniform-per-vertex 重载。

## J1：X1-J split→merge 加固

沿用 X1-J 的真实闭合表面 split→merge case，但只在新测试/新报告中加固，不修改 X1-J v01 冻结包：

- 初始主动储能必须严格大于 `1.0e-2`；
- 最终主动储能漂移绝对值 `<=1.0e-12`；
- `sum(abs(epsilon_alg)) <=1.0e-12`；
- 相对初始纤维最小对齐 `>=1-1.0e-12`；
- 最大材料点 rebind 误差 `<=1.0e-12`；
- 事件计数必须恰为 1 split、0 swap、1 merge。

账本新增 `sum(abs(inter_event_change))` 与 `max(abs(inter_event_change))`，原 `cumulative_inter_event_stored_energy_change` 明确保留为有符号累计。任何“无抵消”结论必须使用新增绝对指标；原有符号和只作望远镜闭合项。

## T1：固定拓扑主动收缩时间 refinement

| 项目 | 冻结值 |
|---|---|
| 几何 | 8 vertices / 12 triangles 闭合心肌测试表面 |
| 力学 coverage | 主动收缩储能；不执行被动、接触、ECM、流体 |
| activation | `alpha=0.05`, `alpha_dot=0`，全程固定 |
| active stiffness | `10` |
| damping | barycentric dual area, `zeta_A=10` |
| final time | `T=0.02` |
| levels | `dt={0.0025,0.00125,0.000625}`；steps `{8,16,32}` |

硬门禁：

- 状态 RMS、轴长/收缩、面积比、体积比、主动储能的相邻层误差均须单调自收敛或进入 `1e-12` roundoff plateau；非 plateau 的观测阶 `p>=0.5`；
- fine-vs-medium 归一化误差：状态与每个客观 QoI 均 `<=2.0e-3`；
- 每步面积、体积、表面质心 cache 的独立归一化残差 `<=1.0e-12`；
- 最小定向点积 `>0`，最小三角质量 `>=0.05`，最小 face area 相对初始最小 face area 比 `>=1.0e-4`；
- 表面质心总漂移 `/L0 <=1.0e-2`；体积比仅要求保持有限正值并落在 `[0.5,1.5]`，该范围是几何 sanity gate，不解释为不可压误差；
- 能量 coverage 为 `active_contraction_only`，逐步检查 `DeltaPsi_active + D_zeta - W_control <= epsilon_num`；其中 `W_control=dt*P_active`；三层累计正残差除以初始主动能量，coarse `<=5.0e-3`，且每次 dt 对半至少缩小 `1.5` 倍。

## S1：固定拓扑表面张力空间 refinement

| 项目 | 冻结值 |
|---|---|
| 几何 | 几何等价单位立方体表面；coarse/base/fine=`8/12`, `26/48`, `98/192` vertices/triangles |
| coverage | 被动表面张力能 `Psi_surface=gamma A`；无 active/contact/ECM/flow |
| surface tension | `gamma=0.02` |
| damping | barycentric dual area, `zeta_A=10` |
| time | `dt=1.0e-4`, `T=2.0e-3`, 20 steps |

不同网格仅比较面积比、体积比、注册表面能比、归一化表面质心漂移和三角质量，不比较节点。相邻网格 QoI 差必须单调自收敛或进入 `1e-10` roundoff plateau；非 plateau 观测阶 `p>=0.25`；fine-vs-base 各 QoI 归一化差 `<=2.0e-2`。几何/cache/定向门禁沿用 T1。逐步 coverage 能量残差 `DeltaPsi_surface + D_zeta` 的累计正值除以初始注册能量必须 `<=1.0e-3`。

## R1：remesh-on robustness

使用与固定拓扑 baseline 相同的单细胞主动 case，`dt=6.25e-4`、`T=5.0e-3`、8 steps；在预注册 step 2 做真实 split，step 3 做对应 merge，不 adaptive remesh。固定拓扑与 remesh-on 分别运行并只比较轴长、面积比、体积比和主动储能，所有归一化差 `<=2.0e-3`。remesh 账本同时执行 J1 的绝对缺陷、纤维、rebind 与事件计数门禁。

## C1：独立短接触 case

- 静态平面盒体顶面 `z_plane=-0.995`，目标细胞初始最低点 `z_min=-1.0`；
- 几何 signed gap `g=z_min-z_plane`，penetration=`max(0,-g)`；该定义仅适用于本冻结平面 case；
- active=0、passive=0，接触作为外部功端口；barycentric dual-area `zeta_A=10`；`dt=1.0e-4`、`T=1.0e-3`；
- 每步 penetration `<=1.0e-2`，作用反作用净力及净矩残差各 `<=1.0e-10`；
- coverage 能量门禁为 `DeltaPsi_active + D_zeta - W_contact <=1.0e-10`，其中 active energy 恒为零；接触势能未注册，不宣称接触总势能不等式。

## F1：失败持久化与原子性

在 T1 同一初态上以有限但极大的 `dt=max_double` 触发首步非有限候选状态。冻结预期：

- status=`failed_non_finite_state`，first failure step=`1`，time before failure=`0`；
- 不 retry、不缩步；reason 原样持久化；配置 hash、失败前/失败后状态 hash 必须存在且相等；
- 位置、force buffer、area/volume/centroid cache 均与失败前一致；
- 支持的固定失败码：`passed`、`failed_invalid_configuration`、`failed_non_finite_state`、`failed_degenerate_or_flipped_surface`、`failed_penetration_limit`、`failed_energy_gate`、`failed_refinement_gate`、`failed_step_exception`。

## 交付与 claim guard

交付必须包含架构 v14、中文报告、机器可读 summary、逐步 CSV 原始时序、阈值/逐项判据结果与可复算命令。Route H Gate A v01 保持 `failed_invalid_numerics`。即使全部通过，唯一允许的结论也是“上述冻结无量纲 case 的短时、声明 coverage 数值门禁通过”；不得升级为长期稳定、生理有效、完整 cell–ECM/FSI、EFE 双稳态/机械记忆或发育机制成立。
