---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V05-V01
inspector: Codex current task; single-worker read-only audit after freeze
inspected_at: 2026-07-30T20:15:00+08:00
status: accepted_with_caveats
---

# Route H Stage 0 v05 只读科学检查报告 v01

## 1. 结论

`accepted_with_caveats`。`V05-FACE-TIE-001` 已以最小、确定且镜像对称的规则关闭。
未发现需要改变科学对象、接触形式、参数、载荷或证据解释的新阻断项。

v05 freeze record SHA-256：`05426C9339B682530D81C13D9AEB0B200F2FE328B99E4FBB9A09E005D37E7F4C`。

## 2. 只读复核

冻结后对下列 8 个技术件复算，全部与 freeze record 一致：

- `data/route_h/route_h_reference_geometry_spec_v05.json`: `45A1BE59D412B0816A4AB0BF15F4D6C37CF93F58D13CF584A22824CB032C9CFA`
- `src/route_h/route_h_contract_v05.json`: `7CE576EF1ABB321256A8AC7736934BDE7901DA553251386E56A2F0E64AFE0B06`
- `src/route_h/route_h_model_specialization_v05.json`: `290B31015913E2A9EBE1B577CF488925EBCD715B15A79B196ABE8782ED154F16`
- `data/route_h/route_h_cases_v05.json`: `F0523D9BA882EA10BF1D9B80607FE1AF064E8810198E01882AA180F3C6150B65`
- `docs/route_h/route_h_coordinate_and_sign_convention_v05.md`: `55AB293795DFE5DB89524B364034C06DD1B7A65C999A04E7D0EED5BF953855C0`
- `docs/route_h/route_h_port_and_power_ledger_v05.csv`: `7A6CA70C084013F949BB761EC741FA11EC0884859FCF09CF71CFBBACC38C4189`
- `tests/route_h/route_h_verification_registry_v05.csv`: `6A0C2279F249B2F0604086AB80AAB09137D04F42FEC66BDECB5A5F6C5F4A1DDA`
- `project_control/route_h_stage0_v05_revision_execution_log.md`: `AD4932F3E2A59DF3B9141AE65CDE905A4D5F5B808C0A6ED7835DB0C627CFC54D`

v04 冻结清单亦复算为 8/8 一致；未覆盖旧版本。

## 3. 反例与修订充分性

v04 的二进制比较使 face 159 的 `|u_x|` 比 `|u_z|` 大 1 ULP，而镜像 face 63
的 `|u_z|` 比另一分量大 1 ULP。相同数学方向因此获得不同 material identity。

v05 的 `8*eps_binary64` tie band：

- 只捕获 8 个数学角方向；没有捕获其他 face；
- 统一按 z 优先将其归入 apical/basal；
- 使 x-/x+/y-/y+ lateral face 数完全相等（各 52）；
- 使全部 998 个登记 neighbor master rays 都命中要求的 slave subtype。

因此该修订既充分关闭 materialization 阻断，也没有扩大模型。

## 4. Caveat

本检查与实现者是同一工作者，不是人员独立复核。其证据级别为单工作者、
冻结后只读、可复算检查。该限制不阻断已授权的 Stage 1 被动验证，但必须保留在
Stage 1 最终 inspection 中。

## 5. 下一状态

允许以 v05 为 Stage 1 frozen input 重新 materialize reference bundle。
Stage 2 仍未授权。
