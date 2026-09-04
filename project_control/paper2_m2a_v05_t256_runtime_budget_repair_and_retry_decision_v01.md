---
decision_id: DEC-PAPER2-M2A-V05-T256-RUNTIME-REPAIR-RETRY-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
source_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md
accepted_failure_execution: project_control/paper2_m2a_v05_t256_execution_record_v01.md
accepted_failure_result: results/paper2_m2/identity_2d_v05_t256_v01_20260904/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v05_1_endpoint_runtime_gate_repair_and_full_t256_retry_only
---

# Paper 2 M2A v05 T256 单端点资源门修复与重试决定 v01

## 1. Failure acceptance

Supervisor 接受 `T256_ENDPOINT_RUNTIME_BUDGET_EXCEEDED` 为完整、合规的 fail-closed 失败，
而不是 T256 数值或科学失败。独立复核结果：

| 检查 | 独立复核结果 |
|---|---:|
| 部分端点 | 18/18 均为唯一 `T256/D0` 键 |
| 科学结构门 | 18/18；逐检查失败 0 项 |
| 失败端点耗时 | `30.38510538799892 s > 30.0 s` |
| 失败时阶段资源 | `148.8072/5400 s`；`1.1218/16 GiB`；无 GPU |
| 失败包 JSON | 12/12 严格解析且全部数值有限 |
| 失败包 hash ledger | 11/11 SHA-256 与字节数一致 |
| 冻结只读输入 | 80/80 当前 SHA-256 与运行前值一致 |
| v05 实现与测试 | 5/5 当前 SHA-256 与 manifest 一致 |
| 独立宿主回归 | 配置项目 `src` 后 10/10 通过 |

失败端点的 D0 相对残差 `3.122497222609623e-11 < 1e-7`、后向误差
`2.4755197436675512e-17 < 1e-12`、功率 residual
`1.1990711241050467e-11 < 1e-8`、离散闭合
`2.743376042460784e-15 < 1e-10`。第 19 个端点、T256 汇总门、动态 NPZ、三层时间门和
identity 均未运行。

精确暂存检查发现五个 v05 Python 新文件各带一个 EOF 空行，`git diff --cached --check`
只报告这五项格式警告。去除空行会改变失败 manifest 已封存的实现哈希，因此文件已恢复为
manifest 的 byte-exact 状态并保留该非功能性警告；v05.1 新文件不得重复此格式问题。

## 2. Resource diagnosis

原 `30 s` 单端点上限来自 M2A 初始预检。该预检以最细端点约 `1 s` 估算整个
T64/T128/T256 矩阵，并给出 30 倍安全包络；它不是力学、误差或身份判据。

实际 T128 的 54 个端点中有 14 个超过 `25 s`，最慢为 `27.3281 s`，说明 30 秒门在进入
T256 前已只剩约 9.8% 余量。T256 前 18 个端点的耗时范围为
`0.3346-30.3851 s`；A1 的两个 S4 端点为 `29.1320/30.3851 s`，对应 T128 比值约
`1.10/1.11`。只有一个端点越线，而总时间与内存分别仅使用批准上限的约 2.76% 和 7.01%。

因此当前阻塞是未随 `T128→T256` 时间步数翻倍而调整的工程资源包络，加上近门运行抖动；
没有证据支持修改模型、求解器、网格、观测量或科学阈值。

## 3. Approved v05.1 repair

建立资源版 v05.1，仅把 T256 单端点运行上限预注册为 `60.0 s`。该值由 T128→T256 的
时间步数精确翻倍得到，不按已观测的 `30.3851 s` 贴线调参。以下门保持不变：

- 阶段总时间 `5400 s`；
- 峰值内存 `16 GiB`；
- CPU 单进程、BLAS/OMP 单线程、固定 DOLFINx 容器、禁网、无 GPU；
- 54 个端点、D0 双残差、功率、闭合、空间、周期、热点与 74 个三层时间门；
- 方程、参数、校准/留出、生产观测量、绝对 floor 和所有科学阈值。

不修改 v05 协议、identity、runner、测试或失败包。允许新增：

- `src/paper2_m2/protocol_v05_1.py`；
- `scripts/run_paper2_m2_identity_2d_t256_v05_1.py`；
- `tests/paper2_m2/test_protocol_v05_1.py`；
- `tests/paper2_m2/test_t256_v05_1_resource_gate.py`；
- create-only 重试结果 `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`；
- `project_control/paper2_m2a_v05_1_t256_resource_repair_retry_execution_record_v01.md`；
- 按决定更新 `project_control/CURRENT_STATUS.md`。

v05.1 必须复用只读的 `identity_2d_v05.py` 与 v05 三层时间门；新 runner 只把端点资源门
改为协议内的 `60.0 s`，并显式记录 v05 与 v05.1 的实现 hash。所有路径仍须在创建输出前
规范化并拒绝项目外路径。

## 4. Retry and tests

重试必须从第 1 个端点开始完整运行 54 个端点，不得续接失败目录或混合两次运行的端点。
测试至少证明：

- v05.1 相对 v05 唯一合同差异是 T256 单端点资源上限 `30→60 s` 与版本标识；
- 已观测 `30.38510538799892 s` 在旧门失败、在新门通过；`>60 s` 仍 fail-closed；
- 总时间、内存、CPU/GPU、科学门和三层时间算法未改变；
- v05 原失败可重放，v03-v05 回归不退化；
- 新结果目录 create-only，v05 失败包和全部冻结输入运行前后哈希不变。

若重试触发任一 60 秒单端点门、5400 秒总门、16 GiB 内存门、科学门、源锁或三层时间门，
立即封存新失败包并停止，不再次调整资源门。

## 5. Formal label and stop boundary

因为科学合同未变，只有完整通过时才可沿用 v05 的
`T256_TIME_CONVERGENCE_PASS_V05`；执行记录必须同时注明使用 v05.1 资源修复。该标签仍不
等于 DCM–FEM identity。

本决定不授权 identity gate、GO-ID/MAYBE-ID/NO-GO-ID、重新校准、S5、M2B、三维、
整心房、真实几何、流体/CFD/FSI、GPU、新求解器或参数扫描。完成后停止在 Supervisor
Gate。
