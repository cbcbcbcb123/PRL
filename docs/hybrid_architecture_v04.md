---
architecture_id: ARCH-PRL-HYBRID-V04
status: frozen_x1_a_remesh_event_source
frozen_at: 2026-08-01
inherits_interface: ARCH-PRL-HYBRID-V03
cell_engine_commit: bbcdad4ae4f0134dec9a30c523ef253b314fc8f3
---

# PRL 自有长期混合架构 v04

本版本冻结 X1-A：受控 `prl-cell-engine` 已成为逐操作 remesh event 的真实事件源。X0-C/D 冻结的材料语义和数值门槛不变；本切片只把原先的接口合同接入 C++ 高性能内核，不实现材料状态迁移算法。

## 冻结边界

```text
prl-cell-engine local_mesh_refiner
  accepted split / swap / merge
        │ synchronous callback
        ▼
prl::core::RemeshEventSink
  before snapshot + operation + after snapshot
        │ X1-B consumer
        ▼
PRL-owned myocardial material-state registry
```

- 合同单一真源：`external/simucell3d/include/prl_cell_engine/remesh_contract.hpp`；
- 历史 include 兼容面：`cpp/include/prl/core/remesh_contract.hpp` 只转发到上述合同，不再复制类型定义；
- 所有跨边界对象均为 PRL value types；上游指针、可复用 local node ID 和 face ID 不跨边界；
- callback 在单次已接受拓扑操作完成后、同一细胞下一次拓扑修改前同步调用；
- `refine_meshes()` 可对不同细胞并发触发 callback，共享 sink 必须自行保证线程安全。

## 身份与版本语义

1. 每个 node 获得 cell-scoped 64-bit `persistent_id`；创建后不因 `cell::rebase()` 改变，也不随空槽复用而复用；
2. 每个 cell 保存单调 `mesh_revision`；每次已接受 split、swap 或 merge 恰好增加 1；
3. 被拒绝且尚未修改拓扑的操作不改变 revision，也不发事件；
4. event 的 `(cell_id, before_revision, after_revision)` 必须与两侧 snapshot 一致，且 `after_revision > before_revision`；
5. 无 sink 时仍更新 revision，但不构造 before/after snapshot，保留原调用方式和低开销路径。

## 操作级行为

| 操作 | node / face 数量 | 持久身份语义 |
|---|---|---|
| edge swap | 不变 / 不变 | 全部 node ID 保留 |
| edge split | `+1 / +2` | 旧 node ID 全保留，新 node 获得新 ID |
| edge merge | `-1 / -2` | 未被替换 node 的 ID 保留，合并点获得新 ID |

## 已验证内容

- `prl-cell-engine` 本地完整 CTest：`126/126 passed`；
- 局部 remesher 定向 CTest：`5/5 passed`；
- split、swap、merge 各自产生一个合法同步事件；
- 无 sink 的已接受操作仍推进 revision；
- `cell::rebase()` 前后持久 node ID 集合一致且唯一；
- 父项目 C++ 合同、Python hybrid、Stage 0 v06 与 Stage 1/2 回归由 X1-A 执行报告记录。

## 尚未完成

X1-A 不宣告 C++ 材料状态迁移、主动收缩、体积 ECM 时间积分、多细胞规模、血流耦合或生理标定完成。下一安全切片 X1-B 将实现消费 `RemeshEventSink` 的 C++ 心肌材料状态迁移适配器，并复用 X0-C 已冻结的区域、纤维与主动状态守恒测试。
