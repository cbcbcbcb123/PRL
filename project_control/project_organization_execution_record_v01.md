---
record_id: PRL-PROJECT-ORGANIZATION-EXECUTION-V01
status: completed
recorded_at: 2026-09-09
completed_at: 2026-09-09
scope: project entrypoints, external expert plan library, and directory responsibility records
mode: direct_plus_check
---

# 项目整理执行记录 v01

## 授权

用户于 2026-09-09 确认直接完成此前提出的全部项目整理方案。实施限于项目内部的目录、索引、规则和治理记录；不扩大到科学计算、外部发布、GPU、删除或清理。

## 实施内容

- 建立 `plan/` 外部专家指导库及其生命周期；
- 登记现有外部科学评审约束和来源缺口；
- 建立 `AGENTS.md` 与 `START_HERE.md` 接手入口；
- 明确内部规划、项目控制、图件、渲染产物和临时目录职责；
- 保留现有路径，不对脏工作区进行批量迁移。

## 实际验收结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 必需入口及关联目标 | `passed` | 17/17 路径存在 |
| `plan/` 结构 | `passed` | 共 8 个文件，均为索引、规则、元数据、指导摘要、来源说明或哈希 |
| 来源缺口标记 | `passed` | 专家身份和原始来源均明确为 `unknown` / `missing_from_current_workspace` |
| 派生约束完整性 | `passed` | 当前 SHA-256 与登记值 `879B621122A988E4B70C1991897997B031C8411CB47FC79B0E0D8CF8C62C99EF` 一致 |
| YAML 可读性 | `passed` | `metadata.yaml` 成功解析，方案 ID 一致 |
| 实际导航目标 | `passed` | 根入口、当前状态、主线、约束、采纳记录和目录审计目标均存在 |
| 文本差异格式 | `passed` | `git diff --check` 无错误 |
| Git 范围 | `passed` | 本轮仅新增治理 Markdown/YAML/哈希文件并修改根 `README.md` |
| 科研代码、数据、结果内容 | `passed` | 本轮未修改、移动、覆盖或删除 |
| 科学和数值再验证 | `not_run` | 不属于本次目录整理范围 |

## 实际偏差

首次验收命令因 PowerShell 将 Markdown 反引号解释为 Unicode 转义而解析失败；该命令没有写入文件。改用单引号正则后复检通过。

随后通用引用扫描把标准方案包中的示例字段 `source/` 和 `guidance.md` 当作根目录导航路径；二者实际是“每个方案包内部”的结构说明，不是缺失链接。最终按实际导航目标复检通过。上述检查偏差均未修改科研文件，不影响整理产物。
