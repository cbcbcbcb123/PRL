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
F6-S1-S6完成原两级圆环的`p/mu=0/0.02/0.04/0.06/0.08`被动资格；主动关闭，物理及原门限保持。

**两网格被动资格passed**：5个粗网格态全部复用，5个细网格态本轮新增。
最高压力时，细网格腔室面积+22.4602%，壁局部max|J−1|=0.0121924%，低于原1%门。
相对不可压解析面积响应误差最大0.0722750%，通过原M1的1%门；
粗细面积响应差0.000865913个百分点，相对差0.00385533%，通过原粗细门。
两级资格不等于多级渐近收敛、应力热点收敛或实验吻合。
5个细网格真实压力态均以统一应力色标和1倍实际形变出图；它们是载荷延拓，不是5个心动时刻。
腔室面积增加不等于壁组织体积增加，位移模长也不等于应变。

![实际三层结构、1倍峰值位移、两网格解析响应与原局部体积门](../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/figures/FigS1S6_qualification/FigS1S6_qualification_v01_20260918/04_FigS1S6_qualification_v01_20260918.png)

[结构/5个细网格压力态应力图与Notebook](../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html) ·
[执行记录、故障定位与修复边界](project_control/ventricle_fem_fine_ring_recovery_execution_v01.md)

## 核心难点与唯一下一步

上轮原生段错误已定位并修复：SNES零次更新收敛后，不应读取尚未执行的MUMPS因子统计。
同环境负例和修复后零载/非零载/已收敛解检查均有原始证据；修复只改诊断，不改力学。
剩余主要缺口是非圆形轮廓：旧CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；DG2轮廓尚未运行。

唯一下一步待确认：回原图像外轮廓（内腔与层界仍为构造），仅做粗/细网格零载及首个p/mu=0.02，共最多4态。
不重算圆环、不改物理或原1%门，单CPU/0GPU/首失败停止；通过后再裁决其余压力及主动收缩。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
本包约105.1MiB；980个父/祖先文件和50项无关修改保持；76测试+21子测试、69项独立数值检查通过。
接口负例6.407秒，修复后接口及科学调用51.511秒；0 GPU/粗网格重算/安装/拉取/删除/自动重跑。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
