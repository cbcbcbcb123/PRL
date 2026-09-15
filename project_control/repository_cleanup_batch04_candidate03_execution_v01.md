---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
implementation_status: source_retention_matrix_passed
source_copy: not_run
deletion_authorized: false
deletion_executed: false
scientific_execution: not_run
---

# Batch 4 候选3退役源码保留矩阵执行记录 v01

## 结论

用户确认的候选3第一安全切片已完成。对退役Paper2/NCS活动源码范围重新建立36个顶层候选、59个普通文件、1,532,153 bytes的逐文件矩阵；每条记录含规范化相对/绝对路径、字节、SHA-256、Git状态、reparse point、精选证据关系、拟议处置及证据引用。

本次只形成分类和哈希，没有复制、移动或删除任何候选文件。矩阵识别出8个被Batch 3A精选证据直接按路径或哈希引用的文件；当前8/8 SHA-256与证据一致。再加入6个最小Python导入依赖后，下一安全切片需要复制保全14个文件、360,089 bytes。其余45个文件、1,172,064 bytes仅标为`defer_as_later_candidate_not_authorized`，不是删除授权清单。

## 范围复核

| 范围 | 顶层路径 | 文件 | 字节 |
|---|---:|---:|---:|
| 4个退役`src`目录 | 4 | 19 | 347,913 |
| 4个退役测试目录＋2个根测试 | 6 | 14 | 147,703 |
| Paper2/NCS Python脚本 | 26 | 26 | 1,036,537 |
| 合计 | 36 | 59 | 1,532,153 |

该结果与架构审计冻结统计逐项一致。26个脚本是`analyze_paper2_*.py`、`run_paper2_*.py`及`run_ncs_m1_all_fem_v01.py`；两个host PowerShell包装不在本候选范围。Git状态为35个`tracked_clean`、0个`tracked_modified`、24个`untracked`。所有36个顶层路径及其后代均未发现reparse point。

## 下一切片必须复制保全的14个文件

| 当前文件 | 字节 | Git | 关系 | 保留依据 |
|---|---:|---|---|---|
| `scripts/run_ncs_m1_all_fem_v01.py` | 23,111 | `untracked` | 直接证据 | NCS精选summary含路径和SHA-256 |
| `scripts/run_paper2_division_dipole_gate_v01.py` | 35,888 | `tracked_clean` | 直接证据 | 谱系v02/v03精选summary含路径和SHA-256 |
| `scripts/run_paper2_lineage_odd_mode_gate_v01.py` | 59,762 | `untracked` | 直接证据 | 谱系v02/v03精选summary含路径和SHA-256 |
| `scripts/run_paper2_lineage_odd_mode_gate_v02.py` | 68,185 | `untracked` | 直接证据 | v02 runner及v03输入哈希 |
| `scripts/run_paper2_lineage_odd_mode_gate_v03.py` | 6,604 | `untracked` | 直接证据 | v03 approved runner SHA-256 |
| `src/paper2_hybrid/config.py` | 4,555 | `tracked_clean` | 直接证据 | 谱系v02/v03输入哈希 |
| `src/paper2_hybrid/model.py` | 42,954 | `tracked_clean` | 直接证据 | 谱系v02/v03输入哈希 |
| `src/paper2_hybrid/numerics.py` | 17,413 | `tracked_clean` | 直接证据 | 谱系v02/v03输入哈希 |
| `scripts/run_paper2_feedback_kernel_gate_v01.py` | 34,811 | `tracked_clean` | 最小依赖 | 被division-dipole runner直接导入 |
| `src/ncs_m1/__init__.py` | 57 | `untracked` | 最小依赖 | 导入`ncs_m1.baseline`前加载 |
| `src/ncs_m1/baseline.py` | 63,083 | `untracked` | 最小依赖 | 被NCS runner直接导入 |
| `src/paper2_hybrid/__init__.py` | 448 | `tracked_clean` | 最小依赖 | 载入直接证据模块前加载 |
| `src/paper2_hybrid/protocol.py` | 2,342 | `tracked_clean` | 最小依赖 | 被包入口及`numerics.py`导入 |
| `src/paper2_hybrid/roles.py` | 876 | `tracked_clean` | 最小依赖 | 被包入口及`model.py`导入 |

拟议目的地逐文件位于`project_control/evidence/retired_routes_v01/source/<原相对路径>`。该目录尚未创建，本轮没有执行复制。保留这些源码仍不足以保证旧运行完整复现：Dolfinx、Basix、MPI/PETSc、UFL、容器镜像及当时Python环境不会由源码复制自动恢复。

## 证据匹配方法与验收

1. 从[Batch 3A精选证据](evidence/retired_routes_v01/)中同时搜索59个规范化候选路径和当前SHA-256；只有8个文件命中。
2. 从保留的NCS summary、谱系v02失败summary及v03数值summary读取记录哈希；8/8与当前文件一致。
3. 检查直接文件的本地Python导入，增加6个最小依赖；不把整套旧测试或全部Paper2脚本误作必要依赖。
4. 对机器矩阵59条记录独立重算文件数、字节和SHA-256；总量及8/6/45分类一致。
5. 核验全部路径仍位于`E:\Temp-Projects\PRL`内，无reparse point；没有用Git未跟踪状态作为删除理由。
6. 同步权威状态后重新渲染驾驶舱；24个本地链接、190个证据路径严格检查无缺失。稳定入口17项quick回归再次通过，未产生运行缓存。

机器矩阵：[batch04_candidate03_source_matrix.json](evidence/repository_cleanup_v01/batch04_candidate03_source_matrix.json)。完整45文件候选及36个绝对顶层路径均在其中，不在本文重复展开。机器验收见[batch04_candidate03_acceptance.json](evidence/repository_cleanup_v01/batch04_candidate03_acceptance.json)。

首次生成的汇总字节为0，因为PowerShell没有按预期聚合有序字典属性；随后一次中间手工汇总又因目录文件使用反斜杠、映射使用正斜杠而漏计目录内直接/依赖文件。两次均只影响新增矩阵的汇总字段。最终值由59条逐文件记录独立求和得到并通过审计总量校验；旧源码、结果和证据没有改变。

## 未完成与下一门

- 14个必要源码尚未复制到精选证据区，状态为`not_run`。
- 45个其余文件没有删除授权，也尚未形成符合删除安全合同的精确删除提案。
- 默认包发现和默认pytest仍保留旧路线；候选4完整切换尚未执行。
- 本次没有运行旧Paper2/NCS计算、Docker、GPU或科学验证；旧结果的原状态不变。

下一步若获确认，只复制上述冻结的14个文件到项目内精选证据区并逐项验证源/目标哈希，不删除任何活动文件。复制验收后，再单独生成带绝对路径、文件数、字节、Git/reparse及不可恢复影响的删除清单，请用户另行确认。
