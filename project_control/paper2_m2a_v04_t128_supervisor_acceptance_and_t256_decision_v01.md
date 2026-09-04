---
decision_id: DEC-PAPER2-M2A-V04-T128-ACCEPT-T256-V01
status: approved_under_human_standing_authority
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_execution: project_control/paper2_m2a_v04_t128_path_repair_retry_execution_record_v01.md
accepted_result: results/paper2_m2/identity_2d_v04_t128_v02_20260903/
next_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: v05_t256_full_numerical_and_three_level_time_gate_only
---

# Paper 2 M2A v04 T128 验收与 T256 执行决定 v01

## 1. Supervisor acceptance

Supervisor 接受 `T128_STAGE_PASS_V04`。本次独立复核不依赖执行记录中的通过标签，结果为：

| 检查 | 独立复核结果 |
|---|---:|
| 唯一 T128/D0 端点 | 54/54；无缺失、无额外键 |
| 结构门 | 54/54；逐检查失败 0 项 |
| 空间主量门 | 74/74 |
| 周期门 | 54/54 |
| S1 热点门 | 2/2 |
| T64→T128 配对 | 74/74；仅审计，不作收敛结论 |
| 结果 hash ledger | 25/25 SHA-256 与字节数一致 |
| JSON / NPZ | 14 个 JSON 可解析；12 个 NPZ、360 个数组全部有限 |
| 冻结只读输入 | 22/22 当前 SHA-256 与封存值一致 |
| 路径/协议定向测试 | 配置项目 `src` 后 6/6 通过 |

独立重算最坏值与执行记录一致：T128 内 S3→S4 最大相对差
`0.00939778390987877 < 0.01`；功率账本
`3.7028260806074476e-09 < 1e-08`；离散闭合
`2.315226770008592e-14 < 1e-10`；D0 相对残差
`2.9681468104030423e-08 < 1e-07`；normwise backward error
`1.2667253508759522e-15 < 1e-12`。

宿主首次测试因未配置项目 `src` 导入路径而在收集阶段停止；设置项目内导入路径后原样
重跑通过。该事件未进入求解逻辑，不构成科学或数值失败。

本验收只确认冻结二维理想模型的 T128 数值阶段。最大 T64→T128 配对相对差
`0.0016598581580133645` 仍是两层审计值，不能证明时间方向、收敛阶或 DCM–FEM identity。

## 2. T256 authorization

按 `paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md` 执行完整 T256
数值阶段：九工况、两表示、S2/S3/S4、单一 D0，共 54 个端点。

本阶段必须：

- 锁定 v03/v04 的方程、参数、校准、空间梯度、D0 双残差门、功率账本和全部观测量；
- 在 T256 内重新通过 74 个空间主量、54 个周期和 2 个热点门；
- 对 S4/D0 的 74 个预注册主量形成唯一的 T64/T128/T256 三层时间记录；
- 使用冻结 floor 检查时间方向、相邻层变化不反增和 T128→T256 相对差 `<=1%`；
- 保存 12 个 S4/D0 动态留出 NPZ，并验证时间网格嵌套、有限值与 hash；
- 任一硬门、源锁或记录完整性失败立即 fail-closed。

## 3. Stop boundary

即使 T256 与三层时间门全部通过，本决定也不授权跨表示 identity gate、GO-ID/MAYBE-ID/
NO-GO-ID、重新校准、S5、M2B、三维、整心房、真实几何、流体、CFD/FSI、GPU、新求解器
或参数扫描。执行完成后停止在 Supervisor Gate。

不允许修改 v01-v04 合同、实现、测试、失败包或成功包；不允许改变方程、生产 traction、
校准/留出划分、1%/周期/功率/闭合阈值或 D0 求解语义。
