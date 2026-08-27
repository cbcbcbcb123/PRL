---
inspection_id: INSPECTION-EFE-NODE1-N1-2C-P5-V01
status: accepted_at_n1_2c_final_human_gate
inspector: human_final_reviewer
prepared_by: codex_current_task
submitted_at: 2026-08-26
related_plan: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
authorization: project_control/efe_node1_n1_2c_t64_acceptance_and_p5_authorization_decision_v01.md
executed_scope: p5_only
stopped_at: n1_2c_final_human_gate
acceptance_decision: project_control/efe_node1_n1_2c_p5_acceptance_and_p6_drafting_authorization_decision_v01.md
---

# EFE Node 1 N1-2c P5 三档时间裁决与最终审阅请求 v01

## 结论先行

P5 已按预登记规则完成，但 **N1-2c 严格时间收敛总门未完全通过**。

这不是一次整体数值失败。T16、T32、T64 分别处于周期态；T32→T64 的七条主要
波形、全部周期积分、全部峰值幅度、周期耗散、绝大多数三维场量和全部安全门均
通过。失败只集中在：

1. ECM 黏弹能与 ECM `||Z||` 的峰值相位差均为 `0.015625T`，高于预登记
   `0.01T` 门；
2. phase 1 的三层位移闭合残差已经很小且随细化下降，但用两个趋零残差互相
   归一化后产生 `78%–85%` 相对差，超过 `5%` 门。

因此最准确的阶段结论是：

> T64 已足以稳定当前基线的主要力学幅值、波形、积分、耗散和物理相位场，但尚
> 不足以通过预登记的全部时间裁决，尤其不能把 ECM 黏弹记忆的峰值相位称为已
> 收敛。

## 授权与证据来源

本次只读取已接受的：

- T16：R5 cycle 8；
- T32：cycle 2；
- T64：cycle 2。

未执行新的心搏周期、T128、空间细化、参数扫描、GPU worker或新外部求解器。
输入 CSV/NPZ/summary 均按 SHA-256 冻结，派生公式见 P5 授权决定。

结果目录：
`results/hybrid/efe_node1_n1_2c_time_adjudication_v01_20260826/`

## 全局时间门

T32→T64 最大差异：

| 类别 | 控制指标 | 最大差 | 门 | 判定 |
|---|---|---:|---:|---|
| 波形 | ECM 黏弹能 | `1.0744%` | `2%` | 通过 |
| 周期积分 | ECM 黏弹能 | `0.5945%` | `2%` | 通过 |
| 峰值幅度 | ECM 黏弹能 | `0.7257%` | `2%` | 通过 |
| 周期耗散 | ECM dissipation | `0.1868%` | `5%` | 通过 |
| 物理相位场 | 最大场摘要差 | `2.4588%` | `5%` | 通过 |
| 峰值相位 | ECM 黏弹能、`||Z||` | `0.015625T` | `0.01T` | **失败** |

29 条全局裁决中 27 条通过。两个失败项为：

- ECM 黏弹能峰值相位：T16/T32/T64 = `1.0 / 1.0 / 0.984375`；
- ECM `||Z||` 峰值相位：T16/T32/T64 =
  `0.6875 / 0.71875 / 0.734375`。

后者呈单调一阶趋势，Richardson 外推相位为 `0.75T`，但 T32→T64 当前差仍大于
硬门，不能用外推替代通过判定。前者位于周期边界附近，为非单调/端点敏感峰值，
不报告 Richardson 结论。

## 三维场与近零闭合问题

160 条场裁决中 154 条通过。六条失败全部来自 phase 1 的三层位移及其 p95：

| 层 | T16 p95 | T32 p95 | T64 p95 | T32→T64 相对差 |
|---|---:|---:|---:|---:|
| 心肌 | `1.68e-8` | `2.87e-9` | `5.00e-10` | `82.61%` |
| ECM | `1.02e-6` | `2.03e-7` | `4.39e-8` | `78.40%` |
| 心内膜 | `3.61e-7` | `9.98e-8` | `1.46e-8` | `85.37%` |

绝对闭合残差从 T16→T32→T64 下降约一个数量级；不存在随细化增大的物理漂移。
失败来自“用趋零量自身作分母”的严格预登记相对定义。该定义在数学上对近零闭合
量病态，但本轮没有事后改门或剔除，故总裁决仍诚实记录为失败。

除这六条近零闭合项外，场量 T32→T64 最大差为 `2.4588%`，低于 `5%` 门；包含
三层位移、ECM `J`、主应变、Cauchy 应力、平衡/黏弹能量密度、耗散密度、内部
变量 `Z` 及两界面法向/切向牵引。

## 观察阶与 Richardson 边界

全局指标状态：

- `13` 项满足单调、非近零且 `0.25 <= p <= 4`，报告 guarded Richardson；
- `5` 项为 `order_not_identifiable`；
- `4` 项为 `nonmonotone_time_refinement`；
- `7` 条波形范数不适用标量观察阶。

主要幅值和积分的可识别观察阶约在一阶附近；ECM `||Z||` 的积分和峰值幅度得到
较高阶，但不把单个指标的高阶当成整体渐近阶证明。

## 安全与求解器边界

三个时间级全部通过原安全门：

| Level | min `J` | min gap | max KKT | max coupling |
|---|---:|---:|---:|---:|
| T16 | `0.987725` | `0.0155228` | `9.47e-6` | `8.34e-5` |
| T32 | `0.987731` | `0.0155200` | `5.73e-8` | `4.61e-5` |
| T64 | `0.987734` | `0.0155184` | `1.35e-7` | `9.13e-5` |

T64 的 coupling 裕量较 T32 变小，但仍低于 `1e-4`；step 15 继续作为已注册的
求解路径敏感相位，不解释为生物学热点。

## 正式 Figure 2 v01

Figure 包：
`02_图表/Figures/Fig2_n1_2_time_adjudication/`
`Fig2_n1_2_time_adjudication_v01_20260826/`

图中：

- A：三档细胞缩短波形；
- B：ECM `||Z||` 幅值接近但峰值相位仍差一个 T64 步；
- C：五类通过、两类失败的门限归一化总览；
- D：两个峰值相位失败项；
- E：phase-1 绝对闭合残差随细化下降；
- F：T64 峰值 ECM 应力和 T32–T64 峰值位移差三维图。

Notebook 执行、自动校验和人工视觉 QA 均通过。Figure 当前为
**validated working, pending human confirmation**，尚未标记 FINAL。

文件 SHA-256：

- P5 summary：`dfe0f48ebdc375ecc9cfab2c22cd09a9b8fdc8e4d1e5a73ff06097200e3cd05d`；
- Figure PNG：`afe3940e874316066e60a5505bdc0503456914220466b3bb5083ffd1f1920276`；
- Figure SVG：`044f4941dbc2389d470dde1a8a4f445570f0d0645be9f8da1d39797f0922bc9e`。

## 软件核验

- 时间细化单元测试：`9 passed`；
- 完整 hybrid 回归：`106 passed in 176.93 s`；
- Ruff：时间细化模块、P5 后处理、测试和 Figure helper 全部通过；
- P5 summary 的 `passed=false` 是科学门结果，不是脚本或软件失败；
- 未启动 GPU，未改变任何接受的 T16/T32/T64 结果。

## 编辑级判断与下一步建议

如果目标是普通工程论文，可以把幅值/波形稳定作为“实际充分”。但本项目面向
Nature Physics，且 EFE 主线正依赖 ECM 黏弹记忆与相位滞后，因此不建议忽略两个
峰值相位失败项，也不建议把当前 T64 直接写成“完整时间收敛”。

建议后续起草一个最窄的 P6 合同：

1. 只增加 T128，不改变物理模型、空间网格、材料、门限或 solver；
2. T64→T128 暖启动后执行两个 T128 周期，专门检验峰值相位是否降至
   `<=0.01T`；
3. 保留本轮严格失败不回写；另行预注册 phase-1 闭合残差以“相对周期峰值位移”
   归一化，作为数学适定的辅助闭合指标；
4. 到 T128 Human Gate 停止，不自动进入空间细化或 N1-2d。

## Requested Human Decision

建议回复：

> 接受 P5 正式裁决与 Figure 2 v01，结论冻结为“主要物理读数在 T64 已稳定，但
> 预登记严格时间收敛总门未完全通过”；不接受“时间收敛已通过”的表述；批准
> 起草 P6 T128 定向验证合同，但暂不执行 T128。P6 只解决峰值相位分辨率和预注册
> 数学适定的闭合辅助指标，不改变物理模型、空间网格、材料、求解门或 Node 1
> 科学问题。

在获得该决定前，状态保持 `n1_2c_final_human_gate_pending_review`。
