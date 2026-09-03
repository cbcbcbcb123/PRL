---
plan_id: PLAN-PRL-INDEPENDENT-THEORY-MAINLINE-V02
status: approved_active
planner: codex_current_task
requested_by: human_final_reviewer
approved_by: human_final_reviewer
approved_at: 2026-09-01
parent_decision: project_control/prl_independent_theory_mainline_supplement_decision_v02.md
preserves_plan_history: project_control/prl_independent_theory_mainline_plan_v01.md
current_lifecycle: prl_figure2_spatial_tolerance_st1_a1_cycle_stability_failed_human_gate
paper_role: independent_theory_first_multiscale_prediction
realistic_journal_target: PRX_Life
conditional_stretch_targets:
  - Physical_Review_Letters
  - Nature_Physics
current_authorization: st1_a1_a2_b1_b2_only
current_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
---

# PRL 独立理论主线 v02：从局部传递律到整心房多尺度预测

## 1. Goal

建立一篇可独立投稿的理论—计算论文：先在主动心肌—黏弹 ECM—被动心内膜三层
系统中辨识可证伪的局部机械传递律，再证明 DCM–FEM 相对连续均质模型的适用边界，
最终把冻结的局部规律上推到整心房尺度，形成预登记、可留出验证的跨尺度预测。

有界中心命题保持为候选：有限厚度、松弛时间与界面连接共同控制周期机械信号的
衰减、相位滞后、热点与耗散；细胞离散性只在连续均质极限失效的局部区间提供增量
预测价值。

## 2. Inputs

- 已冻结的三层 DCM–FEM 模型、时间离散 Figure 2 v02 和全部失败证据；
- 已接受的空间/容差 ST0 与当前 ST1 A1/A2/B1/B2 合同；
- v01 中的 `De、H、K、R、epsilon_c、CV_A、ell_A/d_cell` 候选量；
- 后续经单独批准的 all-FEM 对照、H-FEM 器官几何和留出验证数据。

未经前瞻分区批准，EFE discovery/blind 数据不作为本计划当前输入。

## 3. Outputs：Figure 1–5 证据链

### Figure 1 — 三层理论与无量纲结构

输出主动心肌、有限厚度黏弹 ECM 和被动心内膜的三维方程、功率端口、边界/界面
条件、主动驱动与 SLS 记忆，并冻结最小无量纲组。

**通过门：** 单位、符号、功率共轭、体积条件以及被动、快速松弛、无黏性、薄层和
刚性界面极限全部闭合。Figure 1 只定义候选规律，不提前宣称普适性。

### Figure 2 — 数值可信度与证据边界

输出时间、ECM/DCM 空间离散、C0/C1 代数容差、共同求积/牵引投影、逐步功率闭合、
热点稳定性和终局时间触发门。

**当前执行：** 仅 ST1 A1/A2/B1/B2。A1 完成前不进入 B1；任一事务硬门失败即
fail closed。ST1 完成后返回 Human Gate。ST2/ST3 需另批。

**当前结果（2026-09-01）：** A1 的 128 个单步事务全部接受，但 cycle 2→cycle 1
的界面牵引和 ECM `Z` 周期门失败；B1/A2/B2 均未开始。项目已停在 A1 再周期化
诊断 Human Gate，详见
`project_control/prl_figure2_spatial_tolerance_st1_a1_failure_and_human_gate_v01.md`。

**允许主张：** 在最终 `D1/E2/F200N/C1/T128` 获批并完成前，只能分别报告已验证
的时间证据与固定 T64 空间敏感性，不声称联合时间—空间稳健。

### Figure 3 — `De–H` 局部传递律

以预登记的最小 `De×H` 设计为主轴，`K/R` 只作少量分层或反事实；输出位移/牵引
传递率、相位滞后、局部化长度与循环耗散的状态图、解析/降阶近似和三维数值对照。

**通过门：** 规律必须跨多个网格、边界和几何保持方向一致，并提供未参与拟合的留出
点；若只得到平滑参数响应而无简洁关系，则收缩为 PRX Life 的机制图，不上探 PRL/
Nature Physics。

### Figure 4 — 离散—连续共同极限与 DCM 增量价值

在匹配几何、材料、平均主动功和边界条件下比较 DCM–FEM、cell-resolved all-FEM
与 homogenized all-FEM；冻结共同求积和相同 QoI，建立
`epsilon_c–CV_A–ell_A/d_cell` 适用图。

**通过门：** 先证明共同极限，再讨论细胞身份的增量价值。如果 H-FEM 已能预测局部
QoI，DCM 必须降级为不必要的实现细节；只有在留出反事实上产生稳定增量预测时，才
保留 DCM patch。N1-2d 需单独批准。

### Figure 5 — 整心房跨尺度预测与独立验证

建立 H-FEM 整心房器官骨架，并在模型冻结前按几何/力学规则预登记少量局部 DCM
patch。首先单向把全局 H-FEM 位移、牵引或边界条件传给局部 patch，输出整心房
全局 QoI、局部热点及两种分辨率间的误差预算。

**双向触发门：** 只有局部修正使整器官 QoI 改变 `>5%`，或热点位置移动超过一个
细胞直径，才提交双向功率共轭耦合合同；未触发时保留单向架构。

**独立验证：** 至少留出一个几何、个体、时相或扰动，不参与参数选择和 patch 定位；
在解盲前冻结方程、参数、patch 规则和统计门。预测失败必须作为适用边界保留。

## 4. Implementation Steps 与 Human Gates

1. **Figure 2 ST1：** 完成 A1/B1、A2/B2 两周期端点与 ECM/容差裁决；Human Gate；
2. **Figure 2 ST2：** 另立合同后才执行 DCM—界面与 F200N 边界路径；Human Gate；
3. **Figure 2 ST3：** 另行批准终局细网格 T128 与 Figure 2 后续冻结；Human Gate；
4. **Figure 3：** 单独冻结无量纲定义、最小 `De×H` 设计、留出点和否证门；
5. **Figure 4：** 单独批准 N1-2d 与 all-FEM 共同极限合同；
6. **GeometryAdapter：** 只读定义器官几何到局部三层输入的接口和误差预算；
7. **Figure 5：** 单独批准 H-FEM 器官骨架、patch 预登记和单向全局到局部计算；
8. **双向决策：** 只按 `>5%` / `>1 cell diameter` 触发标准提请批准；
9. **投稿冻结：** 方程、代码、数据分区、图包、失败边界和期刊定位统一终审。

完成任一步不自动授权下一步。

## 5. Impacted Files Or Modules

当前仅更新项目控制文件。后续可能涉及三层求解器、共同求积、all-FEM 对照、
GeometryAdapter、H-FEM 器官模型和图包，但必须由相应前瞻合同逐项确定，本文不
授权修改。

## 6. Test Plan

- Figure 1：量纲、极限与功率恒等式；
- Figure 2：事务门、时间/空间/容差、共同求积与功率闭合；
- Figure 3：留出参数与跨几何方向一致性；
- Figure 4：匹配本构、共同极限和反事实预测；
- Figure 5：patch 预登记复现、全局—局部功率/边界一致性、留出预测与触发门审计。

每个 Figure package 在进入下一图前需要独立核验和 Human Figure Decision Gate。

## 7. Risks

- `De–H` 可能只有平滑响应而无简洁传递律；
- DCM 在匹配共同极限后可能没有稳定增量价值；
- 局部 patch 可能受全局边界误差支配；
- 整心房几何和实验数据可能不足以支持独立留出；
- 多尺度工程复杂度可能掩盖局部理论主线。

对应处置是缩小主张、保留 H-FEM 基线、提前冻结 patch 规则并维持单向耦合，不能靠
扩大参数海或事后挑选热点补救。

## 8. Acceptance Criteria

- Figure 1–5 形成逐级依赖而非并列演示；
- Figure 2 数值门在任何规律或器官预测前闭合；
- Figure 3 有预登记留出点和可证伪规律；
- Figure 4 明确何时需要/不需要 DCM；
- Figure 5 的 patch 定位和预测在解盲前冻结；
- 期刊上探只发生在简洁无量纲规律、跨几何稳健性和独立预测同时成立后。

## 9. Out Of Scope

本计划本身不授权 ST2、ST3、`De×H` 计算、N1-2d、GeometryAdapter 实现、器官级
几何计算、GPU worker、新外部求解器、双向 FSI、电生理、全细胞分辨整心房、大
参数海或 EFE 疾病因果建模。

## 10. Required Memory Updates

项目内以本 v02 和补充决定作为最新路线索引；v01 及历史证据全部保留。Codex 长期
记忆不在本轮自动更新，除非人类另行明确要求。
