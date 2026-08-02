---
architecture_id: ARCH-PRL-HYBRID-V09
status: frozen_x1_f_active_force_assembly
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V08
cell_engine_commit: 29edb7925137277e9e0633cc73cfe86605bd8361
---

# PRL 自有长期混合架构 v09

本版本冻结 X1-F：X1-E 生成的主动节点力已经能够通过持久顶点 ID 原子累加到真实 cell engine 的 `node.force_` 缓冲区，并在同一次装配调用中返回主动能量、激活输入功率、合力、合矩和纤维对齐审计。该缓冲区正是 cell engine time integrator 随后读取的力状态。

## 单步装配路径

```text
current real cell + material registry + frozen contraction units
        │ capture snapshot; require equal cell/revision
        ▼
evaluate_active_contraction()
        │ active energy / input power / persistent-vertex forces
        ▼
assemble_active_cell_forces()
        │ convert without changing identity
        ▼
apply_surface_vertex_forces()
        │ validate revision, IDs, finiteness and resulting buffers
        │ no write before all validation succeeds
        ▼
existing node.force_ += active force
        │ passive/contact contributions remain present
        ▼
ActiveCellForceAssemblyAudit
        └── STOP: X1-F does not call the time integrator
```

## 父项目与 fork 的职责

父项目拥有主动生物力学：激活状态、纤维方向、preferred-length contraction units、主动能量、输入功率和守恒阈值。公共入口为 `prl::cell_engine::assemble_active_cell_forces`。

受控 fork 只拥有通用 cell-engine seam：`prl::cell_engine::apply_surface_vertex_forces` 接收 persistent vertex ID 和三维力增量，不知道心肌、激活、ECM 或血流。它先完成以下检查，再一次性提交结果：

1. expected mesh revision 与目标 cell 一致；
2. 输入非空、顶点 ID 唯一且全部属于当前 used nodes；
3. 输入力、原缓冲区、累加后缓冲区和审计量均有限；
4. 目标 cell 内 persistent vertex ID 唯一。

因此未知顶点、重复顶点、陈旧 revision、非有限输入或可能产生非有限缓冲区时，不会留下部分力写入。调用期间仍遵循 X1-D 的 one-cell/one-owner 规则，不宣告同一 cell 的并发 force assembly 安全。

## 冻结的顺序语义

X1-F 只冻结以下顺序合同：在一次未来 timestep 中，remesh/material transfer 完成且 passive/contact forces 已经装配后，active assembly 以**加法**进入同一 `node.force_`，随后才允许 time integrator 消费该缓冲区。主动装配不覆盖被动力，不改变位置、拓扑 revision、材料状态或 contraction-unit reference length。

当前 upstream-derived `solver::run_iteration` 尚未自动调用该入口；因此生产 driver 必须显式把它放在 passive force assembly 与 position update 之间。X1-F 的测试通过预置非零被动力证明加法语义，但不把这等同于完整 solver orchestration 已接通。

## 验证结果

制造 cell 在 `revision=0` 时预置每节点被动力 `(0.01,-0.02,0.03)`，主动装配后每个 used node 均精确等于“原缓冲区 + X1-E 主动力”。主动账本保持 `Psi=0.01015625`、`P_act=0.06381360077604267`，注入力的节点 L2 范数为 `0.29033924123342336`；合力、合矩残差不超过 `1e-12`。

真实 edge swap 后，mesh/material/assembly revision 同步为 1；同一冻结 contraction unit 再次装配成功，能量、功率与 persistent-vertex force scatter 均与重网格后的独立主动求值一致。陈旧材料 revision、陈旧目标 revision、未知顶点和非有限输入均被拒绝，力缓冲区保持原值。

## 未宣告与下一切片

X1-F 没有改变 `solver::run_iteration`，没有调用 position integrator，也没有产生一步位移、稳定轨迹或收缩率；更不包含 ECM、接触参数标定、血流或生理结论。Route H Stage 2 Gate A 仍为 `failed_invalid_numerics`。

下一安全切片为 X1-G：建立 PRL 自有的单步 driver/hook，把已冻结的 remesh/material、passive force、active assembly 和一次 overdamped position update 按顺序接通，并只验收一步位移方向、revision、离散功率/耗散和失败传播；仍不运行长轨迹，也不接 ECM 或血流。
