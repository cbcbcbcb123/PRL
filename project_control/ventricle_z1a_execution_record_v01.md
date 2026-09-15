---
document_id: PRL-VENTRICLE-Z1A-EXECUTION-RECORD-V01
status: current
substage_status: PASS
parent_stage_status: BLOCKED_DEPENDENCY
physics_status: passed_isotropic_sphere_path
visualization_status: passed
claims_status: synthetic_numerical_benchmark_only
executed_at: 2026-09-11
authorization: project_control/ventricle_z1a_execution_authorization_v01.md
contract: project_control/ventricle_z1a_sphere_baseline_contract_v01.md
result_package: results/ventricle_z1/z1a_v02_20260911
next_stage_authorized: false
---

# Z1-A 球形保守力与 Laplace 基准执行记录 v01

## 裁决

用户采纳“单细胞参考态与多细胞环境成形分开验证”的新版几何策略后，本轮在 CPU 上只读调用唯一 `E:\MeshCell3D\code\muse_dcm` 2.1.0，实际完成 Z1-A。三档球形网格、体积/表面张力独立及组合方向导数、刚体客观性、合力/合矩、Laplace 压差和网格趋势全部通过冻结门，故 **Z1-A 为 PASS**。

该 PASS 只覆盖各向同性球形的体积保守力与恒表面张力路径。父阶段 Z1 仍为 **BLOCKED_DEPENDENCY**：长轴心肌和扁平心内膜缺少局部材料参考态；弯曲项与全局面积导出未获通过；正式加载、卸载、恢复和参考态成立后的接触尚未运行。

## 冻结输入与实际范围

- 预登记：`results/ventricle_z1/z1a_v02_20260911/preregistration.json`；SHA-256 语义哈希 `87554f0d95039140b5c630d8f01a2c6697f1b6132b748645af618be73d540ba3`；
- 唯一内核：`muse_dcm 2.1.0` @ `fa21321b80a371f107afd398f93d7f69508e20c6`，运行前后只读；
- 模型：80/320/1280 面闭合球形网格，`R0=4.5e-6 m`；`K=6000 Pa`，`gamma=5e-5 N/m`；
- 关闭：弯曲、全局面积弹性、主动、接触、ECM、流体；
- 运行：CPU 最多 4 线程；最终数值主体 `1.309355 s`；无 GPU、无网络、无外部仓库写入。

## 通过结果

- 三档几何最小角 `54.099559°`，开放/非流形边为 0；
- 三项最佳方向导数相对误差：体积 `2.200913e-9`、表面张力 `5.944846e-10`、组合 `7.473686e-10`，均低于 `1e-6`；
- 刚体检查最大能量误差 `2.987515e-13`，最大力协变误差 `3.958426e-15`，最大合力/合矩相对残差分别为 `5.519233e-17`、`1.084509e-17`；
- fine Laplace 压差相对误差 `5.299270e-4`；medium→fine 拟合压差变化 `1.628444e-3`；fine 节点平衡残差 `1.559134e-2`，均通过各自 2% 门；
- 独立验证器不导入求解器，回归测试和统一图形样式验收均通过；三张最终图片已人工检查。

## 保留的失败诊断

唯一内核内置的 `pressure_energy` 与 `surface_tension_energy` 导出仍不适合作为正式能量账本：本轮三种组合相对差分别为 `2.310894e3`、`0.5` 和 `1.627610e2`。Z1-A 使用从几何状态独立重建且已通过方向导数的工作共轭能量；导出字段失败被原样保留，不扩展为弯曲或各向异性路径通过。

## 图像与证据

- 离线入口：`results/ventricle_z1/z1a_v02_20260911/index.html`；
- 模型结构：`figures/z1a_model_structure.png`；
- 冻结门结果：`figures/z1a_gate_overview.png`；
- 梯度收敛：`figures/z1a_gradient_convergence.png`；
- 机器摘要：`summary.json`；原始数据：`geometry_metrics.csv`、`gradient_check.csv`、`rigid_checks.csv`、`laplace_check.csv`、`kernel_energy_export_diagnostic.csv`；
- 独立复核：`verification/independent_verification.json`；目视检查：`visual_qa.json`。

## 下一门

下一步是 Z1-B 的最小参考态修复设计：在唯一内核中明确局部参考度量、静止边长/角度或等价的各向异性材料状态，并验证无载保持与卸载恢复。该工作涉及 `E:\MeshCell3D` 外部仓库写入，本轮未授权；Z1-C、多细胞桥接、Z2 和 Z4 均未授权、未运行。

