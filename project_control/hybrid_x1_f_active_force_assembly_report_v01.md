---
report_id: REPORT-PRL-HYBRID-X1-F-V01
status: passed_frozen
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: 29edb7925137277e9e0633cc73cfe86605bd8361
result_id: PRL-HYBRID-X1-F-ACTIVE-FORCE-ASSEMBLY-V01
---

# Hybrid X1-F 主动力单步装配报告 v01

## 结论

X1-F 已完成。父项目新增 `assemble_active_cell_forces`，把 X1-E 的 persistent-vertex active forces 累加到真实 cell engine `node.force_` 缓冲区，并返回同 revision 的能量—功率—力审计。受控 fork 新增与生物学无关的原子 `apply_surface_vertex_forces` seam；没有把 active state、fiber 或心肌类型写入 fork node/face。

## TDD 证据

1. tracer RED：真实集成 target 首先因 `prl/cell_engine/active_force_assembly.hpp` 不存在而编译失败。
2. accumulation GREEN：在真实 cell force buffer 中预置非零被动力，装配后每节点等于 baseline 加主动贡献，证明接口执行累加而非覆盖。
3. failure contract：陈旧 material revision、陈旧 target revision 和未知 persistent vertex 均在写入前拒绝，原缓冲区逐分量不变；fork 独立测试另覆盖非有限力拒绝。
4. remesh composition：真实 edge swap 与材料迁移后，同一 contraction unit 在 revision 1 成功装配，能量、功率、合力、合矩和节点力与独立求值一致。

## 接口与失败边界

- 父项目负责捕获当前 surface snapshot、执行主动求值、转换 force DTO 和汇总功率账本；
- fork 负责按 stable ID 解析 used node，并检查所有 resulting force buffers 后一次提交；
- 目标 cell 在调用期间必须由一个 worker 独占；
- 装配不改变 mesh revision，不更新激活，也不调用 remesh、被动力、接触或时间积分；
- 当前 stock solver 没有自动 hook，未来 owned driver 必须在被动力之后、位置更新之前显式调用。

## 定量结果

| 检查 | 结果 |
|---|---|
| real-cell passive + active accumulation | passed |
| active energy ledger | `0.01015625` |
| active input-power ledger | `0.06381360077604267` |
| injected nodal-force L2 norm | `0.29033924123342336` |
| net force / moment residual | `≤1e-12` |
| stale/unknown/non-finite failure atomicity | passed |
| real post-remesh assembly at revision 1 | passed |
| parent C++ CTest | `23/23 passed` |
| fork standalone CTest | `128/128 passed` |
| owned parent core strict warnings | `13/13 passed` |
| parent Python hybrid + Stage 0/1/2 | `63 passed` |

fork 新增翻译单元在 `-Wall -Wextra -Wpedantic -Werror` 下仅被既有 public headers 的 ignored-qualifier/unused-parameter 告警阻断；对这两类已知继承告警降级后，新翻译单元严格编译通过。未借 X1-F 修改无关上游 API。

## Git 与 CI 边界

fork 提交 `29edb7925137277e9e0633cc73cfe86605bd8361` 已推送到 `origin/codex/cell-engine-integration-seam`。fork workflow 只监听 `main` push 和指向 `main` 的 pull request；本次 branch push 未产生 GitHub Actions run，因此本报告以 Docker 内完整 `128/128` 回归为当前远端同步前的可复现验证证据。

## Claim guard

X1-F 证明主动力可审计地进入真实 cell-engine force buffer，并保持被动力、revision 和 remesh 后身份语义。它不证明 stock solver 已自动调用该 seam，不证明已经执行位置更新或获得稳定收缩轨迹，也不证明 ECM/血流耦合或任何生理效应。
