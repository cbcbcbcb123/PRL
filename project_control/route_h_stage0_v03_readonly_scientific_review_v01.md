---
inspection_id: INSPECT-PRL-ROUTE-H-STAGE0-V03-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V03
inspector: Codex current task; single-worker read-only scientific audit
inspected_at: 2026-07-30T19:01:43+08:00
status: revision_required
related_memory_entries: []
---

# Route H Stage 0 v03 只读科学检查报告 v01

## 1. 检查结论

结论：`revision_required`。

v03 已经实质修复 v02 报告中的大部分问题：

- 材料 tether 现在逐 pair 保存自然间隙 `g0_pair`，参考态黏附开度和滑移均为零；
- icosahedron 种子、细分、ID、序列化、ECM 四面体划分和材料面身份已经确定化；
- 材料 tether 的 master quadrature、ray hit、邻接、覆盖和 hash 字段已经显式化；
- Gate C、Gate D 和完整贴片的边界所有者已区分，v02 中错误的周期敏感性已移出；
- 压力、WSS、主动输入的时间包络、积分区间、功率残差和时间加密指标已经冻结；
- 所有当前支撑均为固定参考 Kelvin–Voigt 端口，基座输入功率严格为零。

但 v03 仍不能作为 Stage 1 的充分入口。本次从离散势本身重推后发现 3 项必须先修订的问题：

1. 动态 steric 把“任意 triangle 的有向平面侧别”当作封闭曲面的穿透判据；在两个完全分离的细胞之间也可得到 `g<0`，从而产生伪排斥；
2. 压力/WSS 的连续 traction 和功率表达式已经给出，但面 quadrature、nodal force 分配及 `v_face` 定义没有冻结，离散外力和离散功率不能唯一复现；
3. 验证注册表要求“basal source map 唯一”，但 v03 没有定义或封存该 map，`SOURCE-JMYO-ZERO` 因而不可执行。

本报告不授权 Stage 1，不修改任何 v03 冻结件，也不生成网格、求解器或响应结果。

## 2. 独立性、只读边界与完整性

本次检查在当前 Codex 任务中以单工作者只读检查完成，没有建立第二检查者或角色隔离窗口。因此：

- 对冻结产物的操作独立：是；检查期间没有修改冻结件；
- 与 v03 编写过程的人员/组织独立：否；
- 可作为科学复核和下一版修订依据；
- 不应称为第二人员、双盲或角色隔离的独立验收。

检查开始时复算：

- 8/8 个 v03 封存文件 SHA-256 与冻结记录一致；
- v03 冻结记录本身 SHA-256 一致；
- 合计 `9/9` 匹配，漂移数 `0`；
- 冻结记录 SHA-256：`74B8848E6BC73F26B4C6D46F75571F5565DF84D5456C9AD87113005F8EB5FE55`。

格式复核：

- 4/4 个 JSON 文件可由 Python 和 Node 标准 JSON 解析器读取；
- power ledger 为 29 行、10 列；
- verification registry 为 67 行、11 列。

本报告是新增检查产物，不属于 v03 原冻结清单。

## 3. 检查方法

本次采用 science-first 只读复核：

1. 复核冻结哈希、状态、授权边界和跨文件引用；
2. 从势函数重推参考态牵引、连续性、客观性和 pair 力/力矩；
3. 构造封闭曲面外部点反例，检查 dynamic steric signed gap 是否真能判定穿透；
4. 从虚功定义重推 pressure/WSS 的离散 nodal force 与功率；
5. 检查细胞、ECM、主动控制、支撑和 gauge 的能量/耗散符号；
6. 检查 Gate A–E 的边界所有权、case 输入、指标和 falsifier；
7. 检查每个注册测试是否有可执行的冻结对象。

未执行：

- 参考细胞或 ECM 网格实例化；
- material tether registry 实例化；
- 求解器、自动微分或有限差分测试；
- Gate A–E；
- 参数扫描、图片或科学结论生成。

## 4. 阻断项总表

| ID | 严重性 | 关联 | 结论 |
|---|---|---|---|
| V03-STERIC-SIGN-001 | blocking | B2 / reference seal | 单个 triangle 的 `g=(x_v-q_f)·n_f` 不是封闭曲面的 signed distance；按当前候选定义会对外部未穿透点产生伪排斥，且没有冻结唯一 surface-feature owner |
| V03-BLOOD-LOAD-DISCRETE-001 | blocking | B4 / D / E / power | pressure/WSS 缺少面 quadrature、nodal force 分配和 `v_face` 定义，外力、resultant、leakage 与功率不能由合同唯一装配 |
| V03-SOURCE-MAP-001 | blocking for registered Gate C verification | C / verification | `SOURCE-JMYO-ZERO` 要求 basal source map 唯一，但 v03 没有 source-map 构造、owner、权重或封存数组 |

另有 2 项非阻断建模说明需要在下一版明确：

| ID | 严重性 | 结论 |
|---|---|---|
| V03-ADH-COMPRESSION-SLACK-001 | caveat | `0≤g<g0_pair` 时黏附法向力和 steric 力都为零；这是有限宽度的闭合松弛带，应明确为有意模型假设 |
| V03-SENSOR-SEMANTICS-001 | caveat | `chi_E` 使用未投影的 `||tau_w||` 且为单一标量；当前因无机械反馈不破坏功率，但其生物学解释应限定为全局诊断量 |

## 5. 详细发现

### 5.1 V03-STERIC-SIGN-001 — triangle 平面侧别不能判定封闭曲面穿透

v03 的动态排斥定义为：

- 对 AABB 距离在 buffer 内的所有 cell–cell 和 cell–ECM 实体对建立双向 vertex-to-triangle candidates；
- 每个 primitive 使用当前 triangle 上的 closest point `q_triangle`；
- `g=(x_vertex-q_triangle)·n_triangle_outward`；
- `phi_rep=0.5*k_rep*max(-g,0)^2`，再乘穿透 vertex 的固定参考 dual-area；
- candidate set 在每个接受状态重算。

该 `g` 只表示一个点位于某个三角形有向平面的哪一侧，不表示该点位于整个封闭曲面的内部还是外部。

构造最简单的反例：令实体 B 位于实体 A 的右侧，二者完全分离。取 B 的 `+x` 外表面 triangle，其外法向为 `n_f=+e_x`；再取 A 中位于该 triangle 左侧的任意 vertex。即使该 vertex 明显位于 B 外部，也有

`g=(x_v-q_f)·e_x<0`。

当前势因此给出 `phi_rep>0` 和非零排斥。对任何闭合凸曲面，一个外部点通常都位于许多“远侧面”的内向半空间中，所以该反例不是退化情形。

这一问题在 v03 的参考几何中会被实际触发到候选层：

- 同层相邻细胞的 AABB 在参考态相接；
- cell–ECM 的 AABB 也在界面处相接；
- frozen search buffer 为正；
- `candidate_primitives` 没有规定“每个 vertex 只保留另一实体全表面上的唯一最近 feature”，也没有 primitive-level 距离/owner 规则。

因此存在两种解释，两种都不能进入 Stage 1：

1. **按文本字面求和所有候选 primitive**：会产生大规模伪排斥，参考态 assembled force 不能按合同预期为零；
2. **实现者自行推断只取全表面最近 triangle**：合同没有冻结跨 triangle 的最小化、inside/outside、tie、边界面集合和 owner，结果不可唯一复现。

此外，当前仅用 vertex-to-triangle 势，triangle–triangle 的纯 edge–edge 交叉只由事后 intersection guard 拒绝，没有在接近交叉时提供排斥能。guard 可以作为失败检测，但不能替代防穿透算子。

修订要求：

1. 明确 cell surface 和 ECM **外边界 surface** 的 primitive 集合；不得把 ECM 内部 tetra face 当作接触面；
2. 对每个有向 `(vertex entity, target surface entity)` 冻结唯一 active surface-feature owner：
   - 在目标实体完整外边界上求全局最近点；
   - 精确规定 face/edge/vertex tie；
   - 使用封闭曲面 inside/outside 或等价可靠方法确定 signed distance 的符号；
   - 外部为正、内部为负；
3. 冻结“一 vertex–一 target surface”的计权和 owner，或明确另一种无伪排斥、无重复计数的离散积分；
4. 对 edge–edge 接近选择其一：
   - 加入保守 edge–edge 势；或
   - 冻结连续碰撞检测与 contact-safe step 规则，证明交叉前状态可被拒绝；
5. 新增静态反例测试：
   - 两个分离闭合体的所有 active signed distances 非负；
   - 参考 patch steric energy、force 和 moment 为零；
   - 一个已知内部点产生负 signed distance；
   - 刚体变换保持能量和力的协变性。

现有 `STERIC-DISCRETE-SPEC=verified_static_at_freeze` 只能说明若干字段存在，不能证明 signed-gap 算子的科学正确性。

### 5.2 V03-BLOOD-LOAD-DISCRETE-001 — 连续 traction 尚未闭合为唯一离散端口

v03 已冻结连续层面的方向：

`t_p=-p(t)n_a(x)`，

`t_tau=(I-n_a⊗n_a)tau_w(t)`。

这两个式子的符号正确：

- 参考 apical outward normal 为 `-e_z`，所以正压力给出 `+e_z` 的入壁载荷；
- `n_a·t_tau=0`，WSS 为当前切向；
- blood load 只属于 endocardium apical，ECM 不直接受载。

但 power ledger 仅写：

`P_face=A_face*t_face·v_face`。

冻结文件没有定义：

- `A_face` 是当前面积还是参考面积；
- 每面几个 quadrature、坐标和权重；
- `v_face` 是重心插值速度、面积平均速度，还是其他量；
- traction 如何分配到三个节点；
- nodal resultant、leakage 和 power 是否使用同一离散 force block；
- follower normal 更新后，拒绝/接受状态中的法向和面积在哪个时刻评估。

例如，对每个当前平面 triangle，以下是一种自洽离散，但它只是可能选择之一，并未在 v03 中冻结：

`f_fa=(A_f/3)t_f,  a=1,2,3`，

`v_f=(v_f1+v_f2+v_f3)/3`，

于是

`sum_a f_fa·v_fa=A_f*t_f·v_f`。

如果实现者选择参考面积、不同 quadrature 或不同速度定义，resultant、瞬时功率和 integrated power residual 都会改变。`LOAD-PRESSURE-NORMAL`、`LOAD-WSS-TANGENTIAL` 和 `POWER-INTEGRATED-RESIDUAL` 因而尚不是可重复的实现测试。

修订要求：

1. 冻结 pressure/WSS 的面 quadrature、当前/参考面积选择和 nodal shape weights；
2. 明确 `v_face`；
3. 要求 ledger power 直接由**同一个已装配 nodal force block**计算：

   `P_pressure=sum_i f_pressure_i·v_i`，

   `P_WSS=sum_i f_WSS_i·v_i`；

4. resultant 和 leakage 也必须由同一 force block汇总；
5. 增加单 triangle 手算测试，核对 nodal force、resultant、法向/切向泄漏和功率。

### 5.3 V03-SOURCE-MAP-001 — 注册测试引用了不存在的 basal source map

verification registry 中的 `SOURCE-JMYO-ZERO` 要求：

> The basal source map is unique while j_myo remains zero.

power ledger 也写明：

`j_myo=0; basal source map may be tested`。

但 v03 的 contract、geometry spec、specialization 和 cases 只冻结了标量 `j_myo=0`，没有定义：

- 哪些 myocardial basal quadrature 是 source owner；
- 映射到哪个 ECM face/tetra；
- 面积权重和方向；
- 多对一/边界 tie；
- source map record 和 hash。

这也没有完全落实项目 handoff 中“心肌来源 ECM 必须以细胞基底面通量映射到相邻 ECM 单元，不能使用无细胞归属的均匀源”的边界。

当前 `j_myo=0`，所以缺失 map 不产生机械力、质量或功率；但 Gate C 的已注册测试仍不可执行。

修订要求二选一：

1. 若保留 source-map 预注册：冻结其 owner、quadrature、cell-to-ECM 映射、权重、record 和 hash；可复用 IF_MYO_ECM 的材料射线几何，但必须显式声明，不能由实现者猜测；
2. 若 Stage 0 当前只允许严格零源：删除“map 唯一”的测试与 ledger 语句，只验证没有 source state、source assembly、source power 和 source owner。未来启用非零 `j_myo` 时再建立新合同版本。

## 6. 非阻断但必须显式记录的建模假设

### 6.1 V03-ADH-COMPRESSION-SLACK-001

材料黏附使用 `delta_g=g-g0_pair`。法向势为：

- `delta_g<0`：常数 `-w`；
- `0≤delta_g≤g_c`：C1 cubic cohesive branch；
- `delta_g>g_c`：0。

因此：

- 参考态 `delta_g=0` 的一阶导数为零，确实无参考黏附牵引；
- 当界面从自然间隙闭合但仍未物理重叠，即 `0≤g<g0_pair`，黏附法向力为零；
- dynamic steric 只在物理 `g<0` 时启动；
- 所以宽度为 `g0_pair` 的闭合区间没有法向恢复力。

这可以被解释为“黏附只抗拉、真正接触才抗压”的有意机制，不必强制修改。但下一版应把它写成显式模型假设，并在 Gate C/D 输出中区分：

- adhesive opening；
- physical gap；
- compression slack；
- physical penetration。

cohesive branch 在 `delta_g=0` 和 `g_c` 处为 C1、非 C2；Stage 1 的非线性算法需要显式事件/半光滑处理。

### 6.2 V03-SENSOR-SEMANTICS-001

`chi_E` 当前为单一标量，输入是注册向量的未投影幅值 `||tau_w||`，而实际机械 traction 为投影后的 `||(I-nn)tau_w||`。在表面倾斜时二者不同。

当前 `chi_E`：

- 无机械反馈；
- 无储能、耗散或输入功率；
- 因此不破坏机械 power ledger。

但报告和未来论文只能把它解释为“全局规定 WSS 命令的诊断滤波量”，不能直接称为逐细胞、逐面的实际 endothelial shear sensor。若未来需要后者，应新建空间所有者和局部输入定义。

## 7. 从定义重推后通过的项目

以下项目在定义层面未发现新的阻断问题；它们不是数值通过声明。

### 7.1 材料 tether 的自然间隙修复成立

令

`s=delta_g/g_c`，

`h(s)=1-3s^2+2s^3`。

cohesive branch 为 `phi_n=-w h(s)`，其导数为

`dphi_n/ddelta_g=(6w/g_c)s(1-s)`。

因此在 `delta_g=0` 和 `delta_g=g_c` 都为零，并与两侧常数 branch C1 连接。参考态逐 pair 有：

- `delta_g=0`；
- `delta_t=0`；
- 法向和切向势的一阶导数均为零。

相对向量、当前 master normal 和 co-rotating tangent basis 在共同刚体旋转下同时旋转，点积不变；所以 `delta_g`、`delta_t` 和 tether energy 客观。若完整负梯度正确实现，同一势自动给出 pair 总力和总力矩为零。

v02 的 `V02-REF-TRACTION-001` 和材料 tether 部分的 `V02-TETHER-SPEC-001` 在 v03 文本定义层面已经解决。

### 7.2 细胞和主动能

- 在 `A=A0`、`V=V0`、`theta=theta0`、`gamma=0` 时，被动 cell energy 一阶导数为零；
- active anchor 使用固定参考面积权重；
- `Lf=||c_plus-c_minus||`，主动合力沿 centroid connector；
- 两侧合力相反且共线，所以净力和净力矩为零；
- `P_active=(dPsi/dLf_star)Lf_star_dot=-kf(Lf-Lf_star)Lf_star_dot` 的 RHS 符号正确。

### 7.3 ECM 热力学符号

在 `F=I`：

- `J=1`；
- `C_bar=I`；
- `dev(C_bar)=0`；
- `Z=0`。

平衡和黏弹储能的一阶导数为零。由

`eta_ve Z_dot=-dW_ve/dZ`

得到内部变量对储能的贡献为

`(dW_ve/dZ):Z_dot=-eta_ve||Z_dot||^2`，

所以登记的耗散 `D_ECM=eta_ve||Z_dot||^2≥0` 符号正确。对称无迹子空间由演化式保持。

### 7.4 固定支撑与 gauge 功率

所有 support/fixture reference 均固定：

- `y_dot=0`；
- Kelvin–Voigt 弹簧能进入 LHS；
- 阻尼耗散非负；
- support-base 和 fixture-base input power 均为零。

未支撑 Gate A/B 只允许一个全局 6 约束 holonomic gauge。若约束率严格为零，则 Lagrange multiplier power 为零；它不能被解释为环境反力。

### 7.5 边界和时间协议

- Gate C：support 只属于 `myocardium.opposite_outer`；ECM lumen/lateral 与 myocardial perimeter lateral 为 traction-free；
- Gate D：只有 ECM outer 的固定测试 fixture；不继承到完整贴片；
- 完整贴片：blood、outer support、四向 perimeter support、endocardial traction-free 和 ECM lateral traction-free 的所有者已分开；
- 无 fully fixed boundary；
- v03 不注册周期敏感性；
- `b(t)` 为 C1 rest–ramp–hold–release，零延拓和总时长明确；
- chain delays、combined synchrony、时间加密步长、积分功率分母和 trapezoidal quadrature 已冻结；
- 空间加密未冒充已通过，并在 Stage 2 前设置了单独 geometry-family 硬门。

## 8. B1–B4 复核判定

| 检查项 | v03 判定 | 原因 |
|---|---|---|
| B1 参考态/身份/锚点 | partially_resolved_revision_required | canonical geometry、自然间隙和 reference target 已闭合；但当前 steric signed-gap 可在参考分离状态产生伪排斥，reference assembled force seal 尚不可信 |
| B2 接触配对/完整梯度 | partially_resolved_revision_required | material tether 已闭合；dynamic steric 的 surface sign、唯一 feature owner 和 edge–edge 防穿透尚未闭合 |
| B3 Gate C 支撑冲突 | resolved | 心肌外侧是唯一 support owner，ECM lumen/lateral 零牵引，Gate D fixture 已隔离 |
| B4 几何/法向/边界 | partially_resolved_revision_required | 几何、方向性 lateral identity 和连续 traction 正确；但 blood traction 尚未冻结为唯一 nodal load/power discretization |

## 9. 生命周期判定与最小下一步

### 当前状态

- Stage 0 v03 冻结件：继续保持不可变；
- v03 只读科学检查：`revision_required`；
- reference mesh materialization：仍未授权；
- Stage 1：继续锁定；
- Stage 2：继续锁定；
- Gate A–E：不得运行；
- stable memory：不得更新为“Stage 0 已验收”。

### 若用户后续批准 Stage 0 v04

最小范围仅包括：

1. 用封闭曲面有效 signed distance/唯一 surface-feature owner 修复 dynamic steric，并处理 edge–edge 安全；
2. 冻结 pressure/WSS 的 face quadrature、nodal force 与同源 power assembly；
3. 定义 basal source map，或删除零源版本中不可执行的 map 唯一性测试；
4. 把 adhesion compression slack 和 `chi_E` 语义写成显式解释边界；
5. 更新对应 contract、geometry、ledger、cases 和 verification registry 后重新冻结。

不得把 v04 修订与 mesh materialization、Stage 1 solver 或数值响应合并执行。

## 10. 检查终止

本次只读检查终止于新增本报告和复核冻结件不变性。没有执行修复，也没有产生进入 Stage 1 的授权。
