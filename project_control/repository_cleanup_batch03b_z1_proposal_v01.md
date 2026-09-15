---
document_id: PRL-REPOSITORY-CLEANUP-BATCH03B-Z1-PROPOSAL-V01
status: passed
recorded_at: 2026-09-14
deletion_executed: true
scientific_execution: not_run
---

# Batch 3B：被取代Z1结果与本轮缓存精确删除提案

## 执行结果

用户按本页冻结口令授权后，45 个精确目录已全部删除：1,275 个文件、490,593,270 bytes，剩余 0；授权已经消费。13 个保留 Z1 包、当前长程 114 项结果哈希和 14 项来源哈希均通过删除前后复核。完整门禁、删除后测量及退役测试依赖修复见[执行记录](repository_cleanup_batch03b_execution_v01.md)。

## 裁决摘要

当前 `results\ventricle_z1` 有55个结果目录、2,503个文件、1,145,414,174 bytes。本轮保留13个直接支撑当前SimuCell3D主线、换核资格、关键失败和后续主动收缩接口的包，共1,242文件、654,934,600 bytes；其余42个被取代探索包共1,261文件、490,479,574 bytes列入永久删除。

另外，本次Batch 3A验收运行重建了3个纯缓存目录，共14文件、113,696 bytes。它们是本任务产生的非权威临时产物，不含原始材料或唯一成果，也一并列入本次新确认清单。

总删除范围为45个精确目录、1,275文件、490,593,270 bytes（467.866 MiB）；Git跟踪文件0，reparse point 0。现已全部删除。

## 明确保留的13个Z1结果包

| 绝对路径 | 文件 | 字节 | 保留依据 |
|---|---:|---:|---|
| `E:\Temp-Projects\PRL\results\ventricle_z1\v01_20260911` | 41 | 3,786,462 | Z1入口、初始几何与数据缺项基线 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_bioform_myo_a_v02_20260913` | 87 | 79,265,034 | 内禀骨架资格中的关键数值失败 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_bioform_myo_r_v03_20260913` | 72 | 102,812,344 | 当前恒定方向骨架合成机制资格 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1tf2m0_simucell3d_migration_v01_20260912` | 60 | 42,457,285 | SimuCell3D换核七门资格证据 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1tf2b_simucell3d_shape_formation_v01_20260912` | 156 | 55,061,337 | 三层形态形成的体积失控关键失败 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_high_amp_deformability_repair_v03_20260913` | 43 | 23,914,908 | 五胞可变形性修复后的合成资格 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_cycle_amp_repair_v02_20260913` | 37 | 17,797,015 | 单胞/同步激活及幅度响应资格 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914` | 22 | 5,865,293 | 固定链接载荷导致网格退化的紧凑诊断包 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_2d_m0_v01_20260914` | 60 | 8,571,766 | 当前二维初始几何资格 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_relaxation_v01_20260914` | 113 | 13,891,481 | 整片接触穿透关键失败 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_contact_repair_v02_20260914` | 300 | 17,023,397 | 修复后正间隙整片资格 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_contact_barrier_v01_20260914` | 136 | 57,431,062 | 当前双胞排斥、步长裁切及接触回归 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_long_doublet_v01_20260914` | 115 | 227,057,216 | 当前最新长程双胞、场量、性能和静态平衡失败 |

这些目录保持原位，不迁入第二套结果树。保留总量为654,934,600 bytes（624.594 MiB）。

## 待永久删除的42个被取代Z1结果目录

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_formal_v01_20260912` | 3 | 5,013 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_formal_v02_20260912` | 5 | 24,368 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_formal_v03_20260912` | 5 | 24,765 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_formal_v04_20260912` | 31 | 2,498,444 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v01_20260912` | 17 | 98,663 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v02_20260912` | 19 | 6,281,670 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v03_20260912` | 19 | 6,281,237 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v04_20260912` | 30 | 8,094,778 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v05_20260912` | 35 | 8,107,263 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\parent_repair_v06_20260912` | 37 | 8,231,219 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\tissue_formation_pilot_v01_20260912` | 31 | 11,094,186 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\tissue_formation_pilot_v02_20260912` | 44 | 13,645,517 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\tissue_formation_pilot_v03_20260912` | 47 | 13,670,634 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\tissue_formation_pilot_v04_20260912` | 48 | 13,932,742 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_contact_repair_v02_dev01_20260914` | 29 | 2,786,243 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_contact_repair_v02_dev02_20260914` | 41 | 2,819,701 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_sheet_contact_repair_v02_dev03_20260914` | 41 | 2,819,859 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_cycle_amp_v01_20260913` | 62 | 33,667,266 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_cycle_amp_visual_v03_20260913` | 6 | 5,415,580 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_high_amp_deformability_repair_v02_20260913` | 51 | 32,586,955 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_high_amp_deformability_v01_20260913` | 75 | 43,327,687 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_high_amp_deformability_visual_v04_20260913` | 4 | 220,869 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_high_amp_deformability_visual_v05_20260913` | 6 | 2,848,056 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_l5_a_pilot_v01_20260913` | 36 | 25,414,198 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_l5_a_repair_v02_20260913` | 29 | 12,666,127 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_l5_a_v01_20260913` | 53 | 28,666,149 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1_myo_strip_load_boundary_v01_20260914` | 82 | 69,199,141 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1a_v02_20260911` | 28 | 4,441,013 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1b_v01_20260911` | 19 | 1,973,160 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1b_v02_20260911` | 22 | 1,635,530 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1b_v03_20260911` | 21 | 1,642,650 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1b_v04_20260911` | 25 | 1,646,615 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v01_20260911` | 11 | 190,793 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v02_20260911` | 15 | 6,778,582 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v03_20260911` | 15 | 6,778,554 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v04_20260911` | 18 | 7,948,153 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v05_20260911` | 28 | 9,705,239 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v06_20260911` | 29 | 9,803,485 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v07_20260911` | 36 | 26,785,106 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1c_v08_20260911` | 35 | 26,784,529 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1tf2a_dcm_ecm_precheck_v01_20260912` | 32 | 12,705,029 |
| `E:\Temp-Projects\PRL\results\ventricle_z1\z1tf2a_dcm_ecm_precheck_v02_20260912` | 41 | 17,232,806 |

分类汇总：旧parent formal/repair 39,647,420 bytes；旧tissue formation pilots 52,343,079；早期Z1a/b/c 106,113,409；已被真实换核替代的TF2A预检29,937,835；整片接触开发包8,425,803；被最终修复/诊断包替代的strip结果254,012,028。

## 本轮任务产生的3个缓存目录

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\.pytest_cache` | 4 | 2,131 |
| `E:\Temp-Projects\PRL\scripts\__pycache__` | 5 | 95,553 |
| `E:\Temp-Projects\PRL\tests\__pycache__` | 5 | 16,012 |

这些目录由本次Batch 3A验收命令重建，均可重建，不含正式结果。

## 依赖与不可恢复影响

- 当前构建、13个保留结果包、Z0、原始data、专家方案、合同、SimuCell3D源码及许可证均不在清单内。
- 42个Z1候选均为未被Git跟踪的派生结果；删除后不能依赖Git恢复。旧合同和执行记录保留，但指向删除包的历史链接将登记为退役链接。
- `z1_myo_strip_load_boundary_v01_20260914`的大型失败轨迹将由保留的紧凑诊断包替代；早期strip可变形性/幅度失败由保留的最终repair包和原执行记录替代。
- TF2A预检由保留的实际SimuCell3D迁移资格与TF2B失败包取代；早期parent/tissue/Z1a-c路线不再承诺完整复算。
- 本批不改力学方程、源码、阈值或科学裁决，不运行模型。

## 确认与执行门（已完成）

执行前已再次检查45/45存在、总计1,275文件/490,593,270 bytes、Git跟踪0、reparse point 0、严格位于工作区，并验证13个保留Z1包和当前长程哈希；全部通过后才执行删除。

用户实际确认口令：

`确认删除 Batch 3B 清单的45个路径；授权对这45个路径使用System.IO.Directory.Delete递归删除，不授权其他路径`

该确认已消费，且不覆盖13个保留Z1包、Batch 4代码、Batch 5 Git、GPU或新科研运行。
