---
decision_id: DECISION-PRL-INDEPENDENT-THEORY-MAINLINE-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-27
canonical_plan: project_control/prl_independent_theory_mainline_plan_v01.md
strategic_supersession:
  - project_control/efe_mainline_authorization_decision_v01.md
preserves:
  - project_control/publication_and_timescale_strategy_v01.md
  - project_control/efe_node0_acceptance_decision_v01.md
  - project_control/efe_node1_n1_2c_p5_acceptance_and_p6_drafting_authorization_decision_v01.md
  - 02_图表/Figures/Fig2_n1_2_time_adjudication/Fig2_n1_2_time_adjudication_v01_20260826
active_execution_authorization:
  contract: project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md
  scope: P0-P3_to_T128_Human_Gate
  executor_thread: codex://threads/019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# PRL 独立理论主线与双论文分工决定 v01

## 人类终审决定

项目当前主线调整为两篇相互独立、顺序明确的论文：

1. **PRL：理论先行的独立论文。** 以主动心肌—有限厚度黏弹 ECM/心胶—被动心内膜边界的周期力学为核心，发展可证伪、可无量纲化、可跨系统迁移的理论框架。PRL 是当前优先级与执行关键路径。
2. **EFE Nature：实验先行的独立论文。** 以斑马鱼 EFE 样表型、个体化四维力学史、前瞻盲验证、谱系与细胞状态、Gate X 因果干预及人源验证为核心。它不是 PRL 发表前的必需章节，也不承担 PRL 的通用理论证明。
3. **论文顺序。** EFE 项目可以在 PRL 完成前提供少量、受控的实验校准与独立验证；PRL 发表并冻结理论版本后，EFE Nature 才把该版本作为预先存在的分析框架，用于疾病机制检验。

## 对旧 EFE 理论主线的前向覆盖

本决定只覆盖 `efe_mainline_authorization_decision_v01.md` 中“EFE 是本仓库主应用、Node 0–4 构成同一理论主线”的战略解释，不追溯改写任何已经完成、失败或冻结的证据。

- 已接受的 EFE Node 0 变量、量纲和接口继续保留，转为 **EFE Nature 的下游机制接口与候选假说库**；
- 已完成的 Node 1 快速三层计算继续保留，转为 **PRL 通用理论与数值验证证据**；
- 原 Node 2–4 的慢重塑、空间病灶和疾病几何路线转为 **EFE Nature 发表后的应用路线**，不再阻塞 PRL；
- Figure 2 v01 及全部失败门、收敛限制、数值警告和哈希证据保持不变，不得因论文分工调整而覆盖或升级表述。

## PRL 的有界中心主张

PRL 当前检验的候选命题是：

> 周期主动变形通过有限厚度黏弹夹层向被动边界传递时，夹层厚度、松弛时间、界面连接、主动异质性和离散细胞尺度共同控制位移/牵引的衰减、相位滞后、局部化与耗散；这些响应可由少数无量纲组合和离散—连续适用边界统一描述。

在完成收敛、共同极限、替代本构和独立实验检验前，上述内容保持为候选理论，不宣称已经建立普适定律。

PRL 不主张也不需要证明：

- EFE 的细胞来源、EndMT、Gate X 或人类疾病机制；
- EFE 的阈值、双稳态、自维持、病灶扩展或治疗效果；
- 单一斑马鱼疾病模型足以证明框架普适；
- DCM–FEM 在所有尺度或所有问题上优于全 FEM。

## EFE 对 PRL 的有限服务方式

EFE 实验仅通过预先登记的接口服务 PRL：

| 数据分区 | 允许用途 | 禁止用途 |
|---|---|---|
| `PRL-Cal` | 估计几何量级、心搏周期、夹层厚度和合理参数范围 | 支撑 PRL 的独立预测或疾病因果结论 |
| `PRL-Val` | 检验冻结后的相位、衰减、局部化或扰动方向预测 | 在看见结果后反向改模型或改门限 |
| `EFE-Discovery` | EFE 表型发现、谱系、Gate X 候选和实验优化 | 进入 PRL 主文的通用规律拟合 |
| `EFE-Blind` | PRL 框架冻结后，检验 EFE 个体/时相/干预预测 | PRL 发表前解盲或参与参数选择 |

同一实验个体、时相或处理组不得同时承担校准与盲验证。任何跨分区移动都需另立前瞻性决定并保留审计记录。

## 当前执行授权

人类终审本轮明确要求通知“总管”任务继续工作。因此批准
`efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md` 的 P0–P3：实现并测试 T128 入口、构造 T64→T128 暖启动、执行两个 T128 事务周期、完成 T32/T64/T128 裁决与 Figure 2 v02，并在 T128 Human Gate 停止。

该授权沿用合同内的全部 fail-closed 门和资源边界；仍不授权：

- T256、空间细化、参数扫描；
- N1-2d、N1-3、原 EFE Node 2–4；
- GPU worker、新外部求解器或双向 FSI；
- 用 Figure 2 v02 静默覆盖已冻结的 Figure 2 v01；
- 把通过的时间离散门外推为完整空间收敛、材料标定或 EFE 机制验证。

## 冻结与复用门

PRL 对外投稿前必须生成带版本号的理论冻结包，至少包含方程、无量纲量、适用域、参数接口、代码提交、验证门和失败边界。EFE Nature 只能引用该冻结版本；若 EFE 数据暴露框架失效，应作为前瞻性扩展或失败证据处理，不得回写并伪装为 PRL 的预先预测。
