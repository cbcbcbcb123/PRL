---
document_id: PRL-VENTRICLE-Z1-EXECUTION-RECORD-V01
status: current
stage_status: BLOCKED_DEPENDENCY
physics_status: blocked
visualization_status: passed
claims_status: synthetic_precheck_only
executed_at: 2026-09-11
authorization: project_control/ventricle_z1_execution_authorization_v01.md
geometry_decision: project_control/ventricle_cell_geometry_strategy_decision_v02.md
result_package: results/ventricle_z1/v01_20260911
next_stage_authorized: false
---

# Z1 被动单/双细胞预检执行记录 v01

## 裁决

用户明确同意后，本轮按新版几何分工执行 Z1 预检：球形基准、3:1:1 长轴心肌探针、4:4:1 扁平心内膜探针，以及五种受控双细胞接触方向。预检触发已冻结的停止规则，因此 Z1 最终状态为 **BLOCKED_DEPENDENCY**，不得写为 PASS，也未继续执行正式加载、持载、卸载、恢复、时间细化或体积罚细化。

这不是“长轴或扁平几何不能生成”。三类几何均已由唯一 `E:\MeshCell3D\code\muse_dcm` 2.1.0 实际生成，并通过 3 档网格的闭合、朝向、退化、独立体积和最小角检查；阻断来自当前本构账本与各向异性参考态语义不足。

## 冻结输入与实际范围

- PRL 证据基线：`b45650a9e370be138a70acf305b6c3a21e6a7ed2`；既有 tracked/untracked 修改未回滚、未清理；
- 唯一内核：MeshCell3D `fa21321b80a371f107afd398f93d7f69508e20c6`，运行前后只读；`internal_forces.py` SHA-256 为 `602edc3939624c62999dfab12a1ccab6407ca2b5ae0732958912d1c9ad7df662`；
- 预登记哈希：`c89ef8ba1ff5442b113801e8088526ba833f3c2803b144f4fec7261a1c4708ec`；
- 几何：等体积 1:1:1、3:1:1、4:4:1；网格为 80/320/1280 面；
- 运行：CPU，最多 4 线程，最终主脚本 14.903 s；未启动 GPU，未联网，未安装软件，未写入外部仓库；
- 正式算例：0；全部在 `formal_cases_manifest.json` 中记录为 `not_run_due_to_precheck_stop`。

## 已通过的子检查

- 唯一内核版本与 Git commit 匹配；
- 3 种几何 × 3 档网格的闭合、面朝向、无退化/重复面和独立体积复核通过；全矩阵最小三角角为 `15.277559°`；
- 球形 Laplace 基准通过：fine 网格的拟合压差相对 `2γ/R` 误差为 `5.299270e-4`；
- 五种受控接触均产生有效接触对，最大合力相对残差为 `1.753497e-16`，重复有效接触对为 0；
- 三张 600 dpi PNG/SVG 图已输出并目视检查；两张定量图的统一样式 manifest 均 PASS；
- 不导入求解器的独立复核 PASS；6 项回归测试 PASS。

## 触发停止的阻断

1. `B-Z1-ENERGY-LEDGER`：压力导出能量不是与 `p=K ln(V0/V)` 对应的零参考势能；全局面积力存在但 `membrane_elasticity_energy` 导出为 0；表面张力的导出能量含 1/2 因子。最大能量导出相对差为 `2.435088e3`（扁平心内膜探针/体积项）。
2. `B-Z1-REFERENCE-SHAPE`：当前公开 `CellTypeParameters` 与本构入口没有局部参考度量、静止边长或静止二面角字段，不能把 3:1:1 或 4:4:1 几何声明为有明确材料意义的无应力参考态。
3. `B-Z1-GRADIENT`：体积、面积和表面张力单项可达到冻结梯度门；弯曲项稳定失败，逐案例最佳误差最差为 `1.105057`，组合项也在 `2.788747e-4` 至 `1.875711e-3`，均高于 `1e-6`。
4. `B-Z1-RIGID`：能量客观性和力旋转协变接近机器精度，但组合内力的合力/合矩相对残差为 `2.4290e-5` 至 `7.0384e-4`，高于冻结的 `1e-10` 代数门。

这些失败没有通过改阈值、调参或省略分项来消除。正式 Z1 力学响应及 Z2 均保持 NOT_RUN。

## 图像与证据入口

- 离线入口：`results/ventricle_z1/v01_20260911/index.html`；
- 模型结构：`results/ventricle_z1/v01_20260911/figures/z1_model_structure.png`；
- 能量账本结果：`results/ventricle_z1/v01_20260911/figures/z1_precheck_results.png`；
- 梯度收敛结果：`results/ventricle_z1/v01_20260911/figures/z1_gradient_convergence.png`；
- 总结与原始表：`summary.json`、`metrics.csv`、`geometry_metrics.csv`、`gradient_check.csv`、`energy_export_check.csv`、`rigid_checks.csv`、`laplace_check.csv`、`contact_pair_ledger.csv`；
- 独立复核：`results/ventricle_z1/v01_20260911/verification/independent_verification.json`；
- 图像验收：`results/ventricle_z1/v01_20260911/visual_qa.json`。

## 下一门

不进入 Z2。下一步应先在独立授权下对唯一内核做最小修复设计与验证：统一保守力的工作共轭能量账本；为长轴/扁平细胞定义可审计的局部参考态；修复弯曲梯度和内力合力/合矩门。修复必须发生在 `E:\MeshCell3D`，属于外部仓库写入，当前未授权。

Z1 只有在上述阻断解除后按新版本结果包重新运行完整预检及 AXIAL/TRANSVERSE/RELAX/CONTACT/REFINE 矩阵，才可重新裁决；不得直接复用本包中的静态几何通过项宣布完整 Z1 PASS。
