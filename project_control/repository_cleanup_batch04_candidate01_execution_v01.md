---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE01-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
implementation_status: passed
storage_gate: blocked
scientific_execution: not_run
deletion_executed: false
---

# Batch 4 候选1安全切片执行记录 v01

## 结论

用户明确确认的候选1安全切片已完成。项目新增稳定的 `src/prl/` Python 包、三组公共接口测试，并更新 `pyproject.toml` 的包发现和安装后命令入口。两个只读命令均已真实调用：长程双胞独立标量账本核验为 `passed`；存储门正确报告当前仓库超过3 GiB硬上限，准入为 `blocked`。

本次 `passed` 只表示安全切片的工程接口和限定范围核验通过。没有运行科研求解器，长程双胞静态平衡仍为 `failed`，父Z1和生物学验证仍为 `blocked`。

## 实际变更

- 新增 `src/prl/`：工作区定位、存储盘点/准入、CLI和独立长程双胞验证。
- 新增 `tests/prl/`：存储策略、长程证据状态和CLI/依赖边界三组测试，共8项。
- 修改 `pyproject.toml`：发现 `prl*`，并登记安装后 `prl` 命令。
- 新增本执行记录及[机器验收记录](evidence/repository_cleanup_v01/batch04_candidate01_acceptance.json)。

没有修改任何冻结旧脚本、C++力学实现、材料参数、门限或保留结果。没有删除、移动、覆盖历史文件，也没有启动GPU、Docker、安装或外部服务。

## 稳定入口

当前仓库采用 `src` 布局。本轮遵守“项目外不得写入”规则，未向全局Python环境执行安装；因此源码检出态的实际核验先设置只对当前PowerShell进程有效的路径：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -X utf8 -m prl storage status
python -B -X utf8 -m prl verify long-doublet
```

项目以后安装后可直接使用相同的 `python -m prl ...` 或 `prl ...` 入口。安装本身不属于本轮授权，也未执行。

## 验收结果

| 验收项 | 状态 | 结果 |
|---|---|---|
| `storage status` | `passed`（接口）/ `blocked`（准入） | 无扫描错误；跳过78个reparse points；当前5,773,467,044 bytes，大于3,221,225,472 bytes硬上限；默认256 MiB任务不可启动 |
| `verify long-doublet` | `passed` | 13/13来源哈希一致；4/4运行矩阵完整；逐工况状态、间距、网格监测标量、功残差、末态残力和逐细胞形变与冻结裁决一致 |
| 科学状态保护 | `passed` | 数值资格`passed`，静态平衡`failed`，父Z1/生物验证`blocked`，16胞动力学`not_run` |
| 公共接口测试 | `passed` | 8 passed；连续两次验证报告一致；`prl`和`prl.verification`包发现通过 |
| 依赖边界 | `passed` | 新包不导入`run_*`历史脚本或Codex skill；没有运行器与验证器共享力学裁决 |
| 无输出污染 | `passed` | `.pytest_cache`及新包/新测试`__pycache__`均不存在 |
| 删除 | `not_run` | 没有删除授权，也没有调用删除接口 |

`verify long-doublet`没有重新计算节点级步长位移范数、节点/三角形交叉谓词或所有可能的incident-vertex折叠构型；命令在机器报告中明确列为`not_recomputed`。因此它是冻结证据的独立来源身份和标量账本复核，不替代原始完整几何验证器，更不构成新的科学结论。

## 回退点与下一门

旧入口和旧结果仍在原位，回退不需要恢复数据。候选2尚为`not_run`；建议下一步先冻结候选2的无物理C++支撑库安全切片及数值等价验收，再决定是否实施。任何源码删除仍需新的精确路径清单和用户确认。
