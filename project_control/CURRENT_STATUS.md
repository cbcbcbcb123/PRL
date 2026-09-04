---
document_id: PRL-CURRENT-STATUS
status: current
last_verified: 2026-09-04
branch: codex/simucell3d-hybrid-feasibility
verified_commit: d40f4813d0dcd5715f8db3011c49bcf0b635b2b5
current_lifecycle: paper2_m2a_v05_1_t256_resource_repair_retry_authorized
current_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md
current_authorization: project_control/paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md
current_clarification: project_control/paper2_m2a_v03_phase_r_endpoint_count_clarification_decision_v01.md
execution_authorized: v05_1_endpoint_runtime_gate_repair_and_full_t256_retry_only
current_execution_log: pending_v05_1_retry_execution
latest_completed_execution_log: project_control/paper2_m2a_v05_t256_execution_record_v01.md
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

Paper 2 M2A v05 T256 已在第 18/54 个端点因 `30.3851 s > 30.0 s` 单端点资源门
fail-closed；18/18 科学结构门均通过，尚无 T256 时间收敛结论。Supervisor 已独立接受
失败并批准资源版 v05.1：只把 T256 单端点上限按时间步翻倍关系预注册为 `60.0 s`，总时间、
内存和全部科学门保持不变；将在全新 v02 目录从第 1 个端点完整重试。identity gate 和 M2B
仍未授权或启动。

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
- 功率账本最小诊断授权：
  `project_control/paper2_m2a_v02_t64_power_ledger_failure_diagnostic_authorization_decision_v01.md`；
- 功率账本诊断执行记录：
  `project_control/paper2_m2a_v02_t64_power_ledger_diagnostic_execution_record_v01.md`；
- create-only 诊断结果包：
  `results/paper2_m2/power_ledger_diagnostic_v01_20260903/`；
- 正式标签：`DISCRETE_LEDGER_MISMATCH_CONFIRMED`。H2 确认 C0/C1 仅改变验收阈值；
  H1、H3、H5 被证伪，H4 被确认；
- Supervisor 验收与 v03 修复决定：
  `project_control/paper2_m2a_v02_diagnostic_acceptance_and_v03_repair_decision_v01.md`；
- 当前 v03 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md`；
- Phase R 端点数量澄清：
  `project_control/paper2_m2a_v03_phase_r_endpoint_count_clarification_decision_v01.md`；
- v03 执行记录：
  `project_control/paper2_m2a_v03_ledger_repair_and_t64_execution_record_v01.md`；
- Phase R create-only 结果包：
  `results/paper2_m2/ledger_repair_v03_pilot_v01_20260903/`，正式标签
  `LEDGER_REPAIR_PILOT_PASS_V03`；
- Phase T64 create-only 结果包：
  `results/paper2_m2/identity_2d_v03_t64_v01_20260903/`，正式标签
  `T64_NUMERICAL_PASS_V03`；54/54 端点、74/74 空间主量、54/54 周期门和 2/2 热点门通过；
- 最大 S3→S4 相对差为 `0.939754% < 1%`；最大 D0 相对残差为
  `2.9681468104030423e-08 < 1e-07`，最大 normwise backward error 为
  `1.0172675692304304e-15 < 1e-12`。该结论仍不是 DCM–FEM identity 判定；
- v03 T64 Supervisor 验收与 T128 授权：
  `project_control/paper2_m2a_v03_t64_supervisor_acceptance_and_t128_decision_v01.md`；
- 当前 v04 T128 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md`；
- v04 T128 失败执行记录：
  `project_control/paper2_m2a_v04_t128_execution_failure_record_v01.md`；
- create-only 失败包：
  `results/paper2_m2/identity_2d_v04_t128_v01_20260903/`；
- 正式失败分类：`RUNNER_PATH_NORMALIZATION_ERROR`。T64 源锁、校准锁与定向测试通过，
  但 provenance manifest 在处理命令行相对源路径时异常；0/54 个 T128 端点运行，未形成
  空间门、动态 NPZ 或 74 个时间配对记录；
- 路径修复与重试决定：
  `project_control/paper2_m2a_v04_t128_path_normalization_repair_and_retry_decision_v01.md`；
- 重试使用新 create-only 目录：
  `results/paper2_m2/identity_2d_v04_t128_v02_20260903/`；
- 路径修复与 T128 重试执行记录：
  `project_control/paper2_m2a_v04_t128_path_repair_retry_execution_record_v01.md`；
- 正式阶段标签：`T128_STAGE_PASS_V04`。54/54 个端点、74/74 个空间门、54/54 个周期门、
  2/2 个热点门通过；74 个 T64→T128 配对仅标为 `T64_T128_PAIR_AUDIT_ONLY`，方向保持
  `PENDING_T256`；
- 成功包 14 个 JSON 和 12 个 NPZ（360 个数组）均为有限值，hash ledger 25/25 条目复算
  一致；原 v04 实现、首次失败包及 v03/T64 源证据保持只读。
- Supervisor 独立验收与 T256 决定：
  `project_control/paper2_m2a_v04_t128_supervisor_acceptance_and_t256_decision_v01.md`；
- 当前 v05 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md`；
- v05 只授权完整 T256 数值阶段与 74 个三层时间门，create-only 目标为
  `results/paper2_m2/identity_2d_v05_t256_v01_20260904/`；不得在本阶段计算跨表示 identity；
- v05 T256 执行记录：
  `project_control/paper2_m2a_v05_t256_execution_record_v01.md`；
- v05 create-only 失败包：
  `results/paper2_m2/identity_2d_v05_t256_v01_20260904/`；
- 正式失败分类：`T256_ENDPOINT_RUNTIME_BUDGET_EXCEEDED`。18/54 个 T256/D0 端点完成且
  18/18 科学结构门通过；第 18 个端点耗时 `30.38510538799892 s`，超过冻结单端点预算
  `30.0 s`。第 19 个端点、74/54/2 个 T256 汇总门、12 个动态留出和 74 个三层时间门
  均未执行；
- 失败包 12 个 JSON 均有限，hash ledger 11/11 条目复算一致；manifest 中 80 个冻结
  v01-v04/T64/T128 文件当前哈希未变。
- v05.1 资源门修复与重试决定：
  `project_control/paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md`；
- v05.1 唯一合同变化是 T256 单端点资源上限 `30→60 s`；阶段总时间 `5400 s`、内存
  `16 GiB`、科学实现和所有数值门不变；
- 全量重试必须从第 1 个端点开始并写入新 create-only 目录
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`，不得续接或覆盖 v01 失败包。

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

M2A 当前只授权资源版 v05.1：新增资源协议与 runner，在 `60.0 s` T256 单端点门下从头
重跑冻结的 54 个端点。不得覆盖或续接 v05 失败包，不得修改 v01-v05 冻结实现；若再次
触发资源门，不再自动放宽。正式 identity gate、S5、重新校准、界面离散/共同投影修改、
生产观测量替换和 1% 门槛修改尚未授权。仍不授权：M2B 三维、
非匹配界面升级、A1 再周期化、B1/A2/B2、A3、A4、B3、B4、D1/F200N 完整周期、旧路线
T256、空间参数扫描、N1-2d、N1-3、原 EFE Node 2–4、GPU worker、新外部求解器、CFD、
单向/双向 FSI、器官级几何扩展或大参数海。

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
