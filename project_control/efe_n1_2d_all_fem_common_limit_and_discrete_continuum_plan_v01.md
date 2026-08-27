---
plan_id: PLAN-EFE-N1-2D-ALL-FEM-COMMON-LIMIT-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-25
executor: not_dispatched
inspector: human_final_reviewer
related_memory_entries: []
execution_authorized: false
mainline_position: after_n1_2c_time_convergence_before_n1_3_screening
---

# EFE N1-2d：全 FEM 共同极限与离散—连续跨越方案 v01

## Goal

建立一个可证伪的三模型验证体系，回答两个不同问题：

1. **正确性问题**：当前 DCM–FEM–DCM 在均匀、固定拓扑和匹配本构的共同极限
   中，是否恢复独立的 cell-resolved all-FEM 解；
2. **必要性问题**：当细胞尺度异质性、细胞身份、离散状态转换和局部 ECM 源项
   重要时，均质 all-FEM 在哪些尺度范围内失去局部预测能力，而 DCM–FEM 是否
   保留了可观测、可验证的信息。

本方案不以“证明 FEM 做不了”为目标。允许形成的最高层级主张为：

> DCM–FEM 在均匀固定拓扑极限中恢复单体有限元参照；当细胞颗粒尺度接近机械
> 传递长度，或细胞机械状态通过阈值非线性驱动局部 ECM 重塑时，均质连续模型
> 会丢失细胞级分布和空间历史，而显式细胞身份成为预测 EFE 萌生位置的必要状态。

## 1. Scientific logic and falsifiable claim

### 1.1 三模型层级

| 模型 | 定义 | 科学角色 |
|---|---|---|
| Cell-resolved all-FEM (`CR-FEM`) | 心肌和心内膜为显式 FEM 壳/膜及封闭体积约束，ECM 为三维体 FEM；每个细胞可独立赋参 | 固定拓扑共同极限参照 |
| Homogenized all-FEM (`H-FEM`) | 心肌/心内膜细胞层被均质为连续主动/被动层，ECM 保持体 FEM | 检验连续化何时足够 |
| DCM–FEM–DCM (`Hyb`) | 显式 DCM 心肌和心内膜细胞，通过连续三维 FEM ECM 耦合 | 保留细胞身份、历史和局部源项 |

`CR-FEM` 不是绝对真值；它是固定拓扑下的独立数值参照。实验才是物理验证。

### 1.2 共同极限

当细胞材料、激活、纤维方向和界面均匀，且细胞尺度远小于机械传递长度时，要求

\[
\mathcal M_{\rm Hyb}
\rightarrow
\mathcal M_{\rm CR-FEM}
\rightarrow
\mathcal M_{\rm H-FEM}
\]

在各自时间、空间和求解容差收敛后成立。这里 \(\mathcal M\) 至少包括全局缩短、
界面牵引、ECM 能量/耗散、相位和细胞层形态。

### 1.3 离散—连续控制量

预注册三个核心无量纲量：

\[
\epsilon_c=\frac{d_{\rm cell}}{\ell_{\rm mech}},
\qquad
CV_A=\frac{\sigma_A}{\bar A},
\qquad
\rho_A=\frac{\ell_A}{d_{\rm cell}},
\]

其中 \(d_{\rm cell}\) 为细胞尺度，\(\ell_{\rm mech}\) 为由细胞层、界面与 ECM
共同决定的机械传递/平滑长度，\(CV_A\) 为激活异质性，\(\ell_A\) 为异质性的
空间相关长度。

预期但尚未证明：`H-FEM` 在 \(\epsilon_c\ll1\)、\(CV_A\to0\) 时有效；在
\(\epsilon_c\sim1\)、较大 \(CV_A\) 或 \(\rho_A\sim1\) 时，局部牵引尾部、
热点位置和细胞刺激分布发生连续模型无法由均值恢复的偏离。

### 1.4 EFE 阈值不交换

若第 \(i\) 个心内膜细胞的机械刺激为 \(S_i\)，状态阈值为 \(S_c\)，则超阈值
细胞比例为

\[
f_{\rm on}=\left\langle H(S_i-S_c)\right\rangle,
\]

而均质模型只使用 \(\bar S\) 时得到 \(H(\langle S_i\rangle-S_c)\)。一般有

\[
\left\langle H(S_i-S_c)\right\rangle
\neq
H\!\left(\left\langle S_i\right\rangle-S_c\right).
\]

因此，本方案关注的不是平均壁应力是否不同，而是相同平均载荷下，局部细胞是否
跨阈、ECM 从何处萌生、斑块是否持续以及这些预测能否被实验观察。

## Inputs

1. `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md` 的界面同一点映射、
   功率转置和退化极限；
2. `project_control/efe_node1_fast_trilayer_mechanics_contract_v01.md` 的三层几何、
   本构、加载、功率账本和 N1-2 数值门；
3. R5 的 D0/E0/F150、T16 周期稳态候选及其完整证据边界；
4. 已生产化的 FEniCSx ECM 后端及 NumPy–UFL 等价性证据；
5. 后续经人类接受的 T16/T32/T64 时间收敛和 DCM/ECM 空间收敛结果；
6. Node 0/Node 2 将冻结的细胞刺激 \(S_i\)、状态变量和 ECM 源项定义。

若第 5、6 项尚未达到门控，本方案相应阶段只能设计，不能形成论文主张。

## Outputs

1. DCM 表面能与 FEM 壳/膜本构的独立参数映射表和切线测试；
2. `CR-FEM`、`H-FEM`、`Hyb` 三套版本化参考模型；
3. 被动、主动峰值和黏弹周期三个共同极限 benchmark；
4. 三模型分别完成的时间、空间和容差收敛证据；
5. \((\epsilon_c,CV_A,\rho_A)\) 控制下的离散—连续适用域图；
6. 相同平均激活、不同细胞分布下的局部牵引、刺激和超阈比例结果；
7. EFE 局部源项/萌生位置的有界验证或明确负结果；
8. Figure 1–3 的增补 panel、Supplementary verification figures 和 Methods
   段落；
9. 失败结果、替代解释、可辨识性和不支持 DCM 必要性的证据。

## Implementation Steps

### V0 — 数学匹配与防止“伪对照”

1. 从 DCM 面积、弯曲、封闭体积和主动纤维能量推导参考态切线模量；
2. 为 `CR-FEM` 选择匹配的非线性壳/膜和腔体体积约束；不得用输出拟合掩盖
   本构不一致；
3. 冻结相同几何、载荷、界面势、法向、参考面积和功率共轭；
4. `CR-FEM` 必须独立装配，不得直接调用 DCM 能量/力 helper；
5. 主实现候选为独立单体 FEniCSx 变分形式；只有能严格匹配材料和界面时，才
   另立 FEBio 等跨求解器简单 benchmark；
6. 先关闭不必要的复杂机制做小变形 patch，再逐项恢复弯曲、主动应变和黏弹性。

### V1 — 共同极限三个 benchmark

1. **被动小变形 patch**：关闭激活和黏弹记忆，比较位移、反力、界面作用—
   反作用、能量及其方向导数；
2. **主动准静态峰值**：在 5%、10%、20% 等匹配主动加载下比较缩短、形态、
   牵引、ECM 应变能、体积和 `J`；
3. **黏弹周期**：使用相同 SLS 参数和波形，比较幅值、相位、周期耗散、内部
   变量和功率账本；
4. 每个模型先独立收敛，再做跨模型比较；禁止比较两个未收敛结果并称为一致。

### V2 — 共同极限与信息损失分离

1. 在均匀同步细胞层上验证 `Hyb ≈ CR-FEM ≈ H-FEM`；
2. 保持平均激活、平均纤维方向和平均刚度不变，只改变细胞间分布；
3. 设置均匀、随机孤立、小簇、大斑块和沿纤维排列等空间图样；
4. 同时扫描 \(CV_A\) 和 \(\rho_A\)，并通过几何/材料改变
   \(\epsilon_c\)；
5. 分开报告全局均值与局部尾部，防止“平均缩短相同”掩盖热点失真。

### V3 — 离散—连续适用域

1. 计算 `H-FEM` 相对 `CR-FEM/Hyb` 的全局误差、局部场误差和热点误差；
2. 以数值不确定性为底噪，确定连续模型何时足够、何时不能预测局部细胞刺激；
3. 形成 \((\epsilon_c,CV_A)\) 主图，并用 \(\rho_A\) 或 ECM 松弛尺度分层；
4. 若不存在超过数值误差的稳定偏离，记录“连续模型在当前范围足够”的负结果。

### V4 — EFE 相关阈值与局部 ECM 源项

1. 只在 Node 2 已冻结 \(S_i\)、\(S_c\)、细胞状态和源项后执行；
2. 对相同平均载荷但不同细胞分布，比较超阈值细胞比例和空间位置；
3. 将离散细胞源项映射至连续 ECM，比较萌生位置、斑块统计和后续力学反馈；
4. 用 cell-resolved FEM 小 patch 复核固定拓扑早期响应；拓扑变化阶段不把
   `CR-FEM` 无法直接延续表述为“FEM 失败”，而是记录所需网格/状态转移；
5. 只有差异大于数值误差、参数不确定性且具有实验可观测量时，才保留 DCM
   必要性主张。

## Paper Integration

### Figure 1 — 理论与信息层级

在现有 DCM–FEM–DCM 三层理论中增加小型模型层级，不把 Figure 1 改成软件
流程图：

- `CR-FEM → Hyb → H-FEM` 的共同极限/均质化关系；
- \(\epsilon_c\)、\(CV_A\)、\(\rho_A\)；
- 阈值不交换关系
  \(\langle H(S_i-S_c)\rangle\neq H(\langle S_i\rangle-S_c)\)；
- 有界主张：连续 ECM 与离散细胞状态的耦合是快力学通向慢 EFE 萌生的最小
  信息结构之一。

Figure 1 只定义逻辑，不提前展示未经计算的相图。

### Figure 2 — Node 1 正确性和连续极限

暂定 panel：

| Panel | 内容 | 证据角色 |
|---|---|---|
| A | 三模型匹配几何、本构和界面 | 模型定义 |
| B | 被动/主动/黏弹共同极限叠加 | 跨方法验证 |
| C | T16/T32/T64、DCM/ECM 网格和容差收敛 | 数值可信度 |
| D | 相同平均激活的均匀与斑驳细胞层 | 反事实设计 |
| E | 全局响应与局部牵引尾部的分离 | 信息损失 |
| F | 初步离散—连续适用域 | 有界机制结果 |

R5 的周期候选只作为 Figure 2 验证链的一部分，不单独承担 DCM 必要性主张。

### Figure 3 — EFE 起始

Figure 3 使用已在 Figure 2 验证的快速刺激分布，展示：

- 相同平均载荷下不同的超阈值细胞比例；
- 离散 ECM 源项与初始斑块位置；
- 均质模型和显式细胞模型对萌生位置的预测差异；
- 若差异不存在，则把“DCM 必要”作为被否定结果，而不是调整阈值制造差异。

### Supplementary figures

- S1：本构映射、patch tests、方向导数和功率符号；
- S2：三模型网格、时间步、容差及独立收敛；
- S3：所有异质性图样、负结果和跨求解器简单 benchmark（若获批并可匹配）。

### Manuscript claim language

允许的目标表述：

> The hybrid formulation recovers a monolithic finite-element reference in
> the homogeneous fixed-topology limit, while retaining cell-resolved
> mechanical histories required to test thresholded and spatially
> heterogeneous ECM remodeling.

禁止表述：

- “FEM 不能模拟细胞/心脏”；
- “DCM 天然比 FEM 更准确”；
- “DCM–FEM 在所有尺度更优”；
- 用计算速度、网格数量或软件便利性替代物理必要性证据。

## Impacted Files Or Modules

执行获批后，预计新建或扩展：

- `docs/theory/`：DCM–FEM 切线映射、均质极限和阈值不交换推导；
- `src/hybrid/`：独立全 FEM reference seam、三模型统一观测量和误差度量；
- `tests/hybrid/`：patch、方向导数、功率、共同极限和跨模型收敛测试；
- `scripts/`：三个 benchmark、异质性生成和适用域后处理入口；
- `results/hybrid/`：不可覆盖的版本化 `CR-FEM/H-FEM/Hyb` 结果；
- `02_图表/Figures/`：经逐图门控的 Figure 1–3 与 Supplementary 包；
- `project_control/`：每阶段执行、检查、偏差和人类决定记录。

具体文件名、求解器、网格和资源预算必须在各阶段执行合同中冻结。本方案不授权
现在创建这些实现文件。

## Test Plan

1. **理论**：量纲、刚体客观性、小应变切线、纯膜/纯弯曲、体积约束和
   `De→0/∞` 极限；
2. **本构映射**：独立拉伸、剪切、弯曲和主动纤维 perturbation，不对最终输出
   反向调参；
3. **界面**：同一点运动、作用—反作用、合矩、能量方向导数和功率转置；
4. **数值**：各模型独立完成时间、空间、容差收敛，报告误差条带；
5. **共同极限**：被动、主动峰值、黏弹周期三工况均比较全局和局部量；
6. **反事实**：相同均值/不同分布、相同方差/不同相关长度、随机种子重复；
7. **阈值**：报告刺激全分布、超阈比例、热点位置与对阈值不确定性的敏感性；
8. **证据**：每个主图 panel 追溯到输入、代码、网格、原始输出和 Notebook。

## Provisional Acceptance Criteria

以下门限必须在首个执行合同中再次冻结；不得结果后调整：

### A. 各模型自身可信度

- 体积、`J`、gap、面质量、KKT、耦合、耗散和功率门不低于 Node 1 合同；
- 时间和空间细化达到各自预登记门，或明确报告未收敛；
- `CR-FEM` 与 `Hyb` 使用独立装配路径和来源审计。

### B. 共同极限

| 指标 | 暂定门 |
|---|---:|
| 被动小变形全局位移、反力、总能量 | `<=1%` |
| 主动峰值全局缩短和反力 | `<=2%` |
| 界面牵引场归一化误差与 p95 | `<=5%` |
| 黏弹周期关键波形差 | `<=2%` |
| 相位差 | `<=0.01T` |
| 周期耗散差 | `<=5%` |
| 各模型数值功率残差 | 正输入功的 `<=1%` |

任何比较误差必须与两侧离散不确定性共同报告。

### C. DCM 必要性主张

只有同时满足以下条件才允许：

1. `Hyb` 与 `CR-FEM` 在共同极限中通过；
2. `H-FEM` 的局部刺激/牵引/超阈比例误差稳定大于三模型数值不确定性；
3. 偏离在多个网格、时间步、随机种子和边界变体中保持；
4. 偏离不能由本构、刚度、界面或平均输入不匹配解释；
5. 相关量能够映射到未来实验或斑马鱼影像观测。

若只出现计算耗时差或全局量的微小差异，不构成 DCM 必要性证据。

## Risks

1. **伪等价**：全 FEM 直接复用 DCM helper，会共同继承同一错误；通过独立变分
   装配和方向导数避免；
2. **伪差异**：细胞壳、体积约束、激活或界面不匹配会制造差异；先做 V0；
3. **两个未收敛结果碰巧一致**：每个模型必须先独立收敛；
4. **均质模型被故意弱化**：`H-FEM` 必须使用合理均质参数和最佳可用连续状态；
5. **把 cell-resolved FEM 的复杂性误写成不能实现**：只比较信息和适用域，不作
   绝对能力断言；
6. **计算量膨胀**：共同极限只做三个代表 benchmark，异质性使用分层设计而非全
   因子；
7. **Node 1 固定拓扑不足以体现 DCM**：若 Node 2/3 不使用细胞身份、阈值状态
   或局部源项，应主动降低 DCM 方法学权重；
8. **GPU 或外部资源依赖**：本方案不授权 GPU；若后续确需 GPU worker，必须按
   项目规则提前获得人类确认。

## Acceptance Criteria For Stage Completion

N1-2d 只有在以下条件全部满足后才可提交 Figure Decision Gate：

1. V0 映射经过独立科学检查；
2. 三个共同极限 benchmark 及各自收敛通过或形成可解释失败；
3. 至少一个异质性设计在保持均值不变的情况下完成；
4. 离散—连续偏离与数值误差、模型差异和参数不确定性分离；
5. DCM 必要性主张通过上述五项门，或被明确否定/降级；
6. Figure 1–3 增补 panel 的主张、证据等级和失败边界通过人类逐图审阅。

## Global Falsifiers

以下任一结果要求收窄或否定路线：

1. `Hyb` 与收敛的 `CR-FEM` 在匹配共同极限中持续不一致；
2. 三模型差异由未匹配本构、界面、边界或离散误差解释；
3. `H-FEM` 在相关参数域内仍准确预测局部牵引分布、超阈细胞比例和 ECM 萌生
   位置；
4. 所谓离散效应只存在于单一网格、随机种子或非生理极端参数；
5. DCM 结果没有可观测量，或阈值结论对未知参数完全不可辨识。

若第 3 项成立，论文应把 DCM 降为实现工具，将核心主张转为连续介质机械机制。

## Out Of Scope

- 本方案批准时不实现或运行任何 FEM/DCM 模型；
- 不授权 T32/T64、网格扫描、N1-3、Node 2/3、GPU worker 或外部求解器安装；
- 不用 all-FEM 重跑整篇论文的全部参数空间；
- 不进行生理参数拟合、实验拟合或正式投稿；
- 不覆盖既有理论、R5 结果、失败证据或已批准 Figure 包；
- 不把跨代码一致性当作实验验证。

## Required Memory Updates

1. 本批准方案和决定记录作为主线 addendum 保留；
2. R5 只有经人类终审接受后才能成为本方案正式输入；
3. 各 V0–V4 阶段仅在执行、独立检查和人类接受后写入稳定项目记忆；
4. 若 DCM 必要性被否定，负结果必须进入稳定记忆并触发论文主张降级；
5. 任何后续计划在讨论 Figure 1–3、N1-3 或 EFE 阈值时，必须检查本方案。

## Sequencing And Next Gate

当前顺序冻结为：

1. 人类终审 R5；
2. 另立并批准 N1-2c 的 T16/T32/T64 时间细化；
3. 完成必要的 DCM/ECM 空间和容差收敛；
4. 起草 N1-2d V0–V1 的首个可执行合同和成本估算；
5. 人类批准后才运行共同极限 benchmark；
6. 通过共同极限门后再执行 V2–V3；
7. V4 等待 Node 2 的刺激、阈值和 ECM 源项定义；
8. 通过逐图 Human Gate 后才更新正式 Figure spine。

下一可授权动作仍是**起草 N1-2c 时间细化合同**；本方案的写入不改变该门控，
也不构成 N1-2d 执行授权。

