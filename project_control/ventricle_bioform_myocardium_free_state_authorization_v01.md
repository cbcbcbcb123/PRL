---
document_id: PRL-VENTRICLE-BIOFORM-MYOCARDIUM-FREE-STATE-AUTHORIZATION-V01
status: authorized
authorized_at: 2026-09-13
stage: Z1-BIOFORM-MYO-A
source: user_message
---

# Z1-BIOFORM-MYO-A 执行授权 v01

用户在确认“先建立细胞类型特异内在力学稳态；心肌先行；不使用目标表面参考形状”的方案后明确回复：“同意，开始。我们先把心肌做出来，然后依次继续”。

该指令授权：

- 在 PRL 项目内创建心肌自由态子阶段的决定、冻结合同、应用层代码、测试和 create-only 结果；
- 复用并在必要时以最小、可回归方式扩展项目内唯一 `external/simucell3d/`；
- 使用 CPU 完成有界三幅值预检和一次冻结正式矩阵；
- 输出实际模型结构图、多状态结果图、力学场图和独立验证；
- 按真实结果更新 `START_HERE.md`、`project_control/CURRENT_STATUS.md` 与项目驾驶舱。

不授权心内膜子门、ECM 锚定心肌、三层重跑、周期主动力学、GPU、安装依赖、删除、提交、推送或外部发布。正式矩阵一经启动即消耗本授权，不得自动创建 v02 重试。
