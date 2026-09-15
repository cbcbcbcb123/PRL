---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-SOURCE-COPY-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
implementation_status: selected_source_copy_passed
deletion_authorized: false
deletion_executed: false
scientific_execution: not_run
---

# Batch 4 候选3精选源码复制执行记录 v01

## 结论

依用户对候选3源码复制切片的确认，已将[来源矩阵](evidence/repository_cleanup_v01/batch04_candidate03_source_matrix.json)冻结的14个必要文件、360,089 bytes逐文件复制到`project_control/evidence/retired_routes_v01/source/`。其中8个文件被Batch 3A精选证据直接按路径或哈希引用，6个文件是解释这些来源所需的最小Python导入依赖。

复制使用`System.IO.File.Copy`且`overwrite=false`；执行前14个目标均不存在。复制后源文件与目标文件SHA-256为14/14一致、字节为14/14一致，未发现reparse point。活动源码仍全部保留，本次没有删除、移动或覆盖任何文件。

同步导航后，驾驶舱24个本地链接和192个证据路径严格检查无缺失；稳定入口17项quick回归通过。检查过程未产生`__pycache__`或`.pytest_cache`。

## 复制范围

| 分类 | 文件 | 字节 | 结果 |
|---|---:|---:|---|
| 精选证据直接引用 | 8 | 258,472 | 源/目标哈希8/8一致 |
| 最小导入依赖 | 6 | 101,617 | 源/目标哈希6/6一致 |
| 合计 | 14 | 360,089 | `passed` |

完整逐文件路径、字节、哈希和关系见[复制清单](evidence/repository_cleanup_v01/batch04_candidate03_source_copy_manifest.json)，机器验收见[复制验收](evidence/repository_cleanup_v01/batch04_candidate03_source_copy_acceptance.json)。原[矩阵验收](evidence/repository_cleanup_v01/batch04_candidate03_acceptance.json)保持为复制前来源分类记录，不回写历史状态。

## 边界与未完成

- 复制不会恢复Dolfinx、Basix、MPI/PETSc、UFL、容器镜像或当时Python环境，因此不声明旧路线完整可重跑。
- 其余45个文件、1,172,064 bytes仍只是后置候选，不是删除清单，也没有删除授权。
- 默认`pyproject.toml`、默认pytest、根README和现有应用没有切换。
- 未运行Paper2/NCS计算、科研求解器、Docker或GPU，未修改力学方程、阈值或科学状态。

下一步只应生成候选3的独立精确删除提案，逐项给出规范化绝对路径、文件数、字节、Git/reparse状态、保留依据和不可恢复影响；在用户明确确认前不得删除任何活动源码。
