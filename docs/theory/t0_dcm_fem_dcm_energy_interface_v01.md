---
theory_id: THEORY-PRL-T0-DCM-FEM-DCM-ENERGY-INTERFACE-V01
status: working_draft_for_human_figure_gate
scope: fixed-stage fast-beat mechanics
evidence_level: proposed_theoretical_structure_not_simulation_evidence
contract: project_control/t0_figure1_theory_contract_v01.md
---

# T0 v01：DCM–FEM–DCM 三层能量与界面理论

## 1. 有界科学主张

在固定发育时期和快速心搏尺度下，可以用同一功率一致的非匹配界面算子连接：

1. 主动、可重网格的心肌 DCM；
2. 近不可压缩、黏弹性的 cardiac-jelly FEM；
3. 被动、可弯曲的心内膜 DCM。

接触拓扑只通过实际界面集合及其方向分布进入，不改变基础作用反作用定律。长波、均匀的一维 ECM 极限必须恢复已经通过 M1 门的集中弹簧—阻尼外载。

这是一项待验证的理论结构，不是三层模型已经稳定运行的证据。

## 2. 构型、时间尺度和符号

固定慢时间 (T=T_0)，只求解快时间 (t\in[0,N/ f]\)。细胞数、拓扑、ECM 自然构型和层厚在本阶段不随慢时间演化。

- 第 (a) 个心肌细胞表面节点：\(\mathbf x_m^a(t)\)；
- cardiac-jelly 参考域：\(\Omega_J^0\)，映射 \(\boldsymbol\chi_J(\mathbf X,t)=\mathbf X+\mathbf u_J\)；
- 变形梯度：\(\mathbf F_J=\mathbf I+\nabla_X\mathbf u_J\)，体积比 \(J_J=\det\mathbf F_J\)；
- 第 (b) 个心内膜细胞节点：\(\mathbf x_e^b(t)\)；
- 心肌—ECM 和 ECM—心内膜界面：\(\Gamma_{mJ}\)、\(\Gamma_{Je}\)；
- 心肌主动状态：\(\alpha_m(t)\)，当前是规定周期输入，不是钙动力学模型。

表面分区为

\[
\Gamma_{\mathrm{cell}}
=\Gamma_{\mathrm{ECM}}
\cup\Gamma_{\mathrm{cell-cell}}
\cup\Gamma_{\mathrm{outer}},
\qquad
\Gamma_i\cap\Gamma_j=\varnothing\quad(i\ne j).
\]

早期心脏主工况取基底面单侧 \(\Gamma_{\mathrm{ECM}}\)；全周/四面包埋是通用对照。

## 3. 两类 DCM 的离散功率方程

保留现有单细胞本构的抽象形式。心肌细胞满足

\[
\partial_{\dot{\mathbf x}_m}\Phi_m
+\nabla_{\mathbf x_m}\Psi_m
+\mathbf G_m^\mathsf T\boldsymbol\lambda_m
=\mathbf f_m^{\mathrm{act}}
+\mathbf f_{J\to m}
+\mathbf f_m^{\mathrm{ext}},
\qquad
\mathbf C_m(\mathbf x_m)=\mathbf 0 .
\]

其中 \(\Psi_m\) 含被动膜面、纤维和允许的全局面积正则项；\(\Phi_m\) 是非负耗散势；\(\mathbf C_m\) 包括精确细胞体积约束。主动功率定义为

\[
P_{\mathrm{act}}=\mathbf f_m^{\mathrm{act}}\cdot\dot{\mathbf x}_m .
\]

心内膜基线不含主动驱动：

\[
\partial_{\dot{\mathbf x}_e}\Phi_e
+\nabla_{\mathbf x_e}\Psi_e
+\mathbf G_e^\mathsf T\boldsymbol\lambda_e
=\mathbf f_{J\to e}
+\mathbf f_{\mathrm{lumen}}
+\mathbf f_e^{\mathrm{ext}}.
\]

若后续证据要求内膜主动性，必须作为新版本加入，不能在 T0 默认为零后又在解释中暗用。

## 4. cardiac-jelly 连续体

使用带内部变量 \(\mathbf z_J\) 的热力学形式：

\[
\Psi_J=\int_{\Omega_J^0}
\psi_J(\mathbf F_J,\mathbf z_J)
+\frac{\kappa_J}{2}(J_J-1)^2\,dV,
\qquad \kappa_J/\mu_J\gg1,
\]

\[
\Phi_J=\int_{\Omega_J^0}
\phi_J(\dot{\mathbf F}_J,\dot{\mathbf z}_J)\,dV,
\qquad
\mathcal D_J
=\partial_{\dot{\mathbf F}_J}\Phi_J:\dot{\mathbf F}_J
+\partial_{\dot{\mathbf z}_J}\Phi_J\cdot\dot{\mathbf z}_J\ge0.
\]

其准静态弱式由 \(\delta\Psi_J+\delta_{\dot{\mathbf u}}\Phi_J\) 与界面、腔压和外边界虚功平衡得到。T0 不预先指定 cardiac jelly 必然是 Kelvin–Voigt、标准线性固体还是孔弹体；第一基线只要求可分别识别可恢复弹性和非负速率耗散。孔弹性作为后续竞争模型，不能与黏弹基线同时无约束加参。

“近不可压缩”表示材料体积变化受强烈抑制，不表示局部层间距离 \(h(s,t)\) 不变；层间材料可通过切向位移和形状改变重排。

## 5. 非匹配 DCM–FEM 界面

### 5.1 同一点运动学

在界面求积点，用 \(\mathbf B_m\) 和 \(\mathbf B_J\) 分别从 DCM 节点及 FEM 节点插值得到两侧位置：

\[
\mathbf y_m=\mathbf B_m\mathbf x_m,
\qquad
\mathbf y_J=\mathbf B_J(\mathbf X_J+\mathbf u_J),
\qquad
\mathbf g=\mathbf y_m-\mathbf y_J.
\]

相对位移分解为

\[
g_n=\mathbf g\cdot\mathbf n_J,
\qquad
\mathbf g_t=(\mathbf I-\mathbf n_J\otimes\mathbf n_J)\mathbf g.
\]

### 5.2 界面储能与耗散

对黏附/连接基线定义

\[
\Psi_\Gamma=\int_{\Gamma}
\psi_\Gamma(g_n,\mathbf g_t,\boldsymbol\xi)\,dA,
\qquad
\Phi_\Gamma=\frac12\int_{\Gamma}
\left(\eta_n\dot g_n^2
+\eta_t\|\dot{\mathbf g}_t\|^2\right)dA,
\]

其中 \(\boldsymbol\xi\) 可在未来表示黏附键内部变量，但 T0 不引入断键动力学。界面阻力为

\[
\mathbf r_\Gamma
=\partial_{\mathbf g}\psi_\Gamma
+\partial_{\dot{\mathbf g}}\phi_\Gamma .
\]

若研究真正接触/脱离，则另加

\[
g_n\ge0,\qquad \lambda_n\ge0,\qquad \lambda_n g_n=0,
\]

且把接触反力和黏附力分开记账。心脏基线首先采用持续连接或有限顺应性黏附，不把“组织相连”退化成只有受压时才工作的无黏附接触。

### 5.3 离散作用反作用与功率闭合

设 \(\mathbf W_\Gamma\) 为同一套界面求积权重。界面对两侧的离散力取

\[
\mathbf f_m^\Gamma
=-\mathbf B_m^\mathsf T\mathbf W_\Gamma\mathbf r_\Gamma,
\qquad
\mathbf f_J^\Gamma
=+\mathbf B_J^\mathsf T\mathbf W_\Gamma\mathbf r_\Gamma .
\]

于是两侧界面功率严格满足

\[
(\mathbf f_m^\Gamma)^\mathsf T\mathbf v_m
+(\mathbf f_J^\Gamma)^\mathsf T\mathbf v_J
=-\mathbf r_\Gamma^\mathsf T\mathbf W_\Gamma\dot{\mathbf g}
=-\dot\Psi_\Gamma-\mathcal D_\Gamma,
\]

\[
\mathcal D_\Gamma
=\partial_{\dot{\mathbf g}}\Phi_\Gamma\cdot\dot{\mathbf g}
\ge0.
\]

这一定义比“先算细胞力、再近邻分配给 FEM”更严格：两侧必须使用同一求积点、同一牵引和互为转置的映射，否则会出现网格相关的伪功。

ECM—心内膜界面 \(\Gamma_{Je}\) 使用完全同构的算子，仅替换 DCM 侧自由度和法向方向。

## 6. 三层总能量—功率账本

定义

\[
\Psi_{\mathrm{tot}}
=\Psi_m+\Psi_J+\Psi_e
+\Psi_{mJ}+\Psi_{Je},
\]

\[
\mathcal D_{\mathrm{tot}}
=\mathcal D_m+\mathcal D_J+\mathcal D_e
+\mathcal D_{mJ}+\mathcal D_{Je}\ge0.
\]

固定发育状态下的目标账本为

\[
\boxed{
\frac{d\Psi_{\mathrm{tot}}}{dt}
+\mathcal D_{\mathrm{tot}}
=P_{\mathrm{act}}
+P_{\mathrm{lumen}}
+P_{\mathrm{outer}}
}
\]

其中规定腔压 \(p_L(t)\) 对心内膜的功率采用统一外法向约定：

\[
P_{\mathrm{lumen}}
=\int_{\Gamma_L}\mathbf t_L\cdot\mathbf v_e\,dA,
\qquad
\mathbf t_L=-p_L\mathbf n_{\mathrm{out}}.
\]

内部界面牵引不再单独出现在右端，因为其功率已经转化为界面储能率和界面耗散。周期极限环上还应满足

\[
\Delta_{\mathrm{cycle}}\Psi_{\mathrm{tot}}\simeq0,
\qquad
W_{\mathrm{act}}+W_{\mathrm{lumen}}+W_{\mathrm{outer}}
\simeq D_{\mathrm{tot}}.
\]

## 7. 接触拓扑变量

接触面积分数和面积方向张量定义为

\[
\phi_A=\frac{A_{\mathrm{ECM}}}{A_{\mathrm{cell}}},
\qquad
\mathbf M_A
=\frac{1}{A_{\mathrm{cell}}}
\int_{\Gamma_{\mathrm{ECM}}}\mathbf n\otimes\mathbf n\,dA,
\qquad
\operatorname{tr}(\mathbf M_A)=\phi_A.
\]

单侧基底接触具有强方向性；近全周均匀包埋则趋于 \(\mathbf M_A\approx(\phi_A/3)\mathbf I\)。Figure 2 将检验：在 \(\phi_A\) 匹配时，\(\mathbf M_A\) 是否仍能预测弯曲、牵引局域化和主动功分配。

## 8. 必须恢复的退化极限

### L0：自由单细胞

当 \(A_\Gamma\to0\) 或 \(k_\Gamma,\eta_\Gamma\to0\) 时，\(\mathbf f_{J\to m}\to0\)，恢复已通过的自由单细胞周期模型。

### L1：完全黏结

当界面顺应性趋零时，\(\mathbf g\to\mathbf0\)，DCM 与 FEM 界面速度连续。反力可以有限，但不得产生额外耗散，除非显式保留界面黏性。

### L2：均匀一维 ECM 端口

对厚度 \(H_J\)、面积 \(A_\Gamma\) 的均匀线性黏弹层，远端固定、位移沿厚度均匀时，

\[
K_J^{\mathrm{eff}}=\frac{E_JA_\Gamma}{H_J},
\qquad
C_J^{\mathrm{eff}}=\frac{\eta_JA_\Gamma}{H_J}.
\]

因此广义反力退化为

\[
F_{\mathrm{env}}
=K_J^{\mathrm{eff}}(L_0-q)
-C_J^{\mathrm{eff}}\dot q,
\]

与 M1 外载端口同构。这一极限是从集中模型进入显式 ECM 的主要连续性检查。

### L3：刚性环境/等长趋向

当 \(K_J^{\mathrm{eff}}/K_c^{\mathrm{ax}}\to\infty\) 且界面不滑移，轴向缩短趋零、界面反力保持有限或增加；不得出现“环境越硬缩短越大”的无解释反转。

### L4：去除心内膜

令 \(A_{Je}\to0\) 或心内膜载荷为零，应恢复心肌—ECM 两层问题。这允许在进入完整三层前先验证单个心肌细胞与显式 ECM patch。

## 9. T1 前只注册、不宣称成立的无量纲控制量

\[
\Lambda_E=\frac{K_J^{\mathrm{eff}}}{K_c^{\mathrm{ax}}},
\qquad
De_J=\omega\tau_J,
\qquad
\Lambda_\Gamma=\frac{K_\Gamma^{\mathrm{eff}}}{K_J^{\mathrm{eff}}},
\qquad
\epsilon_H=\frac{H_J}{L_c}.
\]

- \(\Lambda_E\)：环境与细胞轴向刚度竞争；
- \(De_J\)：心搏周期与 ECM 松弛时间竞争；
- \(\Lambda_\Gamma\)：变形主要落在 ECM 还是界面；
- \(\epsilon_H\)：分布式环境能否被一维端口近似。

Figure 1 只定义这些量；跨波长—频率状态相图属于后续 Figure 5，当前不得提前给出机制结论。

## 10. Figure 1 v01 的四个 panel

- **A**：主动心肌 DCM—连续 cardiac-jelly FEM—被动心内膜 DCM；
- **B**：非匹配界面同一点求积、法向/切向位移差和转置力映射；
- **C**：主动功、腔压功、储能与耗散的能量流；
- **D**：自由细胞 → 集中弹簧/阻尼 → 单侧显式 ECM → 完整三层的退化/递进关系。

图注必须写明：“理论结构示意；不是模拟结果；三层数值稳定性、生理参数和 EFE 机制尚未验证。”

## 11. Falsifiers

以下任一结果会否定或迫使收窄当前 Figure 1 主张：

1. 同一连续运动在 DCM 与 FEM 两侧计算出的界面功不相等；
2. 界面能量残差不随时间步或空间加密下降；
3. 均匀一维 ECM 不能恢复 M1 弹簧/阻尼端口；
4. 固定几何下结果依赖选择哪一侧作为界面求积主面；
5. 接触面积匹配后，方向张量对持出工况没有任何预测增益；
6. 要匹配相位只能同时任意调整细胞阻尼、ECM 黏性和界面黏性，导致参数不可识别。

## 12. 当前状态与下一门

本文件是工作草案。下一步不是运行三层求解，而是由人类终审 Figure 1 的：

1. 三层对象是否正确；
2. 单侧接触是否是心脏主边界；
3. 界面采用持续连接/有限顺应性黏附是否合适；
4. 总能量账本和一维退化极限是否保留。

只有 Figure 1 通过后，才能起草 T1 / Figure 2 的“单心肌细胞—单侧显式 FEM ECM patch”计算合同。

