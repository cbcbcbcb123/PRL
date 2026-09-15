---
document_id: PRL-VENTRICLE-Z1C-EXECUTION-AUTHORIZATION-V01
status: consumed_by_execution
authorized_at: 2026-09-11
scope: z1c_controlled_double_cell_contact_and_mesh_mechanical_fields
---

# Z1-C 执行授权记录 v01

用户在确认下一步为 Z1-C 受控双细胞接触后回复：“同意，最好在网格上标记出曲率，应力，压力等力学量”。

本记录将该决定解释为授权按 `ventricle_z1c_controlled_contact_contract_v01.md` 执行 Z1-C，并增加真实网格上的曲率、膜面力合量、压力和接触牵引可视化。授权不扩展到 Z1 多细胞桥接、Z2、GPU、安装、提交、推送、外部发布或删除。

由于当前模型没有冻结膜厚，网格“应力”必须报告为膜面力合量/等效膜张力 `N/m`，不得换算成未经定义的三维 Cauchy 应力 `Pa`。若现有 MeshCell3D 接触内核必须修改，本授权不足以自动实施该跨仓修复，须先交付阻断证据。

