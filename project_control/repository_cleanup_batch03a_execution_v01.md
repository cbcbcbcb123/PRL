---
document_id: PRL-REPOSITORY-CLEANUP-BATCH03A-EXECUTION-V01
status: passed
recorded_at: 2026-09-14
authorization: exact_nineteen_paths_system_io_directory_delete_after_verified_copy
retained_files: 169
retained_bytes: 55720718
deleted_paths: 19
deleted_files: 14089
deleted_bytes: 1640809991
---

# Batch 3A旧路线结果精选与删除执行记录 v01

## 授权与边界

用户明确回复：`确认执行 Batch 3A：先复制并验收55720718 bytes精选证据，再删除清单中的19个路径；授权对这19个路径使用System.IO.Directory.Delete，不授权其他路径`。

本次只加载[冻结机器清单](evidence/repository_cleanup_v01/batch03a_legacy_results_proposal.json)中的19个绝对目录。Batch 3B的Z1结果、源码、原始数据、专家方案、Git历史及其他路径均不在授权范围。

## 删除前门禁

| 检查 | 结果 |
|---|---:|
| 精确目标 | 19/19存在 |
| 普通文件 | 14,089 |
| 逻辑字节 | 1,640,809,991 |
| Git跟踪文件 | 570 |
| 目标或内部reparse point | 0 |
| 工作区边界 | 19/19严格位于 `E:\Temp-Projects\PRL` 内且不等于工作区根 |
| 精选源漂移 | 0 |

文件数和字节数与冻结提案完全一致。每个目标均由冻结清单逐项解析，没有使用通配符、目录枚举扩展、未解析环境变量、虚拟盘或跨shell路径传递。

## 先复制并验收精选证据

169个精选文件按原相对路径复制到 `E:\Temp-Projects\PRL\project_control\evidence\retired_routes_v01`，共55,720,718 bytes。复制过程中逐文件比较源与目标的字节数和SHA-256，失败0；删除完成后又以Batch 1原始盘点清单独立复核一次，169/169一致。

- [保留文件逐项清单](evidence/repository_cleanup_v01/batch03a_retained_manifest.jsonl)，SHA-256 `04b53d7a80fccf20460eabc96b37800e4c4cc88c88be54ff50de422d18484fd2`；
- [保留摘要](evidence/repository_cleanup_v01/batch03a_retained_summary.json)，SHA-256 `2f2c95f2c9c8eba864b9581a89e42ec82f780cde8879c6ce02a19580076296d8`；其中冻结提案哈希明确标为执行时版本，提案随后只更新为`completed`；
- [退役路径映射](repository_cleanup_retired_path_map_v01.md)。

精选包保留冻结结论、关键失败和有限独立复核能力，不是完整历史备份；被裁减的逐步worker staging、旧探索矩阵和中间版本不再可由新基线恢复。

## 删除执行与后验

复制验收全部通过后，在同一PowerShell进程中对19个已解析目标逐项调用用户授权的 `[System.IO.Directory]::Delete(resolved_target, true)`。19/19成功，剩余0；没有调用其他目标。

| 检查 | 结果 |
|---|---|
| 原19个目录 | 19/19不存在 |
| 精选证据 | 169文件、55,720,718 bytes、哈希失败0 |
| 活动构建 `b\z1m0a` | 存在 |
| SimuCell3D `src/include/LICENSE` | 存在 |
| `data/plan/project_control` | 存在 |
| 当前Z0/Z1与长程包 | 存在 |
| 当前长程结果哈希 | 114/114通过 |
| 当前来源哈希 | 14/14通过 |
| 接触/几何/清理回归 | 13 passed |
| 科研求解器/GPU | not_run |

本次由“复制精选证据后删除原目录”直接净释放1,585,089,273 bytes（1.476 GiB）。删除后、写入最终记录前的工作区测量为16,236个普通文件、6,263,805,804 bytes（5.833624 GiB）。最终文档与导航会产生少量新增字节，不改变1.476 GiB净释放事实。

570个旧Git跟踪文件现在表现为预期删除；未提交、未推送，也未修改远端历史。Batch 3A授权已消费，不覆盖Batch 3B。

## 裁决

Batch 3A为`passed`。这是存储治理结果，不改变任何科学裁决：长程双胞数值资格仍为`passed`，静态平衡仍为`failed`，父Z1与生物验证仍为`blocked`。
