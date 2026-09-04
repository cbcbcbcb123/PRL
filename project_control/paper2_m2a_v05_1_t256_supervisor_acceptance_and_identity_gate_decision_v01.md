---
decision_id: DEC-PAPER2-M2A-V05-1-T256-ACCEPT-IDENTITY-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_execution: project_control/paper2_m2a_v05_1_t256_resource_repair_retry_execution_record_v01.md
accepted_result: results/paper2_m2/identity_2d_v05_t256_v02_20260904/
next_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v06_read_only_identity_postprocessing_only
---

# Paper 2 M2A v05.1 T256 Supervisor 验收与 identity gate 决定 v01

## 1. 决定

Supervisor 在人类持续授权范围内接受 v05.1 T256 资源修复重试，确认其正式标签为
`T256_TIME_CONVERGENCE_PASS_V05`，并授权执行 v06 跨表示 identity gate。

v06 只允许对已经冻结的 S4/T256/D0 结果作 CPU 只读后处理；不得重跑任何 DCM/FEM
求解端点，不得修改 v01-v05.1 实现、结果包、共同投影、模型参数或身份阈值。

## 2. 独立验收结果

| 检查项 | 独立复核结果 | 结论 |
|---|---:|---|
| T256/D0 端点 | 54/54 唯一，54/54 结构门通过 | PASS |
| T256 空间门 | 74/74 | PASS |
| T256 周期门 | 54/54 | PASS |
| T256 热点门 | 2/2 | PASS |
| T64/T128/T256 三层时间门 | 74/74，原始值复算无不一致 | PASS |
| T128→T256 时间节点嵌套 | 12/12，最大绝对误差 0 | PASS |
| 最大最细时间差 `r_12` | `0.0004150504093643955 < 0.01` | PASS |
| 最大直接相对残差 | `2.9681468104030423e-08 < 1e-07` | PASS |
| 最大 backward error | `6.799405880186699e-16 < 1e-12` | PASS |
| 最大功率账本残差 | `2.515595272983527e-09 < 1e-08` | PASS |
| 最大离散闭合误差 | `2.520540448406629e-14 < 1e-10` | PASS |
| 单端点 / 阶段 / 内存预算 | `30.6251 s < 60 s`；`735.4341 s < 5400 s`；`1.1175 GiB < 16 GiB` | PASS |
| JSON / NPZ 有限值 | 16/16 JSON；12/12 NPZ、360/360 数组 | PASS |
| 结果包 ledger | 27/27，且非 ledger 文件恰为 27 个 | PASS |
| 冻结输入与实现哈希 | 运行前后无变化 | PASS |
| GPU | 未使用 | PASS |

宿主 v05.1 定向复核为 `6 passed`。首次复核在收集阶段因未设置项目 `src` 导入路径而
停止；补齐路径后通过，因此该次停止不属于模型、实现或证据失败。

## 3. identity gate 授权边界

授权内容：

1. 读取冻结 T64、T128、T256 结果和 S4/T256/D0 动态留出；
2. 按 v06 冻结的共同网格、标量、波形、牵引、相位、能量、增益和热点算子计算；
3. 输出 create-only JSON 结果包、hash ledger 和执行记录；
4. 给出且只给出 `GO-ID`、`MAYBE-ID`、`NO-GO-ID` 或 `BLOCKED`；
5. 在 Supervisor Gate 停止。

资源上限为 CPU 后处理总时间 `600 s`、峰值内存 `8 GiB`。不得启动 GPU worker。

## 4. 明确不授权

本决定不授权 M2B、S5、三维、整心房、真实几何、流体/CFD/FSI、重新标定、参数扫描、
新外部求解器或任何旧路线扩展。即使 v06 得到 `GO-ID`，也只能起草下一阶段决定，不能
自动启动 M2B。

## 5. 证据边界

本验收只证明冻结理想化二维体系的 T256 数值层和三层时间门通过，不证明 DCM 与 FEM
已经等价。跨表示等价性必须由 v06 独立 identity gate 判定；任何结论不得外推为生理
标定、疾病机制、三维或器官级证据。
