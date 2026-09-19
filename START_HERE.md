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

**现在先给该混合离散做单位立方体基准。v03正J候选保护通过原生/独立核验，但整体资格仍failed。**

- 立方体X=0为解析位移，其他五面为解析牵引，制造解有配套体力；不是心室腔压或收缩。
- 一次容器72.04秒：6次求解尝试、5个有效平衡态、1例保护耗尽、2例未运行；无重跑。
- κ=100细化误差下降，但n=8的位移L2误差4.3239%>2%，H1误差43.6485%>15%，J误差RMS 0.15618%>0.1%。
- κ=1000、n=2不再接受负J，但14个接受步后min J降到1.62e−7；下一步减半20次仍不安全，保护停止。
- 同n=8网格，精确位移P2插值的H1误差2.38%，平衡解43.65%；表示能力不是唯一问题，根因仍需分离。
- 旧接口故障未复现，31条接受路径独立核验通过；安全实现passed不等于平衡或场精度passed。

![实际基准结构与误差、安全诊断](../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/diagnostic.png)

[八工况表与原始状态](../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/index.html) ·
[执行裁决及下一步](project_control/ventricle_mixed_cube_benchmark_v03.md)

## 主要问题与唯一下一步

问题已分成两层：粗网格受保护的Newton路径仍逼近退化，无法收敛；κ=100平衡精度不因保护而改变。
当前证据不能断言锁死/inf-sup失稳，也不能归咎于心室复杂形状；简单基准本身尚未合格。

**唯一下一步：分离制造载荷积分与混合压力约束的误差放大，先利用保存态鉴别，再决定必要的新对照。**
保持材料与原门，不自动换单元、降载或扩大矩阵；不跳到薄层、原心室主动、生长或FSI。
v03一次容器权限已消耗；不增加减半次数，剩余两例不能凭旧授权再开容器。下一次运行仍需确认。

## 证据与存储

5个终态、37个监测状态及31个接受步的候选路径独立复算通过；54项宿主测试通过，原科学失败保留。
结果在已批准PRL-results，不进GitHub；434保护文件与50项旧改动未变，原v01/v02包完整保留。
代码仓3GiB和磁盘余量保护保持；本地main阶段提交，不自动推送。0GPU、无删除、安装或Docker修复。
统一风格160dpi探索图，非投稿终稿；算法迭代不是生理时间。本轮未追加全局记忆。

- [原v01接口失败](project_control/ventricle_mixed_cube_benchmark_execution_v01.md)：完整保留，不重写旧现场。
- [心室保存态投影诊断](../PRL-results/ventricle_fem/volume_projection_audit_v01_20260918/index.html)：r的RMS下降27.3%，最大偏差仍超门。
- [专家原件](plan/active/EXP-20260918-FEM-review-v01/README.md)：身份unknown，采纳与执行权限分开。
- [二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：缩腔约1.85%，不是三维或实验心跳。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
