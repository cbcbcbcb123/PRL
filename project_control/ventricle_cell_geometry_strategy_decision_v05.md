---
document_id: PRL-VENTRICLE-CELL-GEOMETRY-STRATEGY-DECISION-V05
status: adopted
decided_at: 2026-09-12
supersedes: project_control/ventricle_cell_geometry_strategy_decision_v04.md
applies_to: forward ventricle cell-shape, ECM representation, and tissue-formation work
supersedes_scientific_results: false
---

# 心室模型细胞几何、连续组织与 DCM-ECM 策略决定 v05

## 用户决定

用户确认沿用“不以逐边参考态膜能维持细胞外形”的前向路线，并进一步决定：ECM 也采用 DCM 表示，参照 Runser、Vetter 与 Iber 的 SimuCell3D 做法，以闭合三角曲面实体参与变形、接触和力传递。新的三层对象为心肌 DCM、ECM DCM 和心内膜 DCM；不得继续把稀疏 `5×5` 弹簧—弯曲平面作为前向 ECM 主体。

该决定只改变前向模型定义和后续执行优先级，不改写或删除既有 Z1-B、父 Z1、Z1-C、Z1-TF 结果。`results/ventricle_z1/tissue_formation_pilot_v04_20260912` 继续作为旧稀疏 ECM 网络路线的 `UNKNOWN` 证据包。

## “ECM 使用 DCM”的精确定义

1. **共同离散表示**：心肌细胞、心内膜细胞和 ECM 均由可变形三角曲面表示，并通过同一几何、接触、积分和输出框架推进。
2. **不同物理身份**：ECM 不是伪装成细胞的生物对象。ECM 类型关闭生长、分裂、细胞周期和细胞质生物学，具有独立材料参数、面类型和输出身份。
3. **首个有限片几何**：ECM 使用一个连续、闭合的薄层 DCM 实体，显式区分心肌侧面、心内膜侧面和有限片边缘；不以互不连通的 ECM 小球或无厚度渲染平面替代。
4. **界面传力**：同层细胞—细胞及细胞—ECM 主路径使用实际表面的黏附—排斥接触；稀疏锚定弹簧不再是生产主路径。完全节点绑定只作为预注册的无滑移极限对照，不能与有限黏附混称同一模型。
5. **层间隔离**：心肌与心内膜之间的直接接触关闭，所有层间力必须经过 ECM DCM；每项界面作用均记录作用—反作用、接触面积、间隙和功。

## 细胞参考态与 ECM 材料参考态不是同一概念

- 心肌和心内膜继续要求 `reference_shape_modulus=0`，不捕获逐边初始长度来规定长轴或扁平外形；保留目标体积、目标总面积、皮质张力和弯曲。
- ECM 首先验证与 SimuCell3D 表示相符的 `surface-only` 分支：闭合体积/面积、表面张力、弯曲和接触，不使用逐边参考度量。
- 若 `surface-only` ECM 在独立剪切试验中没有可分辨的切向支撑，不能通过提高任意表面参数伪装成固体 ECM。届时允许在 **ECM 对象内部**采用材料参考度量或黏弹内变量；它表示基质的弹性/黏弹参考构型，不得传递给细胞，也不得称为细胞形状参考能。
- ECM 的 `surface-only` 与 `solid/viscoelastic` 分支必须先在独立材料门中裁决，不能直接用最终细胞外形反向选择。

## 连续组织初始化

- 不再以中心距大于直径的独立球阵列作为心内膜组织起点。
- 首选由共同区域的三维 Voronoi/受限铺砌生成闭合细胞，或由显微分割导入；合成首轮采用可复算的规则受限铺砌。
- 初始同层相邻表面须已接触或处于接触截断范围内，并报告接触面积分数、邻居数和顶端—基底连续性；不得只靠跨空隙的弹簧把细胞称为连续组织。
- 心内膜扁平由致密铺砌、细胞—细胞黏附、ECM 支撑和腔面压力共同产生。
- 心肌长轴除致密铺砌外还需要冻结的纤维方向和各向异性胞内承载；SimuCell3D 的上皮表面张力—黏附机制不自动等价于心肌肌原纤维。

## 对 v03 外部合同包的适用范围修订

`plan/active/PRL_Codex_Stage_Contracts_v03` 原文和哈希保持不变。其“薄层 ECM 网络”条款在新的前向心室路线中由本决定取代；Z3、Z4 及依赖它们的后续阶段不得按旧网络定义直接执行，须先形成 DCM-ECM 修订合同。其余一次一阶段、唯一 `muse_dcm` 内核、证据分层、安全和停止规则继续有效。

## 当前代码事实与权限边界

只读审计确认 `E:\MeshCell3D\code\muse_dcm\engine\config.py` 已存在 `create_default_ecm_cell()`、独立 `type_id` 和按类型声明的接触策略；这只说明存在基本配置入口。当前没有找到把连续薄层 ECM DCM 作为三层组织主体的正式运行或材料验收证据，因此实现状态为 `unknown`，不能标记为已完成。

本决定授权更新 PRL 内的决定、合同与驾驶舱，不授权修改 `E:\MeshCell3D`、启动 GPU、执行长时模拟、删除旧包、进入主动周期或 Z2。若预检证明必须修改唯一内核，应列出最小改动和受影响回归后另行取得用户确认。

## 下一子门

下一子门为 `Z1-TF2-A｜DCM-ECM 原语与连续三层几何预检`，合同见 `project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_contract_v01.md`。它先验证 ECM DCM 本身及其界面，再决定是否进入致密三层静态成形；当前计算状态为 `not_run`。

## 文献依据边界

- Runser S, Vetter R, Iber D. *SimuCell3D: three-dimensional simulation of tissue mechanics with cell polarization*. Nature Computational Science 4, 299–309 (2024). https://doi.org/10.1038/s43588-024-00620-9
- 论文明确支持用闭合三角曲面表示细胞、ECM、腔体和细胞核，并通过表面张力、弯曲、面积/体积及黏附—排斥接触求平衡；它没有验证斑马鱼心室 ECM 参数，也没有提供显式心肌肌原纤维模型。

