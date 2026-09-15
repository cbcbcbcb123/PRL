---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-DELETION-PROPOSAL-V01
status: executed_passed
recorded_at: 2026-09-15
deletion_authorized: true
deletion_executed: true
---

# Batch 4 候选3活动Paper2/NCS源码精确删除提案 v01

> 2026-09-15更新：用户已按本提案的精确38路径和两个指定.NET接口授权；执行已`passed`。38/38目标、61文件、1,541,224 bytes永久删除，详见[执行记录](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)。本批授权已消费。

## 裁决摘要

退出前安全切片已`passed`，现冻结38个顶层目标：8个递归目录和30个单文件，共61个普通文件、1,541,224 bytes。Git状态为35个`tracked_clean`、0个`tracked_modified`、26个`untracked`；目标及后代reparse point为0。

精确绝对路径清单为[batch04_candidate03_deletion_targets_v01.txt](evidence/repository_cleanup_v01/batch04_candidate03_deletion_targets_v01.txt)，SHA-256为`2d612a361cbf1f37c1f2c05d07e1a9bac4a3a0b3c506b9b4c57bf06d73a7e6de`。执行时只能从该冻结文件逐项加载，不得枚举或扩大父目录。

## 38个目标

| 规范化绝对路径 | 类型/递归 | 文件 | bytes | Git tracked/untracked | reparse |
|---|---|---:|---:|---:|---:|
| `E:\Temp-Projects\PRL\src\ncs_m1` | 目录/是 | 2 | 63,140 | 0/2 | 0 |
| `E:\Temp-Projects\PRL\src\paper2_figure2` | 目录/是 | 7 | 157,207 | 0/7 | 0 |
| `E:\Temp-Projects\PRL\src\paper2_hybrid` | 目录/是 | 8 | 81,075 | 8/0 | 0 |
| `E:\Temp-Projects\PRL\src\paper2_m1` | 目录/是 | 2 | 46,491 | 2/0 | 0 |
| `E:\Temp-Projects\PRL\tests\ncs_m1` | 目录/是 | 1 | 1,483 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\tests\paper2_figure2` | 目录/是 | 7 | 125,774 | 0/7 | 0 |
| `E:\Temp-Projects\PRL\tests\paper2_hybrid` | 目录/是 | 3 | 6,502 | 3/0 | 0 |
| `E:\Temp-Projects\PRL\tests\paper2_m1` | 目录/是 | 1 | 4,993 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\tests\test_paper2_lineage_odd_mode_gate_v02.py` | 文件/否 | 1 | 5,778 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\tests\test_paper2_lineage_odd_mode_gate_v03.py` | 文件/否 | 1 | 3,173 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\analyze_paper2_first_mode_transfer_v01.py` | 文件/否 | 1 | 34,886 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\analyze_paper2_mean_normal_transfer_v01.py` | 文件/否 | 1 | 33,666 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\analyze_paper2_science_pilot_fields_v01.py` | 文件/否 | 1 | 26,034 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_ncs_m1_all_fem_v01.py` | 文件/否 | 1 | 23,111 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_cell_bloch_asymptotic_probe_v01.py` | 文件/否 | 1 | 34,406 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_cell_mode_drive_overlap_v01.py` | 文件/否 | 1 | 32,893 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_closed_cell_ritz_probe_v01.py` | 文件/否 | 1 | 29,068 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_closed_cell_ritz_probe_v02.py` | 文件/否 | 1 | 12,866 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_division_dipole_gate_v01.py` | 文件/否 | 1 | 35,888 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_feedback_kernel_gate_v01.py` | 文件/否 | 1 | 34,811 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 文件/否 | 1 | 217,615 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_impedance_shift_v01.py` | 文件/否 | 1 | 34,743 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_lineage_odd_mode_gate_v01.py` | 文件/否 | 1 | 59,762 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_lineage_odd_mode_gate_v02.py` | 文件/否 | 1 | 68,185 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_lineage_odd_mode_gate_v03.py` | 文件/否 | 1 | 6,604 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_m1_idealized_strip_v01.py` | 文件/否 | 1 | 8,134 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_natural_probe_v01.py` | 文件/否 | 1 | 30,225 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_pair_junction_probe_v01.py` | 文件/否 | 1 | 62,777 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_rest_length_write_read_v01.py` | 文件/否 | 1 | 36,318 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_science_pilot_v01.py` | 文件/否 | 1 | 38,672 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_shape_coupling_coefficients_v01.py` | 文件/否 | 1 | 28,830 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_static_mode_screen_v01.py` | 文件/否 | 1 | 50,718 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_static_mode_screen_v02.py` | 文件/否 | 1 | 8,985 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_static_mode_screen_v03.py` | 文件/否 | 1 | 10,618 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_transverse_notch_v01.py` | 文件/否 | 1 | 35,933 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_transverse_notch_v02.py` | 文件/否 | 1 | 40,789 | 1/0 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_lineage_odd_mode_gate_v02_host.ps1` | 文件/否 | 1 | 4,500 | 0/1 | 0 |
| `E:\Temp-Projects\PRL\scripts\run_paper2_lineage_odd_mode_gate_v03_host.ps1` | 文件/否 | 1 | 4,571 | 0/1 | 0 |

## 可删除依据与不可恢复影响

- 当前默认包发现仅为`prl`与`prl.verification`；默认pytest和显式quick均19/19通过。
- 候选外148个Python文件AST扫描没有导入这些候选文件或退役包；两个宿主包装已纳入本清单，不会留下断裂包装。
- 与精选历史结果直接相关的14个源码以及两个宿主包装，合计16文件、369,160 bytes，已在`project_control/evidence/retired_routes_v01/source/`逐字节保全。
- 其余45个文件没有进入精选证据；删除后这些旧探索实现将永久退出活动树。Batch 5重建Git基线后不能依赖旧Git历史恢复，也不能再声称旧路线完整可重跑。
- Dolfinx/Basix/MPI/PETSc/UFL、容器镜像和当时Python环境未归档；即使保留16个源码，也只支持证据解释，不承诺完整复现。

## 删除接口与保护路径

若用户确认，8个目录仅允许使用`System.IO.Directory.Delete(resolvedTarget, true)`递归删除；30个文件仅允许使用`System.IO.File.Delete(resolvedTarget)`。执行前必须重新核对冻结清单SHA-256、每个目标的文件数/字节/Git/reparse状态和工作区边界；任何漂移立即停止。

删除后必须复核以下关键路径保持存在且身份通过：

- `E:\Temp-Projects\PRL\project_control\evidence\retired_routes_v01\source`；
- `E:\Temp-Projects\PRL\project_control\evidence\repository_cleanup_v01\batch04_candidate03_exit_safe_slice_identity.json`；
- `E:\Temp-Projects\PRL\src\prl`与`E:\Temp-Projects\PRL\tests\prl`；
- `E:\Temp-Projects\PRL\src\prl_ventricle_support`与`E:\Temp-Projects\PRL\external\simucell3d`；
- `E:\Temp-Projects\PRL\results`、`E:\Temp-Projects\PRL\plan`和`E:\Temp-Projects\PRL\project_control`。

本删除是永久性的，不进入回收站。现已按冻结范围执行完成；没有处理其他路径。

本批当时要求使用的确认文本为：

`确认删除 Batch 4 候选3清单的38个路径；授权对其中8个目录使用System.IO.Directory.Delete递归删除，对30个文件使用System.IO.File.Delete；不授权其他路径`
