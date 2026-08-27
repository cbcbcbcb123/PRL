---
contract_id: EFE-NODE1-FAST-TRILAYER-MECHANICS-CONTRACT-V01
status: approved
planner: codex_primary_single_agent
requested_by: human_final_reviewer
drafted_at: 2026-08-13
lifecycle_state: n1_1_execution
approved_by: human_final_reviewer
approved_at: 2026-08-13
readiness_execution_authorized: true
formal_dynamic_execution_authorized: true
n1_1_execution_authorized: true
n1_2_to_n1_5_execution_authorized: false
n1_1_authorization_decision: project_control/efe_node1_n1_1_authorization_decision_v01.md
n1_r_result: docs/theory/efe_node1_n1r_readiness_theory_v01.md
n1_r_execution: project_control/efe_node1_n1r_execution_log_v01.md
n1_r_human_decision: project_control/efe_node1_n1r_acceptance_decision_v01.md
upstream:
  - project_control/efe_node0_acceptance_decision_v01.md
  - docs/theory/efe_node0_minimal_theory_contract_v01.md
  - docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md
approval_decision: project_control/efe_node1_approval_decision_v01.md
governing_constraints:
  - project_control/external_scientific_review_constraints_v01.md
  - project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
evidence_reuse:
  - project_control/t1_dcm_fem_fixed_topology_contract_v01.md
  - project_control/t1_1r_ecm_thickness_convergence_execution_v01.md
  - project_control/t1_2_ecm_geometry_density_execution_v01.md
  - project_control/node1_viscoelastic_cell_ecm_cycle_execution_v01.md
---

# EFE Node 1 v01：健康三层单元的快速心搏力学合同（草案）

## 1. Contract decision

本合同规划一个慢状态完全冻结的三维 `DCM–FEM–DCM` 快速心搏模型：主动心肌 DCM 通过有限厚度 cardiac-jelly ECM FEM 向被动心内膜 DCM 传递变形、法向牵引、切向牵引、相位与能量；心内膜腔面同时承受规定的压力和 WSS。

本 Node 只回答“健康/未重塑三层壁如何过滤和组合快速机械输入”。它不模拟 ECM 沉积、EndMT、EFE 增厚或发育，也不把任何机械量预先宣布为 EFE 的生物学触发器。

允许形成的最高层级主张是：

> 在冻结慢状态和规定腔内载荷下，健康三层单元可被描述为一个依赖频率、厚度、界面顺应性与材料时间尺度的机械传递器；不同载荷通道是否具有可区分的空间—相位签名，必须由预注册的收敛、反事实和材料竞争检验决定。

## 2. Goal

1. 建立首个包含主动心肌、三维有限厚度 cardiac jelly 和被动心内膜的功率一致快速心搏单元；
2. 给出从输入谐波
   \(\mathbf u=(a_m,p,\boldsymbol\tau_w)\)
   到心内膜/ECM 周期读数 \(\mathcal M(s)\) 的传递映射；
3. 分离主动收缩、腔压和 WSS 的主效应与有限变形交互效应；
4. 检验黏弹 cardiac jelly 的 `De_J` 数据塌缩，并与最小孔弹/水化竞争模型比较；
5. 只把经数值收敛、边界稳健、材料可区分且未来可观测的机械读数送到 Human Gate 1，由人类终审决定 Node 2 的最小刺激子集。

## 3. Inputs and evidence reuse

### 3.1 冻结输入

- Node 0 的层次、法向、符号、快—慢时间分离和功率端口；
- T0 已审阅的同一点求积、旋转一致界面映射与作用—反作用账本；
- 当前三维主动心肌 DCM、有限变形四面体 FEM ECM、材料 tether 和精确体积约束；
- 规定的腔压与 WSS 波形；当前不称为双向 FSI；
- 慢状态固定为健康参考态：
  \(q_E=q_M=\rho_c=\rho_{el}=0\)，\(\mathbf F_g=\mathbf I\)。

### 3.2 既有结果的证据等级

| 既有资产 | 本 Node 的用途 | 不允许的升级 |
|---|---|---|
| T1 固定拓扑镜像 benchmark | 回归检查界面极性、力矩和功率符号 | 不能当作完整三层、动态或 EFE 证据 |
| T1.1R `Y4`、480 四面体 | 新 ECM 网格族的最低起始厚度分辨率 | 不是新三层几何的收敛证明，也不是严格 GCI |
| T1.2 几何/网格扫描 | 提醒局部场对面积、厚度和网格敏感 | `M15` 能量差 11.33% 的失败必须保留，不能称全部场网格无关 |
| 旧黏弹单周期 pilot | 只证明代码路径可连通、材料记忆和耗散接口存在 | 6 四面体、8 时步结果不得用于相位、场分布或材料机制主张 |
| X1-K v10 | 冻结的数值硬门现状 | 仍为失败；不得声称 R1/X1-K、remeshing 或长轨迹稳定已通过 |

旧结果只减少重复开发，不替代本 Node 的三层收敛、边界和材料竞争证据。

## 4. Minimum model

### 4.1 三维几何

基线单元沿腔面法向依次为：

`lumen / passive endocardial DCM / 3D cardiac-jelly FEM / active myocardial DCM / elastic surroundings`

- 心肌：一个封闭三维主动 DCM 细胞；只有朝向 ECM 的一侧建立材料界面；
- 心内膜：一个封闭三维被动 DCM 细胞；基底侧与 ECM 接触，腔面侧承受规定压力/WSS；
- ECM：连接两个活界面的连续四面体层；不得沿用旧单侧模型的“ECM 远端整面固定”作为三层基线；
- 周围组织：在非界面心肌面施加可追踪的弹性支承，用于表示局部心壁邻域并平衡压力/WSS 的净力；刚体规范约束与物理支承必须分开记录；
- 基线为一个细胞尺度局部单元，不宣称代表连续心肌层或完整心室壁。细胞层与器官几何留给 Node 3/4。

两种边界稳健性变体必须保留：

1. 扩大 ECM 横向范围但保持局部几何和材料不变；
2. 改变周围组织支承刚度一个数量级范围。

若候选刺激量随上述变体改变超过预注册门限，它不得进入 Node 2。

### 4.2 细胞力学

- 心肌主动收缩使用内部 preferred-length/active-strain 变形加载，不使用外部轴向力强迫；
- 心肌与心内膜细胞体积在每个快时间求解中保持到等式约束精度；
- 细胞表面积采用有限弹性能，不施加硬面积守恒；面积变化作为诊断量报告；
- 心内膜在 Node 1 中是被动层，不含 EndMT、增殖、迁移或 ECM 分泌；
- 主动收缩、压力和 WSS 的输入功必须分别记录。

### 4.3 ECM 竞争本构

主模型 `J0` 为有限应变标准线性固体型单相黏弹材料：

\[
\mu_J^*(\omega)
=\mu_{eq}+\mu_{ve}\frac{i\omega\tau_J}{1+i\omega\tau_J},
\qquad De_J=\omega\tau_J.
\]

近似不可压缩通过有限体积模量实现，而不是点态厚度不变。黏弹内变量必须满足客观性、非负耗散和周期稳态。

竞争模型 `J1` 为最小孔弹/水化模型，至少具有压力/含液量自由度和厚度相关扩散时间

\[
\tau_p\sim h_J^2/D_p,
\qquad De_p=\omega h_J^2/D_p.
\]

`J0` 与 `J1` 必须在一个参考频率匹配平衡刚度，并尽可能匹配储能和损耗后再比较；禁止用明显不等刚度的参数制造“机制差异”。若现有观测量不能区分两者，正式结论必须是“机制等价/当前不可辨识”。

### 4.4 载荷

- 主动输入：平滑周期激活 \(a_m(t)\)，基线峰值沿用开发期 `0.20`，但它是模型基线，不等于 20% 真实肌节应变或生理标定；
- 压力输入：心内膜腔面规定 \(p(t)\)，方向与 Node 0 的 `-p n_L` 一致；
- 剪切输入：腔面规定切向 \(\boldsymbol\tau_w(t)\)，可改变幅值、方向反转和相对相位；
- 所有波形都必须保存解析定义、离散采样和相位原点；
- 不使用“低血流”同时代替低压力、低 WSS 和低壁变形。

### 4.5 界面与功率账本

两个界面分别为 \(\Gamma_{mJ}\) 与 \(\Gamma_{Je}\)。基线采用材料粘附/切向顺应界面，并设置无耦合、强粘附和有限滑移反事实。

周期功率账本为

\[
P_{act}+P_p+P_{wss}+P_{sup}
=\frac{d}{dt}(\Psi_m+\Psi_e+\Psi_J)
+\mathcal D_J+\mathcal D_\Gamma+R_{num}.
\]

界面内部作用—反作用功在整体账本中必须相消；支承功 `P_sup` 必须单列，不能藏在数值残差中。`R_num` 只表示离散/求解残差，不是物理耗散。

## 5. Dimensionless control space

| 控制量 | 定义/实现 | 预注册筛选水平 |
|---|---|---|
| \(A_m\) | 主动激活峰值相对基线 | `0, 0.5, 1.0, 1.5` × 基线 |
| \(De_J\) | \(\omega\tau_J\) | `0, 0.1, 0.3, 1, 3, 10` |
| \(H_J\) | \(h_J/L\) | `0.5, 1, 2` × 基线 |
| \(\Pi_p\) | \(p_0/\mu_J\) | `0, 0.5, 1, 2` × 基线 |
| \(\Pi_\tau\) | \(\tau_0/\mu_J\) | `0, 0.5, 1, 2` × 基线 |
| \(\Lambda_\Gamma\) | 界面刚度/ECM 有效刚度 | `0.1, 1, 10`，另含 `0` 反事实 |
| \(R_\mu\) | 心肌/心内膜/ECM 刚度竞争比 | `0.25, 1, 4` × 基线 |
| \(De_p\) | `J1` 厚度扩散时间比 | 与 `J0` 的代表慢、中、快三档匹配 |

这些水平用于无量纲机制筛选，不宣称是斑马鱼生理范围。若未来实验给出范围，必须新建标定合同，不得在本合同内静默替换。

不做全因子穷举。先做单因素主效应和三通道载荷分解，再只对出现可重复交互的组合绘制 `De_J–H_J`、`De_J–Λ_Γ` 或 `A_m–Π_p` 二维状态图。

## 6. Outputs and cycle observables

### 6.1 空间—时间场

- 心肌/心内膜节点位移、主应变、面积变化和体积误差；
- ECM 变形梯度、`J`、主应变、Cauchy 应力、储能、损耗和孔压/含液量（仅 `J1`）；
- 双界面法向牵引、切向牵引、滑移、功率与作用—反作用残差；
- 支承反力、支承功和各载荷通道输入功。

### 6.2 传给 Node 2 的候选统计量

\[
\mathcal M(s)=
(\Delta\varepsilon_1,\overline W_J,t_{n,rms},\tau_{rms},OSI,
\phi_{me},\mathcal D_J^{cycle}).
\]

每个量至少报告空间中位数、95 分位数、热点位置、周期波形和相位；不得只报告最大值。界面刺激必须区分法向与切向分量。

在线性小幅极限中，用谐波传递矩阵表示

\[
\widehat{\mathbf y}(\omega)
=\mathbf H(\omega;De_J,H_J,\Lambda_\Gamma,R_\mu)
\widehat{\mathbf u}(\omega).
\]

有限幅值下另报告交互项

\[
\Delta\mathcal M_{int}
=\mathcal M_{a+p+\tau}
-\mathcal M_a-\mathcal M_p-\mathcal M_\tau+2\mathcal M_0,
\]

用来区分真正的有限变形耦合与简单线性叠加。

## 7. Testable hypotheses and falsifiers

### H1：黏弹机械滤波

在 `J0` 中，同一 `De_J` 通过改变频率或改变松弛时间获得时，归一化波形和相位应塌缩。若不塌缩且差异不能由几何非线性解释，单一 `De_J` 描述被否定。

### H2：载荷通道可分辨

主动收缩、压力和 WSS 应在法向牵引、切向牵引、主应变和相位中留下至少一种稳健的不同签名。若所有可观测输出在不确定性内等价，则 Node 2 不得分别拟合三条生物学响应通路。

### H3：界面顺应性控制传递而非凭空造能

降低 \(\Lambda_\Gamma\) 应改变滑移与牵引分配，但不得破坏整体功率闭合。若效应只在单一支承或网格出现，则该界面机制不成立。

### H4：单相黏弹与孔弹/水化的厚度—频率签名可能不同

若 `J1` 出现 \(h_J^2/D_p\) 控制的相位/压力扩散签名，且不能由匹配后的 `J0` 重现，则保留 `J1`；否则优先保留更简约的 `J0`，并把材料机制标记为不可辨识而不是强行选择。

### 直接失败条件

- 候选统计量依赖单一网格、时间步、支承或横向范围；
- 黏弹相位随时间步细化消失；
- 周期末内变量尚未达到周期稳态却被当作稳态结果；
- 规定压力/WSS 被表述为双向 FSI；
- 旧 6 四面体 pilot 被混入正式相位或空间场证据；
- `J0/J1` 未匹配基线刚度就宣称材料机制差异；
- X1-K 未通过即启动正式三层动态数值批次。

## 8. Implementation steps and authorization gates

### N1-R：只读复用与解析准备

合同获批后，在 X1-K 仍失败时只允许：

1. 建立既有 T1 资产的复用/排除清单；
2. 推导小幅传递矩阵、`J0` 复模量、`J1` 厚度扩散极限；
3. 建立双界面制造解、刚体运动、零载荷、零界面和功率符号测试；
4. 冻结几何、单位、波形、网格族与结果 schema；
5. 不运行正式三层周期，不修改 X1-K，不产生论文级机制 claim。

### Hard Gate N1-G0：数值执行前置门

正式三层动态求解前必须有新的受控记录明确 `X1-K passed=true`，包括所要求的 D1/S1/R1/C1/F1；v10 当前失败不能被解释性文字替代。若该门未通过，Node 1 停留在 `readiness_complete_but_numerically_blocked`。

### N1-1：三层基线与制造解

通过 N1-G0 后：

1. 实现被动心内膜 DCM、第二材料界面、腔面载荷和周围组织支承；
2. 依次运行零载荷、主动-only、压力-only、WSS-only；
3. 验证作用—反作用、合力/合矩、刚体客观性、体积、几何和功率账本；
4. 生成第一张阶段审阅图：基线三层 3D 几何、峰值收缩、峰值牵引和周期末状态；
5. 提交人类阶段检查。未接受该图和账本前，不启动参数扫描。

### N1-2：周期稳态与数值收敛

- 每个黏弹/孔弹工况连续运行多个周期，直到两个连续周期的归一化波形差满足门限；
- 时间步至少三档；
- ECM 厚度方向至少 `4/6/8` 个单元层并同步控制横向单元质量；
- DCM 表面至少基线与一个约四倍面数的等效能量离散，必要时增加第三档；
- 求解/耦合容差至少两档；
- 若相邻精细级不通过，追加一级而不是选择性丢弃敏感指标。

### N1-3：载荷分解与无量纲筛选

1. 执行三通道 `2^3` 开/关组合，计算主效应和交互项；
2. 完成 `De_J` 两路径数据塌缩；
3. 依次筛选 `H_J、Λ_Γ、R_μ、Π_p、Π_τ`；
4. 做横向范围与支承刚度稳健性；
5. 只对稳健交互建立二维状态图。

### N1-4：`J0/J1` 材料竞争

在共同的几何、边界、输入和参考频率匹配下比较两种材料，报告可区分量、不可区分量与所需未来实验；不以拟合参数数量多少作为机制成立证据。

### N1-5：Figure 2 与 Human Gate 1

形成可复算数据包、Figure 2 草案、负结果和候选刺激排序。Human Gate 1 决定：

- 哪些 \(\mathcal M\) 分量进入 Node 2；
- `J0`、`J1` 或“材料不可辨识”哪一结论被保留；
- 是否需要额外实验范围再进入慢模型。

本合同获批不自动授权 Node 2。

## 9. Pre-registered numerical acceptance criteria

### 9.1 单工况硬门

- 所有求解器报告成功，无 NaN/Inf；
- 两个细胞最大体积比误差 `<= 1e-8`；
- 归一化 KKT/力学残差 `<= 1e-5`；
- 最小细胞三角面面积比 `>= 0.05`，无翻转；
- 所有 ECM 四面体 `J > 0`，正式基线另要求 `min(J) >= 0.5`；
- 最小界面 gap `>= -1e-12`；
- 每个界面 pair force 与 pair moment residual `<= 1e-10`；
- 许可方向能量导数中心差分相对误差 `<= 1e-5`；
- 物理耗散非负；周期功率闭合残差不超过总正输入功的 `1%`。

### 9.2 周期稳态与时间收敛

- 两个连续周期的关键波形归一化 `L2` 差 `<= 1e-3`；
- 中—细时间步的积分统计量差 `<= 2%`；
- 相位差变化 `<= 0.01` 个周期；
- 耗散变化 `<= 5%`；
- 若峰值跨离散采样点，使用同一周期插值规则，不用索引位置冒充真实相位。

### 9.3 空间和边界稳健性

- 中—细网格的细胞全局读数差 `<= 1%`；
- ECM/界面能量积分、95 分位应力和牵引差 `<= 10%`；
- 候选热点质心移动 `<= 0.1L`；
- 横向范围或支承刚度变体下，候选统计量的中位数与 95 分位变化均 `<= 10%`；
- 若未通过，只能降级为边界依赖观察，不能进入 Node 2。

### 9.4 机制判别门

- `J0` 同 `De_J` 两路径的归一化波形差 `<= 5%`、相位差 `<= 0.02` 周期，方可称数据塌缩；
- `J0/J1` 的差异必须大于数值收敛误差与参数匹配不确定性之和，方可称可区分；
- 候选 Node 2 刺激量必须同时满足：数值收敛、边界稳健、载荷路径可解释、材料敏感性已知、未来实验可观测五项门。

## 10. Figure 2 provisional spine

| Panel | 暂定内容 | 证据类型 |
|---|---|---|
| A | 三维 DCM–FEM–DCM 几何、双界面、压力/WSS/主动输入与支承 | 模型定义 |
| B | 一个收缩周期的 3D 变形、ECM 应力/耗散和心内膜牵引快照 | 收敛后的模拟场 |
| C | 输入功、储能、耗散、支承功和数值残差账本 | 守恒证据 |
| D | `De_J` 两路径塌缩及幅值—相位传递函数 | 无量纲规律 |
| E | 主动/压力/WSS 分解与交互热图 | 因果反事实 |
| F | `J0/J1` 厚度—频率竞争及进入 Node 2 的刺激候选 | 机制判别/负结果 |

Figure 2 只使用实际计算结果和可复算定量图；模型示意只限 Panel A。阶段汇报优先先交 Panel A–C 的 3D 状态图，不等待所有扫描结束。

## 11. Impacted files or modules

合同获批且对应门满足后，预计新增或修改：

- `docs/theory/efe_node1_*`：解析退化、传递矩阵和材料竞争推导；
- `src/hybrid/`：被动心内膜 DCM、双界面三层耦合、腔面载荷、支承与周期账本；
- `tests/hybrid/`：制造解、能量/功率、周期稳态、网格和反事实测试；
- `scripts/run_efe_node1_*`：分批执行入口；
- `results/hybrid/efe_node1_*`：不可覆盖的版本化机器结果；
- `figures/theory/efe_node1_*` 或版本化 Figure 包：阶段审阅图和 Figure 2 草案；
- `project_control/efe_node1_*`：执行、检查、偏差和 Human Gate 1 记录。

不得覆盖旧 T1、Route H、X1-K 或旧 Node 1 pilot 资产。

## 12. Test plan

1. **理论测试**：量纲、复模量极限、`De→0/∞`、`H→0`、零界面、零载荷和线性叠加极限；
2. **几何测试**：刚体平移/旋转、镜像、法向翻转、面积质量、体积和 `J`；
3. **界面测试**：同点映射、双界面独立编号、作用—反作用、合矩与随机方向能量导数；
4. **周期测试**：内变量周期稳态、非负耗散、时间步、耦合容差与相位插值；
5. **收敛测试**：ECM 空间、DCM 表面、边界范围和支承灵敏度；
6. **反事实测试**：主动-only、压力-only、WSS-only、零界面、强粘附和有限滑移；
7. **机制测试**：同 `De_J` 两路径、`J0/J1` 匹配、厚度—频率标度和可辨识性；
8. **证据测试**：每个 Figure panel 可追溯到参数、网格、代码版本、原始结果和生成脚本。

## 13. Risks and mitigations

1. **局部支承主导结果**：扩大横向范围并扫描支承；支承功单列；
2. **单细胞心内膜不代表细胞层**：把 Node 1 主张限制为最小传递单元，层级效应留到 Node 3；
3. **表面积能量过强抑制变形**：不施加硬面积守恒，报告面积变化与能量占比；
4. **高主动变形造成不稳定**：先在基线 0.20 完成收敛，再把 1.5× 作为应力测试；失败如实保留，不用求解器阻尼冒充材料耗散；
5. **黏弹与孔弹不可辨识**：允许明确负结果，并据此提出厚度—频率或局部压力实验；
6. **计算量爆炸**：采用分层筛选而非全因子；任何降采样、降网格或缩短周期必须记录为偏差并退出正式证据；
7. **X1-K 持续失败**：只完成 N1-R，不用固定拓扑旧 pilot 绕过硬门。

## 14. Acceptance criteria for Node 1 completion

Node 1 只有同时满足以下条件才可提交 Human Gate 1：

- 三层基线、三通道单独加载和全加载均通过单工况硬门；
- 周期稳态、时间、空间、容差和边界稳健性达到预注册标准；
- 至少一个候选传递规律通过解析极限或制造解支持；
- `J0` 的 `De_J` 塌缩得到支持或被明确否定；
- `J0/J1` 比较给出可区分或不可区分的可复核结论；
- Figure 2 的每个定量 panel 可从版本化源数据重算；
- 所有失败、偏差和旧证据边界保留；
- 没有启动任何慢变量推进，也没有将机械相关性写成 EFE 因果。

## 15. Out of scope

- `q_E/q_M/ρ_c/ρ_el/A_c/F_g` 的慢时间推进；
- ECM 分泌、降解、胶原/弹性纤维沉积或 EFE 增厚；
- 多心肌细胞层、连续心内膜细胞层、细胞迁移和谱系竞争；
- 双向 FSI、完整腔内血流、电生理和器官循环；
- 斑马鱼参数标定、疾病组拟合或干预预测；
- 修复 X1-K；该问题必须使用独立授权合同；
- Node 2–4 的实现或 Figure 3–6。

## 16. Required memory updates

只有合同经人类批准并完成相应执行/检查后，项目记忆才允许记录：

- Node 1 研究的是健康冻结慢状态下的快速三层传递，不是 EFE 病程；
- 心肌主动收缩采用内部变形加载，细胞体积受约束，表面积不硬守恒；
- ECM 使用连续 FEM 是为了表示厚度方向应力传播、黏弹/孔弹记忆、压力扩散和界面场，而 DCM 保留细胞形态与主动自由度；
- 规定压力/WSS 不等于双向 FSI；
- 进入 Node 2 的机械刺激只能由 Human Gate 1 从通过稳健性门的候选中选择；
- X1-K 和任何收敛失败继续作为冻结证据保留。

## 17. Human approval requested

本草案请求人类终审决定：接受、修改或否决以下五项：

1. Node 1 采用最小 `心肌 DCM–ECM FEM–心内膜 DCM` 三层单元；
2. X1-K 继续作为正式动态数值执行硬门；
3. 先提交三层基线 3D 状态图，再进入参数扫描；
4. `J0` 单相黏弹与 `J1` 最小孔弹/水化作为竞争模型；
5. Human Gate 1 只选择稳健机械刺激，不提前启动慢 EFE 方程。

在明确批准前，本合同不授权任何 Node 1 数值执行。
