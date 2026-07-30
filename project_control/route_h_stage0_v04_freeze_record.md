# Route H Stage 0 v04 冻结记录

## 1. 冻结结论

- 冻结记录 ID：`FREEZE-PRL-ROUTE-H-STAGE0-V04`
- 冻结时间：`2026-07-30T19:30:26+08:00`
- 冻结状态：`frozen_stage0_pending_readonly_inspection`
- 合同：`CONTRACT-PRL-ROUTE-H-STAGE0-V04`
- 特化：`SPECIALIZATION-PRL-ROUTE-H-STAGE0-V04`
- 用例：`CASES-PRL-ROUTE-H-STAGE0-V04`
- 参考几何：`GEOMETRY-PRL-ROUTE-H-STAGE0-V04`
- reference mesh/source-map 实例：未生成，且未授权生成
- Stage 1：**未授权**
- Stage 2：**未授权**

本次冻结执行：

- 用户批准的 Phase 0 阶段内部自主修订；
- `V03-STERIC-SIGN-001`；
- `V03-BLOOD-LOAD-DISCRETE-001`；
- `V03-SOURCE-MAP-001`；
- 两项显式 caveat。

v04 不继承任何 Stage 1 runtime pass 或数值结果。

## 2. 冻结清单

| # | 路径 | 字节数 | SHA-256 |
|---:|---|---:|---|
| 1 | `data/route_h/route_h_reference_geometry_spec_v04.json` | 26846 | `C8CE3036AAE3C9BF33E2960F0B1CAF88560D9F16CED90052188B5BE6253953B7` |
| 2 | `src/route_h/route_h_contract_v04.json` | 20988 | `5BC3EEED149813BCF1F087588917F199629B16EB2D6AB9C55AAAA9D2017065C9` |
| 3 | `src/route_h/route_h_model_specialization_v04.json` | 7378 | `729B03BA5A836510AB9F7760135F0A345624900CBE2678AE047C7F6ACAC3334D` |
| 4 | `data/route_h/route_h_cases_v04.json` | 16248 | `B356CA4DCFDEB5C5CFD2EBB94A6BBB5FC4AF5CDB1A15AB78E2F94DA3B1C93507` |
| 5 | `docs/route_h/route_h_coordinate_and_sign_convention_v04.md` | 10960 | `ED904A99EEA1E8D16331927A1F3F4F7F51DE902B0E99AE6E026C41F3DC388A07` |
| 6 | `docs/route_h/route_h_port_and_power_ledger_v04.csv` | 7802 | `51F453FD6DD195867E0B71E859D11DD05BDD51BBD679A34FDDE5613C61D73F2F` |
| 7 | `tests/route_h/route_h_verification_registry_v04.csv` | 18893 | `B49A4240C6455FA9AE283A2436DE00AAB05F318CE179AD8F36A9725CB265CCA8` |
| 8 | `project_control/route_h_stage0_v04_revision_execution_log.md` | 5026 | `3D2106ED848F2A1477590AF19EBAE5C3CE6FF65F89B644782FE756F0618B559C` |

冻结算法：SHA-256。路径相对于 `E:\Temp-Projects\PRL`。

## 3. v03 finding 闭合映射

| v03 finding | v04 冻结方案 | 主证据 |
|---|---|---|
| `V03-STERIC-SIGN-001` | 完整封闭 target surface、全局最近 feature owner、winding-number sign、exterior ECM boundary、target embedded validity、proper-crossing CCD guard | geometry、contract、coordinate、ledger、verification |
| `V03-BLOOD-LOAD-DISCRETE-001` | current area、barycenter quadrature、`1/3` nodal force、face velocity、共同 nodal force-block resultant/leakage/power | contract、coordinate、cases、ledger、verification |
| `V03-SOURCE-MAP-001` | 每个 myocardial basal master face 一个 source-map record，映射到 boundary face 和唯一 adjacent tetra；`j_myo=0` | geometry、contract、specialization、cases、ledger、verification |
| `V03-ADH-COMPRESSION-SLACK-001` | `0<=g<g0_pair` 显式登记为 tension-only adhesion compression slack | contract、coordinate、cases、ledger、verification |
| `V03-SENSOR-SEMANTICS-001` | `chi_E` 限定为一个全局 unprojected WSS command diagnostic，无局部 shear 或机械反馈 claim | contract、specialization、coordinate、cases、ledger、verification |

## 4. 冻结前检查

- UTF-8 JSON：`4/4`
- CSV：`2/2`
- ledger：30 个唯一 term
- verification registry：81 个唯一 test
- Stage 0 静态登记：`41/41`
- cases：14 个唯一 case，5 个 gate
- direct-input hash：`7/7`
- v02/v03 冻结记录抽取的历史受控 hash：`23/23`
- manufactured/scientific sanity：`16/16`
- placeholder：0
- Stage 1/2/materialization authorization violation：0

关键反例：

- unit-cube 外部点在旧 far-side triangle plane 规则下为负，但 v04 winding-number classifier 正确判定 outside；
- unit-cube 内部点 winding number 为 1；
- 刚体平移后分类不变；
- blood face power 与同一 assembled nodal force-block power 完全一致。

以上只属于 Stage 0 规范检查，不是网格、solver 或 Gate A–E 结果。

## 5. 不变性

v01、v02、v03 保持不可变历史记录。v04 只替代未来工作的 Stage 0 合同目标，不改写旧文件，也不继承旧版本的 pass flag。

## 6. 解冻规则

1. 冻结清单中任一文件发生字节级变化，本记录立即失效；
2. 方程、signed-distance classifier、source-map、blood load assembly、参数、边界、case、阈值或 test 变化必须创建新版本；
3. reference bundle materialization 必须另行获得 Stage 1 授权并形成新封存 bundle；
4. 禁止以同名文件覆盖 v04；
5. 冻结后的下一步只允许新增只读检查报告。

## 7. 下一状态

`stage0_v04_frozen_pending_readonly_scientific_inspection`

Stage 1 仍不授权。
