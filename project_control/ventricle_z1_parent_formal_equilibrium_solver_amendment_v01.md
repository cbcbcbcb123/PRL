---
document_id: PRL-VENTRICLE-Z1-PARENT-FORMAL-EQUILIBRIUM-SOLVER-AMENDMENT-V01
status: frozen
frozen_at: 2026-09-12
applies_to: project_control/ventricle_z1_parent_formal_matrix_contract_v01.md
---

# Z1 正式矩阵零载平衡求解器补充约束 v01

`parent_formal_v02_20260912` 的扁平细胞无界 L-BFGS-B 搜索进入退化网格分支，优化器终止标志与真实残力矛盾。
从 v03 起，所有平衡搜索的每个无量纲自由坐标限制在该次搜索初值 `+/-0.5 L0` 的信赖域内。

该边界只用于阻止数值搜索跨越非物理退化分支，不是细胞的物理弹簧或空间边界条件。接受解必须同时满足：

- 自由节点最大残力 `<=1e-14 N`；
- 无翻面，最小三角形角 `>=15 deg`；
- 任一坐标距离信赖域边界至少 `1e-6 L0`，否则视为边界激活并失败；
- 原材料参数、端区、体积门、动态时间步和全部科学门禁不变。

v01 输入错误包和 v02 退化分支包均保留，不覆盖或删除。
