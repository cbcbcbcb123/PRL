---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V04-DIAGNOSTIC
status: frozen_before_v04_red_or_response_generation
frozen_at: 2026-08-03
parent_commit_before_v04: f7186821197c5c5f1c721b177e2b0e7533404419
cell_engine_commit_before_v04: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
preserves_x1_k_status: failed_instantaneous_smooth_surface_refinement
supervision_source: delegated_independent_mentor_review_2026-08-03
---

# X1-K v04 legacy-cache precision repair + Family B 诊断合同

v04 是受控 instrumentation repair 与瞬时 mesh-family 诊断，不是 X1-K acceptance。它不得覆盖 commits `354972f`、`f718682`、v01/v02/v03 原始合同、报告、CSV、summary 或 Route H Gate A v01=`failed_invalid_numerics`。v02 D1 必须保持原测试名、输入、阈值和硬失败语义。v04 禁止运行 smooth S1、R1、C1、F1 或任何时间轨迹。

执行顺序固定为：合同提交并推送 → fork RED → 冻结 pre-fix 输出 → fork 最小 GREEN → fork 回归/提交/推送 → 父仓更新 submodule → 修复后 Family A → 仅当 A 全过才运行 Family B。A 或 B 任一失败立即冻结 v04 失败并停止。

## 1. RED：修复前公共行为

在受控 SimuCell3D fork 的公共 `cell` seam 新增回归，修复前必须同时观察：

- `decltype(std::declval<const cell&>().get_surface_tension_energy())` 是 `float`，而不是 `double`；
- 标准 projected icosphere level 5（10242 vertices / 20480 faces）通过真实 surface-tension 公共力入口后，excluded legacy cache / registered `gamma*A` 相对 `0.5` 的误差大于 `1e-6`；
- 保存 getter 类型、face 数、registered `gamma*A`、legacy cache、ratio、absolute ratio error、方向残差、normal/tangential relative L2、normalized net force 与力缓冲摘要到新增 pre-fix 机器证据；不得用旧 v03 CSV 代替本轮 RED 输出。

RED 测试必须因为缺少所需 double 精度行为而失败，不能通过反向断言把缺陷写成成功。修复前证据单独保存且后续不得覆盖。

## 2. fork 最小 GREEN 边界

唯一允许的生产修改为：

- `surface_tension_energy_` 的存储类型由 `float` 提升为 `double`；
- `get_surface_tension_energy()` 返回类型由 `float` 提升为 `double`；
- reset 使用 double zero，累加保持 double 运算。

legacy 公式必须仍为 `0.5*gamma*A`，并继续是 excluded plotting/instrumentation owner。禁止修改真实 surface-tension nodal force、face gradient、`gamma*A` registered owner、dual-area damping、网格生成、接触/被动/主动装配、v02 evaluator 或任何既有阈值。其他 energy cache 类型与 I/O 聚合类型不在本切片范围内。

## 3. fork GREEN 回归

同一公共行为测试修复后必须同时满足：

- getter 精确返回 `double`；
- 20480-face level-5 legacy ratio 相对 `0.5` 的绝对误差 `<=1e-10`；
- force buffers cleared 状态与修复前一致；
- 每节点力、registered `gamma*A`、方向残差、normal/tangential relative L2 与 normalized net force 相对 `f718682` 冻结基准的归一化差异均 `<=1e-12`；对于零/近零量，使用 `|new-old|/max(1,|old|)`；节点力使用 `||F_new-F_old||_2/max(1,||F_old||_2)`；
- 公式仍由真实 20480 faces 的 `0.5*surface_tension*face_area` 累加产生，不得以测试专用 setter、预填缓存或替代求和绕过真实入口。

若任一力学不变性判据失败，冻结 `failed_legacy_cache_precision_repair_mechanics_changed` 并停止。

## 4. 双仓提交顺序

GREEN 通过后先在 `external/simucell3d` 受控 fork 分支提交并推送，记录旧/新 fork 完整 SHA 与远端同步。随后父仓仅更新 submodule 指针，并加入 v04 Family A/B 诊断代码、机器证据和报告。禁止重写 fork 历史或修改 upstream remote。

## 5. 修复后 Family A

使用 v03 原样冻结的标准 projected icosphere levels 2、3、4、5，`R0=1`、`gamma=0.02`、`zeta_A=10`、真实 surface-tension 公共力入口、registered `Psi=gamma*A`、barycentric dual-area damping、v02 固定方向与 `epsilon=1e-6 h_rms`。所有 v03 阈值原样保持：

- `||x_i||` 最大偏差 `<=1e-12`，闭合二流形、Euler=2、严格 outward/star-shaped、正 signed volume；
- minimum triangle quality `>=0.05`，minimum-face/mean-area `>=1e-2`，`h_max/h_min<=2`，实际 `h_rms` 严格递减；
- normal/tangential 四层非增，非 plateau 相邻阶 `p>=0.5`，finest 两项均 `<=2e-2`；
- 方向残差进入四层 `<=1e-7` consistency plateau，或误差非增、非 plateau 阶 `p>=0.5` 且 finest `<=1e-6`；
- legacy ratio 相对 `0.5` 的偏差 `<=1e-6`，并额外报告实际修复后误差；
- normalized net force 每层 `<=1e-12`。

旧 f718682 的 Family A 失败事实与 CSV 不变。修复后 A 任一门禁失败，状态为 `failed_repaired_family_A_diagnosis`，并停止，不运行 B。

## 6. Family B：v03 冻结参数化族

只有修复后 A 全过，才执行 B。对标准 projected icosphere source levels 1、2、3、4 的每个单位顶点使用同一固定映射 `x'=normalize(Mx)`：

```
M = [[1.00, 0.10, 0.05],
     [0.10, 1.10, 0.08],
     [0.05, 0.08, 0.90]].
```

`M`、层数、节点、阈值与 v03 完全一致。B 使用与 A 相同的实际 `h`、方向/速度/net-force/mesh/valence/symmetry-class 判据和未重加权 global L2。B 任一门禁失败，状态为 `failed_family_B_parameterized_diagnosis` 并停止。

## 7. 点态风险与 claim guard

无论 A/B 是否通过，都必须保留标准族 12 个 valence-5 extraordinary vertices 的点态 normal error 未收敛事实（v03 约 `0.1345 -> 0.1457`）。Family gate 只检查面积加权 global L2，不能升级为 uniform/pointwise convergence、完整离散证明或动力学有效。交付需为未来轨迹门禁登记 extraordinary-vertex 局部质量/速度审计需求，但 v04 不实现或运行轨迹。

只有修复后 A、B 均通过时，v04 状态才可为 `passed_mesh_family_diagnosis_under_instrumentation_repair`。X1-K 仍未通过；smooth S1/R1/C1/F1、ECM/flow、参数标定、生理与 EFE 机制 claim 均继续禁止。

## 8. 新增交付

不得覆盖旧版本。新增：v04 合同、修复前/后 cache 精度机器证据、A/B 逐层 CSV、逐 valence CSV、逐 symmetry-class CSV、机器 summary、中文报告、全量 parent/fork 测试、strict build、双仓 SHA/远端同步证据和可复算命令。

不得触碰 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 或 `scripts/insert_efe_figure_mockups_docx.py`。
