---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V09-R1
status: frozen_before_r1_response
frozen_at: 2026-08-03
parent_commit_before_r1: 3d0a8217e869213e34223d7206f4588e7b6e9aca
accepted_v08r1_contract: a500893e86c2d5415a48a8458a8a0c2f7eb721ce
accepted_v08r1_result: d457d558757c8b107e92ed43b24985cecbc99fad
accepted_v08r1_sync: 3d0a8217e869213e34223d7206f4588e7b6e9aca
cell_engine_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v09 R1 remesh-on robustness 冻结合同

## 0. 授权、历史与边界

导师接受 v08r1，状态仅为
`passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair`。v08 保持
`failed_adjudicator_contract_incomplete`；Route H Gate A v01 保持
`failed_invalid_numerics`；v02、v04、v06 历史科学失败不改写。X1-K 仍为 false。

本任务只执行 R1，不启动 C1/F1，不进入 ECM/flow、参数标定或机制 claim。不得修改受控 fork、
remesh 算法/判据、已有物理阈值或 v01–v08r1 冻结证据，不产生 adaptive remesh 或 retry。

v08r1 后续表述冻结为：v05 由 `E_total`、`A_v5+A_v6`、`|v_exact|` 重建 global L2，
并与 levels 的 `normal_velocity_relative_l2` 交叉核对；这是“由 levels global L2 与 exact
velocity 隐含的面积闭合”，不得声称 levels CSV 存在独立 surface-area/dual-area 字段。

## 1. Capability 与执行顺序

只读代码检查确认现有 public seam 包括：

- fork `cell` 与 `local_mesh_refiner::split_edge/merge_edge`；
- 同步 `RemeshEvent` 与 public `capture_surface_snapshot`；
- 生产 `MyocardialMaterialTransferSink`、材料状态/transfer audit/remesh-energy ledger getters；
- PRL-owned `advance_owned_active_cell_overdamped_one_step`，可显式使用
  `barycentric_dual_area` damping。

允许在 PRL-owned `short_trajectory`/audit/test/export 层增加最小 R1 runner；不得增加 fork API
或私有测试注入。若 RED 证明上述 public seam 不能完成真实路径，冻结
`failed_r1_public_capability_blocker` 并停止。

严格执行：本合同单独提交并推送 → TDD RED → 最小 GREEN → fixed run → remesh-on run →
首硬门禁裁决 → 版本化结果与真实验证 → 提交、推送、审计 → 停止。合同提交前不得运行
任何 R1 response。

## 2. 冻结单细胞主动 baseline

两条 run 从两个独立但字节等价的同一初态构建：

- 闭合表面：8 vertices / 12 triangles，使用 v01 T1 的冻结心肌测试网格；
- cell id=`17`；初始 mesh revision=`0`；
- passive/contact owners 置零，但必须走 owned step 的真实 passive assembly、active assembly、
  atomic position/cache commit 与 force cleanup；无 contact、pressure、ECM、flow；
- material point `101`：apical，fiber=`(1,0,0)`，activation=`0.05`，rate=`0`；
- material point `205`：basal，fiber=`(1,0,0)`，无 active state；
- host、barycentric coordinates 与 reference weights 沿用 v01 T1 fixture；
- contraction unit id=`501`，controller=`101`，target=`205`，activation owner=`101`，
  active stiffness=`10`，minimum axis/fiber alignment=`0.9`；
- damping=`barycentric_dual_area`，`zeta_A=10`；
- `dt=6.25e-4`，`T=5.0e-3`，严格 8 steps，sample=`0..8`；
- activation 全程冻结，不 adaptive，不 retry，不改步数。

fixed run 全程 revision 0，不创建 remesher。remesh-on run 使用生产 sink，
`maximum_rebind_distance=1e-12`，并构造真实 `local_mesh_refiner(0.1,10.0,true,sink)`；只直接
调用预注册的两次拓扑操作，不调用 adaptive refine/coarsen 驱动。

## 3. 冻结事件顺序

为使 J1 仍是纯 topology cycle、避免把真实动力学能量变化误记为 remesh 缺陷，顺序固定为：

1. step 1：owned motion → sample 1；
2. step 2：owned motion → 在 edge local `(0,1)` 执行真实 split → sample 2；
3. step 3：在任何 motion 前，对新节点与 local vertex 0 的对应 edge 执行真实 merge →
   owned motion → sample 3；
4. steps 4–8：owned motion → sample。

remesh ledger 在 step 2 motion 完成后、split 紧前，以当前 mesh/material 和同一 contraction
unit 开始。因此 split 与 merge 之间没有动力学步，`inter_event_stored_energy_change` 是真正的
事件间审计，不含物理时间演化。不得为了结果改变事件相位、edge、次数或顺序。

预期同步事件严格为：

```text
event 1: edge_split, revision 0 -> 1, at step 2
event 2: edge_merge, revision 1 -> 2, at step 3
split=1, swap=0, merge=1
```

## 4. QoI 定义与 R1 比较门禁

只比较以下四个客观 QoI；不比较节点位置：

- `L_axis(k)`：public active evaluation 中 unit 501 两 material anchors 的当前距离；
- `A_ratio(k)=A(k)/A(0)`：独立三角几何面积比；
- `V_ratio(k)=V(k)/V(0)`：独立闭合表面几何体积比，不称为 volume error；
- `Psi_active(k)`：registered `active_contraction_only` 总储能。

初态相同并冻结归一化：

```text
e_L(k)   = |L_remesh(k)-L_fixed(k)| / L_axis(0)
e_A(k)   = |A_ratio_remesh(k)-A_ratio_fixed(k)|
e_V(k)   = |V_ratio_remesh(k)-V_ratio_fixed(k)|
e_Psi(k) = |Psi_remesh(k)-Psi_fixed(k)| / Psi_active(0)
```

对 `k=0..8` 全部保存，四项分别取 `max_k`；每个最大值必须 `<=2.0e-3`。不得以仅比较终点
替代逐步最大差，也不得新增未映射节点误差。

## 5. J1 remesh-cycle 门禁

ledger coverage 只能为 `active_contraction_only`。由真实同步事件生成，不得伪造或在 runner
中手填：

```text
initial_stored_energy > 1.0e-2
abs(final_stored_energy-initial_stored_energy) <= 1.0e-12
sum(abs(epsilon_alg))
  = cumulative_absolute_algorithmic_energy_defect <= 1.0e-12
minimum step/initial fiber alignment >= 1-1.0e-12
maximum_rebind_error <= 1.0e-12
event_count=2; split=1; swap=0; merge=1
abs(cumulative_declared_remesh_work) <= 1.0e-12
energy_telescoping_residual <= 1.0e-12
```

同时保存并独立门禁：

```text
signed cumulative inter-event stored-energy change
sum(abs(inter-event stored-energy change)) <= 1.0e-12
max(abs(inter-event stored-energy change)) <= 1.0e-12
```

有符号累计只作望远镜闭合项，不能用于“无抵消”结论；该结论必须由 `sum_abs` 与 `max_abs`
支持。每个 event 保存 event ID、operation、before/after revision、stored energy before/after、
inter-event change、`DeltaPsi_remesh`、declared work、`epsilon_alg`、fiber alignment 和 rebind。

## 6. 逐步安全与能量控制

fixed/remesh 每步保存：step/time、topology counts、revision、状态 hash、四个 QoI、面积/体积/
表面质心、orientation、三角质量
`q=4sqrt(3)A/(l1^2+l2^2+l3^2)`、minimum-face/current-run-initial-minimum、独立几何-vs-cache
残差、force-buffer norm、active control work、viscous dissipation 和
`DeltaPsi_active+D_zeta-W_control`。

两条 run 均须满足：

```text
所有保存值有限
minimum oriented alignment > 0
minimum triangle quality >= 0.05
minimum face-area ratio >= 1e-4
maximum normalized cache residual <= 1e-12
surface-centroid drift/L0 <= 1e-2, L0=V0^(1/3)
volume ratio in [0.5,1.5]
force-buffer L2 norm after every owned step <= 1e-12
sum(max(0,DeltaPsi_active+D_zeta-W_control))/Psi_active(0) <= 5e-3
```

registered energy owners：`Psi_active`、`D_zeta`、`W_control`；remesh topology ledger 另注册
`DeltaPsi_remesh` 与零 declared remesh work。excluded：passive energy（本 case 参数为零且未注册）、
contact、pressure、ECM、flow、legacy surface cache。不得宣称 full total-energy inequality。

## 7. TDD、原始证据与验证

第一个公共行为测试调用拟新增的 public R1 runner；在实现前必须因 seam 缺失而 RED。最小
GREEN 必须实际构造 fork cell/refiner、production sink、同步 event、owned step，不能用 synthetic
event、mock sink、私有注入或伪造 ledger。之后再增加 fail-closed evaluator/导出测试。

版本化保存：

- `config.json` 与初始 geometry/material/state hash；
- fixed/remesh `steps.csv`；
- `events.csv`、`material_transfer.csv`、`remesh_energy_ledger.csv`；
- `qoi_comparison.csv`、`criteria.csv`、`summary.json`；
- TDD RED/GREEN、复算命令；
- focused/full parent、fork、strict、Python、Ruff 的原始 `.log` 与 `.exitcode`。

验证 parser 必须从真实日志解析 exit code、完成计数与失败集合，不得硬编码 summary 数字。
完整 parent 回归必须继续保留且仅保留 v02、v04、v06 三个历史失败；fork 必须全绿。

## 8. 状态、停止规则与保护内容

首个硬门禁失败即冻结全部已产生 raw evidence，状态按首失败为：

```text
failed_r1_public_capability_blocker
failed_r1_setup
failed_r1_fixed_trajectory
failed_r1_remesh_trajectory
failed_r1_qoi_difference
failed_r1_j1_gate
failed_r1_geometry_cache_force_finite_gate
failed_r1_verification_evidence
```

通过时唯一允许状态为 `passed_r1_remesh_on_robustness_frozen_case`。无论通过或失败：

```text
x1_k_passed=false
C1/F1=not_executed
downstream_authorized=false
```

不得触碰：

- v01–v08r1 冻结证据与 Route H 包；
- `external/simucell3d/` 内容或 submodule 指针；
- `figures/`；
- `scripts/build_efe_nature_figure_plan_docx.py`；
- `scripts/insert_efe_figure_mockups_docx.py`。

完成合同提交、结果提交、真实远端同步和哈希审计后停止，返回导师；不得自行进入 C1/F1。
