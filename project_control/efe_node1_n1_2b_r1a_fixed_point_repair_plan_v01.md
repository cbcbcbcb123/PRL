---
plan_id: PLAN-EFE-NODE1-N1-2B-R1A-FIXED-POINT-REPAIR-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b-r1a 失败步固定点修复计划 v01

## Goal

在不改变模型、时间离散或验收门的前提下，验证受保护的向量 Aitken 松弛能否
使周期 3 step 4 的 `Z`—几何固定点在最多 12 次外层迭代内闭合，并证明
加速只改变求解路径、不改变待求固定点。

## Inputs

- 冻结 Picard 负结果及其 12 次耦合轨迹；
- `cycle_03/accepted_step_003.npz` 合格检查点；
- D0/E0/F150、激活 `0.10`、`dt=1/16`；
- FEniCSx ECM 后端和既有稀疏 Krylov/DF-SANE 受控回退；
- 最大 12 次外层迭代及既有全部状态硬门。

## Outputs

1. 可单元测试的向量 Aitken 权重与对称零迹 `Z` 松弛函数；
2. 单失败步 pilot 入口、逐迭代检查点和根级成功/失败摘要；
3. 冻结 Picard 与 Aitken 的 `r_Z`、KKT、迭代次数和状态诊断对照图；
4. 生产周期 runner 的根级中途失败摘要；
5. 执行报告和人类终审请求。

## Implementation Steps

1. 在周期收敛模块增加向量 Aitken：首轮权重 `1.0`；随后使用残差差分
   计算标量权重并限制在 `[0.1, 1.0]`；
2. 若当前原始残差较上一轮增长，则把新权重进一步限制到上一权重的一半，
   下限仍为 `0.1`；任何非有限或退化分母均回退到有界权重；
3. 松弛后的 `Z` 逐单元投影到对称零迹子空间；
4. 用冻结 step 3 检查点运行一个 Aitken 分支；机械捕获、Krylov、迭代 8/12
   的延长捕获和 DF-SANE 安排保持与 Picard 基线相同；
5. 每轮仍先计算未松弛的解析 SLS 更新；只有该原始 `r_Z`、更新后 KKT 和
   物理门同时通过时才接受，松弛残差不得替代验收残差；
6. 成功或失败均在 pilot 根目录写出摘要；生产 runner 在耦合门失败前也写出
   根级失败摘要；
7. 从冻结 Picard 证据和新结果生成阶段对照图，提交人类终审。

## Impacted Files Or Modules

- `src/hybrid/efe_cycle_convergence.py`；
- `tests/hybrid/test_efe_cycle_convergence.py`；
- 新增 N1-2b-r1a 单步 pilot 与绘图脚本；
- `scripts/run_efe_node1_n1_2_periodic_case_v01.py` 的根级失败摘要路径；
- `project_control` 中的决定、执行与终审记录。

## Test Plan

- 用标量/向量线性收缩映射检查 Aitken 权重公式和界限；
- 检查残差增长保护、退化分母回退及非有限输入拒绝；
- 检查松弛 `Z` 的对称、零迹和端点权重行为；
- 相关 pytest 与 Ruff 通过；
- pilot JSON/NPZ 可读取，逐迭代字段完整；
- 图像非空并人工视觉核查。

## Risks

- Aitken 可能因强非线性或不精确机械子问题仍无法在 12 次内闭合；
- 过强欠松弛可能稳定但变慢，因此权重下限与 12 次上限共同防止无限拖延；
- 通过单失败步只证明局部求解器修复候选，不能证明完整周期稳定；
- Picard 最终候选未通过固定点门，只能作为轨迹对照，不能作为真解。

## Acceptance Criteria

算法级：

- Aitken 权重始终有限且在 `[0.1,1.0]`；
- 所有松弛猜测的 `Z` 对称与零迹残差 `<=1e-12`；
- 最终验收使用未松弛原始映射残差。

pilot 通过候选：

- 在最多 12 次机械子问题调用内同时达到：KKT `<=1e-5`、原始
  `r_Z<=1e-4`、`min J>=0.5`、`min gap>=-1e-12`；
- 体积、面面积、`Z` 对称/零迹和接触硬门保持通过；
- 不使用比 Picard 基线更宽的物理门或更多外层迭代；
- 输出与冻结 Picard 的残差轨迹、迭代数和物理状态量对照。

若未通过，必须保留负结果并停止；不得追加迭代或改门限。

## Out Of Scope

- 完整周期 3/4 重算或周期稳态声明；
- Anderson 深度扫描、单周期 Poincare 求解或一致切线生产化；
- T32/T64、D1/E1、F200、参数矩阵；
- N1-3、Node 2、实验与论文终稿图。

## Required Memory Updates

只有人类终审接受 r1a 后，才可把 Aitken 路线写为后续完整周期的候选求解器；
本任务自检不构成生产化或科学证据接受。
