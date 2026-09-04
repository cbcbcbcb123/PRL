---
document_id: PRL-CURRENT-STATUS
status: current
last_verified: 2026-09-04
branch: codex/simucell3d-hybrid-feasibility
verified_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
current_lifecycle: paper2_figure2_execution_contract_v02_accepted_implementation_only_authorized
current_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md
current_authorization: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02_supervisor_acceptance_and_implementation_authorization_decision_v01.md
current_clarification: none
execution_authorized: exact_15_figure2_validation_files_implementation_only
current_execution_log: not_started_implementation_candidate_stage
latest_completed_execution_log: project_control/paper2_v08_myocardial_fem_only_architecture_migration_execution_record_v01.md
latest_supervisor_decision: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02_supervisor_acceptance_and_implementation_authorization_decision_v01.md
current_theory_contract: project_control/paper2_figure1_three_layer_theory_contract_v02.md
preserved_legacy_lifecycle: prl_figure2_spatial_tolerance_st1_a1_cycle_stability_failed_human_gate
preserved_legacy_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
current_mainline: project_control/prl_independent_theory_mainline_plan_v03.md
current_mainline_decision: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
current_physical_removal_record: project_control/paper2_myocardial_dcm_physical_removal_execution_record_v01.md
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
---

# PRL 项目当前状态（单一入口）

本页是项目的**当前状态索引**。合同、决定、执行记录和失败记录仍各自保留为不可替代的证据；若旧文档中的“当前状态”与本页冲突，应先核对本页列出的最新决定，而不是改写历史记录。

人类已授予 Paper 2 既定主线内的持续自主执行权：常规与科学阶段不再逐项等待批准，
由 Supervisor 留下版本化决定后连续推进，并每 10 分钟用图表汇报。删除/覆盖既有证据
及启动 GPU worker 仍须单独询问。

## 1. 一句话状态

Paper 2 v08 已通过独立 Supervisor 验收，唯一活跃生产架构冻结为“离散心内膜细胞链＋
主动心肌 FEM＋黏弹 ECM FEM”。旧心肌 DCM 源码、测试、运行入口及
`results/paper2_m2/` 已按人类确认从当前工作树物理删除；历史合同、决定和执行记录仅作
审计。Figure 1 三层理论合同 v02、Figure 2 FEM-only 数值可信度
合同 v03 和执行合同 v02 均已通过独立验收。执行合同冻结 39 个动态调用＋1 个 G0 P0
复用、无环验证梯、128×256 共同域、第二周期精确账本、S1 独立留出以及 create-only
事务。心肌 DCM 与 identity/M2B 路线只在不可改写的文字记录中保留，不得重新进入活跃
源码、模型选择、论文比较或后续整心房架构。当前只授权新增合同列出的 15 个实现/测试文件；不授权
运行测试、solver、Docker 或正式 r01。

旧 DCM–FEM–DCM Figure 2 路线的文字证据链继续保留：T128 时间离散阶段 FINAL 不变；
A1 已完成 128 个接受事务，但因 ECM 黏弹内变量未达到周期门而失败。其旧可执行源码和
`results/paper2_m2/` 已物理删除，不能再运行或迁移成 FEM-only 新模型证据。Git 已跟踪
历史仍可从删除前提交 `8f240cf38cb4db38f02b776d320562058439770f` 审计。

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
- v05.1 资源修复重试执行记录：
  `project_control/paper2_m2a_v05_1_t256_resource_repair_retry_execution_record_v01.md`；
- v05.1 create-only 成功包：
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`；
- 正式标签：`T256_TIME_CONVERGENCE_PASS_V05`。54/54 个端点、74/74 个空间门、
  54/54 个周期门、2/2 个热点门和 74/74 个三层时间门通过；最大 `r_12` 为
  `0.0004150504093643955 < 0.01`；
- 最大直接相对残差为 `2.9681468104030423e-08 < 1e-07`，最大功率账本残差为
  `2.515595272983527e-09 < 1e-08`，最大离散闭合相对误差为
  `2.520540448406629e-14 < 1e-10`；
- 原失败端点本次耗时 `30.62505569300265 s < 60.0 s`。全阶段耗时
  `735.4341055739933 s < 5400 s`，峰值内存 `1.1175003051757812 GiB < 16 GiB`；
- 成功包 16 个 JSON 和 12 个 NPZ（360 个数组）均为有限值，hash ledger 27/27 条目
  复算一致；v05 首次失败包、v05 实现及 T64/T128 源证据保持只读；
- 该结论不拟合收敛阶，也不构成 DCM-FEM identity、生理标定、三维或疾病机制证据。
- v05.1 Supervisor 独立验收与 v06 identity gate 授权：
  `project_control/paper2_m2a_v05_1_t256_supervisor_acceptance_and_identity_gate_decision_v01.md`；
- 当前 v06 identity 合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md`；
- v06 只允许读取冻结 T64/T128/T256 包并比较 S4/T256/D0 的 DCM–FEM 留出端点，输出
  `GO-ID`、`MAYBE-ID`、`NO-GO-ID` 或 `BLOCKED` 后停止在 Supervisor Gate；
- v06 不授权重新求解、改参数、改共同投影、改身份阈值、M2B、三维、流体或 GPU。
- v06 执行记录：
  `project_control/paper2_m2a_v06_identity_gate_execution_record_v01.md`；
- v06 create-only 失败包：
  `results/paper2_m2/identity_gate_v06_v01_20260904/`；
- 正式决策：`BLOCKED`。T64 manifest 对
  `tests/paper2_m2/test_protocol_v03.py` 的期望 SHA-256 为
  `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`，当前文件为
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5`；
- T64 结果包 ledger、端点、结构门、数值门和动态留出均通过；T128/T256 源锁通过；
  v01 `combined_load_gain` 原算子哈希锁通过。阻塞来自冻结实现精确哈希，而非力学或
  identity 数值失败；
- v06 定向测试 `18 passed`，相关轻量回归 `37 passed`；正式入口耗时 `7.5614 s`，
  峰值内存 `0.03888 GiB`，未使用 GPU、网络或求解器；
- 失败发生在正式 identity 计算之前，因此不得报告 GO-ID、MAYBE-ID 或 NO-GO-ID。
- Supervisor EOF 字节诊断与 v06.1 重试决定：
  `project_control/paper2_m2a_v06_t64_test_eof_hash_diagnosis_and_v06_1_retry_decision_v01.md`；
- 当前文件为 1681 字节；只在末尾追加一个 LF 后为 1682 字节，SHA-256 从
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5` 精确变为
  T64 manifest 的 `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`；
- v06.1 仅允许对这一路径和这对精确哈希应用 `ACCEPTED_TEST_EOF_FORMATTING_DELTA`，
  且必须同时核对 Git clean、T128/T256 当前哈希背书和其余全部源锁；
- v06.1 新 create-only 目标为
  `results/paper2_m2/identity_gate_v06_v02_20260904/`，v01 失败包保持冻结。
- v06.1 重试执行记录：
  `project_control/paper2_m2a_v06_1_identity_gate_retry_execution_record_v01.md`；
- 单例兼容正式标签：`ACCEPTED_TEST_EOF_FORMATTING_DELTA`；全部 18 项精确条件通过，
  当前测试文件没有被修改；
- v06.1 正式 identity 决策：`NO-GO-ID`。45 条正式记录为
  `35 pass / 4 maybe / 6 no_go`；只有 `ID-LS` 全部门通过；
- 主要 NO-GO：`ID-A2` 两侧界面牵引差 `80.4031% / 80.3362%`，`ID-LN` 峰值与
  波形缩短差 `18.3367% / 18.0161%`，`ID-S1` 两侧界面牵引差
  `15.0255% / 25.5128%`；
- v06.1 create-only 正式结果包：
  `results/paper2_m2/identity_gate_v06_v02_20260904/`；11/11 JSON 有限，hash ledger
  10/10 一致，源包前后哈希逐项一致，未生成 NPZ；
- 该 `NO-GO-ID` 只适用于冻结理想化二维六留出身份门，不证明任一模型错误，也不外推
  到三维、整心房、生理、EFE、实验或流体。
- v06.1 Supervisor 验收与 v07 诊断决定：
  `project_control/paper2_m2a_v06_1_no_go_identity_supervisor_acceptance_and_v07_diagnostic_decision_v01.md`；
- 当前 v07 只读诊断合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_failure_diagnostic_contract_v07.md`；
- v07 只允许分解既有牵引的幅值、方向、分量、空间/时间模态，穷举一个共同的有限
  signed-permutation 坐标基，审计纯模式/组合载荷与生产提取源码；
- v07 不改变 `NO-GO-ID`，不允许拟合比例、按工况校准、修改实现、重跑端点或进入 M2B；
  若诊断指向实现或模型修订，必须先向人类报告并形成新合同。
- v07 执行记录：
  `project_control/paper2_m2a_v07_identity_no_go_diagnostic_execution_record_v01.md`；
- v07 create-only 正式结果包：
  `results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/`；
- 正式诊断标签：`MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`。四个合同条件中只有该条件为真；
  v06.1 `NO-GO-ID` 未改变；
- 四条失败牵引的共同最优实标量为 `1.094511367664237`，但共同缩放后最大残差为
  `1.9168933799157437`；8 个有限坐标基的共同最优仍是 identity，最大记录残差仍为
  `0.804030579944649`；生产单位、符号、测度、权重、分量与共同投影审计干净；
- 差异主要定位在 `ID-A2`：心肌–ECM 的 `x` 为“空间异质/DC”，两侧 `y` 为
  “空间均值/基频”。C0/CQ 的 A2+LN DC/基频叠加最大残差仅
  `0.0023057714266971428`，不改变 identity 失败；
- 正式包 12/12 JSON 有限，hash ledger 11/11 一致，0 个 NPZ；耗时
  `13.776534800010268 s`，峰值内存 `0.050426483154296875 GiB`；未使用 solver、
  endpoint rerun、Docker、GPU 或网络；
- 当前证据只支持冻结理想化二维基准中的表示级本构不等价，不判断哪种模型正确，也不
  外推到三维、整心房、生理、EFE、实验或流体。
- v07 Supervisor 独立验收与模型架构 Human Gate：
  `project_control/paper2_m2a_v07_supervisor_acceptance_and_model_architecture_human_gate_v01.md`；
- Supervisor 原始数组复算逐值重现 4/4 正式失败牵引、共同标量与 8 个有限坐标基结果；
  v07 的 22 项定向测试、74 项轻量回归和静态检查均独立通过；
- v07 Human Gate 已由人类最新决定关闭；“心肌 DCM comparator”方案未被采用。
- 人类最新架构决定：
  `project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md`；
- 最新决定进一步否决“心肌 DCM comparator”：心肌 DCM 从活跃生产、理论、参数空间、
  图件和器官级扩展中完全退役；只有历史证据保留；
- 当前 v08 迁移合同：
  `project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md`；
- v08 将建立不导入旧双表示模块的 `src/paper2_hybrid/`，移除 representation 轴、心肌
  DCM 参数/校准/identity 指标，并用六个冻结 T64 FEM 工况做严格 FEM→FEM 迁移等价门；
- v08 不授权删除旧证据、重新标定、参数扫描、三维、整心房或流体。
- v08 执行记录：
  `project_control/paper2_v08_myocardial_fem_only_architecture_migration_execution_record_v01.md`；
- 唯一活跃包：`src/paper2_hybrid/`；生产 import graph 不依赖 `paper2_m2`，公共 API 与
  端点键均无心肌表示轴；
- v08 create-only 正式结果包：
  `results/paper2_v08/fem_only_architecture_parity_v01_20260904/`；
- 正式标签：`FEM_ONLY_ARCHITECTURE_PASS_V08`。`A2/LN/LS/C0/CQ/S1` 六工况全部通过；
  规定标量、每工况 28 个完整数组、原生/共同投影牵引的最大误差均为 `0`，ECM 场
  24/24 组字节哈希相等；
- 矩阵对称性、刚体模态处理、界面作用反作用、制造解、单位/符号、周期与离散功率账本
  门全部通过；
- 正式包 9/9 JSON 有限，hash ledger 8/8 一致，0 个新 NPZ；旧参考 24 项与退役代码
  50 项前后锁一致；耗时 `189.14686104100838 s`，峰值内存
  `0.7554397583007812 GiB`；未使用网络、GPU 或 Docker socket；
- 该标签只证明代码提取迁移等价，不是生理验证或新机制结论。当前证据远未达到
  Nature Physics；该期刊仅作为后续问题设计标准和有条件战略目标。

## 1.3 Paper 2 Figure 1–2 当前理论与数值合同门

- Figure 1 已接受合同：
  `project_control/paper2_figure1_three_layer_theory_contract_v02.md`；
- Figure 2 已接受合同：
  `project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md`，SHA-256
  `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249`；
- v03 Supervisor 验收与下一步决定：
  `project_control/paper2_figure2_fem_only_numerical_credibility_v03_supervisor_acceptance_and_execution_contract_decision_v01.md`；
- Figure 2 开发门唯一顺序为
  `G0→G1→G2→G3→G4a→G5→G4b→G4→G6→G7→digest→S1`；
- 共同域冻结为 128 个空间 P0 段 × 256 个周期中心化相位 P0 段；单频场取解析段平均，
  逐步功/耗散独立按区间交叠守恒映射；
- S1 是规则和开发结果 digest 后才解盲的独立空间异质留出；
- 已接受执行合同由
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md` 与
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md`
  按 v02 优先级共同组成；v02 SHA-256 为
  `11ebd843cf23c404c920a0274b409a907e01cd1755a2a5812de1eb8bdc66e253`；
- 执行合同 Supervisor 接受与实现授权：
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02_supervisor_acceptance_and_implementation_authorization_decision_v01.md`；
- 当前只有设计/执行合同被接受，尚无实现验收或 Figure 2 v03 数值 PASS。下一步仅新增
  7 个验证模块、1 个 runner 和 7 个测试，完成后停在实现候选独立复核门。

## 2. 已完成并可引用的阶段证据

- X1-K v11 已得到 `passed_x1_k_v11_transactional_survivor_r1r_c1_f1`，并已由人类终审接受；v01–v10 的失败与修复链继续保留。
- 心肌–ECM–心内膜三层快速力学基线、制造解和分离载荷证据已经形成。
- T16/T32/T64/T128 时间路径已经完成受控裁决；T128 Human Gate 于 2026-08-30 通过。
- Figure 2 v02 已冻结为时间离散阶段 FINAL；它不是整篇论文的最终 Figure 2，也不证明空间、容差或共同极限收敛。
- 空间与容差合同 v02 已闭合 v01 的八项审阅阻塞，独立结论为 `PASS_FOR_HUMAN_REVIEW`；该结论不是执行授权。
- v08 已建立并验证独立 `paper2_hybrid` 活跃命名空间；六工况迁移等价为逐值误差 `0`，
  并已通过独立 Supervisor 复核。
- Figure 1 理论合同 v02 与 Figure 2 数值可信度合同 v03 已通过独立 Supervisor 复核；
  两者是方程/验证规则证据，不是 Figure 2 计算通过证据。

关键证据入口：

- `project_control/hybrid_x1_k_transactional_survivor_repair_execution_report_v11.md`
- `project_control/prl_p6_t128_execution_and_human_gate_review_v01.md`
- `project_control/prl_figure2_v02_time_discretization_freeze_record_v01.md`
- `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`
- `project_control/prl_figure2_spatial_tolerance_contract_v02_independent_review_v01.md`

## 3. 尚缺的论文级证据

1. 新 FEM-only Figure 2 的空间细化、时间细化、代数容差、严格离散功率闭合及终局
   细网格时间触发证据；
2. cell/meso-resolved active FEM 与 homogenized active FEM 的共同极限及粗粒化适用域；
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

M2A 心肌 DCM identity 路线已整体退役；v08 已完成。当前只授权实现 Figure 2 执行合同
列出的 15 个新文件，不授权运行测试、solver、Docker、正式 r01 或创建结果目录。不得删除、
覆盖或续接 v06 v01 失败包与
v06.1 v02 正式包；不得把 EOF 兼容规则扩展到其他文件或哈希，不得修改当前测试文件以
迎合旧 manifest。不得重跑 DCM/FEM 求解器，不得覆盖或续接 v05 失败包及 v05.1 成功包，
也不得修改 v01-v06.1 冻结实现。拟合比例、按工况校准、模型/映射/提取实现修改、S5、
界面离散/共同投影修改、生产观测量替换和身份/数值门槛修改均未授权。
仍不授权：M2B 三维、
非匹配界面升级、A1 再周期化、B1/A2/B2、A3、A4、B3、B4、D1/F200N 完整周期、旧路线
T256、空间参数扫描、N1-2d、N1-3、原 EFE Node 2–4、GPU worker、新外部求解器、CFD、
单向/双向 FSI、器官级几何扩展或大参数海。

## 6. 最新终局主线与空间/容差门之后的优先级

最新路线见 `project_control/prl_independent_theory_mainline_plan_v03.md`，依次为：

1. Figure 1 三层理论；
2. Figure 2 新 FEM-only 架构数值可信度；
3. Figure 3 最小、预登记的 `De × H` 传递律；
4. Figure 4 cell/meso-resolved active FEM 与 homogenized active FEM 的共同极限和
   粗粒化适用域；
5. Figure 5 主动心肌 H-FEM＋黏弹 ECM＋离散心内膜的整心房预测与独立验证。

**Nature Physics** 是问题设计、机制深度与普适性的战略目标，不是当前成熟度结论。
当前证据远未达到该期刊标准；只有获得简洁无量纲规律、跨几何稳健性和独立留出预测，
才保留该目标，否则由后续证据门降档至 **PRX Life**，或在结果形态适合时评估
**Physical Review Letters**。Figure 2 后续、`De×H`、FEM 家族粗粒化、整心房与流体
都需另立前瞻合同，不由本路线图自动授权。

## 7. 仓库一致性待办

- 根目录 `README.md` 仍写有“X1-K 仍未通过”，与已接受的 v11 结果冲突；当前只登记为待修正项，尚未获得修改授权。
- 仓库存在较多未纳入版本控制的结果、图件和过程文件；投稿前必须建立 evidence inventory，逐项确认来源、版本、hash 和是否应纳入仓库。当前不清理、不移动、不提交这些文件。
- 本页的建立不改变任何计算结果、合同状态或执行权限，也不构成提交/推送授权。
