---
record_id: PRL-REPOSITORY-DIRECTORY-RESPONSIBILITY-AUDIT-V01
status: completed
recorded_at: 2026-09-09
audit_type: readonly_inventory_and_non_destructive_organization
scientific_validation: not_run
---

# PRL 仓库目录职责审计 v01

## 结论

采用“新增入口与职责文件、保留历史路径”的整理方式。当前工作区存在大量未跟踪结果、既有修改和跨文档引用；批量移动旧文件会增加来源断裂和误纳入风险，因此本轮不移动、覆盖或删除历史材料。目录整理通过规则、索引和前向约定完成。

## 整理前只读盘点

下表是 2026-09-09 建立规则文件之前的快照：

| 目录 | 文件数 | 总字节数 | 主要内容 | 裁定 |
|---|---:|---:|---|---|
| `planning/` | 310 | 148,965,824 | DOCX/PDF、图像和版式 QA | 内部论文框架及投稿路线；保留原路径 |
| `project_control/` | 317 | 2,295,144 | 307 个 Markdown 及少量 JSON/TXT/CSV | 决定、合同、执行和冻结证据；保留原路径 |
| `figures/` | 19 | 17,947,921 | 理论图、示意图和历史 mockup | 长期图形资产；不作为新定量图包默认入口 |
| `02_图表/` | 104 | 46,408,663 | 脚本、CSV、JSON、Markdown 和图像 | 可复算论文图版本包入口 |
| `artifacts/` | 79 | 28,595,085 | PNG 与 PDF 渲染/审阅产物 | 展示和 QA 产物；非默认科学证据 |
| `tmp/` | 759 | 3,506,897 | JSON、缓存和中间文件 | 既有临时材料；非本轮所有，不清理 |

## 外部专家材料审计

文件名和受控记录检索发现 `project_control/external_scientific_review_constraints_v01.md`，但未发现可确认与其对应的外部专家原始邮件、PDF、DOCX 或签署纪要。`planning/` 下的三个子目录内容表现为内部论文框架、投稿路线及其渲染 QA，不迁入 `plan/`。

因此建立 `EXP-20260802-scientific-review-v01` 包并标记为 `active_constraint_only`。该包只链接并摘要现有派生约束，不声称恢复了专家原文。

## 图件目录裁定

- `02_图表/Figures/`：新建可复算论文定量图版本包的规范位置；
- `figures/`：保留理论示意图、历史 mockup 和被既有文档引用的资产；
- `artifacts/`：保留渲染、视觉检查和阶段交付预览；
- 三者当前内容不做物理合并，以避免破坏引用或错误改变证据等级；
- 新文件按职责进入唯一目录，逐步消除未来重叠。

## 已实施控制

1. 新建根目录 `AGENTS.md` 和 `START_HERE.md`；
2. 新建专用 `plan/` 生命周期、索引及首个历史专家指导包；
3. 新建外部指导采纳矩阵，明确原件与身份缺口；
4. 为 `planning/`、`project_control/`、`figures/`、`02_图表/`、`artifacts/` 和 `tmp/` 建立职责说明；
5. 更新根 `README.md` 的入口与目录定义；
6. 保留全部既有材料、Git 状态和历史路径。

## 未改变事项

- 科研代码、测试、数据、计算结果和图版本包内容未修改；
- 没有运行求解器、Docker、GPU 或高成本任务；
- 没有安装软件、访问外部服务、提交、推送或发布；
- 没有删除、清理、覆盖或批量移动文件；
- 没有把本次组织验收升级为科学、数值或发布验收。
