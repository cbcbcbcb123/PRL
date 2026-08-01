---
report_id: REPORT-PRL-HYBRID-X1-B-V01
status: passed_frozen
completed_at: 2026-08-01
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_commit: 7fc0ae0b2c01218c540d40b48bf81ce3db22e42b
---

# Hybrid X1-B C++ 心肌材料状态迁移执行报告 v01

## 结论

X1-B 已完成并冻结。父项目新增 `MyocardialMaterialTransferSink`，把 X0-C Python oracle 的 persistent ID、区域、主动状态、纤维投影与几何重绑定语义迁入 C++17。实现不把生物学状态放入 fork 的 node/face，也不依赖 local face ID。

## 架构选择

审查过两条路径：

1. 将材料状态写入 cell-engine node/face；接口较少，但状态会随易变拓扑扩散，违反 ADR-PRL-0001；
2. 在父项目实现独立 `RemeshEventSink`，由 persistent material-point ID 拥有生物学并以 persistent vertex ID 表达当前宿主。

采用路径 2。它把几何搜索、状态迁移、审计和并发收进一个深模块，同时让 remesher 保持可替换。

## TDD 证据

- tracer bullet 首次编译因公共头 `myocardial_material_transfer.hpp` 不存在而失败，随后完成 swap 端到端行为并转绿；
- split 与 merge 复用同一公共路径并分别通过，merge 同时验证连续 revision；
- 失败原子性测试最初因异常不包含 material-point ID/距离而失败，补齐可诊断错误后转绿；
- 后续行为测试冻结 persistent host IDs、切平面纤维投影和多细胞并发。

## 实现产物

- `cpp/include/prl/core/myocardial_material_transfer.hpp`：稳定公共接口；
- `cpp/src/myocardial_material_transfer.cpp`：重绑定、纤维迁移、审计与每 cell 并发实现；
- `cpp/tests/myocardial_material_transfer_test.cpp`：七个公共行为测试；
- fork `RemeshTransferAudit`：向后兼容追加 rebind、ID 和 reference-weight 三项审计字段。

## 验收

| 检查 | 结果 |
|---|---|
| parent C++ CTest | `8/8 passed` |
| GCC 14 `-Wall -Wextra -Wpedantic -Werror` build | passed |
| edge swap / split / merge | passed |
| local node/face reorder independence | passed |
| non-coplanar fiber projection | passed |
| out-of-distance failure atomicity | passed |
| multicell concurrent callbacks | passed |
| fork complete CTest | `126/126 passed` |
| parent Python hybrid + Stage 0/1/2 | `63 passed` |
| fork GitHub Actions | run `30697145303`, passed |

## 限制与下一切片

当前 C++ tests 以合同快照直接调用 sink，尚未从真实 `local_mesh_refiner` 触发。X1-C 将建立父项目 integration target，把真实 fork cell、一次 remesh 操作和 `MyocardialMaterialTransferSink` 串成同一条 C++ 路径，并验证 callback 失败传播策略。
