---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V08R1-ADJUDICATOR-REPAIR
status: frozen_before_v08r1_response
frozen_at: 2026-08-03
parent_commit_before_v08r1: 421181f774d89b53c78861868e2833c6ee8f6aac
rejected_v08_contract_commit: 929973c99d4971c3a151f3e0db8ef7931580293f
rejected_v08_result_commit: 66ff245d2da06d083ef205e2a4fc471903205dbb
rejected_v08_sync_commit: 421181f774d89b53c78861868e2833c6ee8f6aac
cell_engine_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
downstream_authorized: false
---

# X1-K v08r1 adjudicator-repair 冻结合同

## 0. 拒绝结论、边界与不可改写历史

导师拒绝 v08 当前“通过”交付。v08 状态冻结为
`failed_adjudicator_contract_incomplete`。该拒绝针对 fail-closed 裁决器的合同实现不完整，
不是新的物理或数值科学失败。v08 的合同、代码、报告和结果包在
`929973c`、`66ff245`、`421181f` 中保留，不覆盖、不改写、不删除。

v08r1 只修复 PRL-owned Python adjudicator、测试、导出、报告、架构与新版本结果包；
不得修改 v05–v08 原始证据、C++、受控 SimuCell3D fork、力、阻尼、registered owner、
legacy cache、物理模型、已有阈值或历史失败测试；不得产生新物理轨迹。

永久保留：

```text
Route H Gate A v01 = failed_invalid_numerics
v02 D1 = failed_instantaneous_smooth_surface_refinement
v04 Family B = failed_family_B_parameterized_diagnosis
v06 mean-radius spatial gate
  = failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic
v08 = failed_adjudicator_contract_incomplete
X1-K = false
R1/C1/F1 = not_executed
downstream_authorized = false
```

## 1. 执行顺序与 TDD

严格顺序：本合同单独提交并推送 → 每次一项 RED/GREEN → 从冻结 23 CSV 重新裁决 →
新版本报告与结果包 → 保存并解析真实验证输出 → 完整回归 → 提交、推送、哈希审计 → 停止。

四轮公共行为测试：

1. source commit/path 被替换、对象不存在或 blob 与 required file 不同字节时 fail closed；
2. 在测试用冻结 spec 同步更新 hash 后，分别破坏 fraction、global-L2 或 error-order
   语义字段，仍必须由语义复算 fail closed；
3. 将 valence-5 pointwise 序列改为改善时，limitation 仍存在、四层值仍报告、
   claim flags 仍为 false，但 revised D1 不得因此失败；
4. verification 缺真实命令输出或 exit code 时 fail closed，summary 不得出现硬编码计数。

每轮先保存能证明缺失行为的 RED，再做最小 GREEN 并运行 focused tests；不在 RED 状态重构。

## 2. 冻结证据与 source Git-object 验证

required evidence 仍严格使用 v08 合同冻结的同一 23 个 CSV、SHA-256、行数、schema 与来源：

- v05：8 文件，source commit `51d606b1165c3c0ca0839e59aebce3e1a89ca640`；
- v06：10 文件，source commit `eb3c97339580e3d2e0f565e47b9b78dab292046e`；
- v07：5 文件，source commit `f4df24c840f357fc06a45c4406bc55b9817199b9`。

除了 v08 已有的 regular-file、current SHA-256、UTF-8、exact schema、rows、finite、keys 与
ledger 检查，每个 EvidenceSpec 必须通过 Git-object 验证：

```text
source_commit^{commit} 必须存在且解析为 commit
source_commit:path 必须存在且解析为 blob
source_blob_bytes = git cat-file blob source_commit:path
current_bytes = required file 原始字节
source_blob_bytes == current_bytes
source_blob_id = git rev-parse source_commit:path
current_blob_id = git hash-object --no-filters required_file
source_blob_id == current_blob_id
```

Git 命令必须使用参数数组、固定 workspace cwd、捕获 stdout/stderr/exit code；对象不存在、
对象类型错误、路径替换、字节或 blob ID 不同均抛出结构化 `EvidenceIntegrityError`。
`provenance_manifest.json` 每项新增并真实输出：
`source_blob_id`、`current_blob_id`、`source_blob_verified=true`。

## 3. v05 error-region / global-L2 / error-order 语义闭合

对每个 Family C source level 1–4，由 `family_c_error_regions.csv` 的 valence-5 与
valence-6 行独立复算：

```text
E_total = E_v5 + E_v6
A_total = A_v5 + A_v6
fraction_v5 = E_v5 / E_total
fraction_v6 = E_v6 / E_total
fraction_v5 + fraction_v6 = 1
e_normal_rebuilt = sqrt(E_total / A_total) / abs(v_exact)
```

冻结绝对/相对比较容差为 `1e-12 * max(1, abs(reference))`。`E_total`、`A_total` 与
`abs(v_exact)` 必须严格大于零。两区 fraction 必须分别等于上述复算值；顶点数与
`family_c_levels.csv` 的 `vertex_count` 闭合；`A_total` 必须与 levels 的 dual-area/surface-area
字段闭合；`e_normal_rebuilt` 必须与 levels 的 area-weighted normal relative L2 字段闭合。

`family_c_error_energy_orders.csv` 三行必须对应相邻 levels `(1,2),(2,3),(3,4)`，并由实际
`h_rms` 逐列复算：

```text
p_E = log(E_coarse/E_fine) / log(h_coarse/h_fine)
```

必须逐列核对 `total_error_energy_order`、`valence_5_error_energy_order`、
`valence_6_error_energy_order`、`valence_5_closed_one_ring_error_energy_order`；其中一环能量
来自 error-region 的 `valence_5_closed_one_ring` 行。任一字段被改坏，即使测试同步更新
EvidenceSpec 的 hash/rows/schema，也必须以语义闭合失败拒绝。

## 4. limitation 与 acceptance 解耦

limitation 是必须存在的报告记录，而不是要求“点态必须不改善”的科学门禁：

- 强制原样报告四层 valence-5 `maximum_pointwise_relative_error`；
- 强制 `pointwise_convergence_claim_allowed=false`；
- 强制 `uniform_convergence_claim_allowed=false`；
- 可报告 observed trend，但无论序列改善、持平或恶化，limitation record 不进入 revised D1
  acceptance 布尔聚合；
- revised D1 只由 role=`revised_acceptance` 的 D1 gates 决定。

测试中的“改善序列”只用于证明逻辑方向正确，不改冻结 raw evidence，也不授权点态 claim。

## 5. 真实 verification evidence

科学 adjudicator 不得硬编码测试计数。v08r1 新建版本化机器日志目录，至少保存：

```text
parent_ctest.log + parent_ctest.exitcode
fork_ctest.log + fork_ctest.exitcode
strict_prl_core.log + strict_prl_core.exitcode
python_pytest.log + python_pytest.exitcode
ruff.log + ruff.exitcode
```

verification parser 必须从文件读取并验证：regular file、UTF-8、exit code、完成标记和实际
计数/预期失败名。允许的唯一完整回归语义：

- parent CTest exit code 可为非零，但必须解析为 55 total、52 passed，且失败集合严格等于
  v02 D1、v04 Family B、v06 short-trajectory 三项历史测试；不得有意外失败；
- fork CTest exit code 为 0，解析为 134/134；
- strict build exit code 为 0，日志含 `Built target prl_core`；
- Python pytest exit code 为 0，从真实日志解析通过计数；
- Ruff exit code 为 0，日志含通过完成标记。

任一 required log/exitcode 缺失、不可解析、计数或失败集合不符时，verification 必须
fail closed；在验证尚未运行前，科学 summary 只能明确写
`verification_status=not_yet_adjudicated`，不得自报计数或总体机器验证通过。最终 summary 的
verification 区只能由 parser 结果生成。

## 6. 科学裁决语义保持不变

除第 2–5 节的 adjudicator 合同修复外，revised D1/S1 的全部数值阈值、v07 mean-radius
结构/时间角色、v06 area/volume/registered-energy 空间与时间门禁、逐步 orientation、q、
face-area ratio、cache、centroid、`surface_tension_only` ledger、force-clear、extraordinary-
vertex/one-ring 风险门禁均与 v08 合同原样一致，不得放宽。

若 23 个冻结 raw CSV 的完整性与全部修复后门禁通过，唯一允许状态为：

```text
passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair
```

同时必须输出：

```text
v08 = failed_adjudicator_contract_incomplete
historical v02/v04/v06 = failed, unchanged
x1_k_passed = false
R1/C1/F1 = not_executed
downstream_authorized = false
```

任一 source object、语义闭合、scientific gate 或 verification evidence 失败，冻结首失败并停止；
不得推进 R1。

## 7. 版本化交付与保护内容

新增且仅新增 v08r1 合同、修复代码/测试、架构、拒绝与修复中文报告，以及
`results/hybrid/x1_k_revised_fixed_topology_v08r1/`。不得覆盖
`results/hybrid/x1_k_revised_fixed_topology_v08/` 或 v01–v07 文件。

交付包括 source/current blob provenance、23 文件 hash/row/schema、v05 语义复算、decision
matrix、ledger replay、四轮 TDD RED/GREEN、真实验证日志/exit code、parser 结果、复算命令、
双仓哈希和远端同步证据。

不得触碰或纳入：

- `figures/`
- `scripts/build_efe_nature_figure_plan_docx.py`
- `scripts/insert_efe_figure_mockups_docx.py`

禁止 ECM/flow 长耦合、参数标定、长期稳定、生理、FSI、EFE 或心脏发育机制 claim。
完成后停止并返回导师。
