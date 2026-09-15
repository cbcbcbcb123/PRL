---
execution_id: T1.1R-Y4-3D-FIELD-FIGURE-EXECUTION-V01
plan_id: T1.1R-Y4-3D-FIELD-FIGURE-CONTRACT-V01
status: completed
scientific_audit: passed
visual_qa: passed
human_final_decision: pending
completed_at: 2026-08-12
---

# T1.1R Y4 三维 ECM 场图执行记录 v01

## 求解器来源

本图不是 FEBio 输出。模型由项目内自研 Python 求解器计算：

- 三维 ECM：线性四面体、有限变形、可压缩等容—体积本构；
- 三维细胞：封闭三角表面 DCM、分布式主动纤维、精确体积约束；
- 界面：材料 tether、作用反作用一致、非穿透不等式；
- 求解：SciPy SLSQP 的单体准静态约束最小化；
- 当前 ECM 为纯弹性峰值状态，未启用黏弹内变量演化。

## 场重构与审计

从 Y4 峰值保存节点和固定拓扑逐四面体重算 `F`、`J`、第一 Piola 应力、Cauchy 应力、von Mises 应力、主应力和能量密度。

- 四面体：480；
- `J`：`0.9935297–1.0045382`，与原求解汇总完全一致；
- 逐单元积分 ECM 能量：`2.924906221943872e-5`；
- 与原保存总 ECM 能量相对误差：`3.48e-16`；
- Cauchy 应力最大反对称分量：`0`。

## 可复现版本包

版本包：`results/hybrid/t1_1r_ecm_thickness_convergence_v01/ Figures/FigT11R_y4_3d_ecm_fields/ FigT11R_y4_3d_ecm_fields_v01_20260812/`。

其中保留：

- NPZ 源数据；
- JSON 审计记录；
- DCM–FEM、ECM 本构、导出和绘图代码快照；
- 已执行 Notebook；
- PNG/SVG；
- methods、哈希与运行环境记录。

自动核验与代理目检均通过。当前版本尚未标记为 final，等待人类终审。

## Claim guard

应力和能量密度仅为 normalized model units，不是 Pa/kPa。界面箭头仅表示方向和相对大小。本图不代表 FEBio、动态心搏、黏弹 cardiac jelly 或实验标定结果。
