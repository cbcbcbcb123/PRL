---
document_id: PRL-REPOSITORY-CLEANUP-BATCH02-EXECUTION-V01
status: blocked_environment
recorded_at: 2026-09-14
authorization: confirmed_exact_thirty_paths
process_started: false
deleted_paths: 0
---

# Batch 2删除执行记录 v01

## 授权与预检

用户准确确认：`确认删除 Batch 2 清单的30个路径`。授权只覆盖[提案](repository_cleanup_batch02_deletion_proposal_v01.md)中的30个绝对路径。

执行前重新从冻结机器摘要加载候选，并逐项验证：

- 30/30存在且解析后的绝对路径位于`E:\Temp-Projects\PRL`内部；
- 4,338个普通文件、287,147,295 bytes；
- Git跟踪文件0，目标或子项reparse point 0；
- 当前活动构建`b\z1m0a`、当前长程结果、SimuCell3D源码/include/LICENSE、data、plan和project_control均存在。

## 执行结果

采用单一PowerShell流程，先重复上述边界检查，再计划逐个以`Remove-Item -LiteralPath <resolved-target> -Recurse -Force`处理，不使用通配符或跨shell路径传递。

工具在PowerShell进程创建前拒绝整个命令，错误类别为`CreateProcess rejected: blocked by policy`。因此没有任何删除指令实际执行，也没有操作到清单之外的路径。按提案第6条，不改用`Directory.Delete`、Python文件接口、Git清理或其他方式绕过。

## 后验核验

| 检查 | 结果 |
|---|---|
| 剩余候选 | 30/30 |
| 剩余普通文件 | 4,338 |
| 剩余字节 | 287,147,295 |
| 实际删除 | 0路径、0 bytes |
| 当前活动构建 | 存在 |
| 当前长程结果 | 存在 |
| SimuCell3D源码/include/LICENSE | 存在 |
| data/plan/project_control | 存在 |
| 科研计算/GPU | not_run |

Batch 2裁决为`blocked_environment`，不是`passed`或部分完成。本次确认已用于该固定尝试；若执行环境允许删除后重试，应重新明确授权同一清单。Batch 3–6保持`not_run`，科研阶段继续暂停。
