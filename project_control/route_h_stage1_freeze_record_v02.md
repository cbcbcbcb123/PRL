# Route H Stage 1 v02 冻结记录

## 1. 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE1-V02`
- frozen at：`2026-07-30T21:06:00+08:00`
- status：`frozen_pending_readonly_inspection`
- supersedes：`FREEZE-PRL-ROUTE-H-STAGE1-V01`
- resolved：`S1V01-WINDING-SUM-ORDER-001`
- contract：`CONTRACT-PRL-ROUTE-H-STAGE0-V05`
- unchanged reference bundle：
  `4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59`
- frozen files：68
- package SHA-256：`7AEFF194A295D0B5FF0D0B686B67C5498A117AFEE2384FA6AB16EA68348FEE67`
- manifest SHA-256：`2716D6337BA539F66508D128D5A78F9BDA76366C1E5143CC127002EB2187173E`

完整逐文件 hash 位于 `project_control/route_h_stage1_freeze_manifest_v02.json`。

## 2. v02 修订

Generalized winding number 的 solid angles 现按 ascending face ID 使用显式
`numpy.float64` scalar accumulator 逐项相加；不使用 pairwise reduction。

对抗回归：

- sequential result：0；
- NumPy pairwise result：986；
- test：passed。

## 3. 冻结状态

- pytest：32/32 passed；
- Ruff：passed；
- Stage 1 registry：37 passed，3 authorization-correct not-run；
- proper intersections：0；
- reference steric energy：0；
- active/full-patch/Stage 2：均未启用或授权。

## 4. 不变性

manifest 中任一文件变化即使本冻结失效。任何 active、trajectory、time/space
refinement、参数、几何、contact/load 或 claim 变化均需新授权/新版本。

下一步只允许新增 v02 冻结后只读 inspection。
