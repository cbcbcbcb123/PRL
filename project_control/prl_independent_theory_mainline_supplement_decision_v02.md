---
decision_id: DECISION-PRL-INDEPENDENT-THEORY-MAINLINE-SUPPLEMENT-V02
status: approved
decider: human_final_reviewer
decided_at: 2026-09-01
canonical_plan: project_control/prl_independent_theory_mainline_plan_v02.md
supersedes_strategy_only:
  - project_control/prl_independent_theory_mainline_plan_v01.md
preserves:
  - project_control/prl_independent_theory_mainline_decision_v01.md
  - project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
  - project_control/prl_figure2_spatial_tolerance_st0_acceptance_and_st1_authorization_decision_v01.md
active_execution_authorization: st1_a1_a2_b1_b2_only
next_execution_gate: prl_figure2_spatial_tolerance_st1_human_gate
---

# PRL 独立理论主线补充决定 v02

## 人类终审决定

人类终审批准《PRL 独立理论主线 v02：从局部传递律到整心房多尺度预测》作为项目
最新终局目标，并要求开始将该目标落到项目控制文件。

本决定只更新论文终局路线与 Figure 1–5 的依赖关系，不追溯改写 v01、既有合同、
失败记录、冻结 Figure 2 或历史状态，也不构成对全部后续计算的批量授权。

## 最新 Figure 1–5 主线

1. **Figure 1 — 三层理论：** 主动心肌—有限厚度黏弹 ECM—被动心内膜的方程、
   功率端口、边界条件与无量纲结构；
2. **Figure 2 — 数值可信度：** 时间、空间、代数容差、功率闭合、共同求积与失败
   边界；
3. **Figure 3 — `De–H` 传递律：** 幅值、相位、局部化和耗散的最小状态图与可证伪
   传递规律；
4. **Figure 4 — 离散—连续共同极限：** DCM–FEM、cell-resolved all-FEM 与
   homogenized all-FEM 的匹配本构、共同极限和适用域；
5. **Figure 5 — 整心房跨尺度预测与独立验证：** 用 H-FEM 器官骨架和预登记局部
   DCM patch，把局部传递律上推为整心房 QoI 与热点预测，并在留出几何/扰动/实验
   上检验。

## 整心房架构决定

- 整体采用 homogenized FEM（H-FEM）器官骨架；
- 只在预登记的局部区域嵌入 DCM patch，禁止先看热点再挑 patch；
- 第一版只做单向 `global H-FEM → local DCM patch`；
- 只有局部修正导致整器官 QoI 改变超过 `5%`，或预测热点移动超过一个细胞直径，
  才可提请人类批准双向功率共轭耦合；
- 不以全细胞分辨整心房作为默认路线。

## 期刊定位

现实投稿目标为 **PRX Life**。只有同时获得简洁无量纲规律、跨几何稳健性和独立
留出预测，才考虑 **Physical Review Letters / Nature Physics**。期刊目标是证据
门后的战略判断，不是预先保证。

## 当前执行边界

当前只继续已经批准的 Figure 2 ST1。A1 正在运行；必须先完成当前工况并遵守既有
fail-closed。ST1 完成后停止在 Human Gate。

ST2、ST3、`De×H`、N1-2d、GeometryAdapter、整心房模型分别另立前瞻合同并逐级
批准。未经明确批准，不启动器官级几何计算、GPU worker、新外部求解器、双向 FSI、
电生理、全细胞分辨整心房或大参数海。
