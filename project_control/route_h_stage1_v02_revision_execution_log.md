---
execution_id: EXEC-PRL-ROUTE-H-STAGE1-V02
supersedes_execution: EXEC-PRL-ROUTE-H-STAGE1-V01
source_inspection: INSPECT-PRL-ROUTE-H-STAGE1-V01
resolved_finding: S1V01-WINDING-SUM-ORDER-001
executor: Codex current task; governed single-worker revision
started_at: 2026-07-30T20:58:00+08:00
completed_at: 2026-07-30T21:04:00+08:00
status: completed_pending_freeze_and_readonly_inspection
---

# Route H Stage 1 v02 修订执行记录

## 1. 修订范围

只修复 v01 冻结后检查的 blocking finding：
`S1V01-WINDING-SUM-ORDER-001`。

未改变：

- Stage 0 v05 与 reference bundle；
- cell/ECM 坐标、拓扑、identity、tether/source-map；
- winding threshold 和 inside/outside 语义；
- steric/contact/adhesion potential；
- DCM/ECM 方程和参数；
- load、support、gauge、ledger 和 registry threshold；
- active/full-patch/Stage 2 授权边界。

## 2. 实现修订

`contact_adhesion.winding_number` 现执行：

1. 按 target face array（即 ascending face ID）构造 solid angle；
2. 三分量 norm、dot 和 determinant 使用显式 binary64 分量运算顺序；
3. `solid_angles[0..N-1]` 使用 `numpy.float64` scalar accumulator 逐项相加；
4. 不调用 `np.sum` 或其他 pairwise reduction。

## 3. 回归 falsifier

新增 `test_winding_accumulator_is_strictly_sequential_binary64`：

`[1e16, 1, …(1000 次)… , 1, -1e16]`

- frozen sequential binary64 result：0；
- NumPy reduction result：986。

因此测试能在当前环境中区分严格顺序与 pairwise reduction，不是同义实现测试。

## 4. 完整复算

- Ruff：all checks passed；
- pytest：32 passed，0 failed/error/skipped；
- reference bundle SHA-256：仍为
  `4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59`；
- 46 eligible steric pairs / 16584 owners；
- reference minimum gap：0；
- proper intersections：0；
- steric energy：0；
- assembled net force/moment：
  `7.58e-31 / 2.91e-30`；
- 40 registry terminal status：37 passed，3 authorization-correct not-run；
- active enabled：false；
- full-patch trajectory run：false；
- Stage 2 authorized：false。

v01 freeze/review 已提交到 Git 历史并保留为 `revision_required` 记录；v02 不覆盖其治理文件。

