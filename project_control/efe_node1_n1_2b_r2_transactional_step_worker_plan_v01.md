---
plan_id: PLAN-EFE-NODE1-N1-2B-R2-TRANSACTIONAL-STEP-WORKER-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b-r2 事务性 time-step worker 计划 v01

## Goal

把一个完全耦合时间步改造成显式事务边界：新鲜子进程只产生 staging
候选，主进程重新读取输入与候选、独立复核全部门并在通过后独占创建接受
检查点；任何 worker 失败或复核失败都不得改变最后接受状态。

## Inputs

- 周期 3 `accepted_step_003.npz`；
- r1b 六条确定性 Picard 路径及共同终态；
- r1a 冻结单步 Picard kernel；
- 固定 `dolfinx/dolfinx:v0.11.0` 环境和 D0/E0/F150 合同。

## Outputs

1. 通用检查点摘要、候选门复核和独占提交工具及测试；
2. r1a kernel 的显式外层迭代上限/失败注入参数，默认科学行为不变；
3. r2 父进程 pilot：3 次独立 worker 成功事务和 1 次受控失败回滚；
4. 每次 worker PID、输入摘要、候选摘要、主进程 oracle、提交摘要和源码指纹；
5. 派生 JSON、阶段诊断图、执行报告和下一人类终审请求。

## Implementation Steps

1. 新增事务模块：稳定数组摘要、主进程门复核、内存构造 NPZ 后的独占
   `create-only` 提交；目标路径已存在时必须拒绝，不允许覆盖；
2. 为 r1a 单步 kernel 增加 `1..12` 外层上限参数和仅用于负控的禁用回退
   参数；默认仍为 12 次及原回退安排；
3. 为 worker 摘要增加 PID/父 PID 和 gate-critical 源码指纹；
4. 父进程依次启动 3 个新鲜 worker，每个从相同输入加载、运行原 Picard、
   形成 staging candidate；
5. 父进程使用新鲜 FEniCSx oracle 重新计算 KKT、体积、`J`、gap、面面积和
   `Z` 结构门，并检查原始 `r_Z`、输入摘要及 r1b 终态等价性；
6. 只有全部门通过时才独占创建该 replicate 的 `accepted_step_004.npz`；
7. 再以 1 次外层且禁用回退执行受控失败，要求 worker 非零退出、staging
   候选保留、接受检查点不存在且输入摘要不变；
8. 汇总结果和图，提交人类终审，不恢复完整周期。

## Impacted Files Or Modules

- 新增 `src/hybrid/efe_step_transaction.py` 及对应测试；
- 参数化 `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`；
- 新增 r2 父进程 pilot 与阶段绘图脚本；
- `project_control` 中的授权、计划、执行和终审记录。

## Test Plan

- 数组摘要稳定性、形状/非有限输入拒绝；
- 候选门对摘要不匹配、worker 失败、KKT/`r_Z`/几何门失败逐项拒绝；
- 独占提交可读取且二次写同一路径被拒绝；
- 3 个成功 worker PID 不同、输入摘要相同、逐轮与终态逐元素一致；
- 失败负控不产生接受检查点且输入摘要前后不变；
- 相关 pytest、Ruff、JSON/NPZ 读取和 PNG 视觉核验通过。

## Risks

- 子进程隔离会增加启动和首次 JIT 时间，但本阶段优先验证证据边界；
- create-only 提交保证不覆盖既有检查点，但不是跨主机分布式事务协议；
- 失败注入只验证“worker 未通过时不提交”，不能穷尽断电等系统级故障；
- 单步通过不证明后续完整周期稳定。

## Acceptance Criteria

成功事务：

- `n=3` 且 worker PID 各异；
- worker 与主进程 oracle 同时通过 KKT `<=1e-5`、原始
  `r_Z<=1e-4`、`min J>=0.5`、`min gap>=-1e-12` 及既有所有状态门；
- 输入检查点摘要前后相同；
- staging candidate、committed checkpoint 与 r1b 冻结终态逐元素一致；
- committed checkpoint 只在复核通过后出现，且二次提交同一路径会被拒绝。

失败事务：

- 受控 worker 不通过并保留诊断候选；
- 主进程拒绝提交；
- `accepted_step_004.npz` 不存在；
- 输入检查点摘要前后相同。

## Out Of Scope

- 周期 driver 全面迁移或完整周期 3/4 重算；
- 自动重试次数/策略、队列系统或跨主机事务；
- Aitken/Anderson、一致切线、门限调整；
- T32/T64、D1/E1、F200、参数扫描、N1-3、Node 2；
- 论文终稿、实验、Git 与发布。

## Required Memory Updates

只有人类终审接受 r2 后，才能把事务 worker seam 写入稳定架构记忆或用于完整
周期；当前自检不构成独立 Inspector 验收。
