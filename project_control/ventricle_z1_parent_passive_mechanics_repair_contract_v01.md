---
document_id: PRL-VENTRICLE-Z1-PARENT-PASSIVE-MECHANICS-REPAIR-CONTRACT-V01
status: frozen
frozen_at: 2026-09-12
stage: Z1-PARENT-REPAIR
base_contract: plan/active/PRL_Codex_Stage_Contracts_v03/stages/Z1_PASSIVE_SINGLE_AND_DOUBLE_CELL.md
retests: results/ventricle_z1/v01_20260911
---

# 父级 Z1 被动力学修复合同 v01

## 目标与唯一实现位置

解除父级 Z1 预检中仍有效的三个本构阻断：弯曲力与导出势能不功共轭、保守能量导出不完整、组合内力合力/合矩不闭合。唯一内核仍为
`E:\MeshCell3D\code\muse_dcm`；PRL 只保存合同、验证脚本、原始结果与图，不复制第二套内核。

Z1-B 已通过的 `reference_shape_modulus` 参考态和 Z1-C 已通过的
`symmetric_reference_quadric_proxy` 接触模式作为继承证据，不在本轮改写。多细胞桥接、主动收缩、周期载荷、Z2、ECM 与流体均不在范围内。

## 冻结修复语义

1. 体积压力仍为 `p=K ln(V0/V)`；其零参考势能必须导出为
   `Psi_V=K[V ln(V/V0)-V+V0]`，满足 `F=-grad(Psi_V)`。
2. 全局面积力保持现有节点力语义；导出
   `Psi_A=0.5 K_A(A/A0-1)^2`。本轮不修改参数数值或阈值。
3. 常量面张力的工作共轭势能为 `Psi_gamma=sum_f gamma_f A_f`；新增明确的
   `surface_potential_energy` 导出供正式账本使用，不改变真实面张力节点力。既有
   `surface_tension_energy=0.5 sum_f gamma_f A_f` 仅按 X1-K 冻结合同保留为
   legacy plotting cache，不得再冒充保守势能。
4. 弯曲能量保持现有逐铰链标量定义；将节点力改为该能量对当前四节点位置的解析负梯度。不得用有限差分力替代生产力，也不得调低弯曲模量或跳过弯曲项。
5. 所有修复分量必须保持平移/旋转客观性；每个闭合单细胞的组合内力必须满足合力与质心合矩门。

## 固定算例与原门禁

- 几何：等体积 `1:1:1` 球、`3:1:1` 长轴心肌探针、`4:4:1` 扁平心内膜探针；
- 网格：80、320、1280 faces；聚焦梯度/刚体检查使用 320 faces，完整复跑沿用原矩阵；
- 参数、扰动方向、步长序列与接触方向继承冻结的
  `results/ventricle_z1/v01_20260911/preregistration.json`；
- 最佳方向导数相对误差 `<=1e-6`；
- 刚体能量、力协变、相对合力、相对合矩均 `<=1e-10`；
- 导出能量相对残差 `<=1%`；
- 网格、Laplace、接触及后续正式工况门不得放宽。

## 执行顺序与停止规则

1. 先添加能复现旧失败的聚焦行为测试；确认修复前失败。
2. 最小修改 Python 参考实现，并复跑聚焦测试及受影响回归测试。
3. 原 `v01_20260911` 结果包保持冻结；新建版本包执行父级 Z1 原预检。
4. 任一冻结门失败，保存失败包并停止，不进入正式加载或 Z2。
5. 通过预检后，才执行父级 Z1 合同已定义的正式被动加载/卸载/恢复与细化矩阵。
6. 图像必须来自真实保存网格/数值场，至少包含模型结构、多个路径点，以及曲率、压力、节点力/能量指标；路径参数不得冒充生理时间。

## 资源与授权边界

CPU 最多 4 线程；预检总时长目标 `<=600 s`，阶段总时长目标 `<=1200 s`。不使用 GPU、不联网、不安装或升级软件、不提交、不推送、不发布、不删除旧失败包或既有文件。
