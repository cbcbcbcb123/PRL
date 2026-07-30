---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V04-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V04
inspector: Codex current task; single-worker read-only scientific audit after freeze
inspected_at: 2026-07-30T19:32:28+08:00
status: accepted_with_caveats
related_memory_entries: []
---

# Route H Stage 0 v04 只读科学检查报告 v01

## 1. 结论

结论：`accepted_with_caveats`。

在 Stage 0 **规范层**没有发现新的 blocking scientific finding。v04 已闭合 v03 的三个阻断项：

1. dynamic steric 不再用任意 triangle 平面侧别判穿透；
2. pressure/WSS 已冻结为唯一 nodal load/power 离散；
3. myocardial basal source map 已具有唯一 owner、target boundary face、target tetra 和 hash record。

两个原 caveat 也已成为显式模型边界：

- tension-only adhesion 的 compression slack；
- `chi_E` 的全局 command-diagnostic 语义。

因此 Phase 0 的“结果前模型合同收敛”退出条件在规范层已经达到。该结论不授权 reference bundle materialization、Stage 1、Stage 2 或任何数值结果。

## 2. 独立性和只读边界

本检查在当前 Codex 任务内由同一工作者于 v04 冻结后切换到只读职责完成，没有第二检查者或独立角色窗口。

- 冻结后只读：是；
- 与执行者人员独立：否；
- 可作为单工作者 science-first 复核；
- 不得称为第二人员或角色隔离的独立验收。

冻结入口复核：

- 8/8 个 v04 冻结件 SHA-256 与冻结记录一致；
- 漂移：0；
- v04 冻结记录 SHA-256：
  `78B67E558099734794C09E0B4B1F16C8484C8E5BADE753C97FF406347F2F2BC9`。

本报告是冻结后新增产物，不属于 v04 原冻结清单。

## 3. 检查方法

1. 复核 8 个冻结 hash 和授权锁；
2. 重构 v03 far-side triangle 伪排斥反例；
3. 重推 generalized winding-number sign、全局 closest-feature owner 和势的客观性；
4. 检查 target surface 的 closed/embedded 前提和 proper-crossing guard；
5. 从 nodal virtual power 重推 pressure/WSS；
6. 检查 source-map 的 owner、target tetra、zero assembly 和 ledger exclusion；
7. 重查 cohesive endpoints、主动功、ECM 耗散、固定支撑和全局 power balance；
8. 检查 cases、falsifier、verification IDs 和 Stage 1/2 锁。

未执行网格、source-map materialization、solver、自动微分、Gate A–E 或参数响应。

## 4. 三项阻断修复复核

### 4.1 `V03-STERIC-SIGN-001` — resolved

v03 对单个 target triangle 使用

`g_plane=(x_v-q_f)·n_f`。

对 unit cube 外部点 `x=(-1,0.5,0.5)` 和 cube 的 `+x` 远侧面，有

`g_plane=-2<0`，

尽管该点明显在 cube 外部。这证明旧规则不是封闭曲面 signed distance。

v04 对一个 ordered source vertex：

1. 在 target 的完整外边界上寻找唯一全局最近 feature；
2. 用完整有向 watertight target 的 generalized winding number `w` 分类；
3. 取 outside `g=+d`、boundary `g=0`、inside `g=-d`。

同一 manufactured cube：

- 外部点 `w≈1.77×10^-17`，正确判为 outside；
- 内部点 `(0.5,0.5,0.5)` 的 `w=1`；
- 共同平移后两者分类不变。

因此 far-side plane 伪排斥已被消除。

势

`phi=0.5*k_rep*A_vertex0*max(-g,0)^2`

只依赖实体间欧氏距离和 closed-surface classification。远离 owner/classification event 时，共同刚体平移/旋转不改变势；完整负梯度因此给出零 pair 总力和零 pair 总力矩。

ECM target 已限制为 exterior boundary triangle，内部 tetra face 不参与接触。winding 使用前 target 必须保持 embedded、oriented、closed 且无 proper self-intersection；ECM 还要求 `J>0`。

纯 edge–edge proper crossing 未被伪装成已有 repulsive energy。v04 明确使用 trial-path collision detection 拒绝未被 negative vertex-surface gap 捕获的 crossing；无法在最小步长内避免时 case 失败。这是可证伪边界，不是隐藏修复。

### 4.2 `V03-BLOOD-LOAD-DISCRETE-001` — resolved

对当前 apical triangle：

`f_fa=(A_f/3)t_f`，

`v_f=(v_0+v_1+v_2)/3`。

因此

`sum_a f_fa·v_a`

`=(A_f/3)t_f·(v_0+v_1+v_2)`

`=A_f t_f·v_f`。

v04 要求：

- current area；
- 一个 barycenter quadrature；
- `N_a=1/3`；
- pressure/WSS resultant、leakage 和 power 共用同一个 assembled nodal force block。

所以离散外力与 power conjugacy 唯一，不再允许实现者在 reference/current area 或 `v_face` 上自行选择。

符号仍正确：

- reference apical outward normal `n=-e_z`；
- `t_p=-pn=+p e_z`；
- `n·[(I-nn)tau_w]=0`。

### 4.3 `V03-SOURCE-MAP-001` — resolved

每个 myocardial `basal_ecm` master-face barycenter 拥有一个 source-map record：

- source cell/face/barycentric；
- target ECM outer boundary face/barycentric；
- target boundary face唯一 incident 的 `target_tetra_id`；
- reference area weight；
- 确定性顺序和 hash。

几何上复用 IF_MYO_ECM ray hit，但 source owner 与 mechanical tether owner 分离。

v04 的 `j_myo=0`，所以：

- mapped amount rate = 0；
- ECM source residual = 0；
- source power = 0。

`SOURCE-JMYO-ZERO` 现在具有可 materialize、可 hash、可执行的明确对象。

## 5. 其他科学复核

### 5.1 材料黏附

cohesive cubic 的斜率与 `s(1-s)` 成正比，在 `s=0` 和 `s=1` 均为零，和两侧常数 branch C1 连接。参考态 `delta_g=0`、`delta_t=0`，所以材料 tether 参考牵引为零。

`delta_g<0` 的法向势为常数。v04 已明确：

`0<=g<g0_pair`

是 tension-only adhesion 的 compression-slack 区间；只有 physical `g<0` 才有 steric repulsion。该区间不再是隐藏假设。

### 5.2 主动、ECM、支撑与功率

- active preferred-length 的 RHS input power 符号正确；
- 中心力 anchor 构造在定义层给出零净力/力矩；
- `F=I`、`J=1`、`Z=0` 是 ECM 无应力参考态；
- `eta Z_dot=-dW/dZ` 给出非负 `eta||Z_dot||^2`；
- fixed support 的 base power 为零；
- pressure/WSS 是 nonconservative external power，不重复登记储能；
- source、`chi_E`、pair transfer、CCD guard 和 numerical gauge 均不属于外部输入。

### 5.3 cases 和证据边界

- 14 个 case 和 5 个 gate 引用完整；
- 41 个 Stage 0 静态项已登记；
- 39 个 Stage 1 runtime 项仍为 `registered_not_run_unauthorized`；
- 1 个 Stage 2 discretization block 保留；
- 空间加密 family 仍是 Stage 2 前置独立门；
- 没有 physiological calibration、parameter sweep、图件或机制 claim。

## 6. 接受时保留的 caveat

1. **没有第二检查者**
   当前是单工作者冻结后只读复核，不是人员独立验收。

2. **runtime 尚未执行**
   winding number、global closest owner、collision detection、source-map coverage 和 nodal blood load 只在规范/制造反例层通过；必须在 Stage 1 materialization 后完成注册测试。

3. **proper edge–edge crossing 是 falsifier**
   v04 不为纯 edge–edge 接近增加新 barrier/penalty。若 collision guard 经常使 case 无法推进，必须停机并由用户选择新的 contact route，不能静默改变模型。

4. **compression slack 是模型选择**
   闭合自然间隙但尚未物理重叠时没有法向恢复力。未来解释需同时报告 physical gap、adhesive opening 和 slack state。

5. **`chi_E` 只表示 command diagnostic**
   它不是局部 endothelial shear、KLF2 或基因网络证据。

6. **Stage 2 尚缺空间离散 family**
   v04 只冻结 base topology；该限制不阻止未来获批的 Stage 1，但阻止 Stage 2 scientific execution。

## 7. 生命周期判定

- Phase 0 / Stage 0 规范收敛：`accepted_with_caveats`；
- v04 冻结件：保持不可变；
- stable Memory：不更新；
- reference materialization：未授权；
- Stage 1：仍需用户一次性进入批准；
- Stage 2：未授权。

如果用户批准 Phase 1，下一阶段可以在一个阶段包内连续完成 reference bundle materialization、被动内核、注册测试、修复、检查和 GitHub 同步，不再逐项请示。

## 8. 检查终止

本次检查终止于本报告。冻结后未修改 v04 的 8 个封存文件。
