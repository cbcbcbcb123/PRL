---
document_id: PRL-REPOSITORY-CLEANUP-BATCH03B-EXECUTION-V01
status: passed
recorded_at: 2026-09-14
authorization: exact_forty_five_paths_system_io_directory_delete
deleted_paths: 45
deleted_files: 1275
deleted_bytes: 490593270
scientific_execution: not_run
---

# Batch 3B 被取代 Z1 结果与缓存删除执行记录 v01

## 授权与范围

用户明确回复：`确认删除 Batch 3B 清单的45个路径；授权对这45个路径使用System.IO.Directory.Delete递归删除，不授权其他路径`。

本次只加载[冻结机器清单](evidence/repository_cleanup_v01/batch03b_z1_proposal.json)中的 45 个绝对目录：42 个被取代的 Z1 派生结果目录和 3 个本轮任务产生的 Python 缓存目录。13 个保留 Z1 包、源码、活动构建、原始数据、专家方案、Git 历史、GPU 和新科研运行均不在授权范围。

## 删除前门禁

| 检查 | 结果 |
|---|---:|
| 精确目标 | 45/45 存在 |
| 普通文件 | 1,275 |
| 逻辑字节 | 490,593,270 |
| Git 跟踪命中 | 0 |
| 目标或内部 reparse point | 0 |
| 工作区边界 | 45/45 严格位于 `E:\Temp-Projects\PRL` 内且不等于工作区根 |
| 目标重复或父子重叠 | 0 |
| 与 13 个保留包重叠 | 0 |
| 当前长程结果哈希 | 114/114 通过 |
| 当前来源哈希 | 14/14 通过 |

45 个目标逐项文件数和字节数以及总量均与冻结提案一致。路径直接来自机器清单，没有使用通配符、宽泛父目录、未解析环境变量、目录映射或跨 shell 路径传递。

## 删除执行与后验

全部预检通过后，在同一 PowerShell 流程中对 45 个已解析目标逐项调用用户授权的 `[System.IO.Directory]::Delete(resolved_target, true)`。45/45 成功，剩余 0；没有调用其他目标。

| 检查 | 结果 |
|---|---|
| 原 45 个目录 | 45/45 不存在 |
| 13 个保留 Z1 包 | 13/13 存在；1,242 文件、654,934,600 bytes，与冻结清单一致 |
| 活动构建 `b\z1m0a` | 存在 |
| SimuCell3D `src/include/LICENSE` | 存在 |
| `data/plan/project_control` | 存在 |
| 当前 Z0 与长程 Z1 包 | 存在 |
| 当前长程结果哈希 | 114/114 通过 |
| 当前来源哈希 | 14/14 通过 |
| 科研求解器/GPU | `not_run`；活动匹配进程 0 |

删除后、最终文档写入前的工作区测量为 14,982 个普通文件、5,773,416,149 bytes（5.377 GiB）。本批直接释放 490,593,270 bytes（467.866 MiB）；后续执行记录和导航更新会增加少量文本字节，不改变直接释放量。

## 回归中发现并关闭的退役依赖

首次无缓存回归为 12 passed、1 failed。失败不是力学行为回归，而是 `tests/test_myo_sheet_contact_repair_v02.py` 仍直接读取已获批退役的 `z1_myo_sheet_contact_repair_v02_dev01_20260914/verdict.json`。该测试已改为读取保留的正式 `z1_myo_sheet_contact_repair_v02_20260914/verdict.json`，继续检查黏附、网格细化、正式矩阵状态和限定适用范围；没有恢复已删除目录、放宽门限或修改力学实现。随后同一组无缓存回归为 13 passed，且 `.pytest_cache`、`scripts\__pycache__`、`tests\__pycache__` 均未重建。

dev01 的历史结论仍在 `ventricle_myocardial_sheet_contact_repair_execution_v02.md` 中原样保留；其原始开发结果包已按本批授权永久裁减，不再声称可完整复算。

## 裁决

Batch 3B 为 `passed`，本次删除授权已消费。这是存储治理与退役依赖修复结果，不改变科学裁决：长程双胞数值资格仍为 `passed`，静态平衡仍为 `failed`，父 Z1 与生物验证仍为 `blocked`。

下一批仅进入 Batch 4 当前代码依赖审计、解耦方案和精确变更清单；不自动删除代码、不重建 Git、不运行科研模型。
