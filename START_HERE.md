---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-18
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流相互作用，不恢复DCM。
先理想化三维及公开资料，后续替换自有实验；本轮几何尚未用morphoHeart标定。
已同意：三维固体 → 生长公式及规定式三维生长 → 双向FSI → 力学生长反馈 → ECM反馈。
[路线补充决定](project_control/ventricle_3d_before_growth_decision_v01.md)不是后续全部运行授权。

## 当前模型与结果

真正三维半椭球壳，构造心内膜/ECM/心肌三域；P2位移/P1压力四面体。
基底环全固定、外壁自由；内壁随动压力，心肌切平面分散主动张力尚未运行。
mu=1、kappa=1000、几何及纤维分布均未标定。不是二维挤出，也不是实验心室。

**F6-S2-D2A：已完成网格质量审查；“网格太规则”不是已证实的单一原因。**
M0/M1为1344/3960单元，原max abs(J-1)=1.5227%/1.4496%，仍都超过1%门。
M1形状有所改善：最小二面角4.41°→6.64°、最小半径比质量q为0.151→0.222（正四面体为1）。
但120个体积超限单元仍全部与固定基底相接，其中72个没有触发预先声明的形状筛查；
另384个远离基底的形状标记单元无一超体积门。形状、位置、薄层与压力表示的影响尚未分离。
三维被动力学均已数值平衡，但加载质量未接受；本次仅离线重算，新增FEM求解0。

![粗细参考网格质量、同单元体积误差及全部单元散点](../PRL-results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918/figures/FigS2D2A_mesh_quality/FigS2D2A_mesh_quality_v01_20260918/04_FigS2D2A_mesh_quality_v01_20260918.png)

[结构/质量图、Notebook及逐单元报告](../PRL-results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918/index.html) ·
[本次执行及边界](project_control/ventricle_fem_3d_mesh_quality_execution_v01.md)

本轮图将原压力场映射到参考网格以对齐单元，不是新的变形状态或生理时间。
121项测试及21项子测试、独立复算和图件交付passed；原科学压力门failed不变。

## 主要难点与唯一下一步

形状筛查不是正确性证明；全部超限紧邻基底，心内膜/ECM厚度方向仍各1个分层区间。
**唯一下一步：同M1多面体边界的内部非结构化剖分对照，先验收几何/质量。**
已发现固定本地镜像中的Gmsh模块，实际导入/网格生成尚未验证。
[有界候选合同](project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md)待执行确认：
只做1个候选，先保持边界与层界面片完全一致；合格才最多zero/p=0.01两态，首失败停。
不同时改变曲面、材料、压力空间、载荷或基底，不放宽1%门，不继续收缩、生长或FSI。

## 证据与存储

结果在已批准的E:\Temp-Projects\PRL-results，不进GitHub。
本包约33.90MiB；2068项内部/外部既有保护文件、50项无关修改保持，仓库低于3GiB。
本地main阶段提交，未推送；无删除、安装或拉取。

- [上一阶段二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：相对受压基线缩腔约1.85%，不是三维或实验心跳。
- [旧高压失败](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)：原1%局部体积门失败保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
