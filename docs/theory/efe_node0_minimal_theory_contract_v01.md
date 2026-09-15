---
theory_id: THEORY-EFE-NODE0-MINIMAL-MULTISCALE-CONTRACT-V01
status: accepted_at_human_gate_0_for_node1_planning
scope: EFE fast_slow_mechanochemical_theory
evidence_level: proposed_theoretical_structure_not_simulation_or_disease_evidence
approved_plan: project_control/efe_theory_mainline_node_plan_v01.md
preserves:
  - project_control/external_scientific_review_constraints_v01.md
  - docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md
human_gate_0_decision: project_control/efe_node0_acceptance_decision_v01.md
---

# EFE Node 0 v01：最小快—慢机械化学理论合同

## 1. 有界科学主张

本合同只提出一个待检验的理论结构：把每个心搏周期内的三层力学响应压缩为局部周期统计量，再由这些统计量推进心内膜细胞状态、纤维生成细胞状态和心内膜下 ECM 重塑。重塑后的 ECM 改变下一次心搏的力学响应，从而闭合快—慢反馈。

候选因果链为：

\[
\text{active myocardium + prescribed lumen loading}
\xrightarrow{\text{fast beat}}
\mathcal M(s,T)
\xrightarrow{\text{slow cell-state kinetics}}
(q_E,q_M)
\xrightarrow{\text{ECM production/growth}}
(\rho_c,\rho_{el},\mathbf A_c,\mathbf F_g)
\xrightarrow{\text{mechanical feedback}}
\mathcal M(s,T+\Delta T).
\]

本合同不宣称：

- 已经证明 EFE 由力学因素引起；
- 已经证明 EndMT 是唯一细胞来源；
- 已经存在双稳态、分岔、机械记忆或临界转变；
- 当前单相黏弹 cardiac jelly 足以预测长期厚度增长；
- 规定的压力和 WSS 等价于双向 FSI；
- 现有代码已经能够稳定执行长期 EFE 模拟。

## 2. 时间尺度与算子分解

### 2.1 两个时间变量

- 快时间 \(t\in[0,T_b]\)：一个心搏周期；
- 慢时间 \(T\)：细胞状态、ECM 更新和发育时间；
- 时间尺度比

\[
\epsilon_t=\frac{T_b}{\tau_r}\ll 1,
\]

其中 \(\tau_r\) 是最短的可信重塑时间尺度。

### 2.2 代表性心搏映射

在慢状态 \(\mathbf y(T)\) 冻结时，快速求解器寻找一个周期状态：

\[
\mathcal X^*(t;\mathbf y,\boldsymbol\ell)
=\mathcal F_{\mathrm{beat}}(\mathbf y,\boldsymbol\ell),
\qquad
\mathcal X^*(t+T_b)=\mathcal X^*(t),
\]

其中 \(\boldsymbol\ell\) 是主动收缩、腔压和 WSS 等规定载荷。周期后处理算子给出

\[
\mathcal M(s,T)=\mathcal P_{\mathrm{cycle}}[\mathcal X^*(t;\mathbf y,\boldsymbol\ell)].
\]

慢状态再由

\[
\frac{d\mathbf y}{dT}=\mathcal R(\mathbf y,\mathcal M,\mathbf c)
\]

更新，其中 \(\mathbf c\) 表示 TGF-\(\beta\)、BMP 等外部生化条件。本结构不逐拍模拟数天或数周。

## 3. 几何、法向与边界

层次从心腔向外依次为：

\[
\text{lumen}
\;|\;
\text{endocardial DCM}
\;|\;
\text{cardiac-jelly / fibrous ECM FEM}
\;|\;
\text{active myocardial DCM}
\;|\;
\text{surroundings}.
\]

定义：

- \(\Gamma_L\)：心内膜顶端、与心腔相邻的表面；
- \(\Gamma_{Je}\)：ECM—心内膜基底界面；
- \(\Gamma_{mJ}\)：心肌—ECM 界面；
- \(\mathbf n_L\)：从固体组织指向心腔的单位外法向；
- \(\mathbf t_p=-p\mathbf n_L\)：腔压作用于固体的牵引；
- \(\boldsymbol\tau_w\cdot\mathbf n_L=0\)：流体作用于心内膜的切向牵引。

第一版把 \(p(s,t)\) 和 \(\boldsymbol\tau_w(s,t)\) 作为规定载荷。它们可以来自成像、降阶流体模型或单向 CFD，但不得称为双向 FSI。

## 4. 快时间力学合同

### 4.1 快状态

\[
\mathcal X=(\mathbf x_m,\mathbf x_e,\mathbf u_J,\mathbf z_J,\boldsymbol\lambda_m,\boldsymbol\lambda_e),
\]

分别表示心肌 DCM 节点、心内膜 DCM 节点、ECM FEM 位移、黏弹内部变量以及细胞体积等约束乘子。

### 4.2 生长后的 ECM 构型

ECM 采用乘法分解：

\[
\mathbf F=\mathbf F_e\mathbf F_g,
\qquad J_e=\det\mathbf F_e.
\]

在一个心搏内 \(\mathbf F_g\)、\(\rho_c\)、\(\rho_{el}\) 和 \(\mathbf A_c\) 冻结。最小混合储能写为

\[
\psi_J=
\psi_{j}(\mathbf F_e,\mathbf z_J)
+U(J_e)
+\rho_c\,\widehat\psi_c(\mathbf F_e,\mathbf A_c)
+\rho_{el}\,\widehat\psi_{el}(\mathbf F_e).
\]

其中：

- \(\psi_j\)：正常 cardiac-jelly 的可恢复黏弹基质能；
- \(U(J_e)\)：体积约束；
- \(\widehat\psi_c\)：单位胶原密度的各向异性储能；
- \(\widehat\psi_{el}\)：单位弹性纤维密度的储能。

该加和式是最小受限混合物，不代表成分间相互作用已被充分描述。单相黏弹固体记为 `J0`；孔弹/双相或 HA 水化—自然体积模型记为竞争变体 `J1`，只有 Node 1 的可观测量能区分时才升级。

### 4.3 总储能与快时间功率账本

沿用已建立的同一点求积、同一牵引和转置映射界面算子：

\[
\Psi^f=
\Psi_m+\Psi_e+\Psi_J+\Psi_{mJ}+\Psi_{Je}.
\]

目标账本为

\[
\boxed{
\frac{d\Psi^f}{dt}+\mathcal D^f
=P_{act}+P_p+P_{wss}+P_{out}+R_{num}
}
\]

其中

\[
P_p=-\int_{\Gamma_L}p\,\mathbf n_L\cdot\mathbf v_e\,da,
\qquad
P_{wss}=\int_{\Gamma_L}\boldsymbol\tau_w\cdot\mathbf v_e\,da.
\]

若主动驱动仍采用 preferred-length 控制器，

\[
\Psi_a=\tfrac12 k_f(L_f-L_f^*)^2,
\qquad
P_{act}=\frac{\partial\Psi_a}{\partial L_f^*}\dot L_f^*
=-k_f(L_f-L_f^*)\dot L_f^*.
\]

\(R_{num}\) 是离散残差，不是物理耗散。周期状态必须分别报告 \(\Delta\Psi^f_{cycle}\)、物理耗散和 \(R_{num}\)。慢时间沉积和生长的化学供能不并入这条快时间账本；它需要在 Node 2 另建慢时间自由能/耗散边界。

## 5. 周期机械刺激向量

为避免把规定载荷、模型内部量和实验可观测量混为一谈，分别定义：

### 5.1 规定载荷

\[
\boldsymbol\ell=
(a_m(t),p(s,t),\boldsymbol\tau_w(s,t),\text{outer support}).
\]

### 5.2 周期响应统计量

\[
\mathcal M=
(\Delta\varepsilon_1,\overline W_J,t_{n,rms},\tau_{rms},OSI,\phi_{me},D_J^{cycle}).
\]

定义为

\[
\Delta\varepsilon_1
=\max_t\varepsilon_1-\min_t\varepsilon_1,
\]

\[
\overline W_J=\frac1{T_b}\int_0^{T_b}W_J(t)\,dt,
\qquad
t_{n,rms}=\left[\frac1{T_b}\int_0^{T_b}(\mathbf t_{Je}\cdot\mathbf n)^2dt\right]^{1/2},
\]

\[
\tau_{rms}=\left[\frac1{T_b}\int_0^{T_b}\|\boldsymbol\tau_w\|^2dt\right]^{1/2},
\]

\[
OSI=\frac12\left(1-
\frac{\left\|\int_0^{T_b}\boldsymbol\tau_wdt\right\|}
{\int_0^{T_b}\|\boldsymbol\tau_w\|dt}\right).
\]

\(\phi_{me}\) 是心肌激活与心内膜主应变一阶谐波相位差。它首先是诊断量，不默认是细胞直接传感器。

Node 1 必须分别检验应变、压力/法向牵引和剪切路径，不能以“低血流”同时代替三者。进入慢方程的最小刺激子集由 Human Gate 1 决定，不在 Node 0 预设全部有效。

## 6. 慢状态与最小演化方程

### 6.1 独立慢状态

\[
\mathbf y=(q_E,q_M,\rho_c,\rho_{el},\mathbf A_c,\mathbf F_g).
\]

- \(q_E\in[0,1]\)：心内膜由稳态内皮向纤维生成/间充质样状态的连续坐标；它不是单一标志物；
- \(q_M\in[0,1]\)：既有间充质来源细胞的活化状态；
- \(\rho_c,\rho_{el}\ge0\)：胶原和弹性纤维密度；
- \(\mathbf A_c\)：对称半正定、迹为 1 的胶原取向张量；
- \(\mathbf F_g\)：ECM 自然构型增长。

完整空间模型中的 EFE 厚度 \(h_{EFE}\) 应从重建几何和 \(\mathbf F_g\) 导出，不与 \(\mathbf F_g\) 同时作为独立状态重复计数。只有 Node 2 的局部降阶模型可暂用 \(h_{EFE}\) 替代 \(\mathbf F_g\)。

### 6.2 细胞状态

最小局部反应形式为

\[
\frac{dq_E}{dT}
=(1-q_E)k_E^+S_E(\mathcal M,c_T,c_B)-k_E^-q_E,
\]

\[
\frac{dq_M}{dT}
=(1-q_M)k_M^+S_M(\mathcal M,c_T,c_B)-k_M^-q_M,
\]

其中 \(c_T\) 和 \(c_B\) 分别表示 TGF-\(\beta\) 与 BMP 轴的外部状态，\(k_E^\pm,k_M^\pm\) 的单位为慢时间的倒数。\(S_E,S_M\in[0,1]\) 是待比较的响应函数；不默认刚度、应变或 WSS 对激活具有单调关系。

### 6.3 ECM 沉积、降解与取向

令

\[
q_F=w_Eq_E+w_Mq_M,
\qquad w_E,w_M\ge0.
\]

则最小密度方程为

\[
\frac{d\rho_c}{dT}
=k_cq_F\left(1-\frac{\rho_c}{\rho_{c,max}}\right)-d_c\rho_c,
\]

\[
\frac{d\rho_{el}}{dT}
=k_{el}q_F\left(1-\frac{\rho_{el}}{\rho_{el,max}}\right)-d_{el}\rho_{el}.
\]

以周期最大主拉伸方向 \(\mathbf n_1\) 为候选取向轴：

\[
\frac{D\mathbf A_c}{DT}
=k_Aq_F(\mathbf n_1\otimes\mathbf n_1-\mathbf A_c)
-d_A\left(\mathbf A_c-\frac13\mathbf I\right).
\]

最小各向异性生长律为

\[
\dot{\mathbf F}_g\mathbf F_g^{-1}
=g_n(q_F,\rho_c,\rho_{el})\,\mathbf n_B\otimes\mathbf n_B
+g_t(q_F,\rho_c,\rho_{el})
(\mathbf I-\mathbf n_B\otimes\mathbf n_B),
\]

其中 \(\mathbf n_B\) 是心内膜基底法向。若实验不能分别识别法向增厚和切向扩展，第一版只保留可识别的一个生长自由度。

## 7. 三个竞争细胞来源模型

| 变体 | 冻结方式 | 物理含义 | 预期空间签名（待检验） |
|---|---|---|---|
| `H1-Endo` | \(w_E>0,w_M=0\) | 心内膜纤维生成状态为主要来源 | 最早病灶与心内膜机械刺激热点相邻 |
| `H2-Mes` | \(w_E=0,w_M>0\) | 既有间充质/心外膜来源细胞为主要来源 | 病灶受迁入路径、细胞库存和扩增控制 |
| `H3-Mixed` | \(w_E>0,w_M>0\) | 心内膜触发与间充质放大共存 | 早期贴近心内膜，后期出现空间放大与来源混合 |

这些是模型变体，不是谱系结论。力学拟合本身无权裁决细胞来源；最终需要谱系追踪、时序标志物和空间 ECM 证据。

## 8. 反馈稳定性与允许的术语

将快映射写为 \(\mathcal M=\mathcal F(\mathbf y;\boldsymbol\ell)\)，慢反应写为 \(\dot{\mathbf y}=\mathcal R(\mathbf y,\mathcal M)\)。在候选稳态 \(\mathbf y^*\) 附近，闭环 Jacobian 为

\[
\mathbf J_{cl}
=\mathcal R_{\mathbf y}
+\mathcal R_{\mathcal M}\mathcal F_{\mathbf y}.
\]

若开环恢复块 \(\mathcal R_{\mathbf y}\) 可逆且稳定，可定义局部反馈增益

\[
\mathcal G
=\rho\!\left[-\mathcal R_{\mathbf y}^{-1}
\mathcal R_{\mathcal M}\mathcal F_{\mathbf y}\right],
\]

其中 \(\rho(\cdot)\) 为谱半径。\(\mathcal G\) 只作为候选反馈强度；不能仅凭 \(\mathcal G>1\) 就宣称发生分岔。正式术语门为：

- “状态变化”：有连续轨迹即可；
- “滞回”：同一控制参数下加载与卸载存在经收敛检验的路径差；
- “双稳态”：同一参数下存在两个稳定定常解及分隔不稳定解/吸引域；
- “机械记忆”：卸载后状态差超过预注册恢复时间，并排除数值迟滞；
- “临界转变”：必须有分岔或有限尺寸标度证据。

## 9. 核心无量纲量

| 符号 | 定义 | 竞争含义 |
|---|---|---|
| \(\epsilon_t\) | \(T_b/\tau_r\) | 快心搏与慢重塑分离 |
| \(De_J\) | \(\omega\tau_J\) | 心搏与心胶松弛竞争 |
| \(H_J\) | \(h_J/L\) | ECM 有限厚度 |
| \(\Pi_p\) | \(p_0/\mu_J\) | 腔压与 ECM 剪切尺度 |
| \(\Pi_\tau\) | \(\tau_0/\mu_J\) | WSS 与 ECM 剪切尺度 |
| \(\Lambda_\Gamma\) | \(K_\Gamma/K_J^{eff}\) | 界面滑移与 ECM 变形竞争 |
| \(R_c\) | \(k_c/(d_c\rho_{c,max})\) | 胶原产生与清除竞争 |
| \(R_{el}\) | \(k_{el}/(d_{el}\rho_{el,max})\) | 弹性纤维产生与清除竞争 |
| \(\Lambda_{enc}\) | \(E_{EFE}h_{EFE}/(E_mh_m)\) | 病理边界层与心肌层面内承载竞争 |
| \(\mathcal G\) | 闭环局部谱增益 | 候选反馈强度，不等同分岔结论 |

## 10. 必须恢复的极限与反事实

1. **健康极限**：\(q_E=q_M=\rho_c=\rho_{el}=0,\mathbf F_g=\mathbf I\)，恢复固定阶段三层快速力学；
2. **零重塑极限**：\(k_c=k_{el}=g_n=g_t=0\)，多次慢步不能累积病理层；
3. **完全清除极限**：产生关闭且 \(d_c,d_{el}>0\)，ECM 增量必须衰减；
4. **开环极限**：令 \(\mathcal F_{\mathbf y}=0\)，细胞状态仍可响应规定载荷，但 ECM 不反过来改变机械刺激；
5. **零流体载荷**：\(p=\boldsymbol\tau_w=0\)，只保留心肌—ECM 传力；
6. **零主动心肌**：\(P_{act}=0\)，只保留规定压力/WSS；
7. **零界面耦合**：\(K_{Je}\to0\)，ECM 不应无因向心内膜传递牵引；
8. **纯弹极限**：\(De_J\to0\) 或关闭黏弹支路，不得保留黏性相位滞后；
9. **冻结生长极限**：\(\mathbf F_g=\mathbf I\) 但允许 \(\rho_c,\rho_{el}\) 改变，用于区分“材料加硬”和“几何增厚”；
10. **来源消融**：分别令 \(w_E=0\) 或 \(w_M=0\)，检验 H1/H2/H3 的可辨识性。

## 11. 模型变量—实验观测映射

| 理论量 | 首选实验读数 | 证据边界 |
|---|---|---|
| \(\Delta\varepsilon_1,\phi_{me}\) | 高速 SPIM/OCT 的心内膜与心肌表面位移 | 需要同一心搏相位配准 |
| \(p,\tau_{rms},OSI\) | 红细胞轨迹 + 单向 CFD/降阶流动反演 | 反演不等同直接测量，第一版不是 FSI |
| \(q_E\) | 心内膜谱系 + 内皮标志下降 + 间充质标志上升 | 单个标志物不足以证明 EndMT |
| \(q_M\) | 间充质/心外膜来源谱系 + 活化标志 | 力学模拟不能代替谱系追踪 |
| \(\rho_c,\mathbf A_c\) | 胶原染色、SHG、取向分析 | 需区分心内膜下与心肌间质 |
| \(\rho_{el}\) | 弹性纤维特异染色/成分测量 | 只有胶原增加不足以命名 EFE |
| \(h_{EFE}\) | 三维组织学或共聚焦心内膜下层厚度 | 必须排除水肿和正常 cardiac jelly |
| \(\Lambda_{enc}\) 的功能后果 | 缩短率、舒张容积、相位和顺应性 | 需要与年龄/发育阶段匹配对照 |

## 12. Node 1 预注册接口

Node 1 只研究慢状态冻结时的快速映射 \(\mathcal F_{beat}\) 和周期后处理 \(\mathcal P_{cycle}\)。其最小任务为：

1. 使用一个主动心肌细胞或最小心肌 patch、有限厚度三维 ECM 和一个心内膜细胞/patch；
2. 依次改变主动缩短、\(De_J\)、\(H_J\)、\(\Pi_p\)、\(\Pi_\tau\) 和双界面顺应性；
3. 通过“改变周期”和“改变松弛时间”两条路径达到相同 \(De_J\)，检验数据塌缩；
4. 分别执行零压力、零 WSS、零主动收缩和零界面耦合反事实；
5. 比较 `J0` 单相黏弹与一个最小 `J1` 孔弹/水化竞争变体；
6. 输出 \(\mathcal M\) 的空间场、周期波形、相位、能量账本和可识别性；
7. 不启动 \(q_E,q_M,\rho_c,\rho_{el},\mathbf F_g\) 的慢时间推进。

Node 1 数值执行的前置硬门：X1-K 必须通过。门未通过前只允许解析退化、制造解和不依赖长期轨迹的接口检查。正式收敛阈值、参数范围和网格族须在单独的 Node 1 合同中预注册。

## 13. Falsifiers

以下任一结果要求收窄或否决本理论路线：

1. 快时间统计量在网格、时间步或界面主从选择改变后不收敛；
2. 只有加入无法独立识别的多个黏性参数才能匹配相位；
3. 斑马鱼病变起始位置与所有预注册机械刺激均无持出预测关联；
4. H1/H2/H3 在可获得的时空读数上完全等价，却宣称唯一细胞来源；
5. EFE 样增厚只能通过预设局部沉积位置产生，不能由模型规则生成；
6. 加载—卸载差随慢时间步缩小而消失，说明“记忆”只是数值迟滞；
7. 病理组织缺少心内膜下胶原与弹性纤维共同增厚，无法通过 EFE 命名门；
8. Node 3/4 的空间结果可由 Node 2 局部模型简单叠加，DCM 的形态、迁移和接触自由度没有预测增益。

## 14. Figure 1 结构与图注边界

Figure 1 v01 采用四个面板：

- **A**：心腔—心内膜 DCM—cardiac-jelly/fibrous ECM FEM—主动心肌 DCM 的三层剖面及压力、WSS、主动收缩；
- **B**：快心搏求解、周期统计量 \(\mathcal M\) 和慢重塑更新的双时间尺度循环；
- **C**：`H1-Endo`、`H2-Mes`、`H3-Mixed` 三个细胞来源竞争模型；
- **D**：健康、可逆重塑、候选持续 EFE 三种状态以及 \(\Lambda_{enc}\) 功能反馈。

强制图注：

> 理论结构示意，并非模拟或实验结果。压力和 WSS 为规定载荷；细胞来源、状态跃迁、双稳态、机械记忆及 EFE 疾病因果均尚未验证。

## 15. Human Gate 0

进入 Node 1 前，人类终审需决定：

1. 是否接受三层几何、法向和压力/WSS 边界；
2. 是否接受把 \(h_{EFE}\) 作为派生量而非完整模型独立状态；
3. 是否保留 H1/H2/H3 三个细胞来源变体；
4. 是否接受先用规定压力/WSS、暂不开发双向 FSI；
5. 是否接受 Node 1 只求健康/冻结慢状态下的快速机械刺激映射；
6. Figure 1 应保留、修改、替换还是停止。

未经 Human Gate 0，不得启动 Node 1。

## 参考依据

1. `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md`：既有三层快时间功率一致接口。
2. Xu X. et al. *Endocardial Fibroelastosis is Caused by Aberrant Endothelial to Mesenchymal Transition*. Circ Res. 2015.
3. Zhang H. et al. *Fibroblasts in an endocardial fibroelastosis disease model mainly originate from mesenchymal derivatives of epicardium*. Cell Research. 2017.
4. Vorisek C. et al. *Mechanical strain triggers endothelial-to-mesenchymal transition of the endocardium in the immature heart*. Pediatric Research. 2022.
