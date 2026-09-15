---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V08-ADJUDICATION
status: frozen_before_v08_acceptance_output
frozen_at: 2026-08-03
parent_commit_before_v08: 49215095f6aa94966af2131979bb98b999aeb28a
cell_engine_commit_before_v08: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
supervision_source: delegated_independent_mentor_review_2026-08-03
x1_k_passed: false
downstream_authorized: false
---

# X1-K v08 D1/S1 固定拓扑修订验收综合合同

## 0. 任务边界与不可改写历史

v08 是对 v05、v06、v07 已冻结原始 CSV 的只读证据裁决，不生成新物理轨迹，不修改 C++ 主离散、受控 SimuCell3D fork、surface-tension force、barycentric dual-area damping、registered `gamma*A` owner、legacy cache、已有 evaluator、测试或阈值。

v08 建立一个新的 acceptance role：

- D1 使用 v05 已预注册的 Family C area-weighted global-L2 网格族语义；
- S1 将 mean radius 从“跨 `h` 解析空间阶”改列为“初始结构恒等式 + 两层时间一致性 QoI”；
- area、volume、registered-energy、时间污染、逐步几何、缓存、能量和 extraordinary-vertex 局部门禁保持原阈值；
- v06 mean-radius 空间门禁的失败仍是历史事实，不在 v08 中回写、禁用、删除或改判。

下列历史状态永久保留：

```text
Route H Gate A v01 = failed_invalid_numerics
v02 D1 = failed_instantaneous_smooth_surface_refinement
v04 Family B = failed_family_B_parameterized_diagnosis
v06 S1 mean-radius spatial gate
  = failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic
v07 = passed_structural_mean_radius_identity_and_time_floor_diagnosis
X1-K = not passed
```

v01–v07 的合同、结果、报告、阈值、失败测试和失败语义不得覆盖、删除、禁用、`xfail` 或改判。完整 parent CTest 必须继续显示 v02、v04、v06 三个历史冻结失败。

## 1. 执行顺序与 TDD

严格顺序为：本合同单独提交并推送 → TDD RED → 最小 fail-closed GREEN → 原始证据完整性裁决 → revised D1 → revised S1 → 权限/历史状态裁决 → 冻结结果包 → 完整回归与同步。

合同提交前不得生成 v08 acceptance 输出。TDD 的第一个外部可观察行为是：当任一 required raw evidence 缺失时，公共 Python adjudicator 必须抛出带首个失败文件的 `EvidenceIntegrityError`，而不是返回部分通过、信任 summary 或继续科学裁决。RED 必须因该公开 adjudicator 尚不存在而失败。最小 GREEN 只实现 manifest 与缺失证据 fail-closed；下一行为测试再要求完整原始证据复算和修订裁决。

只允许新增 PRL-owned 合同、只读 Python adjudicator、TDD 测试、导出脚本、results、docs 和报告。不得修改 `cpp/`、`external/simucell3d/`、既有 v01–v07 文件或已有测试。

## 2. 冻结原始证据清单

SHA-256 为当前受控工作树文件的原始字节摘要；`rows` 不含 header。每个文件的 header 字段名、顺序和数量必须与 `source_commit` 中该路径的 literal CSV header 完全一致，并在 v08 provenance manifest 中记录完整字段数组。任何文件缺失、SHA-256、行数、schema 或来源提交不符均 fail closed。

### v05，source commit `51d606b1165c3c0ca0839e59aebce3e1a89ca640`

| path（前缀 `results/hybrid/x1_k_mesh_family_v05/`） | rows | SHA-256 |
|---|---:|---|
| `family_c_levels.csv` | 4 | `8cecf41ecef3e9a14c24d41f64c86e19cc78eab65182870b0d3ec8d1524d9eec` |
| `criteria.csv` | 23 | `09bbbb1f4934a483c5074fc3c920588b42278e6567811337cb99ef854eacd5e1` |
| `family_c_error_regions.csv` | 12 | `23f2990fd188c42ce85ef03ec1285e9f55f81fcb982786f23da23b630d087a07` |
| `family_c_valence.csv` | 8 | `9e2cc640cc358d78403b43897cdc6cdefbdbe86a3d88d2b3f25f214d56bb8bbb` |
| `family_c_valence5_one_ring.csv` | 4 | `0b529e924766d9c2310628769cdef74f82245d1fa1977b858f817a5558c52de1` |
| `family_c_error_energy_orders.csv` | 3 | `a472eb71b98bc2f89ba0a65d4b1f9ba40937472664cc28bf41fa9b3bb2d794ab` |
| `family_c_symmetry_classes.csv` | 1704 | `c841a56700db051c5b5b230532c4694f1e1c77491a0a0db1bc3dafd07c2127a9` |
| `family_c_symmetry_gate.csv` | 4 | `a5e9fc8c61b6d0e59959bbe7782fd4a08a8752ba0c408a41d8951950b3cecffd` |

### v06，source commit `eb3c97339580e3d2e0f565e47b9b78dab292046e`

| path（前缀 `results/hybrid/x1_k_family_c_trajectory_v06/`） | rows | SHA-256 |
|---|---:|---|
| `final_qoi_gate.csv` | 4 | `6857f1f6d9f415ee17d7c829e98aa835f4d78bf4739b4dd5a83933700ae67699` |
| `time_pollution.csv` | 4 | `9b93ad99a1b0b4843f2af45938a36c6dbad60ed33759f6245358a76a3fd931e0` |
| `raw_global_gate.csv` | 22 | `3f6bb4f9001d784d5be73812f7bf54f0b8db2e64e852abac3f7cdd1d88d5dcea` |
| `family_c_level_1_steps.csv` | 201 | `265783f2784e87aa688047f8169e26d4688443c46c30615a493220431b7cc53f` |
| `family_c_level_2_steps.csv` | 201 | `9b989dbba0d1b9324b69f050c9f5b00b1cc0f371285177be20c320eea0582f46` |
| `family_c_level_3_steps.csv` | 201 | `9f62870379142191123bb36396b869af1953c3b9372b8a7ca2992f6ef5005de1` |
| `family_c_level_4_steps.csv` | 201 | `28ff835aefda74346f3a7fdb203da567fad5c4089e7d53dc16c9346365792690` |
| `family_c_level_4_dt_half_steps.csv` | 401 | `f8094a551499093745172c2e054c72ec3bdebdb346b4f38f97ab35043e15e21d` |
| `local_step_metrics.csv` | 1205 | `76315a41a338c017b676f1149dfd8f8b34ea87ff443ade7267f1192c585e28c8` |
| `energy_ledger.csv` | 1205 | `9731e54fce82ff9946ebb78decc52f5914f87a221a7ea7c804f0c98b67c8c68e` |

### v07，source commit `f4df24c840f357fc06a45c4406bc55b9817199b9`

| path（前缀 `results/hybrid/x1_k_mean_radius_v07/`） | rows | SHA-256 |
|---|---:|---|
| `structural_identity.csv` | 4 | `8c8e2c3de7c8ff878e1b4758113fe8825f51f2cf1484f885e5f5ac114cd74f05` |
| `time_diagnosis.csv` | 2 | `927773dfdde391b12938b36d1b9b02a3b9002b3b6b8e1266dacb95a5f81d6c3d` |
| `global_step_metrics.csv` | 1508 | `dd2c1d1430cd459f7fdd1eeed8435e55818d2983ebfaba200cc87f973c628aab` |
| `local_step_metrics.csv` | 1508 | `e20a8ce622dc46e90153a734fa6ccf6baa891d5a4945aa0e92995a43394aa128` |
| `energy_ledger.csv` | 1508 | `f345a6451c6dd065665a0c3c9729a7d255f197807eb45cc3ed4d569a739890be` |

## 3. Fail-closed 完整性与复算规则

所有 required CSV 必须通过以下顺序检查：

1. regular file 存在；
2. 原始字节 SHA-256 等于冻结值；
3. UTF-8、CSV parse、exact header/schema 和数据行数正确；
4. 任意 cell 不得出现 `NaN`、`Inf`、`Infinity` 或其带符号/大小写变体；
5. 冻结的 family、source level、QoI、run、`dt`、step、time 和 region keys 唯一且闭合；
6. v06 的五条 run 与 v07 的八条 run 必须有连续 `step=0..N`、`time=step*dt`、固定初始 `h` 和共同 `T=0.02`；
7. global/local/energy 的 `(family/run,source_level,dt,step,time)` keys 必须完全相等；
8. 每条能量 run 必须从 step 0 重算 `delta_psi`、`delta_psi+D_zeta`、positive residual 与有序 cumulative positive residual；绝对/相对复算容差冻结为 `1e-12*max(1,|Psi|)`；
9. reported gate/criteria 字段只能作交叉核对，科学判定必须由原始数值重新计算，不能信任 `summary.json` 或 CSV 的 `passed` 自报。

首个失败按上述顺序冻结为 `failed_evidence_integrity_<reason>`，并记录 path、source commit、expected/observed hash、rows、schema 或 key/ledger 摘要；不得继续 D1/S1。

## 4. Revised D1 acceptance

仅使用 v05 Family C。采用实际 `h_rms`，不假设层间倍率 2。全部复算：

```text
h_1 > h_2 > h_3 > h_4 > 0
minimum triangle quality >= 0.05
minimum face/mean area ratio >= 0.01
each h_max/h_min <= 2.0
maximum symmetry class size <= 2
symmetry class count >= floor(N_vertex/2)
maximum directional residual <= 1e-7
maximum |legacy cache ratio - 0.5| <= 1e-6
maximum normalized net force <= 1e-12
normal area-weighted relative L2: four levels nonincreasing
tangential area-weighted relative L2: four levels nonincreasing
p = log(e_coarse/e_fine)/log(h_coarse/h_fine) >= 0.5
finest normal error < 0.02
finest tangential error < 0.02
```

error-region、valence、closed-one-ring 与 error-energy-order CSV 必须闭合：valence-5 与 valence-6 顶点数分区覆盖全部顶点；两区 error energy 之和与 total 在 `1e-12*max(1,E_total)` 内闭合；registered regions 的能量、控制面积和统计量有限且非负。

limitation 是 acceptance 的强制组成部分：四层 valence-5 `maximum_pointwise_relative_error` 必须原样报告；`pointwise_convergence_claim_allowed=false`、`uniform_convergence_claim_allowed=false`。即使 global L2 门禁通过，也不得把控制面积缩小写成点态速度改善。

全部通过时 revised D1 为 `passed_revised_family_c_global_l2_d1`；任一失败则冻结首个 D1 gate 并停止。

## 5. Revised S1 acceptance

### 5.1 mean radius：结构恒等式 + 时间一致性

从 v07 `structural_identity.csv` 的 primitive fields 重算四层：

```text
r_H = |homogeneity_force_contraction
       - exact_homogeneity_force_contraction|
      / |exact_homogeneity_force_contraction| <= 1e-12
r_v = |mean_radial_velocity-exact_mean_radial_velocity|
      / |exact_mean_radial_velocity| <= 1e-12
```

同时要求 `|sum(A_i)/A-1|<=1e-12`、net-force residual `<=1e-12`、radius inconsistency `<=1e-12`、position displacement/force buffer norm 为 0、position/state hashes 不变、force buffers cleared。

从 v07 global raw steps 与 `time_diagnosis.csv` 交叉重算 source levels 1、4 的四档最终 mean-radius responses：

```text
D_k = |Q_dt-Q_dt/2|, D_0>D_1>D_2
p_t = log2(D_k/D_k+1) in [0.75,1.25]
Q_R = 2 Q_5e-5 - Q_1e-4
|Q_R-Q_exact| <= 1e-10 for each level
|Q_R(level 1)-Q_R(level 4)| <= 1e-10
```

若某层三个 `D_k` 全部 `<=1e-13`，必须失败为不足以估阶。v06 mean-radius 的四层 excursion-normalized errors 与负空间阶必须从 `final_qoi_gate.csv` 复报为 `historical_failed_not_rejudged`，不得进入 revised S1 pass 逻辑。

### 5.2 area、volume、registered energy

从 v06 五条 raw step CSV 取得 step-0 与最终值，与 `final_qoi_gate.csv` 交叉核对，并对 `area_ratio`、`volume_ratio`、`energy_ratio` 分别重算：

```text
e_l = |Q_l(T)-Q_exact|/max(|Q_exact-Q_l(0)|,1e-12)
four e_l nonincreasing
all actual-h adjacent analytic orders >= 0.5
finest e_l < 0.02
d_l = |Q_l(T)-Q_l+1(T)|/max(|Q_exact-Q_l(0)|,1e-12)
three d_l nonincreasing
two generalized actual-h orders >= 0.5
```

广义阶使用冻结方程

```text
d_coarse/d_fine
 = (h_coarse^p-h_middle^p)/(h_middle^p-h_fine^p),
p in [0,16], bisection tolerance 1e-12.
```

不得使用 reported `passed` 代替上述复算。

### 5.3 时间、逐步几何、能量与局部风险

area、volume、energy 使用 v06 finest `dt=1e-4` 与 `dt/2=5e-5`：

```text
raw plateau: delta_time<=1e-10 and space_proxy<=1e-10
otherwise delta_time <= 0.25*space_proxy
```

mean radius 只使用 5.1 的 v07 时间门禁，不使用 v06 spatial gate。

v06 五条和 v07 八条 raw runs 均复算并满足：

```text
minimum oriented alignment > 0
minimum triangle quality >= 0.05
minimum face-area/current-run-initial-minimum >= 1e-4
maximum cache residual <= 1e-12
maximum surface-centroid drift/R0 <= 1e-2
sum positive(DeltaPsi+D_zeta)/Psi0 <= 1e-3
maximum V5/closed-ring radial excursion error <= 0.25
maximum V5/closed-ring radial error/h_i(0) <= 5e-4
maximum closed-ring edge scaling error <= 5e-4
minimum closed-ring local quality/current-run-initial-quality >= 0.90
all force_buffers_cleared = true
```

能量 coverage 只能写为 `surface_tension_only`；registered 为 `gamma*A` 与 `D_zeta`；legacy `0.5*gamma*A` cache、membrane、bending、pressure、contact、active、ECM 和 flow 全部 excluded。

全部通过时 revised S1 为 `passed_revised_structural_time_consistent_s1`；任一失败则冻结首个 S1 gate 并停止。

## 6. 状态裁决与输出

只有完整性、revised D1 和 revised S1 全部通过时，v08 唯一允许状态为

```text
passed_revised_fixed_topology_d1_s1_acceptance
```

该状态必须与历史证据状态分栏输出，不得覆盖历史失败：

```text
historical v02/v04/v06 = failed, unchanged
revised D1/S1 acceptance = passed or first failed gate
x1_k_passed = false
R1/C1/F1 = not_executed
downstream_authorized = false
```

交付必须包含：中文裁决报告、架构版本、机器 `summary.json`、`criteria.csv`、逐项 `decision_matrix.csv`、包含 23 文件 hash/rows/schema/source commit 的 `provenance_manifest.json`、key/ledger 复算摘要、TDD RED/GREEN、复算命令、parent/fork/strict/Python/Ruff 与远端同步证据。

任一证据完整性或科学门禁失败，立即冻结首失败、已完成 decision rows 和未执行项；不得运行 R1、C1、F1。

## 7. Claim guard 与受保护内容

v08 不授权 ECM/flow 长耦合、参数标定、长期稳定、生理、FSI、EFE 或心脏发育机制 claim。不得触碰或纳入：

- `figures/`
- `scripts/build_efe_nature_figure_plan_docx.py`
- `scripts/insert_efe_figure_mockups_docx.py`

完成 v08 后必须停止并返回导师，不自行推进 R1/C1/F1。
