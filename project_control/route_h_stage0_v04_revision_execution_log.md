---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V04
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
executor: Codex current task; approved single-task Phase 0 closure
started_at: 2026-07-30T19:10:00+08:00
completed_at: 2026-07-30T19:29:12+08:00
status: completed
deviation_records: []
---

# Route H Stage 0 v04 修订执行记录

## 1. 授权与边界

依据：

- `project_control/route_h_phase_delivery_and_git_sync_decision_v01.md`；
- `project_control/route_h_stage0_v03_readonly_scientific_review_v01.md`；
- 用户指令“同意，开始”。

本执行属于已批准的 Phase 0 内部修订闭环。允许创建、检查、冻结和同步 v04；不允许：

- 参考网格或 source-map 实例化；
- Stage 1 求解器；
- Stage 2 Gate A–E；
- 参数扫描、图件、稿件或稳定 Memory。

v01、v02 和 v03 均保持只读。

## 2. 目标

修复 v03 检查中的三个阻断项：

1. `V03-STERIC-SIGN-001`；
2. `V03-BLOOD-LOAD-DISCRETE-001`；
3. `V03-SOURCE-MAP-001`。

同时把两个非阻断 caveat 变成显式模型边界：

- `V03-ADH-COMPRESSION-SLACK-001`；
- `V03-SENSOR-SEMANTICS-001`。

## 3. 实际修订

### 3.1 动态 steric

旧的“任意 triangle 平面 signed gap”替换为：

- ordered boundary-vertex 到完整封闭 target surface；
- 每个 source vertex 只有一个全局最近 surface feature owner；
- cell 使用完整 watertight surface；
- ECM 只使用 exterior boundary triangle/vertex；
- generalized winding number 判定 inside/outside；
- outside `g=+d`、boundary `g=0`、inside `g=-d`；
- ordered 两个方向都保留，不附加隐含系数；
- target 必须保持 embedded、oriented、closed 且无 proper self-intersection；
- 未被 negative vertex-surface distance 捕获的 proper crossing 由 continuous collision detection 拒绝。

保留原有软穿透 penalty：

`0.5*k_rep*A_vertex0*max(-g,0)^2`。

没有引入新黏附、摩擦、barrier 能或 KKT contact。

### 3.2 blood load

冻结每个当前 apical triangle 的唯一离散：

- current area；
- 一个 barycenter quadrature；
- 三个 `N_a=1/3`；
- `f_fa=(A_f/3)t_f`；
- `v_f=(v_0+v_1+v_2)/3`；
- resultant、leakage 和 power 共用同一 assembled nodal force block；
- `P=sum_i f_i·v_i`。

### 3.3 myocardial source map

每个 myocardial basal master-face barycenter 生成一个独立 source-map record：

- 复用 `IF_MYO_ECM` 已选 ray hit 的几何；
- 保存 source/target face 与 barycentric；
- target ECM boundary face 必须 incident 于唯一 tetra；
- 保存 `target_tetra_id`、reference weight、顺序和 hash；
- v04 中 `j_myo=0`，所有 source assembly、residual 和 power 为零。

### 3.4 caveat

- `0<=g<g0_pair` 明确为 tension-only adhesion 的 compression-slack 区间；
- `chi_E` 明确为一个全局 prescribed WSS command filter，不是局部 shear sensor，且无机械反馈。

## 4. 生成文件

1. `data/route_h/route_h_reference_geometry_spec_v04.json`
2. `src/route_h/route_h_contract_v04.json`
3. `src/route_h/route_h_model_specialization_v04.json`
4. `data/route_h/route_h_cases_v04.json`
5. `docs/route_h/route_h_coordinate_and_sign_convention_v04.md`
6. `docs/route_h/route_h_port_and_power_ledger_v04.csv`
7. `tests/route_h/route_h_verification_registry_v04.csv`
8. 本执行记录

## 5. 检查

最终静态检查结果：

- UTF-8 JSON：`4/4`；
- CSV：`2/2`；
- ledger：30 个唯一 term；
- verification registry：81 个唯一 test；
- Stage 0 静态登记：`41/41`；
- cases：14 个唯一 case，5 个 gate 引用完整；
- contract direct-input hash：`7/7`；
- v02/v03 冻结记录抽取的历史受控 hash：`23/23`；
- Stage 1/2 与 geometry materialization 授权锁：通过；
- placeholder：0；
- manufactured/scientific sanity：`16/16`。

关键 manufactured checks：

- unit-cube 外部点在旧 far-side triangle plane 定义下得到负值，但 generalized winding number 正确给出 outside；
- unit-cube 内部点 winding number 为 1；
- 平移后 winding classification 不变；
- pressure 方向和 WSS 切向投影正确；
- face power 与 assembled nodal-force power 一致；
- cohesive branch 两端一阶导数为零；
- active power、fixed support power、ECM reference state、source zero 和 sensor exclusion 符号一致。

这些检查没有实例化 Route H 参考网格，也不属于 Stage 1 runtime test。

## 6. 偏差与阻断

- 偏差：无；
- 新增 blocking finding：无；
- 未解决的已知边界：
  - adhesion compression slack 是显式接受的模型假设；
  - `chi_E` 仅是全局 command diagnostic；
  - proper edge–edge crossing 无新储能；无法通过最小步长避免时，case 按 falsifier 失败；
  - 空间加密 family 仍是 Stage 2 前置独立门。

## 7. 输出状态

- v04 技术文件：已形成冻结候选；
- reference geometry materialization：未授权、未执行；
- Stage 1：未授权；
- 下一步：生成冻结记录，然后对冻结 v04 做只读科学复核。
