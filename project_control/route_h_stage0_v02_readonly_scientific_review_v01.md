---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V02-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V02
inspector: Codex current task; single-worker read-only scientific audit
inspected_at: 2026-07-29T16:20:00+08:00
status: revision_required
related_memory_entries: []
---

# Route H Stage 0 v02 只读科学检查报告 v01

## 1. 检查结论

结论：`revision_required`。

Stage 0 v02 相比 v01 有实质进步：

- B3 的 Gate C 支撑所有权冲突已经闭合；
- 动态排斥与材料黏附已在概念上分离；
- 主动首选长度的轴、功率符号和固定参考权重彼此一致；
- 完整贴片的层次、尺寸、主要端口和支撑矩阵已经显式化。

但 v02 尚不能作为 Stage 1 的充分入口。检查发现 7 项修订要求，其中前 6 项直接影响参考态、算子可复现性、边界条件或预注册验收；第 7 项在所有当前固定支撑用例中数值为零，但合同的一般移动支撑功率定义不完整。

本报告不授权 Stage 1，也没有修改任何 v02 冻结件。

## 2. 独立性与只读边界

本次检查在当前 Codex 任务中以只读检查职责完成，没有创建独立角色窗口或第二检查者。因此：

- 对冻结产物的操作独立：是；检查期间未修改冻结件；
- 与原编写者的组织/人员独立：否；
- 可作为科学复核和下一版修订依据；
- 不应被描述为第二人员、双盲或角色隔离的独立验收。

检查前复算 v02 冻结清单：

- 8/8 个封存文件 SHA-256 与冻结记录一致；
- 漂移数：0；
- 冻结记录 SHA-256：`6067237F996EC42F2BBC1CB7B90C4816CBF94B4819F248B37043A824D4845359`。

本报告是新增检查产物，不属于 v02 原冻结清单。

## 3. 检查方法

检查采用 science-first 只读方法：

1. 复核冻结哈希、ID、授权边界和文件间引用；
2. 从定义重推无预应力参考态；
3. 检查主动、细胞、ECM、排斥、黏附和支撑的功率/耗散符号；
4. 检查材料配对是否能从规范唯一复现；
5. 检查 Gate C、Gate D、完整贴片及周期敏感性的边界所有者；
6. 检查 case 时间协议、数值加密和验收指标是否可执行；
7. 构造代表性几何方向和移动基座功率反例。

未执行：

- 表面或 ECM 网格实例化；
- 求解器、自动微分或有限差分测试；
- Gate A–E；
- 参数扫描或科学结果生成。

## 4. 阻断项总表

| ID | 严重性 | 关联 | 结论 |
|---|---|---|---|
| V02-REF-TRACTION-001 | blocking | B1 | 超椭球—平面界面并非逐点零间隙，当前黏附势会产生参考预牵引，和 `reference_prestress=false` 冲突 |
| V02-GEOM-ID-001 | blocking | B1/B4 | “canonical icosahedron order”没有给出顶点/面数组和 ID 生成顺序，参考网格与锚点 face ID 不能唯一复现 |
| V02-TETHER-SPEC-001 | blocking | B2 | 冻结材料黏附仍缺少积分点、邻接、覆盖、投影和 unmatched 规则，pair registry 不能由合同唯一生成 |
| V02-BOUNDARY-MAP-001 | blocking | B4 | 外向侧面所有者缺少确定性方向规则；周期边界“相同 template vertex ID”映射与贴片晶格长度不相容 |
| V02-REFINEMENT-001 | blocking | verification | 固定 162/320 拓扑、禁止 remeshing 与空间 edge-scale 加密预注册互相矛盾 |
| V02-PROTOCOL-METRIC-001 | blocking | cases/verification | 压力/WSS 只有幅值，没有时间协议和终止时间；多个 normalized 指标没有分母定义 |
| V02-SUPPORT-POWER-001 | major; fix before moving support is enabled | ledger | 移动 Kelvin–Voigt 支撑输入功率漏掉阻尼基座功；当前固定参考用例中该项恰为零 |

## 5. 详细发现

### 5.1 V02-REF-TRACTION-001 — “nominal gap = 0”不能建立无预牵引参考态

冻结几何把细胞表面定义为 `p=8` 超椭球映射，把 ECM 界面定义为平面。细胞中心和半轴只保证极点接触平面：

- 心内膜中心 `z=-0.12`、半轴 `a_z=0.12`，顶极点位于 `z=0`；
- 心肌中心 `z=0.48`、半轴 `a_z=0.28`，底极点位于 `z=0.20`。

这不意味着整个 `basal_ecm` 材料面逐点 `g=0`。

取规范允许的代表方向

`u=(1/sqrt(2),0,±1/sqrt(2))`。

在 `p=8` 映射下，轴向比例为

`q=2^(-1/8)=0.9170040432`。

于是相对 ECM 平面的代表性正间隙为：

- 心内膜：`g_endo=0.12(1-q)=0.0099595148`；
- 心肌：`g_myo=0.28(1-q)=0.0232388679`。

两者都处于 `0<g<g_c=0.08`。当前黏附势

`phi=-w(1-3s^2+2s^3)`，`s=g/g_c`

在该区间的斜率大小为

`|dphi/dg|=(6w/g_c)s(1-s)>0`。

取 cell–ECM 的 `w=0.03`，得到：

- 心内膜代表点：`|dphi/dg|≈0.24524`；
- 心肌代表点：`|dphi/dg|≈0.46373`。

因此，只要冻结黏附配对覆盖非极点 basal 区域，参考态就有吸引牵引。若配对只覆盖极点，则又缺少面覆盖和剪切传递能力的规范。

受影响的冻结声明：

- `reference_prestress=false`；
- “all registered interfaces have zero reference gap”；
- `REF-FORCE-FREE-CONTRACT` 的静态通过状态；
- Gate C/D/E 的零载参考残差预期。

修订要求：

1. 不能再用单个 `nominal_gap=0` 代表整个材料界面；
2. 对每个冻结材料 tether 登记精确参考自然间隙 `g0_pair`，并以 `g-g0_pair` 定义零牵引自然坐标；或将黏附材料面构造成严格共面的平坦面；
3. 动态排斥仍必须使用物理 signed gap `g`，不得因自然间隙平移而失去防穿透含义；
4. 在允许网格实例化后，必须直接验证总装配参考力和力矩残差，而不是只检查势函数在 `g=0` 的斜率。

### 5.2 V02-GEOM-ID-001 — 参考网格 ID 仍不可唯一复现

几何规范写的是：

`unit_icosahedron_with_canonical_12_vertex_20_face_order`。

但没有列出：

- 12 个种子顶点的精确坐标与 ID；
- 20 个有向面的精确顶点序列与 face ID；
- 每级 subdivision 中新 midpoint ID 的全局分配顺序；
- 四个子面的固定输出顺序。

“canonical”不是唯一算法。不同实现可生成几何等价但 ID 不同的网格；而 v02 又要求：

- 材料面身份持久化；
- 锚定 face ID 哈希；
- template vertex ID 周期配对；
- 完整参考 bundle SHA-256。

几何等价但 ID 不同会导致锚点、配对和哈希不同，因此 B1 的身份冻结和 B4 的可重复几何尚未闭合。

修订要求：

- 在 Stage 0 新版本中直接列出种子顶点/有向面数组、浮点坐标规则和 subdivision ID/face 输出顺序；或引用一个已封存、可读的模板资产及其 SHA-256；
- 在材料化之前定义舍入和序列化规则，避免跨实现哈希漂移。

### 5.3 V02-TETHER-SPEC-001 — 材料黏附 pair registry 仍不是可执行规范

v02 已正确区分：

- 每个接受状态重算的动态排斥；
- 从参考态建立并冻结的材料黏附。

但“deterministic mutual-nearest quadrature pairing with lexicographic ID tie-break”还缺少决定最终离散算子的必要信息：

- 每个三角面的积分点数、位置和权重；
- 哪些实体对属于 eligible neighbor pair；
- reference search radius 和最大允许自然间隙；
- mutual-nearest 是一对一、允许多对一，还是只筛选候选；
- 未配对积分点的处理和最低覆盖率；
- master/slave 材料点是顶点、面内固定重心坐标还是参考最近点；
- 最近点落在边/顶点时的确定性规则；
- 面法向、signed gap 和面内基的退化/切换规则；
- cell–cell、cell–ECM 两类接口的面积归属，避免漏计或重复计。

仅在生成后哈希 pair registry 可以防止漂移，却不能证明 registry 是由冻结规范唯一产生。完整负梯度条款也无法补足尚未定义的离散能量。

修订要求：

- 给出逐步、可复算的材料 pair 构造算法；
- 明确 reference quadrature、邻接表、自然间隙、覆盖阈值、唯一 owner 和序列化；
- 将“配对构造确定性测试”和“界面覆盖测试”列为参考 bundle seal 前置门。

### 5.4 V02-BOUNDARY-MAP-001 — 侧向和周期边界映射未闭合

#### 主贴片侧向所有者

材料 face identity 只有 `lateral`，但主贴片支撑写成：

`outward-facing lateral faces of perimeter myocardial cells only`。

没有冻结规则说明如何把 `lateral` 再分为 `x- / x+ / y- / y+`，也没有说明角部面和等值方向如何处理。因此 primary lateral support owner registry 不能仅从现有规范唯一生成。

同时，未获端口的心内膜周边 lateral 面和 ECM lateral 边界没有逐类明确写成自然零牵引。`direct_support=false` 不等于完整边界分配。

#### 周期敏感性

周期规则要求跨边界配对“相同 template vertex ID”。若两侧边界细胞取相同朝向，同一 template ID 的相对坐标抵消，得到的是细胞中心差，而不是晶格长度：

| 方向 | 晶格长度 | 相同 template ID 的中心差 | 不匹配 |
|---|---:|---:|---:|
| x | 3.0 | 2.0 | -1.0 |
| y，心内膜 | 1.8 | 0.9 | -0.9 |
| y，心肌 | 1.8 | 1.2 | -0.6 |

真正的周期面应将左侧负向材料点与右侧正向材料点配对，通常需要参数方向反射或显式 opposite-face map，而不是相同 ID。

修订要求：

1. 冻结 `lateral_x_minus/lateral_x_plus/lateral_y_minus/lateral_y_plus` 的参考方向规则；
2. 明确主贴片每类外边界是支撑、血流、周期还是零牵引；
3. 用显式 opposite-face material map 定义周期配对和晶格平移；
4. 对 ECM 边界节点、心内膜细胞和心肌细胞分别给出配对规则；
5. 若 E5 暂不需要，可从主冻结 case registry 移出并在后续独立敏感性版本中定义。

### 5.5 V02-REFINEMENT-001 — 固定拓扑与空间加密互相矛盾

同一冻结版本同时要求：

- subdivision level 固定为 2；
- 每个细胞固定 162 顶点、320 面；
- Stage 1/2 fixed topology；
- remeshing disabled；
- ECM 固定为 `12×8×2`；
- 空间加密 edge scales 为 `[1.25,1.0,0.8]`；
- Gate E 必须通过 `SPACE-REFINEMENT`。

当前没有三套预注册网格，也没有说明 edge scale 作用于细胞、ECM、接触积分还是全部离散。若改变网格，会改变 face ID、anchor ID、pair registry 和 reference bundle hash；若不改变网格，则无法执行空间加密。

修订要求二选一：

- 在新版本中冻结 coarse/base/fine 三套确定性参考几何与跨网格观测映射；或
- 删除当前 Stage 0 的空间加密 pass/fail，保留时间加密，并把空间收敛放到另行批准的离散化验证版本。

### 5.6 V02-PROTOCOL-METRIC-001 — 用例时间协议和归一化指标不充分

主动输入有完整的 rest–ramp–hold–release 协议；压力和 WSS 只有幅值/向量，没有：

- 起始时间；
- ramp 形状和持续时间；
- hold/release；
- 与主动协议的同步关系；
- pressure-only/WSS-only 的总时长；
- combined case 的终止时间和积分区间。

在过阻尼系统中，阶跃、缓升和恒载会产生不同峰值、耗散和积分功率，不能在 Stage 1 临时选择而仍声称 case 已预注册。

此外，下列阈值只有数值，没有冻结的归一化公式：

- pairwise action–reaction normalized residual；
- static equilibrium normalized residual；
- pressure/WSS leakage；
- integrated normalized power residual；
- time/space refinement relative difference。

特别是功率残差需要明确：

- 瞬时还是时间积分；
- 分子采用带符号残差还是绝对值积分；
- 分母由 `|Delta Psi|`、`integral D`、`integral |P|` 中哪些项组成；
- 零载 case 的尺度下限；
- 离散时间端点和求积规则。

修订要求：

- 冻结 pressure/WSS 的时间函数、总时长和 combined 同步关系；
- 为每个 normalized/relative metric 给出精确分子、分母、范数、时间窗和零分母保护；
- 明确每个 refinement test 比较的 response metric 列表。

### 5.7 V02-SUPPORT-POWER-001 — 移动支撑输入功率漏掉阻尼基座功

对 Kelvin–Voigt 支撑，令

`r=x-y`，`v_rel=v-y_dot`，

`Psi_s=0.5 r^T K r`，

`D_s=v_rel^T C v_rel`。

支撑对模型节点的总力为

`F_s=-K r-C v_rel`

`=dPsi_s/dy-C v_rel`。

若基座移动，其对模型输入的功率应为

`P_y=F_s·y_dot`

`=(dPsi_s/dy-C(v-y_dot))·y_dot`。

当前 ledger 只登记

`(dPsi_s/dy)·y_dot`，

漏掉

`-C(v-y_dot)·y_dot`。

所有注册用例都冻结 `y_dot=0`，所以该遗漏在当前 cases 中数值为零，不改变 Gate C/D/E 的固定基座平衡。但合同将 `P_environment` 和 `P_fixture_D` 描述为一般移动参考端口，因此定义仍不完整。

修订要求：

- 若移动参考保留为合同能力，补全弹簧与阻尼两部分的基座输入功率；
- 若 Stage 0 只允许固定参考，则从合同一般功率所有者中删除“moving”能力，并明确两个输入端口恒为零。

## 6. 已通过的科学复核项

以下项目在定义层面没有发现新的阻断问题：

1. **主动轴与功率符号**  
   `Lf=||c_plus-c_minus||`、随动中心轴和固定参考面积权重相容；制造的首选长度缩短给出正的控制器输入功率。

2. **细胞参考能**  
   在 `gamma=0`、`A=A0`、`V=V0`、`theta=theta0` 时，面积、体积和弯曲力可为零。

3. **ECM 热力学符号**  
   `F0=I`、`J0=1`、`Z0=0` 使 ECM 储能梯度为零；`eta Z_dot=-dW/dZ` 给出 `D=eta||Z_dot||^2>=0`。

4. **动态排斥/材料黏附的概念分离**  
   v02 已消除“动态搜索集合同时承担持久黏附身份”的直接混用；剩余问题是离散构造不充分。

5. **Gate C 所有权**  
   支撑只属于 `myocardium.opposite_outer`，ECM 心腔侧零牵引；原 B3 已解决。

6. **Gate D 夹具隔离**  
   `P_FIXTURE_D` 已明确为测试夹具，未继承到完整贴片。

7. **血流法向**  
   压力和 WSS 使用当前心内膜顶端法向/切向投影，且不直接加载 ECM。

8. **授权边界**  
   contract、specialization、cases 和 reference bundle 均保持 Stage 1/网格实例化未授权。

这些“通过”只表示方程和合同文本没有发现对应矛盾，不等于实现或数值测试通过。

## 7. B1–B4 复核判定

| 原检查项 | v02 判定 | 原因 |
|---|---|---|
| B1 参考态/身份/锚点 | partially_resolved_revision_required | `V0/A0/theta0/Lf0/Z0` 已定义，但非共面黏附产生参考预牵引，种子网格 ID 仍不唯一 |
| B2 接触配对/完整梯度 | partially_resolved_revision_required | 算子已分离、完整梯度已要求，但离散 pair/quadrature/coverage 仍无法唯一生成 |
| B3 Gate C 支撑冲突 | resolved | 心肌外侧唯一支撑，ECM 心腔侧零牵引，Gate D fixture 已隔离 |
| B4 几何/法向/边界 | partially_resolved_revision_required | 主几何与当前法向已定义，但侧向 owner 与周期映射仍不闭合 |

## 8. 验收与生命周期建议

### 当前状态

- v02 冻结件：保持冻结，作为不可变修订尝试记录；
- v02 科学检查：`revision_required`；
- Stage 1：继续锁定；
- stable memory：不得更新；
- Gate A–E：不得运行。

### 建议的最小下一版范围

若用户批准修订，应创建 **Stage 0 v03**，只处理：

1. 每个材料 tether 的自然参考间隙/零牵引定义；
2. 完全确定的种子网格、ID 和序列化；
3. 完整材料 pair/quadrature/coverage 算法；
4. 主贴片方向性侧面 owner 和正确 opposite-face 周期映射；
5. fixed topology 与 space refinement 的二选一路线；
6. pressure/WSS 时间协议和所有 normalized metric；
7. 移动支撑阻尼基座功或固定端口能力收缩。

不得在修订 Stage 0 的同时实现 solver、生成网格实例或运行任何响应。

## 9. 检查终止

本次只读检查终止于报告写入和冻结件不变性复核。没有执行修复，也没有产生进入 Stage 1 的授权。
