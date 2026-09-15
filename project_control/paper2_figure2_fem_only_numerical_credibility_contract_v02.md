---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V02
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: ade5f96d7b89a6ed6b629a37db795ed08853ba3f
baseline_upstream_ahead_behind: 0/0
supersedes: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01.md
source_review: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01_supervisor_review_v01.md
source_review_disposition: NUMERICAL_DESIGN_REVISION_REQUIRED
accepted_figure1: project_control/paper2_figure1_three_layer_theory_contract_v02.md
accepted_figure1_sha256: a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_numerical_credibility_contract_not_execution_evidence
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度合同 v02

## 0. 修订目的、科学主张和本轮边界

本合同依据
`project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01_supervisor_review_v01.md`
修订 v01，并落实 `NUMERICAL_DESIGN_REVISION_REQUIRED` 的全部裁决：

1. 开发集冻结为 `A2/LN/LS/C0/CQ`，空间异质主动场 `S1` 改为 digest 锁定后解盲的
   独立留出；
2. 共同定义域冻结为 128 个空间 P0 段 × 256 个相位段，单频场和逐步功率采用不同的
   守恒映射；
3. 时间—空间交互量改为以 S4/T256 为同一参考的混合差；
4. N1–N11 全部采用 Supervisor 裁决，不再作为未决候选。

Figure 2 的唯一科学目的，是证明当前二维 FEM-only 三层模型在预注册有限离散阶梯上的
离散方程、代数求解、时间、空间、界面投影、功率账本和周期解具有可审计可信度。

Figure 2 不证明参数具有斑马鱼生理真实性，不证明 EFE、三维心房、流体或疾病机制，
也不验证后续 \(De\times H\) 普适规律。v08 的迁移等价只说明新包重现冻结旧 FEM 臂，
不是 Figure 2 的收敛证据。

本轮只新增本合同，不运行 solver/Docker，不修改 v01、Supervisor 审阅、Figure 1、
CURRENT_STATUS、源码、测试、结果或旧材料，也不执行 Git 暂存、提交或推送。

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

### 1.2 合同与源码锚点

| 对象 | SHA-256 |
|---|---|
| Figure 2 v01 | `4adf514b242610f320e52f0efca0fbb04e3ee1a2525460c3092b4657836f001f` |
| v01 Supervisor 审阅 | `b9fa7003b0fe310d2d28eb17ad0eccdc3894df56f6ecedfa4d029a9c99d587b2` |
| `src/paper2_hybrid/__init__.py` | `4626ee6f49cac099734728fe0dc2f3412ded11cf5066b32aff556cc39324783f` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/projection.py` | `3bd590f0deef1fbe47cfdf01dea48664b25ff5a8716a546e4758bc4a0642176c` |
| `src/paper2_hybrid/protocol.py` | `f96d779cfcd6c76e9535f90a9941a6156b545d53a0270f04a564c68a304fe3ca` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |
| `src/paper2_hybrid/validation.py` | `6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5` |

后续若获准新增 runner、验证模块或测试，执行合同必须将新增文件加入源锁，并保持上述
核心模型文件不变；若确需改核心模型，必须另立模型变更合同，本 Figure 2 合同失效。

### 1.3 运行前后锁

每次未来正式尝试必须在运行前、运行后分别记录：

1. Git HEAD/upstream、ahead/behind 和 scoped status；
2. 活跃包、测试、获批合同、runner 的字节数和 SHA-256；
3. 固定角色 manifest、配置 digest、病例矩阵 digest、阈值 digest、留出封存 digest；
4. 容器镜像 ID、Python/FEniCSx/PETSc/SciPy/NumPy 版本；
5. CPU、内存、网络、GPU 和 Docker socket 状态。

任一运行前后锁不一致即 `SOURCE_OR_PROTOCOL_DRIFT_FAIL`，不得生成 PASS。

## 2. 现有接口与执行前必须补齐的验证接口

### 2.1 已存在但尚未构成 Figure 2 证据

- `HybridConfig` 定义 S2/S3/S4、T64/T128/T256 和病例标签；
- `build_system` 装配主动心肌 FEM、SLS ECM、离散链、双界面和支撑；
- `direct_solver_assurance` 给出直接残差与范数后向误差；
- `discrete_ledger` 给出精确中点能量增量、功、耗散和闭合；
- 当前空间投影器支持原生分片线性场到嵌套较粗 P0 段；
- `global_structural_checks` 检查角色、装配、对称、支撑和主动共轭；
- `simulate_endpoint` 输出两周期位移、牵引、ECM 场和功率数组。

这些接口的存在不是通过证据。

### 2.2 执行合同必须授权补齐，但本轮不实现

1. 任意原生分片线性空间场到 128 个目标 P0 段的**解析分段积分**，包括从 S2/S3 到
   更细公共段，不得用重复值或点抽样；
2. 从每个端点的 DC/一阶谐波系数在 256 个共同相位段重建单频场，并审计更高谐波能量；
3. 把原生逐步功/耗散按时间区间重叠守恒分配到 256 个相位段，不用平均牵引乘平均速度；
4. 两界面、两个物理力分量的独立输出与一侧存储/另一侧严格取负映射；
5. 真实零 RHS 直接求解、连续体/链 affine patch、SLS DC/离散谐波制造解；
6. 正对角对称缩放后的矩阵惯性、特征值、零空间和刚体模态审计；
7. 通用 floor、零分母、phase wrapping、热点集合和 S1 封存/解盲；
8. S2/S3/S4、T64/T128/T256 和四角的统一比较器；
9. create-only 事务 runner、强制最小数组包、结果 manifest 和 hash ledger。

若未来执行未补齐任一接口，G0 前以 `MISSING_VALIDATION_INTERFACE_FAIL` 停止，禁止
手工摘录或旧结果替代。

## 3. 病例矩阵、开发集和 S1 独立留出

### 3.1 病例角色

| 病例 | 驱动 | Figure 2 角色 |
|---|---|---|
| `P0` | 零主动、零外载 | 零驱动、数值噪声 floor；另须真实零 RHS 求解 |
| `P1` | 给定微小 affine 宏观应变 | 被动切线与 patch 辅助；不是完整耦合平衡解 |
| `A2` | 均匀纯主动 | 纯主动开发病例 |
| `LN` | 纯法向规定载荷 | 单输入法向开发病例 |
| `LS` | 纯切向规定载荷 | 单输入切向开发病例 |
| `C0` | 均匀主动 + 同相法向载荷 | 同相多输入开发病例 |
| `CQ` | 均匀主动 + 相差 \(\pi/2\) 的法向载荷 | 正交多输入开发病例 |
| `S1` | 空间异质纯主动 | **独立留出**，规则 digest 后才解盲 |
| `A1` | 当前与 `A2` 具有相同代数输入 | 输入别名审计，不重复计证据 |

`C0/CQ` 是已知线性输入的同相/正交组合，只用于开发多输入相位和叠加审计，不称为
独立新物理。开发集固定为 `A2/LN/LS/C0/CQ`，覆盖主动、法向、切向及两种多输入相位。

### 3.2 分层运行矩阵

| 阶段 | 病例 | 空间/时间端点 | 用途 |
|---|---|---|---|
| G0 | P0、P1、制造解 | S2/S3/S4，静态 | 源、装配、patch、谱、零驱动、作用反作用 |
| G1 | P0、A2、LN、LS、C0、CQ | 先 S2/T64；随后每个正式端点自动检查 | 直接代数求解 |
| G2 | A2、LN、LS、C0、CQ | S3 × T64/T128/T256 | 时间收敛 |
| G3 | A2、LN、LS、C0、CQ | S2/S3/S4 × T128 | 空间收敛 |
| G4 | A2、LN、LS、C0、CQ | S3/S4 × T128/T256 四角 | 联合混合差 |
| G5–G7 | 同一开发集 | 复用通过端点；终局 S4/T256 | 公共域、功率、周期一致性 |
| Hold-out | S1 | S3/S4 × T128/T256 四角 | 异质场、热点和耗散份额解盲 |

### 3.3 留出封存和解盲

在任何 S1 求解前必须生成不可变 `pre_holdout_digest.json`，至少哈希：

- 本合同、后续获批执行合同和 runner；
- N1–N11、floor、相位、公共域和热点规则；
- 开发集全部结果文件；
- S1 四角端点列表、QoI 清单和 PASS/FAIL 规则；
- 数组 schema、资源门和容器 ID。

S1 只能在 G0–G7 开发门全部通过并锁定 digest 后执行。若解盲失败，只能标
`S1_HOLDOUT_FAIL` 并冻结结果；不得修改阈值、热点、floor、公共域或派生量后在同版本
重跑并继续称为独立留出。

## 4. 固定离散阶梯与比较方向

### 4.1 空间阶梯

| 标签 | \(n_x\) | 每连续层 \(n_y\) | 角色 |
|---|---:|---:|---|
| S2 | 32 | 8 | 粗层 |
| S3 | 64 | 16 | 中层、时间门固定层 |
| S4 | 128 | 32 | 当前最细空间参考 |

网格逐级 2 倍嵌套，三层共享 \(n_x\)，三角形对角固定为
`lower_left_to_upper_right`。空间误差方向为

\[
e_{23}=d(Q_{S2},Q_{S3}),\qquad e_{34}=d(Q_{S3},Q_{S4}).
\]

必须同时报告两级，禁止只报 S4；S4 只是有限参考，不是连续极限。

### 4.2 时间阶梯

| 标签 | 每周期步数 | \(\Delta t/T\) | 角色 |
|---|---:|---:|---|
| T64 | 64 | 1/64 | 粗层 |
| T128 | 128 | 1/128 | 中层、空间门固定层 |
| T256 | 256 | 1/256 | 当前最细时间参考 |

时间误差方向为

\[
e_{64,128}=d(Q_{T64},Q_{T128}),\qquad
e_{128,256}=d(Q_{T128},Q_{T256}).
\]

必须同时报告两级；T256 只是有限参考，不是连续时间解。

### 4.3 四角与 fine-reference 混合差

G4 和 S1 留出均使用

\[
(S3,T128),\ (S3,T256),\ (S4,T128),\ (S4,T256).
\]

先定义

\[
\Delta_{st}Q=
Q_{S4,T256}-Q_{S3,T256}-Q_{S4,T128}+Q_{S3,T128}.
\]

标量使用

\[
e_{st}^{(s)}=
\frac{|\Delta_{st}Q|}{\max(|Q_{S4,T256}|,F_Q)},
\]

共同域波形/场使用

\[
e_{st}^{(2)}=
\frac{\|\Delta_{st}Q\|_{L^2(\mathcal D_c)}}
{\max(\|Q_{S4,T256}\|_{L^2(\mathcal D_c)},F_Q\sqrt{|\mathcal D_c|})}.
\]

同一 S4/T256 参考也用于 fine-space 时间边际误差 \(e_t^{S4}\) 和 fine-time 空间边际
误差 \(e_s^{T256}\)。接受门冻结为

\[
e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12}).
\]

若 S4/T256 参考低于 floor，则不构造相对交互比；只要求
\(|\Delta_{st}Q|\le F_Q\) 或相应场范数绝对门。

## 5. 特征尺度、floor、相位和热点规则

### 5.1 预注册尺度与绝对 floor

| QoI 类 | 特征尺度 \(S_Q\) |
|---|---|
| 位移 | \(S_u=a_0L\) |
| 应变、内部变量、宏观/自由缩短 | \(S_\epsilon=a_0\) |
| 牵引/应力 | \(S_t=E_\infty a_0\) |
| 广义力、右端和代数残量 | \(S_f=E_\infty a_0L\) |
| 每单位厚度储能/功 | \(S_W=E_\infty a_0^2L^2\) |
| 功率 | \(S_P=S_W/T\) |

每个 QoI 的噪声 \(N_Q\) 必须来自同一算子的真实零 RHS 直接求解控制，冻结

\[
F_Q=\max(10^{-12}S_Q,10N_Q).
\]

不得用 `1e-30`、非零病例最小值或 S1 解盲结果定义 floor。

### 5.2 比较量和零分母

标量和共同域误差分别为

\[
d_s(q,r)=\frac{|q-r|}{\max(|r|,F_Q)},
\]

\[
d_2(q,r)=
\frac{\|q-r\|_{L^2(\mathcal D_c)}}
{\max(\|r\|_{L^2(\mathcal D_c)},F_Q\sqrt{|\mathcal D_c|})}.
\]

若参考量不高于 floor，记录 `BELOW_RESOLUTION_FLOOR`，不计算相对误差或观察阶；只有
绝对差不高于相应 floor 才通过。不得返回伪 0、NaN 或 Inf。

### 5.3 相位

相位只在指定输入和输出一阶谐波幅值均高于 \(10F_Q\) 时定义：

- A2：相对于主动输入；
- LN：相对于法向载荷；
- LS：相对于切向载荷；
- C0/CQ：相对于主动时钟，同时记录规定载荷的 0 或 \(\pi/2\) 相位；多输入结果不称
  单一传递函数；
- S1 留出：相对于主动输入。

相位差 wrap 为

\[
\Delta\phi=\operatorname{atan2}
[\sin(\phi_1-\phi_2),\cos(\phi_1-\phi_2)]\in[-\pi,\pi].
\]

低幅信号标 `PHASE_UNDEFINED_LOW_AMPLITUDE`，不强置为零。

### 5.4 S1 留出热点

热点只在解盲阶段、主动幅值峰值 \(t=T/2\) 上定义。使用心肌侧轴向物理牵引
\(t_{e\to m,x}=-t_{me,x}^{rep}\) 的最强压缩区。公共段值为 \(t_j\)，冻结

\[
\mathcal H=\{j:t_j\le t_{min}+0.05(t_{max}-t_{min})\}.
\]

场范围必须 \(t_{max}-t_{min}>10F_t\)，热点集长度覆盖不得超过周期域 25%；否则标
`HOTSPOT_DEGENERATE`，只禁止唯一热点主张，不自动否定其他数值 QoI。

非退化时，以周期距离

\[
d_L(x,y)=\min(|x-y|,L-|x-y|)
\]

计算长度加权热点集合的 Hausdorff 距离和 Jaccard，不直接比较数组索引。

## 6. 分层 fail-closed 顺序

```text
G0 静态/制造检查
  -> G1 代数求解器
  -> G2 时间
  -> G3 空间
  -> G4 时间-空间联合混合差
  -> G5 共同域投影
  -> G6 功率闭合
  -> G7 周期稳态一致性
  -> 锁定 pre_holdout_digest
  -> S1 四角解盲
  -> Supervisor Gate
```

任一门失败立即停止。不得在同一正式尝试中修改阈值、floor、病例、网格、时间步、
投影、热点、QoI 或求解器后继续。

## 7. G0 — 静态、制造和矩阵结构

### 7.1 制造检查

在 S2/S3/S4 上全部执行：

1. 源码、角色、病例、阶梯和禁用符号静态审计；
2. UFL 与手工 \(B^TCB\) 装配相对 Frobenius 误差 \(\le10^{-10}\)；
3. 连续体 affine patch、心内膜链 affine patch 相对误差均 \(\le10^{-10}\)；
4. SLS DC 与**当前 CN 离散谐波解析响应**相对误差 \(\le10^{-10}\)，不得混入连续
   时间离散误差；
5. 主动共轭多步长中心差分平台的最优相对误差 \(\le10^{-7}\)；
6. 矩阵相对非对称和制造作用—反作用误差均 \(\le10^{-12}\)；
7. 真实零 RHS 直接求解的绝对残量与解范数不高于 floor。

`P0` 旁路零数组和 `P1` 人工宏观应变不能单独替代真实求解与完整 patch。

### 7.2 正对角缩放与惯性

对实对称矩阵 \(A\)，取其正对角 \(D_A=\operatorname{diag}(A)\)，构造

\[
\widehat A=D_A^{-1/2}AD_A^{-1/2}.
\]

任一应参与缩放的对角项非正即失败。对本来只作用于边界的 \(K_s\)，正对角缩放限制在
受支撑自由度子空间；其余零对角自由度作为已声明设计核保留，同时仍对完整未缩放
\(K_s\) 做半正定惯性审计。冻结结构门：

- \(K_{mat}\) 对称半正定；缩放最小特征值不低于 \(-10^{-10}\)，并在当前
  affine-periodic 约化空间**恰有两个**共同刚体平移零模；零模定义为
  \(|\lambda|\le10^{-10}\lambda_{max}\)；
- 支撑 \(K_s\) 半正定，缩放最小特征值不低于 \(-10^{-10}\)；允许其设计零空间；
- \(K_{mat}+K_s\) 严格正定，不允许未声明零模，缩放
  \(\lambda_{min}/\lambda_{max}>10^{-12}\)；
- \(G\) 严格正定，缩放 \(\lambda_{min}/\lambda_{max}>10^{-12}\)；
- 复杂谐波矩阵只审计可逆性、直接残差和后向误差，不称正定。

零模数与理论声明不一致即 `MATRIX_INERTIA_FAIL`，不得静默修改零阈值。

## 8. G1 — 直接代数求解器

当前 `scipy_superlu` 分别求 DC 实系统和单频复系统。正式 runner 对每个端点另行执行
严格验收：

- 非零 RHS 二范数相对残差 \(\le10^{-10}\)；
- 范数后向误差
  \(\|r\|_\infty/(\|A\|_\infty\|q\|_\infty+\|b\|_\infty)\le10^{-12}\)；
- 零 RHS 使用第 5 节绝对 floor；
- 不得出现零 pivot、非有限值或不可逆系统；
- DC 与复谐波系统分别报告矩阵/RHS 哈希和结果。

当前代码 `1e-7` 只是较宽默认值；正式 runner 用 `1e-10` 作独立验收，不改变 SuperLU
内部 tolerance，也不虚构 tolerance 扫描。任何迭代求解器需另立未来合同。

## 9. G2 — 时间离散

固定 S3，对 A2/LN/LS/C0/CQ 计算 T64/T128/T256。比较：

- 宏观短缩、心内膜平均位移、界面积分牵引的一周期波形；
- 一阶谐波幅值和 wrapped phase；
- 储能、主动/外载/支撑功、drag/SLS 耗散的周期积分；
- ECM 内变量和两界面原生积分范数；
- 峰值只作 sidecar，不替代波形范数。

冻结门：高于 floor 的 T128–T256 标量、波形和积分误差
\(\le2\times10^{-3}\)，相位差 \(\le10^{-2}\) rad；误差必须下降；两级原始差范数均
高于 \(10F_Q\) 时

\[
p_t=\log_2(e_{64,128}/e_{128,256})\ge1.5.
\]

当前谐波求解器验证的是 CN 离散周期响应的时间细化，不是通用非正弦瞬态积分器。

## 10. G3 — 空间离散

固定 T128，对 A2/LN/LS/C0/CQ 计算 S2/S3/S4。G3 先比较全局 QoI、边界合力和原生
积分范数，场比较在 G5 共同域执行。

冻结门：高于 floor 的 S3–S4 全局 QoI 误差 \(\le2\times10^{-2}\)，且

\[
e_{34}\le0.8e_{23}.
\]

P1 位移、分片常应变、界面 penalty、最大值和场可能具有不同阶，必须逐类报告。禁止
用全局均值覆盖场失败，禁止以 S4 图片更平滑作为通过理由。

## 11. G4 — fine-reference 联合混合差

对开发集复用第 4.3 节四角。G4 先对无需跨空间网格逐点对应的标量、周期积分量和波形
执行混合差；共同牵引场在 G5 完成 128×256 投影后，仍用第 4.3 节同一 S4/T256 参考
执行场混合差。两部分均通过才可写 G4 PASS。逐 QoI 检查：

1. S4 上 T128→T256 的边际误差满足 G2 终局门；
2. T256 上 S3→S4 的边际误差满足 G3 终局门；
3. 以 S4/T256 和同一 floor 归一的 \(e_{st}\) 满足
   \(0.5\max(e_t^{S4},e_s^{T256},10^{-12})\) 门；
4. 相位、符号和物理解释在四角一致；
5. 任一 fine corner 的代数、有限性或功率预检失败即停止。

G4 只支持“当前有限四角联合稳定”，不外推连续极限。

## 12. G5 — 128×256 共同域、守恒与场收缩

### 12.1 公共坐标和边界

- 空间：\([-L/2,L/2]\) 上 128 个等长 P0 段；
- 时间：一个归一化周期 \([0,T)\) 上 256 个等长相位段；
- 周期端点用于闭合积分但不重复计权；
- 左右边界使用同一周期合并和半权重规则；
- 两界面、两个物理力分量使用相同坐标、方向和 dtype manifest。

### 12.2 单频位移/牵引场

对 S2/S3/S4 的原生分片线性空间场，逐个公共段解析切分原生单元并积分平均；目标段比
原生段细时仍使用原生线性插值的精确积分，不得简单重复或点抽样。

时间上从每个端点的 DC 与一阶谐波系数重建到 256 个共同相位段。对原生周期数组做
谐波审计；若 \(\widehat Q_k\) 为离散 Fourier 系数，则必须满足

\[
\left(\sum_{|k|>1}|\widehat Q_k|^2\right)^{1/2}
\le F_Q\sqrt{|\mathcal D_c|}.
\]

DC/一阶谐波之外的能量高于该 floor 即
`UNEXPECTED_HIGHER_HARMONIC_FAIL`；不得用单频重建隐藏高次成分。

### 12.3 逐步功和耗散

\(W_a,W_L,W_s,D_{drag},D_{SLS}\) 是原生时间单元上的步积分量，不按单频场处理。每个
原生步量除以其 \(\Delta t\) 得到该步守恒密度，再按与 256 目标相位段的区间重叠比例
分配；目标段总和必须严格复原原生整周期量。

界面功率密度 \(\mathbf t\cdot\dot{\mathbf u}\) 也在原生空间—时间单元上先积分，再按
目标单元重叠守恒映射。禁止用“平均牵引 × 平均速度”代替功率积分。

### 12.4 作用—反作用、合力、功率和场门

只投影并保存一个界面侧的物理作用力，另一侧由 manifest 规定严格取负。必须逐界面、
逐分量通过：

- 常量/线性制造场分量及合力绝对/缩放误差 \(\le10^{-12}\)；
- 原生—公共合力与功率相对误差 \(\le10^{-10}\)；
- 开发集 S3–S4 公共牵引场 \(d_2\le5\times10^{-2}\)；
- 高于 floor 时同时满足 \(d_{34}\le0.8d_{23}\)；
- 不允许用两界面或两分量的合并范数覆盖单项失败。

S1 留出不参与 \(d_{23}\) 规则调定，只在四角上接受既定 S3–S4 终局场门和第 5.4 节
热点门。

## 13. 核心 QoI

| 类别 | 必须输出 |
|---|---|
| 宏观运动 | \(-\bar\epsilon(t)\) 有限支撑短缩；规定自由短缩 \(\langle p\rangle a(t)\) 只作输入/比较器 |
| 心内膜 | 平均切向/法向位移波形和一阶谐波 |
| 双界面 | 四个物理作用力方向、两分量共同场、合力、空间—时间 \(L^2\) 范数 |
| 相位 | 第 5.3 节定义的单输入/多输入 wrapped phase |
| S1 热点 | \(t=T/2\) 的心肌侧最强压缩轴向物理牵引集合、位置和幅值 |
| ECM | \(\epsilon_e,z,\sigma_e\) 有限性和积分范数；von Mises 只称 proxy |
| 储能 | \(\Psi_m,\Psi_e,\Psi_n,\Psi_I,\Psi_{mat},\Psi_s\) 或可审计等价分解 |
| 功/耗散 | 主动、腔面、支撑功，drag/SLS 耗散，逐步和周期闭合 |
| 留出派生量 | S1 四角的耗散份额 \(\chi_D\) |
| 数值 | 直接残差、后向误差、缩放谱/惯性、周期一致性、资源 |

不得把规定自由短缩当求解输出，也不得把二维 ECM von Mises proxy 当三维等效应力。

### 13.1 N1–N11 冻结裁决汇总

以下阈值已经由 v01 Supervisor 审阅逐项裁决，不是候选值，也不继承 v08 的通过结论：

| 编号 | 冻结设计 |
|---|---|
| N1 | UFL—手工装配、连续体/链 affine patch、SLS DC/离散谐波制造解均 \(\le10^{-10}\)；主动共轭多步长平台最优相对误差 \(\le10^{-7}\)；矩阵非对称与制造作用—反作用均 \(\le10^{-12}\) |
| N2 | 正对角对称缩放；\(K_{mat}\) 半正定且恰有两个共同平移零模，半正定最小缩放特征值 \(\ge-10^{-10}\)；\(K_{mat}+K_s\) 与 \(G\) 严格 SPD，缩放 \(\lambda_{min}/\lambda_{max}>10^{-12}\)；复谐波矩阵只验可逆性 |
| N3 | 非零 RHS 二范数相对残差 \(\le10^{-10}\)，范数后向误差 \(\le10^{-12}\)，零 RHS 用绝对 floor，无零 pivot/非有限值 |
| N4 | T128–T256 标量/波形/积分误差 \(\le2\times10^{-3}\)，相位 \(\le10^{-2}\) rad；高于 floor 时误差下降；两级原始差均高于 \(10F_Q\) 时 \(p_t\ge1.5\) |
| N5 | S3–S4 全局 QoI \(\le2\times10^{-2}\)，高于 floor 时 \(e_{34}\le0.8e_{23}\)；场和热点分别服从 N7/N8 |
| N6 | 使用 S4/T256 同一参考的混合差，\(e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12})\)；低于 floor 时用绝对门 |
| N7 | 128×256 公共域；常量/线性场及合力误差 \(\le10^{-12}\)；原生—公共合力/功率 \(\le10^{-10}\)；S3–S4 场 \(d_2\le5\times10^{-2}\)，且高于 floor 时 \(d_{34}\le0.8d_{23}\)；两界面两分量逐项通过 |
| N8 | S1 在 \(t=T/2\) 解盲；\(\eta_h=0.05\)，场范围 \(>10F_t\)，覆盖 \(\le25\%\)，周期 Hausdorff \(\le L/32\)，长度加权 Jaccard \(\ge0.5\)，峰值幅值差 \(\le5\times10^{-2}\) |
| N9 | `ledger-minus-equilibrium` \(\le10^{-10}\)；逐步/整周期归一闭合 \(\le10^{-8}\)；drag/SLS 步耗散 \(\ge-10^{-12}S_W\) |
| N10 | harmonic 两周期状态、牵引和能量一致性 \(\le10^{-10}\)，保留 by-construction 标签 |
| N11 | 单 CPU、峰值内存 \(\le8\) GiB、总墙钟 \(\le3600\) s，无网络/GPU/Docker socket |

任何未来执行合同或 runner 中出现更宽阈值，均以本表为准并触发协议不一致失败；不得
静默取 `config.py` 中较宽的默认值。

## 14. G6 — 功率与耗散

每个端点使用 Figure 1 已接受的精确离散恒等式

\[
W_a+W_L+W_s-\Delta_d\Psi_{mat}-D_{drag}-D_{SLS}=W_{eq\ defect}.
\]

冻结门：

- 每步 `ledger-minus-equilibrium` 相对差 \(\le10^{-10}\)；
- 每步归一闭合残差 \(\le10^{-8}\)；
- 整周期归一闭合 \(\le10^{-8}\)；
- 每步 drag 和 SLS 耗散 \(\ge-10^{-12}S_W\)；
- 原生与公共域功率积分按 G5 相对误差 \(\le10^{-10}\)。

\(\Psi_I\) 已在物质自由能中，界面 penalty 不另记耗散。支撑外端口分区与把
\(\Psi_s\) 纳入总储能的分区必须给出同一周期结果。端点能量直接相减只作 sidecar，
不能替代精确中点增量。分母一律使用第 5 节 floor。

## 15. G7 — harmonic 周期一致性

当前求解器直接求 DC 与单频 CN 谐波系统后构造两个周期。开发集每个端点必须满足：

- 状态 \(q\)、SLS 内变量 \(z\)、两界面物理牵引和能量的 cycle-1/cycle-2 归一差
  \(\le10^{-10}\)；
- 输入周期端点在机器精度内一致；
- 周期总储能变化与 G6 周期积分一致；
- DC/谐波代数系统仍通过 G1。

该门必须标 `harmonic_periodic_solution_by_construction`，不能声称任意初值收敛到吸引
极限环。后者需要另立瞬态合同。

## 16. S1 独立留出与耗散份额

### 16.1 四角应用

解盲后对 S1 四角完整执行 G1、G4–G7 的适用门，不修改任何规则：

- 时间终局：S4 上 T128–T256 标量/波形/积分误差 \(\le2\times10^{-3}\)，相位
  \(\le10^{-2}\) rad；
- 空间终局：T256 上 S3–S4 全局 QoI \(\le2\times10^{-2}\)，公共牵引场
  \(d_2\le5\times10^{-2}\)；
- 混合差：使用 S4/T256 归一并通过第 4.3 节 `0.5` 门；
- 热点：场范围 \(>10F_t\)、覆盖 \(\le25\%\)、S3–S4 周期 Hausdorff
  \(\le L/32\)、长度加权 Jaccard \(\ge0.5\)、峰值幅值相对差 \(\le5\times10^{-2}\)；
- 两界面两分量、功率、耗散、周期与代数门逐项通过。

S1 只运行四角，因此不虚构 T64 观察阶或 S2→S3 场收缩证据。

### 16.2 预注册派生量 \(\chi_D\)

定义每周期耗散份额

\[
\chi_D=\frac{D_{SLS}}{D_{SLS}+D_{drag}}.
\]

只有分母 \(D_{SLS}+D_{drag}>F_W\) 时定义；否则标
`CHI_D_UNDEFINED_LOW_DISSIPATION`，不得强置为 0 或 1。

\(\chi_D\) 不得在开发集上用于调整任何阈值。S1 解盲后使用同类冻结门：S4 上
T128–T256 差 \(\le2\times10^{-3}\)，T256 上 S3–S4 差 \(\le2\times10^{-2}\)，混合差
以 S4/T256 值和 floor 归一并通过第 4.3 节 `0.5` 门。若分母低于 floor，则该派生量只
能记为不可定义，不能提供留出支持；其他预注册 S1 场/热点门仍独立裁决。

## 17. 强制结果与数组合同

### 17.1 create-only 目录

未来正式目录固定为

```text
results/paper2_figure2/
  fem_only_numerical_credibility_v02_YYYYMMDD_<run_id>/
```

`run_id` 必须在执行授权中冻结。目录若存在即 `OUTPUT_PATH_EXISTS_FAIL`，不得覆盖、
删除、清空、移动或复用。失败尝试原位保留 `failure_summary.json`，不能改名为 PASS。

### 17.2 正式文件

| 文件 | 内容 |
|---|---|
| `manifest.json` | schema、合同/规则 digest、环境、状态、证据边界 |
| `gate_summary.json` | G0–G7 和 S1 留出的逐门值、阈值、PASS/FAIL/NA |
| `case_matrix.json` | 端点与开发/留出分区 |
| `algebraic_audit.json` | 残差、后向误差、缩放谱、惯性、pivot、零 RHS |
| `convergence_audit.json` | 时间、空间、fine-reference 混合差、floor、观察阶 |
| `projection_audit.json` | 128×256 域、两界面两分量、原生/公共合力与功率、场收缩 |
| `power_audit.json` | 逐步/周期账本、耗散与能量分区 |
| `periodic_audit.json` | 两周期一致性及 by-construction 标签 |
| `pre_holdout_digest.json` | S1 解盲前全部规则和开发结果哈希 |
| `s1_holdout_audit.json` | S1 四角、热点、\(\chi_D\) 和最终留出裁决 |
| `resource_audit.json` | 墙钟、峰值内存、CPU 与容器隔离 |
| `provenance.json` | Git、源锁、容器和命令参数 |
| `common_observables.npz` | **强制**最小共同域数组包 |
| `hash_ledger.json` | 除自身外正式文件的路径、字节数和 SHA-256 |

JSON 必须 UTF-8、排序键、禁止 NaN/Infinity；`hash_ledger.json` 不自我哈希。

### 17.3 强制数组包

`common_observables.npz` 必须存在且压缩后 \(\le128\) MiB：

- 只含 128×256 共同域牵引、核心一周期波形、必要逐步功率、坐标和 S1 四角；
- 两侧物理作用力只保存一侧，manifest 规定对侧严格取负；
- 禁止 object/pickle、全状态、系统矩阵、重复第二周期和逐单元 ECM 全场；
- 每个数组登记键、shape、dtype、物理方向、病例/端点和内容 SHA-256；
- 数组总包缺失、超限或出现未登记键均为 `ARRAY_CONTRACT_FAIL`。

## 18. 容器、资源与事务边界

- image tag：`dolfinx/dolfinx:v0.11.0`；
- expected image ID：
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 单 CPU/进程，BLAS/OpenMP/PETSc 线程均为 1；
- 总墙钟 \(\le3600\) s，峰值内存 \(\le8\) GiB；
- `--network none`，不挂载 Docker socket，不使用 GPU；
- 源码和合同只读，唯一可写挂载为新 create-only 结果目录；
- 随机种子只用于制造/谱审计，不进入物理解；
- 异常、超时、内存越界或进程非零退出立即 fail closed，不自动重试。

镜像 ID 不匹配时不得自动 pull 或换 tag，返回 `CONTAINER_ID_MISMATCH_FAIL`。

## 19. FAIL 标签与最终裁决

| 标签 | 触发条件 |
|---|---|
| `SOURCE_OR_PROTOCOL_DRIFT_FAIL` | Git、源码、角色、病例、阈值、runner 或留出封存漂移 |
| `RETIRED_ROUTE_REINTRODUCED_FAIL` | 心肌 DCM、representation、identity 或旧包运行依赖出现 |
| `MISSING_VALIDATION_INTERFACE_FAIL` | 第 2.2 节任一必需接口缺失 |
| `STATIC_OR_MANUFACTURED_FAIL` | G0 装配、patch、SLS、主动共轭或作用反作用失败 |
| `MATRIX_INERTIA_FAIL` | 缩放谱、恰好两个 Kmat 平移零模、严格 SPD 或刚体控制失败 |
| `ALGEBRAIC_FAIL` | G1 残差、后向误差、pivot 或有限性失败 |
| `TIME_DISCRETIZATION_FAIL` | G2 终局误差、下降或适用观察阶失败 |
| `SPACE_DISCRETIZATION_FAIL` | G3 终局误差或收缩失败 |
| `JOINT_TRIGGER_FAIL` | G4 fine-reference 混合差失败 |
| `UNEXPECTED_HIGHER_HARMONIC_FAIL` | 单频场存在高于 floor 的 DC/一阶以外能量 |
| `COMMON_PROJECTION_FAIL` | G5 坐标、两界面/分量、合力、功率或场收缩失败 |
| `HOTSPOT_DEGENERATE` | S1 热点低对比或覆盖过宽；只禁止唯一热点主张 |
| `POWER_LEDGER_FAIL` | G6 逐步/周期闭合、耗散或能量分区失败 |
| `PERIODIC_CONSISTENCY_FAIL` | G7 状态、牵引、内变量或能量不一致 |
| `CHI_D_UNDEFINED_LOW_DISSIPATION` | S1 耗散总量不高于 floor；\(\chi_D\) 不可定义 |
| `S1_HOLDOUT_FAIL` | S1 解盲后任一适用硬门失败 |
| `HOLDOUT_RULE_DRIFT_FAIL` | S1 解盲前后规则、开发结果或 digest 漂移 |
| `ARRAY_CONTRACT_FAIL` | 强制 NPZ 缺失、超 128 MiB、含禁用数组或 schema 不符 |
| `OUTPUT_PATH_EXISTS_FAIL` | create-only 路径已存在 |
| `CONTAINER_ID_MISMATCH_FAIL` | 正式镜像 ID 不符 |
| `RESOURCE_LIMIT_FAIL` | CPU、内存、墙钟或隔离边界失败 |
| `NONFINITE_OUTPUT_FAIL` | 任一正式标量/数组非有限 |
| `POST_HOC_GATE_CHANGE_FAIL` | 看开发或留出结果后改规则、阈值或参考层 |

任一硬 FAIL 后最终标签只能是相应失败标签，不得同时写 PASS。`HOTSPOT_DEGENERATE`
只撤销唯一热点位置主张；其他门仍逐项裁决。`CHI_D_UNDEFINED_LOW_DISSIPATION` 使该派生
量不能提供留出支持，但不自动覆盖其他 S1 证据。

只有 G0–G7、源锁、资源、数组合同和 S1 所有适用留出门通过，才可生成候选标签
`FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V02`；仍须独立 Supervisor 和人类终审。

## 20. Figure 2 面板合同（本轮不制图）

| 面板 | 内容 | 证据边界 |
|---|---|---|
| a | G0→G7→digest→S1 的验证梯；固定 FEM-only 三层角色 | v08 迁移等价不进入收敛梯 |
| b | 开发集 S3 上 T64/T128/T256 误差、观察阶和相位 | T256 是有限参考 |
| c | 开发集 T128 上 S2/S3/S4 全局与公共场收缩 | 同时展示粗—中和中—细 |
| d | 开发集四角 fine-reference 混合差 | 分别时间/空间 PASS 不替代联合门 |
| e | 128×256 两界面两分量、合力/功率守恒；解盲后 S1 热点 | 退化时不画唯一热点 |
| f | 功率/耗散、harmonic 周期一致性、S1 \(\chi_D\) 留出 | by-construction 不是吸引极限环证明 |

任何面板只能在对应门通过后制作。失败必须展示或删除主张，禁止只选最平滑病例。

## 21. Nature Physics 战略标准

Figure 2 即使全部通过，也只关闭有限阶梯数值可信度缺口的一部分，不自动产生普适物理。
Nature Physics 仍只是战略设计标准；后续仍需 Figure 3 的简洁 \(De\times H\) 传递律与
独立预测、跨边界/几何稳健性、Figure 4 粗粒化共同极限、可辨识性和真实几何/实验验证。

常规收敛是必要基础，不是 Nature Physics 级核心发现。

## 22. v02 验收门

独立 Supervisor 只有在以下全部满足时才可接受本合同：

1. v01、审阅、Figure 1 和八个核心源码锚点一致；
2. 开发集仅为 A2/LN/LS/C0/CQ，S1 仅在规则 digest 后作为四角留出；
3. 公共域只有 128 空间段 × 256 相位段，并区分单频重建与逐步功率守恒映射；
4. G4 使用第 4.3 节 S4/T256 fine-reference 混合差；
5. N1–N11 全部按 Supervisor 裁决写成硬门，不再列为候选；
6. Kmat 恰有两个共同平移零模，Kmat+Ks 与 G 严格 SPD 的缩放谱门明确；
7. S1 热点固定在 \(t=T/2\)，\(\eta_h=0.05\)，场范围、覆盖率、周期 Hausdorff、
   长度加权 Jaccard 和峰值幅值门全部冻结；
8. \(\chi_D\) 定义、floor 和四角终局/混合差门明确；
9. `common_observables.npz` 强制且压缩后不超过 128 MiB；
10. 直接求解器无 tolerance 轴、create-only、资源和证据边界保留；
11. 审阅只产生接受/修订决定，不自动授权计算。

任一适用项失败即 fail closed，不得以总体设计合理豁免。

## 23. 停止边界

本合同新增后立即停在 Supervisor Gate。合同未被接受前，不授权：

- solver、Docker、数值试跑、参数扫描或 Figure 2 制图；
- 代码、测试、CURRENT_STATUS、Figure 1、结果或旧证据修改；
- Figure 3、3D、整心房、流体/CFD/FSI、实验拟合或 GPU；
- Git add、commit、push、发布或远端操作。
