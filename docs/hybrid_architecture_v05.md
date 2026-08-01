---
architecture_id: ARCH-PRL-HYBRID-V05
status: frozen_x1_b_cpp_material_transfer
frozen_at: 2026-08-01
inherits_interface: ARCH-PRL-HYBRID-V04
cell_engine_commit: 7fc0ae0b2c01218c540d40b48bf81ce3db22e42b
---

# PRL 自有长期混合架构 v05

本版本冻结 X1-B：父项目 C++ core 已实现 `RemeshEventSink` 的生产级心肌材料状态迁移模块。生物学状态继续由 persistent material-point ID 拥有；cell engine 仅产生拓扑事件与表面快照。

## 模块边界

```text
prl-cell-engine
  synchronous RemeshEvent + before/after snapshots
                         │
                         ▼
MyocardialMaterialTransferSink        PRL parent C++ core
  cell registry lookup
  geometric rebind
  fiber transport
  conservation audit
                         │
                         ▼
MyocardialCellMaterialState
  region + active state + fiber + reference weight
```

公共入口只有四个动作：构造 sink、注册初始 cell、同步消费一次 remesh event、读取 cell state/audit。几何搜索、宿主解析、纤维投影、并发锁和异常原子性均封装在实现内部。

## 持久材料点与宿主

- `material_point_id` 拥有 region、active state、fiber direction 和 reference weight；
- 当前宿主使用三个 persistent vertex ID 加重心坐标表示，不存 local face ID；
- node 或 face 的局部顺序变化不会改变材料点身份或宿主解析；
- 一次成功事件只更新宿主、纤维和 material-state revision，不重建生物学身份。

## 一次事件的冻结顺序

1. 验证 event、before、after 的 cell ID 与 revision；
2. 按 cell 获取独立锁并核对已注册 revision；
3. 在 before snapshot 上恢复每个材料点的空间位置；
4. 在 after snapshot 上执行确定性的全局最近三角形搜索；
5. 超出 `maximum_rebind_distance` 时带 material-point ID 和误差 fail-fast；
6. 将旧纤维投影到新宿主切平面、单位化并保持 director 符号；
7. 计算审计指标；全部成功后一次性提交新状态与 revision。

步骤 3–6 使用临时副本。任何异常均不提交材料状态、revision 或 audit。cell engine 已完成的拓扑操作不在本模块中回滚；调用者必须把 callback 异常视为该 simulation step 的致命失败。

## 并发语义

- cell registry map 只在查找或注册时短暂加锁；
- 每个 cell 有独立 mutex，不同细胞的事件可并行迁移；
- 同一 cell 的事件串行化，并通过 revision 阻止漏序或重复消费；
- `cell_state()` 和 `last_audit()` 返回拷贝，不暴露可变内部状态。

## 冻结审计指标

- point count；
- region retention fraction；
- active-state residual；
- maximum fiber norm error；
- maximum fiber tangency error；
- minimum fiber alignment；
- maximum geometric rebind error；
- material-point ID retention fraction；
- reference-weight residual。

## 已验证与未宣告

父项目 C++ 行为测试覆盖 swap、split、merge、局部编号重排、非共面纤维投影、失败原子性和多细胞并发；Python X0-C oracle 与 Route H 回归保持通过。X1-B 尚未把该 sink 接到一个真实 `local_mesh_refiner` 执行中，因此下一切片 X1-C 必须完成真实 remesher—材料迁移端到端测试后，才能宣称生产事件源与生产迁移 consumer 已闭环。
