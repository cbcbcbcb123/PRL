---
plan_id: PLAN-EFE-NODE1-N1-2-BACKEND-PRODUCTIONIZATION-P1-V01
status: approved
planner: codex_project_supervisor
approved_by: human_final_reviewer
approved_at: 2026-08-19
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2 backend productionization P1 计划 v01

## Goal

把已通过 spike 的 FEniCSx ECM 路线改成可显式选择、可回归、可计算切线的
候选生产后端，并判断 PETSc SNES 是否足以替代或补充现有稀疏 Newton。

## Inputs

- 已接受 Python ECM 本构及 F150/D0/E0 静态峰值状态；
- `dolfinx/dolfinx:v0.11.0` 固定 digest 镜像；
- Phase A/Phase B 已通过结果；
- 人类迁移决定
  `project_control/efe_node1_n1_2_fenicsx_backend_migration_decision_v01.md`。

## Outputs

1. 显式 ECM backend seam 与注入测试；
2. FEniCSx ECM 自动微分能量 Hessian/Jacobian 接口；
3. Jacobian 有限差分方向导数验证；
4. PETSc SNES 最小非线性恢复试验及与现有稀疏 Newton 的适用性判断；
5. 基于真实 F150 几何序列的短 SLS 记忆周期回归；
6. P1 执行报告和人类终审包。

## Implementation Steps

1. 给 `evaluate_fast_trilayer_state`、预条件器和 equilibrium solver 增加可选
   backend 参数；默认仍为 Python 参考实现；
2. 修改诊断和峰值 spike 入口使用显式 seam，消除模块级 monkeypatch；
3. 在 FEniCSx backend 中编译残量对位移的二阶自动微分形式，导出输入节点
   顺序的稀疏 Hessian；
4. 用 M0、均匀仿射态和 F150 峰值执行中心差分方向导数、对称性和刚体模态
   检查；
5. 用峰值 ECM 的“目标内力恢复”构造非科学、仅求解器验证的 PETSc SNES
   问题；与当前完整耦合稀疏 Newton 的收敛与成本分开报告；
6. 用 F150 的 `a=0 -> 0.10 -> 0.20 -> 0.10 -> 0` 几何序列推进 SLS
   内变量，对每个相位比较 Python 与 FEniCSx 的能量、内力和 `J`；
7. 运行回归测试和 Ruff，封存失败与最终结果。

## Impacted Files Or Modules

- `src/hybrid/efe_fast_trilayer.py`；
- `src/hybrid/efe_fast_trilayer_solver.py`；
- `src/hybrid/fenicsx_ecm_backend.py`；
- `scripts/diagnose_efe_node1_sparse_preconditioner_v01.py`；
- FEniCSx P1 验证脚本和相应测试；
- `project_control` 中本 P1 的执行与终审记录。

## Test Plan

- 默认参考后端的既有 fast-trilayer 测试必须保持通过；
- 注入 spy/reference backend 后，能量、力、几何指标与默认实现一致；
- Hessian 方向导数相对误差 `<=1e-5`，对称残差 `<=1e-10`；
- PETSc SNES 验证问题必须收敛，残量 `<=1e-8`；
- 短 SLS 周期各相位：总能相对误差 `<=1e-8`、节点力相对 L2
  `<=1e-8`、`J` 最大绝对误差 `<=1e-12`；
- 至少观察到同一 `a=0.10` 几何在上升/下降支因不同 `Z` 产生非零记忆差；
- 相关测试通过，Ruff 通过。

## Risks

- 二阶 UFL 形式的节点排列或符号可能与现有力定义相反；
- PETSc SNES 的 ECM 子问题成功不代表完整 DCM—FEM 系统已迁移；
- 当前全系统 Jacobian 的 DCM/界面部分仍可能成为速度瓶颈；
- 短 SLS 回归是工程回归，不是周期稳定性科学证据。

## Acceptance Criteria

- 显式 seam 无 monkeypatch，默认行为不变；
- Jacobian 和短 SLS 回归全部达到上述数值门；
- PETSc SNES 的结论按实际结果表述，可接受“技术可用但暂不替换全系统
  Newton”的负结论；
- 所有结果明确标记 `not_formal_n1_2_evidence`；
- 不越过正式 N1-2 人类决策门。

## Out Of Scope

- 正式 `D1/E1/32-step` 计算；
- 全系统解析 DCM/界面 Hessian；
- MPI 扩展、GPU、FEBio plugin；
- N1-3、Node 2、实验和论文最终图。

## Required Memory Updates

P1 经人类终审接受后，才可把候选后端、适用范围和保留 caveat 写入稳定项目
规则；本轮不自行写入 stable memory。
