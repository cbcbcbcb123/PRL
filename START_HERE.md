---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-18
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流的相互作用，不恢复DCM。
先做理想化三维模型，以morphoHeart公开资料约束形态；后续通过版本化输入替换为自有实验。
研究顺序为：固体资格 → 三维主动心室 → 双向流固耦合 → 基础生长 → 力学生长反馈 → ECM反馈。
静态公开形态不自动提供心动周期、材料、压力或同一个体连续生长率。
见[已采纳路线与证据边界](project_control/ventricle_development_fsg_idealized_public_data_decision_v01.md)。

## 当前模型与本轮结果

当前为原图像外轮廓上的二维P2位移/DG2压力三角形、三维平面应变有限变形NH固体。
只有外边界来自72 hpf Fish 4图像，内腔及心内膜/ECM/心肌层界为构造；三层被动参数相同。
mu=1、kappa=1000未标定；内壁随动压力、外壁自由，A固定ux/uy、B固定uy去除刚体运动，主动关闭。

**F6-S1-S7首压力两网格资格passed**：原保存M0/M1网格各计算零载和`p/mu=0.02`，4态全部接受。
粗/细网格局部max|J−1|=0.323434%/0.358062%，均低于原1%门；
相同位移网格的旧CG1对应6.71167%/11.15248%，旧失败仍保留。
粗/细腔面积扩张20.056188%/20.105502%，差0.0493142个百分点、相对差0.245277%。
几何、材料和验收门未变，支持局部压力离散影响体积约束的解释；不能直接推广到三维或严格不可压极限。
两级首压力通过不等于完整压力序列、热点收敛或实验吻合。图中是1倍形变、真实载荷态，不是心动时刻。
腔室面积变化不等于壁组织体积变化，位移也不等于应变。

![实际三层结构、1倍受压形变应力及原局部体积门](../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/figures/FigS1S7_qualification/FigS1S7_qualification_v01_20260918/04_FigS1S7_qualification_v01_20260918.png)

[结构、4个真实状态应力图与Notebook](../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/index.html) ·
[执行、指标与证据边界](project_control/ventricle_fem_contour_dg2_execution_v01.md)

## 核心难点与唯一下一步

首压力的局部体积超限已消除；细网格J峰值仍略高于粗网格，热点尚未证明收敛。
材料、压力、无应力参考态及三层界面未由自有实验标定；当前仍是二维固体资格，不是完整心动模型。

唯一下一步待确认：从本轮两网格已接受0.02态继续原被动压力0.04/0.06/0.08，最多6个新态。
不重算零载/0.02或圆环，材料/1%门保持、单CPU/0GPU/首失败即停。
完整被动资格通过后再加入心肌主动收缩；主动/三维/FSI/生长本轮not_run。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
本包约176.1MiB；1194父/祖先文件和50项无关修改保持；110测试+21子测试、40项独立范围检查通过。
一次122.067秒容器、24个Newton向量；0GPU/圆环重算/网格生成/安装/拉取/删除/自动重跑。
交付层唯一有限差分字段的跨平台1.33e-12舍入差已单独核验，原失败记录和全部物理门保留。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-S6两网格DG2圆环完整被动资格](../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html)：已通过，不在本轮重算。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
