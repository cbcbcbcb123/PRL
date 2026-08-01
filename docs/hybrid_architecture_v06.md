---
architecture_id: ARCH-PRL-HYBRID-V06
status: frozen_x1_c_real_cpp_integration
frozen_at: 2026-08-01
inherits_interface: ARCH-PRL-HYBRID-V05
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
---

# PRL 自有长期混合架构 v06

本版本冻结 X1-C：真实 `local_mesh_refiner` 与父项目 `MyocardialMaterialTransferSink` 已在同一条 C++17 执行路径中闭环。该闭环覆盖 cell 初始注册、真实 edge swap、split、merge、同步 remesh event、材料重绑定、纤维迁移、审计与失败传播。

## 端到端路径

```text
real cell
  │ capture_surface_snapshot()
  ▼
MyocardialMaterialTransferSink::register_cell()
  │
  ▼
local_mesh_refiner::swap_edge / split_edge / merge_edge
  │ before snapshot → topology edit → revision++ → after snapshot
  ▼
RemeshEventSink::on_remesh()
  │ geometric rebind + fiber transport + conservation audit
  ▼
MyocardialCellMaterialState at the same cell revision
```

## 冻结的集成边界

- `prl::cell_engine::capture_surface_snapshot(const cell&)` 是只读公共适配器；初始注册与事件发射共用同一实现，避免形成两种快照语义。
- fork 可在父项目中关闭自身 tests、Python binding 和 standalone executable 后作为库嵌入；独立构建时三者的既有默认行为保持不变。
- 父项目集成 target 只显式链接 `prl_core`、`triangulation_modules` 和 `mesh`，不依赖完整 solver、contact、I/O 或 coupled driver。
- 生物学材料状态仍由父项目 persistent material-point registry 拥有；cell-engine node/face 不持有 region、active state、fiber 或 reference weight。

## 成功与失败语义

成功事件结束时必须同时满足：

1. cell mesh revision 增加一次；
2. material-state revision 与 cell revision 相等；
3. persistent material-point ID、region、active state 与 reference weight 保持；
4. 新宿主可解析，纤维完成切平面投影，审计记录对应真实操作。

如果 sink 在回调中拒绝迁移，异常从真实 `local_mesh_refiner` 原样传播；材料状态、material revision 和 audit 均不提交。但 remesher 已完成的拓扑编辑和 cell revision 不回滚。因此该异常是当前 simulation step 的致命失败：上层 driver 必须中止并从最近检查点恢复，不得继续下一次拓扑编辑或力学更新。

## 已验证范围

- 真实 edge swap：region、active state、reference weight、revision 和 audit 闭环；
- 真实 edge split 后 merge：同一 registry 连续消费 revision 1、2；
- 真实 callback 拒绝：异常含 material-point ID 与距离，材料侧保持注册 revision；
- fork 独立构建和 126 项既有测试保持通过；
- 父项目 11 项 C++ tests 与 63 项 Python hybrid/Route H regression 通过。

## 未宣告与下一切片

X1-C 不等于完整 timestep driver，也不宣告主动收缩、体积 ECM 时间积分、血流耦合、多细胞规模性能或生理标定完成。下一安全切片为 X1-D 多细胞 remesh—材料迁移规模与性能基线：先量化吞吐、内存、并发和确定性，再决定主动力学接入预算。
