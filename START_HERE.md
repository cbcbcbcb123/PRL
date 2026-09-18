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
本轮仅将连续线性压力CG1换为逐单元二次压力DG2，保留原几何、材料、加载和1%局部体积门。

F6-S1-R一次17.002秒单CPU调用：896单元圆环零载通过；p/mu=0.02在首个线性求解失败，
SNES=-3，Newton更新0次，残量0.008667。保存2态，只接受1态；原轮廓新求解not_run。
失败初值J=1不代表体积误差修复，也不能据此认定体积锁死。没有自动重跑。

![圆环结构、旧CG1对照和DG2失败诊断](../PRL-results/ventricle_fem/f6s1r_pressure_space_v01_20260918/figures/FigS1R_pressure_failure/FigS1R_pressure_failure_v01_20260918/04_FigS1R_pressure_failure_v01_20260918.png)

[可复算图件与Notebook](../PRL-results/ventricle_fem/f6s1r_pressure_space_v01_20260918/index.html) ·
[执行记录](project_control/ventricle_fem_pressure_space_execution_v01.md)

## 核心难点与唯一下一步

旧轮廓CG1粗/细网格max|J−1|为6.71%/11.15%，原1%门仍failed。
只读投影显示，其体积偏差平方L2范数约99.92%/99.75%位于CG1压力空间不能直接约束的分量；
这不是超限组织体积分数，也不能单凭此排除边界几何影响。

下一步先诊断DG2混合线性系统：获取KSP/MUMPS详细原因、检查切线矩阵、固定自由度和压力块。
本次失败授权已经用完；新求解须明确确认，不改材料或门限，不继续加压或加入主动。
三维/FSI/生长仍not_run；数值测试通过不等于生物学验证。

## 存储与历史

新结果在已批准的 `E:\Temp-Projects\PRL-results`，不进GitHub；旧证据不搬移、不删除。
按预计输出＋至少64MiB停止空间＋10GiB磁盘余量准入；代码仓3GiB硬限保持。
455父文件哈希保持；0 GPU/安装/拉取/删除。阶段直接本地提交main，不自动推送。

- [F6-S0理想圆环26态](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：已通过的旧CG1基准保留。
- [F6-S1-Q粗细网格局部J失败](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)：只有外轮廓来自72hpf Fish4，内腔及三层界面仍为构造。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
