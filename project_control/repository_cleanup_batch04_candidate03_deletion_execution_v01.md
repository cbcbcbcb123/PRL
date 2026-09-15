---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-DELETION-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
deletion_authorized: true
deletion_executed: true
scientific_execution: not_run
---

# Batch 4 候选3退役源码永久删除执行记录 v01

## 结论

用户明确授权的冻结清单已`passed`：8个目录使用`System.IO.Directory.Delete(path, true)`递归删除，30个单文件使用`System.IO.File.Delete(path)`删除。38/38个顶层目标全部消失，实际删除61个普通文件、1,541,224 bytes，剩余目标为0。本次删除不进入回收站，是永久删除；没有处理冻结清单之外的路径。

冻结绝对路径清单为[batch04_candidate03_deletion_targets_v01.txt](evidence/repository_cleanup_v01/batch04_candidate03_deletion_targets_v01.txt)，SHA-256为`2d612a361cbf1f37c1f2c05d07e1a9bac4a3a0b3c506b9b4c57bf06d73a7e6de`。执行前重新核对38个目标、61个文件及逐文件SHA-256；总量、Git状态和reparse point均与提案一致。

## 删除前后核验

| 检查 | 结果 |
|---|---|
| 顶层目标 | 8个递归目录＋30个单文件，38/38匹配冻结清单 |
| 实际内容 | 61个普通文件、1,541,224 bytes |
| Git状态 | 35个`tracked_clean`、26个`untracked`、0个修改 |
| reparse point | 目标及后代0 |
| 精选源码保护 | 32/32保护身份在删除前后逐字节及SHA-256一致 |
| 删除后目标 | 38/38不存在，剩余0 |
| Git范围外变化 | 0 |
| 直接空间变化 | 5,775,305,474 → 5,773,764,250 logical bytes，释放1,541,224 bytes |
| 默认pytest | 19/19 `passed` |
| 显式quick | 19/19 `passed` |
| 默认包发现 | 仅`prl`、`prl.verification` |

机器验收见[JSON](evidence/repository_cleanup_v01/batch04_candidate03_deletion_acceptance.json)，旧路径的证据替代关系见[退役路径映射](repository_cleanup_retired_path_map_v01.md)。16个退役路线源码及包装、369,160 bytes继续保存在`project_control/evidence/retired_routes_v01/source/`；其余45个旧实现没有进入精选证据，不能再声称原路线完整可重跑。Batch 5重建Git基线后不得依赖旧Git历史恢复它们。

## 执行异常与停止边界

第一次命令在PowerShell解析阶段因变量后紧邻冒号而失败；第二次在Git只读预检阶段因反斜杠被解释为无效正则而失败。两次均未进入删除循环，删除数为0。第三次仅修正脚本语法和路径归一化方式，目标、递归范围和删除接口均未改变；随后同一PowerShell进程完成“加载冻结清单—边界/哈希/Git/reparse复核—逐项删除—后验核验”。

## 未改变范围

- 未删除、移动或覆盖任何未授权路径；
- 未更改SimuCell3D、力学方程、材料参数、步长或验证门限；
- 未运行科研求解器、Docker或GPU；
- 未在项目工作区外创建文件或目录；
- 项目仍超过3 GiB硬上限，科研新运行继续`blocked`。

Batch 4仍未整体完成：候选2只建立了无物理C++支撑库，8个应用对带`main`旧`.cpp`的包含式复用尚未迁移。下一步应先冻结候选2应用迁移的精确安全切片；该工作不由本次删除授权自动授权。
