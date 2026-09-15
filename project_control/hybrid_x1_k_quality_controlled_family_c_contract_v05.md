---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V05-DIAGNOSTIC
status: frozen_before_family_c_red_or_response_generation
frozen_at: 2026-08-03
parent_commit_before_v05: 6552ade6807b5d4753102411781d5e3675f83c82
cell_engine_commit_before_v05: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserves_x1_k_status: failed_instantaneous_smooth_surface_refinement
preserves_v04_status: failed_family_B_parameterized_diagnosis
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# X1-K v05 quality-controlled symmetry-broken Family C 诊断合同

v05 只诊断一个质量受控的对称破缺球面网格族，不是新的 X1-K acceptance，也不运行时间轨迹。它不得覆盖或重写 v01–v04 的合同、代码、原始 CSV、summary、报告与失败语义；尤其保留 v02 D1 硬失败、v04 Family B 的 `h_max/h_min>2.0` 失败、受控 fork `e2ed64a` 以及 Route H Gate A v01=`failed_invalid_numerics`。禁止修改 fork、真实 surface-tension 力、barycentric dual-area damping、legacy cache、registered `gamma*A` owner、既有测试、既有阈值或既有 evaluator。

执行顺序冻结为：提交并推送本合同 → TDD RED → 最小诊断实现 → Family C 四层瞬时响应 → 首个硬门禁失败即停止并冻结 v05 失败；只有全部门禁通过时才生成 `passed_quality_controlled_symmetry_broken_global_L2_diagnosis` 版本包。无论通过或失败，均返回导师等待下一合同，不执行 smooth S1、R1、C1 或 F1。

## 1. Family C 的响应前定义

Family C 使用标准 radially projected icosphere 的 source levels 1、2、3、4。对每个源单位顶点 `x` 一次性使用同一映射

```text
M_C = I + 0.5 (M_B - I)
    = [[1.000, 0.050, 0.025],
       [0.050, 1.050, 0.040],
       [0.025, 0.040, 0.950]],

x' = normalize(M_C x).
```

禁止看 Family C 网格或力学响应后调整矩阵、层数、节点、签名、阈值或删点。

`M_C` 为实对称矩阵。Sylvester 判据的三个顺序主子式预注册为

```text
D1 = 1,
D2 = 1.0475,
D3 = det(M_C) = 0.99296875,
```

均严格为正，因此 `M_C` 为 SPD 且 `det(M_C)>0`。其预计算特征值按升序为

```text
lambda(M_C) = [0.934772496, 0.969099738, 1.096127763],
kappa_2(M_C) = 1.172614478.
```

作为响应前失真减弱证明，`M_C-I=0.5(M_B-I)`，两矩阵共享特征向量，且 `lambda_i(M_C)-1=0.5(lambda_i(M_B)-1)`；因此各主方向相对单位映射的谱偏移精确减半，`||M_C-I||_2=0.096127763`，是 `||M_B-I||_2=0.192255525` 的一半，同时 `kappa_2` 从 Family B 的 `1.371125745` 降至 `1.172614478`。这只证明线性映射的谱失真减弱，不预先宣称归一化后的三角网格满足门禁。

## 2. 不变物理入口与连续参照

四层均使用真实 surface-tension 公共力入口、registered `Psi=gamma*A`、`gamma=0.02`、barycentric dual-area damping `zeta_A=10`、`R0=1` 与解析瞬时速度 `v_n=-2 gamma/(zeta_A R)=-0.004`。有限差分方向与 `epsilon=1e-6 h_rms` 沿用 v02/v03。legacy cache 公式仍为 `0.5*gamma*A` 且仍是 excluded plotting/instrumentation owner；它不得替代 registered owner。

## 3. 原样继承的 v03/v04 门禁

每层与四层族必须满足：

- 最大半径偏差 `<=1e-12`；闭合二流形、Euler characteristic `=2`、正 signed volume、严格 outward/star-shaped，且 no-self-intersection proxy 通过；
- minimum triangle quality `q=4 sqrt(3) A/sum(l_i^2) >=0.05`；minimum-face/mean-area `>=0.01`；`h_max/h_min<=2.0`；实际 `h_rms` 严格递减；
- 方向残差四层均进入 `<=1e-7` consistency plateau，或残差非增、所有非 plateau 相邻阶 `p>=0.5` 且 finest `<=1e-6`；
- legacy cache ratio 相对 `0.5` 的绝对误差 `<=1e-6`，force buffers 全部清空；
- normal 与 tangential area-weighted global relative L2 四层均非增；所有非 plateau 相邻阶 `p>=0.5`；finest 两项均 `<0.02`；
- normalized net force 每层 `<=1e-12`。

实际空间阶必须由相邻层真实 `h_rms` 计算，不假设网格尺度恰好减半。任一旧门禁失败，使用对应的原判据与原阈值冻结 v05 失败，不得放宽。

## 4. 响应前几何对称类门禁

symmetry class 只能由调用真实力入口前的几何与拓扑签名定义；签名不得包含力、速度、误差、能量或任何响应量。沿用既有 geometry-only signature evaluator，不改变量化精度或字段。每层新增硬门禁：

```text
maximum_symmetry_class_size <= 2,
symmetry_class_count >= floor(vertex_count / 2).
```

这只检查离散对称轨道已被打破到至多对映点成对，不等于统计独立性或点态收敛。

## 5. normal error energy 的局部分解

令每节点 barycentric dual control area 为 `A_i`，物理法向速度误差为 `e_i=v_i·n_i-v_exact`，冻结总误差能量

```text
E_total = sum_i A_i e_i^2.
```

对每层保存以下诊断：

- `E_v5`：所有 valence-5 顶点；
- `E_v6`：所有 valence-6 顶点；在闭合 icosphere 拓扑上要求 `E_v5+E_v6` 与 `E_total` 只差浮点舍入；
- `E_v5_closed_one_ring`：valence-5 顶点以及所有与其共享一条边的顶点；这是与前两组重叠的局部风险窗口，不能再与 `E_v5+E_v6` 相加。

每组保存 vertex count、绝对 error energy、占 `E_total` 比例、area-weighted RMS、pointwise maximum `|e_i|/|v_exact|`，并用实际相邻 `h_rms` 保存三段观测阶。观测阶和比例在本诊断中是报告量，不新增事后 acceptance 阈值；所有值必须 finite、非负，分区闭合残差需在 `1e-12*max(1,E_total)` 内。

`E_v5_closed_one_ring` 的面积权重可能随加密衰减，因此其能量下降不能写成 valence-5 点态收敛。报告必须同时保留并解释 valence-5 pointwise maximum；即使所有 global L2 门禁通过，也不得宣称 uniform/pointwise convergence。

## 6. TDD 与停止规则

RED 首先通过公共诊断 seam 断言 Family C 需要但当前尚未暴露的量：每节点实际 `A_i`、物理 `e_i` 和 response-pre valence-5 closed-one-ring membership，以及四层局部分解与对称类硬门禁。RED 必须因这些公共行为缺失而失败。

GREEN 只允许增加上述只读诊断字段、聚合 evaluator、Family C 测试入口与导出器；不允许改变任何既有力学结果或旧测试语义。若 Family C 任一门禁失败，状态冻结为与首个失败判据一致的 `failed_*` 并停止。若全部通过，唯一允许状态为 `passed_quality_controlled_symmetry_broken_global_L2_diagnosis`。X1-K 仍未通过，smooth S1/R1/C1/F1、ECM/flow、参数标定、长期稳定、生理与 EFE 机制 claim 均继续禁止。

## 7. 新增交付与保护边界

不得覆盖旧版本。新增 v05 合同、中文报告、机器 summary、Family C levels/valence/symmetry-class/one-ring CSV、criteria、首个失败记录（若失败）、复算命令、全量 parent/fork 测试、strict build 与双仓 SHA/远端同步证据。

不得触碰既有未跟踪的 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 或 `scripts/insert_efe_figure_mockups_docx.py`。
