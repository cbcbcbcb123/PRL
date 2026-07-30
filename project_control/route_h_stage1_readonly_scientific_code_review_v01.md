---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE1-V01
freeze_id: FREEZE-PRL-ROUTE-H-STAGE1-V01
inspector: Codex current task; single-worker read-only scientific/code audit after freeze
inspected_at: 2026-07-30T20:57:00+08:00
status: revision_required
blocking_findings:
  - S1V01-WINDING-SUM-ORDER-001
---

# Route H Stage 1 v01 冻结后只读科学/代码检查

## 1. 结论

结论：`revision_required`。

被动能量、力、reference bundle、作用—反作用、载荷、支撑、来源映射和授权边界没有
发现新的科学路线问题；但发现 1 个确定性合同实现偏差，必须在接受 Stage 1 前修复：

`S1V01-WINDING-SUM-ORDER-001`。

## 2. 冻结完整性

- Stage 1 v01 frozen files：62；
- hash mismatch：0；
- package SHA-256：
  `40A6B7871BE6FEE6143686D698596D743C141553593DF934F1636C067651E5EC`；
- manifest SHA-256：
  `AF83E07A620CA26F56F856E8876A3CB1B602B31BFF8138B7018B1FDED3282475`；
- freeze record SHA-256：
  `6D6D54780C26F34999E523727011069879F6CEDDFC9EE191C8E3097456FCCBBB`。

检查在冻结后只读进行。本报告不属于 v01 manifest。

## 3. Blocking finding

### `S1V01-WINDING-SUM-ORDER-001`

Stage 0 v05 geometry contract 要求 generalized winding number 的 solid angle 按
ascending target face ID，以 binary64 逐项累加。

v01 的 `contact_adhesion.winding_number`：

1. 正确按 `target_faces` 的升序构造每面 solid angle；
2. 但最终使用 `np.sum(...)` 做 reduction。

NumPy reduction 可以采用 pairwise summation，不能证明与合同要求的严格升序逐项
binary64 accumulator 相同。因此：

- 当前 inside/outside 数值反例仍全部通过；
- 但 deterministic byte-to-response contract 没有完全实现；
- 该差异不能以测试通过或“通常数值相近”豁免。

严重性：blocking implementation compliance finding，非科学机制 falsifier。

## 4. 最小修订要求

建立 Stage 1 v02，不覆盖 v01：

1. 每面 solid-angle primitive 可继续向量化计算；
2. norm/dot/determinant 使用显式 binary64 component order；
3. 最终 solid angles 必须在 Python/NumPy binary64 scalar accumulator 中按
   face ID `0..N-1` 逐项相加；
4. 新增一个 adversarial summation-order 回归测试，使 pairwise 与 sequential
   构造在可观察位级上可区分；
5. 重跑 31 项现有测试、完整 reference seal 和 registry evidence；
6. 新建 v02 manifest、freeze 和冻结后只读检查。

不要求改变 winding threshold、steric potential、contact owner、几何、参数或 Stage 0
v05；若修订必须触及这些项目，则转为路线门并请示用户。

## 5. 其余复核

以下项目未发现 blocking finding：

- Stage 0 v05 与 reference bundle hash 链；
- DCM area/bending/volume 解析力；
- ECM first Piola、`Z` 对称无迹演化和非负耗散；
- material tether natural gap、完整 normal/tangent gradient 和 objectivity；
- dynamic global closest owner、inside sign、reference zero steric；
- transverse CCD manufactured crossing 与 isolated tangency；
- 16 个 target self-intersection 和 46 个 reference pair proper crossing 为 0；
- blood pressure/WSS common force block 与 power；
- fixed support、global gauge、zero `j_myo` 和 ledger；
- active/full-patch/Stage 2 guard。

## 6. 独立性 caveat

本检查与实现者为同一工作者，不是人员独立或角色隔离检查。其证据级别为单工作者、
冻结后只读、可复算检查。v02 最终检查也必须继续保留此 caveat。

## 7. 下一状态

`stage1_v01_revision_required_local_deterministic_fix_authorized`

Stage 2 仍未授权。

