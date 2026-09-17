---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-17
---

# PRL｜斑马鱼心室 FEM

## 项目目标与当前模型

只用FEM解释斑马鱼心室跳动及发育，逐步研究组织结构、生长、ECM及心内膜反馈。
不恢复DCM；精细逐细胞分割不是组织尺度FEM的前置条件。

外轮廓来自72 hpf Fish 4、z=39；内腔和三层界面按20/27、21/27、22/27、1构造，
不是实测解剖。FEniCSx二维P2位移/P1压力三角形、三维平面应变有限变形NH，
各层mu=1、kappa=1000（未标定）。内壁随动压力，外壁自由；A固定ux/uy、B固定uy，
只去除刚体运动。主动为0，加载级不是生理时间。

## 当前进展：细网格仍未通过局部体积门

F6-S1-Q只补细网格14164单元的零载与p/mu=0.02两态；粗网格3541单元仅沿用旧数据。
两档同域几何通过，0次重剖分；一次40.770秒容器保存2态，零载通过、非零载局部J失败即停。

加密后max|J−1|从6.71167%升至11.15248%，但超限参考体积分数从0.48565%降至0.14100%。
腔面积变化20.10718%/20.12104%只差0.01387个百分点，仍不能替代原1%局部门。
两档非零载均为失败态诊断，不是已验证的心室响应；无后续加压或主动收缩。

![细网格结构应力与粗细局部J对照](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/figures/FigS1Q_fine_diagnostic/FigS1Q_fine_diagnostic_v01_20260917/04_FigS1Q_fine_diagnostic_v01_20260917.png)

[本地外部图件、两帧动图及Notebook](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html) ·
[执行与原因分析](project_control/ventricle_fem_fenicsx_fine_diagnostic_execution_v01.md)

## 核心难点

细网格求解器残量1.34e-14、独立自由力3.28e-14、弱压力残量3.83e-17均通过；
平均J−1约0.002858%，但局部峰值11.15%。热点靠近外边界、远离固定点；根因尚未确定。
均匀加密没有解决局部问题，下一步需分离边界拐角与体积约束离散影响，不直接调材料或放宽门限。

只有外轮廓实测；内腔/壁厚/纤维、无应力参考态、材料、生理时间与自由三维仍未标定。
圆环基准通过不能替代实测轮廓资格或实验验证。

## 唯一下一科学步骤（待确认）

制定边界拐角/局部体积约束离散的最小分离对照合同，先明确几何允许误差与离散选择，再批准新求解。
不盲目再加密、不继续加压、不加入主动，保持原失败证据与1%门。

## 存储与历史证据

后续新结果使用已批准的`E:\Temp-Projects\PRL-results`，不进入GitHub。
取消新结果的固定阶段体积限额，按预计输出量＋至少64 MiB停止空间＋10 GiB磁盘余量准入。
代码仓仍保持3 GiB硬限；旧results原位保留，未复制、搬移或删除。
两轮主机写入及一次Docker挂载I/O通过，0新科学求解，571个既有FEM文件哈希保持。
见[存储决定](project_control/external_result_store_decision_v01.md)及[验收](project_control/external_result_store_execution_v01.md)。

- [F6-S0理想圆环26态通过](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：仅压力+9.8974%、仅主动−4.3150%、组合+4.5566%，不代表斑马鱼实验拟合。
- [F6-S1-M薄层网格修复](results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html) · [原F6-S1网格失败](results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html) · [原F5局部J失败](results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html)
- [权威状态与历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)

375个父文件保持。73测试及21子测试通过不等于科学通过；单CPU、0 GPU/DCM/自动重跑；无安装或删除。
阶段本地提交main，不自动推送。真实心动、血流、生长与ECM反馈未运行。
