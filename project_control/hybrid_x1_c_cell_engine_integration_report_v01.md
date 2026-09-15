---
report_id: REPORT-PRL-HYBRID-X1-C-V01
status: passed_frozen
completed_at: 2026-08-01
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
---

# Hybrid X1-C 真实 cell-engine—材料迁移集成报告 v01

## 结论

X1-C 已完成。真实 fork `cell`、`local_mesh_refiner`、同步 `RemeshEvent` 与父项目 `MyocardialMaterialTransferSink` 已组成一条可编译、可执行、可回归的端到端 C++ 路径。X1-B 的“合成快照 consumer”证据已提升为“真实 remesher 触发生产 consumer”的集成证据。

## 架构修订

原 snapshot builder 是 `local_mesh_refiner` 的私有成员，无法供初始材料注册复用。X1-C 将纯只读转换提取为公共 `capture_surface_snapshot(const cell&)`，并让注册与事件发射共用它。这样没有公开 remesher 的内部修改逻辑，也没有把初始化绑定到 edge-length 配置。

fork 同时增加嵌入开关：父项目可关闭 fork tests 和 standalone executable，只链接真实重网格所需 target；fork 独立构建的默认入口不变。

## TDD 证据

- RED：父项目真实集成 target 首次编译因 `prl_cell_engine/cell_surface_snapshot.hpp` 不存在而失败；
- GREEN/swap：真实 edge swap 触发 sink，cell/material revision 对齐且材料量守恒；
- GREEN/failure：超出重绑定距离时真实 callback 异常传播，材料 registry 不提交；
- GREEN/split→merge：同一 cell 和 sink 连续消费两次真实操作，revision 从 0→1→2。

## 失败边界

sink 失败只对材料 registry 保持原子性，不能回滚已经完成的 cell topology edit。上层 future driver 必须把异常升级为 fatal step failure，并通过检查点恢复。这一约束已写入架构 v06 和集成行为测试，不能被解释为可恢复 warning。

## 验收

| 检查 | 结果 |
|---|---|
| parent C++ CTest | `11/11 passed` |
| real swap integration | passed |
| real split→merge integration | passed |
| real callback failure propagation | passed |
| fork standalone CTest | `126/126 passed` |
| parent Python hybrid + Stage 0/1/2 | `63 passed` |
| fork GitHub Actions | run `30698500648`, passed |
| whitespace/error check | passed |

fork 公共头仍有上游既存的 ignored-qualifier 与 unused-parameter 告警，因此没有把整个外部翻译单元强制升级为 `-Werror`；X1-C 不借机修改无关上游 API。普通 GCC 构建、真实行为测试和 fork 全量回归均通过。

## 冻结边界与下一切片

本阶段只冻结真实重网格—材料迁移闭环，不包含完整时间推进、主动收缩、体积 ECM、流体、多细胞规模或生理结论。下一安全切片是 X1-D 多细胞规模/性能基线；它应给出不同 cell 数和 remesh 频率下的吞吐、峰值内存、并发缩放与确定性结果。
