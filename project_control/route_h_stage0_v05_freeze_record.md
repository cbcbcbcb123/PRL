# Route H Stage 0 v05 冻结记录

## 1. 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE0-V05`
- frozen at：`2026-07-30T20:12:00+08:00`
- contract：`CONTRACT-PRL-ROUTE-H-STAGE0-V05`
- specialization：`SPECIALIZATION-PRL-ROUTE-H-STAGE0-V05`
- cases：`CASES-PRL-ROUTE-H-STAGE0-V05`
- geometry：`GEOMETRY-PRL-ROUTE-H-STAGE0-V05`
- scope：仅 `V05-FACE-TIE-001` binary64 material-identity tie erratum
- Stage 1：已由独立用户决定授权被动实现
- Stage 2：未授权

## 2. 冻结清单

| # | 路径 | 字节数 | SHA-256 |
|---:|---|---:|---|
| 1 | `data/route_h/route_h_reference_geometry_spec_v05.json` | 31358 | `45A1BE59D412B0816A4AB0BF15F4D6C37CF93F58D13CF584A22824CB032C9CFA` |
| 2 | `src/route_h/route_h_contract_v05.json` | 21898 | `7CE576EF1ABB321256A8AC7736934BDE7901DA553251386E56A2F0E64AFE0B06` |
| 3 | `src/route_h/route_h_model_specialization_v05.json` | 8869 | `290B31015913E2A9EBE1B577CF488925EBCD715B15A79B196ABE8782ED154F16` |
| 4 | `data/route_h/route_h_cases_v05.json` | 17830 | `F0523D9BA882EA10BF1D9B80607FE1AF064E8810198E01882AA180F3C6150B65` |
| 5 | `docs/route_h/route_h_coordinate_and_sign_convention_v05.md` | 11367 | `55AB293795DFE5DB89524B364034C06DD1B7A65C999A04E7D0EED5BF953855C0` |
| 6 | `docs/route_h/route_h_port_and_power_ledger_v05.csv` | 7802 | `7A6CA70C084013F949BB761EC741FA11EC0884859FCF09CF71CFBBACC38C4189` |
| 7 | `tests/route_h/route_h_verification_registry_v05.csv` | 18789 | `6A0C2279F249B2F0604086AB80AAB09137D04F42FEC66BDECB5A5F6C5F4A1DDA` |
| 8 | `project_control/route_h_stage0_v05_revision_execution_log.md` | 1678 | `AD4932F3E2A59DF3B9141AE65CDE905A4D5F5B808C0A6ED7835DB0C627CFC54D` |

冻结算法为 SHA-256。v01–v04 保持不可变。本清单任一文件发生字节变化即使本冻结失效。

## 3. 退出检查

- JSON/CSV 可解析；
- v05 cross-reference 指向 v05；
- v04 freeze hash 8/8 保持一致；
- 8 个 corner tie 采用 z 优先；
- 998/998 neighbor master rays 命中要求的 mirrored slave subtype；
- 无方程、参数、拓扑、contact、load、owner 或 threshold 变化；
- active/full-patch/Stage 2 未授权。

下一步只允许新增 v05 只读检查；检查通过后才重新开始 Stage 1 materialization。
