---
review_id: REV-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V01-SUPERVISOR-V01
status: revision_required
reviewer: independent_supervisor
reviewed_at: 2026-09-04
reviewed_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01.md
reviewed_contract_sha256: 4adf514b242610f320e52f0efca0fbb04e3ee1a2525460c3092b4657836f001f
baseline_commit: ade5f96d7b89a6ed6b629a37db795ed08853ba3f
failure_label: NUMERICAL_DESIGN_REVISION_REQUIRED
next_required_artifact: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02.md
execution_authorized: document_revision_only
---

# Paper 2 Figure 2 数值可信度合同 v01 独立 Supervisor 审阅 v01

## 1. 裁决

v01 正确区分了 v08 迁移等价、Figure 2 数值可信度和后续机制证据，也正确禁止虚构
直接求解器的 tolerance 轴。但病例留出、共同定义域和四角交互量仍有三个实质性设计
阻断，因此返回 `NUMERICAL_DESIGN_REVISION_REQUIRED`，要求新增 v02，不覆盖 v01。

本审阅只授权合同修订，不授权 solver、Docker、代码修改或数值试跑。

## 2. 已接受的主体设计

以下内容在 v02 中应保留：

- G0→G7→留出的 fail-closed 顺序；
- S3×T64/T128/T256 时间阶梯、S2/S3/S4×T128 空间阶梯及 S3/S4×T128/T256 四角；
- `D0` 仅作固定 SuperLU provenance，不存在迭代 tolerance 轴；
- 真实零 RHS、连续体/链 affine patch、SLS DC/谐波制造解和物理作用力门；
- 标量、波形、相位、热点、能量/功率、零分母和绝对 floor 规则；
- create-only、源锁、失败保留、单 CPU、无网络/GPU/socket；
- 周期一致性是 harmonic by construction，不是任意初值极限环收敛。

## 3. v02 必须修复的三个设计阻断

### B1 — 留出病例改为 S1

`C0` 在当前线性系统中是已开发 `A2` 与 `LN` 输入的同相叠加，不能承担最强的独立
留出主张。v02 固定：

- 开发集：`A2/LN/LS/C0/CQ`；
- 独立留出：`S1`，只在全部阈值、floor、投影和热点规则生成 digest 后解盲；
- `S1` 使用 S3/S4×T128/T256 四角，检验未参与规则调定的空间异质主动场、牵引场和
  热点；
- `A1/A2` 仍记录为输入别名，不重复计证据；
- `C0/CQ` 只作为同相/正交多输入开发病例，不称独立物理输入。

热点阈值必须由解析网格分辨率和预注册规则决定，不能查看 `S1` 后调定。

### B2 — 公共定义域改为不下采样的细公共域

公共 32×64 P0 域会丢弃 S3/S4 和 T128/T256 的细尺度内容，可能把高频离散误差平均掉。
v02 固定：

- 空间公共域为 128 个等长 P0 段；对 S2/S3/S4 的原生分片线性牵引作精确分段积分，
  不是简单重复或抽样；
- 时间公共域为 256 个等长相位段；当前单频模型从每个离散端点的 DC/一阶谐波系数
  重建到共同相位域，并核对非 DC/一阶谐波能量低于 floor；
- 逐步功率等非单频乘积量必须在原生时间单元上守恒积分到 256 段，不能用平均牵引乘
  平均速度；
- 同时报告原生积分和公共积分，合力/功率必须守恒；
- `common_observables.npz` 只保存比较所需的公共数组，不保存全状态或系统矩阵。

### B3 — 四角交互缺陷使用同一 fine-reference 归一化

v01 的 `d(spatial increment at T256, spatial increment at T128)` 会以一个离散增量作分母，
却与按 fine solution 归一化的边际误差比较。v02 必须改为先定义混合差

\[
\Delta_{st}Q=
Q_{S4,T256}-Q_{S3,T256}-Q_{S4,T128}+Q_{S3,T128},
\]

再对标量或共同域场使用与 N4/N5 相同的 S4/T256 参考量及绝对 floor 得到
\(e_{st}\)。接受门固定为

\[
e_{st}\le 0.5\max\left(e_t^{S4},e_s^{T256},10^{-12}\right).
\]

低于 floor 的量使用绝对门，不构造不稳定相对交互比。

## 4. N1–N11 的 Supervisor 裁决

### N1 — 修订后接受

- UFL—手工装配相对 Frobenius 门收紧为 `1e-10`；
- 连续体/链 affine patch 与 SLS DC/离散谐波制造解相对误差 `<=1e-10`；
- 主动共轭多步长中心差分平台最优相对误差 `<=1e-7`；
- 矩阵相对非对称与制造作用—反作用均 `<=1e-12`。

SLS 谐波制造门比较当前 CN 离散解析响应；不得把连续时间误差混入 G0。

### N2 — 改为缩放后的明确零空间审计

- `Kmat` 对称半正定，并在当前 affine-periodic 约化空间声明恰有两个共同刚体平移
  零模；
- 支撑为半正定；`Kmat+Ks` 严格正定，不允许未声明零模；
- `G` 严格正定；
- 先用正对角作对称缩放，再审计惯性/特征值；半正定矩阵允许的最小缩放特征值下界为
  `-1e-10`，严格正定矩阵要求最小/最大缩放特征值比 `>1e-12`；
- 复杂谐波矩阵只做可逆性、残差和后向误差审计，不称正定。

若实际离散自由度使零模数与上述理论声明不一致，必须失败并解释，不能静默改门。

### N3 — 接受候选值

非零 RHS 二范数相对残差 `<=1e-10`，范数后向误差 `<=1e-12`；零 RHS 使用绝对 floor；
无零 pivot、非有限值。当前代码的 `1e-7` 仅是宽松默认值，正式 runner 必须另行执行
更严格门，不需要虚构求解器 tolerance 扫描。

### N4 — 接受

T128–T256 终局标量/波形/积分误差 `<=2e-3`，相位 `<=1e-2 rad`；高于 floor 时误差
下降，两个原始差均高于 `10F_Q` 时 `p_t>=1.5`。

### N5 — 接受并保持范围分层

S3–S4 全局 QoI `<=2e-2`，且高于 floor 时 `e34<=0.8 e23`。公共牵引场使用 N7，
热点使用 N8，不以全局均值覆盖场失败。

### N6 — 按 B3 定义接受 `0.5` 系数

`0.5` 表示混合离散交互不得超过较大边际误差的一半；必须使用同一 S4/T256 参考和
floor。该门只支持“当前有限四角联合稳定”，不外推连续极限。

### N7 — 修订后接受

- 采用 B2 的 128×256 共同域；
- 常量/线性制造场及合力误差 `<=1e-12`；
- 原生—公共合力/功率误差 `<=1e-10`；
- S3–S4 公共牵引场 `d2<=5e-2`，且高于 floor 时必须同时满足
  `d34<=0.8 d23`；
- 两界面、两分量逐项通过，不能只验合并范数。

### N8 — 修订热点定义后接受

- `S1` 只在留出阶段解盲；热点取主动幅值峰值 `t=T/2` 时的
  \(t_{e\to m,x}\) 最强压缩区；
- `eta_h=0.05`；场范围必须 `>10F_t`，且热点集覆盖不超过 25%，否则
  `HOTSPOT_DEGENERATE`；
- S3–S4 周期 Hausdorff 距离 `<=L/32`、长度加权 Jaccard `>=0.5`、峰值幅值相对差
  `<=5e-2`；
- 退化只禁止唯一热点主张，不自动否定其他数值 QoI。

### N9、N10、N11 — 接受

- 功率门保持 `ledger-minus-equilibrium <=1e-10`、逐步和整周期归一闭合 `<=1e-8`、
  drag/SLS 步耗散 `>=-1e-12 S_W`；
- harmonic 两周期状态/牵引/能量一致性 `<=1e-10`，并保留 by-construction 标签；
- 正式事务单 CPU、`<=8 GiB`、`<=3600 s`，无网络、GPU 或 Docker socket。

## 5. 数组与留出附加决定

一个 `common_observables.npz` 是独立复核场和波形收敛所必需，改为强制而非可选：

- 压缩后总大小 `<=128 MiB`；
- 只含共同域牵引、核心一周期波形、必要逐步功率、坐标和留出 S1 四角；
- 两侧作用力只保存一侧并在 manifest 规定另一侧严格取负；
- 禁止 object/pickle、全状态、系统矩阵、重复周期和逐单元 ECM 全场；
- 每个数组登记键、shape、dtype、物理方向和内容 SHA-256。

除 `S1` 场/热点外，额外预注册一个留出派生量：

\[
\chi_D=\frac{D_{SLS}}{D_{SLS}+D_{drag}},
\]

分母高于功率 floor 时，在 S1 四角上使用 N4/N5/N6 的同类终局与交互门；该量不得在
开发集上用于调整阈值。

## 6. v02 停止边界

Executor 只允许新增 v02 合同并落实上述裁决。不得修改 v01、本审阅、CURRENT_STATUS、
Figure 1、源码、测试、结果或旧证据；不得运行 solver、Docker、数值试跑、制图、三维、
整心房、流体、实验拟合或 GPU；不得暂存、提交或推送。完成后再次停在 Supervisor Gate。
