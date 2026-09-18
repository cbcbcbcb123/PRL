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
基底环全固定、外壁自由；计划内壁随动压力与心肌切平面分散主动张力。
mu=1、kappa=1000、几何及纤维分布均未标定。不是二维挤出，也不是实验心室。

**F6-S2：三维结构已建成，但运行在无载复核接口处failed。**
粗/细网格1344/3960单元，输入几何门passed；目前仅粗网格无载态实际求解。
无载自由残差1.24e-16、0次Newton更新，随后压力数组多一维导致IndexError，按约定停止。
离线最小回放定位并修正读取，原数组复核u=0、J=1、26项状态检查passed。
原失败不改写；修正后的原生适配器、压力/收缩/细网格平衡仍not_run。

![三维结构与唯一真实无载结果](../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/figures/FigS2_3d_start/FigS2_3d_start_v01_20260918/04_FigS2_3d_start_v01_20260918.png)

[结构图、Notebook和原失败](../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/index.html) ·
[执行与接口修正边界](project_control/ventricle_fem_idealized_3d_execution_v01.md)

只有1个真实无载态，不补造5帧。图为显示剖开与实际1倍坐标，不是生理时间。
一次26.462秒、单CPU/0GPU/0重跑；81测试及图件交付passed，不等于加载资格通过。

## 主要难点与唯一下一步

当前是已定位的工程接口错误，尚无三维加载成败证据。
**待确认：复用原M0无载态，核对修正接口和精确DOF映射，仅续原定余13态。**
不重算已保存无载，不扩大压力/张力或放宽1%门；首失败停。暂不加生长/FSI。

## 证据与存储

结果在已批准的E:\Temp-Projects\PRL-results，不进GitHub。
本包约10.1MiB；1719父文件、53调用文件、50项无关修改保持，仓库低于3GiB。
本地main阶段提交，未推送；无删除、安装或拉取。

- [上一阶段二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：相对受压基线缩腔约1.85%，不是三维或实验心跳。
- [旧高压失败](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)：原1%局部体积门失败保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
