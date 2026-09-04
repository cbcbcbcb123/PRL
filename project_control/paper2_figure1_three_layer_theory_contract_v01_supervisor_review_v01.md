---
review_id: REV-PAPER2-FIGURE1-THREE-LAYER-THEORY-V01-SUPERVISOR-V01
status: revision_required
reviewer: independent_supervisor
reviewed_at: 2026-09-04
reviewed_contract: project_control/paper2_figure1_three_layer_theory_contract_v01.md
reviewed_contract_sha256: b7b0b35823a2c6ebe3152806fd89e2e0740e876bd9a41c84a3736439fceb9be0
baseline_commit: 73fdd570fa7204806bd704a84c44f3eaf804e0e6
failure_label: UNRESOLVED_CANDIDATE_CHOICE
next_required_artifact: project_control/paper2_figure1_three_layer_theory_contract_v02.md
execution_authorized: document_revision_only
---

# Paper 2 Figure 1 三层理论合同 v01 独立 Supervisor 审阅 v01

## 1. 裁决

v01 的物理主线、源码映射、主动功符号、SLS 能量—耗散结构和两个界面的作用—反作用
方向总体正确，但不能直接接受。合同自身第 11 节要求 C1–C6 被裁决或显式排除，而 v01
仍把六项全部保留为未决，因此正式返回 `UNRESOLVED_CANDIDATE_CHOICE`，要求生成 v02，
不得覆盖 v01。

本次返回不否定固定架构，也不授权修改源码或运行求解器。

## 2. 已通过的独立复核

| 检查项 | 独立结果 | 状态 |
|---|---|---|
| 基线与 upstream | `73fdd570...`，0/0 | PASS |
| 四个源码 SHA-256 | 与 v01 全部一致 | PASS |
| 心肌主动本征应变 | 能量、应力、右端和主动共轭符号一致 | PASS |
| ECM SLS | 平衡/Maxwell 并联、内部变量演化、非负耗散一致 | PASS |
| 两界面 | `rep` 为第一命名域内部残量；两域物理力严格反向 | PASS |
| 连续功率闭合 | 支撑作为外端口或总储能的两种分区等价 | PASS |
| CN 离散闭合 | 二次—双线性能量中点增量为精确离散增量 | PASS |
| 快慢松弛 | 振荡分量与 DC 分量已正确区分 | PASS |
| 证据边界 | 未外推到非线性、EFE、流体、整心房或实验 | PASS |

## 3. v02 必须修复的三项阻断

### B1 — 周期链的 affine 宏观应变必须进入公式

v01 文字说明链包含共享 affine 宏观应变，但能量式只写了周期节点位移差，容易被解释
为普通周期链。v02 必须显式定义

\[
\mathbf u_i^n=\widetilde{\mathbf u}_i^n+\bar\epsilon x_i\mathbf e_x,
\qquad \widetilde{\mathbf u}_{i+N}^n=\widetilde{\mathbf u}_i^n,
\]

并把轴向单元差写成
\(\widetilde u_{i+1,x}^n-\widetilde u_{i,x}^n+\bar\epsilon\Delta x\)。法向一阶差和
二阶弯曲差使用周期涨落。这样才与 `_endocardium_transform` 逐项一致。

### B2 — 心内膜线/弯曲刚度组必须消除量纲歧义

v01 的 `k_x^n/E_\infty L` 与 `\kappa_n/E_\infty L^3` 书写存在乘除歧义。v02 必须改为

\[
\mathbf R_n=\left(
\frac{k_x^n}{E_\infty L},
\frac{k_y^n}{E_\infty L},
\frac{\kappa_n}{E_\infty L^3}
\right),
\]

并用二维单位厚度能量逐项说明其无量纲性。其余含连续、界面、支撑、阻尼和线载荷的
组也应使用显式分式，避免同类歧义。

### B3 — C1–C6 必须按下节裁决写入合同正文

v02 不得继续把全部六项笼统标为未决，也不得让已排除项继续阻断 Figure 1 验收。

## 4. Supervisor 对 C1–C6 的裁决

1. **C1 薄层路径：选定源码一致路径。** 变化几何厚度 `H` 时固定
   \(E_\infty,E_M,\nu_\infty,\nu_M,\tau,L,T\) 以及两个无量纲界面刚度。不得同时保持
   \(Eh\) 或 \(E/h\)；这些属于以后另立的反事实路径。薄层极限因此允许跨层体刚度
   增强并最终受界面串联柔度限制。
2. **C2 主动场族：从当前 Figure 1/3 执行范围排除。** 当前只定义 `uniform` 和冻结
   `S1`；不新增随机场、传播相位或可变波长。\(\Lambda_A\) 只作为 Figure 4 前必须另立
   合同的候选控制量，不得画成已扫描轴。
3. **C3 ECM 流变参数化：当前冻结。** Figure 1–3 固定三组泊松比和
   \(R_M=E_M/E_\infty\)，只改变 \(De\) 时改变 \(\tau\)。若以后改变泊松比或体积/剪切
   松弛，必须使用体积与剪切 Maxwell 比并另立合同。
4. **C4 论文牵引命名：选用物理作用力。** 图中箭头和正文使用“第二域施加于第一域”
   的物理力；源码 `reported/internal-residual traction` 仅保留在方法映射中。必须显式给出
   \(\mathbf t_{e\to m}=-\mathbf t_{me}^{rep}\)、
   \(\mathbf t_{m\to e}=+\mathbf t_{me}^{rep}\)、
   \(\mathbf t_{e\to n}=-\mathbf t_{ne}^{rep}\) 和
   \(\mathbf t_{n\to e}=+\mathbf t_{ne}^{rep}\)。
5. **C5 腔面端口：Figure 1 只展示为可选外部端口。** Figure 1 不决定 Figure 3 的主
   驱动工况；该选择延期到 Figure 3 预登记合同。在此之前不得把腔面载荷混入候选
   `De x H` 主规律。
6. **C6 无阻尼奇异极限：从 Figure 1 主张和必验门排除。** 只保留为未来数学适定性
   问题；未另证代数/微分代数极限前，不在面板 e、Figure 2 最小门或正文机制结论中使用。

## 5. v02 停止边界

Executor 只允许新增 v02 合同并修复上述内容。不得修改 v01、本审阅、CURRENT_STATUS、
源码、测试或结果；不得运行 solver、Docker、参数扫描、制图、三维、整心房、流体、
实验拟合或 GPU；不得执行 Git 暂存、提交或推送。完成后再次停在 Supervisor Gate。
