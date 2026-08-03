---
architecture_id: PRL-HYBRID-ARCH-V15
status: frozen_x1_k_v02_failed_instantaneous_velocity_refinement
contract: CONTRACT-PRL-HYBRID-X1-K-V02
parent_contract_commit: c640d2a06c3e8642782bf8a258ca741741d8bae7
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
---

# Hybrid architecture v15 — smooth-surface manufactured gate failure

## 冻结边界

v15 不覆盖 v14，也不修改 X1-K v01 cube 原始失败包。v02 将 cube 重新分类为“非光滑奇异族诊断回归”，并在真实 upstream surface-tension force 上新增两个 PRL-owned 审计 seam：

1. `gamma*A` 有限差分方向导数与 `-sum(F_i dot d_i)` 的一致性；
2. `v_i=F_i/(zeta_A A_i)` 相对解析球面速度的法向 L2、切向 L2 与净力残差。

legacy `surface_tension_energy_=0.5*gamma*A` 只被读取和报告，始终是 excluded plotting cache；注册能量 owner 仍为与实际力一致的 `gamma*A`。

## 已执行顺序

| 顺序 | case | 状态 |
|---:|---|---|
| 1 | D0 cube singular-family diagnostic | passed |
| 2 | D1 `gamma*A` directional derivative | passed, four-level consistency plateau |
| 3 | D1 instantaneous normal/tangential velocity | `failed_instantaneous_smooth_surface_refinement` |
| 4 | smooth S1 trajectory | not executed |
| 5 | R1 remesh-on | not executed |
| 6 | C1 contact | not executed |
| 7 | F1 persistence | not executed |

## 首个失败的结构

规则正二十面体 level 0 在径向缩放方向具有完全对称性：所有顶点控制面积相同、节点面积梯度力同为径向。由全局齐次关系 `sum_i grad_i(A) dot x_i=2A`，逐点质量集总恰好给出 `v_n=-2gamma/zeta_A`，因此 coarse 法向误差约为机器精度。subdivision 后出现不同顶点轨道/局部几何，误差先从零重新出现，再在 level 1→2→3 正常下降。

观测到 normal L2 为 `1.40e-16, 5.738e-2, 3.356e-2, 1.740e-2`；后两对实际 `h` 阶为 `0.806`、`0.957`。tangential L2 为 `2.01e-16, 2.50e-16, 1.088e-2, 4.857e-3`；最后一对阶为 `1.175`。finest 阈值均通过，但合同要求四层误差非增，因此 D1 整体必须失败。

这属于制造网格族的 symmetry-induced coarse superconvergence / geometry-approximation gate 设计问题，并与 barycentric mass lumping 的对称消去共同出现。方向导数 gate 已通过，故当前证据不支持把失败归因为 `gamma*A` force gradient 错误；该 gate 为瞬时量，时间污染尚未进入。

## 保持不变的系统边界

- 高性能 C++ cell engine 与 Python 科研层分工不变；
- upstream/controlled fork 本阶段无修改；
- Route H Gate A v01 仍为 `failed_invalid_numerics`；
- ECM/flow、EFE 双稳态/记忆、参数标定和生理 claim 均未授权；
- X1-K v02 不得标记为 `passed_frozen_cases`。
