---
inspection_id: PREFLIGHT-PRL-ROUTE-H-STAGE2-DISCRETIZATION-V01
inspector: Codex current task; single-worker governed preflight
inspected_at: 2026-07-31T09:14:24+08:00
status: blocked_pending_separate_discretization_family_approval
stage2_authorization: DEC-PRL-ROUTE-H-STAGE2-AUTHORIZATION-V01
blocking_test: STAGE2-DISCRETIZATION-BLOCK
finding_id: S2-PREFLIGHT-DISCRETIZATION-001
stage2_scientific_runs: 0
---

# Route H Stage 2 离散化前置门禁检查 v01

## 1. 结论

Stage 2 Gate A–E 已获用户授权，但当前仍不能开始任何 Stage 2 科学运行。

冻结的 v05 证据链同时规定：

- `route_h_cases_v05.json`：
  `space_refinement_registered=false` 且
  `space_refinement_required_before_stage2=true`；
- `route_h_contract_v05.json`：
  在 Stage 2 前必须另行批准并冻结一个 discretization-verification geometry family；
- `route_h_reference_geometry_spec_v05.json`：
  coarse/base/fine 会改变 ID、tether 和 hash，不能由当前唯一 base topology 冒充；
- `route_h_verification_registry_v05.csv`：
  `STAGE2-DISCRETIZATION-BLOCK` 要求在独立 coarse/base/fine family 获批并封存前，
  Stage 2 科学运行数必须为 0。

因此 `S2-PREFLIGHT-DISCRETIZATION-001` 是授权后的前置治理阻断，不是 Gate A 科学失败，
也不能以普通数值修复方式绕过。截至本记录生成时，Stage 2 科学运行数保持为 0。

## 2. 建议的一次性修订范围

建议先建立 **Stage 0 v06 spatial-discretization amendment**，只解除该前置门禁：

| level | cell surface subdivision | 每细胞 vertices/faces | ECM intervals `(n_x,n_y,n_z)` |
|---|---:|---:|---:|
| coarse | 1 | 42 / 80 | 6 / 4 / 2 |
| base | 2 | 162 / 320 | 12 / 8 / 2 |
| fine | 3 | 642 / 1280 | 24 / 16 / 4 |

其中 base 必须逐位复用 v05 已冻结的 cell/ECM topology 与 reference bundle；coarse/fine
沿相同确定性生成规则独立生成，不改 patch bounds、细胞数、方程、无量纲参数、接触形式、
载荷、功率账本或 Gate A–E 顺序。

v06 还应：

1. 对三个 level 分别重建并封存 face identity、anchor、material tether、source map、
   boundary owner、gauge arrays 与 SHA-256；
2. 对三个 level 分别通过 manifold、orientation、positive tetra、reference force/moment、
   zero steric、coverage 与 hash replay；
3. 以冻结计划已有阈值注册“最后两级空间细化关键量相对差 `<=3%`”，近零量使用冻结的
   绝对阈值，不按响应改阈值；
4. 不新增 periodic case，不启用 turnover、非零 `j_myo`、生理标定或参数 sweep；
5. v06 冻结并只读检查通过后，才关闭 `STAGE2-DISCRETIZATION-BLOCK` 并返回 Gate A。

## 3. 所需决定

该修订会新增两套 identity-bearing geometry 及其证据包，属于冻结范围扩展，不能由 Codex
自行推定授权。需要用户明确批准上述 v06 范围；批准后，v06 内部的生成、检查、普通修复、
冻结、只读复核和 GitHub 阶段同步均按既有阶段规则连续完成，不再逐项请示。
