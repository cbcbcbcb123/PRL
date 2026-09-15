---
decision_id: DEC-PAPER2-AUTONOMOUS-EXECUTION-CHART-REPORTING-V01
status: approved_by_human_final_reviewer
decider: human_final_reviewer
decided_at: 2026-09-03
supervisor_thread_id: 01a05560-ad09-7393-8587-46725eade6df
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
supersedes: per_step_human_approval_for_bounded_paper2_work
---

# Paper 2 自主执行与图表化汇报决定 v01

## 1. Standing authority

自本决定起，人类终审人授权 Supervisor 在 Paper 2 既定理论主线内自主选择、批准、
下发、验收和衔接边界明确的理论与数值步骤，不再逐项等待人类批准。既有 Human Gate
改为 Supervisor Decision Gate；每次决定仍须留下版本化、可审查的范围、判据与证据
边界，不得把自主授权写成科学结论已经成立。

当前第一个执行步骤仍为已单独批准的 S4 终止型空间诊断：
`project_control/paper2_m2a_s4_terminal_spatial_diagnostic_authorization_decision_v01.md`。

## 2. Autonomous scope

Supervisor 可在以下条件下自主推进：

- 既定 Paper 2 主线中的理想化理论、数值可信度、身份转换、最小状态图、共同极限和
  器官级单向多尺度步骤；
- 为回答当前科学问题所需的最小代码、测试、合同、执行记录、轻量图表和版本化结果；
- 基于硬门结果选择继续、缩小、修订、分叉或停止路线；
- 仅 CPU 的常规测试和受预算约束的模拟；
- 在无上游分叉、测试与证据门通过、暂存范围精确可审查时，对当前工作分支形成阶段
  提交并进行非强制远端同步；
- 对失败进行最小诊断，但不得通过放宽阈值、隐藏失败或覆盖旧证据来制造通过。

## 3. Persistent safeguards

- 所有结果 create-only、版本化；旧合同、旧结果、失败包和 hash 证据保持只读；
- 一次只推进一个边界清楚的阶段，先读状态与上游合同，再执行，再验收，再更新状态；
- 模型方程、参数、观测量、校准/留出划分或硬门若改变，必须新建修订版本并保留旧版，
  同时在汇报中突出说明其科学影响；
- 不得批量暂存工作区；不得把无关修改、原始大数组、缓存或临时文件混入阶段提交；
- 不强制推送；远端 behind/diverged 时停止远端写入并报告；
- 不代表用户投稿、发布、合并到受保护分支或对外宣称论文结论；
- 用户可随时暂停、缩小或撤销本授权。

## 4. Mandatory user-confirmation exceptions

以下两类操作仍受工作区高优先级安全规则约束，必须在执行前询问用户：

1. 删除、覆盖或不可恢复地移动既有文件、目录或证据；
2. 启动 GPU worker。

如遇凭据、不可逆外部发布或无法安全恢复的操作，同样先停止并报告。

## 5. Periodic chart reporting

监督节奏保持每 10 分钟。每轮向用户提供紧凑图表，至少包含：

| 字段 | 内容 |
|---|---|
| 阶段 | 当前里程碑与子步骤 |
| 进度 | 文本进度条与百分比；百分比是阶段执行完成度，不冒充科学成功概率 |
| 状态 | 运行中、通过、失败、诊断或停止 |
| 关键门 | 最新数值、阈值与判定 |
| 资源 | CPU/GPU、耗时、内存或预算状态 |
| 下一步 | Supervisor 已选择的最小后续动作 |

即使状态未变化，也按用户要求给出一行简报；但不得重复下发相同任务或制造虚假进度。

## 6. Reporting and evidence boundary

汇报必须区分：计算完成度、数值门是否通过、模型身份是否成立、实验验证是否存在、
以及目标期刊叙事是否成熟。自主执行不改变以下原则：理想体结果不是生理验证，数值
收敛不是模型真实性，M2A 结果不自动外推到三维、整心房或流体耦合。
