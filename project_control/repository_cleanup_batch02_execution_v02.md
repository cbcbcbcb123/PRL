---
document_id: PRL-REPOSITORY-CLEANUP-BATCH02-EXECUTION-V02
status: passed
recorded_at: 2026-09-14
authorization: exact_same_thirty_paths_system_io_directory_delete
deleted_paths: 30
deleted_files: 4338
deleted_bytes: 287147295
---

# Batch 2删除执行记录 v02

## 新授权与边界

首次`Remove-Item`尝试在进程创建前被环境策略拒绝，0个路径删除，[v01](repository_cleanup_batch02_execution_v01.md)保留。用户随后明确回复：`授权对 Batch 2 同一30个路径使用 System.IO.Directory.Delete 递归删除；不授权其他路径`。

本次仅重新加载冻结摘要中的同一30个绝对路径，没有新增目标。执行前再次确认：30/30存在；4,338个普通文件、287,147,295 bytes；Git跟踪0；目标及子项reparse point 0；所有解析路径均严格位于`E:\Temp-Projects\PRL`内部。

## 实际执行

在单一PowerShell进程中逐项完成边界检查后，对每个已解析目标调用经用户明确授权的`[System.IO.Directory]::Delete(resolved_target, true)`。未使用通配符、环境变量目标、虚拟盘、跨shell路径传递或其他路径。

## 后验验收

| 检查 | 结果 |
|---|---|
| 精确目标 | 30/30不存在 |
| 删除文件 | 4,338 |
| 删除字节 | 287,147,295（273.845 MiB） |
| Git已跟踪状态漂移 | 0 |
| 保留的`b\z1m0a` | 存在 |
| 当前长程结果 | 存在，114项结果哈希及14项来源哈希通过 |
| SimuCell3D `src/include/LICENSE` | 存在 |
| `data/plan/project_control` | 存在 |
| 科研计算/GPU | not_run |

删除后工作区只读测量为30,075个普通文件、7,848,877,411 bytes（7.310 GiB）。相对Batch 1基线净减少278,491,571 bytes；小于删除原始字节数，是因为Batch 1之后新增了约8.66 MiB的清理清单、逐文件哈希、测试和导航证据。

13项当前接触/几何/折叠及清理分类回归全部通过；驾驶舱严格链接在更新后另行核验。Batch 2裁决`passed`。删除为永久操作：缓存和构建可重建，19个烟测目录中的派生逐步CSV不可恢复；正式结果及历史记录未删除。

本授权已消费，不覆盖Batch 3。Batch 3只能先形成精选证据与精确路径提案，删除前必须重新确认。
