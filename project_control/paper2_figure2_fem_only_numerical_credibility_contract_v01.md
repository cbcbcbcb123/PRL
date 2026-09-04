---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V01
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: ade5f96d7b89a6ed6b629a37db795ed08853ba3f
baseline_upstream_ahead_behind: 0/0
accepted_figure1: project_control/paper2_figure1_three_layer_theory_contract_v02.md
accepted_figure1_sha256: a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7
authorization_decision: project_control/paper2_figure1_three_layer_theory_v02_supervisor_acceptance_and_figure2_contract_decision_v01.md
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_numerical_credibility_contract_not_execution_evidence
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度合同 v01

## 0. 科学目的、主张上限和本轮边界

Figure 2 的唯一科学目的，是回答：**当前二维 FEM-only 三层模型的离散方程、代数求解、
时间离散、空间离散、界面投影、功率账本和周期解是否在预先规定的误差范围内自洽？**

Figure 2 可以关闭一部分数值可信度缺口，但不能证明：

- 参数具有斑马鱼生理真实性；
- 模型能够解释 EFE、褶皱、三维心房、血流或疾病进展；
- 候选 \(De\times H\) 规律成立；
- 当前证据已达到 Nature Physics 投稿标准。

v08 的六工况逐值迁移等价只证明新包重现冻结旧 FEM 臂，不是本合同的时间、空间、
容差、投影或功率收敛证据。所有 Figure 2 结论必须由本合同验收后另行授权的新计算产生。

本轮只起草合同，不运行 solver 或 Docker，不修改代码、测试、Figure 1、CURRENT_STATUS、
结果或旧材料，也不执行 Git 暂存、提交或推送。

## 1. 唯一活跃对象与源码锁

### 1.1 固定组织角色

| 组织层 | 唯一活跃实现 |
|---|---|
| 心内膜 | `discrete_cell_chain` |
| 心肌 | `active_plane_strain_fem` |
| ECM | `viscoelastic_plane_strain_fem` |
| 流体 | `absent_in_v08` |

心肌 DCM 已永久退出活跃项目。Figure 2 禁止出现心肌 DCM comparator、representation
轴、缩放/校准参数、identity 指标、旧 `paper2_m2` import 或任何 `GO/MAYBE/NO-GO ID`
路线。`D0` 只可作为固定直接求解器的 provenance 标签，不能被解释为 tolerance 轴。

### 1.2 活跃源码哈希

| 文件 | SHA-256 |
|---|---|
| `src/paper2_hybrid/__init__.py` | `4626ee6f49cac099734728fe0dc2f3412ded11cf5066b32aff556cc39324783f` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/projection.py` | `3bd590f0deef1fbe47cfdf01dea48664b25ff5a8716a546e4758bc4a0642176c` |
| `src/paper2_hybrid/protocol.py` | `f96d779cfcd6c76e9535f90a9941a6156b545d53a0270f04a564c68a304fe3ca` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |
| `src/paper2_hybrid/validation.py` | `6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5` |

执行授权若要求新增 Figure 2 runner、审计函数或测试，必须在执行合同中把新文件加入
源锁。本合同的源码哈希只证明起草入口，不授权保持代码不变强行运行。

### 1.3 运行前后锁

未来每次正式尝试必须在运行前、运行后分别记录：

1. Git HEAD、upstream、ahead/behind 和 scoped status；
2. `src/paper2_hybrid/`、`tests/paper2_hybrid/`、获批合同、正式 runner 的字节数与 SHA-256；
3. 固定角色 manifest、配置 digest、病例矩阵 digest 和阈值 digest；
4. 容器镜像 ID、Python/FEniCSx/PETSc/SciPy/NumPy 版本；
5. CPU、内存、网络、GPU 和 Docker socket 状态。

运行前后任一锁不一致即 `SOURCE_OR_PROTOCOL_DRIFT_FAIL`，正式结果不得标 PASS。

## 2. 现有接口审计与必须补齐的执行接口

### 2.1 已存在、但尚未构成 Figure 2 证据的接口

- `HybridConfig` 冻结 S2/S3/S4、T64/T128/T256 和九个病例标签；
- `build_system` 装配平面应变心肌、SLS ECM、离散链、双界面和底部支撑；
- `direct_solver_assurance` 输出直接残差与范数后向误差；
- `discrete_ledger` 输出精确中点能量增量、主动/腔面/支撑功、drag/SLS 耗散和闭合；
- `project_piecewise_linear_to_common_segments` 可把嵌套原生节点场守恒投到较粗 P0 段；
- `global_structural_checks` 检查角色、装配、对称性、支撑和主动功导数；
- `simulate_endpoint` 输出两周期位移、牵引、ECM 场和功率数组。

### 2.2 执行前必须补齐，但本合同不授权实现

1. S2/S3/S4 共同的 32 段界面投影和 64 段共同相位投影；
2. 两界面、两个物理力分量分别输出，不只给合并向量范数；
3. 真实零右端直接求解控制，而不是只使用 `P0` 的旁路零数组；
4. 连续体 affine patch、链 affine patch、SLS 单元谐波响应等制造检查；
5. 对矩阵对称部分的谱/秩检查和刚体模态控制检查；
6. 通用绝对 floor、零分母、phase wrapping 和热点退化处理；
7. T64/T128/T256 与 S2/S3/S4 的统一比较器；
8. 物理牵引方向映射：论文量使用 Figure 1 的
   \(\mathbf t_{e\to m},\mathbf t_{m\to e},\mathbf t_{e\to n},\mathbf t_{n\to e}\)；
9. create-only 事务 runner、结果 manifest 和 hash ledger。

若正式执行授权未覆盖这些接口，必须在 G0 以前以 `MISSING_VALIDATION_INTERFACE_FAIL`
停止，不得用手工摘录或旧结果替代。

## 3. 病例矩阵、开发集与独立留出

### 3.1 病例语义

| 病例 | 驱动 | Figure 2 角色 |
|---|---|---|
| `P0` | 零主动、零外载 | 零驱动、绝对噪声 floor、零右端控制 |
| `P1` | 给定微小 affine 宏观应变 | 被动切线和 patch 辅助检查；不是完整耦合平衡解 |
| `A2` | 均匀纯主动 | 纯主动开发病例 |
| `LN` | 纯法向规定载荷 | 单输入法向开发病例 |
| `LS` | 纯切向规定载荷 | 单输入切向开发病例 |
| `CQ` | 主动 + 相差 \(\pi/2\) 的法向载荷 | 多输入、相位敏感开发病例 |
| `S1` | 空间异质纯主动 | 场、局部化与热点开发病例 |
| `C0` | 主动 + 同相法向载荷 | **独立留出病例**，不得参与阈值、floor 或规则调定 |
| `A1` | 当前源码中与 `A2` 具有相同驱动 | 标签别名审计，不计为独立证据或留出 |

选择理由：`A2/LN/LS/CQ/S1` 是覆盖主动、法向、切向、多输入相位和空间异质性的最小
开发集；`C0` 改变组合载荷相位但不引入新参数，适合作为锁定规则后的留出。当前
`A1/A2` 的 `_case_components` 代数输入相同，禁止用重复结果人为增加病例数。

### 3.2 运行矩阵

| 阶段 | 病例 | 空间/时间端点 | 用途 |
|---|---|---|---|
| G0 | P0、P1、制造解 | S2/S3/S4，静态 | 源码、装配、patch、零驱动、作用反作用 |
| G1 | P0、A2、LN、LS、CQ、S1 | 首先 S2/T64；其后每个正式端点自动检查 | 代数求解器 |
| G2 | A2、LN、LS、CQ、S1 | S3 × T64/T128/T256 | 时间收敛 |
| G3 | A2、LN、LS、CQ、S1 | S2/S3/S4 × T128 | 空间收敛 |
| G4 | A2、LN、LS、CQ、S1 | S3/S4 × T128/T256 四角 | 时间—空间联合触发 |
| G5–G7 | 同一开发集 | 复用所有已通过端点；终局 S4/T256 | 投影、功率、周期一致性 |
| Hold-out | C0 | S3/S4 × T128/T256 四角 | 规则锁定后的独立留出 |

不得先看 `C0` 再修改阈值。若 `C0` 失败，标记 `HOLDOUT_FAIL`，只能另立修订合同；不得
回写本版本阈值后重跑并继续称为独立留出。

## 4. 固定离散阶梯和比较方向

### 4.1 空间阶梯

| 标签 | \(n_x\) | 每连续层 \(n_y\) | 角色 |
|---|---:|---:|---|
| S2 | 32 | 8 | 粗层，只用于误差序列，不作最终参考 |
| S3 | 64 | 16 | 中层、时间收敛固定层 |
| S4 | 128 | 32 | 当前最细空间参考 |

网格逐级 2 倍嵌套，三层使用同一 \(n_x\)，三角形对角线固定为
`lower_left_to_upper_right`。空间比较方向固定为

\[
e_{23}=d(Q_{S2},Q_{S3}),\qquad e_{34}=d(Q_{S3},Q_{S4}),
\]

并以 S4 作为有限阶梯参考。不得只展示 S4，也不得把 S4 称为连续极限。

### 4.2 时间阶梯

| 标签 | 每周期步数 | \(\Delta t/T\) | 角色 |
|---|---:|---:|---|
| T64 | 64 | 1/64 | 粗时间层 |
| T128 | 128 | 1/128 | 中时间层、空间收敛固定层 |
| T256 | 256 | 1/256 | 当前最细时间参考 |

时间比较方向固定为

\[
e_{64,128}=d(Q_{T64},Q_{T128}),\qquad
e_{128,256}=d(Q_{T128},Q_{T256}),
\]

并以 T256 作为有限阶梯参考。不得把 T256 称为连续时间解。

### 4.3 联合四角触发

G4 固定使用

\[
(S3,T128),\ (S3,T256),\ (S4,T128),\ (S4,T256).
\]

对每个 QoI 计算细空间处的时间增量、细时间处的空间增量和交互缺陷

\[
\delta_{st}=d\!\left[
(Q_{S4,T256}-Q_{S3,T256}),
(Q_{S4,T128}-Q_{S3,T128})
\right].
\]

只有 G2 与 G3 分别通过后才可触发 G4。单独时间 PASS 加单独空间 PASS 不等于联合
PASS；联合失败不得被平均值掩盖。

## 5. 通用比较、绝对 floor 和退化规则

### 5.1 预注册特征尺度

采用 Figure 1 的无量纲 benchmark，预先定义：

| QoI 类 | 特征尺度 \(S_Q\) |
|---|---|
| 位移 | \(S_u=a_0L\) |
| 应变、内部变量、宏观/自由缩短 | \(S_\epsilon=a_0\) |
| 牵引/应力 | \(S_t=E_\infty a_0\) |
| 广义力、右端和代数残量 | \(S_f=E_\infty a_0L\) |
| 每单位厚度储能/功 | \(S_W=E_\infty a_0^2L^2\) |
| 功率 | \(S_P=S_W/T\) |

对每个 QoI，从真实零右端直接求解控制得到同一离散/同一算子的数值噪声 \(N_Q\)，冻结

\[
F_Q=\max(10^{-12}S_Q,\ 10N_Q).
\]

不得以 `1e-30` 代替科学 floor，也不得用非零病例的最小值事后定义 floor。

### 5.2 标量、波形和场误差

标量误差为

\[
d_s(q,r)=\frac{|q-r|}{\max(|r|,F_Q)}.
\]

共同定义域上的波形或场误差为

\[
d_2(q,r)=\frac{\|q-r\|_{L^2}}{\max(\|r\|_{L^2},F_Q\sqrt{|\mathcal D|})}.
\]

若参考量 \(\|r\|\le F_Q\)，则记录 `BELOW_RESOLUTION_FLOOR`，不计算相对误差或收敛
阶；只有绝对差 \(\|q-r\|\le F_Q\) 才可通过零量门。零分母不得返回 0、NaN 或 Inf。

### 5.3 相位规则

相位只对已指定输入通道和输出一阶谐波均大于 \(10F_Q\) 的信号定义：

- A2、S1：相对于主动输入；
- LN：相对于法向载荷；
- LS：相对于切向载荷；
- CQ/C0：相对于主动时钟，同时记录规定载荷相位；不得把多输入相位解释为单一传递函数。

相位差必须 wrap 到

\[
\Delta\phi=\operatorname{atan2}[\sin(\phi_1-\phi_2),\cos(\phi_1-\phi_2)]
\in[-\pi,\pi].
\]

低于幅值门时记 `PHASE_UNDEFINED_LOW_AMPLITUDE`，不得强置为零或判收敛失败。

### 5.4 热点退化规则

主热点只在 S1 的心肌侧物理轴向牵引
\(t_{e\to m,x}=-t_{me,x}^{rep}\) 上定义为最强压缩区。共同段场记为 \(t_j\)，候选热点集

\[
\mathcal H=\{j:t_j\le t_{min}+\eta_h(t_{max}-t_{min})\}.
\]

若场范围 \(t_{max}-t_{min}\le F_t\)，或热点集覆盖超过 25% 周期域，标记
`HOTSPOT_DEGENERATE`，不得报告唯一位置。非退化时使用周期距离

\[
d_L(x,y)=\min(|x-y|,L-|x-y|)
\]

比较热点集，不直接比较数组索引。\(\eta_h\)、集合相似阈值和位置阈值见第 13 节
Supervisor 候选裁决。

## 6. 分层、fail-closed 验证顺序

顺序固定为：

```text
G0 静态/制造检查
  -> G1 代数求解器
  -> G2 时间
  -> G3 空间
  -> G4 时间-空间联合触发
  -> G5 共同投影
  -> G6 功率闭合
  -> G7 周期稳态一致性
  -> C0 独立留出
  -> Supervisor Gate
```

任一门失败立即停止后续门；保留失败结果，不得在同一正式尝试中修改阈值、病例、
floor、网格、时间步、求解器或 QoI 后继续。

## 7. G0 — 静态、制造与结构检查

G0 必须在 S2/S3/S4 上完成：

1. 源码、角色、病例、网格、时间阶梯和禁用符号的静态审计；
2. FEniCSx/UFL 与手工 \(B^TCB\) 单元/全局装配一致；
3. 连续体均匀 affine 应变 patch：内部残量与解析边界合力一致；
4. 心内膜周期链 affine patch：轴向差显式含
   \(\bar\epsilon\Delta x\)，能量和宏观共轭力与解析式一致；
5. SLS 单元在 DC 和单频输入下的 \(z\)、应力、相位与解析响应一致；
6. 两界面制造位移跳跃下的四个物理作用力成对相消；
7. 主动能对 \(a\) 的解析导数与多步长有限差分平台一致；
8. \(\mathbf K_{mat}+\mathbf K_s\) 和 \(\mathbf G\) 的对称性；
9. 材料/速率矩阵的正定或半正定结构、预期零空间与底部支撑后的刚体模态消除；
10. 真实零右端经直接求解得到有限零状态，不只接受 `P0` 旁路数组。

`P1` 当前是人为设置的宏观应变数组，不能单独充当完整耦合制造解。任何制造检查必须
给出解析输入、解析输出、离散残量和缩放方式。

## 8. G1 — 代数求解器可信度

### 8.1 固定求解器语义

当前求解器是 `scipy_superlu` 直接因子分解，分别求 DC 实系统和单频复系统。Figure 2
没有可调迭代容差轴；`D0` 只能表示固定直接求解器配置。禁止虚构 D1/D2 或把一次
SuperLU 运行称为 tolerance convergence。

若后续需要迭代求解器或代数 tolerance 扫描，必须标为
`candidate_future_iterative_solver`，另立实现、预条件、停止准则和等价性合同；不属于本
Figure 2 v01。

### 8.2 每端点必须报告

- \(\|Aq-b\|_2/\|b\|_2\)（仅非零右端）；
- 范数后向误差
  \(\|r\|_\infty/(\|A\|_\infty\|q\|_\infty+\|b\|_\infty)\)；
- 零右端绝对残量和解范数；
- DC 与复谐波系统分别的结果；
- 是否出现零/近零 pivot、非有限值或异常条件估计；
- 求解前后矩阵与右端哈希。

若 \(\|b\|\le F_b\)，禁止计算相对残差，改用绝对门。所有正式端点均自动执行 G1；
不能只在最粗端点证明一次。

## 9. G2 — 时间离散可信度

固定 S3，对 A2/LN/LS/CQ/S1 分别计算 T64/T128/T256。比较：

- 宏观短缩、心内膜平均位移和界面积分牵引的完整周期波形；
- 一阶谐波幅值与按第 5.3 节定义的相位；
- 储能、各功/耗散的周期积分；
- ECM 内变量和两界面原生积分范数；
- 峰值只作 sidecar，不单独替代波形范数。

T256 是有限阶梯参考，不是解析时间极限。对高于 floor 的光滑 QoI，要求误差从
T64→T128 到 T128→T256 下降，并报告观察阶

\[
p_t=\log_2\!\left(\frac{e_{64,128}}{e_{128,256}}\right).
\]

当前谐波求解器实现的是 Crank–Nicolson 的离散周期响应；时间门验证该离散响应向细
时间步稳定，而不是验证通用非正弦瞬态积分器。

## 10. G3 — 空间离散可信度

固定 T128，对 A2/LN/LS/CQ/S1 分别计算 S2/S3/S4。G3 先比较不需要跨网格逐点对应的
全局 QoI、边界合力和原生积分范数；牵引场逐点/逐段比较延后到 G5 的共同投影。

必须同时报告 \(e_{23}\) 和 \(e_{34}\)，并说明 P1 位移、分片常应变、界面 penalty、
最大值/热点等 QoI 可能具有不同收敛阶。不得只给一个“总体误差”，也不得强迫低于
floor 的量产生伪收敛阶。

S4 只是当前参考。若 \(e_{34}\) 不下降、符号反转或热点退化，标记空间失败；不得以
S4 图更平滑作为通过理由。

## 11. G4 — 时间—空间联合触发

复用第 4.3 节四角，对开发集的每个核心 QoI 要求：

1. S4 上 T128→T256 的时间增量仍在时间门内；
2. T256 上 S3→S4 的空间增量仍在空间门内；
3. 时间增量与空间增量的交互缺陷不超过预注册门；
4. 相位、符号和物理解释在四角一致；
5. 任一 fine-corner 非有限、失去代数门或功率门预检即失败。

只有 G4 通过，后续才可称“在当前有限阶梯内联合稳定”。禁止使用“时间已收敛 + 空间
已收敛”替代四角证据。

## 12. G5 — 共同界面投影、范数和热点

### 12.1 固定公共定义域

- 空间：\([-L/2,L/2]\) 上 32 个等长 P0 段，端点为 33 个坐标；
- 时间：一个归一化周期 \([0,T)\) 上 64 个等长相位段；
- S2/S3/S4 原生空间段数分别为 32/64/128，公共 32 段嵌套于全部网格；
- T64/T128/T256 原生时间段数分别为 64/128/256，公共 64 段嵌套于全部时间层；
- 周期端点只用于闭合积分，不重复计权；左右边界使用一致的半权重/周期合并规则。

v08 的 64 个公共空间段只适用于其 S4 迁移比较，不能直接用于含 S2 的 Figure 2 空间
阶梯。Figure 2 固定为 32 空间段，不把 v08 投影数值当新证据。

### 12.2 投影对象和守恒要求

对两个界面、两个物理力分量分别执行：

1. 原生分片线性牵引到公共 P0 段的精确分段积分平均；
2. 常量和线性牵引制造场的分量、符号与总合力守恒；
3. 只投影一个界面物理力，再以严格负号生成对侧力，避免独立投影破坏作用—反作用；
4. 空间—时间 \(L^2\) 范数使用共同 32×64 定义域；
5. 界面功率密度 \(\mathbf t\cdot\dot{\mathbf u}\) 单独按原生积分投影/积分，不能假设
   “平均牵引 × 平均速度”自动守恒；
6. 原生与公共坐标、权重、边界、dtype、shape 和方向 manifest 全部写入结果；
7. S1 热点按第 5.4 节在公共段上比较。

G5 必须同时报告原生合力/功率、公共合力/功率及两者差。只报告公共场图片不构成守恒
证据。

## 13. 核心 QoI 与候选硬阈值

### 13.1 必须输出的核心 QoI

| 类别 | QoI |
|---|---|
| 宏观运动 | \(-\bar\epsilon(t)\) 有限支撑短缩；规定自由短缩 \(\langle p\rangle a(t)\) 仅作输入/比较器 |
| 心内膜 | 平均切向/法向位移完整波形和一阶谐波 |
| 双界面 | 四个物理作用力方向、两分量公共场、合力、空间—时间 \(L^2\) 范数 |
| 相位 | 按第 5.3 节各单输入/多输入规则得到的 wrapped phase |
| 热点 | S1 的心肌侧最强压缩轴向物理牵引热点集、周期位置和幅值 |
| ECM | \(\epsilon_e,z,\sigma_e\) 的有限性、积分范数；von Mises 仅称 proxy |
| 储能 | \(\Psi_m,\Psi_e,\Psi_n,\Psi_I,\Psi_{mat},\Psi_s\) 或可审计等价分解 |
| 功/耗散 | 主动功、腔面外载功、支撑功、drag 耗散、SLS 耗散、逐步/整周期闭合 |
| 数值 | DC/谐波残差、后向误差、矩阵谱/对称、周期一致性、资源 |

不得把规定自由短缩当作求解输出，也不得把 ECM von Mises proxy 当作三维等效应力。

### 13.2 `candidate_choice_for_supervisor` 阈值表

下表给出**前瞻候选值**，尚未被验证或接受。Supervisor 必须逐项接受、修改或删除后，
才能起草执行合同；不得把当前 `config.py/protocol.py` 默认值或 v08 PASS 自动视为接受。

| 编号 | 门 | 候选硬阈值 |
|---|---|---|
| N1 | G0 装配/结构 | UFL—手工相对 Frobenius \(\le10^{-6}\)；主动共轭多步长平台相对误差 \(\le10^{-7}\)；矩阵相对非对称 \(\le10^{-12}\)；制造作用—反作用 \(\le10^{-12}\) |
| N2 | G0 谱/刚体 | \(\lambda_{min}(K_{mat}+K_s)/\lambda_{max}>10^{-14}\)；应为半正定的矩阵满足 \(\lambda_{min}/\lambda_{max}\ge-10^{-12}\)；支撑后无未声明刚体零模 |
| N3 | G1 直接求解 | 非零 RHS 相对残差 \(\le10^{-10}\)；范数后向误差 \(\le10^{-12}\)；零 RHS 绝对残差与解范数 \(\le F_Q\)；无零 pivot/非有限值 |
| N4 | G2 时间 | 高于 floor 的 T128–T256 标量/波形/积分量误差 \(\le2\times10^{-3}\)，wrapped phase \(\le10^{-2}\) rad；误差严格下降；当两级**原始差范数**均 \(>10F_Q\) 时 \(p_t\ge1.5\) |
| N5 | G3 空间 | S3–S4 全局 QoI \(\le2\times10^{-2}\)；误差序列满足 \(e_{34}\le0.8e_{23}\)；公共牵引场阈值由 N7 单列 |
| N6 | G4 联合 | fine-space 时间增量满足 N4、fine-time 空间增量满足 N5；对已按第 5 节归一化的量，\(\delta_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12})\) |
| N7 | G5 投影/场 | 解析常量/线性场分量与合力误差 \(\le10^{-12}\)；原生—公共合力/功率相对误差 \(\le10^{-10}\)；S3–S4 公共牵引场 \(d_2\le5\times10^{-2}\) |
| N8 | G5 热点 | \(\eta_h=0.01\)；非退化热点周期 Hausdorff 距离 \(\le L/32\)，集合 Jaccard \(\ge0.5\)，峰值幅值相对差 \(\le5\times10^{-2}\) |
| N9 | G6 功率 | 每步 ledger-minus-equilibrium 相对差 \(\le10^{-10}\)；每步归一闭合残差 \(\le10^{-8}\)；整周期闭合 \(\le10^{-8}\)；每步 drag/SLS 耗散 \(\ge-10^{-12}S_W\) |
| N10 | G7 周期 | \(q,z\)、两界面牵引和能量的 cycle-1/cycle-2 归一差 \(\le10^{-10}\)；输入周期端点在机器精度内一致 |
| N11 | 资源 | 单 CPU 进程、8 GiB、3600 s；任一越界立即 `RESOURCE_LIMIT_FAIL` |

特别说明：当前实现默认的直接相对残差 `1e-7`、后向误差 `1e-12`、功率 `1e-8`、
离散闭合 `1e-10`、周期状态 `1e-3` 等，只是活跃代码现状。N1–N11 是为新 Figure 2
提出的候选门，二者不一致处必须由 Supervisor 明确裁决并在后续实现合同中解决，不能
静默选择较宽者。

### 13.3 不得事后放宽

一旦 Supervisor 接受阈值并生成 digest：

- 不得在看到任何开发或留出结果后提高阈值、改变 floor、删 QoI 或换参考层；
- 不得用均值 PASS 覆盖任一病例/分量/界面硬失败；
- 不得把 `BELOW_RESOLUTION_FLOOR`、`PHASE_UNDEFINED_LOW_AMPLITUDE` 或
  `HOTSPOT_DEGENERATE` 伪装为数值零；
- 如确需修改，必须冻结失败包、另立版本并重新指定独立留出。

## 14. G6 — 功率和耗散闭合

每个正式端点必须使用 Figure 1 接受的精确离散增量：

\[
W_a+W_L+W_s-\Delta_d\Psi_{mat}-D_{drag}-D_{SLS}=W_{eq\ defect}.
\]

必须同时检查：

1. `ledger residual - equilibrium defect work`，验证账本与离散平衡代数一致；
2. 原始逐步闭合残差，验证求解器误差未被恒等式抵消；
3. drag 与 SLS 耗散逐步非负及整周期积分；
4. \(\Psi_I\) 已包含在物质自由能中，界面 penalty 不可另记为耗散；
5. 支撑作为外部保守端口与把 \(\Psi_s\) 纳入总储能的两种分区给出相同整周期结果；
6. 端点能量直接相减只作 sidecar；不得替代精确中点增量；
7. 两界面公共投影功率与原生积分功率在 N7 内一致。

所有分母使用第 5 节 floor 规则。不得以某一步总功接近零导致的任意大相对数直接判定，
也不得省略该步；必须同时报告有量纲绝对残差和按预注册 \(S_W\) 缩放的残差。

## 15. G7 — 周期稳态一致性与主张边界

当前 `_periodic_solution` 直接解 DC 与单频 Crank–Nicolson 谐波系统，再构造两个周期。
因此 G7 只能验证：

- 周期边界、相位采样和两周期状态/牵引/能量一致；
- DC 与谐波方程残差通过 G1；
- 周期总储能变化与功率积分闭合；
- ECM 内变量 \(z\) 与全部物理场在周期端点一致。

这种一致性主要由周期谐波表示构造保证，不能称为“从任意初值经过若干周期收敛到极限
环”。若论文需要后者，必须另立瞬态积分、初值集合、收敛周期数和吸引性合同。

## 16. 结果、数组和 provenance 合同

### 16.1 create-only 目录

未来执行目录固定为

```text
results/paper2_figure2/
  fem_only_numerical_credibility_v01_YYYYMMDD_<run_id>/
```

`run_id` 必须在执行授权中冻结。目录若已存在即 `OUTPUT_PATH_EXISTS_FAIL`，不得覆盖、
删除、清空、移动或复用。失败尝试原位保留 `failure_summary.json`，不改名为 PASS。

### 16.2 最小正式文件

| 文件 | 内容 |
|---|---|
| `manifest.json` | schema、合同/阈值/病例 digest、环境、状态和证据边界 |
| `gate_summary.json` | G0–G7 与 hold-out 的逐项值、阈值、PASS/FAIL/NA 理由 |
| `case_matrix.json` | 实际端点、角色和开发/留出分区 |
| `algebraic_audit.json` | 残差、后向误差、谱、pivot、零 RHS |
| `convergence_audit.json` | 时间、空间、四角交互、floor 和观察阶 |
| `projection_audit.json` | 两界面两分量、原生/公共合力和功率、热点退化 |
| `power_audit.json` | 逐步与整周期账本、耗散和分区一致性 |
| `periodic_audit.json` | 两周期一致性及其“by construction”标签 |
| `holdout_audit.json` | C0 解盲结果；此前文件哈希锁 |
| `resource_audit.json` | 时间、峰值内存、CPU、容器隔离 |
| `provenance.json` | Git、源码锁、容器与命令参数 |
| `hash_ledger.json` | 除自身外正式文件的相对路径、字节数与 SHA-256 |

JSON 必须 UTF-8、排序键、禁止 NaN/Infinity。`hash_ledger.json` 不自我哈希。

### 16.3 数组最小化

只允许一个可选压缩数组包 `common_observables.npz`，且：

- 禁止 pickle/object dtype；
- 只含正式比较所需的 32×64 公共牵引场、核心一周期波形、必要的逐步功率数组和坐标；
- 不保存全状态矩阵、系统矩阵、重复第二周期、每步 ECM 全场或可由同一数据重建的副本；
- 每个数组在 `manifest.json` 中登记键、shape、dtype、物理方向、病例/端点和 SHA-256；
- 若 JSON 标量/范数已足以审计失败，不为失败门额外生成大 NPZ。

## 17. 容器、资源和事务边界

候选正式环境沿用活动 FEM-only v08 的可复现容器锚点，但不继承其数值结论：

- image tag：`dolfinx/dolfinx:v0.11.0`；
- expected image ID：
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- `--network none`，不挂载 Docker socket，不使用 GPU；
- 单 CPU/进程，BLAS/OpenMP/PETSc 线程数均为 1；
- 内存与总墙钟候选门见 N11；
- 源码与合同只读挂载，唯一可写挂载为新 create-only 结果目录；
- 固定随机种子只用于制造/谱审计，不参与物理解；
- 任一异常、超时、内存越界或进程非零退出均 fail closed，不自动重试。

容器镜像 ID 若不匹配，不得自动 pull 或换 tag；返回 `CONTAINER_ID_MISMATCH_FAIL` 等待
新授权。

## 18. FAIL 标签和裁决

| 标签 | 触发条件 |
|---|---|
| `SOURCE_OR_PROTOCOL_DRIFT_FAIL` | Git、源码、角色、病例、阈值或 runner 前后漂移 |
| `RETIRED_ROUTE_REINTRODUCED_FAIL` | 出现心肌 DCM、representation、identity 或旧包运行依赖 |
| `MISSING_VALIDATION_INTERFACE_FAIL` | 第 2.2 节任一必需接口缺失 |
| `STATIC_OR_MANUFACTURED_FAIL` | G0 任一结构、patch、谱或作用反作用门失败 |
| `ALGEBRAIC_FAIL` | G1 残差、后向误差、pivot 或有限性失败 |
| `TIME_DISCRETIZATION_FAIL` | G2 终局误差、下降方向或适用观察阶失败 |
| `SPACE_DISCRETIZATION_FAIL` | G3 终局误差、下降方向或符号稳定失败 |
| `JOINT_TRIGGER_FAIL` | G4 fine-corner 或交互缺陷失败 |
| `COMMON_PROJECTION_FAIL` | G5 坐标、合力、功率、分量或场范数失败 |
| `HOTSPOT_DEGENERATE` | 热点不唯一/不突出；禁止位置主张，不必自动否定其他 QoI |
| `POWER_LEDGER_FAIL` | G6 逐步/周期闭合、耗散或能量分区失败 |
| `PERIODIC_CONSISTENCY_FAIL` | G7 周期状态、牵引、内变量或能量不一致 |
| `HOLDOUT_FAIL` | 锁定后的 C0 任一适用门失败 |
| `OUTPUT_PATH_EXISTS_FAIL` | create-only 目录已存在 |
| `CONTAINER_ID_MISMATCH_FAIL` | 正式镜像 ID 不符 |
| `RESOURCE_LIMIT_FAIL` | CPU、内存、墙钟或隔离边界失败 |
| `NONFINITE_OUTPUT_FAIL` | 任一正式标量/数组为 NaN 或 Infinity |
| `POST_HOC_GATE_CHANGE_FAIL` | 看结果后改阈值、floor、病例、QoI 或参考层 |

任一硬 FAIL 后最终标签只能是相应失败标签；不得同时写 PASS。只有 G0–G7、资源、源锁
和 C0 留出全部通过，才可生成候选标签
`FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V01`，且仍须独立 Supervisor 与人类终审。

## 19. Figure 2 面板合同（本轮不制图）

| 面板 | 内容 | 必须显示的证据边界 |
|---|---|---|
| a | G0→G7→hold-out 验证梯；固定 FEM-only 三层角色 | v08 迁移等价不在收敛梯内 |
| b | S3 上 T64/T128/T256 的误差、观察阶和 phase | T256 是有限参考，不是连续极限 |
| c | T128 上 S2/S3/S4 的误差和参考方向 | 必须同时展示 e23/e34，禁止单网格图 |
| d | S3/S4×T128/T256 四角联合触发 | 分别 PASS 不替代联合 PASS |
| e | 两界面、两分量的 32×64 公共投影、合力/功率守恒与 S1 热点规则 | 热点退化时不画唯一热点 |
| f | 逐步功率闭合、drag/SLS 耗散、周期一致性和 C0 留出 | 周期一致性是 harmonic by construction，不是吸引极限环证明 |

任何面板只能在相应门通过后制作；失败时应展示失败证据或删除该主张，不得只展示最
平滑/最好看的病例。

## 20. Nature Physics 战略标准与剩余缺口

Figure 2 即使全部通过，也只说明当前理想化三层系统在所选有限离散阶梯上数值可信。
它不会自动产生普适物理。Nature Physics 仍只是战略设计标准；后续至少还需：

1. Figure 3 的简洁 \(De\times H\) 传递律、反例和独立留出；
2. 规律跨边界、几何方向和模型层级的稳健性；
3. Figure 4 的主动 FEM 家族粗粒化共同极限及增量预测；
4. 参数可辨识性和替代机制排除；
5. 真实几何或独立实验验证。

若 Figure 2 只能证明常规收敛，它是必要的可信度基础，不是 Nature Physics 级核心发现。

## 21. Supervisor 必须裁决的问题

合同执行前，Supervisor 必须逐项裁决：

1. N1–N11 的候选硬阈值，尤其是直接残差 `1e-10` 与当前实现 `1e-7` 的冲突；
2. G0 的谱门是要求 \(K_{mat}+K_s\) 严格正定，还是按显式零空间采用半正定审计；
3. G4 交互缺陷的定义和 `0.5` 系数是否足以支持联合稳定主张；
4. 公共 32 空间段 × 64 相位段是否接受为三阶梯共同定义域；
5. 热点集合 \(\eta_h=0.01\)、Hausdorff/Jaccard/幅值门是否接受；
6. 3600 s、8 GiB、单 CPU 的总事务预算是否接受；
7. 单个最小 `common_observables.npz` 是否为可复核性所必需；
8. C0 四角是否足以作为独立留出，或需另加一个未用于调门的派生 QoI。

未裁决项统一标记 `candidate_choice_for_supervisor`。不得把本草案状态解释为执行授权。

## 22. 停止边界

本合同新增后立即停在 Supervisor Gate。本轮以及合同未被接受前，均不授权：

- solver、Docker、数值试跑、参数扫描或 Figure 2 制图；
- 代码、测试、CURRENT_STATUS、Figure 1、结果或旧证据修改；
- Figure 3、三维、整心房、流体/CFD/FSI、实验拟合或 GPU；
- Git add、commit、push、发布或远端操作。
