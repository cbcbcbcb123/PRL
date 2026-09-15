---
theory_id: THEORY-EFE-NODE1-N1R-READINESS-V01
status: accepted_at_human_stage_review
scope: analytical_reductions_manufactured_tests_and_numerical_freeze
evidence_level: analytical_readiness_not_simulation_or_efe_mechanism_evidence
approved_contract: project_control/efe_node1_fast_trilayer_mechanics_contract_v01.md
approval_decision: project_control/efe_node1_approval_decision_v01.md
blocked_by: project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
human_decision: project_control/efe_node1_n1r_acceptance_decision_v01.md
---

# EFE Node 1 N1-R v01：解析与数值准备包

## 1. 结论先行

N1-R 已把 Node 1 的最小力学问题冻结为一个慢状态不更新、相位可追踪、功率可闭合的三维 `DCM–FEM–DCM` 单元。现有 T1 资产足以复用界面、单侧 ECM、体积约束和黏弹内部变量的开发基础，但没有任何既有结果足以替代完整三层的收敛与边界检验。

本包得到一个可直接用于校验三维求解器的小幅传递矩阵，并给出以下关键物理判据：

1. 黏弹 `J0` 的频率响应只有在模量比、几何和边界同时固定时才应按 `De_J` 塌缩；
2. 主动收缩能否在心内膜产生牵引，不只取决于 ECM 刚度，还取决于心内膜和心肌周围组织是否提供反力路径；
3. 孔弹/水化 `J1` 不能脱离排液边界单独定义，必须同时报告封闭与可排液极限；
4. 细胞内在黏性和界面黏性在主模型中先置零，避免把多种不可辨识的相位源同时加入；
5. 正式三层动态计算仍被 X1-K 阻断。

以上是解析准备结论，不是模拟结果、材料标定或 EFE 因果证据。

## 2. 既有资产复用与排除矩阵

| 资产 | 复用内容 | 证据等级 | 正式排除项 |
|---|---|---|---|
| `t0_dcm_fem_dcm_energy_interface_v01` | 同点求积、转置映射、双界面功率符号和一维端口极限 | 理论接口 | 尚未证明三层数值稳定或生理有效 |
| `t1_dcm_fem_fixed_topology_*` | 主动 DCM、单侧材料 tether、镜像极性、体积/KKT/界面残差测试 | 代码与回归起点 | 不作为心内膜层、动态相位或 EFE 证据 |
| `t1_1r_ecm_thickness_convergence_*` | `Y4=(5,4,4)` 作为新网格族最低起点 | 单侧准静态局部证据 | 不是新三层几何的收敛证明或严格 GCI |
| `t1_1r_y4_3d_field_figure_*` | 三维四面体场重建和场量导出方法 | 可视化/后处理起点 | 归一化场不能称为实验标定应力 |
| `t1_2_ecm_geometry_density_*` | 面积、厚度与边界敏感性提示 | 反例与风险证据 | `M15` 能量差 11.33% 失败，不能称全部场网格无关 |
| `node1_viscoelastic_cell_ecm_cycle_*` | SLS 内变量、精确松弛和非负耗散路径 | 冒烟测试 | 6 四面体、8 时步；排除全部相位、热点和材料机制主张 |
| `X1-K v10` | 当前真实 remesh/material-transfer 首失败 | 冻结失败证据 | 不得解释为 X1-K、R1、C1 或 F1 通过 |

复用原则：复用实现和测试思想，不复用超出原门限的结论。旧文件不覆盖、不重命名、不删除。

## 3. 坐标、符号与无量纲单位

### 3.1 坐标

- `x`：心肌纤维轴，单位向量 \(\mathbf f=\mathbf e_x\)；
- `y`：由心肌指向心腔，壁面法向 \(\mathbf n_B=\mathbf e_y\)；
- `z`：局部切向横向；
- 心内膜指向心腔的外法向为 \(\mathbf n_L=+\mathbf e_y\)；
- 正压力牵引为 \(-p\mathbf n_L\)；
- 正 WSS 基线方向为 \(+\mathbf e_x\)。

### 3.2 基准量

取心肌参考纤维长度 \(L_0\)、健康 ECM 平衡剪切模量 \(\mu_0\) 和心搏周期 \(T_b\) 为基准：

| 物理量 | 基准 |
|---|---|
| 长度/位移 | \(L_0\) |
| 时间 | \(T_b\) |
| 应力/压力/牵引 | \(\mu_0\) |
| 力 | \(\mu_0L_0^2\) |
| 能量 | \(\mu_0L_0^3\) |
| 速度 | \(L_0/T_b\) |
| 功率 | \(\mu_0L_0^3/T_b\) |
| 面界面刚度 | \(\mu_0/L_0\) |
| 渗透扩散率 | \(L_0^2/T_b\) |

当前所有参数保持无量纲。只有未来独立标定合同才能把数值映射为 `Pa、µm、s`，不得在绘图图例中暗示生理单位。

## 4. 小幅法向传递理论

### 4.1 两自由度退化

在长波、小幅和固定拓扑极限，将心肌—ECM 与 ECM—心内膜的法向运动压缩为界面位移 \(u_m,u_e\)。令：

- \(u_a\)：主动心肌的有符号自由位移；正负号由上述 `y` 方向约定决定；
- \(k_m\)：心肌及周围组织对 \(u_m\) 的等效法向刚度；
- \(k_e\)：心内膜及其边缘约束对 \(u_e\) 的等效法向刚度；
- \(k_J^*(\omega)=A_JM_J^*(\omega)/h_J\)：ECM 复法向刚度；
- \(F_p=-A_L\widehat p\)：规定腔压的复力幅值。

谐波平衡为

\[
\begin{bmatrix}
k_m+k_J^* & -k_J^*\\
-k_J^* & k_e+k_J^*
\end{bmatrix}
\begin{bmatrix}\widehat u_m\\\widehat u_e\end{bmatrix}
=
\begin{bmatrix}k_m\widehat u_a\\\widehat F_p\end{bmatrix}.
\]

记

\[
\Delta^*=k_mk_e+k_J^*(k_m+k_e),
\]

则

\[
\widehat u_m
=\frac{k_m(k_e+k_J^*)\widehat u_a+k_J^*\widehat F_p}{\Delta^*},
\]

\[
\widehat u_e
=\frac{k_mk_J^*\widehat u_a+(k_m+k_J^*)\widehat F_p}{\Delta^*}.
\]

ECM 厚度变化和传递力为

\[
\widehat\delta_J=\widehat u_e-\widehat u_m
=\frac{k_m(\widehat F_p-k_e\widehat u_a)}{\Delta^*},
\qquad
\widehat F_J=k_J^*\widehat\delta_J.
\]

这给出法向输入 \((u_a,p)\) 到位移、间距和牵引的显式传递函数。三维有限变形结果必须在小幅、均匀极限恢复这些表达式。

### 4.2 必须恢复的极限

1. \(k_J^*\to0\)：\(u_m\to u_a\)、\(u_e\to F_p/k_e\)、\(F_J\to0\)；
2. \(k_J^*\to\infty\)：\(u_m-u_e\to0\)，共同位移趋于
   \((k_mu_a+F_p)/(k_m+k_e)\)；
3. \(k_e\to0,F_p=0\)：心内膜自由随动，\(\delta_J\to0\)。因此“主动收缩必然压缩 ECM”并不成立，必须有反力路径；
4. \(u_a=0,F_p\ne0\)：压力仍可通过 ECM 向心肌和周围组织传力；
5. 在全部刚度为实数且无耗散时，相位只能为 `0` 或 `π`；出现连续相位滞后必须来自材料/界面/细胞耗散或惯性，而不能来自时间索引误差。

### 4.3 线性传递矩阵

定义

\[
\widehat{\mathbf x}_n=(\widehat u_m,\widehat u_e)^T,
\quad
\widehat{\mathbf q}_n=(\widehat u_a,\widehat p)^T,
\]

\[
\mathbf K_n^*=
\begin{bmatrix}k_m+k_J^*&-k_J^*\\-k_J^*&k_e+k_J^*\end{bmatrix},
\quad
\mathbf B_n=
\begin{bmatrix}k_m&0\\0&-A_L\end{bmatrix}.
\]

则 \(\widehat{\mathbf x}_n=(\mathbf K_n^*)^{-1}\mathbf B_n\widehat{\mathbf q}_n\)。任意线性读数由

\[
\widehat{\mathbf y}_n
=\mathbf C_n(\mathbf K_n^*)^{-1}\mathbf B_n\widehat{\mathbf q}_n
\mathbf D_n\widehat{\mathbf q}_n
\]

得到。该矩阵是三维代码的独立 benchmark，不用于替代三维场。

## 5. 小幅切向传递理论

沿纤维方向，将 \(k_m,k_e,k_J^*\) 分别替换为切向等效量 \(k_m^t,k_e^t,k_J^{t*}\)，输入为 \(F_\tau=A_L\widehat\tau_w\)。在主模型中不施加主动切向位移，因此

\[
\begin{bmatrix}
k_m^t+k_J^{t*} & -k_J^{t*}\\
-k_J^{t*} & k_e^t+k_J^{t*}
\end{bmatrix}
\begin{bmatrix}\widehat v_m\\\widehat v_e\end{bmatrix}
=
\begin{bmatrix}0\\A_L\widehat\tau_w\end{bmatrix}.
\]

法向与切向在小幅一维极限中解耦；三维有限变形产生的交叉响应必须随载荷幅值趋零而消失，否则优先怀疑坐标、法向或界面映射错误。

## 6. ECM 竞争模型与极限

### 6.1 `J0`：单相标准线性固体

\[
\mu_J^*(\omega)
=\mu_{eq}+\mu_{ve}\frac{iDe_J}{1+iDe_J},
\qquad De_J=\omega\tau_J.
\]

因此

\[
\mu'_J=\mu_{eq}+\mu_{ve}\frac{De_J^2}{1+De_J^2},
\qquad
\mu''_J=\mu_{ve}\frac{De_J}{1+De_J^2}.
\]

- `De_J→0`：恢复平衡模量 \(\mu_{eq}\)，损耗趋零；
- `De_J→∞`：恢复瞬时模量 \(\mu_{eq}+\mu_{ve}\)，损耗趋零；
- `De_J=1`：黏弹支路损耗达到最大；
- 同 `De_J` 数据塌缩还要求 \(\mu_{ve}/\mu_{eq}\)、几何、边界和归一化输入一致，仅匹配 `De_J` 不足以保证塌缩。

主模型中细胞物理黏性和界面黏性先置零。数值线搜索、松弛或 continuation 只能记为算法项，不能计入 \(\mathcal D_J\)。

### 6.2 `J1`：最小孔弹/水化竞争模型

采用线性 Biot 型最小形式作为识别对照：

\[
\boldsymbol\sigma=\mathbb C:\boldsymbol\varepsilon-\alpha p_f\mathbf I,
\]

\[
S\dot p_f+\alpha\,\nabla\!\cdot\dot{\mathbf u}
-\nabla\!\cdot\left(\frac{\kappa}{\eta_f}\nabla p_f\right)=0.
\]

定义 \(D_p=\kappa/(\eta_fS_{eff})\) 与

\[
De_p=\omega h_J^2/D_p.
\]

排液边界不是技术细节，而是模型组成：

- 心肌侧基线：无通量；
- 心内膜侧：以外向 Darcy 通量为正的 Robin 交换
  \(\mathbf q\cdot\mathbf n=L_p p_f\)；该条件表示跨心内膜的等效排液能力，不把心内膜细胞从三层几何中删除；
- `J1-sealed`：\(L_p=0\)；
- `J1-drained`：\(L_p\to\infty\)；
- 横向边界基线无通量，扩大横向范围作为边界敏感性检查。

正式比较只使用 `sealed/drained` 两个极限夹逼，不增加连续排液参数扫描。若实验不能约束排液边界，Node 1 只能报告材料—边界组合的可辨识性。

## 7. 三层参考几何冻结

### 7.1 基线几何 `G0`

- 心肌 DCM：复用现有圆滑封闭参考网格，`162` 顶点、`320` 三角面；其无量纲包围盒跨度为 `1.00 × 0.60 × 0.56`，纤维沿 `x`；它不是长方体细胞；
- ECM：位于心肌的心腔侧，参考厚度 \(H_J=0.30L_0\)，基线横向足迹覆盖心肌 `x–z` 投影；
- 心内膜 DCM：使用同拓扑的扁平封闭细胞，包围盒跨度冻结为 `1.00 × 0.20 × 0.56`，ECM-facing 面法向约为 `-y`，lumen-facing 面法向约为 `+y`；
- 心肌 ECM-facing 面选取参考法向 \(n_y>0.90\) 的三角面；
- 心内膜 ECM-facing 面选取 \(n_y<-0.90\) 的三角面；
- 心内膜腔面载荷区选取 \(n_y>0.90\) 的三角面；
- 两个材料界面均保存参考相对向量 \(\mathbf g_0\)，实际弹性间隙为 \(\bar{\mathbf g}=\mathbf y_{DCM}-\mathbf y_{FEM}-\mathbf g_0\)。因此参考连接长度不是 jelly-free 空隙，也不得计入层厚。

### 7.2 周围组织与规范约束

- 心肌非 ECM-facing 表面通过弹性支承连接参考周围组织；
- 基线支承刚度与 ECM 有效法向刚度比为 `1`，稳健性变体为 `0.1` 和 `10`；
- 刚体平移/旋转的规范约束只消除零模，不得产生或吸收物理功；
- 支承反力和功率单列为 \(P_{sup}\)；
- ECM 横向足迹另设 `1.5×` 扩大变体，检验局部边界控制。

### 7.3 力学自由度冻结

- 心肌：分布式 preferred-length 主动变形；
- 心内膜：被动面积、弯曲、网格质量与精确体积约束；
- 两类细胞：体积误差门 `<=1e-8`，不施加硬表面积守恒；
- ECM：有限变形、近不可压缩；
- 主基线：无细胞物理 drag、无界面黏性、无惯性；相位先只来自 ECM；
- 不执行 split/swap/merge，直至 X1-K 明确通过；通过后是否在 Node 1 正式基线启用重网格仍需保留 on/off 对照。

## 8. 规定载荷波形冻结

令 \(\theta=(t/T_b)\bmod1\)，并定义

\[
w(\theta)=\frac12[1-\cos(2\pi\theta)].
\]

### 8.1 主动收缩

\[
a_m(\theta)=A_mw(\theta),
\]

基线 \(A_m=0.20\)，峰值在 \(\theta=0.5\)。该值是无量纲开发基线，不是体内肌节缩短率。

### 8.2 腔压

\[
p(\theta)=p_{min}+p_{amp}w(\theta-\phi_p).
\]

机制筛选先取 \(p_{min}=0\)、\(\phi_p=0\)，再取 \(\phi_p\in\{-0.25,0,0.25\}\) 周期。压力始终通过 \(-p\mathbf n_L\) 加载。

### 8.3 WSS

反转基线为

\[
\boldsymbol\tau_w(\theta)
=\tau_{amp}\cos[2\pi(\theta-1/2-\phi_\tau)]\mathbf e_x,
\]

其 \(\phi_\tau=0\) 时与主动峰同相，且理想 OSI 为 `0.5`。非反转对照使用 \(\tau_{amp}w(\theta-\phi_\tau)\mathbf e_x\)。

波形文件必须保存解析式、采样值、相位原点和单位；不得只保存图片。

## 9. 空间、时间和容差族冻结

### 9.1 ECM 网格族

对同一物理几何使用结构化六四面体分解：

| 级别 | `(nx, ny, nz)` | 节点数 | 四面体数 | 用途 |
|---|---:|---:|---:|---|
| `E0` | `(5,4,4)` | `150` | `480` | 继承 Y4 的最低起点/粗网格 |
| `E1` | `(8,6,6)` | `441` | `1728` | 正式基线 |
| `E2` | `(10,8,8)` | `891` | `3840` | 细网格 |

`ny` 为厚度方向。若 `E1→E2` 不通过合同门限，追加 `E3`，不得删除敏感输出或把 `E0` 重新称为正式基线。

### 9.2 DCM 表面族

| 级别 | 每个细胞顶点 | 每个细胞三角面 | 用途 |
|---|---:|---:|---|
| `D0` | `162` | `320` | 粗/开发起点 |
| `D1` | `642` | `1280` | 正式基线 |
| `D2` | `2562` | `5120` | 条件细化级 |

`D2` 仅在 `D0→D1` 未达到细胞全局读数 `1%` 门或界面 `10%` 门时启用。不同级别必须重建材料点，而不是用节点编号硬拷贝。

### 9.3 时间与周期族

- 每周期 `16/32/64` 步；旧 `8` 步 pilot 永久排除正式证据；
- 每个材料工况至少运行到连续两个周期关键波形归一化 `L2<=1e-3`；
- 先以 `32` 步寻找周期稳态，再用同一初始周期态完成 `16/32/64` 时间收敛；
- 峰值相位用统一周期插值获得，不用离散索引差代替相位；
- 耦合容差比较 `1e-4` 与 `3e-5`，正式 KKT 门保持 `1e-5`。

## 10. 制造解与接口检查清单

| ID | 检查 | 构造 | 必须结果 |
|---|---|---|---|
| `M0` | 零态 | 零载荷、参考构型、零内变量 | 零牵引、零功率、零耗散、仅允许常数参考能 |
| `M1` | 刚体客观性 | DCM/FEM/载荷方向共同平移与旋转 | 能量和标量不变，向量协变，界面残差不增大 |
| `M2` | 均匀仿射 patch | 对 ECM 施加常 \(\mathbf F\)，DCM 界面点使用同一映射 | \(\bar{\mathbf g}=0\)，无伪界面力，FEM 反力等于解析牵引 |
| `M3` | 单求积点作用反作用 | 任意牵引、同点两侧插值、形函数分片统一 | 合力 `<=1e-10`；同点合矩 `<=1e-10` |
| `M4` | 能量方向导数 | 随机许可扰动中心差分 | 相对误差 `<=1e-5` |
| `M5` | 一维法向端口 | 均匀层、小幅谐波 | 恢复第 4 节传递矩阵，幅值差 `<=1%`、相位差 `<=0.01` 周期 |
| `M6` | 一维切向端口 | 均匀剪切、小幅谐波 | 恢复第 5 节，法向交叉响应随幅值趋零 |
| `M7` | 双界面整体平衡 | 两个界面给定相反牵引 | 内部界面力整体抵消，ECM 合力/合矩闭合 |
| `M8` | 压力/WSS 面积分 | 平面腔面均匀载荷 | 总力和关于参考点的力矩等于解析面积积分 |
| `M9` | SLS 本构 | 松弛阶跃与单频谐波 | 恢复 \(\mu',\mu''\)，耗散非负，`De→0/∞` 极限正确 |
| `M10` | 孔弹质量守恒 | sealed/drained 一维层 | sealed 总液量守恒；drained 通量等于液量变化；时间尺度按 \(h^2/D_p\) 缩放 |
| `M11` | 周期功率 | 达到周期态的任一小幅工况 | 输入功=储能变化+物理耗散+数值残差；残差 `<=1%` 正输入功 |

这些检查是未来实施规格。本 N1-R 未运行三层求解，因此不把表格写成“已通过”。

## 11. 结果目录与 schema 冻结

正式结果使用项目内版本化目录：

`results/hybrid/efe_node1_fast_trilayer_vNN_YYYYMMDD/<case_id>/`

每个 case 至少包含：

### 11.1 `metadata.json`

- `case_id、contract_id、execution_id、code_commit`；
- DCM/FEM 网格级别及完整节点/单元计数；
- 材料模型 `J0/J1-sealed/J1-drained`；
- 坐标、法向、无量纲基准和波形版本；
- 求解器、容差、时间步、周期数、成功/失败状态；
- 是否启用重网格及 X1-K 证据引用。

### 11.2 `cycle_timeseries.csv`

固定列至少包括：

`case_id, cycle, step, t_over_T, activation, pressure, wss_x,`
`myocyte_volume_ratio, endocardial_volume_ratio, myocyte_area_ratio, endocardial_area_ratio,`
`minimum_cell_face_area_ratio, minimum_ecm_J, maximum_ecm_J, minimum_gap,`
`kkt_residual, pair_force_residual_mJ, pair_moment_residual_mJ,`
`pair_force_residual_Je, pair_moment_residual_Je,`
`active_power, pressure_power, wss_power, support_power,`
`stored_cell, stored_ecm, stored_interface, ecm_dissipation, interface_dissipation,`
`numerical_power_residual, normal_traction_rms, shear_traction_rms, axial_strain_p95`。

### 11.3 空间场

- `state_reference.npz` 与预注册相位 `state_phase_*.npz`；
- 保存参考/当前节点、连接、材料点身份、位移、`F/J`、应力、储能、耗散、孔压和界面牵引；
- 可选 `VTU/VTP` 只作查看副本，`NPZ/CSV/JSON` 为可复算源；
- Figure 不得成为唯一数据源。

### 11.4 `cycle_metrics.csv`

每个候选统计量保存 `median、p95、maximum、phase、hotspot_centroid、cycle_integral`，另保存时间/空间/边界差异和是否通过相应门。

### 11.5 失败包

任何首失败必须保存 `failure.json`、最后有效状态、失败工况参数和 stdout/stderr 日志；失败 case 不得被成功 case 静默覆盖。

## 12. N1-R 对 Figure 2 的约束

N1-R 不生成 Figure 2 定量结果。未来 Panel A–C 的首个阶段包必须先回答：

1. 三层几何和载荷区是否与本冻结一致；
2. 3D 变形是否来自实际求解而非示意变形；
3. 压力、WSS、主动功与支承功是否分开；
4. 两个界面作用—反作用是否闭合；
5. ECM 应力、耗散和心内膜牵引是否至少达到 `E1/D1/32-step` 基线，并有向 `E2/64-step` 的收敛证据。

在上述阶段图被人类接受前，不进入大规模无量纲扫描。

## 13. 当前 blocker 与下一门

`X1-K v10` 仍为 `failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind`，且 `R1=false、C1/F1 not_executed、downstream_authorized=false`。因此：

- N1-R 可以提交阶段审阅；
- N1-1 正式三层基线不得启动；
- 旧固定拓扑结果不能绕过该门；
- 下一项可申请的人类授权是单独起草/执行 X1-K 修复合同，而不是直接运行 Figure 2。

## 14. Evidence boundary

本文件只允许声称 Node 1 的科学问题、解析极限、材料竞争、几何、波形、网格族、制造解和结果 schema 已预注册。不得声称：

- 三层模型已经运行或稳定；
- cardiac jelly 的真实材料参数已知；
- 内膜机械刺激已经确定；
- `J0` 或 `J1` 已被选择；
- EFE 的阈值、细胞来源、慢反馈或疾病机制已经得到支持。
