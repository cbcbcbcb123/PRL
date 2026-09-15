---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V03-DIAGNOSTIC
status: frozen_before_v03_response_generation
frozen_at: 2026-08-03
parent_commit_before_v03_results: abf2ee9c5cb9ff776a57e5d52fcf13a91d482125
cell_engine_commit_before_v03_results: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
preserves_x1_k_status: failed_instantaneous_smooth_surface_refinement
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# X1-K v03 mesh-family asymptotic diagnosis 合同

v03 是有界诊断，不是 X1-K acceptance。它不能覆盖或改写 commits `c640d2a`、`abf2ee9`、v01/v02 原始数据或 Route H Gate A v01=`failed_invalid_numerics`。v02 D1 的四层硬失败测试必须保持原测试名、输入、阈值和失败语义；本任务不修改主离散、真实 surface-tension 力装配、`gamma*A` 注册能量、barycentric dual-area damping 或任何 v02 阈值。

合同在任何 A/B 族数值响应前冻结。按 A 后 B 的顺序执行；A 失败即停止且不运行 B，B 失败即停止。任何失败均不得进入 smooth trajectory、R1、C1 或 F1。

## 1. 公共物理与审计量

- `R0=1`、`gamma=0.02`、`zeta_A=10`；
- 真实公共力入口装配 surface-tension nodal force；
- registered owner：`Psi_surface=gamma*A`；
- excluded legacy cache：`surface_tension_energy_=0.5*gamma*A`；
- 解析瞬时速度：`v_exact=-2gamma/(zeta_A R0)=-0.004`；
- 节点速度：`v_i=F_i/(zeta_A A_i)`，`A_i=(1/3)sum_{f incident i}A_f`；
- 方向导数继续使用 v02 固定方向与 `epsilon=1e-6 h_rms`，只支持该预注册方向的一致性，不声称逐自由度 Hessian/gradient 完整证明。

每层保存：vertex/face 数、`h_min/h_rms/h_max`、方向导数残差、legacy ratio、normal/tangential relative L2、net-force residual、最小三角质量、最小 outward alignment、minimum-face/mean-face area ratio、闭合流形与 Euler proxy、顶点级 valence/symmetry-class 响应分布。

## 2. 实际网格尺度与空间阶

唯一边 chord length 为 `l_e`：

`h_rms=sqrt(sum_e l_e^2/N_edge)/R0`，`h_min=min_e l_e/R0`，`h_max=max_e l_e/R0`。

相邻层误差阶只使用实际 `h_rms`：

`p_ij=log(e_i/e_j)/log(h_i/h_j)`。

禁止假设层间倍率为 2。某一 metric 的四层误差全都 `<=1e-10` 时才记 velocity roundoff plateau；方向导数四层全都 `<=1e-7` 时记 existing consistency plateau。

## 3. Family A：标准 projected icosphere 后续层

使用与 v02 完全相同的 outward-oriented icosphere seed、唯一边 midpoint subdivision 和逐顶点单位球径向投影，但只诊断：

| diagnostic level | standard icosphere level | vertices | triangles |
|---:|---:|---:|---:|
| A0 | 2 | 162 | 320 |
| A1 | 3 | 642 | 1280 |
| A2 | 4 | 2562 | 5120 |
| A3 | 5 | 10242 | 20480 |

目的仅是检验 v02 已观察到的后续渐近段，不改变 v02 levels 0–3 的硬失败事实。

## 4. Family B：固定 SPD 参数化对称破缺族

从标准 projected icosphere levels 1、2、3、4 出发，对每个单位顶点统一施加

`x'=normalize(Mx)`，

其中一次冻结

```
M = [[1.00, 0.10, 0.05],
     [0.10, 1.10, 0.08],
     [0.05, 0.08, 0.90]].
```

`M` 对称且非对角；Sylvester 顺序主子式为 `1.00`、`1.09`、`det(M)=0.97265`，均为正，因此 `M` 正定、可逆且 `det(M)>0`。球面映射 `x -> Mx/|Mx|` 有显式逆 `y -> M^{-1}y/|M^{-1}y|`，故连续映射是保向球面微分同胚。所有层必须使用同一 M，禁止按结果调矩阵。

| diagnostic level | source icosphere level | vertices | triangles |
|---:|---:|---:|---:|
| B0 | 1 | 42 | 80 |
| B1 | 2 | 162 | 320 |
| B2 | 3 | 642 | 1280 |
| B3 | 4 | 2562 | 5120 |

## 5. 网格几何、orientation 与无自交代理

每层必须同时满足：

- 所有顶点 `||x_i||=1`，最大半径偏差 `<=1e-12`；
- 每条无向边恰有两个 incident faces，`V-E+F=2`；
- 所有 face 的 `dot((b-a)x(c-a),(a+b+c)/3)/(||...|| ||...||)>0`；该最小值为 outward alignment，必须 `>0`；
- 总 signed volume 为正；所有面相对原点的 signed tetra contribution 为正；
- 上述 closed-manifold + Euler + strict outward/star-shaped face checks 组成冻结的 no-self-intersection proxy；它不是一般三角网格的完整 triangle-triangle intersection 证明；
- `q=4sqrt(3)A/sum(l^2)` 的最小值 `>=0.05`；
- `minimum_face_area/mean_face_area>=1e-2`；
- `h_max/h_min<=2.0`；
- 四层 `h_rms` 严格递减。

任一项失败即将对应 family 标为 mesh-quality/parameterization failure。

## 6. valence 与离散对称等价类

每个顶点保存 persistent/local index、valence、control-area ratio、normal signed relative error、absolute normal error、tangential relative speed。

离散等价类 signature 只使用响应前几何：

1. vertex valence；
2. `A_i/(A/N_vertex)`；
3. incident chord lengths / `h_rms` 的排序序列。

第 2、3 项先按 `1e-10` absolute quantization 取整，再与 valence 共同构成 class ID；不得用速度/力误差定义 class。逐 valence 和逐 class 报告 count、normal error mean/max/RMS、tangential mean/max/RMS。此处的“轨道”是冻结数值等价类代理，不声称完成群论轨道证明。

诊断预期必须通过数据验证而不是先验写死：标准族早期层可出现大 class/对称轨道；固定 M 族若破缺这些类，应表现为 class count 增多、最大 class size 减小。无论分布如何，global gate 不得按 class 重新加权或删除顶点。

## 7. 两族共同硬诊断判据

每个 family 独立执行原 v02 数值阈值：

- normal 与 tangential 四层误差均非增；
- 所有非 plateau 相邻阶 `p>=0.5`；
- finest normal `<=2e-2` 且 finest tangential `<=2e-2`；
- 方向导数四层进入既有 `1e-7` plateau，或误差非增、所有非 plateau 阶 `p>=0.5` 且 finest `<=1e-6`；
- legacy ratio 相对 `0.5` 的偏差 `<=1e-6`，但 legacy cache 保持 excluded；
- 每层 normalized net force `<=1e-12`；
- 第 5 节全部几何代理通过。

Family A 失败码：`failed_family_A_asymptotic_diagnosis`。Family B 失败码：`failed_family_B_parameterized_diagnosis`。失败报告必须区分：渐近误差、参数化映射、方向导数、质量集总、网格质量或 force balance。

## 8. 结果边界与交付

只有 A、B 全部通过，v03 才可标记 `passed_asymptotic_and_symmetry_broken_support`。该状态只表示两个预注册 mesh family 支持“v02 失败源于前层对称超收敛/制造族选择”的诊断；X1-K 仍为未通过，smooth S1/R1/C1/F1 仍禁止执行。

交付新增且不得覆盖旧版本：架构 v16、中文 v03 诊断报告、机器 summary、逐层 CSV、逐 valence CSV、逐 symmetry-class CSV、首个失败证据（如有）、复算命令、全量回归和远端同步证据。不得触碰 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 或 `scripts/insert_efe_figure_mockups_docx.py`。
