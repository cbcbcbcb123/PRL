---
report_id: REPORT-PRL-HYBRID-X1-K-V10-R1-MIDPOINT-DIAGNOSIS
status: failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind
contract_commit: e54bc5933387070c697f5c88218f37f25faea4c3
parent_before_v10: 855bd8b7467761ba7fcdaa49632bed2ee5681e85
cell_engine_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
v09_status: failed_r1_geometry_cache_force_finite_gate
route_h_gate_a_v01: failed_invalid_numerics
x1_k_passed: false
r1_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v10 R1 midpoint-collapse 失败机制 / 可修复性诊断失败报告

## 1. 冻结结论

v10 冻结为
`failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind`，不是诊断通过，也不是 R1 或 X1-K 通过。首个硬失败发生在候选边完整性门禁：split 节点共有 4 条相邻边，public `can_be_merged` 对 4 条均返回 `true`，但候选 3、local edge `(2,8)` 的真实 `merge_edge -> synchronous RemeshEvent -> production MyocardialMaterialTransferSink` 路径因 material point 101 的 rebind 距离
`0.047434164902525666 > 1e-12` 抛出异常，formal response 保留 exit code 1。

因此，合同要求的“所有 eligible 候选完整执行、再作唯一机制分类”没有闭合。runner 错边、冻结 case/API 能力不匹配、通用 remesh 算法缺陷三分分类以及修复方案优选均标记为
`not_adjudicated_due_to_first_failure`。不得用下面的 supporting evidence 越过首失败作正式分类。

v09 永久保持 `failed_r1_geometry_cache_force_finite_gate`；本任务没有重跑或改判 v09，没有生成新 R1 acceptance response，没有修改 fork，也没有进入 C1/F1。

## 2. 已通过的前置与 supporting evidence

独立无动力学初态上的真实 split `(0,1)` 在冻结容差内几何中性：新节点精确位于原边 midpoint，原 persistent vertex 坐标残差为 0，面积与体积跳变为 0，surface-centroid 归一化跳变为 `2.9134042681147884e-17`，axis 跳变为 `1.1950150693478818e-16`，active-energy 跳变为 `4.8235612945336187e-15`。

设原端点为 `x0,x1`，真实 split 点为

```text
m = (x0+x1)/2.
```

冻结 merge edge `(x0,m)` 的 production 实现新建端点 midpoint，因此

```text
q = (x0+m)/2 = (3/4)x0 + (1/4)x1.
```

机器结果为 `q=(0,-0.75,0)`，与解析值的归一化残差为 0；`q` 到 `x0` 的距离恰为原 edge 长度的 `0.25`。这证明 v09 的 frozen half-edge merge 不是 split 的几何逆。该无动力学 topology jump 的 centroid、area、volume 分别为
`0.083736358374574119`、`0.085080957923155662`、`0.125`；它与 v09 含动力学 step-3 的 `0.08373679738719757` 不是同一比较量，不得互相替代。

4 个候选的冻结观察为：

| candidate | edge | public eligible | production merge | topology legal | geometric inverse |
|---|---:|---:|---:|---:|---:|
| 1 | `(0,8)` | true | completed | true | false |
| 2 | `(1,8)` | true | completed | true | false |
| 3 | `(2,8)` | true | material rebind exception | not adjudicated | false |
| 4 | `(3,8)` | true | completed | true | false |

候选 3 揭示 `can_be_merged` 的拓扑可合并判据与带 production material sink 的端到端可执行性并不等价。由于同步 sink 抛错发生在真实 merge 调用中，本版本不继续检查该分支的 post-exception 原子性，也不把它升级为通用算法缺陷。

## 3. 只读源码 provenance

受控 fork 的本地 HEAD 与 tracking upstream 均为
`e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`，工作树干净。5 个直接相关源码的 `commit:path` 均为 Git blob，当前 `git hash-object` 与 source blob ID 一致；Windows checkout 中 4 个文本文件存在行尾字节表示差异，机器清单如实同时保存 `raw_worktree_bytes_equal=false` 与 `git_clean_filter_equivalent=true`，没有声称原始 checkout 字节与 LF blob 完全相等。

源码 supporting observation 为：public header 只有 `can_be_merged`、`split_edge` 与 `merge_edge` 的现有参数；merge 实现固定计算两端 midpoint，然后用两次 `cell::replace_node` 替换两个端点；`RemeshEvent` 不携带 survivor、split ancestor 或 collapse-position 控制。源码中未发现 endpoint-preserving collapse、显式 survivor、split-ancestor inverse 或几何约束/投影 public 选项。

这些事实支持“现有 API 是无 survivor 控制的 midpoint coarsening”这一观察，但由于候选 3 的 production sink 首失败，v10 不据此完成合同规定的唯一机制分类。

## 4. 修复选项与边界

- A：显式 survivor / endpoint-preserving collapse。需要扩展 event identity、材料 host 迁移、能量账本、旧 API 兼容性与 fork 回归面；本任务未实现，也未优选。
- B：split-ancestor inverse operation。需要持久化 ancestry、恢复 vertex/face identity、定义事件并发与多事件合法性；维护面更大；本任务未实现，也未优选。
- C：改 mesh、改 edge 或改阈值。这会改写冻结 case，不能修复或改判 v09；只能在未来新合同中定义不同 robustness case。
- D：merge 后手工恢复坐标。这绕过真实 production 算法并破坏 event/material/energy 原子语义，不可接受。

## 5. 证据与 claim guard

机器包位于 `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/`，包含四阶段逐顶点/face/edge/material CSV、event ancestry、四候选矩阵、解析—机器残差、首失败、criteria、源码 provenance、原始日志和真实验证日志。formal response 的非零退出是科学失败证据；普通 CTest 模式仅断言该精确失败状态仍被保留，因此不会人为增加第四个历史失败测试。

本结果只允许声称：冻结初态上的 split 几何中性、frozen half-edge 的 1/4 点解析闭合，以及候选 3 暴露的 topology eligibility / production material-transfer completion 不闭合。不得声称 v10 机制分类完成、repair 可用、R1 通过、长期稳定、生理有效、完整 cell–ECM/FSI 或 EFE/发育机制成立。
