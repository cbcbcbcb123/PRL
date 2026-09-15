---
report_id: REPORT-PRL-HYBRID-X1-A-V01
status: passed_frozen
completed_at: 2026-08-01
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_commit: bbcdad4ae4f0134dec9a30c523ef253b314fc8f3
official_upstream_base: 38af45154070b2b08dcdb25cbe629de499f382d9
---

# Hybrid X1-A remesh event hook 执行报告 v01

## 结论

X1-A 已完成并冻结。受控 `prl-cell-engine` 现在对每次已接受的 edge split、swap、merge 同步产生 PRL-owned before/after snapshot 事件；节点身份不再依赖会被重排或复用的 local ID。未修改接触模型、重网格判据、力学能量或 ECM 算法。

## 实现范围

- 在 fork 内建立 `prl_cell_engine/remesh_contract.hpp` 单一合同源；
- 为 cell 增加单调 mesh revision；
- 为 node 增加 cell-scoped、不可复用的 persistent ID；
- 为 `local_mesh_refiner` 增加可选 `RemeshEventSink`；
- split、swap、merge 在操作完成后同步发出事件；
- 无 sink 时不构造 snapshot，原三参数构造方式保持兼容；
- 父项目原 `prl/core/remesh_contract.hpp` 改为兼容转发头。

## TDD 证据

1. swap 事件测试先因合同和构造器不存在而失败，随后通过；
2. split 事件测试先以 `t7=0` 失败，随后通过；
3. merge 事件测试先以 `t10=0` 失败，随后通过；
4. rebase 持久身份测试先以 `t11=0` 失败，证明 local ID 不满足合同，加入 persistent ID 后通过。

## 验收结果

| 验收项 | 结果 |
|---|---|
| fork focused local-remesher CTest | `5/5 passed` |
| fork complete local CTest | `126/126 passed` |
| split event topology delta | `+1 node, +2 faces`，passed |
| swap event topology delta | node/face 不变，passed |
| merge event topology delta | `-1 node, -2 faces`，passed |
| persistent IDs across rebase | 100% retained and unique |
| rejected operation revision | unchanged |
| accepted no-sink operation revision | incremented once |
| owned fork GitHub Actions | run `30692305769`, passed |
| parent C++ contract test | `1/1 passed` |
| parent hybrid Python | `14 passed` |
| parent Stage 0 v06 | `11 passed` |
| parent Stage 1/2 | `38 passed` |

## 仓库同步

- owned repository：`https://github.com/cbcbcbcb123/prl-cell-engine`；
- feature branch：`codex/remesh-event-hook`；
- owned `main`：`bbcdad4ae4f0134dec9a30c523ef253b314fc8f3`；
- parent submodule：固定到同一精确 commit；
- official upstream base 与 immutable baseline tag 保持不变。

## 冻结边界与下一切片

本报告只冻结真实事件源、身份和版本语义。X1-B 才实现 C++ 材料状态迁移 consumer；在 X1-B 验收前，不得宣称大规模重网格过程中区域、纤维和主动状态已由生产 C++ 路径守恒。
