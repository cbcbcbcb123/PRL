---
document_id: PRL-VENTRICLE-V03-WORKSPACE-CLEANUP-AUDIT-V01
status: passed
recorded_at: 2026-09-11
audit_type: cleanup_classification_and_execution
cleanup_execution_status: passed
cleanup_completed_at: 2026-09-11T09:17:06+08:00
scientific_validation: not_run
---

# v03 重新起步工作区清理审计

## 结论

已找到一组可再生、无 Git 跟踪文件的缓存与历史构建输出，共 14 个绝对路径、6,053 个文件、232,904,726 bytes（222.115 MiB）。这些路径不包含项目原始数据、正式结果、冻结失败包或唯一源码；删除后唯一影响是相关 Python 缓存需自动重建，SimuCell3D 历史二进制需要重新编译。

用户于 2026-09-11 明确回复“确认删除清单 A 的 14 个路径”。14 个路径随后全部删除；删除后逐项确认均不存在，12 个受保护位置仍存在，Git 已跟踪修改与删除前完全一致。清理执行状态为 **PASS**。

## 清单 A：已确认并删除

| 绝对路径 | 文件数 | 字节数 | 判定依据 |
|---|---:|---:|---|
| `E:\Temp-Projects\PRL\.pytest_cache` | 4 | 853 | pytest 缓存，可自动重建 |
| `E:\Temp-Projects\PRL\scripts\__pycache__` | 6 | 258,563 | Python 字节码缓存，可自动重建 |
| `E:\Temp-Projects\PRL\src\paper2_hybrid\__pycache__` | 4 | 13,516 | Python 字节码缓存，可自动重建 |
| `E:\Temp-Projects\PRL\tests\__pycache__` | 2 | 13,656 | Python 字节码缓存，可自动重建 |
| `E:\Temp-Projects\PRL\external\simucell3d\lib\pybind11\.ruff_cache` | 11 | 3,038 | Ruff 缓存，可自动重建 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x0` | 856 | 6,927,036 | 历史构建输出；源码与合同另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x1a` | 10 | 168,168 | 历史构建输出；源码与合同另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x1a-red` | 1,004 | 50,325,440 | 历史构建输出；源码与失败记录另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x1f` | 975 | 47,947,794 | 历史构建输出；源码与报告另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x1g` | 975 | 48,297,873 | 历史构建输出；源码与报告另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-linux-x1h` | 1,026 | 51,783,221 | 历史构建输出；源码与报告另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-x0` | 154 | 11,093,921 | 历史构建输出；源码与报告另存，可重新编译 |
| `E:\Temp-Projects\PRL\external\simucell3d\build-x1k-v04` | 1,026 | 16,071,647 | 历史构建输出；源码与冻结结果另存，可重新编译 |
| `E:\Temp-Projects\PRL\notebooks` | 0 | 0 | 空目录，无内容 |

对以上每个路径执行 `git ls-files` 的跟踪文件计数均为 0。六个 Linux 构建目录中共发现 12 个 WSL/Linux reparse link，均为 `tinyxml2` 的相对链接：`libtinyxml2.so → libtinyxml2.so.8 → libtinyxml2.so.8.0.0`，目标仍在各自候选构建目录内，没有指向工作区外。

执行采用项目根目录中的精确 Git pathspec。首次清理因 Windows 长路径限制留下 5 个构建目录中的 19 个对象/依赖文件；随后使用单次命令参数 `core.longPaths=true` 对这 5 个原清单路径重试，没有写入持久 Git 配置。最终核验结果：14/14 路径不存在；12/12 受保护位置存在；删除前后已跟踪修改均为 `README.md`、`project_control/CURRENT_STATUS.md` 和 `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`，状态未改变。

## 清单 B：当前不得删除

| 路径 | 审计体量 | 原因 |
|---|---:|---|
| `E:\Temp-Projects\PRL\results` | 14,089 文件，1,564.80 MiB | 含正式 PASS、FAIL、NOT_RESOLVED、运行账本和原始数组；新合同明确要求保留失败包 |
| `E:\Temp-Projects\PRL\project_control` | 整理前 340 文件，2.28 MiB | 决定、合同、门禁、执行和冻结证据；路径被大量交叉引用 |
| `E:\Temp-Projects\PRL\planning` | 312 文件，142.07 MiB | 含历史论文/研究材料及版式 QA；不能在未逐件确认来源前当作废稿 |
| `E:\Temp-Projects\PRL\plan` | 15 文件，0.07 MiB | 外部专家指导及来源/哈希记录 |
| `E:\Temp-Projects\PRL\data` | 108 文件，4.85 MiB | 项目数据；不属于可再生缓存 |
| `E:\Temp-Projects\PRL\02_图表` | 105 文件，44.26 MiB | 用户图件、可复算图包及其证据链 |
| `E:\Temp-Projects\PRL\artifacts` | 80 文件，27.27 MiB | 虽为渲染/审阅产物，但尚未逐项证明可再生且不含唯一验收证据 |
| `E:\Temp-Projects\PRL\figures` | 20 文件，17.12 MiB | 长期示意图和历史图形资产，受既有文档引用 |
| `E:\Temp-Projects\PRL\tmp` | 760 文件，3.34 MiB | 多个绝对/相对路径被历史合同和执行记录引用，不能直接视为无用缓存 |
| `E:\Temp-Projects\PRL\external\simucell3d` 中除清单 A 外的内容 | 已跟踪依赖与源码 | 当前仍是历史代码与复算链组成部分；待 Z0 建立与 `muse_dcm` 的依赖映射 |
| `E:\Temp-Projects\PRL\.git` | 4,167.82 MiB | 唯一完整版本历史和恢复路径，不纳入项目内容清理 |

## 清单 C：桌面源包不在本次清理范围

- `C:\Users\chenb\Desktop\PRL_Codex_Stage_Contracts_v03`
- `C:\Users\chenb\Desktop\PRL_Codex_Stage_Contracts_v03.zip`

两者位于项目工作区外，且分别是本次输入原件和压缩副本。本轮不修改、不清理。

## 确认与授权边界

确认原文：`确认删除清单 A 的 14 个路径`

该确认已消费，仅覆盖清单 A。清单 B/C 未删除；该确认不授权运行 Z0、Z1、GPU、Docker 或外部下载。
