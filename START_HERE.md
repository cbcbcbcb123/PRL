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
F6-S1-S3只检查圆环`p/mu=0.02`保存切线上的MUMPS工作空间设置，物理及1%局部体积门保持。

只将额外工作空间`ICNTL(14): 20 → 100`后，MUMPS错误码从-9变为0，线性修复验证passed。
独立相对残量7.48e-11（门1e-8）；与保留SuperLU解的相对差1.45e-8（门1e-6）。
一次8.380秒单CPU容器，1次MUMPS尝试；0重组装、0新SuperLU因子化、0非线性平衡或状态更新。
矩阵、右端及初值保持，14个其他已记录控制项相同。原DG2受压平衡仍failed，不能用线性通过替代。

![实际圆环结构与工作空间修复后的线性残量](../PRL-results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918/figures/FigS1S3_workspace_check/FigS1S3_workspace_check_v01_20260918/04_FigS1S3_workspace_check_v01_20260918.png)

[结构/残量图与可复算Notebook](../PRL-results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918/index.html) ·
[执行记录](project_control/ventricle_fem_mumps_workspace_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；本轮没有运行轮廓。
已消除保存切线的工作空间故障，但后续Newton切线、非线性平衡及局部体积精度尚未验证。
原矩阵条件数约1e9仍是精度风险，不能从一次小残量推断全部后续状态稳定。

唯一下一步待确认：将已验证的余量100接回原圆环P2/DG2求解器，从保留零载态继续首个`p/mu=0.02`被动态，
不重跑零载、不改物理或1%门。一次有界非线性调用、首失败保全，检查平衡/积分点J/独立力平衡。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
375个父文件和176个来源文件哈希保持；56项测试和21项子测试通过；0 GPU/安装/拉取/删除。
首次镜像检查超时发生在容器创建前，只读确认运行时恢复响应后才开始首次求解；没有Docker重启或计算重跑。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
