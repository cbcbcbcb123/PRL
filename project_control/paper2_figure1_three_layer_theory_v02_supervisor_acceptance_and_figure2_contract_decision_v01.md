---
decision_id: DEC-PAPER2-FIGURE1-THEORY-V02-ACCEPT-FIGURE2-CONTRACT-V01
status: approved_under_human_standing_authority
decider: independent_supervisor
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_contract: project_control/paper2_figure1_three_layer_theory_contract_v02.md
accepted_contract_sha256: a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7
prior_contract: project_control/paper2_figure1_three_layer_theory_contract_v01.md
prior_review: project_control/paper2_figure1_three_layer_theory_contract_v01_supervisor_review_v01.md
accepted_label: FIGURE1_THEORY_CONTRACT_ACCEPTED_V02
next_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01.md
execution_authorized: figure2_contract_drafting_only
---

# Paper 2 Figure 1 理论合同 v02 Supervisor 验收与 Figure 2 合同决定 v01

## 1. 决定

Supervisor 接受 `paper2_figure1_three_layer_theory_contract_v02.md`，正式标签为
`FIGURE1_THEORY_CONTRACT_ACCEPTED_V02`。该合同冻结当前二维三层理论定义：离散心内膜
链、主动心肌 FEM、黏弹 ECM FEM、两个 penalty 界面、底部弹性支撑和可选腔面外载端口。
心肌 DCM 不属于模型、比较、参数或后续共同极限。

v01 保留为首轮草案；其 `UNRESOLVED_CANDIDATE_CHOICE` 审阅记录和 v02 修订共同构成
完整决策链，不覆盖旧文件。

## 2. 独立验收结果

| 检查项 | 独立结果 | 状态 |
|---|---:|---|
| 基线与 upstream | `73fdd570...`，0/0 | PASS |
| 四个活跃源码哈希 | 与 v02 锚点一致 | PASS |
| 周期链 affine 分解 | 轴向差显式含 `bar-epsilon * delta-x` | PASS |
| 心肌主动能与功率 | 能量交叉项、右端及控制功符号一致 | PASS |
| ECM SLS | 能量、应力、演化与非负耗散一致 | PASS |
| 界面物理力 | 四个方向与源码内部残量一一映射、成对相消 | PASS |
| CN 离散增量 | 随机二次—双线性能量复算误差 `1.42e-14` | PASS |
| 无量纲组 | 界面、链、弯曲、体/线阻尼指数全部归零 | PASS |
| 快慢松弛 | DC 与振荡分量区分正确 | PASS |
| C1–C6 | 3 项采用/冻结，3 项明确排除或延期 | PASS |
| 文本完整性 | 667 行；无尾随空格；未转义 `widetilde` 为 0 | PASS |

## 3. 冻结的理论选择

1. `H` 改变采用源码一致路径：固定材料、泊松比、松弛时间、`L/T` 和两个无量纲
   界面刚度，只改变 ECM 几何厚度；
2. Figure 1–3 固定 `R_M` 与三组泊松比，`De` 只通过改变 `tau`；
3. 论文图和正文采用域间物理作用力，源码 `reported/internal-residual traction` 只用于
   方法映射；
4. 可变主动场族延期到 Figure 4 合同；Figure 1/3 不把 `Lambda_A` 当已扫描轴；
5. 腔面载荷在 Figure 1 只作为可选规定外载端口，Figure 3 主驱动另行预登记；
6. 无体/线阻尼奇异极限从 Figure 1 主张、面板和当前必验门中排除。

## 4. 证据边界

本验收只接受方程、符号、功率端口、无量纲组和否证结构。它不是数值可信度、生理
有效性、EFE 机制、实验验证或 Nature Physics 级普适规律的证明。任何 Figure 1 图件
仍须按已冻结面板合同制作和单独审阅，不能把候选控制量画成已观察相图。

## 5. 下一步授权

下一步只授权起草版本化
`project_control/paper2_figure2_fem_only_numerical_credibility_contract_v01.md`，用于冻结当前
FEM-only 架构的时间、空间、代数、共同投影和离散功率可信度设计。合同起草不得运行
solver、Docker、参数扫描或生成结果；不得修改代码、Figure 1 合同或旧证据。

Figure 2 合同必须重新从活跃 `paper2_hybrid` API 与已有数值证据出发，不得迁移旧
DCM–FEM identity 门、旧 Figure 2 结论或心肌 DCM 路线。合同完成后再次停在 Supervisor
Gate；未验收前不授权计算、三维、整心房、流体、实验拟合或 GPU。
