---
architecture_id: ARCH-PRL-HYBRID-V13
status: frozen_x1_j_active_energy_remesh_ledger
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V12
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# PRL 自有长期混合架构 v13

本版本冻结 X1-J v01：在真实 `local_mesh_refiner`—心肌材料迁移同步路径中，为已注册的主动收缩能量所有者建立 split/swap/merge 单事件 `DeltaPsi_remesh` 账本，并建立循环重网格的能量、声明功和纤维漂移门禁。账本覆盖范围通过 `RemeshEnergyCoverage::active_contraction_only` 显式暴露；它不是被动表面、接触、ECM 或流体的全系统能量账本。

## 单事件账本合同

对一次已接受的拓扑事件 `k`，在相同主动收缩单元和状态参数下分别独立计算事件前后的主动储能：

```text
DeltaPsi_remesh[k] = Psi_active(after[k]) - Psi_active(before[k])
W_remesh_declared[k] = 0                         # 纯拓扑事件不伪装成物理功
epsilon_alg[k] = DeltaPsi_remesh[k] - W_remesh_declared[k]
```

事件间若材料主动状态或几何被其他步骤修改，其储能变化单独记入 `inter_event_stored_energy_change`，不得混入重网格缺陷。累计账本满足

```text
Psi_final - Psi_initial
  = sum(inter_event_stored_energy_change)
  + sum(DeltaPsi_remesh)
  + telescoping_residual
```

每个事件同时记录 operation、before/after revision、储能、声明功、算法缺陷、相邻事件纤维对齐、相对账本初始纤维对齐及最大材料点重绑定误差。split、swap、merge 的计数分别保留，不能只给总事件数。

## 原子提交顺序

真实 `local_mesh_refiner` 仍负责在接受拓扑变更时同步发出 before/after 快照。PRL sink 在持有该 cell 的锁时执行：

1. 校验事件 revision、拓扑和材料点身份；
2. 在临时状态中完成材料宿主迁移与纤维切平面投影；
3. 用事件前状态和临时事件后状态分别评价主动储能；
4. 形成单事件缺陷与累计账本，并检查材料点和纤维基线完整性；
5. 仅当以上全部成功后，同时提交材料状态、迁移审计和能量账本。

任一评价失败时不得留下部分更新的材料状态或账本。受控 fork 在 X1-J 无需新增修改：X1-C 已冻结的同步快照接口足以承载此 owned ledger，fork 提交继续固定为 `2d4b2183f5966c2afe3f4234471e727fe5f9e68d`。

## 循环门禁

`evaluate_remesh_cycle_gate` 分别报告而不隐藏以下判据：

- 最小已审计事件数；
- 最终主动储能漂移；
- `sum(abs(epsilon_alg))`，防止正负算法缺陷相互抵消；同时保留 `sum(abs(DeltaPsi_remesh))` 原始跳变量；
- 事件间储能变化；
- 声明的重网格功；
- 能量望远镜残差；
- 相对账本初始纤维的最小对齐度。

阈值必须有限且物理范围有效。门禁通过的语义只限于账本声明的 coverage，调用方不得把 `passed=true` 提升为全系统重网格能量一致性。

## 冻结数值

- 一次真实 swap：`DeltaPsi_remesh=0`，相邻和初始纤维对齐均为 `1`；
- 一次真实 split 后 merge：split 缺陷 `5.2041704279304213e-17`，merge 缺陷 `0`，最终主动储能漂移与累计缺陷均为 `5.2041704279304213e-17`；
- 八个真实 swap/swap-back 循环，共 16 个事件：最终主动储能漂移 `-1.5439038936193583e-16`，累计绝对缺陷 `1.5439038936193583e-16`，声明重网格功 `0`，最小初始纤维对齐 `1`；全部通过 `1e-12` 门槛。

这些值是当前无量纲、单细胞、主动收缩能量所有者的数值回归，不是生理量或轨迹收敛证据。

## Claim guard 与下一阶段

X1-J v01 证明真实 split/swap/merge 事件能够被主动储能账本原子记录，且所测循环没有累积超过门槛的主动储能缺陷、虚构重网格功或纤维漂移。它不覆盖上游被动压力/表面/弯曲能量缓存、接触、体积 ECM 或流体，也不证明离散总能量不等式、时间稳定性、空间/时间收敛、连续收缩轨迹、完整 cell–ECM/血流耦合、EFE 双稳态/机械记忆、发育机制、参数可识别性或生理预测。

下一阶段为 X1-K：短轨迹时间步 refinement、空间 refinement、体积误差、质心漂移、最小 Jacobian/三角质量、接触穿透、离散能量不等式和失败状态持久化。X1-K 通过前继续禁止 ECM/血流长耦合、参数标定和论文机制 claim；`W_F=D_zeta` 仍仅是代数恒等式，Route H Gate A v01 继续保持 `failed_invalid_numerics`。
