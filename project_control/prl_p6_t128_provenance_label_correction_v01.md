---
correction_id: CORRECTION-PRL-P6-T128-PROVENANCE-V01
status: accepted_resolved_label_only_erratum
prepared_by: codex_current_task
date: 2026-08-29
accepted_by: human_final_reviewer
accepted_at: 2026-08-30
affected_execution: EXEC-PRL-P6-T128-V01
---

# PRL P6 T128 溯源标签勘误 v01

## 结论

T128 底层事务引擎摘要中的 `evidence_boundary` 继承了固定文案
`T16 only`。运行参数、相位网格、事务数量、外层正式摘要及 Figure 2 裁决输入均明确
对应 T128，因此这是标签错误，不是时间网格或计算结果错误。

## 证据

- 底层摘要同时记录 `steps_per_cycle=128`、`time_step=0.0078125`、两个周期和
  `256` 个通过事务；
- Figure 2 的 T128 裁决读取外层正式摘要
  `results/hybrid/prl_p6_t128_transactional_cycle_v01_20260827/summary.json`，其
  SHA-256 为 `a58d8b0c...def6`；
- 底层摘要 SHA-256 为 `d48e5841...d4e6`，原文件保持不变；
- 机器可读勘误位于
  `results/hybrid/prl_p6_t128_transactional_cycle_v01_20260827/`
  `provenance_label_correction_v01.json`。

## 修复

通用事务生成器现按实际 `STEPS_PER_CYCLE` 写入 T 标签，并新增静态回归检查。
不重跑计算，不更改任何已有状态、指标、场数据、裁决输入或 Figure 2 数值。

## 治理边界

本勘误只修复溯源文字。Figure 2 v02 仍等待 T128 Human Gate；本记录不授权空间
细化、容差扫描、T256、N1-2d、N1-3、GPU、新求解器或双向 FSI。

人类终审于 2026-08-30 接受本加性勘误及“不回写原始证据”的处理。Figure 2
v02 随 T128 Human Gate 被接受为时间离散阶段 FINAL；其余禁止范围不变。
