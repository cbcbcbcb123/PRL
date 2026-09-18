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
mu=1、kappa=1000未标定；内壁随动压力、外壁自由，A固定ux/uy、B固定uy；主动关闭。

**F6-S1-S8完整被动资格failed，受控停止与交付passed。**
复用两网格零载/0.02，只新增以下粗网格状态；没有重算旧状态。

| p/mu | 腔面积变化 | 局部max\|J−1\| | 原1%门 |
|---|---:|---:|---|
| 0.04 | +32.8079% | 0.5874% | passed |
| 0.06 | +48.0560% | 0.9201% | passed |
| 0.08 | +68.2662% | 1.1737% | failed |

0.08力平衡与DG2局部约束通过，但1个单元的2个积分点超限，因此立即停止；
细网格后续0.04/0.06/0.08没有运行，不能宣称这些压力的粗细资格通过。
热点在构造心肌域、靠近外轮廓凹口，不在固定点邻域；几何效应与网格依赖尚未区分。
平均J约1.000152不能替代局部门；腔面积变化不等于壁体积变化。

![实际结构、失败态应力与局部J及载荷响应](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/figures/FigS1S8_passive_overview/FigS1S8_passive_overview_v01_20260918/04_FigS1S8_passive_overview_v01_20260918.png)

[五个真实压力态图与Notebook](../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html) ·
[完整执行、诊断与边界](project_control/ventricle_fem_contour_passive_execution_v01.md)

图件为真实1倍形变、统一应力色标，加载级不是心动时间；0.08始终标为failed。
本轮132测试+21子测试、交付验收通过；一次57.462秒，17新Newton向量，0GPU/自动重跑。

## 主要难点与唯一下一步

当前两网格都通过的压力基线是0.02；高压局部问题和材料/生理标定尚未解决。
建议保留0.08失败并暂停追高压，**在已通过的0.02基线上加入心肌主动张力递增对照**，
研究主动缩腔如何抵消压力扩张；原材料/1%门、单CPU/0GPU、首失败停止均保持。

这会将“完整高压序列先于主动”调整为“已通过载荷范围内研究主动”，**待用户明确确认**。
本轮未执行主动、三维、FSI、生长或生物学验证，不自动继续新科学阶段。

## 证据、存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不移动、不删除。
本包约110MiB，1358父/祖先文件及50项无关修改哈希保持；仓库低于3GiB。
有限差分派生误差的跨平台舍入比较已单独修复，未改任何物理门或科学failed。
阶段直接本地main提交，不自动推送。

- [原轮廓0/0.02两网格资格](../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/index.html)：原首压力passed，不被高压失败改写。
- [DG2圆环两网格完整被动资格](../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html)：通过并只读复用。
- [F6-S0圆环压力与主动基准](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：历史26态保留。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
