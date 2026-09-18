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
F6-S1-S2仅重放圆环`p/mu=0.02`失败初值的P2/DG2切线诊断，物理设置及1%局部体积门保持。

一次15.351秒单CPU容器完成报告重放，诊断交付passed；原DG2受压平衡仍failed。
MUMPS实际返回`INFOG(1)=-9`：内部数值工作数组过小，`ICNTL(14)=20`，不是`-10`奇异/零主元错误。
同一矩阵的SuperLU解独立相对残量为3.17e-13；矩阵估计条件数约1.09e9，尺度风险仍需关注。
11组矩阵/右端/映射数组与上轮相同，5组前后状态逐字节相同。0非线性平衡求解、0新状态、0自动重跑。

![实际圆环结构与同矩阵MUMPS/SuperLU诊断](../PRL-results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918/figures/FigS1S2_report_replay_v02_20260918.png)

[诊断证据与结果页](../PRL-results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918/index.html) ·
[执行记录](project_control/ventricle_fem_mixed_linear_replay_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；本轮没有运行轮廓。
直接故障已定位为MUMPS内部工作空间不足；容器未OOM退出，不能解释为容器8 GiB总内存耗尽。
前轮的尺度/近奇异假设未被证实为直接根因；小线性残量也不能代替非线性或体积资格。

唯一下一步待确认：只把MUMPS工作空间额外余量`ICNTL(14): 20 → 100`，在同一保存CSR上尝试一次，
要求错误码为0、解有限、相对残量≤1e-8并交叉核验；不更新FEM状态。通过后再恢复圆环非线性被动资格。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
375个父文件和120个F6-S1-R/S源结果文件哈希保持；53项测试和21项子测试通过；0 GPU/安装/拉取/删除。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
