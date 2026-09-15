---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-EXIT-SAFE-SLICE-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
deletion_authorized: false
deletion_executed: false
scientific_execution: not_run
---

# Batch 4 候选3退出前安全切片执行记录 v01

## 结论

用户确认的非删除安全切片已经`passed`。两个谱系奇模态宿主包装共9,071 bytes已复制到项目内精选证据区，源/目标SHA-256为2/2一致且没有覆盖；`pyproject.toml`默认包发现已收敛到`prl*`，默认pytest已收敛到`tests/prl`并禁用cacheprovider；根`README.md`已替换为当前SimuCell3D主线、稳定`python -m prl`命令和证据边界。

原候选4旧身份基线保持原文件和SHA-256不变。新增[当前身份基线](evidence/repository_cleanup_v01/batch04_candidate03_exit_safe_slice_identity.json)，保护当前入口、`src/prl`、`tests/prl`及16个退役路线源码副本，共32项。

## 验收

| 检查 | 结果 |
|---|---|
| 两个宿主包装源/目标哈希 | 2/2 `passed` |
| 默认setuptools包发现 | 仅`prl`、`prl.verification` |
| 默认pytest | 19/19 `passed` |
| 显式`python -m prl test quick` | 19/19 `passed` |
| 当前保护身份 | 32/32 `passed` |
| 候选外Python导入依赖 | 148文件、0依赖、0解析错误 |
| 驾驶舱严格链接 | 25个本地链接、199个证据路径，无缺失 |
| 删除 | `not_run`，未授权 |

第一次包装复制命令实际完成2个复制，但只在最后生成JSON回执时因PowerShell布尔值`false`缺少`$`前缀而退出。没有重复复制或覆盖；随后的只读核验确认源/目标字节和哈希2/2一致。该问题不影响文件内容，但保留在执行记录中。

机器验收见[JSON](evidence/repository_cleanup_v01/batch04_candidate03_exit_safe_slice_acceptance.json)。下一批精确路径已冻结在[删除提案](repository_cleanup_batch04_candidate03_deletion_proposal_v01.md)，但当前没有删除授权。

## 未改变范围

- 未删除、移动或覆盖活动源码；
- 未运行Paper2/NCS计算、科研求解器、Docker或GPU；
- 未修改SimuCell3D、力学方程、参数、阈值或科学状态；
- 未在项目工作区外创建文件或目录。
