---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V07-DIAGNOSIS
status: frozen_before_v07_numerical_response
frozen_at: 2026-08-03
parent_commit_before_v07: b66a43781c48ffc7555ef7d16701e76004406751
cell_engine_commit_before_v07: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserves_x1_k_status: failed_v06_family_c_smooth_short_trajectory
preserves_v06_status: failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# X1-K v07 Family C mean-radius 结构恒等式与时间底噪诊断合同

v07 只诊断 Family C 初始球面上的面积二次齐次恒等式、control-area mean-radius 的初始导数，以及两层网格上的短时一阶时间行为。它不是 X1-K 总验收，不授权 R1、C1、F1、remesh/contact、ECM/flow 长耦合、参数标定或论文机制 claim。

不得覆盖或改写 v01–v06 的合同、原始结果、报告、阈值与失败语义。Route H Gate A v01 始终保持 `failed_invalid_numerics`；v06 始终保持 `failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic`，其 mean-radius 跨空间网格的旧解析单调/阶门禁只能复报，绝不能在 v07 中重判。

受控 fork 固定为 `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`。禁止修改 fork、真实 public surface-tension force、barycentric dual-area damping、registered `gamma*A` owner、legacy cache 公式或任何既有阈值。v07 只允许在 PRL-owned audit/test/export/docs/results 层增加只读审计与诊断。

执行顺序冻结为：本合同单独提交并推送 → TDD RED → 最小结构审计 seam GREEN → 结构恒等式四层正式响应 → 最小时间诊断 seam RED/GREEN → 两层八条时间轨迹作为一个不可调整响应批次 → 预注册门禁 → 冻结通过或首失败。合同提交前不得产生任何 v07 数值响应；任何门禁失败均不得调 `dt`、`T`、矩阵、网格、阈值或 owner。

## 1. 固定模型与 coverage

沿用 v05/v06 Family C：

```text
M_C = [[1.000, 0.050, 0.025],
       [0.050, 1.050, 0.040],
       [0.025, 0.040, 0.950]],
x' = normalize(M_C x),
source levels = 1,2,3,4,
R0 = 1,
gamma = 0.02,
zeta_A = 10.
```

全部网格初始顶点投影在同一 `R0` 球面，固定拓扑。能量 coverage 仍严格限定为 `surface_tension_only`：registered 为 `Psi=gamma*A` 与轨迹中的 `D_zeta`；excluded 为 legacy `0.5*gamma*A` cache、membrane、bending、pressure、contact、active、ECM 和 flow。

## 2. Euler 二次齐次结构推导

对固定拓扑三角表面，将全部顶点按 `x_i -> lambda x_i` 一致缩放。每个三角形面积和总面积满足

```text
A(lambda x) = lambda^2 A(x).
```

Euler 齐次函数定理给出

```text
sum_i x_i · partial(A)/partial(x_i) = 2 A.
```

真实 public surface-tension force 使用 `Psi=gamma*A`，故

```text
F_i = -partial(gamma A)/partial(x_i),
sum_i x_i · F_i = -2 gamma A.
```

每个三角形面积按 `A_f/3` 分配给三个顶点，因此独立 barycentric dual area 满足精确离散分配关系

```text
A = sum_f A_f = sum_i A_i.
```

结构残差冻结为

```text
r_H = |sum_i x_i·F_i + 2 gamma A|/(2 gamma A).
```

该推导适用于固定拓扑面积函数的统一缩放方向；它不等于逐自由度完整方向导数证明，也不允许外推为带其他能量 owner 的总力恒等式。

## 3. 初始 mean-radius 导数的面积权重相消

定义

```text
Rbar = N/A,
N = sum_i A_i r_i,
r_i = |x_i|.
```

在初始投影球面上 `r_i=R0`，故 `N=R0 A`。对任意瞬时速度求导：

```text
dN/dt = R0 dA/dt + sum_i A_i dr_i/dt,
d(Rbar)/dt
 = [(R0 dA/dt + sum_i A_i dr_i/dt)A - R0 A dA/dt]/A^2
 = sum_i A_i dr_i/dt / A.
```

因此只有在所有初始半径相同的这一时刻，面积权重的导数项才相消。取 `n_i=x_i/R0`、`v_i=F_i/(zeta_A A_i)`，则

```text
vbar_r = sum_i A_i(v_i·n_i)/sum_i A_i
       = [sum_i x_i·F_i]/(zeta_A R0 A)
       = -2 gamma/(zeta_A R0).
```

冻结速度残差为

```text
r_v = |vbar_r + 2 gamma/(zeta_A R0)|
      /(2 gamma/(zeta_A R0)).
```

这只是初始等半径球面上的结构恒等式。轨迹离开精确等半径状态后，`r_i` 不再统一，权重导数项一般不相消；不得将近机器精度写成一般非球网格或全轨迹解析恒等式。

## 4. 四层初始结构审计

对 Family C source levels `1,2,3,4`，在任何位移响应前，通过真实 public surface-tension force 和独立几何/dual-area 重算保存：

- vertices、faces、实际 `h_rms/R0`；
- `A=sum_f A_f`、`sum_i A_i`、`sum_i A_i/A-1`；
- `sum_i x_i·F_i`、`-2 gamma A`、`r_H`；
- `vbar_r`、解析 `-2 gamma/(zeta_A R0)`、`r_v`；
- normalized net-force residual；
- maximum `||x_i|-R0|/R0`；
- force 调用前后的状态/位置 hash、maximum position displacement；
- 调用后的 force-buffer maximum norm 与 cleared 状态。

四层全部必须满足：

```text
r_H <= 1e-12,
r_v <= 1e-12,
|sum_i A_i/A - 1| <= 1e-12,
normalized net-force residual <= 1e-12,
maximum relative radius deviation <= 1e-12,
maximum position displacement = 0,
state/position hash unchanged,
force buffers cleared exactly.
```

结构审计任一层失败即冻结 v07 失败，不得进入时间响应批次。

## 5. 两层四档时间响应矩阵

仅在四层结构审计全部通过后，固定 source levels `1` 与 `4`，各自从同一 Family C 初始网格独立运行：

| dt | steps | T |
|---:|---:|---:|
| `4e-4` | 50 | `2e-2` |
| `2e-4` | 100 | `2e-2` |
| `1e-4` | 200 | `2e-2` |
| `5e-5` | 400 | `2e-2` |

全部 fixed topology、无 remesh/contact/active、无 retry/adaptation。八条轨迹组成一个响应前冻结的不可调整批次；全部生成后才按 source level `1`、再 source level `4`、最后跨层 Richardson 的顺序评价。

每次运行逐步保存 v06 的完整全局、局部与能量账本：control-area mean radius、area/volume/registered-energy ratio、centroid、orientation、triangle quality、minimum face-area ratio、cache residual、`DeltaPsi+D_zeta`、valence-5/closed-one-ring 径向与边缩放误差、局部质量、normal-error energy fraction/RMS/pointwise maximum。不得减少时序字段。

## 6. 时间差、阶与舍入平台门禁

对每个 source level，将四档最终 mean-radius raw response 按粗到细记为 `Q_0,Q_1,Q_2,Q_3`，定义

```text
D_0 = |Q_0-Q_1|,
D_1 = |Q_1-Q_2|,
D_2 = |Q_2-Q_3|,
p_t,0 = log2(D_0/D_1),
p_t,1 = log2(D_1/D_2).
```

共同 raw 舍入平台预注册为三个 `D_k` 全部 `<=1e-13`。一旦某层进入该共同平台，状态必须冻结为 `failed_time_roundoff_plateau_insufficient_to_estimate_order`；不得跳过阶数、改用部分差分、放宽平台或缩短时程。

非平台时，每层必须同时满足：

```text
D_0 > D_1 > D_2,
0.75 <= p_t,0 <= 1.25,
0.75 <= p_t,1 <= 1.25.
```

首个不满足项按以下失败顺序冻结：共同平台 → `D_k` 非严格递减 → 第一个越界的 `p_t`。

## 7. 一阶 Richardson 门禁

对每个 source level，使用最细两档 `dt=1e-4` 与 `dt/2=5e-5`：

```text
Q_R = 2 Q_dt/2 - Q_dt,
Q_exact = sqrt(1-4 gamma T/zeta_A)/R0.
```

必须满足：

```text
|Q_R(level 1)-Q_exact| <= 1e-10,
|Q_R(level 4)-Q_exact| <= 1e-10,
|Q_R(level 1)-Q_R(level 4)| <= 1e-10.
```

Richardson 只用于本冻结 mean-radius 时间诊断，不得用来重判 v06 的空间解析门禁。

## 8. v06 只读控制项

八条时间轨迹必须继续满足 v06 已冻结的逐步控制阈值：

```text
minimum oriented alignment > 0,
minimum global triangle quality >= 0.05,
minimum face-area/current-run-initial-minimum >= 1e-4,
maximum cache residual <= 1e-12,
maximum surface-centroid drift/R0 <= 1e-2,
sum positive(DeltaPsi+D_zeta)/Psi0 <= 1e-3,
maximum V5/closed-ring radial excursion error <= 0.25,
maximum V5/closed-ring radial error/h_i(0) <= 5e-4,
maximum closed-ring edge scaling error <= 5e-4,
minimum closed-ring local quality/current-run-initial-local-quality >= 0.90,
all diagnostic force buffers cleared.
```

area、volume 与 registered-energy ratio 的最终解析误差、四档时间差和时序继续原样报告，但 v07 不为它们新建时间阶 acceptance。v06 mean-radius 的四层空间误差、负阶和失败语义必须在 summary/report 中复报，不进入 v07 pass 判定。

任何只读控制回归失败均冻结为 `failed_v06_readonly_control_regression`。

## 9. TDD、状态与交付

TDD 第一轮 tracer 先要求当前尚不存在的公开只读结构审计行为，并必须因缺失 public seam 而 RED；最小 GREEN 后只运行单层结构 tracer。第二轮再要求当前尚不存在的两层四档时间聚合与 gate evaluator，并必须 RED；最小 GREEN 后才允许生成正式时间响应。不得测试私有 helper 或为测试修改主力学路径。

全部新结构、时间、Richardson 与 v06 只读控制门禁通过时，唯一允许状态为

```text
passed_structural_mean_radius_identity_and_time_floor_diagnosis
```

它不是 X1-K pass，也不授权 R1/C1/F1。任一门禁失败则冻结明确首失败、全部已生成原始响应及未执行项并返回导师。

新增且不覆盖旧版的交付包括：v07 合同、架构、中文推导/诊断报告、机器 summary/criteria、四层结构审计 CSV、两层八条逐步全局/局部/能量 CSV、时间差/阶/Richardson CSV、TDD RED/GREEN 证据、首失败或通过证据、复算命令、完整 parent/fork/strict/Python/Ruff 结果及真实远端同步证据。

不得触碰既有未跟踪的 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 或 `scripts/insert_efe_figure_mockups_docx.py`。
