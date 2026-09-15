# Route H Stage 0 v04 — 坐标、材料配对、载荷和功率约定

## 1. 状态

- 合同：`CONTRACT-PRL-ROUTE-H-STAGE0-V04`
- 几何：`GEOMETRY-PRL-ROUTE-H-STAGE0-V04`
- 状态：`frozen_stage0_pending_readonly_inspection`
- 证据：无量纲机制规范；无网格实例、代码、响应或结果。
- Stage 1：未授权。

## 2. 坐标与材料面

采用右手基：

- `e_x=(1,0,0)`：参考心肌轴；
- `e_y=(0,1,0)`：第二面内方向；
- `e_z=(0,0,1)`：心腔指向外侧心肌。

心内膜顶端参考外法向为 `-e_z`。主贴片为

`x∈[0,3]`，`y∈[0,1.8]`，`z∈[-0.24,0.76]`。

每个细胞三角面有永久 primary identity。`lateral` 面还必须有一个方向性 subtype：

`lateral_x_minus`、`lateral_x_plus`、`lateral_y_minus` 或 `lateral_y_plus`。

身份只由参考参数方向 `u_bar` 决定，变形后不得重标。种子顶点、种子有向面、subdivision ID 顺序和数组序列化均在参考几何规范中逐项冻结。

## 3. 当前血流载荷与时间协议

设 `n_a(x)` 为当前心内膜顶端三角面的外法向。

`t_p=-p(t)n_a(x)`，

`t_tau=[I-n_a(x)⊗n_a(x)]tau_w(t)`。

两者唯一所有者均为 `endocardium.apical_lumen`，不得直接加载 ECM。

对每个当前 apical 有向三角面 `f=(0,1,2)`：

`A_f=0.5||(x_1-x_0)×(x_2-x_0)||`，

`v_f=(v_0+v_1+v_2)/3`。

血流端口只用一个当前重心 quadrature，三个 shape weight 均为 `1/3`：

`f_pressure,fa=(A_f/3)t_p,f`，

`f_WSS,fa=(A_f/3)t_tau,f`。

全局节点力是所有 owned apical 面贡献之和。参考面积不得用于 blood-force assembly。

resultant、法向/切向 leakage 和功率必须来自同一个已装配节点力 block：

`P_pressure=sum_i f_pressure,i·v_i=sum_f A_f t_p,f·v_f`，

`P_WSS=sum_i f_WSS,i·v_i=sum_f A_f t_tau,f·v_f`。

pressure/WSS 是 follower external load，不拥有储能。

所有非零主动、压力和 WSS 输入使用相同包络 `b(t)`：

- `b=0`，`0≤t<1`；
- `b=0.5[1-cos(pi(t-1))]`，`1≤t<2`；
- `b=1`，`2≤t<3`；
- `b=0.5[1+cos(pi(t-3))]`，`3≤t<4`；
- `b=0`，`4≤t≤5`；
- 在 `[0,5]` 外按零延拓。

因此

`alpha(t)=alpha_peak b(t-delay)`，

`p(t)=0.05 b(t)`，

`tau_w(t)=(0.02,0,0)b(t)`。

完整贴片 combined case 三种输入同步。三细胞链的 delay 为 `0,0.5,1.0`，总时长为 `6.0`；其他 gate 时长为 `5.0`。

## 4. 主动首选长度

锚定面集使用固定参考三角面积—节点重心权重：

`d=c_plus-c_minus`，

`Lf=||d||`，

`f=d/Lf`，

`Lf_star=Lf0[1-alpha(t)]`，

`Psi_active=0.5 kf(Lf-Lf_star)^2`。

控制器输入功率位于功率等式右端：

`P_active=(dPsi_active/dLf_star)Lf_star_dot`

`=-kf(Lf-Lf_star)Lf_star_dot`。

该中心力构造的总内力和总内力矩为零。所有 passive `gamma_s=0`，不得用 gamma 代替主动机制。

## 5. 物理间隙、自然间隙与材料黏附

v04 不再把整个超椭球—平面界面视为逐点零物理间隙。

每个冻结材料 tether 保存：

- master/slave 实体和 face ID；
- 两侧固定参考 barycentric 坐标；
- 固定参考面积权重；
- 自然物理间隙 `g0_pair`；
- 参考切向基和法向符号。

当前物理间隙为

`g=(x_slave-x_master)·n_pair`。

黏附开度为

`delta_g=g-g0_pair`。

参考态逐 pair 满足 `delta_g=0`，而不是强迫 `g=0`。

法向黏附势：

- `delta_g<0`：`phi_n=-w`；
- `0≤delta_g≤g_c`：`phi_n=-w(1-3s^2+2s^3)`，`s=delta_g/g_c`；
- `delta_g>g_c`：`phi_n=0`。

因此参考自然开度的法向牵引为零。

该法向黏附是 tension-only。`delta_g<0` 时势为常数，法向黏附力为零。由于动态排斥使用物理 `g`，所以

`0≤g<g0_pair`

是有意保留的 compression-slack 区间：自然黏附间隙闭合时没有法向恢复力，只有 `g<0` 的物理重叠才启动 steric repulsion。报告必须同时输出 physical gap、adhesive opening 和 compression-slack 状态，不能把三者混写。

主面以有向边 `v0→v1` 定义 `t1`，`t2=n_pair×t1`。设 `r=x_slave-x_master`：

`delta_t=[r·t1-r0·t10, r·t2-r0·t20]`。

切向势为

`phi_t=0.5 k_t a(delta_g)||delta_t||^2`。

刚体平移和旋转下 `delta_g`、`delta_t` 及能量保持客观。

## 6. 材料 pair 的唯一生成

每个 eligible master face 只有一个 barycenter quadrature，权重为该面的精确参考面积。

- 心内膜 basal 面沿 `+e_z` 射线映射到 ECM `z=0`；
- 心肌 basal 面沿 `-e_z` 射线映射到 ECM `z=0.2`；
- 同层相邻细胞只枚举 `+x`、`+y` 邻居；master 的正向 lateral subtype 沿对应轴射线映射到 slave 的反向 subtype。

选最近合法 hit，同距取最小 slave face ID。每个 eligible master face 必须成功生成一个 pair；覆盖率必须精确为 100%。当前最近点不得替换冻结材料点。

## 7. 动态排斥

动态排斥使用“source vertex 到完整封闭 target surface 的全局 signed distance”，不得使用单个远侧 triangle 的有向平面侧别，也不得使用 `delta_g`。

### 7.1 封闭边界

- cell target：完整、watertight、外向有向的细胞三角曲面；
- ECM target：只有 ECM 外边界三角面；内部 tetra face 禁止进入接触；
- ECM source vertex：只有 incident 于外边界三角面的 boundary vertex。

在计算 winding number 前，当前 target 必须仍是无 proper self-intersection 的 embedded、外向有向、封闭 2-manifold；ECM 还必须保持每个 tetra 的 `J>0`。不满足时直接判定当前 state 无效，不对自交曲面强行解释 inside/outside。

对每个 eligible 无序实体对 `(A,B)`，同时计算：

- A 的每个 boundary vertex 到 B 的完整 target surface；
- B 的每个 boundary vertex 到 A 的完整 target surface。

### 7.2 唯一全局 owner

对一个 source vertex，遍历 target 的全部外边界 triangle，比较精确欧氏 closest-point distance，只保留一个全局最近 feature。距离同值时按：

1. target face ID；
2. face interior；
3. edge 01、edge 12、edge 20；
4. vertex 0、vertex 1、vertex 2

确定唯一 owner。

target 的 inside/outside 使用完整有向封闭面的 generalized winding number：

`w=|sum_f Omega_f|/(4pi)`。

closest distance `d≤1e-12 L0` 时取 boundary、`g=0`；否则：

- `w<0.5-1e-8`：outside，`g=+d`；
- `w>0.5+1e-8`：inside，`g=-d`；
- `|w-0.5|≤1e-8`：分类歧义，trial state 无效。

因此分离实体的外部 vertex 不会因为位于某个远侧 triangle 的内向半空间而产生伪排斥。

### 7.3 势、权重和 crossing guard

每个 ordered source/target owner 的势为：

`phi_rep=0.5 k_rep A_vertex,0 max(-g,0)^2`。

cell source 的 `A_vertex,0` 为所有 incident cell surface 参考面面积的三分之一和；ECM source 只累计 incident 外边界参考面。双向 sampling 均保留，不再乘额外 `1/2`。

远离 owner/classification event 时，对所选 squared-distance piece 取完整负梯度。同一势同时拥有 source 和 target 力，所以 pair transfer 保持内部。

纯 edge–edge crossing 由从上一 accepted state 到 trial state 的线性节点路径 continuous triangle–triangle collision detection 检查。横截式 proper intersection 必须在接受 trial 前拒绝并减小步长；孤立零测度 tangency 且无 side-sign crossing 可以保留为 `g=0`。若减小到登记最小步长仍不能避免 proper intersection，当前 case 失败。该 guard 不是力、储能或耗散。

材料黏附和动态排斥的力均必须是完整离散势梯度，包括当前法向、材料点和切向基的导数。

## 8. 边界所有者

| 场景 | 边界 | 条件/所有者 |
|---|---|---|
| 完整贴片 | 心内膜 apical | pressure/WSS |
| 完整贴片 | 心肌 opposite_outer | 固定参考顺应支撑 |
| 完整贴片 | 周边心肌 outward directional lateral | 固定参考侧向顺应支撑 |
| 完整贴片 | 周边心内膜 lateral | 零牵引 |
| 完整贴片 | ECM 四个 lateral 边界 | 零牵引 |
| Gate C | 心肌 opposite_outer | 固定参考顺应支撑 |
| Gate C | ECM lumen/lateral 与心肌周边 lateral | 零牵引 |
| Gate D | ECM outer | 固定测试夹具 `P_FIXTURE_D` |
| Gate D | ECM lateral 与心内膜周边 lateral | 零牵引 |

周期敏感性不属于 v04。它需要独立的周期影像相互作用和 ECM 周期边界规范。

## 9. 固定支撑及功率

所有注册支撑参考点固定：`y_dot=0`。

`Psi_support=0.5 sum_i w_i(x_i-y_i)^T K(x_i-y_i)`，

`D_support=sum_i w_i v_i^T C v_i≥0`。

因此

`P_support_base=0`，

`P_fixture_D_base=0`。

v04 不具有移动支撑能力。若以后允许移动基座，必须创建新合同并登记弹簧和阻尼两部分的完整基座功。

## 10. ECM

`C=F^T F`，`J=det(F)>0`，`C_bar=J^(-2/3)C`。

`W_eq=0.5 mu_eq[tr(C_bar)-3]+0.5 kappa_eq(ln J)^2`，

`W_ve=0.25 mu_ve||dev(C_bar)-Z||_F^2`。

`eta_ve Z_dot=-dW_ve/dZ`，

`D_ECM=eta_ve||Z_dot||_F^2≥0`。

参考态为 `F0=I`、`J0=1`、`Z0=0`。`A_hat` 和 `H_ECM_hat` 独立冻结，`j_myo=0`。

## 11. 心肌来源映射与 flow sensor

每个 myocardial `basal_ecm` master face barycenter 有一个独立 source-map record。几何上复用 `IF_MYO_ECM` material tether 已选定的：

- myocardial source cell/face/barycentric；
- ECM outer boundary face/barycentric；
- 与该 boundary face 唯一 incident 的 `target_tetra_id`。

reference weight 是 myocardial basal master triangle 的精确参考面积。source-map owner 与 mechanical tether owner 分开登记并单独 hash。

v04 中 `j_myo=0`，因此所有 record 的 amount rate、ECM source residual 和 source power 均严格为零。非零来源仍未授权。

`chi_E` 只有一个全局 diagnostic scalar：

`tau_chi chi_E_dot=G(||tau_w||)-chi_E`。

这里 `||tau_w||` 是未投影的规定 WSS command vector 的模，不是局部投影 traction 的模。`chi_E` 不是逐细胞/逐面的 endothelial shear sensor，不反馈到机械方程，也不拥有机械功率。

## 12. 功率平衡

`d(Psi_cell+Psi_active+Psi_ECM+Psi_steric+Psi_adhesion+Psi_support)/dt`

`+D_cell+D_ECM+D_support`

`=P_active+P_pressure+P_WSS`。

内部 pair transfer、固定基座、`chi_E`、零源和零功率数值 gauge 均不属于右端输入。

`P_pressure` 和 `P_WSS` 必须由第 3 节的共同 nodal force block 直接计算，不能另写不共轭的面功率近似。

积分功率残差定义为

`|DeltaPsi+Trapz(D)-Trapz(P_active+P_pressure+P_WSS)|`

除以

`max[1,|DeltaPsi|+Trapz(D)+Trapz(|P_active|+|P_pressure|+|P_WSS|)]`。

时间积分使用包括首尾端点的复合梯形规则。

## 13. 离散化边界

v04 只有一个身份冻结的 base topology：

- 每个细胞 162 顶点、320 面；
- ECM 为 351 顶点、1152 四面体；
- 禁止 remeshing。

空间加密和周期敏感性均不在 v04 注册。它们必须在 Stage 2 前由独立版本封存，但当前也不构成 Stage 1 授权。
