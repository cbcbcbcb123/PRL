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
F6-S1-S4尝试从原零载续算圆环`p/mu=0.02`，物理及1%局部体积门保持。

本轮failed：Codex新增的监测代码对PETSc只读锁定向量请求可写访问，首次Newton更新前退出。
一次16.914秒单CPU容器；接受受压态0个，初值与末次尝试逐字节相同，独立自由力残量0.00866704。
这不是新的材料/网格失败证据；初值J=1不能当成体积精度改善。
只读记录和MUMPS选项生命周期补丁已写入，60测试+21子测试通过，原容器复验not_run。
此前F6-S1-S3保存切线的MUMPS余量100验证仍passed，但不能替代本次非线性验收。

![实际圆环结构与加载初值的未平衡力](../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v01_20260918/figures/FigS1S4_monitor_failure/FigS1S4_monitor_failure_v01_20260918/04_FigS1S4_monitor_failure_v01_20260918.png)

[结构/失败诊断图与Notebook](../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v01_20260918/index.html) ·
[执行记录与修复边界](project_control/ventricle_fem_ring_resume_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed；本轮没有运行轮廓。
当前直接阻断是新增监测接口；配置测试不足以覆盖真实PETSc只读锁和选项生命周期。

唯一下一步待确认：在同一固定环境先做只读向量/因子选项的微型接口烟测，通过后才从保留零载
续算同一首个`p/mu=0.02`被动态。不重跑零载、不改物理或1%门，一次有界调用、首失败保全。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
本包约11.0MiB；619个父/祖先文件和50项无关工作区改动保持；0 GPU/安装/拉取/删除/自动重跑。
阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
