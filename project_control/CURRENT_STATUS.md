---
document_id: PRL-CURRENT-STATUS
status: current
last_verified: 2026-09-03
branch: codex/simucell3d-hybrid-feasibility
verified_commit: 59d0f8fba85eacc53e17a7318e9784ff9eab1c49
current_lifecycle: paper2_m2a_v02_t64_failed_endpoint53_power_ledger_supervisor_gate
current_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md
current_authorization: project_control/paper2_m2a_s4_supervisor_acceptance_and_v02_ladder_decision_v01.md
execution_authorized: none_v02_t64_failed_waiting_supervisor_decision
current_execution_log: project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md
latest_completed_execution_log: project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md
preserved_legacy_lifecycle: prl_figure2_spatial_tolerance_st1_a1_cycle_stability_failed_human_gate
preserved_legacy_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
current_mainline: project_control/prl_independent_theory_mainline_plan_v02.md
current_mainline_decision: project_control/prl_independent_theory_mainline_supplement_decision_v02.md
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
---

# PRL 项目当前状态（单一入口）

本页是项目的**当前状态索引**。合同、决定、执行记录和失败记录仍各自保留为不可替代的证据；若旧文档中的“当前状态”与本页冲突，应先核对本页列出的最新决定，而不是改写历史记录。

人类已授予 Paper 2 既定主线内的持续自主执行权：常规与科学阶段不再逐项等待批准，
由 Supervisor 留下版本化决定后连续推进，并每 10 分钟用图表汇报。删除/覆盖既有证据
及启动 GPU worker 仍须单独询问。

## 1. 一句话状态

Paper 2 M2A v02 的 T64 全工况数值门在第 53/108 个端点 fail-closed：`ID-LN/DCM/S4/C0` 的功率账本归一化残差为 `1.4651e-07 > 1e-08`，其余该端点结构门通过。执行已停止在 Supervisor Gate；端点 54–108、T64 stage gate、T128/T256、正式 identity gate 和 M2B 均未启动。S4 诊断的既有 `DIAGNOSTIC_PASS` 不被改写，但 v02 当前不能声明 `T64_NUMERICAL_PASS`。

旧 DCM–FEM–DCM Figure 2 路线仍原样保留：T128 时间离散阶段 FINAL 不变；A1 已完成 128 个接受事务，但因 ECM 黏弹内变量未达到周期门而失败。新 M1 不改判 A1，也不把旧时间离散结果迁移成新架构证据。

## 1.1 Paper 2 M0–M1 最新证据

- 执行计划：`project_control/paper2_m0_m1_idealized_model_execution_plan_v01.md`；
- M0 兼容性审计：`project_control/paper2_m0_compatibility_audit_v01.md`；
- 执行日志：`project_control/paper2_m0_m1_idealized_model_execution_log_v01.md`；
- 最终候选结果：`results/paper2_m1/idealized_strip_v03_20260903/`；
- 诊断图：`results/paper2_m1/idealized_strip_v03_20260903/m1_diagnostic_summary.png`。

M1 是一维 P1 条带加二维切向/法向运动学的身份与端口验证，不是生理标定、正式收敛或二维/三维实体证据。v01/v02 结果包作为不覆盖的开发谱系保留，v03 是当前人类门候选。

## 1.2 Paper 2 M1 接受与 M2 合同门

- 人类决定：`project_control/paper2_m1_acceptance_and_m2_contract_authorization_decision_v01.md`；
- M2 合同草案：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`；
- M2A 二维身份转换已获人类授权并进入执行；
- M2A 与 M2B 分门：先做二维直接身份转换，独立检查与人类接受后才可提出三维执行附录。
- 执行授权：`project_control/paper2_m2a_execution_authorization_decision_v01.md`。
- M2A 预检阻塞记录：`project_control/paper2_m2a_preflight_failure_and_human_gate_v01.md`；
- 失败包：`results/paper2_m2/preflight_failure_v01_20260903/preflight.json`；
- 运行时恢复与常规自主执行决定：`project_control/paper2_m2a_runtime_recovery_and_routine_autonomy_decision_v01.md`；
- Docker 修复执行记录：`project_control/paper2_m2a_docker_runtime_repair_execution_record_v01.md`；
- Docker Linux engine 和既定 FEniCSx CPU 容器已验证可用；预检与冻结记录为
  `project_control/paper2_m2a_preflight_freeze_record_v01.md`；
- M2A T64 失败与 Human Gate：
  `project_control/paper2_m2a_t64_spatial_failure_and_human_gate_v01.md`；
- T64 结果包：`results/paper2_m2/identity_2d_v01_20260903/`；不得覆盖或改用其他求解器。
- S3 最小诊断授权：
  `project_control/paper2_m2a_s3_interface_traction_diagnostic_authorization_decision_v01.md`；
  仅允许 T64/C1、ID-A2/ID-S1、DCM/FEM、S2/S3 与共同界面投影比较；
- S3 诊断执行记录：
  `project_control/paper2_m2a_s3_interface_traction_diagnostic_execution_record_v01.md`；
- S3 诊断结果包：
  `results/paper2_m2/s3_interface_traction_diagnostic_v01_20260903/`；
- 诊断为 `OBSERVABLE_DEPENDENT`，不得解释为 M2A 通过或自行替换生产 traction 指标。
- S4 终止型诊断授权：
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_authorization_decision_v01.md`；
  仅允许 T64/C1、ID-A2/ID-S1、DCM/FEM、S3/S4 与冻结共同投影比较，现已完成并停止；
- S4 执行记录：
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_execution_record_v01.md`；
- S4 create-only 结果包：
  `results/paper2_m2/s4_terminal_spatial_diagnostic_v01_20260903/`；
- S4 正式标签为 `DIAGNOSTIC_PASS`；原生量最大 S3→S4 差为 `0.9398%`，共同投影量
  最大差为 `0.8800%`，四个新 S3 端点摘要对旧 S3 的逐项重放最大相对差为 `0`。
- Supervisor 验收与 v02 梯度决定：
  `project_control/paper2_m2a_s4_supervisor_acceptance_and_v02_ladder_decision_v01.md`；
- 当前增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md`；
  生产梯度为 S2/S3/S4；108 端点 T64 数值门已在第 53 个端点 fail-closed；
- v02 T64 执行记录：
  `project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md`；
- v02 T64 create-only 失败包：
  `results/paper2_m2/identity_2d_v02_t64_v01_20260903/`；
- 首个失败：`ID-LN__DCM__S4__T64__C0` 功率账本归一化残差
  `1.465114585633258e-07 > 1e-08`；已完成 53/108 端点，没有 T64 通过结论。

## 2. 已完成并可引用的阶段证据

- X1-K v11 已得到 `passed_x1_k_v11_transactional_survivor_r1r_c1_f1`，并已由人类终审接受；v01–v10 的失败与修复链继续保留。
- 心肌–ECM–心内膜三层快速力学基线、制造解和分离载荷证据已经形成。
- T16/T32/T64/T128 时间路径已经完成受控裁决；T128 Human Gate 于 2026-08-30 通过。
- Figure 2 v02 已冻结为时间离散阶段 FINAL；它不是整篇论文的最终 Figure 2，也不证明空间、容差或共同极限收敛。
- 空间与容差合同 v02 已闭合 v01 的八项审阅阻塞，独立结论为 `PASS_FOR_HUMAN_REVIEW`；该结论不是执行授权。

关键证据入口：

- `project_control/hybrid_x1_k_transactional_survivor_repair_execution_report_v11.md`
- `project_control/prl_p6_t128_execution_and_human_gate_review_v01.md`
- `project_control/prl_figure2_v02_time_discretization_freeze_record_v01.md`
- `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`
- `project_control/prl_figure2_spatial_tolerance_contract_v02_independent_review_v01.md`

## 3. 尚缺的论文级证据

1. Figure 2 的空间细化、代数容差、严格离散功率闭合及终局细网格时间触发证据；
2. DCM–FEM 与 cell-resolved / homogenized all-FEM 的共同极限及适用域；
3. Figure 3 的最小、预注册 `De × H` 状态图，以及可被证伪的稳定传递律；
4. 跨几何稳健性、独立预测和 Figure 5 验证；
5. 可投稿正文、补充材料和完整 evidence inventory。

在这些缺口闭合前，不得把目前结果表述为“DCM–FEM 已形成普适定律”或“已达到 PRL/PRX Life 投稿证据标准”。

## 4. 保留的旧 Figure 2 ST1 状态（非当前执行授权）

旧 ST0 已在当时授权范围内完成并获人类接受，执行记录为
`project_control/prl_figure2_spatial_tolerance_st0_execution_and_human_gate_review_v01.md`。
其历史授权只包括：

- A1=`D0/E1/F150/T64/C0` 与 B1=`D0/E1/F150/T64/C1`；
- A2=`D0/E2/F150/T64/C0` 与 B2=`D0/E2/F150/T64/C1`；
- 每个工况最多两个事务周期；暖启动不计为证据；
- ECM 4/6/8 层、C0/C1、共同求积、周期和功率裁决；
- 完成后停止在 ST1 Human Gate。

该历史授权现在不自动恢复；A1 失败后 B1/A2/B2 仍未开始。任何再周期化或后续端点都必须重新获得明确授权。

原运行时阻塞记录：`project_control/prl_figure2_spatial_tolerance_st1_runtime_blocker_v01.md`。
Docker/FEniCSx 已恢复；最新失败与人类门记录为
`project_control/prl_figure2_spatial_tolerance_st1_e1_warm_start_failure_and_human_gate_v01.md`。
E1 v03 的映射、SLS 周期性、体积和几何质量均通过，但归一化 KKT 残差
`1.9647424237527947e-05` 高于 C0 门 `1e-05`。按 fail-closed 规则，不进入 A1，
也不自动继续 E2、放宽门限或追加求解。

经人类批准的相位 0 诊断记录为
`project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_execution_and_human_gate_v01.md`。
一次额外、配置相同的 80-iteration continuation 将 KKT 降至
`9.986340629229005e-06`，全部硬门通过，但 L-BFGS 仍以达到迭代上限退出，且过门
裕量只有约 `0.1366%`。诊断 checkpoint 未直接用于 A1。人类已批准固定两段 80 次、
无第三段/无 fallback 的暖启动入口 v02；从 accepted R0 原始周期重算的 E1 v04
暖启动已通过，A1 已执行两个 T64 事务周期。全部单步硬门通过，但 cycle 2 相对
cycle 1 的界面牵引波形差 `0.0025315`、ECM `Z` 波形差 `0.0299952` 和周期末 `Z`
差 `0.0686534` 高于 `1e-3` 门，A1 端点失败。失败记录为
`project_control/prl_figure2_spatial_tolerance_st1_a1_failure_and_human_gate_v01.md`。
不自动追加第三周期，不进入 B1/A2/B2；当前等待是否批准 A1 再周期化诊断。

ST1 不包含 A3、A4、B3、B4、D1/F200N 完整周期或细网格 T128。

诊断图：`02_图表/Figures/Fig2_spatial_tolerance_st0_diagnostics_v03_20260901/st0_diagnostics.png`。

授权记录：`project_control/prl_figure2_spatial_tolerance_st0_acceptance_and_st1_authorization_decision_v01.md`。

## 5. 当前禁止范围

M2A v02 的 T64 全工况数值门已失败停止，当前没有自动延续的计算授权。不得补算端点 54–108、重跑失败端点、放宽功率账本门、改变残差定义或进入 T128/T256。正式 identity gate、S5、重新校准、界面离散/共同投影修改、生产观测量替换和 1% 门槛修改尚未授权。仍不授权：M2B 三维、非匹配界面升级、A1 再周期化、B1/A2/B2、A3、A4、B3、B4、D1/F200N 完整周期、旧路线 T256、空间参数扫描、N1-2d、N1-3、原 EFE Node 2–4、GPU worker、新外部求解器、CFD、单向/双向 FSI、器官级几何扩展或大参数海。

## 6. 最新终局主线与空间/容差门之后的优先级

最新路线见 `project_control/prl_independent_theory_mainline_plan_v02.md`，依次为：

1. Figure 1 三层理论；
2. Figure 2 数值可信度；
3. Figure 3 最小、预登记的 `De × H` 传递律；
4. Figure 4 DCM–FEM、cell-resolved all-FEM 与 homogenized all-FEM 的共同极限；
5. Figure 5 H-FEM 整心房骨架＋预登记局部 DCM patch 的跨尺度预测与独立验证。

整心房第一版只允许单向 `global H-FEM → local DCM patch`。只有局部修正使整器官
QoI 改变超过 `5%`，或热点移动超过一个细胞直径，才提请批准双向功率共轭耦合。

现实投稿目标为 **PRX Life**；只有获得简洁无量纲规律、跨几何稳健性和独立留出
预测，才上探 **Physical Review Letters / Nature Physics**。ST2、ST3、`De×H`、
N1-2d、GeometryAdapter 与整心房模型都需另立前瞻合同，不由本路线图自动授权。

## 7. 仓库一致性待办

- 根目录 `README.md` 仍写有“X1-K 仍未通过”，与已接受的 v11 结果冲突；当前只登记为待修正项，尚未获得修改授权。
- 仓库存在较多未纳入版本控制的结果、图件和过程文件；投稿前必须建立 evidence inventory，逐项确认来源、版本、hash 和是否应纳入仓库。当前不清理、不移动、不提交这些文件。
- 本页的建立不改变任何计算结果、合同状态或执行权限，也不构成提交/推送授权。
