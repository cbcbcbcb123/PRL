---
freeze_id: FREEZE-PRL-ROUTE-H-STAGE0-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
contract_id: CONTRACT-PRL-ROUTE-H-STAGE0-V01
decision_id: DEC-PRL-ROUTE-H-STAGE0-ACTIVE-SIGN-AXIS-V01
approved_by: user
approved_at: 2026-07-28T16:15:31+08:00
status: frozen_pending_independent_inspection
stage1_authorized: false
stage2_authorized: false
---

# Route H Stage 0 冻结记录 v01

## User approval

用户明确决定：

> 确认采用两个 Stage 0 修订并冻结 Stage 0；暂不授权 Stage 1

## Frozen scientific decisions

1. 右端主动控制输入功率固定为

   \[
   P_{\rm active\ control}
   =\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star
   =-k_f(L_f-L_f^\star)\dot L_f^\star.
   \]

2. 主动长度和当前轴固定为

   \[
   d=c^+-c^-,
   \qquad
   L_f=\|d\|,
   \qquad
   f_{\rm current}=d/\|d\|.
   \]

   两组锚点是持久材料身份；作用力是中心力对，要求零净内部力、零净内部力矩。

## Frozen artifacts and SHA-256

| Artifact | SHA-256 |
|---|---|
| `src/route_h/route_h_contract_v01.json` | `9410550CB2A99163FC8B6158DB36B78AC5490C8606D9C83FCC6683CD2C1B3243` |
| `src/route_h/route_h_model_specialization_v01.json` | `1EC7FA7B5F5EBEBE56BC99BCD5C411D5C1CFCBBA13B9FC7960CD1C07F7D9FDAC` |
| `data/route_h/route_h_cases_v01.json` | `136232211D5763331AE2E67E55475A3719764D1DBD8F7D99012824FD48A217F7` |
| `docs/route_h/route_h_coordinate_and_sign_convention_v01.md` | `3CF599D524D8D3E0EF0B535BEEFFE4874392AF4643D478EBD52EE471EB0DF25C` |
| `docs/route_h/route_h_port_and_power_ledger_v01.csv` | `0B744B85B4C1DB4B07C5104D56D8A9A9BE46C6DDAA319535044AD6CC0B498184` |
| `tests/route_h/route_h_verification_registry_v01.csv` | `122E8B0B510DEC7EEBA5739351FB0E45456B8C6B36FADD5B6E72FF09A9AE2BE1` |
| `project_control/route_h_stage0_scientific_decision_v01.md` | `85DBA75DDBEB591C992CA2AB302D0F2DED0FB62348EFE3269CBDEE4080C90C21` |

## Freeze checks

- JSON 与 CSV 可解析；
- 两项科学 finding 均为 `resolved`；
- 主动功率符号与随动中心轴字段均为 frozen；
- 15 个 case 全部保持 `not_run_unauthorized`；
- Stage 1、Stage 2 均为未授权；
- `results/`、`figures/`、`notebooks/` 保持为空；
- 未创建 solver、数值轨迹或科学图件。

## Remaining lifecycle boundary

本记录证明用户批准的 Stage 0 合同已经冻结，但当前只有同一执行者的 focused self-check，
不冒充独立科学 inspection。

下一步若继续，应先对这组冻结哈希进行只读科学检查，重点复推：

- 主动功率的链式法则与总账符号；
- 锚点中心力对的客观性和零净力矩；
- pressure/WSS 的法向与切向端口；
- ECM 有限变形能、内部变量耗散与 \(J>0\)；
- \(A\)、\(H_{\rm ECM}\)、\(\chi_E\) 和 \(j_{\rm myo}\) 的隔离；
- cases、阈值和失败停机规则。

即使检查通过，也必须由用户另行明确授权后才能开始 Stage 1。

