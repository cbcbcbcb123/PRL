---
document_id: NCS-M1A-v01-LEDGER-FAILURE-RECORD-v01
status: failed
recorded_at: 2026-09-10
affected_result: results/ncs_m1_all_fem/v01_20260910/m1a
replacement_target: results/ncs_m1_all_fem/v02_20260910/m1a
---

# NCS-M1a v01 正式包账本失败记录

## 判定

v01 正式包保留，不覆盖。其数值门在原摘要中均返回通过，但正式摘要把 `ZERO` 与 `PATCH` 合并为一个旁路文件，没有纳入 `protocol_results`，因此报告 `protocol_count=15`、`factorizations=15`、`rhs_count=17027`，未与冻结的 17 协议逐项对账。v01 的 `execution_status=passed` 因此被本记录否决；当前执行状态为 **failed**，科学分类 **NOT_EVALUABLE**，不得据 v01 进入 M1b。

## 根因和有界修正

根因是序列化/汇总账本遗漏，不是物理、网格、阈值或求解器错误。修正内容仅为：

1. `ZERO` 与 `PATCH` 分别计作两个协议；
2. `ZERO` 的一次稀疏分解/一次 RHS 纳入总账；
3. `PATCH` 是完全规定仿射位移后的运动学恢复，实际为 0 分解/0 RHS；该实际值与冻结估计 1/1 的差异明示记录；
4. 预算门要求协议数恰为 17，而不是仅检查 `<=17`。

该差异不改变任何物理量或接受阈值。按冻结方案“明确实现 bug 可在开发预算内修复并用新包复验”，使用 create-only `v02_20260910` 复验全部 M1a 协议。v01 原始目录、摘要和数据均不修改。

## v01 现场

- 17 个物理/验证意图均实际覆盖，但原摘要只计 15 个 `protocol_results`；
- 原摘要：15 分解、17027 RHS、协议墙钟 62.7215493001 s、端到端 66.9877641000 s；
- 原数值门返回通过只能作为诊断线索，不是有效阶段 PASS；
- M1b：`blocked`，直到 v02 复验和账本门通过。
