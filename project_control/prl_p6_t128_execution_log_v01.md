---
execution_id: EXEC-PRL-P6-T128-V01
plan_id: PLAN-EFE-NODE1-N1-2C-P6-T128-V01
executor: codex_current_task
started_at: 2026-08-27
completed_at: 2026-08-27
status: completed_with_deviation
deviation_records:
  - project_control/prl_p6_t128_deviation_dev001_v01.md
authorization: project_control/prl_independent_theory_mainline_decision_v01.md
---

# PRL P6 T128 定向验证执行记录 v01

## 授权与证据边界

本执行只覆盖 P6 P0–P3：T128 入口与测试、T64→T128 暖启动、两个 T128 CPU
事务周期、T32/T64/T128 裁决和 Figure 2 v02。旧 Figure 2 v01 保持 FINAL。

当前论文语境为 PRL 独立理论主线。结果只用于固定 D0/E0/F150 三层基线的时间
离散验证，不解释为 EFE 疾病机制、空间收敛、材料标定或 DCM–FEM 普适优势。

## 阶段状态

- P0：完成；
- P1：完成；
- P2：完成；
- P3：完成，等待 T128 Human Gate；
- 停止点：T128 Human Gate。

## 命令、变更、测试与输出

P0 完成内容：

- `src/hybrid/efe_time_refinement.py` 注册 T128，并加入周期圆相位距离、边界/平台
  峰值状态、整周期幅值归一化闭合比和两周期事务计数；
- 新增 `scripts/prepare_prl_p6_t128_warm_start_v01.py`；
- 新增 `scripts/run_prl_p6_t128_transactional_cycle_v01.py`；
- 新增 `tests/hybrid/test_prl_p6_t128_entry.py` 并扩展时间细化测试；
- 定向测试：`13 passed`；
- 完整 hybrid 回归：`110 passed in 177.22s`；
- Ruff：通过。

P1 正式结果：

- 失败 v01：宿主缺少 `basix`，未进入求解，见 DEV001；
- 正式 v02：CPU 镜像 `dolfinx/dolfinx:v0.11.0` 内完成；
- T64→T128：`65 -> 129` 相位，五组状态在全部公共相位 bitwise exact；
- 冻结周期残差 `2.06556e-15`，候选内部 `Z` 相对差 `0`；
- phase 0 KKT `8.33425e-7`，体积残差 `6.66134e-16`；
- 最小 ECM `J=0.999018`，最小 gap `0.0391192`；
- create-only checkpoint digest：`83d68a3e...cbe4e`；
- 用时 `70.50 s`，全部暖启动门通过。

P2 正式结果：

- 两个 T128 周期、`256/256` 个事务全部通过，worker PID 全部唯一；
- cycle 2 对 cycle 1 的最大周期门为完整 ECM `Z`：`4.92941e-6`；
- 四条波形最大值为 ECM `||Z||`：`3.94523e-6`；
- 峰值轴向缩短 `0.116881782`，周期 ECM 耗散 `2.47125888e-6`；
- 最大 KKT `1.10797e-7`，最大 coupling residual `8.34060e-5`；
- 最小 ECM `J=0.987735426`，最小 gap `0.015517647`；
- step 30 与 step 95–96 是两周期可重复的局部求解敏感区，均通过原门；
- 总用时 `10845.63 s = 3.01 h`，无重试、无追加周期。

P3 正式结果：

- T64→T128 全局、场、闭合和安全门全部通过；
- 最大相对全局差 `0.5151%`，最大适用场差 `0.4423%`；
- 两个黏弹记忆峰值相位差均为 `0.0078125T < 0.01T`；
- Figure 2 v02 已执行、自动核验并通过代理视觉 QA，保持工作版本等待确认；
- 审阅请求：`project_control/prl_p6_t128_execution_and_human_gate_review_v01.md`。

## 执行后人类处置

人类终审于 2026-08-30 接受 T128 Human Gate，并把 Figure 2 v02 冻结为时间
离散阶段 FINAL。该处置记录于
`project_control/prl_p6_t128_acceptance_and_spatial_tolerance_drafting_authorization_decision_v01.md`。
执行时“工作版本等待确认”的事实保留；本段只记录后续生命周期变化。

## 偏差与阻塞

DEV001：首次 P1 由宿主 Python 启动，因宿主缺少 `basix` 在内部初始化前失败。
失败 v01 目录保留；修正为合同指定的 CPU FEniCSx 容器并使用 create-only v02
目录，不改变科学输入、求解门或后续周期证据定义。当前无科学阻塞。
