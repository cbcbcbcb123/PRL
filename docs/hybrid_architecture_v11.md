---
architecture_id: ARCH-PRL-HYBRID-V11
status: frozen_x1_h_owned_passive_contact_geometry_step
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V10
cell_engine_commit: b8828da18bfda62f28cece95027ba65edd431a0f
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# PRL 自有长期混合架构 v11

本版本冻结 X1-H：PRL owned driver 现能在一个真实 cell-engine cell 上顺序执行真实 face-face 接触装配、`cell::apply_internal_forces(dt)` 被动力装配、X1-E/F 主动力装配、一次 overdamped 位置更新，以及 face/node/cell 派生几何缓存刷新。它仍是单步机制路径，不是 stock solver 自动 orchestration 或连续轨迹。

## 冻结入口与执行顺序

- 父项目入口：`prl::cell_engine::advance_owned_active_cell_overdamped_one_step`；
- fork 位置/几何原语：`prl::cell_engine::advance_surface_overdamped`；
- fork 显式缓存入口：`prl::cell_engine::refresh_surface_geometry`；
- fork 失败清理入口：`prl::cell_engine::reset_surface_forces`。

```text
target + revision-matched material + contraction units
        │ validate dt, damping, ownership/context and empty force buffers
        │ capture active snapshot; evaluate active inputs without writes
        ▼
refresh current face/cell/node geometry caches
        ▼
optional real contact_face_face_via_coupling::run(context)
        │ one mobile target + force-only static bodies only
        │ audit target force and context force/moment balance
        ▼
target.apply_internal_forces(dt)
        │ real pressure/surface-tension/membrane/bending/regularization path
        │ audit passive increment and complete pre-active force buffer
        ▼
evaluate + inject active persistent-vertex forces
        ▼
validate every total force, displacement, pending position and pending geometry
        ▼
atomic commit: positions + force reset + face/cell/node cache refresh
        │ clear static-body force buffers
        ▼
OwnedActiveCellOverdampedStepAudit
        └── STOP: no time loop, no automatic remesh, no ECM/flow advance
```

## 接触合同

X1-H 只接受真实 `contact_face_face_via_coupling`，并把 context 收窄为一个 mobile target 与静态接触体。context 中 cell/local ID 必须唯一且与向量顺序一致；会触发 epithelial–epithelial 位置耦合的类型组合被拒绝。成功算例验证目标接触力非零、静态体位置不变、作用—反作用合力残差为 0、合力矩残差为 `1.77636e-15`，并在返回前清空静态体力缓存。

接触核的点—三角形最近点面内公式原先把首顶点加了两次，导致距离不具平移不变性。受控 fork 已修正为 `a + v(b-a) + w(c-a)`，并加入非原点三角形回归测试。该修复属于实际接触路径正确性的必要条件，不改变接触本构。

## 几何提交与失败边界

所有 pending positions 在写入前用于独立计算并验证每个三角形面积、总面积、闭合面有向体积、面积加权 centroid 和最小三角形面积。只要出现非有限坐标、退化三角形、零体积或非法面—节点引用，位置与力缓存均不提交。成功后同步刷新：

- face normal 与 face area；
- cell surface area、volume 与 centroid；
- 在当前接触配置下的 node normal 与 curvature。

被动力装配之后、位置提交之前若主动审计失败，异常向上传播，节点位置保持不变，目标与接触体的力缓存清零，几何缓存保持与当前位置一致。

上游 `cell::apply_internal_forces` 和 contact `run` 仍是 `noexcept`/assert 风格；其中进程级 assertion 不能被 owned driver 转换成 C++ 异常。X1-H 冻结的是已验证输入与可抛异常路径的传播/清理，不宣称所有上游断言已事务化。被动力装配还可能更新 pressure、target volume 和能量缓存；X1-H 不承诺失败时回滚这些标量历史状态。

## 单步制造审计

在八节点、十二三角形 cell，`dt=1e-3`、统一节点阻尼 `zeta=10` 的无量纲制造算例中：

| 路径 | 接触力 L2 | 被动力增量 L2 | 总力 L2 | 位移 L2 | 步后面积 | 步后体积 | 最小面面积 |
|---|---:|---:|---:|---:|---:|---:|---:|
| passive + active | `0` | `1.50084` | `1.8092` | `1.80920e-4` | `13.2098` | `2.99952` | `0.901269` |
| contact + passive + active | `40` | `1.50084` | `40.7549` | `4.07549e-3` | `13.1954` | `2.99352` | `0.899466` |

这些数值只用于无量纲软件回归。接触强度和几何是制造参数，不能解释为生理量或稳定轨迹证据。

## Claim guard 与后续顺序

X1-H 证明的是一个 PRL-owned、真实被动力/接触力/主动力、预提交几何验证和派生缓存刷新组成的可审计单步。它不证明统一节点阻尼具有空间一致性，不证明时间积分稳定或收敛，不证明循环重网格无伪能量，不证明动态双向 cell–ECM/FSI、EFE 机械记忆、谱系来源或生理预测，也不改变 Route H Gate A v01 的 `failed_invalid_numerics`。

后续必须依次执行 X1-I（阻尼空间一致性）、X1-J（`DeltaPsi_remesh` 账本与循环重网格漂移）和 X1-K（短轨迹多门禁）。X1-K 通过前禁止进入 ECM/血流长耦合、参数标定或论文机制 claim。
