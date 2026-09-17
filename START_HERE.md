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

## 当前进展：已计算变形，局部体积门失败

800 MiB阶段预算已生效。复用合格粗网格3541单元，细网格四分为14164单元；
两档几何通过，最小角23.0435度、源mask IoU99.5882%、轮廓误差1.66974微米保持。

一次25.932秒容器保存两个平衡态：零载passed；p/mu=0.02收敛，但最大局部
|J−1|=6.71167%超过1%门，因此停止。后续8态及细网格力学未运行。
腔面积增加20.10718%及明显变形仅为失败态诊断，不能作为已验证响应。

![结构、形变应力、局部J及两态面积](results/ventricle_fem/f6s1p_retained_passive_v01_20260917/figures/FigS1P_passive_failure/FigS1P_passive_failure_v01_20260917/04_FigS1P_passive_failure_v01_20260917.png)

[图件、两帧动图及Notebook](results/ventricle_fem/f6s1p_retained_passive_v01_20260917/index.html) ·
[执行与原因分析](project_control/ventricle_fem_fenicsx_retained_passive_execution_v01.md)

## 核心难点

求解器残量6.81e-15、独立自由力1.69e-14、弱压力残量3.22e-17均通过；
平均J−1仅0.002858%，但69个单元含超1%的积分点，局部约束仍未满足。
这支持优先检验空间离散影响，而不是直接调软材料、提高体积模量或放宽门限。

只有外轮廓实测；内腔/壁厚/纤维、无应力参考态、材料、生理时间与自由三维仍未标定。
圆环基准通过不能替代实测轮廓资格或实验验证。

## 唯一下一科学步骤（待确认）

只计算尚未运行的细网格p/mu=0及0.02两个状态，与本次保全粗网格对照，
检验局部J误差是否随加密降低。保持材料、载荷和1%门，不重跑粗网格，不继续加压或加入主动。

## 存储与历史证据

新阶段默认800 MiB，另64 MiB停止空间，项目3 GiB硬限保持。用户建议外置PRL-results：
精确项目外路径待确认，尚未搬移或外部新建。现有results已被Git忽略，不随普通提交同步。

- [F6-S0理想圆环26态通过](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)：仅压力+9.8974%、仅主动−4.3150%、组合+4.5566%，不代表斑马鱼实验拟合。
- [F6-S1-M薄层网格修复](results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html) · [原F6-S1网格失败](results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html) · [原F5局部J失败](results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html)
- [权威状态与历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)

308个父文件保持。单CPU、0 GPU/DCM/自动重跑，固定已有镜像、禁网；无安装或删除。
阶段本地提交main，不自动推送。真实心动、血流、生长与ECM反馈未运行。
