---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V10-R1-MIDPOINT-DIAGNOSIS
status: frozen_before_v10_diagnostic_response
frozen_at: 2026-08-03
parent_commit_before_v10: 855bd8b7467761ba7fcdaa49632bed2ee5681e85
v09_contract_commit: f7701d59ce3e1c94737e3b0a276205ed70fae6f8
v09_result_commit: 10bb2c2602b499b5a75ba2d57a35ba717e156616
v09_sync_commit: 855bd8b7467761ba7fcdaa49632bed2ee5681e85
cell_engine_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
v09_status: failed_r1_geometry_cache_force_finite_gate
route_h_gate_a_v01: failed_invalid_numerics
x1_k_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v10 R1 midpoint-collapse failure mechanism / repairability audit 冻结合同

## 0. 授权、目的与永久边界

本任务只诊断 v09 step-3 midpoint-collapse 失败的机制、候选边行为和 public API 可修复性，不修复 fork，不修改或重跑 v09 acceptance，不产生新的 R1 acceptance response。v09 永久保持
`failed_r1_geometry_cache_force_finite_gate`；Route H Gate A v01 永久保持
`failed_invalid_numerics`；X1-K=false，C1/F1 与 downstream 均未授权。

合同先行提交并推送后，才允许产生 v10 topology microprobe 响应。v01–v09 的合同、结果、阈值、日志与失败语义不得覆盖、删除、禁用或改判。不得修改 `external/simucell3d/` 内容或 submodule pointer；不得触碰 `figures/` 与两个受保护脚本。

## 1. 可证伪假设与分类规则

按以下顺序检验，禁止只凭源码文字归因：

1. **H_runner_wrong_edge**：若 split 后存在一个 production-public、`can_be_merged=true` 的 split-node 邻边，真实 merge 可在不恢复坐标、不指定私有状态的情况下恢复 split 前几何、拓扑身份与 QoI 至冻结容差，则 v09 可能是 runner 选错边。反例：所有 eligible 候选均为 endpoint midpoint collapse，且无候选恢复被 split 的原始端点身份/坐标。
2. **H_case_api_mismatch**：若 public API 只有无 survivor 控制的 midpoint coarsening，所有 eligible 候选都合法但没有 split 的几何逆，则分类为“v09 冻结 case 要求几何近逆，而现有 API 只提供一般 midpoint coarsening”的能力不匹配。
3. **H_general_algorithm_defect**：仅当 machine 结果违背 source 定义、产生非有限/非流形/翻转拓扑，或 midpoint coarsening 本身不满足其公开不变量时，才分类为通用 remesh 算法缺陷。

若机器证据不能唯一支持上述一种分类，或出现首个反例，v10 冻结诊断失败并停止；不得调整候选集合、容差或分类定义。

## 2. 冻结 microprobe 初态与生产路径

使用 v09 的 8-vertex/12-face 单细胞、cell id 17、revision 0、两 material points 与 unit 501；activation=0.05、rate=0、stiffness=10、minimum axis/fiber alignment=0.9。所有 probe 均无动力学推进、无 passive/contact/pressure/ECM/flow、无 adaptive remesh、无 retry。

每个分支从字节等价但相互独立的初态 clone 构造，使用真实：

```text
fork cell
  -> production MyocardialMaterialTransferSink(maximum_rebind_distance=1e-12)
  -> public local_mesh_refiner(0.1,10.0,true,sink)
  -> split_edge / can_be_merged / merge_edge
  -> synchronous RemeshEvent
  -> public capture_surface_snapshot and material-state getters
```

不得构造 synthetic event、mock sink、私有 mesh mutation、坐标写回或伪造 lineage/ledger。

## 3. 最小主分支与逐阶段快照

主分支严格保存四个 stage：

1. `before_split`：原始 edge local `(0,1)`；revision 0；
2. `after_split`：真实 split `(0,1)`；revision 1；新节点记为 `m`；
3. `before_merge_frozen`：与 after_split 字节等价，冻结候选 `(0,m)`；
4. `after_merge_frozen`：真实 merge `(0,m)`；revision 2。

每个 stage 保存：全部 used vertex 的 local ID、persistent ID、坐标；全部 face 的 local connectivity 与 persistent connectivity；全部 edge 的 local/persistent endpoints、相邻 face IDs、manifold 标志；revision、V/E/F、Euler characteristic；独立 area、absolute closed volume、surface centroid、orientation、minimum triangle quality；material host/rebind；axis length、registered active energy；同步 event operation/revisions 与显式 action ancestry。

split 几何中性门禁预冻结为：原 persistent vertices 坐标不变，新节点坐标满足原 edge midpoint；area、volume、centroid、axis 与 active energy 的相对/归一化跳变均 `<=1e-12`；orientation>0、minimum q>=0.05、Euler characteristic=2、全部 edge manifold。任一失败即冻结 v10 诊断失败。

## 4. midpoint 解析式与 machine residual

设 split 前原 edge 端点为 `x0`、`x1`，真实 split 新点

```text
m = (x0+x1)/2.
```

若真实 merge 选择 `(x0,m)` 且 production 实现删除两个端点、在端点 midpoint 新建点 `q0m`，则

```text
q0m = (x0+m)/2 = 3/4 x0 + 1/4 x1.
```

因此它距离原 `x0` 为原 edge 的 `1/4`，不是恢复 `x0`。另一半边同理：

```text
qm1 = (m+x1)/2 = 1/4 x0 + 3/4 x1.
```

机器必须由 persistent/local topology 确认被删除端点和新增 persistent ID，并验证
`||q_machine-q_analytic||/L0 <=1e-12`，其中 `L0=V0^(1/3)`。同时保存 merge 瞬时跳变：

```text
e_centroid = ||c_after-c_before||/L0
e_area     = |A_after-A_before|/A0
e_volume   = |V_after-V_before|/V0
e_axis     = |Laxis_after-Laxis_before|/Laxis0
e_energy   = |Psi_after-Psi_before|/Psi0
```

不得用 post-merge 动力学掩盖 topology jump。

## 5. 全候选边枚举

在标准 split 后，按 local endpoint pair 升序枚举 **所有** 与 split node `m` 相邻的 edge。每个候选在独立 clone 上重新执行同一 split；先保存 `can_be_merged`。对所有 `true` 候选执行真实 merge；对 `false` 候选只保存拒绝事实，不调用 merge。

每个候选保存：candidate ID、local/persistent endpoints、是否为原 edge 两个 half-edge 之一、`can_be_merged`、解析 collapse midpoint、machine collapse point与 residual、被删除/新增 persistent IDs、revision/event、V/E/F/Euler/manifold、orientation/min q、centroid/area/volume/axis/energy 瞬时跳变、与 split 前几何的恢复误差。

“几何逆”预冻结为同时满足：原 persistent vertex 集与坐标恢复、原 persistent face connectivity 恢复、area/volume/centroid/axis/energy 恢复误差均 `<=1e-12`。只恢复全局 QoI而丢失原 topology identity 也不得称为 inverse。禁止选择最小误差候选替换 v09。

## 6. 源码 provenance 与 public API 能力审计

只读审计以下受控 fork 对象，并保存 `commit:path`、Git object type、blob ID、SHA-256、行范围与关键声明/实现摘要：

- `include/triangulation_modules/local_mesh_refiner.hpp`；
- `src/triangulation_modules/local_mesh_refiner.cpp`；
- 与 node identity / replace-node / event emission 直接相关且由上述实现引用的最小文件。

必须以 `git cat-file -e/-t/-p` 或等价 Git-object 命令证明对象来自
`e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`，并验证工作树文件字节与该 blob 一致。明确搜索并裁决 public API 是否已有：

- endpoint-preserving collapse；
- explicit survivor selection；
- split-ancestor inverse operation；
- collapse-position constraint/projection。

缺失能力必须由 public header 与实现的对象证据支持，不得仅凭命名或报告文字推断。

## 7. 修复选项只读比较

只提出、不实施：

- **A：explicit survivor / endpoint-preserving collapse**。评估 event 需携带 survivor/deleted identity、材料 host 重绑、能量跳变、旧 API 兼容、fork 维护面及 property/regression tests。
- **B：split-ancestor inverse operation**。评估 ancestry 持久化、只允许合法紧邻 inverse、原 vertex/face identity 恢复、事件语义与多事件/并发维护成本。
- **C：改网格、改 edge 或改阈值**。明确属于改写冻结 case，不能修复或改判 v09；只可在未来新合同中定义不同 robustness case。
- **D：merge 后手工恢复坐标**。明确属于绕过真实 production 算法且污染 event/material/energy 原子语义，不可接受。

不得在本任务修改 fork、实现 prototype 或提交 repair。

## 8. 诊断门禁、状态与交付

通过条件：split 中性、frozen half-edge analytic/machine 闭合、所有 eligible 候选完整枚举、source provenance 闭合、分类唯一且修复矩阵完整。唯一允许通过状态：

```text
passed_midpoint_collapse_failure_mechanism_and_repairability_diagnosis
```

这不是 R1/X1-K pass。任一验证、证据或分类门禁失败，状态为
`failed_v10_midpoint_collapse_diagnosis_<first_reason>`，冻结首反例并停止。

版本化交付到 `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/`：stage vertices/faces/edges、events/ancestry、candidate matrix、geometry/QoI jumps、analytic residual、source provenance、criteria、summary、配置、复算命令；另交付中文报告。保存 focused/full parent、fork、strict、Python、Ruff 的真实日志、exitcode、SHA-256 与 parser 输出，不硬编码测试计数。

合同、结果、同步必须为三个阶段提交并分别推送。完成后停止并返回导师；不得自行实施 repair 或进入 C1/F1。
