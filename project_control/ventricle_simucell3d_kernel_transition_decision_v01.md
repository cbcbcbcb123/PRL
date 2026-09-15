---
document_id: PRL-VENTRICLE-SIMUCELL3D-KERNEL-TRANSITION-DECISION-V01
status: adopted
decided_at: 2026-09-12
applies_to: forward ventricle DCM-ECM implementation after Z1-TF2-A
supersedes_scientific_results: false
---

# 心室三层模型切换至 SimuCell3D 内核的决定 v01

## 用户决定

用户确认：由于 MeshCell3D 将重构并停止当前实现，前向心室 DCM-ECM 路线改用 PRL 中已经受控保存的 `external/simucell3d/` 内核继续。PRL 不复制第二套 SimuCell3D 内核，也不删除或改判任何 MeshCell3D 历史结果。

本决定只授权先完成 `Z1-TF2-M0` 换核资格门。它不把 MeshCell3D 上的 `PASS_Z1_TF2A_PRECHECK / surface_only_supported` 继承为 SimuCell3D 的通过，也不自动授权 `Z1-TF2-B` 静态成形、主动周期、物理时间、Z2、GPU、软件安装、提交、推送或外部发布。

## 内核与适配边界

1. 唯一 SimuCell3D 核心为 `external/simucell3d/`，其上游基线、BSD-3 许可证和 PRL 受控修改谱系继续保留。
2. 新的心室适配层仅保存于 PRL 主项目；不得把一套复制内核放进 `scripts/`、`results/` 或其他目录。
3. 生物对象身份与运动学状态必须分离：`myocardium`、`endocardium`、`ecm` 是对象角色；`deformable`、`fixed`、`prescribed` 是独立约束。不得继续用“ECM 类型”隐式等价“静止”。
4. 首轮固定拓扑；只有固定拓扑换核门通过后，才可在新合同下重新启用 remeshing。
5. 心肌与心内膜的逐边参考态膜能保持关闭。ECM 材料参考态是否需要引入，仍须由独立材料门决定。

## 结论状态

本决定建立迁移路线，不构成模型、数值或科学 PASS。当前 SimuCell3D 心室三层实现状态在 `Z1-TF2-M0` 完成前为 `unknown`。

