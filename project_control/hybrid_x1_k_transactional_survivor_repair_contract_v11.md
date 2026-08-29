---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V11-TRANSACTIONAL-SURVIVOR-REPAIR
status: approved
planner: codex_primary_single_agent
requested_by: human_final_reviewer
drafted_at: 2026-08-13
lifecycle_state: executed_awaiting_human_acceptance
execution_authorized: true
execution_result: passed_x1_k_v11_transactional_survivor_r1r_c1_f1
execution_report: project_control/hybrid_x1_k_transactional_survivor_repair_execution_report_v11.md
approved_by: human_final_reviewer
approved_at: 2026-08-14
git_remote_actions_authorized: false
upstream:
  - project_control/efe_node1_n1r_acceptance_decision_v01.md
  - project_control/hybrid_x1_k_r1_remesh_robustness_failure_report_v09.md
  - project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
  - project_control/hybrid_x1_k_v08_rejection_and_v08r1_repair_report.md
governed_by:
  - project_control/external_scientific_review_constraints_v01.md
protected_history:
  - results/hybrid/x1_k_r1_remesh_robustness_v09/
  - results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/
  - results/hybrid/x1_k_revised_fixed_topology_v08r1/
approval_decision: project_control/hybrid_x1_k_v11_approval_decision.md
---

# X1-K v11：事务化 remesh 与端点保留 collapse 修复合同（草案）

## 1. Goal

修复阻断 EFE Node 1 的两个独立数值合同缺口，并完成新的 X1-K 资格裁决：

1. **事务原子性缺口**：当前 `merge_edge` 先改变 cell 网格并增加 revision，再同步调用材料迁移 sink；若材料点回绑失败，sink 状态保持旧 revision，但 cell 可能已经变更。v10 没有裁决异常后的整体状态原子性。
2. **操作语义缺口**：当前 public `merge_edge` 是把两个端点替换为中点的一般 coarsening，不是 split 的几何逆；v09 却把它用于要求 split→merge 近逆的 R1 case。

v11 选择以下修复路线：

- 把“拓扑上可合并”和“带材料状态可提交”分成两个显式判据；
- 为受观察的 remesh 建立 `prepare → commit/reject` 语义，使任何 pre-commit 拒绝不改变 cell、revision、cache、force buffer 或材料状态；
- 新增**端点保留 collapse**，由调用者明确选择 survivor persistent vertex；旧 midpoint merge 保留且不改义；
- 用端点保留 collapse 构造新的 R1r split→collapse 周期；
- R1r 通过后才按顺序执行 C1 和扩展 F1；
- 只有 v08r1 的 revised D1/S1 证据仍完整，且 R1r/C1/F1 全部通过，才允许将新的 v11 总状态记为 `x1_k_passed=true`。

本合同不重判 v09/v10。其目标不是让旧失败“变成通过”，而是建立一个语义正确的新修复版本。

## 2. Inputs

### 2.1 冻结失败事实

- v09：`failed_r1_geometry_cache_force_finite_gate`；step 3 midpoint merge 的归一化表面质心漂移为 `0.08373679738719757 > 0.01`；
- v10：`failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind`；candidate 3 `(2,8)` 的材料点 101 回绑距离为 `0.047434164902525666 > 1e-12`；
- v10 supporting evidence：split `(0,1)` 几何中性；half-edge midpoint collapse 落在原边四分之一位置；已完成的候选均不是几何逆；
- 受控 fork 基线 commit：`e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`；
- v08r1：仅 revised fixed-topology D1/S1 通过；R1/C1/F1 未执行；
- Route H Gate A v01 继续为 `failed_invalid_numerics`，不得由本合同改判。

### 2.2 当前源码事实

- `local_mesh_refiner::can_be_merged` 只检查拓扑邻接合法性；
- `local_mesh_refiner::merge_edge` 固定使用端点中点并替换两个端点；
- `emit_remesh_event` 在回调前增加 mesh revision；
- `MyocardialMaterialTransferSink::on_remesh` 先在临时副本上计算材料转移，成功后才更新 sink；因此 sink 内部原子，但不等于 cell+sink 整体原子；
- `cell` 有 copy constructor，可作为 preview/rollback 实现候选，但合同只冻结可观察行为，不强制某一种内部事务技术。

### 2.3 允许复用

- v09 的固定单细胞、主动材料、时间步、QoI、几何门、J1 能量账本和版本化输出定义；
- v10 的逐顶点/face/edge/material 审计方法和解析四分之一位置检查；
- v08r1 的 D1/S1 fail-closed adjudicator 与 provenance；
- 当前 parent C++ 材料迁移、owned step、短轨迹、接触和失败状态接口。

## 3. Scientific and software decisions

### 3.1 为什么选端点保留 collapse，而不是 split-ancestor 专用撤销

选择 v10 的 option A：显式 survivor / endpoint-preserving collapse。

理由：

- 它能表达 split half-edge 的几何逆，同时也可用于一般需要保留边界/材料锚点的 coarsening；
- 不要求保存任意长的 split ancestry 或实现只对紧邻 split 有效的专用 undo 状态机；
- survivor identity、位置和材料 host 的语义可以在事件中直接审计；
- 与旧 midpoint merge 可并存，避免静默改变 SimuCell3D 原算法。

这项选择只表示当前工程修复路线，不表示 endpoint-preserving collapse 在所有组织 remeshing 中更物理。一般 coarsening 是否应选中点、端点或误差最小位置属于后续自适应策略问题。

### 3.2 两类可合并判据必须分开

正式 API/审计中必须分栏：

1. `topology_eligible`：只回答 manifold/connectivity 是否允许 collapse；
2. `transfer_acceptable`：在给定 survivor/placement 和 `maximum_rebind_distance` 下，所有材料点是否可转移；
3. `operation_committed`：只有前两项均通过且事务提交成功时为真。

原 `can_be_merged` 可保留以兼容旧调用，但文档和新 runner 只能把它称为 topological eligibility，不得再解释为 production commit guarantee。

### 3.3 事务可观察语义

受材料 sink 观察的每个 remesh 必须具有下列状态机：

```text
proposed
  -> prepared
      -> committed
      -> rejected_before_commit
  -> rejected_before_prepare
```

必须满足：

- `prepare` 可以失败，但不得改变生产 cell 或已提交的材料状态；
- `commit` 只能使用与 prepare 相同的 before/after/event，不得重新选择 host；
- `rejected_*` 时 mesh revision 不增加；
- `committed` 时 cell revision 与 material revision 同时从 `r` 变为 `r+1`；
- 不允许出现“cell 已是 `r+1`、material 仍是 `r`”的可观察状态；
- 多 cell 并发仍按 cell 独立加锁，不建立全局串行锁；
- 若实现采用 preview copy、回滚或 staged topology，最终行为必须通过同一原子性门，不得只靠文档声明。

若无法在现有 fork seam 内实现上述语义，v11 必须冻结为 capability blocker，不得退化为放宽 rebind tolerance。

## 4. Proposed public behavior

### 4.1 端点保留 collapse

新增 public 行为应等价于：

```text
collapse_edge_to_survivor(edge, survivor_persistent_id, cell, edge_workset)
```

具体 C++ 命名可按项目风格调整，但必须满足：

- survivor 必须是目标 edge 的一个端点；
- survivor persistent ID 与坐标保持不变；
- 另一端点及 collapse 后退化的两张面被删除；
- 不创建新的 persistent vertex；
- 更新后的拓扑通过 Euler、manifold、orientation 和质量门；
- event 明确记录 `collapse_mode=endpoint_survivor`、survivor、deleted endpoint 和 placement；
- 旧 `merge_edge` 的 midpoint 行为、签名和回归继续保留。

立即 split `(0,1)` 后，对 half-edge `(0,m)` 选择原 vertex 0 为 survivor，必须恢复 split 前：

- persistent vertex 集及坐标；
- persistent-connectivity face 集；
- area、volume、surface centroid、axis length 和 active energy；
- 材料点 ID、region、active state、reference weight 和 fiber direction。

所有恢复误差门为 `<=1e-12`，orientation `>0`，minimum triangle quality `>=0.05`。

### 4.2 remesh 事件信息

事件必须能区分：

- `edge_split`；
- `edge_merge_midpoint` 或旧 `edge_merge + collapse_mode=midpoint`；
- `edge_collapse_survivor` 或 `edge_merge + collapse_mode=endpoint_survivor`。

事件至少暴露：before/after revision、operation、collapse mode、survivor persistent ID（若存在）、deleted persistent IDs 和 created persistent ID（若存在）。

不得通过解析 before/after 坐标猜 survivor；事件身份是材料迁移、能量账本和失败审计的一部分。

### 4.3 兼容性

- 无 sink 的旧 remesh 路径继续运行；
- 只有 legacy observer seam 的调用方保持源代码可编译，或提供显式迁移层；
- 旧 midpoint merge 的数值行为保持 v10 解析位置；
- parent `MyocardialMaterialTransferSink` 使用新事务 seam，但其成功转移的材料语义不改变；
- 不修改现有物理力、阻尼、接触、主动能或 ECM 模型。

## 5. Implementation Steps

### V11-A：基线与 TDD RED

1. 保存 v09/v10 直接输入和相关源码的 stage-entry hash；
2. 使用 v10 candidate 3 构造真实 production 路径行为测试；
3. 预注册期望：材料拒绝后 cell snapshot、revision、cache、force buffer、edge workset、material state、ledger 全部不变；
4. 在修复前该测试必须 RED，不得把异常改成预期成功；
5. 为 split half-edge 的 survivor collapse 写第二个 RED：现有 public seam 缺少该行为。

若实际基线与 v10 报告不一致，状态冻结为 `failed_v11_baseline_drift`，停止实施。

### V11-B：最小事务修复

1. 在受控 fork 与 parent sink 之间实现 prepare/commit/reject；
2. 使材料可接受性在生产 cell mutation 前完成；
3. 为拒绝路径加入整状态 hash 与 revision 守恒测试；
4. 为成功路径加入 cell/material revision 同步、事件唯一性和 ledger 单次提交测试；
5. 加入两个 cell 并发测试，证明 per-cell transaction 不交叉污染；
6. 不实现 adaptive retry，不改变 `maximum_rebind_distance=1e-12`。

### V11-C：端点保留 collapse

1. 新增 survivor collapse public seam 和事件身份；
2. 实现 half-edge split→survivor-collapse 精确恢复；
3. 证明旧 midpoint merge 仍落在解析中点/四分之一位置；
4. 材料 sink 在 survivor cycle 中保持 ID、region、active state、reference weight、fiber tangent 和 energy ledger；
5. 加入非法 survivor、非 manifold、退化/翻转候选的 pre-commit 拒绝测试。

### V11-D：R1r 新修复版本

沿用 v09 冻结初态、材料、`dt=6.25e-4`、`T=5e-3`、8 steps 和 owned motion。两条独立 run：

- fixed：全程 revision 0；
- remesh：step 2 motion 后 split `(0,1)`；step 3 motion 前 collapse `(0,m)`，明确 survivor persistent ID `0`；其后继续到 step 8。

另运行 candidate 3 transaction probe：

- `topology_eligible=true`；
- `transfer_acceptable=false`；
- `operation_committed=false`；
- status=`rejected_material_rebind_before_commit`；
- rebind distance 仍报告为 `0.047434164902525666` 的冻结复现值，容差只允许机器舍入级差异；
- cell/material/ledger/force/cache/state hash 均与 proposal 前相同。

R1r 必须先通过 transaction probe，再裁决 trajectory。

### V11-E：C1

只有 R1r 通过才执行。完整沿用 X1-K v01 的独立短接触 case：

- 平面盒体顶面 `z=-0.995`，细胞初始 `z_min=-1.0`；
- active/passive 为零，接触为外功端口；
- `dt=1e-4`、`T=1e-3`；
- penetration `<=1e-2`；
- 作用反作用净力与净矩残差各 `<=1e-10`；
- 声明 coverage 残差 `DeltaPsi_active + D_zeta - W_contact <=1e-10`；
- 不宣称未注册接触势能的总势能不等式。

### V11-F：扩展 F1

只有 C1 通过才执行两条失败持久化：

1. 原 F1：`dt=max_double` 触发首步 `failed_non_finite_state`，step 1、time 0、配置和状态 hash 存在且失败前后相同；
2. 新 F1R：candidate 3 材料回绑拒绝必须在 commit 前发生，完整 cell/material 状态不变，且后续一次合法 survivor cycle 仍可成功，证明拒绝没有污染内部事务缓存。

任何失败均停止，不进入总体裁决。

### V11-G：总体裁决

1. 重新验证 v08r1 所需冻结 D1/S1 evidence 的路径、hash、schema 和来源对象；不重跑旧科学轨迹；
2. 汇总 R1r/C1/F1 原始数据和验证日志；
3. 只有全部门禁通过时输出 v11 X1-K pass；
4. 返回人类终审，不自动启动 EFE Node 1 N1-1。

## 6. R1r acceptance criteria

### 6.1 split→survivor-collapse 事件门

```text
event_count = 2
split = 1
endpoint_survivor_collapse = 1
midpoint_merge = 0
revision = 0 -> 1 -> 2
survivor persistent ID = 0
deleted split-node persistent ID = m
created persistent vertex on collapse = none
```

collapse 后与 split 前比较：persistent vertices/coordinates、face connectivity、area、volume、centroid、axis 和 active energy 误差均 `<=1e-12`。

### 6.2 材料和能量门

沿用并明确扩展 v09 J1：

```text
initial active stored energy > 1e-2
abs(final-initial active energy) <= 1e-12
sum(abs(epsilon_alg)) <= 1e-12
sum(abs(inter_event stored-energy change)) <= 1e-12
max(abs(inter_event stored-energy change)) <= 1e-12
minimum initial/step fiber alignment >= 1-1e-12
maximum rebind error <= 1e-12
abs(cumulative declared remesh work) <= 1e-12
energy telescoping residual <= 1e-12
material ID/state/region/reference-weight retention = exact
```

coverage 仍仅为 `active_contraction_only`。

### 6.3 fixed-vs-remesh QoI 门

对 sample `0..8`：

```text
max e_axis   <= 2e-3
max e_area   <= 2e-3
max e_volume <= 2e-3
max e_energy <= 2e-3
```

定义与 v09 相同；不比较节点位置。

### 6.4 逐步安全门

- 全部值 finite；
- minimum oriented alignment `>0`；
- minimum triangle quality `>=0.05`；
- minimum face-area ratio `>=1e-4`；
- normalized geometry/cache residual `<=1e-12`；
- surface-centroid drift `/L0 <=1e-2`；
- volume ratio in `[0.5,1.5]`；
- force-buffer norm after each owned step `<=1e-12`；
- active-only 累计正能量残差 `/Psi0 <=5e-3`。

## 7. Transaction acceptance criteria

### 7.1 拒绝原子性

对 candidate 3，在真实 public path 上拒绝前后必须逐项相同：

- used vertex persistent IDs、坐标和 slot 使用状态；
- face connectivity、edge set、Euler characteristic；
- mesh revision、next persistent ID source；
- area/volume/centroid/geometry cache；
- node force、previous force/position、momentum（按编译 dynamics mode）；
- material point host/barycentric/state/fiber/reference weight；
- material revision、last committed audit 和 remesh-energy ledger；
- edge workset；
- state hash。

所有浮点状态要求 bitwise equal；只对明确不进入状态的诊断字符串允许不同。不得以“几何看起来一样”替代完整原子性。

### 7.2 成功提交原子性

- 一个 proposal 只能 commit 一次；
- cell/material revision 一致；
- event 与 audit 计数恰增 1；
- prepare 的 after snapshot hash 等于 committed after snapshot hash；
- 重复/过期 token、before revision drift 和跨 cell token 必须在 mutation 前拒绝；
- commit 后不得存在可观察的中间 revision mismatch。

### 7.3 异常安全

若无法保证 commit 阶段 no-fail，必须提供并验证精确 rollback。任何 callback 异常后 cell/material 不一致均为硬失败 `failed_v11_transaction_atomicity`。

## 8. Outputs

### 8.1 代码和测试

- 受控 fork：transactional remesh seam、survivor collapse、事件 identity 和 focused tests；
- parent C++：transactional material transfer、R1r runner、C1/F1 reuse/adjudication 和 tests；
- Python：仅负责从原始输出 fail-closed 复算和导出，不生成物理结果。

### 8.2 版本化证据

新增：

`results/hybrid/x1_k_transactional_survivor_repair_v11/`

至少包含：

- `config.json`、stage-entry source provenance；
- RED/GREEN 原始日志；
- transaction proposal/prepare/commit/reject audit；
- candidate 3 pre/post 全状态清单与 hash；
- survivor cycle stage vertices/faces/edges/material；
- fixed/remesh steps、events、QoI、energy ledger；
- C1/F1 原始时序和失败包；
- `criteria.csv`、`decision_matrix.csv`、`summary.json`；
- focused/full/strict/Python/Ruff 的真实日志与 exitcode；
- 中文执行报告。

旧 v08r1/v09/v10 结果目录不得覆盖或修改。

## 9. Impacted Files Or Modules

合同批准后允许触及的范围：

- `external/simucell3d/include/prl_cell_engine/remesh_contract.hpp`；
- `external/simucell3d/include/triangulation_modules/local_mesh_refiner.hpp`；
- `external/simucell3d/src/triangulation_modules/local_mesh_refiner.cpp`；
- 如事务提交确有必要，`external/simucell3d/include/mesh/cell.hpp`、`external/simucell3d/src/mesh/cell.cpp` 的最小 surface-state seam；
- `cpp/include/prl/core/myocardial_material_transfer.hpp`；
- `cpp/src/myocardial_material_transfer.cpp`；
- `cpp/include/prl/cell_engine/`、`cpp/src/` 中新的 v11 R1r/C1/F1 runner/adjudicator；
- 对应 `cpp/tests/`、`tests/`、`scripts/`、`project_control/`、`docs/` 和新 v11 results。

禁止触及：

- v01–v10 的合同、报告和结果原始字节；
- Route H 冻结失败包；
- `figures/` 和论文图；
- EFE Node 1 三层求解器、ECM 材料或参数；
- 项目文件夹外的任何文件或文件夹；
- Git remote、push、pull、发布或 PR。

若实际修复需要超出上述源码范围，停止并提交 deviation，不得自行扩张。

## 10. Test Plan

### 10.1 Public behavior tests

1. material-aware reject leaves complete state unchanged；
2. legal transaction commits exactly once；
3. stale/cross-cell/reused preparation is rejected before mutation；
4. two cells can transact concurrently without audit/state cross-talk；
5. illegal survivor is rejected；
6. split→survivor-collapse recovers geometry/topology/material；
7. legacy midpoint merge result and API compatibility remain unchanged；
8. adaptive/refine path cannot bypass material-aware precommit when a transactional sink is present。

### 10.2 Scientific/numerical tests

- R1r 所有预注册 QoI、J1、几何、cache、force 和 energy 门；
- C1 接触 penetration、作用反作用和外功 coverage；
- F1 非有限状态持久化与 F1R remesh rejection 原子性；
- v08r1 D1/S1 evidence 完整性复核；
- fork 完整测试无新增失败；
- parent 完整测试只允许历史冻结失败集合，v09/v10 精确失败回归必须继续通过；
- strict warnings-as-errors、Python tests 和 Ruff 通过。

验证计数必须从实际日志解析，不在合同中硬编码总数。

### 10.3 Fail-closed order

按 `baseline → transaction → survivor collapse → R1r → C1 → F1 → evidence/verification` 顺序裁决。首个硬失败立即冻结；后续阶段标记 `not_executed_due_to_first_failure`。

## 11. Status vocabulary

允许的首失败状态：

```text
failed_v11_baseline_drift
failed_v11_transaction_public_capability
failed_v11_transaction_atomicity
failed_v11_survivor_collapse_geometry_or_identity
failed_v11_material_transfer_or_energy
failed_v11_r1r_qoi
failed_v11_r1r_geometry_cache_force_finite
failed_v11_c1_contact
failed_v11_f1_persistence
failed_v11_evidence_integrity
failed_v11_verification
```

全部通过时唯一允许状态：

```text
passed_x1_k_v11_transactional_survivor_r1r_c1_f1
```

只有该状态才可同时写：

```text
x1_k_passed = true
revised_d1_s1 = passed_from_v08r1_reverified
r1r = passed
c1 = passed
f1 = passed
node1_n1_1_execution = pending_human_authorization
```

不得自动写 `downstream_authorized=true`；X1-K 通过后仍必须返回人类终审，再决定是否启动 EFE Node 1 N1-1。

## 12. Risks

1. **事务 seam 侵入 fork 核心**：以可观察原子性为门，限定最小 surface-state seam，并完整运行 fork 回归；
2. **preview 与 commit 不一致**：要求 before/after hash 相同、token 单次使用和 revision 锁；
3. **endpoint collapse 只为测试特制**：保留 legacy midpoint，对非法 survivor 和一般边加入属性测试；R1r 只声称预注册 cycle；
4. **材料 rejection 被阈值掩盖**：保持 `1e-12`，禁止调到 `0.05` 让 candidate 3 强行通过；
5. **事件 identity 破坏兼容性**：旧调用路径和结果必须回归；新增字段需要安全默认值或迁移层；
6. **修复 R1 后 C1/F1 仍失败**：接受首失败并停止，不把局部 repair 写成 X1-K 总通过；
7. **dirty worktree 干扰**：执行时仅修改本合同允许的文件，保留并排除用户既有改动；不得使用重置或清理命令；
8. **工程延迟科学主线**：本合同只修复解除 Node 1 硬门所必需的原子性、R1r、C1、F1，不开发通用 remesh 优化器。

## 13. Acceptance Criteria

v11 交付被提交人类终审前必须满足：

- v09/v10 冻结失败证据未改动；
- candidate 3 在材料容差不变时成为 pre-commit rejection，完整状态原子不变；
- split→survivor-collapse 恢复预注册几何、拓扑身份和材料状态；
- legacy midpoint merge 行为未静默改变；
- R1r fixed/remesh QoI、J1 和安全门全部通过；
- C1 与双 F1 全部通过；
- v08r1 D1/S1 evidence 重新验证完整；
- 无新增 fork/parent/Python 非历史回归；
- 所有数字来自版本化 raw evidence，可由独立 parser 复算；
- 执行报告明确限制为冻结无量纲短轨迹数值资格，不宣称长期、生理、FSI 或 EFE 机制。

## 14. Out Of Scope

- 重判或删除 v09/v10；
- 改 mesh、换 edge 或放宽阈值来“通过”旧 case；
- merge 后手工改坐标；
- 通用最优 collapse placement、误差估计器或 adaptive remesh policy；
- 长时间 remesh 统计、ECM/flow 耦合或参数标定；
- EFE Node 1 三层动态计算和 Figure 2；
- Node 2 慢状态、疾病模型或实验拟合；
- Git commit、push、pull、远端同步、PR 或发布。

## 15. Required Memory Updates

仅当 v11 经过执行、独立检查并获人类接受后，项目记忆才允许记录：

- `can_be_merged` 只代表拓扑 eligibility，production commit 还需要材料可接受性；
- remesh 与材料迁移采用 prepare/commit/reject 原子语义；
- endpoint-preserving collapse 与 midpoint coarsening 是不同操作；
- v09/v10 继续是有效历史失败；
- X1-K 的最终状态及具体 D1/S1/R1r/C1/F1 evidence；
- 即使 X1-K 通过，Node 1 N1-1 仍需单独人类授权。

若 v11 失败，只记录新的 failure-and-repair memory，不得把部分 GREEN 测试稳定化为 X1-K pass。

## 16. Human approval requested

请人类终审接受、修改或否决以下四个核心决定：

1. 使用事务化 `prepare → commit/reject` 修复 cell+material 整体原子性；
2. 选择显式 survivor 的端点保留 collapse，而不是 split-ancestor 专用 undo；
3. 用新的 R1r 取代“midpoint merge 必须是 split 几何逆”的错误测试语义，同时永久保留 v09/v10 失败；
4. R1r 通过后按顺序执行 C1 和扩展 F1，但即使 v11 总通过也先返回人类，不自动启动三层 Node 1。

合同获批前不得修改 fork、parent remesh/material 代码或运行 v11 response。
