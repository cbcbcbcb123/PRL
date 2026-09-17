---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-17
---

# PRL｜斑马鱼心室 FEM

## 项目目标

只用FEM建立解释斑马鱼心室跳动及发育的力学模型，逐步研究组织结构、生长、ECM及心内膜反馈。不恢复DCM；精细逐细胞分割不是组织尺度FEM的前置条件。

## 当前模型与边界

外轮廓来自72 hpf Fish 4、z=39；内腔及三层界面按20/27、21/27、22/27、1构造，
不是实测内腔或壁厚。计划采用FEniCSx二维P2位移/P1压力三角形、三维平面应变有限变形
Neo-Hookean材料，各层mu=1、kappa=1000（未标定）。内壁随动压力p/mu=0→0.08，
外壁自由；A固定ux/uy，B固定uy，只消除刚体运动。加载级不是生理时间。

## 已完成：薄层网格修复通过

按局部层间距调整边界目标边长，保持源轮廓及20度质量门不变。
最小候选为1958顶点、3541三角形；最小角从12.8687°提高至23.0435°，
不合格单元由45降为0。三个预声明候选均通过几何检查，不再继续盲目加密。
mask IoU保持99.5882%，原始轮廓采样Hausdorff保持1.66974微米，共享层界完整。

![合格网格、质量对比与存储预算](results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/figures/FigS1M_mesh_repair/FigS1M_mesh_repair_v01_20260917/04_FigS1M_mesh_repair_v01_20260917.png)

[本次执行与裁决](project_control/ventricle_fem_fenicsx_thin_mesh_execution_v01.md) ·
[图件与可复算Notebook](results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html)

## 当前阻断：完整输出预算，而非网格或材料失败

最小候选的两档网格×五个压力状态，加上图件/控制余量，保守预测307.35 MiB，
超过本轮256 MiB准入上限。因此本次**0平衡求解，压力响应、形变与应力均not_run**。
预测不是实际文件体积或RAM占用；没有磁盘写满证据。原调用failed退出保持，
交付裁决为“网格passed、存储blocked”。260个父证据文件哈希保持。

## 最近通过的力学结果

F6-S0理想三层圆环的26个唯一被动/主动平衡态通过。细网格四终态的腔面积变化：
零载0%、仅压力+9.8974%、仅主动−4.3150%、组合+4.5566%。原1%局部J门及独立82项汇总门通过。
圆环不是实测心室，不能替代真实轮廓力学资格或斑马鱼实验验证。

[F6-S0结构与结果](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html) ·
[原F6-S1网格失败](results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html) ·
[原F5局部J失败](results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html)

## 唯一下一步（待确认）

复用已合格的candidate_0，不重做三候选。建议仅下一被动阶段特批384 MiB，
另留64 MiB停止保全空间，项目3 GiB硬上限不变。通过准入后执行原两档网格×五压力的十态矩阵，
材料、加载、时间上限和原质量/力学门不变；首个失败即停，不自动重跑，暂不加入主动收缩。

真实内腔/壁厚/纤维、参考应力、材料、生理时间、自由三维、血流、生长及ECM反馈仍未标定或not_run。
[权威状态与历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)

单CPU、固定已有镜像、禁网、0 GPU/DCM；无安装、删除或项目外新建。阶段本地提交main，不自动推送。
