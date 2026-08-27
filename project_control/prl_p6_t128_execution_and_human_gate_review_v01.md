---
inspection_id: INSPECTION-PRL-P6-T128-V01
status: awaiting_t128_human_gate
inspector: human_final_reviewer
prepared_by: codex_current_task
submitted_at: 2026-08-27
related_plan: project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md
authorization: project_control/prl_independent_theory_mainline_decision_v01.md
execution_log: project_control/prl_p6_t128_execution_log_v01.md
stopped_at: t128_human_gate
---

# PRL P6 T128 执行结果与 Human Gate 审阅请求 v01

## 结论先行

P6 P0–P3 已全部执行完成。固定 D0/E0/F150 三层基线的 T64→T128 比较通过
合同内全部时间、周期闭合和安全门。P5 的严格失败记录保持原样；P6 是新增加的
前瞻性证据，不是追溯改判。

可提交人类终审的有界结论为：

> 对当前固定几何、材料、界面、激活和空间离散，主要波形、幅值、积分、耗散、
> 三维场、周期闭合和黏弹记忆峰值相位在 T64→T128 比较下达到 P6 时间离散门。

该结论不证明空间收敛、材料标定、EFE 疾病机制、DCM–FEM 普适优势或 PRL
候选无量纲控制律。

## P0：实现与回归

- 注册 T128，并加入周期圆相位距离、边界/平台峰值状态和物理幅值归一化闭合比；
- 新增 T128 暖启动、事务 wrapper 和入口回归测试；
- 定向测试：`13 passed`；完整 hybrid 回归：`110 passed in 177.22 s`；
- 最终定向复核：`13 passed`；Ruff：通过。

## P1：T64→T128 暖启动

正式结果：`results/hybrid/prl_p6_t128_warm_start_v02_20260827/`。

| 指标 | 结果 | 判定 |
|---|---:|---|
| 相位点 | `65 -> 129` | 符合 |
| 公共相位状态 | bitwise exact | 通过 |
| 冻结周期残差 | `2.06556e-15` | 通过 |
| 候选内部 `Z` 相对差 | `0` | 通过 |
| phase 0 KKT | `8.33425e-7` | `<1e-5` |
| 最小 ECM `J` | `0.999018` | `>0.5` |
| 最小 gap | `0.0391192` | 通过 |
| 用时 | `70.50 s` | 记录 |

DEV001 保留了首次宿主环境误启动的失败目录；它因缺少 `basix` 在内部初始化前
停止，没有产生 T128 动态证据。正式 v02 使用合同指定 CPU FEniCSx 容器，未
改变科学输入或门限。

## P2：两个 T128 事务周期

正式结果：`results/hybrid/prl_p6_t128_transactional_cycle_v01_20260827/`。

| 指标 | 结果 |
|---|---:|
| 正式事务 | `256 / 256` 通过 |
| worker PID | `256` 个且全部唯一 |
| 时间步 | `1/128 = 0.0078125T` |
| cycle 2 最大周期波形差 | `3.94523e-6` |
| 周期末完整 `Z` 差 | `4.92941e-6` |
| 峰值轴向缩短 | `0.116881782` |
| 周期 ECM 耗散 | `2.47125888e-6` |
| 最大 KKT | `1.10797e-7` |
| 最大 coupling residual | `8.34060e-5` |
| 最小 ECM `J` | `0.987735426` |
| 最小 gap | `0.015517647` |
| 总耗时 | `10845.63 s = 3.01 h` |

step 30 以及 step 95–96 在两个周期可重复表现为局部求解敏感区，但均通过原门，
相邻步立即恢复。它们是数值求解路径诊断，不解释为材料或生物学热点。

## P3：T32/T64/T128 裁决

正式结果：`results/hybrid/prl_p6_t128_time_adjudication_v01_20260827/`。

### 全局与场门

| 类别 | T64→T128 控制差 | 门 | 判定 |
|---|---:|---:|---|
| 波形 | ECM 黏弹能 `0.4030%` | `2%` | 通过 |
| 周期积分 | ECM 黏弹能 `0.2969%` | `2%` | 通过 |
| 峰值幅度 | ECM 黏弹能 `0.5151%` | `2%` | 通过 |
| 周期耗散 | `0.0937%` | `5%` | 通过 |
| 适用三维场 | 黏弹能密度 p95 `0.4423%` | `5%` | 通过 |
| 峰值相位 | 两项均 `0.0078125T` | `0.01T` | 通过 |

两个定向峰值相位为：

- ECM 黏弹能：T32/T64/T128 = `0 / 0.984375 / 0.9921875`；
- ECM `||Z||`：`0.71875 / 0.734375 / 0.7421875`。

前者的 T32 峰值仍被标记为周期边界敏感，因此不报告可靠 Richardson 相位极限，
也不把 `0.9921875T` 解释为精确生物学时序。P6 通过只表示 T64→T128 的周期圆
距离满足预登记门。

### 物理周期闭合

闭合比定义为 phase 1 位移 p95 残差除以整周期位移 p95 幅值：

| 层 | T64 闭合比 | T128 闭合比 | 门 | 判定 |
|---|---:|---:|---:|---|
| 心肌 | `6.95e-9` | `1.52e-9` | `1e-3` | 通过 |
| ECM | `2.06e-6` | `4.84e-7` | `1e-3` | 通过 |
| 心内膜 | `1.04e-6` | `1.64e-7` | `1e-3` | 通过 |

三层绝对闭合残差也随 T32→T64→T128 单调下降。旧 P5 的近零量相对差失败没有
被删除或重分类。

## Figure 2 v02

版本包：
`02_图表/Figures/Fig2_n1_2_time_adjudication/`
`Fig2_n1_2_time_adjudication_v02_20260827/`。

- Notebook 执行、自动核验和代理视觉 QA：通过；
- 当前状态：工作版本，等待人类确认；
- PNG SHA-256：`d6ac70c28fc26dc7740ae8ec9145c9b7bb941a82e1e4f11c453631c625c103db`；
- SVG SHA-256：`2f57dcec2b62854451c3b79dfc7dd30a6c4ce175aa57f2e3f58cce84cd5134a0`；
- Figure 2 v01 仍为 FINAL，PNG/SVG 哈希保持
  `afe3940e...0276 / 044f4941...bc9e`，未覆盖。

## 证据指纹

- T128 暖启动 summary：`139fce3d...beee`；
- T128 两周期 summary：`a58d8b0c...def6`；
- P6 裁决 summary：`5a039dde...4e17`；
- P5 历史 summary：`dfe0f48e...d05d`，状态仍为
  `failed_registered_time_convergence_gate`。

## 停止边界与建议

当前已停在 T128 Human Gate。未执行 T256、空间细化、容差扫描、N1-2d、N1-3、
原 EFE Node 2–4、GPU、新求解器或双向 FSI。

建议接受 P6 后，把 T64 作为当前固定基线的常规幅值/场生产级候选；对峰值相位
敏感的验证仍保留 T128。下一步只能起草 PRL Figure 2 的空间与容差合同，不能由
本次通过自动进入计算。

## 待人类终审的准确决定

> 接受 PRL P6 T128 结果与有界结论，确认 Figure 2 v02 为 FINAL；批准起草
> PRL Figure 2 空间与容差验证合同，但暂不执行。仍不授权 T256、空间细化实算、
> 参数扫描、N1-2d、N1-3、原 EFE Node 2–4、GPU、新求解器或双向 FSI。
