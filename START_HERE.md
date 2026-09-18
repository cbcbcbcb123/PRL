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
F6-S1-S只诊断F6-S1-R圆环`p/mu=0.02`失败初值的P2/DG2切线，不改变几何、材料、加载或1%局部体积门。

唯一一次16.327秒单CPU容器完成1次矩阵组装以及各1次MUMPS/SuperLU尝试，但在写报告时，
MUMPS报告中的非有限值`inf`被严格JSON拒绝。原执行与诊断交付均failed；没有自动重跑、非线性平衡求解或新状态。
独立事后复核passed：9,216阶矩阵有限、无零行/列、满结构秩，896个单元压力块均满秩。
`uu/pp`块范数比约3.14e7，至少2,688个高阶压力模态只受很小的压力块约束，支持尺度/小主元风险；
但KSP、PC、MUMPS INFOG和SuperLU结论未保留，所以求解器根因仍为not_evaluable。

![P2/DG2混合切线结构、尺度和证据边界](../PRL-results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918/figures/FigS1S_linear_system_diagnosis_v02_20260918.png)

[矩阵证据与结果页](../PRL-results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918/index.html) ·
[执行记录](project_control/ventricle_fem_mixed_linear_diagnosis_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；本轮没有运行轮廓。
当前已经排除结构零行、结构秩亏和单元压力质量块奇异，但没有恢复MUMPS实际错误码，不能把尺度假设写成已确认根因。

唯一下一步待确认：用已修复的非有限值序列化，仅重放同一个保留初值的矩阵诊断一次，
获取KSP/PC/MUMPS/SuperLU明细；仍不求平衡、不更新状态、不改材料或门限。之后才裁决块缩放或局部静态消元。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
375个父文件和76个F6-S1-R源结果文件哈希保持；51项测试和21项子测试通过；0 GPU/安装/拉取/删除。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
