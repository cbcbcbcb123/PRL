---
document_id: PRL-REPOSITORY-CLEANUP-BATCH01-INVENTORY-V01
status: passed
recorded_at: 2026-09-14
audit_type: readonly_full_file_hash_inventory
scientific_validation: not_run
---

# Batch 1：完整分类与基线盘点

## 结论

只读遍历 `E:\Temp-Projects\PRL`，不跟随目录 reparse point。共登记 **34,406个普通文件、8,127,368,982 bytes（7.569 GiB）**。每个普通文件记录项目相对路径、字节数、SHA-256及当前分类。盘点程序生成的两个证据文件不把自己纳入清单。

这是本轮开始后的清理基线快照。快照完成后由本任务新增的总合同、两份报告、审计回归测试以及导航更新不反向写入清单，避免清单与自身产生循环哈希；它们属于本任务明确可追踪增量，将在每批执行后的前后差分中单列。

当前主要占用：`.git` 4,464,182,252 bytes（4.158 GiB）；`results` 2,809,119,424 bytes（2.616 GiB）；全部构建树 `b` 228,584,715 bytes。问题主体仍是历史 Git 与结果，不是源码。

权威机器清单：

- [逐文件清单](evidence/repository_cleanup_v01/inventory_manifest.jsonl)，SHA-256 `1e6504248cadf558709fdbedd591fd64d75b8dad06d892b47ff855a2ded2fb30`；
- [结构化摘要](evidence/repository_cleanup_v01/inventory_summary.json)，SHA-256 `f53133e7dc4c3d6177bbc67991c2fc16e4e84ddb96f654093460da8a49583c4d`；
- [可重复审计脚本](../scripts/audit_repository_cleanup_v01.py)。

## 顶层完整分类

| 顶层路径 | 文件 | 字节 | 当前分类 |
|---|---:|---:|---|
| `.git` | 10,095 | 4,464,182,252 | Batch 5建立新基线前保留 |
| `results` | 16,657 | 2,809,119,424 | Batch 3逐包精选，当前不删 |
| `b` | 3,481 | 228,584,715 | 当前树保留，其余列入Batch 2提案 |
| `tmp` | 864 | 192,310,908 | 仅明确烟测/归属目录进入Batch 2；其余待Batch 3 |
| `external` | 1,825 | 176,312,034 | SimuCell3D源码/许可证保留；单个构建树进入Batch 2 |
| `planning` | 312 | 148,975,251 | Batch 3精选内部稿件与预览 |
| `02_图表` | 105 | 46,409,113 | Batch 3逐图包裁决 |
| `artifacts` | 80 | 28,595,494 | Batch 3核对唯一审阅/可重建预览 |
| `figures` | 22 | 18,031,410 | Batch 3核对长期图件及引用 |
| `data` | 108 | 5,088,082 | 原始/输入数据保护 |
| `scripts` | 200 | 4,346,288 | Batch 4先解依赖再删历史入口 |
| `project_control` | 470 | 3,331,248 | 权威决定/合同/证据，保留并另建退役映射 |
| `src` | 34 | 689,564 | Batch 4只维护当前主线，先行为对照 |
| `plan` | 50 | 643,458 | 外部专家材料及哈希，保护 |
| `tests` | 41 | 295,359 | Batch 4按活动主线与安全回归精选 |
| `docs` | 39 | 218,418 | 当前理论/架构保留，旧路线后续索引化 |
| `memory` | 6 | 113,116 | 当前驾驶舱及任务账本保留 |
| `references` | 1 | 98,221 | 来源资料保护 |
| 根级入口与配置 | 9 | 119,602 | AGENTS/START_HERE/README/配置保留 |
| `tools` | 1 | 425 | 待人工判断，未进入删除清单 |
| `imach project_control` | 1 | 0 | 异常零字节文件，待人工判断，未进入删除清单 |

根级入口与配置包括 `AGENTS.md`、`START_HERE.md`、`README.md`、`pyproject.toml`、`.gitignore`、`.gitattributes` 等；机器清单保留逐项记录。

## 分类汇总

| 类别 | 文件 | 字节 | 当前动作 |
|---|---:|---:|---|
| Batch 2候选 | 4,338 | 287,147,295 | 等待用户按精确清单确认 |
| Batch 3证据精选 | 17,176 | 3,051,130,692 | not_run |
| Batch 4解依赖 | 210 | 3,874,330 | not_run；不按版本号直接删 |
| Batch 5新Git基线 | 10,095 | 4,464,182,252 | not_run |
| 活动/治理/原始材料 | 1,290 | 134,329,796 | 保护 |
| 当前活动构建 | 507 | 51,295,019 | 暂时保护 |
| 人工待裁决 | 790 | 135,409,598 | 未知不得删除 |

## 链接、Git及依赖边界

发现78个目录 reparse point，全部在两个旧 Paper2 pytest 临时树中，均已跳过，未遍历其目标；详细路径在摘要。它们不进入Batch 2，以免在未解析前发生越界。

工作树已有大量用户修改与未跟踪科学材料；本轮不把未跟踪状态当删除依据。Batch 2全部候选的 `git ls-files -- <path>` 结果均为0。当前长程双胞运行、验证与绘图使用 `b/z1m0a`，该树未列入候选。当前Python脚本跨版本导入、C++包含旧带入口实现的问题留到Batch 4，先加行为测试并解耦。

## 本批验收

- 完整清单和摘要可解析；
- 全部候选无Git跟踪文件；
- 已跳过目录链接并列明；
- 无删除、移动、压缩、GPU或科学计算；
- 科学项目状态未改变。

因此Batch 1裁决为 `passed`，只代表仓库盘点完整性，不代表任何科研验证。
