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

**F6-S2-R：原生接口已通过，首个三维压力态因局部体积门failed而停止。**
粗/细输入1344/3960单元，复用原M0无载，不重算。p/mu=0.01、Ta=0经3次Newton平衡，残差1.69e-16。
腔体积扩大1.0895%，但局部max abs(J-1)=1.5227%，超过原1%门；此态不接受。
96个超限单元全部与固定基底相接，非相邻单元最大0.5296%。不是接口或线性求解失败。
原失败保留；后续12态、收缩、细网格平衡、生长及FSI均not_run。

![三维结构、首压力应力与局部体积失败](../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/figures/FigS2R_3d_overview/FigS2R_3d_overview_v01_20260918/04_FigS2R_3d_overview_v01_20260918.png)

[结构图、Notebook和失败定位](../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/index.html) ·
[本次执行及边界](project_control/ventricle_fem_idealized_3d_resume_execution_v01.md)

只展示原无载与首压力实存状态，另保存4个Newton状态；不补造5个平衡态或生理时间。
一次31.453秒、单CPU/0GPU/0重跑；87测试及图件交付passed，不等于加载资格通过。

## 主要难点与唯一下一步

当前是基底邻近的局部体积失真；弱平衡满足不代表逐点体积约束满足。
网格、夹持和压力空间贡献尚未分离。
**待确认：已有M1网格仅做零载与同p=0.01两个状态，对照保留M0失败。**
材料/边界/离散/1%门保持，首失败停；不继续收缩、生长或FSI。

## 证据与存储

结果在已批准的E:\Temp-Projects\PRL-results，不进GitHub。
本包约16.94MiB；1817父文件、71调用文件、50项无关修改保持，仓库低于3GiB。
本地main阶段提交，未推送；无删除、安装或拉取。

- [上一阶段二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：相对受压基线缩腔约1.85%，不是三维或实验心跳。
- [旧高压失败](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)：原1%局部体积门失败保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
