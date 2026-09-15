---
document_id: NCS-METHODS-ROUTE-ADOPTION-v01
recorded_at: 2026-09-10
decision_status: passed
numerical_status: not_run
scope: route_adoption_and_M0_M1_documentation
source: current_user_conversation
---

# FEM–DCM 方法路线采纳记录

用户最新指令：“同意你的思路，现在记录到项目中，然后将M0 及M1的仔细方案落到项目中，我让codex执行”。本记录采纳以 **Nature Computational Science 为研究设计目标**的路线：研究组织发生细胞事件时，连续组织与显式细胞之间的力学、状态和物质传递如何保持一致，并逐步验证跨几何、跨组织适用性。期刊水平与方法新颖性均为 `unknown`。

这是一份项目内部决定，依据用户对话形成，不冒充外部专家原件。本轮授权为记录路线、编写执行方案与更新导航；本轮不运行求解器、Docker 或测试计算，不提交、推送或创建自动化。后续执行者收到“执行 M0/M1”后，可按对应方案在限定范围内推进；本次文档不能充当已完成执行或已消耗预算的证据。

## 1. 当前有效路线与取代范围

- 新主计划：[方法路线](../planning/ncs_methods_roadmap_v01.md)。下一工作为 [M0](ncs_m0_method_positioning_plan_v01.md)，其门通过后才进入 [M1](ncs_m1_all_fem_baseline_plan_v01.md)。这里的 **NCS-M1** 不等于历史 Route H 的 M1。
- 在研究目标、后续阶段次序和驾驶舱当前入口上，取代旧的 Nature Physics 优先、P1→P2→P3 推进安排。旧 P1 的通过不再是新方法路线的前提；也不能借改名继续旧失败实验。
- 旧 P1 v03 执行记录仍有效：执行层通过，6/8 纵深带未通过冻结空间门，科学分类 `NOT_RESOLVED`。保留旧 P2/P3 阻塞、失败包和所有冻结约束。没有授权 S4、v04、阈值变更、ROI 或读出替换以挽救旧路线。
- 历史全局有符号牵引偶极路线保持关闭；新 M1 测基线误差、功率与经典传递，不使用该读出。
- 不从旧自主执行决定继承本路线的算力、容器、后台运行或周期汇报授权。本路线的阶段预算及边界见新方案；不建立自动化。

## 2. 固定模型边界

心肌始终采用主动 FEM；目前为**规定主动应变**，不称为完整主动张力模型。ECM 采用黏弹 FEM。历史心内膜离散弹性链不称为真实 DCM。新 M1 采用有限厚度被动心内膜 FEM；后续才换成闭合、可形变、具身份的 DCM 细胞层。

当前从二维理想体开始。血流、三维和生物复杂性是有条件的后续阶段，不是 M0/M1 内容。最终器官方向为心室，以斑马鱼为候选验证对象；不把心内膜女儿细胞预设为全部 EFE 成纤维细胞来源。

允许提出“新型守恒 FEM–DCM–FSI 方法”作为待检验目标，禁止作为已建立成果。守恒指闭合的力、功、物质及事件收支；主动驱动、黏弹耗散、生长与分泌系统的机械能或质量不必恒定。DCM 是候选表示，公平强对照必须包括获得相同身份、分裂和局部状态的动态材料域连续模型。

## 3. 当前证据与保护范围

本次沿用的历史数值证据来自 [v03 执行记录](paper2_lineage_odd_mode_gate_v03_execution_record_v01.md) 和 [摘要](../results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json)，没有重新计算。合同提交基准为 `b45650a9e370be138a70acf305b6c3a21e6a7ed2`；工作树另有未提交材料，不能把 HEAD 当成全部交付物的版本。

用户原始文件 `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md` 只读保留，记录时 SHA256 为 `633BE2CD534C05AC3D3416E4CA046D52B2B17BEF4F4B373FBB1A242A72E33274`。不得修改、还原或纳入建议提交。外部指导原包、原 runner 和历史结果不因路线切换改写。

## 4. 本轮交付与后续授权区别

| 项目 | 当前状态 | 含义 |
|---|---|---|
| 用户采纳方法路线 | PASS | 有当前用户指令 |
| M0/M1 方案落盘 | PASS | 只表示方案已形成 |
| M0 方法定位与数学规格验收 | NOT_RUN | 需要后续执行者完成独立证据和推导 |
| M1 数值基线 | NOT_RUN | 没有新模拟结果 |
| 方法优势、跨组织有效性 | UNKNOWN | 待比较与外部验证 |
| Nature Computational Science 投稿水平 | UNKNOWN | 不由项目路线选择保证 |

使用 `passed/failed/blocked/not_run/unknown` 保存执行状态；表格可显示 PASS/FAIL/BLOCKED/NOT_RUN/UNKNOWN。科学分类如 `NOT_RESOLVED` 单列保存，不能被执行 `passed` 覆盖。
