---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-18
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流相互作用，不恢复DCM。
先理想化三维及公开资料，后续替换自有实验；当前几何尚未用morphoHeart标定。
路线：三维固体 → 生长公式及规定式三维生长 → 双向FSI → 力学生长/ECM反馈。
[路线决定](project_control/ventricle_3d_before_growth_decision_v01.md)不自动授权后续全部运行。

## 当前模型与结果

三维半椭球壳，心内膜/ECM/心肌三域；有限变形NH、P2位移/P1压力四面体。
基底环全固定、外壁自由、内腔随动压力；三维主动张力尚未运行。
mu=1、kappa=1000、几何与纤维分布均未标定，不是实验心室。

**F6-S2-D2B：完成一个同边界非结构化候选，质量门未通过，未进入FEM。**
边界和层界三角形完全保持；3960→2611四面体，预计DOF 19119→13483。
整体q低端5%分位提高4.44%，未达预设5%；最小二面角6.638°→6.811°，
但少数ECM单元最差q由0.222降至0.029。不能凭外观或中位质量接受新网格。

![原M1与非结构化U1的实际网格及质量分布](../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/figures/FigS2D2B_unstructured/FigS2D2B_unstructured_v01_20260918/04_FigS2D2B_unstructured_v01_20260918.png)

[图、Notebook、原始候选及复核](../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/index.html) ·
[执行记录](project_control/ventricle_fem_3d_unstructured_execution_v01.md)

本次原调用还触发节点重编号读取错误；失败保持，只读解析已存MSH得到上述质量结果。
适配器已修订并补测，但完整容器修复后未再运行。132测试及21子测试、离线复算和图件passed。
**新增FEM求解0；没有新的应力、形变或心动结果。**

## 主要难点与唯一下一步

原M0/M1压力态的局部体积偏差仍为1.5227%/1.4496%，超过1%门；
M1全部120个超限单元邻接基底。单纯把规则剖分换成非结构化尚未解决问题。
形状质量、薄层分辨率、夹持及近不可压压力表示的贡献尚未分离。

**唯一下一步：形成近不可压三维混合离散的小基准资格方案，先验证稳定性和局部体积控制。**
不直接照搬二维压力空间，不继续网格参数试错，不修改1%门，不进入生长/FSI；
新的具体基准需确认后执行。本候选授权已消耗，无自动重跑。

## 证据与存储

结果保存在已批准的E:\Temp-Projects\PRL-results，不进GitHub；本包约21.00MiB。
2135项内部/外部保护文件和50项无关修改保持。代码仓低于3GiB；本地main阶段提交，未推送。
无删除、安装、拉取或GPU。任务临时检查目录保留，未获批准不清理。

- [此前形状/J相关审查](../PRL-results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918/index.html)：有反例，未认定单一根因。
- [原三维压力失败](../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html)：原场量与失败保留。
- [二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：缩腔约1.85%，不是三维或实验心跳。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
