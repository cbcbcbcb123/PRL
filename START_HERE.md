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

**F6-S2-D1：细网格仍未通过局部体积门，单纯加密未解决问题。**
M0/M1为1344/3960单元；同p/mu=0.01、Ta=0，腔体积增加1.0895%/1.1059%。
整体响应相对差1.48%，但max abs(J-1)=1.5227%/1.4496%，两者都超过原1%门。
细网格仅改善局部最大值约4.8%；120个超限单元全部与固定基底相接。
两网格均达到数值平衡，非接口或MUMPS失败。M1零载passed；压力态不接受，停止后续加载。

![粗细网格结构、同压力应力与局部体积偏差](../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/figures/FigS2D1_3d_mesh_comparison/FigS2D1_3d_mesh_comparison_v01_20260918/04_FigS2D1_3d_mesh_comparison_v01_20260918.png)

[结构图、Notebook和粗细对照](../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html) ·
[本次执行及边界](project_control/ventricle_fem_3d_fine_pressure_execution_v01.md)

本轮只新增M1无载/首压力，M0原数据保留；保存全部Newton状态，图为真实1倍形变和共同色标。
一次44.488秒、单CPU/0GPU/0重跑；91测试及图件交付passed，不等于加载资格通过。

## 主要难点与唯一下一步

整体响应接近但局部体积仍失真；网格/曲面近似/夹持/压力空间的贡献尚未分离。
**待确认：先形成近不可压体积约束离散的单变量资格方案。**
暂不改材料、载荷或基底；审查三维压力表示、稳定性/锁死及小基准，不直接照搬二维结论。
方案审查不启动FEM；新的小基准/壳对照再按合同确认。不继续收缩、生长或FSI。

## 证据与存储

结果在已批准的E:\Temp-Projects\PRL-results，不进GitHub。
本包约39.57MiB；1940父文件、75调用文件、50项无关修改保持，仓库低于3GiB。
本地main阶段提交，未推送；无删除、安装或拉取。

- [上一阶段二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：相对受压基线缩腔约1.85%，不是三维或实验心跳。
- [旧高压失败](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)：原1%局部体积门失败保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
