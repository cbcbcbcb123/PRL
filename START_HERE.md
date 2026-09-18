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

当前仍是二维P2三角形、三维平面应变有限变形NH固体，不是已完成的三维/FSI。
mu=1、kappa=1000未标定；内壁随动压力、外壁自由，A固定ux/uy、B固定uy去除刚体运动。
F6-S1-S5完成粗圆环`p/mu=0/0.02/0.04/0.06/0.08`；主动收缩关闭，物理及1%局部体积门保持。

粗网格完整5态 **passed**（2态复用、3态新增）：最高压力时腔室面积+22.4593%，
壁局部max|J−1|=0.0134833%，独立自由力残量约1.64e-13。
相对不可压解析面积响应误差最大0.0684168%，通过原M0的2%门。
随后细网格零载出现PETSc原生段错误，**细网格执行failed，粗细比较not_run**；本轮整体不算通过。
5个真实压力态均以统一应力色标和1倍实际形变出图；它们是载荷延拓，不是5个心动时刻。
腔室面积增加不等于壁组织体积增加，位移模长也不等于应变。

![实际三层结构、1倍峰值位移、解析响应与原局部体积门](../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/figures/FigS1S5_qualification/FigS1S5_qualification_v01_20260918/04_FigS1S5_qualification_v01_20260918.png)

[结构/5个压力态应力网格图与Notebook](../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/index.html) ·
[执行记录、失败事实及科学边界](project_control/ventricle_fem_ring_passive_qualification_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；本轮没有运行轮廓。
当前阻断是细圆环零载SIGSEGV 11：只保存初猜/monitor-0，没有最终收敛报告或末态。
优先排查零次Newton时的因子诊断接口，但缺少原生调用栈，崩溃位置与根因尚未确认；本轮没有修复或重跑。

唯一下一步待确认：同环境微型接口定位与最小修复，通过后仅续做细圆环零载及4个压力态；
不重算粗网格、不改物理或1%/解析/粗细门、首失败保全。通过后再回原轮廓，再考虑主动收缩。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
本包约54.9MiB；826个父/祖先文件和50项无关工作区改动保持；68测试+21子测试通过。
一次23.705秒单CPU容器；0 GPU/粗网格已接受态重算/安装/拉取/删除/自动重跑。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
