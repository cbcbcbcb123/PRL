---
decision_id: DEC-PAPER2-M2A-V06-T64-TEST-EOF-HASH-V06-1-RETRY-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
blocked_execution: project_control/paper2_m2a_v06_identity_gate_execution_record_v01.md
blocked_result: results/paper2_m2/identity_gate_v06_v01_20260904/
scientific_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md
retry_result: results/paper2_m2/identity_gate_v06_v02_20260904/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v06_1_exact_test_eof_compatibility_then_identity_postprocessing_only
---

# Paper 2 M2A v06 T64 测试 EOF 哈希诊断与 v06.1 重试决定 v01

## 1. Supervisor 结论

接受 v06 的 `BLOCKED` 及 create-only 失败包。独立复核进一步证明，唯一哈希冲突来自
`tests/paper2_m2/test_protocol_v03.py` 末尾少了一个空行，不是 Python 语义、测试断言、
生产实现或 T64 结果数据变化。

因此批准 v06.1 只修订源锁兼容政策，并在新 create-only 目录重新执行同一 v06 只读
identity 后处理。科学合同、模型、数据、共同投影、观测量、阈值和分类逻辑全部不变。

## 2. 可复现的字节级诊断

| 项目 | 值 |
|---|---|
| T64 manifest 期望 SHA-256 | `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f` |
| 当前文件 SHA-256 | `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5` |
| 当前文件字节数 | `1681` |
| 当前文件末尾 | 一个 LF，文件内容无工作树修改 |
| 诊断变换 | 仅在当前字节流末尾追加一个 `0x0A` |
| 变换后字节数 | `1682` |
| 变换后 SHA-256 | `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f` |

变换后哈希与 T64 manifest 逐字符一致。历史创建记录也显示该测试最初以两个末尾 LF
结束；当前提交版本只保留一个末尾 LF。该差异不改变任何 Python token、测试函数、断言
或执行行为。

补充交叉证据：

- 当前文件无 tracked 工作树差异；
- T128 成功包 manifest 封存当前哈希 `502a5c...`，且其完整源锁与数值门通过；
- T256 成功包 manifest 同样封存当前哈希 `502a5c...`，且 74/74 三层时间门通过；
- T64 其余 5 个实现/测试哈希全部匹配；
- T64 包 23/23 ledger、54/54 端点、54/54 结构门、74/54/2 数值门和 12 个动态留出均通过；
- v06 定向测试 18/18、相关轻量回归 37/37 通过。

## 3. v06.1 唯一允许的兼容规则

v06.1 只有在以下条件全部成立时，才可把该单一冲突标为
`ACCEPTED_TEST_EOF_FORMATTING_DELTA`：

1. 来源标签恰为 `T64`；
2. 路径恰为 `tests/paper2_m2/test_protocol_v03.py`；
3. T64 期望哈希恰为 `4eb28d7c...`，当前哈希恰为 `502a5c92...`；
4. 当前字节流只追加一个 LF 后，字节数为 1682 且哈希恰为 `4eb28d7c...`；
5. 当前文件无 tracked 工作树修改；
6. T128 与 T256 manifest 均逐值封存当前 `502a5c92...`；
7. 除该单一测试 EOF 差异外，T64/T128/T256 的文件集、ledger、生产实现、结果、结构门、
   数值门、解析与有限值检查全部通过；
8. v06/v06.1 定向及相关回归测试全部通过。

任一条件不满足即 `BLOCKED`。不得对其他路径、哈希差异、空白变换或内容变化使用该规则。
不得修改当前测试文件去迎合任一旧 manifest。

## 4. 重试实施边界

优先新增：

- `src/paper2_m2/protocol_v06_1.py`；
- `scripts/run_paper2_m2_identity_gate_v06_1.py`；
- `tests/paper2_m2/test_v06_1_source_lock.py`；
- `project_control/paper2_m2a_v06_1_identity_gate_retry_execution_record_v01.md`；
- create-only 结果 `results/paper2_m2/identity_gate_v06_v02_20260904/`。

冻结只读：v06 合同、v06 实现/测试、v06 失败包、T64/T128/T256 源包及 v01-v05.1
全部实现。v06.1 可以复用 v06 的 identity 算子，但不得修改它们。

正式重试仍须：

- 只读取 S4/T256/D0；
- 使用六个正式留出，校准工况 audit-only；
- 两条界面牵引分别按 64 个共同分段计门；
- 精确复用 v01 `combined_load_gain`；
- 输出完整数值变化包络但不从 identity 差异中扣除；
- 给出 `GO-ID`、`MAYBE-ID`、`NO-GO-ID` 或 `BLOCKED` 后停止。

## 5. 资源与停止条件

CPU-only，总时间 `<=600 s`，峰值内存 `<=8 GiB`；不得使用 GPU、网络、新求解器或
重跑任何端点。v06 v01 失败包不得删除、覆盖或续接；v02 路径若已存在则 fail-closed。

完成后停止在 Supervisor Gate。不授权 M2B、S5、三维、整心房、真实几何、流体/CFD/FSI、
重新标定、参数扫描或修改身份阈值。

## 6. 证据边界

本决定只将一个已被字节级证明的测试文件 EOF 空行差异从“未知实现漂移”降级为“已解释
的非语义格式差异”。它不豁免生产代码哈希，不改变 T64/T128/T256 数值结论，也不预判
DCM–FEM identity 的方向或结果。
