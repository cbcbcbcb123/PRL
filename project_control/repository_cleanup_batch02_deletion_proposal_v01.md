---
document_id: PRL-REPOSITORY-CLEANUP-BATCH02-DELETION-PROPOSAL-V01
status: completed
recorded_at: 2026-09-14
deletion_executed: true_thirty_of_thirty
scientific_validation: not_run
---

# Batch 2：缓存、构建与编译烟测精确删除提案

## 裁决与影响

下列30个绝对路径共 **4,338个普通文件、287,147,295 bytes（273.845 MiB）**。全部位于工作区内，`git ls-files` 均为0；不含当前活动构建 `E:\Temp-Projects\PRL\b\z1m0a`、SimuCell3D源码/许可证、正式results、原始data或project_control记录。

删除后可回收约273.845 MiB。缓存会自动重建；构建目录需要重新配置/编译；旧编译烟测逐步CSV将不可恢复，但它们无文档引用、不是正式结果，正式执行/失败证据位于results及project_control。清理不会解决2 GiB目标，主要空间仍须在Batch 3与5处理。

**当前状态：用户另行明确授权同一30路径使用`System.IO.Directory.Delete`后，30/30删除成功。** 首次`Remove-Item`阻断记录仍保留，不改写。

## A. 缓存：1,461,880 bytes

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\.pytest_cache` | 5 | 4,772 |
| `E:\Temp-Projects\PRL\.ruff_cache` | 3 | 227 |
| `E:\Temp-Projects\PRL\scripts\__pycache__` | 53 | 1,348,663 |
| `E:\Temp-Projects\PRL\tests\__pycache__` | 12 | 108,218 |

## B. 可重建构建树：228,783,680 bytes

| 绝对路径 | 文件 | 字节 | 重建来源/影响 |
|---|---:|---:|---|
| `E:\Temp-Projects\PRL\external\simucell3d\build-prl-ventricle-m0-v01` | 1,215 | 51,493,984 | 源码仍在external/simucell3d；旧迁移构建 |
| `E:\Temp-Projects\PRL\b\z1m0` | 1,249 | 57,785,123 | 源码仍在external/simucell3d；不等于保留的z1m0a |
| `E:\Temp-Projects\PRL\b\z1_bioform_myo` | 462 | 46,408,908 | 源码仍在src/ventricle_bioform_myo；旧条带入口需重编译 |
| `E:\Temp-Projects\PRL\b\simucell3d_regression_v02` | 883 | 37,655,073 | 源码仍在external/simucell3d；历史回归构建 |
| `E:\Temp-Projects\PRL\b\z1tf2b` | 380 | 35,440,592 | 源码仍在src/ventricle_simucell3d_tf2b；换核资格构建 |

这些历史程序的哈希和执行结论仍在原结果/记录中；删除二进制意味着不能直接再次调用，需从保留源码重建。当前正式心肌双胞程序均位于保留的 `b\z1m0a\Release`。

## C. 已登记项目内编译临时目录：571 bytes

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\tmp\contact_barrier_v01_build` | 1 | 255 |
| `E:\Temp-Projects\PRL\tmp\myo_long_doublet_v01_build` | 1 | 316 |

两者只含OWNERSHIP.md和空MSBuildTemp，无原始或唯一成果。前者以前获过单路径批准，但调用被工具拦截；本次作为新整批清单重新确认。

## D. 无引用编译烟测输出：56,901,164 bytes

| 绝对路径 | 文件 | 字节 |
|---|---:|---:|
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v01` | 4 | 535,022 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v02` | 4 | 533,545 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v03` | 3 | 399,641 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v04` | 3 | 2,324,620 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v05_s020` | 4 | 1,797,463 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v05_s040` | 4 | 1,777,445 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v05_s060` | 4 | 1,762,351 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v06_s020` | 4 | 1,805,425 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v06_s040` | 4 | 1,801,034 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v06_s060` | 4 | 1,799,286 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v06_m320_s060` | 4 | 3,874,264 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v07_m320_s060` | 4 | 3,863,805 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v08_m320_s060` | 4 | 3,868,865 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v09_m320_s060` | 4 | 3,885,826 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v10_m320_s060` | 4 | 3,899,434 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v11_m320_s060` | 4 | 4,696,764 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v12_m320_s060` | 4 | 5,517,671 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v13_m320_s060` | 4 | 5,588,099 |
| `E:\Temp-Projects\PRL\tmp\z1_bioform_myo_compile_smoke_v14_m320_s060` | 4 | 7,170,604 |

每个目录仅含派生 `nodes.csv`、`faces.csv`、`step_audits.csv`、`kernel_metrics.json` 的子集；项目文本检索未发现对这些路径的引用。它们不是已登记正式结果。

## 删除后强制验收（尚未执行）

1. 30/30准确目标不存在；工作区外不受影响；
2. `b\z1m0a`、`external\simucell3d\src/include/LICENSE`、当前结果、data、plan、project_control仍存在；
3. 删除前后Git已跟踪修改集合一致；
4. 当前接触、几何安全、折叠监测与交付检查仍通过；不运行新的科研轨迹；
5. 重新盘点释放字节数并追加不可恢复影响记录；
6. 若执行工具拦截，记录 `blocked`，不换用另一删除接口绕过。

用户先准确回复`确认删除 Batch 2 清单的30个路径`，首次工具调用在进程创建前被拒绝，见[阻断记录v01](repository_cleanup_batch02_execution_v01.md)。随后用户明确授权仅对同一30个路径使用`System.IO.Directory.Delete`递归删除。第二次预检内容完全一致，执行后30/30不存在，实际移除4,338文件、287,147,295 bytes，见[完成记录v02](repository_cleanup_batch02_execution_v02.md)。该授权不覆盖Batch 3、代码删除、Git历史替换、GPU或新的科研运行。
