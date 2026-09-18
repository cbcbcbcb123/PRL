---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-18
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流相互作用，不恢复DCM。
先做理想化三维模型，用morphoHeart公开资料约束形态，后续版本化替换自有实验。
顺序为固体资格 → 三维主动心室 → 双向FSI → 基础生长 → 力学生长反馈 → ECM反馈。
静态公开形态不自动给出心动周期、材料、压力或同一个体的连续生长。
见[已采纳路线](project_control/ventricle_development_fsg_idealized_public_data_decision_v01.md)。

## 当前模型与结果

原外轮廓的二维P2位移/DG2压力三角形、平面应变有限变形NH。
只有72 hpf Fish 4外边界来自图像，内腔/心内膜/ECM/心肌界面是构造；三层同被动材料。
mu=1、kappa=1000未标定；内壁随动压力、外壁自由，A固定ux/uy、B固定uy。
外层心肌使用既有主动能量，参考纤维是假设的原点环向，不是实验测得或逐点轮廓切向。

**F6-S1-S9低压主动收缩对照passed。** 固定p/mu=0.02，两个网格各增加四个张力态，
8个新平衡全部接受，受压零张力基线只读复用。

| Ta/mu | M0缩腔量 | M1缩腔量 |
|---|---:|---:|
| 0.025 | −0.4820% | −0.4815% |
| 0.050 | −0.9500% | −0.9491% |
| 0.075 | −1.4048% | −1.4034% |
| 0.100 | −1.8468% | −1.8449% |

缩腔量相对**同压力、零张力基线**。最高张力下仍比无载参考态扩张约17.9%，
所以结论是主动张力部分抵消压力扩张，尚不是强收缩或实验幅度的心跳。
最高张力局部max|J−1|为0.3424%/0.3301%，全部状态通过原1%门。
73项独立汇总检查及原粗细面积门passed；两网格通过不等于应力热点收敛。

![结构、假设纤维、总与主动应力、局部J及缩腔响应](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/figures/FigS1S9_active_overview/FigS1S9_active_overview_v01_20260918/04_FigS1S9_active_overview_v01_20260918.png)

[五个真实张力态图与Notebook](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html) ·
[执行与证据边界](project_control/ventricle_fem_contour_active_execution_v01.md)

图件为真实1倍形变、统一应力色标，加载级不是心动时间。
本轮152测试+21子测试、图件交付passed；一次201.218秒，32个新Newton向量，0GPU/自动重跑。

## 主要难点与唯一下一步

目前主动缩腔较小，材料/压力/纤维/参考态尚未标定；二维平面应变限制仍在。
旧0.08高压局部体积失败完整保留，未重算、未放宽门限；不把本轮低压通过推广至高压。

唯一下一步建议：**进入理想化三维心室固体，建立几何/网格及可解释纤维方向，再检验低压与主动载荷**。
不继续无限扩展二维参数试算；三维离散需独立资格，暂不加血流或生长。待用户确认，不自动运行。

## 证据、存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不移动、不删除。
本包约334.3MiB，1518父/祖先文件及50项无关修改哈希保持；仓库低于3GiB。
阶段直接本地main提交，不自动推送。

- [高压被动失败](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)：0.08局部J偏差1.1737%，原failed保留。
- [原轮廓0/0.02两网格资格](../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/index.html)：原首压力passed，只读复用。
- [DG2圆环两网格完整被动资格](../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html)：通过并只读复用。
- [F6-S0圆环压力与主动基准](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：历史26态保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
