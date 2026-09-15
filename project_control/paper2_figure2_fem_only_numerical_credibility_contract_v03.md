---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V03
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: ade5f96d7b89a6ed6b629a37db795ed08853ba3f
baseline_upstream_ahead_behind: 0/0
supersedes: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02.md
source_review: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02_supervisor_review_v01.md
source_review_disposition: NUMERICAL_DESIGN_MINOR_REVISION_REQUIRED
accepted_figure1: project_control/paper2_figure1_three_layer_theory_contract_v02.md
accepted_figure1_sha256: a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_numerical_credibility_contract_not_execution_evidence
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度合同 v03

## 0. 修订目的、科学主张与本轮边界

本合同依据
`project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02_supervisor_review_v01.md`
修订 v02，只关闭两个剩余阻断：

1. 把联合验证拆成无环、fail-closed 的
   `G4a → G5 → G4b → G4 总裁决`，并同步病例矩阵、S1 留出、结果 schema、面板和
   最终 PASS；
2. 把 DC＋一阶谐波到 256 个公共 P0 相位段的值唯一冻结为**解析段平均**，禁止端点或
   中心点抽样；公共 L2、合力、热点和 G4b 全部使用同一段平均数组。

Figure 2 的唯一科学目的，是证明当前二维 FEM-only 三层模型在预注册有限离散阶梯上的
离散方程、代数求解、时间、空间、共同投影、功率账本和周期解具有可审计可信度。

Figure 2 不证明参数具有斑马鱼生理真实性，不证明 EFE、三维心房、流体或疾病机制，
也不验证后续 \(De\times H\) 普适规律。v08 的迁移等价只说明新包重现冻结旧 FEM 臂，
不是 Figure 2 收敛证据。

本轮只新增本合同，不运行 solver/Docker，不修改 v01/v02、两轮 Supervisor 审阅、
Figure 1、CURRENT_STATUS、源码、测试、结果或旧材料，也不执行 Git 暂存、提交或推送。

## 1. 唯一活跃对象与源码锁

### 1.1 固定角色和永久禁止路线

| 组织层 | 唯一活跃实现 |
|---|---|
| 心内膜 | `discrete_cell_chain` |
| 心肌 | `active_plane_strain_fem` |
| ECM | `viscoelastic_plane_strain_fem` |
| 流体 | `absent_in_v08` |

心肌 DCM 已永久退出活跃项目。禁止心肌 DCM comparator、representation 轴、DCM 缩放/
校准、identity 判据、旧 `paper2_m2` import 或 `GO/MAYBE/NO-GO ID` 路线。`D0` 只可作
固定 SuperLU 直接求解器的 provenance 标签，不是可调 tolerance 轴。

### 1.2 合同、审阅和源码锚点

| 对象 | SHA-256 |
|---|---|
| Figure 2 v01 | `4adf514b242610f320e52f0efca0fbb04e3ee1a2525460c3092b4657836f001f` |
| Figure 2 v02 | `ebbf03fd06142021f658cbb834295cbed9e615890564e776c01234d8a1b3fe7c` |
| v02 Supervisor 审阅 | `57a3675d3e62a7203087f9c8886bd422489d9a1fc3bd778cb5acf3c909d808f9` |
| `src/paper2_hybrid/__init__.py` | `4626ee6f49cac099734728fe0dc2f3412ded11cf5066b32aff556cc39324783f` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/projection.py` | `3bd590f0deef1fbe47cfdf01dea48664b25ff5a8716a546e4758bc4a0642176c` |
| `src/paper2_hybrid/protocol.py` | `f96d779cfcd6c76e9535f90a9941a6156b545d53a0270f04a564c68a304fe3ca` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |
| `src/paper2_hybrid/validation.py` | `6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5` |

未来若获准新增 runner、验证模块或测试，执行合同必须把新增文件加入源锁并保持上述
核心模型文件不变；若确需改核心模型，必须另立模型变更合同，本合同失效。

### 1.3 运行前后锁

每次未来正式尝试必须在运行前、运行后记录：

1. Git HEAD/upstream、ahead/behind 和 scoped status；
2. 活跃包、测试、获批合同、runner 的字节数与 SHA-256；
3. 固定角色、配置、病例矩阵、N1–N11、公共域、门禁 DAG 和留出封存 digest；
4. 容器镜像 ID、Python/FEniCSx/PETSc/SciPy/NumPy 版本；
5. CPU、内存、网络、GPU 和 Docker socket 状态。

任一前后锁不一致即 `SOURCE_OR_PROTOCOL_DRIFT_FAIL`，不得生成 PASS。

## 2. 现有接口与执行前必须补齐的验证接口

### 2.1 已存在但尚未构成 Figure 2 证据

- `HybridConfig` 定义 S2/S3/S4、T64/T128/T256 和病例；
- `build_system` 装配主动心肌 FEM、SLS ECM、离散链、双界面和支撑；
- `direct_solver_assurance` 给出直接残差与范数后向误差；
- `discrete_ledger` 给出精确中点能量增量、功、耗散和闭合；
- 当前空间投影器支持原生分片线性场到嵌套较粗 P0 段；
- `global_structural_checks` 检查角色、装配、对称、支撑和主动共轭；
- `simulate_endpoint` 输出两周期位移、牵引、ECM 场和功率数组。

这些接口的存在不是通过证据。

### 2.2 执行合同必须授权补齐，但本轮不实现

1. 任意原生分片线性空间场到 128 个目标 P0 段的解析分段积分，包括从较粗原生段到
   更细目标段；
2. 从 DC/一阶谐波系数计算 256 个公共相位 P0 **解析段平均**，不允许采样近似；
3. 把原生逐步功/耗散按时间区间交叠守恒分配到 256 段，与单频解析段平均完全分路；
4. 两界面、两个物理力分量的独立输出与一侧存储/另一侧严格取负映射；
5. 真实零 RHS、连续体/链 affine patch、SLS DC/离散谐波制造解；
6. 正对角对称缩放后的矩阵惯性、特征值、零空间和刚体模态审计；
7. 通用 floor、零分母、phase wrapping、热点集合和 S1 封存/解盲；
8. S2/S3/S4、T64/T128/T256、G4a 和 G4b 的统一比较器；
9. create-only runner、强制数组包、结果 manifest 与 hash ledger。

若未来执行未补齐任一接口，在 G0 前以 `MISSING_VALIDATION_INTERFACE_FAIL` 停止，禁止
手工摘录或旧结果替代。

## 3. 病例矩阵、开发集和 S1 独立留出

### 3.1 病例角色

| 病例 | 驱动 | Figure 2 角色 |
|---|---|---|
| `P0` | 零主动、零外载 | 零驱动、噪声 floor；另须真实零 RHS 求解 |
| `P1` | 给定微小 affine 宏观应变 | 被动切线与 patch 辅助；不是完整耦合平衡解 |
| `A2` | 均匀纯主动 | 纯主动开发病例 |
| `LN` | 纯法向规定载荷 | 单输入法向开发病例 |
| `LS` | 纯切向规定载荷 | 单输入切向开发病例 |
| `C0` | 均匀主动 + 同相法向载荷 | 同相多输入开发病例 |
| `CQ` | 均匀主动 + 相差 \(\pi/2\) 的法向载荷 | 正交多输入开发病例 |
| `S1` | 空间异质纯主动 | **独立留出**，规则 digest 后才解盲 |
| `A1` | 当前与 `A2` 代数输入相同 | 输入别名审计，不重复计证据 |

开发集固定为 `A2/LN/LS/C0/CQ`。`C0/CQ` 只作同相/正交多输入开发病例，不称独立
新物理。`A1/A2` 不得重复计数。

### 3.2 无环分层运行矩阵

| 阶段 | 病例 | 空间/时间端点 | 用途与放行关系 |
|---|---|---|---|
| G0 | P0、P1、制造解 | S2/S3/S4，静态 | 源、装配、patch、谱、零驱动；PASS 后到 G1 |
| G1 | P0、A2、LN、LS、C0、CQ | 先 S2/T64；每个端点自动检查 | 直接代数；PASS 后到 G2 |
| G2 | A2、LN、LS、C0、CQ | S3 × T64/T128/T256 | 时间；PASS 后到 G3 |
| G3 | A2、LN、LS、C0、CQ | S2/S3/S4 × T128 | 空间全局量；PASS 后到 G4a |
| G4a | A2、LN、LS、C0、CQ | S3/S4 × T128/T256 | 标量/积分/无需跨网格对应的波形混合差；PASS 后到 G5 |
| G5 | 同一开发集 | 复用阶梯与四角 | 128×256 投影、守恒、场收缩；PASS 后到 G4b |
| G4b | 同一开发集 | 四角共同场 | 公共牵引场混合差；PASS 后形成 G4 总裁决 |
| G4 | 汇总门 | G4a + G5 + G4b | 三者全 PASS 才放行 G6 |
| G6 | 同一开发集 | 全部正式端点 | 功率与耗散；PASS 后到 G7 |
| G7 | 同一开发集 | 全部正式端点 | harmonic 周期一致性；PASS 后锁 digest |
| Hold-out | S1 | S3/S4 × T128/T256 | 按同一子门顺序解盲 |

任何子门失败均停止，不存在 G4 等待后续门却提前写 PASS 的状态。

### 3.3 留出封存和解盲

在任何 S1 求解前必须生成不可变 `pre_holdout_digest.json`，至少哈希：

- 本合同、后续获批执行合同和 runner；
- N1–N11、floor、相位、128×256 解析段平均、热点和门禁 DAG；
- 开发集 G0、G1、G2、G3、G4a、G5、G4b、G4、G6、G7 的全部结果；
- S1 四角、QoI、子门顺序和 PASS/FAIL 规则；
- 数组 schema、资源门和容器 ID。

S1 只能在开发集上述全部门通过后执行。失败只能标 `S1_HOLDOUT_FAIL` 并冻结结果；
不得修改规则后在同版本重跑并继续称独立留出。

## 4. 固定离散阶梯和 fine-reference 混合差

### 4.1 空间阶梯

| 标签 | \(n_x\) | 每连续层 \(n_y\) | 角色 |
|---|---:|---:|---|
| S2 | 32 | 8 | 粗层 |
| S3 | 64 | 16 | 中层、时间门固定层 |
| S4 | 128 | 32 | 当前最细空间参考 |

网格逐级 2 倍嵌套，对角固定 `lower_left_to_upper_right`。必须同时报告

\[
e_{23}=d(Q_{S2},Q_{S3}),\qquad e_{34}=d(Q_{S3},Q_{S4}).
\]

S4 是有限参考，不是连续极限。

### 4.2 时间阶梯

| 标签 | 每周期步数 | \(\Delta t/T\) | 角色 |
|---|---:|---:|---|
| T64 | 64 | 1/64 | 粗层 |
| T128 | 128 | 1/128 | 中层、空间门固定层 |
| T256 | 256 | 1/256 | 当前最细时间参考 |

必须同时报告

\[
e_{64,128}=d(Q_{T64},Q_{T128}),\qquad
e_{128,256}=d(Q_{T128},Q_{T256}).
\]

T256 是有限参考，不是连续时间解。

### 4.3 四角与混合差

G4a、G4b 和 S1 留出均使用

\[
(S3,T128),\ (S3,T256),\ (S4,T128),\ (S4,T256).
\]

定义

\[
\Delta_{st}Q=
Q_{S4,T256}-Q_{S3,T256}-Q_{S4,T128}+Q_{S3,T128}.
\]

标量采用

\[
e_{st}^{(s)}=
\frac{|\Delta_{st}Q|}{\max(|Q_{S4,T256}|,F_Q)},
\]

共同域波形/场采用

\[
e_{st}^{(2)}=
\frac{\|\Delta_{st}Q\|_{L^2(\mathcal D_c)}}
{\max(\|Q_{S4,T256}\|_{L^2(\mathcal D_c)},F_Q\sqrt{|\mathcal D_c|})}.
\]

同一 S4/T256 参考用于 \(e_t^{S4}\) 和 \(e_s^{T256}\)，冻结门

\[
e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12}).
\]

参考低于 floor 时不构造相对交互比，只用 \(|\Delta_{st}Q|\le F_Q\) 或对应场绝对门。

## 5. 特征尺度、floor、相位和热点

### 5.1 特征尺度与绝对 floor

| QoI 类 | 特征尺度 \(S_Q\) |
|---|---|
| 位移 | \(S_u=a_0L\) |
| 应变、内部变量、宏观/自由缩短 | \(S_\epsilon=a_0\) |
| 牵引/应力 | \(S_t=E_\infty a_0\) |
| 广义力、右端和代数残量 | \(S_f=E_\infty a_0L\) |
| 每单位厚度储能/功 | \(S_W=E_\infty a_0^2L^2\) |
| 功率 | \(S_P=S_W/T\) |

噪声 \(N_Q\) 只来自同算子的真实零 RHS 直接求解，冻结

\[
F_Q=\max(10^{-12}S_Q,10N_Q).
\]

不得用 `1e-30`、非零病例或 S1 结果定义 floor。

### 5.2 标量、共同波形和场误差

\[
d_s(q,r)=\frac{|q-r|}{\max(|r|,F_Q)},
\]

\[
d_2(q,r)=
\frac{\|q-r\|_{L^2(\mathcal D_c)}}
{\max(\|r\|_{L^2(\mathcal D_c)},F_Q\sqrt{|\mathcal D_c|})}.
\]

参考不高于 floor 时记录 `BELOW_RESOLUTION_FLOOR`，不计算相对误差或观察阶；只有绝对
差不高于 floor 才通过。不得返回伪 0、NaN 或 Inf。

### 5.3 相位

相位只在输入和输出一阶谐波幅值均高于 \(10F_Q\) 时定义：A2 相对主动输入，LN 相对
法向载荷，LS 相对切向载荷，C0/CQ 相对主动时钟并另记载荷相位，S1 相对主动输入。
多输入病例不称单一传递函数。

\[
\Delta\phi=\operatorname{atan2}
[\sin(\phi_1-\phi_2),\cos(\phi_1-\phi_2)]\in[-\pi,\pi].
\]

低幅信号标 `PHASE_UNDEFINED_LOW_AMPLITUDE`，不强置为零。

### 5.4 S1 留出热点

热点只在以主动幅值峰值 \(t=T/2=t_{128}\) 为中心的公共 P0 相位段上评估。按第 12.2 节
周期半开区间约定，\(I_{128}=[T/2-T/512,T/2+T/512)\)；热点场使用该段的
**解析平均**，不是 \(t=T/2\) 点采样。

对心肌侧轴向物理牵引 \(t_{e\to m,x}=-t_{me,x}^{rep}\) 的 128 个空间段平均值 \(t_k\)，
冻结

\[
\mathcal H=\{k:t_k\le t_{min}+0.05(t_{max}-t_{min})\}.
\]

场范围必须 \(>10F_t\)，热点覆盖不超过周期域 25%；否则标 `HOTSPOT_DEGENERATE`，只
禁止唯一热点主张。非退化时使用周期距离

\[
d_L(x,y)=\min(|x-y|,L-|x-y|)
\]

计算长度加权 Hausdorff 与 Jaccard。

## 6. 唯一无环 fail-closed 顺序

```text
G0 静态/制造
  -> G1 代数
  -> G2 时间
  -> G3 空间全局量
  -> G4a 标量/周期积分/无需跨空间网格对应的波形混合差
  -> G5 128×256 公共域投影、守恒与场收缩
  -> G4b 公共牵引场混合差
  -> G4 总裁决
  -> G6 功率与耗散
  -> G7 harmonic 周期一致性
  -> pre_holdout_digest
  -> S1-G1 -> S1-G4a -> S1-G5 -> S1-G4b -> S1-G4 -> S1-G6 -> S1-G7
  -> Supervisor Gate
```

G4 不是可执行子门；它只在 G4a、G5、G4b 全部 PASS 后汇总为 PASS。任一子门失败立即
停止，不允许越过失败门继续，也不存在“待 G5 后补齐”的暂时 G4 PASS。

## 7. G0 — 静态、制造和矩阵结构

### 7.1 制造检查

在 S2/S3/S4 上执行：

1. 源码、角色、病例、阶梯、公共域、门禁 DAG 与禁用符号审计；
2. UFL—手工 \(B^TCB\) 相对 Frobenius 误差 \(\le10^{-10}\)；
3. 连续体/链 affine patch 相对误差 \(\le10^{-10}\)；
4. SLS DC 与当前 CN 离散谐波解析响应相对误差 \(\le10^{-10}\)，不混入连续时间误差；
5. 主动共轭多步长中心差分平台最优相对误差 \(\le10^{-7}\)；
6. 矩阵相对非对称与制造作用—反作用均 \(\le10^{-12}\)；
7. 真实零 RHS 直接求解残量与解范数不高于 floor。

`P0` 旁路数组和 `P1` 人工宏观应变不能单独替代真实求解与 patch。

### 7.2 正对角缩放、惯性与刚体模态

对实对称矩阵 \(A\) 取正对角 \(D_A=\operatorname{diag}(A)\)，构造

\[
\widehat A=D_A^{-1/2}AD_A^{-1/2}.
\]

任一应缩放对角非正即失败。对仅作用于边界的 \(K_s\)，缩放限制在受支撑自由度子空间；
其余零对角为已声明设计核，完整未缩放 \(K_s\) 仍审计半正定惯性。

- \(K_{mat}\) 对称半正定，缩放最小特征值 \(\ge-10^{-10}\)，且恰有两个共同刚体
  平移零模；零模为 \(|\lambda|\le10^{-10}\lambda_{max}\)；
- \(K_s\) 半正定并允许已声明设计核；
- \(K_{mat}+K_s\) 严格 SPD，缩放 \(\lambda_{min}/\lambda_{max}>10^{-12}\)；
- \(G\) 严格 SPD，缩放 \(\lambda_{min}/\lambda_{max}>10^{-12}\)；
- 复谐波矩阵只验可逆性、残差和后向误差，不称 SPD。

零模数不符即 `MATRIX_INERTIA_FAIL`，不得静默改零阈值。

## 8. G1 — 固定直接代数求解器

`scipy_superlu` 分别求 DC 实系统和单频复系统。每端点必须满足：

- 非零 RHS 二范数相对残差 \(\le10^{-10}\)；
- 范数后向误差
  \(\|r\|_\infty/(\|A\|_\infty\|q\|_\infty+\|b\|_\infty)\le10^{-12}\)；
- 零 RHS 使用绝对 floor；
- 无零 pivot、非有限值或不可逆系统；
- DC/复谐波矩阵、RHS 和结果分别登记。

当前代码 `1e-7` 是宽松默认；正式 runner 独立使用 `1e-10` 验收，不改变 SuperLU 内部
tolerance，也不虚构 tolerance 轴。迭代求解器必须另立合同。

## 9. G2 — 时间离散

固定 S3，对 A2/LN/LS/C0/CQ 计算 T64/T128/T256。比较宏观短缩、心内膜位移、界面
合力波形、谐波幅相、周期储能/功/耗散积分、ECM 内变量与原生积分范数。

高于 floor 的 T128–T256 标量、波形和积分误差 \(\le2\times10^{-3}\)，相位差
\(\le10^{-2}\) rad；误差必须下降；两级原始差均高于 \(10F_Q\) 时

\[
p_t=\log_2(e_{64,128}/e_{128,256})\ge1.5.
\]

峰值只作 sidecar，不替代波形。该门验证 CN 离散周期响应细化，不验证非正弦瞬态积分。

## 10. G3 — 空间离散全局量

固定 T128，对 A2/LN/LS/C0/CQ 计算 S2/S3/S4。G3 只比较无需公共空间逐段对应的全局
QoI、边界合力和原生积分范数；共同牵引场在 G5 检查。

高于 floor 的 S3–S4 全局 QoI \(\le2\times10^{-2}\)，且

\[
e_{34}\le0.8e_{23}.
\]

不得用全局均值覆盖场失败，也不得以 S4 图片更平滑作为通过理由。

## 11. G4a — 预投影联合混合差

对开发集四角的标量、周期积分量及无需跨空间网格逐点对应的波形，使用第 4.3 节同一
S4/T256 参考和 floor，检查：

1. S4 上 T128→T256 边际误差满足 G2 终局门；
2. T256 上 S3→S4 边际误差满足 G3 终局门；
3. \(e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12})\)；
4. 相位、符号与物理解释四角一致；
5. 所有端点保持 G1、有限性与功率预检。

G4a PASS 只放行 G5，不得写 G4 PASS。

## 12. G5 — 128×256 公共域、解析段平均、守恒与场收缩

### 12.1 公共空间 P0 段

空间域 \([-L/2,L/2]\) 划分为 128 个等长半开 P0 段，最右周期端点只用于闭合，不
重复计权。S2/S3/S4 原生分片线性场在每个目标段上解析切分并积分平均；目标段更细时
仍积分原生线性插值，不得重复值或点抽样。

### 12.2 公共相位 P0 解析段平均

令

\[
\Delta t_c=\frac{T}{256},\qquad
t_j=j\Delta t_c,\qquad
\widetilde I_j=[t_j-\Delta t_c/2,t_j+\Delta t_c/2),\qquad
I_j=\widetilde I_j\pmod T,\quad j=0,\ldots,255.
\]

这些以 \(t_j\) 为中心的等长 P0 段在周期圆上无重叠覆盖一周；\(I_0\) 跨越
\(T\equiv0\) 周期边界，但边界只用于闭合，不重复计权。解析积分可在展开区间
\(\widetilde I_j\) 上计算，因为被积场严格周期。
对任一单频标量或空间位置上的场

\[
Q(t)=Q_0+\operatorname{Re}(\widehat Q_1e^{i\omega t}),
\qquad \omega=2\pi/T,
\]

公共 P0 段值唯一冻结为解析段平均

\[
Q_j=\frac{1}{\Delta t_c}
\int_{t_j-\Delta t_c/2}^{t_j+\Delta t_c/2}
\left[Q_0+\operatorname{Re}(\widehat Q_1e^{i\omega t})\right]dt
=Q_0+\operatorname{Re}\!\left[
\widehat Q_1 e^{i\omega t_j}
\frac{2\sin(\omega\Delta t_c/2)}{\omega\Delta t_c}\right].
\]

严禁用左/右端点、段中心或任意节点抽样替代该积分。空间—时间场的公共值是 128 个
空间解析段平均与上述时间解析段平均的张量积；两种线性积分次序必须给出同一结果。

公共一周期 L2 唯一使用

\[
\|Q\|_{L^2(\mathcal D_c)}^2
=\sum_{k=0}^{127}\sum_{j=0}^{255}
\Delta x_c\Delta t_c\,|Q_{k,j}|^2.
\]

公共合力在每个相位段使用 \(\sum_k\Delta x_c\,\mathbf t_{k,j}\)。G4b 的四角场、
N7 场收缩和 S1 热点全部使用同一 `Q[k,j]` 解析段平均数组，不得另建点采样旁路。

峰值相位 \(t=T/2=t_{128}\) 是 \(I_{128}\) 的中心；S1 热点使用以该峰值为中心的
\(Q_{k,128}\) 解析段平均并明确标记 `peak_phase_bin_average`，不冒充精确点值。

对原生周期数组做 Fourier 审计。若 \(\widehat Q_k\) 为系数，则

\[
\left(\sum_{|k|>1}|\widehat Q_k|^2\right)^{1/2}
\le F_Q\sqrt{|\mathcal D_c|};
\]

否则 `UNEXPECTED_HIGHER_HARMONIC_FAIL`，不得用单频重建隐藏高次成分。

### 12.3 逐步功/耗散的独立区间交叠映射

\(W_a,W_L,W_s,D_{drag},D_{SLS}\) 是原生时间单元上的步积分量，禁止套用第 12.2 节
单频公式。每个原生步量除以其 \(\Delta t\) 得到守恒密度，再按原生区间与 256 个目标
段的交叠长度分配；所有目标段总和必须严格复原原生整周期量。

目标段沿用第 12.2 节中心化周期分段。计算交叠时把 \(I_0\) 唯一拆为
\([0,T/512)\cup[T-T/512,T)\)，分别与原生半开区间求交后相加；周期边界不得遗漏或
重复权重。

界面功率密度先在原生空间—时间单元上积分，再走同一交叠守恒映射。禁止平均牵引乘
平均速度，禁止把逐步功/耗散傅里叶重建成单频。

### 12.4 两界面两分量和场收缩门

只投影并保存一个界面侧的物理力，另一侧由 manifest 严格取负。每个界面、每个分量
必须分别满足：

- 常量/线性制造场及合力误差 \(\le10^{-12}\)；
- 原生—公共合力与功率误差 \(\le10^{-10}\)；
- 开发集 S3–S4 公共牵引场 \(d_2\le5\times10^{-2}\)；
- 高于 floor 时 \(d_{34}\le0.8d_{23}\)；
- 不用合并范数覆盖单项失败。

G5 PASS 只放行 G4b，不得提前形成 G4 总 PASS。

## 13. G4b 与 G4 总裁决

### 13.1 G4b 公共牵引场混合差

G5 PASS 后，对开发集两界面、两分量的 128×256 解析段平均场，按第 4.3 节计算
\(\Delta_{st}Q\)、\(e_t^{S4}\)、\(e_s^{T256}\) 和 \(e_{st}\)。每项必须满足：

\[
e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12}),
\]

且 fine-space 时间边际与 fine-time 空间边际分别满足 N4/N5/N7 的适用终局门。低于
floor 时只使用绝对混合差门。任一界面或分量失败即 `G4B_FIELD_MIXED_FAIL`。

### 13.2 G4 总裁决

G4 的状态由以下真值表唯一决定：

| G4a | G5 | G4b | G4 |
|---|---|---|---|
| PASS | PASS | PASS | PASS |
| 其他任一组合 | — | — | FAIL/NOT_REACHED |

G4 PASS 只支持“当前有限四角联合稳定”，不外推连续极限。只有 G4 PASS 才可执行 G6。

## 14. 核心 QoI 与 N1–N11

### 14.1 核心 QoI

| 类别 | 必须输出 |
|---|---|
| 宏观运动 | \(-\bar\epsilon(t)\)；规定自由短缩只作输入/比较器 |
| 心内膜 | 平均切向/法向位移波形和一阶谐波 |
| 双界面 | 四个物理作用力方向、两分量公共场、合力、空间—时间 L2 |
| 相位 | 单输入/多输入 wrapped phase |
| S1 热点 | `peak_phase_bin_average` 上最强压缩物理牵引集合、位置和幅值 |
| ECM | \(\epsilon_e,z,\sigma_e\) 有限性和积分范数；von Mises 只称 proxy |
| 储能 | \(\Psi_m,\Psi_e,\Psi_n,\Psi_I,\Psi_{mat},\Psi_s\) 或等价分解 |
| 功/耗散 | 主动、腔面、支撑功，drag/SLS 耗散，逐步和周期闭合 |
| 留出派生量 | S1 四角的 \(\chi_D\) |
| 数值 | 直接残差、后向误差、缩放谱/惯性、周期一致性、资源 |

不得把自由短缩输入当求解输出，不得把二维 von Mises proxy 当三维等效应力。

### 14.2 N1–N11 冻结硬门

| 编号 | 冻结设计 |
|---|---|
| N1 | 装配、affine patch、SLS DC/离散谐波制造解 \(\le10^{-10}\)；主动共轭 \(\le10^{-7}\)；非对称/作用反作用 \(\le10^{-12}\) |
| N2 | 正对角缩放；\(K_{mat}\) PSD 且恰有两个共同平移零模；\(K_{mat}+K_s\) 与 \(G\) 严格 SPD，缩放特征值比 \(>10^{-12}\)；PSD 最小缩放特征值 \(\ge-10^{-10}\) |
| N3 | 非零 RHS 相对残差 \(\le10^{-10}\)，后向误差 \(\le10^{-12}\)，零 RHS 用绝对 floor，无零 pivot/非有限值 |
| N4 | T128–T256 误差 \(\le2\times10^{-3}\)，相位 \(\le10^{-2}\) rad；高于 floor 时误差下降；适用时 \(p_t\ge1.5\) |
| N5 | S3–S4 全局 QoI \(\le2\times10^{-2}\)，高于 floor 时 \(e_{34}\le0.8e_{23}\) |
| N6 | G4a/G4b 均使用 S4/T256 的混合差 `0.5` 门；低于 floor 用绝对门 |
| N7 | 128×256 解析段平均；制造/合力 \(\le10^{-12}\)，原生—公共合力/功率 \(\le10^{-10}\)，场 \(d_2\le5\times10^{-2}\) 且适用时 \(d_{34}\le0.8d_{23}\) |
| N8 | S1 使用 `peak_phase_bin_average`；\(\eta_h=0.05\)，范围 \(>10F_t\)，覆盖 \(\le25\%\)，Hausdorff \(\le L/32\)，长度加权 Jaccard \(\ge0.5\)，峰值差 \(\le5\times10^{-2}\) |
| N9 | ledger-minus-equilibrium \(\le10^{-10}\)；逐步/周期闭合 \(\le10^{-8}\)；drag/SLS 步耗散 \(\ge-10^{-12}S_W\) |
| N10 | harmonic 两周期状态、牵引和能量一致性 \(\le10^{-10}\)，保留 by-construction 标签 |
| N11 | 单 CPU、峰值内存 \(\le8\) GiB、总墙钟 \(\le3600\) s，无网络/GPU/socket |

不得用 `config.py` 较宽默认值覆盖本表。

## 15. G6 — 功率与耗散

每个端点使用 Figure 1 已接受的精确离散恒等式

\[
W_a+W_L+W_s-\Delta_d\Psi_{mat}-D_{drag}-D_{SLS}=W_{eq\ defect}.
\]

必须满足：

- 每步 ledger-minus-equilibrium 相对差 \(\le10^{-10}\)；
- 每步和整周期归一闭合 \(\le10^{-8}\)；
- 每步 drag/SLS 耗散 \(\ge-10^{-12}S_W\)；
- 原生与公共功率积分差 \(\le10^{-10}\)。

\(\Psi_I\) 已含于物质能，界面 penalty 不另记耗散。支撑外端口与总能分区必须给出
同一周期结果。端点能量相减只作 sidecar，不替代精确中点增量。

## 16. G7 — harmonic 周期一致性

开发集每端点必须满足状态 \(q\)、SLS 内变量 \(z\)、两界面物理牵引和能量的两周期
归一差 \(\le10^{-10}\)，输入周期端点在机器精度内一致，周期能量变化与 G6 一致，
DC/谐波系统保持 G1。

结果必须标 `harmonic_periodic_solution_by_construction`，不能声称任意初值收敛到吸引
极限环。

## 17. S1 独立留出的同一无环子门

### 17.1 解盲顺序

digest 锁定后，S1 四角只能依次执行：

```text
S1-G1
  -> S1-G4a（标量/积分/波形）
  -> S1-G5（128×256 解析段平均、守恒、终局场与热点）
  -> S1-G4b（公共牵引场混合差）
  -> S1-G4（前三个子门汇总）
  -> S1-G6
  -> S1-G7
  -> S1 hold-out 总裁决
```

S1-G4a 使用终局时间误差 \(\le2\times10^{-3}\)、相位 \(\le10^{-2}\) rad、终局空间
全局量 \(\le2\times10^{-2}\) 和混合差 `0.5` 门。S1-G5 使用公共场
\(d_2\le5\times10^{-2}\)、热点 N8 及原生—公共守恒门。S1-G4b 对两界面两分量使用
同一解析段平均数组和 fine-reference 混合差。

S1 只有四角，不虚构 T64 观察阶或 S2→S3 场收缩。

### 17.2 耗散份额 \(\chi_D\)

\[
\chi_D=\frac{D_{SLS}}{D_{SLS}+D_{drag}}.
\]

仅当分母 \(>F_W\) 时定义；否则标 `CHI_D_UNDEFINED_LOW_DISSIPATION`，不强置 0 或 1。
定义时，在 S1-G4a 中检验时间终局差 \(\le2\times10^{-3}\)、空间终局差
\(\le2\times10^{-2}\) 和 fine-reference 混合差 `0.5` 门。该量不得在开发集上调门。

## 18. 强制结果与数组 schema

### 18.1 create-only 目录

未来正式目录：

```text
results/paper2_figure2/
  fem_only_numerical_credibility_v03_YYYYMMDD_<run_id>/
```

`run_id` 在执行授权中冻结。路径存在即 `OUTPUT_PATH_EXISTS_FAIL`，不得覆盖、删除、清空、
移动或复用。失败尝试原位保留，不能改名为 PASS。

### 18.2 正式文件

| 文件 | 内容 |
|---|---|
| `manifest.json` | schema、合同/规则/DAG digest、环境和证据边界 |
| `gate_summary.json` | 分别记录 G0、G1、G2、G3、G4a、G5、G4b、G4、G6、G7 与 S1 子门 |
| `case_matrix.json` | 端点、开发/留出分区和放行关系 |
| `algebraic_audit.json` | 残差、后向误差、缩放谱、惯性、pivot、零 RHS |
| `convergence_audit.json` | 时间、空间与 G4a 标量/积分/波形混合差 |
| `projection_audit.json` | 128×256 解析段平均、守恒、场收缩和高次谐波 |
| `g4b_field_mixed_audit.json` | 两界面两分量公共场四角混合差 |
| `g4_total_adjudication.json` | G4a/G5/G4b 真值表和 G4 总状态 |
| `power_audit.json` | 逐步/周期账本与独立交叠映射 |
| `periodic_audit.json` | 两周期一致性及 by-construction 标签 |
| `pre_holdout_digest.json` | S1 前规则、DAG 和开发结果哈希 |
| `s1_holdout_audit.json` | S1-G1/G4a/G5/G4b/G4/G6/G7、热点与 \(\chi_D\) |
| `resource_audit.json` | 墙钟、内存、CPU、隔离 |
| `provenance.json` | Git、源锁、容器、命令 |
| `common_observables.npz` | 强制公共数组包 |
| `hash_ledger.json` | 除自身外文件的路径、字节数和 SHA-256 |

JSON 必须 UTF-8、排序键、禁止 NaN/Infinity。`hash_ledger.json` 不自哈希。

### 18.3 强制数组包

`common_observables.npz` 必须存在且压缩后 \(\le128\) MiB：

- 单频共同波形/牵引只存第 12.2 节 128×256 解析段平均数组；
- 逐步功/耗散只存第 12.3 节区间交叠守恒数组，并以不同 key namespace 区分；
- 包含必要坐标、开发四角和 S1 四角；相位坐标明确登记为中心 \(t_j=jT/256\)，
  `phase_bin_bounds` 登记对应的周期圆半开段，\(I_0\) 的跨边界表示不得产生重复权重；
- 两侧物理力只存一侧，manifest 规定对侧严格取负；
- 禁止 object/pickle、全状态、系统矩阵、重复周期和逐单元 ECM 全场；
- 每数组登记键、shape、dtype、物理方向、病例/端点、生成路径和内容 SHA-256。

缺失、超 128 MiB、两类时间映射混用或存在未登记键即 `ARRAY_CONTRACT_FAIL`。

## 19. 容器、资源与事务边界

- `dolfinx/dolfinx:v0.11.0`；expected image ID
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 单 CPU/进程，BLAS/OpenMP/PETSc 线程均 1；
- 总墙钟 \(\le3600\) s，峰值内存 \(\le8\) GiB；
- `--network none`，无 Docker socket、无 GPU；
- 源码/合同只读，唯一可写挂载为新 create-only 结果目录；
- 随机种子只用于制造/谱审计；异常、超时、越界或非零退出立即 fail closed，不自动重试。

镜像 ID 不符时不得自动 pull 或换 tag，返回 `CONTAINER_ID_MISMATCH_FAIL`。

## 20. FAIL 标签与最终 PASS

| 标签 | 触发条件 |
|---|---|
| `SOURCE_OR_PROTOCOL_DRIFT_FAIL` | Git、源码、角色、病例、N1–N11、DAG 或 digest 漂移 |
| `RETIRED_ROUTE_REINTRODUCED_FAIL` | 心肌 DCM、representation、identity 或旧包运行依赖出现 |
| `MISSING_VALIDATION_INTERFACE_FAIL` | 第 2.2 节接口缺失 |
| `STATIC_OR_MANUFACTURED_FAIL` | G0 装配、patch、SLS、主动共轭或作用反作用失败 |
| `MATRIX_INERTIA_FAIL` | 缩放谱、两个平移零模或 SPD 失败 |
| `ALGEBRAIC_FAIL` | G1 残差、后向误差、pivot 或有限性失败 |
| `TIME_DISCRETIZATION_FAIL` | G2 时间门失败 |
| `SPACE_DISCRETIZATION_FAIL` | G3 空间门失败 |
| `G4A_MIXED_FAIL` | G4a 标量/积分/波形四角失败 |
| `COMMON_PROJECTION_FAIL` | G5 解析段平均、守恒、场收缩或坐标失败 |
| `UNEXPECTED_HIGHER_HARMONIC_FAIL` | 高次谐波高于 floor |
| `G4B_FIELD_MIXED_FAIL` | G4b 任一界面/分量场混合差失败 |
| `G4_TOTAL_FAIL` | G4a、G5、G4b 未全部 PASS |
| `HOTSPOT_DEGENERATE` | S1 热点低对比/过宽，只撤销唯一热点主张 |
| `POWER_LEDGER_FAIL` | G6 闭合、耗散、分区或交叠映射失败 |
| `PERIODIC_CONSISTENCY_FAIL` | G7 周期一致性失败 |
| `CHI_D_UNDEFINED_LOW_DISSIPATION` | S1 耗散分母不高于 floor |
| `S1_HOLDOUT_FAIL` | S1 任一适用硬门失败 |
| `HOLDOUT_RULE_DRIFT_FAIL` | S1 解盲前后规则或 digest 漂移 |
| `ARRAY_CONTRACT_FAIL` | 强制 NPZ 缺失、超限、两时间路径混用或 schema 错误 |
| `OUTPUT_PATH_EXISTS_FAIL` | create-only 路径存在 |
| `CONTAINER_ID_MISMATCH_FAIL` | 镜像 ID 不符 |
| `RESOURCE_LIMIT_FAIL` | CPU、内存、墙钟或隔离失败 |
| `NONFINITE_OUTPUT_FAIL` | 任一正式量非有限 |
| `POST_HOC_GATE_CHANGE_FAIL` | 看结果后改规则、阈值、DAG 或参考层 |

任一硬 FAIL 后不得同时写 PASS。只有以下顺序中的每个适用状态均为 PASS：

```text
G0, G1, G2, G3, G4a, G5, G4b, G4, G6, G7,
S1-G1, S1-G4a, S1-G5, S1-G4b, S1-G4, S1-G6, S1-G7,
source lock, resource, array contract, hold-out adjudication
```

才可生成候选标签 `FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03`，且仍须独立
Supervisor 与人类终审。

## 21. Figure 2 面板合同（本轮不制图）

| 面板 | 内容 | 证据边界 |
|---|---|---|
| a | 完整无环 DAG：G0→G1→G2→G3→G4a→G5→G4b→G4→G6→G7→digest→S1 子门 | v08 迁移等价不进入收敛梯 |
| b | 开发集 S3 上 T64/T128/T256 误差、观察阶和相位 | T256 是有限参考 |
| c | 开发集 T128 上 S2/S3/S4 全局与公共场收缩 | 全局 G3、场 G5 分开标注 |
| d | G4a 标量混合差、G5 投影和 G4b 场混合差及 G4 真值表 | 不得在 G5/G4b 前标 G4 PASS |
| e | 128×256 解析段平均、两界面两分量、合力/功率；S1 `peak_phase_bin_average` 热点 | 禁端点/中心抽样；退化不画唯一热点 |
| f | G6 功率/耗散、G7 harmonic 周期一致性及 S1 \(\chi_D\) | by-construction 不是吸引极限环 |

失败必须展示或删除主张，禁止只选最平滑病例。

## 22. Nature Physics 战略标准

Figure 2 全部通过也只关闭有限阶梯数值可信度缺口的一部分，不自动产生普适物理。
Nature Physics 仍是战略设计标准；后续仍需 Figure 3 的简洁 \(De\times H\) 传递律与
独立预测、跨边界/几何稳健性、Figure 4 粗粒化共同极限、可辨识性和真实几何/实验验证。

常规收敛是必要基础，不是 Nature Physics 级核心发现。

## 23. v03 验收门

独立 Supervisor 只有在以下全部满足时才可接受：

1. v02、v02 审阅、Figure 1 和八个核心源码锚点一致；
2. 唯一门禁 DAG 为 G4a→G5→G4b→G4，总裁决不能提前；
3. 病例矩阵、S1 子门、结果 schema、面板和最终 PASS 使用同一 DAG；
4. 256 个相位 P0 值使用第 12.2 节解析段平均，禁止端点/中心抽样；
5. 公共 L2、合力、热点和 G4b 只使用同一解析段平均数组；
6. 逐步功/耗散只走第 12.3 节区间交叠守恒路径，不与单频重建混用；
7. v02 已通过的 S1 留出、128×256、fine-reference、N1–N11、强制 NPZ、资源和证据
   边界均未回退；
8. 审阅只产生接受/修订决定，不自动授权计算。

任一适用项失败即 fail closed。

## 24. 停止边界

本合同新增后立即停在 Supervisor Gate。未被接受前，不授权：

- solver、Docker、数值试跑、参数扫描或 Figure 2 制图；
- 代码、测试、CURRENT_STATUS、Figure 1、结果或旧证据修改；
- Figure 3、3D、整心房、流体/CFD/FSI、实验拟合或 GPU；
- Git add、commit、push、发布或远端操作。
