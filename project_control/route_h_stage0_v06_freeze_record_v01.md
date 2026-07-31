# Route H Stage 0 v06 空间离散族冻结记录

## 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE0-V06`
- frozen at：`2026-07-31T10:15:00+08:00`
- status：`frozen_pending_readonly_inspection`
- contract：`CONTRACT-PRL-ROUTE-H-STAGE0-V06`
- frozen files：96
- package SHA-256：`37A7546BCAF12ED4A27D222758B949C4B9C3FDDE459F8F07AA0288C961E5830B`
- manifest SHA-256：`A339B8D38CCE579A8EA0369B5ABAA86F0DE31E77C02CA49CD962753EAE823721`
- family SHA-256：`EB29A59A17CC60CBE67E512B8E210F0052794B841504359A52CFE816AEBB6131`
- v05 base 22 arrays byte exact：`true`
- Stage 2 scientific runs before freeze：`0`

## 三层 reference seal

| level | cell V/F | ECM V/T | min cell quality | min det(Dm) | net force | net moment |
|---|---:|---:|---:|---:|---:|---:|
| coarse | 42 / 80 | 105 / 288 | 0.426993454924 | 0.0225 | 8.943e-31 | 1.972e-31 |
| base | 162 / 320 | 351 / 1152 | 0.346031135426 | 0.005625 | 7.583e-31 | 2.911e-30 |
| fine | 642 / 1280 | 2125 / 9216 | 0.326587294472 | 0.000703125 | 7.733e-31 | 1.171e-30 |

三层均满足：cell watertight/orientation/positive volume、ECM positive tetra、
material/source/owner/gauge coverage、passive reference force、material pair force/moment、
zero steric energy、零 proper intersection 和 deterministic replay。

## coarse geometry admission

v06 冻结 `0.075` 作为 cell–ECM reference tether 的 geometry-only materialization
ceiling；coarse 实测最大 `g0_pair=0.06348416662201481`。该 ceiling 不进入任何
energy、force、power 或 solver；每对 tether 仍使用自身封存的 `g0_pair`。

## 注册状态

`STAGE2-DISCRETIZATION-SEAL` 已通过，原 PreStage2 阻断可以在只读检查接受后关闭。
`SPACE-REFINEMENT` 仍为 `not_run_stage2_preexecution`：v06 只封存 family 和阈值，
没有提前运行 E0/E4 响应。

## 不变性

任一 manifest 内文件变化都会使本冻结失效。v01–v05、Stage 1 v02、力学方程、
无量纲参数、接触/黏附势、载荷、功率账本、periodic 排除和 Gate A–E 顺序均未改变。
本记录不宣告 Stage 2 任一 gate 通过，也不形成生理或论文结论。
