---
decision_id: DEC-PAPER2-M2A-S4-TERMINAL-SPATIAL-DIAGNOSTIC-V01
status: approved_by_human_final_reviewer
decider: human_final_reviewer
decided_at: 2026-09-03
related_contract: project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md
related_execution: project_control/paper2_m2a_s3_interface_traction_diagnostic_execution_record_v01.md
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 M2A S4 终止型空间诊断授权决定 v01

## 1. Decision

人类终审人批准一次边界严格的 S4 终止型空间诊断，用于区分：

1. S3 仍未进入渐近区；
2. 当前界面离散或 traction 观测量存在不可忽略的一致性平台。

本授权不修改原生产 traction 定义、共同投影定义、`1%` 空间门、两项校准、模型方程、
材料/几何/载荷、求解器或冻结配置。诊断完成后必须回到 Human Gate。

## 2. Frozen scientific scope

- 工况：仅 `ID-A2`、`ID-S1`；
- 表示：仅 `DCM`、`FEM`；
- 时间与容差：仅 `T64/C1`；
- 空间层：`S3=(64, 16/层)`、`S4=(128, 32/层)`；
- 原生观测量：沿用既有节点/弹簧 traction 的空间—时间 L2；
- 共同观测量：把 S3 与 S4 的原生 P1 traction 保守投影到 S3 的 64 个共同分段，
  每段取精确积分平均；
- 两个界面均报告：myocardium–ECM 与 endocardium–ECM；
- 两项 DCM 校准值和冻结配置摘要必须与 S3 输入逐值一致；
- 在同一个 create-only 新结果包内重算 S3 与 S4，不拼接旧数组；
- 旧 S3 摘要只用于逐值重放核验与 S2→S3 方向基线。

## 3. Required implementation and checks

允许的写入范围仅为：

- 新入口 `scripts/run_paper2_m2a_s4_terminal_spatial_diagnostic_v01.py`；
- 新的定向测试文件位于 `tests/paper2_m2/`；
- create-only 结果目录
  `results/paper2_m2/s4_terminal_spatial_diagnostic_v01_20260903/`；
- 执行记录
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_execution_record_v01.md`；
- 完成后同步 `project_control/CURRENT_STATUS.md`。

现有 `config.py`、`identity_2d.py`、`interface_projection.py` 已提供显式诊断层和共同投影
能力，不授权修改。若 S4 需要改动这些核心模块、模型或求解器，必须停止并记录偏差。

执行前和执行中必须完成：

1. S4 共同投影制造检查：常场、总界面力、符号和常牵引离散功达到机器精度；
2. 宿主环境与冻结 DOLFINx CPU 容器内的定向测试；
3. S4 单端点装配探针及 UFL/手工矩阵一致性检查；
4. 八个端点的求解残差、作用—反作用、功率账本、非负耗散、周期状态和制造解门；
5. 新结果包内 S3 值对旧 S3 值的逐项重放相对差 `<=1e-12`；
6. S3→S4 的原生量与共同投影量相对差，并报告其相对 S2→S3 的方向；
7. JSON 使用有限数值并可解析；输出 gate-critical 文件的 SHA-256。

## 4. Frozen decision rule

- 任一结构门、投影制造检查、S3 重放、资源门失败：`DIAGNOSTIC_FAIL`；
- 任一指标在原生量与共同投影量之间给出不同的 `1%` 结论：
  `OBSERVABLE_DEPENDENT`；
- 只有全部八项界面指标在两种观测量下均 `<=1%`，且细化方向一致，才可写
  `DIAGNOSTIC_PASS`；
- 其他情况均为 `DIAGNOSTIC_FAIL`。

`DIAGNOSTIC_PASS` 只表示 S3→S4 进入当前空间门的候选，不是 M2A 身份等价通过，也不
自动把 S3/S4 登记为新的生产空间梯度。

## 5. Resource and execution boundary

- 仅使用既有 `dolfinx/dolfinx:v0.11.0` CPU 容器；单进程、容器禁网；
- 不使用 GPU；
- 总预算 `900 s`、`16 GiB`；超限即 fail-closed；
- 旧结果只读，新结果 create-only；不得覆盖、清理或移动既有证据；
- 不授权 T128/T256、完整 324 端点矩阵、M2A GO/MAYBE/NO-GO、M2B、三维、整心房、
  真实几何、CFD/FSI、新求解器、参数扫描、Git 提交/推送或发布。

## 6. Mandatory stop and handoff

无论结果为何，执行任务均须写明：

- S3/S4 两种观测量的逐指标数值、方向与判定；
- 资源使用、测试、偏差、结果文件和 hash；
- 未执行的禁止范围；
- 正式标签 `DIAGNOSTIC_PASS`、`OBSERVABLE_DEPENDENT` 或 `DIAGNOSTIC_FAIL`。

完成后停止在 Human Gate，等待人类决定是修订生产空间梯度、修订界面离散/观测合同，
还是终止当前身份转换路线。
