---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V06-V01
freeze_id: FREEZE-PRL-ROUTE-H-STAGE0-V06
inspector: Codex current task; single-worker read-only scientific/code audit after freeze
inspected_at: 2026-07-31T10:16:00+08:00
status: accepted_with_caveats
blocking_findings: []
resolved_prefreeze_findings:
  - V06-GEOMETRY-ADMISSION-001
  - V06-FLOAT-INTERFACE-SNAP-001
---

# Route H Stage 0 v06 冻结后只读科学/代码检查

## 1. 结论

结论：`accepted_with_caveats`。

没有发现 blocking scientific、deterministic、authorization 或 evidence-chain finding。
`STAGE2-DISCRETIZATION-SEAL` 已满足，原 `STAGE2-DISCRETIZATION-BLOCK` 可以关闭。

该结论只接受 coarse/base/fine identity-bearing reference family 及其 Stage 2 空间响应
预注册；不宣告 Gate A–E、time/space response convergence、生理有效性或论文结论通过。

## 2. 冻结完整性

- frozen files：96；
- hash mismatch：0；
- package SHA-256：
  `37A7546BCAF12ED4A27D222758B949C4B9C3FDDE459F8F07AA0288C961E5830B`；
- manifest SHA-256：
  `A339B8D38CCE579A8EA0369B5ABAA86F0DE31E77C02CA49CD962753EAE823721`；
- freeze record SHA-256：
  `0F503F4C03E15952AA3127C090493CDB143C2FFA98A3264DD1E0BA8BAA4B4B56`；
- family SHA-256：
  `EB29A59A17CC60CBE67E512B8E210F0052794B841504359A52CFE816AEBB6131`；
- v05/Stage 1 direct-input hash mismatch：0；
- v06 base 与 v05 不同数组数：0/22。

本报告在 v06 freeze 后新增，不属于 v06 manifest。

## 3. 数学与几何复核

### 离散族

| level | cell V/F | ECM V/T | min cell quality | min det(Dm) |
|---|---:|---:|---:|---:|
| coarse | 42 / 80 | 105 / 288 | 0.426993454924 | 0.0225 |
| base | 162 / 320 | 351 / 1152 | 0.346031135426 | 0.005625 |
| fine | 642 / 1280 | 2125 / 9216 | 0.326587294472 | 0.000703125 |

三层 cell 均为闭合、定向一致、正体积 2-manifold；ECM tetra 均有正 reference
determinant，且至少保留两个厚度单元层。

### identity、map 与 reference force

- canonical arrays：每层 22；
- fresh deterministic replay：66/66 byte exact；
- material tethers：468 / 1828 / 7268；
- myocardial source maps：144 / 504 / 1944；
- anchor、source、boundary owner 与 gauge coverage：完整；
- maximum reference tether force：`1.879e-16`；
- maximum assembled net force：`8.943e-31`；
- maximum assembled net moment：`2.911e-30`；
- minimum ECM J：1；
- proper intersections：0 / 0 / 0；
- steric energy：0 / 0 / 0。

因此三层 reference seal 都在冻结阈值内。

## 4. 两项预冻结修复复核

### geometry-only admission ceiling

coarse myocardial–ECM 最大 `g0_pair=0.06348416662201481`，所以 v06 在响应前将
cell–ECM materialization admission ceiling 冻结为 `0.075`。代码搜索确认该 ceiling
只在 reference array 生成与覆盖测试中出现；active/passive/contact/ECM/load/support
energy、force、power 和 solver 均不读取它。逐对 `g0_pair` 与
`delta_g=g-g0_pair` 保持不变。

因此该修订不改变机械参数或接触/黏附势，但必须作为 v06 family caveat 长期保留。

### reference-plane snap

初次 fine audit 的 6 个有事件 entity pairs 均来自解析 `z=0.2` 极点的
`0.19999999999999996` one-ULP 表示。修复仅对 coarse/fine 中距解析 extrema
`<=8*eps*max(1,|coordinate|)` 的坐标执行 snap；base 明确禁用。

复核确认：

- fine minimum myocardial z 精确为 `0.2`；
- fine proper intersections 从 6 个有事件 pairs 降为 0；
- base 22 arrays 仍全部 byte exact；
- snap 不进入响应或改变方程、拓扑、参数和势能。

该 finding 已关闭。

## 5. 合同、授权与证据边界

- v05 与 v06 的 active、passive cell、contact/adhesion、ECM、blood-load 和 support
  parameter blocks 结构相等；
- v05 的科学对象、方程、符号、功率账本和 Gate A–E 顺序保持不变；
- periodic 仍未注册；
- Stage 2 scientific runs before freeze：0；
- active/full-patch trajectory during v06：未运行；
- registry：86 `passed`，4 `not_run_stage2_preexecution`；
- `SPACE-REFINEMENT` 只注册 `E0_ZERO` 与 `E4_COMBINED`，尚未运行或继承 pass。

## 6. Caveats

1. 本次为当前 Codex 单工作者检查，不是人员独立复核。
2. `0.075` 是 v06 family 的 geometry admission ceiling，不是生理参数，也不能在后续
   response 后再调整。
3. reference-plane snap 是确定性 floating-point erratum；后续生成器、平台或精度变化
   必须重新通过 byte replay 和 proper-intersection seal。
4. v06 只证明三套 reference 离散能被封存且 reference force/contact 自洽；尚未证明
   Stage 2 响应的空间收敛。
5. Stage 2 参数仍是无量纲验证参数；不得形成生理、发育机制或论文 claim。
6. Stage 2 具体 implicit overdamped integrator 尚未在看到 Gate A 响应前锁定，必须先
   形成单独的数值方法决定与 manufactured tests。

## 7. 下一状态

v06 达到已批准的退出条件。根据用户对 v06 后继续 Stage 2 的授权，下一步允许：

1. 在任何 Gate A response 前锁定 implicit overdamped 数值方法和 objective metrics；
2. 实现主动 preferred-length 的制造解/导数/零力矩 tests；
3. 只运行 Gate A 的 `A0_ZERO` 与 `A1_ACTIVE`；
4. 仅在 Gate A 全部阈值通过后进入 Gate B。

无需再次请求进入 Gate A；任何 Gate A falsifier 仍必须立即阻断下游 gate。
