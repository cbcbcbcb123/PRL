---
report_id: REPORT-PRL-HYBRID-X1-D-V01
status: passed_frozen
completed_at: 2026-08-01
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
result_id: PRL-HYBRID-X1-D-MULTICELL-BASELINE-V01
---

# Hybrid X1-D 多细胞规模与性能基线报告 v01

## 结论

X1-D 已完成。新增 `prl_multicell_remesh_benchmark`，通过公开 CLI 在真实 C++ 路径上配置 cell 数、每 cell 事件数、线程数、operation pattern 和确定性检查。正式 Release 矩阵覆盖 4,096 个 cell、131,072 次连续 swap 事件，以及 4,096 个 cell 的真实 split→merge 动态拓扑事件。

## TDD 证据

1. tracer RED：CMake 因 benchmark 入口文件不存在而失败；实现多细胞真实 swap workload 后 scale smoke 转绿。
2. determinism RED：CLI 拒绝尚未实现的 `--verify-determinism`；加入同配置 serial/parallel 双运行和 semantic digest 比较后转绿。
3. dynamic-topology RED：CLI 拒绝尚未实现的 `--operation-pattern split_merge`；加入真实 split→merge workload 和审计后转绿。

所有测试都通过 CLI 触发真实 cell-engine 和材料 sink，没有暴露私有方法或替换事件源。

## 方法

- 每个 worker 独占一个 cell 的整个事件序列，避免非法的同 cell 并发拓扑编辑；
- 多个 cell 共享一个生产 `MyocardialMaterialTransferSink`，验证 registry map 和 per-cell locks；
- setup 与 remesh 分开计时，吞吐只统计 remesher + 同步材料迁移；
- 三次独立进程采样取中位吞吐，峰值内存取最大 `ru_maxrss`；
- 性能是环境基线，不作为跨机器绝对门槛；状态审计和 digest 一致性是硬门槛。

## 正式结果摘要

- 4,096-cell alternating swap：`131,072` events，4-thread median `397,331.96 events/s`，max RSS `21,760 KiB`；
- 4,096-cell split→merge：`8,192` events，4-thread median `143,972.67 events/s`，max RSS `40,960 KiB`；
- 4-thread speedup：高频 swap `2.80×`，1,024-cell swap `3.22×`，split→merge `1.92×`；
- serial/parallel digest：swap 与 split→merge 均 exact match；
- 128-cell 显式 determinism run：reference/parallel digest 均为 `1c0cefe2ce3ecabc`。

完整原始重复运行位于 `results/hybrid/x1_d_multicell_baseline_v01/summary.json`。

## 验收

| 检查 | 结果 |
|---|---|
| X1-D C++ scale/determinism/split→merge tests | passed |
| parent C++ CTest | `14/14 passed` |
| parent Python hybrid + Stage 0/1/2 | `63 passed` |
| Ruff | passed |
| formal Release matrix | passed |
| serial/parallel semantic digest | exact match |
| diff/JSON validation | passed |

## 限制与下一切片

本报告是 8-node 独立 cell 的 remesh/material-transfer 微基准，不含接触检测、内力、主动收缩、ECM、完整时间步或 I/O；因此不形成器官级规模承诺。下一安全切片为 X1-E 单细胞主动收缩 C++ 最小闭环，先冻结主动能量/力、状态更新、功率与 remesh 一致性，再讨论体积 ECM 接入。
