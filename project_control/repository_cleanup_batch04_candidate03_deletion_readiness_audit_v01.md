---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE03-DELETION-READINESS-AUDIT-V01
status: blocked
recorded_at: 2026-09-15
deletion_authorized: false
deletion_executed: false
scientific_execution: not_run
---

# Batch 4 候选3删除前依赖资格审计 v01

## 结论

候选3精选源码复制已经`passed`，但活动Paper2/NCS代码尚不具备安全删除资格。原36个候选路径、59文件、1,532,153 bytes不是完整退出闭包：两个未纳入矩阵的PowerShell宿主包装仍调用其中的v02/v03 runner；`pyproject.toml`仍把三个Paper2包列为默认发现对象；根`README.md`仍把退役Hybrid路线和历史命令写成活动用法。

因此本审计状态为`blocked`，没有生成删除授权清单，也没有删除任何文件。

## 已通过的依赖边界

- 14个必要源码、360,089 bytes已复制到项目内精选证据区，源/目标哈希14/14一致。
- 对`scripts/`、`src/`、`tests/`中候选范围外的148个Python文件做AST导入扫描，0个文件导入59个候选文件或四个退役包，0个解析错误。
- 当前稳定`prl`快速门仍不依赖候选源码。

## 阻断项

| 路径/配置 | 当前事实 | 删除风险 |
|---|---|---|
| `scripts/run_paper2_lineage_odd_mode_gate_v02_host.ps1` | 4,500 bytes，SHA-256 `4a4483...0dae`，untracked，无reparse | 仍调用待退役v02 runner；直接删runner会留下断裂包装 |
| `scripts/run_paper2_lineage_odd_mode_gate_v03_host.ps1` | 4,571 bytes，SHA-256 `35a45a...66ba`，untracked，无reparse | 仍调用待退役v03 runner；直接删runner会留下断裂包装 |
| `pyproject.toml` | 默认发现`paper2_figure2`、`paper2_hybrid`、`paper2_m1`及`prl` | 删除包后项目元数据仍错误宣称包含退役包 |
| `README.md` | 仍展示旧Hybrid/Route H结构和运行命令 | 新基线入口与实际主线继续冲突 |

两个包装共9,071 bytes，均被现有`project_control`合同或阶段记录引用，但尚未复制到精选证据区。机器审计见[JSON](evidence/repository_cleanup_v01/batch04_candidate03_deletion_readiness_audit.json)。

## 下一安全切片

下一切片应一次完成以下非删除工作：

1. 将两个宿主包装复制到`project_control/evidence/retired_routes_v01/source/scripts/`并逐项核验哈希，禁止覆盖；
2. 将`pyproject.toml`默认包发现收敛为当前`prl*`，默认pytest收敛到`tests/prl`；
3. 将根`README.md`改为当前SimuCell3D主线、`START_HERE.md`和稳定`python -m prl`入口，历史路线只保留证据索引；
4. 验证默认包发现、默认pytest、显式quick、保护源码哈希及驾驶舱链接。

该切片不包含删除。只有其通过后，才可重新盘点原36路径加两个包装形成38个顶层路径、61文件、1,541,224 bytes的精确删除提案；该统计目前不是删除清单，也没有授权。
