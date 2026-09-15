---
plan_id: PLAN-PRL-INDEPENDENT-THEORY-MAINLINE-V03
status: approved_active_architecture
approved_by: human_final_reviewer
approved_at: 2026-09-04
architecture_decision: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
preserves_plan_history: project_control/prl_independent_theory_mainline_plan_v02.md
active_model: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
fluid_status: deferred_to_separate_contract
strategic_design_target: Nature_Physics
evidence_based_fallback_targets:
  - PRX_Life
  - Physical_Review_Letters_if_scope_and_format_fit
---

# PRL 独立理论主线 v03：主动心肌 FEM 经黏弹 ECM 向离散心内膜传递

## 1. 中心问题与证据边界

当前唯一活跃模型由主动心肌 FEM、黏弹 ECM FEM 和离散心内膜细胞链构成。论文研究：
有限厚度、松弛时间、界面连接和主动场空间尺度如何共同决定周期机械信号的幅值、相位、
热点与耗散，以及主动场粗粒化与界面传递何时不对易。

本路线先做无流体的固体三层理论；真实流场只可在后续独立合同中分层加入。数值收敛不
等于生理真实性，理想化二维结果不外推到整心房、EFE、实验或临床。

**期刊口径：** Nature Physics 是问题设计、机制深度、普适性和独立预测的战略目标，
不是当前成熟度判断。现阶段证据远未达到 Nature Physics 投稿标准；只有后续出现简洁
无量纲规律、跨几何稳健性和独立留出预测，才保留该目标。否则在后续证据门依据实际
贡献降档至 PRX Life，或在篇幅与结果形态更适合时评估 Physical Review Letters。

## 2. 历史路线处置

Paper 2 M2A v01–v07 的双表示合同、源码、测试、运行记录和结果包统一标记为
`retired_historical_evidence`。它们只用于解释路线终止和审计历史，不是新架构的验证
数据，不迁移为活跃 API，也不进入后续参数扫描或论文机制证据。

## 3. Figure 1–5 证据链

### Figure 1 — 三层理论与功率端口

给出主动心肌连续体、有限厚度 SLS ECM 和离散心内膜细胞链的方程、周期边界、界面
penalty、主动功、腔面功、阻尼与黏弹耗散，并冻结最小无量纲组。

**通过门：** 单位、符号、作用反作用、离散功率恒等式、被动/无黏性/快速松弛/薄层/
刚性界面极限闭合。Figure 1 只定义候选规律。

### Figure 2 — FEM-only 数值可信度

验证时间、心肌/ECM 空间离散、代数容差、共同求积、牵引投影、逐步功率闭合、热点与
终局细网格时间触发门。v08 迁移等价门只证明新代码重现历史 FEM 臂，不替代新的空间、
时间和容差验证。

**通过门：** 当前架构自身完成前瞻冻结的联合时间—空间—容差证据后，才能进入规律图。

### Figure 3 — `De × H` 机械传递状态图

用最小预登记 `De × H` 设计输出位移/牵引传递率、相位滞后、局部化长度和循环耗散；
界面连接与主动场异质性只作有限分层或反事实。

**通过门：** 规律跨多个网格、边界和几何方向一致，并通过未参与拟合的留出点。若只
得到平滑参数响应，则收缩为 PRX Life 机制图，不上探 PRL/Nature Physics。

### Figure 4 — 主动 FEM 家族的粗粒化适用域

在匹配几何、材料、平均主动功、边界条件和共同 QoI 下，比较
cell/meso-resolved active FEM 与 homogenized active FEM。以主动场相关长度、各向异性、
空间变异和 ECM 松弛尺度建立粗粒化适用域，检验“先粗粒化主动场”与“先经界面传递”
是否不对易。

**通过门：** 先证明共同极限，再报告细尺度主动场是否在留出反事实上提供稳定增量
预测；不得用事后挑选热点制造差异。

### Figure 5 — 整心房预测与独立验证

建立主动心肌 H-FEM＋黏弹 ECM＋离散心内膜的整心房骨架，输出全局运动、局部牵引/
应变热点和分辨率误差预算。方程、参数、局部加密规则和统计门在解盲前冻结，并至少留出
一个几何、个体、时相或扰动。

流体不在第一版 Figure 5 中；只有固体模型证据闭合后，才另立单向或双向流固耦合合同。

## 4. 顺序与决策门

1. v08 完成新命名空间、静态架构门和六工况迁移等价；
2. 单独冻结 Figure 1 方程与极限；
3. 单独执行 Figure 2 新架构数值可信度；
4. 预登记 Figure 3 的无量纲设计、留出点和否证门；
5. 另立 Figure 4 FEM 家族共同极限合同；
6. 另立 Figure 5 几何、加密规则和独立验证合同；
7. 证据链完整后再决定投稿目标和是否加入流体层。

每一步完成后均停在独立审阅门，不自动授权下一图。

## 5. 当前未授权范围

本计划不授权 Figure 2 后续求解、`De × H` 参数扫描、Figure 4 粗粒化计算、三维、整心房、
真实流场、CFD/FSI、实验拟合、GPU worker、大参数海或论文成稿。v08 只执行架构迁移与
六工况 S4/T64/D0 等价门。
