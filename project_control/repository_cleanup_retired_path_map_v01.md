---
document_id: PRL-REPOSITORY-CLEANUP-RETIRED-PATH-MAP-V01
status: current
recorded_at: 2026-09-14
scope: batch03a_batch03b_batch04_candidate03
---

# Batch 3A–3B结果及Batch 4候选3源码退役路径映射

本页不改写历史合同或执行记录。历史文档仍可保留原始路径文字，但下表明确说明原路径已经永久退役，以及是否存在精选证据。精选根目录为 `E:\Temp-Projects\PRL\project_control\evidence\retired_routes_v01`。

| 已删除原路径 | 精选证据或当前解释 |
|---|---|
| `E:\Temp-Projects\PRL\results\hybrid` | 保留ST1两个完整周期状态/检查点/时间序列/汇总、输入暖启动、R1折叠诊断及事务修复；路径为 `project_control\evidence\retired_routes_v01\results\hybrid\...`。其他Hybrid结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\route_h` | 完整保留 `project_control\evidence\retired_routes_v01\results\route_h\stage2_gate_a_v04`；其他Route H结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\ncs_m1_all_fem` | 完整保留 `project_control\evidence\retired_routes_v01\results\ncs_m1_all_fem\v03_20260910`；v01/v02永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_lineage_odd_mode_gate` | 完整保留 `project_control\evidence\retired_routes_v01\results\paper2_lineage_odd_mode_gate`。 |
| `E:\Temp-Projects\PRL\results\paper2_cell_bloch_asymptotic_probe` | 无结果文件迁入精选包；合同/结论记录保留在 `project_control`。 |
| `E:\Temp-Projects\PRL\results\paper2_cell_mode_drive_overlap` | 无结果文件迁入精选包；合同/结论记录保留在 `project_control`。 |
| `E:\Temp-Projects\PRL\results\paper2_closed_cell_ritz_probe` | 无结果文件迁入精选包；合同/结论记录保留在 `project_control`。 |
| `E:\Temp-Projects\PRL\results\paper2_division_dipole_gate` | 无结果文件迁入精选包；合同/结论记录保留在 `project_control`。 |
| `E:\Temp-Projects\PRL\results\paper2_feedback_kernel` | 无结果文件迁入精选包；合同/结论记录保留在 `project_control`。 |
| `E:\Temp-Projects\PRL\results\paper2_impedance_shift` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_m1` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_natural_probe` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_pair_junction_probe` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_rest_length_write_read` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_science_pilot` | 无完整结果包迁入；关键谱系奇模态边界已由保留的v03摘要和治理记录覆盖。 |
| `E:\Temp-Projects\PRL\results\paper2_shape_coupling_coefficients` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_static_mode_screen` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_transverse_notch` | 无结果文件迁入精选包；旧结果永久裁减。 |
| `E:\Temp-Projects\PRL\results\paper2_v08` | 无结果文件迁入精选包；旧结果永久裁减。 |

## Batch 3B Z1退役路径

Batch 3B按[精确提案](repository_cleanup_batch03b_z1_proposal_v01.md)及[执行记录](repository_cleanup_batch03b_execution_v01.md)永久删除42个被取代的Z1派生结果目录；完整绝对路径、文件数和字节数仍由[冻结机器清单](evidence/repository_cleanup_v01/batch03b_z1_proposal.json)逐项保存。它们按证据替代关系解释如下：

| 退役组 | 当前解释或保留证据 |
|---|---|
| `parent_formal_v01–v04`、`parent_repair_v01–v06`、`tissue_formation_pilot_v01–v04` | 早期形态形成探索永久裁减；换核资格、体积失控关键失败和当前方向骨架资格分别由保留的 `z1tf2m0_simucell3d_migration_v01_20260912`、`z1tf2b_simucell3d_shape_formation_v01_20260912`、`z1_bioform_myo_r_v03_20260913` 支撑。 |
| `z1a_v02`、`z1b_v01–v04`、`z1c_v01–v08`、`z1tf2a_dcm_ecm_precheck_v01–v02` | 早期Z1与TF2A预检永久裁减；合同和执行记录保留，不再承诺原包完整复算。 |
| `z1_myo_sheet_contact_repair_v02_dev01–dev03` | 开发失败/过渡包永久裁减；失败数值结论保留在 `ventricle_myocardial_sheet_contact_repair_execution_v02.md`，当前正式资格由保留的 `z1_myo_sheet_contact_repair_v02_20260914` 支撑。 |
| 早期/视觉版 strip cycle、high-amplitude、L5 与大型 load-boundary 包 | 被保留的最终幅度、可变形性修复包和紧凑网格退化诊断包替代；旧大轨迹及重复预览永久裁减。 |

Batch 3B另删除3个当次任务产生的Python缓存目录；它们不是科学证据，不登记为历史结果链接。

## Batch 4候选3源码退役路径

2026-09-15按[精确提案](repository_cleanup_batch04_candidate03_deletion_proposal_v01.md)及[执行记录](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)永久删除8个源码/测试目录和30个单文件，共38个顶层路径、61个文件、1,541,224 bytes。16个与精选证据直接相关的源码及宿主包装、369,160 bytes保存在`project_control/evidence/retired_routes_v01/source/`，并由32项当前保护身份覆盖；其余45个实现永久裁减。

| 退役组 | 当前解释或保留证据 |
|---|---|
| `src/ncs_m1`与相关runner | 两个包文件和`run_ncs_m1_all_fem_v01.py`保存在精选源码区；外部FEniCSx环境未归档，不承诺完整重跑。 |
| `src/paper2_hybrid`与关键门脚本 | 6个最小包文件以及division、feedback和lineage v01–v03关键runner保存在精选源码区。 |
| 两个lineage host包装 | v02/v03包装逐字节保存在精选源码区。 |
| `src/paper2_figure2`、`src/paper2_m1`、退役测试及其余分析/runner | 未进入精选证据的45个实现永久裁减；合同、执行结论和已选结果证据继续保留。 |

Batch 3A逐文件来源、字节和SHA-256见 [Batch 3A保留清单](evidence/repository_cleanup_v01/batch03a_retained_manifest.jsonl)。Batch 3A–3B结果及Batch 4候选3源码的机器可读前缀登记见 [retired_paths_v01.json](evidence/repository_cleanup_v01/retired_paths_v01.json)。驾驶舱渲染器不改写append-only任务日志，而是在原路径缺失且命中退役前缀时把链接明确重定向到本映射页。任何旧文档中的原路径仍只是历史引用，不能据此声称路径当前存在或原路线仍可完整复算。
