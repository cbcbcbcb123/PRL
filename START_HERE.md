---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-19
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流相互作用，不恢复DCM。
先理想化三维及公开资料，后续替换自有实验；当前几何尚未用morphoHeart标定。
路线：三维固体 → 规定式三维生长 → 双向FSI → 力学生长/ECM反馈。
[路线决定](project_control/ventricle_3d_before_growth_decision_v01.md)不自动授权全部后续计算。

## 当前模型与已完成结果

主研究模型是三域半椭球心室：心内膜/ECM/心肌，有限变形NH、P2位移/P1压力四面体。
基底环全固定、外壁自由、内腔随动压力；μ=1、κ=1000未标定，三维主动尚未运行。
原心室局部体积最大偏差1.4496%仍超过1%门，不能作为合格的生物心动模型。

**现在先给该混合离散做单位立方体基准。v02已执行：两个非零patch通过，但整体资格failed。**

- 立方体X=0为解析位移，其他五面为解析牵引，制造解有配套体力；不是心室腔压或收缩。
- 一次容器64.03秒：6次求解尝试、5个有效平衡态、1个安全失败、2例未运行；无重跑。
- κ=100细化误差下降，但n=8的位移L2误差4.3239%>2%，H1误差43.6485%>15%，J误差RMS 0.15618%>0.1%。
- κ=1000、n=2在Newton第1步检出负J=−0.17637；生产积分点仍全正，额外采样使失效显现并停止计算。
- 旧表达式接口故障未复现；基础非零patch、独立装配/载荷/切线检查通过，不等于场精度已通过。

![实际基准结构与误差、安全诊断](../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/diagnostic.png)

[八工况表与原始状态](../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/index.html) ·
[执行裁决及下一步](project_control/ventricle_mixed_cube_benchmark_v02.md)

## 主要问题与唯一下一步

问题已具体到两层：粗网格的试探步可能产生负Jacobian；即使平衡残差很小，位移和局部体积精度仍可不足。
当前证据不能断言锁死/inf-sup失稳，也不能归咎于心室复杂形状；简单基准本身尚未合格。

**唯一下一步：制定并确认“试探步接受前正J保护＋同基准精度复验”的有界修订批次。**
保持材料与原门，不自动换单元、降载或扩大矩阵；不跳到薄层、原心室主动、生长或FSI。
v02一次容器权限已消耗；剩余两例不能凭旧授权再开容器。下一次运行仍需确认。

## 证据与存储

5个终态及24个监测状态独立复算通过；49项宿主测试通过，安全失败和精度失败仍保留。
结果在已批准PRL-results，145文件16,593,908 bytes，不进GitHub；289保护文件与50项旧改动未变。
代码仓3GiB和磁盘余量保护保持；本地main阶段提交，不自动推送。0GPU、无删除、安装或Docker修复。
统一风格160dpi探索图，非投稿终稿；算法迭代不是生理时间。用户要求的故障教训已保存为Codex记忆更新。

- [原v01接口失败](project_control/ventricle_mixed_cube_benchmark_execution_v01.md)：完整保留，不重写旧现场。
- [心室保存态投影诊断](../PRL-results/ventricle_fem/volume_projection_audit_v01_20260918/index.html)：r的RMS下降27.3%，最大偏差仍超门。
- [专家原件](plan/active/EXP-20260918-FEM-review-v01/README.md)：身份unknown，采纳与执行权限分开。
- [二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：缩腔约1.85%，不是三维或实验心跳。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
