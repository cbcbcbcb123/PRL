---
report_id: REPORT-PRL-HYBRID-X1-K-FAILURE-V01
status: failed_spatial_refinement_nonconvergent_area_energy
failed_at: 2026-08-03
parent_branch: codex/simucell3d-hybrid-feasibility
acceptance_contract: CONTRACT-PRL-HYBRID-X1-K-V01
acceptance_contract_commit: 1241d80
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
result_id: PRL-HYBRID-X1-K-SHORT-TRAJECTORY-V01
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# Hybrid X1-K 短轨迹失败报告 v01

## 结论

X1-K 未通过。所有 case、阈值、失败码和比较量已在任何 trajectory 结果产生前提交到远端（commit `1241d80`）。T1 固定拓扑主动时间 refinement 通过，但 S1 表面张力空间 refinement 的 area ratio 和注册表面能 ratio 出现约负一阶行为，触发硬门禁。执行已原样停止，没有调阈值、缩短 `T`、改变 `dt`、删除 QoI 或进入 R1/C1/F1。

## TDD 执行证据

1. split→merge 加固 RED 仅因 rebind gate 尚不存在而编译失败；GREEN 后非零初始能量、最终漂移、绝对算法缺陷、纤维和 rebind 联合通过。
2. inter-event RED 仅因 absolute/max 指标尚不存在而编译失败；GREEN 后有符号和虽抵消，绝对累计与单事件最大值仍拒绝错误结论。
3. T1 tracer RED 仅因 `short_trajectory.hpp` 尚不存在而失败；GREEN 后生成逐步几何、QoI、coverage 能量和 hash 审计。
4. T1 refinement RED 仅因三层比较接口尚不存在而失败；GREEN 后状态与轴长、收缩、面积比、体积比、主动能量全部通过冻结门禁。
5. S1 tracer RED 仅因表面张力 trajectory 接口尚不存在而失败；单层 GREEN 后能量、质量、定向和 cache 均有效。
6. S1 refinement RED 仅因客观 QoI 空间比较接口尚不存在而失败；实现固定门禁后得到科学性 RED：area/registered-energy 不自收敛。按照监督合同，此 RED 被冻结为 X1-K 终止状态，不继续“修绿”。

## T1 通过结果

| 比较量 | coarse-medium error | medium-fine error | observed order | gate |
|---|---:|---:|---:|---|
| state RMS / `L0` | `1.6332467973203779e-8` | `8.1637057497523182e-9` | `1.0004467223827034` | passed |
| axis length | — | — | `1.0004466394371907` | passed |
| contraction | — | — | `1.0004466394354372` | passed |
| area ratio | — | — | `1.000446737190632` | passed |
| volume ratio | — | — | `1.0004466742744309` | passed |
| registered active energy | — | — | `1.0004457665779467` | passed |

三层累计正能量残差/初始主动能量为 `3.2857097751376663e-6`、`1.6423405646888264e-6`、`8.2104176026394916e-7`，满足 coarse `<=5e-3` 且每次至少缩小 1.5 倍。`W_F=D_zeta` 未被用作该结论；门禁使用了独立 step-after 主动能量形成的 `DeltaPsi_active + D_zeta - W_control`。

## S1 硬失败

冻结设置：单位 cube，midpoint coarse/base/fine=`8/12`,`26/48`,`98/192`，`gamma=0.02`，`zeta_A=10`，`dt=1e-4`，`T=0.002`。逐步原始值见 `results/hybrid/x1_k_short_trajectory_v01/s1_spatial_timeseries.csv`。

| 判据 | 冻结阈值 | 观测 | 结果 |
|---|---:|---:|---|
| area monotonic/order | `p>=0.25` | `p=-0.99994175072770464` | failed |
| registered-energy monotonic/order | `p>=0.25` | `p=-0.99994175072770464` | failed |
| volume monotonic/order | `p>=0.25` | `p=0.9994846234517949` | passed |
| base-fine objective error | `<=2e-2` | max `3.1998220180295966e-5` | passed |
| coverage energy residual | `<=1e-3` | max `1.5200192547477984e-10` | passed |
| minimum triangle quality | `>=0.05` | `0.86599768533958354` | passed |
| orientation | `>0` | min `0.99999999590388045` | passed |
| cache residual | `<=1e-12` | `2.4825341532472731e-16` | passed |

失败不是“数值发散到无穷”或几何损坏，而是对 refinement 更敏感的系统性 area/energy 速率变化。coarse→base 的最终 area-ratio 差为 `1.599975607236015e-5`，base→fine 为 `3.1998220180295966e-5`，后者约为前者两倍。

## 诊断性解释

当前 `cell::apply_surface_tension_and_membrane_elasticity` 对每个三角形施加 `-gamma * grad(A_face)`；X1-I 阻尼则是 `zeta_i=zeta_A A_i`。对非光滑 cube 棱边，surface-tension 面积梯度形成棱边集中力。midpoint refinement 下棱边节点力典型按 `h` 变化，而顶点双面积按 `h^2` 变化，因此速度尺度可随 `1/h` 增长。最终 area/energy 变化量随 refinement 约翻倍，与观测负一阶相符。

这是基于实现和缩放的推断。下一版若获授权，应先决定是将 S1 改为光滑等价几何，还是为非光滑棱边建立与线集中力匹配的阻尼/控制度量；不能直接改门槛。

## 验证状态

| 检查 | 结果 |
|---|---:|
| parent C++ CTest | `38/39 passed`; S1 gate intentionally failed and persisted |
| owned parent core `-Wall -Wextra -Wpedantic -Werror` | `14/14 passed` |
| parent Python pytest | `63/63 passed` |
| tracked Python Ruff | all checks passed |
| S1 raw timeseries | `63` rows; coarse/base/fine each `21` rows |
| fork | no X1-K modification; remains at independently verified `2d4b218` |
| Route H Gate A v01 | unchanged `failed_invalid_numerics` |

## 停止与 claim guard

R1、C1、F1 均标记 `not_executed_due_to_prior_hard_gate_failure`。本包不允许“X1-K 部分通过”被简写为“短轨迹稳定”；只允许分别陈述 T1 通过与 S1 失败。ECM/血流长耦合、参数标定和论文机制 claim 继续禁止。
