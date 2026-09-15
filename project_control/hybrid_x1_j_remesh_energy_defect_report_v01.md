---
report_id: REPORT-PRL-HYBRID-X1-J-V01
status: passed_frozen_active_energy_owner
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
result_id: PRL-HYBRID-X1-J-REMESH-ENERGY-DEFECT-V01
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# Hybrid X1-J 重网格能量缺陷报告 v01

## 结论

X1-J v01 已按主动收缩能量所有者范围冻结。PRL owned material sink 现在把真实 `local_mesh_refiner` 接受的 split/swap/merge 事件转换为可审计的 `DeltaPsi_remesh` 单事件记录和累计循环账本；材料迁移、主动储能评价、纤维漂移审计与账本更新共享同一个成功/失败提交边界。

覆盖范围显式固定为 `active_contraction_only`。因此本报告没有把通过结果表述为被动力、接触、ECM 或流体的全系统能量一致性，也没有修改或覆盖 Route H Gate A v01 的 `failed_invalid_numerics` 历史包。

## TDD 证据

1. **RED 1**：先加入真实 swap 公共行为测试；编译仅因 `begin_active_remesh_energy_ledger`、`last_remesh_energy_defect` 和 `remesh_energy_ledger` 尚不存在而失败。
2. **GREEN 1**：实现 revision-matched 主动储能账本和事件前后独立能量评价；真实 swap 的 `DeltaPsi_remesh=0`，纤维对齐为 `1`。
3. **RED 2**：先要求 split/swap/merge 独立计数；编译仅因三个 operation counter 尚不存在而失败。
4. **GREEN 2**：实现分类累计与望远镜闭合；真实 split 后 merge 的累计缺陷和最终储能漂移同为 `5.2041704279304213e-17`。
5. **RED 3**：先写 8 次 swap/swap-back 循环门禁；编译仅因 `RemeshCycleGateThresholds` 和 `evaluate_remesh_cycle_gate` 尚不存在而失败。
6. **GREEN 3**：实现七项独立判据及无效阈值拒绝；16 个事件在 `1e-12` 门槛内通过。
7. **REFACTOR**：把 coverage、单事件缺陷、累计账本和门禁结果固化为公共类型；保持既有材料迁移接口和 X1-C fork 快照合同不变。

## 定量结果

| 场景 | 事件 | `DeltaPsi_remesh` / 漂移 | 声明重网格功 | 初始纤维最小对齐 |
|---|---:|---:|---:|---:|
| real swap | 1 swap | `0` | `0` | `1` |
| real split→merge | 1 split + 1 merge | split `5.2041704279304213e-17`; merge `0`; final `5.2041704279304213e-17` | `0` | finite / tracked |
| 8 real swap cycles | 16 swaps | final `-1.5439038936193583e-16`; cumulative absolute `1.5439038936193583e-16` | `0` | `1` |

循环门槛为：最终能量漂移、累计绝对缺陷、事件间储能变化、声明功和望远镜残差均不超过 `1e-12`，初始纤维对齐不低于 `1-1e-12`，事件数至少为 1。所有组成判据均独立返回；另有反例测试确认每一种失败不会被总布尔值隐藏。

## 验证门禁

| 检查 | 结果 |
|---|---:|
| X1-J targeted CTest | `4/4 passed` |
| parent C++ CTest | `34/34 passed` |
| owned parent core `-Wall -Wextra -Wpedantic -Werror` | `14/14 passed` |
| fork standalone CTest | `133/133 passed` |
| parent Python | `63/63 passed` |
| tracked Python Ruff | passed |
| diff / JSON checks | passed |

受控 fork 在本阶段无代码变更，仍固定并同步在 `cbcbcbcb123/prl-cell-engine` 的 `codex/cell-engine-integration-seam` 分支、提交 `2d4b2183f5966c2afe3f4234471e727fe5f9e68d`。X1-J 代码和证据只需在父仓库提交。

## 冻结失败边界

- 账本只能在 mesh revision 与已注册材料状态一致时启动，且同一 cell 不可静默重复启动；
- 材料点身份丢失、纤维无效、能量评价失败或 revision 不连续时，材料状态和账本均不得部分提交；
- 纯拓扑重网格声明功固定为零；任何非零外部 remesh work 必须通过未来的新接口和新版本显式注册；
- `sum(abs(DeltaPsi_remesh))` 与 `sum(abs(epsilon_alg))` 分别保留，门禁使用后者，不能仅用有符号和掩盖正负抵消；
- `passed` 必须与 `coverage=active_contraction_only` 一起解释。

## Claim guard

X1-J v01 仅证明主动收缩储能所有者在所测真实 split/swap/merge 及 swap 循环上的可审计重网格缺陷与纤维漂移门禁。当前被动表面/压力/弯曲缓存、接触、ECM 和流体没有注册到该能量账本，所以不能宣称全系统重网格能量守恒或离散总能量不等式。它也不证明稳定收缩轨迹、时间/空间收敛、完整耦合、EFE 双稳态/机械记忆、发育机制、参数标定或生理预测。

下一安全阶段仅为 X1-K 短轨迹多门禁。X1-K 通过前不得进入长耦合或扩大论文 claim。
