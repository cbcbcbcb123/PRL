---
contract_id: CONTRACT-PAPER2-FIGURE1-THREE-LAYER-THEORY-V01
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_theory_first
baseline_commit: 73fdd570fa7204806bd704a84c44f3eaf804e0e6
baseline_upstream_ahead_behind: 0/0
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
fluid_status: absent
evidence_level: source_audited_theory_contract_not_validated_mechanism
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 1 三层理论合同 v01

## 0. 合同目的与强制边界

本合同只把当前 `src/paper2_hybrid/` 已实现的二维三层系统翻译成可审阅的理论对象，
冻结 Figure 1 所需的几何、方程、功率端口、无量纲量、极限和否证门。它不是数值运行
授权，也不把 v08 的“迁移等价”升级为生理真实性或普适机制证据。

唯一活跃架构为：**离散心内膜链 + 主动心肌 FEM + 黏弹 ECM FEM**。流体缺席。
心肌 DCM 已完全退出活跃项目，不得作为 comparator、参数、表示轴、图中备选路线或
共同极限分支重新出现。旧 v01–v07 仅是只读历史证据。

本合同基于以下只读源码快照：

| 文件 | SHA-256 |
|---|---|
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |

若独立审阅时任一哈希不一致，本合同只能标记 `SOURCE_DRIFT_BLOCKED`，不得自动按新
源码解释本合同。

## 1. 当前模型能够和不能代表什么

### 1.1 已实现的最小物理

- 二维、小应变、各向同性、平面应变的心肌和 ECM 连续体；
- 心肌以给定轴向主动本征应变收缩，不含电生理和主动张力动力学；
- ECM 为平衡弹性支路与一个 Maxwell 支路并联的标准线性固体（SLS）；
- 心内膜为周期离散节点链，具有轴向、横向近邻弹簧和法向弯曲能；
- 两个界面均为参考构形上的双分量线性 penalty 连接；
- 心肌底面为双分量线性弹性支撑，不是硬夹持；
- 三层共享轴向 affine-periodic 宏观应变，自由涨落周期；
- 系统无惯性，采用体/线阻尼与 SLS 内变量形成过阻尼动态；
- 腔面载荷是直接施加于心内膜链的给定线载荷，不由流体计算。

### 1.2 当前未实现，Figure 1 不得暗示已实现

- 三维曲率、有限应变、几何非线性、材料非线性或屈曲/褶皱；
- 心内膜细胞面积/体积、细胞形状能、重排、分裂、迁移或生长；
- ECM 孔弹性、流固耦合、严格不可压缩、水迁移、重塑、降解或沉积；
- 界面滑移、摩擦、脱黏、黏附更新、单侧接触或损伤；
- 压力由腔内流场反馈、心肌电激活传播或钙动力学；
- EFE、整心房、实验拟合、疾病参数或临床预测。

因此，Figure 1 中的“离散心内膜”必须画成节点—连边链，不能画成已经具有面积守恒、
多边形边界或细胞重排能力的完整细胞模型。

## 2. 几何、变量和符号

### 2.1 理想化二维三层几何

采用一个周期单元

\[
\Omega_m=(-L/2,L/2)\times(-h_m,0),\qquad
\Omega_e=(-L/2,L/2)\times(0,h_e),
\]

其中下层 \(\Omega_m\) 为心肌，上层 \(\Omega_e\) 为 ECM；心内膜链位于
\(\Gamma_n=\{(x,h_e)\}\)。源码分别在局部纵坐标 \([0,h_m]\) 和 \([0,h_e]\)
建网格，以上平移后的堆叠坐标只用于理论表达，不改变源码力学。

取 \(\mathbf e_x\) 沿心肌纤维/周期方向，\(\mathbf e_y\) 从心肌指向 ECM 与腔面。
因此腔面指向心壁的法向载荷为负 \(y\) 方向。

### 2.2 状态变量

| 符号 | 含义 | 当前离散 |
|---|---|---|
| \(\mathbf u_m(\mathbf X,t)\) | 心肌位移 | 三角形 P1 FEM |
| \(\mathbf u_e(\mathbf X,t)\) | ECM 位移 | 三角形 P1 FEM |
| \(\mathbf z(\mathbf X,t)\) | ECM Maxwell 支路内部应变 | 每单元 3 分量 |
| \(\mathbf u_i^n(t)\) | 第 \(i\) 个心内膜链节点位移 | 周期节点链 |
| \(\bar\epsilon(t)\) | 三层共享的轴向宏观应变 | 一个全局自由度 |
| \(a(t)\) | 主动应变幅值 | 给定周期控制量 |
| \(p(x)\) | 主动场空间剖面 | `uniform` 或 `S1` |

代码采用工程剪切 Voigt 记号

\[
\widehat{\boldsymbol\epsilon}
=(\epsilon_{xx},\epsilon_{yy},2\epsilon_{xy})^\mathsf T,
\qquad
\widehat{\boldsymbol\sigma}
=(\sigma_{xx},\sigma_{yy},\sigma_{xy})^\mathsf T.
\]

各向同性平面应变矩阵为

\[
\mathbf C(E,\nu)=
\begin{bmatrix}
\lambda+2\mu&\lambda&0\\
\lambda&\lambda+2\mu&0\\
0&0&\mu
\end{bmatrix},\quad
\mu=\frac{E}{2(1+\nu)},\quad
\lambda=\frac{E\nu}{(1+\nu)(1-2\nu)}.
\]

### 2.3 周期与宏观应变条件

对 \(\alpha\in\{m,e,n\}\)，

\[
\mathbf u_\alpha(L/2,t)-\mathbf u_\alpha(-L/2,t)
=\bar\epsilon(t)L\mathbf e_x,
\]

其余涨落和 ECM 内变量沿 \(x\) 周期，对偶牵引反周期。\(\bar\epsilon\) 在生产工况中
是共同未知量，其变分方程给出周期单元的宏观轴向平衡；`P1` 仅是人为给定微小
\(\bar\epsilon\) 的被动切线诊断，不是生产边界条件。

## 3. 三层本构和界面方程

### 3.1 主动心肌 FEM

定义 \(\mathbf M=(1,0,0)^\mathsf T\)。当前主动本征应变为
\(-a(t)p(x)\mathbf M\)，故心肌自由能和应力为

\[
\Psi_m=\frac12\int_{\Omega_m}
\big(\widehat{\boldsymbol\epsilon}_m+a p\mathbf M\big)^\mathsf T
\mathbf C_m
\big(\widehat{\boldsymbol\epsilon}_m+a p\mathbf M\big)\,dA,
\]

\[
\widehat{\boldsymbol\sigma}_m
=\mathbf C_m\big(\widehat{\boldsymbol\epsilon}_m+a p\mathbf M\big).
\]

所以 \(a>0\) 的无载应力自由状态是轴向缩短
\(\epsilon_{xx}=-a p\)，不是外加边界位移或表面力。当前周期波形为

\[
a(t)=\frac{a_0}{2}\,[1-\cos(2\pi t/T)].
\]

`uniform` 使用 \(p=1\)；`S1` 使用

\[
p(x)=1+c_A\cos(2\pi x/L),\qquad c_A=0.35.
\]

### 3.2 黏弹 ECM FEM

令 \(\mathbf C_\infty\) 为平衡支路，\(\mathbf C_M\) 为 Maxwell 支路。ECM 自由能、
应力和内部变量演化为

\[
\Psi_e=\frac12\int_{\Omega_e}
\widehat{\boldsymbol\epsilon}_e^\mathsf T\mathbf C_\infty
\widehat{\boldsymbol\epsilon}_e
+(\widehat{\boldsymbol\epsilon}_e-\mathbf z)^\mathsf T\mathbf C_M
(\widehat{\boldsymbol\epsilon}_e-\mathbf z)\,dA,
\]

\[
\widehat{\boldsymbol\sigma}_e
=\mathbf C_\infty\widehat{\boldsymbol\epsilon}_e
+\mathbf C_M(\widehat{\boldsymbol\epsilon}_e-\mathbf z),
\]

\[
\tau\mathbf C_M\dot{\mathbf z}
+\mathbf C_M(\mathbf z-\widehat{\boldsymbol\epsilon}_e)=\mathbf0,
\quad\text{即}\quad
\tau\dot{\mathbf z}+\mathbf z=\widehat{\boldsymbol\epsilon}_e.
\]

源码允许平衡支路和 Maxwell 支路具有不同泊松比。当前 \(\nu_\infty=0.45\) 只是近似
不可压，不是不可压约束。

### 3.3 离散心内膜链

令 \(\Delta x=L/N\)，周期指标按模 \(N\) 解释，并包含共享 affine 宏观应变。当前能量为

\[
\Psi_n=\frac12\sum_{i=0}^{N-1}\left[
\frac{k_x^n}{\Delta x}(u^n_{i+1,x}-u^n_{i,x})^2
+\frac{k_y^n}{\Delta x}(u^n_{i+1,y}-u^n_{i,y})^2
\right]
+\frac{\kappa_n}{2\Delta x^3}\sum_{i=0}^{N-1}
(u^n_{i-1,y}-2u^n_{i,y}+u^n_{i+1,y})^2.
\]

这里的 \(k_y^n\) 是相邻节点法向位移差的线性刚度，不是局部细胞面积或体积约束。

### 3.4 两个 penalty 界面

定义位移跳跃和源码报告牵引

\[
\mathbf j_{me}=\mathbf u_m^+-\mathbf u_e^-,\qquad
\mathbf t_{me}^{\rm rep}=k_{me}\mathbf j_{me},
\]

\[
\mathbf j_{ne}=\mathbf u_n-\mathbf u_e^+,\qquad
\mathbf t_{ne}^{\rm rep}=k_{ne}\mathbf j_{ne}.
\]

界面能为

\[
\Psi_I=\frac12\int_{\Gamma_{me}}k_{me}|\mathbf j_{me}|^2\,ds
+\frac12\int_{\Gamma_{ne}}k_{ne}|\mathbf j_{ne}|^2\,ds.
\]

`rep` 必须保留到论文符号经 Supervisor 确认：它是对第一个命名域的**内部残量方向**。
因此实际作用在第一个域上的弹簧力为 \(-\mathbf t^{\rm rep}\)，作用在第二个域上的力为
\(+\mathbf t^{\rm rep}\)，两者严格反向。对应强式界面条件为

\[
\boldsymbol\sigma_m\mathbf n_m=-\mathbf t_{me}^{\rm rep},\qquad
\boldsymbol\sigma_e\mathbf n_e=+\mathbf t_{me}^{\rm rep}
\quad(\Gamma_{me}),
\]

以及 ECM 上表面受 \(+\mathbf t_{ne}^{\rm rep}\)，心内膜链受
\(-\mathbf t_{ne}^{\rm rep}\)。离散装配使用梯形线积分权重；共同界面上的总力必须逐对
相消。

### 3.5 底部支撑和腔面载荷

心肌底面支撑能为

\[
\Psi_s=\frac12\int_{\Gamma_s}
\left(k_{sx}u_{m,x}^2+k_{sy}u_{m,y}^2\right)ds,
\quad
\boldsymbol\sigma_m\mathbf n_m=-\mathbf K_s\mathbf u_m.
\]

腔面载荷 \(\mathbf t_L(x,t)\) 直接作用在离散链。负 \(y\) 为从腔面指向心壁，正 \(x\)
为切向正方向。它是外载功端口，不是流体压力解。

### 3.6 过阻尼平衡

连续体内部满足

\[
\gamma_m\dot{\mathbf u}_m-\nabla\!\cdot\boldsymbol\sigma_m=\mathbf0,
\qquad
\gamma_e\dot{\mathbf u}_e-\nabla\!\cdot\boldsymbol\sigma_e=\mathbf0,
\]

心内膜节点满足

\[
\xi_n w_i\dot{\mathbf u}_i^n
+\frac{\partial(\Psi_n+\Psi_I)}{\partial\mathbf u_i^n}
=w_i\mathbf t_{L,i}.
\]

弱式是全系统的权威表达。以包含连续位移、链节点、宏观应变和 \(\mathbf z\) 的广义状态
\(\mathbf q\) 表示，源码装配为

\[
\mathbf G\dot{\mathbf q}+(\mathbf K_{mat}+\mathbf K_s)\mathbf q
=\mathbf f_L(t)-\mathbf h\,a(t),
\]

其中 \(\mathbf G=\mathbf C_{drag}+\mathbf C_{SLS}\)，且
\(\mathbf C_{SLS}\) 只在 \(\mathbf z\) 块中含
\(\tau\mathbf C_M\)。系统无质量矩阵乘加速度项，因此不得称为惯性动力学。

## 4. 自由能、功率端口与耗散闭合

### 4.1 两种等价能量分区

源码物质自由能为

\[
\Psi_{mat}=\Psi_m+\Psi_e+\Psi_n+\Psi_I
=\frac12\mathbf q^\mathsf T\mathbf K_{mat}\mathbf q
+a\,\mathbf h^\mathsf T\mathbf q+\frac12c_a a^2.
\]

热力学总储能可写成 \(\Psi_{tot}=\Psi_{mat}+\Psi_s\)。源码功率账本把支撑放在外部
保守端口，而非放入 `material_energy`；两种分区必须给出相同总平衡，不得混用。

### 4.2 连续功率定义

\[
P_a=\frac{\partial\Psi_{mat}}{\partial a}\dot a
=\left(\mathbf h^\mathsf T\mathbf q+c_a a\right)\dot a,
\]

\[
P_L=\mathbf f_L^\mathsf T\dot{\mathbf q},\qquad
P_s=-(\mathbf K_s\mathbf q)^\mathsf T\dot{\mathbf q}=-\dot\Psi_s,
\]

\[
\mathcal D_{drag}=\dot{\mathbf q}^\mathsf T\mathbf C_{drag}\dot{\mathbf q}\ge0,
\qquad
\mathcal D_{SLS}=\int_{\Omega_e}
\tau\dot{\mathbf z}^\mathsf T\mathbf C_M\dot{\mathbf z}\,dA\ge0.
\]

实现一致的连续闭合为

\[
P_a+P_L+P_s=\dot\Psi_{mat}+\mathcal D_{drag}+\mathcal D_{SLS},
\]

等价地

\[
P_a+P_L=\dot\Psi_{tot}+\mathcal D_{drag}+\mathcal D_{SLS}.
\]

`active power` 是主动本征应变控制量与其能量共轭量的功率端口，不可替换为“主动表面
力乘速度”。周期稳态下若 \(\mathbf q(T)=\mathbf q(0)\)、\(a(T)=a(0)\)，则总储能变化为
零，整周期输入功等于两类耗散。

### 4.3 源码一致的离散闭合

令 \(\Delta\mathbf q=\mathbf q_{n+1}-\mathbf q_n\)，上标 \(n+1/2\) 表示端点平均，
\(\Delta t=T/N_t\)。Crank–Nicolson 平衡为

\[
\mathbf G\frac{\Delta\mathbf q}{\Delta t}
+(\mathbf K_{mat}+\mathbf K_s)\mathbf q^{n+1/2}
=\mathbf f_L^{n+1/2}-\mathbf h a^{n+1/2}.
\]

对当前二次—双线性能量，权威离散能量增量是

\[
\Delta_d\Psi_{mat}=
(\mathbf K_{mat}\mathbf q^{n+1/2}+\mathbf h a^{n+1/2})^\mathsf T
\Delta\mathbf q
+(\mathbf h^\mathsf T\mathbf q^{n+1/2}+c_a a^{n+1/2})\Delta a.
\]

各步账本为

\[
W_a=(\mathbf h^\mathsf T\mathbf q^{n+1/2}+c_a a^{n+1/2})\Delta a,
\]

\[
W_L=(\mathbf f_L^{n+1/2})^\mathsf T\Delta\mathbf q,
\qquad
W_s=-(\mathbf K_s\mathbf q^{n+1/2})^\mathsf T\Delta\mathbf q,
\]

\[
D_{drag}=\frac{\Delta\mathbf q^\mathsf T\mathbf C_{drag}\Delta\mathbf q}{\Delta t},
\qquad
D_{SLS}=\frac{\Delta\mathbf q^\mathsf T\mathbf C_{SLS}\Delta\mathbf q}{\Delta t},
\]

\[
W_a+W_L+W_s-\Delta_d\Psi_{mat}-D_{drag}-D_{SLS}=W_{eq\ defect}.
\]

精确平衡时右端为零。直接用两个很接近的端点能量相减只作 sidecar 审计；不得替代
\(\Delta_d\Psi_{mat}\)，以免浮点消减误差被误判为物理功率缺口。

## 5. 最小无量纲结构

取 \(L\)、心搏周期 \(T\) 和 ECM 平衡 Young 模量 \(E_\infty\) 为参考量。当前代码是
无量纲 benchmark，表中的“当前值”只是源码参数映射，不是斑马鱼测量值。

### 5.1 Figure 3 主轴和 Figure 1 必须展示的控制量

| 组 | 定义 | 控制机制 | 独立性要求 | 未来可测量接口 | 当前值/状态 |
|---|---|---|---|---|---|
| \(De\) | \(\tau/T\) | ECM 记忆相对心搏快慢，决定 Maxwell 支路幅值和相位 | 若通过改变 \(T\) 扫描，会同时改变所有阻尼比；主扫描应固定 \(T\) 而改变 \(\tau\)，或同步保持阻尼组不变 | 周期 \(T\)；ECM 应力松弛时间 \(\tau\) | 0.22 |
| \(H\) | \(h_e/L\) | 有限厚度、跨层衰减和边界影响 | 固定 \(L,h_m/L\) 与网格误差后才可独立解释 | 分割得到 ECM 厚度与周期/组织尺度 | 0.30 |
| \(\mathbf K_I\) | \((k_{me}L/E_\infty,\ k_{ne}L/E_\infty)\) | 两界面的跳跃、牵引传递和有效串联柔度 | 两个界面通常不可合并为一个 \(K\)；只有经证明的对称或串联降阶才可合并 | 跨界面位移—牵引反演、黏附扰动 | (8, 7) |
| \(\mathcal A\) | \(\sigma_{a0}/E_\infty\)，\(\sigma_{a0}=C_{m,xxxx}a_0\) | 主动收缩相对于 ECM 参考刚度的驱动强度 | 与 \(E_m/E_\infty\) 和 \(a_0\) 不同时独立；扫 \(\mathcal A\) 时必须固定其中一个并报告另一个 | 无载短缩 \(a_0\)、主动应力或牵引、心肌模量 | 约 0.337 |
| \(\mathbf B_d\) | \((\gamma_mL^2/E_\infty T,\ \gamma_eL^2/E_\infty T,\ \xi_nL/E_\infty T)\) | 过阻尼弹性响应时间相对心搏周期 | 改变 \(T\) 会与 \(De\) 同时变化；三层阻尼不可在未验证前合并 | 多频位移—相位响应或释放实验 | (0.12, 0.05, 0.10) |
| \(\Lambda_A\) | \(\ell_A/L\) | 主动异质性尺度与跨层机械平滑尺度的竞争 | 必须在异质性幅度 \(c_A\) 固定时改变；均匀场没有有限 \(\ell_A\) | 钙/肌节激活空间图的波长或相关长度 | `S1`: 1；通用变化未实现 |

### 5.2 必须冻结为条件变量、不能藏在主轴后的组

| 组 | 定义与作用 | 当前值/状态 |
|---|---|---|
| \(H_m\) | \(h_m/L\)，心肌相对厚度 | 0.20 |
| \(R_m\) | \(E_m/E_\infty\)，被动心肌/ECM 刚度比 | 2.5 |
| \(R_M\) | \(E_M/E_\infty\)，ECM 瞬时增量与频率响应幅度 | 0.7 |
| \(\boldsymbol\nu\) | \((\nu_m,\nu_\infty,\nu_M)\)，决定平面应变下剪切/体积权重 | (0.30, 0.45, 0.30) |
| \(\mathbf R_n\) | \((k_x^n/E_\infty L,\ k_y^n/E_\infty L,\ \kappa_n/E_\infty L^3)\)，链拉伸、法向梯度和弯曲 | (0.8, 0.25, 0.02) |
| \(\mathbf S\) | \((k_{sx}L/E_\infty,\ k_{sy}L/E_\infty)\)，底部支撑 | (0.45, 0.60) |
| \(c_A\) | 主动场异质性幅度；必须与 \(\Lambda_A\) 分开 | `S1`: 0.35 |
| \(\mathbf T_L\) | \((t_{L,n}/E_\infty,t_{L,t}/E_\infty)\)，给定腔面载荷 | 峰值 (0.08, 0.05) |

若 \(\nu_\infty\) 或 \(\nu_M\) 也参与变化，仅用 \(R_M\) 不足以表征 SLS；必须改用
平衡/Maxwell 的体积模量比与剪切模量比。该扩展尚未实现，属于
`candidate_choice_for_supervisor`。

## 6. 强制极限与可预期结论

| 极限 | 必须得到的结果 | 证据边界 |
|---|---|---|
| 被动 \(a=0\) | 主动端口严格为零；响应只来自外载或被动诊断 | 不等于零驱动 |
| 零驱动 \(a=0,\mathbf f_L=0\) | 在底部支撑控制刚体模态时，\(\mathbf q=0,\mathbf z=0\)，牵引和耗散为零 | 对应 `P0` |
| ECM 无黏性/快速松弛 \(De\to0\) | 除初始边界层外 \(\mathbf z\to\epsilon_e\)，Maxwell 应力与 SLS 耗散消失，只剩 \(\mathbf C_\infty\) | 不等于令所有体/线阻尼为零 |
| 慢松弛 \(De\to\infty\) | 周期振荡分量上 \(\mathbf z\) 近冻结，ECM 接近 \(\mathbf C_\infty+\mathbf C_M\)；DC 分量仍可松弛，历史/初值需显式说明 | 不得笼统称为“完全弹性”而忽略 DC |
| 无体/线阻尼 \(\mathbf B_d\to0\) | 与 SLS 无黏性分开处理；系统趋于准静态代数/微分代数极限 | 当前求解路径未单独验证该奇异极限 |
| 薄 ECM \(H\to0\) | 固定体模量时跨层有效刚度通常随 \(1/h_e\) 增大；非平凡界面极限需说明保持 \(E\)、\(Eh\) 或 \(E/h\) 中哪一个 | 路径未定，见候选选择 C1 |
| 软界面 \(\mathbf K_I\to0\) | 相应界面牵引趋零并解耦；若失去刚体控制，必须报告奇异/不可辨识而非伪响应 | 两界面必须分别取极限 |
| 刚界面 \(\mathbf K_I\to\infty\) | 位移跳跃趋零，得到 tied-interface 概念极限；penalty 条件数恶化必须单列 | 不能以单个任意大值宣称已达极限 |
| 均匀主动场 \(p=1\) | 在均匀几何/载荷下恢复轴向平移对称；`S1` 型唯一热点消失 | 若仍出现固定热点，优先判为网格/边界伪影 |

## 7. 候选机制、反例和 fail-closed 标签

### 7.1 Figure 1 只允许提出的候选机制

1. 有限 \(De\) 使 ECM 成为频率依赖的幅值—相位滤波层；
2. 有限 \(H\) 与两个有限界面刚度共同决定跨层传递和空间平滑；
3. 当主动场尺度 \(\Lambda_A\) 接近机械平滑尺度时，主动场粗粒化与跨界面传递可能
   不对易；
4. 总输入功在可恢复储能、体/线阻尼耗散与 SLS 耗散间重新分配。

以上均是待 Figure 2–4 验证的候选，不是 Figure 1 的结果。

### 7.2 反例与否证条件

- 若改变 \(De\) 后的响应可完全由同步变化的 \(\mathbf B_d\) 解释，则“ECM 记忆控制”
  未被识别；
- 若 \(De\times H\) 趋势在边界支撑、界面刚度或网格改变后反向，不能称为普适状态图；
- 若两个不同 \((De,H,\mathbf K_I,\mathbf B_d)\) 组合产生不可区分输出，则参数反演不可
  识别，不能从单一相位/幅值唯一推断 ECM 参数；
- 若均匀主动场仍产生锁定于三角网格方向的热点，则空间机制被数值各向异性否定；
- 若 \(\Lambda_A\) 的留出变化不提高共同 QoI 的预测，粗粒化不对易机制应被否定或缩窄；
- 当前系统是线性的，若所谓阈值、分岔、褶皱或损伤现象只来自本模型，直接判为
  `SCOPE_OVERCLAIM`；
- 单一正弦频率只给一个频点的传递幅值与相位，不能据此宣称完整频谱规律。

### 7.3 失败标签

| 标签 | 触发条件 | 处置 |
|---|---|---|
| `SOURCE_DRIFT_BLOCKED` | 基线、源码哈希或活跃角色变化 | 停止审阅，另立版本 |
| `FORMULATION_MISMATCH` | 合同方程不能逐项映射到当前装配 | Figure 1 不通过 |
| `SIGN_OR_ACTION_REACTION_FAIL` | 任一界面方向或成对合力不闭合 | Figure 1 不通过 |
| `POWER_CONJUGACY_FAIL` | 主动、外载、支撑任一功率共轭量错误 | Figure 1 不通过 |
| `NEGATIVE_DISSIPATION_FAIL` | 正定参数下出现物理耗散为负 | Figure 1 不通过 |
| `LIMIT_INCONSISTENT_FAIL` | 第 6 节任一适用极限不闭合 | Figure 1 不通过 |
| `UNIDENTIFIABLE_GROUPS` | 目标组与隐藏共变量无法独立改变或观测 | 缩窄机制，不做唯一反演 |
| `MECHANISM_FALSIFIED` | 预登记趋势或留出预测失败 | 保留失败，收缩或放弃候选机制 |
| `SCOPE_OVERCLAIM` | 把二维线性模型外推为褶皱、EFE、流体或临床结论 | 拒绝相应图文 |
| `UNRESOLVED_CANDIDATE_CHOICE` | 下节候选项影响方程/极限但未裁决 | 不授权后续计算 |

## 8. `candidate_choice_for_supervisor`

以下内容不是当前源码唯一决定的物理，Executor 不自行选择：

1. **`candidate_choice_for_supervisor/C1` 薄层渐近路径：** \(H\to0\) 时保持三维体模量、面内积分刚度 \(Eh\)，还是
   跨层刚度 \(E/h\) 的目标量不变；Figure 3 前必须选定。
2. **`candidate_choice_for_supervisor/C2` 通用主动场族：** 当前只有 `uniform` 和一个 \(c_A=0.35,\ell_A=L\) 的余弦；
   是否新增可变波长、随机相关场或相位传播，必须另立实现合同。
3. **`candidate_choice_for_supervisor/C3` ECM 流变参数化：** 若泊松比参与变化，采用体积/剪切两个 Maxwell 比，而不是
   单一 \(E_M/E_\infty\)。
4. **`candidate_choice_for_supervisor/C4` 论文牵引命名：** 是保留源码 `reported/internal-residual traction`，还是把图中箭头
   全部转换为“第二域施加于第一域的物理力”；无论选择哪一种，不能混用。
5. **`candidate_choice_for_supervisor/C5` 腔面端口角色：** Figure 1 可展示给定腔面载荷端口，但 Figure 3 主机制是采用
   主动驱动单独工况，还是保留主动—外载组合，需在参数预登记前决定。
6. **`candidate_choice_for_supervisor/C6` 无阻尼奇异极限：** 是否把 \(\mathbf B_d\to0\) 纳入正文极限；若纳入，需另证
   代数/微分代数问题的适定性，不能沿用当前直接求解通过作为证明。

任何 C1–C6 的裁决都只能影响后续版本；本合同不授权修改源码。

## 9. Figure 1 面板级内容合同（本轮不制图）

| 面板 | 必须展示 | 禁止展示 | 证据标签 |
|---|---|---|---|
| a 三层几何与方向 | 周期单元、\(L,h_m,h_e\)、\(x/y\)、心肌/ECM/链、两界面、底部支撑、可选腔面载荷、主动收缩方向 | DCM 心肌、流体流线、三维心房、真实细胞多边形 | model definition |
| b 构成模块 | 心肌主动本征应变；ECM 的 \(E_\infty\parallel(E_M,\eta)\) SLS；链的轴向/横向/弯曲；两个界面弹簧 | 脱黏、接触、孔弹性或未实现的非线性元件 | implemented constitutive structure |
| c 方程与功率端口 | 广义平衡、\(P_a,P_L,P_s\)、\(\dot\Psi\)、\(\mathcal D_{drag},\mathcal D_{SLS}\) 和作用—反作用箭头 | 数值 PASS 当作机制证据 | source-audited identity |
| d 无量纲结构 | 核心 \(De,H\)，条件组 \(\mathbf K_I,\mathcal A,\mathbf B_d,\Lambda_A\)，并标出隐藏控制量 | 把候选组画成已发现相图 | preregistered candidate controls |
| e 极限与否证 | 快/慢松弛、软/刚界面、薄层、均匀主动场，以及 fail-closed 路径 | 预测热图、实验拟合或疾病结论 | falsifiable theory contract |

图注必须写明：二维、线性、小应变、过阻尼、无流体；面板 d/e 是候选规律和验证路线，
不是已观察结果。

## 10. 实验接口：仅供未来约束和留出验证

实验在当前阶段不得用于拟合。未来可按预先划分的 calibration/hold-out 规则提供：

- 影像分割：\(L,h_m,h_e\) 和位移相位；
- 高速心搏影像：\(T\)、跨层位移传递率和相位差；
- ECM 松弛/频率实验：\(E_\infty,E_M,\tau,\nu\) 的约束；
- 无载短缩、主动牵引或肌节/钙成像：\(a_0,\sigma_{a0},c_A,\ell_A\)；
- 界面扰动结合跨界面位移：\(k_{me},k_{ne}\) 的范围；
- 心内膜链形变或局部力学实验：\(k_x^n,k_y^n,\kappa_n\) 的范围；
- 至少一个未参与参数约束的个体、时相、频率、几何或扰动作为留出验证。

若只测得位移而没有独立材料或力学约束，应优先报告可辨识参数组合，不做单参数唯一
反演。

## 11. Figure 1 fail-closed 验收门

独立 Supervisor 只有在以下全部满足时才可接受本合同：

1. 基线与四个源码哈希一致，且唯一活跃角色未变化；
2. 独立重推 \(\Psi_m,\Psi_e,\Psi_n,\Psi_I\) 对状态的变分，与源码矩阵符号逐项一致；
3. 两界面内部残量与实际物理力方向明确，作用—反作用严格闭合；
4. 连续功率恒等式与精确离散增量分别闭合，支撑能的两种分区不混用；
5. 所有无量纲量通过量纲检查，并列出依赖关系，未把相关参数伪装成独立轴；
6. 被动、零驱动、快/慢松弛、无黏性、无体/线阻尼、薄层、软/刚界面和均匀主动场
   极限均有一致解释；
7. C1–C6 被明确裁决，或从本轮 Figure 1/后续 Figure 3 范围显式排除；
8. Figure 1 面板不包含未实现物理、数值结果、实验拟合或疾病外推；
9. 合同保持 `source_audited_theory_contract_not_validated_mechanism` 标签；
10. 审阅只产生接受/修订决定，不自动授权 Figure 2、Figure 3 或任何计算。

任一条失败即 fail closed，使用第 7.3 节标签返回修改，不得以“总体趋势合理”豁免。

## 12. 从迁移等价到普适机制的证据缺口

v08 已证明新活跃包在同一容器和浮点路径下重现冻结旧 FEM 臂；这只关闭软件迁移门。
要接近 Nature Physics 的战略设计标准，至少仍缺：

1. 当前架构自身的联合时间—空间—容差—投影—功率闭合；
2. 从方程导出的简洁传递尺度或降阶关系，而非只画平滑参数响应；
3. `De×H` 规律在多个边界、几何和网格上的方向稳健性；
4. 对未参与拟合/调参点的定量留出预测；
5. 主动场粗粒化与跨层传递不对易的共同极限和稳定增量证据；
6. 参数可辨识性、替代机制和反例的主动排除；
7. 后续独立实验或真实几何验证。

当前线性二维模型若最终只产生预期的线性滤波和连续参数响应，应按证据降至更合适的
PRX Life，或在贡献形态和篇幅确实适合时评估 Physical Review Letters。Nature Physics
只是机制深度、普适性和独立预测的战略标准，不是当前投稿成熟度结论。

## 13. 停止边界

本合同完成后必须停在 Supervisor Gate。本轮不授权 solver、Docker、参数扫描、Figure 1
图片、Figure 2/3/4/5、3D、整心房、流体/CFD/FSI、实验拟合、GPU worker、代码/测试/
结果/CURRENT_STATUS 修改，亦不授权 `git add`、commit 或 push。
