---
decision_id: DEC-PAPER2-V08-ACCEPT-FEM-ONLY-ACTIVE-ARCHITECTURE-FREEZE-V01
status: accepted_and_frozen
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
human_architecture_decision: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
accepted_contract: project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md
accepted_execution: project_control/paper2_v08_myocardial_fem_only_architecture_migration_execution_record_v01.md
accepted_result: results/paper2_v08/fem_only_architecture_parity_v01_20260904/
accepted_label: FEM_ONLY_ARCHITECTURE_PASS_V08
execution_authorized: none_pending_next_versioned_theory_contract
---

# Paper 2 v08 Supervisor 验收与心肌 FEM-only 活跃架构冻结 v01

## 1. Supervisor 决定

Supervisor 接受 v08 正式标签 `FEM_ONLY_ARCHITECTURE_PASS_V08`，并冻结唯一活跃生产
架构：

| 组织层 | 固定实现 |
|---|---|
| 心内膜 | 离散细胞链 |
| 心肌 | 主动平面应变 FEM |
| ECM | 黏弹平面应变 FEM |
| 流体 | v08 不包含，后续必须另立合同 |

心肌 DCM 从活跃源码、运行时选择、参数空间、端点命名、论文主线、Figure 4 比较和后续
整心房模型中退役。不得重新引入心肌 DCM comparator、表示轴、缩放/校准参数或
DCM–FEM identity 判据。

v01–v07 的旧源码、测试、runner 和结果只作为 `retired_historical_evidence` 原样保留，
用于审计路线为何终止；它们不是活跃模型、输入、验证资料或论文机制证据。物理删除旧
证据不在本决定授权范围内。

## 2. 独立验收结果

| 检查项 | Supervisor 独立结果 | 结论 |
|---|---:|---|
| 宿主静态/API/投影测试 | 9/9 | PASS |
| 新增 Python 规范检查 | 全部通过 | PASS |
| 活跃包 AST/import 审计 | 8 个文件；0 个旧包 import；0 个禁用路径 | PASS |
| 固定角色与无表示轴 API | 角色不可切换；端点键不含表示 | PASS |
| 六工况迁移等价 | A2/LN/LS/C0/CQ/S1 全部通过 | PASS |
| 数值误差 | 所有冻结标量、数组与投影最大误差均为 0 | PASS |
| ECM 场 | 24/24 数组字节哈希一致 | PASS |
| 正式结果包 | 9 个 JSON；0 个 NPZ；全部有限 | PASS |
| 结果 hash ledger | 8/8 文件字节数与 SHA-256 独立复算一致 | PASS |
| 旧参考与退役源码锁 | 运行前后快照一致 | PASS |
| 资源与边界 | 189.1469 s；0.75544 GiB；单 CPU；无网络/GPU | PASS |

关键结构门同时通过：材料加支撑矩阵与速率矩阵对称；UFL/手工装配相对误差
`1.0322e-15`；界面作用反作用误差 `0`；主动功共轭相对误差 `3.9385e-08`；共同投影
合力误差 `0`，离散界面功误差 `1.3878e-17`。

## 3. 验收解释

六个工况的逐值误差为零，证明新 `paper2_hybrid` 生产实现完整迁移了冻结旧 FEM 臂，
且迁移没有改变求解顺序、观测量或功率账本。该结果足以关闭软件架构迁移门。

它不证明模型具有生理真实性，也不构成 EFE、三维、整心房、流体、实验或临床结论；
更不代表项目已经达到 Nature Physics 投稿证据标准。Nature Physics 继续作为问题设计、
普适规律和独立预测的战略目标，最终期刊必须由后续证据决定。

## 4. 论文主线冻结

接受 `project_control/prl_independent_theory_mainline_plan_v03.md` 作为当前主线：

1. Figure 1：主动心肌 FEM—黏弹 ECM—离散心内膜的三层理论与功率端口；
2. Figure 2：FEM-only 空间、时间、容差、投影和功率闭合；
3. Figure 3：`De x H` 机械传递状态图与留出预测；
4. Figure 4：cell/meso-resolved active FEM 与 homogenized active FEM 的共同极限和
   粗粒化适用域；
5. Figure 5：主动心肌 H-FEM、黏弹 ECM 与离散心内膜的整心房模型；流体后续分层加入。

## 5. 停止边界与下一步

v08 已在 Supervisor Gate 闭合。下一步只能先形成版本化 Figure 1 理论合同，冻结方程、
无量纲组、极限、反例和可证伪通过门；在该合同形成前，不启动 Figure 2 后续求解、
`De x H` 扫描、Figure 4 粗粒化计算、三维、整心房、流体、实验拟合或 GPU worker。
