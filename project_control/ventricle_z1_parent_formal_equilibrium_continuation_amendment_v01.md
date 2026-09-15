---
document_id: PRL-VENTRICLE-Z1-PARENT-FORMAL-EQUILIBRIUM-CONTINUATION-AMENDMENT-V01
status: frozen
frozen_at: 2026-09-12
applies_to: project_control/ventricle_z1_parent_formal_matrix_contract_v01.md
---

# Z1 正式矩阵零载平衡数值延拓补充 v01

v04 的零载平衡从仅含参考度量的形状开始，把体积、面积、恒张力和弯曲项按
`0.25, 0.50, 0.75, 1.00` 四级同时开启；每一级以上一级解为初值。最终一级严格恢复冻结的完整组合势能。

延拓只改变达到同一最终平衡方程的数值路径，不改变最终材料参数、边界条件、残力门或科学结论。沿用
`+/-0.5 L0` 坐标信赖域，并继续要求最终解不触碰边界、自由节点最大残力 `<=1e-14 N`、无翻面且最小角
`>=15 deg`。任一条件失败即保留失败包并停止。
