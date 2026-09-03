---
decision_id: DEC-PAPER2-M2A-V04-T128-PATH-REPAIR-RETRY-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-03
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
source_failure_record: project_control/paper2_m2a_v04_t128_execution_failure_record_v01.md
source_failure_result: results/paper2_m2/identity_2d_v04_t128_v01_20260903/
governing_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md
retry_result: results/paper2_m2/identity_2d_v04_t128_v02_20260903/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: minimal_path_normalization_repair_and_full_t128_retry
---

# Paper 2 M2A v04 T128 路径修复与重试决定 v01

## 1. Failure acceptance

Supervisor 接受失败分类 `RUNNER_PATH_NORMALIZATION_ERROR`，并独立复核：

- 失败包 5/5 JSON 可解析，hash ledger 4/4 一致；
- T64 源锁、校准锁和预检均通过；
- T128 端点与 NPZ 数量均为 0；
- v04 两个模块、原 runner 和两个测试的 SHA-256 与失败记录一致；
- 因此该失败不携带 T128 科学结论，也不否定 v03/T64。

## 2. Root cause and minimal repair

根因仅在原 v04 runner 的命令行路径归一化：相对路径被直接传给只接受绝对路径的
`Path.relative_to(PROJECT_ROOT)`。新 runner 必须在任何输出或计算之前：

1. 将所有项目路径参数相对 `PROJECT_ROOT` 解析为绝对规范路径；
2. 对绝对输入保持同一目标；
3. 验证解析后的路径仍位于项目根内，越界则 fail-closed；
4. 后续 provenance 只接收规范化后的绝对路径。

不得修改或覆盖原 v04 runner、v04 模块、测试或失败包。允许新增：

- `scripts/run_paper2_m2_identity_2d_t128_v04_1.py`；
- `tests/paper2_m2/test_t128_v04_1_path_normalization.py`；
- create-only 重试包
  `results/paper2_m2/identity_2d_v04_t128_v02_20260903/`；
- 重试执行记录，并更新 `CURRENT_STATUS.md`。

新 runner 可复制原 runner后做最小路径修复；manifest 必须同时记录原 runner、新 runner、
本决定和 v04 合同的哈希。

## 3. Regression gate

重试前必须证明：

- 失败路径可由定向测试复现；
- 相对与绝对项目内路径得到相同规范目标；
- 项目外路径被拒绝；
- 规范化发生在 output directory 创建和 manifest 写入之前；
- v04 原测试与真实 S4/T128/D0 测试继续通过。

## 4. Retry scope

路径修复门通过后，完整重跑 v04 合同的 54 个 T128 端点、T128 内 74/54/2 门以及 74 个
T64→T128 配对审计。所有方程、校准、D0、功率/闭合/空间阈值、资源预算和结果解释均
完全沿用 v04。

任一门失败立即封口。即使成功也停止在 Supervisor Gate，不运行 T256、时间收敛裁决、
identity gate、M2B、三维、整心房、流体或 GPU。不得 Git 提交或推送。

## 5. Evidence boundary

重试成功只能产生 `T128_STAGE_PASS_V04`。路径修复本身没有科学含义；两个时间层仍不足以
证明时间收敛或 DCM–FEM identity。
