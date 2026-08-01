---
architecture_id: ARCH-PRL-HYBRID-V07
status: frozen_x1_d_multicell_scale_baseline
frozen_at: 2026-08-01
inherits_interface: ARCH-PRL-HYBRID-V06
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
---

# PRL 自有长期混合架构 v07

本版本冻结 X1-D：父项目现在具有可复现的 Release C++ 多细胞 remesh—材料迁移微基准。它使用真实 `cell`、`local_mesh_refiner`、同步 remesh callback 和 `MyocardialMaterialTransferSink`，不使用 mock 或合成事件。

## 基准执行边界

```text
N independent real cells
        │ one cell is owned by one worker for the whole workload
        ▼
dynamic work queue ── 1 or 4 std::thread workers
        │
        ▼
real swap or split→merge topology edits
        │ synchronous before/event/after callback
        ▼
shared MyocardialMaterialTransferSink
        │ per-cell state lock + deterministic transfer
        ▼
revision / material invariants + semantic digest
```

同一 cell 的事件始终串行；不同 cell 才能并发。计时区只包含真实拓扑编辑和同步材料迁移，cell 构造与初始注册单独计时。进程峰值 RSS 覆盖完整 workload。

## 两种冻结 workload

- `alternating_swap`：在同一 cell 上交替 swap 两条对角边，保持节点/面数量不变，用于测量高频 callback、快照和材料迁移吞吐。
- `split_merge`：每个新鲜 cell 执行一次真实 split 和一次真实 merge，覆盖节点/面动态分配与回收。只执行一对操作，避免 merge 引起的几何收缩把网格退化成本混入基准。

每次运行都检查 cell/material revision、point count、region、active state、persistent material-point ID、reference weight、rebind audit，并对最终状态计算同一构建内稳定的 FNV-1a semantic digest。串行与并行 digest 不同即失败。

## v01 参考环境与结果

环境：`prl-simucell3d-x0:38af451`，GCC 14.2.0，CMake `Release`，WSL2/Linux x86_64；每个场景独立运行三次，报告中位吞吐和最大峰值 RSS。绝对性能不设跨硬件 pass/fail 阈值。

| workload | cells | events | threads | median events/s | max peak RSS |
|---|---:|---:|---:|---:|---:|
| alternating swap, high frequency | 128 | 16,384 | 1 | 104,039 | 15,228 KiB |
| alternating swap, high frequency | 128 | 16,384 | 4 | 291,501 | 15,228 KiB |
| alternating swap, scale | 1,024 | 32,768 | 1 | 109,372 | 15,228 KiB |
| alternating swap, scale | 1,024 | 32,768 | 4 | 351,776 | 15,228 KiB |
| alternating swap, largest | 4,096 | 131,072 | 4 | 397,332 | 21,760 KiB |
| split→merge, scale | 1,024 | 2,048 | 1 | 53,633 | 15,228 KiB |
| split→merge, scale | 1,024 | 2,048 | 4 | 103,022 | 15,228 KiB |
| split→merge, largest | 4,096 | 8,192 | 4 | 143,973 | 40,960 KiB |

观察到的 4-thread speedup 为：高频 swap `2.80×`、1,024-cell swap `3.22×`、split→merge `1.92×`。从 1,024 到 4,096-cell swap 场景估算的增量峰值 RSS 约为 `2.13 KiB/cell`；该值受分配器和 RSS 粒度影响，只作为同环境基线。

## 冻结结论与限制

X1-D 证明当前 C++ seam 能在 4,096 个独立小表面细胞上保持材料语义、跨线程确定性和有效并行扩展。它不证明完整 cell mechanics、contact、主动收缩、ECM assembly、coupled timestep、血流或器官级网格的性能；8-node cell 的 events/s 不能外推为真实心脏吞吐。

下一安全切片为 X1-E 单细胞主动收缩 C++ 最小闭环：把 material-point active state 与纤维方向接入可审计的主动能量/力和功率端口，同时保持 remesh 前后语义一致；暂不同时接入体积 ECM 或血流。
