---
plan_id: T1.1R-Y4-3D-FIELD-FIGURE-CONTRACT-V01
status: approved
approved_by: human_final_reviewer
approved_at: 2026-08-12
source_execution: project_control/t1_1r_ecm_thickness_convergence_execution_v01.md
evidence_level: model_normalized_3d_field_visualization
---

# T1.1R Y4 三维 ECM 场图合同 v01

## 科学问题

在已经通过厚度工程网格不敏感门的 Y4 峰值状态中，三维 ECM 的变形、体积变化、应力和储能集中在哪里，细胞—ECM 牵引如何传入体 ECM？

## 固定输入

- `Y4=(5,4,4)` basal 峰值激活 `0.20`；
- 原始细胞节点、ECM 节点和固定拓扑四面体；
- `mu_eq=1.0`、`kappa_eq=20.0`、`mu_ve=0.0`；
- 不重新优化、不改变状态、不做空间平滑或人为插值。

## 逐单元场定义

\[
\mathbf F=\mathbf D_s\mathbf D_m^{-1},\qquad J=\det\mathbf F,
\]

\[
\boldsymbol\sigma=J^{-1}\mathbf P\mathbf F^\mathsf{T},
\]

\[
\sigma_{\mathrm{vm}}=\sqrt{\frac32\operatorname{dev}(\boldsymbol\sigma):
\operatorname{dev}(\boldsymbol\sigma)}.
\]

最大/最小主应力由对称 Cauchy 应力的特征值计算；应变能密度直接采用当前 ECM 本构的 equilibrium density。所有应力和能量密度均为当前未标定模型单位，不使用 Pa 或 kPa。

## 图面板

1. 初始与真实变形后的三维细胞—ECM 网格；
2. ECM 节点位移模量；
3. 四面体体积比 `J`；
4. von Mises 应力；
5. 最大主 Cauchy 应力；
6. ECM 应变能密度与归一化界面节点力方向。

四面体场按单元常值显示；三维几何使用实际位移，不夸大变形。界面力箭头只表达方向和相对大小。

## 验收与证据边界

- `J` 范围必须复现 Y4 汇总值；
- 逐单元积分能量必须与 Y4 保存的总 ECM 能量一致，归一化误差 `<=1e-10`；
- Cauchy 应力必须在数值对称误差内，最大反对称分量 `<=1e-12`；
- 图中必须明确标注 normalized/model units；
- 不得称为 FEBio 结果、实验标定应力、真实 kPa 应力或动态心搏应力。
