---
document_id: PRL-VENTRICLE-Z1C-CONTACT-DISCRETIZATION-REPAIR-CONTRACT-V02
status: frozen
frozen_at: 2026-09-11
stage: Z1-C-REPAIR
supersedes: PRL-VENTRICLE-Z1C-CONTACT-DISCRETIZATION-REPAIR-CONTRACT-V01
reason: v01_reference_vertex_quadrature_failed_four_of_five_refinement_cases
---

# Z1-C 接触面积测度与离散修复合同 v02

## v01 处置

v01 的参考顶点面积模式已完成工程试算：面积变化路径达到功共轭，且球形
medium→fine 峰值反力变化达到 `<=5%`；但长轴和扁平细胞的 4/4 方向仍失败，
相对变化为 `24.5%–65.9%`。因此该模式只保留为已否证的诊断分支，不用于
Z1-C 科学重跑，也不得据此把 Z1-C 标记为通过。

## 修订后的预注册修复

新建对称参考面求积模式：

- 每个源三角面的 3 个二阶面积求积点分别使用固定参考面面积的 `1/3`；
- 参考面面积只由捕获的参考边长重建，不使用当前面积；
- 每个源求积点对每个目标细胞只选择一个最近的合格三角面；
- 源面按固定重心坐标分配力，目标面按最近点重心坐标分配反力；
- 双向 surface→surface 求积各乘 `1/2`；
- 黏附和排斥的细胞表型缩放均采用两侧几何平均；
- 没有显式参考态时在任何力、接触面积或接触计数改变前失败关闭。

既有 `legacy_target_face_all` 默认模式不变。v01 的
`symmetric_reference_vertex` 仅作为失败机制的可审计诊断模式保留，Z1-C runner
必须显式选择新的参考面模式。

## 门禁

RED→GREEN 工程门与 Z1-C 原门完全沿用 v01，不降低误差或网格收敛阈值。
新增要求：每个源求积点/目标细胞最多选择一个目标面；求积点次序或面 ID 不得
改变总反力、能量及活动计数。

## 可视化与范围

v01 的 11 个加载/卸载路径点、共同视角/色标和“lambda 仅为路径参数”的要求
全部沿用。授权边界不变：不启动 GPU、不安装、不提交、不推送、不进入多细胞
桥接或 Z2。
