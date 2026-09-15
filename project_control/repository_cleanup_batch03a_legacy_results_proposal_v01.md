---
document_id: PRL-REPOSITORY-CLEANUP-BATCH03A-LEGACY-RESULTS-PROPOSAL-V01
status: completed
recorded_at: 2026-09-14
copy_executed: true_169_files_55720718_bytes_hash_verified
deletion_executed: true_nineteen_of_nineteen
scientific_execution: not_run
---

# Batch 3A：旧路线结果精选与永久删除提案

## 裁决摘要

本提案只覆盖已经退出当前前向主线的 Hybrid、Route H、Paper2 和 NCS/FEM 结果。19个待退役顶层目录共14,089个普通文件、1,640,809,991 bytes（1,564.798 MiB）；其中570个文件当前被旧Git历史跟踪，reparse point为0。

执行顺序固定为：先把55,720,718 bytes（53.139 MiB）精选证据按原相对路径复制到 `E:\Temp-Projects\PRL\project_control\evidence\retired_routes_v01`，逐文件核对字节数和SHA-256，再删除下列19个原目录。预计净释放1,585,089,273 bytes（1.476 GiB），工作区由当前约7.310 GiB降至约5.834 GiB；2 GiB目标仍需Batch 3B和Batch 5完成。

当前状态：用户按本页确认文本授权后，精选证据已复制并通过169/169哈希验收，19/19目录已经删除；详情见[执行记录](repository_cleanup_batch03a_execution_v01.md)和[退役路径映射](repository_cleanup_retired_path_map_v01.md)。本次未处理当前 `results\ventricle_z0`、`results\ventricle_z1`、源码、原始数据、专家方案、合同、许可证、Git历史或任何其他路径。

## 精选证据

### Hybrid：周期不稳定、折叠诊断和事务修复

保留最终ST1失败的两个完整周期数值状态、末态检查点、逐周期与总时间序列、汇总和输入暖启动包；不保留128个accepted-step及其每步worker staging。另完整保留R1中点折叠诊断和事务幸存者修复包。

- 11个ST1指定文件：32,761,335 bytes；机器清单逐项冻结了绝对源路径、字节和SHA-256。
- `E:\Temp-Projects\PRL\results\hybrid\prl_figure2_spatial_tolerance_st1_warm_e1_v04_20260901`：3文件，1,967,852 bytes。
- `E:\Temp-Projects\PRL\results\hybrid\x1_k_r1_midpoint_collapse_diagnosis_v10`：49文件，1,469,877 bytes。
- `E:\Temp-Projects\PRL\results\hybrid\x1_k_transactional_survivor_repair_v11`：43文件，1,365,635 bytes。

保留能力：可独立读取两个周期的状态数组，复核周期波形差、末态差、几何门和关键失败诊断。失去能力：不能恢复全部逐步优化候选、worker staging或完整旧探索矩阵，也不再承诺原路线直接重跑。

### Route H：最终非法数值失败

- 完整保留 `E:\Temp-Projects\PRL\results\route_h\stage2_gate_a_v04`：30文件，11,105,701 bytes。

该包同时包含A0接受轨迹、A1最后有效轨迹、被拒绝候选、失败快照、逐步审计、网格与图件，可支持“被拒绝候选未污染接受轨迹”的复核。更早v01-v03和其他载荷探索不再保留完整结果。

### Paper2：谱系奇模态边界

- 完整保留 `E:\Temp-Projects\PRL\results\paper2_lineage_odd_mode_gate`：2文件，167,694 bytes。

保留v02运行时失败和v03 `NOT_RESOLVED`总裁决；其余Paper2探针、参数矩阵和预览不再保持完整结果。专家原件、采纳决定、合同和失败记录仍保留在 `plan` 与 `project_control`。

### NCS/FEM：最终合格基准

- 完整保留 `E:\Temp-Projects\PRL\results\ncs_m1_all_fem\v03_20260910`：31文件，6,882,624 bytes。

保留最终合格的NPZ、汇总和正式PNG/SVG；v01/v02版本演进不再保留。该合成FEM基准仅作为历史资格证据，不重新进入当前主线。

## 待永久删除的19个精确目录

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\results\hybrid` | 13,528 | 1,225,646,833 |
| `E:\Temp-Projects\PRL\results\ncs_m1_all_fem` | 113 | 16,727,542 |
| `E:\Temp-Projects\PRL\results\paper2_cell_bloch_asymptotic_probe` | 1 | 416,331 |
| `E:\Temp-Projects\PRL\results\paper2_cell_mode_drive_overlap` | 1 | 21,232 |
| `E:\Temp-Projects\PRL\results\paper2_closed_cell_ritz_probe` | 2 | 83,887 |
| `E:\Temp-Projects\PRL\results\paper2_division_dipole_gate` | 2 | 36,124 |
| `E:\Temp-Projects\PRL\results\paper2_feedback_kernel` | 2 | 92,026 |
| `E:\Temp-Projects\PRL\results\paper2_impedance_shift` | 27 | 105,767,559 |
| `E:\Temp-Projects\PRL\results\paper2_lineage_odd_mode_gate` | 2 | 167,694 |
| `E:\Temp-Projects\PRL\results\paper2_m1` | 57 | 10,674,898 |
| `E:\Temp-Projects\PRL\results\paper2_natural_probe` | 1 | 1,955,892 |
| `E:\Temp-Projects\PRL\results\paper2_pair_junction_probe` | 1 | 2,160,831 |
| `E:\Temp-Projects\PRL\results\paper2_rest_length_write_read` | 1 | 88,896 |
| `E:\Temp-Projects\PRL\results\paper2_science_pilot` | 61 | 133,764,364 |
| `E:\Temp-Projects\PRL\results\paper2_shape_coupling_coefficients` | 1 | 553,537 |
| `E:\Temp-Projects\PRL\results\paper2_static_mode_screen` | 18 | 3,322,199 |
| `E:\Temp-Projects\PRL\results\paper2_transverse_notch` | 23 | 70,459,438 |
| `E:\Temp-Projects\PRL\results\paper2_v08` | 9 | 186,234 |
| `E:\Temp-Projects\PRL\results\route_h` | 239 | 68,684,474 |

按路线汇总：Hybrid 1,225,646,833 bytes；Paper2 329,751,142 bytes；Route H 68,684,474 bytes；NCS/FEM 16,727,542 bytes。

## 依赖、链接与不可恢复影响

- 这些目录不是当前SimuCell3D心肌→心内膜→ECM运行依赖；当前活动构建和Z0/Z1结果不在清单内。
- 旧合同与执行记录中存在指向原 `results` 路径的历史链接。原文不改写；执行后另建退役映射，标出精选证据新位置及不再可访问的原路径。
- 570个Git跟踪文件会在旧工作树中显示删除，这是Batch 5建立新基线前的预期状态；不提交、不推送、不改远端历史。
- 删除后，未进入精选包的1,585,089,273 bytes历史结果不可从新基线恢复；旧Git对象暂时仍占空间，但Batch 5验收后也将永久移除。
- 精选包不是完整历史压缩包，不能据此声称所有旧计算可重跑。它只支持冻结结论、关键失败和有限独立复核。

## 执行门与确认文本

执行前已重新检查19/19存在、严格位于工作区、reparse point为0、文件与字节数无漂移。复制后逐文件哈希一致且精选包可读取，才调用获准删除接口；全部门禁通过。

用户已准确回复冻结确认文本，该授权已经消费。它不覆盖Batch 3B被取代Z1结果、Batch 4代码、Batch 5 Git、GPU或新科研运行。
