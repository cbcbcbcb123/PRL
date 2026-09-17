---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-17
---

# PRL｜斑马鱼心室 FEM

## 项目目标

只用FEM建立解释斑马鱼心室跳动及发育的力学模型，逐步研究组织结构、生长、ECM及心内膜反馈。不恢复DCM；精细逐细胞分割不是组织尺度FEM的前置条件。

## 当前模型与边界

F6-S0采用开源FEniCSx，先验证理想三层圆环。二维P2位移/P1混合压力三角形，
本构为三维平面应变有限变形。896/3584单元两档网格；内外半径20/27与1，
层界21/27与22/27。三层目前只作区域标签，均采用未标定Neo-Hookean材料mu=1、kappa=1000。

内壁随动压力p/mu=0→0.08，外壁自由；(1,0)固定ux/uy、(-1,0)固定uy只去除刚体运动。
主动应力仅施于心肌层、沿参考环向纤维，Ta/mu=0→0.10；四终态比较采用p/mu=0或0.04。
理想圆环不是实测心室，加载级不是生理时间。

[当前合同与公式](project_control/ventricle_fem_fenicsx_ring_active_contract_v01.md) ·
[完成裁决](project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md)

![三层区域、主动纤维、压力及两档网格](results/ventricle_fem/f6s0_active_completion_v01_20260917/figures/model_structure.png)

## 已完成与核心结果

G0运行时、G1被动与G2主动资格均 **passed**。保留10个被动态、16个主动/组合态，共26个唯一平衡态。

- 细网格同一四组对照：零载0%；仅压力+9.8974%；仅主动−4.3150%；压力＋主动+4.5566%。
- 主动张力使同一压力下的腔面积响应降低5.3408个百分点；组合工况相对零载仍为扩张。
- 细网格纯主动与组合末态最大局部体积偏差分别0.007705%和0.005376%，原1%门通过。
- 两网格主动末态腔响应差1.62e-7，组合1.51e-7；独立82项汇总门与主动虚功复核通过。
- 首次调用保存10个被动态后遇到字段读取错误；修复后只补尚未运行的16态，0重复平衡求解。原失败保留，两次科学容器累计69秒。

![四组真实终态与统一应力色标](results/ventricle_fem/f6s0_active_completion_v01_20260917/figures/four_conditions.png)

## 当前主要难点

开源后端的理想被动与主动基准已通过；真实外轮廓仍待新后端资格。原F5图像外轮廓
max|J−1|=54.09%的失败保持，不用圆环结果替代。真实内腔/壁厚/纤维、残余应力、材料、
生理时间和自由三维运动仍未标定。

## 唯一下一步

F6-S1：用同一FEniCSx后端接回已保全的72 hpf Fish 4真实外轮廓，明确内腔/层界仍为构造几何；
先通过被动压力和1%局部J门，再加入主动收缩。无需重复圆环资格矩阵。F6-S1尚未运行。

主动心跳、生理周期、实测材料、真实自由三维心室、血流、生长与ECM反馈均not_run。

## 证据入口

- [F6-S0结构、定量图与动图](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html) · [完整独立复核](results/ventricle_fem/f6s0_active_completion_v01_20260917/post_verification.json)
- [被动父证据及原读取失败](results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917/index.html)
- [保留的F5真实外轮廓失败](results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html) · [F4圆柱父资格](results/ventricle_fem/f4_curved_pressure_v01_20260917/index.html)
- [权威状态与历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)

单CPU、0 GPU/DCM/科学重跑；固定本地镜像、禁网、不拉取。原失败包与Docker隔离目录保留；无删除、安装、提交或推送。
